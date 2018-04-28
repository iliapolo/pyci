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
from pyci.shell.main import app

log = logger.get_logger(__name__)


# pylint: disable=too-few-public-methods
class Runner(object):

    def __init__(self):
        super(Runner, self).__init__()
        self._runner = CliRunner()

    def run(self, command, catch_exceptions=False):

        args = split(command)

        log.info('Invoking command: {}. [cwd={}, args={}]'.format(command, os.getcwd(), args))

        result = self._runner.invoke(app, args, catch_exceptions=catch_exceptions)

        if isinstance(result.exception, SystemExit) and not catch_exceptions:
            raise SystemExit(result.output)

        return result


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
