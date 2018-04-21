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
import copy
import os

import semver
from boltons.cacheutils import cachedproperty
# noinspection PyPackageRequirements
from github import Github
# noinspection PyPackageRequirements
from github import GithubObject
# noinspection PyPackageRequirements
from github import InputGitTreeElement
# noinspection PyPackageRequirements
from github.GithubException import GithubException
# noinspection PyPackageRequirements
from github.GithubException import UnknownObjectException

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api.model.changelog import Changelog
from pyci.api.model.changelog import ChangelogCommit
from pyci.api.model.changelog import ChangelogIssue
from pyci.api.model.issue import Issue
from pyci.api.model.release import Release
from pyci.api.runner import LocalCommandRunner
from pyci.api.utils import download

log = logger.get_logger(__name__)


BUMP_COMMIT_MESSAGE_FORMAT = 'Bump version to {0} following commit {1}'


class GitHub(object):

    """
    Provides Github capabilities.

    Each instance of this class is associated with a certain repository.

    Args:
        repo (str): The repository full name. (e.g iliapolo/pyci)
        access_token (str): The access token for using Github Rest API.
        master_branch (:`str`, optional): What is the master branch of the repository. This is
            not the default branch, but rather the master one. That is, the branch that will
            represent the latest stable version of the project. Defaults to 'master'.
    """

    def __init__(self, repo, access_token, master_branch='master'):
        self.__branches = {}
        self._hub = Github(access_token)
        self._repo_name = repo
        self.master_branch_name = master_branch
        self._log_ctx = {
            'repo': self._repo_name,
            'master_branch': self.master_branch_name
        }

    @cachedproperty
    def repo(self):
        try:
            self._debug('Fetching repo...')
            repo = self._hub.get_repo(self._repo_name)
            self._debug('Fetched repo.', repo_url=repo.html_url)
            return repo
        except UnknownObjectException:
            raise exceptions.RepositoryNotFoundException(repo=self._repo_name)

    @cachedproperty
    def last_release(self):
        try:
            self._debug('Fetching latest release...')
            last_release = self.repo.get_latest_release()
            self._debug('Fetched latest release.', last_release=last_release.url)
            return last_release
        except UnknownObjectException:
            self._debug('No releases exist yet.')

    @cachedproperty
    def default_branch_name(self):
        self._debug('Fetching default branch...')
        branch = self.repo.default_branch
        self._debug('Fetched default branch.', default_branch=branch)
        return branch

    def validate_commit(self, branch=None, sha=None):

        """
        Validate a commit should be be released. Valid commits are one's who are attached to an
        issue that has at least one of the release labels. i.e, such an issue that will cause a
        version bump.

        Args:
            branch (:`str`, optional): Which branch name does the commit belong to.
                Defaults to the default branch of the repository.
            sha (:`str`, optional): What is the sha of the commit. Defaults to the value of
                branch_name.

        Raises:
            CommitNotRelatedToIssueException: Raised when the commit is not related to any issue.
            IssueIsNotLabeledAsReleaseException: Raised when the issue does not have any release
                labels.

        """

        branch = branch or self.default_branch_name
        self._get_or_create_branch(branch).validate_commit(sha=sha)

    def generate_changelog(self, branch=None, sha=None):

        """
        Generate a changelog for the given commit.

        The generated changelog is always with respect to the latest release of the repository.

        Args:
            branch (:`str`, optional): Which branch name does the commit belong to.
                Defaults to the default branch of the repository.
            sha (:`str`, optional): What is the sha of the commit. Defaults to the value of
                branch_name.

        Returns:
            pyci.api.model.changelog.Changelog: A changelog instance.
        """

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).generate_changelog(sha=sha)

    def create_release(self, branch=None, sha=None, version=None):

        """
        Release a commit and assign it the given version. This method will also attach
        a complete changelog to the release.

        Args:
            branch (:`str`, optional): Which branch name does the commit belong to.
                Defaults to the default branch of the repository.
            sha (:`str`, optional): What is the sha of the commit. Defaults to the value of
                branch_name.
            version (str): Which version should the release have. If None is specified,
            it will be auto-incremented according to this commits changelog. This will be the
            release name.

        Returns:
            pyci.api.model.release.Release: A release object containing information about the
                release.

        """

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).create_release(sha=sha, version=version)

    def upload_asset(self, asset, release):

        """
        Upload an asset to an existing Github release.

        Args:
            asset (str): Path to the asset file.
            release (str): The release title.

        Raises:
            AssetAlreadyPublishedException: Raised when the given asset already exists in the
                release. This is determined by the basename of the asset file path.

        """
        asset = os.path.abspath(asset)

        self._debug('Validating asset file exists...', asset=asset)
        utils.validate_file_exists(asset)
        self._debug('Validated asset file exists.', asset=asset)

        try:
            self._debug('Fetching release...', release=release)
            git_release = self.repo.get_release(id=release)
            self._debug('Fetched release.', release_url=git_release.url)
        except UnknownObjectException:
            raise exceptions.ReleaseNotFoundException(release=release)

        try:
            self._debug('Uploading asset...', asset=asset, release=release)
            git_release.upload_asset(path=asset, content_type='application/octet-stream')
            asset_url = 'https://github.com/{0}/releases/download/{1}/{2}'.format(
                self._repo_name, git_release.title, os.path.basename(asset))
            self._debug('Uploaded asset.', asset_url=asset_url, release=release)
            return asset_url
        except IOError:
            # this is so messed up, pygithub does not raise
            # a proper exception in case the asset already exists.
            # so we are left with assuming that is the case.

            # pylint: disable=fixme
            # TODO open a bug in pygithub

            asset_name = os.path.basename(asset)
            raise exceptions.AssetAlreadyPublishedException(asset=asset_name,
                                                            release=git_release.title)
        except GithubException as e:

            if e.data['errors'][0]['code'] == 'already_exists':
                asset_name = os.path.basename(asset)
                raise exceptions.AssetAlreadyPublishedException(asset=asset_name,
                                                                release=git_release.title)

            raise

    def detect_issue(self, sha=None, commit_message=None):

        """
        Detect which issue a commit is related to. This is done by looking up the number
        following the '#' sign in the commit message. If this number corresponds to an issue,
        we are done. If not, check if it corresponds to a pull request, if so, detect the issue
        number from the pull request body.

        Args:
            sha (:`str`, optional): The commit sha. Used to retrieve the commit message. Not
                needed if you pass 'commit_message' directly.
            commit_message (:`str`, optional): The commit message to detect from. Not necessary
                if you pass the 'sha' argument.

        Return:
            int: The issue number, or None if not found.
        """

        if not sha and not commit_message:
            raise exceptions.InvalidArgumentsException('either sha or commit_message is required.')

        if sha and commit_message:
            raise exceptions.InvalidArgumentsException('either sha or commit_message is allowed.')

        self._debug('Detecting issue for commit...', sha=sha, commit_message=commit_message)

        if not commit_message:
            self._debug('Fetching commit message...', sha=sha)
            commit_message = self.repo.get_commit(sha=sha).commit.message
            self._debug('Fetched commit message...', sha=sha, commit_message=commit_message)

        self._debug('Extracting link...', sha=sha, commit_message=commit_message)
        ref = utils.extract_link(commit_message)
        self._debug('Extracted link.', sha=sha, commit_message=commit_message, link=ref)

        pr_number = None
        issue_number = None

        if ref:
            try:

                self._debug('Fetching pull request...', sha=sha, commit_message=commit_message,
                            ref=ref)
                pull = self.repo.get_pull(number=ref)
                self._debug('Fetched pull request.', sha=sha, commit_message=commit_message,
                            ref=ref, pull_request=pull.url)

                pr_number = ref

                self._debug('Extracting issue number from pull request body...', sha=sha,
                            commit_message=commit_message, ref=ref, pull_request_body=pull.body)
                issue_number = utils.extract_link(pull.body)
                self._debug('Extracted issue number from pull request body', sha=sha,
                            commit_message=commit_message, ref=ref, pull_request_body=pull.body,
                            issue_number=issue_number)

            except UnknownObjectException:
                self._debug('Link is not a pull request.', sha=sha, commit_message=commit_message,
                            ref=ref)
                # ref is not a pull request.
                # that's ok
                pr_number = None

                issue_number = ref

        if issue_number:
            try:
                self._debug('Fetching issue...', sha=sha, commit_message=commit_message,
                            issue_number=issue_number)
                issue = self.repo.get_issue(number=issue_number)
                self._debug('Fetched issue.', sha=sha, commit_message=commit_message,
                            issue_url=issue.url)
                return Issue(impl=issue, number=issue.number, url=issue.html_url)
            except UnknownObjectException:
                # this is unexpected, it means the reference in either the pull
                # request or the commit points to a non existing issue!
                raise exceptions.IssueNotFoundException(commit_message=commit_message,
                                                        pr_number=pr_number,
                                                        issue_number=issue_number)

        self._debug('No link found in commit message', sha=sha, commit_message=commit_message)
        return None

    def delete_release(self, release):

        """
        Delete a release.

        Args:
            release (str): The release title.

        Raises:
            ReleaseNotFoundException: Raised when the given release is not found.
        """
        try:

            self._debug('Fetching release...', release=release)
            rel = self.repo.get_release(id=release)
            self._debug('Fetched release.', release=release)

            self._debug('Deleting release...', release=release)
            rel.delete_release()
            self._debug('Deleted release.', release=release)

        except UnknownObjectException:
            raise exceptions.ReleaseNotFoundException(release=release)

    def delete_tag(self, tag):

        """
        Delete a tag.

        Args:
            tag (str): The tag name.

        Raises:
            TagNotFoundException: Raised when the given tag is not found.
        """

        try:
            self._debug('Fetching tag...', release=tag)
            tag = self.repo.get_git_ref('tags/{0}'.format(tag))
            self._debug('Fetched tag.', tag=tag.ref)

            self._debug('Deleting ref', ref=tag.ref)
            tag.delete()
            self._debug('Deleted ref', ref=tag.ref)

        except UnknownObjectException:
            raise exceptions.TagNotFoundException(tag=tag)

    def bump_version(self, sha=None, version=None, version_modifier=None, dry=False, branch=None):

        """
        Bump the version of setup.py according the version modifiers.
        Note, This will actually create a commit on top of the branch you specify.

        Args:
            sha (:`str`, optional): Sha of the commit that the current setup.py version is
                extracted from. Defaults to the value of branch_name.
            version (:`str`, optional): Which version setup.py should have. If None is specified,
                this will be calculated according to the version modifiers.
            version_modifier (:`str`, optional): A semantic version modifier (e.g minor, major..)
            dry (:`bool`, optional): Instead of performing the commit, just returns the
                contents of setup.py as it would be. Defaults to False.
            branch (:`str`, optional): The branch name to perform to commit on. Defaults to
                the default branch of the repository.

        Returns:
            GitCommit: The commit that bumped the version. Or the contents of setup.py in case
                the dry argument was True.
        """

        if version and version_modifier:
            raise exceptions.InvalidArgumentsException('either version or version_modifier is '
                                                       'allowed')

        branch = branch or self.default_branch_name
        commit = self._get_or_create_branch(branch).bump_version(
            sha=sha,
            version=version,
            version_modifier=version_modifier,
            dry=dry)
        return commit

    def close_issue(self, issue, release):

        issue_comment = 'This issue is part of release [{}]({})'.format(
            release.title, release.html_url)

        self._debug('Closing issue...', issue=issue.number)
        issue.edit(state='closed')
        self._debug('Successfully closed issue.', issue=issue.number)

        issue_comments = [comment.body for comment in issue.get_comments()]

        if issue_comment not in issue_comments:
            self._debug('Adding a comment to issue...', issue=issue.number)
            issue.create_comment(body=issue_comment)
            self._debug('Added comment.', issue=issue.number, comment=issue_comment)

    def reset_branch(self, branch, sha):

        self._debug('Fetching master ref...', branch=branch)
        ref = self.repo.get_git_ref('heads/{0}'.format(branch))
        self._debug('Fetched ref', ref=ref.ref)

        self._debug('Resetting branch with sha', branch=branch, sha=sha)
        ref.edit(sha=sha, force=True)
        self._debug('Reset branch with sha', branch=branch, sha=sha)

    def reset_tag(self, tag, sha):

        self._debug('Fetching tag ref...', tag=tag)
        ref = self.repo.get_git_ref('tags/{0}'.format(tag))
        self._debug('Fetched tag ref', ref=ref.ref)

        self._debug('Resetting branch with sha', tag=tag, sha=sha)
        ref.edit(sha=sha, force=True)
        self._debug('Reset branch with sha', tag=tag, sha=sha)

    def _get_or_create_branch(self, branch=None):
        branch = branch or self.default_branch_name
        if branch not in self.__branches:
            self.__branches[branch] = _GitHubBranch(gh=self, branch_name=branch)
        return self.__branches[branch]

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)


