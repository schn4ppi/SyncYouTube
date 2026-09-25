# -*- coding: utf-8 -*-
"""Kleine Fehler der Oberfläche (Gesamtprüfung Gruppe 6, 25.09.2026), jeweils
als echtes Seiten-JavaScript per deno ausgeführt.

F11: Im VLC-Modus stand die Zeitleiste der Kopfleiste gesperrt auf 0:00; nur
die Leiste im Player konnte VLC spulen. Beide nutzen jetzt dieselben Helfer.
"""
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

from test_medientasten_verhalten import _js_funktion, _lauf, _pc, _pc_helfer  # noqa: E402


# ------------------------------------------------------------------ F11

def _spul_teile(q):
    namen = ["zeit", "cmdSeekDrag", "cmdSeekEnd", "cmdSeekTick",
             "plbSeekDrag", "plbSeekEnd", "plbTick"]
    for extra in ("spulStand", "spulenAuf"):                # Helfer nach der Reparatur
        if f"function {extra}(" in q:
            namen.append(extra)
    return [
        "let plGeraet='browser', vlcPosLetzte=0, vlcDauerLetzte=0, _posMerkTs=Date.now();",
        "let cmdSeekAktiv=false, plbSeekAktiv=false; const _befehle=[];",
        "function vlcAktiv(){return plGeraet==='vlc';}",
        "async function vlcBefehl(c,a){_befehle.push([c,a]); return {};}",
        "function posMerken(){} function posMerkerMalen(){}",
        "function feld(id){_els[id]={id, value:0, disabled:true, textContent:''}; return _els[id];}",
        "['cmd-seek','cmd-t0','cmd-t1','plb-seek','plb-t0','plb-t1'].forEach(feld);",
        "function stand(p){return {wert:_els[p+'-seek'].value, gesperrt:_els[p+'-seek'].disabled,"
        " t0:_els[p+'-t0'].textContent, t1:_els[p+'-t1'].textContent};}",
        *[_js_funktion(q, n) for n in namen],
    ]


def test_kopfleiste_spult_auch_am_geraet_vlc(tmp_path):
    (e1, e2) = _lauf(tmp_path, *_spul_teile(_pc()),
                     "plGeraet='vlc'; vlcPosLetzte=50; vlcDauerLetzte=200;",
                     "cmdSeekTick(); plbTick(); aus({kopf:stand('cmd'), leiste:stand('plb')});",
                     "cmdSeekDrag(500); const t0=_els['cmd-t0'].textContent; cmdSeekEnd(500);"
                     " aus({t0, befehle:_befehle.slice(), pos:vlcPosLetzte});")
    assert e1["kopf"] == {"wert": 250, "gesperrt": False, "t0": "0:50", "t1": "3:20"}, e1
    assert e1["kopf"]["wert"] == e1["leiste"]["wert"] and e1["kopf"]["t1"] == e1["leiste"]["t1"]
    assert e2["t0"] == "1:40"
    assert e2["befehle"] == [["seek", {"wert": 100}]] and e2["pos"] == 100


def test_player_leiste_spult_am_geraet_vlc_wie_bisher(tmp_path):
    (e,) = _lauf(tmp_path, *_spul_teile(_pc()),
                 "plGeraet='vlc'; vlcPosLetzte=50; vlcDauerLetzte=200;",
                 "plbSeekDrag(250); const t0=_els['plb-t0'].textContent; plbSeekEnd(250);"
                 " aus({t0, befehle:_befehle.slice(), aktiv:plbSeekAktiv});")
    assert e == {"t0": "0:50", "befehle": [["seek", {"wert": 50}]], "aktiv": False}


def test_kopfleiste_im_browser_unveraendert(tmp_path):
    (e1, e2, e3) = _lauf(tmp_path, *_spul_teile(_pc()),
                         "const el=fakeMedia({id:'pl-el', duration:100, currentTime:25}); _els['pl-el']=el;",
                         "cmdSeekTick(); aus(stand('cmd'));",
                         "cmdSeekEnd(500); plbSeekEnd(800); aus({t:el.currentTime, befehle:_befehle.slice()});",
                         "delete _els['pl-el']; cmdSeekTick(); aus(stand('cmd'));")
    assert e1 == {"wert": 250, "gesperrt": False, "t0": "0:25", "t1": "1:40"}
    assert e2 == {"t": 80, "befehle": []}
    assert e3 == {"wert": 0, "gesperrt": True, "t0": "0:00", "t1": "0:00"}


