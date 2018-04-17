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

from pyci.api import logger, exceptions
from pyci.api import utils
from pyci.api.utils import extract, download
from pyci.api.runner import LocalCommandRunner

log = logger.get_logger(__name__)


class Packager(object):

    def __init__(self, repo=None, sha=None, path=None):

        if sha and path:
            raise exceptions.InvalidArgumentsException("Either 'sha' or 'path' is allowed")

        if not sha and not path:
            raise exceptions.InvalidArgumentsException("Either 'sha' or 'path' is required")

        self._repo = repo
        self._sha = sha
        self._path = path
        self._runner = LocalCommandRunner()

    def binary(self, entrypoint=None, name=None, target_dir=None):

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = target_dir or os.getcwd()
            name = name or self.name
            entrypoint = entrypoint or self.entrypoint

            destination = os.path.join(target_dir, '{0}-{1}-{2}'.format(name,
                                                                        platform.machine(),
                                                                        platform.system()))

            if platform.system().lower() == 'windows':
                destination = '{0}.exe'.format(destination)

            utils.validate_does_not_exist(path=destination)

            log.debug('Binary path will be: {0}'.format(destination))
            log.debug('Entrypoint assumed as: {0}'.format(entrypoint))

            dist_dir = os.path.join(temp_dir, 'dist')
            build_dir = os.path.join(temp_dir, 'build')

            script = os.path.join(self.repo_dir, entrypoint)

            if not os.path.exists(script):
                raise exceptions.EntrypointNotFoundException(repo=self._repo,
                                                             entrypoint=entrypoint)

            result = self._runner.run('pyinstaller --onefile --distpath {0} '
                                      '--workpath {1} --specpath {2} {3}'
                                      .format(dist_dir,
                                              build_dir,
                                              temp_dir,
                                              script),
                                      stdout_pipe=False)

            if result.std_err:
                log.debug('pyinstaller command error: {0}'.format(result.std_err))

            if result.std_out:
                log.debug('pyinstaller command output: {0}'.format(result.std_out))

            actual_name = utils.lsf(dist_dir)[0]

            shutil.copy(os.path.join(dist_dir, actual_name), destination)
            log.debug('Packaged successfully: {0}'.format(destination))
            return os.path.abspath(destination)
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

            result = self._runner.run(command, cwd=self.repo_dir)

            if result.std_err:
                log.debug('wheel command error: {0}'.format(result.std_err))

            if result.std_out:
                log.debug('wheel command output: {0}'.format(result.std_out))

            actual_name = utils.lsf(dist_dir)[0]

            destination = os.path.join(target_dir, actual_name)

            utils.validate_does_not_exist(path=destination)

            shutil.copy(os.path.join(dist_dir, actual_name), destination)
            log.debug('Packaged successfully: {0}'.format(destination))
            return os.path.abspath(destination)

        finally:
            shutil.rmtree(temp_dir)

    @cachedproperty
    def repo_dir(self):

        if self._path:

            log.debug('Copying local repository to temp directory...')
            temp_dir = tempfile.mkdtemp()
            repo_copy = os.path.join(temp_dir, 'repo')
            shutil.copytree(self._path, repo_copy)
            log.debug('Successfully copied repo to: {0}'.format(repo_copy))
            return repo_copy

        repo_base_name = '/'.join(self._repo.split('/')[1:])

        log.debug('Fetching repository ({0})...'.format(self._sha))
        url = 'https://github.com/{0}/archive/{1}.zip'.format(self._repo, self._sha)
        archive = download(url)
        repo_dir = extract(archive=archive)
        log.debug('Successfully fetched repository: {0}'.format(repo_dir))

        return os.path.join(repo_dir, '{0}-{1}'.format(repo_base_name, self._sha))

    @cachedproperty
    def name(self):

        setup_py_file = os.path.join(self.repo_dir, 'setup.py')

        try:
            utils.validate_file_exists(setup_py_file)
        except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException) as e:
            raise exceptions.NotPythonProjectException(repo=self._repo, cause=str(e))

        return self._runner.run('python {0} --name'.format(setup_py_file)).std_out

    @cachedproperty
    def entrypoint(self):

        # first look for a spec file in the repository root.
        spec_file_basename = '{0}.spec'.format(self.name)
        spec_file_path = os.path.join(self.repo_dir, spec_file_basename)
        try:
            utils.validate_file_exists(path=spec_file_path)
            return spec_file_path
        except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException):
            pass

        # now look for a main.py file
        top_level_pacakge = self._find_top_level_package()
        script_file = os.path.join(top_level_pacakge, 'shell', 'main.py')
        full_path = os.path.join(self.repo_dir, script_file)
        try:
            utils.validate_file_exists(path=full_path)
            return full_path
        except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException):
            pass

        raise exceptions.DefaultEntrypointNotFoundException(repo=self._repo,
                                                            expected_paths=[
                                                                spec_file_basename,
                                                                script_file
                                                            ])

    def _find_top_level_package(self):

        directories = utils.lsd(self.repo_dir)

        possibles = set()

        for directory in directories:
            if os.path.exists(os.path.join(self.repo_dir, directory, '__init__.py')):
                possibles.add(directory)

        if not possibles:
            raise exceptions.PackageNotFound(repo=self._repo)

        if len(possibles) > 1:
            raise exceptions.MultiplePackagesFound(repo=self._repo, packages=possibles)

        return possibles.pop()
