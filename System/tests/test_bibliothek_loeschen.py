# -*- coding: utf-8 -*-
"""Titel aus der Bibliothek löschen: Mehrfachauswahl, Entf-Taste, keine Tonlücke.

Nutzer-Rückmeldung (über JB, 19.10.2026), zwei Befunde:

1. „Trotz Mehrfachauswahl konnte ich nicht mehrere Songs auf einmal löschen …
   ich musste jeden über Rechtsklick deleten. Entf. ging auch nicht.“ — Der
   Rechtsklick-Punkt „In den Papierkorb“ nahm immer nur den angeklickten Titel
   (`delEinzeln(id)`), und die Entf-Taste wirkte in der Bibliothek nur in der
   Playlist-Ansicht (dort nimmt sie Titel aus der Liste). JB: „Das ist mir auch
   mal aufgefallen.“
2. „Wenn ich einen random Song lösche, wird der aktuelle Song kurz pausiert.“ —
   Gemessen am 21.10.2026 in Firefox 158 (eigenes Wegwerf-Profil gegen die
   Testwelt, WebDriver BiDi): Solange der native `confirm()`-Dialog offen ist,
   steht die Uhr des AudioContext still, das `<audio>`-Element läuft weiter.
   Die Musik geht über den Web-Audio-Graphen (`vizVerbinde`: Equalizer,
   Visualizer, Überblendung), also ist sie so lange stumm — und das Stück
   springt danach um die Dialog-Zeit weiter. Bilanz des Laufs: Wanduhr +3,82 s,
   AudioContext +1,56 s, Dialog 2,22 s offen. Ohne Dialog: +9,97 s gegen
   +9,98 s. Chromium zeigt die Lücke nicht (Messung im Browser-Pane).

Darum fragt jedes Löschen von Titeln über den app-eigenen `frageModal` (er
blockiert nichts) und nie über confirm/alert/prompt. Ausgeführt wird das ECHTE
JavaScript der PC-Oberfläche mit deno (Hilfen aus test_medientasten_verhalten).

Nicht hier gemessen: die hörbare Wirkung selbst (live in Firefox gemessen, s. o.)
und der Server-Teil des Löschens (tests/test_loeschen_und_pfade.py).
"""
import os
import sys

import pytest

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

from test_medientasten_verhalten import _block_ende, _js_funktion, _lauf, _pc  # noqa: E402

UMGEBUNG = r"""
const _calls=[], _nativ=[], _modale=[]; let _ja=null, _modalOffen=false;
globalThis.confirm=t=>{_nativ.push('confirm: '+t); return true;};
globalThis.alert=t=>{_nativ.push('alert: '+t);};
globalThis.prompt=t=>{_nativ.push('prompt: '+t); return '';};
_els['view-lib']={offsetParent:{}};                     // _els: Attrappe aus test_medientasten_verhalten
// Wie die echte Seite: Legende, Einstellungen und Geo-Assistent stehen als
// VERSTECKTE .modal dauerhaft im Dokument (gemessen 21.10.); offen ist nur,
// was angezeigt wird.
const _versteckt=['hilfemodal','settingsmodal','geowiz'].map(id=>({id,_display:'none'}));
const _rueckfrage={id:'',_display:'flex'};
function _modale_im_dom(){return _modalOffen?[..._versteckt,_rueckfrage]:_versteckt;}
document.querySelector=s=>s==='.modal'?(_modale_im_dom()[0]||null):null;
document.querySelectorAll=s=>s==='.modal'?_modale_im_dom():[];
globalThis.getComputedStyle=el=>({display:el._display||'block'});
function frageModal(text,jaLabel,onJa){_modale.push(text); _ja=onJa;}
async function api(pfad,body){_calls.push([pfad,body]); return {ok:true};}
async function libLaden(){_calls.push(['libLaden']);}
async function plLaden(){_calls.push(['plLaden']);}
function libMalen(){} function toast(t){_calls.push(['toast',t]);} function plInfo(t){_calls.push(['info',t]);}
function kontextMenuBauen(ev,eintraege){_menue=eintraege;} let _menue=[];
function nurPc(e){e.nurPc=true; return e;} function menuGeradeZu(){return false;}
let NUR_FERN=false, libPlaylistView=null, libAuswahl=new Set(), _hkFang=null;
const plState=[{id:'p1',name:'Liste A',items:['a','b','c','d','e']}];
const libdaten=['a','b','c','d','e'].map(k=>({id:k,titel:'Song '+k.toUpperCase(),vorhanden:true,qualitaet:'audio'}));
function libFind(k){return libdaten.find(x=>x.id===k);}
function filmTasten(){return false;} function hkAktionFuer(){return '';} function hkCode(){return '';}
function medienTasteHatSitzung(){return false;}
const _ev={stopPropagation(){},currentTarget:{getBoundingClientRect(){return {left:5,right:5,top:5,bottom:5};}}};
function _taste(key,o){return Object.assign({key,code:key,ctrlKey:false,metaKey:false,altKey:false,shiftKey:false,
  _vd:false,preventDefault(){this._vd=true;},
  target:{matches:()=>false,isContentEditable:false,dataset:{},closest:()=>null}},o||{});}
async function _ruhe(){for(let i=0;i<20;i++)await new Promise(r=>setTimeout(r,0));}
function _papierkorb(){return _calls.filter(c=>c[0]==='/api/biblio'&&c[1].art==='loeschen').map(c=>c[1].id);}
function _stand(extra){return Object.assign({nativ:_nativ.slice(), modale:_modale.slice(), papierkorb:_papierkorb(),
  playlist:_calls.filter(c=>c[0]==='/api/playlist').map(c=>c[1]),
  neuGeladen:_calls.filter(c=>c[0]==='libLaden').length, auswahl:[...libAuswahl]},extra||{});}
"""

