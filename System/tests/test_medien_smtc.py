# -*- coding: utf-8 -*-
"""Windows-Medienanmeldung des VLC-Motors (medien_smtc.py, JB-Go 23.09.2026).

Spielt der VLC-Motor des Servers, soll Windows ihn als Medienquelle kennen
(Overlay mit Titel/Interpret/Album/Cover, Medientasten, Overlay-Knöpfe).

KEINE echte Windows-Anmeldung in diesen Tests: pywinrt wird durch eine
Attrappe in sys.modules ersetzt, das unsichtbare Fenster durch eine feste
Zahl, libvlc durch einen nachgebauten Spieler. Geprüft wird das ERGEBNIS —
was an der (nachgebauten) Windows-Sitzung bzw. am (nachgebauten) VLC
ankommt —, nicht die Schreibweise im Quelltext.
"""
import ast
import enum
import importlib.util
import os
import re
import sys
import threading
import time
import types
from datetime import timedelta

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app   # noqa: E402  (Import startet keinen Server und meldet nichts an)

SMTC_PFAD = os.path.join(MODUL_DIR, "medien_smtc.py")
WINRT_MODULE = ("winrt", "winrt.windows", "winrt.windows.media",
                "winrt.windows.media.interop", "winrt.windows.foundation",
                "winrt.windows.storage", "winrt.windows.storage.streams",
                "winrt.runtime")


# ---------------------------------------------------------------- Attrappen

class Knopf(enum.IntEnum):          # Werte wie pywinrt 3.2.1 (live ausgelesen 23.09.)
    PLAY = 0
    PAUSE = 1
    STOP = 2
    RECORD = 3
    FAST_FORWARD = 4
    REWIND = 5
    NEXT = 6
    PREVIOUS = 7
    CHANNEL_UP = 8
    CHANNEL_DOWN = 9


class Status(enum.IntEnum):
    CLOSED = 0
    CHANGING = 1
    STOPPED = 2
    PLAYING = 3
    PAUSED = 4


class Typ(enum.IntEnum):
    UNKNOWN = 0
    MUSIC = 1
    VIDEO = 2
    IMAGE = 3


class FakeAnzeige:
    """display_updater: erst update() macht Änderungen für Windows sichtbar —
    darum hält `gezeigt` den Stand beim letzten update() fest."""

    def __init__(self):
        self.updates = 0
        self.gezeigt = None
        self.clear_all()

    def clear_all(self):
        self.type = Typ.UNKNOWN
        self.music_properties = types.SimpleNamespace(title="", artist="", album_title="")
        self.video_properties = types.SimpleNamespace(title="", subtitle="")
        self.thumbnail = None

    def update(self):
        self.updates += 1
        if self.type == Typ.VIDEO:
            titel, interpret, album = (self.video_properties.title,
                                       self.video_properties.subtitle, "")
        else:
            titel, interpret, album = (self.music_properties.title,
                                       self.music_properties.artist,
                                       self.music_properties.album_title)
        self.gezeigt = {"typ": self.type, "titel": titel, "interpret": interpret,
                        "album": album,
                        "cover": getattr(self.thumbnail, "quelle", None)}


class FakeZeitleiste:
    def __init__(self):
        self.start_time = self.min_seek_time = self.position = None
        self.max_seek_time = self.end_time = None


class FakeSmtc:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self._an = False
        self.an_verlauf = []
        self.is_play_enabled = self.is_pause_enabled = self.is_stop_enabled = False
        self.is_next_enabled = self.is_previous_enabled = False
        self.playback_status = Status.CLOSED
        self.display_updater = FakeAnzeige()
        self.zeitleisten = []
        self.knopf_rufe, self.spul_rufe = [], []
        self.abmelde_fehler = 0          # so oft scheitert is_enabled=False (z. B. RPC-Wackler)

    @property
    def is_enabled(self):
        return self._an

    @is_enabled.setter
    def is_enabled(self, wert):
        if not wert and self.abmelde_fehler > 0:
            self.abmelde_fehler -= 1
            raise OSError("RPC_E_DISCONNECTED (Attrappe)")
        self._an = wert
        self.an_verlauf.append(wert)

    def add_button_pressed(self, handler):
        self.knopf_rufe.append(handler)
        return "griff-knopf"

    def add_playback_position_change_requested(self, handler):
        self.spul_rufe.append(handler)
        return "griff-spulen"

    def update_timeline_properties(self, tl):
        self.zeitleisten.append({k: getattr(tl, k) for k in (
            "start_time", "min_seek_time", "position", "max_seek_time", "end_time")})

    # ---- Test-Helfer: so ruft Windows die Rückrufe (sender, args) ----
    def druecken(self, knopf):
        for h in list(self.knopf_rufe):
            h(self, types.SimpleNamespace(button=knopf))

    def spulen(self, sekunden):
        for h in list(self.spul_rufe):
            h(self, types.SimpleNamespace(
                requested_playback_position=timedelta(seconds=sekunden)))

    def echte_zeitleisten(self):
        return [z for z in self.zeitleisten if z["end_time"] and z["end_time"] > timedelta(0)]


@pytest.fixture
def ms():
    """Das Modul selbst — als Fixture, damit ein fehlendes Modul jeden Test
    einzeln rot macht (statt die ganze Datei beim Sammeln zu reißen)."""
    import medien_smtc
    return medien_smtc


@pytest.fixture
def winrt_attrappe(monkeypatch, ms):
    zustand = types.SimpleNamespace(smtc=None, hwnds=[], faeden=[], apartment=[])

    def get_for_window(hwnd):
        zustand.hwnds.append(hwnd)
        zustand.faeden.append(threading.current_thread().name)
        zustand.smtc = FakeSmtc(hwnd)
        return zustand.smtc

    mods = {name: types.ModuleType(name) for name in WINRT_MODULE}
    for name in ("winrt", "winrt.windows", "winrt.windows.storage"):
        mods[name].__path__ = []
    mods["winrt.windows.media"].MediaPlaybackStatus = Status
    mods["winrt.windows.media"].MediaPlaybackType = Typ
    mods["winrt.windows.media"].SystemMediaTransportControlsButton = Knopf
    mods["winrt.windows.media"].SystemMediaTransportControlsTimelineProperties = FakeZeitleiste
    mods["winrt.windows.media.interop"].get_for_window = get_for_window
    mods["winrt.windows.foundation"].Uri = lambda s: types.SimpleNamespace(roh=s)
    mods["winrt.windows.storage.streams"].RandomAccessStreamReference = types.SimpleNamespace(
        create_from_uri=lambda uri: types.SimpleNamespace(quelle=uri.roh))
    mods["winrt.runtime"].ApartmentType = types.SimpleNamespace(MULTI_THREADED=1, SINGLE_THREADED=0)
    mods["winrt.runtime"].init_apartment = lambda art: zustand.apartment.append(art)
    for name, mod in mods.items():
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.setattr(ms, "_fenster_bauen", lambda: 4711)
    return zustand


