# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = [('bin', 'bin')]
hiddenimports = ['oberflaeche', 'handy', 'geo', 'vpn', 'update', 'medien_smtc', 'windows_kennung',
                 'cookie_kopie']
tmp_ret = collect_all('yt_dlp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('yt_dlp_ejs')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pykakasi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# pywinrt für die Windows-Medienanmeldung des VLC-Motors (medien_smtc.py,
# 23.09.2026). winrt ist ein Namespace-Paket aus mehreren Verteilungen mit
# .pyd-Dateien und einer eigenen msvcp140.dll: collect_all holt .pyd, DLL und
# Metadaten. Die tieferen Namespace-Ebenen (winrt.windows.*) meldet collect_all
# NICHT als Module (gemessen 23.09.: nur winrt._winrt*, winrt.runtime,
# winrt.system) — darum die genutzten Module ausdrücklich dazu. medien_smtc
# importiert sie erst zur Laufzeit; fehlen sie, läuft die exe ohne Overlay.
tmp_ret = collect_all('winrt')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
hiddenimports += ['winrt.runtime', 'winrt.windows.foundation', 'winrt.windows.media',
                  'winrt.windows.media.interop', 'winrt.windows.storage.streams']


a = Analysis(
    ['youtube_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='SyncYouTube',
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
