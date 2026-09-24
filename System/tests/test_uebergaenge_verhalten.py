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
import re
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
KERN = ("aktKey", "queueIdxPassend", "nachEnde", "playerAdvance", "xfAbbrechen",
        "xfZuruecknehmen", "xfNaechsterIndex", "xfNachfolgerGilt", "xfPruefen", "xfIstAudio",
        "starteCrossfade", "xfLautstaerke", "xfUebernehmen", "gaplessPreload", "uebergangTick",
        "plTitelEnde", "renderPlayerMedia", "sleepSetzen", "sleepAusloesen", "sleepLabel",
        "repeatCycle")
# In dieser Runde neu: fehlen sie (Rot-Lauf am alten Stand), bleiben sie weg —
# wer sie braucht, bricht dann mit „… is not defined". Dass es sie gibt,
# erzwingt test_uebergangs_bausteine_gibt_es.
NEU = ("nachEnde", "xfZuruecknehmen", "xfNachfolgerGilt", "xfPruefen", "plTitelEnde")

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
    teile += [_js_funktion(q, n) for n in KERN + extra
              if n not in NEU or re.search(r"^function " + n + r"\(", q, re.M)]
    return teile


def test_uebergangs_bausteine_gibt_es():
    """Die EINE Entscheidung „was kommt nach dem Titelende?" und ihre Helfer
    stehen als Top-Level-Funktionen in der Seite; der ended-Listener ist die
    benannte Funktion (sonst wäre sie nicht mit dem echten Code prüfbar)."""
    q = _pc()
    for n in NEU:
        _js_funktion(q, n)
    rumpf = _js_funktion(q, "renderPlayerMedia")
    assert "addEventListener('ended',plTitelEnde)" in rumpf
    assert "nachEnde(" in _js_funktion(q, "playerAdvance"), "playerAdvance fragt die EINE Entscheidung"
    assert "nachEnde(" in _js_funktion(q, "xfNaechsterIndex"), "die Übergänge fragen dieselbe"


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


# ------------------------------------ Befund 2: EINE Entscheidung nach dem Ende
# Vorher entschieden zwei Stellen: playerAdvance kannte Sleep, Radio,
# Wiederholen, Zufall und Abspielart; die Übergänge (xfNaechsterIndex) nur
# Radio und Wiederholen-alle, und das Titelende übernahm den vorbereiteten
# Nachfolger an playerAdvance vorbei.

ENDE = r"""
function neu(o){o=o||{};                               // Grundzustand je Fall (Modul-Variablen, nicht globalThis)
  xfNext=null; adoptEl=null; vizGain=null; calls.length=0; crossfadeSek=4;
  radioAktiv=!!o.radioAktiv; playShuffle=!!o.playShuffle; playRepeat=o.playRepeat||'aus';
  uebergang=o.uebergang||'crossfade'; _passt=o._passt||(()=>true); sleepSetzen('0');
  playerState={idx:0,queue:['a','b','c'],quelle:''};}
const titel=()=>calls.filter(c=>c.startsWith('titel:')).map(c=>c.slice(6));
function vorEnde(idx,rest){const el=starte(idx); el.currentTime=100-rest; feuer(el,'timeupdate'); bild(500); return el;}
function ende(el){el.ended=true; el.paused=true; feuer(el,'ended');}
"""


