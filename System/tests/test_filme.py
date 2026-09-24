# -*- coding: utf-8 -*-
"""Sicherheitsnetz Film-Fundament (Doku/SYNC_FILME_SPEC.md, Plan
Doku/SYNC_FILME_PLAN.md). Kein Netz, keine Platte ausser tmp_path; alle
Jellyfin/TMDB/OMDb-Antworten sind Fakes — genau wie die Manga-Quellen-Tests."""
import json
import os
import re
import sys
import time

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


BASIS = "https://jelly.example"
# Ohne Anmeldung erreichbar — alles andere will ein Token sehen.
FREI = ("/Users/AuthenticateByName", "/System/Info/Public")


def _token_im_kopf(kopf, server="12"):
    """Welches Token ein Jellyfin dieser Version in den Köpfen FINDET.

    Jellyfin 12 (Renés Server seit dem Update zwischen 20.09. und 24.09.2026)
    liest es nur aus `Authorization: MediaBrowser …, Token="…"`; der alte Kopf
    `X-Emby-Token` zählt dort nicht mehr. Jellyfin 10.11 (der Vorgänger) liest in
    dieser Attrappe nur `X-Emby-Token` — damit ist die Gegenprobe scharf, dass der
    Übergang auch zu einem älteren Server trägt."""
    kopf = kopf or {}
    if server == "10.11":
        return kopf.get("X-Emby-Token") or ""
    m = re.search(r'Token="([^"]*)"', kopf.get("Authorization") or "")
    return m.group(1) if m else ""


def _fake_http(antworten, server="12", mitschrift=None):
    """antworten: Liste (teil_der_url, status, json_objekt); gematcht per
    Teilstring. Unerwartete URL = Testfehler (nichts geht still ins Netz).

    Die Attrappe wertet die Köpfe AUS (Lehrbuch L19: die Attrappe muss den
    Unterschied modellieren). Bis 24.09.2026 ignorierte sie `kopf` — und darum
    blieb für jeden Test unsichtbar, dass Renés Server nach dem Update auf
    Jellyfin 12.1.0 jeden Datenabruf mit 401 ablehnte, der das Token nur im alten
    Kopf trug. Gültig sind GEHEIM-TOKEN (die Sitzung überlebt in den Tests den
    Tausch der Attrappe) und die Tokens der Anmelde-Antworten dieser Liste."""
    gueltig = {FAKE_AUTH["AccessToken"]}
    gueltig.update(obj["AccessToken"] for teil, _st, obj in antworten
                   if "AuthenticateByName" in teil and isinstance(obj, dict)
                   and obj.get("AccessToken"))

    def http(url, daten=None, kopf=None, timeout=15):
        if mitschrift is not None:
            mitschrift.append((url, dict(kopf or {})))
        if url.startswith(BASIS) and not any(f in url for f in FREI):
            if _token_im_kopf(kopf, server) not in gueltig:
                return 401, b""
        for teil, status, obj in antworten:
            if teil in url:
                return status, json.dumps(obj).encode("utf-8")
        raise AssertionError("unerwartete URL: " + url)
    return http


class JellyfinAttrappe:
    """Ein Jellyfin mit Gedächtnis: stellt je Anmeldung ein NEUES Token aus, und
    wie das echte gilt je DeviceId nur das zuletzt ausgestellte.

    version:          '12' (Token nur im Authorization-Kopf) oder '10.11'.
    anmeldung:        Status von AuthenticateByName (401 = Passwort, 403 = Drossel).
    lehnt_ab:         jedes Token wird abgelehnt, auch das frische (so sähe ein
                      künftiger Kopf-Wechsel aus: Anmeldung 200, Abruf 401).
    entwerte_ersten:  der erste Datenabruf entwertet Token 1 (eine zweite Sitzung
                      mit derselben DeviceId hat sich angemeldet).
    antworten:        Liste (teil_des_pfads, status, obj|bytes).
    Jeder Ruf landet in `rufe` als (pfad, kopf, daten)."""

    def __init__(self, version="12", anmeldung=200, lehnt_ab=False,
                 entwerte_ersten=False, antworten=None, public_version="12.1.0"):
        self.version, self.anmeldung, self.lehnt_ab = version, anmeldung, lehnt_ab
        self.entwerte_ersten = entwerte_ersten
        self.public_version = public_version
        self.antworten = antworten if antworten is not None else STANDARD_ANTWORTEN
        self.tokens, self.rufe, self.entwertet = [], [], set()

    def anmeldungen(self):
        return sum(1 for p, _k, _d in self.rufe if p.startswith(FREI[0]))

    def datenrufe(self):
        return [(p, k) for p, k, _d in self.rufe if not p.startswith(FREI)]

    def __call__(self, url, daten=None, kopf=None, timeout=15):
        assert url.startswith(BASIS), "nur Renés (Attrappen-)Server: " + url
        pfad, kopf = url[len(BASIS):], dict(kopf or {})
        self.rufe.append((pfad, kopf, daten))
        if pfad.startswith(FREI[0]):
            if self.anmeldung != 200:
                return self.anmeldung, b""
            self.tokens.append(f"TOKEN-{len(self.tokens) + 1}")
            return 200, json.dumps({"AccessToken": self.tokens[-1],
                                    "User": {"Id": "u1"}}).encode()
        if pfad.startswith(FREI[1]):
            return 200, json.dumps({"Version": self.public_version}).encode()
        tok = _token_im_kopf(kopf, self.version)
        if (self.lehnt_ab or not self.tokens or tok != self.tokens[-1]
                or tok in self.entwertet):
            return 401, b""
        if (self.entwerte_ersten and not self.entwertet
                and not pfad.startswith("/System/Info")):
            self.entwertet.add(tok)
            return 401, b""
        for teil, status, obj in self.antworten:
            if teil in pfad:
                return status, obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        raise AssertionError("unerwarteter Pfad: " + pfad)


