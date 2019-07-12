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

from pyci.api.package.packager import Packager
from pyci.api import utils
from pyci.api import exceptions
from pyci.tests import distros
from pyci.tests import utils as test_utils
from pyci.tests import conftest


def test_binary(pack, runner):

    pack.run('binary --entrypoint {}'.format(conftest.SPEC_FILE), binary=True)

    expected_package_path = os.path.join(os.getcwd(), 'py-ci-{}-{}'.format(platform.machine(), platform.system()))

    if utils.is_windows():
        expected_package_path = '{0}.exe'.format(expected_package_path)

    assert os.path.exists(expected_package_path)

    # lets make sure the binary actually works
    assert runner.run(expected_package_path)


def test_binary_options(pack, mocker):

    mocker.patch(target='pyci.api.package.packager.Packager.binary', new=test_utils.MagicMock())

    pack.run('binary '
             '--base-name name '
             '--entrypoint entrypoint '
             '--pyinstaller-version 3.4')

    # noinspection PyUnresolvedReferences
    Packager.binary.assert_called_once_with(base_name='name',  # pylint: disable=no-member
                                            entrypoint='entrypoint',
                                            pyinstaller_version='3.4')


def test_binary_file_exists(pack, mocker):

    def _binary(**__):
        raise exceptions.BinaryExistsException(path='path')

    mocker.patch(target='pyci.api.package.packager.Packager.binary', side_effect=_binary)

    result = pack.run('binary', catch_exceptions=True)

    expected_output = 'Binary exists'
    expected_possible_solution = 'Delete/Move the binary and try again'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out


def test_binary_no_setup_py_file(pack, mocker, repo_path):

    def _binary(**__):

        raise exceptions.FailedDetectingPackageMetadataException(
            argument='entry_points',
            reason=exceptions.SetupPyNotFoundException(repo=repo_path))

    mocker.patch(target='pyci.api.package.packager.Packager.binary', side_effect=_binary)

    result = pack.run('binary', catch_exceptions=True)

    expected_output = 'Failed detecting entry_points'
    expected_possible_solutions = [
        'Create a setup.py file and follow standard python packaging structure',
        'Use --entrypoint to specify a custom entrypoint'
    ]

    assert expected_output in result.std_out
    for expected_possible_solution in expected_possible_solutions:
        assert expected_possible_solution in result.std_out


def test_binary_missing_entry_points_from_setup_py_file(pack, mocker, repo_path):

    def _binary(**__):

        raise exceptions.FailedDetectingPackageMetadataException(
            argument='entry_points',
            reason=exceptions.MissingSetupPyArgumentException(repo=repo_path, argument='entry_points'))

    mocker.patch(target='pyci.api.package.packager.Packager.binary', side_effect=_binary)

    result = pack.run('binary', catch_exceptions=True)

    expected_output = 'Failed detecting entry_points'
    expected_possible_solutions = [
        "Add the 'entry_points' argument to your setup.py file",
        'Use --entrypoint to specify a custom entrypoint'
    ]

    assert expected_output in result.std_out
    for expected_possible_solution in expected_possible_solutions:
        assert expected_possible_solution in result.std_out


def test_binary_console_script_not_found(pack, repo_path, mocker):

    def _binary(**__):

        raise exceptions.ConsoleScriptNotFoundException(repo=repo_path, script='script')

    mocker.patch(target='pyci.api.package.packager.Packager.binary', side_effect=_binary)

    result = pack.run('binary', catch_exceptions=True)

    expected_output = 'Console script not found in repo'
    expected_possible_solutions = [
        "Fix the 'entry_points' argument in setup.py to point to an existing script",
        'Use --entrypoint to specify a different script than the one in setup.py (discouraged)'
    ]

    assert expected_output in result.std_out
    for expected_possible_solution in expected_possible_solutions:
        assert expected_possible_solution in result.std_out


def test_wheel(pack, repo_version):

    result = pack.run('wheel --universal', binary=True)

    expected_path = os.path.join(os.getcwd(), 'py_ci-{0}-py2.py3-none-any.whl'.format(repo_version))

    expected_output = 'Wheel package created: {}'.format(expected_path)

    assert expected_output in result.std_out
    assert os.path.exists(expected_path)


def test_wheel_options(pack, mocker):

    mocker.patch(target='pyci.api.package.packager.Packager.wheel', new=test_utils.MagicMock())

    pack.run('wheel --universal --wheel-version 0.33.4')

    # noinspection PyUnresolvedReferences
    Packager.wheel.assert_called_once_with(universal=True,  # pylint: disable=no-member
                                           wheel_version='0.33.4')


def test_wheel_file_exists(pack, mocker):

    def _wheel(**__):
        raise exceptions.WheelExistsException(path='path')

    mocker.patch(target='pyci.api.package.packager.Packager.wheel', side_effect=_wheel)

    result = pack.run('wheel', catch_exceptions=True)

    expected_output = 'Wheel exists'
    expected_possible_solution = 'Delete/Move the package and try again'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out


