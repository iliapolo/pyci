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

from pyci.api import exceptions
from pyci.api import logger
from pyci.api.runner import LocalCommandRunner

log = logger.get_logger(__name__)


# pylint: disable=too-few-public-methods
class PyPI(object):

    def __init__(self, username, password, repository_url=None, test=False):

        if repository_url and test:
            raise exceptions.BadArgumentException('Either repository_url or test is allowed')

        self.test = test
        self.repository_url = repository_url
        self.username = username
        self.password = password
        self._runner = LocalCommandRunner()

    def upload(self, wheel):

        wheel = os.path.abspath(wheel)

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
        log.debug('Uploading wheel to PyPI repository ({0}): {1}'
                  .format(repository_url or 'default', wheel))
        self._runner.run('{0} {1}'.format(command, wheel), execution_env=env)
        log.debug('Successfully uploaded wheel')
