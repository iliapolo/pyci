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
from github.GithubException import UnknownObjectException

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils


class GitHubReleaser(object):

    _repo = None
    _logger = None
    _hub = None

    def __init__(self, repo, access_token, log_level='info'):

        self._logger = logger.get_logger('api.releaser.GithubReleaser', level=log_level)

        self._hub = Github(access_token)
        self._repo_name = repo

    @cachedproperty
    def _repo(self):
        self._logger.debug('Fetching repo...')
        repo = self._hub.get_repo(self._repo_name)
        self._logger.debug('Fetched repo: {0}'.format(self._repo_name))
        return repo

    def release(self, branch_name):
        return _GitHubBranchReleaser(repo=self._repo,
                                     branch_name=branch_name,
                                     log=self._logger).release()

    def upload(self, asset, release):

        release = self._repo.get_release(id=release)
        release.upload_asset(path=asset, content_type='application/octet-stream')

        return 'https://github.com/{0}/releases/download/{1}/{2}'\
            .format(self._repo.name, release.title, os.path.basename(asset))

    def delete(self, version):

        releases = [r for r in list(self._repo.get_releases()) if r.title == version]

        if len(releases) > 1:
            raise exceptions.MultipleReleasesFoundException(release=version,
                                                            how_many=len(releases))

        if releases:
            release = releases[0]
            self._logger.debug('Deleting release: {0}'.format(version))
            release.delete_release()
        else:
            self._logger.debug('Release {0} not found, skipping...'.format(version))

        refs = [ref for ref in list(self._repo.get_git_refs()) if ref.ref == 'refs/tags/{0}'
                .format(version)]

        if len(refs) > 1:
            raise exceptions.MultipleRefsFoundException(ref=version, how_many=len(refs))

        if refs:
            ref = refs[0]
            self._logger.debug('Deleting ref: {0}'.format(ref.ref))
            ref.delete()
        else:
            self._logger.debug('Tag {0} not found, skipping...'.format(version))