# Seitenfunktionen, die die Löschwege ausführen. Fehlt eine (Umbau), bleibt sie
# weg; wer sie braucht, bricht dann laut mit „… is not defined“.
FUNKTIONEN = ("libItemMenu", "libLoeschen", "delEinzeln", "biblio", "dubDelete",
              "plAuswahlEntfernen", "plApi")


def _taste_handler(q):
    """Der EINE globale keydown-Zuhörer der Seite (anonym, trägt die Hotkey-
    Tabelle HK_TUN), klammergenau ausgeschnitten und als `_tasteDrücken` benannt."""
    kopf = "document.addEventListener('keydown',e=>"
    i = q.index(kopf)
    while True:
        auf = i + len(kopf)
        ende = _block_ende(q, auf)
        if "HK_TUN" in q[auf:ende]:
            return "const _tasteDruecken=e=>" + q[auf:ende + 1] + ";"
        i = q.index(kopf, ende)


def _loeschen_lauf(tmp_path, *schritte):
    q = _pc()
    teile = [UMGEBUNG]
    for name in FUNKTIONEN:
        try:
            teile.append(_js_funktion(q, name))
        except AssertionError:
            pass
    teile.append(_taste_handler(q))
    return _lauf(tmp_path, *teile, *schritte)


def _menue_klick(id_):
    """Rechtsklick auf `id_`, dann „In den Papierkorb“, dann „Ja“ im Dialog."""
    return ("libItemMenu(_ev," + repr(id_) + ");"
            " const _e=_menue.find(e=>String(e[0]).includes('Papierkorb'));"
            " const _label=_e?_e[0]:'(kein Papierkorb-Punkt)'; if(_e)_e[1]();"
            " await _ruhe(); if(_ja)await _ja(); await _ruhe();")


def test_rechtsklick_loescht_die_ganze_auswahl(tmp_path):
    """Befund 1: Ist der angeklickte Titel Teil einer Mehrfachauswahl, reist die
    ganze Auswahl mit (Explorer-Muster, dieselbe Regel wie „Zu Playlist“ und
    „Wiedergabe…“). EINE Rückfrage, EIN Neuladen der Bibliothek am Ende."""
    (e,) = _loeschen_lauf(
        tmp_path, "libAuswahl=new Set(['a','b','c']);", _menue_klick("b"),
        "aus(_stand({label:_label}));")
    assert "(3)" in e["label"], f"der Menüpunkt nennt die Auswahl nicht: {e['label']!r}"
    assert e["papierkorb"] == ["a", "b", "c"], e
    assert e["nativ"] == [], f"nativer Dialog hält in Firefox die Musik an: {e['nativ']}"
    assert len(e["modale"]) == 1 and "3 Titel" in e["modale"][0], e["modale"]
    assert e["neuGeladen"] == 1, "die Bibliothek nur einmal am Ende neu laden"
    assert e["auswahl"] == [], "gelöschte Titel bleiben nicht markiert"


def test_rechtsklick_ausserhalb_der_auswahl_loescht_nur_diesen(tmp_path):
    """Explorer-Muster: Rechtsklick auf einen NICHT markierten Titel meint nur
    ihn; die bestehende Auswahl bleibt unangetastet."""
    (e,) = _loeschen_lauf(
        tmp_path, "libAuswahl=new Set(['a','b']);", _menue_klick("d"),
        "aus(_stand({label:_label}));")
    assert "(" not in e["label"], e["label"]
    assert e["papierkorb"] == ["d"], e
    assert e["nativ"] == [], f"nativer Dialog hält in Firefox die Musik an: {e['nativ']}"
    assert len(e["modale"]) == 1 and "Song D" in e["modale"][0], e["modale"]
    assert e["auswahl"] == ["a", "b"], e


def test_entf_legt_die_auswahl_in_den_papierkorb(tmp_path):
    """Befund 1: Entf in der Bibliothek (nicht Playlist-Ansicht) legt die
    markierten Titel nach Rückfrage in den Papierkorb."""
    (e,) = _loeschen_lauf(
        tmp_path, "libAuswahl=new Set(['a','c']);",
        "const t=_taste('Delete'); _tasteDruecken(t); await _ruhe();",
        "const vorJa=_papierkorb().length; if(_ja)await _ja(); await _ruhe();",
        "aus(_stand({vd:t._vd, vorJa}));")
    assert e["modale"] and "2 Titel" in e["modale"][0], f"Entf fragt nicht / tut nichts: {e}"
    assert e["vorJa"] == 0, "vor dem Ja darf nichts gelöscht sein"
    assert e["papierkorb"] == ["a", "c"] and e["vd"], e
    assert e["nativ"] == [], e["nativ"]


