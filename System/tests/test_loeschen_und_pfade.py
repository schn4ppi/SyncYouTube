# -*- coding: utf-8 -*-
"""Lösch- und Pfadlücken (Gesamtprüfung 25.09.2026, Gruppe 2).

Jeder Test hier fährt die echte Funktion mit Werten, wie sie ein Client
schicken kann: `..\\x`, ein absoluter Pfad, ein UNC-Pfad und ein gültiger
Wert. Der Papierkorb ist in jedem Test eine Attrappe (der echte ginge in JBs
Windows-Papierkorb), und UNC-Pfade erreichen nie das Netz: jeder Datei-Zugriff
darauf wird vorher abgefangen und gezählt (`kein_netzpfad`, für jeden Test).
Der Rechnername endet auf `.invalid` (RFC 2606, löst nie auf) als zweite
Sicherung.
"""
import builtins
import glob as glob_modul
import os
import shutil
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402

UNC = "\\\\unc-probe.invalid\\freigabe\\x"


def _unter(pfad, wurzel):
    pfad = os.path.normcase(os.path.abspath(pfad))
    wurzel = os.path.normcase(os.path.abspath(wurzel))
    return pfad == wurzel or pfad.startswith(wurzel.rstrip(os.sep) + os.sep)


def _ist_unc(pfad):
    try:
        s = os.fsdecode(os.fspath(pfad))
    except TypeError:
        return False
    return s.startswith(("\\\\", "//"))


# Prüfungen liefern „gibt es nicht“, Aufzählungen nichts, alles andere scheitert
# mit OSError, bevor Windows den Pfad sieht.
_PRUEFUNGEN = ((os.path, ("isfile", "exists", "isdir", "lexists", "getsize"), False),
               (glob_modul, ("glob", "iglob"), []))
_ZUGRIFFE = ((os, ("mkdir", "makedirs", "remove", "unlink", "rmdir", "replace", "rename",
                   "stat", "lstat", "scandir", "listdir", "utime", "open", "startfile")),
             (shutil, ("copy", "copy2", "copyfile", "move", "rmtree")),
             (builtins, ("open",)))


@pytest.fixture(autouse=True)
def kein_netzpfad(monkeypatch):
    """Liste der abgefangenen UNC-Zugriffe (ein Test, der sie erwartet, leert sie)."""
    zugriffe = []

    def pruefung(echt, leer):
        def f(*a, **k):
            if any(_ist_unc(x) for x in a[:2]):
                zugriffe.append(os.fspath(a[0]))
                return leer
            return echt(*a, **k)
        return f

    def zugriff(echt):
        def f(*a, **k):
            if any(_ist_unc(x) for x in a[:2]):
                zugriffe.append(os.fspath(a[0]))
                raise OSError("Test: UNC-Zugriff abgefangen")
            return echt(*a, **k)
        return f
    for modul, namen, leer in _PRUEFUNGEN:
        for n in namen:
            monkeypatch.setattr(modul, n, pruefung(getattr(modul, n), leer))
    for modul, namen in _ZUGRIFFE:
        for n in namen:
            if hasattr(modul, n):
                monkeypatch.setattr(modul, n, zugriff(getattr(modul, n)))
    yield zugriffe


@pytest.fixture
def korb(monkeypatch):
    """Papierkorb-Attrappe: merkt sich jeden Pfad; `korb.klappt` steuert den
    Erfolg. Bei Erfolg verschwindet die Datei (wie im echten Papierkorb)."""
    class Korb(list):
        klappt = True

    k = Korb()

    def in_papierkorb(pfad):
        k.append(pfad)
        if k.klappt and os.path.isfile(pfad):
            os.replace(pfad, pfad + ".im_korb")
        return k.klappt
    monkeypatch.setattr(app, "_in_papierkorb", in_papierkorb)
    return k


