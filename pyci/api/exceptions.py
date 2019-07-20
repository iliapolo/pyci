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

import platform
import os

import six


class ApiException(BaseException):
    pass


class CommandExecutionException(ApiException):

    def __init__(self, command, error, output, code):
        self.command = command
        self.error = error
        self.code = code
        self.output = output
        super(CommandExecutionException, self).__init__(self.__str__())

    def __str__(self):

        error = self.error
        output = self.output

        if six.PY2:

            # In Python2, string literals are encoded with ASCII by default.
            # This means that formatting with a unicode type can produce a UnicodeEncodeError
            # (because it would require encoding it using the default encoding)
            # We detect such a situation and force encoding with UTF-8.
            # This seems awfully strange, do I have to do this every time I use .format?
            # pylint: disable=fixme
            # TODO see if there is a better solution for this...

            # pylint: disable=undefined-variable
            if isinstance(error, unicode):
                error = error.encode('utf-8')

            # pylint: disable=undefined-variable
            if isinstance(output, unicode):
                output = output.encode('utf-8')

        return "Command '{0}' executed with an error." \
               "\ncode: {1}" \
               "\nerror: {2}" \
               "\noutput: {3}" \
            .format(self.command, self.code, error, output)


class InvalidArgumentsException(ApiException):

    def __init__(self, message):
        self.message = message
        super(InvalidArgumentsException, self).__init__(self.__str__())

    def __str__(self):
        return self.message


class FileDoesntExistException(ApiException):

    def __init__(self, path):
        self.path = path
        super(FileDoesntExistException, self).__init__(self.__str__())

    def __str__(self):
        return 'File does not exist: {0}'.format(self.path)


class DirectoryDoesntExistException(ApiException):

    def __init__(self, path):
        self.path = path
        super(DirectoryDoesntExistException, self).__init__(self.__str__())

    def __str__(self):
        return 'Directory does not exist: {0}'.format(self.path)


class FileExistException(ApiException):

    def __init__(self, path):
        self.path = path
        super(FileExistException, self).__init__(self.__str__())

    def __str__(self):
        return 'File exists: {0}'.format(self.path)


class FileIsADirectoryException(ApiException):

    def __init__(self, path):
        self.path = path
        super(FileIsADirectoryException, self).__init__(self.__str__())

    def __str__(self):
        return 'File is a directory: {0}'.format(self.path)


class DirectoryIsAFileException(ApiException):

    def __init__(self, path):
        self.path = path
        super(DirectoryIsAFileException, self).__init__(self.__str__())

    def __str__(self):
        return 'Directory is a file: {0}'.format(self.path)


class RegexMatchFailureException(ApiException):

    def __init__(self, regex):
        self.regex = regex
        super(RegexMatchFailureException, self).__init__(self.__str__())

    def __str__(self):
        return "No match found for regex '{}'".format(self.regex)


