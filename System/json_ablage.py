# -*- coding: utf-8 -*-
"""json_ablage.py — JSON-Dateien sicher lesen, schreiben und ändern.

Drei Funktionen, die die App für ihre Zustandsdateien nutzt:
    json_laden(pfad, standard)       nie eine Ausnahme; fehlt/defekt -> standard
    json_schreiben(pfad, daten)      atomar (tmp-Datei + Ersetzen, mit Wiederholung)
    json_aendern(pfad, aenderung)    Lesen-Ändern-Schreiben unter einer Dateisperre
"""
import json
import os
import threading
import time


def _json_lesegriff(pfad, flags):
    """Windows-Leser geben Lesen, Schreiben und Löschen der Datei frei (JR61)."""
    import _winapi
    import msvcrt

    # 0x7 = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE.
    griff = _winapi.CreateFile(
        os.fsdecode(pfad), _winapi.GENERIC_READ, 0x7, _winapi.NULL,
        _winapi.OPEN_EXISTING, 0x80, _winapi.NULL)
    try:
        return msvcrt.open_osfhandle(griff, flags)
    except BaseException:
        # Vor der erfolgreichen Übergabe gehört der native Griff noch uns.
        _winapi.CloseHandle(griff)
        raise


LESEFRIST_S = 0.25                  # so lange wartet ein Leser höchstens auf einen Schreiber, der gerade ersetzt


def _schreiber_ersetzt(pfad):
    """Liegt neben `pfad` die tmp-Datei eines Schreibers (`<pfad>.<pid>.<thread>.tmp`, siehe `json_schreiben`)?

    Nur dann fehlt der Dateiname vorübergehend, weil gerade ersetzt wird; sonst fehlt die Datei wirklich."""
    ordner, name = os.path.split(os.path.abspath(pfad))
    try:
        return any(n.startswith(name + ".") and n.endswith(".tmp") for n in os.listdir(ordner))
    except OSError:
        return False


def json_laden(pfad, standard=None):
    """JSON lesen; fehlt/defekt -> standard (nie eine Exception).

    **Ersetzt gerade ein Schreiber die Datei, fehlt ihr Name unter Windows einen Augenblick** (FileNotFoundError,
    winerror 2) oder der Zugriff wird verweigert (winerror 5): Nicht die Datei fehlt, der Austausch läuft. Gemessen
    03.11.2026 mit 8 Schreibern, 3 Lesern und 10 Rechenfressern: 21 von 870 Lesevorgängen sahen so den Ersatzstand
    (kein ungültiges JSON, sondern ein fehlender Name); im Stop-Gate bei Last 1 von 132 (Wächter test_nebenlaeufigkeit).
    Wer den Ersatzstand für den echten hält und zurückschreibt, verlöre Einträge. Darum: Steht neben der Datei die tmp-Datei
    eines Schreibers, wird kurz erneut gelesen (höchstens `LESEFRIST_S`). Fehlt die Datei ohne Schreiber, gilt sie nach einem
    einzigen Nachsehen als fehlend (der Schreiber kann zwischen Fehler und Prüfung fertig geworden sein): kein Warten auf
    Dateien, die es nicht gibt."""
    ende = None
    nachsehen = True
    while True:
        try:
            if os.name == "nt":
                datei = open(pfad, encoding="utf-8", opener=_json_lesegriff)
            else:
                datei = open(pfad, encoding="utf-8")
            with datei as f:
                return json.load(f)
        except (FileNotFoundError, PermissionError):
            jetzt = time.monotonic()
            ende = jetzt + LESEFRIST_S if ende is None else ende
            if jetzt >= ende:
                break
            if _schreiber_ersetzt(pfad):
                nachsehen = True
                time.sleep(0.001)
            elif nachsehen:
                nachsehen = False
            else:
                break
        except (OSError, ValueError):
            break
    return {} if standard is None else standard


