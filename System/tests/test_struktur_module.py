# -*- coding: utf-8 -*-
"""Ausgelagerte Module der App (Gesamtprüfung Abschnitt 4, ab Y2, 25.09.2026).

Teile von youtube_app.py wandern in eigene Module (links, …). Vier Regeln
halten das verhaltensgleich und prüfbar:

1. Einbahn wie bei filme und geo: ein ausgelagertes Modul importiert
   youtube_app nie. Was es braucht, kommt per Parameter oder `einrichten()`.
2. `app.X` bleibt erreichbar: jeder Name, den ein ausgelagertes Modul
   definiert, steht in youtube_app als Verweis (dasselbe Objekt).
3. Die App ruft `modul.X`, nie den Verweis `X`. Nur so trifft EIN Ersatz im
   Test (an `modul.X`) jeden Aufrufer, in der App wie im Modul selbst.
4. Kein Test ersetzt einen Verweis (`app.X`): der Ersatz träfe keinen
   Aufrufer, und der Test liefe still ins Echte. Hier am Quelltext aller
   Tests geprüft (setattr, Zuweisung, auch mit eigenem Rückweg im finally);
   die conftest prüft es zusätzlich am Ende jedes Tests zur Laufzeit.

Welche Module ausgelagert sind, steht im Quelltext der App (`from M import …`
mit M als Datei in System\\, `conftest.VERWEISE`), nicht in einer Handliste.
"""
import ast
import glob
import importlib
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DIESE_DATEI = os.path.abspath(__file__)
for _pfad in (MODUL_DIR, TEST_DIR):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

import conftest  # noqa: E402
import youtube_app as app  # noqa: E402

AUSGELAGERT = sorted(set(conftest.VERWEISE.values()))


def _baum(modul):
    with open(os.path.join(MODUL_DIR, modul + ".py"), encoding="utf-8") as f:
        return ast.parse(f.read())


def _definiert(modul):
    """Namen, die das Modul auf oberster Ebene selbst anlegt (def, class, Zuweisung)."""
    namen = set()
    for k in _baum(modul).body:
        if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            namen.add(k.name)
        elif isinstance(k, ast.Assign):
            namen.update(z.id for z in k.targets if isinstance(z, ast.Name))
        elif isinstance(k, ast.AnnAssign) and isinstance(k.target, ast.Name):
            namen.add(k.target.id)
    return namen


def test_ableitung_findet_die_ausgelagerten_module():
    """Gegenprobe für die Ableitung: fände sie nichts mehr, wären die
    folgenden Tests leer und grün."""
    assert {"links"} <= set(AUSGELAGERT), AUSGELAGERT
    assert len(conftest.VERWEISE) >= 10, conftest.VERWEISE


def test_einbahn_kein_ausgelagertes_modul_importiert_die_app():
    for modul in AUSGELAGERT:
        for k in ast.walk(_baum(modul)):
            if isinstance(k, ast.Import):
                namen = {a.name.split(".")[0] for a in k.names}
            elif isinstance(k, ast.ImportFrom):
                namen = {(k.module or "").split(".")[0]}
            else:
                continue
            assert "youtube_app" not in namen, f"{modul}.py importiert youtube_app (Zeile {k.lineno})"


def test_jeder_name_bleibt_als_app_x_erreichbar():
    """Jeder Name eines ausgelagerten Moduls ist `app.X`, dasselbe Objekt, und
    der Verweis zeigt auf das Modul, das ihn wirklich anlegt."""
    for modul in AUSGELAGERT:
        m = importlib.import_module(modul)
        definiert = _definiert(modul)
        verwiesen = {n for n, heim in conftest.VERWEISE.items() if heim == modul}
        assert definiert == verwiesen, (
            f"{modul}: ohne Verweis in youtube_app {sorted(definiert - verwiesen)}, "
            f"Verweis ohne eigene Definition {sorted(verwiesen - definiert)}")
        for n in definiert:
            assert getattr(app, n) is getattr(m, n), f"app.{n} ist nicht {modul}.{n}"


def nackte_verweise(quelltext, verweise):
    """(Zeile, Name) jeder Stelle, an der ein Quelltext einen Verweis ohne sein
    Heimatmodul benutzt (die `from M import …`-Zeile selbst zählt nicht)."""
    funde = []
    for k in ast.walk(ast.parse(quelltext)):
        if isinstance(k, ast.Name) and k.id in verweise:
            funde.append((k.lineno, k.id))
    return sorted(funde)


def test_die_app_ruft_ueber_das_heimatmodul():
    with open(app.__file__, encoding="utf-8") as f:
        funde = nackte_verweise(f.read(), conftest.VERWEISE)
    assert not funde, ("youtube_app ruft einen Verweis direkt statt über das Heimatmodul "
                       f"(ein Ersatz im Test träfe diese Stelle nicht): {funde}")


