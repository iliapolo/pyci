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

TWINE_PASSWORD = 'TWINE_PASSWORD'
TWINE_USERNAME = 'TWINE_USERNAME'
GITHUB_ACCESS_TOKEN = 'GITHUB_ACCESS_TOKEN'


def github_access_token(ci_provider):

    if GITHUB_ACCESS_TOKEN in os.environ:
        return os.environ[GITHUB_ACCESS_TOKEN]

    if not ci_provider:
        return click.prompt('Enter Github access token:', hide_input=True)  # pragma: no cover

    raise click.ClickException('Please provide a github access token by setting the '
                               '{} env variable.'.format(GITHUB_ACCESS_TOKEN))


def twine_username(ci_provider):

    if TWINE_USERNAME in os.environ:
        return os.environ[TWINE_USERNAME]

    if not ci_provider:
        return click.prompt('Enter twine username:', hide_input=True)  # pragma: no cover

    raise click.ClickException('Please provide a pypi username by setting the '
                               '{} env variable.'.format(TWINE_USERNAME))


def twine_password(ci_provider):

    if TWINE_PASSWORD in os.environ:
        return os.environ[TWINE_PASSWORD]

    if not ci_provider:
        return click.prompt('Enter twine password:', hide_input=True)  # pragma: no cover

    raise click.ClickException('Please provide a pypi password by setting the '
                               '{} env variable.'.format(TWINE_PASSWORD))
