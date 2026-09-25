# -*- coding: utf-8 -*-
"""Was darf ein Gerät im WLAN? (Gesamtprüfung Gruppe 5, JB-Entscheide 7a, 25.09.2026)

Wie in test_zugang_und_vertrauen.py läuft jede Anfrage durch den ECHTEN
Handler samt echtem Riegel, ohne Server und ohne Socket. Die Helfer und die
Fixture `rechner` (Rechnername `JB-PC`, leere Versuchsbremse) kommen von dort.
"""
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
if TEST_DIR not in sys.path:
    sys.path.insert(0, TEST_DIR)

from test_zugang_und_vertrauen import (  # noqa: E402,F401  (rechner: autouse-Fixture)
    CODE, LAN, PC_IM_LAN, _anfrage, _fernsteuerung, rechner)


# ------------------------------------------------------------ 7a Punkt 8: Alias /handy weg

def test_alias_handy_ist_weg_und_m_bleibt(monkeypatch):
    """Kein Verweis, das README nennt nur /m (Abschnitt 5). Vom PC: 404 statt
    der Handy-Seite; aus dem WLAN ist /handy auch kein freier Koppel-Weg mehr."""
    st, _, koerper = _anfrage("/handy", kopf={"Host": "127.0.0.1:8776"})
    assert st == 404, koerper[:80]
    st, _, koerper = _anfrage("/m", kopf={"Host": "127.0.0.1:8776"})
    assert st == 200 and b"YTDL" in koerper
    _fernsteuerung(monkeypatch)
    st, _, _ = _anfrage("/handy", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 403, "ohne Zugangsdaten ist /handy kein freier Weg mehr"
    st, _, koerper = _anfrage("/m", ip=LAN, kopf={"Host": PC_IM_LAN})
    assert st == 200 and b"YTDL" in koerper, "/m bleibt der freie Einstieg mit Code-Eingabe"
