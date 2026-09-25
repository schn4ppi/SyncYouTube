# -*- coding: utf-8 -*-
"""Jede POST-Route antwortet genau einmal (Nacharbeit Y7, 25.09.2026).

In der alten if/elif-Kette antwortete das Ende der Kette {"ok": true} für
jeden Zweig ohne eigene Meldung. Seit der Routentabelle tut das `self._ok()`
in der Methode, also neuer Code in zehn Methoden; für drei davon gab es
keinen Test (biblio_enrich, untertitel_laden, autotag). Fehlt `_ok()`,
schickt der Server gar keine Antwort, und der fetch der Oberfläche bricht ab.

Geprüft wird hier jede POST-Zeile von ROUTEN, gefunden in der Tabelle, nicht
in einer Handliste: die ECHTE Methode läuft durch den echten Handler (ohne
Server, ohne Socket), gezählt wird `send_response`. Alles, was die Methode
aufruft und etwas tun könnte, ersetzt eine Attrappe, gefunden im Syntaxbaum
der Methode: Funktionen der App, Methoden an Modulen und Objekten der App
(Faden-Start, Warteschlange speichern, Film-Server, VLC …) und die Helfer
`self._…`. Die Helfer selbst antworten nie (eigener Test unten), sonst
verdeckte ihre Attrappe eine zweite Antwort. Daten-Wache und Netzsperre der
conftest bleiben an: was eine Attrappe vergäße, scheiterte dort laut.

Jede Route läuft mit drei Attrappen-Ergebnissen (leer, voll, null), damit
beide Seiten einer Abfrage wie `if neu_id:` drankommen, und mit jedem Körper,
den die Methode per `daten.get("art") == "…"` unterscheidet. Jeder Lauf muss
genau eine Antwort geben, und mindestens einer davon ohne 500.

Bekannt doppelt ist POST /api/umbenennen (Altlast der alten Kette,
verhaltensgleich übernommen). Er steht als xfail(strict=True) drin: die
Reparatur schaltet ihn sichtbar um, eine weitere Änderung dort fällt auf.
"""
import ast
import inspect
import os
import sys
import textwrap
import types

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
for _pfad in (MODUL_DIR, TEST_DIR):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import _anfrage, rechner  # noqa: E402,F401  (rechner: autouse)

PC = {"Host": "127.0.0.1:8776"}
POST_ROUTEN = sorted(pfad for verb, pfad in app.ROUTEN if verb == "POST")
BEKANNT_DOPPELT = {
    "/api/umbenennen": "Altlast der alten Kette: nach der Antwort von migration_anwenden "
                       "bzw. migration_rueckgaengig folgt ein zweites {ok: true}",
}
# Aufrufe, die bleiben: `_antwort` ist die Antwort selbst, `_ok` ruft ihn.
KEIN_ERSATZ = {"_antwort", "_ok"}
ANTWORT_AUFRUFE = {"_antwort", "_ok", "send_response", "send_error", "_stream_datei"}


class _Leer(dict):
    """Attrappen-Ergebnis „leer“: falsch, iterierbar ohne Inhalt, als JSON {};
    jede Methode daran (etwa `Thread(…).start()`) liefert es selbst."""
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: self


class _Null(int):
    """Attrappen-Ergebnis „null“: falsch und kein dict (nimmt den anderen Zweig
    von `isinstance(x, dict)`), als JSON 0."""
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: self


ERGEBNISSE = {"leer": _Leer, "voll": lambda: _Leer(attrappe=True), "null": _Null}


class _Stellvertreter:
    """Steht in der App für ein Modul oder Objekt (threading, filme, Q …): die
    genannten Attribute sind Attrappen, alles andere reicht er durch."""
    def __init__(self, echt, ersatz):
        self._echt, self._ersatz = echt, ersatz

    def __getattr__(self, name):
        return self._ersatz[name] if name in self._ersatz else getattr(self._echt, name)


def _baum(funktion):
    return ast.parse(textwrap.dedent(inspect.getsource(funktion)))


