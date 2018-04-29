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

# noinspection PyPackageRequirements
import pytest

from pyci.api import ci, exceptions


@pytest.mark.parametrize("env,expected_name,expected_repo,expected_branch,expected_sha,"
                         "expected_tag,expected_pull_request", [
                             (
                                 {
                                     'TRAVIS': 'True',
                                     'TRAVIS_REPO_SLUG': 'iliapolo/pyci',
                                     'TRAVIS_BRANCH': 'master',
                                     'TRAVIS_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                                     'TRAVIS_TAG': '0.0.1',
                                     'TRAVIS_PULL_REQUEST': '5'
                                 },
                                 "Travis-CI",
                                 "iliapolo/pyci",
                                 "master",
                                 "33526a9e0445541d96e027db2aeb93d07cdf8bd6",
                                 "0.0.1",
                                 "5"
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
                                     'APPVEYOR_PULL_REQUEST_NUMBER': '5'
                                 },
                                 "AppVeyor",
                                 "iliapolo/pyci",
                                 "master",
                                 "33526a9e0445541d96e027db2aeb93d07cdf8bd6",
                                 "0.0.1",
                                 "5"
                             ),
                         ])
def test_detect(env,
                expected_name,
                expected_repo,
                expected_branch,
                expected_sha,
                expected_tag,
                expected_pull_request):

    ci_system = ci.detect(env)

    assert expected_name == ci_system.name
    assert expected_repo == ci_system.repo
    assert expected_branch == ci_system.branch
    assert expected_sha == ci_system.sha
    assert expected_tag == ci_system.tag
    assert expected_pull_request == ci_system.pull_request


@pytest.mark.parametrize("env,expected_reason", [
    (
        {
            'TRAVIS': 'True',
            'TRAVIS_REPO_SLUG': 'iliapolo/pyci',
            'TRAVIS_BRANCH': 'master',
            'TRAVIS_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'TRAVIS_TAG': '0.0.1',
            'TRAVIS_PULL_REQUEST': '5'
        },
        "Build is a Pull Request (5)"
    ),

    (
        {
            'TRAVIS': 'True',
            'TRAVIS_REPO_SLUG': 'iliapolo/pyci',
            'TRAVIS_BRANCH': 'master',
            'TRAVIS_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'TRAVIS_TAG': '0.0.1',
            'TRAVIS_PULL_REQUEST': 'false'
        },
        "Build is a Tag (0.0.1)"
    ),

    (
        {
            'TRAVIS': 'True',
            'TRAVIS_REPO_SLUG': 'iliapolo/pyci',
            'TRAVIS_BRANCH': 'master',
            'TRAVIS_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'TRAVIS_TAG': None,
            'TRAVIS_PULL_REQUEST': 'false'
        },
        "The current build branch (master) does not match the release branch (release)"
    ),


    (
        {
            'TRAVIS': 'True',
            'TRAVIS_REPO_SLUG': 'iliapolo/pyci',
            'TRAVIS_BRANCH': 'release',
            'TRAVIS_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'TRAVIS_TAG': None,
            'TRAVIS_PULL_REQUEST': 'false'
        },
        None
    ),

    (
        {
            'APPVEYOR': 'True',
            'APPVEYOR_REPO_NAME': 'iliapolo/pyci',
            'APPVEYOR_REPO_BRANCH': 'master',
            'APPVEYOR_REPO_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'APPVEYOR_REPO_TAG_NAME': '0.0.1',
            'APPVEYOR_PULL_REQUEST_NUMBER': '5'
        },
        "Build is a Pull Request (5)"
    ),

    (
        {
            'APPVEYOR': 'True',
            'APPVEYOR_REPO_NAME': 'iliapolo/pyci',
            'APPVEYOR_REPO_BRANCH': 'master',
            'APPVEYOR_REPO_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'APPVEYOR_REPO_TAG_NAME': '0.0.1',
            'APPVEYOR_PULL_REQUEST_NUMBER': None
        },
        "Build is a Tag (0.0.1)"
    ),

    (
        {
            'APPVEYOR': 'True',
            'APPVEYOR_REPO_NAME': 'iliapolo/pyci',
            'APPVEYOR_REPO_BRANCH': 'master',
            'APPVEYOR_REPO_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'APPVEYOR_REPO_TAG_NAME': None,
            'APPVEYOR_PULL_REQUEST_NUMBER': None
        },
        "The current build branch (master) does not match the release branch (release)"
    ),


    (
        {
            'APPVEYOR': 'True',
            'APPVEYOR_REPO_NAME': 'iliapolo/pyci',
            'APPVEYOR_REPO_BRANCH': 'release',
            'APPVEYOR_REPO_COMMIT': '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
            'APPVEYOR_REPO_TAG_NAME': None,
            'APPVEYOR_PULL_REQUEST_NUMBER': None
        },
        None
    ),


])
def test_validate_rc(env, expected_reason):

    ci_system = ci.detect(env)

    if expected_reason:
        with pytest.raises(exceptions.ReleaseValidationFailedException) as info:
            ci_system.validate_build(release_branch='release')
        assert expected_reason in str(info.value)
    else:
        ci_system.validate_build(release_branch='release')
