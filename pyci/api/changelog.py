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

from pyci.api import utils


class Changelog(object):

    def __init__(self, features, bugs, internals, dangling_commits, current_version):
        self._current_version = current_version
        self._features = features
        self._bugs = bugs
        self._internals = internals
        self._dangling_commits = dangling_commits

    @property
    def features(self):
        return self._sort_issues(self._features or [])

    @property
    def bugs(self):
        return self._sort_issues(self._bugs or [])

    @property
    def internals(self):
        return self._sort_issues(self._internals or [])

    @property
    def dangling_commits(self):
        return self._sort_commits(self._dangling_commits or [])

    @property
    def issues(self):
        all_issues = []
        all_issues.extend(self.features)
        all_issues.extend(self.bugs)
        all_issues.extend(self.internals)
        return self._sort_issues(all_issues)

    @property
    def empty(self):
        return not (self.features or
                    self.bugs or
                    self.dangling_commits or
                    self.internals or
                    self.dangling_commits)

    @cachedproperty
    def next_version(self):

        result = self._current_version

        for issue in self._sort_issues(self.issues, reverse=False):
            label_names = [label.name for label in list(issue.get_labels())]
            result = utils.get_next_release(result, label_names)

        return None if result == self._current_version else result

    def add_dangling_commit(self, commit):
        self._dangling_commits.append(commit)
        self._dangling_commits = self._sort_commits(self._dangling_commits)

    def render(self):
        return utils.render_changelog(
            features=[self._issue_to_change(feature) for feature in self.features],
            bugs=[self._issue_to_change(bug) for bug in self.bugs],
            internals=[self._issue_to_change(internal) for internal in self.internals],
            dangling_commits=[self._commit_to_change(dangling_commit) for dangling_commit in
                              self.dangling_commits]
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
