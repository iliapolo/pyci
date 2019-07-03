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
import tempfile

import semver
from boltons.cacheutils import cachedproperty
from github import Github
from github import InputGitTreeElement
from github.GithubException import UnknownObjectException
from github.GithubException import GithubException

from pyci.api.model import ChangelogIssue
from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api import model
from pyci.api.runner import LocalCommandRunner


BUMP_VERSION_COMMIT_MESSAGE_FORMAT = 'Bump version to {}'


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

        self.__commits = {}
        self._logger = logger.Logger(__name__)
        self._hub = Github(access_token, timeout=30)
        self._repo_name = repo
        self._log_ctx = {
            'repo': self._repo_name,
        }

    @staticmethod
    def create(repo, access_token):
        return GitHubRepository(repo=repo, access_token=access_token)

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

    def validate_commit(self, sha=None, hooks=None):

        """
        Validate a commit should be be released. Valid commits are one's who are attached to an
        issue that has at least one of the release labels. i.e, such an issue that will cause a
        version bump.

        Args:
            hooks: dictionary of callable hooks to execute in various steps of this method.
            sha (:str, optional): To validate a specific commit.

        Raises:
            exceptions.CommitNotRelatedToIssueException: Raised when the commit is not related to any issue.
            exceptions.IssueIsNotLabeledAsReleaseException: Raised when the issue does not have any release labels.

        """

        sha = sha or self.default_branch_name
        self._get_or_create_commit(sha).validate(hooks=hooks)

    def generate_changelog(self, sha=None, base=None, hooks=None):

        """
        Generate a changelog for the given commit.

        The generated changelog is always with respect to the latest release of the repository.

        Args:
            hooks: dictionary of callable hooks to execute in various steps of this method.
            sha (:str, optional): For a specific commit.
            base: (:str, optional): Base sha to start from (exclusive). Can also be a branch name.
                Defaults to the last release prior to sha/branch.

        Returns:
            pyci.api.model.Changelog: A changelog instance.
        """

        sha = sha or self.default_branch_name
        return self._get_or_create_commit(sha).generate_changelog(base=base, hooks=hooks)

    def create_release(self, sha=None):

        """
        Create a release pointing to the specific commit. The release title will be the setup.py
        version as it was in the commit.

        Args:
            sha (:str, optional): From this specific commit.

        Returns:
            pyci.api.model.Release: A release object containing information about the
                release.

        Raises:
            exceptions.ReleaseAlreadyExistException: Raised when the release already exists.
            exceptions.NotPythonProjectException: Raised a project does not conform to python standard packaging.

        """

        sha = sha or self.default_branch_name
        return self._get_or_create_commit(sha).create_release()

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

        self._logger.debug('Updating release with changelog...', release=release)
        git_release.update_release(name=git_release.title, message=changelog)
        self._logger.debug('Successfully updated release with changelog', release=release)

        release_sha = self.repo.get_git_ref(ref='tags/{}'.format(git_release.tag_name)).object.sha
        return model.Release(impl=git_release,
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
            try:
                commit_message = self.repo.get_commit(sha=sha).commit.message
            except GithubException as e:
                if isinstance(e, UnknownObjectException) or 'No commit found for SHA' in str(e):
                    raise exceptions.CommitNotFoundException(sha=sha)

            self._debug('Fetched commit message...', sha=sha, commit_message=commit_message)

        self._debug('Extracting link...', sha=sha, commit_message=commit_message)
        ref = utils.extract_link(commit_message)
        self._debug('Extracted link.', sha=sha, commit_message=commit_message, link=ref)

        issue_number = None

        if ref:
            try:

                self._debug('Fetching pull request...', sha=sha, commit_message=commit_message,
                            ref=ref)
                pull = self.repo.get_pull(number=ref)
                self._debug('Fetched pull request.', sha=sha, commit_message=commit_message,
                            ref=ref, pull_request=pull.url)

                self._debug('Extracting issue number from pull request body...', sha=sha,
                            commit_message=commit_message, ref=ref, pull_request_body=pull.body)
                issue_number = utils.extract_link(pull.body)
                self._debug('Extracted issue number from pull request body', sha=sha,
                            commit_message=commit_message, ref=ref, pull_request_body=pull.body,
                            issue_number=issue_number)

            except UnknownObjectException:
                self._debug('Link is not a pull request.', sha=sha, commit_message=commit_message,
                            ref=ref)
                issue_number = ref

        if issue_number:
            try:
                self._debug('Fetching issue...', sha=sha, commit_message=commit_message,
                            issue_number=issue_number)
                issue = self.repo.get_issue(number=issue_number)
                self._debug('Fetched issue.', sha=sha, commit_message=commit_message,
                            issue_url=issue.url)

                sue = model.Issue(impl=issue, number=issue.number, url=issue.html_url)

                self._debug('Detected issue.', sha=sha, commit_message=commit_message,
                            issue=sue.url)
                return sue
            except UnknownObjectException:
                # this is unexpected, it means the reference is either the pull
                # request or the commit points to a non existing issue!
                raise exceptions.IssueNotFoundException(issue=issue_number)

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
        Bump the version of setup.py according to the semantic specification.
        The base version is retrieved from the current setup.py file of the branch.
        Note, This will actually create a commit on top of the branch you specify.

        Args:
            semantic (:str, optional): A semantic version modifier (e.g minor, major..).
            branch (:str, optional): The branch to push to commit to. Defaults to the default repository branch.

        Returns:
            pyci.api.model.Commit: The commit that was created.

        Raises:
            pyci.api.exceptions.TargetVersionEqualsCurrentVersionException:
                Current version in setup.py is equal to the calculated version number.
        """

        if not semantic:
            raise exceptions.InvalidArgumentsException('semantic cannot be empty')

        if semantic not in ChangelogIssue.SEMANTIC_VERSION_LABELS:
            raise exceptions.InvalidArgumentsException('semantic must be one of: {}'
                                                       .format(ChangelogIssue.SEMANTIC_VERSION_LABELS))

        branch = branch or self.default_branch_name

        last_branch_commit = self._get_or_create_commit(sha=branch)

        current_version = last_branch_commit.setup_py_version

        bumps = {
            model.ChangelogIssue.PATCH: semver.bump_patch,
            model.ChangelogIssue.MINOR: semver.bump_minor,
            model.ChangelogIssue.MAJOR: semver.bump_major
        }

        self._debug('Determining next version', current_version=current_version)
        next_version = bumps[semantic](current_version)
        self._debug('Determined next version', current_version=current_version, next_version=next_version)

        return self.set_version(value=next_version, branch=branch)

    def set_version(self, value, branch=None):

        """
        Sets the version of setup.py file to the specified version number.
        Note, This will actually create a commit on top of the branch you specify.

        Args:
            value (str): The semantic version string.
            branch (:str, optional): The branch to push to commit to. Defaults to the default repository branch.

        Returns:
            pyci.api.model.Bump: The commit that was created.

        Raises:
            pyci.api.exceptions.TargetVersionEqualsCurrentVersionException:
                Current version in setup.py is equal to the given value.

        """

        if not value:
            raise exceptions.InvalidArgumentsException('value cannot be empty')

        try:
            semver.parse(value)
        except (TypeError, ValueError):
            raise exceptions.InvalidArgumentsException('value is not a legal semantic version')

        branch = branch or self.default_branch_name

        last_branch_commit = self._get_or_create_commit(sha=branch)

        current_version = last_branch_commit.setup_py_version

        self._debug('Generating setup.py file contents...', next_version=value)
        setup_py = utils.generate_setup_py(last_branch_commit.setup_py, value)
        self._debug('Generated setup.py file contents.')

        commit_message = BUMP_VERSION_COMMIT_MESSAGE_FORMAT.format(value)

        if current_version == value:
            raise exceptions.TargetVersionEqualsCurrentVersionException(version=current_version)

        bump_commit = self.commit(path='setup.py', contents=setup_py, message=commit_message)
        return model.Bump(
            impl=bump_commit.impl,
            prev_version=current_version,
            next_version=value,
            sha=bump_commit.sha)

    def reset_branch(self, name, sha, hard=False):

        """
        Reset the branch to the sha. This is equivalent to 'git reset'.

        Args:
            name (:str): The branch name.
            sha (:str): The sha to reset to.
            hard (:bool, optional): Preform a hard reset. Defaults to false.
        """

        if not name:
            raise exceptions.InvalidArgumentsException('name cannot be empty')

        if not sha:
            raise exceptions.InvalidArgumentsException('sha cannot be empty')

        try:
            self._reset_ref(ref='heads/{}'.format(name), sha=sha, hard=hard)
        except UnknownObjectException:
            raise exceptions.BranchNotFoundException(branch=name, repo=self._repo_name)

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

            return model.Branch(impl=ref, sha=ref.object.sha, name=name)

        except GithubException as e:
            if e.data['message'] == 'Object does not exist':
                raise exceptions.CommitNotFoundException(sha=sha)
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

    def commit(self, path, contents, message, branch=None):

        """
        Commit a file to the repository.

        Args:
            path (str): Path to the file, relative to the repository root.
            contents (str): The new contents of the file.
            message (str): The commit message.
            branch (:str, optional): The branch to commit to. Defaults to the repository default branch.
        """

        if not path:
            raise exceptions.InvalidArgumentsException('path cannot be empty')

        if not contents:
            raise exceptions.InvalidArgumentsException('contents cannot be empty')

        if not message:
            raise exceptions.InvalidArgumentsException('message cannot be empty')

        branch = branch or self.default_branch_name

        self._debug('Fetching last commit for branch...')
        try:
            last_commit = self.repo.get_commit(sha=branch)
        except GithubException as e:
            if isinstance(e, UnknownObjectException) or 'No commit found for SHA' in str(e):
                raise exceptions.BranchNotFoundException(branch=branch,
                                                         repo=self.repo.full_name)
            raise  # pragma: no cover
        self._debug('Fetched last commit for branch.', last_commit=last_commit.sha)

        commit = self._create_commit(path, contents, message, last_commit.sha)

        self._debug('Updating branch to point to commit...', branch=branch, sha=commit.sha)
        ref = self.repo.get_git_ref(ref='heads/{0}'.format(branch))
        ref.edit(sha=commit.sha)
        self._debug('Updated branch to point to commit', branch=branch, sha=ref.object.sha)

        return commit

    def close_issue(self, num, release):

        """
        Close an issue as part of a specific release. This method will add a comment to the
        issue, specifying the release its a part of.

        Args:
            num (int): The issue number.
            release (str): The release title this issue if a part of.

        Raises:
            ReleaseNotFoundException: Raised when the given release title does not exist.
        """

        if not num:
            raise exceptions.InvalidArgumentsException('num cannot be empty')

        if not release:
            raise exceptions.InvalidArgumentsException('release cannot be empty')

        try:
            issue = self.repo.get_issue(number=num)
        except UnknownObjectException:
            raise exceptions.IssueNotFoundException(issue=num)

        try:
            git_release = self.repo.get_release(id=release)
        except UnknownObjectException:
            raise exceptions.ReleaseNotFoundException(release=release)

        self._debug('Closing issue...', issue=issue.number)
        issue.edit(state='closed')
        self._debug('Closed issue.', issue=issue.number)

        issue_comments = [comment.body for comment in issue.get_comments()]

        issue_comment = 'This issue is part of release [{}]({})'.format(
            git_release.title, git_release.html_url)

        if issue_comment not in issue_comments:
            self._debug('Adding a comment to issue...', issue=issue.number)
            issue.create_comment(body=issue_comment)
            self._debug('Added comment.', issue=issue.number, comment=issue_comment)

    def get_release(self, title):

        """
        Fetch a release by its title.

        Args:
            title: The release title.

        Returns:
            pyci.api.model.Release: The release object.

        """

        if not title:
            raise exceptions.InvalidArgumentsException('title cannot be empty')

        try:
            release = self.repo.get_release(id=title)
        except UnknownObjectException:
            raise exceptions.ReleaseNotFoundException(release=title)

        tag = self.repo.get_git_ref('tags/{}'.format(release.tag_name))

        return model.Release(impl=release,
                             title=release.title,
                             url=release.html_url,
                             sha=tag.object.sha)

    def _create_set_version_commit(self, value, sha):

        commit = self._get_or_create_commit(sha=sha)

        current_version = commit.setup_py_version

        self._debug('Generating setup.py file contents...', next_version=value)
        setup_py = utils.generate_setup_py(commit.setup_py, value)
        self._debug('Generated setup.py file contents.')

        commit_message = BUMP_VERSION_COMMIT_MESSAGE_FORMAT.format(value)

        if current_version == value:
            raise exceptions.TargetVersionEqualsCurrentVersionException(version=current_version)

        return self._create_commit(path='setup.py',
                                   contents=setup_py,
                                   message=commit_message,
                                   sha=sha)

    def _create_commit(self, path, contents, message, sha):

        tree = InputGitTreeElement(path=path,
                                   mode='100644',
                                   type='blob',
                                   content=contents)

        commit = self.repo.get_commit(sha=sha)

        self._debug('Fetching base tree for sha...', sha=commit.commit.tree.sha)
        base_tree = self.repo.get_git_tree(sha=commit.commit.tree.sha)
        self._debug('Fetched base tree for sha', sha=commit.commit.tree.sha,
                    tree=base_tree.sha)

        self._debug('Creating tree...', tree_element=tree, base_tree=base_tree.sha)
        git_tree = self.repo.create_git_tree(tree=[tree], base_tree=base_tree)
        self._debug('Created tree.', tree_element=tree, tree_sha=git_tree.sha,
                    base_tree=base_tree.sha)

        self._debug('Creating commit...', commit_message=message, tree=git_tree.sha,
                    parent=commit.sha)
        commit = self.repo.create_git_commit(message=message,
                                             tree=git_tree,
                                             parents=[commit.commit])
        self._debug('Created commit', commit_message=message, tree=git_tree.sha,
                    parent=commit.sha,
                    sha=commit.sha)

        return model.Commit(impl=commit, sha=commit.sha, url=commit.html_url)

    def _get_or_create_commit(self, sha):
        if sha not in self.__commits:
            self.__commits[sha] = _GitHubCommit(repo=self, sha=sha)
        return self.__commits[sha]

    def _reset_ref(self, ref, sha, hard):

        self._debug('Fetching ref...', ref=ref)
        ref = self.repo.get_git_ref(ref)
        self._debug('Fetched ref', ref=ref.ref)
        if ref.object.sha == sha:
            raise exceptions.RefAlreadyAtShaException(ref=ref.ref, sha=sha)

        try:
            self._debug('Resetting ref with sha', ref=ref.ref, sha=sha)
            ref.edit(sha=sha, force=hard)
            self._debug('Reset ref with sha', ref=ref.ref, sha=sha)
        except GithubException as e:
            if e.data['message'] == 'Object does not exist':
                raise exceptions.CommitNotFoundException(sha=sha)
            if e.data['message'] == 'Update is not a fast forward':
                raise exceptions.UpdateNotFastForwardException(ref=ref.ref, sha=sha)
            raise  # pragma: no cover

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        self._logger.debug(message, **kwargs)


class _GitHubCommit(object):

    def __init__(self, repo, sha):
        self._repo = repo
        self._sha = sha
        self._runner = LocalCommandRunner()
        self._logger = logger.Logger(__name__)
        self._log_ctx = {
            'repo': self._repo.repo.full_name,
            'sha': self._sha
        }

    @cachedproperty
    def commit(self):
        try:
            self._debug('Fetching commit...')
            commit = self._repo.repo.get_commit(sha=self._sha)
            self._debug('Fetched commit.', commit=commit.html_url)
            return commit
        except GithubException as e:
            if isinstance(e, UnknownObjectException) or 'No commit found for SHA' in str(e):
                raise exceptions.CommitNotFoundException(sha=self._sha)
            raise

    @cachedproperty
    def issue(self):
        issue = self._repo.detect_issue(commit_message=self.commit.commit.message)
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

        try:
            content_file = self._repo.repo.get_contents(path='setup.py',
                                                        ref=self.commit.sha)
        except UnknownObjectException:
            raise exceptions.NotPythonProjectException(repo=self._repo.repo.full_name,
                                                       sha=self.commit.sha,
                                                       cause='setup.py file not found')

        setup_py_file = os.path.join(tempfile.mkdtemp(), 'setup.py')

        with open(setup_py_file, 'w') as stream:
            stream.write(content_file.decoded_content.decode('utf-8'))

        return setup_py_file

    @cachedproperty
    def setup_py(self):
        with open(self.setup_py_path) as stream:
            return stream.read()

    @cachedproperty
    def setup_py_version(self):
        self._debug('Extracting current setup.py version...')
        setup_py_version = utils.extract_version_from_setup_py(self.setup_py)
        self._debug('Extracted current setup.py version...', setup_py_version=setup_py_version)
        return setup_py_version

    def validate(self, hooks):

        hooks = hooks or {}

        pre_issue = hooks.get('pre_issue')
        pre_label = hooks.get('pre_label')
        post_issue = hooks.get('post_issue')
        post_label = hooks.get('post_label')

        self._debug('Validating commit should be released...')

        if pre_issue:
            pre_issue()

        if self.issue is None:
            raise exceptions.CommitNotRelatedToIssueException(sha=self.commit.sha)

        if post_issue:
            post_issue()

        if pre_label:
            pre_label()

        if not any(label in self.labels for label in ['patch', 'minor', 'major']):
            raise exceptions.IssueNotLabeledAsReleaseException(issue=self.issue.number, sha=self.commit.sha)

        if post_label:
            post_label()

        self._debug('Validation passed. Commit should be released')

    def create_release(self):

        version = self.setup_py_version

        try:

            self._debug('Creating Github release...', name=version, sha=self.commit.sha, tag=version)
            github_release = self._repo.repo.create_git_release(
                tag=version,
                target_commitish=self.commit.sha,
                name=version,
                message='',
                draft=False,
                prerelease=False
            )
            self._debug('Created Github release...', name=version, sha=self.commit.sha, tag=version)

            return model.Release(impl=github_release,
                                 title=version,
                                 url=github_release.html_url,
                                 sha=self.commit.sha)

        except GithubException as e:

            if e.data['errors'][0]['code'] != 'already_exists':
                raise  # pragma: no cover

            raise exceptions.ReleaseAlreadyExistsException(release=version)

    # pylint: disable=too-many-branches,too-many-statements
    def generate_changelog(self, base, hooks):

        hooks = hooks or {}

        pre_commit = hooks.get('pre_commit')
        pre_collect = hooks.get('pre_collect')
        pre_analyze = hooks.get('pre_analyze')
        post_analyze = hooks.get('post_analyze')
        post_commit = hooks.get('post_commit')

        self._debug('Generating changelog...')

        if pre_collect:
            pre_collect()

        # additional API call to support branch names as base
        if base:
            base = self._repo.repo.get_commit(sha=base).sha

        base = base or self._fetch_last_release()

        self._debug('Fetching commits...')
        all_commits = self._repo.repo.get_commits(sha=self.commit.sha)

        commits = []

        # this relies on the fact github returns a descending order list.
        # will this always be the case? couldn't find any docs about it...
        # i really don't want to sort it myself because it might mean fetching a lot of commits,
        # which takes time...
        for commit in all_commits:
            if commit.sha == base:
                break
            else:
                commits.append(commit)

        if not commits:
            raise exceptions.EmptyChangelogException(sha=self.commit.sha, base=base)

        self._debug('Fetched commits.', sha=self.commit.sha, base=base)

        changelog = model.Changelog(current_version=self.setup_py_version, sha=self.commit.sha)

        if pre_analyze:
            pre_analyze(commits)

        for commit in commits:

            if pre_commit:
                pre_commit(commit)

            issue = None
            try:
                issue = self._repo.detect_issue(commit_message=commit.commit.message)
            except exceptions.IssueNotFoundException as e:
                # This shouldn't stop us from creating a changelog
                self._debug('Commit {} is linked to a non-existing issue/pr: {}. Ignoring...'
                            .format(commit.sha, e.issue))

            if issue is None:
                self._debug('Found commit.', sha=commit.sha, commit_message=commit.commit.message)
                change = model.ChangelogCommit(
                    title=commit.commit.message,
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
                    semantic = model.ChangelogIssue.PATCH
                elif 'minor' in labels:
                    semantic = model.ChangelogIssue.MINOR
                elif 'major' in labels:
                    semantic = model.ChangelogIssue.MAJOR

                if 'feature' in labels:
                    self._debug('Found feature.', issue=issue.number)
                    kind = model.ChangelogIssue.FEATURE
                elif 'bug' in labels:
                    self._debug('Found bug.', issue=issue.number)
                    kind = model.ChangelogIssue.BUG
                else:
                    self._debug('Found issue.', issue=issue.number)
                    kind = model.ChangelogIssue.ISSUE

                change = model.ChangelogIssue(
                    impl=issue,
                    title=issue.title,
                    url=issue.html_url,
                    timestamp=issue.created_at,
                    kind=kind,
                    semantic=semantic)

            self._debug('Adding change to changelog.', change=change.url)
            changelog.add(change)

            if post_commit:
                post_commit()

        if post_analyze:
            post_analyze()

        self._debug('Generated changelog.')

        return changelog

    def _fetch_last_release(self):

        last_release = None

        # this relies on the fact github returns a descending order list.
        # will this always be the case? couldn't find any docs about it...
        # i really don't want to sort it myself because it might mean fetching a lot of releases,
        # which takes time...
        for release in self._repo.repo.get_releases():
            tag_commit = self._fetch_tag_commit(release.tag_name)
            if tag_commit.commit.author.date <= self.commit.commit.author.date:
                last_release = tag_commit.sha
                break

        return last_release

    def _fetch_tag_commit(self, tag_name):
        tag = self._repo.repo.get_git_ref(ref='tags/{0}'.format(tag_name))
        return self._repo.repo.get_commit(sha=tag.object.sha)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        self._logger.debug(message, **kwargs)
