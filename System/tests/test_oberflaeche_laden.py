# -*- coding: utf-8 -*-
"""Statusabruf der Oberfläche (Gesamtprüfung F9, unsichtbarer Teil, 25.09.2026).

`laden()` holt jede Sekunde /api/status. Bekam es eine Fehlerantwort (etwa
403 auf einem gekoppelten Gerät, dessen API-Aufrufe keinen Token tragen),
übernahm es sie als Stand: `daten` war danach `{fehler: …}`, und
`configFuellen` setzte `cfgInit` VOR dem Zugriff auf `daten.config` — der
Zugriff warf, und das Einstellungs-Formular wurde nie wieder gefüllt, auch
nicht nach einer späteren guten Antwort.

Beide Funktionen laufen hier als echtes Seiten-JavaScript (deno).
"""
import json
import os
import re
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

from test_medientasten_verhalten import _js_funktion, _js_zeile, _lauf, _pc  # noqa: E402

GUT = {"config": {"ziel_ordner": "D:/Ziel", "unterordner": True, "metadaten": True,
                  "cookies_browser": "firefox", "parallel": 2, "standard_qualitaet": "beste",
                  "geo_proxies": [], "untertitel_sprachen": ["de"]},
       "ziel": "D:/Ziel", "items": [], "ui_stand": 1}


def _umgebung():
    q = _pc()
    anfang = q.index("function configFuellen")
    ids = sorted(set(re.findall(r"getElementById\('([^']+)'\)",
                                q[anfang:q.index("async function laden", anfang)])))
    assert "cfg_ziel" in ids and len(ids) > 10, ids
    felder = "".join(f"_els[{json.dumps(i)}]={{value:'',checked:false}};" for i in ids)
    return [
        "let daten=null; const _ap=[];",
        "function apiStatus(ok){_ap.push(ok);} function malen(){} function remoteAusfuehren(){}",
        "function nachschubMelden(){} function subStilVomServer(){} function uiStandPruefen(){}",
        felder,
        "let _antwort=null; globalThis.fetch=async()=>_antwort;",
        "function antwort(ok,status,d){_antwort={ok,status,json:async()=>d};}",
        _js_zeile(q, "let cfgInit"),
        _js_funktion(q, "configFuellen"),
        _js_funktion(q, "laden"),
    ], ids


def test_fehlerantwort_wird_nicht_zum_stand(tmp_path):
    teile, _ = _umgebung()
    (e1, e2) = _lauf(tmp_path, *teile,
                     "antwort(false,403,{fehler:'Kein Zugriff'}); await laden();",
                     "aus({daten, cfgInit, ap:_ap.slice()});",
                     f"antwort(true,200,{json.dumps(GUT)}); await laden();",
                     "aus({ziel:daten&&daten.ziel, cfgInit, feld:_els['cfg_ziel'].value, ap:_ap.slice()});")
    assert e1["daten"] is None, "eine 403-Antwort darf den Stand nicht ersetzen"
    assert e1["cfgInit"] is False and e1["ap"] == [False]
    assert e2["ziel"] == "D:/Ziel" and e2["cfgInit"] is True
    assert e2["feld"] == "D:/Ziel", "nach der ersten guten Antwort wird das Formular gefüllt"
    assert e2["ap"][-1] is True


def test_cfginit_erst_nach_erfolg(tmp_path):
    teile, _ = _umgebung()
    (e1, e2) = _lauf(tmp_path, *teile,
                     f"daten={json.dumps(GUT)}; const _weg=_els['cfg_autoupdate']; delete _els['cfg_autoupdate'];",
                     "try{configFuellen();}catch(e){} aus({cfgInit});",
                     "_els['cfg_autoupdate']=_weg; configFuellen(); aus({cfgInit, feld:_els['cfg_ziel'].value});")
    assert e1["cfgInit"] is False, "ein Fehler mitten im Füllen darf das Formular nicht sperren"
    assert e2["cfgInit"] is True and e2["feld"] == "D:/Ziel"
