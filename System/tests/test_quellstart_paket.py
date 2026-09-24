# -*- coding: utf-8 -*-
"""Quellstart-Paket (tools/quellstart_paket.py) — Auslieferungs-Wächter (24.09.2026).

Befunde der Analyse „auslieferung" (mit den Korrekturen ihrer Gegenprüfung):

1. Das Paket-Python (Embeddable 3.12.10) passte nicht zum Bau-Python (venv 3.14):
   pip legte cp314-Binärteile in ein 3.12-Paket, Pillow war nicht ladbar, pywinrt
   fehlte ganz. Belastbar ist nur: Paket-Python = Major.Minor des Bau-Pythons, und
   ein Import-Rauchtest am fertigen Paket (pip wertet Umgebungsmarker gegen das
   LAUFENDE Python aus, `--python-version` schützt davor nicht).
2. Das veröffentlichte ZIP hatte kein ffmpeg/ffprobe/deno und kein yt-dlp-ejs.
3. Werkstatt-Dateien (tools/, build_release.py, browser-addon/) wurden ausgeliefert,
   LICENSE/LIZENZEN.md fehlten, der Bauordner wurde nie geleert.

KEIN Netz, KEIN pip, KEIN echtes Embeddable: die Netz-Schritte ersetzen Attrappen,
alles andere (git ls-files, Kopieren, Packen, Rauchtest-Bausteine) läuft echt in
einem Wegwerf-Repo unter tmp_path. Den echten Bau beweist der Probebau
(`--ausgabe System/build_tmp/...`), nicht diese Datei.
"""
import ast
import importlib.metadata as md
import importlib.util
import os
import re
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WURZEL_ECHT = os.path.dirname(MODUL_DIR)
PFAD = os.path.join(MODUL_DIR, "tools", "quellstart_paket.py")
SMTC_PFAD = os.path.join(MODUL_DIR, "medien_smtc.py")
ANFORDERUNGEN = os.path.normpath(os.path.join(
    WURZEL_ECHT, "..", "SyncDashTray", "System", "requirements.txt"))


def _laden():
    spec = importlib.util.spec_from_file_location("quellstart_paket_unter_test", PFAD)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)            # Import baut nichts (nur main() baut)
    return modul


@pytest.fixture
def qp():
    return _laden()


def _winrt_importe():
    """Auto-Discovery wie in test_medien_smtc: welche winrt-Module nutzt der Server?"""
    baum = ast.parse(open(SMTC_PFAD, encoding="utf-8").read())
    genutzt = set()
    for n in ast.walk(baum):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("winrt"):
            genutzt.add(n.module)
        elif isinstance(n, ast.Import):
            genutzt |= {a.name for a in n.names if a.name.startswith("winrt")}
    assert genutzt, "Auto-Discovery findet keine winrt-Importe — der Wächter wäre blind"
    return genutzt


def _verteilung(modul):
    """winrt.windows.media.interop -> winrt-Windows.Media.Interop (pywinrt-Schema)."""
    return "winrt-" + ".".join(t.capitalize() for t in modul.split(".")[1:])