class _GitHubBranch(object):

    def __init__(self, gh, branch_name):
        self.github = gh
        self.branch_name = branch_name
        self.__commits = {}
        self._runner = LocalCommandRunner()
        self._log_ctx = {
            'repo': self.github.repo.full_name,
            'branch': self.branch_name
        }

    def validate_commit(self, sha):
        sha = sha or self.branch_name
        self._debug('Validating...', sha=sha)
        self._get_or_create_commit(sha=sha).validate_commit()
        self._debug('Validated.', sha=sha)

    def generate_changelog(self, sha):
        sha = sha or self.branch_name
        self._debug('Generating changelog...', sha=sha)
        changelog = self._get_or_create_commit(sha=sha).generate_changelog()
        self._debug('Generated changelog.', sha=sha, changelog=changelog)
        return changelog

    def create_release(self, sha, version):
        sha = sha or self.branch_name
        return self._get_or_create_commit(sha=sha).create_release(version=version)

    def commit_file(self, path, contents, message):

        tree = InputGitTreeElement(path=path,
                                   mode='100644',
                                   type='blob',
                                   content=contents)

        self._debug('Fetching last commit for branch...')
        last_commit = self.github.repo.get_commit(sha=self.branch_name)
        self._debug('Fetched last commit for branch.', last_commit=last_commit.sha)

        self._debug('Fetching base tree for sha...', sha=last_commit.commit.tree.sha)
        base_tree = self.github.repo.get_git_tree(sha=last_commit.commit.tree.sha)
        self._debug('Fetched base tree for sha', sha=last_commit.commit.tree.sha,
                    tree=base_tree.sha)

        self._debug('Creating tree...', tree_element=tree, base_tree=base_tree.sha)
        git_tree = self.github.repo.create_git_tree(tree=[tree], base_tree=base_tree)
        self._debug('Created tree.', tree_element=tree, tree_sha=git_tree.sha,
                    base_tree=base_tree.sha)

        self._debug('Creating commit...', commit_message=message, tree=git_tree.sha,
                    parent=last_commit.sha)
        commit = self.github.repo.create_git_commit(message=message,
                                                    tree=git_tree,
                                                    parents=[last_commit.commit])
        self._debug('Created commit', commit_message=message, tree=git_tree.sha,
                    parent=last_commit.sha,
                    sha=commit.sha)

        self._debug('Updating branch to point to commit...', branch=self.branch_name,
                    sha=commit.sha)
        ref = self.github.repo.get_git_ref(ref='heads/{0}'.format(self.branch_name))
        ref.edit(sha=commit.sha)
        self._debug('Updated branch to point to commit', branch=self.branch_name,
                    sha=ref.object.sha)

        return commit

    def bump_version(self, sha, version, version_modifier, dry):

        sha = sha or self.branch_name

        commit = self._get_or_create_commit(sha=sha)

        current_version = commit.setup_py_version
        setup_py = commit.setup_py

        if version:
            self._debug('Validating the given version string is a legal semver...', version=version)
            semver.parse(version)

        def _bump_current_version():

            result = current_version

            if version_modifier == ChangelogIssue.PATCH:
                self._debug('Bumping patch version', version=result)
                result = semver.bump_patch(result)
                self._debug('Bumped patch version', version=result)
            if version_modifier == ChangelogIssue.MINOR:
                self._debug('Bumping minor version', version=result)
                result = semver.bump_minor(result)
                self._debug('Bumped minor version', version=result)
            if version_modifier == ChangelogIssue.MAJOR:
                self._debug('Bumping major version', version=result)
                result = semver.bump_major(result)
                self._debug('Bumped major version', version=result)

            return result

        self._debug('Determining next version', current_version=current_version)
        next_version = version or _bump_current_version()
        self._debug('Determined next version', current_version=current_version,
                    next_version=next_version)

        self._debug('Generating setup.py file contents...', setup_py=setup_py,
                    next_version=next_version)
        setup_py = utils.generate_setup_py(setup_py, next_version)
        self._debug('Generated setup.py file contents...', setup_py=setup_py)

        commit_message = BUMP_COMMIT_MESSAGE_FORMAT.format(next_version, sha)

        if dry:
            return setup_py

        if current_version != next_version:
            self._debug('Committing setup.py file...', commit_message=commit_message,
                        file_contenst=setup_py)
            return self.commit_file(path='setup.py',
                                    contents=setup_py,
                                    message=commit_message)
        self._debug('Not performing commit because the current version is equal to the next '
                    'version.', current_version=current_version, next_version=next_version)
        return None

    def _get_or_create_commit(self, sha):
        if sha not in self.__commits:
            self.__commits[sha] = _GitHubCommit(branch=self, sha=sha)
        return self.__commits[sha]

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)


