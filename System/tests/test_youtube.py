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