def test_kopfleiste_vlc_ohne_dauer_bleibt_gesperrt(tmp_path):
    (e,) = _lauf(tmp_path, *_spul_teile(_pc()),
                 "plGeraet='vlc'; vlcDauerLetzte=0;",
                 "cmdSeekTick(); cmdSeekEnd(300); aus({kopf:stand('cmd'), befehle:_befehle.slice()});")
    assert e["kopf"]["gesperrt"] is True and e["befehle"] == []



# ------------------------------------------------------------------ F17
# Eine neue Playlist wurde als „die zuletzt gelistete“ geraten. Bei einem
# Fehler oder einer gleichzeitig angelegten Abo-Playlist landeten die Titel in
# der falschen Liste. Jetzt antwortet der Server mit der id.

def _playlist_teile(q, antwort_create):
    namen = ["plCreate", "queueAlsPlaylist", "plApi", "plLaden"]
    if "function plAnlegen(" in q:
        namen.append("plAnlegen")
    return [
        "let plState=[]; const _post=[]; const _toasts=[];",
        # derweil legte der Server eine Abo-Playlist an: sie steht am Ende der Liste
        "const _server=[{id:'neu1', name:'Neu', items:[]}, {id:'abo9', name:'Abo', items:[]}];",
        f"const _create={antwort_create};",
        "globalThis.fetch=async(url,opt)=>{",
        "  if(url==='/api/playlists')return {ok:true, json:async()=>({items:_server})};",
        "  const b=JSON.parse(opt.body); _post.push(b);",
        "  if(b.art==='create')return _create;",
        "  return {ok:true, json:async()=>({ok:true})};};",
        "globalThis.prompt=()=>'Neu'; function plMalen(){} function toast(t){_toasts.push(t);}",
        "let playerState={queue:['a|mp3','b|mp3'], idx:0};",
        "_els['plsel']={value:''};",
        *_pc_helfer(),
        *[_js_funktion(q, n) for n in namen],
    ]


OK_MIT_ID = "{ok:true, status:200, json:async()=>({ok:true, id:'neu1'})}"
ABGELEHNT = "{ok:false, status:403, json:async()=>({fehler:'nur_pc'})}"


def test_neue_playlist_wird_ueber_ihre_id_gewaehlt(tmp_path):
    (e,) = _lauf(tmp_path, *_playlist_teile(_pc(), OK_MIT_ID),
                 "await plCreate(); aus({sel:_els['plsel'].value});")
    assert e["sel"] == "neu1", "gewählt wurde die zuletzt gelistete statt der neuen Playlist"


def test_warteschlange_landet_in_der_neuen_playlist(tmp_path):
    (e,) = _lauf(tmp_path, *_playlist_teile(_pc(), OK_MIT_ID),
                 "await queueAlsPlaylist(); aus({adds:_post.filter(b=>b.art==='add').map(b=>b.id)});")
    assert e["adds"] == ["neu1", "neu1"]


def test_gescheiterte_anlage_fuellt_keine_fremde_playlist(tmp_path):
    (e1, e2) = _lauf(tmp_path, *_playlist_teile(_pc(), ABGELEHNT),
                     "await plCreate(); aus({sel:_els['plsel'].value});",
                     "await queueAlsPlaylist(); aus({adds:_post.filter(b=>b.art==='add').length,"
                     " toasts:_toasts});")
    assert e1["sel"] == ""
    assert e2["adds"] == 0 and any("nicht anlegen" in t for t in e2["toasts"])


# ------------------------------------------------------------------ F26

def test_hilfe_zum_ansicht_menue_nennt_nur_vorhandene_eintraege():
    """Die Hilfe nannte im ⚙-Ansicht-Menü noch „Ordner-Import“; den Menüpunkt
    gibt es seit Build 122 nicht mehr (der Ordner-Blick läuft von selbst).
    Geprüft wird jeder genannte Eintrag gegen das Menü (ohne Kommentare)."""
    import re
    q = _pc()
    zeile = next(z for z in q.splitlines() if "<b>⚙ Ansicht</b> bündelt" in z)
    genannt = re.sub(r"<[^>]+>", "", zeile.split("Darstellung:", 1)[1]).strip()
    eintraege = [e.strip() for e in genannt.split(",")][1:]   # der erste sind die vier Knöpfe
    menue = q[q.index('id="libansicht"'):q.index('id="libcolmenu"')]
    menue = re.sub(r"<!--.*?-->", "", menue, flags=re.S)
    fehlt = [e for e in eintraege if e not in menue]
    assert eintraege and not fehlt, f"die Hilfe nennt, was es im Menü nicht gibt: {fehlt}"


