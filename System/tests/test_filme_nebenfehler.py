# -*- coding: utf-8 -*-
"""Kleine Fehler im Film-Teil (Gesamtprüfung Gruppe 6, 25.09.2026). Kein Netz,
keine Platte außer tmp_path; alle Antworten sind Attrappen (Muster test_filme).

F12: Ein kurzer TMDB- oder OMDb-Ausfall (auch eine 429-Antwort) ließ die
Detailseite 14 Tage leer, und der OMDb-Tageszähler wurde nie gespeichert, der
Deckel griff also nie.
F13: reihen() fragte TMDB bei Fehlschlägen ohne wirksamen Deckel.
"""
import json
import os
import sys
import time

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

import filme  # noqa: E402
from test_filme import (FAKE_AUTH, FAKE_INFO, FAKE_ITEMS, FAKE_OMDB, FAKE_TMDB,  # noqa: E402
                        _attrappen_ohne_unerwartete_rufe, _einrichten, _fake_http)

assert _attrappen_ohne_unerwartete_rufe                 # autouse-Fixture gilt auch hier


def _katalog(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, FAKE_ITEMS)]))
    filme.katalog_abzug()
    monkeypatch.setattr(filme, "_meta_keys", lambda: {"tmdb": "T", "omdb": "O"})


def _meta():
    with open(filme._pfade["meta"], encoding="utf-8") as f:
        return json.load(f)


def _altern(item_id, sekunden):
    d = _meta()
    d[item_id]["ts"] -= sekunden
    with open(filme._pfade["meta"], "w", encoding="utf-8") as f:
        json.dump(d, f)


def _technik():
    return ("/Items/f1", 200, FAKE_ITEMS["Items"][0])


# ------------------------------------------------------------------ F12

def test_kurzer_tmdb_ausfall_haelt_nur_eine_stunde(tmp_path, monkeypatch):
    _katalog(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 429, {"status_message": "zu viele"}),
        ("omdbapi.com", 200, FAKE_OMDB), _technik()]))
    assert filme.detail("f1")["beschreibung"] == ""
    # binnen der Stunde: aus dem Zwischenspeicher, kein neuer Abruf
    monkeypatch.setattr(filme, "_http", _fake_http([]))
    assert filme.detail("f1")["beschreibung"] == ""
    # nach einer Stunde: neuer Versuch, der jetzt gelingt
    _altern("f1", 3601)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, FAKE_TMDB), ("omdbapi.com", 200, FAKE_OMDB), _technik()]))
    assert filme.detail("f1")["beschreibung"].startswith("Astronaut")


def test_netzfehler_bei_omdb_haelt_nur_eine_stunde(tmp_path, monkeypatch):
    _katalog(tmp_path, monkeypatch)
    tmdb_ok = _fake_http([("api.themoviedb.org", 200, FAKE_TMDB), _technik()])

    def http(url, **kw):
        if "omdbapi.com" in url:
            raise OSError("Zeitüberschreitung")
        return tmdb_ok(url, **kw)
    monkeypatch.setattr(filme, "_http", http)
    assert filme.detail("f1")["imdb_rating"] == ""
    _altern("f1", 3601)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, FAKE_TMDB), ("omdbapi.com", 200, FAKE_OMDB), _technik()]))
    assert filme.detail("f1")["imdb_rating"] == "8.0"


def test_vollstaendige_antwort_haelt_vierzehn_tage(tmp_path, monkeypatch):
    _katalog(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, FAKE_TMDB), ("omdbapi.com", 200, FAKE_OMDB), _technik()]))
    filme.detail("f1")
    _altern("f1", 3 * 24 * 3600)
    monkeypatch.setattr(filme, "_http", _fake_http([]))    # jeder Abruf wäre ein Fehler
    assert filme.detail("f1")["imdb_rating"] == "8.0"


