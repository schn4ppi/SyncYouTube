# -*- coding: utf-8 -*-
"""Medientasten: Randfälle aus der skeptischen Prüfung vom 24.09.2026.

Ein Prüf-Workflow (drei Blickwinkel, jeder Befund danach von einem
unabhängigen Widerleger angegriffen) fand 22 haltbare Randfälle im ersten
Wurf. Diese Datei nagelt sie fest — wieder mit dem ECHTEN JavaScript der
Seiten, ausgeführt mit deno (Hilfen aus test_medientasten_verhalten.py):

* Serien: ein zweiter ⏮ während die Vorfolge noch lädt, traf dieselbe Folge
  (JBs „2. Druck = Anfang" ging verloren); Esc während eines Folgenwechsels
  öffnete den Player danach von selbst wieder; die Folgenliste vergaß die
  Stelle nach Esc; eine leere Serverantwort legte ⏭/⏮ für die Sitzung lahm.
* Film: ein Sprung vom Overlay-Regler ging in etwa jedem vierten Fall
  verloren (der 1-s-Takt überschrieb das Ziel) und traf nach Esc die Musik.
* Server-Knöpfe (VLC): ein ⏭ wirkte in JEDER offenen Seite, die VLC abfragt;
  mehrere schnelle Drücke schrumpften zu einem; eine Musik-Kachel steuerte
  den Film.
* Tastatur: der keydown-Rückfall für MediaTrackPrevious war ungeprüft; J/L,
  Ziffern und Pos1 sprangen im Film in der unsichtbaren Musik.
* Crossfade-Abbruch ließ die Quelle stehen (toter Windows-Eintrag).
* Nachladen: ein fehlender Platzhalter lieferte eine tote Seite aus; eine
  Baustein-Änderung erreichte offene Tabs nie.
* Handy: Verdrahtung der Listener und die PC-Sperre waren ungeprüft; ▶ nach
  „Handy → PC → Handy" spielte ein Element ohne Quelle.
"""
import importlib
import os
import re
import sys

import pytest

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

from test_medientasten_verhalten import (  # noqa: E402
    MODUL_DIR, _block_ende, _handy, _js_funktion, _js_zeile, _lauf, _modul_js, _pc)

FOLGEN = r"""
const eps=[
 {id:'e1',staffel:1,folge:1,laufzeit_min:40,position_s:0,gesehen:true},
 {id:'e2',staffel:1,folge:2,laufzeit_min:40,position_s:1200,gesehen:false},
 {id:'e3',staffel:1,folge:3,laufzeit_min:40,position_s:0,gesehen:false},
 {id:'e4',staffel:1,folge:4,laufzeit_min:40,position_s:0,gesehen:false},
 {id:'e5',staffel:1,folge:5,laufzeit_min:40,position_s:0,gesehen:false}];
"""


def _film_kern():
    q = _pc()
    return [_js_zeile(q, "let tvpMedienGen")] + [_js_funktion(q, n) for n in (
        "tvpLandePos", "tvpZurueckZiel", "tvpWeiterZiel", "tvpBasis", "tvpFolgePosMerken",
        "tvpWechselStarten", "tvpZielAusfuehren", "tvpFolge", "tvpZurueck")]


FILM_STUBS = r"""
var tvpOffen=true, tvpModus='browser', tvpIdAkt='e3', tvpPos=600, tvpDauer=2400, tvInfoDaten=null;
const plays=[], seeks=[], merk=[];
function filmePlay(id,pos,gen){plays.push([id,pos,gen]); return new Promise(()=>{});}   // lädt „ewig"
async function tvpFolgenHolen(){return eps;}
function tvpBefehl(c,d){seeks.push([c,d&&d.wert]); return Promise.resolve({});}
function tvpTick(){} function tvpLadeZeigen(){} function zeit(s){return String(s);}
globalThis.fetch=(u,o)=>{merk.push([String(u), o&&o.body]); return Promise.resolve({json:async()=>({})});};
"""


# ------------------------------------------------------------- Serien-Wechsel

def test_zweiter_zurueck_waehrend_die_vorfolge_laedt(tmp_path):
    """JB-Regel Variante C: der 2. Druck führt an den Anfang der Vorfolge —
    auch wenn sie beim 2. Druck noch lädt (Detail-Abruf an Renés Server).
    Vorher rechneten beide Drücke von der ALTEN Folge aus und trafen dasselbe
    Ziel; die Regel verlor ihren Zustand."""
    (e,) = _lauf(tmp_path, FOLGEN, FILM_STUBS, *_film_kern(), r"""
await tvpZurueck(); const p1=[...plays[0]], n1=tvpModusNaechster&&tvpModusNaechster.modus;
await tvpZurueck(); const p2=[...plays[1]], n2=tvpModusNaechster&&tvpModusNaechster.modus;
await tvpZurueck(); const p3=[...plays[2]];
const gespeichert=merk.filter(m=>m[0].includes('fortschritt')).length;
aus({p1,n1,p2,n2,p3,gespeichert,gen:tvpWechselGen});
""")
    assert e["p1"][:2] == ["e2", 1200] and e["n1"] == "gelandet"
    assert e["p2"][:2] == ["e2", 0] and e["n2"] == "musik", "2. Druck: Anfang der Vorfolge"
    assert e["p3"][:2] == ["e1", 0], "3. Druck in den ersten 3 s: noch eine zurück"
    assert e["p1"][2] < e["p2"][2] < e["p3"][2] == e["gen"], "jeder Druck überholt den vorigen"
    assert e["gespeichert"] == 1, "die laufende Folge wird genau einmal gemerkt"


