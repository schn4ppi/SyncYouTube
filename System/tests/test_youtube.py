# -*- coding: utf-8 -*-
"""Verhaltens-Sicherheitsnetz für den YouTube-Downloader.

Nagelt das aktuelle Verhalten der reinen (seiteneffektfreien) Funktionen fest,
BEVOR wir aufräumen/umbauen — genau wie in CLAUDE.md gefordert. Diese Tests
gehen NIE ins Netz und schreiben NICHTS auf die Platte; sie prüfen nur Logik.

Zwei Wege, es auszuführen:
    python tests/test_youtube.py      (ohne Zusatzpakete, druckt PASS/FAIL)
    pytest tests/                     (falls pytest installiert ist)
"""
import os
import sys
import time

# Modul-Ordner (YouTube/) auf den Pfad, damit geo/vpn/youtube_app importierbar sind.
MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import geo          # noqa: E402
import vpn          # noqa: E402
import youtube_app as app   # noqa: E402  (Import liest nur JBs JSONs, startet keinen Server)
import update       # noqa: E402  (Auto-Updater: reine Funktionen, kein Netz)


# ---------------------------------------------------------------- geo.py

def test_geo_fehler_erkennen():
    ja = ("The uploader has not made this video available in your country.")
    nein = "HTTP Error 403: Forbidden"
    assert geo.ist_geo_fehler(ja) is True
    assert geo.ist_geo_fehler(nein) is False
    assert geo.ist_geo_fehler("") is False
    assert geo.ist_geo_fehler(None) is False


def test_geo_laender_parsen():
    txt = ("This video is available in United Kingdom, Ireland, Guernsey and Jersey.")
    assert geo.laender_aus_fehler(txt) == ["United Kingdom", "Ireland", "Guernsey", "Jersey"]
    assert geo.laender_aus_fehler("kein Land hier") == []


def test_iso_codes():
    assert geo.iso("United Kingdom") == "GB"
    assert geo.iso("Germany") == "DE"
    assert geo.iso("Fantasialand") is None


def test_kandidaten_reihenfolge():
    # 0-Aufwand-Fall: keine eigenen/Gratis-Proxys, kein VPN eingerichtet ->
    # der Header-Trick fürs erste erlaubte Land muss der erste Versuch sein.
    cfg = {"geo_gratis_proxy": False, "geo_proxies": [], "geo_wireguard_ordner": ""}
    liste = geo.kandidaten(["United Kingdom", "Ireland"], cfg)
    assert liste, "mindestens der Header-Trick sollte entstehen"
    assert liste[0].opts.get("geo_bypass_country") == "GB"


# ---------------------------------------------------------------- vpn.py

def test_land_waehlen_bevorzugt_reihenfolge():
    # land_waehlen nimmt das erste passende Land in vpn.LAENDER-Reihenfolge.
    assert vpn.land_waehlen(["Ireland", "United Kingdom"]) == "United Kingdom"
    assert vpn.land_waehlen(["Fantasia"]) is None


# ---------------------------------------------------------------- youtube_app.py

def test_video_id():
    assert app._video_id("https://www.youtube.com/watch?v=jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert app._video_id("https://youtu.be/jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert app._video_id("https://www.youtube.com/watch?v=abc123&list=PL9") == "abc123"


def test_geladen_key():
    assert app._geladen_key("https://youtu.be/abcdef", "audio") == "abcdef|audio"


def test_ist_einzelvideo():
    # watch?v=…&list=… -> DIESES Video (True); reine /playlist -> ganze Liste (False)
    assert app.ist_einzelvideo("https://www.youtube.com/watch?v=abc&list=PL1") is True
    assert app.ist_einzelvideo("https://www.youtube.com/playlist?list=PL1") is False


def test_kanal_url_normalisieren():
    # bloße Kanal-Formen bekommen /videos angehängt (sonst nur Reiter statt Videos)
    assert app._kanal_url("https://www.youtube.com/@MrBeast") == "https://www.youtube.com/@MrBeast/videos"
    assert app._kanal_url("https://www.youtube.com/channel/UC123") == "https://www.youtube.com/channel/UC123/videos"
    assert app._kanal_url("https://www.youtube.com/c/Name/") == "https://www.youtube.com/c/Name/videos"
    assert app._kanal_url("https://www.youtube.com/user/Name") == "https://www.youtube.com/user/Name/videos"
    # bereits /videos, Playlists, Watch-Links und Fremd-Hosts bleiben unveraendert
    assert app._kanal_url("https://www.youtube.com/@MrBeast/videos") == "https://www.youtube.com/@MrBeast/videos"
    assert app._kanal_url("https://www.youtube.com/playlist?list=PL1") == "https://www.youtube.com/playlist?list=PL1"
    assert app._kanal_url("https://www.youtube.com/watch?v=abc") == "https://www.youtube.com/watch?v=abc"
    assert app._kanal_url("https://example.com/@foo") == "https://example.com/@foo"


def test_kategorie():
    assert app._kategorie("audio", 0) == "MP3"
    assert app._kategorie("beste", 2160) == "4K+"
    assert app._kategorie("beste", 1080) == "Video"


def test_titel_und_kategorie_aus_name():
    assert app._titel_aus_name("Me at the zoo [jNQXAC9IVRw].mp4") == "Me at the zoo"
    assert app._kat_aus_name("song.mp3") == "MP3"
    assert app._kat_aus_name("clip.mp4") == "Video"


def test_plausible_id():
    assert app._plausible_id("jNQXAC9IVRw") is True
    assert app._plausible_id("x") is False


def test_sponsorblock_kategorien():
    assert app.sponsorblock_kategorien("") == []
    assert app.sponsorblock_kategorien("sponsor") == ["sponsor"]
    assert "sponsor" in app.sponsorblock_kategorien("alle")
    assert "intro" in app.sponsorblock_kategorien("alle")


def test_zeit_sekunden():
    assert app._zeit_sekunden("83") == 83
    assert app._zeit_sekunden("1:23") == 83
    assert app._zeit_sekunden("1:02:03") == 3723
    assert app._zeit_sekunden("") is None
    assert app._zeit_sekunden("quatsch") is None


def test_tag_kandidat():
    # 'Künstler - Titel [Müll]' -> sauber getrennt, Müll-Klammern weg
    e = {"titel": "Green Day - Boulevard Of Broken Dreams [Official Music Video] [4K Upgrade]",
         "uploader": "GreenDayVEVO"}
    ku, ti = app._tag_kandidat(e)
    assert ku == "Green Day"
    assert ti == "Boulevard Of Broken Dreams"
    # kein ' - ' im Titel -> Kanalname (ohne '- Topic'-Zusatz) als Künstler
    e2 = {"titel": "Some Song (Lyrics)", "uploader": "Artist - Topic"}
    ku2, ti2 = app._tag_kandidat(e2)
    assert ku2 == "Artist"
    assert ti2 == "Some Song"


def test_romaji():
    vtt = ("WEBVTT\nKind: captions\n\n00:00:01.000 --> 00:00:03.000\n"
           "残酷な天使のテーゼ\n\n00:00:03.000 --> 00:00:05.000\nHello World")
    out = app._romaji(vtt)
    assert "zankoku" in out and "tenshi" in out       # Kanji/Kana -> Hepburn
    assert "-->" in out and "WEBVTT" in out           # Zeitstempel/Kopf unangetastet
    assert "Hello World" in out                       # Latein bleibt


def test_vtt_sprache():
    assert app._vtt_sprache("C:/x/Song [abc123].ja-orig.vtt") == "ja-orig"
    assert app._vtt_sprache("C:/x/Song [abc123].de.vtt") == "de"
    assert app._vtt_sprache("C:/x/Song [abc123].mp3") == ""


def test_artist_passt():
    rec_abba = {"artist-credit": [{"name": "ABBA"}]}
    rec_esque = {"artist-credit": [{"name": "ABBA-Esque"}]}
    assert app._artist_passt(rec_abba, "ABBA") is True
    assert app._artist_passt(rec_esque, "ABBA") is False      # Coverband abgelehnt
    assert app._artist_passt(rec_abba, "") is True            # kein Kandidat = kein Wächter


def test_ist_musik():
    assert app._ist_musik({"kategorie": "MP3", "name": "a.mp3"}) is True
    assert app._ist_musik({"kategorie": "Video", "name": "a.m4a"}) is True
    assert app._ist_musik({"kategorie": "Video", "name": "a.mp4"}) is False


def test_zugriff_erlaubt():
    # localhost darf IMMER (egal ob Fernsteuerung an/aus)
    assert app.zugriff_erlaubt("127.0.0.1", False, "", "") is True
    assert app.zugriff_erlaubt("::1", False, "ABC123", "") is True
    # LAN: aus -> nie
    assert app.zugriff_erlaubt("192.168.0.5", False, "ABC123", "ABC123") is False
    # LAN: an, aber Code falsch/fehlt -> nein
    assert app.zugriff_erlaubt("192.168.0.5", True, "ABC123", "") is False
    assert app.zugriff_erlaubt("192.168.0.5", True, "ABC123", "XXX") is False
    # LAN: an + richtiger Code -> ja
    assert app.zugriff_erlaubt("192.168.0.5", True, "ABC123", "ABC123") is True
    # an, aber gar kein Code gesetzt -> nein (kein Blank-Zugriff)
    assert app.zugriff_erlaubt("192.168.0.5", True, "", "") is False


def test_update_versionen():
    # JBs Tag-Stil v.x.y.z MIT Punkt muss immer richtig gelesen werden
    assert update.parse_version("v.1.0.1") == (1, 0, 1)
    assert update.parse_version("v1.2.3") == (1, 2, 3)
    assert update.parse_version("1.2") == (1, 2)
    assert update.is_newer("v.1.1.0", "1.0.1") is True
    assert update.is_newer("v.1.0.1", "1.0.1") is False
    assert update.is_newer("1.0.0", "1.0.1") is False


def test_update_assets_repo_pin():
    # Nur Assets aus dem EIGENEN Repo zaehlen — fremde URLs werden ignoriert
    gut = {"name": "SyncYouTube.exe",
           "browser_download_url": "https://github.com/schn4ppi/SyncYouTube/releases/download/v.1.1.0/SyncYouTube.exe"}
    sha = {"name": "SyncYouTube.exe.sha256",
           "browser_download_url": "https://github.com/schn4ppi/SyncYouTube/releases/download/v.1.1.0/SyncYouTube.exe.sha256"}
    boese = {"name": "SyncYouTube.exe", "browser_download_url": "https://evil.example/SyncYouTube.exe"}
    exe, sh = update.pick_assets([boese, gut, sha])
    assert exe is gut and sh is sha
    exe2, _ = update.pick_assets([boese])
    assert exe2 is None


def test_update_verify():
    import hashlib
    daten = b"x" * update.MIN_EXE_SIZE
    assert update.verify_exe(b"kurz")[0] is False                      # zu klein
    assert update.verify_exe(daten, expected_size=1)[0] is False       # Groesse falsch
    assert update.verify_exe(daten, expected_sha="0" * 64)[0] is False # SHA falsch
    ok, _ = update.verify_exe(daten, len(daten), hashlib.sha256(daten).hexdigest())
    assert ok is True
    assert update.parse_sha256("abc " + "f" * 64 + "  SyncYouTube.exe") == "f" * 64


def test_update_check_release():
    rel = {"tag_name": "v.9.9.9", "assets": [
        {"name": "SyncYouTube.exe",
         "browser_download_url": "https://github.com/schn4ppi/SyncYouTube/releases/download/v.9.9.9/SyncYouTube.exe",
         "size": 123}]}
    info = update.check_release("1.1.0", fetch_json=lambda: rel)
    assert info["available"] is True and info["version"] == "9.9.9" and info["size"] == 123
    info2 = update.check_release("9.9.9", fetch_json=lambda: rel)
    assert info2["available"] is False
    info3 = update.check_release("1.0.0", fetch_json=lambda: (_ for _ in ()).throw(OSError("offline")))
    assert info3["available"] is False                                 # offline = kein Fehler


def test_datei_aus():
    # |beste-Key darf NIE die MP3 bekommen (Bild blieb schwarz), |audio nie das Video
    beide = [r"C:\x\MP3\Song [id123456].mp3", r"C:\x\Video\Song [id123456].mp4"]
    assert app._datei_aus(beide, "beste").endswith(".mp4")
    assert app._datei_aus(beide, "audio").endswith(".mp3")
    assert app._datei_aus([beide[0]], "beste").endswith(".mp3")   # nur Audio da -> besser als nichts
    assert app._datei_aus([], "beste") is None
    assert app._datei_aus(None, "audio") is None


def test_soll_kategorie():
    # Einsortier-Selbstheilung (JB 14.07.): Audio-Endung reicht für MP3;
    # Nicht-Medien werden NIE angefasst ('' = tabu); unbekanntes Video ohne
    # DB-Treffer/ffprobe-Datei bleibt unklar (None -> Ordner "Sonstiges").
    assert app._soll_kategorie(r"C:\x\Song [abc123def45].mp3") == "MP3"
    assert app._soll_kategorie("egal.opus") == "MP3"
    assert app._soll_kategorie("notizen.txt") == ""
    assert app._soll_kategorie("_worklist.md") == ""
    assert app._soll_kategorie("unbekanntes-video-ohne-id.mp4") is None
    # Höhe aus der geladen-DB: 2160p -> 4K+, darunter -> Video
    app._geladen["testvid9999|beste"] = {"name": "T [testvid9999].mp4", "hoehe": 2160}
    try:
        assert app._soll_kategorie("T [testvid9999].mp4") == "4K+"
        app._geladen["testvid9999|beste"]["hoehe"] = 1080
        assert app._soll_kategorie("T [testvid9999].mp4") == "Video"
    finally:
        del app._geladen["testvid9999|beste"]      # JBs echte DB nicht anfassen


def test_abo_feed_url():
    # RSS-Puls (Pinchflat-Muster): Feed-URL aus Kanal-/Playlist-Info ableiten
    assert app._abo_feed_url({"channel_id": "UCabc123"}).endswith("channel_id=UCabc123")
    assert app._abo_feed_url({"id": "PLxyz"}).endswith("playlist_id=PLxyz")
    assert app._abo_feed_url({"id": "@handle"}) == ""
    assert app._abo_feed_url({}) == ""


def test_abo_rss_ids():
    # IDs aus dem Feed-XML; Netzfehler -> None (dann übernimmt der Voll-Weg)
    xml = ("<feed><entry><yt:videoId>abc123XYZ_-</yt:videoId></entry>"
           "<entry><yt:videoId>def456ghi78</yt:videoId></entry></feed>")

    class _Antwort:
        def read(self):
            return xml.encode()

    echt = app.urllib.request.urlopen
    try:
        app.urllib.request.urlopen = lambda *a, **k: _Antwort()
        assert app._abo_rss_ids("https://x") == ["abc123XYZ_-", "def456ghi78"]

        def kaputt(*a, **k):
            raise OSError("Netz weg")
        app.urllib.request.urlopen = kaputt
        assert app._abo_rss_ids("https://x") is None
    finally:
        app.urllib.request.urlopen = echt


def test_vtt_cues_und_suche(tmp_path=None):
    # Transkript-Volltextsuche (JB 21.07.): VTT parsen (Tags/Entities raus,
    # rollende Dubletten zusammen), Begriff case-insensitiv finden.
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "clip.en.vtt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n"
                "Hello <c>there</c> &amp; welcome\n\n"
                "00:00:03.000 --> 00:00:05.000\nHello there &amp; welcome\n\n"
                "00:00:07.500 --> 00:00:09.000\nThe SECRET word is banana\n")
    cues = app._vtt_cues(p)
    assert cues[0] == (1.0, "Hello there & welcome")           # Tags weg, &amp; -> &
    assert len(cues) == 2                                       # rollende Dublette zusammengefasst
    assert cues[1][0] == 7.5 and "banana" in cues[1][1]

    echt = app.untertitel_datei
    app.untertitel_datei = lambda k: (p, "en") if k == "clipKEY" else (None, "")
    app._geladen["clipKEY"] = {"titel": "Clip"}
    try:
        tr = app.transkript_suche("BANANA")                    # case-insensitiv
        assert tr and tr[0]["key"] == "clipKEY"
        assert tr[0]["treffer"][0]["zeit"] == 7.5
        assert app.transkript_suche("x") == []                 # <2 Zeichen
        assert app.transkript_suche("gibtsnicht") == []
    finally:
        app.untertitel_datei = echt
        app._geladen.pop("clipKEY", None)


