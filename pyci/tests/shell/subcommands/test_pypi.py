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

from pyci.tests import conftest


@pytest.mark.parametrize("binary", [False, True])
def test_upload(log, pypi, pack, binary):

    log.info("Creating wheel...")
    wheel_path = pack.api.wheel()

    expected_url = 'https://test.pypi.org/manage/project/py-ci/release/{}/'.format(
        wheel_path.split('-')[1])

    result = pypi.run('upload --wheel {}'.format(wheel_path), binary=binary)

    expected_output = '* Wheel uploaded: {}'.format(expected_url)

    assert expected_output in result.std_out


@pytest.mark.parametrize("binary", [False, True])
def test_upload_already_published(pypi, pack, binary):

    wheel_path = pack.api.wheel()

    pypi.run('upload --wheel {}'.format(wheel_path), catch_exceptions=True, binary=binary)

    # change the source code but create a wheel with the same version
    main = os.path.join(pack.api.repo_dir, 'pyci', 'shell', 'main.py')
    with open(main, 'w') as stream:
        stream.write('import os')

    os.remove(wheel_path)
    wheel_path = pack.api.wheel()

    result = pypi.run('upload --wheel {}'.format(wheel_path), catch_exceptions=True, binary=binary)

    expected_output = 'A wheel with the same name as {} was already uploaded'\
                      .format(os.path.basename(wheel_path))

    assert expected_output in result.std_out


@pytest.mark.skip()
@pytest.mark.linux
def test_binary_cross_platform_upload(platforms):

    local_binary_path = platforms.ubuntu.binary()

    try:
        remote_binary_path = platforms.alpine.add(local_binary_path)

        pack_command = '{0} --debug pack --repo {1} --sha {2} wheel'.format(remote_binary_path,
                                                                            conftest.REPO_UNDER_TEST,
                                                                            conftest.LAST_COMMIT)

        upload_command = 'TWINE_USERNAME=stub TWINE_PASSWORD=stub {0} ' \
                         '--debug pypi ' \
                         '--test upload ' \
                         '--wheel /pyci_guinea_pig-0.0.1-py3-none-any.whl'.format(remote_binary_path)

        command = '{} && {}'.format(pack_command, upload_command)

        result = platforms.alpine.run('chmod +x {0} && {1}'.format(remote_binary_path, command))

        # This means everything worked fine with regards to packaging. We expect this
        # error because we provide false credentials since we are not really interested in actually
        # uploading the wheel.
        assert 'Invalid or non-existent authentication' in result.std_out

    finally:
        os.remove(local_binary_path)
