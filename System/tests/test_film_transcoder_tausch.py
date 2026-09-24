# -*- coding: utf-8 -*-
"""Film im Browser: der Transcoder-Sprung TAUSCHT das <video> (24.09.2026).

Befund: Jeder Sprung im Transcoder-Modus (Pfeile, Balken, Windows-Zeitleiste,
zweites ⏮ in Serien) und die Selbstheilung „direkt → Transcoder" setzten eine
neue Quelle im SELBEN Element. Das verwirft den alten Abspieler sofort — nach
der Messung vom 24.09. (Folgenwechsel, Edge + Windows 11) gibt Windows dann bei
der nächsten Pause die „aktuelle Sitzung" an eine andere pausierte App ab, und
⏯ startet Firefox oder Spotify statt den Film. Der Folgenwechsel war schon
richtig gebaut (altes Video anhalten, erst leeren, wenn das neue spielt); der
Sprung-Weg nutzt jetzt dieselbe Mechanik: ein NEUES Element an derselben
Stelle, das alte wird nur gehalten, wenn es wirklich gespielt hat.

Die Attrappe modelliert die Unterschiede, um die es geht (Lehrbuch: „Attrappe
muss den Unterschied modellieren"):

* currentSrc wechselt erst bei der Quellenwahl — ein NEUES Element hat bis
  dahin ein leeres currentSrc (der Film-Takt hielt das für das Filmende), ein
  altes Element meldet noch die vorige Quelle.
* Eine neue Quelle setzt das Tempo auf defaultPlaybackRate zurück
  (Lade-Algorithmus der HTML-Spezifikation) — wer nur playbackRate überträgt,
  verliert 1,5x beim Sprung.
* play() kann verweigert werden (Autoplay); das Element bleibt dann stehen.

Nicht hier gemessen: ob Windows die Sitzung beim Tausch wirklich bei Edge lässt
(Live-Messung braucht den Transcoder, also Renés Jellyfin, Stand 24.09. mit
HTTP 401 blockiert) und was der Server mit dem Strom des gehaltenen Elements
macht (ein Transcode zur Zeit, youtube_app._tc_starten).
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

# Attrappe: Film-<video> mit Lade-Algorithmus, Quellenwahl und Listener-Liste,
# dazu der #tv-player, der beim Neuaufbau (innerHTML) sein Video austauscht.
ATTRAPPE = r"""
var tvpOffen=false, tvpPos=0, tvpDauer=0, tvpLief=false, tvpTicks=0, tvpAktiv=0, tvpIdAkt='', tvpMeta={},
    tvInfoDaten=null, tvHeroDaten=null, tvpZurueckModus='normal', tvpModusNaechster=null, tvpWechsel=null,
    tvpModus='browser', vlcKeyLetzter='', tvpTc=false, tvpTcOffset=0, tvpTcVcopy=false, plVol=40, tvpTimer=1,
    _tvpSprungTimer=null, tvInfoOffen=false, vlcSpielt=false;
