# -*- coding: utf-8 -*-
"""Importe nutzen vorhandene Datei-Infos, ohne Medien/Schlüssel umzuschreiben.

Alle Dateien liegen in tmp_path; ffprobe/ffmpeg und Netz werden ersetzt.
Bestandsfall: lokale Import-ID, aber Quelladresse und Bild IN der MP4.
"""
import json
import os
import sys
import types
from urllib.parse import parse_qs, urlparse

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402


def _probe(monkeypatch, url="https://www.youtube.com/watch?v=FTQbiNvZqaY"):
    daten = {
        "format": {"duration": "271.123", "tags": {"artist": "TOTO", "comment": url}},
        "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264", "height": 1080},
            {"index": 1, "codec_type": "audio", "codec_name": "aac", "sample_rate": "44100"},
            {"index": 2, "codec_type": "video", "codec_name": "mjpeg", "height": 360,
             "disposition": {"attached_pic": 1}},
        ],
    }
    monkeypatch.setattr(app, "_ffmpeg_exe", lambda: "ffmpeg.exe")
    def ffprobe(args, **kw):
        assert kw["encoding"] == "utf-8", "Datei-Tags sind auch unter Windows UTF-8"
        assert "format_tags=artist,comment,purl" in args[args.index("-show_entries") + 1]
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(daten, ensure_ascii=False))

    monkeypatch.setattr(app.subprocess, "run", ffprobe)
    return daten


def _datei(tmp_path):
    datei = tmp_path / "Toto - Africa (Official HD Video).mp4"
    datei.write_bytes(b"Unveraenderte Videodatei")
    return datei


def test_probe_liest_quelle_dauer_kanal_und_bildspur(monkeypatch, tmp_path):
    _probe(monkeypatch)
    t = app._technik(str(_datei(tmp_path)))
    assert t["quell_id"] == "FTQbiNvZqaY"
    assert t["url"] == "https://www.youtube.com/watch?v=FTQbiNvZqaY"
    assert t["dauer"] == pytest.approx(271.123)
    assert t["uploader"] == "TOTO"
    assert t["cover_stream"] == 2
    assert (t["vcodec"], t["height"]) == ("h264", 1080)


@pytest.mark.parametrize("url", ["", "https://youtube.com.fremd.de/watch?v=FTQbiNvZqaY",
                               "https://example.org/?v=FTQbiNvZqaY",
                               "Quelle: https://www.youtube.com/watch?v=FTQbiNvZqaY"])
def test_fremde_oder_freie_texte_ergeben_keine_quell_id(monkeypatch, tmp_path, url):
    _probe(monkeypatch, url)
    assert "quell_id" not in app._technik(str(_datei(tmp_path)))


def test_purl_und_fehlende_dauer_sind_zulaessig(monkeypatch, tmp_path):
    daten = _probe(monkeypatch, "")
    daten["format"] = {"duration": "N/A", "tags": {"PURL": "https://youtu.be/FTQbiNvZqaY"}}
    t = app._technik(str(_datei(tmp_path)))
    assert t["quell_id"] == "FTQbiNvZqaY" and "dauer" not in t


def test_fehlgeschlagene_probe_wird_beim_naechsten_backfill_wiederholt(monkeypatch, tmp_path):
    _probe(monkeypatch)
    datei = _datei(tmp_path)
    e = {"pfad": str(datei), "importiert": True, "acodec": "aac", "idtag": False,
         "fp": app._datei_fp(str(datei))}
    monkeypatch.setattr(app, "_geladen", {"lokal-abc|lokal": e})
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app.subprocess, "run", lambda *a, **k: types.SimpleNamespace(
        returncode=1, stdout="{}"))
    app.technik_backfill()
    assert "datei_metadaten" not in e and "quell_id" not in e
    _probe(monkeypatch)
    app.technik_backfill()
    assert e["datei_metadaten"] is True and e["quell_id"] == "FTQbiNvZqaY"


def test_backfill_heilt_import_trotz_vorhandener_codecs_einmalig(monkeypatch, tmp_path):
    _probe(monkeypatch)
    datei = _datei(tmp_path)
    key = "lokal-3683d75ff40|lokal"
    e = {"pfad": str(datei), "name": datei.name, "titel": "Eigener Titel", "importiert": True,
         "acodec": "aac", "fp": app._datei_fp(str(datei)), "idtag": False, "plays": 7}
    monkeypatch.setattr(app, "_geladen", {key: e})
    monkeypatch.setattr(app, "_playlists", [{"items": [key]}])
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    geschrieben = []
    monkeypatch.setattr(app, "_geladen_speichern", lambda: geschrieben.append(True))
    app.technik_backfill()
    assert list(app._geladen) == [key] and app._playlists[0]["items"] == [key]
    assert e["titel"] == "Eigener Titel" and e["plays"] == 7
    assert e["dauer"] == pytest.approx(271.123) and e["uploader"] == "TOTO"
    assert e["quell_id"] == "FTQbiNvZqaY" and e["cover_stream"] == 2
    assert datei.read_bytes() == b"Unveraenderte Videodatei"
    assert e["fp"] == app._datei_fp(str(datei))
    assert len(geschrieben) == 1
    monkeypatch.setattr(app, "_technik", lambda p: pytest.fail("Import wurde erneut geprüft"))
    app.technik_backfill()
    assert len(geschrieben) == 1
    kachel = app.bibliothek_liste()[0]
    assert parse_qs(urlparse(kachel["thumb"]).query) == {"id": [key]}


