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
    monkeypatch.setattr(qp, "_rauchtest", lambda *a, **k: [], raising=False)


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


# ------------------------------------------- Pflicht-Rauchtest vor dem Zippen
# Der 08.09.-Bau prüfte nichts am Erzeugnis: das ZIP ging mit nicht ladbarem Pillow,
# ohne yt-dlp-ejs und ohne ffmpeg/deno als Release-Anhang hinaus.

def test_kein_zip_wenn_der_rauchtest_scheitert(qp, repo, monkeypatch, tmp_path):
    _netz_attrappen(qp, monkeypatch)
    gesehen = {}

    def rauchtest(paket, *rest, **kw):
        # Der Rauchtest sieht das FERTIGE Paket (bin, Lizenzen, Startdatei schon da).
        gesehen["inhalt"] = _alle_dateien(paket)
        return ["PIL.Image: ImportError: cannot import name '_imaging'"]
    monkeypatch.setattr(qp, "_rauchtest", rauchtest)
    aus = tmp_path / "probebau"
    with pytest.raises(qp.BauFehler, match="Rauchtest"):
        qp.main(["--ausgabe", str(aus)])
    assert not (aus / "SyncYouTube-Quellstart.zip").exists(), "ZIP trotz rotem Rauchtest"
    assert not (aus / "SyncYouTube-Quellstart.zip.sha256").exists()
    assert {"System/bin/deno.exe", "LICENSE", "SyncYouTube-Quellstart.bat",
            "System/youtube_app.py", "python/python.exe"} <= gesehen["inhalt"]


def test_rauchtest_laedt_jedes_noetige_modul(qp):
    laden, finden = qp._probe_module()
    # Jedes winrt-Modul, das medien_smtc importiert (Auto-Discovery, auch künftige).
    fehlend = sorted(_winrt_importe() - set(laden))
    assert not fehlend, f"Rauchtest lädt nicht: {fehlend}"
    # PIL.Image lädt die Binärteile (_imaging) — genau daran scheiterte v.1.2.6.
    assert {"PIL.Image", "yt_dlp", "yt_dlp_ejs"} <= set(laden)
    # vlc nur FINDEN: import vlc lädt die libvlc des installierten VLC, nicht aus dem Paket.
    assert "vlc" in finden
    # Jede Verteilung aus PAKETE ist mit mindestens einem ihrer Module vertreten
    # (Zuordnung aus den Paket-Angaben der venv, nicht aus einer Handliste).
    zu_verteilung = md.packages_distributions()
    geprueft = [m.split(".")[0] for m in list(laden) + list(finden)]
    ohne_probe = []
    for eintrag in qp.PAKETE:
        name = _normname(_zerlegen(eintrag)[0])
        module = {m for m, v in zu_verteilung.items() if name in {_normname(x) for x in v}}
        if not module & set(geprueft):
            ohne_probe.append(name)
    assert not ohne_probe, f"Rauchtest prüft diese Pakete nicht: {ohne_probe}"


def test_rauchtest_ist_ohne_winrt_importe_blind_und_bricht_ab(qp, tmp_path, monkeypatch):
    _schreiben(str(tmp_path / "medien_smtc.py"), "import os\n")
    monkeypatch.setattr(qp, "SYSTEM", str(tmp_path))
    with pytest.raises(qp.BauFehler, match="winrt"):
        qp._probe_module()


def test_abi_scan_gegen_die_paket_fassung(qp, tmp_path):
    lib = tmp_path / "lib"
    tag = qp.PY_TAG
    for rel in (f"PIL/_imaging.{tag}-win_amd64.pyd",       # passt
                "winrt/_winrt.pyd",                          # ohne Marke (stabile ABI)
                "wrapt/_wrappers.cp312-win_amd64.pyd",       # falsche Fassung
                f"x/_y.{tag}-win32.pyd",                     # falsche Plattform
                "z/__pycache__/m.cpython-312.pyc"):          # Bytecode fremder Fassung
        _schreiben(str(lib / rel), b"")
    befunde = qp._abi_fehler(str(lib), tag)
    text = "\n".join(befunde)
    assert len(befunde) == 3, befunde
    for teil in ("_wrappers.cp312-win_amd64.pyd", f"_y.{tag}-win32.pyd", "m.cpython-312.pyc"):
        assert teil in text, teil


def test_paket_fassung_aus_der_pth_datei(qp, tmp_path):
    _schreiben(str(tmp_path / "python314._pth"), "python314.zip\n")
    assert qp._paket_tag(str(tmp_path)) == "cp314"
    assert qp._paket_tag(str(tmp_path / "leer")) is None


def test_je_verteilung_genau_ein_dist_info(qp, tmp_path):
    lib = tmp_path / "lib"
    for d in ("yt_dlp-2026.7.4.dist-info", "yt_dlp-2026.8.19.dist-info",
              "wrapt-2.2.2.dist-info", "winrt_runtime-3.2.1.dist-info"):
        _schreiben(str(lib / d / "METADATA"), "x")
    befunde = qp._verteilungs_dubletten(str(lib))
    assert len(befunde) == 1 and "yt_dlp" in befunde[0], befunde


