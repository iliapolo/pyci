# -*- mode: python -*-

import os
import sys
import platform

block_cipher = None

datas = [('pyci/resources/changelog.jinja', 'pyci/resources'),
         ('pyci/resources/pyci.ascii', 'pyci/resources'),
         ('pyci/resources/virtualenv.py', 'pyci/resources'),
         ('pyci/resources/virtualenv_support/pip-19.1.1-py2.py3-none-any.whl', 'pyci/resources/virtualenv_support'),
         ('pyci/resources/virtualenv_support/setuptools-41.0.1-py2.py3-none-any.whl', 'pyci/resources/virtualenv_support'),
         ('pyci/resources/virtualenv_support/wheel-0.33.4-py2.py3-none-any.whl', 'pyci/resources/virtualenv_support')]

# This ugly hack is courtesy of the following issue:
# https://github.com/pyinstaller/pyinstaller/issues/4064#issuecomment-496097756

import distutils
if distutils.distutils_path.endswith('__init__.py'):
    distutils.distutils_path = os.path.dirname(distutils.distutils_path)

# This ugly hack is courtesy of setuptools importing these modules dynamically.
# Therefore pyinstaller has no idea they should be included.

hidden_imports = [
    'setuptools._vendor.packaging.version',
    'setuptools._vendor.packaging.specifiers',
    'setuptools._vendor.pyparsing',
    'six.moves.html_parser'
]

a = Analysis(['pyci/shell/main.py'],
             pathex=['.'],
             binaries=[],
             datas=datas,
             hiddenimports=hidden_imports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='pyci',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True)