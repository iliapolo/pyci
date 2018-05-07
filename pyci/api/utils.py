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

import requests

from pyci.api import exceptions
from pyci.api.runner import LocalCommandRunner


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


def get_local_repo():

    """
    Detect the git repository of the current directory.

    Returns:
        str: The repository full name. (e.g iliapolo/pyci).
    """

    runner = LocalCommandRunner()
    try:
        result = runner.run('git remote -v')
        return extract_repo(result.std_out.splitlines()[0])
    except exceptions.CommandExecutionException:
        return None


def extract_repo(git_url):

    """
    Extracts the repository name from a git URL.

    Args:
        git_url (str): The git remote url.

    Returns:
        str: The full repository name or None if not found.
    """

    try:
        return git_url.split(' ')[0].split('.git')[0].split('.com')[1][1:]
    except IndexError:
        return None


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
        FileDoesntExistException: Raised if the path does not exist.
        FileIsADirectoryException: Raised if the given path points to a directory.
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


def download(url, target=None):

    """
    Download a URL to a file.

    Args:
        url (str): The URL to download.
        target (:`str`, optional): The target file. Defaults to a temporary file.

    Returns:
        str: Path to the downloaded file.
    """

    target = target or os.path.join(tempfile.mkdtemp(), str(uuid.uuid4()))

    r = requests.get(url, stream=True)
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
        setup_py (str): The current setup.py file contents.
        version (str): The desired version the setup.py file should have.

    Returns:
        str: The modified contents of the setup.py file with the new version number.
    """

    p = re.compile('.*(version=.*),?')
    match = p.search(setup_py)
    if match:
        return setup_py.replace(match.group(1), "version='{0}',".format(version))
    raise exceptions.FailedGeneratingSetupPyException(setup_py=setup_py, version=version)


def get_executable(name):

    """
    Retrieve the path to an executable script. On linux platforms this wont actually do
    anything. However, for windows it will return the absolute path to the executable inside the
    'Scripts' directory of the python installation.

    Args:
        name (str): The executable name.

    """

    bin_directory = os.path.abspath(os.path.join(sys.executable, os.pardir))

    try:
        # running inside a bundled pyinstaller app
        boot_loader = getattr(sys, '_MEIPASS')
        bin_directory = os.path.join(boot_loader, 'bin')
    except AttributeError:
        pass

    executable = name
    if platform.system().lower() == 'windows':
        if name.lower() != 'python'
            bin_directory = os.path.join(bin_directory, 'Scripts')
        executable = os.path.join(bin_directory, '{}.exe'.format(executable))
    else:
        executable = os.path.join(bin_directory, executable)
    return executable


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

    url = 'https://github.com/{0}/archive/{1}.zip'.format(repo_name, sha)
    archive = download(url)
    repo_dir = unzip(archive=archive)

    repo_dir = os.path.join(repo_dir, '{0}-{1}'.format(repo_base_name, sha))

    setup_py_file = os.path.join(repo_dir, 'setup.py')

    try:
        validate_file_exists(setup_py_file)
    except (exceptions.FileIsADirectoryException, exceptions.FileDoesntExistException) as e:
        raise exceptions.NotPythonProjectException(repo=repo_name, cause=str(e), sha=sha)

    return repo_dir
