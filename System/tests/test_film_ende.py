# -*- coding: utf-8 -*-
"""Folgen- und Filmende: Stelle und „gesehen" melden (Analyse folgenende.md, 24.09.2026).

Befund: Die Oberfläche schickte das Feld „gesehen" nirgends mit. Ein Browser-Film
endete still (tvpZu merkte nur die Stelle kurz vor dem Ende, KEIN Netzaufruf);
im VLC wurde das Ende gar nicht erkannt — libvlc meldet am Ende 'ende' und bleibt
dort stehen, der Film-Takt prüfte nur 'aus', und die Fernbedienung blieb mit
Lade-Spinner offen. Die Folgenliste zeigte danach ⏸ statt ✓, „▶ Weiterschauen"
wählte die fertige Folge, der Film blieb in „Weiterschauen".

JB-Entscheidung 24.09.2026: „gesehen" ab 90 % der Dauer — auch Beenden per Esc
oder ⏭ im Abspann (dieselbe Grenze wie Jellyfin und tvpLandePos). Sleep-Timer:
„nein, nur musik, aber wenn der film zu ende ist, keinen weiteren starten".

Ausgeführt wird das ECHTE JavaScript der Seite mit deno (Hilfen aus
test_medientasten_verhalten.py): der Film-Takt tvpTick samt Ende-Weg, tvpZu,
filmStopp, der Folgenwechsel und die Meldestelle. Die Attrappe modelliert die
Unterschiede, um die es geht (Lehrbuch: „Attrappe muss den Unterschied
modellieren"): der Browser meldet am Ende 'aus' ohne Schlüssel, libvlc 'ende'
MIT dem Film-Schlüssel und Stelle 0; übernimmt die Musik den einen VLC, gehört
der Status (Schlüssel, Stelle) ihr. Die Server-Hälfte (Katalog-Spiegel, VLC-
Stopp nur für den eigenen Titel) läuft mit den Jellyfin- und libvlc-Attrappen.

Nicht hier gemessen: ob Renés Jellyfin „gesehen" wirklich setzt (live erst,
wenn der Zugang wieder geht; Stand 24.09. HTTP 401 beim Katalog-Abruf), und ob
libvlc am Ende eines Netz-Stroms wirklich in 'ende' stehen bleibt (gestützt
durch zwei Messungen im Code, medien_smtc.py und vlcTick).
"""
import os
import re
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import test_medien_smtc  # noqa: E402  (nachgebautes libvlc für die Server-Hälfte)
from test_filme import FAKE_ITEMS, JellyfinAttrappe, filme  # noqa: E402
from test_medientasten_verhalten import (  # noqa: E402
    _js_funktion,
    _js_zeile,
    _lauf,
    _pc,
)

vlc_attrappe = test_medien_smtc.vlc_attrappe          # Fixture

# Die Globalen der Seite, wörtlich (so zählt, was die Seite wirklich deklariert).
ZEILEN = ("let tvpTimer=", "let tvpMeta=", "let tvpModus=", "let tvpTc=", "let tvpMedienGen",
          "let sleepTimer=", "let tvTab=", "let tvHeroId=", "let tvInfoStapel=", "let tvInfoDaten=",
          "let vlcPosLetzte=", "let plGeraet=")
# In dieser Runde neu: fehlen sie (Rot-Lauf am alten Stand), bleiben sie weg —
# dann läuft der alte Ende-Weg, und die Tests scheitern am VERHALTEN.
NEU_ZEILEN = ("let tvpGesehenGemeldet",)
NEU = ("tvpFilmEnde", "tvpMeldeDauer", "filmFortschrittMelden", "filmGemeldetAnwenden",
       "filmLokalNachziehen", "nachFilmEnde", "sleepHaeltAn")
NAMEN = ("tvpTick", "tvpZu", "tvpFolgePosMerken", "medienNachFilm", "tvpLandePos", "tvSerienPlay",
         "filmLaeuft", "filmStopp", "tvpZielAusfuehren", "tvpWechselStarten", "tvpZurueckZiel",
         "tvpWeiterZiel", "tvpBasis", "tvpFolgenHolen", "tvpFolge", "tvpZurueck", "sleepSetzen",
         "sleepAusloesen", "sleepLabel", "tvInfo") + NEU

