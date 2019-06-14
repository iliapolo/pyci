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

import sys

import click

from pyci.api import exceptions
from pyci.api import utils
from pyci.api.packager import DEFAULT_PY_INSTALLER_VERSION
from pyci.api.packager import DEFAULT_WHEEL_VERSION
from pyci.shell import handle_exceptions
from pyci.shell import logger

log = logger.get()


@click.command()
@click.pass_context
@click.option('--name', required=False,
              help='The base name of the binary executable to be created. Defaults to the top '
                   'most python package of your project. Note that the full '
                   'name will be a suffixed with platform specific info. This corresponds to '
                   'the --name option used by '
                   'PyInstaller (https://pythonhosted.org/PyInstaller/usage.html)')
@click.option('--entrypoint', required=False,
              help='Path (relative to the repository root) of the file to be used as the '
                   'executable entry point. This corresponds to the positional script argument '
                   'passed to PyInstaller (https://pythonhosted.org/PyInstaller/usage.html)')
@click.option('--pyinstaller-version', required=False,
              help='Which version of PyInstaller to use. Note that PyCI is tested only against version {}, this is '
                   'an advanced option, use at your own peril'.format(DEFAULT_PY_INSTALLER_VERSION))
@handle_exceptions
def binary(ctx, name, entrypoint, pyinstaller_version):

    """
    Create a binary executable.

    This command creates a self-contained binary executable for your project.
    The binary is platform dependent (architecture, os). For example, on a 64bit MacOS the name
    will be: pyci-x86_64-Darwin

    The cool thing is that users can even run the executable on environments without python
    installed, since the binary packs a python version inside.

    Under the hood, pyci uses PyInstaller to create binary packages.

    see https://pythonhosted.org/PyInstaller/

    """

    try:
        package_path = binary_internal(entrypoint=entrypoint,
                                       name=name,
                                       packager=ctx.parent.packager,
                                       pyinstaller_version=pyinstaller_version)
        log.echo('Binary package created: {}'.format(package_path))
    except exceptions.FileExistException as e:
        err = click.ClickException('Binary already exists: {}'.format(e.path))
        err.exit_code = 101
        err.cause = 'You probably forgot to move/delete the package you created last time'
        err.possible_solutions = [
            'Delete/Move the binary and try again'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.DefaultEntrypointNotFoundException as e:
        err = click.ClickException('Failed locating an entrypoint file')
        err.exit_code = 102
        err.cause = "You probably created the entrypoint in a different location than " \
                    "PyCI knows about.\nFor more details see " \
                    "https://github.com/iliapolo/pyci#cli-detection"
        err.possible_solutions = [
            'Create an entrypoint file in one of the following paths: {}'
            .format(', '.join(e.expected_paths)),
            'Use --entrypoint to specify a custom entrypoint path'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.EntrypointNotFoundException as e:
        err = click.ClickException('The entrypoint path you specified does not exist: {}'
                                   .format(e.entrypoint))
        err.exit_code = 103
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


@click.command()
@click.pass_context
@click.option('--universal', is_flag=True,
              help='Use this if your project supports both python2 and python3 natively. This '
                   'corresponds to the --universal option of bdis_wheel '
                   '(https://wheel.readthedocs.io/en/stable/)')
@click.option('--wheel-version', required=False,
              help='Which version of wheel to use. Note that PyCI is tested only against version {}, this is '
                   'an advanced option, use at your own peril'.format(DEFAULT_WHEEL_VERSION))
@handle_exceptions
def wheel(ctx, universal, wheel_version):

    """
    Create a python wheel.

    see https://pythonwheels.com/

    """

    try:
        package_path = wheel_internal(universal=universal,
                                      packager=ctx.parent.packager,
                                      wheel_version=wheel_version)
        log.echo('Wheel package created: {}'.format(package_path))
    except exceptions.FileExistException as e:
        err = click.ClickException('Wheel already exists: {}'.format(e.path))
        err.exit_code = 104
        err.cause = 'You probably forgot to move/delete the package you created last time'
        err.possible_solutions = [
            'Delete/Move the package and try again'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


def wheel_internal(universal, packager, wheel_version):

    try:
        log.echo('Packaging wheel...', break_line=False)
        package_path = packager.wheel(universal=universal, wheel_version=wheel_version)
        log.checkmark()
        return package_path
    except BaseException as _:
        log.xmark()
        raise


def binary_internal(entrypoint, name, pyinstaller_version, packager):

    try:
        log.echo('Packaging binary...', break_line=False)
        package_path = packager.binary(
            entrypoint=entrypoint,
            pyinstaller_version=pyinstaller_version,
            name=name)
        log.checkmark()
        return package_path
    except BaseException as _:
        log.xmark()
        raise
