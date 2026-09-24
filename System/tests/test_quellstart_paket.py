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
import subprocess
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


# ------------------------------------------ Befund 2/3: Inhalt und Bauordner

# Ein Wegwerf-Repo mit derselben Form wie SyncYouTube: versionierte Laufzeit-Dateien,
# Werkstatt-Dateien, gitignored bin/ und ein Nutzerdatum, das NIE mitdarf.
_VERSIONIERT = {
    "LICENSE": "GPL-3.0 Text\n",
    "LIZENZEN.md": "# Lizenzen\n",
    "README.md": "# SyncYouTube\n",
    "_LIESMICH.txt": "Kurzanleitung\n",
    "System/youtube_app.py": "print('app')\n",
    "System/layout_kern.js": "// kern\n",
    "System/lizenzen/pywinrt_LICENSE.txt": "MIT License\n",
    "System/build_release.py": "# bau\n",
    "System/SyncYouTube.spec": "# spec\n",
    "System/MODULE.md": "# karte\n",
    "System/tools/quellstart_paket.py": "# werkstatt\n",
    "System/tools/medien_probe.py": "# drueckt Medientasten\n",
    "System/browser-addon/build.py": "# addon-bau\n",
    "System/browser-addon/shared/popup.js": "// addon\n",
    "System/docs/NAECHSTER_PROMPT.md": "# uebergabe\n",
    "System/tests/test_beispiel.py": "# test\n",
}
_LAUFZEIT = {"System/youtube_app.py", "System/layout_kern.js",
             "System/lizenzen/pywinrt_LICENSE.txt"}
_BIN = {"ffmpeg.exe": b"MZ-ffmpeg", "ffprobe.exe": b"MZ-ffprobe", "deno.exe": b"MZ-deno"}


def _schreiben(pfad, inhalt):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "wb") as f:
        f.write(inhalt if isinstance(inhalt, bytes) else inhalt.encode("utf-8"))


def _lesen(pfad):
    with open(pfad, "rb") as f:
        return f.read()


@pytest.fixture
def repo(tmp_path, monkeypatch, qp):
    wurzel = tmp_path / "repo"
    for rel, inhalt in _VERSIONIERT.items():
        _schreiben(str(wurzel / rel), inhalt)
    for name, inhalt in _BIN.items():                     # wie echt: gitignored
        _schreiben(str(wurzel / "System" / "bin" / name), inhalt)
    _schreiben(str(wurzel / "System" / "config.json"), '{"geheim": 1}')   # Nutzerdatum
    subprocess.run(["git", "init", "-q"], cwd=wurzel, check=True)
    subprocess.run(["git", "add", "--", *_VERSIONIERT], cwd=wurzel, check=True)
    system = str(wurzel / "System")
    monkeypatch.setattr(qp, "WURZEL", str(wurzel))
    monkeypatch.setattr(qp, "SYSTEM", system)
    monkeypatch.setattr(qp, "BAU", os.path.join(system, "build_tmp", "quellstart"))
    monkeypatch.setattr(qp, "DIST", os.path.join(system, "dist_exe"), raising=False)
    return wurzel


def _alle_dateien(basis):
    gefunden = set()
    for ordner, _, dateien in os.walk(basis):
        for d in dateien:
            gefunden.add(os.path.relpath(os.path.join(ordner, d), basis).replace("\\", "/"))
    return gefunden


def test_kopie_nur_laufzeit_ohne_werkstatt(qp, repo, tmp_path):
    # Werkstatt ≠ Produkt: tools/ (medien_probe DRÜCKT Medientasten), build_release.py,
    # browser-addon/ (ohne .xpi zur Laufzeit nutzlos), docs/, tests/, .spec, .md
    # bleiben draußen. Nutzerdaten ohnehin (nur git ls-files).
    paket = tmp_path / "paket"
    qp._quellen_kopieren(str(paket / "System"))
    assert _alle_dateien(str(paket)) == _LAUFZEIT