def test_lrc_cues():
    # LRCLIB-Text -> (zeit, text) für die Transkript-Suche (Build 68).
    cues = app._lrc_cues("[ar:X]\n[00:01.50] erste Zeile\n[00:04.00] zweite Zeile\n\n[00:06.00]")
    assert cues[0] == (1.5, "erste Zeile")
    assert cues[1] == (4.0, "zweite Zeile")
    assert len(cues) == 2                              # Meta-Zeile + leere Marke fallen weg


def test_lyrics_holen():
    # LRCLIB-Lyrics (JB 21.07.): Künstler+Titel -> synced LRC, gecacht; ohne
    # Künstler/Titel gar keine Abfrage. Netz wird gemockt, Cache stillgelegt.
    echt_get, echt_json = app._lrclib_get, app._json_speichern
    app._json_speichern = lambda *a, **k: None
    app._lyrics.clear()
    app._geladen["lyrTEST|audio"] = {"kuenstler": "Michael Jackson", "titel": "Rockin' Robin", "dauer": 165}
    app._geladen["lyrLEER|audio"] = {"titel": "Ohne Kuenstler"}
    rufe = []
    try:
        app._lrclib_get = lambda a, t, al, d: rufe.append((a, t)) or "[00:01.00] la la"
        assert app.lyrics_holen("lyrTEST|audio") == "[00:01.00] la la"
        assert app.lyrics_holen("lyrTEST|audio") == "[00:01.00] la la"   # 2. Mal: Cache
        assert len(rufe) == 1                                            # nur EINMAL wirklich gefragt
        assert app.lyrics_holen("lyrLEER|audio") == ""                   # kein Künstler -> keine Abfrage
        assert len(rufe) == 1
    finally:
        app._lrclib_get, app._json_speichern = echt_get, echt_json
        app._lyrics.clear()
        app._geladen.pop("lyrTEST|audio", None)
        app._geladen.pop("lyrLEER|audio", None)


def test_abo_nr():
    # CD-Muster (JB 21.07.): Folgen-Liste ist neueste-zuerst -> älteste = 1,
    # neueste = Gesamtzahl. Nicht im Cache -> 0.
    import json
    import tempfile
    d = tempfile.mkdtemp()
    alt = app.ABO_INDEX_ORDNER
    app.ABO_INDEX_ORDNER = d
    try:
        folgen = [{"id": "vNEU"}, {"id": "vMITTE"}, {"id": "vALT"}]
        with open(os.path.join(d, "abo1.json"), "w", encoding="utf-8") as f:
            json.dump({"folgen": folgen}, f)
        assert app._abo_nr("abo1", "vNEU") == 3
        assert app._abo_nr("abo1", "vMITTE") == 2
        assert app._abo_nr("abo1", "vALT") == 1
        assert app._abo_nr("abo1", "xxx") == 0
        assert app._abo_nr("fehlt", "vNEU") == 0
    finally:
        app.ABO_INDEX_ORDNER = alt


def test_abo_regel_ok():
    # Opt-in-Regeln je Abo: Shorts/Streams/Stichtag/Titel-Filter; fehlt ein
    # Datenfeld, greift die Regel NICHT (lieber laden als still verlieren).
    abo = {"filter_titel": "", "ohne_shorts": True, "ohne_streams": True, "ab_datum": "2026-01-01"}
    assert app._abo_regel_ok(abo, {"title": "x", "duration": 30}) is False
    assert app._abo_regel_ok(abo, {"title": "x", "live_status": "is_live"}) is False
    assert app._abo_regel_ok(abo, {"title": "x", "upload_date": "20250101"}) is False
    assert app._abo_regel_ok(abo, {"title": "x", "duration": 600, "upload_date": "20260315"}) is True
    assert app._abo_regel_ok(abo, {"title": "x", "duration": 600}) is True
    assert app._abo_regel_ok({"filter_titel": "Folge"}, {"title": "Podcast Folge 12"}) is True
    assert app._abo_regel_ok({"filter_titel": "Folge"}, {"title": "Trailer"}) is False


def test_abo_playlist_zuordnen():
    # Fertiger Abo-Download -> eigene Abo-Playlist (anlegen, nie doppelt).
    # Speichern wird stillgelegt, damit JBs echte JSON-Dateien unberührt bleiben.
    def still(*a, **k):
        return None
    echt_json, echt_pl = app._json_speichern, app._playlists_speichern
    app._json_speichern, app._playlists_speichern = still, still
    app._abos.append({"id": "aboTEST", "name": "TestKanal", "qualitaet": "audio"})
    app._geladen["vidTEST9999|audio"] = {"name": "t.mp3"}
    try:
        app._abo_playlist_zuordnen("aboTEST", "vidTEST9999|audio")
        pl = next(p for p in app._playlists if p.get("name") == "TestKanal")
        assert pl["items"] == ["vidTEST9999|audio"]
        app._abo_playlist_zuordnen("aboTEST", "vidTEST9999|audio")
        assert pl["items"] == ["vidTEST9999|audio"]      # nicht doppelt
        assert next(a for a in app._abos if a["id"] == "aboTEST")["playlist_id"] == pl["id"]
    finally:
        app._json_speichern, app._playlists_speichern = echt_json, echt_pl
        app._playlists[:] = [p for p in app._playlists if p.get("name") != "TestKanal"]
        app._abos[:] = [a for a in app._abos if a.get("id") != "aboTEST"]
        app._geladen.pop("vidTEST9999|audio", None)


def test_abo_create_normalisiert_kanal_url():
    # Build 91 (JB-Fund): Abo auf blossen Kanal-Link (/@name, /channel/UC…)
    # muss auf /videos normalisiert werden — sonst merkt sich die Baseline
    # nur die Kanal-REITER („#1 Shorts / #2 Videos" statt Folgen).
    rufe = []

    def fake_flach(url, limit=60):
        rufe.append(url)
        return {"title": "TestKanal - Videos", "channel_id": "UCtest",
                "entries": [{"id": "vid00000001"}, {"id": "vid00000002"}]}

    echt_flach, echt_json = app._abo_flach, app._json_speichern
    app._abo_flach, app._json_speichern = fake_flach, lambda *a, **k: None
    try:
        r = app.abo_aktion({"art": "create", "url": "https://www.youtube.com/@TestKanal"})
        assert r.get("ok") and r["basis"] == 2
        assert rufe == ["https://www.youtube.com/@TestKanal/videos"]
        abo = next(a for a in app._abos if a["id"] == r["id"])
        assert abo["url"] == "https://www.youtube.com/@TestKanal/videos"
        assert abo["name"] == "TestKanal"              # Tab-Suffix „ - Videos" weg
        assert abo["bekannt"] == ["vid00000001", "vid00000002"]
    finally:
        app._abo_flach, app._json_speichern = echt_flach, echt_json
        app._abos[:] = [a for a in app._abos if a.get("name") != "TestKanal"]


def test_mix_erkennen_und_limit():
    # Build 98 (JB): YouTube-Mixe (Radio, list=RD…) sind endlos + nicht-
    # deterministisch (JB mass 1877 vs 563 Titel fuer denselben Mix) —
    # die Anzahl ist ab jetzt WAEHLBAR (1..500, Default 50), nie „alle".
    assert app._ist_mix("https://www.youtube.com/watch?v=a&list=RDa") is True
    assert app._ist_mix("https://www.youtube.com/watch?v=a&list=RDCLAK5uy_x") is True
    assert app._ist_mix("https://www.youtube.com/watch?v=a&list=PLnormal") is False
    assert app._ist_mix("https://www.youtube.com/playlist?list=PL1") is False
    assert app._mix_limit(None) == 50                  # Default wie bisher
    assert app._mix_limit(25) == 25
    assert app._mix_limit("100") == 100
    assert app._mix_limit(0) == 50                     # Unsinn -> Default
    assert app._mix_limit(9999) == 500                 # Deckel gegen Endlos-Radio
    assert app._mix_limit("quatsch") == 50


def test_kanal_info_mix_mit_limit():
    # Build 98: kanal_info loest Mixe nur bis zum Wunsch-Limit auf (schnell,
    # keine 20-s-Sanduhr fuer 1800 Titel) und meldet mix:true fuers Frontend.
    rufe = []

    def fake_flach(url, limit=60):
        rufe.append(limit)
        return {"title": "Mix - Test", "id": "RDabc",
                "entries": [{"id": f"v{i:010d}"} for i in range(min(limit, 25))]}

    echt = app._abo_flach
    app._abo_flach = fake_flach
    try:
        d = app.kanal_info("https://www.youtube.com/watch?v=abc&list=RDabc", limit=25)
        assert d.get("ok") and d.get("mix") is True and d["anzahl"] == 25
        assert rufe == [25]
        d2 = app.kanal_info("https://www.youtube.com/playlist?list=PL1")
        assert d2.get("mix") is False and rufe[-1] == 5000   # Nicht-Mix wie bisher
    finally:
        app._abo_flach = echt


def test_addon_hab():
    # Build 98 (JB): das Addon fragt, ob ein Video schon in der Bibliothek
    # ist (Hover-Knopf wird gruen). Reine Key-Suche, kein Netz.
    app._geladen["vidHAB00001|audio"] = {"name": "t.mp3"}
    app._geladen["vidHAB00001|beste"] = {"name": "t.mp4"}
    try:
        d = app.addon_hab("vidHAB00001")
        assert d["da"] is True and sorted(d["formate"]) == ["audio", "beste"]
        assert app.addon_hab("gibtsnich123") == {"da": False, "formate": []}
        assert app.addon_hab("") == {"da": False, "formate": []}
    finally:
        app._geladen.pop("vidHAB00001|audio", None)
        app._geladen.pop("vidHAB00001|beste", None)


def test_playlist_einreihen():
    # Build 100 (JB): Entdecker-Downloads sammeln sich automatisch in einer
    # benannten Playlist („✨ Entdeckt 23.07.") — anlegen falls neu, nie doppelt.
    still = lambda *a, **k: None                       # noqa: E731
    echt_pl, echt_json = app._playlists_speichern, app._json_speichern
    app._playlists_speichern, app._json_speichern = still, still
    app._geladen["vidENT00001|audio"] = {"name": "e.mp3"}
    try:
        app._playlist_einreihen("✨ Entdeckt 23.07.", "vidENT00001|audio")
        pl = next(p for p in app._playlists if p.get("name") == "✨ Entdeckt 23.07.")
        assert pl["items"] == ["vidENT00001|audio"]
        app._playlist_einreihen("✨ Entdeckt 23.07.", "vidENT00001|audio")
        assert pl["items"] == ["vidENT00001|audio"]    # nicht doppelt
        app._playlist_einreihen("", "vidENT00001|audio")           # kein Name -> no-op
        app._playlist_einreihen("✨ Entdeckt 23.07.", "fremd|audio")  # nicht geladen -> no-op
        assert pl["items"] == ["vidENT00001|audio"]
    finally:
        app._playlists_speichern, app._json_speichern = echt_pl, echt_json
        app._playlists[:] = [p for p in app._playlists if p.get("name") != "✨ Entdeckt 23.07."]
        app._geladen.pop("vidENT00001|audio", None)


def test_entdecken_bibliothek():
    # Build 106 (JB): ✨ ohne gewählte Playlist = die GANZE Bibliothek als
    # Quelle. Seeds gewichtet nach plays (was JB wirklich hört), max 1 Seed
    # je Künstler (Vielfalt); Import-Dateien ohne echte YouTube-Id fallen raus.
    def fake_flach(url, limit=60):
        return {"entries": [{"id": "neuFund0001", "title": "Neu", "duration": 100}]}

    echt = app._abo_flach
    app._abo_flach = fake_flach
    app._geladen["vielGSPLT01|audio"] = {"name": "a.mp3", "plays": 50, "kuenstler": "Kate Bush"}
    app._geladen["vielGSPLT02|audio"] = {"name": "b.mp3", "plays": 40, "kuenstler": "Kate Bush"}
    app._geladen["andereBand1|audio"] = {"name": "c.mp3", "plays": 30, "kuenstler": "Survivor"}
    app._geladen["lokal-abcdef12345|lokal"] = {"name": "fremd.mp4", "importiert": True}
    try:
        d = app.entdecken("", seeds=2, je_seed=5)      # leer = Bibliothek
        assert d.get("ok") and d["seeds"] == 2
        assert [f["id"] for f in d["funde"]] == ["neuFund0001"]
        # Künstler-Dedupe: die 2 Seeds dürfen nicht beide Kate Bush sein
        assert d.get("quelle") == "bibliothek"
    finally:
        app._abo_flach = echt
        for k in ("vielGSPLT01|audio", "vielGSPLT02|audio", "andereBand1|audio",
                  "lokal-abcdef12345|lokal"):
            app._geladen.pop(k, None)


def test_datei_fp():
    # Bibliothek 2.0, Etappe 1 (JB-Go): Content-Fingerabdruck (JBs „Magnet"-
    # Idee) — sha1 ueber erste + letzte 64 KB + Groesse (OpenSubtitles-Stil).
    # Erkennt eine Datei am INHALT: Umbenennen aendert nichts, Inhalt schon.
    import tempfile
    d = tempfile.mkdtemp()
    p1 = os.path.join(d, "Song [abc123def45].mp3")
    with open(p1, "wb") as f:
        f.write(b"A" * 200000)                         # 200 KB
    fp1 = app._datei_fp(p1)
    assert fp1 and len(fp1) == 40                      # sha1-Hex
    p2 = os.path.join(d, "Song ohne Klammern.mp3")     # UMBENANNT -> gleicher fp
    os.rename(p1, p2)
    assert app._datei_fp(p2) == fp1
    with open(p2, "ab") as f:                          # Inhalt geaendert -> anderer fp
        f.write(b"B")
    assert app._datei_fp(p2) != fp1
    klein = os.path.join(d, "mini.mp3")                # kleiner als 128 KB
    with open(klein, "wb") as f:
        f.write(b"x" * 1000)
    assert len(app._datei_fp(klein)) == 40
    assert app._datei_fp(os.path.join(d, "fehlt.mp3")) == ""   # weg -> leer, kein Crash


def test_mb_pro_min():
    # Build 105 (JB: „wie viel lade ich ungefähr?"): Groessen-Schaetzung aus
    # den ECHTEN eigenen Downloads (Median MB/min je Qualitaet); zu wenig
    # Datenpunkte -> ehrliche Erfahrungs-Fallbacks.
    for i, (g, d) in enumerate([(30e6, 180), (40e6, 240), (35e6, 200),
                                (50e6, 300), (28e6, 170)]):
        app._geladen[f"mbtest{i:05d}|audio"] = {"groesse": g, "dauer": d, "qualitaet": "audio"}
    try:
        f = app._mb_pro_min("audio")
        assert 8 <= f <= 12                            # ~10 MB/min aus den Fixtures
        assert app._mb_pro_min("2160p") == 60          # keine Daten -> Fallback
        assert app._mb_pro_min("unbekannt") == 25      # unbekannte Qualitaet -> beste-Fallback
    finally:
        for i in range(5):
            app._geladen.pop(f"mbtest{i:05d}|audio", None)


