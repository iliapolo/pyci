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
import re
import shutil
import stat
import sys
import tempfile
import uuid
import zipfile
import six


import requests

from pyci.api import exceptions


def extract_link(commit_message):

    """
    Extracts the link number from a commit message. A link is considered as the first number
    following the '#' sign.
    For example:
        "Implemented feature (#4)" --> link = 4

    Returns:
        int: The link number from the message or None if doesn't exist.
    """

    # pylint: disable=anomalous-backslash-in-string
    p = re.compile('.* ?#(\d+)')
    match = p.match(commit_message)
    if match:
        return int(match.group(1))

    return None


def lsf(directory):

    """
    List file names in a given directory. Only first level files are returned and only the file
    basename, i.e without the directory path.

    Args:
        directory (str): A directory path.

    Returns:
        list: A list of file names.
    """

    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


def rmf(directory):

    """
    Delete the entire directory. This function also handles windows "Access Denied" errors when the
    directory contains read-only files. This function is equivalent to 'rm -rf' on linux systems.

    Args:
        directory (str): Path to the directory to delete.
    """

    def remove_read_only(func, path, _):
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(directory, onerror=remove_read_only)


def validate_file_exists(path):

    """
    Validate that the given path points an existing file.

    Raises:
        FileDoesntExistException: Raised if the path does not exist.
        FileIsADirectoryException: Raised if the given path points to a directory.
    """

    if not os.path.exists(path):
        raise exceptions.FileDoesntExistException(path=path)
    if os.path.isdir(path):
        raise exceptions.FileIsADirectoryException(path=path)


def validate_directory_exists(path):

    """
    Validate that the given path points an existing directory.

    Raises:
        DirectoryDoesntExistException: Raised if the directory doesnt exist.
        DirectoryIsAFileException: Raised if the directory path points to a file.
    """

    if not os.path.exists(path):
        raise exceptions.DirectoryDoesntExistException(path=path)
    if os.path.isfile(path):
        raise exceptions.DirectoryIsAFileException(path=path)


def validate_file_does_not_exist(path):

    """
    Validate that the given path points an existing file.

    Args:
        path (str): The path to validate.

    Raises:
        FileExistException: Raised if the given path points to a file.
        FileIsADirectoryException: Raised if the given path points to a directory.
    """

    if os.path.isfile(path):
        raise exceptions.FileExistException(path=path)
    if os.path.isdir(path):
        raise exceptions.FileIsADirectoryException(path=path)


def unzip(archive, target_dir=None):

    """
    Unzips a zip archive.

    Args:
        archive (str): Path to the zip archive.
        target_dir (:`str`, optional): A directory to unzip the archive to. Defaults to a
            temporary directory.

    Returns:
        str: A directory path to the extracted archive.
    """

    target_dir = target_dir or tempfile.mkdtemp()

    zip_ref = zipfile.ZipFile(archive, 'r')
    zip_ref.extractall(target_dir)
    zip_ref.close()

    return target_dir


