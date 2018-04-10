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
from pyci.api import utils
from pyci.api.downloader import download
from pyci.api.extractor import extract
from pyci.api.runner import LocalCommandRunner


class Packager(object):

    def __init__(self, repo, log_level='info'):
        self._repo = repo
        self._logger = logger.get_logger('api.packager.Packager', level=log_level)
        self._runner = LocalCommandRunner()

    def binary(self, branch, entrypoint=None, name=None, target_dir=None):

        self._logger.debug('Fetching repository...')
        repo_dir = self._fetch_repo(self._repo, branch)
        self._logger.debug('Successfully fetched repository: {0}'.format(repo_dir))

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = target_dir or os.getcwd()
            name = name or self._find_name(repo_dir=repo_dir)
            entrypoint = self._find_entrypoint(name, repo_dir, entrypoint=entrypoint)

            full_name = '{0}-{1}-{2}'.format(name, platform.machine(), platform.system())

            target = os.path.join(target_dir, full_name)

            if os.path.exists(target):
                raise exceptions.BinaryAlreadyExists(path=target)

            self._logger.debug('Binary name will be: {0}'.format(full_name))
            self._logger.debug('Entrypoint assumed as: {0}'.format(entrypoint))

            self._runner.run('pyinstaller --onefile --name {0} --distpath {1} --workpath {2} '
                             '--specpath {3} {4}'
                             .format(full_name,
                                     os.path.join(temp_dir, 'dist'),
                                     os.path.join(temp_dir, 'build'),
                                     temp_dir,
                                     entrypoint),
                             stdout_pipe=False,
                             exit_on_failure=True)
            package_path = os.path.join(target_dir, full_name)
            shutil.copy(os.path.join(temp_dir, 'dist', name), package_path)
            self._logger.debug('Packaged successfully: {0}'.format(package_path))
            return package_path
        finally:
            shutil.rmtree(repo_dir)
            shutil.rmtree(temp_dir)

    def wheel(self):
        raise NotImplementedError()

    def _fetch_repo(self, repo, branch):

        url = 'https://github.com/{0}/archive/{1}.zip'.format(self._repo, branch)
        archive = download(url)
        repo_dir = extract(archive=archive)

        repo_base_name = '/'.join(repo.split('/')[1:])

        return os.path.join(repo_dir, '{0}-{1}'.format(repo_base_name, branch))

    def _find_name(self, repo_dir):

        directories = utils.lsd(repo_dir)

        possibles = set()

        for directory in directories:
            if os.path.exists(os.path.join(repo_dir, directory, '__init__.py')):
                possibles.add(directory)

        if not possibles:
            raise exceptions.PackageNotFound(repo=self._repo)

        if len(possibles) > 1:
            raise exceptions.MultiplePackagesFound(repo=self._repo, packages=possibles)

        return possibles.pop()

    def _find_entrypoint(self, name, repo_dir, entrypoint=None):

        entrypoint = entrypoint or os.path.join(name, 'shell', 'main.py')

        full_path = os.path.join(repo_dir, entrypoint)
        if not os.path.exists(full_path):
            raise exceptions.EntrypointNotFoundException(repo=self._repo, expected_path=entrypoint)

        return full_path