def test_tmdb_404_ist_endgueltig(tmp_path, monkeypatch):
    # Titel gibt es bei TMDB nicht: das ist kein Ausfall, sondern die Antwort.
    _katalog(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 404, {}), ("omdbapi.com", 200, FAKE_OMDB), _technik()]))
    filme.detail("f1")
    _altern("f1", 3601)
    monkeypatch.setattr(filme, "_http", _fake_http([]))
    assert filme.detail("f1")["imdb_rating"] == "8.0"


def test_omdb_zaehler_wird_gespeichert(tmp_path, monkeypatch):
    _katalog(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, FAKE_TMDB), ("omdbapi.com", 200, FAKE_OMDB), _technik()]))
    filme.detail("f1")
    d = _meta()
    assert d.get("omdb_tag") == time.strftime("%Y-%m-%d")
    assert d.get("omdb_zaehler") == 1


def test_omdb_deckel_greift_und_holt_morgen_nach(tmp_path, monkeypatch):
    _katalog(tmp_path, monkeypatch)
    heute = time.strftime("%Y-%m-%d")
    with open(filme._pfade["meta"], "w", encoding="utf-8") as f:
        json.dump({"omdb_tag": heute, "omdb_zaehler": filme.OMDB_TAGES_DECKEL}, f)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, FAKE_TMDB), _technik()]))   # OMDb wäre ein unerwarteter Ruf
    assert filme.detail("f1")["imdb_rating"] == ""
    assert _meta()["omdb_zaehler"] == filme.OMDB_TAGES_DECKEL
    # am nächsten Tag (neuer Zähler) und nach der Stunde: OMDb wird nachgeholt
    d = _meta()
    d["omdb_tag"] = "2000-01-01"
    with open(filme._pfade["meta"], "w", encoding="utf-8") as f:
        json.dump(d, f)
    _altern("f1", 3601)
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("api.themoviedb.org", 200, FAKE_TMDB), ("omdbapi.com", 200, FAKE_OMDB), _technik()]))
    assert filme.detail("f1")["imdb_rating"] == "8.0"
    assert _meta()["omdb_zaehler"] == 1 and _meta()["omdb_tag"] == heute


# ------------------------------------------------------------------ F13
# reihen() versprach „kein Netz“, fragte aber TMDB synchron. Der Deckel „8“
# zählte nur Erfolge: scheiterten die Abrufe, liefen bis zu 120 mit je 15 s
# Zeitlimit, und jede Fehlantwort wurde bei jedem Laden erneut gefragt.

def _reihen_katalog(tmp_path, monkeypatch, n=30):
    _einrichten(tmp_path, monkeypatch)
    items = {"Items": [
        {"Id": f"m{i:02d}", "Name": f"Film {i}", "Type": "Movie", "CommunityRating": 9.0 - i * 0.01,
         "Genres": ["Drama"], "ProviderIds": {"Tmdb": f"{1000 + i}"}, "ImageTags": {},
         "UserData": {"Played": False}} for i in range(n)]}
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
        ("/Items", 200, items)]))
    filme.katalog_abzug()
    monkeypatch.setattr(filme, "_meta_keys", lambda: {"tmdb": "K", "omdb": ""})


def _tmdb_zaehler(monkeypatch, antwort):
    rufe = []

    def http(url, **kw):
        assert "themoviedb.org" in url, url
        rufe.append(url)
        if isinstance(antwort, Exception):
            raise antwort
        return antwort
    monkeypatch.setattr(filme, "_http", http)
    return rufe


def test_reihen_deckelt_versuche_nicht_erfolge(tmp_path, monkeypatch):
    # 404: TMDB kennt den Titel nicht. Das ist eine Antwort, kein Ausfall.
    _reihen_katalog(tmp_path, monkeypatch)
    rufe = _tmdb_zaehler(monkeypatch, (404, b"{}"))
    filme.reihen()
    assert len(rufe) == 8, f"{len(rufe)} TMDB-Abrufe in einem Laden (Deckel 8 Versuche)"
    filme.reihen()
    assert len(rufe) == 16
    assert not set(rufe[:8]) & set(rufe[8:]), "eine Fehlantwort wurde beim nächsten Laden erneut gefragt"


