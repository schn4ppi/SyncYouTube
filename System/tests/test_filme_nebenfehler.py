# -*- coding: utf-8 -*-
"""Kleine Fehler im Film-Teil (Gesamtprüfung Gruppe 6, 25.09.2026). Kein Netz,
keine Platte außer tmp_path; alle Antworten sind Attrappen (Muster test_filme).

F12: Ein kurzer TMDB- oder OMDb-Ausfall (auch eine 429-Antwort) ließ die
Detailseite 14 Tage leer, und der OMDb-Tageszähler wurde nie gespeichert, der
Deckel griff also nie.
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
