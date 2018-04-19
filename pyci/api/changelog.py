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

from boltons.cacheutils import cachedproperty
from jinja2 import Template

from pyci.api import utils
from pyci.resources import get_resource


class Changelog(object):

    def __init__(self, current_version):
        self._current_version = current_version
        self.features = set()
        self.bugs = set()
        self.issues = set()
        self.dangling_commits = set()

    @property
    def all_issues(self):
        the_lot = []
        the_lot.extend(self.features)
        the_lot.extend(self.bugs)
        the_lot.extend(self.issues)
        return self._sort_issues(the_lot)

    @property
    def empty(self):
        return not (self.features or
                    self.bugs or
                    self.issues or
                    self.dangling_commits)

    @cachedproperty
    def next_version(self):

        result = self._current_version

        for issue in self._sort_issues(self.all_issues, reverse=False):
            label_names = [label.name for label in list(issue.get_labels())]
            result = utils.get_next_release(result, label_names)

        return None if result == self._current_version else result

    def add_feature(self, feature):
        self.features.add(feature)

    def add_bug(self, bug):
        self.bugs.add(bug)

    def add_issue(self, other_issue):
        self.issues.add(other_issue)

    def add_dangling_commit(self, commit):
        self.dangling_commits.add(commit)

    def render(self):

        features = {self._issue_to_change(feature) for feature in self._sort_issues(self.features)}
        bugs = {self._issue_to_change(bug) for bug in self._sort_issues(self.bugs)}
        issues = {self._issue_to_change(other_issue) for other_issue in self._sort_issues(
            self.issues)}
        dangling_commits = {self._commit_to_change(commit) for commit in self._sort_commits(
            self.dangling_commits)}

        return Template(get_resource('changelog.jinja')).render(
            features=features,
            bugs=bugs,
            issues=issues,
            dangling_commits=dangling_commits
        )

    @staticmethod
    def _issue_to_change(issue):
        return Change(title=issue.title, url=issue.html_url)

    @staticmethod
    def _commit_to_change(commit):
        return Change(title=commit.message, url=commit.html_url)

    @staticmethod
    def _sort_issues(issues, reverse=True):
        return sorted(issues, key=lambda issue: issue.created_at, reverse=reverse)

    @staticmethod
    def _sort_commits(commits, reverse=True):
        return sorted(commits, key=lambda commit: commit.author.date, reverse=reverse)


# pylint: disable=too-few-public-methods
class Change(object):

    def __init__(self, title, url):
        self.title = title
        self.url = url

    def __eq__(self, other):
        return other.url == self.url

    def __hash__(self):
        return hash(self.url)
