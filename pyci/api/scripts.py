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
import sys

from virtualenv import main
from pyci.api import exceptions


def _shlex_split(command):
    lex = shlex.shlex(command, posix=True)
    lex.whitespace_split = True
    lex.escape = ''
    return list(lex)


class Virtualenv(object):

    @staticmethod
    def run(args):

        original_argv = list(sys.argv)

        # This doesn't really matter since it being
        # cut in the 'main' function anyway.
        new_args = ['virtualenv']

        shlexed = _shlex_split(args)

        new_args.extend(shlexed)

        try:
            sys.argv = new_args
            main()
        except SystemExit as e:
            if e.code != 0:
                raise exceptions.ScriptInvocationException(script='virtualenv',
                                                           arguments=shlexed,
                                                           error=str(e))
        finally:
            sys.argv = original_argv


class Python(object):

    @staticmethod
    def run(args):

        original_argv = list(sys.argv)

        # This doesn't really matter since it being
        # cut in the 'main' function anyway.
        new_args = ['python']

        shlexed = _shlex_split(args)

        new_args.extend(shlexed)

        try:
            script = shlexed[0]
            with  open(script) as f:
                content = f.read()
            sys.argv = new_args
            exec content
        except SystemExit as e:
            if e.code != 0:
                raise exceptions.ScriptInvocationException(script='python',
                                                           arguments=shlexed,
                                                           error=e.message)
        finally:
            sys.argv = original_argv


virtualenv = Virtualenv()
python = Python()

# python.run('/Users/elipolonsky/dev/src/github.com/iliapolo/pyci/setup.py --help')