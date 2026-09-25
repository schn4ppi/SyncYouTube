# -*- coding: utf-8 -*-
"""Was darf ein Gerät im WLAN? (Gesamtprüfung Gruppe 5, JB-Entscheide 7a, 25.09.2026)

Wie in test_zugang_und_vertrauen.py läuft jede Anfrage durch den ECHTEN
Handler samt echtem Riegel, ohne Server und ohne Socket. Die Helfer und die
Fixture `rechner` (Rechnername `JB-PC`, leere Versuchsbremse) kommen von dort.
"""
import ast
import json
import os
import sys
from urllib.parse import urlencode, urlparse

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if TEST_DIR not in sys.path:
    sys.path.insert(0, TEST_DIR)

import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import (  # noqa: E402,F401  (rechner: autouse-Fixture)
    CODE, LAN, PC_IM_LAN, _anfrage, _fernsteuerung, rechner)


# ------------------------------------------------------------ 7a Punkt 8: Alias /handy weg

def test_alias_handy_ist_weg_und_m_bleibt(monkeypatch):
    """Kein Verweis, das README nennt nur /m (Abschnitt 5). Vom PC: 404 statt
    der Handy-Seite; aus dem WLAN ist /handy auch kein freier Koppel-Weg mehr."""
    st, _, koerper = _anfrage("/handy", kopf={"Host": "127.0.0.1:8776"})
    assert st == 404, koerper[:80]
    st, _, koerper = _anfrage("/m", kopf={"Host": "127.0.0.1:8776"})
    assert st == 200 and b"YTDL" in koerper
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/handy", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 403, "ohne Zugangsdaten ist /handy kein freier Weg mehr"
    st, _, koerper = _anfrage("/m", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 200 and b"YTDL" in koerper, "/m bleibt der freie Einstieg mit Code-Eingabe"


# ------------------------------------------------------------ 7a Punkt 2: WLAN-Rechte (S10)
# Die Routen kommen aus dem Syntaxbaum des Routers, nicht aus einer Handliste:
# eine neue Route ohne Einordnung macht den Test rot, eine verwaiste Einordnung
# ebenso. Welche Route wohin gehört, steht nur in LAN_ERLAUBT und NUR_PC.

def _ist_pfad_ausdruck(k, namen=frozenset()):
    """`self.path`, `urlparse(self.path).path` oder ein lokaler Name, der
    diesen Wert trägt (`pfad = urlparse(self.path).path`)."""
    if isinstance(k, ast.Name):
        return k.id in namen
    if isinstance(k, ast.Attribute) and k.attr == "path":
        if isinstance(k.value, ast.Name) and k.value.id == "self":
            return True
        return bool(isinstance(k.value, ast.Call) and isinstance(k.value.func, ast.Name)
                    and k.value.func.id == "urlparse" and k.value.args
                    and _ist_pfad_ausdruck(k.value.args[0]))
    return False


def _routen_aus_dem_code():
    """(Methode, Pfad) jeder Route, wie der Router sie vergleicht: `==`, `in (…)`
    und `.startswith(…)` auf dem Pfad in Handler._get_routen/_post_routen."""
    with open(app.__file__, encoding="utf-8") as f:
        baum = ast.parse(f.read())
    handler = next(k for k in baum.body if isinstance(k, ast.ClassDef) and k.name == "Handler")
    methoden = {f.name: f for f in handler.body if isinstance(f, ast.FunctionDef)}
    routen = set()
    for name, methode in (("_get_routen", "GET"), ("_post_routen", "POST")):
        if name not in methoden:                     # alter Stand ohne getrennten Router
            continue
        namen = frozenset(z.id for k in ast.walk(methoden[name]) if isinstance(k, ast.Assign)
                          and _ist_pfad_ausdruck(k.value)
                          for z in k.targets if isinstance(z, ast.Name))
        for k in ast.walk(methoden[name]):
            werte = []
            if isinstance(k, ast.Compare) and _ist_pfad_ausdruck(k.left, namen):
                for op, rechts in zip(k.ops, k.comparators):
                    if isinstance(op, ast.Eq):
                        werte.append(rechts)
                    elif isinstance(op, ast.In) and isinstance(rechts, (ast.Tuple, ast.List, ast.Set)):
                        werte.extend(rechts.elts)
            elif (isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute)
                  and k.func.attr == "startswith" and _ist_pfad_ausdruck(k.func.value, namen)):
                werte.extend(k.args)
            for w in werte:
                if isinstance(w, ast.Constant) and isinstance(w.value, str):
                    routen.add((methode, w.value))
    return routen


ROUTEN = sorted(_routen_aus_dem_code())

# Routen mit Prüfer: eine Probe, die aus dem WLAN durchgeht, und Proben, die
# nur am PC gehen. Jede Route mit Prüfer MUSS hier Proben haben.
PROBEN = {
    ("POST", "/api/vlc"): ({"cmd": "pause"},
                           [{"cmd": "play", "url": "file:///C:/Windows/win.ini"},
                            {"cmd": "fenster", "hwnd": 1, "pid": 1}]),
    ("POST", "/api/biblio"): ({"art": "herz", "id": "abc"},
                              [{"art": "loeschen", "id": "abc"}, {"art": "vergessen", "id": "abc"},
                               {"art": "bulk", "op": "loeschen", "keys": ["abc"]},
                               {"art": "extern", "id": "abc"}, {"art": "ordner", "id": "abc"},
                               {"art": "archiv", "id": "abc"}, {}]),
    ("POST", "/api/action"): ({"art": "pause", "id": "abc"},
                              [{"art": "ordner_offen"}, {"art": "ordner", "id": "abc"}]),
    ("POST", "/api/add"): ({"urls": "https://www.youtube.com/watch?v=abcdefghijk"},
                           [{"urls": "https://vimeo.com/1"}, {},
                            {"urls": "https://www.youtube.com/watch?v=a\nhttps://www.youtube.com/watch?v=b"},
                            {"urls": "https://www.youtube.com/watch?v=a", "ziel_playlist": "Entdeckt"}]),
    ("GET", "/api/kanal_info"): ({"url": "https://www.youtube.com/@kanal"},
                                 [{"url": "http://127.0.0.1:8779/"}, {}]),
}


def _proben(route):
    return PROBEN.get(route, ({}, []))


@pytest.fixture
def geroutet(monkeypatch):
    """Die Router-Rümpfe durch einen Zeugen ersetzen: geprüft wird das Tor VOR
    dem Routing, ohne dass eine Route etwas tut (kein Download, kein VLC, kein
    Netz, keine Datei)."""
    erreicht = []

    def zeuge(methode):
        def routen(self, *_daten):
            erreicht.append((methode, urlparse(self.path).path))
            app._antwort(self, 200, {"geroutet": True})
        return routen
    monkeypatch.setattr(app.Handler, "_get_routen", zeuge("GET"), raising=False)
    monkeypatch.setattr(app.Handler, "_post_routen", zeuge("POST"), raising=False)
    return erreicht


