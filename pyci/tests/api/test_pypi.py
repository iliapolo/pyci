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

# noinspection PyPackageRequirements
import pytest

from pyci.api import logger, exceptions
from pyci.api import utils
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.shell import secrets
from pyci.tests.conftest import patch_setup_py, REPO_UNDER_TEST

logger.setup_loggers(logging.DEBUG)


def test_upload(pypi_packager, pypi, temp_dir):

    wheel_path = pypi_packager.wheel(target_dir=temp_dir)
    wheel_url = pypi.upload(wheel=wheel_path)
    utils.download(url=wheel_url)


def test_upload_already_exists(pypi, temp_dir):

    packager = Packager.create(repo=REPO_UNDER_TEST,
                               sha='fc517a05bdd22748714e9900b9c9860f37546738')

    # noinspection PyProtectedMember
    # pylint: disable=protected-access
    patch_setup_py(packager._repo_dir)

    wheel_path = packager.wheel(target_dir=temp_dir)

    pypi.upload(wheel=wheel_path)

    # change the source code but create a wheel with the same version
    main = os.path.join(packager._repo_dir, 'pyci_guinea_pig', 'shell', 'main.py')
    with open(main, 'w') as stream:
        stream.write('import os')

    os.remove(wheel_path)
    wheel_path = packager.wheel(target_dir=temp_dir)

    with pytest.raises(exceptions.WheelAlreadyPublishedException):
        pypi.upload(wheel=wheel_path)


def test_upload_twine_execution_failed(pypi_packager, temp_dir):

    pypi = PyPI.create(username=secrets.twine_username(True),
                       password=secrets.twine_password(True),
                       repository_url='htttp://repository-url',
                       test=False)

    wheel_path = pypi_packager.wheel(target_dir=temp_dir)
    with pytest.raises(exceptions.FailedPublishingWheelException):
        pypi.upload(wheel=wheel_path)


def test_no_username():

    with pytest.raises(exceptions.InvalidArgumentsException):
        PyPI.create(username='', password='pass')


def test_no_password():

    with pytest.raises(exceptions.InvalidArgumentsException):
        PyPI.create(username='user', password='')


def test_repository_url_and_test():

    with pytest.raises(exceptions.InvalidArgumentsException):
        PyPI.create(username='user', password='pass', test=True, repository_url='repository')
