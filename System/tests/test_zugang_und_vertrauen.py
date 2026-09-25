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
LETZTER = {}                                     # der Handler der letzten _anfrage


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
    LETZTER["h"] = h
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


# ------------------------------------------------------------ S13: aus heißt aus

def _gekoppelt():
    """Ein fertig gekoppeltes Gerät (Pairing samt Freigabe am PC) -> Token."""
    import profil_geraete as pg
    a = pg.geraet_anmelden("Handy")
    assert pg.geraet_bestaetigen(a["geraet_id"], "standard")
    return pg.geraet_token_abholen(a["geraet_id"], a["code"])["token"]


def test_fernsteuerung_aus_sperrt_auch_gekoppelte_geraete_sofort(monkeypatch):
    """Vorher galt „aus" für gekoppelte Geräte erst nach einem Neustart (bis
    dahin lauscht der Server weiter im WLAN)."""
    token = _gekoppelt()
    _fernsteuerung(monkeypatch, an=True)
    kopf = {"Host": PC_IM_LAN, "X-Geraet": token}
    assert _anfrage("/api/status", ip=LAN, kopf=kopf)[0] == 200
    app.CFG["fernsteuerung"] = False                  # am PC ausgeschaltet, kein Neustart
    assert _anfrage("/api/status", ip=LAN, kopf=kopf)[0] == 403
    assert _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN, "X-Code": CODE})[0] == 403
    app.CFG["fernsteuerung"] = True                   # wieder an: gilt ebenso sofort
    assert _anfrage("/api/status", ip=LAN, kopf=kopf)[0] == 200


@pytest.mark.parametrize("pfad,methode", [("/", "GET"), ("/m", "GET"), ("/koppeln", "GET"),
                                          ("/api/geraet_anmelden", "POST")])
def test_fernsteuerung_aus_auch_keine_koppel_wege(monkeypatch, pfad, methode):
    import profil_geraete as pg
    _fernsteuerung(monkeypatch, an=False)
    rumpf = {"name": "Fremd"} if methode == "POST" else None
    st, _, koerper = _anfrage(pfad, methode=methode, ip=LAN, kopf={"Host": PC_IM_LAN}, rumpf=rumpf)
    assert st == 403, (pfad, koerper[:80])
    assert pg.geraete_liste() == [], "bei ausgeschalteter Fernsteuerung koppelt sich niemand an"


def test_fernsteuerung_aus_laesst_den_pc_selbst_durch(monkeypatch):
    _fernsteuerung(monkeypatch, an=False)
    assert _anfrage("/api/status", kopf={"Host": "127.0.0.1:8776"})[0] == 200


# ------------------------------------------------------------ S7: Versuchsbremse

class Uhr:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def uhr(monkeypatch):
    u = Uhr()
    monkeypatch.setattr(app, "_bremse_uhr", u, raising=False)
    return u


def _mit_code(code, ip=LAN):
    return _anfrage("/api/status", ip=ip, kopf={"Host": PC_IM_LAN, "X-Code": code})[0]


def test_bremse_greift_ab_zehn_fehlversuchen(monkeypatch, uhr):
    _fernsteuerung(monkeypatch)
    for _ in range(9):
        assert _mit_code("FALSCH") == 403
    assert _mit_code(CODE) == 200, "neun Fehlversuche sperren noch nicht"
    for _ in range(10):
        assert _mit_code("FALSCH") == 403
    assert _mit_code(CODE) == 403, "nach zehn Fehlversuchen hilft auch der richtige Code nicht"
    uhr.t += 1.5                                      # erste Sperre: 1 s
    assert _mit_code(CODE) == 200, "nach Ablauf der Sperre geht es wieder"
    for _ in range(9):
        assert _mit_code("FALSCH") == 403
    assert _mit_code(CODE) == 200, "der Erfolg hat den Zähler zurückgesetzt"


def test_bremse_waechst_exponentiell_bis_15_minuten(monkeypatch, uhr):
    """Nach jedem Fehlversuch messen, wie lange die Sperre steht; der nächste
    Versuch kommt erst danach (während der Sperre zählt keiner)."""
    _fernsteuerung(monkeypatch)
    sperren = []
    for _ in range(24):
        assert _mit_code("FALSCH") == 403
        dauer = 0.0
        while app._bremse_gesperrt(LAN):
            uhr.t += 0.25
            dauer += 0.25
        sperren.append(dauer)
    assert sperren[:9] == [0.0] * 9, sperren
    assert sperren[9:14] == [1.0, 2.0, 4.0, 8.0, 16.0], sperren
    assert max(sperren) == 900.0 and sperren[-1] == 900.0, "Deckel 15 Minuten"


