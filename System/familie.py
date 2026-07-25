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
import threading
import time

KERN_VERSION = 2                    # bei Schema-/Verhaltensänderung hochzählen


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
    """Atomar schreiben (eigene tmp-Datei + replace). Rückgabe True bei Erfolg.

    **Der tmp-Name MUSS je Schreiber eindeutig sein.** Bis 23.07.2026 hieß er fest
    `<pfad>.tmp` — und genau daran zerbrach die Familie unter Mehr-Session-Last.
    Gemessen mit 8 gleichzeitigen Schreibern und 4 Lesern auf einer Datei:
    **3.105 von 3.200 Schreibvorgängen schlugen fehl** (Windows-Freigabekonflikt am
    gemeinsamen tmp) und **2.835 Lesevorgänge sahen ungültiges JSON**. Der Grund ist
    tückisch: `os.replace` IST atomar — nur nützt das nichts, wenn zwei Prozesse
    vorher dieselbe Quelldatei beschreiben und einer die halb gefüllte verschiebt.
    Mit eigenem tmp-Namen je Prozess/Thread: 0 kaputte Lesevorgänge.

    **Zweiter Windows-Befund derselben Messung:** `os.replace` scheitert, solange ein
    LESER die Zieldatei geöffnet hat (Freigabekonflikt) — bei 4 Dauer-Lesern schlugen
    so noch 2.984 von 3.200 Schreibvorgängen fehl, obwohl niemand etwas falsch machte.
    Unter Linux gibt es das nicht; die Familie läuft aber auf Windows. Deshalb ein
    kurzer Wiederholungs-Anlauf (~0,5 s) statt sofort aufzugeben: der Leser ist im
    Millisekundenbereich wieder weg.
    """
    tmp = f"{pfad}.{os.getpid()}.{threading.get_ident():x}.tmp"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=1)
    except (OSError, TypeError, ValueError):
        _aufraeumen(tmp)
        return False
    for versuch in range(25):
        try:
            os.replace(tmp, pfad)
            return True
        except OSError:
            time.sleep(0.02 * (versuch + 1) if versuch < 5 else 0.02)
    _aufraeumen(tmp)                # Rest nie liegen lassen (sonst Müll im System\)
    return False


def _aufraeumen(tmp):
    try:
        os.remove(tmp)
    except OSError:
        pass


SPERRE_ALT_S = 30.0                 # so alt darf eine Sperre höchstens sein


def json_aendern(pfad, aenderung, standard=None, wartezeit_s=5.0):
    """Lesen-Ändern-Schreiben UNTER EINER SPERRE — für gemeinsam geführte Dateien.

    `json_schreiben` allein genügt dafür nicht: Es schreibt zwar heil, aber zwei
    Sessions, die gleichzeitig lesen, je einen Eintrag ergänzen und zurückschreiben,
    überschreiben sich gegenseitig. Gemessen (8 Sessions): **5 von 8 Einträgen waren
    am Ende weg** — jede Datei war für sich gültig, der Inhalt trotzdem falsch. Genau
    so verliert die Familie Reviere (`claims.json`) und Merkposten.

    `aenderung(daten)` bekommt die geladenen Daten und gibt die neuen zurück (oder
    ändert sie in place und gibt None zurück). Rückgabe: die geschriebenen Daten,
    oder None, wenn die Sperre nicht zu bekommen war.

    Nicht-destruktiv im Zweifel: Bekommt niemand die Sperre, wird NICHT blind
    geschrieben — lieber diese Änderung auslassen als die Arbeit anderer wegwerfen.
    Eine verwaiste Sperre (Prozess abgestürzt) verfällt nach `SPERRE_ALT_S`.
    """
    sperre = pfad + ".sperre"
    ende = time.time() + wartezeit_s
    griff = None
    while time.time() < ende:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
            griff = os.open(sperre, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:                    # verwaiste Sperre eines abgestürzten Prozesses
                if time.time() - os.path.getmtime(sperre) > SPERRE_ALT_S:
                    os.remove(sperre)
                    continue
            except OSError:
                pass
            time.sleep(0.01)
        except OSError:
            return None
    if griff is None:
        return None
    try:
        daten = json_laden(pfad, standard)
        neu = aenderung(daten)
        if neu is None:
            neu = daten
        json_schreiben(pfad, neu)
        return neu
    finally:
        os.close(griff)
        try:
            os.remove(sperre)
        except OSError:
            pass


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
