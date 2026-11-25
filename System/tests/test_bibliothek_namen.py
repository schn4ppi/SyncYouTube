# -*- coding: utf-8 -*-
"""Namens-Baukasten: Format-Klammern entfernen, Aufnahme-Zusätze erhalten.

Kein Netz und keine echten Mediendateien; die Daten-Wache in conftest.py
isoliert die App, der Probelauf benutzt ausschließlich tmp_path.
"""
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402


@pytest.mark.parametrize(("roh", "sauber"), [
    ("Toto - Africa (Official HD Video)", "Toto - Africa"),
    ("Survivor - Eye Of The Tiger (Official HD Video)", "Survivor - Eye Of The Tiger"),
    ("Prince - Purple Rain [Official Music Video HD]", "Prince - Purple Rain"),
    ("Prince - Purple Rain (Official 4K Video)", "Prince - Purple Rain"),
    ("Prince - Purple Rain (Full HD Video)", "Prince - Purple Rain"),
    ("Fleetwood Mac - Landslide (Live) (Official HD Video)", "Fleetwood Mac - Landslide (Live)"),
    ("Rick Astley - Never Gonna Give You Up (Official HD Video) (4K Remaster)",
     "Rick Astley - Never Gonna Give You Up (4K Remaster)"),
    ("Prince - Purple Rain (Video Mix)", "Prince - Purple Rain (Video Mix)"),
    ("Prince - Purple Rain (4K Remaster)", "Prince - Purple Rain (4K Remaster)"),
])
def test_namen_formatklammern_ohne_aufnahmedaten_verlust(roh, sauber):
    assert app._dateiname_bauen({"titel": roh}, schema=app.NAME_STANDARD) == sauber


def test_namen_probelauf_bereinigt_hd_video_ohne_umbenennen(tmp_path, monkeypatch):
    datei = tmp_path / "Toto - Africa (Official HD Video).mp4"
    datei.write_bytes(b"nur eine isolierte Probe")
    eintrag = {"titel": datei.stem, "name": datei.name,
               "pfad": str(datei), "fp": "vorhandenes-sicherheitsnetz", "importiert": True}
    monkeypatch.setattr(app, "_geladen", {"lokal-probe|lokal": eintrag})

    plan = app.migration_probelauf(schema=app.NAME_STANDARD)

    assert len(plan) == 1
    assert plan[0]["alt"] == str(datei)
    assert plan[0]["neu"] == str(tmp_path / "Toto - Africa.mp4")
    assert plan[0]["konflikt"] == ""
    assert datei.read_bytes() == b"nur eine isolierte Probe"
    assert not (tmp_path / "Toto - Africa.mp4").exists()
    assert eintrag["pfad"] == str(datei)
