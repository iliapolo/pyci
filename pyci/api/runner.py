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
import shlex
import subprocess

from pyci.api import exceptions
from pyci.api import logger

log = logger.get_logger(__name__)


# pylint: disable=too-many-arguments,too-few-public-methods
class LocalCommandRunner(object):

    """
    Provides local command line execution abilities.

    Args:
        host (str): The host string to be displayed in log messages.
    """

    def __init__(self, host='localhost'):
        self._log_ctx = {
            'host': host
        }

    def run(self, command, exit_on_failure=True, cwd=None, execution_env=None, pipe=True):

        """
        Runs the specified command.

        The output of the execution will be piped and returned in the return value of this method.
        However, if the current logger is configured from the DEBUG level, the output will be
        displayed immediately and the return value will not contain the output.
        The above also applied for the standard error stream.

        Args:
            command (:str:list): The command to execute.
            exit_on_failure: True to raise an exception if the execution failed, False otherwise.
                In case you pass False, you can examine the error stream by
                using .std_err of the return value.
            cwd (str): The directory to execute the command in.
            execution_env (dict): Additional environment for the execution. (on top of the
                current one)
            pipe (bool): True to pipe stdout and stderr, False to print in real time.

        Raises:
            exceptions.CommandExecutionException: Raised when the execution failed and the
                exist_on_failure argument is True.

        Returns:
            CommandExecutionResponse: A response object containing necessary information about
                the execution:
                    - the command.
                    - the output.
                    - the error.
                    - the exist code.

        """
        if isinstance(command, list):
            popen_args = command
        else:
            popen_args = _shlex_split(command)

        self._debug('Running command...', command=command)

        command_env = os.environ.copy()
        command_env.update(execution_env or {})
        p = subprocess.Popen(args=popen_args,
                             stdout=subprocess.PIPE if pipe else None,
                             stderr=subprocess.PIPE if pipe else None,
                             cwd=cwd,
                             env=command_env,
                             universal_newlines=True)
        out, err = p.communicate()
        if out:
            out = out.rstrip()
        if err:
            err = err.rstrip()

        self._debug('Finished running command.', command=command, exit_code=p.returncode)

        if p.returncode != 0:
            error = exceptions.CommandExecutionException(
                command=command,
                error=err,
                output=out,
                code=p.returncode)
            if exit_on_failure:
                raise error

        return CommandExecutionResponse(
            command=command,
            std_out=out,
            std_err=err,
            return_code=p.returncode)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)


def _shlex_split(command):
    lex = shlex.shlex(command, posix=True)
    lex.whitespace_split = True
    lex.escape = ''
    return list(lex)


# pylint: disable=too-few-public-methods
class CommandExecutionResponse(object):

    def __init__(self, command, std_out, std_err, return_code):
        self.command = command
        self.std_out = std_out
        self.std_err = std_err
        self.return_code = return_code
