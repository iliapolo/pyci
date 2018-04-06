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


from setuptools import setup


PROGRAM_NAME = 'pyrelease'

setup(
    name=PROGRAM_NAME,
    version='0.1',
    author='Eli Polonsky',
    author_email='eli.polonsky@gmail.com',
    packages=[
        PROGRAM_NAME,
        '{0}.api'.format(PROGRAM_NAME),
        '{0}.shell'.format(PROGRAM_NAME),
        '{0}.shell.commands'.format(PROGRAM_NAME),
    ],
    license='LICENSE',
    description="Command Line Interface for releasing open source python libraries",
    entry_points={
        'console_scripts': [
            '{0} = {0}.shell.main:app'.format(PROGRAM_NAME)
        ]
    },
    install_requires=[
        'click==6.7',
        'wryte==0.2.1',
        'pygithub==1.38',
        'semver==2.7.9'
    ]
)
