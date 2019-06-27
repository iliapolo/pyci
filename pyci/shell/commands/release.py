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

import tempfile

import click

from pyci.api import exceptions
from pyci.api import utils
from pyci.api.gh import GitHubRepository
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.api.packager import DEFAULT_PY_INSTALLER_VERSION
from pyci.api.packager import DEFAULT_WHEEL_VERSION
from pyci.shell import BRANCH_HELP, detect_repo
from pyci.api.utils import is_pyinstaller
from pyci.shell import MASTER_BRANCH_HELP
from pyci.shell import RELEASE_BRANCH_HELP
from pyci.shell import REPO_HELP
from pyci.shell import handle_exceptions, secrets
from pyci.shell.subcommands import github
from pyci.shell.subcommands import pack
from pyci.shell.subcommands import pypi
from pyci.shell.logger import get as get_logger

log = get_logger()


# pylint: disable=too-many-arguments,too-many-locals
@click.command()
@handle_exceptions
@click.pass_context
@click.option('--repo', required=False,
              help=REPO_HELP)
@click.option('--branch-name', required=False,
              help=BRANCH_HELP)
@click.option('--changelog-base', required=False,
              help='Base commit for changelog generation. (exclusive)')
@click.option('--version', required=False,
              help='Use this version instead of the automatic, changelog based, generated version.')
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
@click.option('--pyinstaller-version', required=False,
              help='Which version of PyInstaller to use. Note that PyCI is tested only against version {}, this is '
                   'an advanced option, use at your own peril'.format(DEFAULT_PY_INSTALLER_VERSION))
@click.option('--wheel-version', required=False,
              help='Which version of wheel to use. Note that PyCI is tested only against version {}, this is '
                   'an advanced option, use at your own peril'.format(DEFAULT_WHEEL_VERSION))
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
            pyinstaller_version,
            wheel_version,
            changelog_base,
            version,
            force):

    """
    Execute a complete release process.

    This command will do the following:

        1. Execute a github release on the specified branch. (see 'pyci github release --help')

        2. Create and upload a platform dependent binary executable to the release. (Optional)

        3. Create and upload a wheel package to PyPI. (Optional)

    """

    ci_provider = ctx.parent.ci_provider

    branch_name = branch_name or (ci_provider.branch if ci_provider else None)

    if not branch_name:
        raise click.ClickException('Must provide --branch-name')

    repo = detect_repo(ctx, ci_provider, repo)

    if not no_binary and is_pyinstaller():
        error = click.ClickException('Creating a binary package is not supported when '
                                     'running from within a binary')
        error.possible_solutions = [
            'Use --no-binary to skip creating the binary package',
            'Run the command after installing pyci as a wheel (pip install pyci)'
        ]
        raise error

    try:

        github_release, wheel_url = release_internal(
            binary_entrypoint=binary_entrypoint,
            branch_name=branch_name,
            ci=ci_provider,
            force=force,
            master_branch_name=master_branch_name,
            no_binary=no_binary,
            no_wheel=no_wheel,
            pypi_test=pypi_test,
            pypi_url=pypi_url,
            release_branch_name=release_branch_name,
            repo=repo,
            wheel_universal=wheel_universal,
            pyinstaller_version=pyinstaller_version,
            wheel_version=wheel_version,
            changelog_base=changelog_base,
            version=version)

        log.echo('Hip Hip, Hurray! :). Your new version is released and ready to go.', add=True)
        log.echo('Github: {}'.format(github_release.url))

        if wheel_url:
            log.echo('PyPI: {}'.format(wheel_url))

    except exceptions.ReleaseValidationFailedException as e:
        log.sub()
        log.echo("Not releasing: {}".format(str(e)))


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
                     wheel_universal,
                     pyinstaller_version,
                     wheel_version,
                     changelog_base,
                     version):

    gh = GitHubRepository.create(repo=repo, access_token=secrets.github_access_token())
    github_release = github.release_branch_internal(
        branch_name=branch_name,
        master_branch_name=master_branch_name,
        release_branch_name=release_branch_name,
        force=force,
        gh=gh,
        ci_provider=ci,
        changelog_base=changelog_base,
        version=version)

    package_directory = tempfile.mkdtemp()
    packager = Packager.create(repo, sha=github_release.sha, target_dir=package_directory)

    wheel_url = None

    try:

        log.echo('Creating and uploading packages', add=True)

        if not no_binary:
            log.echo('Binary', add=True)
            _upload_binary(binary_entrypoint=binary_entrypoint,
                           gh=gh,
                           packager=packager,
                           github_release=github_release,
                           pyinstaller_version=pyinstaller_version)
            log.sub()

        if not no_wheel:
            log.echo('Wheel', add=True)
            wheel_url = _upload_wheel(packager=packager,
                                      pypi_test=pypi_test,
                                      pypi_url=pypi_url,
                                      wheel_universal=wheel_universal,
                                      wheel_version=wheel_version)
            log.sub()

        log.sub()

    finally:
        try:
            utils.rmf(package_directory)
        except BaseException as e:
            log.warn('Failed cleaning up packager directory ({}): {}'
                     .format(package_directory, str(e)))

    return github_release, wheel_url


def _upload_wheel(packager, pypi_test, pypi_url, wheel_universal, wheel_version):

    pypi_api = PyPI.create(username=secrets.twine_username(),
                           password=secrets.twine_password(),
                           test=pypi_test,
                           repository_url=pypi_url)

    wheel_path = pack.wheel_internal(universal=wheel_universal,
                                     packager=packager,
                                     wheel_version=wheel_version)
    try:
        wheel_url = pypi.upload_internal(wheel=wheel_path, pypi=pypi_api)
    except exceptions.WheelAlreadyPublishedException as e:
        # hmm, this is ok when running concurrently but not
        # so much otherwise...ho can we tell?
        wheel_url = e.url
        log.echo('Wheel {} already published.'.format(e.wheel))

    return wheel_url


def _upload_binary(binary_entrypoint, gh, packager, github_release, pyinstaller_version):

    binary_package_path = None

    try:

        binary_package_path = pack.binary_internal(entrypoint=binary_entrypoint,
                                                   name=None,
                                                   packager=packager,
                                                   pyinstaller_version=pyinstaller_version)

        github.upload_asset_internal(asset=binary_package_path,
                                     release=github_release.title,
                                     gh=gh)
    except IOError:
        # this is really weird, but for some reason this might
        # happen when the asset already exists...
        # see https://github.com/sigmavirus24/github3.py/issues/779
        log.echo('Asset {} already published.'.format(binary_package_path))
    except exceptions.AssetAlreadyPublishedException as e:
        # hmm, this is ok when running concurrently but not
        # so much otherwise...ho can we tell?
        log.echo('Asset {} already published.'.format(e.asset))
    except exceptions.DefaultEntrypointNotFoundException as e:
        # this is ok, just means that the project is not an executable
        # according to our assumptions.
        log.echo('Binary package will not be created because an entrypoint was not '
                 'found in the expected paths: {}. \nYou can specify a custom '
                 'entrypoint path by using the "--binary-entrypoint" option.\n'
                 'If your package is not meant to be an executable binary, '
                 'use the "--no-binary" flag to avoid seeing this message'
                 .format(e.expected_paths))
