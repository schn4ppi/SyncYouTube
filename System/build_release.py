#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SyncYouTube bauen, signieren, Pruefsumme schreiben — ein Weg, eine Datei.

WARUM ES DIESE DATEI GIBT (08.09.2026). SyncYouTube hatte
KEIN Bau-Skript: es gab nur `SyncYouTube.spec`,
den jemand von Hand mit PyInstaller aufrief. Damit fehlte auch der Signier-Schritt,
den andere Programme schon hatten.
Die Folge, wie ein Nutzer sie erlebte: *„Der YouTube-Downloader geht fuer ihn nach ein
paar Tagen nicht mehr, weil er die GitHub-Version hat und Windows diese irgendwann
als Virus identifiziert und Teile davon in Quarantaene setzt."* Eine unsignierte
200-MB-PyInstaller-Datei ist der klassische Fehlalarm; die EV-Signatur ist die
Loesung, und sie darf nicht davon abhaengen, dass jemand sie von Hand nachholt.

REIHENFOLGE (nicht vertauschbar):
  1. bauen        — PyInstaller nach dist/, danach die ERZEUGNIS-Prüfung (24.09.2026):
                    stehen die winrt-Erweiterungen und die DLLs, die das winrt-Paket
                    mitbringt (bis pywinrt 3: msvcp140.dll), in der
                    Bauliste? Sonst Abbruch — auch bei --nur-signieren (dort an der
                    Bauliste des letzten Baus). Der Wächter test_exe_nimmt_pywinrt_mit
                    führt nur die Bauvorschrift aus; die exe vom 08.09. hatte trotz
                    Vorschrift kein winrt (Bauliste: 0 Einträge).
  2. signieren    — ueber das Signier-Skript (tools/bau_lokal.json) (EIN Zertifikat fuer die
                    alle Programme, mit RFC-3161-Zeitstempel: ohne ihn werden alle
                    Signaturen ungueltig, sobald das Zertifikat 2027 ablaeuft)
  3. Pruefsumme   — ERST NACH dem Signieren. Die Signatur wird IN die Datei
                    geschrieben; ein vorher gebildeter SHA-256 stuende falsch in
                    den Release-Notizen und der Updater der Alt-Clients wuerde ihn
                    verwerfen.
  4. kopieren     — die fertige Datei nach oben, wo die Startdatei sie erwartet

FAIL-CLOSED: Signieren ist PFLICHT (Entscheid 7a Punkt 6, 25.09.2026). Das
Selbst-Update tauscht nur noch exe mit gueltiger Signatur desselben Herausgebers;
ein unsignierter Release hielte also jedes Update an. Darum baut dieses Skript
ohne gesteckten Token gar nicht erst (Pruefung vor PyInstaller, klare Meldung),
und scheitert das Signieren spaeter doch (`signieren.signiere_pflicht` wirft
`SignierFehler`), bricht es ab, bevor Pruefsumme oder Kopie nach oben entstehen.

BAU-UMGEBUNG (25.11.2026): gebaut wird nur aus `System\\bau_venv` (tools/bau_umgebung.py).
Bis 1.4.0 lief der Bau aus der gemeinsamen venv, und die exe bekam deren zufällige
Fassungen (numpy, websockets 16 statt 17.4). Weicht das laufende Python von
tools/bau_stand.txt ab, bricht der Bau vor PyInstaller ab.

Aufruf:  bau_venv\\Scripts\\python.exe build_release.py [--nur-signieren]
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
# Das Signier-Skript (signieren.py) liegt außerhalb dieses Repos, auf dem Bau-PC.
# Wo, steht nur dort: tools/bau_lokal.json {"signieren_ordner": "<Ordner>"}
# (nicht versioniert) oder die Umgebungsvariable SYNCYOUTUBE_SIGNIEREN.


def _signier_ordner():
    ordner = os.environ.get("SYNCYOUTUBE_SIGNIEREN", "")
    lokal = os.path.join(HIER, "tools", "bau_lokal.json")
    if not ordner and os.path.isfile(lokal):
        import json
        with open(lokal, encoding="utf-8") as f:
            ordner = (json.load(f) or {}).get("signieren_ordner", "")
    return ordner


if _signier_ordner():
    sys.path.insert(0, _signier_ordner())
