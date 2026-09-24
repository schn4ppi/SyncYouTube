# -*- coding: utf-8 -*-
"""Mindest-Sehzeit: „gesehen" nur nach wirklich geschauter Zeit (JB-Idee 24.09.2026).

JB wörtlich: „eventuell auch gucken wie lange ein film geguckt wurde, sozusagen
einen mindest timer um festzulegen - bedenken wenn ab einer bestimmten stelle
weiter, bzw angefangen wird".

Regel (Hauptagent, Runde 3): „gesehen" nur, wenn
  (a) die Stelle 90 % der Dauer erreicht (das natürliche Ende liegt dahinter) UND
  (b) in DIESER Wiedergabe wirklich geschaute Zeit W >= M,
      M = min(5 min, 50 % × max(0, 0,9·Dauer − Startstelle)).
W = Summe der Spiel-Intervalle in Medienzeit (Tempo egal); ein Schritt über 3 s
gilt als Sprung und zählt nicht. Startstelle = Stelle, mit der diese Wiedergabe
öffnet (Start oder Weiterschauen). Gemessen im Browser am <video> (timeupdate),
im VLC aus den Stellen des 1-s-Takts — für natürliches Ende, Esc und ⏭ gleich.

Wird „gesehen" verweigert, darf die gemeldete Stelle Jellyfin nicht selbst zum
Haken bringen. Beleg Jellyfin-Quelltext, Tag v12.1 (Commit ee91c75, 15.09.2026):
POST /Sessions/Playing/Progress → SessionManager.OnPlaybackProgress(info, false)
→ für jeden Nutzer UserDataManager.UpdatePlayState(item, data, PositionTicks).
Dort setzt Played: Anteil > MaxResumePct (90), Stelle ≥ Laufzeit − 1 s, eine
Laufzeit unter MinResumeDurationSeconds (300) ab MinResumePct (5 %), und eine
unbekannte Laufzeit immer. `_jellyfin_setzt_played` bildet das nach und prüft
jede verweigerte Meldung gegen JEDE Laufzeit, die Jellyfin haben könnte
(laufzeit_min ist auf Minuten gerundet: ±30 s).

Ausgeführt wird das ECHTE JavaScript der Seite mit deno: tvFilmPlayer (setzt die
Startstelle), die Listener des Film-<video> (timeupdate), der 1-s-Takt tvpTick,
tvpFilmEnde, filmStopp (Esc), tvpFolge/tvpZielAusfuehren (⏭) und die EINE
Meldestelle. Die Attrappe modelliert die Unterschiede, um die es geht: der
Browser liefert timeupdate in Medienzeit (auch nach einem Sprung genau einmal
mit der neuen Stelle), das Transcoder-Video beginnt bei 0 plus Versatz, ein
pausiertes altes Video feuert NACH dem Tausch noch ein timeupdate (HTML: pause()
reiht timeupdate + pause ein), libvlc meldet am Ende 'ende' mit Stelle 0.

Nicht hier gemessen: ob Renés Jellyfin die Meldungen so verarbeitet (Stand
24.09. HTTP 401), und die echte Taktung von timeupdate im verdeckten Tab.
"""
import os
import re
import sys
from fractions import Fraction

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

from test_film_transcoder_tausch import ATTRAPPE  # noqa: E402
from test_medientasten_verhalten import (  # noqa: E402
    _js_funktion,
    _js_zeile,
    _lauf,
    _modul_js,
    _pc,
)

# In dieser Runde neu: fehlen sie (Rot-Lauf am alten Stand), bleiben sie weg —
# dann läuft der alte Weg, und die Tests scheitern am VERHALTEN.
NEU_ZEILEN = ("const SEHZEIT=",)
NEU = ("sehzeitUrteil", "tvpSehzeitZaehlen")
NAMEN = ("tvpDirektSrc", "tvpBefehl", "tvpAbgeloestFreigeben", "tvpVideoVerdrahten", "tvpVideoTauschen",
         "tvFilmPlayer", "tvpZu", "tvpTick", "tvpFilmEnde", "tvpMeldeDauer", "filmFortschrittMelden",
         "filmGemeldetAnwenden", "filmReihenAnwenden", "filmLokalNachziehen", "filmStopp", "tvpFolge",
         "tvpZielAusfuehren", "tvpWeiterZiel", "tvpLandePos", "tvpBasis", "tvpWechselStarten") + NEU