@pytest.fixture
def entfernt(monkeypatch, tmp_path):
    """Zeichnet jedes os.remove auf. Innerhalb von tmp_path löscht es echt;
    alles andere (UNC, fremde Laufwerke) wird NICHT ausgeführt, sondern mit
    OSError abgelehnt: so geht kein Test ins Netz."""
    aufrufe = []
    echt = os.remove

    def remove(pfad, *a, **k):
        aufrufe.append(os.fspath(pfad))
        if not _unter(pfad, tmp_path):
            raise OSError("Test: Zugriff außerhalb von tmp_path abgelehnt")
        return echt(pfad, *a, **k)
    monkeypatch.setattr(os, "remove", remove)
    return aufrufe


# ---------------------------------------------------------------- S1: /api/abo löscht per ungeprüfter Id

def _abo_welt(tmp_path, monkeypatch):
    index = tmp_path / "daten" / "abo_index"
    index.mkdir(parents=True)
    monkeypatch.setattr(app, "ABO_INDEX_ORDNER", str(index))
    opfer = tmp_path / "daten" / "x.json"            # neben dem Index (wie config.json)
    opfer.write_text("{}", encoding="utf-8")
    return index, opfer


@pytest.mark.parametrize("boese", ["..\\x", "../x", "ABSOLUT", UNC])
def test_abo_delete_mit_fremder_id_loescht_nichts(tmp_path, monkeypatch, korb, entfernt, boese):
    """Die Id kommt vom Client. Vorher löschte `delete` die Datei
    `<ABO_INDEX_ORDNER>/<id>.json` endgültig, auch ohne Abo dieser Id."""
    index, opfer = _abo_welt(tmp_path, monkeypatch)
    if boese == "ABSOLUT":
        boese = str(opfer)[:-len(".json")]
    r = app.abo_aktion({"art": "delete", "id": boese})
    assert r.get("ok"), r
    assert opfer.is_file(), "eine Datei außerhalb des Abo-Index wurde gelöscht"
    fremd = [p for p in entfernt + list(korb) if not _unter(p, index)]
    assert not fremd, f"Löschversuch außerhalb des Abo-Index: {fremd}"


def test_abo_delete_ohne_abo_laesst_index_datei_stehen(tmp_path, monkeypatch, korb, entfernt):
    """Gültig aussehende Id, aber kein Abo dazu: nichts wird angefasst."""
    index, _ = _abo_welt(tmp_path, monkeypatch)
    waise = index / "deadbeef.json"
    waise.write_text("{}", encoding="utf-8")
    assert app.abo_aktion({"art": "delete", "id": "deadbeef"}).get("ok")
    assert waise.is_file() and not entfernt and not korb


def test_abo_delete_gueltig_index_in_den_papierkorb(tmp_path, monkeypatch, korb, entfernt):
    """Echtes Abo (Id wie uuid4().hex[:8]): sein Folgen-Cache geht in den
    Papierkorb, nie per os.remove; das Abo selbst ist weg."""
    index, opfer = _abo_welt(tmp_path, monkeypatch)
    cache = index / "a1b2c3d4.json"
    cache.write_text("{}", encoding="utf-8")
    app._abos.append({"id": "a1b2c3d4", "name": "K", "qualitaet": "audio"})
    assert app.abo_aktion({"art": "delete", "id": "a1b2c3d4"}).get("ok")
    assert korb == [str(cache)], korb
    assert not entfernt, f"os.remove statt Papierkorb: {entfernt}"
    assert not any(a.get("id") == "a1b2c3d4" for a in app._abos)
    assert opfer.is_file()


def test_abo_delete_abo_mit_fremder_id_form_wird_entfernt_ohne_datei(tmp_path, monkeypatch,
                                                                     korb, entfernt):
    """Steht im Bestand ein Abo, dessen Id keine uuid-Form hat, geht das Abo
    wie bisher; eine Datei wird dann aber nicht angefasst."""
    index, opfer = _abo_welt(tmp_path, monkeypatch)
    app._abos.append({"id": "..\\x", "name": "K", "qualitaet": "audio"})
    assert app.abo_aktion({"art": "delete", "id": "..\\x"}).get("ok")
    assert not any(a.get("id") == "..\\x" for a in app._abos)
    assert opfer.is_file() and not entfernt and not korb


# ---------------------------------------------------------------- S4: /api/cover und /api/untertitel

