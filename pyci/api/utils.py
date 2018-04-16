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

from pyci.api import exceptions
from pyci.resources import get_resource
from pyci.api.runner import LocalCommandRunner


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


def get_href(commit_message):

    # pylint: disable=anomalous-backslash-in-string
    p = re.compile('.* ?#(\d+)')
    match = p.match(commit_message)
    if match:
        return int(match.group(1))

    return None


def get_next_release(last_release, labels):

    next_release = last_release

    if 'patch' in labels:
        next_release = semver.bump_patch(last_release)

    if 'minor' in labels:
        next_release = semver.bump_minor(last_release)

    if 'major' in labels:
        next_release = semver.bump_major(last_release)

    return next_release


def render_changelog(**kwargs):
    return Template(get_resource('changelog.jinja')).render(**kwargs)


def lsf(directory):

    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]


def lsd(directory):

    return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]


def smkdir(directory):

    if not os.path.exists(directory):
        os.makedirs(directory)


def get_local_repo():

    runner = LocalCommandRunner()
    try:
        result = runner.run('git remote -v')
        return parse_repo(result.std_out.splitlines()[0])
    except exceptions.CommandExecutionException:
        return None


def parse_repo(remote_url):
    try:
        return remote_url.split(' ')[0].split('.git')[0].split('.com')[1][1:]
    except IndexError:
        return None


def validate_file_exists(path):

    if not os.path.exists(path):
        raise exceptions.FileDoesntExistException(path=path)
    if os.path.isdir(path):
        raise exceptions.FileIsADirectoryException(path=path)


def validate_does_not_exist(path):

    if os.path.isfile(path):
        raise exceptions.FileExistException(path=path)
    if os.path.isdir(path):
        raise exceptions.FileIsADirectoryException(path=path)