def test_bin_wird_ausdruecklich_mitgeliefert(qp, repo, tmp_path):
    # System/bin ist gitignored, git ls-files sieht es nie (08.09.: kein ffmpeg/deno
    # im ZIP). Leitplanke P11: kein Selbst-Download — also ausdrücklich mitkopieren.
    ziel_sys = tmp_path / "paket" / "System"
    qp._bin_kopieren(str(ziel_sys))
    for name, inhalt in _BIN.items():
        assert _lesen(str(ziel_sys / "bin" / name)) == inhalt, name
    os.rename(str(repo / "System" / "bin" / "deno.exe"), str(repo / "System" / "bin" / "deno.alt"))
    with pytest.raises(qp.BauFehler, match="deno.exe"):
        qp._bin_kopieren(str(tmp_path / "paket2" / "System"))


def test_lizenz_und_readme_aus_der_wurzel(qp, repo, tmp_path):
    # GPLv3 §4: der eigene Lizenztext gehört in jede Weitergabe (08.09.: fehlte).
    paket = tmp_path / "paket"
    qp._wurzel_dateien_kopieren(str(paket))
    assert _alle_dateien(str(paket)) == {"LICENSE", "LIZENZEN.md", "README.md"}
    for name in ("LICENSE", "LIZENZEN.md", "README.md"):
        assert _lesen(str(paket / name)) == _lesen(str(repo / name))
    os.rename(str(repo / "LICENSE"), str(repo / "LICENSE.alt"))
    with pytest.raises(qp.BauFehler, match="LICENSE"):
        qp._wurzel_dateien_kopieren(str(tmp_path / "paket2"))


def test_pywinrt_lizenztext_liegt_versioniert_bei():
    # pywinrts dist-info bringt KEINE Lizenzdatei mit (venv geprüft) — der MIT-Text
    # (github.com/pywinrt/pywinrt, Marke v3.2.1) liegt darum selbst bei, und die
    # Whitelist-.gitignore darf ihn nicht verschlucken.
    rel = "System/lizenzen/pywinrt_LICENSE.txt"
    text = open(os.path.join(WURZEL_ECHT, rel), encoding="utf-8").read()
    for pflicht in ("MIT License", "Copyright (c) Microsoft Corporation",
                    "Copyright (c) 2021-2025 David Lechner",
                    "The above copyright notice and this permission notice"):
        assert pflicht in text, pflicht
    ignoriert = subprocess.run(["git", "check-ignore", "-q", rel], cwd=WURZEL_ECHT)
    assert ignoriert.returncode == 1, f"{rel} wird von .gitignore verschluckt"


def test_frischer_bauordner_legt_alten_beiseite(qp, tmp_path):
    # pip --target in ein altes lib/ ließ doppelte dist-info liegen (08.09.: zwei
    # yt-dlp-Fassungen im ZIP). Frisch bauen — den alten Ordner UMBENENNEN, nie löschen.
    paket = tmp_path / "paket"
    _schreiben(str(paket / "lib" / "yt_dlp-2026.7.4.dist-info" / "METADATA"), "alt")
    qp._frischer_bauordner(str(paket))
    assert paket.is_dir() and not os.listdir(str(paket))
    beiseite = [p for p in tmp_path.iterdir() if p.name.startswith("paket_alt_")]
    assert len(beiseite) == 1, list(tmp_path.iterdir())
    assert _lesen(str(beiseite[0] / "lib" / "yt_dlp-2026.7.4.dist-info" / "METADATA")) == b"alt"


