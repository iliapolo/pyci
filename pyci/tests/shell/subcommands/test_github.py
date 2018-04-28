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

# noinspection PyPackageRequirements
import pytest
# noinspection PyPackageRequirements
from mock import MagicMock

from pyci.api import logger, exceptions
from pyci.api.exceptions import ApiException
from pyci.api.model.bump import Bump
from pyci.api.model.commit import Commit
from pyci.api.model.issue import Issue
from pyci.api.model.release import Release
from pyci.tests.shell import Runner

log = logger.get_logger(__name__)


@pytest.fixture(name='github')
def _github(temp_dir, mocker):

    gh_mock = MagicMock()

    mocker.patch(target='pyci.api.gh.new', new=MagicMock(return_value=gh_mock))

    # pylint: disable=too-few-public-methods
    class GithubSubCommand(Runner):

        def __init__(self, repo):
            super(GithubSubCommand, self).__init__()
            self.repo = repo

        def run(self, command, catch_exceptions=False):

            command = 'github --repo iliapolo/pyci-guinea-pig {}'.format(command)

            return super(GithubSubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield GithubSubCommand(gh_mock)
    finally:
        os.chdir(cwd)


@pytest.fixture(name='real_github')
def _real_github(temp_dir):

    # pylint: disable=too-few-public-methods
    class GithubSubCommand(Runner):

        def run(self, command, catch_exceptions=False):

            command = 'github --repo iliapolo/pyci-guinea-pig {}'.format(command)

            return super(GithubSubCommand, self).run(command, catch_exceptions)

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield GithubSubCommand()
    finally:
        os.chdir(cwd)


@pytest.fixture(name='pyci')
def _pyci(temp_dir):

    cwd = os.getcwd()

    try:
        os.chdir(temp_dir)
        yield Runner()
    finally:
        os.chdir(cwd)


@pytest.mark.usefixtures("no_ci")
def test_no_repo(pyci, github, capture):

    # the 'validate-commit' part isn't important, it could have been any other command.
    # we just want main.py to run the 'github' function.
    pyci.run('github validate-commit', catch_exceptions=True)

    expected_output = 'Failed detecting repository name. Please provide it using the ' \
                      '"--repo" option.\nIf you are running locally, you can also ' \
                      'execute this command from your project root directory ' \
                      '(repository will be detected using git).'

    assert expected_output == capture.records[1].msg
    github.repo.validate_commit.assert_not_called()


# @pytest.mark.wet
# def test_release_branch(real_github, capture):
#
#     real_github.run('release --branch release --force')


def test_validate_commit_no_sha_no_branch(github, capture):

    github.run('validate-commit', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --branch.'

    assert expected_output == capture.records[1].msg
    github.repo.validate_commit.assert_not_called()


def test_validate_commit_sha_and_branch(github, capture):

    github.run('validate-commit --sha sha --branch branch', catch_exceptions=True)

    expected_output = 'Use either --sha or --branch, not both.'

    assert expected_output == capture.records[1].msg
    github.repo.validate_commit.assert_not_called()


def test_validate_commit_sha(github, capture):

    github.run('validate-commit --sha sha')

    expected_output = 'Validation passed!'

    assert expected_output == capture.records[1].msg
    github.repo.validate_commit.assert_called_once_with(sha='sha', branch=None)


def test_validate_commit_branch(github, capture):

    github.run('validate-commit --branch branch')

    expected_output = 'Validation passed!'

    assert expected_output == capture.records[1].msg
    github.repo.validate_commit.assert_called_once_with(sha=None, branch='branch')


def test_validate_commit_failed(github, capture):

    exception = ApiException('error')

    github.repo.validate_commit = MagicMock(side_effect=exception)

    github.run('validate-commit --branch branch', catch_exceptions=True)

    expected_output = 'Validation failed: error'

    assert expected_output == capture.records[2].msg
    github.repo.validate_commit.assert_called_once_with(sha=None, branch='branch')


def test_generate_changelog_no_sha_no_branch(github, capture):

    github.run('generate-changelog', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --branch.'

    assert expected_output == capture.records[1].msg
    github.repo.generate_changelog.assert_not_called()


def test_generate_changelog_sha_and_branch(github, capture):

    github.run('generate-changelog --sha sha --branch branch', catch_exceptions=True)

    expected_output = 'Use either --sha or --branch, not both.'

    assert expected_output == capture.records[1].msg
    github.repo.generate_changelog.assert_not_called()


def test_generate_changelog_sha(github, capture, temp_dir):

    destination = os.path.join(temp_dir, 'changelog.md')

    changelog = MagicMock()
    changelog.render = MagicMock(return_value='changelog')
    github.repo.generate_changelog = MagicMock(return_value=changelog)

    github.run('generate-changelog --sha sha --target {}'.format(destination))

    expected_output = 'Generated at {}'.format(destination)

    assert expected_output == capture.records[2].msg
    github.repo.generate_changelog.assert_called_once_with(sha='sha', branch=None)


def test_generate_changelog_branch(github, capture, temp_dir):

    destination = os.path.join(temp_dir, 'changelog.md')

    changelog = MagicMock()
    changelog.render = MagicMock(return_value='changelog')
    github.repo.generate_changelog = MagicMock(return_value=changelog)

    github.run('generate-changelog --branch branch --target {}'.format(destination))

    expected_output = 'Generated at {}'.format(destination)

    assert expected_output == capture.records[2].msg
    github.repo.generate_changelog.assert_called_once_with(branch='branch', sha=None)


@pytest.mark.usefixtures("isolated")
def test_generate_changelog_no_target(github, capture):

    destination = os.path.join(os.getcwd(), 'sha-changelog.md')

    changelog = MagicMock()
    changelog.render = MagicMock(return_value='changelog')
    github.repo.generate_changelog = MagicMock(return_value=changelog)

    github.run('generate-changelog --sha sha')

    expected_output = 'Generated at {}'.format(destination)

    assert expected_output == capture.records[2].msg
    github.repo.generate_changelog.assert_called_once_with(sha='sha', branch=None)


def test_generate_changelog_failed(github, capture):

    exception = ApiException('error')

    github.repo.generate_changelog = MagicMock(side_effect=exception)

    github.run('generate-changelog --branch branch', catch_exceptions=True)

    expected_output = 'Failed generating changelog: error'

    assert expected_output == capture.records[2].msg
    github.repo.generate_changelog.assert_called_once_with(sha=None, branch='branch')


def test_create_release_no_sha_no_branch(github, capture):

    github.run('create-release', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --branch.'

    assert expected_output == capture.records[1].msg
    github.repo.create_release.assert_not_called()


def test_create_release_sha_and_branch(github, capture):

    github.run('create-release --sha sha --branch branch', catch_exceptions=True)

    expected_output = 'Use either --sha or --branch, not both.'

    assert expected_output == capture.records[1].msg
    github.repo.create_release.assert_not_called()


def test_create_release_sha(github, capture):

    release = Release(title='0.0.1', url='url', impl=None, sha='sha')

    github.repo.create_release = MagicMock(return_value=release)

    github.run('create-release --sha sha')

    expected_output = 'Release created: url'

    assert expected_output == capture.records[1].msg
    github.repo.create_release.assert_called_once_with(sha='sha', branch=None)


def test_create_release_branch(github, capture):

    release = Release(title='0.0.1', url='url', impl=None, sha='sha')

    github.repo.create_release = MagicMock(return_value=release)

    github.run('create-release --branch branch')

    expected_output = 'Release created: url'

    assert expected_output == capture.records[1].msg
    github.repo.create_release.assert_called_once_with(sha=None, branch='branch')


def test_create_release_not_python_project(github, capture):

    exception = exceptions.NotPythonProjectException(repo='repo', sha='sha', cause='cause')

    github.repo.create_release = MagicMock(side_effect=exception)

    github.run('create-release --branch branch', catch_exceptions=True)

    expected_error_message = 'Failed creating release: {}'.format(str(exception))
    expected_possible_solution = 'Please follow these instructions to create a standard ' \
                                 'python project --> https://packaging.python.org' \
                                 '/tutorials/distributing-packages/'

    assert expected_error_message in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    github.repo.create_release.assert_called_once_with(sha=None, branch='branch')


def test_create_release_failed(github, capture):

    exception = ApiException('error')

    github.repo.create_release = MagicMock(side_effect=exception)

    github.run('create-release --branch branch', catch_exceptions=True)

    expected_output = 'Failed creating release: error'

    assert expected_output == capture.records[2].msg
    github.repo.create_release.assert_called_once_with(sha=None, branch='branch')


def test_upload_asset(github, capture):

    github.repo.upload_asset = MagicMock(return_value='url')

    github.run('upload-asset --asset asset --release release')

    expected_output = 'Uploaded: url'

    assert expected_output == capture.records[1].msg
    github.repo.upload_asset.assert_called_once_with(asset='asset', release='release')


def test_upload_asset_failed(github, capture):

    exception = ApiException('error')

    github.repo.upload_asset = MagicMock(side_effect=exception)

    github.run('upload-asset --asset asset --release release', catch_exceptions=True)

    expected_output = 'Failed uploading asset: error'

    assert expected_output == capture.records[2].msg
    github.repo.upload_asset.assert_called_once_with(asset='asset', release='release')


def test_detect_issue_no_sha_no_message(github, capture):

    github.run('detect-issue', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --message.'

    assert expected_output == capture.records[1].msg
    github.repo.detect_issue.assert_not_called()


def test_detect_issue_sha_and_message(github, capture):

    github.run('detect-issue --sha sha --message message', catch_exceptions=True)

    expected_output = 'Use either --sha or --message, not both.'

    assert expected_output == capture.records[1].msg
    github.repo.detect_issue.assert_not_called()


def test_detect_issue(github, capture):

    issue = Issue(impl=None, number=4, url='url')

    github.repo.detect_issue = MagicMock(return_value=issue)

    github.run('detect-issue --message message')

    expected_output = 'Issue detected: url'

    assert expected_output == capture.records[1].msg
    github.repo.detect_issue.assert_called_once_with(commit_message='message', sha=None)


def test_detect_issue_not_related_to_issue(github, capture):

    github.repo.detect_issue = MagicMock(return_value=None)

    github.run('detect-issue --message message')

    expected_output = 'The commit is not related ot any issue.'

    assert expected_output == capture.records[1].msg
    github.repo.detect_issue.assert_called_once_with(commit_message='message', sha=None)


def test_detect_issue_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.detect_issue = MagicMock(side_effect=exception)

    github.run('detect-issue --sha sha', catch_exceptions=True)

    expected_output = 'Failed detecting issue: error'

    assert expected_output == capture.records[2].msg
    github.repo.detect_issue.assert_called_once_with(commit_message=None, sha='sha')


def test_delete_release(github, capture):

    github.run('delete-release --name 0.0.1')

    expected_output = 'Deleted release: 0.0.1'

    assert expected_output == capture.records[1].msg
    github.repo.delete_release.assert_called_once_with(name='0.0.1')


def test_delete_release_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.delete_release = MagicMock(side_effect=exception)

    github.run('delete-release --name 0.0.1', catch_exceptions=True)

    expected_output = 'Failed deleting release: error'

    assert expected_output == capture.records[2].msg
    github.repo.delete_release.assert_called_once_with(name='0.0.1')


def test_delete_tag(github, capture):

    github.run('delete-tag --name 0.0.1')

    expected_output = 'Deleted tag: 0.0.1'

    assert expected_output == capture.records[1].msg
    github.repo.delete_tag.assert_called_once_with(name='0.0.1')


def test_delete_tag_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.delete_tag = MagicMock(side_effect=exception)

    github.run('delete-tag --name 0.0.1', catch_exceptions=True)

    expected_output = 'Failed deleting tag: error'

    assert expected_output == capture.records[2].msg
    github.repo.delete_tag.assert_called_once_with(name='0.0.1')


def test_bump_version(github, capture):

    bump = Bump(prev_version='0.0.1', next_version='0.0.2', impl=None, sha='sha')

    github.repo.bump_version = MagicMock(return_value=bump)

    github.run('bump-version --branch release --semantic patch')

    expected_output = 'Bumped version from 0.0.1 to 0.0.2'

    assert expected_output == capture.records[1].msg
    github.repo.bump_version.assert_called_once_with(branch='release', semantic='patch')


def test_bump_version_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.bump_version = MagicMock(side_effect=exception)

    github.run('bump-version --branch release --semantic patch', catch_exceptions=True)

    expected_output = 'Failed bumping version: error'

    assert expected_output == capture.records[2].msg
    github.repo.bump_version.assert_called_once_with(branch='release', semantic='patch')


def test_set_version(github, capture):

    bump = Bump(prev_version='0.0.1', next_version='0.0.2', impl=None, sha='sha')

    github.repo.set_version = MagicMock(return_value=bump)

    github.run('set-version --branch release --value 0.0.2')

    expected_output = 'Version is now 0.0.2 (was 0.0.1)'

    assert expected_output == capture.records[1].msg
    github.repo.set_version.assert_called_once_with(branch='release', value='0.0.2')


def test_set_version_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.set_version = MagicMock(side_effect=exception)

    github.run('set-version --branch release --value 0.0.1', catch_exceptions=True)

    expected_output = 'Failed setting version: error'

    assert expected_output == capture.records[2].msg
    github.repo.set_version.assert_called_once_with(branch='release', value='0.0.1')


def test_reset_branch(github, capture):

    github.run('reset-branch --name release --sha sha')

    expected_output = 'Branch release is now at sha.'

    assert expected_output == capture.records[1].msg
    github.repo.reset_branch.assert_called_once_with(name='release', sha='sha')


def test_reset_branch_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.reset_branch = MagicMock(side_effect=exception)

    github.run('reset-branch --name release --sha sha', catch_exceptions=True)

    expected_output = 'Failed resetting branch: error'

    assert expected_output == capture.records[2].msg
    github.repo.reset_branch.assert_called_once_with(name='release', sha='sha')


def test_reset_tag(github, capture):

    github.run('reset-tag --name release --sha sha')

    expected_output = 'Tag release is now at sha.'

    assert expected_output == capture.records[1].msg
    github.repo.reset_tag.assert_called_once_with(name='release', sha='sha')


def test_reset_tag_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.reset_tag = MagicMock(side_effect=exception)

    github.run('reset-tag --name release --sha sha', catch_exceptions=True)

    expected_output = 'Failed resetting tag: error'

    assert expected_output == capture.records[2].msg
    github.repo.reset_tag.assert_called_once_with(name='release', sha='sha')


def test_create_branch(github, capture):

    github.run('create-branch --name release --sha sha')

    expected_output = 'Branch created: release.'

    assert expected_output == capture.records[1].msg
    github.repo.create_branch.assert_called_once_with(name='release', sha='sha')


def test_create_branch_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.create_branch = MagicMock(side_effect=exception)

    github.run('create-branch --name release --sha sha', catch_exceptions=True)

    expected_output = 'Failed creating branch: error'

    assert expected_output == capture.records[2].msg
    github.repo.create_branch.assert_called_once_with(name='release', sha='sha')


def test_delete_branch(github, capture):

    github.run('delete-branch --name branch')

    expected_output = 'Branch deleted: branch.'

    assert expected_output == capture.records[1].msg
    github.repo.delete_branch.assert_called_once_with(name='branch')


def test_delete_branch_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.delete_branch = MagicMock(side_effect=exception)

    github.run('delete-branch --name branch', catch_exceptions=True)

    expected_output = 'Failed deleting branch: error'

    assert expected_output == capture.records[2].msg
    github.repo.delete_branch.assert_called_once_with(name='branch')


def test_commit_file(github, capture):

    commit = Commit(impl=None, sha='sha', url='url')

    github.repo.commit_file = MagicMock(return_value=commit)

    github.run('commit-file --path path --contents contents --message message --branch branch')

    expected_output = 'Committed: url'

    assert expected_output == capture.records[1].msg
    github.repo.commit_file.assert_called_once_with(path='path', contents='contents',
                                                    message='message', branch='branch')


def test_commit_file_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.commit_file = MagicMock(side_effect=exception)

    github.run('commit-file --path path --contents contents --message message --branch branch',
               catch_exceptions=True)

    expected_output = 'Failed committing file: error'

    assert expected_output == capture.records[2].msg
    github.repo.commit_file.assert_called_once_with(path='path', contents='contents',
                                                    message='message', branch='branch')


def test_create_commit(github, capture):

    commit = Commit(impl=None, sha='sha', url='url')

    github.repo.create_commit = MagicMock(return_value=commit)

    github.run('create-commit --path path --contents contents --message message --branch branch')

    expected_output = 'Created: url'

    assert expected_output == capture.records[1].msg
    github.repo.create_commit.assert_called_once_with(path='path', contents='contents',
                                                      message='message', branch='branch')


def test_create_commit_failed(github, capture):

    exception = exceptions.ApiException('error')

    github.repo.create_commit = MagicMock(side_effect=exception)

    github.run('create-commit --path path --contents contents --message message --branch branch',
               catch_exceptions=True)

    expected_output = 'Failed creating commit: error'

    assert expected_output == capture.records[2].msg
    github.repo.create_commit.assert_called_once_with(path='path', contents='contents',
                                                      message='message', branch='branch')
