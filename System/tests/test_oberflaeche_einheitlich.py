# -*- coding: utf-8 -*-
"""Zwei kleine Sichtänderungen (JB-Entscheid 7a Punkt 8, Gesamtprüfung Gruppe 7).

Gedämpfte Farbe: Die feste gedämpfte Textfarbe #8a7d74 stand 26-mal inline im
Markup und in erzeugtem HTML (25 Stil-Attribute, ein Wert in einem Ausdruck). Inline-Stile erreicht keine Regel des Tag-Modus,
deshalb blieb sie dort hell-auf-hell (die Regeln des Tag-Modus nehmen für
gedämpften Text #7a6e64). Jetzt steht sie als Variable `--gedaempft` einmal im
Stil, und der Tag-Modus setzt sie um.

Untermenüs: Es gab zwei Motoren. Das Bibliotheks-Menü (`libItemMenu`) baute
sich selbst und tauschte für „Zu Playlist“ und „Ausschnitte“ seinen Inhalt
aus; alle anderen Rechtsklick-Menüs (`kontextMenuBauen`) klappen Untermenüs
rechts daneben aus. Jetzt baut `libItemMenu` über `kontextMenuBauen`, und
beide Untermenüs klappen aus; das häufigere Verhalten (5 von 7 Untermenüs,
Windows-Muster) gilt überall. Geprüft als echtes Seiten-JavaScript per deno.

Geprüft wird das ERZEUGTE HTML (`oberflaeche.HTML`); ob der Browser die
Variable wirklich auflöst und wie die Flyouts aussehen, misst dieser Test
nicht (kein Browser im Gate).
"""
import os
import re
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
for _pfad in (MODUL_DIR, TEST_DIR):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

_STIL = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.S | re.I)


def _teile():
    import oberflaeche
    html = oberflaeche.HTML
    stil = "\n".join(_STIL.findall(html))
    return stil, _STIL.sub("", html)


def test_gedaempfte_farbe_ist_eine_variable_mit_tag_fassung():
    stil, rest = _teile()
    assert "#8a7d74" not in rest.lower(), "die gedämpfte Farbe steht noch inline"
    assert rest.count("var(--gedaempft)") >= 25, rest.count("var(--gedaempft)")
    root = re.search(r":root\{([^}]*)\}", stil).group(1)
    assert "--gedaempft:#8a7d74" in root.replace(" ", "")
    hell = re.findall(r"html\.light\{([^}]*)\}", stil)
    assert any("--gedaempft:#7a6e64" in h.replace(" ", "") for h in hell), \
        "der Tag-Modus braucht seine eigene gedämpfte Farbe (wie .info im Tag-Modus)"


# ------------------------------------------------------------ Untermenüs

# Kleines DOM für Menüs: Elemente mit innerHTML, aus dem die Knöpfe gelesen
# werden, ein <body> als Liste und querySelectorAll('.klasse') darüber.
MENUE_DOM = r"""
const _body=[];
function _knoepfeAus(h){
  const out=[]; const re=/<button([^>]*)>([\s\S]*?)<\/button>/g; let m;
  while((m=re.exec(h))){
    const ds={}; for(const a of m[1].matchAll(/data-(\w+)="([^"]*)"/g)) ds[a[1]]=a[2];
    out.push({dataset:ds, className:(m[1].match(/class="([^"]*)"/)||['',''])[1],
      textContent:m[2].replace(/<[^>]*>/g,''), style:{},
      getBoundingClientRect(){return {left:10,right:210,top:40,bottom:60};}});
  }
  return out;
}
function _el(){
  return {className:'', style:{}, dataset:{}, _html:'', _knoepfe:[], offsetWidth:180, offsetHeight:120,
    get innerHTML(){return this._html;}, set innerHTML(h){this._html=h; this._knoepfe=_knoepfeAus(h);},
    querySelectorAll(sel){return /button/.test(sel)?this._knoepfe:[];}, querySelector(){return null;},
    getBoundingClientRect(){return {left:10,right:210,top:10,bottom:300};},
    remove(){const i=_body.indexOf(this); if(i>=0)_body.splice(i,1);}, contains(){return false;}};
}
document.createElement=()=>_el();
document.body={appendChild(e){_body.push(e);}, contains(e){return _body.includes(e);}};
document.querySelectorAll=(sel)=>{const k=sel.replace(/^\./,'');
  return _body.filter(e=>(' '+e.className+' ').includes(' '+k+' '));};
globalThis.innerWidth=1200; globalThis.innerHeight=800;
function popoverBei(){} function menuSchliesser(){} function menuGeradeZu(){return false;}
function esc(t){return String(t||'').replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');}
function zeit(s){return String(s);}
const _api=[];
async function plApi(d){_api.push(d);} function plInfo(){} async function plAnlegen(){return 'neu';}
const plState=[{id:'p1',name:'Liste A',items:[]},{id:'p2',name:'Liste B',items:['x']}];
let libAuswahl=new Set(), libPlaylistView=null;
const _x={id:'k1',titel:'Song',vorhanden:true,url:'https://www.youtube.com/watch?v=k1',hat_geschwister:true};
const _clip={id:'k1|clip1',titel:'Refrain',clip:true,vorhanden:true};
function libFind(){return _x;} function gruppeVon(){return [_x,_clip];}
function _klick(k){return k.onclick({stopPropagation(){}});}
const _ev={stopPropagation(){},currentTarget:{getBoundingClientRect(){return {left:5,right:5,top:5,bottom:5};}}};
"""


