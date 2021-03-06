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
    name='py-ci',
    url='https://github.com/iliapolo/pyci/',
    version='0.8.3',
    author='Eli Polonsky',
    author_email='eli.polonsky@gmail.com',
    packages=[
        BASE_PACKAGE_NAME,
        '{0}.resources'.format(BASE_PACKAGE_NAME),
        '{0}.resources.virtualenv_support'.format(BASE_PACKAGE_NAME),
        '{0}.resources.windows_support'.format(BASE_PACKAGE_NAME),
        '{0}.api'.format(BASE_PACKAGE_NAME),
        '{0}.api.ci'.format(BASE_PACKAGE_NAME),
        '{0}.api.model'.format(BASE_PACKAGE_NAME),
        '{0}.api.package'.format(BASE_PACKAGE_NAME),
        '{0}.api.publish'.format(BASE_PACKAGE_NAME),
        '{0}.api.scm'.format(BASE_PACKAGE_NAME),
        '{0}.shell'.format(BASE_PACKAGE_NAME),
        '{0}.shell.commands'.format(BASE_PACKAGE_NAME),
        '{0}.shell.subcommands'.format(BASE_PACKAGE_NAME)
    ],
    package_data={
        BASE_PACKAGE_NAME: [
            'resources/changelog.jinja',
            'resources/pyci.ascii',
            'resources/virtualenv.py',
            'resources/virtualenv_support/pip-19.1.1-py2.py3-none-any.whl',
            'resources/virtualenv_support/setuptools-41.0.1-py2.py3-none-any.whl',
            'resources/windows_support/installer.nsi.jinja',
            'resources/windows_support/nsis-3.04.zip',
            'resources/windows_support/path.nsh'
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
        'click==7.0',
        'semver==2.8.0',
        'PyGithub==1.40',
        'requests==2.22.0',
        'jinja2==2.10.1',
        'boltons==18.0.0',
        'twine==1.11.0',
        'six==1.11.0',
        'colorama==0.3.9',
        'wheel==0.33.4',
        'packaging==19.0'
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
