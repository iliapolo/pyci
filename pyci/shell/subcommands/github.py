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
from pyci.shell import RELEASE_BRANCH_HELP
from pyci.shell import RELEASE_SHA_HELP
from pyci.shell import RELEASE_VERSION_HELP

log = logger.get_logger(__name__)


@click.command('release')
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False,
              help=RELEASE_BRANCH_HELP)
@click.option('--sha', required=False,
              help=RELEASE_SHA_HELP)
@click.option('--version', required=False,
              help=RELEASE_VERSION_HELP)
def release_(ctx, sha, version, branch):

    """

    Create a Github Release.

    This command will have the following affects:

        1. Github release with the version as its title. (With changelog)

        2. A version bump commit to setup.py in the corresponding branch.

    Notice that this command does not perform any validations on the sha or the branch.
    (This is as opposed to 'pyci release').

    However, if pyci detects that the sha is actually already released, it will log a
    message and exit successfully. (#idempotent-cli)

    """

    ci = ctx.parent.ci

    branch = branch or (ci.branch if ci else None) or ctx.parent.github.default_branch_name
    sha = sha or branch or (ci.sha if ci else None) or ctx.parent.github.default_branch_name

    try:
        log.info('Creating release... (sha={0}, branch={1})'.format(sha, branch))
        release_title = ctx.parent.github.release(branch_name=branch, sha=sha, version=version)
        log.info('Successfully created release: {0}'.format(release_title))
    except exceptions.CommitIsAlreadyReleasedException as e:
        # this is ok, maybe someone is running the command on the same commit
        # over and over again (#idempotant-cli)
        log.info('The commit is already released: {0}, I can rest, yey :)'.format(e.release))


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--asset', required=True,
              help='Path to the asset you want to upload.')
@click.option('--release', required=True,
              help='The name of the release you want to upload to.')
def upload(ctx, asset, release):

    """

    Upload an asset to a Github release.

    This command will have the following affects:

        1. Additional asset in the specified release. (The name of the asset in the release will
        be the basename of the file path.)

    Note that if an asset with the given name already exists in the release, the command will
    log a message and exit successfully (#idempotent-cli)

    """

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
@click.option('--release', required=True,
              help='The name of the release you want to delete.')
def delete(ctx, release):

    """

    Delete a Github release.

    This command will have the following affects:

        1. The release will be deleted from the 'releases' tab.
        2. The tag associated with the release will also be deleted.

    Note that if the release (and or tag) does not exist, the command will log a message and
    exit successfully (#idempotent-cli)

    """

    log.info('Deleting release {0}...'.format(release))
    ctx.parent.github.delete(release=release)
    log.info('Done')


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False,
              help='The name of the branch you want to commit to. The defaulting heuristics are as '
                   'follows: 1) The branch the build was triggered on. 2) '
                   'The default branch name of the repository.')
@click.option('--sha', required=False,
              help='The sha of the commit used to download setup.py. The defaulting heuristics are '
                   'as follows: 1) The value of --branch. 2) The '
                   'branch that triggered the build. 3) The name of the default branch')
@click.option('--version', required=False,
              help='The version you want setup.py to have. Cannot be used in conjunction with '
                   '--patch nor --minor nor --major.')
@click.option('--patch', is_flag=True,
              help='Bump the patch version. Cannot be used in conjunction with --version.')
@click.option('--minor', is_flag=True,
              help='Bump the minor version. Cannot be used in conjunction with --version.')
@click.option('--major', is_flag=True,
              help='Bump the major version. Cannot be used in conjunction with --version.')
@click.option('--dry', is_flag=True,
              help="Don't actually perform the commit, "
                   "just show me what setup.py will look like if you had.")
def bump(ctx, sha, branch, version, patch, minor, major, dry):

    """

    Bump the version of setup.py.

    Downloads the setup.py file from the commit you specified, and bumps its version
    according to the version options.

    This command wil have the following affects:

        1. A bump version commit to setup.py (If not --dry)

    Note that if you specify --version and give the same version that setup.py currently has,
    the command will complete successfully (#idempotent-cli)

    """

    if version and (patch or minor or major):
        raise click.BadOptionUsage("When specifying '--version' you cannot "
                                   "specify any additional version options (--patch, --minor, "
                                   "--major)")

    ci = ctx.parent.ci

    branch = branch or (ci.branch if ci else None) or ctx.parent.github.default_branch_name
    sha = sha or branch or (ci.sha if ci else None) or ctx.parent.github.default_branch_name

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
@click.option('--branch', required=False,
              help='The name of the branch you want to calculate changelog for. The last commit '
                   'of this repository will be used. The defaulting '
                   'heuristics are as follows: 1) The branch the build was triggered on. 2) '
                   'The default branch name of the repository.')
@click.option('--sha', required=False,
              help='The sha of the commit you want to calculate changelog for. The defaulting '
                   'heuristics are as follows: 1) The value of --branch. 2) The '
                   'branch that triggered the build. 3) The name of the default branch')
def changelog(ctx, sha, branch):

    """

    Show changelog of a specific commit.

    Calculates the changelog of the given commit relative to the latest release available.

    The output may include the following sections:

        1. Features - features that were introduced.

        2. Bugs - bugs were fixed.

        3. Internals - internal issues that were implemented.

        4. Dangling Commits - commits pushed to the branch that are not related to any issue.

    This command does not have any affects and is read-only.

    """

    ci = ctx.parent.ci

    branch = branch or (ci.branch if ci else None) or ctx.parent.github.default_branch_name
    sha = sha or branch or (ci.sha if ci else None) or ctx.parent.github.default_branch_name

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
    if change_log.other_issues:
        internals_table = _build_table(change_log.other_issues)

    dangling_commits_table = None
    if change_log.other_issues:
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


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False,
              help='The sha of the commit you want to inspect. The defaulting heuristics are as '
                   'follows: 1) The branch that triggered the build. '
                   '2) The name of the default branch')
@click.option('--message', required=False)
def issue(ctx, sha, message):

    """

    Detect an issue for a specific commit.

    This command does not have any affects and is read-only.

    Parses the commit message to detect which issue as related to that commit.

    This command does not have any affects and is read-only.

    """

    if sha and message:
        raise click.BadOptionUsage("Either '--sha' or '--message' is allowed (not both)")

    if not sha and not message:
        raise click.BadOptionUsage("Either '--sha' or '--message' is required")

    ci = ctx.parent.ci

    sha = sha or (ci.sha if ci else None) or ctx.parent.github.default_branch_name

    if sha:
        log.info('Detecting issue number from commit: {0}'.format(sha))
    if message:
        log.info('Detecting issue number from message: {0}'.format(message))

    git_issue = ctx.parent.github.issue(sha=sha, commit_message=message)
    if git_issue is None:
        log.info('No issue detected')
    else:
        log.info('Issue detected: {0}'.format(git_issue.html_url))
