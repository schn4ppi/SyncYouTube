# -*- coding: utf-8 -*-
"""Nebenläufigkeit und Persistenz der App (Gesamtprüfung 25.09.2026, Gruppe 4).

Jeder Test fährt das echte Verhalten: echte Dateien in tmp_path (die conftest
legt alle Datenpfade dorthin), echte Fäden, und wo Windows mitspielt, ein
echter Leser, der die Zieldatei offen hält. Attrappen stehen nur dort, wo
sonst YouTube gefragt würde.
"""
import json
import os
import sys
import threading

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402


def _faeden(ziele, timeout=60):
    """Startet je Ziel einen Faden, wartet und meldet hängende Fäden laut."""
    faeden = [threading.Thread(target=z, daemon=True) for z in ziele]
    for f in faeden:
        f.start()
    for f in faeden:
        f.join(timeout)
    assert not any(f.is_alive() for f in faeden), "Fäden hängen"


# ---------------------------------------------------------------- F5: Schreiben mit Wiederholung

def test_speichern_wartet_kurz_auf_einen_leser(tmp_path):
    """Windows: os.replace scheitert, solange ein Leser die Zieldatei offen hat
    (etwa das Dashboard beim Lesen von yt_status.json). Vorher gab das Speichern
    sofort auf, und im Worker-Faden war das tödlich (F1)."""
    pfad = str(tmp_path / "yt_status.json")
    app._json_speichern(pfad, {"stand": 1})
    leser = open(pfad, encoding="utf-8")
    zu = threading.Timer(0.15, leser.close)
    zu.start()
    try:
        app._json_speichern(pfad, {"stand": 2})
    finally:
        zu.join()
        leser.close()
    with open(pfad, encoding="utf-8") as f:
        assert json.load(f) == {"stand": 2}


def test_parallele_schreiber_auf_dieselbe_datei_scheitern_nicht(tmp_path):
    """Vorher teilten sich alle Schreiber EINEN tmp-Namen (`<pfad>.tmp`)."""
    pfad = str(tmp_path / "warteschlange.json")
    start = threading.Barrier(8)
    fehler = []

    def schreiber(n):
        def lauf():
            start.wait()
            for i in range(30):
                try:
                    app._json_speichern(pfad, {"n": n, "i": i, "fuell": "x" * 4000})
                except Exception as e:               # noqa: BLE001 — sammeln, unten melden
                    fehler.append(repr(e))
        return lauf

    _faeden([schreiber(n) for n in range(8)])
    assert not fehler, f"{len(fehler)} Schreibvorgänge scheiterten, etwa {fehler[0]}"
    with open(pfad, encoding="utf-8") as f:
        assert json.load(f)["i"] == 29
    assert not [p for p in os.listdir(tmp_path) if p.endswith(".tmp")], "tmp-Reste liegen"


def test_bleibt_die_datei_blockiert_kommt_weiter_ein_oserror_ohne_reste(tmp_path):
    """Der heutige Vertrag bleibt: wer speichert, erfährt vom Scheitern (OSError).
    Neu: keine tmp-Reste neben den Daten."""
    pfad = str(tmp_path / "config.json")
    app._json_speichern(pfad, {"alt": True})
    with open(pfad, encoding="utf-8"):
        with pytest.raises(OSError):
            app._json_speichern(pfad, {"neu": True})
    with open(pfad, encoding="utf-8") as f:
        assert json.load(f) == {"alt": True}
    assert not [p for p in os.listdir(tmp_path) if p.endswith(".tmp")], "tmp-Reste liegen"


def test_cfg_schreiber_kommen_sich_nicht_in_die_quere():
    """Für config.json galten drei Sperr-Regime (Q.lock, _io_lock, keines).
    Die Wiedergabe-Regel fügt den Schlüssel `wiedergabe` ein und nimmt ihn
    wieder heraus, während die Einstellungen gespeichert werden."""
    start = threading.Barrier(2)
    fehler = []

    def wiedergabe():
        start.wait()
        for i in range(150):
            try:
                app.wiedergabe_setzen({"global": 1, "speed": 1.25} if i % 2 else {"global": 1})
            except Exception as e:                   # noqa: BLE001
                fehler.append(repr(e))

    def einstellungen():
        start.wait()
        for i in range(150):
            try:
                app.Handler._config(None, {"metadaten": bool(i % 2)})
            except Exception as e:                   # noqa: BLE001
                fehler.append(repr(e))

    _faeden([wiedergabe, einstellungen])
    assert not fehler, f"{len(fehler)} Fehler, etwa {fehler[0]}"
    with open(app.CONFIG_PFAD, encoding="utf-8") as f:
        assert json.load(f) == json.loads(json.dumps(app.CFG)), "Datei und Speicher gehen auseinander"