class FakeEreignisse:
    """event_manager() von python-vlc: libvlc ruft die angehängten Rückrufe auf
    SEINEM eigenen Faden auf — darum feuert die Attrappe ebenfalls auf einem
    fremden Faden und merkt sich, wie lange jeder Rückruf gebraucht hat."""

    def __init__(self):
        self.rueckrufe = {}
        self.dauer = []

    def event_attach(self, typ, rueckruf, *args, **kw):
        self.rueckrufe.setdefault(typ, []).append((rueckruf, args, kw))
        return 0

    def feuern(self, typ):
        def lauf():
            for f, args, kw in list(self.rueckrufe.get(typ, ())):
                t0 = time.monotonic()
                f(types.SimpleNamespace(type=typ), *args, **kw)
                self.dauer.append(time.monotonic() - t0)
        t = threading.Thread(target=lauf, name="libvlc-Attrappe", daemon=True)
        t.start()
        return t


@pytest.fixture
def vlc_attrappe(monkeypatch, tmp_path):
    """Nachgebautes python-vlc mit ECHTER set_pause-Semantik (0 = weiter,
    1 = Pause) — der Kern der Knopf-Zuordnung.

    `Spieler.asynchron = True` bildet nach, was libvlc wirklich tut: play,
    set_pause und set_time wirken erst später (hier: beim nächsten `takt()`),
    play öffnet zuerst (Opening). Ohne diesen Unterschied wären die Stellen,
    die genau DAFÜR gebaut sind, in den Tests unsichtbar."""
    fake_vlc = types.ModuleType("vlc")
    fake_vlc.State = types.SimpleNamespace(Playing="P", Paused="p", Ended="E", Error="X",
                                           Stopped="S", Opening="O", Buffering="B",
                                           NothingSpecial="N")
    fake_vlc.MediaSlaveType = types.SimpleNamespace(subtitle=0)
    fake_vlc.EventType = types.SimpleNamespace(
        MediaPlayerEndReached="EndReached", MediaPlayerStopped="Stopped",
        MediaPlayerEncounteredError="EncounteredError", MediaPlayerPlaying="Playing",
        MediaPlayerPaused="Paused")

    class FakeSpieler:
        asynchron = False

        def __init__(self):
            self.zustand, self.zeit, self.vol, self.rufe = "N", 0, 100, []
            self._offen = []
            self.ereignisse = FakeEreignisse()

        def _spaeter(self, aenderung):
            if self.asynchron:
                self._offen.append(aenderung)
            else:
                aenderung()

        def takt(self):
            """libvlc hat umgeschaltet: alle ausstehenden Änderungen wirken jetzt."""
            offen, self._offen = self._offen, []
            for aenderung in offen:
                aenderung()

        def event_manager(self):
            return self.ereignisse

        def ende(self):
            """Titel zu Ende: libvlc setzt Ended und meldet EndReached (fremder Faden)."""
            self.zustand = "E"
            return self.ereignisse.feuern("EndReached")

        def set_media(self, m):
            self.rufe.append(("media", m.pfad))

        def play(self):
            self.rufe.append(("play",))
            if self.asynchron:
                self.zustand = "O"
            self._spaeter(lambda: setattr(self, "zustand", "P"))

        def pause(self):
            self.rufe.append(("toggle",))
            self.zustand = "p" if self.zustand == "P" else "P"

        def set_pause(self, x):
            self.rufe.append(("pause", x))
            self._spaeter(lambda: setattr(self, "zustand", "p" if x else "P"))

        def stop(self):
            self.rufe.append(("stop",))
            self.zustand = "S"

        def set_hwnd(self, h):
            self.rufe.append(("hwnd", h))

        def set_time(self, ms_):
            self.rufe.append(("seek", ms_))
            self._spaeter(lambda: setattr(self, "zeit", ms_))

        def get_time(self):
            return self.zeit

        def get_length(self):
            return 200000

        def audio_set_volume(self, v):
            self.vol = v

        def audio_get_volume(self):
            return self.vol

        def set_rate(self, r):
            pass

        def get_rate(self):
            return 1.0

        def get_state(self):
            return self.zustand

    class FakeInstanz:
        def media_player_new(self):
            return FakeSpieler()

        def media_new(self, pfad):
            return types.SimpleNamespace(pfad=pfad)

    fake_vlc.Instance = lambda *a: FakeInstanz()
    fake_vlc.Spieler = FakeSpieler
    monkeypatch.setitem(sys.modules, "vlc", fake_vlc)
    monkeypatch.setattr(app, "_vlc", {"instanz": None, "spieler": None, "key": "",
                                      "grund": "", "vol_wunsch": None, "hwnd": 0})
    mp3 = tmp_path / "lied.mp3"
    mp3.write_bytes(b"x" * 10)
    monkeypatch.setattr(app, "_geladen", {
        "abc|mp3": {"pfad": str(mp3), "titel": "Rick Astley - Never Gonna Give You Up (Official Video)",
                    "track": "Never Gonna Give You Up", "kuenstler": "Rick Astley",
                    "album": "Whenever You Need Somebody"},
        "xyz|mp3": {"pfad": str(mp3), "titel": "Zweites Lied", "uploader": "Kanal Zwei"},
    })
    return fake_vlc


@pytest.fixture
def bruecke(monkeypatch, ms, winrt_attrappe):
    """Die Brücke so, wie main() sie anlegt — nur synchron (faden=False,
    Knopf-Befehle sofort), damit die Tests ohne Warten auskommen."""
    monkeypatch.setattr(app, "_smtc", None)            # Rückweg: nach dem Test wieder None
    log = []
    b = app._smtc_einrichten(faden=False, ausfuehren=lambda f: f(), nachlauf=0,
                             log=log.append)
    assert app._smtc is b
    return types.SimpleNamespace(b=b, log=log)


def _spielt(key="abc|mp3", pos=3.0, dauer=200.0, zustand="spielt"):
    return {"key": key, "zustand": zustand, "pos": pos, "dauer": dauer}


def _sync(ms, **kw):
    kw.setdefault("faden", False)
    kw.setdefault("ausfuehren", lambda f: f())
    kw.setdefault("nachlauf", 0)
    return ms.SmtcBruecke(port=8776, **kw)


# ---------------------------------------------------------------- Brücke allein

def test_zustandsspiegel_und_abmeldung(ms, winrt_attrappe):
    # Vertrag Punkt 4: angemeldet, solange VLC ein Medium hat und spielt oder
    # pausiert; bei aus/ende/stop abgemeldet (Windows entfernt die Sitzung).
    b = _sync(ms)
    b.nachfuehren({"key": "abc|mp3", "zustand": "aus"})
    assert winrt_attrappe.smtc is None, "ohne laufendes Medium darf nichts angemeldet werden (lazy)"
    b.nachfuehren(_spielt())
    s = winrt_attrappe.smtc
    assert s is not None and s.hwnd == 4711, "Anmeldung muss am eigenen Fenster hängen"
    assert s.is_enabled is True and s.playback_status == Status.PLAYING
    assert s.is_play_enabled and s.is_pause_enabled and s.is_stop_enabled
    b.nachfuehren(_spielt(zustand="pause"))
    assert s.is_enabled is True and s.playback_status == Status.PAUSED
    b.nachfuehren(_spielt(zustand="ende"))
    assert s.is_enabled is False, "'ende' muss abmelden"
    b.nachfuehren(_spielt())
    assert s.is_enabled is True and s.playback_status == Status.PLAYING
    b.nachfuehren({"key": "", "zustand": "aus", "pos": 0, "dauer": 0})
    assert s.is_enabled is False, "stop (key leer) muss abmelden"
    b.nachfuehren(_spielt())
    b.nachfuehren(_spielt(zustand="aus"))
    assert s.is_enabled is False, "'aus' muss abmelden"
    b.nachfuehren(_spielt())
    b.nachfuehren(_spielt(zustand="fehler"))
    assert s.is_enabled is False, "'fehler' ist kein laufendes Medium"
    # Öffnen/Puffern eines Stroms ist kein „aus": angemeldet, Status CHANGING.
    b.nachfuehren(_spielt(zustand="laedt"))
    assert s.is_enabled is True and s.playback_status == Status.CHANGING
    assert len(winrt_attrappe.hwnds) == 1, "Fenster + Anmeldung genau EINMAL, nicht je Titel"
    assert winrt_attrappe.apartment == [1], "Arbeitsfaden muss MTA initialisieren"


