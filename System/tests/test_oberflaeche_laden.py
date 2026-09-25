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
        "function fernModusSetzen(){}",   # Gerät im WLAN? eigener Test: test_zugang_seiten_js.py
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


# ------------------------------------------------ F10: Neuladen erst bei Pause
# JB-Entscheid 7a Punkt 5 (25.09.2026): Ändert sich der Stand der Oberfläche,
# während Musik (#pl-el) oder VLC spielt, lädt die Seite nicht mitten im Titel
# neu. Sie merkt es vor und holt es bei der nächsten Pause oder am Titelende
# nach; am Titelende ersetzt das Neuladen das Weiterschalten.

def _neuladen_teile(q):
    anfang = q.index("let uiStand=null")
    return [
        "const _ss={}; Object.defineProperty(globalThis, 'sessionStorage', {configurable:true,"
        " value:{getItem:k=>_ss[k]??null, setItem(k,v){_ss[k]=String(v);}}});",
        "globalThis.location={reload(){_log.push('reload');}};",
        "let tvpOffen=false, tvInfoOffen=false, tvDialogOffen=false, xfNext=null;",
        "document.activeElement=null;",
        "function nachEnde(){return {art:'titel', idx:1};}",
        "function playerAdvance(){_log.push('weiter');}",
        # vlcTick braucht diese Nachbarn; sie tun hier nichts
        "let subMode='aus', subCues=null, karRAF=0, _posMerk={}, _posMerkTs=0, vlcStatus=null;",
        "function huelleVideoRect(){} function vlcPosGeschaetzt(){return 0;} function medienVlcSpiegel(){}",
        "function subTick(){} function vlcKarLauf(){} function ico(){return '';} function vlcNeustart(){}",
        "function vlcAktiv(){return plGeraet==='vlc';} function aktKey(){return 'song|mp3';}",
        "async function vlcBefehl(){return vlcStatus;}",
        "let plGeraet='browser';",
        _js_zeile(q, "let vlcTimer=null"),
        _js_zeile(q, "let vlcPosLetzte=0"),
        q[anfang:q.index("/* Addon-Nachschub", anfang)],
        _js_funktion(q, "plTitelEnde"),
        _js_funktion(q, "vlcTick"),
    ]


def test_neuladen_wartet_auf_pause_bei_musik(tmp_path):
    (e1, e2) = _lauf(tmp_path, *_neuladen_teile(_pc()),
                     "const el=fakeMedia({id:'pl-el', paused:false}); _els['pl-el']=el;",
                     "uiStandPruefen('a'); uiStandPruefen('b'); uiStandPruefen('b'); aus({log:_log.slice()});",
                     "el.paused=true; uiStandPruefen('b'); aus({log:_log.slice()});")
    assert "reload" not in e1["log"], "mitten im Titel darf die Seite nicht neu laden"
    assert e2["log"].count("reload") == 1, "in der Pause holt der nächste Takt das Neuladen nach"


def test_neuladen_am_titelende_statt_weiter(tmp_path):
    (e1, e2) = _lauf(tmp_path, *_neuladen_teile(_pc()),
                     "const el=fakeMedia({id:'pl-el', paused:false}); _els['pl-el']=el;",
                     "uiStandPruefen('a'); uiStandPruefen('b'); aus({log:_log.slice()});",
                     "el.paused=true; el.ended=true; plTitelEnde({target:el}); aus({log:_log.slice()});")
    assert e1["log"] == []
    assert e2["log"] == ["reload"], "am Titelende lädt die Seite neu, statt weiterzuschalten"


def test_ohne_neuen_stand_schaltet_das_titelende_weiter(tmp_path):
    (e,) = _lauf(tmp_path, *_neuladen_teile(_pc()),
                 "const el=fakeMedia({id:'pl-el', paused:false}); _els['pl-el']=el;",
                 "uiStandPruefen('a'); uiStandPruefen('a');",
                 "el.paused=true; el.ended=true; plTitelEnde({target:el}); aus({log:_log.slice()});")
    assert e["log"] == ["weiter"]


def test_neuladen_innerhalb_einer_minute_schaltet_weiter(tmp_path):
    (e,) = _lauf(tmp_path, *_neuladen_teile(_pc()),
                 "_ss['ui_reload_ts']=String(Date.now());",
                 "const el=fakeMedia({id:'pl-el', paused:false}); _els['pl-el']=el;",
                 "uiStandPruefen('a'); uiStandPruefen('b');",
                 "el.paused=true; el.ended=true; plTitelEnde({target:el}); aus({log:_log.slice()});")
    assert e["log"] == ["weiter"], "die Minuten-Bremse bleibt; dann geht die Musik normal weiter"


def test_neuladen_wartet_auf_vlc(tmp_path):
    (e1, e2, e3) = _lauf(
        tmp_path, *_neuladen_teile(_pc()),
        "plGeraet='vlc'; vlcSpielt=true;",
        "uiStandPruefen('a'); uiStandPruefen('b'); aus({log:_log.slice()});",
        "vlcStatus={verfuegbar:true, zustand:'spielt', key:'song|mp3', pos:10, dauer:200};"
        " await vlcTick(); uiStandPruefen('b'); aus({log:_log.slice()});",
        "vlcStatus={verfuegbar:true, zustand:'ende', key:'song|mp3', pos:200, dauer:200};"
        " await vlcTick(); aus({log:_log.slice()});")
    assert e1["log"] == [] and e2["log"] == [], "solange VLC spielt, lädt die Seite nicht neu"
    assert e3["log"] == ["reload"], "am VLC-Titelende lädt die Seite neu, statt weiterzuschalten"


def test_neuladen_bei_vlc_pause(tmp_path):
    (e,) = _lauf(tmp_path, *_neuladen_teile(_pc()),
                 "plGeraet='vlc'; vlcSpielt=true; uiStandPruefen('a'); uiStandPruefen('b');",
                 "vlcStatus={verfuegbar:true, zustand:'pausiert', key:'song|mp3', pos:10, dauer:200};"
                 " await vlcTick(); uiStandPruefen('b'); aus({log:_log.slice()});")
    assert e["log"] == ["reload"]
