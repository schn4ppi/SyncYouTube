# -*- coding: utf-8 -*-
"""Findet Inline-Handler, in die ein Wert eingesetzt wird (Gesamtprüfung S3,
Nachtrag 25.09.2026). Kein Test, sondern das Werkzeug der Wächter in
test_schluessel_im_handler.py.

Ein Handler-Attribut (`onclick="…"`, `onerror="…"`, …) in einem JS-String
darf nur statischen Code tragen. Werte kommen über `data-…`-Attribute und
`this.dataset` hinein: der Browser dekodiert den Attributwert vor der
Ausführung, ein ' oder " aus einem Wert wäre sonst Skript. Gefunden wird
  * ein `${…}` innerhalb des Handler-Werts (Template-Loch) und
  * ein Handler-Wert, der am Ende des String-Literals noch offen ist
    (Verkettung wie `'onclick="f(\\''+x+'\\')"'`).

Dazu zerlegt `literale()` JavaScript in seine String- und Template-Literale
(Kommentare, reguläre Ausdrücke und verschachtelte Löcher werden richtig
übersprungen). Auto-Discovery der Seiten: jedes Modul in System/, dessen
Quelltext `<script` enthält; geprüft werden alle Skript-Blöcke aller
Zeichenketten des Moduls.
"""
import glob
import importlib
import os
import re

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_REGEX_VOR = set("(,=:[!&|?{};+-*%<>~^")
_REGEX_WORTE = {"return", "typeof", "case", "do", "else", "in", "of", "void", "delete", "throw", "new"}


class Literal:
    def __init__(self, start):
        self.start = start
        self.teile = []           # ('text', dekodiert) | ('loch', ausdruck)

    def text(self, t):
        if self.teile and self.teile[-1][0] == "text":
            self.teile[-1] = ("text", self.teile[-1][1] + t)
        else:
            self.teile.append(("text", t))


def _escape(c):
    return {"n": "\n", "t": "\t", "r": "\r"}.get(c, c)


def literale(code, i=0, ende=None, aus=None):
    """Alle String-/Template-Literale in code[i:ende] (auch in Löchern).
    Liefert (Liste, Index nach dem Ende). Endet bei `ende` == '}' an der
    passenden schließenden Klammer (für Template-Löcher)."""
    aus = [] if aus is None else aus
    tiefe = 0
    letztes = ""                  # letztes bedeutsames Zeichen/Wort (für Regex-Erkennung)
    n = len(code)
    while i < n:
        c = code[i]
        if c in " \t\r\n":
            i += 1
            continue
        if code.startswith("//", i):
            j = code.find("\n", i)
            i = n if j < 0 else j
            continue
        if code.startswith("/*", i):
            j = code.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "'\"":
            lit = Literal(i)
            j = i + 1
            while j < n and code[j] != c:
                if code[j] == "\\":
                    lit.text(_escape(code[j + 1]))
                    j += 2
                    continue
                if code[j] == "\n":           # kaputter String: hier abbrechen
                    break
                lit.text(code[j])
                j += 1
            aus.append(lit)
            i = j + 1
            letztes = "a"
            continue
        if c == "`":
            lit = Literal(i)
            aus.append(lit)
            j = i + 1
            while j < n and code[j] != "`":
                if code[j] == "\\":
                    lit.text(_escape(code[j + 1]))
                    j += 2
                    continue
                if code.startswith("${", j):
                    _, k = literale(code, j + 2, "}", aus)
                    lit.teile.append(("loch", code[j + 2:k]))
                    j = k + 1
                    continue
                lit.text(code[j])
                j += 1
            i = j + 1
            letztes = "a"
            continue
        if c == "/" and (letztes == "" or letztes in _REGEX_VOR or letztes in _REGEX_WORTE):
            j, klasse = i + 1, False           # regulärer Ausdruck
            while j < n:
                if code[j] == "\\":
                    j += 2
                    continue
                if code[j] == "[":
                    klasse = True
                elif code[j] == "]":
                    klasse = False
                elif code[j] == "/" and not klasse:
                    break
                elif code[j] == "\n":
                    break
                j += 1
            i = j + 1
            while i < n and code[i].isalpha():
                i += 1
            letztes = "a"
            continue
        if c == "{":
            tiefe += 1
        elif c == "}":
            if ende == "}" and tiefe == 0:
                return aus, i
            tiefe -= 1
        m = re.match(r"[A-Za-z_$][\w$]*", code[i:i + 40])
        if m:
            letztes = m.group(0)
            i += len(letztes)
            continue
        letztes = c
        i += 1
    return aus, i


_HANDLER = re.compile(r"(?<![\w-])(on[a-z]+)\s*=\s*([\"'])")


def befunde(code):
    """[(Offset, Handler, Art, Ausschnitt)] für eingesetzte Werte in Handlern."""
    funde = []
    for lit in literale(code)[0]:
        teile = lit.teile
        for nr, (art, wert) in enumerate(teile):
            if art != "text":
                continue
            for m in _HANDLER.finditer(wert):
                quote, rest = m.group(2), wert[m.end():]
                if quote in rest:
                    continue                           # im selben Stück geschlossen
                if nr + 1 < len(teile):
                    funde.append((lit.start, m.group(1), "${…}", wert[m.start():][:80] + "${" + teile[nr + 1][1][:40] + "}"))
                else:
                    funde.append((lit.start, m.group(1), "Verkettung", wert[m.start():][:120]))
    return funde


def skripte(html):
    return [m.group(1) for m in re.finditer(r"<script\b[^>]*>(.*?)</script\s*>", html, re.S | re.I)]


def seiten():
    """{Modulname: [Skript-Text, …]} für jedes Modul mit `<script` im Quelltext."""
    erg = {}
    for pfad in sorted(glob.glob(os.path.join(MODUL_DIR, "*.py"))):
        if "<script" not in open(pfad, encoding="utf-8").read():
            continue
        name = os.path.splitext(os.path.basename(pfad))[0]
        modul = importlib.import_module(name)
        texte = [w for w in vars(modul).values() if isinstance(w, str) and "<script" in w]
        erg[name] = [s for t in texte for s in skripte(t)]
    return erg


def alle_befunde():
    erg = []
    for name, bloecke in seiten().items():
        for block in bloecke:
            for off, handler, art, stueck in befunde(block):
                zeile = block.count("\n", 0, off) + 1
                erg.append(f"{name}: {handler} ({art}) Blockzeile {zeile}: {stueck}")
    return erg
