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

from pyci.api.packager import DEFAULT_PY_INSTALLER_VERSION
from pyci.api.packager import DEFAULT_WHEEL_VERSION

BRANCH = 'The name of the branch you want to release. The defaulting heuristics ' \
              'are as follows: ' \
              '1) The branch the build was triggered on. ' \
              '2) The default branch name of the repository.'


MASTER_BRANCH = 'The master branch name. That is, the branch that should point to the ' \
                     'latest stable release. Defaults to master.'


RELEASE_BRANCH = 'The release branch name. That is, the branch that releases should be ' \
                      'made from. This is used to silently ignore commits made to other ' \
                      'branches. Defaults to the repository default branch.'


REPO = 'Github repository full name (i.e: <owner>/<repo>). When running inside a CI ' \
       'system, this will be automatically detected using environment variables.'


ENTRYPOINT = 'Path (relative to the repository root) of the file to be used as the ' \
             'executable entry point. This corresponds to the positional script argument ' \
             'passed to PyInstaller (https://pythonhosted.org/PyInstaller/usage.html)'

BASE_NAME = "The base name of the created file. Defaults to the name specified in setup.py (if exists). " \
            "Note that the full name will be suffixed with platform specific info. For example, on a 64-bit MacOS " \
            "machine, given the name 'pyci', the file will be 'pyci-x86_64-Darwin'"

PY_INSTALLER_VERSION = 'Which version of PyInstaller to use. Note that PyCI is tested only against ' \
               'version {}, this is an advanced option, use at your own peril'.format(DEFAULT_PY_INSTALLER_VERSION)


WHEEL_VERSION = 'Which version of wheel to use for packaging. Note that PyCI is tested only against version {}, ' \
        'this is an advanced option, use at your own peril'.format(DEFAULT_WHEEL_VERSION)
