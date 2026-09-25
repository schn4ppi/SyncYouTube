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


# ------------------------------------------------------------------ F21
# Eigene Proxys ohne Land (für alle) standen je erlaubtem Land einmal in der
# Kette: bei drei Ländern wurde derselbe Proxy dreimal versucht, je bis zu 30 s.

def test_eigener_proxy_nur_einmal_in_der_kette():
    import geo
    cfg = {"geo_methoden": ["proxy_manuell"], "geo_gratis_proxy": False,
           "geo_proxies": ["socks5://10.0.0.1:1080", "GB=socks5://10.0.0.2:1080",
                           "IE=socks5://10.0.0.1:1080"]}
    liste = geo.kandidaten(["United Kingdom", "Ireland", "Guernsey"], cfg)
    proxys = [v.opts["proxy"] for v in liste]
    assert proxys == ["socks5://10.0.0.1:1080", "socks5://10.0.0.2:1080"], proxys


def test_gratis_proxys_ohne_doppel(monkeypatch):
    import geo
    monkeypatch.setattr(geo, "freie_proxys", lambda code: ["http://10.1.1.1:80", f"http://{code}:80"])
    cfg = {"geo_methoden": ["proxy_frei"], "geo_proxies": []}
    liste = geo.kandidaten(["United Kingdom", "Ireland"], cfg)
    proxys = [v.opts["proxy"] for v in liste]
    assert proxys == ["http://10.1.1.1:80", "http://GB:80", "http://IE:80"], proxys


# ------------------------------------------------------------------ F22
# Die VPN-Adapter der Geo-Umgehung: Windscribe und WireGuard meldeten Erfolg
# ohne Prüfung und trennten danach auch eine Verbindung, die der Nutzer selbst
# aufgebaut hatte; NordVPN trennte die eigene Verbindung des Nutzers, wenn die
# Insights-Abfrage scheiterte (Status unbekannt galt als „nicht verbunden“).

def _nord(monkeypatch, status):
    import geo
    rufe = []
    monkeypatch.setattr(geo._nord, "status", lambda timeout=6: dict(status))
    monkeypatch.setattr(geo._nord, "verbinden", lambda land, timeout=60: rufe.append(("verbinden", land)) or True)
    monkeypatch.setattr(geo._nord, "trennen", lambda timeout=20: rufe.append(("trennen",)) or True)
    return geo._NordAdapter(), rufe


def test_nord_status_unbekannt_fasst_nichts_an(monkeypatch):
    ad, rufe = _nord(monkeypatch, {})                  # Insights nicht erreichbar
    assert ad.verbinden_wenn_noetig("United Kingdom") is False
    ad.trennen_wenn_selbst()
    assert rufe == [], "bei unbekanntem Status wurde umgeschaltet oder getrennt"


def test_nord_eigene_verbindung_bleibt(monkeypatch):
    ad, rufe = _nord(monkeypatch, {"protected": True, "country_code": "DE"})
    assert ad.verbinden_wenn_noetig("United Kingdom") is True
    ad.trennen_wenn_selbst()
    assert rufe == []


def test_nord_verbindet_und_trennt_selbst(monkeypatch):
    ad, rufe = _nord(monkeypatch, {"protected": False, "country_code": "DE"})
    assert ad.verbinden_wenn_noetig("United Kingdom") is True
    ad.trennen_wenn_selbst()
    assert rufe == [("verbinden", "United Kingdom"), ("trennen",)]


class _Cli:
    """Attrappe für subprocess in geo: Antworten je Befehl, Mitschrift."""

    def __init__(self, antworten):
        import subprocess
        self.antworten, self.rufe = dict(antworten), []
        self.DEVNULL, self.PIPE = subprocess.DEVNULL, subprocess.PIPE
        self.SubprocessError, self.CREATE_NO_WINDOW = subprocess.SubprocessError, 0

    def run(self, befehl, **kw):
        wort = befehl[1]
        self.rufe.append(wort)
        a = self.antworten.get(wort, (0, ""))
        if callable(a):
            a = a()
        return types.SimpleNamespace(returncode=a[0], stdout=a[1], stderr="")


