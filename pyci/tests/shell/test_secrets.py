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
import contextlib
import os

import click
# noinspection PyPackageRequirements
import pytest

from pyci.shell import secrets


@contextlib.contextmanager
def env(key, value):

    current_value = os.environ.get(key)

    try:
        if value is None and key in os.environ:
            del os.environ[key]
        elif value is not None:
            os.environ[key] = value
        yield
    finally:
        if current_value is not None:
            os.environ[key] = current_value


def test_github_access_token():

    with env(secrets.GITHUB_ACCESS_TOKEN, 'token'):
        token = secrets.github_access_token()

        expected_token = 'token'

        assert expected_token == token


def test_github_access_token_none():

    with env(secrets.GITHUB_ACCESS_TOKEN, None):
        with pytest.raises(click.ClickException):
            secrets.github_access_token()


def test_twine_username():

    with env(secrets.TWINE_USERNAME, 'user'):
        token = secrets.twine_username()

        expected_token = 'user'

        assert expected_token == token


def test_twine_username_none():

    with env(secrets.TWINE_USERNAME, None):
        with pytest.raises(click.ClickException):
            secrets.twine_username()


def test_twine_password():

    with env(secrets.TWINE_PASSWORD, 'user'):
        token = secrets.twine_password()

        expected_token = 'user'

        assert expected_token == token


def test_twine_password_none():

    with env(secrets.TWINE_PASSWORD, None):
        with pytest.raises(click.ClickException):
            secrets.twine_password()
