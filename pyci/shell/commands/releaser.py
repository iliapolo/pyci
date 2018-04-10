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
from pyci.shell import cidetector


# pylint: disable=too-many-arguments
@click.command()
@click.pass_context
@click.option('--sha', required=True)
@click.option('--no-binary', is_flag=True)
@click.option('--binary-entrypoint', required=False)
@click.option('--binary-name', required=False)
@click.option('--force', is_flag=True)
def release(ctx, sha, no_binary, binary_entrypoint, binary_name, force):

    def _do_release():

        release_title = None
        try:
            click.echo('Creating release...')
            release_title = ctx.parent.releaser.release(sha)
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
        if release_title and not no_binary:
            try:
                click.echo('Creating binary package...')
                package = ctx.parent.packager.binary(branch=sha,
                                                     entrypoint=binary_entrypoint,
                                                     name=binary_name)
                click.echo('Successfully created binary package: {0}'.format(package))

                click.echo('Uploading binary package to release...')
                asset_url = ctx.parent.releaser.upload(asset=package, release=release_title)
                click.echo('Successfully uploaded binary package to release: {0}'.format(asset_url))
            except exceptions.EntrypointNotFoundException as e:
                # this is ok, the package doesn't contain an entrypoint in the
                # expected default location. we should however print a log
                # since the user might have expected the binary package (since the default is
                #  to create one)
                click.echo('Binary package will not be created because an entrypoint was not '
                           'found in the expected path: {0}. \nYou can specify a custom '
                           'entrypoint path by using the "--binary-entrypoint" option.\n'
                           'If your package is not meant to be an executable binary, '
                           'use the "--no-binary" flag to avoid seeing this message'
                           .format(e.expected_path))

    ci = cidetector.detect(sha)

    if ci.system:
        click.echo('Detected CI: {0}'.format(ci.system))

    if force or ci.should_release:
        _do_release()
    else:
        click.echo('No need to release this commit: {0}'.format(ci.reason))


@click.command()
@click.pass_context
@click.option('--version', required=True)
def delete(ctx, version):

    click.echo('Deleting release {0}...'.format(version))
    ctx.parent.releaser.delete(version)
    click.echo('Done')