def _senden(methode, pfad, daten=None, ip=LAN, kopf=None):
    kopf = dict({"Host": PC_IM_LAN if ip == LAN else "127.0.0.1:8776"}, **(kopf or {}))
    if methode == "GET":
        if daten:
            pfad += "?" + urlencode(daten)
        return _anfrage(pfad, ip=ip, kopf=kopf)
    return _anfrage(pfad, methode="POST", ip=ip, kopf=kopf, rumpf=daten or {})


def test_der_router_hat_die_erwarteten_routen():
    """Gegenprobe für die Ableitung: fände sie nichts mehr (Umbau des Routers),
    wären die folgenden Tests leer und grün."""
    assert len(ROUTEN) >= 70, ROUTEN
    for r in (("GET", "/"), ("GET", "/m"), ("GET", "/media"), ("GET", "/api/status"),
              ("POST", "/api/remote"), ("POST", "/api/config"), ("POST", "/api/abo")):
        assert r in ROUTEN, r


def test_jede_route_ist_genau_einmal_eingeordnet():
    lan, pc = set(app.LAN_ERLAUBT), set(app.NUR_PC)
    assert not lan & pc, f"doppelt eingeordnet: {sorted(lan & pc)}"
    assert not set(ROUTEN) - lan - pc, f"Routen ohne Einordnung: {sorted(set(ROUTEN) - lan - pc)}"
    assert not (lan | pc) - set(ROUTEN), f"Einordnung ohne Route: {sorted((lan | pc) - set(ROUTEN))}"
    for route, (grund, _pruefer) in app.LAN_ERLAUBT.items():
        assert isinstance(grund, str) and len(grund) > 8, (route, "ohne Grund")
    for route, grund in app.NUR_PC.items():
        assert isinstance(grund, str) and len(grund) > 8, (route, "ohne Grund")
    mit_pruefer = {r for r, e in app.LAN_ERLAUBT.items() if e[1]}
    assert mit_pruefer == set(PROBEN), "jede Route mit Prüfer braucht Proben (und nur die)"


@pytest.mark.parametrize("methode,pfad", ROUTEN)
def test_jede_route_aus_dem_wlan_mit_gueltigem_code(monkeypatch, geroutet, methode, pfad):
    """Das Handy mit richtigem Code: nur-PC-Routen prallen mit 403 ab und
    erreichen den Router nie; erlaubte Routen kommen an."""
    _fernsteuerung(monkeypatch)
    st, _, koerper = _senden(methode, pfad, _proben((methode, pfad))[0], kopf={"X-Code": CODE})
    if (methode, pfad) in app.NUR_PC:
        assert st == 403, (methode, pfad, koerper[:120])
        assert json.loads(koerper).get("nur_pc") is True
        assert geroutet == [], "eine nur-PC-Route darf den Router nicht erreichen"
    else:
        assert st == 200, (methode, pfad, koerper[:120])
        assert geroutet == [(methode, pfad)]


@pytest.mark.parametrize("methode,pfad", ROUTEN)
def test_jede_route_vom_pc(geroutet, methode, pfad):
    """Der PC selbst darf alles, auch die gesperrten Zweige."""
    frei, gesperrt = _proben((methode, pfad))
    for daten in [frei] + gesperrt:
        geroutet.clear()
        st, _, koerper = _senden(methode, pfad, daten, ip="127.0.0.1")
        assert st == 200 and geroutet == [(methode, pfad)], (methode, pfad, daten, koerper[:120])


@pytest.mark.parametrize("route", sorted(PROBEN))
def test_gesperrte_zweige_gemischter_routen(monkeypatch, geroutet, route):
    _fernsteuerung(monkeypatch)
    methode, pfad = route
    for daten in PROBEN[route][1]:
        st, _, koerper = _senden(methode, pfad, daten, kopf={"X-Code": CODE})
        assert st == 403 and json.loads(koerper).get("nur_pc") is True, (route, daten, koerper[:120])
    assert geroutet == []


def test_gekoppeltes_geraet_hat_dieselben_rechte_wie_der_code(monkeypatch, geroutet):
    from test_zugang_und_vertrauen import _gekoppelt
    token = _gekoppelt()
    _fernsteuerung(monkeypatch)
    assert _senden("POST", "/api/config", {"auto_update": False}, kopf={"X-Geraet": token})[0] == 403
    assert _senden("GET", "/api/geraete", kopf={"X-Geraet": token})[0] == 403
    assert _senden("POST", "/api/remote", {"cmd": "play"}, kopf={"X-Geraet": token})[0] == 200
    assert geroutet == [("POST", "/api/remote")]


def test_head_folgt_den_regeln_von_get(monkeypatch, geroutet):
    _fernsteuerung(monkeypatch)
    assert _anfrage("/api/geraete", methode="HEAD", ip=LAN,
                    kopf={"Host": PC_IM_LAN, "X-Code": CODE})[0] == 403
    assert geroutet == []


def test_unbekannte_route_ist_aus_dem_wlan_gesperrt(monkeypatch, geroutet):
    """fail-closed: was in keiner Tabelle steht, geht nur am PC."""
    _fernsteuerung(monkeypatch)
    for methode, pfad in (("GET", "/api/gibtsnicht"), ("POST", "/api/gibtsnicht"),
                          ("GET", "/mediaX"), ("GET", "/api/cover/../../x")):
        st, _, _ = _senden(methode, pfad, kopf={"X-Code": CODE})
        assert st == 403, (methode, pfad)
    assert geroutet == []


# Echte Routen (ohne Zeugen): die Sperre wirkt, bevor die Route etwas tut.

def test_wlan_kann_keine_einstellungen_abos_und_profile_aendern(monkeypatch):
    _fernsteuerung(monkeypatch)
    ziel_vorher = app.CFG.get("ziel_ordner")
    kopf = {"Host": PC_IM_LAN, "X-Code": CODE}
    st, _, _ = _anfrage("/api/config", methode="POST", ip=LAN, kopf=kopf,
                        rumpf={"ziel_ordner": "C:\\Fremd", "fernsteuerung": True})
    assert st == 403 and app.CFG.get("ziel_ordner") == ziel_vorher
    aufrufe = []
    monkeypatch.setattr(app, "abo_aktion", lambda d: aufrufe.append(d) or {"ok": True})
    st, _, _ = _anfrage("/api/abo", methode="POST", ip=LAN, kopf=kopf,
                        rumpf={"art": "entfernen", "id": "..\\x", "mit_videos": True})
    assert st == 403 and aufrufe == []
    import profil_geraete as pg
    vorher = len(pg.profil_liste())
    st, _, _ = _anfrage("/api/profil_anlegen", methode="POST", ip=LAN, kopf=kopf,
                        rumpf={"name": "Fremd"})
    assert st == 403 and len(pg.profil_liste()) == vorher


