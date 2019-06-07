import os
import uuid

from pyci.api.runner import LocalCommandRunner
from pyci.api import logger

log = logger.get_logger(__name__)


class Ubuntu(object):

    def __init__(self, local_repo_path):
        super(Ubuntu, self).__init__()
        self._volumes = {}
        self._local_repo_path = local_repo_path
        self._local_runner = LocalCommandRunner()

    def binary(self, virtualenv=True):

        base_repo_name = os.path.basename(self._local_repo_path)

        container_repo_path = '/tmp/{}/{}/.'.format(uuid.uuid4(), base_repo_name)

        if virtualenv:

            container_virtualenv_path = '/tmp/{}/env'.format(uuid.uuid4())

            install_command = 'pip install virtualenv==16.6.0 && ' \
                              'virtualenv {0} && ' \
                              '{0}/bin/pip install {1}' \
                              .format(container_virtualenv_path,
                                      container_repo_path)
            pack_command = '{0}/bin/pyci --debug pack --path {1} --target-dir {1} binary'.format(
                container_virtualenv_path, container_repo_path
            )

        else:
            install_command = 'pip install {0}'.format(container_repo_path)
            pack_command = 'pyci --debug pack --path {0} --target-dir {0} binary'.format(container_repo_path)

        command = '{} && {}'.format(install_command, pack_command)

        docker_command = 'docker run -v {}:{} python:3.6.8-stretch /bin/bash -c "{}"'\
            .format(self._local_repo_path, container_repo_path, command)
        self._local_runner.run(docker_command, pipe=True)

        binary_path = os.path.join(self._local_repo_path, 'py-ci-x86_64-Linux')

        return binary_path

    def add(self, resource_path):

        remote_path = '/tmp/{}/{}'.format(uuid.uuid4(), os.path.basename(resource_path))

        self._volumes[resource_path] = remote_path

        return remote_path

    def run(self, command):

        volumes = ''

        for key, value in self._volumes.iteritems():
            volumes = '{} -v {}:{}'.format(volumes, key, value)

        docker_command = 'docker run {} python:3.6.8-stretch /bin/bash -c "{}"'.format(volumes, command)

        return self._local_runner.run(docker_command, pipe=True, exit_on_failure=False)
