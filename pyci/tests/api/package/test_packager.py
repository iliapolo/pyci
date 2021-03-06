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
from pyci.api.package.packager import Packager
from pyci.api import utils
from pyci.tests import conftest
from pyci.tests import resources as test_resources


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


def test_target_dir_doesnt_exist(repo_path):

    with pytest.raises(exceptions.DirectoryDoesntExistException):
        Packager.create(target_dir='doesnt-exist',
                        path=repo_path)


def test_sha_doesnt_exist():

    with pytest.raises(exceptions.DownloadFailedException):
        Packager.create(repo='iliapolo/pyci', sha='doesnt-exist')


def test_wheel(pyci):

    py_version = 'py3' if utils.is_python_3() else 'py2'

    expected = 'py_ci-{}-{}-none-any.whl'.format(pyci.version, py_version)

    assert expected in pyci.wheel_path


def test_wheel_no_setup_py(pack, repo_path):

    os.remove(os.path.join(repo_path, 'setup.py'))

    with pytest.raises(exceptions.SetupPyNotFoundException):
        pack.api.wheel()


def test_wheel_no_python_py_installer(pack, mocker):

    mocker.patch('pyci.api.utils.is_pyinstaller')

    def _which(*_):
        return None

    mocker.patch('pyci.api.utils.which', side_effect=_which)

    with pytest.raises(exceptions.PythonNotFoundException):
        pack.api.wheel()


def test_wheel_no_python(pack, mocker):

    def _get_python_executable(*_):
        return None

    mocker.patch('pyci.api.utils.get_python_executable', side_effect=_get_python_executable)

    with pytest.raises(exceptions.PythonNotFoundException):
        pack.api.wheel()


def test_wheel_options(pack, repo_version):

    expected = os.path.join(os.getcwd(), 'py_ci-{0}-py2.py3-none-any.whl'.format(repo_version))

    actual = pack.api.wheel(universal=True)

    assert expected == actual


def test_wheel_file_exists(pack, repo_version):

    py_version = 'py3' if utils.is_python_3() else 'py2'

    expected = os.path.join(os.getcwd(), 'py_ci-{}-{}-none-any.whl'
                            .format(repo_version, py_version))

    with open(expected, 'w') as stream:
        stream.write('package')

    with pytest.raises(exceptions.WheelExistsException):
        pack.api.wheel()


def test_binary(runner, pyci):

    expected = 'py-ci-{0}-{1}'.format(platform.machine(), platform.system())

    if platform.system() == 'Windows':
        expected = '{0}.exe'.format(expected)

    assert expected in pyci.binary_path

    # lets make sure the binary actually works
    runner.run('{0} --help'.format(pyci.binary_path))


def test_binary_no_setup_py(pack, repo_path):

    os.remove(os.path.join(repo_path, 'setup.py'))

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        pack.api.binary()

    assert isinstance(e.value.reason, exceptions.SetupPyNotFoundException)


def test_binary_no_python_py_installer(pack, mocker):

    mocker.patch('pyci.api.utils.is_pyinstaller')

    def _which(*_):
        return None

    mocker.patch('pyci.api.utils.which', side_effect=_which)

    with pytest.raises(exceptions.PythonNotFoundException):
        pack.api.binary()


def test_binary_no_python(pack, mocker):

    def _get_python_executable(*_):
        return None

    mocker.patch('pyci.api.utils.get_python_executable', side_effect=_get_python_executable)

    with pytest.raises(exceptions.PythonNotFoundException):
        pack.api.binary()


def test_binary_auto_detect_entrypoint(runner):

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'with-entrypoint'))

    packager = Packager.create(path=repo_path)

    binary_path = packager.binary()

    # lets make sure the binary actually works
    assert runner.run(binary_path).std_out == 'Hello from entrypoint'


def test_binary_no_default_name_no_basename():

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-name'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        packager.binary()

    assert e.value.argument == 'name'


def test_binary_custom_entrypoint(pack, request, runner, repo_path):

    custom_main = os.path.join('pyci', 'shell', 'custom_main.py')
    with open(os.path.join(repo_path, custom_main), 'w') as stream:
        stream.write('''
import six

if __name__ == '__main__':
    six.print_('It works!')        
''')

    name = request.node.name

    expected = os.path.join(os.getcwd(), '{}-{}-{}'
                            .format(name, platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected = '{}.exe'.format(expected)

    actual = pack.api.binary(base_name=name,
                             entrypoint=custom_main)

    assert expected == actual

    # lets make sure the binary actually works
    assert runner.run(actual).std_out == 'It works!'


def test_binary_only_requirements_txt(runner):

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'only-requirements'))

    packager = Packager.create(path=repo_path)

    binary_path = packager.binary(base_name='only-requirements', entrypoint='main.py')

    # lets make sure the binary actually works
    assert runner.run(binary_path).std_out == 'Hello from requirements'


