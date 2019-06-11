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

import pytest
try:
    # python2
    from mock import MagicMock
except ImportError:
    # python3
    # noinspection PyUnresolvedReferences,PyCompatibility
    from unittest.mock import MagicMock

from pyci.api import ci, exceptions


@pytest.mark.parametrize("env,expected_name,expected_repo,expected_branch,expected_sha,"
                         "expected_tag,expected_pull_request,expected_build_url", [

                             (
                                 {
                                     'CIRCLECI': 'True',
                                     'CIRCLE_PROJECT_USERNAME': 'iliapolo',
                                     'CIRCLE_PROJECT_REPONAME': 'pyci',
                                     'CIRCLE_BRANCH': 'master',
                                     'CIRCLE_SHA1': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                                     'CIRCLE_TAG': '0.0.1',
                                     'CIRCLE_BUILD_URL': 'build-url'
                                 },
                                 "CircleCI",
                                 "iliapolo/pyci",
                                 "master",
                                 "33526a9e0445541d96e027db2aeb93d07cdf8bd6",
                                 "0.0.1",
                                 None,
                                 'build-url'
                             ),

                             (
                                 {
                                     'CIRCLECI': 'True',
                                     'CIRCLE_PROJECT_USERNAME': None,
                                     'CIRCLE_PROJECT_REPONAME': None,
                                     'CIRCLE_BRANCH': None,
                                     'CIRCLE_SHA1': None,
                                     'CIRCLE_TAG': None,
                                     'CIRCLE_BUILD_URL': None
                                 },
                                 "CircleCI",
                                 None,
                                 None,
                                 None,
                                 None,
                                 None,
                                 None
                             ),

                             (
                                 {
                                     'TRAVIS': 'True',
                                     'TRAVIS_REPO_SLUG': 'iliapolo/pyci',
                                     'TRAVIS_BRANCH': 'master',
                                     'TRAVIS_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                                     'TRAVIS_TAG': '0.0.1',
                                     'TRAVIS_PULL_REQUEST': '5',
                                     'TRAVIS_BUILD_ID': '40'
                                 },
                                 "Travis-CI",
                                 "iliapolo/pyci",
                                 "master",
                                 "33526a9e0445541d96e027db2aeb93d07cdf8bd6",
                                 "0.0.1",
                                 "5",
                                 'https://travis-ci.org/iliapolo/pyci/builds/40'
                             ),

                             (
                                 {
                                     'TRAVIS': 'True',
                                     'TRAVIS_REPO_SLUG': None,
                                     'TRAVIS_BRANCH': None,
                                     'TRAVIS_COMMIT': None,
                                     'TRAVIS_TAG': None,
                                     'TRAVIS_PULL_REQUEST': 'false'
                                 },
                                 "Travis-CI",
                                 None,
                                 None,
                                 None,
                                 None,
                                 None,
                                 None
                             ),

                             (
                                 {
                                     'APPVEYOR': 'True',
                                     'APPVEYOR_REPO_NAME': 'iliapolo/pyci',
                                     'APPVEYOR_REPO_BRANCH': 'master',
                                     'APPVEYOR_REPO_COMMIT':
                                         '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                                     'APPVEYOR_REPO_TAG_NAME': '0.0.1',
                                     'APPVEYOR_PULL_REQUEST_NUMBER': '5',
                                     'APPVEYOR_BUILD_VERSION': '1.0.0'
                                 },
                                 "AppVeyor",
                                 "iliapolo/pyci",
                                 "master",
                                 "33526a9e0445541d96e027db2aeb93d07cdf8bd6",
                                 "0.0.1",
                                 "5",
                                 'https://ci.appveyor.com/project/iliapolo/pyci/build/1.0.0'
                             ),

                             (
                                 {
                                     'APPVEYOR': 'True',
                                     'APPVEYOR_REPO_NAME': None,
                                     'APPVEYOR_REPO_BRANCH': None,
                                     'APPVEYOR_REPO_COMMIT': None,
                                     'APPVEYOR_REPO_TAG_NAME': None,
                                     'APPVEYOR_PULL_REQUEST_NUMBER': None,
                                     'APPVEYOR_BUILD_VERSION': None
                                 },
                                 "AppVeyor",
                                 None,
                                 None,
                                 None,
                                 None,
                                 None,
                                 None
                             )
                         ])
def test_detect(env,
                expected_name,
                expected_repo,
                expected_branch,
                expected_sha,
                expected_tag,
                expected_pull_request,
                expected_build_url):

    ci_system = ci.detect(env)

    assert expected_name == ci_system.name
    assert expected_repo == ci_system.repo
    assert expected_branch == ci_system.branch
    assert expected_sha == ci_system.sha
    assert expected_tag == ci_system.tag
    assert expected_pull_request == ci_system.pull_request
    assert expected_build_url == ci_system.build_url


def test_validate_build_pull_request():

    ci_system = MagicMock()

    ci_system.pull_request = 5

    with pytest.raises(exceptions.BuildIsAPullRequestException):
        # noinspection PyTypeChecker
        ci.validate_build(ci_provider=ci_system, release_branch='release')


def test_validate_build_tag():

    ci_system = MagicMock()

    ci_system.pull_request = None
    ci_system.tag = 'tag'

    with pytest.raises(exceptions.BuildIsATagException):
        # noinspection PyTypeChecker
        ci.validate_build(ci_provider=ci_system, release_branch='release')


def test_validate_build_branch():

    ci_system = MagicMock()

    ci_system.pull_request = None
    ci_system.tag = None
    ci_system.branch = 'branch'

    with pytest.raises(exceptions.BuildBranchDiffersFromReleaseBranchException):
        # noinspection PyTypeChecker
        ci.validate_build(ci_provider=ci_system, release_branch='release')


def test_validate_build():

    ci_system = MagicMock()

    ci_system.pull_request = None
    ci_system.tag = None
    ci_system.branch = 'release'

    # noinspection PyTypeChecker
    ci.validate_build(ci_provider=ci_system, release_branch='release')
