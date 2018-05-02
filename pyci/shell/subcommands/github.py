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
from pyci.api import logger
from pyci.api import utils
from pyci.api.model import Release, ChangelogCommit, Branch
from pyci.shell import BRANCH_HELP
from pyci.shell import MASTER_BRANCH_HELP
from pyci.shell import RELEASE_BRANCH_HELP
from pyci.shell import handle_exceptions

log = logger.get_logger(__name__)


@click.command('release')
@handle_exceptions
@click.pass_context
@click.option('--branch-name', required=False,
              help=BRANCH_HELP)
@click.option('--master-branch-name', required=False, default='master',
              help=MASTER_BRANCH_HELP)
@click.option('--release-branch-name', required=False, default='release',
              help=RELEASE_BRANCH_HELP)
@click.option('--force', is_flag=True,
              help='Force release without any validations.')
def release_branch(ctx, branch_name, master_branch_name, release_branch_name, force):

    """
    Release a branch.

    This command will do the following:

        1. Create a Github release with the version as its title. (With changelog)

        2. Create a commit bumping the version of setup.py on top of the branch.

        3. Update the master branch to point to the release commit.

        4. Close any issues related included in the changelog.

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
    executions. You can also safely run this command in parallel, this is important when running
    your CI process on multiple systems concurrently.

    """

    ci = ctx.parent.parent.ci

    sha = ci.sha if ci else None
    branch_name = branch_name or (ci.branch if ci else None)

    try:

        release_branch_internal(branch_name=branch_name,
                                master_branch_name=master_branch_name,
                                release_branch_name=release_branch_name,
                                force=force,
                                gh=ctx.parent.github,
                                ci=ci,
                                sha=sha)

    except exceptions.ReleaseValidationFailedException as e:
        log.info('Not releasing: {}'.format(str(e)))

    except exceptions.ApiException as e:
        err = click.ClickException('Failed releasing: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('validate-commit')
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False,
              help='Validate the last commit of this branch.')
@click.option('--sha', required=False,
              help='Validate this specific commit.')
