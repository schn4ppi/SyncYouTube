# -*- coding: utf-8 -*-
"""Kleine Fehler der Oberfläche (Gesamtprüfung Gruppe 6, 25.09.2026), jeweils
als echtes Seiten-JavaScript per deno ausgeführt.

F11: Im VLC-Modus stand die Zeitleiste der Kopfleiste gesperrt auf 0:00; nur
die Leiste im Player konnte VLC spulen. Beide nutzen jetzt dieselben Helfer.
"""
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

from test_medientasten_verhalten import _js_funktion, _lauf, _pc  # noqa: E402


# ------------------------------------------------------------------ F11

def _spul_teile(q):
    namen = ["zeit", "cmdSeekDrag", "cmdSeekEnd", "cmdSeekTick",
             "plbSeekDrag", "plbSeekEnd", "plbTick"]
    for extra in ("spulStand", "spulenAuf"):                # Helfer nach der Reparatur
        if f"function {extra}(" in q:
            namen.append(extra)
    return [
        "let plGeraet='browser', vlcPosLetzte=0, vlcDauerLetzte=0, _posMerkTs=Date.now();",
        "let cmdSeekAktiv=false, plbSeekAktiv=false; const _befehle=[];",
        "function vlcAktiv(){return plGeraet==='vlc';}",
        "async function vlcBefehl(c,a){_befehle.push([c,a]); return {};}",
        "function posMerken(){} function posMerkerMalen(){}",
        "function feld(id){_els[id]={id, value:0, disabled:true, textContent:''}; return _els[id];}",
        "['cmd-seek','cmd-t0','cmd-t1','plb-seek','plb-t0','plb-t1'].forEach(feld);",
        "function stand(p){return {wert:_els[p+'-seek'].value, gesperrt:_els[p+'-seek'].disabled,"
        " t0:_els[p+'-t0'].textContent, t1:_els[p+'-t1'].textContent};}",
        *[_js_funktion(q, n) for n in namen],
    ]


def test_kopfleiste_spult_auch_am_geraet_vlc(tmp_path):
    (e1, e2) = _lauf(tmp_path, *_spul_teile(_pc()),
                     "plGeraet='vlc'; vlcPosLetzte=50; vlcDauerLetzte=200;",
                     "cmdSeekTick(); plbTick(); aus({kopf:stand('cmd'), leiste:stand('plb')});",
                     "cmdSeekDrag(500); const t0=_els['cmd-t0'].textContent; cmdSeekEnd(500);"
                     " aus({t0, befehle:_befehle.slice(), pos:vlcPosLetzte});")
    assert e1["kopf"] == {"wert": 250, "gesperrt": False, "t0": "0:50", "t1": "3:20"}, e1
    assert e1["kopf"]["wert"] == e1["leiste"]["wert"] and e1["kopf"]["t1"] == e1["leiste"]["t1"]
    assert e2["t0"] == "1:40"
    assert e2["befehle"] == [["seek", {"wert": 100}]] and e2["pos"] == 100


def test_player_leiste_spult_am_geraet_vlc_wie_bisher(tmp_path):
    (e,) = _lauf(tmp_path, *_spul_teile(_pc()),
                 "plGeraet='vlc'; vlcPosLetzte=50; vlcDauerLetzte=200;",
                 "plbSeekDrag(250); const t0=_els['plb-t0'].textContent; plbSeekEnd(250);"
                 " aus({t0, befehle:_befehle.slice(), aktiv:plbSeekAktiv});")
    assert e == {"t0": "0:50", "befehle": [["seek", {"wert": 50}]], "aktiv": False}


def test_kopfleiste_im_browser_unveraendert(tmp_path):
    (e1, e2, e3) = _lauf(tmp_path, *_spul_teile(_pc()),
                         "const el=fakeMedia({id:'pl-el', duration:100, currentTime:25}); _els['pl-el']=el;",
                         "cmdSeekTick(); aus(stand('cmd'));",
                         "cmdSeekEnd(500); plbSeekEnd(800); aus({t:el.currentTime, befehle:_befehle.slice()});",
                         "delete _els['pl-el']; cmdSeekTick(); aus(stand('cmd'));")
    assert e1 == {"wert": 250, "gesperrt": False, "t0": "0:25", "t1": "1:40"}
    assert e2 == {"t": 80, "befehle": []}
    assert e3 == {"wert": 0, "gesperrt": True, "t0": "0:00", "t1": "0:00"}


def test_kopfleiste_vlc_ohne_dauer_bleibt_gesperrt(tmp_path):
    (e,) = _lauf(tmp_path, *_spul_teile(_pc()),
                 "plGeraet='vlc'; vlcDauerLetzte=0;",
                 "cmdSeekTick(); cmdSeekEnd(300); aus({kopf:stand('cmd'), befehle:_befehle.slice()});")
    assert e["kopf"]["gesperrt"] is True and e["befehle"] == []

