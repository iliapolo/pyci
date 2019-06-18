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

import pytest

from pyci.api import exceptions
from pyci.api import utils
from pyci.api.pypi import PyPI
from pyci.shell import secrets


def test_upload(pypi, wheel_path):

    wheel_url = pypi.api.upload(wheel=wheel_path)
    utils.download(url=wheel_url)


def test_upload_already_exists(pypi, pack, mocker):

    wheel_path = pack.api.wheel()

    # Mocking the response from PyPI in this case
    def _upload(*_, **__):
        raise BaseException('File already exists')

    mocker.patch(target='twine.commands.upload.main', side_effect=_upload)

    with pytest.raises(exceptions.WheelAlreadyPublishedException):
        pypi.api.upload(wheel=wheel_path)


def test_upload_twine_execution_failed(pack, mocker):

    pypi = PyPI.create(username='username',
                       password='password',
                       repository_url='htttp://repository-url',
                       test=False)

    # Mocking the response from PyPI in this case
    def _upload(*_, **__):
        raise BaseException('Server failure')

    mocker.patch(target='twine.commands.upload.main', side_effect=_upload)

    wheel_path = pack.api.wheel()
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