def download(url, target=None, headers=None):

    """
    Download a URL to a file.

    Args:
        url (str): The URL to download.
        target (:str, optional): The target file. Defaults to a temporary file.
        headers (:dict, optional): Request headers.

    Returns:
        str: Path to the downloaded file.
    """

    target = target or os.path.join(tempfile.mkdtemp(), str(uuid.uuid4()))

    r = requests.get(url, stream=True, headers=headers or {})
    if r.status_code != 200:
        raise exceptions.DownloadFailedException(url=url, code=r.status_code, err=r.reason)
    with open(target, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    return target


def generate_setup_py(setup_py, version):

    """
    Generate a setup.py file with the given version. This function replaces the current 'version'
    section of the setup.py file with the specified version value.

    Args:
        setup_py (:str): The current setup.py file contents.
        version (:str): The desired version the setup.py file should have.

    Returns:
        str: The modified contents of the setup.py file with the new version number.
    """

    p = re.compile('.*(version=.*),?')
    match = p.search(setup_py)
    if match:
        return setup_py.replace(match.group(1), "version='{0}',".format(version))
    raise exceptions.FailedGeneratingSetupPyException(setup_py=setup_py, version=version)


def get_python_executable(name, exec_home=None):

    """
    Retrieve the path to an executable script. On linux platforms this wont actually do
    anything. However, for windows it will return the absolute path to the executable inside the
    'Scripts' directory of the python installation.

    Args:
        name (:str): The executable name.
        exec_home (:str, optional): The base python installation directory. Defaults to
        `sys.exec_prefix`

    Returns:
        Full path to the executable file.

    """

    if not exec_home and is_pyinstaller():
        raise RuntimeError('Executables are not supported when running inside a PyInstaller '
                           'bootloader. Are you sure this is what you wanted to do?')

    def _for_linux():

        return os.path.join(exec_home, 'bin', name)

    def _for_windows():

        exe = '{}.exe'.format(name)
        executable_p = os.path.join(exec_home, exe)
        if not os.path.exists(executable_p):
            scripts_directory = os.path.join(exec_home, 'scripts')
            executable_p = os.path.join(scripts_directory, exe)
        if os.path.exists(executable_p):
            return executable_p

        raise RuntimeError('Executable not found: {}'.format(exe))

    exec_home = exec_home or os.path.abspath(sys.exec_prefix)

    if is_windows():
        executable_path = _for_windows()
    else:
        executable_path = _for_linux()

    return os.path.abspath(executable_path)


def is_windows():

    """
    Check if the current OS is window.

    Returns:
         True if windows, False otherwise.
    """

    return platform.system().lower() == 'windows'


def download_repo(repo_name, sha):

    """
    Download and validate the repository from a specific sha.

    Args:
        repo_name (str): The repository full name. (e.g iliapolo/pyci)
        sha (str): The sha of the commit to download.

    Raises:
        exceptions.NotPythonProjectException: Raised when the repository does not contain
            a setup.py file.
    """

    repo_base_name = '/'.join(repo_name.split('/')[1:])

    url = 'https://github.com/{}/archive/{}.zip'.format(repo_name, sha)

    headers = {}

    token = os.environ.get('GITHUB_ACCESS_TOKEN')
    if token:
        headers = {
            'Authorization': 'token {}'.format(token)
        }
    archive = download(url, headers=headers)
    repo_dir = unzip(archive=archive)

    repo_dir = os.path.join(repo_dir, '{}-{}'.format(repo_base_name, sha))

    return repo_dir


def is_python_3():

    """
    Checks the current python version.

    Returns:
        True if the current python version is at least 3.0, False otherwise.
    """

    return six.PY3


def raise_with_traceback(err, tb):

    """
    Raise, in a python version agnostic manner, the provided error with the provided traceback.

    Args:
        err (BaseException): The exception to raise.
        tb (types.Traceback): The traceback to attach to the error.

    """

    six.reraise(type(err), err, tb)


def is_pyinstaller():

    """
    Returns:
        True if we are running inside a bundled pyinstaller package. False otherwise.

    """
    try:
        getattr(sys, '_MEIPASS')
        return True
    except AttributeError:
        return False


def extract_version_from_setup_py(setup_py_content):

    """
    Extract the value of the 'version' argument from the setup.py file. (Regex based)

    Args:
        setup_py_content (str): The setup.py file contents.

    Returns:
         The version defined in setup.py
    """

    regex = 'version=["\'](.*)["\']'

    name = re.compile(regex)

    match = name.search(setup_py_content)

    if match:
        return match.group(1)

    raise exceptions.RegexMatchFailureException(regex=regex)


def which(program):

    """
    Lookup the program in the system PATH. Equivalent to the unix 'which' command.

    Args:
        program (str): The program pure name.

    Returns:
        The program full name (including .exe if necessary)
    """

    path = os.getenv('PATH')

    for p in path.split(os.path.pathsep):
        program_path = os.path.join(p, executable(program))
        if os.path.exists(program_path):
            if os.access(program_path, os.X_OK):
                return program_path

    return None


def executable(program):

    """
    Transform the program name to an executable name. Basically just means
    adding .exe in case of windows.

    Args:
        program (str): The program pure name.

    Returns:
        The program "canonical" name.
    """

    return '{}.exe'.format(program) if is_windows() else program


def validate_nsis_version(version):

    """
    Validate the version number adheres to NSIS specifications.
    NSIS enforces version strings in the form of X.X.X.X

    Args:
        version (str): The version to check.

    Raises:
         IllegalNSISVersion: In case the version doesn't meet the regex.
    """

    parts = version.split('.')

    if len(parts) != 4:
        raise exceptions.InvalidNSISVersionException(pattern='X.X.X.X', version=version)
