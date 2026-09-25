# -*- coding: utf-8 -*-
"""Zugang auf den Seiten selbst (Gesamtprüfung Gruppe 5, JB-Entscheid 7a Punkt 1, 25.09.2026).

Der Server setzt Geräte-Token und Code seit dem 25.09. als HttpOnly-Cookie
(tests/test_wlan_rechte.py). Hier das Gegenstück in den Seiten, als echtes
Seiten-JavaScript per deno ausgeführt:
  * Kopplungsseite: der Token landet nicht mehr im localStorage; ein alter
    Eintrag geht EINMAL an den Server und ist danach weg.
  * Handy-Seite: der Code landet nicht mehr im localStorage; ein alter
    Eintrag geht EINMAL an den Server und ist danach weg; Medien-Adressen
    tragen den Code nur, wenn der Browser kein Cookie nimmt.
  * PC-Oberfläche auf einem Gerät im WLAN: Einstellungen und nur-PC-Aktionen
    sind ausgeblendet; eine trotzdem abgewiesene Aktion meldet sich einmal.
"""
import json
import os
import re
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

from test_medientasten_verhalten import _handy, _js_funktion, _js_zeile, _lauf, _pc  # noqa: E402

# localStorage mit removeItem und Spur; location/history als Attrappe.
SPEICHER = r"""
const _spur=[];
Object.defineProperty(globalThis,'localStorage',{configurable:true,writable:true,
  value:{_d:{}, getItem(k){return k in this._d?this._d[k]:null;},
  setItem(k,v){_spur.push('set:'+k); this._d[k]=String(v);}, removeItem(k){_spur.push('weg:'+k); delete this._d[k];}}});
Object.defineProperty(globalThis,'location',{configurable:true,writable:true,
  value:{search:'',pathname:'/',href:'/',replace(u){_spur.push('replace:'+u);}}});
Object.defineProperty(globalThis,'history',{configurable:true,writable:true,
  value:{replaceState(a,b,u){_spur.push('ersetzt:'+u);}}});
"""


# ------------------------------------------------------------ Kopplungsseite

def _koppel_skript():
    import profil_geraete
    html = profil_geraete.PAIRING_HTML
    return html[html.index("<script>") + 8:html.index("</script>")]


def test_koppelseite_speichert_den_token_nicht_mehr(tmp_path):
    q = _koppel_skript()
    (e,) = _lauf(
        tmp_path, SPEICHER,
        "_els.code={textContent:''}; const _takte=[];",
        "globalThis.setInterval=(f)=>{_takte.push(f); return 1;}; globalThis.clearInterval=()=>{};",
        "globalThis.fetch=async(u,o)=>{_spur.push('fetch:'+u); return {json:async()=>("
        "u.startsWith('/api/geraet_anmelden')?{geraet_id:'g1',code:'ABC123'}:{token:'TOK42',profil:'kinder'})};};",
        _js_funktion(q, "koppeln"),
        "await koppeln(); await _takte[0]();",
        "aus({spur:_spur, speicher:localStorage._d, code:_els.code.textContent});")
    assert e["code"] == "ABC123"
    assert "replace:/?geraet=TOK42" in e["spur"], "der Server macht aus dem Token ein Cookie"
    assert "ytdl_geraet_token" not in e["speicher"] and "set:ytdl_geraet_token" not in e["spur"], e
    assert e["speicher"].get("ytdl_profil") == "kinder", "die Profil-Wahl ist kein Geheimnis und bleibt"


def test_koppelseite_schickt_einen_alten_token_einmal_und_entfernt_ihn(tmp_path):
    q = _koppel_skript()
    (e,) = _lauf(
        tmp_path, SPEICHER,
        "localStorage._d.ytdl_geraet_token='ALT99'; _els.code={textContent:''};",
        "globalThis.setInterval=()=>1; globalThis.fetch=async(u)=>{_spur.push('fetch:'+u); return {json:async()=>({})};};",
        _js_funktion(q, "koppeln"),
        "await koppeln(); aus({spur:_spur, speicher:localStorage._d});")
    assert e["spur"] == ["weg:ytdl_geraet_token", "replace:/?geraet=ALT99"], e
    assert e["speicher"] == {}


