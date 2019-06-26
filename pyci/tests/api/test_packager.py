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
from pyci.tests import conftest
from pyci.tests import  resources as test_resources


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


def test_default_target_dir(pack):

    target_dir = Packager.create(path=pack.api.repo_dir).target_dir

    assert os.getcwd() == target_dir


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


def test_wheel(pyci):

    py_version = 'py3' if utils.is_python_3() else 'py2'

    expected = 'py_ci-{}-{}-none-any.whl'.format(pyci.version, py_version)

    assert expected in pyci.wheel_path


def test_wheel_not_python_project(pack):

    os.remove(os.path.join(pack.api.repo_dir, 'setup.py'))

    with pytest.raises(exceptions.NotPythonProjectException):
        pack.api.wheel()


def test_wheel_options(pack, repo_version, temp_dir):

    pack.api.target_dir = temp_dir

    expected = os.path.join(temp_dir, 'py_ci-{0}-py2.py3-none-any.whl'.format(repo_version))

    actual = pack.api.wheel(universal=True)

    assert expected == actual


def test_wheel_file_exists(pack, repo_version):

    py_version = 'py3' if utils.is_python_3() else 'py2'

    expected = os.path.join(os.getcwd(), 'py_ci-{}-{}-none-any.whl'
                            .format(repo_version, py_version))

    with open(expected, 'w') as stream:
        stream.write('package')

    with pytest.raises(exceptions.FileExistException):
        pack.api.wheel()


def test_binary(runner, pyci):

    expected = 'py-ci-{0}-{1}'.format(platform.machine(), platform.system())

    if platform.system() == 'Windows':
        expected = '{0}.exe'.format(expected)

    assert expected in pyci.binary_path

    # lets make sure the binary actually works
    runner.run('{0} --help'.format(pyci.binary_path))


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


def test_binary_only_requirements_txt(runner, temp_dir):

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'only-requirements'))

    packager = Packager.create(path=repo_path, target_dir=temp_dir)

    binary_path = packager.binary(name='only-requirements', entrypoint='main.py')

    # lets make sure the binary actually works
    assert runner.run(binary_path).std_out == 'Hello from requirements'


def test_binary_no_requirements(runner, temp_dir):

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-requirements'))

    packager = Packager.create(path=repo_path, target_dir=temp_dir)

    binary_path = packager.binary(name='no-requirements', entrypoint='main.py')

    result = runner.run(binary_path, exit_on_failure=False)

    assert 'No module' in result.std_err
    assert 'six' in result.std_err


def test_binary_file_exists(pack):

    expected = os.path.join(os.getcwd(), 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected = '{0}.exe'.format(expected)

    with open(expected, 'w') as stream:
        stream.write('package')

    with pytest.raises(exceptions.FileExistException):
        pack.api.binary(entrypoint=conftest.SPEC_FILE)


def test_binary_default_entrypoint_doesnt_exist(pack):

    os.remove(os.path.join(pack.api.repo_dir, conftest.SPEC_FILE))
    os.remove(os.path.join(pack.api.repo_dir, 'pyci', 'shell', 'main.py'))

    with pytest.raises(exceptions.DefaultEntrypointNotFoundException):
        pack.api.binary()


def test_binary_entrypoint_doesnt_exist(pack):

    with pytest.raises(exceptions.EntrypointNotFoundException):
        pack.api.binary(entrypoint='doesnt-exist')


def test_exei_no_binary_path(pack, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    with pytest.raises(exceptions.InvalidArgumentsException):
        pack.api.exei(binary_path=None)


def test_exei_binary_path_doesnt_exist(pack, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    with pytest.raises(exceptions.BinaryFileDoesntExistException):
        pack.api.exei(binary_path='doesnt-exist')


def test_exei_invalid_version_string(pack, mocker, temp_dir):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(temp_dir, 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    with pytest.raises(exceptions.InvalidNSISVersionException):
        pack.api.exei(binary_package, version='1.2')


def test_exei_license_not_found(pack, mocker, temp_dir):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(temp_dir, 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    with pytest.raises(exceptions.LicenseNotFoundException):
        pack.api.exei(binary_package, version='1.0.0.0', license_path='doesnt-exist')


def test_exei_destination_exists(pack, mocker, repo_path, temp_dir):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(temp_dir, 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    destination = os.path.join(temp_dir, 'installer.exe')

    with open(destination, 'w') as f:
        f.write('dummy')

    with pytest.raises(exceptions.FileExistException):
        pack.api.exei(binary_package,
                      version='1.0.0.0',
                      license_path=os.path.join(repo_path, 'LICENSE'),
                      output=destination)


def test_exei_target_directory_doesnt_exists(pack, mocker, repo_path, temp_dir):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(temp_dir, 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    destination = os.path.join(temp_dir, 'doesnt-exist', 'installer.exe')

    with pytest.raises(exceptions.DirectoryDoesntExistException):
        pack.api.exei(binary_package,
                      version='1.0.0.0',
                      license_path=os.path.join(repo_path, 'LICENSE'),
                      output=destination)


@pytest.mark.linux
def test_exei_on_linux(pack):

    with pytest.raises(exceptions.WrongPlatformException):
        pack.api.exei(binary_path='doesnt-exist')


@pytest.mark.windows
def test_exei(pack, pyci):

    basename = os.path.basename(pyci.binary_path)
    name = basename.replace('.exe', '')

    pack.api.exei(pyci.binary_path)

    expected = os.path.join(os.getcwd(), '{}-installer.exe'.format(name))

    assert os.path.exists(expected)
