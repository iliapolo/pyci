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

import semver
from boltons.cacheutils import cachedproperty
from jinja2 import Template

from pyci.api import logger
from pyci.api import exceptions
from pyci.resources import get_text_resource


# pylint: disable=too-few-public-methods
class Branch(object):

    def __init__(self, impl, sha, name):
        self.sha = sha
        self.impl = impl
        self.name = name


# pylint: disable=too-few-public-methods
class Bump(object):

    def __init__(self, impl, prev_version, next_version, sha):
        self.sha = sha
        self.prev_version = prev_version
        self.next_version = next_version
        self.impl = impl


# pylint: disable=too-few-public-methods
class Commit(object):

    def __init__(self, impl, sha, url):
        self.impl = impl
        self.sha = sha
        self.url = url


# pylint: disable=too-few-public-methods
class Issue(object):

    def __init__(self, impl, number, url):
        self.url = url
        self.impl = impl
        self.number = number


# pylint: disable=too-few-public-methods
class Release(object):

    def __init__(self, impl, title, url, sha):
        self.sha = sha
        self.url = url
        self.title = title
        self.impl = impl


class Changelog(object):

    """
    Represents a changelog of a certain commit from the last release.
    Note that it does not actually calculate the changelog, but is merely a convenient container
    for the calculation result.

    To generate a changelog, see gh.GitHub.changelog()

    A Changelog is comprised of the following components:

        - Features: These are issues who introduce a new feature to the system.

        - Bugs: These are issues who fix a bug in the system..

        - Issues: These are general issues (i.e not bugs or features)

        - Commits: These are commits not related to any issue.

    The class is instantiated with all the components being empty. Adding various components
    is done using the 'add' method.

    For example, to add a minor bug:

        changelog = Changelog(sha='sha', current_version='1.0.0')
        minor_bug = ChangelogIssue(title='Nasty bug',
                                   url='https://iliapolo/pyci/issues/4',
                                   timestamp=14234987234,
                                   kind_modifier=ChangelogIssue.BUG,
                                   version_modifier=ChangelogIssue.MINOR)
        changelog.add(minor_bug)

    Once you finish populating the instance, you can generate a Markdown file using
    the 'render()' method:

        md = changelog.render()

    Args:
        current_version (str): What is the current version of the project. Must be a semantic
            string version.
        sha (str): What is the commit sha this changelog is generated for.
    """

    def __init__(self, sha, current_version):

        if not sha:
            raise exceptions.InvalidArgumentsException('sha cannot be empty')

        if not current_version:
            raise exceptions.InvalidArgumentsException('current_version cannot be empty')

        try:
            semver.parse(current_version)
        except (TypeError, ValueError):
            raise exceptions.InvalidArgumentsException('Version is not a legal semantic '
                                                       'version string')

        self._current_version = current_version
        self._sha = sha
        self._logger = logger.Logger(__name__)
        self._log_ctx = {
            'sha': self.sha,
            'current_version': self._current_version
        }

        self.features = set()
        self.bugs = set()
        self.issues = set()
        self.commits = set()

    @property
    def sha(self):
        return self._sha

    @property
    def all_issues(self):

        """
        Returns:
            list: A list containing all issues associated with this changelog. Regardless of
                their kind.
        """

        the_lot = []
        the_lot.extend(self.features)
        the_lot.extend(self.bugs)
        the_lot.extend(self.issues)
        return self._sort(the_lot)

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
                    self.commits)

    @cachedproperty
    def next_version(self):

        """
        Based on the changelog, calculate what the next version would be. This is done by iterating
        over all issues in order and incrementing the version number according to each issue
        version modifier.

        Returns:
             str: The semantic version string
        """

        result = self._current_version

        self._debug('Determining next version...')

        for issue in self._sort(self.all_issues, reverse=False):

            if issue.version_modifier == ChangelogIssue.PATCH:
                result = semver.bump_patch(result)

            if issue.version_modifier == ChangelogIssue.MINOR:
                result = semver.bump_minor(result)

            if issue.version_modifier == ChangelogIssue.MAJOR:
                result = semver.bump_major(result)

            self._debug('Applied issue on incremental result.', issue_title=issue.title,
                        result=result, version_modifier=issue.version_modifier)

        result = None if result == self._current_version else result

        self._debug('Determined next version.', next_version=result)

        return result

    def add(self, change):

        """
        Add a change to this changelog. Based on the kind_modifier of the change, this will add it
        to the appropriate collection, which can later be retrieved.

        Args:
            change (:ChangelogIssue:ChangelogCommit): Either a commit or an issue.
        """

        if not isinstance(change, (ChangelogCommit, ChangelogIssue)):
            raise exceptions.InvalidArgumentsException('change must be of type '
                                                       '`pyci.api.changelog.ChangelogCommit` or '
                                                       '`pyci.api.changelog.ChangelogIssue`')

        if isinstance(change, ChangelogIssue):
            if change.kind_modifier == ChangelogIssue.FEATURE:
                self.features.add(change)
            if change.kind_modifier == ChangelogIssue.BUG:
                self.bugs.add(change)
            if change.kind_modifier == ChangelogIssue.ISSUE:
                self.issues.add(change)

        if isinstance(change, ChangelogCommit):
            self.commits.add(change)

    def render(self):

        """
        Render a MarkDown file from the current changelog.
        All issues and commits are sorted by its timestamp. That is, commits/issues
        appearing at the top of the file are the most recent ones.

        Returns:
            str: The md string representing the changelog instance.
        """

        kw = {
            'features': self._sort(self.features),
            'bugs': self._sort(self.bugs),
            'issues': self._sort(self.issues),
            'commits': self._sort(self.commits)
        }

        self._debug('Rendering changelog markdown file')
        markdown = Template(get_text_resource('changelog.jinja')).render(**kw)
        self._debug('Rendered markdown')
        return markdown

    @staticmethod
    def _sort(changes, reverse=True):
        return sorted(changes, key=lambda change: change.timestamp, reverse=reverse)

    def _debug(self, message, **kwargs):
        kwargs = copy.deepcopy(kwargs)
        kwargs.update(self._log_ctx)
        self._logger.debug(message, **kwargs)


