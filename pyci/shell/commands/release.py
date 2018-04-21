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

import click

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils
from pyci.api.gh import GitHub
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.shell import handle_exceptions, secrets
from pyci.shell import RELEASE_BRANCH_HELP
from pyci.shell import RELEASE_SHA_HELP
from pyci.shell import RELEASE_VERSION_HELP
from pyci.shell import REPO_HELP

log = logger.get_logger(__name__)


# we disable it here because this really is a big function
# that does plenty of stuff, not many like these..
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
@click.command()
@handle_exceptions
@click.pass_context
@click.option('--repo', required=False,
              help=REPO_HELP)
@click.option('--branch', required=False,
              help=RELEASE_BRANCH_HELP)
@click.option('--sha', required=False,
              help=RELEASE_SHA_HELP)
@click.option('--version', required=False,
              help=RELEASE_VERSION_HELP)
@click.option('--release-branch', required=False,
              help='The name of the branch from which releases should be made. Defaults to the '
                   'repository default branch. This is needed in order to silently ignore this '
                   'command when running on different branches.')
@click.option('--no-binary', is_flag=True,
              help='Do not create and upload a binary executable as part of the release process.')
@click.option('--binary-entrypoint', required=False,
              help='Path (relative to the repository root) of the file to be used as the '
                   'executable entry point. This corresponds to the positional script argument '
                   'passed to PyInstaller (https://pythonhosted.org/PyInstaller/usage.html)')
@click.option('--binary-name', required=False,
              help='The base name of the binary executable to be created. Note that the full '
                   'name will be a suffixed with platform specific info. This corresponds to '
                   'the --name option used by '
                   'PyInstaller (https://pythonhosted.org/PyInstaller/usage.html)')
@click.option('--no-wheel', is_flag=True,
              help='Do not create and upload a wheel package to PyPI as part of the release '
                   'process.')
@click.option('--pypi-test', is_flag=True,
              help='Use PyPI test index. This option is ignored if --no-wheel is used.')
@click.option('--pypi-url', is_flag=True,
              help='Specify a custom PyPI index url. This option is ignored if --no-wheel is '
                   'used.')
@click.option('--no-ci', is_flag=True,
              help='Instructs me to execute this command even though its not running inside a CI '
                   'system.')
@click.option('--force', is_flag=True,
              help='Instructs me to execute this command even if the specific commit does not '
                   'meet the release requirements.')
