# -*- mode: python -*-

import os
import sys

block_cipher = None

datas = [('pyci/resources/changelog.jinja', 'pyci/resources')]

bin_directory = os.path.abspath(os.path.join(sys.executable, os.pardir))

for bin in [f for f in os.listdir(bin_directory)
    if os.path.isfile(os.path.join(bin_directory, f))]:
        data = (os.path.join(bin_directory, bin), 'bin')
        datas.append(data)

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
