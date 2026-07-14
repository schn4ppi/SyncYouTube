# -*- coding: utf-8 -*-
"""
YouTube-Downloader — eigenständiges Suite-Modul (JB-Wunsch 07/2026).

Was es tut:
  - Warteschlange ohne Limit (warteschlange.json, überlebt Neustarts)
  - Qualität wählbar (Beste / 2160p / 1440p / 1080p / 720p / nur Audio)
  - Automatischer Neuversuch bei Abbruch (Backoff), Downloads werden
    FORTGESETZT wo sie aufgehört haben (yt-dlp .part-Dateien)
  - Premium-Konto: Cookies werden aus dem Browser gelesen (Standard: Firefox),
    damit lädt yt-dlp als angemeldeter Premium-Nutzer
  - Kleine Web-Oberfläche auf http://127.0.0.1:8776 (nur lokal, wie Suite-Settings)

Suite-Regeln: stdlib-HTTP-Server (kein Framework), nur 127.0.0.1, nichts
Destruktives (Entfernen aus der Liste löscht NIE Dateien), atomare JSON-Writes,
alles UTF-8. Einzige Fremdbibliothek: yt-dlp (Core-venv). ffmpeg liegt in bin/.
"""
import glob
import hashlib
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import geo
import update

__version__ = "1.1.1"

# Als .exe (PyInstaller, sys.frozen): alle Daten/bin NEBEN der exe, nicht im
# Temp-Entpackordner — sonst verschwänden Warteschlange/Config bei jedem Start.
# JB-Ordnerstandard: Quellcode + Technik liegen in System\, der Downloads-Ordner
# (extern) eine Ebene darüber im Programmordner. Bei der exe ist beides die
# exe-Ebene (exe liegt oben im Programmordner).
if getattr(sys, "frozen", False):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
    PROGRAMM_DIR = SCRIPT_DIR
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))        # System\
    PROGRAMM_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
CONFIG_PFAD = os.path.join(SCRIPT_DIR, "config.json")
QUEUE_PFAD = os.path.join(SCRIPT_DIR, "warteschlange.json")
GELADEN_PFAD = os.path.join(SCRIPT_DIR, "geladen_log.json")  # „Datenbank" fertiger Downloads
PLAYLIST_PFAD = os.path.join(SCRIPT_DIR, "playlists.json")
STATUS_PFAD = os.path.join(SCRIPT_DIR, "yt_status.json")   # fürs Dashboard (read-only Konsument)
BIN_DIR = os.path.join(SCRIPT_DIR, "bin")
# In der Release-exe sind ffmpeg/ffprobe/deno MIT eingepackt (PyInstaller-Bundle,
# entpackt nach sys._MEIPASS/bin). Ein eigener bin\-Ordner NEBEN der exe hat
# Vorrang (so kann man ffmpeg/deno selbst aktualisieren), sonst gilt das Bundle.
if getattr(sys, "frozen", False) and not os.path.isdir(BIN_DIR):
    _bundle_bin = os.path.join(getattr(sys, "_MEIPASS", SCRIPT_DIR), "bin")
    if os.path.isdir(_bundle_bin):
        BIN_DIR = _bundle_bin
# bin\ (ffmpeg + deno) auf den PATH: yt-dlp braucht seit 2026 eine JS-Runtime
# (Deno) für YouTubes n-Challenge — ohne sie fehlen Formate oder es kommt
# "No video formats found" (mit Cookies).
os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ.get("PATH", "")

STANDARD_CONFIG = {
    "port": 8776,
    "ziel_ordner": "",              # leer = YouTube/Downloads
    "cookies_browser": "firefox",   # firefox | chrome | edge | keine
    "standard_qualitaet": "beste",
    "parallel": 1,                  # gleichzeitige Downloads (1-3)
    "max_wiederholungen": 10,       # danach Status "fehler" (Knopf setzt zurück)
    "geo_vpn": True,                # Geo-Sperren automatisch umgehen (Master-Schalter)
    "geo_gratis_proxy": True,       # öffentliche Gratis-Proxys mitprobieren
    "geo_proxies": [],              # eigene Proxys, Zeilen wie "GB=socks5://ip:port"
    "geo_wireguard_ordner": "",     # Ordner mit WireGuard-.conf (z.B. ProtonVPN Free)
    "unterordner": True,            # nach Kategorie einsortieren (MP3 / 4K+ / Video)
    "metadaten": True,              # Titel/Autor/Datum in die Datei schreiben
    "fehler_ausblenden_min": 5,     # Fehler-Einträge nach so vielen Minuten aus der Queue nehmen (0 = nie)
    "sponsorblock": "",             # "" = aus | "sponsor" = nur Werbung | "alle" = Werbung+Intro/Outro/… rausschneiden
    "fernsteuerung": False,         # Handy-Fernsteuerung im Heim-WLAN erlauben (Standard AUS = nur 127.0.0.1)
    "fernsteuerung_code": "",       # Zugangscode fürs Handy (wird beim ersten Aktivieren erzeugt)
    "untertitel": False,            # Untertitel beim Download mitziehen (Standard aus; der Player holt sie fuers Karaoke bei Bedarf)
    "auto_update": False,           # Selbst-Update der exe (Opt-in; prüft täglich das GitHub-Release)
}


def zugriff_erlaubt(client_ip, aktiv, code_soll, code_ist):
    """Wer darf auf die App zugreifen? Der eigene PC (localhost) IMMER. Aus dem
    Heim-WLAN NUR, wenn die Fernsteuerung an ist UND der Zugangscode stimmt.
    (Sicherheits-Kern der Handy-Fernsteuerung — bewusst als reine Funktion testbar.)"""
    if client_ip in ("127.0.0.1", "::1", "localhost"):
        return True
    if not aktiv:
        return False
    return bool(code_soll) and code_ist == code_soll

# SponsorBlock: welche Segmente beim Download rausgeschnitten werden (Community-Daten
# von sponsor.ajay.app, via yt-dlp). "" = aus, damit nichts ungefragt verändert wird.
SPONSORBLOCK_ALLE = ["sponsor", "selfpromo", "intro", "outro", "preview",
                     "interaction", "music_offtopic"]


def sponsorblock_kategorien(modus):
    if modus == "sponsor":
        return ["sponsor"]
    if modus == "alle":
        return list(SPONSORBLOCK_ALLE)
    return []

# Unterordner je Kategorie (JB-Wunsch: mp3 / 4k+ / Rest getrennt)
UNTERORDNER = {"MP3": "MP3", "4K+": "4K+", "Video": "Video"}

# Backoff zwischen automatischen Neuversuchen (Sekunden), letzter Wert wiederholt sich
BACKOFF = [10, 30, 60, 120, 300]

# Fehler, die kein Neuversuch heilt (Geo-Sperre, gelöscht, privat) -> sofort "fehler"
DAUERHAFT = ("available in your country", "private video", "video unavailable",
             "no longer available", "has been removed", "account associated",
             "sign in to confirm your age")

QUALITAETEN = {
    "beste":  "bestvideo*+bestaudio/best",
    "2160p":  "bestvideo*[height<=2160]+bestaudio/best[height<=2160]/best",
    "1440p":  "bestvideo*[height<=1440]+bestaudio/best[height<=1440]/best",
    "1080p":  "bestvideo*[height<=1080]+bestaudio/best[height<=1080]/best",
    "720p":   "bestvideo*[height<=720]+bestaudio/best[height<=720]/best",
    "audio":  "bestaudio/best",
}


class AbbruchError(Exception):
    """Vom Nutzer angefordert (Pause-Knopf) — kein echter Fehler."""


# ---------------------------------------------------------------- Persistenz

_io_lock = threading.RLock()


def _json_laden(pfad, fallback):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        # kaputte Datei nie verlieren (Suite-Regel: nicht-destruktiv)
        if os.path.exists(pfad):
            try:
                os.replace(pfad, pfad + ".defekt")
            except OSError:
                pass
        return fallback


def _json_speichern(pfad, daten):
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=1)
    os.replace(tmp, pfad)


def config_laden():
    cfg = dict(STANDARD_CONFIG)
    cfg.update({k: v for k, v in _json_laden(CONFIG_PFAD, {}).items() if k in STANDARD_CONFIG})
    return cfg


# ---------------------------------------------------------------- Warteschlange

class Warteschlange:
    """Alle Einträge + Locks. Ein Eintrag = EIN Video (Playlists werden beim
    Hinzufügen in Einzelvideos aufgelöst)."""

    def __init__(self):
        self.lock = threading.RLock()
        self.items = []
        self.abbrueche = set()      # ids, deren laufender Download stoppen soll
        daten = _json_laden(QUEUE_PFAD, {"items": []})
        for it in daten.get("items", []):
            # Nach Neustart: was lief, wird wieder eingereiht -> Resume via .part
            if it.get("status") == "laeuft":
                it["status"] = "wartend"
            it.setdefault("naechster_versuch", 0)
            self.items.append(it)

    # ---- Persistenz (Status-Änderungen sofort, Fortschritt macht der Ticker)
    def speichern(self):
        with self.lock, _io_lock:
            _json_speichern(QUEUE_PFAD, {"items": self.items})
            zaehl = {}
            for it in self.items:
                zaehl[it["status"]] = zaehl.get(it["status"], 0) + 1
            fertige = [it for it in self.items if it["status"] == "fertig"]
            _json_speichern(STATUS_PFAD, {
                "stand": time.time(),
                "zaehler": zaehl,
                "letzte_datei": (fertige[-1].get("datei") or fertige[-1].get("titel")) if fertige else "",
            })

    def finde(self, item_id):
        for it in self.items:
            if it["id"] == item_id:
                return it
        return None

    def neu(self, url, titel, qualitaet, dauer=None):
        it = {
            "id": uuid.uuid4().hex[:10],
            "url": url,
            "titel": titel or url,
            "qualitaet": qualitaet if qualitaet in QUALITAETEN else "beste",
            "status": "wartend",     # wartend|laeuft|pausiert|fertig|fehler|prueft
            "prozent": 0.0,
            "geschw": 0,
            "eta": None,
            "geladen": 0,
            "gesamt": 0,
            "phase": "",
            "datei": "",
            "fehler": "",
            "versuche": 0,
            "naechster_versuch": 0,
            "dauer": dauer,
            "kategorie": "",
            "uploader": "",
            "upload_date": "",
            "vcodec": "",
            "acodec": "",
            "abr": 0,
            "asr": 0,
            "hoehe": 0,
            "hinzugefuegt": time.time(),
            "fertig_ts": None,
        }
        with self.lock:
            self.items.append(it)
        return it

    def naechster(self):
        """Nächsten wartenden Eintrag atomar auf 'laeuft' setzen."""
        jetzt = time.time()
        with self.lock:
            for it in self.items:
                if it["status"] == "wartend" and it["naechster_versuch"] <= jetzt:
                    it["status"] = "laeuft"
                    it["fehler"] = ""
                    self.abbrueche.discard(it["id"])
                    return it
        return None


Q = Warteschlange()
CFG = config_laden()


def ziel_ordner():
    pfad = CFG.get("ziel_ordner") or os.path.join(PROGRAMM_DIR, "Downloads")
    try:
        os.makedirs(pfad, exist_ok=True)
    except OSError:
        pfad = os.path.join(PROGRAMM_DIR, "Downloads")
        os.makedirs(pfad, exist_ok=True)
    return pfad


def _ffmpeg_pfad():
    exe = os.path.join(BIN_DIR, "ffmpeg.exe")
    return BIN_DIR if os.path.exists(exe) else None


def _kategorie(qualitaet, hoehe):
    """Zielkategorie eines Downloads: MP3 (Audio) / 4K+ (>=2160p) / Video (Rest)."""
    if qualitaet == "audio":
        return "MP3"
    if hoehe and hoehe >= 2160:
        return "4K+"
    return "Video"


def _ordner_fuer(kategorie):
    if not CFG.get("unterordner", True):
        return ziel_ordner()
    pfad = os.path.join(ziel_ordner(), UNTERORDNER.get(kategorie, "Video"))
    try:
        os.makedirs(pfad, exist_ok=True)
        return pfad
    except OSError:
        return ziel_ordner()


def _hoehe_ffprobe(pfad):
    """Echte Videohöhe der fertigen Datei (v:0 = echtes Video, nicht das Cover)."""
    if not pfad or not os.path.exists(pfad) or not _ffmpeg_pfad():
        return None
    try:
        out = subprocess.run(
            [os.path.join(BIN_DIR, "ffprobe.exe"), "-v", "error",
             "-select_streams", "v:0", "-show_entries", "stream=height",
             "-of", "csv=p=0", pfad],
            capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW)
        return int((out.stdout.strip().splitlines() or ["0"])[0])
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _technik(pfad):
    """Codec-/Qualitäts-Infos der fertigen Datei per ffprobe:
    {vcodec, height, acodec, abr(kbps), asr(Hz)}. Das eingebettete Cover (mjpeg
    mit attached_pic) wird als Videospur ignoriert."""
    if not pfad or not os.path.isfile(pfad) or not _ffmpeg_pfad():
        return {}
    try:
        out = subprocess.run(
            [os.path.join(BIN_DIR, "ffprobe.exe"), "-v", "error", "-print_format", "json",
             "-show_entries",
             "stream=codec_type,codec_name,height,bit_rate,sample_rate:stream_disposition=attached_pic"
             ":format=bit_rate", pfad],
            capture_output=True, text=True, timeout=25,
            creationflags=subprocess.CREATE_NO_WINDOW)
        data = json.loads(out.stdout or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}
    res = {"vcodec": "", "height": 0, "acodec": "", "abr": 0, "asr": 0}
    for s in data.get("streams", []):
        cover = (s.get("disposition") or {}).get("attached_pic")
        if s.get("codec_type") == "video" and not cover and not res["vcodec"]:
            res["vcodec"] = s.get("codec_name", "")
            res["height"] = int(s.get("height") or 0)
        elif s.get("codec_type") == "audio" and not res["acodec"]:
            res["acodec"] = s.get("codec_name", "")
            try:
                res["abr"] = round(int(s.get("bit_rate") or 0) / 1000)
            except (TypeError, ValueError):
                res["abr"] = 0
            try:
                res["asr"] = int(s.get("sample_rate") or 0)
            except (TypeError, ValueError):
                res["asr"] = 0
    if not res["abr"]:                               # mp3: Bitrate steht evtl. nur im Format
        try:
            res["abr"] = round(int(data.get("format", {}).get("bit_rate") or 0) / 1000)
        except (TypeError, ValueError):
            pass
    return res


