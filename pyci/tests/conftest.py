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
import tempfile

# noinspection PyPackageRequirements
import copy
import pytest
# noinspection PyPackageRequirements
from testfixtures import LogCapture

from pyci.api import utils
from pyci.api.runner import LocalCommandRunner
from pyci import shell
from pyci.shell.subcommands import github
from pyci.shell.subcommands import pack
from pyci.shell.subcommands import pypi
from pyci.api import logger


@pytest.fixture(name='capture', autouse=True)
def _capture():
    names = (shell.__name__, github.__name__, pack.__name__, pypi.__name__)
    with LogCapture(names=names) as capture:

        # LogCapture removes all handlers from the given loggers.
        # lets re-add the console handler, it makes it easier to debug.
        for name in names:
            log = logger.get_logger(name)
            log.add_console_handler(logging.DEBUG)

        yield capture


@pytest.fixture()
def temp_file(request):

    file_path = tempfile.mkstemp(suffix=request.node.name)[1]

    try:
        yield file_path
    finally:
        # cleanup
        os.remove(file_path)


@pytest.fixture()
def temp_dir(request):

    dir_path = tempfile.mkdtemp(suffix=request.node.name)

    try:
        yield dir_path
    finally:
        # cleanup
        utils.rmf(dir_path)


@pytest.fixture()
def home_dir():

    homedir = tempfile.mkdtemp()
    os.environ['HOME'] = homedir

    try:
        yield homedir

    finally:
        # cleanup
        utils.rmf(homedir)


@pytest.fixture()
def runner():

    yield LocalCommandRunner()


@pytest.fixture()
def isolated():

    cwd = os.getcwd()
    t = tempfile.mkdtemp()
    os.chdir(t)
    try:
        yield t
    finally:
        os.chdir(cwd)
        utils.rmf(t)
