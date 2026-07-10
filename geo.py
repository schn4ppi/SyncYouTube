# -*- coding: utf-8 -*-
"""Gestufte Geo-Umgehung für den YouTube-Downloader.

Idee (JB-Wunsch): ALLE Wege verketten und sich gegenseitig stützen. Bei einem
„nicht in deinem Land verfügbar"-Fehler probiert der Downloader die Methoden der
Reihe nach durch — billig/mühelos zuerst, aufwändig zuletzt — bis eine Zugang
gibt. Wer nichts einrichtet, bekommt die kostenlosen Stufen automatisch; wer
alles einrichtet (eigene Proxys, VPN, WireGuard), hat das volle Programm.

Reihenfolge:
  1. HEADER-TRICK  yt-dlp --geo-bypass-country  (gratis, sofort; hilft bei
                   YouTube selten, kostet aber nichts)
  2. EIGENE PROXYS aus den Einstellungen (--proxy; zuverlässig, weil vom Nutzer)
  3. GRATIS-PROXYS öffentlich, nach Land gefiltert (gratis, aber wackelig)
  4. VPN-ADAPTER   NordVPN / Windscribe / WireGuard-Config (verbindet ins Land)

Jede Methode liefert einen `Versuch`: yt-dlp-Zusatzoptionen (proxy /
geo_bypass_country) und optional setup/teardown (fürs VPN). Der eigentliche
Zugangs-Check + Download passiert in youtube_app.py.
"""
import json
import os
import re
import shutil
import subprocess
import urllib.request

import vpn as _nord

# Ländername -> ISO-2 (für --geo-bypass-country und Proxy-Auswahl). Deckt die
# in YouTube-Geo-Fehlern üblichen Länder ab; ergänzt vpn.LAENDER.
LAND_ISO = {
    "United Kingdom": "GB", "United States": "US", "United States of America": "US",
    "Ireland": "IE", "Canada": "CA", "Australia": "AU", "New Zealand": "NZ",
    "Germany": "DE", "Austria": "AT", "Switzerland": "CH", "Netherlands": "NL",
    "France": "FR", "Belgium": "BE", "Luxembourg": "LU", "Italy": "IT", "Spain": "ES",
    "Portugal": "PT", "Denmark": "DK", "Norway": "NO", "Sweden": "SE", "Finland": "FI",
    "Iceland": "IS", "Poland": "PL", "Czech Republic": "CZ", "Czechia": "CZ",
    "Slovakia": "SK", "Hungary": "HU", "Romania": "RO", "Bulgaria": "BG",
    "Greece": "GR", "Croatia": "HR", "Slovenia": "SI", "Estonia": "EE",
    "Latvia": "LV", "Lithuania": "LT", "Japan": "JP", "South Korea": "KR",
    "Korea, Republic of": "KR", "Brazil": "BR", "Mexico": "MX", "Argentina": "AR",
    "Chile": "CL", "Colombia": "CO", "India": "IN", "Singapore": "SG",
    "Hong Kong": "HK", "Taiwan": "TW", "Turkey": "TR", "Ukraine": "UA",
    "South Africa": "ZA", "Israel": "IL", "United Arab Emirates": "AE",
    "Guernsey": "GG", "Jersey": "JE", "Isle of Man": "IM", "Gibraltar": "GI",
}


def iso(land):
    return LAND_ISO.get(land) or _nord.LAENDER.get(land)


# ---------------------------------------------------------------- Geo-Fehler
# yt-dlp meldet Ländersperren als Klartext. Das Erkennen/Auswerten ist
# provider-unabhängig und gehört deshalb in dieses Modul (nicht zu NordVPN).

def ist_geo_fehler(fehlertext):
    """True, wenn der yt-dlp-Fehler eine Ländersperre ist."""
    return "available in your country" in (fehlertext or "").lower()


def laender_aus_fehler(fehlertext):
    """Erlaubte Länder aus einem Geo-Fehler ziehen. yt-dlp schreibt z. B.
    '… This video is available in A, B, C and D' -> ['A', 'B', 'C', 'D']."""
    m = re.search(r"video is available in ([^.]+)", fehlertext or "")
    if not m:
        return []
    return [n.strip() for n in re.split(r",\s*|\s+and\s+", m.group(1)) if n.strip()]


