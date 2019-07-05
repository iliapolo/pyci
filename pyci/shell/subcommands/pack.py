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

import click

from pyci.api import exceptions
from pyci.api import utils
from pyci.shell import handle_exceptions
from pyci.shell import logger
from pyci.shell.exceptions import ShellException
from pyci.shell import help as pyci_help

log = logger.get()


@click.command()
@click.pass_context
@click.option('--base-name', required=False,
              help=pyci_help.BASE_NAME)
@click.option('--entrypoint', required=False,
              help=pyci_help.ENTRYPOINT)
@click.option('--pyinstaller-version', required=False,
              help=pyci_help.PY_INSTALLER_VERSION)
@handle_exceptions
def binary(ctx, base_name, entrypoint, pyinstaller_version):

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

        packager = ctx.obj.packager

        log.echo('Packaging binary...', break_line=False)
        package_path = packager.binary(
            entrypoint=entrypoint,
            pyinstaller_version=pyinstaller_version,
            base_name=base_name)
        log.checkmark()
        log.echo('Binary package created: {}'.format(package_path))
        return package_path
    except BaseException as e:

        if isinstance(e, exceptions.BinaryExistsException):
            e.exit_code = 101
            e.cause = 'You probably forgot to move/delete the package you created last time'
            e.possible_solutions = [
                'Delete/Move the binary and try again'
            ]

        if isinstance(e, exceptions.DefaultEntrypointNotFoundException):
            e.exit_code = 102
            e.cause = "You probably created the entrypoint in a different location than " \
                      "PyCI knows about.\nFor more details see " \
                      "https://github.com/iliapolo/pyci#cli-detection"
            e.possible_solutions = [
                # pylint this 'e' is of type BaseException here - IntelliJ gets it though.
                # pylint: disable=no-member
                'Create an entrypoint file in one of the following paths: {}'.format(', '.join(e.expected_paths)),
                'Use --entrypoint to specify a custom entrypoint path'
            ]

        if isinstance(e, exceptions.EntrypointNotFoundException):
            e.exit_code = 103

        log.xmark()
        raise


@click.command()
@click.pass_context
@click.option('--universal', is_flag=True,
              help='Use this if your project supports both python2 and python3 natively. This '
                   'corresponds to the --universal option of bdis_wheel '
                   '(https://wheel.readthedocs.io/en/stable/)')
@click.option('--wheel-version', required=False,
              help=pyci_help.WHEEL_VERSION)
@handle_exceptions
def wheel(ctx, universal, wheel_version):

    """
    Create a python wheel.

    Running this command requires a python installation.

    The python interpreter used is detected by running a python equivalent of the linux `which python` command.
    Make sure the python version you want is the first available `python` in your PATH.

    Note that you can only create wheels for projects that follow standard python packaging.

    see https://pythonwheels.com/

    """

    try:

        packager = ctx.obj.packager

        log.echo('Packaging wheel...', break_line=False)
        package_path = packager.wheel(universal=universal, wheel_version=wheel_version)
        log.checkmark()
        log.echo('Wheel package created: {}'.format(package_path))
        return package_path

    except BaseException as e:

        if isinstance(e, exceptions.WheelExistsException):
            e.exit_code = 104
            e.cause = 'You probably forgot to move/delete the package you created last time'
            e.possible_solutions = [
                'Delete/Move the package and try again'
            ]

        log.xmark()
        raise


@click.command()
@click.pass_context
@click.option('--binary-path', required=False,
              help='Path to a pre-packed binary executable. '
                   "This is the program that the installer will install. You can create this file by running the "
                   "'pyci pack binary' command.")
@click.option('--version', required=False,
              help='Version of the program. Must be in the form of X.X.X.X. Defaults to the version value in setup.py '
                   '(if exists)')
@click.option('--output', required=False,
              help='Path to write the created installer file.')
@click.option('--author', required=False,
              help='Program author. Defaults to the author value in setup.py (if exists)')
@click.option('--website', required=False,
              help='Website URL. Defaults to the url value in setup.py (if exists)')
@click.option('--copyr', required=False,
              help='Copyright string. Default to an empty value.')
@click.option('--license-path', required=False,
              help='Path to a license file. This license will appear as part of the installation Wizard. Defaults '
                   'to license value in setup.py (if exists)')
@handle_exceptions
def nsis(ctx, binary_path, version, output, author, website, copyr, license_path):

    """
    Create a windows executable installer.

    This operation creates a windows installer from a binary executable. The binary will be installed
    under the corresponding "Program Files" directory. In addition, the PATH variable will be changed to
    include the path to your program.

    Under the hood, PyCI uses NSIS to create it. Can only be executed on windows machines.

    See https://nsis.sourceforge.io/Main_Page
    """

    if not utils.is_windows():
        raise ShellException('NSIS packaging can only run on windows machines')

    try:

        packager = ctx.obj.packager

        log.echo('Packaging NSIS installer...', break_line=False)
        package_path = packager.nsis(binary_path,
                                     version=version,
                                     output=output,
                                     author=author,
                                     website=website,
                                     copyr=copyr,
                                     license_path=license_path)
        log.checkmark()
        log.echo('Installer package created: {}'.format(package_path))
        return package_path

    except BaseException as e:

        if isinstance(e, exceptions.FailedReadingSetupPyAuthorException):
            e.possible_solutions = [
                'Create a standard setup.py file in your project root',
                'Use --author to specify a custom author'
            ]

        if isinstance(e, exceptions.FailedReadingSetupPyLicenseException):
            e.possible_solutions = [
                'Create a standard setup.py file in your project root',
                'Use --license-path to specify a custom author'
            ]

        if isinstance(e, exceptions.FailedReadingSetupPyVersionException):
            e.possible_solutions = [
                'Create a standard setup.py file in your project root',
                'Use --version to specify a custom author'
            ]

        if isinstance(e, exceptions.FailedReadingSetupPyURLException):
            e.possible_solutions = [
                'Create a standard setup.py file in your project root',
                'Use --website to specify a custom author'
            ]

        log.xmark()
        raise
