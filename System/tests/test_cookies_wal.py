# -*- coding: utf-8 -*-
"""Firefox-Cookies samt WAL (Lehre aus SyncFindus, Auftrag 24.09.2026).

BEFUND (geprüft an yt-dlp 2026.08.19 in der venv): `yt_dlp/cookies.py`,
`_open_database_copy`, kopiert beim Lesen der Firefox-Cookies nur
`cookies.sqlite` (`shutil.copy`), nicht das `-wal`. Firefox schreibt im
WAL-Modus; alles seit seinem letzten Checkpoint — gerade frische
Anmelde-Cookies — steht nur im `-wal`. SyncYouTube übergab bisher
`cookiesfrombrowser=("firefox",)` und sah diese Cookies nicht. Rot-Lauf vor dem
Fix: alle fünf Cookie-Wege sahen nur `alt`, nie `frisch`.

Die Zusagen:
  (a) Die Attrappe stellt den Ausfall her: der heutige Weg (yt-dlp direkt aufs
      Profil) sieht das Cookie aus dem WAL nicht.
  (b) Jeder Cookie-Weg von youtube_app (Auflösen, Download, Abo, Metadaten,
      Untertitel) gibt dem ECHTEN yt-dlp-Extraktor den WAL-Stand — mit
      richtigem Ablauf (die Kopie behält `user_version`; ab Firefox 142 steht
      der Ablauf in Millisekunden).
  (c) Auch wenn der Browser die Datei exklusiv hält: das Original wird nur als
      Datei gelesen, bleibt byte-gleich, und daneben entsteht nichts. Ohne
      `-wal` (Firefox sauber beendet) klappt die Kopie ebenso. Die Kopie ist
      EINE Datei im Rollback-Modus (Familien-Lehrbuch L88).
  (d) Nach dem Block ist die Kopie weg — auch nach einem Fehler im Block, der
      unverändert weitergeht; zwei Aufrufe teilen sich nie eine Kopie.
  (e) Beginnt der Browser das WAL zwischen Hauptdatei- und WAL-Kopie neu, geht
      nichts verloren; kommt nie ein stimmiges Paar zustande, bleibt es beim
      heutigen Weg.
  (f) Jeder Fehler führt still auf den heutigen Weg: yt-dlp bekommt DASSELBE
      Options-Dict wie heute, und im Temp bleibt nichts liegen.
  (g) Die Optionen des Aufrufers bleiben unberührt.
  (h) Jeder YoutubeDL der Programm-Dateien entsteht über `_ydl`
      (Auto-Discovery im AST, mit Gegenprobe des Finders).
  (i) Die Test-Wache aus `tests/conftest.py` steht in jedem Test.

Kein Test liest JBs echtes Firefox-Profil: APPDATA, LOCALAPPDATA, die Suchorte
und das Temp zeigen in `tmp_path`, und `welt` prüft das, bevor irgendetwas
gelesen wird. Keine Verbindung zu YouTube: yt-dlp wird nur gebaut und nach
seinen Cookies gefragt (`cookiejar`), `extract_info` ist ersetzt.

NICHT geprüft (Prüf-Fläche): ein echter Firefox-Prozess — ob er
`cookies.sqlite` exklusiv hält, ist nicht gemessen; (c) prüft den strengeren
Fall. Das PyInstaller-Paket. Chrome und Edge (bleiben auf dem heutigen Weg).
"""
import ast
import contextlib
import glob
import hashlib
import os
import shutil
import sqlite3
import sys
import types

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import cookie_kopie  # noqa: E402
import youtube_app as app  # noqa: E402

ABLAUF = 1_900_000_000                  # s; Firefox >= 142 speichert Millisekunden
SCHEMA = ("CREATE TABLE moz_cookies (id INTEGER PRIMARY KEY, "
          "originAttributes TEXT NOT NULL DEFAULT '', name TEXT, value TEXT, "
          "host TEXT, path TEXT, expiry INTEGER, lastAccessed INTEGER, "
          "creationTime INTEGER, isSecure INTEGER, isHttpOnly INTEGER)")
#: Nur für (e): eine zweite Tabelle, damit der Commit nach dem WAL-Neubeginn
#: die Seite mit `frisch` NICHT mitbringt (bei Firefox: ein anderes Blatt).
NEBEN = "CREATE TABLE moz_nebenbei (id INTEGER PRIMARY KEY, notiz TEXT)"


