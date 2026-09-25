# -*- coding: utf-8 -*-
"""Doppelungen zusammengelegt (Gesamtprüfung Gruppe 7, Abschnitt 5, 25.09.2026).

Heiß nachladbare Seiten: Welche Seiten pro Anfrage frisch geladen werden,
stand an drei Stellen (Router, Selbst-Neustart, `ui_stand`). In der Liste des
Selbst-Neustarts fehlte `fernbedienung.py`: Der Router lud sie pro Anfrage neu,
und trotzdem startete jede Änderung daran den ganzen Server neu. Jetzt steht
es an EINER Stelle (`HEISSE_SEITEN`); geprüft wird am Verhalten: was der
echte Router neu lädt, was den Selbst-Neustart auslöst, was `ui_stand` zählt.
"""
import ast
import glob
import importlib
import json
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
for _pfad in (MODUL_DIR, TEST_DIR):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

import links  # noqa: E402  (Kanal-Regel, seit Gesamtprüfung Y2 dort)
import musik_einstufung  # noqa: E402  (Musikmuster, seit Gesamtprüfung Y3 dort)
import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import _anfrage, rechner  # noqa: E402,F401  (rechner: autouse)

PC = {"Host": "127.0.0.1:8776"}
SEITEN = ("/", "/m", "/fernbedienung")          # die Seiten-Routen des GET-Routers


# ------------------------------------------------------------ heiß nachladbare Seiten

def _neu_geladen(monkeypatch):
    """importlib.reload durch einen Zeugen ersetzen: merkt sich die Namen in
    Aufruf-Reihenfolge und lädt nichts wirklich neu."""
    geladen = []
    monkeypatch.setattr(importlib, "reload", lambda m: geladen.append(m.__name__) or m)
    return geladen


def test_der_router_laedt_genau_die_heissen_seiten_neu(monkeypatch):
    """Jede Seiten-Route lädt ihre Seite (und den Baustein davor) pro Anfrage
    neu, und genau diese Dateien löst der Selbst-Neustart NICHT aus. Vorher
    lud der Router fernbedienung.py neu, die Neustart-Liste kannte sie nicht."""
    alle = set()
    for route in SEITEN:
        geladen = _neu_geladen(monkeypatch)
        st, _, koerper = _anfrage(route, kopf=PC)
        assert st == 200 and koerper.lstrip().lower().startswith(b"<!doctype html"), (route, koerper[:80])
        assert geladen, f"{route}: die Seite lädt nicht pro Anfrage neu"
        if "medien_session" in geladen:
            assert geladen.index("medien_session") < len(geladen) - 1, \
                f"{route}: der Baustein muss VOR der Seite nachladen: {geladen}"
        alle |= set(geladen)
    assert {m + ".py" for m in alle} == app._HEISS_NACHLADBAR, (sorted(alle), sorted(app._HEISS_NACHLADBAR))


def _code_ordner(monkeypatch, tmp_path):
    for name in ("youtube_app.py", "filme.py", "oberflaeche.py", "handy.py",
                 "medien_session.py", "fernbedienung.py"):
        (tmp_path / name).write_text("# Attrappe\n", encoding="utf-8")
        os.utime(tmp_path / name, (1_700_000_000, 1_700_000_000))
    monkeypatch.setattr(app, "SCRIPT_DIR", str(tmp_path))


def test_aenderung_an_einer_heissen_seite_startet_den_server_nicht_neu(monkeypatch, tmp_path):
    _code_ordner(monkeypatch, tmp_path)
    vorher = app._quell_signatur()
    for name in ("oberflaeche.py", "handy.py", "medien_session.py", "fernbedienung.py"):
        os.utime(tmp_path / name, (1_700_000_500, 1_700_000_500))
        assert app._quell_signatur() == vorher, f"{name}: löst einen unnötigen Selbst-Neustart aus"
    os.utime(tmp_path / "filme.py", (1_700_000_500, 1_700_000_500))
    assert app._quell_signatur() != vorher, "Gegenprobe: Backend-Code muss den Neustart auslösen"


