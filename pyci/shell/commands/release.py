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
from pyci.api.packager import DEFAULT_PY_INSTALLER_VERSION
from pyci.api.packager import DEFAULT_WHEEL_VERSION
from pyci.shell import handle_exceptions
from pyci.shell.subcommands import github
from pyci.shell.subcommands import pack
from pyci.shell.subcommands import pypi
from pyci.shell.logger import get as get_logger
from pyci.shell.exceptions import TerminationException
from pyci.shell import help as pyci_help

log = get_logger()


# pylint: disable=too-many-arguments,too-many-locals
@click.command()
@handle_exceptions
@click.pass_context
@click.option('--repo', required=False,
              help=pyci_help.REPO)
@click.option('--branch', required=False,
              help=pyci_help.BRANCH)
@click.option('--changelog-base', required=False,
              help='Base commit for changelog generation. (exclusive)')
@click.option('--version', required=False,
              help='Use this version instead of the automatic, changelog based, generated version.')
@click.option('--master-branch', required=False, default='master',
              help=pyci_help.MASTER_BRANCH)
@click.option('--release-branch', required=False, default='release',
              help=pyci_help.RELEASE_BRANCH)
@click.option('--pypi-test', is_flag=True,
              help='Use PyPI test index. This option is ignored if --no-wheel is used.')
@click.option('--pypi-url', is_flag=True,
              help='Specify a custom PyPI index url. This option is ignored if --no-wheel is '
                   'used.')
@click.option('--binary-entrypoint', required=False,
              help=pyci_help.ENTRYPOINT)
@click.option('--binary-base-name', required=False,
              help=pyci_help.BASE_NAME)
@click.option('--wheel-universal', is_flag=True,
              help='Should the created wheel be universal?.')
@click.option('--force', is_flag=True,
              help='Force release without any validations.')
@click.option('--no-wheel', is_flag=True,
              help='Do not create and upload a wheel package to PyPI as part of the release '
                   'process.')
@click.option('--no-wheel-publish', is_flag=True,
              help='Do not upload the wheel to PyPI. (Will still upload to the GitHub release)')
@click.option('--no-binary', is_flag=True,
              help='Do not create and upload a binary executable as part of the release process.')
@click.option('--no-installer', is_flag=True,
              help='Do not create and upload an installer package.')
@click.option('--pyinstaller-version', required=False,
              help='Which version of PyInstaller to use. Note that PyCI is tested only against '
                   'version {}, this is an advanced option, use at your own peril'
              .format(DEFAULT_PY_INSTALLER_VERSION))
@click.option('--wheel-version', required=False,
              help='Which version of wheel to use. Note that PyCI is tested only against '
                   'version {}, this is an advanced option, use at your own peril'
              .format(DEFAULT_WHEEL_VERSION))