def test_player_advance_reihenfolge_bleibt(tmp_path):
    """playerAdvance ohne Übergang: die Reihenfolge Sleep · Radio (schlägt
    Wiederholen-eins) · eins · Zufall · Abspielart · alle · Bibliothek. Am
    alten Stand grün, damit das Zusammenlegen nichts verschiebt."""
    q = _pc()
    e = _lauf(tmp_path, *_kern(q), ENDE, r"""
const faelle=[
 ['sleep',  ()=>{sleepSetzen('titel');}],
 ['radio',  ()=>{radioAktiv=true;}],
 ['radioEnde',()=>{radioAktiv=true; playerState.idx=2;}],
 ['radioEins',()=>{radioAktiv=true; playRepeat='eins';}],
 ['eins',   ()=>{playRepeat='eins';}],
 ['zufall', ()=>{playShuffle=true; playerState.queue=['a','b','c','d']; Math.random=()=>0.99;}],
 ['zufallLeer',()=>{playShuffle=true; _passt=x=>x.id==='a';}],
 ['art',    ()=>{_passt=x=>x.id!=='b';}],
 ['alle',   ()=>{playRepeat='alle'; playerState.idx=2; _passt=x=>x.id!=='a';}],
 ['stopp',  ()=>{playerState.idx=2;}],
 ['bib',    ()=>{playerState.queue=['a'];}],
];
for(const [name,f] of faelle){neu(); f(); calls.length=0; const vorher=playerState.idx;
  playerAdvance();
  aus({name, idx:playerState.idx, vorher, titel:titel(), bib:calls.includes('bib'), sleep:sleepTitelende});}
""")
    r = {x["name"]: x for x in e}
    assert r["sleep"]["titel"] == [] and r["sleep"]["sleep"] is False
    assert r["radio"]["idx"] == 1 and r["radio"]["titel"] == ["b"]
    assert r["radioEnde"]["idx"] == 2 and r["radioEnde"]["titel"] == ["c"], "Radio am Ende: gleicher Index"
    assert r["radioEins"]["idx"] == 1, "Radio schlägt Wiederholen-eins (Verhalten bleibt)"
    assert r["eins"]["idx"] == 0 and r["eins"]["titel"] == ["a"]
    assert r["zufall"]["idx"] == 3 and r["zufall"]["titel"] == ["d"]
    assert r["zufallLeer"]["titel"] == [], "Zufall ohne passenden Kandidaten: Stopp"
    assert r["art"]["idx"] == 2 and r["art"]["titel"] == ["c"], "Abspielart überspringt b"
    assert r["alle"]["idx"] == 1 and r["alle"]["titel"] == ["b"], "alle: von vorn, erster passender"
    assert r["stopp"]["titel"] == [] and r["stopp"]["bib"] is False
    assert r["bib"]["bib"] is True and r["bib"]["titel"] == []


def test_sleep_nach_diesem_titel_schlaegt_den_uebergang(tmp_path):
    q = _pc()
    e = _lauf(tmp_path, *_kern(q), ENDE, r"""
for(const art of ['crossfade','gapless','automix']){
  neu({uebergang:art}); sleepSetzen('titel'); const el=starte(0); calls.length=0;
  el.currentTime=art==='gapless'?90:97; feuer(el,'timeupdate'); bild(500);
  const vorbereitet=!!xfNext; ende(el);
  aus({art, vorbereitet, titel:titel(), bleibt:_els['pl-el']===el, sleep:sleepTitelende});
}
""")
    for x in e:
        assert x["vorbereitet"] is False, f"{x['art']}: bei Sleep nach diesem Titel kein Übergang"
        assert x["titel"] == [] and x["bleibt"] is True, f"{x['art']}: nach dem Titel ist Schluss"
        assert x["sleep"] is False, f"{x['art']}: der Sleep-Timer hat ausgelöst"


def test_wiederholen_eins_schlaegt_den_uebergang(tmp_path):
    q = _pc()
    e = _lauf(tmp_path, *_kern(q), ENDE, r"""
for(const art of ['crossfade','gapless','automix']){
  neu({uebergang:art, playRepeat:'eins'}); const el=starte(0); calls.length=0;
  el.currentTime=art==='gapless'?90:97; feuer(el,'timeupdate'); bild(500);
  const vorbereitet=!!xfNext; ende(el);
  const jetzt=_els['pl-el'];
  aus({art, vorbereitet, titel:titel(), idx:playerState.idx, frisch:jetzt!==el&&!_audios.includes(jetzt)});
}
""")
    for x in e:
        assert x["vorbereitet"] is False, f"{x['art']}: eins blendet nicht in den nächsten Titel"
        assert x["titel"] == ["a"] and x["idx"] == 0 and x["frisch"] is True, x


