# -*- coding: utf-8 -*-
"""Nächste Folge: Tempo und Stumm bleiben (JB 24.09.2026: „Behalten").

Befund (Analyse transcoder.md, „Tempo und Stumm"): Beim Folgenwechsel per
⏭/⏮ lief die neue Folge wieder in normalem Tempo und mit Ton, das Tempo-Menü
zeigte aber noch das alte Tempo als aktiv — tvpRateWert ist global und wurde
weder übertragen noch zurückgesetzt. JB hat entschieden: Tempo und Stumm
bleiben beim Folgenwechsel derselben Film-Sitzung erhalten. Ein ganz neuer
Film-Start (Bibliothek, Esc und neu) beginnt wie bisher bei 1x mit Ton. In
jedem Fall zeigt das Tempo-Menü das Tempo, das wirklich läuft.

Ausgeführt wird die ECHTE Kette der Seite (tvpWechselStarten → filmePlay →
filmePlayVlc → tvFilmPlayer, dazu tvpRate/tvpPanel für das Menü) mit deno.
Die Attrappe modelliert die Unterschiede, um die es geht (Lehrbuch: „Attrappe
muss den Unterschied modellieren"):

* Jedes Laden eines <video> setzt playbackRate auf defaultPlaybackRate zurück
  (Lade-Algorithmus der HTML-Spezifikation). Wer nur playbackRate setzt,
  verliert das Tempo beim nächsten Laden.
* Der VLC ist EIN Spieler für Musik und Film; die Film-Route am Server setzt
  kein Tempo. Ob libvlc das Tempo über einen Medienwechsel hält, ist hier
  nicht gemessen — darum laufen die VLC-Fälle mit beiden Modellen (Start
  behält das Tempo des Vorgängers / Start setzt es auf 1).

Nicht hier gemessen: das echte Edge-<video> und der echte VLC (Live-Probe
braucht Renés Jellyfin).
"""
import os
import sys

import pytest

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

from test_film_transcoder_tausch import ATTRAPPE, TICK_STUB  # noqa: E402
from test_medientasten_verhalten import (  # noqa: E402
    _js_funktion,
    _js_zeile,
    _lauf,
    _modul_js,
    _pc,
)

# Die Transcoder-Attrappe ersetzt den VLC-Start durch einen Stub; hier läuft
# der ECHTE filmePlayVlc (Reihenfolge: erst Start am Server, dann Tempo).
_VLC_STUB = "function filmePlayVlc(id,pos,mm){vlcStarts.push([id,pos]);}\n"

UMFELD = r"""
globalThis.setInterval=()=>1;                         // kein echter 1-s-Takt in der Attrappe
var tvpWechselGen=0;
async function huelleMelden(){}
const seq=[];                                         // was am Server/VLC ankam, in Reihenfolge
const vlc={rate:1, key:'', playSetztTempo:false};    // der EINE VLC (Musik + Film)
const METAS={};
function folge(id,browser){METAS[id]={id, titel:'Folge '+id, typ:'folge', serie_id:'S', laufzeit_min:40,
  video_codec:browser?'h264':'hevc', audio_codec:browser?'aac':'ac3'};}
globalThis.fetch=async(url,o)=>{
  if(url.startsWith('/api/filme/detail?id=')){
    const id=decodeURIComponent(url.slice('/api/filme/detail?id='.length));
    return {json:async()=>METAS[id]||{fehler:'unbekannt'}};
  }
  if(url==='/api/filme/play'){                        // Film-Route: startet im VLC, setzt KEIN Tempo
    const b=JSON.parse(o.body); vlc.key='film:'+b.id; if(vlc.playSetztTempo)vlc.rate=1;
    seq.push(['start',b.id]);
    return {json:async()=>({zustand:'spielt', key:vlc.key})};
  }
  return {json:async()=>({})};
};
vlcBefehl=async(cmd,d)=>{
  seq.push([cmd,d&&d.wert]);
  if(cmd==='rate')vlc.rate=d.wert;
  if(cmd==='stop')vlc.key='';
  return {zustand:vlc.key?'spielt':'aus', key:vlc.key, rate:vlc.rate, ton:[], sub:[], verfuegbar:true};
};
_els['tvp-panel']={style:{display:'none'}, dataset:{}, innerHTML:''};
function menueTempo(){                                // Tempo-Menü öffnen, markierten Knopf lesen
  const p=_els['tvp-panel']; p.style.display='none'; p.dataset.art='';
  tvpPanel('tempo');
  const an=[...p.innerHTML.matchAll(/class="tvpp-knopf an" onclick="tvpRate\(([\d.]+)\)"/g)].map(m=>+m[1]);
  p.style.display='none';
  return an.length===1?an[0]:an;
}
async function ruhe(){for(let i=0;i<40;i++)await new Promise(r=>setTimeout(r,0));}
"""