# ═══════════════════════════════════════════════════════════════════════
# Die Attrappe: ein laufender Firefox, dessen jüngstes Cookie nur im WAL steht
# ═══════════════════════════════════════════════════════════════════════

def _cookie(con, name):
    con.execute("INSERT INTO moz_cookies (name, value, host, path, expiry, isSecure) "
                "VALUES (?, 'attrappe', '.youtube.com', '/', ?, 1)", (name, ABLAUF * 1000))


def _firefox(profil, exklusiv=True):
    """cookies.sqlite wie bei laufendem Firefox; liefert den OFFENEN Schreiber.

    `alt` steht in der Hauptdatei, `frisch` nur im WAL. Schlösse der letzte
    Nutzer die Datenbank, checkpointete SQLite von selbst und der Rückstand
    wäre weg — deshalb bleibt der Schreiber offen, und zwar mit exklusiver
    Sperre: der strengste Fall für „Firefox darf dabei laufen".
    """
    profil.mkdir(parents=True)
    pfad = profil / "cookies.sqlite"
    basis = sqlite3.connect(pfad)
    basis.execute("PRAGMA journal_mode=WAL")
    basis.execute(SCHEMA)
    basis.execute(NEBEN)
    basis.execute("PRAGMA user_version=17")
    _cookie(basis, "alt")
    basis.commit()
    basis.close()                       # letzter Nutzer: alles in der Hauptdatei
    firefox = sqlite3.connect(pfad, isolation_level=None)
    if exklusiv:
        firefox.execute("PRAGMA locking_mode=EXCLUSIVE")
    firefox.execute("PRAGMA wal_autocheckpoint=0")
    _cookie(firefox, "frisch")
    return firefox


@pytest.fixture
def welt(tmp_path, monkeypatch, request):
    """Firefox-Profil, Suchorte und Temp in tmp_path — geprüft, BEVOR gelesen wird.
    Indirekt parametrisierbar: False = Firefox im Normalmodus mit `-shm`
    (Prüfung Runde 2: JBs echtes Profil hat ein `-shm`, also sehr
    wahrscheinlich kein Exklusiv-Modus); Vorgabe True = der strengste Fall."""
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    import conftest
    from yt_dlp import cookies as yc
    # Die Wache biegt auch yt-dlps eigene Suche um; die Welt braucht die echte
    # (über APPDATA/LOCALAPPDATA in tmp_path) — bewusst zurückgenommen.
    monkeypatch.setattr(yc, "_firefox_browser_dirs", conftest.ECHTE_FIREFOX_SUCHE)
    for ort in yc._firefox_browser_dirs():
        assert os.path.abspath(ort).startswith(str(tmp_path)), (
            f"Die Firefox-Suche zeigt aus der Testwelt hinaus: {ort}")
    monkeypatch.setattr(cookie_kopie, "WURZELN", None)   # die Suche wie im Betrieb
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr("tempfile.tempdir", str(temp))
    monkeypatch.setitem(app.CFG, "cookies_browser", "firefox")
    profil = appdata / "Mozilla" / "Firefox" / "Profiles" / "probe.default-release"
    exklusiv = getattr(request, "param", True)
    firefox = _firefox(profil, exklusiv=exklusiv)
    yield types.SimpleNamespace(profil=profil, firefox=firefox, temp=temp, exklusiv=exklusiv)
    firefox.close()


def _namen(profil):
    """Cookie-NAMEN einer Kopie (nie Werte)."""
    with contextlib.closing(sqlite3.connect(os.path.join(profil, "cookies.sqlite"))) as con:
        return {r[0] for r in con.execute("SELECT name FROM moz_cookies")}


def _abbild(ordner):
    """Name -> (Größe, mtime, sha256) jeder Datei im Ordner."""
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns,
                     hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(ordner.iterdir())}


# ═══════════════════════════════════════════════════════════════════════
# (a) und (b): heute unsichtbar, über jeden Cookie-Weg sichtbar
# ═══════════════════════════════════════════════════════════════════════

