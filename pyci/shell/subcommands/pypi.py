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

from pyci.api import logger
from pyci.shell import handle_exceptions


log = logger.get_logger(__name__)


@click.command()
@handle_exceptions
@click.pass_context
@click.option('--wheel', required=True)
def upload(ctx, wheel):

    log.info('Uploading wheel...')
    ctx.parent.pypi.upload(wheel)
    log.info('Done')