def _einrichten(tmp_path, monkeypatch):
    filme.einrichten(str(tmp_path))
    filme._sitzung.clear()
    filme._fehlversuch_ts = 0.0
    filme._anmelde_sperre_ts = 0.0         # Anmelde-Backoff nie zwischen Tests
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
    # Backoff abgelaufen: Seit 24.09. steht die Stufe in filme_zustand.json
    # (übersteht den Selbst-Neustart) — also dort 31 Minuten zurückdrehen,
    # nicht nur den Prozess-Merker löschen.
    filme._fehlversuch_ts = 0.0
    filme.fam.json_aendern(filme._pfade["zustand"], lambda d: d.__setitem__(
        "letzter_versuch", d["letzter_versuch"] - 31 * 60))
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
    monkeypatch.setattr(filme, "_meta_keys", lambda: {})   # kein TMDB im Test
    r = filme.reihen()
    assert [e["id"] for e in r["weiterschauen"]] == ["f1"]
    # Top (JB): Gesehenes fliegt raus - s1 (8.7) ist gesehen, f1 fuehrt.
    assert r["top"][0]["id"] == "f1"
    # Seit 13.08.2026 werden Sprach-/Schreibvarianten zusammengeführt: Renés
    # echte Bibliothek taggt zweisprachig, „Science-Fiction" und „Science
    # Fiction" (ebenso Comedy/Komödie, neun Paare) standen als getrennte Reihen
    # nebeneinander. Die Attrappe nutzt die Bindestrich-Schreibweise, die Reihe
    # heißt jetzt einheitlich wie der Anzeigename.
    assert "Science Fiction" in r["genres"]
    assert "Science-Fiction" not in r["genres"]
    assert r["neu"][0]["id"] == "f1"                 # einziger mit DateCreated


def test_top_bayes(tmp_path, monkeypatch):
    # JB-Go 06.08. („Bei top mach so etwas wie einen bayes score"): Jellyfin
    # hat keinen Vote-Count, also eicht TMDB - ein Film mit 8000 Stimmen
    # (8.0) schlaegt das Ein-Stimmen-Artefakt (10.0, keine TMDB-Id), das am
    # Prior 6.8 haengen bleibt. Beim ZWEITEN Lauf kommt alles aus dem Cache.
    _einrichten(tmp_path, monkeypatch)
    items = {"Items": [
        dict(FAKE_ITEMS["Items"][0],
             UserData={"PlaybackPositionTicks": 0, "Played": False}),
        {"Id": "x9", "Name": "Geisterwertung", "Type": "Movie",
         "CommunityRating": 10.0, "Genres": [], "ProviderIds": {},
         "ImageTags": {}, "UserData": {"Played": False}},
    ]}
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, items)]))
    filme.katalog_abzug()
    monkeypatch.setattr(filme, "_meta_keys", lambda: {"tmdb": "K"})
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("themoviedb.org/3/movie/286217", 200,
         {"vote_count": 8000, "vote_average": 8.0})]))
    r = filme.reihen()
    assert [e["id"] for e in r["top"][:2]] == ["f1", "x9"], \
        "Bayes muss die belegte 8.0 vor die unbelegte 10.0 setzen"
    # Zweiter Lauf: KEIN Netz mehr noetig (Stimmen-Cache).
    monkeypatch.setattr(filme, "_http", _fake_http([]))
    assert filme.reihen()["top"][0]["id"] == "f1"