def test_a_die_attrappe_stellt_den_ausfall_her(welt):
    """Der heutige Weg: yt-dlp mit `("firefox",)` direkt aufs Profil."""
    import yt_dlp
    with yt_dlp.YoutubeDL(app._ydl_basis_opts(mit_cookies=True)) as ydl:
        namen = {c.name for c in ydl.cookiejar}
    assert "alt" in namen
    assert "frisch" not in namen, (
        "yt-dlp liest das -wal inzwischen selbst mit — dann ist cookie_kopie "
        "überflüssig und kann mit dieser Probe ins Archiv")


def _spion(monkeypatch):
    """Der ECHTE YoutubeDL; nur `extract_info` ist ersetzt: er liest die Cookies
    und bricht dann ab (kein Netz)."""
    import yt_dlp
    gesehen = {}

    class Spion(yt_dlp.YoutubeDL):
        def extract_info(self, url, download=True, *a, **k):
            gesehen.update({c.name: c.expires for c in self.cookiejar})
            raise app.AbbruchError()

    monkeypatch.setattr(yt_dlp, "YoutubeDL", Spion)
    return gesehen


def _weg_aufloesen(tmp_path, monkeypatch):
    # Der Platzhalter ist ein echter Eintrag der Warteschlange (die conftest legt
    # Q je Test frisch an): seit F2 fragt aufloesen YouTube nur für einen
    # Platzhalter, der noch in der Liste steht.
    monkeypatch.setattr(app.Q, "speichern", lambda *a, **k: None)
    monkeypatch.setattr(app, "FEHLER_LOG", str(tmp_path / "yt_fehler.jsonl"))
    app.aufloesen("https://www.youtube.com/watch?v=ABCdef12345", "720p")


def _weg_download(tmp_path, monkeypatch):
    monkeypatch.setattr(app.Q, "speichern", lambda *a, **k: None)
    monkeypatch.setattr(app, "FEHLER_LOG", str(tmp_path / "yt_fehler.jsonl"))
    item = {"id": "cookiewal1", "qualitaet": "720p", "status": "laeuft",
            "titel": "Probe", "url": "https://www.youtube.com/watch?v=ABCdef12345",
            "prozent": 0.0, "geladen": 0, "gesamt": 0, "geschw": 0, "phase": "",
            "versuche": 0, "fehler": "", "naechster_versuch": 0}
    app._download_lauf(item)


def _weg_abo(tmp_path, monkeypatch):
    app._abo_flach("https://www.youtube.com/@probe/videos")


def _weg_metadaten(tmp_path, monkeypatch):
    app._enrich_eintrag("ABCdef12345|720p", {"titel": "Probe"})


def _weg_untertitel(tmp_path, monkeypatch):
    key = "ABCdef12345|720p"
    monkeypatch.setitem(app._geladen, key, {"titel": "Probe"})
    monkeypatch.setattr(app, "_pfad_zu_key", lambda k: str(tmp_path / "probe.mp4"))
    monkeypatch.setattr(app, "untertitel_ordner", lambda: str(tmp_path / "untertitel"))
    app.untertitel_nachladen(key)


WEGE = {"aufloesen": _weg_aufloesen, "download": _weg_download, "abo": _weg_abo,
        "metadaten": _weg_metadaten, "untertitel": _weg_untertitel}


@pytest.mark.parametrize("welt", [True, False], indirect=True, ids=["exklusiv", "normal"])
@pytest.mark.parametrize("weg", sorted(WEGE))
def test_b_jeder_cookie_weg_sieht_das_wal_cookie(weg, welt, tmp_path, monkeypatch):
    gesehen = _spion(monkeypatch)
    WEGE[weg](tmp_path, monkeypatch)
    assert "alt" in gesehen, f"{weg}: yt-dlp hat gar keine Cookies gelesen"
    assert "frisch" in gesehen, (
        f"{weg}: das frische Cookie steht nur im -wal, yt-dlp sieht es nicht")
    assert gesehen["frisch"] == ABLAUF, "Ablauf falsch: user_version ging verloren"
    assert os.listdir(welt.temp) == [], f"{weg}: Cookie-Kopie im Temp liegengeblieben"


