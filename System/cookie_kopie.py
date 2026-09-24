# -*- coding: utf-8 -*-
"""Firefox-Cookies für yt-dlp samt WAL — Lehre aus SyncFindus (24.09.2026).

BEFUND (geprüft an yt-dlp 2026.08.19, `yt_dlp/cookies.py`, `_open_database_copy`):
yt-dlp kopiert beim Lesen der Firefox-Cookies nur `cookies.sqlite`, nicht das
`-wal` daneben. Firefox schreibt im WAL-Modus; alles seit seinem letzten
Checkpoint steht nur im `-wal` — gerade die frischen Anmelde-Cookies nach einem
neuen Login bei YouTube. SyncYouTube übergab `cookiesfrombrowser=("firefox",)`
und lud deshalb mit dem alten Stand (gemessen in `tests/test_cookies_wal.py`).

DER WEG (derselbe Gedanke wie `fremde_datenbank.lese_kopie` in SyncFindus):

1. Die Quelle ist dieselbe Datei, die yt-dlp heute nähme (seine eigene
   Profilsuche, jüngste `cookies.sqlite`).
2. Ein frischer, privater Ordner je Aufruf (`mkdtemp`): zwei Fäden teilen sich
   nie eine Kopie, und ein liegengebliebenes `-wal` gerät nie auf eine neuere
   Hauptdatei.
3. Hauptdatei und `-wal` werden nur als DATEI gelesen, so wie yt-dlp es heute
   schon tut, nie als Datenbank geöffnet. Firefox darf dabei laufen — auch
   wenn er die Datei exklusiv hält, dann weist SQLite jede fremde Verbindung
   mit „database is locked" ab (gemessen 24.09.) —, und in seinem Profil
   entsteht keine Datei.
4. Der WAL-Kopf wird VOR der Hauptdatei gelesen und mit dem der Kopie
   verglichen. Beginnt Firefox das WAL dazwischen neu, passen Hauptdatei und
   WAL nicht zusammen; dann von vorn, höchstens `VERSUCHE` Mal.
5. Die SQLite-Backup-API zieht aus der Rohkopie (Hauptdatei + WAL) EINE
   vollständige `profil/cookies.sqlite`, danach im Rollback-Modus — eine
   einzige Datei ohne WAL-Kopf. Direkt vom Original ginge das nicht: hält
   Firefox die Datei exklusiv, wiederholt Pythons `Connection.backup` das
   „database is locked" endlos (gemessen: nach 600 s noch nicht zurück).
   Nur dieser Ordner geht als
   Firefox-Profil an yt-dlp — dessen Kopie der Hauptdatei enthält dann alles.
   Vorher sucht yt-dlps eigene Profilsuche die Datei dort: findet sie sie
   nicht (etwa wegen eines Sonderzeichens im Temp-Pfad), gilt die Kopie als
   gescheitert.
6. Nach dem Block ist der Ordner weg — keine Cookie-Kopien im Temp.

Bei JEDEM Fehler (kein Firefox, kein yt-dlp, Datei unlesbar, kein stimmiges
Paar, Backup scheitert, Tabelle fehlt) liefert `firefox_profil` None, und der
Aufrufer nimmt den heutigen Weg — nie schlechter als vorher.

Cookie-WERTE liest dieses Modul nie aus und schreibt sie nirgends hin; die
Prüfung der Kopie zählt nur Zeilen.
"""
import contextlib
import os
import shutil
import sqlite3
import tempfile

#: Wo nach Firefox-Profilen gesucht wird. None = dieselben Orte wie yt-dlp
#: (der heutige Weg). `tests/conftest.py` setzt hier für jeden Test einen Ort
#: ohne Profil ein, damit kein Test JBs echtes Firefox-Profil liest.
WURZELN = None

#: So oft darf Firefox das WAL während der Kopie neu beginnen, bevor der
#: heutige Weg übernimmt. Jeder Neubeginn setzt einen vollständigen
#: Checkpoint voraus; schon zwei in derselben Sekunde sind ungewöhnlich.
VERSUCHE = 3