# ------------------------------------------------------------------ F27
# Der einzige ungeschützte localStorage-Zugriff auf oberster Ebene: ist der
# Speicher gesperrt (Browser-Einstellung, Datenschutzmodus), wirft schon der
# Zugriff, und das ganze Skript der Seite bricht ab.

GESPERRT = ("Object.defineProperty(globalThis, 'localStorage', {configurable:true,"
            " get(){throw new Error('SecurityError: Speicher gesperrt');}});"
            "Object.defineProperty(globalThis, 'sessionStorage', {configurable:true,"
            " get(){throw new Error('SecurityError: Speicher gesperrt');}});")


def test_geraete_wahl_ueberlebt_gesperrten_speicher(tmp_path):
    from test_medientasten_verhalten import _js_zeile
    (e,) = _lauf(tmp_path, GESPERRT, *_pc_helfer(), _js_zeile(_pc(), "let plGeraet"),
                 "aus({plGeraet});")
    assert e == {"plGeraet": "browser"}


def test_neuladen_ueberlebt_gesperrten_speicher(tmp_path):
    """Seit F10 fragt auch das Titelende uiNeuLaden(); wirft dort der gesperrte
    Sitzungsspeicher, bliebe die Musik am Titelende stehen."""
    from test_oberflaeche_laden import _neuladen_teile
    teile = [t for t in _neuladen_teile(_pc()) if not t.startswith("const _ss=")]   # ohne Speicher-Attrappe
    (e,) = _lauf(tmp_path, GESPERRT, *teile,
                 "const el=fakeMedia({id:'pl-el', paused:false}); _els['pl-el']=el;",
                 "uiStandPruefen('a'); uiStandPruefen('b');",
                 "el.paused=true; el.ended=true; plTitelEnde({target:el}); aus({log:_log.slice()});")
    assert e["log"] == ["reload"], e


# ------------------------------------------------ Orchestrator-Entscheide (Gruppe 6d)
# M3U-Import über 2 MB: der Server weist den Körper mit 413 ab (S14), die Seite
# meldete trotzdem „Import ✓ — 0 Titel gefunden“. Jetzt ehrlich „zu groß“.

def _import_teile(q, antwort):
    return [
        "const _info=[]; const _post=[]; function plInfo(t){_info.push(t);}",
        "async function plLaden(){} function plMalen(){} globalThis.prompt=()=>'Liste';",
        "_els['plsel']={value:''};",
        f"globalThis.fetch=async(url,opt)=>{{_post.push(url); return {antwort};}};",
        "function datei(n){return {files:[{name:'liste.m3u', text:async()=>'#EXTM3U '+'x'.repeat(n)}], value:'x'};}",
        *_pc_helfer(),
        _js_funktion(q, "plImport"),
    ]


def test_m3u_ueber_zwei_mb_meldet_zu_gross(tmp_path):
    ok = "{ok:true, status:200, json:async()=>({ok:true, id:'p1', gefunden:3})}"
    (e,) = _lauf(tmp_path, *_import_teile(_pc(), ok),
                 "await plImport(datei(2*1024*1024+10)); aus({info:_info, post:_post.length});")
    assert e["post"] == 0, "eine zu große Datei muss gar nicht erst geschickt werden"
    assert len(e["info"]) == 1 and "zu groß" in e["info"][0] and "✓" not in e["info"][0], e


def test_m3u_abgewiesen_meldet_den_grund(tmp_path):
    zu_gross = "{ok:false, status:413, json:async()=>({fehler:'Anfrage zu groß (höchstens 2 MB)'})}"
    (e,) = _lauf(tmp_path, *_import_teile(_pc(), zu_gross),
                 "await plImport(datei(100)); aus({info:_info});")
    assert "zu groß" in e["info"][-1] and "✓" not in e["info"][-1], e
    nur_pc = "{ok:false, status:403, json:async()=>({fehler:'Nur am PC möglich.', nur_pc:true})}"
    (e,) = _lauf(tmp_path, *_import_teile(_pc(), nur_pc),
                 "await plImport(datei(100)); aus({info:_info});")
    assert "Nur am PC" in e["info"][-1] and "✓" not in e["info"][-1], e


def test_m3u_import_gelingt_wie_bisher(tmp_path):
    ok = "{ok:true, status:200, json:async()=>({ok:true, id:'p1', gefunden:3})}"
    (e,) = _lauf(tmp_path, *_import_teile(_pc(), ok),
                 "await plImport(datei(100)); aus({info:_info, sel:_els['plsel'].value});")
    assert e == {"info": ["Import ✓ — 3 Titel gefunden"], "sel": "p1"}