def _netz_attrappen(qp, monkeypatch):
    """Ersetzt nur die Netz-Schritte (python.org, PyPI) und den Rauchtest."""
    def python_holen(ziel):
        _schreiben(os.path.join(ziel, "python.exe"), b"MZ-python")
        _schreiben(os.path.join(ziel, "python314._pth"), "python314.zip\n.\nimport site\n")

    def pakete_holen(lib):
        _schreiben(os.path.join(lib, "yt_dlp", "__init__.py"), "")
        _schreiben(os.path.join(lib, "yt_dlp-2026.8.19.dist-info", "METADATA"), "x")
        # pip-Starter tragen den Pfad des BAU-Pythons (JBs Benutzerordner) in sich
        _schreiben(os.path.join(lib, "bin", "yt-dlp.exe"), b"#!C:\\Users\\bau\\python.exe")
    monkeypatch.setattr(qp, "_python_holen", python_holen)
    monkeypatch.setattr(qp, "_pakete_holen", pakete_holen)
    monkeypatch.setattr(qp, "_rauchtest", lambda paket: [], raising=False)


def _zip_namen(pfad):
    import zipfile
    with zipfile.ZipFile(pfad) as z:
        return set(z.namelist())


def test_ausgabe_ort_laesst_veroeffentlichte_zip_unberuehrt(qp, repo, monkeypatch, tmp_path):
    _netz_attrappen(qp, monkeypatch)
    veroeffentlicht = os.path.join(qp.DIST, "SyncYouTube-Quellstart.zip")
    _schreiben(veroeffentlicht, b"VEROEFFENTLICHT")
    _schreiben(veroeffentlicht + ".sha256", b"abc  SyncYouTube-Quellstart.zip\n")
    aus = tmp_path / "probebau"
    qp.main(["--ausgabe", str(aus)])
    assert _lesen(veroeffentlicht) == b"VEROEFFENTLICHT", "dist_exe wurde angefasst"
    assert _lesen(veroeffentlicht + ".sha256") == b"abc  SyncYouTube-Quellstart.zip\n"
    ziel = aus / "SyncYouTube-Quellstart.zip"
    namen = _zip_namen(str(ziel))
    pflicht = {"SyncYouTube-Quellstart.bat", "LICENSE", "LIZENZEN.md", "README.md",
               "python/python.exe", "lib/yt_dlp/__init__.py", "System/youtube_app.py",
               "System/layout_kern.js", "System/lizenzen/pywinrt_LICENSE.txt",
               "System/bin/ffmpeg.exe", "System/bin/ffprobe.exe", "System/bin/deno.exe"}
    assert pflicht <= namen, sorted(pflicht - namen)
    verboten = [n for n in namen if n.startswith(("System/tools/", "System/tests/",
                                                  "System/docs/", "System/browser-addon/",
                                                  "lib/bin/"))
                or n in ("System/build_release.py", "System/config.json", "_LIESMICH.txt")]
    assert not verboten, verboten
    # Prüfsumme liegt daneben (Release-Asset „.sha256")
    import hashlib
    soll = hashlib.sha256(_lesen(str(ziel))).hexdigest() + "  SyncYouTube-Quellstart.zip\n"
    assert _lesen(str(ziel) + ".sha256").decode("ascii") == soll


def test_altes_ergebnis_wird_beiseitegelegt_nicht_geloescht(qp, repo, monkeypatch):
    # Bricht ein Bau ab, darf am Ziel keine veraltete ZIP stehen, die jemand für
    # frisch hält (Fund 07.08.) — aber sie wird beiseitegelegt, nicht gelöscht.
    _netz_attrappen(qp, monkeypatch)
    alt = os.path.join(qp.DIST, "SyncYouTube-Quellstart.zip")
    _schreiben(alt, b"ALTE-ZIP")
    _schreiben(alt + ".sha256", b"alte-summe")
    qp.main([])
    assert _lesen(alt) != b"ALTE-ZIP" and "System/youtube_app.py" in _zip_namen(alt)
    gerettet = {}
    for ordner, _, dateien in os.walk(qp.BAU):
        for d in dateien:
            if d.startswith("SyncYouTube-Quellstart.zip"):
                gerettet[d] = _lesen(os.path.join(ordner, d))
    assert gerettet == {"SyncYouTube-Quellstart.zip": b"ALTE-ZIP",
                        "SyncYouTube-Quellstart.zip.sha256": b"alte-summe"}, gerettet
