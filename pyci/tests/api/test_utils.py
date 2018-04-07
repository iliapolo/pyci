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
import tempfile

import pytest

import pyci
from pyci.api import utils
from pyci.api.changelog import Change


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
    ("1.2.3", ['nothing'], "1.2.3"),
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


@pytest.mark.parametrize("url,expected", [
    ("git@github.com:iliapolo/pyci.git", "iliapolo/pyci"),
    ("https://github.com/iliapolo/pyci.git", "iliapolo/pyci"),
    ("not-a-git-url", None),
])
def test_parse_repo(url, expected):

    actual = utils.parse_repo(url)

    assert expected == actual


@pytest.mark.parametrize("cwd,expected", [
    (os.path.abspath(os.path.join(os.path.abspath(pyci.__file__), os.pardir, os.pardir)),
     'iliapolo/pyci'),
    (tempfile.mkdtemp(), None)
])
def test_get_local_repo(cwd, expected):

    prev_cwd = os.getcwd()

    try:
        os.chdir(cwd)
        actual = utils.get_local_repo()

        assert expected == actual
    finally:
        os.chdir(prev_cwd)


@pytest.mark.parametrize("bugs,features,internals,dangling_commits,expected", [

    ([], [Change(title='this is the feature', url='this is the feature url')], [], [], '''*Changes*


**New Features:**


- this is the feature ([Issue](this is the feature url))







'''),

    ([Change(title='this is the bug', url='this is the bug url')], [], [], [], '''*Changes*




**Bug Fixes:**


- this is the bug ([Issue](this is the bug url))





'''),

    ([], [], [Change(title='this is the internal', url='this is the internal url')], [],
     '''*Changes*






**Internals:**


- this is the internal ([Issue](this is the internal url))



''')


])
def test_render_changelog(bugs, features, internals, dangling_commits, expected):

    actual = utils.render_changelog(features=features, bugs=bugs, internals=internals,
                                    dangling_commits=dangling_commits)

    assert expected == actual
