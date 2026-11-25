# -*- coding: utf-8 -*-
"""Film-Riegel je Profil (25.11.2026: „Ich möchte, dass man keinen Zugriff auf
externe Bibliotheken bekommt, die bereits bei mir angebunden sind, jeder hat seine
eigenen Zugänge. Das ist wichtig!").

Bis 1.4.1 bekam jedes gekoppelte Gerät und jedes Profil den Film-Katalog, die
Ströme, Bilder und die Wünsche an Jellyseerr über Besitzer-Zugang im Schlüsselbund.
Jetzt nur das Profil, dem der Zugang gehört (das Besitzer-Profil). Geprüft wird
an JEDER Route unter /api/filme/ aus der Routen-Tabelle, auch an künftigen.
"""
import inspect
import json
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

import filme  # noqa: E402
import profil_geraete as pg  # noqa: E402
import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import (  # noqa: E402,F401  (rechner: autouse-Fixture)
    CODE, LAN, PC_IM_LAN, _anfrage, _fernsteuerung, rechner)

# Was der Riegel selbst fragt (liest nur den Schlüsselbund, ruft nie einen Server).
DIE_PRUEFUNG_SELBST = {"profil_hat_konto", "dienste_fuer", "_zugang_aus"}
FILM_ROUTEN = sorted((verb, pfad) for verb, pfad in app.ROUTEN if pfad.startswith(app.FILM_PRAEFIX))


def _gekoppelt(profil_id):
    a = pg.geraet_anmelden("Handy")
    assert pg.geraet_bestaetigen(a["geraet_id"], profil_id)
    return pg.geraet_token_abholen(a["geraet_id"], a["code"])["token"]


@pytest.fixture
def stolperdraht(monkeypatch):
    """Jede Funktion in filme meldet, wenn sie gerufen wird: hinter dem Riegel darf
    keine einzige laufen (kein Katalog, kein Strom, keine Anmeldung beim Film-Server)."""
    gerufen = []
    for name, f in vars(filme).items():
        if (inspect.isfunction(f) and f.__module__ == filme.__name__
                and name not in DIE_PRUEFUNG_SELBST):
            monkeypatch.setattr(filme, name, lambda *a, _n=name, **k: gerufen.append(_n))
    return gerufen


def _rufen(verb, pfad, ip, kopf):
    rumpf = {"id": "f1"} if verb == "POST" else None
    return _anfrage(pfad + "?id=f1", methode=verb, ip=ip, kopf=kopf, rumpf=rumpf)


def _gesperrt(st, koerper):
    d = json.loads(koerper or b"{}")
    return st in (200, 403) and d.get("profil_ohne_zugang") is True


def test_die_tabelle_kennt_film_routen():
    assert len(FILM_ROUTEN) >= 15, FILM_ROUTEN


@pytest.mark.parametrize("verb,pfad", FILM_ROUTEN)
def test_fremdes_profil_bekommt_nichts_ueber_jbs_zugang(monkeypatch, stolperdraht, verb, pfad):
    _fernsteuerung(monkeypatch)
    pg.profil_anlegen("Anna", "🦁")
    anna = next(p["id"] for p in pg.profil_liste() if p["name"] == "Anna")
    kopf = {"Host": PC_IM_LAN, "X-Geraet": _gekoppelt(anna)}
    st, _, koerper = _rufen(verb, pfad, LAN, kopf)
    assert _gesperrt(st, koerper), (pfad, st, koerper[:200])
    assert stolperdraht == [], f"{pfad}: hinter dem Riegel lief {stolperdraht}"


@pytest.mark.parametrize("verb,pfad", FILM_ROUTEN)
def test_nur_mit_fernsteuerungs_code_kein_profil_keine_filme(monkeypatch, stolperdraht, verb, pfad):
    _fernsteuerung(monkeypatch)
    st, _, koerper = _rufen(verb, pfad, LAN, {"Host": PC_IM_LAN, "X-Code": CODE})
    assert _gesperrt(st, koerper), (pfad, st, koerper[:200])
    assert stolperdraht == []


@pytest.mark.parametrize("verb,pfad", FILM_ROUTEN)
def test_am_pc_mit_fremdem_profil_gewaehlt_gesperrt(stolperdraht, verb, pfad):
    rumpf = {"id": "f1"} if verb == "POST" else None
    st, _, koerper = _anfrage(pfad + "?id=f1&profil=anna", methode=verb, rumpf=rumpf)
    assert _gesperrt(st, koerper), (pfad, st, koerper[:200])
    assert stolperdraht == []


