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

log = logger.get_logger(__name__)


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--wheel', required=True,
              help='Path to the wheel file.')
def upload(ctx, wheel):

    """
    Upload a wheel to PyPI.

    Not much more to say here really :)

    """

    try:
        upload_internal(wheel=wheel, pypi=ctx.parent.pypi)
    except exceptions.ApiException as e:
        err = click.ClickException('Failed uploading wheel: {}'.format(str(e)))
        raise type(err), err, sys.exc_info()[2]


def upload_internal(wheel, pypi):
    log.info('Uploading wheel...(this may take some time)')
    wheel_url = pypi.upload(wheel=wheel)
    log.info('Wheel uploaded: {}'.format(wheel_url))
    return wheel_url
