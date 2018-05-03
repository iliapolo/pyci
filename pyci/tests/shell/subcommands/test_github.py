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
import tempfile

# noinspection PyPackageRequirements
import pytest
# noinspection PyPackageRequirements
from github import GithubException
# noinspection PyPackageRequirements
from mock import MagicMock

from pyci.api import logger, exceptions
from pyci.api.exceptions import ApiException, ReleaseValidationFailedException
from pyci.api.model import Bump, Commit, Issue, Release

log = logger.get_logger(__name__)


def _create_release(patched_github, request, sha, name=None):

    release_name = name or request.node.name

    return patched_github.gh.repo.create_git_release(
        tag=release_name,
        target_commitish=sha,
        name=release_name,
        message=''
    )


def _create_commit(patched_github, request, message=None):

    message = message or request.node.name

    return patched_github.gh.commit_file(
        path='README.md',
        contents=request.node.name,
        message=message,
        branch='release')


def test_no_repo(pyci, patched_github, capture):

    # the 'validate-commit' part isn't important, it could have been any other command.
    # we just want main.py to run the 'github' function.
    pyci.run('--no-ci github validate-commit', catch_exceptions=True)

    expected_output = 'Failed detecting repository name'

    expected_solution1 = 'Provide it using the --repo option'

    expected_solution2 = 'Run the command from the porject root directory, the repository ' \
                         'name will be detected using git commands'

    assert expected_output in capture.records[1].msg
    assert expected_solution1 in capture.records[1].msg
    assert expected_solution2 in capture.records[1].msg
    patched_github.gh.validate_commit.assert_not_called()


def test_release_branch_failed(patched_github, capture):

    exception = ApiException('error')

    patched_github.gh.generate_changelog = MagicMock(side_effect=exception)

    patched_github.run('release --branch-name release', catch_exceptions=True)

    expected_output = 'Failed releasing: error'

    assert expected_output == capture.records[7].msg


def test_release_validation_failed(patched_github, capture):

    exception = ReleaseValidationFailedException('error')

    patched_github.gh.generate_changelog = MagicMock(side_effect=exception)

    patched_github.run('release --branch-name release', catch_exceptions=True)

    expected_output = 'Not releasing: error'

    assert expected_output == capture.records[6].msg


@pytest.mark.wet(issues=False)
def test_release_branch_cannot_determine_next_version(github, capture, request):

    expected_cause = 'Failed releasing: Cannot determine what the next version number should be'

    _create_release(github, request, 'fc517a05bdd22748714e9900b9c9860f37546738', '0.0.1')
    _create_commit(github, request)

    github.run('release --branch-name release --force', catch_exceptions=True)

    assert expected_cause in capture.records[3].msg


@pytest.mark.wet
def test_release_branch(github):

    github.run('release --branch-name release')

    expected_release_title = '1.0.0'
    repo = github.gh.repo
    github_release = repo.get_release(id=expected_release_title)

    expected_message = 'Set version to 1.0.0'
    expected_issue_comment = 'This issue is part of release [{}]({})'.format(
        expected_release_title, github_release.html_url)
    expected_temp_branch_name = 'release-e4f0041f7bac3a672db645377c720ff61ad2b22a'

    release_tag_sha = repo.get_git_ref(ref='tags/{}'.format(github_release.tag_name)).object.sha
    release_tag_commit = repo.get_commit(sha=release_tag_sha)
    release_branch_sha = repo.get_commit(sha='release').sha
    master_branch_sha = repo.get_commit(sha='master').sha

    assert expected_message == release_tag_commit.commit.message

    with pytest.raises(GithubException):
        repo.get_branch(branch=expected_temp_branch_name)

    def _assert_issue(number):
        issue = repo.get_issue(number=number)
        comments = [comment.body for comment in issue.get_comments()]
        assert issue.state == 'closed'
        assert expected_issue_comment in comments

    _assert_issue(1)
    _assert_issue(5)
    _assert_issue(6)
    _assert_issue(7)

    assert release_tag_sha == release_branch_sha
    assert release_tag_sha == master_branch_sha

    assert expected_message in github_release.body


def test_validate_build(pyci, capture, mocker):

    ci = MagicMock()

    mocker.patch(target='pyci.api.ci.detect', new=MagicMock(return_value=ci))

    pyci.run('github validate-build --release-branch-name release')

    expected_output = 'Validation passed!'

    assert expected_output == capture.records[1].msg
    ci.validate_build.assert_called_once_with(release_branch='release')