def _fertiges_paket(basis):
    """Ein Paket in der Form, die main() baut (für die Struktur-Prüfung)."""
    kopiert = ["System/youtube_app.py", "System/lizenzen/pywinrt_LICENSE.txt"]
    for rel in ["LICENSE", "LIZENZEN.md", "README.md", "SyncYouTube-Quellstart.bat",
                "python/python.exe", "python/python314._pth", "lib/yt_dlp/__init__.py",
                *kopiert, "System/bin/ffmpeg.exe", "System/bin/ffprobe.exe",
                "System/bin/deno.exe"]:
        _schreiben(os.path.join(basis, rel), b"x")
    return kopiert


def test_struktur_pruefung(qp, tmp_path):
    paket = str(tmp_path / "paket")
    kopiert = _fertiges_paket(paket)
    assert qp._struktur_fehler(paket, kopiert) == []
    # Werkstatt im Paket, fehlende Pflichtdateien, ein unerwartetes Datum in System/
    _schreiben(os.path.join(paket, "System", "tools", "medien_probe.py"), b"x")
    _schreiben(os.path.join(paket, "System", "config.json"), b"{}")
    os.rename(os.path.join(paket, "LICENSE"), os.path.join(paket, "LICENSE.weg"))
    os.rename(os.path.join(paket, "System", "bin", "deno.exe"),
              os.path.join(paket, "deno.weg"))
    os.rename(os.path.join(paket, "System", "lizenzen", "pywinrt_LICENSE.txt"),
              os.path.join(paket, "lizenz.weg"))
    text = "\n".join(qp._struktur_fehler(paket, kopiert))
    for teil in ("System/tools/medien_probe.py", "System/config.json", "LICENSE",
                 "deno.exe", "pywinrt_LICENSE.txt"):
        assert teil in text, (teil, text)


def test_import_probe_mit_echtem_interpreter(qp, tmp_path):
    # Die Probe läuft wirklich (hier mit dem Test-Python statt des Paket-Pythons):
    # fehlende Module, Module von außerhalb des Pakets und eine falsche Fassung fallen auf.
    _schreiben(str(tmp_path / "im_paket_xyz.py"), "WERT = 1\n")
    befunde = qp._import_probe(sys.executable, str(tmp_path),
                               ["im_paket_xyz", "json", "gibt_es_nicht_xyz"],
                               ["auch_nicht_da_xyz"], tuple(sys.version_info[:2]))
    text = "\n".join(befunde)
    assert "gibt_es_nicht_xyz" in text and "auch_nicht_da_xyz" in text
    assert "json" in text, "json kommt aus dem Test-Python, nicht aus dem Paket"
    assert "im_paket_xyz" not in text, text
    falsch = qp._import_probe(sys.executable, str(tmp_path), ["im_paket_xyz"], [], (3, 99))
    assert any("3.99" in b for b in falsch), falsch


def test_programm_muss_antworten(qp, tmp_path):
    assert qp._antwortet([sys.executable, "--version"], "Python") is None
    assert qp._antwortet([sys.executable, "--version"], "deno ") is not None
    assert qp._antwortet([str(tmp_path / "gibt_es_nicht.exe"), "--version"], "deno ") \
        is not None


def test_interpreter_muss_psf_signiert_sein(qp, tmp_path):
    # Die Prämisse des Quellstart-Wegs: SAC lässt den PSF-signierten Interpreter durch.
    unsigniert = tmp_path / "python.exe"
    _schreiben(str(unsigniert), b"MZ-unsigniert")
    assert qp._signatur_fehler(str(unsigniert)), "unsignierte Datei ging durch"
    # Gültig signiert, aber nicht von der PSF (Microsoft) — auch das ist ein Befund.
    fremd = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                         "WindowsPowerShell", "v1.0", "powershell.exe")
    assert qp._signatur_fehler(fremd), "fremd signierte Datei galt als PSF-signiert"
    basis = getattr(sys, "_base_executable", sys.executable)
    assert qp._signatur_fehler(basis) == [], f"{basis} gilt nicht als PSF-signiert"