def test_koppelseite_eines_gekoppelten_geraets_meldet_es_nicht_neu_an(tmp_path):
    """SameSite=Strict: öffnet eine fremde App (QR-Scanner) die Seite, schickt
    der Browser das Cookie beim ersten Laden womöglich nicht mit, und ein
    gekoppeltes Gerät sähe die Kopplungsseite. Ein Abruf AUS der Seite trägt
    es: gilt der Zugang, geht es zurück auf die Startseite statt in eine neue
    Anmeldung. Die Schleifenwache entscheidet über die Zeit (Abnahme
    25.09.2026): landet das Gerät binnen 30 s wieder hier, ist es eine Schleife
    und es wird angemeldet; öffnet der TV-Starter denselben Tab später noch
    einmal, geht es wieder zurück (vorher nur einmal je Browser-Sitzung, und
    am PC erschien eine überflüssige Kopplungsanfrage)."""
    q = _koppel_skript()
    (e1, e2, e3, e4) = _lauf(
        tmp_path, SPEICHER,
        "let _sitzung={}; Object.defineProperty(globalThis,'sessionStorage',{configurable:true,writable:true,"
        " value:{getItem:k=>_sitzung[k]||null, setItem:(k,v)=>{_sitzung[k]=String(v);}}});",
        "let _uhr=1790000000000; Date.now=()=>_uhr;",
        "_els.code={textContent:''}; globalThis.setInterval=()=>1;",
        "globalThis.fetch=async(u)=>{_spur.push('fetch:'+u); return {ok:u==='/api/status',status:200,"
        " json:async()=>(u.startsWith('/api/geraet_anmelden')?{geraet_id:'g',code:'C'}:{})};};",
        _js_funktion(q, "koppeln"),
        "await koppeln(); aus({spur:_spur.slice()}); _spur.length=0;",
        "_uhr+=2000; await koppeln(); aus({spur:_spur.slice()}); _spur.length=0;",
        "_sitzung={}; _uhr+=600000; await koppeln(); aus({spur:_spur.slice()}); _spur.length=0;",
        "_uhr+=60000; await koppeln(); aus({spur:_spur.slice()});")
    assert e1["spur"] == ["fetch:/api/status", "replace:/"], e1
    assert "fetch:/api/geraet_anmelden" in e2["spur"] and "replace:/" not in e2["spur"], \
        f"nach 2 s ist es eine Schleife: {e2}"
    assert e3["spur"] == ["fetch:/api/status", "replace:/"], e3
    assert e4["spur"] == ["fetch:/api/status", "replace:/"], f"nach 60 s wieder zurück, keine neue Anfrage: {e4}"


def test_koppelseite_nimmt_den_merker_der_alten_fassung(tmp_path):
    """Die alte Fassung merkte '1' statt einer Zeit: kein Hindernis für den Rücksprung."""
    q = _koppel_skript()
    (e,) = _lauf(
        tmp_path, SPEICHER,
        "const _sitzung={ytdl_koppeln_zurueck:'1'}; Object.defineProperty(globalThis,'sessionStorage',"
        "{configurable:true,writable:true,value:{getItem:k=>_sitzung[k]||null, setItem:(k,v)=>{_sitzung[k]=String(v);}}});",
        "_els.code={textContent:''}; globalThis.setInterval=()=>1;",
        "globalThis.fetch=async(u)=>{_spur.push('fetch:'+u); return {ok:u==='/api/status',status:200,"
        " json:async()=>({})};};",
        _js_funktion(q, "koppeln"), "await koppeln(); aus({spur:_spur.slice(), merker:_sitzung.ytdl_koppeln_zurueck});")
    assert e["spur"] == ["fetch:/api/status", "replace:/"], e
    assert int(e["merker"]) > 1_000_000_000_000, "gemerkt wird die Zeit des Sprungs"