def test_zweimal_weiter_sind_zwei_folgen(tmp_path):
    (e,) = _lauf(tmp_path, FOLGEN, FILM_STUBS, *_film_kern(), r"""
await tvpFolge(1); await tvpFolge(1);
aus({ziele:plays.map(p=>p[0])});
""")
    assert e["ziele"] == ["e4", "e5"]


def test_esc_waehrend_des_folgenwechsels_oeffnet_nichts_mehr(tmp_path):
    """Vorher: filmePlay wartete auf /api/filme/detail, JB drückte Esc (Film
    zu), danach öffnete sich die neue Folge über der geschlossenen Ansicht."""
    q = _pc()
    (e,) = _lauf(tmp_path, r"""
var tvInfoDaten=null, tvpOffen=true, tvpModus='browser', tvpTc=false, tvpTcVcopy=false, tvpWechselGen=1;
const auf=[], vlc=[]; let antworte;
globalThis.fetch=()=>new Promise(r=>{antworte=()=>r({json:async()=>({id:'F4',titel:'Vier',video_codec:'h264',audio_codec:'aac'})});});
function filmeBrowserKann(){return true;} function tvFilmPlayer(id){auf.push(id);}
function vlcBefehl(c){vlc.push(c);} async function filmePlayVlc(){vlc.push('filmePlayVlc');}
""", _js_funktion(q, "filmePlay"), r"""
const p=filmePlay('F4',0,1);
tvpWechselGen=2; tvpOffen=false;           // Esc: filmStopp überholt den Wechsel
antworte(); await p;
const p2=filmePlay('F5',0,3); tvpWechselGen=3; tvpOffen=true; antworte(); await p2;   // gültiger Wechsel
const p3=filmePlay('F6',0); antworte(); await p3;                                   // normaler Start
aus({auf, vlc});
""")
    assert e["auf"] == ["F5", "F6"], e
    fp = _js_funktion(q, "filmePlayVlc")
    assert "tvpWechselGen" in fp, "auch der VLC-Weg muss überholte Wechsel verwerfen"
    # Nur Esc (filmStopp) bricht einen ladenden Wechsel ab — Folgenende und
    # Selbstheilung der ALTEN Folge dürfen den ausdrücklichen Druck nicht schlucken.
    fs = _js_funktion(q, "filmStopp")
    assert "tvpWechselGen++" in fs and "tvpWechsel=null" in fs
    assert "tvpWechselGen++" not in _js_funktion(q, "tvpZu")


def test_gescheiterter_wechsel_bleibt_nicht_haengen(tmp_path):
    """Scheitert das Öffnen der Zielfolge (VLC meldet einen Fehler oder ist
    nicht erreichbar), darf der Wechsel nicht „ausstehend" bleiben — sonst
    rechnete jeder weitere ⏭/⏮ von einer Folge aus, die nie aufging."""
    q = _pc()
    (e,) = _lauf(tmp_path, r"""
var tvpWechselGen=2, tvpWechsel={gen:2,id:'F4',pos:0,modus:'normal'}, tvpModusNaechster=null, tvInfoDaten=null, plVol=4, tvpOffen=true, tvpModus='vlc';
const toasts=[];
function toast(t){toasts.push(t);} function vlcBefehl(){} function tvFilmPlayer(){}
globalThis.fetch=async()=>({json:async()=>({fehler:'Datei nicht gefunden'})});
""", _js_funktion(q, "filmePlayVlc"), r"""
tvpModusNaechster={id:'F4',modus:'gelandet'};
await filmePlayVlc('F4',0,{titel:'Vier'},2);
const a=tvpWechsel, naechster=tvpModusNaechster;
tvpWechsel={gen:3,id:'F5',pos:0,modus:'normal'}; tvpWechselGen=3;
globalThis.fetch=async()=>{throw new Error('Netz weg');};
await filmePlayVlc('F5',0,{titel:'Fünf'},3);
aus({a, b:tvpWechsel, toasts, naechster});
""")
    assert e["a"] is None and e["b"] is None, e
    assert e["naechster"] is None, "ein gescheiterter Wechsel vererbt seinen Zurück-Modus nicht"
    assert len(e["toasts"]) == 2


