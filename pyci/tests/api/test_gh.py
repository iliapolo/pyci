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

import contextlib
import os

# noinspection PyPackageRequirements
import pytest
# noinspection PyPackageRequirements
from github import Github, UnknownObjectException, GithubException

from pyci.api import exceptions
from pyci.api import utils
from pyci.api import logger
from pyci.api.gh import GitHub


logger.setup_loggers('DEBUG')


@pytest.fixture(name='github')
def _github():
    return Github(os.environ['GITHUB_ACCESS_TOKEN'])


@pytest.fixture(name='pyci_guinea_pig')
def _pyci_guinea_pig():
    return GitHub(repo='iliapolo/pyci-guinea-pig', access_token=os.environ['GITHUB_ACCESS_TOKEN'])


@contextlib.contextmanager
def release(github, request, sha):

    def _delete_release():

        try:
            rel.delete_release()
        except UnknownObjectException:
            pass

        try:
            tag = repo.get_git_ref('tags/{0}'.format(request.node.name))
            tag.delete()
        except GithubException:
            pass

    repo = github.get_repo('iliapolo/pyci-guinea-pig')

    rel = repo.create_git_release(
        tag=request.node.name,
        target_commitish=sha,
        name=request.node.name,
        message=''
    )

    yield rel

    _delete_release()


@contextlib.contextmanager
def commit(pyci_guinea_pig):

    repo = pyci_guinea_pig.repo

    current_commit = repo.get_commit(sha='release')

    yield

    ref = repo.get_git_ref('heads/release')
    ref.edit(sha=current_commit.sha, force=True)


def test_default_branch_name(pyci_guinea_pig):

    expected = 'release'

    actual = pyci_guinea_pig.default_branch_name

    assert expected == actual


def test_last_release(request, github, pyci_guinea_pig):

    with release(github, request, sha='aee0c4c21d64f95f6742838aded957c2be71c2e5'):

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


def test_generate_changelog_empty(request, github, pyci_guinea_pig):

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6'):
        changelog = pyci_guinea_pig.generate_changelog(
            sha='703afd5a11e186167606a071a556f30174f741d5')
        assert changelog.empty


def test_delete_release(request, github, pyci_guinea_pig):

    repo = github.get_repo('iliapolo/pyci-guinea-pig')

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6') as rel:
        pyci_guinea_pig.delete_release(release=rel.title)

        with pytest.raises(UnknownObjectException):
            repo.get_release(id=request.node.name)


def test_delete_tag(request, github, pyci_guinea_pig):

    repo = github.get_repo('iliapolo/pyci-guinea-pig')

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6') as rel:
        pyci_guinea_pig.delete_tag(tag=rel.title)

        with pytest.raises(GithubException):
            repo.get_git_ref('tags/{0}'.format(request.node.name))


def test_upload_asset(request, github, pyci_guinea_pig, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6') as rel:
        pyci_guinea_pig.upload_asset(asset=asset, release=rel.title)

        repo = github.get_repo('iliapolo/pyci-guinea-pig')
        assets = list(repo.get_release(id=rel.title).get_assets())

        expected_number_of_assets = 1

        assert expected_number_of_assets == len(assets)
        assert request.node.name == assets[0].name


def test_upload_asset_already_exists(request, github, pyci_guinea_pig, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6') as rel:
        pyci_guinea_pig.upload_asset(asset=asset, release=rel.title)
        with pytest.raises(exceptions.AssetAlreadyPublishedException):
            new = GitHub(repo='iliapolo/pyci-guinea-pig', access_token=os.environ[
                'GITHUB_ACCESS_TOKEN'])
            new.upload_asset(asset=asset, release=rel.title)


def test_bump_version_patch(runner, pyci_guinea_pig):

    with commit(pyci_guinea_pig):
        bump_commit = pyci_guinea_pig.bump_version(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                                   version_modifier='patch')

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '0.0.2'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_version_minor(runner, pyci_guinea_pig):

    with commit(pyci_guinea_pig):
        bump_commit = pyci_guinea_pig.bump_version(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                                   version_modifier='minor')

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '0.1.0'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_version_major(runner, pyci_guinea_pig):

    with commit(pyci_guinea_pig):
        bump_commit = pyci_guinea_pig.bump_version(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                                   version_modifier='major')

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '1.0.0'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_version_version(runner, pyci_guinea_pig):

    with commit(pyci_guinea_pig):
        bump_commit = pyci_guinea_pig.bump_version(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                                   version='1.2.3')

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '1.2.3'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_version_same_version(pyci_guinea_pig):

    with commit(pyci_guinea_pig):
        bump_commit = pyci_guinea_pig.bump_version(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                                   version='0.0.1')
        assert bump_commit is None


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


def test_create_release(pyci_guinea_pig):

    with commit(pyci_guinea_pig):

        rel = None
        try:

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

        finally:
            if rel:
                pyci_guinea_pig.delete_release(release=rel.title)
                pyci_guinea_pig.delete_tag(tag=rel.title)
                for issue in rel.changelog.all_issues:
                    issue.impl.edit(state='open')