# ------------------------------------------------------------ Handy-Seite

def _handy_teile(q):
    return [SPEICHER,
            "_els.code={value:''}; _els.loginfehler={textContent:''}; _els.tipp={textContent:''};",
            "let _keks=false, _codeRichtig='ABCDE23456', _kekseNehmen=true;",
            # Server-Attrappe: X-Code richtig -> 200 + Cookie; Cookie -> 200; sonst 403
            "globalThis.fetch=async(u,o)=>{const k=(o&&o.headers&&o.headers['X-Code'])||'';"
            " _spur.push('fetch:'+u+(k?' X-Code='+k:''));"
            " const adr=(u.match(/[?&]code=([^&]+)/)||[])[1]||'';"
            " const ok=(k===_codeRichtig)||(adr===_codeRichtig)||_keks;"
            " if((k===_codeRichtig||adr===_codeRichtig)&&_kekseNehmen)_keks=true;"
            " return {ok, status:ok?200:403, json:async()=>(ok?{items:[]}:{fehler:'Kein Zugriff'})};};",
            "let aktuell=null; const _gezeigt=[]; function appZeigen(){_gezeigt.push(1);}",
            _js_zeile(q, "let KOPF"),
            _js_zeile(q, "let dev"),
            _js_funktion(q, "lsLesen"), _js_funktion(q, "lsWeg"),
            _js_funktion(q, "api"), _js_funktion(q, "mitCode"),
            _js_funktion(q, "codePruefen"), _js_funktion(q, "anmelden"), _js_funktion(q, "starten")]


def test_handy_speichert_den_code_nicht_und_meldet_sich_per_cookie_an(tmp_path):
    q = _handy()
    (e,) = _lauf(tmp_path, *_handy_teile(q),
                 "_els.code.value=' abcde-23456 '; await anmelden();",
                 "aus({spur:_spur, speicher:localStorage._d, gezeigt:_gezeigt.length, kopf:KOPF,"
                 " media:mitCode('/media?id=x'), feld:_els.code.value});")
    assert "fetch:/api/status X-Code=ABCDE23456" in e["spur"], "Leerraum und Bindestrich raus, groß"
    assert "set:ytdl_code" not in e["spur"] and "ytdl_code" not in e["speicher"], e
    assert e["gezeigt"] == 1 and e["kopf"] == "", "das Cookie trägt den Zugang"
    assert "code=" not in e["media"], "Medien-Adressen brauchen den Code nicht mehr"
    assert e["feld"] == "", "der Code bleibt nicht im Eingabefeld stehen"


def test_handy_ohne_cookies_nutzt_den_code_nur_solange_die_seite_offen_ist(tmp_path):
    q = _handy()
    (e,) = _lauf(tmp_path, *_handy_teile(q),
                 "_kekseNehmen=false; _els.code.value='ABCDE23456'; await anmelden();",
                 "aus({speicher:localStorage._d, gezeigt:_gezeigt.length, kopf:KOPF,"
                 " media:mitCode('/media?id=x'), tipp:_els.tipp.textContent});")
    assert e["gezeigt"] == 1 and e["kopf"] == "ABCDE23456"
    assert e["media"] == "/media?id=x&code=ABCDE23456", "Rückfall: der Code in der Medien-Adresse"
    assert e["speicher"] == {}, "auch dann nie im localStorage"


