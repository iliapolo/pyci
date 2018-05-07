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

import pyci
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
PATCHED_FIXTURES = ['patched_pack', 'patched_pypi', 'patched_github', 'capture', 'mocker']


@pytest.fixture(name='patched_pack')
def _patched_pack(temp_dir, mocker):

    packager = MagicMock()

    mocker.patch(target='pyci.api.packager.Packager.create', new=MagicMock(return_value=packager))

    # pylint: disable=too-few-public-methods
    class PackSubCommand(Runner):

        def __init__(self, _packager):
            super(PackSubCommand, self).__init__()
            self.packager = _packager

        def run(self, command, catch_exceptions=False):

            command = 'pack --sha sha --repo {} {}'.format(REPO_UNDER_TEST, command)

            return super(PackSubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield PackSubCommand(packager)
    finally:
        os.chdir(cwd)


@pytest.fixture(name='patched_pypi')
def _patched_pypi(temp_dir, mocker):

    pypi = MagicMock()

    mocker.patch(target='pyci.api.pypi.PyPI.create', new=MagicMock(return_value=pypi))

    # pylint: disable=too-few-public-methods
    class PyPISubCommand(Runner):

        def __init__(self, _pypi):
            super(PyPISubCommand, self).__init__()
            self.pypi = _pypi

        def run(self, command, catch_exceptions=False):

            command = 'pypi {}'.format(command)

            return super(PyPISubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield PyPISubCommand(pypi)
    finally:
        os.chdir(cwd)


@pytest.fixture(name='patched_github')
def _patched_github(temp_dir, mocker):

    gh = MagicMock()

    mocker.patch(target='pyci.api.gh.GitHubRepository.create', new=MagicMock(return_value=gh))

    # pylint: disable=too-few-public-methods
    class GithubSubCommand(Runner):

        def __init__(self, _gh):
            super(GithubSubCommand, self).__init__()
            self.gh = _gh

        def run(self, command, catch_exceptions=False):

            command = '--debug --no-ci github --repo {} {}'.format(REPO_UNDER_TEST, command)

            return super(GithubSubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield GithubSubCommand(gh)
    finally:
        os.chdir(cwd)


@pytest.fixture(name='github')
def _github(request, temp_dir, gh):

    # pylint: disable=too-few-public-methods
    class GithubSubCommand(Runner):

        def __init__(self, _gh):
            super(GithubSubCommand, self).__init__()
            self.gh = _gh

        def run(self, command, catch_exceptions=False):

            command = '--debug --no-ci github --repo {} {}'.format(REPO_UNDER_TEST, command)

            return super(GithubSubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        with _github_cleanup(request, gh.repo):
            yield GithubSubCommand(gh)
    finally:
        os.chdir(cwd)


@pytest.fixture(name='pyci')
def _pyci(request, repo, temp_dir):

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        with _github_cleanup(request, repo):
            yield Runner()
    finally:
        os.chdir(cwd)


@pytest.fixture(name='pypi')
def _pypi():

    yield PyPI.create(username=secrets.twine_username(True),
                      password=secrets.twine_password(True),
                      test=True)


@pytest.fixture(name='gh')
def _gh(request, repo):
    repository = GitHubRepository.create(repo=REPO_UNDER_TEST,
                                         access_token=secrets.github_access_token(True))
    setattr(repository, 'repo', repo)
    with _github_cleanup(request, repo):
        yield repository


@pytest.fixture(name='repo', scope='module')
def _repo():
    return Github(secrets.github_access_token(True)).get_repo(REPO_UNDER_TEST)


@pytest.fixture(name='packager')
def _packager():

    local_repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))
    packager = Packager.create(path=local_repo_path)

    try:
        yield packager
    finally:
        packager.clean()


@pytest.fixture(name='pypi_packager')
def _pypi_packager(temp_dir):

    local_repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))

    dest = os.path.join(temp_dir, 'repo')
    shutil.copytree(local_repo_path, dest)

    patch_setup_py(dest)

    packager = Packager.create(path=dest)

    try:
        yield packager
    finally:
        packager.clean()


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


@pytest.fixture(name='runner')
def _runner():

    yield LocalCommandRunner()


@pytest.fixture(name='version')
def _version(runner):

    setup_py_path = os.path.abspath(os.path.join(pyci.__file__,
                                                 os.pardir,
                                                 os.pardir,
                                                 'setup.py'))

    yield runner.run('{} {} --version'.format(utils.get_executable('python'),
                                              setup_py_path)).std_out


@pytest.fixture(name='isolated')
def _isolated():

    cwd = os.getcwd()
    t = tempfile.mkdtemp()
    os.chdir(t)
    try:
        yield t
    finally:
        os.chdir(cwd)
        utils.rmf(t)


@pytest.fixture(name='skip', autouse=True)
def _skip(request):

    def __skip(reason):
        pytest.skip('[{}] {}'.format(request.node.location, reason))

    system = platform.system().lower()
    provider = ci.detect()
    fixtures = request.node.fixturenames

    test_package = os.environ.get('PYCI_TEST_PACKAGE', 'source')

    if test_package != 'source' and any(patch in fixtures for patch in PATCHED_FIXTURES):
        __skip('Tests using patched objects should only run in process')

    if test_package == 'binary' and 'api' in request.fspath.strpath:
        __skip('Api tests should not run on the binary package')

    if test_package == 'wheel' and 'api' in request.fspath.strpath:
        __skip('Api tests should not run on the wheel package')

    if hasattr(request.node.function, 'binary') and test_package != 'binary':
        __skip('This test should only run on the binary package')

    if hasattr(request.node.function, 'linux') and system == 'windows':
        __skip('This test should not run on windows')

    if hasattr(request.node.function, 'wet') and system != 'darwin':
        __skip('Wet tests should only run on the Darwin build')

    if hasattr(request.node.function, 'wet') and provider and provider.name != ci.TRAVIS:
        __skip('Wet tests should only run on Travis-CI')

    if hasattr(request.node.function, 'wet') and provider and not provider.pull_request:
        __skip('Wet tests should only run on the PR build')


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
