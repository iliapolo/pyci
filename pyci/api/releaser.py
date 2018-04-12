#############################################################################
# Copyright (c) 2018 Eli Polonsky. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   * See the License for the specific language governing permissions and
#   * limitations under the License.
#
#############################################################################
import os

from boltons.cacheutils import cachedproperty
from github import Github
from github import GithubObject
from github.GithubException import GithubException
from github.GithubException import UnknownObjectException

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils


log = logger.get_logger(__name__)


class GitHubReleaser(object):

    _repo = None
    _logger = None
    _hub = None

    def __init__(self, repo, access_token):
        self._hub = Github(access_token)
        self._repo_name = repo

    @cachedproperty
    def _repo(self):
        log.debug('Fetching repo...')
        repo = self._hub.get_repo(self._repo_name)
        log.debug('Fetched repo: {0}'.format(self._repo_name))
        return repo

    @cachedproperty
    def default_branch(self):
        return self._repo.default_branch

    def release(self, sha=None):
        return _GitHubBranchReleaser(repo=self._repo,
                                     sha=sha).release()

    def upload(self, asset, release):

        release = self._repo.get_release(id=release)
        release.upload_asset(path=asset, content_type='application/octet-stream')

        return 'https://github.com/{0}/releases/download/{1}/{2}'\
            .format(self._repo_name, release.title, os.path.basename(asset))

    def delete(self, version):

        releases = [r for r in list(self._repo.get_releases()) if r.title == version]

        if len(releases) > 1:
            raise exceptions.MultipleReleasesFoundException(release=version,
                                                            how_many=len(releases))

        if releases:
            release = releases[0]
            log.debug('Deleting release: {0}'.format(version))
            release.delete_release()
        else:
            log.debug('Release {0} not found, skipping...'.format(version))

        refs = [ref for ref in list(self._repo.get_git_refs()) if ref.ref == 'refs/tags/{0}'
                .format(version)]

        if len(refs) > 1:
            raise exceptions.MultipleRefsFoundException(ref=version, how_many=len(refs))

        if refs:
            ref = refs[0]
            log.debug('Deleting ref: {0}'.format(ref.ref))
            ref.delete()
        else:
            log.debug('Tag {0} not found, skipping...'.format(version))


