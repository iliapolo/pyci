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
import pytest

from pyci.api import exceptions
from pyci.api.packager import Packager
from pyci.api import utils


def test_sha_and_not_repo():

    with pytest.raises(exceptions.InvalidArgumentsException):
        Packager.create(sha='sha')


def test_sha_and_path():

    with pytest.raises(exceptions.InvalidArgumentsException):
        Packager.create(repo='repo', sha='sha', path='path')


def test_repo_and_path():

    with pytest.raises(exceptions.InvalidArgumentsException):
        Packager.create(path='path', repo='repo')


def test_not_sha_and_not_path():

    with pytest.raises(exceptions.InvalidArgumentsException):
        Packager.create()


def test_path_doesnt_exist():

    with pytest.raises(exceptions.DirectoryDoesntExistException):
        Packager.create(path='doesnt-exist')


def test_target_dir_doesnt_exist(pack):

    with pytest.raises(exceptions.DirectoryDoesntExistException):
        Packager.create(target_dir='doesnt-exist',
                        path=pack.api.repo_dir)


def test_set_target_dir_doesnt_exist(pack):

    with pytest.raises(exceptions.DirectoryDoesntExistException):
        pack.api.target_dir = 'doesnt-exist'


def test_repo_dir_sha():

    packager = Packager.create(repo='iliapolo/pyci', sha='release')

    expected_setup_py_file = os.path.join(packager.repo_dir, 'setup.py')

    assert os.path.exists(expected_setup_py_file)


def test_sha_doesnt_exist():

    with pytest.raises(exceptions.DownloadFailedException):
        Packager.create(repo='iliapolo/pyci', sha='doesnt-exist')


def test_wheel(pack):

    py_version = 'py3' if utils.is_python_3() else 'py2'

    expected = os.path.join(os.getcwd(), 'py_ci-{}-{}-none-any.whl'
                            .format(pack.version, py_version))

    actual = pack.api.wheel()

    assert expected == actual


def test_wheel_not_python_project(pack):

    os.remove(os.path.join(pack.api.repo_dir, 'setup.py'))

    with pytest.raises(exceptions.NotPythonProjectException):
        pack.api.wheel()


def test_wheel_options(pack, temp_dir):

    pack.api.target_dir = temp_dir

    expected = os.path.join(temp_dir, 'py_ci-{0}-py2.py3-none-any.whl'.format(pack.version))

    actual = pack.api.wheel(universal=True)

    assert expected == actual


def test_wheel_file_exists(pack):

    py_version = 'py3' if utils.is_python_3() else 'py2'

    expected = os.path.join(os.getcwd(), 'py_ci-{}-{}-none-any.whl'
                            .format(pack.version, py_version))

    with open(expected, 'w') as stream:
        stream.write('package')

    with pytest.raises(exceptions.FileExistException):
        pack.api.wheel()


def test_binary(pack, runner):

    expected = os.path.join(os.getcwd(), 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected = '{0}.exe'.format(expected)

    actual = pack.api.binary(entrypoint='pyci.spec')

    assert expected == actual

    # lets make sure the binary actually works
    runner.run('{0} --help'.format(actual))


def test_binary_options(pack, request, runner, temp_dir):

    pack.api.target_dir = temp_dir

    custom_main = os.path.join('pyci', 'shell', 'custom_main.py')
    with open(os.path.join(pack.api.repo_dir, custom_main), 'w') as stream:
        stream.write('''
import six

if __name__ == '__main__':
    six.print_('It works!')        
''')

    name = request.node.name

    expected = os.path.join(temp_dir, '{}-{}-{}'
                            .format(name, platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected = '{}.exe'.format(expected)

    actual = pack.api.binary(name=name,
                             entrypoint=custom_main)

    assert expected == actual

    # lets make sure the binary actually works
    assert runner.run(actual).std_out == 'It works!'


def test_binary_file_exists(pack):

    expected = os.path.join(os.getcwd(), 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected = '{0}.exe'.format(expected)

    with open(expected, 'w') as stream:
        stream.write('package')

    with pytest.raises(exceptions.FileExistException):
        pack.api.binary(entrypoint='pyci.spec')


def test_binary_default_entrypoint_doesnt_exist(pack):

    os.remove(os.path.join(pack.api.repo_dir, 'pyci.spec'))
    os.remove(os.path.join(pack.api.repo_dir, 'pyci', 'shell', 'main.py'))

    with pytest.raises(exceptions.DefaultEntrypointNotFoundException):
        pack.api.binary()


def test_binary_entrypoint_doesnt_exist(pack):

    with pytest.raises(exceptions.EntrypointNotFoundException):
        pack.api.binary(entrypoint='doesnt-exist')
