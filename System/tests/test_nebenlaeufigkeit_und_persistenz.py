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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
