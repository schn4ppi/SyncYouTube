# -*- coding: utf-8 -*-
"""📡 Live-TV (JB-Go 05.08., Recherche im IDEEN_RADAR): frei empfangbare,
LEGALE öffentlich-rechtliche Sender aus der gepflegten kodinerds-clean-Liste
(ARD/ZDF/Dritte/ARTE …) — m3u8-Streams, die der VLC-Motor direkt spielt.
Liste wird 24 h gecacht; tote Sender heilen sich beim nächsten Abruf.
Einbahn-Regel wie filme/geo: importiert NIE youtube_app."""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

import familie as fam

QUELLE = ("https://raw.githubusercontent.com/jnk22/kodinerds-iptv/master/"
          "iptv/clean/clean_tv.m3u")
CACHE_ALTER_S = 24 * 3600
ERLAUBTE_SCHEMEN = ("http", "https")
_pfade = {}


def einrichten(daten_dir):
    _pfade["cache"] = os.path.join(daten_dir, "live_tv.json")


def _erlaubt(url):
    """Nur http(s) mit Rechnername (Gesamtprüfung S18): die Liste kommt aus
    dem Netz, und VLC öffnet jede Adresse daraus. Datei-, Laufwerks- oder
    Freigabe-Adressen haben in einer Senderliste nichts zu suchen."""
    try:
        teile = urllib.parse.urlsplit(str(url or ""))
    except ValueError:
        return False
    return teile.scheme.lower() in ERLAUBTE_SCHEMEN and bool(teile.hostname)


def m3u_zerlegen(text):
    """#EXTINF-Zeilen → (Kanäle (Name, Logo, Gruppe) + folgende URL-Zeile,
    Zahl der verworfenen Einträge ohne http(s)-Adresse)."""
    out = []
    verworfen = 0
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
            if _erlaubt(zeile):
                info["url"] = zeile
                out.append(info)
            else:
                verworfen += 1
            info = None
    return out, verworfen


def m3u_parsen(text):
    """Nur die Kanäle aus m3u_zerlegen."""
    return m3u_zerlegen(text)[0]


def _nur_erlaubte(kanaele):
    """Auch ein Cache von vor dem Filter liefert nur http(s) aus."""
    return [k for k in (kanaele or []) if isinstance(k, dict) and _erlaubt(k.get("url"))]


def _cache_lesen():
    try:
        with open(_pfade["cache"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _fehler_merken(d, fehler):
    """Gescheiterten Abruf im Cache festhalten (Lehrbuch P5: Stille ist ein
    Ausfall). Alter Stand und alte Kanäle bleiben unverändert; `fehler_seit`
    hält den ERSTEN Fehlzeitpunkt, damit das Alter der Liste ablesbar ist."""
    d["letzter_fehler"] = f"{type(fehler).__name__}: {fehler}"
    if not d.get("fehler_seit"):
        d["fehler_seit"] = time.time()
    d.setdefault("stand", 0)
    d.setdefault("kanaele", [])
    try:
        fam.json_schreiben(_pfade["cache"], d)
    except OSError as e:                   # Cache nicht schreibbar ⇒ wenigstens melden
        print(f"live_tv: Fehler-Vermerk nicht schreibbar ({e})", file=sys.stderr)


def kanaele(frisch=False):
    """Senderliste aus dem Cache (24 h) oder frisch von der Quelle. Scheitert
    der Abruf, trägt der alte Cache weiter — der Fehler wird aber gemerkt
    (`letzter_fehler`/`fehler_seit`) und über status() sichtbar. Ausgeliefert
    werden nur Kanäle mit http(s)-Adresse; wie viele der Abruf verworfen
    hat, steht als `verworfen` im Cache und in status()."""
    d = _cache_lesen()
    if not frisch and time.time() - (d.get("stand") or 0) < CACHE_ALTER_S:
        return _nur_erlaubte(d.get("kanaele"))
    try:
        with urllib.request.urlopen(QUELLE, timeout=30) as r:
            liste, verworfen = m3u_zerlegen(r.read().decode("utf-8", "replace"))
        if not liste:
            raise ValueError("Senderliste leer (0 Kanäle geparst"
                             + (f", {verworfen} ohne http(s) verworfen)" if verworfen else ")"))
        fam.json_schreiben(_pfade["cache"], {"stand": time.time(),
                                             "kanaele": liste, "verworfen": verworfen})
        return liste
    except Exception as e:                 # noqa: BLE001 — alter Cache trägt, Fehler wird gemerkt
        _fehler_merken(d, e)
    return _nur_erlaubte(d.get("kanaele"))


def status():
    """Für /api/live und Wächter: Stand der Liste, Kanalzahl, letzter Fehler
    (leer = gesund), seit wann der Abruf scheitert (0 = gar nicht) und wie
    viele Einträge der letzte Abruf ohne http(s)-Adresse verworfen hat."""
    d = _cache_lesen()
    return {"stand": d.get("stand") or 0,
            "kanaele": len(d.get("kanaele") or []),
            "fehler": d.get("letzter_fehler") or "",
            "fehler_seit": d.get("fehler_seit") or 0,
            "verworfen": d.get("verworfen") or 0}
