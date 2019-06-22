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
import logging
import os
import platform
import shutil
import tempfile
import contextlib

from boltons.cacheutils import cachedproperty

from pyci.api import logger, exceptions
from pyci.api import utils
from pyci.api.runner import LocalCommandRunner
from pyci.resources import get_text_resource
from pyci.resources import get_binary_resource


DEFAULT_PY_INSTALLER_VERSION = '3.4'
DEFAULT_WHEEL_VERSION = '0.33.4'


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
        target_dir (:str, optional): Target directory where packages will be created.

    """

    def __init__(self, repo=None, sha=None, path=None, target_dir=None, log=None):

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
        self._target_dir = target_dir or os.getcwd()
        self._sha = sha
        self._path = os.path.abspath(path) if path else None
        self._logger = log or logger.Logger(__name__)
        self._runner = LocalCommandRunner(log=self._logger)
        self._log_ctx = {
            'repo': self._repo,
            'sha': self._sha,
            'path': self._path
        }
        self._repo_dir = self._create_repo()

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
    def create(repo=None, sha=None, path=None, target_dir=None, log=None):
        return Packager(repo=repo,
                        sha=sha,
                        path=path,
                        target_dir=target_dir,
                        log=log)

    def binary(self, name=None, entrypoint=None, pyinstaller_version=None):

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
                   - <name>/shell/main.py
            pyinstaller_version (:str, optional): Which PyInstaller version to use.

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

            name = name or self._default_name
            entrypoint = entrypoint or self._default_entrypoint(name)

            destination = os.path.join(self.target_dir, '{0}-{1}-{2}'
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

            with self._create_virtualenv(name) as virtualenv:

                self._logger.debug('Installing pyinstaller...')

                pip_path = utils.get_python_executable('pip', exec_home=virtualenv)
                self._runner.run('{} pyinstaller=={}'
                                 .format(self._pip_install(pip_path),
                                         pyinstaller_version or DEFAULT_PY_INSTALLER_VERSION),
                                 cwd=self._repo_dir)

                self._debug('Running pyinstaller...',
                            entrypoint=entrypoint,
                            destination=destination)
                pyinstaller_path = utils.get_python_executable('pyinstaller', exec_home=virtualenv)
                self._runner.run(
                    '{} '
                    '--onefile '
                    '--distpath {} '
                    '--workpath {} '
                    '--specpath {} {}'
                    .format(self._pyinstaller(pyinstaller_path),
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

    def wheel(self, universal=False, wheel_version=None):

        """
        Create a wheel package.

        This method will create a wheel package, according the the regular python wheel standards.

        Under the hood, this uses the bdist_wheel command provider by the wheel project.

        Args:
            universal (bool): True if the created will should be universal, False otherwise.
            wheel_version (:str, optional): Which wheel version to use.

        Raises:
            FileExistsException: Raised if the destination file already exists.
            DirectoryDoesntExistException: Raised if the destination directory does not exist.

        For more information please visit https://pythonwheels.com/.

        """

        temp_dir = tempfile.mkdtemp()
        try:

            dist_dir = os.path.join(temp_dir, 'dist')
            bdist_dir = os.path.join(temp_dir, 'bdist')

            setup_py_file = os.path.join(self._repo_dir, 'setup.py')

            try:
                utils.validate_file_exists(setup_py_file)
            except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException) as e:
                raise exceptions.NotPythonProjectException(repo=self._repo,
                                                           cause=str(e),
                                                           sha=self._sha,
                                                           path=self._path)

            with self._create_virtualenv(self._default_name) as virtualenv:

                self._logger.debug('Installing wheel...')

                pip_path = utils.get_python_executable('pip', exec_home=virtualenv)
                self._runner.run('{} wheel=={}'
                                 .format(self._pip_install(pip_path),
                                         wheel_version or DEFAULT_WHEEL_VERSION),
                                 cwd=self._repo_dir)

                command = '{} {} bdist_wheel --bdist-dir {} --dist-dir {}'.format(
                    utils.get_python_executable('python', exec_home=virtualenv),
                    setup_py_file,
                    bdist_dir,
                    dist_dir)

                if universal:
                    command = '{0} --universal'.format(command)

                self._debug('Running bdist_wheel...', universal=universal)

                self._runner.run(command, cwd=self._repo_dir)

            self._debug('Finished running bdist_wheel.', universal=universal)

            actual_name = utils.lsf(dist_dir)[0]

            destination = os.path.join(self.target_dir, actual_name)

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
            self._debug('Downloading repo {}@{}...'.format(self._repo, self._sha))
            repo_dir = utils.download_repo(self._repo, self._sha)

        return repo_dir

    @cachedproperty
    def _default_name(self):
        setup_py_file = os.path.join(self._repo_dir, 'setup.py')
        with open(setup_py_file) as f:
            try:
                return utils.extract_name_from_setup_py(f.read())
            except exceptions.RegexMatchFailureException as e:
                raise exceptions.FailedExtractingNameFromSetupPyException(repo=self._repo,
                                                                          sha=self._sha,
                                                                          path=self._path,
                                                                          cause=str(e))

    def _default_entrypoint(self, name):

        expected_paths = [
            '{0}.spec'.format(name),
            os.path.join(name, 'shell', 'main.py')
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

    @contextlib.contextmanager
    def _create_virtualenv(self, name, python=None):

        temp_dir = tempfile.mkdtemp()

        virtualenv_path = os.path.join(temp_dir, name)

        self._debug('Creating virtualenv {}'.format(virtualenv_path))

        interpreter = python

        if not interpreter:

            if utils.is_pyinstaller():
                interpreter = utils.which('python')
                if not interpreter:
                    raise exceptions.PythonNotFoundException()

            else:
                interpreter = utils.get_python_executable('python')

        def _create_virtualenv_dist():

            dist_directory = os.path.join(temp_dir, 'virtualenv-dist')
            support_directory = os.path.join(dist_directory, 'virtualenv_support')

            os.makedirs(dist_directory)
            os.makedirs(support_directory)

            _virtualenv_py = os.path.join(dist_directory, 'virtualenv.py')

            def _write_support_wheel(_wheel):

                with open(os.path.join(support_directory, _wheel), 'wb') as _w:
                    _w.write(get_binary_resource(os.path.join('virtualenv_support', _wheel)))

            with open(_virtualenv_py, 'w') as venv_py:
                venv_py.write(get_text_resource('virtualenv.py'))

            _write_support_wheel('pip-19.1.1-py2.py3-none-any.whl')
            _write_support_wheel('setuptools-41.0.1-py2.py3-none-any.whl')

            return _virtualenv_py

        virtualenv_py = _create_virtualenv_dist()

        create_virtualenv_command = '{} {} --no-wheel {}'.format(interpreter,
                                                                 virtualenv_py,
                                                                 virtualenv_path)

        setup_py_file = os.path.join(self._repo_dir, 'setup.py')
        requirements_file = os.path.join(self._repo_dir, 'requirements.txt')

        self._runner.run(create_virtualenv_command, cwd=self._repo_dir)

        pip_path = utils.get_python_executable('pip', exec_home=virtualenv_path)

        requires = None

        if os.path.exists(requirements_file):

            # Simply use the requirements file.
            self._debug('Using requirements file: {}'.format(requirements_file))
            requires = requirements_file

        elif os.path.exists(setup_py_file):

            # Dump the 'install_requires' argument from setup.py into a requirements file.
            egg_base = os.path.join(temp_dir, 'egg-base')
            os.mkdir(egg_base)

            self._debug('Dumping requirements file for {}'.format(name))
            self._runner.run('{} {} egg_info --egg-base {}'.format(interpreter, setup_py_file, egg_base),
                             cwd=self._repo_dir)

            requires = None
            for dirpath, _, filenames in os.walk(egg_base):
                if 'requires.txt' in filenames:
                    requires = os.path.join(dirpath, 'requires.txt')

            if not requires:
                # Something is really wrong if this happens
                raise RuntimeError('Unable to create requires.txt file')

        if requires:
            command = '{} -r {}'.format(self._pip_install(pip_path), requires)
            self._debug('Installing {} requirements...'.format(name))
            self._runner.run(command, cwd=self._repo_dir)

        self._debug('Successfully created virtualenv {}'.format(virtualenv_path))

        try:
            yield virtualenv_path
        finally:
            utils.rmf(temp_dir)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        self._logger.debug(message, **kwargs)

    def _pip_install(self, pip_path):

        command = '{} install'.format(pip_path)
        if self._logger.isEnabledFor(logging.DEBUG):
            command = '{}'.format(command)
        return command

    def _pyinstaller(self, pyinstaller_path):

        command = pyinstaller_path
        if self._logger.isEnabledFor(logging.DEBUG):
            command = '{} --log-level DEBUG'.format(command)
        return command
