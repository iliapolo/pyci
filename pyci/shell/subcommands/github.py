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

import os
import sys
import tempfile

import click

from pyci.api import exceptions
from pyci.api import utils
from pyci.api import model
from pyci.shell import solutions
from pyci.shell import handle_exceptions
from pyci.shell.logger import get as get_logger
from pyci.shell.exceptions import ShellException
from pyci.shell.exceptions import TerminationException
from pyci.shell import help as pyci_help
from pyci.shell.subcommands import ci

log = get_logger()


@click.command('release')
@handle_exceptions
@click.pass_context
@click.option('--branch',
              help=pyci_help.BRANCH)
@click.option('--master-branch', required=False, default='master',
              help=pyci_help.MASTER_BRANCH)
@click.option('--release-branch', required=False, default='release',
              help=pyci_help.RELEASE_BRANCH)
@click.option('--version', required=False,
              help='Use this version instead of the automatic, changelog based, generated version.')
@click.option('--changelog-base', required=False,
              help='Base commit for changelog generation. (exclusive)')
@click.option('--force', is_flag=True,
              help='Force release without any validations.')
# pylint: disable=inconsistent-return-statements
def release_(ctx, version, branch, master_branch, release_branch, changelog_base, force):

    """
    Release a branch.

    Note that this differs from the create-release command:

        1. Create a Github release with the version as its title.

        2. Create a commit bumping the version of setup.py on top of the branch.

        3. Generated and upload changelog of the head of the branch, relative to the latest release.

        4. Update the master branch to point to the release commit.

        4. Close any related issues with a comment specifying the release title.

    The version is calculated automatically according to the changelog. Note that the release tag
    will point to the above mentioned commit.

    The command is mainly intended to be executed automatically using CI systems (as described
    below), and implements certain heuristics in order to perform properly.

    Note, the release process will only take place if the following conditions hold:

        1. The current build passes validation. (see validate-build)

        2. The tip of the branch passes validation. (see validate-commit)

        3. The release does not yet exist.

    If either of these conditions is not satisfied, the command will be silently ignored and
    complete successfully. This is useful so that your builds will not fail when running on
    commits that shouldn't be released.

    This command is idempotent, given that the tip of your branch hasn't changed between
    executions. You can safely run this command in parallel, this is important when running
    your CI process on multiple systems concurrently.

    """

    ci_provider = ctx.obj.ci_provider
    gh = ctx.obj.github

    branch = branch or (ci_provider.branch if ci_provider else None)
    sha = ci_provider.sha if ci_provider else branch

    if not force:

        try:
            ctx.invoke(ci.validate_build, release_branch=release_branch)
            ctx.invoke(validate_commit, sha=sha)
        except TerminationException as e:
            if isinstance(e.cause, exceptions.ReleaseValidationFailedException):
                log.sub()
                log.echo("Not releasing: {}".format(str(e)))
                return

            raise

    log.echo("Releasing branch '{}'".format(branch), add=True)

    changelog = _generate_changelog(gh=gh, sha=sha, base=changelog_base)

    next_version = version or changelog.next_version

    if not next_version:

        err = ShellException('None of the commits in the changelog references an issue '
                             'labeled with a release label. Cannot determine what the '
                             'version number should be.')
        err.cause = 'You probably only committed internal issues since the last release, ' \
                    'or forgot to reference the issue.'
        err.possible_solutions = [
            'Amend the message of one of the commits to reference a release issue',
            'Push another commit that references a release issue',
            'Use --version to specify a version manually'
        ]

        raise err

    release = _create_release(ctx=ctx,
                              changelog=changelog,
                              branch=branch,
                              master_branch=master_branch,
                              version=next_version,
                              sha=sha)

    log.echo('Closing issues', add=True)
    for issue in changelog.all_issues:
        ctx.invoke(close_issue, number=issue.impl.number, release=release.title)
    log.sub()

    log.sub()

    log.echo('Successfully released: {}'.format(release.url))

    return release


@click.command(context_settings=dict(ignore_unknown_options=True,))
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False,
              help='Validate this specific commit.')