STUBS = r"""
const _timer=[];                                        // Sleep-Minuten: steuerbare Uhr statt echter Wartezeit
globalThis.setTimeout=(f,ms)=>{_timer.push({f,ms}); return _timer.length;};
globalThis.clearTimeout=id=>{if(id&&_timer[id-1])_timer[id-1].f=()=>{};};
function timerLaeuftAb(){_timer.splice(0).forEach(t=>t.f());}
const netz=[], vlc=[], starts=[], zeichnungen=[], infos=[], toasts=[];
let antwort=null, ANTWORTEN=[];
globalThis.fetch=(u,o)=>{u=String(u); netz.push([u, o&&o.body?JSON.parse(o.body):null]);
  const a=ANTWORTEN.find(([t])=>u.startsWith(t));
  return Promise.resolve({json:async()=>(a?a[1]:{ok:true})});};
// Der Takt fragt den Motor; alles andere, was an ihn geht, wird mitgeschrieben.
function tvpBefehl(c,d){if(c==='status')return Promise.resolve(antwort); vlc.push('tvp:'+c); return Promise.resolve({});}
function vlcBefehl(c,d){vlc.push('vlc:'+c+(d&&d.nur_key?'@'+d.nur_key:''));
  if(c==='play'||c==='toggle')starts.push('vlc:'+c); return Promise.resolve({});}
function vlcAktiv(){return plGeraet==='vlc';}
// Alles, womit nach einem Filmende etwas LOSLAUFEN könnte (Folge, Musik):
function filmePlay(id,pos){starts.push('film:'+id+'@'+(pos||0));}
function playerAdvance(){starts.push('musik:weiter');} function renderPlayerMedia(){starts.push('musik:titel');}
function playerPlay(){starts.push('musik:play');} function naechstesAusBibliothek(){starts.push('musik:bib');}
function tvpIdleTick(){} function tvpMedienZustand(){} function ico(){return '';} function zeit(s){return String(s);}
function tvpLadeZeigen(){} function tvpAbgeloestFreigeben(){} function xfPruefen(){}
function bild(){const d=tvInfoDaten&&tvInfoDaten.d; if(!d)return '-';
  return d.typ==='serie'?tvInfoDaten.eps.map(x=>x.id+':'+x.position_s+(x.gesehen?'✓':'')).join(',')
                        :'film:'+d.position_s+(d.gesehen?'✓':'');}
function tvInfoMalen(){zeichnungen.push(bild());}
function tvMalen(){zeichnungen.push('tv');}
function toast(t){toasts.push(t);}
let _vlcPos=0; function vlcPosGeschaetzt(){return _vlcPos;}
const medienS={freigeben(){}, leeren(){}, info(){}, aktionen(){}, zustand(){}};
function medienTastenAnmelden(){} function aktKey(){return 'a';} function libFind(k){return {id:k};}
function medienInfoSetzen(){} function medienZustand(){}
function tvKey(){} function tvProfil(){return 'standard';} function esc(s){return String(s);}
document.body={appendChild(el){el.parentNode=this;}};
_els['tv-info']={style:{}, innerHTML:'', parentNode:null};
_els['pl-el']=fakeMedia({id:'pl-el', paused:true});     // die Musik darunter (pausiert)
const E=(id,pos,gesehen)=>({id, staffel:1, folge:+id.slice(1), laufzeit_min:40, position_s:pos, gesehen:!!gesehen});
function folgen(){return [E('e1',0,true),E('e2',0,true),E('e3',1200),E('e4',0),E('e5',0)];}
const F=(id,pos)=>({id, typ:'film', titel:id, laufzeit_min:100, position_s:pos, gesehen:false});
function lage(o){
  o=o||{};
  tvpOffen=o.offen??true; tvpIdAkt=o.id??'e3'; tvpModus=o.modus||'browser'; tvpLief=o.lief??true;
  tvpTicks=o.ticks??5; tvpPos=o.pos??0; tvpDauer=o.dauer??0; tvpTimer=1; tvpWechsel=o.wechsel??null;
  tvpMeta=o.meta??{typ:'folge', serie_id:'s9', laufzeit_min:40};
  if(typeof tvpGesehenGemeldet!=='undefined'){tvpGesehenGemeldet=''; filmGemeldet={};}
  tvInfoOffen=o.info??true; tvInfoDaten=('daten' in o)?o.daten:{d:{id:'s9',typ:'serie'}, eps:folgen()};
  tvpFolgenCache={sid:'s9', eps:folgen()};
  tvFilmReihen=o.reihen??null; tvHeroDaten=o.hero??null;
  vlcKeyLetzter=o.key??''; vlcSpielt=!!o.vlcSpielt; _vlcPos=0; plGeraet=o.geraet||'browser';
  netz.length=0; vlc.length=0; starts.length=0; zeichnungen.length=0; infos.length=0; toasts.length=0;
  _log.length=0;
}
const koerper=()=>netz.filter(n=>n[0]==='/api/filme/fortschritt').map(n=>n[1]);
const folge=(l,id)=>{const e=(l||[]).find(x=>x.id===id); return e?[e.position_s, e.gesehen]:null;};
async function takte(n){for(let i=0;i<n;i++)await tvpTick();}
async function ruhe(){for(let i=0;i<50;i++)await null;}   // Mikro-Aufgaben abarbeiten (fetch-Attrappen)
"""


def _teile():
    q = _pc()
    zeilen = [_js_zeile(q, z) for z in ZEILEN]
    zeilen += [_js_zeile(q, z) for z in NEU_ZEILEN if re.search(r"^" + re.escape(z), q, re.M)]
    namen = [n for n in NAMEN if n not in NEU or re.search(r"^(?:async )?function " + n + r"\(", q, re.M)]
    return zeilen + [STUBS] + [_js_funktion(q, n) for n in namen]