UMFELD = r"""
globalThis.setTimeout=()=>0; globalThis.setInterval=()=>0;      // kein echter Takt: die Tests treiben tvpTick
globalThis.clearTimeout=()=>{}; globalThis.clearInterval=()=>{};
var tvpWechselGen=0, tvpFolgenCache=null;
const netz=[], starts=[];
globalThis.fetch=(u,o)=>{u=String(u); netz.push([u, o&&o.body?JSON.parse(o.body):null]);
  return Promise.resolve({json:async()=>({})});};
const koerper=()=>netz.filter(n=>n[0]==='/api/filme/fortschritt').map(n=>n[1]);
function tvInfo(){} function vlcPosGeschaetzt(){return 0;}
function filmePlay(id,pos){starts.push(id+'@'+(pos||0));}
let EPS=[], D=0, ID='';
async function tvpFolgenHolen(){return EPS;}
// Der EINE VLC: der Takt liest seinen Status, ein Sprung setzt die Stelle.
let vlcStatus={zustand:'aus', key:'', pos:0, dauer:0};
vlcBefehl=(c,d)=>{
  if(c==='seek')vlcStatus={...vlcStatus, pos:d.wert};
  return Promise.resolve(c==='status'?{verfuegbar:true, ...vlcStatus}:{});
};
const video=()=>_els['tvp-video'];
const stelle=()=>tvpModus==='browser'?(tvpTc?tvpTcOffset:0)+video().currentTime:vlcStatus.pos;
/* Eine Wiedergabe öffnen, wie filmePlay es tut: Browser direkt, Transcoder oder VLC. */
async function start(id,pos,o){
  o=o||{};
  if(tvpOffen)tvpZu();
  tvpModus=o.vlc?'vlc':'browser'; tvpTc=!!o.tc; tvpTimer=1; tvpWechsel=null;
  tvpGesehenGemeldet=''; filmGemeldet={}; netz.length=0; toasts.length=0; starts.length=0;
  const min=o.min??40; D=min*60; ID=id;
  EPS=[{id, staffel:1, folge:3, laufzeit_min:min, position_s:pos, gesehen:false},
       {id:id+'n', staffel:1, folge:4, laufzeit_min:min, position_s:0, gesehen:false}];
  const meta={typ:'folge', serie_id:'s9', titel:'Dark · S1 F3', laufzeit_min:min};
  if(o.vlc)vlcStatus={zustand:'aus', key:'film:'+id, pos:0, dauer:0};   // libvlc öffnet noch
  tvFilmPlayer(id,meta.titel,pos,meta);
  if(o.vlc){vlcStatus={zustand:'spielt', key:'film:'+id, pos, dauer:D};}
  else{
    const v=video(); v.feuer('timeupdate');               // Autoplay: kurz Stelle 0 (Transcoder: Versatz)
    if(!tvpTc)v.feuer('loadedmetadata');                   // direkt: springt auf die Einstiegsstelle
    spielen(v); v.feuer('timeupdate');
  }
  await tvpTick();
}
/* Spielt bis zur Filmstelle `bis`: Browser = timeupdate je Schritt (Medienzeit),
   VLC = ein Takt je Schritt. Danach zieht ein Takt tvpPos nach (wie der 1-s-Takt). */
async function schaue(bis,schritt){
  schritt=schritt||(tvpModus==='browser'?0.25:1);
  if(tvpModus==='browser'){
    const v=video(); v.paused=false;
    while(stelle()+schritt<=bis+1e-9){v.currentTime+=schritt; v.feuer('timeupdate');}
  }else{
    while(vlcStatus.pos+schritt<=bis+1e-9){vlcStatus={...vlcStatus, zustand:'spielt', pos:vlcStatus.pos+schritt};
      await tvpTick();}
  }
  await tvpTick();
}
/* Sprung wie tvpSeek/tvpRel: Stelle merken, Motor springen lassen. */
async function springe(ziel){
  tvpPos=ziel; await tvpBefehl('seek',{wert:ziel});
  if(tvpModus==='browser'){const v=video(); if(tvpTc)spielen(v); v.feuer('timeupdate');}
  await tvpTick();
}
/* Ausgang: natürliches Ende, Esc (filmStopp) oder ⏭ (tvpFolge). */
async function beende(art){
  if(art==='ende'){
    if(tvpModus==='browser'){await schaue(D); const v=video(); v.ended=true; v.paused=true;}
    else{await schaue(D-1); vlcStatus={...vlcStatus, zustand:'ende', pos:0, dauer:0};}
    await tvpTick();
  }else if(art==='esc')await filmStopp();
  else await tvpFolge(1);
  const r={art, koerper:koerper(), toast:toasts.at(-1)||'', offen:tvpOffen,
           lokal:filmGemeldet[ID]||null, liste:[EPS[0].position_s, EPS[0].gesehen]};
  if(tvpOffen)tvpZu();
  tvpWechsel=null;
  return r;
}
const AUSGAENGE=['ende','esc','weiter'];
const MODI=[['browser',{}],['transcoder',{tc:true}],['vlc',{vlc:true}]];
"""


