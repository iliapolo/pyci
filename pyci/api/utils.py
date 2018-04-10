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
# see https://help.github.com/articles/closing-issues-using-keywords/
from jinja2 import Template

from pyci.resources import get_resource

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

    versions = [release.title for release in releases]

    return sorted(versions, cmp=lambda t1, t2: semver.compare(t2, t1))[0]


def get_next_release(last_release, labels):

    if last_release is None:
        return '0.0.1'

    label_names = [label.name for label in labels]

    semantic_version = last_release.split('.')

    micro = int(semantic_version[2])
    minor = int(semantic_version[1])
    major = int(semantic_version[0])

    if 'micro' in label_names:
        micro = micro + 1

    if 'minor' in label_names:
        micro = 0
        minor = minor + 1

    if 'major' in label_names:
        micro = 0
        minor = 0
        major = major + 1

    return '{0}.{1}.{2}'.format(major, minor, micro)


def render_changelog(features, bugs):
    return Template(get_resource('changelog.jinja')).render(features=features, bugs=bugs)


def lsf(directory):

    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


def lsd(directory):

    return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]


def smkdir(directory):

    if not os.path.exists(directory):
        os.makedirs(directory)