def test_wheel_no_setup_py(pack, repo_path, mocker):

    def _wheel(**__):
        raise exceptions.SetupPyNotFoundException(repo=repo_path)

    mocker.patch(target='pyci.api.package.packager.Packager.wheel', side_effect=_wheel)

    result = pack.run('wheel', catch_exceptions=True)

    expected_output = 'does not contain a setup.py'
    expected_possible_solution = 'Create a setup.py file'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out


@pytest.mark.windows
def test_nsis(pack):

    pack.run('nsis', binary=True)

    expected_package_path = os.path.join(os.getcwd(), 'py-ci-{}-{}-installer.exe'
                                         .format(platform.machine(), platform.system()))

    assert os.path.exists(expected_package_path)


def test_nsis_options(pack, mocker):

    mocker.patch('pyci.api.utils.is_windows')

    mocker.patch(target='pyci.api.package.packager.Packager.nsis', new=test_utils.MagicMock())

    pack.run('nsis '
             '--binary-path binary-path '
             '--version version '
             '--output output '
             '--author author '
             '--url url '
             '--copyright copyright '
             '--license license')

    # noinspection PyUnresolvedReferences
    Packager.nsis.assert_called_once_with('binary-path',  # pylint: disable=no-member
                                          version='version',
                                          output='output',
                                          author='author',
                                          url='url',
                                          copyright_string='copyright',
                                          license_path='license')


def test_nsis_no_setup_py(pack, repo_path, mocker):

    def _nsis(*_, **__):

        raise exceptions.FailedDetectingPackageMetadataException(
            argument='something',
            reason=exceptions.SetupPyNotFoundException(repo=repo_path))

    mocker.patch('pyci.api.utils.is_windows')

    mocker.patch(target='pyci.api.package.packager.Packager.nsis', side_effect=_nsis)

    result = pack.run('nsis --binary-path binary-path', catch_exceptions=True)

    expected_output = 'does not contain a setup.py'
    expected_possible_solution = 'Create a setup.py file'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out


def test_nsis_missing_argument_from_setup_py(pack, repo_path, mocker):

    def _nsis(*_, **__):

        raise exceptions.FailedDetectingPackageMetadataException(
            argument='something',
            reason=exceptions.MissingSetupPyArgumentException(repo=repo_path, argument='something'))

    mocker.patch('pyci.api.utils.is_windows')

    mocker.patch(target='pyci.api.package.packager.Packager.nsis', side_effect=_nsis)

    result = pack.run('nsis --binary-path binary-path', catch_exceptions=True)

    expected_output = 'Failed detecting something'
    expected_possible_solutions = [
        "Add the 'something' argument to your setup.py file",
        'Use --something to specify a custom something'
    ]

    assert expected_output in result.std_out
    for expected_possible_solution in expected_possible_solutions:
        assert expected_possible_solution in result.std_out


@pytest.mark.docker
@pytest.mark.cross_distro
@pytest.mark.parametrize("build_distro_id", [
    'build:PythonStretch:2.7.16',
    'build:PythonStretch:3.6.8'
])
def test_binary_cross_distribution_wheel(log, repo_version, repo_path, test_name, build_distro_id):

    run_distro_ids = [
        'run:PythonStretch:2.7.16',
        'run:PythonStretch:3.6.8',
        'run:Ubuntu:18.04',
        'run:Ubuntu:16.04',
        'run:Ubuntu:14.04'
    ]

    build_distro = distros.from_string(test_name, build_distro_id)

    build_distro.boot()

    log.debug("Creating binary package on: {}".format(build_distro_id))
    local_binary_path = build_distro.binary(repo_path)
    log.debug("Binary package created: {}".format(local_binary_path))

    try:
        for run_distro_id in run_distro_ids:

            log.debug('Running on target: {}'.format(run_distro_id))

            run_distro = distros.from_string(test_name, run_distro_id)

            if run_distro.python_version is not None:
                # wheels can only be built on distros with python installed
                expected_output = 'py_ci-{}-{}-none-any.whl'.format(
                    repo_version,
                    'py2' if run_distro.python_version.startswith('2') else 'py3')
            else:
                expected_output = 'Python installation not found in PATH'

            try:

                run_distro.boot()

                remote_binary_path = run_distro.add(local_binary_path)
                remote_repo_path = run_distro.add(repo_path)

                locale_setup = ''
                if build_distro.python_version.startswith('3'):
                    # pyci was packed with python 3.
                    # need to configure locale before invoking.
                    # http://click.palletsprojects.com/en/6.x/python3/
                    locale_setup = 'export LC_ALL=C.UTF-8 && export LANG=C.UTF-8 &&'

                result = run_distro.run('chmod +x {} && {} {} pack --path {} wheel'
                                        .format(remote_binary_path, locale_setup,
                                                remote_binary_path, remote_repo_path),
                                        exit_on_failure=False)

                assert expected_output in result.std_out

            finally:
                run_distro.shutdown()
    finally:
        os.remove(local_binary_path)
        build_distro.shutdown()