def _sidecars_mit(alt, neu):
    """Untertitel-Dateien (stem.<lang>.vtt) mit der Mediendatei mitnehmen."""
    alt_stem = os.path.splitext(alt)[0]
    neu_stem = os.path.splitext(neu)[0]
    for f in glob.glob(glob.escape(alt_stem) + ".*.vtt"):
        try:
            os.replace(f, neu_stem + f[len(alt_stem):])
        except OSError:
            pass


def _in_unterordner(pfad, kategorie):
    """Fertige Datei in ihren Kategorie-Unterordner verschieben (gleiches
    Laufwerk -> atomar). Gibt den neuen Pfad zurück; bei Fehler den alten."""
    if not pfad or not os.path.exists(pfad) or not CFG.get("unterordner", True):
        return pfad
    neu = os.path.join(_ordner_fuer(kategorie), os.path.basename(pfad))
    if os.path.abspath(neu) == os.path.abspath(pfad):
        return pfad
    try:
        os.replace(pfad, neu)         # überschreibt eine gleiche Datei (selbes Video, neuester Lauf)
        _sidecars_mit(pfad, neu)      # .vtt-Untertitel wandern mit
        return neu
    except OSError:
        return pfad


def ist_einzelvideo(url):
    """watch?v=…&list=… heißt: JB will DIESES Video, nicht die ganze Liste.
    Nur reine Playlist-Links (/playlist?list=…) werden komplett übernommen."""
    try:
        p = urlparse(url)
        qs = parse_qs(p.query)
        return bool(qs.get("v")) or "/playlist" not in p.path
    except ValueError:
        return True


# ---------------------------------------------------------------- yt-dlp

def _ydl_basis_opts(mit_cookies=True):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "windowsfilenames": True,
        "retries": 5,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        # Ohne Timeout blockiert eine eingeschlafene Verbindung den Worker EWIG
        # (JB-Vorfall 13.07.: ein Download hing 68h bei 0%, dahinter stand die
        # ganze Warteschlange). Mit Timeout wird daraus ein normaler Fehler,
        # der in den Backoff geht — und der Worker nimmt den nächsten Eintrag.
        "socket_timeout": 30,
    }
    ff = _ffmpeg_pfad()
    if ff:
        opts["ffmpeg_location"] = ff
    browser = CFG.get("cookies_browser", "firefox")
    if mit_cookies and browser and browser != "keine":
        opts["cookiesfrombrowser"] = (browser,)
    return opts


def _ist_cookie_fehler(exc):
    t = str(exc).lower()
    return "cookie" in t or "could not copy" in t or "decrypt" in t or "browser" in t


def _ist_untertitel_fehler(exc):
    """Nur der Untertitel-Abruf ist gescheitert (z.B. drosselt YouTube die
    Untertitel-Endpoints gern mit HTTP 429) — das Video selbst wäre ladbar.
    Dann: gleicher Lauf nochmal OHNE Untertitel statt stundenlanger Backoff-
    Schleife bei 0% (JB-Vorfall 11.07.); die .vtt lädt der Player später nach."""
    t = str(exc).lower()
    return "subtitle" in t and ("429" in t or "too many requests" in t
                                or "unable to download" in t)


def aufloesen(url, qualitaet, ganze_liste=False):
    """URL prüfen und in Queue-Einträge verwandeln (Playlist/Mix -> Einzelvideos).
    ganze_liste=True erzwingt die komplette Liste/den Mix auch bei einem
    watch?v=…&list=…-Link (JB-/Kumpel-Wunsch: „YouTube-Mixe runterladen").
    Läuft im Hintergrund-Thread, damit die Oberfläche nie blockiert."""
    import yt_dlp
    platzhalter = Q.neu(url, None, qualitaet)
    platzhalter["status"] = "prueft"
    Q.speichern()
    opts = _ydl_basis_opts()
    # Mixe (list=RD…/RDMM…) sind endlos — auf 50 Titel deckeln, damit nicht
    # tausende Einträge entstehen; echte Playlists laufen unbegrenzt.
    mix = bool(re.search(r"[?&]list=(RD|UL|RDMM|RDCLAK)", url))
    if ganze_liste and mix:
        opts["playlistend"] = 50
    opts.update({"extract_flat": "in_playlist", "skip_download": True,
                 "noplaylist": (not ganze_liste) and ist_einzelvideo(url)})
    try:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:                       # noqa: BLE001 — Cookie-Probleme heilen
            if not _ist_cookie_fehler(e):
                raise
            opts.pop("cookiesfrombrowser", None)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
    except Exception as e:                           # noqa: BLE001 — Nutzer sieht den Text
        voll = str(e)
        platzhalter["fehler"] = _fehltext(e)
        if geo.ist_geo_fehler(voll) and CFG.get("geo_vpn"):
            platzhalter["geo_laender"] = geo.laender_aus_fehler(voll)
            platzhalter["status"] = "wartend"        # Worker übernimmt die Geo-Kette
        else:
            platzhalter["status"] = "fehler"
        Q.speichern()
        return

    eintraege = info.get("entries") if info.get("_type") == "playlist" else None
    with Q.lock:
        if platzhalter not in Q.items:               # Nutzer hat ihn derweil entfernt
            return
        if eintraege is not None:
            Q.items.remove(platzhalter)
            for e in eintraege:
                if not e:
                    continue
                v_url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
                if _schon_da(v_url, qualitaet):
                    continue
                neu = Q.neu(v_url, e.get("title"), qualitaet, e.get("duration"))
                fund = schon_geladen(v_url, qualitaet)
                if fund:
                    _als_uebersprungen(neu, fund)
        else:
            platzhalter["titel"] = info.get("title") or url
            platzhalter["dauer"] = info.get("duration")
            platzhalter["url"] = info.get("webpage_url") or url
            if _schon_da(platzhalter["url"], qualitaet, ausser=platzhalter["id"]):
                Q.items.remove(platzhalter)
            else:
                fund = schon_geladen(platzhalter["url"], qualitaet)
                if fund:
                    _als_uebersprungen(platzhalter, fund)
                else:
                    platzhalter["status"] = "wartend"
    Q.speichern()


def _video_id(url):
    m = re.search(r"[?&]v=([\w-]{6,})", url) or re.search(r"youtu\.be/([\w-]{6,})", url)
    return m.group(1) if m else url


# ---- „Schon geladen"-Datenbank (JB-Regel: identischer Name + gleiche Größe
# -> überspringen). Überlebt „Liste leeren" und App-Neustarts.

_geladen = _json_laden(GELADEN_PFAD, {})    # "videoid|qualitaet" -> {name, groesse, pfad, ts}


def _geladen_key(url, qualitaet):
    return f"{_video_id(url)}|{qualitaet}"


def _kapitel_aus_info(info):
    """YouTube-Kapitel aus yt-dlp-Info in eine schlanke Liste [{start, titel}]."""
    out = []
    for c in ((info or {}).get("chapters") or []):
        if c and c.get("start_time") is not None:
            out.append({"start": round(float(c["start_time"]), 1), "titel": (c.get("title") or "")[:120]})
    return out[:300]


def geladen_merken(item):
    datei = item.get("datei")
    if not datei:
        return
    try:
        groesse = os.path.getsize(datei)
    except OSError:
        return
    key = _geladen_key(item["url"], item["qualitaet"])
    alt = _geladen.get(key, {})
    _geladen[key] = {
        "name": os.path.basename(datei), "groesse": groesse, "pfad": datei,
        "kategorie": item.get("kategorie", ""), "titel": item.get("titel", ""),
        "uploader": item.get("uploader", ""), "dauer": item.get("dauer"),
        "upload_date": item.get("upload_date", ""), "url": item.get("url", ""),
        "qualitaet": item.get("qualitaet", ""),
        "vcodec": item.get("vcodec", ""), "acodec": item.get("acodec", ""),
        "abr": item.get("abr", 0), "asr": item.get("asr", 0), "hoehe": item.get("hoehe", 0),
        "kapitel": item.get("kapitel") or alt.get("kapitel") or [],
        "archiviert": alt.get("archiviert", False), "ts": time.time()}
    with _io_lock:
        _json_speichern(GELADEN_PFAD, _geladen)


# ---- Bibliothek: Ansicht über alle je geladenen Titel (aus geladen_log.json).

def _titel_aus_name(name):
    t = re.sub(r"\.[^.]+$", "", name or "")          # Endung weg
    t = re.sub(r"\s*\[[\w-]{6,}\]\s*$", "", t)        # [videoid] weg
    return t.strip() or (name or "")


def _kat_aus_name(name):
    n = (name or "").lower()
    return "MP3" if n.endswith((".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav")) else "Video"


def _plausible_id(vid):
    return bool(re.fullmatch(r"[\w-]{6,20}", vid or ""))


def _datei_index():
    """videoid -> Pfad aus EINEM Ordner-Durchlauf (inkl. Unterordner). So braucht
    die Bibliothek nicht pro Eintrag zu suchen (erkennt auch verschobene Dateien)."""
    idx = {}
    for root, _, files in os.walk(ziel_ordner()):
        for f in files:
            # NUR Mediendateien: die .vtt-Untertitel/.jpg-Cover NEBEN dem Video
            # dürfen den Index nie vergiften — sonst spielt /media eine
            # Untertitel-Datei aus und das Bild bleibt schwarz (JB-Fund 14.07.).
            if not f.lower().endswith(AUDIO_EXT + VIDEO_EXT):
                continue
            m = re.search(r"\[([\w-]{6,})\]", f)
            if m:
                idx.setdefault(m.group(1), []).append(os.path.join(root, f))
    return idx


def _datei_aus(liste, qualitaet=""):
    """Aus mehreren Dateien derselben Video-ID die zur QUALITÄT passende wählen:
    audio-Key -> Audio-Datei zuerst, alles andere -> Video-Datei zuerst. Sonst
    bekam ein |beste-Eintrag die MP3-Fassung -> Ton ja, Bild schwarz (JB 14.07.)."""
    if not liste:
        return None
    audio = [p for p in liste if p.lower().endswith(AUDIO_EXT)]
    video = [p for p in liste if p.lower().endswith(VIDEO_EXT)]
    if qualitaet == "audio":
        return (audio or video or liste)[0]
    return (video or audio or liste)[0]


def bibliothek_liste():
    idx = _datei_index()
    out = []
    for key, e in list(_geladen.items()):
        vid, _, qual = key.partition("|")
        gespeichert = e.get("pfad")
        pfad = gespeichert if (gespeichert and os.path.isfile(gespeichert)) else _datei_aus(idx.get(vid), qual)
        art = ""
        if pfad:
            art = "audio" if pfad.lower().endswith(AUDIO_EXT) else "video"
        out.append({
            "id": key, "videoid": vid, "dateiart": art,
            "qualitaet": e.get("qualitaet") or qual or "",
            "titel": e.get("titel") or _titel_aus_name(e.get("name", "")),
            "uploader": e.get("uploader", ""), "dauer": e.get("dauer"),
            "upload_date": e.get("upload_date", ""),
            "kategorie": e.get("kategorie") or _kat_aus_name(e.get("name", "")),
            "vcodec": e.get("vcodec", ""), "acodec": e.get("acodec", ""),
            "abr": e.get("abr", 0), "asr": e.get("asr", 0), "hoehe": e.get("hoehe", 0),
            "groesse": e.get("groesse", 0), "name": e.get("name", ""),
            "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg" if _plausible_id(vid) else "",
            "url": e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if _plausible_id(vid) else ""),
            "vorhanden": bool(pfad), "archiviert": bool(e.get("archiviert")),
            "plays": e.get("plays", 0), "blacklist": bool(e.get("blacklist")),
            "last_play": e.get("last_play", 0), "ts": e.get("ts", 0),
            "kapitel": e.get("kapitel") or [],
            "kuenstler": e.get("kuenstler", ""), "album": e.get("album", ""),
            "track": e.get("track", ""), "jahr": e.get("jahr", ""),
        })
    out.sort(key=lambda x: x["ts"] or 0, reverse=True)
    return out


# ---- Datei zu einem Bibliotheks-Schlüssel finden (für Media/Player/Extern)

def _pfad_zu_key(key):
    e = _geladen.get(key)
    if not e:
        return None
    gespeichert = e.get("pfad")
    if gespeichert and os.path.isfile(gespeichert):
        return gespeichert
    vid, _, qual = key.partition("|")
    return _datei_aus(_datei_index().get(vid), qual)


# ---- Media-Streaming mit Range (fürs Abspielen/Suchen im HTML5-Player)

_MIME = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".opus": "audio/ogg", ".ogg": "audio/ogg",
         ".flac": "audio/flac", ".wav": "audio/wav", ".aac": "audio/aac",
         ".mp4": "video/mp4", ".webm": "video/webm", ".mkv": "video/x-matroska", ".mov": "video/quicktime"}


def _stream_datei(handler, pfad):
    """Datei ausliefern, Range-Anfragen (Seek/Abspielen) inklusive."""
    groesse = os.path.getsize(pfad)
    ctype = _MIME.get(os.path.splitext(pfad)[1].lower()) \
        or mimetypes.guess_type(pfad)[0] or "application/octet-stream"
    rng = handler.headers.get("Range")
    start, ende, teil = 0, groesse - 1, False
    if rng and rng.startswith("bytes="):
        teil = True
        s, _, e2 = rng[6:].partition("-")
        try:
            start = int(s) if s else 0
            ende = int(e2) if e2 else groesse - 1
        except ValueError:
            start, ende = 0, groesse - 1
        ende = min(ende, groesse - 1)
        if start > ende or start < 0:
            start, ende = 0, groesse - 1
    laenge = ende - start + 1
    handler.send_response(206 if teil else 200)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Accept-Ranges", "bytes")
    handler.send_header("Content-Length", str(laenge))
    if teil:
        handler.send_header("Content-Range", f"bytes {start}-{ende}/{groesse}")
    _cors(handler)
    handler.end_headers()
    if handler.command == "HEAD":
        return
    with open(pfad, "rb") as f:
        f.seek(start)
        rest = laenge
        while rest > 0:
            chunk = f.read(min(65536, rest))
            if not chunk:
                break
            try:
                handler.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
            rest -= len(chunk)


