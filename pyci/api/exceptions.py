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


class ApiException(BaseException):
    pass


class ReleaseNotFoundException(ApiException):

    """
    Raised when the release id does not match any existing github releases.

    Args:
        release (str): The id of the release
    """

    def __init__(self, release):
        self.release = release
        super(ReleaseNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Release not found: {0}'.format(self.release)


class RefNotFoundException(ApiException):

    def __init__(self, ref):
        self.ref = ref
        super(RefNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Ref not found: {0}'.format(self.ref)


class CommandExecutionException(ApiException):

    """
    Raised when a local command execution failed to complete successfully.

    Args:
        command (str): The command to execute.
        error (str): The error output of the execution.
        output (str): The standard output of the execution.
        code (int): The exit code of the execution.
    """

    def __init__(self, command, error, output, code):
        self.command = command
        self.error = error
        self.code = code
        self.output = output
        super(CommandExecutionException, self).__init__(self.__str__())

    def __str__(self):
        return "Command '{0}' executed with an error." \
               "\ncode: {1}" \
               "\nerror: {2}" \
               "\noutput: {3}" \
            .format(self.command, self.code,
                    self.error or None,
                    self.output or None)


class MultiplePackagesFound(ApiException):

    """
    Raised when multiple top level python packages are found in the repository.
    A properly structured python project should contain a top level package, usually named
    after the project name. All other python packages should reside under it.

    Args:
        repo (str): The repository in question.
        packages (set): All the top level packages found.
    """

    def __init__(self, repo, packages):
        self.repo = repo
        self.packages = packages
        super(MultiplePackagesFound, self).__init__(self.__str__())

    def __str__(self):
        return 'Found multiple python packages at the root level of your repo ({0}): {1}'.format(
            self.repo, ','.join(self.packages))


class PackageNotFound(ApiException):

    """
    Raised when no top level python package was found in the repository.
    A properly structured python project should contain a top level package, usually named
    after the project name. All other python packages should reside under it.

    Args:

        repo (str): The repository in question.

    """

    def __init__(self, repo):
        self.repo = repo
        super(PackageNotFound, self).__init__(self.__str__())

    def __str__(self):
        return 'No python packages found at the root level of your repo ({0})'.format(self.repo)


class DefaultEntrypointNotFoundException(ApiException):

    """

    Raised when attempting to locate a default entrypoint for building a binary package.
    This process takes place if the user does not provide a specific entrypoint. In which case,
    pyci will look for a .spec or a main.py file.

    Args:

        repo (str): The repository in question.
        name (str): The project name as defined in the setup.py file.
        top_level_package (str): The name of the top level python package.

    """

    def __init__(self, repo, name, top_level_package):
        self.top_level_package = top_level_package
        self.name = name
        self.repo = repo
        super(DefaultEntrypointNotFoundException, self).__init__(self.__str__())

    def __str__(self):

        expected_paths = [
            os.path.join(self.top_level_package, 'shell', 'main.py'),
            '{0}.spec'.format(self.name)
        ]

        return 'No entrypoint found for repo ({0}): Looked in --> [{1}]'.format(
            self.repo, ', '.join(expected_paths))


class EntrypointNotFoundException(ApiException):

    """

    Raised when the entrypoint a user provided does not exist.

    Args:

        repo (str): THe repository in question.

    """

    def __init__(self, repo, entrypoint):
        self.entrypoint = entrypoint
        self.repo = repo
        super(EntrypointNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Entrypoint not found for repo ({0}): {1}'.format(self.repo, self.entrypoint)


class CommitNotRelatedToIssueException(ApiException):

    """

    Raised when the commit we want to release is not related to any issue (i.e dangling commit).

    Args:

        sha (str): The sha of the commit.

    """

    def __init__(self, sha):
        self.sha = sha
        super(CommitNotRelatedToIssueException, self).__init__(self.__str__())

    def __str__(self):
        return 'The commit is not related to any issue: {0}'.format(self.sha)


class IssueIsNotLabeledAsReleaseException(ApiException):

    """

    Raised when the issue related to the commit we want to release, is not labeled with any release
    labels (e.g patch, minor, major)

    Args:

        sha (str): The sha of the commit.
        issue (int): The issue number.

    """

    def __init__(self, sha, issue):
        self.sha = sha
        self.issue = issue
        super(IssueIsNotLabeledAsReleaseException, self).__init__(self.__str__())

    def __str__(self):
        return 'Issue ({0}) of commit ({1} is not labeled with any release labels'\
            .format(self.issue, self.sha)


class CommitIsAlreadyReleasedException(ApiException):

    """

    Raised when the commit we want to release is already released.

    Args:

        sha (str): The sha of the commit to release.
        release (str): The id of the release its released in.

    """

    def __init__(self, sha, release):
        self.sha = sha
        self.release = release
        super(CommitIsAlreadyReleasedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit is already released: {0} (release {1})'.format(self.sha, self.release)


class CommitNotFoundException(ApiException):

    """

    Raised when the commit sha specified does not exist.

    Args:

        sha (str): The sha of the commit.

    """

    def __init__(self, sha):
        self.sha = sha
        super(CommitNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit not found: {0}'.format(self.sha)


class ReleaseConflictException(ApiException):

    """

    """

    def __init__(self, our_sha, their_sha, release):
        self.our_sha = our_sha
        self.their_sha = their_sha
        self.release = release
        super(ReleaseConflictException, self).__init__(self.__str__())

    def __str__(self):
        return 'Release conflict. The release ({0}) already exists but with a different ' \
               'commit ({1}) than ours ({2})'.format(self.release, self.their_sha, self.our_sha)


class NotReleaseCandidateException(ApiException):

    """

    Raised when the current build should not trigger a release process.

    Args:

         reason (str): The reason why a release should not take place.

    """

    def __init__(self, reason):
        self.reason = reason
        super(NotReleaseCandidateException, self).__init__(self.__str__())

    def __str__(self):
        return self.reason


class FailedGeneratingSetupPyException(ApiException):

    """

    Raised when the setup.py file

    """

    def __init__(self, setup_py, version):
        self.setup_py = setup_py
        self.version = version
        super(FailedGeneratingSetupPyException, self).__init__(self.__str__())

    def __str__(self):
        return 'Failed generating a setup.py file with version: {0}. ' \
               '\nThe original file is: \n{1}'.format(self.version, self.setup_py)


class InvalidArgumentsException(ApiException):

    def __init__(self, message):
        self.message = message
        super(InvalidArgumentsException, self).__init__(self.__str__())

    def __str__(self):
        return self.message


class SemanticVersionException(ApiException):

    def __init__(self, version):
        self.version = version
        super(SemanticVersionException, self).__init__(self.__str__())

    def __str__(self):
        return 'The version ({0} does not conform to the semantic version scheme'\
                .format(self.version)


class TargetVersionNotGreaterThanSetupPyVersionException(ApiException):

    def __init__(self, current_version, target_version):
        self.current_version = current_version
        self.target_version = target_version
        super(TargetVersionNotGreaterThanSetupPyVersionException, self).__init__(self.__str__())

    def __str__(self):
        return 'Target version ({0}) is not greater than current setup.py version ({1})'\
               .format(self.target_version, self.current_version)


class TargetVersionNotGreaterThanLastReleaseVersionException(ApiException):

    def __init__(self, last_release_version, target_version):
        self.last_release_version = last_release_version
        self.target_version = target_version
        super(TargetVersionNotGreaterThanLastReleaseVersionException, self).__init__(self.__str__())

    def __str__(self):
        return 'Target version ({0}) is not greater than last release version ({1})' \
            .format(self.target_version, self.last_release_version)


class EmptyChangelogException(ApiException):

    def __init__(self, sha, last_release):
        self.last_release = last_release
        self.sha = sha
        super(EmptyChangelogException, self).__init__(self.__str__())

    def __str__(self):
        return 'Changelog from last release ({0}) for commit ({1}) is empty'.format(
            self.last_release, self.sha)


class CannotDetermineNextVersionException(ApiException):

    def __init__(self, sha):
        self.sha = sha
        super(CannotDetermineNextVersionException, self).__init__(self.__str__())

    def __str__(self):
        return 'Cannot determine what the next version number should be. The commit ({0}) ' \
               'is not preceded with any release eligible issues'.format(self.sha)


class FileDoesntExistException(ApiException):

    def __init__(self, path):
        self.path = path
        super(FileDoesntExistException, self).__init__(self.__str__())

    def __str__(self):
        return 'File does not exist: {0}'.format(self.path)


class FileExistException(ApiException):

    def __init__(self, path):
        self.path = path
        super(FileExistException, self).__init__(self.__str__())

    def __str__(self):
        return 'File exist: {0}'.format(self.path)


class FileIsADirectoryException(ApiException):

    def __init__(self, path):
        self.path = path
        super(FileIsADirectoryException, self).__init__(self.__str__())

    def __str__(self):
        return 'File is a directory: {0}'.format(self.path)


class AssetAlreadyPublishedException(ApiException):

    def __init__(self, asset, release):
        self.asset = asset
        self.release = release
        super(AssetAlreadyPublishedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Asset ({0}) already exists in release ({1})'.format(self.asset, self.release)


class WheelAlreadyPublishedException(ApiException):

    def __init__(self, wheel, url):
        self.wheel = wheel
        self.url = url
        super(WheelAlreadyPublishedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Wheel ({0}) already exists in ({1})'.format(self.wheel, self.url)


class IssueNotFoundException(ApiException):

    def __init__(self, commit_message, pr_number, issue_number):
        self.commit_message = commit_message
        self.pr_number = pr_number
        self.issue_number = issue_number
        super(IssueNotFoundException, self).__init__(self.__str__())

    def __str__(self):

        if self.pr_number:
            message = 'commit ({0}) --> pr ({1}) --> issue ({2})'.format(
                self.commit_message,
                self.pr_number,
                self.issue_number)
        else:
            message = 'commit ({0}) --> issue ({1})'.format(self.commit_message, self.issue_number)

        return 'Issue not found: {0}'.format(message)


class NotPythonProjectException(ApiException):

    def __init__(self, repo, cause):
        self.cause = cause
        self.repo = repo
        super(NotPythonProjectException, self).__init__(self.__str__())

    def __str__(self):
        return 'It seems like the repository ({0}) does not contain a valid python project: {1}.' \
               'Please follow the instructions to create a standard python project --> ' \
               'https://packaging.python.org/tutorials/distributing-packages/'.format(self.repo,
                                                                                      self.cause)
