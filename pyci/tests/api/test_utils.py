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

import tempfile

import pytest

import pyci
import pyci.api
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
            pyci.api.utils.generate_setup_py(setup_py, version)
    else:
        expected_setup_py = resources.get_resource(expected)
        actual = pyci.api.utils.generate_setup_py(setup_py, version)
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