def test_handy_alter_code_geht_einmal_zum_server_und_ist_danach_weg(tmp_path):
    q = _handy()
    (richtig, falsch) = _lauf(
        tmp_path, *_handy_teile(q),
        "localStorage._d.ytdl_code='ABCDE23456'; await starten();",
        "aus({spur:_spur.slice(), speicher:{...localStorage._d}, gezeigt:_gezeigt.length});",
        "_spur.length=0; _keks=false; _gezeigt.length=0; localStorage._d.ytdl_code='FALSCH2345'; await starten();",
        "aus({spur:_spur.slice(), speicher:{...localStorage._d}, gezeigt:_gezeigt.length,"
        " fehler:_els.loginfehler.textContent});")
    assert richtig["spur"].count("fetch:/api/status X-Code=ABCDE23456") == 1, richtig
    assert "weg:ytdl_code" in richtig["spur"] and richtig["speicher"] == {}
    assert richtig["gezeigt"] == 1, "mit dem alten, noch gültigen Code geht es ohne Eingabe weiter"
    assert "weg:ytdl_code" in falsch["spur"] and falsch["speicher"] == {}, "auch ein falscher Code geht weg"
    assert falsch["gezeigt"] == 0


def test_handy_zeigt_fernsteuerung_aus_statt_falscher_code(tmp_path):
    q = _handy()
    (e,) = _lauf(tmp_path, *_handy_teile(q),
                 "globalThis.fetch=async()=>({ok:false,status:403,json:async()=>"
                 "({fehler:'Fernsteuerung am PC ausgeschaltet.'})});",
                 "_els.code.value='ABCDE23456'; await anmelden(); aus({f:_els.loginfehler.textContent});")
    assert e["f"] == "Fernsteuerung am PC ausgeschaltet."


# ------------------------------------------------------------ PC-Oberfläche auf einem Gerät im WLAN

KLASSEN = r"""
function _klassen(){const s=new Set(); return {add:x=>s.add(x), remove:x=>s.delete(x),
  toggle:(x,an)=>{if(an===undefined?!s.has(x):an)s.add(x); else s.delete(x);}, contains:x=>s.has(x), _s:s};}
document.body={classList:_klassen(), appendChild(){}};
"""


def test_status_schaltet_den_fern_modus(tmp_path):
    q = _pc()
    (e,) = _lauf(tmp_path, KLASSEN,
                 _js_zeile(q, "let NUR_FERN"), _js_funktion(q, "fernModusSetzen"),
                 "fernModusSetzen(true); const a=document.body.classList.contains('fern');",
                 "fernModusSetzen(false); const b=document.body.classList.contains('fern');",
                 "fernModusSetzen(undefined); const c=NUR_FERN;",
                 "NUR_FERN=false; document.body.classList.remove('fern'); fernModusSetzen(undefined);",
                 "const d=NUR_FERN||document.body.classList.contains('fern');",
                 "aus({a,b,c,d});")
    # Ein Status ohne das Feld ändert nichts: er kommt vom noch laufenden alten
    # Server, der die neue Seite schon heiß nachlädt (bis zu seinem
    # Selbst-Neustart). Die PC-Seite bleibt dann PC (d), ein Gerät bleibt Gerät (c).
    assert e == {"a": False, "b": True, "c": True, "d": False}, e


def _menue_rendern(q, funktion, aufruf, nur_fern):
    """Ein Menü der Oberfläche bauen lassen und die sichtbaren Einträge lesen."""
    return [
        KLASSEN,
        _js_zeile(q, "let NUR_FERN"), _js_funktion(q, "nurPc"), _js_funktion(q, "menuFuerGeraet"),
        f"NUR_FERN={'true' if nur_fern else 'false'};",
        "const _menues=[]; document.createElement=()=>{const m={style:{},querySelectorAll:()=>[]};"
        " _menues.push(m); return m;}; document.querySelectorAll=()=>[];",
        "function popoverBei(){} function menuSchliesser(){} function menuGeradeZu(){return false;}",
        # Funktionen, die die Menüs nur als Wert ablegen (nie aufgerufen)
        "function plTogglePlay(){} function playerPrev(){} function playerNext(){} function vlcNeustart(){}"
        " function playerYoutube(){} function playerExtern(){} function queueWerkzeugListe(){return [];}",
        "let libAuswahl=new Set(), libPlaylistView=null, plGeraet='browser', playSpeed=1, subMode='aus',"
        " subSprachen=[], subLang='', subCues=null, subRomaji=false, vizMode='', VIZMODES=[], SUBMODES=[];",
        "const _x={id:'k1',titel:'T',vorhanden:true,url:'https://www.youtube.com/watch?v=k1',"
        "hat_geschwister:true};",
        "function libFind(){return _x;} function gruppeVon(){return [_x];} function aktKey(){return 'k1';}",
        "const playerState={queue:['k1','k2'],idx:0};",
        _js_funktion(q, "kontextMenuBauen") if funktion != "kontextMenuBauen" else "",
        _js_funktion(q, funktion),
        aufruf,
        "aus({html:_menues.map(m=>m.innerHTML||'').join('|')});",
    ]


