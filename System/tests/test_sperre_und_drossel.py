# -*- coding: utf-8 -*-
"""Wächter für die YouTube-Sperren (Befunde 07.09.2026).

Fünf Dinge werden hier festgenagelt, alle ohne Netz und ohne Server:

1. Eine Sperre (Bot-Verdacht, 403, 429) wird NICHT als Cookie-Problem geheilt.
   YouTube hängt an jede Bot-Meldung den Satz »Use --cookies-from-browser …«
   an (`YoutubeIE._youtube_login_hint`) — der enthält »cookie« und »browser«,
   also hielt `_ist_cookie_fehler` die Sperre für ein Cookie-Problem, warf die
   Cookies weg und lief sofort erneut los. Ohne Cookies wählt yt-dlp aber die
   nicht angemeldeten Vorgabe-Wege, also genau die gesperrten.
2. Ein gesperrter Eintrag wird nicht wiederholt, sondern gestoppt und
   dauerhaft festgehalten.
3. Kein Funktions-Parameter verdeckt ein importiertes Modul (Auto-Discovery
   über alle Programm-Dateien). Der Parameter `geo` in `_download_lauf` hat
   genau das getan: im Fehlerzweig stand `False.ist_geo_fehler(...)`, jeder
   gewöhnliche Download-Fehler flog als AttributeError aus der Funktion und
   der komplette Neuversuch-Mechanismus war unerreichbar.
4. Gegen YouTube bremst eine Drossel, so wie gegen MusicBrainz auch.
5. Die Anzeige übersetzt Sperren, bevor sie »Cookie-Fehler« sagt.

Nicht gemessen (Leitplanke P6 verlangt die Liste): ob YouTube eine Sperre
tatsächlich wieder aufhebt, ob die gewählten Pausen die richtige Länge haben,
und das Verhalten des fertigen PyInstaller-Pakets.
"""
import ast
import glob
import io as _io
import os
import re
import sys
import types

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import oberflaeche  # noqa: E402
import youtube_app as app  # noqa: E402

DIESE_DATEI = os.path.abspath(__file__)


# ------------------------------------------------- 1) Sperre schlägt Cookie

def _echte_bot_meldung():
    """Der ECHTE Meldungstext von yt-dlp, nicht ein nachgebauter (P6: die
    Attrappe muss den Unterschied modellieren, um den es geht)."""
    from yt_dlp.extractor.youtube._video import YoutubeIE
    return ("ERROR: [youtube] ABCdef12345: Sign in to confirm you are not a bot. "
            + YoutubeIE()._youtube_login_hint)


def test_bot_meldung_traegt_den_cookie_hinweis():
    """Belegt die Ursache: die Bot-Meldung SIEHT aus wie ein Cookie-Problem."""
    t = _echte_bot_meldung().lower()
    assert "cookie" in t and "browser" in t
    assert app._ist_cookie_fehler(_echte_bot_meldung()) is True


def test_sperre_wird_vor_cookie_erkannt():
    assert app._ist_sperre(_echte_bot_meldung()) is True


def test_sperre_erkennt_alle_faelle():
    faelle = [
        "Sign in to confirm you are not a bot",
        "The uploader has rate-limited this download",
        "HTTP Error 429: Too Many Requests",
        "HTTP Error 403: Forbidden",
        "Unable to solve captcha",
    ]
    for f in faelle:
        assert app._ist_sperre(f) is True, f


def test_gegenprobe_harmlose_meldungen_sind_keine_sperre():
    """Rote Gegenprobe zur Wortgrenze: in der Video-Kennung »dQw403abcXY«
    steckt »403« ohne jede Bedeutung (Leitplanke P8)."""
    harmlos = [
        "unable to download video data: <urlopen error timed out>",
        "[youtube] dQw403abcXY: Downloading webpage",
        "[youtube] xy429zzz1234: Video unavailable",
        "ffmpeg exited with code 1",
    ]
    for f in harmlos:
        assert app._ist_sperre(f) is False, f


# ------------------------------------------- 2) Gesperrt heißt nicht warten

class _AttrappeYDL:
    """yt-dlp-Attrappe, die genau eine Meldung wirft (kein Netz)."""
    meldung = ""

    def __init__(self, opts):
        _AttrappeYDL.letzte_opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=False):
        raise RuntimeError(_AttrappeYDL.meldung)