def test_besitzer_profil_sieht_seine_filme_am_pc_und_auf_seinen_geraeten(monkeypatch):
    _fernsteuerung(monkeypatch)
    monkeypatch.setattr(filme, "katalog_lesen", lambda: {"eintraege": [{"id": "f1"}]})
    kopf = {"Host": PC_IM_LAN, "X-Geraet": _gekoppelt(pg.STANDARD_PROFIL["id"])}
    for ip, k in ((LAN, kopf), ("127.0.0.1", None)):
        st, _, koerper = _anfrage("/api/filme/katalog", ip=ip, kopf=k)
        assert st == 200 and json.loads(koerper)["eintraege"] == [{"id": "f1"}], (ip, koerper[:200])


def test_gesperrte_lese_routen_behalten_ihre_form():
    """Die Oberfläche bricht nicht: leere Reihen und ein Zustand mit Hinweis."""
    st, _, koerper = _anfrage("/api/filme/reihen?profil=anna")
    d = json.loads(koerper)
    assert st == 200 and d["weiterschauen"] == [] and d["genres"] == {} and d["profil_ohne_zugang"]
    st, _, koerper = _anfrage("/api/filme/zustand?profil=anna")
    d = json.loads(koerper)
    assert st == 200 and d["zugang"] is False and "eigenen Film-Zugang" in d["fehler"]


def test_oberflaeche_nennt_den_grund_statt_fremder_filme(tmp_path):
    """filmWarnung mit dem echten Seiten-JavaScript (deno): ein gesperrtes Profil
    sieht den Hinweis, nicht „Kein Jellyfin-Zugang eingerichtet“."""
    from test_jellyfin_zugang import _warnung
    st, _, koerper = _anfrage("/api/filme/zustand?profil=anna")
    w = _warnung(tmp_path, json.loads(koerper))
    assert w.startswith("🔒") and "eigenen Film-Zugang" in w, w


# ------------------------------------------------ Stufe 2: eigenes Konto je Profil
# Ein Profil verbindet sein EIGENES Jellyfin-Konto und bekommt eine eigene Kopie
# des filme-Moduls: eigene Sitzung, eigener Katalog, eigener Schlüsselbund-Eintrag,
# eigene Gerätekennung. Nie den Katalog oder die Schlüssel des Besitzers.

from test_filme import BASIS, JellyfinAttrappe  # noqa: E402


@pytest.fixture
def anna(monkeypatch):
    _fernsteuerung(monkeypatch)
    pg.profil_anlegen("Anna", "🦁")
    pid = next(p["id"] for p in pg.profil_liste() if p["name"] == "Anna")
    jf = JellyfinAttrappe("12")
    monkeypatch.setattr(filme, "_http", jf)          # die Kopien übernehmen ihn beim Laden
    angestossen = []
    monkeypatch.setattr(app, "_filme_abzug_anstossen", lambda **k: angestossen.append(k) or True)
    return {"id": pid, "kopf": {"Host": PC_IM_LAN, "X-Geraet": _gekoppelt(pid)},
            "jf": jf, "angestossen": angestossen}


def _konto(kopf, **rumpf):
    st, _, koerper = _anfrage("/api/filme_konto", methode="POST", ip=LAN, kopf=kopf, rumpf=rumpf)
    return st, json.loads(koerper)


def _verbinden(a, passwort="geheim-anna"):
    return _konto(a["kopf"], art="verbinden", url=BASIS, benutzer="anna", passwort=passwort)


def _eintraege(bund, profil):
    """Alle Schlüsselbund-Einträge dieses Profils."""
    return {(d, n) for d, n in bund.daten if d.endswith("/" + profil)}


def test_profil_verbindet_sein_eigenes_konto(anna, schluesselbund):
    vorher = dict(schluesselbund.daten)
    st, erg = _verbinden(anna)
    assert st == 200 and erg == {"ok": True}, erg
    dienst = f"SyncYouTube-Jellyfin/{anna['id']}"
    assert schluesselbund.daten[(dienst, "benutzer")] == "anna"
    assert schluesselbund.daten[(dienst, "passwort")] == "geheim-anna"
    assert {k: v for k, v in schluesselbund.daten.items() if k in vorher} == vorher, \
        "das Konto eines anderen Profils wurde angefasst"
    assert anna["angestossen"] and anna["angestossen"][0]["fm"] is not filme, "kein eigener Katalog-Abzug"
    # Ab jetzt ist das Profil hinter dem Riegel erlaubt, mit SEINEM Modul.
    fm = app.filme_fuer(anna["id"])
    assert fm is not None and fm is not filme and fm._profil == anna["id"]
    st, _, koerper = _anfrage("/api/filme_konto", ip=LAN, kopf=anna["kopf"])
    sicht = json.loads(koerper)
    assert sicht["verbunden"] is True and sicht["benutzer"] == "anna"
    assert "geheim-anna" not in koerper.decode("utf-8"), "das Passwort steht in einer Antwort"