def _teile(szenario):
    q = _pc()
    assert _VLC_STUB in ATTRAPPE, "Attrappe verändert: der VLC-Start-Stub ist nicht mehr da"
    namen = ["tvpDirektSrc", "tvpBefehl", "tvpAbgeloestFreigeben", "tvpVideoVerdrahten",
             "tvpVideoTauschen", "tvFilmPlayer", "tvpZu", "filmeBrowserKann", "filmePlay",
             "filmePlayVlc", "tvpWechselStarten", "tvpPanel", "tvpRate"]
    return ([_modul_js(), "const medienS=medienSitzung(()=>null);",
             _js_zeile(q, "let tvpAbgeloest"), _js_zeile(q, "let tvpGesehenGemeldet"),
             _js_zeile(q, "let tvpRateWert"), ATTRAPPE.replace(_VLC_STUB, ""), TICK_STUB, UMFELD]
            + [_js_funktion(q, n) for n in namen] + [szenario])


def test_folgenwechsel_im_browser_behaelt_tempo_und_stumm(tmp_path):
    """⏭ im Browser-Player: die neue Folge läuft im gewählten Tempo und bleibt
    stumm. Das Tempo steht auch in defaultPlaybackRate — sonst setzt das
    nächste Laden die Folge wieder auf 1x. Das Menü zeigt das echte Tempo,
    auch über zwei Wechsel hinweg."""
    (e,) = _lauf(tmp_path, *_teile(r"""
folge('F1',true); folge('F2',true); folge('F3',true);
await filmePlay('F1',0); const A=_els['tvp-video']; spielen(A);
await tvpRate(1.5); A.muted=true;                     // Tempo-Menü + Taste M
const vorher={rate:A.playbackRate, menue:menueTempo()};
tvpWechselStarten('F2',0,'normal'); await ruhe();
const B=_els['tvp-video'];
const zweite={neu:B!==A, id:tvpIdAkt, rate:B.playbackRate, rateStd:B.defaultPlaybackRate, stumm:B.muted,
  menue:menueTempo()};
B.load();                                             // ein späteres Laden (Lade-Algorithmus)
const nachLaden=B.playbackRate;
spielen(B);
tvpWechselStarten('F3',0,'normal'); await ruhe(); const C=_els['tvp-video'];
aus({vorher, zweite, nachLaden, dritte:{neu:C!==B, id:tvpIdAkt, rate:C.playbackRate, stumm:C.muted,
  menue:menueTempo()}});
"""))
    assert e["vorher"] == {"rate": 1.5, "menue": 1.5}, f"Vorbedingung: {e['vorher']}"
    z = e["zweite"]
    assert z["neu"] and z["id"] == "F2", f"Vorbedingung: der Wechsel baut ein neues Video: {z}"
    assert z["rate"] == 1.5, f"die nächste Folge verliert das Tempo: {z}"
    assert z["rateStd"] == 1.5, f"ohne defaultPlaybackRate setzt das nächste Laden auf 1x zurück: {z}"
    assert z["stumm"] is True, f"die nächste Folge verliert Stumm: {z}"
    assert z["menue"] == 1.5, f"das Tempo-Menü zeigt nicht das echte Tempo: {z}"
    assert e["nachLaden"] == 1.5, "nach einem Laden läuft die Folge wieder in 1x"
    assert e["dritte"] == {"neu": True, "id": "F3", "rate": 1.5, "stumm": True, "menue": 1.5}, e["dritte"]


def test_neuer_film_aus_der_bibliothek_startet_normal(tmp_path):
    """Esc und ein neuer Film aus der Bibliothek: keine Folge DIESER Sitzung —
    er beginnt wie bisher bei 1x mit Ton, und das Menü zeigt 1x (vorher
    stand dort noch das Tempo des vorigen Films)."""
    (e,) = _lauf(tmp_path, *_teile(r"""
folge('F1',true); folge('F9',true);
await filmePlay('F1',0); const A=_els['tvp-video']; spielen(A);
await tvpRate(1.5); A.muted=true;
tvpZu();                                              // Esc: Film zu
await filmePlay('F9',0); const D=_els['tvp-video'];
aus({neu:!!D&&D!==A, offen:tvpOffen, rate:D.playbackRate, rateStd:D.defaultPlaybackRate, stumm:D.muted,
  menue:menueTempo()});
"""))
    assert e["neu"] and e["offen"], f"Vorbedingung: der neue Film läuft im Browser: {e}"
    assert (e["rate"], e["rateStd"], e["stumm"]) == (1, 1, False), f"ein neuer Film beginnt bei 1x mit Ton: {e}"
    assert e["menue"] == 1, f"das Tempo-Menü zeigt noch das Tempo des vorigen Films: {e}"


@pytest.mark.parametrize("play_setzt_tempo", [False, True],
                         ids=["vlc-behaelt-tempo", "vlc-start-setzt-1x"])