def _labels(html):
    return re.findall(r"<button[^>]*>([^<]+)", html)


def test_bibliotheks_menue_zeigt_im_wlan_keine_nur_pc_aktionen(tmp_path):
    q = _pc()
    aufruf = "libItemMenu({stopPropagation(){},currentTarget:{getBoundingClientRect(){return {};}}},'k1');"
    (pc,) = _lauf(tmp_path, *_menue_rendern(q, "libItemMenu", aufruf, False))
    (fern,) = _lauf(tmp_path, *_menue_rendern(q, "libItemMenu", aufruf, True))
    alle, wlan = _labels(pc["html"]), _labels(fern["html"])
    for text in ("Papierkorb", "Im Ordner zeigen", "Ausschnitt schneiden", "Zu Playlist",
                 "Archiv", "Meistgespielt", "Wiedergabe"):
        assert any(text in t for t in alle), (text, alle)
        assert not any(text in t for t in wlan), (text, wlan)
    for text in ("Abspielen", "Als Nächstes", "Auf YouTube öffnen", "Eigenschaften"):
        assert any(text in t for t in wlan), (text, wlan)


def test_player_und_playlist_menue_im_wlan(tmp_path):
    q = _pc()
    for funktion, aufruf, weg in (
            ("playerKontext", "playerKontext({preventDefault(){},stopPropagation(){},clientX:1,clientY:1});",
             ("Zu Playlist", "Ausschnitt schneiden", "Im Ordner zeigen", "extern öffnen")),
            ("plItemKontext", "plItemKontext({preventDefault(){},stopPropagation(){},clientX:1,clientY:1},0);",
             ("Im Ordner zeigen",))):
        (pc,) = _lauf(tmp_path, *_menue_rendern(q, funktion, aufruf, False))
        (fern,) = _lauf(tmp_path, *_menue_rendern(q, funktion, aufruf, True))
        for text in weg:
            assert any(text in t for t in _labels(pc["html"])), (funktion, text)
            assert not any(text in t for t in _labels(fern["html"])), (funktion, text)
        assert _labels(fern["html"]), "das Menü bleibt, nur ohne nur-PC-Einträge"


def test_einstellungen_oeffnen_sich_im_wlan_nicht(tmp_path):
    q = _pc()
    (pc, fern) = _lauf(
        tmp_path, KLASSEN, _js_zeile(q, "let NUR_FERN"),
        "const _t=[]; function toast(x){_t.push(x);} function einstellungenModalInit(){}",
        "_els.settingsmodal={style:{display:'none'}};",
        _js_funktion(q, "einstellungenOeffnen"),
        "einstellungenOeffnen(); aus({d:_els.settingsmodal.style.display, t:_t.slice()});",
        "_els.settingsmodal.style.display='none'; NUR_FERN=true;",
        "einstellungenOeffnen(); aus({d:_els.settingsmodal.style.display, t:_t.slice()});")
    assert pc["d"] == "flex" and pc["t"] == []
    assert fern["d"] == "none" and fern["t"] and "PC" in fern["t"][0]


