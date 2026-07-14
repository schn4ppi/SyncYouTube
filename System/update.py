# -*- coding: utf-8 -*-
"""Self-Update der gepackten SyncYouTube.exe — non-destruktiv, nur User-Space.

Übernimmt das erprobte SyncManga-Muster (JB-Dauerregel: jedes Release hat einen
Auto-Updater): Versions-Check und exe-Download laufen AUSSCHLIESSLICH gegen das
gepinnte GitHub-Repo, der Download wird gegen Größe + .sha256-Asset verifiziert,
und der Tausch ist der Windows-Trick ohne Adminrechte (laufende exe -> .old
umbenennen, neue an den Originalpfad, Neustart). Schlägt irgendetwas fehl,
bleibt die alte exe unangetastet lauffähig.

Im Quellcode-Modus (nicht gefroren) ist Selbst-Update bewusst AUS — dort
aktualisiert git. Alle Netzzugriffe sind injizierbar (fetch/fetch_json),
damit die Entscheidungslogik in Tests ohne Netz läuft.
"""
import json
import os

# JBs öffentliches Repo der App. NUR von hier wird aktualisiert.
REPO = "schn4ppi/SyncYouTube"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
EXE_ASSET = "syncyoutube.exe"        # erwarteter Asset-Name (case-insensitiv verglichen)
MIN_EXE_SIZE = 50 * 2 ** 20          # exe bündelt ffmpeg/deno (~190 MB); kleiner = kaputter Download


def frozen_exe():
    """Pfad der laufenden .exe — oder None im Quellbaum (dann gibt es nichts zu tauschen)."""
    import sys
    return sys.executable if getattr(sys, "frozen", False) else None


