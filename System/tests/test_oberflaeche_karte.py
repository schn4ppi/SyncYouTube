# -*- coding: utf-8 -*-
"""Die Kopf-Karte der Oberfläche stimmt mit ihren Bannern überein
(Gesamtprüfung O2, 25.09.2026).

Der Kopf von `oberflaeche.py` nennt die Hauptbereiche des Hauptskripts in der
Reihenfolge des Dokuments, je als Zeile „==== Titel“. Im Skript markiert sie
ein Banner `/* ================= Titel ================= */`. Geprüft wird:
  * jedes Banner steht in der Karte, in derselben Reihenfolge, und die Karte
    nennt keinen Bereich, den es nicht gibt (Auto-Discovery: die Banner werden
    aus dem Text gelesen, es gibt keine Handliste);
  * jedes Hauptbanner hat dieselbe Form (17 Gleichheitszeichen je Seite), damit
    eine Suche nach „/* =================“ alle findet.
Die Gegenproben zeigen an einer Kopie, dass ein fehlender, ein vertauschter und
ein anders geschriebener Bereich auffallen.
"""
import os
import re
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import oberflaeche  # noqa: E402

_BANNER = re.compile(r"^/\* ={17} (.+?) ={17} \*/$", re.M)
# Jede Zeile, die wie ein Hauptbanner beginnt, egal wie viele = sie trägt.
_BANNERARTIG = re.compile(r"^\s*(?:/\*|//)\s*={3,}.*$", re.M)
_KARTE = re.compile(r"^ {4}==== (.+?)\s*$", re.M)


def _abweichungen(skript, doku):
    """Liste der Befunde; leer heißt: Karte und Banner passen."""
    befunde = []
    banner = _BANNER.findall(skript)
    karte = _KARTE.findall(doku)
    if banner != karte:
        befunde.append(f"Banner im Skript: {banner}\nKarte im Kopf:    {karte}")
    for zeile in _BANNERARTIG.findall(skript):
        if not _BANNER.fullmatch(zeile.strip()):
            befunde.append(f"Banner in anderer Form: {zeile.strip()!r}")
    return befunde


def test_karte_nennt_jeden_hauptbereich_in_reihenfolge():
    banner = _BANNER.findall(oberflaeche._HTML_ROH)
    assert len(banner) >= 15, f"zu wenige Hauptbereiche gefunden: {banner}"
    assert not _abweichungen(oberflaeche._HTML_ROH, oberflaeche.__doc__)


def test_gegenproben_fehlend_vertauscht_andere_form():
    skript, doku = oberflaeche._HTML_ROH, oberflaeche.__doc__
    banner = _BANNER.findall(skript)
    ohne = skript.replace(f"/* {'=' * 17} {banner[3]} {'=' * 17} */", "/* weg */", 1)
    assert _abweichungen(ohne, doku), "ein fehlendes Banner fiel nicht auf"
    a, b = f"    ==== {banner[1]}\n", f"    ==== {banner[2]}\n"
    assert a in doku and b in doku
    vertauscht = doku.replace(a, "\0").replace(b, a).replace("\0", b)
    assert _abweichungen(skript, vertauscht), "eine vertauschte Karte fiel nicht auf"
    anders = skript + "\n/* ===== Neuer Bereich ===== */\n"
    assert any("anderer Form" in f for f in _abweichungen(anders, doku))
