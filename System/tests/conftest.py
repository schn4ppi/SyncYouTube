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

Film-Teil, Schlüsselbund und Netz (Prüfung Runde 3): Nach dem frühen Import
zeigte `filme` für jeden Test ohne eigenes `einrichten(tmp_path)` auf JBs echte
filme_*.json. `filme._zugang` und `filme._meta_keys` lesen JBs echten
Windows-Schlüsselbund, `filme._http` geht ins Netz (Renés Server; die 403-Drossel
trifft auch SyncFindus). Nachgemessen am 25.09.: vier Tests lasen so JBs echten
TMDB-Schlüssel und reichten ihn an ihre Attrappe — nur die verhinderte den
Netzruf. Jetzt bekommt jeder Test eigene Film-Pfade in `tmp_path`, und
Schlüsselbund und Netz sind für die GANZE Sitzung gesperrt — auch für
Hintergrundfäden, die ihren Test überleben (der Hüllen-Rückfall wartet in
einem Faden). Ein Zugriff scheitert laut (pytest.fail) und wird am Testende
noch einmal gemeldet. Wer Jellyfin oder Schlüssel braucht, setzt seine
Attrappe wie bisher selbst (monkeypatch); danach gilt wieder die Sperre.

`tests/test_wachen.py` prüft die Wachen, `test_cookies_wal.py::test_i` die
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
import filme  # noqa: E402
import windows_kennung  # noqa: E402  (Import schreibt nichts)
import youtube_app  # noqa: E402,F401  (früh: sein filme.einrichten läuft nie nach dem eines Tests)

FILM_SPERREN = ("_zugang", "_meta_keys", "_seerr_url",   # Schlüsselbund (Jellyfin, TMDB/OMDb, Seerr)
                "_http", "_seerr_http")                 # Netz (Jellyfin + Metadaten, Seerr)
_FILM_ZUGRIFFE = []

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


def _film_sperre(name):
    def gesperrt(*_a, **_k):
        _FILM_ZUGRIFFE.append(name)
        pytest.fail(f"Test griff auf filme.{name} zu (JBs Schlüsselbund bzw. das Netz) — "
                    "Attrappe per monkeypatch setzen", pytrace=False)
    gesperrt.film_sperre = name
    return gesperrt


def _film_sperren_setzen():
    """Jede Sperre, die fehlt, wieder einsetzen. Ein `importlib.reload(filme)`
    (test_filme, „Zustand überlebt den Neustart") definiert die echten
    Funktionen neu — ohne das hier liefe der Rest der Sitzung ungesperrt."""
    for n in FILM_SPERREN:
        if getattr(getattr(filme, n, None), "film_sperre", None) != n:
            setattr(filme, n, _film_sperre(n))


@pytest.fixture(scope="session", autouse=True)
def _film_schluessel_und_netz_gesperrt():
    """Für die GANZE Sitzung: ein Hintergrundfaden, der seinen Test überlebt
    (Warten auf die Seite, Nachreichen), trifft nach dem Zurücksetzen des
    Test-monkeypatch wieder die Sperre, nie das Echte."""
    echt = {n: getattr(filme, n) for n in FILM_SPERREN}
    _film_sperren_setzen()
    yield
    for n, f in echt.items():
        setattr(filme, n, f)


@pytest.fixture(autouse=True)
def _film_pfade_im_tmp(tmp_path):
    """Eigene Film-Pfade je Test; liefert die Liste der gesperrten Zugriffe
    (ein Test, der den Alarm selbst prüft, leert sie). Setzt die Sperren vor
    und nach jedem Test neu (s. _film_sperren_setzen)."""
    _film_sperren_setzen()
    alt = dict(filme._pfade)
    filme.einrichten(str(tmp_path))
    yield _FILM_ZUGRIFFE
    filme._pfade.clear()
    filme._pfade.update(alt)
    _film_sperren_setzen()
    if _FILM_ZUGRIFFE:
        n = list(_FILM_ZUGRIFFE)
        _FILM_ZUGRIFFE.clear()
        pytest.fail(f"Test griff auf Schlüsselbund bzw. Netz des Film-Teils zu ({n}, "
                    "auch im Hintergrundfaden)", pytrace=False)
