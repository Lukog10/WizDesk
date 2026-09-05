# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['wiz/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('LICENSE', '.'),
        ('THIRD_PARTY_LICENSES.md', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtSvg',
        'pynput.keyboard._win32',
        'psutil',
        'win32gui',
        'win32process',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WizDesk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                    # Disable UPX to prevent antivirus false positives
    console=False,                # Silent GUI mode without black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/wizdesk.ico',
    version='version.txt',        # Windows PE resource metadata
    uac_admin=False,              # Standard user privileges (asInvoker)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WizDesk',
)