def test_anmelde_backoff_und_neuer_auth_kopf(tmp_path, monkeypatch):
    # Fund 06.08.: Renés Server-Update (10.9.7 -> 10.11.11) + Anmelde-Sturm
    # gleicher DeviceIds endeten in 403. (1) Beide Auth-Koepfe senden
    # (X-Emby-Authorization ist in 10.11 abgekuendigt); (2) nach 403 ist
    # 10 Minuten RUHE - kein weiterer Versuch hämmert die Sperre fest.
    _einrichten(tmp_path, monkeypatch)
    gesehen = {}

    def http(url, daten=None, kopf=None, timeout=15):
        gesehen.update(kopf or {})
        return 403, b"{}"
    monkeypatch.setattr(filme, "_http", http)
    assert filme._anmelden() is None
    assert "Authorization" in gesehen and "X-Emby-Authorization" in gesehen
    assert filme._anmelde_sperre_ts > filme.time.time() + 500   # ~10 min Sperre
    # Waehrend der Sperre: KEIN weiterer Netz-Versuch.
    monkeypatch.setattr(filme, "_http", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("Anmeldung trotz Backoff versucht")))
    assert filme._anmelden() is None


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

# Eine Folge mit echter Jellyfin-Id (32 Hex) — _folge_holen prüft die Form.
FOLGE_ID = "9f2c41ab7d3e40aab6c5e81d2f0a7c63"
FOLGE = {"Id": FOLGE_ID, "Name": "Geheimnisse", "Type": "Episode",
         "SeriesName": "Dark", "SeriesId": "s1", "ParentIndexNumber": 1,
         "IndexNumber": 1, "Genres": [], "RunTimeTicks": 30_600_000_000,
         "ProviderIds": {}, "ImageTags": {}, "UserData": {},
         "MediaStreams": [{"Type": "Video", "Codec": "h264", "Height": 1080}]}

# Was die JellyfinAttrappe auf Datenabrufe antwortet (Reihenfolge zählt:
# der Katalog-Pfad „/Users/u1/Items?" vor dem Einzel-Pfad „/Users/u1/Items/").
STANDARD_ANTWORTEN = [
    ("/System/Info", 200, {"Version": "12.1.0"}),
    ("/Users/u1/Items?", 200, FAKE_ITEMS),
    ("/Users/u1/Items/" + FOLGE_ID, 200, FOLGE),
    ("/Users/u1/Items/f1", 200, dict(FAKE_ITEMS["Items"][0], MediaStreams=[
        {"Type": "Video", "Codec": "hevc", "Height": 2160}])),
    ("/Images/", 200, b"JPEGDATEN"),
    ("/Shows/s1/Episodes", 200, FAKE_EPS),
    ("/Sessions/Playing/Progress", 204, b""),
    ("/PlayedItems/", 200, {}),
]


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


def test_detail_netflix_felder(tmp_path, monkeypatch):
    # Build 184: die Detailseite braucht Regie/Drehbuch/Tagline/Trailer
    # (TMDB) und Aufloesung/Ton-Kanaele+Sprachen/Untertitel (Jellyfin).
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items?", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    monkeypatch.setattr(filme, "_meta_keys", lambda: {"tmdb": "T", "omdb": ""})
    tmdb_voll = dict(FAKE_TMDB)
    tmdb_voll["tagline"] = "Angst ist der Verstandeskiller."
    tmdb_voll["credits"] = {"cast": [{"name": "Matt Damon"}],
                            "crew": [{"name": "Ridley Scott", "job": "Director"},
                                     {"name": "Drew Goddard", "job": "Screenplay"}]}
    tmdb_voll["videos"] = {"results": [
        {"site": "YouTube", "type": "Trailer", "key": "abc123", "name": "Trailer 1"},
        {"site": "Vimeo", "type": "Trailer", "key": "nein", "name": "falsche Seite"}]}
    jelly_voll = {"MediaStreams": [
        {"Type": "Video", "Codec": "hevc", "Height": 2160},
        {"Type": "Audio", "Codec": "eac3", "Channels": 6, "Language": "ger"},
        {"Type": "Audio", "Codec": "dts", "Channels": 8, "Language": "eng"},
        {"Type": "Subtitle", "Language": "ger"}, {"Type": "Subtitle", "Language": "eng"}]}
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, tmdb_voll),
        ("/Items/f1", 200, jelly_voll)]))
    d = filme.detail("f1")
    assert d["regie"] == ["Ridley Scott"] and d["drehbuch"] == ["Drew Goddard"]
    assert d["tagline"].startswith("Angst")
    assert d["trailer"] == [{"key": "abc123", "name": "Trailer 1"}], "nur YouTube"
    assert d["hoehe"] == 2160 and d["audio_kanaele"] == 8
    assert d["audio_sprachen"] == ["ger", "eng"] and d["sub_sprachen"] == ["ger", "eng"]


