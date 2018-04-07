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
from github import UnknownObjectException, GithubException, GitRelease

from pyci.api import exceptions, utils
from pyci.api.gh import GitHubRepository
from pyci.api.model import Changelog, ChangelogIssue
from pyci.shell import secrets
from pyci.tests import conftest
from pyci.tests.conftest import LAST_COMMIT
from pyci.tests import utils as test_utils


CURRENT_VERSION = '0.0.1'


def _create_branch(github, request, sha, name=None):

    branch_name = name or request.node.name

    return github.api.repo.create_git_ref(ref='refs/heads/{}'.format(branch_name), sha=sha)


def test_no_repo():

    with pytest.raises(exceptions.InvalidArgumentsException):
        GitHubRepository.create(repo='', access_token='token')


def test_no_access_token():

    with pytest.raises(exceptions.InvalidArgumentsException):
        GitHubRepository.create(repo='repo', access_token='')


def test_non_existing_repo():

    with pytest.raises(exceptions.RepositoryNotFoundException):
        _ = GitHubRepository.create(repo='iliapolo/doesnt-exist',
                                    access_token=secrets.github_access_token(True)).repo


def test_default_branch_name(github):

    expected = 'release'

    actual = github.api.default_branch_name

    assert expected == actual


def test_validate_commit_commit_not_related_to_issue(github):

    with pytest.raises(exceptions.CommitNotRelatedToIssueException):
        github.api.validate_commit(sha='aee0c4c21d64f95f6742838aded957c2be71c2e5')


def test_validate_commit_issue_is_not_labeled_as_release(github):

    with pytest.raises(exceptions.IssueNotLabeledAsReleaseException):
        github.api.validate_commit(sha='4772c5708ff25a69f1f6c8106c7fe863c6686459')


@pytest.mark.parametrize("sha", [
    'f7a59debfce6c2242eea5078fa0007b004ce3a57',  # patch issue
    '5b0aa87aac95cc24d24684f30daab44d2cc61d5d',  # minor issue
    'ee1e10067bda8200cc17ae7901c2d3f0fa0c7333'   # major issue
])
def test_validate_commit_via_issue(github, sha):

    github.api.validate_commit(sha=sha)


