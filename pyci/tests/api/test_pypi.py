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
import logging
import os
import shutil
import time

import pytest

import pyci
from pyci.api import logger, exceptions
from pyci.api import utils
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI

logger.setup_loggers(logging.DEBUG)


@pytest.fixture(name='packager')
def pack(temp_dir):

    local_repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))

    dest = os.path.join(temp_dir, 'repo')
    shutil.copytree(local_repo_path, dest)

    with open(os.path.join(dest, 'setup.py'), 'r') as stream:
        setup_py = stream.read()

    setup_py = utils.generate_setup_py(setup_py, '{}'.format(int(time.time())))

    with open(os.path.join(dest, 'setup.py'), 'w') as stream:
        stream.write(setup_py)

    packager = Packager(path=dest)

    yield packager

    packager.clean()


@pytest.fixture(name='pypi')
def pypy():

    yield PyPI(username=os.environ['TWINE_USERNAME'], password=os.environ['TWINE_PASSWORD'],
               test=True)


def test_upload(packager, pypi, temp_dir):

    wheel_path = packager.wheel(target_dir=temp_dir)
    wheel_url = pypi.upload(wheel=wheel_path)
    utils.download(url=wheel_url)


def test_no_username():

    with pytest.raises(exceptions.InvalidArgumentsException):
        PyPI(username='', password='pass')


def test_no_password():

    with pytest.raises(exceptions.InvalidArgumentsException):
        PyPI(username='user', password='')


def test_repository_url_and_test():

    with pytest.raises(exceptions.InvalidArgumentsException):
        PyPI(username='user', password='pass', test=True, repository_url='repository')
