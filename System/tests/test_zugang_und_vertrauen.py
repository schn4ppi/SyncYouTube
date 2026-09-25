# -*- coding: utf-8 -*-
"""Vertrauen in Anfragen (Gesamtprüfung 25.09.2026, Gruppe 3).

Jede Anfrage läuft hier durch den ECHTEN Handler samt echtem Zugriffsriegel
(`_hat_zugriff`) — ohne Server und ohne Socket, die Antwort landet in einem
Puffer. Anders als die älteren Handler-Tests ersetzt hier niemand den Riegel:
genau er ist das Thema.

Die LAN-Adresse des Geräts ist 192.168.178.50, die des PCs 192.168.178.20
(so stünde sie im Host-Kopf, wenn das Handy die App im WLAN aufruft). Der
Rechnername ist in jedem Test `JB-PC` (Attrappe für `socket.gethostname`).
"""
import email.message
import io
import json
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402

LAN = "192.168.178.50"
PC_IM_LAN = "192.168.178.20:8776"
CODE = "AB12CD"


@pytest.fixture(autouse=True)
def rechner(monkeypatch):
    monkeypatch.setattr(app.socket, "gethostname", lambda: "JB-PC")
    monkeypatch.setattr(app, "_remote", {"n": 0, "cmd": "", "key": "", "wert": None, "ts": 0})
    bremse = getattr(app, "_fehlversuche", None)
    if bremse is not None:
        bremse.clear()
    yield
    if bremse is not None:
        bremse.clear()


def _fernsteuerung(monkeypatch, an=True):
    monkeypatch.setitem(app.CFG, "fernsteuerung", an)
    monkeypatch.setitem(app.CFG, "fernsteuerung_code", CODE)


def _anfrage(pfad, *, methode="GET", ip="127.0.0.1", kopf=None, rumpf=None):
    """Eine Anfrage durch den echten Handler; liefert (Status, Köpfe, Körper)."""
    h = object.__new__(app.Handler)
    h.path, h.command, h.request_version = pfad, methode, "HTTP/1.1"
    h.requestline = f"{methode} {pfad} HTTP/1.1"
    h.client_address = (ip, 50000)
    h.headers = email.message.Message()
    kopf = dict(kopf or {})
    if rumpf is not None and not isinstance(rumpf, bytes):
        rumpf = json.dumps(rumpf).encode("utf-8")
    if rumpf is not None and "Content-Length" not in kopf:
        kopf["Content-Length"] = str(len(rumpf))
    for k, v in kopf.items():
        h.headers[k] = v
    h.rfile, h.wfile = io.BytesIO(rumpf or b""), io.BytesIO()
    h.close_connection = False
    getattr(h, "do_" + methode)()
    roh = h.wfile.getvalue()
    kopfteil, _, koerper = roh.partition(b"\r\n\r\n")
    zeilen = kopfteil.decode("latin-1").split("\r\n")
    status = int(zeilen[0].split(" ", 2)[1]) if zeilen and zeilen[0] else 0
    koepfe = {}
    for z in zeilen[1:]:
        k, _, v = z.partition(":")
        koepfe.setdefault(k.strip().lower(), []).append(v.strip())
    return status, koepfe, koerper


def _fern(befehl="play", **kopf):
    """POST /api/remote (reiner Speicher-Befehl, keine Platte, kein Netz)."""
    return _anfrage("/api/remote", methode="POST", kopf=kopf, rumpf={"cmd": befehl})


# ------------------------------------------------------------ S2: Host-Kopf

def test_lan_ohne_code_wird_abgewiesen(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 403


def test_lan_mit_code_kommt_durch(monkeypatch):
    _fernsteuerung(monkeypatch)
    st, _, koerper = _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN, "X-Code": CODE})
    assert st == 200
    assert "fernsteuerung_code" not in koerper.decode("utf-8"), "der Code geht nie ins WLAN"


def test_fremder_host_wird_abgewiesen(monkeypatch):
    """DNS-Rebinding: eine fremde Seite, deren Name auf 127.0.0.1 zeigt, trägt
    ihren eigenen Namen im Host-Kopf. Vorher kam sie durch (Localhost = immer)."""
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/api/status", kopf={"Host": "angreifer.example:8776"})
    assert st == 403
    st, _, _ = _anfrage("/api/status", ip=LAN, kopf={"Host": "angreifer.example:8776", "X-Code": CODE})
    assert st == 403, "auch der richtige Code hilft einem fremden Namen nicht"
    assert _fern(Host="angreifer.example:8776")[0] == 403
    assert app._remote["n"] == 0, "der Befehl darf nicht ausgeführt sein"