def test_bausteine_gibt_es():
    """Die EINE Meldestelle und der Ende-Weg stehen als Top-Level-Bausteine in
    der Seite (sonst wären sie nicht mit dem echten Code prüfbar), und alle drei
    Aufrufer gehen durch sie: Takt-Ende, Esc (filmStopp), Folgenwechsel."""
    q = _pc()
    for n in NEU:
        _js_funktion(q, n)
    _js_zeile(q, "let tvpGesehenGemeldet")
    assert "tvpFilmEnde(" in _js_funktion(q, "tvpTick")
    for aufrufer in ("tvpFilmEnde", "filmStopp", "tvpZielAusfuehren"):
        rumpf = _js_funktion(q, aufrufer)
        assert "filmFortschrittMelden(" in rumpf, f"{aufrufer} meldet nicht über die Meldestelle"
        assert "/api/filme/fortschritt" not in rumpf, f"{aufrufer} meldet an der Meldestelle vorbei"
    assert "/api/filme/fortschritt" in _js_funktion(q, "filmFortschrittMelden")


# ------------------------------------------------------------- Takt: das Ende

def test_browser_ende_meldet_gesehen_und_zieht_die_folgen_nach(tmp_path):
    """Browser-Modus: am Ende liefert das <video> 'aus' ohne Schlüssel. Vorher
    schloss der Takt nur (kein Netzaufruf) und merkte die Stelle kurz vor dem
    Ende — die Kachel zeigte ⏸, „▶ Weiterschauen" wählte die fertige Folge.
    Jetzt: genau EINE Meldung mit gesehen, lokal gesehen + Stelle 0 (wie
    Jellyfin), die offene Info wird neu gezeichnet."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
lage({pos:2395, dauer:2400});
antwort={zustand:'aus', key:'', pos:2400, dauer:2400, verfuegbar:true};
await takte(2);                                           // der zweite Takt trifft einen geschlossenen Player
const r={offen:tvpOffen, koerper:koerper(), vlc:[...vlc], info:folge(tvInfoDaten.eps,'e3'),
         cache:folge(tvpFolgenCache.eps,'e3'), bilder:[...zeichnungen], starts:[...starts]};
tvSerienPlay(); r.weiter=starts.at(-1);
aus(r);
""")
    assert e["offen"] is False
    assert e["koerper"] == [{"id": "e3", "position_s": 2400, "gesehen": True}], e["koerper"]
    assert e["vlc"] == [], "Browser-Film: nichts an den Geräte-VLC (der gehört der Musik)"
    assert e["info"] == [0, True] and e["cache"] == [0, True], (e["info"], e["cache"])
    assert e["bilder"] == ["e1:0✓,e2:0✓,e3:0✓,e4:0,e5:0"], e["bilder"]
    assert e["starts"] == [], "nach dem Ende startet nichts von selbst"
    assert e["weiter"] == "film:e4@0", "▶ Weiterschauen wählt die NÄCHSTE Folge"


def test_vlc_ende_wird_erkannt_gemeldet_und_freigegeben(tmp_path):
    """libvlc meldet am Ende 'ende' (nicht 'aus') und behält den Schlüssel
    'film:<id>' samt Stelle 0. Vorher fiel der Takt durch: Spinner, offene
    Fernbedienung, keine Meldung. Jetzt schließt er, meldet mit der letzten
    bekannten Stelle, und der VLC wird freigegeben — nur für DIESEN Titel
    (nur_key); die Seite vergisst den Schlüssel wie bei Esc. Weitere Takte
    melden nichts mehr."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
lage({modus:'vlc', pos:2395, dauer:2400});
antwort={zustand:'ende', key:'film:e3', pos:0, dauer:0, verfuegbar:true};
await tvpTick();
const r={offen:tvpOffen, koerper:koerper(), vlc:[...vlc], info:folge(tvInfoDaten.eps,'e3'), key:vlcKeyLetzter};
await takte(2);
r.danach=koerper().length;
aus(r);
""")
    assert e["offen"] is False, "das VLC-Ende schließt die Fernbedienung"
    assert e["koerper"] == [{"id": "e3", "position_s": 2395, "gesehen": True}], e["koerper"]
    assert e["vlc"] == ["vlc:stop@film:e3"] and e["key"] == "", e
    assert e["info"] == [0, True]
    assert e["danach"] == 1, "weitere Takte melden nichts"


def test_abbruch_mittendrin_meldet_nur_die_stelle(tmp_path):
    """Strom reißt bei 50 % ab (der Browser meldet ebenfalls 'aus'): die Stelle
    wird gemeldet, „gesehen" nicht; lokal bleibt die Folge angefangen."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
lage({pos:1100, dauer:2400});
antwort={zustand:'aus', key:'', pos:1200.4, dauer:2400, verfuegbar:true};
await tvpTick();
aus({koerper:koerper(), info:folge(tvInfoDaten.eps,'e3')});
""")
    assert e["koerper"] == [{"id": "e3", "position_s": 1200}], e["koerper"]
    assert e["info"] == [1200, False]