def _dl(tmp_path, monkeypatch):
    dl = tmp_path / "dl"
    (dl / "Cover").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(dl))
    return dl


def _boeser_schluessel(boese, tmp_path):
    if boese == "ABSOLUT":
        return str(tmp_path / "geheim") + "|beste"
    return boese + "|beste"


BOESE_IDS = ["..\\geheim", "../geheim", "ABSOLUT", UNC]   # ABSOLUT = mit Laufwerk


@pytest.mark.parametrize("boese", BOESE_IDS)
def test_cover_liest_nur_im_cover_ordner(tmp_path, monkeypatch, kein_netzpfad, boese):
    """/api/cover?id=… liest `Cover/<id>.jpg`. Vorher verließ die Id den
    Ordner (`..`, Laufwerk) oder fragte ein Netzlaufwerk an (UNC)."""
    dl = _dl(tmp_path, monkeypatch)
    (dl / "geheim.jpg").write_bytes(b"GEHEIM")           # Cover\..\geheim.jpg
    (tmp_path / "geheim.jpg").write_bytes(b"GEHEIM")     # absoluter Pfad
    assert app.cover_aus_datei(_boeser_schluessel(boese, tmp_path)) is None
    assert not kein_netzpfad, f"Netzlaufwerk angefragt: {kein_netzpfad}"


@pytest.mark.parametrize("boese", BOESE_IDS)
def test_cover_schreibt_nur_in_den_cover_ordner(tmp_path, monkeypatch, kein_netzpfad, boese):
    """Das Sidecar-Cover eines Videos entsteht aus demselben Schlüssel; mit
    einer schiefen Id landete das Bild außerhalb des Cover-Ordners."""
    dl = _dl(tmp_path, monkeypatch)
    video = dl / "clip.mp4"
    video.write_bytes(b"v" * 10)
    key = _boeser_schluessel(boese, tmp_path)
    monkeypatch.setattr(app, "_geladen", {key: {"pfad": str(video)}})
    vorher = {p for p in tmp_path.rglob("*")}
    app._cover_in_datei(key, app._geladen[key], b"B" * 3000)
    neu = {p for p in tmp_path.rglob("*")} - vorher
    assert not neu, f"Cover außerhalb des Cover-Ordners geschrieben: {neu}"
    assert not kein_netzpfad, f"Netzlaufwerk angefragt: {kein_netzpfad}"


def test_cover_gueltige_ids_bleiben(tmp_path, monkeypatch):
    """YouTube-Id und eigene lokal-Id lesen weiter ihr Sidecar."""
    dl = _dl(tmp_path, monkeypatch)
    for vid in ("vid123abc45", "lokal-0123456789a"):
        (dl / "Cover" / f"{vid}.jpg").write_bytes(vid.encode())
        assert app.cover_aus_datei(f"{vid}|beste") == vid.encode()


@pytest.mark.parametrize("boese", BOESE_IDS)
def test_untertitel_nur_im_untertitel_ordner(tmp_path, monkeypatch, kein_netzpfad, boese):
    """/api/untertitel?id=… sucht `Untertitel/<id>.*.vtt`. Vorher verließ die
    Id den Ordner oder fragte ein Netzlaufwerk an."""
    dl = _dl(tmp_path, monkeypatch)
    (dl / "Untertitel").mkdir()
    for ort in (dl, tmp_path):                           # Untertitel\..\ und absolut
        (ort / "geheim.de.vtt").write_text("WEBVTT\n\nGEHEIM", encoding="utf-8")
    key = _boeser_schluessel(boese, tmp_path)
    assert app.untertitel_liste(key) == []
    assert app.untertitel_datei(key) == (None, "")
    assert not kein_netzpfad, f"Netzlaufwerk angefragt: {kein_netzpfad}"