# JB-Entscheid 7a Punkt 2 als Verhaltensanker (Abnahme 25.09.2026). Die Tests
# oben prüfen, dass der Handler SEINER Tabelle folgt; ob die Tabelle zum
# Entscheid passt, prüften sie nicht: fünf Routen von NUR_PC nach LAN_ERLAUBT
# verschoben, und die Suite blieb grün. Hier steht je Kategorie des Entscheids
# eine feste Route mit typischem Rumpf. Sie läuft durch den ECHTEN Router
# (ohne Zeugen); ein Fühler ersetzt nur die Funktion, die die Wirkung hätte.
# Aus dem WLAN mit gültigem Code: 403 und der Fühler bleibt stumm. Vom PC: der
# Fühler schlägt an (Gegenprobe: er hängt wirklich an dieser Route).
JB_NUR_PC = [
    # (Kategorie des JB-Entscheids, Methode, Pfad, Rumpf bzw. Anfrage, (Ort, Fühler))
    ("Dateien verschieben: Umbenennen", "POST", "/api/umbenennen", {"go": True}, ("app", "migration_anwenden")),
    ("Dateien löschen: Bibliothek", "POST", "/api/biblio", {"art": "loeschen", "id": "k"}, ("handler", "_biblio")),
    ("Dateien löschen: Abo samt Videos", "POST", "/api/abo",
     {"art": "entfernen", "id": "a", "mit_videos": True}, ("app", "abo_aktion")),
    ("Dateien aufnehmen", "POST", "/api/importieren", {}, ("app", "ordner_importieren")),
    ("Programm beenden", "POST", "/api/beenden", {}, ("server", "shutdown")),
    ("WireGuard-Dateien ablegen", "POST", "/api/geo_wireguard",
     {"land": "DE", "content": "[Interface]\nPrivateKey = x\n"}, ("handler", "_geo_wireguard")),
    ("VPN-Test starten", "POST", "/api/geo_test", {}, ("handler", "_geo_test_start")),
    ("Playlists ändern", "POST", "/api/playlist", {"art": "neu", "name": "X"}, ("app", "playlist_aktion")),
    ("Playlists anlegen", "POST", "/api/playlist_import", {"name": "X", "m3u": "#EXTM3U"},
     ("app", "playlist_import_m3u")),
    ("Tags schreiben", "POST", "/api/autotag", {"keys": ["k"]}, ("app", "autotag_lauf")),
    ("Clips erzeugen", "POST", "/api/clip", {"id": "k", "von": 1, "bis": 2}, ("app", "clip_erstellen")),
    ("Bibliothek ändern: Clip-Favorit", "POST", "/api/clip_favorit", {"id": "k"}, ("app", "_clip_favorit_setzen")),
    ("Metadaten schreiben", "POST", "/api/biblio_enrich", {}, ("app", "biblio_enrich_alle")),
    ("Pfade setzen: config.json", "POST", "/api/config", {"ziel_ordner": "C:\\Fremd"}, ("handler", "_config")),
    ("Pfade setzen: Ordnerdialog", "GET", "/api/ordner_waehlen", {"start": "C:\\"}, ("app", "ordner_waehlen")),
    ("config.json: Wiedergabe-Regeln", "POST", "/api/wiedergabe", {"global": 1, "merge": 1, "sub": "an"},
     ("app", "wiedergabe_setzen")),
    ("config.json: neuer Code", "POST", "/api/code_erneuern", {}, ("app", "neuer_fernsteuerungs_code")),
    ("profile.json: Profil anlegen", "POST", "/api/profil_anlegen", {"name": "X"}, ("pg", "profil_anlegen")),
    ("profile.json: Gerät freigeben", "POST", "/api/geraet_bestaetigen", {"id": "g"}, ("pg", "geraet_bestaetigen")),
    ("profile.json: Gerät trennen", "POST", "/api/geraet_entfernen", {"id": "g"}, ("pg", "geraet_entfernen")),
    ("Prozesse am PC: Explorer", "POST", "/api/action", {"art": "ordner_offen"}, ("app", "ordner_zeigen")),
]


@pytest.fixture
def fuehler(monkeypatch):
    """Setzt den Fühler einer JB_NUR_PC-Zeile; liefert die Liste seiner Aufrufe.
    Hintergrundfäden laufen sofort (wie in `eingereiht`), damit auch eine
    Wirkung im Faden (Tags, Metadaten, Beenden) ohne Warten sichtbar ist."""
    import threading
    import types

    import profil_geraete as pg
    monkeypatch.setattr(app, "threading", types.SimpleNamespace(**dict(vars(threading), Thread=_SofortFaden)))

    def setzen(ort, name):
        aufrufe = []

        def spur(*a, **k):
            aufrufe.append(name)
            return {"ok": True}
        if ort == "server":
            monkeypatch.setattr(app.Handler, "server", types.SimpleNamespace(shutdown=spur), raising=False)
        elif ort == "handler":
            monkeypatch.setattr(app.Handler, name, spur)
        else:
            monkeypatch.setattr({"app": app, "pg": pg}[ort], name, spur)
        return aufrufe
    return setzen


def _durch_den_router(methode, pfad, daten, ip):
    kopf = {"X-Code": CODE} if ip == LAN else {}
    return _senden(methode, pfad, daten, ip=ip, kopf=kopf)


@pytest.mark.parametrize("kategorie,methode,pfad,daten,sitz", JB_NUR_PC, ids=[z[0] for z in JB_NUR_PC])
def test_jb_entscheid_diese_wirkungen_nur_am_pc(monkeypatch, fuehler, kategorie, methode, pfad, daten, sitz):
    _fernsteuerung(monkeypatch)
    aufrufe = fuehler(*sitz)
    st, _, koerper = _durch_den_router(methode, pfad, daten, LAN)
    assert st == 403 and json.loads(koerper).get("nur_pc") is True, (kategorie, st, koerper[:120])
    assert aufrufe == [], f"{kategorie}: aus dem WLAN erreichte {pfad} die Wirkung"
    st, _, koerper = _durch_den_router(methode, pfad, daten, "127.0.0.1")
    assert aufrufe == [sitz[1]], f"Gegenprobe: vom PC muss {pfad} den Fühler {sitz[1]} erreichen ({st}, {koerper[:120]})"


def test_fernsteuern_aus_dem_wlan_geht_weiter(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/api/remote", methode="POST", ip=LAN,
                        kopf={"Host": PC_IM_LAN, "X-Code": CODE}, rumpf={"cmd": "next"})
    assert st == 200 and app._remote["cmd"] == "next"


# Tor und Router lesen denselben Pfad (Abnahme 25.09.2026): der POST-Router
# verglich die rohe Adresse samt Anfrageteil. POST /api/filme/merk?profil=…
# (so ruft der Fernsehmodus die Merkliste) lief darum vom PC wie aus dem WLAN
# auf 404 „unbekannt“, und die Oberfläche meldete „Von der Liste genommen“.

def test_film_merkliste_mit_anfrageteil_vom_pc(tmp_path):
    import filme
    st, _, koerper = _anfrage("/api/filme/merk?profil=kinder", methode="POST",
                              kopf={"Host": "127.0.0.1:8776"}, rumpf={"id": "film1"})
    assert st == 200 and json.loads(koerper) == {"an": True}, koerper[:120]
    assert "film1" in filme.merkliste_lesen("kinder"), "gemerkt im Profil aus der Adresse"
    st, _, koerper = _anfrage("/api/filme/merk?profil=kinder", methode="POST",
                              kopf={"Host": "127.0.0.1:8776"}, rumpf={"id": "film1"})
    assert json.loads(koerper) == {"an": False} and "film1" not in filme.merkliste_lesen("kinder")


