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

try:
    # python2
    from mock import MagicMock
except ImportError:
    # python3
    # noinspection PyUnresolvedReferences,PyCompatibility
    from unittest.mock import MagicMock

import pytest

from pyci.api.packager import Packager
from pyci.tests import distros
from pyci.tests import conftest


@pytest.mark.parametrize("binary", [False, True])
def test_binary(pack, temp_dir, request, runner, binary, mocker):

    pack.api.target_dir = temp_dir

    if not binary:
        mocker.patch(target='pyci.api.packager.Packager.binary', new=MagicMock())

    name = request.node.name.replace('[', '-').replace(']', '')
    custom_main = os.path.join('pyci', 'shell', 'custom_main.py')

    with open(os.path.join(pack.api.repo_dir, custom_main), 'w') as stream:
        stream.write('''
import six

if __name__ == '__main__':
    six.print_('It works!')        
''')

    pack.run('binary --base-name {} --entrypoint {} --pyinstaller-version 3.4'
             .format(name, custom_main), binary=binary)

    if binary:

        expected_package_path = os.path.join(temp_dir, '{}-{}-{}'
                                             .format(name, platform.machine(), platform.system()))

        if platform.system() == 'Windows':
            expected_package_path = '{0}.exe'.format(expected_package_path)

        assert os.path.exists(expected_package_path)

        # lets make sure the binary actually works
        assert runner.run(expected_package_path).std_out == 'It works!'

    else:

        # noinspection PyUnresolvedReferences
        Packager.binary.assert_called_once_with(base_name=name,  # pylint: disable=no-member
                                                entrypoint=custom_main,
                                                pyinstaller_version='3.4')


@pytest.mark.parametrize("binary", [False, True])
def test_binary_file_exists(pack, binary):

    expected_package_path = os.path.join(os.getcwd(), 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected_package_path = '{0}.exe'.format(expected_package_path)

    with open(expected_package_path, 'w') as stream:
        stream.write('package')

    result = pack.run('binary --entrypoint {}'.format(conftest.SPEC_FILE),
                      catch_exceptions=True, binary=binary)

    expected_output = 'Binary exists'
    expected_possible_solution = 'Delete/Move the binary and try again'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out


@pytest.mark.parametrize("binary", [False, True])
def test_binary_default_entrypoint_doesnt_exist(pack, binary):

    result = pack.run('binary', catch_exceptions=True, binary=binary)

    expected_output = 'No entrypoint found for repo'
    expected_possible_solutions = [
        'Create an entrypoint file in one of the following paths',
        'Use --entrypoint to specify a custom entrypoint path'
    ]

    assert expected_output in result.std_out
    for expected_possible_solution in expected_possible_solutions:
        assert expected_possible_solution in result.std_out


@pytest.mark.parametrize("binary", [False, True])
def test_binary_entrypoint_doesnt_exist(pack, binary):

    result = pack.run('binary --entrypoint doesnt-exist', catch_exceptions=True, binary=binary)

    expected_output = 'Entrypoint not found for repo'

    assert expected_output in result.std_out


@pytest.mark.parametrize("binary", [False, True])
def test_wheel(pack, repo_version, temp_dir, binary, mocker):

    pack.api.target_dir = temp_dir

    if not binary:
        mocker.patch(target='pyci.api.packager.Packager.wheel', new=MagicMock())

    result = pack.run('wheel --universal --wheel-version 0.33.4', binary=binary)

    if binary:

        expected_path = os.path.join(temp_dir, 'py_ci-{0}-py2.py3-none-any.whl'
                                     .format(repo_version))

        expected_output = 'Wheel package created: {}'.format(expected_path)

        assert expected_output in result.std_out
        assert os.path.exists(expected_path)

    else:

        # noinspection PyUnresolvedReferences
        Packager.wheel.assert_called_once_with(universal=True,  # pylint: disable=no-member
                                               wheel_version='0.33.4')


@pytest.mark.parametrize("binary", [False])
def test_wheel_file_exists(pack, repo_version, binary):

    expected_path = os.path.join(os.getcwd(), 'py_ci-{}-py2.py3-none-any.whl'
                                 .format(repo_version))

    with open(expected_path, 'w') as stream:
        stream.write('package')

    result = pack.run('wheel --universal', catch_exceptions=True, binary=binary)

    expected_output = 'Wheel exists'
    expected_possible_solution = 'Delete/Move the package and try again'

    assert expected_output in result.std_out
    assert expected_possible_solution in result.std_out


@pytest.mark.parametrize("binary", [False, True])
def test_wheel_not_python_project(pack, binary):

    os.remove(os.path.join(pack.api.repo_dir, 'setup.py'))

    result = pack.run('wheel', binary=binary, catch_exceptions=True)

    expected_output = 'does not contain a valid python project'

    assert expected_output in result.std_out


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
