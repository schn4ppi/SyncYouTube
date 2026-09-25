# -*- coding: utf-8 -*-
"""Toter Code bleibt draußen (Gesamtprüfung Gruppe 7, Abschnitt 5, 25.09.2026).

Entfernt wurden: die Route `POST /api/importieren` samt `ordnerImportieren()`
und der Zweig `art:'bulk'` in `_biblio` samt `_enrich_keys` und den fünf
`bulk…`-Funktionen der Oberfläche. Beide Server-Befunde prüft je ein
Verhaltenstest durch den echten Handler.
"""
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
for _pfad in (MODUL_DIR, TEST_DIR):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import _anfrage, rechner  # noqa: E402,F401  (rechner: autouse)

PC = {"Host": "127.0.0.1:8776"}


# ------------------------------------------------------------ Server

def test_importieren_route_ist_weg(monkeypatch):
    """Seit Build 122 (60a55df, 23.07.2026) rief niemand mehr POST /api/importieren.
    Der Ordner-Import selbst bleibt (Ticker und Selbstheilung rufen ihn)."""
    aufrufe = []
    monkeypatch.setattr(app, "ordner_importieren", lambda: aufrufe.append(1) or 0)
    st, _, koerper = _anfrage("/api/importieren", methode="POST", kopf=PC, rumpf={})
    assert st == 404, koerper[:120]
    assert aufrufe == []
    assert ("POST", "/api/importieren") not in app.NUR_PC
    assert callable(app.ordner_importieren), "der Import im Ticker bleibt"


def test_bulk_zweig_in_biblio_ist_weg(monkeypatch, tmp_path):
    """Der Zweig art:'bulk' hatte keine Oberfläche mehr, trug aber eine
    Lösch-Operation. Nach dem Entfernen ändert ein solcher Rumpf nichts."""
    datei = tmp_path / "Titel [abcdefghijk].mp3"
    datei.write_bytes(b"x" * 2048)
    key = "abcdefghijk|audio"
    app._geladen[key] = {"name": datei.name, "pfad": str(datei), "titel": "Titel", "uploader": "K"}
    geloescht = []
    monkeypatch.setattr(app, "_datei_loeschen", lambda k: geloescht.append(k))
    for op, felder in (("loeschen", {}), ("vergessen", {}), ("archiv", {}),
                       ("tag", {"uploader": "Neu", "titel_suchen": "Titel", "titel_ersetzen": "X"})):
        st, _, koerper = _anfrage("/api/biblio", methode="POST", kopf=PC,
                                  rumpf={"art": "bulk", "op": op, "keys": [key], "felder": felder})
        assert st == 200, koerper[:120]
    assert geloescht == [], "kein Löschen mehr über den toten Zweig"
    assert app._geladen.get(key) == {"name": datei.name, "pfad": str(datei), "titel": "Titel", "uploader": "K"}
    assert datei.exists()
    assert not hasattr(app, "_enrich_keys"), "nur der tote Zweig rief _enrich_keys"