def test_live_tv_parser(tmp_path):
    import live_tv
    live_tv.einrichten(str(tmp_path))
    m3u = ('#EXTM3U\n'
           '#EXTINF:-1 tvg-logo="https://l/ard.png" group-title="Hauptsender",Das Erste\n'
           'https://s/ard/master.m3u8\n'
           '#EXTINF:-1 group-title="Regional",WDR\n'
           'https://s/wdr.m3u8\n'
           '# Kommentar\n')
    k = live_tv.m3u_parsen(m3u)
    assert k[0] == {"name": "Das Erste", "logo": "https://l/ard.png",
                    "gruppe": "Hauptsender", "url": "https://s/ard/master.m3u8"}
    assert k[1]["gruppe"] == "Regional" and k[1]["logo"] == ""


def test_snippet_baecker(tmp_path, monkeypatch):
    # JB-Go Hover-Snippet: deterministisch bei 27% Laufzeit, still bei Fehlern.
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    rufe = []

    def fake_run(cmd, **kw):
        rufe.append(cmd)
        with open(cmd[-1], "wb") as f:               # letztes Arg = tmp-Datei
            f.write(b"0" * 20000)
        class R: pass
        return R()
    import subprocess
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert filme.snippet_backen("f1") is True
    cmd = rufe[0]
    assert cmd[cmd.index("-ss") + 1] == str(int(141 * 60 * 0.27)), "27% der Laufzeit"
    assert "-an" in cmd and "6" in cmd, "6 s, stumm"
    assert filme.snippet_lesen("f1"), "fertiges Snippet muss lesbar sein"
    assert filme.snippet_backen("f1") is False, "zweites Backen ist ein No-op"
    assert filme.snippet_lesen("gibtsnicht") is None


def test_ausfall_bleibt_nicht_still(tmp_path, monkeypatch):
    """Ein gescheiterter Abzug muss auf der Platte landen — und sichtbar werden.

    Der Ausfall vom 06.–13.08.2026 lief SIEBEN TAGE, ohne dass irgendetwas davon
    erzählt hat: `katalog_abzug()` gab `{"ok": False, "fehler": …}` sauber
    zurück, aber beide Aufrufstellen warfen den Rückgabewert weg
    (`youtube_app.py` Ticker + Sync-Route). Es gab keine Film-Karte im Dashboard,
    kein Banner, keinen Leer-Hinweis. Das gute Ausfall-Verhalten — der Spiegel
    steht bei Serverausfall bewusst weiter — hat den Ausfall damit unsichtbar
    gemacht: ein alter Spiegel sah exakt aus wie ein frischer.

    Wurzel-Lösung: Der Ausgang wird IM Abzug festgehalten, nicht beim Aufrufer,
    und auf Platte, weil die App sich bei jeder Code-Änderung selbst neu startet
    und ein Prozess-Merker dabei vergisst."""
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    assert filme.katalog_abzug()["ok"]
    z = filme.zustand()
    da = z["anzahl"]
    assert da > 0 and not z["fehler"] and z["fehlversuche"] == 0
    assert z["still_seit_s"] < 60, "nach einem Erfolg darf nichts 'still' sein"

    # Jetzt sperrt der Server (403 wie am 06.08.) — Prozess-Zustand zurücksetzen,
    # damit die Anmeldung wirklich neu versucht wird.
    filme._sitzung.clear()
    filme._anmelde_sperre_ts = 0.0
    monkeypatch.setattr(filme, "_http", lambda *a, **k: (403, b"{}"))
    erg = filme.katalog_abzug()
    assert not erg["ok"]
    z = filme.zustand()
    assert z["fehler"], "der Fehlschlag steht nirgends — genau das war der 7-Tage-Fehler"
    assert z["fehlversuche"] == 1
    assert z["anzahl"] == da, "der Spiegel muss stehen bleiben (Ausfall-Verhalten laut Spec)"

    # Und er überlebt den Prozess: frisch geladen ist er immer noch da.
    import importlib
    importlib.reload(filme)
    filme.einrichten(str(tmp_path))
    assert filme.zustand()["fehler"], "Zustand überlebt den Neustart nicht"

    # Zweiter Fehlschlag zählt hoch, ein Erfolg löscht alles wieder.
    filme._sitzung.clear()
    filme._anmelde_sperre_ts = 0.0
    monkeypatch.setattr(filme, "_http", lambda *a, **k: (403, b"{}"))
    filme.katalog_abzug()
    assert filme.zustand()["fehlversuche"] == 2
    filme._sitzung.clear()
    filme._anmelde_sperre_ts = 0.0
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    z = filme.zustand()
    assert not z["fehler"] and z["fehlversuche"] == 0


