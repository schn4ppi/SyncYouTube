# -*- coding: utf-8 -*-
"""Routentabelle des Handlers (Gesamtprüfung Y7, 25.09.2026).

Vorher verteilten zwei if/elif-Ketten die Anfragen (43 GET-Zweige, 34 POST-
Zweige). Jetzt steht jede Route einmal in `ROUTEN` {(Methode, Pfad): Name
der Handler-Methode}; verglichen wird genau mit `urlparse(self.path).path`,
HEAD folgt GET. Geprüft wird hier, dass der Router wirklich nach dieser
Tabelle verteilt und nach nichts sonst, dass jede Tabellenzeile ihre Methode
erreicht, dass der Methodenname aus dem Pfad folgt (Nacharbeit: sonst fiele
ein Zeilentausch nicht auf, die Rechte hängen am Pfad), und die
Reihenfolge-Fallen der alten Kette. Die Rechte (LAN_ERLAUBT,
NUR_PC) prüft tests/test_wlan_rechte.py, abgeleitet aus derselben Tabelle.

Wie in test_zugang_und_vertrauen.py läuft jede Anfrage durch den ECHTEN
Handler, ohne Server und ohne Socket; ein Zeuge ersetzt nur die Methode der
Route, damit keine Route etwas tut (kein Download, kein VLC, kein Netz).
"""
import ast
import inspect
import json
import os
import sys
import textwrap
from urllib.parse import urlparse

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
for _pfad in (MODUL_DIR, TEST_DIR):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import _anfrage, rechner  # noqa: E402,F401  (rechner: autouse)

PC = {"Host": "127.0.0.1:8776"}
VERTEILER = ("_get_routen", "_post_routen")


def tabellen_fehler(routen, handler):
    """Was an einer Routentabelle nicht stimmt (leer = alles gut): Methode
    fehlt, falsches Präfix, Pfad nicht genau, Route-Methode ohne Tabellenzeile."""
    fehler = []
    for (verb, pfad), name in routen.items():
        if verb not in ("GET", "POST"):
            fehler.append(f"{verb} {pfad}: unbekannte Methode")
        if not (pfad.startswith("/") and "?" not in pfad and "#" not in pfad):
            fehler.append(f"{verb} {pfad}: kein reiner Pfad")
        if not name.startswith(f"_{verb.lower()}_") or name in VERTEILER:
            fehler.append(f"{verb} {pfad}: {name} passt nicht zur Methode")
        if not callable(getattr(handler, name, None)):
            fehler.append(f"{verb} {pfad}: Handler.{name} fehlt")
    genannt = set(routen.values())
    for name in dir(handler):
        if name.startswith(("_get_", "_post_")) and name not in VERTEILER and name not in genannt:
            fehler.append(f"Handler.{name} ist in keiner Tabellenzeile")
    return fehler


def test_tabelle_und_methoden_passen_zusammen():
    assert len(app.ROUTEN) >= 70, "Gegenprobe: die Tabelle ist nicht leer"
    assert tabellen_fehler(app.ROUTEN, app.Handler) == []


def test_gegenprobe_tabellen_fehler_werden_gefunden():
    kaputt = dict(app.ROUTEN)
    kaputt[("GET", "/api/gibtsnicht")] = "_get_gibtsnicht"
    kaputt[("POST", "/api/x?y=1")] = "_post_remote"
    del kaputt[("GET", "/api/lyrics")]
    funde = tabellen_fehler(kaputt, app.Handler)
    assert "GET /api/gibtsnicht: Handler._get_gibtsnicht fehlt" in funde
    assert "POST /api/x?y=1: kein reiner Pfad" in funde
    assert "Handler._get_lyrics ist in keiner Tabellenzeile" in funde


# Pfad und Methode gehören zusammen (Nacharbeit Y7, 25.09.2026). Die Rechte
# hängen am Pfad (LAN_ERLAUBT, NUR_PC), was läuft, hängt am Methodennamen in
# ROUTEN. Vertauschte man zwei Tabellenzeilen, liefe eine Methode, die nur am
# PC erlaubt ist, unter einem Pfad, den das WLAN darf (Gegenprobe der Abnahme:
# /api/live mit _get_geraete, volle Suite grün). Darum folgt der Name aus dem
# Pfad: `_<verb>_` + Pfad ohne führendes `/api/` bzw. `/`, dabei `/` und `.`
# zu `_`. Ausnahmen stehen nur hier, kurz und ausdrücklich.
NAMENS_AUSNAHMEN = {
    ("GET", "/"): "_get_oberflaeche",
    ("GET", "/index.html"): "_get_oberflaeche",
    ("GET", "/m"): "_get_handy",
}


def methodenname_aus_pfad(verb, pfad):
    if (verb, pfad) in NAMENS_AUSNAHMEN:
        return NAMENS_AUSNAHMEN[(verb, pfad)]
    rest = pfad[len("/api/"):] if pfad.startswith("/api/") else pfad[1:]
    return f"_{verb.lower()}_" + rest.replace("/", "_").replace(".", "_")


