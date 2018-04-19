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

import pytest
from github import Github, UnknownObjectException, GithubException

from pyci.api import exceptions
from pyci.api import utils
from pyci.api import logger
from pyci.api.gh import GitHub
from pyci.api.gh import BUMP_COMMIT_MESSAGE_FORMAT


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

    try:
        rel = repo.get_release(id=request.node.name)
        _delete_release()
    except UnknownObjectException:
        pass

    rel = repo.create_git_release(
        tag=request.node.name,
        target_commitish=sha,
        name=request.node.name,
        message=''
    )

    yield rel

    _delete_release()


@contextlib.contextmanager
def commit(github):

    repo = github.get_repo('iliapolo/pyci-guinea-pig')
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


def test_validate_commit_not_related_to_issue(pyci_guinea_pig):

    with pytest.raises(exceptions.CommitNotRelatedToIssueException):
        pyci_guinea_pig.validate(sha='aee0c4c21d64f95f6742838aded957c2be71c2e5')


def test_validate_issue_is_not_labeled_as_release(pyci_guinea_pig):

    with pytest.raises(exceptions.IssueIsNotLabeledAsReleaseException):
        pyci_guinea_pig.validate(sha='4772c5708ff25a69f1f6c8106c7fe863c6686459')


@pytest.mark.parametrize("sha", [
    'f7a59debfce6c2242eea5078fa0007b004ce3a57',  # patch issue
    '5b0aa87aac95cc24d24684f30daab44d2cc61d5d',  # minor issue
    'ee1e10067bda8200cc17ae7901c2d3f0fa0c7333'   # major issue
])
def test_validate_via_issue(pyci_guinea_pig, sha):

    pyci_guinea_pig.validate(sha=sha)


