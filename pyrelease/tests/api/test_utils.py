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

from pyrelease.api import utils


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

