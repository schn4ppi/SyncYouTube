# -*- coding: utf-8 -*-
"""Jellyfin-Zugang nach dem Ausfall vom 23./24.09.2026: ehrlich einordnen,
gestaffelt warten, nichts still verschlucken.

Der Ausfall selbst (Jellyfin 12 las das Token nur noch im Authorization-Kopf)
ist in tests/test_filme.py festgenagelt. Diese Datei prüft, was der Ausfall
über die Selbstheilung verraten hat:

* Die 401-Heilung kannte nur „Token von einer zweiten Sitzung entwertet". Wurde
  auch das frische Token abgelehnt, stand da nur „Items-Abruf HTTP 401", und die
  Oberfläche meldete „Renés Server antwortet seit … nicht" — obwohl er antwortete.
* Der Backoff lebte nur im Prozess-Speicher. Die App startet sich bei jeder
  Code-Änderung selbst neu; danach war der Abzug sofort wieder fällig
  (51 Versuche in gut 18 Stunden).
* Eine Antwort ohne JSON warf eine Ausnahme aus dem Abzug; dann wurde weder
  der Zustand notiert noch ein Backoff gesetzt — der 5-s-Ticker hätte sofort
  wieder angeklopft.

Alle Server sind Attrappen (JellyfinAttrappe aus test_filme.py wertet die Köpfe
aus); kein Netz, keine Anmeldung gegen Renés echten Server.
"""
import json
import os
import sys
import threading
import time
import urllib.error

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

from test_filme import FAKE_ITEMS, JellyfinAttrappe, filme  # noqa: E402

PASSWORT = "GEHEIMES-PASSWORT-7Q"


def _einrichten(pfad, monkeypatch):
    os.makedirs(pfad, exist_ok=True)
    filme.einrichten(str(pfad))
    filme._sitzung.clear()
    filme._fehlversuch_ts = 0.0
    filme._anmelde_sperre_ts = 0.0
    filme._anmelde_art = ""
    monkeypatch.setattr(filme, "_zugang", lambda: {
        "url": "https://jelly.example", "benutzer": "JBK", "passwort": PASSWORT})


def _neustart():
    """Was der Selbst-Neustart (os.execv) vergisst: alle Prozess-Merker."""
    filme._sitzung.clear()
    filme._fehlversuch_ts = 0.0
    filme._anmelde_sperre_ts = 0.0
    filme._anmelde_art = ""


def _zurueckdrehen(sekunden):
    """Den letzten Versuch in filme_zustand.json in die Vergangenheit legen."""
    filme.fam.json_aendern(filme._pfade["zustand"], lambda d: d.__setitem__(
        "letzter_versuch", float(d["letzter_versuch"]) - sekunden), standard={})


def _alter_spiegel():
    """Ein Spiegel vom 20.09. mit der damaligen Server-Version."""
    filme.fam.json_schreiben(filme._pfade["katalog"], {
        "stand": time.time() - 4 * 24 * 3600, "server_version": "10.11.11",
        "eintraege": [filme._eintrag(it) for it in FAKE_ITEMS["Items"]]})


# ------------------------------------------------------------ Fehlerarten

def test_merkmal_abgelehnt_wird_benannt_und_zeigt_die_echte_version(tmp_path, monkeypatch):
    """Anmeldung 200, Abruf mit dem frischen Token wieder 401: genau der Fall vom
    23./24.09. Er bekommt einen eigenen Namen, die Server-Version kommt ohne
    Anmeldung über /System/Info/Public, und der Kopf der Filmseite zeigt sie
    statt „10.11.11" aus dem alten Spiegel."""
    _einrichten(tmp_path, monkeypatch)
    _alter_spiegel()
    jf = JellyfinAttrappe("12", lehnt_ab=True, public_version="12.1.0")
    monkeypatch.setattr(filme, "_http", jf)
    assert filme.katalog_abzug()["ok"] is False
    z = filme.zustand()
    assert z["fehler_art"] == "merkmal_abgelehnt", z
    assert jf.anmeldungen() == 2, "genau eine Neuanmeldung, dann aufhören"
    assert z["server_version"] == "12.1.0", z
    assert z["anzahl"] == 2, "der alte Spiegel bleibt stehen"
    # Eine weitere Anmeldung hilft nicht: 10 Minuten Ruhe, auch für den Abzug.
    filme.katalog_abzug()
    assert jf.anmeldungen() == 2, "trotz abgelehnter Anmeldeform weiter angemeldet"
    assert filme.zustand()["fehler_art"] == "merkmal_abgelehnt"