def _teile():
    q = _pc()
    zeilen = [_modul_js(), "const medienS=medienSitzung(()=>null);", _js_zeile(q, "let tvpAbgeloest"),
              _js_zeile(q, "let tvpGesehenGemeldet"), _js_zeile(q, "let tvpRateWert")]
    zeilen += [_js_zeile(q, z) for z in NEU_ZEILEN if re.search(r"^" + re.escape(z), q, re.M)]
    namen = [n for n in NAMEN if n not in NEU or re.search(r"^(?:async )?function " + n + r"\(", q, re.M)]
    return zeilen + [ATTRAPPE, UMFELD] + [_js_funktion(q, n) for n in namen]


# ------------------------------------------------ Jellyfin 12.1 als Orakel

def _jellyfin_setzt_played(position_s, laufzeit_s):
    """UserDataManager.UpdatePlayState, Jellyfin Tag v12.1 (ee91c75), Zeilen
    443-497, mit den Vorgaben aus ServerConfiguration.cs (MinResumePct 5,
    MaxResumePct 90, MinResumeDurationSeconds 300). Ticks = 1e-7 s."""
    ticks, laufzeit = int(position_s) * 10_000_000, round(laufzeit_s * 10_000_000)
    if laufzeit <= 0:
        return True                          # unbekannte Laufzeit: „fully played"
    if ticks <= 0:
        return False
    anteil = Fraction(ticks * 100, laufzeit)
    if anteil < 5:
        return False                         # Anfang: Stelle 0, nicht gespielt
    if anteil > 90 or ticks >= laufzeit - 10_000_000:
        return True
    return laufzeit_s < 300                  # kurzes Stück: ab 5 % gespielt


def test_orakel_bildet_jellyfin_nach():
    """Blindheits-Probe des Orakels an den Grenzen aus dem Quelltext."""
    assert _jellyfin_setzt_played(2160, 2400) is False, "genau 90 %: nicht > 90"
    assert _jellyfin_setzt_played(2161, 2400) is True
    assert _jellyfin_setzt_played(119, 2400) is False and _jellyfin_setzt_played(10, 2400) is False
    assert _jellyfin_setzt_played(150, 290) is True, "unter 5 min: ab 5 % gespielt"
    assert _jellyfin_setzt_played(10, 290) is False, "unter 5 % bleibt es offen"
    assert _jellyfin_setzt_played(10, 0) is True, "ohne Laufzeit immer gespielt"


def _bleibt_offen(k, dauer):
    """Eine verweigerte Meldung bringt Jellyfin bei KEINER möglichen Laufzeit
    (laufzeit_min auf Minuten gerundet: ±30 s) zum Haken."""
    assert "gesehen" not in k, k
    for laufzeit in range(int(dauer) - 30, int(dauer) + 31):
        assert not _jellyfin_setzt_played(k["position_s"], laufzeit), \
            f"Stelle {k['position_s']} setzt bei Laufzeit {laufzeit} s in Jellyfin „gespielt“: {k}"