def test_nur_pc_elemente_sind_markiert_und_die_regel_blendet_sie_aus():
    """Der ⚙-Weg und die Abo-Knöpfe tragen die Klasse nur-pc; die CSS-Regel
    blendet sie auf Geräten im WLAN aus (body.fern)."""
    from html.parser import HTMLParser
    q = _pc()

    class Knopf(HTMLParser):
        gefunden = {}

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "button" and a.get("onclick") in ("abosZeigen()", "dlboxTab('abos')"):
                Knopf.gefunden[a["onclick"]] = (a.get("class") or "").split()
    Knopf().feed(q)
    assert set(Knopf.gefunden) == {"abosZeigen()", "dlboxTab('abos')"}, Knopf.gefunden
    assert all("nur-pc" in k for k in Knopf.gefunden.values()), Knopf.gefunden
    assert re.search(r"body\.fern \.nur-pc\s*\{\s*display:\s*none\s*!important", q), "CSS-Regel fehlt"


def test_optionen_menue_im_wlan_ohne_einstellungen(tmp_path):
    q = _pc()
    stubs = ("function fensterAbstand(){return 0;} const SKINS=[]; let uebergang='normal', crossfadeSek=0,"
             " normAn=false, canvasAn=false, sleepTitelende=false, sleepEndeZeit=0, sleepStufe='0';"
             " const PL_AR=[]; function klickArt(){return 'doppel';} function plqRahmenArt(){return 'auto';}"
             " function aktuellerSkin(){return '';} function sprungWeite(){return 5;} function sleepLabel(){}"
             " function subStilInit(){} function fernInfoMalen(){} function popoverBei(){}"
             " let daten={config:{fehler_ausblenden_min:5}};")
    (e,) = _lauf(
        tmp_path, KLASSEN, stubs,
        "const _m=[]; document.createElement=()=>{const m={style:{},querySelector:()=>null}; _m.push(m); return m;};",
        "document.body.appendChild=()=>{}; document.addEventListener=()=>{};",
        _js_funktion(q, "optionenToggle"),
        "optionenToggle({stopPropagation(){},currentTarget:{getBoundingClientRect(){return {};}}});",
        "aus({html:_m[0].innerHTML});")
    zeilen = re.findall(r'<div class="optrow([^"]*)"[^>]*>(?:<span>)?([^<]*)', e["html"])
    klassen = {text.strip(): k for k, text in zeilen}
    for text in ("Fehler ausblenden", "Dateinamen", "Wiedergabe-Standard", "Alle Einstellungen",
                 "📱 Fernsteuerung", "📺 Geräte (TV/Handy)"):
        assert "nur-pc" in klassen.get(text, ""), (text, klassen)
    for text in ("Look", "Übergang zwischen Titeln", "📺 Fernsehmodus"):
        assert "nur-pc" not in klassen.get(text, "x"), (text, klassen)


def test_abgewiesene_aktion_meldet_sich_einmal(tmp_path):
    q = _pc()
    (e,) = _lauf(
        tmp_path, _js_zeile(q, "let NUR_FERN"), "NUR_FERN=true; const _t=[]; function toast(x){_t.push(x);}",
        "globalThis.fetch=async(u)=>({status:403,ok:false,clone(){return this;},"
        " json:async()=>({fehler:'Nur am PC: schreibt config.json.',nur_pc:true})});",
        _js_zeile(q, "const _nurPcGemeldet"), _js_funktion(q, "fetchHuelleSetzen"),
        "fetchHuelleSetzen();",
        "await fetch('/api/wiedergabe',{method:'POST'}); await fetch('/api/wiedergabe?x=1');",
        "await new Promise(r=>setTimeout(r,0)); aus({t:_t});")
    assert len(e["t"]) == 1 and "config.json" in e["t"][0], e


def test_laden_setzt_den_fern_modus_aus_dem_status(tmp_path):
    q = _pc()
    (e,) = _lauf(
        tmp_path, KLASSEN, _js_zeile(q, "let NUR_FERN"), _js_funktion(q, "fernModusSetzen"),
        "let daten=null; function apiStatus(){} function configFuellen(){} function malen(){}",
        "function remoteAusfuehren(){} function nachschubMelden(){} function subStilVomServer(){}",
        "function uiStandPruefen(){}",
        "globalThis.fetch=async()=>({ok:true,status:200,json:async()=>({lokal:false,items:[],config:{}})});",
        _js_funktion(q, "laden"),
        "await laden(); aus({fern:NUR_FERN, klasse:document.body.classList.contains('fern')});")
    assert e == {"fern": True, "klasse": True}
    assert json.dumps(e)