def test_folge_wird_direkt_bei_jellyfin_geholt(tmp_path, monkeypatch):
    """detail() findet auch Serien-FOLGEN — die stehen nie im Spiegel.

    Der Abzug holt bewusst nur `IncludeItemTypes=Movie,Series` (Renés Simpsons
    allein haben 553 Folgen). Bis 13.08.2026 gab `detail(folgen_id)` deshalb
    None, die Route antwortete 404 mit `{"fehler": …}` — und die Oberfläche las
    dieses Fehler-Objekt als gültige Meta. Für JB hieß das bei JEDER Folge:
    kein Titel, Dauer 0 (tote Zeitleiste) und immer die schwerste
    Transcode-Gangart, obwohl viele Folgen h264 sind."""
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    assert not any(e["typ"] == "folge" for e in filme.katalog_lesen()["eintraege"])

    # Echte Jellyfin-Id (32 Hex) — die Kurzform "ep1" der übrigen Attrappen
    # würde die ID-Form-Prüfung nicht passieren, und genau diese Prüfung soll
    # hier ja mitlaufen (L19: die Attrappe muss den Unterschied modellieren).
    EP = "9f2c41ab7d3e40aab6c5e81d2f0a7c63"
    folge = {"Id": EP, "Name": "Geheimnisse", "Type": "Episode",
             "SeriesName": "Dark", "SeriesId": "s1", "ParentIndexNumber": 1,
             "IndexNumber": 1, "ProductionYear": 2017, "Genres": [],
             "RunTimeTicks": 30_600_000_000, "ProviderIds": {},
             "MediaStreams": [{"Type": "Video", "Codec": "h264"},
                              {"Type": "Audio", "Codec": "ac3"}],
             "ImageTags": {}, "UserData": {}}
    monkeypatch.setattr(filme, "_meta_keys", lambda: {})
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items/" + EP, 200, folge)]))
    d = filme.detail(EP)
    assert d, "Folge wird nicht nachgeschlagen"
    assert d["titel"] == "Dark · S1 F1 — Geheimnisse", d["titel"]
    assert d["typ"] == "folge" and d["serie_id"] == "s1"
    assert d["laufzeit_min"] == 51, "ohne Dauer bleibt die Zeitleiste tot"
    assert d["video_codec"] == "h264", "ohne Codec wählt die Weiche immer den schwersten Weg"

    # Unsinnige Ids dürfen KEINEN Ruf an Renés Server auslösen
    def kein_ruf(*a, **k):
        raise AssertionError("unerlaubter Netz-Ruf")
    monkeypatch.setattr(filme, "_http", kein_ruf)
    for boese in ("", "../boese", "kurz", "a" * 200, "hallo welt"):
        assert filme._folge_holen(boese) is None, boese