def test_untertitel_gueltige_id_und_url_schluessel_bleiben(tmp_path, monkeypatch, kein_netzpfad):
    """Eine YouTube-Id findet ihren Untertitel im Ordner; ein Download, der
    nicht von YouTube stammt (die ganze URL ist der Schlüssel), behält den
    Rückfall über seine Datei in der Bibliothek."""
    dl = _dl(tmp_path, monkeypatch)
    (dl / "Untertitel").mkdir()
    ut = dl / "Untertitel" / "abcdef12345.de.vtt"
    ut.write_text("WEBVTT", encoding="utf-8")
    assert app.untertitel_liste("abcdef12345|beste") == [(str(ut), "de")]
    video = dl / "Clip.mp4"
    video.write_bytes(b"v")
    neben = dl / "Clip.en.vtt"
    neben.write_text("WEBVTT", encoding="utf-8")
    url_key = "https://example.org/video/7|beste"
    monkeypatch.setattr(app, "_geladen", {url_key: {"pfad": str(video)}})
    assert app.untertitel_liste(url_key) == [(str(neben), "en")]
    assert not kein_netzpfad


@pytest.mark.parametrize("boese", BOESE_IDS)
def test_untertitel_nachladen_schreibt_nur_in_den_untertitel_ordner(tmp_path, monkeypatch,
                                                                    kein_netzpfad, boese):
    """/api/untertitel_laden: der Schlüssel wird zum Ziel des yt-dlp-Laufs.
    Mit einer schiefen Id läge die .vtt außerhalb des Untertitel-Ordners."""
    dl = _dl(tmp_path, monkeypatch)
    video = dl / "clip.mp4"
    video.write_bytes(b"v")
    key = _boeser_schluessel(boese, tmp_path)
    monkeypatch.setattr(app, "_geladen", {key: {"pfad": str(video), "url": "https://example.org/v"}})
    ziele = []

    class Ydl:
        def __init__(self, opts):
            ziele.append(opts["outtmpl"]["default"])

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, *a, **k):
            return {}
    monkeypatch.setattr(app, "_ydl", Ydl)
    app.untertitel_nachladen(key)
    ordner = str(dl / "Untertitel")
    draussen = [z for z in ziele if not _unter(z, ordner)]
    assert not draussen, f"Untertitel-Ziel außerhalb des Ordners: {draussen}"


def test_untertitel_nachladen_gueltige_id_bleibt(tmp_path, monkeypatch):
    dl = _dl(tmp_path, monkeypatch)
    video = dl / "clip.mp4"
    video.write_bytes(b"v")
    monkeypatch.setattr(app, "_geladen", {"abcdef12345|beste": {"pfad": str(video)}})
    ziele = []

    class Ydl:
        def __init__(self, opts):
            ziele.append(opts["outtmpl"]["default"])

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, *a, **k):
            return {}
    monkeypatch.setattr(app, "_ydl", Ydl)
    app.untertitel_nachladen("abcdef12345|beste")
    assert ziele == [os.path.join(str(dl / "Untertitel"), "abcdef12345") + ".%(ext)s"]


# ---------------------------------------------------------------- S6: kein harter Lösch-Rückfall

def _bibliothek(tmp_path, monkeypatch, name="Titel [abcdef12345].mp3", ort=None):
    dl = _dl(tmp_path, monkeypatch)
    ordner = ort or (dl / "MP3")
    ordner.mkdir(parents=True, exist_ok=True)
    datei = ordner / name
    datei.write_bytes(b"MUSIK")
    key = "abcdef12345|audio"
    app._geladen[key] = {"name": name, "pfad": str(datei)}
    app._playlists.append({"id": "pl1", "name": "P", "items": [key]})
    return dl, datei, key


def _meldungen():
    try:
        with open(app.FEHLER_LOG, encoding="utf-8") as f:
            return [z for z in f.read().splitlines() if '"papierkorb"' in z]
    except OSError:
        return []


def test_papierkorb_klappt_nichts_weiter(tmp_path, monkeypatch, korb, entfernt):
    dl, datei, key = _bibliothek(tmp_path, monkeypatch)
    app._datei_loeschen(key)
    assert korb == [str(datei)] and not entfernt
    assert not (dl / "_Papierkorb").exists()
    assert app._playlists[-1]["items"] == []
    assert not _meldungen()