def zuordnungs_fehler(routen, lan_erlaubt, nur_pc):
    """Was an der Zuordnung Pfad → Methode nicht stimmt (leer = alles gut)."""
    fehler = [f"{verb} {pfad}: {name}, aus dem Pfad folgt {methodenname_aus_pfad(verb, pfad)}"
              for (verb, pfad), name in sorted(routen.items())
              if name != methodenname_aus_pfad(verb, pfad)]
    fehler += [f"Ausnahme {verb} {pfad} hat keine Route" for verb, pfad in NAMENS_AUSNAHMEN
               if (verb, pfad) not in routen]
    # Mehrere Pfade zu einer Methode (/ und /index.html): nur als Ausnahme und
    # nur mit denselben Rechten, sonst entschiede der Pfad über dieselbe Methode.
    pfade_je_methode = {}
    for schluessel, name in routen.items():
        pfade_je_methode.setdefault(name, []).append(schluessel)
    for name, schluessel in sorted(pfade_je_methode.items()):
        if len(schluessel) < 2:
            continue
        if any(s not in NAMENS_AUSNAHMEN for s in schluessel):
            fehler.append(f"{name} unter mehreren Pfaden {sorted(schluessel)}")
        rechte = {"WLAN" if s in lan_erlaubt else "PC" if s in nur_pc else "?" for s in schluessel}
        if len(rechte) > 1:
            fehler.append(f"{name} unter Pfaden mit verschiedenen Rechten {sorted(schluessel)}")
    return fehler


def test_der_methodenname_folgt_aus_dem_pfad():
    assert zuordnungs_fehler(app.ROUTEN, app.LAN_ERLAUBT, app.NUR_PC) == []


def _vertauscht(routen, a, b):
    neu = dict(routen)
    neu[a], neu[b] = routen[b], routen[a]
    return neu


def test_gegenprobe_vertauschte_zeilen_werden_gefunden():
    """Die drei Vertauschungen der Abnahme (M1, M1b, M1c) machen den Wächter
    rot, ebenso ein zweiter Pfad zu einer Methode, eine Ausnahme ohne Route
    und zwei Pfade einer Methode mit verschiedenen Rechten."""
    for a, b in ((("GET", "/api/live"), ("GET", "/api/geraete")),
                 (("GET", "/api/addon_update"), ("GET", "/api/schaetzfaktoren")),
                 (("GET", "/api/lyrics"), ("GET", "/api/transkript_suche"))):
        funde = zuordnungs_fehler(_vertauscht(app.ROUTEN, a, b), app.LAN_ERLAUBT, app.NUR_PC)
        assert len(funde) == 2 and all(f.startswith((f"{a[0]} {a[1]}:", f"{b[0]} {b[1]}:"))
                                       for f in funde), funde
    doppelt = dict(app.ROUTEN)
    doppelt[("GET", "/api/filme_detail")] = "_get_filme_detail"      # folgt dem Namen, aber zweiter Pfad
    lan = dict(app.LAN_ERLAUBT)
    lan[("GET", "/api/filme_detail")] = ("Probe", None)             # gleiche Rechte: nur der zweite Pfad fällt auf
    assert zuordnungs_fehler(doppelt, lan, app.NUR_PC) == [
        "_get_filme_detail unter mehreren Pfaden "
        "[('GET', '/api/filme/detail'), ('GET', '/api/filme_detail')]"]
    ohne = dict(app.ROUTEN)
    del ohne[("GET", "/m")]
    assert zuordnungs_fehler(ohne, app.LAN_ERLAUBT, app.NUR_PC) == ["Ausnahme GET /m hat keine Route"]
    rechte = dict(app.LAN_ERLAUBT)
    del rechte[("GET", "/index.html")]
    assert zuordnungs_fehler(app.ROUTEN, rechte, app.NUR_PC) == [
        "_get_oberflaeche unter Pfaden mit verschiedenen Rechten "
        "[('GET', '/'), ('GET', '/index.html')]"]


def test_die_verteiler_kennen_keinen_pfad():
    """Nach nichts sonst als der Tabelle: in den beiden Verteilern steht kein
    Pfad (vorher hing an jedem Vergleich der Kette eine Route)."""
    for name in VERTEILER:
        baum = ast.parse(textwrap.dedent(inspect.getsource(getattr(app.Handler, name))))
        pfade = [k.value for k in ast.walk(baum) if isinstance(k, ast.Constant)
                 and isinstance(k.value, str) and k.value.startswith("/")]
        assert pfade == [], (name, pfade)


@pytest.fixture
def zeugen(monkeypatch):
    """Ersetzt JEDE Route-Methode durch einen Zeugen, der seinen Namen notiert
    und 200 mit dem Namen antwortet."""
    erreicht = []

    def zeuge(name, verb):
        if verb == "GET":
            def methode(self):
                erreicht.append(name)
                app._antwort(self, 200, {"zeuge": name})
        else:
            def methode(self, daten):
                erreicht.append(name)
                app._antwort(self, 200, {"zeuge": name, "daten": daten})
        return methode
    for (verb, _pfad), name in app.ROUTEN.items():
        monkeypatch.setattr(app.Handler, name, zeuge(name, verb))
    return erreicht


