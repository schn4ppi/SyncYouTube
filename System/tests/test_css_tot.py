# -*- coding: utf-8 -*-
"""Keine CSS-Regel für eine Klasse, die es nirgends gibt (Gesamtprüfung,
Gruppe 9, 26.09.2026).

Die Oberfläche schleppte Regeln für Elemente mit, die längst ersetzt waren
(die alte Warteschlange mit .eintrag/.kopf/.pill/.qtag/.balken, ein Griff
.panel-grip, eine Stufe .bo1, die es in der Leiste nie gab). Jede davon kostet
beim Lesen Zeit und täuscht Zusammenhänge vor.

Auto-Discovery: jedes Modul in System/, dessen Quelltext <style enthält, und
darin jede Zeichenkette mit <style>…</style> (heute oberflaeche, handy,
fernbedienung, profil_geraete). Jede Klasse aus einem Selektor im Stil muss
benutzt werden:
  * im Markup als Wort in einem class-Attribut,
  * in einem Skript als Wort in einem class-Attribut eines String- oder
    Template-Literals (auch in einem Loch mitten im Attribut und über eine
    Verkettung `'<div class="a'+(x?' b':'')+'">'` hinweg),
  * als Argument von classList.add/remove/toggle/contains/replace, als
    Zuweisung an className oder in einem Selektor von querySelector,
    querySelectorAll, closest oder matches.
Ein Wort, das nur irgendwo als Text steht ('balken' als Name eines
Visualizer-Modus), zählt NICHT: genau so versteckten sich tote Regeln.

Was aus Daten oder Tabellen kommt und darum nie als Klassen-Wort im Quelltext
steht, steht unten in AUSNAHMEN, je mit Grund und einem Beleg, der die
dynamische Stelle im Skript nachweist. Verschwindet die Stelle oder die
Regel, wird die Ausnahme selbst rot.
"""
import glob
import importlib
import os
import re
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (MODUL_DIR, TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import handler_scanner as hs  # noqa: E402

# (Klassen oder Präfix, Grund, Beleg im Skript als regulärer Ausdruck)
AUSNAHMEN = [
    ({"r-"}, "Präfix: Anfass-Ränder der Panels, je Richtung eine Klasse",
     r'class="rgriff r-\$\{r\}"'),
    ({"wartend", "pausiert", "uebersprungen"},
     "Status eines Downloads kommt vom Server und wird zur Klasse der Zeile",
     r'class="qline \$\{it\.status\}"'),
    ({"ja", "nein", "teils"}, "Farbe der Vergleichstabelle, aus dem Zellentext berechnet",
     r'<span class="\$\{c\}">'),
    ({"theme-hacker", "theme-neon", "theme-ozean"},
     "Looks: die Klasse steht in der Tabelle SKINS und im Frühstart-Skript",
     r"h\.classList\.add\(def\[2\]\)"),
]

_STIL = re.compile(r"<style\b[^>]*>(.*?)</style\s*>", re.S | re.I)
_KLASSE = re.compile(r"\.(-?[A-Za-z_][\w-]*)")
_WORT = re.compile(r"(?<![\w-])-?[A-Za-z_][\w-]*(?![\w-])")
_CLASS_ATTR = re.compile(r"(?<![\w-])class\s*=\s*([\"'])")
_API_VOR = re.compile(r"(?:classList\.(?:add|remove|toggle|contains|replace)\([^();]*"
                      r"|className\s*(?:\+?=|[!=]==?)[^;]*)$")
_SEL_VOR = re.compile(r"(?:querySelector(?:All)?|closest|matches)\([^();]*$")


def seiten():
    """{Modul.Variable: HTML} für jede Zeichenkette mit <style> in System/."""
    erg = {}
    for pfad in sorted(glob.glob(os.path.join(MODUL_DIR, "*.py"))):
        with open(pfad, encoding="utf-8") as f:
            if "<style" not in f.read():
                continue
        name = os.path.splitext(os.path.basename(pfad))[0]
        modul = importlib.import_module(name)
        for var, wert in vars(modul).items():
            if isinstance(wert, str) and not var.startswith("__") and _STIL.search(wert):
                erg[f"{name}.{var}"] = wert
    return erg


def stil_klassen(html):
    """Alle Klassen aus Selektoren (Kommentare, Zeichenketten, url() raus)."""
    klassen = set()
    for css in _STIL.findall(html):
        css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
        css = re.sub(r"url\([^)]*\)|\"[^\"]*\"|'[^']*'", " ", css)
        for m in re.finditer(r"([^{}]*)\{", css):
            klassen |= set(_KLASSE.findall(m.group(1)))
    return klassen


def _worte_bis(text, quote):
    """Worte bis zum schließenden Anführungszeichen; zweiter Wert: geschlossen?"""
    j = text.find(quote)
    return set(_WORT.findall(text if j < 0 else text[:j])), j >= 0, j


def benutzte_klassen(html):
    ohne_stil = _STIL.sub(" ", html)
    markup = re.sub(r"<script\b[^>]*>.*?</script\s*>|<!--.*?-->", " ", ohne_stil, flags=re.S | re.I)
    benutzt = set()
    for m in re.finditer(r"(?<![\w-])class\s*=\s*([\"'])(.*?)\1", markup, re.S):
        benutzt |= set(_WORT.findall(m.group(2)))
    for code in hs.skripte(ohne_stil):
        offen = None                          # class-Attribut über eine Verkettung hinweg offen
        for lit in hs.literale(code)[0]:
            vor = code[max(0, lit.start - 200):lit.start]
            api, sel = bool(_API_VOR.search(vor)), bool(_SEL_VOR.search(vor))
            for art, text in lit.teile:
                if art == "loch":
                    if offen:                 # Loch mitten im class-Attribut: jedes Literal darin
                        for innen in hs.literale(text)[0]:
                            benutzt |= {w for a, t in innen.teile if a == "text" for w in _WORT.findall(t)}
                    continue
                if api:
                    benutzt |= set(_WORT.findall(text))
                if sel:
                    benutzt |= set(_KLASSE.findall(text))
                i = 0
                if offen:
                    worte, zu, j = _worte_bis(text, offen)
                    benutzt |= worte
                    if not zu:
                        continue
                    offen, i = None, j + 1
                while True:
                    m = _CLASS_ATTR.search(text, i)
                    if not m:
                        break
                    worte, zu, j = _worte_bis(text[m.end():], m.group(1))
                    benutzt |= worte
                    if not zu:
                        offen = m.group(1)
                        break
                    i = m.end() + j + 1
    return benutzt


def ohne_ausnahmen(klassen):
    return {k for k in klassen
            if not any(k in namen or any(n.endswith("-") and k.startswith(n) for n in namen)
                       for namen, _, _ in AUSNAHMEN)}


def tote_klassen(html):
    return sorted(ohne_ausnahmen(stil_klassen(html) - benutzte_klassen(html)))


def test_jede_stil_klasse_wird_benutzt():
    s = seiten()
    assert {"oberflaeche.HTML", "handy.HTML", "fernbedienung.HTML"} <= set(s), sorted(s)
    tot = {name: tote_klassen(html) for name, html in s.items()}
    tot = {k: v for k, v in tot.items() if v}
    assert not tot, ("CSS-Regeln für Klassen, die weder Markup noch Skript setzt "
                     "(entfernen oder mit Grund in AUSNAHMEN):\n"
                     + "\n".join(f"{k}: {', '.join(v)}" for k, v in tot.items()))


@pytest.mark.parametrize("namen, grund, beleg", AUSNAHMEN, ids=[g[:30] for _, g, _ in AUSNAHMEN])
def test_jede_ausnahme_hat_noch_ihren_grund(namen, grund, beleg):
    """Eine Ausnahme gilt nur, solange es die Regel UND die dynamische Stelle
    gibt; sonst versteckte sie irgendwann eine tote Regel."""
    import oberflaeche
    html = oberflaeche.HTML
    klassen = stil_klassen(html)
    for n in namen:
        treffer = [k for k in klassen if k.startswith(n)] if n.endswith("-") else [n] * (n in klassen)
        assert treffer, f"Ausnahme {n!r}: keine Regel im Stil mehr — Ausnahme streichen"
        if not n.endswith("-"):
            assert n not in benutzte_klassen(html), f"Ausnahme {n!r}: wird schon erkannt — Ausnahme streichen"
    assert re.search(beleg, "\n".join(hs.skripte(html))), f"Beleg für „{grund}“ fehlt: {beleg}"


# ------------------------------------------------------------ Gegenproben

SEITE = """<style>.a{x:1} .b .c{x:1} html.d .e:hover{x:1} @media (max-width:5px){.f{x:.5}}
.nurstil{x:1} .wort{x:1} .kommentar{x:1} .teil{x:1} /* .imkommentar{} */</style>
<div class="a b"></div>
<script>
const x=`<span class="c ${y?'e':''}">`;          // Loch im class-Attribut
el.classList.add('d'); q.className='f';
const w='wort';                                  // nur als Wort, nicht als Klasse
// class="kommentar"
const t='<i class="teilweise">';
</script>"""


def test_gegenprobe_tote_und_benutzte_klassen():
    assert stil_klassen(SEITE) == {"a", "b", "c", "d", "e", "f", "nurstil", "wort", "kommentar", "teil"}
    assert tote_klassen(SEITE) == ["kommentar", "nurstil", "teil", "wort"]


def test_gegenprobe_verkettung_und_selektor():
    seite = ("<style>.lrc{x:1}.sel{x:1}.tgl{x:1}.weg{x:1}</style><script>"
             "const h='<div class=\"kar'+(a?' lrc':'')+'\">';"
             "document.querySelectorAll('#x .sel').forEach(e=>e.classList.toggle('tgl',!!a));"
             "</script>")
    assert tote_klassen(seite) == ["weg"]


def test_gegenprobe_am_echten_bestand():
    """Eine neue Regel für eine Klasse, die niemand setzt, macht den Wächter
    rot — auch mitten im echten Stil der Oberfläche."""
    import oberflaeche
    html = oberflaeche.HTML.replace("<style>", "<style>.gibt-es-nicht-probe{color:red}", 1)
    assert "gibt-es-nicht-probe" in tote_klassen(html)
    ohne = [a for a in AUSNAHMEN if "r-" not in a[0]]
    zurueck = AUSNAHMEN[:]
    try:
        AUSNAHMEN[:] = ohne
        assert "r-nw" in tote_klassen(oberflaeche.HTML), "ohne Ausnahme fiele der Präfix auf"
    finally:
        AUSNAHMEN[:] = zurueck
