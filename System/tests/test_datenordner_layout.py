# -*- coding: utf-8 -*-
"""Startpfade isoliert auswerten, ohne App-Import oder echte Zustandsdateien.

Die originale Pfadinitialisierung läuft mit gefälschtem sys.frozen/executable.
Alle Dateien und Verzeichnisse entstehen ausschließlich in tmp_path.
"""
import ast
import glob
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


QUELLE = Path(__file__).resolve().parents[1] / "youtube_app.py"


def _start(programm, frozen=True, bundle=None):
    baum = ast.parse(QUELLE.read_text(encoding="utf-8"))
    namen = {"_standard_daten_dir", "_daten_dir", "ziel_ordner",
             "_addon_xpi_pfad", "_quell_signatur"}
    zuweisungen = {"BIN_DIR", "CONFIG_PFAD", "QUEUE_PFAD", "GELADEN_PFAD",
                   "PLAYLIST_PFAD", "STATUS_PFAD"}
    raum = {"os": os, "glob": glob,
            "sys": SimpleNamespace(frozen=frozen,
                                   executable=str(programm / "SyncYouTube.exe"),
                                   _MEIPASS=str(bundle or programm / "bundle")),
            "__file__": str(programm / "System" / "youtube_app.py")}
    for knoten in baum.body:
        auswahl = (isinstance(knoten, ast.FunctionDef) and knoten.name in namen)
        if isinstance(knoten, ast.If):
            # Der Startblock und die bin-Rückfallebene; kein main()/PATH-Eingriff.
            auswahl = any(isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in {"SCRIPT_DIR", "BIN_DIR"}
                for t in n.targets) for n in ast.walk(knoten))
        if isinstance(knoten, ast.Assign):
            auswahl = any(isinstance(t, ast.Name) and t.id in zuweisungen
                          for t in knoten.targets)
        if auswahl:
            # DATEN_DIR vor den davon abgeleiteten Dateipfaden bestimmen.
            if isinstance(knoten, ast.Assign) and "_daten_dir" in raum:
                raum["DATEN_DIR"], raum["TESTMODUS"] = raum["_daten_dir"]([], {})
            exec(compile(ast.Module(body=[knoten], type_ignores=[]),
                         str(QUELLE), "exec"), raum)
    return raum


def _layout(tmp_path):
    system = tmp_path / "System"
    system.mkdir()
    (system / "youtube_app.py").write_text("# Quelle\n", encoding="utf-8")
    return system


def test_exe_und_quellstart_teilen_system_daten(tmp_path):
    system = _layout(tmp_path)
    exe, quelle = _start(tmp_path), _start(tmp_path, frozen=False)
    for name in ("DATEN_DIR", "CONFIG_PFAD", "QUEUE_PFAD", "GELADEN_PFAD",
                 "PLAYLIST_PFAD", "STATUS_PFAD"):
        assert exe[name] == quelle[name]
        assert Path(exe[name]) == system or Path(exe[name]).parent == system
    assert exe["PROGRAMM_DIR"] == quelle["PROGRAMM_DIR"] == str(tmp_path)
    assert exe["SCRIPT_DIR"] == str(tmp_path)
    assert quelle["SCRIPT_DIR"] == str(system)


@pytest.mark.parametrize("system_art", ["fehlt", "leer", "verzeichnis_statt_py"])
def test_verteilte_exe_behaelt_daten_neben_exe(tmp_path, system_art):
    if system_art != "fehlt":
        (tmp_path / "System").mkdir()
    if system_art == "verzeichnis_statt_py":
        (tmp_path / "System" / "youtube_app.py").mkdir()
    welt = _start(tmp_path)
    assert welt["DATEN_DIR"] == str(tmp_path)
    assert welt["_daten_dir"]([], {}) == (str(tmp_path), False)


@pytest.mark.parametrize("frozen", [False, True])
def test_testmodus_hat_vorrang_und_behaelt_temp_fallback(tmp_path, frozen):
    _layout(tmp_path)
    welt = _start(tmp_path, frozen=frozen)
    probe = tmp_path / "isolierte_probe"
    assert welt["_daten_dir"](["x", "--testmodus", str(probe)], {}) == (str(probe), True)
    assert probe.is_dir()
    assert welt["_daten_dir"](["x", "--testmodus", "--no-browser"],
                              {"TEMP": str(probe)}) == (str(probe / "ytdl-testmodus"), True)
    assert welt["_daten_dir"](["x", "--testmodus"],
                              {"TMP": str(probe)}) == (str(probe / "ytdl-testmodus"), True)


def test_technik_downloads_addon_und_signatur_ziehen_nicht_um(tmp_path):
    system = _layout(tmp_path)
    for ort in (tmp_path, system):
        (ort / "bin").mkdir()
        addon = ort / "browser-addon" / "dist"
        addon.mkdir(parents=True)
        (addon / "probe.xpi").write_bytes(b"addon")
    for frozen, code in ((True, tmp_path), (False, system)):
        welt = _start(tmp_path, frozen=frozen)
        assert welt["BIN_DIR"] == str(code / "bin")
        assert welt["_addon_xpi_pfad"]() == str(code / "browser-addon" / "dist" / "probe.xpi")
        welt["CFG"] = {}
        assert welt["ziel_ordner"]() == str(tmp_path / "Downloads")
        welt["_HEISS_NACHLADBAR"] = set()
        vorher = welt["_quell_signatur"]()
        (code / "neues_backend.py").write_text("# Technik\n", encoding="utf-8")
        assert welt["_quell_signatur"]() > vorher
        welt["TESTMODUS"] = True
        welt["DATEN_DIR"] = str(tmp_path / "probe")
        assert welt["ziel_ordner"]() == str(tmp_path / "probe" / "Downloads")


def test_exe_bin_faellt_weiter_auf_bundle_zurueck(tmp_path):
    _layout(tmp_path)
    bundle = tmp_path / "entpackt"
    (bundle / "bin").mkdir(parents=True)
    welt = _start(tmp_path, bundle=bundle)
    assert welt["DATEN_DIR"] == str(tmp_path / "System")
    assert welt["BIN_DIR"] == str(bundle / "bin")
    # Ein bin nur unter System wurde auch bisher von der exe nicht benutzt.
    (tmp_path / "System" / "bin").mkdir()
    assert _start(tmp_path, bundle=bundle)["BIN_DIR"] == str(bundle / "bin")