def test_nachlauf_ueberbrueckt_titelwechsel(ms, winrt_attrappe):
    # Zwischen zwei Titeln meldet VLC kurz 'ende' — die Seite schickt Millisekunden
    # später den nächsten play. Ohne Nachlauf verschwände die Windows-Sitzung
    # bei JEDEM Titelwechsel und käme wieder (Overlay flackert, Medientasten
    # landen kurz bei einer anderen App).
    uhr = [100.0]
    b = _sync(ms, nachlauf=1.5, uhr=lambda: uhr[0])
    b.nachfuehren(_spielt("a|mp3"))
    s = winrt_attrappe.smtc
    uhr[0] = 101.0
    b.nachfuehren(_spielt("a|mp3", zustand="ende"))
    assert s.is_enabled is True, "innerhalb des Nachlaufs bleibt die Sitzung"
    uhr[0] = 101.2
    b.nachfuehren(_spielt("b|mp3"))
    assert False not in s.an_verlauf, "Titelwechsel darf nicht abmelden"
    uhr[0] = 110.0
    b.nachfuehren(_spielt("b|mp3", zustand="ende"))
    assert s.is_enabled is True
    uhr[0] = 111.6
    b.nachfuehren(_spielt("b|mp3", zustand="ende"))
    assert s.is_enabled is False, "nach dem Nachlauf muss abgemeldet sein"


def test_zeitleiste_takt_und_spulen(ms, winrt_attrappe):
    # Vertrag Punkt 4: Zeitleiste höchstens etwa 1x pro Sekunde, sofort nach
    # dem Spulen, nur bei dauer>0; start=min_seek=0, max_seek=end=dauer.
    uhr = [0.0]
    b = _sync(ms, uhr=lambda: uhr[0])
    b.nachfuehren(_spielt("k|mp3", pos=10, dauer=200))
    s = winrt_attrappe.smtc
    assert s.echte_zeitleisten()[-1] == {
        "start_time": timedelta(0), "min_seek_time": timedelta(0),
        "position": timedelta(seconds=10), "max_seek_time": timedelta(seconds=200),
        "end_time": timedelta(seconds=200)}
    n = len(s.echte_zeitleisten())
    uhr[0] = 0.4
    b.nachfuehren(_spielt("k|mp3", pos=10.4, dauer=200))
    assert len(s.echte_zeitleisten()) == n, "öfter als etwa 1x pro Sekunde"
    uhr[0] = 1.0
    b.nachfuehren(_spielt("k|mp3", pos=11, dauer=200))
    assert len(s.echte_zeitleisten()) == n + 1
    assert s.echte_zeitleisten()[-1]["position"] == timedelta(seconds=11)
    uhr[0] = 1.2
    b.nachfuehren(_spielt("k|mp3", pos=50, dauer=200), gespult=True)
    assert len(s.echte_zeitleisten()) == n + 2, "nach dem Spulen muss die Zeitleiste sofort folgen"
    assert s.echte_zeitleisten()[-1]["position"] == timedelta(seconds=50)
    # Live-TV (dauer 0): keine Zeitleiste — und die des Vorgängers verschwindet.
    uhr[0] = 5.0
    b.nachfuehren(_spielt("live:Das Erste", pos=5, dauer=0))
    assert len(s.echte_zeitleisten()) == n + 2, "bei dauer 0 keine Zeitleiste"
    assert s.zeitleisten[-1]["end_time"] == timedelta(0), \
        "die Zeitleiste des vorigen Titels darf beim Live-Sender nicht stehen bleiben"


def test_cover_nur_eigene_pfade(ms):
    # Vertrag Punkt 2: cover ist ein Pfad der eigenen Seite; der Server baut
    # http://127.0.0.1:<PORT>+pfad. Alles andere wird verworfen — Windows holt
    # das Bild selbst ab, eine fremde Adresse wäre ein Abruf in fremdem Auftrag.
    assert ms.cover_url("/api/cover?id=abc%7Cmp3", 8776) == \
        "http://127.0.0.1:8776/api/cover?id=abc%7Cmp3"
    assert ms.cover_url("/api/filme/bild?id=x&art=Primary", 8790) == \
        "http://127.0.0.1:8790/api/filme/bild?id=x&art=Primary"
    for boese in ("https://evil.example/x.png", "http://127.0.0.1:8776/api/cover?id=x",
                  "//evil.example/x.png", "javascript:alert(1)", "file:///C:/x.png",
                  "\\\\server\\x.png", "/\\evil.example", " /api/cover", "/api/cover?id=a b",
                  "/api/cover\n", "", None, 42, "/" + "a" * 3000):
        assert ms.cover_url(boese, 8776) == "", f"fremder/kaputter Cover-Wert durchgelassen: {boese!r}"


def test_cover_nur_bild_routen(ms):
    # Windows holt das Cover VOM EIGENEN PC ab (127.0.0.1). 'medien' darf auch
    # ein gekoppeltes Handy schicken — ließe der Filter jeden eigenen Pfad zu,
    # erreichte es über Windows die Routen, die nur für den PC selbst gelten
    # (/api/ordner_waehlen öffnet dort einen Ordnerdialog). Darum nur die
    # beiden Bild-Routen, und zwar genau diese (der Server prüft per
    # startswith — „/api/coverx" landete sonst auch beim Cover).
    for boese in ("/api/ordner_waehlen", "/api/ordner_waehlen?start=C:", "/api/pfad_da?pfad=C:",
                  "/api/migration_probelauf", "/api/coverx?id=1", "/api/cover/../ordner_waehlen?id=1",
                  "/api/filme/bildx?id=1", "/api/cover%2F..%2Fordner_waehlen?id=1", "/"):
        assert ms.cover_url(boese, 8776) == "", f"Nicht-Bild-Route als Cover durchgelassen: {boese!r}"
    assert ms.cover_url("/api/cover?id=abc%7Cmp3", 8776) == \
        "http://127.0.0.1:8776/api/cover?id=abc%7Cmp3"
    assert ms.cover_url("/api/filme/bild?id=x&art=Primary", 8776) == \
        "http://127.0.0.1:8776/api/filme/bild?id=x&art=Primary"