# ------------------------------------------------------ JBs drei Beispiele

def test_beispiel_ab_null_zehn_sekunden_dann_ans_ende_ist_nicht_gesehen(tmp_path):
    """Beispiel 1: ab 0 gestartet, nach 10 s ans Ende gesprungen → NICHT gesehen —
    für natürliches Ende, Esc und ⏭ gleich, im Browser, im Transcoder und im VLC.
    Gemeldet wird die letzte ECHT geschaute Stelle vor dem Sprung (10 s), lokal
    wie an Jellyfin; der Toast sagt, warum es nicht zählt."""
    e = _lauf(tmp_path, *_teile(), r"""
for(const [modus,o] of MODI)for(const art of AUSGAENGE){
  await start('e3',0,o); await schaue(10); await springe(D-5);
  aus({modus, ...await beende(art)});
}
""")
    assert len(e) == 9
    for r in e:
        assert r["koerper"] == [{"id": "e3", "position_s": 10}], r
        assert r["lokal"] == {"position_s": 10, "gesehen": False}, r
        _bleibt_offen(r["koerper"][0], 2400)
        if r["art"] == "esc":
            assert "zu wenig geschaut" in r["toast"] and "bei 10." in r["toast"], r
            assert "als gesehen markiert" not in r["toast"], r
        if r["art"] == "weiter":
            assert r["liste"] == [10, False], f"die Folgenliste zeigt die gesprungene Stelle: {r}"


def test_beispiel_bei_85_prozent_weiter_bis_zum_abspann_ist_gesehen(tmp_path):
    """Beispiel 2: bei 85 % weitergeschaut bis zum Abspann → gesehen. Startstelle
    2040 von 2400 s: M = min(300, 50 % × 120) = 60 s, geschaut werden 260 s bis
    2300 (Esc/⏭ im Abspann) bzw. bis zum Ende."""
    e = _lauf(tmp_path, *_teile(), r"""
for(const [modus,o] of MODI)for(const art of AUSGAENGE){
  await start('e3',2040,o); await schaue(2300);
  aus({modus, ...await beende(art)});
}
""")
    assert len(e) == 9
    for r in e:
        (k,) = r["koerper"]
        assert k.get("gesehen") is True and k["id"] == "e3" and k["position_s"] >= 2300, r
        assert r["lokal"] == {"position_s": 0, "gesehen": True}, r
        if r["art"] == "esc":
            assert "als gesehen markiert" in r["toast"], r
        if r["art"] == "weiter":
            assert r["liste"] == [0, True], r


def test_beispiel_ab_50_prozent_erst_nach_mindest_sehzeit_gesehen(tmp_path):
    """Beispiel 3: ab 50 % gestartet, sofort ans Ende gesprungen → nicht gesehen
    (gemeldet: die Startstelle); erst nach min(5 min, 20 % der Dauer) echter
    Sehzeit gesehen — beide Seiten der Grenze, beide Zweige des min():
    40-min-Folge (20 % = 8 min > 5 min: M = 300 s) und 20-min-Folge
    (20 % = 4 min: M = 240 s)."""
    e = _lauf(tmp_path, *_teile(), r"""
for(const [modus,o] of MODI){
  for(const art of AUSGAENGE){
    await start('e3',1200,o); await springe(D-5);
    aus({fall:'sofort', modus, ...await beende(art)});
  }
  for(const [fall,min,ab,bis] of [['300 knapp',40,1200,1499],['300',40,1200,1500],
                                  ['240 knapp',20,600,839],['240',20,600,840]]){
    await start('e3',ab,{...o, min}); await schaue(bis); await springe(D-5);
    aus({fall, modus, bis, dauer:D, ...await beende('esc')});
  }
}
""")
    assert len(e) == 3 * 7
    for r in e:
        k = r["koerper"]
        if r["fall"] == "sofort":
            assert k == [{"id": "e3", "position_s": 1200}], r
            _bleibt_offen(k[0], 2400)
        elif r["fall"].endswith("knapp"):
            assert k == [{"id": "e3", "position_s": r["bis"]}], f"eine Sekunde zu wenig zählt nicht: {r}"
            _bleibt_offen(k[0], r["dauer"])
        else:
            assert k == [{"id": "e3", "position_s": r["dauer"] - 5, "gesehen": True}], r