def test_binary_no_requirements(runner):

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-requirements'))

    packager = Packager.create(path=repo_path)

    binary_path = packager.binary(base_name='no-requirements', entrypoint='main.py')

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

    with pytest.raises(exceptions.BinaryExistsException):
        pack.api.binary(entrypoint=conftest.SPEC_FILE)


def test_binary_console_script_not_found(pack, repo_path):

    os.remove(os.path.join(repo_path, 'pyci', 'shell', 'main.py'))

    with pytest.raises(exceptions.ConsoleScriptNotFoundException):
        pack.api.binary()


def test_binary_no_default_entrypoint():

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-entrypoint'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        packager.binary()

    assert e.value.argument == 'entry_points'


def test_binary_multiple_default_entrypoints():

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'multiple-entrypoints'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.MultipleDefaultEntrypointsFoundException):
        packager.binary()


def test_binary_entrypoint_doesnt_exist(pack):

    with pytest.raises(exceptions.EntrypointNotFoundException):
        pack.api.binary(entrypoint='doesnt-exist')


def test_nsis_no_binary_path(pack, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    with pytest.raises(exceptions.InvalidArgumentsException):
        pack.api.nsis(binary_path=None)


def test_nsis_binary_path_doesnt_exist(pack, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    with pytest.raises(exceptions.BinaryDoesntExistException):
        pack.api.nsis(binary_path='doesnt-exist')


def test_nsis_invalid_version_string(pack, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(os.getcwd(), 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    with pytest.raises(exceptions.InvalidNSISVersionException):
        pack.api.nsis(binary_package, version='1.2')


def test_nsis_license_not_found(pack, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(os.getcwd(), 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    with pytest.raises(exceptions.LicenseNotFoundException):
        pack.api.nsis(binary_package, version='1.0.0.0', license_path='doesnt-exist')


def test_nsis_no_default_author(temp_file, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-author'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        packager.nsis(temp_file)

    assert e.value.argument == 'author'


def test_nsis_no_default_description(temp_file, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-description'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        packager.nsis(temp_file)

    assert e.value.argument == 'description'


def test_nsis_no_default_url(temp_file, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-url'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        packager.nsis(temp_file)

    assert e.value.argument == 'url'


def test_nsis_no_default_license(temp_file, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-license'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        packager.nsis(temp_file)

    assert e.value.argument == 'license'


def test_nsis_no_default_version(temp_file, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    repo_path = test_resources.get_resource_path(os.path.join('repos', 'no-version'))

    packager = Packager.create(path=repo_path)

    with pytest.raises(exceptions.FailedDetectingPackageMetadataException) as e:
        packager.nsis(temp_file)

    assert e.value.argument == 'version'


def test_nsis_destination_exists(pack, mocker, repo_path):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(os.getcwd(), 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    destination = os.path.join(os.getcwd(), 'installer.exe')

    with open(destination, 'w') as f:
        f.write('dummy')

    with pytest.raises(exceptions.FileExistException):
        pack.api.nsis(binary_package,
                      version='1.0.0.0',
                      license_path=os.path.join(repo_path, 'LICENSE'),
                      output=destination)


def test_nsis_target_directory_doesnt_exists(pack, mocker, repo_path):

    mocker.patch('pyci.api.utils.is_windows')

    binary_package = os.path.join(os.getcwd(), 'binary.exe')

    with open(binary_package, 'w') as f:
        f.write('dummy')

    destination = os.path.join(os.getcwd(), 'doesnt-exist', 'installer.exe')

    with pytest.raises(exceptions.DirectoryDoesntExistException):
        pack.api.nsis(binary_package,
                      version='1.0.0.0',
                      license_path=os.path.join(repo_path, 'LICENSE'),
                      output=destination)


@pytest.mark.linux
def test_nsis_on_linux(pack):

    with pytest.raises(exceptions.WrongPlatformException):
        pack.api.nsis(binary_path='doesnt-exist')


@pytest.mark.windows
def test_nsis(pack, pyci):

    basename = os.path.basename(pyci.binary_path)
    name = basename.replace('.exe', '')

    pack.api.nsis(pyci.binary_path)

    expected = os.path.join(os.getcwd(), '{}-installer.exe'.format(name))

    assert os.path.exists(expected)