def test_medien_vor_und_nach_play_und_rueckfall(ms, winrt_attrappe):
    # Vertrag Punkt 2: Metadaten gelten für genau ihren key; vor oder nach
    # play — beides wirkt. Ohne passende Metadaten: sinnvoller Rückfall.
    bib = {"bib|mp3": {"titel": "Bibliothekstitel", "interpret": "Kanal", "album": ""}}
    b = _sync(ms, titel_nachschlagen=bib.get)
    b.seite_meldet()
    b.medien({"key": "a|mp3", "titel": "Titel A", "interpret": "Künstler Ä",
              "album": "Album Ö", "cover": "/api/cover?id=a%7Cmp3",
              "weiter": True, "zurueck": False})
    b.nachfuehren(_spielt("a|mp3"))
    s = winrt_attrappe.smtc
    assert s.display_updater.gezeigt == {
        "typ": Typ.MUSIC, "titel": "Titel A", "interpret": "Künstler Ä", "album": "Album Ö",
        "cover": "http://127.0.0.1:8776/api/cover?id=a%7Cmp3"}
    # Metadaten für den NÄCHSTEN Titel kommen vorab — sie dürfen den laufenden
    # nicht überschreiben, und eine fremde Cover-Adresse fällt weg.
    b.medien({"key": "b|mp3", "titel": "Titel B", "interpret": "", "album": "",
              "cover": "https://evil.example/b.png", "weiter": True, "zurueck": True})
    b.nachfuehren(_spielt("a|mp3"))
    assert s.display_updater.gezeigt["titel"] == "Titel A"
    b.nachfuehren(_spielt("b|mp3"))
    assert s.display_updater.gezeigt["titel"] == "Titel B"
    assert s.display_updater.gezeigt["cover"] is None, "fremde Cover-URL darf nicht bei Windows landen"
    # Rückfall: Musik-key aus der Bibliothek, sonst key ohne Präfix; Cover leer,
    # weiter/zurück frei (die Seite ist frisch).
    b.nachfuehren(_spielt("bib|mp3"))
    assert s.display_updater.gezeigt["titel"] == "Bibliothekstitel"
    assert s.display_updater.gezeigt["interpret"] == "Kanal"
    assert s.display_updater.gezeigt["cover"] is None
    assert s.is_next_enabled and s.is_previous_enabled
    b.nachfuehren(_spielt("film:4711"))
    assert s.display_updater.gezeigt["titel"] == "4711"
    assert s.display_updater.gezeigt["typ"] == Typ.VIDEO, "Filme/Live als Video melden"
    b.nachfuehren(_spielt("live:Das Erste", dauer=0))
    assert s.display_updater.gezeigt["titel"] == "Das Erste"
    # Metadaten NACH dem Start: wirken beim nächsten Abgleich.
    b.medien({"key": "live:Das Erste", "titel": "Das Erste HD", "interpret": "Live-TV",
              "album": "", "cover": "", "weiter": False, "zurueck": False})
    b.nachfuehren(_spielt("live:Das Erste", dauer=0))
    assert s.display_updater.gezeigt["titel"] == "Das Erste HD"
    assert s.display_updater.gezeigt["interpret"] == "Live-TV"
    assert not s.is_next_enabled and not s.is_previous_enabled


def test_weiter_zurueck_nur_mit_frischer_seite(ms, winrt_attrappe):
    # Vertrag Punkt 5: ⏭/⏮ nur frei, wenn das Metadaten-Flag es erlaubt UND
    # eine Seite /api/vlc in den letzten 3 s abgefragt hat — die Warteschlange
    # lebt in der Seite; ohne offene Seite kann niemand weiterschalten.
    uhr = [0.0]
    b = _sync(ms, uhr=lambda: uhr[0])
    b.medien({"key": "k|mp3", "titel": "T", "interpret": "", "album": "", "cover": "",
              "weiter": True, "zurueck": False})
    b.nachfuehren(_spielt("k|mp3"))
    s = winrt_attrappe.smtc
    assert not s.is_next_enabled and not s.is_previous_enabled, "ohne Seite nichts freigeben"
    b.seite_meldet()
    b.nachfuehren(_spielt("k|mp3"))
    assert s.is_next_enabled and not s.is_previous_enabled
    uhr[0] = 2.9
    b.nachfuehren(_spielt("k|mp3"))
    assert s.is_next_enabled
    uhr[0] = 3.5
    b.nachfuehren(_spielt("k|mp3"))
    assert not s.is_next_enabled, "Seite seit über 3 s still — Weiter muss gesperrt sein"
    b.seite_meldet()
    b.nachfuehren(_spielt("k|mp3"))
    assert s.is_next_enabled
    b.medien({"key": "k|mp3", "titel": "T", "interpret": "", "album": "", "cover": "",
              "weiter": True, "zurueck": True})
    b.nachfuehren(_spielt("k|mp3"))
    assert s.is_previous_enabled


def test_knopf_ereignisse_zaehler_und_befehle(ms, winrt_attrappe):
    # Vertrag Punkt 3+5: NEXT/PREVIOUS zählen nur hoch (die Seite schaltet) —
    # gesamt UND je Richtung (vor/zurueck, 24.09.2026: sonst wurden ⏭ und ein
    # schnell folgendes ⏮ beide in der letzten Richtung ausgeführt),
    # PLAY/PAUSE/STOP und Spulen gehen als Befehl an den Server.
    rufe = []
    b = _sync(ms, befehl=lambda was, wert=None: rufe.append((was, wert)))
    b.nachfuehren(_spielt())
    s = winrt_attrappe.smtc
    assert b.felder() == {"smtc": True, "taste": {"n": 0, "was": "", "vor": 0, "zurueck": 0}}
    s.druecken(Knopf.NEXT)
    assert rufe == [] and b.felder()["taste"] == {"n": 1, "was": "next", "vor": 1, "zurueck": 0}
    s.druecken(Knopf.PREVIOUS)
    assert rufe == [] and b.felder()["taste"] == {"n": 2, "was": "prev", "vor": 1, "zurueck": 1}
    s.druecken(Knopf.PLAY)
    s.druecken(Knopf.PAUSE)
    s.druecken(Knopf.STOP)
    s.druecken(Knopf.FAST_FORWARD)                 # nicht freigegeben -> ignorieren
    assert rufe == [("play", None), ("pause", None), ("pause", None)], \
        "STOP muss wie die Browser-Seite pausieren (Medium bleibt)"
    s.spulen(42.5)
    assert rufe[-1] == ("seek", 42.5)
    assert b.felder()["taste"]["n"] == 2


def test_knopf_ereignis_wartet_nie_auf_vlc(ms, winrt_attrappe):
    # Vertrag Punkt 6: Knöpfe kommen auf WinRT-Fäden an. Wartet der Rückruf auf
    # die VLC-Sperre, während ein Handler unter dieser Sperre die SMTC anfasst,
    # droht eine Verklemmung — der Rückruf muss sofort zurückkehren.
    frei, erledigt = threading.Event(), threading.Event()

    def befehl(was, wert=None):
        frei.wait(5)
        erledigt.set()
    b = ms.SmtcBruecke(port=8776, faden=False, nachlauf=0, befehl=befehl)
    b.nachfuehren(_spielt())
    t0 = time.monotonic()
    winrt_attrappe.smtc.druecken(Knopf.PAUSE)
    assert time.monotonic() - t0 < 0.5, "Knopf-Rückruf blockiert den WinRT-Faden"
    assert not erledigt.is_set()
    frei.set()
    assert erledigt.wait(3), "der Befehl muss trotzdem ausgeführt werden"