def test_entdecken():
    # Build 99 (JB): „📻 Neues entdecken" — Radio-Mixe zu Playlist-Titeln
    # aufloesen, ALLES Bekannte (Bibliothek + Seeds) rausfiltern; Titel, die
    # in MEHREREN Seed-Mixen auftauchen, zuerst (staerkstes Signal).
    rufe = []

    def fake_flach(url, limit=60):
        rufe.append(url)
        sid = url.split("v=")[1].split("&")[0]
        gemeinsam = {"id": "neuBEIDE001", "title": "Ueberall", "duration": 200}
        if sid == "seedA000001":
            return {"entries": [gemeinsam,
                                {"id": "seedA000001", "title": "der Seed selbst"},
                                {"id": "altGELADEN1", "title": "kenn ich schon"},
                                {"id": "neuNURA0001", "title": "Nur in A", "duration": 100}]}
        return {"entries": [gemeinsam,
                            {"id": "neuNURB0001", "title": "Nur in B", "duration": 150}]}

    echt_flach = app._abo_flach
    app._abo_flach = fake_flach
    app._playlists.append({"id": "plENT", "name": "Entdecker-Test",
                           "items": ["seedA000001|audio", "seedB000001|audio"]})
    app._geladen["seedA000001|audio"] = {"name": "a.mp3"}
    app._geladen["seedB000001|audio"] = {"name": "b.mp3"}
    app._geladen["altGELADEN1|beste"] = {"name": "alt.mp4"}
    try:
        d = app.entdecken("plENT", seeds=2, je_seed=25)
        assert d.get("ok") and d["seeds"] == 2 and len(rufe) == 2
        ids = [f["id"] for f in d["funde"]]
        assert ids[0] == "neuBEIDE001"                 # Score 2 zuerst
        assert d["funde"][0]["score"] == 2
        assert set(ids) == {"neuBEIDE001", "neuNURA0001", "neuNURB0001"}
        assert "altGELADEN1" not in ids                # Bibliothek gefiltert
        assert "seedA000001" not in ids                # Seeds gefiltert
        leer = app.entdecken("gibtsnicht")
        assert leer.get("fehler")
    finally:
        app._abo_flach = echt_flach
        app._playlists[:] = [p for p in app._playlists if p.get("id") != "plENT"]
        for k in ("seedA000001|audio", "seedB000001|audio", "altGELADEN1|beste"):
            app._geladen.pop(k, None)


def test_abo_baseline_shorts_fallback():
    # Build 91 (Simulations-Fund): Shorts-only-Kanaele (@YouTubeShorts) haben
    # KEINEN /videos-Tab — yt-dlp liefert 404/leer. Dann den /shorts-Tab
    # probieren, statt das Abo mit „ohne Videos" abzulehnen. Tab-Titel wie
    # „Kanal - Videos" verlieren ihr Suffix (sonst wird es der Abo-Name).
    def fake_flach(url, limit=60):
        if url.endswith("/shorts"):
            return {"title": "ShortsKanal - Shorts", "channel_id": "UCshorts",
                    "entries": [{"id": "shrt0000001"}]}
        return {}                                      # /videos-Tab existiert nicht

    echt_flach = app._abo_flach
    app._abo_flach = fake_flach
    try:
        url, ids, titel, info = app._abo_baseline("https://www.youtube.com/@S/videos")
        assert url == "https://www.youtube.com/@S/shorts"
        assert ids == ["shrt0000001"]
        assert titel == "ShortsKanal"                  # Suffix „ - Shorts" weg
        assert info.get("channel_id") == "UCshorts"
        # Playlist-URL ohne /videos-Ende: KEIN Shorts-Umweg, leer bleibt leer
        url2, ids2, _, _ = app._abo_baseline("https://www.youtube.com/playlist?list=PLx")
        assert url2.endswith("list=PLx") and ids2 == []
    finally:
        app._abo_flach = echt_flach


def test_abo_baseline_topic_uploads():
    # Build 91 (Simulations-Fund): Kuenstler-Topic-Kanaele (auto-generiert,
    # „Kate Bush - Topic") haben WEDER videos- noch shorts-Tab — erst die
    # Uploads-Playlist UU<Kanal-Suffix> traegt die Songs. Namens-Praefix
    # „Uploads from " gehoert nicht in den Abo-Namen.
    def fake_flach(url, limit=60):
        if "list=UUtopicsuffix" in url:
            return {"title": "Uploads from X - Topic", "channel_id": "UCtopicsuffix",
                    "entries": [{"id": "song0000001"}, {"id": "song0000002"}]}
        return {}                                      # beide Tabs fehlen

    echt_flach = app._abo_flach
    app._abo_flach = fake_flach
    try:
        url, ids, titel, info = app._abo_baseline(
            "https://www.youtube.com/channel/UCtopicsuffix/videos")
        assert url == "https://www.youtube.com/playlist?list=UUtopicsuffix"
        assert ids == ["song0000001", "song0000002"]
        assert titel == "X - Topic"                    # „Uploads from " weg
        assert info.get("channel_id") == "UCtopicsuffix"
        # /@handle ohne Kanal-ID: kein UU-Ausweg ableitbar -> ehrlich leer
        url2, ids2, _, _ = app._abo_baseline("https://www.youtube.com/@X/videos")
        assert ids2 == []
    finally:
        app._abo_flach = echt_flach


def test_abo_delete_mit_videos():
    # Build 95 (JB): Abo entfernen optional MIT den über das Abo geladenen
    # Videos — NUR Inhalte der eigenen Abo-Playlist (wie abo_aufraeumen),
    # Papierkorb statt hart, manuell Geladenes bleibt unberührt.
    import tempfile
    d = tempfile.mkdtemp()
    alt_ordner = app.ABO_INDEX_ORDNER
    app.ABO_INDEX_ORDNER = d
    still = lambda *a, **k: None                       # noqa: E731
    echt_json, echt_pl = app._json_speichern, app._playlists_speichern
    echt_del = app._datei_loeschen
    app._json_speichern, app._playlists_speichern = still, still
    weg = []
    app._datei_loeschen = lambda key: weg.append(key)
    app._abos.append({"id": "aboWEG", "name": "K", "qualitaet": "audio", "playlist_id": "plWEG"})
    app._playlists.append({"id": "plWEG", "name": "K", "items": ["vidA0000001|audio", "vidB0000001|audio"]})
    app._geladen["vidA0000001|audio"] = {"name": "a.mp3"}
    app._geladen["vidB0000001|audio"] = {"name": "b.mp3"}
    app._geladen["fremd0000001|audio"] = {"name": "f.mp3"}   # NICHT vom Abo — muss bleiben
    try:
        r = app.abo_aktion({"art": "delete", "id": "aboWEG", "mit_videos": True})
        assert r.get("ok") and r.get("geloescht") == 2
        assert sorted(weg) == ["vidA0000001|audio", "vidB0000001|audio"]
        assert "vidA0000001|audio" not in app._geladen
        assert "vidB0000001|audio" not in app._geladen
        assert "fremd0000001|audio" in app._geladen            # unberührt
        assert not any(a.get("id") == "aboWEG" for a in app._abos)
        assert not any(p.get("id") == "plWEG" for p in app._playlists)
        # OHNE mit_videos: nur das Abo geht (Bestandsverhalten)
        app._abos.append({"id": "aboBLEIBT", "name": "B", "qualitaet": "audio"})
        r2 = app.abo_aktion({"art": "delete", "id": "aboBLEIBT"})
        assert r2.get("ok") and r2.get("geloescht", 0) == 0
        assert "fremd0000001|audio" in app._geladen
    finally:
        app.ABO_INDEX_ORDNER = alt_ordner
        app._json_speichern, app._playlists_speichern = echt_json, echt_pl
        app._datei_loeschen = echt_del
        app._abos[:] = [a for a in app._abos if a.get("id") not in ("aboWEG", "aboBLEIBT")]
        app._playlists[:] = [p for p in app._playlists if p.get("id") != "plWEG"]
        for k in ("vidA0000001|audio", "vidB0000001|audio", "fremd0000001|audio"):
            app._geladen.pop(k, None)


def test_abo_heilen():
    # Build 91: Bestands-Abos aus der Build-88-Zeit tragen den blossen
    # Kanal-Link + Reiter-IDs als Baseline (JBs KateBush-Abo). Heilen =
    # URL normalisieren, Baseline NEU holen (ohne Downloads), Folgen-Cache
    # verwerfen. Netz weg ⇒ alles bleibt unveraendert (nicht-destruktiv).
    import json
    import tempfile
    d = tempfile.mkdtemp()
    alt_ordner = app.ABO_INDEX_ORDNER
    app.ABO_INDEX_ORDNER = d
    echt_flach, echt_json = app._abo_flach, app._json_speichern
    app._json_speichern = lambda *a, **k: None
    abo = {"id": "aboHEIL", "url": "https://www.youtube.com/channel/UCkaputt",
           "name": "Kanal", "qualitaet": "beste",
           "bekannt": ["UCkaputt", "UCkaputt"], "feed": ""}
    cache = os.path.join(d, "aboHEIL.json")
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"folgen": [{"id": "UCkaputt", "titel": "Kanal - Videos"}]}, f)
    try:
        app._abo_flach = lambda url, limit=60: {}          # Netz/Kanal weg
        assert app._abo_heilen(abo) == (False, False)
        assert abo["url"] == "https://www.youtube.com/channel/UCkaputt"
        assert abo["bekannt"] == ["UCkaputt", "UCkaputt"]  # unveraendert
        assert os.path.exists(cache)

        app._abo_flach = lambda url, limit=60: {
            "title": "Kanal", "channel_id": "UCkaputt",
            "entries": [{"id": "vidA0000001"}, {"id": "vidB0000001"}]}
        assert app._abo_heilen(abo) == (True, True)
        assert abo["url"] == "https://www.youtube.com/channel/UCkaputt/videos"
        assert abo["bekannt"] == ["vidA0000001", "vidB0000001"]
        assert abo["feed"].endswith("channel_id=UCkaputt")
        assert not os.path.exists(cache)                   # Reiter-Cache verworfen

        assert app._abo_heilen(abo) == (True, False)       # schon sauber
    finally:
        app.ABO_INDEX_ORDNER = alt_ordner
        app._abo_flach, app._json_speichern = echt_flach, echt_json


def test_abos_pruefen_heilt_ohne_lawine():
    # Build 91, Lawinen-Schutz: Die Heilung erneuert die Baseline — die
    # aktuellen Videos des Kanals duerfen danach NICHT als „neu" in die
    # Warteschlange rauschen. Kein einziger Download-Thread darf starten.
    starts = []

    class FakeThread:
        def __init__(self, *a, **k):
            starts.append(k)

        def start(self):
            pass

    echt_thread, echt_rss = app.threading.Thread, app._abo_rss_ids
    echt_flach, echt_json = app._abo_flach, app._json_speichern
    alt_abos = app._abos[:]
    app.threading.Thread = FakeThread
    app._abo_rss_ids = lambda feed: None                   # kein Netz im Test
    app._json_speichern = lambda *a, **k: None
    app._abo_flach = lambda url, limit=60: {
        "title": "Kanal", "channel_id": "UCheil",
        "entries": [{"id": "vidN0000001"}, {"id": "vidN0000002"}]}
    abo = {"id": "aboLAWINE", "url": "https://www.youtube.com/@Kanal",
           "name": "Kanal", "qualitaet": "beste",
           "bekannt": ["UCheil", "UCheil"], "feed": "", "neu": 0}
    app._abos[:] = [abo]
    try:
        app.abos_pruefen()
        assert starts == []                                # KEINE Download-Lawine
        assert abo["url"] == "https://www.youtube.com/@Kanal/videos"
        assert abo["bekannt"] == ["vidN0000001", "vidN0000002"]
    finally:
        app.threading.Thread, app._abo_rss_ids = echt_thread, echt_rss
        app._abo_flach, app._json_speichern = echt_flach, echt_json
        app._abos[:] = alt_abos


def test_dubletten_score():
    # Dubletten-Heilung (JB 14.07.): bei mehreren Einträgen auf dieselbe Datei
    # gewinnt der echte Download vor dem Ordner-Import, benannte Qualität vor
    # 'lokal', Kanal-Info gibt den Ausschlag.
    echt = {"qualitaet": "audio", "uploader": "Kanal"}
    import_lokal = {"qualitaet": "lokal", "importiert": True}
    import_audio = {"qualitaet": "audio", "importiert": True}
    assert app._dubletten_score(echt) > app._dubletten_score(import_audio)
    assert app._dubletten_score(import_audio) > app._dubletten_score(import_lokal)
    assert app._dubletten_score({"qualitaet": "beste"}) > app._dubletten_score({"qualitaet": "lokal"})


def test_vtt_verwaist():
    # Selbstheilung 14.07.: verwaiste .vtt erkennen — gehörige Untertitel
    # (<stamm>.<sprache>.vtt neben existierendem Medium) bleiben, Doppelungen
    # aus dem Alt-Index-Bug (.de.de.vtt) und Reste ohne Medium fliegen raus.
    stems = {r"c:\d\mp3\song [abc12345678]".lower(),
             r"c:\d\mp3\mr. blue sky [xyz98765432]".lower()}
    assert app._vtt_verwaist(r"C:\d\mp3\Song [abc12345678].de.vtt", stems) is False
    assert app._vtt_verwaist(r"C:\d\mp3\Song [abc12345678].ja-orig.vtt", stems) is False
    assert app._vtt_verwaist(r"C:\d\mp3\Song [abc12345678].vtt", stems) is False
    assert app._vtt_verwaist(r"C:\d\mp3\Mr. Blue Sky [xyz98765432].en.vtt", stems) is False
    assert app._vtt_verwaist(r"C:\d\mp3\Song [abc12345678].de.de.vtt", stems) is True
    assert app._vtt_verwaist(r"C:\d\mp3\Geloescht [ttt11111111].de.vtt", stems) is True


def test_ist_untertitel_fehler():
    # JB-Vorfall 11.07.: YouTube drosselte die Untertitel (429) und der ganze
    # Download hing stundenlang bei 0% — solche Fehler müssen als "heilbar
    # ohne Untertitel" erkannt werden.
    ja = "Unable to download video subtitles for 'de': HTTP Error 429: Too Many Requests"
    assert app._ist_untertitel_fehler(ja) is True
    assert app._ist_untertitel_fehler("ERROR: Unable to download video subtitles") is True
    # KEINE Untertitel-Heilung bei anderen Fehlern (Video-429, Geo, Formate):
    assert app._ist_untertitel_fehler("HTTP Error 429: Too Many Requests") is False
    assert app._ist_untertitel_fehler("Requested format is not available") is False
    assert app._ist_untertitel_fehler("") is False


