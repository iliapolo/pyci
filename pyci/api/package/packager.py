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

import sys
import copy
import logging
import os
import platform
import shutil
import tempfile
import contextlib

from boltons.cacheutils import cachedproperty
from jinja2 import Template

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

    If you specify a sha (and repo), the packager will download your repository from that sha and
    operate on it. If you specify a local path, it will operate directly on that path,
    in which case, the sha and repo arguments are irrelevant.

    Args:

        repo (:str, optional): The repository full name.

        sha (:str, optional): The of the repository.

        path (:str, optional): The path to your local working copy of the repository.

        target_dir (:str, optional): Target directory where packages will be created.

        python (:str, optional): The python interpreter to use for packaging.
            If not specified, the first 'python' program found in your PATH will be used.

    """

    def __init__(self, repo=None, sha=None, path=None, target_dir=None, python=None):

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

        self._repo_location = path if path else '{}@{}'.format(repo, sha)
        self._python = python
        self._target_dir = target_dir or os.getcwd()
        self._logger = logger.Logger(__name__)
        self._runner = LocalCommandRunner(log=self._logger)
        self._log_ctx = {
            'repo': self._repo_location,
        }
        self._repo_dir = self._create_repo(path, sha, repo)

    def _create_repo(self, path, sha, repo):

        if path:
            repo_dir = path
        else:
            self._debug('Downloading {}...'.format(self._repo_location))
            repo_dir = utils.download_repo(repo, sha)

        return repo_dir

    @staticmethod
    def create(repo=None, sha=None, path=None, target_dir=None, python=None):
        return Packager(repo=repo,
                        sha=sha,
                        path=path,
                        target_dir=target_dir,
                        python=python)

    def binary(self, base_name=None, entrypoint=None, pyinstaller_version=None):

        """
        Create a binary executable.

        This method will create a self-contained, platform dependent, executable file.

        Under the hood, this uses the PyInstaller project.

        For more information please visit https://www.pyinstaller.org/

        Args:

            base_name (:str, optional):

                The base name of the target file. The final name will be in the
                form of: <name>-<platform-machine>-<platform-system> (e.g pyci-x86_64-Darwin).
                Defaults to the 'name' specified in your setup.py file.

            entrypoint (:str, optional):

                Path to a script file from which the executable
                is built. This can either by a .py or a .spec file.
                By default, the packager will look for the entry point specified in setup.py.

            pyinstaller_version (:str, optional):

                Which PyInstaller version to use. Defaults to 3.4.

        Raises:

            BinaryExistsException:

                Destination file already exists.

            DirectoryDoesntExistException:

                Destination directory does not exist.

            DefaultEntrypointNotFoundException:

                A custom entrypoint is not provided and the default entry-points
                pyci looks for are also missing.

            EntrypointNotFoundException:

                The provided custom entrypoint provided does not exist in the repository.

            MultipleDefaultEntrypointsFoundException:

                If setup.py contains multiple entrypoints specification.

        """

        temp_dir = tempfile.mkdtemp()
        try:

            base_name = base_name or self._name
            entrypoint = entrypoint or self._entrypoint

            destination = os.path.join(self._target_dir, '{0}-{1}-{2}'
                                       .format(base_name, platform.machine(), platform.system()))

            if platform.system().lower() == 'windows':
                destination = '{0}.exe'.format(destination)

            try:
                utils.validate_file_does_not_exist(path=destination)
            except exceptions.FileExistException as e:
                raise exceptions.BinaryExistsException(path=e.path)

            dist_dir = os.path.join(temp_dir, 'dist')
            build_dir = os.path.join(temp_dir, 'build')

            script = os.path.join(self._repo_dir, entrypoint)

            if not os.path.exists(script):
                raise exceptions.EntrypointNotFoundException(repo=self._repo_location,
                                                             entrypoint=entrypoint)

            with self._create_virtualenv(base_name) as virtualenv:

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

        Under the hood, this uses the bdist_wheel command provided by the wheel project.

        For more information please visit https://pythonwheels.com/

        Args:
            universal (:bool, optional): True if the created will should be universal, False otherwise.
            wheel_version (:str, optional): Which wheel version to use.

        Raises:
            WheelExistsException: Destination file already exists.
            DirectoryDoesntExistException: Destination directory does not exist.

        """

        temp_dir = tempfile.mkdtemp()
        try:

            dist_dir = os.path.join(temp_dir, 'dist')
            bdist_dir = os.path.join(temp_dir, 'bdist')

            if not os.path.exists(self._setup_py_path):
                raise exceptions.SetupPyNotFoundException(repo=self._repo_location)

            name = self._name

            with self._create_virtualenv(name) as virtualenv:

                self._logger.debug('Installing wheel...')

                pip_path = utils.get_python_executable('pip', exec_home=virtualenv)
                self._runner.run('{} wheel=={}'
                                 .format(self._pip_install(pip_path),
                                         wheel_version or DEFAULT_WHEEL_VERSION),
                                 cwd=self._repo_dir)

                command = '{} {} bdist_wheel --bdist-dir {} --dist-dir {}'.format(
                    utils.get_python_executable('python', exec_home=virtualenv),
                    self._setup_py_path,
                    bdist_dir,
                    dist_dir)

                if universal:
                    command = '{0} --universal'.format(command)

                self._debug('Running bdist_wheel...', universal=universal)

                self._runner.run(command, cwd=self._repo_dir)

            self._debug('Finished running bdist_wheel.', universal=universal)

            actual_name = utils.lsf(dist_dir)[0]

            destination = os.path.join(self._target_dir, actual_name)

            try:
                utils.validate_file_does_not_exist(path=destination)
            except exceptions.FileExistException as e:
                raise exceptions.WheelExistsException(path=e.path)

            shutil.copy(os.path.join(dist_dir, actual_name), destination)
            self._debug('Packaged successfully.', package=destination)
            return os.path.abspath(destination)

        finally:
            utils.rmf(temp_dir)

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    def nsis(self, binary_path,
             version=None,
             output=None,
             author=None,
             url=None,
             copyright_string=None,
             description=None,
             license_path=None):

        """
        Create a windows installer package.

        This method will produce an executable installer (.exe) that, when executed, will install
        the provided binary into "Program Files". In addition, it will manipulate the system PATH
        variable on the target machine so that the binary can be executed from any directory.

        Under the hood, this uses the NSIS project.

        For more information please visit https://nsis.sourceforge.io/Main_Page

        Args:

            binary_path (:str): True if the created will should be universal, False otherwise.

            version (:str, optional): Version string metadata. Defaults to the 'version' argument
                in your setup.py file.

            output (:str, optional): Target file to create. Defaults to
                {binary-path-basename}-installer.exe

            author (:str, optional): Package author. Defaults to the value specified in setup.py.

            url (:str, optional): URL to the package website. Defaults to the value specified in setup.py.

            copyright_string (:str, optional): Copyright. Defaults to an empty string.

            description (:str, optional): Package description. Defaults to the value specified in setup.py.

            license_path (:str, optional): Path to a license file. Defaults to the value specified in setup.py.

        Raises:

            LicenseNotFoundException: License file doesn't exist.

            BinaryFileDoesntExistException: The provided binary file doesn't exist.

            FileExistsException: Destination file already exists.

            DirectoryDoesntExistException: The destination directory does not exist.

        """

        if not utils.is_windows():
            raise exceptions.WrongPlatformException(expected='Windows')

        if not binary_path:
            raise exceptions.InvalidArgumentsException('Must pass binary_path')

        try:
            self._debug('Validating binary exists: {}'.format(binary_path))
            utils.validate_file_exists(binary_path)
        except (exceptions.FileDoesntExistException, exceptions.FileIsADirectoryException):
            raise exceptions.BinaryDoesntExistException(binary_path)

        try:
            version = version or self._version
            self._debug('Validating version string: {}'.format(version))
            utils.validate_nsis_version(version)
        except exceptions.InvalidNSISVersionException as err:
            tb = sys.exc_info()[2]
            try:
                # Auto-correction attempt for standard python versions
                version = '{}.0'.format(version)
                utils.validate_nsis_version(version)
            except exceptions.InvalidNSISVersionException:
                utils.raise_with_traceback(err, tb)

        installer_base_name = os.path.basename(binary_path).replace('.exe', '')
        try:
            name = self._name
        except BaseException as e:
            self._debug('Unable to extract default name from setup.py: {}. Using binary base name...'.format(str(e)))
            name = installer_base_name

        installer_name = '{}-installer'.format(installer_base_name)
        copyright_string = copyright_string or ''

        destination = os.path.abspath(output or '{}.exe'.format(
            os.path.join(self._target_dir, installer_name)))
        self._debug('Validating destination file does not exist: {}'.format(destination))
        utils.validate_file_does_not_exist(destination)

        target_directory = os.path.abspath(os.path.join(destination, os.pardir))

        self._debug('Validating target directory exists: {}'.format(target_directory))
        utils.validate_directory_exists(target_directory)

        try:
            license_path = license_path or os.path.abspath(os.path.join(self._repo_dir,
                                                                        self._license))
            self._debug('Validating license file exists: {}'.format(license_path))
            utils.validate_file_exists(license_path)
        except (exceptions.FileDoesntExistException, exceptions.FileIsADirectoryException) as e:
            raise exceptions.LicenseNotFoundException(str(e))

        author = author or self._author
        url = url or self._url
        description = description or self._description

        config = {
            'name': name,
            'author': author,
            'website': url,
            'copyright': copyright_string,
            'license_path': license_path,
            'binary_path': binary_path,
            'description': description,
            'installer_name': installer_name
        }

        temp_dir = tempfile.mkdtemp()

        try:

            support = 'windows_support'

            template = get_text_resource(os.path.join(support, 'installer.nsi.jinja'))
            nsis_zip_resource = get_binary_resource(os.path.join(support, 'nsis-3.04.zip'))
            path_header_resource = get_text_resource(os.path.join(support, 'path.nsh'))

            self._debug('Rendering nsi template...')
            nsi = Template(template).render(**config)
            installer_path = os.path.join(temp_dir, 'installer.nsi')
            with open(installer_path, 'w') as f:
                f.write(nsi)
            self._debug('Finished rendering nsi template: {}'.format(installer_path))

            self._debug('Writing path header file...')
            path_header_path = os.path.join(temp_dir, 'path.nsh')
            with open(path_header_path, 'w') as header:
                header.write(path_header_resource)
            self._debug('Finished writing path header file: {}'.format(path_header_path))

            self._debug('Extracting NSIS from resources...')

            nsis_archive = os.path.join(temp_dir, 'nsis.zip')
            with open(nsis_archive, 'wb') as _w:
                _w.write(nsis_zip_resource)
            utils.unzip(nsis_archive, target_dir=temp_dir)
            self._debug('Finished extracting makensis.exe from resources: {}'.format(nsis_archive))

            makensis_path = os.path.join(temp_dir, 'nsis-3.04', 'makensis.exe')
            command = '{} -DVERSION={} {}'.format(makensis_path, version, installer_path)

            self._debug('Creating installer...')
            self._runner.run(command, cwd=temp_dir)

            out_file = os.path.join(temp_dir, '{}.exe'.format(installer_name))

            self._debug('Copying {} to target path...'.format(out_file))
            shutil.copyfile(out_file, destination)
            self._debug('Finished copying installer to target path: {}'.format(destination))

            self._debug('Packaged successfully.', package=destination)

            return destination

        finally:
            utils.rmf(temp_dir)

    @cachedproperty
    def _name(self):
        return self._setup_py_argument('name')

    @cachedproperty
    def _author(self):
        return self._setup_py_argument('author')

    @cachedproperty
    def _version(self):
        return self._setup_py_argument('version')

    @cachedproperty
    def _description(self):
        return self._setup_py_argument('description')

    @cachedproperty
    def _license(self):
        return self._setup_py_argument('license')

    @cachedproperty
    def _url(self):
        return self._setup_py_argument('url')

    @cachedproperty
    def _entrypoint(self):

        entry_points = self._setup_py_argument('entry_points')

        console_scripts = entry_points['console_scripts']

        if len(console_scripts) > 1:
            raise exceptions.MultipleDefaultEntrypointsFoundException(repo=self._repo_location,
                                                                      entrypoints=console_scripts)

        script = console_scripts[0].split('=')[1].strip().split(':')[0].replace('.', os.sep)

        script_path = os.path.join(self._repo_dir, '{}.py'.format(script))

        if not os.path.exists(script_path):
            raise exceptions.ConsoleScriptNotFoundException(repo=self._repo_location, script=script_path)

        return script_path

    @cachedproperty
    def _setup_py_path(self):
        return os.path.join(self._repo_dir, 'setup.py')

    @cachedproperty
    def _setup_py(self):

        with open(self._setup_py_path) as f:
            setup_py = f.read()

        kwargs = {}

        def _setup(*_, **__):
            kwargs.update(__)

        import setuptools

        setup_func = setuptools.setup

        try:

            with tempfile.NamedTemporaryFile() as errors:

                setuptools.setup = _setup

                obj = compile(setup_py, errors.name, mode='exec')

                # pylint: disable=eval-used
                eval(obj)

                return kwargs

        finally:
            setuptools.setup = setup_func

    @cachedproperty
    def _interpreter(self):
        return self._python or self._lookup_interpreter()

    def _lookup_interpreter(self):
        if utils.is_pyinstaller():
            self._debug('Running inside a frozen package...Looking up python interpreter from PATH')
            interpreter = utils.which('python')
        else:
            self._debug('Running inside a python environment...Looking up python interpreter locally')
            interpreter = utils.get_python_executable('python')

        if not interpreter:
            raise exceptions.PythonNotFoundException()

        self._debug('Python interpreter: {}'.format(interpreter))

        return interpreter

    # pylint: disable=too-many-branches
    @contextlib.contextmanager
    def _create_virtualenv(self, name):

        temp_dir = tempfile.mkdtemp()

        virtualenv_path = os.path.join(temp_dir, name)

        self._debug('Creating virtualenv {}'.format(virtualenv_path))

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

        create_virtualenv_command = '{} {} --no-wheel {}'.format(self._interpreter,
                                                                 virtualenv_py,
                                                                 virtualenv_path)

        requirements_file = os.path.join(self._repo_dir, 'requirements.txt')

        self._runner.run(create_virtualenv_command, cwd=self._repo_dir)

        pip_path = utils.get_python_executable('pip', exec_home=virtualenv_path)

        install_command = None

        if os.path.exists(requirements_file):

            self._debug('Using requirements file: {}'.format(requirements_file))
            install_command = '{} -r {}'.format(self._pip_install(pip_path), requirements_file)

        elif os.path.exists(self._setup_py_path):

            self._debug('Using install_requires from setup.py: {}'.format(self._setup_py_path))
            requires = self._setup_py.get('install_requires')
            install_command = '{} {}'.format(self._pip_install(pip_path), ' '.join(requires))

        if install_command:
            self._debug('Installing {} requirements...'.format(name))
            self._runner.run(install_command, cwd=self._repo_dir)

        self._debug('Successfully created virtualenv {}'.format(virtualenv_path))

        try:
            yield virtualenv_path
        finally:
            try:
                utils.rmf(temp_dir)
            except BaseException as e:
                if utils.is_windows():
                    # The temp_dir was populated with files written by a different process
                    # (pip install) On windows, this causes a [Error 5] Access is denied error.
                    # Eventually I will have to fix this - until then, sorry windows users...
                    self._debug("Failed cleaning up temporary directory after creating virtualenv "
                                "{}: {} - You might have some leftovers because of this..."
                                .format(temp_dir, str(e)))
                else:
                    raise

    def _setup_py_argument(self, argument):

        if not os.path.exists(self._setup_py_path):
            err = exceptions.SetupPyNotFoundException(repo=self._repo_location)

        else:
            self._debug('Reading {} from setup.py...'.format(argument))
            value = self._setup_py.get(argument)
            if value is None:
                err = exceptions.MissingSetupPyArgumentException(repo=self._repo_location,
                                                                 argument=argument)
            else:
                return value

        raise exceptions.FailedDetectingPackageMetadataException(argument=argument, reason=err)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        self._logger.debug(message, **kwargs)

    def _pip_install(self, pip_path):

        command = '{} install'.format(pip_path)
        if self._logger.isEnabledFor(logging.DEBUG):
            command = '{} -v'.format(command)
        return command

    def _pyinstaller(self, pyinstaller_path):

        command = pyinstaller_path
        if self._logger.isEnabledFor(logging.DEBUG):
            command = '{} --log-level DEBUG'.format(command)
        return command