def test_geteilter_zustand_geht_nicht_verloren(tmp_path, monkeypatch):
    """Merkliste und Fortschritts-Warteschlange überleben gleichzeitige Schreiber.

    Zwei belegte Verluste (13.08.2026), beide dasselbe Muster — Lesen, Ändern,
    Schreiben ohne Sperre:
    1. Merkliste: PC, Fernsehmodus und Handy schreiben in dieselbe Datei. Zwei
       gleichzeitige Herz-Klicks löschten nicht einen Eintrag, sondern den ganzen
       Profil-Schlüssel des anderen.
    2. Warteschlange: `fortschritt_nachreichen()` las die Liste, SENDETE (das
       dauert), und schrieb dann den Rest über den inzwischen aktuellen Stand.
       Wer in diesen Sekunden einen Film stoppte, verlor seinen Spot spurlos —
       und zwar bevorzugt während des 6-h-Abzugs, der mit genau diesem Nachreichen
       endet.

    Geprüft wird das ERGEBNIS unter echter Nebenläufigkeit, nicht die Schreibweise."""
    import threading
    _einrichten(tmp_path, monkeypatch)

    # --- 1) Merkliste: 24 gleichzeitige Klicks auf verschiedene Profile
    def klick(n):
        filme.merkliste_toggle(f"id{n:03d}", profil=("A" if n % 2 else "B"))
    faeden = [threading.Thread(target=klick, args=(n,)) for n in range(24)]
    for f in faeden:
        f.start()
    for f in faeden:
        f.join()
    a, b = filme.merkliste_lesen("A"), filme.merkliste_lesen("B")
    assert len(a) + len(b) == 24, f"Einträge verloren: A={len(a)} B={len(b)} (soll 24)"

    # --- 2) Warteschlange: während des Nachreichens kommen neue Meldungen dazu
    monkeypatch.setattr(filme, "_zugang", lambda: {
        "url": "https://jelly.example", "benutzer": "JBK", "passwort": "pw"})
    for n in range(5):                       # 5 liegengebliebene Meldungen
        fam_liste = {"item": f"alt{n}", "position_s": n, "gesehen": False, "ts": 100.0 + n}
        filme.fam.json_aendern(filme._pfade["queue"],
                               lambda q, m=fam_liste: (q or []) + [m], standard=[])
    assert len(filme._queue_lesen()) == 5

    dazwischen = threading.Event()

    def langsam_senden(item_id, position_s, gesehen=False, nur_gesehen=False):
        dazwischen.set()                     # Signal: das Senden läuft
        time.sleep(0.05)                     # …und dauert
        return filme.SENDE_OK
    # Seit 24.09. sendet das Nachreichen über den Weg MIT Grund (SENDE_*), damit
    # ein dauerhafter 4xx die Warteschlange nicht blockiert.
    monkeypatch.setattr(filme, "_fortschritt_senden_mit_grund", langsam_senden)
    monkeypatch.setattr(filme, "_http", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("kein Netz in diesem Test")))

    def stoerer():
        dazwischen.wait(2)
        time.sleep(0.02)
        filme.fam.json_aendern(               # JB stoppt mitten im Nachreichen einen Film
            filme._pfade["queue"],
            lambda q: (q or []) + [{"item": "GERADE_GESTOPPT", "position_s": 2520,
                                    "gesehen": False, "ts": 999.0}], standard=[])
    t = threading.Thread(target=stoerer)
    t.start()
    geschafft = filme.fortschritt_nachreichen()
    t.join()

    assert geschafft == 5
    rest = filme._queue_lesen()
    assert any(m["item"] == "GERADE_GESTOPPT" for m in rest), \
        "der Spot des gerade gestoppten Films wurde vom Nachreichen überschrieben"
    assert not any(m["item"].startswith("alt") for m in rest), \
        "erledigte Meldungen blieben liegen"


def test_nur_ein_abzug_gleichzeitig():
    """Sync-Knopf und 6-h-Ticker teilen sich EINE Sperre.

    Vorher hatte nur der Ticker eine; der Knopf startete blind einen zweiten
    Thread. Zwei Voll-Abzüge parallel gegen Renés Server sind bei 4885 Titeln
    zehn gleichzeitige 1000er-Seiten — und beide enden mit
    `fortschritt_nachreichen()`, das dann jede Meldung doppelt schickt."""
    import youtube_app as app
    quelle = open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    assert "def _filme_abzug_anstossen" in quelle
    i = quelle.index('elif self.path == "/api/filme/sync"')
    block = quelle[i:i + 600]
    assert "_filme_abzug_anstossen()" in block, "der Sync-Knopf umgeht die Sperre"
    assert "threading.Thread(target=filme.katalog_abzug" not in quelle, \
        "es gibt noch einen ungesperrten Abzug-Start"
    # Ergebnis statt Schreibweise: der zweite Anstoß muss abgelehnt werden
    gestartet = []
    echt = filme.katalog_abzug
    try:
        filme.katalog_abzug = lambda: (time.sleep(0.4), gestartet.append(1))[1]
        assert app._filme_abzug_anstossen() is True
        assert app._filme_abzug_anstossen() is False, "zwei Abzüge gleichzeitig möglich"
        time.sleep(0.6)
        assert app._filme_abzug_anstossen() is True, "Sperre wird nicht freigegeben"
        time.sleep(0.6)
    finally:
        filme.katalog_abzug = echt


