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
from pyci.api import logger
from pyci.shell import handle_exceptions
from pyci.shell import is_binary

log = logger.get_logger(__name__)


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
@click.option('--target-dir', required=False,
              help='The directory to create the binary in. Defaults to the current directory.')
@handle_exceptions
def binary(ctx, name, entrypoint, target_dir):

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

    if is_binary():
        raise click.ClickException('Creating a binary package is not supported when running from '
                                   'within a binary')

    try:
        binary_internal(entrypoint=entrypoint,
                        name=name,
                        target_dir=target_dir,
                        packager=ctx.parent.packager)
    except exceptions.FileExistException as e:
        err = click.ClickException('Failed creating binary package: {}'.format(str(e)))
        err.possible_solutions = [
            'Delete/Move the file and try again'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.FileIsADirectoryException as e:
        err = click.ClickException('Failed creating binary package: {}'.format(str(e)))
        err.possible_solutions = [
            'Delete/Move the directory and try again'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.ApiException as e:
        err = click.ClickException('Failed creating binary package: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


@click.command()
@click.pass_context
@click.option('--universal', is_flag=True,
              help='Use this if your project supports both python2 and python3 natively. This '
                   'corresponds to the --universal option of bdis_wheel '
                   '(https://wheel.readthedocs.io/en/stable/)')
@click.option('--target-dir', required=False,
              help='The directory to create the wheel in. Defaults to the current directory.')
@handle_exceptions
def wheel(ctx, target_dir, universal):

    """
    Create a python wheel.

    see https://pythonwheels.com/

    """

    try:
        wheel_internal(target_dir=target_dir, universal=universal, packager=ctx.parent.packager)
    except exceptions.FileExistException as e:
        err = click.ClickException('Failed creating wheel package: {}'.format(str(e)))
        err.possible_solutions = [
            'Delete/Move the file and try again'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.FileIsADirectoryException as e:
        err = click.ClickException('Failed creating wheel package: {}'.format(str(e)))
        err.possible_solutions = [
            'Delete/Move the directory and try again'
        ]
        raise type(err), err, sys.exc_info()[2]
    except exceptions.ApiException as e:
        err = click.ClickException('Failed creating wheel package: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


def wheel_internal(target_dir, universal, packager):
    log.info('Packaging... (this may take some time)')
    package_path = packager.wheel(
        target_dir=target_dir,
        universal=universal
    )
    log.info('Wheel package created: {}'.format(package_path))
    return package_path


def binary_internal(entrypoint, name, target_dir, packager):

    log.info('Packaging... (this may take some time)')
    package_path = packager.binary(entrypoint=entrypoint,
                                   name=name,
                                   target_dir=target_dir)
    log.info('Binary package created: {}'.format(package_path))
    return package_path
