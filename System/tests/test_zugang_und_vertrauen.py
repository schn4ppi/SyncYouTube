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
import socket
import sys
import threading
import time

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


ADDON_URSPRUENGE = ["moz-extension://0a1b2c3d-4e5f-6789-abcd-ef0123456789",
                    "chrome-extension://abcdefghijklmnopabcdefghijklmnop"]


@pytest.mark.parametrize("origin", ADDON_URSPRUENGE)
def test_addon_ursprung_kommt_durch_auch_ohne_content_type(origin):
    """Das Addon sendet BEWUSST ohne Content-Type (browser-addon/shared/background.js)."""
    st, _, _ = _fern(Host="127.0.0.1:8776", Origin=origin)
    assert st == 200, origin


@pytest.mark.parametrize("origin", ADDON_URSPRUENGE)
def test_addon_ursprung_und_cors_sagen_dasselbe(origin):
    """Gruppe 6: Origin-Prüfung und CORS kennen dieselben Erweiterungs-Schemata
    (vorher ließ die Prüfung auch ms-browser-extension durch, CORS nicht)."""
    st, koepfe, _ = _anfrage("/api/add", methode="OPTIONS", kopf={"Host": "127.0.0.1:8776", "Origin": origin})
    assert st == 204 and koepfe.get("access-control-allow-origin") == [origin]


def test_alt_edge_erweiterung_wird_abgewiesen():
    """Das Schema ms-browser-extension gab es nur im alten Edge (EdgeHTML), den
    es nicht mehr gibt; das Addon läuft im heutigen Edge als chrome-extension.
    Die Origin-Prüfung ließ es trotzdem durch, CORS nicht: jetzt beide nicht."""
    alt = "ms-browser-extension://Addon_1.0.0.0_abc"
    assert _fern(Host="127.0.0.1:8776", Origin=alt)[0] == 403
    st, koepfe, _ = _anfrage("/api/add", methode="OPTIONS", kopf={"Host": "127.0.0.1:8776", "Origin": alt})
    assert st == 403 and "access-control-allow-origin" not in koepfe


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
    # Wieder an: der Riegel lässt sofort durch. Im Betrieb kommt die Anfrage
    # aber nur an, wenn der Server schon im WLAN lauscht, also mit
    # eingeschalteter Fernsteuerung gestartet wurde (main bindet sonst nur
    # 127.0.0.1); nach einem Start mit „aus" braucht das Einschalten wie
    # bisher einen Neustart.
    app.CFG["fernsteuerung"] = True
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


# Nacharbeit S7: Prüfen und Zählen lagen in zwei getrennten Sperrabschnitten,
# dazwischen der Vergleich; geraet_ok liest dabei profile.json von der Platte
# und gibt den Faden frei. Jede Anfrage, die in dieses Fenster fiel, durfte
# raten. Die Attrappe unten macht das Fenster so breit wie ein langsamer
# Plattenzugriff (50 ms), damit der Stoß es sicher trifft.

def _versuche_zaehlen(monkeypatch):
    """Zählt jeden Vergleich (Code und Geräte-Token), den der Riegel anstellt."""
    import profil_geraete as pg
    vergleiche = {"code": 0, "token": 0}
    zaehler_lock = threading.Lock()
    echt_ok, echt_code = pg.geraet_ok, app.zugriff_erlaubt

    def langsam_ok(tok):
        if tok:
            with zaehler_lock:
                vergleiche["token"] += 1
        time.sleep(0.05)                              # profile.json von der Platte
        return echt_ok(tok)

    def code_gezaehlt(*a):
        if a[3]:
            with zaehler_lock:
                vergleiche["code"] += 1
        return echt_code(*a)

    monkeypatch.setattr(pg, "geraet_ok", langsam_ok)
    monkeypatch.setattr(app, "zugriff_erlaubt", code_gezaehlt)
    return vergleiche


