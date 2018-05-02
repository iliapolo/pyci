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

# noinspection PyPackageRequirements

# noinspection PyPackageRequirements
from mock import MagicMock

from pyci.api import exceptions


def test_upload(patched_pypi, capture):

    patched_pypi.pypi.upload = MagicMock(return_value='url')

    patched_pypi.run('upload --wheel wheel')

    expected_output = 'Wheel uploaded: url'

    assert expected_output == capture.records[1].msg
    patched_pypi.pypi.upload.assert_called_once_with(wheel='wheel')


def test_upload_failed(patched_pypi, capture):

    exception = exceptions.ApiException('error')
    patched_pypi.pypi.upload = MagicMock(side_effect=exception)

    patched_pypi.run('upload --wheel wheel', catch_exceptions=True)

    expected_output = 'Failed uploading wheel: error'

    assert expected_output in capture.records[2].msg
    patched_pypi.pypi.upload.assert_called_once_with(wheel='wheel')