def test_film_merkliste_mit_anfrageteil_aus_dem_wlan(monkeypatch):
    import filme
    _fernsteuerung(monkeypatch)
    st, _, koerper = _anfrage("/api/filme/merk?profil=egal", methode="POST", ip=LAN,
                              kopf={"Host": PC_IM_LAN, "X-Code": CODE}, rumpf={"id": "film2"})
    assert st == 200 and json.loads(koerper) == {"an": True}, koerper[:120]
    assert "film2" in filme.merkliste_lesen("standard"), "mit Code gilt das Standard-Profil, nie die Adresse"


def test_post_mit_anfrageteil_erreicht_dieselbe_route(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/api/remote?von=tv", methode="POST", ip=LAN,
                        kopf={"Host": PC_IM_LAN, "X-Code": CODE}, rumpf={"cmd": "next"})
    assert st == 200 and app._remote["cmd"] == "next"
    st, _, koerper = _anfrage("/api/config?x=1", methode="POST", ip=LAN,
                              kopf={"Host": PC_IM_LAN, "X-Code": CODE}, rumpf={"ziel_ordner": "C:\\Fremd"})
    assert st == 403 and json.loads(koerper).get("nur_pc") is True, "das Tor sieht denselben Pfad wie der Router"


# ------------------------------------------------------------ S10: eine Schreibweise, ::1 ist lokal

@pytest.mark.parametrize("ip", ["127.0.0.1", "::1", "127.0.0.2", "::ffff:127.0.0.1"])
def test_loopback_in_jeder_schreibweise_ist_der_pc(tmp_path, ip):
    """Vorher wiesen sechs Stellen mit `client_address != "127.0.0.1"` den PC
    ab, wenn er über ::1 kam. Jetzt entscheidet überall `_ist_lokal`."""
    st, _, koerper = _anfrage("/api/pfad_da?" + urlencode({"pfad": str(tmp_path)}), ip=ip,
                              kopf={"Host": "[::1]:8776" if ":" in ip else "127.0.0.1:8776"})
    assert st == 200 and json.loads(koerper) == {"da": True}, (ip, koerper[:120])


@pytest.mark.parametrize("ip", [LAN, "10.0.0.7", "::ffff:192.168.178.50", "fe80::1", ""])
def test_nicht_loopback_ist_nie_der_pc(ip):
    assert not app.ist_loopback(ip)


# ------------------------------------------------------------ Nachschärfung S2: Host-Regel

@pytest.mark.parametrize("host", [
    "jb-pc", "jb-pc:8776", "JB-PC.fritz.box:8776", "jb-pc.local:8776", "jb-pc.lan:8776",
    "jb-pc.home.arpa:8776", "jb-pc.localdomain:8776", "jb-pc.fritz.box.:8776",
    "localhost:8776", "192.168.178.20:8776", "[::1]:8776"])
def test_host_eigener_name_mit_heimnetz_endung(host):
    assert _anfrage("/api/status", kopf={"Host": host})[0] == 200, host


@pytest.mark.parametrize("host", [
    "jb-pc.fremde-domain.de:8776", "jb-pc.example:8776", "jb-pc.local.angreifer.de:8776",
    "jb-pc.fritz.box.angreifer.de:8776", "jb-pc.home:8776", "jb-pc.arpa:8776",
    "localhost.local:8776", "anderer-pc.fritz.box:8776", "jb-pc-x.lan:8776"])
def test_host_eigener_name_unter_fremder_domain_wird_abgewiesen(host):
    """Vorher reichte das erste Label: jb-pc.fremde-domain.de kam durch, und
    wer diesen Namen im DNS besitzt, kann ihn per Rebinding auf 127.0.0.1 zeigen."""
    assert _anfrage("/api/status", kopf={"Host": host})[0] == 403, host


def test_dashboard_darf_auch_unter_localhost_einbetten():
    st, koepfe, _ = _anfrage("/?embed=1", kopf={"Host": "127.0.0.1:8776"})
    csp = " ".join(koepfe.get("content-security-policy", []))
    assert st == 200
    assert "http://127.0.0.1:8765" in csp and "http://localhost:8765" in csp, csp


# ------------------------------------------------------------ Nachschärfung S13: ehrlicher Text

@pytest.mark.parametrize("pfad", ["/", "/m", "/koppeln", "/fernbedienung"])
def test_gekoppeltes_geraet_sieht_fernsteuerung_aus_statt_nicht_gekoppelt(monkeypatch, pfad):
    from test_zugang_und_vertrauen import _gekoppelt
    token = _gekoppelt()
    _fernsteuerung(monkeypatch, an=False)
    st, koepfe, koerper = _anfrage(pfad, ip=LAN, kopf={"Host": PC_IM_LAN, "X-Geraet": token})
    text = koerper.decode("utf-8")
    assert st == 403, (pfad, text[:120])
    assert "Fernsteuerung am PC ausgeschaltet" in text and "nicht gekoppelt" not in text, text[:200]
    assert koepfe["content-type"][0].startswith("text/html"), "eine Seite zeigt Text, kein JSON"


def test_api_meldet_fernsteuerung_aus_ebenso(monkeypatch):
    _fernsteuerung(monkeypatch, an=False)
    for methode, pfad in (("GET", "/api/status"), ("POST", "/api/remote")):
        st, _, koerper = _senden(methode, pfad, {"cmd": "play"} if methode == "POST" else None,
                                 kopf={"X-Code": CODE})
        assert st == 403 and "Fernsteuerung am PC ausgeschaltet" in json.loads(koerper)["fehler"]
    assert app._remote["n"] == 0


# ------------------------------------------------------------ 7a Punkt 7: Links aus dem WLAN nur YouTube

class _SofortFaden:
    """Ersatz für threading.Thread in `_add`: führt das Ziel sofort aus, damit
    der Test ohne Warten sieht, welche Links eingereiht wurden."""

    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self._ziel, self._args, self._kwargs = target, args, kwargs or {}

    def start(self):
        self._ziel(*self._args, **self._kwargs)


@pytest.fixture
def eingereiht(monkeypatch):
    import threading
    import types
    links = []
    monkeypatch.setattr(app, "aufloesen", lambda url, *a, **k: links.append(url))
    monkeypatch.setattr(app, "threading", types.SimpleNamespace(**dict(vars(threading), Thread=_SofortFaden)))
    return links


def _add(urls, ip=LAN, **mehr):
    kopf = {"X-Code": CODE} if ip == LAN else {}
    return _senden("POST", "/api/add", dict({"urls": urls}, **mehr), ip=ip, kopf=kopf)


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=abcdefghijk", "https://youtube.com/watch?v=abcdefghijk",
    "https://m.youtube.com/watch?v=abcdefghijk", "https://music.youtube.com/watch?v=abcdefghijk",
    "https://youtu.be/abcdefghijk", "https://www.youtube-nocookie.com/embed/abcdefghijk",
    "https://youtube-nocookie.com/embed/abcdefghijk", "http://www.youtube.com/playlist?list=PLx",
    "https://WWW.YOUTUBE.COM./@kanal", "  https://www.youtube.com/watch?v=abcdefghijk\n"])