_VLC_KANDIDATEN = (r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                   r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe")


def extern_abspielen(pfad):
    """In VLC öffnen, falls installiert, sonst im Windows-Standardplayer."""
    for v in _VLC_KANDIDATEN:
        if os.path.exists(v):
            subprocess.Popen([v, pfad])
            return
    try:
        os.startfile(pfad)                           # noqa: einzig sinnvoll unter Windows
    except (OSError, AttributeError):
        subprocess.Popen(["explorer", "/select,", pfad])


# ---- Ausschnitt/Clip: vorne + hinten wegschneiden -> EINE neue Datei (ffmpeg) ----

def _zeit_sekunden(s):
    """„1:23" / „1:02:03" / „83" -> Sekunden. None bei leer/ungültig."""
    s = (str(s or "")).strip()
    if not s:
        return None
    try:
        sek = 0.0
        for teil in s.split(":"):
            sek = sek * 60 + float(teil)
        return sek
    except ValueError:
        return None


def clip_erstellen(daten):
    """Aus einer vorhandenen Datei den Bereich [start, ende] herausschneiden
    (leer = Anfang/Ende) und als NEUEN Bibliothekseintrag speichern. Das Original
    bleibt unangetastet (nicht-destruktiv)."""
    key = daten.get("id") or ""
    e = _geladen.get(key)
    if not e:
        return {"fehler": "Titel unbekannt"}
    quelle = _pfad_zu_key(key)
    if not (quelle and os.path.isfile(quelle)):
        return {"fehler": "Datei nicht gefunden (verschoben/gelöscht?)"}
    ff = os.path.join(BIN_DIR, "ffmpeg.exe")
    if not os.path.exists(ff):
        return {"fehler": "ffmpeg fehlt"}
    start = _zeit_sekunden(daten.get("start")) or 0.0
    ende = _zeit_sekunden(daten.get("ende"))
    if ende is not None and ende <= start:
        return {"fehler": "„Bis“ muss nach „Von“ liegen."}

    basis, ext = os.path.splitext(os.path.basename(quelle))
    ordner = os.path.dirname(quelle)
    ziel = os.path.join(ordner, f"{basis} (Ausschnitt){ext}")
    n = 2
    while os.path.exists(ziel):
        ziel = os.path.join(ordner, f"{basis} (Ausschnitt {n}){ext}")
        n += 1

    cmd = [ff, "-y", "-ss", str(start), "-i", quelle]
    if ende is not None:
        cmd += ["-t", str(ende - start)]             # Dauer (nach input-seek relativ)
    cmd += ["-c", "copy", "-avoid_negative_ts", "make_zero", ziel]
    try:
        subprocess.run(cmd, capture_output=True, timeout=600,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as ex:
        return {"fehler": f"ffmpeg-Fehler: {ex}"}
    if not os.path.isfile(ziel):
        return {"fehler": "Ausschnitt fehlgeschlagen (Quelle geschützt?)"}

    vid = key.split("|")[0]
    neu_key = f"{vid}|clip{uuid.uuid4().hex[:6]}"      # eigener Eintrag, Quell-Thumbnail bleibt
    with _io_lock:
        eintrag = {k: e.get(k) for k in ("kategorie", "uploader", "upload_date", "url",
                                         "qualitaet", "vcodec", "acodec", "abr", "asr", "hoehe")}
        eintrag.update({"name": os.path.basename(ziel), "groesse": os.path.getsize(ziel),
                        "pfad": ziel, "titel": (e.get("titel") or basis) + " (Ausschnitt)",
                        "dauer": (ende - start) if ende is not None else None,
                        "ts": time.time(), "archiviert": False})
        _geladen[neu_key] = eintrag
        _json_speichern(GELADEN_PFAD, _geladen)
    return {"ok": True, "name": os.path.basename(ziel)}


# ---- Auto-Tagging (MusicBrainz): Künstler/Titel/Album sauber nachschlagen ----
# Gratis-API ohne Key; Regel: max. 1 Anfrage/Sekunde + aussagekräftiger User-Agent.

MB_API = "https://musicbrainz.org/ws/2/recording"
MB_UA = "JB-YTDL-Suite/1.0 (https://github.com/schn4ppi)"

# Müll-Klammern aus YouTube-Titeln: [Official Video], (Lyrics), [4K Upgrade] …
_TITEL_MUELL = re.compile(
    r"(?i)[\(\[](official|video|audio|lyric|lyrics|hd|hq|4k|8k|remaster|visualizer"
    r"|mv|m/v|full album|live|explicit|clean)[^\)\]]*[\)\]]")


def _tag_kandidat(e):
    """Aus YouTube-Titel + Kanal einen (kuenstler, titel)-Kandidaten raten.
    'Green Day - Boulevard … [Official Video]' -> ('Green Day', 'Boulevard …')."""
    t = _TITEL_MUELL.sub(" ", e.get("titel") or "")
    t = re.sub(r"\s+", " ", t).strip(" -–—|")
    ku = ""
    for sep in (" - ", " – ", " — ", ": "):
        if sep in t:
            ku, t = t.split(sep, 1)
            break
    if not ku:                                        # kein 'Künstler - Titel' -> Kanalname säubern
        ku = re.sub(r"(?i)\s*-\s*topic$|vevo$", "", e.get("uploader") or "").strip()
    return ku.strip(), t.strip(" -–—|")


def _mb_get(url, timeout=10):
    """GET mit MusicBrainz-Pflicht-User-Agent; bei Drossel (503) EIN Retry nach Pause."""
    import urllib.request
    for versuch in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": MB_UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:                            # noqa: BLE001 — meist Rate-Limit
            if versuch == 2:
                raise
            time.sleep(2.5)


def _mb_kuenstler(daten):
    return "".join((a.get("name") or "") + (a.get("joinphrase") or "")
                   for a in daten.get("artist-credit", []) if isinstance(a, dict)).strip()


def _artist_passt(rec, kuenstler):
    """Wächter gegen Coverbands: 'ABBA-Esque' darf nicht als 'ABBA' durchgehen."""
    if not kuenstler:
        return True
    import difflib
    a = re.sub(r"[^a-z0-9]", "", _mb_kuenstler(rec).lower())
    k = re.sub(r"[^a-z0-9]", "", kuenstler.lower())
    return a == k or difflib.SequenceMatcher(None, a, k).ratio() >= 0.85


def _mb_suche(kuenstler, titel, timeout=10):
    """Künstler/Titel/Album via MusicBrainz. Zwei Stufen (die Recording-Suche allein
    ist voller gleichnamiger Live-Bootlegs — live ausgetestet 09.07.2026):
    1) Recording-SUCHE, gefiltert auf offizielle Studio-Alben, exakter Titel bevorzugt,
       frühestes Erst-Release-Datum gewinnt.
    2) Recording-LOOKUP (volle Release-Liste) -> frühestes offizielles Studio-Album;
       Jahr aus dem Release-Group-Erstdatum (sonst Reissue-Jahre).
    Findet die Filter-Suche nichts, korrigiert eine offene Suche nur Künstler/Titel."""
    import urllib.parse
    if not titel:
        return None
    basis = f'recording:"{titel}"' + (f' AND artist:"{kuenstler}"' if kuenstler else "")
    def suche(q, limit):
        try:
            return _mb_get(MB_API + "?" + urllib.parse.urlencode(
                {"query": q, "fmt": "json", "limit": str(limit)}), timeout)
        except Exception:                            # noqa: BLE001 — Netz: kein Fund
            return {}
    data = suche(basis + " AND status:official AND primarytype:album NOT secondarytype:*", 15)
    recs = [r for r in data.get("recordings", []) if int(r.get("score", 0)) >= 85
            and not r.get("video") and _artist_passt(r, kuenstler)]
    exakt = [r for r in recs if (r.get("title") or "").lower() == titel.lower()]
    pool = exakt or recs
    pool.sort(key=lambda r: r.get("first-release-date") or "9999")
    if not pool:                                     # kein Studio-Album: nur Künstler/Titel säubern
        time.sleep(1.1)
        data = suche(basis, 5)
        recs = [r for r in data.get("recordings", []) if int(r.get("score", 0)) >= 85
                and _artist_passt(r, kuenstler)]
        if not recs:
            return None
        rec = next((r for r in recs if (r.get("title") or "").lower() == titel.lower()), recs[0])
        return {"kuenstler": _mb_kuenstler(rec), "titel": rec.get("title", ""), "album": "", "jahr": ""}
    time.sleep(1.1)                                  # MusicBrainz-Takt vor dem Lookup
    try:
        det = _mb_get(f"https://musicbrainz.org/ws/2/recording/{pool[0]['id']}"
                      "?inc=releases+release-groups+artist-credits&fmt=json", timeout)
    except Exception:                                # noqa: BLE001
        return {"kuenstler": _mb_kuenstler(pool[0]), "titel": pool[0].get("title", ""), "album": "", "jahr": ""}
    alben = [rel for rel in det.get("releases", [])
             if (rel.get("release-group") or {}).get("primary-type") == "Album"
             and not (rel.get("release-group") or {}).get("secondary-types")
             and rel.get("status") == "Official"
             # undatierte „Alben" sind fast immer Box-Sets/Datenmüll -> nur Datiertes zählt
             and (rel.get("date") or (rel.get("release-group") or {}).get("first-release-date"))]
    alben.sort(key=lambda r: r.get("date") or "9999")
    album, jahr = "", ""
    if alben:
        album = alben[0].get("title") or ""
        rg = alben[0].get("release-group") or {}
        jahr = ((rg.get("first-release-date") or alben[0].get("date") or ""))[:4]
    # Bei un-exaktem Titel-Treffer (z.B. „… (instrumental)") den EIGENEN gesäuberten
    # Titel behalten — das Album stimmt trotzdem.
    mb_titel = det.get("title", "") or pool[0].get("title", "")
    return {"kuenstler": _mb_kuenstler(det) or _mb_kuenstler(pool[0]),
            "titel": mb_titel if exakt else titel,
            "album": album, "jahr": jahr}


def _ist_musik(e):
    n = (e.get("name") or "").lower()
    return e.get("kategorie") == "MP3" or n.endswith((".mp3", ".m4a", ".opus", ".ogg", ".flac"))


def _tags_in_datei(key, e):
    """Künstler/Titel/Album per ffmpeg IN die MP3 schreiben (Streams kopiert,
    Cover bleibt; bei jedem Fehler bleibt die Originaldatei unangetastet)."""
    pfad = _pfad_zu_key(key)
    ff = os.path.join(BIN_DIR, "ffmpeg.exe")
    if not (pfad and os.path.isfile(pfad) and os.path.exists(ff)):
        return
    if not pfad.lower().endswith(".mp3"):            # andere Container erstmal nur in der DB
        return
    tmp = pfad + ".tagtmp.mp3"
    cmd = [ff, "-y", "-i", pfad, "-map", "0", "-c", "copy", "-id3v2_version", "3",
           "-metadata", f"artist={e.get('kuenstler', '')}",
           "-metadata", f"title={e.get('track') or e.get('titel', '')}",
           "-metadata", f"album={e.get('album', '')}"]
    if e.get("jahr"):
        cmd += ["-metadata", f"date={e['jahr']}"]
    cmd += [tmp]
    try:
        subprocess.run(cmd, capture_output=True, timeout=120,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        if os.path.isfile(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, pfad)
            with _io_lock:
                e["groesse"] = os.path.getsize(pfad)  # Größe in der DB nachziehen (Dubletten-Check!)
                _json_speichern(GELADEN_PFAD, _geladen)
    except (OSError, subprocess.SubprocessError):
        pass
    finally:
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except OSError:
            pass


_autotag = {"laeuft": False, "gesamt": 0, "erledigt": 0, "getaggt": 0}


def autotag_lauf(keys=None):
    """Auto-Tagging im Hintergrund: Kandidat raten -> MusicBrainz -> DB-Felder
    (kuenstler/album/track/jahr) + Tags in die MP3. Ohne keys: alle Musik ohne Album."""
    if _autotag["laeuft"]:
        return
    _autotag.update({"laeuft": True, "gesamt": 0, "erledigt": 0, "getaggt": 0})
    try:
        alle = list(keys) if keys else [k for k, e in list(_geladen.items())
                                        if _ist_musik(e) and not e.get("album")]
        _autotag["gesamt"] = len(alle)
        for k in alle:
            e = _geladen.get(k)
            _autotag["erledigt"] += 1
            if not e:
                continue
            ku, ti = _tag_kandidat(e)
            fund = _mb_suche(ku, ti)
            time.sleep(1.5)                          # MusicBrainz-Regel: max 1 Anfrage/Sekunde (+Puffer)
            if not fund:
                continue
            with _io_lock:
                e["kuenstler"] = fund["kuenstler"] or ku
                e["album"] = fund["album"]
                e["track"] = fund["titel"] or ti
                if fund.get("jahr"):
                    e["jahr"] = fund["jahr"]
                _json_speichern(GELADEN_PFAD, _geladen)
            _autotag["getaggt"] += 1
            _tags_in_datei(k, e)
    finally:
        _autotag["laeuft"] = False


# ---- Untertitel: .vtt neben der Mediendatei finden bzw. nachladen ----

def _vtt_sprache(pfad):
    m = re.search(r"\.([A-Za-z0-9-]+)\.vtt$", pfad)
    return m.group(1) if m else ""


def untertitel_liste(key):
    """Alle .vtt-Dateien zu einem Bibliotheks-Key als [(pfad, sprache)], sortiert:
    ORIGINAL-Sprache (…-orig, fürs Karaoke) vor Deutsch vor Englisch vor Rest."""
    pfad = _pfad_zu_key(key)
    if not pfad:
        return []
    stem = os.path.splitext(pfad)[0]
    dateien = glob.glob(glob.escape(stem) + ".*.vtt")

    def rang(f):
        s = _vtt_sprache(f).lower()
        return 0 if s.endswith("-orig") else (1 if s.startswith("de") else (2 if s.startswith("en") else 3))
    dateien.sort(key=rang)
    return [(f, _vtt_sprache(f)) for f in dateien]


def untertitel_datei(key, sprache=None):
    """Beste (oder gewünschte) .vtt zu einem Key -> (pfad, sprache) oder (None, '')."""
    liste = untertitel_liste(key)
    if not liste:
        return None, ""
    if sprache:
        for f, s in liste:
            if s == sprache:
                return f, s
    return liste[0]


def _romaji(vtt_text):
    """Japanische Untertitel-Zeilen in Romaji (Hepburn) umschreiben — Zeitstempel
    und VTT-Kopf bleiben unangetastet. Braucht pykakasi (Core-venv); ohne die
    Bibliothek kommt der Text unverändert zurück."""
    try:
        import pykakasi
    except ImportError:
        return vtt_text
    kks = getattr(_romaji, "_kks", None)
    if kks is None:
        kks = _romaji._kks = pykakasi.kakasi()
    out = []
    for zeile in vtt_text.split("\n"):
        z = zeile.strip()
        if "-->" in zeile or not z or z.isdigit() or z.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")):
            out.append(zeile)
        else:
            try:
                out.append(" ".join(t["hepburn"] for t in kks.convert(zeile)).strip() or zeile)
            except Exception:                        # noqa: BLE001 — im Zweifel Original
                out.append(zeile)
    return "\n".join(out)


def untertitel_nachladen(key):
    """Untertitel für einen vorhandenen Titel nachträglich von YouTube holen
    (nur die .vtt, kein Video-Download). Läuft im Hintergrund-Thread."""
    import yt_dlp
    e = _geladen.get(key)
    pfad = _pfad_zu_key(key)
    if not (e and pfad):
        return
    vid = key.split("|")[0]
    url = e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if _plausible_id(vid) else "")
    if not url:
        return
    stem = os.path.splitext(pfad)[0]
    opts = _ydl_basis_opts()
    opts.update({"skip_download": True, "noplaylist": True,
                 "writesubtitles": True, "writeautomaticsub": True,
                 "subtitleslangs": ["de", "en", ".*-orig"], "subtitlesformat": "vtt/best",
                 "outtmpl": {"default": stem + ".%(ext)s"}})   # .vtt landet neben der Datei
    for _ in (1, 2):
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                y.extract_info(url, download=True)             # skip_download: nur Untertitel
            return
        except Exception:                            # noqa: BLE001 — Cookie/Netz, 2. Versuch ohne Cookies
            opts.pop("cookiesfrombrowser", None)


# ---- Handy-Fernsteuerung: LAN-Adresse + Befehls-Kanal (Handy -> PC-Player) ----

def _lan_ip():
    """Eigene IP im Heim-WLAN (für den Handy-Link)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


# Letzter Fernsteuer-Befehl vom Handy; der PC-Player pollt ihn über /api/status.
_remote = {"n": 0, "cmd": "", "key": "", "wert": None, "ts": 0}


def remote_befehl(daten):
    cmd = daten.get("cmd")
    if cmd in ("play", "pause", "next", "prev", "playkey"):
        _remote["n"] += 1
        _remote["cmd"] = cmd
        _remote["key"] = daten.get("key", "")
        _remote["wert"] = daten.get("wert")
        _remote["ts"] = time.time()
    return {"ok": True, "n": _remote["n"]}


def fernsteuerung_info():
    """Status-Häppchen fürs UI: an/aus, Code, Handy-Link (nur wenn aktiv)."""
    aktiv = bool(CFG.get("fernsteuerung"))
    port = int(CFG.get("port", 8776))
    return {
        "aktiv": aktiv,
        "code": CFG.get("fernsteuerung_code") or "",
        "url": (f"http://{_lan_ip()}:{port}/m" if aktiv else ""),
    }


def _in_papierkorb(pfad):
    """Datei in den Windows-Papierkorb verschieben (wiederherstellbar!) statt hart
    zu löschen. Gibt True bei Erfolg zurück."""
    try:
        import ctypes
        from ctypes import wintypes

        class _OP(ctypes.Structure):
            _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
                        ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
                        ("fFlags", ctypes.c_uint16), ("fAnyAborted", wintypes.BOOL),
                        ("hNameMappings", wintypes.LPVOID), ("lpszTitle", wintypes.LPCWSTR)]
        FO_DELETE, FOF_ALLOWUNDO, FOF_NOCONF, FOF_SILENT = 3, 0x40, 0x10, 0x4
        op = _OP()
        op.wFunc = FO_DELETE
        op.pFrom = pfad + "\0\0"                      # doppelt-null-terminiert
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONF | FOF_SILENT
        return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0
    except Exception:                                # noqa: BLE001 — Fallback im Aufrufer
        return False


def _datei_loeschen(key):
    """Datei zu einem Key in den Papierkorb (Fallback: hart löschen) + aus allen
    Playlists nehmen. Der Aufrufer entfernt den DB-Eintrag selbst."""
    pfad = _pfad_zu_key(key)
    if pfad and os.path.isfile(pfad):
        if not _in_papierkorb(pfad):
            try:
                os.remove(pfad)
            except OSError:
                pass
    for pl in _playlists:
        pl["items"] = [x for x in pl.get("items", []) if x != key]


# ---- Playlists (playlists.json): [{id, name, items:[key,...], ts}]

_playlists = _json_laden(PLAYLIST_PFAD, [])
if not isinstance(_playlists, list):
    _playlists = []


def _playlists_speichern():
    with _io_lock:
        _json_speichern(PLAYLIST_PFAD, _playlists)


def playlist_aktion(daten):
    art = daten.get("art")
    with _io_lock:
        if art == "create":
            name = (str(daten.get("name") or "")).strip()[:80] or "Playlist"
            _playlists.append({"id": uuid.uuid4().hex[:8], "name": name, "items": [], "ts": time.time()})
        else:
            pl = next((p for p in _playlists if p.get("id") == daten.get("id")), None)
            if not pl:
                return
            if art == "delete":
                _playlists[:] = [p for p in _playlists if p.get("id") != pl["id"]]
            elif art == "rename":
                pl["name"] = (str(daten.get("name") or pl["name"])).strip()[:80] or pl["name"]
            elif art == "add":
                k = daten.get("key")
                if k and k in _geladen and k not in pl["items"]:
                    pl["items"].append(k)
            elif art == "remove":
                pl["items"] = [x for x in pl["items"] if x != daten.get("key")]
            elif art == "reorder" and isinstance(daten.get("items"), list):
                pl["items"] = [k for k in daten["items"] if k in pl["items"]]
            elif art == "sync_config":
                if isinstance(daten.get("sync_ordner"), str):
                    pl["sync_ordner"] = daten["sync_ordner"].strip()
                if daten.get("sync_modus") in ("kopieren", "spiegeln"):
                    pl["sync_modus"] = daten["sync_modus"]
        _json_speichern(PLAYLIST_PFAD, _playlists)


def playlist_sync(pl):
    """Playlist-Dateien in den Zielordner (Gerät/USB/Handy) kopieren.
    Modus 'spiegeln': aus der Playlist entfernte Titel werden im Ziel GELÖSCHT —
    aber NUR Dateien, die wir selbst dorthin kopiert haben (sync_manifest),
    nie fremde Dateien im Ordner (nicht-destruktiv gegenüber JBs Daten)."""
    if not pl:
        return {"fehler": "Playlist unbekannt"}
    ordner = (pl.get("sync_ordner") or "").strip()
    if not ordner:
        return {"fehler": "kein Zielordner eingerichtet"}
    try:
        os.makedirs(ordner, exist_ok=True)
    except OSError as e:
        return {"fehler": f"Zielordner nicht erreichbar: {e}"}
    idx = _datei_index()
    gewollt = {}                                      # basename -> Quellpfad
    for key in pl.get("items", []):
        e = _geladen.get(key)
        if not e:
            continue
        src = (e.get("pfad") if e.get("pfad") and os.path.isfile(e.get("pfad"))
               else _datei_aus(idx.get(key.split("|")[0]), key.partition("|")[2]))
        if src and os.path.isfile(src):
            gewollt[os.path.basename(src)] = src
    kopiert = uebersprungen = geloescht = fehler = 0
    for name, src in gewollt.items():
        ziel = os.path.join(ordner, name)
        try:
            if os.path.exists(ziel) and os.path.getsize(ziel) == os.path.getsize(src):
                uebersprungen += 1
            else:
                shutil.copy2(src, ziel)
                kopiert += 1
        except OSError:
            fehler += 1
    if pl.get("sync_modus") == "spiegeln":
        for name in list(pl.get("sync_manifest") or []):
            if name not in gewollt:                   # aus Playlist entfernt -> im Ziel weg
                ziel = os.path.join(ordner, name)
                try:
                    if os.path.isfile(ziel):
                        os.remove(ziel)
                        geloescht += 1
                except OSError:
                    fehler += 1
    with _io_lock:
        pl["sync_manifest"] = sorted(gewollt.keys())
        pl["sync_ts"] = time.time()
        _json_speichern(PLAYLIST_PFAD, _playlists)
    return {"ok": True, "kopiert": kopiert, "uebersprungen": uebersprungen,
            "geloescht": geloescht, "fehler": fehler, "im_ziel": len(gewollt)}


def playlist_m3u(pl):
    """Eine Playlist als .m3u-Text (mit #EXTINF-Titeln, absolute Pfade)."""
    idx = _datei_index()
    zeilen = ["#EXTM3U"]
    for key in pl.get("items", []):
        e = _geladen.get(key)
        if not e:
            continue
        src = (e.get("pfad") if e.get("pfad") and os.path.isfile(e.get("pfad"))
               else _datei_aus(idx.get(key.split("|")[0]), key.partition("|")[2]))
        if not src:
            continue
        zeilen.append(f"#EXTINF:{int(e.get('dauer') or 0)},{e.get('titel') or os.path.basename(src)}")
        zeilen.append(src)
    return "\n".join(zeilen) + "\n"


def playlist_import_m3u(name, text):
    """Aus einer .m3u eine Playlist bauen: Dateinamen gegen die Bibliothek matchen."""
    nach_name = {}
    for k, e in _geladen.items():
        if e.get("name"):
            nach_name.setdefault(e["name"], k)
    keys = []
    for ln in (text or "").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        k = nach_name.get(os.path.basename(ln.replace("\\", "/")))
        if k and k not in keys:
            keys.append(k)
    with _io_lock:
        pl = {"id": uuid.uuid4().hex[:8], "name": (str(name or "")).strip()[:80] or "Import",
              "items": keys, "ts": time.time()}
        _playlists.append(pl)
        _json_speichern(PLAYLIST_PFAD, _playlists)
    return {"ok": True, "id": pl["id"], "gefunden": len(keys)}


# ---- Abos (abos.json): Kanäle/Playlists automatisch auf neue Videos prüfen.
#      Beim Abonnieren werden die AKTUELL vorhandenen Video-IDs als „bekannt"
#      gemerkt und NICHT geladen (Baseline) — geholt wird nur, was danach neu
#      dazukommt (kein versehentliches Herunterladen des ganzen Archivs).

ABO_PFAD = os.path.join(SCRIPT_DIR, "abos.json")
_abos = _json_laden(ABO_PFAD, [])
if not isinstance(_abos, list):
    _abos = []


def _abo_ids(url, limit=60):
    """Video-IDs eines Kanals / einer Playlist (flach, ohne Download) + Titel."""
    import yt_dlp
    opts = _ydl_basis_opts()
    opts.update({"extract_flat": "in_playlist", "skip_download": True,
                 "playlistend": limit, "noplaylist": False})
    ids, titel = [], ""
    for _ in (1, 2):
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(url, download=False)
            titel = info.get("title") or info.get("uploader") or ""
            for e in (info.get("entries") or []):
                if e and e.get("id"):
                    ids.append(e["id"])
            break
        except Exception:                            # noqa: BLE001 — Cookie/Netz, 2. Versuch ohne Cookies
            opts.pop("cookiesfrombrowser", None)
    return ids, titel


def abo_aktion(daten):
    art = daten.get("art")
    if art == "create":
        url = (str(daten.get("url") or "")).strip()
        if not url.lower().startswith(("http://", "https://")):
            return {"fehler": "Bitte einen Kanal- oder Playlist-Link angeben."}
        qual = daten.get("qualitaet") if daten.get("qualitaet") in QUALITAETEN else CFG["standard_qualitaet"]
        ids, titel = _abo_ids(url)                    # Baseline merken, NICHT laden
        abo = {"id": uuid.uuid4().hex[:8], "url": url, "name": titel or url,
               "qualitaet": qual, "bekannt": ids, "ts": time.time(), "neu": 0}
        with _io_lock:
            _abos.append(abo)
            _json_speichern(ABO_PFAD, _abos)
        return {"ok": True, "id": abo["id"], "name": abo["name"], "basis": len(ids)}
    if art == "delete":
        with _io_lock:
            _abos[:] = [a for a in _abos if a.get("id") != daten.get("id")]
            _json_speichern(ABO_PFAD, _abos)
        return {"ok": True}
    if art == "pruefen":
        return {"ok": True, "neu": abos_pruefen()}
    return {"fehler": "unbekannt"}


def abos_pruefen():
    """Alle Abos auf neue Videos prüfen und Neues in die Warteschlange legen.
    Gibt die Zahl neu eingereihter Videos zurück."""
    gesamt = 0
    for abo in list(_abos):
        ids, titel = _abo_ids(abo.get("url", ""))
        if not ids:
            continue
        bekannt = set(abo.get("bekannt") or [])
        neu = [i for i in ids if i not in bekannt]
        for vid in neu:
            url = f"https://www.youtube.com/watch?v={vid}"
            if _schon_da(url, abo["qualitaet"]) or schon_geladen(url, abo["qualitaet"]):
                continue
            threading.Thread(target=aufloesen, args=(url, abo["qualitaet"]), daemon=True).start()
            gesamt += 1
        with _io_lock:
            abo["bekannt"] = ids
            if titel and (not abo.get("name") or abo["name"] == abo["url"]):
                abo["name"] = titel
            abo["neu"] = abo.get("neu", 0) + len(neu)
            abo["geprueft"] = time.time()
            _json_speichern(ABO_PFAD, _abos)
    return gesamt


def _abos_hintergrund():
    """Kurz nach Start + danach alle 6 h prüfen (Daemon-Thread)."""
    time.sleep(30)
    while True:
        try:
            abos_pruefen()
        except Exception:                            # noqa: BLE001
            pass
        time.sleep(6 * 3600)


def _enrich_eintrag(key, e):
    """Fehlende Metadaten (Titel/Kanal/Dauer/Datum) für einen Alt-Eintrag per
    yt-dlp nachladen (nur Metadaten, kein Download)."""
    import yt_dlp
    vid = key.split("|")[0]
    if not _plausible_id(vid):
        return False
    opts = _ydl_basis_opts()
    opts.update({"skip_download": True, "noplaylist": True})
    info = None
    for _ in (1, 2):
        try:
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            break
        except Exception:                            # noqa: BLE001 — Cookie/Netz, 2. Versuch ohne Cookies
            opts.pop("cookiesfrombrowser", None)
    if not info:
        return False
    e["titel"] = info.get("title") or e.get("titel", "")
    e["uploader"] = info.get("uploader") or info.get("channel") or e.get("uploader", "")
    if info.get("duration"):
        e["dauer"] = info["duration"]
    e["upload_date"] = info.get("upload_date") or e.get("upload_date", "")
    e["url"] = info.get("webpage_url") or e.get("url", "")
    kap = _kapitel_aus_info(info)
    if kap:
        e["kapitel"] = kap                             # Kapitel für Alt-Einträge nachtragen
    return True


_technik_laeuft = False


def technik_backfill():
    """Codec/Qualität für vorhandene Dateien nachtragen, die es noch nicht haben
    (per ffprobe, lokal, offline). Läuft einmal im Hintergrund beim Start."""
    global _technik_laeuft
    if _technik_laeuft:
        return
    _technik_laeuft = True
    try:
        idx = _datei_index()
        geaendert = False
        for k, e in list(_geladen.items()):
            if e.get("acodec"):
                continue
            vid = k.split("|")[0]
            pfad = (e.get("pfad") if e.get("pfad") and os.path.isfile(e.get("pfad"))
                    else _datei_aus(idx.get(vid), k.partition("|")[2]))
            t = _technik(pfad) if pfad else {}
            if t:
                e.update({"vcodec": t.get("vcodec", ""), "acodec": t.get("acodec", ""),
                          "abr": t.get("abr", 0), "asr": t.get("asr", 0),
                          "hoehe": t.get("height", 0) or e.get("hoehe", 0)})
                geaendert = True
        if geaendert:
            with _io_lock:
                _json_speichern(GELADEN_PFAD, _geladen)
    finally:
        _technik_laeuft = False


# ---- Downloads-Ordner selbstheilend einsortieren (JB 14.07.): von Hand
# verschobene Dateien wandern anhand ihrer Metadaten zurück in den richtigen
# Kategorie-Ordner (MP3 / 4K+ / Video); was unklar bleibt, kommt nach
# "Sonstiges" statt falsch einsortiert zu werden.

SONSTIGES = "Sonstiges"
AUDIO_EXT = (".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav", ".aac")
VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov", ".avi")
_einsortier_laeuft = False


def _soll_kategorie(pfad):
    """Kategorie einer Datei im Downloads-Ordner: Audio-Endung -> MP3;
    Video -> Höhe aus der geladen-DB (Video-ID im Namen) oder per ffprobe;
    '' = keine Mediendatei (nicht anfassen), None = Mediendatei, aber unklar."""
    ext = os.path.splitext(pfad)[1].lower()
    if ext in AUDIO_EXT:
        return "MP3"
    if ext not in VIDEO_EXT:
        return ""
    m = re.search(r"\[([\w-]{6,})\]", os.path.basename(pfad))
    if m:
        vid = m.group(1)
        for k, e in _geladen.items():
            if k.split("|")[0] == vid and e.get("hoehe"):
                return _kategorie("", e.get("hoehe"))
    h = _hoehe_ffprobe(pfad)
    return _kategorie("", h) if h else None


def downloads_einsortieren():
    """Bewegt Mediendateien INNERHALB des Downloads-Ordners an ihren Platz.
    Nicht-destruktiv: nie überschreiben (nummerierter Name), .part/.vtt/Bilder
    und frisch geänderte Dateien (<60 s, evtl. noch in Arbeit) bleiben liegen,
    Playlist-Sync-Ziele im Downloads-Ordner sind tabu (Spiegel-Kopien)."""
    global _einsortier_laeuft
    if _einsortier_laeuft or not CFG.get("unterordner", True):
        return 0
    _einsortier_laeuft = True
    bewegt = 0
    try:
        basis = os.path.abspath(ziel_ordner())
        tabu = [os.path.abspath(p["sync_ordner"]) for p in _playlists if p.get("sync_ordner")]
        for wurzel, dirs, dateien in os.walk(basis):
            w = os.path.abspath(wurzel)
            if any(w == t or w.startswith(t + os.sep) for t in tabu):
                dirs[:] = []
                continue
            for fn in dateien:
                pfad = os.path.join(wurzel, fn)
                kat = _soll_kategorie(pfad)
                if kat == "":
                    continue                          # keine Mediendatei -> in Ruhe lassen
                ziel_dir = _ordner_fuer(kat) if kat else os.path.join(basis, SONSTIGES)
                if w == os.path.abspath(ziel_dir):
                    continue                          # liegt schon richtig
                try:
                    if time.time() - os.path.getmtime(pfad) < 60:
                        continue                      # evtl. gerade in Arbeit
                    os.makedirs(ziel_dir, exist_ok=True)
                    stem, ext = os.path.splitext(fn)
                    neu, n = os.path.join(ziel_dir, fn), 2
                    while os.path.exists(neu):        # nie überschreiben
                        neu = os.path.join(ziel_dir, f"{stem} ({n}){ext}")
                        n += 1
                    os.replace(pfad, neu)
                    _sidecars_mit(pfad, neu)
                    bewegt += 1
                    for e in _geladen.values():       # Bibliothek kennt sofort den neuen Ort
                        if e.get("pfad") == pfad:
                            e["pfad"] = neu
                            e["name"] = os.path.basename(neu)
                            if kat:
                                e["kategorie"] = kat
                except OSError:
                    continue
        if bewegt:
            with _io_lock:
                _json_speichern(GELADEN_PFAD, _geladen)
            _sag(f"Downloads einsortiert: {bewegt} Datei(en) an den richtigen Platz bewegt")
    finally:
        _einsortier_laeuft = False
    return bewegt


def ordner_importieren():
    """Mediendateien im Downloads-Ordner, die NICHT in der Bibliothek stehen,
    additiv aufnehmen (JB-/Kumpel-Wunsch: „andere Elemente im Ordner erkennen").
    Video-ID aus dem Namen ([id]) wird als Schlüssel genutzt, sonst ein
    stabiler Pfad-Hash; Titel = Dateiname ohne [id]. Löscht/ändert nie etwas."""
    bekannt = set()
    for k, e in _geladen.items():
        p = e.get("pfad")
        if p:
            bekannt.add(os.path.normcase(os.path.abspath(p)))
    neu = 0
    for wurzel, _, dateien in os.walk(ziel_ordner()):
        for fn in dateien:
            if not fn.lower().endswith(AUDIO_EXT + VIDEO_EXT):
                continue
            pfad = os.path.join(wurzel, fn)
            if os.path.normcase(os.path.abspath(pfad)) in bekannt:
                continue
            m = re.search(r"\[([\w-]{6,})\]", fn)
            vid = m.group(1) if m else ("lokal-" + hashlib.md5(
                os.path.abspath(pfad).encode("utf-8")).hexdigest()[:11])
            audio = fn.lower().endswith(AUDIO_EXT)
            key = f"{vid}|{'audio' if audio else 'lokal'}"
            if key in _geladen:
                continue
            try:
                groesse = os.path.getsize(pfad)
            except OSError:
                continue
            _geladen[key] = {
                "name": fn, "groesse": groesse, "pfad": pfad,
                "kategorie": "MP3" if audio else _kat_aus_name(fn),
                "titel": _titel_aus_name(fn),
                "url": (f"https://www.youtube.com/watch?v={vid}" if _plausible_id(vid) else ""),
                "qualitaet": "audio" if audio else "lokal",
                "importiert": True, "ts": time.time()}
            neu += 1
    if neu:
        with _io_lock:
            _json_speichern(GELADEN_PFAD, _geladen)
        _sag(f"Ordner-Import: {neu} neue Datei(en) in die Bibliothek aufgenommen")
    return neu


def pfade_heilen():
    """Tote 'pfad'-Einträge der geladen-DB reparieren (z.B. nach einem Ordner-
    Umzug wie Stage 3): existiert der gespeicherte Pfad nicht mehr, aber die
    Datei ist per Video-ID im Downloads-Ordner auffindbar, wird der Eintrag
    auf den echten Ort umgeschrieben. Rein additiv, löscht nie etwas."""
    idx = _datei_index()
    geheilt = 0
    for k, e in _geladen.items():
        p = e.get("pfad")
        if p and not os.path.isfile(p):
            neu = _datei_aus(idx.get(k.split("|")[0]), k.partition("|")[2])
            if neu:
                e["pfad"] = neu
                e["name"] = os.path.basename(neu)
                geheilt += 1
    if geheilt:
        with _io_lock:
            _json_speichern(GELADEN_PFAD, _geladen)
        _sag(f"Pfade geheilt: {geheilt} Bibliotheks-Einträge zeigen wieder auf echte Dateien")
    return geheilt


def _einsortieren_hintergrund():
    """Kurz nach dem Start + alle 6 h aufräumen (Daemon-Thread)."""
    time.sleep(20)
    for fn in (pfade_heilen, ordner_importieren):     # Pfade heilen + fremde Dateien aufnehmen
        try:
            fn()
        except Exception:                             # noqa: BLE001
            pass
    while True:
        try:
            downloads_einsortieren()
            ordner_importieren()
        except Exception:                             # noqa: BLE001
            pass
        time.sleep(6 * 3600)


_enrich_laeuft = False


def biblio_enrich_alle():
    """Alle Einträge ohne Kanal-Info nachreichern (Hintergrund, sanft gedrosselt)."""
    global _enrich_laeuft
    if _enrich_laeuft:
        return
    _enrich_laeuft = True
    try:
        for k in [k for k, e in list(_geladen.items()) if not e.get("uploader")]:
            e = _geladen.get(k)
            if e and _enrich_eintrag(k, e):
                with _io_lock:
                    _json_speichern(GELADEN_PFAD, _geladen)
            time.sleep(0.4)
    finally:
        _enrich_laeuft = False


def _enrich_keys(keys):
    """Metadaten für BESTIMMTE Einträge neu laden (Batch-Auswahl, erzwingt Nachladen)."""
    for k in list(keys):
        e = _geladen.get(k)
        if e and _enrich_eintrag(k, e):
            with _io_lock:
                _json_speichern(GELADEN_PFAD, _geladen)
        time.sleep(0.4)


def _finde_datei(url, e):
    """Datei zu einem DB-Eintrag finden: gespeicherter Pfad, Zielordner/Name,
    zuletzt rekursiv über die eindeutige Video-ID im Dateinamen ('[<id>]')
    — so wird sie auch in Unterordnern gefunden, egal wie groß sie ist."""
    for k in (e.get("pfad"), os.path.join(ziel_ordner(), e.get("name") or "")):
        if k and os.path.isfile(k):
            return k
    vid = _video_id(url)
    muster = os.path.join(ziel_ordner(), "**", f"*[[]{glob.escape(vid)}[]]*")
    treffer = [p for p in glob.glob(muster, recursive=True)
               if os.path.isfile(p) and p.lower().endswith(AUDIO_EXT + VIDEO_EXT)]
    return _datei_aus(treffer, e.get("qualitaet") or "")


def schon_geladen(url, qualitaet):
    """Schon fertig auf der Platte? Primär zählt die eindeutige Video-ID im
    Dateinamen (nicht die Byte-Größe): so bleibt ein Download auch dann als
    Dublette erkannt, wenn sich die Größe geändert hat (z. B. durch nachträglich
    eingebettetes Cover/Metadaten). Weicht die Größe ab, wird der DB-Eintrag
    geheilt statt das Video fälschlich neu zu laden. -> Fundpfad oder None."""
    e = _geladen.get(_geladen_key(url, qualitaet))
    if not e:
        return None
    pfad = _finde_datei(url, e)
    if not pfad:
        return None
    try:
        groesse = os.path.getsize(pfad)
    except OSError:
        return None
    if groesse < 1024:                       # unplausibel klein -> als ungültig ignorieren
        return None
    if groesse != e.get("groesse") or pfad != e.get("pfad"):
        e.update({"groesse": groesse, "pfad": pfad, "name": os.path.basename(pfad)})
        with _io_lock:
            _json_speichern(GELADEN_PFAD, _geladen)
    return pfad


def db_statistik():
    """Alle je geladenen Downloads für den Gesamt-Counter: Summe + je Kategorie."""
    kat = {}
    for e in _geladen.values():
        k = e.get("kategorie")
        if not k:                     # Altbestand ohne Kategorie -> aus Endung raten
            name = (e.get("name") or "").lower()
            k = "MP3" if name.endswith((".mp3", ".m4a", ".opus", ".ogg", ".flac")) else "Video"
        kat[k] = kat.get(k, 0) + 1
    return {"gesamt": len(_geladen), "kategorien": kat}


def _addon_xpi_pfad():
    """Neueste signierte Browser-Erweiterung neben dem Code (browser-addon/dist),
    falls vorhanden — die App bietet sie dann unter /addon.xpi zur Installation an."""
    treffer = sorted(glob.glob(os.path.join(SCRIPT_DIR, "browser-addon", "dist", "*.xpi")))
    return treffer[-1] if treffer else ""


def _als_uebersprungen(item, fundpfad):
    item["status"] = "uebersprungen"
    item["datei"] = fundpfad
    try:
        item["gesamt"] = os.path.getsize(fundpfad)
    except OSError:
        item["gesamt"] = 0
    item["prozent"] = 100.0
    item["phase"] = ""
    item["fehler"] = ""
    if not item.get("kategorie"):
        e = _geladen.get(_geladen_key(item["url"], item["qualitaet"]))
        item["kategorie"] = (e or {}).get("kategorie") or _kategorie(item["qualitaet"], None)


def _schon_da(url, qualitaet, ausser=None):
    """Gleiches Video in gleicher Qualität nur einmal — andere Qualität ist erlaubt."""
    vid = _video_id(url)
    return any(it["id"] != ausser and it["qualitaet"] == qualitaet
               and _video_id(it["url"]) == vid for it in Q.items)


def _fehltext(exc):
    t = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))      # ANSI-Farben raus
    t = t.replace("ERROR: ", "").strip()
    return t[:300]


def herunterladen(item):
    """Einen Eintrag laden. Fortsetzen (.part) macht yt-dlp automatisch."""
    erzwingen = bool(item.pop("erzwingen", False))
    if not erzwingen:
        fund = schon_geladen(item["url"], item["qualitaet"])
        if fund:                                     # JB-Regel: Name+Größe identisch -> überspringen
            _als_uebersprungen(item, fund)
            Q.speichern()
            return
    if item.get("geo_laender") and not item.get("geo_versucht") and CFG.get("geo_vpn"):
        _geo_download(item, erzwingen)
        return
    _download_lauf(item, erzwingen)


def _zugang_ok(url, extra_opts, timeout=30):
    """Schneller Check (nur Metadaten, ohne Cookies): gibt es mit diesen Optionen
    Zugang zum Video (kein Geo-Fehler, Formate vorhanden)?"""
    import yt_dlp
    opts = _ydl_basis_opts(mit_cookies=False)
    opts.update({"skip_download": True, "noplaylist": True,
                 "quiet": True, "no_warnings": True, "socket_timeout": 20})
    opts.update(extra_opts or {})
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=False)
        return bool(info) and bool(info.get("formats") or info.get("url") or info.get("entries"))
    except Exception:                                # noqa: BLE001 — jeder Fehler = kein Zugang
        return False


