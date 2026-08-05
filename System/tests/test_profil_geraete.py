# -*- coding: utf-8 -*-
"""Sicherheitsnetz Teilprojekt 3 (Profile + Geraete). Der Geraete-Riegel ist
JBs PFLICHT-Waechter: Externe kommen NUR mit Zugangsdaten an die Bibliothek."""
import os
import sys
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
    pg._schreiben(d)
    assert all(g["id"] != a["geraet_id"] for g in pg.geraete_liste()), \
        "abgelaufene Pairing-Anfragen muessen verschwinden"


def test_riegel_verkabelt():
    # PFLICHT-Waechter (Spec 'Zugriff & Sicherheit'): der Handler prueft den
    # Geraete-Token, Pairing-Wege sind frei, Verwaltung NUR lokal.
    quelle = open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    i = quelle.index("def _hat_zugriff")
    block = quelle[i:i + 1600]
    assert "profil_geraete.geraet_ok" in block, "Geraete-Token wird nicht geprueft"
    assert "/api/geraet_anmelden" in block and "/api/geraet_status" in block, \
        "Pairing muss VOR dem Token erreichbar sein"
    for geschuetzt in ("/api/geraete", "/api/geraet_qr"):
        j = quelle.index(f'"{geschuetzt}"')
        assert "_ist_lokal" in quelle[j:j + 300], geschuetzt + " muss nur-PC sein"
    for geschuetzt in ("/api/geraet_bestaetigen", "/api/geraet_entfernen"):
        j = quelle.index(f'"{geschuetzt}"')
        assert "_ist_lokal" in quelle[j:j + 300], geschuetzt + " muss nur-PC sein"
    assert "PAIRING_HTML" in quelle, "unbekanntes LAN-Geraet muss die Koppel-Seite sehen"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