def test_kein_melden_ohne_eigenes_ende(tmp_path):
    """Kein „gesehen" und keine falsche Stelle in vier Fällen:
    (a) ein Folgenwechsel lädt — das 'aus' der alten Folge schließt nicht;
    (b) der Film lief nie an — nichts zu melden;
    (c) Live-Sendung (keine Kennung) — 'aus' schließt wie bisher, ohne Meldung
        und ohne Stopp; ein 'ende' mit Live-Schlüssel schließt NICHT (wie bisher:
        dass Live am Stromende von selbst schließt, ist nicht bestätigt);
    (d) die Musik hat den EINEN VLC übernommen — der Status gehört ihr: die
        Film-Stelle zählt, die der Musik nicht (auch nicht, wenn sie größer ist),
        kein „gesehen" (auch nicht bei 95 %: das war kein Ende), und kein Stopp
        (der träfe die Musik)."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
const r={};
lage({pos:2395, dauer:2400, wechsel:{gen:2, id:'e4'}});
antwort={zustand:'aus', key:'', pos:2400, dauer:2400}; await tvpTick();
r.wechsel={offen:tvpOffen, koerper:koerper()};
lage({lief:false, ticks:9, pos:0});
antwort={zustand:'aus', key:'', pos:0, dauer:0}; await tvpTick();
r.nieAn={offen:tvpOffen, koerper:koerper()};
lage({id:'', modus:'vlc', meta:{titel:'ARD'}});
antwort={zustand:'ende', key:'live:ARD', pos:0, dauer:0}; await tvpTick();
const liveEnde=tvpOffen;
antwort={zustand:'aus', key:'live:ARD', pos:0, dauer:0}; await tvpTick();
r.live={liveEnde, offen:tvpOffen, koerper:koerper(), vlc:[...vlc]};
lage({modus:'vlc', pos:100, dauer:2400});
antwort={zustand:'spielt', key:'abc|mp4', pos:2300, dauer:2500}; await tvpTick();
r.musik={offen:tvpOffen, koerper:koerper(), vlc:[...vlc]};
lage({modus:'vlc', pos:2300, dauer:2400});
antwort={zustand:'aus', key:'abc|mp3', pos:50, dauer:200}; await tvpTick();
r.musikSpaet={offen:tvpOffen, koerper:koerper(), vlc:[...vlc]};
aus(r);
""")
    assert e["wechsel"] == {"offen": True, "koerper": []}, e["wechsel"]
    assert e["nieAn"] == {"offen": False, "koerper": []}, e["nieAn"]
    assert e["live"] == {"liveEnde": True, "offen": False, "koerper": [], "vlc": []}, e["live"]
    assert e["musik"] == {"offen": False, "koerper": [{"id": "e3", "position_s": 100}], "vlc": []}, e["musik"]
    assert e["musikSpaet"] == {"offen": False, "koerper": [{"id": "e3", "position_s": 2300}], "vlc": []}, \
        e["musikSpaet"]


def test_nahe_am_ende_fortgesetzt_meldet_trotzdem(tmp_path):
    """Gegenprüfung (übersehen): Wird eine Folge nahe dem Ende fortgesetzt, meldet
    libvlc oft 'ende', bevor je 'spielt' kam. Die Anlauf-Gnade bleibt (ein
    kurzes 'ende' beim Start ist kein Ende), danach wird geschlossen — und ab
    90 % mit der Einstiegsstelle als gesehen gemeldet. Unter 90 % bleibt es wie
    beim Film, der nie anlief: nichts melden."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
const r={};
for(const [fall,pos] of [['abspann',2300],['mitte',600]]){
  lage({modus:'vlc', lief:false, ticks:0, pos, dauer:0});
  antwort={zustand:'ende', key:'film:e3', pos:0, dauer:0};
  await takte(8); const gnade=tvpOffen; await tvpTick();
  r[fall]={gnade, offen:tvpOffen, koerper:koerper(), vlc:[...vlc]};
}
aus(r);
""")
    assert e["abspann"] == {"gnade": True, "offen": False, "vlc": ["vlc:stop@film:e3"],
                            "koerper": [{"id": "e3", "position_s": 2300, "gesehen": True}]}, e["abspann"]
    assert e["mitte"] == {"gnade": True, "offen": False, "vlc": ["vlc:stop@film:e3"], "koerper": []}, e["mitte"]