def test_sleep_oder_eins_waehrend_der_blende_nehmen_sie_zurueck(tmp_path):
    """Wettlauf: Sleep bzw. eins wird erst gesetzt, wenn der Nachfolger schon
    hörbar einblendet. sleepSetzen/repeatCycle nehmen die Blende sofort
    zurück; wird die Regel am Menü vorbei gesetzt, fängt das Titelende sie."""
    q = _pc()
    sleep, eins, direkt, anAus = _lauf(tmp_path, *_kern(q), ENDE, r"""
function lauf(name,setzen){
  neu({playRepeat:'alle'}); const el=vorEnde(0,3); bild(500); const nx=xfNext; calls.length=0;
  setzen(el);
  const sofort={weg:xfNext===null, src:nx.src, paused:nx.paused, vol:r3(el.volume), xf:el._xf};
  feuer(el,'timeupdate'); bild(500);
  const wieder=!!xfNext; ende(el);
  aus({name, sofort, wieder, titel:titel(), sleep:sleepTitelende, vol:r3(el.volume), src:nx.src});
}
lauf('sleep',()=>sleepSetzen('titel'));
lauf('eins',()=>repeatCycle());                         // alle -> eins
lauf('direkt',()=>{sleepTitelende=true;});              // am Menü vorbei
// an, ein timeupdate im Fenster (uebergangTick merkt „Blende versucht"), wieder aus
lauf('anAus',el=>{sleepSetzen('titel'); feuer(el,'timeupdate'); sleepSetzen('0');});
""")
    for x in (sleep, eins):
        assert x["sofort"] == {"weg": True, "src": "", "paused": True, "vol": 0.4, "xf": False}, x
        assert x["wieder"] is False, f"{x['name']}: im Fenster startet keine neue Blende"
    assert sleep["titel"] == [] and sleep["sleep"] is False
    assert eins["titel"] == ["a"], "eins: derselbe Titel frisch von vorn"
    assert direkt["sofort"]["weg"] is False, "am Menü vorbei: die Blende läuft bis zum Ende"
    assert direkt["titel"] == [] and direkt["src"] == "" and direkt["vol"] == 0.4, \
        "das Titelende nimmt sie zurück: Nachfolger freigegeben, alter Titel wieder laut, Schluss"
    # Dokumentierte Grenze (Gegenprüfung, Korrektur 3): Sleep im Fenster an und
    # wieder aus — für DIESEN Wechsel keine Blende mehr, das Ende schaltet hart weiter.
    assert anAus["wieder"] is False and anAus["titel"] == ["b"], anAus


def test_normaler_uebergang_und_radio_mit_eins_laufen_weiter(tmp_path):
    """Gegenprobe gegen „Übergänge ganz aus": ohne Sleep/eins übernimmt das
    Titelende den Nachfolger; Radio schlägt eins (Verhalten wie bisher)."""
    q = _pc()
    e = _lauf(tmp_path, *_kern(q), ENDE, r"""
for(const [name,o] of [['normal',{}],['gapless',{uebergang:'gapless'}],['radioEins',{radioAktiv:true,playRepeat:'eins'}]]){
  neu(o); const el=vorEnde(0,name==='gapless'?10:3); const nx=xfNext; calls.length=0; ende(el);
  aus({name, key:nx&&nx._key, uebernommen:!!nx&&_els['pl-el']===nx, idx:playerState.idx, titel:titel()});
}
""")
    for x in e:
        assert x["key"] == "b" and x["uebernommen"] is True and x["idx"] == 1 and x["titel"] == ["b"], x


def test_titelende_eines_abgeloesten_elements_schaltet_nicht(tmp_path):
    """Der ended-Listener nimmt das Element aus dem Ereignis: meldet ein schon
    abgelöstes (nicht mehr im Dokument), entscheidet es nichts mehr."""
    q = _pc()
    (e,) = _lauf(tmp_path, *_kern(q), ENDE, r"""
neu(); const alt=starte(0); starte(1); calls.length=0;
alt.ended=true; feuer(alt,'ended');
aus({titel:titel(), idx:playerState.idx, verbunden:alt.isConnected});
""")
    assert e == {"titel": [], "idx": 1, "verbunden": False}, e