def test_folgenliste_merkt_die_stelle_nach_esc(tmp_path):
    """Vorher: filmStopp schrieb die Stelle nur in die Info-Seite der SERIE;
    die Folgenliste (Info-Seite bzw. Zwischenspeicher) blieb alt, ⏮ landete
    danach am Anfang statt an der gemerkten Stelle."""
    q = _pc()
    (e,) = _lauf(tmp_path, FOLGEN, _js_zeile(q, "let tvpMedienGen"),
                 _js_funktion(q, "tvpFolgePosMerken"), r"""
var tvInfoDaten={d:{id:'s9'}, eps:JSON.parse(JSON.stringify(eps))};
tvpFolgenCache={sid:'s9', eps:JSON.parse(JSON.stringify(eps))};
tvpFolgePosMerken('e4',1200);
aus({info:tvInfoDaten.eps[3].position_s, cache:tvpFolgenCache.eps[3].position_s});
""")
    assert e == {"info": 1200, "cache": 1200}
    assert "tvpFolgePosMerken(" in _js_funktion(q, "tvpZu"), "der eine Ausgang merkt die Stelle"


def test_leere_folgenliste_wird_nicht_festgeschrieben(tmp_path):
    """filme.episoden() antwortet bei jedem Jellyfin-Fehler mit einer leeren
    Liste (HTTP 200). Die durfte nicht für die ganze Sitzung gelten — und ⏮
    auf eine Folge, die nicht in der Liste steht, darf sie nicht neu starten."""
    q = _pc()
    (e,) = _lauf(tmp_path, FOLGEN, _js_zeile(q, "let tvpMedienGen"),
                 _js_funktion(q, "tvpFolgenHolen"), _js_funktion(q, "tvpLandePos"),
                 _js_funktion(q, "tvpZurueckZiel"), r"""
var tvInfoDaten=null, tvpMeta={typ:'folge', serie_id:'s9'};
globalThis.fetch=async()=>({json:async()=>({items:[]})});
const r=await tvpFolgenHolen();
aus({r, cache:tvpFolgenCache, fremd:tvpZurueckZiel(eps,'x',2400,'normal')});
""")
    assert e == {"r": None, "cache": None, "fremd": None}


def test_film_sprung_geht_nicht_verloren_und_trifft_nach_esc_nichts(tmp_path):
    """Vorher las der verzögerte Sprung die GLOBALE Position — lief der
    1-s-Takt dazwischen (≈ jeder vierte Fall), sprang der Film an die alte
    Stelle; nach Esc ging der Sprung als VLC-Befehl an die Musik."""
    q = _pc()
    (e,) = _lauf(tmp_path, _js_zeile(q, "let tvpMedienGen"), FILM_STUBS,
                 _js_funktion(q, "tvpSpringeAuf"), r"""
tvpSpringeAuf(1800); tvpPos=600;                    // der Takt überschreibt dazwischen
await new Promise(r=>setTimeout(r,350));
tvpSpringeAuf(900); tvpOffen=false;                 // Esc innerhalb von 250 ms
await new Promise(r=>setTimeout(r,350));
aus({seeks});
""")
    assert e["seeks"] == [["seek", 1800]], e["seeks"]
    assert "clearTimeout(_tvpSprungTimer)" in _js_funktion(q, "tvpZu")


def test_film_merkt_seinen_schluessel_sofort_und_heilt_mit_regel():
    """Esc direkt nach einem Folgenwechsel nahm den alten Schlüssel (erst der
    Takt zog ihn nach) und überschrieb die Stelle der VORIGEN Folge. Die
    Selbstheilung Browser -> VLC setzte JBs Zurück-Modus zurück."""
    q = _pc()
    fp = _js_funktion(q, "tvFilmPlayer")
    assert "vlcKeyLetzter=" in fp
    assert "tvpVideoVerdrahten(v,id,pos)" in fp, "das Film-Video braucht seine Listener"
    vd = _js_funktion(q, "tvpVideoVerdrahten")
    i = vd.index("filmePlayVlc(id,pos")
    assert "tvpModusNaechster={id" in vd[vd.rindex("\n", 0, i - 200):i], \
        "vor dem VLC-Rückfall den Zurück-Modus weiterreichen"


# ------------------------------------------------------------- Server-Knöpfe

def test_server_knoepfe_nur_fuer_die_seite_der_sie_gehoeren(tmp_path):
    """Jede Seite, die /api/vlc abfragt, sieht den Zähler. Handeln darf nur
    die Seite, deren Titel bzw. Film der VLC gerade spielt — vorher schaltete
    ein zweiter offener Tab mit und übernahm den gemeinsamen VLC. Mehrere
    schnelle Drücke sind mehrere Schritte."""
    q = _pc()
    (e,) = _lauf(tmp_path, _js_zeile(q, "let _smtcTasteN"), _js_funktion(q, "smtcTaste"), r"""
var tvpOffen=false, tvpIdAkt='', plGeraet='vlc'; let akt='k1';
const calls=[];
function vlcAktiv(){return plGeraet==='vlc';} function aktKey(){return akt;}
function playerSchritte(n){calls.push('musik'+n);}
async function tvpFolge(d){calls.push('film+');} async function tvpZurueck(){calls.push('film-');}
const S=(key,n,vor,zur)=>smtcTaste({key,smtc:true,taste:{n,was:'',vor,zurueck:zur}});
await S('k1',3,2,1);             // erster Stand: merken
await S('k1',4,3,1);             // ⏭ auf meine Musik
await S('k9',5,4,1);             // fremder Titel: nichts
await S('k1',7,4,3);             // zwei schnelle ⏮: ein Wechsel um zwei
await S('k1',9,5,4);             // ⏭ und gleich ⏮: heben sich auf
tvpOffen=true; tvpIdAkt='F2';
await S('film:F2',10,6,4);       // mein Film
await S('k1',11,6,5);            // Musik-Kachel bei offenem Film: die Tasten gehören dem Film (JB)
await S('film:F7',12,7,5);       // fremder Film: nichts
await smtcTaste({key:'k1',smtc:true,taste:{n:1,was:'',vor:1,zurueck:0}});   // Server neu gestartet: nur merken
await smtcTaste({key:'film:F2',smtc:true,taste:{n:2,was:'next'}});         // älterer Server ohne Richtungszähler
aus({calls});
""")
    assert e["calls"] == ["musik1", "musik-2", "film+", "film-", "film+"], e["calls"]