@pytest.mark.parametrize("host", [
    "127.0.0.1:8776", "localhost:8776", "LOCALHOST:8776", "[::1]:8776", PC_IM_LAN,
    "10.0.0.7", "jb-pc:8776", "JB-PC.fritz.box:8776", "jb-pc.local:8776", None])
def test_erlaubte_hosts(host):
    kopf = {"Host": host} if host else {}
    st, _, _ = _anfrage("/api/status", kopf=kopf)
    assert st == 200, host


@pytest.mark.parametrize("host", [
    "angreifer.example:8776", "127.0.0.1.nip.io:8776", "localhost.angreifer.example:8776",
    "anderer-pc:8776", "127.1:8776", "angreifer.example@127.0.0.1:8776", ".fritz.box:8776",
    "[nicht-ip]:8776", "127.0.0.1:port"])
def test_abgewiesene_hosts(host):
    st, _, _ = _anfrage("/api/status", kopf={"Host": host})
    assert st == 403, host


# ------------------------------------------------------------ S2: Origin

def test_fremder_origin_wird_abgewiesen():
    """Klassischer CSRF: eine offene Webseite schickt per text/plain-POST einen
    Befehl an 127.0.0.1. Der Host-Kopf stimmt, der Origin verrät die Seite."""
    st, _, _ = _fern(Host="127.0.0.1:8776", Origin="https://angreifer.example")
    assert st == 403
    assert app._remote["n"] == 0, "der Befehl darf nicht ausgeführt sein"


@pytest.mark.parametrize("origin", ["null", "http://localhost:8776", "http://127.0.0.1:8765",
                                    "file://", "data:text/html,x"])
def test_origin_muss_der_eigene_sein(origin):
    st, _, _ = _fern(Host="127.0.0.1:8776", Origin=origin)
    assert st == 403, origin


def test_eigener_origin_kommt_durch(monkeypatch):
    assert _fern(Host="127.0.0.1:8776", Origin="http://127.0.0.1:8776")[0] == 200
    assert _fern(Host="localhost:8776", Origin="http://localhost:8776")[0] == 200
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/api/remote", methode="POST", ip=LAN, rumpf={"cmd": "play"},
                        kopf={"Host": PC_IM_LAN, "Origin": "http://" + PC_IM_LAN, "X-Code": CODE})
    assert st == 200, "die Handy-Seite im WLAN schickt ihren eigenen Ursprung"


def test_ohne_origin_bleibt_erlaubt():
    """So rufen Tray (Beenden), SyncFindus (link_weiche) und die Hülle: urllib
    ohne Origin-Kopf."""
    assert _fern(Host="127.0.0.1:8776")[0] == 200
    assert app._remote["n"] == 1


@pytest.mark.parametrize("origin", ["moz-extension://0a1b2c3d-4e5f-6789-abcd-ef0123456789",
                                    "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
                                    "ms-browser-extension://Addon_1.0.0.0_abc"])
def test_addon_ursprung_kommt_durch_auch_ohne_content_type(origin):
    """Das Addon sendet BEWUSST ohne Content-Type (browser-addon/shared/background.js)."""
    st, _, _ = _fern(Host="127.0.0.1:8776", Origin=origin)
    assert st == 200, origin


def test_preflight_nur_fuer_das_addon():
    st, koepfe, _ = _anfrage("/api/add", methode="OPTIONS",
                             kopf={"Host": "127.0.0.1:8776", "Origin": "moz-extension://abc"})
    assert st == 204 and koepfe.get("access-control-allow-origin") == ["moz-extension://abc"]
    st, koepfe, _ = _anfrage("/api/add", methode="OPTIONS",
                             kopf={"Host": "127.0.0.1:8776", "Origin": "https://angreifer.example"})
    assert st == 403 and "access-control-allow-origin" not in koepfe


# ------------------------------------------------------------ S2: Einbettung

def test_nur_das_dashboard_darf_einbetten():
    """Das Dashboard (Tray-Server 127.0.0.1:8765) lädt /?embed=1 im Rahmen;
    jede andere Seite darf die App nicht einbetten (Klick-Entführung)."""
    st, koepfe, _ = _anfrage("/?embed=1", kopf={"Host": "127.0.0.1:8776"})
    assert st == 200
    csp = " ".join(koepfe.get("content-security-policy", []))
    assert "frame-ancestors 'self' http://127.0.0.1:8765" in csp, koepfe
    assert "x-frame-options" not in koepfe, "DENY würde das Dashboard aussperren"
    st, koepfe, _ = _anfrage("/api/status", kopf={"Host": "127.0.0.1:8776"})
    assert "frame-ancestors" in " ".join(koepfe.get("content-security-policy", []))
