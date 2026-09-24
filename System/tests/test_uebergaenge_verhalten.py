# -*- coding: utf-8 -*-
"""Übergänge (Crossfade · Gapless · Automix): VERHALTEN statt Schreibweise.

Ausgeführt wird das ECHTE JavaScript der PC-Oberfläche mit deno (Hilfen aus
test_medientasten_verhalten.py): `renderPlayerMedia` baut das Player-Element,
die Ereignisse (timeupdate, pause, seeked, ended) laufen durch die echten
Listener, `uebergangTick`/`starteCrossfade`/`xfUebernehmen` blenden wirklich.

Die Attrappe modelliert, worum es geht (Lehrbuch: die Attrappe muss den
Unterschied modellieren):
* eine steuerbare Uhr (`performance.now`) und ein Bildtakt, der nur läuft,
  wenn der Test `bild(ms)` ruft — so ist ein ruhendes requestAnimationFrame
  (Hintergrund-Tab) darstellbar;
* Elemente mit eigener Lautstärke, eigenem Tempo und Anschluss ans Dokument
  (`isConnected`), dazu die Freigabe (`medienS.freigeben`: Quelle weg + Pause).

Nicht hier gemessen: die hörbare Wirkung im echten Browser (Chromium mischt
el.volume und den Web-Audio-Graphen selbst) und ob timeupdate im verdeckten
Tab wirklich weiterläuft (bekanntes Browserverhalten, nicht gemessen).
"""
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

from test_medientasten_verhalten import (  # noqa: E402
    _js_funktion,
    _js_zeile,
    _lauf,
    _modul_js,
    _pc,
)

# Der Player-Kern, den diese Tests mit ausführen (echter Seiten-Code).
KERN = ("aktKey", "queueIdxPassend", "playerAdvance", "xfAbbrechen", "xfNaechsterIndex",
        "xfIstAudio", "starteCrossfade", "xfUebernehmen", "gaplessPreload", "uebergangTick",
        "renderPlayerMedia", "sleepSetzen", "sleepAusloesen", "sleepLabel", "repeatCycle")

UMGEBUNG = r"""
let _T=0; const performance={now:()=>_T};                 // steuerbare Uhr
const _raf=[]; function requestAnimationFrame(f){_raf.push(f);}
function bild(ms){_T+=ms; _raf.splice(0).forEach(g=>g());} // EIN Bild nach ms Millisekunden
function mediaEl(o){const e=fakeMedia(Object.assign({volume:1,_h:{}},o));
  e.addEventListener=function(t,f){(this._h[t]=this._h[t]||[]).push(f);}; return e;}
function feuer(el,t){((el._h||{})[t]||[]).forEach(f=>f({target:el,type:t}));}
const _audios=[];
globalThis.Audio=function(src){const e=mediaEl({id:'xf:'+decodeURIComponent(String(src).split('id=')[1]||''),
  src,isConnected:false}); _audios.push(e); return e;};
globalThis.fetch=()=>Promise.resolve({ok:true,json:async()=>({})});
const calls=[];
var uebergang='crossfade', crossfadeSek=4, xfNext=null, adoptEl=null, vizGain=null, vizAnalyser=null,
    plVol=40, radioAktiv=false, playShuffle=false, playRepeat='aus', plGeraet='browser', tvpOffen=false,
    playerState={idx:0,queue:['a','b','c'],quelle:''}, plqSel=null, _vlc=false, _nr=0;
let _passt=()=>true;
function libFind(k){return (k===undefined||k===null)?undefined:{id:k,titel:k,vorhanden:true,kategorie:'MP3',dateiart:'audio'};}
function artPasst(x){return _passt(x);}
function radioNachfuellen(){calls.push('nachfuellen');}
function naechstesAusBibliothek(){calls.push('bib');}
function vlcAktiv(){return _vlc;}
function vlcBefehl(c){calls.push('vlc:'+c); return Promise.resolve({});}
function renderPlayerVlc(){calls.push('vlc-ansicht');}
function filmTasten(){return false;}
function esc(s){return String(s);} function plBarHTML(){return '';}
function spulStopp(){} function cmdNowRender(){} function transportRender(){} function medienZustand(){}
function subTick(){} function karLauf(){} function plBarIdleInit(){} function seitenverhaeltnisAnwenden(){}
function vizVerbinde(){} function vizFarbeAktualisieren(){} function vizModeRender(){} function vizStart(){}
function medienInfoSetzen(x,k){calls.push('titel:'+k);}
function lieblingMalen(){} function renderPlayerQueue(){} function playerLayoutSet(){}
function speedAnwenden(){} function wiedergabeAnwenden(){} function renderKapitel(){} function subLaden(){}
function canvasAnwenden(){} function plqFocus(){} function toast(){} function ensurePlayer(){}
_els['pl-titel']={}; _els['pl-pos']={};
_els['pl-media']={classList:{remove(){},toggle(){}}, onclick:null,
  set innerHTML(h){const alt=_els['pl-el']; if(alt)alt.isConnected=false;
    if(h.includes('id="pl-el"'))_els['pl-el']=mediaEl({id:'pl-el#'+(++_nr)}); else delete _els['pl-el'];},
  appendChild(e){e.isConnected=true; _els['pl-el']=e;}};
// Titel starten (wie playerPlay): Element bauen, es spielt und hat eine Dauer.
function starte(idx){playerState.idx=idx; renderPlayerMedia();
  const el=_els['pl-el']; el.paused=false; el.duration=100; el.currentTime=0; return el;}
const r3=v=>Math.round(v*1000)/1000;
"""


