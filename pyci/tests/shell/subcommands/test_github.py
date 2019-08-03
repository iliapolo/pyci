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

import pytest
from github import GithubException, UnknownObjectException

from pyci.tests.conftest import REPO_UNDER_TEST, LAST_COMMIT
from pyci.api.scm.gh import BUMP_VERSION_COMMIT_MESSAGE_FORMAT
from pyci.api.ci import ci
from pyci.api import utils
from pyci.tests import utils as test_utils


def _create_commit(github, request, message=None):

    message = message or request.node.name

    return github.api.commit(
        path='README.md',
        contents=request.node.name,
        message=message,
        branch='release')


def _create_branch(github, request, sha, name=None):

    branch_name = name or request.node.name

    return github.api.repo.create_git_ref(ref='refs/heads/{}'.format(branch_name), sha=sha)


@pytest.mark.wet
def test_release(github):

    github.run('release --branch release')

    expected_release_title = '1.0.0'
    repo = github.api.repo
    github_release = repo.get_release(id=expected_release_title)

    expected_message = BUMP_VERSION_COMMIT_MESSAGE_FORMAT.format(expected_release_title)
    expected_issue_comment = 'This issue is part of release [{}]({})'.format(
        expected_release_title, github_release.html_url)

    release_tag_sha = repo.get_git_ref(ref='tags/{}'.format(github_release.tag_name)).object.sha
    release_tag_commit = repo.get_commit(sha=release_tag_sha)
    release_branch_sha = repo.get_commit(sha='release').sha
    master_branch_sha = repo.get_commit(sha='master').sha

    assert expected_message == release_tag_commit.commit.message

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


@pytest.mark.wet
def test_release_commit_multiple_issues(github):

    github.api.commit(path='README.md',
                      contents='For release',
                      message='This resolves issue #12 and #11',
                      branch='release')

    github.run('release --branch release')

    expected_release_title = '3.0.0'
    repo = github.api.repo
    github_release = repo.get_release(id=expected_release_title)

    expected_issue_comment = 'This issue is part of release [{}]({})'.format(
        expected_release_title, github_release.html_url)

    def _assert_issue(number):
        issue = repo.get_issue(number=number)
        comments = [comment.body for comment in issue.get_comments()]
        assert issue.state == 'closed'
        assert expected_issue_comment in comments

    _assert_issue(1)
    _assert_issue(5)
    _assert_issue(6)
    _assert_issue(7)
    _assert_issue(11)
    _assert_issue(12)


@pytest.mark.wet
def test_release_twice(github):

    github.run('release --force --branch release')

    github.api.reset_branch(name='release', sha=LAST_COMMIT, hard=True)
    github.api.reset_branch(name='master', sha=LAST_COMMIT, hard=True)

    github.run('release --force --branch release')

    expected_number_of_releases = 1

    assert expected_number_of_releases == len(list(github.api.repo.get_releases()))


@pytest.mark.wet
def test_release_force_with_changelog_base(github, request):

    test_utils.create_release(github.api, request, 'cf2d64132f00c849ae1bb62ffb2e32b719b6cbac', '1.0.0')

    github.api.set_version(value='1.0.0', branch='release')

    # run another release with a changelog generated from a sha prior to existing release
    # this should cause another major version bump
    github.run('release --branch release --force --changelog-base 4772c5708ff25a69f1f6c8106c7fe863c6686459')

    expected_release_title = '2.0.0'

    github_release = github.api.repo.get_release(id=expected_release_title)

    assert github_release


@pytest.mark.wet
def test_release_with_version(github):

    expected_release_title = '8.0.0'

    github.run('release --branch release --version {}'.format(expected_release_title))

    github_release = github.api.repo.get_release(id=expected_release_title)

    assert github_release


