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


class Context(object):

    def __init__(self):
        super(Context, self).__init__()
        self._ci_provider = None
        self._github = None
        self._packager = None

    @property
    def ci_provider(self):
        return self._ci_provider

    @ci_provider.setter
    def ci_provider(self, value):
        self._ci_provider = value

    @property
    def github(self):
        return self._github

    @github.setter
    def github(self, value):
        self._github = value

    @property
    def packager(self):
        return self._packager

    @packager.setter
    def packager(self, value):
        self._packager = value
