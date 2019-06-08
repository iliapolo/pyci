# -*- mode: python -*-

import os
import sys
import platform

block_cipher = None

windows = platform.system().lower() == 'windows'

datas = [('pyci/resources/changelog.jinja', 'pyci/resources'),
         ('pyci/resources/pyci.ascii', 'pyci/resources')]

a = Analysis(['pyci/shell/main.py'],
             pathex=['.'],
             binaries=[],
             datas=datas,
             hiddenimports=[],
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
