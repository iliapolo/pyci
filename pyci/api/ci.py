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

import copy

from pyci.api import exceptions
from pyci.api import logger

TRAVIS = 'Travis-CI'
APPVEYOR = 'AppVeyor'


log = logger.get_logger(__name__)


class _CI(object):

    """
    Represents a specific CI system. It provides access to various data that CI systems can
    offer us using environment variables. Neither this class nor its children are meant for
    direct instantiation. Instead, use the 'detect()' function of this module to automatically
    get the appropriate implementation for the current execution environment.

    However, have a look at the public properties of this class to get an idea of what
    information you can access.

    """

    def __init__(self, environ):
        self.environ = environ
        self._log_ctx = {
            'repo': self.repo,
            'sha': self.sha,
            'branch': self.branch
        }

    @property
    def name(self):

        """
        Returns:
            str: The name of the CI system. (e.g Travis-CI)
        """
        raise NotImplementedError()  # pragma: no cover

    @property
    def repo(self):

        """
        Returns:
            str: The name of the repository the build is running for.
        """
        raise NotImplementedError()  # pragma: no cover

    @property
    def sha(self):

        """
        Returns:
            str: The commit sha that triggered the build.
        """
        raise NotImplementedError()  # pragma: no cover

    @property
    def branch(self):

        """
        Returns:
            str: The name of the branch the commit was pushed to.
        """
        raise NotImplementedError()  # pragma: no cover

    @property
    def pull_request(self):

        """
        Returns:
            int: If this build is a PR build, gives the PR number. Otherwise will return None.
        """
        raise NotImplementedError()  # pragma: no cover

    @property
    def tag(self):

        """
        Returns:
            str: If this build is a TAG build, gives the TAG name. Otherwise will return None.
        """
        raise NotImplementedError()  # pragma: no cover

    def detect(self):

        """
        Returns:
            bool: Check if the specific implementation is the correct one.
        """
        raise NotImplementedError()  # pragma: no cover

    def validate_rc(self, release_branch):

        """
        Validates the current build should trigger a release process. There are a few conditions
        for that:

            1. The current build is not a PR build.

            2. The current build is not a TAG build.

            3. The current build branch is the same as the release branch.

        Args:
            release_branch (str): What is the release branch to validate against. (e.g release)

        Raises:
              NotReleaseCandidateException: Raised when the current build is deemed as not
              release worthy. That is, the current build should not trigger a release process.
        """

        self._debug('Validating build...', release_branch=release_branch)

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

        self._debug('Successfully validated build.', release_branch=release_branch)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)


class _TravisCI(_CI):

    @property
    def name(self):
        return TRAVIS

    @property
    def pull_request(self):
        # travis sets this env variable to the 'false' string in case this
        # build isn't a pull request... see https://docs.travis-ci.com/user/environment-variables/
        pr = self.environ.get('TRAVIS_PULL_REQUEST')
        return pr if pr != 'false' else None

    @property
    def tag(self):
        return self.environ.get('TRAVIS_TAG')

    @property
    def sha(self):
        return self.environ.get('TRAVIS_COMMIT')

    @property
    def branch(self):
        return self.environ.get('TRAVIS_BRANCH')

    @property
    def repo(self):
        return self.environ.get('TRAVIS_REPO_SLUG')

    def detect(self):
        return self.environ.get('TRAVIS')


class _AppVeyor(_CI):

    @property
    def name(self):
        return APPVEYOR

    @property
    def pull_request(self):
        return self.environ.get('APPVEYOR_PULL_REQUEST_NUMBER')

    @property
    def tag(self):
        return self.environ.get('APPVEYOR_REPO_TAG_NAME')

    @property
    def sha(self):
        return self.environ.get('APPVEYOR_REPO_COMMIT')

    @property
    def branch(self):
        return self.environ.get('APPVEYOR_REPO_BRANCH')

    @property
    def repo(self):
        return self.environ.get('APPVEYOR_REPO_NAME')

    def detect(self):
        return self.environ.get('APPVEYOR')


# pylint: disable=too-few-public-methods
class _CIDetector(object):

    _ci_systems = []

    def __init__(self, environ):
        self._ci_systems.append(_TravisCI(environ))
        self._ci_systems.append(_AppVeyor(environ))

    def detect(self):

        ci = None
        for system in self._ci_systems:
            if system.detect():
                ci = system

        return ci


def detect(environ=None):

    """
    Detects which CI system we are currently running on.

    Returns:
         _CI: The specific implementation for the detected system.
    """

    return _CIDetector(environ or os.environ).detect()
