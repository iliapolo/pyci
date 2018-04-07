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
import platform
import shutil
import tempfile

from boltons.cacheutils import cachedproperty

from pyci.api import logger, exceptions
from pyci.api import utils
from pyci.api.runner import LocalCommandRunner

log = logger.get_logger(__name__)


class Packager(object):

    """
    Provides packaging capabilities.

    A packager instance is associated with a specific version of your repository, and is capable
    of packing various formats of it.

    If you specify a sha, the packager will download your repository from that sha and
    operate on it. If you specify a local path, it will create a copy of your local
    repository version and operate on that, in which case, the sha argument is irrelevant.

    Args:
        repo (:str, optional): The repository full name.
        sha (:str, optional): The of the repository.
        path (:str, optional): The path to your local working copy of the repository.

    """

    def __init__(self, repo=None, sha=None, path=None, target_dir=None):

        if sha and not repo:
            raise exceptions.InvalidArgumentsException('Must pass repo as well when passing sha')

        if sha and path:
            raise exceptions.InvalidArgumentsException("Either 'sha' or 'path' is allowed")

        if repo and path:
            raise exceptions.InvalidArgumentsException("Either 'repo' or 'path' is allowed")

        if not sha and not path:
            raise exceptions.InvalidArgumentsException("Either 'sha' or 'path' is required")

        if target_dir:
            utils.validate_directory_exists(target_dir)

        if path:
            utils.validate_directory_exists(path)

        self._repo = repo
        self._target_dir = target_dir
        self._sha = sha
        self._path = os.path.abspath(path) if path else None
        self._runner = LocalCommandRunner()
        self._repo_dir = self._create_repo()
        self._log_ctx = {
            'repo': self._repo,
            'sha': self._sha,
            'path': self._path
        }

    @property
    def target_dir(self):
        return self._target_dir

    @target_dir.setter
    def target_dir(self, target_dir):
        utils.validate_directory_exists(target_dir)
        self._target_dir = target_dir

    @property
    def repo_dir(self):
        return self._repo_dir

    @staticmethod
    def create(repo=None, sha=None, path=None, target_dir=None):
        return Packager(repo=repo, sha=sha, path=path, target_dir=target_dir)

    def binary(self, name=None, entrypoint=None):

        """
        Create a binary executable.

        This method will create a self-contained, platform dependent, executable file. The
        executable will include a full copy of the current python version, meaning you will be
        able to run this executable even on environments that don't have python installed.

        Under the hood, this uses the PyInstaller project.

        Args:
            name (str): The base name of the target file. The final name will be in the
               form of: <name>-<platform-machine>-<platform-system> (e.g pyci-x86_64-Darwin).
               Defaults to the 'name' specified in your setup.py file.
            entrypoint (:`str`, optional): Path to a script file from which the executable
               is built. This can either by a .py or a .spec file.
               By default, the packager will look for the following files (in order):
                   - <name>.spec
                   - shell/main.py

        For more information please visit https://www.pyinstaller.org/.

        Raises:
            FileExistsException: Raised if the destination file already exists.
            DirectoryDoesntExistException: Raised if the destination directory does not exist.
            DefaultEntrypointNotFoundException: Raised when a custom entrypoint is not provided
                and the default entry-points pyci looks for are also missing.
            EntrypointNotFoundException: Raised when the custom entrypoint provided does not
                exist in the repository.

        """

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = self.target_dir or os.getcwd()

            name = name or self._default_name
            entrypoint = entrypoint or self._default_entrypoint

            destination = os.path.join(target_dir, '{0}-{1}-{2}'
                                       .format(name, platform.machine(), platform.system()))

            if platform.system().lower() == 'windows':
                destination = '{0}.exe'.format(destination)

            utils.validate_file_does_not_exist(path=destination)

            dist_dir = os.path.join(temp_dir, 'dist')
            build_dir = os.path.join(temp_dir, 'build')

            script = os.path.join(self._repo_dir, entrypoint)

            if not os.path.exists(script):
                raise exceptions.EntrypointNotFoundException(repo=self._repo,
                                                             entrypoint=entrypoint)

            self._debug('Running pyinstaller...', entrypoint=entrypoint, destination=destination)
            self._runner.run(
                '{} '
                '--onefile '
                '--distpath {} '
                '--workpath {} '
                '--specpath {} {}'
                .format(utils.get_executable('pyinstaller'),
                        dist_dir,
                        build_dir,
                        temp_dir,
                        script))

            self._debug('Finished running pyinstaller', entrypoint=entrypoint,
                        destination=destination)

            actual_name = utils.lsf(dist_dir)[0]

            package_path = os.path.join(dist_dir, actual_name)
            self._debug('Copying package to destination...', src=package_path, dst=destination)
            shutil.copy(package_path, destination)

            self._debug('Packaged successfully.', package=destination)
            return os.path.abspath(destination)
        finally:
            utils.rmf(temp_dir)

    def wheel(self, universal=False):

        """
        Create a wheel package.

        This method will create a wheel package, according the the regular python wheel standards.

        Under the hood, this uses the bdist_wheel command provider by the wheel project.

        Args:
            universal (bool): True if the created will should be universal, False otherwise.

        Raises:
            FileExistsException: Raised if the destination file already exists.
            DirectoryDoesntExistException: Raised if the destination directory does not exist.

        For more information please visit https://pythonwheels.com/.

        """

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = self.target_dir or os.getcwd()

            dist_dir = os.path.join(temp_dir, 'dist')
            bdist_dir = os.path.join(temp_dir, 'bdist')

            command = '{} setup.py bdist_wheel --bdist-dir {} --dist-dir {}'\
                      .format(utils.get_executable('python'), bdist_dir, dist_dir)

            if universal:
                command = '{0} --universal'.format(command)

            self._debug('Running bdist_wheel...', universal=universal)
            result = self._runner.run(command, cwd=self._repo_dir)
            self._debug('Finished running bdist_wheel.', universal=universal)

            self._debug(result.std_out)

            actual_name = utils.lsf(dist_dir)[0]

            destination = os.path.join(target_dir, actual_name)

            utils.validate_file_does_not_exist(path=destination)

            shutil.copy(os.path.join(dist_dir, actual_name), destination)
            self._debug('Packaged successfully.', package=destination)
            return os.path.abspath(destination)

        finally:
            utils.rmf(temp_dir)

    def _create_repo(self):

        if self._path:
            repo_dir = self._path
        else:
            repo_dir = utils.download_repo(self._repo, self._sha)

        setup_py_file = os.path.join(repo_dir, 'setup.py')

        try:
            utils.validate_file_exists(setup_py_file)
        except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException) as e:
            raise exceptions.NotPythonProjectException(
                repo=self._repo,
                cause=str(e),
                sha=self._sha)

        return repo_dir

    @cachedproperty
    def _default_name(self):
        setup_py_file = os.path.join(self._repo_dir, 'setup.py')
        return self._runner.run('{} {} --name'.format(utils.get_executable('python'),
                                                      setup_py_file)).std_out

    @cachedproperty
    def _default_entrypoint(self):

        expected_paths = [
            '{0}.spec'.format(self._default_name),
            '{0}.spec'.format(self._default_name.replace('-', '_')),
            '{0}.spec'.format(self._default_name.replace('-', '')),
            os.path.join(self._default_name.replace('-', '_'), 'shell', 'main.py'),
            os.path.join(self._default_name.replace('-', ''), 'shell', 'main.py')
        ]

        for path in expected_paths:
            try:
                full_path = os.path.join(self._repo_dir, path)
                utils.validate_file_exists(path=full_path)
                return full_path
            except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException):
                pass

        raise exceptions.DefaultEntrypointNotFoundException(
            repo=self._repo, name=self._default_name, expected_paths=expected_paths)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)