def test_anmeldung_abgelehnt_wird_benannt(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12", anmeldung=401)
    monkeypatch.setattr(filme, "_http", jf)
    assert filme.katalog_abzug()["ok"] is False
    assert filme.zustand()["fehler_art"] == "anmeldung_abgelehnt"


def test_403_bei_der_anmeldung_ist_eine_voruebergehende_drossel(tmp_path, monkeypatch):
    """Gegenprüfung 24.09.: 403 ist auf Renés Server die bekannte 10-Minuten-
    Drossel gehäufter Anmeldungen (06.08., SyncFindus 28.08.). Sie wird benannt,
    aber NICHT zum Dauerstopp: nach Drossel und Backoff-Stufe darf die
    Automatik es wieder versuchen."""
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12", anmeldung=403)
    monkeypatch.setattr(filme, "_http", jf)
    assert filme.katalog_abzug()["ok"] is False
    assert filme.zustand()["fehler_art"] == "drossel"
    assert filme._anmelde_sperre_ts > time.time() + 500, "10 Minuten Anmelde-Ruhe"
    _neustart()
    _zurueckdrehen(31 * 60)
    assert filme.sync_faellig(alter_s=0) is True, "403 darf die Automatik nicht dauerhaft stoppen"


def test_netzfehler_wird_benannt(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)

    def http(url, daten=None, kopf=None, timeout=15):
        raise urllib.error.URLError("getaddrinfo failed")
    monkeypatch.setattr(filme, "_http", http)
    assert filme.katalog_abzug()["ok"] is False
    assert filme.zustand()["fehler_art"] == "netz"


def test_serverfehler_wird_benannt_und_erfolg_raeumt_auf(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12", antworten=[("/System/Info", 200, {"Version": "12.1.0"}),
                                           ("/Users/u1/Items?", 503, b"")])
    monkeypatch.setattr(filme, "_http", jf)
    assert filme.katalog_abzug()["ok"] is False
    assert filme.zustand()["fehler_art"] == "server"
    _neustart()
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12"))
    assert filme.katalog_abzug()["ok"] is True
    z = filme.zustand()
    assert z["fehler_art"] == "" and z["fehler"] == "" and z["server_version"] == "12.1.0"


# ------------------------------------------------ kein Ausbruch ohne Zählung

def test_antwort_ohne_json_bricht_nicht_aus_dem_abzug(tmp_path, monkeypatch):
    """Nebenfund 24.09.: Liefert der Server bei 200 eine Wartungs- oder
    Proxy-Seite, flog die Ausnahme aus katalog_abzug() — ohne Zustand, ohne
    Backoff, und der 5-s-Ticker stieß sofort den nächsten Abzug an."""
    html = b"<html><body>Wartung</body></html>"
    for name, antworten in (
            ("anmeldung", None),
            ("katalog", [("/System/Info", 200, {"Version": "12.1.0"}),
                         ("/Users/u1/Items?", 200, html)])):
        _einrichten(tmp_path / name, monkeypatch)
        if antworten is None:
            monkeypatch.setattr(filme, "_http", lambda *a, **k: (200, html))
        else:
            monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", antworten=antworten))
        r = filme.katalog_abzug()               # darf NICHT werfen
        assert r["ok"] is False, name
        z = filme.zustand()
        assert z["fehler_art"] == "server" and z["fehlversuche"] == 1, (name, z)
        assert filme.sync_faellig(alter_s=0) is False, f"{name}: kein Backoff nach Nicht-JSON"