def test_folgenwechsel_mit_vlc_uebertraegt_das_tempo(tmp_path, play_setzt_tempo):
    """In der Hülle wechselt eine Serie zwischen Browser und VLC, je nach Codec
    der Folge. Das Tempo geht in jede Richtung mit — im VLC per Tempo-Befehl
    NACH dem Start (vorher gesendet, setzte ein Start mit 1x es zurück). Ein
    neuer Film aus der Bibliothek im VLC läuft bei 1x, auch wenn der VLC
    vorher schneller spielte (Musik mit 1,25x), und das Menü zeigt 1x."""
    szenario = r"""
vlc.playSetztTempo=__PLAY_SETZT__; window.pywebview={};   // Hülle: was der Browser nicht kann, spielt der VLC
folge('F1',true); folge('F2',false); folge('F3',false); folge('F4',true); folge('F5',false);
await filmePlay('F1',0); const A=_els['tvp-video']; spielen(A);
await tvpRate(1.5); A.muted=true;
seq.length=0;
tvpWechselStarten('F2',0,'normal'); await ruhe();                         // Browser -> VLC
const inVlc={modus:tvpModus, id:tvpIdAkt, vlcRate:vlc.rate, menue:menueTempo(), seq:seq.slice()};
seq.length=0;
tvpWechselStarten('F3',0,'normal'); await ruhe();                         // VLC -> VLC
const vlcZuVlc={modus:tvpModus, id:tvpIdAkt, vlcRate:vlc.rate, menue:menueTempo(), seq:seq.slice()};
tvpWechselStarten('F4',0,'normal'); await ruhe(); const D=_els['tvp-video'];   // VLC -> Browser
const zurueck={modus:tvpModus, id:tvpIdAkt, rate:D&&D.playbackRate, rateStd:D&&D.defaultPlaybackRate,
  stumm:D&&D.muted, menue:menueTempo()};
tvpZu(); vlc.rate=1.25;                                                    // Esc; danach spielte die Musik mit 1,25x
await filmePlay('F5',0); await ruhe();                                     // filmePlay wartet den VLC-Start nicht ab
aus({inVlc, vlcZuVlc, zurueck, bibliothek:{modus:tvpModus, id:tvpIdAkt, vlcRate:vlc.rate, menue:menueTempo()}});
""".replace("__PLAY_SETZT__", "true" if play_setzt_tempo else "false")
    (e,) = _lauf(tmp_path, *_teile(szenario))
    i = e["inVlc"]
    assert (i["modus"], i["id"]) == ("vlc", "F2"), f"Vorbedingung: F2 läuft im VLC: {i}"
    assert ["start", "F2"] in i["seq"], i
    assert i["vlcRate"] == 1.5, f"Browser -> VLC: die Folge verliert das Tempo: {i}"
    assert i["menue"] == 1.5, i
    v = e["vlcZuVlc"]
    assert (v["modus"], v["id"]) == ("vlc", "F3"), f"Vorbedingung: {v}"
    assert v["vlcRate"] == 1.5 and v["menue"] == 1.5, f"VLC -> VLC: Tempo muss nach dem Start gesetzt sein: {v}"
    z = e["zurueck"]
    assert (z["modus"], z["id"]) == ("browser", "F4"), f"Vorbedingung: {z}"
    assert z["rate"] == 1.5 and z["rateStd"] == 1.5 and z["menue"] == 1.5, f"VLC -> Browser: {z}"
    assert z["stumm"] is False, \
        "der VLC kennt kein Stumm (Taste M wirkt dort nicht) — was in der VLC-Folge hörbar war, bleibt hörbar"
    b = e["bibliothek"]
    assert (b["modus"], b["id"]) == ("vlc", "F5"), f"Vorbedingung: {b}"
    assert b["vlcRate"] == 1 and b["menue"] == 1, f"ein neuer Film im VLC beginnt bei 1x, das Menü zeigt 1x: {b}"


def test_menue_zeigt_nach_dem_vlc_rueckfall_das_echte_tempo(tmp_path):
    """Selbstheilung bis zum VLC (Browser sperrt sich, Transcoder auch): der
    VLC-Rückfall ist ein neuer Start im VLC. Welches Tempo er nimmt, legt
    dieser Test nicht fest — nur, dass das Menü genau das zeigt."""
    (e,) = _lauf(tmp_path, *_teile(r"""
folge('F1',true);
await filmePlay('F1',0); const A=_els['tvp-video']; spielen(A);
await tvpRate(1.5);
A.feuer('error'); const B=_els['tvp-video'];        // direkt -> Transcoder (Tempo geht mit)
const tc={neu:B!==A, rate:B.playbackRate};
spielen(B); B.feuer('error'); await ruhe();           // Transcoder -> VLC
aus({tc, modus:tvpModus, offen:tvpOffen, id:tvpIdAkt, vlcRate:vlc.rate, menue:menueTempo()});
"""))
    assert e["tc"] == {"neu": True, "rate": 1.5}, f"Vorbedingung (Runde 1): {e['tc']}"
    assert (e["modus"], e["offen"], e["id"]) == ("vlc", True, "F1"), f"Vorbedingung: der VLC übernimmt: {e}"
    assert e["menue"] == e["vlcRate"], f"das Tempo-Menü zeigt nicht das Tempo des VLC: {e}"
