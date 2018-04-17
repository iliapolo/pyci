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

import semver
from boltons.cacheutils import cachedproperty
from github import Github
from github import GithubObject
from github import InputGitTreeElement
from github.GitCommit import GitCommit
from github.GithubException import GithubException
from github.GithubException import UnknownObjectException

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api.changelog import Changelog
from pyci.api.runner import LocalCommandRunner
from pyci.api.utils import download

log = logger.get_logger(__name__)


BUMP_COMMIT_MESSAGE_FORMAT = 'Bump version to {0} following commit {1}'


class GitHub(object):

    __branches = {}

    _hub = None

    def __init__(self, repo, access_token, master_branch='master'):
        self._hub = Github(access_token)
        self._repo_name = repo
        self.master_branch_name = master_branch

    @cachedproperty
    def repo(self):
        log.debug('Fetching repo [repo_name={0}]'.format(self._repo_name))
        repo = self._hub.get_repo(self._repo_name)
        log.debug('Fetched repo [repo={0}]'.format(repo.url))
        return repo

    @cachedproperty
    def last_release(self):
        last_release = None
        try:
            log.debug('Fetching latest release')
            last_release = self.repo.get_latest_release()
        except UnknownObjectException:
            pass
        log.debug('Fetched latest release [release={0}]'.format(
            last_release.url if last_release else None))
        return last_release

    @cachedproperty
    def default_branch_name(self):
        log.debug('Fetching default branch')
        branch = self.repo.default_branch
        log.debug('Fetched default branch [default_branch={0}]'.format(branch))
        return branch

    def validate(self, branch_name=None, sha=None):
        branch_name = branch_name or self.default_branch_name
        return self._get_or_create_branch(branch_name).validate(sha=sha)

    def changelog(self, branch_name=None, sha=None):
        branch_name = branch_name or self.default_branch_name
        return self._get_or_create_branch(branch_name).changelog(sha=sha)

    def release(self, branch_name=None, sha=None, version=None):
        branch_name = branch_name or self.default_branch_name
        return self._get_or_create_branch(branch_name).release(sha=sha, version=version)

    def upload(self, asset, release):

        asset = os.path.abspath(asset)

        utils.validate_file_exists(asset)

        git_release = self.repo.get_release(id=release)
        try:
            git_release.upload_asset(path=asset, content_type='application/octet-stream')
        except IOError:
            # this is so messed up, pygithub does not raise
            # a proper exception in case the asset already exists.
            # so we are left with assuming that is the case.

            # pylint: disable=fixme
            # TODO open a bug in pygithub

            asset_name = os.path.basename(asset)
            raise exceptions.AssetAlreadyPublishedException(asset=asset_name,
                                                            release=git_release.title)

        return 'https://github.com/{0}/releases/download/{1}/{2}' \
            .format(self._repo_name, git_release.title, os.path.basename(asset))

    def issue(self, sha=None, commit_message=None):

        assert sha or commit_message
        assert not (sha and commit_message)

        if not commit_message:
            commit_message = self.repo.get_commit(sha=sha).commit.message

        log.debug('Extracting href from commit message: {0}'.format(commit_message))
        ref = utils.get_href(commit_message)
        log.debug('Extracted href from commit: {0}'.format(ref))

        pr_number = None
        issue_number = None

        if ref:
            try:

                log.debug('Checking if href ({0}) is a pull request...'.format(ref))
                pull = self.repo.get_pull(number=ref)
                log.debug('Href ({0}) is a pull request: {1}'.format(ref, pull.number))

                pr_number = ref

                log.debug('Extracting issue number from pull request body: {0}'.format(pull.body))
                issue_number = utils.get_href(pull.body)
                log.debug('Extracted issue number from pull request body: {0}'
                          .format(issue_number))

            except UnknownObjectException:
                log.debug('Href ({0}) is not a pull request'.format(ref))
                # ref is not a pull request.
                # that's ok
                pr_number = None

                issue_number = ref
                log.debug('Assuming href is an issue number: {0}'.format(issue_number))

        if issue_number:
            try:
                log.debug('Fetching issue number {0}...'.format(issue_number))
                issue = self.repo.get_issue(number=issue_number)
                log.debug('Successfully fetched issue: {0}'.format(issue.number))
                return issue
            except UnknownObjectException:
                # this is unexpected, it means the reference in either the pull
                # request or the commit points to a non existing issue!
                raise exceptions.IssueNotFoundException(commit_message=commit_message,
                                                        pr_number=pr_number,
                                                        issue_number=issue_number)

        return None

    def delete(self, release):

        try:
            rel = self.repo.get_release(id=release)
            log.debug('Deleting release [id={0}]'.format(release))
            rel.delete_release()
        except UnknownObjectException:
            log.debug('Release not found, skipping [title={0}]'.format(release))

        try:
            tag = self.repo.get_git_ref('tags/{0}'.format(release))
            log.debug('Deleting ref [ref={0}]'.format(tag.ref))
            tag.delete()
            log.debug('Ref not found, skipping [ref={0}]'.format(tag.ref))
        except UnknownObjectException:
            pass

    def bump(self,
             sha=None,
             version=None,
             patch=False,
             minor=False,
             major=False,
             dry=False,
             branch_name=None):
        branch_name = branch_name or self.default_branch_name
        return self._get_or_create_branch(branch_name).bump(
            sha=sha,
            version=version,
            patch=patch,
            minor=minor,
            major=major,
            dry=dry)

    def _get_or_create_branch(self, branch_name=None):
        branch_name = branch_name or self.default_branch_name
        if branch_name not in self.__branches:
            self.__branches[branch_name] = _GitHubBranch(gh=self, branch_name=branch_name)
        return self.__branches[branch_name]