def test_datei_videoid_kette():
    # Bibliothek 2.0 (Build 110): DIE zentrale Auflösung Datei -> Video-Id.
    # Stufe 1 Name, Stufe 2 bekannter DB-Pfad, Stufe 3 Content-Fingerabdruck —
    # Grundlage dafür, dass Dateinamen ihre [Id]-Klammern verlieren dürfen.
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    mit_id = os.path.join(d, "Song [abcdef12345].mp3")
    ohne = os.path.join(d, "Sauberer Name.mp3")
    kopie = os.path.join(d, "Verschoben und umbenannt.mp3")
    with open(ohne, "wb") as f:
        f.write(b"INHALT-A" * 500)
    shutil.copy(ohne, kopie)
    alt_geladen = app._geladen
    app._geladen = {"vidPfad0001|audio": {"pfad": ohne},
                    "vidFpxx0001|audio": {"fp": app._datei_fp(kopie)}}
    try:
        assert app._datei_videoid(mit_id) == "abcdef12345"      # Name (Datei muss nicht existieren)
        assert app._datei_videoid(ohne) == "vidPfad0001"        # bekannter Pfad
        assert app._datei_videoid(kopie) == "vidFpxx0001"       # Fingerabdruck
        assert app._datei_videoid(os.path.join(d, "gibtsnicht.mp3")) == ""
    finally:
        app._geladen = alt_geladen


def test_fp_von_cache():
    # Build 110: Cache liefert stabil, erkennt aber Inhalts-Änderungen (mtime).
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "x.mp3")
    with open(p, "wb") as f:
        f.write(b"ALT" * 100)
    fp1 = app._fp_von(p)
    assert fp1 and app._fp_von(p) == fp1              # zweiter Aufruf: aus dem Cache
    with open(p, "wb") as f:
        f.write(b"NEU-INHALT" * 100)
    t = time.time() + 5
    os.utime(p, (t, t))                               # mtime sicher verschieben
    fp2 = app._fp_von(p)
    assert fp2 and fp2 != fp1


def test_technik_backfill_fp():
    # Build 110: der Start-Backfill trägt fp für Bestands-Einträge nach — auch
    # wenn acodec längst da ist (kein ffprobe-Aufruf nötig); Einträge ohne
    # Datei bleiben unangetastet, nichts crasht.
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "Bestand [bestand0001].mp3")
    with open(p, "wb") as f:
        f.write(b"BESTAND" * 300)
    alt_ziel, alt_json, alt_geladen = app.ziel_ordner, app._json_speichern, app._geladen
    app.ziel_ordner = lambda: d
    app._json_speichern = lambda *a, **k: None
    app._geladen = {"bestand0001|audio": {"acodec": "mp3", "pfad": p},
                    "wegdatei001|audio": {"acodec": "mp3"}}     # keine Datei -> bleibt ohne fp
    try:
        app.technik_backfill()
        assert app._geladen["bestand0001|audio"].get("fp") == app._datei_fp(p)
        assert "fp" not in app._geladen["wegdatei001|audio"]
    finally:
        app.ziel_ordner, app._json_speichern = alt_ziel, alt_json
        app._geladen = alt_geladen


def test_id_tag_rundlauf_und_kette():
    # Build 111 (Bibliothek 2.0 Schicht 2): Video-Id als Tag IN der mp3.
    # Schreiben -> Lesen liefert die Id zurück; das fp ÄNDERT sich durchs Tag
    # (deshalb gilt: erst Tag, dann fp speichern); die Kette erkennt eine
    # getaggte Datei auch OHNE jeden DB-Eintrag (Kumpel-Kopie-Szenario).
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "Vom Kumpel kopiert.mp3")
    with open(p, "wb") as f:
        f.write(b"\xff\xfbAUDIO" * 400)
    fp_vorher = app._datei_fp(p)
    assert app._id_tag_schreiben(p, "tagvid00001") is True
    assert app._id_tag_lesen(p) == "tagvid00001"
    assert app._datei_fp(p) != fp_vorher              # Tag verschiebt den Inhalt
    assert app._datei_videoid(p) == "tagvid00001"     # Stufe 4, ganz ohne DB
    # Grenzen: Video-Container werden NIE beschrieben (GB-Rewrite-Gefahr),
    # leere Id auch nicht.
    assert app._id_tag_schreiben(os.path.join(d, "film.mp4"), "tagvid00001") is False
    assert app._id_tag_schreiben(p, "") is False


def test_technik_backfill_idtag():
    # Build 111: der Backfill taggt EIGENE Bestands-Downloads (und erneuert
    # danach fp+Größe); importierte Fremd-Dateien bleiben unangetastet.
    import tempfile
    d = tempfile.mkdtemp()
    eigen = os.path.join(d, "Eigener Download [eigenvid001].mp3")
    fremd = os.path.join(d, "JBs CD-Rip.mp3")
    for pf in (eigen, fremd):
        with open(pf, "wb") as f:
            f.write(b"\xff\xfbBESTAND" * 300)
    fp_fremd = app._datei_fp(fremd)
    alt_ziel, alt_json, alt_geladen = app.ziel_ordner, app._json_speichern, app._geladen
    app.ziel_ordner = lambda: d
    app._json_speichern = lambda *a, **k: None
    app._geladen = {"eigenvid001|audio": {"acodec": "mp3", "pfad": eigen,
                                          "fp": app._datei_fp(eigen)},
                    "fremdvid001|audio": {"acodec": "mp3", "pfad": fremd,
                                          "fp": fp_fremd, "importiert": True}}
    try:
        app.technik_backfill()
        e = app._geladen["eigenvid001|audio"]
        assert e.get("idtag") is True
        assert app._id_tag_lesen(eigen) == "eigenvid001"
        assert e.get("fp") == app._datei_fp(eigen)     # fp NACH dem Tag erneuert
        f2 = app._geladen["fremdvid001|audio"]
        assert f2.get("idtag") is False                # nur markiert …
        assert app._datei_fp(fremd) == fp_fremd        # … Datei unverändert
    finally:
        app.ziel_ordner, app._json_speichern = alt_ziel, alt_json
        app._geladen = alt_geladen


def test_dateiname_bauen_schema():
    # Build 113 (JB): Bausteine wählbar UND in der Reihenfolge schiebbar.
    e = {"titel": "Prince - Purple Rain (Official Music Video) [HD]",
         "kuenstler": "Prince", "track": "Purple Rain", "album": "Purple Rain",
         "jahr": "1984", "track_nr": 7}
    bau = app._dateiname_bauen
    assert bau(e, schema=["kuenstler", "titel"]) == "Prince - Purple Rain"
    assert bau(e, schema=["titel", "kuenstler"]) == "Purple Rain - Prince"
    assert bau(e, schema=["nr", "kuenstler", "titel"]) == "07 Prince - Purple Rain"
    assert bau(e, schema=["kuenstler", "titel", "album", "jahr"]) == \
        "Prince - Purple Rain (Purple Rain) (1984)"
    # „Zusatz" trägt nur, was die AUFNAHME beschreibt — Werbe-Klammern fliegen raus.
    live = {"titel": "Fleetwood Mac - Landslide (Live) (Official Video) [HD]"}
    assert bau(live, schema=["kuenstler", "titel", "zusatz"]) == \
        "Fleetwood Mac - Landslide (Live)"
    # Video-Id nur, wenn ausdrücklich gewählt
    mit_id = dict(e, _vid="uW1UIDYmYyI")
    assert bau(mit_id, schema=["kuenstler", "titel", "id"]) == \
        "Prince - Purple Rain [uW1UIDYmYyI]"
    # Windows-verbotene Zeichen verschwinden, nichts bleibt am Ende hängen
    boese = {"titel": "AC/DC - T.N.T. ?", "kuenstler": "AC/DC", "track": "T.N.T. ?"}
    gebaut = bau(boese, schema=["kuenstler", "titel"])
    assert not set(gebaut) & set('<>:"/\\|?*') and not gebaut.endswith((".", " "))


def test_orig_tag_und_undo():
    # Build 113: der ursprüngliche Name wird IN der Datei vermerkt (JB) und
    # „↩ Rückgängig" nimmt den letzten Lauf zurück — auch die .vtt.
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "Prince - Purple Rain (Official Video) [vidorig0001].mp3")
    v = os.path.join(d, "Prince - Purple Rain (Official Video) [vidorig0001].de.vtt")
    for pf in (p, v):
        with open(pf, "wb") as f:
            f.write(b"\xff\xfbTON" * 300)
    alt_json, alt_sag, alt_geladen = app._json_speichern, app._sag, app._geladen
    alt_prot = app.PROTOKOLL_PFAD
    app.PROTOKOLL_PFAD = os.path.join(d, "protokoll.json")
    app._sag = lambda *a, **k: None
    app._json_speichern = alt_json          # echtes Speichern nur für die Protokoll-Datei
    gespeichert = {}

    def faelschung(pfad, daten):
        if pfad == app.PROTOKOLL_PFAD:
            return alt_json(pfad, daten)
        gespeichert["db"] = True
    app._json_speichern = faelschung
    app._geladen = {"vidorig0001|audio": {"pfad": p, "fp": "fpO", "titel": "Prince - Purple Rain (Official Video)",
                                          "kuenstler": "Prince", "track": "Purple Rain"}}
    try:
        r = app.migration_anwenden(go=True, schema=["kuenstler", "titel"])
        assert r["umbenannt"] == 1
        neu = os.path.join(d, "Prince - Purple Rain.mp3")
        assert os.path.isfile(neu) and os.path.isfile(os.path.join(d, "Prince - Purple Rain.de.vtt"))
        assert app._orig_tag(neu) == os.path.basename(p)      # Original steht IN der Datei
        assert app._geladen["vidorig0001|audio"]["pfad"] == neu
        z = app.migration_rueckgaengig()
        assert z == {"ok": True, "zurueck": 2, "blockiert": 0}
        assert os.path.isfile(p) and os.path.isfile(v) and not os.path.exists(neu)
        assert app._geladen["vidorig0001|audio"]["pfad"] == p
        assert app.migration_rueckgaengig()["ok"] is False     # Protokoll ist leer
    finally:
        app._json_speichern, app._sag = alt_json, alt_sag
        app._geladen, app.PROTOKOLL_PFAD = alt_geladen, alt_prot


def test_migration_probelauf_und_anwenden():
    # Build 112 (Klammern-Projekt): Probelauf listet nur, Anwenden benennt
    # NUR Konfliktfreies um — additiv, .vtt wandert mit, DB zieht nach.
    import tempfile
    d = tempfile.mkdtemp()
    a = os.path.join(d, "Song A [aaaavid0001].mp3")
    av = os.path.join(d, "Song A [aaaavid0001].de.vtt")
    b = os.path.join(d, "Song B [bbbbvid0001].mp3")          # ohne fp/Tag -> gesperrt
    c = os.path.join(d, "Song C [ccccvid0001].mp3")          # Ziel existiert schon
    czal = os.path.join(d, "Song C.mp3")
    for pf in (a, av, b, c, czal):
        with open(pf, "wb") as f:
            f.write(b"\xff\xfbX" * 200)
    # LEHRE aus dem 23.07.-Vorfall: _geladen KOMPLETT ersetzen, nie in JBs
    # echte DB einfügen — migration_anwenden(go=True) hätte sonst (und HAT
    # einmal!) die echte Bibliothek umbenannt. Rollback war nur dank
    # fp/DB-Pfaden trivial; der Test läuft seitdem vollisoliert.
    alt_json, alt_sag, alt_geladen = app._json_speichern, app._sag, app._geladen
    app._json_speichern = lambda *ar, **k: None
    app._sag = lambda *ar, **k: None
    app._geladen = {
        "aaaavid0001|audio": {"pfad": a, "fp": "fpA"},
        "bbbbvid0001|audio": {"pfad": b},
        "ccccvid0001|audio": {"pfad": c, "fp": "fpC"},
    }
    try:
        plan = {x["key"]: x for x in app.migration_probelauf()}
        assert plan["aaaavid0001|audio"]["konflikt"] == ""
        assert plan["aaaavid0001|audio"]["neu"] == os.path.join(d, "Song A.mp3")
        assert plan["aaaavid0001|audio"]["vtt"] == [av]
        assert "Sicherheitsnetz" in plan["bbbbvid0001|audio"]["konflikt"]
        assert "existiert" in plan["ccccvid0001|audio"]["konflikt"]
        assert os.path.isfile(a)                              # Probelauf fasst NICHTS an
        r0 = app.migration_anwenden()                         # ohne go: verweigert
        assert r0.get("ok") is False and os.path.isfile(a)
        r = app.migration_anwenden(go=True)
        assert r == {"ok": True, "umbenannt": 1, "uebersprungen": 2}
        assert os.path.isfile(os.path.join(d, "Song A.mp3"))
        assert os.path.isfile(os.path.join(d, "Song A.de.vtt"))
        assert not os.path.exists(a) and not os.path.exists(av)
        assert os.path.isfile(b) and os.path.isfile(c)        # Konflikte unangetastet
        e = app._geladen["aaaavid0001|audio"]
        assert e["pfad"].endswith("Song A.mp3") and e["name"] == "Song A.mp3"
    finally:
        app._json_speichern, app._sag = alt_json, alt_sag
        app._geladen = alt_geladen


def test_pfad_da():
    # Build 109 (JB-Failsafe): das Sync-Fenster graut tote Pfade nur aus und
    # fragt live nach — die Antwort muss die Wirklichkeit JETZT spiegeln.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        assert app.pfad_da(d)["da"] is True
    assert app.pfad_da(d)["da"] is False            # nach dem with wieder weg
    assert app.pfad_da("")["da"] is False
    assert app.pfad_da(r"C:\gibt\es\nicht\xyz123")["da"] is False
    assert app.pfad_da("kein\x00pfad")["da"] is False   # kaputte Zeichen crashen nicht


# ---------------------------------------------------------------- Runner (ohne pytest)

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            ok += 1
        except Exception as e:                          # noqa: BLE001 — Testreport
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{ok}/{len(tests)} Tests bestanden.")
    sys.exit(0 if ok == len(tests) else 1)


# ---------------------------------------------------------------- Oberflaechen-Waechter (Build 125)

def _oberflaeche_html():
    """Der HTML-Rumpf der Oberflaeche (ohne <style>/<script>) als Baum-Parser-Futter."""
    import oberflaeche
    return oberflaeche.HTML


def _funktionsende(quelle, start):
    """Ende der JS-Funktion, die bei `start` beginnt (Anfang der naechsten).

    Feste Zeichenfenster (`quelle[i:i+1800]`) sind truegerisch: waechst die
    Funktion, rutscht der gepruefte Inhalt lautlos aus dem Fenster und der
    Waechter wird gruen, ohne etwas zu pruefen - oder rot, obwohl alles
    stimmt (beides am 23.07. passiert).
    """
    naechste = quelle.find("\nfunction ", start + 1)
    return naechste if naechste > 0 else len(quelle)


def _kaefig_klassen(quelle):
    """Klassen/Ids, die im CSS Containment setzen.

    `container-type` und `contain:` erzeugen Layout-Containment. Das macht das
    Element zum Stapel-Kontext UND zum Bezugsrahmen fuer absolut/fixed
    positionierte Kinder — ein Menue darin kann per z-index NIE hoeher steigen
    als sein Kaefig (live gemessen 23.07.: Ansicht-Menue mit z-index 6100 lag
    unter einem Panel mit z-index 14).
    """
    import re
    css = re.search(r"<style>(.*?)</style>", quelle, re.S)
    assert css, "Kein <style>-Block gefunden"
    raus = set()
    for regel in re.finditer(r"([^{}]+)\{([^{}]*)\}", css.group(1)):
        sel, koerper = regel.group(1), regel.group(2)
        if "container-type" in koerper or re.search(r"\bcontain\s*:", koerper):
            for s in sel.split(","):
                for name in re.findall(r"[.#]([A-Za-z0-9_-]+)", s):
                    raus.add(name)
    return raus


