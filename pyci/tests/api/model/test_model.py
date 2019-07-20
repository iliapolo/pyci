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

import pytest

from pyci.api import exceptions
from pyci.api.model import model


class TestChangelogIssue(object):

    @staticmethod
    def test_no_title():
        with pytest.raises(exceptions.InvalidArgumentsException):
            model.ChangelogIssue(title='', url='url', timestamp=100)

    @staticmethod
    def test_no_url():
        with pytest.raises(exceptions.InvalidArgumentsException):
            model.ChangelogIssue(title='title', url='', timestamp=100)

    @staticmethod
    def test_no_timestamp():
        with pytest.raises(exceptions.InvalidArgumentsException):
            model.ChangelogIssue(title='title', url='url', timestamp=None)


class TestChangelogCommit(object):

    @staticmethod
    def test_no_title():
        with pytest.raises(exceptions.InvalidArgumentsException):
            model.ChangelogCommit(title='', url='url', timestamp=100)

    @staticmethod
    def test_no_url():
        with pytest.raises(exceptions.InvalidArgumentsException):
            model.ChangelogCommit(title='title', url='', timestamp=100)

    @staticmethod
    def test_no_timestamp():
        with pytest.raises(exceptions.InvalidArgumentsException):
            model.ChangelogCommit(title='title', url='url', timestamp=None)