def test_wlan_darf_youtube_links_laden(monkeypatch, eingereiht, url):
    _fernsteuerung(monkeypatch)
    st, _, koerper = _add(url)
    assert st == 200, (url, koerper[:120])
    assert eingereiht == [url.strip()]


@pytest.mark.parametrize("urls", [
    "https://vimeo.com/123", "https://youtube.com.angreifer.de/watch?v=x",
    "https://angreifer.de/?u=https://www.youtube.com/", "https://www.youtube.com@angreifer.de/",
    "https://angreifer.de@www.youtube.com/watch?v=x", "https://www.youtube.com\\@angreifer.de/",
    "https://www.youtube.com:8776/watch?v=x", "ftp://www.youtube.com/x", "javascript:alert(1)",
    "https://www.youtube.com/watch?v=a\nhttps://www.youtube.com/watch?v=b",
    "https://www.youtube.com/watch?v=a\rhttp://127.0.0.1:8779/",
    "https://www.youtube.com/watch?v=a https://angreifer.de/",
    "https://www.youtube.com/watch?v=a\thttps://angreifer.de/", "", ["https://www.youtube.com/watch?v=a"],
    "http://127.0.0.1:8779/api/x",
    # Unicode-Zeilentrenner: str.splitlines() in `_add` teilt auch dort (Abnahme 25.09.2026)
    "https://www.youtube.com/watch?v=abcdefghijk https://vimeo.com/123",
    "https://www.youtube.com/watch?v=abcdefghijk https://vimeo.com/123",
    "https://www.youtube.com/watch?v=abcdefghijk\x85https://vimeo.com/123",
    "https://www.youtube.com/watch?v=abcdefghijk https://vimeo.com/123"])
def test_wlan_andere_und_mehrere_links_werden_abgelehnt(monkeypatch, eingereiht, urls):
    _fernsteuerung(monkeypatch)
    st, _, koerper = _add(urls)
    assert st == 403 and json.loads(koerper).get("nur_pc") is True, (urls, koerper[:120])
    assert eingereiht == []


@pytest.mark.parametrize("zeichen", [" ", " ", "\x85", " ", "　", "\x1c", "​"])
def test_youtube_link_mit_trenner_oder_steuerzeichen_gilt_nicht(zeichen):
    """Prüfer und Router zerlegen gleich: was `splitlines` trennt, was als
    Leerraum gilt und jedes Steuer- oder Formatzeichen macht den Link ungültig."""
    assert app.ist_youtube_link("https://www.youtube.com/watch?v=abcdefghijk")
    assert not app.ist_youtube_link(f"https://www.youtube.com/watch?v=abc{zeichen}defghijk"), repr(zeichen)


def test_wlan_reiht_nicht_in_eine_playlist_ein(monkeypatch, eingereiht):
    """ziel_playlist legt Titel in eine Playlist: Playlists ändern geht nur am PC."""
    _fernsteuerung(monkeypatch)
    st, _, _ = _add("https://www.youtube.com/watch?v=abcdefghijk", ziel_playlist="Entdeckt")
    assert st == 403 and eingereiht == []


def test_wlan_kanal_info_nur_fuer_youtube(monkeypatch):
    _fernsteuerung(monkeypatch)
    abrufe = []
    monkeypatch.setattr(app, "kanal_info", lambda url, limit=None: abrufe.append(url) or {"n": 1})
    kopf = {"X-Code": CODE}
    assert _senden("GET", "/api/kanal_info", {"url": "https://www.youtube.com/@kanal"}, kopf=kopf)[0] == 200
    assert _senden("GET", "/api/kanal_info", {"url": "http://127.0.0.1:8779/"}, kopf=kopf)[0] == 403
    assert _senden("GET", "/api/kanal_info", {"url": "https://angreifer.de/"}, kopf=kopf)[0] == 403
    assert abrufe == ["https://www.youtube.com/@kanal"]


# Vom PC geht jeder http(s)-Link wie bisher, nur nie einer auf den eigenen Rechner.

@pytest.fixture
def aufloesung(monkeypatch):
    """Namensauflösung und eigene Adressen als Attrappe (kein DNS im Test)."""
    namen = {"zeigt-auf-loopback.example": {"127.0.0.1"}, "zeigt-auf-mich.example": {"192.168.178.20"},
             "vimeo.com": {"151.101.0.217"}, "gemischt.example": {"93.184.216.34", "::1"}}

    def aufloesen(host):
        if host in ("www.youtube.com", "youtube.com", "youtu.be"):
            raise AssertionError("YouTube-Links brauchen keine Namensauflösung")
        return namen.get(host, set())
    monkeypatch.setattr(app, "_namen_aufloesen", aufloesen)
    monkeypatch.setattr(app, "_eigene_adressen", lambda: {"192.168.178.20", "fe80::1"})


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8779/x", "http://127.1:8779/x", "http://2130706433:8779/x",
    "http://0x7f000001/x", "http://0x7f.1/x", "http://0177.0.0.1/x", "http://127.0.1/x",
    "http://0/x", "http://0.0.0.0:8779/x", "http://[::1]:8778/x", "http://[::ffff:127.0.0.1]/x",
    "http://[::ffff:7f00:1]/x", "http://[0:0:0:0:0:0:0:1]/x", "http://localhost:8779/x",
    "http://LOCALHOST./x", "http://foo.localhost/x", "http://zeigt-auf-loopback.example/x",
    "http://zeigt-auf-mich.example:8776/x", "http://192.168.178.20:8776/api/cover?id=x",
    "http://gemischt.example/x", "http://[fe80::1]/x"])
def test_pc_links_auf_den_eigenen_rechner_werden_nie_eingereiht(eingereiht, aufloesung, url):
    st, _, _ = _add(url, ip="127.0.0.1")
    assert st == 200 and eingereiht == [], url


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=abcdefghijk", "https://vimeo.com/123",
    "http://192.168.178.99/film.mp4", "https://unbekannt.example/x"])
def test_pc_darf_fremde_links_wie_bisher(eingereiht, aufloesung, url):
    """Vom PC bleibt alles erlaubt, was nicht auf ihn selbst zeigt (auch ein
    anderes Gerät im Heimnetz und ein Name, der sich gerade nicht auflösen lässt:
    dann scheitert der Download ehrlich in der Liste)."""
    st, _, _ = _add(url, ip="127.0.0.1")
    assert st == 200 and eingereiht == [url], url


def test_pc_mehrere_zeilen_bleiben_erlaubt(eingereiht, aufloesung):
    st, _, _ = _add("https://www.youtube.com/watch?v=a\nhttp://127.1/x\nhttps://vimeo.com/1", ip="127.0.0.1")
    assert st == 200 and eingereiht == ["https://www.youtube.com/watch?v=a", "https://vimeo.com/1"]


