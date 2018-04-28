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


class ReleaseValidationFailedException(ApiException):
    pass


class BuildIsAPullRequestException(ReleaseValidationFailedException):

    def __init__(self, pull_request):
        self.pull_request = pull_request
        super(BuildIsAPullRequestException, self).__init__(self.__str__())

    def __str__(self):
        return 'Build is a Pull Request ({})'.format(self.pull_request)


class BuildIsATagException(ReleaseValidationFailedException):

    def __init__(self, tag):
        self.tag = tag
        super(BuildIsATagException, self).__init__(self.__str__())

    def __str__(self):
        return 'Build is a Tag ({})'.format(self.tag)


class BuildBranchDiffersFromReleaseBranchException(ReleaseValidationFailedException):

    def __init__(self, release_branch, branch):
        self.release_branch = release_branch
        self.branch = branch
        super(BuildBranchDiffersFromReleaseBranchException, self).__init__(self.__str__())

    def __str__(self):
        return 'The current build branch ({}) does not match the release branch ({})'\
            .format(self.branch, self.release_branch)


class CommitNotRelatedToIssueException(ReleaseValidationFailedException):

    def __init__(self, sha):
        self.sha = sha
        super(CommitNotRelatedToIssueException, self).__init__(self.__str__())

    def __str__(self):
        return 'The commit ({}) is not related to any issue'.format(self.sha)


class IssueNotLabeledAsReleaseException(ReleaseValidationFailedException):

    def __init__(self, sha, issue):
        self.sha = sha
        self.issue = issue
        super(IssueNotLabeledAsReleaseException, self).__init__(self.__str__())

    def __str__(self):
        return 'Issue (#{}) of commit ({}) is not labeled with any release labels' \
            .format(self.issue, self.sha)


class ReleaseNotFoundException(ApiException):

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

    def __init__(self, repo, packages):
        self.repo = repo
        self.packages = packages
        super(MultiplePackagesFound, self).__init__(self.__str__())

    def __str__(self):
        return 'Found multiple python packages at the root level of your repo ({0}): {1}'.format(
            self.repo, ','.join(self.packages))


class PackageNotFound(ApiException):

    def __init__(self, repo):
        self.repo = repo
        super(PackageNotFound, self).__init__(self.__str__())

    def __str__(self):
        return 'No python packages found at the root level of your repo ({0})'.format(self.repo)


class DefaultEntrypointNotFoundException(ApiException):

    def __init__(self, repo, name, top_level_package):
        self.top_level_package = top_level_package
        self.name = name
        self.repo = repo
        self.expected_paths = [
            os.path.join(self.top_level_package, 'shell', 'main.py'),
            '{0}.spec'.format(self.name)
        ]
        super(DefaultEntrypointNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'No entrypoint found for repo ({0}): Looked in --> [{1}]'.format(
            self.repo, ', '.join(self.expected_paths))


class EntrypointNotFoundException(ApiException):

    def __init__(self, repo, entrypoint):
        self.entrypoint = entrypoint
        self.repo = repo
        super(EntrypointNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Entrypoint not found for repo ({0}): {1}'.format(self.repo, self.entrypoint)


class CommitIsAlreadyReleasedException(ApiException):

    def __init__(self, sha, release):
        self.sha = sha
        self.release = release
        super(CommitIsAlreadyReleasedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit ({}) is already released ({})'.format(self.sha, self.release)


class CommitNotFoundException(ApiException):

    def __init__(self, sha):
        self.sha = sha
        super(CommitNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit not found: {0}'.format(self.sha)


class ReleaseConflictException(ApiException):

    def __init__(self, our_sha, their_sha, release):
        self.our_sha = our_sha
        self.their_sha = their_sha
        self.release = release
        super(ReleaseConflictException, self).__init__(self.__str__())

    def __str__(self):
        return 'Release conflict. The release ({0}) already exists but with a different ' \
               'commit ({1}) than ours ({2})'.format(self.release, self.their_sha, self.our_sha)


class FailedGeneratingSetupPyException(ApiException):

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
        return 'File exist: {0}'.format(self.path)


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

    def __init__(self, repo, cause, sha):
        self.sha = sha
        self.cause = cause
        self.repo = repo
        super(NotPythonProjectException, self).__init__(self.__str__())

    def __str__(self):
        return 'It seems like the commit ({}) in repository ({}) does not contain a valid ' \
               'python project: {}.'.format(self.sha, self.repo, self.cause)


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
        return 'Branch ({}) doesnt exist in repo ({})'.format(self.branch, self.repo)


class ShaNotFoundException(ApiException):

    def __init__(self, sha, repo):
        self.sha = sha
        self.repo = repo
        super(ShaNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Sha ({}) doesnt exist in repo ({})'.format(self.sha, self.repo)


class TargetVersionEqualsCurrentVersionException(ApiException):

    def __init__(self, version):
        self.version = version
        super(TargetVersionEqualsCurrentVersionException, self).__init__(self.__str__())

    def __str__(self):
        return 'The target version and current version are the same: {}'.format(self.version)


class DownloadFailedException(ApiException):

    def __init__(self, url, code, err):
        self.url = url
        self.code = code
        self.err = err
        super(DownloadFailedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Downloading URL ({}) resulted in an error ({}: {})'.format(self.url,
                                                                           self.code,
                                                                           self.err)


class BranchAlreadyExistsException(ApiException):

    def __init__(self, repo, branch):
        self.repo = repo
        self.branch = branch
        super(BranchAlreadyExistsException, self).__init__(self.__str__())

    def __str__(self):
        return 'Branch ({}) in repo ({}) already exists'.format(self.branch, self.repo)
