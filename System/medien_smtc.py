# -*- coding: utf-8 -*-
"""Windows-Medienanmeldung des VLC-Motors (JB-Go 23.09.2026, „pywinrt im Server").

Warum es das gibt: Spielt SyncYouTube über das Gerät „VLC" (Musik, Filme im
VLC, Live-TV), kommt der Ton aus libvlc im SERVER-Prozess. Der Browser meldet
sich zwar per Media Session API bei Windows an, spielt in diesem Modus aber
selbst nichts — Windows kannte SyncYouTube dann nicht (live gemessen): kein
Titel im Medien-Overlay, Medientasten gingen ins Leere oder an eine andere App.

Dieses Modul kapselt ALLES, was mit WinRT zu tun hat (SystemMediaTransport-
Controls, kurz SMTC). Den Weg hat die Machbarkeits-Probe vom 23.09. festgelegt:
ein eigenes, unsichtbares Top-Level-Fenster (WS_POPUP, eigener Faden mit
Nachrichtenschleife) und `winrt.windows.media.interop.get_for_window(hwnd)` —
ein reiner Serverprozess hat sonst kein Fenster, an das Windows die Sitzung
hängen könnte.

Bauform (Einbahn wie geo/vpn/filme): das Modul importiert youtube_app NIE.
Der Server reicht Rückrufe herein (Knopf ausführen, Titel nachschlagen,
Protokoll). Drei Regeln für die Fäden:

* WinRT-Aufrufe laufen NUR im eigenen Arbeitsfaden. Ein HTTP-Handler legt
  lediglich den Soll-Zustand ab und kehrt sofort zurück — ein hängender
  Windows-Mediendienst kann so nie einen Handler oder die VLC-Sperre halten.
  Eine Ausnahme, gemessen 24.09.: `get_for_window` (pywinrt-Interop) gibt
  den GIL NICHT frei. Während dieses einen Aufrufs je Prozess stehen alle
  Python-Fäden; hinge er, stünde der Server. Darum braucht das unsichtbare
  Fenster selbst nie Python (siehe _fenster_bauen) — so kann wenigstens eine
  Nachricht an das Fenster diesen Aufruf nicht verklemmen.
* Knopf-Ereignisse kommen auf WinRT-Fäden an. Sie zählen nur hoch oder
  starten einen kurzen Faden für den VLC-Befehl: würde der Ereignis-Faden
  selbst auf die VLC-Sperre warten, während ein Handler unter dieser Sperre
  gerade die SMTC anfasst, wäre eine Verklemmung möglich.
* Fehlt pywinrt oder scheitert die Anmeldung: EIN Protokolleintrag,
  `verfuegbar` wird False, alles andere läuft wie bisher. pywinrt wird erst
  im Arbeitsfaden importiert — der Server startet auch ohne (Quellstart mit
  eigenem Python).
"""
import math
import re
import sys
import threading
import time
from collections import OrderedDict
from datetime import timedelta

SEITE_FRISCH = 3.0       # s: so lange gilt eine Seite als offen (Vertrag Punkt 5)
ZEITLEISTE_TAKT = 0.9    # s: „höchstens etwa 1x pro Sekunde" — 0.9 statt 1.0, damit
                         # der 1-s-Takt der Seite (Zittern ±50 ms) nicht jede zweite
                         # Meldung verschluckt und die Zeitleiste im 2-s-Ruck liefe.
AUS_NACHLAUF = 1.5       # s: zwischen zwei Titeln meldet VLC kurz 'ende', der nächste
                         # play kommt Millisekunden später. Sofort abmelden hieße: die
                         # Sitzung verschwindet bei JEDEM Titelwechsel und kommt wieder
                         # (Overlay flackert, Medientasten landen kurz woanders).
META_MAX = 16            # Metadaten je key; die Seite schickt höchstens den laufenden
                         # und den nächsten Titel vorab — 16 ist reichlich Puffer.
