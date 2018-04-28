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

# noinspection PyPackageRequirements
import pytest

# noinspection PyPackageRequirements
from mock import MagicMock

from pyci.api import exceptions
from pyci.tests.shell import Runner


@pytest.fixture(name='pack')
def _pack(temp_dir, mocker):

    packager_mock = MagicMock()

    mocker.patch(target='pyci.api.packager.new', new=MagicMock(return_value=packager_mock))

    # pylint: disable=too-few-public-methods
    class PackSubCommand(Runner):

        def __init__(self, packager):
            super(PackSubCommand, self).__init__()
            self.packager = packager

        def run(self, command, catch_exceptions=False):

            command = 'pack --sha sha --repo iliapolo/pyci-guinea-pig {}'.format(command)

            return super(PackSubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield PackSubCommand(packager_mock)
    finally:
        os.chdir(cwd)


def test_binary(pack, capture):

    pack.packager.binary = MagicMock(return_value='path')

    pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir')

    expected_output = 'Binary package created: path'

    assert expected_output == capture.records[1].msg
    pack.packager.binary.assert_called_once_with(name='name',
                                                 entrypoint='entrypoint',
                                                 target_dir='target-dir')


def test_binary_failed(pack, capture):

    exception = exceptions.ApiException('error')
    pack.packager.binary = MagicMock(side_effect=exception)

    pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir',
             catch_exceptions=True)

    expected_output = 'Failed creating binary package: error'

    assert expected_output in capture.records[2].msg
    pack.packager.binary.assert_called_once_with(name='name',
                                                 entrypoint='entrypoint',
                                                 target_dir='target-dir')


def test_binary_file_exists(pack, capture):

    exception = exceptions.FileExistException(path='path')
    pack.packager.binary = MagicMock(side_effect=exception)

    pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir',
             catch_exceptions=True)

    expected_output = 'Failed creating binary package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the file and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    pack.packager.binary.assert_called_once_with(name='name',
                                                 entrypoint='entrypoint',
                                                 target_dir='target-dir')


def test_binary_file_is_a_directory(pack, capture):

    exception = exceptions.FileIsADirectoryException(path='path')
    pack.packager.binary = MagicMock(side_effect=exception)

    pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir',
             catch_exceptions=True)

    expected_output = 'Failed creating binary package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the directory and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    pack.packager.binary.assert_called_once_with(name='name',
                                                 entrypoint='entrypoint',
                                                 target_dir='target-dir')


def test_wheel(pack, capture):

    pack.packager.wheel = MagicMock(return_value='path')

    pack.run('wheel --universal --target-dir target-dir')

    expected_output = 'Wheel package created: path'

    assert expected_output == capture.records[1].msg
    pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')


def test_wheel_failed(pack, capture):

    exception = exceptions.ApiException('error')
    pack.packager.wheel = MagicMock(side_effect=exception)

    pack.run('wheel --universal --target-dir target-dir', catch_exceptions=True)

    expected_output = 'Failed creating wheel package: error'

    assert expected_output in capture.records[2].msg
    pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')


def test_wheel_file_exists(pack, capture):

    exception = exceptions.FileExistException(path='path')
    pack.packager.wheel = MagicMock(side_effect=exception)

    pack.run('wheel --universal --target-dir target-dir', catch_exceptions=True)

    expected_output = 'Failed creating wheel package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the file and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')


def test_wheel_file_is_a_directory(pack, capture):

    exception = exceptions.FileIsADirectoryException(path='path')
    pack.packager.wheel = MagicMock(side_effect=exception)

    pack.run('wheel --universal --target-dir target-dir', catch_exceptions=True)

    expected_output = 'Failed creating wheel package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the directory and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')
