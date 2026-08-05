# -*- coding: utf-8 -*-
"""Sicherheitsnetz Film-Fundament (Doku/SYNC_FILME_SPEC.md, Plan
Doku/SYNC_FILME_PLAN.md). Kein Netz, keine Platte ausser tmp_path; alle
Jellyfin/TMDB/OMDb-Antworten sind Fakes — genau wie die Manga-Quellen-Tests."""
import json
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import filme  # noqa: E402

FAKE_AUTH = {"AccessToken": "GEHEIM-TOKEN", "User": {"Id": "u1"}}
FAKE_INFO = {"Version": "10.9.7"}
FAKE_ITEMS = {"Items": [
    {"Id": "f1", "Name": "Der Marsianer", "Type": "Movie", "ProductionYear": 2015,
     "Genres": ["Science-Fiction"], "OfficialRating": "FSK-12", "CommunityRating": 7.7,
     "RunTimeTicks": 84_600_000_000, "DateCreated": "2026-07-01T10:00:00Z",
     "ProviderIds": {"Imdb": "tt3659388", "Tmdb": "286217"},
     "ImageTags": {"Primary": "abc"},
     "MediaStreams": [{"Type": "Video", "Codec": "hevc"}, {"Type": "Audio", "Codec": "eac3"}],
     "UserData": {"PlaybackPositionTicks": 6_000_000_000, "Played": False}},
    {"Id": "s1", "Name": "Dark", "Type": "Series", "ProductionYear": 2017,
     "Genres": ["Drama"], "CommunityRating": 8.7, "ProviderIds": {"Tmdb": "70523"},
     "ImageTags": {}, "UserData": {"Played": True}},
]}
FAKE_TMDB = {"overview": "Astronaut strandet auf dem Mars.",
             "credits": {"cast": [{"name": "Matt Damon"}, {"name": "Jessica Chastain"}]},
             "recommendations": {"results": [{"id": 286217}, {"id": 157336}]}}
FAKE_OMDB = {"imdbRating": "8.0", "Metascore": "80",
             "Ratings": [{"Source": "Rotten Tomatoes", "Value": "91%"}]}


def _fake_http(antworten):
    """antworten: Liste (teil_der_url, status, json_objekt); gematcht per
    Teilstring. Unerwartete URL = Testfehler (nichts geht still ins Netz)."""
    def http(url, daten=None, kopf=None, timeout=15):
        for teil, status, obj in antworten:
            if teil in url:
                return status, json.dumps(obj).encode("utf-8")
        raise AssertionError("unerwartete URL: " + url)
    return http


def _einrichten(tmp_path, monkeypatch):
    filme.einrichten(str(tmp_path))
    filme._sitzung.clear()
    filme._fehlversuch_ts = 0.0
    monkeypatch.setattr(filme, "_zugang", lambda: {
        "url": "https://jelly.example", "benutzer": "JBK", "passwort": "pw"})


# ---------------------------------------------------------------- Task 1

def test_anmelden_und_abzug(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH),
        ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS),
    ]))
    r = filme.katalog_abzug()
    assert r["ok"] is True and r["anzahl"] == 2
    sp = filme.katalog_lesen()
    assert sp["server_version"] == "10.9.7"
    e = sp["eintraege"][0]
    assert e["titel"] == "Der Marsianer" and e["typ"] == "film"
    assert e["imdb"] == "tt3659388" and e["tmdb"] == "286217"
    assert e["laufzeit_min"] == 141 and e["video_codec"] == "hevc"
    assert e["position_s"] == 600 and e["gesehen"] is False
    assert sp["eintraege"][1]["typ"] == "serie"


def test_abzug_scheitert_spiegel_bleibt(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH),
        ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    assert filme.katalog_abzug()["ok"] is True
    filme._sitzung.clear()
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 500, {})]))
    r = filme.katalog_abzug()
    assert r["ok"] is False
    assert len(filme.katalog_lesen()["eintraege"]) == 2, "Alter Spiegel muss stehen bleiben"
    # Backoff (Selbstheilungs-Regel): nach dem Fehlschlag darf der 5-s-Ticker
    # NICHT sofort den naechsten Abzug anstossen - sonst haemmert er in
    # Dauerschleife auf Renés Server ein (live fast passiert am 05.08.).
    assert filme.sync_faellig(alter_s=0) is False, "Fehlschlag ohne Backoff"
    filme._fehlversuch_ts = 0.0
    assert filme.sync_faellig(alter_s=0) is True


