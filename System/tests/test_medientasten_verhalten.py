# -*- coding: utf-8 -*-
"""Medientasten: VERHALTEN statt Schreibweise (Leitplanke P6).

Hintergrund (23.09.2026): Die Media Session der Oberfläche ist live gemessen —
echte Tastendrücke in Edge, Firefox und der Programm-Hülle schalten den
Musik-Player weiter. Dabei und in der Code-Analyse fielen Wechselwirkungen auf,
die diese Datei festnagelt:

* Der Film-Player hatte KEINE eigene Anbindung. Die Musik-Handler galten auch
  bei offenem Film: „Weiter" legte einen Musiktitel unter den Film, Play
  startete die Musik, Spulen spulte die Musik.
* Im Geräte-Modus VLC schickte die Play-Taste `play` ohne Titel (Server:
  „Datei nicht gefunden"); Spulen lief ins Leere. Live gemessen: Weil der
  Zustand dort nie gepflegt wurde, sandte Windows bei Play/Pause immer „play" —
  VLC ließ sich per Taste nicht anhalten.
* JBs Zurück-Regel für Serien (JB 23.09.2026, Variante C, x = 3 s):
  1. Druck = Vorfolge an ihrer gemerkten Stelle (zu Ende geschaut: Anfang),
  2. Druck = Anfang dieser Folge, ab da wie beim Musik-Player.
* Die Handy-Seite bekommt den gemeinsamen Baustein (Sperrbildschirm); nebenbei
  schaltete ein Titelende am Handy den PC weiter, obwohl auf „PC" umgestellt war.

Ausgeführt wird das ECHTE JavaScript mit der geliehenen JS-Laufzeit aus
`System/bin` (deno, dieselbe wie für yt-dlp) — gegen eine Attrappe von
`navigator.mediaSession`, die jede Handler-Anmeldung, jede Metadaten-Zuweisung
und jeden `setPositionState`-Ruf mitschreibt. Fehlt deno, wird übersprungen
statt still grün zu behaupten.

Nicht hier gemessen (P6 verlangt die Liste): ob Windows/Android/iOS die
Metadaten wirklich anzeigen, welche Sitzung Windows die Tasten gibt, und das
Zusammenspiel mit dem Server-Teil (pywinrt). Das ist live gemessen bzw. steht
in tests/test_medien_smtc.py.
"""
import json
import os
import re
import subprocess
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

DENO = os.path.join(MODUL_DIR, "bin", "deno.exe")

# Attrappe: protokolliert alles, was die Seite an navigator.mediaSession tut.
UMGEBUNG = r"""
globalThis.window = globalThis;
const _log = [];
class MediaMetadata { constructor(m){ Object.assign(this, JSON.parse(JSON.stringify(m||{}))); } }
globalThis.MediaMetadata = MediaMetadata;
const _FAKE = { handler:{}, metadata:null, playbackState:'none', lage:[],
  setActionHandler(n,f){ this.handler[n]=f; },
  setPositionState(p){ this.lage.push(p===undefined?null:p); } };
Object.defineProperty(globalThis.navigator, 'mediaSession', {value:_FAKE, configurable:true});
const _els = {};
globalThis.document = { getElementById:id=>_els[id]||null, querySelectorAll:()=>[],
  addEventListener(){}, fullscreenElement:null };
globalThis.localStorage = { _d:{}, getItem(k){return this._d[k]??null;}, setItem(k,v){this._d[k]=String(v);} };
function fakeMedia(o){ return Object.assign({id:'', src:'', paused:true, currentTime:0, duration:NaN,
  playbackRate:1, isConnected:true, ended:false,
  play(){ this.paused=false; _log.push('play:'+this.id); return Promise.resolve(); },
  pause(){ this.paused=true; _log.push('pause:'+this.id); }, addEventListener(){},
  removeAttribute(n){ if(n==='src')this.src=''; _log.push('ohneQuelle:'+this.id); },
  load(){ _log.push('load:'+this.id); } }, o); }
function aus(o){ console.log(JSON.stringify(o)); }
"""


def _deno_oder_skip():
    if not os.path.exists(DENO):
        pytest.skip("deno fehlt in System/bin — JS nicht ausführbar gemessen")


def _template_ende(q, i):
    """Index hinter dem schließenden Backtick eines Template-Strings ab i."""
    while i < len(q):
        c = q[i]
        if c == "\\":
            i += 2
            continue
        if c == "`":
            return i + 1
        if c == "$" and q[i + 1:i + 2] == "{":
            i = _block_ende(q, i + 1) + 1
            continue
        i += 1
    raise AssertionError("Template-String ohne Ende")


def _block_ende(q, i):
    """Index der schließenden Klammer zum `{` bei i. Zeichenketten,
    Template-Strings und Kommentare zählen nicht mit (dort stehen oft
    Klammern, z. B. in ${…} oder in CSS-Texten)."""
    tiefe = 0
    while i < len(q):
        c = q[i]
        if c in "'\"":
            j = i + 1
            while j < len(q) and q[j] != c and q[j] != "\n":
                j += 2 if q[j] == "\\" else 1
            i = j + 1
            continue
        if c == "`":
            i = _template_ende(q, i + 1)
            continue
        if q.startswith("//", i):
            i = q.index("\n", i)
            continue
        if q.startswith("/*", i):
            i = q.index("*/", i) + 2
            continue
        if c == "{":
            tiefe += 1
        elif c == "}":
            tiefe -= 1
            if tiefe == 0:
                return i
        i += 1
    raise AssertionError("Block ohne Ende")


