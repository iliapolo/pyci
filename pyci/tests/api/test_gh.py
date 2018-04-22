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
from github import Github, UnknownObjectException, GithubException

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api.gh import GitHubRepository

log = logger.get_logger(__name__)


logger.setup_loggers('DEBUG')


@pytest.fixture(name='github')
def _github():
    return Github(os.environ['GITHUB_ACCESS_TOKEN'])


# pylint: disable=too-many-nested-blocks,too-many-branches
@pytest.fixture(name='pyci_guinea_pig')
def _pyci_guinea_pig(request):

    guinea_pig = GitHubRepository(repo='iliapolo/pyci-guinea-pig',
                                  access_token=os.environ['GITHUB_ACCESS_TOKEN'])

    repo = Github(os.environ['GITHUB_ACCESS_TOKEN']).get_repo('iliapolo/pyci-guinea-pig')

    current_commit = None
    wet = None

    try:
        wet = getattr(request.node.function, 'wet')
    except AttributeError:
        pass

    if wet:
        # this test might will modify the state of the repository.
        # save the current commit so we can rollback.
        current_commit = repo.get_commit(sha='release')
        wet = getattr(request.node.function, 'wet')

    try:

        yield guinea_pig

    finally:

        if wet:

            if wet.kwargs.get('commits', True):
                log.info('Resetting release branch to original state...')
                ref = repo.get_git_ref('heads/release')
                ref.edit(sha=current_commit.sha, force=True)

            if wet.kwargs.get('releases', True):
                log.info('Deleting any releases...')
                for release in repo.get_releases():
                    release.delete_release()

            if wet.kwargs.get('tags', True):
                log.info('Deleting any tags...')
                for tag in repo.get_tags():
                    ref = repo.get_git_ref('tags/{}'.format(tag.name))
                    ref.delete()

            if wet.kwargs.get('branches', True):
                log.info('Deleting any additional branches...')
                for branch in repo.get_branches():
                    if branch.name not in ['master', 'release']:
                        ref = repo.get_git_ref('heads/{}'.format(branch.name))
                        ref.delete()

            if wet.kwargs.get('issues', True):
                log.info('Re-opening and cleaning all issues...')
                for issue in repo.get_issues(state='all'):
                    if not issue.pull_request:
                        issue.edit(state='open')
                        for comment in issue.get_comments():
                            comment.delete()


def _create_release(pyci_guinea_pig, request, sha, name=None):

    release_name = name or request.node.name

    return pyci_guinea_pig.repo.create_git_release(
        tag=release_name,
        target_commitish=sha,
        name=release_name,
        message=''
    )


def test_no_repo():

    with pytest.raises(exceptions.InvalidArgumentsException):
        GitHubRepository(repo='', access_token='token')


def test_no_access_token():

    with pytest.raises(exceptions.InvalidArgumentsException):
        GitHubRepository(repo='repo', access_token='')


def test_non_existing_repo():

    with pytest.raises(exceptions.RepositoryNotFoundException):
        _ = GitHubRepository(repo='iliapolo/doesnt-exist',
                             access_token=os.environ['GITHUB_ACCESS_TOKEN']).repo


def test_default_branch_name(pyci_guinea_pig):

    expected = 'release'

    actual = pyci_guinea_pig.default_branch_name

    assert expected == actual


@pytest.mark.wet(issues=False)
def test_last_release(pyci_guinea_pig, request):

    _create_release(pyci_guinea_pig, request, sha='aee0c4c21d64f95f6742838aded957c2be71c2e5')

    last_release = pyci_guinea_pig.last_release

    expected_last_release_title = request.node.name

    assert expected_last_release_title == last_release.title


def test_last_release_none(pyci_guinea_pig):

    last_release = pyci_guinea_pig.last_release

    assert last_release is None


def test_validate_commit_commit_not_related_to_issue(pyci_guinea_pig):

    with pytest.raises(exceptions.CommitNotRelatedToIssueException):
        pyci_guinea_pig.validate_commit(sha='aee0c4c21d64f95f6742838aded957c2be71c2e5')


def test_validate_commit_issue_is_not_labeled_as_release(pyci_guinea_pig):

    with pytest.raises(exceptions.IssueIsNotLabeledAsReleaseException):
        pyci_guinea_pig.validate_commit(sha='4772c5708ff25a69f1f6c8106c7fe863c6686459')