# ------------------------------------------------------------- Messung

def test_sprung_regel_tempo_rueckwaerts_und_pause(tmp_path):
    """Nur Spiel-Intervalle zählen, in Medienzeit: ein Schritt von genau 3 s
    zählt, einer von 3,25 s ist ein Sprung; bei 1,5x kommen 0,375 s Medienzeit
    je timeupdate (Tempo egal, es zählt die Medienzeit). Rückwärts zählt nicht
    (auch nicht in kleinen Schritten), und Ziehen am Regler in kleinen
    Schritten zählt nicht, solange pausiert ist. Geprüft über das Ergebnis:
    ab 0, dann ans Ende gesprungen und Esc — gesehen nur mit W >= 300 s."""
    e = _lauf(tmp_path, *_teile(), r"""
const gesehen=()=>koerper().some(k=>k.gesehen);
async function fall(name,modus,o,wie){await start('e3',0,o); await wie(); await springe(D-5); await filmStopp();
  aus({name, modus, gesehen:gesehen(), k:koerper()}); tvpWechsel=null;}   // tvpZu stellt tvpModus zurück
for(const [modus,o] of [['browser',{}],['vlc',{vlc:true}]]){
  await fall('3 s',modus,o,()=>schaue(300,3));
  await fall('3,25 s',modus,o,()=>schaue(299,3.25));
  await fall('rückwärts',modus,o,async()=>{await schaue(200);
    for(let i=0;i<50;i++){                                  // in 2-s-Schritten zurück, während es spielt
      if(tvpModus==='browser'){video().currentTime-=2; video().feuer('timeupdate');}
      else{vlcStatus={...vlcStatus, pos:vlcStatus.pos-2}; await tvpTick();}}
    await schaue(200);});                                   // wieder hoch bis 200: das zählt (100 s)
  await fall('pause',modus,o,async()=>{await schaue(200);
    for(let i=0;i<50;i++){                                  // pausiert in 2-s-Schritten vor
      if(tvpModus==='browser'){const v=video(); v.paused=true; v.currentTime+=2; v.feuer('timeupdate');}
      else{vlcStatus={...vlcStatus, zustand:'pause', pos:vlcStatus.pos+2}; await tvpTick();}}});
}
await fall('1,5x','browser',{},async()=>{video().playbackRate=1.5; await schaue(300,0.375);});
""")
    ergebnis = {(r["name"], r["modus"]): r["gesehen"] for r in e}
    assert ergebnis == {
        ("3 s", "browser"): True, ("3 s", "vlc"): True,
        ("3,25 s", "browser"): False, ("3,25 s", "vlc"): False,
        ("rückwärts", "browser"): True, ("rückwärts", "vlc"): True,     # 200 + 100 = 300
        ("pause", "browser"): False, ("pause", "vlc"): False,           # 200
        ("1,5x", "browser"): True,
    }, ergebnis
    r = next(x for x in e if x["name"] == "rückwärts" and x["modus"] == "browser")
    assert r["k"][0]["gesehen"] is True


def test_rueckwaerts_in_kleinen_schritten_zaehlt_nicht(tmp_path):
    """Gegenstück zu „rückwärts": nach 200 s in 2-s-Schritten zurück bis 100 und
    NICHT wieder hoch — W bleibt 200 s (ein Betrag statt der Richtung zählte
    hier 100 s dazu und machte daraus „gesehen")."""
    e = _lauf(tmp_path, *_teile(), r"""
for(const [modus,o] of [['browser',{}],['vlc',{vlc:true}]]){
  await start('e3',0,o); await schaue(200);
  for(let i=0;i<50;i++){
    if(tvpModus==='browser'){video().currentTime-=2; video().feuer('timeupdate');}
    else{vlcStatus={...vlcStatus, pos:vlcStatus.pos-2}; await tvpTick();}}
  await springe(D-5); await filmStopp();
  aus({modus, k:koerper()}); tvpWechsel=null;
}
""")
    assert [r["modus"] for r in e] == ["browser", "vlc"]
    for r in e:
        assert r["k"] == [{"id": "e3", "position_s": 200}], r