def test_jedes_profil_sieht_nur_seinen_eigenen_katalog(anna):
    filme.ablage.json_schreiben(filme._pfade["katalog"], {"stand": 1, "eintraege": [{"id": "nur-standard"}]})
    assert _verbinden(anna)[1] == {"ok": True}
    fm = app.filme_fuer(anna["id"])
    assert fm.katalog_abzug()["ok"]                  # Annas eigener Abzug gegen ihren Server
    st, _, koerper = _anfrage("/api/filme/katalog", ip=LAN, kopf=anna["kopf"])
    ids = [e["id"] for e in json.loads(koerper)["eintraege"]]
    assert st == 200 and "f1" in ids and "nur-standard" not in ids, ids
    st, _, koerper = _anfrage("/api/filme/katalog")   # der PC mit dem ersten Profil: nur seiner
    assert [e["id"] for e in json.loads(koerper)["eintraege"]] == ["nur-standard"]
    assert fm.geraet_kennung() != filme.geraet_kennung(), "zwei Profile, eine Gerätekennung"


def test_falsches_passwort_speichert_nichts(anna, schluesselbund):
    anna["jf"].anmeldung = 401
    st, erg = _verbinden(anna, passwort="falsch")
    assert st == 200 and "abgelehnt" in erg["fehler"] and "falsch" not in json.dumps(erg)
    assert not _eintraege(schluesselbund, anna["id"])
    assert app.filme_fuer(anna["id"]) is None
    st, erg = _verbinden(anna)                       # gleich danach: Ruhe, kein zweiter Versuch
    assert "Minute" in erg["fehler"] and anna["jf"].anmeldungen() == 1


def test_fremde_schluessel_bleiben_beim_anderen_profil(anna, schluesselbund):
    schluesselbund.set_password(filme.dienste_fuer("standard")["tmdb"], "api_key", "TMDB-STANDARD")
    schluesselbund.set_password(filme.dienste_fuer("standard")["seerr"], "url", "https://seerr.example")
    assert _verbinden(anna)[1] == {"ok": True}
    fm = app.filme_fuer(anna["id"])
    assert fm._meta_keys() == {"tmdb": "", "omdb": ""}, "Anna nutzt fremde TMDB-Schlüssel"
    assert fm._seerr_url() == "", "Anna nutzt ein fremdes Jellyseerr"
    assert fm._dienste["tmdb"] == f"SyncYouTube-TMDB/{anna['id']}"


def test_eigene_tmdb_und_omdb_schluessel_sind_freiwillig(anna, schluesselbund):
    st, erg = _konto(anna["kopf"], art="verbinden", url=BASIS, benutzer="anna",
                     passwort="geheim-anna", tmdb="tmdb-schluessel-anna", omdb="omdbanna1")
    assert erg == {"ok": True}, erg
    assert app.filme_fuer(anna["id"])._meta_keys() == {"tmdb": "tmdb-schluessel-anna",
                                                       "omdb": "omdbanna1"}
    st, erg = _konto(anna["kopf"], art="verbinden", url=BASIS, benutzer="anna",
                     passwort="x", tmdb="kein schlüssel!")
    assert "Schlüssel" in erg["fehler"]


ALTE_NAMEN = ("Sync-Jellyfin", "Sync-Jellyseerr", "Sync-TMDB", "Sync-OMDb")


def test_alte_eintraege_werden_nie_gelesen(monkeypatch, schluesselbund):
    """Entscheid 25.11.2026: Das Programm hat keinen Bezug zu Zugängen, die nicht über
    „Konto verbinden“ entstanden sind, auch nicht für das erste Profil. Alte Einträge
    unter den früheren Namen bleiben im Schlüsselbund liegen und werden nie gelesen."""
    schluesselbund.daten.clear()
    for dienst in ALTE_NAMEN:
        for name in ("url", "benutzer", "passwort", "api_key"):
            schluesselbund.set_password(dienst, name, "alt")
    alt = dict(schluesselbund.daten)
    st, _, koerper = _anfrage("/api/filme/zustand")
    d = json.loads(koerper)
    assert d["profil_ohne_zugang"] is True and d["kann_verbinden"] is True, d
    assert app.filme_fuer("standard") is None
    assert schluesselbund.daten == alt, "alte Einträge verändert"
    quelle = open(filme.__file__, encoding="utf-8").read() + open(app.__file__, encoding="utf-8").read()
    for name in ALTE_NAMEN:
        assert f'"{name}"' not in quelle, f"der alte Name {name} steht noch im Code"


