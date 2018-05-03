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
import logging
import os

# noinspection PyPackageRequirements
import pytest
# noinspection PyPackageRequirements
from github import UnknownObjectException, GithubException, GitRelease

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api.gh import GitHubRepository
from pyci.api.model import Changelog, ChangelogIssue
from pyci.shell import secrets


log = logger.get_logger(__name__)


logger.setup_loggers(logging.DEBUG)


CURRENT_VERSION = '0.0.1'


def _create_release(gh, request, sha, name=None):

    release_name = name or request.node.name

    return gh.repo.create_git_release(
        tag=release_name,
        target_commitish=sha,
        name=release_name,
        message=''
    )


def _create_branch(gh, request, sha, name=None):

    branch_name = name or request.node.name

    return gh.repo.create_git_ref(ref='refs/heads/{}'.format(branch_name), sha=sha)


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


def test_default_branch_name(gh):

    expected = 'release'

    actual = gh.default_branch_name

    assert expected == actual


@pytest.mark.wet(issues=False)
def test_last_release(gh, request):

    _create_release(gh, request, sha='aee0c4c21d64f95f6742838aded957c2be71c2e5')

    last_release = gh.last_release

    expected_last_release_title = request.node.name

    assert expected_last_release_title == last_release.title


def test_last_release_none(gh):

    last_release = gh.last_release

    assert last_release is None


def test_validate_commit_commit_not_related_to_issue(gh):

    with pytest.raises(exceptions.CommitNotRelatedToIssueException):
        gh.validate_commit(sha='aee0c4c21d64f95f6742838aded957c2be71c2e5')


def test_validate_commit_issue_is_not_labeled_as_release(gh):

    with pytest.raises(exceptions.IssueNotLabeledAsReleaseException):
        gh.validate_commit(sha='4772c5708ff25a69f1f6c8106c7fe863c6686459')


@pytest.mark.parametrize("sha", [
    'f7a59debfce6c2242eea5078fa0007b004ce3a57',  # patch issue
    '5b0aa87aac95cc24d24684f30daab44d2cc61d5d',  # minor issue
    'ee1e10067bda8200cc17ae7901c2d3f0fa0c7333'   # major issue
])
def test_validate_commit_via_issue(gh, sha):

    gh.validate_commit(sha=sha)


