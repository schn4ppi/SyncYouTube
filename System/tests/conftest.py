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

Daten-Wache (Gesamtprüfung Y0, 25.09.2026): Ohne --testmodus ist DATEN_DIR
der System-Ordner. Jeder Test sah darum JBs echte Konfiguration,
Warteschlange, Bibliothek, Playlists und Abos, und `ziel_ordner()` zeigte auf
den echten Downloads-Ordner; geschützt hat nur Handarbeit (19×
`_json_speichern =`). Gemessen am 25.09. mit einem Schreib-Protokoll über den
vollen Lauf: ein Test schrieb warteschlange.json und yt_status.json in den
System-Ordner, acht Tests legten Downloads\\ an. Jetzt:
  * Jeder Modul-Pfad der App, der ins Datenverzeichnis oder in den
    Programmordner zeigt, liegt je Test in `tmp_path` (gefunden am Wert, nicht
    an einer Namensliste; nur die Code-Orte SCRIPT_DIR und BIN_DIR bleiben).
    Ebenso `profil_geraete` und `live_tv`.
  * Alles, was die App beim Import aus einer Datei lädt (Q, CFG, Bibliothek,
    Playlists, Abos, Lyrics, Listen-Log; gefunden im Quelltext der App), wird
    je Test frisch aus dem leeren `tmp_path` geladen. CFG als tiefe Kopie:
    `config_laden` teilt sonst die Listen mit STANDARD_CONFIG.
  * Zwischen den Tests zeigt alles in einen Sitzungs-Ordner, damit ein
    Hintergrundfaden, der seinen Test überlebt, nie die echten Pfade erbt.
  * Ein Audit-Hook lässt jeden Schreibversuch in den Programmordner laut
    scheitern (öffnen zum Schreiben, umbenennen, löschen, Ordner anlegen,
    Zeitstempel/Rechte setzen), auch im Ziel der Junction System\\bin.
    Frei bleiben `__pycache__`, `.pytest_cache` sowie basetemp und %TEMP%,
    falls sie im Programmordner liegen. Den Papierkorb (ctypes, ohne
    Audit-Ereignis) sperrt eine Hülle um `youtube_app._in_papierkorb`.
Grenzen: Der Import der App LIEST die echten Dateien weiterhin einmal (nur
lesend; schreiben würde er nur eine defekte Datei beiseite, und das scheitert
jetzt laut). Kindprozesse sieht der Hook nicht. Ein eigener Download-Ordner
aus JBs config.json liegt außerhalb des Programmordners; ihn schützt nur, dass
CFG je Test frisch aus den Vorgaben kommt. Der Direkt-Lauf
`python tests/test_youtube.py` lädt diese Datei nicht und hat keine Wache.

Netz (Y0): benannte Sperren wie beim Film-Teil für geo.freie_proxys,
vpn.status, vpn._still (startet NordVPN.exe) und update.fetch_*. Dazu ein
allgemeiner Riegel im selben Hook: jede Verbindung, jeder urllib-Abruf und
jede Namensauflösung nach draußen scheitert laut (live_tv ruft urlopen direkt
und hat keine eigene Netz-Funktion), ebenso der Start eines VPN-Programms.
Lokale Adressen bleiben erlaubt, ebenso ein UDP-connect (sendet nichts; so
ermittelt `_lan_ip` die eigene Adresse).

