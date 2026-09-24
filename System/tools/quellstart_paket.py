# -*- coding: utf-8 -*-
"""Quellstart-Paket bauen (Pete-Fall 07.08.2026: Windows **Smart App Control**
blockiert unsere PyInstaller-exe — jeder Build ist ein frisch gehashtes
UNIKAT ohne Signatur und ohne Reputation, und SAC kennt kein „Trotzdem
ausführen").

Der Quellstart-Weg umgeht nichts, er nimmt den sauberen Pfad: der offizielle
python.org-Interpreter ist von der Python Software Foundation SIGNIERT, unsere
.py-Dateien sind für SAC Daten, keine Programme. ffmpeg/ffprobe/deno aus
System/bin liegen bei (Leitplanke P11: kein Selbst-Download beim Nutzer); deno.exe
ist signiert (Deno Land Inc.), ffmpeg/ffprobe sind es nicht — ob Smart App
Control sie durchlässt, ist ungemessen.

Inhalt (Befunde 24.09.2026, das v.1.2.6-ZIP war praktisch nicht lauffähig):
versionierte Laufzeit-Dateien aus System/ (git ls-files, OHNE Werkstatt: tools/,
build_release.py, browser-addon/, docs/, tests/) + System/bin + LICENSE,
LIZENZEN.md, README.md aus der Repo-Wurzel + die gepinnten Pakete in lib/.
Gebaut wird in einem FRISCHEN Ordner (der alte wird umbenannt, nie gelöscht),
und vor dem Zippen läuft ein Pflicht-Rauchtest am fertigen Paket.

Aufruf (Werkstatt, nicht im Auslieferungsweg):
    venv\\Scripts\\python System\\tools\\quellstart_paket.py [--ausgabe ORDNER]
Ergebnis: System\\dist_exe\\SyncYouTube-Quellstart.zip (+ .sha256); mit
--ausgabe landet beides in ORDNER, und dist_exe bleibt unberührt (Probebau).
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

SYSTEM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WURZEL = os.path.dirname(SYSTEM)
BAU = os.path.join(SYSTEM, "build_tmp", "quellstart")
DIST = os.path.join(SYSTEM, "dist_exe")          # veröffentlichte ZIP (Release-Asset)
ZIP_NAME = "SyncYouTube-Quellstart.zip"
# Ausdrücklich mitgeliefert, weil gitignored (System/bin) bzw. außerhalb von System/:
BIN_DATEIEN = ("ffmpeg.exe", "ffprobe.exe", "deno.exe")
WURZEL_DATEIEN = ("LICENSE", "LIZENZEN.md", "README.md")
# Werkstatt ≠ Produkt: nie im Nutzerpaket (medien_probe.py DRÜCKT Medientasten).
WERKSTATT_ORDNER = ("tools", "tests", "docs", "browser-addon")
WERKSTATT_DATEIEN = ("System/build_release.py",)
# Lizenztexte, die kein Paket selbst mitbringt (pywinrt: dist-info ohne LICENSE).
LIZENZTEXTE = ("System/lizenzen/pywinrt_LICENSE.txt",)
# Rauchtest: diese Module lädt das PAKET-Python wirklich (PIL.Image zieht die
# Binärteile _imaging — genau daran scheiterte v.1.2.6), dazu jedes winrt-Modul,
# das medien_smtc importiert (Auto-Discovery in _probe_module).
PROBE_LADEN = ("PIL.Image", "yt_dlp", "yt_dlp_ejs", "mutagen", "pykakasi",
               "keyring", "qrcode", "pystray")
# Nur FINDEN: `import vlc` lädt die libvlc des beim Nutzer installierten VLC —
# das Paket liefert nur den Python-Aufsatz, ein Laden bewiese nichts übers Paket.
PROBE_FINDEN = ("vlc",)


class BauFehler(Exception):
    """Der Bau bricht ab — es entsteht KEIN ZIP (fail-closed)."""


def _sag(text):
    # ASCII-Ausgaben: die Windows-Konsole laeuft auf cp1252 und wirft bei
    # Sonderzeichen einen UnicodeEncodeError (Fund 07.08.). Fremde Fehlertexte
    # (Importfehler, Pfade) koennen Sonderzeichen tragen — darum ersetzen.
    print(str(text).encode("ascii", "replace").decode("ascii"), flush=True)
# Paket-Python = Bau-Python (Befund 24.09.2026): pip installiert mit DIESEM Python
# (sys.executable) und wählt Binärteile für seine Fassung. Bis v.1.2.6 lag im Paket
# ein 3.12.10 neben cp314-Dateien aus der 3.14-venv — Pillow war nicht ladbar,
# pywinrt wäre es auch nicht gewesen. `--python-version` allein schützt nicht:
# Umgebungsmarker wertet pip weiter gegen das LAUFENDE Python aus. Also dieselbe
# Fassung, und der Rauchtest am fertigen Paket bleibt Pflicht.
PY_VER = "{}.{}.{}".format(*sys.version_info[:3])
PY_TAG = "cp{}{}".format(*sys.version_info[:2])     # Marke der Binärteile, z. B. cp314
PY_URL = (f"https://www.python.org/ftp/python/{PY_VER}/"
          f"python-{PY_VER}-embed-amd64.zip")
# Gepinnt wie SyncDashTray/System/requirements.txt (dort ohne Pin: die Fassung der
# Familien-venv, aus der auch die exe gebaut wird) — exe und ZIP eines Releases
# tragen so dieselben Fassungen. Der Wächter test_quellstart_paket gleicht ab.
# yt-dlp[default] bringt yt-dlp-ejs mit („Required for full YouTube support").
PAKETE = ["yt-dlp[default]==2026.8.19", "pystray==0.19.5", "pillow==12.2.0",
          "mutagen==1.48.1", "pykakasi==2.3.0", "keyring==25.7.0", "qrcode==8.2",
          "python-vlc==3.0.21203",
          # Windows-Medienanmeldung des VLC-Motors (medien_smtc.py, JB-Go 23.09.)
          "winrt-runtime==3.2.1", "winrt-Windows.Foundation==3.2.1",
          "winrt-Windows.Media==3.2.1", "winrt-Windows.Media.Interop==3.2.1",
          "winrt-Windows.Storage.Streams==3.2.1"]


def _embed_pfad():
    """Zwischenspeicher des Embeddable MIT Fassung im Namen: ein altes 3.12-Archiv
    (bis 24.09. hieß es fassungslos python-embed.zip) darf nie als 3.14 gelten."""
    return os.path.join(BAU, f"python-{PY_VER}-embed-amd64.zip")


def _python_holen(ziel):
    """Signiertes Embeddable-Python von python.org laden + entpacken."""
    zp = _embed_pfad()
    if not os.path.exists(zp):
        _sag(f"Lade {PY_URL} ...")
        teil = zp + ".teil"                   # halber Download gilt nie als Zwischenspeicher
        urllib.request.urlretrieve(PY_URL, teil)
        os.replace(teil, zp)
    with zipfile.ZipFile(zp) as z:
        z.extractall(ziel)
    # site-packages aktivieren: im ._pth 'import site' einkommentieren und
    # unseren lib-Ordner anhängen (Standard-Kniff des Embeddable-Pakets).
    for name in os.listdir(ziel):
        if name.endswith("._pth"):
            p = os.path.join(ziel, name)
            with open(p, encoding="utf-8") as f:
                text = f.read()
            text = text.replace("#import site", "import site")
            if "..\\lib" not in text:
                text += "..\\lib\n..\\System\n"
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)


def _pakete_holen(lib):
    # --only-binary=:all: — nur fertige Räder, nie eine sdist mit dem Bau-Compiler;
    # --no-compile — kein Bytecode des Bau-Pythons im Paket; --isolated — keine
    # pip-Einstellungen dieses PCs (Index, Proxy) im Bau.
    _sag(f"Installiere Abhaengigkeiten nach: {lib}")
    subprocess.run([sys.executable, "-m", "pip", "--isolated", "install",
                    "--disable-pip-version-check", "--no-warn-script-location",
                    "--only-binary=:all:", "--no-compile",
                    "--target", lib, *PAKETE], check=True)


def _wird_ausgeliefert(rel):
    """Gehört diese versionierte Datei (Pfad wie git ls-files) ins Nutzerpaket?

    Ausschlussliste statt Positivliste (Gegenprüfung 24.09.): layout_kern.js und die
    heiß nachgeladenen Oberflächen werden per Pfad geladen, nicht per import — eine
    Positivliste „was youtube_app importiert" verlöre sie still."""
    rel = rel.replace("\\", "/")
    teile = rel.split("/")
    if rel in WERKSTATT_DATEIEN or "tests" in teile[:-1]:
        return False
    if len(teile) > 2 and teile[0] == "System" and teile[1] in WERKSTATT_ORDNER:
        return False
    return not rel.endswith((".spec", ".md"))


