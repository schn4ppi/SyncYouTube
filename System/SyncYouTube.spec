# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Die PC-Oberfläche setzt oberflaeche.py seit dem Strukturumbau (25.11.2026) aus
# Dateien zusammen; sie liegen in der exe als Daten (geprüft von build_release.py,
# oberflaeche_fehlt).
datas = [('pc_oberflaeche', 'pc_oberflaeche'), ('layout_kern.js', '.')]
binaries = [('bin', 'bin')]
# Die Seiten aus youtube_app.HEISSE_SEITEN samt Bausteinen (oberflaeche, handy,
# fernbedienung, medien_session) lädt der Router über ihren NAMEN
# (importlib.import_module in _seite_frisch); kein Import-Scanner sieht sie.
# Ohne diese Einträge fehlte fernbedienung in der exe (Nacharbeit Gruppe 7,
# 25.09.2026; Wächter test_exe_nimmt_jede_heisse_seite_mit).
hiddenimports = ['oberflaeche', 'handy', 'fernbedienung', 'medien_session',
                 'geo', 'vpn', 'update', 'medien_smtc', 'windows_kennung', 'cookie_kopie',
                 'abrufweg']
tmp_ret = collect_all('yt_dlp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('yt_dlp_ejs')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pykakasi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# pywinrt für die Windows-Medienanmeldung des VLC-Motors (medien_smtc.py,
# 23.09.2026). winrt ist ein Namespace-Paket aus mehreren Verteilungen mit
# .pyd-Dateien (bis pywinrt 3 auch einer eigenen msvcp140.dll): collect_all holt .pyd, DLL und
# Metadaten. Die tieferen Namespace-Ebenen (winrt.windows.*) meldet collect_all
# NICHT als Module (gemessen 23.09.: nur winrt._winrt*, winrt.runtime,
# winrt.system) — darum die genutzten Module ausdrücklich dazu. medien_smtc
# importiert sie erst zur Laufzeit; fehlen sie, läuft die exe ohne Overlay.
tmp_ret = collect_all('winrt')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
hiddenimports += ['winrt.runtime', 'winrt.windows.foundation', 'winrt.windows.media',
                  'winrt.windows.media.interop', 'winrt.windows.storage.streams']


a = Analysis(
    ['start_exe.py'],              # kleine Startdatei, siehe dort (Avira-Fehlalarm ab 512 KiB)
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


# Lizenztexte (Techdebt-Durchsicht 25.11.2026): Freizügige Lizenzen verlangen, dass
# Copyright-Vermerk und Lizenztext MIT ausgeliefert werden. Bis 1.4.0 lagen der exe
# nur die Texte bei, die zufällig mit den Metadaten kamen (13 von rund 40 Paketen).
# Jetzt kommt für jede Verteilung, deren Module nach der Analyse in der exe stehen,
# jede Lizenzdatei aus ihrer .dist-info mit, nach lizenzen/<Verteilung>/; dazu
# PyInstaller (Startprogramm) und Pythons eigene LICENSE.txt (samt OpenSSL, Tcl/Tk,
# SQLite und den anderen Teilen, die python.org mitliefert).
import importlib.metadata as _md
import os as _os
import sys as _sys


def _lizenz_dateien(analyse, immer=("pyinstaller",)):
    zuordnung = _md.packages_distributions()
    oben = {str(e[0]).replace("\\", "/").split("/")[0].split(".")[0]
            for e in [*analyse.pure, *analyse.binaries, *analyse.datas]}
    verteilungen = {d for m in oben for d in zuordnung.get(m, [])} | set(immer)
    dazu = []
    for name in sorted(verteilungen):
        try:
            dateien = _md.distribution(name).files or []
        except _md.PackageNotFoundError:
            continue
        for datei in dateien:
            teile = datei.parts
            if len(teile) < 2 or not teile[0].endswith(".dist-info"):
                continue
            rest = "/".join(teile[1:])
            if any(z in rest.upper() for z in ("LICEN", "COPYING", "NOTICE")):
                dazu.append((f"lizenzen/{name}/{rest}", str(datei.locate()), "DATA"))
    python_lizenz = _os.path.join(_sys.base_prefix, "LICENSE.txt")
    if _os.path.isfile(python_lizenz):
        dazu.append(("lizenzen/python/LICENSE.txt", python_lizenz, "DATA"))
    return dazu


a.datas += _lizenz_dateien(a)
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
