# -*- coding: utf-8 -*-
"""Die Wachen aus tests/conftest.py gelten in JEDEM Modul (Prüfung Runde 2).

Dieses Modul fordert für die Wachen nichts an und hat keine eigene: was hier
greift, greift überall. Jeder Test hält dazu auch den Rot-Lauf von JBs echten
Orten fern (APPDATA zeigt in tmp_path) — ohne Wache träfe er sonst genau das,
wovor die Wache schützen soll.
"""
import os
import subprocess
import sys
import textwrap

import pytest

HIER = os.path.dirname(os.path.abspath(__file__))
MODUL_DIR = os.path.dirname(HIER)
for _pfad in (MODUL_DIR, HIER):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

from yt_dlp import cookies as yc  # noqa: E402

import windows_kennung as wk  # noqa: E402


def _fremde_orte(monkeypatch, tmp_path):
    """APPDATA/LOCALAPPDATA in tmp_path: der Rot-Lauf erreicht nie JBs Profil
    oder Startmenü (beide Suchen hängen an diesen Variablen)."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))


# Der Faden stirbt am gewollten Alarm; pytest meldet das sonst als Warnung.
@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_startmenue_wache_gilt_ueberall_und_schlaegt_laut_an(request, monkeypatch, tmp_path):
    """Vorher stand die Wache nur in test_windows_kennung.py, und ihr
    AssertionError landete im `except Exception` von startmenue_eintrag: das
    Ergebnis hieß "fehler", der Test blieb grün. Ein künftiger Test, der
    youtube_app.main() ruft, hätte JBs echtes Startmenü beschrieben. Jetzt:
    in jedem Modul gesperrt, und der Zugriff scheitert laut — auch im
    Hintergrundfaden (dort meldet es die Wache am Testende)."""
    _fremde_orte(monkeypatch, tmp_path)
    (tmp_path / "appdata" / "Microsoft" / "Windows" / "Start Menu" / "Programs").mkdir(parents=True)
    with pytest.raises(pytest.fail.Exception):
        wk.startmenue_eintrag()
    zugriffe = request.getfixturevalue("_kein_echtes_startmenue")
    assert zugriffe == ["startmenue_ordner"]
    faden = wk.startmenue_eintrag(faden=True)             # der Weg aus youtube_app.main()
    faden.join(30)
    assert zugriffe == ["startmenue_ordner"] * 2, "der Zugriff im Faden blieb unbemerkt"
    assert not list((tmp_path / "appdata").rglob("*.lnk")), "trotz Wache geschrieben"
    zugriffe.clear()                                       # der Alarm war hier gewollt


def test_zugriff_im_faden_macht_den_test_rot_auch_ohne_eigene_pruefung(tmp_path):
    """Der Startmenü-Eintrag entsteht im Betrieb im Hintergrundfaden
    (startmenue_eintrag(faden=True) in youtube_app.main()). Dort stirbt nur der
    Faden am Alarm — pytest machte daraus bloß eine Warnung. Die Wache meldet
    darum jeden Zugriff am Testende noch einmal. Geprüft in einem Kindlauf,
    dessen einziger Test NICHTS selbst prüft: er muss trotzdem rot enden."""
    probe = tmp_path / "test_probe_faden.py"
    probe.write_text(textwrap.dedent('''
        import pytest
        import windows_kennung as wk

        @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
        def test_zugriff_nur_im_faden(monkeypatch, tmp_path):
            monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
            wk.startmenue_eintrag(faden=True).join(30)
        '''), encoding="utf-8")
    lauf = subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "-q", "-p", "no:cacheprovider", "-p", "conftest",
         "--rootdir", str(tmp_path), "--basetemp", str(tmp_path / "kind")],
        cwd=str(tmp_path), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, env=dict(os.environ, PYTHONPATH=HIER, PYTHONIOENCODING="utf-8"))
    aus = lauf.stdout + lauf.stderr
    assert lauf.returncode != 0 and "echtes Startmenü" in aus, aus[-2000:]
    assert "1 passed, 1 error" in aus, aus[-2000:]


def test_firefox_wache_deckt_auch_yt_dlps_eigene_suche(monkeypatch, tmp_path):
    """Im Rückfallweg bekommt yt-dlp `("firefox",)` und sucht die Profile selbst
    (`_firefox_browser_dirs`, über APPDATA/LOCALAPPDATA). Die Wache bog nur
    `cookie_kopie.WURZELN` um: ein Test mit echtem YoutubeDL hätte JBs Profil
    gelesen. Hier liegt ein Profil genau dort, wo yt-dlp ohne Wache sucht."""
    _fremde_orte(monkeypatch, tmp_path)
    profil = tmp_path / "appdata" / "Mozilla" / "Firefox" / "Profiles" / "probe.default"
    profil.mkdir(parents=True)
    (profil / "cookies.sqlite").write_bytes(b"")
    orte = [os.path.abspath(p) for p in yc._firefox_browser_dirs()]
    assert not any(p.startswith(str(tmp_path)) for p in orte), (
        f"yt-dlps eigene Profilsuche ist nicht umgebogen: {orte}")
    assert yc._newest(yc._firefox_cookie_dbs(list(yc._firefox_browser_dirs()))) is None
    import conftest
    assert conftest.ECHTE_FIREFOX_SUCHE is not yc._firefox_browser_dirs
    assert any(p.startswith(str(tmp_path))
               for p in map(os.path.abspath, conftest.ECHTE_FIREFOX_SUCHE())), (
        "ECHTE_FIREFOX_SUCHE ist nicht mehr yt-dlps echte Suche")


def test_film_wache_sperrt_schluesselbund_und_netz(request, tmp_path):
    """Prüfung Runde 3: Nach dem frühen youtube_app-Import zeigte `filme` für
    jeden Test ohne eigenes einrichten() auf JBs echte filme_*.json, und
    `_zugang`/`_meta_keys`/`_seerr_url` lasen seinen echten Schlüsselbund
    (nachgemessen: vier Tests lasen den echten TMDB-Schlüssel). Jetzt zeigen die
    Film-Pfade in tmp_path, und jeder Zugriff auf Schlüsselbund oder Netz
    scheitert laut — auch an `except Exception` vorbei (pytest.fail)."""
    import filme
    zugriffe = request.getfixturevalue("_film_pfade_im_tmp")
    assert all(p.startswith(str(tmp_path)) for p in filme._pfade.values()), filme._pfade
    for name, args in (("_zugang", ()), ("_meta_keys", ()), ("_seerr_url", ()),
                       ("_http", ("https://jelly.example/Items",)),
                       ("_seerr_http", ("https://seerr.example/api/v1/search",))):
        with pytest.raises(pytest.fail.Exception):
            getattr(filme, name)(*args)
    assert zugriffe == ["_zugang", "_meta_keys", "_seerr_url", "_http", "_seerr_http"], zugriffe
    # Der echte Weg durch filme: _jellyfin_ruf fängt `except Exception` — die
    # Sperre kommt trotzdem durch (vorher wäre das ein stiller Netzfehler).
    zugriffe.clear()
    filme._sitzung.clear()
    filme._anmelde_sperre_ts = filme._merkmal_ruhe_ts = 0.0
    with pytest.raises(pytest.fail.Exception):
        filme.fortschritt("f1", 100)
    assert zugriffe == ["_zugang"], zugriffe
    zugriffe.clear()                                       # der Alarm war hier gewollt


def test_film_zugriff_im_faden_macht_den_test_rot(tmp_path):
    """Der Hüllen-Rückfall meldet in einem Hintergrundfaden (und wartet dort
    auf die Seite). Stirbt nur der Faden an der Sperre, machte pytest daraus
    bloß eine Warnung — die Wache meldet den Zugriff darum am Testende noch
    einmal. Geprüft in einem Kindlauf, dessen einziger Test nichts selbst prüft:
    er muss trotzdem rot enden."""
    probe = tmp_path / "test_probe_film_faden.py"
    probe.write_text(textwrap.dedent('''
        import threading
        import pytest
        import filme

        @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
        def test_meldung_nur_im_faden():
            f = threading.Thread(target=lambda: filme.fortschritt("f1", 100))
            f.start()
            f.join(30)
        '''), encoding="utf-8")
    lauf = subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "-q", "-p", "no:cacheprovider", "-p", "conftest",
         "--rootdir", str(tmp_path), "--basetemp", str(tmp_path / "kind")],
        cwd=str(tmp_path), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, env=dict(os.environ, PYTHONPATH=HIER, PYTHONIOENCODING="utf-8"))
    aus = lauf.stdout + lauf.stderr
    assert lauf.returncode != 0 and "Schlüsselbund bzw. Netz des Film-Teils" in aus, aus[-2000:]
    assert "1 passed, 1 error" in aus, aus[-2000:]


def test_film_wache_ueberlebt_das_neuladen_von_filme(tmp_path):
    """test_filme lädt `filme` neu („Zustand überlebt den Neustart"); das
    definiert die echten Funktionen neu. Im vollen Lauf sperrte danach
    `_seerr_url` nicht mehr (gefunden am 25.09.). Die Wache setzt ihre Sperren
    darum vor und nach jedem Test wieder ein. Geprüft in einem Kindlauf: ein
    Test lädt neu, der nächste findet alle Sperren wieder vor — geprüft am
    Zustand, ohne die Funktionen aufzurufen (kein Weg zum echten Schlüsselbund)."""
    probe = tmp_path / "test_probe_film_neuladen.py"
    probe.write_text(textwrap.dedent('''
        import importlib
        import conftest
        import filme

        def test_a_laedt_neu():
            importlib.reload(filme)

        def test_b_findet_alle_sperren():
            offen = [n for n in conftest.FILM_SPERREN
                     if getattr(getattr(filme, n), "film_sperre", None) != n]
            assert not offen, f"nach dem Neuladen ungesperrt: {offen}"
        '''), encoding="utf-8")
    lauf = subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "-q", "-p", "no:cacheprovider", "-p", "conftest",
         "--rootdir", str(tmp_path), "--basetemp", str(tmp_path / "kind")],
        cwd=str(tmp_path), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, env=dict(os.environ, PYTHONPATH=HIER, PYTHONIOENCODING="utf-8"))
    aus = lauf.stdout + lauf.stderr
    assert lauf.returncode == 0 and "2 passed" in aus, aus[-2000:]
