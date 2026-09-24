# -*- coding: utf-8 -*-
"""Wachen, die für JEDEN SyncYouTube-Test gelten.

Firefox-Profil (24.09.2026): Jeder YoutubeDL-Aufbau in youtube_app.py sucht vor
dem Start die Cookie-Datenbank des Browsers (`cookie_kopie`). Ohne diese Wache
läse schon ein Test mit einer yt-dlp-Attrappe JBs echtes Firefox-Profil und
kopierte seine Cookies ins Temp. Deshalb zeigt die Suche in jedem Test auf
einen Ort, an dem kein Profil liegt; wer eine Firefox-Welt braucht, legt sie in
`tmp_path` an und setzt `cookie_kopie.WURZELN` selbst (monkeypatch).
`tests/test_cookies_wal.py::test_i_die_wache_steht_in_jedem_test` prüft das.
"""
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import cookie_kopie  # noqa: E402

KEIN_PROFIL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "__kein_firefox_profil__")


@pytest.fixture(autouse=True)
def _kein_echtes_firefox_profil(monkeypatch):
    monkeypatch.setattr(cookie_kopie, "WURZELN", [KEIN_PROFIL])
