# -*- coding: utf-8 -*-
"""Self-Update der gepackten SyncYouTube.exe — non-destruktiv, nur User-Space.

Übernimmt das erprobte SyncManga-Muster (JB-Dauerregel: jedes Release hat einen
Auto-Updater): Versions-Check und exe-Download laufen AUSSCHLIESSLICH gegen das
gepinnte GitHub-Repo, der Download wird gegen Größe + .sha256-Asset verifiziert,
und der Tausch ist der Windows-Trick ohne Adminrechte (laufende exe -> .old
umbenennen, neue an den Originalpfad, Neustart). Schlägt irgendetwas fehl,
bleibt die alte exe unangetastet lauffähig.

Signatur Pflicht (JB-Entscheid 7a Punkt 6, Gesamtprüfung S9, 25.09.2026):
getauscht wird nur eine exe mit gültiger Authenticode-Signatur (WinVerifyTrust
über ctypes, kein Kindprozess, keine neue Abhängigkeit), deren Signierer
(Inhaber und Aussteller des Zertifikats) dem der laufenden exe gleicht. Fehlt
die `.sha256` im Release, wird abgebrochen statt still weiterzumachen.

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
    ein manipulierter Eintrag in der API-Antwort kann nie woandershin führen.

    Die Prüfsumme wird EXAKT an `SyncYouTube.exe.sha256` erkannt. Die frühere
    Regel „endet auf .sha256 und enthält syncyoutube“ passte auf zwei Assets des
    echten Releases (auch auf `SyncYouTube-Quellstart.zip.sha256`) und behielt
    den LETZTEN Treffer. Gemessen am Release v.1.2.4: in der von GitHub
    gelieferten Reihenfolge gewann zufällig die richtige Datei, in umgekehrter
    Reihenfolge die des Quellstart-Pakets — dann verwirft `verify_exe` jede
    gesunde exe mit „Prüfsumme stimmt nicht“, und das Selbst-Update hätte still
    nie wieder funktioniert. Findet sich keine passende Prüfsumme, bricht
    `download_exe` ab (S9); eine FALSCHE Prüfsumme wäre ebenso ein Abbruch."""
    prefix = f"https://github.com/{repo}/releases/download/"
    exe = sha = None
    for a in assets or []:
        if not isinstance(a, dict) or not str(a.get("browser_download_url", "")).startswith(prefix):
            continue
        name = str(a.get("name", "")).lower()
        if name == EXE_ASSET:
            exe = a
        elif name == EXE_ASSET + ".sha256":
            sha = a
    return exe, sha


def parse_sha256(text):
    """Erste 64-stellige Hex-Folge aus einer .sha256-Datei -> lowercase ('' wenn keine)."""
    import re
    m = re.search(r"[0-9a-fA-F]{64}", str(text or ""))
    return m.group(0).lower() if m else ""