def _js_funktion(quelle, name):
    """Quelltext EINER Top-Level-Funktion der Seite, klammergenau ausgeschnitten."""
    m = re.search(r"^(?:async )?function " + re.escape(name) + r"\(", quelle, re.M)
    assert m, f"JS-Funktion {name}() fehlt"
    tiefe, i = 0, m.end() - 1                   # an der öffnenden Parameter-Klammer
    while True:
        tiefe += {"(": 1, ")": -1}.get(quelle[i], 0)
        if tiefe == 0:
            break
        i += 1
    ende = _block_ende(quelle, quelle.index("{", i))
    return quelle[m.start():ende + 1]


def _js_zeile(quelle, anfang):
    """Eine Top-Level-Zeile (z. B. `let _smtcTasteN=…`) wörtlich übernehmen."""
    m = re.search(r"^" + re.escape(anfang) + r".*$", quelle, re.M)
    assert m, f"Zeile »{anfang}…« fehlt"
    return m.group(0)


def _pc():
    import oberflaeche
    return oberflaeche.HTML


def _handy():
    import handy
    return handy.HTML


def _modul_js():
    import medien_session
    return medien_session.MEDIEN_JS


# Die zentralen Helfer der PC-Oberfläche (Gesamtprüfung O3): Server-Ruf und
# Browser-Speicher. Wer Seitenfunktionen ausschneidet, die sie rufen, bindet
# sie mit _pc_helfer() ein; _lauf prüft das vorher (_helfer_wache).
PC_HELFER = ("apiFehlertext", "api", "lsLesen", "lsSchreiben", "lsWeg")


def _pc_helfer():
    q = _pc()
    return [_js_funktion(q, n) for n in PC_HELFER]


def _helfer_wache(text):
    """Ruft ein Teil einen der Helfer, den kein Teil definiert, scheitert der
    Lauf laut. Die Seitenfunktionen fangen Fehler oft selbst
    (`try{…}catch(e){}`): ein fehlender Helfer wäre dort ein stiller
    ReferenceError, und der Test prüfte etwas anderes als die Seite
    (Gegenprobe in test_oberflaeche_api.py)."""
    fehlt = [n for n in PC_HELFER
             if re.search(r"(?<![\w.$])" + n + r"\(", text)
             and not re.search(r"\bfunction " + n + r"\(|(?<![\w.$])" + n + r"\s*=[^=]", text)]
    assert not fehlt, (f"Teile rufen {fehlt}, aber kein Teil definiert sie: "
                       "*_pc_helfer() in die Teile aufnehmen")


def _lauf(tmp_path, *teile):
    """Führt Attrappe + Teile aus und liefert die JSON-Zeilen von aus(...)."""
    _helfer_wache("\n".join(teile))
    _deno_oder_skip()
    skript = tmp_path / "lauf.mjs"
    skript.write_text(UMGEBUNG + "\n" + "\n".join(teile) + "\n", encoding="utf-8")
    lauf = subprocess.run([DENO, "run", "--quiet", str(skript)], capture_output=True,
                          text=True, encoding="utf-8", timeout=120)
    assert lauf.returncode == 0, (lauf.stderr or lauf.stdout)[-1500:]
    return [json.loads(z) for z in lauf.stdout.splitlines() if z.strip().startswith("{")]


# ----------------------------------------------------- gemeinsamer Baustein

def test_baustein_wird_in_beide_seiten_eingesetzt():
    """Ein Baustein, zwei Seiten: der Platzhalter ist ersetzt, die Fabrik steht
    genau EINMAL in jeder Seite (kein Rest, keine Doppelung)."""
    import medien_session
    for name, html in (("oberflaeche", _pc()), ("handy", _handy())):
        assert medien_session.PLATZHALTER not in html, f"{name}: Platzhalter nicht ersetzt"
        assert html.count("function medienSitzung(") == 1, f"{name}: Baustein nicht genau einmal"


def test_baustein_zustand_klemmt_und_raeumt(tmp_path):
    """setPositionState wirft bei Position > Dauer oder Rate 0 — der Baustein
    klemmt. Bei unendlicher Dauer (Strom) LÖSCHT er die Zeitleiste, statt die
    des Vortitels stehen zu lassen (Befund der Analyse 23.09.)."""
    (e,) = _lauf(tmp_path, _modul_js(), r"""
const s=medienSitzung(()=>document.getElementById('x'));
_els.x=fakeMedia({id:'x',duration:200,currentTime:250,playbackRate:1.5});
s.zustand('playing'); const a=_FAKE.lage.at(-1);
_els.x.duration=Infinity; s.zustand('playing'); const b=_FAKE.lage.at(-1);
s.zustand('paused',{dauer:100,pos:-5,rate:0}); const c=_FAKE.lage.at(-1);
s.aktionen({nexttrack:null});
s.info({title:'T',artist:'A',album:'L',artwork:s.bilder([['/c','512x512'],['','1x1']])});
const meta=_FAKE.metadata;
s.leeren();
const alt=fakeMedia({id:'alt',src:'/media?id=1',paused:false}); s.freigeben(alt); s.freigeben(null);
aus({a,b,c,naechster:('nexttrack' in _FAKE.handler)&&_FAKE.handler.nexttrack===null,
     meta,nachher:_FAKE.metadata,zustand:_FAKE.playbackState,letzte:_FAKE.lage.at(-1),
     frei:{src:alt.src, paused:alt.paused, log:_log}});
""")
    assert e["a"] == {"duration": 200, "playbackRate": 1.5, "position": 200}
    assert e["b"] is None, "unendliche Dauer muss die Zeitleiste löschen"
    assert e["c"] == {"duration": 100, "playbackRate": 1, "position": 0}
    assert e["naechster"], "aktionen({nexttrack:null}) muss den Knopf abmelden"
    assert e["meta"]["title"] == "T" and len(e["meta"]["artwork"]) == 1, e["meta"]
    assert e["nachher"] is None and e["zustand"] == "none" and e["letzte"] is None
    # Gemessen 23.09.: ein abgelöstes Element mit Quelle HÄLT Windows' Eintrag
    # („pausiert", Seitentitel) — freigeben löst die Quelle und beendet den Player.
    assert e["frei"]["src"] == "" and e["frei"]["paused"] is True
    assert "load:alt" in e["frei"]["log"], e["frei"]


