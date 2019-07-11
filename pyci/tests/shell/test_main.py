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


def test_pack_sha_and_path(pyci):

    result = pyci.run('pack --sha sha --path path --repo repo wheel', catch_exceptions=True)

    expected_output = 'Use either --sha or --path, not both'

    assert expected_output in result.std_out


def test_pack_repo_no_sha(pyci):

    result = pyci.run('--no-ci pack --repo repo wheel', catch_exceptions=True)

    expected_output = 'Must specify --sha as well'

    assert expected_output in result.std_out


def test_pack_repo_sha_path(pyci):

    result = pyci.run('pack --repo repo --sha sha --path path wheel', catch_exceptions=True)

    expected_output = 'Use either --sha or --path, not both'

    assert expected_output in result.std_out


def test_pack_no_repo(pyci):

    result = pyci.run('--no-ci pack wheel --help', catch_exceptions=True)

    expected_output = 'Failed detecting repository name'

    assert expected_output in result.std_out


def test_pack_target_dir_doesnt_exist(pyci):

    result = pyci.run('pack --repo repo --sha sha --target-dir doesnt-exist wheel --help', catch_exceptions=True)

    expected_output = 'Directory does not exist: doesnt-exist'

    assert expected_output in result.std_out


def test_pack_sha_doesnt_exist(pyci):

    result = pyci.run('pack --repo iliapolo/pyci --sha doesnt-exist wheel --help', catch_exceptions=True)

    expected_output = 'Not Found'

    assert expected_output in result.std_out


def test_github_no_repo(pyci):

    result = pyci.run('--no-ci github validate-commit --help', catch_exceptions=True)

    expected_output = 'Failed detecting repository name'

    assert expected_output in result.std_out