class DownloadFailedException(ApiException):

    def __init__(self, url, code, err):
        self.url = url
        self.code = code
        self.err = err
        super(DownloadFailedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Downloading URL ({}) resulted in an error ({}: {})'.format(self.url, self.code, self.err)


class PythonNotFoundException(ApiException):

    def __init__(self):
        super(PythonNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return "Python installation not found in PATH"


class ReleaseValidationFailedException(ApiException):
    pass


class BuildIsAPullRequestException(ReleaseValidationFailedException):

    def __init__(self, pull_request):
        self.pull_request = pull_request
        super(BuildIsAPullRequestException, self).__init__(self.__str__())

    def __str__(self):
        return 'Build belongs to PR number {}'.format(self.pull_request)


class BuildIsATagException(ReleaseValidationFailedException):

    def __init__(self, tag):
        self.tag = tag
        super(BuildIsATagException, self).__init__(self.__str__())

    def __str__(self):
        return 'Build running on TAG number {}'.format(self.tag)


class BuildBranchDiffersFromReleaseBranchException(ReleaseValidationFailedException):

    def __init__(self, release_branch, branch):
        self.release_branch = release_branch
        self.branch = branch
        super(BuildBranchDiffersFromReleaseBranchException, self).__init__(self.__str__())

    def __str__(self):
        return "Build running on branch '{}', which differs from the release branch '{}'" \
            .format(self.branch, self.release_branch)


class BinaryExistsException(ApiException):

    def __init__(self, path):
        self.path = path
        super(BinaryExistsException, self).__init__(self.__str__())

    def __str__(self):
        return 'Binary exists: {0}'.format(self.path)


class BinaryDoesntExistException(ApiException):

    def __init__(self, path):
        self.path = path
        super(BinaryDoesntExistException, self).__init__(self.__str__())

    def __str__(self):
        return "Binary file doesn't exist: {}".format(self.path)


class WheelExistsException(ApiException):

    def __init__(self, path):
        self.path = path
        super(WheelExistsException, self).__init__(self.__str__())

    def __str__(self):
        return 'Wheel exists: {0}'.format(self.path)


class InvalidNSISVersionException(ApiException):

    def __init__(self, version, pattern):
        self.pattern = pattern
        self.version = version
        super(InvalidNSISVersionException, self).__init__(self.__str__())

    def __str__(self):
        return "Illegal NSIS version string '{}': Must match pattern '{}'".format(
            self.version, self.pattern)


class SetupPyNotFoundException(ApiException):

    def __init__(self, repo):
        self.repo = repo
        super(SetupPyNotFoundException, self).__init__(self.__str__())

    def __str__(self):

        return 'Repository {} does not contain a setup.py file'.format(self.repo)


class MissingSetupPyArgumentException(ApiException):

    def __init__(self, repo, argument):
        self.repo = repo
        self.argument = argument
        super(MissingSetupPyArgumentException, self).__init__(self.__str__())

    def __str__(self):

        return "setup.py in repository '{}' doesnt contains an '{}' argument".format(self.repo, self.argument)


class FailedDetectingPackageMetadataException(ApiException):

    def __init__(self, argument, reason):
        self.argument = argument
        self.reason = reason
        super(FailedDetectingPackageMetadataException, self).__init__(self.__str__())

    def __str__(self):
        return 'Failed detecting {}: {}'.format(self.argument, self.reason)


class WrongPlatformException(ApiException):

    def __init__(self, expected):
        self.expected = expected
        super(WrongPlatformException, self).__init__(self.__str__())

    def __str__(self):
        return "Wrong execution Platform. Expected '{}' but running on '{}'".format(
            self.expected, platform.system()
        )


class MultipleDefaultEntrypointsFoundException(ApiException):

    def __init__(self, repo, entrypoints):
        self.entrypoints = entrypoints
        self.repo = repo
        super(MultipleDefaultEntrypointsFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Multiple entry points found for repo {}: {}'.format(self.repo, self.entrypoints)


class ConsoleScriptNotFoundException(ApiException):

    def __init__(self, repo, script):
        self.script = script
        self.repo = repo
        super(ConsoleScriptNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return "Console script not found in repo {}: {}".format(self.repo, self.script)


class EntrypointNotFoundException(ApiException):

    def __init__(self, repo, entrypoint):
        self.entrypoint = entrypoint
        self.repo = repo
        super(EntrypointNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Entrypoint not found for repo ({}): {}'.format(self.repo, self.entrypoint)


class LicenseNotFoundException(ApiException):

    def __init__(self, path):
        self.path = path
        super(LicenseNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return "License not found: {}".format(self.path)


class FailedPublishingWheelException(ApiException):

    def __init__(self, wheel, error):
        self.wheel = wheel
        self.error = error
        super(FailedPublishingWheelException, self).__init__(self.__str__())

    def __str__(self):
        return 'Failed publihsing wheel ({}): {}'.format(self.wheel, self.error)


class CommitNotRelatedToIssueException(ReleaseValidationFailedException):

    def __init__(self, sha):
        self.sha = sha
        super(CommitNotRelatedToIssueException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit {} does not reference any issue'.format(self.sha)


class IssueNotLabeledAsReleaseException(ReleaseValidationFailedException):

    def __init__(self, sha, issue):
        self.sha = sha
        self.issue = issue
        super(IssueNotLabeledAsReleaseException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit {} references issue number {}, which is not labeled with any ' \
               'release labels'.format(self.sha, self.issue)


class ReleaseNotFoundException(ApiException):

    def __init__(self, release):
        self.release = release
        super(ReleaseNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Release not found: {0}'.format(self.release)


class CommitNotFoundException(ApiException):

    def __init__(self, sha):
        self.sha = sha
        super(CommitNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit not found: {0}'.format(self.sha)


class FailedGeneratingSetupPyException(ApiException):

    def __init__(self, setup_py, version):
        self.setup_py = setup_py
        self.version = version
        super(FailedGeneratingSetupPyException, self).__init__(self.__str__())

    def __str__(self):
        return 'Failed generating a setup.py file with version: {0}. ' \
               '\nThe original file is: \n{1}'.format(self.version, self.setup_py)


class EmptyChangelogException(ApiException):

    def __init__(self, sha, base):
        self.base = base
        self.sha = sha
        super(EmptyChangelogException, self).__init__(self.__str__())

    def __str__(self):
        return 'Changelog of commit {}, relative to commit {}, is empty'.format(self.sha, self.base)


class IssueNotFoundException(ApiException):

    def __init__(self, issue):
        self.issue = issue
        super(IssueNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Issue {} not found'.format(self.issue)


class RepositoryNotFoundException(ApiException):

    def __init__(self, repo):
        self.repo = repo
        super(RepositoryNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Repository not found: {}'.format(self.repo)


class TagNotFoundException(ApiException):

    def __init__(self, tag):
        self.tag = tag
        super(TagNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return "Tag not found: {}".format(self.tag)


class BranchNotFoundException(ApiException):

    def __init__(self, branch, repo):
        self.branch = branch
        self.repo = repo
        super(BranchNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Branch {} doesnt exist in {}'.format(self.branch, self.repo)


class UpdateNotFastForwardException(ApiException):

    def __init__(self, ref, sha):
        self.sha = sha
        self.ref = ref
        super(UpdateNotFastForwardException, self).__init__(self.__str__())

    def __str__(self):
        return "Update of ref {} to {} is not a fast-forward".format(self.ref, self.sha)


class ReleaseAlreadyExistsException(ApiException):

    def __init__(self, release):
        self.release = release
        super(ReleaseAlreadyExistsException, self).__init__(self.__str__())

    def __str__(self):
        return 'Release {} already exists'.format(self.release)


class TargetVersionEqualsCurrentVersionException(ApiException):

    def __init__(self, version):
        self.version = version
        super(TargetVersionEqualsCurrentVersionException, self).__init__(self.__str__())

    def __str__(self):
        return 'The target version and current version are the same: {}'.format(self.version)


class BranchAlreadyExistsException(ApiException):

    def __init__(self, repo, branch):
        self.repo = repo
        self.branch = branch
        super(BranchAlreadyExistsException, self).__init__(self.__str__())

    def __str__(self):
        return 'Branch ({}) in repo ({}) already exists'.format(self.branch, self.repo)


class RefAlreadyAtShaException(ApiException):

    def __init__(self, ref, sha):
        self.ref = ref
        self.sha = sha
        super(RefAlreadyAtShaException, self).__init__(self.__str__())

    def __str__(self):
        return 'Reference {} is already at {}'.format(self.ref, self.sha)


class AssetAlreadyPublishedException(ApiException):

    def __init__(self, asset, release):
        self.asset = asset
        self.release = release
        super(AssetAlreadyPublishedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Asset ({0}) already exists in release ({1})'.format(self.asset, self.release)


class WheelAlreadyPublishedException(ApiException):

    def __init__(self, wheel, url):
        self.wheel = os.path.basename(wheel)
        self.url = url
        super(WheelAlreadyPublishedException, self).__init__(self.__str__())

    def __str__(self):
        return 'A wheel with the same name as {} was already uploaded to {}'.format(
            self.wheel, self.url)
