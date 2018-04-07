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

from pyci.api import exceptions, ci
from pyci.api import utils
from pyci.api import model
from pyci.shell import BRANCH_HELP
from pyci.shell import MASTER_BRANCH_HELP
from pyci.shell import RELEASE_BRANCH_HELP
from pyci.shell import handle_exceptions
from pyci.shell.logger import get as get_logger

log = get_logger()


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

    ci_provider = ctx.parent.parent.ci_provider

    branch_name = branch_name or (ci_provider.branch if ci_provider else None)

    try:

        release = release_branch_internal(
            branch_name=branch_name,
            master_branch_name=master_branch_name,
            release_branch_name=release_branch_name,
            force=force,
            gh=ctx.parent.github,
            ci_provider=ci_provider)
        log.echo('Successfully released: {}'.format(release.url))
    except exceptions.ReleaseValidationFailedException as e:
        log.sub()
        log.echo("Not releasing: {}".format(str(e)))


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

    validate_commit_internal(branch=branch, sha=sha, gh=ctx.parent.github)
    log.echo('Validation passed')


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

    ci_provider = ctx.parent.parent.ci_provider

    validate_build_internal(release_branch_name=release_branch_name, ci_provider=ci_provider)
    log.echo('Validation passed')


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

    default_destination = os.path.join(os.getcwd(), '{}-changelog.md'.format(sha or branch))
    target = target or default_destination
    destination = os.path.abspath(target)

    utils.validate_directory_exists(os.path.abspath(os.path.join(destination, os.pardir)))
    utils.validate_file_does_not_exist(destination)

    changelog = generate_changelog_internal(branch=branch, sha=sha, gh=ctx.parent.github)

    log.echo('Writing changelog file')

    with open(destination, 'w') as stream:
        rendered = changelog.render()
        stream.write(rendered)

    log.echo('Generated at {}'.format(destination))


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
        release = create_release_internal(branch=branch, sha=sha, gh=ctx.parent.github)
        log.echo('Release created: {}'.format(release.url))
    except exceptions.NotPythonProjectException as e:
        err = click.ClickException(str(e))
        err.possible_solutions = [
            'Please follow these instructions to create a standard '
            'python project --> https://packaging.python.org/tutorials/distributing-packages/'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


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

    url = upload_asset_internal(asset=asset, release=release, gh=ctx.parent.github)
    log.echo('Uploaded asset: {}'.format(url))


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

    upload_changelog_internal(changelog=changelog, rel=release, gh=ctx.parent.github)
    log.echo('Uploaded changelog to release {}'.format(release))


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
        log.echo('Detecting issue...', break_line=False)
        issue = ctx.parent.github.detect_issue(sha=sha, commit_message=message)
        log.checkmark()
        if issue:
            log.echo('Issue detected: {}'.format(issue.url))
        else:
            log.echo('The commit is not related ot any issue.')
    except:
        log.xmark()
        raise


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

    delete_release_internal(gh=ctx.parent.github, name=name)
    log.echo('Done')


@click.command('delete-tag')
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The name of the tag you want to delete.')
def delete_tag(ctx, name):

    """
    Delete a tag.

    """

    delete_tag_internal(gh=ctx.parent.github, name=name)
    log.echo('Done')


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
        log.echo('Bumping version...', break_line=False)
        bump = ctx.parent.github.bump_version(branch=branch, semantic=semantic)
        log.checkmark()
        log.echo('Bumped version from {} to {}'.format(bump.prev_version, bump.next_version))
    except:
        log.xmark()
        raise


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

    bump = set_version_internal(branch=branch, value=value, gh=ctx.parent.github)
    log.echo('Version is now {} (was {})'.format(bump.next_version, bump.prev_version))


@click.command('reset-branch')
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

    reset_branch_internal(name=name, sha=sha, hard=hard, gh=ctx.parent.github)
    log.echo('Branch {} is now at {}'.format(name, sha))


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

    This is equivalent to 'git reset'

    """

    try:
        log.echo('Updating tag...', break_line=False)
        ctx.parent.github.reset_tag(name=name, sha=sha)
        log.checkmark()
        log.echo('Tag {} is now at {}'.format(name, sha))
    except:
        log.xmark()
        raise


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

    create_branch_internal(name=name, sha=sha, gh=ctx.parent.github)
    log.echo('Branch {} created at {}'.format(name, sha))


@click.command('delete-branch')
@handle_exceptions
@click.pass_context
@click.option('--name', required=True,
              help='The branch name')
def delete_branch(ctx, name):

    """
    Delete a branch.

    """

    delete_branch_internal(name=name, gh=ctx.parent.github)
    log.echo('Done')


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
        log.echo('Committing file...', break_line=False)
        commit = ctx.parent.github.commit_file(
            path=path,
            contents=contents,
            message=message,
            branch=branch)
        log.checkmark()
        log.echo('Created commit: {}'.format(commit.url))
    except:
        log.xmark()
        raise


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
        log.echo('Creating commit...', break_line=False)
        commit = ctx.parent.github.create_commit(path=path,
                                                 contents=contents,
                                                 message=message,
                                                 branch=branch)
        log.checkmark()
        log.echo('Created commit: {}'.format(commit.url))
    except:
        log.xmark()
        raise


@click.command('close-issue')
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

    close_issue_internal(number=number, release=release, gh=ctx.parent.github)
    log.echo('Done')


def delete_release_internal(gh, name):
    try:
        log.echo('Deleting release...', break_line=False)
        gh.delete_release(name=name)
        log.checkmark()
    except:
        log.xmark()
        raise


def delete_tag_internal(gh, name):
    try:
        log.echo('Deleting tag...', break_line=False)
        gh.delete_tag(name=name)
        log.checkmark()
    except:
        log.xmark()
        raise


def close_issue_internal(number, release, gh):

    try:
        log.echo('Closing issue number {}...'.format(number), break_line=False)
        gh.close_issue(num=number, release=release)
        log.checkmark()
    except:
        log.xmark()
        raise


def generate_changelog_internal(branch, sha, gh):

    def _pre_commit(commit):
        log.echo('{}'.format(commit.commit.message), break_line=False)

    def _pre_collect():
        log.echo('Collecting commits')

    def _pre_analyze(commits):
        log.echo('Analyzing {} commits'.format(len(commits)), add=True)

    def _post_commit():
        log.checkmark()

    def _post_analyze():
        log.sub()

    log.echo('Generating changelog', add=True)
    changelog = gh.generate_changelog(branch=branch, sha=sha,
                                      hooks={
                                          'pre_commit': _pre_commit,
                                          'pre_collect': _pre_collect,
                                          'pre_analyze': _pre_analyze,
                                          'post_analyze': _post_analyze,
                                          'post_commit': _post_commit
                                      })
    log.sub()
    return changelog


def set_version_internal(branch, value, gh):

    try:
        log.echo('Setting version...', break_line=False)
        bump = gh.set_version(branch=branch, value=value)
        log.checkmark()
        return bump
    except:
        log.xmark()
        raise


def upload_changelog_internal(changelog, rel, gh):

    try:
        log.echo('Uploading changelog...', break_line=False)
        utils.validate_file_exists(changelog)
        with open(changelog) as stream:
            gh.upload_changelog(changelog=stream.read(), release=rel)
        log.checkmark()
    except:
        log.xmark()
        raise


def create_release_internal(branch, sha, gh):
    log.echo('Creating a GitHub release')
    release = gh.create_release(sha=sha, branch=branch)
    return release


def create_branch_internal(name, sha, gh):

    try:
        log.echo('Creating branch...', break_line=False)
        branch = gh.create_branch(name=name, sha=sha)
        log.checkmark()
        return branch
    except:
        log.xmark()
        raise


def delete_branch_internal(name, gh):

    try:
        log.echo('Deleting branch...', break_line=False)
        branch = gh.delete_branch(name=name)
        log.checkmark()
        return branch
    except:
        log.xmark()
        raise


def reset_branch_internal(name, sha, hard, gh):

    try:
        log.echo("Updating {} branch...".format(name), break_line=False)
        gh.reset_branch(name=name, sha=sha, hard=hard)
        log.checkmark()
    except:
        log.xmark()
        raise


def validate_commit_internal(branch, sha, gh):

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
        gh.validate_commit(branch=branch, sha=sha,
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


def validate_build_internal(release_branch_name, ci_provider):

    def _pre_pr():
        log.echo('Build is not a PR...', break_line=False)

    def _post_pr():
        log.checkmark()

    def _pre_tag():
        log.echo('Build is not a TAG...', break_line=False)

    def _post_tag():
        log.checkmark()

    def _pre_branch():
        log.echo("Build branch is '{}'...".format(release_branch_name), break_line=False)

    def _post_branch():
        log.checkmark()

    if ci_provider:
        log.echo('Validating build {}'.format(ci_provider.build_url), add=True)
        try:
            ci.validate_build(ci_provider=ci_provider, release_branch=release_branch_name,
                              hooks={
                                  'pre_pr': _pre_pr,
                                  'pre_tag': _pre_tag,
                                  'pre_branch': _pre_branch,
                                  'post_pr': _post_pr,
                                  'post_tag': _post_tag,
                                  'post_branch': _post_branch
                              })
            log.sub()
        except:
            log.xmark()
            log.sub()
            raise


def upload_asset_internal(asset, release, gh):

    try:
        log.echo('Uploading {}...'.format(os.path.basename(asset)), break_line=False)
        asset_url = gh.upload_asset(asset=asset, release=release)
        log.checkmark()
        return asset_url
    except:
        log.xmark()
        raise


def release_branch_internal(branch_name,
                            master_branch_name,
                            release_branch_name,
                            force,
                            gh,
                            ci_provider):

    sha = ci_provider.sha if ci_provider else None

    log.echo("Releasing branch '{}'".format(branch_name), add=True)

    if not force:

        validate_build_internal(ci_provider=ci_provider, release_branch_name=release_branch_name)
        validate_commit_internal(branch=None if sha else branch_name, gh=gh, sha=sha)

    changelog = generate_changelog_internal(gh=gh,
                                            branch=None if sha else branch_name,
                                            sha=sha)

    if not changelog.next_version:

        err = click.ClickException('None of the commits in the changelog references an issue '
                                   'labeled with a release label. Cannot determine what the '
                                   'version number should be.')
        err.cause = 'You probably only committed internal issues since the last release, ' \
                    'or forgot to reference the issue.'
        err.possible_solutions = [
            'Amend the message of one the commits to reference a release issue',
            'Push another commit that references a release issue'
        ]

        raise err

    try:
        release = _create_release(gh=gh,
                                  changelog=changelog,
                                  branch_name=branch_name,
                                  master_branch_name=master_branch_name,
                                  sha=sha)
        _close_issues(gh=gh,
                      changelog=changelog,
                      release=release.title)

        log.sub()

        return release

    except exceptions.UpdateNotFastForwardException as e:

        e.cause = 'You probably merged another PR to the {} branch before this execution ' \
                  'ended. This means you wont be able to release this commit. However, ' \
                  'the second PR will be released soon enough and contain this commit.' \
                  ''.format(release_branch_name)

        tb = sys.exc_info()[2]
        utils.raise_with_traceback(e, tb)


def _create_release(gh, changelog, branch_name, master_branch_name, sha):

    try:

        # figure out how to avoid calling private api here...
        # exposing this doesn't seem like a good solution either.
        # noinspection PyProtectedMember
        # pylint: disable=protected-access
        commit = gh._create_set_version_commit(value=changelog.next_version,
                                               branch=branch_name,
                                               sha=sha).impl

        release = create_release_internal(branch=None, gh=gh, sha=commit.sha)

        bump = model.ChangelogCommit(title=commit.message,
                                     url=commit.html_url,
                                     timestamp=commit.author.date,
                                     impl=commit)
        changelog.add(bump)

        changelog_file = os.path.join(tempfile.mkdtemp(), 'changelog.md')
        with open(changelog_file, 'w') as stream:
            stream.write(changelog.render())
        upload_changelog_internal(changelog=changelog_file, gh=gh, rel=release.title)

        try:
            log.echo('Bumping version to {}'.format(changelog.next_version))
            reset_branch_internal(gh=gh, name=branch_name, sha=commit.sha, hard=False)
            if master_branch_name != branch_name:
                reset_branch_internal(gh=gh, name=master_branch_name, sha=commit.sha, hard=False)
        except exceptions.UpdateNotFastForwardException as e:
            log.echo(str(e))
            log.echo('Cleaning up', add=True)
            delete_release_internal(gh=gh, name=release.title)
            delete_tag_internal(gh=gh, name=release.title)
            log.sub()
            raise

    except exceptions.ReleaseAlreadyExistsException as e:
        log.echo('Release {} already exists'.format(e.release))
        ref = gh.repo.get_git_ref(ref='tags/{}'.format(e.release))
        rel = gh.repo.get_release(id=changelog.next_version)
        release = model.Release(impl=rel,
                                title=rel.title,
                                url=rel.html_url,
                                sha=ref.object.sha)

    return release


def _close_issues(gh, changelog, release):
    log.echo('Closing issues', add=True)
    for issue in changelog.all_issues:
        close_issue_internal(number=issue.impl.number, release=release, gh=gh)
    log.sub()