def validate_commit(ctx, sha, **_):

    """
    Validate that a commit should be released.

    The conditions for release are:

        1. The commit is associated to an issue via the '#' sign in its message.

        2. The issue is marked with at least one of the release labels. (patch, minor, major).

    """

    gh = ctx.obj.github
    ci_provider = ctx.obj.ci_provider

    sha = sha or (ci_provider.sha if ci_provider else None)

    def _pre_issue():
        log.echo('Commit references an issue...', break_line=False)

    def _post_issue():
        log.checkmark()

    def _pre_label():
        log.echo('Issue is labeled with a release label...', break_line=False)

    def _post_label():
        log.checkmark()

    log.echo('Validating commit', add=True)

    try:
        gh.validate_commit(sha=sha,
                           hooks={
                               'pre_issue': _pre_issue,
                               'pre_label': _pre_label,
                               'post_issue': _post_issue,
                               'post_label': _post_label
                           })
    except exceptions.ReleaseValidationFailedException as e:
        log.xmark()
        log.sub()
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(e, tb)
    log.sub()

    log.echo('Validation passed')


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--base', required=False,
              help='Use this commit as the base (exclusive). Can also be a branch name.')
@click.option('--sha', required=False,
              help='Generate for this specific commit.')
@click.option('--target', required=False, type=click.Path(exists=False),
              help='Path to the destination file. Defaults to ./<sha/branch>-changelog.md')
def generate_changelog(ctx, base, sha, target):

    """
    Generate a changelog file of a specific commit.

    Determines the changelog of the given commit relative to the latest release available and
    creates a .md file.

    The output file may include the following sections:

        1. Features - features that were introduced.

        2. Bugs - bugs were fixed.

        3. Issues - general issues that were implemented.

        4. Dangling Commits - commits pushed to the branch that are not related to any issue.

    """

    gh = ctx.obj.github

    default_destination = os.path.join(os.getcwd(), '{}-changelog.md'.format(sha))
    target = target or default_destination
    destination = os.path.abspath(target)

    utils.validate_directory_exists(os.path.abspath(os.path.join(destination, os.pardir)))
    utils.validate_file_does_not_exist(destination)

    changelog = _generate_changelog(gh=gh, base=base, sha=sha)

    with open(destination, 'w') as stream:
        rendered = changelog.render()
        stream.write(rendered)

    log.echo('Changelog written to: {}'.format(destination))

    return changelog


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False,
              help='Release this specific commit.')
def create_release(ctx, sha):

    """
    Create a release from a commit.

    The release title will be the version in setup.py of the specified commit.

    This command is NOT idempotent.

    """

    try:

        gh = ctx.obj.github

        log.echo('Creating a GitHub release')
        release = gh.create_release(sha=sha)
        log.echo('Release created: {}'.format(release.url))
        return release

    except exceptions.NotPythonProjectException as e:
        err = ShellException(str(e))
        err.possible_solutions = solutions.non_standard_project()
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--asset', required=True,
              help='Path to the asset you want to upload.')
@click.option('--release', required=True,
              help='The name of the release you want to upload to.')
def upload_asset(ctx, asset, release):

    """
    Upload an asset to a release.

    The name of the asset in the release will be the basename of the asset file.

    """

    try:

        gh = ctx.obj.github

        log.echo('Uploading {} to release {}...'
                 .format(os.path.basename(asset), release), break_line=False)
        asset_url = gh.upload_asset(asset=asset, release=release)
        log.checkmark()
        log.echo('Uploaded asset: {}'.format(asset_url))
        return asset_url
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--changelog', required=True,
              help='Path to the changelog file you want to upload.')
@click.option('--release', required=True,
              help='The name of the release you want to upload to.')
def upload_changelog(ctx, changelog, release):

    """
    Upload a changelog to a release.

    Note that this will override any existing changelog.

    """

    try:

        gh = ctx.obj.github

        log.echo('Uploading changelog...', break_line=False)
        utils.validate_file_exists(changelog)
        with open(changelog) as stream:
            gh.upload_changelog(changelog=stream.read(), release=release)
        log.checkmark()
        log.echo('Uploaded changelog to release {}'.format(release))
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--sha', required=False,
              help='Detect from a sha, the message will be retrieved.')
