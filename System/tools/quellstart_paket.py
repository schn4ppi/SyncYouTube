# -*- coding: utf-8 -*-
"""Quellstart-Paket bauen (Pete-Fall 07.08.2026: Windows **Smart App Control**
blockiert unsere PyInstaller-exe — jeder Build ist ein frisch gehashtes
UNIKAT ohne Signatur und ohne Reputation, und SAC kennt kein „Trotzdem
ausführen").

Der Quellstart-Weg umgeht nichts, er nimmt den sauberen Pfad: der offizielle
python.org-Interpreter ist von der Python Software Foundation SIGNIERT, unsere
.py-Dateien sind für SAC Daten, keine Programme. ffmpeg/deno aus System/bin
sind weit verbreitete Binärdateien mit Cloud-Reputation.

Aufruf (Werkstatt, nicht im Auslieferungsweg):
    venv\\Scripts\\python System\\tools\\quellstart_paket.py
Ergebnis: System\\dist_exe\\SyncYouTube-Quellstart.zip
"""
import os
import subprocess
import sys
import urllib.request
import zipfile

SYSTEM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WURZEL = os.path.dirname(SYSTEM)
BAU = os.path.join(SYSTEM, "build_tmp", "quellstart")
# Paket-Python = Bau-Python (Befund 24.09.2026): pip installiert mit DIESEM Python
# (sys.executable) und wählt Binärteile für seine Fassung. Bis v.1.2.6 lag im Paket
# ein 3.12.10 neben cp314-Dateien aus der 3.14-venv — Pillow war nicht ladbar,
# pywinrt wäre es auch nicht gewesen. `--python-version` allein schützt nicht:
# Umgebungsmarker wertet pip weiter gegen das LAUFENDE Python aus. Also dieselbe
# Fassung, und der Rauchtest am fertigen Paket bleibt Pflicht.
PY_VER = "{}.{}.{}".format(*sys.version_info[:3])
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
        print(f"Lade {PY_URL} ...")
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
    # ASCII-Ausgaben: die Windows-Konsole laeuft auf cp1252 und wirft bei
    # Sonderzeichen einen UnicodeEncodeError — der Bau starb daran lautlos
    # und liess die ALTE zip liegen (Fund 07.08., fast ausgeliefert).
    # --only-binary=:all: — nur fertige Räder, nie eine sdist mit dem Bau-Compiler;
    # --no-compile — kein Bytecode des Bau-Pythons im Paket; --isolated — keine
    # pip-Einstellungen dieses PCs (Index, Proxy) im Bau.
    print("Installiere Abhaengigkeiten nach:", lib)
    subprocess.run([sys.executable, "-m", "pip", "--isolated", "install",
                    "--disable-pip-version-check", "--no-warn-script-location",
                    "--only-binary=:all:", "--no-compile",
                    "--target", lib, *PAKETE], check=True)


def _quellen_kopieren(ziel_sys):
    """NUR versionierte Quell-Dateien (git ls-files) + bin/ — keine Nutzerdaten."""
    dateien = subprocess.run(
        ["git", "ls-files", "System"], cwd=WURZEL, check=True,
        capture_output=True, text=True).stdout.splitlines()
    for rel in dateien:
        if "/tests/" in rel or rel.endswith((".spec", ".md")):
            continue
        quelle = os.path.join(WURZEL, rel)
        ziel = os.path.join(os.path.dirname(ziel_sys), rel)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(quelle, "rb") as f_in, open(ziel, "wb") as f_out:
            f_out.write(f_in.read())


def _start_bat(ziel):
    # CRLF-Pflicht (Familienregel): cmd zerhackt LF-Zeilen.
    inhalt = ("@echo off\r\nchcp 65001>nul\r\ncd /d %~dp0\r\n"
              "start \"\" python\\pythonw.exe System\\youtube_app.py\r\n")
    with open(os.path.join(ziel, "SyncYouTube-Quellstart.bat"), "wb") as f:
        f.write(inhalt.encode("ascii"))


def main():
    # Altes Ergebnis WEG, bevor gebaut wird: bricht der Bau ab, darf keine
    # veraltete zip zurueckbleiben, die jemand fuer frisch haelt (Fund 07.08.).
    altes = os.path.join(SYSTEM, "dist_exe", "SyncYouTube-Quellstart.zip")
    for weg in (altes, altes + ".sha256"):
        if os.path.exists(weg):
            os.remove(weg)
    os.makedirs(BAU, exist_ok=True)
    _python_holen(os.path.join(BAU, "paket", "python"))
    _pakete_holen(os.path.join(BAU, "paket", "lib"))
    _quellen_kopieren(os.path.join(BAU, "paket", "System"))
    _start_bat(os.path.join(BAU, "paket"))
    ziel = os.path.join(SYSTEM, "dist_exe", "SyncYouTube-Quellstart.zip")
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    print("Packe", ziel)
    with zipfile.ZipFile(ziel, "w", zipfile.ZIP_DEFLATED) as z:
        basis = os.path.join(BAU, "paket")
        for ordner, _, dateien in os.walk(basis):
            for d in dateien:
                voll = os.path.join(ordner, d)
                z.write(voll, os.path.relpath(voll, basis))
    print("Fertig:", ziel)


if __name__ == "__main__":
    main()
