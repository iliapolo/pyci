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

import copy
import os
import tempfile

from wheel.cli import unpack
from twine.commands import upload

from pyci.api import exceptions, utils
from pyci.api import logger
from pyci.api.runner import LocalCommandRunner
from pyci.api.runner import shlex_split


# pylint: disable=too-few-public-methods
class PyPI(object):

    """
    Provides access to PyPI API.

    Every PyPI instance is associated with a set of credentials, as well as the repository URL.
    You can specify test=True to use PyPI's test repostiory, or repository_url to use a custom
    repository. If non are passed, the default PyPI repository is used.

    Args:
        username (str): The username for PyPI.
        password (str): The password for PyPI.
        repository_url (str): A custom repository url.
        test (bool): True to use the test PyPI repository, False otherwise.
    """

    def __init__(self, username, password, repository_url=None, test=False):

        if not username:
            raise exceptions.InvalidArgumentsException('username cannot be None')

        if not password:
            raise exceptions.InvalidArgumentsException('password cannot be None')

        if repository_url and test:
            raise exceptions.InvalidArgumentsException('either repository_url or test is allowed')

        self.test = test
        self.repository_url = 'https://test.pypi.org/legacy/' if self.test else repository_url
        self.username = username
        self.password = password
        self._runner = LocalCommandRunner()
        self._site = 'test.pypi.org' if self.test else 'pypi.org'
        self._logger = logger.Logger(__name__)
        self._log_ctx = {
            'test': self.test,
            'repository_url': self.repository_url,
            'site': self._site
        }

    @staticmethod
    def create(username, password, repository_url=None, test=False):
        return PyPI(username=username, password=password, repository_url=repository_url, test=test)

    def upload(self, wheel):

        """
        Upload a wheel to PyPI.

        Args:
            wheel (str): Path to a wheel package.

        Raises:
            WheelAlreadyPublishedException: Raised when the wheel already exists in the PyPI
                repository.
        """

        wheel = os.path.abspath(wheel)

        wheel_version = os.path.basename(wheel).split('-')[1]

        wheel_url = 'https://{}/manage/project/{}/release/{}/'.format(
            self._site, self._extract_project_name(wheel), wheel_version)

        args = '--username {} --password {}'.format(self.username, self.password)
        if self.repository_url:
            args = '{} --repository-url {}'.format(args, self.repository_url)

        args = shlex_split('{} {}'.format(args, wheel))

        try:
            self._debug('Uploading wheel to PyPI repository...', wheel=wheel)
            upload.main(args)
            self._debug('Successfully uploaded wheel', wheel_url=wheel_url)
            return wheel_url
        except BaseException as e:

            if 'File already exists' in str(e):
                wheel_name = os.path.basename(wheel)
                raise exceptions.WheelAlreadyPublishedException(wheel=wheel_name, url=wheel_url)

            raise exceptions.FailedPublishingWheelException(wheel=wheel, error=str(e))

    @staticmethod
    def _extract_project_name(wheel):

        wheel = os.path.abspath(wheel)

        wheel_parts = os.path.basename(wheel).split('-')

        temp_dir = tempfile.mkdtemp()

        try:

            project_name = None

            unpack.unpack(path=wheel, dest=temp_dir)

            wheel_project = '{}-{}'.format(wheel_parts[0], wheel_parts[1])
            metadata_file_path = os.path.join(temp_dir,
                                              wheel_project,
                                              '{}.dist-info'.format(wheel_project),
                                              'METADATA')
            with open(metadata_file_path) as stream:
                for line in stream.read().splitlines():
                    if line.startswith('Name: '):
                        project_name = line.split('Name: ')[1]
                        break
            return project_name
        finally:
            utils.rmf(temp_dir)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        self._logger.debug(message, **kwargs)