# ------------------------------------------------------------- Tastatur

def _keydown(q):
    i = q.index("document.addEventListener('keydown',e=>{")
    auf = q.index("{", i + len("document.addEventListener('keydown',e=>"))
    return "function kd(e){" + q[auf + 1:_block_ende(q, auf)] + "}"


def test_keydown_rueckfall_und_hotkeys_folgen_der_weiche(tmp_path):
    """Der keydown-Rückfall wird AUSGEFÜHRT (vorher prüfte ein Zeichenfenster
    nur die Nachbarzeile — MediaTrackPrevious war blind).

    Echte Tastendrücke am 24.09.2026 zeigten: Hat das Fenster den Fokus, kommt
    eine Medientaste ZWEIMAL an — über Windows an die aktuelle Sitzung UND als
    keydown in der Seite. VLC-⏯ pausierte am Server und die Seite schaltete
    sofort zurück; VLC-⏭ sprang zwei Titel; 2× ⏮ in der Serie wurden drei
    Schritte. Die 400-ms-Sperre greift nicht (der Windows-Weg ist langsamer).
    Darum wirkt der keydown-Rückfall NUR, wenn es keine SyncYouTube-Sitzung bei
    Windows gibt, die die Taste ohnehin bekommt. J/L/Ziffern/Pos1/K/N/P (keine
    Medientasten) gehören bei offenem Film dem Film."""
    q = _pc()
    teile = [_js_zeile(q, "let _medienLetzte"), _js_zeile(q, "let tvpAbgeloest")] + [_js_funktion(q, n) for n in (
        "filmTasten", "medienEinmal", "medienWeiter", "medienZurueck", "medienTasteHatSitzung")] + [_keydown(q)]
    (e,) = _lauf(tmp_path, *teile, r"""
var tvpOffen=false, tvpModus='browser', tvpDauer=3000, libPlaylistView=false, libAuswahl=new Set(), _hkFang=null;
var plGeraet='browser', vlcSmtc=false;
const calls=[];
const HKMAP={KeyK:'playpause',KeyJ:'rueck10',KeyL:'vor10',KeyN:'naechster',KeyP:'voriger',Home:'anfang',End:'ende'};
function hkCode(e){return e.code;} function hkAktionFuer(c){return HKMAP[c]||'';}
function sprungWeite(){return 5;} function plTogglePlay(){calls.push('musik-pp');}
function vlcAktiv(){return plGeraet==='vlc';} function plbSpringen(s){calls.push('musik-spring:'+s);}
function playerNext(){calls.push('musik+');} function playerPrev(){calls.push('musik-');}
function tvpFolge(d){calls.push('film+');} function tvpZurueck(){calls.push('film-');}
function tvpBefehl(c){calls.push('film-'+c);} function tvpTick(){}
function tvpRel(s){calls.push('film-spring:'+s);} function tvpSpringeAuf(t){calls.push('film-auf:'+t);}
function tastenLegende(){} function _vol(){} function _rate(){}
_els['pl-el']=fakeMedia({id:'pl-el',duration:200,currentTime:50});      // ohne Quelle: keine Seiten-Sitzung
const T=c=>kd({code:c,key:c,target:null,ctrlKey:false,metaKey:false,altKey:false,shiftKey:false,preventDefault(){}});
let t=1000; Date.now=()=>(t+=1000);
const MEDIEN=['MediaTrackNext','MediaTrackPrevious','MediaPlayPause'];
for(const c of [...MEDIEN,'KeyL'])T(c);
const ohneSitzung=[...calls]; calls.length=0;
_els['pl-el'].src='/media?id=k1'; _els['pl-el'].played={length:0};     // Quelle, aber nie gespielt (nach Neuladen)
T('MediaPlayPause'); const nieGespielt=[...calls]; calls.length=0;
_els['pl-el'].played={length:1};                                         // hat gespielt: Seiten-Sitzung bei Windows
for(const c of MEDIEN)T(c);
_els['pl-el'].played={length:0}; _els['pl-el'].paused=false;            // spielt gerade
T('MediaTrackNext');
const mitSitzung=[...calls]; calls.length=0;
_els['pl-el'].src=''; _els['pl-el'].paused=true; plGeraet='vlc'; vlcSmtc=true;   // VLC mit Server-Sitzung
for(const c of MEDIEN)T(c);
const vlcServer=[...calls]; calls.length=0;
vlcSmtc=false;                                                           // VLC ohne Server-Sitzung (winrt fehlt)
T('MediaTrackNext'); const vlcOhne=[...calls]; calls.length=0;
plGeraet='browser'; tvpOffen=true;                                       // Browser-Film: Seiten-Sitzung
_els['tvp-video']=fakeMedia({id:'tvp-video',src:'/media?id=f1',paused:false});
for(const c of [...MEDIEN,'KeyL','KeyJ','Home','Digit5','KeyN','KeyP','KeyK','End'])T(c);
const film=[...calls], plZeit=_els['pl-el'].currentTime; calls.length=0;
delete _els['tvp-video']; tvpOffen=false;
t+=1000; Date.now=()=>t; medienEinmal('next','ms'); T('MediaTrackNext');          // kein Sitz, aber Windows war schneller
aus({ohneSitzung, nieGespielt, mitSitzung, vlcServer, vlcOhne, film, plZeit, doppelt:[...calls]});
""")
    assert e["ohneSitzung"] == ["musik+", "musik-", "musik-pp", "musik-spring:10"], e["ohneSitzung"]
    assert e["nieGespielt"] == ["musik-pp"], "Chromium meldet erst nach dem ersten Ton an — bis dahin wirkt der Rückfall"
    assert e["mitSitzung"] == [], "Windows gibt die Taste der Seiten-Sitzung — kein zweiter Schritt"
    assert e["vlcServer"] == [], "Windows gibt die Taste der Server-Sitzung — kein zweiter Schritt"
    assert e["vlcOhne"] == ["musik+"], "ohne Server-Sitzung bleibt der Rückfall der einzige Weg"
    assert e["film"] == ["film-spring:10", "film-spring:-10", "film-auf:0", "film-auf:1500",
                         "film+", "film-", "film-toggle"], e["film"]
    assert e["plZeit"] == 50, "die Musik unter dem Film bleibt unberührt"
    assert e["doppelt"] == [], "keydown hinter dem Windows-Druck wird geschluckt"