def test_rauchtest_verdrahtet_alle_pruefungen(qp, monkeypatch, tmp_path):
    # _rauchtest selbst: jede Prüfung läuft am PAKET (nicht am Bau-Python), und jeder
    # Befund eines Bausteins kommt in der Gesamtliste an.
    paket = str(tmp_path / "paket")
    kopiert = _fertiges_paket(paket)
    py = os.path.join(paket, "python", "python.exe")
    aufrufe = {"antwortet": []}

    def import_probe(p, basis, laden, finden, version):
        aufrufe["probe"] = (p, basis, list(laden), list(finden), version)
        return ["Probe-Befund"]

    def signatur(p):
        aufrufe["signatur"] = p
        return ["Signatur-Befund"]

    def antwortet(befehl, erwartet):
        aufrufe["antwortet"].append(befehl)
        return f"{os.path.basename(befehl[0])}-Befund"
    monkeypatch.setattr(qp, "_import_probe", import_probe)
    monkeypatch.setattr(qp, "_signatur_fehler", signatur)
    monkeypatch.setattr(qp, "_antwortet", antwortet)
    befunde = qp._rauchtest(paket, kopiert)
    assert aufrufe["signatur"] == py
    p, basis, laden, finden, version = aufrufe["probe"]
    assert (p, basis, version) == (py, paket, tuple(sys.version_info[:2]))
    assert (laden, finden) == tuple(map(list, qp._probe_module()))
    gestartet = {os.path.relpath(b[0], paket).replace("\\", "/") for b in aufrufe["antwortet"]}
    assert gestartet == {"System/bin/deno.exe", "System/bin/ffmpeg.exe",
                         "System/bin/ffprobe.exe"}
    for teil in ("Probe-Befund", "Signatur-Befund", "deno.exe-Befund",
                 "ffmpeg.exe-Befund", "ffprobe.exe-Befund"):
        assert teil in befunde, (teil, befunde)
    # ABI-, Dubletten- und Struktur-Befunde kommen ebenso an
    _schreiben(os.path.join(paket, "lib", "w", "_x.cp312-win_amd64.pyd"), b"")
    _schreiben(os.path.join(paket, "System", "tools", "medien_probe.py"), b"")
    text = "\n".join(qp._rauchtest(paket, kopiert))
    assert "_x.cp312-win_amd64.pyd" in text and "System/tools/medien_probe.py" in text


# ---------------------------------------------- Doku: README und LIZENZEN.md

def _readme():
    return open(os.path.join(WURZEL_ECHT, "README.md"), encoding="utf-8").read()


def _lizenzen():
    return open(os.path.join(WURZEL_ECHT, "LIZENZEN.md"), encoding="utf-8").read()


def test_readme_pip_befehle_folgen_der_paketliste(qp):
    # EINE Liste (PAKETE): jeder README-Abschnitt mit pip-Befehlen nennt jedes Paket
    # des Quellstarts, yt-dlp MIT [default] (sonst fehlt yt-dlp-ejs). Bis 24.09.
    # nannte der eine Abschnitt kein [default], der andere kein mutagen/keyring/qrcode.
    erwartet = set()
    for eintrag in qp.PAKETE:
        name, extra, _ = _zerlegen(eintrag)
        erwartet.add(f"{_normname(name)}[{extra}]" if extra else _normname(name))
    geprueft = []
    for abschnitt in re.split(r"\n(?=#{2,3} )", _readme()):
        befehle = (re.findall(r"`(pip install [^`]*)`", abschnitt)
                   + re.findall(r"^\s*(pip install .*)$", abschnitt, re.M))
        if not befehle:
            continue
        titel = abschnitt.strip().splitlines()[0]
        geprueft.append(titel)
        genannt = set()
        for wort in " ".join(befehle).split():
            wort = wort.strip('"\'')
            m = re.fullmatch(r"([A-Za-z0-9_.\-]+)(\[[^\]]+\])?", wort)
            if m:
                genannt.add(_normname(m.group(1)) + (m.group(2) or ""))
        fehlend = sorted(erwartet - genannt)
        assert not fehlend, f"README-Abschnitt {titel!r}: pip-Befehle ohne {fehlend}"
    assert len(geprueft) >= 2, f"zu wenige pip-Abschnitte gefunden: {geprueft}"


def _genannt(text, name):
    norm = lambda s: re.sub(r"[-_.]+", "-", s.lower())    # noqa: E731
    return re.search(rf"(?<![a-z0-9-]){re.escape(norm(name))}(?![a-z0-9-])", norm(text))


def test_lizenzen_nennt_jede_verteilung_des_quellstarts(qp):
    # Jede Verteilung EINZELN (der Familien-Wächter lässt bei winrt schon den
    # Modulnamen genügen — Gegenprüfung 24.09.), dazu der beigelegte pywinrt-Text.
    text = _lizenzen()
    fehlend = [n for n in (_zerlegen(p)[0] for p in qp.PAKETE) if not _genannt(text, n)]
    assert not fehlend, f"LIZENZEN.md nennt nicht: {fehlend}"
    assert "System/lizenzen/pywinrt_LICENSE.txt" in text


def test_lizenzen_msvcp140_nur_mit_beleg():
    # Die C++-Laufzeit steht NICHT unter MIT; eine Angabe dazu braucht die Quelle.
    for absatz in re.split(r"\n\s*\n", _lizenzen()):
        if "msvcp140" in absatz.lower():
            assert "https://learn.microsoft.com/" in absatz, absatz


def test_lizenzen_versionskopf_ist_die_aktuelle_fassung():
    # Bis 24.09. stand „aktuelle Fassung v.1.2.4" im Kopf, ausgeliefert war 1.2.6.
    quelle = open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    fassung = re.search(r'^__version__ = "([^"]+)"', quelle, re.M).group(1)
    kopf = re.search(r"aktuelle Fassung\W*v\.?\s*([0-9.]+)", _lizenzen())
    assert kopf, "LIZENZEN.md nennt keine aktuelle Fassung"
    assert kopf.group(1).rstrip(".") == fassung, \
        f"LIZENZEN.md gilt für v.{kopf.group(1)}, youtube_app ist {fassung}"