def test_ohne_zugang_ehrlich(tmp_path, monkeypatch):
    filme.einrichten(str(tmp_path))
    filme._sitzung.clear()
    monkeypatch.setattr(filme, "_zugang", lambda: None)
    r = filme.katalog_abzug()
    assert r["ok"] is False and "Keyring" in r["fehler"]


# ---------------------------------------------------------------- Task 2

def test_sync_faellig(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    assert filme.sync_faellig() is True          # noch nie gezogen
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH),
        ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    assert filme.sync_faellig() is False         # frisch
    assert filme.sync_faellig(alter_s=0) is True  # sofort wieder faellig


def test_routen_verkabelt():
    quelle = open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    assert "/api/filme/katalog" in quelle and "/api/filme/sync" in quelle
    assert "filme.einrichten(DATEN_DIR)" in quelle
    assert "filme_sync_pruefen()" in quelle, "6-h-Haken fehlt in ticker_schleife"


# ---------------------------------------------------------------- Task 3

def test_bild_cache(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO)]))
    abrufe = []
    echt = filme._http

    def http(url, **kw):
        if "/Images/" in url:
            abrufe.append(url)
            return 200, b"JPEGDATEN"
        return echt(url, **kw)
    monkeypatch.setattr(filme, "_http", http)
    assert filme.bild_holen("f1") == b"JPEGDATEN"
    assert filme.bild_holen("f1") == b"JPEGDATEN"
    assert len(abrufe) == 1, "Zweiter Abruf muss aus dem Platten-Cache kommen"
    assert filme.bild_holen("../boese") is None, "Pfad-Ausbruch verboten"


# ---------------------------------------------------------------- Task 4

def test_detail_anreicherung(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    monkeypatch.setattr(filme, "_meta_keys", lambda: {"tmdb": "T", "omdb": "O"})
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, FAKE_TMDB),
        ("omdbapi.com", 200, FAKE_OMDB)]))
    d = filme.detail("f1")
    assert d["titel"] == "Der Marsianer"
    assert d["cast"] == ["Matt Damon", "Jessica Chastain"]
    assert d["imdb_rating"] == "8.0" and d["tomatometer"] == "91%"
    # Zweiter Abruf: alles aus dem Cache (der Fake wuerde sonst zuschlagen)
    monkeypatch.setattr(filme, "_http", _fake_http([]))
    assert filme.detail("f1")["metacritic"] == "80"
    assert filme.detail("gibtsnicht") is None


# ---------------------------------------------------------------- Task 5

def test_reihen(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    r = filme.reihen()
    assert [e["id"] for e in r["weiterschauen"]] == ["f1"]
    assert r["top"][0]["id"] == "s1"                 # 8.7 vor 7.7
    assert "Science-Fiction" in r["genres"]
    assert r["neu"][0]["id"] == "f1"                 # einziger mit DateCreated


# ---------------------------------------------------------------- Task 6

def test_play_und_fortschritt_queue(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO)]))
    url = filme.stream_url("f1")
    assert url and "/Videos/f1/stream" in url and "GEHEIM-TOKEN" in url
    # Ausfall => Queue statt Verlust:
    monkeypatch.setattr(filme, "_http", _fake_http([]))  # jede URL knallt
    assert filme.fortschritt("f1", 623) is False
    q = json.load(open(filme._pfade["queue"], encoding="utf-8"))
    assert q[0]["item"] == "f1" and q[0]["position_s"] == 623
    # Netz wieder da => nachreichen, Queue leer:
    monkeypatch.setattr(filme, "_http", _fake_http([("Sessions/Playing", 204, {})]))
    assert filme.fortschritt("f1", 700) is True
    assert filme.fortschritt_nachreichen() == 1
    assert json.load(open(filme._pfade["queue"], encoding="utf-8")) == []


# ---------------------------------------------------------------- Task 7

def test_kein_token_in_antworten(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    for antwort in (filme.katalog_lesen(), filme.reihen()):
        blob = json.dumps(antwort)
        assert "GEHEIM-TOKEN" not in blob
        assert "jelly.example" not in blob, "Renés Adresse gehoert nicht in Antworten"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))


