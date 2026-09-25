# -*- coding: utf-8 -*-
"""Sicherheitsnetz Teilprojekt 3 (Profile + Geraete). Der Geraete-Riegel ist
JBs PFLICHT-Waechter: Externe kommen NUR mit Zugangsdaten an die Bibliothek."""
import os
import sys
import threading
import time

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import profil_geraete as pg  # noqa: E402


def _einrichten(tmp_path):
    pg.einrichten(str(tmp_path))


def test_profile_grundlagen(tmp_path):
    _einrichten(tmp_path)
    assert pg.profil_liste()[0]["id"] == "standard", "Standard-Profil fehlt"
    p = pg.profil_anlegen("Anna", "🦁")
    assert p["id"] and p["name"] == "Anna" and p["emoji"] == "🦁"
    assert pg.profil_gibt_es(p["id"]) and not pg.profil_gibt_es("nix")
    assert pg.profil_anlegen("") is None, "leerer Name darf nichts anlegen"


def test_pairing_kette_und_riegel(tmp_path):
    # Der volle Fluss: anmelden -> Code; VOR der Freigabe kein Zugriff;
    # Freigabe NUR ueber die PC-Funktion; Token EINMALIG abholbar; Widerruf
    # macht den Token sofort wertlos (JB: einzeln widerrufbar).
    _einrichten(tmp_path)
    a = pg.geraet_anmelden("Wohnzimmer-TV")
    assert len(a["code"]) == 6 and a["geraet_id"]
    assert pg.geraet_ok("irgendwas") is None
    # Abholen VOR der Freigabe: nichts (Riegel!)
    assert pg.geraet_token_abholen(a["geraet_id"], a["code"]) is None
    # PC gibt frei (Profil-Zuordnung; unbekanntes Profil faellt auf standard)
    assert pg.geraet_bestaetigen(a["geraet_id"], "gibtsnicht") is True
    t = pg.geraet_token_abholen(a["geraet_id"], a["code"])
    assert t and t["token"] and t["profil"] == "standard"
    assert pg.geraet_token_abholen(a["geraet_id"], a["code"]) is None, \
        "Code muss nach dem Abholen entwertet sein"
    assert pg.geraet_token_abholen(a["geraet_id"], "FALSCH") is None
    assert pg.geraet_ok(t["token"]) == "standard", "Riegel-Kern: Token -> Profil"
    # Liste fuers UI traegt NIE den Token
    import json
    assert t["token"] not in json.dumps(pg.geraete_liste()), "Token-Leck in der Liste"
    # Widerruf: sofort wertlos
    gid = pg.geraete_liste()[0]["id"]
    assert pg.geraet_entfernen(gid) is True
    assert pg.geraet_ok(t["token"]) is None, "getrenntes Geraet darf NICHT mehr rein"


def test_pairing_codes_altern(tmp_path, monkeypatch):
    _einrichten(tmp_path)
    a = pg.geraet_anmelden("Alt-Handy")
    d = pg._lesen()
    d["geraete"][0]["ts"] = time.time() - pg.CODE_ALTER_S - 1
    pg.fam.json_schreiben(pg._pfade["profile"], d)
    assert all(g["id"] != a["geraet_id"] for g in pg.geraete_liste()), \
        "abgelaufene Pairing-Anfragen muessen verschwinden"


def test_riegel_verkabelt(monkeypatch):
    # PFLICHT-Waechter (Spec 'Zugriff & Sicherheit'): der Handler prueft den
    # Geraete-Token, Pairing-Wege sind frei, Verwaltung NUR lokal. Seit dem
    # 25.09.2026 am Verhalten des echten Handlers (LAN-Adresse, kein Ersatz des
    # Riegels) statt an Quelltext-Fenstern; die volle Routen-Inventur steht in
    # tests/test_wlan_rechte.py.
    import youtube_app as app
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from test_zugang_und_vertrauen import LAN, PC_IM_LAN, _anfrage
    monkeypatch.setitem(app.CFG, "fernsteuerung", True)
    monkeypatch.setitem(app.CFG, "fernsteuerung_code", "")      # nur der Geräte-Token zählt
    monkeypatch.setattr(app, "_fehlversuche", {})
    kopf = {"Host": PC_IM_LAN}
    # Unbekanntes Gerät: die Koppel-Seite statt einer kalten 403, Pairing frei
    st, _, koerper = _anfrage("/", ip=LAN, kopf=kopf)
    assert st == 200 and pg.PAIRING_HTML.encode("utf-8") == koerper
    assert _anfrage("/api/status", ip=LAN, kopf=kopf)[0] == 403
    import json
    st, _, koerper = _anfrage("/api/geraet_anmelden", methode="POST", ip=LAN, kopf=kopf,
                              rumpf={"name": "TV"})
    a = json.loads(koerper)
    assert st == 200 and a.get("code"), "Pairing muss VOR dem Token erreichbar sein"
    assert pg.geraet_bestaetigen(a["geraet_id"], "standard")
    st, _, koerper = _anfrage(f"/api/geraet_status?id={a['geraet_id']}&code={a['code']}",
                              ip=LAN, kopf=kopf)
    token = json.loads(koerper)["token"]
    # Der Token wird geprüft; Verwaltung bleibt nur-PC, auch mit Token
    assert _anfrage("/api/status", ip=LAN, kopf=dict(kopf, **{"X-Geraet": token}))[0] == 200
    assert _anfrage("/api/status", ip=LAN, kopf=dict(kopf, **{"X-Geraet": "falsch"}))[0] == 403
    mit = dict(kopf, **{"X-Geraet": token})
    for pfad in ("/api/geraete", "/api/geraet_qr"):
        assert _anfrage(pfad, ip=LAN, kopf=mit)[0] == 403, pfad + " muss nur-PC sein"
    for pfad in ("/api/geraet_bestaetigen", "/api/geraet_entfernen"):
        st, _, _ = _anfrage(pfad, methode="POST", ip=LAN, kopf=mit, rumpf={"id": a["geraet_id"]})
        assert st == 403, pfad + " muss nur-PC sein"
    assert any(g["id"] == a["geraet_id"] for g in pg.geraete_liste()), "Gerät blieb gekoppelt"