# ------------------------------------------------------ PC: Handler-Weiche

def _pc_medien_teile():
    q = _pc()
    namen = ("filmTasten", "medienEinmal", "medienPlay", "medienPause", "medienSpringe",
             "medienRelativ", "medienWeiter", "medienZurueck", "_msPlay", "_msPause",
             "_msWeiter", "_msZurueck", "medienTastenAnmelden")
    return [_modul_js(), _js_zeile(q, "const medienS="), _js_zeile(q, "let _medienLetzte"),
            _js_zeile(q, "let _medienAngemeldet")] + [_js_funktion(q, n) for n in namen]


STUBS_PC = r"""
var tvpOffen=false, tvpModus='browser', vlcSpielt=false, plGeraet='browser';
var vlcDauerLetzte=300, vlcPosLetzte=0;
const calls=[];
function vlcAktiv(){return plGeraet==='vlc';}
function playerNext(){calls.push('playerNext');} function playerPrev(){calls.push('playerPrev');}
function tvpFolge(d){calls.push('tvpFolge:'+d);} function tvpZurueck(){calls.push('tvpZurueck');}
function tvpRel(s){calls.push('tvpRel:'+s);} function tvpSpringeAuf(t){calls.push('tvpSpringeAuf:'+t);}
function tvpMedien(w){calls.push('tvpMedien:'+w);}
function plTogglePlay(){calls.push('plTogglePlay');}
function plbSpringen(s){calls.push('plbSpringen:'+s);}
function vlcBefehl(c,d){calls.push('vlc:'+c+(d?':'+JSON.stringify(d):'')); return Promise.resolve({});}
"""


def test_tasten_steuern_musik_film_und_vlc_richtig(tmp_path):
    """Dieselben Windows-Knöpfe, drei Ziele: Musik im Browser, Film (JB 23.09.:
    „Film steuern + nächste Folge") und Gerät VLC. Musik darf NIE unter einem
    offenen Film loslaufen, und VLC bekommt nie `play` ohne Titel.

    ROTE GEGENPROBE: vor dem Umbau fehlten filmTasten/medienWeiter — der Lauf
    brach ab; mit dem alten medienPlay stand 'vlc:play' in der VLC-Liste."""
    (e,) = _lauf(tmp_path, STUBS_PC, *_pc_medien_teile(), r"""
_els['pl-el']=fakeMedia({id:'pl-el',duration:200});
medienTastenAnmelden();
const H=_FAKE.handler;
H.play(); H.nexttrack(); H.previoustrack(); H.seekto({seekTime:42}); H.seekforward({});
const musik=[...calls], plZeit=_els['pl-el'].currentTime; calls.length=0;
tvpOffen=true;
H.pause(); H.nexttrack(); H.previoustrack(); H.seekto({seekTime:42}); H.seekbackward({seekOffset:5});
const film=[...calls]; calls.length=0;
tvpOffen=false; plGeraet='vlc'; vlcSpielt=false;
H.play(); vlcSpielt=true; H.play(); H.pause(); H.seekto({seekTime:500});
aus({musik, plZeit, film, vlc:[...calls], log:_log});
""")
    assert e["musik"] == ["playerNext", "playerPrev", "plbSpringen:10"], e["musik"]
    assert e["plZeit"] == 42 and "play:pl-el" in e["log"]
    assert e["film"] == ["tvpMedien:pause", "tvpFolge:1", "tvpZurueck", "tvpSpringeAuf:42",
                         "tvpRel:-5"], e["film"]
    assert not any(c.startswith("vlc:play") for c in e["vlc"]), e["vlc"]
    assert e["vlc"] == ["plTogglePlay", "vlc:pause", 'vlc:seek:{"wert":300}'], e["vlc"]


def test_kein_doppelschritt_zwischen_taste_und_windows(tmp_path):
    """Kommt eine Medientaste in einem Browser ZUSÄTZLICH als keydown an, darf
    „Weiter" nicht doppelt schalten. Absichtlich schnell zweimal über denselben
    Weg bleibt aber erlaubt (zwei Titel weiter)."""
    q = _pc()
    (e,) = _lauf(tmp_path, _js_zeile(q, "let _medienLetzte"), _js_funktion(q, "medienEinmal"), r"""
let T=1000; Date.now=()=>T;
const r=[medienEinmal('next','ms'), medienEinmal('next','ms')];
T+=100; r.push(medienEinmal('next','taste'));
T+=1000; r.push(medienEinmal('next','taste'));
T+=50; r.push(medienEinmal('pp','ms'));
aus({r});
""")
    assert e["r"] == [True, True, False, True, True], e["r"]
    # Der keydown-Rückfall der Seite nutzt dieselbe Sperre und dieselbe Weiche.
    i = q.index("case 'MediaTrackNext'")
    stelle = q[i - 200:i + 400]
    assert "medienEinmal(" in stelle and "medienWeiter()" in stelle, stelle