def test_token_invalidiert_einmal_neu_anmelden(tmp_path, monkeypatch):
    # Live gefunden 05.08.: Jellyfin wirft das alte Token weg, sobald sich
    # dieselbe DeviceId neu anmeldet (zweite Sitzung). Selbstheilung: bei 401
    # EINMAL frisch anmelden und wiederholen - sonst landet jede Meldung
    # faelschlich in der Queue und der Abzug scheitert dauerhaft.
    _einrichten(tmp_path, monkeypatch)
    ablauf = []

    def http(url, daten=None, kopf=None, timeout=15):
        ablauf.append(url.split("/")[-1].split("?")[0])
        if "AuthenticateByName" in url:
            return 200, json.dumps(FAKE_AUTH).encode()
        if "/System/Info" in url:
            return 200, json.dumps(FAKE_INFO).encode()
        if "Sessions/Playing" in url:
            # erster Versuch: Token tot; nach der Neu-Anmeldung: angenommen
            if ablauf.count("Progress") == 1:
                return 401, b"{}"
            return 204, b""
        raise AssertionError("unerwartete URL: " + url)
    monkeypatch.setattr(filme, "_http", http)
    assert filme.fortschritt("f1", 42) is True, "401 muss geheilt werden, nicht in die Queue"
    assert ablauf.count("AuthenticateByName") == 2, "genau EINE Neu-Anmeldung"
    assert not os.path.exists(filme._pfade["queue"]), "nichts darf in der Queue landen"


FAKE_EPS = {"Items": [
    {"Id": "e2", "Name": "Zweite", "ParentIndexNumber": 1, "IndexNumber": 2,
     "UserData": {"PlaybackPositionTicks": 3_000_000_000}},
    {"Id": "e1", "Name": "Pilot", "ParentIndexNumber": 1, "IndexNumber": 1,
     "RunTimeTicks": 18_000_000_000, "UserData": {"Played": True}},
    {"Id": "e3", "Name": "Finale", "ParentIndexNumber": 2, "IndexNumber": 1,
     "UserData": {}},
]}


def test_episoden(tmp_path, monkeypatch):
    # JB-Go "weiter mit den serien episoden": ein Ruf liefert Staffel/Folge/
    # Seh-Stand; Sortierung Staffel->Folge (Jellyfin liefert ungeordnet).
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Shows/s1/Episodes", 200, FAKE_EPS)]))
    eps = filme.episoden("s1")
    assert [e["id"] for e in eps] == ["e1", "e2", "e3"], "Sortierung Staffel->Folge"
    assert eps[0]["gesehen"] is True and eps[0]["laufzeit_min"] == 30
    assert eps[1]["position_s"] == 300 and eps[1]["staffel"] == 1 and eps[1]["folge"] == 2
    assert filme.episoden("../boese") == [], "Pfad-Ausbruch verboten"


def test_merkliste(tmp_path, monkeypatch):
    # JB-Go "film watchlist": lokale Liste, Toggle, Reihe + gemerkt-Flag.
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    assert filme.merkliste_toggle("f1") is True
    assert filme.reihen()["merkliste"][0]["id"] == "f1"
    monkeypatch.setattr(filme, "_meta_keys", lambda: {"tmdb": "", "omdb": ""})
    assert filme.detail("f1")["gemerkt"] is True
    assert filme.merkliste_toggle("f1") is False, "zweiter Klick nimmt raus"
    assert filme.reihen()["merkliste"] == []


def test_merkliste_je_profil(tmp_path, monkeypatch):
    # Teilprojekt 3: jede Person hat ihre EIGENE Liste; der Altbestand
    # (nackte Liste aus Build 181) gehoert dem Standard-Profil.
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    with open(filme._pfade["merk"], "w", encoding="utf-8") as f:
        json.dump(["f1"], f)                        # Altformat
    assert filme.merkliste_lesen() == ["f1"], "Altbestand -> Standard-Profil"
    assert filme.merkliste_lesen("anna") == []
    assert filme.merkliste_toggle("s1", "anna") is True
    assert filme.merkliste_lesen("anna") == ["s1"]
    assert filme.merkliste_lesen() == ["f1"], "Profile duerfen sich nicht mischen"
    assert [e["id"] for e in filme.reihen("anna")["merkliste"]] == ["s1"]
    monkeypatch.setattr(filme, "_meta_keys", lambda: {"tmdb": "", "omdb": ""})
    assert filme.detail("s1", "anna")["gemerkt"] is True
    assert filme.detail("s1")["gemerkt"] is False