def test_unerwartete_ausnahme_im_abzug_wird_gezaehlt(tmp_path, monkeypatch):
    """Die äußere Schicht: was auch immer im Abzug schiefgeht, es wird notiert
    und bekommt einen Backoff, statt aus dem Start-Faden zu fliegen."""
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12"))

    def kaputt(it):
        raise RuntimeError("unerwartet")
    monkeypatch.setattr(filme, "_eintrag", kaputt)
    assert filme.katalog_abzug()["ok"] is False
    z = filme.zustand()
    assert z["fehlversuche"] == 1 and z["fehler_art"] == "server", z
    assert filme.sync_faellig(alter_s=0) is False


def test_folgenliste_ohne_json_wirft_nicht(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", antworten=[
        ("/System/Info", 200, {"Version": "12.1.0"}),
        ("/Shows/s1/Episodes", 200, b"<html>Wartung</html>")]))
    assert filme.episoden("s1") == []
    # Auch die ANMELDUNG kann eine Wartungsseite liefern: keine Ausnahme in die
    # Route, und die nächste Kachel meldet sich nicht sofort wieder an.
    _einrichten(tmp_path / "anmeldung", monkeypatch)
    rufe = []

    def wartung(url, daten=None, kopf=None, timeout=15):
        rufe.append(url)
        return 200, b"<html>Wartung</html>"
    monkeypatch.setattr(filme, "_http", wartung)
    assert filme.episoden("s1") == [] and filme.bild_holen("f1") is None
    assert len(rufe) == 1, rufe


# ------------------------------------------------------ Backoff mit Gedächtnis

def test_backoff_uebersteht_den_selbst_neustart_und_ist_gestaffelt(tmp_path, monkeypatch):
    """Der Backoff stand nur im Prozess-Speicher; der Selbst-Neustart bei jeder
    Code-Änderung setzte ihn zurück, und weil der Spiegel älter als 6 h war, war
    der Abzug sofort wieder fällig. Jetzt zählt filme_zustand.json: 30 min,
    1 h, 2 h, 4 h, höchstens 6 h."""
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", anmeldung=500))
    filme.katalog_abzug()
    _neustart()
    assert filme.sync_faellig(alter_s=0) is False, "Neustart vergisst den Backoff"
    assert [filme.backoff_s(n) for n in range(7)] == [0, 1800, 3600, 7200, 14400,
                                                      21600, 21600]
    _zurueckdrehen(31 * 60)
    assert filme.sync_faellig(alter_s=0) is True
    filme.katalog_abzug()                       # zweiter Fehlschlag: Stufe 1 h
    _neustart()
    _zurueckdrehen(31 * 60)
    assert filme.sync_faellig(alter_s=0) is False, "Stufe 2 muss länger warten"
    _zurueckdrehen(30 * 60)
    assert filme.sync_faellig(alter_s=0) is True
    filme.fam.json_aendern(filme._pfade["zustand"],
                           lambda d: d.update(fehlversuche=9, letzter_versuch=time.time()))
    _zurueckdrehen(5.9 * 3600)
    assert filme.sync_faellig(alter_s=0) is False
    _zurueckdrehen(0.2 * 3600)
    assert filme.sync_faellig(alter_s=0) is True, "höchstens 6 h Pause"


def test_knopf_abgleichen_bleibt_trotz_backoff_frei(tmp_path, monkeypatch):
    """⟳ Abgleichen umgeht die Staffel: JB darf jederzeit selbst anstoßen."""
    import youtube_app as app
    _einrichten(tmp_path, monkeypatch)
    filme.fam.json_schreiben(filme._pfade["zustand"], {
        "fehlversuche": 9, "letzter_versuch": time.time(), "fehler": "x",
        "fehler_art": "server"})
    assert filme.sync_faellig(alter_s=0) is False
    gerufen = threading.Event()
    monkeypatch.setattr(filme, "katalog_abzug", gerufen.set)
    assert app._filme_abzug_anstossen() is True
    assert gerufen.wait(5), "der Knopf-Weg wurde vom Backoff blockiert"