def test_kurzes_ende_beim_folgenwechsel_schliesst_nicht(tmp_path):
    """medien_smtc.py (gemessen): zwischen zwei Titeln meldet VLC kurz 'ende'.
    Weder während der Wechsel lädt (alte Folge am Ende, Server evtl. schon mit
    neuem Schlüssel) noch direkt nach der Ankunft der neuen Folge (Anlauf-Gnade)
    darf das schließen oder etwas melden — erst das echte Ende danach."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
const r={};
lage({modus:'vlc', pos:2395, dauer:2400, wechsel:{gen:2, id:'e4'}});
antwort={zustand:'ende', key:'film:e3', pos:0, dauer:0}; await tvpTick();
antwort={zustand:'ende', key:'film:e4', pos:0, dauer:0}; await tvpTick();
r.laedt={offen:tvpOffen, koerper:koerper(), vlc:[...vlc]};
lage({id:'e4', modus:'vlc', lief:false, ticks:0, pos:0});   // angekommen: Anlauf der neuen Folge
antwort={zustand:'ende', key:'film:e4', pos:2399, dauer:2400}; await tvpTick();
const kurz={offen:tvpOffen, koerper:koerper()};
antwort={zustand:'spielt', key:'film:e4', pos:1, dauer:2400}; await takte(2);
antwort={zustand:'spielt', key:'film:e4', pos:2398, dauer:2400}; await tvpTick();
antwort={zustand:'ende', key:'film:e4', pos:0, dauer:0}; await tvpTick();
r.neu={kurz, offen:tvpOffen, koerper:koerper()};
lage({id:'e4', modus:'vlc', lief:false, ticks:0, pos:0});   // das kurze 'ende' bleibt stehen (VLC hängt)
antwort={zustand:'ende', key:'film:e4', pos:2399, dauer:2400}; await takte(9);
r.haengt={offen:tvpOffen, koerper:koerper(), vlc:[...vlc]};
aus(r);
""")
    assert e["laedt"] == {"offen": True, "koerper": [], "vlc": []}, e["laedt"]
    assert e["neu"]["kurz"] == {"offen": True, "koerper": []}, "kurzes 'ende' beim Anlauf ist kein Ende"
    assert e["neu"]["offen"] is False
    assert e["neu"]["koerper"] == [{"id": "e4", "position_s": 2398, "gesehen": True}], e["neu"]
    # Hängt der VLC im Anlauf-'ende' mit der Stelle der ALTEN Folge, schließt die
    # Gnade nach 9 Takten — aber diese Stelle gehört nicht der neuen Folge.
    assert e["haengt"] == {"offen": False, "koerper": [], "vlc": ["vlc:stop@film:e4"]}, e["haengt"]


# ------------------------------------------------------- Esc und Folgenwechsel

def test_esc_im_abspann_ist_gesehen(tmp_path):
    """JB: Beenden per Esc ab 90 % zählt als gesehen. Die Reihenfolge zählt:
    tvpZu merkt die Stelle in der Folgenliste — die Meldestelle schreibt „gesehen"
    und Stelle 0 DANACH, sonst stünde wieder die Stelle kurz vor dem Ende dort.
    Mittendrin bleibt es beim Merken der Stelle (Körper wie bisher). Ohne offenen
    Player (VLC, Esc aus der Musik-Leiste) sind Dauer und Meta vom vorigen Film
    übrig: dann nie „gesehen"."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
const r={};
lage({pos:2300, dauer:2400}); await filmStopp();
r.abspann={koerper:koerper(), info:folge(tvInfoDaten.eps,'e3'), cache:folge(tvpFolgenCache.eps,'e3'),
           bilder:[...zeichnungen], toast:toasts.at(-1)};
lage({pos:1234, dauer:2400}); await filmStopp();
r.mitte={koerper:koerper(), info:folge(tvInfoDaten.eps,'e3'), toast:toasts.at(-1)};
lage({offen:false, pos:2300, dauer:2400, key:'film:F7', vlcSpielt:true}); _vlcPos=5000; await filmStopp();
r.ohnePlayer={koerper:koerper()};
aus(r);
""")
    a = e["abspann"]
    assert a["koerper"] == [{"id": "e3", "position_s": 2300, "gesehen": True}], a
    assert a["info"] == [0, True] and a["cache"] == [0, True], a
    assert a["bilder"] == ["e1:0✓,e2:0✓,e3:0✓,e4:0,e5:0"], "genau einmal neu gezeichnet, mit ✓"
    assert "gesehen" in a["toast"], a["toast"]
    m = e["mitte"]
    assert m["koerper"] == [{"id": "e3", "position_s": 1234}], m
    assert m["info"] == [1234, False] and "1234" in m["toast"], m
    assert e["ohnePlayer"]["koerper"] == [{"id": "F7", "position_s": 5000}], e["ohnePlayer"]