def _geo_download(item, erzwingen):
    """Gestufte Geo-Umgehung (JB-Wunsch: alle Wege verketten): Header-Trick ->
    eigene Proxys -> Gratis-Proxys -> VPN. Der erste Weg, der Zugang gibt,
    gewinnt. Geo-Läufe laufen IMMER ohne Konto-Cookies. VPN-Verbindungen werden
    nach dem Download wieder getrennt (außer JB war selbst schon verbunden)."""
    laender = item.get("geo_laender") or []
    item["geo_versucht"] = True
    kands = geo.kandidaten(laender, CFG)
    if not kands:
        item["status"] = "fehler"
        item["phase"] = ""
        item["fehler"] = "Geo-Sperre — kein nutzbares Land erkannt (" + ", ".join(laender[:4]) + ")"
        Q.speichern()
        return
    for kand in kands:
        if item["id"] in Q.abbrueche:
            item["status"] = "pausiert"; item["phase"] = ""; Q.speichern(); return
        item["phase"] = "Geo: " + kand.name
        item["geschw"] = 0
        Q.speichern()
        setup_ok = True
        if kand.setup:
            try:
                setup_ok = bool(kand.setup())
            except Exception:                        # noqa: BLE001
                setup_ok = False
        try:
            if setup_ok and _zugang_ok(item["url"], kand.opts):
                _download_lauf(item, erzwingen, mit_cookies=False, extra_opts=kand.opts, geo=True)
        finally:
            if kand.teardown:
                try:
                    kand.teardown()
                except Exception:                    # noqa: BLE001
                    pass
        if item["status"] in ("fertig", "pausiert"):
            return
    item["status"] = "fehler"
    item["phase"] = ""
    item["fehler"] = ("Geo-Umgehung fehlgeschlagen (" + ", ".join(laender[:4]) +
                      "). Tipp: eigenen Proxy/VPN im Zahnrad einrichten.")
    Q.speichern()