# ---------------------------------------------------------------- F15: Rettungskopie

def test_zweiter_defekt_ueberschreibt_die_erste_rettungskopie_nicht(tmp_path):
    pfad = tmp_path / "geladen_log.json"
    pfad.write_text("{kaputt 1", encoding="utf-8")
    assert app._json_laden(str(pfad), {}) == {}
    pfad.write_text("{kaputt 2", encoding="utf-8")
    assert app._json_laden(str(pfad), {}) == {}
    kopien = [p for p in tmp_path.iterdir() if p.name.startswith("geladen_log.json.")
              and p.name.endswith(".defekt")]
    assert sorted(p.read_text(encoding="utf-8") for p in kopien) == ["{kaputt 1", "{kaputt 2"], \
        "jede defekte Fassung braucht ihre eigene Rettungskopie"


# ---------------------------------------------------------------- F16: auto_neustart

def test_auto_neustart_laesst_sich_in_der_config_abschalten():
    with open(app.CONFIG_PFAD, "w", encoding="utf-8") as f:
        json.dump({"auto_neustart": False}, f)
    assert app.config_laden().get("auto_neustart", True) is False, \
        "config_laden warf auto_neustart weg: der Selbst-Neustart war nicht abschaltbar"


def test_auto_neustart_bleibt_als_vorgabe_an():
    assert not os.path.exists(app.CONFIG_PFAD)
    assert app.config_laden()["auto_neustart"] is True


# ---------------------------------------------------------------- F1: Worker-Tod

class _Halt(BaseException):
    """Beendet eine Worker-Schleife im Test (kein `except Exception` fängt das)."""


def _worker_mit_halt(monkeypatch, halt):
    """Die echte worker_schleife in einem Faden; `halt` beendet sie beim
    nächsten Griff nach Arbeit. Liefert den Faden und seinen Ausgang."""
    echt_naechster = app.Q.naechster

    def naechster():
        if halt.is_set():
            raise _Halt()
        return echt_naechster()
    monkeypatch.setattr(app.Q, "naechster", naechster)
    ausgang = []

    def lauf():
        try:
            app.worker_schleife()
        except _Halt:
            ausgang.append("halt")
        except BaseException as e:                   # noqa: BLE001 — der Test will den Tod sehen
            ausgang.append(repr(e))
            raise
    faden = threading.Thread(target=lauf, daemon=True)
    faden.start()
    return faden, ausgang


def _warten(bedingung, s=10.0):
    ende = threading.Event()
    for _ in range(int(s / 0.01)):
        if bedingung():
            return True
        ende.wait(0.01)
    return bedingung()


def _speichern_scheitert_einmal(monkeypatch, wann=1):
    """Q.speichern wirft beim `wann`-ten Aufruf einmal einen OSError (so, wie
    os.replace scheitert, während das Dashboard yt_status.json liest)."""
    echt = app.Q.speichern
    zaehler = {"n": 0}

    def speichern():
        zaehler["n"] += 1
        if zaehler["n"] == wann:
            raise OSError(13, "Der Prozess kann nicht auf die Datei zugreifen")
        return echt()
    monkeypatch.setattr(app.Q, "speichern", speichern)
    return zaehler


def test_worker_ueberlebt_ein_gescheitertes_speichern(monkeypatch):
    geladen = []

    def herunterladen(item):
        geladen.append(item["id"])
        item["status"] = "fertig"
    monkeypatch.setattr(app, "herunterladen", herunterladen)
    monkeypatch.setattr(app, "fehler_merken", lambda *a, **k: None)
    _speichern_scheitert_einmal(monkeypatch, wann=1)
    eins = app.Q.neu("https://www.youtube.com/watch?v=aaaaaaaaaaa", "eins", "beste")
    zwei = app.Q.neu("https://www.youtube.com/watch?v=bbbbbbbbbbb", "zwei", "beste")
    halt = threading.Event()
    faden, ausgang = _worker_mit_halt(monkeypatch, halt)
    try:
        assert _warten(lambda: len(geladen) == 2 or not faden.is_alive()), "Worker steht"
    finally:
        halt.set()
        faden.join(10)
    assert ausgang == ["halt"], f"der Worker-Faden starb: {ausgang}"
    assert geladen == [eins["id"], zwei["id"]], "nach dem Scheitern lud der Worker nicht weiter"
    assert eins["status"] != "laeuft", "der Eintrag blieb auf »laeuft« stehen"


