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


# ------------------------------------------------ Folgenliste: leer oder gestört?

def test_folgenliste_nennt_den_grund_und_bleibt_eine_liste(tmp_path, monkeypatch):
    """Befund 3: episoden() gab bei JEDEM Fehler still [] zurück — die Oberfläche
    zeigte eine Serie ohne Folgen, obwohl nur der Zugang gestört war. Der
    Rückgabetyp von episoden() bleibt eine Liste (Gegenprüfung 24.09.); der Grund
    kommt über episoden_mit_grund() in die Route."""
    faelle = [
        ("ok", JellyfinAttrappe("12"), 3, ""),
        ("merkmal", JellyfinAttrappe("12", lehnt_ab=True), 0, "zugang"),
        ("passwort", JellyfinAttrappe("12", anmeldung=401), 0, "zugang"),
        ("drossel", JellyfinAttrappe("12", anmeldung=403), 0, "zugang"),
        ("server", JellyfinAttrappe("12", antworten=[("/System/Info", 200, {}),
                                                     ("/Shows/s1/Episodes", 502, b"")]), 0, "netz"),
        ("unbekannt", JellyfinAttrappe("12", antworten=[("/System/Info", 200, {}),
                                                        ("/Shows/s1/Episodes", 404, b"")]), 0, ""),
    ]
    for name, jf, anzahl, grund in faelle:
        _einrichten(tmp_path / name, monkeypatch)
        monkeypatch.setattr(filme, "_http", jf)
        liste, fehler = filme.episoden_mit_grund("s1")
        assert (len(liste), fehler) == (anzahl, grund), name
        _neustart()
        assert isinstance(filme.episoden("s1"), list), name
    _einrichten(tmp_path / "netz", monkeypatch)

    def weg(url, daten=None, kopf=None, timeout=15):
        raise urllib.error.URLError("timed out")
    monkeypatch.setattr(filme, "_http", weg)
    assert filme.episoden_mit_grund("s1") == ([], "netz")


