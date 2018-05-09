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


try:
    # python2
    from mock import MagicMock
except ImportError:
    # noinspection PyUnresolvedReferences
    # python3
    from unittest.mock import MagicMock

from pyci.api import exceptions


def test_binary(patched_pack, capture):

    patched_pack.packager.binary = MagicMock(return_value='path')

    patched_pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir')

    expected_output = 'Binary package created: path'

    assert expected_output == capture.records[1].msg
    patched_pack.packager.binary.assert_called_once_with(
        name='name',
        entrypoint='entrypoint',
        target_dir='target-dir')


def test_binary_failed(patched_pack, capture):

    exception = exceptions.ApiException('error')
    patched_pack.packager.binary = MagicMock(side_effect=exception)

    patched_pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir',
                     catch_exceptions=True)

    expected_output = 'Failed creating binary package: error'

    assert expected_output in capture.records[2].msg
    patched_pack.packager.binary.assert_called_once_with(
        name='name',
        entrypoint='entrypoint',
        target_dir='target-dir')


def test_binary_file_exists(patched_pack, capture):

    exception = exceptions.FileExistException(path='path')
    patched_pack.packager.binary = MagicMock(side_effect=exception)

    patched_pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir',
                     catch_exceptions=True)

    expected_output = 'Failed creating binary package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the file and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_pack.packager.binary.assert_called_once_with(
        name='name',
        entrypoint='entrypoint',
        target_dir='target-dir')


def test_binary_file_is_a_directory(patched_pack, capture):

    exception = exceptions.FileIsADirectoryException(path='path')
    patched_pack.packager.binary = MagicMock(side_effect=exception)

    patched_pack.run('binary --name name --entrypoint entrypoint --target-dir target-dir',
                     catch_exceptions=True)

    expected_output = 'Failed creating binary package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the directory and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_pack.packager.binary.assert_called_once_with(
        name='name',
        entrypoint='entrypoint',
        target_dir='target-dir')


def test_wheel(patched_pack, capture):

    patched_pack.packager.wheel = MagicMock(return_value='path')

    patched_pack.run('wheel --universal --target-dir target-dir')

    expected_output = 'Wheel package created: path'

    assert expected_output == capture.records[1].msg
    patched_pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')


def test_wheel_failed(patched_pack, capture):

    exception = exceptions.ApiException('error')
    patched_pack.packager.wheel = MagicMock(side_effect=exception)

    patched_pack.run('wheel --universal --target-dir target-dir', catch_exceptions=True)

    expected_output = 'Failed creating wheel package: error'

    assert expected_output in capture.records[2].msg
    patched_pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')


def test_wheel_file_exists(patched_pack, capture):

    exception = exceptions.FileExistException(path='path')
    patched_pack.packager.wheel = MagicMock(side_effect=exception)

    patched_pack.run('wheel --universal --target-dir target-dir', catch_exceptions=True)

    expected_output = 'Failed creating wheel package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the file and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')


def test_wheel_file_is_a_directory(patched_pack, capture):

    exception = exceptions.FileIsADirectoryException(path='path')
    patched_pack.packager.wheel = MagicMock(side_effect=exception)

    patched_pack.run('wheel --universal --target-dir target-dir', catch_exceptions=True)

    expected_output = 'Failed creating wheel package: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the directory and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_pack.packager.wheel.assert_called_once_with(universal=True, target_dir='target-dir')
