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

import click

from pyci.api import exceptions
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

        pypi = ctx.obj.pypi

        log.echo('Uploading {} to PyPI...'.format(os.path.basename(wheel)), break_line=False)
        wheel_url = pypi.upload(wheel=wheel)
        log.checkmark()
        log.echo('Wheel uploaded: {}'.format(wheel_url))
        return wheel_url
    except BaseException as e:

        if isinstance(e, exceptions.WheelAlreadyPublishedException):
            e.cause = 'You probably forgot to bump the version number of your project'

        log.xmark()
        raise