globalThis.screen={isExtended:false};
document.body={appendChild(){}}; document.querySelector=()=>null;
const toasts=[], vlcStarts=[], gemerkt=[];
function ico(){return '';} function esc(s){return s;} function zeit(s){return String(s);}
function tvpWach(){} function toast(t){toasts.push(t);} function tvpMedienZustand(){} function tvpMedienAn(){}
function tvpIdleTick(){} function tvInfoMalen(){}
function filmePlayVlc(id,pos,mm){vlcStarts.push([id,pos]);}
function vlcBefehl(){return Promise.resolve({});}
function tvpFolgePosMerken(id,p){gemerkt.push([id,p]);} function medienNachFilm(){}
const _videos=[]; let _playScheitert=false;
function filmVideo(){
  const v={id:'', className:'', autoplay:false, paused:true, currentTime:0, duration:NaN, ended:false,
    defaultPlaybackRate:1, playbackRate:1, muted:false, volume:1, isConnected:false,
    played:{length:0}, _src:'', _cs:'', _geladen:false, _h:{}, _attr:{},
    get src(){return this._src;},
    set src(u){this._src=String(u); this._laden();},
    get currentSrc(){return this._cs;},             // wechselt erst bei der Quellenwahl
    _laden(){                                       // Lade-Algorithmus (HTML-Spezifikation)
      if(this._geladen)this.paused=true;
      this._geladen=true; this.currentTime=0; this.playbackRate=this.defaultPlaybackRate;
    },
    quellenwahl(){this._cs=this._src;},
    play(){_log.push('play:'+this.nr);
      if(_playScheitert)return Promise.reject(new Error('NotAllowedError'));
      this.paused=false; return Promise.resolve();},
    pause(){this.paused=true; _log.push('pause:'+this.nr);},
    setAttribute(n,w){this._attr[n]=String(w);},
    removeAttribute(n){if(n==='src')this._src=''; _log.push('ohneQuelle:'+this.nr);},
    load(){this._laden(); _log.push('load:'+this.nr);},
    addEventListener(n,f,o){(this._h[n]=this._h[n]||[]).push({f,once:!!(o&&o.once)});},
    feuer(n){const l=this._h[n]||[]; this._h[n]=l.filter(x=>!x.once); l.forEach(x=>x.f({stopPropagation(){}}));},
    hoert(n){return (this._h[n]||[]).length;},
    replaceWith(n){this.isConnected=false; if(_els['tvp-video']===this)_els['tvp-video']=n; n.isConnected=true;}
  };
  v.nr=_videos.push(v);
  return v;
}
document.createElement=t=>{if(t!=='video')throw new Error('unerwartet: '+t); return filmVideo();};
function spielen(v){v.quellenwahl(); v.paused=false; v.played={length:1}; v.feuer('playing');}
_els['tv-player']={id:'tv-player', style:{}, classList:{add(){},remove(){},toggle(){}}, contains(){return true;},
  addEventListener(){},
  set innerHTML(h){                                   // Neuaufbau: das alte Video fliegt aus dem Dokument
    if(_els['tvp-video'])_els['tvp-video'].isConnected=false;
    const m=/<video id="tvp-video"[^>]*src="([^"]*)"/.exec(h);
    if(m){const v=filmVideo(); v.id='tvp-video'; v.autoplay=true; v.isConnected=true; v.src=m[1]; _els['tvp-video']=v;}
    else delete _els['tvp-video'];
  }};
const META={titel:'Eins', laufzeit_min:120};
"""

TICK_STUB = "function tvpTick(){}"


def _teile(*extra, tick_echt=False):
    q = _pc()
    namen = ["tvpDirektSrc", "tvpBefehl", "tvpAbgeloestFreigeben", "tvpVideoVerdrahten",
             "tvpVideoTauschen", "tvFilmPlayer", "tvpZu"] + list(extra)
    if tick_echt:
        namen.append("tvpTick")
    return ([_modul_js(), "const medienS=medienSitzung(()=>null);", _js_zeile(q, "let tvpAbgeloest"),
             ATTRAPPE] + ([] if tick_echt else [TICK_STUB]) + [_js_funktion(q, n) for n in namen])


def test_transcoder_sprung_tauscht_das_element(tmp_path):
    """T1: Ein Sprung im Transcoder baut ein NEUES <video> an derselben Stelle.
    Lautstärke, Stumm und Tempo (auch defaultPlaybackRate, sonst setzt die neue
    Quelle 1,5x auf 1x zurück) gehen mit. Das alte Video verstummt, bleibt aber
    mit Quelle gehalten, bis das neue spielt. Die Antwort des Sprungs meldet
    schon die Stelle des NEUEN Videos."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
tvpTc=true;
tvFilmPlayer('F1','Eins',0,META);
const A=_els['tvp-video']; spielen(A); A.currentTime=30; A.volume=0.25; A.muted=true;
await tvpBefehl('rate',{wert:1.5});
const sprung=await tvpBefehl('seek',{wert:1800});
const B=_els['tvp-video'];
const nach={bNeu:!!B&&B!==A, bSrc:B.src, bId:B.id, bKlasse:B.className, bAuto:B.autoplay,
  bInline:B._attr.playsinline, bVol:B.volume, bStumm:B.muted, bRate:B.playbackRate,
  bRateStd:B.defaultPlaybackRate, bSpielt:!B.paused, bImDokument:B.isConnected,
  hoert:Object.fromEntries(['error','click','play','pause','playing','loadedmetadata'].map(n=>[n,B.hoert(n)])),
  aStumm:A.paused, aImDokument:A.isConnected, aSrc:A.src, sprungPos:sprung.pos};