def test_ui_stand_zaehlt_die_oberflaeche_und_ihren_baustein(monkeypatch, tmp_path):
    """Alte Tabs erneuern sich, wenn die Oberfläche ODER der Baustein neuer
    ist; die Handy-Seite und die Fernbedienung zählen hier nicht mit."""
    _code_ordner(monkeypatch, tmp_path)

    def stand():
        st, _, koerper = _anfrage("/api/status", kopf=PC)
        assert st == 200, koerper[:120]
        return json.loads(koerper)["ui_stand"]
    assert stand() == 1_700_000_000
    os.utime(tmp_path / "handy.py", (1_700_000_900, 1_700_000_900))
    os.utime(tmp_path / "fernbedienung.py", (1_700_000_900, 1_700_000_900))
    assert stand() == 1_700_000_000
    os.utime(tmp_path / "medien_session.py", (1_700_000_100, 1_700_000_100))
    assert stand() == 1_700_000_100
    os.utime(tmp_path / "oberflaeche.py", (1_700_000_200, 1_700_000_200))
    assert stand() == 1_700_000_200


# ------------------------------------------------------------ JS-Fehler-Rekorder

def test_js_rekorder_schreibt_unter_der_sperre_des_fehlerkanals(monkeypatch, tmp_path):
    """Der Rekorder der Oberfläche war eine Kopie von `fehler_merken`, nur ohne
    `_fehler_lock`: Zwei Meldungen über dem Deckel konnten sich beim Kürzen
    gegenseitig Zeilen wegschreiben. Jetzt wartet er auf dieselbe Sperre."""
    import threading
    ziel = tmp_path / "js_fehler.jsonl"
    monkeypatch.setattr(app, "JS_FEHLER_LOG", str(ziel))
    ergebnis = {}

    def melden():
        ergebnis["antwort"] = _anfrage("/api/js_fehler", methode="POST", kopf=PC,
                                       rumpf={"text": "TypeError: x", "quelle": "/", "zeile": 7, "stack": "at f"})
    with app._fehler_lock:
        faden = threading.Thread(target=melden, daemon=True)
        faden.start()
        faden.join(0.5)
        assert not ziel.exists(), "der Rekorder schrieb, obwohl der Fehlerkanal gesperrt war"
    faden.join(5)
    assert ergebnis["antwort"][0] == 200
    zeile = json.loads(ziel.read_text(encoding="utf-8").strip())
    assert {k: zeile[k] for k in ("text", "quelle", "zeile", "stack")} == \
        {"text": "TypeError: x", "quelle": "/", "zeile": 7, "stack": "at f"}, "die Felder bleiben"
    assert set(zeile) == {"ts", "text", "quelle", "zeile", "stack"}


def test_js_rekorder_bleibt_gedeckelt(monkeypatch, tmp_path):
    ziel = tmp_path / "js_fehler.jsonl"
    ziel.write_text("x" * 250_000 + "\n", encoding="utf-8")
    monkeypatch.setattr(app, "JS_FEHLER_LOG", str(ziel))
    st, _, _ = _anfrage("/api/js_fehler", methode="POST", kopf=PC, rumpf={"text": "Probe"})
    assert st == 200 and ziel.stat().st_size < 200_000
    assert json.loads(ziel.read_text(encoding="utf-8").splitlines()[-1])["text"] == "Probe"


# ------------------------------------------------------------ Kanal-Links

KANAL_PROBEN = [
    "https://www.youtube.com/@kanal", "https://www.youtube.com/@kanal/", "https://youtube.com/@Kanal",
    "https://www.youtube.com/channel/UC123", "https://www.youtube.com/c/Name", "https://www.youtube.com/user/alt",
    "https://www.youtube.com/@kanal/videos", "https://www.youtube.com/@kanal/streams",
    "https://www.youtube.com/@kanal/shorts", "https://www.youtube.com/@kanal/playlists",
    "https://www.youtube.com/@kanal/featured", "https://www.youtube.com/@kanal/live",
    "https://www.youtube.com/@kanal/community", "https://www.youtube.com/@kanal/about",
    "https://www.youtube.com/watch?v=abcdefghijk", "https://www.youtube.com/playlist?list=PL1",
    "https://www.youtube.com/shorts/abcdefghijk", "https://www.youtube.com/", "https://www.youtube.com/results",
    "https://www.youtube.com/@a/b/c",
]