def _kern(q, *extra):
    """Attrappe + Baustein + echter Player-Kern der Seite."""
    teile = [UMGEBUNG, _modul_js(), _js_zeile(q, "const medienS="), _js_zeile(q, "let sleepTimer=")]
    teile += [_js_funktion(q, n) for n in KERN + extra]
    return teile


# ------------------------------------------- Pause/Rücksprung in der Blende
# Diese beiden Wege nahmen die Überblendung schon vor dieser Runde zurück
# (zwei gleiche Dreierzeilen in renderPlayerMedia). Die Tests entstanden
# VOR dem Zusammenlegen in einen Helfer und waren am alten Stand grün.

def test_pause_in_der_blende_nimmt_den_uebergang_zurueck(tmp_path):
    q = _pc()
    ergebnisse = _lauf(tmp_path, *_kern(q), r"""
for(const mitGain of [false,true]){
  xfNext=null; vizGain=mitGain?{gain:{value:1}}:null;
  const el=starte(0); el.currentTime=97;
  feuer(el,'timeupdate');                              // Crossfade startet (Rest 3 s)
  bild(500); bild(500);
  const nx=xfNext, vorher={laeuft:!!nx&&!nx.paused, xf:el._xf};
  el.pause(); feuer(el,'pause');
  aus({mitGain, vorher, xfNext, nxSrc:nx.src, nxPaused:nx.paused, xf:el._xf, vol:r3(el.volume),
       gain:vizGain&&vizGain.gain.value});
}
// Gapless: der Nachfolger ist nur gepuffert (pausiert) -> Pause lässt ihn liegen
uebergang='gapless'; xfNext=null; vizGain=null;
{ const el=starte(0); el.currentTime=90; feuer(el,'timeupdate');
  const nx=xfNext; el.pause(); feuer(el,'pause');
  aus({gapless:true, bleibt:xfNext===nx&&!!nx, src:nx&&nx.src}); }
// Natürliches Ende: 'pause' feuert vor 'ended', der Übergang darf NICHT weg
uebergang='crossfade'; xfNext=null;
{ const el=starte(0); el.currentTime=97; feuer(el,'timeupdate'); bild(500);
  const nx=xfNext; el.ended=true; el.pause(); feuer(el,'pause');
  aus({ende:true, bleibt:xfNext===nx&&!!nx&&!nx.paused}); }
""")
    ohne, mit, gapless, ende = ergebnisse
    for e in (ohne, mit):
        assert e["vorher"] == {"laeuft": True, "xf": True}, e
        assert e["xfNext"] is None and e["nxSrc"] == "" and e["nxPaused"] is True, \
            "der einblendende Titel muss freigegeben werden (Quelle weg, pausiert)"
        assert e["xf"] is False, "nach dem Weiterspielen muss uebergangTick neu starten dürfen"
        assert e["vol"] == 0.4, "der alte Titel bekommt die eingestellte Lautstärke zurück"
    assert mit["gain"] == 1, "die Web-Audio-Verstärkung des alten Titels geht auf 1 zurück"
    assert gapless["bleibt"] is True and gapless["src"], "Gapless: der gepufferte Nachfolger bleibt"
    assert ende["bleibt"] is True, "beim natürlichen Ende bleibt die Überblendung (übernimmt gleich)"


def test_ruecksprung_aus_der_blende_nimmt_den_uebergang_zurueck(tmp_path):
    q = _pc()
    (e,) = _lauf(tmp_path, *_kern(q), r"""
const el=starte(0); el.currentTime=97; feuer(el,'timeupdate'); bild(500);
const nx=xfNext;
el.currentTime=96.2; feuer(el,'seeked');               // Rest 3,8 s: noch im Fenster -> bleibt
const bleibt=xfNext===nx;
el.currentTime=50; feuer(el,'seeked');                 // weit zurück -> Übergang zurück
aus({bleibt, xfNext, nxSrc:nx.src, nxPaused:nx.paused, xf:el._xf, vol:r3(el.volume)});
""")
    assert e["bleibt"] is True, "ein kleiner Sprung im Fenster bricht die Blende nicht ab"
    assert e["xfNext"] is None and e["nxSrc"] == "" and e["nxPaused"] is True
    assert e["xf"] is False and e["vol"] == 0.4
