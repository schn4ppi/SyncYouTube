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
        "xfIstAudio", "starteCrossfade", "xfLautstaerke", "xfUebernehmen", "gaplessPreload",
        "uebergangTick", "renderPlayerMedia", "sleepSetzen", "sleepAusloesen", "sleepLabel",
        "repeatCycle")

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


# ------------------------------------------- Befund 1: Lautstärke der Blende
# Vorher rampte der neue Titel absolut von 0 auf 1,0 (plVol nie gelesen) und
# sprang bei der Übernahme auf plVol; ohne Web Audio sprang der ALTE Titel im
# ersten Bild von plVol auf 1,0. Ziel jeder Rampe: die eingestellte Lautstärke.

def test_crossfade_haelt_die_eingestellte_lautstaerke(tmp_path):
    q = _pc()
    ohne, mit = _lauf(tmp_path, *_kern(q), r"""
for(const mitGain of [false,true]){
  xfNext=null; vizGain=mitGain?{gain:{value:1}}:null;
  const el=starte(0); el.currentTime=96;               // Rest 4 s = crossfadeSek
  feuer(el,'timeupdate');
  const nx=xfNext; let maxNeu=nx.volume, maxAlt=el.volume, mitte=null;
  for(let i=1;i<=8;i++){bild(500); maxNeu=Math.max(maxNeu,nx.volume); maxAlt=Math.max(maxAlt,el.volume);
    if(i===4)mitte={neu:r3(nx.volume),alt:r3(el.volume),gain:vizGain&&r3(vizGain.gain.value)};}
  const ende={neu:r3(nx.volume),alt:r3(el.volume),gain:vizGain&&r3(vizGain.gain.value)};
  el.ended=true; feuer(el,'ended');
  aus({mitGain, maxNeu:r3(maxNeu), maxAlt:r3(maxAlt), mitte, ende,
       uebernommen:_els['pl-el']===nx, vol:r3(nx.volume)});
}
""")
    assert ohne["maxNeu"] <= 0.4 and ohne["ende"]["neu"] == 0.4, ohne
    assert ohne["maxAlt"] <= 0.4, "ohne Web Audio darf der alte Titel nicht erst auf 100 % springen"
    assert ohne["mitte"] == {"neu": 0.2, "alt": 0.2, "gain": None}, ohne
    assert ohne["ende"]["alt"] == 0 and ohne["uebernommen"] and ohne["vol"] == 0.4, ohne
    assert mit["maxAlt"] == 0.4 and mit["mitte"] == {"neu": 0.2, "alt": 0.4, "gain": 0.5}, mit
    assert mit["ende"] == {"neu": 0.4, "alt": 0.4, "gain": 0} and mit["maxNeu"] <= 0.4, mit


def test_crossfade_folgt_der_lautstaerke_bis_zur_uebernahme(tmp_path):
    """Regler/Pfeiltaste während der Blende UND nach ihrem Ende (Automix
    blendet bis zu 16 s vor dem Titelende): plbVol erreicht nur pl-el, also
    den alten, stummen Titel — die Rampe muss plVol weiter nachführen."""
    q = _pc()
    (e,) = _lauf(tmp_path, *_kern(q), r"""
const el=starte(0); el.currentTime=96; feuer(el,'timeupdate'); const nx=xfNext;
for(let i=0;i<4;i++)bild(500);                          // p = 0,5
plVol=80; bild(500);                                   // p = 0,625
const waehrend=r3(nx.volume);
bild(500); bild(500); bild(500);                       // p = 1: Blende fertig, Titel läuft noch
plVol=20; bild(16);
aus({waehrend, danach:r3(nx.volume), alt:r3(el.volume)});
""")
    assert e == {"waehrend": 0.5, "danach": 0.2, "alt": 0}, e


def test_crossfade_mit_tempo_endet_mit_dem_titel(tmp_path):
    """Die Restzeit ist Medienzeit, die Rampe läuft in Wanduhrzeit: bei 2×
    endet der Titel nach der halben Zeit. Der Nachfolger läuft im selben
    Tempo ein (sonst springt das Tempo bei der Übernahme)."""
    q = _pc()
    zwei, halb = _lauf(tmp_path, *_kern(q), r"""
for(const rate of [2,0.5]){
  xfNext=null;
  const el=starte(0); el.playbackRate=rate; el.currentTime=96; feuer(el,'timeupdate');
  const nx=xfNext;
  for(let i=0;i<4;i++)bild(500);                        // 2 s Wanduhr
  aus({rate, neu:r3(nx.volume), alt:r3(el.volume), tempo:nx.playbackRate, grund:nx.defaultPlaybackRate});
}
""")
    assert zwei == {"rate": 2, "neu": 0.4, "alt": 0, "tempo": 2, "grund": 2}, zwei
    assert halb == {"rate": 0.5, "neu": 0.1, "alt": 0.3, "tempo": 0.5, "grund": 0.5}, halb


def test_crossfade_im_hintergrund_folgt_der_restzeit(tmp_path):
    """Verdeckter Tab: requestAnimationFrame ruht, timeupdate läuft weiter.
    Ohne Nachführung im timeupdate-Takt spielte der neue Titel stumm und
    setzte erst bei der Übernahme mitten im Lied ein."""
    q = _pc()
    eins, zwei = _lauf(tmp_path, *_kern(q), r"""
for(const rate of [1,2]){
  xfNext=null;
  const el=starte(0); el.playbackRate=rate; el.currentTime=96; feuer(el,'timeupdate');
  const nx=xfNext, stufen=[];                           // KEIN bild(): das Bild ruht
  for(const t of [97,98,99]){el.currentTime=t; feuer(el,'timeupdate'); stufen.push(r3(nx.volume));}
  aus({rate, stufen, alt:r3(el.volume)});
}
""")
    assert eins == {"rate": 1, "stufen": [0.1, 0.2, 0.3], "alt": 0.1}, eins
    # Bei 2× dauert die Blende 2 s Wanduhr für 4 s Medienzeit: nach 1 s
    # Medienzeit (0,5 s Wanduhr) ist sie zu einem Viertel durch — wie bei 1×.
    assert zwei == {"rate": 2, "stufen": [0.1, 0.2, 0.3], "alt": 0.1}, zwei


def test_gapless_startet_mit_der_eingestellten_lautstaerke(tmp_path):
    q = _pc()
    (e,) = _lauf(tmp_path, *_kern(q), r"""
uebergang='gapless';
const el=starte(0); el.currentTime=90; feuer(el,'timeupdate');
const nx=xfNext; let beimStart=null; const p0=nx.play;
nx.play=function(){beimStart=r3(this.volume); return p0.call(this);};
el.ended=true; feuer(el,'ended');
aus({beimStart, uebernommen:_els['pl-el']===nx});
""")
    assert e == {"beimStart": 0.4, "uebernommen": True}, e


def test_automix_ohne_ueberblenddauer_blendet_sechs_sekunden(tmp_path):
    """Überblend-Dauer „aus" (0): Automix meint 6 s (crossfadeSek||6), die
    Rampe rechnete aber mit 0 und blendete in 0,3 s."""
    q = _pc()
    (e,) = _lauf(tmp_path, *_kern(q), r"""
uebergang='automix'; crossfadeSek=0; vizGain={gain:{value:1}};
const el=starte(0); el.currentTime=95; feuer(el,'timeupdate');   // Rest 5 s
bild(1000);
aus({gain:r3(vizGain.gain.value), laeuft:!!xfNext});
""")
    assert e == {"gain": 0.8, "laeuft": True}, e