def test_weiter_im_abspann_ist_gesehen(tmp_path):
    """JB: ⏭ im Abspann zählt als gesehen. Die alte Folge wird gemeldet und
    lokal ✓; ein anschließendes ⏮ landet bei ihr am Anfang. Einmalig: Esc,
    während die nächste Folge noch lädt, meldet die alte nicht noch einmal
    (ihre Stelle kurz vor dem Ende schriebe sonst über „gesehen"). Der Merker
    gilt NUR für „gesehen": nach ⏭ mittendrin meldet ein Esc die neue Stelle."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
lage({pos:2300, dauer:2400});
await tvpFolge(1);
const r={koerper:koerper(), ziel:starts.at(-1), info:folge(tvInfoDaten.eps,'e3')};
tvpPos=2310; await filmStopp();                            // Esc, e4 lädt noch
r.esc={koerper:koerper().length, info:folge(tvInfoDaten.eps,'e3'), toast:toasts.at(-1)};
lage({pos:1200, dauer:2400}); await tvpFolge(1);
tvpPos=1210; await filmStopp();
r.mitte={koerper:koerper(), info:folge(tvInfoDaten.eps,'e3')};
lage({pos:2300, dauer:2400}); await tvpFolge(1);
tvpWechsel=null; tvpIdAkt='e4'; tvpPos=3; tvpZurueckModus='normal';   // e4 ist angekommen
starts.length=0; await tvpZurueck();
r.zurueck={ziel:starts.at(-1), modus:tvpModusNaechster&&tvpModusNaechster.modus};
aus(r);
""")
    assert e["koerper"] == [{"id": "e3", "position_s": 2300, "gesehen": True}], e["koerper"]
    assert e["ziel"] == "film:e4@0" and e["info"] == [0, True], e
    assert e["esc"]["koerper"] == 1 and e["esc"]["info"] == [0, True], e["esc"]
    assert "gesehen" in e["esc"]["toast"], e["esc"]
    assert e["mitte"] == {"koerper": [{"id": "e3", "position_s": 1200}, {"id": "e3", "position_s": 1210}],
                          "info": [1210, False]}, e["mitte"]
    assert e["zurueck"] == {"ziel": "film:e3@0", "modus": "musik"}, e["zurueck"]


# ------------------------------------------------------------ Film: Kopien

def test_filmende_zieht_info_reihen_und_hero_nach(tmp_path):
    """Einzelfilm: Info-Seite (d), alle Reihen, Hero — an EINER Stelle. Der Film
    fliegt aus „Weiterschauen" (wie reihen() am Server: Stelle > 0 und nicht
    gesehen). Bei geschlossener Info zeichnet der sichtbare Fernsehmodus neu."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
const r={};
const reihen=()=>({weiterschauen:[F('F1',3000),F('F2',100)], top:[F('F1',3000)], neu:[],
                   merkliste:[F('F1',3000)], genres:{Drama:[F('F1',3000)]}});
lage({id:'F1', pos:5990, dauer:6000, meta:{typ:'film', laufzeit_min:100},
      daten:{d:F('F1',3000), eps:[]}, reihen:reihen(), hero:F('F1',3000)});
antwort={zustand:'aus', key:'', pos:6000, dauer:6000}; await tvpTick();
const g=a=>a.map(x=>x.id+':'+x.position_s+(x.gesehen?'✓':''));
r.info={koerper:koerper(), d:[tvInfoDaten.d.position_s, tvInfoDaten.d.gesehen], bilder:[...zeichnungen],
        weiter:g(tvFilmReihen.weiterschauen), top:g(tvFilmReihen.top), merk:g(tvFilmReihen.merkliste),
        genre:g(tvFilmReihen.genres.Drama), hero:[tvHeroDaten.position_s, tvHeroDaten.gesehen]};
lage({id:'F1', pos:3100, dauer:6000, meta:{typ:'film', laufzeit_min:100}, info:false, daten:null,
      reihen:reihen()});
_els.tv={style:{display:''}};                              // Fernsehmodus sichtbar, Info zu
antwort={zustand:'aus', key:'', pos:3100, dauer:6000}; await tvpTick();
r.tv={koerper:koerper(), bilder:[...zeichnungen], weiter:g(tvFilmReihen.weiterschauen)};
delete _els.tv;
aus(r);
""")
    i = e["info"]
    assert i["koerper"] == [{"id": "F1", "position_s": 6000, "gesehen": True}], i
    assert i["d"] == [0, True] and i["bilder"] == ["film:0✓"], i
    assert i["weiter"] == ["F2:100"], "gesehen fliegt aus Weiterschauen"
    assert i["top"] == ["F1:0✓"] and i["merk"] == ["F1:0✓"] and i["genre"] == ["F1:0✓"], i
    assert i["hero"] == [0, True], i
    t = e["tv"]
    assert t["koerper"] == [{"id": "F1", "position_s": 3100}] and t["bilder"] == ["tv"], t
    assert t["weiter"] == ["F1:3100", "F2:100"], t


