# -*- coding: utf-8 -*-
"""JB-Entscheid 25.09.2026 (Gesamtprüfung, Frage 4): Ein Playlist-Sync-Ziel in
der Bibliothek oder auf einem Netzwerkpfad wird beim Einrichten mit klarer
Meldung abgelehnt. Bestehende Einrichtungen laufen weiter; dort schützt schon
der Abgleich „Ziel ist die Quelldatei selbst“ die Originale.

Die Prüfung ist rein textlich: Sie fasst den Pfad nicht an, denn schon ein
`os.path.isdir` auf einen UNC-Pfad öffnet eine Netzverbindung.
"""
import json
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

import youtube_app as app  # noqa: E402
from test_medientasten_verhalten import _js_funktion, _lauf, _pc  # noqa: E402
from test_zugang_und_vertrauen import _anfrage  # noqa: E402


@pytest.fixture
def welt(tmp_path, monkeypatch):
    dl = tmp_path / "Downloads"
    (dl / "MP3").mkdir(parents=True)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(dl))
    pl = {"id": "p1", "name": "P", "items": []}
    app._playlists.append(pl)
    return dl, pl


def _einrichten(ziel):
    return app.playlist_aktion({"art": "sync_config", "id": "p1", "sync_ordner": ziel,
                                "sync_modus": "spiegeln", "sync_auto": True})


@pytest.mark.parametrize("unter", ["", "MP3", os.path.join("MP3", "Stick")])
def test_ziel_in_der_bibliothek_wird_abgelehnt(welt, unter):
    dl, pl = welt
    r = _einrichten(str(dl / unter) if unter else str(dl))
    assert isinstance(r, dict) and "Bibliothek" in r.get("fehler", ""), r
    assert not {"sync_ordner", "sync_modus", "sync_auto"} & set(pl), \
        f"eine abgelehnte Einrichtung hat trotzdem etwas gesetzt: {pl}"


@pytest.mark.parametrize("ziel", [r"\\server\freigabe\Musik", "//server/freigabe/Musik",
                                  "\\\\?\\UNC\\server\\freigabe\\Musik"])
def test_netzwerkpfad_wird_abgelehnt(welt, ziel, monkeypatch):
    _, pl = welt
    angefasst = []
    for name in ("isdir", "exists", "isfile"):
        echt = getattr(os.path, name)
        monkeypatch.setattr(os.path, name,
                            lambda p, _e=echt, _n=name: angefasst.append((_n, p)) or _e(p))
    r = _einrichten(ziel)
    assert isinstance(r, dict) and "Netzwerk" in r.get("fehler", ""), r
    assert "sync_ordner" not in pl
    assert not [a for a in angefasst if "server" in str(a[1])], f"UNC-Pfad angefasst: {angefasst}"


@pytest.mark.parametrize("wie", ["daneben", "aehnlicher_name", "leer", "langer_pfad"])
def test_ziel_ausserhalb_und_leer_werden_angenommen(welt, tmp_path, wie):
    _, pl = welt
    ziel = {"daneben": str(tmp_path / "Stick"),
            "aehnlicher_name": str(tmp_path / "Downloads2"),     # kein Teil von Downloads
            "leer": "",
            "langer_pfad": "\\\\?\\" + str(tmp_path / "Stick")}[wie]
    assert _einrichten(ziel) is None
    assert pl["sync_ordner"] == ziel and pl["sync_modus"] == "spiegeln" and pl["sync_auto"] is True


def test_langer_pfad_in_die_bibliothek_wird_abgelehnt(welt):
    dl, pl = welt
    r = _einrichten("\\\\?\\" + str(dl / "MP3"))
    assert isinstance(r, dict) and "Bibliothek" in r.get("fehler", ""), r
    assert "sync_ordner" not in pl


def test_ablehnung_kommt_ueber_die_route(welt):
    dl, pl = welt
    st, _, koerper = _anfrage("/api/playlist", methode="POST",
                              rumpf={"art": "sync_config", "id": "p1", "sync_ordner": str(dl / "MP3")})
    assert st == 200
    assert "Bibliothek" in json.loads(koerper).get("fehler", "")
    assert "sync_ordner" not in pl


def _dialog_teile():
    return [
        "const _toasts=[], _schritte=[]; let _antwort={status:200, daten:{ok:true}};",
        "globalThis.fetch=async (url,o)=>{_schritte.push('fetch:'+JSON.parse(o.body).art);"
        " return {ok:_antwort.status<400, status:_antwort.status, json:async()=>_antwort.daten};};",
        "function toast(t){_toasts.push(t);} async function plLaden(){_schritte.push('laden');}",
        "function plSyncNow(id){_schritte.push('sync:'+id);}",
        "async function plApi(b){_schritte.push('plApi'); await plLaden();}",
        "_els['sync-pfad']={value:'D:\\\\Stick'}; _els['sync-auto']={checked:true};",
        "_els['sync-fly']={remove(){_schritte.push('zu');}};",
        _js_funktion(_pc(), "syncSpeichern"),
    ]


def test_dialog_zeigt_die_ablehnung_und_bleibt_offen(tmp_path):
    (abgelehnt, erlaubt) = _lauf(
        tmp_path, *_dialog_teile(),
        "_antwort={status:200, daten:{fehler:'Der Sync-Ordner liegt in der Bibliothek.'}};"
        " await syncSpeichern('p1', true);"
        " aus({toasts:_toasts.splice(0), schritte:_schritte.splice(0),"
        " gemerkt:localStorage.getItem('ytdl_sync_letzter')});",
        "_antwort={status:200, daten:{ok:true}}; await syncSpeichern('p1', true);"
        " aus({toasts:_toasts.splice(0), schritte:_schritte.splice(0),"
        " gemerkt:localStorage.getItem('ytdl_sync_letzter')});")
    assert abgelehnt["toasts"] and "Bibliothek" in abgelehnt["toasts"][0], abgelehnt
    assert "zu" not in abgelehnt["schritte"] and "sync:p1" not in abgelehnt["schritte"], abgelehnt
    assert abgelehnt["gemerkt"] is None, "ein abgelehnter Ordner wird nicht als letzter gemerkt"
    assert "zu" in erlaubt["schritte"] and "sync:p1" in erlaubt["schritte"], erlaubt
    assert erlaubt["gemerkt"] == "D:\\Stick"