def test_vlc_zustand_wird_gespiegelt(tmp_path):
    """Live gemessen 23.09.: im VLC-Modus stand playbackState dauerhaft auf
    'paused', Windows schickte deshalb bei Play/Pause immer „play" — VLC war
    per Taste nicht anzuhalten. Der 1-s-Status spiegelt jetzt den Zustand,
    solange der Server die Anmeldung nicht selbst übernimmt (smtc)."""
    q = _pc()
    (e,) = _lauf(tmp_path, _modul_js(), _js_zeile(q, "const medienS="),
                 _js_zeile(q, "let _smtcTasteN"), _js_funktion(q, "filmTasten"),
                 _js_funktion(q, "medienVlcSpiegel"), r"""
var tvpOffen=false, tvpModus='vlc', plGeraet='vlc';
function vlcAktiv(){return plGeraet==='vlc';} function aktKey(){return 'k1';}
_FAKE.metadata={title:'alt'};
medienVlcSpiegel({key:'k1',zustand:'spielt',pos:30,dauer:200,rate:1,smtc:false});
const a={z:_FAKE.playbackState, l:_FAKE.lage.at(-1), m:_FAKE.metadata};
medienVlcSpiegel({key:'k1',zustand:'pause',pos:31,dauer:200,rate:1,smtc:false});
const b=_FAKE.playbackState;
medienVlcSpiegel({key:'film:F1',zustand:'spielt',pos:99,dauer:5000,rate:1,smtc:false});  // VLC spielt einen Film
const fremd={z:_FAKE.playbackState, l:_FAKE.lage.at(-1)};
medienVlcSpiegel({key:'k1',zustand:'spielt',pos:32,dauer:200,rate:1,smtc:true});
aus({a,b,fremd,c:{z:_FAKE.playbackState,m:_FAKE.metadata}});
""")
    assert e["a"]["z"] == "playing" and e["a"]["l"] == {"duration": 200, "playbackRate": 1,
                                                        "position": 30}
    assert e["b"] == "paused"
    assert e["fremd"] == {"z": "paused", "l": {"duration": 200, "playbackRate": 1, "position": 31}}, \
        "spielt der VLC etwas anderes (Film), bleibt die Musik-Kachel unberührt"
    # Übernimmt der Server (pywinrt), räumt die Seite ihre Sitzung: sonst stünde
    # SyncYouTube zweimal im Windows-Overlay.
    assert e["c"] == {"z": "none", "m": None}, e["c"]
    # …und der 1-s-Takt des Geräts VLC ruft den Spiegel wirklich auf.
    assert "medienVlcSpiegel(s)" in _js_funktion(q, "vlcTick"), "vlcTick spiegelt nicht"


def test_server_knoepfe_werden_genau_einmal_ausgefuehrt(tmp_path):
    """Vertrag mit medien_smtc.py: jede /api/vlc-Antwort trägt taste={n,was}.
    Der erste Stand wird nur gemerkt (kein Nachplappern nach dem Laden), jede
    Änderung von n wird ausgeführt, eine Wiederholung desselben Stands nie.
    (Wem der Druck gehört, prüft test_medientasten_randfaelle.py.)"""
    q = _pc()
    (e,) = _lauf(tmp_path, _js_zeile(q, "let _smtcTasteN"), _js_funktion(q, "smtcTaste"), r"""
var tvpOffen=false, tvpIdAkt='';
const calls=[];
function vlcAktiv(){return true;} function aktKey(){return 'k1';}
function playerSchritte(n){calls.push(n>0?'weiter':'zurueck');}
async function tvpFolge(){} async function tvpZurueck(){}
const S=(n,was,vor,zur)=>smtcTaste({key:'k1',smtc:true,taste:{n,was,vor,zurueck:zur}});
await S(4,'next',4,0); await S(4,'next',4,0); await S(5,'next',5,0); await S(5,'next',5,0); await S(6,'prev',5,1);
await smtcTaste(null); await smtcTaste({verfuegbar:true});
aus({calls, smtc:vlcSmtc});
""")
    assert e["calls"] == ["weiter", "zurueck"], e["calls"]
    assert e["smtc"] is True
    i = q.index("async function vlcBefehl")
    assert "smtcTaste(" in q[i:q.index("\nfunction ", i)], \
        "jede /api/vlc-Antwort muss durch smtcTaste laufen (Musik- UND Film-Takt)"


