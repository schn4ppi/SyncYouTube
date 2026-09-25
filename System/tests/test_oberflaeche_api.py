# -*- coding: utf-8 -*-
"""Zentrale Helfer der Oberfläche: api() und lsLesen/lsSchreiben/lsWeg
(Gesamtprüfung O3, 25.09.2026).

Vorher stand dieselbe fetch-Zeile für jeden POST 57-mal in der Seite, und nur
vier Stellen prüften r.ok. Jetzt gehen 54 davon über `api(pfad, body, opt)`.
Diese Datei hält fest:
  * api() schickt genau das, was die alte Zeile schickte (Methode, Kopf,
    Körper als JSON; ein fertiger Text unverändert; ohne Körper '{}');
  * die Antwort des Servers kommt unverändert zurück; nur eine Fehlerantwort
    OHNE `fehler` bekommt den einheitlichen Text; eine unlesbare Antwort und
    ein Netzfehler werfen (so nehmen die lesenden Stellen ihren alten
    catch-Weg); {roh:true} liefert den Response selbst;
  * fetch wird bei jedem Ruf neu nachgeschlagen (die Hülle für Geräte im WLAN
    greift auch hier);
  * die Speicher-Helfer überstehen einen gesperrten Speicher (F27);
  * Auto-Discovery: jeder POST, der noch roh `fetch` ruft, steht mit Grund in
    ROH_BLEIBT, und localStorage wird nur noch in den Helfern beschrieben;
  * Gegenprobe zur Helfer-Wache in `_lauf`: ohne sie liefe ein Test, der den
    Helfer vergisst, still grün, weil die Seite Fehler oft selbst fängt.

Die Verhaltensgleichheit aller 101 geänderten Funktionen ist zusätzlich einmal
mit einer Alles-Attrappe gemessen (alt gegen neu, sechs Server-Antworten), siehe
Commit-Nachricht; dauerhaft prüfen das die bestehenden deno-Tests der Seite.
"""
import json
import os
import re
import sys
from collections import Counter

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

import test_medientasten_verhalten as tmv  # noqa: E402
from test_medientasten_verhalten import (  # noqa: E402
    _js_funktion,
    _lauf,
    _pc,
    _pc_helfer,
    _template_ende,
)

# POSTs, die bewusst roh bleiben, mit Grund und Anzahl der Stellen.
ROH_BLEIBT = {
    "'/api/filme/fortschritt'": (1, "keepalive:true: die Meldung muss auch beim Schließen der Seite "
                                   "hinausgehen; api() reicht keine fetch-Optionen durch"),
    "'/api/js_fehler'": (2, "der Fehler-Rekorder darf von keinem Helfer abhängen, sonst meldet er "
                            "einen Fehler in api() selbst nicht"),
}

NETZ = r"""
const _rufe=[]; let _naechste=null;
function antwort(status, text){ return {ok:status>=200&&status<300, status,
  json:async()=>JSON.parse(text)}; }
globalThis.fetch=async(url,opt)=>{ _rufe.push({url, opt:JSON.parse(JSON.stringify(opt))});
  if(_naechste instanceof Error) throw _naechste; return _naechste; };
async function fall(f){ try{ return {wert: await f()}; }catch(e){ return {wirft: String(e.message||e)}; } }
"""
KOPF = {"method": "POST", "headers": {"Content-Type": "application/json"}}


# ---------------------------------------------------------------- Anfrage

def test_api_schickt_genau_die_alte_anfrage(tmp_path):
    koerper = [{"urls": "https://www.youtube.com/watch?v=x", "qualitaet": "beste"},
               {"id": "k|mp3", "art": "herz", "text": "Grüße \"zitiert\" 'x' <b>"},
               {"keys": ["a", "b"], "merge": 1, "speed": 1.25, "leer": None}, [], 0, "fertig"]
    (e,) = _lauf(tmp_path, NETZ, *_pc_helfer(),
                 "_naechste=antwort(200,'{\"ok\":true}');",
                 f"const K={json.dumps(koerper)};",
                 "for(const k of K){ await api('/api/x',k); }",
                 "await api('/api/leer');",
                 # die alte Zeile, wörtlich, zum Vergleich
                 "const alt=K.map(k=>({method:'POST',headers:{'Content-Type':'application/json'},"
                 "body:typeof k==='string'?k:JSON.stringify(k)}));",
                 "aus({rufe:_rufe, alt});")
    for ruf, alt in zip(e["rufe"], e["alt"]):
        assert ruf == {"url": "/api/x", "opt": alt}
    assert e["rufe"][-1] == {"url": "/api/leer", "opt": dict(KOPF, body="{}")}, \
        "ohne Körper schickte die alte Zeile body:'{}'"
    assert e["rufe"][len(koerper) - 1]["opt"]["body"] == "fertig", "ein fertiger Text geht unverändert"


