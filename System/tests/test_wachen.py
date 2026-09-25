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


# ---------------------------------------------------------------- Daten-Wache und Netz (Y0, 25.09.2026)
#
# Vorher zeigte youtube_app in JEDEM Test auf den System-Ordner (ohne
# --testmodus ist DATEN_DIR = SCRIPT_DIR): Konfiguration, Warteschlange,
# Bibliothek, Playlists, Abos, Protokolle, und ziel_ordner() auf den echten
# Downloads-Ordner. Geschützt hat nur Handarbeit (19× `_json_speichern =`).
# Gemessen am 25.09. mit einem Schreib-Protokoll über den vollen Lauf:
# test_abbruch_greift_auch_beim_zusammenfuegen schrieb warteschlange.json und
# yt_status.json in den System-Ordner, acht Tests legten Downloads\ an.

PROGRAMM = os.path.dirname(MODUL_DIR)       # System\ und Downloads\: im Betrieb JBs echte Daten
# Einen Ordner, den es nie gibt: Ohne Wache scheitert jeder Schreibversuch
# hierhin an FileNotFoundError, es entsteht also auch im Rot-Lauf nichts.
PROBE = os.path.join(MODUL_DIR, "__wache_probe__")


def _kindlauf(probe, tmp_path, **env):
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(probe), "-q", "-p", "no:cacheprovider", "-p", "conftest",
         "--rootdir", str(tmp_path), "--basetemp", str(tmp_path / "kind")],
        cwd=str(tmp_path), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, env=dict(os.environ, PYTHONPATH=HIER, PYTHONIOENCODING="utf-8", **env))


def test_daten_pfade_der_app_zeigen_in_tmp_path(tmp_path):
    """Am Ergebnis geprüft, nicht an einer Liste: KEIN Modul-Pfad der App zeigt
    mehr in den Programmordner, außer den beiden Code-Orten. Ein neuer
    `X_PFAD = os.path.join(DATEN_DIR, …)` fällt damit ohne Nachtrag auf."""
    import live_tv
    import profil_geraete
    import youtube_app as app
    wurzel = os.path.normcase(PROGRAMM) + os.sep
    echt = sorted(n for n, v in vars(app).items()
                  if isinstance(v, str) and not n.startswith("__") and n not in ("SCRIPT_DIR", "BIN_DIR")
                  and os.path.isabs(v) and (os.path.normcase(v) + os.sep).startswith(wurzel))
    assert not echt, f"Diese App-Pfade zeigen in den echten Programmordner: {echt}"
    tmp = os.path.normcase(str(tmp_path))
    for pfad in (app.DATEN_DIR, app.CONFIG_PFAD, app.QUEUE_PFAD, app.GELADEN_PFAD,
                 app.ABO_INDEX_ORDNER, app.FEHLER_LOG, app.ziel_ordner(),
                 profil_geraete._pfade["profile"], live_tv._pfade["cache"]):
        assert os.path.normcase(pfad).startswith(tmp), f"nicht in tmp_path: {pfad}"


def test_zustand_der_app_ist_je_test_frisch(tmp_path):
    """Q, CFG, Bibliothek, Playlists, Abos, Lyrics und Listen-Log wurden beim
    Import aus JBs Dateien geladen und von allen Tests geteilt: was ein Test
    hineinschrieb, sah der nächste. Kindlauf: der erste Test füllt alles, der
    zweite muss leere Zustände sehen, auch in den Vorgabe-Listen von CFG."""
    probe = tmp_path / "test_probe_zustand.py"
    probe.write_text(textwrap.dedent('''
        import youtube_app as app

        def test_a_fuellt_alles():
            app.Q.items.append({"id": "probe", "status": "wartend"})
            app.CFG["ziel_ordner"] = "X:/gibt/es/nicht"
            app.CFG["geo_proxies"].append("probe")
            for name in ("_geladen", "_lyrics", "_listen_log"):
                getattr(app, name)["probe"] = 1
            app._playlists.append({"id": "probe"})
            app._abos.append({"id": "probe"})

        def test_b_sieht_nichts_davon():
            assert app.Q.items == []
            assert app.CFG["ziel_ordner"] == "" and app.CFG["geo_proxies"] == []
            assert app.STANDARD_CONFIG["geo_proxies"] == []
            assert (app._geladen, app._lyrics, app._listen_log) == ({}, {}, {})
            assert (app._playlists, app._abos) == ([], [])
        '''), encoding="utf-8")
    lauf = _kindlauf(probe, tmp_path)
    aus = lauf.stdout + lauf.stderr
    assert lauf.returncode == 0 and "2 passed" in aus, aus[-2000:]


