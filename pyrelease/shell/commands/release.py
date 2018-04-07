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

from pyrelease.api.releaser import GithubReleaser
from pyrelease.shell import secrets


@click.command()
@click.option('--repo', required=True)
@click.option('--branch', required=False)
@click.option('--no-ci', is_flag=True)
def release(repo, branch, no_ci):

    travis_branch = os.environ.get('TRAVIS_BRANCH')

    if travis_branch:
        # we are running in travis.
        # make sure this is not a pull request build and that we are
        # running on the correct branch
        click.echo('Running inside CI system: Travis-CI')
        if os.environ.get('TRAVIS_PULL_REQUEST_BRANCH'):
            click.echo('The current build is a PR build, not releasing...')
            return
        if travis_branch != branch:
            click.echo('The current build branch ({0}) does not match the release branch ({1}), '
                       'not releasing...'.format(travis_branch, branch))
            return

        releaser = GithubReleaser(repo=repo,
                                  access_token=secrets.github_access_token())
        releaser.release(branch)

    else:

        # we are not running in a ci system. only release if explicitly specified
        if no_ci:
            releaser = GithubReleaser(repo=repo,
                                      access_token=secrets.github_access_token())
            releaser.release(branch)

        else:

            click.echo('No CI system detected. Not releasing...')
            click.echo('If you wish to release from your local machine, use the "--no-ci" flag')




@click.command()
@click.option('--repo', required=True)
@click.option('--version', required=True)
def delete(repo, version):

    releaser = GithubReleaser(repo=repo, access_token=secrets.github_access_token())
    releaser.delete(version)