def _win_posix_ersetzen(quelle, ziel):
    """Offenes Ziel atomar ersetzen: FileRenameInfoEx, Windows 10 1809/NTFS."""
    import _winapi
    import ctypes
    from ctypes import wintypes

    class _UMBENENNUNG(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("RootDirectory", wintypes.HANDLE),
                    ("FileNameLength", wintypes.DWORD), ("FileName", wintypes.WCHAR * 1)]

    kern = ctypes.WinDLL("kernel32", use_last_error=True)
    setzen = kern.SetFileInformationByHandle
    setzen.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    setzen.restype = wintypes.BOOL
    name = os.fsdecode(os.path.abspath(ziel)).encode("utf-16-le", errors="surrogatepass")
    # Unter x64 liegt FileName bei Byte 20, sizeof liefert wegen Auffüllung 24.
    # Platz für ein abschließendes Nullzeichen: Ohne liest Windows beim Ersetzen einer
    # VORHANDENEN Datei über das Namensende hinaus und legt „r.json翸“ an, statt r.json
    # zu ersetzen — und meldet Erfolg (gemessen 22.10.2026, JR61).
    versatz = _UMBENENNUNG.FileName.offset
    groesse = max(ctypes.sizeof(_UMBENENNUNG), versatz + len(name) + 2)
    puffer = ctypes.create_string_buffer(groesse)
    info = _UMBENENNUNG.from_buffer(puffer)
    info.Flags = 0x3  # FILE_RENAME_FLAG_REPLACE_IF_EXISTS | FILE_RENAME_FLAG_POSIX_SEMANTICS
    info.RootDirectory = None
    info.FileNameLength = len(name)  # UTF-16-Bytes, ohne Abschlussnull, auch für Emoji.
    ctypes.memmove(ctypes.addressof(puffer) + versatz, name, len(name))
    # DELETE-Recht auf der Quelle; alle Freigaben, damit kein eigener Griff sperrt.
    griff = _winapi.CreateFile(
        os.fsdecode(quelle), 0x10000, 0x7, _winapi.NULL,
        _winapi.OPEN_EXISTING, 0x80, _winapi.NULL)
    try:
        if not setzen(griff, 22, puffer, groesse):  # FileRenameInfoEx = 22.
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        _winapi.CloseHandle(griff)


def _json_ersetzen(quelle, ziel):
    """Nur bei fehlender POSIX-Unterstützung den bisherigen Ersetzer verwenden."""
    try:
        _win_posix_ersetzen(quelle, ziel)
    except OSError as fehler:
        # INVALID_FUNCTION, NOT_SUPPORTED, INVALID_PARAMETER, CALL_NOT_IMPLEMENTED.
        if getattr(fehler, "winerror", None) not in (1, 50, 87, 120):
            raise
        # Der native Quellgriff ist bereits geschlossen. Nicht global merken:
        # Unterstützung kann sich zwischen zwei Ziel-Dateisystemen unterscheiden.
        os.replace(quelle, ziel)