@pytest.mark.parametrize("sha", [
    'f7a59debfce6c2242eea5078fa0007b004ce3a57',  # patch issue
    '5b0aa87aac95cc24d24684f30daab44d2cc61d5d',  # minor issue
    'ee1e10067bda8200cc17ae7901c2d3f0fa0c7333'   # major issue
])
def test_validate_commit_via_issue(pyci_guinea_pig, sha):

    pyci_guinea_pig.validate_commit(sha=sha)


def test_validate_commit_via_pull_request(pyci_guinea_pig):

    pyci_guinea_pig.validate_commit(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')


def test_validate_commit_no_sha_nor_branch(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.validate_commit(sha='', branch='')


def test_validate_commit_sha_and_branch(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.validate_commit(sha='branch', branch='branch')


def test_generate_changelog_no_sha_nor_branch(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.generate_changelog(sha='', branch='')


def test_generate_changelog_sha_and_branch(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.generate_changelog(sha='branch', branch='branch')


def test_generate_changelog(pyci_guinea_pig):

    changelog = pyci_guinea_pig.generate_changelog(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698')

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


@pytest.mark.wet(issues=False)
def test_generate_changelog_empty(pyci_guinea_pig, request):

    _create_release(pyci_guinea_pig, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')

    changelog = pyci_guinea_pig.generate_changelog(sha='703afd5a11e186167606a071a556f30174f741d5')
    assert changelog.empty


def test_delete_release_no_name(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.delete_release(name='')


@pytest.mark.wet(issues=False)
def test_delete_release(pyci_guinea_pig, request):

    repo = pyci_guinea_pig.repo

    rel = _create_release(pyci_guinea_pig, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')

    pyci_guinea_pig.delete_release(name=rel.title)

    with pytest.raises(UnknownObjectException):
        repo.get_release(id=request.node.name)


def test_delete_non_existing_release(pyci_guinea_pig):

    with pytest.raises(exceptions.ReleaseNotFoundException):
        pyci_guinea_pig.delete_release(name='doesnt-exist')


def test_delete_tag_no_name(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.delete_tag(name='')


@pytest.mark.wet(issues=False)
def test_delete_tag(pyci_guinea_pig, request):

    repo = pyci_guinea_pig.repo

    rel = _create_release(pyci_guinea_pig, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    pyci_guinea_pig.delete_tag(name=rel.title)

    with pytest.raises(GithubException):
        repo.get_git_ref('tags/{0}'.format(request.node.name))


def test_delete_non_existing_tag(pyci_guinea_pig):

    with pytest.raises(exceptions.TagNotFoundException):
        pyci_guinea_pig.delete_tag(name='doesnt-exist')


def test_upload_asset_no_asset(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.upload_asset(asset='', release='release')


def test_upload_asset_no_release(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.upload_asset(asset='asset', release='')


def test_upload_asset_non_existing_release(request, temp_dir, pyci_guinea_pig):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    with pytest.raises(exceptions.ReleaseNotFoundException):
        pyci_guinea_pig.upload_asset(asset=asset, release='doesnt-exist')


@pytest.mark.wet(issues=False)
def test_upload_asset(pyci_guinea_pig, request, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    rel = _create_release(pyci_guinea_pig, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    pyci_guinea_pig.upload_asset(asset=asset, release=rel.title)

    repo = pyci_guinea_pig.repo
    assets = list(repo.get_release(id=rel.title).get_assets())

    expected_number_of_assets = 1

    assert expected_number_of_assets == len(assets)
    assert request.node.name == assets[0].name


@pytest.mark.wet(issues=False)
def test_upload_asset_already_exists(pyci_guinea_pig, request, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    rel = _create_release(pyci_guinea_pig, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6')
    pyci_guinea_pig.upload_asset(asset=asset, release=rel.title)
    with pytest.raises(exceptions.AssetAlreadyPublishedException):
        pyci_guinea_pig.upload_asset(asset=asset, release=rel.title)


@pytest.mark.wet(issues=False)
@pytest.mark.parametrize("semantic,expected_version", [
    ('patch', '0.0.3'),
    ('minor', '0.1.0'),
    ('major', '1.0.0')
])
def test_bump_version(runner, pyci_guinea_pig, semantic, expected_version):

    bump_commit = pyci_guinea_pig.bump_version(semantic=semantic)

    setup_py_path = utils.download(
        'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
        .format(bump_commit.sha))

    actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

    assert expected_version == actual_version


def test_bump_version_no_semantic(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.bump_version(semantic='')


def test_bump_version_semantic_illegal(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.bump_version(semantic='not-semantic')


@pytest.mark.wet(issues=False)
def test_set_version(runner, pyci_guinea_pig):

    bump_commit = pyci_guinea_pig.set_version(value='1.2.3')

    setup_py_path = utils.download(
        'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
        .format(bump_commit.sha))

    expected_version = '1.2.3'

    actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

    assert expected_version == actual_version


def test_set_version_same_version(pyci_guinea_pig):

    with pytest.raises(exceptions.TargetVersionEqualsCurrentVersionException):
        pyci_guinea_pig.set_version(value='0.0.2')


def test_detect_issue_direct(pyci_guinea_pig):

    issue = pyci_guinea_pig.detect_issue(sha='6536eefd0ec33141cc5c14be50a34631e8d79af8')

    expected_issue_number = 7

    assert expected_issue_number == issue.number

    issue = pyci_guinea_pig.detect_issue(commit_message='Dummy commit linked to issue (#7)')

    assert expected_issue_number == issue.number


def test_detect_issue_via_pr(pyci_guinea_pig):

    issue = pyci_guinea_pig.detect_issue(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')

    expected_issue_number = 5

    assert expected_issue_number == issue.number

    issue = pyci_guinea_pig.detect_issue(commit_message='Merged pull request (#10)')

    assert expected_issue_number == issue.number


def test_detect_issue_not_exists(pyci_guinea_pig):

    with pytest.raises(exceptions.IssueNotFoundException):
        pyci_guinea_pig.detect_issue(commit_message='Issue (#2500)')


def test_detect_issue_no_issue(pyci_guinea_pig):

    issue = pyci_guinea_pig.detect_issue(commit_message='Commit message without issue ref')

    assert issue is None


def test_detect_issue_no_sha_no_commit_message(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.detect_issue()


def test_detect_issue_sha_and_commit_message(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.detect_issue(sha='sha', commit_message='message')


def test_create_release_no_sha_nor_branch(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.create_release(sha='', branch='')


def test_create_release_sha_and_branch(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.create_release(sha='branch', branch='branch')


@pytest.mark.wet(issues=False)
def test_create_release_empty_changelog(pyci_guinea_pig, request):

    _create_release(pyci_guinea_pig, request,
                    sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81',
                    name='0.0.1')
    with pytest.raises(exceptions.EmptyChangelogException):
        pyci_guinea_pig.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')


@pytest.mark.wet(issues=False)
def test_create_release_commit_is_already_released(pyci_guinea_pig, request):

    _create_release(pyci_guinea_pig, request,
                    sha='a849e11c1ff2c5067347cf97adc159f221ef2237',
                    name='0.0.2')
    with pytest.raises(exceptions.CommitIsAlreadyReleasedException):
        pyci_guinea_pig.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')


def test_create_release_not_semantic_version(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81',
                                       version='not-semantic')


def test_create_release_non_existing_commit(pyci_guinea_pig):

    with pytest.raises(exceptions.CommitNotFoundException):
        pyci_guinea_pig.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab89',
                                       version='1.0.0')


@pytest.mark.wet(issues=False)
def test_create_existing_release_different_sha(pyci_guinea_pig, request):

    _create_release(pyci_guinea_pig, request,
                    sha='6536eefd0ec33141cc5c14be50a34631e8d79af8',
                    name='0.0.1')
    with pytest.raises(exceptions.ReleaseConflictException):
        pyci_guinea_pig.create_release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81',
                                       version='0.0.1')


@pytest.mark.wet(issues=False)
def test_create_release_cannot_determine_version(pyci_guinea_pig, request):

    _create_release(pyci_guinea_pig, request,
                    sha='6785ae160c9330ae8620730def90f1f32814adba',
                    name='0.0.2')
    with pytest.raises(exceptions.CannotDetermineNextVersionException):
        pyci_guinea_pig.create_release(sha='e4f0041f7bac3a672db645377c720ff61ad2b22a')


@pytest.mark.wet
def test_create_release_delete_pr_branch(pyci_guinea_pig):

    sha = '1997dbd53731b5f51153bbae35bbab6fcc6dab81'
    pyci_guinea_pig.create_branch(name='issue5', sha=sha)
    rel = pyci_guinea_pig.create_release(sha=sha)

    expected_release_changelog = rel.changelog.render()
    expected_release_title = '1.0.0'
    expected_release_sha = sha

    actual_release = pyci_guinea_pig.repo.get_release(id='1.0.0')
    actual_release_title = actual_release.title
    actual_release_sha = pyci_guinea_pig.repo.get_git_ref('tags/{}'.format(
        actual_release.tag_name)).object.sha
    actual_release_changelog = actual_release.body

    assert expected_release_title == actual_release_title
    assert expected_release_changelog == actual_release_changelog
    assert expected_release_sha == actual_release_sha


@pytest.mark.wet
def test_create_release_no_pr_branch(pyci_guinea_pig):

    sha = '1997dbd53731b5f51153bbae35bbab6fcc6dab81'
    rel = pyci_guinea_pig.create_release(sha=sha)

    expected_release_changelog = rel.changelog.render()
    expected_release_title = '1.0.0'
    expected_release_sha = sha

    actual_release = pyci_guinea_pig.repo.get_release(id='1.0.0')
    actual_release_title = actual_release.title
    actual_release_sha = pyci_guinea_pig.repo.get_git_ref('tags/{}'.format(
        actual_release.tag_name)).object.sha
    actual_release_changelog = actual_release.body

    assert expected_release_title == actual_release_title
    assert expected_release_changelog == actual_release_changelog
    assert expected_release_sha == actual_release_sha


def test_set_version_no_value(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.set_version(value='')


def test_set_version_not_semantic(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.set_version(value='not-semantic')


def test_reset_branch_no_name(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.reset_branch(name='', sha='sha')


def test_reset_branch_no_sha(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.reset_branch(name='name', sha='')


def test_reset_branch_non_existing_branch(pyci_guinea_pig):

    with pytest.raises(exceptions.BranchNotFoundException):
        pyci_guinea_pig.reset_branch(name='doesnt-exist', sha='sha')


def test_reset_branch_non_existing_sha(pyci_guinea_pig):

    with pytest.raises(exceptions.ShaNotFoundException):
        pyci_guinea_pig.reset_branch(name='release',
                                     sha='e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1')


@pytest.mark.wet(issues=False)
def test_reset_branch(pyci_guinea_pig):

    expected_sha = '6536eefd0ec33141cc5c14be50a34631e8d79af8'

    pyci_guinea_pig.reset_branch(name='release', sha=expected_sha)

    actual_sha = pyci_guinea_pig.repo.get_commit(sha='release').sha

    assert expected_sha == actual_sha


def test_reset_tag_no_name(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.reset_tag(name='', sha='sha')


def test_reset_tag_no_sha(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.reset_tag(name='name', sha='')


def test_reset_tag_non_existing_tag(pyci_guinea_pig):

    with pytest.raises(exceptions.TagNotFoundException):
        pyci_guinea_pig.reset_tag(name='doesnt-exist', sha='sha')


@pytest.mark.wet(issues=False)
def test_reset_tag_non_existing_sha(pyci_guinea_pig, request):

    _create_release(pyci_guinea_pig, request,
                    sha='aee0c4c21d64f95f6742838aded957c2be71c2e5',
                    name='0.0.1')
    with pytest.raises(exceptions.ShaNotFoundException):
        pyci_guinea_pig.reset_tag(name='0.0.1', sha='e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1')


@pytest.mark.wet(issues=False)
def test_reset_tag(pyci_guinea_pig, request):

    expected_sha = 'aee0c4c21d64f95f6742838aded957c2be71c2e5'

    _create_release(pyci_guinea_pig, request,
                    sha='33526a9e0445541d96e027db2aeb93d07cdf8bd6',
                    name='0.0.1')
    pyci_guinea_pig.reset_tag(name='0.0.1', sha=expected_sha)

    actual_sha = pyci_guinea_pig.repo.get_git_ref('tags/0.0.1').object.sha

    assert expected_sha == actual_sha


def test_create_branch_no_name(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.create_branch(sha='sha', name='')


def test_create_branch_no_sha(pyci_guinea_pig):

    with pytest.raises(exceptions.InvalidArgumentsException):
        pyci_guinea_pig.create_branch(sha='', name='name')


def test_create_branch_sha_doesnt_exist(pyci_guinea_pig):

    with pytest.raises(exceptions.ShaNotFoundException):
        pyci_guinea_pig.create_branch(sha='1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e', name='name')


def test_create_branch(request, pyci_guinea_pig):

    sha = 'e4f0041f7bac3a672db645377c720ff61ad2b22a'
    pyci_guinea_pig.create_branch(sha=sha, name=request.node.name)

    branch = pyci_guinea_pig.repo.get_git_ref('heads/{}'.format(request.node.name))

    assert sha == branch.object.sha
