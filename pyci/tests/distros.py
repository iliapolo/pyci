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
import uuid

from pyci.api.runner import LocalCommandRunner
from pyci.api import logger, utils
from pyci.tests import conftest


class PythonStretch(object):

    def __init__(self, python_version):
        super(PythonStretch, self).__init__()
        self._python_version = python_version
        self._image = 'python:{}-stretch'.format(python_version)
        self._logger = logger.Logger(__name__)
        self._volumes = {}
        self._local_runner = LocalCommandRunner(log=self._logger)

    @property
    def python_version(self):
        return self._python_version

    @property
    def has_python(self):
        return True

    def binary(self, local_repo_path):

        base_repo_name = os.path.basename(local_repo_path)

        container_repo_path = '/tmp/{}/{}'.format(uuid.uuid4(), base_repo_name)

        install_command = 'ls -l {0} && pip install {0}/.'.format(container_repo_path)
        pack_command = 'pyci --debug pack --path {0} --target-dir {0} binary --entrypoint {1}'.format(
            container_repo_path, conftest.SPEC_FILE)

        command = '{} && {}'.format(install_command, pack_command)

        docker_command = '{} run -v {}:{} {} /bin/bash -c "{}"'\
            .format(docker(), local_repo_path, container_repo_path, self._image, command)
        self._local_runner.run(docker_command)

        binary_path = os.path.join(local_repo_path, 'py-ci-x86_64-Linux')

        return binary_path

    def add(self, resource_path):

        remote_path = '/tmp/{}/{}'.format(uuid.uuid4(), os.path.basename(resource_path))

        self._volumes[resource_path] = remote_path

        return remote_path

    def run(self, command, exit_on_failure=True):

        volumes = ''

        for key, value in self._volumes.items():
            volumes = '{} -v {}:{}'.format(volumes, key, value)

        docker_command = '{} run {} {} /bin/bash -c "{}"'.format(docker(), volumes, self._image, command)

        return self._local_runner.run(docker_command, exit_on_failure=exit_on_failure)


class CentOS(object):

    def __init__(self):
        super(CentOS, self).__init__()
        self._image = 'centos:centos7.6.1810'
        self._logger = logger.Logger(__name__)
        self._volumes = {}
        self._local_runner = LocalCommandRunner(log=self._logger)

    @property
    def python_version(self):
        return '2.7.5'

    @property
    def has_python(self):
        return True

    def binary(self, local_repo_path):

        base_repo_name = os.path.basename(local_repo_path)

        container_repo_path = '/tmp/{}/{}/.'.format(uuid.uuid4(), base_repo_name)

        install_command = 'ls -l {0} && pip install {0}'.format(container_repo_path)
        pack_command = 'pyci --debug pack --path {0} --target-dir {0} binary --entrypoint {1}'.format(
            container_repo_path, conftest.SPEC_FILE)

        command = '{} && {}'.format(install_command, pack_command)

        docker_command = '{} run -v {}:{} {} /bin/bash -c "{}"' \
            .format(docker(), local_repo_path, container_repo_path, self._image, command)
        self._local_runner.run(docker_command)

        binary_path = os.path.join(local_repo_path, 'py-ci-x86_64-Linux')

        return binary_path

    def add(self, resource_path):

        remote_path = '/tmp/{}/{}'.format(uuid.uuid4(), os.path.basename(resource_path))

        self._volumes[resource_path] = remote_path

        return remote_path

    def run(self, command, exit_on_failure=True):

        volumes = ''

        for key, value in self._volumes.items():
            volumes = '{} -v {}:{}'.format(volumes, key, value)

        docker_command = '{} run {} {} /bin/bash -c "{}"'.format(docker(), volumes, self._image, command)

        return self._local_runner.run(docker_command, exit_on_failure=exit_on_failure)


class Ubuntu(object):

    def __init__(self, version):
        super(Ubuntu, self).__init__()
        self._image = 'ubuntu:{}'.format(version)
        self._logger = logger.Logger(__name__)
        self._volumes = {}
        self._local_runner = LocalCommandRunner(log=self._logger)

    @property
    def python_version(self):
        return None

    @property
    def has_python(self):
        return False

    def binary(self):
        raise NotImplementedError('This image does not contain a python installation')

    def add(self, resource_path):

        remote_path = '/tmp/{}/{}'.format(uuid.uuid4(), os.path.basename(resource_path))

        self._volumes[resource_path] = remote_path

        return remote_path

    def run(self, command, exit_on_failure=True):

        volumes = ''

        for key, value in self._volumes.items():
            volumes = '{} -v {}:{}'.format(volumes, key, value)

        docker_command = '{} run {} {} /bin/bash -c "{}"'.format(docker(), volumes, self._image, command)

        return self._local_runner.run(docker_command, exit_on_failure=exit_on_failure)


def from_string(distro):

    parts = distro.split(':')

    os_part = parts[1]
    arg_part = parts[2]

    os_cls = os_mapping[os_part]

    return os_cls(arg_part)


def docker():
    path = utils.which('docker')
    if not path:
        raise RuntimeError('docker command not found')
    return path


os_mapping = {
    'Ubuntu': Ubuntu,
    'PythonStretch': PythonStretch
}