def parse_version(v):
    """'v1.2.3' / '1.2' / 'v.1.2.3' -> (1,2,3) / (1,2) / (1,2,3).

    Führende v/V UND Punkte fallen weg — JB taggt real `v.1.0.1`; das darf nie
    als (0,1,0,1) gelesen werden, sonst hält sich die App fälschlich für aktuell."""
    parts = []
    for p in str(v or "").strip().lstrip("vV.").split("."):
        digits = "".join(ch for ch in p if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(remote, local):
    """True, wenn `remote` neuer ist als `local` (längenunabhängig)."""
    a, b = parse_version(remote), parse_version(local)
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def pick_assets(assets, repo=REPO):
    """(exe_asset, sha_asset) aus einer Release-Asset-Liste — rein, testbar.

    Akzeptiert NUR Assets, deren Download-URL auf das eigene Repo zeigt —
    ein manipulierter Eintrag in der API-Antwort kann nie woandershin führen."""
    prefix = f"https://github.com/{repo}/releases/download/"
    exe = sha = None
    for a in assets or []:
        if not isinstance(a, dict) or not str(a.get("browser_download_url", "")).startswith(prefix):
            continue
        name = str(a.get("name", "")).lower()
        if name == EXE_ASSET:
            exe = a
        elif name.endswith(".sha256") and "syncyoutube" in name:
            sha = a
    return exe, sha


def parse_sha256(text):
    """Erste 64-stellige Hex-Folge aus einer .sha256-Datei -> lowercase ('' wenn keine)."""
    import re
    m = re.search(r"[0-9a-fA-F]{64}", str(text or ""))
    return m.group(0).lower() if m else ""


def check_release(current, fetch_json=None):
    """Neuestes Release auswerten -> {available, version, exe_url, size, sha_url}.

    Fehler, kein Release oder kein exe-Asset -> available=False; die App läuft
    einfach normal weiter. /releases/latest liefert nie Prereleases."""
    fetch_json = fetch_json or fetch_release_json
    try:
        data = fetch_json() or {}
    except Exception:                                # noqa: BLE001 — offline ist kein Fehler
        return {"available": False, "version": ""}
    tag = str(data.get("tag_name") or "").strip()
    exe, sha = pick_assets(data.get("assets"))
    return {"available": bool(exe) and is_newer(tag, current),
            "version": tag.lstrip("vV."),
            "exe_url": (exe or {}).get("browser_download_url", ""),
            "size": int((exe or {}).get("size") or 0),
            "sha_url": (sha or {}).get("browser_download_url", "")}


def verify_exe(data, expected_size=0, expected_sha=""):
    """Download prüfen -> (ok, grund). Erst wenn ALLE verfügbaren Prüfungen
    bestehen (Mindestgröße, exakte Release-Größe, SHA256), darf getauscht werden."""
    import hashlib
    n = len(data or b"")
    if n < MIN_EXE_SIZE:
        return False, f"nur {n} Bytes (kaputter/abgebrochener Download)"
    if expected_size and n != int(expected_size):
        return False, f"Größe {n} != erwartet {expected_size}"
    if expected_sha and hashlib.sha256(data).hexdigest() != expected_sha.lower():
        return False, "SHA256-Prüfsumme stimmt nicht"
    return True, ""


def fetch_release_json(url=None, timeout=20):
    """GET /releases/latest (echtes Netz). GitHub verlangt einen User-Agent."""
    import urllib.request
    req = urllib.request.Request(url or RELEASE_API,
                                 headers={"User-Agent": "SyncYouTube-Updater",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_https(url, timeout=600):
    """Bytes einer HTTPS-URL — alles andere wird abgelehnt, nie umgeschrieben."""
    import urllib.request
    if not str(url).startswith("https://"):
        raise ValueError(f"nur HTTPS erlaubt: {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": "SyncYouTube-Updater"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def download_exe(info, dest_dir, fetch=None):
    """Release-exe verifiziert nach `SyncYouTube_neu.exe` laden -> Pfad.

    Erst ALLES prüfen (verify_exe), dann atomar schreiben (tmp + os.replace) —
    ein halber Download liegt nie unter dem Zielnamen. Wirft bei jedem Zweifel."""
    fetch = fetch or fetch_https
    data = fetch(info["exe_url"])
    expected_sha = ""
    if info.get("sha_url"):
        try:
            expected_sha = parse_sha256(fetch(info["sha_url"]).decode("utf-8", "replace"))
        except Exception:                            # noqa: BLE001 — dann greifen die Größen-Prüfungen
            expected_sha = ""
    ok, why = verify_exe(data, info.get("size") or 0, expected_sha)
    if not ok:
        raise ValueError(f"Update verworfen: {why}")
    target = os.path.join(dest_dir, "SyncYouTube_neu.exe")
    tmp = target + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, target)
    return target


def apply_exe_update(new_exe, running_exe, restart=True):
    """Selbst-Ersetzen ohne Adminrechte: laufende exe -> `.old` (das erlaubt
    Windows), neue exe an den Originalpfad, Neustart. Schlägt der Tausch fehl,
    rollt die alte zurück — es gibt keinen Moment ohne lauffähige App."""
    old = running_exe + ".old"
    try:
        if os.path.exists(old):
            os.remove(old)                           # Rest vom letzten Update
    except OSError:
        old = running_exe + f".old-{os.getpid()}"    # noch gesperrt -> eindeutiger Name
    os.rename(running_exe, old)
    try:
        os.replace(new_exe, running_exe)
    except OSError:
        os.rename(old, running_exe)                  # Rollback
        raise
    if restart:
        import subprocess
        subprocess.Popen([running_exe], close_fds=True)
        os._exit(0)                                  # nichts darf den Neustart festhalten


def cleanup_old_exe(running_exe=None):
    """`.old`(-…) früherer Updates löschen — best-effort beim Start."""
    exe = running_exe or frozen_exe()
    if not exe:
        return
    import glob
    for p in glob.glob(exe + ".old*"):
        try:
            os.remove(p)
        except OSError:
            pass
