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
import platform
import shutil

import pytest

from pyci.api import utils


def test_binary(pack, runner):

    result = pack.run('binary')

    expected_package_path = os.path.join(os.getcwd(), 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected_package_path = '{0}.exe'.format(expected_package_path)

    expected_output = '* Binary package created: {}'.format(expected_package_path)

    assert expected_output in result.std_out
    assert os.path.exists(expected_package_path)

    # lets make sure the binary actually works
    runner.run('{0} --help'.format(expected_package_path))


def test_binary_options(pack, temp_dir, request, runner):

    pack.api.target_dir = temp_dir

    custom_main = os.path.join('pyci', 'shell', 'custom_main.py')
    with open(os.path.join(pack.api.repo_dir, custom_main), 'w') as stream:
        stream.write('''
import six

if __name__ == '__main__':
    six.print_('It works!')        
''')

    name = request.node.name

    result = pack.run('binary --name {} --entrypoint {}'.format(name, custom_main))

    expected_package_path = os.path.join(temp_dir, '{}-{}-{}'
                                         .format(name, platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected_package_path = '{0}.exe'.format(expected_package_path)

    expected_output = '* Binary package created: {}'.format(expected_package_path)

    assert expected_output in result.std_out
    assert os.path.exists(expected_package_path)

    # lets make sure the binary actually works
    assert runner.run(expected_package_path).std_out == 'It works!'


def test_binary_from_binary(pack):

    result = pack.run('binary', binary=True, catch_exceptions=True)

    expected_package_path = os.path.join(os.getcwd(), 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected_package_path = '{0}.exe'.format(expected_package_path)

    expected_output = 'Creating a binary package is not supported when ' \
                      'running from within a binary'

    assert expected_output in result.std_out
    assert not os.path.exists(expected_package_path)


def test_binary_file_exists(pack):

    expected_package_path = os.path.join(os.getcwd(), 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected_package_path = '{0}.exe'.format(expected_package_path)

    with open(expected_package_path, 'w') as stream:
        stream.write('package')

    result = pack.run('binary', catch_exceptions=True)

    expected_output = 'Binary already exists: {}'.format(expected_package_path)
    expected_possible_solution = 'Delete/Move the binary and try again'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out


def test_binary_default_entrypoint_doesnt_exist(pack):

    repo_dir = pack.api.repo_dir

    shutil.move(src=os.path.join(repo_dir, 'pyci', 'shell', 'main.py'),
                dst=os.path.join(repo_dir, 'pyci', 'shell', 'main2.py'))

    shutil.move(src=os.path.join(repo_dir, 'pyci.spec'),
                dst=os.path.join(repo_dir, 'pyci2.spec'))

    result = pack.run('binary', catch_exceptions=True)

    expected_output = 'Failed locating an entrypoint file'
    expected_possible_solutions = [
        'Create an entrypoint file in one of the following paths',
        'Use --entrypoint to specify a custom entrypoint path'
    ]

    assert expected_output in result.std_out
    for expected_possible_solution in expected_possible_solutions:
        assert expected_possible_solution in result.std_out


def test_binary_entrypoint_doesnt_exist(pack):

    result = pack.run('binary --entrypoint doesnt-exist', catch_exceptions=True)

    expected_output = 'The entrypoint path you specified does not exist: doesnt-exist'

    assert expected_output in result.std_out


@pytest.mark.parametrize("binary", [False, True])
def test_wheel(pack, binary):

    result = pack.run('wheel', binary=binary)

    py = 'py3' if utils.is_python_3() else 'py2'

    expected_path = os.path.join(os.getcwd(), 'py_ci-{}-{}-none-any.whl'.format(pack.version, py))

    expected_output = '* Wheel package created: {}'.format(expected_path)

    assert expected_output in result.std_out
    assert os.path.exists(expected_path)


@pytest.mark.parametrize("binary", [False, True])
def test_wheel_options(pack, temp_dir, binary):

    pack.api.target_dir = temp_dir

    result = pack.run('wheel --universal', binary=binary)

    expected_path = os.path.join(temp_dir, 'py_ci-{0}-py2.py3-none-any.whl'.format(pack.version))

    expected_output = '* Wheel package created: {}'.format(expected_path)

    assert expected_output in result.std_out
    assert os.path.exists(expected_path)


@pytest.mark.parametrize("binary", [False, True])
def test_wheel_file_exists(pack, binary):

    expected_path = os.path.join(os.getcwd(), 'py_ci-{}-py2.py3-none-any.whl'
                                 .format(pack.version))

    with open(expected_path, 'w') as stream:
        stream.write('package')

    result = pack.run('wheel --universal', catch_exceptions=True, binary=binary)

    expected_output = 'Wheel already exists: {}'.format(expected_path)
    expected_possible_solution = 'Delete/Move the package and try again'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out
