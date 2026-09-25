# -*- coding: utf-8 -*-
"""Toter Code bleibt draußen (Gesamtprüfung Gruppe 7, Abschnitt 5, 25.09.2026).

Entfernt wurden: die Route `POST /api/importieren` samt `ordnerImportieren()`,
der Zweig `art:'bulk'` in `_biblio` samt `_enrich_keys` und den fünf
`bulk…`-Funktionen der Oberfläche und die übrigen toten Funktionen der
Oberfläche.

Die zwei Server-Befunde prüft je ein Verhaltenstest durch den echten Handler.
Für die Oberfläche gibt es einen Wächter über das ERZEUGTE Skript
(`oberflaeche.HTML`), mit Auto-Discovery statt Handliste: jede
Top-Level-Funktion wird irgendwo genannt (im Seitentext ohne Kommentare oder
in einem anderen Auslieferungs-Teil: Hülle, Handy-Seite, Fernbedienung,
Server, Browser-Erweiterung).
Grenzen: Eine Funktion, die nur noch eine tote Funktion aufruft, zählt als
genannt, bis der Aufrufer weg ist (dann schlägt der Wächter an). Python-Texte
(Docstrings, HTML in Strings) zählen als Nennung, Python-Kommentare nicht.
"""
import glob
import io
import os
import re
import sys
import tokenize

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
for _pfad in (MODUL_DIR, TEST_DIR):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import _anfrage, rechner  # noqa: E402,F401  (rechner: autouse)

PC = {"Host": "127.0.0.1:8776"}


# ------------------------------------------------------------ Server

def test_importieren_route_ist_weg(monkeypatch):
    """Seit Build 122 (60a55df, 23.07.2026) rief niemand mehr POST /api/importieren.
    Der Ordner-Import selbst bleibt (Ticker und Selbstheilung rufen ihn)."""
    aufrufe = []
    monkeypatch.setattr(app, "ordner_importieren", lambda: aufrufe.append(1) or 0)
    st, _, koerper = _anfrage("/api/importieren", methode="POST", kopf=PC, rumpf={})
    assert st == 404, koerper[:120]
    assert aufrufe == []
    assert ("POST", "/api/importieren") not in app.NUR_PC
    assert callable(app.ordner_importieren), "der Import im Ticker bleibt"


def test_bulk_zweig_in_biblio_ist_weg(monkeypatch, tmp_path):
    """Der Zweig art:'bulk' hatte keine Oberfläche mehr, trug aber eine
    Lösch-Operation. Nach dem Entfernen ändert ein solcher Rumpf nichts."""
    datei = tmp_path / "Titel [abcdefghijk].mp3"
    datei.write_bytes(b"x" * 2048)
    key = "abcdefghijk|audio"
    app._geladen[key] = {"name": datei.name, "pfad": str(datei), "titel": "Titel", "uploader": "K"}
    geloescht = []
    monkeypatch.setattr(app, "_datei_loeschen", lambda k: geloescht.append(k))
    for op, felder in (("loeschen", {}), ("vergessen", {}), ("archiv", {}),
                       ("tag", {"uploader": "Neu", "titel_suchen": "Titel", "titel_ersetzen": "X"})):
        st, _, koerper = _anfrage("/api/biblio", methode="POST", kopf=PC,
                                  rumpf={"art": "bulk", "op": op, "keys": [key], "felder": felder})
        assert st == 200, koerper[:120]
    assert geloescht == [], "kein Löschen mehr über den toten Zweig"
    assert app._geladen.get(key) == {"name": datei.name, "pfad": str(datei), "titel": "Titel", "uploader": "K"}
    assert datei.exists()
    assert not hasattr(app, "_enrich_keys"), "nur der tote Zweig rief _enrich_keys"


# ------------------------------------------------------------ Oberfläche: Funktionen

_SKRIPT = re.compile(r"<script\b[^>]*>(.*?)</script\s*>", re.S | re.I)
_KOPF = re.compile(r"^(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(", re.M)


def _ohne_kommentare(text):
    """JS-/CSS-Blockkommentare, HTML-Kommentare und `//`-Zeilenkommentare
    (nach Leerraum oder Satzzeichen, also nicht in `https://`) entfernen."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return re.sub(r"(^|[\s;{}(),])//[^\n]*", r"\1", text, flags=re.M)


def _py_ohne_kommentare(pfad):
    with open(pfad, "rb") as f:
        return " ".join(t.string for t in tokenize.tokenize(io.BytesIO(f.read()).readline)
                        if t.type != tokenize.COMMENT)


def unbenannte_funktionen(seite, andere=""):
    """Namen der Top-Level-Funktionen aus den <script>-Blöcken von `seite`,
    die außer ihrem eigenen Kopf nirgends genannt werden (`.name` als
    Eigenschaft zählt nicht, außer an `window`/`globalThis`; `name(`,
    `onclick="name()"`, `f=name` zählen)."""
    namen = [m.group(1) for block in _SKRIPT.findall(seite) for m in _KOPF.finditer(block)]
    text = _ohne_kommentare(seite)
    tot = []
    for name in namen:
        nennung = re.compile(r"(?:(?<![\w$.])|\b(?:window|globalThis)\.)" + re.escape(name) + r"(?![\w$])")
        kopf = re.compile(r"^(?:async\s+)?function\s*\*?\s*" + re.escape(name) + r"\s*\(", re.M)
        if len(nennung.findall(text)) - len(kopf.findall(text)) + len(nennung.findall(andere)) <= 0:
            tot.append(name)
    return tot


def _andere_auslieferungs_teile():
    """Alles, was mit ausgeliefert wird und die Seite aufrufen könnte: die
    übrigen Module in System/ (Hülle ruft per evaluate_js), layout_kern.js und
    die Browser-Erweiterung. Nicht: Tests, Werkzeuge, Doku."""
    teile = []
    for pfad in sorted(glob.glob(os.path.join(MODUL_DIR, "*.py"))):
        if os.path.basename(pfad) != "oberflaeche.py":
            teile.append(_py_ohne_kommentare(pfad))
    for pfad in [os.path.join(MODUL_DIR, "layout_kern.js")] + sorted(
            glob.glob(os.path.join(MODUL_DIR, "browser-addon", "shared", "*.*"))):
        if pfad.endswith((".js", ".html")) and os.path.isfile(pfad):
            with open(pfad, encoding="utf-8") as f:
                teile.append(_ohne_kommentare(f.read()))
    return "\n".join(teile)


def test_gegenprobe_unbenannte_funktion_wird_gefunden():
    seite = ("<p onclick=\"d()\"></p><script>\nfunction a(){ b(); x.c(); }\nfunction b(){}\n"
             "function c(){} // c() nur im Kommentar\nasync function d(){}\nfunction e(){}\n</script>")
    assert unbenannte_funktionen(seite) == ["a", "c", "e"]
    assert unbenannte_funktionen(seite, andere="window.e()") == ["a", "c"]


def test_jede_funktion_der_oberflaeche_wird_genannt():
    import oberflaeche
    tot = unbenannte_funktionen(oberflaeche.HTML, _andere_auslieferungs_teile())
    assert not tot, (f"Funktionen ohne Aufrufer im Skript der Oberfläche: {tot} — entfernen "
                     "(die git-Historie ist der Rückweg) oder den Aufruf wiederherstellen")