def test_reihen_serverfehler_pausiert_das_eichen(tmp_path, monkeypatch):
    for antwort in ((500, b"{}"), (429, b"{}"), (401, b"{}")):
        _reihen_katalog(tmp_path / str(antwort[0]), monkeypatch)
        rufe = _tmdb_zaehler(monkeypatch, antwort)
        filme.reihen()
        filme.reihen()
        assert len(rufe) == 1, f"{antwort[0]}: nach dem ersten Fehlschlag {len(rufe) - 1} weitere Abrufe"


def test_reihen_netzfehler_pausiert_das_eichen(tmp_path, monkeypatch):
    _reihen_katalog(tmp_path, monkeypatch)
    rufe = _tmdb_zaehler(monkeypatch, OSError("Zeitüberschreitung"))
    r = filme.reihen()
    assert len(rufe) == 1, f"nach einem Netzfehler noch {len(rufe) - 1} weitere Abrufe"
    assert r["top"], "die Reihen stehen trotzdem"
    filme.reihen()
    assert len(rufe) == 1, "binnen der Pause fragt reihen() TMDB nicht erneut"


def test_reihen_fehlschlag_ruht_einen_tag(tmp_path, monkeypatch):
    _reihen_katalog(tmp_path, monkeypatch, n=3)
    rufe = _tmdb_zaehler(monkeypatch, (404, b"{}"))
    filme.reihen()
    assert len(rufe) == 3
    filme.reihen()
    assert len(rufe) == 3, "binnen eines Tages keine neue Frage nach denselben Titeln"
    d = _meta()
    d["tmdb_stimmen_fehl"] = {k: v - 86401 for k, v in d["tmdb_stimmen_fehl"].items()}
    with open(filme._pfade["meta"], "w", encoding="utf-8") as f:
        json.dump(d, f)
    filme.reihen()
    assert len(rufe) == 6, "nach einem Tag wird erneut gefragt"


def test_reihen_eicht_weiter_acht_je_laden(tmp_path, monkeypatch):
    _reihen_katalog(tmp_path, monkeypatch)
    rufe = _tmdb_zaehler(monkeypatch, (200, json.dumps({"vote_count": 900, "vote_average": 7.5}).encode()))
    filme.reihen()
    assert len(rufe) == 8
    filme.reihen()
    assert len(rufe) == 16 and len(set(rufe)) == 16
    assert len(_meta()["tmdb_stimmen"]) == 16


# ------------------------------------------------------------------ F19
# Liegengebliebene Meldungen („gesehen“, Stellen) gingen nur am Ende eines
# erfolgreichen Katalog-Abzugs raus. Scheitert der Abzug tagelang (Renés
# Server sperrte mit 403), blieben sie liegen, obwohl einzelne Meldungen längst
# wieder ankamen. Jetzt reicht eine angekommene Meldung gedrosselt nach.

def _queue(eintraege):
    with open(filme._pfade["queue"], "w", encoding="utf-8") as f:
        json.dump(eintraege, f)


def _queue_jetzt():
    try:
        with open(filme._pfade["queue"], encoding="utf-8") as f:
            return json.load(f)
    except OSError:
        return []


