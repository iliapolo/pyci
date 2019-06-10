import os
import uuid

import pyci
from pyci.api.runner import LocalCommandRunner
from pyci.api import logger


class Stretch(object):

    def __init__(self, python_version):
        super(Stretch, self).__init__()
        self._python_version = python_version
        self._image = 'python:{}-stretch'.format(python_version)
        self._logger = logger.Logger(__name__)
        self._volumes = {}
        self._local_repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))
        self._local_runner = LocalCommandRunner(log=self._logger)

    @property
    def python_version(self):
        return self._python_version

    @property
    def has_python(self):
        return False

    def binary(self):

        base_repo_name = os.path.basename(self._local_repo_path)

        container_repo_path = '/tmp/{}/{}/.'.format(uuid.uuid4(), base_repo_name)

        install_command = 'pip install {}'.format(container_repo_path)
        pack_command = 'pyci --debug pack --path {0} --target-dir {0} binary --entrypoint pyci.spec'.format(
            container_repo_path)

        command = '{} && {}'.format(install_command, pack_command)

        docker_command = 'docker run -v {}:{} {} /bin/bash -c "{}"'\
            .format(self._local_repo_path, container_repo_path, self._image, command)
        self._local_runner.run(docker_command)

        binary_path = os.path.join(self._local_repo_path, 'py-ci-x86_64-Linux')

        return binary_path

    def add(self, resource_path):

        remote_path = '/tmp/{}/{}'.format(uuid.uuid4(), os.path.basename(resource_path))

        self._volumes[resource_path] = remote_path

        return remote_path

    def run(self, command, exit_on_failure=True):

        volumes = ''

        for key, value in self._volumes.iteritems():
            volumes = '{} -v {}:{}'.format(volumes, key, value)

        docker_command = 'docker run {} {} /bin/bash -c "{}"'.format(volumes, self._image, command)

        return self._local_runner.run(docker_command, exit_on_failure=exit_on_failure)


class Ubuntu(object):

    def __init__(self, version):
        super(Ubuntu, self).__init__()
        self._image = 'ubuntu:{}'.format(version)
        self._logger = logger.Logger(__name__)
        self._volumes = {}
        self._local_repo_path = os.path.abspath(os.path.join(pyci.__file__, os.pardir, os.pardir))
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

        for key, value in self._volumes.iteritems():
            volumes = '{} -v {}:{}'.format(volumes, key, value)

        docker_command = 'docker run {} {} /bin/bash -c "{}"'.format(volumes, self._image, command)

        return self._local_runner.run(docker_command, exit_on_failure=exit_on_failure)
