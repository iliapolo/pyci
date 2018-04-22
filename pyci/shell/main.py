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

from pyci.api import ci
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.api.gh import GitHubRepository
from pyci.api import logger
from pyci.shell import handle_exceptions
from pyci.shell import secrets
from pyci.shell.subcommands import pack as pack_group
from pyci.shell.subcommands import github as github_group
from pyci.shell.subcommands import pypi as pypi_group
from pyci.shell.commands import release
from pyci.shell import REPO_HELP


log = logger.get_logger(__name__)


@click.group()
@click.option('--debug', is_flag=True,
              help='Show debug messages')
@click.pass_context
@handle_exceptions
def app(ctx, debug):

    """
    Welcome to pyci!

    I can make the release process of your python project very easy :)

    Environment Variables:

    Note that some of the commands require credentials. They are not available as command line
    options but rather as environment variables. If the necessary env variable is not defined,
    you will be prompted to securely input the credentials.

        - GITHUB_ACCESS_TOKEN (Used to access GitHub API)

        - TWINE_USERNAME (Used to connect to PyPI)

        - TWINE_PASSWORD (Used to connect to PyPI)

    """

    if debug:
        logger.setup_loggers(level='DEBUG')

    ctx.ci = ci.detect()

    if ctx.ci:
        log.info('Detected CI: {0}'.format(ctx.ci.name))


@click.group()
@click.option('--repo', required=False,
              help=REPO_HELP)
@click.pass_context
@handle_exceptions
def github(ctx, repo):

    """
    Sub-command for Github operations.
    """

    repo = release.detect_repo(ctx.parent.ci, repo)

    ctx.github = GitHubRepository(repo=repo, access_token=secrets.github_access_token())


@click.group()
@click.pass_context
@click.option('--repo', required=False,
              help='Github repository full name (i.e: <owner>/<repo>). '
                   'When running inside a CI system, this will be '
                   'automatically detected using environment variables. '
                   'When running locally from your repository root directory, '
                   'detected via git commands.')
@click.option('--sha', required=False,
              help='Sha of the commit you wish to pack. Cannot be used in conjunction with --path')
@click.option('--path', required=False,
              help='Path to the root directory of the project. Cannot be used in '
                   'conjunction with --sha')
@handle_exceptions
def pack(ctx, repo, sha, path):

    """
    Sub-command for packing source code.

    Notice that in case neither --sha nor --path are provided, the last commit from your
    repository's default branch will be
    used.

    """

    repo = release.detect_repo(ctx.parent.ci, repo)

    if sha and path:
        raise click.ClickException("Either '--sha' or '--path' is allowed (not both)")

    if not sha and not path:
        sha = GitHubRepository(repo=repo,
                               access_token=secrets.github_access_token()).default_branch_name

    ctx.packager = Packager(repo=repo, path=path, sha=sha)


@click.group()
@click.pass_context
@click.option('--test', is_flag=True,
              help='Use PyPI test repository (https://test.pypi.org/legacy/)')
@click.option('--repository-url', required=False,
              help='Specify a custom PyPI URL')
@handle_exceptions
def pypi(ctx, test, repository_url):

    """
    Sub-command for PyPI operations.
    """

    ctx.pypi = PyPI(repository_url=repository_url,
                    test=test,
                    username=secrets.twine_username(),
                    password=secrets.twine_password())


github.add_command(github_group.delete)
github.add_command(github_group.bump)
github.add_command(github_group.release_)
github.add_command(github_group.changelog)
github.add_command(github_group.upload)
github.add_command(github_group.issue)
github.add_command(github_group.reset_branch)
github.add_command(github_group.set_version)

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