def check_release(current, fetch_json=None):
    """Neuestes Release auswerten -> {available, grund, version, exe_url, size, sha_url}.

    Fehler, kein Release oder kein exe-Asset -> available=False; die App läuft
    einfach normal weiter. /releases/latest liefert nie Prereleases.

    `grund` sagt, WARUM nichts zu tun ist: "offline" (GitHub nicht erreichbar),
    "kein-asset" (Release ohne passende exe), "aktuell" (nichts Neueres) oder
    "neu". Ohne diese Unterscheidung meldete die App jeden Ausgang als „Schon
    aktuell“ — solange das Update Opt-in war, sah das nur, wer selbst nachschaute;
    als Vorgabe wäre ein dauerhaft kaputter Update-Weg von einem gesunden nicht
    mehr zu unterscheiden."""
    fetch_json = fetch_json or fetch_release_json
    try:
        data = fetch_json() or {}
    except Exception:                                # noqa: BLE001 — offline ist kein Fehler
        return {"available": False, "grund": "offline", "version": ""}
    tag = str(data.get("tag_name") or "").strip()
    exe, sha = pick_assets(data.get("assets"))
    neuer = bool(exe) and is_newer(tag, current)
    return {"available": neuer,
            "grund": "neu" if neuer else ("kein-asset" if not exe else "aktuell"),
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

    Erst Größe und SHA-256 prüfen (verify_exe; ohne `.sha256` im Release kein
    Tausch), dann unter dem Zwischennamen schreiben, dort die Signatur prüfen
    (signatur_pruefen gegen die laufende exe) und erst dann atomar an den
    Zielnamen (os.replace) — eine ungeprüfte oder halbe Datei liegt nie unter
    dem Zielnamen. Eine verworfene Signatur bleibt als `….verworfen` liegen
    (nichts wird gelöscht). Wirft bei jedem Zweifel."""
    fetch = fetch or fetch_https
    if not info.get("sha_url"):
        raise ValueError("Update verworfen: Prüfsumme (SyncYouTube.exe.sha256) fehlt im Release")
    data = fetch(info["exe_url"])
    try:
        expected_sha = parse_sha256(fetch(info["sha_url"]).decode("utf-8", "replace"))
    except Exception as e:                           # noqa: BLE001 — ohne Prüfsumme kein Tausch (S9)
        raise ValueError(f"Update verworfen: Prüfsumme nicht ladbar ({e})") from e
    if not expected_sha:
        raise ValueError("Update verworfen: in der Prüfsummen-Datei steht keine Prüfsumme")
    ok, why = verify_exe(data, info.get("size") or 0, expected_sha)
    if not ok:
        raise ValueError(f"Update verworfen: {why}")
    target = os.path.join(dest_dir, "SyncYouTube_neu.exe")
    tmp = target + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    ok, why = signatur_pruefen(tmp, frozen_exe())
    if not ok:
        os.replace(tmp, target + ".verworfen")
        raise ValueError(f"Update verworfen: {why}")
    os.replace(tmp, target)
    return target


# ---- Authenticode (S9): WinVerifyTrust über ctypes ------------------------

_WTD_UI_NONE = 2
_WTD_REVOKE_NONE, _WTD_REVOKE_WHOLECHAIN = 0, 1
_WTD_CHOICE_FILE = 1
_WTD_STATEACTION_VERIFY, _WTD_STATEACTION_CLOSE = 1, 2
_WTD_REVOCATION_CHECK_NONE = 0x10
_WTD_REVOCATION_CHECK_CHAIN_EXCLUDE_ROOT = 0x80
_WTD_CACHE_ONLY_URL_RETRIEVAL = 0x1000
_WTD_DISABLE_MD2_MD4 = 0x2000
_CERT_NAME_RDN_TYPE, _CERT_NAME_ISSUER_FLAG, _CERT_X500_NAME_STR = 2, 1, 3


def _authenticode(pfad, offline):
    """WinVerifyTrust (WINTRUST_ACTION_GENERIC_VERIFY_V2) für eine Datei ->
    (Code, (Inhaber, Aussteller) | None). Code 0 = gültig signiert, die Kette
    endet an einer vertrauenswürdigen Wurzel. Die Namen stammen aus derselben
    Prüfung (Signierer 0, Zertifikat 0 der Kette), gehören also genau zu der
    Signatur, die als gültig galt; ohne gültige Signatur gibt es keine Namen.

    `offline`: keine Sperrlisten-Prüfung und nur der Zwischenspeicher (kein
    Netz). Sonst werden Sperrlisten der ganzen Kette außer der Wurzel geprüft."""
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    class WINTRUST_FILE_INFO(ctypes.Structure):
        _fields_ = [("cbStruct", wintypes.DWORD), ("pcwszFilePath", wintypes.LPCWSTR),
                    ("hFile", wintypes.HANDLE), ("pgKnownSubject", ctypes.c_void_p)]

    class WINTRUST_DATA(ctypes.Structure):
        _fields_ = [("cbStruct", wintypes.DWORD), ("pPolicyCallbackData", ctypes.c_void_p),
                    ("pSIPClientData", ctypes.c_void_p), ("dwUIChoice", wintypes.DWORD),
                    ("fdwRevocationChecks", wintypes.DWORD), ("dwUnionChoice", wintypes.DWORD),
                    ("pFile", ctypes.POINTER(WINTRUST_FILE_INFO)),
                    ("dwStateAction", wintypes.DWORD), ("hWVTStateData", wintypes.HANDLE),
                    ("pwszURLReference", wintypes.LPWSTR), ("dwProvFlags", wintypes.DWORD),
                    ("dwUIContext", wintypes.DWORD), ("pSignatureSettings", ctypes.c_void_p)]

    class CRYPT_PROVIDER_CERT(ctypes.Structure):    # nur der Anfang wird gelesen
        _fields_ = [("cbStruct", wintypes.DWORD), ("pCert", ctypes.c_void_p)]

    verify_v2 = GUID(0x00AAC56B, 0xCD44, 0x11D0,
                     (ctypes.c_ubyte * 8)(0x8C, 0xC2, 0x00, 0xC0, 0x4F, 0xC2, 0x95, 0xEE))
    wt = ctypes.WinDLL("wintrust")
    c32 = ctypes.WinDLL("crypt32")
    wt.WinVerifyTrust.argtypes = [wintypes.HWND, ctypes.POINTER(GUID), ctypes.c_void_p]
    wt.WinVerifyTrust.restype = wintypes.LONG
    wt.WTHelperProvDataFromStateData.argtypes = [wintypes.HANDLE]
    wt.WTHelperProvDataFromStateData.restype = ctypes.c_void_p
    wt.WTHelperGetProvSignerFromChain.argtypes = [ctypes.c_void_p, wintypes.DWORD,
                                                  wintypes.BOOL, wintypes.DWORD]
    wt.WTHelperGetProvSignerFromChain.restype = ctypes.c_void_p
    wt.WTHelperGetProvCertFromChain.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    wt.WTHelperGetProvCertFromChain.restype = ctypes.POINTER(CRYPT_PROVIDER_CERT)
    c32.CertGetNameStringW.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                       ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD]
    c32.CertGetNameStringW.restype = wintypes.DWORD

    datei = WINTRUST_FILE_INFO(ctypes.sizeof(WINTRUST_FILE_INFO), str(pfad), None, None)
    daten = WINTRUST_DATA()
    daten.cbStruct = ctypes.sizeof(WINTRUST_DATA)
    daten.dwUIChoice = _WTD_UI_NONE
    daten.dwUnionChoice = _WTD_CHOICE_FILE
    daten.pFile = ctypes.pointer(datei)
    daten.dwStateAction = _WTD_STATEACTION_VERIFY
    if offline:
        daten.fdwRevocationChecks = _WTD_REVOKE_NONE
        daten.dwProvFlags = (_WTD_REVOCATION_CHECK_NONE | _WTD_CACHE_ONLY_URL_RETRIEVAL
                             | _WTD_DISABLE_MD2_MD4)
    else:
        daten.fdwRevocationChecks = _WTD_REVOKE_WHOLECHAIN
        daten.dwProvFlags = _WTD_REVOCATION_CHECK_CHAIN_EXCLUDE_ROOT | _WTD_DISABLE_MD2_MD4
    code = wt.WinVerifyTrust(None, ctypes.byref(verify_v2), ctypes.byref(daten)) & 0xFFFFFFFF
    namen = None
    try:
        if code == 0:
            prov = wt.WTHelperProvDataFromStateData(daten.hWVTStateData)
            signierer = wt.WTHelperGetProvSignerFromChain(prov, 0, False, 0) if prov else None
            zert = wt.WTHelperGetProvCertFromChain(signierer, 0) if signierer else None
            if zert and zert.contents.pCert:
                def name(flags):
                    art = wintypes.DWORD(_CERT_X500_NAME_STR)
                    puffer = ctypes.create_unicode_buffer(2048)
                    c32.CertGetNameStringW(zert.contents.pCert, _CERT_NAME_RDN_TYPE, flags,
                                           ctypes.byref(art), puffer, 2048)
                    return puffer.value
                inhaber, aussteller = name(0), name(_CERT_NAME_ISSUER_FLAG)
                if inhaber and aussteller:
                    namen = (inhaber, aussteller)
    finally:
        daten.dwStateAction = _WTD_STATEACTION_CLOSE
        wt.WinVerifyTrust(None, ctypes.byref(verify_v2), ctypes.byref(daten))
    return code, namen


def authenticode_online(pfad):
    """Signatur samt Sperrlisten (Netz). Die conftest sperrt diese Fassung."""
    return _authenticode(pfad, offline=False)


def authenticode_offline(pfad):
    """Signatur ohne Sperrlisten, nur lokal."""
    return _authenticode(pfad, offline=True)


def signatur_pruefen(neu, laufend):
    """(ok, grund): trägt `neu` eine gültige Authenticode-Signatur desselben
    Signierers (Inhaber UND Aussteller) wie die laufende exe `laufend`?

    Die neue Datei wird samt Sperrlisten geprüft (ein widerrufenes Zertifikat
    gilt nicht). Die laufende dient nur als Maß für den Herausgeber und wird
    lokal gelesen: wurde ihr Zertifikat später widerrufen, soll gerade das
    Update mit dem neuen Zertifikat desselben Herausgebers noch ankommen.
    Jeder Zweifel ist ein Nein (fail-closed)."""
    if not laufend:
        return False, "keine laufende exe zum Vergleich der Signatur"
    try:
        code, wer = authenticode_online(neu)
    except Exception as e:                           # noqa: BLE001 — fail-closed
        return False, f"Signatur nicht prüfbar ({e})"
    if code != 0 or not wer:
        return False, f"Signatur fehlt oder ist ungültig (WinVerifyTrust 0x{code:08X})"
    try:
        code_alt, wer_alt = authenticode_offline(laufend)
    except Exception as e:                           # noqa: BLE001 — fail-closed
        return False, f"Signatur der laufenden exe nicht prüfbar ({e})"
    if code_alt != 0 or not wer_alt:
        return False, ("die laufende exe ist nicht gültig signiert "
                       f"(0x{code_alt:08X}), der Herausgeber ist nicht vergleichbar")
    if wer[0] != wer_alt[0]:
        return False, f"anderer Signierer: {wer[0]} statt {wer_alt[0]}"
    if wer[1] != wer_alt[1]:
        return False, f"anderer Aussteller: {wer[1]} statt {wer_alt[1]}"
    return True, ""


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