spielen(B); B.currentTime=12;
const st=await tvpBefehl('status');
aus({nach, spielt:{aSrc:A.src, bSrc:B.src, gehalten:tvpAbgeloest.length, aLoad:_log.includes('load:'+A.nr)},
     st:{pos:st.pos, zustand:st.zustand, key:st.key}});
""")
    n = e["nach"]
    assert n["bNeu"], "der Sprung muss ein neues Element bauen, nicht die Quelle des alten ersetzen"
    assert "id=F1" in n["bSrc"] and "tc=1" in n["bSrc"] and "start=1800" in n["bSrc"], n["bSrc"]
    assert (n["bId"], n["bKlasse"], n["bAuto"], n["bInline"]) == ("tvp-video", "tvp-video", True, ""), n
    assert n["bVol"] == 0.25 and n["bStumm"] is True, "Lautstärke und Stumm gehen mit"
    assert n["bRate"] == 1.5 and n["bRateStd"] == 1.5, "Tempo überlebt die neue Quelle nur mit defaultPlaybackRate"
    assert n["bSpielt"] and n["bImDokument"]
    h = n["hoert"]
    assert all(h[x] >= 1 for x in ("error", "click", "play", "pause")), h
    assert h["playing"] >= 2, "Markierung „hat gespielt“ + Freigabe des alten bei 'playing'"
    assert h["loadedmetadata"] == 0, "der Transcoder-Strom beginnt schon an der Stelle"
    assert n["aStumm"] and not n["aImDokument"], "das alte Video verstummt und verlässt das Dokument"
    assert "start=0" in n["aSrc"], "… behält aber seine Quelle, bis das neue spielt (Windows' Sitzung)"
    assert n["sprungPos"] == 1800, "die Antwort des Sprungs gehört zum NEUEN Video"
    assert e["spielt"] == {"aSrc": "", "bSrc": n["bSrc"], "gehalten": 0, "aLoad": True}, e["spielt"]
    assert e["st"] == {"pos": 1812, "zustand": "spielt", "key": "film:F1"}, e["st"]


def test_doppelsprung_leert_das_ungespielte_sofort(tmp_path):
    """T2: Zwei schnelle Sprünge. Das Zwischen-Element hat nie gespielt, hält
    also keine Sitzung — es wird sofort geleert (seine Verbindung zum Server
    zu). Das alte, das gespielt hat, bleibt bis zum 'playing' des dritten."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
tvpTc=true;
tvFilmPlayer('F1','Eins',0,META); const A=_els['tvp-video']; spielen(A);
await tvpBefehl('seek',{wert:1800}); const B=_els['tvp-video'];
await tvpBefehl('seek',{wert:2400}); const C=_els['tvp-video'];
const vorC={verschieden:A!==B&&B!==C&&A!==C, bSrc:B.src, bSteht:B.paused, bImDokument:B.isConnected,
  aSrc:A.src, cSrc:C.src, gehalten:tvpAbgeloest.length, offset:tvpTcOffset};
spielen(C);
aus({vorC, nachC:{aSrc:A.src, cSrc:C.src, gehalten:tvpAbgeloest.length}});
""")
    v = e["vorC"]
    assert v["verschieden"], "jeder Sprung ein eigenes Element"
    assert v["bSrc"] == "" and v["bSteht"] and not v["bImDokument"], "nie gespielt: sofort leeren"
    assert "start=0" in v["aSrc"], "das gespielte bleibt gehalten, bis ein Nachfolger spielt"
    assert "start=2400" in v["cSrc"] and v["gehalten"] == 1 and v["offset"] == 2400, v
    assert e["nachC"]["aSrc"] == "" and "start=2400" in e["nachC"]["cSrc"] and e["nachC"]["gehalten"] == 0


def test_selbstheilung_vor_den_metadaten_tauscht_ohne_doppelsprung(tmp_path):
    """T3a: Das direkte Abspielen sperrt sich, bevor die Metadaten kamen (der
    typische Fall: Format oder HTTP-Fehler). Der Transcoder übernimmt in einem
    NEUEN Element ab der Einstiegsstelle — ohne den liegengebliebenen
    loadedmetadata-Sprung, der auf dem Transcoder-Strom noch einmal auf die
    Einstiegsstelle gesprungen wäre. Das alte Element hat nie gespielt und
    wird sofort geleert."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