def test_bremse_je_ip_und_nie_fuer_den_pc(monkeypatch, uhr):
    _fernsteuerung(monkeypatch)
    for _ in range(12):
        _mit_code("FALSCH")
    assert _mit_code(CODE) == 403
    assert _mit_code(CODE, ip="192.168.178.51") == 200, "ein anderes Gerät bleibt frei"
    for _ in range(30):
        _mit_code("FALSCH", ip="127.0.0.1")
    assert _mit_code(CODE, ip="127.0.0.1") == 200, "der PC selbst wird nie gebremst"


def test_bremse_zaehlt_falsche_geraete_token(monkeypatch, uhr):
    _fernsteuerung(monkeypatch)
    for _ in range(10):
        st, _, _ = _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN, "X-Geraet": "f" * 32})
        assert st == 403
    assert _mit_code(CODE) == 403


def test_anfragen_ohne_zugangsdaten_zaehlen_nicht(monkeypatch, uhr):
    """Die PC-Oberfläche auf einem gekoppelten Gerät fragt ohne Token (F9) —
    ein Strom solcher 403 darf das Gerät nicht aussperren."""
    _fernsteuerung(monkeypatch)
    for _ in range(30):
        assert _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN})[0] == 403
    assert _mit_code(CODE) == 200


def test_vergleiche_laufen_zeitkonstant(monkeypatch):
    import hmac

    import profil_geraete as pg
    token = _gekoppelt()
    echt, aufrufe = hmac.compare_digest, []

    def spion(a, b):
        aufrufe.append((a, b))
        return echt(a, b)

    monkeypatch.setattr(hmac, "compare_digest", spion)
    assert app.zugriff_erlaubt(LAN, True, CODE, CODE) is True
    assert aufrufe, "Code-Vergleich ohne hmac.compare_digest"
    aufrufe.clear()
    assert app.zugriff_erlaubt(LAN, True, CODE, "ÄÖÜ") is False, "Nicht-ASCII bricht nicht"
    aufrufe.clear()
    assert pg.geraet_ok(token) == "standard"
    assert aufrufe, "Token-Vergleich ohne hmac.compare_digest"


def test_waehrend_der_sperre_zaehlt_nichts(monkeypatch, uhr):
    """Anfragen während einer Sperre prallen ab, ohne sie zu verlängern."""
    _fernsteuerung(monkeypatch)
    for _ in range(10):
        _mit_code("FALSCH")
    for _ in range(50):
        assert _mit_code("FALSCH") == 403
    uhr.t += 1.1
    assert _mit_code(CODE) == 200


# ------------------------------------------------------------ S14: Körper und Zeitlimit

def _post_mit_laenge(laenge, rumpf=b'{"cmd": "play"}'):
    return _anfrage("/api/remote", methode="POST", rumpf=rumpf,
                    kopf={"Host": "127.0.0.1:8776", "Content-Length": laenge})[0]


def test_koerper_ueber_2_mb_wird_abgewiesen_ohne_zu_lesen():
    assert _post_mit_laenge(str(2 * 1024 * 1024 + 1)) == 413
    h = LETZTER["h"]
    assert h.rfile.tell() == 0, "der Körper darf gar nicht erst gelesen werden"
    assert h.close_connection, "danach wird die Verbindung geschlossen"
    assert app._remote["n"] == 0


def test_koerper_bis_2_mb_bleibt_erlaubt():
    rumpf = json.dumps({"cmd": "play", "fuell": "x" * (2 * 1024 * 1024 - 40)}).encode()
    assert len(rumpf) <= 2 * 1024 * 1024
    assert _post_mit_laenge(str(len(rumpf)), rumpf) == 200


@pytest.mark.parametrize("laenge", ["-1", "-5", "abc", "1e3", "0x10"])
def test_unlesbare_laenge_gibt_400(laenge):
    """Eine negative Länge las bisher bis zum Verbindungsende, eine unlesbare
    warf eine Ausnahme ohne Antwort."""
    assert _post_mit_laenge(laenge) == 400
    assert LETZTER["h"].close_connection
    assert app._remote["n"] == 0


def test_handler_hat_ein_zeitlimit_von_30_s():
    assert app.Handler.timeout == 30


def test_zeitlimit_wirkt_im_echten_server(monkeypatch):
    """Ein Client, der die Anfrage nie zu Ende schickt, hält keinen Faden
    fest: der Server schließt die Verbindung nach dem Zeitlimit (hier auf
    0,5 s verkürzt, gemessen am echten ThreadingHTTPServer auf 127.0.0.1)."""
    import socket
    import threading
    import time
    monkeypatch.setattr(app.Handler, "timeout", 0.5)
    srv = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    faden = threading.Thread(target=srv.serve_forever, daemon=True)
    faden.start()
    try:
        s = socket.create_connection(srv.server_address, timeout=5)
        s.sendall(b"POST /api/remote HTTP/1.1\r\nHost: 127.0.0.1\r\n")   # Kopf nie beendet
        t0 = time.monotonic()
        assert s.recv(1024) == b"", "der Server hätte die Verbindung schließen müssen"
        assert time.monotonic() - t0 < 4
        s.close()
    finally:
        srv.shutdown()
        srv.server_close()