def validate_commit(ctx, branch, sha):

    """
    Validate that a commit should be released.

    The conditions for release are:

        1. The commit is associated to an issue via the '#' sign in its message.

        2. The issue is marked with at least one of the release labels. (patch, minor, major).

    """

    if sha and branch:
        raise click.BadOptionUsage('Use either --sha or --branch, not both.')

    if not sha and not branch:
        raise click.BadOptionUsage('Must specify either --sha or --branch.')

    try:
        validate_commit_internal(branch=branch, sha=sha, gh=ctx.parent.github)
    except exceptions.ApiException as e:
        err = click.ClickException('Commit validation failed: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('validate-build')
@handle_exceptions
@click.pass_context
@click.option('--release-branch-name', required=True,
              help=RELEASE_BRANCH_HELP)
def validate_build(ctx, release_branch_name):

    """
    Validate the current build should be released.

    The conditions for release are:

        1. The current build is not a PR build.

        2. The current build is not a TAG build.

        3. The current build is running on the release branch.

    """

    ci = ctx.parent.parent.ci

    try:
        validate_build_internal(release_branch_name=release_branch_name, ci=ci)
    except exceptions.ApiException as e:
        err = click.ClickException('Build validation failed: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('generate-changelog')
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False,
              help='Generate for the last commit of this branch.')
@click.option('--sha', required=False,
              help='Generate for this specific commit.')
@click.option('--target', required=False, type=click.Path(exists=False),
              help='Path to the destination file. Defaults to ./<sha/branch>-changelog.md')
def generate_changelog(ctx, sha, branch, target):

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

    if sha and branch:
        raise click.BadOptionUsage('Use either --sha or --branch, not both.')

    if not sha and not branch:
        raise click.BadOptionUsage('Must specify either --sha or --branch.')

    try:

        default_destination = os.path.join(os.getcwd(), '{}-changelog.md'.format(sha or branch))
        target = target or default_destination
        destination = os.path.abspath(target)

        utils.validate_directory_exists(os.path.abspath(os.path.join(destination, os.pardir)))
        utils.validate_file_does_not_exist(destination)

        changelog = generate_changelog_internal(branch=branch, sha=sha, gh=ctx.parent.github)

        log.debug('Writing changelog file...', target=target, destination=destination)

        with open(destination, 'w') as stream:
            rendered = changelog.render()
            stream.write(rendered)

        log.info('Generated at {}'.format(destination))
    except exceptions.FileExistException as e:
        err = click.ClickException('Failed generating changelog: {}'.format(str(e)))
        err.possible_solutions = [
            'Delete/Move the file and try again'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.FileIsADirectoryException as e:
        err = click.ClickException('Failed generating changelog: {}'.format(str(e)))
        err.possible_solutions = [
            'Delete/Move the directory and try again'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.DirectoryDoesntExistException as e:
        err = click.ClickException('Failed generating changelog: {}'.format(str(e)))
        err.possible_solutions = [
            'Create the directory and try again'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.ApiException as e:
        err = click.ClickException('Failed generating changelog: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('create-release')
@handle_exceptions
@click.pass_context
@click.option('--branch', required=False,
              help='Release the last commit of this branch.')
@click.option('--sha', required=False,
              help='Release this specific commit.')
def create_release(ctx, sha, branch):

    """
    Create a release from a commit.

    The release title will be the version in setup.py of the specified commit.

    This command is NOT idempotent.

    """

    if sha and branch:
        raise click.BadOptionUsage('Use either --sha or --branch, not both.')

    if not sha and not branch:
        raise click.BadOptionUsage('Must specify either --sha or --branch.')

    try:
        create_release_internal(branch=branch, sha=sha, gh=ctx.parent.github)
    except exceptions.NotPythonProjectException as e:
        err = click.ClickException('Failed creating release: {}'.format(str(e)))
        err.possible_solutions = [
            'Please follow these instructions to create a standard '
            'python project --> https://packaging.python.org/tutorials/distributing-packages/'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.ApiException as e:
        err = click.ClickException('Failed creating release: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('upload-asset')
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
        upload_asset_internal(asset=asset, release=release, gh=ctx.parent.github)
    except exceptions.ApiException as e:
        err = click.ClickException('Failed uploading asset: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('upload-changelog')
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
        upload_changelog_internal(changelog=changelog, rel=release, gh=ctx.parent.github)
    except exceptions.ApiException as e:
        err = click.ClickException('Failed uploading changelog: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('detect-issue')
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
        raise click.BadOptionUsage('Use either --sha or --message, not both.')

    if not sha and not message:
        raise click.BadOptionUsage('Must specify either --sha or --message.')

    try:
        log.info('Detecting issue for {}'.format(sha or message))
        issue = ctx.parent.github.detect_issue(sha=sha, commit_message=message)
        if issue:
            log.info('Issue detected: {}'.format(issue.url))
        else:
            log.info('The commit is not related ot any issue.')
    except exceptions.ApiException as e:
        err = click.ClickException('Failed detecting issue: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('delete-release')
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
        log.info('Deleting release {0}...'.format(name))
        ctx.parent.github.delete_release(name=name)
        log.info('Deleted release: {}'.format(name))
    except exceptions.ApiException as e:
        err = click.ClickException('Failed deleting release: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('delete-tag')
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The name of the tag you want to delete.')
def delete_tag(ctx, name):

    """
    Delete a tag.

    """

    try:
        log.info('Deleting tag {0}...'.format(name))
        ctx.parent.github.delete_tag(name=name)
        log.info('Deleted tag: {}'.format(name))
    except exceptions.ApiException as e:
        err = click.ClickException('Failed deleting tag: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('bump-version')
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
        log.info('Bumping version of branch {}'.format(branch))
        bump = ctx.parent.github.bump_version(branch=branch, semantic=semantic)
        log.info('Bumped version from {} to {}'.format(bump.prev_version, bump.next_version))
    except exceptions.ApiException as e:
        err = click.ClickException('Failed bumping version: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('set-version')
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
        set_version_internal(branch=branch, value=value, gh=ctx.parent.github)
    except exceptions.ApiException as e:
        err = click.ClickException('Failed setting version: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('reset-branch')
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The branch name')
@click.option('--sha', required=True,
              help='The sha to reset the branch to.')
def reset_branch(ctx, name, sha):

    """
    Reset the specified branch to the given sha.

    This is equivalent to 'git reset --hard'

    """

    try:
        reset_branch_internal(name=name, sha=sha, gh=ctx.parent.github)
    except exceptions.ApiException as e:
        err = click.ClickException('Failed resetting branch: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('reset-tag')
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The tag name')
@click.option('--sha', required=True,
              help='The sha to reset the tag to.')
def reset_tag(ctx, name, sha):

    """
    Reset the specified branch to the given sha.

    This is equivalent to 'git reset --hard'

    """

    try:
        log.info('Resetting branch {} to sha {}'.format(name, sha))
        ctx.parent.github.reset_tag(name=name, sha=sha)
        log.info('Tag {} is now at {}.'.format(name, sha))
    except exceptions.ApiException as e:
        err = click.ClickException('Failed resetting tag: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('create-branch')
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
        create_branch_internal(name=name, sha=sha, gh=ctx.parent.github)
    except exceptions.ApiException as e:
        err = click.ClickException('Failed creating branch: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('delete-branch')
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The branch name')
def delete_branch(ctx, name):

    """
    Delete a branch.

    """

    try:
        delete_branch_internal(name=name, gh=ctx.parent.github)
    except exceptions.ApiException as e:
        err = click.ClickException('Failed deleting branch: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('commit-file')
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
def commit_file(ctx, branch, path, contents, message):

    """
    Commit a file remotely.

    """

    try:
        log.info('Committing file {}'.format(path))
        commit = ctx.parent.github.commit_file(
            path=path,
            contents=contents,
            message=message,
            branch=branch)
        log.info('Committed: {}'.format(commit.url))
    except exceptions.ApiException as e:
        err = click.ClickException('Failed committing file: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command('create-commit')
@handle_exceptions
@click.pass_context
@click.option('--branch', required=True,
              help='The last commit of this branch will be the parent of the created commit.')
@click.option('--path', required=True,
              help='Path to the file, relative to the repository root.')
@click.option('--contents', required=True,
              help='The new file contents.')
@click.option('--message', required=True,
              help='The commit message.')
def create_commit(ctx, branch, path, contents, message):

    """
    Create a commit in the repository.

    Note, this command does not actually update any reference to point to this commit.
    The created commit will be floating until you reset some reference to it.

    """

    try:
        log.info('Creating commit...')
        commit = ctx.parent.github.create_commit(path=path,
                                                 contents=contents,
                                                 message=message,
                                                 branch=branch)
        log.info('Created: {}'.format(commit.url))
    except exceptions.ApiException as e:
        err = click.ClickException('Failed creating commit: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


def generate_changelog_internal(branch, sha, gh):
    log.info('Generating changelog for {}... (this may take a while)'.format(sha or branch))
    changelog = gh.generate_changelog(branch=branch, sha=sha)
    return changelog


def set_version_internal(branch, value, gh):
    log.info('Setting version of branch {}'.format(branch))
    bump = gh.set_version(branch=branch, value=value)
    log.info('Version is now {} (was {})'.format(bump.next_version, bump.prev_version))
    return bump


def upload_changelog_internal(changelog, rel, gh):
    log.info('Uploading changelog to release {}..'.format(rel))
    utils.validate_file_exists(changelog)
    with open(changelog) as stream:
        rel = gh.upload_changelog(changelog=stream.read(), release=rel)
    log.info('Uploaded: {}'.format(rel.url))


def create_release_internal(branch, sha, gh):
    log.info('Creating a release from {}...'.format(sha or branch))
    release = gh.create_release(sha=sha, branch=branch)
    log.info('Release created: {}'.format(release.url))
    return release


def create_branch_internal(name, sha, gh):
    log.info('Creating branch {} from sha {}..'.format(name, sha))
    branch = gh.create_branch(name=name, sha=sha)
    log.info('Branch created: {}.'.format(name))
    return branch


def delete_branch_internal(name, gh):
    log.info('Deleting branch {}..'.format(name))
    branch = gh.delete_branch(name=name)
    log.info('Branch deleted: {}.'.format(name))
    return branch


def reset_branch_internal(name, sha, gh):
    log.info('Resetting branch {} to sha {}'.format(name, sha))
    gh.reset_branch(name=name, sha=sha)
    log.info('Branch {} is now at {}.'.format(name, sha))


def validate_commit_internal(branch, sha, gh):
    log.info('Validating {} should be released...'.format(sha or branch))
    gh.validate_commit(branch=branch, sha=sha)
    log.info('Validation passed!')


def validate_build_internal(release_branch_name, ci):

    log.info('Validating build...')
    if ci:
        ci.validate_build(release_branch=release_branch_name)
    log.info('Validation passed!')


def upload_asset_internal(asset, release, gh):
    log.info('Uploading asset {} to release {}.. (this may take a while)'.format(asset, release))
    asset_url = gh.upload_asset(asset=asset, release=release)
    log.info('Uploaded: {}'.format(asset_url))


# pylint: disable=too-many-locals
def release_branch_internal(branch_name,
                            master_branch_name,
                            release_branch_name,
                            force,
                            sha,
                            gh,
                            ci):

    log.info('Creating release from {}...'.format(sha or branch_name))

    if not force:

        validate_build_internal(ci=ci, release_branch_name=release_branch_name)
        validate_commit_internal(branch=None if sha else branch_name, gh=gh, sha=sha)

    changelog = generate_changelog_internal(branch=None if sha else branch_name, gh=gh, sha=sha)

    next_version = changelog.next_version

    if not next_version:
        raise exceptions.CannotDetermineNextVersionException(sha=sha)

    log.info('Creating floating version commit...')
    # figure out how to avoid calling private api here...
    # exposing this doesn't seem like a good solution either.
    # noinspection PyProtectedMember
    # pylint: disable=protected-access
    bump = gh._create_set_version_commit(value=next_version, branch=branch_name)
    actual_commit = bump.impl
    log.info('Created commit: {}'.format(actual_commit.sha))

    branch = None
    try:
        release_branch_name = 'releasing-{}'.format(changelog.sha)
        branch = _get_or_create_branch(actual_commit=actual_commit,
                                       gh=gh,
                                       branch_name=release_branch_name)
        release = _get_or_create_release(gh=gh,
                                         next_version=next_version,
                                         branch_name=release_branch_name)
    finally:
        if branch:
            delete_branch_internal(gh=gh, name=branch.name)

    bump_change = ChangelogCommit(title=actual_commit.message,
                                  url=actual_commit.html_url,
                                  timestamp=actual_commit.author.date,
                                  impl=actual_commit)
    changelog.add(bump_change)

    changelog_file = os.path.join(tempfile.mkdtemp(), 'changelog.md')
    with open(changelog_file, 'w') as stream:
        stream.write(changelog.render())
    upload_changelog_internal(changelog=changelog_file, gh=gh, rel=release.title)

    for issue in changelog.all_issues:
        log.info('Closing issue: {} ({})'.format(issue.title, issue.url))
        # figure out how to avoid calling private api here...
        # exposing this doesn't seem like a good solution either.
        # noinspection PyProtectedMember
        # pylint: disable=protected-access
        gh._close_issue(issue=issue.impl, release=release.impl)

    reset_branch_internal(gh=gh, name=branch_name, sha=release.sha)

    reset_branch_internal(gh=gh, name=master_branch_name, sha=release.sha)

    log.info('Successfully created release: {}'.format(release.url))

    return release


def _get_or_create_release(gh, next_version, branch_name):

    try:
        release = create_release_internal(branch=branch_name, gh=gh, sha=None)
    except exceptions.CommitIsAlreadyReleasedException as e:  # pragma: no cover

        # someone beat us to the punch.
        # lets just use the existing release.

        ref = gh.repo.get_git_ref(ref='tags/{}'.format(e.release))  # pragma: no cover
        rel = gh.repo.get_release(id=next_version)  # pragma: no cover
        release = Release(impl=rel,
                          title=rel.title,
                          url=rel.html_url,
                          sha=ref.object.sha)  # pragma: no cover

    return release


def _get_or_create_branch(actual_commit, gh, branch_name):

    try:
        branch = create_branch_internal(gh=gh, name=branch_name, sha=actual_commit.sha)
    except exceptions.BranchAlreadyExistsException:  # pragma: no cover

        # someone beat us to the punch.
        # lets just use the existing branch.

        ref = gh.get_git_ref(ref='heads/{}'.format(branch_name))  # pragma: no cover
        branch = Branch(impl=ref, sha=ref.object.sha, name=branch_name)  # pragma: no cover

    return branch