@pytest.mark.wet
def test_release_not_fast_forward(pyci, repo, mocker):

    ci_provider = ci.detect(environ={
        'TRAVIS': 'True',
        'TRAVIS_REPO_SLUG': REPO_UNDER_TEST,
        'TRAVIS_BRANCH': 'release',
        'TRAVIS_COMMIT': '5b0aa87aac95cc24d24684f30daab44d2cc61d5d',
        'TRAVIS_TAG': None,
        'TRAVIS_PULL_REQUEST': 'false'
    })

    detect = test_utils.MagicMock(return_value=ci_provider)

    mocker.patch(target='pyci.api.ci.ci.detect', new=detect)

    result = pyci.run('github --repo {} release --force --branch release'
                      .format(REPO_UNDER_TEST),
                      catch_exceptions=True)

    expected_output = 'is not a fast-forward'
    expected_number_of_releases = 0
    expected_number_of_tags = 0
    releases = repo.get_releases()
    tags = repo.get_tags()

    assert expected_output in result.std_out
    assert expected_number_of_releases == len(list(releases))
    assert expected_number_of_tags == len(list(tags))


@pytest.mark.wet
def test_release_branch_cannot_determine_next_version(github):

    github.api.reset_branch(name='release', sha='33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                            hard=True)

    expected_cause = 'None of the commits in the changelog references an issue labeled with a ' \
                     'release label. Cannot determine what the version number should be'

    result = github.run('release --force --branch release', catch_exceptions=True)

    assert expected_cause in result.std_out


@pytest.mark.wet
def test_release_validation_failed(github):

    github.api.reset_branch(name='release', sha='33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                            hard=True)

    result = github.run('release --branch release', catch_exceptions=True)

    expected_output = 'Not releasing: Commit 33526a9e0445541d96e027db2aeb93d07cdf8bd6 does ' \
                      'not reference any issue'

    assert not list(github.api.repo.get_releases())
    assert expected_output in result.std_out
    assert result.return_code == 0


def test_validate_commit_sha(github):

    result = github.run('validate-commit --sha {}'.format(LAST_COMMIT))

    expected_output = 'Validation passed'

    assert expected_output in result.std_out


def test_validate_commit(github):

    result = github.run('validate-commit')

    expected_output = 'Validation passed'

    assert expected_output in result.std_out


def test_generate_changelog_sha(github, temp_dir):

    destination = os.path.join(temp_dir, 'changelog.md')

    result = github.run('generate-changelog --sha {} --target {}'.format(LAST_COMMIT, destination))

    expected_output = 'Changelog written to: {}'.format(destination)

    assert os.path.exists(destination)
    assert expected_output in result.std_out


def test_generate_changelog_from_base(github, temp_dir):

    destination = os.path.join(temp_dir, 'changelog.md')

    base = '4772c5708ff25a69f1f6c8106c7fe863c6686459'

    result = github.run('generate-changelog --base {} --sha {} --target {}'.format(base, LAST_COMMIT, destination))

    expected_output = 'Changelog written to: {}'.format(destination)

    assert os.path.exists(destination)
    assert expected_output in result.std_out


def test_generate_changelog_no_target(github):

    destination = os.path.join(os.getcwd(), 'release-changelog.md')

    result = github.run('generate-changelog --sha release')

    expected_output = 'Changelog written to: {}'.format(destination)

    assert os.path.exists(destination)
    assert expected_output in result.std_out


def test_generate_changelog_failed(github):

    destination = os.path.join(os.getcwd(), 'release-changelog.md')

    with open(destination, 'w') as stream:
        stream.write('changelog')

    result = github.run('generate-changelog --sha release', catch_exceptions=True)

    expected_output = 'File exists: {}'.format(destination)

    assert expected_output in result.std_out


def test_upload_changelog_failed(github):

    result = github.run('upload-changelog --changelog doesnt-exist --release release',
                        catch_exceptions=True)

    expected_output = 'File does not exist: doesnt-exist'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_upload_changelog(github, request, temp_dir):

    release = test_utils.create_release(github.api, request, LAST_COMMIT)

    changelog_file = os.path.join(temp_dir, 'changelog')
    changelog_content = 'changelog'

    with open(changelog_file, 'w') as stream:
        stream.write(changelog_content)

    result = github.run('upload-changelog --changelog {} --release {}'
                        .format(changelog_file, release.title), catch_exceptions=True)

    expected_output = 'Uploaded changelog to release {}'.format(release.title)

    release_body = github.api.repo.get_release(id=release.title).body

    assert changelog_content == release_body
    assert expected_output in result.std_out


@pytest.mark.wet
def test_create_release_sha(github):

    result = github.run('create-release --sha {}'.format(LAST_COMMIT))

    expected_output = 'Release created: https://github.com/{}/releases/tag/0.0.1'.format(
        REPO_UNDER_TEST)

    assert github.api.repo.get_release(id='0.0.1')
    assert expected_output in result.std_out


@pytest.mark.wet
def test_create_release_already_exists(github):

    sha = '1997dbd53731b5f51153bbae35bbab6fcc6dab81'
    github.api.create_release(sha=sha)

    result = github.run('create-release --sha={}'.format(sha), catch_exceptions=True)

    expected_output = 'Release 0.0.1 already exists'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_create_release_not_python_project(github):

    sha = '3ee89f04a8a2b71d06aa80c5178943e7b396be47'

    result = github.run('create-release --sha {}'.format(sha), catch_exceptions=True)

    expected_error_message = 'does not contain a setup.py file'
    expected_possible_solution = 'Create a setup.py file'

    assert expected_error_message in result.std_out
    assert expected_possible_solution in result.std_out


def test_create_release_failed(github):

    result = github.run('create-release --sha branch', catch_exceptions=True)

    expected_output = 'Commit not found: branch'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_upload_asset(github, request, temp_dir):

    release = test_utils.create_release(github.api, request, LAST_COMMIT)

    asset_file = os.path.join(temp_dir, 'asset')
    with open(asset_file, 'w') as stream:
        stream.write('asset')

    result = github.run('upload-asset --asset {} --release {}'.format(asset_file, release.title))

    expected_output = 'Uploaded asset: https://github.com/{}/releases/download/{}/asset'.format(
        REPO_UNDER_TEST, release.title)

    assets = [asset.name for asset in github.api.repo.get_release(id=release.title).get_assets()]

    assert 'asset' in assets
    assert expected_output in result.std_out


def test_upload_asset_failed(github):

    result = github.run('upload-asset --asset asset --release release', catch_exceptions=True)

    expected_output = 'File does not exist'

    assert expected_output in result.std_out


def test_detect_issues_no_sha_no_message(github):

    result = github.run('detect-issues', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --message.'

    assert expected_output in result.std_out


def test_detect_issues_sha_and_message(github):

    result = github.run('detect-issues --sha sha --message message', catch_exceptions=True)

    expected_output = 'Use either --sha or --message, not both.'

    assert expected_output in result.std_out


def test_detect_issues(github):

    result = github.run('detect-issues --message "Dummy commit linked to issue (#6)"')

    expected_output = 'Issue detected: https://github.com/{}/issues/6'.format(REPO_UNDER_TEST)

    assert expected_output in result.std_out


def test_detect_issues_not_related_to_issue(github):

    result = github.run('detect-issues --message message')

    expected_output = 'The commit is not related ot any issue.'

    assert expected_output in result.std_out


def test_detect_issues_failed(github):

    result = github.run('detect-issues --sha sha', catch_exceptions=True)

    expected_output = 'Commit not found: sha'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_delete_release(github, request):

    release = test_utils.create_release(github.api, request, LAST_COMMIT)

    github.run('delete-release --name {}'.format(release.title))

    with pytest.raises(UnknownObjectException):
        github.api.repo.get_release(id=release.title)


def test_delete_release_failed(github):

    result = github.run('delete-release --name 0.0.1', catch_exceptions=True)

    expected_output = 'Release not found: 0.0.1'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_delete_tag(github, request):

    release = test_utils.create_release(github.api, request, LAST_COMMIT)

    github.run('delete-tag --name {}'.format(release.title))

    with pytest.raises(UnknownObjectException):
        github.api.repo.get_git_ref('tags/{}'.format(release.title))


def test_delete_tag_failed(github):

    result = github.run('delete-tag --name 0.0.1', catch_exceptions=True)

    expected_output = 'Tag not found: 0.0.1'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_bump_version(github, temp_dir, runner):

    result = github.run('bump-version --branch release --semantic patch')

    expected_version = '0.0.2'
    expected_output = 'Bumped version from 0.0.1 to {}'.format(expected_version)

    setup_py = github.api.repo.get_contents(path='setup.py', ref='heads/release').decoded_content
    setup_py_path = os.path.join(temp_dir, 'setup.py')
    with open(setup_py_path, 'wb') as stream:
        stream.write(setup_py)

    actual_version = runner.run('{} {} --version'.format(utils.get_python_executable('python'),
                                                         setup_py_path)).std_out

    assert expected_output in result.std_out
    assert expected_version == actual_version


def test_bump_version_failed(github):

    result = github.run('bump-version --branch doesnt-exist --semantic patch',
                        catch_exceptions=True)

    expected_output = 'Commit not found: doesnt-exist'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_set_version(github, temp_dir, runner):

    expected_version = '0.0.3'
    result = github.run('set-version --branch release --value {}'.format(expected_version))

    setup_py = github.api.repo.get_contents(path='setup.py', ref='heads/release').decoded_content
    setup_py_path = os.path.join(temp_dir, 'setup.py')
    with open(setup_py_path, 'wb') as stream:
        stream.write(setup_py)

    actual_version = runner.run('{} {} --version'.format(utils.get_python_executable('python'),
                                                         setup_py_path)).std_out

    expected_output = 'Version is now {} (was 0.0.1)'.format(expected_version)

    assert expected_output in result.std_out
    assert expected_version == actual_version


def test_set_version_failed(github):

    result = github.run('set-version --branch doesnt-exist --value 0.0.1', catch_exceptions=True)

    expected_output = 'Commit not found: doesnt-exist'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_reset_branch(github):

    # pylint: disable=protected-access
    commit = github.api._create_commit(sha='release',
                                       path='README.md',
                                       contents='hello',
                                       message='message')

    result = github.run('reset-branch --name release --sha {}'.format(commit.sha))

    expected_output = 'Branch release is now at {}'.format(commit.sha)

    actual_sha = github.api.repo.get_branch(branch='release').commit.sha

    assert commit.sha == actual_sha
    assert expected_output in result.std_out


@pytest.mark.wet
def test_reset_branch_already_at_sha(github):

    result = github.run('reset-branch --name release --sha={}'.format(LAST_COMMIT),
                        catch_exceptions=True)

    expected_output = 'Reference refs/heads/release is already at {}'.format(LAST_COMMIT)

    assert expected_output in result.std_out


@pytest.mark.wet
def test_reset_branch_hard(github):

    # pylint: disable=protected-access
    commit = github.api._create_commit(sha='release',
                                       path='README.md',
                                       contents='hello',
                                       message='message')

    result = github.run('reset-branch --name release --sha {} --hard'.format(commit.sha))

    expected_output = 'Branch release is now at {}'.format(commit.sha)

    actual_sha = github.api.repo.get_branch(branch='release').commit.sha

    assert commit.sha == actual_sha
    assert expected_output in result.std_out


@pytest.mark.wet
def test_reset_branch_not_fast_forward(github):

    sha = '5b0aa87aac95cc24d24684f30daab44d2cc61d5d'

    result = github.run('reset-branch --name release --sha {}'.format(sha), catch_exceptions=True)

    expected_output = 'Update of ref refs/heads/release to {} is not a ' \
                      'fast-forward'.format(sha)

    branch = github.api.repo.get_branch(branch='release')

    assert branch.commit.sha == LAST_COMMIT
    assert expected_output in result.std_out


@pytest.mark.wet
def test_reset_branch_not_fast_forward_hard(github):

    expected_sha = '5b0aa87aac95cc24d24684f30daab44d2cc61d5d'

    result = github.run('reset-branch --name release --sha {} --hard'.format(expected_sha))

    expected_output = 'Branch release is now at {}'.format(expected_sha)

    branch = github.api.repo.get_branch(branch='release')

    assert branch.commit.sha == expected_sha
    assert expected_output in result.std_out


def test_reset_branch_failed(github):

    result = github.run('reset-branch --name doesnt-exist --sha sha', catch_exceptions=True)

    expected_output = 'Branch doesnt-exist doesnt exist in {}'.format(REPO_UNDER_TEST)

    assert expected_output in result.std_out


@pytest.mark.wet
def test_create_branch(github, request):

    expected_sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'

    branch_name = request.node.name

    result = github.run('create-branch --name {} --sha {}'.format(branch_name, expected_sha))

    expected_output = 'Branch {} created at {}'.format(branch_name, expected_sha)

    branch = github.api.repo.get_branch(branch=branch_name)

    assert expected_output in result.std_out
    assert expected_sha == branch.commit.sha


def test_create_branch_failed(github):

    result = github.run('create-branch '
                        '--name release '
                        '--sha e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1', catch_exceptions=True)

    expected_output = 'Commit not found: e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_delete_branch(github, request):

    branch_name = request.node.name

    _create_branch(github, request, LAST_COMMIT, name=branch_name)

    result = github.run('delete-branch --name {}'.format(branch_name))

    expected_output = 'Done'

    with pytest.raises(GithubException):
        github.api.repo.get_branch(branch=branch_name)

    assert expected_output in result.std_out


def test_delete_branch_failed(github):

    result = github.run('delete-branch --name branch', catch_exceptions=True)

    expected_output = 'Branch branch doesnt exist in iliapolo/pyci-guinea-pig'

    assert expected_output in result.std_out


@pytest.mark.wet
def test_commit_file(github):

    contents = 'contents'

    result = github.run('commit '
                        '--path README.md '
                        '--contents {} '
                        '--message message '
                        '--branch release'.format(contents))

    expected_output = 'Created commit'

    readme = github.api.repo.get_contents(path='README.md', ref='heads/release').decoded_content

    if utils.is_python_3():
        readme = readme.decode()

    assert expected_output in result.std_out
    assert contents == readme


def test_commit_file_failed(github):

    result = github.run('commit '
                        '--path path '
                        '--contents contents '
                        '--message message '
                        '--branch branch',
                        catch_exceptions=True)

    expected_output = 'Branch branch doesnt exist in {}'.format(REPO_UNDER_TEST)

    assert expected_output in result.std_out


@pytest.mark.wet
def test_close_issue_issue_doesnt_exist(github, request):

    release = test_utils.create_release(github.api, request, LAST_COMMIT)

    expected_output = 'Issue 100 not found'

    result = github.run('close-issue --number=100 --release={}'.format(release.title),
                        catch_exceptions=True)

    assert expected_output in result.std_out


def test_close_issue_release_doesnt_exist(github):

    expected_output = 'Release not found: doesnt-exist'

    result = github.run('close-issue --number=7 --release=doesnt-exist',
                        catch_exceptions=True)

    assert expected_output in result.std_out


@pytest.mark.wet
def test_close_issue(github, request):

    release = test_utils.create_release(github.api, request, LAST_COMMIT)

    github.run('close-issue --number=7 --release {}'.format(release.title))

    expected_status = 'closed'
    expected_comment = 'This issue is part of release [{}]({})'.format(
        release.title, release.html_url)

    issue = github.api.repo.get_issue(number=7)

    issue_comments = [comment.body for comment in issue.get_comments()]

    assert expected_status == issue.state
    assert expected_comment in issue_comments
