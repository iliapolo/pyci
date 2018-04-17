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
import pkg_resources

import pytest


from pyci.api.packager import Packager
from pyci.api import logger, exceptions
import pyci


logger.setup_loggers('DEBUG')


@pytest.fixture(name='packager')
def pack():

    local_repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))
    packager = Packager(path=local_repo_path)

    yield packager


def test_name_not_python_project():

    # for that we need to use our guinea-pig project...
    # using the very first sha of the project, before it even was a python project..
    packager = Packager(repo='iliapolo/pyci-guinea-pig',
                        sha='aee0c4c21d64f95f6742838aded957c2be71c2e5')

    with pytest.raises(exceptions.NotPythonProjectException):
        _ = packager.name


def test_name_python_project(packager):

    expected = 'py-ci'

    assert expected == packager.name


def test_entrypoint_no_entrypoint():

    # for that we need to use our guinea-pig project...
    # using a sha before we added the main.py file.
    packager = Packager(repo='iliapolo/pyci-guinea-pig',
                        sha='b22803b93eaca693db78f9d551ec295946765135')

    with pytest.raises(exceptions.DefaultEntrypointNotFoundException):
        _ = packager.entrypoint


def test_entrypoint_script():

    # for that we need to use our guinea-pig project...
    # using a sha when we first added the main.py file
    packager = Packager(repo='iliapolo/pyci-guinea-pig',
                        sha='0596d82b4786a531b7370448e2b5d0de9922f01a')

    assert os.path.join('pyci_guinea_pig', 'shell', 'main.py') in packager.entrypoint


def test_entrypoint_spec():

    # for that we need to use our guinea-pig project...
    # using a sha when we first added the spec file
    packager = Packager(repo='iliapolo/pyci-guinea-pig',
                        sha='6cadc14419e57549365ac4dabea59c4c08be581c')

    assert 'pyci-guinea-pig.spec' in packager.entrypoint


def test_wheel(packager, temp_dir):

    version = pkg_resources.get_distribution('py-ci').version

    expected = os.path.join(temp_dir, 'py_ci-{0}-py2-none-any.whl'.format(version))

    actual = packager.wheel(target_dir=temp_dir)

    assert expected == actual


def test_wheel_universal(packager, temp_dir):

    version = pkg_resources.get_distribution('py-ci').version

    expected = os.path.join(temp_dir, 'py_ci-{0}-py2.py3-none-any.whl'.format(version))

    actual = packager.wheel(target_dir=temp_dir, universal=True)

    assert expected == actual


def test_binary(packager, runner, temp_dir):

    expected = os.path.join(temp_dir, 'py-ci-{0}-{1}'.format(
        platform.machine(), platform.system()))

    if platform.system() == 'Windows':
        expected = '{0}.exe'.format(expected)

    actual = packager.binary(target_dir=temp_dir)

    assert expected == actual

    # lets make sure the binary actually works
    runner.run('{0} --help'.format(actual))


def test_binary_custom_entrypoint_and_name(request, runner, temp_dir):

    # for that we need to use our guinea-pig project...
    # using a sha when we first added the spec file
    packager = Packager(repo='iliapolo/pyci-guinea-pig',
                        sha='33526a9e0445541d96e027db2aeb93d07cdf8bd6')

    name = request.node.name

    expected = os.path.join(temp_dir, '{0}-{1}-{2}'.format(name,
                                                           platform.machine(),
                                                           platform.system()))

    if platform.system() == 'Windows':
        expected = '{0}.exe'.format(expected)

    actual = packager.binary(target_dir=temp_dir, name=name,
                             entrypoint=os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py'))

    assert expected == actual

    # lets make sure the binary actually works
    # see https://github.com/iliapolo/pyci-guinea-pig/blob/master/pyci_guinea_pig
    # /shell/custom_main.py
    assert runner.run(actual).std_out == 'It works!'