def test_frisch_geladene_info_behaelt_die_meldung(tmp_path):
    """Esc bei geschlossener Info öffnet sofort die Info — deren Daten kommen
    vom Server (Spiegel bzw. Jellyfin live), und der zieht erst nach, wenn
    Jellyfin die Meldung angenommen hat. Die Meldungen dieser Seite gelten
    darum auch für frisch geladene Daten: Film ohne „Weiterschauen bei 99 %",
    Folge mit ✓, „▶ Weiterschauen" wählt die nächste."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
const r={};
lage({id:'F1', pos:5990, dauer:6000, meta:{typ:'film', laufzeit_min:100}, info:false, daten:null});
ANTWORTEN=[['/api/filme/detail', F('F1',5400)], ['/api/filme/mehrwie', {items:[]}]];
await filmStopp(); await ruhe();                           // filmStopp öffnet die Info (Esc bei geschlossener Info)
r.film={id:tvInfoId, d:[tvInfoDaten.d.position_s, tvInfoDaten.d.gesehen]};
lage({pos:2300, dauer:2400, info:false, daten:null});
ANTWORTEN=[['/api/filme/detail', {id:'s9', typ:'serie', titel:'Dark'}], ['/api/filme/mehrwie', {items:[]}],
           ['/api/filme/episoden', {items:folgen()}]];
await filmStopp(); await ruhe();
r.serie={id:tvInfoId, e3:folge(tvInfoDaten.eps,'e3')};
starts.length=0; tvSerienPlay(); r.serie.weiter=starts.at(-1);
aus(r);
""")
    assert e["film"] == {"id": "F1", "d": [0, True]}, "die frisch geladene Film-Info kennt die Meldung"
    assert e["serie"]["id"] == "s9" and e["serie"]["e3"] == [0, True], e["serie"]
    assert e["serie"]["weiter"] == "film:e4@0", e["serie"]


# --------------------------------------------------- Sleep: nichts startet

def test_sleep_aktiv_oder_abgelaufen_nach_dem_filmende_startet_nichts(tmp_path):
    """JB 24.09.2026: „nein, nur musik, aber wenn der film zu ende ist, keinen
    weiteren starten". Wächter über den GANZEN Ende-Weg (Takt, tvpZu, Meldestelle,
    Musik-Übergabe medienNachFilm): ist der Sleep-Timer aktiv (Minuten oder
    „nach diesem Titel") oder abgelaufen, startet nach dem Filmende nichts —
    keine nächste Folge, keine Musik, kein VLC-Start — und die EINE
    Entscheidung nachFilmEnde sagt „schlaf". Heute startet dort auch ohne Sleep
    nichts (eine Automatik „nächste Folge" ist nicht bestätigt); wer sie baut,
    muss nachFilmEnde fragen, sonst wird dieser Test rot."""
    e = _lauf(tmp_path, *_teile(), r"""
const faelle=[['ohne',()=>sleepSetzen('0')], ['minuten',()=>sleepSetzen('30')], ['titel',()=>sleepSetzen('titel')],
              ['abgelaufen',()=>{sleepSetzen('1'); timerLaeuftAb();}]];
for(const [modus,geraet] of [['browser','browser'],['vlc','vlc']]){
  for(const [fall,stellen] of faelle){
    lage({modus, geraet, pos:2395, dauer:2400}); stellen(); vlc.length=0;
    antwort=modus==='browser'?{zustand:'aus', key:'', pos:2400, dauer:2400}
                            :{zustand:'ende', key:'film:e3', pos:0, dauer:0};
    await takte(3);
    aus({modus, fall, offen:tvpOffen, starts:[...starts], vlc:[...vlc], musik:_log.filter(x=>x.startsWith('play:')),
         entscheidung:(typeof nachFilmEnde==='function')?nachFilmEnde().art:'fehlt',
         gemeldet:koerper().length});
  }
}
sleepSetzen('1'); timerLaeuftAb(); sleepSetzen('0');
aus({fall:'neu gestellt', entscheidung:(typeof nachFilmEnde==='function')?nachFilmEnde().art:'fehlt'});
""")
    *filme_faelle, neu = e
    assert len(filme_faelle) == 8
    for x in filme_faelle:
        assert x["offen"] is False and x["gemeldet"] == 1, x
        assert x["starts"] == [] and x["musik"] == [], f"nach dem Filmende startete etwas: {x}"
        erlaubt = ["vlc:stop@film:e3"] if x["modus"] == "vlc" else []
        assert x["vlc"] == erlaubt, x
        soll = "nichts" if x["fall"] == "ohne" else "schlaf"
        assert x["entscheidung"] == soll, x
    assert neu["entscheidung"] == "nichts", "ein neu gestellter Sleep-Timer hebt „abgelaufen“ auf"


# ------------------------------------------------------ Server: Spiegel + VLC

def _spiegel(tmp_path, monkeypatch):
    os.makedirs(tmp_path, exist_ok=True)
    filme.einrichten(str(tmp_path))
    filme._sitzung.clear()
    filme._fehlversuch_ts = 0.0
    filme._anmelde_sperre_ts = 0.0
    filme._merkmal_ruhe_ts = 0.0
    monkeypatch.setattr(filme, "_zugang", lambda: {
        "url": "https://jelly.example", "benutzer": "JBK", "passwort": "pw"})
    filme.fam.json_schreiben(filme._pfade["katalog"], {
        "stand": time.time() - 3600, "server_version": "12.1.0",
        "eintraege": [filme._eintrag(it) for it in FAKE_ITEMS["Items"]]})