def _windscribe(monkeypatch, antworten):
    import geo
    cli = _Cli(antworten)
    monkeypatch.setattr(geo, "subprocess", cli)
    ad = geo._WindscribeAdapter()
    monkeypatch.setattr(ad, "_exe", lambda: r"C:\Programme\Windscribe\windscribe-cli.exe")
    return ad, cli


def test_windscribe_eigene_verbindung_bleibt(monkeypatch):
    ad, cli = _windscribe(monkeypatch, {"status": (0, "Connect state: Connected: London")})
    assert ad.verbinden_wenn_noetig("United Kingdom") is True
    ad.trennen_wenn_selbst()
    assert "connect" not in cli.rufe and "disconnect" not in cli.rufe, cli.rufe


def test_windscribe_prueft_den_rueckgabecode(monkeypatch):
    ad, cli = _windscribe(monkeypatch, {"status": (0, "Connect state: Disconnected"),
                                        "connect": (1, "Error: not logged in")})
    assert ad.verbinden_wenn_noetig("United Kingdom") is False
    assert cli.rufe[:2] == ["status", "connect"]


def test_windscribe_verbindet_und_trennt_selbst(monkeypatch):
    zustand = ["Connect state: Disconnected"]

    def verbinden():
        zustand[0] = "Connect state: Connected: London"
        return (0, "")
    ad, cli = _windscribe(monkeypatch, {"status": lambda: (0, zustand[0]), "connect": verbinden})
    assert ad.verbinden_wenn_noetig("United Kingdom") is True
    ad.trennen_wenn_selbst()
    assert cli.rufe == ["status", "connect", "status", "disconnect"], cli.rufe


def test_windscribe_unlesbarer_status_fasst_nichts_an(monkeypatch):
    ad, cli = _windscribe(monkeypatch, {"status": (0, "")})
    assert ad.verbinden_wenn_noetig("United Kingdom") is False
    ad.trennen_wenn_selbst()
    assert cli.rufe == ["status"]


def _wireguard(monkeypatch, tmp_path, dienst_da, antworten):
    import geo
    (tmp_path / "GB.conf").write_text("[Interface]\n", encoding="utf-8")
    cli = _Cli(antworten)
    monkeypatch.setattr(geo, "subprocess", cli)
    monkeypatch.setattr(geo, "_dienst_da", lambda name: dienst_da, raising=False)
    ad = geo._WireguardAdapter(str(tmp_path))
    monkeypatch.setattr(ad, "_exe", lambda: r"C:\Programme\WireGuard\wireguard.exe")
    return ad, cli


def test_wireguard_eigener_tunnel_bleibt(monkeypatch, tmp_path):
    ad, cli = _wireguard(monkeypatch, tmp_path, True, {})
    assert ad.verbinden_wenn_noetig("United Kingdom") is True
    ad.trennen_wenn_selbst()
    assert cli.rufe == [], "der schon laufende Tunnel des Nutzers wurde angefasst"


def test_wireguard_prueft_den_rueckgabecode(monkeypatch, tmp_path):
    ad, cli = _wireguard(monkeypatch, tmp_path, False, {"/installtunnelservice": (1, "")})
    assert ad.verbinden_wenn_noetig("United Kingdom") is False
    ad.trennen_wenn_selbst()
    assert cli.rufe == ["/installtunnelservice"], cli.rufe


def test_wireguard_verbindet_und_trennt_selbst(monkeypatch, tmp_path):
    ad, cli = _wireguard(monkeypatch, tmp_path, False, {"/installtunnelservice": (0, "")})
    assert ad.verbinden_wenn_noetig("United Kingdom") is True
    ad.trennen_wenn_selbst()
    assert cli.rufe == ["/installtunnelservice", "/uninstalltunnelservice"], cli.rufe


def test_dienst_abfrage_echt_und_lokal():
    import geo
    assert geo._dienst_da("EventLog") is True, "den Ereignisprotokoll-Dienst hat jedes Windows"
    assert geo._dienst_da("WireGuardTunnel$gibt-es-nicht-7f3a") is False
