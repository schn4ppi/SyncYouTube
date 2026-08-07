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
PY_VER = "3.12.10"
PY_URL = (f"https://www.python.org/ftp/python/{PY_VER}/"
          f"python-{PY_VER}-embed-amd64.zip")
PAKETE = ["yt-dlp", "pystray", "pillow", "mutagen", "pykakasi",
          "keyring", "qrcode", "python-vlc"]


def _python_holen(ziel):
    """Signiertes Embeddable-Python von python.org laden + entpacken."""
    zp = os.path.join(BAU, "python-embed.zip")
    if not os.path.exists(zp):
        print(f"Lade {PY_URL} …")
        urllib.request.urlretrieve(PY_URL, zp)
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
    print("Installiere Abhängigkeiten →", lib)
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade",
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