def test_kein_token_und_kein_passwort_in_dateien(tmp_path, monkeypatch):
    """Zugangsdaten nur im Keyring: weder Token noch Passwort (auch kein Hash
    als Ersatz-Merkmal) landen in einer Datei des Film-Teils."""
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12", lehnt_ab=True)
    monkeypatch.setattr(filme, "_http", jf)
    filme.katalog_abzug()
    _neustart()
    jf2 = JellyfinAttrappe("12")
    monkeypatch.setattr(filme, "_http", jf2)
    filme.katalog_abzug()
    filme.fortschritt("f1", 10)
    for wurzel, _ordner, dateien in os.walk(tmp_path):
        for name in dateien:
            inhalt = open(os.path.join(wurzel, name), "rb").read().decode("utf-8", "replace")
            assert "TOKEN-" not in inhalt, name
            assert PASSWORT not in inhalt, name
    z = json.load(open(filme._pfade["zustand"], encoding="utf-8"))
    assert set(z) <= {"letzter_versuch", "letzter_erfolg", "anzahl", "fehler",
                      "fehlversuche", "fehler_seit", "fehler_art", "server_version"}, z


# ------------------------------------------------------ Route + Anzeige

def _handler(pfad, lokal=True):
    """Eine Handler-Instanz OHNE Server und ohne Socket: die Antwort landet in
    einem Puffer. So läuft die echte Route, ohne Port 8776 anzufassen."""
    import email.message
    import io

    import youtube_app as app
    h = object.__new__(app.Handler)
    h.path, h.command, h.request_version = pfad, "GET", "HTTP/1.1"
    h.requestline = f"GET {pfad} HTTP/1.1"
    h.client_address = ("127.0.0.1" if lokal else "192.168.178.50", 50000)
    h.headers = email.message.Message()
    h.wfile = io.BytesIO()
    h._hat_zugriff = lambda: True                # Kopplung ist hier nicht das Thema
    return h


def _antwort_von(h):
    roh = h.wfile.getvalue()
    kopf, _, rumpf = roh.partition(b"\r\n\r\n")
    status = int(kopf.split(b" ", 2)[1]) if kopf else 0
    return status, rumpf


def _route(pfad, lokal=True):
    h = _handler(pfad, lokal)
    h.do_GET()
    status, rumpf = _antwort_von(h)
    return status, (json.loads(rumpf) if rumpf.startswith(b"{") else rumpf)


def test_zustand_route_nennt_die_fehlerart_und_maskiert_fremde_geraete(tmp_path, monkeypatch):
    """Am PC der Wortlaut, im WLAN nur die Fehlerart mit einem Kurztext ohne
    Adresse und ohne Rohtext (der kann eine urllib-Ausnahme MIT Renés Adresse
    enthalten). Vorher bekam jedes fremde Gerät „Server nicht erreichbar" —
    auch wenn der Server erreichbar war und nur die Anmeldeform ablehnte."""
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", lehnt_ab=True))
    filme.katalog_abzug()
    filme.fam.json_aendern(filme._pfade["zustand"], lambda d: d.__setitem__(
        "fehler", "Items-Abruf: <urlopen error https://jelly.example/geheim>"))
    st, z = _route("/api/filme/zustand")
    assert st == 200 and z["fehler_art"] == "merkmal_abgelehnt"
    assert "jelly.example" in z["fehler"], "am PC der volle Wortlaut"
    st, z = _route("/api/filme/zustand", lokal=False)
    assert z["fehler_art"] == "merkmal_abgelehnt" and z["server_version"] == "12.1.0"
    assert "jelly.example" not in json.dumps(z), "Adresse an ein fremdes Gerät"
    assert "Anmeldeform" in z["fehler"], z["fehler"]