def _menue_lauf(tmp_path, *schritte):
    from test_medientasten_verhalten import _js_funktion, _js_zeile, _lauf, _pc, _pc_helfer
    q = _pc()
    teile = [MENUE_DOM, _js_zeile(q, "let NUR_FERN"), *_pc_helfer()]
    for name in ("nurPc", "menuFuerGeraet", "kmFuellen", "kontextMenuBauen",
                 "libItemMenu", "plAddListe", "gruppeListe"):
        teile.append(_js_funktion(q, name))
    return _lauf(tmp_path, *teile, *schritte)


def test_bibliotheks_menue_klappt_untermenues_rechts_aus(tmp_path):
    """EIN Untermenü-Verhalten (JB-Entscheid 7a Punkt 8): Das Bibliotheks-Menü
    tauschte bei „Zu Playlist“ und „Ausschnitte“ seinen eigenen Inhalt aus,
    der Player-Rechtsklick klappte Untermenüs rechts daneben aus (Windows-
    Muster, 5 von 7 Untermenüs). Jetzt klappen beide aus, das Hauptmenü
    bleibt stehen; die Wahl in der Liste schließt beides."""
    (vorher, nachher) = _menue_lauf(
        tmp_path,
        "libItemMenu(_ev,'k1'); const m=_body[0];",
        "const zp=m._knoepfe.find(b=>b.textContent.includes('Zu Playlist'));",
        "const au=m._knoepfe.find(b=>b.textContent.includes('Ausschnitte'));",
        "_klick(zp); let fly=_body.find(e=>e.className.includes('km-flyout'));",
        "aus({pfeile:[zp.className,au.className], haupt:_body.includes(m)&&m.innerHTML.includes('Alles auswählen'),"
        " fly:fly?fly.innerHTML:null});",
        "if(fly){const pl=fly._knoepfe.find(b=>b.dataset.pl==='p1'); await _klick(pl);}",
        "aus({api:_api, offen:_body.length});")
    assert vorher["pfeile"] == ["km-hatsub", "km-hatsub"], vorher["pfeile"]
    assert vorher["haupt"], "das Hauptmenü muss stehen bleiben"
    assert vorher["fly"] and "Zu Playlist hinzufügen" in vorher["fly"] and "Liste B" in vorher["fly"], vorher
    assert nachher == {"api": [{"art": "add", "id": "p1", "key": "k1"}], "offen": 0}, nachher


def test_ausschnitte_klappen_aus_und_das_hauptmenue_bleibt(tmp_path):
    (e,) = _menue_lauf(
        tmp_path,
        "libItemMenu(_ev,'k1'); const m=_body[0];",
        "_klick(m._knoepfe.find(b=>b.textContent.includes('Ausschnitte')));",
        "const fly=_body.filter(e=>e.className.includes('km-flyout'));",
        "aus({n:fly.length, fly:fly.length?fly[0].innerHTML:'', haupt:_body.includes(m)&&m.innerHTML.includes('Alles auswählen')});")
    assert e["n"] == 1 and e["haupt"], e
    assert "Favorit" in e["fly"] and "Refrain" in e["fly"] and "clip-schutz" in e["fly"], e["fly"]