def test_das_erste_profil_verbindet_sich_wie_jedes_andere(monkeypatch, schluesselbund):
    schluesselbund.daten.clear()
    _fernsteuerung(monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12"))
    monkeypatch.setattr(app, "_filme_abzug_anstossen", lambda **k: True)
    kopf = {"Host": PC_IM_LAN, "X-Geraet": _gekoppelt(pg.STANDARD_PROFIL["id"])}
    st, erg = _konto(kopf, art="verbinden", url=BASIS, benutzer="ich", passwort="pw-standard")
    assert erg == {"ok": True}, erg
    assert schluesselbund.daten[("SyncYouTube-Jellyfin/standard", "benutzer")] == "ich"
    assert app.filme_fuer("standard") is filme
    st, erg = _konto(kopf, art="trennen")
    assert erg.get("ok") and app.filme_fuer("standard") is None
    st, erg = _konto({"Host": PC_IM_LAN, "X-Code": CODE}, art="verbinden", url=BASIS,
                     benutzer="x", passwort="y")
    assert st == 403, "nur mit Fernsteuerungs-Code: kein Profil, kein Konto"


def test_trennen_nimmt_den_zugang_und_legt_die_daten_beiseite(anna, schluesselbund):
    assert _verbinden(anna)[1] == {"ok": True}
    fm = app.filme_fuer(anna["id"])
    assert fm.merkliste_toggle("f1", anna["id"]) is True
    ordner = os.path.join(app.DATEN_DIR, app.FILM_KONTO_ORDNER, anna["id"])
    st, erg = _konto(anna["kopf"], art="trennen")
    assert st == 200 and erg.get("ok"), erg
    assert not _eintraege(schluesselbund, anna["id"])
    assert app.filme_fuer(anna["id"]) is None and not os.path.exists(ordner)
    beiseite = os.listdir(os.path.join(app.DATEN_DIR, app.FILM_KONTO_ORDNER, "_getrennt"))
    assert len(beiseite) == 1 and beiseite[0].startswith(anna["id"]), "die Merkliste ist weg"
    st, _, koerper = _anfrage("/api/filme/katalog", ip=LAN, kopf=anna["kopf"])
    assert json.loads(koerper).get("profil_ohne_zugang") is True


def test_eine_probe_nutzt_nie_die_echten_zugaenge(monkeypatch, schluesselbund):
    """Fund 25.11.2026: Der --testmodus las den echten Schlüsselbund, und sein leerer
    Datenordner machte den 6-h-Abzug sofort fällig: jeder Probelauf holte mit dem
    echten Konto den ganzen Katalog des Film-Servers. Jetzt zeigen Hauptmodul und
    jede Profil-Kopie auf eigene, leere Einträge mit „-Testmodus“."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("filme_probe", filme.__file__)
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    for dienst in ("SyncYouTube-Jellyfin/standard", "SyncYouTube-Jellyfin/anna"):
        for name, wert in (("url", "https://jelly.example"), ("benutzer", "nutzer"), ("passwort", "echt")):
            schluesselbund.set_password(dienst, name, wert)
    schluesselbund.set_password("SyncYouTube-TMDB/standard", "api_key", "TMDB-ECHT")
    assert probe._zugang() is not None, "Gegenprobe: ohne Probe-Schalter sähe sie das echte Konto"
    app.film_zugaenge_fuer_probe(probe)
    app.film_zugaenge_fuer_probe(probe)               # zweimal: kein doppeltes Anhängen
    assert probe._zugang() is None and probe._meta_keys() == {"tmdb": "", "omdb": ""}
    assert not probe.profil_hat_konto("anna")
    assert probe._dienste["jellyfin"] == "SyncYouTube-Jellyfin-Testmodus/standard"
    assert probe.dienste_fuer("anna")["jellyfin"] == "SyncYouTube-Jellyfin-Testmodus/anna"
    # Die Kopie je Profil übernimmt die Grundnamen des Hauptmoduls.
    monkeypatch.setattr(app, "filme", probe)
    pg.profil_anlegen("Anna", "🦁")
    pid = next(p["id"] for p in pg.profil_liste() if p["name"] == "Anna")
    kopie = app.filme_fuer(pid, anlegen=True)
    assert kopie._dienste["jellyfin"] == f"SyncYouTube-Jellyfin-Testmodus/{pid}"
