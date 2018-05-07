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

from click.testing import CliRunner

from pyci.api import logger
from pyci.api.runner import LocalCommandRunner
from pyci.shell.main import app

log = logger.get_logger(__name__)


# pylint: disable=too-few-public-methods
class Runner(object):

    def __init__(self):
        super(Runner, self).__init__()
        self._click_runner = CliRunner()
        self._local_runner = LocalCommandRunner()

    def run(self, command, catch_exceptions=False):

        executable_path = os.environ.get('PYCI_EXECUTABLE_PATH')
        if executable_path:
            return self._run_executable(executable_path, command, catch_exceptions)
        else:
            return self._run_source(command, catch_exceptions)

    def _run_source(self, command, catch_exceptions):

        args = split(command)

        log.info('Invoking command: {}. [cwd={}, args={}]'.format(command, os.getcwd(), args))

        result = self._click_runner.invoke(app, args, catch_exceptions=catch_exceptions)

        if isinstance(result.exception, SystemExit) and not catch_exceptions:
            raise SystemExit(result.output)  # pragma: no cover

        return result

    def _run_executable(self, executable_path, command, catch_exceptions):

        return self._local_runner.run('{} {}'.format(executable_path, command),
                                      exit_on_failure=not catch_exceptions)


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