def test_leere_warteschlange_raeumt_das_overlay(tmp_path):
    """Befund: nach „Warteschlange leeren" blieben Titel und Zeitleiste im
    Overlay stehen, ein laufender Crossfade spielte weiter, und VLC spielte
    unsteuerbar weiter (vlcAktiv ohne Titel = false)."""
    q = _pc()
    (e,) = _lauf(tmp_path, _modul_js(), _js_zeile(q, "const medienS="), *_pc_helfer(),
                 _js_funktion(q, "filmTasten"), _js_funktion(q, "renderPlayerMedia"), r"""
var tvpOffen=false, plGeraet='vlc', adoptEl=null; const calls=[];
_els['pl-media']={innerHTML:'x'};
function spulStopp(){} function aktKey(){return undefined;} function libFind(){return null;}
function xfAbbrechen(){calls.push('xfAbbrechen');}
function vlcBefehl(c){calls.push('vlc:'+c); return Promise.resolve({});}
_FAKE.metadata={title:'alt'}; _FAKE.playbackState='playing';
_els['pl-el']=fakeMedia({id:'pl-el',src:'/media?id=alt',paused:false});
renderPlayerMedia();
aus({calls, m:_FAKE.metadata, z:_FAKE.playbackState, l:_FAKE.lage.at(-1), altSrc:_els['pl-el'].src});
""")
    assert "xfAbbrechen" in e["calls"] and "vlc:stop" in e["calls"], e["calls"]
    assert e["m"] is None and e["z"] == "none" and e["l"] is None
    assert e["altSrc"] == "", "das abgelöste Element muss seine Quelle lösen, sonst bleibt Windows' Eintrag"


def test_zeitleiste_folgt_spruengen_und_uebernahme():
    """Befund: setPositionState lief nur bei play/pause — nach jedem Sprung
    (Overlay-Regler, Pfeile, Kapitel) und nach einer Crossfade-Übernahme
    (kein play-Ereignis) zeigte Windows die alte Stelle bzw. 'paused'.
    Live nachgemessen im Browser (Zeitleiste nach Sprung); hier der Anschluss."""
    q = _pc()
    i = q.index("function renderPlayerMedia")
    rumpf = q[i:q.index("\nfunction ", i + 10)]
    assert "'seeked'" in rumpf and "'ratechange'" in rumpf, "kein Sprung-/Tempo-Anschluss"
    j = rumpf.index("'seeked'")
    assert "medienZustand(" in rumpf[j:rumpf.index("}));", j)], "Sprung ohne Zeitleisten-Nachzug"
    assert re.search(r"if\(uebernahme&&el\)medienZustand\(", rumpf), \
        "nach der Crossfade-Übernahme muss der Zustand nachgezogen werden"
    # Titelwechsel/Wechsel auf VLC: das alte Element wird freigegeben (live
    # gemessen: sonst blieb 'YouTube-Downloader (pausiert)' neben der VLC-Sitzung).
    assert "if(altEl&&altEl!==el)medienS.freigeben(altEl)" in rumpf


def test_film_gibt_sein_video_frei(tmp_path):
    """Film zu oder Folgenwechsel: das alte <video> löst seine Quelle, sonst
    hält es Windows' Eintrag als „pausiert" mit dem Seitentitel.

    Die REIHENFOLGE zählt (Messung 24.09.2026, Edge + Windows 11): Wurde das
    alte Video geleert (Quelle weg + load()), BEVOR die neue Folge spielte,
    gab Windows bei der nächsten Pause die „aktuelle Sitzung" an eine andere
    pausierte App ab — der nächste ⏯ startete Firefox statt den Film
    (reproduziert, auch ohne Taste; Musik-Titelwechsel nicht betroffen).
    Geleert, sobald die neue Folge spielt: Edge blieb in allen Läufen aktuell.
    Darum verstummt das alte Video sofort und wird erst bei „playing" des
    neuen geleert; ohne neues Video (VLC) sofort; tvpZu räumt Liegengebliebenes."""
    q = _pc()
    zu = _js_funktion(q, "tvpZu")
    assert "medienS.freigeben(document.getElementById('tvp-video'))" in zu
    assert "tvpAbgeloestFreigeben()" in zu, "Film zu: auch noch wartende alte Folgen leeren"
    (e,) = _lauf(tmp_path, _modul_js(), "const medienS=medienSitzung(()=>null);",
                 _js_zeile(q, "let tvpAbgeloest"), _js_zeile(q, "let tvpGesehenGemeldet"),
                 _js_zeile(q, "let tvpRateWert"), _js_funktion(q, "tvpAbgeloestFreigeben"),
                 _js_funktion(q, "tvpVideoVerdrahten"), _js_funktion(q, "tvFilmPlayer"), r"""
var tvpOffen=false, tvpPos=0, tvpDauer=0, tvpLief=false, tvpTicks=0, tvpAktiv=0, tvpIdAkt='', tvpMeta={},
    tvInfoDaten=null, tvHeroDaten=null, tvpZurueckModus='normal', tvpModusNaechster=null, tvpWechsel=null,
    tvpModus='browser', vlcKeyLetzter='', tvpTc=false, tvpTcOffset=0, tvpTcVcopy=false, plVol=40, tvpTimer=1;
globalThis.screen={isExtended:false}; document.body={appendChild(){}};
function tvpDirektSrc(){return '/media?id='+tvpIdAkt;} function ico(){return '';} function esc(s){return s;}
function zeit(s){return String(s);} function tvpWach(){} function toast(){} function tvpZu(){} function filmePlayVlc(){}
function tvpBefehl(){} function tvpTick(){} function tvpMedienZustand(){} function tvpMedienAn(){}
function videoMit(src){
  const v=fakeMedia({id:'tvp-video', src, paused:false, volume:1}); v._h={};
  v.addEventListener=(n,f,o)=>{(v._h[n]=v._h[n]||[]).push({f,once:!!(o&&o.once)});};
  v.feuer=n=>{const l=v._h[n]||[]; v._h[n]=l.filter(x=>!x.once); l.forEach(x=>x.f({}));};
  return v;
}
_els['tv-player']={id:'tv-player', style:{}, classList:{add(){},remove(){}}, contains(){return true;}, addEventListener(){},
  set innerHTML(h){                                   // Neuaufbau: das alte Video fliegt aus dem Dokument
    if(_els['tvp-video'])_els['tvp-video'].isConnected=false;
    const m=/<video id="tvp-video"[^>]*src="([^"]*)"/.exec(h);
    if(m)_els['tvp-video']=videoMit(m[1]); else delete _els['tvp-video'];
  }};
tvFilmPlayer('F1','Eins',0,{titel:'Eins'});
const A=_els['tvp-video'];
tvFilmPlayer('F2','Zwei',0,{titel:'Zwei'});
const B=_els['tvp-video'];
const wechsel={bNeu:!!B&&B!==A, aStumm:A.paused, aQuelle:A.src, bHoert:Object.keys(B._h).sort()};
B.feuer('playing');
const spielt={aQuelle:A.src, bQuelle:B.src};
tvFilmPlayer('F3','Drei',0,{titel:'Drei'}); const C=_els['tvp-video'];
tvpModus='vlc'; tvFilmPlayer('F4','Vier',0,{titel:'Vier'});           // Rückfall auf VLC: kein neues Video
aus({wechsel, spielt, vlc:{b:B.src, c:C.src, video:!!_els['tvp-video']}});
""")
    assert e["wechsel"]["bNeu"], "der Neuaufbau liefert ein neues Video"
    assert {"error", "click", "play", "pause"} <= set(e["wechsel"]["bHoert"]), \
        f"das neue Film-Video ist nicht verdrahtet: {e['wechsel']['bHoert']}"
    assert e["wechsel"]["aStumm"], "die alte Folge verstummt sofort"
    assert e["wechsel"]["aQuelle"] == "/media?id=F1", "… wird aber erst geleert, wenn die neue spielt"
    assert e["spielt"] == {"aQuelle": "", "bQuelle": "/media?id=F2"}, e["spielt"]
    assert e["vlc"] == {"b": "", "c": "", "video": False}, "ohne neues Video: sofort leeren"