def test_validate_commit_via_pull_request(github):

    github.api.validate_commit(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')


def test_validate_commit_no_sha_nor_branch(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.validate_commit(sha='', branch='')


def test_validate_commit_sha_and_branch(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.validate_commit(sha='branch', branch='branch')


def test_generate_changelog_no_sha_nor_branch(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.generate_changelog(sha='', branch='')


def test_generate_changelog_sha_and_branch(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.generate_changelog(sha='branch', branch='branch')


# pylint: disable=too-many-locals
@pytest.mark.wet
def test_generate_changelog_relative_to_release(github, request):

    # create two releases from commits prior to our one
    test_utils.create_release(github, request, '0596d82b4786a531b7370448e2b5d0de9922f01a', '0.0.1')
    test_utils.create_release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6', '0.0.2')

    # this is our commit
    ours = github.api.set_version(value='0.0.3', branch='release')

    # create two releases for commits after ours
    after1 = github.api.set_version(value='0.0.4', branch='release')
    after2 = github.api.set_version(value='0.0.5', branch='release')

    test_utils.create_release(github, request, after1.sha, '0.0.4')
    test_utils.create_release(github, request, after2.sha, '0.0.5')

    # this should give us the changelog relative to the 0.0.2 release, not the latest.
    changelog = github.api.generate_changelog(sha=ours.sha)

    expected_features = {7, 6}
    expected_bugs = {5}
    expected_issues = {1}
    expected_commits = {ours.sha}
    expected_next_version = '1.0.0'

    actual_features = {feature.impl.number for feature in changelog.features}
    actual_bugs = {bug.impl.number for bug in changelog.bugs}
    actual_issues = {issue.impl.number for issue in changelog.issues}
    actual_commits = {com.impl.sha for com in changelog.commits}
    actual_next_version = changelog.next_version

    assert expected_features == actual_features
    assert expected_bugs == actual_bugs
    assert expected_issues == actual_issues
    assert expected_commits == actual_commits
    assert expected_next_version == actual_next_version


def test_generate_changelog_no_release(github):

    changelog = github.api.generate_changelog(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')

    expected_features = {7, 6}
    expected_bugs = {5}
    expected_issues = {1}
    expected_commits = {
        '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
        '703afd5a11e186167606a071a556f30174f741d5',
        '6cadc14419e57549365ac4dabea59c4c08be581c',
        '0596d82b4786a531b7370448e2b5d0de9922f01a',
        'b22803b93eaca693db78f9d551ec295946765135',
        '3ee89f04a8a2b71d06aa80c5178943e7b396be47',
        'aee0c4c21d64f95f6742838aded957c2be71c2e5'
    }
    expected_next_version = '1.0.0'

    actual_features = {feature.impl.number for feature in changelog.features}
    actual_bugs = {bug.impl.number for bug in changelog.bugs}
    actual_issues = {issue.impl.number for issue in changelog.issues}
    actual_commits = {com.impl.sha for com in changelog.commits}
    actual_next_version = changelog.next_version

    assert expected_features == actual_features
    assert expected_bugs == actual_bugs
    assert expected_issues == actual_issues
    assert expected_commits == actual_commits
    assert expected_next_version == actual_next_version


def test_upload_changelog_no_changelog(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.upload_changelog(changelog='', release='0.0.1')


def test_upload_changelog_no_release(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.upload_changelog(changelog='changelog', release='')


def test_upload_changelog_non_existing_release(github):

    with pytest.raises(exceptions.ReleaseNotFoundException):
        github.api.upload_changelog(changelog='changelog', release='doesnt-exist')


@pytest.mark.wet
def test_upload_changelog(github, request):

    expected_sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'
    expected_title = '0.0.1'

    test_utils.create_release(github, request, expected_sha, expected_title)

    changelog = Changelog(sha=expected_sha, current_version='0.0.1')

    changelog.add(ChangelogIssue(title='title',
                                 url='url',
                                 timestamp=100,
                                 kind=ChangelogIssue.FEATURE,
                                 semantic=ChangelogIssue.MINOR))

    release = github.api.upload_changelog(changelog=changelog.render(), release='0.0.1')

    github_release = github.api.repo.get_release(id='0.0.1')

    expected_changelog_entry = 'title ([Issue](url))'

    assert expected_sha == release.sha
    assert expected_title == release.title
    assert github_release.html_url == release.url
    assert isinstance(release.impl, GitRelease.GitRelease)

    assert expected_changelog_entry in github_release.body


@pytest.mark.wet
def test_generate_changelog_empty(github, request):

    expected_sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'
    expected_release = '0.0.1'

    test_utils.create_release(github, request, expected_sha, expected_release)

    with pytest.raises(exceptions.EmptyChangelogException) as e:
        github.api.generate_changelog(sha=expected_sha)

    assert expected_sha == e.value.sha
    assert expected_release == e.value.previous_release


def test_delete_release_no_name(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.delete_release(name='')


@pytest.mark.wet
def test_delete_release(github, request):

    repo = github.api.repo

    rel = test_utils.create_release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')

    github.api.delete_release(name=rel.title)

    with pytest.raises(UnknownObjectException):
        repo.get_release(id=request.node.name)


def test_delete_non_existing_release(github):

    with pytest.raises(exceptions.ReleaseNotFoundException):
        github.api.delete_release(name='doesnt-exist')


def test_delete_tag_no_name(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.delete_tag(name='')


@pytest.mark.wet
def test_delete_tag(github, request):

    repo = github.api.repo

    rel = test_utils.create_release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    github.api.delete_tag(name=rel.title)

    with pytest.raises(GithubException):
        repo.get_git_ref('tags/{0}'.format(request.node.name))


def test_delete_non_existing_tag(github):

    with pytest.raises(exceptions.TagNotFoundException):
        github.api.delete_tag(name='doesnt-exist')


def test_upload_asset_no_asset(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.upload_asset(asset='', release='release')


def test_upload_asset_no_release(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.upload_asset(asset='asset', release='')


def test_upload_asset_non_existing_release(github, request, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    with pytest.raises(exceptions.ReleaseNotFoundException):
        github.api.upload_asset(asset=asset, release='doesnt-exist')


@pytest.mark.wet
def test_upload_asset(github, request, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    rel = test_utils.create_release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    github.api.upload_asset(asset=asset, release=rel.title)

    repo = github.api.repo
    assets = list(repo.get_release(id=rel.title).get_assets())

    expected_number_of_assets = 1

    assert expected_number_of_assets == len(assets)
    assert request.node.name == assets[0].name


@pytest.mark.wet
def test_upload_asset_already_exists(github, request, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    rel = test_utils.create_release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    github.api.upload_asset(asset=asset, release=rel.title)
    with pytest.raises(exceptions.AssetAlreadyPublishedException):
        github.api.upload_asset(asset=asset, release=rel.title)


@pytest.mark.wet
@pytest.mark.parametrize("semantic,expected_version", [
    ('patch', '0.0.2'),
    ('minor', '0.1.0'),
    ('major', '1.0.0')
])
def test_bump_version(github, runner, semantic, expected_version, temp_dir):

    bump = github.api.bump_version(semantic=semantic, branch='release')

    setup_py = github.api.repo.get_contents(path='setup.py', ref=bump.sha).decoded_content
    setup_py_path = os.path.join(temp_dir, 'setup.py')
    with open(setup_py_path, 'wb') as stream:
        stream.write(setup_py)

    actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

    assert expected_version == actual_version
    assert expected_version == bump.next_version
    assert CURRENT_VERSION == bump.prev_version


def test_bump_version_no_semantic(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.bump_version(semantic='')


def test_bump_version_semantic_illegal(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.bump_version(semantic='not-semantic')


@pytest.mark.wet
def test_set_version(github, runner, temp_dir):

    bump = github.api.set_version(value='1.2.3', branch='release')

    setup_py = github.api.repo.get_contents(path='setup.py', ref=bump.sha).decoded_content
    setup_py_path = os.path.join(temp_dir, 'setup.py')
    with open(setup_py_path, 'wb') as stream:
        stream.write(setup_py)

    expected_version = '1.2.3'

    actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

    assert expected_version == actual_version
    assert expected_version == bump.next_version
    assert CURRENT_VERSION == bump.prev_version


@pytest.mark.wet
def test_set_version_same_version(github):

    with pytest.raises(exceptions.TargetVersionEqualsCurrentVersionException):
        github.api.set_version(value=CURRENT_VERSION, branch='release')


def test_get_release_no_release(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.get_release(title='')


@pytest.mark.wet
def test_get_release(github, request):

    release = test_utils.create_release(github, request, LAST_COMMIT)

    actual_release = github.api.get_release(release.title)

    assert actual_release.url == release.html_url


def test_get_release_doesnt_exist(github):

    with pytest.raises(exceptions.ReleaseNotFoundException):
        github.api.get_release('doesnt-exist')


def test_close_issue_no_num(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.close_issue(num='', release='release')


def test_close_issue_no_release(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.close_issue(num=1, release='')


@pytest.mark.wet
def test_close_issue_issue_doesnt_exist(github, request):

    release = test_utils.create_release(github, request, LAST_COMMIT)

    with pytest.raises(exceptions.IssueNotFoundException):
        github.api.close_issue(num=100, release=release.title)


def test_close_issue_release_doesnt_exist(github):

    with pytest.raises(exceptions.ReleaseNotFoundException):
        github.api.close_issue(num=7, release='doesnt-exist')


@pytest.mark.wet
def test_close_issue(github, request):

    release = test_utils.create_release(github, request, LAST_COMMIT)

    github.api.close_issue(num=7, release=release.title)

    expected_status = 'closed'
    expected_comment = 'This issue is part of release [{}]({})'.format(
        release.title, release.html_url)

    issue = github.api.repo.get_issue(number=7)

    issue_comments = [comment.body for comment in issue.get_comments()]

    assert expected_status == issue.state
    assert expected_comment in issue_comments


def test_detect_issue_direct(github):

    issue = github.api.detect_issue(sha=conftest.LAST_COMMIT)

    expected_issue_number = 7

    assert expected_issue_number == issue.number

    issue = github.api.detect_issue(commit_message='Dummy commit linked to issue (#7)')

    assert expected_issue_number == issue.number


def test_detect_issue_via_pr(github):

    issue = github.api.detect_issue(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')

    expected_issue_number = 5

    assert expected_issue_number == issue.number

    issue = github.api.detect_issue(commit_message='Merged pull request (#10)')

    assert expected_issue_number == issue.number


def test_detect_issue_not_exists(github):

    with pytest.raises(exceptions.IssueNotFoundException):
        github.api.detect_issue(commit_message='Issue (#2500)')


def test_detect_issue_does_not_exist_via_pr(github):

    with pytest.raises(exceptions.IssueNotFoundException):
        github.api.detect_issue(commit_message='PR #9')


def test_detect_issue_no_issue(github):

    issue = github.api.detect_issue(commit_message='Commit message without issue ref')

    assert issue is None


def test_detect_issue_no_sha_no_commit_message(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.detect_issue()


def test_detect_issue_sha_and_commit_message(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.detect_issue(sha='sha', commit_message='message')


def test_create_release_no_sha_nor_branch(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.create_release(sha='', branch='')


def test_create_release_sha_and_branch(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.create_release(sha='branch', branch='branch')


def test_create_release_non_existing_commit(github):

    with pytest.raises(exceptions.CommitNotFoundException):
        github.api.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab89')


def test_create_release_not_python_project(github):

    sha = 'aee0c4c21d64f95f6742838aded957c2be71c2e5'
    with pytest.raises(exceptions.NotPythonProjectException):
        github.api.create_release(sha=sha)


@pytest.mark.wet
def test_create_release(github):

    sha = '1997dbd53731b5f51153bbae35bbab6fcc6dab81'
    rel = github.api.create_release(sha=sha)

    expected_release_title = '0.0.1'
    expected_release_sha = sha
    expected_release_url = 'https://github.com/iliapolo/pyci-guinea-pig/releases/tag/0.0.1'

    actual_release = github.api.repo.get_release(id='0.0.1')
    actual_release_title = actual_release.title
    actual_release_sha = github.api.repo.get_git_ref('tags/{}'.format(
        actual_release.tag_name)).object.sha
    actual_release_url = actual_release.html_url

    assert expected_release_title == actual_release_title
    assert expected_release_url == actual_release_url
    assert expected_release_sha == actual_release_sha

    assert expected_release_title == rel.title
    assert expected_release_url == rel.url


@pytest.mark.wet
def test_create_release_already_exists(github):

    sha = '1997dbd53731b5f51153bbae35bbab6fcc6dab81'
    github.api.create_release(sha=sha)

    with pytest.raises(exceptions.ReleaseAlreadyExistsException):
        github.api.create_release(sha=sha)


def test_set_version_no_value(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.set_version(value='')


def test_set_version_not_semantic(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.set_version(value='not-semantic')


def test_reset_branch_no_name(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.reset_branch(name='', sha='sha')


def test_reset_branch_no_sha(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.reset_branch(name='name', sha='')


def test_reset_branch_non_existing_branch(github):

    with pytest.raises(exceptions.BranchNotFoundException):
        github.api.reset_branch(name='doesnt-exist', sha='sha')


def test_reset_branch_non_existing_sha(github):

    with pytest.raises(exceptions.CommitNotFoundException):
        github.api.reset_branch(name='release', sha='e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1')


@pytest.mark.wet
def test_reset_branch(github):

    commit = github.api.create_commit(branch='release',
                                      path='README.md',
                                      contents='hello',
                                      message='message')

    github.api.reset_branch(name='release', sha=commit.sha)

    actual_sha = github.api.repo.get_branch(branch='release').commit.sha

    assert commit.sha == actual_sha


@pytest.mark.wet
def test_reset_branch_already_at_sha(github):

    with pytest.raises(exceptions.RefAlreadyAtShaException):
        github.api.reset_branch(name='release', sha=LAST_COMMIT)


@pytest.mark.wet
def test_reset_branch_hard(github):

    commit = github.api.create_commit(branch='release',
                                      path='README.md',
                                      contents='hello',
                                      message='message')

    github.api.reset_branch(name='release', sha=commit.sha, hard=True)

    actual_sha = github.api.repo.get_branch(branch='release').commit.sha

    assert commit.sha == actual_sha


@pytest.mark.wet
def test_reset_branch_not_fast_forward(github):

    with pytest.raises(exceptions.UpdateNotFastForwardException):
        github.api.reset_branch(name='release', sha='5b0aa87aac95cc24d24684f30daab44d2cc61d5d')

    branch = github.api.repo.get_branch(branch='release')

    assert branch.commit.sha == LAST_COMMIT


@pytest.mark.wet
def test_reset_branch_not_fast_forward_hard(github):

    expected_sha = '5b0aa87aac95cc24d24684f30daab44d2cc61d5d'

    github.api.reset_branch(name='release', sha=expected_sha, hard=True)

    branch = github.api.repo.get_branch(branch='release')

    assert branch.commit.sha == expected_sha


def test_reset_tag_no_name(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.reset_tag(name='', sha='sha')


def test_reset_tag_no_sha(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.reset_tag(name='name', sha='')


def test_reset_tag_non_existing_tag(github):

    with pytest.raises(exceptions.TagNotFoundException):
        github.api.reset_tag(name='doesnt-exist', sha='sha')


@pytest.mark.wet
def test_reset_tag_non_existing_sha(github, request):

    test_utils.create_release(github, request,
                              sha='aee0c4c21d64f95f6742838aded957c2be71c2e5',
                              name='0.0.1')
    with pytest.raises(exceptions.CommitNotFoundException):
        github.api.reset_tag(name='0.0.1', sha='e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1')


@pytest.mark.wet
def test_reset_tag(github, request):

    release_sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'

    test_utils.create_release(github, request, sha=release_sha, name='0.0.1')

    commit = github.api.create_commit(branch='release',
                                      path='README.md',
                                      contents='hello',
                                      message='message',
                                      sha=release_sha)

    github.api.reset_tag(name='0.0.1', sha=commit.sha)

    actual_sha = github.api.repo.get_git_ref('tags/0.0.1').object.sha

    assert commit.sha == actual_sha


@pytest.mark.wet
def test_reset_tag_already_at_sha(github, request):

    test_utils.create_release(github, request, sha=LAST_COMMIT, name='0.0.1')

    with pytest.raises(exceptions.RefAlreadyAtShaException):
        github.api.reset_tag(name='0.0.1', sha=LAST_COMMIT)


def test_create_branch_no_name(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.create_branch(sha='sha', name='')


def test_create_branch_no_sha(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.create_branch(sha='', name='name')


def test_create_branch_sha_doesnt_exist(github):

    with pytest.raises(exceptions.CommitNotFoundException):
        github.api.create_branch(sha='1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e', name='name')


@pytest.mark.wet
def test_create_branch(github, request):

    sha = 'e4f0041f7bac3a672db645377c720ff61ad2b22a'
    github.api.create_branch(sha=sha, name=request.node.name)

    branch = github.api.repo.get_git_ref('heads/{}'.format(request.node.name))

    assert sha == branch.object.sha


def test_create_branch_already_exists(github):

    sha = 'e4f0041f7bac3a672db645377c720ff61ad2b22a'
    with pytest.raises(exceptions.BranchAlreadyExistsException):
        github.api.create_branch(sha=sha, name='release')


def test_delete_branch_no_name(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.delete_branch(name='')


def test_delete_branch_doesnt_exist(github):

    with pytest.raises(exceptions.BranchNotFoundException):
        github.api.delete_branch(name='doesnt-exist')


@pytest.mark.wet
def test_delete_branch(github, request):

    branch = _create_branch(github, request, 'e4f0041f7bac3a672db645377c720ff61ad2b22a')

    branch_name = branch.ref.split('refs/heads/')[1]

    github.api.delete_branch(name=branch_name)

    with pytest.raises(UnknownObjectException):
        github.api.repo.get_git_ref(ref=branch.ref)


def test_commit_file_no_path(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.commit_file(path=None, contents='contents', message='message')


def test_commit_file_no_contents(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.commit_file(path='path', contents=None, message='message')


def test_commit_file_no_message(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.commit_file(path='path', contents='contents', message=None)


@pytest.mark.wet
def test_commit_file_branch_doesnt_exist(github, request):

    with pytest.raises(exceptions.BranchNotFoundException):
        github.api.commit_file(
            path='README.md',
            contents='contents',
            message=request.node.name,
            branch='doesnt-exist')


@pytest.mark.wet
def test_commit_file(github, request):

    contents = request.node.name
    commit = github.api.commit_file(
        path='README.md',
        contents=contents,
        message=request.node.name,
        branch='release')

    actual_commit = github.api.repo.get_commit(sha='release')

    expected_message = request.node.name

    readme = github.api.repo.get_contents(path='README.md', ref='heads/release').decoded_content

    if utils.is_python_3():
        readme = readme.decode()

    assert expected_message == actual_commit.commit.message
    assert contents == readme
    assert commit.sha == actual_commit.sha
    assert commit.url == actual_commit.html_url


def test_create_commit_no_path(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.create_commit(path=None, contents='contents', message='message')


def test_create_commit_no_contents(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.create_commit(path='path', contents=None, message='message')


def test_create_commit_no_message(github):

    with pytest.raises(exceptions.InvalidArgumentsException):
        github.api.create_commit(path='path', contents='contents', message=None)


def test_create_commit(github, request):

    commit = github.api.create_commit(
        path='README.md',
        contents=request.node.name,
        message=request.node.name,
        branch='release')

    actual_commit = github.api.repo.get_commit(sha=commit.sha)

    expected_message = request.node.name

    assert expected_message == actual_commit.commit.message
    assert commit.sha == actual_commit.sha
    assert commit.url == actual_commit.html_url