def test_worker_ueberlebt_ein_gescheitertes_speichern_nach_einem_fehler(monkeypatch):
    """Scheitert der Download UND danach das Speichern im Fehlerzweig."""
    versuche = []

    def herunterladen(item):
        versuche.append(item["id"])
        if len(versuche) == 1:
            raise RuntimeError("yt-dlp ist abgestürzt")
        item["status"] = "fertig"
    monkeypatch.setattr(app, "herunterladen", herunterladen)
    monkeypatch.setattr(app, "fehler_merken", lambda *a, **k: None)
    _speichern_scheitert_einmal(monkeypatch, wann=2)   # 1 = vor dem Laden, 2 = im Fehlerzweig
    eins = app.Q.neu("https://www.youtube.com/watch?v=aaaaaaaaaaa", "eins", "beste")
    zwei = app.Q.neu("https://www.youtube.com/watch?v=bbbbbbbbbbb", "zwei", "beste")
    halt = threading.Event()
    faden, ausgang = _worker_mit_halt(monkeypatch, halt)
    try:
        assert _warten(lambda: len(versuche) == 2 or not faden.is_alive()), "Worker steht"
    finally:
        halt.set()
        faden.join(10)
    assert ausgang == ["halt"], f"der Worker-Faden starb: {ausgang}"
    assert eins["status"] == "fehler" and zwei["status"] == "fertig"


def test_worker_start_ersetzt_tote_faeden(monkeypatch):
    starts = []
    monkeypatch.setattr(app, "worker_schleife", lambda: starts.append(1))   # stirbt sofort
    monkeypatch.setattr(app, "_worker_anzahl", 0, raising=False)            # alter Zähler
    monkeypatch.setattr(app, "_worker_faeden", [], raising=False)
    app._worker_start(1)
    assert _warten(lambda: len(starts) == 1)
    threading.Event().wait(0.05)                     # der erste Faden ist sicher zu Ende
    app._worker_start(1)
    assert _warten(lambda: len(starts) == 2, s=2), "ein toter Worker wird nie ersetzt"


# ---------------------------------------------------------------- F2/F3: Auflösen

class _YtdlpAttrappe:
    """Statt YouTube: jeder Abruf wartet am Tor `frei` und zählt, wie viele
    gleichzeitig laufen. `antwort(url)` liefert das Info-Dict."""

    def __init__(self, antwort=None):
        self.frei = threading.Event()
        self.lock = threading.Lock()
        self.laufend = 0
        self.hoechstens = 0
        self.urls = []
        self.antwort = antwort or (lambda url: {"title": "Titel " + url[-4:], "webpage_url": url,
                                                "duration": 60})

    def ydl(self, opts):
        import contextlib
        attrappe = self

        class Ydl:
            def extract_info(self, url, download=False):
                with attrappe.lock:
                    attrappe.laufend += 1
                    attrappe.hoechstens = max(attrappe.hoechstens, attrappe.laufend)
                    attrappe.urls.append(url)
                try:
                    attrappe.frei.wait(20)
                    return attrappe.antwort(url)
                finally:
                    with attrappe.lock:
                        attrappe.laufend -= 1

        @contextlib.contextmanager
        def cm():
            yield Ydl()
        return cm()


def _aufloesen_vorbereiten(monkeypatch, antwort=None):
    attrappe = _YtdlpAttrappe(antwort)
    monkeypatch.setattr(app, "_ydl", attrappe.ydl)
    monkeypatch.setattr(app, "_liste_vermerken", lambda *a, **k: None)
    monkeypatch.setattr(app, "fehler_merken", lambda *a, **k: None)
    return attrappe


def _sechs_minuten_spaeter_heilen(monkeypatch):
    """Die Heilung einmal jetzt und einmal sechs Minuten später (sie misst ab
    dem ersten Sehen bzw. ab dem Eintritt ins Auflösen)."""
    app.queue_heilen()
    echt = app.time.time
    with monkeypatch.context() as m:
        m.setattr(app.time, "time", lambda: echt() + 360)
        app.queue_heilen()


def _url(i):
    return f"https://www.youtube.com/watch?v=vid{i:08d}"