# ------------------------------------------------------- Serien: JBs Regel

FOLGEN = r"""
const eps=[
 {id:'e1',staffel:1,folge:1,laufzeit_min:40,position_s:0,gesehen:true},
 {id:'e2',staffel:1,folge:2,laufzeit_min:40,position_s:1200,gesehen:false},
 {id:'e3',staffel:1,folge:3,laufzeit_min:40,position_s:2300,gesehen:false},
 {id:'e4',staffel:1,folge:4,laufzeit_min:40,position_s:20,gesehen:false},
 {id:'e5',staffel:1,folge:5,laufzeit_min:40,position_s:900,gesehen:false},
 {id:'e6',staffel:1,folge:6,laufzeit_min:40,position_s:0,gesehen:false}];
const kurz=z=>z?(z.art==='folge'?[z.e.id,z.pos,z.modus]:[z.art,z.modus]):null;
"""


def test_zurueck_regel_fuer_serien(tmp_path):
    """JB 23.09.2026 (Variante C, x = 3 s): „Vorfolge, dann Anfang; wenn die
    Vorfolge zu Ende geschaut wurde, dann direkt zum Anfang."
    Zu Ende = gesehen oder ab 90 % (Jellyfins Standard-Grenze für „gespielt");
    unter 30 s gilt wie bei den Folgen-Kacheln „von vorn"."""
    q = _pc()
    (e,) = _lauf(tmp_path, FOLGEN, _js_zeile(q, "const SEHZEIT="), _js_funktion(q, "tvpLandePos"),
                 _js_funktion(q, "tvpZurueckZiel"), _js_funktion(q, "tvpWeiterZiel"), r"""
aus({
 jb_beispiel: kurz(tvpZurueckZiel(eps,'e6',1200,'normal')),  // Folge 6, Min 20 -> Folge 5 an ihrer Stelle
 gemerkt:     kurz(tvpZurueckZiel(eps,'e3',600,'normal')),
 zweiter:     kurz(tvpZurueckZiel(eps,'e2',1201,'gelandet')),
 spaeter:     kurz(tvpZurueckZiel(eps,'e2',1500,'gelandet')),
 musik_anf:   kurz(tvpZurueckZiel(eps,'e2',1,'musik')),
 musik_mitte: kurz(tvpZurueckZiel(eps,'e2',50,'musik')),
 zu_ende:     kurz(tvpZurueckZiel(eps,'e4',100,'normal')),
 unter30:     kurz(tvpZurueckZiel(eps,'e5',100,'normal')),
 erste:       kurz(tvpZurueckZiel(eps,'e1',100,'normal')),
 weiter:      kurz(tvpWeiterZiel(eps,'e1')),
 weiter_ende: kurz(tvpWeiterZiel(eps,'e6')),
 fremd:       kurz(tvpWeiterZiel(eps,'x'))});
""")
    assert e["jb_beispiel"] == ["e5", 900, "gelandet"]
    assert e["gemerkt"] == ["e2", 1200, "gelandet"]
    assert e["zweiter"] == ["anfang", "musik"], "2. Druck: Anfang der Vorfolge"
    assert e["spaeter"] == ["anfang", "musik"], "später: Anfang (Musik-Regel, > 3 s)"
    assert e["musik_anf"] == ["e1", 0, "musik"], "in den ersten 3 s: noch eine Folge zurück (gesehen -> Anfang)"
    assert e["musik_mitte"] == ["anfang", "musik"]
    assert e["zu_ende"] == ["e3", 0, "musik"], "96 % geschaut = zu Ende -> direkt Anfang"
    assert e["unter30"] == ["e4", 0, "musik"], "unter 30 s gemerkt = von vorn"
    assert e["erste"] == ["anfang", "musik"], "keine Vorfolge: Anfang der ersten"
    assert e["weiter"] == ["e2", 1200, "normal"]
    assert e["weiter_ende"] is None and e["fremd"] is None


