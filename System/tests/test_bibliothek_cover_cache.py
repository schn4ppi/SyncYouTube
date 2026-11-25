# -*- coding: utf-8 -*-
"""Bildspuren nur bei Dateiänderung erneut extrahieren; Speicher bleibt begrenzt."""
import io
import os
import types

import pytest

import youtube_app as app


@pytest.fixture
def bildspur(monkeypatch, tmp_path):
    datei = tmp_path / "Video.mp4"
    datei.write_bytes(b"Videodatei")
    key = "lokal-cover|lokal"
    monkeypatch.setattr(app, "_geladen", {key: {"pfad": str(datei), "cover_stream": 2}})
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app, "_ffmpeg_exe", lambda: "ffmpeg.exe")
    monkeypatch.setattr(app, "_cover_bildspur_cache", {})
    aufrufe = []

    def ffmpeg(args, **kwargs):
        aufrufe.append(args)
        return types.SimpleNamespace(returncode=0, stdout=b"JPEG")

    monkeypatch.setattr(app.subprocess, "run", ffmpeg)
    return key, datei, aufrufe


def test_wiederholte_coverabrufe_starten_ffmpeg_nur_einmal(bildspur):
    key, datei, aufrufe = bildspur
    for _ in range(66):
        assert app.cover_aus_datei(key) == b"JPEG"
    assert len(aufrufe) == 1
    assert datei.read_bytes() == b"Videodatei"


@pytest.mark.parametrize("aenderung", ["groesse", "mtime", "pfad", "stream"])
def test_geaenderte_datei_oder_bildspur_wird_neu_gelesen(bildspur, aenderung):
    key, datei, aufrufe = bildspur
    assert app.cover_aus_datei(key) == b"JPEG"
    vorher = datei.stat()
    if aenderung == "groesse":
        datei.write_bytes(b"Videodatei mit neuen Tags")
        os.utime(datei, ns=(vorher.st_atime_ns, vorher.st_mtime_ns))
    elif aenderung == "mtime":
        os.utime(datei, ns=(vorher.st_atime_ns, vorher.st_mtime_ns + 2_000_000_000))
    elif aenderung == "pfad":
        andere = datei.with_name("Anderes Video.mp4")
        andere.write_bytes(datei.read_bytes())
        os.utime(andere, ns=(vorher.st_atime_ns, vorher.st_mtime_ns))
        app._geladen[key]["pfad"] = str(andere)
    else:
        app._geladen[key]["cover_stream"] = 3
    assert app.cover_aus_datei(key) == b"JPEG"
    assert len(aufrufe) == 2


def test_cache_behaelt_zuletzt_benutzte_bilder_bis_zur_obergrenze(monkeypatch, bildspur):
    key, datei, aufrufe = bildspur
    monkeypatch.setattr(app, "_COVER_BILDSPUR_MAX", 2)
    for anderer in ("zweites|lokal", "drittes|lokal"):
        app._geladen[anderer] = {"pfad": str(datei), "cover_stream": 2}
    for aktuell in (key, "zweites|lokal", key, "drittes|lokal", key):
        assert app.cover_aus_datei(aktuell) == b"JPEG"
    assert len(aufrufe) == 3
    assert app.cover_aus_datei("zweites|lokal") == b"JPEG"
    assert len(aufrufe) == 4
    assert len(app._cover_bildspur_cache) == 2


def test_cache_ist_auch_in_bytes_begrenzt(monkeypatch, bildspur):
    key, datei, aufrufe = bildspur
    monkeypatch.setattr(app, "_COVER_BILDSPUR_BYTES", 6)
    app._geladen["zweites|lokal"] = {"pfad": str(datei), "cover_stream": 2}
    for aktuell in (key, "zweites|lokal", key):
        assert app.cover_aus_datei(aktuell) == b"JPEG"
    assert len(aufrufe) == 3
    assert sum(map(len, app._cover_bildspur_cache.values())) <= 6


def test_uebergrosses_bild_wird_geliefert_aber_nicht_gepuffert(monkeypatch, bildspur):
    key, _, aufrufe = bildspur
    monkeypatch.setattr(app, "_COVER_BILDSPUR_BYTES", 3)
    assert app.cover_aus_datei(key) == b"JPEG"
    assert app.cover_aus_datei(key) == b"JPEG"
    assert len(aufrufe) == 2 and not app._cover_bildspur_cache


def test_ffmpeg_fehler_wird_beim_naechsten_abruf_erneut_versucht(monkeypatch, bildspur):
    key, _, _ = bildspur
    antworten = iter([types.SimpleNamespace(returncode=1, stdout=b""),
                      types.SimpleNamespace(returncode=0, stdout=b"JPEG")])
    monkeypatch.setattr(app.subprocess, "run", lambda *a, **k: next(antworten))
    assert app.cover_aus_datei(key) is None
    assert app.cover_aus_datei(key) == b"JPEG"
    assert app.cover_aus_datei(key) == b"JPEG"


def test_neues_sidecar_hat_vorrang_vor_gepufferter_bildspur(bildspur):
    key, datei, aufrufe = bildspur
    assert app.cover_aus_datei(key) == b"JPEG"
    cover = datei.parent / "Cover" / "lokal-cover.jpg"
    cover.parent.mkdir()
    cover.write_bytes(b"Neues Albumcover")
    assert app.cover_aus_datei(key) == b"Neues Albumcover"
    assert len(aufrufe) == 1


def test_cover_antwort_erlaubt_weiterhin_eine_stunde_browsercache(monkeypatch):
    monkeypatch.setattr(app, "cover_aus_datei", lambda key: b"JPEG")
    kopf, codes = {}, []
    handler = types.SimpleNamespace(
        path="/api/cover?id=lokal-cover%7Clokal", headers={}, wfile=io.BytesIO(),
        send_response=lambda code: codes.append(code),
        send_header=lambda name, wert: kopf.update({name: wert}),
        end_headers=lambda: None)
    app.Handler._get_cover(handler)
    assert codes == [200] and handler.wfile.getvalue() == b"JPEG"
    assert kopf["Cache-Control"] == "max-age=3600"
