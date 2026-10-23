# -*- coding: utf-8 -*-
"""Nur tmp_path; Prozesse/Port werden ersetzt, keine laufende App wird berührt."""
import errno
import json
import types

import pytest

from tools import bibliothek_zusammenfuehren as werkzeug


def _json(pfad, daten):
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")


def _welt(tmp_path, quelle, ziel):
    (tmp_path / "System").mkdir()
    _json(tmp_path / "geladen_log.json", quelle)
    _json(tmp_path / "System" / "geladen_log.json", ziel)
    return tmp_path


def _datei(tmp_path, name="neu.mp4"):
    pfad = tmp_path / name
    pfad.write_bytes(b"Medieninhalt")
    return str(pfad)


def _bestand(pfad):
    return {str(p.relative_to(pfad)): p.read_bytes() for p in pfad.rglob("*") if p.is_file()}


def test_standard_ist_reiner_probelauf_mit_echtem_neuen_eintrag(tmp_path, monkeypatch, capsys):
    datei = _datei(tmp_path)
    _welt(tmp_path, {"neu|beste": {"pfad": datei, "titel": "Über den Wolken"}}, {})
    vorher = _bestand(tmp_path)
    monkeypatch.setattr(werkzeug, "stillstand_pruefen", lambda: pytest.fail("Probelauf prüft keine Prozesse"))
    assert werkzeug.main(["--programm", str(tmp_path)]) == 0
    bericht = json.loads(capsys.readouterr().out)
    assert bericht["modus"] == "Probelauf"
    assert bericht["neu"] == ["neu|beste"]
    assert bericht["anzahl"] == {"neu": 1, "dubletten": 0, "konflikte": 0}
    assert _bestand(tmp_path) == vorher


@pytest.mark.parametrize("nach_fp", [False, True])
def test_reimporte_werden_nach_windows_pfad_oder_fp_nicht_doppelt_aufgenommen(tmp_path, nach_fp):
    alt = {"pfad": r"C:\Downloads\Lied.mp3", "fp": "bekannt", "titel": "Reicher Titel",
           "uploader": "Kanal", "dauer": 123, "plays": 7, "ts": 10}
    reimport = {"pfad": r"c:/downloads/LIED.mp3", "ts": 20, "importiert": True}
    if nach_fp:
        reimport.update(pfad=r"C:\Andere\Kopie.mp3", fp="bekannt")
    _welt(tmp_path, {"lokal|lokal": reimport}, {"video|audio": alt})
    plan = werkzeug.planen(tmp_path)
    assert set(plan["ergebnis"]) == {"video|audio"}
    assert plan["ergebnis"]["video|audio"]["uploader"] == "Kanal"
    assert plan["ergebnis"]["video|audio"]["plays"] == 7
    assert plan["ergebnis"]["video|audio"]["ts"] == 10
    assert "importiert" not in plan["ergebnis"]["video|audio"]
    assert plan["bericht"]["dubletten"] == [{"quelle": "lokal|lokal", "ziel": "video|audio"}]


def test_vollstaendigere_quelle_gewinnt_metadaten_und_erhaelt_zaehler_und_unterfelder(tmp_path):
    quelle = {"titel": "Vollständiger Titel", "uploader": "Kanal", "dauer": 60,
              "album": "Album", "genre": "Pop", "plays": 2, "last_play": 30,
              "wiedergabe": {"tempo": 1.1}, "ts": 20}
    ziel = {"titel": "Alter Titel", "plays": 12, "last_play": 25, "ts": 10,
            "wiedergabe": {"sub_offset": -0.1}, "blacklist": True}
    _welt(tmp_path, {"id|audio": quelle}, {"id|audio": ziel})
    plan = werkzeug.planen(tmp_path)
    e = plan["ergebnis"]["id|audio"]
    assert e["titel"] == "Vollständiger Titel" and e["blacklist"] is True
    assert (e["plays"], e["last_play"], e["ts"]) == (12, 30, 10)
    assert e["wiedergabe"] == {"sub_offset": -0.1, "tempo": 1.1}
    assert plan["bericht"]["konflikte"][0]["felder"]


