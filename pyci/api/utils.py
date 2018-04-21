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
import re
import tempfile
import uuid
import zipfile

import datetime
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


def lsd(directory):

    """
    List directory names in a given directory. Only first level directories are returned and only
    the directory basename, i.e without the parent directory path.

    Args:
        directory (str): A directory path.

    Returns:
        list: A list of directory names.
    """

    return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]


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


def validate_does_not_exist(path):

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


def datetime_to_epoch(dt):

    """
    Convert a datetime object to epoch milliseconds.

    Args:
        dt (datetime.datetime): The datetime object.
    """

    epoch = datetime.datetime.utcfromtimestamp(0)

    return (dt - epoch).total_seconds() * 1000.0
