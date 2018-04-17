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

import json
import os
import shutil
import tempfile

from pyci.api import exceptions
from pyci.api import logger
from pyci.api.runner import LocalCommandRunner

log = logger.get_logger(__name__)


# pylint: disable=too-few-public-methods
class PyPI(object):

    def __init__(self, username, password, repository_url=None, test=False):

        if repository_url and test:
            raise exceptions.InvalidArgumentsException('Either repository_url or test is allowed')

        self.test = test
        self.repository_url = repository_url
        self.username = username
        self.password = password
        self._runner = LocalCommandRunner()

    def upload(self, wheel):

        wheel = os.path.abspath(wheel)

        wheel_version = os.path.basename(wheel).split('-')[1]

        site = 'pypi.org'
        if self.test:
            site = 'test.{0}'.format(site)

        wheel_url = 'https://{0}/manage/project/{1}/release/{2}/'.format(
            site, self._extract_project_name(wheel), wheel_version)

        log.debug('Wheel url will be: {0}'.format(wheel_url))

        repository_url = None
        if self.test:
            repository_url = 'https://test.pypi.org/legacy/'
        if self.repository_url:
            repository_url = self.repository_url

        command = 'twine upload'
        if repository_url:
            command = '{0} --repository-url {1}'.format(command, repository_url)

        env = {
            'TWINE_USERNAME': self.username,
            'TWINE_PASSWORD': self.password
        }

        try:
            log.debug('Uploading wheel to PyPI repository ({0}): {1}'
                      .format(repository_url or 'default', wheel))
            self._runner.run('{0} {1}'.format(command, wheel), execution_env=env)
            log.debug('Successfully uploaded wheel')
        except exceptions.CommandExecutionException as e:
            if 'File already exists' in e.error:
                wheel_name = os.path.basename(wheel)
                raise exceptions.WheelAlreadyPublishedException(wheel=wheel_name, url=wheel_url)

        return wheel_url

    def _extract_project_name(self, wheel):

        wheel = os.path.abspath(wheel)

        wheel_parts = os.path.basename(wheel).split('-')

        temp_dir = tempfile.mkdtemp()
        try:
            self._runner.run('wheel unpack --dest {0} {1}'.format(temp_dir, wheel))
            wheel_project = '{0}-{1}'.format(wheel_parts[0], wheel_parts[1])
            metadata_file_path = os.path.join(temp_dir,
                                              wheel_project,
                                              '{0}.dist-info'.format(wheel_project),
                                              'metadata.json')
            with open(metadata_file_path) as stream:
                metadata = json.loads(stream.read())
                return metadata['name']
        finally:
            shutil.rmtree(temp_dir)