class _Change(object):

    def __init__(self, title, url, timestamp):

        if not title:
            raise exceptions.InvalidArgumentsException('title cannot be empty')

        if not url:
            raise exceptions.InvalidArgumentsException('url cannot be empty')

        if not timestamp:
            raise exceptions.InvalidArgumentsException('timestamp cannot be empty')

        self.timestamp = timestamp
        self.title = title
        self.url = url

    def __eq__(self, other):
        return other.url == self.url

    def __hash__(self):
        return hash(self.url)


class ChangelogIssue(_Change):

    """
    Represents a change that originated from an Issue.

    Args:
        - kind_modifier (str): What kind is this issue (bug, feature..)
        - version_modifier (str): What is the version severity of this issue (patch, minor...)
        - impl (obj): The internal implementation of the issue.
    """

    FEATURE = 'feature'
    BUG = 'bug'
    ISSUE = 'issue'
    PATCH = 'patch'
    MINOR = 'minor'
    MAJOR = 'major'

    SEMANTIC_VERSION_LABELS = [PATCH, MINOR, MAJOR]
    TYPE_LABELS = [FEATURE, BUG, ISSUE]

    def __init__(self, title, url, timestamp, kind=ISSUE, semantic=None, impl=None):
        super(ChangelogIssue, self).__init__(title, url, timestamp)
        self.kind_modifier = kind
        self.version_modifier = semantic
        self.impl = impl


class ChangelogCommit(_Change):

    """
    Represents a change that originated from a commit not related to any issue.

    Args:
        - impl (obj): The internal implementation of the issue.
    """

    def __init__(self, title, url, timestamp, impl=None):
        super(ChangelogCommit, self).__init__(title, url, timestamp)
        self.impl = impl
