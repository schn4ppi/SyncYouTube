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
