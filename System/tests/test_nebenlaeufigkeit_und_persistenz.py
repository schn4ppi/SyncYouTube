# -*- coding: utf-8 -*-
"""Nebenläufigkeit und Persistenz der App (Gesamtprüfung 25.09.2026, Gruppe 4).

Jeder Test fährt das echte Verhalten: echte Dateien in tmp_path (die conftest
legt alle Datenpfade dorthin), echte Fäden, und wo Windows mitspielt, ein
echter Leser, der die Zieldatei offen hält. Attrappen stehen nur dort, wo
sonst YouTube gefragt würde.
"""
import email.message
import io
import json
import os
import sys
import threading
import time

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import musik_einstufung  # noqa: E402  (Titel-Helfer, seit Gesamtprüfung Y3 dort)
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


def test_cfg_speichern_und_wiedergabe_regel_warten_aufeinander(monkeypatch):
    """Der Test oben wird nur mit dem alten festen tmp-Namen rot, nicht ohne
    die gemeinsame Sperre (Gegenprobe der Abnahme). Hier läuft der Serialisierer
    Schlüssel für Schlüssel über CFG und hält nach dem ersten an; genau dann
    nimmt die Wiedergabe-Regel ohne Felder den Schlüssel `wiedergabe` heraus
    (er steht in den Vorgaben). Ohne _cfg_lock ändert sich das Dict mitten im
    Durchlauf, mit ihr wartet die Regel, bis gespeichert ist."""
    assert "wiedergabe" in app.CFG
    echt = app.fam.json_schreiben
    im_lauf, weiter = threading.Event(), threading.Event()

    def langsam(pfad, daten, *a, **k):
        if pfad == app.CONFIG_PFAD and not im_lauf.is_set():
            for i, _ in enumerate(daten):            # wie ein Serialisierer über das lebende Dict
                if i == 0:
                    im_lauf.set()
                    weiter.wait(5)
        return echt(pfad, daten, *a, **k)
    monkeypatch.setattr(app.fam, "json_schreiben", langsam)
    fehler = []

    def einstellungen():
        try:
            app.Handler._config(None, {"metadaten": True})
        except Exception as e:                       # noqa: BLE001
            fehler.append("einstellungen: " + repr(e))

    def wiedergabe():
        try:
            app.wiedergabe_setzen({"global": 1})     # keine Felder: Regel und Schlüssel raus
        except Exception as e:                       # noqa: BLE001
            fehler.append("wiedergabe: " + repr(e))
    a = _im_faden(einstellungen)
    assert im_lauf.wait(10)
    b = _im_faden(wiedergabe)
    b.join(0.5)                                      # ohne gemeinsame Sperre ist sie jetzt durch
    weiter.set()
    a.join(10)
    b.join(10)
    assert not fehler, fehler
    assert "wiedergabe" not in app.CFG and app.CFG["metadaten"] is True
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
    """Statt YouTube: jeder Abruf wartet am Tor `frei` (oder an seinem eigenen
    Tor `tore[url]`) und zählt, wie viele gleichzeitig laufen. `antwort(url)`
    liefert das Info-Dict."""

    def __init__(self, antwort=None):
        self.frei = threading.Event()
        self.tore = {}
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
                    attrappe.tore.get(url, attrappe.frei).wait(20)
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
    mit vollem yt-dlp-Abruf: genau das Muster, das YouTube sperrt (F2). Wer nur
    auf einen Platz wartet, hängt nicht: die 5-min-Heilung misst ab dem Eintritt
    (vorher gab sie Wartende nach 300 s frei, auch wenn die Plätze arbeiteten)."""
    attrappe = _aufloesen_vorbereiten(monkeypatch)
    for i in range(6):
        attrappe.tore[_url(i)] = threading.Event()
    uhr = _stellbare_uhr(monkeypatch)
    faeden = [_im_faden(app.aufloesen, _url(i), "beste") for i in range(6)]
    try:
        assert _warten(lambda: len(app.Q.items) == 6), "Platzhalter müssen sofort erscheinen"
        assert all(it["status"] == "prueft" for it in app.Q.items)
        assert _warten(lambda: attrappe.laufend >= 2)
        threading.Event().wait(0.3)                  # den übrigen Zeit geben, sich vorzudrängeln
        assert attrappe.hoechstens == 2, f"{attrappe.hoechstens} yt-dlp-Abrufe liefen gleichzeitig"
        app.queue_heilen()                           # sieht alle sechs zum ersten Mal
        uhr["plus"] = 4 * 60                         # nach 4 min sind die ersten beiden fertig
        for u in list(attrappe.urls):
            attrappe.tore[u].set()
        assert _warten(lambda: len(attrappe.urls) == 4 and attrappe.laufend == 2)
        uhr["plus"] = 8 * 60                         # zwei warten seit 8 min, die Plätze arbeiten seit 4
        app.queue_heilen()
        threading.Event().wait(0.3)
        wartende = [it for it in app.Q.items if it["url"] not in attrappe.urls]
        assert len(wartende) == 2 and all(it["status"] == "prueft" for it in wartende),             [it["status"] for it in wartende]
        assert attrappe.hoechstens == 2, f"{attrappe.hoechstens} yt-dlp-Abrufe liefen gleichzeitig"
    finally:
        attrappe.frei.set()
        for tor in attrappe.tore.values():
            tor.set()
        for f in faeden:
            f.join(20)
    assert attrappe.hoechstens == 2
    assert sorted(attrappe.urls) == [_url(i) for i in range(6)]
    assert all(it["status"] == "wartend" for it in app.Q.items), [it["status"] for it in app.Q.items]


def _stellbare_uhr(monkeypatch):
    """time.time der App plus `uhr["plus"]` Sekunden."""
    echt = app.time.time
    uhr = {"plus": 0}
    monkeypatch.setattr(app.time, "time", lambda: echt() + uhr["plus"])
    return uhr


def _stand(url):
    return next((it["status"] for it in app.Q.items if it["url"] == url), None)


def test_zwei_haengende_abrufe_sperren_neue_links_nicht_aus(monkeypatch):
    """Zwei Auflösungen hängen (eine Verbindung, die nie antwortet). Die
    Heilung reiht ihre Einträge nach 5 min wieder ein, ihr Faden steckt aber
    weiter in yt-dlp. Vorher hielten sie damit beide Plätze für immer, und
    jeder weitere Link (Addon, SyncFindus, Handy, Oberfläche) stand für immer
    auf „prueft“: genau der Fall, für den es die Heilung gibt."""
    attrappe = _aufloesen_vorbereiten(monkeypatch)
    for i in (2, 3):
        attrappe.tore[_url(i)] = threading.Event()
        attrappe.tore[_url(i)].set()                 # nur die ersten beiden hängen
    uhr = _stellbare_uhr(monkeypatch)
    faeden = [_im_faden(app.aufloesen, _url(i), "beste") for i in (0, 1)]
    try:
        assert _warten(lambda: attrappe.laufend == 2)
        faeden.append(_im_faden(app.aufloesen, _url(2), "beste"))
        assert _warten(lambda: _stand(_url(2)) == "prueft")
        app.queue_heilen()
        uhr["plus"] = 6 * 60
        app.queue_heilen()
        assert _stand(_url(0)) == _stand(_url(1)) == "wartend", "die Heilung reiht die Hänger ein"
        assert _warten(lambda: _stand(_url(2)) == "wartend"), \
            f"nach 6 min steht der dritte Link noch auf prueft: {[(u[-4:], _stand(u)) for u in map(_url, range(3))]}"
        # Ein Link, der danach kommt, wird gleich geprüft, nicht erst nach der nächsten Heilung.
        faeden.append(_im_faden(app.aufloesen, _url(3), "beste"))
        assert _warten(lambda: _stand(_url(3)) == "wartend", s=5), "ein neuer Link wartet auf die Hänger"
    finally:
        attrappe.frei.set()
        for f in faeden:
            f.join(20)
    assert sorted(attrappe.urls) == [_url(i) for i in range(4)], "jeder Link fragt YouTube genau einmal"


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


def test_spaete_sperre_beim_aufloesen_wird_auch_nach_der_uebernahme_vermerkt(monkeypatch):
    """F3 lässt einen übernommenen Eintrag in Ruhe. Der Fehlerzweig kehrte dabei
    aber schon vor dem Vermerk zurück: eine Sperre aus einem späten Auflösen
    schaltete den Schutzschalter nicht ein und fehlte im Fehlerkanal."""
    def antwort(url):
        raise Exception(BOT)
    attrappe = _aufloesen_vorbereiten(monkeypatch, antwort)
    gemeldet = []
    monkeypatch.setattr(app, "fehler_merken", lambda url, text, art="", *a, **k: gemeldet.append(art))
    faden = _im_faden(app.aufloesen, _url(1), "beste")
    try:
        assert _warten(lambda: attrappe.laufend == 1)
        platzhalter = app.Q.items[0]
        _sechs_minuten_spaeter_heilen(monkeypatch)
        assert app.Q.naechster() is platzhalter
    finally:
        attrappe.frei.set()
        faden.join(20)
    assert platzhalter["status"] == "laeuft", "der übernommene Eintrag bleibt in Ruhe (F3)"
    assert app.youtube_gesperrt() > 0, "die späte Sperre schaltete den Schutzschalter nicht ein"
    assert any("sperre" in a for a in gemeldet), f"keine Spur im Fehlerkanal: {gemeldet}"


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


# ---------------------------------------------------------------- F4: YouTube-Sperre

BOT = ("ERROR: [youtube] abc: Sign in to confirm you're not a bot. Use --cookies-from-browser "
       "or --cookies for the authentication.")
COOKIE = "ERROR: Could not copy Chrome cookie database."
NETZ = "ERROR: Unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>"


class _YoutubeAttrappe:
    """Statt yt-dlp: jede Anfrage wird mit ihren Cookies notiert und bekommt
    die nächste Antwort aus `antworten` (Text = Ausnahme, dict = Info)."""

    def __init__(self, *antworten):
        self.antworten = list(antworten)
        self.abrufe = []

    def ydl(self, opts):
        import contextlib
        attrappe = self

        class Ydl:
            def extract_info(self, url, download=False):
                attrappe.abrufe.append({"url": url, "cookies": "cookiesfrombrowser" in opts})
                antwort = attrappe.antworten.pop(0) if attrappe.antworten else {"title": "ok"}
                if isinstance(antwort, str):
                    raise Exception(antwort)
                return antwort

        @contextlib.contextmanager
        def cm():
            yield Ydl()
        return cm()


@pytest.fixture
def youtube(monkeypatch):
    """Liefert eine Fabrik: youtube(*antworten) setzt die Attrappe ein. Dazu
    ein Fehlerkanal zum Mitlesen und eine Uhr, die sich vorstellen lässt."""
    fehler = []
    monkeypatch.setattr(app, "fehler_merken", lambda url, text, art="", *a, **k: fehler.append(art))
    monkeypatch.setitem(app.CFG, "cookies_browser", "firefox")

    def setzen(*antworten):
        attrappe = _YoutubeAttrappe(*antworten)
        monkeypatch.setattr(app, "_ydl", attrappe.ydl)
        attrappe.fehler = fehler
        return attrappe
    return setzen


def _uhr_vor(monkeypatch, sekunden):
    echt = app.time.time
    monkeypatch.setattr(app.time, "time", lambda: echt() + sekunden)


def _eintrag(tmp_path, vid="abcdefghijk"):
    datei = tmp_path / f"Titel [{vid}].mp3"
    datei.write_bytes(b"x")
    key = f"{vid}|audio"
    app._geladen[key] = {"pfad": str(datei), "url": f"https://www.youtube.com/watch?v={vid}",
                         "titel": "Titel", "name": datei.name}
    return key


def _nebenweg(art, tmp_path):
    """Die drei Nebenwege, die YouTube außerhalb des Downloads fragen."""
    if art == "abo":
        return lambda: app._abo_flach("https://www.youtube.com/@probe/videos")
    key = _eintrag(tmp_path)
    if art == "anreichern":
        return lambda: app._enrich_eintrag(key, app._geladen[key])
    return lambda: app.untertitel_nachladen(key)


@pytest.mark.parametrize("art", ["abo", "anreichern", "untertitel"])
def test_sperre_behaelt_die_cookies_fragt_nicht_nochmal_und_wird_gemeldet(youtube, tmp_path, art):
    """Vorher warfen die drei Nebenwege bei jeder Ausnahme die Cookies weg und
    fragten sofort erneut — bei einer Sperre genau der Weg in die nächste."""
    attrappe = youtube(BOT)
    _nebenweg(art, tmp_path)()
    assert len(attrappe.abrufe) == 1, attrappe.abrufe
    assert attrappe.abrufe[0]["cookies"] is True
    assert any("sperre" in a for a in attrappe.fehler), f"keine Spur im Fehlerkanal: {attrappe.fehler}"


@pytest.mark.parametrize("art", ["abo", "anreichern", "untertitel"])
def test_cookie_fehler_versucht_es_weiter_ohne_cookies(youtube, tmp_path, art):
    attrappe = youtube(COOKIE, {"title": "Titel", "uploader": "Kanal", "entries": []})
    _nebenweg(art, tmp_path)()
    assert [a["cookies"] for a in attrappe.abrufe] == [True, False]


@pytest.mark.parametrize("art", ["abo", "anreichern", "untertitel"])
def test_netzfehler_ohne_zweitversuch(youtube, tmp_path, art):
    """Plan F4, „Kleine Änderung“ (Befundbericht Abschnitt 3; kein eigener
    JB-Entscheid, in Abschnitt 7a nicht enthalten, als Frage an JB offen):
    ohne Cookies hilft bei einem Netzfehler nicht, der Zweitversuch kostete
    nur einen weiteren Abruf."""
    attrappe = youtube(NETZ)
    _nebenweg(art, tmp_path)()
    assert len(attrappe.abrufe) == 1


def test_nach_einer_sperre_pausieren_die_serien_schleifen_eine_halbe_stunde(youtube, tmp_path, monkeypatch):
    monkeypatch.setattr(app.time, "sleep", lambda s: None)       # die 0,4-s-Pausen der Schleife
    attrappe = youtube(BOT)
    for i in range(3):
        _eintrag(tmp_path, f"vid{i:08d}")
    _abo_anlegen()
    app.biblio_enrich_alle()                         # erster Abruf: Sperre, die anderen warten
    assert len(attrappe.abrufe) == 1, f"{len(attrappe.abrufe)} Abrufe trotz Sperre"
    app.abos_pruefen()
    assert app.entdecken("").get("fehler"), "Entdecken muss die Pause melden"
    assert len(attrappe.abrufe) == 1, "Abo-Prüfung oder Entdecken fragten trotz Sperre"
    _uhr_vor(monkeypatch, 31 * 60)
    app.abos_pruefen()
    assert len(attrappe.abrufe) == 2, "nach der Pause muss es weitergehen"


def test_eine_sperre_beim_aufloesen_pausiert_die_nebenwege(youtube, tmp_path):
    attrappe = youtube(BOT)
    _abo_anlegen()
    app.aufloesen("https://www.youtube.com/watch?v=abcdefghijk", "beste")
    assert app.Q.items[0]["status"] == "fehler"
    app.abos_pruefen()
    assert len(attrappe.abrufe) == 1, "die Abo-Prüfung fragte gleich nach der Sperre wieder"


def test_entdecken_fragt_nach_einer_sperre_keine_weiteren_seeds(youtube, tmp_path):
    """Fünf Seeds, höchstens drei laufen zugleich: wer nach der ersten Sperre
    an die Reihe kommt, fragt nicht mehr."""
    attrappe = youtube(*[BOT] * 5)
    for i in range(5):
        key = _eintrag(tmp_path, f"seed{i:07d}")
        app._geladen[key]["uploader"] = f"Kanal {i}"
    app.entdecken("", seeds=5)
    assert 1 <= len(attrappe.abrufe) <= 3, f"{len(attrappe.abrufe)} Seeds fragten trotz Sperre"


# ---------------------------------------------------------------- F4 Nacharbeit: die Pause gilt den Serien

def _folgen_info(n=5):
    return {"title": "Probe", "entries": [{"id": f"alt{i:08d}", "title": f"Folge {i}"} for i in range(n)]}


def _eingereiht(monkeypatch):
    """abos_pruefen reiht über aufloesen ein: hier wird nur mitgeschrieben."""
    urls = []
    monkeypatch.setattr(app, "aufloesen", lambda url, *a, **k: urls.append(url))
    return urls


def _in_der_sperrpause(monkeypatch):
    monkeypatch.setattr(app, "_youtube_gesperrt_bis", app.time.time() + 10 * 60)


def _abo_anlegen(bekannt=()):
    abo = {"id": "abcd1234", "url": "https://www.youtube.com/@probe/videos", "name": "Probe",
           "qualitaet": app.CFG["standard_qualitaet"], "bekannt": list(bekannt), "ts": 0, "neu": 0,
           "feed": ""}
    app._abos.append(abo)
    return abo


def test_abo_anlage_in_der_sperrpause_fragt_youtube_und_reiht_danach_nichts_altes_ein(youtube, monkeypatch):
    """Die Pause übersprang auch JBs einzelne Abo-Anlage: das Abo bekam ohne
    einen einzigen Abruf eine leere Baseline und trotzdem die Antwort „ok“.
    Nach der Pause hielt abos_pruefen jede Folge des Kanals für neu (bis 60)."""
    eingereiht = _eingereiht(monkeypatch)
    _in_der_sperrpause(monkeypatch)
    attrappe = youtube(_folgen_info(), _folgen_info())
    antwort = app.abo_aktion({"art": "create", "url": "https://www.youtube.com/@probe"})
    assert antwort.get("ok") and antwort.get("basis") == 5, (antwort, attrappe.abrufe)
    _uhr_vor(monkeypatch, 31 * 60)
    app.abos_pruefen()
    assert eingereiht == [], f"{len(eingereiht)} alte Folgen wurden eingereiht"


def test_abo_anlage_ohne_antwort_von_youtube_holt_die_baseline_nach_statt_alles_zu_laden(youtube, monkeypatch):
    """Scheitert der Erst-Blick der Anlage (Sperre oder Netz), speicherte
    abo_aktion eine leere Baseline, und der nächste Puls lud den ganzen Kanal."""
    eingereiht = _eingereiht(monkeypatch)
    attrappe = youtube(BOT, BOT)                     # bei der Anlage sperrt YouTube
    assert app.abo_aktion({"art": "create", "url": "https://www.youtube.com/@probe"}).get("ok")
    attrappe.antworten[:] = [_folgen_info() for _ in range(3)]   # nach der Pause antwortet es
    _uhr_vor(monkeypatch, 31 * 60)
    app.abos_pruefen()
    app.abos_pruefen()                               # und beim Puls danach
    assert eingereiht == [], f"{len(eingereiht)} alte Folgen wurden eingereiht"
    assert app._abos[0]["bekannt"] == [f"alt{i:08d}" for i in range(5)], "die Baseline fehlt weiter"


@pytest.mark.parametrize("art", ["kanal_info", "abo_folgen", "untertitel"])
def test_einzelaktionen_fragen_auch_in_der_sperrpause(youtube, tmp_path, monkeypatch, art):
    """Die Pause gilt den Serien-Schleifen. Was JB einzeln anstößt, fragt
    YouTube weiter; vorher meldete es „nicht erreichbar“ oder tat still nichts."""
    _in_der_sperrpause(monkeypatch)
    attrappe = youtube(_folgen_info())
    if art == "kanal_info":
        assert app.kanal_info("https://www.youtube.com/@probe").get("ok")
    elif art == "abo_folgen":
        assert app.abo_folgen(_abo_anlegen()["id"], aktualisieren=True).get("ok")
    else:
        app.untertitel_nachladen(_eintrag(tmp_path))
    assert len(attrappe.abrufe) == 1, attrappe.abrufe


# ---------------------------------------------------------------- F6: Bibliotheks-DB

def _grosse_bibliothek(n=3000):
    for i in range(n):
        app._geladen[f"alt{i:08d}|beste"] = {"name": f"Titel {i} [alt{i:08d}].mp4", "titel": "T" * 40,
                                             "groesse": 1000 + i, "ts": 1_700_000_000 + i,
                                             "kategorie": "Video", "uploader": "Kanal"}


def _download_fertig(tmp_path, i):
    """Wie der Worker nach einem fertigen Download: die Datei ist da, der
    Eintrag kommt in die Bibliothek (geladen_merken)."""
    vid = f"neu{i:08d}"
    datei = tmp_path / f"Neu {i} [{vid}].bin"
    datei.write_bytes(b"x" * 10)
    app.geladen_merken({"datei": str(datei), "url": f"https://www.youtube.com/watch?v={vid}",
                        "qualitaet": "beste", "titel": f"Neu {i}"})


def test_bibliothek_speichern_waehrend_downloads_eintragen(tmp_path):
    """Vorher trug geladen_merken ohne Sperre ein, während ein anderer Faden
    die Bibliothek schrieb (json.dump läuft dabei über das lebende Dict):
    „dictionary changed size during iteration“, und ein fertiger Download
    galt als Fehlschlag."""
    _grosse_bibliothek()
    herz_key = "alt00000000|beste"
    start = threading.Barrier(3)
    fehler = []

    def herz():
        start.wait()
        for _ in range(30):
            try:
                app.herz_umschalten(herz_key)
            except Exception as e:                   # noqa: BLE001
                fehler.append("herz: " + repr(e))

    def downloads():
        start.wait()
        for i in range(150):
            try:
                _download_fertig(tmp_path, i)
            except Exception as e:                   # noqa: BLE001
                fehler.append("download: " + repr(e))

    def statistik():
        start.wait()
        for _ in range(300):
            try:
                app.db_statistik()
                app.addon_hab("neu00000001")
            except Exception as e:                   # noqa: BLE001
                fehler.append("lesen: " + repr(e))

    _faeden([herz, downloads, statistik])
    assert not fehler, f"{len(fehler)} Fehler, etwa {fehler[0]}"
    assert sum(1 for k in app._geladen if k.startswith("neu")) == 150
    with open(app.GELADEN_PFAD, encoding="utf-8") as f:
        auf_platte = json.load(f)
    assert auf_platte == json.loads(json.dumps(app._geladen)), "die Platte trägt einen älteren Stand"


# ---------------------------------------------------------------- F7: keine Sperre über Ordnerlauf und Senden

class _LangsamerClient(io.BytesIO):
    """Ein Gerät im WLAN, das die Antwort nur langsam abnimmt: jedes write
    wartet am Tor `frei`."""

    def __init__(self):
        super().__init__()
        self.schreibt = threading.Event()
        self.frei = threading.Event()

    def write(self, b):
        self.schreibt.set()
        self.frei.wait(20)
        return super().write(b)


def _handler(pfad="/", wfile=None):
    h = object.__new__(app.Handler)
    h.path, h.command, h.request_version = pfad, "GET", "HTTP/1.1"
    h.requestline = f"GET {pfad} HTTP/1.1"
    h.client_address = ("127.0.0.1", 50000)
    h.headers = email.message.Message()
    h.rfile, h.wfile = io.BytesIO(b""), wfile or io.BytesIO()
    h.close_connection = False
    return h


def _im_faden(ziel, *args):
    f = threading.Thread(target=ziel, args=args, daemon=True)
    f.start()
    return f


def _kommt_durch(ziel, *args, s=3):
    """Läuft `ziel` in höchstens `s` Sekunden durch?"""
    f = _im_faden(ziel, *args)
    f.join(s)
    return not f.is_alive()


def _langsam_abrufen(pfad):
    client = _LangsamerClient()
    faden = _im_faden(_handler(pfad, client).do_GET)
    assert client.schreibt.wait(10), "die Antwort kam nie beim Senden an"
    return client, faden


def test_langsamer_client_beim_status_haelt_die_worker_nicht_auf():
    app.Q.neu("https://www.youtube.com/watch?v=aaaaaaaaaaa", "eins", "beste")
    client, faden = _langsam_abrufen("/api/status")
    try:
        assert _kommt_durch(app.Q.naechster), "der Worker wartet, bis ein langsamer Client fertig liest"
    finally:
        client.frei.set()
        faden.join(20)


@pytest.mark.parametrize("pfad", ["/api/bibliothek", "/api/playlists", "/api/abos"])
def test_langsamer_client_haelt_weder_download_noch_playlist_auf(tmp_path, monkeypatch, pfad):
    monkeypatch.setattr(app, "_auto_import_anstossen", lambda *a, **k: None)
    _download_fertig(tmp_path, 0)
    client, faden = _langsam_abrufen(pfad)
    try:
        assert _kommt_durch(_download_fertig, tmp_path, 1), \
            "ein fertiger Download wartet auf einen langsamen Client"
        assert _kommt_durch(app.playlist_aktion, {"art": "create", "name": "Neu"}), \
            "eine neue Playlist wartet auf einen langsamen Client"
    finally:
        client.frei.set()
        faden.join(20)


def test_ordnerlauf_der_bibliothek_haelt_keinen_download_auf(tmp_path, monkeypatch):
    """Der Datei-Index läuft durch den ganzen Download-Ordner (os.walk); auf
    einem großen oder schlafenden Laufwerk dauert das. Hier hält ein Tor ihn an."""
    monkeypatch.setattr(app, "_auto_import_anstossen", lambda *a, **k: None)
    _download_fertig(tmp_path, 0)
    im_lauf, weiter = threading.Event(), threading.Event()

    def langsamer_index():
        im_lauf.set()
        weiter.wait(20)
        return {}
    monkeypatch.setattr(app, "_datei_index", langsamer_index)
    faden = _im_faden(_handler("/api/bibliothek").do_GET)
    try:
        assert im_lauf.wait(10)
        assert _kommt_durch(_download_fertig, tmp_path, 1), \
            "ein fertiger Download wartet auf den Ordnerlauf der Bibliothek"
    finally:
        weiter.set()
        faden.join(20)


def test_langsame_dateisuche_beim_aufloesen_haelt_die_worker_nicht_auf(tmp_path, monkeypatch):
    """Beim Einreihen einer Playlist sucht schon_geladen jede bekannte Folge
    auf der Platte (rekursives glob über den Download-Ordner)."""
    for i in range(3):
        app._geladen[f"folge{i:06d}|beste"] = {"name": f"Folge {i}.mp4", "pfad": ""}
    app.Q.neu("https://www.youtube.com/watch?v=bbbbbbbbbbb", "wartet schon", "beste")
    in_suche, weiter = threading.Event(), threading.Event()

    def langsame_suche(url, e):
        in_suche.set()
        weiter.wait(20)
        return None
    monkeypatch.setattr(app, "_finde_datei", langsame_suche)
    antwort = {"_type": "playlist", "title": "Liste",
               "entries": [{"id": f"folge{i:06d}", "title": f"Folge {i}",
                            "url": f"https://www.youtube.com/watch?v=folge{i:06d}"} for i in range(3)]}
    attrappe = _aufloesen_vorbereiten(monkeypatch, lambda url: antwort)
    attrappe.frei.set()
    faden = _im_faden(app.aufloesen, "https://www.youtube.com/playlist?list=PLabc", "beste", True)
    try:
        assert in_suche.wait(10)
        assert _kommt_durch(app.Q.naechster), "der Worker wartet auf die Dateisuche des Auflösens"
    finally:
        weiter.set()
        faden.join(20)
    assert sum(1 for it in app.Q.items if "folge" in it["url"]) == 3


def test_explorer_start_haelt_weder_worker_noch_bibliothek_auf(tmp_path, monkeypatch):
    """„Im Ordner zeigen“ startet den Explorer; das darf keine Sperre halten."""
    offen, weiter = threading.Event(), threading.Event()

    def langsamer_explorer(pfad=None):
        offen.set()
        weiter.wait(20)
    monkeypatch.setattr(app, "ordner_zeigen", langsamer_explorer)
    it = app.Q.neu("https://www.youtube.com/watch?v=ccccccccccc", "fertig", "beste")
    app.Q.neu("https://www.youtube.com/watch?v=ddddddddddd", "wartet", "beste")
    _download_fertig(tmp_path, 0)
    h = _handler()
    faden = _im_faden(h._action, {"art": "ordner", "id": it["id"]})
    try:
        assert offen.wait(10)
        assert _kommt_durch(app.Q.naechster), "der Worker wartet auf den Explorer"
    finally:
        weiter.set()
        faden.join(20)
    offen.clear()
    weiter.clear()
    faden = _im_faden(h._biblio, {"art": "ordner", "id": "neu00000000|beste"})
    try:
        assert offen.wait(10)
        assert _kommt_durch(_download_fertig, tmp_path, 1), "ein Download wartet auf den Explorer"
    finally:
        weiter.set()
        faden.join(20)


def test_extern_abspielen_sucht_die_datei_ohne_sperre(tmp_path, monkeypatch):
    """„Extern abspielen“ sucht eine verschobene Datei per Ordnerlauf und
    startet VLC oder den Standardplayer; beides lief unter _io_lock."""
    monkeypatch.setattr(app, "_auto_import_anstossen", lambda *a, **k: None)
    gestartet = []
    monkeypatch.setattr(app, "extern_abspielen", gestartet.append)
    _download_fertig(tmp_path, 0)
    key = "neu00000000|beste"
    datei = app._geladen[key]["pfad"]
    app._geladen[key]["pfad"] = str(tmp_path / "verschoben.bin")   # Datei liegt woanders
    im_lauf, weiter = threading.Event(), threading.Event()

    def langsamer_index():
        im_lauf.set()
        weiter.wait(20)
        return {"neu00000000": [datei]}
    monkeypatch.setattr(app, "_datei_index", langsamer_index)
    faden = _im_faden(_handler()._biblio, {"art": "extern", "id": key})
    try:
        assert im_lauf.wait(10)
        assert _kommt_durch(_download_fertig, tmp_path, 1),             "ein fertiger Download wartet auf den Ordnerlauf von „extern abspielen“"
    finally:
        weiter.set()
        faden.join(20)
    assert gestartet == [datei], "der Player muss die gefundene Datei bekommen"


def test_loeschen_haelt_downloads_nicht_auf_und_laesst_einen_neuen_eintrag_stehen(tmp_path, monkeypatch):
    """Die Papierkorb-Bewegung lief unter _io_lock: ein langsamer Papierkorb
    (großes Video, Netzlaufwerk) hielt jeden fertigen Download an."""
    monkeypatch.setattr(app, "_auto_import_anstossen", lambda *a, **k: None)
    _download_fertig(tmp_path, 0)
    key = "neu00000000|beste"
    pl = {"id": "pl000001", "name": "Liste", "items": [key], "ts": 0}
    app._playlists.append(pl)
    bewegt, im_lauf, weiter = [], threading.Event(), threading.Event()

    def langsamer_papierkorb(pfad):
        bewegt.append(pfad)
        im_lauf.set()
        weiter.wait(20)
        return "papierkorb"
    monkeypatch.setattr(app, "_rueckholbar_entfernen", langsamer_papierkorb)
    alt = app._geladen[key]
    faden = _im_faden(_handler()._biblio, {"art": "loeschen", "id": key})
    try:
        assert im_lauf.wait(10)
        assert _kommt_durch(_download_fertig, tmp_path, 1), "ein fertiger Download wartet auf den Papierkorb"
        assert _kommt_durch(_download_fertig, tmp_path, 0), "derselbe Titel, frisch geladen, wartet"
    finally:
        weiter.set()
        faden.join(20)
    assert bewegt == [alt["pfad"]]
    assert key in app._geladen and app._geladen[key] is not alt, "der frische Eintrag ging verloren"
    assert "neu00000001|beste" in app._geladen
    assert pl["items"] == [], "der gelöschte Titel steht noch in der Playlist"


# ---------------------------------------------------------------- F8: Auto-Tag holt nach

def _musik(*titel):
    keys = []
    for i, t in enumerate(titel):
        k = f"musik{i:06d}|audio"
        app._geladen[k] = {"titel": t, "kategorie": "MP3", "name": f"{t}.mp3", "pfad": ""}
        keys.append(k)
    return keys


def _musicbrainz_mit_tor(monkeypatch):
    """Statt MusicBrainz: jede Suche wird notiert und wartet am Tor `frei`."""
    gesucht, frei, erste = [], threading.Event(), threading.Event()

    def mb_suche(ku, ti, timeout=10, live_hinweis=None):
        gesucht.append(ti)
        erste.set()
        frei.wait(20)
        return None
    monkeypatch.setattr(app, "_mb_suche", mb_suche)
    monkeypatch.setattr(app, "_itunes_suche", lambda *a, **k: None)
    monkeypatch.setattr(musik_einstufung, "_tag_kandidat", lambda e: ("Kanal", e.get("titel", "")))
    monkeypatch.setattr(app.time, "sleep", lambda s: None)
    return gesucht, frei, erste


def test_autotag_holt_titel_nach_die_waehrend_eines_laufs_fertig_werden(monkeypatch):
    """Vorher verwarf autotag_lauf den Auftrag still, wenn schon ein Lauf lief:
    ein zweiter Download, der während des Taggens fertig wurde, blieb ungetaggt
    (nachgeholt nur über den Voll-Lauf-Knopf)."""
    eins, zwei = _musik("Erstes Lied", "Zweites Lied")
    gesucht, frei, erste = _musicbrainz_mit_tor(monkeypatch)
    lauf = _im_faden(app.autotag_lauf, [eins])
    try:
        assert erste.wait(10)
        app.autotag_lauf([zwei])                     # der zweite Download ist fertig
    finally:
        frei.set()
        lauf.join(20)
    assert _warten(lambda: not app._autotag["laeuft"])
    assert "Zweites Lied" in gesucht, f"der zweite Titel wurde nie getaggt: {gesucht}"


def test_autotag_holt_auch_einen_angefragten_voll_lauf_nach(monkeypatch):
    eins, zwei = _musik("Erstes Lied", "Zweites Lied")
    gesucht, frei, erste = _musicbrainz_mit_tor(monkeypatch)
    lauf = _im_faden(app.autotag_lauf, [eins])
    try:
        assert erste.wait(10)
        app.autotag_lauf()                           # JB drückt „alle taggen“
    finally:
        frei.set()
        lauf.join(20)
    assert _warten(lambda: not app._autotag["laeuft"])
    assert "Zweites Lied" in gesucht, f"der Voll-Lauf ging verloren: {gesucht}"


def test_autotag_wiederholt_einen_voll_lauf_nicht_fuer_einen_zweiten_voll_klick(monkeypatch):
    """Ein Voll-Klick während eines Voll-Laufs ist schon abgedeckt: der Lauf
    nimmt alles, was ohne Album ist, und was danach fertig wird, kommt als
    Schlüssel nach. Nachgeholt wird ein Voll-Lauf nur hinter einem
    Schlüssel-Lauf (sonst sucht jeder weiter unauffindbare Titel noch einmal
    bei MusicBrainz, je 1,5 bis 3 s)."""
    _musik("Erstes Lied", "Zweites Lied")
    gesucht, frei, erste = _musicbrainz_mit_tor(monkeypatch)
    lauf = _im_faden(app.autotag_lauf)               # „alle taggen“
    try:
        assert erste.wait(10)
        app.autotag_lauf()                           # derselbe Knopf noch einmal
    finally:
        frei.set()
        lauf.join(20)
    assert _warten(lambda: not app._autotag["laeuft"])
    assert sorted(gesucht) == ["Erstes Lied", "Zweites Lied"], f"der Voll-Lauf lief doppelt: {gesucht}"


def test_autotag_gibt_den_merker_am_ende_nur_einmal_frei(monkeypatch):
    """autotag_lauf setzte den Merker am Ende zweimal zurück: unter der Sperre
    vor dem return und danach im finally noch einmal. Startete genau dazwischen
    ein neuer Lauf, verlor er seinen Merker, und ein dritter Anstoß lief
    parallel: zwei Läufe fragten MusicBrainz gleichzeitig (Regel: höchstens
    eine Anfrage pro Sekunde)."""
    k1, k2, k3 = _musik("Erstes Lied", "Zweites Lied", "Drittes Lied")
    zaehler_lock, aktiv, gesucht, frei = threading.Lock(), [0, 0], [], threading.Event()

    def mb_suche(ku, ti, timeout=10, live_hinweis=None):
        with zaehler_lock:
            aktiv[0] += 1
            aktiv[1] = max(aktiv[1], aktiv[0])
            gesucht.append(ti)
        try:
            if ti != "Erstes Lied":
                frei.wait(20)
            return None
        finally:
            with zaehler_lock:
                aktiv[0] -= 1
    monkeypatch.setattr(app, "_mb_suche", mb_suche)
    monkeypatch.setattr(app, "_itunes_suche", lambda *a, **k: None)
    monkeypatch.setattr(musik_einstufung, "_tag_kandidat", lambda e: ("Kanal", e.get("titel", "")))
    monkeypatch.setattr(app.time, "sleep", lambda s: None)
    lauf_a = threading.Thread(target=app.autotag_lauf, args=([k1],), daemon=True)
    haelt, weiter = threading.Event(), threading.Event()
    echt = app._autotag_lock

    class Sperre:
        """Hält Lauf A an, wenn er nach getaner Arbeit und schon freigegebenem
        Merker noch einmal nach der Sperre greift."""
        def __enter__(self):
            if (threading.current_thread() is lauf_a and "Erstes Lied" in gesucht
                    and not app._autotag["laeuft"] and not haelt.is_set()):
                haelt.set()
                weiter.wait(20)
            return echt.__enter__()

        def __exit__(self, *a):
            return echt.__exit__(*a)
    monkeypatch.setattr(app, "_autotag_lock", Sperre())
    lauf_a.start()
    faeden = [lauf_a]
    try:
        assert _warten(lambda: haelt.is_set() or not lauf_a.is_alive())
        faeden.append(_im_faden(app.autotag_lauf, [k2]))       # Lauf B startet genau jetzt
        assert _warten(lambda: "Zweites Lied" in gesucht)
        weiter.set()
        lauf_a.join(10)
        faeden.append(_im_faden(app.autotag_lauf, [k3]))       # Anstoß C, während B läuft
        _warten(lambda: "Drittes Lied" in gesucht or not faeden[-1].is_alive())
        parallel = aktiv[1]
    finally:
        weiter.set()
        frei.set()
        for f in faeden:
            f.join(20)
    assert parallel == 1, f"{parallel} Auto-Tag-Läufe fragten MusicBrainz gleichzeitig"
    assert _warten(lambda: not app._autotag["laeuft"])
    assert "Drittes Lied" in gesucht, "C wurde weder nachgeholt noch gestartet"


# ---------------------------------------------------------------- Läuft-schon-Merker

def _merker_zeilen():
    """Zeilen der App, die einen Merker „laeuft“ auf True setzen, am Syntaxbaum
    gefunden statt am Zeilentext: eine Zuweisung von True an `…laeuft`,
    `x.laeuft` oder `x["laeuft"]`, dazu `x.update({"laeuft": True, …})`. Eine
    Antwort wie `return {"ok": True, "laeuft": True}` setzt nichts und zählt
    nicht mit."""
    import ast
    with open(app.__file__, encoding="utf-8") as f:
        baum = ast.parse(f.read())

    def ist_true(knoten):
        return isinstance(knoten, ast.Constant) and knoten.value is True

    def ist_merker(ziel):
        if isinstance(ziel, ast.Name):
            return "laeuft" in ziel.id
        if isinstance(ziel, ast.Attribute):
            return "laeuft" in ziel.attr
        return (isinstance(ziel, ast.Subscript) and isinstance(ziel.slice, ast.Constant)
                and ziel.slice.value == "laeuft")

    def setzt_im_dict(aufruf):
        return (isinstance(aufruf.func, ast.Attribute) and aufruf.func.attr == "update"
                and any(isinstance(d, ast.Dict) and any(
                    isinstance(k, ast.Constant) and k.value == "laeuft" and ist_true(v)
                    for k, v in zip(d.keys, d.values)) for d in aufruf.args))
    zeilen = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Assign) and ist_true(knoten.value) and any(map(ist_merker, knoten.targets)):
            zeilen.add(knoten.lineno)
        elif isinstance(knoten, ast.Call) and setzt_im_dict(knoten):
            zeilen.add(knoten.lineno)
    return zeilen


def _unguenstigste_verzahnung(n, treffer):
    """threading.settrace-Spur: jeder Faden hält an einer Zeile an, die einen
    Merker „laeuft“ auf True setzt (`_merker_zeilen`), bis alle n dort sind
    (höchstens 0,5 s). So läuft jedes Mal die Verzahnung, in der alle zwischen
    Prüfen und Setzen stehen; ein Merker unter Sperre lässt dort nur einen hin.
    Jeder Halt landet in `treffer`: greift der Haltepunkt nicht mehr (etwa weil
    der Merker anders gesetzt wird), scheitert der Test laut, statt still ohne
    erzwungene Verzahnung grün zu bleiben."""
    schranke = threading.Barrier(n, timeout=0.5)
    datei = app.__file__
    zeilen = _merker_zeilen()

    def spur(frame, ereignis, arg):
        if ereignis == "call":
            return spur if frame.f_code.co_filename == datei else None
        if ereignis == "line" and frame.f_lineno in zeilen:
            treffer.append(frame.f_lineno)
            try:
                schranke.wait()
            except threading.BrokenBarrierError:
                pass
        return spur
    return spur


def _zaehlt_und_wartet(zaehler, frei, ergebnis=None):
    def arbeit(*a, **k):
        zaehler.append(1)
        frei.wait(20)
        return ergebnis
    return arbeit


def _lauf_vorbereiten(art, monkeypatch, tmp_path, zaehler, frei):
    arbeit = _zaehlt_und_wartet(zaehler, frei, {})
    if art == "technik":
        monkeypatch.setattr(app, "_datei_index", arbeit)
        return app.technik_backfill
    if art == "metadaten":
        monkeypatch.setattr(app, "_ffmpeg_exe", lambda: "ffmpeg.exe")
        monkeypatch.setattr(app, "_datei_index", arbeit)
        return app.metadaten_backfill
    if art == "einsortieren":
        monkeypatch.setitem(app.CFG, "unterordner", True)
        monkeypatch.setattr(app, "_id_karten", arbeit)
        return app.downloads_einsortieren
    if art == "anreichern":
        app._geladen["ohnekanal01|beste"] = {"titel": "Ohne Kanal"}
        monkeypatch.setattr(app, "_enrich_eintrag", _zaehlt_und_wartet(zaehler, frei, False))
        return app.biblio_enrich_alle
    if art == "autotag":
        keys = _musik("Ein Lied")
        monkeypatch.setattr(app, "_mb_suche", _zaehlt_und_wartet(zaehler, frei))
        monkeypatch.setattr(app, "_itunes_suche", lambda *a, **k: None)
        monkeypatch.setattr(musik_einstufung, "_tag_kandidat", lambda e: ("Kanal", e.get("titel", "")))
        return lambda: app.autotag_lauf(keys)
    # Geo-Test: der Knopf startet den Test in einem eigenen Faden
    monkeypatch.setattr(app, "_geo_test", {"laeuft": False, "stand": 0.0, "url": "", "titel": "",
                                           "info": "", "ergebnisse": []})
    monkeypatch.setattr(app, "geo_test_lauf", arbeit)
    h = _handler()
    return lambda: h._geo_test_start({"url": "https://www.youtube.com/watch?v=geogesperrt", "laender": ["GB"]})


@pytest.mark.parametrize("art", ["technik", "metadaten", "einsortieren", "anreichern", "autotag", "geotest"])
def test_gleichzeitige_anstoesse_starten_genau_einen_lauf(monkeypatch, tmp_path, art):
    """Sechs „läuft schon“-Merker standen ohne Sperre da: Prüfen und Setzen
    waren zwei Schritte, und zwei Anstöße im selben Augenblick liefen beide los
    (zwei ffmpeg-Läufe auf dieselbe Datei, doppelte MusicBrainz-Anfragen)."""
    monkeypatch.setattr(app.time, "sleep", lambda s: None)
    zaehler, frei = [], threading.Event()
    anstoss = _lauf_vorbereiten(art, monkeypatch, tmp_path, zaehler, frei)
    treffer = []
    threading.settrace(_unguenstigste_verzahnung(8, treffer))
    try:
        faeden = [_im_faden(anstoss) for _ in range(8)]
    finally:
        threading.settrace(None)
    try:
        assert _warten(lambda: len(zaehler) >= 1)
        threading.Event().wait(0.8)                  # alle übrigen hatten Zeit, loszulaufen
        gestartet = len(zaehler)
    finally:
        frei.set()
        for f in faeden:
            f.join(20)
    assert treffer, "der Haltepunkt am Merker griff nie: die ungünstigste Verzahnung wurde nicht erzwungen"
    assert gestartet == 1, f"{gestartet} Läufe liefen gleichzeitig los"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


# ------------------------------------------ _json_laden: Sperre ist kein Defekt (Gruppe 6d)
# Hielt ein anderes Programm die Datei kurz exklusiv offen (Virenscanner,
# Sicherung, das Dashboard), warf das Öffnen PermissionError [WinError 32].
# _json_laden hielt das für einen Defekt: Rettungskopie versucht und die leere
# Vorgabe zurückgegeben, die das nächste Speichern über die echte Datei
# schrieb. Jetzt liest es bei einem Sperr-Fehler kurz erneut.

def _exklusiv_sperren(pfad):
    """Die Datei so öffnen, wie es ein fremdes Programm tut: ohne Freigabe
    (dwShareMode 0). Jeder andere Zugriff scheitert mit WinError 32."""
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.CreateFileW(str(pfad), 0x80000000, 0, None, 3, 0x80, None)   # GENERIC_READ, OPEN_EXISTING
    assert h and h != wintypes.HANDLE(-1).value, ctypes.get_last_error()
    return lambda: k32.CloseHandle(h)


def test_json_laden_wartet_eine_kurze_sperre_ab(tmp_path):
    pfad = tmp_path / "geladen_log.json"
    pfad.write_text('{"k|beste": {"name": "echt.mp4"}}', encoding="utf-8")
    freigeben = _exklusiv_sperren(pfad)
    with pytest.raises(PermissionError):
        open(pfad, encoding="utf-8").close()          # die Sperre wirkt wirklich
    t = threading.Timer(0.3, freigeben)
    t.start()
    try:
        daten = app._json_laden(str(pfad), {})
    finally:
        t.join()
    assert daten == {"k|beste": {"name": "echt.mp4"}}, "eine kurze Sperre galt als Defekt"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["geladen_log.json"], "Rettungskopie trotz Sperre"


def test_json_laden_gibt_eine_dauersperre_nach_kurzem_warten_auf(tmp_path):
    pfad = tmp_path / "geladen_log.json"
    pfad.write_text("{}", encoding="utf-8")
    freigeben = _exklusiv_sperren(pfad)
    try:
        start = time.monotonic()
        assert app._json_laden(str(pfad), {"vorgabe": 1}) == {"vorgabe": 1}
        assert time.monotonic() - start < 3, "das Warten ist begrenzt"
    finally:
        freigeben()
    assert pfad.read_text(encoding="utf-8") == "{}", "die gesperrte Datei bleibt, wie sie ist"


def test_json_laden_legt_eine_kaputte_datei_ohne_warten_beiseite(tmp_path):
    pfad = tmp_path / "geladen_log.json"
    pfad.write_text("{kaputt", encoding="utf-8")
    start = time.monotonic()
    assert app._json_laden(str(pfad), {}) == {}
    assert time.monotonic() - start < 0.5
    assert any(p.name.endswith(".defekt") for p in tmp_path.iterdir())


# Befund der Abnahme 25.09.2026: test_aufloesen_hoechstens_zwei_… fiel in einer
# vollen Suite unter Last einmal durch und war danach 7 von 7 grün. Die Plätze des
# Auflösens sind Modul-Zustand; ein Faden eines früheren Tests, der unter Last
# noch in seinem Platz steckt, nahm dem nächsten Test einen der zwei Plätze weg.
# Jeder Test bekommt deshalb frische Plätze (conftest). Die zwei Tests hier
# belegen das in fester Reihenfolge: der erste lässt einen Platz belegt zurück.
_liegengelassen = {}


def test_plaetze_a_ein_test_laesst_einen_platz_belegt_zurueck():
    plaetze = app._aufloese_plaetze
    drin, raus = threading.Event(), threading.Event()

    def halten():
        with plaetze.platz():
            drin.set()
            raus.wait(30)

    threading.Thread(target=halten, daemon=True).start()
    assert drin.wait(5)
    _liegengelassen["plaetze"] = plaetze
    _liegengelassen["raus"] = raus


def test_plaetze_b_der_naechste_test_hat_beide_plaetze_frei():
    try:
        assert app._aufloese_plaetze is not _liegengelassen.get("plaetze"), \
            "die Plätze des Auflösens werden zwischen den Tests nicht erneuert"
        assert app._aufloese_plaetze._inhaber == {}
        assert app._prueft_wartet == set()
    finally:
        if "raus" in _liegengelassen:
            _liegengelassen["raus"].set()