def test_papierkorb_scheitert_rueckholbar_verschoben_nie_geloescht(tmp_path, monkeypatch,
                                                                    korb, entfernt):
    """Vorher: scheiterte der Papierkorb, löschte `_datei_loeschen` endgültig
    (os.remove). Jetzt wandert die Datei in `_Papierkorb` im Download-Ordner
    (derselbe Datenträger), und das wird gemeldet."""
    korb.klappt = False
    dl, datei, key = _bibliothek(tmp_path, monkeypatch)
    app._datei_loeschen(key)
    assert not entfernt, f"endgültig gelöscht per os.remove: {entfernt}"
    gerettet = dl / "_Papierkorb" / datei.name
    assert gerettet.read_bytes() == b"MUSIK", "Datei nicht rückholbar im _Papierkorb"
    assert not datei.exists()
    assert app._playlists[-1]["items"] == []
    assert len(_meldungen()) == 1 and datei.name in _meldungen()[0]


def test_papierkorb_meldet_erfolg_datei_liegt_noch(tmp_path, monkeypatch, entfernt):
    """Meldet der Papierkorb Erfolg, liegt die Datei aber noch da (abgebrochen),
    greift derselbe Rückfall."""
    monkeypatch.setattr(app, "_in_papierkorb", lambda p: True)
    dl, datei, key = _bibliothek(tmp_path, monkeypatch)
    app._datei_loeschen(key)
    assert (dl / "_Papierkorb" / datei.name).is_file() and not datei.exists()
    assert not entfernt


def test_rueckfall_ueberschreibt_nie(tmp_path, monkeypatch, korb, entfernt):
    korb.klappt = False
    dl, datei, key = _bibliothek(tmp_path, monkeypatch)
    (dl / "_Papierkorb").mkdir()
    alt = dl / "_Papierkorb" / datei.name
    alt.write_bytes(b"ALT")
    app._datei_loeschen(key)
    assert alt.read_bytes() == b"ALT"
    assert (dl / "_Papierkorb" / "Titel [abcdef12345] (2).mp3").read_bytes() == b"MUSIK"


def test_rueckfall_ausserhalb_des_download_ordners_neben_der_datei(tmp_path, monkeypatch,
                                                                   korb, entfernt):
    korb.klappt = False
    _dl(tmp_path, monkeypatch)
    dl, datei, key = _bibliothek(tmp_path, monkeypatch, ort=tmp_path / "anderswo")
    app._datei_loeschen(key)
    assert (tmp_path / "anderswo" / "_Papierkorb" / datei.name).is_file()
    assert not entfernt


def test_rueckfall_scheitert_datei_bleibt_und_wird_gemeldet(tmp_path, monkeypatch, korb, entfernt):
    korb.klappt = False
    dl, datei, key = _bibliothek(tmp_path, monkeypatch)

    def kein_rename(*a, **k):
        raise OSError("gesperrt")
    monkeypatch.setattr(os, "rename", kein_rename)
    monkeypatch.setattr(os, "replace", kein_rename)
    app._datei_loeschen(key)
    assert datei.read_bytes() == b"MUSIK" and not entfernt
    assert len(_meldungen()) == 1


def _rueckhol_welt(tmp_path, monkeypatch):
    """Je eine Mediendatei in `_Papierkorb` und in einem `_entfernt` darunter,
    alt genug für das Einsortieren (60-s-Regel)."""
    dl = _dl(tmp_path, monkeypatch)
    dateien = []
    for ordner in (dl / "_Papierkorb", dl / "Stick" / "_entfernt"):
        ordner.mkdir(parents=True)
        d = ordner / "Weg [zzzzzz12345].mp3"
        d.write_bytes(b"WEG")
        os.utime(d, (1_000_000, 1_000_000))
        dateien.append(d)
    return dl, dateien


def test_rueckhol_ordner_sind_vom_index_ausgenommen(tmp_path, monkeypatch):
    _rueckhol_welt(tmp_path, monkeypatch)
    assert "zzzzzz12345" not in app._datei_index()
    assert app._finde_datei("https://www.youtube.com/watch?v=zzzzzz12345", {}) is None


