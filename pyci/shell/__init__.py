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
import traceback
from functools import wraps

import six
import click

from pyci.api import exceptions
from pyci.shell import logger

log = logger.get()


def handle_exceptions(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        try:
            func(*args, **kwargs)
        except (exceptions.ApiException, click.ClickException) as e:
            tbio = six.StringIO()
            traceback.print_exc(file=tbio)
            log.debug(tbio.getvalue())
            log.error(str(e))
            info = build_info(e)
            if info:
                log.echo(info, fg='yellow', prefix=False)
            sys.exit(1)
        except BaseException as be:
            tbio = six.StringIO()
            traceback.print_exc(file=tbio)
            log.debug(tbio.getvalue())
            log.error(str(be)
                      + '\n\n'
                      + 'If you see this message, you probably encountered a bug. '
                        'Please feel free to report it to https://github.com/iliapolo/pyci/issues')
            sys.exit(1)

    return wrapper


def build_info(exception):

    info = None

    if hasattr(exception, 'cause'):
        info = '\n' + exception.cause + '\n'

    if hasattr(exception, 'possible_solutions'):
        info = (info or '') + '\nPossible solutions: \n\n' + \
               '\n'.join(['    - ' + solution + '.' for solution in exception.possible_solutions])

    return info


def detect_repo(ctx, ci_provider, repo):

    repo = repo or (ci_provider.repo if ci_provider else None)
    if repo is None:
        error = click.ClickException(message='Failed detecting repository name')
        error.cause = 'PyCI can only detect the repository name when running inside a CI ' \
                      'provider.\nOtherwise, you must explicitly pass it in the command line.'
        error.possible_solutions = [
            'Provide it using the --repo option ({} --repo)'.format(ctx.command_path)
        ]
        raise error
    return repo


BRANCH_HELP = 'The name of the branch you want to release. The defaulting heuristics ' \
                      'are as follows: ' \
                      '1) The branch the build was triggered on. ' \
                      '2) The default branch name of the repository.'


MASTER_BRANCH_HELP = 'The master branch name. That is, the branch that should point to the ' \
                     'latest stable release. Defaults to master.'


RELEASE_BRANCH_HELP = 'The release branch name. That is, the branch that releases should be ' \
                      'made from. This is used to silently ignore commits made to other ' \
                      'branches. Defaults to the repository default branch.'


REPO_HELP = 'Github repository full name (i.e: <owner>/<repo>). When running inside a CI ' \
            'system, this will be automatically detected using environment variables.'
