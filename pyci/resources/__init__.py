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

import pkgutil


def get_text_resource(path):

    """
    Fetch a resource text file.

    Args:
        path (str): The path of the resource relative to this package.
    Returns:
        str: The resource as a character string.
    """

    return get_binary_resource(path).decode('UTF-8', 'ignore')


def get_binary_resource(path):

    """
    Fetch a resource binary file.

    Args:
        path (str): The path of the resource relative to this package.
    Returns:
        str: The resource as a binary string.
    """

    return pkgutil.get_data(__name__, path)
