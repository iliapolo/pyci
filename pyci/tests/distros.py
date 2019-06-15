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
import abc

from pyci.api.runner import LocalCommandRunner
from pyci.api import logger
from pyci.tests import conftest


class _Distro(object):

    def __init__(self, name, image, log=None):
        super(_Distro, self).__init__()
        self._image = image
        self._logger = log or logger.Logger(__name__)
        self._local_runner = LocalCommandRunner(log=self._logger, host=self._image)
        self._container_name = name
        self._data_container_name = '{}-data'.format(self._container_name)

    @abc.abstractproperty
    def python_version(self):
        pass

    def boot(self):

        self._logger.info('Booting up {}...'.format(self._image))
        self._create_data_container()

    def add(self, resource_path):

        remote_path = '/data/{}'.format(os.path.basename(resource_path))

        self._logger.info('Copying {} to distro {}...'.format(resource_path, self._image))
        self._local_runner.run('docker cp {} {}:{}'.format(resource_path, self._data_container_name, remote_path))

        return remote_path

    def run(self, command, exit_on_failure=True):

        docker_command = 'docker run --volumes-from {} {} /bin/bash -c "{}"'.format(self._data_container_name,
                                                                                    self._image,
                                                                                    command)
        return self._local_runner.run(docker_command, exit_on_failure=exit_on_failure)

    def shutdown(self):

        self._logger.info('Shutting down {}...'.format(self._image))
        self._local_runner.run('docker rm -vf {}'.format(self._data_container_name), exit_on_failure=False)
        self._local_runner.run('docker rm -vf {}'.format(self._container_name), exit_on_failure=False)

    def binary(self, local_repo_path):

        assert self.python_version is not None

        container_repo_path = self.add(local_repo_path)

        pack_command = 'pip install {0}/. && pyci --debug pack --path {0} --target-dir {0} binary --entrypoint {1}' \
            .format(container_repo_path, conftest.SPEC_FILE)

        self.run(pack_command)

        expected_binary_name = 'py-ci-x86_64-Linux'

        container_binary_path = os.path.join(container_repo_path, expected_binary_name)

        self._local_runner.run('docker cp {}:{} {}'.format(self._data_container_name,
                                                           container_binary_path,
                                                           local_repo_path))

        return os.path.join(local_repo_path, expected_binary_name)

    def _create_data_container(self):
        self._local_runner.run('docker create -v /data --name {} {}'.format(self._data_container_name, self._image))


class PythonStretch(_Distro):

    def __init__(self, name, python_version):
        super(PythonStretch, self).__init__(name, 'python:{}-stretch'.format(python_version))
        self._python_version = python_version

    @property
    def python_version(self):
        return self._python_version


class CentOS(_Distro):

    def __init__(self, name):
        super(CentOS, self).__init__(name, 'centos:centos7.6.1810')

    @property
    def python_version(self):
        return '2.7.5'


class Ubuntu(_Distro):

    def __init__(self, name, version):
        super(Ubuntu, self).__init__(name, 'ubuntu:{}'.format(version))

    @property
    def python_version(self):
        return None


def from_string(name, distro):

    parts = distro.split(':')

    env = parts[0]
    os_part = parts[1]
    arg_part = parts[2]

    os_cls = os_mapping[os_part]

    return os_cls('{}-{}'.format(env, name), arg_part)


os_mapping = {
    'Ubuntu': Ubuntu,
    'PythonStretch': PythonStretch
}
