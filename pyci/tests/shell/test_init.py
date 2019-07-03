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

from pyci.shell import handle_exceptions
from pyci.shell.exceptions import TerminationException


def test_handle_unexpected_exception():

    @handle_exceptions
    def command():
        raise RuntimeError('error')

    with pytest.raises(TerminationException) as e:
        command()

    assert 'If you see this message, you probably encountered a bug' in str(e.value)