# ------------------------------------------------------------ 7a Punkt 3: längere Codes, „Code erneuern“

LESBAR = set("ABCDEFGHJKMNPQRSTUVWXYZ23456789")        # ohne 0/O, 1/I/L
PC = {"Host": "127.0.0.1:8776"}


def test_neuer_code_ist_lang_und_gut_lesbar(monkeypatch):
    """Vorher 6 Hex-Zeichen (16,8 Millionen Möglichkeiten, 0 und O verwechselbar)."""
    monkeypatch.setitem(app.CFG, "fernsteuerung", False)
    monkeypatch.setitem(app.CFG, "fernsteuerung_code", "")
    st, _, _ = _anfrage("/api/config", methode="POST", kopf=PC, rumpf={"fernsteuerung": True})
    code = app.CFG["fernsteuerung_code"]
    assert st == 200 and len(code) >= 10 and set(code) <= LESBAR, code
    codes = {app.neuer_fernsteuerungs_code() for _ in range(200)}
    assert len(codes) == 200 and all(len(c) >= 10 for c in codes)
    assert set("".join(codes)) == LESBAR, "das ganze lesbare Alphabet, nicht nur Hex"


def test_bisheriger_code_bleibt_bis_zum_klick(monkeypatch):
    """Kein Zwangswechsel beim Update: Aus- und Einschalten und andere
    Einstellungen lassen einen vorhandenen (alten, kurzen) Code stehen."""
    _fernsteuerung(monkeypatch)
    for rumpf in ({"fernsteuerung": False}, {"fernsteuerung": True}, {"metadaten": True}):
        assert _anfrage("/api/config", methode="POST", kopf=PC, rumpf=rumpf)[0] == 200
    assert app.CFG["fernsteuerung_code"] == CODE
    assert _senden("GET", "/api/status", kopf={"X-Code": CODE})[0] == 200


