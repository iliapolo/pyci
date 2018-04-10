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

import shlex

from click.testing import CliRunner

from pyci.api import logger
from pyci.api.constants import PROGRAM_NAME
from pyci.shell.main import app


# pylint: disable=too-few-public-methods
class Runner(object):

    def __init__(self):
        super(Runner, self).__init__()
        self._runner = CliRunner()
        self.log = logger.get_logger('{0}.tests.shell.commands:Runner'.format(PROGRAM_NAME))

    def run(self, command, catch_exceptions=False):

        self.log.info('Invoking command: {0}'.format(command))

        result = self._runner.invoke(app, shlex.split(command)[1:],
                                     catch_exceptions=catch_exceptions)

        if isinstance(result.exception, SystemExit) and not catch_exceptions:
            raise SystemExit(result.output)

        return result