def test_kanal_links_eine_regel_fuer_beide_leser():
    """link_deuten und _kanal_url urteilen gleich: eine blosse Kanal-Wurzel ist
    mehrdeutig (laden oder abonnieren?) und bekommt beim Laden /videos
    angehängt; eine Unterseite ist eindeutig und bleibt, wie sie ist."""
    for url in KANAL_PROBEN:
        d = app.link_deuten(url)
        wurzel = d["typ"] == "kanal" and not d["eindeutig"]
        assert (app._kanal_url(url) != url) == wurzel, (url, d["typ"], app._kanal_url(url))
        if wurzel:
            assert app._kanal_url(url).endswith("/videos")


def test_kanal_links_regel_steht_an_einer_stelle(monkeypatch):
    """Die Regel stand zweimal wortgleich da (link_deuten und _kanal_url). Jetzt
    gibt es sie einmal: Eine neue Unterseite gilt sofort für beide Leser.
    Ersetzt wird im Heimatmodul `links` (Gesamtprüfung Y2): ein Ersatz an
    app._KANAL_UNTERSEITEN träfe keinen der beiden Leser mehr."""
    url = "https://www.youtube.com/@kanal/community"
    assert app.link_deuten(url)["typ"] == "video"      # heute: keine bekannte Unterseite
    monkeypatch.setattr(links, "_KANAL_UNTERSEITEN", links._KANAL_UNTERSEITEN + ("/community",))
    assert app.link_deuten(url) == {"typ": "kanal", "eindeutig": True, "frage": "", "optionen": []}
    assert app._kanal_url(url) == url


# ------------------------------------------------------------ Musikmuster

MUSIK_PROBEN = [
    ({"name": "Queen - Bohemian Rhapsody [abc].mp4"}, True),
    ({"name": "Queen – Bohemian Rhapsody.webm"}, True),
    ({"name": "Q - X.mkv"}, False),                      # Künstler zu kurz
    ({"name": "Warum X - und Y.mp4"}, True),             # Muster greift (bewusst großzügig)
    ({"name": "Lets Play Folge 3.mp4"}, False),
    ({"name": "Ein sehr sehr langer Kanalname der mehr als vierzig Zeichen hat - Titel.mp4"}, False),
    ({"name": "Clip.mp4", "uploader": "Queen - Topic"}, True),
    ({"name": "Clip.mp4", "uploader": "QueenVEVO"}, True),
    ({"name": "Hörbuch.mp3"}, True),
    ({"name": "x.avi"}, False),
    ({"name": "Queen - Song.avi"}, False),               # kein Video-Format der Liste
    ({"name": "egal.mp4", "kategorie": "MP3"}, True),
]


def test_ist_musik_bleibt_gleich():
    for e, erwartet in MUSIK_PROBEN:
        assert app._ist_musik(e) is erwartet, e


def test_musikmuster_steht_an_einer_stelle(monkeypatch):
    """„Künstler - Titel“ stand wortgleich in _ist_musik und _ist_musik_muster.
    Jetzt fragt _ist_musik das Muster ab: eine Änderung wirkt auf beide.
    Ersetzt wird im Heimatmodul `musik_einstufung` (Gesamtprüfung Y3)."""
    gefragt = []
    monkeypatch.setattr(musik_einstufung, "_ist_musik_muster", lambda e: gefragt.append(e["name"]) or True)
    assert app._ist_musik({"name": "Lets Play Folge 3.mp4"}) is True
    assert gefragt == ["Lets Play Folge 3.mp4"]


