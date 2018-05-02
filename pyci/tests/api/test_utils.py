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

# noinspection PyPackageRequirements
import pytest

import pyci
import pyci.api
from pyci.api import utils, exceptions


@pytest.mark.parametrize("url,expected", [
    ("git@github.com:iliapolo/pyci.git", "iliapolo/pyci"),
    ("https://github.com/iliapolo/pyci.git", "iliapolo/pyci"),
    ("not-a-git-url", None),
])
def test_parse_repo(url, expected):

    actual = utils.extract_repo(url)

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
    
    '''),

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
    version2='0.1',
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
    
    ''', '2.0.1', None)

])
def test_generate_setup_py(setup_py, version, expected):

    if expected is None:
        with pytest.raises(exceptions.FailedGeneratingSetupPyException):
            pyci.api.utils.generate_setup_py(setup_py, version)
    else:
        actual = pyci.api.utils.generate_setup_py(setup_py, version)
        assert expected == actual


def test_validate_directory_exists():

    with pytest.raises(exceptions.DirectoryDoesntExistException):
        utils.validate_directory_exists(path='doesnt-exist')

    with pytest.raises(exceptions.DirectoryIsAFileException):
        utils.validate_directory_exists(path=tempfile.mkstemp()[1])

    utils.validate_directory_exists(tempfile.mkdtemp())


def test_validate_file_exists():

    with pytest.raises(exceptions.FileDoesntExistException):
        utils.validate_file_exists(path='doesnt-exist')

    with pytest.raises(exceptions.FileIsADirectoryException):
        utils.validate_file_exists(path=tempfile.mkdtemp())

    utils.validate_file_exists(tempfile.mkstemp()[1])


def test_validate_file_does_not_exist():

    with pytest.raises(exceptions.FileExistException):
        utils.validate_file_does_not_exist(path=tempfile.mkstemp()[1])

    with pytest.raises(exceptions.FileIsADirectoryException):
        utils.validate_file_does_not_exist(path=tempfile.mkdtemp())

    utils.validate_file_does_not_exist(path='doesnt-exist')