def _baum_verstoesse(quelle, schwebend, kaefige):
    """Findet schwebende Flaechen, die im HTML unter einem Kaefig haengen."""
    from html.parser import HTMLParser

    leer = {"br", "img", "input", "meta", "link", "hr", "source", "path", "circle", "rect"}

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stapel = []
            self.treffer = []

        def handle_starttag(self, tag, attrs):
            d = dict(attrs)
            namen = set(d.get("class", "").split())
            if d.get("id"):
                namen.add(d["id"])
            if namen & schwebend:
                kaefig = [k for eb in self.stapel for k in (eb & kaefige)]
                if kaefig:
                    self.treffer.append((sorted(namen & schwebend)[0], kaefig[-1]))
            if tag not in leer:
                self.stapel.append(namen)

        def handle_endtag(self, tag):
            if tag not in leer and self.stapel:
                self.stapel.pop()

    p = P()
    p.feed(quelle)
    return p.treffer


def test_schwebende_flaechen_nicht_im_kaefig():
    # JB-Fund (mehrere Runden): „Ansicht-Menue liegt hinter den Panels".
    # Wurzel: das Menue haengt statisch in .libbar, und .libbar traegt
    # container-type:inline-size (seit Build 122, fuer die schmalen Leisten).
    # Regel ab jetzt: schwebende Flaechen gehoeren an den <body> — nie in ein
    # Element mit Containment. Dieser Waechter gilt automatisch fuer JEDE
    # kuenftige Flaeche und jeden kuenftigen Kaefig.
    quelle = _oberflaeche_html()
    schwebend = {"abo-flyout", "panelmenu", "itemmenu", "colmenu", "popover", "modal-box"}
    kaefige = _kaefig_klassen(quelle)
    assert "libbar" in kaefige, "Erwartet: .libbar traegt Containment (sonst Test veraltet)"
    verstoesse = _baum_verstoesse(quelle, schwebend, kaefige)
    assert not verstoesse, (
        "Schwebende Flaeche sitzt im Containment-Kaefig (z-index wirkt dort nicht): "
        + ", ".join(f"{f} in .{k}" for f, k in verstoesse)
    )


def test_kopfleiste_symbolspalte_bleibt_senkrecht():
    # JB-Bild: Abo/Tag-Nacht/Hilfe/Einstellungen sind eine SENKRECHTE Leiste.
    # Gemessen bei 476 px: eine @media-Regel drehte sie auf flex-direction:row
    # (4 Knoepfe nebeneinander, 121 px statt 28 px breit).
    import re
    quelle = _oberflaeche_html()
    css = re.search(r"<style>(.*?)</style>", quelle, re.S).group(1)
    for regel in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, koerper = regel.group(1), regel.group(2)
        if re.search(r"\.cmd-side\b", sel) and re.search(r"flex-direction\s*:\s*row", koerper):
            raise AssertionError(f"Symbol-Spalte wird waagerecht gedreht: {sel.strip()}")


def test_kopfleiste_player_hat_mindestmass():
    # JB-Fund: „Statistik-Spalte ueberlappt den Player". Gemessen bei 360 px:
    # Statistik (126) + Symbole (121) sind flex:0 0 auto und geben nie nach,
    # also schrumpfte NUR der Player — auf 69 px, sein Inhalt lief 135 px
    # heraus, mitten unter die Statistik. Der Player braucht ein Mindestmass,
    # damit bei Platzmangel etwas ANDERES ausweicht.
    import re
    quelle = _oberflaeche_html()
    css = re.search(r"<style>(.*?)</style>", quelle, re.S).group(1)
    masse = [
        int(m2.group(1))
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)
        if re.search(r"[.#]cmd-now\b", m.group(1))
        for m2 in re.finditer(r"min-width\s*:\s*(\d+)px", m.group(2))
    ]
    assert masse and max(masse) >= 200, (
        "#cmd-now braucht ein echtes Mindestmass (>=200px). Gefunden: "
        + (str(masse) if masse else "keins")
        + " — min-width:0 erlaubt das Schrumpfen bis zum Ueberlauf."
    )


def test_abbruch_greift_auch_beim_zusammenfuegen():
    # JB-Fund: „Laufende Downloads lassen sich nicht abbrechen."
    # Wurzel: die Optionen trugen nur progress_hooks. Der feuert waehrend des
    # Ladens — danach uebernimmt ffmpeg (Bild+Ton zusammenfuegen, MP3 wandeln,
    # Cover einbetten), und genau in dieser laengsten Phase (Anzeige
    # „Zusammenfuegen") sah niemand mehr nach, ob JB abgebrochen hat.
    # yt-dlp bietet dafuer postprocessor_hooks — die muessen denselben
    # Abbruch pruefen wie der Fortschritts-Hook.
    import types
    gefangen = {}

    class FakeYDL:
        def __init__(self, opts):
            gefangen["opts"] = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=True):
            return {"id": "abbruchtest", "title": "Probe", "ext": "mp4"}

    fake = types.ModuleType("yt_dlp")
    fake.YoutubeDL = FakeYDL
    alt = sys.modules.get("yt_dlp")
    sys.modules["yt_dlp"] = fake
    item = {"id": "abbr1", "qualitaet": "720p", "status": "laeuft", "titel": "Probe",
            "url": "https://example.invalid/v", "prozent": 0.0, "geladen": 0, "gesamt": 0,
            "geschw": 0, "phase": "", "versuche": 0, "fehler": "", "naechster_versuch": 0}
    try:
        try:
            app._download_lauf(item)
        except Exception:                             # noqa: BLE001 — nur die opts zaehlen
            pass
        opts = gefangen.get("opts") or {}
        assert opts.get("progress_hooks"), "progress_hooks fehlen"
        pp = opts.get("postprocessor_hooks")
        assert pp, ("postprocessor_hooks fehlen — waehrend „Zusammenfuegen\" "
                    "greift kein Abbruch")
        # Der Nachbearbeitungs-Hook muss den Abbruch genauso beachten.
        app.Q.abbrueche.add("abbr1")
        try:
            fehler = None
            try:
                pp[0]({"status": "started", "postprocessor": "Merger"})
            except app.AbbruchError:
                fehler = "abbruch"
            assert fehler == "abbruch", (
                "postprocessor_hook stoppt nicht bei gesetztem Abbruch")
        finally:
            app.Q.abbrueche.discard("abbr1")
    finally:
        if alt is not None:
            sys.modules["yt_dlp"] = alt
        else:
            sys.modules.pop("yt_dlp", None)


# ---------------------------------------------------------------- Ein Feld fuer alles (Build 126)

def test_link_deuten_eindeutige_faelle():
    # JB-Ziel: EIN Feld, Enter genuegt, die App erkennt den Typ am Link.
    # Gefragt wird NUR bei echter Mehrdeutigkeit — alles hier ist eindeutig
    # und darf niemals eine Rueckfrage ausloesen.
    d = app.link_deuten
    for url, typ in [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video"),
        ("https://youtu.be/dQw4w9WgXcQ", "video"),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "video"),
        ("https://www.youtube.com/shorts/abcdefghijk", "video"),
        ("https://www.youtube.com/playlist?list=PLabcdefgh", "playlist"),
        ("https://www.youtube.com/@MrBeast/videos", "kanal"),
        ("https://www.youtube.com/@MrBeast/streams", "kanal"),
    ]:
        r = d(url)
        assert r["typ"] == typ, f"{url} -> {r['typ']}, erwartet {typ}"
        assert r["eindeutig"] is True, f"{url} loest unnoetig eine Rueckfrage aus"
        assert not r.get("frage"), f"{url} traegt eine Frage, obwohl eindeutig"


def test_link_deuten_die_zwei_echten_mehrdeutigkeiten():
    # Genau zwei Faelle sind wirklich mehrdeutig (JB hat sie benannt):
    # Kanal = laden oder abonnieren? Video-in-Playlist = eines oder alle?
    kanal = app.link_deuten("https://www.youtube.com/@MrBeast")
    assert kanal["typ"] == "kanal" and kanal["eindeutig"] is False
    assert {o["id"] for o in kanal["optionen"]} == {"laden", "abo"}

    inpl = app.link_deuten("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLabc")
    assert inpl["typ"] == "video_in_playlist" and inpl["eindeutig"] is False
    assert {o["id"] for o in inpl["optionen"]} == {"eines", "alle"}

    # Jede Option muss einen Klartext fuer den Menschen tragen.
    for r in (kanal, inpl):
        assert r.get("frage"), "Rueckfrage ohne Fragetext"
        for o in r["optionen"]:
            assert o.get("text"), "Option ohne Beschriftung"


def test_link_deuten_mix_bleibt_beim_bestehenden_weg():
    # Mixe (list=RD…) sind endlos und haben schon ihre eigene Anzahl-Frage
    # (Build 98). Die Deutung meldet sie als Mix und erfindet keine zweite.
    r = app.link_deuten("https://www.youtube.com/watch?v=abc&list=RDabc")
    assert r["typ"] == "mix"
    assert r["eindeutig"] is True          # Anzahl-Frage kommt aus dem Mix-Weg


def test_link_deuten_kein_link():
    for text in ("", "   ", "einfach nur text", "ftp://example.invalid/x"):
        r = app.link_deuten(text)
        assert r["typ"] == "unbekannt", f"{text!r} -> {r['typ']}"
        assert r["eindeutig"] is False


def test_link_deuten_fremde_seite_ist_kein_youtube():
    # yt-dlp kann viele Seiten; ein fremder Link ist ein normaler Download
    # und darf keine YouTube-Rueckfrage ausloesen.
    r = app.link_deuten("https://vimeo.com/123456")
    assert r["typ"] == "video" and r["eindeutig"] is True


def test_link_rueckfrage_wird_immer_gestellt():
    # JB 23.07.: "Das Feld immer so muss nicht sein, diese Abfrage ist meiner
    # Meinung nach immer relevant." Ob man einen Kanal abonniert oder laedt,
    # haengt am Kanal - eine gemerkte Antwort waere hier eine Falle. Es darf
    # also KEINE Config geben, die die Rueckfrage ueberspringt.
    for weg in ("link_antwort_kanal", "link_antwort_playlist"):
        assert weg not in app.CFG, f"{weg} lebt noch - die Rueckfrage waere abschaltbar"
    for url in ("https://www.youtube.com/@MrBeast",
                "https://www.youtube.com/watch?v=abc&list=PLx"):
        r = app.link_deuten(url)
        assert r["eindeutig"] is False
        assert "gemerkt" not in r, "Die Deutung traegt noch eine gemerkte Antwort"
        assert sum(1 for o in r["optionen"] if o.get("standard")) == 1


def test_liste_zuschneiden_menge_und_richtung():
    # JB 23.07.: "ich wuerde gerne einen Regler haben bei alle Videos jetzt
    # laden ... die Option aelteste/neueste zuerst ist relevant."
    # yt-dlp liefert Kanaele NEUESTE ZUERST. Der Zuschnitt muss deshalb
    # wissen, von welchem Ende er nimmt - und die Downloads sollen danach
    # chronologisch laufen (aelteste zuerst), so wie es der Abo-Backkatalog
    # schon macht.
    neu_zuerst = [{"id": f"v{i}", "title": f"Folge {10-i}"} for i in range(10)]
    z = app._liste_zuschneiden

    # Keine Menge = alles bleibt, Reihenfolge unangetastet.
    assert z(neu_zuerst, None, "neu") == neu_zuerst
    assert z(neu_zuerst, 0, "neu") == neu_zuerst

    # Die 3 NEUESTEN: das sind die ersten drei der Quelle.
    ids = [e["id"] for e in z(neu_zuerst, 3, "neu")]
    assert ids == ["v0", "v1", "v2"]

    # Die 3 AELTESTEN: das andere Ende - und chronologisch geladen,
    # also aelteste zuerst.
    ids = [e["id"] for e in z(neu_zuerst, 3, "alt")]
    assert ids == ["v9", "v8", "v7"]

    # Mehr gewuenscht als vorhanden: einfach alles, kein Fehler.
    assert len(z(neu_zuerst, 999, "neu")) == 10
    # Leere/kaputte Eintraege fliegen raus, ohne zu crashen.
    assert z([None, {"id": "a"}, None], 5, "neu") == [{"id": "a"}]
    assert z([], 3, "neu") == []


def test_menuschliesser_schliesst_das_uebergebene_menue():
    # JB-Fund 23.07.: "das Fenster ging eben nicht weg, auch wenn ich nichts
    # angewaehlt habe. Wenn ich woanders hinklicke, dann sollte es
    # verschwinden."
    # Wurzel: menuSchliesser(m) nahm das Menue entgegen, benutzte es aber
    # NICHT - es raeumte hartkodiert nur .itemmenu weg. Aufrufer mit einer
    # anderen Klasse (die Link-Rueckfrage und der Mengen-Regler sind
    # .panelmenu) bekamen stillschweigend gar kein Schliessen.
    # Der Waechter haelt fest, dass der Parameter wirklich verwendet wird -
    # sonst faellt der naechste Aufrufer mit neuer Klasse genauso durch.
    import re
    quelle = _oberflaeche_html()
    m = re.search(r"function menuSchliesser\(m\)\{(.*?)\n\}", quelle, re.S)
    assert m, "menuSchliesser nicht gefunden"
    koerper = m.group(1)
    assert re.search(r"\bm\.remove\(\)", koerper), (
        "menuSchliesser entfernt sein eigenes Argument nicht - Menues mit "
        "anderer Klasse als .itemmenu bleiben offen stehen")
    assert re.search(r"\bm\.contains\(", koerper), (
        "menuSchliesser prueft nicht, ob der Klick INS uebergebene Menue "
        "ging - ein Klick auf den eigenen Inhalt wuerde es zuklappen")


def test_schwebende_flaechen_werden_alle_geschlossen():
    # Jede Flaeche, die per menuSchliesser aufgeraeumt wird, muss auch am
    # <body> haengen (sonst greift popoverBei/das Schliessen ins Leere) -
    # und umgekehrt darf keine neue schwebende Flaeche ohne Schliesser
    # gebaut werden. Geprueft an den beiden Build-126/127-Flaechen.
    quelle = _oberflaeche_html()
    for funktion, flaeche in (("linkFrage", "linkfrage"),
                              ("mengenRegler", "mengenregler")):
        i = quelle.index("function " + funktion)
        block = quelle[i:i + 3000]
        assert "document.body.appendChild(m)" in block, (
            f"{funktion}: Flaeche haengt nicht am <body>")
        assert "menuSchliesser(m)" in block, (
            f"{funktion}: kein Aussenklick-Schliesser - {flaeche} bliebe stehen")


def test_tooltips_sind_standardmaessig_verborgen():
    # JB-Fund 23.07. ("Formatierung wieder gekippt"): Die Aufschluesselung im
    # Zaehler stand dauerhaft in der Statistik-Spalte und blaehte sie auf.
    # Wurzel: die Regeln hingen an der KLASSE `.counter`, das Element traegt
    # aber `class="cmd-count"` (nur die id heisst counter). Ein toter
    # Selektor versteckt nichts - und faellt niemandem auf, weil CSS still
    # scheitert.
    # Dieser Waechter prueft die EIGENSCHAFT statt des Namens: fuer jedes
    # .tip im HTML muss es eine Regel geben, die es verbirgt und die ueber
    # eine Klasse laeuft, die das Eltern-Element wirklich traegt.
    import re
    quelle = _oberflaeche_html()
    css = re.search(r"<style>(.*?)</style>", quelle, re.S).group(1)

    # Welche Selektoren verbergen ein .tip?
    verstecker = set()
    for regel in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, koerper = regel.group(1), regel.group(2)
        if re.search(r"\.tip\b", sel) and re.search(r"display\s*:\s*none", koerper):
            for teil in sel.split(","):
                m = re.search(r"\.([A-Za-z][\w-]*)\s+\.tip\b", teil)
                if m:
                    verstecker.add(m.group(1))
    assert verstecker, "Keine Regel verbirgt .tip — die Aufschluesselung stuende immer offen"

    # Jedes .tip im HTML muss einen Vorfahren mit einer dieser Klassen haben.
    for treffer in re.finditer(r'<span[^>]*class="[^"]*\btip\b[^"]*"', quelle):
        davor = quelle[max(0, treffer.start() - 400):treffer.start()]
        eltern_klassen = set()
        for m in re.finditer(r'class="([^"]*)"', davor):
            eltern_klassen.update(m.group(1).split())
        assert eltern_klassen & verstecker, (
            "Ein .tip haengt unter keinem Element, das von der Versteck-Regel "
            f"getroffen wird. Versteckt wird unter: {sorted(verstecker)}; "
            f"vorhanden sind: {sorted(eltern_klassen)}")


