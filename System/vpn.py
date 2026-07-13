# -*- coding: utf-8 -*-
"""NordVPN-Steuerung für den YouTube-Downloader.

(Das Erkennen/Auswerten von Geo-Fehlern liegt provider-unabhängig in geo.py.)

Die NordVPN-Windows-App bringt eine Kommandozeile mit:
    NordVPN.exe -c -g "United Kingdom"    verbinden (Land)
    NordVPN.exe -d                        trennen
Ob und wo wir rauskommen, prüft Nords eigene Insights-API (protected/country_code).

Regeln (nicht verhandelbar):
  - Geo-Läufe laufen IMMER ohne Konto-Cookies (deutsche Anmeldung + Auslands-IP
    provoziert sonst Konto-Sicherheitschecks).
  - War das VPN schon an (JB selbst verbunden), wird NICHTS umgeschaltet —
    dann wird nur durch den bestehenden Tunnel versucht.
  - Nach einem automatischen Verbinden wird IMMER wieder getrennt (finally).
"""
import json
import os
import subprocess
import time
import urllib.request

INSIGHTS = "https://api.nordvpn.com/v1/helpers/ips/insights"

_EXE_KANDIDATEN = (
    r"C:\Program Files\NordVPN\NordVPN.exe",
    r"C:\Program Files (x86)\NordVPN\NordVPN.exe",
)

# NordVPN-Länder (Auswahl) mit ISO-Code zum Verifizieren.
# Die Reihenfolge ist zugleich die Präferenz bei mehreren erlaubten Ländern.
LAENDER = {
    "United Kingdom": "GB", "United States": "US", "Canada": "CA", "Ireland": "IE",
    "Australia": "AU", "New Zealand": "NZ", "Netherlands": "NL", "France": "FR",
    "Italy": "IT", "Spain": "ES", "Austria": "AT", "Switzerland": "CH",
    "Belgium": "BE", "Denmark": "DK", "Norway": "NO", "Sweden": "SE",
    "Finland": "FI", "Poland": "PL", "Czech Republic": "CZ", "Portugal": "PT",
    "Japan": "JP", "Brazil": "BR", "Mexico": "MX", "South Korea": "KR",
}


def exe():
    for p in _EXE_KANDIDATEN:
        if os.path.exists(p):
            return p
    return None


def verfuegbar():
    return exe() is not None


def status(timeout=6):
    """Aktueller Netz-Status laut NordVPN-Insights: {'protected': bool, 'country_code': ...}."""
    try:
        with urllib.request.urlopen(INSIGHTS, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:                                # noqa: BLE001 — offline etc.
        return {}


def aktiv():
    return bool(status().get("protected"))


def land_waehlen(laender):
    """Bevorzugtes NordVPN-Land aus der erlaubten Liste; None wenn keins passt."""
    for name in LAENDER:
        if name in laender:
            return name
    return None


def _still(cmd):
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=subprocess.CREATE_NO_WINDOW)


def verbinden(land, timeout=60):
    """NordVPN ins Land schalten und warten, bis die Auslands-IP wirklich steht."""
    pfad = exe()
    if not pfad:
        return False
    _still([pfad, "-c", "-g", land])
    ziel_code = LAENDER.get(land)
    ende = time.time() + timeout
    while time.time() < ende:
        time.sleep(3)
        s = status()
        if s.get("protected") and (not ziel_code or s.get("country_code") == ziel_code):
            return True
    return False


def trennen(timeout=20):
    """Zurück auf die normale Verbindung (best effort)."""
    pfad = exe()
    if not pfad:
        return False
    _still([pfad, "-d"])
    ende = time.time() + timeout
    while time.time() < ende:
        time.sleep(2)
        if not status().get("protected"):
            return True
    return False
