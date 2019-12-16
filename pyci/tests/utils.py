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

import shutil
import os
import time

# This whole bit is just so test will import magic mock
# in a unified way from this file, without needing to duplicate this logic.
try:
    # python2
    # pylint: disable=unused-import
    from mock import MagicMock
except ImportError:
    # python3
    # noinspection PyUnresolvedReferences,PyCompatibility
    # pylint: disable=unused-import
    from unittest.mock import MagicMock


from pyci.api.utils import generate_setup_py


def create_release(gh, request, sha, name=None, draft=False):

    release_name = name or request.node.name

    return gh.repo.create_git_release(
        tag=release_name,
        target_commitish=sha,
        name=release_name,
        message='',
        draft=draft
    )


def patch_setup_py(local_repo_path):

    with open(os.path.join(local_repo_path, 'setup.py'), 'r') as stream:
        setup_py = stream.read()

    version = int(round(time.time() * 1000))
    setup_py = generate_setup_py(setup_py, '{}'.format(version))

    with open(os.path.join(local_repo_path, 'setup.py'), 'w') as stream:
        stream.write(setup_py)

    return version


def copy_repo(dst):

    import pyci
    source_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))

    def _copyfile(path):
        shutil.copyfile(path, os.path.join(dst, os.path.basename(path)))

    code = os.path.join(source_path, 'pyci')
    setup_py = os.path.join(source_path, 'setup.py')
    spec = os.path.join(source_path, 'pyci.spec')
    license_path = os.path.join(source_path, 'LICENSE')

    shutil.copytree(code, os.path.join(dst, os.path.basename(code)))
    _copyfile(setup_py)
    _copyfile(spec)
    _copyfile(license_path)