def test_vollbild_overlay_hat_das_wichtigste():
    # JB Punkt 3: Vollbild-Overlay wie Netflix/Disney - "nur das Wichtigste:
    # Play/Pause, +/-10 s, Zeitleiste, Untertitel, naechster Titel, Beenden".
    # Der Grund, warum diese Knoepfe NUR im Vollbild noetig sind: Zufall/Vor/
    # Zurueck wohnen seit Build 121 oben in der Steuerzentrale - die ist im
    # Vollbild aber nicht sichtbar. Ohne sie kaeme man dort nicht weiter.
    import re
    quelle = _oberflaeche_html()
    css = re.search(r"<style>(.*?)</style>", quelle, re.S).group(1)

    # Die Zusatz-Knoepfe existieren und sind als „nur im Vollbild" markiert.
    for kennung in ("plb-back10", "plb-fwd10", "plb-next", "plb-exitfs"):
        assert kennung in quelle, f"Vollbild-Knopf {kennung} fehlt"

    # Ausserhalb des Vollbilds verborgen, im Vollbild sichtbar.
    assert re.search(r"\.nur-vollbild\{[^}]*display\s*:\s*none", css), \
        "Die Vollbild-Knoepfe waeren auch ausserhalb des Vollbilds sichtbar"
    assert re.search(r":fullscreen[^{]*\.nur-vollbild\{[^}]*display\s*:", css), \
        "Im Vollbild werden die Zusatz-Knoepfe nicht eingeblendet"
    # Und im Vollbild raeumt es die Nebensachen weg (JB: nur das Wichtigste).
    assert re.search(r":fullscreen[^{]*\.weg-im-vollbild\{[^}]*display\s*:\s*none", css), \
        "Im Vollbild bleibt alles stehen - das ist kein Netflix-Muster"


def test_player_bild_springt_nicht():
    # JB ausdruecklich: "16:9 FEST - echtes Mass je Video = Nogo, das Bild
    # darf nicht springen." Das Bildfeld haengt deshalb an einem festen
    # Seitenverhaeltnis (Standard 16:9) und NICHT an den Maszen des Videos;
    # object-fit:contain legt das Bild mit Balken hinein, statt den Rahmen
    # zu verformen.
    import re
    quelle = _oberflaeche_html()
    css = re.search(r"<style>(.*?)</style>", quelle, re.S).group(1)
    regeln = [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)
              if re.search(r"\.pl-media\s+video\b", m.group(1))]
    zusammen = " ".join(regeln)
    assert "aspect-ratio" in zusammen, \
        "Das Bildfeld hat kein festes Seitenverhaeltnis - es springt je Video"
    assert "object-fit:contain" in zusammen.replace(" ", ""), \
        "Ohne object-fit:contain wuerde das Bild verzerrt statt eingepasst"
    # Andere Verhaeltnisse als Option (JB: "zusaetzlich als Layout-Option").
    assert re.search(r"seitenverhaeltnis|--pl-ar", css + quelle), \
        "Es gibt keine Umschaltung auf ein anderes Seitenverhaeltnis"


def test_addon_knopf_braucht_gueltigen_anker():
    # JB-Fund 23.07.: "das firefox plugin ist bei einem beendeten video ganz
    # oben links. nicht mehr im video, sondern ausserhalb."
    # Wurzel: getBoundingClientRect() liefert bei einem Element OHNE Masse
    # (beendetes Video, ausgeblendeter Player, gerade ausgetauschter DOM)
    # lauter Nullen. zeigen() rechnete blind weiter, und Math.max(4, 0+6)
    # klemmte den Knopf in die linke obere Bildschirmecke - sichtbar, aber
    # ohne jeden Bezug zum Video.
    # Regel: ohne brauchbaren Anker wird der Knopf VERSTECKT, nicht geparkt.
    import io
    import os
    quelle = io.open(os.path.join(os.path.dirname(__file__), "..",
                                  "browser-addon", "shared", "content.js"),
                     encoding="utf-8").read()
    assert "ankerBrauchbar" in quelle, "Keine Pruefung des Ankers vorhanden"
    # zeigen() muss die Pruefung wirklich anwenden und bei Unbrauchbarkeit raus.
    i = quelle.index("function zeigen(")
    block = quelle[i:i + 900]
    assert "ankerBrauchbar" in block, "zeigen() prueft den Anker nicht"
    assert "verstecken()" in block, "zeigen() versteckt den Knopf nicht bei unbrauchbarem Anker"
    # Und die Position darf nicht mehr an den Bildschirmrand geklemmt werden,
    # sondern an den Anker (JB-Dauerregel: Masse an die POSITION koppeln).
    assert "Math.max(4," not in block, (
        "Der Knopf wird weiter an den Bildschirmrand geklemmt statt an das Video")


def test_klickart_zum_abspielen_einstellbar():
    # JB Punkt 4: "Einstellung Einfach- vs. Doppelklick zum Abspielen
    # (Doppelklick Standard - JBs Kumpel bevorzugt Einfachklick; JB:
    # Doppelklick fuehlt sich nativer an und stoert die Auswahl nicht)."
    # Der Grund fuer den Standard steckt in JBs Begruendung: bei Einfachklick
    # kollidiert Abspielen mit dem Auswaehlen. Wer ihn trotzdem will, stellt
    # ihn um - deshalb muss die Wahl existieren UND der Standard Doppelklick
    # sein.
    quelle = _oberflaeche_html()
    assert "klickArt" in quelle, "Keine Einstellung fuer die Klick-Art vorhanden"
    assert "ytdl_klickart" in quelle, "Die Wahl wird nicht gemerkt"
    # Standard ist Doppelklick.
    import re
    m = re.search(r"function klickArt\(\)\{[^}]*'(einfach|doppel)'", quelle)
    assert m and m.group(1) == "doppel", "Standard ist nicht Doppelklick"
    # Und die Kacheln/Zeilen muessen den Doppelklick auch auswerten.
    assert "kachelDblClick" in quelle, "Kacheln reagieren nicht auf Doppelklick"


def test_titel_auf_playlist_ziehen():
    # JB Punkt 4: "Titel auf Playlists ziehen; auf 'keine Playlist' fallen
    # lassen = neue anlegen; Mehrfachauswahl zusammen ziehen; Rueckgaengig
    # dafuer."
    quelle = _oberflaeche_html()
    assert "plselDrop" in quelle, "Die Playlist-Auswahl ist kein Fallziel"
    assert "ondrop=\"plselDrop(event)\"" in quelle, "Kein ondrop an der Playlist-Auswahl"
    # Fallen lassen auf "keine Playlist" legt eine NEUE an.
    i = quelle.index("function plselDrop")
    block = quelle[i:i + 2200]
    assert "art:'create'" in block.replace(" ", ""), \
        "Fallenlassen auf 'keine Playlist' legt keine neue an"
    # Mehrfachauswahl reist mit (die Entscheidung faellt in plZiehKeys).
    j = quelle.index("function plZiehKeys")
    zieh = quelle[j:j + 700]
    assert "libAuswahl" in zieh, "Die Mehrfachauswahl wird beim Ziehen nicht mitgenommen"
    assert "libAuswahl.size>1" in zieh.replace(" ", ""),         "Ein einzeln gezogener Titel darf nicht die ganze Auswahl mitreissen"
    # Und es gibt ein Rueckgaengig.
    assert "plZurueck" in quelle, "Kein Rueckgaengig fuer das Einreihen"


def test_rahmenauswahl_in_der_bibliothek():
    # JB Punkt 4: "Rahmen-Auswahl mit der Maus wie in Windows / wie in der
    # Abo-Ansicht." Das Muster gibt es dort bereits (aboBandStart, Build 94) -
    # die Bibliothek bekommt dasselbe, damit sich beides gleich anfuehlt.
    quelle = _oberflaeche_html()
    assert "libBandStart" in quelle, "Keine Rahmen-Auswahl in der Bibliothek"
    i = quelle.index("function libBandStart")
    block = quelle[i:_funktionsende(quelle, i)]
    # Dieselben Eigenschaften wie das Vorbild: erst ab ein paar Pixeln ein
    # Band, Strg additiv, nachlaufender Klick wird geschluckt.
    assert "ctrlKey" in block, "Strg erweitert die Auswahl nicht"
    assert "libBandLief" in block, "Kein Merker fuer einen gelaufenen Band-Zug"
    # Die Eigenschaft zaehlt, nicht der Name: der Klick-Handler muss den
    # Merker abfragen, sonst hebt der nachlaufende Klick die Auswahl auf.
    k = quelle.index("function kachelClick")
    assert "libBandLief" in quelle[k:k + 400],         "kachelClick schluckt den nachlaufenden Klick nicht"
    # Die Elemente brauchen eine Kennung, damit der Rahmen sie treffen kann.
    assert 'data-id="${x.id}"' in quelle, "Kacheln/Zeilen tragen keine data-id"


def test_rahmen_in_der_playlist_startet_auch_auf_einer_zeile():
    # JB dreimal gemeldet, zuletzt 23.07.: "Ich kann im Player immer noch kein
    # Fenster mit der Maus ziehen." Build 139 hatte das Muster der BIBLIOTHEK
    # uebernommen - dort startet das Band nur auf freier Flaeche, damit die
    # ziehbaren Kacheln ziehbar bleiben. In einer LISTE gibt es diese Flaeche
    # aber nicht. Am echten Fenster gemessen (23.07., Build 144): bei 14 Titeln
    # ist .pl-queue randvoll (Inhalt 362 px in 150 px Sicht), bei 3 Titeln
    # schrumpft sie auf exakt ihre Zeilenhoehe (76 px) - freie Hoehe 0 px in
    # BEIDEN Faellen, weil .pl-queue mit dem Inhalt waechst (flex:0 1 auto +
    # max-height). Jeder Punkt der Liste liegt also auf einer .pl-item, das
    # Band konnte nie starten. Denselben Fund gab es im Abo-Fenster schon
    # (Build 94: "die Zeilen sind vollbreit, freie Flaeche gibt es kaum").
    quelle = _oberflaeche_html()
    i = quelle.index("function plqBandStart")
    block = quelle[i:i + 2800].replace(" ", "")
    assert "closest('.pl-item'))return" not in block, (
        "plqBandStart steigt auf JEDER Zeile aus - in einer Liste ohne freie "
        "Flaeche kann das Band damit nie starten")
    # Die Entscheidung faellt jetzt an der MARKIERUNG statt am blossen
    # Zeilen-Treffer (Explorer-Muster: erst waehlen, dann die Auswahl greifen).
    assert "plqAuswahl.has" in block or "contains('sel')" in block, (
        "Der Zeilen-Fall wird nicht an der Markierung entschieden")


def test_playlist_umsortieren_bleibt_neben_dem_rahmen():
    # Der Zeilen-Ausschluss aus Build 139 hatte einen echten Grund: die Zeilen
    # sind draggable (Umsortieren, und seit Build 141 zieht die Mehrfachauswahl
    # mit). Beides muss nebeneinander bestehen - der Rahmen darf das Ziehen
    # nicht auffressen.
    quelle = _oberflaeche_html()
    i = quelle.index("function plqBandStart")
    block = quelle[i:i + 2800].replace(" ", "")
    # 1) Eine markierte Zeile bleibt ziehbar (dort steigt das Band aus).
    assert "return" in block and "sel" in block,         "Auf einer markierten Zeile hat das Ziehen keinen Vorrang mehr"
    # 2) Wo das Band gilt, muss der native HTML5-Drag abgewuergt werden -
    #    sonst frisst er die pointermove-Ereignisse und das Band bleibt leer.
    j = quelle.index("function plqDragStart")
    drag = quelle[j:j + 700].replace(" ", "")
    assert "preventDefault" in drag, (
        "plqDragStart wuergt den nativen Drag nicht ab - er verschluckt dann "
        "die Bewegung, die das Band braucht")
    # 3) Rueckweg (JB Punkt 7: "Einstellung zum Umschalten der Rahmen-Auswahl"):
    #    das alte Verhalten muss einstellbar bleiben.
    assert "plqRahmenArt" in quelle, "Keine Einstellung fuer die Rahmen-Auswahl"
    assert "opt_plqrahmen" in quelle, "Die Einstellung steht in keinem Menue"


def test_playlist_markierung_zeigt_die_ganze_auswahl():
    # Live-Fund beim Nachmessen des Rahmens (23.07., Build 144): Das Band
    # waehlte korrekt aus (plqAuswahl = 0..4), doch nach dem Loslassen trug
    # KEINE Zeile mehr die Klasse 'sel' - plqMark() malte nur den Fokus-Eintrag
    # plqSel an und loeschte die eben gezogene Auswahl sofort wieder weg.
    # Denselben Weg nimmt der Strg-Klick. renderPlayerQueue kannte beide
    # Quellen laengst ("i===plqSel||plqAuswahl.has(i)") - plqMark war beim
    # Nachziehen von Build 139 schlicht vergessen worden. Zwei Stellen, eine
    # Wahrheit: wer 'sel' setzt, muss beide Quellen kennen.
    quelle = _oberflaeche_html()
    i = quelle.index("function plqMark")
    block = quelle[i:i + 400].replace(" ", "")
    assert "plqAuswahl" in block, (
        "plqMark malt die Mehrfachauswahl nicht an - eine gezogene Auswahl "
        "verschwindet beim Loslassen wieder")


def test_kanal_nummer_ist_keine_tracknummer():
    # JB Punkt 4: "Videonummer je Kanal als eigenes Feld." Mit ausdruecklicher
    # Warnung: NICHT als Track-Nummer - die heisst "Position innerhalb eines
    # Werks", daraus entstuende "500x die 1". Vorbild ist abo_nr.
    eintraege = [
        {"id": "a|b", "uploader": "Kanal X", "upload_date": "20240101"},
        {"id": "b|b", "uploader": "Kanal X", "upload_date": "20240301"},
        {"id": "c|b", "uploader": "kanal x", "upload_date": "20240201"},   # Schreibweise egal
        {"id": "d|b", "uploader": "Anderer", "upload_date": "20240101"},
        {"id": "e|b", "uploader": "", "upload_date": "20240101"},
    ]
    nr, von = app._kanal_nummern(eintraege)
    # Je Kanal durchnummeriert, aeltestes = 1. Genau das verhindert "500x die 1".
    assert (nr["a|b"], nr["c|b"], nr["b|b"]) == (1, 2, 3)
    # Ein anderer Kanal faengt wieder bei 1 an.
    assert nr["d|b"] == 1
    # Ohne Kanal gibt es KEINE Nummer - lieber keine Angabe als eine erfundene.
    assert "e|b" not in nr
    # Und die Gesamtzahl je Kanal, damit "3 / 12" moeglich ist.
    assert von["a|b"] == 3 and von["d|b"] == 1


