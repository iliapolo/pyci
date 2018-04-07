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
import os

import click

from pyci.api import exceptions
from pyci.api import utils
from pyci.shell import handle_exceptions
from pyci.shell import logger

log = logger.get()


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
        wheel_url = upload_internal(wheel=wheel, pypi=ctx.parent.pypi)
        log.echo('Wheel uploaded: {}'.format(wheel_url))
    except exceptions.WheelAlreadyPublishedException as e:
        e.cause = 'You probably forgot to bump the version number of your project'
        tb = sys.exc_info()[2]
        utils.raise_with_traceback(e, tb)


def upload_internal(wheel, pypi):

    try:
        log.echo('Uploading {}...'.format(os.path.basename(wheel)), break_line=False)
        wheel_url = pypi.upload(wheel=wheel)
        log.checkmark()
        return wheel_url
    except:
        log.xmark()
        raise