# ---- Geo-Test (Assistent): probiert die Kette und meldet je Methode Zugang ja/nein

_geo_test = {"laeuft": False, "stand": 0.0, "url": "", "titel": "", "info": "", "ergebnisse": []}


def geo_test_lauf(url, titel, laender):
    _geo_test.update({"laeuft": True, "stand": time.time(), "url": url, "titel": titel,
                      "info": "", "ergebnisse": []})
    try:
        kands = geo.kandidaten(laender, CFG)
        if not kands:
            _geo_test["info"] = "Keine Methode möglich (Land nicht erkannt oder alles aus)."
            return
        for kand in kands:
            eintrag = {"name": kand.name, "ok": None}
            _geo_test["ergebnisse"].append(eintrag)
            _geo_test["stand"] = time.time()
            setup_ok = True
            if kand.setup:
                try:
                    setup_ok = bool(kand.setup())
                except Exception:                    # noqa: BLE001
                    setup_ok = False
            ok = False
            try:
                ok = bool(setup_ok and _zugang_ok(url, kand.opts, timeout=25))
            finally:
                if kand.teardown:
                    try:
                        kand.teardown()
                    except Exception:                # noqa: BLE001
                        pass
            eintrag["ok"] = ok
            _geo_test["stand"] = time.time()
            if ok:
                _geo_test["info"] = f"Zugang über: {kand.name}"
                return
        _geo_test["info"] = "Keine Methode gab Zugang — Proxy/VPN einrichten."
    finally:
        _geo_test["laeuft"] = False
        _geo_test["stand"] = time.time()


