# -*- coding: utf-8 -*-
"""Lösch- und Pfadlücken (Gesamtprüfung 25.09.2026, Gruppe 2).

Jeder Test hier fährt die echte Funktion mit Werten, wie sie ein Client
schicken kann: `..\\x`, ein absoluter Pfad, ein UNC-Pfad und ein gültiger
Wert. Der Papierkorb ist in jedem Test eine Attrappe (der echte ginge in JBs
Windows-Papierkorb), und UNC-Pfade erreichen nie das Netz: ein Zugriff darauf
wird vorher abgefangen und gezählt.
"""
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402

UNC = "\\\\server\\freigabe\\x"


def _unter(pfad, wurzel):
    pfad = os.path.normcase(os.path.abspath(pfad))
    wurzel = os.path.normcase(os.path.abspath(wurzel))
    return pfad == wurzel or pfad.startswith(wurzel.rstrip(os.sep) + os.sep)


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