def test_tasten_gehoeren_dem_film_auch_wenn_er_im_vlc_laeuft(tmp_path):
    """JB 23.09.2026: „Musik läuft weiter, die Tasten gehören dem Film." Auch
    wenn der Film im VLC läuft und die Browser-Kachel wegen der Musik existiert,
    steuert sie den Film und zeigt ihn; ein Musik-Titelwechsel überschreibt sie
    nicht — die Server-Kachel des VLC bekommt ihre Angaben aber weiter.
    (Die Zwischenfassung „jede Kachel steuert, was sie zeigt" widersprach der
    Regel: Windows gab die Tasten dann je nach Laune der Musik.)"""
    q = _pc()
    teile = [_modul_js(), _js_zeile(q, "const medienS="), _js_zeile(q, "let _medienLetzte"),
             _js_zeile(q, "let _medienAngemeldet"), _js_zeile(q, "let _smtcTasteN")] + [_js_funktion(q, n) for n in (
        "filmTasten", "medienEinmal", "medienPlay", "medienPause", "medienSpringe", "medienRelativ",
        "medienWeiter", "medienZurueck", "_msPlay", "_msPause", "_msWeiter", "_msZurueck",
        "medienTastenAnmelden", "medienInfoSetzen")]
    (e,) = _lauf(tmp_path, *teile, r"""
var tvpOffen=true, tvpModus='vlc', vlcSpielt=true, plGeraet='vlc', playerState={quelle:''};
const calls=[], server=[];
function vlcAktiv(){return true;} function playerNext(){calls.push('musik+');} function playerPrev(){}
function tvpFolge(){calls.push('film+');} function tvpZurueck(){} function tvpMedien(w){calls.push('film-'+w);}
function tvpRel(){} function tvpSpringeAuf(){} function plbSpringen(){} function plTogglePlay(){calls.push('musik-pp');}
function vlcBefehl(c,d){server.push([c,d&&d.key]);}
medienTastenAnmelden(); _FAKE.handler.nexttrack(); _FAKE.handler.pause();
_FAKE.metadata={title:'Film'};
medienInfoSetzen({titel:'Song',uploader:'K'},'k1');
aus({kachel:[...calls], meta:_FAKE.metadata&&_FAKE.metadata.title, server});
""")
    assert e["kachel"] == ["film+", "film-pause"], e
    assert e["meta"] == "Film", "ein Musik-Titelwechsel überschreibt die Film-Kachel nicht"
    assert ["medien", "k1"] in e["server"], "die Server-Kachel des VLC bekommt die Musik-Angaben weiter"


# ------------------------------------------------------------- Crossfade

def test_crossfade_abbruch_gibt_das_element_frei(tmp_path):
    q = _pc()
    (e,) = _lauf(tmp_path, _modul_js(), _js_zeile(q, "const medienS="), r"""
let xfNext=fakeMedia({id:'xf',src:'/media?id=2',paused:false}); var vizGain=null; const alt=xfNext;
""", _js_funktion(q, "xfAbbrechen"), r"""
xfAbbrechen();
aus({xfNext, src:alt.src, paused:alt.paused});
""")
    assert e == {"xfNext": None, "src": "", "paused": True}


# ------------------------------------------------------------- Nachladen

