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

    This command wil have the following affects:

        1. Github release with the version as its title. (With changelog)

        2. A version bump commit to setup.py in the corresponding branch.

        3. Platform dependent binary executable uploaded to the release. (Optional)

        4. Wheel package uploaded to PyPI (Optional)

    In order for the commit to be released, it must meet the following requirements:

        - The current build is a not a PR build. (Applicable only in CI)

        - The current build is a not a tag build (Applicable only in CI)

        - The current build branch differs from the release branch (Applicable only in CI)

        - The commit is not related to any issue.

        - The issue related to the commit is not a release candidate.

    If the commit does not meet any of these requirements, the command will simply return
    successfully and won't do anything. (it will not fail).

    """

    ci = ctx.parent.ci

    sha = ci.sha if ci else None
    branch_name = branch_name or (ci.branch if ci else None)

    repo = detect_repo(ctx.parent.ci, repo)

    try:

        gh = GitHubRepository(repo=repo, access_token=secrets.github_access_token())

        github_release = github.release_branch_internal(
            branch_name=branch_name,
            master_branch_name=master_branch_name,
            release_branch_name=release_branch_name,
            force=force,
            sha=sha,
            gh=gh,
            ci=ci
        )

        packager = Packager(repo, sha=github_release.sha)

        package_directory = tempfile.mkdtemp()

        try:

            log.info('Creating and uploading packages...')

            if not no_binary:

                upload_binary(binary_entrypoint, gh, package_directory, packager)

            if not no_wheel:

                upload_wheel(package_directory, packager, pypi_test, pypi_url, wheel_universal)

            log.info('Hip Hip, Hurray! :). Your new version is released and ready to go.')

        finally:
            packager.clean()
            utils.rmf(package_directory)

    except exceptions.ReleaseValidationFailedException as e:
        log.info('Not releasing: {}'.format(str(e)))

    except exceptions.ApiException as e:
        err = click.ClickException('Failed releasing: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


def upload_wheel(package_directory, packager, pypi_test, pypi_url, wheel_universal):

    pypi_api = PyPI(username=secrets.twine_username(),
                    password=secrets.twine_password(),
                    test=pypi_test, repository_url=pypi_url)
    wheel_path = pack.wheel_internal(universal=wheel_universal,
                                     target_dir=package_directory,
                                     packager=packager)
    pypi.upload_internal(wheel=wheel_path, pypi=pypi_api)


def upload_binary(binary_entrypoint, gh, package_directory, packager):

    try:

        binary_package_path = pack.binary_internal(entrypoint=binary_entrypoint,
                                                   name=None,
                                                   target_dir=package_directory,
                                                   packager=packager)

        github.upload_asset_internal(asset=binary_package_path,
                                     release=release.title,
                                     gh=gh)

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
        raise click.ClickException(message='Failed detecting repository name. Please provide it '
                                           'using the "--repo" option.\nIf you are running '
                                           'locally, you can also execute this command from your '
                                           'project root directory (repository will be detected '
                                           'using git).')
    return repo