# ═══════════════════════════════════════════════════════════════════════
# (c) Das Original: nur gelesen, auch unter exklusiver Sperre
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("welt", [True, False], indirect=True, ids=["exklusiv", "normal"])
def test_c_original_bleibt_unberuehrt_auch_bei_exklusiver_sperre(welt):
    """Exklusiv: jede fremde Verbindung wäre „locked". Normalmodus (Prüfung
    Runde 2, wie JBs Profil mit `-shm`): das Original bleibt SAMT `-shm`
    byte-gleich, und das frische Cookie aus dem WAL ist in der Kopie."""
    ziel = welt.profil / "cookies.sqlite"
    if welt.exklusiv:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            fremd = sqlite3.connect(ziel.as_uri() + "?mode=ro", uri=True, timeout=0)
            try:
                fremd.execute("SELECT count(*) FROM moz_cookies").fetchone()
            finally:
                fremd.close()
    vorher = _abbild(welt.profil)
    assert "cookies.sqlite-wal" in vorher
    assert ("cookies.sqlite-shm" in vorher) is (not welt.exklusiv), sorted(vorher)
    with cookie_kopie.firefox_profil(("firefox",)) as profil:
        assert profil, "Die Kopie scheitert, solange der Browser die Datei hält"
        assert _namen(profil) == {"alt", "frisch"}
    assert _abbild(welt.profil) == vorher, "Das Firefox-Profil wurde verändert"


def test_c2_ohne_wal_firefox_sauber_beendet(welt):
    welt.firefox.close()                # letzter Nutzer: checkpointet, -wal ist weg
    assert not (welt.profil / "cookies.sqlite-wal").exists()
    with cookie_kopie.firefox_profil(("firefox",)) as profil:
        assert profil and _namen(profil) == {"alt", "frisch"}


def test_c3_die_kopie_ist_eine_einzige_datei_im_rollback_modus(welt):
    """Die Backup-API übernimmt den WAL-Kopf der Quelle; ohne Umstellung legte
    jeder Leser `-wal` und `-shm` neben die Kopie (Familien-Lehrbuch L88)."""
    with cookie_kopie.firefox_profil(("firefox",)) as profil:
        assert os.listdir(profil) == ["cookies.sqlite"]
        with open(os.path.join(profil, "cookies.sqlite"), "rb") as f:
            kopf = f.read(20)
        assert (kopf[18], kopf[19]) == (1, 1), "Die Kopie steht noch im WAL-Modus"


# ═══════════════════════════════════════════════════════════════════════
# (d) Aufräumen, Fehler im Block, Gleichzeitigkeit
# ═══════════════════════════════════════════════════════════════════════

def test_d_keine_kopie_bleibt_zurueck(welt):
    with cookie_kopie.firefox_profil(("firefox",)) as profil:
        assert os.path.isfile(os.path.join(profil, "cookies.sqlite"))
    assert not os.path.exists(profil)
    assert os.listdir(welt.temp) == []


def test_d2_ein_fehler_im_block_geht_weiter_und_die_kopie_ist_trotzdem_weg(welt):
    """Die Sperren-Erkennung von youtube_app muss yt-dlps Meldung unverändert sehen."""
    with pytest.raises(RuntimeError, match="not a bot"):
        with cookie_kopie.firefox_profil(("firefox",)):
            raise RuntimeError("Sign in to confirm you're not a bot")
    assert os.listdir(welt.temp) == []


def test_d3_zwei_aufrufe_teilen_sich_nie_eine_kopie(welt):
    with cookie_kopie.firefox_profil(("firefox",)) as a, \
            cookie_kopie.firefox_profil(("firefox",)) as b:
        assert a and b and a != b
        assert _namen(a) == _namen(b) == {"alt", "frisch"}
    assert os.listdir(welt.temp) == []


# ═══════════════════════════════════════════════════════════════════════
# (e) Firefox beginnt das WAL während der Kopie neu
# ═══════════════════════════════════════════════════════════════════════

def _neubeginn(firefox):
    """Firefox checkpointet vollständig und beginnt das WAL mit einem Commit neu.

    Der Commit trifft bewusst eine ANDERE Tabelle: er darf die Seite mit
    `frisch` nicht mitbringen, sonst wäre der Verlust unsichtbar.
    """
    firefox.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    firefox.execute("INSERT INTO moz_nebenbei (notiz) VALUES ('neu begonnen')")


def _nach_hauptdatei(monkeypatch, aktion):
    """Lässt `aktion` laufen, sobald die Hauptdatei kopiert ist, vor dem -wal."""
    echt = shutil.copyfile

    def copyfile(quelle, ziel, *a, **k):
        ergebnis = echt(quelle, ziel, *a, **k)
        if os.fspath(quelle).endswith("cookies.sqlite"):
            aktion()
        return ergebnis

    monkeypatch.setattr(cookie_kopie, "shutil",
                        types.SimpleNamespace(copyfile=copyfile, rmtree=shutil.rmtree))