def _download_lauf(item, erzwingen=False, mit_cookies=True, extra_opts=None, geo=False):
    import yt_dlp

    def hook(d):
        if item["id"] in Q.abbrueche:
            raise AbbruchError()
        if d["status"] == "downloading":
            gesamt = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            item["geladen"] = d.get("downloaded_bytes") or 0
            item["gesamt"] = gesamt
            item["geschw"] = d.get("speed") or 0
            item["eta"] = d.get("eta")
            if gesamt:
                item["prozent"] = round(item["geladen"] * 100.0 / gesamt, 1)
            info = d.get("info_dict") or {}
            # Video- und Tonspur kommen nacheinander — anzeigen, was gerade lädt
            note = (info.get("format_note") or "").lower()
            if (info.get("vcodec") in (None, "none")) or "audio" in note:
                item["phase"] = "Tonspur"
            else:
                item["phase"] = "Video"
        elif d["status"] == "finished":
            item["prozent"] = 100.0
            item["phase"] = "Zusammenfügen"
            item["geschw"] = 0

    opts = _ydl_basis_opts(mit_cookies=mit_cookies)
    opts.update({
        "outtmpl": os.path.join(ziel_ordner(), "%(title)s [%(id)s].%(ext)s"),
        "format": QUALITAETEN[item["qualitaet"]],
        "noplaylist": True,
        "continuedl": True,
        "progress_hooks": [hook],
        "merge_output_format": "mp4",
    })
    # OHNE ffmpeg kann yt-dlp Bild+Ton nicht zusammenfügen -> Videos schlugen fehl
    # (z.B. nackte exe ohne bin\-Ordner). Fallback: fertige Kombi-Formate (progressive),
    # begrenzt auf die gewünschte Höhe — läuft ohne Zusammenfügen, max. ~720p.
    if not _ffmpeg_pfad() and item["qualitaet"] != "audio":
        h = {"2160p": 2160, "1440p": 1440, "1080p": 1080, "720p": 720}.get(item["qualitaet"])
        grenze = f"[height<={h}]" if h else ""
        opts["format"] = (f"best{grenze}[vcodec!=none][acodec!=none]"
                          f"/best[vcodec!=none][acodec!=none]/best")
        opts.pop("merge_output_format", None)
    if erzwingen:                                    # „Trotzdem laden": vorhandene Datei ersetzen
        opts["overwrites"] = True

    # Untertitel als .vtt neben die Datei legen. ".*-orig" = die ORIGINAL-Sprache
    # des Videos (yt-dlp-Kennung für die unübersetzte Auto-Spur, z.B. "ja-orig") —
    # wichtig fürs Karaoke (JB: authentisch, als Romaji angezeigt).
    if CFG.get("untertitel", True):
        opts.update({"writesubtitles": True, "writeautomaticsub": True,
                     "subtitleslangs": ["de", "en", ".*-orig"], "subtitlesformat": "vtt/best"})

    hat_ff = bool(_ffmpeg_pfad())
    pps = []
    # SponsorBlock: Werbe-/Intro-Segmente rausschneiden (zuerst in der PP-Kette,
    # damit danach Metadaten/Cover auf die geschnittene Datei angewandt werden).
    sb_cats = sponsorblock_kategorien(CFG.get("sponsorblock", "")) if hat_ff else []
    if sb_cats:
        pps.append({"key": "SponsorBlock", "categories": sb_cats, "when": "after_filter"})
        pps.append({"key": "ModifyChapters", "remove_sponsor_segments": sb_cats})
    if item["qualitaet"] == "audio":
        opts.pop("merge_output_format", None)
        if hat_ff:
            pps.append({"key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3", "preferredquality": "0"})
        else:  # ohne ffmpeg keine Umwandlung -> natives m4a nehmen
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"

    # Metadaten (Titel, Uploader als Künstler, Datum, Beschreibung, Kapitel) in
    # die Datei schreiben — muss VOR dem Cover laufen (sonst überschreibt ffmpeg
    # beim Metadaten-Remux das Bild wieder).
    if hat_ff and CFG.get("metadaten", True):
        pps.append({"key": "FFmpegMetadata", "add_metadata": True,
                    "add_chapters": True})
    # Thumbnail als Dateicover einbetten (Video = Cover-Art, Audio = statisches
    # Album-Bild, das der Explorer als MP3-Vorschau zeigt). Braucht ffmpeg; nach
    # jpg wandeln, weil YouTube oft .webp liefert (mp4/mp3 können kein webp-Cover).
    if hat_ff:
        opts["writethumbnail"] = True
        pps.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})
        pps.append({"key": "EmbedThumbnail"})
    if pps:
        opts["postprocessors"] = pps
    if extra_opts:                                   # Geo-Umgehung: proxy / geo_bypass_country
        opts.update(extra_opts)

    def _lauf(o):
        with yt_dlp.YoutubeDL(o) as ydl:
            return ydl.extract_info(item["url"], download=True)

    try:
        try:
            info = _lauf(opts)
        except AbbruchError:
            raise
        except Exception as e:                       # noqa: BLE001 — heilbare Fehler heilen
            if _ist_cookie_fehler(e):
                opts.pop("cookiesfrombrowser", None)
            elif _ist_untertitel_fehler(e):
                for k in ("writesubtitles", "writeautomaticsub",
                          "subtitleslangs", "subtitlesformat"):
                    opts.pop(k, None)
            else:
                raise
            info = _lauf(opts)
        rd = (info or {}).get("requested_downloads") or []
        if rd:
            item["datei"] = rd[0].get("filepath") or ""
        # Codec/Qualität aus der fertigen Datei lesen (fürs Bibliotheks-Feld)
        tech = _technik(item["datei"])
        item["vcodec"] = tech.get("vcodec", "")
        item["acodec"] = tech.get("acodec", "")
        item["abr"] = tech.get("abr", 0)
        item["asr"] = tech.get("asr", 0)
        # Kategorie bestimmen (echte Höhe) und in den passenden Unterordner legen
        hoehe = (info or {}).get("height") or (rd[0].get("height") if rd else None) or tech.get("height")
        item["hoehe"] = hoehe or 0
        item["kategorie"] = _kategorie(item["qualitaet"], hoehe)
        item["datei"] = _in_unterordner(item["datei"], item["kategorie"])
        if item["datei"] and os.path.exists(item["datei"]):
            item["gesamt"] = os.path.getsize(item["datei"])   # echte Endgröße (nach Cover/Metadaten)
        item["titel"] = (info or {}).get("title") or item["titel"]
        item["uploader"] = (info or {}).get("uploader") or (info or {}).get("channel") or item.get("uploader", "")
        item["upload_date"] = (info or {}).get("upload_date") or item.get("upload_date", "")
        item["kapitel"] = _kapitel_aus_info(info)      # YouTube-Kapitel für Sprungmarken im Player
        if (info or {}).get("duration"):
            item["dauer"] = info["duration"]
        item["status"] = "fertig"
        item["prozent"] = 100.0
        item["phase"] = ""
        item["fertig_ts"] = time.time()
        geladen_merken(item)
    except AbbruchError:
        item["status"] = "pausiert"
        item["phase"] = ""
        item["geschw"] = 0
        if item not in Q.items:                      # via „Entfernen" abgebrochen -> id aufräumen
            Q.abbrueche.discard(item["id"])
    except Exception as e:                           # noqa: BLE001 — Auto-Neuversuch
        if item["id"] in Q.abbrueche:                # yt-dlp verpackt Hook-Fehler teils neu
            item["status"] = "pausiert"
            item["phase"] = ""
            item["geschw"] = 0
            if item not in Q.items:
                Q.abbrueche.discard(item["id"])
            Q.speichern()
            return
        item["versuche"] += 1
        item["fehler"] = _fehltext(e)
        item["geschw"] = 0
        item["phase"] = ""
        voll = str(e)
        if geo:                                      # Geo-Lauf: kein Backoff, die Kette geht weiter
            item["status"] = "fehler"
            Q.speichern()
            return
        if geo.ist_geo_fehler(voll) and not item.get("geo_versucht") and CFG.get("geo_vpn"):
            item["geo_laender"] = geo.laender_aus_fehler(voll)
            item["versuche"] -= 1                     # zählt nicht als Fehlversuch
            item["naechster_versuch"] = 0
            item["status"] = "wartend"                # nächster Lauf geht durch die Geo-Kette
        elif any(s in item["fehler"].lower() for s in DAUERHAFT):
            item["status"] = "fehler"                # Neuversuch bringt hier nichts
        elif item["versuche"] <= CFG.get("max_wiederholungen", 10):
            warte = BACKOFF[min(item["versuche"] - 1, len(BACKOFF) - 1)]
            item["naechster_versuch"] = time.time() + warte
            item["status"] = "wartend"               # Neuversuch setzt am .part fort
        else:
            item["status"] = "fehler"
    Q.speichern()


def worker_schleife():
    while True:
        item = Q.naechster()
        if item is None:
            time.sleep(1)
            continue
        Q.speichern()
        herunterladen(item)


_fehler_seit = {}   # item-id -> Zeitpunkt, seit dem der Eintrag „fehler" ist


def _fehler_aufraeumen():
    """Fehler-Einträge, die seit `fehler_ausblenden_min` Minuten in der Queue
    stehen, automatisch entfernen (JB-Wunsch: nicht ewig den Fehler lesen)."""
    minuten = CFG.get("fehler_ausblenden_min", 0)
    if not minuten:
        _fehler_seit.clear()
        return
    jetzt = time.time()
    raus = set()
    with Q.lock:
        fehler_ids = {it["id"] for it in Q.items if it["status"] == "fehler"}
        for i in fehler_ids:                          # neue Fehler-Zeitpunkte merken
            _fehler_seit.setdefault(i, jetzt)
        for i in list(_fehler_seit):                  # nicht mehr fehlerhafte vergessen
            if i not in fehler_ids:
                del _fehler_seit[i]
        raus = {i for i, t0 in _fehler_seit.items() if jetzt - t0 >= minuten * 60}
        if raus:
            Q.items[:] = [it for it in Q.items if it["id"] not in raus]
            for i in raus:
                _fehler_seit.pop(i, None)
    if raus:
        Q.speichern()


