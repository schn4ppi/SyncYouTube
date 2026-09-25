# -*- coding: utf-8 -*-
"""Kleine Fehler in App-Kern, Update, Geo, VPN und Hülle (Gesamtprüfung
Gruppe 6, 25.09.2026). Kein Netz, keine echten Daten: die conftest legt alle
Datenpfade je Test in tmp_path und sperrt das Netz.

F14: Das Auto-Update prüfte nur Downloads, nicht die Wiedergabe, und beendet
den Prozess hart. Jetzt gilt dieselbe Leerlauf-Definition wie beim
Selbst-Neustart (`_code_leerlauf`).
"""
import os
import sys
import time
import types

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402


class _Stopp(Exception):
    pass


def _update_takt(monkeypatch, runden=2):
    """_update_hintergrund mit einer eigenen Uhr: nach `runden` Schlafpausen
    endet die Endlosschleife. Nur `app.time` wird ersetzt, nicht das echte
    Modul (andere Fäden schlafen normal weiter)."""
    schlaf, rufe = [], []

    def schlafen(s):
        schlaf.append(s)
        if len(schlaf) >= runden:
            raise _Stopp
    uhr = types.SimpleNamespace(**{n: getattr(time, n) for n in dir(time) if not n.startswith("_")})
    uhr.sleep = schlafen
    monkeypatch.setattr(app, "time", uhr)
    monkeypatch.setitem(app.CFG, "auto_update", True)
    monkeypatch.setattr(app.update, "frozen_exe", lambda: r"C:\Programm\SyncYouTube.exe")
    monkeypatch.setattr(app, "update_lauf", lambda icon=None: rufe.append("update"))
    return schlaf, rufe


def test_auto_update_wartet_auf_vlc(monkeypatch):
    schlaf, rufe = _update_takt(monkeypatch)
    monkeypatch.setattr(app, "_vlc_haelt_neustart_auf", lambda: True)   # VLC spielt, nichts lädt
    with pytest.raises(_Stopp):
        app._update_hintergrund()
    assert rufe == [], "mitten in der Wiedergabe darf das Update den Prozess nicht beenden"
    assert schlaf == [90, 1800]


def test_auto_update_wartet_nach_browser_wiedergabe(monkeypatch):
    schlaf, rufe = _update_takt(monkeypatch)
    monkeypatch.setattr(app, "_vlc_haelt_neustart_auf", lambda: False)
    monkeypatch.setattr(app, "_letzter_stream", time.time())          # gerade abgespielt
    with pytest.raises(_Stopp):
        app._update_hintergrund()
    assert rufe == [] and schlaf == [90, 1800]


def test_auto_update_wartet_auf_downloads(monkeypatch):
    schlaf, rufe = _update_takt(monkeypatch)
    monkeypatch.setattr(app, "_vlc_haelt_neustart_auf", lambda: False)
    monkeypatch.setattr(app, "_letzter_stream", 0.0)
    monkeypatch.setattr(app.Q, "items", [{"id": "a", "status": "laeuft"}])
    with pytest.raises(_Stopp):
        app._update_hintergrund()
    assert rufe == [] and schlaf == [90, 1800]


def test_auto_update_im_leerlauf(monkeypatch):
    schlaf, rufe = _update_takt(monkeypatch)
    monkeypatch.setattr(app, "_vlc_haelt_neustart_auf", lambda: False)
    monkeypatch.setattr(app, "_letzter_stream", 0.0)
    monkeypatch.setattr(app.Q, "items", [{"id": "a", "status": "fertig"}])
    with pytest.raises(_Stopp):
        app._update_hintergrund()
    assert rufe == ["update"] and schlaf == [90, 24 * 3600]


# ------------------------------------------------------------------ F17

def test_playlist_anlage_antwortet_mit_id(monkeypatch):
    import json

    from test_zugang_und_vertrauen import _anfrage
    monkeypatch.setattr(app, "_playlists", [{"id": "alt00001", "name": "Alt", "items": [], "ts": 0}])
    st, _, koerper = _anfrage("/api/playlist", methode="POST", rumpf={"art": "create", "name": "Neu"})
    assert st == 200
    antwort = json.loads(koerper)
    neu = [p for p in app._playlists if p["name"] == "Neu"]
    assert len(neu) == 1 and antwort.get("id") == neu[0]["id"], antwort
    st, _, koerper = _anfrage("/api/playlist", methode="POST",
                              rumpf={"art": "rename", "id": "alt00001", "name": "Umbenannt"})
    assert st == 200 and json.loads(koerper) == {"ok": True}, "die übrigen Aktionen antworten wie bisher"
