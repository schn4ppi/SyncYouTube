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
  1. bauen        — PyInstaller nach dist/, danach die ERZEUGNIS-Prüfung (24.09.2026):
                    stehen die winrt-Erweiterungen und winrt/msvcp140.dll in der
                    Bauliste? Sonst Abbruch. Der Wächter test_exe_nimmt_pywinrt_mit
                    führt nur die Bauvorschrift aus; die exe vom 08.09. hatte trotz
                    Vorschrift kein winrt (Bauliste: 0 Einträge).
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
import ast
import hashlib
import importlib.util
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
# Was WIRKLICH in die exe gepackt wird (onefile: das pkg, das an die exe gehängt wird).
BAULISTE = os.path.join(HIER, "build", "SyncYouTube", "PKG-00.toc")
SMTC = os.path.join(HIER, "medien_smtc.py")


def winrt_erweiterungen(smtc_pfad=SMTC):
    """Auto-Discovery: welche winrt-Binärerweiterungen braucht der Server?

    Aus den winrt-Importen von medien_smtc.py (wie _winrt_importe im Wächter
    test_medien_smtc) über die Paket-Quellen dieses Pythons — also derselben
    Umgebung, aus der PyInstaller baut: `winrt.windows.media` lädt seine Klassen
    per `from winrt._winrt_windows_media import …`. Keine Handliste."""
    with open(smtc_pfad, encoding="utf-8") as f:
        baum = ast.parse(f.read())
    module = {n.module for n in ast.walk(baum)
              if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("winrt")}
    if not module:
        raise RuntimeError(f"{smtc_pfad} importiert kein winrt - die Pruefung waere blind")
    erweiterungen = set()
    for modul in module:
        spec = importlib.util.find_spec(modul)
        if spec is None or not spec.origin:
            raise RuntimeError(f"{modul} ist in diesem Python nicht installiert")
        with open(spec.origin, encoding="utf-8") as f:
            quelle = ast.parse(f.read())
        erweiterungen |= {n.module.split(".", 1)[1] for n in ast.walk(quelle)
                          if isinstance(n, ast.ImportFrom)
                          and (n.module or "").startswith("winrt._")}
    return erweiterungen


def _quellen_unter_site_packages(bauliste):
    """Aus der PyInstaller-Bauliste: Pfadteile NACH site-packages je Eintrag
    (Muster eingebackene_namen im Familien-Wächter test_syncyoutube_lizenzen:
    gemessen wird an der QUELLE, nicht an einer vermuteten Schreibweise der Ziele)."""
    with open(bauliste, encoding="utf-8") as f:
        inhalt = ast.literal_eval(f.read())
    teile_je_eintrag = []
    for block in (inhalt if isinstance(inhalt, (list, tuple)) else ()):
        if not isinstance(block, list):
            continue
        for eintrag in block:
            if (isinstance(eintrag, tuple) and len(eintrag) == 3
                    and isinstance(eintrag[1], str)):
                teile = eintrag[1].replace("\\", "/").split("/")
                klein = [t.lower() for t in teile]
                if "site-packages" in klein:
                    teile_je_eintrag.append(teile[klein.index("site-packages") + 1:])
    return teile_je_eintrag


def erzeugnis_pruefen(bauliste=None, erwartet=None):
    """Was fehlt in der exe? Leere Liste = alles drin. FAIL-CLOSED: ohne lesbare
    Bauliste oder ohne Auto-Discovery gilt alles als fehlend.

    Geprüft: jede winrt-Erweiterung (winrt/<name>.<marke>.pyd) und winrt/msvcp140.dll
    — die C++-Laufzeit muss NEBEN den .pyd liegen, dort sucht Windows sie."""
    bauliste = bauliste or BAULISTE
    try:
        erwartet = set(erwartet) if erwartet is not None else winrt_erweiterungen()
    except (OSError, SyntaxError, RuntimeError) as e:
        return [f"Auto-Discovery der winrt-Teile gescheitert: {e}"]
    try:
        quellen = _quellen_unter_site_packages(bauliste)
    except (OSError, SyntaxError, ValueError) as e:
        return [f"Bauliste {bauliste} nicht lesbar: {e}"]
    im_winrt = {t[1].lower() for t in quellen if len(t) == 2 and t[0].lower() == "winrt"}
    fehlt = [name for name in sorted(erwartet)
             if not any(d.startswith(name.lower() + ".") and d.endswith(".pyd")
                        for d in im_winrt)]
    if "msvcp140.dll" not in im_winrt:
        fehlt.append("msvcp140.dll")
    return fehlt


def bauen():
    print("[1/4] PyInstaller laeuft (dauert einige Minuten) …")
    lauf = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", SPEC],
                          cwd=HIER)
    if lauf.returncode != 0:
        sys.exit("[FEHLER] Bau fehlgeschlagen — nichts wird veroeffentlicht.")
    if not os.path.exists(GEBAUT):
        sys.exit(f"[FEHLER] {GEBAUT} fehlt trotz Exitcode 0.")
    fehlt = erzeugnis_pruefen()
    if fehlt:
        sys.exit("[FEHLER] Die exe ist ohne Windows-Medienanmeldung gebaut, in der "
                 f"Bauliste fehlen: {', '.join(fehlt)} (winrt) — nichts wird veroeffentlicht.")
    print("      Erzeugnis-Pruefung: winrt-Erweiterungen und msvcp140.dll sind drin.")


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