def test_folgen_route_meldet_den_grund_additiv(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", lehnt_ab=True))
    st, antwort = _route("/api/filme/episoden?id=s1")
    assert st == 200 and antwort == {"items": [], "fehler": "zugang"}, antwort
    _einrichten(tmp_path / "ok", monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12"))
    st, antwort = _route("/api/filme/episoden?id=s1", lokal=False)
    assert st == 200 and len(antwort["items"]) == 3 and "fehler" not in antwort, antwort


def _info_lauf(tmp_path, episoden_antwort, nachher=""):
    from test_medientasten_verhalten import _js_funktion, _js_zeile, _lauf, _pc
    q = _pc()
    teile = [_js_zeile(q, "let tvHeroId="), _js_zeile(q, "let tvInfoStapel="),
             _js_zeile(q, "let tvInfoDaten=")] + [_js_funktion(q, n) for n in (
                 "tvInfo", "tvInfoMalen", "tvQualitaet", "tvTon", "tvSerienPlay",
                 "folgenFehlerText")]
    (e,) = _lauf(tmp_path, *teile, r"""
function esc(t){return String(t==null?'':t);} function tvInfoFokusMalen(){} function tvKey(){}
function tvProfil(){return 'standard';} function tvpLandePos(){return 0;}
const toasts=[], plays=[]; function toast(t){toasts.push(t);} function filmePlay(id,p){plays.push(id);}
document.body={appendChild(el){el.parentNode=this;}};
_els['tv-info']={style:{}, innerHTML:'', parentNode:null};
const EPS=""" + json.dumps(episoden_antwort) + r""";
globalThis.fetch=async(u)=>({json:async()=>(
  u.startsWith('/api/filme/detail')?{id:'s1',typ:'serie',titel:'Dark'}:
  u.startsWith('/api/filme/mehrwie')?{items:[]}:
  u.startsWith('/api/filme/episoden')?EPS:{})});
await tvInfo('s1');
""" + nachher + r"""
aus({html:_els['tv-info'].innerHTML, toasts, plays});
""")
    return e


def test_info_seite_zeigt_gestoerten_zugang_statt_leerer_staffel(tmp_path):
    """Die Info-Seite einer Serie (echtes Seiten-JavaScript, deno): mit
    fehler:'zugang' erscheint der Hinweis statt einer stillen, leeren Staffel;
    ▶ Weiterschauen sagt dasselbe statt „Keine Folgen gefunden"."""
    e = _info_lauf(tmp_path, {"items": [], "fehler": "zugang"}, "tvSerienPlay();")
    assert "Folgen gerade nicht abrufbar – Zugang zu Renés Server gestört" in e["html"], e["html"]
    assert e["toasts"] and "Zugang zu Renés Server gestört" in e["toasts"][-1], e["toasts"]
    assert e["plays"] == []
    e = _info_lauf(tmp_path, {"items": [], "fehler": "netz"})
    assert "Folgen gerade nicht abrufbar" in e["html"] and "Zugang" not in e["html"]
    # Ohne Fehler (Serie wirklich ohne Folgen) bleibt alles wie bisher.
    e = _info_lauf(tmp_path, {"items": []}, "tvSerienPlay();")
    assert "nicht abrufbar" not in e["html"] and e["toasts"] == ["🎬 Keine Folgen gefunden."]
    e = _info_lauf(tmp_path, {"items": [{"id": "e1", "staffel": 1, "folge": 1, "titel": "Pilot",
                                         "position_s": 0, "gesehen": False}]})
    assert "Staffel 1" in e["html"] and "nicht abrufbar" not in e["html"]


# ------------------------------------------ Fortschritt, „gesehen" und Warteschlange

def _queue():
    return filme._queue_lesen()


def _meldungen(jf):
    """(art, item, position_s) je Fortschritts-/Gesehen-Ruf, in Reihenfolge."""
    out = []
    for pfad, _k, daten in jf.rufe:
        if pfad.startswith("/Sessions/Playing/Progress"):
            out.append(("progress", daten["ItemId"], daten["PositionTicks"] // 10_000_000))
        elif "/PlayedItems/" in pfad:
            out.append(("gesehen", pfad.rsplit("/", 1)[1], None))
    return out


def _queue_setzen(eintraege):
    filme.fam.json_schreiben(filme._pfade["queue"], eintraege)


def test_gesehen_wird_geprueft_und_sonst_nachgereicht(tmp_path, monkeypatch):
    """folgenende.md Befund 3: PlayedItems lief ohne Statusprüfung. Scheiterte nur
    dieser Ruf, ging „gesehen" still verloren — nichts kam in die Warteschlange."""
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12")
    monkeypatch.setattr(filme, "_http", jf)
    assert filme.fortschritt("f1", 2350, gesehen=True) is True
    assert _meldungen(jf) == [("progress", "f1", 2350), ("gesehen", "f1", None)]
    assert _queue() == []
    # PlayedItems scheitert (500): die Meldung darf nicht verloren gehen.
    _einrichten(tmp_path / "kaputt", monkeypatch)
    jf = JellyfinAttrappe("12", antworten=[("/System/Info", 200, {}),
                                           ("/Sessions/Playing/Progress", 204, b""),
                                           ("/PlayedItems/", 500, b"")])
    monkeypatch.setattr(filme, "_http", jf)
    assert filme.fortschritt("f1", 2350, gesehen=True) is False
    q = _queue()
    assert len(q) == 1 and q[0]["item"] == "f1" and q[0]["gesehen"] is True, q
    # Netz wieder gesund: nachreichen schickt NUR PlayedItems (die Stelle zählt
    # bei „gesehen" nicht mehr und darf nichts Neueres überschreiben).
    jf.antworten = JellyfinAttrappe("12").antworten      # derselbe Server, wieder gesund
    jf.rufe.clear()
    assert filme.fortschritt_nachreichen() == 1
    assert _meldungen(jf) == [("gesehen", "f1", None)], _meldungen(jf)
    assert _queue() == []


def test_gesehen_heilt_einen_401_mit_genau_einer_anmeldung(tmp_path, monkeypatch):
    _einrichten(tmp_path, monkeypatch)
    jf = JellyfinAttrappe("12")
    erst = []

    def http(url, daten=None, kopf=None, timeout=15):
        if "/PlayedItems/" in url and not erst:
            erst.append(1)
            jf.entwertet.add(jf.tokens[-1])      # zweite Sitzung: Token 1 ist weg
            return 401, b""
        return jf(url, daten, kopf, timeout)
    monkeypatch.setattr(filme, "_http", http)
    assert filme.fortschritt("f1", 2350, gesehen=True) is True
    assert jf.anmeldungen() == 2 and _queue() == []


def test_je_titel_nur_die_neueste_meldung(tmp_path, monkeypatch):
    """Nachreichen schickte JEDE liegengebliebene Meldung in Reihenfolge — eine
    alte Stelle überschrieb danach eine neuere desselben Titels (Gegenprüfung
    folgenende.md). Jetzt zählt je Titel nur die jüngste; die älteren sind mit
    ihr erledigt."""
    _einrichten(tmp_path, monkeypatch)
    _queue_setzen([
        {"item": "f1", "position_s": 100, "gesehen": False, "ts": 1.0},
        {"item": "s1", "position_s": 50, "gesehen": False, "ts": 1.5},
        {"item": "f1", "position_s": 900, "gesehen": False, "ts": 2.0}])
    jf = JellyfinAttrappe("12")
    monkeypatch.setattr(filme, "_http", jf)
    assert filme.fortschritt_nachreichen() == 2
    assert _meldungen(jf) == [("progress", "s1", 50), ("progress", "f1", 900)], _meldungen(jf)
    assert _queue() == []


def test_dauerhafter_4xx_blockiert_die_warteschlange_nicht(tmp_path, monkeypatch):
    """Ein Eintrag, den Jellyfin mit 4xx abweist (z. B. keine gültige Kennung),
    geht nie durch. Vorher hielt er über `break` alle Meldungen dahinter auf —
    still, denn die Warteschlange wird nirgends angezeigt. Jetzt: markiert und
    nie wieder gesendet (SENDE_KAPUTT wie in SyncFindus), aber NICHT gelöscht."""
    _einrichten(tmp_path, monkeypatch)
    _queue_setzen([
        {"item": "abc123", "position_s": 10, "gesehen": False, "ts": 1.0},
        {"item": "f1", "position_s": 700, "gesehen": False, "ts": 2.0}])
    jf = JellyfinAttrappe("12")

    def http(url, daten=None, kopf=None, timeout=15):
        if (daten or {}).get("ItemId") == "abc123":
            jf.rufe.append((url, dict(kopf or {}), daten))
            return 400, b""
        return jf(url, daten, kopf, timeout)
    monkeypatch.setattr(filme, "_http", http)
    assert filme.fortschritt_nachreichen() == 1
    q = _queue()
    assert [(m["item"], m.get("abgewiesen")) for m in q] == [("abc123", True)], q
    vorher = len(jf.rufe)
    assert filme.fortschritt_nachreichen() == 0
    assert len(jf.rufe) == vorher, "ein abgewiesener Eintrag wurde erneut gesendet"
    # Direkt gemeldet und abgewiesen: gemerkt (nichts still verworfen), aber nie
    # wieder gesendet.
    assert filme.fortschritt("abc123", 20) is False
    assert all(m.get("abgewiesen") for m in _queue())


def test_abgelehnte_anmeldeform_ist_kein_kaputter_eintrag(tmp_path, monkeypatch):
    """401 auch nach frischer Anmeldung ist ein Server-/Zugangsproblem, kein
    Fehler des Eintrags: nichts wird als abgewiesen markiert, alles bleibt für
    den nächsten Lauf liegen."""
    _einrichten(tmp_path, monkeypatch)
    eintraege = [{"item": "f1", "position_s": 700, "gesehen": False, "ts": 2.0},
                 {"item": "s1", "position_s": 5, "gesehen": True, "ts": 3.0}]
    _queue_setzen(eintraege)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", lehnt_ab=True))
    assert filme.fortschritt_nachreichen() == 0
    assert _queue() == eintraege
    # Ebenso 403 (nicht berechtigt / gedrosselt) und 429: Zugang oder Zeit,
    # nicht der Eintrag — liegen lassen, nicht abweisen.
    for status in (403, 429):
        _einrichten(tmp_path / str(status), monkeypatch)
        _queue_setzen(eintraege)
        monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12", antworten=[
            ("/System/Info", 200, {}), ("/Sessions/Playing/Progress", status, b""),
            ("/PlayedItems/", status, b"")]))
        assert filme.fortschritt_nachreichen() == 0
        assert _queue() == eintraege, status


# ------------------------------------------------------ Strom-Adresse + Proxy

MARKE = "https://marke.example/strom"


def test_strom_adresse_entsteht_an_einer_stelle(tmp_path, monkeypatch):
    """Befund 4 bleibt eine Messfrage (nimmt Jellyfin 12 `api_key=` in der Adresse
    noch an?). Umgestellt wird erst nach der Live-Messung — aber dann an EINER
    Stelle. Aufruf statt Erwähnung: VLC-Start, Browser-Proxy und Szenen-Vorschau
    bekommen alle, was `_strom_adresse` baut."""
    import subprocess

    import youtube_app as app
    _einrichten(tmp_path, monkeypatch)
    monkeypatch.setattr(filme, "_http", JellyfinAttrappe("12"))
    assert filme.katalog_abzug()["ok"]
    # Form heute (unverändert): Token als api_key in der Adresse, Kennung kodiert
    # — eine Kennung vom Client darf keine andere Jellyfin-Route ansteuern.
    assert filme.stream_url("f1") == ("https://jelly.example/Videos/f1/stream"
                                      "?static=true&api_key=TOKEN-1")
    assert "/System/Info" not in filme.stream_url("../../System/Info?x=")
    monkeypatch.setattr(filme, "_strom_adresse", lambda basis, iid, tok: f"{MARKE}/{iid}")
    assert filme.stream_url("f1") == MARKE + "/f1"
    # Szenen-Vorschau (ffmpeg)
    befehle = []

    def fake_run(cmd, **kw):
        befehle.append(cmd)
        return None
    monkeypatch.setattr(subprocess, "run", fake_run)
    filme.snippet_backen("f1")
    assert befehle and befehle[0][befehle[0].index("-i") + 1] == MARKE + "/f1"
    # VLC-Start (POST /api/filme/play)
    vlc = []
    monkeypatch.setattr(app, "vlc_kommando", lambda d: vlc.append(d) or {"ok": True})
    import email.message
    import io
    h = _handler("/api/filme/play")
    h.command = "POST"
    rumpf = json.dumps({"id": "f1"}).encode()
    h.headers = email.message.Message()
    h.headers["Content-Length"] = str(len(rumpf))
    h.rfile = io.BytesIO(rumpf)
    h.do_POST()
    assert vlc and vlc[0]["url"] == MARKE + "/f1", vlc
    # Browser-Proxy (GET /api/filme/direkt)
    geoeffnet = []

    def fake_urlopen(req, timeout=None):
        geoeffnet.append(req.full_url)
        raise urllib.error.URLError("Testende")
    monkeypatch.setattr(app.urllib.request, "urlopen", fake_urlopen)
    _route("/api/filme/direkt?id=f1")
    assert geoeffnet == [MARKE + "/f1"], geoeffnet


def test_browser_proxy_antwortet_bei_jellyfin_fehler_ehrlich(tmp_path, monkeypatch):
    """Gegenprüfung 24.09. (Befund 4, Korrektur 3): HTTPError ist ein OSError, und
    `except (OSError, ConnectionError): pass` schickte GAR KEINE Antwort — der
    Browser sah einen abgebrochenen Strom ohne Meldung. Jetzt: Jellyfins Status
    und ein kurzer Text; nie die Adresse (sie trägt das Token)."""
    import io

    import youtube_app as app
    geheim = "https://jelly.example/Videos/f1/stream?static=true&api_key=GEHEIM-TOKEN"
    monkeypatch.setattr(filme, "stream_url", lambda iid: geheim)
    for fehler, status_soll, wort in (
            (urllib.error.HTTPError(geheim, 401, "Unauthorized", {}, io.BytesIO(b"")), 401, "401"),
            (urllib.error.HTTPError(geheim, 503, "Unavailable", {}, io.BytesIO(b"")), 503, "503"),
            (urllib.error.URLError("getaddrinfo failed: jelly.example"), 502, "nicht erreichbar")):
        def fake_urlopen(req, timeout=None, _f=fehler):
            raise _f
        monkeypatch.setattr(app.urllib.request, "urlopen", fake_urlopen)
        status, antwort = _route("/api/filme/direkt?id=f1", lokal=False)
        assert status == status_soll, (status, antwort)
        assert wort in antwort["fehler"], antwort
        blob = json.dumps(antwort)
        assert "GEHEIM-TOKEN" not in blob and "jelly.example" not in blob, blob


class _Strom:
    """urlopen-Antwort (Kontextmanager) für die Vorprobe."""
    status = 206

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_transcoder_zweig_antwortet_bei_jellyfin_fehler_ehrlich(tmp_path, monkeypatch):
    """Prüfung Runde 1 (mittel): Der tc=1-Zweig (HEVC/AC3/DTS im Browser und der
    Rückfall nach jedem Fehler im Direkt-Zweig) schickte `200` ab, BEVOR ffmpeg
    ein Byte hatte. Lehnte Jellyfin die Adresse ab, bekam der Browser 200 mit
    leerem Strom. Jetzt fragt der Server vorab EIN Byte (Range 0-0) und
    antwortet bei einem Fehler wie der Direkt-Zweig — ffmpeg startet dann gar
    nicht. Nie die Adresse (sie trägt das Token)."""
    import io

    import youtube_app as app
    geheim = "https://jelly.example/Videos/f1/stream?static=true&api_key=GEHEIM-TOKEN"
    monkeypatch.setattr(filme, "stream_url", lambda iid: geheim)
    monkeypatch.setattr(app, "_ffmpeg_exe", lambda: r"C:\bin\ffmpeg.exe")
    gestartet, jellyfin = [], {"gibt_heraus": False}

    class Prozess:
        """ffmpeg liest die Adresse selbst: lehnt Jellyfin ab, kommt NICHTS."""
        def __init__(self, cmd):
            gestartet.append(cmd)
            self.stdout = io.BytesIO(b"FMP4" * 4 if jellyfin["gibt_heraus"] else b"")

        def kill(self):
            pass
    monkeypatch.setattr(app, "_tc_starten", Prozess)
    pfad = "/api/filme/direkt?id=f1&tc=1&vcopy=1&start=0"
    for fehler, status_soll, wort in (
            (urllib.error.HTTPError(geheim, 401, "Unauthorized", {}, io.BytesIO(b"")), 401, "401"),
            (urllib.error.HTTPError(geheim, 404, "Not Found", {}, io.BytesIO(b"")), 404, "404"),
            (urllib.error.URLError("getaddrinfo failed: jelly.example"), 502, "nicht erreichbar"),
            (TimeoutError("timed out"), 502, "nicht erreichbar")):
        def fake_urlopen(req, timeout=None, _f=fehler):
            raise _f
        monkeypatch.setattr(app.urllib.request, "urlopen", fake_urlopen)
        status, antwort = _route(pfad, lokal=False)
        assert status == status_soll, (fehler, status, antwort)
        assert wort in antwort["fehler"], antwort
        blob = json.dumps(antwort)
        assert "GEHEIM-TOKEN" not in blob and "jelly.example" not in blob, blob
        assert gestartet == [], "ffmpeg darf bei abgelehntem Strom nicht starten"
    # Gesund: die Vorprobe fragt genau ein Byte, dann streamt ffmpeg wie bisher.
    proben = []

    def gesund(req, timeout=None):
        proben.append((req.full_url, req.get_header("Range")))
        return _Strom()
    monkeypatch.setattr(app.urllib.request, "urlopen", gesund)
    jellyfin["gibt_heraus"] = True
    status, rumpf = _route(pfad, lokal=False)
    assert status == 200 and rumpf == b"FMP4" * 4, (status, rumpf)
    assert proben == [(geheim, "bytes=0-0")], proben
    assert len(gestartet) == 1 and geheim in gestartet[0]


def test_alter_zustand_ohne_fehlerart_wird_nicht_nachtraeglich_eingeordnet(tmp_path, monkeypatch):
    """JBs filme_zustand.json vom 24.09. trägt „Items-Abruf HTTP 401" OHNE
    fehler_art. Daraus darf keine erfundene Einordnung werden: Anzeige und
    Maskierung bleiben wie bisher, bis der nächste Abzug die Art selbst notiert."""
    _einrichten(tmp_path, monkeypatch)
    filme.fam.json_schreiben(filme._pfade["zustand"], {
        "letzter_versuch": time.time(), "fehler": "Items-Abruf HTTP 401",
        "fehlversuche": 51, "fehler_seit": time.time() - 18 * 3600})
    assert filme.zustand()["fehler_art"] == ""
    st, z = _route("/api/filme/zustand", lokal=False)
    assert z["fehler"] == "Server nicht erreichbar" and z["fehler_art"] == "", z
