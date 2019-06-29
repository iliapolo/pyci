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
import platform

import pytest

try:
    # python2
    from mock import MagicMock
    from mock import ANY
except ImportError:
    # python3
    # noinspection PyUnresolvedReferences,PyCompatibility
    from unittest.mock import MagicMock
    from unittest.mock import ANY

from pyci.tests.conftest import LAST_COMMIT


@pytest.mark.wet
@pytest.mark.record(platform=True)
def test_release(release, temp_dir, mocker):

    release_options = '--pypi-test --binary-entrypoint {}'.format(
        os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py'))

    expected_binary_name = 'pyci-guinea-pig.binary'
    expected_wheel_name = 'pyci-guinea-pig.whl'

    binary_path = os.path.join(temp_dir, expected_binary_name)
    wheel_path = os.path.join(temp_dir, expected_wheel_name)

    # This mock has to create a file with the proper name
    # since the file is actually uploaded to the release.
    def _binary(*_, **__):

        with open(binary_path, 'w') as f:
            f.write('binary')

        return binary_path

    # This mock can create whatever file it wants since it not
    # being uploaded anywhere, nor is it being asserted on.
    def _wheel(*_, **__):

        with open(wheel_path, 'w') as f:
            f.write('wheel')

        return wheel_path

    # This mock can return anything it wants since this URL is not being
    # asserted upon.
    def _upload(*_, **__):
        return 'http://this-is-an-upload-url'

    mocker.patch(target='pyci.api.packager.Packager.binary', side_effect=_binary)
    mocker.patch(target='pyci.api.packager.Packager.wheel', side_effect=_wheel)
    mocker.patch(target='pyci.api.pypi.PyPI.upload', side_effect=_upload)

    release.run('--branch-name release {}'.format(release_options))

    github_release = release.github.api.repo.get_release(id='1.0.0')

    assets = [asset.name for asset in github_release.get_assets()]
    assert expected_binary_name in assets
    assert expected_wheel_name in assets

    from pyci.api.pypi import PyPI

    # noinspection PyUnresolvedReferences
    PyPI.upload.assert_called_once_with(wheel=wheel_path)  # pylint: disable=no-member


@pytest.mark.wet
@pytest.mark.record(platform=True)
def test_release_no_wheel_publish(release, temp_dir, mocker):

    release_options = '--no-wheel-publish --binary-entrypoint {}'.format(
        os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py'))

    expected_binary_name = 'pyci-guinea-pig.binary'
    expected_wheel_name = 'pyci-guinea-pig.whl'

    binary_path = os.path.join(temp_dir, expected_binary_name)
    wheel_path = os.path.join(temp_dir, expected_wheel_name)

    # This mock has to create a file with the proper name
    # since the file is actually uploaded to the release.
    def _binary(*_, **__):

        with open(binary_path, 'w') as f:
            f.write('binary')

        return binary_path

    # This mock can create whatever file it wants since it not
    # being uploaded anywhere, nor is it being asserted on.
    def _wheel(*_, **__):

        with open(wheel_path, 'w') as f:
            f.write('wheel')

        return wheel_path

    # This mock can return anything it wants since this URL is not being
    # asserted upon.
    def _upload(*_, **__):
        return 'http://this-is-an-upload-url'

    mocker.patch(target='pyci.api.packager.Packager.binary', side_effect=_binary)
    mocker.patch(target='pyci.api.packager.Packager.wheel', side_effect=_wheel)
    mocker.patch(target='pyci.api.pypi.PyPI.upload', side_effect=_upload)

    release.run('--branch-name release {}'.format(release_options))

    github_release = release.github.api.repo.get_release(id='1.0.0')

    assets = [asset.name for asset in github_release.get_assets()]
    assert expected_binary_name in assets
    assert expected_wheel_name in assets

    from pyci.api.pypi import PyPI

    # noinspection PyUnresolvedReferences
    PyPI.upload.assert_not_called()  # pylint: disable=no-member


@pytest.mark.wet
@pytest.mark.record(platform=True)
def test_release_twice(release, mocker, temp_dir):

    release_options = '--pypi-test --binary-entrypoint {}'.format(
        os.path.join('pyci_guinea_pig', 'shell', 'custom_main.py'))

    expected_binary_name = 'pyci-guinea-pig-{}-{}'.format(platform.machine(), platform.system())
    if platform.system().lower() == 'windows':
        expected_binary_name = '{0}.exe'.format(expected_binary_name)

    # This mock has to create a file with the proper name
    # since the file is actually uploaded to the release.
    def _binary(*_, **__):

        binary_path = os.path.join(temp_dir, expected_binary_name)

        with open(binary_path, 'w') as f:
            f.write('binary')

        return binary_path

    # This mock can create whatever file it wants since it not
    # being uploaded anywhere, nor is it being asserted on.
    def _wheel(*_, **__):

        binary_path = os.path.join(temp_dir, 'pyci-guinea-pig.whl')

        with open(binary_path, 'w') as f:
            f.write('wheel')

        return binary_path

    # This mock can return anything it wants since this URL is not being
    # asserted upon.
    def _upload(*_, **__):
        return 'http://this-is-an-upload-url'

    mocker.patch(target='pyci.api.packager.Packager.binary', side_effect=_binary)
    mocker.patch(target='pyci.api.packager.Packager.wheel', side_effect=_wheel)
    mocker.patch(target='pyci.api.pypi.PyPI.upload', side_effect=_upload)

    release.run('--branch-name release {}'.format(release_options))

    release.github.api.reset_branch(name='release', sha=LAST_COMMIT, hard=True)
    release.github.api.reset_branch(name='master', sha=LAST_COMMIT, hard=True)

    release.run('--branch-name release {}'.format(release_options))

    expected_number_of_releases = 1

    assert expected_number_of_releases == len(list(release.github.api.repo.get_releases()))


@pytest.mark.skip('Need to create a specific commit to fit this use case')
@pytest.mark.wet
def test_release_default_entrypoint_not_found(release):

    sha = 'cf2d64132f00c849ae1bb62ffb2e32b719b6cbac'
    release.github.api.reset_branch(name='release', sha=sha, hard=True)
    release.github.api.reset_branch(name='master', sha=sha, hard=True)

    release.github.api.commit_file(path='README.md',
                                   message='Release (#7)',
                                   branch='release',
                                   contents='contents')

    result = release.run('--branch-name release', catch_exceptions=True)

    expected_message = 'Binary package will not be created'

    assert expected_message in result.std_out
    release.github.api.repo.get_release(id='1.0.0')


@pytest.mark.wet
def test_release_validation_failed(release):

    sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'
    release.github.api.reset_branch(name='release', sha=sha, hard=True)

    result = release.run('--branch-name release', catch_exceptions=True)

    expected_output = 'Not releasing: Commit {} does not reference any issue'.format(sha)

    assert expected_output in result.std_out


def test_release_options(release, mocker):

    def _release_internal(*_, **__):
        return MagicMock(), MagicMock()

    mocker.patch(target='pyci.shell.commands.release.release_internal', side_effect=_release_internal)
    mocker.patch(target='pyci.api.packager.Packager.create', new=MagicMock())

    release.run('--branch-name release '
                '--no-binary '
                '--no-wheel '
                '--changelog-base base '
                '--version 1.2.3 '
                '--no-wheel-publish')

    from pyci.shell.commands import release

    # noinspection PyUnresolvedReferences
    release.release_internal.assert_called_once_with(  # pylint: disable=no-member

        binary_entrypoint=ANY,
        branch_name='release',
        ci=ANY,
        force=False,
        master_branch_name='master',
        no_binary=True,
        no_wheel=True,
        pypi_test=False,
        pypi_url=ANY,
        release_branch_name='release',
        repo=ANY,
        wheel_universal=False,
        pyinstaller_version=ANY,
        wheel_version=ANY,
        changelog_base='base',
        no_wheel_publish=True,
        version='1.2.3')


def test_release_failed(release):

    result = release.run('--branch-name doesnt-exist', catch_exceptions=True)

    expected_output = 'Commit not found: doesnt-exist'

    assert expected_output in result.std_out
