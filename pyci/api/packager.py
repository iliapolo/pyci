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
from pyci.api.utils import unzip, download
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
        repo (:`str`, optional): The repository full name.
        sha (:`str`, optional): The of the repository.
        path (:`str`, optional): The path to your local working copy of the repository.

    """

    def __init__(self, repo=None, sha=None, path=None):

        if sha and not repo:
            raise exceptions.InvalidArgumentsException('repo must be provided when using sha')

        if sha and path:
            raise exceptions.InvalidArgumentsException("either 'sha' or 'path' is allowed")

        if not sha and not path:
            raise exceptions.InvalidArgumentsException("either 'sha' or 'path' is required")

        self._repo = repo
        self._sha = sha
        self._path = path
        self._runner = LocalCommandRunner()
        self._log_ctx = {
            'repo': self._repo,
            'sha': self._sha,
            'path': self._path
        }

    def binary(self, name=None, entrypoint=None, target_dir=None):

        """
        Create a binary executable.

        This method will create a self-contained, platform dependent, executable file. The
        executable will include a full copy of the current python version, meaning you will be
        able to run this executable even on environments that dont have python installed.

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
            target_dir (str): Path to a directory where the file will be placed.
               Defaults to the current directory.

        For more information please visit https://www.pyinstaller.org/.

        Raises:
            FileExistsException: Raised if the destination file already exists.
            FileIsADirectoryException: Raised if the destination file already exists and is a
                directory.
            DefaultEntrypointNotFoundException: Raised when a custom entrypoint is not provided
                and the default entry-points pyci looks for are also missing.
            EntrypointNotFoundException: Raised when the custom entrypoint provided does not
                exist in the repository.

        """

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = target_dir or os.getcwd()
            name = name or self._default_name
            entrypoint = entrypoint or self._default_entrypoint

            destination = os.path.join(target_dir, '{0}-{1}-{2}'.format(name,
                                                                        platform.machine(),
                                                                        platform.system()))

            if platform.system().lower() == 'windows':
                destination = '{0}.exe'.format(destination)

            utils.validate_does_not_exist(path=destination)

            dist_dir = os.path.join(temp_dir, 'dist')
            build_dir = os.path.join(temp_dir, 'build')

            script = os.path.join(self._repo_dir, entrypoint)

            if not os.path.exists(script):
                raise exceptions.EntrypointNotFoundException(repo=self._repo,
                                                             entrypoint=entrypoint)

            self._debug('Running pyinstaller...', entrypoint=entrypoint, destination=destination)
            result = self._runner.run('pyinstaller --onefile --distpath {0} '
                                      '--workpath {1} --specpath {2} {3}'
                                      .format(dist_dir,
                                              build_dir,
                                              temp_dir,
                                              script))

            self._debug('Finished running pyinstaller', entrypoint=entrypoint,
                        destination=destination)

            if result.std_err:
                self._debug(result.std_err)

            if result.std_out:
                self._debug(result.std_out)

            actual_name = utils.lsf(dist_dir)[0]

            package_path = os.path.join(dist_dir, actual_name)
            self._debug('Copying package to destination...', src=package_path, dst=destination)
            shutil.copy(package_path, destination)

            self._debug('Packaged successfully.', package=destination)
            return os.path.abspath(destination)
        finally:
            shutil.rmtree(temp_dir)

    def wheel(self, target_dir=None, universal=False):

        """
        Create a wheel package.

        This method will create a wheel package, according the the regular python wheel standards.

        Under the hood, this uses the bdist_wheel command provider by the wheel project.

        Args:
            target_dir (str): Path to the directory the wheel will be placed in.
            universal (bool): True if the created will should be universal, False otherwise.

        Raises:
            FileExistsException: Raised if the destination file already exists.
            FileIsADirectoryException: Raised if the destination file already exists and is a
                directory.

        For more information please visit https://pythonwheels.com/.

        """

        temp_dir = tempfile.mkdtemp()
        try:

            target_dir = target_dir or os.getcwd()

            dist_dir = os.path.join(temp_dir, 'dist')
            bdist_dir = os.path.join(temp_dir, 'bdist')

            command = 'python setup.py bdist_wheel --bdist-dir {0} --dist-dir {1}'\
                      .format(bdist_dir, dist_dir)

            if universal:
                command = '{0} --universal'.format(command)

            self._debug('Running bdist_wheel...', universal=universal)
            result = self._runner.run(command, cwd=self._repo_dir)
            self._debug('Finished running bdist_wheel.', universal=universal)

            if result.std_err:
                self._debug(result.std_err)

            if result.std_out:
                self._debug(result.std_out)

            actual_name = utils.lsf(dist_dir)[0]

            destination = os.path.join(target_dir, actual_name)

            utils.validate_does_not_exist(path=destination)

            shutil.copy(os.path.join(dist_dir, actual_name), destination)
            self._debug('Packaged successfully.', package=destination)
            return os.path.abspath(destination)

        finally:
            shutil.rmtree(temp_dir)

    def clean(self):

        """
        Clean the resources this packager instance used.

        """

        shutil.rmtree(self._repo_dir)
        delattr(self, '_repo_dir')

    @cachedproperty
    def _repo_dir(self):

        if self._path:

            self._debug('Copying local repository to temp directory...')
            temp_dir = tempfile.mkdtemp()
            repo_copy = os.path.join(temp_dir, 'repo')
            shutil.copytree(self._path, repo_copy)
            self._debug('Successfully copied repo.', repo_copy=repo_copy)
            return repo_copy

        repo_base_name = '/'.join(self._repo.split('/')[1:])

        self._debug('Fetching repository...')
        url = 'https://github.com/{0}/archive/{1}.zip'.format(self._repo, self._sha)
        archive = download(url)
        repo_dir = unzip(archive=archive)
        self._debug('Successfully fetched repository.', repo_dir=repo_dir)

        return os.path.join(repo_dir, '{0}-{1}'.format(repo_base_name, self._sha))

    @cachedproperty
    def _default_name(self):

        setup_py_file = os.path.join(self._repo_dir, 'setup.py')

        try:
            utils.validate_file_exists(setup_py_file)
        except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException) as e:
            raise exceptions.NotPythonProjectException(repo=self._repo, cause=str(e))

        return self._runner.run('python {0} --name'.format(setup_py_file)).std_out

    @cachedproperty
    def _default_entrypoint(self):

        # first look for a spec file in the repository root.
        spec_file_basename = '{0}.spec'.format(self._default_name)
        spec_file_path = os.path.join(self._repo_dir, spec_file_basename)
        try:
            utils.validate_file_exists(path=spec_file_path)
            return spec_file_path
        except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException):
            pass

        # now look for a main.py file
        top_level_pacakge = self._find_top_level_package()
        script_file = os.path.join(top_level_pacakge, 'shell', 'main.py')
        full_path = os.path.join(self._repo_dir, script_file)
        try:
            utils.validate_file_exists(path=full_path)
            return full_path
        except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException):
            pass

        raise exceptions.DefaultEntrypointNotFoundException(repo=self._repo,
                                                            name=self._default_name,
                                                            top_level_package=top_level_pacakge)

    def _find_top_level_package(self):

        directories = utils.lsd(self._repo_dir)

        possibles = set()

        for directory in directories:
            if os.path.exists(os.path.join(self._repo_dir, directory, '__init__.py')):
                possibles.add(directory)

        if not possibles:
            raise exceptions.PackageNotFound(repo=self._repo)

        if len(possibles) > 1:
            raise exceptions.MultiplePackagesFound(repo=self._repo, packages=possibles)

        return possibles.pop()

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)