def test_download_box_ohne_nur_pc_aktionen_im_wlan(tmp_path):
    """„📂 Zielordner“ (öffnet den Explorer am PC) und der Abos-Reiter samt
    „🔄 Jetzt prüfen“ gehören dem PC; „🧹 Aufräumen“ bleibt."""
    q = _pc()
    dlaction = re.search(r"^const DLACTION=.*?;$", q, re.M | re.S).group(0)
    teile = [KLASSEN, _js_zeile(q, "let NUR_FERN"),
             "let miniAn=false, dlboxAktiv='queue'; const DLV=['queue','done','log','abos'];", dlaction,
             "_els.dlbox={}; _els['dlbox-body']={style:{},appendChild(){}}; _els['dlbox-tabs']={style:{}};",
             "_els['dlbox-action']={style:{},textContent:'',setAttribute(){}}; _els.stash={appendChild(){}};",
             "document.querySelectorAll=()=>[]; function aboLaden(){}",
             _js_funktion(q, "dlboxRender")]
    zeige = "aus({aktiv:dlboxAktiv, knopf:_els['dlbox-action'].style.display, text:_els['dlbox-action'].textContent});"
    (pc_q, pc_abos, fern_q, fern_abos, fern_done) = _lauf(
        tmp_path, *teile,
        "dlboxRender();", zeige, "dlboxAktiv='abos'; dlboxRender();", zeige,
        "NUR_FERN=true; dlboxAktiv='queue'; _els['dlbox-action'].style.display=''; dlboxRender();", zeige,
        "dlboxAktiv='abos'; dlboxRender();", zeige,
        "dlboxAktiv='done'; dlboxRender();", zeige)
    assert pc_q["knopf"] == "" and "Zielordner" in pc_q["text"]
    assert pc_abos["aktiv"] == "abos" and pc_abos["knopf"] == ""
    assert fern_q["knopf"] == "none"
    assert fern_abos["aktiv"] == "queue" and fern_abos["knopf"] == "none"
    assert fern_done["knopf"] == "" and "Aufräumen" in fern_done["text"]


def test_playlist_werkzeuge_im_wlan_ohne_verwaltung(tmp_path):
    """Die Playlist-Werkzeuge (⋯ an der Playlist und im Player) laufen über
    einen dritten Menü-Motor (aktionsMenu): Umbenennen, Löschen, Sync, Import,
    Wiedergabe-Regeln und „Als Playlist speichern“ gehen nur am PC."""
    q = _pc()
    for funktion, weg in (("plWerkzeuge", ("Umbenennen", "Löschen", "Sync einrichten",
                                           "Jetzt synchronisieren", "importieren")),
                          ("plWerkzeugeImPlayer", ("Umbenennen", "Sync einrichten", "importieren",
                                                   "Wiedergabe", "Als Playlist speichern"))):
        ergebnisse = []
        for fern in (False, True):
            teile = _menue_rendern(q, funktion, f"{funktion}({{stopPropagation(){{}},"
                                   "currentTarget:{getBoundingClientRect(){return {};}}});", fern)
            teile.insert(-2, _js_funktion(q, "aktionsMenu"))
            teile.insert(-2, _js_funktion(q, "queueWerkzeugListe"))
            teile.insert(-2, "function entdeckerOeffnen(){} function plRename(){} function plDelete(){}"
                             " function plSyncConfig(){} function plSyncNow(){} function plExport(){}"
                             " function queueAlsPlaylist(){} function queueUmkehren(){} function queueDuplikate(){}"
                             " function queueLeeren(){} function mixeMenu(){} globalThis.getComputedStyle=()=>({});"
                             " document.querySelector=()=>null;")
            teile = [t.replace("function queueWerkzeugListe(){return [];}", "") for t in teile]
            (e,) = _lauf(tmp_path, *teile)
            ergebnisse.append(_labels(e["html"]))
        pc, wlan = ergebnisse
        for text in weg:
            assert any(text in t for t in pc), (funktion, text, pc)
            assert not any(text in t for t in wlan), (funktion, text, wlan)
        assert any("exportieren" in t for t in wlan), "Lesen (Export) bleibt"