def test_nachladen_mit_kaputtem_platzhalter_behaelt_die_alte_seite(monkeypatch):
    """Vorher: reload band HTML zuerst an die Rohvorlage, dann warf das
    Einsetzen — youtube_app schluckte den Fehler und lieferte eine Seite ohne
    Baustein aus (ReferenceError, Oberfläche tot)."""
    import medien_session
    import oberflaeche
    alt = oberflaeche.HTML

    def kaputt(html):
        raise ValueError("Platzhalter fehlt (Testfall)")
    monkeypatch.setattr(medien_session, "einsetzen", kaputt)
    with pytest.raises(ValueError):
        importlib.reload(oberflaeche)
    assert oberflaeche.HTML is alt, "die ausgelieferte Seite muss die alte, heile bleiben"
    monkeypatch.undo()
    importlib.reload(oberflaeche)
    assert "function medienSitzung(" in oberflaeche.HTML


def test_baustein_wird_heiss_nachgeladen():
    """Eine Änderung am Baustein muss offene Tabs erreichen: er wird mit der
    Oberfläche nachgeladen, und der Stand der Oberfläche zählt ihn mit."""
    quelle = open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    m = re.search(r"_HEISS_NACHLADBAR = \{([^}]*)\}", quelle)
    assert m and "medien_session.py" in m.group(1)
    for seite in ("handy", "oberflaeche"):
        i = quelle.index(f"importlib.reload({seite})")
        vorher = quelle[quelle.rindex("try:", 0, i) - 200:i]
        assert "importlib.reload(medien_session)" in vorher, f"{seite}: Baustein nicht vorher nachgeladen"
    j = quelle.index("ui_stand = ")
    assert "medien_session.py" in quelle[j:j + 400]


# ------------------------------------------------------------- Handy

HANDY_STUBS = r"""
var CODE='C0DE', dev='handy', aktuell=null;
var daten=[{id:'k1',titel:'Eins',uploader:'K',thumb:'',vorhanden:true},{id:'k2',titel:'Zwei',uploader:'K',thumb:'',vorhanden:true}];
const remoteCalls=[];
function remote(c){remoteCalls.push(c); return Promise.resolve();}
async function api(){return {ok:true};}
const _hoerer={};
_els.el=fakeMedia({id:'el', addEventListener(t,f){(_hoerer[t]=_hoerer[t]||[]).push(f);}});
function feuer(t){(_hoerer[t]||[]).forEach(f=>f());}
_els.suche={value:''}; _els.nowtitel={}; _els.nowsub={}; _els.pp={textContent:'▶'};
_els['dev-pc']={classList:{toggle(){}}}; _els['dev-handy']={classList:{toggle(){}}}; _els.vol={style:{}}; _els.tipp={};
"""


def _handy_alles():
    h = _handy()
    namen = ("esc", "libFind", "aktuelleListe", "setDev", "spiel", "steuer", "handyNachbar",
             "handyEnde", "handyMedienInfo", "handyMedienAnmelden")
    m = re.search(r"^const _el=document\.getElementById\('el'\);$.*?^handyMedienAnmelden\(\);$", h,
                  re.M | re.S)
    assert m, "Listener-Block der Handy-Seite nicht gefunden"
    return [_modul_js(), _js_zeile(h, "const medienS=")] + [_js_funktion(h, n) for n in namen] + [m.group(0)]


def test_handy_verdrahtung_und_pc_sperre(tmp_path):
    """Die echten Listener laufen mit: im Modus „PC" löst ein Titelende nichts
    am PC aus und meldet keinen Zustand; jeder Sperrbildschirm-Knopf bleibt im
    PC-Modus wirkungslos (vorher nur mit dev='handy' geprüft — blind)."""
    (e,) = _lauf(tmp_path, HANDY_STUBS, *_handy_alles(), r"""
spiel('k1'); setDev('pc');
feuer('ended'); feuer('pause');
const nachPc={remote:[...remoteCalls], z:_FAKE.playbackState};
for(const a of ['nexttrack','previoustrack','play','pause','stop'])_FAKE.handler[a]();
_FAKE.handler.seekto({seekTime:9});
aus({nachPc, danach:{remote:[...remoteCalls], src:_els.el.src, t:_els.el.currentTime}});
""")
    assert e["nachPc"] == {"remote": [], "z": "none"}, e
    assert e["danach"] == {"remote": [], "src": "", "t": 0}, e


def test_handy_play_nach_pc_umweg_startet_den_titel_neu(tmp_path):
    """Handy -> PC -> Handy: das Element ist freigegeben (keine Quelle). ▶
    spielte vorher ins Leere und zeigte trotzdem ⏸."""
    (e,) = _lauf(tmp_path, HANDY_STUBS, *_handy_alles(), r"""
spiel('k2'); setDev('pc'); setDev('handy');
steuer('pp');
const a={src:_els.el.src, paused:_els.el.paused};
aktuell=null; _els.el.pause(); _els.el.removeAttribute('src'); _els.pp.textContent='▶'; steuer('pp');
aus({a, ohneTitel:{pp:_els.pp.textContent, paused:_els.el.paused}});
""")
    assert "id=k2" in e["a"]["src"] and e["a"]["paused"] is False, e
    assert e["ohneTitel"] == {"pp": "▶", "paused": True}, e


