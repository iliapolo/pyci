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

from pyci.api.ci import CIDetector
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.api.gh import GitHub
from pyci.api import logger
from pyci.shell import handle_exceptions
from pyci.shell import secrets
from pyci.shell.subcommands import pack as pack_group
from pyci.shell.subcommands import github as github_group
from pyci.shell.subcommands import pypi as pypi_group
from pyci.shell.commands import release


@click.group()
@click.option('--debug', is_flag=True)
@click.pass_context
@handle_exceptions
def app(ctx, debug):

    if debug:
        logger.setup_loggers('DEBUG')

    ctx.ci = CIDetector().detect()

    if ctx.ci:
        click.echo('Detected CI: {0}'.format(ctx.ci.name))


@click.group()
@click.option('--repo', required=False)
@click.pass_context
@handle_exceptions
def github(ctx, repo):

    repo = release.detect_repo(ctx.parent.ci, repo)

    ctx.github = GitHub(repo=repo, access_token=secrets.github_access_token())


@click.group()
@click.pass_context
@click.option('--repo', required=False)
@click.option('--sha', required=False)
@click.option('--path', required=False)
@handle_exceptions
def pack(ctx, repo, sha, path):

    if sha and path:
        raise click.ClickException("Either '--sha' or '--path' is allowed (not both)")

    if not sha and not path:
        raise click.ClickException("Either '--sha' or '--path' is required")

    if not path:
        repo = release.detect_repo(ctx.parent.ci, repo)

    ctx.packager = Packager(repo=repo, path=path, sha=sha)


@click.group()
@click.pass_context
@click.option('--test', is_flag=True)
@click.option('--repository-url', required=False)
@handle_exceptions
def pypi(ctx, test, repository_url):

    ctx.pypi = PyPI(repository_url=repository_url,
                    test=test,
                    username=secrets.twine_username(),
                    password=secrets.twine_password())


github.add_command(github_group.delete)
github.add_command(github_group.bump)
github.add_command(github_group.release)

pack.add_command(pack_group.binary)
pack.add_command(pack_group.wheel)

pypi.add_command(pypi_group.upload)

app.add_command(github)
app.add_command(pack)
app.add_command(pypi)
app.add_command(release.release)

# allows running the application as a single executable
# created by pyinstaller
if getattr(sys, 'frozen', False):
    # pylint: disable=no-value-for-parameter
    app(sys.argv[1:])
