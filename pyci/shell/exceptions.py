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

import click

from pyci.shell import logger

log = logger.get()


class TerminationException(click.ClickException):

    def __init__(self, message, cause, tb):
        self.tb = tb
        self.cause = cause
        super(TerminationException, self).__init__(message or str(cause))

    def show(self, _file=None):
        log.debug(self.tb)
        log.error(self.format_message())
        info = build_info(self.cause)
        if info:
            log.echo(info, fg='yellow', prefix=False)


class ShellException(click.ClickException):
    pass


def build_info(exception):

    info = None

    if hasattr(exception, 'cause'):
        info = '\n' + exception.cause + '\n'

    if hasattr(exception, 'possible_solutions'):
        info = (info or '') + '\nPossible solutions: \n\n' + \
               '\n'.join(['    - ' + solution + '.' for solution in exception.possible_solutions])

    return info