def test_code_erneuern_am_pc(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, _, koerper = _anfrage("/api/code_erneuern", methode="POST", kopf=PC, rumpf={})
    neu = app.CFG["fernsteuerung_code"]
    assert st == 200 and neu != CODE and len(neu) >= 10 and set(neu) <= LESBAR, neu
    assert json.loads(koerper)["code"] == neu
    with open(app.CONFIG_PFAD, encoding="utf-8") as f:
        assert json.load(f)["fernsteuerung_code"] == neu, "der neue Code überlebt den Neustart"
    assert _senden("GET", "/api/status", kopf={"X-Code": CODE})[0] == 403, "der alte Code gilt nicht mehr"
    assert _senden("GET", "/api/status", kopf={"X-Code": neu})[0] == 200


def test_code_erneuern_nicht_aus_dem_wlan(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, _, _ = _senden("POST", "/api/code_erneuern", {}, kopf={"X-Code": CODE})
    assert st == 403 and app.CFG["fernsteuerung_code"] == CODE


def test_handy_nimmt_lange_codes_an():
    """Das Eingabefeld der Handy-Seite schnitt nach 6 Zeichen ab."""
    from html.parser import HTMLParser
    import handy

    class Feld(HTMLParser):
        attrs = None

        def handle_starttag(self, tag, attrs):
            if tag == "input" and dict(attrs).get("id") == "code":
                Feld.attrs = dict(attrs)
    Feld().feed(handy.HTML)
    assert Feld.attrs is not None
    assert int(Feld.attrs.get("maxlength") or 999) >= 10, Feld.attrs


def test_knopf_code_erneuern_in_den_einstellungen(tmp_path):
    from test_medientasten_verhalten import _js_funktion, _lauf, _pc
    q = _pc()
    (an, aus_) = _lauf(
        tmp_path,
        "function esc(t){return String(t==null?'':t);}",
        "_els.fernbtn={textContent:''}; _els.ferninfo={innerHTML:'',textContent:''};",
        "_els['fern-symbol']={style:{}};",
        "let daten={fernsteuerung:{aktiv:true,code:'ABCDEFGHJK',url:'http://pc:8776/m'}};",
        _js_funktion(q, "fernInfoMalen"),
        "fernInfoMalen(); aus({html:_els.ferninfo.innerHTML});",
        "daten={fernsteuerung:{aktiv:false,code:'',url:''}}; _els.ferninfo.innerHTML='';",
        "fernInfoMalen(); aus({html:_els.ferninfo.innerHTML, text:_els.ferninfo.textContent});")
    assert "ABCDEFGHJK" in an["html"] and "fernCodeErneuern()" in an["html"], an
    assert "Code erneuern" in an["html"]
    assert "fernCodeErneuern" not in aus_["html"], "ausgeschaltet gibt es keinen Code zu erneuern"


def test_code_erneuern_nur_im_einstellungs_menue(tmp_path):
    """JB-Entscheid 7a Punkt 3 nennt EINEN Knopf „Code erneuern“ in den
    Einstellungen. Ein zweiter im 📱-Fenster der Kopfleiste war nicht
    beauftragt (Abnahme 25.09.2026, Regel „jeden Knopf rechtfertigen“); ob er
    dort erwünscht ist, fragt der Bericht JB. Das Fenster zeigt Code und Link."""
    from test_medientasten_verhalten import _js_funktion, _lauf, _pc
    q = _pc()
    (e,) = _lauf(
        tmp_path,
        "function esc(t){return String(t==null?'':t);} function menuGeradeZu(){return false;}",
        "function popoverBei(){} function menuSchliesser(){}",
        "const _m=[]; document.createElement=()=>{const m={style:{}}; _m.push(m); return m;};",
        "document.body={appendChild(){}}; document.querySelectorAll=()=>[];",
        "let daten={fernsteuerung:{aktiv:true,code:'ABCDEFGHJK',url:'http://pc:8776/m'}};",
        _js_funktion(q, "fernFenster"),
        "fernFenster({currentTarget:{getBoundingClientRect(){return {};}}}); aus({html:_m[0].innerHTML});")
    assert "ABCDEFGHJK" in e["html"] and "http://pc:8776/m" in e["html"], e
    assert "fernCodeErneuern" not in e["html"], "der Knopf gehört ins ⚙-Menü, nicht zusätzlich hierher"
    assert "fernToggle()" in e["html"], "Ausschalten bleibt im Fenster"


def test_code_erneuern_fragt_und_holt_den_neuen_stand(tmp_path):
    from test_medientasten_verhalten import _js_funktion, _lauf, _pc
    q = _pc()
    (e,) = _lauf(
        tmp_path,
        "const _spur=[]; let _jaSagen=true;",
        "function frageModal(text,ja,onJa){_spur.push('frage'); if(_jaSagen)onJa();}",
        "globalThis.fetch=async(url,opt)=>{_spur.push((opt&&opt.method||'GET')+' '+url);"
        " return {ok:true,status:200,json:async()=>({code:'NEU2345678'})};};",
        "async function laden(){_spur.push('laden');} function fernInfoMalen(){_spur.push('malen');}",
        "function toast(t){_spur.push('toast:'+t);}",
        _js_funktion(q, "fernCodeErneuern"),
        "await fernCodeErneuern(); await new Promise(r=>setTimeout(r,0));",
        "const nachJa=_spur.slice(); _spur.length=0; _jaSagen=false; await fernCodeErneuern();",
        "aus({nachJa, nachNein:_spur.slice()});")
    assert e["nachJa"][:2] == ["frage", "POST /api/code_erneuern"], e
    assert "laden" in e["nachJa"] and any("NEU2345678" in s for s in e["nachJa"]), e
    assert e["nachNein"] == ["frage"], "ohne Bestätigung ändert sich nichts"


# ------------------------------------------------------------ 7a Punkt 1: Kopplung und Code per Cookie (S17, F9)

def _kekse(koepfe):
    """name -> vollständige Set-Cookie-Zeile."""
    return {z.split("=", 1)[0].strip(): z for z in koepfe.get("set-cookie", [])}


def _attribute(zeile):
    teile = [t.strip() for t in zeile.split(";")]
    return teile[0].split("=", 1)[1], {t.split("=", 1)[0].lower(): (t.split("=", 1) + [""])[1] for t in teile[1:]}


def _mit_gekoppeltem_geraet(monkeypatch):
    from test_zugang_und_vertrauen import _gekoppelt
    token = _gekoppelt()
    _fernsteuerung(monkeypatch)
    return token


@pytest.mark.parametrize("pfad,ziel", [("/?geraet={t}", "/"), ("/?embed=1&geraet={t}", "/?embed=1"),
                                       ("/index.html?geraet={t}&profil=x", "/index.html?profil=x"),
                                       ("/m?geraet={t}", "/m")])
def test_token_in_der_adresse_wird_cookie_und_verschwindet(monkeypatch, pfad, ziel):
    token = _mit_gekoppeltem_geraet(monkeypatch)
    st, koepfe, _ = _anfrage(pfad.format(t=token), ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 302, (pfad, st)
    assert koepfe["location"] == [ziel], koepfe.get("location")
    wert, attr = _attribute(_kekse(koepfe)["syncyt_geraet"])
    assert wert == token
    assert "httponly" in attr and attr.get("samesite") == "Strict" and attr.get("path") == "/"
    assert int(attr["max-age"]) >= 365 * 24 * 3600, "der Token-Keks hält lange"
    assert token not in " ".join(koepfe["location"])


def test_code_in_der_adresse_wird_cookie_und_verschwindet(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, koepfe, _ = _anfrage(f"/m?code={CODE}", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 302 and koepfe["location"] == ["/m"]
    wert, attr = _attribute(_kekse(koepfe)["syncyt_code"])
    assert wert == CODE and "httponly" in attr and attr.get("samesite") == "Strict"


def test_das_cookie_oeffnet_seite_api_und_post(monkeypatch):
    """F9: Die Aufrufe der Oberfläche auf einem gekoppelten Gerät trugen keinen
    Zugang und bekamen 403. Mit dem Cookie tragen sie ihn von selbst."""
    token = _mit_gekoppeltem_geraet(monkeypatch)
    for keks in (f"syncyt_geraet={token}", f"syncyt_code={CODE}",
                 f"andere_app=1; syncyt_geraet={token}; kaputt"):
        kopf = {"Host": PC_IM_LAN, "Cookie": keks}
        st, koepfe, koerper = _anfrage("/", ip=LAN, kopf=kopf)
        assert st == 200 and b"<html" in koerper[:400].lower(), keks
        st, koepfe, _ = _anfrage("/api/status", ip=LAN, kopf=kopf)
        assert st == 200 and "set-cookie" not in koepfe, "ein API-Aufruf setzt das Cookie nie neu"
        st, koepfe, _ = _anfrage("/api/remote", methode="POST", ip=LAN, kopf=kopf, rumpf={"cmd": "next"})
        assert st == 200 and "set-cookie" not in koepfe
    assert app._remote["cmd"] == "next"


# Gleitende Verlängerung (Abnahme 25.09.2026): Das Token-Cookie lief 400 Tage
# nach der KOPPLUNG ab, danach stand der Fernseher wieder auf der
# Kopplungsseite. Jetzt setzt jede SEITE (nicht jeder API-Aufruf, die
# Oberfläche fragt jede Sekunde) ein gültiges Token-Cookie mit voller
# Laufzeit neu: die 400 Tage zählen ab dem letzten Öffnen.

@pytest.mark.parametrize("seite", ["/", "/index.html", "/m", "/?embed=1"])
def test_seite_verlaengert_das_token_cookie(monkeypatch, seite):
    token = _mit_gekoppeltem_geraet(monkeypatch)
    st, koepfe, _ = _anfrage(seite, ip=LAN, kopf={"Host": PC_IM_LAN, "Cookie": f"syncyt_geraet={token}"})
    assert st == 200, (seite, st)
    wert, attr = _attribute(_kekse(koepfe)["syncyt_geraet"])
    assert wert == token and int(attr["max-age"]) == app.COOKIE_DAUER["syncyt_geraet"]
    assert "httponly" in attr and attr.get("samesite") == "Strict" and attr.get("path") == "/"


def test_code_cookie_wird_nicht_verlaengert(monkeypatch):
    """Der Code gilt 30 Tage ab der Eingabe (offene Frage an JB, ob länger)."""
    _fernsteuerung(monkeypatch)
    st, koepfe, _ = _anfrage("/m", ip=LAN, kopf={"Host": PC_IM_LAN, "Cookie": f"syncyt_code={CODE}"})
    assert st == 200 and "set-cookie" not in koepfe


def test_kopf_und_adresse_bleiben_als_rueckfall(monkeypatch):
    """Kein Zwang zum Cookie: X-Code/X-Geraet und ?code= auf API-Wegen gehen
    weiter (ohne Umleitung; ein Medien-Strom folgt keiner). Der Server setzt
    dabei das Cookie, damit Bild- und Medien-Adressen den Code nicht brauchen."""
    token = _mit_gekoppeltem_geraet(monkeypatch)
    st, koepfe, _ = _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN, "X-Code": CODE})
    assert st == 200 and "syncyt_code" in _kekse(koepfe)
    st, koepfe, _ = _anfrage(f"/api/profile?geraet={token}", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 200 and "location" not in koepfe and "syncyt_geraet" in _kekse(koepfe)
    st, koepfe, _ = _anfrage(f"/media?id=gibtsnicht&code={CODE}", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 404 and "location" not in koepfe, "API-Wege antworten direkt"


def test_ungueltiges_cookie_wird_geloescht_und_zaehlt_einmal(monkeypatch):
    """Ein veraltetes Cookie (Code erneuert, Gerät getrennt) schickte die
    Oberfläche jede Sekunde mit: ohne Löschen liefe das Gerät nach zehn
    Sekunden in die Versuchsbremse, bis zu 15 Minuten."""
    _fernsteuerung(monkeypatch)
    kopf = {"Host": PC_IM_LAN, "Cookie": "syncyt_code=ALTERCODE1; syncyt_geraet=0123456789abcdef"}
    st, koepfe, _ = _anfrage("/api/status", ip=LAN, kopf=kopf)
    assert st == 403
    for name in ("syncyt_code", "syncyt_geraet"):
        wert, attr = _attribute(_kekse(koepfe)[name])
        assert wert == "" and attr.get("max-age") == "0", (name, koepfe.get("set-cookie"))
    assert app._fehlversuche[LAN]["n"] == 1
    st, _, koerper = _anfrage("/", ip=LAN, kopf=kopf)
    assert st == 200 and b"koppeln" in koerper.lower(), "ohne gültigen Zugang: die Koppel-Seite"


def test_fernsteuerung_aus_loescht_das_cookie_nicht(monkeypatch):
    """Aus heißt aus — aber wieder an heißt: das Gerät ist ohne neue Kopplung da."""
    token = _mit_gekoppeltem_geraet(monkeypatch)
    app.CFG["fernsteuerung"] = False
    st, koepfe, _ = _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN, "Cookie": f"syncyt_geraet={token}"})
    assert st == 403 and "set-cookie" not in koepfe


def test_kopplungs_code_der_koppelseite_zaehlt_nicht_als_fehlversuch(monkeypatch):
    """/api/geraet_status trägt den KOPPLUNGS-Code in `code` (alle 3 s): der
    ist kein Fernsteuerungs-Code und darf die Bremse nicht füllen."""
    import profil_geraete as pg
    _fernsteuerung(monkeypatch)
    a = pg.geraet_anmelden("TV")
    for _ in range(12):
        st, koepfe, _ = _anfrage(f"/api/geraet_status?id={a['geraet_id']}&code={a['code']}",
                                 ip=LAN, kopf={"Host": PC_IM_LAN})
        assert st == 200 and "set-cookie" not in koepfe
    assert LAN not in app._fehlversuche or app._fehlversuche[LAN]["n"] == 0


def test_pc_bekommt_nie_ein_cookie():
    st, koepfe, _ = _anfrage(f"/?code={CODE}", kopf={"Host": "127.0.0.1:8776"})
    assert st == 200 and "set-cookie" not in koepfe


@pytest.mark.parametrize("pfad,methode,ip", [
    ("/", "GET", "127.0.0.1"), ("/api/status", "GET", "127.0.0.1"), ("/api/gibtsnicht", "GET", "127.0.0.1"),
    ("/api/status", "GET", LAN), ("/", "GET", LAN), ("/api/remote", "POST", LAN)])
def test_jede_antwort_verbietet_den_referrer(monkeypatch, pfad, methode, ip):
    """Ein Link aus der Oberfläche (etwa ↗ YouTube) nimmt die Adresse der
    Seite nie mit; früher stand dort der Token oder Code."""
    _fernsteuerung(monkeypatch)
    st, koepfe, _ = _senden(methode, pfad, {"cmd": "play"} if methode == "POST" else None, ip=ip)
    assert koepfe.get("referrer-policy") == ["no-referrer"], (pfad, st, koepfe)


def test_status_meldet_ob_die_seite_am_pc_laeuft(monkeypatch):
    token = _mit_gekoppeltem_geraet(monkeypatch)
    _, _, koerper = _anfrage("/api/status", kopf={"Host": "127.0.0.1:8776"})
    assert json.loads(koerper)["lokal"] is True
    _, _, koerper = _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN, "Cookie": f"syncyt_geraet={token}"})
    d = json.loads(koerper)
    assert d["lokal"] is False and "fernsteuerung" not in d and "ziel" not in d
    assert "wiedergabe" in d["config"], "ein gekoppelter Fernseher spielt mit JBs Wiedergabe-Regeln"
    assert "ziel_ordner" not in d["config"] and "fernsteuerung_code" not in d["config"]


def test_profil_des_geraets_kommt_aus_dem_cookie(monkeypatch):
    import profil_geraete as pg
    _fernsteuerung(monkeypatch)
    p = pg.profil_anlegen("Kinder", "🐻")
    a = pg.geraet_anmelden("TV")
    assert pg.geraet_bestaetigen(a["geraet_id"], p["id"])
    token = pg.geraet_token_abholen(a["geraet_id"], a["code"])["token"]
    _, _, koerper = _anfrage("/api/profile", ip=LAN, kopf={"Host": PC_IM_LAN, "Cookie": f"syncyt_geraet={token}"})
    assert json.loads(koerper)["aktiv"] == p["id"]


def test_wlan_darf_einen_verschobenen_titel_neu_laden(monkeypatch, geroutet):
    """„⬇ Erneut herunterladen“ im Bibliotheks-Menü ist ein Download-Anstoß
    (7a Punkt 2), also aus dem WLAN erlaubt; alle anderen Zweige nicht."""
    _fernsteuerung(monkeypatch)
    st, _, _ = _senden("POST", "/api/biblio", {"art": "neuladen", "id": "abc"}, kopf={"X-Code": CODE})
    assert st == 200 and geroutet == [("POST", "/api/biblio")]


# „Trotzdem laden“ (Abnahme 25.09.2026): ein übersprungener Eintrag wird mit
# erzwingen neu geladen, yt-dlp ersetzt die vorhandene Datei (overwrites) ohne
# Papierkorb. Das ist Dateien löschen im Sinne von 7a Punkt 2 und geht bis zu
# JBs Antwort nur am PC; Weiter nach Pause oder Fehler bleibt im WLAN erlaubt.

def _eintrag(status):
    it = app.Q.neu("https://www.youtube.com/watch?v=abcdefghijk", "Titel", "beste")
    with app.Q.lock:
        it["status"] = status
    return it


@pytest.fixture
def ohne_download(monkeypatch):
    """Ein Eintrag auf „wartend“ lädt nie wirklich (falls ein Worker läuft)."""
    monkeypatch.setattr(app, "herunterladen", lambda item: None)


def test_trotzdem_laden_ersetzt_die_datei_nur_am_pc(monkeypatch, ohne_download):
    _fernsteuerung(monkeypatch)
    it = _eintrag("uebersprungen")
    st, _, koerper = _senden("POST", "/api/action", {"art": "weiter", "id": it["id"]}, kopf={"X-Code": CODE})
    assert st == 403 and json.loads(koerper).get("nur_pc") is True, koerper[:120]
    assert it["status"] == "uebersprungen" and not it.get("erzwingen"), it
    st, _, _ = _senden("POST", "/api/action", {"art": "weiter", "id": it["id"]}, ip="127.0.0.1")
    assert st == 200 and it.get("erzwingen") is True and it["status"] == "wartend", "vom PC wie bisher"


@pytest.mark.parametrize("status", ["pausiert", "fehler"])
def test_weiter_nach_pause_oder_fehler_geht_aus_dem_wlan(monkeypatch, ohne_download, status):
    _fernsteuerung(monkeypatch)
    it = _eintrag(status)
    st, _, _ = _senden("POST", "/api/action", {"art": "weiter", "id": it["id"]}, kopf={"X-Code": CODE})
    assert st == 200 and it["status"] == "wartend" and not it.get("erzwingen"), it
