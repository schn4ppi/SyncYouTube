# -*- coding: utf-8 -*-
"""Film und Serien: kleine Nebenbefunde der Analyse vom 24.09.2026.

Die Analysen „Folgenende" und „Transcoder" fanden am Rand vier kleine,
belegte Fehler. Diese Datei nagelt sie fest — mit dem ECHTEN JavaScript der
Seite, ausgeführt mit deno (Hilfen aus test_medientasten_verhalten.py):

* Die Tasten F (Vollbild) und I (Bild-in-Bild) wirkten bei offenem Film auf die
  Musik darunter: F holte beim zweiten Druck den Musik-Player ins Vollbild, I
  versuchte Bild-in-Bild auf der Musik. JB-Regel: „Die Tasten gehören dem Film".
* Serien-„▶ Weiterschauen" (tvSerienPlay) wählte die angefangene Folge richtig,
  startete sie aber immer bei 0 — die Folgen-Kachel übergab ihre Stelle, der
  Knopf nicht. Jetzt gilt dieselbe Regel wie beim Landen per ⏮/⏭
  (tvpLandePos: gesehen, ab 90 % oder bis 30 s = Anfang).

Die Attrappe modelliert den Unterschied, um den es geht (Lehrbuch: „Attrappe
muss den Unterschied modellieren"): welches Element ins Vollbild geht
(#tv-player des Films oder der Musik-Player) und wie der zweite Druck das
Vollbild wieder verlässt.
"""
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

from test_medientasten_randfaelle import _keydown  # noqa: E402
from test_medientasten_verhalten import _js_funktion, _lauf, _pc  # noqa: E402

# ------------------------------------------------------------- Tasten F und I

def test_f_und_i_gehoeren_bei_offenem_film_dem_film(tmp_path):
    """Ohne Film bleiben F und I beim Musik-Player (Vollbild, Bild-in-Bild).
    Bei offenem Film schaltet F das Film-Vollbild (#tv-player, derselbe Weg
    wie der Vollbild-Knopf der Fernbedienung), I tut nichts — der Film bietet
    kein Bild-in-Bild an, und die Musik darunter ist unsichtbar."""
    q = _pc()
    teile = [_js_funktion(q, n) for n in ("filmTasten", "tvpVollbild")] + [_keydown(q)]
    (e,) = _lauf(tmp_path, *teile, r"""
var tvpOffen=false, libPlaylistView=false, libAuswahl=new Set(), _hkFang=null;
const calls=[];
const HKMAP={KeyF:'vollbild', KeyI:'pip'};
function hkCode(e){return e.code;} function hkAktionFuer(c){return HKMAP[c]||'';}
function plbFullscreen(){calls.push('musik-vollbild');} function plbPip(){calls.push('musik-pip');}
function toast(){}
function vollbildFlaeche(id){return {id, requestFullscreen(){calls.push('vollbild-an:'+id);
  document.fullscreenElement=this; return Promise.resolve();}};}
document.exitFullscreen=()=>{calls.push('vollbild-aus:'+(document.fullscreenElement||{}).id);
  document.fullscreenElement=null; return Promise.resolve();};
_els['tv-player']=vollbildFlaeche('tv-player');
_els['pl-el']=fakeMedia({id:'pl-el', tagName:'VIDEO'});
const T=c=>kd({code:c, key:c.slice(-1).toLowerCase(), target:null, ctrlKey:false, metaKey:false,
  altKey:false, shiftKey:false, preventDefault(){}});
T('KeyF'); T('KeyI');
const ohneFilm=[...calls]; calls.length=0;
tvpOffen=true;                                        // Film offen
T('KeyF'); const an=document.fullscreenElement&&document.fullscreenElement.id;
T('KeyI');
T('KeyF');
aus({ohneFilm, film:[...calls], an, danach:document.fullscreenElement});
""")
    assert e["ohneFilm"] == ["musik-vollbild", "musik-pip"], e["ohneFilm"]
    assert e["film"] == ["vollbild-an:tv-player", "vollbild-aus:tv-player"], e["film"]
    assert e["an"] == "tv-player", "F holt den FILM ins Vollbild"
    assert e["danach"] is None, "der zweite Druck verlässt das Film-Vollbild wieder"


# ------------------------------------------------------- Serien-Weiterschauen

def test_serien_weiterschauen_setzt_an_der_gemerkten_stelle_fort(tmp_path):
    """„▶ Weiterschauen" auf der Serien-Info startet die gewählte Folge an ihrer
    gemerkten Stelle, nach derselben Regel wie ⏮/⏭ (tvpLandePos): gesehen,
    ab 90 % der Laufzeit oder bis 30 s zählt als Anfang. Die Auswahl der Folge
    (angefangene vor erster ungesehener, sonst die erste) bleibt unverändert."""
    q = _pc()
    (e,) = _lauf(tmp_path, _js_funktion(q, "tvpLandePos"), _js_funktion(q, "tvSerienPlay"), r"""
var tvInfoDaten={d:{id:'s9', typ:'serie'}, eps:[]};
const plays=[];
function filmePlay(id,pos){plays.push([id, pos===undefined?null:pos]);}
function toast(){}
const E=(id,pos,gesehen)=>({id, staffel:1, folge:+id.slice(1), laufzeit_min:40, position_s:pos, gesehen});
const fall=l=>{tvInfoDaten.eps=l; tvSerienPlay(); return plays.at(-1);};
aus({
  angefangen: fall([E('e1',0,true), E('e2',1200,false), E('e3',0,false)]),
  kurz:       fall([E('e1',0,true), E('e2',20,false),   E('e3',0,false)]),
  abspann:    fall([E('e1',0,true), E('e2',2200,false), E('e3',0,false)]),
  neu:        fall([E('e1',0,true), E('e2',0,false)]),
  alle:       fall([E('e1',500,true), E('e2',0,true)]),
});
""")
    assert e["angefangen"] == ["e2", 1200], "die angefangene Folge setzt an ihrer Stelle fort"
    assert e["kurz"] == ["e2", 0], "bis 30 s angeschaut: von vorn"
    assert e["abspann"] == ["e2", 0], "ab 90 % (Abspann): von vorn, wie beim Landen per ⏮/⏭"
    assert e["neu"] == ["e2", 0]
    assert e["alle"] == ["e1", 0], "alles gesehen: erste Folge von vorn, auch mit alter Stelle"
