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
from pyci.api import logger
from pyci.shell import handle_exceptions

log = logger.get_logger(__name__)


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False)
@click.option('--sha', required=False)
def release(ctx, branch, sha):

    try:
        log.info('Creating release...')
        release_title = ctx.parent.github.release(branch_name=branch, sha=sha)
        log.info('Successfully created release: {0}'.format(release_title))
    except exceptions.CommitIsAlreadyReleasedException as e:

        # this is ok, maybe someone is running the command on the same commit
        # over and over again. no need to error here since we still might have things
        # to do later on.
        log.info('The commit is already released: {0}, I can rest, yey :)'.format(e.release))

        # pylint: disable=fixme
        # TODO can there be a scenario where to concurrent releases
        # TODO are executed on the os? this will cause an override of the artifact...


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--version', required=True)
def delete(ctx, version):

    log.info('Deleting release {0}...'.format(version))
    ctx.parent.releaser.delete(version)
    log.info('Done')


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

    try:
        log.info('Bumping version...')
        setup_py = ctx.parent.releaser.bump(
            branch_name=branch,
            version=version,
            patch=patch,
            minor=minor,
            major=major,
            dry=dry)
    except ValueError as e:
        raise click.ClickException(str(e))
    if dry:
        log.info('\n\n**Running in Dry Mode**\n\n')
        log.info('Here is what setup.py will look like: \n\n{0}'.format(setup_py))
    log.info('Done')