ABMELDE_VERSUCHE = 5     # scheitert das Abmelden, holt der Arbeitsfaden es je Nachlauf
                         # selbst nach — höchstens so oft, dann erst beim nächsten Status
                         # (ein dauerhaft toter Mediendienst soll keine Endlosschleife sein).
FENSTER_KLASSE = "SyncYouTubeSmtc"

# Cover: nur ein Pfad der eigenen Seite. Druckbares ASCII ohne Leerzeichen,
# kein „//" am Anfang (sonst wäre es eine protokoll-relative FREMDE Adresse),
# kein Backslash (Windows würde \\server\ als UNC-Pfad deuten). fullmatch statt
# ^…$: „$" passt in Python auch VOR einem abschließenden Zeilenumbruch.
_PFAD_OK = re.compile(r"/(?![/\\])[\x21-\x7e]*")
# Und nur diese beiden Bild-Routen (Skeptiker-Befund 24.09.): Windows holt das
# Cover VOM EIGENEN PC ab (127.0.0.1), 'medien' darf aber auch ein gekoppeltes
# Handy schicken. Jeder andere eigene Pfad wäre ein Umweg an den „nur lokal"-
# Riegeln vorbei — /api/ordner_waehlen öffnete am PC einen Ordnerdialog.
# Verglichen wird der GANZE Pfad vor dem „?", denn der Server prüft per
# startswith (ein „/api/coverx" landete dort sonst auch beim Cover).
BILD_ROUTEN = frozenset({"/api/cover", "/api/filme/bild"})
_STEUERZEICHEN = re.compile(r"[\x00-\x1f\x7f]+")
_PRAEFIX = re.compile(r"^[a-z]+:")


def cover_url(pfad, port):
    """Bild-Pfad der eigenen Seite -> Adresse, unter der Windows das Bild
    abholt. Alles andere (fremde URL, UNC, Steuerzeichen, Nicht-Text, eine
    Nicht-Bild-Route) -> '' (verworfen)."""
    if not isinstance(pfad, str) or len(pfad) > 2000:
        return ""
    if not _PFAD_OK.fullmatch(pfad) or "\\" in pfad:
        return ""
    if pfad.split("?", 1)[0] not in BILD_ROUTEN:
        return ""
    return f"http://127.0.0.1:{int(port)}{pfad}"


def _text(wert, laenge=300):
    t = "" if wert is None else str(wert)
    return _STEUERZEICHEN.sub(" ", t).strip()[:laenge]


def _zahl(wert):
    try:
        z = float(wert or 0)
    except (TypeError, ValueError):
        return 0.0
    return z if math.isfinite(z) and z > 0 else 0.0


def _kurzer_faden(aufgabe):
    threading.Thread(target=aufgabe, name="SMTC-Knopf", daemon=True).start()


def _winrt_laden():
    """pywinrt erst hier importieren (lazy, im Arbeitsfaden). Gemessen 23.09.:
    der Import allein initialisiert KEIN COM-Apartment (CoGetApartmentType ->
    CO_E_NOTINITIALIZED) — darum hier ausdrücklich MTA. Im MTA sind die
    SMTC-Objekte auch von den WinRT-Ereignis-Fäden aus erreichbar."""
    from types import SimpleNamespace
    from winrt.runtime import ApartmentType, init_apartment
    from winrt.windows.foundation import Uri
    from winrt.windows.media import (MediaPlaybackStatus, MediaPlaybackType,
                                     SystemMediaTransportControlsButton,
                                     SystemMediaTransportControlsTimelineProperties)
    from winrt.windows.media.interop import get_for_window
    from winrt.windows.storage.streams import RandomAccessStreamReference
    try:
        init_apartment(ApartmentType.MULTI_THREADED)
    except Exception:                                # noqa: BLE001 — schon initialisiert ist auch gut
        pass
    return SimpleNamespace(Uri=Uri, Status=MediaPlaybackStatus, Typ=MediaPlaybackType,
                           Knopf=SystemMediaTransportControlsButton,
                           Zeitleiste=SystemMediaTransportControlsTimelineProperties,
                           get_for_window=get_for_window, Bildquelle=RandomAccessStreamReference)


