# -*- mode: python -*-

import os
import sys
import platform

block_cipher = None

windows = platform.system().lower() == 'windows'

datas = [('pyci/resources/changelog.jinja', 'pyci/resources'),
         ('pyci/resources/pyci.ascii', 'pyci/resources')]

python_parent = os.path.abspath(os.path.join(sys.executable, os.pardir))

if not windows:
    for executable in [f for f in os.listdir(python_parent)
        if os.path.isfile(os.path.join(python_parent, f))]:
            data = (os.path.join(python_parent, executable), 'bin')
            datas.append(data)
else:

    if 'scripts' in python_parent.lower():
        for executable in [f for f in os.listdir(python_parent)
            if os.path.isfile(os.path.join(python_parent, f))]:
                data = (os.path.join(python_parent, executable), 'scripts')
                datas.append(data)
    else:
        for executable in [f for f in os.listdir(python_parent)
            if os.path.isfile(os.path.join(python_parent, f))]:
                data = (os.path.join(python_parent, executable), '.')
                datas.append(data)
        scripts_directory = os.path.join(python_parent, 'scripts')
        for executable in [f for f in os.listdir(scripts_directory)
            if os.path.isfile(os.path.join(scripts_directory, f))]:
                data = (os.path.join(scripts_directory, executable), 'scripts')
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