def test_rueckhol_ordner_sind_vom_import_ausgenommen(tmp_path, monkeypatch):
    _rueckhol_welt(tmp_path, monkeypatch)
    monkeypatch.setattr(app, "_sag", lambda *a, **k: None)
    assert app.ordner_importieren() == 0
    assert not any(k.startswith("zzzzzz12345") for k in app._geladen)


def test_rueckhol_ordner_sind_vom_einsortieren_ausgenommen(tmp_path, monkeypatch):
    dl, dateien = _rueckhol_welt(tmp_path, monkeypatch)
    monkeypatch.setattr(app, "_sag", lambda *a, **k: None)
    monkeypatch.setitem(app.CFG, "unterordner", True)
    assert app.downloads_einsortieren() == 0
    assert all(d.is_file() for d in dateien)


def test_download_ordner_darf_selbst_so_heissen(tmp_path, monkeypatch):
    """Nur Ordner UNTER dem Download-Ordner sind ausgenommen: liegt er selbst
    in einem Ordner namens `_Papierkorb`, bleibt alles sichtbar."""
    dl = tmp_path / "_Papierkorb" / "dl"
    dl.mkdir(parents=True)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(dl))
    (dl / "Da [yyyyyy12345].mp3").write_bytes(b"DA")
    assert "yyyyyy12345" in app._datei_index()
    assert app._finde_datei("https://www.youtube.com/watch?v=yyyyyy12345", {}) == \
        str(dl / "Da [yyyyyy12345].mp3")


# ---------------------------------------------------------------- S5: Playlist-Spiegeln (unsichtbarer Teil)

A, B = "A [aaaaaa11111].mp3", "B [bbbbbb22222].mp3"
KA, KB = "aaaaaa11111|audio", "bbbbbb22222|audio"


def _sync_welt(tmp_path, monkeypatch, modus="spiegeln"):
    """Bibliothek mit zwei Titeln im Download-Ordner, Playlist mit beiden,
    Sync-Ziel `stick` außerhalb der Bibliothek."""
    dl = _dl(tmp_path, monkeypatch)
    (dl / "MP3").mkdir()
    for name, key, inhalt in ((A, KA, b"AAAA"), (B, KB, b"BBBBBB")):
        (dl / "MP3" / name).write_bytes(inhalt)
        app._geladen[key] = {"name": name, "pfad": str(dl / "MP3" / name)}
    stick = tmp_path / "stick"
    pl = {"id": "p1", "name": "P", "items": [KA, KB], "sync_ordner": str(stick),
          "sync_modus": modus}
    app._playlists.append(pl)
    return dl, stick, pl


def test_playlist_sync_kopiert(tmp_path, monkeypatch, entfernt):
    """Aufruf-Test (vorher rief kein Test playlist_sync)."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    r = app.playlist_sync(pl)
    assert r == {"ok": True, "kopiert": 2, "uebersprungen": 0, "geloescht": 0,
                 "fehler": 0, "im_ziel": 2}, r
    assert (stick / A).read_bytes() == b"AAAA" and (stick / B).read_bytes() == b"BBBBBB"
    r = app.playlist_sync(pl)
    assert r["kopiert"] == 0 and r["uebersprungen"] == 2
    assert not entfernt


def test_playlist_sync_entfernt_rueckholbar_nach_entfernt(tmp_path, monkeypatch, entfernt):
    """Spiegeln: ein aus der Playlist genommener Titel verlässt das Ziel in den
    Unterordner `_entfernt` statt per os.remove."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    app.playlist_sync(pl)
    pl["items"] = [KB]
    r = app.playlist_sync(pl)
    assert r["geloescht"] == 1 and not entfernt, entfernt
    assert not (stick / A).exists()
    assert (stick / "_entfernt" / A).read_bytes() == b"AAAA"
    assert (stick / B).is_file()
    assert (dl / "MP3" / A).is_file(), "das Original in der Bibliothek bleibt"