def test_validate_commit_via_pull_request(gh):

    gh.validate_commit(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')


def test_validate_commit_no_sha_nor_branch(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.validate_commit(sha='', branch='')


def test_validate_commit_sha_and_branch(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.validate_commit(sha='branch', branch='branch')


def test_generate_changelog_no_sha_nor_branch(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.generate_changelog(sha='', branch='')


def test_generate_changelog_sha_and_branch(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.generate_changelog(sha='branch', branch='branch')


# pylint: disable=too-many-locals
@pytest.mark.wet(issues=False)
def test_generate_changelog_relative_to_release(gh, request):

    # create two releases from commits prior to our one
    _create_release(gh, request, '0596d82b4786a531b7370448e2b5d0de9922f01a', '0.0.1')
    _create_release(gh, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6', '0.0.2')

    # this is our commit
    ours = gh.set_version(value='0.0.3')

    # create two releases for commits after ours
    after1 = gh.set_version(value='0.0.4')
    after2 = gh.set_version(value='0.0.5')

    _create_release(gh, request, after1.sha, '0.0.4')
    _create_release(gh, request, after2.sha, '0.0.5')

    # this should give us the changelog relative to the 0.0.2 release, not the latest.
    changelog = gh.generate_changelog(sha=ours.sha)

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


def test_generate_changelog_no_release(gh):

    changelog = gh.generate_changelog(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')

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


def test_upload_changelog_no_changelog(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.upload_changelog(changelog='', release='0.0.1')


def test_upload_changelog_no_release(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.upload_changelog(changelog='changelog', release='')


def test_upload_changelog_non_existing_release(gh):

    with pytest.raises(exceptions.ReleaseNotFoundException):
        gh.upload_changelog(changelog='changelog', release='doesnt-exist')


@pytest.mark.wet(issues=False)
def test_upload_changelog(gh, request):

    expected_sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'
    expected_title = '0.0.1'

    _create_release(gh, request, expected_sha, expected_title)

    changelog = Changelog(sha=expected_sha, current_version='0.0.1')

    changelog.add(ChangelogIssue(title='title',
                                 url='url',
                                 timestamp=100,
                                 kind=ChangelogIssue.FEATURE,
                                 semantic=ChangelogIssue.MINOR))

    release = gh.upload_changelog(changelog=changelog.render(), release='0.0.1')

    github_release = gh.repo.get_release(id='0.0.1')

    expected_changelog_entry = 'title ([Issue](url))'

    assert expected_sha == release.sha
    assert expected_title == release.title
    assert github_release.html_url == release.url
    assert isinstance(release.impl, GitRelease.GitRelease)

    assert expected_changelog_entry in github_release.body


@pytest.mark.wet(issues=False)
def test_generate_changelog_empty(gh, request):

    expected_sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'
    expected_release = '0.0.1'

    _create_release(gh, request, expected_sha, expected_release)

    with pytest.raises(exceptions.EmptyChangelogException) as e:
        gh.generate_changelog(sha=expected_sha)

    assert expected_sha == e.value.sha
    assert expected_release == e.value.previous_release


def test_delete_release_no_name(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.delete_release(name='')


@pytest.mark.wet(issues=False)
def test_delete_release(gh, request):

    repo = gh.repo

    rel = _create_release(gh, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')

    gh.delete_release(name=rel.title)

    with pytest.raises(UnknownObjectException):
        repo.get_release(id=request.node.name)


def test_delete_non_existing_release(gh):

    with pytest.raises(exceptions.ReleaseNotFoundException):
        gh.delete_release(name='doesnt-exist')


def test_delete_tag_no_name(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.delete_tag(name='')


@pytest.mark.wet(issues=False)
def test_delete_tag(gh, request):

    repo = gh.repo

    rel = _create_release(gh, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    gh.delete_tag(name=rel.title)

    with pytest.raises(GithubException):
        repo.get_git_ref('tags/{0}'.format(request.node.name))


def test_delete_non_existing_tag(gh):

    with pytest.raises(exceptions.TagNotFoundException):
        gh.delete_tag(name='doesnt-exist')


def test_upload_asset_no_asset(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.upload_asset(asset='', release='release')


def test_upload_asset_no_release(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.upload_asset(asset='asset', release='')


def test_upload_asset_non_existing_release(request, temp_dir, gh):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    with pytest.raises(exceptions.ReleaseNotFoundException):
        gh.upload_asset(asset=asset, release='doesnt-exist')


@pytest.mark.wet(issues=False)
def test_upload_asset(gh, request, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    rel = _create_release(gh, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    gh.upload_asset(asset=asset, release=rel.title)

    repo = gh.repo
    assets = list(repo.get_release(id=rel.title).get_assets())

    expected_number_of_assets = 1

    assert expected_number_of_assets == len(assets)
    assert request.node.name == assets[0].name


@pytest.mark.wet(issues=False)
def test_upload_asset_already_exists(gh, request, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    rel = _create_release(gh, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    gh.upload_asset(asset=asset, release=rel.title)
    with pytest.raises(exceptions.AssetAlreadyPublishedException):
        gh.upload_asset(asset=asset, release=rel.title)


@pytest.mark.wet(issues=False)
@pytest.mark.parametrize("semantic,expected_version", [
    ('patch', '0.0.2'),
    ('minor', '0.1.0'),
    ('major', '1.0.0')
])
def test_bump_version(runner, gh, semantic, expected_version):

    bump = gh.bump_version(semantic=semantic)

    setup_py_path = utils.download(
        'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
        .format(bump.sha))

    actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

    assert expected_version == actual_version
    assert expected_version == bump.next_version
    assert CURRENT_VERSION == bump.prev_version


def test_bump_version_no_semantic(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.bump_version(semantic='')


def test_bump_version_semantic_illegal(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.bump_version(semantic='not-semantic')


@pytest.mark.wet(issues=False)
def test_set_version(runner, gh):

    bump = gh.set_version(value='1.2.3')

    setup_py_path = utils.download(
        'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
        .format(bump.sha))

    expected_version = '1.2.3'

    actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

    assert expected_version == actual_version
    assert expected_version == bump.next_version
    assert CURRENT_VERSION == bump.prev_version


@pytest.mark.wet(issues=False)
def test_set_version_same_version(gh):

    with pytest.raises(exceptions.TargetVersionEqualsCurrentVersionException):
        gh.set_version(value=CURRENT_VERSION)


def test_detect_issue_direct(gh):

    issue = gh.detect_issue(sha='6536eefd0ec33141cc5c14be50a34631e8d79af8')

    expected_issue_number = 7

    assert expected_issue_number == issue.number

    issue = gh.detect_issue(commit_message='Dummy commit linked to issue (#7)')

    assert expected_issue_number == issue.number


def test_detect_issue_via_pr(gh):

    issue = gh.detect_issue(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')

    expected_issue_number = 5

    assert expected_issue_number == issue.number

    issue = gh.detect_issue(commit_message='Merged pull request (#10)')

    assert expected_issue_number == issue.number


def test_detect_issue_not_exists(gh):

    with pytest.raises(exceptions.IssueNotFoundException):
        gh.detect_issue(commit_message='Issue (#2500)')


def test_detect_issue_does_not_exist_via_pr(gh):

    with pytest.raises(exceptions.IssueNotFoundException):
        gh.detect_issue(commit_message='PR #9')


def test_detect_issue_no_issue(gh):

    issue = gh.detect_issue(commit_message='Commit message without issue ref')

    assert issue is None


def test_detect_issue_no_sha_no_commit_message(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.detect_issue()


def test_detect_issue_sha_and_commit_message(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.detect_issue(sha='sha', commit_message='message')


def test_create_release_no_sha_nor_branch(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.create_release(sha='', branch='')


def test_create_release_sha_and_branch(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.create_release(sha='branch', branch='branch')


@pytest.mark.wet(issues=False)
def test_create_release_commit_is_already_released(gh, request):

    _create_release(gh, request,
                    sha='a849e11c1ff2c5067347cf97adc159f221ef2237',
                    name='0.0.2')
    with pytest.raises(exceptions.CommitIsAlreadyReleasedException):
        gh.create_release(sha='a849e11c1ff2c5067347cf97adc159f221ef2237')


def test_create_release_non_existing_commit(gh):

    with pytest.raises(exceptions.CommitNotFoundException):
        gh.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab89')


def test_create_release_not_python_project(gh):

    sha = 'aee0c4c21d64f95f6742838aded957c2be71c2e5'
    with pytest.raises(exceptions.NotPythonProjectException):
        gh.create_release(sha=sha)


@pytest.mark.wet(issues=False)
def test_create_release_release_conflict(gh, request):

    _create_release(gh, request,
                    sha='6536eefd0ec33141cc5c14be50a34631e8d79af8',
                    name='0.0.1')
    with pytest.raises(exceptions.ReleaseConflictException):
        gh.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')


@pytest.mark.wet
def test_create_release(gh):

    sha = '1997dbd53731b5f51153bbae35bbab6fcc6dab81'
    rel = gh.create_release(sha=sha)

    expected_release_title = '0.0.1'
    expected_release_sha = sha
    expected_release_url = 'https://github.com/iliapolo/pyci-guinea-pig/releases/tag/0.0.1'

    actual_release = gh.repo.get_release(id='0.0.1')
    actual_release_title = actual_release.title
    actual_release_sha = gh.repo.get_git_ref('tags/{}'.format(
        actual_release.tag_name)).object.sha
    actual_release_url = actual_release.html_url

    assert expected_release_title == actual_release_title
    assert expected_release_url == actual_release_url
    assert expected_release_sha == actual_release_sha

    assert expected_release_title == rel.title
    assert expected_release_url == rel.url


def test_set_version_no_value(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.set_version(value='')


def test_set_version_not_semantic(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.set_version(value='not-semantic')


def test_reset_branch_no_name(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.reset_branch(name='', sha='sha')


def test_reset_branch_no_sha(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.reset_branch(name='name', sha='')


def test_reset_branch_non_existing_branch(gh):

    with pytest.raises(exceptions.BranchNotFoundException):
        gh.reset_branch(name='doesnt-exist', sha='sha')


def test_reset_branch_non_existing_sha(gh):

    with pytest.raises(exceptions.ShaNotFoundException):
        gh.reset_branch(name='release', sha='e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1')


@pytest.mark.wet(issues=False)
def test_reset_branch(gh):

    expected_sha = '6536eefd0ec33141cc5c14be50a34631e8d79af8'

    gh.reset_branch(name='release', sha=expected_sha)

    actual_sha = gh.repo.get_commit(sha='release').sha

    assert expected_sha == actual_sha


def test_reset_tag_no_name(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.reset_tag(name='', sha='sha')


def test_reset_tag_no_sha(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.reset_tag(name='name', sha='')


def test_reset_tag_non_existing_tag(gh):

    with pytest.raises(exceptions.TagNotFoundException):
        gh.reset_tag(name='doesnt-exist', sha='sha')


@pytest.mark.wet(issues=False)
def test_reset_tag_non_existing_sha(gh, request):

    _create_release(gh, request,
                    sha='aee0c4c21d64f95f6742838aded957c2be71c2e5',
                    name='0.0.1')
    with pytest.raises(exceptions.ShaNotFoundException):
        gh.reset_tag(name='0.0.1', sha='e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1')


@pytest.mark.wet(issues=False)
def test_reset_tag(gh, request):

    expected_sha = 'aee0c4c21d64f95f6742838aded957c2be71c2e5'

    _create_release(gh, request,
                    sha='33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                    name='0.0.1')
    gh.reset_tag(name='0.0.1', sha=expected_sha)

    actual_sha = gh.repo.get_git_ref('tags/0.0.1').object.sha

    assert expected_sha == actual_sha


def test_create_branch_no_name(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.create_branch(sha='sha', name='')


def test_create_branch_no_sha(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.create_branch(sha='', name='name')


def test_create_branch_sha_doesnt_exist(gh):

    with pytest.raises(exceptions.ShaNotFoundException):
        gh.create_branch(sha='1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e', name='name')


@pytest.mark.wet(issues=False)
def test_create_branch(request, gh):

    sha = 'e4f0041f7bac3a672db645377c720ff61ad2b22a'
    gh.create_branch(sha=sha, name=request.node.name)

    branch = gh.repo.get_git_ref('heads/{}'.format(request.node.name))

    assert sha == branch.object.sha


def test_create_branch_already_exists(gh):

    sha = 'e4f0041f7bac3a672db645377c720ff61ad2b22a'
    with pytest.raises(exceptions.BranchAlreadyExistsException):
        gh.create_branch(sha=sha, name='release')


def test_delete_branch_no_name(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.delete_branch(name='')


def test_delete_branch_doesnt_exist(gh):

    with pytest.raises(exceptions.BranchNotFoundException):
        gh.delete_branch(name='doesnt-exist')


@pytest.mark.wet(issues=False)
def test_delete_branch(gh, request):

    branch = _create_branch(gh, request, 'e4f0041f7bac3a672db645377c720ff61ad2b22a')

    branch_name = branch.ref.split('refs/heads/')[1]

    gh.delete_branch(name=branch_name)

    with pytest.raises(UnknownObjectException):
        gh.repo.get_git_ref(ref=branch.ref)


def test_commit_file_no_path(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.commit_file(path=None, contents='contents', message='message')


def test_commit_file_no_contents(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.commit_file(path='path', contents=None, message='message')


def test_commit_file_no_message(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.commit_file(path='path', contents='contents', message=None)


@pytest.mark.wet(issues=False)
def test_commit_file(gh, request):

    commit = gh.commit_file(
        path='README.md',
        contents=request.node.name,
        message=request.node.name,
        branch='release')

    actual_commit = gh.repo.get_commit(sha='release')

    expected_message = request.node.name

    assert expected_message == actual_commit.commit.message

    # pylint: disable=fixme
    # TODO figure out why this doesn't work...(open a bug in the meantime)
    # readme_url = 'https://raw.githubusercontent.com/{}/release/README.md'.format(
    #     gh.repo.full_name)
    # readme_file = utils.download(readme_url)
    # with open(readme_file) as stream:
    #     actual_readme_content = stream.read()
    # expected_content = request.node.name
    # assert expected_content == actual_readme_content

    assert commit.sha == actual_commit.sha
    assert commit.url == actual_commit.html_url


def test_create_commit_no_path(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.create_commit(path=None, contents='contents', message='message')


def test_create_commit_no_contents(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.create_commit(path='path', contents=None, message='message')


def test_create_commit_no_message(gh):

    with pytest.raises(exceptions.InvalidArgumentsException):
        gh.create_commit(path='path', contents='contents', message=None)


@pytest.mark.wet(issues=False)
def test_create_commit(gh, request):

    commit = gh.create_commit(
        path='README.md',
        contents=request.node.name,
        message=request.node.name,
        branch='release')

    actual_commit = gh.repo.get_commit(sha=commit.sha)

    expected_message = request.node.name

    assert expected_message == actual_commit.commit.message
    assert commit.sha == actual_commit.sha
    assert commit.url == actual_commit.html_url