def test_aufloesen_hoechstens_zwei_zugleich_und_wartende_heilen_nicht(monkeypatch):
    """Der Knopf „Alle (N)“ startet bis zu 5.000 Auflösungen auf einmal, jede
    mit vollem yt-dlp-Abruf: genau das Muster, das YouTube sperrt (F2)."""
    attrappe = _aufloesen_vorbereiten(monkeypatch)
    faeden = [threading.Thread(target=app.aufloesen, args=(_url(i), "beste"), daemon=True)
              for i in range(6)]
    for f in faeden:
        f.start()
    try:
        assert _warten(lambda: len(app.Q.items) == 6), "Platzhalter müssen sofort erscheinen"
        assert all(it["status"] == "prueft" for it in app.Q.items)
        assert _warten(lambda: attrappe.laufend >= 2)
        threading.Event().wait(0.3)                  # den übrigen Zeit geben, sich vorzudrängeln
        assert attrappe.hoechstens == 2, f"{attrappe.hoechstens} yt-dlp-Abrufe liefen gleichzeitig"
        # Wer nur auf einen Platz wartet, hängt nicht: die 5-min-Heilung läuft
        # erst ab dem Eintritt (vorher gab sie Wartende nach 300 s frei).
        _sechs_minuten_spaeter_heilen(monkeypatch)
        in_arbeit = {u for u in attrappe.urls}
        wartende = [it for it in app.Q.items if it["url"] not in in_arbeit]
        assert len(wartende) == 4 and all(it["status"] == "prueft" for it in wartende), \
            [it["status"] for it in wartende]
    finally:
        attrappe.frei.set()
        for f in faeden:
            f.join(20)
    assert attrappe.hoechstens == 2
    assert sorted(attrappe.urls) == [_url(i) for i in range(6)]
    assert all(it["status"] == "wartend" for it in app.Q.items), [it["status"] for it in app.Q.items]


@pytest.mark.parametrize("art", ["video", "playlist"])
def test_aufloesen_laesst_einen_schon_uebernommenen_eintrag_in_ruhe(monkeypatch, art):
    """Hängt das Auflösen länger als 5 min, reiht die Heilung den Eintrag ein
    und ein Worker lädt ihn. Kam das Auflösen danach doch zurück, setzte es den
    Status blind auf „wartend“ (ein zweiter Worker lädt dasselbe) bzw. warf den
    laufenden Eintrag aus der Liste (F3)."""
    def antwort(url):
        if art == "playlist":
            return {"_type": "playlist", "title": "Liste",
                    "entries": [{"id": "folge00001", "title": "Folge 1", "url": _url(90)}]}
        return {"title": "Titel", "webpage_url": url, "duration": 60}
    attrappe = _aufloesen_vorbereiten(monkeypatch, antwort)
    faden = threading.Thread(target=app.aufloesen, args=(_url(1), "beste"), daemon=True)
    faden.start()
    try:
        assert _warten(lambda: attrappe.laufend == 1)
        platzhalter = app.Q.items[0]
        _sechs_minuten_spaeter_heilen(monkeypatch)
        assert platzhalter["status"] == "wartend", "die Heilung reiht den hängenden Eintrag ein"
        assert app.Q.naechster() is platzhalter and platzhalter["status"] == "laeuft"
    finally:
        attrappe.frei.set()
        faden.join(20)
    assert platzhalter["status"] == "laeuft", "das späte Auflösen hat den Status überschrieben"
    assert app.Q.items == [platzhalter], "das späte Auflösen hat die Liste umgebaut"


def test_aufloesen_fragt_youtube_nicht_mehr_wenn_der_platzhalter_weg_ist(monkeypatch):
    attrappe = _aufloesen_vorbereiten(monkeypatch)
    faeden = [threading.Thread(target=app.aufloesen, args=(_url(i), "beste"), daemon=True)
              for i in range(3)]
    for f in faeden:
        f.start()
    try:
        assert _warten(lambda: len(app.Q.items) == 3 and attrappe.laufend >= 2)
        threading.Event().wait(0.1)
        dritter = next((it for it in app.Q.items if it["url"] not in attrappe.urls), None)
        assert dritter is not None, "alle drei fragten YouTube gleichzeitig"
        with app.Q.lock:
            app.Q.items.remove(dritter)              # JB entfernt ihn, solange er wartet
    finally:
        attrappe.frei.set()
        for f in faeden:
            f.join(20)
    assert dritter["url"] not in attrappe.urls, "für einen entfernten Eintrag wurde YouTube gefragt"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
