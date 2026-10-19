# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('D:\\Python Desktop\\POS_V2\\build_profiles\\ABDO_MARKET\\customer_features.json', '.'), ('D:\\Python Desktop\\POS_V2\\.env', '.')]
binaries = []
hiddenimports = ['mysql.connector.locales.eng.client_error']
tmp_ret = collect_all('mysql.connector')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['D:\\Python Desktop\\POS_V2\\pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['django', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HyperPOS_ABDO_MARKET',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
