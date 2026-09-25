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
    (dl / "Cover").mkdir(parents=True)
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
