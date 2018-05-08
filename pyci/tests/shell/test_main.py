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


def test_pack_sha_and_path(pyci, capture):

    pyci.run('pack --sha sha --path path --repo repo wheel', catch_exceptions=True)

    expected_output = 'Use either --sha or --path, not both'

    assert expected_output == capture.records[1].msg


def test_pack_not_sha_not_path(pyci, capture):

    pyci.run('pack --repo repo wheel', catch_exceptions=True)

    expected_output = 'Must specify either --sha or --path'

    assert expected_output == capture.records[1].msg


def test_github_no_repo(pyci, patched_github, capture):

    pyci.run('--no-ci github validate-commit', catch_exceptions=True)

    expected_output = 'Failed detecting repository name'

    expected_solution1 = 'Provide it using the --repo option'

    assert expected_output in capture.records[1].msg
    assert expected_solution1 in capture.records[1].msg
    patched_github.gh.validate_commit.assert_not_called()