# ---------------------------------------------------------------- S8: Sperre (Gesamtpruefung 25.09.)
# profile.json wurde ohne Sperre gelesen und zurueckgeschrieben, auch beim blossen
# Pruefen eines Tokens. Ein paralleler Faden schrieb dann den alten Stand zurueck,
# und ein gerade getrenntes Geraet war wieder gekoppelt.

class _Uhr:
    """Jede Abfrage eine Stunde spaeter: so stempelte der alte Riegel bei JEDER
    Pruefung `zuletzt` und schrieb die Datei."""

    def __init__(self):
        self._t = time.time()
        self._lock = threading.Lock()

    def time(self):
        with self._lock:
            self._t += 3700
            return self._t


def _gekoppelt(name):
    a = pg.geraet_anmelden(name)
    assert pg.geraet_bestaetigen(a["geraet_id"], "standard") is True
    t = pg.geraet_token_abholen(a["geraet_id"], a["code"])
    return a["geraet_id"], t["token"]


def test_widerruf_haelt_gegen_parallele_pruefungen(tmp_path, monkeypatch):
    _einrichten(tmp_path)
    bleiben = [_gekoppelt(f"Bleibt {i}") for i in range(7)]
    weg = [_gekoppelt(f"Weg {i}") for i in range(12)]
    monkeypatch.setattr(pg, "time", _Uhr())
    start = threading.Barrier(8)
    fertig = threading.Event()
    fehler = []

    def pruefer(tok):
        start.wait()
        while not fertig.is_set():
            try:
                if pg.geraet_ok(tok) != "standard":
                    fehler.append("gekoppeltes Geraet abgewiesen")
            except Exception as e:                   # noqa: BLE001 — sammeln, unten melden
                fehler.append(repr(e))
            time.sleep(0.0005)

    def widerrufer():
        start.wait()
        try:
            for gid, _tok in weg:
                if pg.geraet_entfernen(gid) is not True:
                    fehler.append("Widerruf meldete keinen Erfolg")
                time.sleep(0.002)
        finally:
            fertig.set()

    faeden = [threading.Thread(target=pruefer, args=(tok,)) for _gid, tok in bleiben]
    faeden.append(threading.Thread(target=widerrufer))
    for f in faeden:
        f.start()
    for f in faeden:
        f.join(60)
    assert not any(f.is_alive() for f in faeden), "Faeden haengen"
    assert not fehler, fehler[:5]
    zurueck = [gid for gid, tok in weg if pg.geraet_ok(tok)]
    assert not zurueck, f"{len(zurueck)} getrennte Geraete kamen durch parallele Pruefungen zurueck"
    assert {g["id"] for g in pg.geraete_liste()} == {gid for gid, _tok in bleiben}


def test_pruefen_schreibt_nie(tmp_path, monkeypatch):
    _einrichten(tmp_path)
    _gid, tok = _gekoppelt("TV")
    pfad = tmp_path / "profile.json"
    vorher = pfad.read_bytes()
    monkeypatch.setattr(pg, "time", _Uhr())
    for _ in range(3):
        assert pg.geraet_ok(tok) == "standard"
    assert pg.geraet_ok("falsch") is None
    pg.geraete_liste()
    assert pfad.read_bytes() == vorher, "Pruefen und Auflisten duerfen profile.json nicht schreiben"


def test_nach_lesefehler_wird_nie_geschrieben(tmp_path):
    _einrichten(tmp_path)
    gid, tok = _gekoppelt("TV")
    pfad = tmp_path / "profile.json"
    kaputt = pfad.read_bytes()[:-7]                  # abgeschnitten: kein gueltiges JSON mehr
    pfad.write_bytes(kaputt)
    assert pg.geraet_anmelden("Neu") is None
    assert pg.profil_anlegen("Anna") is None
    assert pg.geraet_bestaetigen(gid, "standard") is False
    assert pg.geraet_token_abholen(gid, "ABCDEF") is None
    assert pg.geraet_entfernen(gid) is False
    assert pg.geraet_ok(tok) is None                 # fail-closed
    assert pg.geraete_liste() == []
    assert pfad.read_bytes() == kaputt, "eine unlesbare profile.json wurde ueberschrieben"


def test_parallele_aenderungen_gehen_nicht_verloren(tmp_path):
    _einrichten(tmp_path)
    start = threading.Barrier(8)
    fehler = []

    def anleger(n):
        start.wait()
        for i in range(5):
            if not pg.profil_anlegen(f"P{n}-{i}"):
                fehler.append(f"P{n}-{i}")

    faeden = [threading.Thread(target=anleger, args=(n,)) for n in range(8)]
    for f in faeden:
        f.start()
    for f in faeden:
        f.join(60)
    assert not fehler, fehler
    namen = {p["name"] for p in pg.profil_liste()}
    fehlt = {f"P{n}-{i}" for n in range(8) for i in range(5)} - namen
    assert not fehlt, f"{len(fehlt)} von 40 Profilen gingen verloren"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
