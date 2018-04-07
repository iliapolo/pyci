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
from prettytable import PrettyTable

from pyci.api import exceptions
from pyci.api import logger
from pyci.shell import handle_exceptions

log = logger.get_logger(__name__)


@click.command('release')
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False)
@click.option('--version', required=False)
@click.option('--branch', required=False)
def release_(ctx, sha, version, branch):

    try:
        log.info('Creating release...')
        release_title = ctx.parent.github.release(branch_name=branch, sha=sha, version=version)
        log.info('Successfully created release: {0}'.format(release_title))
    except exceptions.CommitIsAlreadyReleasedException as e:
        # this is ok, maybe someone is running the command on the same commit
        # over and over again (#idempotant-cli)
        log.info('The commit is already released: {0}, I can rest, yey :)'.format(e.release))


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--asset', required=True)
@click.option('--release', required=True)
def upload(ctx, asset, release):

    log.info('Uploading asset {0} to release {1}.. (this may take a while)'.format(asset, release))
    try:
        ctx.parent.github.upload(asset=asset, release=release)
    except exceptions.AssetAlreadyPublishedException:
        # this is ok, maybe someone is running the command on the same asset
        # over and over again (#idempotant-cli).
        log.info('Asset already published for release')

    log.info('Done')


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--release', required=True)
def delete(ctx, release):

    log.info('Deleting release {0}...'.format(release))
    ctx.parent.github.delete(release=release)
    log.info('Done')


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False)
@click.option('--branch', required=False)
@click.option('--version', required=False)
@click.option('--patch', is_flag=True)
@click.option('--minor', is_flag=True)
@click.option('--major', is_flag=True)
@click.option('--dry', is_flag=True)
def bump(ctx, sha, branch, version, patch, minor, major, dry):

    if version and (patch or minor or major):
        raise click.ClickException("When specifying '--version' you cannot "
                                   "specify any additional version options (--patch, --minor, "
                                   "--major)")

    log.info('Bumping version...')
    setup_py = ctx.parent.github.bump(
        sha=sha,
        branch_name=branch,
        version=version,
        patch=patch,
        minor=minor,
        major=major,
        dry=dry)
    if dry:
        log.info('\n\n**Running in Dry Mode**\n\n')
        log.info('Here is what setup.py will look like: \n\n{0}'.format(setup_py))
    log.info('Done')


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False)
@click.option('--branch', required=False)
def changelog(ctx, sha, branch):

    log.info('Fetching latest release...')
    latest_release = ctx.parent.github.last_release

    if latest_release:
        log.info('Generating changelog from version {0}... (this may take a while)'
                 .format(latest_release.title))
    else:
        log.info("Your project hasn't been released yet, generating first changelog...")
    change_log = ctx.parent.github.changelog(branch_name=branch, sha=sha)

    def _build_table(issues):

        table = PrettyTable(field_names=['issue', 'title', 'url', 'labels'])

        for ish in issues:
            labels = ','.join([label.name for label in list(ish.get_labels())])
            table.add_row([ish.number, ish.title, ish.html_url, labels])

        return table.get_string()

    # these functions may take some time
    # because it actually fetches labels from github.
    # this is why we first build all tables and only then
    # start printing. to provide a smooth print.
    features_table = None
    if change_log.features:
        features_table = _build_table(change_log.features)

    bugs_table = None
    if change_log.bugs:
        bugs_table = _build_table(change_log.bugs)

    internals_table = None
    if change_log.internals:
        internals_table = _build_table(change_log.internals)

    dangling_commits_table = None
    if change_log.internals:
        dangling_commits_table = _build_table(change_log.dangling_commits)

    next_version = change_log.next_version

    # now we can print smoothly
    if not change_log.empty:
        click.echo('')

        if features_table:
            click.echo('Features:')
            click.echo(features_table)
            click.echo('')

        if bugs_table:
            click.echo('Bugs:')
            click.echo(bugs_table)
            click.echo('')

        if internals_table:
            click.echo('Internals:')
            click.echo(internals_table)
            click.echo('')

        if dangling_commits_table:
            click.echo('Dangling Commits:')
            click.echo(dangling_commits_table)
            click.echo('')

        log.info('Based on this changelog, the next version will be: {0}'
                 .format(next_version))
    else:
        log.info('Changelog is empty')


@click.command('detect-issue')
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False)
@click.option('--message', required=False)
def issue(ctx, sha, message):

    if sha and message:
        raise click.ClickException("Either '--sha' or '--message' is allowed (not both)")

    if not sha and not message:
        raise click.ClickException("Either '--sha' or '--message' is required")

    if sha:
        log.info('Detecting issue number from commit: {0}'.format(sha))
    if message:
        log.info('Detecting issue number from message: {0}'.format(message))

    git_issue = ctx.parent.github.issue(sha=sha, commit_message=message)
    if git_issue is None:
        log.info('No issue detected')
    else:
        log.info('Issue detected: {0}'.format(git_issue.html_url))
