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


BASE_PACKAGE_NAME = 'pyci'

PROGRAM_NAME = 'pyci'

# this is different because it determines the name of the project
# in PyPi, and unfortunately 'pyci' is taken :(
PROJECT_NAME = 'py-ci'

setup(
    name=PROJECT_NAME,
    version='0.0.1',
    author='Eli Polonsky',
    author_email='eli.polonsky@gmail.com',
    packages=[
        BASE_PACKAGE_NAME,
        '{0}.resources'.format(BASE_PACKAGE_NAME),
        '{0}.api'.format(BASE_PACKAGE_NAME),
        '{0}.shell'.format(BASE_PACKAGE_NAME),
        '{0}.shell.commands'.format(BASE_PACKAGE_NAME)
    ],
    license='LICENSE',
    description="Command Line Interface for releasing open source python libraries",
    entry_points={
        'console_scripts': [
            '{0} = {1}.shell.main:app'.format(PROGRAM_NAME, BASE_PACKAGE_NAME)
        ]
    },
    install_requires=[
        'click==6.7',
        'wryte==0.2.1',
        'pygithub==1.38',
        'semver==2.7.9',
        'pygithub==1.38',
        'pyinstaller==3.3.1',
        'requests==2.18.4',
        'jinja2==2.10',
        'boltons==18.0.0',
        'wheel==0.29.0',
        'twine==1.11.0'
    ]
)
