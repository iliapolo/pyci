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

import logging
import os
import platform
import shutil
import tempfile
import time
import contextlib

import pytest
from github import Github
from mock import MagicMock
from testfixtures import LogCapture

from pyci import shell
from pyci.api import logger, ci
from pyci.api import utils
from pyci.api.gh import GitHubRepository
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.api.runner import LocalCommandRunner
from pyci.shell import secrets
from pyci.tests.shell import Runner

log = logger.get_logger(__name__)

logger.setup_loggers(logging.DEBUG)

REPO_UNDER_TEST = 'iliapolo/pyci-guinea-pig'


@pytest.fixture(name='pyci')
def _pyci(request, repo, repo_path):

    with _github_cleanup(request, repo):
        yield Runner(repo_path)


@pytest.fixture(name='release')
def _release(request, pyci, gh):

    # pylint: disable=too-few-public-methods
    class ReleaseCommand(object):

        def __init__(self):
            self.gh = gh

        @staticmethod
        def run(command, binary=False, pipe=False, catch_exceptions=False):

            command = '--debug --no-ci release --repo {} {}'.format(REPO_UNDER_TEST, command)

            return pyci.run(command=command,
                            binary=binary,
                            pipe=pipe,
                            catch_exceptions=catch_exceptions)

    with _github_cleanup(request, gh.repo):
        yield ReleaseCommand()


@pytest.fixture(name='github')
def _github(request, pyci, gh):

    # pylint: disable=too-few-public-methods
    class GithubSubCommand(object):

        def __init__(self):
            self.gh = gh

        @staticmethod
        def run(command, binary=False, pipe=False, catch_exceptions=False):

            command = '--debug --no-ci github --repo {} {}'.format(REPO_UNDER_TEST, command)

            return pyci.run(command=command,
                            binary=binary,
                            pipe=pipe,
                            catch_exceptions=catch_exceptions)

    with _github_cleanup(request, gh.repo):
        yield GithubSubCommand()


@pytest.fixture(name='gh')
def _gh(request, repo):
    repository = GitHubRepository.create(repo=REPO_UNDER_TEST,
                                         access_token=secrets.github_access_token(True))
    setattr(repository, 'repo', repo)
    with _github_cleanup(request, repo):
        yield repository


@pytest.fixture(name='capture')
def _capture():

    from pyci.shell.subcommands import github
    from pyci.shell.subcommands import pack
    from pyci.shell.subcommands import pypi
    from pyci.shell.commands import release

    names = (shell.__name__, github.__name__, pack.__name__, pypi.__name__, release.__name__)
    with LogCapture(names=names) as cap:

        # LogCapture removes all handlers from the given loggers.
        # lets re-add the console handler, it makes it easier to debug.
        for name in names:
            logger.get_logger(name).add_console_handler(logging.DEBUG)

        yield cap


@pytest.fixture(name='temp_dir')
def _temp_dir(request):

    dir_path = tempfile.mkdtemp(suffix=request.node.name)

    try:
        yield dir_path
    finally:
        # cleanup
        utils.rmf(dir_path)


@pytest.fixture(name='skip', autouse=True)
def _skip(request):

    def __skip(reason):
        pytest.skip('[{}] {}'.format(request.node.location, reason))

    system = platform.system().lower()
    provider = ci.detect()

    if hasattr(request.node.function, 'linux') and system == 'windows':
        __skip('This test should not run on windows')

    if hasattr(request.node.function, 'wet') and system != 'darwin':
        __skip('Wet tests should only run on the Darwin build')

    if hasattr(request.node.function, 'wet') and provider and provider.name != ci.TRAVIS:
        __skip('Wet tests should only run on Travis-CI')

    if hasattr(request.node.function, 'wet') and provider and not provider.pull_request:
        __skip('Wet tests should only run on the PR build')


@pytest.fixture(name='patched_pack')
def _patched_pack(mocker, pyci):

    packager = MagicMock()

    mocker.patch(target='pyci.api.packager.Packager.create', new=MagicMock(return_value=packager))

    # pylint: disable=too-few-public-methods
    class PackSubCommand(object):

        def __init__(self):
            self.packager = packager

        @staticmethod
        def run(command, binary=False, pipe=False, catch_exceptions=False):

            command = 'pack --sha sha --repo {} {}'.format(REPO_UNDER_TEST, command)

            return pyci.run(command=command,
                            binary=binary,
                            pipe=pipe,
                            catch_exceptions=catch_exceptions)

    yield PackSubCommand()