def release(ctx,
            repo,
            sha,
            branch,
            version,
            release_branch,
            no_binary,
            no_wheel,
            binary_entrypoint,
            binary_name,
            pypi_test,
            pypi_url,
            no_ci,
            force):

    """
    Execute a complete release process.

    This command wil have the following affects:

        1. Github release with the version as its title. (With changelog)

        2. A version bump commit to setup.py in the corresponding branch.

        3. Platform dependent binary executable uploaded to the release. (Optional)

        4. Wheel package uploaded to PyPI (Optional)

    In order for the commit to be released, it must meet the following requirements:

        - The current build is a not a PR build. (Applicable only in CI)

        - The current build is a not a tag build (Applicable only in CI)

        - The current build branch differs from the release branch (Applicable only in CI)

        - The commit is not related to any issue.

        - The issue related to the commit is not a release candidate.

    If the commit does not meet any of these requirements, the command will simply return
    successfully and won't do anything. (it will not fail).

    """

    # pylint: disable=too-many-branches
    def _do_release():

        release_title = None
        try:

            log.debug('Releasing sha: {0}'.format(sha))

            if not force:
                log.debug('Validating this commit is eligible for release...')
                github.validate_commit(branch=branch, sha=sha)
                log.debug('Validation passed')

            log.info('Creating release...')
            release_title = github.create_release(branch=branch,
                                                  sha=sha,
                                                  version=version)
            log.info('Successfully created release: {0}'.format(release_title))

            github.reset_branch(branch='master', sha=release.sha)

        except exceptions.CommitIsAlreadyReleasedException as e:

            # this is ok, maybe someone is running the command on the same commit
            # over and over again. no need to error here since we still might have things
            # to do later on.
            log.info('The commit ({0}) is already released: {1}, Moving on...'.format(
                e.sha, e.release))

            # pylint: disable=fixme
            # TODO can there be a scenario where to concurrent releases
            # TODO are executed on the os? this will cause an override of the artifact...
            release_title = e.release
        except (exceptions.CommitNotRelatedToIssueException,
                exceptions.IssueIsNotLabeledAsReleaseException) as e:
            # not all commits are eligible for release, this is such a case.
            # we should just break and do nothing...
            log.info('Not releasing: {0}'.format(str(e)))

        # release_title may be None in case this commit should not
        # be released.
        if release_title:

            packager = Packager(repo=repo, sha=release_title)

            if not no_binary:

                try:
                    log.info('Creating binary package...')
                    package = packager.binary(entrypoint=binary_entrypoint,
                                              name=binary_name)
                    log.info('Successfully created binary package: {0}'.format(package))

                    log.info('Uploading binary package to release...')
                    try:
                        asset_url = github.upload_asset(asset=package, release=release_title)
                        log.info('Successfully uploaded binary package to release: {0}'
                                 .format(asset_url))
                    except exceptions.AssetAlreadyPublishedException:
                        log.info('Binary package already published in release. Moving on...')
                    finally:
                        os.remove(package)

                except exceptions.DefaultEntrypointNotFoundException as ene:
                    # this is ok, the package doesn't contain an entrypoint in the
                    # expected default location. we should however print a log
                    # since the user might have expected the binary package (since the default is
                    #  to create one)
                    log.info('Binary package will not be created because an entrypoint was not '
                             'found in the expected path: {}. \nYou can specify a custom '
                             'entrypoint path by using the "--binary-entrypoint" option.\n'
                             'If your package is not meant to be an executable binary, '
                             'use the "--no-binary" flag to avoid seeing this message'
                             .format(ene.expected_paths))

            if not no_wheel:

                log.info('Creating wheel...')
                package = packager.wheel()
                log.info('Successfully created wheel: {0}'.format(package))

                pypi = PyPI(repository_url=pypi_url,
                            test=pypi_test,
                            username=secrets.twine_username(),
                            password=secrets.twine_password())

                try:
                    log.info('Uploading wheel to PyPI...')
                    wheel_url = pypi.upload(wheel=package)
                    log.info('Successfully uploaded wheel to PyPI: {0}'.format(wheel_url))
                except exceptions.WheelAlreadyPublishedException as e:
                    log.info('Wheel package already published in {0}. Moving on...'.format(e.url))
                finally:
                    os.remove(package)

    ci = ctx.parent.ci

    if ci is None and not no_ci:
        log.info('No CI system detected. If you wish to release nevertheless, '
                 'use the "--no-ci" option.')
    else:

        try:

            log.debug('Detecting repo...')
            repo = detect_repo(ci, repo)
            log.debug('Repo detected: {0}'.format(repo))

            github = GitHub(repo=repo, access_token=secrets.github_access_token())

            branch = branch or (ci.branch if ci else None) or github.default_branch_name
            sha = sha or branch or ci.sha or github.default_branch_name

            log.debug('Detecting release branch name...')
            release_branch = release_branch or github.default_branch_name
            log.debug('Release branch name detected: {0}'.format(release_branch))

            if ci and not force:

                log.debug('Validating release candidacy with CI system for branch: {0}'
                          .format(release_branch))
                ci.validate_rc(release_branch)
                log.debug('Validation passed')

            if not ci:
                log.debug('Skipped CI validation since we are not running inside a CI system.')

            if not force:
                log.debug('Skipped CI validation since --force was used.')

            _do_release()
            log.info('Done!')

        except exceptions.NotReleaseCandidateException as nrce:
            log.info('No need to release this commit: {0}'.format(str(nrce)))


def detect_repo(ci, repo):

    repo = repo or (ci.repo if ci else utils.get_local_repo())
    if repo is None:
        raise click.ClickException(message='Failed detecting repository name. Please provide it '
                                           'using the "--repo" option.\nIf you are running '
                                           'locally, you can also execute this command from your '
                                           'project root directory (repository will be detected '
                                           'using git).')
    return repo