# ---------------------------------------------------------------- Antwort

def test_api_liefert_die_antwort_des_servers_unveraendert(tmp_path):
    (e,) = _lauf(tmp_path, NETZ, *_pc_helfer(), r"""
const erg={};
_naechste=antwort(200,'{"ok":true,"id":"p1"}'); erg.ok=await fall(()=>api('/api/a',{}));
_naechste=antwort(403,'{"fehler":"Nur am PC möglich.","nur_pc":true}'); erg.pc=await fall(()=>api('/api/a',{}));
_naechste=antwort(500,'{}'); erg.ohneText=await fall(()=>api('/api/a',{}));
_naechste=antwort(200,'{"fehler":"abgelehnt"}'); erg.fehler200=await fall(()=>api('/api/a',{}));
_naechste=antwort(200,'[1,2]'); erg.liste=await fall(()=>api('/api/a',{}));
_naechste=antwort(200,'<html>'); erg.unlesbar=await fall(()=>api('/api/a',{}));
_naechste=new TypeError('Failed to fetch'); erg.netz=await fall(()=>api('/api/a',{}));
const roh=antwort(413,'{"fehler":"zu groß"}'); _naechste=roh;
erg.roh=(await api('/api/a','t',{roh:true}))===roh;
aus(erg);
""")
    assert e["ok"] == {"wert": {"ok": True, "id": "p1"}}
    assert e["pc"] == {"wert": {"fehler": "Nur am PC möglich.", "nur_pc": True}}, \
        "eine Fehlerantwort des Servers bleibt, wie sie ist (kein zusätzliches ok)"
    assert e["ohneText"] == {"wert": {"fehler": "Server antwortet mit 500."}}
    assert e["fehler200"] == {"wert": {"fehler": "abgelehnt"}}
    assert e["liste"] == {"wert": [1, 2]}
    assert e["unlesbar"] == {"wirft": "Server antwortet mit 200."}
    assert e["netz"] == {"wirft": "Failed to fetch"}
    assert e["roh"] is True


def test_api_nimmt_das_fetch_zum_zeitpunkt_des_rufs(tmp_path):
    """Geräte im WLAN umhüllen fetch (fetchHuelleSetzen), nachdem api() schon
    definiert ist; die Hülle muss trotzdem greifen."""
    (e,) = _lauf(tmp_path, NETZ, *_pc_helfer(), r"""
const roh=globalThis.fetch; const spur=[];
globalThis.fetch=async(...a)=>{ spur.push('huelle'); return roh(...a); };
_naechste=antwort(200,'{}'); await api('/api/a');
aus({spur, rufe:_rufe.length});
""")
    assert e == {"spur": ["huelle"], "rufe": 1}


# --------------------------------------------- lesende Stellen, stellvertretend

def test_wunsch_stellen_meldet_erfolg_fehler_und_netz(tmp_path):
    teile = [NETZ, *_pc_helfer(), "const _t=[]; function toast(x){_t.push(x);} function tvMalen(){_t.push('malen');}",
             _js_funktion(_pc(), "tvAnfrage")]
    (e,) = _lauf(tmp_path, *teile, r"""
const erg={};
_naechste=antwort(200,'{"ok":true}'); const w={tmdb:1,typ:'film'}; await tvAnfrage(w); erg.ok=[..._t, w.status];
_t.length=0; _naechste=antwort(502,'{"fehler":"Jellyseerr antwortet nicht."}'); await tvAnfrage({tmdb:2}); erg.fehler=[..._t];
_t.length=0; _naechste=new TypeError('Failed to fetch'); await tvAnfrage({tmdb:3}); erg.netz=[..._t];
erg.koerper=_rufe.map(r=>JSON.parse(r.opt.body));
aus(erg);
""")
    assert e["ok"] == ["➕ Wunsch gestellt — René lädt ihn, sobald er kann.", "malen", "kommt"]
    assert e["fehler"] == ["➕ Jellyseerr antwortet nicht."]
    assert e["netz"] == ["➕ Anfrage nicht erreichbar."]
    assert e["koerper"][0] == {"tmdb": 1, "typ": "film"}


def test_geo_test_zeigt_den_fehler_des_servers(tmp_path):
    teile = [NETZ, *_pc_helfer(), "const _a=[]; globalThis.alert=x=>_a.push(x); let geoTestTimer=null;"
             " function geoStatusLaden(x){_a.push('status:'+x);} globalThis.setInterval=()=>7;",
             _js_funktion(_pc(), "geoTestStart")]
    (e,) = _lauf(tmp_path, *teile, r"""
_naechste=antwort(200,'{"fehler":"Kein VPN eingerichtet."}'); await geoTestStart(); const a=[..._a];
_a.length=0; _naechste=antwort(200,'{"ok":true}'); await geoTestStart();
aus({a, b:[..._a], timer:geoTestTimer});
""")
    assert e == {"a": ["Kein VPN eingerichtet."], "b": ["status:true"], "timer": 7}


