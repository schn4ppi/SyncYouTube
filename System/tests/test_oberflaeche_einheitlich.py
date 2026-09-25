# -*- coding: utf-8 -*-
"""Zwei kleine Sichtänderungen (JB-Entscheid 7a Punkt 8, Gesamtprüfung Gruppe 7).

Gedämpfte Farbe: Die feste gedämpfte Textfarbe #8a7d74 stand 25-mal inline im
Markup und in erzeugtem HTML. Inline-Stile erreicht keine Regel des Tag-Modus,
deshalb blieb sie dort hell-auf-hell (die Regeln des Tag-Modus nehmen für
gedämpften Text #7a6e64). Jetzt steht sie als Variable `--gedaempft` einmal im
Stil, und der Tag-Modus setzt sie um.

Geprüft wird das ERZEUGTE HTML (`oberflaeche.HTML`); ob der Browser die
Variable wirklich auflöst, misst dieser Test nicht (kein Browser im Gate).
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