sys.path.insert(0, os.path.join(HIER, "tools"))
import bau_pakete  # noqa: E402
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
    Umgebung, aus der PyInstaller baut. Den Importen wird über alle Ebenen
    gefolgt, in beiden Schreibweisen: pywinrt 3 lud je Bereich ein eigenes Teil
    (`from winrt._winrt_windows_media import …`), pywinrt 4 hat einen
    gemeinsamen Kern (`from winrt._winrt import …`, über winrt.runtime) und für
    Interop ein eigenes (`import winrt._winrt_windows_media_interop as _native`).
    Keine Handliste."""
    def winrt_importe(baum):
        for n in ast.walk(baum):
            if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("winrt"):
                yield n.module
            elif isinstance(n, ast.Import):
                yield from (a.name for a in n.names if a.name.startswith("winrt"))

    with open(smtc_pfad, encoding="utf-8") as f:
        offen = set(winrt_importe(ast.parse(f.read())))
    if not offen:
        raise RuntimeError(f"{smtc_pfad} importiert kein winrt - die Pruefung waere blind")
    gesehen, erweiterungen = set(), set()
    while offen:
        modul = offen.pop()
        if modul in gesehen:
            continue
        gesehen.add(modul)
        spec = importlib.util.find_spec(modul)
        if spec is None or not spec.origin:
            raise RuntimeError(f"{modul} ist in diesem Python nicht installiert")
        if spec.origin.lower().endswith(".pyd"):
            erweiterungen.add(modul.split(".", 1)[1])
        elif spec.origin.endswith(".py"):
            with open(spec.origin, encoding="utf-8") as f:
                offen |= set(winrt_importe(ast.parse(f.read()))) - gesehen
    return erweiterungen


def winrt_dlls():
    """DLLs, die das installierte winrt-Paket selbst mitbringt (pywinrt 3:
    msvcp140.dll, pywinrt 4: keine). Sie müssen NEBEN den .pyd in der exe liegen."""
    spec = importlib.util.find_spec("winrt")
    ordner = next(iter(spec.submodule_search_locations or []), None) if spec else None
    if not ordner or not os.path.isdir(ordner):
        raise RuntimeError("winrt ist in diesem Python nicht installiert")
    return {d for d in os.listdir(ordner) if d.lower().endswith(".dll")}


def _quellen_unter_site_packages(bauliste):
    """Aus der PyInstaller-Bauliste: Pfadteile NACH site-packages je Eintrag
    (Muster eingebackene_namen im Wächter test_syncyoutube_lizenzen:
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


def erzeugnis_pruefen(bauliste=None, erwartet=None, dlls=None):
    """Was fehlt in der exe? Leere Liste = alles drin. FAIL-CLOSED: ohne lesbare
    Bauliste oder ohne Auto-Discovery gilt alles als fehlend.

    Geprüft: jede winrt-Erweiterung (winrt/<name>.<marke>.pyd) und jede DLL, die
    das winrt-Paket mitbringt (bis pywinrt 3 die C++-Laufzeit msvcp140.dll) — sie
    muss NEBEN den .pyd liegen, dort sucht Windows sie."""
    bauliste = bauliste or BAULISTE
    try:
        erwartet = set(erwartet) if erwartet is not None else winrt_erweiterungen()
        dlls = set(dlls) if dlls is not None else winrt_dlls()
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
    fehlt += [dll for dll in sorted(dlls) if dll.lower() not in im_winrt]
    return fehlt


def _zielnamen(bauliste):
    """Aus der PyInstaller-Bauliste: der Name jedes Eintrags in der exe, mit /."""
    with open(bauliste, encoding="utf-8") as f:
        inhalt = ast.literal_eval(f.read())
    return {eintrag[0].replace("\\", "/")
            for block in (inhalt if isinstance(inhalt, (list, tuple)) else ())
            if isinstance(block, list)
            for eintrag in block
            if isinstance(eintrag, tuple) and len(eintrag) == 3 and isinstance(eintrag[0], str)}


def oberflaeche_fehlt(bauliste=None, hier=HIER):
    """Welche Teile der PC-Oberfläche fehlen in der exe? Seit dem Strukturumbau
    (25.11.2026) setzt oberflaeche.py die Seite aus pc_oberflaeche/ und
    layout_kern.js zusammen; fehlt eines, startet die exe ohne Oberfläche.
    Auto-Discovery über den Ordner, keine Handliste; FAIL-CLOSED wie oben."""
    teile = os.path.join(hier, "pc_oberflaeche")
    erwartet = {"layout_kern.js"}
    for ordner, _unter, namen in os.walk(teile):
        erwartet |= {os.path.relpath(os.path.join(ordner, n), hier).replace("\\", "/")
                     for n in namen}
    if len(erwartet) < 4:
        return [f"Auto-Discovery der Oberflächen-Teile unter {teile} fand fast nichts"]
    try:
        ziele = _zielnamen(bauliste or BAULISTE)
    except (OSError, SyntaxError, ValueError) as e:
        return [f"Bauliste {bauliste or BAULISTE} nicht lesbar: {e}"]
    return sorted(erwartet - ziele)


def bauen():
    print("[1/4] PyInstaller laeuft (dauert einige Minuten) …")
    lauf = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", SPEC],
                          cwd=HIER)
    if lauf.returncode != 0:
        sys.exit("[FEHLER] Bau fehlgeschlagen — nichts wird veroeffentlicht.")
    if not os.path.exists(GEBAUT):
        sys.exit(f"[FEHLER] {GEBAUT} fehlt trotz Exitcode 0.")
    erzeugnis_oder_abbruch()