def test_kanal_nummer_weicht_der_echten_abo_nummer():
    # Wo eine ECHTE Kanal-Nummer bekannt ist (Abo-Backkatalog: aelteste Folge
    # = 1 ueber den ganzen Kanal), hat sie Vorrang vor der abgeleiteten
    # Bibliotheks-Position - sie ist die genauere Wahrheit.
    quelle = open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    i = quelle.index("def _kanal_nummern")
    # Die Zuweisung selbst steht in der Bibliotheks-Liste.
    j = quelle.index('"abo_nr": e.get("abo_nr"')
    umfeld = quelle[j:j + 600]
    assert "kanal_nr" in umfeld, "Die Kanal-Nummer steht nicht in der Bibliotheks-Liste"
    assert "abo_nr" in umfeld, "Die echte Abo-Nummer hat keinen Vorrang"
    # Abgeleitet statt gespeichert: eine gespeicherte Nummer wuerde falsch,
    # sobald ein aelteres Video des Kanals dazukommt.
    block = quelle[i:i + 1200]
    assert "upload_date" in block, "Die Reihenfolge haengt nicht am Upload-Datum"
    # Die Oberflaeche zeigt es als eigene Spalte.
    ui = _oberflaeche_html()
    assert "kanal_nr" in ui, "Keine Spalte fuer die Kanal-Nummer"
    # Und sie zeigt eine ABGELEITETE Nummer nur, wenn es beim selben Kanal
    # etwas zu ordnen gibt. An JBs echter Bibliothek gemessen: 69 von 84
    # Titeln stuenden sonst auf "#1" - er hat von den meisten Kanaelen genau
    # EIN Video. Das saehe aus wie die befuerchtete "500x die 1".
    k = ui.index("kanalnr:{")
    spalte = ui[k:k + 400]
    assert "kanal_von>1" in spalte.replace(" ", ""), (
        "Eine Kanal-Nummer erscheint auch bei nur einem Video des Kanals")


def test_playlist_fuellt_den_freien_platz():
    # JB mit Bild (23.07.): "jetzt ist playlist nur noch ein kleines fenster,
    # das sollte dynamisch bis zum unteren rand von playlist gehen."
    # Gemessen im vertikalen Layout bei 560 px Panel: Karte 489 px, aber die
    # Playlist-SPALTE nahm davon nur 199 px (flex:0 0 auto) und die Liste war
    # zusaetzlich auf max-height:150px gedeckelt - 180 px Inhalt scrollten in
    # 150 px, waehrend darunter Platz ungenutzt blieb.
    # Das Video bleibt an 16:9 gebunden; alles Uebrige gehoert der Liste.
    # ERLEDIGT ist der Teil ohne Video: das herausgeloeste Playlist-FENSTER.
    # Dort war die Karte nur so hoch wie ihr Inhalt (132 px in einem 420 px
    # hohen Panel), weil `#view-plq` selbst keine Hoehe hatte - height:100%
    # von auto ist auto.
    quelle = _oberflaeche_html()
    css = quelle[quelle.index("<style"):quelle.index("</style>")]
    kurz = " ".join(css.split())
    assert "#view-plq{height:100%" in kurz, (
        "Das Playlist-Fenster hat keine eigene Hoehen-Regel - seine Karte "
        "bleibt inhaltshoch, und darunter bleibt totes Schwarz")
    i = kurz.find("#view-plq{height:100%")
    assert "#view-plq>.card{flex:1 1 auto" in kurz[i:i + 200], (
        "Die Karte im Playlist-Fenster fuellt das Panel nicht aus")
    # NICHT erledigt und bewusst nicht geraten: die Playlist IM Player. Dort
    # konkurriert ein 16:9-Video mit fester Hoehe mit der Liste um dieselbe
    # Hoehe; vier CSS-Wege sind daran gescheitert (jeder live gemessen).
    # Der Kommentar im CSS haelt den Stand fest, damit die naechste Session
    # nicht bei null anfaengt - verschwindet er, ist die Warnung weg.
    assert "vier CSS-Wege" in css, (
        "Der offene Stand der Player-Playlist ist im CSS nicht mehr vermerkt")


def test_rahmen_gilt_im_ganzen_fenster():
    # JB-Regel mit Bild (23.07.): "genauso wie oben, sollte man auch von unten
    # ein fenster ziehen koennen ... solange es in dem fenster ist, ist ein
    # feld ziehen gewaehrleistet."
    # Gemessen war das Gegenteil, und zwar bei BEIDEN Listen aus derselben
    # Wurzel: die Karte ist nur so hoch wie ihr INHALT, nicht so hoch wie das
    # Panel. Playlist-Fenster: Panel 420 px, Karte 132 px - die 232 px darunter
    # gehoerten dem `panel-body`, dort hing "KEINER bis zum body". Bibliothek
    # auf einen Treffer gefiltert: 105 px Leerraum, gleicher Befund.
    # Der Zuhoerer gehoert deshalb an den panel-body: das IST das Fenster.
    quelle = _oberflaeche_html()
    r = quelle.index("function renderPlayerQueue")
    assert "panel-body" in quelle[r:_funktionsende(quelle, r)], (
        "Der Playlist-Rahmen deckt den leeren Bereich unter der Liste nicht ab")
    m = quelle.index("function libMalen")
    assert "panel-body" in quelle[m:_funktionsende(quelle, m)], (
        "Der Bibliotheks-Rahmen deckt den leeren Bereich unter den Kacheln nicht ab")
    # Ausgenommen bleibt die Videoflaeche - dort zieht man kein Band, sie hat
    # ihre eigene Steuerung und ist Drop-Ziel.
    b = quelle.index("function plqBandStart")
    assert "pl-media" in quelle[b:_funktionsende(quelle, b)], (
        "Auf dem Video darf kein Rahmen starten")
    # Ein Panel kann mehrere Ansichten tragen (Reiter). Der Zuhoerer am
    # panel-body darf deshalb nur anspringen, wenn SEINE Liste dort sichtbar
    # ist - sonst zieht man in Ansicht A einen Rahmen ueber Ansicht B.
    assert "offsetParent" in quelle[b:_funktionsende(quelle, b)], (
        "Der Rahmen prueft nicht, ob seine Liste in diesem Fenster sichtbar ist")


def test_lieblingssongs_knopf_im_player():
    # JB Punkt 3: "Spotify-artiges + im Player oben fuer eine
    # Lieblingssongs-Playlist."
    quelle = _oberflaeche_html()
    assert "pl-lieb" in quelle, "Kein Lieblings-Knopf im Player"
    assert "lieblingToggle" in quelle, "Der Knopf tut nichts"
    t = quelle[quelle.index("function lieblingToggle"):]
    t = t[:_funktionsende(quelle, quelle.index("function lieblingToggle"))
          - quelle.index("function lieblingToggle")].replace('"', "'")
    # Die Playlist entsteht beim ERSTEN Klick - JB soll sie nicht erst von
    # Hand anlegen muessen, sonst ist der Knopf beim ersten Mal eine Sackgasse.
    assert "'create'" in t, "Die Lieblings-Playlist wird nicht selbst angelegt"
    # Zweiter Klick nimmt wieder heraus (Spotify-Verhalten), und zwar ueber
    # 'ersetzen': 'remove' traefe zwar auch, aber 'ersetzen' setzt die Liste
    # exakt und ist derselbe Weg wie ueberall sonst.
    assert "'ersetzen'" in t, "Der Knopf kann nur hinzufuegen, nicht wieder herausnehmen"
    # Der Knopf ZEIGT den Zustand des laufenden Titels (gefuellt/leer).
    i = quelle.index("function lieblingMalen")
    m = quelle[i:_funktionsende(quelle, i)]
    assert "istLiebling" in m, "Der Knopf zeigt nicht, ob der Titel schon drin ist"
    # Und er wird beim Titelwechsel nachgezogen, sonst zeigt er den Vorgaenger.
    r = quelle.index("function renderPlayerMedia")
    assert "lieblingMalen" in quelle[r:_funktionsende(quelle, r)], (
        "Beim Titelwechsel bleibt der Knopf auf dem alten Stand stehen")


def test_rahmen_darf_oberhalb_der_playlist_beginnen():
    # JB nach der Probe mit der echten Maus (23.07.): "wie in bibliothek soll
    # der fenster ziehen modus in player/playlist schon ein/zwei reihen
    # darueber funktionieren koennen" - das Ziehen selbst laeuft seit
    # Build 144 ("ansonsten funktioniert das fenster ziehen jetzt").
    # Dieselbe Bitte gab es fuer die BIBLIOTHEK schon einmal (Build 143:
    # "ich kann immer noch kein Fenster ziehen von einer Reihe ueber der
    # Bibliothek, das ist frustrierend"); dort haengt der Zuhoerer seitdem
    # auch an der Karte. In der Playlist hing er nur an der Liste selbst -
    # wer eine Reihe darueber ansetzte, traf ins Leere.
    quelle = _oberflaeche_html()
    r = quelle[quelle.index("function renderPlayerQueue"):][:2600]
    assert "pl-side" in r, (
        "Der Rahmen haengt nicht am Behaelter oberhalb der Playlist im Player")
    assert "view-plq" in r, (
        "Im herausgeloesten Playlist-Fenster haengt er nicht an der Karte")
    b = quelle[quelle.index("function plqBandStart"):][:1800].replace(" ", "")
    # Getroffen und gescrollt wird trotzdem die LISTE, nicht der Behaelter -
    # sonst schiebt das Rand-Nachschieben am falschen Element.
    assert "'.pl-queue'" in b, (
        "plqBandStart ermittelt die Liste nicht aus dem Behaelter")
    # Zwei Ebenen hoeren mit -> ohne Sperre entstuenden ZWEI Baender uebereinander.
    assert "plqZugLaeuft" in b, (
        "Keine Sperre gegen ein zweites Band, wenn beide Ebenen mithoeren")


def test_playlist_folgt_dem_hineingezogenen_titel():
    # JB Punkt 2: "Playlist speichern/aktualisieren, wenn man Titel in eine
    # gerade laufende Playlist zieht" - "ganz dezent irgendwo".
    # Vorher war das gar nicht moeglich: playerPlay bekam nur den NAMEN der
    # Quelle mit (plPlaySel rief playerPlay(ids,start,p.name)), nie ihre Id.
    # Der Player wusste also nicht, WOHIN er zurueckspeichern soll.
    quelle = _oberflaeche_html()
    assert "plid" in quelle, "Der Player merkt sich die Playlist-Id nicht"
    i = quelle.index("function plPlaySel")
    ende = quelle.index("function plExport", i)          # genau diese eine Funktion, nicht mehr
    assert "p.id" in quelle[i:ende], "plPlaySel reicht die Playlist-Id nicht weiter"
    # "Geaendert?" wird VERGLICHEN, nicht gemerkt: ein Merker muesste an jeder
    # kuenftigen Aenderungsstelle gesetzt werden und wird dort vergessen.
    j = quelle.index("function plqGeaendert")
    vgl = quelle[j:j + 900].replace(" ", "")
    assert "plState" in vgl, "Der Aenderungs-Zustand wird nicht gegen die gespeicherte Playlist geprueft"
    # Mischen ist eine Wiedergabe-Entscheidung, keine Playlist-Aenderung -
    # sonst stuende nach jedem Zufalls-Start sofort "geaendert" da und der
    # Hinweis waere wertlos (Calm-Design: nur bei echtem Handlungsbedarf).
    assert "sort" in vgl, "Der Vergleich zaehlt die Reihenfolge mit - Mischen wuerde ihn ausloesen"


def test_playlist_sichern_zerstoert_die_reihenfolge_nicht():
    # Nicht-destruktiv (HARTE REGEL): Wer bei gemischter Wiedergabe einen
    # Titel hineinzieht, darf damit nicht die gespeicherte Reihenfolge
    # ueberschreiben. Deshalb behaelt das Sichern die Reihenfolge der
    # PLAYLIST bei, wirft nur Entferntes raus und haengt Neues hinten an.
    quelle = _oberflaeche_html()
    i = quelle.index("function plqSichern")
    block = quelle[i:i + 1200]
    kurz = block.replace(" ", "").replace('"', "'")
    assert "'ersetzen'" in kurz, (
        "Gesichert wird nicht ueber 'ersetzen' - nur das setzt die Liste exakt")
    assert "p.items" in kurz, (
        "Das Sichern geht nicht von der gespeicherten Reihenfolge aus")
    # Der Hinweis erscheint NUR bei Bedarf und haengt an beiden Playlist-Sichten.
    assert "plq-sichern" in quelle, "Kein Sichern-Hinweis in der Oberflaeche"
    r = quelle.index("function renderPlayerQueue")
    assert "plq-sichern" in quelle[r:_funktionsende(quelle, r)], (
        "renderPlayerQueue blendet den Hinweis nicht nach Bedarf ein/aus")


def test_tag_kandidat_zweiter_versuch_ohne_klammern():
    # JB: "wieso sind mehrere titel noch nicht korrekt benannt?"
    # Zwei Gruende. Der zweite: der Muell-Filter kennt nur BEKANNTE Zusaetze
    # (official, lyrics, live ...). Alles andere bleibt stehen und laesst die
    # MusicBrainz-Suche ins Leere laufen - z.B. "(Traduzione Italiana)" oder
    # "(from The Wildlife Concert)" aus JBs Bibliothek.
    # Loesung: ein ZWEITER Versuch ohne jegliche Klammer-Zusaetze. Fuer die
    # Suche ist ein Klammerzusatz fast nie Teil des echten Titels - und wenn
    # doch, findet MusicBrainz ihn auch ohne.
    blank = app._titel_blank
    assert blank("Tears in Heaven - Live 1992 (Traduzione Italiana)")         == "Tears in Heaven - Live 1992"
    # Grenze, bewusst so: Zusaetze nach einem BINDESTRICH bleiben stehen.
    # Sehr viele echte Titel tragen Bindestriche ("Ich will - Rammstein",
    # "Sgt. Pepper's - Reprise"); sie abzuschneiden wuerde mehr kaputt machen
    # als heilen. Klammern dagegen sind fast immer Beiwerk.
    assert blank("Take Me Home, Country Roads (from The Wildlife Concert)") \
        == "Take Me Home, Country Roads"
    assert blank("Rocky Mountain High [Remastered 2015]") == "Rocky Mountain High"
    # Ein sauberer Titel bleibt unangetastet.
    assert blank("The Boxer") == "The Boxer"
    # Und es bleibt IMMER etwas uebrig - ein leerer Suchbegriff waere nutzlos.
    assert blank("(nur Klammern)") == "(nur Klammern)"
    assert blank("") == ""


def test_autotag_laeuft_nach_dem_download():
    # JB: "auto tagging sollte standartmaessig direkt nach dem download
    # passieren." Bisher musste man es im Ansicht-Menue von Hand anstossen -
    # deshalb trugen frisch geladene Titel noch den rohen YouTube-Namen.
    # Es haengt sich an das BESTEHENDE Fertig-Ereignis (Last-Budget-Regel:
    # kein neuer Dauerprozess, kein neuer Zeitplan).
    import inspect
    quelle = inspect.getsource(app)
    assert "autotag_nach_download" in quelle, "Kein Auto-Tagging nach dem Download"
    i = quelle.index("def autotag_nach_download")
    block = quelle[i:i + 1400]
    # Nur Musik, und nur wenn noch nichts getaggt ist - sonst waeren es
    # sinnlose Anfragen an MusicBrainz bei jedem Video.
    assert "_ist_musik" in block, "Auch Videos wuerden getaggt"
    assert "album" in block, "Schon getaggte Titel wuerden erneut abgefragt"