@pytest.fixture(name='patched_pypi')
def _patched_pypi(mocker, pyci):

    pypi = MagicMock()

    mocker.patch(target='pyci.api.pypi.PyPI.create', new=MagicMock(return_value=pypi))

    # pylint: disable=too-few-public-methods
    class PyPISubCommand(object):

        def __init__(self):
            self.pypi = pypi

        @staticmethod
        def run(command, binary=False, pipe=False, catch_exceptions=False):

            command = 'pypi {}'.format(command)

            return pyci.run(command=command,
                            binary=binary,
                            pipe=pipe,
                            catch_exceptions=catch_exceptions)

    yield PyPISubCommand()


@pytest.fixture(name='patched_github')
def _patched_github(mocker, pyci):

    gh = MagicMock()

    mocker.patch(target='pyci.api.gh.GitHubRepository.create', new=MagicMock(return_value=gh))

    # pylint: disable=too-few-public-methods
    class GithubSubCommand(object):

        def __init__(self):
            self.gh = gh

        @staticmethod
        def run(command, binary=False, pipe=False, catch_exceptions=False):

            command = '--debug --no-ci github --repo {} {}'.format(REPO_UNDER_TEST, command)

            return pyci.run(command=command,
                            binary=binary,
                            pipe=pipe,
                            catch_exceptions=catch_exceptions)

    yield GithubSubCommand()


@pytest.fixture(name='pypi', scope='session')
def _pypi():

    yield PyPI.create(username=secrets.twine_username(True),
                      password=secrets.twine_password(True),
                      test=True)


@pytest.fixture(name='repo', scope='session')
def _repo():
    return Github(secrets.github_access_token(True)).get_repo(REPO_UNDER_TEST)


@pytest.fixture(name='packager', scope='session')
def _packager(repo_path):

    packager = Packager.create(path=repo_path)

    try:
        yield packager
    finally:
        packager.clean()


@pytest.fixture(name='pypi_packager', scope='session')
def _pypi_packager(temp_dir, repo_path):

    dest = os.path.join(temp_dir, 'repo')
    shutil.copytree(repo_path, dest)

    patch_setup_py(dest)

    packager = Packager.create(path=dest)

    try:
        yield packager
    finally:
        packager.clean()


@pytest.fixture(name='runner', scope='session')
def _runner():

    yield LocalCommandRunner()


@pytest.fixture(name='version', scope='session')
def _version(runner, repo_path):

    setup_py_path = os.path.abspath(os.path.join(repo_path, 'setup.py'))

    yield runner.run('{} {} --version'.format(utils.get_executable('python'),
                                              setup_py_path)).std_out


@pytest.fixture(name='repo_path', scope='session')
def _repo_path():
    import pyci
    return os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))


@contextlib.contextmanager
def _github_cleanup(request, repo):

    current_commit = None
    wet = None

    try:
        wet = getattr(request.node.function, 'wet')
        current_commit = repo.get_commit(sha='release')
    except AttributeError:
        pass

    try:
        yield
    finally:
        if wet:
            _reset_repo(current_commit, repo, wet)


def _reset_repo(current_commit, repo, wet):

    if wet.kwargs.get('commits', True):
        _reset_release(current_commit, repo)
    if wet.kwargs.get('releases', True):
        _delete_releases(repo)
    if wet.kwargs.get('tags', True):
        _delete_tags(repo)
    if wet.kwargs.get('branches', True):
        _delete_branches(repo)
    if wet.kwargs.get('issues', True):
        _reset_issues(repo)


def _reset_release(commit, repo):
    log.info('Resetting release branch to original state...')
    ref = repo.get_git_ref('heads/release')
    ref.edit(sha=commit.sha, force=True)


def _reset_issues(repo):
    log.info('Re-opening and cleaning all issues...')
    for issue in repo.get_issues(state='all'):
        if not issue.pull_request:
            issue.edit(state='open')
            for comment in issue.get_comments():
                comment.delete()


def _delete_releases(repo):
    log.info('Deleting any releases...')
    for release in repo.get_releases():
        release.delete_release()


def _delete_tags(repo):
    log.info('Deleting any tags...')
    for tag in repo.get_tags():
        ref = repo.get_git_ref('tags/{}'.format(tag.name))
        ref.delete()


def _delete_branches(repo):
    log.info('Deleting any additional branches...')
    for branch in repo.get_branches():
        if branch.name not in ['master', 'release']:
            ref = repo.get_git_ref('heads/{}'.format(branch.name))
            ref.delete()


def patch_setup_py(local_repo_path):

    with open(os.path.join(local_repo_path, 'setup.py'), 'r') as stream:
        setup_py = stream.read()

    setup_py = utils.generate_setup_py(setup_py, '{}'.format(int(time.time())))

    with open(os.path.join(local_repo_path, 'setup.py'), 'w') as stream:
        stream.write(setup_py)