def _warnung(tmp_path, z):
    from test_medientasten_verhalten import _js_funktion, _lauf, _pc
    q = _pc()
    (e,) = _lauf(tmp_path, _js_funktion(q, "filmDauerGrob"), _js_funktion(q, "filmWarnung"),
                 "aus({w: filmWarnung(" + json.dumps(z) + ")});")
    return e["w"]


BASIS_Z = {"zugang": True, "fehler": "Items-Abruf HTTP 401 trotz frischer Anmeldung",
           "still_seit_s": 20 * 3600, "anzahl": 5100, "server_version": "12.1.0"}


def test_film_warnung_sagt_je_fehlerart_was_los_ist(tmp_path):
    """filmWarnung mit dem ECHTEN Seiten-JavaScript (deno). Der Ausfall vom
    23./24.09. hieß dort „Renés Server antwortet seit … nicht" — irreführend:
    er antwortete, er lehnte nur die Anmeldeform ab."""
    w = _warnung(tmp_path, dict(BASIS_Z, fehler_art="merkmal_abgelehnt"))
    assert "antwortet" not in w and "Anmeldeform" in w and "12.1.0" in w, w
    assert "5100" in w, "der Hinweis auf den gezeigten Spiegel fehlt"
    w = _warnung(tmp_path, dict(BASIS_Z, fehler_art="anmeldung_abgelehnt"))
    assert "Passwort" in w and "Sync-Jellyfin" in w and "antwortet" not in w, w
    w = _warnung(tmp_path, dict(BASIS_Z, fehler_art="drossel"))
    assert "bremst" in w and "René fragen" in w and "antwortet" not in w, w
    w = _warnung(tmp_path, dict(BASIS_Z, fehler_art="netz", fehler="Renés Server nicht erreichbar"))
    assert "antwortet seit" in w and "nicht" in w, w
    w = _warnung(tmp_path, dict(BASIS_Z, fehler_art="server", fehler="Items-Abruf HTTP 503"))
    assert "HTTP 503" in w and "antwortet seit" not in w, w
    # Alter Zustand ohne Fehlerart (vor dem 24.09. geschrieben): wie bisher.
    alt = dict(BASIS_Z)
    assert "antwortet seit" in _warnung(tmp_path, alt)
    # Calm: ein einzelner kurzer Fehlschlag bleibt still — auch mit Fehlerart.
    assert _warnung(tmp_path, dict(BASIS_Z, fehler_art="merkmal_abgelehnt",
                                   still_seit_s=3600)) == ""


def test_fernsehmodus_zeigt_dieselbe_ehrliche_warnung(tmp_path):
    """Der Fernsehmodus nutzt dieselbe Warnung (Gegenprüfung 24.09.: mittesten)."""
    from test_medientasten_verhalten import _js_funktion, _lauf, _pc
    q = _pc()
    z = dict(BASIS_Z, fehler_art="merkmal_abgelehnt")
    (e,) = _lauf(tmp_path, _js_funktion(q, "filmDauerGrob"), _js_funktion(q, "filmWarnung"),
                 _js_funktion(q, "tvKopfMalen"), r"""
const TV_TABS=[]; var tvTab='home', tvProfile=[];
function tvProfil(){return 'standard';} function esc(t){return String(t);}
document.createElement=()=>({});
const gesetzt=[];
_els['tv-kopf']={innerHTML:'', insertAdjacentElement(wo,el){gesetzt.push([wo,el.id,el.textContent]);}};
var tvFilmZustand=""" + json.dumps(z) + r""";
tvKopfMalen();
aus({gesetzt});
""")
    ((wo, ident, text),) = e["gesetzt"]
    assert ident == "tv-warnung" and "Anmeldeform" in text and "antwortet" not in text, text
