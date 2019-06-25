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
import sys
import contextlib
import os
import platform
import tempfile

import click

import pytest
from github import Github


from pyci.api import logger
from pyci.api import utils
from pyci.api.gh import GitHubRepository
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.api.runner import LocalCommandRunner
from pyci.shell import secrets
from pyci.tests.shell import PyCI
from pyci.tests.shell import CLICK_ISOLATION
from pyci import tests
from pyci.tests import utils as test_utils

logger.DEFAULT_LOG_LEVEL = logging.DEBUG

REPO_UNDER_TEST = 'iliapolo/pyci-guinea-pig'
LAST_COMMIT = 'cf2d64132f00c849ae1bb62ffb2e32b719b6cbac'
SPEC_FILE = 'pyci.spec'


@pytest.fixture(name='skip', autouse=True)
def _skip(request, test_name):

    def __skip(reason):
        pytest.skip('[{}] {}'.format(request.node.location, reason))

    system = platform.system().lower()
    docker = utils.which('docker')

    if _get_marker(request, test_name, 'linux') is not None and system == 'windows':
        __skip('This test should not run on windows')

    if _get_marker(request, test_name, 'windows') is not None and system != 'windows':
        __skip('This test should not run on windows')

    if _get_marker(request, test_name, 'docker') is not None and docker is None:
        __skip('This test can only run when docker is installed')


@pytest.fixture(name='cleanup', autouse=True)
def _cleanup(log, request, repo, test_name):
    with _github_cleanup(log, test_name, request, repo):
        yield


@pytest.fixture(name='patch', autouse=True)
def _patch_github_connection(request, test_name, connection_patcher):
    connection_patcher.update(_get_data_file(request, test_name))
    yield


@pytest.fixture(name='cwd', autouse=True)
def _cwd(temp_dir):

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield
    finally:
        os.chdir(cwd)


@pytest.fixture(name='non_interactive', autouse=True)
def _non_interactive():
    os.environ['PYCI_INTERACTIVE'] = 'False'


@pytest.fixture(name='_log', autouse=True)
def _mock_log(mocker, log):

    def _log(level, message, **kwargs):

        if os.environ.get(CLICK_ISOLATION):
            # This means we are running inside an isolated click
            # environment, So we add this to buffer regular log messages as well
            # in order to capture the entire execution output.
            # TODO this feels super hacky - rethink.
            click.echo(message)

        # This prints the messages in real time while the test is running
        log.log(level, '{}{}'.format(message.strip(), logger.Logger.format_key_values(**kwargs)))

    mocker.patch(target='pyci.api.logger.Logger._log', side_effect=_log)


@pytest.fixture(name='pyci', scope='session')
def _pyci(log, global_repo_path):

    return PyCI(global_repo_path, log)


@pytest.fixture(name='release')
def _release(pyci, github):

    # pylint: disable=too-few-public-methods
    class ReleaseCommand(object):

        def __init__(self):
            self.github = github

        @staticmethod
        def run(command, binary=False, catch_exceptions=False):

            command = '--no-ci release --repo {} {}'.format(REPO_UNDER_TEST, command)

            return pyci.run(command=command,
                            binary=binary,
                            catch_exceptions=catch_exceptions)

    yield ReleaseCommand()


@pytest.fixture(name='github')
def _github(pyci, repo, token):

    repository = GitHubRepository.create(repo=REPO_UNDER_TEST,
                                         access_token=token)
    setattr(repository, 'repo', repo)

    # pylint: disable=too-few-public-methods
    class GithubSubCommand(object):

        def __init__(self):
            self.api = repository

        @staticmethod
        def run(command, binary=False, catch_exceptions=False):

            command = '--no-ci github --repo {} {}'.format(REPO_UNDER_TEST, command)

            return pyci.run(command=command,
                            binary=binary,
                            catch_exceptions=catch_exceptions)

    yield GithubSubCommand()


@pytest.fixture(name='pack')
def _pack(pyci, repo_path):

    packager = Packager.create(path=repo_path)

    # pylint: disable=too-few-public-methods
    class PackSubCommand(object):

        def __init__(self):
            self.api = packager

        def run(self, command, binary=False, catch_exceptions=False):

            # noinspection PyProtectedMember
            # pylint: disable=protected-access
            pack_options = '--path {}'.format(packager._repo_dir)
            if self.api.target_dir:
                pack_options = '{} --target-dir {}'.format(pack_options, self.api.target_dir)

            command = '--no-ci pack {} {}'.format(pack_options, command)

            return pyci.run(command=command,
                            binary=binary,
                            catch_exceptions=catch_exceptions)

    return PackSubCommand()


@pytest.fixture(name='pypi')
def _pypi(pyci):

    # pylint: disable=too-few-public-methods
    class PyPISubCommand(object):

        def __init__(self):
            self.api = PyPI.create(username=secrets.twine_username(),
                                   password=secrets.twine_password(),
                                   test=True)

        @staticmethod
        def run(command, binary=False, catch_exceptions=False):

            command = '--no-ci pypi --test {}'.format(command)

            return pyci.run(command=command,
                            binary=binary,
                            catch_exceptions=catch_exceptions)

    yield PyPISubCommand()


@pytest.fixture(name='temp_dir')
def _temp_dir(request):

    name = request.node.originalname or request.node.name

    dir_path = tempfile.mkdtemp(suffix=name)

    try:
        yield dir_path
    finally:
        utils.rmf(dir_path)


