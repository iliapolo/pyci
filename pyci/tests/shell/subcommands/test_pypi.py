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

# noinspection PyPackageRequirements
import pytest

# noinspection PyPackageRequirements
from mock import MagicMock

from pyci.api import exceptions
from pyci.tests.shell import Runner


@pytest.fixture(name='pypi')
def _pypi(temp_dir, mocker):

    pypi_mock = MagicMock()

    mocker.patch(target='pyci.api.pypi.new', new=MagicMock(return_value=pypi_mock))

    # pylint: disable=too-few-public-methods
    class PyPISubCommand(Runner):

        def __init__(self, pypi):
            super(PyPISubCommand, self).__init__()
            self.pypi = pypi

        def run(self, command, catch_exceptions=False):

            command = 'pypi {}'.format(command)

            return super(PyPISubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield PyPISubCommand(pypi_mock)
    finally:
        os.chdir(cwd)


def test_upload(pypi, capture):

    pypi.pypi.upload = MagicMock(return_value='url')

    pypi.run('upload --wheel wheel')

    expected_output = 'Wheel uploaded: url'

    assert expected_output == capture.records[1].msg
    pypi.pypi.upload.assert_called_once_with(wheel='wheel')


def test_upload_failed(pypi, capture):

    exception = exceptions.ApiException('error')
    pypi.pypi.upload = MagicMock(side_effect=exception)

    pypi.run('upload --wheel wheel', catch_exceptions=True)

    expected_output = 'Failed uploading wheel: error'

    assert expected_output in capture.records[2].msg
    pypi.pypi.upload.assert_called_once_with(wheel='wheel')
