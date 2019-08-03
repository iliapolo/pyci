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
import sys

import pytest

from pyci.tests import resources
from pyci.api import utils, exceptions


@pytest.mark.parametrize("setup_py_path,version,expected", [
    ('setup.py.0.1', '2.0.1', 'setup.py.0.1.expected'),
    ('setup.py.corrupted', '2.0.1', None)

])
def test_generate_setup_py(setup_py_path, version, expected):

    setup_py = resources.get_resource(setup_py_path)

    if expected is None:
        with pytest.raises(exceptions.FailedGeneratingSetupPyException):
            utils.generate_setup_py(setup_py, version)
    else:
        expected_setup_py = resources.get_resource(expected)
        actual = utils.generate_setup_py(setup_py, version)
        assert expected_setup_py == actual


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


def test_extract_version_from_setup_py_double_quotes():

    expected = '0.1.0'

    actual = utils.extract_version_from_setup_py("""
setup(
    version="{}",
)

    """.format(expected))

    assert actual == expected


def test_extract_version_from_setup_py_single_quotes():

    expected = '0.1.0'

    actual = utils.extract_version_from_setup_py("""
setup(
    version='{}',
)

    """.format(expected))

    assert actual == expected


def test_extract_version_from_setup_py_no_match():

    with pytest.raises(exceptions.RegexMatchFailureException):
        utils.extract_version_from_setup_py("""
setup(
    hello='world',
)
    
""")


def test_get_python_executable():

    python_path = utils.get_python_executable('python')

    assert os.path.abspath(sys.exec_prefix) in python_path


def test_get_python_executable_from_pyinstaller():

    try:
        setattr(sys, '_MEIPASS', 'mock')
        with pytest.raises(RuntimeError) as e:
            utils.get_python_executable('python')
        assert 'Executables are not supported' in str(e)
    finally:
        delattr(sys, '_MEIPASS')


def test_get_python_executable_from_pyinstaller_with_exec_host():

    try:
        setattr(sys, '_MEIPASS', 'mock')
        python_path = utils.get_python_executable('python', exec_home=sys.exec_prefix)
        assert os.path.abspath(sys.exec_prefix) in python_path
    finally:
        delattr(sys, '_MEIPASS')


def test_which_python():

    python_path = utils.which('python')

    assert os.path.abspath(sys.exec_prefix).lower() in python_path.lower()


def test_extract_links_multiple_matches():

    links = utils.extract_links('This commit closes issues #21 and #24')

    assert links == [21, 24]


def test_extract_links_no_matches():

    links = utils.extract_links('This commit doesnt close any issue')

    assert links == []


@pytest.mark.linux
def test_which_ls():

    ls_path = utils.which('ls')

    assert 'ls' in ls_path


def test_which_non_existent():

    poop = utils.which('poop')

    assert poop is None