class _GitHubBranch(object):

    __commits = {}

    def __init__(self, gh, branch_name):
        self.github = gh
        self.branch_name = branch_name
        self._runner = LocalCommandRunner()

    def validate(self, sha):
        sha = sha or self.branch_name
        return self._get_or_create_commit(sha=sha).validate()

    def changelog(self, sha):
        sha = sha or self.branch_name
        return self._get_or_create_commit(sha=sha).changelog()

    def release(self, sha, version):
        sha = sha or self.branch_name
        return self._get_or_create_commit(sha=sha).release(version=version)

    def commit(self, file_path, file_contents, message):

        tree = InputGitTreeElement(path=file_path,
                                   mode='100644',
                                   type='blob',
                                   content=file_contents)

        last_commit = self.github.repo.get_commit(sha=self.branch_name)
        base_tree = self.github.repo.get_git_tree(sha=last_commit.commit.tree.sha)
        git_tree = self.github.repo.create_git_tree(tree=[tree], base_tree=base_tree)

        commit = self.github.repo.create_git_commit(message=message,
                                                    tree=git_tree,
                                                    parents=[last_commit.commit])

        ref = self.github.repo.get_git_ref(ref='heads/{0}'.format(self.branch_name))
        ref.edit(sha=commit.sha)

        return commit

    def bump(self, sha, version, patch, minor, major, dry):

        sha = sha or self.branch_name

        commit = self._get_or_create_commit(sha=sha)

        current_version = commit.setup_py_version
        setup_py = commit.setup_py

        if version:
            log.debug('Validating the given version string ({0}) is a legal semver...'
                      .format(version))
            semver.parse(version)

        def _bump_current_version():

            result = current_version

            if patch:
                result = semver.bump_patch(result)
            if minor:
                result = semver.bump_minor(result)
            if major:
                result = semver.bump_major(result)

            return result

        next_version = version or _bump_current_version()

        setup_py = utils.generate_setup_py(setup_py, next_version)

        commit_message = BUMP_COMMIT_MESSAGE_FORMAT.format(next_version, sha)

        if not dry and current_version != next_version:
            return self.commit(file_path='setup.py',
                               file_contents=setup_py,
                               message=commit_message)

        return setup_py

    def _get_or_create_commit(self, sha):
        if sha not in self.__commits:
            self.__commits[sha] = _GitHubCommit(branch=self, sha=sha)
        return self.__commits[sha]