#: Der WAL-Kopf: Magie, Format, Seitengröße, Checkpoint-Nummer, Salz 1 und 2,
#: Prüfsumme. Ein Neubeginn ändert Checkpoint-Nummer und Salz.
WAL_KOPF_BYTES = 32

NAME = "cookies.sqlite"


def _quelle(wurzeln):
    """Die Cookie-Datenbank, die yt-dlp heute nähme — oder None."""
    from yt_dlp import cookies as yc
    if wurzeln is None:
        wurzeln = list(yc._firefox_browser_dirs())
    return yc._newest(yc._firefox_cookie_dbs(wurzeln))


def _wal_kopf(pfad):
    try:
        with open(pfad, "rb") as f:
            return f.read(WAL_KOPF_BYTES)
    except FileNotFoundError:
        return None


def _stimmig_kopieren(quelle, ziel):
    """Kopiert Hauptdatei und -wal; True, wenn beide zum selben WAL-Stand gehören."""
    vorher = _wal_kopf(quelle + "-wal")
    shutil.copyfile(quelle, ziel)
    try:
        shutil.copyfile(quelle + "-wal", ziel + "-wal")
    except FileNotFoundError:
        pass                          # kein WAL (mehr): der Vergleich entscheidet
    return _wal_kopf(ziel + "-wal") == vorher


def _yt_dlp_findet(profil, ziel):
    """Findet yt-dlp mit diesem Profilpfad genau die Kopie? (seine eigene Suche)"""
    from yt_dlp import cookies as yc
    _, gesehen, _, _ = yc._parse_browser_specification("firefox", profil)
    gefunden = yc._newest(yc._firefox_cookie_dbs([gesehen]))
    return bool(gefunden) and os.path.normcase(os.path.abspath(gefunden)) \
        == os.path.normcase(os.path.abspath(ziel))


def _vollstaendige_kopie(quelle, ordner):
    """Profilordner mit einer vollständigen Kopie von `quelle`, oder None."""
    for versuch in range(1, VERSUCHE + 1):
        roh_ordner = os.path.join(ordner, f"roh{versuch}")
        os.mkdir(roh_ordner)
        roh = os.path.join(roh_ordner, NAME)
        if _stimmig_kopieren(quelle, roh):
            break
    else:
        return None
    profil = os.path.join(ordner, "profil")
    os.mkdir(profil)
    ziel = os.path.join(profil, NAME)
    with contextlib.closing(sqlite3.connect(roh)) as von, \
            contextlib.closing(sqlite3.connect(ziel)) as nach:
        von.backup(nach)
        # Die Backup-API übernimmt den WAL-Kopf der Quelle (2/2); im
        # Rollback-Modus ist die Kopie EINE Datei (Familien-Lehrbuch L88).
        nach.execute("PRAGMA journal_mode=DELETE").fetchone()
        nach.execute("SELECT count(*) FROM moz_cookies").fetchone()
    return profil if _yt_dlp_findet(profil, ziel) else None


@contextlib.contextmanager
def firefox_profil(auswahl):
    """Profilordner mit einer vollständigen Kopie der Firefox-Cookies — oder None.

    `auswahl` ist der `cookiesfrombrowser`-Wert der yt-dlp-Optionen. Ersetzt
    wird nur die Vorgabe `("firefox",)` ohne eigenes Profil, Schlüsselbund oder
    Container; alles andere liefert None, ohne etwas anzufassen. Der Ordner lebt
    bis zum Ende des Blocks. Ein Fehler IM Block geht unverändert weiter.
    """
    ordner = profil = None
    try:
        if isinstance(auswahl, (tuple, list)) and tuple(auswahl) == ("firefox",):
            quelle = _quelle(WURZELN)
            if quelle:
                ordner = tempfile.mkdtemp(prefix="syncyoutube_cookies_")
                profil = _vollstaendige_kopie(quelle, ordner)
    except Exception:                                # noqa: BLE001 — jeder Fehler: der heutige Weg
        profil = None
    try:
        yield profil
    finally:
        if ordner:
            shutil.rmtree(ordner, ignore_errors=True)
