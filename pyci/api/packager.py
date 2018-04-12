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

from boltons.cacheutils import cachedproperty
from github import Github

from pyci.api import logger, exceptions
from pyci.api import utils
from pyci.api.downloader import download
from pyci.api.extractor import extract
from pyci.api.runner import LocalCommandRunner


log = logger.get_logger(__name__)


class Packager(object):

    # pylint: disable=too-many-arguments
    def __init__(self, repo, access_token=None, sha=None, local_repo_path=None):
        self._repo = repo
        self._sha = sha or self._fetch_default_branch(access_token)
        self._local_repo_path = local_repo_path
        self._runner = LocalCommandRunner()

    def binary(self, entrypoint=None, name=None, target_dir=None):

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = target_dir or os.getcwd()
            name = name or self._find_name(repo_dir=self._repo_dir)
            entrypoint = self._find_entrypoint(name, entrypoint=entrypoint)

            destination = os.path.join(target_dir, '{0}-{1}-{2}'.format(name,
                                                                        platform.machine(),
                                                                        platform.system()))

            if platform.system().lower() == 'windows':
                destination = '{0}.exe'.format(destination)

            if os.path.exists(destination):
                raise exceptions.BinaryAlreadyExists(path=destination)

            log.debug('Binary path will be: {0}'.format(destination))
            log.debug('Entrypoint assumed as: {0}'.format(entrypoint))

            dist_dir = os.path.join(temp_dir, 'dist')
            build_dir = os.path.join(temp_dir, 'build')

            result = self._runner.run('pyinstaller --onefile --distpath {0} '
                                      '--workpath {1} --specpath {2} {3}'
                                      .format(dist_dir, build_dir, temp_dir, entrypoint),
                                      stdout_pipe=False,
                                      exit_on_failure=True)

            if result.std_err:
                log.debug('pyinstaller command error: {0}'.format(result.std_err))

            if result.std_out:
                log.debug('pyinstaller command output: {0}'.format(result.std_out))

            actual_name = utils.lsf(dist_dir)[0]

            shutil.copy(os.path.join(dist_dir, actual_name), destination)
            log.debug('Packaged successfully: {0}'.format(destination))
            return destination
        finally:
            shutil.rmtree(temp_dir)

    def wheel(self, target_dir=None, universal=False):

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = target_dir or os.getcwd()

            dist_dir = os.path.join(temp_dir, 'dist')
            bdist_dir = os.path.join(temp_dir, 'bdist')

            command = 'python setup.py bdist_wheel --bdist-dir {0} --dist-dir {1}'\
                      .format(bdist_dir, dist_dir)

            if universal:
                command = '{0} --universal'.format(command)

            result = self._runner.run(command, cwd=self._repo_dir)

            if result.std_err:
                log.debug('wheel command error: {0}'.format(result.std_err))

            if result.std_out:
                log.debug('wheel command output: {0}'.format(result.std_out))

            actual_name = utils.lsf(dist_dir)[0]

            destination = os.path.join(target_dir, actual_name)

            if os.path.exists(destination):
                raise exceptions.WheelAlreadyExistsException(path=destination)

            shutil.copy(os.path.join(dist_dir, actual_name), destination)
            log.debug('Packaged successfully: {0}'.format(destination))
            return destination

        finally:
            shutil.rmtree(temp_dir)

    def _fetch_default_branch(self, access_token):
        hub = Github(access_token)
        return hub.get_repo(self._repo).default_branch

    @cachedproperty
    def _repo_dir(self):

        repo_base_name = '/'.join(self._repo.split('/')[1:])

        if self._local_repo_path:

            # pylint: disable=fixme
            # TODO document and explain that the 'sha' argument is ignored here

            log.debug('Copying local repository to temp directory...')
            temp_dir = tempfile.mkdtemp()
            repo_copy = os.path.join(temp_dir, repo_base_name)
            shutil.copytree(self._local_repo_path, repo_copy)
            log.debug('Successfully copied repo to: {0}'.format(repo_copy))
            return repo_copy

        log.debug('Fetching repository...')
        url = 'https://github.com/{0}/archive/{1}.zip'.format(self._repo, self._sha)
        archive = download(url)
        repo_dir = extract(archive=archive)
        log.debug('Successfully fetched repository: {0}'.format(repo_dir))

        return os.path.join(repo_dir, '{0}-{1}'.format(repo_base_name, self._sha))

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

    def _find_entrypoint(self, name, entrypoint=None):

        spec_file_name = '{0}.spec'.format(name)
        spec_file = os.path.join(self._repo_dir, spec_file_name)

        if entrypoint is None and os.path.exists(spec_file):
            return spec_file

        script_file = os.path.join(name, 'shell', 'main.py')

        entrypoint = entrypoint or script_file

        full_path = os.path.join(self._repo_dir, entrypoint)
        if not os.path.exists(full_path):
            raise exceptions.EntrypointNotFoundException(repo=self._repo,
                                                         expected_paths=[
                                                             spec_file_name,
                                                             script_file
                                                         ])

        return full_path