def test_validate_build_failed(pyci, capture, mocker):

    ci = MagicMock()

    exception = exceptions.ApiException('error')
    ci.validate_build = MagicMock(side_effect=exception)

    mocker.patch(target='pyci.api.ci.detect', new=MagicMock(return_value=ci))

    pyci.run('github validate-build --release-branch-name release', catch_exceptions=True)

    expected_output = 'Build validation failed: error'

    assert expected_output == capture.records[2].msg
    ci.validate_build.assert_called_once_with(release_branch='release')


def test_validate_commit_no_sha_no_branch(patched_github, capture):

    patched_github.run('validate-commit', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --branch.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.validate_commit.assert_not_called()


def test_validate_commit_sha_and_branch(patched_github, capture):

    patched_github.run('validate-commit --sha sha --branch branch', catch_exceptions=True)

    expected_output = 'Use either --sha or --branch, not both.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.validate_commit.assert_not_called()


def test_validate_commit_sha(patched_github, capture):

    patched_github.run('validate-commit --sha sha')

    expected_output = 'Validation passed!'

    assert expected_output == capture.records[1].msg
    patched_github.gh.validate_commit.assert_called_once_with(sha='sha', branch=None)


def test_validate_commit_branch(patched_github, capture):

    patched_github.run('validate-commit --branch branch')

    expected_output = 'Validation passed!'

    assert expected_output == capture.records[1].msg
    patched_github.gh.validate_commit.assert_called_once_with(sha=None, branch='branch')


def test_validate_commit_failed(patched_github, capture):

    exception = ApiException('error')

    patched_github.gh.validate_commit = MagicMock(side_effect=exception)

    patched_github.run('validate-commit --branch branch', catch_exceptions=True)

    expected_output = 'Commit validation failed: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.validate_commit.assert_called_once_with(sha=None, branch='branch')


def test_generate_changelog_no_sha_no_branch(patched_github, capture):

    patched_github.run('generate-changelog', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --branch.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.generate_changelog.assert_not_called()


def test_generate_changelog_sha_and_branch(patched_github, capture):

    patched_github.run('generate-changelog --sha sha --branch branch', catch_exceptions=True)

    expected_output = 'Use either --sha or --branch, not both.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.generate_changelog.assert_not_called()


def test_generate_changelog_sha(patched_github, capture, temp_dir):

    destination = os.path.join(temp_dir, 'changelog.md')

    changelog = MagicMock()
    changelog.render = MagicMock(return_value='changelog')
    patched_github.gh.generate_changelog = MagicMock(return_value=changelog)

    patched_github.run('generate-changelog --sha sha --target {}'.format(destination))

    expected_output = 'Generated at {}'.format(destination)

    assert expected_output == capture.records[2].msg
    patched_github.gh.generate_changelog.assert_called_once_with(sha='sha', branch=None)


def test_generate_changelog_branch(patched_github, capture, temp_dir):

    destination = os.path.join(temp_dir, 'changelog.md')

    changelog = MagicMock()
    changelog.render = MagicMock(return_value='changelog')
    patched_github.gh.generate_changelog = MagicMock(return_value=changelog)

    patched_github.run('generate-changelog --branch branch --target {}'.format(destination))

    expected_output = 'Generated at {}'.format(destination)

    assert expected_output == capture.records[2].msg
    patched_github.gh.generate_changelog.assert_called_once_with(branch='branch', sha=None)


@pytest.mark.usefixtures("isolated")
def test_generate_changelog_no_target(patched_github, capture):

    destination = os.path.join(os.getcwd(), 'sha-changelog.md')

    changelog = MagicMock()
    changelog.render = MagicMock(return_value='changelog')
    patched_github.gh.generate_changelog = MagicMock(return_value=changelog)

    patched_github.run('generate-changelog --sha sha')

    expected_output = 'Generated at {}'.format(destination)

    assert expected_output == capture.records[2].msg
    patched_github.gh.generate_changelog.assert_called_once_with(sha='sha', branch=None)


def test_generate_changelog_file_exists(patched_github, capture):

    exception = exceptions.FileExistException(path='path')

    patched_github.gh.generate_changelog = MagicMock(side_effect=exception)

    patched_github.run('generate-changelog --branch branch', catch_exceptions=True)

    expected_output = 'Failed generating changelog: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the file and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_github.gh.generate_changelog.assert_called_once_with(sha=None, branch='branch')


def test_generate_changelog_file_is_a_directory(patched_github, capture):

    exception = exceptions.FileIsADirectoryException(path='path')

    patched_github.gh.generate_changelog = MagicMock(side_effect=exception)

    patched_github.run('generate-changelog --branch branch', catch_exceptions=True)

    expected_output = 'Failed generating changelog: {}'.format(str(exception))
    expected_possible_solution = 'Delete/Move the directory and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_github.gh.generate_changelog.assert_called_once_with(sha=None, branch='branch')


def test_generate_changelog_directory_doesnt_exist(patched_github, capture):

    exception = exceptions.DirectoryDoesntExistException(path='path')

    patched_github.gh.generate_changelog = MagicMock(side_effect=exception)

    patched_github.run('generate-changelog --branch branch', catch_exceptions=True)

    expected_output = 'Failed generating changelog: {}'.format(str(exception))
    expected_possible_solution = 'Create the directory and try again'

    assert expected_output in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_github.gh.generate_changelog.assert_called_once_with(sha=None, branch='branch')


def test_generate_changelog_failed(patched_github, capture):

    exception = ApiException('error')

    patched_github.gh.generate_changelog = MagicMock(side_effect=exception)

    patched_github.run('generate-changelog --branch branch', catch_exceptions=True)

    expected_output = 'Failed generating changelog: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.generate_changelog.assert_called_once_with(sha=None, branch='branch')


def test_upload_changelog_file_validation_error(patched_github, capture):

    patched_github.run('upload-changelog --changelog changelog --release release',
                       catch_exceptions=True)

    expected_output = 'Failed uploading changelog: File does not exist: changelog'

    assert expected_output == capture.records[2].msg
    patched_github.gh.upload_changelog.assert_not_called()


def test_upload_changelog_failed(patched_github, capture):

    exception = ApiException('error')

    patched_github.gh.upload_changelog = MagicMock(side_effect=exception)

    changelog = tempfile.mkstemp()[1]

    patched_github.run('upload-changelog --changelog {} --release release'.format(changelog),
                       catch_exceptions=True)

    expected_output = 'Failed uploading changelog: error'

    assert expected_output == capture.records[2].msg
    with open(changelog) as stream:
        patched_github.gh.upload_changelog.assert_called_once_with(
            changelog=stream.read(),
            release='release')


def test_upload_changelog(patched_github, capture):

    release = Release(impl=None, title='title', url='url', sha='sha')

    patched_github.gh.upload_changelog = MagicMock(return_value=release)

    changelog = tempfile.mkstemp()[1]

    patched_github.run('upload-changelog --changelog {} --release release'.format(changelog),
                       catch_exceptions=True)

    expected_output = 'Uploaded: url'

    assert expected_output == capture.records[1].msg


def test_create_release_no_sha_no_branch(patched_github, capture):

    patched_github.run('create-release', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --branch.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.create_release.assert_not_called()


def test_create_release_sha_and_branch(patched_github, capture):

    patched_github.run('create-release --sha sha --branch branch', catch_exceptions=True)

    expected_output = 'Use either --sha or --branch, not both.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.create_release.assert_not_called()


def test_create_release_sha(patched_github, capture):

    release = Release(title='0.0.1', url='url', impl=None, sha='sha')

    patched_github.gh.create_release = MagicMock(return_value=release)

    patched_github.run('create-release --sha sha')

    expected_output = 'Release created: url'

    assert expected_output == capture.records[1].msg
    patched_github.gh.create_release.assert_called_once_with(sha='sha', branch=None)


def test_create_release_branch(patched_github, capture):

    release = Release(title='0.0.1', url='url', impl=None, sha='sha')

    patched_github.gh.create_release = MagicMock(return_value=release)

    patched_github.run('create-release --branch branch')

    expected_output = 'Release created: url'

    assert expected_output == capture.records[1].msg
    patched_github.gh.create_release.assert_called_once_with(sha=None, branch='branch')


def test_create_release_not_python_project(patched_github, capture):

    exception = exceptions.NotPythonProjectException(repo='repo', sha='sha', cause='cause')

    patched_github.gh.create_release = MagicMock(side_effect=exception)

    patched_github.run('create-release --branch branch', catch_exceptions=True)

    expected_error_message = 'Failed creating release: {}'.format(str(exception))
    expected_possible_solution = 'Please follow these instructions to create a standard ' \
                                 'python project --> https://packaging.python.org' \
                                 '/tutorials/distributing-packages/'

    assert expected_error_message in capture.records[2].msg
    assert expected_possible_solution in capture.records[2].msg
    patched_github.gh.create_release.assert_called_once_with(sha=None, branch='branch')


def test_create_release_failed(patched_github, capture):

    exception = ApiException('error')

    patched_github.gh.create_release = MagicMock(side_effect=exception)

    patched_github.run('create-release --branch branch', catch_exceptions=True)

    expected_output = 'Failed creating release: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.create_release.assert_called_once_with(sha=None, branch='branch')


def test_upload_asset(patched_github, capture):

    patched_github.gh.upload_asset = MagicMock(return_value='url')

    patched_github.run('upload-asset --asset asset --release release')

    expected_output = 'Uploaded: url'

    assert expected_output == capture.records[1].msg
    patched_github.gh.upload_asset.assert_called_once_with(asset='asset', release='release')


def test_upload_asset_failed(patched_github, capture):

    exception = ApiException('error')

    patched_github.gh.upload_asset = MagicMock(side_effect=exception)

    patched_github.run('upload-asset --asset asset --release release', catch_exceptions=True)

    expected_output = 'Failed uploading asset: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.upload_asset.assert_called_once_with(asset='asset', release='release')


def test_detect_issue_no_sha_no_message(patched_github, capture):

    patched_github.run('detect-issue', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --message.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.detect_issue.assert_not_called()


def test_detect_issue_sha_and_message(patched_github, capture):

    patched_github.run('detect-issue --sha sha --message message', catch_exceptions=True)

    expected_output = 'Use either --sha or --message, not both.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.detect_issue.assert_not_called()


def test_detect_issue(patched_github, capture):

    issue = Issue(impl=None, number=4, url='url')

    patched_github.gh.detect_issue = MagicMock(return_value=issue)

    patched_github.run('detect-issue --message message')

    expected_output = 'Issue detected: url'

    assert expected_output == capture.records[1].msg
    patched_github.gh.detect_issue.assert_called_once_with(commit_message='message', sha=None)


def test_detect_issue_not_related_to_issue(patched_github, capture):

    patched_github.gh.detect_issue = MagicMock(return_value=None)

    patched_github.run('detect-issue --message message')

    expected_output = 'The commit is not related ot any issue.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.detect_issue.assert_called_once_with(commit_message='message', sha=None)


def test_detect_issue_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.detect_issue = MagicMock(side_effect=exception)

    patched_github.run('detect-issue --sha sha', catch_exceptions=True)

    expected_output = 'Failed detecting issue: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.detect_issue.assert_called_once_with(commit_message=None, sha='sha')


def test_delete_release(patched_github, capture):

    patched_github.run('delete-release --name 0.0.1')

    expected_output = 'Deleted release: 0.0.1'

    assert expected_output == capture.records[1].msg
    patched_github.gh.delete_release.assert_called_once_with(name='0.0.1')


def test_delete_release_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.delete_release = MagicMock(side_effect=exception)

    patched_github.run('delete-release --name 0.0.1', catch_exceptions=True)

    expected_output = 'Failed deleting release: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.delete_release.assert_called_once_with(name='0.0.1')


def test_delete_tag(patched_github, capture):

    patched_github.run('delete-tag --name 0.0.1')

    expected_output = 'Deleted tag: 0.0.1'

    assert expected_output == capture.records[1].msg
    patched_github.gh.delete_tag.assert_called_once_with(name='0.0.1')


def test_delete_tag_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.delete_tag = MagicMock(side_effect=exception)

    patched_github.run('delete-tag --name 0.0.1', catch_exceptions=True)

    expected_output = 'Failed deleting tag: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.delete_tag.assert_called_once_with(name='0.0.1')


def test_bump_version(patched_github, capture):

    bump = Bump(prev_version='0.0.1', next_version='0.0.2', impl=None, sha='sha')

    patched_github.gh.bump_version = MagicMock(return_value=bump)

    patched_github.run('bump-version --branch release --semantic patch')

    expected_output = 'Bumped version from 0.0.1 to 0.0.2'

    assert expected_output == capture.records[1].msg
    patched_github.gh.bump_version.assert_called_once_with(branch='release', semantic='patch')


def test_bump_version_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.bump_version = MagicMock(side_effect=exception)

    patched_github.run('bump-version --branch release --semantic patch', catch_exceptions=True)

    expected_output = 'Failed bumping version: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.bump_version.assert_called_once_with(branch='release', semantic='patch')


def test_set_version(patched_github, capture):

    bump = Bump(prev_version='0.0.1', next_version='0.0.2', impl=None, sha='sha')

    patched_github.gh.set_version = MagicMock(return_value=bump)

    patched_github.run('set-version --branch release --value 0.0.2')

    expected_output = 'Version is now 0.0.2 (was 0.0.1)'

    assert expected_output == capture.records[1].msg
    patched_github.gh.set_version.assert_called_once_with(branch='release', value='0.0.2')


def test_set_version_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.set_version = MagicMock(side_effect=exception)

    patched_github.run('set-version --branch release --value 0.0.1', catch_exceptions=True)

    expected_output = 'Failed setting version: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.set_version.assert_called_once_with(branch='release', value='0.0.1')


def test_reset_branch(patched_github, capture):

    patched_github.run('reset-branch --name release --sha sha')

    expected_output = 'Branch release is now at sha.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.reset_branch.assert_called_once_with(name='release', sha='sha')


def test_reset_branch_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.reset_branch = MagicMock(side_effect=exception)

    patched_github.run('reset-branch --name release --sha sha', catch_exceptions=True)

    expected_output = 'Failed resetting branch: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.reset_branch.assert_called_once_with(name='release', sha='sha')


def test_reset_tag(patched_github, capture):

    patched_github.run('reset-tag --name release --sha sha')

    expected_output = 'Tag release is now at sha.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.reset_tag.assert_called_once_with(name='release', sha='sha')


def test_reset_tag_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.reset_tag = MagicMock(side_effect=exception)

    patched_github.run('reset-tag --name release --sha sha', catch_exceptions=True)

    expected_output = 'Failed resetting tag: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.reset_tag.assert_called_once_with(name='release', sha='sha')


def test_create_branch(patched_github, capture):

    patched_github.run('create-branch --name release --sha sha')

    expected_output = 'Branch created: release.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.create_branch.assert_called_once_with(name='release', sha='sha')


def test_create_branch_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.create_branch = MagicMock(side_effect=exception)

    patched_github.run('create-branch --name release --sha sha', catch_exceptions=True)

    expected_output = 'Failed creating branch: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.create_branch.assert_called_once_with(name='release', sha='sha')


def test_delete_branch(patched_github, capture):

    patched_github.run('delete-branch --name branch')

    expected_output = 'Branch deleted: branch.'

    assert expected_output == capture.records[1].msg
    patched_github.gh.delete_branch.assert_called_once_with(name='branch')


def test_delete_branch_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.delete_branch = MagicMock(side_effect=exception)

    patched_github.run('delete-branch --name branch', catch_exceptions=True)

    expected_output = 'Failed deleting branch: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.delete_branch.assert_called_once_with(name='branch')


def test_commit_file(patched_github, capture):

    commit = Commit(impl=None, sha='sha', url='url')

    patched_github.gh.commit_file = MagicMock(return_value=commit)

    patched_github.run('commit-file '
                       '--path path '
                       '--contents contents '
                       '--message message '
                       '--branch branch')

    expected_output = 'Committed: url'

    assert expected_output == capture.records[1].msg
    patched_github.gh.commit_file.assert_called_once_with(
        path='path',
        contents='contents',
        message='message',
        branch='branch')


def test_commit_file_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.commit_file = MagicMock(side_effect=exception)

    patched_github.run('commit-file '
                       '--path path '
                       '--contents contents '
                       '--message message '
                       '--branch branch',
                       catch_exceptions=True)

    expected_output = 'Failed committing file: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.commit_file.assert_called_once_with(
        path='path',
        contents='contents',
        message='message',
        branch='branch')


def test_create_commit(patched_github, capture):

    commit = Commit(impl=None, sha='sha', url='url')

    patched_github.gh.create_commit = MagicMock(return_value=commit)

    patched_github.run('create-commit '
                       '--path path '
                       '--contents contents '
                       '--message message '
                       '--branch branch')

    expected_output = 'Created: url'

    assert expected_output == capture.records[1].msg
    patched_github.gh.create_commit.assert_called_once_with(
        path='path',
        contents='contents',
        message='message',
        branch='branch')


def test_create_commit_failed(patched_github, capture):

    exception = exceptions.ApiException('error')

    patched_github.gh.create_commit = MagicMock(side_effect=exception)

    patched_github.run('create-commit '
                       '--path path '
                       '--contents contents '
                       '--message message '
                       '--branch branch',
                       catch_exceptions=True)

    expected_output = 'Failed creating commit: error'

    assert expected_output == capture.records[2].msg
    patched_github.gh.create_commit.assert_called_once_with(
        path='path',
        contents='contents',
        message='message',
        branch='branch')
