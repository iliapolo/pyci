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


from pyci.shell import handle_exceptions
from pyci.shell import help as pyci_help
from pyci.shell.logger import get as get_logger
from pyci.api import ci


log = get_logger()


@click.command(context_settings=dict(ignore_unknown_options=True,))
@handle_exceptions
@click.pass_context
@click.option('--release-branch', required=True,
              help=pyci_help.RELEASE_BRANCH)
def validate_build(ctx, release_branch, **_):

    """
    Validate the current build should be released.

    The conditions for release are:

        1. The current build is not a PR build.

        2. The current build is not a TAG build.

        3. The current build is running on the release branch.

    """

    ci_provider = ctx.obj.ci_provider

    def _pre_pr():
        log.echo('Build is not a PR...', break_line=False)

    def _post_pr():
        log.checkmark()

    def _pre_tag():
        log.echo('Build is not a TAG...', break_line=False)

    def _post_tag():
        log.checkmark()

    def _pre_branch():
        log.echo("Build branch is '{}'...".format(release_branch), break_line=False)

    def _post_branch():
        log.checkmark()

    if ci_provider:
        log.echo('Validating build {}'.format(ci_provider.build_url), add=True)
        try:
            ci.validate_build(ci_provider=ci_provider, release_branch=release_branch,
                              hooks={
                                  'pre_pr': _pre_pr,
                                  'pre_tag': _pre_tag,
                                  'pre_branch': _pre_branch,
                                  'post_pr': _post_pr,
                                  'post_tag': _post_tag,
                                  'post_branch': _post_branch
                              })
            log.sub()
            log.echo('Validation passed')
        except BaseException:
            log.xmark()
            log.sub()
            raise