tvpTc=false;
tvFilmPlayer('F1','Eins',1200,META); const A=_els['tvp-video'];
const aMeta=A.hoert('loadedmetadata');
A.feuer('error');
const B=_els['tvp-video'];
aus({aMeta, bNeu:B!==A, tc:tvpTc, offset:tvpTcOffset, bSrc:B.src, bMeta:B.hoert('loadedmetadata'),
     aSrc:A.src, bSpielt:!B.paused, toasts, vlcStarts});
""")
    assert e["aMeta"] == 1, "Vorbedingung: das direkte Video springt nach den Metadaten auf die Stelle"
    assert e["bNeu"], "die Selbstheilung baut ein neues Element"
    assert e["tc"] is True and e["offset"] == 1200
    assert "tc=1" in e["bSrc"] and "start=1200" in e["bSrc"], e["bSrc"]
    assert e["bMeta"] == 0, "kein zweiter Sprung auf dem Transcoder-Strom"
    assert e["aSrc"] == "" and e["bSpielt"], "das nie gespielte direkte Video wird sofort geleert"
    assert len(e["toasts"]) == 1 and "Transcoder" in e["toasts"][0] and e["vlcStarts"] == [], e


def test_selbstheilung_mitten_im_film_und_vlc_an_der_aktuellen_stelle(tmp_path):
    """T3b: Beide Stufen der Kette mitten im Film. Das direkte Video bricht bei
    1500 ab — es hat gespielt und wird bis zum 'playing' des Transcoder-Videos
    gehalten. Scheitert danach auch der Transcoder (Stand 2500), startet der VLC
    an der ZULETZT gemeldeten Stelle, nicht am Einstieg (1200) und nicht beim
    Offset des ersten Tauschs (1500)."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
tvpTc=false;
tvFilmPlayer('F1','Eins',1200,META); const A=_els['tvp-video'];
spielen(A); A.feuer('loadedmetadata'); tvpPos=1500;
A.feuer('error');
const B=_els['tvp-video'];
const heil={bNeu:B!==A, bSrc:B.src, aSrc:A.src, gehalten:tvpAbgeloest.length};
spielen(B);
const nachSpiel={aSrc:A.src};
tvpPos=2500;
B.feuer('error');
aus({heil, nachSpiel, vlcStarts, offen:tvpOffen, naechster:tvpModusNaechster, gemerkt, toasts:toasts.length,
     video:!!_els['tvp-video'], bSrc:B.src});
""")
    h = e["heil"]
    assert h["bNeu"] and "tc=1" in h["bSrc"] and "start=1500" in h["bSrc"], h
    assert "id=F1" in h["aSrc"] and "tc=1" not in h["aSrc"] and h["gehalten"] == 1, \
        "das gespielte direkte Video hält Windows' Sitzung, bis der Transcoder spielt"
    assert e["nachSpiel"]["aSrc"] == ""
    assert e["vlcStarts"] == [["F1", 2500]], "der VLC übernimmt an der aktuellen Stelle"
    assert e["offen"] is False and e["naechster"] == {"id": "F1", "modus": "normal"}, e
    assert e["gemerkt"] == [["F1", 2500]] and e["toasts"] == 2
    assert e["video"] is False and e["bSrc"] == "", "das Browser-Video ist nach dem Rückfall geleert"


def test_fehler_des_abgeloesten_videos_loest_nichts_aus(tmp_path):
    """T4: Ein error des alten, schon ersetzten Videos (etwa weil der Server
    seinen Strom beendet, sobald das neue anfragt) darf weder einen Toast noch
    einen zweiten Tausch noch den VLC-Rückfall auslösen."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