def _quellen_kopieren(ziel_sys):
    """NUR versionierte Laufzeit-Dateien (git ls-files, ohne Werkstatt) — keine
    Nutzerdaten, denn die sind per .gitignore draußen. Gibt die Pfade zurück."""
    dateien = subprocess.run(
        ["git", "ls-files", "System"], cwd=WURZEL, check=True,
        capture_output=True, text=True).stdout.splitlines()
    kopiert = []
    for rel in dateien:
        if not _wird_ausgeliefert(rel):
            continue
        quelle = os.path.join(WURZEL, rel)
        ziel = os.path.join(os.path.dirname(ziel_sys), rel)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(quelle, "rb") as f_in, open(ziel, "wb") as f_out:
            f_out.write(f_in.read())
        kopiert.append(rel)
    return kopiert


def _bin_kopieren(ziel_sys):
    """ffmpeg/ffprobe/deno AUSDRÜCKLICH mitliefern: System/bin ist gitignored, git
    ls-files sieht es nie (das v.1.2.6-ZIP hatte darum weder ffmpeg noch deno — ohne
    Deno liefert YouTube „No video formats found"). Leitplanke P11: kein
    Selbst-Download beim Nutzer. Fehlt eine Datei, bricht der Bau ab."""
    quelle = os.path.join(SYSTEM, "bin")
    ziel = os.path.join(ziel_sys, "bin")
    os.makedirs(ziel, exist_ok=True)
    for name in BIN_DATEIEN:
        q = os.path.join(quelle, name)
        if not os.path.isfile(q):
            raise BauFehler(f"{q} fehlt - ohne {name} kein Quellstart-Paket.")
        shutil.copy2(q, os.path.join(ziel, name))