def test_transcoder_sprung_altes_video_verfaelscht_die_messung_nicht(tmp_path):
    """Transcoder: jeder Sprung baut ein NEUES <video> (Stelle = Versatz + 0).
    Das alte feuert danach noch zweimal timeupdate (HTML): pause() reiht eines
    ein (dort Stelle 10), und die Freigabe per load(), sobald das neue spielt,
    setzt es auf 0 und meldet auch das — mitten zwischen die Schritte des neuen.
    Mit dem Versatz des NEUEN gerechnet sind das falsche Film-Stellen; der
    zweite Stoß ließ den nächsten echten Schritt 1,25 s statt 0,25 s zählen.
    Gezählt wird nur das aktuelle Film-Video: genau 10 s + 290 s = 300 s."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
await start('e3',0,{tc:true}); await schaue(10);
const A=video();
tvpPos=2000; await tvpBefehl('seek',{wert:2000}); const B=video();
A.feuer('timeupdate');                                      // pause() des alten: eingereihtes timeupdate
spielen(B); B.feuer('timeupdate');                          // das neue spielt → das alte wird freigegeben
const aFrei={src:A.src, t:A.currentTime};
for(let i=0;i<4;i++){B.currentTime+=0.25; B.feuer('timeupdate');}
A.feuer('timeupdate');                                      // load() des alten: Stelle 0 → timeupdate
await schaue(2290);
const w=tvpSeh.w;
await springe(D-5); await filmStopp();
aus({neu:A!==B, aFrei, w, k:koerper()});
""")
    assert e["neu"], "Vorbedingung: der Sprung hat das Video getauscht"
    assert e["aFrei"] == {"src": "", "t": 0}, f"Vorbedingung: das alte ist freigegeben (load): {e['aFrei']}"
    assert e["w"] == 300, f"geschaute Zeit verfälscht durch das alte Video: {e['w']}"
    assert e["k"] == [{"id": "e3", "position_s": 2395, "gesehen": True}], e


def test_jede_wiedergabe_zaehlt_fuer_sich(tmp_path):
    """Die Sehzeit gehört zu EINER Wiedergabe: ⏭ nach 400 s in Folge e3 meldet
    e3 (unter 90 %: nur die Stelle). Die nächste Folge beginnt mit W = 0 und
    ihrer eigenen Startstelle — sofort ans Ende gesprungen ist sie NICHT gesehen
    (die 400 s der vorigen Folge zählen nicht mit)."""
    (e,) = _lauf(tmp_path, *_teile(), r"""
await start('e3',0); await schaue(400); await tvpFolge(1);
const vorige=koerper(), ziel=starts.at(-1); netz.length=0;
ID=EPS[1].id;                                               // filmePlay öffnet die nächste Folge
tvFilmPlayer(ID,'Dark · S1 F4',0,{typ:'folge', serie_id:'s9', titel:'Dark · S1 F4', laufzeit_min:40});
const v=video(); v.feuer('timeupdate'); spielen(v); await tvpTick();
await springe(D-5); await filmStopp();
aus({vorige, ziel, naechste:koerper()});
""")
    assert e["vorige"] == [{"id": "e3", "position_s": 400}], e
    assert e["ziel"] == "e3n@0", e
    assert e["naechste"] == [{"id": "e3n", "position_s": 0}], e


# --------------------------------------------- Jellyfin darf nicht selbst haken