def test_zufall_und_abspielart_gelten_auch_fuer_den_uebergang(tmp_path):
    """Zufall: der Index wird EINMAL gezogen und im vorbereiteten Element
    gehalten (ein zweiter Zug am Titelende darf ihn nicht ändern).
    Abspielart: ein nicht passender Titel wird übersprungen."""
    q = _pc()
    zufall, art = _lauf(tmp_path, *_kern(q), ENDE, r"""
neu({playShuffle:true}); playerState.queue=['a','b','c','d']; Math.random=()=>0.99;
{ const el=vorEnde(0,3); const nx=xfNext; Math.random=()=>0; ende(el);
  aus({key:nx&&nx._key, uebernommen:!!nx&&_els['pl-el']===nx, idx:playerState.idx}); }
neu({_passt:x=>x.id!=='b'});
{ const el=vorEnde(0,3); const nx=xfNext; ende(el);
  aus({key:nx&&nx._key, uebernommen:!!nx&&_els['pl-el']===nx, idx:playerState.idx}); }
""")
    assert zufall == {"key": "d", "uebernommen": True, "idx": 3}, zufall
    assert art == {"key": "c", "uebernommen": True, "idx": 2}, art


# ------------------------------- Befund 4: Warteschlangen-Umbau in der Blende
# Vorher setzte die Übernahme blind den gemerkten Index; nach einem Umbau
# zeigte er auf einen anderen Titel, renderPlayerMedia verwarf das schon
# spielende Element ohne Freigabe — es lief verwaist und unsteuerbar weiter.
# Regel (Gegenprüfung): übernommen wird nur, was die Warteschlange JETZT als
# Nächstes vorsieht; sonst freigeben und normal weiter.

def test_warteschlangen_umbau_waehrend_der_blende(tmp_path):
    q = _pc()
    extra = ("plqRemove", "queueAlsNaechstes", "queueUmkehren")
    e = _lauf(tmp_path, *_kern(q, *extra), ENDE, r"""
function fall(name, queue, idx, umbau, art){
  neu({uebergang:art}); playerState.queue=queue; const el=vorEnde(idx,art==='gapless'?10:3);
  const nx=xfNext; calls.length=0; _log.length=0;
  umbau(); ende(el);
  const jetzt=_els['pl-el'];
  aus({name, vorbereitet:nx&&nx._key, uebernommen:jetzt===nx, titel:titel(), idx:playerState.idx,
       aktuell:playerState.queue[playerState.idx], nxSrc:nx&&nx.src, nxPaused:nx&&nx.paused,
       gestartet:_log.includes('play:'+(nx&&nx.id))});
}
fall('davorWeg', ['z','a','b','c'], 1, ()=>plqRemove(0));
fall('nachfolgerWeg', ['z','a','b','c'], 1, ()=>plqRemove(2));
fall('alsNaechstes', ['a','b','c'], 0, ()=>queueAlsNaechstes('N'));
fall('umkehren', ['a','b','c','d'], 1, ()=>queueUmkehren());
// Gapless: der gepufferte Nachfolger darf nach dem Umbau nicht einmal kurz anlaufen
fall('alsNaechstesGapless', ['a','b','c'], 0, ()=>queueAlsNaechstes('N'), 'gapless');
""")
    r = {x["name"]: x for x in e}
    assert r["davorWeg"]["uebernommen"] is True and r["davorWeg"]["aktuell"] == "b", r["davorWeg"]
    for name, soll in (("nachfolgerWeg", "c"), ("alsNaechstes", "N"), ("umkehren", "a"),
                       ("alsNaechstesGapless", "N")):
        x = r[name]
        assert x["uebernommen"] is False and x["aktuell"] == soll and x["titel"] == [soll], x
        assert x["nxSrc"] == "" and x["nxPaused"] is True, f"{name}: das vorbereitete Element ist frei"
    assert r["alsNaechstesGapless"]["gestartet"] is False, r["alsNaechstesGapless"]