def test_playlist_sync_fremde_gleich_grosse_datei_bleibt(tmp_path, monkeypatch, entfernt):
    """Wurzel 1: eine schon vorhandene, gleich große Datei im Ziel ist nicht
    unsere Kopie. Vorher kam sie ins Merkblatt und wurde später gelöscht."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    stick.mkdir()
    (stick / A).write_bytes(b"XXXX")                  # fremd, gleiche Größe wie A
    app.playlist_sync(pl)
    pl["items"] = [KB]
    app.playlist_sync(pl)
    assert (stick / A).read_bytes() == b"XXXX", "fremde Datei im Ziel angefasst"
    assert not entfernt


def test_playlist_sync_neuer_zielordner_erbt_kein_merkblatt(tmp_path, monkeypatch, entfernt):
    """Wurzel 2: nach einem Wechsel des Zielordners galt das alte Merkblatt im
    neuen Ordner und traf dort gleichnamige fremde Dateien."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    app.playlist_sync(pl)
    neu = tmp_path / "handy"
    neu.mkdir()
    (neu / B).write_bytes(b"MEINE EIGENE KOPIE")
    pl["sync_ordner"] = str(neu)
    pl["items"] = [KA]
    app.playlist_sync(pl)
    assert (neu / B).read_bytes() == b"MEINE EIGENE KOPIE"
    assert not (neu / "_entfernt").exists() and not entfernt


def test_playlist_sync_fehlende_quelle_entfernt_nichts(tmp_path, monkeypatch, entfernt):
    """Wurzel 3: fehlt eine Quelle kurz (Platte ab, Datei umbenannt), galt der
    Titel als entfernt und wurde im Ziel gelöscht. Jetzt bleibt alles, und das
    Ergebnis nennt die fehlenden Quellen."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    app.playlist_sync(pl)
    (dl / "MP3" / A).rename(tmp_path / "weg.mp3")
    r = app.playlist_sync(pl)
    assert (stick / A).read_bytes() == b"AAAA"
    assert r.get("fehlend") == 1 and r["geloescht"] == 0
    assert not entfernt


def test_playlist_sync_fehlende_quelle_blockiert_auch_das_entfernen(tmp_path, monkeypatch,
                                                                    entfernt):
    """Fehlt irgendeine Quelle, wird in diesem Lauf nichts entfernt; der
    nächste vollständige Lauf holt es nach."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    app.playlist_sync(pl)
    (dl / "MP3" / A).rename(tmp_path / "weg.mp3")
    pl["items"] = [KA]                                # B wirklich entfernt, A fehlt kurz
    app.playlist_sync(pl)
    assert (stick / B).is_file()
    (tmp_path / "weg.mp3").rename(dl / "MP3" / A)
    r = app.playlist_sync(pl)
    assert r["geloescht"] == 1 and (stick / "_entfernt" / B).is_file()
    assert not entfernt


def test_playlist_sync_ordner_in_der_bibliothek_trifft_nie_das_original(tmp_path, monkeypatch,
                                                                        entfernt):
    """Liegt der Sync-Ordner dort, wo die Originale liegen, ist das Ziel die
    Quelle selbst: nie ins Merkblatt, nie entfernen."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    pl["sync_ordner"] = str(dl / "MP3")
    r = app.playlist_sync(pl)
    assert r["kopiert"] == 0 and r["uebersprungen"] == 2
    pl["items"] = [KB]
    app.playlist_sync(pl)
    assert (dl / "MP3" / A).read_bytes() == b"AAAA", "Original aus der Bibliothek entfernt"
    assert not (dl / "MP3" / "_entfernt").exists() and not entfernt


def test_playlist_sync_altes_merkblatt_wird_uebernommen(tmp_path, monkeypatch, entfernt):
    """Bestand vor der Umstellung: `sync_manifest` (Namensliste). Eine dort
    genannte, gleich große Kopie eines Titels der Playlist gilt weiter als
    unsere; entfernt JB den Titel, verlässt sie das Ziel wie bisher (jetzt
    rückholbar). Die alte Liste verschwindet aus der Playlist."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    stick.mkdir()
    (stick / A).write_bytes(b"AAAA")
    (stick / B).write_bytes(b"BBBBBB")
    pl["sync_manifest"] = [A, B]
    app.playlist_sync(pl)
    assert "sync_manifest" not in pl
    pl["items"] = [KB]
    r = app.playlist_sync(pl)
    assert r["geloescht"] == 1 and (stick / "_entfernt" / A).read_bytes() == b"AAAA"
    assert not entfernt