def test_film_overlay_titel_und_knoepfe(tmp_path):
    """Eine Folge zeigt im Overlay Folgenname, Serie und „Staffel · Folge";
    ohne Nachfolger verschwindet „Weiter" (setActionHandler(null) statt eines
    Knopfs, der ins Leere greift). Nach dem Film gehört das Overlay wieder der
    Musik bzw. wird geräumt."""
    q = _pc()
    teile = [FOLGEN, _modul_js(), _js_zeile(q, "const medienS="), _js_zeile(q, "let _medienLetzte"),
             _js_zeile(q, "let _medienAngemeldet"), _js_zeile(q, "let tvpMedienGen"),
             _js_zeile(q, "const SEHZEIT=")]
    teile += [_js_funktion(q, n) for n in (
        "filmTasten", "medienEinmal", "medienPlay", "medienPause", "medienSpringe", "medienRelativ",
        "medienWeiter", "medienZurueck", "_msPlay", "_msPause", "_msWeiter", "_msZurueck",
        "medienTastenAnmelden", "tvpLandePos", "tvpWeiterZiel", "tvpFolgeTitel", "tvpMedienAn",
        "tvpMedienZustand", "medienNachFilm", "medienInfoSetzen", "medienZustand")]
    (e,) = _lauf(tmp_path, *teile, r"""
var tvpOffen=true, tvpModus='browser', tvpIdAkt='e6', plGeraet='browser', vlcSpielt=false;
var tvpDauer=2400, tvpPos=100;
var tvpMeta={titel:'Dark · S1 F6 — Verbrechen', typ:'folge', serie_id:'s9'};
var playerState={quelle:'Bibliothek'};
const vlcCalls=[];
function vlcAktiv(){return false;} function vlcBefehl(c,d){vlcCalls.push([c,d]); return Promise.resolve({});}
async function tvpFolgenHolen(){return eps;}
function aktKey(){return null;} function libFind(){return null;}
await tvpMedienAn();
const film={m:_FAKE.metadata, weiter:_FAKE.handler.nexttrack, zurueck:typeof _FAKE.handler.previoustrack};
tvpOffen=false; medienNachFilm();
aus({film, nachher:{m:_FAKE.metadata, weiter:typeof _FAKE.handler.nexttrack, z:_FAKE.playbackState}, vlcCalls});
""")
    m = e["film"]["m"]
    assert m["title"] == "Verbrechen" and m["artist"] == "Dark" and m["album"] == "Staffel 1 · Folge 6", m
    assert any("/api/filme/bild?id=e6" in b["src"] for b in m["artwork"]), m["artwork"]
    assert e["film"]["weiter"] is None, "letzte Folge: kein Weiter-Knopf"
    assert e["film"]["zurueck"] == "function"
    assert e["nachher"] == {"m": None, "weiter": "function", "z": "none"}, e["nachher"]
    assert e["vlcCalls"] == [], "Browser-Film meldet nichts an den VLC-Server"


def test_vlc_film_meldet_metadaten_an_den_server(tmp_path):
    """Läuft der Film im VLC (Hülle, Live-TV), spielt der Ton außerhalb des
    Browsers — die Windows-Anmeldung macht dann der Server (pywinrt). Die Seite
    liefert ihm Titel, Bild und ob es Weiter/Zurück gibt (Vertrag cmd 'medien')."""
    q = _pc()
    teile = [FOLGEN, _modul_js(), _js_zeile(q, "const medienS="), _js_zeile(q, "let _medienLetzte"),
             _js_zeile(q, "let _medienAngemeldet"), _js_zeile(q, "let tvpMedienGen"),
             _js_zeile(q, "const SEHZEIT=")]
    teile += [_js_funktion(q, n) for n in (
        "filmTasten", "medienEinmal", "medienPlay", "medienPause", "medienSpringe", "medienRelativ",
        "medienWeiter", "medienZurueck", "_msPlay", "_msPause", "_msWeiter", "_msZurueck",
        "medienTastenAnmelden", "tvpLandePos", "tvpWeiterZiel", "tvpFolgeTitel", "tvpMedienAn",
        "tvpMedienZustand")]
    (e,) = _lauf(tmp_path, *teile, r"""
var tvpOffen=true, tvpModus='vlc', tvpIdAkt='e2', plGeraet='browser', vlcSpielt=false;
var tvpDauer=2400, tvpPos=100;
var tvpMeta={titel:'Dark · S1 F2 — Lügen', typ:'folge', serie_id:'s9'};
const vlcCalls=[];
function vlcAktiv(){return false;} function vlcBefehl(c,d){vlcCalls.push([c,d]); return Promise.resolve({});}
async function tvpFolgenHolen(){return eps;}
await tvpMedienAn();
aus({vlcCalls, kachel:_FAKE.metadata&&_FAKE.metadata.title});
""")
    assert e["kachel"] == "Lügen", "auch die Browser-Kachel zeigt den Film (die Tasten gehören ihm)"
    ((cmd, d),) = e["vlcCalls"]
    assert cmd == "medien" and d["key"] == "film:e2", e["vlcCalls"]
    assert d["titel"] == "Lügen" and d["interpret"] == "Dark" and d["album"] == "Staffel 1 · Folge 2"
    assert d["cover"].startswith("/api/filme/bild?id=e2") and d["weiter"] is True and d["zurueck"] is True