def test_arbeitsfaden_blockiert_keinen_handler(ms, winrt_attrappe, monkeypatch):
    # Vertrag Punkt 6: ein HTTP-Handler legt nur den Soll-Zustand ab. Selbst
    # wenn die Windows-Anmeldung hängt, kehrt nachfuehren sofort zurück.
    zaeh = threading.Event()
    interop = sys.modules["winrt.windows.media.interop"]
    echt = interop.get_for_window

    def langsam(hwnd):
        zaeh.wait(5)
        return echt(hwnd)
    monkeypatch.setattr(interop, "get_for_window", langsam)
    b = ms.SmtcBruecke(port=8776, nachlauf=0)       # Standard: eigener Arbeitsfaden
    t0 = time.monotonic()
    b.nachfuehren(_spielt())
    assert time.monotonic() - t0 < 0.3, "nachfuehren blockiert den Aufrufer"
    zaeh.set()
    ende = time.monotonic() + 3
    while time.monotonic() < ende and not (winrt_attrappe.smtc and winrt_attrappe.smtc.is_enabled):
        time.sleep(0.02)
    assert winrt_attrappe.smtc and winrt_attrappe.smtc.is_enabled, \
        "der Arbeitsfaden muss die Anmeldung nachholen"
    assert winrt_attrappe.faeden and winrt_attrappe.faeden[0] != threading.current_thread().name


def _warte(bedingung, zeit=3.0):
    ende = time.monotonic() + zeit
    while time.monotonic() < ende:
        if bedingung():
            return True
        time.sleep(0.02)
    return bool(bedingung())


def test_arbeitsfaden_prueft_fristen_selbst(ms, winrt_attrappe, monkeypatch):
    # Schließt JB die Seite, fragt niemand mehr /api/vlc — trotzdem müssen
    # ⏭/⏮ nach der Frische-Frist gesperrt werden (sonst schaltet ein Druck
    # ins Leere) und die Sitzung nach dem Nachlauf verschwinden. Das erledigt
    # der Arbeitsfaden selbst über seine Wartezeit, ohne eigenen Takt.
    # Das 'ende' reicht dieser Test der Brücke direkt; wie es OHNE Seite aus
    # libvlc ankommt, prüft test_liedende_ohne_seite_meldet_ab.
    monkeypatch.setattr(ms, "SEITE_FRISCH", 0.2)
    b = ms.SmtcBruecke(port=8776, nachlauf=0.2)
    b.medien({"key": "k|mp3", "titel": "T", "weiter": True, "zurueck": True})
    b.seite_meldet()
    b.nachfuehren(_spielt("k|mp3"))
    assert _warte(lambda: winrt_attrappe.smtc and winrt_attrappe.smtc.is_next_enabled)
    s = winrt_attrappe.smtc
    n = len(s.echte_zeitleisten())
    assert _warte(lambda: not s.is_next_enabled and not s.is_previous_enabled, 2), \
        "⏭/⏮ bleiben ohne offene Seite frei"
    assert len(s.echte_zeitleisten()) == n, \
        "die Selbst-Prüfung darf keine veraltete Position als Zeitleiste melden"
    b.nachfuehren(_spielt("k|mp3", zustand="ende"))
    assert _warte(lambda: s.is_enabled is False, 2), \
        "ohne weiteren Status bleibt die Sitzung nach dem Nachlauf stehen"


def test_fehlendes_winrt_kein_absturz(ms, monkeypatch):
    # Vertrag Punkt 1: fehlt pywinrt, gibt es keinen Absturz, EINEN Log-Eintrag
    # und verfuegbar=False — und es entsteht auch kein nutzloses Fenster.
    for name in WINRT_MODULE:
        monkeypatch.setitem(sys.modules, name, None)
    fenster = []
    monkeypatch.setattr(ms, "_fenster_bauen", lambda: fenster.append(1) or 4711)
    log = []
    b = _sync(ms, log=log.append)
    b.nachfuehren(_spielt())
    b.nachfuehren(_spielt(zustand="pause"))
    assert b.felder()["smtc"] is False and b.verfuegbar is False
    assert len(log) == 1, f"genau ein Log-Eintrag erwartet, bekam {log}"
    assert fenster == [], "ohne pywinrt darf kein Fenster entstehen"


def test_get_for_window_scheitert(ms, winrt_attrappe, monkeypatch):
    def kaputt(hwnd):
        winrt_attrappe.hwnds.append(hwnd)
        raise OSError("Klasse nicht registriert")
    monkeypatch.setattr(sys.modules["winrt.windows.media.interop"], "get_for_window", kaputt)
    log = []
    b = _sync(ms, log=log.append)
    b.nachfuehren(_spielt())
    b.nachfuehren(_spielt())
    assert b.felder()["smtc"] is False
    assert len(log) == 1 and "Klasse nicht registriert" in log[0]
    assert len(winrt_attrappe.hwnds) == 1, "nach dem Fehlschlag nicht im Takt neu versuchen"


def test_gescheiterte_abmeldung_wird_nachgeholt(ms, winrt_attrappe):
    # Scheitert is_enabled=False einmal (RPC-Wackler des Mediendienstes), darf
    # die Sitzung nicht für immer stehen bleiben: Ob Windows sie noch zeigt,
    # ist danach UNBEKANNT — also erneut abmelden, beim nächsten Abgleich und
    # ohne Seite durch den Arbeitsfaden selbst.
    log = []
    b = _sync(ms, log=log.append)
    b.nachfuehren(_spielt())
    s = winrt_attrappe.smtc
    s.abmelde_fehler = 1
    b.nachfuehren(_spielt(zustand="ende"))
    assert s.is_enabled is True and len(log) == 1, "der Wackler gehört einmal ins Protokoll"
    b.nachfuehren(_spielt(zustand="aus"))
    assert s.is_enabled is False, "nach einem gescheiterten Abmelden bleibt die Sitzung für immer"

    b2 = ms.SmtcBruecke(port=8776, nachlauf=0.1)   # Standard: eigener Arbeitsfaden
    b2.nachfuehren(_spielt())
    assert _warte(lambda: winrt_attrappe.smtc is not s and winrt_attrappe.smtc.is_enabled)
    s2 = winrt_attrappe.smtc
    s2.abmelde_fehler = 1
    b2.nachfuehren(_spielt(zustand="ende"))
    assert _warte(lambda: s2.abmelde_fehler == 0), "der erste Abmelde-Versuch kam nicht"
    assert _warte(lambda: s2.is_enabled is False, 2), \
        "ohne weiteren Status holt der Arbeitsfaden die Abmeldung nicht nach"