def _eintrag(item_id):
    return next(e for e in filme.katalog_lesen()["eintraege"] if e["id"] == item_id)


def test_spiegel_zieht_nach_erfolgreicher_meldung_nach(tmp_path, monkeypatch):
    """reihen() und detail() lesen den Katalog-Spiegel, und der nächste Abzug
    kommt erst in 6 h — seit 23.09. scheitert er ganz. Nach einer ANGENOMMENEN
    Meldung zieht der Server den Eintrag darum selbst nach (wie Jellyfin:
    gesehen heißt Stelle 0; eine bloße Stelle ändert „gesehen" nicht). Eine
    Meldung, die nur in der Warteschlange landet, ändert den Spiegel nicht;
    eine Folge (steht nicht im Spiegel) lässt die Datei unberührt."""
    _spiegel(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12")
    monkeypatch.setattr(filme, "_http", jf)
    assert _eintrag("f1")["position_s"] == 600 and _eintrag("f1")["gesehen"] is False
    assert filme.fortschritt("f1", 3100) is True
    assert (_eintrag("f1")["position_s"], _eintrag("f1")["gesehen"]) == (3100, False)
    assert [e["id"] for e in filme.reihen()["weiterschauen"]] == ["f1"]
    assert filme.fortschritt("f1", 7700, gesehen=True) is True
    assert (_eintrag("f1")["position_s"], _eintrag("f1")["gesehen"]) == (0, True)
    assert filme.reihen()["weiterschauen"] == [], "gesehen fliegt aus Weiterschauen"
    # Folge: nicht im Spiegel -> Datei unberührt (kein Umschreiben, kein 'null').
    vorher = open(filme._pfade["katalog"], "rb").read()
    assert filme.fortschritt("e3", 2300, gesehen=True) is True
    assert open(filme._pfade["katalog"], "rb").read() == vorher
    # Jellyfin nimmt nicht an -> Warteschlange, Spiegel bleibt.
    jf.antworten = [("/Sessions/Playing/Progress", 500, b"")]
    assert filme.fortschritt("s1", 999) is False
    assert _eintrag("s1")["position_s"] == 0
    assert len(filme._queue_lesen()) == 1


def test_spiegel_und_abzug_schreiben_nacheinander(tmp_path, monkeypatch):
    """Zwei Schreiber, eine Datei (Familien-Regel „Kann eine Änderung verloren
    gehen?"): der Abzug schreibt den ganzen Spiegel, die Meldung ändert einen
    Eintrag. Läse die Meldung den alten Spiegel, schriebe der Abzug dazwischen
    und danach die Meldung, wäre der frische Abzug weg. Darum schreibt der Abzug
    unter derselben Sperre, die die Meldung nimmt."""
    _spiegel(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", antworten=[
        ("/System/Info", 200, {"Version": "12.1.0"}),
        ("/Users/u1/Items", 200, FAKE_ITEMS), ("/Sessions/Playing/Progress", 204, b"")]))
    gesehen = []
    echt = filme.fam.json_schreiben

    def schreiben(pfad, daten, *a, **kw):
        if os.path.abspath(str(pfad)) == os.path.abspath(filme._pfade["katalog"]):
            sperre = filme._datei_locks.get(str(filme._pfade["katalog"]))
            gesehen.append(bool(sperre and sperre.locked()))
        return echt(pfad, daten, *a, **kw)
    monkeypatch.setattr(filme.fam, "json_schreiben", schreiben)
    assert filme.katalog_abzug()["ok"] is True
    assert gesehen == [True], f"der Abzug schreibt den Spiegel ohne die gemeinsame Sperre: {gesehen}"


def test_vlc_stopp_mit_nur_key_trifft_nur_diesen_titel(monkeypatch, vlc_attrappe):
    """Am Filmende gibt die Seite den VLC frei ('stop'), damit libvlc den
    Endzustand samt Schlüssel loslässt. Hat inzwischen die Musik den einen VLC
    übernommen, darf das sie nicht treffen: 'stop' mit nur_key wirkt nur, wenn
    VLC genau diesen Titel hat. Ohne nur_key stoppt es wie bisher."""
    import youtube_app as app
    monkeypatch.setattr(app, "_smtc", None)
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    sp = app._vlc["spieler"]
    st = app.vlc_kommando({"cmd": "stop", "nur_key": "film:e3"})
    assert ("stop",) not in sp.rufe and st["key"] == "abc|mp3", "die Musik wurde gestoppt"
    app.vlc_kommando({"cmd": "play", "key": "film:e3", "url": "https://jelly.example/strom"})
    st = app.vlc_kommando({"cmd": "stop", "nur_key": "film:e3"})
    assert sp.rufe[-1] == ("stop",) and st["key"] == "", st
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    st = app.vlc_kommando({"cmd": "stop"})
    assert sp.rufe[-1] == ("stop",) and st["key"] == "", "ohne nur_key stoppt es wie bisher"

