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

try:
    # python2
    from mock import MagicMock
except ImportError:
    # python3
    # noinspection PyUnresolvedReferences,PyCompatibility
    from unittest.mock import MagicMock

from twine.commands import upload

import pytest
from pyci.shell import secrets


@pytest.mark.parametrize("binary", [False, True])
def test_upload(pypi, binary, pyci, mocker):

    if not binary:
        mocker.patch(target='twine.commands.upload.main', new=MagicMock())

    expected_url = 'https://test.pypi.org/manage/project/py-ci/release/{}/'.format(
        pyci.wheel_path.split('-')[1])

    result = pypi.run('upload --wheel {}'.format(pyci.wheel_path), binary=binary)

    if binary:

        expected_output = 'Wheel uploaded: {}'.format(expected_url)

        assert expected_output in result.std_out

    else:

        expected_args = ['--username', secrets.twine_username(),
                         '--password', secrets.twine_password(),
                         '--repository-url', 'https://test.pypi.org/legacy/',
                         pyci.wheel_path]

        # noinspection PyUnresolvedReferences
        upload.main.assert_called_once_with(expected_args)  # pylint: disable=no-member


@pytest.mark.parametrize("binary", [False, True])
def test_upload_already_published(pypi, pack, binary, mocker):

    # Mocking the response from PyPI in this case
    def _upload(*_, **__):
        raise BaseException('File already exists')

    wheel_path = pack.api.wheel()

    if not binary:
        mocker.patch(target='twine.commands.upload.main', side_effect=_upload)

    result = pypi.run('upload --wheel {}'.format(wheel_path), catch_exceptions=True, binary=binary)

    expected_output = 'A wheel with the same name as {} was already uploaded' \
        .format(os.path.basename(wheel_path))

    if binary:

        # change the source code but create a wheel with the same version
        main = os.path.join(pack.api.repo_dir, 'pyci', 'shell', 'main.py')
        with open(main, 'w') as stream:
            stream.write('import os')

        os.remove(wheel_path)
        wheel_path = pack.api.wheel()

        result = pypi.run('upload --wheel {}'.format(wheel_path), catch_exceptions=True, binary=binary)

        assert expected_output in result.std_out

    else:

        assert expected_output in result.std_out
