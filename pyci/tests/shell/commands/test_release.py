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

import pytest

from pyci.tests.conftest import LAST_COMMIT


@pytest.mark.wet
# pylint: disable=too-many-locals
def test_release(release, temp_dir, mocker):

    expected_entrypoint = 'entrypoint'
    expected_author = 'author'
    expected_website = 'website'
    expected_license_path = 'license-path'
    expected_copyr = 'copyr'

    release_options = '--pypi-test ' \
                      '--author {} ' \
                      '--website {} ' \
                      '--license-path {} ' \
                      '--copyr {} ' \
                      '--binary-entrypoint {}'.format(expected_author,
                                                      expected_website,
                                                      expected_license_path,
                                                      expected_copyr,
                                                      expected_entrypoint)

    expected_binary_name = 'pyci-guinea-pig.binary'
    expected_wheel_name = 'pyci-guinea-pig.whl'
    expected_installer_name = 'pyci-guinea-pig.exe'

    binary_path = os.path.join(temp_dir, expected_binary_name)
    wheel_path = os.path.join(temp_dir, expected_wheel_name)
    installer_path = os.path.join(temp_dir, expected_installer_name)

    def _nsis(*_, **kwargs):

        assert expected_author == kwargs.get('author')
        assert expected_website == kwargs.get('website')
        assert expected_license_path == kwargs.get('license_path')
        assert expected_copyr == kwargs.get('copyr')

        with open(installer_path, 'w') as f:
            f.write('nsis')

        return binary_path

    def _binary(*_, **kwargs):

        assert expected_entrypoint == kwargs.get('entrypoint')

        with open(binary_path, 'w') as f:
            f.write('binary')

        return binary_path

    def _wheel(*_, **__):

        with open(wheel_path, 'w') as f:
            f.write('wheel')

        return wheel_path

    def _upload(*_, **__):
        return 'http://this-is-an-upload-url'

    def _is_windows():
        return True

    mocker.patch(target='pyci.api.utils.is_windows', side_effect=_is_windows)
    mocker.patch(target='pyci.api.packager.Packager.binary', side_effect=_binary)
    mocker.patch(target='pyci.api.packager.Packager.wheel', side_effect=_wheel)
    mocker.patch(target='pyci.api.packager.Packager.nsis', side_effect=_nsis)
    mocker.patch(target='pyci.api.pypi.PyPI.upload', side_effect=_upload)

    release.run('--branch release {}'.format(release_options))

    github_release = release.github.api.repo.get_release(id='1.0.0')

    assets = [asset.name for asset in github_release.get_assets()]
    assert expected_binary_name in assets
    assert expected_wheel_name in assets
    assert expected_installer_name in assets

    from pyci.api.pypi import PyPI

    # noinspection PyUnresolvedReferences
    PyPI.upload.assert_called_once_with(wheel=wheel_path)  # pylint: disable=no-member


@pytest.mark.wet
def test_release_no_wheel_publish(release, temp_dir, mocker):

    release_options = '--no-wheel-publish --no-installer --binary-entrypoint {}'.format(
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

    release.run('--branch release {}'.format(release_options))

    github_release = release.github.api.repo.get_release(id='1.0.0')

    assets = [asset.name for asset in github_release.get_assets()]
    assert expected_binary_name in assets
    assert expected_wheel_name in assets

    from pyci.api.pypi import PyPI

    # noinspection PyUnresolvedReferences
    PyPI.upload.assert_not_called()  # pylint: disable=no-member


@pytest.mark.wet
def test_release_twice(release, mocker, temp_dir):

    release_options = '--pypi-test --no-installer --binary-entrypoint {}'.format(
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

        return binary_path

    # This mock can return anything it wants since this URL is not being
    # asserted upon.
    def _upload(*_, **__):
        return 'http://this-is-an-upload-url'

    mocker.patch(target='pyci.api.packager.Packager.binary', side_effect=_binary)
    mocker.patch(target='pyci.api.packager.Packager.wheel', side_effect=_wheel)
    mocker.patch(target='pyci.api.pypi.PyPI.upload', side_effect=_upload)

    release.run('--branch release {}'.format(release_options))

    release.github.api.reset_branch(name='release', sha=LAST_COMMIT, hard=True)
    release.github.api.reset_branch(name='master', sha=LAST_COMMIT, hard=True)

    release.run('--branch release {}'.format(release_options))

    expected_number_of_releases = 1

    assert expected_number_of_releases == len(list(release.github.api.repo.get_releases()))


@pytest.mark.skip('Need to create a specific commit to fit this use case')
@pytest.mark.wet
def test_release_default_entrypoint_not_found(release):

    sha = 'cf2d64132f00c849ae1bb62ffb2e32b719b6cbac'
    release.github.api.reset_branch(name='release', sha=sha, hard=True)
    release.github.api.reset_branch(name='master', sha=sha, hard=True)

    release.github.api.commit(path='README.md',
                              message='Release (#7)',
                              branch='release',
                              contents='contents')

    result = release.run('--branch release', catch_exceptions=True)

    expected_message = 'Binary package will not be created'

    assert expected_message in result.std_out
    release.github.api.repo.get_release(id='1.0.0')


@pytest.mark.wet
def test_release_validation_failed(release):

    sha = '33526a9e0445541d96e027db2aeb93d07cdf8bd6'
    release.github.api.reset_branch(name='release', sha=sha, hard=True)

    result = release.run('--branch release', catch_exceptions=True)

    expected_output = 'Not releasing: Commit {} does not reference any issue'.format(sha)

    assert not list(release.github.api.repo.get_releases())
    assert expected_output in result.std_out
    assert result.return_code == 0


def test_release_failed(release):

    result = release.run('--branch doesnt-exist', catch_exceptions=True)

    expected_output = 'Commit not found: doesnt-exist'

    assert expected_output in result.std_out