def test_playlist_sync_kopieren_entfernt_nie(tmp_path, monkeypatch, entfernt):
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch, modus="kopieren")
    app.playlist_sync(pl)
    pl["items"] = [KB]
    r = app.playlist_sync(pl)
    assert r["geloescht"] == 0 and (stick / A).is_file() and not entfernt


def test_auto_sync_merkt_unvollstaendigen_lauf_nicht(tmp_path, monkeypatch, entfernt):
    """Auto-Sync merkte sich die Signatur auch nach einem Lauf mit fehlender
    Quelle; danach kopierte er nie wieder, bis sich die Playlist änderte."""
    monkeypatch.setattr(app, "_auto_sync_stand", {})
    if hasattr(app, "_auto_sync_nachholen"):
        monkeypatch.setattr(app, "_auto_sync_nachholen", {})
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    pl["sync_auto"] = True
    stick.mkdir()
    (dl / "MP3" / A).rename(tmp_path / "weg.mp3")
    uhr = [1_000_000.0]
    monkeypatch.setattr(app.time, "time", lambda: uhr[0])
    app.auto_sync_pruefen()
    assert (stick / B).is_file() and not (stick / A).exists()
    (tmp_path / "weg.mp3").rename(dl / "MP3" / A)     # Platte wieder da
    uhr[0] += 3600
    app.auto_sync_pruefen()
    assert (stick / A).read_bytes() == b"AAAA", "fehlende Quelle wurde nie nachkopiert"


def test_playlist_sync_umbenannter_titel_alte_kopie_geht(tmp_path, monkeypatch, entfernt):
    """Wie bisher beim Spiegeln: heißt ein Titel in der Bibliothek neu, geht
    die Kopie unter dem alten Namen aus dem Ziel (jetzt rückholbar)."""
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    app.playlist_sync(pl)
    neu_name = "A neu [aaaaaa11111].mp3"
    (dl / "MP3" / A).rename(dl / "MP3" / neu_name)
    app._geladen[KA]["pfad"] = str(dl / "MP3" / neu_name)
    r = app.playlist_sync(pl)
    assert (stick / neu_name).is_file() and not (stick / A).exists()
    assert (stick / "_entfernt" / A).is_file() and r["geloescht"] == 1
    assert not entfernt


def test_auto_sync_versucht_unvollstaendig_erst_nach_pause(tmp_path, monkeypatch):
    """Solange eine Quelle fehlt, läuft der Auto-Sync nicht in jedem 5-s-Takt
    (jeder Lauf durchsucht den Download-Ordner), sondern frühestens nach
    AUTO_SYNC_NACHHOL_S; eine geänderte Playlist läuft sofort."""
    monkeypatch.setattr(app, "_auto_sync_stand", {})
    monkeypatch.setattr(app, "_auto_sync_nachholen", {})
    dl, stick, pl = _sync_welt(tmp_path, monkeypatch)
    pl["sync_auto"] = True
    stick.mkdir()
    (dl / "MP3" / A).rename(tmp_path / "weg.mp3")
    laeufe = []
    echt = app.playlist_sync
    monkeypatch.setattr(app, "playlist_sync", lambda p: laeufe.append(1) or echt(p))
    uhr = [1_000_000.0]
    monkeypatch.setattr(app.time, "time", lambda: uhr[0])
    app.auto_sync_pruefen()
    uhr[0] += 5
    app.auto_sync_pruefen()
    assert len(laeufe) == 1, "unvollständiger Lauf wiederholt sich in jedem Takt"
    pl["items"] = [KA]                                # Playlist geändert: sofort
    app.auto_sync_pruefen()
    assert len(laeufe) == 2
    uhr[0] += app.AUTO_SYNC_NACHHOL_S + 1
    app.auto_sync_pruefen()
    assert len(laeufe) == 3