@pytest.mark.skipif(sys.platform != "win32", reason="echtes Win32-Fenster")
def test_fenster_antwortet_auch_wenn_ein_faden_den_gil_haelt(ms, monkeypatch):
    # get_for_window aus pywinrt gibt den GIL NICHT frei (gemessen 24.09.: das
    # Interop-.pyd importiert PyEval_SaveThread gar nicht). Schickt Windows
    # dem unsichtbaren Fenster währenddessen eine Nachricht und bräuchte die
    # Fensterprozedur dafür den GIL, stünde der GANZE Server. Nachgestellt mit
    # SendMessageTimeoutW über ctypes.PyDLL — PyDLL hält den GIL ebenso fest.
    # Nur ein unsichtbares Fenster, keine Windows-Medienanmeldung.
    import ctypes
    from ctypes import wintypes
    monkeypatch.setattr(ms, "_fenster", {"hwnd": 0, "proc": None})
    hwnd = ms._fenster_bauen()
    assert hwnd, "unsichtbares Fenster ließ sich nicht anlegen"
    mit_gil = ctypes.PyDLL("user32")
    senden = mit_gil.SendMessageTimeoutW
    senden.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                       wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t))
    senden.restype = ctypes.c_ssize_t
    u32 = ctypes.WinDLL("user32")
    u32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.c_void_p)
    u32.GetWindowThreadProcessId.restype = wintypes.DWORD
    u32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    u32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM)
    faden_id = u32.GetWindowThreadProcessId(hwnd, None)
    try:
        ergebnis = ctypes.c_size_t()
        t0 = time.monotonic()
        ok = senden(hwnd, 0x0000, 0, 0, 0x0000, 1000, ctypes.byref(ergebnis))   # WM_NULL, SMTO_NORMAL
        dauer = time.monotonic() - t0
        assert ok, (f"Fenster antwortet nicht, solange ein anderer Faden den GIL hält "
                    f"({dauer:.2f} s) — die Fensterprozedur braucht Python")
    finally:
        u32.PostMessageW(hwnd, 0x0010, 0, 0)            # WM_CLOSE -> DestroyWindow im Fensterfaden
        u32.PostThreadMessageW(faden_id, 0x0012, 0, 0)  # WM_QUIT -> Nachrichtenschleife endet


def test_modul_laedt_ohne_pywinrt(monkeypatch):
    # Lazy-Vertrag: das Modul selbst importiert pywinrt NICHT — sonst stürzte
    # der Server-Start ohne pywinrt (Quellstart mit eigenem Python) ab.
    for name in WINRT_MODULE:
        monkeypatch.setitem(sys.modules, name, None)
    spec = importlib.util.spec_from_file_location("medien_smtc_ohne_winrt", SMTC_PFAD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "SmtcBruecke")


# ---------------------------------------------------------------- Verdrahtung im Server

def test_jede_vlc_antwort_traegt_smtc_und_taste(monkeypatch, vlc_attrappe):
    # Vertrag Punkt 3: JEDE /api/vlc-Antwort — auch ohne Brücke (Tests, kein
    # main()), ohne Spieler und im Fehlerfall — trägt smtc + taste.
    monkeypatch.setattr(app, "_smtc", None)
    leer = {"n": 0, "was": "", "vor": 0, "zurueck": 0}
    st = app.vlc_kommando({"cmd": "status"})
    assert st["smtc"] is False and st["taste"] == leer
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    assert st["zustand"] == "spielt" and st["smtc"] is False and st["taste"] == leer
    st = app.vlc_kommando({"cmd": "play", "key": "gibtsnicht|mp3"})
    assert st.get("fehler") and "smtc" in st and "taste" in st
    assert "smtc" in app.vlc_status() and "taste" in app.vlc_status()
    monkeypatch.setitem(sys.modules, "vlc", None)
    app._vlc.update(instanz=None, spieler=None, key="")
    st = app.vlc_kommando({"cmd": "pruefen"})
    assert st["verfuegbar"] is False and st["smtc"] is False and st["taste"] == leer


def test_knoepfe_wirken_am_vlc(vlc_attrappe, bruecke, winrt_attrappe):
    # Vertrag Punkt 5 am ERGEBNIS: was kommt beim (nachgebauten) VLC an?
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    assert st["smtc"] is True
    s = winrt_attrappe.smtc
    assert s.is_enabled and s.playback_status == Status.PLAYING
    sp = app._vlc["spieler"]
    starts = sp.rufe.count(("play",))
    s.druecken(Knopf.PAUSE)
    assert sp.rufe[-1] == ("pause", 1) and s.playback_status == Status.PAUSED
    s.druecken(Knopf.PLAY)
    assert sp.rufe[-1] == ("pause", 0), "PLAY muss die Pause aufheben"
    assert s.playback_status == Status.PLAYING
    assert sp.rufe.count(("play",)) == starts, \
        "PLAY darf nicht cmd 'play' ohne key auslösen (scheitert mit 'Datei nicht gefunden')"
    s.druecken(Knopf.STOP)
    assert sp.rufe[-1] == ("pause", 1) and ("stop",) not in sp.rufe
    assert app._vlc["key"] == "abc|mp3" and s.is_enabled, "STOP pausiert nur, das Medium bleibt"
    n = len(sp.rufe)
    s.druecken(Knopf.NEXT)
    s.druecken(Knopf.PREVIOUS)
    assert len(sp.rufe) == n, "NEXT/PREVIOUS dürfen VLC nicht anfassen"
    st = app.vlc_kommando({"cmd": "status"})
    assert st["taste"] == {"n": 2, "was": "prev", "vor": 1, "zurueck": 1}
    s.spulen(42)
    assert sp.rufe[-1] == ("seek", 42000)
    assert s.echte_zeitleisten()[-1]["position"] == timedelta(seconds=42), \
        "nach dem Spulen aus Windows muss die Zeitleiste sofort stimmen"
    assert bruecke.log == []


def test_medien_befehl_und_rueckfall_im_server(vlc_attrappe, bruecke, winrt_attrappe):
    port = int(app.CFG.get("port", 8776))
    st = app.vlc_kommando({"cmd": "medien", "key": "abc|mp3", "titel": "Never Gonna Give You Up",
                           "interpret": "Rick Astley", "album": "Whenever You Need Somebody",
                           "cover": "/api/cover?id=abc%7Cmp3", "weiter": True, "zurueck": True})
    assert st["zustand"] == "aus" and st["smtc"] is True and "taste" in st
    assert app._vlc["spieler"] is None, "'medien' darf libvlc nicht nachladen (wie der Status-Takt)"
    assert winrt_attrappe.smtc is None, "Metadaten allein melden noch nichts an"
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    s = winrt_attrappe.smtc
    assert s.display_updater.gezeigt == {
        "typ": Typ.MUSIC, "titel": "Never Gonna Give You Up", "interpret": "Rick Astley",
        "album": "Whenever You Need Somebody",
        "cover": f"http://127.0.0.1:{port}/api/cover?id=abc%7Cmp3"}
    assert s.is_next_enabled and s.is_previous_enabled
    # Wechsel auf einen key ohne Metadaten: Bibliothekstitel, Cover leer.
    app.vlc_kommando({"cmd": "play", "key": "xyz|mp3"})
    assert s.display_updater.gezeigt["titel"] == "Zweites Lied"
    assert s.display_updater.gezeigt["interpret"] == "Kanal Zwei"
    assert s.display_updater.gezeigt["cover"] is None
    # Metadaten NACH dem play wirken sofort (die Antwort gleicht ab).
    app.vlc_kommando({"cmd": "medien", "key": "xyz|mp3", "titel": "Zweites Lied (Live)",
                      "interpret": "Band", "album": "", "cover": "",
                      "weiter": False, "zurueck": True})
    assert s.display_updater.gezeigt["titel"] == "Zweites Lied (Live)"
    assert not s.is_next_enabled and s.is_previous_enabled
    # Spulen von der Seite: Zeitleiste sofort, nicht erst im nächsten Takt.
    app.vlc_kommando({"cmd": "seek", "wert": 100})
    assert s.echte_zeitleisten()[-1]["position"] == timedelta(seconds=100)
    # Stop von der Seite (Gerät zurück auf Browser) meldet ab (nachlauf=0).
    app.vlc_kommando({"cmd": "stop"})
    assert s.is_enabled is False