@click.option('--message', required=False,
              help='Detect from a commit message directly.')
def detect_issue(ctx, sha, message):

    """
    Detect an issue for a specific commit.

    Parses the commit message to detect which issue as related to that commit.

    """

    if sha and message:
        raise click.UsageError('Use either --sha or --message, not both.')

    if not sha and not message:
        raise click.UsageError('Must specify either --sha or --message.')

    try:
        log.echo('Detecting issue...', break_line=False)
        issue = ctx.obj.github.detect_issue(sha=sha, commit_message=message)
        log.checkmark()
        if issue:
            log.echo('Issue detected: {}'.format(issue.url))
        else:
            log.echo('The commit is not related ot any issue.')
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The name of the release you want to delete.')
def delete_release(ctx, name):

    """
    Delete a release.

    This command will not delete the tag associated with the release.
    To delete the tag as well, use the 'delete-tag' command.
    """

    try:

        gh = ctx.obj.github

        log.echo('Deleting release...', break_line=False)
        gh.delete_release(name=name)
        log.checkmark()
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The name of the tag you want to delete.')
def delete_tag(ctx, name):

    """
    Delete a tag.

    """

    try:

        gh = ctx.obj.github

        log.echo('Deleting tag...', break_line=False)
        gh.delete_tag(name=name)
        log.checkmark()
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--branch', required=True,
              help='Which branch to read setup.py from.')
@click.option('--semantic', required=True, type=click.Choice(['patch', 'minor', 'major']),
              help='Which semantic bump to perform.')
def bump_version(ctx, branch, semantic):

    """
    Bump the version of setup.py.

    This command will create a commit on top of the specified branch.

    """

    try:
        log.echo('Bumping version...', break_line=False)
        bump = ctx.obj.github.bump_version(branch=branch, semantic=semantic)
        log.checkmark()
        log.echo('Bumped version from {} to {}'.format(bump.prev_version, bump.next_version))
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--branch', required=True,
              help='Which branch to create the commit on.')
@click.option('--value', required=True,
              help='The semantic version value.')
def set_version(ctx, branch, value):

    """
    Bump the version of setup.py.

    This command will create a commit on top of the specified branch.

    """

    try:

        gh = ctx.obj.github

        log.echo('Setting version...', break_line=False)
        bump = gh.set_version(branch=branch, value=value)
        log.checkmark()
        log.echo('Version is now {} (was {})'.format(bump.next_version, bump.prev_version))
        return bump
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The branch name')
@click.option('--sha', required=True,
              help='The sha to reset the branch to.')
@click.option('--hard', is_flag=True,
              help='Preform a hard reset.')
def reset_branch(ctx, name, sha, hard):

    """
    Reset the specified branch to the given sha.

    This is equivalent to 'git reset'

    """

    try:

        gh = ctx.obj.github

        log.echo("Updating {} branch...".format(name), break_line=False)
        gh.reset_branch(name=name, sha=sha, hard=hard)
        log.echo('Branch {} is now at {} '.format(name, sha), break_line=False)
        log.checkmark()
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The branch name')
@click.option('--sha', required=True,
              help='The sha to branch out from.')
def create_branch(ctx, name, sha):

    """
    Create a branch from a specific sha.

    """

    try:

        gh = ctx.obj.github

        log.echo('Creating branch...', break_line=False)
        branch = gh.create_branch(name=name, sha=sha)
        log.checkmark()
        log.echo('Branch {} created at {}'.format(name, sha))
        return branch
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The branch name')
def delete_branch(ctx, name):

    """
    Delete a branch.

    """

    try:

        gh = ctx.obj.github

        log.echo('Deleting branch...', break_line=False)
        branch = gh.delete_branch(name=name)
        log.checkmark()
        log.echo('Done')
        return branch
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--branch', required=True,
              help='The branch to commit to.')
@click.option('--path', required=True,
              help='Path to the file, relative to the repository root.')
@click.option('--contents', required=True,
              help='The new file contents.')
