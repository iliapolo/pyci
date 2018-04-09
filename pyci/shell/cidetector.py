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


# pylint: disable=too-few-public-methods

import os


TRAVIS = 'Travis-CI'


def detect(branch):

    ci = CIDetection(should_release=False, reason='Not running inside CI. Use the "--force" flag '
                                                  'if you wish to release anyway.')

    travis_branch = os.environ.get('TRAVIS_BRANCH')

    if travis_branch:
        ci.system = TRAVIS
        ci.should_release = True
        if os.environ.get('TRAVIS_PULL_REQUEST_BRANCH'):
            ci.should_release = False
            ci.reason = 'The current build is a PR build'
        if travis_branch != branch:
            ci.should_release = False
            ci.reason = 'The current build branch ({0}) does not match the release branch ({1})'\
                .format(travis_branch, branch)

    return ci


class CIDetection(object):

    def __init__(self, system=None, should_release=True, reason=None):
        self.system = system
        self.should_release = should_release
        self.reason = reason