def test_warteschlange_heilt_tote_auftraege():
    # JB Punkt 6: "Warteschlange gegen tote Auftraege selbst heilen."
    # Zwei Loecher gab es:
    #  1. Beim Start wurde nur "laeuft" wieder eingereiht - ein Eintrag, der
    #     beim Absturz gerade AUFGELOEST wurde ("prueft"), blieb fuer immer
    #     liegen: Q.naechster() greift nur "wartend" auf, also ruehrte ihn
    #     nie wieder jemand an.
    #  2. Zur Laufzeit konnte ein Auftrag im Zustand "prueft" haengen, wenn
    #     der Aufloese-Thread starb.
    # Geheilt wird NICHT-DESTRUKTIV: der Eintrag wird wieder eingereiht, die
    # .part-Datei bleibt liegen und der Download setzt fort.
    import inspect
    quelle = inspect.getsource(app)
    assert "def queue_heilen" in quelle, "Keine Selbstheilung der Warteschlange"
    i = quelle.index("def queue_heilen")
    block = quelle[i:i + 1500]
    assert '"prueft"' in block, "Haengende 'prueft'-Auftraege werden nicht geheilt"
    assert '"wartend"' in block, "Der Auftrag wird nicht wieder eingereiht"
    # Nichts wird geloescht - Selbstheilung ist nicht-destruktiv (harte Regel).
    assert "remove" not in block and "del " not in block, \
        "Die Heilung entfernt Eintraege - das waere destruktiv"

    # Und der Start raeumt beide Zustaende ab.
    start = quelle[quelle.index("class Warteschlange"):]
    start = start[:start.index("def speichern")]
    assert '"prueft"' in start, "Beim Start bleibt 'prueft' liegen"


def test_playlist_erlaubt_doppelte_titel():
    # JB 23.07.: "Ich will songs auch doppelt in eine playlist ziehen koennen.
    # Ist ja meine Entscheidung."
    # Das Backend hat es bisher STILL verhindert (k not in pl["items"]) - der
    # Titel wurde gezogen, und nichts passierte. Eine Playlist ist eine
    # Reihenfolge, kein Mengenbegriff: derselbe Song darf zweimal vorkommen.
    import tempfile, os, json
    alt_pl, alt_sp = app._playlists, app._json_speichern
    app._json_speichern = lambda *a, **k: None
    try:
        app._playlists = [{"id": "p1", "name": "Test", "items": [], "ts": 0}]
        schluessel = next(iter(app._geladen), None)
        if not schluessel:
            return                                    # leere Bibliothek: nichts zu pruefen
        for _ in range(3):
            app.playlist_aktion({"art": "add", "id": "p1", "key": schluessel})
        assert app._playlists[0]["items"] == [schluessel] * 3, \
            "Doppelte Titel werden weiterhin verschluckt"
        # Rueckgaengig braucht eine Aktion, die die Liste EXAKT wiederherstellt -
        # ein 'remove' wuerde alle Vorkommen treffen, nicht nur den letzten Wurf.
        app.playlist_aktion({"art": "ersetzen", "id": "p1", "items": [schluessel]})
        assert app._playlists[0]["items"] == [schluessel]
        # Unbekannte Keys prallen ab (nichts Erfundenes in der Playlist).
        app.playlist_aktion({"art": "ersetzen", "id": "p1", "items": ["gibtsnicht", schluessel]})
        assert app._playlists[0]["items"] == [schluessel]
    finally:
        app._playlists, app._json_speichern = alt_pl, alt_sp


def test_player_rahmen_ist_16zu9():
    # JB-Bild: "jetzt ist der player nicht mehr 16:9, oder? Also Player 16:9
    # obenbuendig ... Der Player ist ja eigentlich nur das 16:9 bild und
    # darunter und darueber grosse freie flaechen."
    # Der Rahmen (nicht nur das <video>) muss das Verhaeltnis tragen - sonst
    # waechst er bei einem Audio-Titel mit quadratischem Cover ueber die
    # ganze Panel-Hoehe, und genau das zeigte JBs Bild.
    import re
    quelle = _oberflaeche_html()
    css = re.search(r"<style>(.*?)</style>", quelle, re.S).group(1)
    treffer = [m.group(2) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)
               if re.search(r"#view-player[^,{]*\.pl-media\b(?!\s+\w)", m.group(1))
               and "aspect-ratio" in m.group(2)]
    assert treffer, "Der Player-RAHMEN traegt kein Seitenverhaeltnis"
    zus = " ".join(treffer).replace(" ", "")
    assert "height:auto" in zus, \
        "Mit fester Hoehe schlaegt die Hoehe das Seitenverhaeltnis (gemessen)"


def test_css_kommentare_sind_sauber_geschlossen():
    # Eigener Fehler, ZWEIMAL gemacht (Build 132 und 138): beim Erweitern
    # eines Kommentarblocks blieb ein zweites "*/" stehen. CSS-Kommentare
    # schachteln NICHT - nach dem ersten "*/" lief die weitere Prosa als CSS,
    # und der Parser verwarf die folgende Regel STILLSCHWEIGEND. Beide Male
    # fiel es nur auf, weil eine Live-Messung die Regel vermisste; im
    # Quelltext sieht so etwas voellig harmlos aus.
    # Deshalb dieser Waechter: jeder Kommentar muss genau EIN Ende haben.
    import re
    quelle = _oberflaeche_html()
    css = re.search(r"<style>(.*?)</style>", quelle, re.S).group(1)
    fehler = []
    for m in re.finditer(r"/\*(.*?)\*/", css, re.S):
        if "*/" in m.group(1):
            fehler.append(m.group(1)[:70])
    assert not fehler, ("CSS-Kommentar mit mehreren Enden — die Regel danach "
                        "wird verworfen: " + str(fehler))
    # Und die Zahl der Oeffner muss zur Zahl der Schliesser passen.
    assert css.count("/*") == css.count("*/"), \
        f"Unpaarige CSS-Kommentare: {css.count('/*')} Oeffner, {css.count('*/')} Schliesser"


def test_zuletzt_geoeffnetes_fenster_liegt_oben():
    # JB: "Wenn ich auf Namensbaukasten gehe, dann ist das geoeffnete Fenster
    # hinter dem Optionen-Fenster. Sollten nicht neu geoeffnete Fenster ueber
    # dem restlichen sein?" - Ja. Wurzel: die Ebenen waren STATISCH und
    # willkuerlich verteilt (.abo-flyout 900, .modal 5000, .panelmenu 6000,
    # .itemmenu 9000). Der Namens-Baukasten ist ein .abo-flyout und lag damit
    # zwangslaeufig unter dem Optionen-Menue - unabhaengig davon, was zuerst
    # geoeffnet wurde.
    # Regel: beim Oeffnen zaehlt eine gemeinsame Funktion die Ebene hoch.
    quelle = _oberflaeche_html()
    assert "function nachVorn" in quelle, "Keine Funktion, die ein Fenster nach vorn holt"
    i = quelle.index("function nachVorn")
    block = quelle[i:i + 400]
    assert "zIndex" in block, "nachVorn setzt keine Ebene"
    # Und sie muss beim Oeffnen der Fenster auch gerufen werden.
    # popoverBei deckt alle Menues ab; die Flyout-Fenster holen sich beim
    # Anhaengen selbst nach vorn (5 Stellen). Beides pruefen.
    j = quelle.index("function popoverBei")
    assert "nachVorn" in quelle[j:j + 700], "popoverBei holt das Menue nicht nach vorn"
    assert quelle.count("appendChild(fly); nachVorn(fly)") >= 4, (
        "Nicht alle Flyout-Fenster holen sich nach vorn")


def test_schwebende_flaechen_werden_nicht_unendlich_gross():
    # JB: "sie sollten auch eine Standardgroesse haben, nicht unendlich gross
    # werden wenn ich Vollbild auf einem Ultrawide stelle."
    # imBlick koppelt die Hoechstmasse an die Position (Anti-Scroll-Regel) -
    # auf einem 3440-px-Schirm ergibt das ein 3000 px breites Menue. Es
    # braucht zusaetzlich eine absolute Obergrenze.
    import re
    quelle = _oberflaeche_html()
    i = quelle.index("function imBlick")
    block = quelle[i:i + 2200]
    assert "MAX_FLY" in block, "Keine Obergrenze fuer schwebende Flaechen"
    assert "Math.min(" in block, "Die Obergrenze wird nicht mit dem Platz verrechnet"
    m = re.search(r"MAX_FLY\s*=\s*\{\s*b\s*:\s*(\d+)\s*,\s*h\s*:\s*(\d+)", quelle)
    assert m, "MAX_FLY ist nicht als Breite/Hoehe definiert"
    assert 600 <= int(m.group(1)) <= 1400, "Unplausible Hoechstbreite"


def test_plinfo_meldungen_verfallen():
    # JB: "Man sieht 'Eric Clapton - Tears in' eingereiht (3 Titel) dauerhaft,
    # bei F5 ist es verschwunden, war da etwas stuck?" - Nein: die Meldung
    # wurde gesetzt und NIE zurueckgenommen. Ereignis-Meldungen brauchen ein
    # Verfallsdatum; Fortschritts-Meldungen ("laeuft noch") duerfen bleiben.
    quelle = _oberflaeche_html()
    assert "function plInfo" in quelle, "Keine zentrale Stelle fuer die Info-Zeile"
    i = quelle.index("function plInfo")
    block = quelle[i:i + 700]
    assert "setTimeout" in block, "Ereignis-Meldungen verfallen nicht"
    assert "bleibt" in block, "Fortschritts-Meldungen koennen nicht bestehen bleiben"


def test_umbenennen_zieht_den_titel_nach():
    # JB: "dateinamen sind jetzt umbenannt, doch in der bibliothek nicht.
    # Warum?" - Weil das Umbenennen nur `pfad` und `name` aktualisierte. Die
    # Bibliothek zeigt aber `titel`, und der blieb der rohe YouTube-Titel.
    # Der Dateiname ist die Wahrheit, die JB sieht - die Anzeige muss ihm
    # folgen. Der Original-Titel geht dabei NICHT verloren (titel_orig),
    # denn er ist die Grundlage fuer Suche und Tagging.
    import inspect
    quelle = inspect.getsource(app.migration_anwenden)
    assert 'e["titel"]' in quelle, "Der Titel wird beim Umbenennen nicht nachgezogen"
    assert "titel_orig" in quelle, "Der urspruengliche Titel wird nicht gesichert"


def test_musikvideos_gelten_als_musik():
    # JB: "Es sind zwar Videos, aber es sind Videos von Liedern. Ich finde da
    # sollte es so gelten." Vorher pruefte _ist_musik nur auf Audio-Dateien,
    # also lief das Auto-Tagging fuer Musikvideos (MP4) nie.
    ist = app._ist_musik
    # Audio bleibt Musik.
    assert ist({"name": "lied.mp3"})
    assert ist({"kategorie": "MP3", "name": "x.m4a"})
    # Musikvideos: VEVO/-Topic-Kanaele und das "Kuenstler - Titel"-Muster.
    assert ist({"name": "Gary Moore - Still Got The Blues (Live).mp4",
                "kategorie": "Video"})
    assert ist({"name": "irgendwas.mp4", "uploader": "ElthonJohnVEVO"})
    assert ist({"name": "irgendwas.mp4", "uploader": "Nirvana - Topic"})
    # Ein normales Video ohne diese Merkmale bleibt aussen vor - sonst
    # befragt die App MusicBrainz zu jedem Let's Play.
    assert not ist({"name": "Why WoW Classic Will Be PERFECT.mp4",
                    "kategorie": "Video", "uploader": "Asmongold TV"})
    assert not ist({"name": "urlaub2019.mp4", "kategorie": "Video"})


def test_mehrere_titel_in_den_player_ziehen():
    # JB: "wenn ich vier markiert habe und die alle in den player ziehe, dann
    # ist nur eins davon in der playlist."
    # Wurzel: plMediaDrop/cmdNowDrop lasen nur EINEN Key aus dem Zug. Die
    # Mehrfachauswahl reiste nicht mit - anders als beim Wurf auf die
    # Playlist-Auswahl, wo plZiehKeys() das laengst richtig macht. Beide
    # Wege muessen dieselbe Funktion benutzen, sonst laufen sie auseinander.
    quelle = _oberflaeche_html()
    for fn in ("plMediaDrop", "cmdNowDrop"):
        i = quelle.index("function " + fn)
        block = quelle[i:i + 900]
        assert "plZiehKeys" in block, f"{fn} nimmt die Mehrfachauswahl nicht mit"
        assert "getData('ytdl/key')" not in block, \
            f"{fn} liest weiterhin nur einen einzelnen Key"


def test_titel_abgleich_holt_umbenannte_nach():
    # JB: "Was ist jetzt mit z.B. Rocky Mountain High in der Bibliothek, ich
    # seh immer noch nicht die geordneten titel."
    # Der Fix aus Build 140 greift nur beim NAECHSTEN Umbenennen. Was schon
    # umbenannt auf der Platte liegt, trug in der DB weiter den alten Titel.
    # Der Abgleich zieht das einmalig nach - nicht-destruktiv, der
    # Original-Titel wird gesichert.
    import inspect
    quelle = inspect.getsource(app)
    assert "def titel_abgleich" in quelle, "Kein Abgleich fuer bereits umbenannte Dateien"
    i = quelle.index("def titel_abgleich")
    block = quelle[i:i + 1200]
    assert "titel_orig" in block, "Der urspruengliche Titel wird nicht gesichert"
    assert "_titel_aus_name" in block, "Der Titel wird nicht aus dem Dateinamen gebildet"


def test_zieh_anfasser_zeigt_die_anzahl():
    # JB: "wenn ich die dateien ziehe und ich mehrere angewaehlt habe ... dann
    # sehe ich nur den ersten track ... da sollte dann stattdessen so etwas
    # wie: 8 ausgewaehlte tracks stehen."
    # Windows stapelt die Symbole und legt ein Zaehler-Abzeichen darauf,
    # macOS ebenso mit rotem Abzeichen - gemeinsam ist beiden: die ANZAHL
    # steht dran. Genau das fehlte; der Anfasser zeigte immer nur den Titel,
    # den man zufaellig gegriffen hatte.
    quelle = _oberflaeche_html()
    i = quelle.index("function ziehTooltip")
    block = quelle[i:i + 900]
    assert "libAuswahl" in block, "Der Anfasser kennt die Auswahl nicht"
    assert "ausgewählt" in block or "ausgewaehlt" in block, \
        "Der Anfasser nennt die Anzahl nicht"


def test_klick_ins_leere_hebt_die_auswahl_auf():
    # JB: "wenn ich linksklick woanders hinsetze, dann hebt sich meine
    # auswahl nicht auf." Im Explorer raeumt ein Klick auf freie Flaeche die
    # Auswahl ab - hier blieb sie samt Bulk-Leiste stehen.
    quelle = _oberflaeche_html()
    i = quelle.index("function libBandStart")
    block = quelle[i:_funktionsende(quelle, i)]
    assert "libAuswahl.clear()" in block, \
        "Ein Klick auf freie Flaeche raeumt die Auswahl nicht ab"


def test_bulk_playlist_fragt_welche():
    # JB: "Wenn ich + Playlist anklicke, dann sollte die option kommen zu
    # welcher playlist ich die hinzufuegen soll."
    # Vorher verlangte es eine oben vorgewaehlte Liste und brach sonst mit
    # einer Meldung ab - man musste also erst woanders etwas einstellen.
    quelle = _oberflaeche_html()
    i = quelle.index("function bulkPlaylist")
    block = quelle[i:i + 900]
    assert "plOptionen" in block or "kmListe" in block, \
        "bulkPlaylist bietet keine Playlist-Auswahl an"
    assert "Bitte oben eine Playlist" not in block, \
        "bricht weiterhin ab, statt zu fragen"