`tests/test_wachen.py` prüft die Wachen, `test_cookies_wal.py::test_i` die
Firefox-Wache gegen die echte Suche.
"""
import ast
import copy
import os
import socket
import sys
import tempfile
import urllib.parse

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)
PROGRAMM_DIR = os.path.dirname(MODUL_DIR)      # System\ + Downloads\: im Betrieb JBs Daten


# ---------------------------------------------------------------- Daten-Wache (Audit-Hook)
# Vor dem Import der App eingehängt: auch ein Schreiben beim Import scheitert laut.

def _norm(pfad):
    try:
        pfad = os.fsdecode(os.fspath(pfad))
    except TypeError:
        return None
    return os.path.normcase(os.path.abspath(pfad))


def _unter(pfad, wurzel):
    """Beide normiert (normcase + abspath)."""
    return pfad == wurzel or pfad.startswith(wurzel.rstrip(os.sep) + os.sep)


# Geschützt: der Programmordner und das Ziel der bin-Junction (im Worktree der
# Live-Ordner). SYNCYT_WACHE_ZUSATZ nimmt weitere Orte dazu: so prüft ein
# Kindlauf die Wache an einem Ordner in tmp_path statt an echten Daten.
GESCHUETZT = list(dict.fromkeys(
    _norm(p) for p in [PROGRAMM_DIR, os.path.realpath(PROGRAMM_DIR),
                       os.path.realpath(os.path.join(MODUL_DIR, "bin"))]
    + [z for z in os.environ.get("SYNCYT_WACHE_ZUSATZ", "").split(os.pathsep) if z]))
# Ausnahmen gelten nur, wenn sie IM geschützten Ort liegen; basetemp kommt zu
# Sitzungsbeginn dazu.
_ERLAUBT = [_norm(tempfile.gettempdir())]
_FREIE_ORDNER = {"__pycache__", ".pytest_cache"}


def geschuetzt(pfad):
    """True, wenn ein Test hier nichts verändern darf."""
    p = _norm(pfad)
    if p is None:
        return False
    for w in GESCHUETZT:
        if _unter(p, w):
            if _FREIE_ORDNER & set(p[len(w):].split(os.sep)):
                return False
            return not any(_unter(p, a) and _unter(a, w) for a in _ERLAUBT)
    return False


_WACHE_FUNDE = []
_SCHARF = [True]                                 # pytest_sessionfinish entschärft (Cache, JUnit)
_SCHREIB_MODI = set("wax+")
_SCHREIB_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
_ZIEL_ARGS = {"os.rename": (0, 1), "shutil.move": (0, 1),          # os.replace meldet os.rename
              "os.link": (1,), "os.symlink": (1,), "shutil.copyfile": (1,), "shutil.copytree": (1,),
              "os.remove": (0,), "os.rmdir": (0,), "os.mkdir": (0,), "shutil.rmtree": (0,),
              "os.utime": (0,), "os.chmod": (0,), "os.truncate": (0,)}
_VPN_PROGRAMME = {"nordvpn.exe", "windscribe-cli.exe", "windscribe-cli", "wireguard.exe", "wg.exe"}
_EIGENER_NAME = socket.gethostname().lower()
_BEACHTET = frozenset(_ZIEL_ARGS) | {"open", "socket.connect", "socket.sendto", "socket.getaddrinfo",
                                     "urllib.Request", "subprocess.Popen"}


def _alarm(fund, text):
    _WACHE_FUNDE.append(fund)
    pytest.fail(text, pytrace=False)             # BaseException: kein `except OSError` schluckt das


def _schreib_alarm(ereignis, pfad):
    _alarm(f"Programmordner ({ereignis}): {pfad}",
           f"Test schrieb in den echten Programmordner ({ereignis}: {pfad}) — Pfad in tmp_path legen")


def _netz_alarm(ereignis, ziel):
    _alarm(f"Netz ({ereignis}): {ziel}",
           f"Test ging ins Netz bzw. startete ein VPN-Programm ({ereignis}: {ziel}) — "
           "Attrappe per monkeypatch setzen")


def _lokal(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    host = str(host or "").strip("[]").lower()
    return host in ("", "localhost", "::1", "0:0:0:0:0:0:0:1") or host.startswith("127.")


def _wache(ereignis, args):
    if ereignis not in _BEACHTET or not _SCHARF[0]:
        return
    if ereignis == "open":
        pfad, modus, flags = args
        if isinstance(pfad, int):
            return
        if modus is not None:
            if not _SCHREIB_MODI & set(str(modus)):
                return
        elif not (isinstance(flags, int) and flags & _SCHREIB_FLAGS):
            return
        if geschuetzt(pfad):
            _schreib_alarm(ereignis, pfad)
    elif ereignis in _ZIEL_ARGS:
        for i in _ZIEL_ARGS[ereignis]:
            if i < len(args) and not isinstance(args[i], int) and geschuetzt(args[i]):
                _schreib_alarm(ereignis, args[i])
    elif ereignis in ("socket.connect", "socket.sendto"):
        sock, adresse = args[0], args[-1]
        if ereignis == "socket.connect" and getattr(sock, "type", None) == socket.SOCK_DGRAM:
            return                               # UDP-connect sendet nichts (_lan_ip)
        if isinstance(adresse, tuple) and adresse and not _lokal(adresse[0]):
            _netz_alarm(ereignis, adresse)
    elif ereignis == "socket.getaddrinfo":
        host = args[0]
        if host is not None and not _lokal(host) and str(host).lower() != _EIGENER_NAME:
            _netz_alarm(ereignis, host)
    elif ereignis == "urllib.Request":
        teile = urllib.parse.urlsplit(str(args[0]))
        if teile.scheme not in ("file", "data") and not _lokal(teile.hostname):
            _netz_alarm(ereignis, args[0])
    elif ereignis == "subprocess.Popen":
        programm = args[0] or (args[1][0] if isinstance(args[1], (list, tuple)) and args[1]
                               else str(args[1] or "").split(" ")[0])
        if os.path.basename(os.fsdecode(programm)).strip('"').lower() in _VPN_PROGRAMME:
            _netz_alarm(ereignis, programm)


sys.addaudithook(_wache)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """pytest selbst schreibt danach Cache und Berichte, auch in den Programmordner."""
    _SCHARF[0] = False


from yt_dlp import cookies as _yt_dlp_cookies  # noqa: E402

import cookie_kopie  # noqa: E402
import filme  # noqa: E402
import geo  # noqa: E402
import live_tv  # noqa: E402
import profil_geraete  # noqa: E402
import update  # noqa: E402
import vpn  # noqa: E402
import windows_kennung  # noqa: E402  (Import schreibt nichts)
import youtube_app  # noqa: E402  (früh: sein filme.einrichten läuft nie nach dem eines Tests)

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


# ---------------------------------------------------------------- Netz: benannte Sperren (Y0)

NETZ_SPERREN = ((geo, "freie_proxys"),                           # Gratis-Proxy-Liste (geonode)
                (vpn, "status"), (vpn, "_still"),                # NordVPN-Insights; startet NordVPN.exe
                (update, "fetch_release_json"), (update, "fetch_https"))  # GitHub-Release


def _netz_sperre(modul, name):
    def gesperrt(*_a, **_k):
        _netz_alarm("Sperre", f"{modul.__name__}.{name}")
    gesperrt.netz_sperre = name
    return gesperrt


def _netz_sperren_setzen():
    """Wie beim Film-Teil: jede Sperre, die fehlt (Neuladen, Test ohne
    monkeypatch), wieder einsetzen."""
    for modul, name in NETZ_SPERREN:
        if getattr(getattr(modul, name, None), "netz_sperre", None) != name:
            setattr(modul, name, _netz_sperre(modul, name))


# ---------------------------------------------------------------- Daten der App je Test in tmp_path (Y0)

CODE_ORTE = ("SCRIPT_DIR", "BIN_DIR")            # Code, keine Daten: bleiben am echten Ort
_ECHT_DATEN_DIR = youtube_app.DATEN_DIR
_ECHT_PROGRAMM_DIR = youtube_app.PROGRAMM_DIR


def _echte_app_pfade():
    """Name → Wert jeder Modul-Konstante der App, die ins Datenverzeichnis oder
    in den Programmordner zeigt. Am Wert gefunden: ein neuer
    `X_PFAD = os.path.join(DATEN_DIR, …)` ist ohne Nachtrag mit dabei."""
    wurzel = _norm(_ECHT_PROGRAMM_DIR)
    return {n: v for n, v in vars(youtube_app).items()
            if not n.startswith("__") and n not in CODE_ORTE and isinstance(v, str)
            and os.path.isabs(v) and _unter(_norm(v), wurzel)}


ECHTE_APP_PFADE = _echte_app_pfade()


def _umgelegt(wert, ziel):
    """Derselbe Pfad unter `ziel`: DATEN_DIR und PROGRAMM_DIR werden zu `ziel`
    (die Downloads liegen dann in ziel\\Downloads, wie im --testmodus)."""
    for basis in (_ECHT_DATEN_DIR, _ECHT_PROGRAMM_DIR):          # das engere zuerst
        if _unter(_norm(wert), _norm(basis)):
            rest = os.path.relpath(wert, basis)
            return ziel if rest == os.curdir else os.path.join(ziel, rest)
    return wert


_LADER = ("_json_laden", "Warteschlange", "config_laden")


def _geladene_zustaende():
    """(Name, Ausdruck) jeder Modul-Zuweisung der App, die beim Import aus einer
    Datei lädt, z. B. `_geladen = _json_laden(GELADEN_PFAD, {})`. Im Quelltext
    gefunden; neu ausgewertet, nachdem die Pfade umgelegt sind."""
    with open(youtube_app.__file__, encoding="utf-8") as f:
        baum = ast.parse(f.read())
    for k in baum.body:
        if (isinstance(k, ast.Assign) and len(k.targets) == 1 and isinstance(k.targets[0], ast.Name)
                and isinstance(k.value, ast.Call) and isinstance(k.value.func, ast.Name)
                and k.value.func.id in _LADER):
            yield k.targets[0].id, compile(ast.Expression(k.value), youtube_app.__file__, "eval")


GELADENE_ZUSTAENDE = tuple(_geladene_zustaende())
if {"Q", "CFG", "_geladen"} - {n for n, _ in GELADENE_ZUSTAENDE}:   # Suche kaputt: laut, nicht still
    raise RuntimeError(f"conftest: geladene Zustände der App nicht gefunden: {GELADENE_ZUSTAENDE}")
# Was config_laden beim Lesen einer alten config.json füllt.
ZUSTAND_AUS_CONFIG = {"VORGABEN_NEU": list, "VORGABEN_ROH": dict}


def _daten_umlegen(setzen, ziel):
    """Alle Datenpfade der App nach `ziel`, dann jeden geladenen Zustand frisch
    aus dem (leeren) `ziel` laden. `setzen` ist setattr oder monkeypatch.setattr."""
    for name, wert in ECHTE_APP_PFADE.items():
        setzen(youtube_app, name, _umgelegt(wert, ziel))
    for name, leer in ZUSTAND_AUS_CONFIG.items():
        setzen(youtube_app, name, leer())
    for name, ausdruck in GELADENE_ZUSTAENDE:
        wert = eval(ausdruck, vars(youtube_app))                  # der App-eigene Ausdruck
        if isinstance(wert, (dict, list)):
            wert = copy.deepcopy(wert)       # CFG teilt sonst Listen mit STANDARD_CONFIG
        setzen(youtube_app, name, wert)


_ECHT_PAPIERKORB = youtube_app._in_papierkorb


def _papierkorb_setzen():
    """Der Papierkorb geht über ctypes (kein Audit-Ereignis): Hülle, die für den
    Programmordner laut scheitert und sonst das Echte ruft."""
    if getattr(youtube_app._in_papierkorb, "daten_wache", False):
        return

    def in_papierkorb(pfad):
        if geschuetzt(pfad):
            _schreib_alarm("Papierkorb", pfad)
        return _ECHT_PAPIERKORB(pfad)
    in_papierkorb.daten_wache = True
    youtube_app._in_papierkorb = in_papierkorb


_NEBEN_MODULE = (profil_geraete, live_tv)        # filme: eigene Wache oben


def _wache_meldung():
    if _WACHE_FUNDE:
        n = list(_WACHE_FUNDE)
        _WACHE_FUNDE.clear()
        pytest.fail(f"Test griff auf den echten Programmordner oder das Netz zu ({n}; "
                    "auch im Hintergrundfaden)", pytrace=False)


@pytest.fixture(scope="session", autouse=True)
def _daten_der_sitzung(tmp_path_factory):
    """Zwischen den Tests zeigt alles in einen Sitzungs-Ordner: ein Faden, der
    seinen Test überlebt, erbt nach dem Zurücksetzen nie die echten Pfade.
    Bewusst ohne Rückweg am Sitzungsende, aus demselben Grund."""
    _ERLAUBT.append(_norm(tmp_path_factory.getbasetemp()))
    ziel = str(tmp_path_factory.mktemp("daten_sitzung"))
    _daten_umlegen(setattr, ziel)
    for modul in (filme,) + _NEBEN_MODULE:
        modul.einrichten(ziel)
    _papierkorb_setzen()
    _netz_sperren_setzen()
    yield
    _wache_meldung()                             # Funde nach dem letzten Test


@pytest.fixture(autouse=True)
def _daten_wache(tmp_path, monkeypatch):
    """Eigene Daten je Test in tmp_path, leere Zustände; liefert die Liste der
    Funde (ein Test, der den Alarm selbst prüft, leert sie). Was die Wache
    fängt, meldet sie am Testende noch einmal: im Hintergrundfaden stirbt
    sonst nur der Faden, und pytest macht daraus bloß eine Warnung."""
    _papierkorb_setzen()
    _netz_sperren_setzen()
    _daten_umlegen(monkeypatch.setattr, str(tmp_path))
    alt = [(modul, dict(modul._pfade)) for modul in _NEBEN_MODULE]
    for modul in _NEBEN_MODULE:
        modul.einrichten(str(tmp_path))
    yield _WACHE_FUNDE
    for modul, pfade in alt:
        modul._pfade.clear()
        modul._pfade.update(pfade)
    _papierkorb_setzen()
    _netz_sperren_setzen()
    _wache_meldung()
