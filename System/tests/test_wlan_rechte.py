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

def _ist_pfad_ausdruck(k):
    """`self.path` oder `urlparse(self.path).path`."""
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
        for k in ast.walk(methoden[name]):
            werte = []
            if isinstance(k, ast.Compare) and _ist_pfad_ausdruck(k.left):
                for op, rechts in zip(k.ops, k.comparators):
                    if isinstance(op, ast.Eq):
                        werte.append(rechts)
                    elif isinstance(op, ast.In) and isinstance(rechts, (ast.Tuple, ast.List, ast.Set)):
                        werte.extend(rechts.elts)
            elif (isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute)
                  and k.func.attr == "startswith" and _ist_pfad_ausdruck(k.func.value)):
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


def test_fernsteuern_aus_dem_wlan_geht_weiter(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/api/remote", methode="POST", ip=LAN,
                        kopf={"Host": PC_IM_LAN, "X-Code": CODE}, rumpf={"cmd": "next"})
    assert st == 200 and app._remote["cmd"] == "next"


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
    "http://127.0.0.1:8779/api/x"])
def test_wlan_andere_und_mehrere_links_werden_abgelehnt(monkeypatch, eingereiht, urls):
    _fernsteuerung(monkeypatch)
    st, _, koerper = _add(urls)
    assert st == 403 and json.loads(koerper).get("nur_pc") is True, (urls, koerper[:120])
    assert eingereiht == []


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