def erzeugnis_oder_abbruch():
    """Erzeugnis-Pruefung mit Abbruch — im Bau-Weg UND vor --nur-signieren
    (Pruefung Runde 1: sonst signierte --nur-signieren die exe ohne winrt, die
    ein gescheiterter Bau in dist/ liegen liess, und legte sie oben bereit)."""
    fehlt = erzeugnis_pruefen()
    if fehlt:
        sys.exit("[FEHLER] Die exe ist ohne Windows-Medienanmeldung gebaut, in der "
                 f"Bauliste fehlen: {', '.join(fehlt)} (winrt) — nichts wird veroeffentlicht.")
    print("      Erzeugnis-Pruefung: winrt-Erweiterungen und ihre DLLs sind drin.")
    fehlt = oberflaeche_fehlt()
    if fehlt:
        sys.exit("[FEHLER] Der exe fehlen Teile der Oberfläche, in der Bauliste fehlen: "
                 f"{', '.join(fehlt)} — nichts wird veroeffentlicht.")
    print("      Erzeugnis-Pruefung: alle Teile der Oberfläche sind drin.")


def token_oder_abbruch():
    """Vor jedem Bau: ohne signtool oder Code-Signing-Zertifikat (der eToken
    meldet es, sobald er steckt) wird nicht gebaut. Die eigentliche Pflicht
    prueft danach `signiere_pflicht`; das hier spart die Minuten des Baus."""
    if not signieren.signtool_pfad() or not signieren.zertifikate():
        sys.exit("[FEHLER] Kein Signatur-Token: signtool oder Code-Signing-Zertifikat fehlt. "
                 "Ohne Signatur wird nicht gebaut, denn das Selbst-Update tauscht nur "
                 "signierte exe. eToken stecken, SafeNet-Client anmelden, neu starten.")


def signieren_und_pruefen():
    print("[2/4] Signieren (der Token fragt ggf. nach der PIN) …")
    try:
        return signieren.signiere_pflicht(GEBAUT, beschreibung="SyncYouTube")
    except signieren.SignierFehler as e:
        sys.exit(f"[FEHLER] Signatur nicht moeglich, nichts wird veroeffentlicht: {e}")


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


def bau_umgebung_oder_abbruch():
    """Nur aus der Bau-Umgebung bauen: sonst bekäme die exe fremde Fassungen."""
    abweichend = bau_pakete.abweichungen()
    if abweichend:
        sys.exit("[FEHLER] Dieses Python ist nicht die Bau-Umgebung (tools/bau_stand.txt): "
                 + "; ".join(abweichend[:5])
                 + ". Aufruf mit bau_venv\\Scripts\\python.exe, sie entsteht mit "
                   "tools\\bau_umgebung.py.")


def main():
    bau_umgebung_oder_abbruch()
    token_oder_abbruch()
    if "--nur-signieren" not in sys.argv:
        bauen()
    elif not os.path.exists(GEBAUT):
        sys.exit(f"[FEHLER] --nur-signieren, aber {GEBAUT} fehlt.")
    else:
        erzeugnis_oder_abbruch()           # fail-closed auch ohne Bau (Bauliste des letzten Baus)
    signieren_und_pruefen()
    pruefsumme()
    nach_oben()
    print("\nFertig.")


if __name__ == "__main__":
    main()
