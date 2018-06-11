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
import logging

import click
import six

from pyci.api.logger import Logger as ApiLogger

try:
    # noinspection PyStatementEffect
    # pylint: disable=pointless-statement
    unicode
    _unicode = True
except NameError:
    _unicode = False


RIGHT_ARROW = '\xe2\x86\x92'
ASTRIX = '*'
CHECK_MARK = '\xe2\x9c\x93'
X_MARK = '\xe2\x9c\x97'


def get():
    return log


class _Logger(object):

    INDENT_SIZE = 2

    _indent = 0

    _last_break_line = True

    def __init__(self):

        self._indent = 0
        self._last_break_line = True

        self._logger = ApiLogger(name='pyci')

    @property
    def logger(self):
        return self._logger

    def sub(self):
        self._indent = self._indent - self.INDENT_SIZE

    def add(self):
        self._indent = self._indent + self.INDENT_SIZE

    def checkmark(self):
        self._unicode(' {}'.format(CHECK_MARK), break_line=True, fg='green')
        self._last_break_line = True

    def xmark(self):
        self._unicode(' {}'.format(X_MARK), break_line=True, fg='red')
        self._last_break_line = True

    def right_arrow(self):
        self._unicode('{} '.format(RIGHT_ARROW), break_line=False)
        self._last_break_line = False

    def astrix(self):
        click.secho('{} '.format(ASTRIX), nl=False)
        self._last_break_line = False

    def echo(self, message, fg=None, break_line=True, add=False, prefix=True):
        if self._is_debug():
            self.info(message)
        else:

            prefix_char = None

            if not self._last_break_line or not prefix:
                pass

            else:
                prefix_char = RIGHT_ARROW if add else ASTRIX
                click.echo(' ' * self._indent, nl=False)

            if break_line:
                message = message + os.linesep

            if add:
                self.add()

            if prefix_char == RIGHT_ARROW:
                self.right_arrow()
            if prefix_char == ASTRIX:
                self.astrix()

            self._last_break_line = break_line

            click.secho(message, nl=False, fg=fg)

    def info(self, message):
        self._logger.info(message + os.linesep)

    def debug(self, message):
        self._logger.debug(message + os.linesep)

    def warn(self, message):
        self._logger.warn(message + os.linesep)

    def error(self, message):
        if self._is_debug():
            self._logger.error(message + os.linesep)
        else:
            self.echo('', prefix=False)
            self.echo('ERROR: {}'.format(message), prefix=False, fg='red')

    def _is_debug(self):
        return self._logger.logger.isEnabledFor(logging.DEBUG)

    def _unicode(self, char, fg=None, break_line=True):
        if self._is_debug():
            if break_line:
                self.info('')
        else:
            try:
                click.secho(char, nl=break_line, fg=fg)
            except BaseException as e:
                self.debug('Cant print the Unicode character: {}'.format(str(e)))
                click.echo('', nl=break_line)


class NoLineBreakStreamHandler(logging.StreamHandler):

    def emit(self, record):

        try:
            msg = self.format(record)
            stream = self.stream
            fs = "%s"
            if not _unicode:
                stream.write(fs % msg)
            else:
                try:
                    if isinstance(msg, six.text_type) and getattr(stream, 'encoding', None):
                        ufs = u'%s'
                        try:
                            stream.write(ufs % msg)
                        except UnicodeEncodeError:
                            stream.write((ufs % msg).encode(stream.encoding))
                    else:
                        stream.write(fs % msg)
                except UnicodeError:
                    stream.write(fs % msg.encode("UTF-8"))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as e:
            log.error(str(e))
            self.handleError(record)


log = _Logger()
