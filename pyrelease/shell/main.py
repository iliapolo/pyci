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

import sys

import click

from pyrelease.shell import handle_exceptions
from pyrelease.shell.commands import release


@click.group()
@handle_exceptions
def app(*_):
    pass


app.add_command(release.release)
app.add_command(release.delete)

# allows running the application as a single executable
# created by pyinstaller
if getattr(sys, 'frozen', False):
    app(sys.argv[1:])
