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
# noinspection PyPackageRequirements
from github import InputGitTreeElement
# noinspection PyPackageRequirements
from github.GithubException import GithubException
# noinspection PyPackageRequirements
from github.GithubException import UnknownObjectException

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api.model import Branch, Bump, Commit, Issue, Release, Changelog, ChangelogIssue, \
    ChangelogCommit
from pyci.api.runner import LocalCommandRunner
from pyci.api.utils import download

log = logger.get_logger(__name__)


SET_VERSION_COMMIT_MESSAGE_FORMAT = 'Set version to {}'


class GitHubRepository(object):

    """
    Provides Github capabilities.

    Each instance of this class is associated with a certain repository.

    Args:
        repo (str): The repository full name. (e.g iliapolo/pyci)
        access_token (str): The access token for using Github Rest API.
    """

    def __init__(self, repo, access_token):

        if not repo:
            raise exceptions.InvalidArgumentsException('repo cannot be empty')

        if not access_token:
            raise exceptions.InvalidArgumentsException('access_token cannot be empty')

        self.__branches = {}
        self._access_token = access_token
        self._repo_name = repo
        self._log_ctx = {
            'repo': self._repo_name,
        }

    @staticmethod
    def create(repo, access_token):
        return GitHubRepository(repo=repo, access_token=access_token)

    @cachedproperty
    def _hub(self):
        return Github(self._access_token)

    @cachedproperty
    def repo(self):
        try:
            self._debug('Fetching repo...')
            repo = self._hub.get_repo(self._repo_name)
            self._debug('Fetched repo.', url=repo.html_url)
            return repo
        except UnknownObjectException:
            raise exceptions.RepositoryNotFoundException(repo=self._repo_name)

    @cachedproperty
    def default_branch_name(self):
        self._debug('Fetching default branch...')
        name = self.repo.default_branch
        self._debug('Fetched default branch.', name=name)
        return name

    def validate_commit(self, branch=None, sha=None):

        """
        Validate a commit should be be released. Valid commits are one's who are attached to an
        issue that has at least one of the release labels. i.e, such an issue that will cause a
        version bump.

        Args:
            branch (:str, optional): To validate the last commit of this branch.
            sha (:str, optional): To validate a specific commit.

        Raises:
            exceptions.CommitNotRelatedToIssueException: Raised when the commit is not related to
                any issue.
            exceptions.IssueIsNotLabeledAsReleaseException: Raised when the issue does not have any
                release labels.

        """

        if branch and sha:
            raise exceptions.InvalidArgumentsException('either branch or sha is allowed')

        if not branch and not sha:
            raise exceptions.InvalidArgumentsException('either branch or sha is required')

        branch = branch or self.default_branch_name
        self._get_or_create_branch(branch).validate_commit(sha=sha)

    def generate_changelog(self, branch=None, sha=None):

        """
        Generate a changelog for the given commit.

        The generated changelog is always with respect to the latest release of the repository.

        Args:
            branch (:str, optional): For the last commit of this branch.
            sha (:str, optional): For a specific commit.

        Returns:
            pyci.api.model.Changelog: A changelog instance.
        """

        if branch and sha:
            raise exceptions.InvalidArgumentsException('either branch or sha is allowed')

        if not branch and not sha:
            raise exceptions.InvalidArgumentsException('either branch or sha is required')

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).generate_changelog(sha=sha)

    def create_release(self, branch=None, sha=None):

        """
        Create a release pointing to the specific commit. The release title will be the setup.py
        version as it was in the commit.

        Args:
            branch (:str, optional): From the last commit of this branch.
            sha (:str, optional): From this specific commit.

        Returns:
            pyci.api.model.Release: A release object containing information about the
                release.

        Raises:
            exceptions.CommitIsAlreadyReleasedException: Raised when the specified commit is
                already released under the relevant release.
            exceptions.ReleaseConflictException: Raised when a release with the relevant title
                already exists, but it points to a different commit than ours.
            exceptions.NotPythonProjectException: Raised when attempting to release a project
                that does not conform to python standard packaging.

        """

        if branch and sha:
            raise exceptions.InvalidArgumentsException('either branch or sha is allowed')

        if not branch and not sha:
            raise exceptions.InvalidArgumentsException('either branch or sha is required')

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).create_release(sha=sha)

    def upload_asset(self, asset, release):

        """
        Upload an asset to an existing Github release.

        Args:
            asset (str): Path to the asset file.
            release (str): The release name.

        Returns:
            str: The uploaded asset URL.

        Raises:
            AssetAlreadyPublishedException: Raised when the given asset already exists in the
                release. This is determined by the basename of the asset file path.

        """

        if not asset:
            raise exceptions.InvalidArgumentsException('asset cannot be empty')

        if not release:
            raise exceptions.InvalidArgumentsException('release cannot be empty')

        asset = os.path.abspath(asset)

        utils.validate_file_exists(asset)

        try:
            self._debug('Fetching release...', name=release)
            git_release = self.repo.get_release(id=release)
            self._debug('Fetched release.', url=git_release.html_url)
        except UnknownObjectException:
            raise exceptions.ReleaseNotFoundException(release=release)

        try:
            self._debug('Uploading asset...', asset=asset, release=release)
            git_release.upload_asset(path=asset, content_type='application/octet-stream')
            asset_url = 'https://github.com/{0}/releases/download/{1}/{2}'.format(
                self._repo_name, git_release.title, os.path.basename(asset))
            self._debug('Uploaded asset.', url=asset_url, release=release)

            # because of this bug i currently have to use my own version of PyGithub :\
            # see https://github.com/PyGithub/PyGithub/issues/779

            return asset_url
        except GithubException as e:

            if e.data['errors'][0]['code'] == 'already_exists':
                asset_name = os.path.basename(asset)
                raise exceptions.AssetAlreadyPublishedException(asset=asset_name,
                                                                release=git_release.title)

            # cannot test the unexpected, unfortunately...
            raise  # pragma: no cover

    def upload_changelog(self, changelog, release):

        """
        Upload a changelog to the release.

        Note this will override the existing (if any) changelog.

        Args:
            changelog (str): The changelog string.
            release (str): The release name.
        """

        if not changelog:
            raise exceptions.InvalidArgumentsException('changelog cannot be empty')

        if not release:
            raise exceptions.InvalidArgumentsException('release cannot be empty')

        try:
            self._debug('Fetching release...', name=release)
            git_release = self.repo.get_release(id=release)
            self._debug('Fetched release.', url=git_release.html_url)
        except UnknownObjectException:
            raise exceptions.ReleaseNotFoundException(release=release)

        log.debug('Updating release with changelog...', release=release, changelog=changelog)
        git_release.update_release(name=git_release.title, message=changelog)
        log.debug('Successfully updated release with changelog', release=release,
                  changelog=changelog)

        release_sha = self.repo.get_git_ref(ref='tags/{}'.format(git_release.tag_name)).object.sha
        return Release(impl=git_release,
                       title=git_release.title,
                       url=git_release.html_url,
                       sha=release_sha)

    def detect_issue(self, sha=None, commit_message=None):

        """
        Detect which issue a commit is related to. This is done by looking up the number
        following the '#' sign in the commit message. If this number corresponds to an issue,
        we are done. If not, check if it corresponds to a pull request, if so, detect the issue
        number from the pull request body.

        Args:
            sha (:str, optional): Using the commit sha.
            commit_message (:str, optional): Using the commit message.

        Return:
            pyci.api.model.Issue: The issue, if found.
            None: If the commit does not contain a link to an issue number.
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

                sue = Issue(impl=issue, number=issue.number, url=issue.html_url)

                self._debug('Detected issue.', sha=sha, commit_message=commit_message,
                            issue=sue.url)
                return sue
            except UnknownObjectException:
                # this is unexpected, it means the reference in either the pull
                # request or the commit points to a non existing issue!
                raise exceptions.IssueNotFoundException(commit_message=commit_message,
                                                        pr_number=pr_number,
                                                        issue_number=issue_number)

        self._debug('No link found in commit message', sha=sha, commit_message=commit_message)
        return None

    def delete_release(self, name):

        """
        Delete a release. Note that this does not delete the tag associated with this release.
        To delete the tag, use the 'delete_tag' method.

        Args:
            name (str): The release name.

        Raises:
            ReleaseNotFoundException: Raised when the given release is not found.
        """

        if not name:
            raise exceptions.InvalidArgumentsException('name cannot be empty')

        try:

            self._debug('Fetching release...', name=name)
            rel = self.repo.get_release(id=name)
            self._debug('Fetched release.', name=rel.title)

            self._debug('Deleting release...', name=rel.title)
            rel.delete_release()
            self._debug('Deleted release.', name=rel.title)

        except UnknownObjectException:
            raise exceptions.ReleaseNotFoundException(release=name)

    def delete_tag(self, name):

        """
        Delete a tag.

        Args:
            name (str): The tag name.

        Raises:
            TagNotFoundException: Raised when the given tag is not found.
        """

        if not name:
            raise exceptions.InvalidArgumentsException('name cannot be empty')

        try:
            self._debug('Fetching tag...', name=name)
            tag = self.repo.get_git_ref('tags/{0}'.format(name))
            self._debug('Fetched tag.', ref=tag.ref)

            self._debug('Deleting tag...', ref=tag.ref)
            tag.delete()
            self._debug('Deleted tag.', ref=tag.ref)

        except UnknownObjectException:
            raise exceptions.TagNotFoundException(tag=name)

    def bump_version(self, semantic, branch=None):

        """
        Bump the version of setup.py according the semantic specification.
        The base version is retrieved from the current setup.py file of the branch.
        Note, This will actually create a commit on top of the branch you specify.

        Args:
            semantic (:str, optional): A semantic version modifier (e.g minor, major..).
            branch (:str, optional): The branch name to perform to commit on. Defaults to
                the default branch of the repository.

        Returns:
            pyci.api.model.Commit: The commit that was created.
        """

        if not semantic:
            raise exceptions.InvalidArgumentsException('semantic cannot be empty')

        if semantic not in ['patch', 'minor', 'major']:
            raise exceptions.InvalidArgumentsException('semantic must be one of: [patch, minor, '
                                                       'major]')

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).bump_version(semantic=semantic)

    def set_version(self, value, branch=None):

        """
        Sets the version of setup.py file to the specified version number.
        Note, This will actually create a commit on top of the branch you specify.

        Args:
            value (str): The semantic version string.
            branch (:str, optional): The branch name to perform to commit on. Defaults to
                the default branch of the repository.

        Returns:
            pyci.api.model.Bump: The commit that was created.
        """

        if not value:
            raise exceptions.InvalidArgumentsException('value cannot be empty')

        try:
            semver.parse(value)
        except (TypeError, ValueError):
            raise exceptions.InvalidArgumentsException('value is not a legal semantic version')

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).set_version(value=value, reset=True)

    def reset_branch(self, name, sha):

        """
        Reset the branch to the sha. This is equivalent to 'git reset --hard'.

        Args:
            name (str): The branch name.
            sha (str): The sha to reset to.
        """

        if not name:
            raise exceptions.InvalidArgumentsException('name cannot be empty')

        if not sha:
            raise exceptions.InvalidArgumentsException('sha cannot be empty')

        try:
            self._debug('Fetching branch ref...', branch=name)
            ref = self.repo.get_git_ref('heads/{0}'.format(name))
            self._debug('Fetched branch ref', ref=ref.ref)
        except UnknownObjectException:
            raise exceptions.BranchNotFoundException(branch=name, repo=self._repo_name)

        try:
            self._debug('Resetting branch with sha', branch=name, sha=sha)
            ref.edit(sha=sha, force=True)
            self._debug('Reset branch with sha', branch=name, sha=sha)
        except GithubException as e:
            if e.data['message'] == 'Object does not exist':
                raise exceptions.ShaNotFoundException(sha=sha, repo=self._repo_name)
            raise  # pragma: no cover

    def reset_tag(self, name, sha):

        """
        Reset the tag to the sha. This is equivalent to 'git reset --hard'.

        Args:
            name (str): The tag name.
            sha (str): The sha to reset to.
        """

        if not name:
            raise exceptions.InvalidArgumentsException('name cannot be empty')

        if not sha:
            raise exceptions.InvalidArgumentsException('sha cannot be empty')

        try:
            self._debug('Fetching tag ref...', tag=name)
            ref = self.repo.get_git_ref('tags/{0}'.format(name))
            self._debug('Fetched tag ref', ref=ref.ref)
        except UnknownObjectException:
            raise exceptions.TagNotFoundException(tag=name)

        try:
            self._debug('Resetting branch with sha', tag=name, sha=sha)
            ref.edit(sha=sha, force=True)
            self._debug('Reset branch with sha', tag=name, sha=sha)
        except GithubException as e:
            if e.data['message'] == 'Object does not exist':
                raise exceptions.ShaNotFoundException(sha=sha, repo=self._repo_name)
            raise  # pragma: no cover

    def create_branch(self, name, sha):

        """
        Create a branch.

        Args:
            name (str): The branch name.
            sha (str): The sha to create the branch from.

        Raises:
            exceptions.ShaNotFoundException: Raised if the given sha does not exist.
            exceptions.BranchAlreadyExistsException: Raised if the given branch name already exists.
        """

        if not name:
            raise exceptions.InvalidArgumentsException('name cannot be empty')

        if not sha:
            raise exceptions.InvalidArgumentsException('sha cannot be empty')

        try:

            self._debug('Creating branch...', name=name, sha=sha)
            ref = self.repo.create_git_ref(ref='refs/heads/{}'.format(name), sha=sha)
            self._debug('Created branch...', name=name, sha=sha)

            return Branch(impl=ref, sha=ref.object.sha, name=name)

        except GithubException as e:
            if e.data['message'] == 'Object does not exist':
                raise exceptions.ShaNotFoundException(sha=sha, repo=self._repo_name)
            if e.data['message'] == 'Reference already exists':
                raise exceptions.BranchAlreadyExistsException(repo=self._repo_name, branch=name)
            raise  # pragma: no cover

    def delete_branch(self, name):

        """
        Delete a branch.

        Args:
            name (str): The branch name.

        Raises: exceptions.BranchNotFoundException: Raised when the branch with the given name
            does not exist.
        """

        if not name:
            raise exceptions.InvalidArgumentsException('name cannot be empty')

        try:

            self._debug('Fetching branch...', name=name)
            ref = self.repo.get_git_ref(ref='heads/{}'.format(name))
            self._debug('Fetched branch...', name=name)

            self._debug('Deleting reference...', ref=ref.ref)
            ref.delete()
            self._debug('Deleted reference.', ref=ref.ref)

        except UnknownObjectException:
            raise exceptions.BranchNotFoundException(branch=name, repo=self._repo_name)

    def commit_file(self, path, contents, message, branch=None):

        """
        Commit a file to the repository.

        Args:
            path (str): Path to the file, relative to the repository root.
            contents (str): The new contents of the file.
            message (str): The commit message.
            branch (str, optional): The branch to commit to. Defaults to the repository default
                branch.
        """

        if not path:
            raise exceptions.InvalidArgumentsException('path cannot be empty')

        if not contents:
            raise exceptions.InvalidArgumentsException('contents cannot be empty')

        if not message:
            raise exceptions.InvalidArgumentsException('message cannot be empty')

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).commit_file(path=path,
                                                              contents=contents,
                                                              message=message)

    def create_commit(self, path, contents, message, branch=None):

        """
        Create a commit in the repository.

        Note, this method does not actually update any reference to point to this commit.
        The created commit will be floating until you reset some reference to it.

        This is advanced API, only use it if you really know what you are doing.

        Args:
            path (str): Path to the file, relative to the repository root.
            contents (str): The new contents of the file.
            message (str): The commit message.
            branch (str, optional): The last commit of the branch will be the parent of the
                created commit. Defaults to the repository default branch.
        """

        if not path:
            raise exceptions.InvalidArgumentsException('path cannot be empty')

        if not contents:
            raise exceptions.InvalidArgumentsException('contents cannot be empty')

        if not message:
            raise exceptions.InvalidArgumentsException('message cannot be empty')

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).create_commit(path=path,
                                                                contents=contents,
                                                                message=message)

    def _close_issue(self, issue, release):

        self._debug('Closing issue...', issue=issue.number)
        issue.edit(state='closed')
        self._debug('Closed issue.', issue=issue.number)

        issue_comments = [comment.body for comment in issue.get_comments()]

        issue_comment = 'This issue is part of release [{}]({})'.format(
            release.title, release.html_url)

        if issue_comment not in issue_comments:
            self._debug('Adding a comment to issue...', issue=issue.number)
            issue.create_comment(body=issue_comment)
            self._debug('Added comment.', issue=issue.number, comment=issue_comment)

    def _create_set_version_commit(self, value, branch=None):

        """
        Internal! Do not use

        """

        branch = branch or self.default_branch_name
        return self._get_or_create_branch(branch).set_version(value=value, reset=False)

    def _get_or_create_branch(self, branch):
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
        self._get_or_create_commit(sha=sha).validate_commit()

    def generate_changelog(self, sha):
        sha = sha or self.branch_name
        return self._get_or_create_commit(sha=sha).generate_changelog()

    def create_release(self, sha):
        sha = sha or self.branch_name
        return self._get_or_create_commit(sha=sha).create_release()

    def commit_file(self, path, contents, message):

        commit = self.create_commit(path, contents, message)

        self._debug('Updating branch to point to commit...', branch=self.branch_name,
                    sha=commit.sha)
        ref = self.github.repo.get_git_ref(ref='heads/{0}'.format(self.branch_name))
        ref.edit(sha=commit.sha)
        self._debug('Updated branch to point to commit', branch=self.branch_name,
                    sha=ref.object.sha)

        return commit

    def create_commit(self, path, contents, message):

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

        return Commit(impl=commit, sha=commit.sha, url=commit.html_url)

    def bump_version(self, semantic):

        commit = self._get_or_create_commit(sha=self.branch_name)

        current_version = commit.setup_py_version

        def _bump_current_version():

            result = current_version

            if semantic == ChangelogIssue.PATCH:
                result = semver.bump_patch(result)
            if semantic == ChangelogIssue.MINOR:
                result = semver.bump_minor(result)
            if semantic == ChangelogIssue.MAJOR:
                result = semver.bump_major(result)

            return result

        self._debug('Determining next version', current_version=current_version)
        next_version = _bump_current_version()
        self._debug('Determined next version', current_version=current_version,
                    next_version=next_version)

        return self.set_version(value=next_version)

    def set_version(self, value, reset=True):

        commit = self._get_or_create_commit(sha=self.branch_name)

        current_version = commit.setup_py_version
        setup_py = commit.setup_py

        self._debug('Generating setup.py file contents...', setup_py=setup_py,
                    next_version=value)
        setup_py = utils.generate_setup_py(setup_py, value)
        self._debug('Generated setup.py file contents...', setup_py=setup_py)

        commit_message = SET_VERSION_COMMIT_MESSAGE_FORMAT.format(value)

        if current_version != value:
            if reset:
                bump_commit = self.commit_file(path='setup.py', contents=setup_py,
                                               message=commit_message)
            else:
                bump_commit = self.create_commit(path='setup.py', contents=setup_py,
                                                 message=commit_message)
            return Bump(impl=bump_commit.impl, prev_version=current_version, next_version=value,
                        sha=bump_commit.sha)

        raise exceptions.TargetVersionEqualsCurrentVersionException(version=current_version)

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
            self._debug('Fetched commit.', commit=commit.html_url)
            return commit
        except UnknownObjectException:
            raise exceptions.CommitNotFoundException(sha=self._sha)

    @cachedproperty
    def issue(self):
        issue = self._branch.github.detect_issue(commit_message=self.commit.commit.message)
        if issue:
            issue = issue.impl
        return issue

    @cachedproperty
    def labels(self):
        self._debug('Fetching issue labels...', issue=self.issue.html_url)
        labels = [label.name for label in self.issue.get_labels()]
        self._debug('Fetched labels.', issue=self.issue.html_url,
                    labels=','.join([label for label in labels]))
        return labels

    @cachedproperty
    def setup_py_path(self):
        setup_py_url = 'https://raw.githubusercontent.com/{}/{}/setup.py'.format(
            self._branch.github.repo.full_name, self.commit.sha)
        self._debug('Fetching setup.py...', setup_py_url=setup_py_url)
        try:
            setup_py_path = download(url=setup_py_url)
        except exceptions.DownloadFailedException as e:
            if e.code == 404:
                raise exceptions.NotPythonProjectException(repo=self._branch.github.repo.full_name,
                                                           cause='setup.py not found',
                                                           sha=self.commit.sha)
            raise  # pragma: no cover
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

        self._debug('Validating commit should be released...')

        if self.issue is None:
            raise exceptions.CommitNotRelatedToIssueException(sha=self.commit.sha)

        if not any(label in self.labels for label in ['patch', 'minor', 'major']):
            raise exceptions.IssueNotLabeledAsReleaseException(issue=self.issue.number,
                                                               sha=self.commit.sha)

        self._debug('Validation passed. Commit should be released')

    def create_release(self):

        version = self.setup_py_version

        try:

            self._debug('Creating Github release...', name=version, sha=self.commit.sha,
                        tag=version)
            github_release = self._branch.github.repo.create_git_release(
                tag=version,
                target_commitish=self.commit.sha,
                name=version,
                message='',
                draft=False,
                prerelease=False
            )
            self._debug('Created Github release...', name=version, sha=self.commit.sha,
                        tag=version)

            return Release(impl=github_release, title=version, url=github_release.html_url,
                           sha=self.commit.sha)

        except GithubException as e:

            if e.data['errors'][0]['code'] != 'already_exists':
                raise  # pragma: no cover

            release = self._branch.github.repo.get_release(id=version)
            release_commit = self._fetch_tag_commit(release.tag_name)

            if release_commit.sha == self.commit.sha:
                # this can only happen with concurrent executions on the same commit.
                # otherwise, the commit changelog would have been empty and we wouldn't get
                # here.
                raise exceptions.CommitIsAlreadyReleasedException(sha=self.commit.sha,
                                                                  release=version)

            raise exceptions.ReleaseConflictException(release=version,
                                                      our_sha=self.commit.sha,
                                                      their_sha=release_commit.sha)

    # pylint: disable=too-many-branches
    def generate_changelog(self):

        self._debug('Generating changelog...')

        releases = {}

        for release in self._branch.github.repo.get_releases():
            commit = self._fetch_tag_commit(release.tag_name)
            if commit.commit.author.date <= self.commit.commit.author.date:
                releases[commit.sha] = {
                    'date': commit.commit.author.date,
                    'name': release.title,
                    'sha': commit.sha
                }

        self._debug('Fetching commits...')
        all_commits = self._branch.github.repo.get_commits(sha=self.commit.sha)

        commits = []
        previous_release = {}

        # this relies on the fact github returns a descending order list.
        # will this always be the case? couldn't find any docs about it...
        # i really don't want to sort it myself because it might mean fetching a lot of commits,
        # which takes time...
        for commit in all_commits:
            if commit.sha not in releases.keys():
                commits.append(commit)
            else:
                previous_release = releases[commit.sha]
                break

        if not commits:
            raise exceptions.EmptyChangelogException(sha=self.commit.sha,
                                                     previous_release=previous_release['name'])

        self._debug('Fetched commits.', previous_release=previous_release.get('name'),
                    commits=','''.join([commit.sha for commit in commits]))

        changelog = Changelog(current_version=self.setup_py_version, sha=self.commit.sha)

        for commit in commits:

            issue = self._branch.github.detect_issue(commit_message=commit.commit.message)

            if issue is None:
                self._debug('Found commit.', sha=commit.sha, commit_message=commit.commit.message)
                change = ChangelogCommit(title=commit.commit.message,
                                         url=commit.html_url,
                                         timestamp=commit.commit.author.date,
                                         impl=commit)
            else:

                issue = issue.impl
                self._debug('Fetching labels...', issue=issue.number)
                labels = [label.name for label in list(issue.get_labels())]
                self._debug('Fetched labels.', issue=issue.number, labels=','.join(labels))

                semantic = None

                if 'patch' in labels:
                    semantic = ChangelogIssue.PATCH
                elif 'minor' in labels:
                    semantic = ChangelogIssue.MINOR
                elif 'major' in labels:
                    semantic = ChangelogIssue.MAJOR

                if 'feature' in labels:
                    self._debug('Found feature.', issue=issue.number)
                    kind = ChangelogIssue.FEATURE
                elif 'bug' in labels:
                    self._debug('Found bug.', issue=issue.number)
                    kind = ChangelogIssue.BUG
                else:
                    self._debug('Found issue.', issue=issue.number)
                    kind = ChangelogIssue.ISSUE

                change = ChangelogIssue(impl=issue,
                                        title=issue.title,
                                        url=issue.html_url,
                                        timestamp=issue.created_at,
                                        kind=kind,
                                        semantic=semantic)

            self._debug('Adding change to changelog.', change=change.url)
            changelog.add(change)

        self._debug('Generated changelog.', changelog=changelog.render())

        return changelog

    def _fetch_tag_commit(self, tag_name):
        tag = self._branch.github.repo.get_git_ref(ref='tags/{0}'.format(tag_name))
        return self._branch.github.repo.get_commit(sha=tag.object.sha)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)