class _GitHubCommit(object):

    def __init__(self, branch, sha):
        self._branch = branch
        self._sha = sha
        self._runner = LocalCommandRunner()
        self._log_ctx = {
            'repo': self._branch.github.repo.full_name,
            'branch': self._branch.branch_name,
            'sha': self._sha
        }

    @cachedproperty
    def commit(self):
        try:
            self._debug('Fetching commit...')
            commit = self._branch.github.repo.get_commit(sha=self._sha)
            self._debug('Fetched commit.', commit=commit.url)
            return commit
        except UnknownObjectException:
            raise exceptions.CommitNotFoundException(sha=self._sha)

    @cachedproperty
    def pr(self):
        self._debug('Fetching pull request from commit...', commit=self.commit.url)
        pr_number = utils.extract_link(self.commit.commit.message)
        pr = self._branch.github.repo.get_pull(number=pr_number) if pr_number else None
        self._debug('Fetched pull request.', pr=pr.url if pr else None)
        return pr

    @cachedproperty
    def issue(self):
        self._debug('Fetching issue...', commit=self.commit.url)
        issue = self._branch.github.detect_issue(commit_message=self.commit.commit.message)
        if issue:
            issue = issue.impl
        self._debug('Fetched issue.', issue=issue.url if issue else None)
        return issue

    @cachedproperty
    def labels(self):
        self._debug('Fetching issue labels...', issue=self.issue.url)
        labels = [label.name for label in self.issue.get_labels()]
        self._debug('Fetched labels.', issue=self.issue.url,
                    labels=','.join([label for label in labels]))
        return labels

    @cachedproperty
    def setup_py_path(self):
        setup_py_url = 'https://raw.githubusercontent.com/{}/{}/setup.py'.format(
            self._branch.github.repo.full_name, self.commit.sha)
        self._debug('Fetching setup.py...', setup_py_url=setup_py_url)
        setup_py_path = download(url=setup_py_url)
        self._debug('Fetched setup.py.', setup_py_url=setup_py_url, setup_py_path=setup_py_path)
        return setup_py_path

    @cachedproperty
    def setup_py(self):
        with open(self.setup_py_path) as stream:
            return stream.read()

    @cachedproperty
    def setup_py_version(self):
        self._debug('Extracting current setup.py version...')
        setup_py_version = self._runner.run('python {0} --version'
                                            .format(self.setup_py_path)).std_out
        self._debug('Extracted current setup.py version...', setup_py_version=setup_py_version)
        return setup_py_version

    def validate_commit(self):

        if self.issue is None:
            raise exceptions.CommitNotRelatedToIssueException(sha=self.commit.sha)

        if not any(label in self.labels for label in ['patch', 'minor', 'major']):
            raise exceptions.IssueIsNotLabeledAsReleaseException(issue=self.issue.number,
                                                                 sha=self.commit.sha)

    def create_release(self, version):

        changelog = self.generate_changelog()

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

        version = version or changelog.next_version
        if not version:
            raise exceptions.CannotDetermineNextVersionException(sha=self.commit.sha)

        self._debug('Validating next version number...', next_version=version)
        self._validate_version(version)
        self._debug('Validated next version number.', next_version=version)

        self._debug('Creating Github Release...', version=version)
        release = self._create_release(name=version, changelog=changelog)
        self._debug('Successfully created release.', version=version)

        for issue in changelog.all_issues:
            self._branch.github.close_issue(issue.impl, release)

        if self.pr:
            try:
                self._debug('Fetching pull request branch...', pr_branch=self.pr.head.ref)
                pull_request_ref = self._branch.github.repo.get_git_ref(
                    'heads/{0}'.format(self.pr.head.ref))
                self._debug('Deleting ref', ref=pull_request_ref.ref)
                pull_request_ref.delete()
                self._debug('Deleted ref', ref=pull_request_ref.ref)
            except UnknownObjectException:
                self._debug('Pull request branch does not exist...', branch=self.pr.head.ref)
                # this is ok, the branch doesn't necessarily have to be there.
                # it might have been deleted when the pull request was merged

        return Release(title=version, changelog=changelog)

    def generate_changelog(self):

        since = GithubObject.NotSet
        last_release_sha = None
        last_release_title = None
        if self._branch.github.last_release:

            last_release_title = self._branch.github.last_release.title
            last_release_commit = self._fetch_tag_commit(tag_name=last_release_title)
            since = last_release_commit.commit.committer.date
            last_release_sha = last_release_commit.sha

        self._debug('Fetching commits...', since=since, last_release=last_release_title)
        commits = list(self._branch.github.repo.get_commits(sha=self.commit.sha, since=since))
        self._debug('Fetched commits.', since=since, last_release=last_release_title,
                    number_of_commits=len(commits))

        changelog = Changelog(current_version=self.setup_py_version, sha=self.commit.sha)

        for commit in commits:

            if commit.sha == last_release_sha:
                continue

            issue = self._branch.github.detect_issue(commit_message=commit.commit.message)

            if issue is None:
                self._debug('Commit is not related to an issue.', commit=commit.sha)
                self._debug('Found dangling commit.', sha=commit.sha,
                            commit_message=commit.commit.message)
                change = ChangelogCommit(title=commit.commit.message,
                                         url=commit.html_url,
                                         timestamp=commit.commit.author.date,
                                         impl=commit)
            else:

                issue = issue.impl
                self._debug('Fetching labels...', issue=issue.number)
                labels = [label.name for label in list(issue.get_labels())]
                self._debug('Fetched labels.', issue=issue.number, labels=','.join(labels))

                version_modifier = None

                if 'patch' in labels:
                    version_modifier = ChangelogIssue.PATCH
                if 'minor' in labels:
                    version_modifier = ChangelogIssue.MINOR
                if 'major' in labels:
                    version_modifier = ChangelogIssue.MAJOR

                if 'feature' in labels:
                    self._debug('Found feature.', issue=issue.number)
                    kind_modifier = ChangelogIssue.FEATURE
                elif 'bug' in labels:
                    self._debug('Found bug', issue=issue.number)
                    kind_modifier = ChangelogIssue.BUG
                else:
                    self._debug('Found issue', issue=issue.number)
                    kind_modifier = ChangelogIssue.ISSUE

                change = ChangelogIssue(impl=issue,
                                        title=issue.title,
                                        url=issue.html_url,
                                        timestamp=issue.created_at,
                                        kind_modifier=kind_modifier,
                                        version_modifier=version_modifier)

            changelog.add(change)

        return changelog

    def _create_release(self, name, changelog):
        try:
            release = self._branch.github.repo.create_git_release(
                tag=name,
                target_commitish=self.commit.sha,
                name=name,
                message=changelog.render(),
                draft=False,
                prerelease=False
            )
        except GithubException as e:

            if e.data['errors'][0]['code'] != 'already_exists':
                raise

            release = self._branch.github.repo.get_release(id=name)
            release_commit = self._fetch_tag_commit(release.tag_name)

            if release_commit.sha == self.commit.sha:
                # there might be concurrent executions running on the
                # same commit (two different CI systems for example)
                raise exceptions.CommitIsAlreadyReleasedException(sha=self.commit.sha,
                                                                  release=name)

            bump_version_message = BUMP_COMMIT_MESSAGE_FORMAT.format(name, self.commit.sha)
            if release_commit.commit.message == bump_version_message:
                # this means the commits of the release is actually just a bump version commit
                # the followed our commit. we consider this as being the same commit as ours.

                # pylint: disable=fixme
                # TODO maybe this should be a specific exception type?
                raise exceptions.CommitIsAlreadyReleasedException(sha=self.commit.sha,
                                                                  release=name)

            # if we get here, its bad. the release already exists but with a different commit than
            # ours? it probably means there are two concurrent release jobs on the same
            # branch...

            # pylint: disable=fixme
            # TODO what should we do here? what are the implications of this?
            raise exceptions.ReleaseConflictException(release=name,
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

    def _fetch_tag_commit(self, tag_name):
        tag = self._branch.github.repo.get_git_ref(ref='tags/{0}'.format(tag_name))
        return self._branch.github.repo.get_commit(sha=tag.object.sha)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)
