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


class ApiException(BaseException):
    pass


class InvalidCommitMessage(ApiException):

    def __init__(self, commit_message):
        self.commit_message = commit_message
        super(InvalidCommitMessage, self).__init__(self.__str__())

    def __str__(self):
        return "Invalid commit message ({0}: Must contain a reference to the pull request by " \
               "using the '(#<pull-request-id)' string inside the message>"\
               .format(self.commit_message)


class InvalidPullRequestBody(ApiException):

    def __init__(self, body):
        self.body = body
        super(InvalidPullRequestBody, self).__init__(self.__str__())

    def __str__(self):
        return "Invalid pull request body ({0}): Must contain a reference to the issue number by " \
               "using the '#<issue-id>' string inside the body"


class ReleaseNotFoundException(ApiException):

    def __init__(self, release):
        self.release = release
        super(ReleaseNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Release not found: {0}'.format(self.release)


class MultipleReleasesFoundException(ApiException):

    def __init__(self, release, how_many):
        self.how_many = how_many
        self.release = release
        super(MultipleReleasesFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Multiple releases found ({0}): {1}'.format(self.release, self.how_many)


class RefNotFoundException(ApiException):

    def __init__(self, ref):
        self.ref = ref
        super(RefNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Ref not found: {0}'.format(self.ref)


class MultipleRefsFoundException(ApiException):

    def __init__(self, ref, how_many):
        self.how_many = how_many
        self.ref = ref
        super(MultipleRefsFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Multiple refs found ({0}): {1}'.format(self.ref, self.how_many)


class TagNotFoundException(ApiException):

    def __init__(self, tag, release):
        self.tag = tag
        self.release = release
        super(TagNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'Tag ({0}) not found for release: {1}'.format(self.tag, self.release)


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


class BinaryAlreadyExists(ApiException):

    def __init__(self, path):
        self.path = path
        super(BinaryAlreadyExists, self).__init__(self.__str__())

    def __str__(self):
        return 'Binary file already exists: {0}'.format(self.path)


class WheelAlreadyExistsException(ApiException):

    def __init__(self, path):
        self.path = path
        super(WheelAlreadyExistsException, self).__init__(self.__str__())

    def __str__(self):
        return 'Wheel file already exists: {0}'.format(self.path)


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


class EntrypointNotFoundException(ApiException):

    def __init__(self, repo, expected_paths):
        self.expected_paths = expected_paths
        self.repo = repo
        super(EntrypointNotFoundException, self).__init__(self.__str__())

    def __str__(self):
        return 'No entrypoint found for repo ({0}): Looked in --> [{1}]'.format(
            self.repo, ', '.join(self.expected_paths))


class CommitNotRelatedToPullRequestException(ApiException):

    def __init__(self, sha):
        self.sha = sha
        super(CommitNotRelatedToPullRequestException, self).__init__(self.__str__())

    def __str__(self):
        return 'The commit is not related to any pull request: {0}'.format(self.sha)


class PullRequestNotRelatedToIssueException(ApiException):

    def __init__(self, sha, pr):
        self.sha = sha
        self.pr = pr
        super(PullRequestNotRelatedToIssueException, self).__init__(self.__str__())

    def __str__(self):
        return 'The pull request is not related to any issue: {0} (commit {1})'.format(self.pr,
                                                                                       self.sha)


class IssueIsNotLabeledAsReleaseException(ApiException):

    def __init__(self, sha, pr, issue):
        self.pr = pr
        self.sha = sha
        self.issue = issue
        super(IssueIsNotLabeledAsReleaseException, self).__init__(self.__str__())

    def __str__(self):
        return 'Issue is not labeled with any release labels: {0} (commit {1}, pr {2})'\
            .format(self.issue, self.sha, self.pr)


class CommitIsAlreadyReleasedException(ApiException):

    def __init__(self, sha, release):
        self.sha = sha
        self.release = release
        super(CommitIsAlreadyReleasedException, self).__init__(self.__str__())

    def __str__(self):
        return 'Commit is already released: {0} (release {1})'.format(self.sha, self.release)


class ReleaseConflictException(ApiException):

    def __init__(self, our_sha, their_sha, release):
        self.our_sha = our_sha
        self.their_sha = their_sha
        self.release = release
        super(ReleaseConflictException, self).__init__(self.__str__())

    def __str__(self):
        return 'Release conflict. The release ({0}) already exists but with a different ' \
               'commit ({1}) than ours ({2})'.format(self.release, self.their_sha, self.our_sha)


class NotReleaseCandidateException(ApiException):

    def __init__(self, reason):
        self.reason = reason
        super(NotReleaseCandidateException, self).__init__(self.__str__())

    def __str__(self):
        return self.reason