def _lauf_mit(meldung, tmp_path, monkeypatch):
    fake = types.ModuleType("yt_dlp")
    fake.YoutubeDL = _AttrappeYDL
    _AttrappeYDL.meldung = meldung
    monkeypatch.setitem(sys.modules, "yt_dlp", fake)
    monkeypatch.setattr(app.Q, "speichern", lambda *a, **k: None)
    monkeypatch.setattr(app, "FEHLER_LOG", str(tmp_path / "yt_fehler.jsonl"))
    item = {"id": "waechter1", "qualitaet": "720p", "status": "laeuft",
            "titel": "Probe", "url": "https://www.youtube.com/watch?v=ABCdef12345",
            "prozent": 0.0, "geladen": 0, "gesamt": 0, "geschw": 0, "phase": "",
            "versuche": 0, "fehler": "", "naechster_versuch": 0}
    app._download_lauf(item)
    return item


def test_gesperrter_eintrag_wird_nicht_wiederholt(tmp_path, monkeypatch):
    item = _lauf_mit(_echte_bot_meldung(), tmp_path, monkeypatch)
    assert item["status"] == "fehler", (
        "Eine Sperre darf nicht in den Backoff — jeder Neuversuch bestätigt "
        "YouTube das Muster und verlängert die Sperre")
    assert not item["naechster_versuch"]


def test_gesperrter_eintrag_hinterlaesst_eine_spur(tmp_path, monkeypatch):
    _lauf_mit("HTTP Error 429: Too Many Requests", tmp_path, monkeypatch)
    spur = tmp_path / "yt_fehler.jsonl"
    assert spur.exists(), "Fehlschlag ohne dauerhafte Spur"
    text = spur.read_text(encoding="utf-8")
    assert "sperre" in text and "429" in text


def test_normaler_fehler_geht_weiter_in_den_backoff(tmp_path, monkeypatch):
    """Gegenprobe zur Sperre UND Regressions-Wache für die Modul-Verdeckung:
    ein gewöhnlicher Netzfehler MUSS den Neuversuch-Mechanismus erreichen."""
    item = _lauf_mit("unable to download video data: <urlopen error timed out>",
                     tmp_path, monkeypatch)
    assert item["status"] == "wartend", (
        "Der Backoff ist unerreichbar — genau das Bild, das die verdeckte "
        "geo-Variable erzeugt hat")
    assert item["versuche"] == 1
    assert item["naechster_versuch"] > 0


def test_fehlerspur_bleibt_gedeckelt(tmp_path):
    """Der Fehlerkanal darf nie ungebremst wachsen (Muster js_fehler.jsonl)."""
    ziel = tmp_path / "yt_fehler.jsonl"
    ziel.write_text("x" * 250_000 + "\n", encoding="utf-8")
    app.fehler_merken("https://example.invalid/v", "Probe", "test", pfad=str(ziel))
    assert ziel.stat().st_size < 200_000


def test_jeder_zeilen_deckel_kuerzt_auch_nach_bytes():
    """Fehler-Zwilling: »die letzten 200 Zeilen behalten« deckelt nicht, wenn
    EINE Zeile riesig ist (abgeschnittener Fremd-Text ohne Umbruch). Beide
    Rekorder — `yt_fehler.jsonl` und `js_fehler.jsonl` — müssen zusätzlich nach
    Bytes kürzen. Auto-Discovery über alle Zeilen-Deckel der Programmdateien."""
    offen = []
    for pfad in _programm_dateien():
        with _io.open(pfad, encoding="utf-8") as f:
            zeilen = f.readlines()
        for nr, zeile in enumerate(zeilen):
            if "readlines()[-" not in zeile:
                continue
            fenster = "".join(zeilen[nr:nr + 8])
            if "encode(" not in fenster or "pop(0)" not in fenster:
                offen.append((os.path.basename(pfad), nr + 1, zeile.strip()))
    assert not offen, (
        "Zeilen-Deckel ohne Byte-Kürzung — eine einzige lange Zeile hebelt ihn "
        "aus: " + repr(offen))


# ------------------------------------------- 3) Kein Parameter verdeckt ein Modul

def _modulnamen(baum):
    namen = set()
    for knoten in baum.body:
        if isinstance(knoten, ast.Import):
            for a in knoten.names:
                namen.add((a.asname or a.name).split(".")[0])
    return namen


def _verdeckungen(quelle):
    """(Funktion, Modul, Attribut, Zeile) je Parameter, der ein importiertes
    Modul verdeckt UND im Rumpf als Modul benutzt wird."""
    baum = ast.parse(quelle)
    mods = _modulnamen(baum)
    funde = []
    for fn in ast.walk(baum):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        koll = {a.arg for a in fn.args.args + fn.args.kwonlyargs} & mods
        if not koll:
            continue
        for m in ast.walk(fn):
            if (isinstance(m, ast.Attribute) and isinstance(m.value, ast.Name)
                    and m.value.id in koll):
                funde.append((fn.name, m.value.id, m.attr, m.lineno))
    return funde


