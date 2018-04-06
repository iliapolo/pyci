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