def test_uebernahme_ueberschreibt_keine_bestehenden_angaben():
    e = {"dauer": 42, "uploader": "Eigener Kanal", "url": "https://example.org/original"}
    app._datei_metadaten_uebernehmen(e, {"dauer": 271, "uploader": "TOTO", "url": "neu"})
    assert (e["dauer"], e["uploader"], e["url"]) == (42, "Eigener Kanal", "https://example.org/original")


def test_neuer_import_hat_metadaten_sofort(monkeypatch, tmp_path):
    _probe(monkeypatch)
    datei = _datei(tmp_path)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app, "_id_tag_lesen", lambda p: "")
    monkeypatch.setattr(app, "_geladen", {})
    monkeypatch.setitem(app.CFG, "auto_umbenennen", False)
    assert app.ordner_importieren() == 1
    e = next(iter(app._geladen.values()))
    assert e["pfad"] == str(datei) and e["uploader"] == "TOTO" and e["dauer"] > 271
    assert e["quell_id"] == "FTQbiNvZqaY" and e["datei_metadaten"] is True
    assert app.ordner_importieren() == 0
    assert datei.read_bytes() == b"Unveraenderte Videodatei"


def test_ohne_lokalbild_nutzt_import_die_echte_quell_id(monkeypatch, tmp_path):
    datei = _datei(tmp_path)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app, "_geladen", {"lokal-abc|lokal": {
        "pfad": str(datei), "quell_id": "FTQbiNvZqaY"}})
    assert app.bibliothek_liste()[0]["thumb"] == "https://i.ytimg.com/vi/FTQbiNvZqaY/mqdefault.jpg"


@pytest.mark.parametrize("eigenes_cover", [False, True])
def test_cover_ordner_wird_ueber_quell_id_wieder_gefunden(monkeypatch, tmp_path, eigenes_cover):
    datei = _datei(tmp_path)
    cover = tmp_path / "Cover" / "FTQbiNvZqaY.jpg"
    cover.parent.mkdir()
    cover.write_bytes(b"vorhandenes JPEG")
    if eigenes_cover:
        (cover.parent / "lokal-abc.jpg").write_bytes(b"eigenes Cover")
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app, "_geladen", {"lokal-abc|lokal": {
        "pfad": str(datei), "quell_id": "FTQbiNvZqaY"}})
    monkeypatch.setattr(app.subprocess, "run", lambda *a, **k: pytest.fail("Bild liegt schon vor"))
    assert app.cover_aus_datei("lokal-abc|lokal") == (b"eigenes Cover" if eigenes_cover else b"vorhandenes JPEG")
    assert app.bibliothek_liste()[0]["thumb"].startswith("/api/cover?")


@pytest.mark.parametrize("fehler", [False, True])
def test_eingebettetes_bild_nur_lesen_keine_mediendatei_schreiben(monkeypatch, tmp_path, fehler):
    datei = _datei(tmp_path)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app, "_geladen", {"lokal-abc|lokal": {"pfad": str(datei), "cover_stream": 2}})
    monkeypatch.setattr(app, "_ffmpeg_exe", lambda: "ffmpeg.exe")
    aufrufe = []

    def ffmpeg(args, **kw):
        aufrufe.append(args)
        return types.SimpleNamespace(returncode=1 if fehler else 0, stdout=b"JPEG")

    monkeypatch.setattr(app.subprocess, "run", ffmpeg)
    assert app.cover_aus_datei("lokal-abc|lokal") == (None if fehler else b"JPEG")
    assert aufrufe[0][-1] == "pipe:1" and "0:2" in aufrufe[0]
    assert str(datei) == aufrufe[0][aufrufe[0].index("-i") + 1]
    assert datei.read_bytes() == b"Unveraenderte Videodatei"


def test_ohne_bildspur_wird_keine_videospur_extrahiert(monkeypatch, tmp_path):
    datei = _datei(tmp_path)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app, "_geladen", {"lokal-abc|lokal": {"pfad": str(datei)}})
    monkeypatch.setattr(app.subprocess, "run", lambda *a, **k: pytest.fail("Keine Bildspur bekannt"))
    assert app.cover_aus_datei("lokal-abc|lokal") is None