def _aufrufe(baum):
    """(Basis, Name) jedes Aufrufs: `f()` → (None, "f"), `x.f()` → ("x", "f")."""
    for k in ast.walk(baum):
        if isinstance(k, ast.Call):
            if isinstance(k.func, ast.Name):
                yield None, k.func.id
            elif isinstance(k.func, ast.Attribute) and isinstance(k.func.value, ast.Name):
                yield k.func.value.id, k.func.attr


def attrappen_setzen(mp, methode, ergebnis):
    """Ersetzt, was die Route-Methode aufruft und etwas tun könnte; liefert,
    was ersetzt wurde. Bleiben: eingebaute Funktionen, `_antwort`/`_ok` und
    Lese-Aufrufe an dict/list der App (CFG.get, _geladen.get)."""
    def attrappe(*a, **k):
        return ergebnis()

    def helfer(self, *a, **k):
        return ergebnis()
    ersetzt, stellvertreter = [], {}
    for basis, name in _aufrufe(_baum(getattr(app.Handler, methode))):
        if name in KEIN_ERSATZ:
            continue
        if basis is None:
            if callable(vars(app).get(name)):
                mp.setattr(app, name, attrappe)
                ersetzt.append(name)
        elif basis == "self":
            mp.setattr(app.Handler, name, helfer)
            ersetzt.append("self." + name)
        elif basis in vars(app):
            objekt = vars(app)[basis]
            if not isinstance(objekt, types.ModuleType) and type(objekt).__module__ == "builtins":
                continue
            stellvertreter.setdefault(basis, {})[name] = attrappe
            ersetzt.append(f"{basis}.{name}")
    for basis, ersatz in stellvertreter.items():
        mp.setattr(app, basis, _Stellvertreter(vars(app)[basis], ersatz))
    # Im Betrieb setzt socketserver den Server; /api/beenden liest server.shutdown.
    mp.setattr(app.Handler, "server", types.SimpleNamespace(shutdown=attrappe), raising=False)
    return sorted(set(ersetzt))


def koerper_der_methode(methode):
    """{"x": 1} und je `daten.get("k") == "w"` in der Methode ein Körper {"k": "w"}."""
    koerper = [{"x": 1}]
    for k in ast.walk(_baum(getattr(app.Handler, methode))):
        if not (isinstance(k, ast.Compare) and len(k.ops) == 1 and isinstance(k.ops[0], ast.Eq)):
            continue
        frage, wert = k.left, k.comparators[0]
        if (isinstance(frage, ast.Call) and isinstance(frage.func, ast.Attribute)
                and frage.func.attr == "get" and isinstance(frage.func.value, ast.Name)
                and frage.func.value.id == "daten" and frage.args
                and isinstance(frage.args[0], ast.Constant) and isinstance(wert, ast.Constant)):
            koerper.append({frage.args[0].value: wert.value})
    return koerper


def antwort_befunde(monkeypatch, pfad):
    """Läufe einer POST-Route, die nicht genau einmal antworten, und ein Befund,
    falls jeder Lauf in 500 endet (dann lief der eigentliche Weg nie)."""
    methode = app.ROUTEN[("POST", pfad)]
    befunde, codes_alle = [], []
    for koerper in koerper_der_methode(methode):
        for art, ergebnis in ERGEBNISSE.items():
            with monkeypatch.context() as mp:
                attrappen_setzen(mp, methode, ergebnis)
                codes = []
                echt = app.Handler.send_response

                def zaehlend(self, code, message=None, _codes=codes, _echt=echt):
                    _codes.append(code)
                    return _echt(self, code, message)
                mp.setattr(app.Handler, "send_response", zaehlend)
                _anfrage(pfad, methode="POST", kopf=PC, rumpf=koerper)
            codes_alle += codes
            if len(codes) != 1:
                befunde.append(f"{pfad} {koerper} ({art}): {len(codes)} Antworten {codes}")
    if codes_alle and all(c == 500 for c in codes_alle):
        befunde.append(f"{pfad}: jeder Lauf endet in 500 {codes_alle}")
    return befunde


@pytest.mark.parametrize("pfad", [
    pytest.param(p, marks=pytest.mark.xfail(strict=True, reason=BEKANNT_DOPPELT[p]))
    if p in BEKANNT_DOPPELT else p for p in POST_ROUTEN])