def test_baustein_meldet_uebrige_knoepfe_auch_wenn_einer_wirft(tmp_path):
    """Kernversprechen des Bausteins: ein Browser, der eine Aktion nicht kennt,
    wirft bei setActionHandler — die übrigen Knöpfe müssen trotzdem ankommen."""
    (e,) = _lauf(tmp_path, _modul_js(), r"""
const orig=_FAKE.setActionHandler.bind(_FAKE);
_FAKE.setActionHandler=(n,f)=>{if(n==='stop'||n==='seekto')throw new TypeError('unbekannt'); orig(n,f);};
const s=medienSitzung(()=>null);
s.aktionen({play:()=>1, stop:()=>1, nexttrack:()=>1, seekto:()=>1, previoustrack:()=>1});
aus({da:Object.keys(_FAKE.handler).sort()});
""")
    assert e["da"] == ["nexttrack", "play", "previoustrack"], e



# ------------------------------------------------------ Gegenprüfung, Runde 2

TAKT_STUBS = r"""
var tvpOffen=true, tvpIdAkt='e3', tvpModus='vlc', tvpLief=true, tvpTicks=3, tvpPos=0, tvpDauer=0,
    tvpWechsel=null, tvInfoOffen=false, vlcKeyLetzter='k1', vlcSpielt=true;
const zu=[]; let antwort=null, halte=null;
function tvpBefehl(c){return new Promise(r=>{ if(halte){halte.push(()=>r(antwort));} else r(antwort); });}
function tvpZu(){zu.push(tvpIdAkt);} function tvpIdleTick(){} function tvpMedienZustand(){}
function ico(){return '';} function zeit(s){return String(s);} function tvInfoMalen(){}
"""


def test_takt_haelt_den_folgenwechsel_nicht_fuer_das_ende(tmp_path):
    """Gegenprüfung (hoch): Beim Folgenwechsel im VLC meldet der Server den
    Anlauf der NEUEN Folge als 'aus' — der Takt hielt das für das Ende der
    alten, schloss den Player, und der Wechsel wurde verworfen (Film weg).
    Dazu: eine Antwort, die vor einem Wechsel abgeschickt wurde, überschrieb
    danach Schlüssel und Stelle der neuen Folge."""
    q = _pc()
    (e,) = _lauf(tmp_path, TAKT_STUBS, _js_funktion(q, "tvpTick"), r"""
tvpWechsel={gen:2,id:'e4'}; antwort={zustand:'aus', key:'film:e4', pos:1, dauer:0};
await tvpTick(); const a={zu:[...zu]};
tvpWechsel=null; halte=[]; antwort={zustand:'spielt', key:'film:e3', pos:1500, dauer:2400};
const t=tvpTick(); tvpIdAkt='e4'; vlcKeyLetzter='film:e4'; halte.forEach(f=>f()); await t;
const b={zu:[...zu], pos:tvpPos, key:vlcKeyLetzter};
halte=null; tvpIdAkt='e3'; antwort={zustand:'aus', key:'film:e3', pos:2399, dauer:2400};
await tvpTick(); const c={zu:[...zu]};
zu.length=0; tvpModus='browser'; vlcKeyLetzter='k1'; vlcSpielt=true;
antwort={zustand:'pause', key:'film:e3', pos:10, dauer:2400};
await tvpTick(); const d={key:vlcKeyLetzter, spielt:vlcSpielt, zu:[...zu]};
tvpWechsel={gen:5,id:'e4'}; antwort={zustand:'aus', key:'', pos:0, dauer:0};   // Browser: alte Folge endet, neue lädt
await tvpTick(); const f={zu:[...zu]};
aus({a,b,c,d,f});
""")
    assert e["f"]["zu"] == [], "Folgenende während eines ladenden Wechsels schließt nicht (der Druck bleibt gültig)"
    assert e["a"]["zu"] == [], "Anlauf der neuen Folge ist kein Ende"
    assert e["b"] == {"zu": [], "pos": 0, "key": "film:e4"}, "veraltete Antwort verworfen"
    assert e["c"]["zu"] == ["e3"], "das echte Ende schließt weiterhin"
    assert e["d"] == {"key": "k1", "spielt": True, "zu": []}, \
        "Browser-Film: der Geräte-VLC gehört der Musik, der Film-Takt schreibt ihn nicht"


