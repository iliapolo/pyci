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

import logging
import sys

import click

import pyci
import pyci.shell
from pyci.api import logger as api_logger
from pyci.api import ci
from pyci.api.gh import GitHubRepository
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.api import exceptions
from pyci.api import utils
from pyci.shell import REPO_HELP
from pyci.shell import handle_exceptions
from pyci.shell import secrets
from pyci.shell.commands import release
from pyci.shell.subcommands import github as github_group
from pyci.shell.subcommands import pack as pack_group
from pyci.shell.subcommands import pypi as pypi_group
from pyci.shell import logger as shell_logger
from pyci import resources

log = shell_logger.get()


@click.group()
@click.option('--debug', is_flag=True,
              help='Show debug messages')
@click.option('--no-ci', is_flag=True,
              help='Do not detect the current CI provider. This is considered advanced usage, '
                   'do it only if you know what you are doing!.')
@click.pass_context
@handle_exceptions
def app(ctx, debug, no_ci):

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

    ascii_art = resources.get_text_resource('pyci.ascii')

    log.echo('', prefix=False)
    log.echo(ascii_art, prefix=False)

    if debug:
        api_logger.DEFAULT_LOG_LEVEL = logging.DEBUG
        shell_logger.get().logger.set_level(logging.DEBUG)

    ctx.ci_provider = None
    if not no_ci:
        ctx.ci_provider = ci.detect()

    if ctx.ci_provider:
        log.echo('Detected CI Provider: {0}'.format(ctx.ci_provider.name))


@click.group()
@click.option('--repo', required=False,
              help=REPO_HELP)
@click.pass_context
@handle_exceptions
def github(ctx, repo):

    """
    Sub-command for Github operations.
    """

    repo = pyci.shell.detect_repo(ctx, ctx.parent.ci_provider, repo)

    ctx.github = GitHubRepository.create(
        repo=repo,
        access_token=secrets.github_access_token())


@click.group()
@click.pass_context
@click.option('--repo', required=False,
              help=REPO_HELP)
@click.option('--sha', required=False,
              help='Pack a specific sha.')
@click.option('--path', required=False,
              help='Pack a local copy of the repo.')
@click.option('--target-dir', required=False,
              help='The directory to create the packages in. Defaults to the current directory.')
@handle_exceptions
def pack(ctx, repo, sha, path, target_dir):

    """
    Sub-command for packing source code.

    Notice that in case neither --sha nor --path are provided, the last commit from your
    repository's default branch will be
    used.

    """

    if not path:
        repo = pyci.shell.detect_repo(ctx, ctx.parent.ci_provider, repo)

    if repo and not sha:
        raise click.BadOptionUsage('Must specify --sha as well')

    if sha and path:
        raise click.ClickException("Use either --sha or --path, not both")

    if not sha and not path:
        raise click.BadOptionUsage('Must specify either --sha or --path')

    try:
        ctx.packager = Packager.create(repo=repo, path=path, sha=sha, target_dir=target_dir)
    except exceptions.DirectoryDoesntExistException as e:
        err = click.ClickException('The target directory you specified does not exist: {}'
                                   .format(e.path))
        err.possible_solutions = [
            'Create the directory and try again'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.NotPythonProjectException:
        err = click.ClickException('The project is not structured as a standard python '
                                   'project.')
        err.possible_solutions = [
            'Please follow these instructions to create a standard '
            'python project --> https://packaging.python.org/tutorials/distributing-packages/'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.DownloadFailedException as e:
        err = click.ClickException('Failed downloading repository content: {}'.format(e.err))
        if e.code == 404:
            err.cause = 'You either provided a non existing sha or a non existing repository'
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


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

    ctx.pypi = PyPI.create(repository_url=repository_url,
                           test=test,
                           username=secrets.twine_username(),
                           password=secrets.twine_password())


github.add_command(github_group.release_branch)
github.add_command(github_group.validate_commit)
github.add_command(github_group.validate_build)
github.add_command(github_group.generate_changelog)
github.add_command(github_group.create_release)
github.add_command(github_group.upload_asset)
github.add_command(github_group.upload_changelog)
github.add_command(github_group.detect_issue)
github.add_command(github_group.delete_release)
github.add_command(github_group.delete_tag)
github.add_command(github_group.bump_version)
github.add_command(github_group.set_version)
github.add_command(github_group.reset_branch)
github.add_command(github_group.reset_tag)
github.add_command(github_group.create_branch)
github.add_command(github_group.delete_branch)
github.add_command(github_group.create_commit)
github.add_command(github_group.commit_file)
github.add_command(github_group.close_issue)

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
    app(sys.argv[1:])  # pragma: no cover