def nordvpn_verfuegbar():
    """Ist die NordVPN-App auf diesem PC installiert? (nur für die Status-Anzeige)"""
    return _nord.verfuegbar()


class Versuch:
    """Ein Umgehungs-Versuch. `opts` wird in die yt-dlp-Optionen gemischt.
    `setup()` (optional) baut z. B. eine VPN-Verbindung auf (True=ok);
    `teardown()` (optional) räumt danach auf."""
    def __init__(self, name, opts=None, setup=None, teardown=None):
        self.name = name
        self.opts = dict(opts or {})
        self.setup = setup
        self.teardown = teardown


# ---------------------------------------------------------------- Proxys

def freie_proxys(code, limit=4, timeout=8):
    """Öffentliche Gratis-Proxys im Zielland (best effort, geonode-API)."""
    if not code:
        return []
    api = ("https://proxylist.geonode.com/api/proxy-list?limit=25&page=1"
           f"&sort_by=lastChecked&sort_type=desc&country={code}"
           "&protocols=socks5%2Chttp%2Chttps")
    urls = []
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        for p in data.get("data", []):
            protos = p.get("protocols") or ["http"]
            proto = "socks5" if "socks5" in protos else protos[0]
            ip, port = p.get("ip"), p.get("port")
            if ip and port:
                urls.append(f"{proto}://{ip}:{port}")
            if len(urls) >= limit:
                break
    except Exception:                                # noqa: BLE001 — Netz/Format, best effort
        pass
    return urls


def manuelle_proxys(code, cfg):
    """Eigene Proxys aus den Einstellungen. Zeilen wie
    'GB=socks5://1.2.3.4:1080' (nur fürs Land) oder 'socks5://…' (für alle)."""
    out = []
    for eintrag in (cfg.get("geo_proxies") or []):
        eintrag = (eintrag or "").strip()
        if not eintrag or eintrag.startswith("#"):
            continue
        if "=" in eintrag and "://" in eintrag and eintrag.index("=") < eintrag.index("://"):
            land, _, url = eintrag.partition("=")
            land = land.strip().upper()
            if land in ("*", "", code):
                out.append(url.strip())
        else:
            out.append(eintrag)
    return out


# ---------------------------------------------------------------- VPN-Adapter

class _NordAdapter:
    name = "NordVPN"

    def verfuegbar(self):
        return _nord.verfuegbar()

    def verbinden_wenn_noetig(self, land):
        if _nord.aktiv():                            # JB ist selbst verbunden -> nichts anfassen
            self._selbst = False
            return True
        self._selbst = True
        return _nord.verbinden(land)

    def trennen_wenn_selbst(self):
        if getattr(self, "_selbst", False):
            _nord.trennen()


