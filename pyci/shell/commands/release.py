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

import click

from pyci.api import exceptions
from pyci.api.packager import Packager


# pylint: disable=too-many-arguments
from pyci.shell import handle_exceptions


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False)
@click.option('--no-binary', is_flag=True)
@click.option('--no-wheel', is_flag=True)
@click.option('--binary-entrypoint', required=False)
@click.option('--binary-name', required=False)
@click.option('--force', is_flag=True)
def create(ctx, branch, no_binary, no_wheel, binary_entrypoint, binary_name, force):

    ci = ctx.parent.parent.ci

    def _do_release(branch_name):

        release_title = None
        try:
            click.echo('Creating release...')
            release_title = ctx.parent.releaser.release(branch_name=branch_name)
            click.echo('Successfully created release: {0}'.format(release_title))
        except exceptions.CommitIsAlreadyReleasedException as e:

            # this is ok, maybe someone is running the command on the same commit
            # over and over again. no need to error here since we still might have things
            # to do later on.
            click.echo('The commit is already released: {0}, Moving on...'.format(e.release))

            # pylint: disable=fixme
            # TODO can there be a scenario where to concurrent releases
            # TODO are executed on the os? this will cause an override of the artifact...
            release_title = e.release
        except (exceptions.CommitNotRelatedToPullRequestException,
                exceptions.PullRequestNotRelatedToIssueException,
                exceptions.IssueIsNotLabeledAsReleaseException) as e:
            # not all commits are eligible for release, this is such a case.
            # we should just break and do nothing...
            click.echo('Not releasing: {0}'.format(str(e)))

        # release_title may be None in case this commit should not
        # be released.
        if release_title:

            packager = Packager(repo=ctx.parent.parent.repo,
                                branch=branch_name,
                                version=release_title)

            if not no_binary:

                try:
                    click.echo('Creating binary package...')
                    package = packager.binary(entrypoint=binary_entrypoint,
                                              name=binary_name)
                    click.echo('Successfully created binary package: {0}'.format(package))

                    click.echo('Uploading binary package to release...')
                    asset_url = ctx.parent.releaser.upload(asset=package, release=release_title)
                    click.echo('Successfully uploaded binary package to release: {0}'
                               .format(asset_url))

                except exceptions.EntrypointNotFoundException as ene:
                    # this is ok, the package doesn't contain an entrypoint in the
                    # expected default location. we should however print a log
                    # since the user might have expected the binary package (since the default is
                    #  to create one)
                    click.echo('Binary package will not be created because an entrypoint was not '
                               'found in the expected path: {0}. \nYou can specify a custom '
                               'entrypoint path by using the "--binary-entrypoint" option.\n'
                               'If your package is not meant to be an executable binary, '
                               'use the "--no-binary" flag to avoid seeing this message'
                               .format(ene.expected_paths))

            if not no_wheel:

                click.echo('Creating wheel...')
                package = packager.wheel()
                click.echo('Successfully created wheel: {0}'.format(package))

                click.echo('Uploading wheel to PyPI...')
                wheel_url = ctx.parent.releaser.upload_pypi(wheel=package)
                click.echo('Successfully uploaded wheel to PyPI: {0}'.format(wheel_url))

    if ci is None and not force:
        click.echo('No CI system detected. If you wish to release nevertheless, '
                   'use the "--force" option.')
    else:

        try:

            branch_name = branch or ctx.parent.releaser.default_branch

            if ci:

                ci.validate_rc(branch_name)

            _do_release(branch_name)

        except exceptions.NotReleaseCandidateException as nrce:
            click.echo('No need to release this commit: {0}'.format(str(nrce)))


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--version', required=True)
def delete(ctx, version):

    click.echo('Deleting release {0}...'.format(version))
    ctx.parent.releaser.delete(version)
    click.echo('Done')


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False)
@click.option('--version', required=False)
@click.option('--patch', is_flag=True)
@click.option('--minor', is_flag=True)
@click.option('--major', is_flag=True)
@click.option('--dry', is_flag=True)
def bump(ctx, branch, version, patch, minor, major, dry):

    if version and (patch or minor or major):
        raise click.ClickException("When specifying '--version' you cannot "
                                   "specify any additional version options (patch, minor, major)")

    click.echo('Bumping version...')
    try:
        setup_py = ctx.parent.releaser.bump(branch_name=branch,
                                            version=version,
                                            patch=patch,
                                            minor=minor,
                                            major=major,
                                            dry=dry)
    except ValueError as e:
        raise click.ClickException(str(e))
    if dry:
        click.echo('\n\n**Running in Dry Mode**\n\n')
        click.echo('Here is what setup.py will look like: \n\n{0}'.format(setup_py))
    click.echo('Done')