def test_gegenprobe_verdeckung_wird_gefunden():
    """Rote Gegenprobe: genau der Bauzustand von vor der Reparatur."""
    kaputt = ("import geo\n"
              "def _download_lauf(item, geo=False):\n"
              "    if geo:\n"
              "        return\n"
              "    if geo.ist_geo_fehler('x'):\n"
              "        pass\n")
    assert _verdeckungen(kaputt) == [("_download_lauf", "geo", "ist_geo_fehler", 5)]
    heil = ("import geo\n"
            "def _download_lauf(item, geo_lauf=False):\n"
            "    if geo_lauf:\n"
            "        return\n"
            "    if geo.ist_geo_fehler('x'):\n"
            "        pass\n")
    assert _verdeckungen(heil) == []


def _programm_dateien():
    """Auto-Discovery statt Handliste: alle Programm-Dateien von SyncYouTube,
    ohne Tests, ohne geliehene Motoren, ohne Bau-Reste."""
    aus = ("bin", "build", "build_tmp", "dist", "dist_exe", "daten", "tests",
           "__pycache__", "docs")
    dateien = []
    muster = (glob.glob(os.path.join(MODUL_DIR, "*.py"))
              + glob.glob(os.path.join(MODUL_DIR, "tools", "*.py")))
    for pfad in muster:
        voll = os.path.abspath(pfad)
        if any(t in aus for t in voll.split(os.sep)) or voll == DIESE_DATEI:
            continue
        dateien.append(voll)
    return dateien


def test_kein_parameter_verdeckt_ein_modul():
    assert _programm_dateien(), "Auto-Discovery hat nichts gefunden"
    schuldige = []
    for pfad in _programm_dateien():
        with _io.open(pfad, encoding="utf-8") as f:
            for fund in _verdeckungen(f.read()):
                schuldige.append((os.path.basename(pfad),) + fund)
    assert not schuldige, (
        "Parameter verdeckt ein importiertes Modul — der Modulzugriff im selben "
        "Rumpf wird zur AttributeError-Falle: " + repr(schuldige))


# ------------------------------------------------------------- 4) Drossel

def test_drossel_gegen_youtube():
    """Gegen MusicBrainz wird an sieben Stellen pausiert, gegen YouTube stand
    nichts (Leitplanke P10: fremde Dienste bremsen)."""
    assert app.DROSSEL.get("sleep_interval", 0) >= 1
    assert app.DROSSEL.get("max_sleep_interval", 0) >= app.DROSSEL["sleep_interval"]
    assert app.DROSSEL.get("sleep_interval_requests", 0) >= 1


def test_drossel_bremst_nur_den_download_weg():
    """Die Bremse gehoert an den Download, nicht an die Auflösung.

    Sie stand zuerst in `_ydl_basis_opts` und wirkte damit auf alle sechs
    Aufrufer — auch auf `aufloesen`, `untertitel_nachladen`, `_abo_flach`,
    `_enrich_eintrag` und `_zugang_ok`, also auf die Wege, bei denen JB vor dem
    Bildschirm auf eine Antwort wartet (Abnahme-Mangel 07.09.2026).

    ROTE GEGENPROBE: die drei Schluessel zurueck in `_ydl_basis_opts` schreiben
    ⇒ dieser Test faellt."""
    basis = app._ydl_basis_opts(mit_cookies=False)
    for schluessel in ("sleep_interval", "max_sleep_interval", "sleep_interval_requests"):
        assert schluessel not in basis, (
            f"{schluessel} steht in der gemeinsamen Options-Basis und bremst damit "
            f"auch das Aufloesen, den Abo-Scan und die Anreicherung")
    quelle = _io.open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    stelle = quelle.index("def _download_lauf(")
    ende = quelle.index(chr(10) + "def ", stelle + 10)
    assert "opts.update(DROSSEL)" in quelle[stelle:ende], (
        "Der Download-Weg muss die Drossel selbst setzen")


def test_yt_dlp_kennt_android_vr_nicht_mehr_als_vorgabe():
    """yt-dlp 2026.07.04 hatte android_vr an erster Stelle der Vorgabe-Wege;
    YouTube weist den seit dem 17./18.08.2026 mit HTTP 403 ab (yt-dlp-Fehler
    17456, behoben in 2026.08.19). Fällt die venv zurück, fällt dieser
    Wächter."""
    from yt_dlp.extractor.youtube._video import YoutubeIE
    assert "android_vr" not in YoutubeIE._DEFAULT_CLIENTS, (
        "yt-dlp ist wieder auf einem Stand, der android_vr als Vorgabe nutzt — "
        "das ist der Weg, den YouTube mit 403 abweist")