def test_e_neubeginn_waehrend_der_kopie_verliert_nichts(welt, monkeypatch):
    begonnen = []

    def einmal():
        if not begonnen:
            _neubeginn(welt.firefox)
            begonnen.append(True)

    _nach_hauptdatei(monkeypatch, einmal)
    with cookie_kopie.firefox_profil(("firefox",)) as profil:
        assert begonnen, "Attrappe: der Neubeginn wurde nie ausgelöst"
        assert profil and _namen(profil) == {"alt", "frisch"}, (
            "Hauptdatei vor dem Checkpoint, -wal danach: das Paar passt nicht "
            "zusammen, und was der Checkpoint geschrieben hat, fehlt")


def test_e2_ohne_stimmiges_paar_bleibt_es_beim_heutigen_weg(welt, monkeypatch):
    _nach_hauptdatei(monkeypatch, lambda: _neubeginn(welt.firefox))
    with cookie_kopie.firefox_profil(("firefox",)) as profil:
        assert profil is None
    assert os.listdir(welt.temp) == []


# ═══════════════════════════════════════════════════════════════════════
# (f) und (g): jeder Fehler = der heutige Weg; die Aufrufer-Optionen bleiben
# ═══════════════════════════════════════════════════════════════════════

class _Attrappe:
    """YoutubeDL, der nur festhält, welches Options-Dict er bekam."""
    bekommen = []

    def __init__(self, opts):
        _Attrappe.bekommen.append(opts)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _kein_firefox(welt, tmp_path, monkeypatch, opts):
    monkeypatch.setattr(cookie_kopie, "WURZELN", [str(tmp_path / "leer")])


def _kaputte_datei(welt, tmp_path, monkeypatch, opts):
    welt.firefox.close()
    (welt.profil / "cookies.sqlite").write_bytes(b"keine Datenbank " * 64)


def _anderer_browser(welt, tmp_path, monkeypatch, opts):
    opts["cookiesfrombrowser"] = ("chrome",)


def _eigenes_profil(welt, tmp_path, monkeypatch, opts):
    opts["cookiesfrombrowser"] = ("firefox", str(welt.profil))


def _ohne_cookies(welt, tmp_path, monkeypatch, opts):
    opts.pop("cookiesfrombrowser")


def _yt_dlp_ohne_profilsuche(welt, tmp_path, monkeypatch, opts):
    """Die private yt-dlp-Funktion fehlt (Umbau in einer künftigen Fassung)."""
    from yt_dlp import cookies as yc
    monkeypatch.delattr(yc, "_firefox_cookie_dbs")


def _temp_mit_klammer(welt, tmp_path, monkeypatch, opts):
    """yt-dlps Profilsuche ist ein glob — `[x]` im Temp-Pfad wäre eine Zeichenklasse."""
    temp = tmp_path / "Temp [x]"
    temp.mkdir()
    monkeypatch.setattr("tempfile.tempdir", str(temp))


RUECKFAELLE = {"kein_firefox": _kein_firefox, "kaputte_datei": _kaputte_datei,
               "anderer_browser": _anderer_browser, "eigenes_profil": _eigenes_profil,
               "ohne_cookies": _ohne_cookies,
               "yt_dlp_ohne_profilsuche": _yt_dlp_ohne_profilsuche,
               "temp_mit_klammer": _temp_mit_klammer}


@pytest.mark.parametrize("fall", sorted(RUECKFAELLE))
def test_f_jeder_fehler_fuehrt_still_auf_den_heutigen_weg(fall, welt, tmp_path, monkeypatch):
    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", _Attrappe)
    opts = app._ydl_basis_opts(mit_cookies=True)
    RUECKFAELLE[fall](welt, tmp_path, monkeypatch, opts)
    vorher = dict(opts)
    _Attrappe.bekommen = []
    with app._ydl(opts):
        pass
    assert _Attrappe.bekommen == [opts] and _Attrappe.bekommen[0] is opts, (
        f"{fall}: yt-dlp bekam nicht dasselbe Options-Dict wie heute")
    assert opts == vorher
    for ordner in (welt.temp, tmp_path / "Temp [x]"):
        if ordner.exists():
            assert os.listdir(ordner) == [], f"{fall}: Reste im Temp"