tvpTc=true;
tvFilmPlayer('F1','Eins',0,META); const A=_els['tvp-video']; spielen(A);
await tvpBefehl('seek',{wert:1800}); const B=_els['tvp-video'];
const n=_videos.length;
A.feuer('error');
aus({neu:B!==A, toasts, vlcStarts, offen:tvpOffen, aktuell:_els['tvp-video']===B, neueVideos:_videos.length-n,
     bSrc:B.src});
""")
    assert e["neu"], "Vorbedingung: der Sprung hat getauscht"
    assert e["toasts"] == [] and e["vlcStarts"] == [], e
    assert e["offen"] is True and e["aktuell"] is True and e["neueVideos"] == 0
    assert "start=1800" in e["bSrc"]


def test_film_zu_raeumt_auch_getauschte(tmp_path):
    """T5: Esc nach einem Sprung, bevor das neue Video spielt: beide Elemente
    lösen ihre Quelle — sonst bliebe ein toter Eintrag in Windows' Overlay."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
tvpTc=true;
tvFilmPlayer('F1','Eins',0,META); const A=_els['tvp-video']; spielen(A);
await tvpBefehl('seek',{wert:1800}); const B=_els['tvp-video'];
const vorher={neu:B!==A, aSrc:A.src, bSrc:B.src};
tvpZu();
aus({vorher, aSrc:A.src, bSrc:B.src, gehalten:tvpAbgeloest.length, video:!!_els['tvp-video'], offen:tvpOffen});
""")
    v = e["vorher"]
    assert v["neu"] and "start=0" in v["aSrc"] and "start=1800" in v["bSrc"], v
    assert (e["aSrc"], e["bSrc"], e["gehalten"]) == ("", "", 0), e
    assert e["video"] is False and e["offen"] is False


def test_anlauf_gnade_fuer_das_getauschte_video(tmp_path):
    """Gegenprüfung (übersehen): Ein NEUES Element hat bis zur Quellenwahl ein
    leeres currentSrc — der Film-Takt las das als „aus" und schloss den Film,
    weil der Film vorher schon lief (tvpLief). Das Start-Element schützt die
    Anlauf-Gnade; das getauschte bekommt sie jetzt auch. Das echte Filmende
    wird danach weiter erkannt."""
    (e,) = _lauf(tmp_path, *_teile(tick_echt=True), r"""
tvpTc=true;
tvFilmPlayer('F1','Eins',0,META); const A=_els['tvp-video']; spielen(A);
await tvpTick();
const vor={lief:tvpLief, offen:tvpOffen};
await tvpBefehl('seek',{wert:1800}); const B=_els['tvp-video'];
const bVorWahl=B.currentSrc;
await tvpTick();                               // der 1-s-Takt kommt vor der Quellenwahl
const vorWahl={offen:tvpOffen, aktuell:_els['tvp-video']===B};
spielen(B); B.currentTime=5; await tvpTick();
const nachWahl={offen:tvpOffen, lief:tvpLief, pos:tvpPos};
B.ended=true; await tvpTick();                 // echtes Filmende
aus({neu:B!==A, vor, bVorWahl, vorWahl, nachWahl, ende:{offen:tvpOffen}});
""")
    assert e["neu"], "Vorbedingung: der Sprung hat getauscht"
    assert e["vor"] == {"lief": True, "offen": True}
    assert e["bVorWahl"] == "", "Vorbedingung der Attrappe: neues Element ohne currentSrc"
    assert e["vorWahl"] == {"offen": True, "aktuell": True}, "der Sprung darf den Film nicht schließen"
    assert e["nachWahl"] == {"offen": True, "lief": True, "pos": 1805}, e["nachWahl"]
    assert e["ende"] == {"offen": False}, "das Filmende wird weiter erkannt"


def test_gehaltenes_video_zaehlt_als_sitzung(tmp_path):
    """Gegenprüfung (übersehen): Verweigert der Browser play() für das neue
    Element, hält das alte, gespielte Video Windows' Sitzung weiter — die
    Medientaste kommt über Windows. Der keydown-Rückfall darf dann NICHT
    zusätzlich wirken (sonst die Doppelwirkung vom 24.09.). Ein gehaltenes
    Video, das nie gespielt hat, zählt nicht."""
    q = _pc()
    (e,) = _lauf(tmp_path, *_teile("filmTasten", "medienTasteHatSitzung"), r"""