def _fake_seerr(antworten, mitschrift=None):
    """Wie _fake_http, aber mit Set-Cookie-Rueckgabe (Seerr-Sitzung)."""
    def http(url, daten=None, kopf=None, timeout=20):
        if mitschrift is not None:
            mitschrift.append((url, daten, dict(kopf or {})))
        for teil, status, obj, keks in antworten:
            if teil in url:
                return status, json.dumps(obj).encode("utf-8"), keks
        raise AssertionError("unerwartete Seerr-URL: " + url)
    return http


FAKE_SEERR_SUCHE = {"results": [
    {"mediaType": "movie", "id": 438631, "title": "Dune", "releaseDate": "2021-09-15",
     "posterPath": "/dune.jpg", "mediaInfo": {"status": 5}},
    {"mediaType": "tv", "id": 90228, "name": "Dune: Prophecy",
     "firstAirDate": "2024-11-17", "mediaInfo": {"status": 4}},
    {"mediaType": "movie", "id": 111, "title": "Wuenschbar", "releaseDate": "2020-01-01"},
    {"mediaType": "person", "id": 999, "name": "Kein Titel"},
]}


def test_seerr_suche_und_anfrage(tmp_path, monkeypatch):
    # Teilprojekt 4: Anmeldung mit dem Jellyfin-Konto, Status-Mapping,
    # Serien-Anfrage mit allen Staffeln, 409 = ehrliche Meldung.
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_seerr_url", lambda: "https://seerr.example")
    filme._seerr["cookie"] = ""
    schrift = []
    monkeypatch.setattr(filme, "_seerr_http", _fake_seerr([
        ("auth/jellyfin", 200, {"username": "JBK"}, "connect.sid=abc; Path=/"),
        ("/search", 200, FAKE_SEERR_SUCHE, ""),
        ("/request?take", 200, {"results": [
            {"status": 2, "media": {"tmdbId": 286217, "mediaType": "movie", "status": 3}}]}, ""),
    ], schrift))
    t = filme.seerr_suche("Dune")
    assert [x["status"] for x in t] == ["da", "teils", ""]
    assert t[0]["poster"].startswith("https://image.tmdb.org/t/p/w300/")
    assert t[1]["typ"] == "serie" and t[1]["jahr"] == "2024"
    assert all(x["typ"] != "person" for x in t), "Personen fliegen raus"
    # Cookie kam aus der Anmeldung und geht bei der Suche mit:
    assert any("connect.sid=abc" in (k.get("Cookie") or "") for _, _, k in schrift)
    # Meine Wuensche: Titel aus dem eigenen Katalog, wenn schon gespiegelt
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    w = filme.seerr_meine()
    assert w[0]["titel"] == "Der Marsianer" and w[0]["status"] == "kommt"
    # Anfrage: Serie -> seasons all; 409 -> ehrlich
    monkeypatch.setattr(filme, "_seerr_http", _fake_seerr([
        ("/api/v1/request", 201, {}, "")], schrift))
    assert filme.seerr_anfragen(90228, "serie")["ok"] is True
    assert schrift[-1][1]["seasons"] == "all" and schrift[-1][1]["mediaType"] == "tv"
    monkeypatch.setattr(filme, "_seerr_http", _fake_seerr([
        ("/api/v1/request", 409, {}, "")]))
    r = filme.seerr_anfragen(438631, "film")
    assert r["ok"] is False and "Schon angefragt" in r["fehler"]


def test_seerr_sitzung_heilt(tmp_path, monkeypatch):
    # Abgelaufene Sitzung (403) wird EINMAL frisch angemeldet - wie die
    # Jellyfin-Token-Heilung.
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_seerr_url", lambda: "https://seerr.example")
    filme._seerr["cookie"] = "connect.sid=ALT"
    lauf = {"n": 0}

    def http(url, daten=None, kopf=None, timeout=20):
        if "auth/jellyfin" in url:
            return 200, b"{}", "connect.sid=NEU; Path=/"
        lauf["n"] += 1
        if "connect.sid=ALT" in (kopf or {}).get("Cookie", ""):
            return 403, b"{}", ""
        return 200, json.dumps({"results": []}).encode(), ""
    monkeypatch.setattr(filme, "_seerr_http", http)
    assert filme.seerr_suche("x") == []
    assert lauf["n"] == 2, "genau ein Heilungs-Versuch mit frischer Sitzung"
