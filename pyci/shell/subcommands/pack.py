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
              help="The base name of the created file. Defaults to the name specified in setup.py (if exists). "
                   "Note that the full name will be suffixed with platform specific info. "
                   "For example, on a 64-bit MacOS machine, given the name 'pyci', the file will be "
                   "'pyci-x86_64-Darwin'")
@click.option('--entrypoint', required=False,
              help='A relative path to a file that serves as the entry point to your application '
                   '(i.e the main script). If not specified, PyCI applies some heuristics for automatically '
                   'detecting this. See https://github.com/iliapolo/pyci#cli-detection')
@click.option('--pyinstaller-version', required=False,
              help='Which version of PyInstaller to use. Note that PyCI is tested only against '
                   'version {}, this is an advanced option, use at your own peril'
              .format(DEFAULT_PY_INSTALLER_VERSION))
@handle_exceptions
def binary(ctx, name, entrypoint, pyinstaller_version):

    """
    Create a binary executable.

    This command creates a self-contained binary executable for your project.
    The binary is platform dependent (architecture, os). For example, on a 64-bit MacOS the name
    will be: pyci-x86_64-Darwin

    Note that the executable also packs the Python distribution inside it. Which means the created file
    can even be executed on machines without python installed.

    However, running this command (i.e packaging a binary) does require a python installation.
    The python interpreter used is detected by running a python equivalent of the linux `which python` command.
    Make sure the python version you want is the first available `python` in your PATH.

    Future versions of PyCI will allow specifying the python interpreter directly in the command line.

    Under the hood, PyCI uses PyInstaller to create binary packages.

    see https://pythonhosted.org/PyInstaller/

    """

    try:
        package_path = binary_internal(entrypoint=entrypoint,
                                       name=name,
                                       packager=ctx.parent.packager,
                                       pyinstaller_version=pyinstaller_version)
        log.echo('Binary package created: {}'.format(package_path))
    except exceptions.BinaryExistsException as e:
        err = click.ClickException(str(e))
        err.exit_code = 101
        err.cause = 'You probably forgot to move/delete the package you created last time'
        err.possible_solutions = [
            'Delete/Move the binary and try again'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.DefaultEntrypointNotFoundException as e:
        err = click.ClickException(str(e))
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
        err = click.ClickException(str(e))
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
              help='Which version of wheel to use for packaging. Note that PyCI is tested only against '
                   'version {}, this is an advanced option, use at your own peril'
              .format(DEFAULT_WHEEL_VERSION))
@handle_exceptions
def wheel(ctx, universal, wheel_version):

    """
    Create a python wheel.

    Running this command requires a python installation.
    The python interpreter used is detected by running a python equivalent of the linux `which python` command.
    Make sure the python version you want is the first available `python` in your PATH.

    Note that you can only create wheels for project that follow standard python packaging.

    see https://pythonwheels.com/

    """

    try:
        package_path = wheel_internal(universal=universal,
                                      packager=ctx.parent.packager,
                                      wheel_version=wheel_version)
        log.echo('Wheel package created: {}'.format(package_path))
    except exceptions.WheelExistsException as e:
        err = click.ClickException(str(e))
        err.exit_code = 104
        err.cause = 'You probably forgot to move/delete the package you created last time'
        err.possible_solutions = [
            'Delete/Move the package and try again'
        ]
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)


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
              help='Which version of PyInstaller to use. Note that PyCI is tested only against '
                   'version {}, this is an advanced option, use at your own peril'
              .format(DEFAULT_PY_INSTALLER_VERSION))
@click.option('--binary-path', required=False)
@click.option('--version', required=False)
@click.option('--output', required=False)
@click.option('--author', required=False)
@click.option('--website', required=False)
@click.option('--copyr', required=False)
@click.option('--license-path', required=False)
@handle_exceptions
# pylint: disable=too-many-arguments
# pylint: disable=too-many-statements
def exei(ctx, name, entrypoint, pyinstaller_version, binary_path,
         version, output, author, website, copyr, license_path):

    """
    Create a windows executable installer.

    This operation creates an windows installer from a binary executable. You can provide a
    pre-packaged binary with the --binary-path option. If you do not provide it, PyCI will create
    one on the fly.

    Under the hood, PyCI uses NSIS to create it. Can only be executed on windows machines.

    See https://nsis.sourceforge.io/Main_Page
    """

    if not utils.is_windows():
        raise click.ClickException('exei packaging can only run on windows machines')

    if not binary_path:

        try:
            binary_path = binary_internal(name=name,
                                          entrypoint=entrypoint,
                                          pyinstaller_version=pyinstaller_version,
                                          packager=ctx.parent.packager)
        except exceptions.DefaultEntrypointNotFoundException as e:
            err = click.ClickException(str(e))
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
            err = click.ClickException(str(e))
            err.exit_code = 103
            tb = sys.exc_info()[2]
            utils.raise_with_traceback(err, tb)
        except exceptions.FailedReadingSetupPyNameException as e:
            err = click.ClickException(str(e))
            err.possible_solutions = [
                'Create a standard setup.py file in your project root',
                'Use --name to specify a custom name'
            ]
            err.exit_code = 104
            tb = sys.exc_info()[2]
            utils.raise_with_traceback(err, tb)

    try:
        package_path = exei_internal(binary_path=binary_path,
                                     version=version,
                                     output=output,
                                     author=author,
                                     website=website,
                                     copyr=copyr,
                                     license_path=license_path,
                                     packager=ctx.parent.packager)
        log.echo('Installer package created: {}'.format(package_path))
    except exceptions.FailedReadingSetupPyAuthorException as e:
        err = click.ClickException(str(e))
        err.possible_solutions = [
            'Create a standard setup.py file in your project root',
            'Use --author to specify a custom author'
        ]
        err.exit_code = 105
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.FailedReadingSetupPyLicenseException as e:
        err = click.ClickException(str(e))
        err.possible_solutions = [
            'Create a standard setup.py file in your project root',
            'Use --license-path to specify a custom license'
        ]
        err.exit_code = 105
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.FailedReadingSetupPyVersionException as e:
        err = click.ClickException(str(e))
        err.possible_solutions = [
            'Create a standard setup.py file in your project root',
            'Use --version to specify a custom version'
        ]
        err.exit_code = 105
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(err, tb)
    except exceptions.FailedReadingSetupPyURLException as e:
        err = click.ClickException(str(e))
        err.possible_solutions = [
            'Create a standard setup.py file in your project root',
            'Use --website to specify a custom website'
        ]
        err.exit_code = 105
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


def exei_internal(binary_path, version, output, author, website, copyr, license_path, packager):

    try:
        log.echo('Packaging exei...', break_line=False)
        package_path = packager.exei(binary_path,
                                     version=version,
                                     output=output,
                                     author=author,
                                     website=website,
                                     copyr=copyr,
                                     license_path=license_path)
        log.checkmark()
        return package_path
    except BaseException as _:
        log.xmark()
        raise
