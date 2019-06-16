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

import time
import os
import shlex
import subprocess

from pyci.api import exceptions
from pyci.api import logger


# pylint: disable=too-many-arguments,too-few-public-methods
class LocalCommandRunner(object):

    """
    Provides local command line execution abilities.

    Args:
        host (str): The host string to be displayed in log messages.
    """

    def __init__(self, host=None, log=None):
        self._logger = log or logger.Logger(__name__)
        self._host = host
        self._output_logger = logger.Logger(name='runner-output', fmt='%(message)s')

    # pylint: disable=too-many-locals
    def run(self, command, exit_on_failure=True, cwd=None, execution_env=None):

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
            popen_args = shlex_split(command)

        cwd = cwd or os.getcwd()

        self._debug('Running command...', command=command, cwd=cwd)

        command_env = os.environ.copy()
        command_env.update(execution_env or {})
        p = subprocess.Popen(args=popen_args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             cwd=cwd,
                             env=command_env,
                             universal_newlines=True)

        def _is_alive(_p):
            return p.poll() is None

        def _format_line(line):
            return '[{}] {}'.format(self._host, line) if self._host and line else line

        stdout = []
        stderr = []

        while True:
            out = _format_line(p.stdout.readline().strip(os.linesep))
            err = _format_line(p.stderr.readline().strip(os.linesep))
            if not out and not err and not _is_alive(p):
                break
            if out:
                stdout.append(out)
                self._output_logger.debug(out)
            if err:
                stderr.append(err)
                self._output_logger.debug(err)
            time.sleep(0.1)

        out_leftovers, err_leftovers = p.communicate()

        def _log_stream(stream, buf):
            for line in stream.splitlines():

                line = _format_line(line)

                buf.append(line)
                self._output_logger.debug(line)

        _log_stream(out_leftovers, stdout)
        _log_stream(err_leftovers, stderr)

        out = os.linesep.join(stdout)
        err = os.linesep.join(stderr)

        self._debug('Finished running command.', command=command, exit_code=p.returncode, cwd=cwd)

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
        self._logger.debug(message, **kwargs)


def shlex_split(command):
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
