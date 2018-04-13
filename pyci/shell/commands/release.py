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
from pyci.api.gh import GitHub
from pyci.api import logger
from pyci.api import utils
from pyci.api.packager import Packager
from pyci.api.pypi import PyPI
from pyci.shell import handle_exceptions, secrets


log = logger.get_logger(__name__)


# we disable it here because this really is a big function
# that does plenty of stuff, not many like these..
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
@click.command()
@handle_exceptions
@click.pass_context
@click.option('--repo', required=False)
@click.option('--branch', required=False)
@click.option('--sha', required=False)
@click.option('--no-binary', is_flag=True)
@click.option('--no-wheel', is_flag=True)
@click.option('--pypi-test', is_flag=True)
@click.option('--pypi-url', is_flag=True)
@click.option('--binary-entrypoint', required=False)
@click.option('--binary-name', required=False)
@click.option('--force', is_flag=True)
def release(ctx,
            repo,
            branch,
            sha,
            no_binary,
            no_wheel,
            binary_entrypoint,
            binary_name,
            pypi_test,
            pypi_url,
            force):

    ci = ctx.parent.ci

    log.debug('Detecting sha...')
    sha = sha or (ci.sha if ci else None)
    log.debug('Sha detected: {0}'.format(sha))

    def _do_release():

        release_title = None
        try:
            log.info('Creating release...')
            release_title = github.release(branch_name=branch_name, sha=sha)
            log.info('Successfully created release: {0}'.format(release_title))
        except exceptions.CommitIsAlreadyReleasedException as e:

            # this is ok, maybe someone is running the command on the same commit
            # over and over again. no need to error here since we still might have things
            # to do later on.
            log.info('The commit is already released: {0}, Moving on...'.format(e.release))

            # pylint: disable=fixme
            # TODO can there be a scenario where to concurrent releases
            # TODO are executed on the os? this will cause an override of the artifact...
            release_title = e.release
        except (exceptions.CommitNotRelatedToPullRequestException,
                exceptions.PullRequestNotRelatedToIssueException,
                exceptions.IssueIsNotLabeledAsReleaseException) as e:
            # not all commits are eligible for release, this is such a case.
            # we should just break and do nothing...
            log.info('Not releasing: {0}'.format(str(e)))

        # release_title may be None in case this commit should not
        # be released.
        if release_title:

            packager = Packager(repo=repo, sha=sha)

            if not no_binary:

                try:
                    log.info('Creating binary package...')
                    package = packager.binary(entrypoint=binary_entrypoint,
                                              name=binary_name)
                    log.info('Successfully created binary package: {0}'.format(package))

                    log.info('Uploading binary package to release...')
                    asset_url = github.upload(asset=package, release=release_title)
                    log.info('Successfully uploaded binary package to release: {0}'
                             .format(asset_url))

                except exceptions.EntrypointNotFoundException as ene:
                    # this is ok, the package doesn't contain an entrypoint in the
                    # expected default location. we should however print a log
                    # since the user might have expected the binary package (since the default is
                    #  to create one)
                    log.info('Binary package will not be created because an entrypoint was not '
                             'found in the expected path: {0}. \nYou can specify a custom '
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

                log.info('Uploading wheel to PyPI...')
                wheel_url = pypi.upload(wheel=package)
                log.info('Successfully uploaded wheel to PyPI: {0}'.format(wheel_url))

    if ci is None and not force:
        log.info('No CI system detected. If you wish to release nevertheless, '
                 'use the "--force" option.')
    else:

        try:

            log.debug('Detecting repo...')
            repo = detect_repo(ci, repo)
            log.debug('Repo detected: {0}'.format(repo))

            github = GitHub(repo=repo, access_token=secrets.github_access_token())

            log.debug('Detecting branch name...')
            branch_name = branch or (ci.branch if ci else github.default_branch)
            log.debug('Branch name detected: {0}'.format(branch_name))

            if ci:

                log.debug('Validating branch name with CI system: {0}'.format(branch_name))
                ci.validate_rc(branch_name)
                log.debug('Validation passed')

            _do_release()

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
