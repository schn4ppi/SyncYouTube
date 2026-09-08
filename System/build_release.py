#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SyncYouTube bauen, signieren, Pruefsumme schreiben — ein Weg, eine Datei.

WARUM ES DIESE DATEI GIBT (08.09.2026). SyncYouTube hatte als einziges
ausgelieferte Programm der Familie KEIN Bau-Skript: es gab nur `SyncYouTube.spec`,
den jemand von Hand mit PyInstaller aufrief. Damit fehlte auch der Signier-Schritt,
den SyncManga seit dem 27.08. hat (`build/release_build.py` ruft `signieren`).
Die Folge steht in JBs Worten: *„Der YouTube-Downloader geht fuer ihn nach ein
paar Tagen nicht mehr, weil er die GitHub-Version hat und Windows diese irgendwann
als Virus identifiziert und Teile davon in Quarantaene setzt."* Eine unsignierte
200-MB-PyInstaller-Datei ist der klassische Fehlalarm; die EV-Signatur ist die
Loesung, und sie darf nicht davon abhaengen, dass jemand sie von Hand nachholt.

REIHENFOLGE (nicht vertauschbar):
  1. bauen        — PyInstaller nach dist/
  2. signieren    — ueber SyncDashTray/System/signieren.py (EIN Zertifikat fuer die
                    ganze Familie, mit RFC-3161-Zeitstempel: ohne ihn werden alle
                    Signaturen ungueltig, sobald das Zertifikat 2027 ablaeuft)
  3. Pruefsumme   — ERST NACH dem Signieren. Die Signatur wird IN die Datei
                    geschrieben; ein vorher gebildeter SHA-256 stuende falsch in
                    den Release-Notizen und der Updater der Alt-Clients wuerde ihn
                    verwerfen. Genau diese Falle steht schon in SyncMangas Bau-Skript.
  4. kopieren     — die fertige Datei nach oben, wo die Startdatei sie erwartet

FAIL-CLOSED: Ist ein Code-Signing-Zertifikat im Speicher, ist Signieren PFLICHT —
scheitert es, bricht der Bau ab (`signieren.SignierFehler`). Ein still unsignierter
Release waere schlimmer als ein abgebrochener Bau. Steckt der Token nicht, meldet
`signieren` das und der Bau laeuft unsigniert weiter; dieses Skript sagt es dann
deutlich, damit niemand versehentlich einen unsignierten Stand veroeffentlicht.

Aufruf:  venv-python build_release.py [--nur-signieren]
"""
import hashlib
import os
import shutil
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))                 # SyncYouTube/System
OBEN = os.path.normpath(os.path.join(HIER, ".."))                 # SyncYouTube
FAMILIE = os.path.normpath(os.path.join(OBEN, "..", "SyncDashTray", "System"))
sys.path.insert(0, FAMILIE)
import signieren  # noqa: E402

SPEC = os.path.join(HIER, "SyncYouTube.spec")
GEBAUT = os.path.join(HIER, "dist", "SyncYouTube.exe")


def bauen():
    print("[1/4] PyInstaller laeuft (dauert einige Minuten) …")
    lauf = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", SPEC],
                          cwd=HIER)
    if lauf.returncode != 0:
        sys.exit("[FEHLER] Bau fehlgeschlagen — nichts wird veroeffentlicht.")
    if not os.path.exists(GEBAUT):
        sys.exit(f"[FEHLER] {GEBAUT} fehlt trotz Exitcode 0.")


def signieren_und_pruefen():
    print("[2/4] Signieren (der Token fragt ggf. nach der PIN) …")
    ergebnis = signieren.signiere(GEBAUT, beschreibung="SyncYouTube")
    if ergebnis == "kein_zertifikat":
        print("[WARNUNG] Kein Zertifikat im Speicher — die Datei ist UNSIGNIERT.")
        print("          Nicht veroeffentlichen: Defender wird sie beim Nutzer")
        print("          frueher oder spaeter in Quarantaene setzen.")
    return ergebnis


def pruefsumme():
    print("[3/4] Pruefsumme (nach dem Signieren, sonst stimmt sie nicht) …")
    roh = open(GEBAUT, "rb").read()
    h = hashlib.sha256(roh).hexdigest()
    with open(GEBAUT + ".sha256", "w", encoding="ascii") as f:
        f.write(h + "  SyncYouTube.exe\n")
    print(f"      {len(roh) / 2**20:.1f} MB, SHA-256 {h}")
    return h


def nach_oben():
    print("[4/4] Nach oben kopieren …")
    ziel = os.path.join(OBEN, "SyncYouTube.exe")
    shutil.copy(GEBAUT, ziel)
    shutil.copy(GEBAUT + ".sha256", ziel + ".sha256")
    print(f"      {ziel}")


def main():
    if "--nur-signieren" not in sys.argv:
        bauen()
    elif not os.path.exists(GEBAUT):
        sys.exit(f"[FEHLER] --nur-signieren, aber {GEBAUT} fehlt.")
    ergebnis = signieren_und_pruefen()
    pruefsumme()
    nach_oben()
    print("\nFertig." if ergebnis != "kein_zertifikat" else
          "\nFertig — ABER UNSIGNIERT, siehe Warnung oben.")


if __name__ == "__main__":
    main()