_fenster = {"hwnd": 0}
_fenster_lock = threading.Lock()


def _fenster_bauen(wartezeit=5.0):
    """Unsichtbares Top-Level-Fenster samt Nachrichtenschleife in einem eigenen
    daemon-Faden (Muster der Probe vom 23.09.); liefert das hwnd, 0 bei Fehlschlag.

    Warum mit Nachrichtenschleife: ein Top-Level-Fenster ohne Schleife gilt als
    „hängt" — Rundsendungen anderer Programme (z. B. WM_SETTINGCHANGE) würden
    auf uns warten. Genau EIN Fenster je Prozess; ein zweiter Aufruf liefert es
    wieder.

    Warum DefWindowProcW selbst als Fensterprozedur (nativer Zeiger, kein
    Python-Rückruf): get_for_window hält den GIL (gemessen 24.09.). Eine
    Nachricht, die währenddessen an dieses Fenster geschickt wird, beantwortet
    Windows innerhalb von GetMessageW — mit einem Python-Rückruf bräuchte das
    den GIL, und der ganze Server stünde. Nativ braucht das Fenster den GIL
    nie, und es gibt keinen Rückruf, der am Leben gehalten werden muss."""
    with _fenster_lock:
        if _fenster["hwnd"]:
            return _fenster["hwnd"]
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)      # eigene Instanz:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # fremde argtypes bleiben unberührt
        LRESULT = ctypes.c_ssize_t

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", ctypes.c_void_p),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

        user32.RegisterClassW.argtypes = (ctypes.POINTER(WNDCLASSW),)
        user32.RegisterClassW.restype = wintypes.ATOM
        user32.CreateWindowExW.argtypes = (wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                           wintypes.DWORD, ctypes.c_int, ctypes.c_int,
                                           ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                           wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID)
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                       wintypes.UINT, wintypes.UINT)
        user32.GetMessageW.restype = wintypes.BOOL
        user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)
        user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)
        user32.DispatchMessageW.restype = LRESULT
        kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        proc = ctypes.cast(user32.DefWindowProcW, ctypes.c_void_p).value
        bereit, box = threading.Event(), {"h": 0}

        def schleife():
            try:
                hinst = kernel32.GetModuleHandleW(None)
                wc = WNDCLASSW()
                wc.lpfnWndProc = proc
                wc.hInstance = hinst
                wc.lpszClassName = FENSTER_KLASSE
                user32.RegisterClassW(ctypes.byref(wc))  # 0 = gibt es schon; Fenster geht trotzdem
                box["h"] = user32.CreateWindowExW(0, FENSTER_KLASSE, "SyncYouTube",
                                                  0x80000000,  # WS_POPUP, unsichtbar
                                                  0, 0, 0, 0, None, None, hinst, None) or 0
            finally:
                bereit.set()
            if not box["h"]:
                return
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        threading.Thread(target=schleife, name="SMTC-Fenster", daemon=True).start()
        bereit.wait(wartezeit)
        _fenster["hwnd"] = int(box["h"] or 0)
        return _fenster["hwnd"]