def test_kein_anmelde_sturm_im_eigenen_prozess(tmp_path, monkeypatch):
    """Viele gleichzeitige Anfragen erzeugen EINE Anmeldung, nicht zwölf.

    Der Kommentar in `_anmelden` schrieb den 403 vom 06.08.2026 den
    „Zweitprozessen" zu. Nachgemessen am 13.08.: Der Sturm passt vollständig in
    EINEN Prozess. Der Fernsehmodus lädt dutzende Kacheln gleichzeitig, jede ruft
    `bild_holen`, alle sehen im selben Moment „kein Token" und melden sich an —
    und weil Jellyfin Tokens je DeviceId entwertet, bekommt jede vorherige
    Sitzung 401 und meldet sich WIEDER an. Diese Kaskade ist der plausibelste
    Erzeuger der Kontosperre, die Renés Server sieben Tage dicht hielt.

    Ohne diesen Wächter wäre der Fix ein Vorsatz: Er misst die Zahl der
    tatsächlichen Anmelde-Rufe unter echter Nebenläufigkeit."""
    import threading
    _einrichten(tmp_path, monkeypatch)
    anmeldungen = []

    def http(url, daten=None, kopf=None, timeout=15):
        if "AuthenticateByName" in url:
            anmeldungen.append(time.time())
            time.sleep(0.05)               # eine Anmeldung dauert
            return 200, json.dumps(FAKE_AUTH).encode()
        if "/System/Info" in url:
            return 200, json.dumps(FAKE_INFO).encode()
        if "/Images/" in url:
            return 200, b"JPEGDATEN"
        raise AssertionError("unerwartete URL: " + url)
    monkeypatch.setattr(filme, "_http", http)

    start = threading.Barrier(12)

    def kachel(n):
        start.wait()                       # alle zwölf gleichzeitig losreißen
        filme.bild_holen(f"{n:032x}")
    faeden = [threading.Thread(target=kachel, args=(n,)) for n in range(12)]
    for f in faeden:
        f.start()
    for f in faeden:
        f.join()
    assert len(anmeldungen) == 1, (
        f"{len(anmeldungen)} Anmeldungen fuer einen Bildschirm voller Kacheln — "
        "genau diese Kaskade hat Renes Server gesperrt")


# ------------------------------------------------ Jellyfin 12 (Befund 24.09.2026)

def test_jellyfin12_katalog_mit_token_im_authorization_kopf(tmp_path, monkeypatch):
    """Renés Server läuft seit dem Update (zwischen 20.09. 14:52 und 24.09. 14:20)
    auf Jellyfin 12.1.0. Die Anmeldung trug schon beide Kopf-Formen, jeder
    Datenabruf danach aber das Token nur im alten `X-Emby-Token`. Ergebnis live:
    51 Fehlversuche mit „Items-Abruf HTTP 401" — auch mit dem ganz frischen
    Token. SyncFindus lief gegen denselben Server durch, weil es das Token im
    `Authorization`-Kopf mitschickt. Mit dem alten Code liefert dieser Test genau
    den Live-Text."""
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12")
    monkeypatch.setattr(filme, "_http", jf)
    r = filme.katalog_abzug()
    assert r["ok"] is True, r["fehler"]
    assert r["anzahl"] == 2 and jf.anmeldungen() == 1
    # /System/Info braucht ebenfalls das Token — sonst stünde „?" im Spiegel.
    assert filme.katalog_lesen()["server_version"] == "12.1.0"


def test_jellyfin1011_gegenprobe_alter_kopf_traegt_weiter(tmp_path, monkeypatch):
    """Gegenprobe: ein Server, der nur `X-Emby-Token` liest, bleibt bedient."""
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("10.11")
    monkeypatch.setattr(filme, "_http", jf)
    r = filme.katalog_abzug()
    assert r["ok"] is True, r["fehler"]
    assert filme.episoden("s1") and filme.fortschritt("f1", 60) is True


def test_jeder_jellyfin_abruf_traegt_den_ganzen_ausweis(tmp_path, monkeypatch):
    """Wächter „Aufruf statt Erwähnung": jeder WIRKLICHE Ruf wird mitgeschrieben.

    Die Wurzel des Ausfalls: Beim 10.11-Update (06.08.) wurde der neue Kopf nur
    an der Anmeldung nachgezogen, eine gemeinsame Kopf-Funktion für alle Rufe
    gab es nie. Darum hier jeder Weg einmal: Katalog, Server-Version, Bild,
    Folgenliste, Detail-Technik, einzelne Folge, Fortschritt und „gesehen"."""
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12")
    monkeypatch.setattr(filme, "_http", jf)
    monkeypatch.setattr(filme, "_meta_keys", lambda: {})
    assert filme.katalog_abzug()["ok"]
    assert filme.bild_holen("f1") == b"JPEGDATEN"
    assert len(filme.episoden("s1")) == 3
    assert filme.detail("f1")["hoehe"] == 2160       # der Technik-Ruf kam durch
    assert filme.detail(FOLGE_ID)["hoehe"] == 1080   # _folge_holen + Technik-Ruf
    assert filme.fortschritt("f1", 2350, gesehen=True) is True
    tok = jf.tokens[-1]
    wege = set()
    for pfad, kopf, _d in jf.rufe:
        assert kopf.get("User-Agent", "").startswith("SyncYouTube"), (pfad, kopf)
        assert kopf.get("X-Emby-Authorization") == filme.GERAET_KOPF, (pfad, kopf)
        if pfad.startswith(FREI):
            assert "Token=" not in kopf.get("Authorization", ""), (pfad, kopf)
            continue
        assert kopf.get("Authorization") == filme.GERAET_KOPF + f', Token="{tok}"', (pfad, kopf)
        assert kopf.get("X-Emby-Token") == tok, (pfad, kopf)   # für ältere Server
        wege.add(re.sub(r"[0-9a-f]{32}|f1|s1|u1", "·", pfad.split("?")[0]))
    assert wege >= {"/System/Info", "/Users/·/Items", "/Items/·/Images/Primary",
                    "/Shows/·/Episodes", "/Users/·/Items/·", "/Sessions/Playing/Progress",
                    "/Users/·/PlayedItems/·"}, wege