def _normname(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def _zerlegen(eintrag):
    """'yt-dlp[default]==2026.8.19' -> ('yt-dlp', 'default', '2026.8.19')."""
    m = re.fullmatch(r"([A-Za-z0-9_.\-]+)(?:\[([^\]]+)\])?(?:==([^\s;]+))?", eintrag)
    assert m, f"PAKETE-Eintrag nicht lesbar: {eintrag!r}"
    return m.group(1), m.group(2), m.group(3)


# ------------------------------------------------ Befund 1: Paket-Python + pip

def test_paket_python_ist_das_bau_python(qp):
    # Paket-Python und Binärteile dürfen nie auseinanderlaufen: pip installiert mit
    # dem Bau-Python, also muss das ausgelieferte Python dieselbe Fassung sein.
    teile = qp.PY_VER.split(".")
    assert teile[:2] == [str(sys.version_info.major), str(sys.version_info.minor)], \
        f"Paket-Python {qp.PY_VER} passt nicht zum Bau-Python {sys.version.split()[0]}"
    assert f"/{qp.PY_VER}/python-{qp.PY_VER}-embed-amd64.zip" in qp.PY_URL
    assert qp.PY_URL.startswith("https://www.python.org/ftp/python/")
    # Der Zwischenspeicher trägt die Fassung im Namen: ein altes 3.12-Embeddable
    # darf nie als 3.14 durchgehen (bis 24.09. hieß er fassungslos python-embed.zip).
    assert qp.PY_VER in os.path.basename(qp._embed_pfad())


def test_pip_nur_fertige_raeder_ohne_bytecode(qp, monkeypatch, tmp_path):
    aufrufe = []

    def run(befehl, **kw):
        aufrufe.append(befehl)
        return type("Lauf", (), {"returncode": 0})()
    monkeypatch.setattr(qp.subprocess, "run", run)
    lib = str(tmp_path / "lib")
    qp._pakete_holen(lib)
    assert len(aufrufe) == 1, aufrufe
    befehl = aufrufe[0]
    assert befehl[:3] == [sys.executable, "-m", "pip"] and "install" in befehl, befehl
    # Nur fertige Räder: eine sdist würde mit dem Bau-Compiler für das Bau-Python
    # gebaut — genau die Falle, die den 08.09.-Bau unbrauchbar machte.
    assert "--only-binary=:all:" in befehl
    # Kein Bytecode des Bau-Pythons im Paket (08.09.: 1.361 nutzlose cpython-314.pyc).
    assert "--no-compile" in befehl
    i = befehl.index("--target")
    assert befehl[i + 1] == lib
    for paket in qp.PAKETE:
        assert paket in befehl, f"{paket} wird nicht installiert"


def test_pakete_gepinnt_und_yt_dlp_ejs_dabei(qp):
    # Ungepinnt zog jeder Bau andere Fassungen als die exe desselben Releases.
    ungepinnt = [p for p in qp.PAKETE if _zerlegen(p)[2] is None]
    assert not ungepinnt, f"ungepinnt: {ungepinnt}"
    extras = {_normname(_zerlegen(p)[0]): _zerlegen(p)[1] for p in qp.PAKETE}
    # yt-dlp-ejs kommt NUR über das Extra „default" (Required for full YouTube support).
    assert extras.get("yt-dlp") == "default", "yt-dlp ohne [default]: yt-dlp-ejs fehlt"


def test_pakete_enthalten_pywinrt(qp):
    # Jede winrt-Verteilung, die medien_smtc wirklich importiert (Auto-Discovery),
    # plus die Laufzeit selbst — sonst meldet der VLC-Motor im Quellstart nichts an.
    namen = {_normname(_zerlegen(p)[0]) for p in qp.PAKETE}
    erwartet = {"winrt-runtime"} | {_normname(_verteilung(m)) for m in _winrt_importe()}
    fehlend = sorted(erwartet - namen)
    assert not fehlend, f"im Quellstart fehlten: {fehlend}"


def _anforderungen():
    pins = {}
    for zeile in open(ANFORDERUNGEN, encoding="utf-8"):
        zeile = zeile.split("#", 1)[0].strip()
        m = re.fullmatch(r"([A-Za-z0-9_.\-]+)(?:\[[^\]]+\])?\s*==\s*(\S+)", zeile)
        if m:
            pins[_normname(m.group(1))] = m.group(2)
    return pins


def test_pins_wie_requirements_und_exe(qp):
    # Eine Wahrheit: wo die Familien-requirements.txt pinnt, gilt ihr Pin; die übrigen
    # tragen die Fassung, die im Bau-Python liegt und damit auch in der exe landet.
    # Ohne die Familie (öffentliches Repo) gibt es diese Datei nicht.
    if not os.path.isfile(ANFORDERUNGEN):
        pytest.skip("SyncDashTray/System/requirements.txt fehlt (Repo allein ausgecheckt)")
    pins = _anforderungen()
    abweichend = []
    for eintrag in qp.PAKETE:
        name, _extra, fassung = _zerlegen(eintrag)
        soll = pins.get(_normname(name)) or md.version(name)
        if fassung != soll:
            abweichend.append(f"{name}: Paket {fassung}, Soll {soll}")
    assert not abweichend, abweichend