class _WindscribeAdapter:
    name = "Windscribe"
    _exe_kandidaten = (r"C:\Program Files\Windscribe\windscribe-cli.exe",
                       r"C:\Program Files (x86)\Windscribe\windscribe-cli.exe")

    def _exe(self):
        w = shutil.which("windscribe-cli")
        if w:
            return w
        for p in self._exe_kandidaten:
            if os.path.exists(p):
                return p
        return None

    def verfuegbar(self):
        return self._exe() is not None

    def verbinden_wenn_noetig(self, land):
        exe = self._exe()
        if not exe:
            return False
        code = iso(land) or land
        self._selbst = True
        try:
            subprocess.run([exe, "connect", code], timeout=60,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    def trennen_wenn_selbst(self):
        exe = self._exe()
        if exe and getattr(self, "_selbst", False):
            try:
                subprocess.run([exe, "disconnect"], timeout=30,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.SubprocessError):
                pass


class _WireguardAdapter:
    """Nutzt WireGuard-Config-Dateien (z. B. von ProtonVPN Free). Der Nutzer
    legt .conf-Dateien in einen Ordner, benannt nach Ländercode (GB.conf …).
    Braucht wireguard.exe und i. d. R. Admin-Rechte."""
    name = "WireGuard"
    _exe_kandidaten = (r"C:\Program Files\WireGuard\wireguard.exe",)

    def __init__(self, ordner):
        self.ordner = ordner
        self._tunnel = None

    def _exe(self):
        for p in self._exe_kandidaten:
            if os.path.exists(p):
                return p
        return shutil.which("wireguard")

    def verfuegbar(self):
        return bool(self._exe()) and os.path.isdir(self.ordner or "")

    def _conf_fuer(self, land):
        code = (iso(land) or "").lower()
        try:
            dateien = [f for f in os.listdir(self.ordner) if f.lower().endswith(".conf")]
        except OSError:
            return None
        for f in dateien:                            # exakter Ländercode zuerst
            if f.lower().startswith(code + "."):
                return os.path.join(self.ordner, f)
        for f in dateien:                            # oder Code irgendwo im Namen
            if code and code in f.lower():
                return os.path.join(self.ordner, f)
        return None

    def verbinden_wenn_noetig(self, land):
        exe = self._exe()
        conf = self._conf_fuer(land)
        if not (exe and conf):
            return False
        self._tunnel = os.path.splitext(os.path.basename(conf))[0]
        try:
            subprocess.run([exe, "/installtunnelservice", conf], timeout=40,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return True
        except (OSError, subprocess.SubprocessError):
            return False

    def trennen_wenn_selbst(self):
        exe = self._exe()
        if exe and self._tunnel:
            try:
                subprocess.run([exe, "/uninstalltunnelservice", self._tunnel], timeout=30,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except (OSError, subprocess.SubprocessError):
                pass


def vpn_adapter(cfg):
    """Ersten verfügbaren VPN-Adapter zurückgeben (oder None)."""
    for ad in (_NordAdapter(), _WindscribeAdapter(), _WireguardAdapter(cfg.get("geo_wireguard_ordner"))):
        try:
            if ad.verfuegbar():
                return ad
        except Exception:                            # noqa: BLE001
            continue
    return None


def wireguard_laender(ordner):
    """Ländercodes aus den .conf-Dateien im WireGuard-Ordner (Dateiname = Land)."""
    if not ordner or not os.path.isdir(ordner):
        return []
    out = []
    try:
        for f in os.listdir(ordner):
            if f.lower().endswith(".conf"):
                out.append(os.path.splitext(f)[0].upper())
    except OSError:
        pass
    return sorted(set(out))


def status(cfg):
    """Was ist auf diesem PC für die Geo-Umgehung verfügbar/eingerichtet?"""
    wg = _WireguardAdapter(cfg.get("geo_wireguard_ordner"))
    ad = vpn_adapter(cfg)
    return {
        "nordvpn": _NordAdapter().verfuegbar(),
        "windscribe": _WindscribeAdapter().verfuegbar(),
        "wireguard_exe": bool(wg._exe()),
        "wireguard_ordner": cfg.get("geo_wireguard_ordner") or "",
        "wireguard_laender": wireguard_laender(cfg.get("geo_wireguard_ordner")),
        "aktiver_adapter": ad.name if ad else "",
    }


# ---------------------------------------------------------------- Kette

def kandidaten(laender, cfg):
    """Alle Geo-Versuche in Reihenfolge (billig -> aufwändig) als Liste."""
    methoden = cfg.get("geo_methoden") or ["geobypass", "proxy_manuell", "proxy_frei", "vpn"]
    codes = [c for c in (iso(l) for l in laender) if c]
    liste = []

    if "geobypass" in methoden and codes:
        liste.append(Versuch(f"Header-Trick ({codes[0]})",
                             {"geo_bypass": True, "geo_bypass_country": codes[0]}))

    if "proxy_manuell" in methoden:
        for c in codes or ["*"]:
            for url in manuelle_proxys(c, cfg):
                liste.append(Versuch(f"eigener Proxy ({c})", {"proxy": url}))

    if "proxy_frei" in methoden and cfg.get("geo_gratis_proxy", True):
        for c in codes[:2]:
            for url in freie_proxys(c):
                liste.append(Versuch(f"Gratis-Proxy ({c})", {"proxy": url}))

    if "vpn" in methoden:
        ad = vpn_adapter(cfg)
        if ad:
            land = _nord.land_waehlen(laender) or (laender[0] if laender else None)
            if land:
                liste.append(Versuch(
                    f"{ad.name} → {land}",
                    setup=(lambda a=ad, l=land: a.verbinden_wenn_noetig(l)),
                    teardown=(lambda a=ad: a.trennen_wenn_selbst())))
    return liste
