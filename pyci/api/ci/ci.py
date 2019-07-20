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

from pyci.api import exceptions

CIRCLE = 'CircleCI'
TRAVIS = 'Travis-CI'
APPVEYOR = 'AppVeyor'


class _Provider(object):

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

    @property
    def build_url(self):

        """
        Returns:
            str: The URL of the build execution.
        """
        raise NotImplementedError()  # pragma: no cover

    def detect(self):

        """
        Returns:
            bool: Check if the specific implementation is the correct one.
        """
        raise NotImplementedError()  # pragma: no cover

    def running_builds(self, branch, repo):

        """
        Fetch running builds.

        Args:
            branch (str): The branch name the builds are running on.
            repo (str): The repo slug name the builds are running on.

        Returns:
            list: A list of builds that are currently running on the given branch.

        """


class _CircleCI(_Provider):

    @property
    def name(self):
        return CIRCLE

    @property
    def repo(self):
        org = self.environ.get('CIRCLE_PROJECT_USERNAME')
        name = self.environ.get('CIRCLE_PROJECT_REPONAME')
        if org and name:
            return '{}/{}'.format(org, name)
        return None

    @property
    def sha(self):
        return self.environ.get('CIRCLE_SHA1')

    @property
    def branch(self):
        return self.environ.get('CIRCLE_BRANCH')

    @property
    def pull_request(self):
        # currently circle ci does not support running builds on the PR.
        # see https://discuss.circleci.com/t/pull-requests-not-triggering-build/1213/10
        # see https://discuss.circleci.com/t/pull-requests-not-triggering-build/1213/6
        return None

    @property
    def tag(self):
        return self.environ.get('CIRCLE_TAG')

    @property
    def build_url(self):
        return self.environ.get('CIRCLE_BUILD_URL')

    def detect(self):
        return self.environ.get('CIRCLECI')


class _TravisCI(_Provider):

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

    @property
    def build_url(self):

        build_id = self.environ.get('TRAVIS_BUILD_ID')

        if build_id:
            return 'https://travis-ci.org/{}/builds/{}'.format(self.repo, build_id)

        return None

    def detect(self):
        return self.environ.get('TRAVIS')


class _AppVeyor(_Provider):

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

    @property
    def build_url(self):

        build_version = self.environ.get('APPVEYOR_BUILD_VERSION')

        if build_version:
            return 'https://ci.appveyor.com/project/{}/build/{}'.format(self.repo, build_version)

        return None

    def detect(self):
        return self.environ.get('APPVEYOR')


def detect(environ=None):

    """
    Detects which CI provider we are currently running on.

    Args:
        environ (dict): The environment dictionary to use. Defaults to os.environ

    Returns:
         _Provider: The specific implementation for the detected provider.
    """

    environ = environ or os.environ

    providers = [_TravisCI(environ), _AppVeyor(environ), _CircleCI(environ)]

    for provider in providers:
        if provider.detect():
            return provider

    return None


def validate_build(ci_provider, release_branch, hooks=None):

    """
    Validates the current build should trigger a release process. There are a few conditions
    for that:

        1. The current build is not a PR build.

        2. The current build is not a TAG build.

        3. The current build branch is the same as the release branch.

    Args:
        hooks: dictionary of callable hooks to execute in various steps of this method.
        release_branch (str): What is the release branch to validate against. (e.g release)
        ci_provider (_Provider): The CI provider we are currently running on. see 'detect'.

    Raises:
          NotReleaseCandidateException: Raised when the current build is deemed as not
          release worthy. That is, the current build should not trigger a release process.
    """

    pre_pr = hooks.get('pre_pr') if hooks else None
    pre_tag = hooks.get('pre_tag') if hooks else None
    pre_branch = hooks.get('pre_branch') if hooks else None

    post_pr = hooks.get('post_pr') if hooks else None
    post_tag = hooks.get('post_tag') if hooks else None
    post_branch = hooks.get('post_branch') if hooks else None

    if pre_pr:
        pre_pr()

    if ci_provider.pull_request:
        raise exceptions.BuildIsAPullRequestException(pull_request=ci_provider.pull_request)

    if post_pr:
        post_pr()

    if pre_tag:
        pre_tag()

    if ci_provider.tag:
        raise exceptions.BuildIsATagException(tag=ci_provider.tag)

    if post_tag:
        post_tag()

    if pre_branch:
        pre_branch()

    if ci_provider.branch != release_branch:
        raise exceptions.BuildBranchDiffersFromReleaseBranchException(
            branch=ci_provider.branch,
            release_branch=release_branch)

    if post_branch:
        post_branch()
