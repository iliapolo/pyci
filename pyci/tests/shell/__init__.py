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
import platform
import re
import tempfile
import logging

import pytest
from click.testing import CliRunner
from boltons.cacheutils import cachedproperty

import pyci
from pyci.api import logger
from pyci.api.packager import Packager
from pyci.api.runner import LocalCommandRunner
from pyci.shell.main import app
from pyci.api.runner import CommandExecutionResponse


CLICK_ISOLATION = '__CLICK_ISOLATION'


# pylint: disable=too-few-public-methods
class PyCI(object):

    def __init__(self, log=None):

        repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))

        self._logger = log or logger.Logger(__name__)
        self._click_runner = CliRunner()
        self._local_runner = LocalCommandRunner()
        self._packager = Packager.create(path=repo_path, target_dir=tempfile.mkdtemp())

    def run(self, command, binary=False, catch_exceptions=False):

        if self._logger.isEnabledFor(logging.DEBUG):
            command = '--debug {}'.format(command)

        if binary:
            response = self._run_binary(command=command)
        else:
            try:
                os.environ[CLICK_ISOLATION] = 'True'
                response = self._run_source(command=command)
            finally:
                del os.environ[CLICK_ISOLATION]

        if response.return_code != 0 and not catch_exceptions:

            pytest.fail("Invocation of command '{0}' failed. {1}{1}{2}{1}{1}{3}".format(
                command,
                os.linesep,
                response.std_out,
                response.std_err))

        return response

    def _run_source(self, command):

        args = split(command)

        self._logger.info('Invoking command: {} [cwd={}]'.format(command, os.getcwd()))

        result = self._click_runner.invoke(app, args, catch_exceptions=True)

        exception = result.exception

        return CommandExecutionResponse(command=command,
                                        std_out=result.output,
                                        std_err=str(exception) if exception else None,
                                        return_code=result.exit_code)

    def _run_binary(self, command):

        command = '{} {}'.format(self.binary_path, command)

        self._logger.info('Invoking command: {}. [cwd={}]'.format(command, os.getcwd()))

        return self._local_runner.run(command, exit_on_failure=False, execution_env={
            'PYCI_INTERACTIVE': 'False'
        })

    @cachedproperty
    def binary_path(self):

        # pylint: disable=cyclic-import
        from pyci.tests import conftest

        package_path = os.environ.get('PYCI_BINARY_PATH', None)

        if not package_path:
            self._logger.info('Creating binary package... [cwd={}]'.format(os.getcwd()))
            package_path = self._packager.binary(entrypoint=conftest.SPEC_FILE)
            self._logger.info('Created binary package: {} [cwd={}]'.format(package_path, os.getcwd()))

        return package_path

    @cachedproperty
    def wheel_path(self):

        self._logger.info('Creating wheel package... [cwd={}]'.format(os.getcwd()))
        package_path = self._packager.wheel()
        self._logger.info('Created wheel package: {} [cwd={}]'.format(package_path, os.getcwd()))
        return package_path


# take from https://stackoverflow.com/questions/33560364/python-windows-parsing-command-
# lines-with-shlex?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
# pylint: disable=too-many-branches
def split(command):

    if platform.system().lower() != 'windows':
        re_cmd_lex = r'"((?:\\["\\]|[^"])*)"|' \
                     r"'([^']*)'|(\\.)|(&&?|\|\|?|\d?\>|[<])|([^\s'" \
                     r'"\\&|<>]+)|(\s+)|(.)'
    else:
        re_cmd_lex = r'"((?:""|\\["\\]|[^"])*)"?()|(\\\\(?=\\*")|\\")|(&&?|\|\|' \
                     r'?|\d?>|[<])|([^\s"&|<>]+)|(\s+)|(.)'

    args = []
    accu = None
    for qs, qss, esc, pipe, word, white, fail in re.findall(re_cmd_lex, command):
        if word:
            pass
        elif esc:
            word = esc[1]
        elif white or pipe:
            if accu is not None:
                args.append(accu)
            if pipe:
                args.append(pipe)
            accu = None
            continue
        elif fail:
            raise ValueError("invalid or incomplete shell string")
        elif qs:
            word = qs.replace('\\"', '"').replace('\\\\', '\\')
            if platform == 0:
                word = word.replace('""', '"')
        else:
            word = qss   # may be even empty; must be last

        accu = (accu or '') + word

    if accu is not None:
        args.append(accu)

    return args
