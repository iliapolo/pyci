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

import copy
from boltons.cacheutils import cachedproperty
from jinja2 import Template

from pyci.api import utils
from pyci.resources import get_resource
from pyci.api import exceptions
from pyci.api import logger


log = logger.get_logger(__name__)


class Changelog(object):

    """
    Represents a changelog of a certain commit from the last release.
    Note that it does not actually calculate the changelog, but is merely a convenient container
    for the calculation result.

    A Changelog is comprised of the following components:

        - Features: These are issues labeled with the 'feature' label.

        - Bugs: These are issues labeled with the 'bug' label.

        - Issues: These are general issues (i.e not bugs or features)

        - Dangling Commits: These are commits not related to any issue.

    The class is instantiated with all the components being empty. Adding various components
    is done using the appropriate 'add' method.

    For example, to add a bug:

        changelog = Changelog(current_version='1.0.0')
        changelog.add_bug(issue_describing_bug)

    Once you finish populating the instance, you can generate a Markdown file using
    the 'render()' method:

        md = changelog.render()

    Args:
        current_version (str): What is the current version of the project.
        sha (str): What is the commit sha this changelog is generated for.
    """

    def __init__(self, sha, current_version):

        if not sha:
            raise exceptions.InvalidArgumentsException('sha cannot be None')

        if not current_version:
            raise exceptions.InvalidArgumentsException('current_version cannot be None')

        self._current_version = current_version
        self.sha = sha
        self.features = set()
        self.bugs = set()
        self.issues = set()
        self.dangling_commits = set()
        self._log_ctx = {
            'sha': self.sha,
            'current_version': self._current_version
        }

    @property
    def all_issues(self):

        """
        Returns:
            list: A list containing all issues associated with this changelog. Regardless of
                their label.
        """

        the_lot = []
        the_lot.extend(self.features)
        the_lot.extend(self.bugs)
        the_lot.extend(self.issues)
        return the_lot

    @property
    def empty(self):

        """
        Returns:
             bool: True if the changelog is empty (i.e does not contain any commits nor issues),
                False otherwise
        """

        return not (self.features or
                    self.bugs or
                    self.issues or
                    self.dangling_commits)

    @cachedproperty
    def next_version(self):

        """
        Based on the changelog, calculate what the next version would be. This is done by iterating
        over all issues in order of creation and incrementing the version number according
        to each issue labels.

        Returns:
             str: The semantic version string
        """

        result = self._current_version

        self._debug('Determining next version...')

        for issue in self._sort_issues(self.all_issues, reverse=False):
            label_names = [label.name for label in list(issue.get_labels())]
            self._debug('Applying issue on incremental result.', issue=issue.number, result=result)
            result = utils.bump_version(result, label_names)
            self._debug('Applied issue on incremental result.', issue=issue.number, result=result)

        result = None if result == self._current_version else result

        self._debug('Determined next version.', next_version=result)

        return result

    def add_feature(self, feature):

        """
        Add a feature to this changelog.

        Args:
            feature (github.Issue): The feature to add.
        """

        self.features.add(feature)

    def add_bug(self, bug):

        """
        Add a bug to this changelog.

        Args:
            bug (github.Issue): The bug to add.
        """

        self.bugs.add(bug)

    def add_issue(self, issue):

        """
        Add an issue to this changelog.

        Args:
            issue (github.Issue): The issue to add.
        """

        self.issues.add(issue)

    def add_dangling_commit(self, commit):

        """
        Add a dangling commit to this changelog.

        Args:
            commit (github.Commit): The commit to add.
        """

        self.dangling_commits.add(commit)

    def render(self):

        """
        Render a well formatted MarkDown file from the current changelog.
        All issues and commits are sorted by creation/commit date. That is, commits/issues
        appearing at the top of the file are the most recent ones.

        Returns:
            str: The md string representing the changelog instance.
        """

        features = {self._issue_to_change(feature) for feature in self._sort_issues(self.features)}
        bugs = {self._issue_to_change(bug) for bug in self._sort_issues(self.bugs)}
        issues = {self._issue_to_change(other_issue) for other_issue in self._sort_issues(
            self.issues)}
        dangling_commits = {self._commit_to_change(commit) for commit in self._sort_commits(
            self.dangling_commits)}

        kw = {
            'features': features,
            'bugs': bugs,
            'issues': issues,
            'dangling_commits': dangling_commits
        }

        self._debug('Rendering changelog markdown file', **kw)
        markdown = Template(get_resource('changelog.jinja')).render(**kw)
        self._debug('Rendered markdown', changelog=markdown, **kw)
        return markdown

    def _issue_to_change(self, issue):
        self._debug('Transforming issue to Change', issue=issue.number)
        change = Change(title=issue.title, url=issue.html_url)
        self._debug('Transformed issue to Change', issue=issue.number, change=change)
        return change

    def _commit_to_change(self, commit):
        self._debug('Transforming commit to Change', commit=commit.sha)
        change = Change(title=commit.message, url=commit.html_url)
        self._debug('Transformed commit to Change', sha=commit.sha, change=change)
        return change

    @staticmethod
    def _sort_issues(issues, reverse=True):
        return sorted(issues, key=lambda issue: issue.created_at, reverse=reverse)

    @staticmethod
    def _sort_commits(commits, reverse=True):
        return sorted(commits, key=lambda commit: commit.author.date, reverse=reverse)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        log.debug(message, **kwargs)


# pylint: disable=too-few-public-methods
class Change(object):

    def __init__(self, title, url):
        self.title = title
        self.url = url

    def __eq__(self, other):
        return other.url == self.url

    def __hash__(self):
        return hash(self.url)

    def __str__(self):
        return 'Change[title={}, url={}]'.format(self.title, self.url)