# pylint: disable=too-many-public-methods
class TestChangelog(object):

    @staticmethod
    def test_no_sha():

        with pytest.raises(exceptions.InvalidArgumentsException):
            model.Changelog(sha='', current_version='0.0.1')

    @staticmethod
    def test_no_current_version():

        with pytest.raises(exceptions.InvalidArgumentsException):
            model.Changelog(sha='sha', current_version='')

    @staticmethod
    def test_current_version_not_semantic():

        with pytest.raises(exceptions.InvalidArgumentsException):
            model.Changelog(sha='sha', current_version='123')

    @staticmethod
    def test_empty():

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        assert changelog.empty

    @staticmethod
    def test_add_invalid_type():

        changelog = model.Changelog(sha='sha', current_version='0.0.1')
        with pytest.raises(exceptions.InvalidArgumentsException):
            changelog.add({})

    @staticmethod
    def test_add_feature(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        feature = model.ChangelogIssue(title=request.node.name,
                                       url='url',
                                       timestamp=121234,
                                       kind=model.ChangelogIssue.FEATURE)

        changelog.add(feature)

        expected_feature_title = request.node.name
        expected_number_of_features = 1

        assert expected_number_of_features == len(changelog.features)
        assert expected_feature_title == changelog.features.pop().title
        assert not changelog.bugs
        assert not changelog.issues
        assert not changelog.commits

    @staticmethod
    def test_add_bug(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        bug = model.ChangelogIssue(title=request.node.name,
                                   url='url',
                                   timestamp=121234,
                                   kind=model.ChangelogIssue.BUG)

        changelog.add(bug)

        expected_bug_title = request.node.name
        expected_number_of_bugs = 1

        assert expected_number_of_bugs == len(changelog.bugs)
        assert expected_bug_title == changelog.bugs.pop().title
        assert not changelog.features
        assert not changelog.issues
        assert not changelog.commits

    @staticmethod
    def test_add_issue(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        bug = model.ChangelogIssue(title=request.node.name,
                                   url='url',
                                   timestamp=121234,
                                   kind=model.ChangelogIssue.ISSUE)

        changelog.add(bug)

        expected_issue_title = request.node.name
        expected_number_of_issues = 1

        assert expected_number_of_issues == len(changelog.issues)
        assert expected_issue_title == changelog.issues.pop().title
        assert not changelog.features
        assert not changelog.bugs
        assert not changelog.commits

    @staticmethod
    def test_add_commit(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        commit = model.ChangelogCommit(title=request.node.name,
                                       url='url',
                                       timestamp=121234)

        changelog.add(commit)

        expected_commit_title = request.node.name
        expected_number_of_commits = 1

        assert expected_number_of_commits == len(changelog.commits)
        assert expected_commit_title == changelog.commits.pop().title
        assert not changelog.features
        assert not changelog.bugs
        assert not changelog.issues

    @staticmethod
    def test_not_empty_features(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        feature = model.ChangelogIssue(title=request.node.name,
                                       url='url',
                                       timestamp=121234,
                                       kind=model.ChangelogIssue.FEATURE)

        changelog.add(feature)

        assert not changelog.empty

    @staticmethod
    def test_not_empty_bugs(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        bug = model.ChangelogIssue(title=request.node.name,
                                   url='url',
                                   timestamp=121234,
                                   kind=model.ChangelogIssue.BUG)

        changelog.add(bug)

        assert not changelog.empty

    @staticmethod
    def test_not_empty_issues(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        issue = model.ChangelogIssue(title=request.node.name,
                                     url='url',
                                     timestamp=121234,
                                     kind=model.ChangelogIssue.ISSUE)

        changelog.add(issue)

        assert not changelog.empty

    @staticmethod
    def test_not_empty_commits(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        commit = model.ChangelogCommit(title=request.node.name,
                                       url='url',
                                       timestamp=121234)

        changelog.add(commit)

        assert not changelog.empty

    @staticmethod
    def test_add_identical_features():

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        feature1 = model.ChangelogIssue(title='feature',
                                        url='url',
                                        timestamp=100,
                                        kind=model.ChangelogIssue.FEATURE)

        feature2 = model.ChangelogIssue(title='feature',
                                        url='url',
                                        timestamp=100,
                                        kind=model.ChangelogIssue.FEATURE)

        changelog.add(feature1)
        changelog.add(feature2)

        expected_number_of_features = 1

        assert expected_number_of_features == len(changelog.features)

    @staticmethod
    def test_add_identical_bugs():

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        bug1 = model.ChangelogIssue(title='bug',
                                    url='url',
                                    timestamp=100,
                                    kind=model.ChangelogIssue.BUG)

        bug2 = model.ChangelogIssue(title='bug',
                                    url='url',
                                    timestamp=100,
                                    kind=model.ChangelogIssue.BUG)

        changelog.add(bug1)
        changelog.add(bug2)

        expected_number_of_bugs = 1

        assert expected_number_of_bugs == len(changelog.bugs)

    @staticmethod
    def test_add_identical_issues():

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        issue1 = model.ChangelogIssue(title='issue',
                                      url='url',
                                      timestamp=100,
                                      kind=model.ChangelogIssue.ISSUE)

        issue2 = model.ChangelogIssue(title='issue',
                                      url='url',
                                      timestamp=100,
                                      kind=model.ChangelogIssue.ISSUE)

        changelog.add(issue1)
        changelog.add(issue2)

        expected_number_of_issues = 1

        assert expected_number_of_issues == len(changelog.issues)

    @staticmethod
    def test_add_identical_commits():

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        commit1 = model.ChangelogCommit(title='commit',
                                        url='url',
                                        timestamp=100)

        commit2 = model.ChangelogIssue(title='commit',
                                       url='url',
                                       timestamp=100)

        changelog.add(commit1)
        changelog.add(commit2)

        expected_number_of_commits = 1

        assert expected_number_of_commits == len(changelog.commits)

    @staticmethod
    def test_next_version():

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        patch_issue = model.ChangelogIssue(title='patch issue',
                                           url='url1',
                                           timestamp=100,
                                           semantic=model.ChangelogIssue.PATCH)

        minor_issue = model.ChangelogIssue(title='minor issue',
                                           url='url2',
                                           timestamp=50,
                                           semantic=model.ChangelogIssue.MINOR)

        major_issue = model.ChangelogIssue(title='major issue',
                                           url='url3',
                                           timestamp=10,
                                           semantic=model.ChangelogIssue.MAJOR)

        changelog.add(patch_issue)
        changelog.add(minor_issue)
        changelog.add(major_issue)

        expected_version = '1.1.1'

        assert expected_version == changelog.next_version

    @staticmethod
    def test_next_version_none(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        non_release_issue = model.ChangelogIssue(title=request.node.name,
                                                 url='url',
                                                 timestamp=123123)
        changelog.add(non_release_issue)

        expected_version = None

        assert expected_version == changelog.next_version

    @staticmethod
    def test_render_only_issues(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        issue = model.ChangelogIssue(title=request.node.name,
                                     url='url',
                                     timestamp=121234,
                                     kind=model.ChangelogIssue.ISSUE)

        changelog.add(issue)

        expected = """*Changes*






**Issues:**


- {} ([Issue](url))



""".format(request.node.name)

        actual = changelog.render()

        assert expected == actual

    @staticmethod
    def test_render_only_bugs(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        bug = model.ChangelogIssue(title=request.node.name,
                                   url='url',
                                   timestamp=121234,
                                   kind=model.ChangelogIssue.BUG)

        changelog.add(bug)

        expected = """*Changes*




**Bug Fixes:**


- {} ([Issue](url))





""".format(request.node.name)

        actual = changelog.render()

        assert expected == actual

    @staticmethod
    def test_render_only_features(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        feature = model.ChangelogIssue(title=request.node.name,
                                       url='url',
                                       timestamp=121234,
                                       kind=model.ChangelogIssue.FEATURE)

        changelog.add(feature)

        expected = """*Changes*


**New Features:**


- {} ([Issue](url))







""".format(request.node.name)

        actual = changelog.render()

        assert expected == actual

    @staticmethod
    def test_render_only_commits(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        commit = model.ChangelogCommit(title=request.node.name,
                                       url='url',
                                       timestamp=121234)

        changelog.add(commit)

        expected = """*Changes*








**Dangling Commits:**


- {} ([Commit](url))

""".format(request.node.name)

        actual = changelog.render()

        assert expected == actual

    @staticmethod
    def test_render_all(request):

        changelog = model.Changelog(sha='sha', current_version='0.0.1')

        commit = model.ChangelogCommit(title=request.node.name,
                                       url='url',
                                       timestamp=121234)

        bug = model.ChangelogIssue(title=request.node.name,
                                   url='url',
                                   timestamp=121234,
                                   kind=model.ChangelogIssue.FEATURE)

        issue = model.ChangelogIssue(title=request.node.name,
                                     url='url',
                                     timestamp=121234,
                                     kind=model.ChangelogIssue.ISSUE)

        feature = model.ChangelogIssue(title=request.node.name,
                                       url='url',
                                       timestamp=121234,
                                       kind=model.ChangelogIssue.FEATURE)

        changelog.add(commit)
        changelog.add(bug)
        changelog.add(issue)
        changelog.add(feature)

        expected = """*Changes*


**New Features:**


- {0} ([Issue](url))






**Issues:**


- {0} ([Issue](url))




**Dangling Commits:**


- {0} ([Commit](url))

""".format(request.node.name)

        actual = changelog.render()

        assert expected == actual
