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

import platform
import os

# noinspection PyPackageRequirements
import pytest
from mock import MagicMock

from pyci.api import exceptions
from pyci.tests.conftest import REPO_UNDER_TEST


@pytest.mark.wet
def test_release(pyci, repo):

    pyci.run('--debug --no-ci release --repo {} --branch-name release --pypi-test '
             '--binary-entrypoint {}'
             .format(REPO_UNDER_TEST, os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py')))

    github_release = repo.get_release(id='1.0.0')

    expected_asset_name = 'pyci-guinea-pig-{}-{}'.format(platform.machine(), platform.system())

    assets = [asset.name for asset in github_release.get_assets()]

    assert expected_asset_name in assets


def test_release_validation_failed(pyci, capture, mocker):

    exception = exceptions.ReleaseValidationFailedException('error')

    mocker.patch(target='pyci.shell.commands.release.release_internal',
                 new=MagicMock(side_effect=exception))

    pyci.run('--debug --no-ci release --repo {} --branch-name release --pypi-test '
             '--binary-entrypoint {}'
             .format(REPO_UNDER_TEST, os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py')),
             catch_exceptions=True)

    expected_output = 'Not releasing: error'

    assert expected_output == capture.records[0].msg


def test_release_failed(pyci, capture, mocker):

    exception = exceptions.ApiException('error')

    mocker.patch(target='pyci.shell.commands.release.release_internal',
                 new=MagicMock(side_effect=exception))

    pyci.run('--debug --no-ci release --repo {} --branch-name release --pypi-test '
             '--binary-entrypoint {}'
             .format(REPO_UNDER_TEST, os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py')),
             catch_exceptions=True)

    expected_output = 'Failed releasing: error'

    assert expected_output == capture.records[1].msg


@pytest.mark.wet
def test_release_wheel_already_published(pyci, repo, mocker):

    exception = exceptions.WheelAlreadyPublishedException(wheel='wheel', url='url')

    mocker.patch(target='pyci.shell.subcommands.pypi.upload_internal',
                 new=MagicMock(side_effect=exception))

    pyci.run('--debug --no-ci release --repo {} --branch-name release --pypi-test '
             '--binary-entrypoint {}'
             .format(REPO_UNDER_TEST, os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py')),
             catch_exceptions=True)

    github_release = repo.get_release(id='1.0.0')

    expected_asset_name = 'pyci-guinea-pig-{}-{}'.format(platform.machine(), platform.system())

    assets = [asset.name for asset in github_release.get_assets()]

    assert expected_asset_name in assets


@pytest.mark.wet
def test_release_asset_already_published(pyci, repo, mocker):

    exception = exceptions.AssetAlreadyPublishedException(asset='asset', release='release')

    mocker.patch(target='pyci.shell.subcommands.github.upload_asset_internal',
                 new=MagicMock(side_effect=exception))

    pyci.run('--debug --no-ci release --repo {} --branch-name release --pypi-test '
             '--binary-entrypoint {}'
             .format(REPO_UNDER_TEST, os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py')),
             catch_exceptions=True)

    github_release = repo.get_release(id='1.0.0')

    expected_asset_name = 'pyci-guinea-pig-{}-{}'.format(platform.machine(), platform.system())

    assets = [asset.name for asset in github_release.get_assets()]

    assert expected_asset_name not in assets


@pytest.mark.wet
def test_release_default_entrypoint_not_found(pyci, repo, capture, mocker):

    exception = exceptions.DefaultEntrypointNotFoundException(repo='repo', name='name',
                                                              expected_paths=['path'])

    mocker.patch(target='pyci.shell.subcommands.pack.binary_internal',
                 new=MagicMock(side_effect=exception))

    pyci.run('--debug --no-ci release --repo {} --branch-name release --pypi-test '
             '--binary-entrypoint {}'
             .format(REPO_UNDER_TEST, os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py')),
             catch_exceptions=True)

    github_release = repo.get_release(id='1.0.0')

    expected_asset_name = 'pyci-guinea-pig-{}-{}'.format(platform.machine(), platform.system())

    assets = [asset.name for asset in github_release.get_assets()]

    expected_message = "Binary package will not be created"
    assert expected_asset_name not in assets
    assert expected_message in capture.records[26].msg