def test_direkte_nur_pc_knoepfe_tragen_die_klasse(tmp_path):
    """Knöpfe außerhalb der Menüs: ＋ (Titel in Playlist), ↻ Fehlende Infos
    nachladen (schreibt Metadaten), 🏷 Auto-Tagging und ✂ in der Player-Leiste."""
    from html.parser import HTMLParser
    q = _pc()

    class Knoepfe(HTMLParser):
        def __init__(self):
            super().__init__()
            self.gefunden = {}

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "button" and a.get("onclick"):
                self.gefunden.setdefault(a["onclick"], (a.get("class") or "").split())

    statisch = Knoepfe()
    statisch.feed(q)
    for onclick in ("bulkPlaylist(event)", "libEnrich(this)", "autotagAlle();ansichtZu()"):
        assert "nur-pc" in statisch.gefunden.get(onclick, []), (onclick, statisch.gefunden.get(onclick))
    for onclick in ("plView()", "plWerkzeuge(event)", "dublettenPopover(event);ansichtZu()"):
        assert "nur-pc" not in statisch.gefunden.get(onclick, ["fehlt"]), onclick
    (e,) = _lauf(tmp_path, "let plGeraet='browser', playSpeed=1, plVol=100; function ico(){return '';}",
                 _js_funktion(q, "plBarHTML"), "aus({html:plBarHTML(true)});")
    leiste = Knoepfe()
    leiste.feed(e["html"])
    assert "nur-pc" in leiste.gefunden.get("clipDialog(aktKey())", []), leiste.gefunden.get("clipDialog(aktKey())")
    assert "nur-pc" not in leiste.gefunden.get("subMenu(event)", ["fehlt"])


def test_download_zeile_ohne_trotzdem_und_ordner_im_wlan(tmp_path):
    """„▶ Trotzdem“ ersetzt eine vorhandene Datei, „📂 Ordner“ öffnet den
    Explorer am PC: beides lehnt der Server aus dem WLAN ab (Abnahme
    25.09.2026). Auf einem Gerät im WLAN stehen die Knöpfe darum nicht in der
    aufgeklappten Download-Zeile; Weiter, Pause und Entfernen bleiben."""
    q = _pc()
    teile = [_js_zeile(q, "let NUR_FERN"),
             "let daten={jetzt:0}; const offeneQueue=new Set(['u1','f1']);",
             "function esc(t){return String(t==null?'':t);} function balkenAscii(){return '';}"
             " function mb(){return '';} function zeit(){return '';} function tempo(){return '';}",
             _js_funktion(q, "kurzfehler"), _js_funktion(q, "reihe"),
             "const u={id:'u1',status:'uebersprungen',titel:'T',qualitaet:'beste',datei:'x.mp4',gesamt:1};",
             "const f={id:'f1',status:'fehler',titel:'T',qualitaet:'beste',fehler:'x'};",
             "aus({u:reihe(u), f:reihe(f)}); NUR_FERN=true; aus({u:reihe(u), f:reihe(f)});"]
    (pc, fern) = _lauf(tmp_path, *teile)
    assert "Trotzdem" in pc["u"] and "'ordner'" in pc["u"], pc["u"]
    assert "Trotzdem" not in fern["u"] and "'ordner'" not in fern["u"], fern["u"]
    assert "'entfernen'" in fern["u"] and "Abspielen" in fern["u"]
    assert "'weiter'" in fern["f"], "Weiter nach einem Fehler bleibt im WLAN"
