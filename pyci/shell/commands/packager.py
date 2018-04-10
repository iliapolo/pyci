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
from pyci.shell import handle_exceptions


@click.command()
@click.pass_context
@click.option('--name', required=False)
@click.option('--entrypoint', required=False)
@click.option('--target-dir', required=False)
@handle_exceptions
def binary(ctx, name, entrypoint, target_dir):

    click.echo('Packaging... (this may take some time)')
    try:
        package_path = ctx.parent.packager.binary(entrypoint=entrypoint,
                                                  name=name,
                                                  target_dir=target_dir)
    except exceptions.BinaryAlreadyExists as e:
        e.possible_solutions = [
            'Delete/Move the file and try again'
        ]
        raise e
    click.echo('Package created: {0}'.format(package_path))