@click.option('--message', required=True,
              help='The commit message.')
def commit(ctx, branch, path, contents, message):

    """
    Commit a file remotely.

    """

    try:
        log.echo('Committing file...', break_line=False)
        the_commit = ctx.obj.github.commit(
            path=path,
            contents=contents,
            message=message,
            branch=branch)
        log.checkmark()
        log.echo('Created commit: {}'.format(the_commit.url))
    except BaseException as _:
        log.xmark()
        raise


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--number', required=True, type=int,
              help='The issue number.')
@click.option('--release', required=True,
              help='The release this issue is part of.')
def close_issue(ctx, number, release):

    """
    Closes an issue as part of a specific release. This command will also add a comment to the
    issue linking to the release.

    """

    try:

        gh = ctx.obj.github

        log.echo('Closing issue number {}...'.format(number), break_line=False)
        gh.close_issue(num=number, release=release)
        log.checkmark()
    except BaseException as _:
        log.xmark()
        raise


def _create_release(ctx, changelog, version, branch, master_branch, sha):

    gh = ctx.obj.github

    next_version = version or changelog.next_version

    try:

        # figure out how to avoid calling private api here...
        # exposing this doesn't seem like a good solution either.
        # noinspection PyProtectedMember
        # pylint: disable=protected-access
        set_version_commit = gh._create_set_version_commit(value=next_version, sha=sha).impl

        release = ctx.invoke(create_release, sha=set_version_commit.sha)

        bump = model.ChangelogCommit(title=set_version_commit.message,
                                     url=set_version_commit.html_url,
                                     timestamp=set_version_commit.author.date,
                                     impl=set_version_commit)
        changelog.add(bump)

        changelog_file = os.path.join(tempfile.mkdtemp(), 'changelog.md')
        with open(changelog_file, 'w') as stream:
            stream.write(changelog.render())
        ctx.invoke(upload_changelog, changelog=changelog_file, release=release.title)

        log.echo('Bumping version to {}'.format(next_version))
        ctx.invoke(reset_branch, name=branch, sha=set_version_commit.sha, hard=False)
        if master_branch != branch:
            ctx.invoke(reset_branch, name=master_branch, sha=set_version_commit.sha, hard=False)

    except TerminationException as e:

        if isinstance(e.cause, exceptions.ReleaseAlreadyExistsException):
            log.echo('Release {} already exists'.format(e.cause.release))
            ref = gh.repo.get_git_ref(ref='tags/{}'.format(e.cause.release))
            rel = gh.repo.get_release(id=next_version)
            release = model.Release(impl=rel,
                                    title=rel.title,
                                    url=rel.html_url,
                                    sha=ref.object.sha)
            return release

        if isinstance(e.cause, exceptions.UpdateNotFastForwardException):
            e.cause.cause = 'You probably merged another PR to the {} branch before this execution ' \
                            'ended. This means you wont be able to release this commit. However, ' \
                            'the second PR will be released soon enough and contain this commit.' \
                .format(branch)

            log.echo(str(e))
            log.echo('Cleaning up...', add=True)
            ctx.invoke(delete_release, name=next_version)
            ctx.invoke(delete_tag, name=next_version)
            log.sub()

        raise

    return release


def _generate_changelog(gh, base, sha):

    def _pre_commit(_commit):
        log.echo('{}'.format(_commit.commit.message), break_line=False)

    def _pre_collect():
        log.echo('Collecting commits')

    def _pre_analyze(commits):
        log.echo('Analyzing {} commits'.format(len(commits)), add=True)

    def _post_commit():
        log.checkmark()

    def _post_analyze():
        log.sub()

    log.echo('Generating changelog', add=True)
    changelog = gh.generate_changelog(base=base, sha=sha,
                                      hooks={
                                          'pre_commit': _pre_commit,
                                          'pre_collect': _pre_collect,
                                          'pre_analyze': _pre_analyze,
                                          'post_analyze': _post_analyze,
                                          'post_commit': _post_commit
                                      })

    log.sub()

    log.echo('Changelog generation completed')

    return changelog
