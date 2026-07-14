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