def test_exakter_schluessel_biegt_original_nicht_auf_clip_fingerprint_um(tmp_path):
    quelle = {"pfad": r"C:\Medien\Original.mp3", "fp": "clip-fp", "titel": "vollständig",
              "uploader": "Kanal", "dauer": 80, "album": "Album", "plays": 5}
    original = {"pfad": quelle["pfad"], "fp": "original-fp", "plays": 12}
    clip = {"pfad": r"C:\Medien\Ausschnitt.mp3", "fp": "clip-fp", "dauer": 10}
    _welt(tmp_path, {"id|audio": quelle}, {"id|audio": original, "id|clipabc": clip})
    plan = werkzeug.planen(tmp_path)
    assert plan["ergebnis"]["id|audio"]["fp"] == "original-fp"
    assert plan["ergebnis"]["id|audio"]["titel"] == "vollständig"
    assert plan["ergebnis"]["id|audio"]["plays"] == 12
    assert plan["ergebnis"]["id|clipabc"] == clip
    assert plan["bericht"]["konflikte"][0]["weitere_pfad_fp_treffer"] == ["id|clipabc"]


def test_mehrdeutige_identitaet_ohne_exakten_schluessel_bleibt_offen(tmp_path):
    _welt(tmp_path, {"lokal": {"fp": "gleich", "plays": 5}},
          {"original": {"fp": "gleich", "plays": 1}, "clip": {"fp": "gleich", "plays": 2}})
    plan = werkzeug.planen(tmp_path)
    assert plan["ergebnis"] == plan["ziel_daten"]
    assert plan["bericht"]["nicht_uebernommen"] == ["lokal"]
    assert plan["bericht"]["konflikte"][0]["ziele"] == ["clip", "original"]


def test_unbekannte_altlast_ohne_datei_wird_als_konflikt_gemeldet(tmp_path):
    _welt(tmp_path, {"alt": {"pfad": str(tmp_path / "geloeschter-trailer.mp4"), "ts": 1}}, {})
    plan = werkzeug.planen(tmp_path)
    assert plan["ergebnis"] == {}
    assert plan["bericht"]["neu"] == []
    assert plan["bericht"]["nicht_uebernommen"] == ["alt"]
    assert "Datei fehlt" in plan["bericht"]["konflikte"][0]["aktion"]


def test_neue_quelle_mit_zwei_ids_fuer_selbe_datei_wird_nur_einmal_aufgenommen(tmp_path):
    datei = _datei(tmp_path)
    _welt(tmp_path, {"neu": {"pfad": datei}, "lokal": {"pfad": datei, "dauer": 42}}, {})
    plan = werkzeug.planen(tmp_path)
    assert list(plan["ergebnis"]) == ["neu"]
    assert plan["ergebnis"]["neu"]["dauer"] == 42
    assert plan["bericht"]["neu"] == ["neu"]
    assert len(plan["bericht"]["dubletten"]) == 1


def test_config_queue_filme_werden_nur_benannt_und_nicht_uebernommen(tmp_path, capsys):
    _welt(tmp_path, {}, {})
    for name in ("config.json", "warteschlange.json", "filme_zustand.json", "filme_katalog.json"):
        _json(tmp_path / name, {"geheim": "QUELL-PASSWORT", "wert": 2})
        _json(tmp_path / "System" / name, {"geheim": "ZIEL-PASSWORT", "wert": 1})
    vorher = _bestand(tmp_path)
    assert werkzeug.main(["--programm", str(tmp_path)]) == 0
    ausgabe = capsys.readouterr().out
    bericht = json.loads(ausgabe)
    assert {e["datei"] for e in bericht["andere_dateien"]} == {
        "config.json", "warteschlange.json", "filme_zustand.json", "filme_katalog.json"}
    assert all(e["vorschlag"] for e in bericht["andere_dateien"])
    assert "PASSWORT" not in ausgabe
    assert _bestand(tmp_path) == vorher


