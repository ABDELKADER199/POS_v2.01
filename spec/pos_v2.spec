# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for HyperPOS V2"""
import os
import sys

# Project paths
PROJECT_ROOT = r'D:\Python Desktop\POS_V2'
VENV_SITE_PACKAGES = r'D:\Python Desktop\.venv\Lib\site-packages'

# Collect all data files needed for the app
datas = [
    (os.path.join(PROJECT_ROOT, '.env'), '.'),
]

# Add any additional files like images/icons
for asset in ['assets', 'icons', 'images']:
    path = os.path.join(PROJECT_ROOT, asset)
    if os.path.exists(path):
        datas.append((path, asset))

# Hidden imports (modules PyInstaller might miss)
hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtPrintSupport',
    'mysql.connector',
    'bcrypt',
    'dotenv',
    'logging',
    'logging.handlers',
    'json',
    'os',
    'sys',
    'threading',
    'time',
    'datetime',
    're',
    'shutil',
    'subprocess',
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[PROJECT_ROOT, VENV_SITE_PACKAGES],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HyperPOS_V2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version='2.0.0',
)
