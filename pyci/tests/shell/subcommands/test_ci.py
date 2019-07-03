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

from pyci.api import ci

try:
    # python2
    from mock import MagicMock
except ImportError:
    # python3
    # noinspection PyUnresolvedReferences,PyCompatibility
    from unittest.mock import MagicMock


def test_validate_build(pyci, mocker):

    ci_provider = ci.detect(environ={
        'TRAVIS': 'True',
        'TRAVIS_REPO_SLUG': 'repo',
        'TRAVIS_BRANCH': 'release',
        'TRAVIS_COMMIT': None,
        'TRAVIS_TAG': None,
        'TRAVIS_PULL_REQUEST': 'false'
    })

    detect = MagicMock(return_value=ci_provider)

    mocker.patch(target='pyci.api.ci.detect', new=detect)

    result = pyci.run('ci validate-build --release-branch release')

    expected_output = 'Validation passed'

    assert expected_output in result.std_out


def test_validate_build_failed(pyci, mocker):

    ci_provider = ci.detect(environ={
        'TRAVIS': 'True',
        'TRAVIS_REPO_SLUG': 'repo',
        'TRAVIS_BRANCH': 'release',
        'TRAVIS_COMMIT': None,
        'TRAVIS_TAG': '0.0.1',
        'TRAVIS_PULL_REQUEST': 'false'
    })

    detect = MagicMock(return_value=ci_provider)

    mocker.patch(target='pyci.api.ci.detect', new=detect)

    result = pyci.run('ci validate-build --release-branch release', catch_exceptions=True)

    expected_output = 'Build running on TAG number 0.0.1'

    assert expected_output in result.std_out
