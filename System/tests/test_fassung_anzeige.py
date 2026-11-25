# -*- coding: utf-8 -*-
"""Die Kopfleiste zeigt die echte Programmfassung.

Vorher stand dort ein von Hand gepflegter Stempel („Build 2026-07-14 · 143“),
der seit Juli nicht mehr mitlief, während die App bis v1.4.0 weiterwuchs. Wer
bei einer Frage auf ihn schaute, sah einen falschen Stand.
"""
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
for pfad in (MODUL_DIR, TESTS_DIR):
    if pfad not in sys.path:
        sys.path.insert(0, pfad)

import youtube_app as app  # noqa: E402
from test_zugang_und_vertrauen import _anfrage  # noqa: E402


def test_kopfleiste_zeigt_die_programmfassung():
    st, _, koerper = _anfrage("/")
    seite = koerper.decode("utf-8")
    assert st == 200
    assert 'id="buildmark"' in seite
    assert f">v{app.__version__}</span>" in seite, "die Fassung fehlt in der Kopfleiste"
    assert "/*APP_VERSION*/" not in seite, "der Platzhalter wurde nicht ersetzt"
    assert "Build 2026" not in seite, "der alte Stempel ist zurück"
