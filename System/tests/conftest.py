# -*- coding: utf-8 -*-
"""Wachen, die für JEDEN SyncYouTube-Test gelten.

Firefox-Profil (24.09.2026): Jeder YoutubeDL-Aufbau in youtube_app.py sucht vor
dem Start die Cookie-Datenbank des Browsers (`cookie_kopie`). Ohne diese Wache
läse schon ein Test mit einer yt-dlp-Attrappe JBs echtes Firefox-Profil und
kopierte seine Cookies ins Temp. Deshalb zeigt die Suche in jedem Test auf
einen Ort, an dem kein Profil liegt; wer eine Firefox-Welt braucht, legt sie in
`tmp_path` an und setzt `cookie_kopie.WURZELN` selbst (monkeypatch).
Prüfung Runde 2: auch yt-dlps EIGENE Profilsuche (`_firefox_browser_dirs`, der
Rückfallweg mit `("firefox",)`) zeigt dorthin — vorher nur `cookie_kopie`. Wer
die echte Suche braucht (eine Welt in tmp_path über APPDATA), nimmt sie
bewusst zurück: `ECHTE_FIREFOX_SUCHE` (so die Fixture `welt`).

Startmenü (Prüfung Runde 2): `windows_kennung.startmenue_ordner` ist in jedem
Test gesperrt — vorher nur in test_windows_kennung.py, und ein Test, der
youtube_app.main() ruft, hätte JBs echtes Startmenü beschrieben. Der Zugriff
scheitert LAUT: pytest.fail erbt von BaseException (das `except Exception` in
startmenue_eintrag schluckte den alten AssertionError), und weil der Eintrag
im Betrieb im Hintergrundfaden entsteht, meldet die Wache jeden Zugriff am
Testende noch einmal.

Film-Pfade (Prüfung Runde 2, Nebenfund): youtube_app ruft beim IMPORT
`filme.einrichten(DATEN_DIR)` — ohne --testmodus ist das der System-Ordner mit JBs
echten Film-Dateien. Importierte erst ein Test das Modul (lazy, nach seinem
eigenen `filme.einrichten(tmp_path)`), zeigte der Film-Teil danach auf die
Produktion: `pytest tests/test_jellyfin_zugang.py -k zustand_route` allein las
JBs filme_zustand.json und wurde rot. Im vollen Lauf fiel es nicht auf, weil
ein anderes Modul youtube_app schon beim Sammeln importierte. Darum hier, vor
jedem Test.

`tests/test_wachen.py` prüft beide Wachen, `test_cookies_wal.py::test_i` die
Firefox-Wache gegen die echte Suche.
"""
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

from yt_dlp import cookies as _yt_dlp_cookies  # noqa: E402

import cookie_kopie  # noqa: E402
import windows_kennung  # noqa: E402  (Import schreibt nichts)
import youtube_app  # noqa: E402,F401  (früh: sein filme.einrichten läuft nie nach dem eines Tests)

KEIN_PROFIL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "__kein_firefox_profil__")
ECHTE_FIREFOX_SUCHE = _yt_dlp_cookies._firefox_browser_dirs


@pytest.fixture(autouse=True)
def _kein_echtes_firefox_profil(monkeypatch):
    monkeypatch.setattr(cookie_kopie, "WURZELN", [KEIN_PROFIL])
    monkeypatch.setattr(_yt_dlp_cookies, "_firefox_browser_dirs", lambda: [KEIN_PROFIL])


@pytest.fixture(autouse=True)
def _kein_echtes_startmenue(monkeypatch):
    """Liefert die Liste der Zugriffe (ein Test, der den Alarm selbst prüft, leert sie)."""
    zugriffe = []

    def gesperrt():
        zugriffe.append("startmenue_ordner")
        pytest.fail("Test griff auf JBs echtes Startmenü zu (windows_kennung.startmenue_ordner)",
                    pytrace=False)
    monkeypatch.setattr(windows_kennung, "startmenue_ordner", gesperrt)
    yield zugriffe
    if zugriffe:
        pytest.fail(f"Test griff auf JBs echtes Startmenü zu ({len(zugriffe)}×, "
                    "auch im Hintergrundfaden)", pytrace=False)