# ------------------------------------------------------------ Audio-Endungen (Y3)
# Vorher fünf Stellen in drei Fassungen (Abschnitt 5). Ob `.wav` und `.aac`
# überall als Audio gelten, ist JB-Frage 7 (Abschnitt 9): Zähler und Auto-Tag
# änderten sich. Bis dahin bleibt jede Fassung, wie sie ist. Diese Proben
# halten das heutige Ergebnis fest, auch das Uneinheitliche.

ENDUNGEN = (".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav", ".aac",
            ".mp4", ".mkv", ".webm", ".mov", ".avi", ".txt")
AUDIO_KURZ = {".mp3", ".m4a", ".opus", ".ogg", ".flac"}


def test_audio_endungen_ergebnis_bleibt_gleich(monkeypatch):
    kat = {e: app._kat_aus_name("x" + e) for e in ENDUNGEN}
    assert kat == {e: "MP3" if e in AUDIO_KURZ | {".wav"} else "Video" for e in ENDUNGEN}
    musik = {e: app._ist_musik({"name": "x" + e}) for e in ENDUNGEN}
    assert musik == {e: e in AUDIO_KURZ for e in ENDUNGEN}          # .wav/.aac: nein
    grad = {e: app._musik_grad({"name": "x" + e}) for e in ENDUNGEN}
    assert grad == {e: "wahrscheinlich" if e in AUDIO_KURZ else "nein" for e in ENDUNGEN}
    video = {e: app._ist_musik({"name": "Queen - Song" + e}) for e in ENDUNGEN}
    assert video == {e: e in AUDIO_KURZ | {".mp4", ".mkv", ".webm"} for e in ENDUNGEN}
    soll = {e: app._soll_kategorie("x" + e) for e in (".wav", ".aac", ".mp3", ".txt")}
    assert soll == {".wav": "MP3", ".aac": "MP3", ".mp3": "MP3", ".txt": ""}   # alle sieben
    monkeypatch.setattr(app, "_geladen", {f"id{i}|q": {"name": "x" + e} for i, e in enumerate(ENDUNGEN)})
    assert app.db_statistik() == {"gesamt": len(ENDUNGEN),
                                  "kategorien": {"MP3": len(AUDIO_KURZ), "Video": len(ENDUNGEN) - len(AUDIO_KURZ)}}


def audio_endungslisten(quelltext):
    """Zeilen jeder Liste von Audio-Endungen im Quelltext: ein Tupel, eine
    Liste oder eine Menge aus mindestens drei Zeichenketten, die alle mit
    einem Punkt beginnen, darunter ".mp3"."""
    zeilen = []
    for k in ast.walk(ast.parse(quelltext)):
        if isinstance(k, (ast.Tuple, ast.List, ast.Set)) and len(k.elts) >= 3:
            werte = [e.value for e in k.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if len(werte) == len(k.elts) and ".mp3" in werte and all(w.startswith(".") for w in werte):
                zeilen.append(k.lineno)
    return zeilen


def test_audio_endungen_stehen_an_einer_stelle():
    """Jede Fassung steht einmal in musik_einstufung.py; eine neue Liste
    anderswo wäre die sechste Stelle. Auto-Discovery über alle Programm-Dateien."""
    funde = {}
    for pfad in sorted(glob.glob(os.path.join(MODUL_DIR, "*.py"))
                       + glob.glob(os.path.join(MODUL_DIR, "tools", "*.py"))):
        with open(pfad, encoding="utf-8") as f:
            zeilen = audio_endungslisten(f.read())
        if zeilen:
            funde[os.path.relpath(pfad, MODUL_DIR)] = zeilen
    assert set(funde) == {"musik_einstufung.py"}, funde
    assert len(funde["musik_einstufung.py"]) == 3, "drei Fassungen, je einmal (JB-Frage 7 offen)"


def test_gegenprobe_endungsliste_wird_gefunden():
    quelle = 'def f(n):\n    return n.endswith((".mp3", ".m4a", ".flac"))\nX = (".m4a", ".mp4", ".mov")\n'
    assert audio_endungslisten(quelle) == [2]