# pylint: disable=too-many-branches
def release(ctx,
            repo,
            branch,
            master_branch,
            release_branch,
            pypi_test,
            pypi_url,
            binary_entrypoint,
            binary_base_name,
            wheel_universal,
            no_binary,
            no_wheel,
            pyinstaller_version,
            wheel_version,
            changelog_base,
            version,
            no_wheel_publish,
            no_installer,
            force):

    """
    Execute a complete release process.

        1. Execute a github release on the specified branch. (see 'pyci github release --help')

        2. Create and upload a platform dependent binary executable to the release.

        3. Create and upload a wheel to the release.

        4. Publish the wheel on PyPI.

    Much of this process is configurable via the command options. For example you can choose not to publish
    the wheel to PyPI by specifying the '--no-publish` flag.

    """

    ci_provider = ctx.obj.ci_provider

    branch = branch or (ci_provider.branch if ci_provider else None)

    if not branch:
        raise click.BadOptionUsage(option_name='branch-name', message='Must provide --branch-name when '
                                                                      'running outside CI')

    try:

        # No other way unfortunately, importing it normally would cause
        # an actual runtime cyclic-import problem.
        # pylint: disable=cyclic-import
        from pyci.shell import main

        ctx.invoke(main.github, repo=repo)
        ctx.invoke(main.pypi, test=pypi_test, repository_url=pypi_url)

        github_release = ctx.invoke(github.release_,
                                    version=version,
                                    branch=branch,
                                    master_branch=master_branch,
                                    release_branch=release_branch,
                                    changelog_base=changelog_base,
                                    force=force)

        ctx.invoke(main.pack, repo=repo, sha=github_release.sha)

        package_directory = tempfile.mkdtemp()

        wheel_url = None

        try:

            binary_path = None
            wheel_path = None
            installer_path = None

            log.echo('Creating packages', add=True)

            if not no_binary:
                binary_path = _pack_binary(ctx=ctx,
                                           base_name=binary_base_name,
                                           entrypoint=binary_entrypoint,
                                           pyinstaller_version=pyinstaller_version)

            if not no_wheel:
                wheel_path = _pack_wheel(ctx=ctx,
                                         wheel_universal=wheel_universal,
                                         wheel_version=wheel_version)

            if not no_installer:
                installer_path = _pack_installer(ctx=ctx, binary_path=binary_path)

            log.sub()

            log.echo('Uploading packages', add=True)

            if binary_path:
                _upload_asset(ctx=ctx,
                              asset_path=binary_path,
                              github_release=github_release)

            if installer_path:
                _upload_asset(ctx=ctx,
                              asset_path=installer_path,
                              github_release=github_release)

            if wheel_path:
                _upload_asset(ctx=ctx,
                              asset_path=wheel_path,
                              github_release=github_release)

                if not no_wheel_publish:
                    _upload_pypi(ctx=ctx,
                                 wheel_path=wheel_path)

            log.sub()

        finally:
            try:
                utils.rmf(package_directory)
            except BaseException as e:
                log.warn('Failed cleaning up packager directory ({}): {}'
                         .format(package_directory, str(e)))

        log.echo('Hip Hip, Hurray! :). Your new version is released and ready to go.', add=True)
        log.echo('Github: {}'.format(github_release.url))

        if wheel_url:
            log.echo('PyPI: {}'.format(wheel_url))

        return github_release, wheel_url

    except TerminationException as e:

        if isinstance(e.cause, exceptions.ReleaseValidationFailedException):
            log.sub()
            log.echo("Not releasing: {}".format(str(e)))
            return None, None

        raise


def _pack_installer(ctx, binary_path):

    if not utils.is_windows():
        # Currently installers are only supported for windows.
        # Rpm and Deb are in the works.
        return None

    exei_path = ctx.invoke(pack.exei,
                           binary_path=binary_path,
                           version=None,
                           output=None,
                           author=None,
                           website=None,
                           copyr=None,
                           license_path=None)

    return exei_path


def _pack_wheel(ctx, wheel_universal, wheel_version):

    wheel_path = ctx.invoke(pack.wheel,
                            universal=wheel_universal,
                            wheel_version=wheel_version)

    return wheel_path


def _pack_binary(ctx, base_name, entrypoint, pyinstaller_version):

    binary_package_path = None

    try:

        binary_package_path = ctx.invoke(pack.binary,
                                         entrypoint=entrypoint,
                                         base_name=base_name,
                                         pyinstaller_version=pyinstaller_version)

    except TerminationException as e:

        if isinstance(e.cause, exceptions.DefaultEntrypointNotFoundException):
            # this is ok, just means that the project is not an executable
            # according to our assumptions.
            log.echo('Binary package will not be created because an entrypoint was not '
                     'found in the expected paths: {}. \nYou can specify a custom '
                     'entrypoint path by using the "--binary-entrypoint" option.\n'
                     'If your package is not meant to be an executable binary, '
                     'use the "--no-binary" flag to avoid seeing this message'
                     .format(e.cause.expected_paths))
            return binary_package_path

        raise

    return binary_package_path


def _upload_asset(ctx, asset_path, github_release):

    try:

        ctx.invoke(github.upload_asset,
                   asset=asset_path,
                   release=github_release.title)

    except TerminationException as e:

        if isinstance(e.cause, IOError):
            # this is really weird, but for some reason this might
            # happen when the asset already exists...
            # see https://github.com/sigmavirus24/github3.py/issues/779
            log.echo('Asset {} already published.'.format(asset_path))
            return

        if isinstance(e.cause, exceptions.AssetAlreadyPublishedException):
            # hmm, this is ok when running concurrently but not
            # so much otherwise...ho can we tell?
            log.echo('Asset {} already published.'.format(e.cause.asset))
            return

        raise


def _upload_pypi(ctx, wheel_path):

    try:

        ctx.invoke(pypi.upload, wheel=wheel_path)

    except TerminationException as e:

        if isinstance(e.cause, exceptions.WheelAlreadyPublishedException):
            # hmm, this is ok when running concurrently but not
            # so much otherwise...ho can we tell?
            log.echo('Wheel {} already published.'.format(e.cause.wheel))
            return

        raise