def test_verworfenes_uebernahme_element_wird_freigegeben(tmp_path):
    """Verteidigung in renderPlayerMedia: passt das übernommene Element nicht
    zum Titel, wird es freigegeben statt nur vergessen."""
    q = _pc()
    (e,) = _lauf(tmp_path, *_kern(q), r"""
starte(0);
const fremd=mediaEl({id:'fremd',src:'/media?id=x',paused:false}); fremd._key='x'; adoptEl=fremd;
playerState.idx=1; renderPlayerMedia();
aus({src:fremd.src, paused:fremd.paused, adoptEl, spielt:_els['pl-el']!==fremd});
""")
    assert e == {"src": "", "paused": True, "adoptEl": None, "spielt": True}, e


# ------------------------------------------------ Befund 3 + Menü: Sleep-Timer
# Eine Uhr, die der Test auslöst (sonst hielte ein echter 15-min-Timer deno fest).
UHR = r"""
const _timer=[];
globalThis.setTimeout=(f,ms)=>{_timer.push({f,ms}); return _timer.length;};
globalThis.clearTimeout=id=>{if(_timer[id-1])_timer[id-1].f=()=>{};};
function timerLaeuftAb(){_timer.splice(0).forEach(t=>t.f());}
"""


def test_sleep_timer_stoppt_auch_vlc(tmp_path):
    """Am Gerät VLC gibt es kein pl-el: der Minuten-Timer setzte nur die
    Anzeige zurück, VLC spielte weiter. Der Film bleibt unberührt (JB-Frage)."""
    q = _pc()
    vlc_min, vlc_titel, browser = _lauf(tmp_path, UHR, *_kern(q), ENDE, r"""
neu(); _vlc=true; delete _els['pl-el']; calls.length=0;
sleepSetzen('15'); timerLaeuftAb();
aus({fall:'vlcMinuten', calls:[...calls], ende:sleepEndeZeit});
neu(); _vlc=true; delete _els['pl-el']; sleepSetzen('titel'); calls.length=0;
playerAdvance();                                        // wie vlcTick beim Zustand 'ende'
aus({fall:'vlcTitel', calls:[...calls], sleep:sleepTitelende});
neu(); _vlc=false; const el=starte(0); calls.length=0;
sleepSetzen('30'); timerLaeuftAb();
aus({fall:'browser', calls:[...calls], pausiert:el.paused, ende:sleepEndeZeit});
""")
    assert vlc_min == {"fall": "vlcMinuten", "calls": ["vlc:pause"], "ende": 0}, vlc_min
    assert vlc_titel == {"fall": "vlcTitel", "calls": ["vlc:pause"], "sleep": False}, vlc_titel
    assert browser == {"fall": "browser", "calls": [], "pausiert": True, "ende": 0}, browser


def test_sleep_menue_zeigt_die_laufende_stufe(tmp_path):
    """Das Optionen-Menü zeigte bei laufendem Minuten-Timer „aus" — „aus"
    erneut zu wählen löste kein change aus, der Timer war übers Menü nicht
    abzuschalten. Geprüft wird die echte Zeile aus dem Menü-Aufbau."""
    q = _pc()
    m = re.search(r"^\s*(const slp=m\.querySelector\('#opt_sleep'\);.*)$", q, re.M)
    assert m, "Sleep-Zeile im Optionen-Menü nicht gefunden"
    (e,) = _lauf(tmp_path, UHR, *_kern(q), "function menue(m){" + m.group(1) + " return slp.value;}", r"""
const slp={value:''}, M={querySelector:s=>s==='#opt_sleep'?slp:null}, werte=[];
for(const v of ['30','titel','0','60']){sleepSetzen(v); werte.push(menue(M));}
timerLaeuftAb(); werte.push(menue(M));                  // abgelaufen: wieder „aus"
aus({werte});
""")
    assert e == {"werte": ["30", "titel", "0", "60", "0"]}, e