def test_apply_sichert_original_exklusiv_und_schreibt_nur_ueber_familie(tmp_path, monkeypatch):
    _welt(tmp_path, {"neu": {"pfad": _datei(tmp_path)}}, {"alt": {"plays": 8}})
    _json(tmp_path / "config.json", {"wert": "unbestätigt"})
    monkeypatch.setattr(werkzeug, "stillstand_pruefen", lambda: None)
    original = (tmp_path / "System" / "geladen_log.json").read_bytes()
    quellbytes = (tmp_path / "geladen_log.json").read_bytes()
    schreiben = werkzeug.fam.json_aendern
    aufrufe = []

    def familie(pfad, aenderung, **kwargs):
        aufrufe.append((pfad, kwargs))
        return schreiben(pfad, aenderung, **kwargs)

    monkeypatch.setattr(werkzeug.fam, "json_aendern", familie)
    sicherung = werkzeug.anwenden(werkzeug.planen(tmp_path))
    assert sicherung.read_bytes() == original
    assert ".vor-zusammenfuehrung-" in sicherung.name and sicherung.suffix == ".bak"
    assert set(json.loads((tmp_path / "System" / "geladen_log.json").read_text(encoding="utf-8"))) == {"alt", "neu"}
    assert (tmp_path / "geladen_log.json").read_bytes() == quellbytes
    assert not (tmp_path / "System" / "config.json").exists()
    assert len(aufrufe) == 1 and aufrufe[0][1]["streng"] is True
    nachher = _bestand(tmp_path)
    assert werkzeug.anwenden(werkzeug.planen(tmp_path)) is None
    assert _bestand(tmp_path) == nachher


@pytest.mark.parametrize("welche", ["quelle", "ziel"])
def test_apply_verweigert_zwischenzeitlich_geaenderten_bestand(tmp_path, monkeypatch, welche):
    _welt(tmp_path, {"neu": {"pfad": _datei(tmp_path)}}, {})
    plan = werkzeug.planen(tmp_path)
    _json(plan[welche], {"fremd": {"titel": "inzwischen geändert"}})
    vorher = _bestand(tmp_path)
    monkeypatch.setattr(werkzeug, "stillstand_pruefen", lambda: None)
    with pytest.raises(werkzeug.ZusammenfuehrungAbgelehnt, match="Bestand seit"):
        werkzeug.anwenden(plan)
    assert _bestand(tmp_path) == vorher


def test_apply_verweigert_laufende_app_ohne_backup_oder_schreiben(tmp_path, monkeypatch, capsys):
    _welt(tmp_path, {"neu": {"pfad": _datei(tmp_path)}}, {})
    vorher = _bestand(tmp_path)

    def laeuft():
        raise werkzeug.ZusammenfuehrungAbgelehnt("SyncYouTube.exe läuft")

    monkeypatch.setattr(werkzeug, "stillstand_pruefen", laeuft)
    assert werkzeug.main(["--programm", str(tmp_path), "--apply"]) == 2
    assert "läuft" in capsys.readouterr().err
    assert _bestand(tmp_path) == vorher


def test_appstart_zwischen_plan_und_schreiben_verweigert_apply(tmp_path, monkeypatch):
    _welt(tmp_path, {"neu": {"pfad": _datei(tmp_path)}}, {})
    vorher = _bestand(tmp_path)
    pruefungen = []

    def stillstand():
        pruefungen.append(True)
        if len(pruefungen) == 2:
            raise werkzeug.ZusammenfuehrungAbgelehnt("inzwischen gestartet")

    monkeypatch.setattr(werkzeug, "stillstand_pruefen", stillstand)
    with pytest.raises(werkzeug.ZusammenfuehrungAbgelehnt, match="inzwischen gestartet"):
        werkzeug.anwenden(werkzeug.planen(tmp_path))
    assert len(pruefungen) == 2
    assert _bestand(tmp_path) == vorher


def test_bestehende_sicherung_wird_niemals_ueberschrieben(tmp_path, monkeypatch):
    _welt(tmp_path, {"neu": {"pfad": _datei(tmp_path)}}, {})
    feste_zeit = types.SimpleNamespace(strftime=lambda muster: "20261023-120000-000001")
    monkeypatch.setattr(werkzeug.datetime, "datetime", types.SimpleNamespace(now=lambda: feste_zeit))
    monkeypatch.setattr(werkzeug, "stillstand_pruefen", lambda: None)
    sicherung = tmp_path / "System" / "geladen_log.json.vor-zusammenfuehrung-20261023-120000-000001.bak"
    sicherung.write_bytes(b"vorhandene Sicherung")
    vorher = _bestand(tmp_path)
    with pytest.raises(FileExistsError):
        werkzeug.anwenden(werkzeug.planen(tmp_path))
    assert _bestand(tmp_path) == vorher


