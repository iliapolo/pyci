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

from twine.commands import upload

from pyci.shell import secrets
from pyci.tests import utils as test_utils


def test_upload(pypi, pyci, mocker):

    mocker.patch(target='twine.commands.upload.main', new=test_utils.MagicMock())

    pypi.run('upload --wheel {}'.format(pyci.wheel_path))

    expected_args = ['--username', secrets.twine_username(),
                     '--password', secrets.twine_password(),
                     '--repository-url', 'https://test.pypi.org/legacy/',
                     pyci.wheel_path]

    # noinspection PyUnresolvedReferences
    upload.main.assert_called_once_with(expected_args)  # pylint: disable=no-member


def test_upload_already_published(pypi, pyci, mocker):

    # Mocking the response from PyPI in this case
    def _upload(*_, **__):
        raise BaseException('File already exists')

    mocker.patch(target='twine.commands.upload.main', side_effect=_upload)

    result = pypi.run('upload --wheel {}'.format(pyci.wheel_path), catch_exceptions=True)

    expected_output = 'A wheel with the same name as {} was already uploaded' \
        .format(os.path.basename(pyci.wheel_path))

    assert expected_output in result.std_out
