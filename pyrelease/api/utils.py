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

import re


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
    p = re.compile('.* ?({0}) #(\d+)'.format(SUPPORTED_KEYWORDS))
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