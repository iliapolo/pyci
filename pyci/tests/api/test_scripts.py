
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

import platform
import os

import pytest

from pyci.api import scripts
from pyci.api import exceptions


def test_virtualenv_valid(temp_dir):

    scripts.virtualenv.run(temp_dir)

    assert os.path.exists(_get_executable(temp_dir, 'python'))


def test_virtualenv_invalid(temp_dir):

    env_path = os.path.join(temp_dir, 'env')

    with open(env_path, 'w') as f:
        f.write('env')

    with pytest.raises(exceptions.ScriptInvocationException) as e:
        scripts.virtualenv.run(env_path)

    assert 'failed: 3' in str(e.value)


def _get_executable(name, exec_home):

    def _for_linux():

        return os.path.join(exec_home, 'bin', name)

    def _for_windows():

        exe = '{}.exe'.format(name)
        executable = os.path.join(exec_home, exe)
        if os.path.exists(executable):
            return executable
        scripts_directory = os.path.join(exec_home, 'scripts')
        return os.path.join(scripts_directory, exe)

    if platform.system().lower() == 'windows':
        executable_path = _for_windows()
    else:
        executable_path = _for_linux()
    return executable_path