def test_fehlendes_winrt_im_server(monkeypatch, vlc_attrappe, ms):
    # Vertrag Punkt 1+3 über den Server-Weg: kein Absturz, smtc:false.
    for name in WINRT_MODULE:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setattr(app, "_smtc", None)
    log = []
    app._smtc_einrichten(faden=False, ausfuehren=lambda f: f(), nachlauf=0, log=log.append)
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    assert st["zustand"] == "spielt", "der VLC-Motor muss ohne pywinrt normal spielen"
    assert st["smtc"] is False and st["taste"] == {"n": 0, "was": "", "vor": 0, "zurueck": 0}
    app.vlc_kommando({"cmd": "status"})
    assert len(log) == 1


def test_liedende_ohne_seite_meldet_ab(vlc_attrappe, bruecke, winrt_attrappe):
    # Vertrag Punkt 4 auch OHNE offene Seite: JB schließt Seite oder Hülle, VLC
    # spielt im Server weiter, das Lied endet. Dann fragt niemand mehr
    # /api/vlc — das Ende muss trotzdem bei Windows ankommen, sonst zeigt das
    # Overlay unbegrenzt „spielt" und fängt die Play/Pause-Taste ab.
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    s = winrt_attrappe.smtc
    assert s.is_enabled and s.playback_status == Status.PLAYING
    sp = app._vlc["spieler"]
    sp.ende().join(2)
    assert _warte(lambda: s.is_enabled is False, 2), \
        "Liedende ohne Seite: Windows zeigt die Sitzung weiter als laufend"
    # Die Selbstheilung baut libvlc neu auf — die Meldung muss am NEUEN Spieler hängen.
    app._vlc_reset()
    app.vlc_kommando({"cmd": "play", "key": "xyz|mp3"})
    assert _warte(lambda: s.is_enabled is True)
    sp2 = app._vlc["spieler"]
    assert sp2 is not sp
    sp2.ende().join(2)
    assert _warte(lambda: s.is_enabled is False, 2), "nach dem Neuaufbau fehlt die Ende-Meldung"


def test_vlc_ereignis_wartet_nie_auf_die_sperre(vlc_attrappe, bruecke, winrt_attrappe):
    # libvlc verbietet libvlc-Aufrufe im eigenen Ereignis-Faden. Und hält ein
    # Handler gerade _vlc_lock (etwa in sp.stop(), das auf diesen Faden
    # warten kann), verklemmte ein wartender Rückruf den Server. Der Rückruf
    # muss sofort zurückkehren; die Arbeit erledigt ein eigener kurzer Faden.
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    sp = app._vlc["spieler"]
    s = winrt_attrappe.smtc
    with app._vlc_lock:
        t = sp.ende()
        t.join(1.0)
        assert sp.ereignisse.rueckrufe.get("EndReached"), \
            "kein libvlc-Ereignis angehängt — das Ende käme ohne Seite nie an"
        assert not t.is_alive() and max(sp.ereignisse.dauer) < 0.5, \
            "der Ereignis-Rückruf wartet auf die VLC-Sperre"
        assert s.is_enabled is True
    assert _warte(lambda: s.is_enabled is False, 2)


def test_neustart_wartet_solange_vlc_spielt(monkeypatch, vlc_attrappe):
    # Der Selbst-Neustart bei neuem Code ersetzt den Prozess per os.execv —
    # samt libvlc und Windows-Sitzung. Beim Browser-Stream wartet er über
    # _letzter_stream; spielt der VLC-Motor, muss er genauso warten, auch
    # ohne offene Seite (dann setzt niemand _letzter_stream).
    monkeypatch.setattr(app, "_smtc", None)
    monkeypatch.setattr(app.Q, "items", [])
    monkeypatch.setattr(app, "_letzter_stream", 0.0)
    assert app._code_leerlauf() is True
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    assert app._code_leerlauf() is False, "startet mitten im VLC-Titel neu"
    app._vlc["spieler"].zustand = "B"
    assert app._code_leerlauf() is False, "startet neu, während VLC puffert"
    app.vlc_kommando({"cmd": "stop"})
    assert app._code_leerlauf() is True, "nach dem Stopp darf neu gestartet werden"
    # Hält gerade jemand die VLC-Sperre, arbeitet jemand am VLC: nicht neu
    # starten — und die 5-s-Schleife darf dabei nicht hängen bleiben.
    frei, gehalten = threading.Event(), threading.Event()

    def halter():
        with app._vlc_lock:
            gehalten.set()
            frei.wait(5)
    t = threading.Thread(target=halter, daemon=True)
    t.start()
    assert gehalten.wait(2)
    try:
        t0 = time.monotonic()
        assert app._code_leerlauf() is False
        assert time.monotonic() - t0 < 1.0, "die Neustart-Prüfung wartet auf die VLC-Sperre"
    finally:
        frei.set()
        t.join(2)


def test_windows_knopf_zeigt_sofort_das_gewollte(monkeypatch, vlc_attrappe, bruecke, winrt_attrappe):
    # libvlc schaltet asynchron: direkt nach set_pause meldet es noch den alten
    # Zustand. Ohne offene Seite käme kein weiterer Status — Windows muss nach
    # einem Knopf sofort das Gewollte zeigen.
    monkeypatch.setattr(vlc_attrappe.Spieler, "asynchron", True)
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    sp = app._vlc["spieler"]
    sp.takt()
    app.vlc_kommando({"cmd": "status"})
    s = winrt_attrappe.smtc
    assert s.playback_status == Status.PLAYING
    s.druecken(Knopf.PAUSE)
    assert sp.zustand == "P", "Attrappe: libvlc hat noch nicht umgeschaltet"
    assert s.playback_status == Status.PAUSED, "nach PAUSE zeigt Windows weiter „spielt“"
    sp.takt()
    s.druecken(Knopf.PLAY)
    assert sp.zustand == "p"
    assert s.playback_status == Status.PLAYING, "nach PLAY zeigt Windows weiter „pausiert“"


def test_spulen_zeigt_sofort_die_sollstelle(monkeypatch, vlc_attrappe, bruecke, winrt_attrappe):
    # Vertrag Punkt 4: Zeitleiste „sofort nach Spulen" — libvlc meldet die neue
    # Stelle aber erst später. Windows bekommt die gewünschte Stelle sofort,
    # egal ob die Seite oder Windows gespult hat.
    monkeypatch.setattr(vlc_attrappe.Spieler, "asynchron", True)
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    sp = app._vlc["spieler"]
    sp.takt()
    s = winrt_attrappe.smtc
    app.vlc_kommando({"cmd": "seek", "wert": 100})
    assert sp.zeit == 0, "Attrappe: libvlc hat noch nicht gespult"
    assert s.echte_zeitleisten()[-1]["position"] == timedelta(seconds=100), \
        "Spulen von der Seite: Windows zeigt die alte Stelle"
    s.spulen(42)
    assert s.echte_zeitleisten()[-1]["position"] == timedelta(seconds=42), \
        "Spulen aus Windows: Windows zeigt die alte Stelle"


