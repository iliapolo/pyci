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

from pyci.api import exceptions

TRAVIS = 'Travis-CI'
APPVEYOR = 'AppVeyor'


class _CI(object):

    @property
    def name(self):
        raise NotImplementedError()

    @property
    def repo(self):
        raise NotImplementedError()

    @property
    def sha(self):
        raise NotImplementedError()

    @property
    def branch(self):
        raise NotImplementedError()

    @property
    def pull_request(self):
        raise NotImplementedError()

    @property
    def tag(self):
        raise NotImplementedError()

    def detect(self):
        raise NotImplementedError()

    def validate_rc(self, release_branch):

        if self.pull_request:
            raise exceptions.NotReleaseCandidateException(reason='Build is a Pull Request ({0})'
                                                          .format(self.pull_request))

        if self.tag:
            raise exceptions.NotReleaseCandidateException(reason='Build is a Tag ({0})'
                                                          .format(self.tag))

        if self.branch != release_branch:
            raise exceptions.NotReleaseCandidateException(
                reason='The current build branch ({0}) does not match the release branch ({1})'
                .format(self.branch, release_branch))


class _TravisCI(_CI):

    @property
    def name(self):
        return TRAVIS

    @property
    def pull_request(self):
        # travis sets this env variable to the 'false' string in case this
        # build isn't a pull request... see https://docs.travis-ci.com/user/environment-variables/
        return None if os.environ.get('TRAVIS_PULL_REQUEST') == 'false' else None

    @property
    def tag(self):
        return os.environ.get('TRAVIS_TAG')

    @property
    def sha(self):
        return os.environ.get('TRAVIS_COMMIT')

    @property
    def branch(self):
        return os.environ.get('TRAVIS_BRANCH')

    @property
    def repo(self):
        return os.environ.get('TRAVIS_REPO_SLUG')

    def detect(self):
        return os.environ.get('TRAVIS')


class _AppVeyor(_CI):

    @property
    def name(self):
        return APPVEYOR

    @property
    def pull_request(self):
        return os.environ.get('APPVEYOR_PULL_REQUEST_NUMBER')

    @property
    def tag(self):
        return os.environ.get('APPVEYOR_REPO_TAG_NAME')

    @property
    def sha(self):
        return os.environ.get('APPVEYOR_REPO_COMMIT')

    @property
    def branch(self):
        return os.environ.get('APPVEYOR_REPO_BRANCH')

    @property
    def repo(self):
        return os.environ.get('APPVEYOR_REPO_NAME')

    def detect(self):
        return os.environ.get('APPVEYOR')


class CIDetector(object):

    _ci_systems = []

    def __init__(self):
        self._ci_systems.append(_TravisCI())
        self._ci_systems.append(_AppVeyor())

    def detect(self):

        ci = None
        for system in self._ci_systems:
            if system.detect():
                ci = system

        return ci