# pylint: disable=too-few-public-methods
class _GitHubBranchReleaser(object):

    def __init__(self, repo, branch_name, log):

        self._logger = log
        self._branch_name = branch_name
        self._repo = repo

    @cachedproperty
    def _branch(self):
        self._logger.debug('Fetching branch...')
        branch = self._repo.get_branch(branch=self._branch_name)
        self._logger.debug('Fetched branch: {0}'.format(branch.name))
        return branch

    @cachedproperty
    def _commit(self):
        self._logger.debug('Fetching commit...')
        commit = self._repo.get_commit(sha=self._branch.commit.sha)
        self._logger.debug('Fetched commit: {0}'.format(commit.sha))
        return commit

    @cachedproperty
    def _pr(self):
        self._logger.debug('Fetching pull request...')
        pr = self._fetch_pr(self._commit)
        self._logger.debug('Fetched pull request: {0}'.format(pr))
        return pr

    @cachedproperty
    def _issue(self):
        self._logger.debug('Fetching issue...')
        issue = self._fetch_issue(self._pr)
        self._logger.debug('Fetched issue: {0}'.format(issue))
        return issue

    @cachedproperty
    def _releases(self):
        self._logger.debug('Fetching releases...')
        return list(self._repo.get_releases())

    @cachedproperty
    def _tags(self):
        self._logger.debug('Fetching tags...')
        return list(self._repo.get_tags())

    @cachedproperty
    def _last_release(self):
        self._logger.debug('Extracting latest release')
        last_release = utils.get_latest_release(self._releases)
        self._logger.debug('Extracted latest release: {0}'.format(last_release))
        return last_release

    @cachedproperty
    def _labels(self):
        self._logger.debug('Fetching issue labels...')
        labels = list(self._issue.get_labels())
        self._logger.debug('Fetched labels: {0}'.format(','.join([label.name for label in labels])))
        return labels

    def release(self):

        should_release = self._should_release()
        should = should_release[0]
        next_release = should_release[1]

        if should:

            self._logger.debug('Next version will be: {0}'.format(next_release))

            self._logger.debug('Fetching changelog...')
            changelog = self._generate_changelog()

            self._logger.debug('Creating Github Release...')
            self._repo.create_git_release(
                tag=next_release,
                target_commitish=self._branch_name,
                name=next_release,
                message=changelog,
                draft=False,
                prerelease=False
            )
            self._logger.debug('Successfully created release: {0}'.format(next_release))

            self._logger.debug('Fetching master ref...')
            master = self._repo.get_git_ref('heads/master')
            self._logger.debug('Fetched ref: {0}'.format(master.ref))

            self._logger.debug('Updating master branch')
            master.edit(sha=self._branch.commit.sha, force=True)
            self._logger.debug('Successfully updated master branch to: {0}'.format(
                self._branch.commit.sha))

            try:
                pull_request_ref = self._repo.get_git_ref('heads/{0}'.format(self._pr.head.ref))
                self._logger.debug('Deleting ref: {0}'.format(pull_request_ref.ref))
                pull_request_ref.delete()
            except UnknownObjectException:
                # this is ok, the branch doesn't necessarily have to be there.
                # it might have been deleted when the pull request was merged
                pass

        return next_release

    def _should_release(self):

        should = True

        if self._last_release:
            tag = [t for t in list(self._tags) if t.name == self._last_release][0]
            if self._commit.sha == tag.commit.sha:
                self._logger.debug('The latest commit of this branch is already released: {0}'
                                   .format(self._last_release))
                should = False

        if self._pr is None:
            self._logger.debug('Commit ({0}) is not related to any pull request, '
                               'not releasing...'.format(self._commit.commit.sha))
            should = False

        if self._issue is None:
            self._logger.debug('Pull request {0} is not related to any issue, '
                               'not releasing...'.format(self._pr.number))
            should = False

        next_release = utils.get_next_release(self._last_release, self._labels)
        if next_release == self._last_release:
            self._logger.debug('The latest commit corresponds to an issue that is not '
                               'marked as a release issue. not releasing....')
            should = False

        return should, next_release

    def _fetch_issue(self, pull_request):

        issue_number = utils.get_issue_number(pull_request.body)
        return self._repo.get_issue(number=int(issue_number)) if issue_number else None

    def _fetch_pr(self, commit):

        pr_number = utils.get_pull_request_number(commit.commit.message)
        return self._repo.get_pull(number=pr_number) if pr_number else None

    def _generate_changelog(self):

        # pylint: disable=too-few-public-methods
        class Task(object):

            def __init__(self, title, url):
                self.title = title
                self.url = url

            def __eq__(self, other):
                return other.url == self.url

            def __hash__(self):
                return hash(self.url)

        since = GithubObject.NotSet
        latest_sha = None
        if self._last_release:

            self._logger.debug('Fetching tag: {0}'.format(self._last_release))
            latest_tag = self._repo.get_git_ref(ref='tags/{0}'.format(self._last_release))
            self._logger.debug('Fetched tag: {0}'.format(self._last_release))

            # pylint: disable=fixme
            # TODO this looks like internal github API. see if we can do better
            latest_sha = latest_tag.raw_data['object']['sha']

            latest_commit = self._repo.get_commit(sha=latest_sha)
            since = latest_commit.commit.committer.date

        commits = list(self._repo.get_commits(sha=self._branch.name, since=since))

        features = set()
        bugs = set()

        for commit in commits:

            self._logger.debug('Fetching issue for commit: {0}'.format(commit.commit.message))
            pull_request = self._fetch_pr(commit)
            issue = self._fetch_issue(pull_request) if pull_request else None
            self._logger.debug('Fetched Issue: {0}'.format(issue))

            if issue is None:
                continue

            if commit.sha == latest_sha:
                continue

            labels = [label.name for label in list(issue.get_labels())]

            if 'feature' in labels:
                features.add(Task(title=issue.title, url=issue.html_url))

            if 'bug' in labels:
                bugs.add(Task(title=issue.title, url=issue.html_url))

        return utils.render_changelog(features=features, bugs=bugs)