# ------------------------------------------------- 5) Anzeige übersetzt Sperren

def _kurzfehler_quelle():
    treffer = re.search(r"function kurzfehler\(t\)\{.*?\n\}", oberflaeche.HTML, re.S)
    assert treffer, "kurzfehler() nicht in der Oberfläche gefunden"
    return treffer.group(0)


def test_anzeige_prueft_sperren_vor_cookie():
    """Reihenfolge ist hier die Sache selbst: die Bot-Meldung enthält das Wort
    »cookie«, also log die Anzeige den Nutzer mit »Cookie-Fehler« an."""
    q = _kurzfehler_quelle()
    assert q.index("not a bot") < q.index("includes('cookie')")
    assert q.index("too many requests") < q.index("includes('cookie')")
    assert q.index("forbidden") < q.index("includes('cookie')")


def test_anzeige_uebersetzt_die_drei_faelle():
    q = _kurzfehler_quelle()
    for wort in ("Bot-Verdacht", "drosselt", "403"):
        assert wort in q, wort


def test_anzeige_liefert_die_richtigen_texte(tmp_path):
    """Ergebnis statt Schreibweise (P6): `kurzfehler()` wird wirklich
    ausgeführt — mit der geliehenen JS-Laufzeit aus `System/bin` (deno, dieselbe,
    die yt-dlp für YouTubes n-Challenge braucht). Fehlt sie, wird übersprungen
    statt still grün zu behaupten."""
    import json
    import subprocess

    deno = os.path.join(MODUL_DIR, "bin", "deno.exe")
    if not os.path.exists(deno):
        import pytest
        pytest.skip("deno fehlt in System/bin — JS nicht ausführbar gemessen")

    proben = [_echte_bot_meldung(),
              "unable to download video data: HTTP Error 429: Too Many Requests",
              "HTTP Error 403: Forbidden",
              "could not copy Firefox cookie database",
              "[youtube] dQw403abcXY: Video unavailable"]
    skript = tmp_path / "kurzfehler.mjs"
    skript.write_text(_kurzfehler_quelle()
                      + "\nfor (const x of " + json.dumps(proben) + ")"
                      + " console.log(kurzfehler(x));\n", encoding="utf-8")
    lauf = subprocess.run([deno, "run", str(skript)], capture_output=True,
                          text=True, encoding="utf-8", timeout=120)
    assert lauf.returncode == 0, lauf.stderr[-500:]
    zeilen = [z.strip() for z in lauf.stdout.splitlines() if z.strip()]
    assert zeilen == ["YouTube verlangt Anmeldung (Bot-Verdacht)",
                      "zu viele Anfragen — YouTube drosselt",
                      "YouTube verweigert den Zugriff (403)",
                      "Cookie-Fehler",            # echter Cookie-Fehler bleibt einer
                      "nicht verfügbar"], zeilen  # »403« in der Kennung zählt nicht


def test_sperre_im_geo_lauf_hinterlaesst_eine_spur():
    """Abnahme-Mangel 07.09.2026: Der Geo-Zweig kehrte vor der Aufzeichnung zurueck.

    Oben wird bei einer Sperre absichtlich NICHT gemerkt (das macht der
    `elif _ist_sperre`-Zweig weiter unten), und `if geo_lauf: … return` sprang
    genau daran vorbei. Ausgerechnet der Fall, fuer den der Fehlerkanal gebaut
    wurde, blieb damit spurlos.

    ROTE GEGENPROBE: die drei Zeilen im geo_lauf-Zweig entfernen ⇒ dieser Test
    faellt (gefahren am 07.09.2026)."""
    quelle = _io.open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    stelle = quelle.index("def _download_lauf(")
    ende = quelle.index(chr(10) + "def ", stelle + 10)
    rumpf = quelle[stelle:ende]
    geo_zweig = rumpf[rumpf.index('if geo_lauf:'):]
    bis_return = geo_zweig[:geo_zweig.index("return")]
    assert "fehler_merken(" in bis_return, (
        "Eine Sperre im Geo-Lauf muss aufgezeichnet werden, bevor die Funktion "
        "zurueckkehrt")
    assert "_ist_sperre(" in bis_return, "…und zwar nur, wenn es wirklich eine Sperre ist"
