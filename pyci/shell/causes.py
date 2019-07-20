#############################################################################
# Copyright (c) 2019 Eli Polonsky. All rights reserved
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


def no_setup_py_file(argument):
    return "PyCI uses the setup.py file to auto-detect the {}. " \
           "Unfortunately, your project doesn't seem to have a setup.py file.".format(argument)


def missing_argument_from_setup_py(argument):
    return "PyCI uses the setup.py file to auto-detect the {}. " \
           "Unfortunately, your project setup.py file doesn't contain the '{}' argument." \
        .format(argument, argument)
