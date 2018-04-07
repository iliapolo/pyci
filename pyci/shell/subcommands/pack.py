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
from pyci.shell import handle_exceptions
from pyci.api.utils import is_pyinstaller
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
@handle_exceptions
def binary(ctx, name, entrypoint):

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

    if is_pyinstaller():
        raise click.ClickException('Creating a binary package is not supported when running from '
                                   'within a binary')

    try:
        package_path = binary_internal(entrypoint=entrypoint,
                                       name=name,
                                       packager=ctx.parent.packager)
        log.echo('Binary package created: {}'.format(package_path))
    except exceptions.FileExistException as e:
        err = click.ClickException('Binary already exists: {}'.format(e.path))
        err.cause = 'You probably forgot to move/delete the package you created last time'
        err.possible_solutions = [
            'Delete/Move the binary and try again'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.DefaultEntrypointNotFoundException as e:
        err = click.ClickException('Failed locating an entrypoint file')
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
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


@click.command()
@click.pass_context
@click.option('--universal', is_flag=True,
              help='Use this if your project supports both python2 and python3 natively. This '
                   'corresponds to the --universal option of bdis_wheel '
                   '(https://wheel.readthedocs.io/en/stable/)')
@handle_exceptions
def wheel(ctx, universal):

    """
    Create a python wheel.

    see https://pythonwheels.com/

    """

    try:
        package_path = wheel_internal(universal=universal,
                                      packager=ctx.parent.packager)
        log.echo('Wheel package created: {}'.format(package_path))
    except exceptions.FileExistException as e:
        err = click.ClickException('Wheel already exists: {}'.format(e.path))
        err.cause = 'You probably forgot to move/delete the package you created last time'
        err.possible_solutions = [
            'Delete/Move the package and try again'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


def wheel_internal(universal, packager):

    try:
        log.echo('Packaging wheel...', break_line=False)
        package_path = packager.wheel(
            universal=universal
        )
        log.checkmark()
        return package_path
    except:
        log.xmark()
        raise


def binary_internal(entrypoint, name, packager):

    try:
        log.echo('Packaging binary...', break_line=False)
        package_path = packager.binary(
            entrypoint=entrypoint,
            name=name)
        log.checkmark()
        return package_path
    except:
        log.xmark()
        raise