def test_verweigert_meldet_die_stelle_unter_jellyfins_grenze(tmp_path):
    """Verweigerte Meldungen bringen Jellyfin nie selbst zum Haken (Orakel über
    alle möglichen Laufzeiten), und die Stelle ist die letzte ECHT geschaute
    unterhalb der Grenze. Die Grenze rechnet mit der kleinsten möglichen
    Jellyfin-Laufzeit (Dauer − 30 s, laufzeit_min ist gerundet): 0,9 × 2370 =
    2133 s.
    (a) echt über die Grenze geschaut (2120 → 2140), dann gesprungen: 2133.
    (b) erst hinter der Grenze echt geschaut (ab 2140): zählt nicht als Stelle,
        gemeldet wird die letzte echte davor (60 s) — „vor dem Sprung".
    (c) Mitte (1200 s, Esc): unverändert die Stelle selbst.
    (d) die Musik übernimmt den VLC bei 95 % (kein eigenes Ende, also kein
        „gesehen" wie bisher): die Stelle wird unter die Grenze begrenzt —
        vorher meldete die Seite 2300 s, und Jellyfin setzte den Haken selbst.
    (e) kurzes Stück (5 min): Jellyfin setzt unter 300 s Laufzeit schon ab 5 %
        „gespielt" — verweigert wird dort Stelle 0 gemeldet."""
    e = _lauf(tmp_path, *_teile(), r"""
const r={};
await start('e3',0); await schaue(10); await springe(2120); await schaue(2140); await springe(D-5);
await filmStopp(); r.a=koerper(); tvpWechsel=null;
await start('e3',0); await schaue(60); await springe(2140); await schaue(2170); await springe(D-5);
await filmStopp(); r.b=koerper(); tvpWechsel=null;
await start('e3',0); await schaue(1200); await filmStopp(); r.c=koerper(); tvpWechsel=null;
await start('e3',0,{vlc:true}); await schaue(2300);
vlcStatus={zustand:'spielt', key:'abc|mp3', pos:12, dauer:200}; await tvpTick();
r.d=koerper(); r.dOffen=tvpOffen;
await start('e3',0,{min:5}); await schaue(150); await filmStopp(); r.e=koerper(); r.eDauer=D;
aus(r);
""")
    (r,) = e
    assert r["a"] == [{"id": "e3", "position_s": 2133}], r["a"]
    assert r["b"] == [{"id": "e3", "position_s": 60}], r["b"]
    assert r["c"] == [{"id": "e3", "position_s": 1200}], r["c"]
    assert r["dOffen"] is False and r["d"] == [{"id": "e3", "position_s": 2133}], r["d"]
    assert r["e"] == [{"id": "e3", "position_s": 0}], r["e"]
    for k in (r["a"][0], r["b"][0], r["c"][0], r["d"][0]):
        _bleibt_offen(k, 2400)
    _bleibt_offen(r["e"][0], r["eDauer"])


# ------------------------------------------------------- Regel an EINER Stelle

def test_regel_steht_an_einer_stelle():
    """Die Zahlen der Regel stehen in EINER Konstante (mit JBs Idee und Datum im
    Kommentar darüber); die Bausteine selbst tragen keine eigenen Zahlen, und die
    Meldestelle rechnet nicht mehr mit einer eigenen 90-%-Grenze."""
    q = _pc()
    zeile = _js_zeile(q, "const SEHZEIT=")
    for teil in ("gesehenAb:0.9", "mindestS:300", "mindestAnteil:0.5", "sprungS:3",
                 "jfMaxResume:0.9", "jfKurzS:300", "jfSpielraumS:30"):
        assert teil in zeile, f"{teil} fehlt in {zeile}"
    kopf = q[max(0, q.index(zeile) - 2500):q.index(zeile)]
    assert "JB-Idee 24.09.2026" in kopf and "mindest timer" in kopf, "JBs Idee mit Datum über der Regel"
    for n in NEU:
        rumpf = _js_funktion(q, n)
        zahlen = [z for z in re.findall(r"(?<![\w.$])\d+(?:\.\d+)?(?![\w])", rumpf) if z != "0"]
        assert not zahlen, f"{n}: eigene Zahlen {zahlen} — sie gehören in SEHZEIT"
    assert "0.9" not in _js_funktion(q, "filmFortschrittMelden")
    assert "0.9" not in _js_funktion(q, "tvpFilmEnde")
    assert "sehzeitUrteil(" in _js_funktion(q, "filmFortschrittMelden"), "die EINE Meldestelle entscheidet"
    assert "tvpSehzeitZaehlen(" in _js_funktion(q, "tvpVideoVerdrahten"), "Browser: das <video> misst"
    assert "tvpSehzeitZaehlen(" in _js_funktion(q, "tvpTick"), "VLC: der 1-s-Takt misst"