def _stoss(anzahl, kopf, ip=LAN):
    """`anzahl` Anfragen gleichzeitig (hinter einer Schranke); liefert die Status."""
    schranke, ergebnisse = threading.Barrier(anzahl), []

    def eine():
        schranke.wait()
        ergebnisse.append(_anfrage("/api/status", ip=ip, kopf=dict(kopf))[0])
    faeden = [threading.Thread(target=eine) for _ in range(anzahl)]
    for f in faeden:
        f.start()
    for f in faeden:
        f.join(30)
    assert not any(f.is_alive() for f in faeden), "ein Faden hängt"
    return ergebnisse


def test_paralleler_stoss_nach_ablauf_der_sperre_hat_nur_einen_versuch(monkeypatch, uhr):
    """Zähler auf 30, Sperre gerade abgelaufen, 50 Anfragen gleichzeitig mit
    falschem Code UND fremdem Geräte-Token (den Kopf kann jeder beilegen):
    höchstens EIN Vergleich je Fenster, alle anderen prallen ab."""
    _fernsteuerung(monkeypatch)
    for _ in range(30):
        assert _mit_code("FALSCH") == 403
        uhr.t += app.BREMSE_MAX_S + 1                 # jede Sperre abwarten: alle 30 zählen
    vergleiche = _versuche_zaehlen(monkeypatch)
    ergebnisse = _stoss(50, {"Host": PC_IM_LAN, "X-Code": "FALSCH", "X-Geraet": "f" * 32})
    assert ergebnisse == [403] * 50
    assert vergleiche["code"] <= 1 and vergleiche["token"] <= 1, vergleiche
    assert app._bremse_gesperrt(LAN), "der eine Fehlversuch hat die nächste Sperre gesetzt"


def test_erster_stoss_hat_hoechstens_zehn_versuche(monkeypatch, uhr):
    """Vor dem zehnten Fehlversuch gab es gar keine Sperre: ein Stoß aus 50
    gleichzeitigen Anfragen durfte 50-mal raten. Jetzt höchstens so oft, wie
    nacheinander auch (zehn), danach steht die Sperre."""
    _fernsteuerung(monkeypatch)
    vergleiche = _versuche_zaehlen(monkeypatch)
    ergebnisse = _stoss(50, {"Host": PC_IM_LAN, "X-Code": "FALSCH", "X-Geraet": "f" * 32})
    assert ergebnisse == [403] * 50
    assert vergleiche["code"] <= app.BREMSE_AB and vergleiche["token"] <= app.BREMSE_AB, vergleiche
    assert _mit_code(CODE) == 403, "nach zehn Fehlversuchen steht die Sperre"


def test_gekoppeltes_geraet_mit_vielen_gleichzeitigen_anfragen_kommt_immer_durch(monkeypatch, uhr):
    """Die Handy-Seite lädt Vorschaubilder und Status parallel, jede Anfrage mit
    Token. Die Bremse darf dabei keine einzige abweisen (Erlaubt-Fall)."""
    import profil_geraete as pg
    token = _gekoppelt()
    assert pg.geraet_ok(token)                        # Zeitstempel schon gesetzt: kein Schreiben im Stoß (S8)
    _fernsteuerung(monkeypatch)
    _versuche_zaehlen(monkeypatch)
    ergebnisse = _stoss(40, {"Host": PC_IM_LAN, "X-Geraet": token})
    assert ergebnisse == [200] * 40
    assert not app._bremse_gesperrt(LAN)


def test_ausnahme_im_vergleich_zaehlt_nicht_und_gibt_den_platz_frei(monkeypatch, uhr):
    """Scheitert der Vergleich selbst (profile.json nicht lesbar), zählt das
    nicht als Fehlversuch, und der belegte Platz wird wieder frei."""
    import profil_geraete as pg
    _fernsteuerung(monkeypatch)

    def kaputt(tok):
        raise OSError("profile.json gerade nicht lesbar")
    monkeypatch.setattr(pg, "geraet_ok", kaputt)
    for _ in range(3 * app.BREMSE_AB):
        with pytest.raises(OSError):
            _anfrage("/api/status", ip=LAN, kopf={"Host": PC_IM_LAN, "X-Geraet": "f" * 32})
    assert app._fehlversuche == {}, "nichts gezählt, kein Platz belegt"


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
    """Der Wächter für den WERT: die Tests am echten Server unten verkürzen
    das Zeitlimit selbst und können ihn deshalb nicht bewachen."""
    assert app.Handler.timeout == 30


