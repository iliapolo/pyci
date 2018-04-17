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
import shutil
import tempfile

import pytest

from pyci.api.runner import LocalCommandRunner


@pytest.fixture()
def temp_file():

    file_path = tempfile.mkstemp()[1]

    yield file_path

    # cleanup
    os.remove(file_path)


@pytest.fixture()
def temp_dir():

    dir_path = tempfile.mkdtemp()

    yield dir_path

    # cleanup
    shutil.rmtree(dir_path)


@pytest.fixture()
def home_dir():

    homedir = tempfile.mkdtemp()
    os.environ['HOME'] = homedir

    yield homedir

    # cleanup
    shutil.rmtree(homedir)


@pytest.fixture()
def runner():

    yield LocalCommandRunner()
