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

import traceback
from functools import wraps

import six

from pyci.api.exceptions import ApiException
from pyci.shell.exceptions import TerminationException
from pyci.shell.exceptions import ShellException


def handle_exceptions(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        def _tb():
            tbio = six.StringIO()
            traceback.print_exc(file=tbio)
            return tbio.getvalue()

        try:
            return func(*args, **kwargs)
        except (ApiException, ShellException) as e:
            raise TerminationException(str(e), e, _tb())
        except TerminationException:
            raise
        except BaseException as be:
            message = str(be) \
                      + '\n\n' \
                      + 'If you see this message, you probably encountered a bug. ' \
                        'Please feel free to report it to https://github.com/iliapolo/pyci/issues'
            raise TerminationException(message, be, _tb())

    return wrapper


def detect_repo(ctx, ci_provider, repo):

    repo = repo or (ci_provider.repo if ci_provider else None)
    if repo is None:
        error = ShellException(message='Failed detecting repository name')
        error.cause = 'PyCI can only detect the repository name when running inside a CI ' \
                      'provider.\nOtherwise, you must explicitly pass it in the command line.'
        error.possible_solutions = [
            'Provide it using the --repo option ({} --repo)'.format(ctx.command_path)
        ]
        raise error
    return repo