# ------------------------------------------------------------------ Handy

def _handy_teile():
    h = _handy()
    namen = ("esc", "libFind", "aktuelleListe", "setDev", "spiel", "steuer", "handyNachbar",
             "handyEnde", "handyMedienInfo", "handyMedienAnmelden", "mitCode", "lsSchreiben")
    return [_modul_js(), _js_zeile(h, "const medienS=")] + [_js_funktion(h, n) for n in namen]


def test_handy_sperrbildschirm_steuert_das_handy(tmp_path):
    """Sperrbildschirm-Knöpfe wirken auf das Handy-Element — nie auf den PC.
    Seit dem 25.09.2026 trägt ein HttpOnly-Cookie den Zugang (JB-Entscheid 7a
    Punkt 1); den Code in der Cover-Adresse gibt es nur noch als Rückfall für
    einen Browser ohne Cookies (KOPF). Hier dieser Rückfall, der Weg mit
    Cookie steht in test_zugang_seiten_js.py."""
    (e,) = _lauf(tmp_path, r"""
var KOPF='AB12CD', dev='handy', aktuell=null;
var daten=[{id:'k1',titel:'Eins',uploader:'Kanal',kuenstler:'Künstlerin',thumb:'https://i.ytimg.com/1.jpg',vorhanden:true},
           {id:'k2',titel:'Zwei',uploader:'Kanal2',thumb:'',vorhanden:true}];
const remoteCalls=[];
_els.el=fakeMedia({id:'el'}); _els.suche={value:''}; _els.nowtitel={}; _els.nowsub={}; _els.pp={};
_els['dev-pc']={classList:{toggle(){}}}; _els['dev-handy']={classList:{toggle(){}}};
_els.vol={style:{}}; _els.tipp={};
async function api(){return {ok:true};}
function remote(c,k){remoteCalls.push(c); return Promise.resolve();}   // zählt nur, ob der PC gerufen wird
""", *_handy_teile(), r"""
handyMedienAnmelden();
spiel('k1');
const m=_FAKE.metadata, src1=_els.el.src;
_FAKE.handler.nexttrack();
const src2=_els.el.src;
_FAKE.handler.pause();
const pausiert=_els.el.paused;
aus({m, src1, src2, pausiert, remoteCalls, hatSeekFwd:'seekforward' in _FAKE.handler});
""")
    assert e["m"]["title"] == "Eins" and e["m"]["artist"] == "Künstlerin", e["m"]
    assert any("/api/cover?id=k1&code=AB12CD" in b["src"] for b in e["m"]["artwork"]), e["m"]
    assert "id=k2" in e["src2"] and e["src1"] != e["src2"], "Weiter spielt am Handy den nächsten Titel"
    assert e["pausiert"] is True and e["remoteCalls"] == [], "Sperrbildschirm darf den PC nicht steuern"
    assert e["hatSeekFwd"] is False, "iOS zeigt sonst ±-Sprungtasten statt Titel vor/zurück"


def test_handy_umschalten_auf_pc_stoppt_das_handy(tmp_path):
    """Befund: setDev('pc') ließ das Handy weiterspielen, und am Titelende
    schickte es 'next' an den PC — der PC sprang ungewollt weiter.

    ROTE GEGENPROBE: mit dem alten ended->steuer('next') steht 'next' in remoteCalls."""
    (e,) = _lauf(tmp_path, r"""
var KOPF='', dev='handy', aktuell=null;
var daten=[{id:'k1',titel:'Eins',uploader:'K',thumb:'',vorhanden:true},{id:'k2',titel:'Zwei',uploader:'K',thumb:'',vorhanden:true}];
const remoteCalls=[];
_els.el=fakeMedia({id:'el'}); _els.suche={value:''}; _els.nowtitel={}; _els.nowsub={}; _els.pp={};
_els['dev-pc']={classList:{toggle(){}}}; _els['dev-handy']={classList:{toggle(){}}};
_els.vol={style:{}}; _els.tipp={};
async function api(){return {ok:true};}
function remote(c,k){remoteCalls.push(c); return Promise.resolve();}
""", *_handy_teile(), r"""
handyMedienAnmelden(); spiel('k1');
setDev('pc');
const nachUmschalten={paused:_els.el.paused, m:_FAKE.metadata, z:_FAKE.playbackState, src:_els.el.src};
handyEnde();
aus({nachUmschalten, remoteCalls});
""")
    assert e["nachUmschalten"] == {"paused": True, "m": None, "z": "none", "src": ""}, e["nachUmschalten"]
    assert e["remoteCalls"] == [], e["remoteCalls"]
