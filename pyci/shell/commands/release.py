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
import tempfile

import click

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api.gh import GitHubRepository
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.shell import BRANCH_HELP
from pyci.shell import REPO_HELP
from pyci.shell import MASTER_BRANCH_HELP
from pyci.shell import RELEASE_BRANCH_HELP
from pyci.shell import handle_exceptions, secrets
from pyci.shell.subcommands import github
from pyci.shell.subcommands import pack
from pyci.shell.subcommands import pypi

log = logger.get_logger(__name__)


# pylint: disable=too-many-arguments,too-many-locals
@click.command()
@handle_exceptions
@click.pass_context
@click.option('--repo', required=False,
              help=REPO_HELP)
@click.option('--branch-name', required=False,
              help=BRANCH_HELP)
@click.option('--master-branch-name', required=False, default='master',
              help=MASTER_BRANCH_HELP)
@click.option('--release-branch-name', required=False, default='release',
              help=RELEASE_BRANCH_HELP)
@click.option('--pypi-test', is_flag=True,
              help='Use PyPI test index. This option is ignored if --no-wheel is used.')
@click.option('--pypi-url', is_flag=True,
              help='Specify a custom PyPI index url. This option is ignored if --no-wheel is '
                   'used.')
@click.option('--binary-entrypoint', required=False,
              help='Path (relative to the repository root) of the file to be used as the '
                   'executable entry point. This corresponds to the positional script argument '
                   'passed to PyInstaller (https://pythonhosted.org/PyInstaller/usage.html)')
@click.option('--wheel-universal', is_flag=True,
              help='Should the created wheel be universal?.')
@click.option('--force', is_flag=True,
              help='Force release without any validations.')
@click.option('--no-wheel', is_flag=True,
              help='Do not create and upload a wheel package to PyPI as part of the release '
                   'process.')
@click.option('--no-binary', is_flag=True,
              help='Do not create and upload a binary executable as part of the release process.')
def release(ctx,
            repo,
            branch_name,
            master_branch_name,
            release_branch_name,
            pypi_test,
            pypi_url,
            binary_entrypoint,
            wheel_universal,
            no_binary,
            no_wheel,
            force):

    """
    Execute a complete release process.

    This command will do the following:

        1. Execute a github release on the specified branch. (see 'pyci github release --help')

        2. Create and upload ad platform dependent binary executable to the release. (Optional)

        3. Create and upload a wheel package to PyPI. (Optional)

    """

    ci = ctx.parent.ci

    branch_name = branch_name or (ci.branch if ci else None)

    repo = detect_repo(ctx.parent.ci, repo)

    try:

        release_internal(binary_entrypoint=binary_entrypoint,
                         branch_name=branch_name,
                         ci=ci,
                         force=force,
                         master_branch_name=master_branch_name,
                         no_binary=no_binary,
                         no_wheel=no_wheel,
                         pypi_test=pypi_test,
                         pypi_url=pypi_url,
                         release_branch_name=release_branch_name,
                         repo=repo,
                         wheel_universal=wheel_universal)

    except exceptions.ReleaseValidationFailedException as e:
        log.info('Not releasing: {}'.format(str(e)))

    except exceptions.ApiException as e:
        err = click.ClickException('Failed releasing: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


def release_internal(binary_entrypoint,
                     branch_name,
                     ci,
                     force,
                     master_branch_name,
                     no_binary,
                     no_wheel,
                     pypi_test,
                     pypi_url,
                     release_branch_name,
                     repo,
                     wheel_universal):

    gh = GitHubRepository.create(repo=repo, access_token=secrets.github_access_token(ci))
    github_release = github.release_branch_internal(
        branch_name=branch_name,
        master_branch_name=master_branch_name,
        release_branch_name=release_branch_name,
        force=force,
        gh=gh,
        ci=ci)

    packager = Packager.create(repo, sha=github_release.sha)
    package_directory = tempfile.mkdtemp()

    try:

        log.info('Creating and uploading packages...')

        if not no_binary:
            _upload_binary(binary_entrypoint=binary_entrypoint,
                           gh=gh,
                           package_directory=package_directory,
                           packager=packager,
                           github_release=github_release)

        if not no_wheel:
            _upload_wheel(ci=ci,
                          package_directory=package_directory,
                          packager=packager,
                          pypi_test=pypi_test,
                          pypi_url=pypi_url,
                          wheel_universal=wheel_universal)

        log.info('Hip Hip, Hurray! :). Your new version is released and ready to go.')

    finally:
        packager.clean()
        utils.rmf(package_directory)


def _upload_wheel(ci, package_directory, packager, pypi_test, pypi_url, wheel_universal):

    pypi_api = PyPI.create(username=secrets.twine_username(ci),
                           password=secrets.twine_password(ci),
                           test=pypi_test,
                           repository_url=pypi_url)
    wheel_path = pack.wheel_internal(universal=wheel_universal,
                                     target_dir=package_directory,
                                     packager=packager)
    try:
        pypi.upload_internal(wheel=wheel_path, pypi=pypi_api)
    except exceptions.WheelAlreadyPublishedException:
        # hmm, this is ok when running concurrently but not
        # so much otherwise...ho can we tell?
        pass


def _upload_binary(binary_entrypoint, gh, package_directory, packager, github_release):

    try:

        binary_package_path = pack.binary_internal(entrypoint=binary_entrypoint,
                                                   name=None,
                                                   target_dir=package_directory,
                                                   packager=packager)

        github.upload_asset_internal(asset=binary_package_path,
                                     release=github_release.title,
                                     gh=gh)

    except exceptions.AssetAlreadyPublishedException:
        # hmm, this is ok when running concurrently but not
        # so much otherwise...ho can we tell?
        pass
    except exceptions.DefaultEntrypointNotFoundException as e:
        # this is ok, just means that the project is not an executable
        # according to our assumptions.
        log.info('Binary package will not be created because an entrypoint was not '
                 'found in the expected paths: {}. \nYou can specify a custom '
                 'entrypoint path by using the "--binary-entrypoint" option.\n'
                 'If your package is not meant to be an executable binary, '
                 'use the "--no-binary" flag to avoid seeing this message'
                 .format(e.expected_paths))


def detect_repo(ci, repo):

    repo = repo or (ci.repo if ci else utils.get_local_repo())
    if repo is None:
        error = click.ClickException(message='Failed detecting repository name')
        error.possible_solutions = [
            'Provide it using the --repo option',
            'Run the command from the porject root directory, the repository name will be '
            'detected using git commands'
        ]
        raise error
    return repo
