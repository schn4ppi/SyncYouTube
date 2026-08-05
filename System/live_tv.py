# -*- coding: utf-8 -*-
"""📡 Live-TV (JB-Go 05.08., Recherche im IDEEN_RADAR): frei empfangbare,
LEGALE öffentlich-rechtliche Sender aus der gepflegten kodinerds-clean-Liste
(ARD/ZDF/Dritte/ARTE …) — m3u8-Streams, die der VLC-Motor direkt spielt.
Liste wird 24 h gecacht; tote Sender heilen sich beim nächsten Abruf.
Einbahn-Regel wie filme/geo: importiert NIE youtube_app."""
import json
import os
import re
import time
import urllib.request

import familie as fam

QUELLE = ("https://raw.githubusercontent.com/jnk22/kodinerds-iptv/master/"
          "iptv/clean/clean_tv.m3u")
CACHE_ALTER_S = 24 * 3600
_pfade = {}


def einrichten(daten_dir):
    _pfade["cache"] = os.path.join(daten_dir, "live_tv.json")


def m3u_parsen(text):
    """#EXTINF-Zeilen → Kanäle (Name, Logo, Gruppe) + folgende URL-Zeile."""
    out = []
    info = None
    for zeile in (text or "").splitlines():
        zeile = zeile.strip()
        if zeile.startswith("#EXTINF"):
            logo = re.search(r'tvg-logo="([^"]*)"', zeile)
            gruppe = re.search(r'group-title="([^"]*)"', zeile)
            name = zeile.rpartition(",")[2].strip()
            info = {"name": name, "logo": logo.group(1) if logo else "",
                    "gruppe": gruppe.group(1) if gruppe else "Sender"}
        elif zeile and not zeile.startswith("#") and info:
            info["url"] = zeile
            out.append(info)
            info = None
    return out


def kanaele(frisch=False):
    try:
        with open(_pfade["cache"], encoding="utf-8") as f:
            d = json.load(f)
        if not frisch and time.time() - (d.get("stand") or 0) < CACHE_ALTER_S:
            return d.get("kanaele") or []
    except (OSError, ValueError):
        d = {}
    try:
        with urllib.request.urlopen(QUELLE, timeout=30) as r:
            liste = m3u_parsen(r.read().decode("utf-8", "replace"))
        if liste:
            fam.json_schreiben(_pfade["cache"], {"stand": time.time(),
                                                 "kanaele": liste})
            return liste
    except Exception:                      # noqa: BLE001 — alter Cache trägt
        pass
    return d.get("kanaele") or []