def test_g_die_optionen_des_aufrufers_bleiben_unberuehrt(welt, monkeypatch):
    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", _Attrappe)
    opts = app._ydl_basis_opts(mit_cookies=True)
    vorher = dict(opts)
    _Attrappe.bekommen = []
    with app._ydl(opts):
        bekommen = _Attrappe.bekommen[-1]
        browser, profil = bekommen["cookiesfrombrowser"]
        assert bekommen is not opts and browser == "firefox"
        assert os.path.isfile(os.path.join(profil, "cookies.sqlite")), (
            "Die Kopie muss leben, solange der YoutubeDL lebt")
    assert opts == vorher and opts["cookiesfrombrowser"] == ("firefox",)
    assert not os.path.exists(profil)


# ═══════════════════════════════════════════════════════════════════════
# (h) Jeder YoutubeDL entsteht über _ydl (Auto-Discovery)
# ═══════════════════════════════════════════════════════════════════════

def _youtubedl_bauer(quelltext, datei):
    """Jede Stelle, die einen YoutubeDL baut, als `datei::funktion`."""
    stellen = set()

    def besuchen(knoten, kette):
        for kind in ast.iter_child_nodes(knoten):
            if isinstance(kind, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                besuchen(kind, kette + (kind.name,))
                continue
            if isinstance(kind, ast.Call):
                f = kind.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                if name == "YoutubeDL":
                    stellen.add(f"{datei}::{'.'.join(kette) or '<modul>'}")
            besuchen(kind, kette)

    besuchen(ast.parse(quelltext), ())
    return stellen


def _programm_dateien():
    return sorted(glob.glob(os.path.join(MODUL_DIR, "*.py"))
                  + glob.glob(os.path.join(MODUL_DIR, "tools", "*.py")))


def test_h_jeder_youtubedl_entsteht_ueber_ydl():
    dateien = _programm_dateien()
    assert any(p.endswith("youtube_app.py") for p in dateien)
    stellen = set()
    for pfad in dateien:
        with open(pfad, encoding="utf-8") as f:
            stellen |= _youtubedl_bauer(f.read(), os.path.relpath(pfad, MODUL_DIR))
    assert stellen == {"youtube_app.py::_ydl"}, (
        "Ein YoutubeDL entsteht an _ydl vorbei — dort sähe yt-dlp die frischen "
        f"Firefox-Cookies aus dem -wal nicht: {sorted(stellen)}")


def test_h2_gegenprobe_der_finder_sieht_einen_direkten_bau():
    direkt = ("def _abo_flach(url):\n    import yt_dlp\n"
              "    with yt_dlp.YoutubeDL({}) as y:\n        return y\n")
    assert _youtubedl_bauer(direkt, "x.py") == {"x.py::_abo_flach"}
    assert _youtubedl_bauer("from yt_dlp import YoutubeDL\nYoutubeDL({})\n", "y.py") \
        == {"y.py::<modul>"}
    assert _youtubedl_bauer('"""yt_dlp.YoutubeDL(opts) im Text"""\n', "z.py") == set()


# ═══════════════════════════════════════════════════════════════════════
# (i) Die Wache aus conftest.py
# ═══════════════════════════════════════════════════════════════════════

def test_i_die_wache_steht_in_jedem_test():
    """Ohne Fixture-Anforderung: die Suche findet während der Tests kein Profil
    (beide Suchen: cookie_kopie und yt-dlps eigene, s. tests/test_wachen.py)."""
    import conftest
    from yt_dlp import cookies as yc
    assert cookie_kopie.WURZELN is not None, (
        "tests/conftest.py setzt die Suchorte nicht — ein Test läse JBs Firefox-Profil")
    echte = {os.path.normcase(os.path.abspath(p)) for p in conftest.ECHTE_FIREFOX_SUCHE()}
    assert not echte & {os.path.normcase(os.path.abspath(p)) for p in yc._firefox_browser_dirs()}
    gesetzt = {os.path.normcase(os.path.abspath(p)) for p in cookie_kopie.WURZELN}
    assert not echte & gesetzt
    assert cookie_kopie._quelle(cookie_kopie.WURZELN) is None
