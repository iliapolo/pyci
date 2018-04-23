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
# noinspection PyPackageRequirements
import pytest

import pyci
from pyci.api import logger, exceptions
from pyci.api.packager import Packager


logger.setup_loggers('DEBUG')


@pytest.fixture(name='packager')
def pack():

    local_repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))
    packager = Packager(path=local_repo_path)

    try:
        yield packager
    finally:
        packager.clean()


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


def test_binary_no_default_entrypoint(request, temp_dir):

    # for that we need to use our guinea-pig project...
    # using a sha without any entry-points.
    packager = Packager(repo='iliapolo/pyci-guinea-pig',
                        sha='b22803b93eaca693db78f9d551ec295946765135')

    name = request.node.name

    with pytest.raises(exceptions.DefaultEntrypointNotFoundException):
        packager.binary(target_dir=temp_dir, name=name)


def test_binary_no_custom_entrypoint(request, temp_dir):

    # for that we need to use our guinea-pig project...
    # using a sha without the custom main script.
    packager = Packager(repo='iliapolo/pyci-guinea-pig',
                        sha='b22803b93eaca693db78f9d551ec295946765135')

    name = request.node.name

    with pytest.raises(exceptions.EntrypointNotFoundException):
        packager.binary(target_dir=temp_dir, name=name,
                        entrypoint=os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py'))


def test_binary_custom_entrypoint_and_name(request, runner, temp_dir):

    # for that we need to use our guinea-pig project...
    # using a sha with the custom main script.
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


def test_sha_and_not_repo():

    with pytest.raises(exceptions.InvalidArgumentsException):
        Packager(sha='sha', repo='')


def test_sha_and_path():

    with pytest.raises(exceptions.InvalidArgumentsException):
        Packager(sha='sha', path='path')


def test_not_sha_and_not_path():

    with pytest.raises(exceptions.InvalidArgumentsException):
        Packager(sha='', path='', repo='iliapolo/repo')