@pytest.fixture(name='repo', scope='session')
def _repo(connection_patcher, token):

    get_repo_data = os.path.join(os.path.dirname(tests.__file__),
                                 "replay_data",
                                 "pyci.tests.conftest.get_repo.txt")

    try:
        connection_patcher.patch()
        connection_patcher.update(get_repo_data)

        repo = Github(token, timeout=30).get_repo(
            REPO_UNDER_TEST, lazy=False)
        yield repo
    finally:
        connection_patcher.reset()


@pytest.fixture(name='connection_patcher', scope='session')
def _github_connection_patcher(token, mode):

    pytest.register_assert_rewrite('pyci.tests.framework')

    from pyci.tests import github_patcher

    record = mode == 'RECORD'

    return github_patcher.GithubConnectionPatcher(record=record, token=token)


@pytest.fixture(name='token', scope='session')
def _token(mode):

    if mode == 'RECORD':
        token = secrets.github_access_token()
    else:
        # when replaying, the token is not needed.
        token = 'token'

    # set the environment variable so that the commands code will use it and not
    # get stuck on prompt when running from IDE.
    os.environ[secrets.GITHUB_ACCESS_TOKEN] = token

    return token


@pytest.fixture(name='mode', scope='session')
def _mode():

    record = os.environ.get('PYGITHUB_RECORD', False)

    if record:
        return 'RECORD'

    return 'REPLAY'


@pytest.fixture(name='runner', scope='session')
def _runner():

    yield LocalCommandRunner()


@pytest.fixture(name='repo_path')
def _repo_path(log, temp_dir):

    target_repo_path = os.path.join(temp_dir, 'pyci')

    log.info('Copying source directory to {}...'.format(target_repo_path))
    test_utils.copy_repo(target_repo_path)
    log.info('Finished copying source directory to: {}'.format(target_repo_path))

    return target_repo_path


@pytest.fixture(name='repo_version')
def _repo_version(repo_path):

    version = test_utils.patch_setup_py(repo_path)
    return version


@pytest.fixture(name='global_repo_path', scope='session')
def _global_repo_path(log):

    temp_dir = tempfile.mkdtemp()
    target_repo_path = os.path.join(temp_dir, 'pyci')

    log.info('Copying source directory to {}...'.format(target_repo_path))
    test_utils.copy_repo(target_repo_path)
    log.info('Finished copying source directory to: {}'.format(target_repo_path))

    try:
        yield target_repo_path
    finally:
        utils.rmf(target_repo_path)


@contextlib.contextmanager
def _github_cleanup(log, test_name, request, repo):

    wet = _get_marker(request, test_name, 'wet') is not None

    try:
        yield
    finally:
        if wet:
            _reset_repo(log, repo)


@pytest.fixture(name='log', scope='session')
def _log():

    lo = logging.getLogger('pyci.tests')
    lo.setLevel(logger.DEFAULT_LOG_LEVEL)
    lo.propagate = False
    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logger.DEFAULT_LOG_LEVEL)
    formatter = logging.Formatter(logger.DEFAULT_LOG_FORMAT)
    ch.setFormatter(formatter)

    lo.addHandler(ch)

    return lo


@pytest.fixture(name='test_name')
def _test_name(request):
    sanitized = request.node.nodeid\
        .replace(os.sep, '.')\
        .replace('/', '.')\
        .replace('::', '.')\
        .replace(':', '.')\
        .replace('[', '-')\
        .replace(']', '')
    return sanitized


def _reset_repo(log, repo):

    _reset_commits(log, repo)
    _reset_releases(log, repo)
    _reset_tags(log, repo)
    _reset_branches(log, repo)
    _reset_issues(log, repo)


def _reset_commits(log, repo):

    log.info('Resetting release branch to original state...')
    ref = repo.get_git_ref('heads/release')
    ref.edit(sha=LAST_COMMIT, force=True)

    log.info('Resetting master branch to original state...')
    ref = repo.get_git_ref('heads/master')
    ref.edit(sha=LAST_COMMIT, force=True)


def _reset_issues(log, repo):
    log.info('Re-opening and cleaning all issues...')
    for issue in repo.get_issues(state='all'):
        if not issue.pull_request:
            issue.edit(state='open')
            for comment in issue.get_comments():
                comment.delete()


def _reset_releases(log, repo):
    log.info('Deleting any releases...')
    for release in repo.get_releases():
        release.delete_release()


def _reset_tags(log, repo):
    log.info('Deleting any tags...')
    for tag in repo.get_tags():
        ref = repo.get_git_ref('tags/{}'.format(tag.name))
        ref.delete()


def _reset_branches(log, repo):
    log.info('Deleting any additional branches...')
    for branch in repo.get_branches():
        if branch.name not in ['master', 'release']:
            ref = repo.get_git_ref('heads/{}'.format(branch.name))
            ref.delete()


def _get_marker(request, test_name, marker_name):

    markers = [mark for mark in request.node.own_markers if mark.name == marker_name]

    if len(markers) > 1:
        raise RuntimeError("Invalid markers for test '{}': Multiple '{}' markers found".format(marker_name, test_name))

    return markers[0] if markers else None


def _get_data_file(request, test_name):

    def _is_test_platform_dependent():

        record_mark = _get_marker(request, test_name, 'record')

        if not record_mark:
            return False

        return record_mark.kwargs.get('platform', False)

    file_name = os.path.join(os.path.dirname(tests.__file__), "replay_data", test_name + ".txt")

    if _is_test_platform_dependent():
        file_name = '{}-{}'.format(file_name, platform.system().lower())

    return file_name
