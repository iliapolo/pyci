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

from pyci.api import utils


def test_get_pull_request_number():

    actual = utils.get_pull_request_number('Implemented feature 1 (#6)')

    expected = 6

    assert expected == actual


@pytest.mark.parametrize("keyword", utils.SUPPORTED_KEYWORDS)
def test_get_issue_number(keyword):

    pr_body = 'This pull request {0} #3 more text'.format(keyword)
    actual = utils.get_issue_number(pr_body)

    expected = '3'

    assert expected == actual


@pytest.mark.parametrize("last_release,labels,expected", [
    (None, ['whatever'], "0.0.1"),
    ("1.2.3", ['nothing'], None),
    ("1.2.3", ['patch'], "1.2.4"),
    ("1.2.3", ['minor'], "1.3.0"),
    ("1.2.3", ['major'], "2.0.0"),
    ("1.2.3", ['major', 'minor', 'patch'], "2.0.0"),
    ("1.2.3", ['major', 'minor'], "2.0.0"),
    ("1.2.3", ['major', 'patch'], "2.0.0"),
    ("1.2.3", ['minor', 'patch'], "1.3.0")
])
def test_get_next_release(last_release, labels, expected):

    actual = utils.get_next_release(last_release=last_release, labels=labels)

    assert expected == actual