# ---------------------------------------------------------------- Speicher

def test_speicher_helfer_normal_und_gesperrt(tmp_path):
    from test_oberflaeche_nebenfehler import GESPERRT
    (normal,) = _lauf(tmp_path, *_pc_helfer(),
                      "lsSchreiben('a','1'); lsSchreiben('n',5); const vorher=[lsLesen('a'),lsLesen('n'),lsLesen('fehlt')];",
                      "lsWeg('a'); aus({vorher, nachher:lsLesen('a')});")
    assert normal == {"vorher": ["1", "5", None], "nachher": None}
    (gesperrt,) = _lauf(tmp_path, GESPERRT, *_pc_helfer(),
                        "lsSchreiben('a','1'); lsWeg('a'); aus({wert:lsLesen('a')});")
    assert gesperrt == {"wert": None}, "ein gesperrter Speicher darf nichts abbrechen"


# ---------------------------------------------------------------- Auto-Discovery

def _klammer_ende(q, i):
    """Index der schließenden Klammer zur '(' bei i (Strings/Templates übersprungen)."""
    tiefe = 0
    while True:
        c = q[i]
        if c in "'\"":
            j = i + 1
            while q[j] != c:
                j += 2 if q[j] == "\\" else 1
            i = j + 1
            continue
        if c == "`":
            i = _template_ende(q, i + 1)
            continue
        if c == "(":
            tiefe += 1
        elif c == ")":
            tiefe -= 1
            if tiefe == 0:
                return i
        i += 1


def _rohe_posts(q):
    """Erstes Argument jedes fetch(…), dessen Argumente method:'POST' tragen."""
    funde = Counter()
    for m in re.finditer(r"(?<![\w.$])fetch\(", q):
        auf = m.end() - 1
        args = q[auf + 1:_klammer_ende(q, auf)]
        if "method:'POST'" not in args:
            continue
        funde[re.split(r",\s*[{\n]", args, maxsplit=1)[0].strip()] += 1
    return funde


def _seiten_skript():
    q = _pc()
    return "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script\s*>", q, re.S | re.I))


def test_rohe_posts_nur_mit_grund():
    funde = _rohe_posts(_seiten_skript())
    assert funde.pop("pfad", 0) == 1, "api() selbst ruft fetch genau einmal"
    erwartet = {pfad: n for pfad, (n, _) in ROH_BLEIBT.items()}
    assert dict(funde) == erwartet, (
        "Ein POST ruft fetch roh ohne Eintrag in ROH_BLEIBT (dann über api() schicken) "
        f"oder ein Eintrag ist überholt: gefunden {dict(funde)}")


def test_gegenprobe_roher_post_faellt_auf():
    q = _seiten_skript() + "\nfetch('/api/neu',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});"
    assert _rohe_posts(q)["'/api/neu'"] == 1


def test_speicher_wird_nur_in_den_helfern_beschrieben():
    q = _seiten_skript()
    for n in ("lsSchreiben", "lsWeg"):
        q = q.replace(_js_funktion(q, n), "")
    rest = re.findall(r"localStorage\.(?:setItem|removeItem)\(.{0,40}", q)
    assert not rest, f"localStorage direkt beschrieben (lsSchreiben/lsWeg nehmen): {rest}"


# ---------------------------------------------------------------- Helfer-Wache

SEITE_MIT_FANG = ("async function speichern(){ try{ await api('/api/config',{a:1}); }catch(e){} return 'fertig'; }")


def test_helfer_wache_schlaegt_laut_an():
    with pytest.raises(AssertionError, match="api"):
        tmv._helfer_wache(SEITE_MIT_FANG)
    tmv._helfer_wache("\n".join(_pc_helfer() + [SEITE_MIT_FANG]))       # mit Helfer: still


def test_ohne_wache_liefe_der_vergessene_helfer_still_gruen(tmp_path, monkeypatch):
    """Die Gegenprobe zur Wache: ohne sie fängt die Seite den ReferenceError
    selbst, der Test sähe „fertig“ und keinen einzigen Ruf."""
    monkeypatch.setattr(tmv, "_helfer_wache", lambda text: None)
    (still,) = _lauf(tmp_path, NETZ, SEITE_MIT_FANG, "aus({r: await speichern(), rufe:_rufe.length});")
    assert still == {"r": "fertig", "rufe": 0}
    (echt,) = _lauf(tmp_path, NETZ, *_pc_helfer(), SEITE_MIT_FANG,
                    "_naechste=antwort(200,'{}'); aus({r: await speichern(), rufe:_rufe.length});")
    assert echt == {"r": "fertig", "rufe": 1}