def test_apply_meldet_familie_schreibfehler_und_behaelt_sicherung(tmp_path, monkeypatch):
    _welt(tmp_path, {"neu": {"pfad": _datei(tmp_path)}}, {})
    monkeypatch.setattr(werkzeug, "stillstand_pruefen", lambda: None)
    monkeypatch.setattr(werkzeug.fam, "json_schreiben", lambda *args: False)
    with pytest.raises(werkzeug.ZusammenfuehrungAbgelehnt, match="Schreiben fehlgeschlagen"):
        werkzeug.anwenden(werkzeug.planen(tmp_path))
    sicherungen = list((tmp_path / "System").glob("*.bak"))
    assert len(sicherungen) == 1 and sicherungen[0].read_bytes() == b"{}"
    assert (tmp_path / "System" / "geladen_log.json").read_bytes() == b"{}"


@pytest.mark.parametrize("inhalt", ["{kaputt", "[]", '{"key": 42}', '{"key": {"fp": 42}}'])
def test_ungueltige_bibliothek_wird_nicht_heilgeheilt(tmp_path, inhalt):
    _welt(tmp_path, {}, {})
    (tmp_path / "System" / "geladen_log.json").write_text(inhalt, encoding="utf-8")
    vorher = _bestand(tmp_path)
    with pytest.raises(werkzeug.ZusammenfuehrungAbgelehnt):
        werkzeug.planen(tmp_path)
    assert _bestand(tmp_path) == vorher


def _windows_pruefung(monkeypatch, stdout="[]", fehler=None, belegt=None):
    monkeypatch.setattr(werkzeug, "os", types.SimpleNamespace(name="nt"))
    monkeypatch.setattr(werkzeug.subprocess, "CREATE_NO_WINDOW", 0, raising=False)

    def prozesse(args, **kwargs):
        assert "Get-CimInstance Win32_Process" in args[-1]
        assert "SyncYouTube.exe" in args[-1] and "youtube_app\\.py" in args[-1]
        if fehler:
            raise fehler
        return types.SimpleNamespace(stdout=stdout)

    class Socket:
        def __init__(self, familie, typ):
            self.familie = familie

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def setsockopt(self, *args):
            pass

        def bind(self, adresse):
            assert adresse[1] == 8776
            if self.familie == belegt:
                raise OSError(errno.EADDRINUSE, "belegt")

    monkeypatch.setattr(werkzeug.subprocess, "run", prozesse)
    monkeypatch.setattr(werkzeug.socket, "SO_EXCLUSIVEADDRUSE", 0, raising=False)
    monkeypatch.setattr(werkzeug.socket, "socket", Socket)


@pytest.mark.parametrize("stdout", ['["SyncYouTube.exe (PID 123)"]', '["pythonw.exe (PID 234)"]',
                                    "kein JSON", "null", "{}"])
def test_prozesspruefung_verweigert_laufende_app_und_unsichere_antwort(monkeypatch, stdout):
    _windows_pruefung(monkeypatch, stdout=stdout)
    with pytest.raises(werkzeug.ZusammenfuehrungAbgelehnt):
        werkzeug.stillstand_pruefen()


def test_prozesspruefung_verweigert_abfragefehler(monkeypatch):
    _windows_pruefung(monkeypatch, fehler=OSError("CIM nicht erreichbar"))
    with pytest.raises(werkzeug.ZusammenfuehrungAbgelehnt, match="nicht sicher prüfbar"):
        werkzeug.stillstand_pruefen()


@pytest.mark.parametrize("familie", [werkzeug.socket.AF_INET, werkzeug.socket.AF_INET6])
def test_portpruefung_verweigert_ipv4_oder_ipv6_listener(monkeypatch, familie):
    _windows_pruefung(monkeypatch, belegt=familie)
    with pytest.raises(werkzeug.ZusammenfuehrungAbgelehnt, match="Port 8776"):
        werkzeug.stillstand_pruefen()


def test_leere_prozessliste_und_freier_port_lassen_pruefung_passieren(monkeypatch):
    _windows_pruefung(monkeypatch)
    werkzeug.stillstand_pruefen()