@pytest.mark.parametrize("fall,vorher,taste", [
    ("Nein im Dialog", "", "'Delete'"),
    ("Gerät im WLAN", "NUR_FERN=true;", "'Delete'"),
    ("Bibliothek nicht sichtbar", "_els['view-lib']={offsetParent:null};", "'Delete'"),
    ("Tippen im Eingabefeld", "", "'Delete',{target:{matches:()=>true,dataset:{},closest:()=>null}}"),
    ("Rückfrage schon offen", "_modalOffen=true;", "'Delete'"),
    ("leere Auswahl", "libAuswahl=new Set();", "'Delete'"),
])
def test_entf_loescht_nichts_ausserhalb_seines_falls(tmp_path, fall, vorher, taste):
    (e,) = _loeschen_lauf(
        tmp_path, "libAuswahl=new Set(['a','c']);", vorher,
        f"_tasteDruecken(_taste({taste})); await _ruhe();",
        "aus(_stand());")
    assert e["papierkorb"] == [], f"{fall}: es wurde gelöscht {e}"
    if fall == "Nein im Dialog":
        assert len(e["modale"]) == 1, e
    else:
        assert e["modale"] == [], f"{fall}: es kam eine Rückfrage {e}"


def test_entf_in_der_playlist_ansicht_nimmt_nur_aus_der_liste(tmp_path):
    """Bestehendes Verhalten (JB 07.08.) bleibt: in der Playlist-Ansicht nimmt
    Entf die markierten Titel aus der LISTE, die Dateien bleiben."""
    (e,) = _loeschen_lauf(
        tmp_path, "libPlaylistView='p1'; libAuswahl=new Set(['a','b']);",
        "_tasteDruecken(_taste('Delete')); await _ruhe(); if(_ja)await _ja(); await _ruhe();",
        "aus(_stand());")
    assert e["papierkorb"] == [], e
    assert e["playlist"] == [{"art": "remove", "id": "p1", "key": "a"},
                             {"art": "remove", "id": "p1", "key": "b"}], e


def test_kein_loeschweg_fragt_mit_nativem_dialog(tmp_path):
    """Befund 2: Auch die übrigen Wege, Titel zu löschen oder aus einer Liste zu
    nehmen, fragen app-eigen — Dubletten-Fenster und Entf ab 5 Titeln in der
    Playlist-Ansicht."""
    (dub, pl) = _loeschen_lauf(
        tmp_path,
        "dubDelete('e'); await _ruhe(); if(_ja)await _ja(); await _ruhe();",
        "aus(_stand());",
        "_nativ.length=0; _modale.length=0; _calls.length=0; _ja=null;",
        "libPlaylistView='p1'; libAuswahl=new Set(['a','b','c','d','e']);",
        "await plAuswahlEntfernen(); await _ruhe(); if(_ja)await _ja(); await _ruhe();",
        "aus(_stand());")
    assert dub["nativ"] == [] and len(dub["modale"]) == 1 and dub["papierkorb"] == ["e"], dub
    assert pl["nativ"] == [] and len(pl["modale"]) == 1 and len(pl["playlist"]) == 5, pl
    assert pl["papierkorb"] == [], pl


def test_rueckfrage_schliesst_mit_esc_ohne_zu_loeschen(tmp_path):
    """Wer per Entf löscht, hat die Hände an der Tastatur: Esc bricht die
    Rückfrage ab (Enter bestätigt — der Ja-Knopf hat den Fokus)."""
    q = _pc()
    (e,) = _lauf(
        tmp_path,
        "const _ovs=[]; let _jaGerufen=0, _gestoppt=false;",
        "function esc(t){return String(t);}",
        "function _knopf(){return {onclick:null, focus(){this._fokus=true;}};}",
        "document.createElement=()=>{const ov={className:'',innerHTML:'',_h:{},_ja:_knopf(),_nein:_knopf(),"
        " querySelector(s){return s==='[data-ja]'?this._ja:this._nein;},"
        " addEventListener(t,f){this._h[t]=f;}, remove(){this._weg=true;}}; _ovs.push(ov); return ov;};",
        "document.body={appendChild(){}};",
        _js_funktion(q, "frageModal"),
        "frageModal('Wirklich?','Ja',()=>{_jaGerufen++;}); const ov=_ovs[0];",
        "if(ov._h.keydown)ov._h.keydown({key:'Escape',stopPropagation(){_gestoppt=true;},preventDefault(){}});",
        "aus({weg:!!ov._weg, ja:_jaGerufen, gestoppt:_gestoppt, fokus:!!ov._ja._fokus});")
    assert e["fokus"], "der Ja-Knopf hat den Fokus (Enter bestätigt)"
    assert e["weg"] and e["ja"] == 0 and e["gestoppt"], f"Esc schließt die Rückfrage nicht: {e}"