# pylint: disable=too-few-public-methods
class _GitHubBranchReleaser(object):

    def __init__(self, repo, sha=None):
        self._repo = repo
        self._sha = sha or self._repo.default_branch

    @cachedproperty
    def _commit(self):
        log.debug('Fetching commit...')
        commit = self._repo.get_commit(sha=self._sha)
        log.debug('Fetched commit: {0}'.format(commit.sha))
        return commit

    @cachedproperty
    def _pr(self):
        log.debug('Fetching pull request...')
        pr = self._fetch_pr(self._commit)
        log.debug('Fetched pull request: {0}'.format(pr))
        return pr

    @cachedproperty
    def _issue(self):
        log.debug('Fetching issue...')
        issue = self._fetch_issue(self._pr)
        log.debug('Fetched issue: {0}'.format(issue))
        return issue

    @cachedproperty
    def _releases(self):
        log.debug('Fetching releases...')
        return list(self._repo.get_releases())

    @cachedproperty
    def _tags(self):
        log.debug('Fetching tags...')
        return list(self._repo.get_tags())

    @cachedproperty
    def _last_release(self):
        log.debug('Extracting latest release')
        last_release = utils.get_latest_release(self._releases)
        log.debug('Extracted latest release: {0}'.format(last_release))
        return last_release

    @cachedproperty
    def _labels(self):
        log.debug('Fetching issue labels...')
        labels = list(self._issue.get_labels())
        log.debug('Fetched labels: {0}'.format(','.join([label.name for label in labels])))
        return labels

    def release(self):

        self._validate_commit()

        label_names = [label.name for label in self._labels]

        next_release = utils.get_next_release(self._last_release, label_names)

        log.debug('Next version will be: {0}'.format(next_release))

        log.debug('Fetching changelog...')

        # pylint: disable=fixme
        # TODO i dont like returning tuples, think of a better way
        changelog = self._generate_changelog()
        changelog_body = changelog[0]
        changelog_issues = changelog[1]

        log.debug('Successfully fetched changelog')

        try:
            log.debug('Creating Github Release...')
            release = self._repo.create_git_release(
                tag=next_release,
                target_commitish=self._commit.sha,
                name=next_release,
                message=changelog_body,
                draft=False,
                prerelease=False
            )
            log.debug('Successfully created release: {0}'.format(next_release))
        except GithubException as e:

            if e.data['errors'][0]['code'] != 'already_exists':
                raise

            release = self._repo.get_release(id=next_release)
            commit = self._fetch_commit(release.tag_name)

            if commit.sha == self._commit.sha:
                # we already checked if this commit is released in _validate_commit(),
                # how can this be? well, there might be concurrent executions running on the
                # same commit (two different CI systems for example)
                raise exceptions.CommitIsAlreadyReleasedException(sha=self._commit.sha,
                                                                  release=next_release)

            # if we get here, its bad. the release already exists but with a different commit than
            # ours? it probably means there are two concurrent release jobs on the same
            # branch...

            # pylint: disable=fixme
            # TODO what should we do here? what are the implications of this?
            raise exceptions.ReleaseConflictException(release=next_release,
                                                      our_sha=self._commit.sha,
                                                      their_sha=commit.sha)

        for issue in changelog_issues:
            self._comment_issue(issue, release)

        log.debug('Fetching master ref...')
        master = self._repo.get_git_ref('heads/master')
        log.debug('Fetched ref: {0}'.format(master.ref))

        log.debug('Updating master branch')
        master.edit(sha=self._commit.sha, force=True)
        log.debug('Successfully updated master branch to: {0}'.format(
            self._commit.sha))

        try:
            pull_request_ref = self._repo.get_git_ref('heads/{0}'.format(self._pr.head.ref))
            log.debug('Deleting ref: {0}'.format(pull_request_ref.ref))
            pull_request_ref.delete()
        except UnknownObjectException:
            # this is ok, the branch doesn't necessarily have to be there.
            # it might have been deleted when the pull request was merged
            pass

        return next_release

    def _validate_commit(self):

        if self._pr is None:
            raise exceptions.CommitNotRelatedToPullRequestException(sha=self._commit.sha)

        if self._issue is None:
            raise exceptions.PullRequestNotRelatedToIssueException(sha=self._commit.sha,
                                                                   pr=self._pr.number)

        label_names = [label.name for label in self._labels]

        next_release = utils.get_next_release(self._last_release, label_names)
        if next_release is None:
            raise exceptions.IssueIsNotLabeledAsReleaseException(issue=self._issue.number,
                                                                 sha=self._commit.sha,
                                                                 pr=self._pr.number)

        if self._last_release:
            tag = [t for t in list(self._tags) if t.name == self._last_release][0]
            if self._commit.sha == tag.commit.sha:
                raise exceptions.CommitIsAlreadyReleasedException(sha=self._commit.sha,
                                                                  release=tag.name)

    def _comment_issue(self, issue, release):

        issue_comment = 'This issue is part of release [{0}]({1})'.format(release.title,
                                                                          release.html_url)

        log.debug('Adding a comment to issue: {0}'.format(self._issue))
        issue.create_comment(body=issue_comment)
        log.debug('Added comment: {0}'.format(issue_comment))

    def _fetch_issue(self, pull_request):

        issue_number = utils.get_issue_number(pull_request.body)
        return self._repo.get_issue(number=int(issue_number)) if issue_number else None

    def _fetch_pr(self, commit):

        pr_number = utils.get_pull_request_number(commit.commit.message)
        return self._repo.get_pull(number=pr_number) if pr_number else None

    def _fetch_commit(self, tag_name):

        tag = self._repo.get_git_ref(ref='tags/{0}'.format(tag_name))

        # pylint: disable=fixme
        # TODO this looks like internal github API. see if we can do better
        sha = tag.raw_data['object']['sha']

        return self._repo.get_commit(sha=sha)

    def _generate_changelog(self):

        since = GithubObject.NotSet
        latest_sha = None
        if self._last_release:

            latest_commit = self._fetch_commit(tag_name=self._last_release)
            since = latest_commit.commit.committer.date
            latest_sha = latest_commit.sha

        commits = list(self._repo.get_commits(sha=self._commit.sha, since=since))

        features = set()
        bugs = set()
        internals = set()

        issues = []

        for commit in commits:

            log.debug('Fetching issue for commit: {0}'.format(commit.commit.message))
            pull_request = self._fetch_pr(commit)
            issue = self._fetch_issue(pull_request) if pull_request else None
            log.debug('Fetched Issue: {0}'.format(issue))

            if issue is None:
                continue

            if commit.sha == latest_sha:
                continue

            labels = [label.name for label in list(issue.get_labels())]

            if 'feature' in labels:
                features.add(Task(title=issue.title, url=issue.html_url))

            if 'bug' in labels:
                bugs.add(Task(title=issue.title, url=issue.html_url))

            if 'internal' in labels:
                internals.add(Task(title=issue.title, url=issue.html_url))

            issues.append(issue)

        return utils.render_changelog(features=features, bugs=bugs, internals=internals), issues


# pylint: disable=too-few-public-methods
class Task(object):

    def __init__(self, title, url):
        self.title = title
        self.url = url

    def __eq__(self, other):
        return other.url == self.url

    def __hash__(self):
        return hash(self.url)