class _EchterServer:
    """Der echte ThreadingHTTPServer mit dem echten Handler auf 127.0.0.1 und
    freiem Port. Das Zeitlimit ist verkürzt, damit kein Test 30 s wartet;
    `protokoll` spielt einen künftigen HTTP/1.1-Handler (Keep-Alive) nach."""

    def __init__(self, monkeypatch, zeitlimit, protokoll=None):
        monkeypatch.setattr(app.Handler, "timeout", zeitlimit)
        if protokoll:
            monkeypatch.setattr(app.Handler, "protocol_version", protokoll)
        self.srv = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        self.port = self.srv.server_address[1]

    def __enter__(self):
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *_a):
        self.srv.shutdown()
        self.srv.server_close()

    def verbinden(self, empfangspuffer=None):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if empfangspuffer:                            # vor connect: kleines TCP-Fenster
            s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, empfangspuffer)
        s.settimeout(10)
        s.connect(self.srv.server_address)
        return s


def _bis_zum_ende(s):
    """Alles bis die Gegenseite schließt (oder 10 s nichts kommt)."""
    roh = b""
    try:
        while True:
            stueck = s.recv(65536)
            if not stueck:
                break
            roh += stueck
    except TimeoutError:
        pass
    return roh


def test_zeitlimit_wirkt_im_echten_server(monkeypatch):
    """Mechanismus-Nachweis, kein Wächter für den Wert (der steht in
    test_handler_hat_ein_zeitlimit_von_30_s): Ein Client, der seine Anfrage
    nie zu Ende schickt, hält keinen Faden fest; der Server schließt die
    Verbindung nach dem Zeitlimit (hier 0,5 s)."""
    with _EchterServer(monkeypatch, zeitlimit=0.5) as server:
        s = server.verbinden()
        s.sendall(b"POST /api/remote HTTP/1.1\r\nHost: 127.0.0.1\r\n")   # Kopf nie beendet
        t0 = time.monotonic()
        assert s.recv(1024) == b"", "der Server hätte die Verbindung schließen müssen"
        assert time.monotonic() - t0 < 4
        s.close()


# ------------------------------------------------------------ S14 Nacharbeit: Ströme überleben eine Pause
# Abnahme 25.09.: Handler.timeout = 30 galt auch beim Schreiben, und sendall
# wertet es als Gesamtdauer je Schreibaufruf. Nimmt der Browser bei einem
# pausierten Film länger nichts ab, starb der Strom; beim Transcoder
# (Accept-Ranges: none, keine Länge) kann der Browser nichts nachholen, das
# Video endete nach dem Fortsetzen mit einem Fehler. Nachgestellt mit kleinem
# Empfangspuffer, damit die Pause den Server wirklich im Schreiben festhält.

STROM_BYTES = 16 * 1024 * 1024
ZEITLIMIT_KURZ = 0.4
PAUSE_S = 4 * ZEITLIMIT_KURZ


class _Quelle:
    """Liefert `groesse` Null-Bytes stückweise, ohne sie vorzuhalten
    (ffmpeg-Ausgabe bzw. Jellyfin-Antwort)."""

    def __init__(self, groesse):
        self.rest = groesse

    def read(self, n=-1):
        n = self.rest if n is None or n < 0 else min(n, self.rest)
        self.rest -= n
        return bytes(n)