class SmtcBruecke:
    """Hält die Windows-Mediensitzung auf dem Stand des VLC-Motors.

    Öffentlich (fadensicher, blockiert nie): `nachfuehren(status)`,
    `medien(daten)`, `seite_meldet()`, `felder()`, `verfuegbar`.
    `faden=False` / `ausfuehren` / `uhr` / `nachlauf` sind nur für Tests: dort
    läuft der Abgleich synchron im Aufrufer, mit steuerbarer Uhr."""

    def __init__(self, port=8776, befehl=None, titel_nachschlagen=None, log=None,
                 faden=True, ausfuehren=None, uhr=time.monotonic, nachlauf=AUS_NACHLAUF):
        self._port = int(port)
        self._befehl = befehl or (lambda was, wert=None: None)
        self._nachschlagen = titel_nachschlagen
        self._log = log or (lambda text: None)
        self._faden_an = bool(faden)
        self._ausfuehren = ausfuehren or _kurzer_faden
        self._uhr = uhr
        self._nachlauf = float(nachlauf)
        # Geteilt zwischen Handlern, Knopf-Fäden und Arbeitsfaden (unter _lock):
        self._lock = threading.Lock()
        self._wecker = threading.Event()
        self._arbeiter = None
        self._meta = OrderedDict()
        self._taste = {"n": 0, "was": "", "vor": 0, "zurueck": 0}
        self._seite_ts = None
        self._soll = None
        self._soll_neu = False
        self._gespult = False
        self._kaputt = ""
        self._gemeldet = set()
        # Nur der Abgleich fasst diese an (Arbeitsfaden bzw. synchron unter _abgleich):
        self._abgleich = threading.Lock()
        self._w = None
        self._smtc = None
        self._griffe = []
        self._ist = {}
        self._unsicher = False       # nach einem Fehlschlag: zeigt Windows die Sitzung noch?
        self._abmelde_fehler = 0
        self._aus_seit = None
        self._tl_ts = None

    # ---- öffentliche Seite -------------------------------------------------

    @property
    def verfuegbar(self):
        """Windows-Anmeldung möglich: Windows und kein bekannter Fehlschlag.
        Vor dem ersten Abspielen ist das eine Erwartung (lazy) — scheitert die
        Anmeldung dann, meldet die nächste Antwort ehrlich False."""
        return sys.platform == "win32" and not self._kaputt

    def felder(self):
        """Die Zusatzfelder JEDER /api/vlc-Antwort (Vertrag Punkt 3)."""
        with self._lock:
            return {"smtc": self.verfuegbar, "taste": dict(self._taste)}

    def seite_meldet(self):
        """Eine Seite hat /api/vlc abgefragt — nur dann gibt es jemanden, der
        die Warteschlange weiterschalten kann (⏭/⏮ freigeben)."""
        with self._lock:
            self._seite_ts = self._uhr()

    def medien(self, daten):
        """Metadaten der Seite für GENAU einen key merken (vor oder nach dessen
        play — der Abgleich nimmt sie, sobald VLC diesen key spielt)."""
        key = _text(daten.get("key"), 400)
        if not key:
            return False
        eintrag = {"titel": _text(daten.get("titel")),
                   "interpret": _text(daten.get("interpret")),
                   "album": _text(daten.get("album")),
                   "cover": cover_url(daten.get("cover"), self._port),
                   "weiter": bool(daten.get("weiter")),
                   "zurueck": bool(daten.get("zurueck"))}
        with self._lock:
            self._meta[key] = eintrag
            self._meta.move_to_end(key)
            while len(self._meta) > META_MAX:
                self._meta.popitem(last=False)
        return True

    def nachfuehren(self, status, gespult=False):
        """Neuen VLC-Status als Soll ablegen. Kehrt sofort zurück; die
        WinRT-Arbeit macht der Arbeitsfaden (der erst beim ersten Bedarf
        entsteht — ohne VLC-Wiedergabe gibt es weder Faden noch Fenster)."""
        soll = {"key": _text(status.get("key"), 400),
                "zustand": str(status.get("zustand") or "aus"),
                "pos": _zahl(status.get("pos")), "dauer": _zahl(status.get("dauer"))}
        starten = False
        with self._lock:
            self._soll = soll
            self._soll_neu = True
            self._gespult = self._gespult or bool(gespult)
            if (self._faden_an and self._arbeiter is None and not self._kaputt
                    and self._aktiv(soll)):
                self._arbeiter = threading.Thread(target=self._schleife,
                                                  name="SMTC-Arbeiter", daemon=True)
                starten = True
        if not self._faden_an:
            self._schritt()
            return
        if starten:
            self._arbeiter.start()
        self._wecker.set()

    # ---- Arbeitsfaden -------------------------------------------------------

    @staticmethod
    def _aktiv(soll):
        # 'laedt' = libvlc öffnet/puffert (der Server meldet es aus Opening/
        # Buffering): kein „aus" — sonst verschwände die Sitzung bei jedem
        # Titelstart und bei jedem Puffern eines Film-/Live-Stroms.
        return bool(soll["key"]) and soll["zustand"] in ("spielt", "pause", "laedt")

    def _schleife(self):
        while True:
            self._wecker.wait(self._frist())
            self._wecker.clear()      # VOR dem Lesen: ein Soll danach weckt erneut
            self._schritt()

    def _frist(self):
        """Sekunden bis zur nächsten Selbst-Prüfung (None = schlafen, bis ein
        Soll kommt): Ende des Nachlaufs und Ablauf der Seiten-Frische — ohne
        sie blieben Sitzung bzw. ⏭/⏮ stehen, wenn keine Seite mehr fragt."""
        jetzt, fristen = self._uhr(), []
        nachholen = self._unsicher and self._abmelde_fehler < ABMELDE_VERSUCHE
        if self._aus_seit is not None and (self._ist.get("an") or nachholen):
            fristen.append(self._aus_seit + self._nachlauf - jetzt)
        if any(self._ist.get("nav") or ()):
            with self._lock:
                ts = self._seite_ts
            if ts is not None:
                fristen.append(ts + SEITE_FRISCH - jetzt + 0.05)
        return max(0.05, min(fristen)) if fristen else None

    def _schritt(self):
        with self._abgleich:
            with self._lock:
                soll, neu, gespult = self._soll, self._soll_neu, self._gespult
                self._soll_neu = self._gespult = False
                meta = self._meta.get(soll["key"]) if soll else None
                seite_ts = self._seite_ts
            if soll is None:
                return
            try:
                if meta is None and self._aktiv(soll):
                    meta = self._rueckfall(soll["key"])
                self._anwenden(soll, neu, gespult, meta, seite_ts)
            except Exception as e:                   # noqa: BLE001 — nie den Faden reißen
                # Was Windows jetzt zeigt, ist UNBEKANNT (nicht „nichts"): der
                # aktive Zweig setzt beim nächsten Abgleich alles neu, der
                # inaktive meldet (erneut) ab — sonst bliebe eine Sitzung, deren
                # Abmeldung einmal scheiterte, für immer stehen.
                self._ist = {}
                self._unsicher = self._smtc is not None
                self._melden(f"Abgleich mit Windows gescheitert: {e}")

    def _rueckfall(self, key):
        """Kein Metadaten-Paket für diesen key: Bibliothekstitel (Musik), sonst
        der key ohne Präfix ('live:Das Erste' -> 'Das Erste'). Cover leer,
        weiter/zurück frei (Vertrag Punkt 2)."""
        info = None
        if self._nachschlagen is not None:
            try:
                info = self._nachschlagen(key)
            except Exception:                        # noqa: BLE001 — dann eben der key
                info = None
        if info and _text(info.get("titel")):
            titel, interpret, album = (_text(info.get("titel")), _text(info.get("interpret")),
                                       _text(info.get("album")))
        else:
            titel, interpret, album = _PRAEFIX.sub("", key, count=1), "", ""
        return {"titel": titel, "interpret": interpret, "album": album, "cover": "",
                "weiter": True, "zurueck": True}

    def _bereit(self):
        """SMTC beim ersten Bedarf anlegen: pywinrt laden, Fenster bauen,
        get_for_window. Jeder Fehlschlag ist endgültig (EIN Protokolleintrag,
        verfuegbar=False) — im Sekundentakt neu versuchen brächte nur Lärm."""
        if self._smtc is not None or self._kaputt:
            return self._smtc
        try:
            self._w = _winrt_laden()
        except Exception as e:                       # noqa: BLE001 — pywinrt fehlt
            self._kaputt = "pywinrt fehlt"
            self._melden(f"nicht verfügbar, pywinrt fehlt ({e}). Der VLC-Motor spielt "
                         "weiter, nur ohne Windows-Overlay und Medientasten.")
            return None
        try:
            hwnd = _fenster_bauen()
            if not hwnd:
                raise OSError("unsichtbares Fenster ließ sich nicht anlegen")
            smtc = self._w.get_for_window(hwnd)
            self._griffe = [smtc.add_button_pressed(self._knopf),
                            smtc.add_playback_position_change_requested(self._spulen)]
        except Exception as e:                       # noqa: BLE001 — Anmeldung verweigert
            self._kaputt = "Anmeldung gescheitert"
            self._melden(f"Anmeldung bei Windows gescheitert ({e}). Der VLC-Motor "
                         "spielt weiter, nur ohne Windows-Overlay und Medientasten.")
            return None
        self._smtc = smtc
        return smtc

    def _anwenden(self, soll, neu, gespult, meta, seite_ts):
        jetzt = self._uhr()
        if not self._aktiv(soll):
            if not self._ist.get("an") and not self._unsicher:
                self._aus_seit = None
                return
            if self._aus_seit is None:
                self._aus_seit = jetzt
            if jetzt - self._aus_seit < self._nachlauf:
                return                               # Nachlauf: gleich kommt vielleicht der nächste Titel
            self._abmelden()
            return
        self._aus_seit = None
        smtc = self._bereit()
        if smtc is None:
            return
        w = self._w
        if not self._ist.get("an"):
            smtc.is_play_enabled = True
            smtc.is_pause_enabled = True
            smtc.is_stop_enabled = True
            smtc.is_enabled = True
            self._ist = {"an": True}
            self._unsicher, self._abmelde_fehler = False, 0
        key = soll["key"]
        video = key.startswith(("film:", "live:"))
        anzeige = (key, video, meta["titel"], meta["interpret"], meta["album"], meta["cover"])
        neuer_titel = anzeige != self._ist.get("anzeige")
        if neuer_titel:
            self._anzeige_setzen(smtc, anzeige)
            self._ist["anzeige"] = anzeige
        if key != self._ist.get("key"):
            # Die Zeitleiste des Vorgängers löschen: ein Live-Sender (dauer 0)
            # zeigte sonst die Position des letzten Lieds weiter an.
            self._zeitleiste(smtc, 0.0, 0.0)
            self._ist["key"] = key
            self._tl_ts = None
        status = {"spielt": w.Status.PLAYING, "pause": w.Status.PAUSED,
                  "laedt": w.Status.CHANGING}[soll["zustand"]]
        statuswechsel = status != self._ist.get("status")
        if statuswechsel:
            smtc.playback_status = status
            self._ist["status"] = status
        frisch = seite_ts is not None and jetzt - seite_ts <= SEITE_FRISCH
        nav = (bool(meta["weiter"]) and frisch, bool(meta["zurueck"]) and frisch)
        if nav != self._ist.get("nav"):
            smtc.is_next_enabled, smtc.is_previous_enabled = nav
            self._ist["nav"] = nav
        # Zeitleiste nur aus einem FRISCHEN Status (eine Selbst-Prüfung nach
        # Fristablauf trägt eine alte Position), höchstens etwa 1x pro Sekunde,
        # sofort nach Spulen, Titel- oder Statuswechsel.
        if soll["dauer"] > 0 and (neu or gespult) and (
                gespult or statuswechsel or neuer_titel or self._tl_ts is None
                or jetzt - self._tl_ts >= ZEITLEISTE_TAKT):
            self._zeitleiste(smtc, soll["pos"], soll["dauer"])
            self._tl_ts = jetzt

    def _anzeige_setzen(self, smtc, anzeige):
        _key, video, titel, interpret, album, cover = anzeige
        w = self._w
        du = smtc.display_updater
        du.clear_all()                               # sauberer Stand beim Wechsel Musik <-> Video
        if video:
            du.type = w.Typ.VIDEO
            du.video_properties.title = titel
            du.video_properties.subtitle = interpret
        else:
            du.type = w.Typ.MUSIC
            du.music_properties.title = titel
            du.music_properties.artist = interpret
            du.music_properties.album_title = album
        if cover:
            du.thumbnail = w.Bildquelle.create_from_uri(w.Uri(cover))
        du.update()

    def _zeitleiste(self, smtc, pos, dauer):
        tl = self._w.Zeitleiste()
        tl.start_time = timedelta(0)
        tl.min_seek_time = timedelta(0)
        tl.position = timedelta(seconds=min(max(0.0, pos), dauer))
        tl.max_seek_time = timedelta(seconds=dauer)
        tl.end_time = timedelta(seconds=dauer)
        smtc.update_timeline_properties(tl)

    def _abmelden(self):
        try:
            self._smtc.is_enabled = False            # Windows entfernt die Sitzung
        except Exception:
            # Nach einem weiteren Nachlauf erneut versuchen — der Arbeitsfaden
            # wacht dafür selbst auf (_frist), auch wenn keine Seite mehr fragt.
            self._abmelde_fehler += 1
            self._aus_seit = self._uhr()
            raise
        self._ist = {}
        self._unsicher, self._abmelde_fehler = False, 0
        self._aus_seit = None
        self._tl_ts = None

    # ---- Ereignisse aus Windows (WinRT-Fäden) -------------------------------

    def _knopf(self, sender, args):
        try:
            name = self._w.Knopf(args.button).name
        except Exception:                            # noqa: BLE001 — unbekannter Knopf
            return
        if name in ("NEXT", "PREVIOUS"):
            # Die Warteschlange lebt in der Seite: nur zählen, die Seite führt
            # jede Änderung genau einmal aus (Muster wie _remote).
            with self._lock:
                self._taste["n"] += 1
                self._taste["was"] = "next" if name == "NEXT" else "prev"
                # Je Richtung mitzählen: ⏭ und ein schnell folgendes ⏮ zwischen
                # zwei Abfragen der Seite sollen sich aufheben, nicht zweimal
                # in der letzten Richtung wirken (Prüf-Befund 24.09.2026).
                self._taste["vor" if name == "NEXT" else "zurueck"] += 1
            return
        # STOP pausiert wie die Browser-Seite (stop = pause, Medium bleibt).
        was = {"PLAY": "play", "PAUSE": "pause", "STOP": "pause"}.get(name)
        if was:
            self._ausfuehren(lambda: self._befehl_sicher(was))

    def _spulen(self, sender, args):
        try:
            p = args.requested_playback_position
            sek = p.total_seconds() if hasattr(p, "total_seconds") else float(p) / 1e7
        except Exception:                            # noqa: BLE001 — kaputte Anfrage ignorieren
            return
        sek = max(0.0, float(sek))
        self._ausfuehren(lambda: self._befehl_sicher("seek", sek))

    def _befehl_sicher(self, was, wert=None):
        try:
            self._befehl(was, wert)
        except Exception as e:                       # noqa: BLE001 — Knopf darf nie etwas reißen
            self._melden(f"Knopf '{was}' am VLC gescheitert: {e}")

    def _melden(self, text):
        """Jede Meldung genau EINMAL ins Protokoll (kein Sekundentakt-Lärm)."""
        with self._lock:
            if text in self._gemeldet or len(self._gemeldet) > 50:
                return
            self._gemeldet.add(text)
        try:
            self._log(text)
        except Exception:                            # noqa: BLE001 — Protokoll ist Kür
            pass