def json_schreiben(pfad, daten):
    """Atomar schreiben (eigene tmp-Datei + replace). Rückgabe True bei Erfolg.

    **Der tmp-Name MUSS je Schreiber eindeutig sein.** Bis 23.07.2026 hieß er fest
    `<pfad>.tmp` — und genau daran zerbrachen Dateien unter Last mehrerer Prozesse.
    Gemessen mit 8 gleichzeitigen Schreibern und 4 Lesern auf einer Datei:
    **3.105 von 3.200 Schreibvorgängen schlugen fehl** (Windows-Freigabekonflikt am
    gemeinsamen tmp) und **2.835 Lesevorgänge sahen ungültiges JSON**. Der Grund ist
    tückisch: `os.replace` IST atomar — nur nützt das nichts, wenn zwei Prozesse
    vorher dieselbe Quelldatei beschreiben und einer die halb gefüllte verschiebt.
    Mit eigenem tmp-Namen je Prozess/Thread: 0 kaputte Lesevorgänge.

    **Zweiter Windows-Befund derselben Messung:** `os.replace` scheitert, solange ein
    LESER die Zieldatei geöffnet hat (Freigabekonflikt) — bei 4 Dauer-Lesern schlugen
    so noch 2.984 von 3.200 Schreibvorgängen fehl, obwohl niemand etwas falsch machte.
    JR61 (22.10.2026): Löschfreigabe allein genügte im roten Zwischenstand nicht:
    **240 von 240 Schreibvorgängen** scheiterten bei gehaltenen freigegebenen Lesern.
    Deshalb gibt `json_laden` alle 3 Freigaben und der Windows-Ersetzer nutzt
    FileRenameInfoEx mit POSIX-Semantik. Alte Leser behalten den alten Inhalt,
    neue Leser bekommen den neuen. Ohne Unterstützung bleibt `os.replace` mit
    den bisherigen 25 Wiederholungen; Linux/macOS verwenden es unverändert.
    """
    tmp = f"{pfad}.{os.getpid()}.{threading.get_ident():x}.tmp"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(pfad)), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=1)
    except (OSError, TypeError, ValueError):
        _aufraeumen(tmp)
        return False
    ersetzen = _json_ersetzen if os.name == "nt" else os.replace
    for versuch in range(25):
        try:
            ersetzen(tmp, pfad)
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


def json_aendern(pfad, aenderung, standard=None, wartezeit_s=5.0, streng=False):
    """Lesen-Ändern-Schreiben UNTER EINER SPERRE — für gemeinsam geführte Dateien.

    `json_schreiben` allein genügt dafür nicht: Es schreibt zwar heil, aber zwei
    Sessions, die gleichzeitig lesen, je einen Eintrag ergänzen und zurückschreiben,
    überschreiben sich gegenseitig. Gemessen (8 Sessions): **5 von 8 Einträgen waren
    am Ende weg** — jede Datei war für sich gültig, der Inhalt trotzdem falsch. Genau
    so gehen Einträge verloren.

    `aenderung(daten)` bekommt die geladenen Daten und gibt die neuen zurück (oder
    ändert sie in place und gibt None zurück). Rückgabe: die geschriebenen Daten,
    oder None, wenn die Sperre nicht zu bekommen war.

    Nicht-destruktiv im Zweifel: Bekommt niemand die Sperre, wird NICHT blind
    geschrieben — lieber diese Änderung auslassen als die Arbeit anderer wegwerfen.
    Eine verwaiste Sperre (Prozess abgestürzt) verfällt nach `SPERRE_ALT_S`.

    `streng=True` (Register JR68, 21.10.2026): Liegt die Datei vor, ist aber nicht lesbar
    (kaputt oder gerade blockiert), wird NICHT geschrieben — Rückgabe None. Für Dateien, die
    ein Ersatzstand nie überschreiben darf (große Caches, handgepflegte Korrekturen,
    Historien). Ohne `streng` heilt die Funktion eine kaputte Datei mit `standard`.
    None kommt auch, wenn das Schreiben selbst scheitert (bis 21.10. verschwiegen).
    """
    pfad = str(pfad)          # auch Path-Objekte annehmen (10.08.: stuerzte sonst ab)
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
        except PermissionError:
            # Windows (06.10.2026): Die Sperre des Vorgängers ist gelöscht, aber noch
            # nicht weg („Löschen ausstehend", solange jemand sie offen hält, auch ein
            # Virenscanner). Das ist belegt, nicht kaputt: weiter warten. Sofort None
            # verbrannte alle Versuche in Millisekunden (Wächter test_nebenlaeufigkeit).
            time.sleep(0.01)
        except OSError:
            return None
    if griff is None:
        return None
    try:
        leer = {} if standard is None else standard
        daten = json_laden(pfad, leer)      # bei Fehler: genau `leer` (Identität zählt)
        if streng and daten is leer and os.path.exists(pfad):
            return None
        neu = aenderung(daten)
        if neu is None:
            neu = daten
        return neu if json_schreiben(pfad, neu) else None
    finally:
        os.close(griff)
        try:
            os.remove(sperre)
        except OSError:
            pass
