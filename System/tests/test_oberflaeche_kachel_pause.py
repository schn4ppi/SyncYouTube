# -*- coding: utf-8 -*-
"""Bibliothekskacheln spiegeln Play/Pause auch ohne oder mit defektem Bild.

Das echte Seiten-JavaScript läuft gegen eine kleine DOM-Attrappe wie in den
übrigen Oberflächentests. CSS-Pseudoelemente prüft ein separater Vertragstest,
weil die geliehene JavaScript-Laufzeit keine CSS-Darstellung besitzt.
"""
import os
import re
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

from test_medientasten_verhalten import _js_funktion, _lauf, _pc  # noqa: E402


def _kachel_teile():
    return [
        "let playShuffle=false, playRepeat='aus', radioAktiv=false, playArt='alle';",
        "const PLAYART=[]; let geraet='browser', vlcSpielt=false, key='bild';",
        "function vlcAktiv(){return geraet==='vlc';} function aktKey(){return key;}",
        "function ico(n){return n;}",
        "const karten=['bild','ohne','defekt'].map(id=>{",
        "  const klassen=new Set(['thumbwrap', ...(id==='bild'?[]:['platzhalter'])]);",
        "  return {dataset:{key:id}, title:'Abspielen', klassen, classList:{",
        "    toggle(n,an){if(an)klassen.add(n); else klassen.delete(n);}}};});",
        "document.querySelectorAll=s=>s==='.thumbwrap[data-key]'?karten:[];",
        "function stand(){return karten.map(b=>({id:b.dataset.key,",
        "  spielt:b.klassen.has('spielt'), title:b.title}));}",
        "_els['pl-el']=fakeMedia({id:'pl-el'});",
        _js_funktion(_pc(), "transportRender"),
    ]


@pytest.mark.parametrize("geraet", ["browser", "vlc"])
@pytest.mark.parametrize("titel", ["bild", "ohne", "defekt"])
def test_jede_kachel_spiegelt_abspielen_pause_und_titelwechsel(tmp_path, geraet, titel):
    spielt, pause, wechsel = _lauf(
        tmp_path, *_kachel_teile(),
        f"geraet='{geraet}'; key='{titel}';",
        # Der andere Wiedergabeweg meldet absichtlich den gegenteiligen Zustand.
        "_els['pl-el'].paused=geraet!=='browser'; vlcSpielt=geraet==='vlc';",
        "transportRender(); aus({karten:stand()});",
        "_els['pl-el'].paused=geraet==='browser'; vlcSpielt=geraet!=='vlc';",
        "transportRender(); aus({karten:stand()});",
        "key='anderer-titel'; _els['pl-el'].paused=false; vlcSpielt=true;",
        "transportRender(); aus({karten:stand()});",
    )
    assert spielt["karten"] == [
        {"id": id_, "spielt": id_ == titel, "title": "Pause" if id_ == titel else "Abspielen"}
        for id_ in ("bild", "ohne", "defekt")
    ]
    erwartet = [{"id": id_, "spielt": False, "title": "Abspielen"}
                for id_ in ("bild", "ohne", "defekt")]
    assert pause["karten"] == erwartet
    assert wechsel["karten"] == erwartet


def test_neu_gezeichnete_kacheln_behalten_den_wiedergabezustand(tmp_path):
    (e,) = _lauf(
        tmp_path, *_kachel_teile(),
        "let libSelectMode=false, libModus='kachel';",
        "function fuelleSortSelect(){} function bulkMalen(){} function libBandStart(){}",
        "function libGefiltert(){return [{}];}",
        "function kacheln(){karten.forEach(b=>b.klassen.delete('spielt')); return '<Kacheln>';}",
        "_els['libselbtn']={classList:{toggle(){}}};",
        "_els['libinhalt']={innerHTML:'', closest(){return null;}};",
        _js_funktion(_pc(), "libMalen"),
        "key='ohne'; _els['pl-el'].paused=false; libMalen(); aus({karten:stand()});",
    )
    assert [k["id"] for k in e["karten"] if k["spielt"]] == ["ohne"]


def test_pause_symbol_gilt_fuer_bild_und_platzhalter():
    """Beide tatsächlich verwendeten Pseudoelemente müssen Pause anzeigen."""
    css = "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", _pc(), re.S))
    regeln = re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    for selector in (".thumbwrap.spielt::before", ".thumbwrap.platzhalter.spielt::after"):
        assert any(selector in kopf.split(",") and re.search(r"content\s*:\s*['\"]⏸['\"]", rumpf)
                   for kopf, rumpf in ((k.strip(), r) for k, r in regeln)), selector
    assert any(".thumbwrap.spielt::before" in kopf.split(",") and "opacity:.92" in rumpf
               for kopf, rumpf in ((k.strip(), r) for k, r in regeln))