def test_jede_post_route_antwortet_genau_einmal(monkeypatch, pfad):
    assert antwort_befunde(monkeypatch, pfad) == []


def test_ableitung_findet_die_post_routen_und_ihre_attrappen():
    """Gegenprobe für die Ableitung: die Tabelle liefert die POST-Routen, der
    Syntaxbaum die Attrappen (Faden-Start, Warteschlange, Film-Server, Helfer)
    und die Körper der Abfragen."""
    assert len(POST_ROUTEN) >= 30 and set(BEKANNT_DOPPELT) <= set(POST_ROUTEN)
    with pytest.MonkeyPatch.context() as mp:
        assert attrappen_setzen(mp, "_post_beenden", _Leer) == ["Q.speichern", "threading.Thread"]
        assert attrappen_setzen(mp, "_post_biblio_enrich", _Leer) == ["threading.Thread"]
        assert attrappen_setzen(mp, "_post_add", _Leer) == ["self._add"]
        assert "filme.stream_url" in attrappen_setzen(mp, "_post_filme_play", _Leer)
        assert "_zeile_anhaengen" in attrappen_setzen(mp, "_post_js_fehler", _Leer)
    assert koerper_der_methode("_post_playlist") == [{"x": 1}, {"art": "sync"}]
    assert koerper_der_methode("_post_umbenennen") == [{"x": 1}, {"art": "undo"}]


@pytest.mark.parametrize("fassung,erwartet", [
    ("ohne", "0 Antworten"), ("doppelt", "2 Antworten"), ("kaputt", "jeder Lauf endet in 500")])
def test_gegenprobe_falsche_antwortzahl_wird_gefunden(monkeypatch, fassung, erwartet):
    """Eine Route ohne Antwort, mit zwei Antworten und eine, die immer
    scheitert, fallen auf."""
    def ohne(self, daten):
        pass

    def doppelt(self, daten):
        app._antwort(self, 200, {})
        self._ok()

    def kaputt(self, daten):
        raise RuntimeError("Probe")
    monkeypatch.setattr(app.Handler, "_post_biblio_enrich",
                        {"ohne": ohne, "doppelt": doppelt, "kaputt": kaputt}[fassung])
    befunde = antwort_befunde(monkeypatch, "/api/biblio_enrich")
    assert befunde and all(erwartet in b for b in befunde), befunde


def _helfer_mit_antwort():
    """Handler-Methoden, die eine POST-Route über `self._…` ruft (auch über
    weitere Helfer) und die selbst antworten."""
    routen = set(app.ROUTEN.values())
    offen = [name for (verb, _), name in app.ROUTEN.items() if verb == "POST"]
    gesehen, funde = set(offen), []
    while offen:
        name = offen.pop()
        for basis, helfer in _aufrufe(_baum(getattr(app.Handler, name))):
            if basis != "self" or helfer in KEIN_ERSATZ or helfer in gesehen or helfer in routen:
                continue
            gesehen.add(helfer)
            funktion = getattr(app.Handler, helfer, None)
            if not inspect.isfunction(funktion):     # in Python geschrieben, sonst kein Quelltext
                continue
            baum = _baum(funktion)
            if any(n in ANTWORT_AUFRUFE for _, n in _aufrufe(baum)):
                funde.append(f"{name} → self.{helfer}")
            offen.append(helfer)
    return sorted(funde), gesehen


def test_die_helfer_der_post_routen_antworten_nicht_selbst():
    """Die Attrappe eines Helfers (self._add, self._config …) verdeckte sonst
    eine zweite Antwort: `_post_add` ruft nach `self._add` noch `self._ok()`."""
    funde, gesehen = _helfer_mit_antwort()
    assert {"_add", "_action", "_config", "_biblio"} <= gesehen, "Gegenprobe: die Suche findet die Helfer"
    assert funde == []


def test_gegenprobe_helfer_mit_antwort_wird_gefunden(monkeypatch):
    def _add(self, daten):
        app._antwort(self, 400, {"fehler": "Probe"})
    monkeypatch.setattr(app.Handler, "_add", _add)
    funde, _ = _helfer_mit_antwort()
    assert funde == ["_post_add → self._add"]
