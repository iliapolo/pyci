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
import re

import semver
from jinja2 import Template

from pyci.resources import get_resource


# see https://help.github.com/articles/closing-issues-using-keywords/
SUPPORTED_KEYWORDS = [

    'close',
    'closes',
    'closed',
    'fix',
    'fixes',
    'fixed',
    'resolve',
    'resolves',
    'resolved'

]


def get_issue_number(pr_body):

    # pylint: disable=anomalous-backslash-in-string
    p = re.compile('.* ?({0}) #(\d+)'.format('|'.join(SUPPORTED_KEYWORDS)))
    match = p.match(pr_body)

    if match:
        return match.group(2)

    return None


def get_pull_request_number(commit_message):

    # pylint: disable=anomalous-backslash-in-string
    p = re.compile('.* ?\(#(\d+)\)')
    match = p.match(commit_message)
    if match:
        return int(match.group(1))

    return None


def get_latest_release(releases):

    if not releases:
        return None

    semver.bump_patch()

    versions = [release.title for release in releases]

    return sorted(versions, cmp=lambda t1, t2: semver.compare(t2, t1))[0]


def get_next_release(last_release, labels):

    if last_release is None:
        return '0.0.1'

    next_release = None

    if 'patch' in labels:
        next_release = semver.bump_patch(last_release)

    if 'minor' in labels:
        next_release = semver.bump_minor(last_release)

    if 'major' in labels:
        next_release = semver.bump_major(last_release)

    return next_release if next_release != last_release else None


def render_changelog(features, bugs, internals):
    return Template(get_resource('changelog.jinja')).render(features=features,
                                                            bugs=bugs,
                                                            internals=internals)


def lsf(directory):

    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


def lsd(directory):

    return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]


def smkdir(directory):

    if not os.path.exists(directory):
        os.makedirs(directory)
