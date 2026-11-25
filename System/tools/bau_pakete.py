# -*- coding: utf-8 -*-
"""Die EINE Liste der Fassungen, mit denen SyncYouTube gebaut wird.

Warum (Techdebt-Durchsicht 25.11.2026): Bis v1.4.0 baute die exe aus der
gemeinsamen venv, ohne feste Fassungen, das Quellstart-Paket aus
einer eigenen, festen Liste. Dasselbe Release bündelte so verschiedene Stände
(websockets 16.0 gegen 17.4, curl_cffi nur in der exe), und die exe schleppte
alles mit, was zufällig in der gemeinsamen venv lag (numpy, 29,6 MB, unbenutzt).

Jetzt bauen beide aus derselben Bau-Umgebung `System\\bau_venv` mit eigenem
Python (`System\\bau_python`, siehe tools/bau_umgebung.py). Diese Datei nennt
die Pakete; `bau_stand.txt` daneben hält fest, was die Umgebung danach WIRKLICH
enthält, samt allen mitgezogenen Paketen. Der Quellstart installiert mit
diesem Stand als Vorgabe und bekommt so dieselben Fassungen wie die exe.
"""
import importlib.metadata as md
import os
import re

HIER = os.path.dirname(os.path.abspath(__file__))
STAND_DATEI = os.path.join(HIER, "bau_stand.txt")

# Was die App zur Laufzeit braucht (exe UND Quellstart).
LAUFZEIT = [
    # yt-dlp[default] bringt yt-dlp-ejs mit („Required for full YouTube support").
    "yt-dlp[default]==2026.11.23",
    # Browser-Nachahmung für yt-dlp (lag bis 1.4.0 nur zufällig in der exe).
    "curl_cffi==0.17.0",
    "pystray==0.19.5", "pillow==13.0.0", "mutagen==1.48.1", "pykakasi==2.3.0",
    "keyring==25.7.0", "qrcode==8.2", "python-vlc==3.0.21203",
    # Windows-Medienanmeldung des VLC-Motors (medien_smtc.py, Freigabe 23.09.).
    # Ab pywinrt 4 tragen die Windows-Pakete die SDK-Nummer als Fassung (Epoche 4!);
    # Interop hat eine eigene Zählung.
    "winrt-runtime==4.2.1", "winrt-Windows.Foundation==4!10.0.28000.2957",
    "winrt-Windows.Media==4!10.0.28000.2957", "winrt-Windows.Media.Interop==4.0.0",
    "winrt-Windows.Storage.Streams==4!10.0.28000.2957",
    # Fenster-Modus (huelle.py, SyncYouTube-Fenster.bat): der Besitzer 25.11.2026 „für alle".
    "pywebview==6.2.1",
]

# Sonst gilt „nur fertige Räder“ (eine sdist würde mit dem Compiler dieses PCs
# gebaut). proxy_tools (von pywebview gebraucht) gibt es nur als Quellpaket; es
# ist ein einziges Python-Modul ohne Compiler-Teil.
NUR_QUELLE = ["proxy_tools"]


def pip_format():
    """pip-Schalter: fertige Räder, außer für NUR_QUELLE."""
    return ["--only-binary=:all:", *(f"--no-binary={n}" for n in NUR_QUELLE)]


# Nur zum Bauen und Prüfen, nie ausgeliefert.
WERKSTATT = ["pyinstaller==6.22.3", "pytest==9.2.0", "pytest-xdist==3.8.0"]


def normname(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def zerlegen(eintrag):
    """'yt-dlp[default]==2026.11.23' -> ('yt-dlp', 'default', '2026.11.23')."""
    m = re.fullmatch(r"([A-Za-z0-9_.\-]+)(?:\[([^\]]+)\])?(?:==([^\s;]+))?", eintrag)
    if not m:
        raise ValueError(f"Paket-Eintrag nicht lesbar: {eintrag!r}")
    return m.group(1), m.group(2), m.group(3)


def stand_lesen(pfad=STAND_DATEI):
    """{normname: Fassung} aus bau_stand.txt (Ausgabe von pip freeze)."""
    stand = {}
    with open(pfad, encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.split("#", 1)[0].strip()
            m = re.fullmatch(r"([A-Za-z0-9_.\-]+)==(\S+)", zeile)
            if m:
                stand[normname(m.group(1))] = m.group(2)
    return stand


def abweichungen(pfad=STAND_DATEI, fassung_von=md.version):
    """Liste der Unterschiede zwischen bau_stand.txt und DIESEM Python.

    Leer heißt: hier läuft die Bau-Umgebung. Der Bau bricht sonst ab, denn mit
    einem anderen Python bekäme die exe wieder fremde Fassungen."""
    befunde = []
    for name, soll in sorted(stand_lesen(pfad).items()):
        try:
            ist = fassung_von(name)
        except md.PackageNotFoundError:
            befunde.append(f"{name}: fehlt (Soll {soll})")
            continue
        if ist != soll:
            befunde.append(f"{name}: {ist} statt {soll}")
    return befunde
