# -*- coding: utf-8 -*-
"""familie.py — gemeinsamer Kern der Sync-Programmfamilie (JB-Go 20.07.2026).

Liegt als IDENTISCHE Kopie in jedem Programm unter `System\\familie.py`
(Autarkie-Regel: Kopie statt Import-Abhängigkeit). Ein Wächter-Test im Gate
erzwingt, dass alle Kopien byte-gleich sind — Änderungen also IMMER hier
UND in allen Kopien machen (oder das Kopier-Werkzeug im Test-Kommentar nutzen).

Warum: Beim Stage-3-Umbau mussten ~50 handgestrickte `..\\..\\`-Pfadketten
einzeln angefasst werden; zwei rutschten durch. Mit diesem Kern gibt es beim
nächsten Umbau EINE Stelle. Außerdem: einheitliches `status.json` je Programm
(fürs Dashboard/Tray, statt je Programm ein eigenes Format).

Verwendung (aus jedem Skript in <Programm>\\System\\):
    import familie as fam
    fam.programm()                  # -> Pfad zu <Programm>\\
    fam.erstellt("Bericht.html")    # -> <Programm>\\Erstellt\\Bericht.html
    fam.nachbar("SyncMail", "MailArchiv")
    fam.status_schreiben(ok=True, zaehler={"mails": 5}, meldung="alles gut")
"""
import json
import os
import time

KERN_VERSION = 1                    # bei Schema-/Verhaltensänderung hochzählen


def system():
    """<Programm>\\System — der Ordner, in dem diese Kopie liegt."""
    return os.path.dirname(os.path.abspath(__file__))


def programm():
    """<Programm>\\ — der Programmordner (eine Ebene über System)."""
    return os.path.normpath(os.path.join(system(), ".."))


def familie():
    """Familien-Wurzel (Claude\\) — zwei Ebenen über System."""
    return os.path.normpath(os.path.join(system(), "..", ".."))


def programm_name():
    return os.path.basename(programm())


def erstellt(*teile):
    """<Programm>\\Erstellt\\… — Ergebnisse für JB (Ordner wird angelegt)."""
    p = os.path.join(programm(), "Erstellt", *teile)
    os.makedirs(os.path.dirname(p) if teile else p, exist_ok=True)
    return p


def extern(name, *teile):
    """<Programm>\\<name>\\… — externer Bezugsordner (MailArchiv, Downloads …)."""
    return os.path.join(programm(), name, *teile)


def nachbar(name, *teile):
    """Anderes Programm der Familie: nachbar('SyncMail', 'System', 'x.py')."""
    return os.path.join(familie(), name, *teile)


def json_laden(pfad, standard=None):
    """JSON lesen; fehlt/defekt -> standard (nie eine Exception)."""
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {} if standard is None else standard


def json_schreiben(pfad, daten):
    """Atomar schreiben (tmp + replace). Rückgabe True bei Erfolg."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
        tmp = pfad + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=1)
        os.replace(tmp, pfad)
        return True
    except OSError:
        return False


STATUS_DATEI = "status.json"        # Einheitsschema, liegt in <Programm>\\System\\


def status_schreiben(ok=True, zaehler=None, meldung="", **extra):
    """Einheitlicher Programm-Status fürs Dashboard/Tray (JB-Standard 20.07.2026).

    Schema v1: {schema, programm, ok, ts, zuletzt, zaehler{}, meldung, ...extra}
    Best-effort: schlägt NIE fehl (Status ist Komfort, nie Blocker)."""
    daten = {"schema": KERN_VERSION, "programm": programm_name(), "ok": bool(ok),
             "ts": time.time(), "zuletzt": time.strftime("%Y-%m-%d %H:%M:%S"),
             "zaehler": zaehler or {}, "meldung": str(meldung or "")}
    daten.update(extra)
    return json_schreiben(os.path.join(system(), STATUS_DATEI), daten)


def status_lesen(programm_name_oder_pfad):
    """Status eines Programms lesen: Name ('SyncMail') oder direkter Pfad."""
    p = programm_name_oder_pfad
    if os.sep not in p and "/" not in p:
        p = nachbar(p, "System", STATUS_DATEI)
    return json_laden(p, {})