def test_ueberholter_vlc_start_wird_angehalten(tmp_path):
    """Gegenprüfung (mittel): ⏭ auf eine VLC-Folge, dann schnell ⏭ auf eine
    Browser-Folge — der überholte VLC-Start lief unsichtbar weiter. Er wird
    angehalten, wenn der VLC noch IHN spielt und das Ziel eine andere Folge ist."""
    q = _pc()
    (e,) = _lauf(tmp_path, r"""
var tvpWechselGen=2, tvpWechsel={gen:2,id:'F4'}, tvpModusNaechster=null, tvInfoDaten=null, plVol=4, tvpOffen=true, tvpModus='browser', tvpIdAkt='F3';
const befehle=[]; let serverKey='film:F4', neuesZiel='F5';
function toast(){} function tvFilmPlayer(){befehle.push('auf');}
async function vlcBefehl(c){befehle.push(c); return {key:serverKey};}
// Während der VLC-Start (POST) läuft, kommt der nächste Druck: neue Generation, neues Ziel
globalThis.fetch=async()=>{tvpWechselGen=3; tvpWechsel={gen:3,id:neuesZiel}; return {json:async()=>({ok:true})};};
""", _js_funktion(q, "filmePlayVlc"), r"""
await filmePlayVlc('F4',0,{titel:'Vier'},2);                       // überholt, VLC spielt noch F4
const a=[...befehle]; befehle.length=0;
tvpWechselGen=2; tvpWechsel={gen:2,id:'F4'}; neuesZiel='F4';
await filmePlayVlc('F4',0,{titel:'Vier'},2);                       // überholt, aber dieselbe Folge ist Ziel
const b=[...befehle];
aus({a,b});
""")
    assert e["a"] == ["status", "stop"], e
    assert e["b"] == [], "dieselbe Folge als neues Ziel wird nicht angehalten"


def test_selbstheilung_und_esc_mit_der_offenen_folge():
    """Gegenprüfung: die Selbstheilung setzt den Zurück-Modus NACH tvpZu (das
    ihn räumt); Fehler des alten Videos während eines Wechsels werden
    ignoriert; der Ausgang räumt einen liegengebliebenen Modus."""
    q = _pc()
    vd = _js_funktion(q, "tvpVideoVerdrahten")          # die Listener des Film-Videos
    i = vd.index("filmePlayVlc(id,pos")
    abschnitt = vd[vd.rindex("addEventListener('error'", 0, i):i]
    assert abschnitt.index("tvpZu()") < abschnitt.index("tvpModusNaechster={id"), abschnitt
    assert "tvpWechsel" in abschnitt and "tvpIdAkt!==id" in abschnitt, \
        "Fehler des alten Videos während eines Wechsels dürfen nichts auslösen"
    assert "tvpModusNaechster=null" in _js_funktion(q, "tvpZu")


def test_esc_speichert_die_offene_folge(tmp_path):
    """Gegenprüfung (hoch): Mit Gerät VLC schrieb der Geräte-Takt den
    Musik-Schlüssel dazwischen — Esc speicherte die Stelle dann unter der
    falschen Kennung oder tat gar nichts. filmStopp nimmt jetzt die offene Folge."""
    q = _pc()
    (e,) = _lauf(tmp_path, r"""
var tvpOffen=true, tvpIdAkt='F9', tvpPos=1234, vlcKeyLetzter='k1', vlcSpielt=true, tvFilmReihen=null,
    tvInfoDaten=null, tvInfoOffen=true, tvpWechselGen=1, tvpWechsel=null, tvpModusNaechster=null, tvpMeta=null;
const merk=[], vlc=[], zu=[];
globalThis.fetch=(u,o)=>{merk.push(JSON.parse(o.body)); return Promise.resolve({});};
function tvpBefehl(){} function vlcBefehl(c){vlc.push(c);} function tvpZu(){zu.push(1); tvpOffen=false;}
function toast(){} function zeit(s){return String(s);} function vlcPosGeschaetzt(){return 0;} function tvInfo(){}
""", _js_funktion(q, "filmLaeuft"), _js_funktion(q, "filmStopp"), r"""
const laeuft=filmLaeuft(); await filmStopp();
const film={merk:[...merk], zu:zu.length, laeuft};
tvpOffen=true; tvpIdAkt=''; vlcKeyLetzter='k1'; zu.length=0; merk.length=0;
await filmStopp();
aus({film, live:{vlc, zu:zu.length, merk:merk.length}});
""")
    assert e["film"] == {"merk": [{"id": "F9", "position_s": 1234}], "zu": 1, "laeuft": True}, e
    assert e["live"] == {"vlc": ["stop"], "zu": 1, "merk": 0}, e


def test_mehrere_server_druecke_sind_ein_wechsel(tmp_path):
    """Gegenprüfung: mehrere ⏭ zwischen zwei Abfragen starteten jeden
    Zwischentitel mit eigenem VLC-Befehl (Reihenfolge am Server nicht fest).
    Jetzt EIN Wechsel ans Ziel; ein einzelner Druck bleibt playerNext/Prev."""
    q = _pc()
    (e,) = _lauf(tmp_path, r"""
var radioAktiv=false, playerState={idx:2, queue:['a','b','c','d','e','f','g']};
const calls=[];
function queueIdxPassend(i,r){return (i>=0&&i<playerState.queue.length)?i:-1;}
function renderPlayerMedia(){calls.push('render:'+playerState.idx);}
function playerNext(){calls.push('next');} function playerPrev(){calls.push('prev');}
function radioNachfuellen(){calls.push('radio');}
""", _js_funktion(q, "playerSchritte"), r"""
playerSchritte(1); playerSchritte(-1); playerSchritte(3); playerSchritte(-9);
radioAktiv=true; playerSchritte(2);
aus({calls});
""")
    assert e["calls"] == ["next", "prev", "render:5", "render:0", "radio", "render:2"], e["calls"]