def test_gegenprobe_nackter_verweis_wird_gefunden():
    quelle = ("from links import _video_id  # noqa: F401\n"
              "import links\n"
              "def f(url):\n"
              "    return _video_id(url) or links._video_id(url)\n")
    assert nackte_verweise(quelle, {"_video_id": "links"}) == [(4, "_video_id")]


def ersatz_an_der_app(quelltext):
    """(Zeile, Name) jedes Ersatzes an youtube_app in einem Test-Quelltext:
    `setattr(app, "X", …)` (auch monkeypatch.setattr/delattr), die Textform
    `setattr("youtube_app.X", …)` und die Zuweisung `app.X = …`. `app` ist
    jeder Name, unter dem die Datei youtube_app importiert."""
    baum = ast.parse(quelltext)
    aliase = set()
    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            aliase.update(a.asname or a.name for a in k.names if a.name == "youtube_app")
    funde = []
    for k in ast.walk(baum):
        if isinstance(k, ast.Call) and isinstance(k.func, (ast.Attribute, ast.Name)):
            name = k.func.attr if isinstance(k.func, ast.Attribute) else k.func.id
            if name not in ("setattr", "delattr") or not k.args:
                continue
            erstes = k.args[0]
            if (isinstance(erstes, ast.Constant) and isinstance(erstes.value, str)
                    and erstes.value.startswith("youtube_app.")):
                funde.append((k.lineno, erstes.value.split(".", 1)[1]))
            elif (isinstance(erstes, ast.Name) and erstes.id in aliase and len(k.args) > 1
                  and isinstance(k.args[1], ast.Constant) and isinstance(k.args[1].value, str)):
                funde.append((k.lineno, k.args[1].value))
        ziele = (k.targets if isinstance(k, ast.Assign)
                 else [k.target] if isinstance(k, (ast.AugAssign, ast.AnnAssign)) else [])
        for z in ziele:
            if isinstance(z, ast.Attribute) and isinstance(z.value, ast.Name) and z.value.id in aliase:
                funde.append((z.lineno, z.attr))
    return sorted(funde)


def test_kein_test_ersetzt_einen_verweis():
    """Ein Ersatz an `app.X` für einen Verweis ist ein vergessenes Patch-Ziel:
    ersetzt wird `modul.X`. Auch Ersatz mit eigenem Rückweg (try/finally),
    den die Laufzeit-Wache der conftest am Testende nicht mehr sähe."""
    funde = []
    for pfad in sorted(glob.glob(os.path.join(TEST_DIR, "*.py"))):
        if os.path.abspath(pfad) == DIESE_DATEI:
            continue                               # die Gegenproben unten ersetzen mit Absicht
        with open(pfad, encoding="utf-8") as f:
            for zeile, name in ersatz_an_der_app(f.read()):
                if name in conftest.VERWEISE:
                    funde.append(f"{os.path.basename(pfad)}:{zeile} app.{name} "
                                 f"-> {conftest.VERWEISE[name]}.{name}")
    assert not funde, "Tests ersetzen einen Verweis statt des Heimatmoduls:\n" + "\n".join(funde)


def test_gegenprobe_ersatz_an_der_app_wird_gefunden():
    quelle = ("import youtube_app as app\n"
              "import links\n"
              "def test_x(monkeypatch):\n"
              "    monkeypatch.setattr(app, '_video_id', lambda u: u)\n"
              "    monkeypatch.setattr('youtube_app._kanal_url', str)\n"
              "    app._ist_mix = lambda u: True\n"
              "    monkeypatch.setattr(links, '_mix_limit', int)\n")
    assert ersatz_an_der_app(quelle) == [(4, "_video_id"), (5, "_kanal_url"), (6, "_ist_mix")]


def test_gegenprobe_laufzeit_wache(monkeypatch):
    """Die Laufzeit-Wache der conftest sieht einen ersetzten Verweis, und nur
    ihn: der Ersatz am Heimatmodul ist der richtige Weg."""
    import links
    monkeypatch.setattr(links, "_video_id", lambda u: "ersatz")
    assert conftest.umgebogene_verweise() == []
    assert app._kanal_url is links._kanal_url
    monkeypatch.setattr(app, "_video_id", lambda u: u)
    assert conftest.umgebogene_verweise() == ["_video_id"]
    monkeypatch.undo()                             # sonst schlüge die Wache hier am Ende an
    assert conftest.umgebogene_verweise() == []


def test_gegenprobe_ersatz_am_heimatmodul_erreicht_die_app(monkeypatch):
    """Der richtige Weg wirkt: ein Ersatz an links.X erreicht die Aufrufer in
    der App (hier die Schon-geladen-DB, die den Schlüssel aus der Video-Id baut)."""
    import links
    monkeypatch.setattr(links, "_video_id", lambda u: "ERSATZ")
    assert app._geladen_key("https://www.youtube.com/watch?v=abcdefghijk", "mp3") == "ERSATZ|mp3"