def test_schreiben_in_den_programmordner_scheitert_laut(request, tmp_path):
    """Jeder Weg in den Programmordner scheitert laut, auch an `except OSError`
    vorbei (pytest.fail erbt von BaseException). Dabei die Falle aus dem
    Familien-Lehrbuch: `os.makedirs(…, exist_ok=True)` verschluckt eine Sperre,
    die als OSError kommt, wenn der Ordner schon existiert."""
    import conftest
    import youtube_app as app
    quelle = tmp_path / "q.json"
    quelle.write_text("{}", encoding="utf-8")
    for weg in (lambda: open(os.path.join(PROBE, "config.json"), "w", encoding="utf-8"),
                lambda: os.replace(str(quelle), os.path.join(PROBE, "warteschlange.json")),
                lambda: os.makedirs(MODUL_DIR, exist_ok=True)):
        with pytest.raises(pytest.fail.Exception):
            weg()
    assert quelle.exists(), "die Quelle ist trotz Sperre weg"
    # Papierkorb (ctypes, kein Audit-Ereignis): eigene Sperre am Aufrufpunkt.
    # Erst nach dem Beweis oben gerufen, damit der Rot-Lauf nie Windows fragt.
    assert getattr(app._in_papierkorb, "daten_wache", False), "_in_papierkorb ist ungesperrt"
    with pytest.raises(pytest.fail.Exception):
        app._in_papierkorb(os.path.join(PROBE, "titel.mp3"))
    # Die Entscheidung selbst: Code-Ort, Downloads, bin-Ziel geschützt;
    # tmp_path, __pycache__ und .pytest_cache frei.
    bin_ziel = os.path.realpath(os.path.join(MODUL_DIR, "bin"))
    for pfad, gesperrt in ((os.path.join(MODUL_DIR, "config.json"), True),
                           (os.path.join(PROGRAMM, "Downloads", "titel.mp3"), True),
                           (os.path.join(bin_ziel, "deno.exe"), True),
                           (str(tmp_path / "x.json"), False),
                           (os.path.join(MODUL_DIR, "__pycache__", "x.pyc"), False),
                           (os.path.join(MODUL_DIR, "tests", "__pycache__", "x.pyc"), False),
                           (os.path.join(MODUL_DIR, ".pytest_cache", "v", "x"), False)):
        assert conftest.geschuetzt(pfad) is gesperrt, pfad
    zugriffe = request.getfixturevalue("_daten_wache")
    assert len(zugriffe) == 4 and all("Programmordner" in z for z in zugriffe), zugriffe
    zugriffe.clear()                                       # der Alarm war hier gewollt


def test_schreiben_im_faden_macht_den_test_rot(tmp_path):
    """Ein Hintergrundfaden, der ins echte Datenverzeichnis schreibt, stirbt nur
    selbst am Alarm, pytest machte daraus bloß eine Warnung. Die Wache meldet
    jeden Versuch darum am Testende noch einmal. Der Kindlauf schützt zusätzlich
    einen Ordner in tmp_path, der den Programmordner spielt: selbst ohne Wache
    landete die Datei also nie in einem echten Ordner."""
    echt = tmp_path / "echt"
    echt.mkdir()
    probe = tmp_path / "test_probe_schreiben.py"
    probe.write_text(textwrap.dedent(f'''
        import threading
        import pytest

        @pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
        def test_schreibt_nur_im_faden():
            f = threading.Thread(target=lambda: open({str(echt / "config.json")!r}, "w").close())
            f.start()
            f.join(30)
        '''), encoding="utf-8")
    lauf = _kindlauf(probe, tmp_path, SYNCYT_WACHE_ZUSATZ=str(echt))
    aus = lauf.stdout + lauf.stderr
    assert not (echt / "config.json").exists(), "trotz Wache geschrieben"
    assert lauf.returncode != 0 and "echten Programmordner" in aus, aus[-2000:]
    assert "1 passed, 1 error" in aus, aus[-2000:]


def test_netz_ist_fuer_live_tv_geo_vpn_und_update_gesperrt(request):
    """Vorher sperrte die conftest nur das Netz des Film-Teils. live_tv,
    geo.freie_proxys, vpn (NordVPN-Status und das Umschalten der Verbindung)
    und update gingen ohne Attrappe ins echte Netz. Jetzt: benannte Sperren
    wie bei filme, dazu ein allgemeiner Riegel für jede Verbindung nach
    draußen (live_tv hat keine eigene Netz-Funktion, es ruft urlopen direkt).
    Die Reihenfolge ist Absicht: erst der Riegel am Ereignis (ohne jeden
    Netzverkehr), dann erst echte Aufrufe. Fehlt der Riegel, endet der Test
    vorher, und der Rot-Lauf geht nie ins Netz."""
    import conftest
    import live_tv
    for ereignis, args in (("socket.connect", (None, ("192.0.2.1", 443))),
                           ("urllib.Request", ("https://example.invalid/liste.m3u", None, {}, "GET")),
                           ("subprocess.Popen", (r"C:\Program Files\NordVPN\NordVPN.exe",
                                                 ["NordVPN.exe", "-d"], None, None))):
        with pytest.raises(pytest.fail.Exception):
            sys.audit(ereignis, *args)
    sys.audit("socket.connect", None, ("127.0.0.1", 8790))      # lokal bleibt erlaubt
    offen = [f"{m.__name__}.{n}" for m, n in conftest.NETZ_SPERREN
             if getattr(getattr(m, n), "netz_sperre", None) != n]
    assert not offen, f"ungesperrt: {offen}"
    for modul, name in conftest.NETZ_SPERREN:
        with pytest.raises(pytest.fail.Exception):
            getattr(modul, name)()
    with pytest.raises(pytest.fail.Exception):
        live_tv.kanaele(frisch=True)
    zugriffe = request.getfixturevalue("_daten_wache")
    assert len(zugriffe) == 3 + len(conftest.NETZ_SPERREN) + 1, zugriffe
    assert any("raw.githubusercontent.com" in z for z in zugriffe), zugriffe
    zugriffe.clear()                                       # der Alarm war hier gewollt