def _wege_mit_heilung():
    """(Name, Aufruf, Prüfung) für jeden Weg, der ein entwertetes Token heilt."""
    return [
        ("katalog", lambda: filme.katalog_abzug(), lambda r: r["ok"]),
        ("bild", lambda: filme.bild_holen("f1"), lambda r: r == b"JPEGDATEN"),
        ("episoden", lambda: filme.episoden("s1"), lambda r: len(r) == 3),
        ("folge", lambda: filme._folge_holen(FOLGE_ID), lambda r: r and r["typ"] == "folge"),
        ("fortschritt", lambda: filme.fortschritt("f1", 42), lambda r: r is True),
        ("gesehen", lambda: filme.fortschritt("f1", 2350, True), lambda r: r is True),
    ]


def test_wiederholung_nach_neuanmeldung_baut_alle_koepfe_neu(tmp_path, monkeypatch):
    """Jellyfin entwertet Token 1 beim ersten Abruf (zweite Sitzung mit derselben
    DeviceId). Die Wiederholung muss Token 2 in ALLEN Köpfen tragen: ein altes
    Token im `Authorization`-Kopf überstimmt ein neues in `X-Emby-Token` — genau
    dieser Fehler steckt in SyncFindus' Stream-Proxy (Gegenprüfung 24.09.).
    `_folge_holen` hatte bis 24.09. gar keine Heilung: die Folge kam dann als
    „Film nicht gefunden" an."""
    for name, aufruf, pruefung in _wege_mit_heilung():
        _einrichten(tmp_path / name, monkeypatch)
        jf = JellyfinAttrappe("12", entwerte_ersten=True)
        monkeypatch.setattr(filme, "_http", jf)
        erg = aufruf()
        assert pruefung(erg), (name, erg)
        assert jf.anmeldungen() == 2, (name, jf.anmeldungen())
        letzter = jf.datenrufe()[-1][1]
        assert 'Token="TOKEN-2"' in letzter["Authorization"], (name, letzter)
        assert letzter["X-Emby-Token"] == "TOKEN-2", (name, letzter)


def test_frisches_token_eines_anderen_fadens_wird_nicht_verworfen(tmp_path, monkeypatch):
    """Nebenfund 24.09.: `_sitzung.clear()` stand AUSSERHALB der Anmelde-Sperre.

    Ein Faden mit veraltetem Token bekommt 401 — inzwischen hat sich ein anderer
    Faden längst frisch angemeldet. Der alte Code warf dessen frisches Token weg
    und meldete sich erneut an; wegen derselben DeviceId entwertete das den
    anderen Faden: genau die Kaskade vom 13.08. Richtig: nur das EIGENE,
    abgelehnte Token verwerfen, sonst das frische des anderen nehmen."""
    _einrichten(tmp_path, monkeypatch)
    filme._sitzung.update(token="ALT", user_id="u1", version="12.1.0")
    anmeldungen = []

    def http(url, daten=None, kopf=None, timeout=15):
        if "AuthenticateByName" in url:
            anmeldungen.append(url)
            return 200, json.dumps({"AccessToken": "DRITT", "User": {"Id": "u1"}}).encode()
        if "/System/Info" in url:
            return 200, b'{"Version": "12.1.0"}'
        tok = _token_im_kopf(kopf)
        if tok == "ALT":
            filme._sitzung.update(token="FRISCH")   # der andere Faden war schneller
            return 401, b""
        return (204, b"") if tok == "FRISCH" else (401, b"")
    monkeypatch.setattr(filme, "_http", http)
    assert filme.fortschritt("f1", 42) is True
    assert anmeldungen == [], "das frische Token des anderen Fadens wurde verworfen"
    assert filme._sitzung["token"] == "FRISCH"