def _wurzel_dateien_kopieren(paket):
    """LICENSE (GPLv3 §4: der Lizenztext gehört in jede Weitergabe), LIZENZEN.md und
    README.md liegen außerhalb von System/ und fehlten deshalb bis v.1.2.6."""
    os.makedirs(paket, exist_ok=True)
    for name in WURZEL_DATEIEN:
        q = os.path.join(WURZEL, name)
        if not os.path.isfile(q):
            raise BauFehler(f"{q} fehlt - kein Paket ohne {name}.")
        shutil.copy2(q, os.path.join(paket, name))


def _stempel():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def _frei(pfad):
    """Ein noch nicht vergebener Name (pfad, pfad_1, …) — nichts wird überschrieben."""
    kandidat, n = pfad, 1
    while os.path.exists(kandidat):
        kandidat, n = f"{pfad}_{n}", n + 1
    return kandidat


def _frischer_bauordner(paket):
    """In einem FRISCHEN Ordner bauen: pip --target in ein altes lib/ ließ doppelte
    dist-info liegen (08.09.: yt-dlp 2026.7.4 und 2026.8.19 im selben ZIP), aus git
    entfernte Quellen blieben stehen. Der alte Ordner wird UMBENANNT, nie gelöscht."""
    if os.path.exists(paket):
        alt = _frei(f"{paket}_alt_{_stempel()}")
        os.rename(paket, alt)
        _sag(f"Alter Bauordner beiseitegelegt: {alt}")
    os.makedirs(paket)


def _altes_ergebnis_beiseite(ziel_zip):
    """Eine ZIP (+ .sha256) am Ziel kommt VOR dem Bau weg: bricht er ab, darf keine
    veraltete ZIP liegen bleiben, die jemand für frisch hält (Fund 07.08.). Sie wird
    nach build_tmp/quellstart/beiseite/<Zeitstempel>/ verschoben, nicht gelöscht."""
    ablage = None
    for weg in (ziel_zip, ziel_zip + ".sha256"):
        if os.path.exists(weg):
            if ablage is None:
                ablage = _frei(os.path.join(BAU, "beiseite", _stempel()))
                os.makedirs(ablage)
            shutil.move(weg, os.path.join(ablage, os.path.basename(weg)))
    if ablage:
        _sag(f"Vorheriges Ergebnis beiseitegelegt: {ablage}")


def _zip_eintraege(paket):
    """(Datei, Name im ZIP) — ohne lib/bin: pip-Starter (yt-dlp.exe, keyring.exe …)
    zeigen fest auf das BAU-Python samt Benutzerpfad und sind beim Nutzer nutzlos."""
    for ordner, unter, dateien in os.walk(paket):
        rel_ordner = os.path.relpath(ordner, paket).replace("\\", "/")
        if rel_ordner == "lib":
            unter[:] = [u for u in unter if u != "bin"]
        for d in sorted(dateien):
            voll = os.path.join(ordner, d)
            yield voll, os.path.relpath(voll, paket).replace("\\", "/")