def _senden(verb, pfad, rumpf=None):
    if verb == "POST":
        return _anfrage(pfad, methode="POST", kopf=PC, rumpf=rumpf or {"x": 1})
    return _anfrage(pfad, methode=verb, kopf=PC)


@pytest.mark.parametrize("verb,pfad", sorted(app.ROUTEN))
def test_jede_tabellenzeile_erreicht_ihre_methode(zeugen, verb, pfad):
    st, _, koerper = _senden(verb, pfad)
    name = app.ROUTEN[(verb, pfad)]
    assert st == 200 and zeugen == [name], (verb, pfad, st, zeugen, koerper[:120])
    antwort = json.loads(koerper)
    assert antwort["zeuge"] == name
    if verb == "POST":
        assert antwort["daten"] == {"x": 1}, "der Körper kommt bei der Methode an"


def test_head_folgt_get(zeugen):
    st, _, _ = _anfrage("/api/status", methode="HEAD", kopf=PC)
    assert st == 200 and zeugen == ["_get_status"]


# Reihenfolge-Fallen der alten Kette: In einer if/elif-Kette mit Vergleich per
# Anfang hätte /api/addon_hab die Liste (/api/addon_hab_liste) geschluckt, je
# nachdem, was zuerst stand; /media verglich früher mit dem Anfang. Seit
# Gruppe 6 verglich die Kette genau; die Tabelle kann gar nicht anders.
@pytest.mark.parametrize("pfad,erwartet", [
    ("/api/addon_hab_liste?id=PL1", "_get_addon_hab_liste"),
    ("/api/addon_hab?id=abcdefghijk", "_get_addon_hab"),
    ("/api/addon_hab_liste", "_get_addon_hab_liste"),
    ("/media?id=k%7Cmp3", "_get_media"),
    ("/api/status?x=1", "_get_status"),
    ("/?embed=1", "_get_oberflaeche"),
    ("/index.html", "_get_oberflaeche"),
    ("/api/filme/detail?id=1", "_get_filme_detail"),
])
def test_reihenfolge_fallen_der_alten_kette(zeugen, pfad, erwartet):
    st, _, _ = _anfrage(pfad, kopf=PC)
    assert st == 200 and zeugen == [erwartet], (pfad, zeugen)


@pytest.mark.parametrize("verb,pfad", [
    ("GET", "/media/abc"), ("GET", "/mediaX"), ("GET", "/media.mp3"), ("GET", "/api/addon_hab_listeX"),
    ("GET", "/api/addon_ha"), ("GET", "/api/status/"), ("GET", "/API/STATUS"), ("GET", "/handy"),
    ("GET", "/api/gibtsnicht"), ("POST", "/api/gibtsnicht"), ("POST", "/api/remote/"),
    ("GET", "/api/remote"), ("POST", "/api/status"),
])
def test_alles_ausser_der_tabelle_ist_unbekannt(zeugen, verb, pfad):
    """Vom PC (dort gilt kein WLAN-Tor): nur genaue Tabellenzeilen kommen an,
    auch nicht die falsche Methode für einen bekannten Pfad."""
    st, _, koerper = _senden(verb, pfad)
    assert st == 404 and json.loads(koerper) == {"fehler": "unbekannt"}, (verb, pfad, st, koerper[:120])
    assert zeugen == []


def test_post_ohne_eigene_meldung_antwortet_ok(monkeypatch):
    """Die Kette antwortete am Ende {"ok": true} für Zweige ohne eigene Meldung;
    jetzt tut es `_ok()` in der Methode (hier /api/played ohne Eintrag)."""
    st, _, koerper = _anfrage("/api/played", methode="POST", kopf=PC, rumpf={"id": "gibtsnicht|mp3"})
    assert st == 200 and json.loads(koerper) == {"ok": True}


def test_post_ausnahme_wird_500(monkeypatch):
    """Wie in der Kette: eine Ausnahme in einer POST-Route wird 500 mit Text."""
    def kaputt(daten):
        raise RuntimeError("Probe")
    monkeypatch.setattr(app, "remote_befehl", kaputt)
    st, _, koerper = _anfrage("/api/remote", methode="POST", kopf=PC, rumpf={"cmd": "next"})
    assert st == 500 and "Probe" in json.loads(koerper)["fehler"]


def test_zeuge_sieht_den_pfad_ohne_anfrageteil(monkeypatch):
    """Die Methode liest den Anfrageteil selbst (self.path bleibt unverändert)."""
    gesehen = []
    monkeypatch.setattr(app.Handler, "_get_lyrics", lambda self: gesehen.append(self.path)
                        or app._antwort(self, 200, {}))
    _anfrage("/api/lyrics?id=k", kopf=PC)
    assert gesehen == ["/api/lyrics?id=k"] and urlparse(gesehen[0]).path == "/api/lyrics"