def test_validate_via_pull_request(pyci_guinea_pig):

    pyci_guinea_pig.validate(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')


def test_changelog(pyci_guinea_pig):

    changelog = pyci_guinea_pig.changelog(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698')

    expected_features = {7, 6}
    expected_bugs = {5}
    expected_issues = {1}
    expected_dangling_commits = {
        '33526a9e0445541d96e027db2aeb93d07cdf8bd6',
        '703afd5a11e186167606a071a556f30174f741d5',
        '6cadc14419e57549365ac4dabea59c4c08be581c',
        '0596d82b4786a531b7370448e2b5d0de9922f01a',
        'b22803b93eaca693db78f9d551ec295946765135',
        '3ee89f04a8a2b71d06aa80c5178943e7b396be47',
        'aee0c4c21d64f95f6742838aded957c2be71c2e5'
    }
    expected_next_version = '1.0.0'

    actual_features = {feature.number for feature in changelog.features}
    actual_bugs = {bug.number for bug in changelog.bugs}
    actual_issues = {issue.number for issue in changelog.issues}
    actual_dangling_commits = {com.sha for com in changelog.dangling_commits}
    actual_next_version = changelog.next_version

    assert expected_features == actual_features
    assert expected_bugs == actual_bugs
    assert expected_issues == actual_issues
    assert expected_dangling_commits == actual_dangling_commits
    assert expected_next_version == actual_next_version


def test_changelog_empty(request, github, pyci_guinea_pig):

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6'):
        changelog = pyci_guinea_pig.changelog(sha='703afd5a11e186167606a071a556f30174f741d5')
        assert changelog.empty


def test_delete(request, github, pyci_guinea_pig):

    repo = github.get_repo('iliapolo/pyci-guinea-pig')

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6') as rel:
        pyci_guinea_pig.delete(release=rel.title)

        with pytest.raises(UnknownObjectException):
            repo.get_release(id=request.node.name)
        with pytest.raises(GithubException):
            repo.get_git_ref('tags/{0}'.format(request.node.name))


def test_upload(request, github, pyci_guinea_pig, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6') as rel:
        pyci_guinea_pig.upload(asset=asset, release=rel.title)

        repo = github.get_repo('iliapolo/pyci-guinea-pig')
        assets = list(repo.get_release(id=rel.title).get_assets())

        assert 1 == len(assets)
        assert request.node.name == assets[0].name


def test_upload_already_exists(request, github, pyci_guinea_pig, temp_dir):

    asset = os.path.join(temp_dir, request.node.name)

    with open(asset, 'w') as stream:
        stream.write('Hello')

    with release(github, request, '33526a9e0445541d96e027db2aeb93d07cdf8bd6') as rel:
        pyci_guinea_pig.upload(asset=asset, release=rel.title)
        with pytest.raises(exceptions.AssetAlreadyPublishedException):
            new = GitHub(repo='iliapolo/pyci-guinea-pig', access_token=os.environ[
                'GITHUB_ACCESS_TOKEN'])
            new.upload(asset=asset, release=rel.title)


def test_bump_patch(runner, github, pyci_guinea_pig):

    with commit(github):
        bump_commit = pyci_guinea_pig.bump(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                           patch=True)

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '0.0.2'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_minor(runner, github, pyci_guinea_pig):

    with commit(github):
        bump_commit = pyci_guinea_pig.bump(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                           minor=True)

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '0.1.0'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_major(runner, github, pyci_guinea_pig):

    with commit(github):
        bump_commit = pyci_guinea_pig.bump(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                           major=True)

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '1.0.0'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_version(runner, github, pyci_guinea_pig):

    with commit(github):
        bump_commit = pyci_guinea_pig.bump(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                           version='1.2.3')

        setup_py_path = utils.download(
            'https://raw.githubusercontent.com/iliapolo/pyci-guinea-pig/{0}/setup.py'
            .format(bump_commit.sha))

        expected_version = '1.2.3'

        actual_version = runner.run('python {0} --version'.format(setup_py_path)).std_out

        assert expected_version == actual_version


def test_bump_same_version(github, pyci_guinea_pig):

    with commit(github):
        bump_commit = pyci_guinea_pig.bump(sha='2b38a0386f9b3cc50de9095a38f3fb82301e2698',
                                           version='0.0.1')
        assert bump_commit is None


def test_issue_direct(pyci_guinea_pig):

    issue = pyci_guinea_pig.issue(sha='6536eefd0ec33141cc5c14be50a34631e8d79af8')

    assert 7 == issue.number

    issue = pyci_guinea_pig.issue(commit_message='Dummy commit linked to issue (#7)')

    assert 7 == issue.number


def test_issue_via_pr(pyci_guinea_pig):

    issue = pyci_guinea_pig.issue(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')

    assert 5 == issue.number

    issue = pyci_guinea_pig.issue(commit_message='Merged pull request (#10)')

    assert 5 == issue.number


def test_issue_not_exists(pyci_guinea_pig):

    with pytest.raises(exceptions.IssueNotFoundException):
        pyci_guinea_pig.issue(commit_message='Issue (#2500)')


def test_issue_no_issue(pyci_guinea_pig):

    issue = pyci_guinea_pig.issue(commit_message='Commit message without issue ref')

    assert issue is None


def test_issue_no_sha_no_commit_message(pyci_guinea_pig):

    with pytest.raises(AssertionError):
        pyci_guinea_pig.issue()


def test_issue_sha_and_commit_message(pyci_guinea_pig):

    with pytest.raises(AssertionError):
        pyci_guinea_pig.issue(sha='sha', commit_message='message')


def test_release(github, pyci_guinea_pig):

    with commit(github):

        release_title = None
        changelog = None
        try:
            release_title = pyci_guinea_pig.release(sha='1997dbd53731b5f51153bbae35bbab6fcc6dab81')

            repo = github.get_repo('iliapolo/pyci-guinea-pig')

            rel = repo.get_release(id=release_title)

            last_commit_on_release = repo.get_commit(sha='release')
            last_commit_on_master = repo.get_commit(sha='master')

            expected_commit_message = BUMP_COMMIT_MESSAGE_FORMAT.format(
                '1.0.0',
                '1997dbd53731b5f51153bbae35bbab6fcc6dab81')
            expected_release_title = '1.0.0'
            changelog = pyci_guinea_pig.changelog(sha=last_commit_on_release.sha)
            expected_release_body = changelog.render()

            assert expected_release_title == rel.title
            assert expected_commit_message == last_commit_on_release.commit.message
            assert expected_release_body == rel.body
            assert last_commit_on_release.sha == last_commit_on_master.sha

        finally:
            if release_title:
                pyci_guinea_pig.delete(release=release_title)
            if changelog:
                for issue in changelog.all_issues:
                    issue.edit(state='open')



