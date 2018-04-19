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
import pyci.api
from pyci.api import utils
from pyci.api.changelog import Change


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


@pytest.mark.parametrize("setup_py,version,expected", [
    ('''
    
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


from setuptools import setup


PROGRAM_NAME = 'pyci'

setup(
    name=PROGRAM_NAME,
    version='0.1',
    author='Eli Polonsky',
    author_email='eli.polonsky@gmail.com',
    packages=[
        PROGRAM_NAME,
        '{0}.api'.format(PROGRAM_NAME),
        '{0}.shell'.format(PROGRAM_NAME),
        '{0}.shell.commands'.format(PROGRAM_NAME),
    ],
    license='LICENSE',
    description="Command Line Interface for releasing open source python libraries",
    entry_points={
        'console_scripts': [
            '{0} = {0}.shell.main:app'.format(PROGRAM_NAME)
        ]
    },
    install_requires=[
        'click==6.7',
        'wryte==0.2.1',
        'pygithub==1.38',
        'semver==2.7.9',
        'pygithub==1.38',
        'pyinstaller==3.3.1',
        'requests==2.18.4',
        'jinja2==2.10',
        'boltons==18.0.0',
        'wheel==0.29.0'
    ]
)    
    
    ''', '2.0.1', '''
    
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


from setuptools import setup


PROGRAM_NAME = 'pyci'

setup(
    name=PROGRAM_NAME,
    version='2.0.1',
    author='Eli Polonsky',
    author_email='eli.polonsky@gmail.com',
    packages=[
        PROGRAM_NAME,
        '{0}.api'.format(PROGRAM_NAME),
        '{0}.shell'.format(PROGRAM_NAME),
        '{0}.shell.commands'.format(PROGRAM_NAME),
    ],
    license='LICENSE',
    description="Command Line Interface for releasing open source python libraries",
    entry_points={
        'console_scripts': [
            '{0} = {0}.shell.main:app'.format(PROGRAM_NAME)
        ]
    },
    install_requires=[
        'click==6.7',
        'wryte==0.2.1',
        'pygithub==1.38',
        'semver==2.7.9',
        'pygithub==1.38',
        'pyinstaller==3.3.1',
        'requests==2.18.4',
        'jinja2==2.10',
        'boltons==18.0.0',
        'wheel==0.29.0'
    ]
)    
    
    ''')
])
def test_generate_setup_py(setup_py, version, expected):

    actual = pyci.api.utils.generate_setup_py(setup_py, version)

    assert expected == actual
