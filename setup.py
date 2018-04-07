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

from setuptools import setup


BASE_PACKAGE_NAME = 'pyci'

PROGRAM_NAME = 'pyci'

# this is different because it determines the name of the project
# in PyPi, and unfortunately 'pyci' is taken :(
PROJECT_NAME = 'py-ci'

setup(
    name=PROJECT_NAME,
    version='0.3.0',
    author='Eli Polonsky',
    author_email='eli.polonsky@gmail.com',
    packages=[
        BASE_PACKAGE_NAME,
        '{0}.resources'.format(BASE_PACKAGE_NAME),
        '{0}.api'.format(BASE_PACKAGE_NAME),
        '{0}.shell'.format(BASE_PACKAGE_NAME),
        '{0}.shell.commands'.format(BASE_PACKAGE_NAME),
        '{0}.shell.subcommands'.format(BASE_PACKAGE_NAME)
    ],
    package_data={
        BASE_PACKAGE_NAME: [
            'resources/changelog.jinja',
            'resources/pyci.ascii'
        ],
    },
    license='LICENSE',
    description="CI toolchain for Python projects",
    entry_points={
        'console_scripts': [
            '{0} = {1}.shell.main:app'.format(PROGRAM_NAME, BASE_PACKAGE_NAME)
        ]
    },
    install_requires=[
        'click==6.7',
        'semver==2.8.0',
        'PyGithub>=1.38',
        'pyinstaller==3.3.1',
        'requests==2.18.4',
        'jinja2==2.10',
        'boltons==18.0.0',
        'wheel==0.31.1',
        'twine==1.11.0',
        'six==1.11.0',
        'colorama==0.3.9'
    ],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Natural Language :: English',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