def _weg_transcoder(monkeypatch, tmp_path):
    import filme
    monkeypatch.setattr(filme, "stream_url", lambda iid, druck=False: "http://127.0.0.1:9/film")
    monkeypatch.setattr(app, "_ffmpeg_exe", lambda: r"C:\bin\ffmpeg.exe")
    monkeypatch.setattr(app, "_strom_vorprobe", lambda url: None)

    class Prozess:
        def __init__(self, cmd):
            self.stdout = _Quelle(STROM_BYTES)

        def kill(self):
            pass
    monkeypatch.setattr(app, "_tc_starten", Prozess)
    return "/api/filme/direkt?id=f1&tc=1&vcopy=1&start=0"


def _weg_jellyfin_direkt(monkeypatch, tmp_path):
    import filme
    monkeypatch.setattr(filme, "stream_url", lambda iid, druck=False: "http://127.0.0.1:9/film")

    class Antwort(_Quelle):
        status = 200
        headers = {"Content-Type": "video/mp4", "Content-Length": str(STROM_BYTES),
                   "Accept-Ranges": "bytes"}

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False
    monkeypatch.setattr(app.urllib.request, "urlopen", lambda req, timeout=None: Antwort(STROM_BYTES))
    return "/api/filme/direkt?id=f1"


def _weg_datei(monkeypatch, tmp_path):
    datei = tmp_path / "film.mp4"
    with open(datei, "wb") as f:
        for _ in range(STROM_BYTES // (1 << 20)):
            f.write(bytes(1 << 20))
    monkeypatch.setattr(app, "_pfad_zu_key", lambda key: str(datei))
    return "/media?id=film"


def _lesen_mit_pause(server, pfad):
    """Wie ein Browser-Player: Kopf und das erste MB lesen, dann pausieren
    (nichts abnehmen), dann den Rest. Liefert (Kopf, Körperlänge)."""
    s = server.verbinden(empfangspuffer=16384)
    s.sendall(f"GET {pfad} HTTP/1.1\r\nHost: 127.0.0.1:{server.port}\r\n\r\n".encode())
    roh = b""
    while b"\r\n\r\n" not in roh:
        stueck = s.recv(65536)
        assert stueck, f"Verbindung ohne Kopf zu: {roh[:200]!r}"
        roh += stueck
    kopf, _, koerper = roh.partition(b"\r\n\r\n")
    n = len(koerper)
    while n < (1 << 20):
        stueck = s.recv(65536)
        if not stueck:
            break
        n += len(stueck)
    time.sleep(PAUSE_S)                               # Video pausiert: der Browser nimmt nichts ab
    n += len(_bis_zum_ende(s))
    s.close()
    return kopf.decode("latin-1"), n


@pytest.mark.parametrize("weg", [_weg_transcoder, _weg_jellyfin_direkt, _weg_datei],
                         ids=["transcoder", "jellyfin_direkt", "datei"])
def test_strom_ueberlebt_eine_pause_laenger_als_das_zeitlimit(monkeypatch, tmp_path, weg):
    """Der Client liest mitten im Strom viermal so lange nichts, wie das
    (verkürzte) Zeitlimit erlaubt, und bekommt danach den Rest vollständig."""
    pfad = weg(monkeypatch, tmp_path)
    with _EchterServer(monkeypatch, zeitlimit=ZEITLIMIT_KURZ) as server:
        kopf, n = _lesen_mit_pause(server, pfad)
    assert kopf.startswith("HTTP/1.0 200"), kopf
    assert n == STROM_BYTES, f"nach der Pause fehlen {STROM_BYTES - n} von {STROM_BYTES} Bytes"


def test_nach_einem_strom_liest_die_naechste_anfrage_wieder_mit_zeitlimit(monkeypatch, tmp_path):
    """Das Zeitlimit fällt nur für das Ausliefern eines Stroms weg, nie für das
    Lesen einer Anfrage: Spräche der Handler HTTP/1.1 mit Keep-Alive, läse er
    die nächste Anfrage auf derselben Verbindung wieder mit Zeitlimit."""
    datei = tmp_path / "klein.mp4"
    datei.write_bytes(b"x" * 1000)
    monkeypatch.setattr(app, "_pfad_zu_key", lambda key: str(datei))
    with _EchterServer(monkeypatch, zeitlimit=ZEITLIMIT_KURZ, protokoll="HTTP/1.1") as server:
        s = server.verbinden()
        s.sendall(b"GET /media?id=k HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
        roh = b""
        while not roh.endswith(b"x" * 1000):
            stueck = s.recv(65536)
            assert stueck, roh[:200]
            roh += stueck
        assert roh.startswith(b"HTTP/1.1 200"), roh[:200]
        s.sendall(b"GET /api/status HTTP/1.1\r\nHost: 127.0.0.1\r\n")      # Kopf nie beendet
        t0 = time.monotonic()
        assert s.recv(1024) == b"", "der Server hätte die Verbindung schließen müssen"
        assert time.monotonic() - t0 < 4
        s.close()


# ------------------------------------------------------------ Abgewiesene POSTs schließen die Verbindung
# Abnahme 25.09.: Die 403 aus Host/Origin-Prüfung und Riegel lasen den Körper
# nicht und ließen die Verbindung offen. Unter HTTP/1.0 harmlos (eine Anfrage
# je Verbindung); spräche der Handler HTTP/1.1, würde ein Körper, der selbst
# eine Anfrage ohne Origin enthält, als zweite Anfrage ausgeführt.

def test_abgewiesener_post_schliesst_die_verbindung_in_beiden_zweigen(monkeypatch):
    st, _, _ = _fern(Host="127.0.0.1:8776", Origin="https://angreifer.example")
    assert st == 403 and LETZTER["h"].close_connection, "Zweig Host/Origin"
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/api/remote", methode="POST", ip=LAN, kopf={"Host": PC_IM_LAN},
                        rumpf={"cmd": "play"})
    assert st == 403 and LETZTER["h"].close_connection, "Zweig Riegel"
    assert app._remote["n"] == 0


def test_koerper_eines_abgewiesenen_posts_wird_nie_zur_zweiten_anfrage(monkeypatch):
    innen = b'{"cmd": "play"}'
    zweite = (b"POST /api/remote HTTP/1.1\r\nHost: 127.0.0.1\r\n"
              b"Content-Length: " + str(len(innen)).encode() + b"\r\n\r\n" + innen)
    with _EchterServer(monkeypatch, zeitlimit=1.0, protokoll="HTTP/1.1") as server:
        erste = (f"POST /api/remote HTTP/1.1\r\nHost: 127.0.0.1:{server.port}\r\n"
                 f"Origin: https://angreifer.example\r\nContent-Type: text/plain\r\n"
                 f"Content-Length: {len(zweite)}\r\n\r\n").encode() + zweite
        s = server.verbinden()
        s.sendall(erste)
        antwort = _bis_zum_ende(s)
        s.close()
    assert antwort.startswith(b"HTTP/1.1 403"), antwort[:200]
    assert antwort.count(b"HTTP/1.1 ") == 1, antwort
    assert app._remote["n"] == 0, "der eingeschmuggelte Befehl darf nicht laufen"


# ------------------------------------------------------------ S8: profile.json unlesbar

def test_geraet_anmelden_bei_unlesbarer_profildatei_meldet_fehler_und_schreibt_nicht(monkeypatch):
    """Vorher ersetzte eine Anmeldung eine unlesbare profile.json durch eine
    Datei mit nur dem neuen Gerät: alle gekoppelten Geräte und Profile weg."""
    _fernsteuerung(monkeypatch)
    pfad = app.profil_geraete._pfade["profile"]
    with open(pfad, "wb") as f:
        f.write(b'{"profile": [{"id": "standard"')           # abgeschnitten
    st, _, koerper = _anfrage("/api/geraet_anmelden", methode="POST", ip=LAN,
                              kopf={"Host": PC_IM_LAN}, rumpf={"name": "Handy"})
    assert st == 200
    antwort = json.loads(koerper)
    assert isinstance(antwort, dict) and antwort.get("fehler") and "code" not in antwort, antwort
    with open(pfad, "rb") as f:
        assert f.read() == b'{"profile": [{"id": "standard"', "unlesbare profile.json wurde ersetzt"
