# -*- coding: utf-8 -*-
"""Protokoll-Datei (Gesamtprüfung Gruppe 7, Plan Abschnitt 6 Punkt 1, 25.09.2026).

Unter pythonw (SyncYouTube.bat, Hülle) und in der exe gibt es keine Konsole:
`_sag` lief dort ins Leere, jeder Ticker-Fehler und jede Meldung des
Selbst-Updates ging verloren. Jetzt schreibt `_sag` zusätzlich in
`yt_protokoll.log` im Datenverzeichnis (logging mit RotatingFileHandler,
höchstens 1 MB, dazu drei Vorgänger). `main()` richtet das als Erstes ein.

Nicht hier gemessen: ein echter Lauf unter pythonw (die Suite startet das
Programm nie); das Verhalten ohne Konsole ist mit `sys.stdout = None`
nachgestellt.
"""
import logging
import os
import subprocess
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402


@pytest.fixture
def protokoll(tmp_path):
    """Protokoll in tmp_path; danach wieder abgemeldet (der Logger ist global)."""
    pfad = tmp_path / "yt_protokoll.log"
    handler = app.protokoll_einrichten(str(pfad))
    yield pfad
    app._protokoll.removeHandler(handler)
    handler.close()


def _zeilen(pfad):
    return pfad.read_text(encoding="utf-8").splitlines()


def test_sag_schreibt_auch_ohne_konsole_ins_protokoll(protokoll, monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)            # wie unter pythonw
    app._sag("Downloads einsortiert: 3 Datei(en) an den richtigen Platz bewegt")
    (zeile,) = _zeilen(protokoll)
    assert zeile.endswith(" INFO Downloads einsortiert: 3 Datei(en) an den richtigen Platz bewegt"), zeile
    assert zeile[:4].isdigit() and zeile[4] == "-", "Zeitstempel vorn"


def test_sag_schreibt_weiter_auf_die_konsole(protokoll, capsys):
    app._sag("Hallo Konsole")
    assert capsys.readouterr().out == "Hallo Konsole\n"
    assert _zeilen(protokoll)[-1].endswith(" INFO Hallo Konsole")


def test_protokoll_ist_gedeckelt(protokoll):
    """Höchstens 1 MB je Datei und drei Vorgänger, das Älteste fällt weg."""
    zeile = "x" * 1000
    for i in range(4600):                               # ~4,6 MB Meldungen
        app._sag(f"{i:05d} {zeile}")
    namen = sorted(p.name for p in protokoll.parent.iterdir())
    assert namen == ["yt_protokoll.log", "yt_protokoll.log.1", "yt_protokoll.log.2", "yt_protokoll.log.3"], namen
    for p in protokoll.parent.iterdir():
        assert p.stat().st_size <= app.PROTOKOLL_GROESSE, (p.name, p.stat().st_size)
    assert "04599 " in _zeilen(protokoll)[-1], "das Neueste steht in der aktuellen Datei"
    alle = "".join(p.read_text(encoding="utf-8") for p in protokoll.parent.iterdir())
    assert "00000 " not in alle, "das Älteste ist weggefallen"


def test_ohne_einrichten_schreibt_sag_keine_datei(tmp_path, capsys):
    """Beim Import (Tests, Werkzeuge) entsteht keine Datei; erst main() richtet
    sie ein. Der Logger meldet sich dann auch nicht über stderr."""
    app._sag("nur Konsole")
    aus = capsys.readouterr()
    assert aus.out == "nur Konsole\n" and aus.err == ""
    assert not any(isinstance(h, logging.FileHandler) for h in app._protokoll.handlers)


def test_sonderwege_schreiben_ins_protokoll_und_in_den_fehlerkanal(protokoll, monkeypatch, tmp_path):
    """_smtc_log und _kennung_log melden Probleme: jetzt auch im Protokoll
    (Stufe WARNING); der Eintrag im Fehlerkanal yt_fehler.jsonl bleibt."""
    kanal = tmp_path / "yt_fehler.jsonl"
    monkeypatch.setattr(app, "FEHLER_LOG", str(kanal))
    app._smtc_log("pywinrt fehlt")
    app._kennung_log("Kennung nicht gesetzt")
    z = _zeilen(protokoll)
    assert z[0].endswith(" WARNING Windows-Medienanmeldung: pywinrt fehlt"), z
    assert z[1].endswith(" WARNING Kennung nicht gesetzt"), z
    kanal_text = kanal.read_text(encoding="utf-8")
    assert '"art": "smtc"' in kanal_text and '"art": "kennung"' in kanal_text


def test_main_richtet_das_protokoll_als_erstes_ein(monkeypatch):
    """Vor allem anderen, damit schon die Windows-Kennung ihre Probleme dort
    ablegen kann. Geprüft ohne echten Start: ein Halt beim Einrichten."""
    class Halt(Exception):
        pass
    kennung = []

    def einrichten(pfad=None):
        raise Halt(pfad)
    monkeypatch.setattr(app, "protokoll_einrichten", einrichten)
    monkeypatch.setattr(app.windows_kennung, "setze_kennung", lambda **kw: kennung.append(kw))
    with pytest.raises(Halt):
        app.main()
    assert kennung == [], "die Kennung lief vor dem Protokoll"


def test_protokoll_liegt_im_datenverzeichnis_und_wird_nie_committet():
    assert os.path.dirname(app.PROTOKOLL_LOG) == app.DATEN_DIR
    wurzel = os.path.dirname(MODUL_DIR)
    if not os.path.isdir(os.path.join(wurzel, ".git")) and not os.path.isfile(os.path.join(wurzel, ".git")):
        pytest.skip("kein git-Arbeitsbaum")
    namen = [f"System/yt_protokoll.log{s}" for s in ("", ".1", ".2", ".3")]
    lauf = subprocess.run(["git", "check-ignore", "--no-index", *namen], cwd=wurzel,
                          capture_output=True, text=True)
    assert sorted(lauf.stdout.split()) == sorted(namen), (lauf.stdout, lauf.stderr)
