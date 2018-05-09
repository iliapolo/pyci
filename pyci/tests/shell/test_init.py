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

import pytest

try:
    # python2
    from mock import MagicMock
except ImportError:
    # noinspection PyUnresolvedReferences
    # python3
    from unittest.mock import MagicMock


def test_handle_unexpected_exception(patched_github, capture):

    exception = RuntimeError('error')

    patched_github.gh.validate_commit = MagicMock(side_effect=exception)

    with pytest.raises(SystemExit):
        patched_github.run('validate-commit --sha sha')

    expected_output = 'If you this message, it probably means you encountered a bug. ' \
                      'Please feel free to report it to https://github.com/iliapolo/pyci/issues'

    assert expected_output == capture.records[3].msg