var vlcSmtc=false; function vlcAktiv(){return false;}
_els['pl-el']=fakeMedia({id:'pl-el'});             // Musik ohne Quelle: keine Musik-Sitzung
tvpTc=true;
tvFilmPlayer('F1','Eins',0,META); const A=_els['tvp-video']; spielen(A);
const spielt=medienTasteHatSitzung();
_playScheitert=true;
await tvpBefehl('seek',{wert:1800}); const B=_els['tvp-video'];
const gehalten={sitzung:medienTasteHatSitzung(), bSteht:B.paused, neu:B!==A, aGehalten:tvpAbgeloest.includes(A)};
_playScheitert=false; spielen(B);
const nachher={sitzung:medienTasteHatSitzung(), aSrc:A.src};
tvpZu(); tvpModus='browser'; tvpTimer=1;             // kein echter 1-s-Takt in der Attrappe
tvFilmPlayer('F2','Zwei',0,META); tvFilmPlayer('F3','Drei',0,META);   // Folgenwechsel, nichts hat gespielt
const nieGespielt={sitzung:medienTasteHatSitzung(), gehalten:tvpAbgeloest.length};
aus({spielt, gehalten, nachher, nieGespielt});
""")
    assert e["spielt"] is True
    g = e["gehalten"]
    assert g["neu"] and g["bSteht"] and g["aGehalten"], g
    assert g["sitzung"] is True, "das gehaltene, gespielte Video hält die Sitzung: kein keydown-Rückfall"
    assert e["nachher"] == {"sitzung": True, "aSrc": ""}, e["nachher"]
    assert e["nieGespielt"] == {"sitzung": False, "gehalten": 1}, e["nieGespielt"]
    # …und der keydown-Rückfall fragt genau diese Funktion.
    i = q.index("document.addEventListener('keydown',e=>{")
    assert "medienTasteHatSitzung()" in q[i:i + 6000], "der keydown-Rückfall muss die Sitzung prüfen"


# ------------------------------------------------------------ Quelltext-Wächter

_FILM_FUNKTION = re.compile(r"^(?:async )?function (tvp\w*|tvFilmPlayer)\(", re.M)
# Die einzigen Stellen, an denen eine Film-Funktion eine Quelle zuweisen darf:
# der Tausch selbst (neues Element) und das Standbild-Bild der Hülle.
_ERLAUBT = {("tvpVideoTauschen", "neu"), ("tvpIdleTick", "bg")}


def test_waechter_keine_neue_quelle_im_film_video():
    """Auto-Discovery über ALLE Film-Funktionen (tvp*, tvFilmPlayer): keine
    Funktion setzt eine neue Quelle auf ein bestehendes Element — jede neue
    Quelle geht durch tvpVideoTauschen. Eine künftige tvp-Funktion ist
    automatisch mit geprüft."""
    q = _pc()
    namen = sorted(set(_FILM_FUNKTION.findall(q)))
    pflicht = {"tvpBefehl", "tvFilmPlayer", "tvpVideoVerdrahten", "tvpVideoTauschen", "tvpZu", "tvpIdleTick"}
    assert pflicht <= set(namen), f"Wächter blind: {sorted(pflicht - set(namen))} nicht gefunden"
    funde, erlaubt_gesehen = [], set()
    for name in namen:
        rumpf = _js_funktion(q, name)
        for m in re.finditer(r"([\w$]+)\s*\.\s*src\s*=(?!=)", rumpf):
            if (name, m.group(1)) in _ERLAUBT:
                erlaubt_gesehen.add((name, m.group(1)))
            else:
                funde.append(f"{name}: {m.group(0)}")
        for m in re.finditer(r"setAttribute\(\s*['\"]src['\"]", rumpf):
            funde.append(f"{name}: {m.group(0)}")
    assert not funde, "neue Quelle im bestehenden Film-Video (Windows verliert die Sitzung): " + "; ".join(funde)
    assert erlaubt_gesehen == _ERLAUBT, f"Ausnahmen veraltet: {sorted(_ERLAUBT - erlaubt_gesehen)}"