def test_oeffnen_und_puffern_bleiben_angemeldet(monkeypatch, vlc_attrappe, bruecke, winrt_attrappe):
    # libvlc öffnet nach play zuerst (Opening) und puffert bei Strömen
    # zwischendurch (Buffering); vlc_status nennt beides 'aus'. Für Windows ist
    # das kein Ende: angemeldet, Status CHANGING — sonst verschwände die
    # Sitzung bei jedem Titelstart (nachlauf=0 hier: keine Gnadenfrist).
    monkeypatch.setattr(vlc_attrappe.Spieler, "asynchron", True)
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    assert st["zustand"] == "aus" and st["key"] == "abc|mp3", "Attrappe: libvlc öffnet noch"
    s = winrt_attrappe.smtc
    assert s is not None and s.is_enabled, "beim Öffnen muss die Sitzung schon stehen"
    assert s.playback_status == Status.CHANGING
    sp = app._vlc["spieler"]
    sp.takt()
    app.vlc_kommando({"cmd": "status"})
    assert s.playback_status == Status.PLAYING
    sp.zustand = "B"
    app.vlc_kommando({"cmd": "status"})
    assert s.is_enabled and s.playback_status == Status.CHANGING
    assert False not in s.an_verlauf, "Öffnen/Puffern darf nicht abmelden"


def test_fenster_befehl_zaehlt_nicht_als_seite(monkeypatch, vlc_attrappe, winrt_attrappe):
    # 'fenster' schickt die Hülle (Video-Einbettung), keine Seite mit
    # Warteschlange — es darf ⏭/⏮ nicht freigeben (Vertrag Punkt 5).
    monkeypatch.setattr(app, "_smtc", None)
    uhr = [0.0]
    app._smtc_einrichten(faden=False, ausfuehren=lambda f: f(), nachlauf=0, log=[].append,
                         uhr=lambda: uhr[0])
    app.vlc_kommando({"cmd": "medien", "key": "abc|mp3", "titel": "T",
                      "weiter": True, "zurueck": True})
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    s = winrt_attrappe.smtc
    assert s.is_next_enabled and s.is_previous_enabled
    uhr[0] = 10.0
    app.vlc_kommando({"cmd": "fenster", "hwnd": 0})
    assert not s.is_next_enabled and not s.is_previous_enabled, \
        "'fenster' der Hülle gibt ⏭/⏮ frei, obwohl keine Seite mehr fragt"


def test_smtc_wird_nur_in_main_angelegt():
    # Ein Import von youtube_app (Tests, Werkzeuge) darf nichts bei Windows
    # anmelden — die Brücke entsteht erst in main(), hinter dem Einzel-Instanz-
    # Riegel. Gezählt wird der AUFRUF im Syntaxbaum, nicht die Erwähnung: ein
    # auskommentiertes „# _smtc_einrichten()" ließe die Anmeldung still ausfallen.
    assert app._smtc is None
    baum = ast.parse(open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read())
    wo = set()
    for knoten in baum.body:
        for n in ast.walk(knoten):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "_smtc_einrichten"):
                wo.add(getattr(knoten, "name", "<Modulebene>"))
    assert wo == {"main"}, f"_smtc_einrichten() wird aufgerufen in {sorted(wo) or 'nirgends'}, " \
                           "erwartet: nur in main()"


# ---------------------------------------------------------------- Auslieferung

def _winrt_importe():
    """Auto-Discovery: welche winrt-Module importiert medien_smtc.py wirklich?"""
    baum = ast.parse(open(SMTC_PFAD, encoding="utf-8").read())
    genutzt = set()
    for n in ast.walk(baum):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("winrt"):
            genutzt.add(n.module)
        elif isinstance(n, ast.Import):
            genutzt |= {a.name for a in n.names if a.name.startswith("winrt")}
    assert genutzt, "Auto-Discovery findet keine winrt-Importe — der Wächter wäre blind"
    return genutzt


def test_exe_nimmt_pywinrt_mit(monkeypatch):
    # Die Bauvorschrift wird AUSGEFÜHRT (mit Attrappen für PyInstaller) und das
    # Ergebnis geprüft: jedes von medien_smtc genutzte winrt-Modul steht in den
    # hiddenimports (collect_all findet die tieferen Namespace-Ebenen nicht —
    # gemessen 23.09.), und collect_all('winrt') liefert .pyd + DLL.
    gesammelt = []

    def collect_all(name):
        gesammelt.append(name)
        return ([("daten-" + name, ".")], [("bin-" + name, ".")], ["hidden-" + name])
    hooks = types.ModuleType("PyInstaller.utils.hooks")
    hooks.collect_all = collect_all
    for name, mod in (("PyInstaller", types.ModuleType("PyInstaller")),
                      ("PyInstaller.utils", types.ModuleType("PyInstaller.utils")),
                      ("PyInstaller.utils.hooks", hooks)):
        monkeypatch.setitem(sys.modules, name, mod)
    analyse = {}

    def Analysis(skripte, **kw):
        analyse.update(kw)
        return types.SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
    g = {"__name__": "__spec__", "Analysis": Analysis,
         "PYZ": lambda *a, **k: None, "EXE": lambda *a, **k: None}
    spec = open(os.path.join(MODUL_DIR, "SyncYouTube.spec"), encoding="utf-8").read()
    exec(compile(spec, "SyncYouTube.spec", "exec"), g)
    assert "winrt" in gesammelt, "collect_all('winrt') fehlt — .pyd/msvcp140.dll kämen nicht mit"
    assert ("bin-winrt", ".") in analyse["binaries"]
    fehlend = sorted(m for m in _winrt_importe() | {"medien_smtc"}
                     if m not in analyse["hiddenimports"])
    assert not fehlend, f"in der exe fehlten: {fehlend}"


def test_readme_pip_zeile_nennt_pywinrt():
    # Start mit eigenem Python: JEDER README-Abschnitt, der pip-Befehle nennt
    # (Voraussetzungen, Quellstart — per Auto-Discovery, auch künftige), muss
    # python-vlc und jedes genutzte winrt-Paket nennen (Verteilungsname aus dem
    # Modulnamen: winrt.windows.media.interop -> winrt-Windows.Media.Interop).
    # Sonst fehlt auf diesem Weg die Windows-Anmeldung still.
    readme = open(os.path.join(MODUL_DIR, "..", "README.md"), encoding="utf-8").read()
    erwartet = {"python-vlc", "winrt-runtime"}
    for modul in _winrt_importe():
        teile = modul.split(".")[1:]
        erwartet.add(("winrt-" + ".".join(t.capitalize() for t in teile)).lower())
    geprueft = []
    for abschnitt in re.split(r"\n(?=#{2,3} )", readme):
        befehle = (re.findall(r"`(pip install [^`]*)`", abschnitt)
                   + re.findall(r"^\s*(pip install .*)$", abschnitt, re.M))
        if not befehle:
            continue
        titel = abschnitt.strip().splitlines()[0]
        geprueft.append(titel)
        pakete = {p.lower().strip('"') for b in befehle for p in b.split()}
        fehlend = sorted(erwartet - pakete)
        assert not fehlend, f"README-Abschnitt {titel!r}: pip-Befehle ohne {fehlend}"
    assert geprueft, "keine pip-Befehle in der README gefunden — der Wächter wäre blind"
