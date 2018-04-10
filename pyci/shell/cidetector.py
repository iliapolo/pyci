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
APPVEYOR = 'AppVeyor'


def detect(branch):

    ci = CIDetection(should_release=False, reason='Not running inside CI. Use the "--force" flag '
                                                  'if you wish to release anyway.')

    travis_branch = os.environ.get('TRAVIS_BRANCH')
    appveyor_branch = os.environ.get('APPVEYOR_REPO_BRANCH')

    if travis_branch:
        ci.system = TRAVIS
        ci.should_release = True
        if os.environ.get('TRAVIS_PULL_REQUEST_BRANCH'):
            ci.should_release = False
            ci.reason = 'The current build is a PR build'
        elif travis_branch != branch:
            ci.should_release = False
            ci.reason = 'The current build branch ({0}) does not match the release branch ({1})'\
                .format(travis_branch, branch)

    elif appveyor_branch:
        ci.system = APPVEYOR
        ci.should_release = True
        if os.environ.get('APPVEYOR_PULL_REQUEST_HEAD_REPO_BRANCH'):
            ci.should_release = False
            ci.reason = 'The current build is a PR build'
        elif os.environ.get('APPVEYOR_REPO_TAG_NAME'):
            ci.should_release = False
            ci.reason = 'The current build is a tag build ({0})'.format(
                os.environ['APPVEYOR_REPO_TAG_NAME'])
        elif appveyor_branch != branch:
            ci.should_release = False
            ci.reason = 'The current build branch ({0}) does not match the release branch ({1})' \
                .format(appveyor_branch, branch)

    return ci


class CIDetection(object):

    def __init__(self, system=None, should_release=True, reason=None):
        self.system = system
        self.should_release = should_release
        self.reason = reason
