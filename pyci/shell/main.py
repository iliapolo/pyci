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

from pyci.api.packager import Packager
from pyci.api.releaser import GitHubReleaser
from pyci.shell import handle_exceptions
from pyci.shell import secrets
from pyci.shell.commands import packager as packager_group
from pyci.shell.commands import releaser as releaser_group


@click.group()
@click.option('--repo', required=True)
@click.pass_context
@handle_exceptions
def app(ctx, repo):

    ctx.repo = repo


@click.group()
@click.pass_context
@handle_exceptions
def releaser(ctx):

    ctx.releaser = GitHubReleaser(repo=ctx.parent.repo, access_token=secrets.github_access_token())
    ctx.packager = Packager(repo=ctx.parent.repo)


@click.group()
@click.pass_context
@click.option('--branch', required=True)
@handle_exceptions
def packager(ctx, branch):

    ctx.packager = Packager(repo=ctx.parent.repo)
    ctx.branch = branch


releaser.add_command(releaser_group.release)
releaser.add_command(releaser_group.delete)

packager.add_command(packager_group.binary)

app.add_command(releaser)
app.add_command(packager)

# allows running the application as a single executable
# created by pyinstaller
if getattr(sys, 'frozen', False):
    # pylint: disable=no-value-for-parameter
    app(sys.argv[1:])