def _packen(paket, ziel_zip):
    os.makedirs(os.path.dirname(ziel_zip), exist_ok=True)
    _sag(f"Packe {ziel_zip}")
    with zipfile.ZipFile(ziel_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for voll, name in _zip_eintraege(paket):
            z.write(voll, name)
    h = hashlib.sha256()
    with open(ziel_zip, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    with open(ziel_zip + ".sha256", "w", encoding="ascii", newline="\n") as f:
        f.write(f"{h.hexdigest()}  {os.path.basename(ziel_zip)}\n")
    return h.hexdigest()


# ---------------------------------------------------------------- Rauchtest
# Pflicht vor dem Zippen, fail-closed: jeder Baustein gibt eine Liste von Befunden
# zurück (leer = in Ordnung); ein einziger Befund, und es entsteht KEIN ZIP.

def _winrt_module():
    """Auto-Discovery: welche winrt-Module importiert medien_smtc.py wirklich?"""
    with open(os.path.join(SYSTEM, "medien_smtc.py"), encoding="utf-8") as f:
        baum = ast.parse(f.read())
    genutzt = set()
    for n in ast.walk(baum):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("winrt"):
            genutzt.add(n.module)
        elif isinstance(n, ast.Import):
            genutzt |= {a.name for a in n.names if a.name.startswith("winrt")}
    if not genutzt:
        raise BauFehler("medien_smtc.py importiert kein winrt-Modul - der Rauchtest "
                        "waere fuer die Windows-Medienanmeldung blind.")
    return genutzt


def _probe_module():
    """(zu ladende, nur zu findende) Module für die Import-Probe im Paket-Python."""
    return list(PROBE_LADEN) + sorted(_winrt_module()), list(PROBE_FINDEN)


def _paket_tag(python_dir):
    """cpXY des ausgelieferten Pythons, gelesen an seiner pythonXY._pth."""
    if not os.path.isdir(python_dir):
        return None
    for name in os.listdir(python_dir):
        m = re.fullmatch(r"python(\d)(\d+)\._pth", name)
        if m:
            return f"cp{m.group(1)}{m.group(2)}"
    return None


def _abi_fehler(lib, tag):
    """Jede Binärerweiterung muss zur Paket-Fassung passen: `.<tag>-win_amd64.pyd`
    oder ohne Marke (`.pyd`, so heißt die stabile ABI unter Windows). Bytecode
    einer FREMDEN Fassung verrät pip-Kompilat des Bau-Pythons (08.09.: cp314 in 3.12)."""
    befunde = []
    for ordner, _, dateien in os.walk(lib):
        for d in dateien:
            rel = os.path.relpath(os.path.join(ordner, d), lib).replace("\\", "/")
            klein = d.lower()
            if klein.endswith(".pyd"):
                m = re.search(r"\.(cp\d+)-([a-z0-9_]+)\.pyd$", klein)
                if m and (m.group(1) != tag or m.group(2) != "win_amd64"):
                    befunde.append(f"Binaerteil passt nicht zu {tag}-win_amd64: lib/{rel}")
            elif klein.endswith(".pyc"):
                m = re.search(r"\.cpython-(\d+)", klein)
                if m and f"cp{m.group(1)}" != tag:
                    befunde.append(f"Bytecode einer fremden Python-Fassung: lib/{rel}")
    return befunde


def _verteilungs_dubletten(lib):
    """Je Verteilung genau EIN dist-info (08.09.: yt-dlp 2026.7.4 neben 2026.8.19)."""
    gesehen = {}
    if os.path.isdir(lib):
        for name in os.listdir(lib):
            if name.endswith(".dist-info"):
                verteilung = re.sub(r"[-_.]+", "-", name[:-len(".dist-info")].rsplit("-", 1)[0])
                gesehen.setdefault(verteilung.lower(), []).append(name)
    return [f"mehrere Fassungen derselben Verteilung: {', '.join(sorted(v))}"
            for v in gesehen.values() if len(v) > 1]


def _struktur_fehler(paket, kopiert):
    """Pflichtdateien da, und in System/ NUR, was der Bau hineinlegte (versionierte
    Laufzeit-Dateien + bin): eine Werkstatt-Datei oder ein Nutzerdatum fiele auf."""
    befunde = []
    pflicht = [*WURZEL_DATEIEN, "SyncYouTube-Quellstart.bat", "python/python.exe",
               *LIZENZTEXTE, *(f"System/bin/{n}" for n in BIN_DATEIEN)]
    for rel in pflicht:
        if not os.path.isfile(os.path.join(paket, *rel.split("/"))):
            befunde.append(f"fehlt im Paket: {rel}")
    erlaubt = {k.replace("\\", "/") for k in kopiert}
    erlaubt |= {f"System/bin/{n}" for n in BIN_DATEIEN}
    for ordner, _, dateien in os.walk(os.path.join(paket, "System")):
        for d in dateien:
            rel = os.path.relpath(os.path.join(ordner, d), paket).replace("\\", "/")
            if rel not in erlaubt:
                befunde.append(f"unerwartet im Paket: {rel}")
    return befunde


# Läuft IM Paket-Python: lädt/findet die Module, meldet Fassung und Herkunft (JSON).
_PROBE = r"""
import importlib, importlib.util, json, sys
laden, finden = json.loads(sys.argv[1]), json.loads(sys.argv[2])
aus = {"version": list(sys.version_info[:2]), "fehler": {}, "orte": {}}
def ort(m):
    return getattr(m, "__file__", None) or next(iter(getattr(m, "__path__", [])), "")
for name in laden:
    try:
        aus["orte"][name] = ort(importlib.import_module(name))
    except BaseException as e:
        aus["fehler"][name] = type(e).__name__ + ": " + str(e)
for name in finden:
    try:
        spec = importlib.util.find_spec(name)
    except BaseException as e:
        spec, aus["fehler"][name] = None, type(e).__name__ + ": " + str(e)
    if spec is None:
        aus["fehler"].setdefault(name, "nicht gefunden")
    else:
        aus["orte"][name] = spec.origin or ""
print(json.dumps(aus))
"""


def _ohne_python_umgebung():
    return {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}


def _import_probe(py, paket, laden, finden, version):
    """Das Paket-Python (-B: schreibt keinen Bytecode) lädt jedes nötige Modul.
    Geprüft wird auch die HERKUNFT: ein Modul von außerhalb des Pakets bewiese nichts."""
    try:
        lauf = subprocess.run([py, "-B", "-E", "-c", _PROBE, json.dumps(laden),
                               json.dumps(finden)], cwd=paket, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=300, env=_ohne_python_umgebung())
    except (OSError, subprocess.TimeoutExpired) as e:
        return [f"Paket-Python startet nicht: {e}"]
    zeilen = (lauf.stdout or "").strip().splitlines()
    try:
        aus = json.loads(zeilen[-1])
    except (ValueError, IndexError):
        return [f"Import-Probe ohne Ergebnis (Exitcode {lauf.returncode}): "
                f"{(lauf.stderr or '').strip()[-400:]}"]
    befunde = []
    if tuple(aus["version"]) != tuple(version):
        befunde.append("Paket-Python ist {}.{}, erwartet {}.{}".format(*aus["version"], *version))
    for name, fehler in sorted(aus["fehler"].items()):
        befunde.append(f"Modul {name}: {fehler}")
    wurzel = os.path.normcase(os.path.abspath(paket)) + os.sep
    for name, ort in sorted(aus["orte"].items()):
        if not os.path.normcase(os.path.abspath(ort or "?")).startswith(wurzel):
            befunde.append(f"Modul {name} kommt nicht aus dem Paket: {ort}")
    return befunde


def _antwortet(befehl, erwartet):
    """None, wenn das Programm startet und mit `erwartet` antwortet, sonst ein Befund."""
    name = os.path.basename(befehl[0])
    try:
        lauf = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"{name} antwortet nicht: {e}"
    ausgabe = ((lauf.stdout or "") + (lauf.stderr or "")).strip()
    if lauf.returncode != 0 or not ausgabe.lower().startswith(erwartet.lower()):
        return f"{name} {' '.join(befehl[1:])}: Exitcode {lauf.returncode}, {ausgabe[:120]!r}"
    return None


def _signatur_fehler(pfad):
    """Die Prämisse des Quellstart-Wegs: der Interpreter ist von der Python Software
    Foundation signiert (Authenticode). Pfad über die Umgebung, nie in den Befehl."""
    befehl = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
              "$s = Get-AuthenticodeSignature -LiteralPath $env:QS_PRUEFPFAD; "
              "Write-Output $s.Status; Write-Output $s.SignerCertificate.Subject"]
    try:
        lauf = subprocess.run(befehl, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60,
                              env=dict(os.environ, QS_PRUEFPFAD=pfad),
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as e:
        return [f"Signatur von {pfad} nicht pruefbar: {e}"]
    zeilen = [z.strip() for z in (lauf.stdout or "").splitlines() if z.strip()]
    status = zeilen[0] if zeilen else "?"
    signierer = zeilen[1] if len(zeilen) > 1 else ""
    if status != "Valid" or "O=Python Software Foundation" not in signierer:
        return [f"{pfad} ist nicht gueltig PSF-signiert (Status {status}, {signierer!r})"]
    return []


def _rauchtest(paket, kopiert):
    """Alle Prüfungen am FERTIGEN Paket; die Struktur zuletzt, damit auch auffiele,
    wenn eine Probe etwas ins Paket geschrieben hätte."""
    python_dir = os.path.join(paket, "python")
    lib = os.path.join(paket, "lib")
    tag = _paket_tag(python_dir)
    befunde = []
    if tag is None:
        befunde.append("keine pythonXY._pth im Paket - Fassung unbekannt")
    elif tag != PY_TAG:
        befunde.append(f"Paket-Python {tag} passt nicht zum Bau-Python {PY_TAG}")
    befunde += _abi_fehler(lib, tag or PY_TAG)
    befunde += _verteilungs_dubletten(lib)
    py = os.path.join(python_dir, "python.exe")
    befunde += _signatur_fehler(py)
    laden, finden = _probe_module()
    befunde += _import_probe(py, paket, laden, finden, tuple(sys.version_info[:2]))
    bin_dir = os.path.join(paket, "System", "bin")
    for name, schalter, erwartet in (("deno.exe", "--version", "deno "),
                                     ("ffmpeg.exe", "-version", "ffmpeg version"),
                                     ("ffprobe.exe", "-version", "ffprobe version")):
        befund = _antwortet([os.path.join(bin_dir, name), schalter], erwartet)
        if befund:
            befunde.append(befund)
    befunde += _struktur_fehler(paket, kopiert)
    return befunde


def _start_bat(ziel):
    # CRLF-Pflicht (Familienregel): cmd zerhackt LF-Zeilen.
    inhalt = ("@echo off\r\nchcp 65001>nul\r\ncd /d %~dp0\r\n"
              "start \"\" python\\pythonw.exe System\\youtube_app.py\r\n")
    with open(os.path.join(ziel, "SyncYouTube-Quellstart.bat"), "wb") as f:
        f.write(inhalt.encode("ascii"))


def _argumente(argv):
    p = argparse.ArgumentParser(description="SyncYouTube-Quellstart.zip bauen")
    p.add_argument("--ausgabe", metavar="ORDNER",
                   help="ZIP + .sha256 hierhin statt nach System/dist_exe "
                        "(Probebau: die veroeffentlichte ZIP bleibt unberuehrt)")
    return p.parse_args(argv)


def main(argv=None):
    args = _argumente(argv)
    ziel = os.path.join(os.path.abspath(args.ausgabe) if args.ausgabe else DIST, ZIP_NAME)
    _altes_ergebnis_beiseite(ziel)
    os.makedirs(BAU, exist_ok=True)
    paket = os.path.join(BAU, "paket")
    _frischer_bauordner(paket)
    _python_holen(os.path.join(paket, "python"))
    _pakete_holen(os.path.join(paket, "lib"))
    kopiert = _quellen_kopieren(os.path.join(paket, "System"))
    _bin_kopieren(os.path.join(paket, "System"))
    _wurzel_dateien_kopieren(paket)
    _start_bat(paket)
    _sag("Rauchtest am fertigen Paket ...")
    befunde = _rauchtest(paket, kopiert)
    if befunde:
        for befund in befunde:
            _sag(f"  - {befund}")
        raise BauFehler(f"Rauchtest: {len(befunde)} Befund(e) - kein ZIP.")
    _sag("Rauchtest bestanden.")
    summe = _packen(paket, ziel)
    _sag(f"Fertig: {ziel} (SHA-256 {summe})")
    return ziel


if __name__ == "__main__":
    try:
        main()
    except BauFehler as e:
        _sag(f"[FEHLER] {e}")
        _sag("Kein ZIP gebaut.")
        sys.exit(1)
