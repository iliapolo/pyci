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

import wryte


loggers = {}


DEFAULT_LOG_LEVEL = 'INFO'


class Logger(object):

    _logger = None

    def __init__(self, name=None, level=DEFAULT_LOG_LEVEL):
        self._name = name
        self._logger = wryte.Wryte(name)
        self._logger.logger.propagate = False
        self.set_level(level)

    @property
    def name(self):
        return self._name

    def set_level(self, level):
        self._logger.set_level(level)

    def info(self, message):
        self._logger.info(message)

    def warning(self, message):
        self._logger.warning(message)

    def warn(self, message):
        self._logger.warn(message)

    def error(self, message):
        self._logger.error(message)

    def debug(self, message):
        self._logger.debug(message)


def get_logger(name):
    if name not in loggers:
        loggers[name] = Logger(name)
    return loggers[name]


def setup_loggers(level=DEFAULT_LOG_LEVEL):
    for logger in loggers.values():
        logger.set_level(level)