class _GitHubCommit(object):

    def __init__(self, branch, sha):
        self._branch = branch
        self._sha = sha
        self._runner = LocalCommandRunner()

    @cachedproperty
    def commit(self):
        log.debug('Fetching commit [sha={0}]'.format(self._sha))
        commit = self._branch.github.repo.get_commit(sha=self._sha)
        log.debug('Fetched commit [commit={0}]'.format(commit.url))
        return commit

    @cachedproperty
    def pr(self):
        log.debug('Fetching pull request [commit={0}]'.format(self.commit.url))
        pr = self._fetch_pr(self.commit)
        log.debug('Fetched pull request [pr={0}]'.format(pr.url if pr else None))
        return pr

    @cachedproperty
    def issue(self):
        log.debug('Fetching issue [commit={0}]'.format(self.commit.url))
        issue = self._branch.github.issue(commit_message=self.commit.commit.message)
        log.debug('Fetched issue. [issue={0}]'.format(issue.url if issue else None))
        return issue

    @cachedproperty
    def labels(self):
        log.debug('Fetching issue labels [issue={0}]'.format(self.issue.url))
        labels = list(self.issue.get_labels())
        log.debug('Fetched labels. [labels={0}]'.format(','.join([label.name for label in labels])))
        return labels

    @cachedproperty
    def setup_py_path(self):
        setup_py_url = 'https://raw.githubusercontent.com/{0}/{1}/setup.py'.format(
            self._branch.github.repo.full_name, self.commit.sha)
        log.debug('Downloading setup.py from: {0}'.format(setup_py_url))
        setup_py_path = download(url=setup_py_url)
        log.debug('Successfully downloaded setup.py')
        return setup_py_path

    @cachedproperty
    def setup_py(self):
        with open(self.setup_py_path) as stream:
            return stream.read()

    @cachedproperty
    def setup_py_version(self):
        return self._runner.run('python {0} --version'.format(self.setup_py_path)).std_out

    def release(self, version=None):

        log.debug('Fetching changelog...')

        changelog = self.changelog()

        if changelog.empty:

            title = self._branch.github.last_release.title

            # this definitely means the commit has already been released, however, it might have
            # been released in a release prior to the last one. this is why we cant raise a
            # CommitIsAlreadyReleasedException.
            # having said that, there is a special case where we CAN verify that the last release
            # was indeed the one to release this commit. here it is:

            last_release_commit = self._fetch_tag_commit(tag_name=title)
            if last_release_commit.commit.message == BUMP_COMMIT_MESSAGE_FORMAT.format(
                    title,
                    self.commit.sha):
                raise exceptions.CommitIsAlreadyReleasedException(sha=self.commit.sha,
                                                                  release=title)

            raise exceptions.EmptyChangelogException(sha=self.commit.sha, last_release=title)

        log.debug('Successfully fetched changelog')

        log.debug('Calculating what the next version number should...')

        version = version or changelog.next_version
        if not version:
            raise exceptions.CannotDetermineNextVersionException(sha=self.commit.sha)

        log.debug('Next version will be: {0}'.format(version))

        log.debug('Validating next version number ({0})...'.format(version))
        self._validate_version(version)
        log.debug('Validation passed')

        log.debug('Creating Github Release ({0})...'.format(version))
        release = self._create_release(version)
        log.debug('Successfully created release: {0}'.format(version))

        for issue in changelog.issues:
            self._close_issue(issue, release)

        log.debug('Creating a version bump commit on branch: {0}'.format(self._branch.branch_name))
        bump_version_commit = self._branch.bump(sha=self.commit.sha,
                                                version=version,
                                                major=False,
                                                minor=False,
                                                patch=False,
                                                dry=False)
        log.debug('Successfully bumped version to: {0}'.format(version))

        log.debug('Fetching release tag...')
        release_tag = self._branch.github.repo.get_git_ref('tags/{0}'.format(release.tag_name))
        log.debug('Fetched releases tag: {0}'.format(release_tag.ref))

        if isinstance(bump_version_commit, GitCommit):
            changelog.add_dangling_commit(bump_version_commit)
            log.debug('Updating tag ({0}) with version commit: {1}'
                      .format(release.tag_name, bump_version_commit.message))
            release_tag.edit(sha=bump_version_commit.sha, force=True)
            log.debug('Successfully updated tag ({0}) with version commit: {1}'
                      .format(release.tag_name, bump_version_commit.message))

        log.debug('Updating release ({0}) with changelog...'.format(release.title))
        release.update_release(name=release.title, message=changelog.render())
        log.debug('Successfully updated release with changelog')

        log.debug('Fetching master ref...')
        master = self._branch.github.repo.get_git_ref('heads/{0}'.format(
            self._branch.github.master_branch_name))
        log.debug('Fetched ref: {0}'.format(master.ref))

        log.debug('Updating {0} branch with release sha: {1}'
                  .format(self._branch.github.master_branch_name, release_tag.object.sha))
        master.edit(sha=release_tag.object.sha, force=True)
        log.debug('Successfully updated {0} branch to: {1}'
                  .format(self._branch.github.master_branch_name, release_tag.object.sha))

        if self.pr:
            try:
                pull_request_ref = self._branch.github.repo.get_git_ref(
                    'heads/{0}'.format(self.pr.head.ref))
                log.debug('Deleting ref: {0}'.format(pull_request_ref.ref))
                pull_request_ref.delete()
            except UnknownObjectException:
                # this is ok, the branch doesn't necessarily have to be there.
                # it might have been deleted when the pull request was merged
                pass

        return version

    def validate(self):

        if self.issue is None:
            raise exceptions.CommitNotRelatedToIssueException(sha=self.commit.sha)

        test_release = '0.0.0'
        next_release = utils.get_next_release('0.0.0', [label.name for label in self.labels])
        if next_release == test_release:
            # this means the issue will not cause a version bump.
            # which means its not labeled as a release candidate.
            raise exceptions.IssueIsNotLabeledAsReleaseException(issue=self.issue.number,
                                                                 sha=self.commit.sha,
                                                                 pr=self.pr.number)

    def changelog(self):

        since = GithubObject.NotSet
        last_release_sha = None
        last_release_title = None
        if self._branch.github.last_release:

            last_release_title = self._branch.github.last_release.title
            last_release_commit = self._fetch_tag_commit(tag_name=last_release_title)
            since = last_release_commit.commit.committer.date
            last_release_sha = last_release_commit.sha

        log.debug('Fetching commits prior to {0} since the last release ({1})'.format(
            self.commit.sha, last_release_title))
        commits = list(self._branch.github.repo.get_commits(sha=self.commit.sha, since=since))
        log.debug('Fetched {0} commits'.format(len(commits)))

        features = set()
        bugs = set()
        internals = set()
        dangling_commits = []

        for commit in commits:

            log.debug('Fetching issue for commit: {0}'.format(commit.commit.message))
            issue = self._branch.github.issue(commit_message=commit.commit.message)
            log.debug('Fetched Issue: {0}'.format(issue))

            if commit.sha == last_release_sha:
                continue

            if issue is None:
                dangling_commits.append(commit.commit)
                continue

            labels = [label.name for label in list(issue.get_labels())]

            if 'feature' in labels:
                features.add(issue)

            if 'bug' in labels:
                bugs.add(issue)

            if 'internal' in labels:
                internals.add(issue)

        return Changelog(features=features,
                         bugs=bugs,
                         internals=internals,
                         dangling_commits=dangling_commits,
                         current_version=self.setup_py_version)

    def _create_release(self, next_release):
        try:
            release = self._branch.github.repo.create_git_release(
                tag=next_release,
                target_commitish=self.commit.sha,
                name=next_release,
                message='',
                draft=False,
                prerelease=False
            )
        except GithubException as e:

            if e.data['errors'][0]['code'] != 'already_exists':
                raise

            release = self._branch.github.repo.get_release(id=next_release)
            release_commit = self._fetch_tag_commit(release.tag_name)

            if release_commit.sha == self.commit.sha:
                # there might be concurrent executions running on the
                # same commit (two different CI systems for example)
                raise exceptions.CommitIsAlreadyReleasedException(sha=self.commit.sha,
                                                                  release=next_release)

            bump_version_message = BUMP_COMMIT_MESSAGE_FORMAT.format(next_release, self.commit.sha)
            if release_commit.commit.message == bump_version_message:
                # this means the commits of the release is actually just a bump version commit
                # the followed our commit. we consider this as being the same commit as ours.

                # pylint: disable=fixme
                # TODO maybe this should be a specific exception type?
                raise exceptions.CommitIsAlreadyReleasedException(sha=self.commit.sha,
                                                                  release=next_release)

            # if we get here, its bad. the release already exists but with a different commit than
            # ours? it probably means there are two concurrent release jobs on the same
            # branch...

            # pylint: disable=fixme
            # TODO what should we do here? what are the implications of this?
            raise exceptions.ReleaseConflictException(release=next_release,
                                                      our_sha=self.commit.sha,
                                                      their_sha=release_commit.sha)
        return release

    def _validate_version(self, version):

        try:
            semver.parse(version)
        except (TypeError, ValueError):
            raise exceptions.SemanticVersionException(version=version)

        if self._branch.github.last_release and semver.compare(
                version, self._branch.github.last_release.title) <= 0:
            raise exceptions.TargetVersionNotGreaterThanLastReleaseVersionException(
                target_version=version,
                last_release_version=self._branch.github.last_release.title)

        if semver.compare(version, self.setup_py_version) <= 0:
            raise exceptions.TargetVersionNotGreaterThanSetupPyVersionException(
                current_version=self.setup_py_version, target_version=version)

    def _fetch_pr(self, commit):
        pr_number = utils.get_href(commit.commit.message)
        return self._branch.github.repo.get_pull(number=pr_number) if pr_number else None

    def _fetch_tag_commit(self, tag_name):
        tag = self._branch.github.repo.get_git_ref(ref='tags/{0}'.format(tag_name))
        return self._branch.github.repo.get_commit(sha=tag.object.sha)

    @staticmethod
    def _close_issue(issue, release):

        issue_comment = 'This issue is part of release [{0}]({1})'.format(
            release.title, release.html_url)

        log.debug('Closing issue {0}...'.format(issue.number))
        issue.edit(state='closed')
        log.debug('Successfully closed issue: {0}'.format(issue.number))

        log.debug('Adding a comment to issue: {0}'.format(issue))
        issue.create_comment(body=issue_comment)
        log.debug('Added comment: {0}'.format(issue_comment))
