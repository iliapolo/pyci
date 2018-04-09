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
import shutil
import tempfile

from pyci.api import logger, exceptions
from pyci.api.runner import LocalCommandRunner


class Packager(object):

    def __init__(self):
        self._logger = logger.get_logger('api.packager.Packager')
        self._runner = LocalCommandRunner()

    def binary(self, entrypoint, name, target_dir=None):

        target_dir = target_dir or os.getcwd()
        entrypoint = os.path.abspath(entrypoint)
        name = '{0}-{1}-{2}'.format(name, platform.machine(), platform.system())

        target = os.path.join(target_dir, name)

        if os.path.exists(target):
            raise exceptions.BinaryAlreadyExists(path=target)

        temp_dir = tempfile.mkdtemp()
        try:
            self._runner.run('pyinstaller --onefile --name {0} --distpath {1} --workpath {2} '
                             '--specpath {3} {4}'
                             .format(name,
                                     os.path.join(temp_dir, 'dist'),
                                     os.path.join(temp_dir, 'build'),
                                     temp_dir,
                                     entrypoint),
                             stdout_pipe=False)
            package_path = os.path.join(temp_dir, 'dist', name)

            shutil.copy(package_path, target_dir)
            package_path = os.path.join(target_dir, name)
            self._logger.debug('Packaged successfully: {0}'.format(package_path))
            return package_path
        finally:
            shutil.rmtree(temp_dir)

    def wheel(self):
        raise NotImplementedError()