def _jellyfin_ok(mitschrift):
    return _fake_http([("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO),
                       ("Sessions/Playing", 204, {}), ("UserPlayedItems", 200, {})],
                      mitschrift=mitschrift)


def _sofort(monkeypatch):
    """Den Hintergrund-Faden des Nachreichens sofort im Test laufen lassen."""
    monkeypatch.setattr(filme, "_im_hintergrund", lambda f: f(), raising=False)


def test_angekommene_meldung_reicht_liegengebliebene_nach(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    _sofort(monkeypatch)
    _queue([{"item": "f9", "position_s": 0, "gesehen": True, "ts": time.time() - 3600}])
    rufe = []
    monkeypatch.setattr(filme, "_http", _jellyfin_ok(rufe))
    assert filme.fortschritt("f1", 100) is True
    assert any("UserPlayedItems/f9" in url for url, _ in rufe), "das liegengebliebene „gesehen“ ging nicht raus"
    assert _queue_jetzt() == []


def test_nachreichen_ist_gedrosselt(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    _sofort(monkeypatch)
    rufe = []
    monkeypatch.setattr(filme, "_http", _jellyfin_ok(rufe))
    _queue([{"item": "f9", "position_s": 0, "gesehen": True, "ts": time.time() - 3600}])
    filme.fortschritt("f1", 100)
    _queue([{"item": "f8", "position_s": 0, "gesehen": True, "ts": time.time() - 60}])
    filme.fortschritt("f1", 200)
    assert not any("UserPlayedItems/f8" in url for url, _ in rufe), \
        "binnen zehn Minuten ein zweites Nachreichen"
    assert _queue_jetzt()[0]["item"] == "f8"


def test_nachreich_fehler_wird_vermerkt_und_die_meldung_gilt(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    _sofort(monkeypatch)
    monkeypatch.setattr(filme, "_http", _jellyfin_ok([]))
    _queue([{"item": "f9", "position_s": 0, "gesehen": True, "ts": time.time() - 3600}])

    def kaputt():
        raise RuntimeError("Warteschlange unlesbar")
    monkeypatch.setattr(filme, "fortschritt_nachreichen", kaputt)
    assert filme.fortschritt("f1", 100) is True
    d = json.load(open(filme._pfade["zustand"], encoding="utf-8"))
    assert "Warteschlange unlesbar" in d.get("nachreichen_fehler", ""), d


def test_ohne_offene_meldung_kein_nachreichen(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    laeufe = []
    monkeypatch.setattr(filme, "_im_hintergrund", lambda f: laeufe.append(f), raising=False)
    monkeypatch.setattr(filme, "_http", _jellyfin_ok([]))
    _queue([{"item": "f9", "position_s": 5, "gesehen": False, "ts": 1, "abgewiesen": True}])
    assert filme.fortschritt("f1", 100) is True
    assert laeufe == [], "abgewiesene Einträge allein lösen kein Nachreichen aus"


# ------------------------------------------------------------------ F20
# Der Bild-Cache schrieb nicht atomar: brach das Schreiben ab (Platte voll,
# Prozess beendet), blieb ein abgeschnittenes Bild unter dem Zielnamen liegen,
# und jeder spätere Abruf lieferte es aus dem Cache, für immer.

class _HalbeDatei:
    """Schreibt die Hälfte und scheitert dann, wie eine volle Platte."""

    def __init__(self, pfad):
        self._f = open(pfad, "wb")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self._f.close()
        return False

    def write(self, roh):
        self._f.write(roh[:len(roh) // 2])
        raise OSError(28, "Kein Platz auf dem Datenträger")


def test_bild_cache_haelt_kein_halbes_bild(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    bild = b"\xff\xd8" + b"JPEG" * 500
    monkeypatch.setattr(filme, "_http", _fake_http([
        ("AuthenticateByName", 200, FAKE_AUTH), ("/System/Info", 200, FAKE_INFO)]))
    antwort = filme._http

    def http(url, **kw):
        if "/Images/" in url:
            return 200, bild
        return antwort(url, **kw)
    monkeypatch.setattr(filme, "_http", http)
    echt = open

    def oeffnen(pfad, modus="r", *a, **k):
        if "wb" in modus and "filme_bilder" in str(pfad):
            return _HalbeDatei(pfad)
        return echt(pfad, modus, *a, **k)
    monkeypatch.setattr(filme, "open", oeffnen, raising=False)
    try:
        erstes = filme.bild_holen("f1")
    except OSError:
        erstes = None
    assert erstes in (None, bild)
    monkeypatch.setattr(filme, "open", echt, raising=False)
    assert filme.bild_holen("f1") == bild, "ein abgeschnittenes Bild blieb im Cache"
    ordner = os.listdir(filme._pfade["bilder"])
    assert ordner == ["f1_Primary.jpg"], ordner