def ticker_schleife():
    """Fortschritt alle 5 s sichern, damit ein Absturz höchstens 5 s Anzeige kostet."""
    while True:
        time.sleep(5)
        if any(it["status"] == "laeuft" for it in Q.items):
            Q.speichern()
        _fehler_aufraeumen()


# ---------------------------------------------------------------- HTTP-Server

def _cors(handler):
    """CORS nur für Browser-Erweiterungen freigeben (nie für beliebige Webseiten —
    der Server lauscht ohnehin nur auf 127.0.0.1). Erlaubt das Firefox-Addon,
    Links direkt an die Warteschlange zu schicken."""
    origin = handler.headers.get("Origin", "")
    if origin.startswith(("moz-extension://", "chrome-extension://")):
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Access-Control-Allow-Headers", "Content-Type")
        handler.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")


def _antwort(handler, code, daten, ctype="application/json"):
    body = daten if isinstance(daten, bytes) else json.dumps(daten, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", ctype + "; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    _cors(handler)
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):                        # Konsole ruhig halten
        pass

    def do_OPTIONS(self):                             # CORS-Preflight des Addons
        self.send_response(204)
        _cors(self)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def _hat_zugriff(self):
        """Localhost immer; aus dem LAN nur die Handy-Seite selbst oder mit gültigem Code."""
        ip = self.client_address[0] if self.client_address else ""
        if ip in ("127.0.0.1", "::1"):
            return True
        if urlparse(self.path).path in ("/m", "/handy"):
            return True
        q = parse_qs(urlparse(self.path).query)
        code = (q.get("code") or [self.headers.get("X-Code", "")])[0]
        return zugriff_erlaubt(ip, CFG.get("fernsteuerung"), CFG.get("fernsteuerung_code") or "", code)

    def do_GET(self):
        if not self._hat_zugriff():
            return _antwort(self, 403, {"fehler": "Kein Zugriff — Fernsteuerung aus oder falscher Code."})
        if urlparse(self.path).path in ("/m", "/handy"):     # schlanke Handy-Oberfläche
            import importlib
            import handy
            try:
                importlib.reload(handy)
            except Exception:                        # noqa: BLE001
                pass
            return _antwort(self, 200, handy.HTML.encode("utf-8"), "text/html")
        if self.path in ("/", "/index.html"):
            # Oberfläche bei jedem Aufruf FRISCH laden (sonst cacht Python das Modul
            # und Änderungen an oberflaeche.py erscheinen erst nach App-Neustart —
            # ein Browser-Refresh reicht jetzt).
            import importlib
            import oberflaeche
            try:
                importlib.reload(oberflaeche)
            except Exception:                        # noqa: BLE001 — im Zweifel alte Version
                pass
            _antwort(self, 200, oberflaeche.HTML.encode("utf-8"), "text/html")
        elif self.path == "/api/status":
            with Q.lock:
                _antwort(self, 200, {"items": Q.items, "config": CFG,
                                     "ziel": ziel_ordner(), "ffmpeg": bool(_ffmpeg_pfad()),
                                     "vpn": geo.nordvpn_verfuegbar(), "db": db_statistik(),
                                     "remote": _remote, "fernsteuerung": fernsteuerung_info(),
                                     "autotag": _autotag, "addon_xpi": bool(_addon_xpi_pfad()),
                                     "jetzt": time.time()})
        elif self.path == "/addon.xpi":
            # Signierte Firefox-Erweiterung direkt aus der App installieren —
            # richtiger MIME-Typ, damit Firefox den Installations-Dialog zeigt.
            p = _addon_xpi_pfad()
            if not p:
                return _antwort(self, 404, {"fehler": "Keine signierte Erweiterung da "
                                            "(browser-addon/dist/*.xpi fehlt)."})
            with open(p, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-xpinstall")
            self.send_header("Content-Length", str(len(body)))
            _cors(self)
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/bibliothek":
            with _io_lock:
                _antwort(self, 200, {"items": bibliothek_liste()})
        elif self.path == "/api/playlists":
            with _io_lock:
                _antwort(self, 200, {"items": _playlists})
        elif self.path == "/api/abos":
            with _io_lock:
                _antwort(self, 200, {"items": _abos})
        elif self.path.startswith("/api/playlist_export"):
            pid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            pl = next((p for p in _playlists if p.get("id") == pid), None)
            if not pl:
                return _antwort(self, 404, {"fehler": "Playlist unbekannt"})
            body = playlist_m3u(pl).encode("utf-8")
            fn = re.sub(r"[^\w .-]", "_", pl.get("name", "playlist"))[:60] or "playlist"
            self.send_response(200)
            self.send_header("Content-Type", "audio/x-mpegurl; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{fn}.m3u"')
            self.send_header("Content-Length", str(len(body)))
            _cors(self)
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/geo_status":
            st = geo.status(CFG)
            st["config"] = {k: CFG.get(k) for k in ("geo_vpn", "geo_gratis_proxy")}
            st["proxy_anzahl"] = len(CFG.get("geo_proxies") or [])
            st["test"] = _geo_test
            _antwort(self, 200, st)
        elif self.path.startswith("/api/untertitel"):
            q = parse_qs(urlparse(self.path).query)
            key = (q.get("id") or [""])[0]
            wunsch = (q.get("lang") or [""])[0]
            romaji = (q.get("romaji") or ["0"])[0] == "1"
            f, lang = untertitel_datei(key, wunsch or None)
            if not f:
                return _antwort(self, 404, {"fehler": "keine Untertitel auf der Platte"})
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                # Romaji nur für Japanisch/Original-Spuren (Latein-Texte laufen eh durch)
                if romaji and (lang.lower().startswith("ja") or lang.lower().endswith("-orig")):
                    text = _romaji(text)
                else:
                    romaji = False
                _antwort(self, 200, {"lang": lang, "vtt": text, "romaji": romaji,
                                     "sprachen": [s for _, s in untertitel_liste(key)]})
            except OSError:
                _antwort(self, 404, {"fehler": "Untertitel-Datei nicht lesbar"})
        elif self.path.startswith("/media"):
            key = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            pfad = _pfad_zu_key(key)
            if pfad and os.path.isfile(pfad):
                _stream_datei(self, pfad)
            else:
                _antwort(self, 404, {"fehler": "Datei nicht gefunden"})
        else:
            _antwort(self, 404, {"fehler": "unbekannt"})

    def do_POST(self):
        if not self._hat_zugriff():
            return _antwort(self, 403, {"fehler": "Kein Zugriff — Fernsteuerung aus oder falscher Code."})
        n = int(self.headers.get("Content-Length") or 0)
        try:
            daten = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except ValueError:
            return _antwort(self, 400, {"fehler": "kein JSON"})
        try:
            if self.path == "/api/remote":            # Befehl vom Handy an den PC-Player
                return _antwort(self, 200, remote_befehl(daten))
            if self.path == "/api/beenden":
                # Sauberes Beenden aus der Suite (JB 14.07.2026: im Suite-Betrieb gibt es
                # kein eigenes Tray mehr — Steuerung über SyncDashTray/Dashboard). Nur vom
                # eigenen PC (bei aktiver Handy-Fernsteuerung lauscht der Server im WLAN).
                if self.client_address[0] != "127.0.0.1":
                    return _antwort(self, 403, {"fehler": "nur lokal"})
                Q.speichern()
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return _antwort(self, 200, {"ok": True})
            if self.path == "/api/add":
                self._add(daten)
            elif self.path == "/api/action":
                self._action(daten)
            elif self.path == "/api/config":
                self._config(daten)
            elif self.path == "/api/played":         # ein Titel wurde abgespielt
                with _io_lock:
                    e = _geladen.get(daten.get("id") or "")
                    if e:
                        e["plays"] = int(e.get("plays", 0)) + 1
                        e["last_play"] = time.time()  # für „Zuletzt gespielt"
                        _json_speichern(GELADEN_PFAD, _geladen)
            elif self.path == "/api/biblio":
                self._biblio(daten)
            elif self.path == "/api/biblio_enrich":
                threading.Thread(target=biblio_enrich_alle, daemon=True).start()
            elif self.path == "/api/importieren":     # fremde Dateien im Ordner aufnehmen
                n = ordner_importieren()
                return _antwort(self, 200, {"neu": n})
            elif self.path == "/api/playlist":
                if daten.get("art") == "sync":
                    pl = next((p for p in _playlists if p.get("id") == daten.get("id")), None)
                    return _antwort(self, 200, playlist_sync(pl))
                playlist_aktion(daten)
            elif self.path == "/api/geo_wireguard":
                return _antwort(self, 200, self._geo_wireguard(daten))
            elif self.path == "/api/geo_test":
                return _antwort(self, 200, self._geo_test_start(daten))
            elif self.path == "/api/playlist_import":
                return _antwort(self, 200, playlist_import_m3u(daten.get("name"), daten.get("m3u")))
            elif self.path == "/api/abo":
                return _antwort(self, 200, abo_aktion(daten))
            elif self.path == "/api/clip":
                return _antwort(self, 200, clip_erstellen(daten))
            elif self.path == "/api/untertitel_laden":
                threading.Thread(target=untertitel_nachladen, args=(daten.get("id") or "",), daemon=True).start()
            elif self.path == "/api/autotag":
                threading.Thread(target=autotag_lauf, args=(daten.get("keys"),), daemon=True).start()
            else:
                return _antwort(self, 404, {"fehler": "unbekannt"})
            _antwort(self, 200, {"ok": True})
        except Exception as e:                       # noqa: BLE001
            _antwort(self, 500, {"fehler": _fehltext(e)})

    def _add(self, daten):
        qualitaet = daten.get("qualitaet") or CFG["standard_qualitaet"]
        ganze_liste = bool(daten.get("ganze_liste"))
        urls = [u.strip() for u in (daten.get("urls") or "").splitlines() if u.strip()]
        for url in urls:
            if not url.lower().startswith(("http://", "https://")):
                continue
            threading.Thread(target=aufloesen, args=(url, qualitaet, ganze_liste), daemon=True).start()

    def _action(self, daten):
        art = daten.get("art")
        if art == "ordner_offen":
            subprocess.Popen(["explorer", ziel_ordner()])
            return
        if art == "fertige_raus":
            with Q.lock:
                Q.items[:] = [x for x in Q.items
                              if x["status"] not in ("fertig", "uebersprungen")]
            Q.speichern()
            return
        if art == "queue_aufraeumen":                # Fehler + Erledigte raus, Laufendes/Wartendes bleibt
            with Q.lock:
                Q.items[:] = [x for x in Q.items
                              if x["status"] not in ("fertig", "uebersprungen", "fehler")]
            Q.speichern()
            return
        it = Q.finde(daten.get("id") or "")
        if not it:
            return
        with Q.lock:
            if art == "pause":
                if it["status"] == "laeuft":
                    Q.abbrueche.add(it["id"])        # Hook stoppt -> pausiert, .part bleibt
                elif it["status"] == "wartend":
                    it["status"] = "pausiert"
            elif art == "weiter" and it["status"] in ("pausiert", "fehler", "uebersprungen"):
                if it["status"] == "uebersprungen":  # „Trotzdem laden" ersetzt die Datei
                    it["erzwingen"] = True
                    it["prozent"] = 0.0
                    it["geladen"] = 0
                    it["gesamt"] = 0
                it.pop("geo_versucht", None)         # Geo-Automatik darf wieder ran
                it["status"] = "wartend"
                it["versuche"] = 0
                it["naechster_versuch"] = 0
                it["fehler"] = ""
            elif art == "sofort" and it["status"] == "wartend":
                it["naechster_versuch"] = 0
                it["fehler"] = ""
            elif art == "entfernen":                 # geht jetzt auch bei Laufenden (JB 13.07.)
                if it["status"] == "laeuft":
                    Q.abbrueche.add(it["id"])        # laufenden Abruf stoppen, .part bleibt
                Q.items.remove(it)                   # nur Listeneintrag — Dateien bleiben!
            elif art == "hoch" and it["status"] == "wartend":
                i = Q.items.index(it)
                ziel = next((j for j in range(i - 1, -1, -1)
                             if Q.items[j]["status"] == "wartend"), None)
                if ziel is not None:
                    Q.items.insert(ziel, Q.items.pop(i))
            elif art == "ordner":
                pfad = it.get("datei")
                if pfad and os.path.exists(pfad):
                    subprocess.Popen(["explorer", "/select,", pfad])
                else:
                    subprocess.Popen(["explorer", ziel_ordner()])
        Q.speichern()

    def _geo_wireguard(self, daten):
        """Eine WireGuard-.conf (Inhalt) unter <LAND>.conf im Ordner ablegen und
        den Ordner in die Config setzen. So richtet der Assistent WireGuard ein."""
        content = daten.get("content") or ""
        land = (daten.get("land") or "").strip().upper()
        if not content.strip() or not re.fullmatch(r"[A-Z]{2}", land):
            return {"fehler": "Config-Inhalt oder Ländercode (2 Buchstaben) fehlt."}
        if "[Interface]" not in content or "[Peer]" not in content:
            return {"fehler": "Das sieht nicht nach einer WireGuard-Config aus ([Interface]/[Peer] fehlt)."}
        ordner = CFG.get("geo_wireguard_ordner") or os.path.join(SCRIPT_DIR, "wireguard")
        try:
            os.makedirs(ordner, exist_ok=True)
            with open(os.path.join(ordner, land + ".conf"), "w", encoding="utf-8") as f:
                f.write(content)
            with Q.lock:
                CFG["geo_wireguard_ordner"] = ordner
                _json_speichern(CONFIG_PFAD, CFG)
        except OSError as e:
            return {"fehler": str(e)}
        return {"ok": True, "ordner": ordner, "laender": geo.wireguard_laender(ordner)}

    def _geo_test_start(self, daten):
        """Geo-Test starten: probiert die Kette an einem geo-gesperrten Video und
        meldet je Methode Zugang ja/nein (Ergebnisse via /api/geo_status)."""
        if _geo_test["laeuft"]:
            return {"ok": True, "laeuft": True}
        url = daten.get("url")
        laender = daten.get("laender")
        titel = daten.get("titel") or ""
        if not url:                                  # sonst: ein geo-gesperrtes Item aus der Queue
            it = next((i for i in Q.items if i.get("geo_laender")), None)
            if it:
                url, laender, titel = it["url"], it.get("geo_laender"), it.get("titel", "")
        if not url:
            return {"fehler": "Kein geo-gesperrtes Video zum Testen. Füge eins hinzu, "
                              "das in deinem Land blockiert ist, und starte den Test erneut."}
        threading.Thread(target=geo_test_lauf, args=(url, titel, laender or []), daemon=True).start()
        return {"ok": True, "laeuft": True}

    def _config(self, daten):
        erlaubt_browser = ("firefox", "chrome", "edge", "keine")
        with Q.lock:
            if daten.get("ziel_ordner") is not None:
                CFG["ziel_ordner"] = str(daten["ziel_ordner"]).strip()
            if daten.get("cookies_browser") in erlaubt_browser:
                CFG["cookies_browser"] = daten["cookies_browser"]
            if daten.get("standard_qualitaet") in QUALITAETEN:
                CFG["standard_qualitaet"] = daten["standard_qualitaet"]
            if isinstance(daten.get("geo_vpn"), bool):
                CFG["geo_vpn"] = daten["geo_vpn"]
            if isinstance(daten.get("geo_gratis_proxy"), bool):
                CFG["geo_gratis_proxy"] = daten["geo_gratis_proxy"]
            if isinstance(daten.get("geo_proxies"), list):
                CFG["geo_proxies"] = [str(x).strip() for x in daten["geo_proxies"] if str(x).strip()][:50]
            if daten.get("geo_wireguard_ordner") is not None:
                CFG["geo_wireguard_ordner"] = str(daten["geo_wireguard_ordner"]).strip()
            if isinstance(daten.get("unterordner"), bool):
                CFG["unterordner"] = daten["unterordner"]
            if isinstance(daten.get("metadaten"), bool):
                CFG["metadaten"] = daten["metadaten"]
            if isinstance(daten.get("fehler_ausblenden_min"), (int, float)):
                CFG["fehler_ausblenden_min"] = max(0, min(120, int(daten["fehler_ausblenden_min"])))
            if daten.get("sponsorblock") in ("", "sponsor", "alle"):
                CFG["sponsorblock"] = daten["sponsorblock"]
            if isinstance(daten.get("untertitel"), bool):
                CFG["untertitel"] = daten["untertitel"]
            if isinstance(daten.get("auto_update"), bool):
                CFG["auto_update"] = daten["auto_update"]
            if isinstance(daten.get("fernsteuerung"), bool):
                CFG["fernsteuerung"] = daten["fernsteuerung"]
                if daten["fernsteuerung"] and not CFG.get("fernsteuerung_code"):
                    CFG["fernsteuerung_code"] = uuid.uuid4().hex[:6].upper()   # Code beim Aktivieren erzeugen
            if isinstance(daten.get("parallel"), int) and 1 <= daten["parallel"] <= 3:
                CFG["parallel"] = daten["parallel"]
                _worker_start(CFG["parallel"])
            _json_speichern(CONFIG_PFAD, CFG)

    def _biblio(self, daten):
        key = daten.get("id") or ""
        art = daten.get("art")
        if art == "bulk":                            # mehrere auf einmal (Mehrfachauswahl)
            op = daten.get("op")
            keys = [k for k in (daten.get("keys") or []) if k in _geladen]
            if op == "enrich":                       # Metadaten der Auswahl neu laden (Hintergrund)
                threading.Thread(target=_enrich_keys, args=(keys,), daemon=True).start()
                return
            felder = daten.get("felder") or {}       # für op == "tag"
            with _io_lock:
                for k in keys:
                    e = _geladen.get(k)
                    if not e:
                        continue
                    if op == "archiv":
                        e["archiviert"] = True
                    elif op == "entarchiv":
                        e["archiviert"] = False
                    elif op == "loeschen":
                        _datei_loeschen(k)
                        _geladen.pop(k, None)
                    elif op == "vergessen":
                        _geladen.pop(k, None)
                    elif op == "tag":                # Batch-Tag: Kanal setzen + Titel-Ersetzung
                        up = felder.get("uploader")
                        if isinstance(up, str) and up.strip():
                            e["uploader"] = up.strip()[:200]
                        such = felder.get("titel_suchen")
                        if isinstance(such, str) and such:
                            ers = str(felder.get("titel_ersetzen") or "")
                            e["titel"] = ((e.get("titel") or "").replace(such, ers)).strip()[:300]
                _json_speichern(GELADEN_PFAD, _geladen)
                _json_speichern(PLAYLIST_PFAD, _playlists)
            return
        with _io_lock:
            e = _geladen.get(key)
            if not e:
                return
            if art == "loeschen":                    # Datei in den Papierkorb + aus Liste
                _datei_loeschen(key)
                _geladen.pop(key, None)
                _json_speichern(GELADEN_PFAD, _geladen)
                _json_speichern(PLAYLIST_PFAD, _playlists)
                return
            if art == "ordner":                      # Datei im Explorer zeigen (markiert)
                vid = key.split("|")[0]
                pfad = e.get("pfad")
                if not (pfad and os.path.exists(pfad)):
                    pfad = _datei_aus(_datei_index().get(vid), key.partition("|")[2])
                if pfad and os.path.exists(pfad):
                    subprocess.Popen(["explorer", "/select,", pfad])
                else:
                    subprocess.Popen(["explorer", ziel_ordner()])
                return
            if art == "neuladen":                    # verschobenen/gelöschten Titel neu holen
                vid = key.split("|")[0]
                url = e.get("url") or (f"https://www.youtube.com/watch?v={vid}"
                                       if _plausible_id(vid) else "")
                quali = e.get("qualitaet") or (key.split("|", 1)[1] if "|" in key else "beste")
                if url:
                    threading.Thread(target=aufloesen, args=(url, quali), daemon=True).start()
                return
            if art == "extern":                      # in VLC / Standardplayer öffnen
                pfad = _pfad_zu_key(key)
                if pfad:
                    extern_abspielen(pfad)
                return
            if art == "archiv":
                e["archiviert"] = True
            elif art == "entarchiv":
                e["archiviert"] = False
            elif art == "blacklist":                 # aus „Meistgespielt" ausschließen
                e["blacklist"] = True
            elif art == "unblacklist":
                e["blacklist"] = False
            elif art == "vergessen":                 # nur aus der Bibliothek, Datei bleibt
                _geladen.pop(key, None)
            _json_speichern(GELADEN_PFAD, _geladen)


_worker_anzahl = 0


def _worker_start(soll):
    """Worker nur hochfahren (laufende Threads sanft auslaufen zu lassen wäre
    komplex — überzählige Worker finden schlicht keine Arbeit mehr)."""
    global _worker_anzahl
    while _worker_anzahl < soll:
        threading.Thread(target=worker_schleife, daemon=True).start()
        _worker_anzahl += 1


def _sag(text):
    """Konsolen-Ausgabe, die auch unter pythonw (kein stdout) nicht abstürzt."""
    try:
        if sys.stdout is not None:
            print(text)
    except (OSError, ValueError, AttributeError):
        pass


def update_lauf(icon=None):
    """Update suchen, verifiziert laden, tauschen, neu starten (JB-Release-Standard).
    Meldet den Ausgang best-effort als Tray-Notiz + Log. Im Quellcode-Modus
    (nicht gefroren) bewusst deaktiviert — dort aktualisiert git."""
    def melde(text):
        _sag("Update: " + text)
        try:
            if icon:
                icon.notify(text, "SyncYouTube")
        except Exception:                            # noqa: BLE001 — Notiz ist nur Komfort
            pass
    exe = update.frozen_exe()
    if not exe:
        melde("Quellcode-Modus — Selbst-Update ist aus, bitte per git aktualisieren.")
        return
    try:
        info = update.check_release(__version__)
        if not info.get("available"):
            melde(f"Schon aktuell (v{__version__}).")
            return
        melde(f"Neue Version v{info['version']} — lade herunter …")
        neu = update.download_exe(info, os.path.dirname(exe))
        melde(f"v{info['version']} verifiziert — Neustart …")
        update.apply_exe_update(neu, exe)            # startet neu, kehrt nicht zurück
    except Exception as e:                           # noqa: BLE001 — alte Version läuft weiter
        melde("fehlgeschlagen, alte Version läuft weiter: " + _fehltext(e))


_tray_ref = []                                       # [icon] sobald der Tray läuft (für Notizen)


def _update_hintergrund():
    """Opt-in-Auto-Update (Standard AUS): kurz nach Start, danach täglich."""
    time.sleep(90)
    while True:
        if CFG.get("auto_update") and update.frozen_exe():
            try:
                update_lauf(_tray_ref[0] if _tray_ref else None)
            except Exception:                        # noqa: BLE001
                pass
        time.sleep(24 * 3600)


def _tray_icon(url):
    """Tray-Symbol mit Menü (Öffnen / Downloads-Ordner / Beenden). Gibt None
    zurück, falls pystray/Pillow fehlen — dann läuft die App ohne Tray weiter."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:                                # noqa: BLE001 — Tray ist optional
        return None
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((5, 5, 59, 59), fill=(20, 17, 15, 255))
    d.ellipse((5, 5, 59, 59), outline=(214, 119, 86, 255), width=4)
    d.rectangle((29, 17, 35, 34), fill=(214, 119, 86, 255))     # Download-Pfeil
    d.polygon([(32, 46), (19, 30), (45, 30)], fill=(214, 119, 86, 255))
    d.rectangle((21, 49, 43, 53), fill=(201, 149, 43, 255))

    def oeffnen(icon=None, item=None):
        webbrowser.open(url)

    def ordner(icon=None, item=None):
        subprocess.Popen(["explorer", ziel_ordner()])

    def beenden(icon=None, item=None):
        icon.stop()

    def erweiterung(icon=None, item=None):
        # Dezenter Weg zur Browser-Erweiterung (JB 13.07.: nicht übergriffig):
        # lokal vorhandene signierte .xpi direkt anbieten, sonst die Release-Seite.
        webbrowser.open(url + "/addon.xpi" if _addon_xpi_pfad()
                        else "https://github.com/schn4ppi/SyncYouTube/releases/latest")

    def updaten(icon=None, item=None):
        threading.Thread(target=update_lauf, args=(icon,), daemon=True).start()

    eintraege = [
        pystray.MenuItem("Öffnen", oeffnen, default=True),
        pystray.MenuItem("Downloads-Ordner", ordner),
        pystray.MenuItem("Browser-Erweiterung installieren…", erweiterung),
    ]
    if update.frozen_exe():                          # Quellcode-Modus: kein Selbst-Update
        eintraege.append(pystray.MenuItem("Nach Updates suchen…", updaten))
    eintraege.append(pystray.MenuItem("Beenden", beenden))
    menu = pystray.Menu(*eintraege)
    icon = pystray.Icon("ytdl", img, "YouTube-Downloader", menu)
    _tray_ref[:] = [icon]
    return icon


def main():
    sys.path.insert(0, SCRIPT_DIR)
    port = int(CFG.get("port", 8776))
    # Nur bei aktivierter Handy-Fernsteuerung im ganzen WLAN lauschen, sonst strikt
    # nur auf dem eigenen PC (Sicherheits-Standard der Suite: 127.0.0.1).
    host = "0.0.0.0" if CFG.get("fernsteuerung") else "127.0.0.1"
    url = f"http://127.0.0.1:{port}"
    # Einzel-Instanz: läuft schon eine? Dann nur den Browser öffnen und beenden,
    # statt einen zweiten Prozess (und ggf. ein Fenster) zu hinterlassen.
    # WICHTIG (JB-Fund 14.07.2026): der Bind-Fehler ist auf Windows KEIN verlässlicher
    # Wächter — HTTPServer setzt SO_REUSEADDR, ein zweiter Bind auf denselben Port
    # GELINGT dort einfach (zwei Server, Anfragen landen zufällig). Deshalb AKTIV
    # anklopfen: antwortet schon jemand auf dem Port, nur den Browser öffnen.
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            laeuft = True
    except OSError:
        laeuft = False
    if laeuft:
        _sag("Läuft bereits — öffne nur den Browser.")
        if "--no-browser" not in sys.argv:
            webbrowser.open(url)
        return
    try:
        srv = ThreadingHTTPServer((host, port), Handler)
    except OSError:
        _sag("Läuft bereits — öffne nur den Browser.")
        if "--no-browser" not in sys.argv:
            webbrowser.open(url)
        return
    _worker_start(max(1, min(3, int(CFG.get("parallel", 1)))))
    threading.Thread(target=ticker_schleife, daemon=True).start()
    threading.Thread(target=technik_backfill, daemon=True).start()   # Codecs für Alt-Dateien
    threading.Thread(target=_abos_hintergrund, daemon=True).start()  # Abos auf neue Videos prüfen
    threading.Thread(target=_einsortieren_hintergrund, daemon=True).start()  # verschobene Dateien zurücksortieren
    update.cleanup_old_exe()                                          # Reste früherer Selbst-Updates
    threading.Thread(target=_update_hintergrund, daemon=True).start()  # Opt-in-Auto-Update (Standard aus)
    _sag(f"YouTube-Downloader läuft: {url}")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    # Eigenes Tray-Symbol NUR in der Standalone-exe (JB 14.07.2026: „nur für die
    # Standalone-Version") — im Suite-Betrieb (Quellcode) läuft die App unsichtbar,
    # gesteuert über Dashboard + SyncDashTray-Tray (Öffnen /yt, Beenden /api/beenden).
    # --tray erzwingt das Symbol (Debug), --no-tray unterdrückt es auch in der exe.
    tray_gewollt = getattr(sys, "frozen", False) or "--tray" in sys.argv
    tray = _tray_icon(url) if (tray_gewollt and "--no-tray" not in sys.argv) else None
    if tray is not None:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            tray.run()                               # blockiert bis „Beenden"
        except Exception:                            # noqa: BLE001 — Fallback ohne Tray
            _sag("Tray nicht verfügbar — laufe weiter im Vordergrund.")
            srv.serve_forever()
        Q.speichern()
        _sag("Beendet — Warteschlange gespeichert.")
        return

    try:
        srv.serve_forever()                          # endet auch via POST /api/beenden
    except KeyboardInterrupt:
        pass
    Q.speichern()
    _sag("Beendet — Warteschlange gespeichert.")


if __name__ == "__main__":
    main()
