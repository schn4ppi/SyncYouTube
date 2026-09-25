# -*- coding: utf-8 -*-
"""Syntax-Wächter für das GANZE Skript der Oberfläche (Gesamtprüfung O0, 25.09.2026).

Die vier `<script>`-Blöcke von `oberflaeche.HTML` teilen sich im Browser einen
globalen Bereich. Ein Syntaxfehler in einem Block, oder ein `let`/`const`, das
ein anderer Block schon deklariert hat, lässt den ganzen Block nicht laufen:
Die Seite zeigt dann nur ihr statisches Gerüst (Vorfall vom 07.08.: „jetzt seh
ich den player und die bibliothek nicht mehr"). Bisher fand das nur ein
Wächter für eine einzige Ursache, den zerrissenen String
(`test_youtube._offene_js_strings`).

Geprüft wird mit der geliehenen JS-Laufzeit aus `System/bin` (deno, dieselbe
wie für yt-dlp): Jeder Block einzeln und alle zusammen in Dokument-Reihenfolge
werden per `new Function(text)` nur ÜBERSETZT, nie ausgeführt, und nicht
strikt (wie ein klassisches Skript im Browser). Fehlt deno, wird sichtbar
übersprungen statt still grün zu melden.

Nicht geprüft: Inline-Handler (`onclick="…"`), Laufzeitfehler, und ob der
Browser jede Syntax kennt, die V8 kennt.
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
# Wie der HTML-Parser: ein Skript endet am ersten </script>, egal wo.
_SKRIPT = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.S | re.I)

_PRUEFER = r"""
const VARIANTEN = JSON.parse(%s);
function fehler(text) {
  try { new Function(text); return null; }          // nur übersetzen, nie ausführen
  catch (e) { return String((e && e.message) || e); }
}
const out = {};
for (const [name, bloecke] of Object.entries(VARIANTEN)) {
  const funde = [];
  bloecke.forEach((text, i) => {
    const f = fehler(text);
    if (f) funde.push(`Block ${i + 1} von ${bloecke.length}: ${f}`);
  });
  // Getrennt durch ';', damit kein Block in den nächsten hineinläuft.
  const f = fehler(bloecke.join("\n;\n"));
  if (f) funde.push(`alle Blöcke zusammen: ${f}`);
  out[name] = funde;
}
console.log(JSON.stringify(out));
"""


def skripte(html):
    """Inhalt jedes <script>-Blocks, in Dokument-Reihenfolge."""
    return [m.group(1) for m in _SKRIPT.finditer(html)]


def _deno_oder_skip():
    if not os.path.exists(DENO):
        pytest.skip("deno fehlt in System/bin — Syntax der Oberfläche NICHT geprüft")


def _pruefen(tmp_path, varianten):
    """{Name: [Blocktext, …]} → {Name: [Fund, …]} in EINEM deno-Lauf."""
    datei = tmp_path / "syntax_pruefer.mjs"
    datei.write_text(_PRUEFER % json.dumps(json.dumps(varianten)), encoding="utf-8")
    lauf = subprocess.run([DENO, "run", "--quiet", str(datei)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120)
    assert lauf.returncode == 0, lauf.stderr[-2000:]
    return json.loads(lauf.stdout.strip().splitlines()[-1])


def _bloecke():
    import oberflaeche
    b = skripte(oberflaeche.HTML)
    assert len(b) >= 4, f"erwartet mindestens die vier Skript-Blöcke, gefunden {len(b)}"
    return b


def test_ganzes_oberflaechen_skript_ist_gueltig(tmp_path):
    _deno_oder_skip()
    funde = _pruefen(tmp_path, {"echt": _bloecke()})["echt"]
    assert not funde, "Syntaxfehler im Skript der Oberfläche:\n" + "\n".join(funde)


def test_gegenproben_doppeltes_let_und_fehlende_klammer(tmp_path):
    """Beide Fehlerarten, je in einer KOPIE des echten Texts (die Datei bleibt
    unberührt): ein `let`, das ein ANDERER Block schon deklariert (jeder Block
    für sich bleibt gültig, erst zusammen scheitern sie, wie im Browser), und
    eine fehlende schließende Klammer im großen Block."""
    _deno_oder_skip()
    echt = _bloecke()
    groesster = max(range(len(echt)), key=lambda i: len(echt[i]))
    name = re.search(r"^let\s+(\w+)", echt[groesster], re.M).group(1)
    anderer = 0 if groesster else 1
    doppelt = list(echt)
    doppelt[anderer] = f"let {name}=0;\n" + doppelt[anderer]
    klammer = list(echt)
    ende = klammer[groesster].rindex("}")
    klammer[groesster] = klammer[groesster][:ende] + klammer[groesster][ende + 1:]
    funde = _pruefen(tmp_path, {"doppelt": doppelt, "klammer": klammer})
    assert len(funde["doppelt"]) == 1 and funde["doppelt"][0].startswith("alle Blöcke zusammen") \
        and name in funde["doppelt"][0], funde["doppelt"]
    assert any(f.startswith(f"Block {groesster + 1} ") for f in funde["klammer"]), funde["klammer"]
