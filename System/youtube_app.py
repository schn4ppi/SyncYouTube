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
import contextlib
import glob
import hashlib
import hmac
import json
import logging
import logging.handlers
import math
import mimetypes
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode, urlparse, urlsplit, parse_qs, parse_qsl

import cookie_kopie         # Firefox-Cookies samt WAL für yt-dlp (Lehre aus SyncFindus, 24.09.2026)
import familie as fam       # gemeinsamer Kern: atomares Schreiben mit Wiederholung (F5)
import geo
import links                # reine Link-Deutung (Gesamtprüfung Y2); die App ruft links.X
import medien_smtc          # Windows-Medienanmeldung des VLC-Motors (pywinrt erst bei Bedarf)
import musik_einstufung     # Musik-Einstufung und Titel-Helfer (Gesamtprüfung Y3); die App ruft musik_einstufung.X
import update
import windows_kennung      # App-Kennung JBK.SyncYouTube + Startmenü-Eintrag (JB 24.09.2026)
# Verweise für Aufrufer von außen (Tests, Werkzeuge): app.X bleibt erreichbar.
# Die App selbst ruft modul.X (links.X, musik_einstufung.X); ein Test ersetzt
# nur modul.X (Wächter tests/test_struktur_module.py).
from links import (  # noqa: F401
    YOUTUBE_HOSTS, _KANAL_UNTERSEITEN, _KANAL_WURZEL, _KEIN_LINK_ZEICHEN,
    _ist_mix, _kanal_url, _liste_zuschneiden, _mix_limit,
    _plausible_id, _video_id, ist_einzelvideo, ist_youtube_link,
    link_deuten, link_zeilen)
from musik_einstufung import (  # noqa: F401
    AUDIO_EXT, AUDIO_EXT_OHNE_AAC, AUDIO_EXT_OHNE_WAV_AAC, MUSIKVIDEO_EXT,
    VIDEO_EXT, _ANHAENGSEL, _KEIN_LIED, _LIED_MAXDAUER,
    _TITEL_MUELL, _ist_live_titel, _ist_musik, _ist_musik_muster,
    _kanal_nummern, _kat_aus_name, _musik_grad, _musik_grade,
    _tag_kandidat, _titel_aus_name, _titel_blank, _titel_kern)

__version__ = "1.2.7"

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


def _daten_dir(argv, env):
    """Testmodus-Weiche (JB: „Testmodus, der Proben außerhalb JBs echter
    Ordner fährt"). Vorfall 23.07.: ein Auto-Import-Test legte eine Probedatei
    in Downloads/ — Datei, DB-Eintrag und ein Warteschlangen-Auftrag mit
    erfundener Adresse blieben JB sichtbar. Jetzt technisch verhindert:
    `--testmodus [pfad]` legt ALLE Zustandsdateien (Config, DB, Warteschlange,
    Playlists, Abos, Logs, Downloads) in einen Wegwerf-Ordner. Code (bin/,
    browser-addon, .py-Signatur des Selbst-Neustarts) bleibt am SCRIPT_DIR."""
    if "--testmodus" in argv:
        i = argv.index("--testmodus")
        pfad = (argv[i + 1] if i + 1 < len(argv)
                and not argv[i + 1].startswith("--") else "")
        if not pfad:
            pfad = os.path.join(env.get("TEMP") or env.get("TMP") or SCRIPT_DIR,
                                "ytdl-testmodus")
        os.makedirs(pfad, exist_ok=True)
        return os.path.abspath(pfad), True
    return SCRIPT_DIR, False


# Produktiv-Ports der Familie (CLAUDE.md): 8776 YouTube · 8778 Docs · 8779 Findus ·
# 8780 Findus-Gast · 8781 ReelWerkstatt. Der Probe-Port liegt bewusst darüber.
TESTMODUS_PORT = 8790


def _testmodus_config(cfg, daten_dir):
    """Im Testmodus erzwingen: eigener Port AUSSERHALB der Produktiv-Spanne
    8776–8781 (8776 ist JBs SyncYouTube, 8779 seit 08.08. SyncFindus — der
    alte Wert 8779 kollidierte damit, Befund 06.09.2026),
    Downloads im Probenordner, Selbst-Neustart AUS (eine Probe soll sich nicht
    selbst neu starten und dabei ihre Argumente verlieren) und Selbst-Update
    AUS: seit dessen Vorgabe AN ist (08.09.2026), würde eine Probe sonst die
    echte exe herunterladen und tauschen."""
    cfg["port"] = TESTMODUS_PORT
    cfg["ziel_ordner"] = os.path.join(daten_dir, "Downloads")
    cfg["auto_neustart"] = False
    cfg["auto_update"] = False                        # eine Probe tauscht NIE eine exe
    cfg["fernsteuerung"] = False                      # Probe lauscht NIE im WLAN
    return cfg


DATEN_DIR, TESTMODUS = _daten_dir(sys.argv, os.environ)
CONFIG_PFAD = os.path.join(DATEN_DIR, "config.json")
QUEUE_PFAD = os.path.join(DATEN_DIR, "warteschlange.json")
GELADEN_PFAD = os.path.join(DATEN_DIR, "geladen_log.json")  # „Datenbank" fertiger Downloads
PLAYLIST_PFAD = os.path.join(DATEN_DIR, "playlists.json")
STATUS_PFAD = os.path.join(DATEN_DIR, "yt_status.json")   # fürs Dashboard (read-only Konsument)
# Film-Fundament (Doku/SYNC_FILME_SPEC.md): eigenes Modul, Einbahn-Regel wie
# geo/vpn — filme importiert NIE youtube_app. Braucht DATEN_DIR (Testmodus!).
import filme                                              # noqa: E402
filme.einrichten(DATEN_DIR)
# Teilprojekt 3 (Profile + Geräte): gleiche Bauform. Bewusst NICHT
# "profile.py" — das würde das stdlib-Modul profile (Profiler) überschatten.
import profil_geraete                                     # noqa: E402
profil_geraete.einrichten(DATEN_DIR)
import live_tv                                            # noqa: E402
live_tv.einrichten(DATEN_DIR)
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
# deno fragt sonst einmal am Tag im Netz nach einer neuen Version; yt-dlp
# startet es als Kindprozess, der die Variable erbt (Gesamtprüfung Gruppe 6).
# Eine eigene Wahl in der Umgebung bleibt stehen.
os.environ.setdefault("DENO_NO_UPDATE_CHECK", "1")

STANDARD_CONFIG = {
    "port": 8776,
    "ziel_ordner": "",              # leer = YouTube/Downloads
    # JB-Entscheid 08.09.2026, ZWEITE Fassung: Vorgabe bleibt „firefox“.
    # Kurz stand hier „keine“ (Gedanke: ohne Cookies hängt das YouTube-Konto an
    # keinem Abruf). JB hat das noch am selben Abend zurückgenommen — *„das
    # Risiko ist zu groß“* — und die eigene Messung gibt ihm recht: ohne
    # Cookies wählt yt-dlp die nicht angemeldeten Vorgabe-Zugangswege, also
    # genau die, gegen die YouTube sperrt (siehe `_ist_sperre`, 403-Runde
    # 07.09.2026). Cookies-aus hätte Sperren eher wahrscheinlicher gemacht
    # statt seltener, und nebenbei Premium-Qualität und altersbeschränkte
    # Videos gekostet. NICHT ohne neue Messung erneut umdrehen.
    # Werte: firefox | chrome | edge | keine
    "cookies_browser": "firefox",
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
    # JB-Entscheid 08.09.2026: Vorgabe ist AN. Die verteilte exe fiel bei
    # Mitnutzern aus, weil eine alte Fassung liegen blieb; ein Programm, das
    # sich selbst aktuell hält, ist der einzige Weg dagegen, der ohne den
    # Nutzer auskommt. Wirkt nur in der gepackten exe (im Quellcode-Modus
    # aktualisiert git), tauscht nur im Leerlauf, prüft Größe + SHA256.
    "auto_update": True,
    # Selbst-Neustart, wenn sich der Quellcode ändert (nur im Leerlauf). Stand
    # bis 25.09.2026 nicht hier, also warf `config_laden` den Schlüssel weg und
    # der Neustart ließ sich per config.json nicht abschalten (Gesamtprüfung F16).
    "auto_neustart": True,
    # GEMESSEN 08.09.2026: Diese fünf Schlüssel schreibt das Programm selbst in
    # config.json, aber sie standen NICHT hier — und `config_laden` behält nur,
    # was hier steht. Also gingen sie bei JEDEM Neustart verloren: das gewählte
    # Namensschema, das Auto-Umbenennen, die Untertitel-Sprachen, die global
    # gemerkte Untertitel-Größe und der Merker der Untertitel-Altlast — weshalb
    # `wiedergabe_sub_altlast_raeumen` bei jedem Start erneut lief und dabei
    # config.json neu schrieb. Ein Schlüssel, den das Programm schreibt, gehört
    # in die Vorgaben; sonst ist er eine Einstellung ohne Gedächtnis.
    "name_schema": [],              # Namens-Baukasten (leer = NAME_STANDARD)
    "auto_umbenennen": False,       # Alt-Dateien beim Lauf mit umbenennen
    "untertitel_sprachen": [],      # leer = die Vorauswahl der Oberfläche
    "wiedergabe": {},               # Wiedergabe-Regeln (Untertitel-Größe/-Stil, je Titel)
    "wg_sub_migriert": False,       # Untertitel-Altlast einmalig geräumt?
    # Stand der ausgelieferten Vorgaben. Wird VORGABEN_STAND hochgezählt, zieht
    # `_vorgaben_nachziehen` die neuen Werte EINMALIG auch in eine bestehende
    # config.json nach — sonst erreicht eine Entscheidung nur Neuinstallationen,
    # und genau die brauchen sie am wenigsten.
    "vorgaben_stand": 0,
    # Build 127 (JB): Die Link-Rückfrage wird IMMER gestellt — „diese Abfrage
    # ist meiner Meinung nach immer relevant". Ob man einen Kanal abonniert
    # oder lädt, hängt am Kanal, nicht an einer Voreinstellung; eine gemerkte
    # Antwort wäre hier eine Falle statt Komfort. Deshalb gibt es dafür
    # bewusst KEINE Config-Schlüssel (mehr).
}


def ist_loopback(ip):
    """Kommt eine Anfrage vom eigenen Rechner? 127.0.0.0/8 und ::1, auch als
    IPv4 in IPv6 (::ffff:127.0.0.1). Die EINE Schreibweise für alle Riegel
    (Gesamtprüfung S10, 25.09.2026): vorher wiesen sechs Stellen mit
    `client_address != "127.0.0.1"` den PC ab, wenn er über ::1 kam."""
    import ipaddress
    try:
        adresse = ipaddress.ip_address(str(ip or "").split("%")[0])
    except ValueError:
        return False
    if getattr(adresse, "ipv4_mapped", None):
        adresse = adresse.ipv4_mapped
    return adresse.is_loopback


# Fernsteuerungs-Code (JB-Entscheid 7a Punkt 3, 25.09.2026): neue Codes haben 10
# Zeichen aus einem gut lesbaren Alphabet (ohne 0/O und 1/I/L), gut 49 Bit
# statt 24 (vorher 6 Hex-Zeichen). Ein vorhandener Code bleibt gültig, bis JB am
# PC „Code erneuern“ klickt; kein Zwangswechsel beim Update.
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LAENGE = 10


def neuer_fernsteuerungs_code():
    import secrets
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LAENGE))


def zugriff_erlaubt(client_ip, aktiv, code_soll, code_ist):
    """Wer darf auf die App zugreifen? Der eigene PC (localhost) IMMER. Aus dem
    Heim-WLAN NUR, wenn die Fernsteuerung an ist UND der Zugangscode stimmt.
    (Sicherheits-Kern der Handy-Fernsteuerung — bewusst als reine Funktion testbar.)"""
    if client_ip == "localhost" or ist_loopback(client_ip):
        return True
    if not aktiv:
        return False
    # Zeitkonstant verglichen (S7): die Antwortzeit verrät keine Präfixe.
    return bool(code_soll) and hmac.compare_digest(str(code_ist or "").encode("utf-8"),
                                                   str(code_soll).encode("utf-8"))


# Versuchsbremse je Client-IP (Gesamtprüfung S7, 25.09.2026) für Fernsteuerungs-
# Code und Geräte-Token: ab dem zehnten Fehlversuch sperrt sie 1 s, dann je
# weiterem Versuch doppelt so lange, höchstens 15 Minuten. Während einer Sperre
# wird nichts geprüft und nichts gezählt; ein Erfolg setzt zurück. Der PC selbst
# (Loopback) läuft nie hinein. Anfragen OHNE Zugangsdaten zählen nicht: sie
# können nichts erraten, und die PC-Seite auf einem gekoppelten Gerät schickt
# solche in Serie (F9).
# Nacharbeit 25.09.: Prüfen und Belegen geschehen in EINEM Sperrabschnitt
# (_bremse_versuch). Gleichzeitig laufen höchstens so viele Vergleiche, wie
# bis zur nächsten Sperre noch frei sind: vor dem zehnten Fehlversuch zusammen
# höchstens zehn, danach genau einer je Sperrfenster. Wer darüber hinaus
# kommt, wartet kurz auf einen laufenden Vergleich statt abzuprallen; ein
# gekoppeltes Gerät mit vielen parallelen Anfragen wird so nie abgewiesen.
BREMSE_AB = 10
BREMSE_MAX_S = 15 * 60
BREMSE_WARTEN_S = 10                 # so lange wartet ein Versuch höchstens auf einen freien Platz
_fehlversuche = {}                   # ip -> {"n": Fehlversuche, "bis": gesperrt bis, "ts": letzter,
#                                            "laufend": gerade laufende Vergleiche}
_fehlversuche_lock = threading.Lock()
_bremse_frei = threading.Condition(_fehlversuche_lock)
_bremse_uhr = time.monotonic


def _bremse_wartezeit(n):
    """Sperrdauer in Sekunden nach n Fehlversuchen in Folge."""
    if n < BREMSE_AB:
        return 0
    return min(BREMSE_MAX_S, 2 ** min(n - BREMSE_AB, 20))


def _bremse_gesperrt(ip):
    with _fehlversuche_lock:
        e = _fehlversuche.get(ip)
        return bool(e) and _bremse_uhr() < e["bis"]


def _bremse_versuch(ip):
    """True = dieser Versuch darf vergleichen; danach MUSS genau eines von
    _bremse_erfolg, _bremse_fehlversuch oder _bremse_freigeben folgen.
    False = gesperrt (oder nach BREMSE_WARTEN_S kein Platz frei); dann wird
    weder verglichen noch gezählt."""
    frist = time.monotonic() + BREMSE_WARTEN_S
    with _bremse_frei:
        while True:
            e = _fehlversuche.get(ip)
            if e and _bremse_uhr() < e["bis"]:
                return False
            n, laufend = (e["n"], e["laufend"]) if e else (0, 0)
            if laufend == 0 or n + laufend < BREMSE_AB:
                if e is None:
                    e = _fehlversuche[ip] = {"n": 0, "bis": 0.0, "ts": _bremse_uhr(), "laufend": 0}
                e["laufend"] += 1
                return True
            rest = frist - time.monotonic()
            if rest <= 0:
                return False
            _bremse_frei.wait(rest)


def _bremse_abschliessen(ip, fehlversuch):
    """Einen belegten Versuch freigeben; im Sperrabschnitt gerufen."""
    jetzt = _bremse_uhr()
    e = _fehlversuche.setdefault(ip, {"n": 0, "bis": 0.0, "ts": jetzt, "laufend": 0})
    e["laufend"] = max(0, e["laufend"] - 1)
    if fehlversuch is True:
        e["n"] += 1
        e["ts"] = jetzt
        e["bis"] = jetzt + _bremse_wartezeit(e["n"])
    elif fehlversuch is False:                       # Erfolg setzt zurück
        e["n"], e["bis"] = 0, 0.0
    if e["n"] == 0 and e["laufend"] == 0:
        del _fehlversuche[ip]
    _bremse_frei.notify_all()


def _bremse_fehlversuch(ip):
    with _bremse_frei:
        jetzt = _bremse_uhr()
        if len(_fehlversuche) > 1024:                  # Deckel: lange Ruhende fallen weg
            for alt in [k for k, v in _fehlversuche.items()
                        if not v["laufend"] and v["bis"] <= jetzt
                        and jetzt - v["ts"] > 4 * BREMSE_MAX_S]:
                del _fehlversuche[alt]
        _bremse_abschliessen(ip, True)


def _bremse_erfolg(ip):
    with _bremse_frei:
        _bremse_abschliessen(ip, False)


def _bremse_freigeben(ip):
    """Vergleich ohne Ergebnis (Ausnahme): Platz frei, nichts gezählt."""
    with _bremse_frei:
        _bremse_abschliessen(ip, None)

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

# Fehler, hinter denen YouTube uns AKTIV aussperrt: Bot-Verdacht, Drossel,
# HTTP 403/429. Befund 07.09.2026: Diese Faelle standen in KEINER Liste, also
# lief ein gesperrter Eintrag bis zu max_wiederholungen (Vorgabe 10) erneut
# gegen YouTube — aus einer weichen Drossel wurde so eine harte Sperre, weil
# jeder Neuversuch das Muster bestaetigt. Ein Treffer heisst deshalb: nicht
# wiederholen, Grund festhalten (Leitplanke P10 »fremde Dienste bremsen«).
SPERRE = ("not a bot", "rate-limited", "rate limited", "too many requests",
          "forbidden", "captcha", "http error 403", "http error 429")

# Nackte Statuszahlen nur mit Wortgrenze: in einer Video-Kennung wie
# "dQw403abcXY" steckt "403" ohne jede Bedeutung (Leitplanke P8 — ein Treffer
# zaehlt nur mit Ort und Wortgrenze).
_SPERRE_ZAHL = re.compile(r"(?<![0-9a-z])(403|429)(?![0-9a-z])")

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
# EINE Sperre für config.json (Gesamtprüfung F5): vorher schrieben die
# Einstellungen unter Q.lock, die Wiedergabe-Regeln unter _io_lock und die
# Altlast-Räumung ohne Sperre. Wer CFG ändert oder speichert, hält _cfg_lock.
_cfg_lock = threading.RLock()


class _LaeuftSchon:
    """„Läuft schon“-Merker, der Prüfen und Setzen in EINEM Schritt macht
    (Gesamtprüfung, Doppelungen App-Kern). Vorher standen sechs Merker ohne
    Sperre da: `if x_laeuft: return` und `x_laeuft = True` waren zwei Schritte,
    und zwei Anstöße im selben Augenblick liefen beide los."""

    def __init__(self):
        self._lock = threading.Lock()
        self.laeuft = False

    def starten(self):
        """True: dieser Aufrufer darf laufen (und MUSS danach `fertig()` rufen)."""
        with self._lock:
            if self.laeuft:
                return False
            self.laeuft = True
            return True

    def fertig(self):
        with self._lock:
            self.laeuft = False


def _zustand_starten(zustand, lock, **felder):
    """Dasselbe für ein Zustands-Dict, das die Oberfläche liest (`_geo_test`):
    Prüfen und Setzen von zustand["laeuft"] unter `lock`. `autotag_lauf` macht
    es mit eigener Sperre, weil es dabei Nachzuholendes merkt (F8)."""
    with lock:
        if zustand.get("laeuft"):
            return False
        zustand.update(felder)
        zustand["laeuft"] = True
        return True


_SPERR_FEHLER = (32, 33)                             # ERROR_SHARING_VIOLATION, ERROR_LOCK_VIOLATION


def _voruebergehend_gesperrt(e):
    """Hält gerade ein anderes Programm die Datei (Virenscanner, Sicherung, das
    Dashboard)? Unter Windows kommt das als PermissionError [WinError 32/33]."""
    return isinstance(e, PermissionError) or getattr(e, "winerror", None) in _SPERR_FEHLER


def _json_laden(pfad, fallback):
    """JSON lesen; eine kaputte Datei wandert nach `<pfad>.<Zeitstempel>.defekt`
    und es gilt `fallback`. Ein Sperr-Fehler ist kein Defekt (Gesamtprüfung
    Gruppe 6): dann wird knapp 1 s lang erneut gelesen, erst danach gilt die
    Datei als unlesbar. Vorher legte schon eine kurze fremde Sperre die leere
    Vorgabe an, die das nächste Speichern über die echte Datei schrieb."""
    for versuch in range(10):
        try:
            with open(pfad, encoding="utf-8") as f:
                return json.load(f)
        except OSError as e:
            if _voruebergehend_gesperrt(e) and versuch < 9:
                time.sleep(0.05 * (versuch + 1) if versuch < 5 else 0.05)
                continue
        except ValueError:
            pass
        break
    # kaputte Datei nie verlieren (Suite-Regel: nicht-destruktiv)
    if os.path.exists(pfad):
        _defekt_beiseite(pfad)
    return fallback


def _defekt_beiseite(pfad):
    """Rettungskopie `<pfad>.<Zeitstempel>.defekt`, nie über eine vorhandene
    (Gesamtprüfung F15): vorher hieß sie immer `<pfad>.defekt`, und ein zweiter
    Defekt überschrieb die erste Kopie. `os.rename` ersetzt unter Windows kein
    vorhandenes Ziel; bei gleichem Zeitstempel zählt ein Zusatz hoch."""
    stempel = time.strftime("%Y%m%d-%H%M%S")
    for n in range(1, 100):
        ziel = f"{pfad}.{stempel}{'' if n == 1 else '-' + str(n)}.defekt"
        if os.path.exists(ziel):
            continue
        try:
            os.rename(pfad, ziel)
            return ziel
        except FileExistsError:
            continue
        except OSError:
            return None
    return None


def _json_speichern(pfad, daten):
    """Atomar schreiben über `familie.json_schreiben` (Gesamtprüfung F5): eigener
    tmp-Name je Faden und ein kurzer Wiederholungs-Anlauf, solange ein Leser die
    Zieldatei offen hat. Vorher teilten sich alle Schreiber `<pfad>.tmp` und
    gaben beim ersten Freigabekonflikt auf. Der Vertrag bleibt: Scheitert das
    Schreiben, kommt ein OSError."""
    if not fam.json_schreiben(pfad, daten):
        raise OSError(f"{os.path.basename(pfad)} ließ sich nicht schreiben")


def _cfg_speichern():
    """config.json schreiben — unter _cfg_lock, wie jede Änderung an CFG."""
    with _cfg_lock:
        _json_speichern(CONFIG_PFAD, CFG)


# Stand der ausgelieferten Vorgaben — hochzählen, wenn eine Vorgabe sich ändert.
VORGABEN_STAND = 1

# (Schlüssel, bisher ausgelieferter Wert, neuer Wert). Umgestellt wird NUR dort,
# wo noch der alte Auslieferungswert steht — wer `auto_update` bewusst
# ausgeschaltet hat, behält es ausgeschaltet.
#
# Hier stand kurz auch `("cookies_browser", "firefox", "keine")`. JB hat das
# noch vor der ersten Ausführung zurückgenommen; gemessen war zu dem Zeitpunkt
# KEINE einzige Installation umgestellt — JBs config.json trug weder den neuen
# Wert noch `vorgaben_stand`, und das veröffentlichte Release ist älter als die
# Änderung. Deshalb genügt das Entfernen des Eintrags; ein Rück-Umstellungs-
# Schritt wäre ein Heilmittel gegen einen Schaden, den es nie gab.
VORGABEN_UMSTELLUNG = (
    ("auto_update", False, True),               # JB-Entscheid 08.09.2026
)

# Was die Umstellung in DIESEM Lauf geändert hat — main() schreibt es fest
# (mit Sicherung davor) und sagt es dem Nutzer.
VORGABEN_NEU = []

# Der GELESENE Stand der config.json, bevor irgendetwas daran geändert wurde.
# GEMESSEN 08.09.2026 an einem echten Probelauf: eine Sicherung, die in main()
# einfach die Datei kopiert, kommt zu SPÄT — `wiedergabe_sub_altlast_raeumen`
# schreibt config.json direkt beim Start, also enthielt der „Rückweg“ schon die
# neuen Werte. Ein Rückweg, der nur so heißt, ist schlimmer als keiner.
VORGABEN_ROH = {}


def _vorgaben_nachziehen(cfg, roh):
    """Neue Vorgaben EINMALIG auch in eine bestehende config.json nachziehen.

    Ohne das erreicht eine Entscheidung nur Neuinstallationen: `config_laden`
    lässt die Datei gewinnen, und eine Datei hat wirklich jeder — das Programm
    schreibt sie beim Start selbst. GEMESSEN am 08.09.2026 an JBs eigener
    config.json: dort stand `auto_update: false`, die gedrehte Vorgabe hätte
    also nicht einmal seinen eigenen PC erreicht. Am selben Abend um 20:12
    hat der Tray das Programm normal gestartet und die Umstellung ist dort
    live gelaufen — `auto_update` false → true, alles andere unangetastet.

    Drei Zusagen:
      * Sie greift genau einmal — danach steht `vorgaben_stand` in der Datei.
      * Sie überfährt keine bewusste Wahl: umgestellt wird nur, wo noch exakt
        der alte Auslieferungswert steht.
      * Sie hat einen Rückweg: main() legt die alte Datei daneben, bevor der
        neue Stand geschrieben wird (JB-Regel: kein Verlust ohne Rückweg).

    Ehrlich dazu: „nie angefasst“ und „bewusst auf den alten Wert gestellt“
    sind in einer alten Datei nicht unterscheidbar. Dafür gibt es den Rückweg
    und die Meldung — nicht, weil die Unterscheidung gelänge.
    """
    if not roh:                                       # frische Installation
        return VORGABEN_STAND
    stand = roh.get("vorgaben_stand")
    stand = stand if isinstance(stand, int) else 0
    if stand >= VORGABEN_STAND:
        return stand
    for schluessel, alt, neu in VORGABEN_UMSTELLUNG:
        if roh.get(schluessel) == alt:
            cfg[schluessel] = neu
            VORGABEN_NEU.append((schluessel, alt, neu))
    if VORGABEN_NEU:
        VORGABEN_ROH.clear()
        VORGABEN_ROH.update(roh)                      # der Stand VOR allem
    return VORGABEN_STAND


def config_laden():
    cfg = dict(STANDARD_CONFIG)
    roh = _json_laden(CONFIG_PFAD, {})
    cfg.update({k: v for k, v in roh.items() if k in STANDARD_CONFIG})
    cfg["vorgaben_stand"] = _vorgaben_nachziehen(cfg, roh)
    if TESTMODUS:                                     # Probe: eigener Port, eigene Downloads,
        _testmodus_config(cfg, DATEN_DIR)             # kein Selbst-Neustart, kein WLAN
    return cfg


def vorgaben_umstellung_festschreiben():
    """Die Umstellung in die Datei schreiben — mit Sicherungskopie davor.

    Läuft erst in main(), nachdem der Einzel-Instanz-Riegel bestanden ist: eine
    zweite Instanz, die sich gleich wieder beendet, darf die Datei des laufenden
    Programms nicht anfassen. Gesichert wird der GELESENE Stand (`VORGABEN_ROH`),
    nicht die Datei — die ist zu diesem Zeitpunkt längst neu geschrieben. Lässt
    sich die Sicherung nicht anlegen, wird NICHT umgestellt."""
    # Nur melden, was am Ende WIRKLICH so in CFG steht. Im Testmodus setzt
    # `_testmodus_config` auto_update danach wieder auf False - eine Meldung
    # "auto_update False -> True" waere dort schlicht unwahr.
    geaendert = [(s, a, n) for s, a, n in VORGABEN_NEU if CFG.get(s) == n]
    if not geaendert:
        return []
    sicherung = os.path.join(DATEN_DIR, "config_vor_stand%d.json" % VORGABEN_STAND)
    if not os.path.exists(sicherung):
        try:
            _json_speichern(sicherung, VORGABEN_ROH)
        except OSError:                               # noqa: BLE001 — lieber nicht umstellen
            return []                                 # als ohne Rückweg umstellen
    _cfg_speichern()
    return geaendert


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
            # Nach Neustart: was lief, wird wieder eingereiht -> Resume via .part.
            # Build 137: „prueft" gehört genauso dazu. Ein Eintrag, der beim
            # Beenden gerade AUFGELÖST wurde, blieb sonst für immer liegen —
            # Q.naechster() greift nur „wartend" auf, also rührte ihn nie
            # wieder jemand an. Das war einer von JBs toten Aufträgen.
            if it.get("status") in ("laeuft", "prueft"):
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
    # Testmodus: JEDER Fallback landet im Probenordner — nie in JBs Downloads
    # (der Fallback war sonst genau das Loch, durch das die Probedatei kam).
    basis = DATEN_DIR if TESTMODUS else PROGRAMM_DIR
    pfad = CFG.get("ziel_ordner") or os.path.join(basis, "Downloads")
    try:
        os.makedirs(pfad, exist_ok=True)
    except OSError:
        pfad = os.path.join(basis, "Downloads")
        os.makedirs(pfad, exist_ok=True)
    return pfad


def _ffmpeg_ordner():
    """Der ORDNER, in dem ffmpeg.exe liegt — genau das erwartet yt-dlp als
    `ffmpeg_location`. Rückgabe None, wenn ffmpeg fehlt."""
    exe = os.path.join(BIN_DIR, "ffmpeg.exe")
    return BIN_DIR if os.path.exists(exe) else None


def _ffmpeg_exe():
    """Das PROGRAMM selbst — für alles, was ffmpeg startet (subprocess).

    Bewusst getrennt von `_ffmpeg_ordner()`: Der frühere gemeinsame Name
    `_ffmpeg_pfad()` beantwortete zwei verschiedene Fragen („wo liegt es?" und
    „womit starte ich es?") und wurde genau einmal falsch verstanden — die
    Transcode-Weiche übergab den Ordner als Programm an Popen und starb mit
    `WinError 5: Zugriff verweigert`. Gemessen 13.08.2026 gegen Renés echte
    Bibliothek: 18 von 20 Titeln (AC3/E-AC3/DTS/HEVC) brauchen den Transcode,
    der Fehler traf also fast jeden Film im Browser-Player. Ein Name, eine
    Frage (Lehrbuch L20)."""
    exe = os.path.join(BIN_DIR, "ffmpeg.exe")
    return exe if os.path.exists(exe) else None


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
    if not pfad or not os.path.exists(pfad) or not _ffmpeg_exe():
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
    if not pfad or not os.path.isfile(pfad) or not _ffmpeg_exe():
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
    """Untertitel-Dateien (stem.<lang>.vtt/.srt) mit der Mediendatei mitnehmen.
    Auch .srt: yt-dlp liefert je nach Quelle SubRip — genau so verwaiste ein
    Grim-Dawn-Untertitel beim Verschieben (JB-Fund, 05.08.)."""
    alt_stem = os.path.splitext(alt)[0]
    neu_stem = os.path.splitext(neu)[0]
    for f in (glob.glob(glob.escape(alt_stem) + ".*.vtt")
              + glob.glob(glob.escape(alt_stem) + ".*.srt")):
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
        # Gegen YouTube bremste bisher NICHTS, waehrend fuer MusicBrainz an
        # sieben Stellen sorgfaeltig pausiert wird (Befund 07.09.2026). Ein
        # ungebremster Abruf-Sturm ist genau das Muster, das YouTube mit 429
        # und der Bot-Abfrage beantwortet. Die Drossel steht deshalb NICHT hier,
        # sondern in DROSSEL und wird nur vom Download-Weg gesetzt (siehe unten).
    }
    ff = _ffmpeg_ordner()
    if ff:
        opts["ffmpeg_location"] = ff
    # Zweiter Vorgabewert: greift, wenn CFG den Schlüssel gar nicht kennt.
    # Er muss dasselbe sagen wie STANDARD_CONFIG, sonst hätte das Programm zwei
    # Wahrheiten über seine eigene Vorgabe (Befund 08.09.2026) — der Wächter
    # `test_es_gibt_nur_eine_wahrheit_ueber_die_cookie_vorgabe` misst das.
    browser = CFG.get("cookies_browser", "firefox")
    if mit_cookies and browser and browser != "keine":
        opts["cookiesfrombrowser"] = (browser,)
    return opts


@contextlib.contextmanager
def _ydl(opts):
    """`yt_dlp.YoutubeDL(opts)` — die Firefox-Cookies dabei aus einer Kopie SAMT WAL.

    yt-dlp kopiert beim Lesen der Firefox-Cookies nur `cookies.sqlite`, nicht das
    `-wal` (gemessen an 2026.08.19); frische Anmelde-Cookies stehen aber noch
    dort. `cookie_kopie` legt deshalb vorher eine vollständige Kopie in einen
    eigenen Ordner, und yt-dlp bekommt dessen Pfad als Firefox-Profil. Scheitert
    das, geht `opts` UNVERÄNDERT weiter — der heutige Weg.

    Die Kopie lebt so lange wie der YoutubeDL (er liest die Cookies erst beim
    ersten Abruf) und ist danach weg. Die Optionen des Aufrufers bleiben
    unberührt: Seine Cookie-Heilung wirft danach weiter `("firefox",)` aus
    SEINEM Dict. Jeder YoutubeDL der Programm-Dateien entsteht hier
    (Wächter `tests/test_cookies_wal.py`).
    """
    import yt_dlp
    with cookie_kopie.firefox_profil(opts.get("cookiesfrombrowser")) as profil:
        if profil:
            opts = dict(opts, cookiesfrombrowser=("firefox", profil))
        with yt_dlp.YoutubeDL(opts) as ydl:
            yield ydl


# Massvolle Drossel nach Leitplanke P10 — NUR fuer den Download-Weg.
#
# Sie stand zuerst in `_ydl_basis_opts` und wirkte damit auf alle sechs Aufrufer:
# `aufloesen`, `untertitel_nachladen`, `_abo_flach`, `_enrich_eintrag` und
# `_zugang_ok`. yt-dlp schlaeft bei `sleep_interval_requests` vor JEDER
# Extraktions-Anfrage — die eine Sekunde haette also auch die Wege gebremst, bei
# denen JB vor dem Bildschirm auf eine Antwort wartet (Abnahme-Mangel 07.09.2026).
# Wer YouTube in Serie belastet, ist der Download; dort gehoert die Bremse hin.
DROSSEL = {
    "sleep_interval": 2,            # 2-8 s Zufallspause vor jedem Video
    "max_sleep_interval": 8,
    "sleep_interval_requests": 1,   # 1 s zwischen den Abrufen EINER Aufloesung
}


def _ist_sperre(exc):
    """YouTube sperrt uns aus — Bot-Verdacht, Drossel, HTTP 403/429.

    Muss VOR `_ist_cookie_fehler` gefragt werden: YouTube haengt an jede
    Bot-Meldung den Satz »Use --cookies-from-browser …« an
    (`YoutubeIE._youtube_login_hint`). Der enthaelt »cookie« UND »browser«,
    also hielt die Cookie-Heilung die Sperre fuer ein Cookie-Problem, warf die
    Cookies weg und lief SOFORT nochmal los — ohne Cookies aber waehlt yt-dlp
    die nicht angemeldeten Vorgabe-Wege, also genau die, gegen die YouTube
    gerade sperrt. Die Selbstheilung fuehrte damit in die Wand
    (Befund 07.09.2026, Leitplanke P10).
    """
    t = str(exc).lower()
    return any(s in t for s in SPERRE) or bool(_SPERRE_ZAHL.search(t))


def _ist_cookie_fehler(exc):
    t = str(exc).lower()
    return "cookie" in t or "could not copy" in t or "decrypt" in t or "browser" in t


# Schutzschalter gegen YouTube-Sperren (Gesamtprüfung F4). Vorher warfen drei
# Nebenwege (Untertitel, Abo-Blick, Anreichern) bei JEDER Ausnahme die Cookies
# weg und fragten sofort erneut, ohne `_ist_sperre` und ohne Fehlereintrag;
# Anreichern, Abo-Prüfung und Entdecken liefen während einer Sperre einfach
# weiter. Jetzt setzt jede erkannte Sperre (Download, Auflösen, Nebenweg) den
# Zeitstempel „gesperrt bis“, und jede Serien-Schleife (Anreichern, Abo-Prüfung,
# Entdecken) liest ihn vor dem nächsten Abruf. Was JB einzeln anstößt (Abo
# anlegen, Kanal-Rückfrage, Backkatalog, Untertitel), fragt weiter: die Pause
# soll Serien bremsen, nicht JBs Klicks ins Leere laufen lassen (Nacharbeit F4).
SPERRE_PAUSE_S = 30 * 60
_youtube_gesperrt_bis = 0.0
_youtube_sperre_lock = threading.Lock()


def youtube_sperre_vermerken(exc):
    """Ist `exc` eine YouTube-Sperre, pausieren die Nebenwege SPERRE_PAUSE_S
    lang. True bei einer Sperre (erst `_ist_sperre`, dann der Zeitstempel)."""
    global _youtube_gesperrt_bis
    if not _ist_sperre(exc):
        return False
    with _youtube_sperre_lock:
        _youtube_gesperrt_bis = max(_youtube_gesperrt_bis, time.time() + SPERRE_PAUSE_S)
    return True


def youtube_gesperrt():
    """Restsekunden der Pause nach einer Sperre, sonst 0."""
    return max(0.0, _youtube_gesperrt_bis - time.time())


def _nebenweg_abruf(opts, url, wo, download=False):
    """Der yt-dlp-Abruf der Nebenwege (Untertitel, Abo-Blick, Anreichern,
    Entdecken). Eine Sperre wird gemeldet und nicht wiederholt, die Cookies
    bleiben (ohne Cookies wählt yt-dlp genau die Wege, gegen die YouTube
    sperrt). Nur ein Cookie-Fehler bekommt einen Zweitversuch ohne Cookies;
    nach einem reinen Netzfehler entfällt er. Die Pause nach einer Sperre prüft
    der Aufrufer, wenn er eine Serie ist. Rückgabe: das Info-Dict oder None."""
    for versuch in (1, 2):
        try:
            with _ydl(opts) as y:
                return y.extract_info(url, download=download)
        except Exception as e:                       # noqa: BLE001 — Nebenweg: None statt Absturz
            if youtube_sperre_vermerken(e):          # vor dem Cookie-Test: die Bot-Meldung nennt Cookies
                fehler_merken(url, str(e), "sperre-" + wo)
                return None
            if versuch == 1 and _ist_cookie_fehler(e):
                opts.pop("cookiesfrombrowser", None)
                continue
            return None
    return None


def _ist_untertitel_fehler(exc):
    """Nur der Untertitel-Abruf ist gescheitert (z.B. drosselt YouTube die
    Untertitel-Endpoints gern mit HTTP 429) — das Video selbst wäre ladbar.
    Dann: gleicher Lauf nochmal OHNE Untertitel statt stundenlanger Backoff-
    Schleife bei 0% (JB-Vorfall 11.07.); die .vtt lädt der Player später nach."""
    t = str(exc).lower()
    return "subtitle" in t and ("429" in t or "too many requests" in t
                                or "unable to download" in t)


# Höchstens zwei yt-dlp-Auflösungen gleichzeitig (Gesamtprüfung F2). Je Folge
# oder Link startet ein eigener Faden, der Knopf „Alle (N)“ schickt bis zu 5.000
# auf einmal — ungebremst ist das genau der Abruf-Sturm, den YouTube mit 429 und
# der Bot-Abfrage beantwortet. Der Platzhalter erscheint weiter sofort; nur der
# Abruf wartet auf einen Platz.
AUFLOESEN_GEDULD_S = 300    # so lange darf ein Auflösen dauern, dann gilt es als hängend


class _AufloesePlaetze:
    """Die Plätze für das Auflösen. Wer länger als AUFLOESEN_GEDULD_S auf
    seinem Platz sitzt, gilt als hängend und zählt nicht mehr mit: genau dann
    reiht `queue_heilen` seinen Eintrag wieder ein. Sein Faden steckt weiter in
    yt-dlp, der Platz geht aber an den nächsten Link. Eine BoundedSemaphore
    hielten zwei hängende Abrufe für immer, und jeder weitere Link stand
    danach auf „prueft“ (Nacharbeit F2)."""

    def __init__(self, anzahl):
        self.anzahl = anzahl
        self._bed = threading.Condition(threading.Lock())
        self._inhaber = {}                            # Marke -> Eintrittszeit (nur nicht hängende)

    def _haenger_abschreiben(self):
        """Hängende Inhaber zählen nicht mehr. True, wenn einer dazukam."""
        grenze = time.time() - AUFLOESEN_GEDULD_S
        alt = [m for m, t in self._inhaber.items() if t <= grenze]
        for m in alt:
            self._inhaber.pop(m)
        return bool(alt)

    @contextlib.contextmanager
    def platz(self):
        marke = object()
        with self._bed:
            while True:
                self._haenger_abschreiben()
                if len(self._inhaber) < self.anzahl:
                    break
                # Geweckt wird bei jeder Freigabe und aus der Heilung; spätestens
                # dann, wenn der älteste Inhaber zum Hänger wird.
                rest = min(self._inhaber.values()) + AUFLOESEN_GEDULD_S - time.time()
                self._bed.wait(min(max(rest, 0.5), AUFLOESEN_GEDULD_S))
            self._inhaber[marke] = time.time()
        try:
            yield
        finally:
            with self._bed:
                if self._inhaber.pop(marke, None) is not None:
                    self._bed.notify()               # ein Hänger gab seinen Platz schon ab

    def haenger_freigeben(self):
        """Aus `queue_heilen`: die Plätze hängender Abrufe an Wartende geben."""
        with self._bed:
            if self._haenger_abschreiben():
                self._bed.notify_all()


_aufloese_plaetze = _AufloesePlaetze(2)


def _info_abrufen(url, opts):
    """Der yt-dlp-Abruf des Auflösens, samt Cookie-Heilung."""
    try:
        with _ydl(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:                           # noqa: BLE001 — Cookie-Probleme heilen
        # Sperre zuerst: die Bot-Meldung TRAEGT den Cookie-Hinweis in sich,
        # ein Wegwerfen der Cookies laeuft direkt in den naechsten 403.
        if _ist_sperre(e) or not _ist_cookie_fehler(e):
            raise
        opts.pop("cookiesfrombrowser", None)
        with _ydl(opts) as ydl:
            return ydl.extract_info(url, download=False)


def aufloesen(url, qualitaet, ganze_liste=False, abo="", ersetzt=None, limit=None, ziel_playlist="",
              menge=None, richtung="neu", von=None, bis=None):
    """URL prüfen und in Queue-Einträge verwandeln (Playlist/Mix -> Einzelvideos).
    ganze_liste=True erzwingt die komplette Liste/den Mix auch bei einem
    watch?v=…&list=…-Link (JB-/Kumpel-Wunsch: „YouTube-Mixe runterladen").
    limit: Wunsch-Anzahl fuer Mixe (Build 98, JB: einstellbar; 1..500).
    abo: Abo-Id — fertige Downloads landen dann in der Abo-Playlist;
    ersetzt: alte Bibliotheks-Keys, die NACH dem Erfolg in den Papierkorb gehen.
    Läuft im Hintergrund-Thread, damit die Oberfläche nie blockiert.
    Den Status ändert das Ergebnis nur, solange der Eintrag noch „prueft“
    (Gesamtprüfung F3): hat ihn die Heilung derweil eingereiht und ein Worker
    übernommen, bleibt er in Ruhe — sonst lüde ein zweiter Worker dasselbe."""
    platzhalter = Q.neu(url, None, qualitaet)
    if abo:
        platzhalter["abo"] = abo
    if ersetzt:
        platzhalter["abo_ersetzt"] = list(ersetzt)
    with Q.lock:
        platzhalter["status"] = "prueft"
        _prueft_wartet.add(platzhalter["id"])        # wartet auf einen Platz: heilt nicht
    try:
        Q.speichern()
        opts = _ydl_basis_opts()
        # Mixe (list=RD…) sind endlos — Wunsch-Anzahl (Build 98, Default 50),
        # damit nicht tausende Einträge entstehen; echte Playlists laufen unbegrenzt.
        # Von–bis-Bereich (v1.1.1, JB übers Addon: „von was bis was") — schneidet
        # schon bei der Auslese. Review-Finding 4: bei Mixen geht auch `bis` durch
        # die 1..500-Klemme (_mix_limit), sonst hebelte ein getipptes bis=99999
        # genau den Deckel aus, den _mix_limit gegen endlose Listen aufstellt.
        # Ohne bis, aber mit von: 50 Stück ab von (statt Start>Ende=leer).
        if ganze_liste and links._ist_mix(url):
            opts["playlistend"] = links._mix_limit(bis or ((von + 49) if von else None) or limit)
        elif bis:
            opts["playlistend"] = bis
        if von:
            opts["playliststart"] = von
        opts.update({"extract_flat": "in_playlist", "skip_download": True,
                     "noplaylist": (not ganze_liste) and links.ist_einzelvideo(url)})
        info, fehler = _aufloesen_abruf(platzhalter, url, opts)
    finally:
        with Q.lock:
            _prueft_wartet.discard(platzhalter["id"])
    if info is None and fehler is None:              # entfernt oder übernommen, bevor ein Platz frei war
        return
    if fehler is not None:
        voll = str(fehler)
        # Sperre und Fehlerkanal immer, auch wenn der Eintrag derweil übernommen
        # ist: eine späte Sperre muss die Nebenwege genauso pausieren.
        fehler_merken(url, voll, "aufloesen" + (" / sperre" if youtube_sperre_vermerken(fehler) else ""))
        with Q.lock:
            if platzhalter.get("status") != "prueft":    # F3: derweil übernommen
                return
            platzhalter["fehler"] = _fehltext(fehler)
            if geo.ist_geo_fehler(voll) and CFG.get("geo_vpn"):
                platzhalter["geo_laender"] = geo.laender_aus_fehler(voll)
                platzhalter["status"] = "wartend"    # Worker übernimmt die Geo-Kette
            else:
                platzhalter["status"] = "fehler"
        Q.speichern()
        return
    _aufloesen_einreihen(platzhalter, info, url, qualitaet, ganze_liste, abo, ziel_playlist,
                         menge, richtung, von, bis)


def _aufloesen_abruf(platzhalter, url, opts):
    """Auf einen Platz warten, dann yt-dlp fragen. Rückgabe (info, fehler);
    (None, None), wenn der Platzhalter vorher entfernt oder übernommen wurde —
    dann wird YouTube gar nicht gefragt."""
    with _aufloese_plaetze.platz():
        with Q.lock:
            _prueft_wartet.discard(platzhalter["id"])
            if platzhalter not in Q.items or platzhalter.get("status") != "prueft":
                return None, None
            _prueft_seit[platzhalter["id"]] = time.time()   # die 5-min-Geduld beginnt jetzt
        try:
            return _info_abrufen(url, opts), None
        except Exception as e:                       # noqa: BLE001 — Nutzer sieht den Text
            return None, e


def _aufloesen_einreihen(platzhalter, info, url, qualitaet, ganze_liste, abo, ziel_playlist,
                         menge, richtung, von, bis):
    """Das Ergebnis des Auflösens in die Warteschlange übernehmen.
    Q.lock hält nur das Einreihen selbst (Gesamtprüfung F7): die Platte fragt
    `schon_geladen` vorher (bei einer verschobenen Datei ein rekursives glob
    über den ganzen Download-Ordner), die Playlists werden danach geschrieben.
    Vorher warteten Worker und Ticker so lange mit."""
    eintraege = info.get("entries") if info.get("_type") == "playlist" else None
    if eintraege is not None:
        kandidaten = []
        for e in links._liste_zuschneiden(eintraege, menge, richtung):   # Build 127: JB-Regler
            v_url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
            kandidaten.append((e, v_url, schon_geladen(v_url, qualitaet)))
    else:
        einzel_url = info.get("webpage_url") or url
        einzel_fund = schon_geladen(einzel_url, qualitaet)
    zuordnen = []                                     # schon Geladenes: in die Playlists, nach der Sperre
    vermerken = False
    with Q.lock:
        if platzhalter not in Q.items:               # Nutzer hat ihn derweil entfernt
            return
        if platzhalter.get("status") != "prueft":    # F3: Heilung + Worker haben übernommen
            return
        if eintraege is not None and not eintraege and (von or bis):
            # Review-Finding 7: ein leerer von/bis-Bereich verschwand STUMM —
            # Platzhalter weg, kein Fehler, das Addon meldete „✓ eingereiht".
            # Jetzt bleibt ein ehrlicher Fehler-Eintrag stehen.
            platzhalter["status"] = "fehler"
            platzhalter["fehler"] = ("Der Bereich von/bis ergab keine Videos — "
                                     "liegt „von“ hinter dem Listenende?")
        elif eintraege is not None:
            Q.items.remove(platzhalter)
            vermerken = bool(kandidaten)
            for e, v_url, fund in kandidaten:
                if _schon_da(v_url, qualitaet):
                    continue
                neu = Q.neu(v_url, e.get("title"), qualitaet, e.get("duration"))
                if abo:
                    neu["abo"] = abo
                if ziel_playlist:
                    neu["ziel_pl"] = ziel_playlist
                if fund:
                    _als_uebersprungen(neu, fund)
                    zuordnen.append(_geladen_key(v_url, qualitaet))
        else:
            platzhalter["titel"] = info.get("title") or url
            platzhalter["dauer"] = info.get("duration")
            platzhalter["url"] = einzel_url
            if ziel_playlist:
                platzhalter["ziel_pl"] = ziel_playlist
            if _schon_da(platzhalter["url"], qualitaet, ausser=platzhalter["id"]):
                Q.items.remove(platzhalter)
            elif einzel_fund:
                _als_uebersprungen(platzhalter, einzel_fund)
            else:
                platzhalter["status"] = "wartend"
    for key in zuordnen:
        if abo:                                      # war schon da -> trotzdem in die Abo-Playlist
            _abo_playlist_zuordnen(abo, key)
        if ziel_playlist:                            # dito fuer die Entdeckt-Playlist (Build 100)
            _playlist_einreihen(ziel_playlist, key)
    Q.speichern()
    if vermerken:                                     # v1.1.2: komplette Liste vermerken (Haken im Addon)
        _liste_vermerken(url, ganze_liste, von, bis)


# ---- „Schon geladen"-Datenbank (JB-Regel: identischer Name + gleiche Größe
# -> überspringen). Überlebt „Liste leeren" und App-Neustarts.

_geladen = _json_laden(GELADEN_PFAD, {})    # "videoid|qualitaet" -> {name, groesse, pfad, ts}

# Die Bibliotheks-DB unter EINER Sperre (Gesamtprüfung F6). Einträge kommen und
# gehen nur unter _io_lock, jeder Durchlauf geht über einen Schnappschuss, der
# unter derselben Sperre entsteht. Gespeichert wird über _geladen_speichern: der
# Text entsteht unter der Sperre, geschrieben wird außerhalb, und ein älterer
# Stand überschreibt nie einen neueren. Vorher trug geladen_merken ohne Sperre
# ein, während ein anderer Faden json.dump über das lebende Dict laufen ließ:
# „dictionary changed size during iteration“, und ein fertiger Download galt
# als Fehlschlag (gemessen: 13 bis 16 von 30 Speichervorgängen).
_geladen_schreib_lock = threading.Lock()
_geladen_stand = {"erzeugt": 0, "geschrieben": 0}


def _geladen_schnappschuss():
    """(Schlüssel, Eintrag)-Paare der Bibliothek, unter der Sperre gezogen. Die
    Einträge sind die lebenden Dicts: Felder ändern wirkt, Einfügen/Entfernen
    im Schnappschuss nicht."""
    with _io_lock:
        return list(_geladen.items())


def _geladen_schluessel():
    with _io_lock:
        return list(_geladen)


def _geladen_speichern():
    """Die Bibliothek schreiben. OSError wie `_json_speichern`."""
    with _io_lock:
        text = json.dumps(_geladen, ensure_ascii=False)
        _geladen_stand["erzeugt"] += 1
        nr = _geladen_stand["erzeugt"]
    daten = json.loads(text)
    with _geladen_schreib_lock:
        if nr < _geladen_stand["geschrieben"]:
            return                                    # ein neuerer Stand liegt schon auf der Platte
        _json_speichern(GELADEN_PFAD, daten)
        _geladen_stand["geschrieben"] = nr


def _geladen_key(url, qualitaet):
    return f"{links._video_id(url)}|{qualitaet}"


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
    # Id-Tag VOR dem Fingerabdruck (Tag verschiebt den Dateianfang — sonst
    # stimmt das gespeicherte fp nicht mehr mit der Datei überein).
    idtag = _id_tag_schreiben(datei, key.split("|")[0])
    try:
        groesse = os.path.getsize(datei)             # Tag hat die Datei vergrößert
    except OSError:
        pass
    fp = _datei_fp(datei)                            # Content-Ausweis (Bibliothek 2.0)
    with _io_lock:                                   # F6: Eintragen nur unter der Sperre
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
            "archiviert": alt.get("archiviert", False), "ts": time.time(),
            "idtag": idtag,
            "fp": fp}
    _geladen_speichern()
    if item.get("abo"):                              # Abo-Download -> in die Abo-Playlist
        _abo_playlist_zuordnen(item["abo"], key)
    if item.get("ziel_pl"):                          # Entdecker-Download -> „✨ Entdeckt …" (Build 100)
        _playlist_einreihen(item["ziel_pl"], key)
    for altkey in (item.get("abo_ersetzt") or []):   # Format-Erneuern: Altes ERST NACH Erfolg weg
        if altkey != key and altkey in _geladen:
            with _io_lock:
                _datei_loeschen(altkey)
                _geladen.pop(altkey, None)
                _geladen_speichern()
            _playlists_speichern()


# ---- Bibliothek: Ansicht über alle je geladenen Titel (aus geladen_log.json).


def _datei_index():
    """videoid -> Pfad aus EINEM Ordner-Durchlauf (inkl. Unterordner). So braucht
    die Bibliothek nicht pro Eintrag zu suchen (erkennt auch verschobene Dateien).
    Namenlose Dateien (ohne [Id]) löst die zentrale Kette auf — die Karten
    entstehen erst, wenn wirklich eine solche Datei auftaucht (Alltagskosten 0)."""
    idx = {}
    karten = None
    for root, _, files in _walk_ohne_rueckhol(ziel_ordner()):
        for f in files:
            # NUR Mediendateien: die .vtt-Untertitel/.jpg-Cover NEBEN dem Video
            # dürfen den Index nie vergiften — sonst spielt /media eine
            # Untertitel-Datei aus und das Bild bleibt schwarz (JB-Fund 14.07.).
            if not f.lower().endswith(musik_einstufung.AUDIO_EXT + musik_einstufung.VIDEO_EXT):
                continue
            pfad = os.path.join(root, f)
            m = re.search(r"\[([\w-]{6,})\]", f)
            vid = m.group(1) if m else ""
            if not vid:
                if karten is None:
                    karten = _id_karten()
                vid = _datei_videoid(pfad, karten)
            if vid:
                idx.setdefault(vid, []).append(pfad)
    return idx


def _datei_aus(liste, qualitaet=""):
    """Aus mehreren Dateien derselben Video-ID die zur QUALITÄT passende wählen:
    audio-Key -> Audio-Datei zuerst, alles andere -> Video-Datei zuerst. Sonst
    bekam ein |beste-Eintrag die MP3-Fassung -> Ton ja, Bild schwarz (JB 14.07.)."""
    if not liste:
        return None
    audio = [p for p in liste if p.lower().endswith(musik_einstufung.AUDIO_EXT)]
    video = [p for p in liste if p.lower().endswith(musik_einstufung.VIDEO_EXT)]
    if qualitaet == "audio":
        return (audio or video or liste)[0]
    return (video or audio or liste)[0]


def bibliothek_liste():
    idx = _datei_index()
    out = []
    for key, e in _geladen_schnappschuss():
        vid, _, qual = key.partition("|")
        gespeichert = e.get("pfad")
        pfad = gespeichert if (gespeichert and os.path.isfile(gespeichert)) else _datei_aus(idx.get(vid), qual)
        art = ""
        if pfad:
            art = "audio" if pfad.lower().endswith(musik_einstufung.AUDIO_EXT) else "video"
        out.append({
            "id": key, "videoid": vid, "dateiart": art,
            "qualitaet": e.get("qualitaet") or qual or "",
            "titel": e.get("titel") or musik_einstufung._titel_aus_name(e.get("name", "")),
            "uploader": e.get("uploader", ""), "dauer": e.get("dauer"),
            "upload_date": e.get("upload_date", ""),
            "kategorie": e.get("kategorie") or musik_einstufung._kat_aus_name(e.get("name", "")),
            "vcodec": e.get("vcodec", ""), "acodec": e.get("acodec", ""),
            "abr": e.get("abr", 0), "asr": e.get("asr", 0), "hoehe": e.get("hoehe", 0),
            "groesse": e.get("groesse", 0), "name": e.get("name", ""),
            "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg" if links._plausible_id(vid) else "",
            "url": e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if links._plausible_id(vid) else ""),
            "vorhanden": bool(pfad), "archiviert": bool(e.get("archiviert")),
            "plays": e.get("plays", 0), "blacklist": bool(e.get("blacklist")),
            "last_play": e.get("last_play", 0), "ts": e.get("ts", 0),
            "kapitel": e.get("kapitel") or [],
            "kuenstler": e.get("kuenstler", ""), "album": e.get("album", ""),
            "track": e.get("track", ""), "jahr": e.get("jahr", ""),
            "genre": e.get("genre", ""),
            "cover_album": bool(e.get("cover_album")),
            "herz": bool(e.get("herz")),             # ❤ Lieblingssong (JB 05.08.)
            "abo_nr": e.get("abo_nr", ""),
            "wiedergabe": e.get("wiedergabe") or None,
        })
    # Build 144g (JB Punkt 4): „Videonummer je Kanal als eigenes Feld."
    # Die ECHTE Kanal-Nummer aus dem Abo-Backkatalog hat Vorrang — sie zählt
    # über den ganzen Kanal, nicht nur über das, was hier liegt.
    nummer, gesamt = musik_einstufung._kanal_nummern(out)
    # Build 144h (JB Punkt 5): „nur Lieder" braucht eine Einstufung, die den
    # KANAL mitliest — deshalb über die ganze Liste, nicht je Eintrag.
    grade = musik_einstufung._musik_grade([(x["id"], x) for x in out])
    # Build 144o: Favorit-Repräsentant je Gruppe. Nur er erscheint im Raster
    # und im Zufall; die übrigen (Clips + Hauptsong, falls ein Clip Favorit
    # ist) liegen im Rechtsklick. `hat_geschwister` sagt, ob es überhaupt
    # Alternativen gibt (für das Gruppen-Menü + das ✂-Abzeichen).
    fav = set(_favorit_je_gruppe().values())
    gruppen_groesse = {}
    for x in out:
        gruppen_groesse[_clip_gruppe(x["id"])] = gruppen_groesse.get(_clip_gruppe(x["id"]), 0) + 1
    for x in out:
        vid = _clip_gruppe(x["id"])
        x["kanal_nr"] = x.get("abo_nr") or nummer.get(x["id"], 0)
        x["kanal_von"] = gesamt.get(x["id"], 0)
        x["musik"] = grade.get(x["id"], "nein")
        x["clip"] = _ist_clip(x["id"])
        x["gruppe"] = vid
        x["ist_favorit"] = (x["id"] in fav)
        x["hat_geschwister"] = gruppen_groesse.get(vid, 1) > 1
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


def _schreib_zeitlimit_aufheben(handler):
    """S14 (Nacharbeit 25.09.2026): Ströme ohne Schreib-Zeitlimit ausliefern.
    Nach dem Kopf gerufen, von allen Strom-Wegen (Datei, Jellyfin-Proxy,
    Transcoder). Ein pausierter Film nimmt minutenlang nichts ab; mit dem
    Zeitlimit des Handlers bräche der Strom nach 30 s ab, und beim Transcoder
    (keine Länge, keine Range) kann der Browser nichts nachholen. Ein Client,
    der ganz weg ist, beendet den Strom über den Verbindungsabbruch wie vor S14."""
    verbindung = getattr(handler, "connection", None)
    if verbindung is not None:
        try:
            verbindung.settimeout(None)
        except OSError:
            pass


def _stream_datei(handler, pfad):
    """Datei ausliefern, Range-Anfragen (Seek/Abspielen) inklusive."""
    globals()["_letzter_stream"] = time.time()        # Build 144m: „gerade Wiedergabe" merken
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
    _schreib_zeitlimit_aufheben(handler)
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


def ordner_zeigen(pfad=None):
    """Explorer öffnen und IN DEN VORDERGRUND holen (JB 07.08.: „Zielordner
    öffnet sich im Hintergrund").

    Wurzel: Windows verweigert einem Hintergrundprozess (unser pythonw-Server
    hat keinen Eingabe-Fokus) das Setzen des Vordergrundfensters —
    `Popen(["explorer", …])` erbt diese Sperre. Der Umweg über die Shell
    (`os.startfile`, intern ShellExecute) gilt als Nutzer-veranlasst; die
    Shell darf ihr Fenster nach vorn holen.
    """
    ziel = pfad or ziel_ordner()
    try:
        if pfad and os.path.isfile(pfad):
            # Datei markieren: dafür braucht es explorer /select — danach
            # das Fenster per ShellExecute-Regel nach vorn holen.
            subprocess.Popen(["explorer", "/select,", os.path.normpath(pfad)])
            return
        os.startfile(os.path.normpath(ziel))         # Windows-Weg (Vordergrund!)
    except (OSError, AttributeError):
        subprocess.Popen(["explorer", os.path.normpath(ziel)])


def extern_abspielen(pfad):
    """In VLC öffnen, falls installiert, sonst im Windows-Standardplayer."""
    for v in _VLC_KANDIDATEN:
        if os.path.exists(v):
            subprocess.Popen([v, pfad])
            return
    try:
        os.startfile(pfad)                           # einzig sinnvoll unter Windows
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


def _clip_basisname(quelle):
    """Dateiname-Stamm für einen Ausschnitt — ohne die [Video-Id]-Klammern.
    Dieselbe Klammer-Regel wie in `_migrations_ziel` (e=None)."""
    stamm = os.path.splitext(os.path.basename(quelle))[0]
    return re.sub(r"\s*\[[\w-]{6,}\]", "", stamm).strip()


# ---- Ausschnitte gehören zu ihrem Song (Build 144k, JB 25.07.) --------------
# JB: „die ausschnitte sollten einen eigenen ordner bekommen, wie eine playlist,
# nur in dem song … nur der favorit zählt." Ein Ausschnitt trägt |clip im
# Schlüssel und teilt die Video-Id mit seinem Song. Genau EIN Ausschnitt je
# Song ist der Favorit: die eigene Wahl (`favorit`-Flag), sonst der neuste.
def _ist_clip(key):
    return "|clip" in (key or "")


def _clip_gruppe(key):
    return (key or "").split("|")[0]


def _favorit_je_gruppe():
    """Video-Id -> Schlüssel des Favoriten der Gruppe (Build 144o, JB 25.07.).

    Der Favorit ist der REPRÄSENTANT: er wird angezeigt, abgespielt und zählt
    im Zufall. Wählbar ist JEDER Eintrag der Gruppe — der Hauptsong ODER ein
    Ausschnitt. Regel: die eigene Wahl (`favorit`-Flag) gewinnt; ohne Wahl ist
    der HAUPTSONG (Nicht-Clip) der Favorit — nur wenn es gar keinen Hauptsong
    gibt (reine Clip-Gruppe), der neuste. Reine Auslese, kein Seiteneffekt.
    """
    gruppen = {}
    for k, e in _geladen_schnappschuss():
        gruppen.setdefault(_clip_gruppe(k), []).append((k, e))
    fav = {}
    for vid, liste in gruppen.items():
        gewaehlt = [p for p in liste if p[1].get("favorit")]
        if gewaehlt:
            fav[vid] = max(gewaehlt, key=lambda p: p[1].get("ts") or 0)[0]
            continue
        haupt = [p for p in liste if not _ist_clip(p[0])]
        basis = haupt or liste                       # Hauptsong bevorzugt, sonst neuster Clip
        fav[vid] = max(basis, key=lambda p: p[1].get("ts") or 0)[0]
    return fav


def _clip_favorit_setzen(key):
    """JBs Wahl festhalten: dieser Eintrag (Hauptsong ODER Ausschnitt) wird
    Favorit seiner Gruppe, die Geschwister verlieren das Flag (persistiert)."""
    if key not in _geladen:
        return {"fehler": "unbekannt"}
    vid = _clip_gruppe(key)
    with _io_lock:
        for k, e in _geladen_schnappschuss():
            if _ist_clip(k) and _clip_gruppe(k) == vid:
                if k == key:
                    e["favorit"] = True
                else:
                    e.pop("favorit", None)
        _geladen_speichern()
    return {"ok": True}


def _clip_favorit_zuruecksetzen(vid):
    """Alle Favoriten-Wahlen einer Gruppe löschen — damit nach einem NEUEN
    Ausschnitt wieder der neuste (also der neue) Favorit ist (JB-Wunsch)."""
    for k, e in _geladen_schnappschuss():
        if _ist_clip(k) and _clip_gruppe(k) == vid:
            e.pop("favorit", None)


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

    # Build 144i (JB 25.07.): den Ausschnitt sauber benennen — die
    # [Video-Id]-Klammern des Quellnamens wandern NICHT mit.
    basis = _clip_basisname(quelle)
    ext = os.path.splitext(quelle)[1]
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
        # Build 144o: der NEUE Ausschnitt wird Favorit (JB) — die früheren
        # Wahlen der Gruppe löschen und das Flag auf den neuen Eintrag setzen.
        # (Ohne Flag wäre sonst der Hauptsong der Standard-Favorit.)
        _clip_favorit_zuruecksetzen(vid)
        eintrag["favorit"] = True
        _geladen[neu_key] = eintrag
        _geladen_speichern()
    return {"ok": True, "name": os.path.basename(ziel)}


# ---- Auto-Tagging (MusicBrainz): Künstler/Titel/Album sauber nachschlagen ----
# Gratis-API ohne Key; Regel: max. 1 Anfrage/Sekunde + aussagekräftiger User-Agent.

MB_API = "https://musicbrainz.org/ws/2/recording"
MB_UA = "JB-YTDL-Suite/1.0 (https://github.com/schn4ppi)"


def titel_abgleich():
    """Anzeige-Titel an bereits umbenannte Dateien angleichen (Build 141).

    JB: „Was ist jetzt mit z. B. Rocky Mountain High in der Bibliothek, ich
    seh immer noch nicht die geordneten Titel." Der Fix aus Build 140 greift
    nur beim NÄCHSTEN Umbenennen — was längst umbenannt auf der Platte liegt,
    trug in der Datenbank weiter den alten YouTube-Titel.

    Dieser Abgleich zieht das einmalig nach. Nicht-destruktiv: der
    ursprüngliche Titel wird in `titel_orig` gesichert (Grundlage für Suche
    und Auto-Tagging), und angefasst wird nur, wo der Dateiname wirklich
    etwas anderes sagt als die Anzeige. Läuft einmal beim Start, nicht
    periodisch (Last-Budget).
    """
    geaendert = 0
    with _io_lock:
        for _k, e in _geladen_schnappschuss():
            name = e.get("name") or ""
            if not name:
                continue
            aus_name = musik_einstufung._titel_aus_name(name)
            if not aus_name or aus_name == (e.get("titel") or ""):
                continue
            if not e.get("titel_orig"):
                e["titel_orig"] = e.get("titel") or ""
            e["titel"] = aus_name
            geaendert += 1
        if geaendert:
            _geladen_speichern()
    if geaendert:
        _sag(f"Bibliothek: {geaendert} Titel an die Dateinamen angeglichen.")
    return geaendert


def autotag_nach_download(item):
    """Frisch geladene Musik gleich benennen (Build 136, JB-Wunsch).

    JB: „Auto-Tagging sollte standardmäßig direkt nach dem Download
    passieren." Vorher musste man es im Ansicht-Menü von Hand anstoßen —
    deshalb trug frisch Geladenes noch den rohen YouTube-Namen.

    Bewusst zurückhaltend: NUR Musik (bei Videos gibt es bei MusicBrainz
    nichts zu holen) und nur, wenn noch kein Album eingetragen ist. Es hängt
    sich an das bestehende Fertig-Ereignis, startet also keinen neuen
    Dauerprozess und keinen neuen Zeitplan (Last-Budget-Regel). Läuft im
    Hintergrund, damit der nächste Download nicht auf MusicBrainz wartet.
    """
    try:
        key = _geladen_key(item.get("url") or "", item.get("qualitaet") or "")
        e = _geladen.get(key)
        if not e or not musik_einstufung._ist_musik(e) or e.get("album"):
            return
        threading.Thread(target=autotag_lauf, args=([key],), daemon=True).start()
    except Exception:                                 # noqa: BLE001 — nie den Download stören
        pass


def auto_umbenennen_nach_download(item):
    """Frisch geladene Datei sofort sauber benennen (JB 25.07.: „Das sollte
    direkt automatisch passieren").

    Der Download schreibt „%(title)s [%(id)s]" — die [Video-Id]-Klammern
    blieben bisher für immer stehen, weil KEIN Download-Pfad je umbenannte
    (autotag_lauf schreibt nur Tags). Jetzt läuft nach dem Download derselbe
    nicht-destruktive, reversible Weg wie beim Ordner-Import: migration_anwenden
    entfernt die Klammern, wendet das Namens-Schema an, nimmt .vtt-Geschwister
    mit und schreibt ein Rückroll-Protokoll (↩ im Namens-Fenster).

    Gesteuert vom bestehenden Schalter `auto_umbenennen` — bei JB an. Der frisch
    geladene Eintrag trägt fp + Id-Tag (geladen_merken), das Sicherheitsnetz der
    Migration greift also. Bricht etwas: die Klammern bleiben, alles läuft
    weiter (die Erkennungs-Kette trägt beide Namen).
    """
    if not CFG.get("auto_umbenennen"):
        return
    try:
        key = _geladen_key(item.get("url") or "", item.get("qualitaet") or "")
        if key not in _geladen:
            return
        r = migration_anwenden(go=True, keys={key})
        if r.get("umbenannt"):
            _sag("Auto-Umbenennen: frisch geladene Datei nach dem Namens-Schema "
                 "benannt (↩ rückgängig im Namens-Fenster)")
    except Exception:                                 # noqa: BLE001 — nie den Download stören
        pass


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


def _mb_norm_titel(t):
    """Titel für den Exakt-Vergleich normalisieren (JB-Go 05.08.): MusicBrainz
    schreibt Titel mit TYPOGRAFISCHEN Zeichen („“Heroes“", ’, –, …) — der
    YouTube-Name kommt mit geraden. Ohne Angleich fiel der Exakt-Treffer aus
    und die Datums-Sortierung wählte ein obskures Fremd-Release (live: Bowies
    „Heroes" bekam „Turn On the Lights", 2008)."""
    t = (t or "").casefold()
    for z in "\"'“”„‚‘’‛′″«»‹›":
        t = t.replace(z, "")
    t = t.replace("–", "-").replace("—", "-").replace("…", "...")
    return " ".join(t.replace(" ", " ").split())


def _itunes_suche(kuenstler, titel, timeout=10):
    """Zweite Quelle (JB 05.08., „links und rechts schauen"): die iTunes
    Search API — offen, ohne Schlüssel, mit Alben, Jahr, Genre und großem
    Cover. Nur als RÜCKFALL, wenn MusicBrainz nichts oder kein Album liefert;
    übernommen wird nur ein Treffer, dessen Titel UND Künstler normalisiert
    zum Kandidaten passen (JB-Leitsatz: nur Belegtes)."""
    import urllib.parse
    import urllib.request
    if not titel:
        return None
    q = urllib.parse.urlencode({"term": f"{kuenstler} {titel}".strip(),
                                "media": "music", "entity": "song", "limit": "5"})
    try:
        req = urllib.request.Request("https://itunes.apple.com/search?" + q,
                                     headers={"User-Agent": MB_UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:                                # noqa: BLE001 — Netz: kein Fund
        return None
    for t in data.get("results", []) or []:
        tn, ka = _mb_norm_titel(t.get("trackName")), _mb_norm_titel(titel)
        # exakt ODER Präfix (iTunes hängt Untertitel an: „Running Up That
        # Hill (A Deal with God)") — Präfix nur bei aussagekräftiger Länge.
        if tn != ka and not (len(ka) >= 8 and tn.startswith(ka)):
            continue
        if kuenstler and _mb_norm_titel(t.get("artistName")) != _mb_norm_titel(kuenstler):
            continue
        cover = (t.get("artworkUrl100") or "").replace("100x100", "600x600")
        return {"kuenstler": t.get("artistName") or kuenstler,
                "titel": t.get("trackName") or titel,
                "album": t.get("collectionName") or "",
                "jahr": (t.get("releaseDate") or "")[:4],
                "genre": t.get("primaryGenreName") or "",
                "release_id": "", "rg_id": "", "cover_url": cover}
    return None


def _bild_laden(url, timeout=15):
    """Ein Bild von einer URL (iTunes-Artwork) — gleiche Plausibilität wie
    beim Cover Art Archive, ein kurzer Retry."""
    if not url:
        return None
    import urllib.request
    for versuch in (1, 2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": MB_UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                daten = r.read()
            if 2000 < len(daten) < 10 * 1024 * 1024:
                return daten
            return None
        except Exception:                            # noqa: BLE001
            time.sleep(3)
    return None


def _mb_suche(kuenstler, titel, timeout=10, live_hinweis=None):
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
    # KEIN "NOT secondarytype:*" mehr (JB-Go 05.08., live gemessen): das
    # schloss ein Recording aus, sobald es auf IRGENDEINER Compilation liegt —
    # also gerade die Originale (Bowies 1977er "Heroes" liegt auf zig
    # Best-ofs), während obskure Ein-Album-Duplikate überlebten. Der
    # Compilation-Schutz sitzt weiter in der RELEASE-Auswahl unten.
    data = suche(basis + " AND status:official AND primarytype:album", 100)
    recs = [r for r in data.get("recordings", []) if int(r.get("score", 0)) >= 85
            and not r.get("video") and _artist_passt(r, kuenstler)]
    exakt = [r for r in recs if _mb_norm_titel(r.get("title")) == _mb_norm_titel(titel)]
    pool = exakt or recs
    pool.sort(key=lambda r: r.get("first-release-date") or "9999")
    if not pool:                                     # kein Studio-Album: nur Künstler/Titel säubern
        time.sleep(1.1)
        data = suche(basis, 5)
        recs = [r for r in data.get("recordings", []) if int(r.get("score", 0)) >= 85
                and _artist_passt(r, kuenstler)]
        if not recs:
            return None
        rec = next((r for r in recs
                    if _mb_norm_titel(r.get("title")) == _mb_norm_titel(titel)), recs[0])
        return {"kuenstler": _mb_kuenstler(rec), "titel": rec.get("title", ""),
                "album": "", "jahr": "", "release_id": "", "rg_id": "", "genre": ""}
    # ALBUM-zentrierte Wahl (JB-Go 05.08., dreifach live gemessen): MusicBrainz
    # führt denselben Song als VIELE Recordings (Original, Remaster je
    # Compilation, …). Wer erst EIN Recording wählt und dann dessen Releases
    # ansieht, greift daneben — die Duplikate hängen an obskuren Alben.
    # Die SUCHE liefert je Recording seine Releases samt Release-Group mit:
    # also über ALLE exakten Treffer das früheste echte Album wählen und das
    # zugehörige Recording nehmen. Compilation-Schutz sitzt HIER: keine
    # secondary-types — außer Soundtrack, denn der IST das kanonische Album
    # (Purple Rain). Undatierte „Alben" sind fast immer Box-Sets/Datenmüll.
    # Live-Titel-Regel (JB 05.08., Nirvana-Fall): sagt der QUELL-TitEL selbst
    # „live/unplugged", zählen auch offizielle LIVE-Alben — und gewinnen sogar
    # vor Studio-Alben (die Aufnahme IST die Live-Fassung; „MTV Unplugged in
    # New York" schlägt „Nevermind"). Gibt es kein Live-Album, bleibt das
    # Studio-Album der ehrliche Rückfall (Metadaten ja, der Live-Vermerk
    # bleibt im eigenen Titel). OHNE Live-Marker bleiben Live-Alben verboten
    # — der alte Bootleg-Schutz.
    ist_live = live_hinweis if live_hinweis is not None else musik_einstufung._ist_live_titel(titel)
    def _album_ok(rel):
        rg = rel.get("release-group") or {}
        sec = rg.get("secondary-types") or []
        return (rg.get("primary-type") == "Album"
                and (not sec or sec == ["Soundtrack"]
                     or (ist_live and sec == ["Live"]))
                and (rel.get("status") or "Official") == "Official"
                and (rel.get("date") or rg.get("first-release-date")))
    kandidaten = []                                  # (rang, datum, recording, release)
    for r in pool:
        for rel in (r.get("releases") or []):
            if _album_ok(rel):
                rg = rel.get("release-group") or {}
                sec = rg.get("secondary-types") or []
                rang = 0 if (ist_live and sec == ["Live"]) else (1 if ist_live else 0)
                kandidaten.append((rang,
                                   rel.get("date") or rg.get("first-release-date") or "9999",
                                   r, rel))
    kandidaten.sort(key=lambda x: (x[0], x[1]))
    rec = kandidaten[0][2] if kandidaten else pool[0]
    rel = kandidaten[0][3] if kandidaten else None
    album = (rel.get("title") or "") if rel else ""
    rg = (rel.get("release-group") or {}) if rel else {}
    jahr = ((rg.get("first-release-date") or (rel.get("date") if rel else "") or ""))[:4]
    release_id = (rel.get("id") or "") if rel else ""
    rg_id = rg.get("id") or ""
    time.sleep(1.1)                                  # MusicBrainz-Takt vor dem Lookup
    try:
        # Lookup nur noch für Künstler-Schreibweise + Genres — die Album-Wahl
        # ist oben schon gefallen (aus der Suche, ohne Extra-Abruf).
        det = _mb_get(f"https://musicbrainz.org/ws/2/recording/{rec['id']}"
                      "?inc=artist-credits+genres&fmt=json", timeout)
    except Exception:                                # noqa: BLE001 — Album ist trotzdem belegt
        return {"kuenstler": _mb_kuenstler(rec), "titel": rec.get("title", ""),
                "album": album, "jahr": jahr,
                "release_id": release_id, "rg_id": rg_id, "genre": ""}
    # Genre (Etappe A): live gemessen trägt das RECORDING fast nie Genres —
    # sie leben an der RELEASE-GROUP (Toto/Africa: Recording leer, RG „pop
    # rock" 10×). Darum ein Nachschlag — nur wenn ein Album gefunden wurde,
    # und nur das meistbestätigte Genre, hübsch geschrieben.
    # Nur Belegtes — falsche Tags wandern beim Kopieren mit (JB-Leitsatz).
    genres = sorted((det.get("genres") or []), key=lambda g: -(g.get("count") or 0))
    if not genres and rg_id:
        time.sleep(1.1)                              # MusicBrainz-Takt
        try:
            rgd = _mb_get(f"https://musicbrainz.org/ws/2/release-group/{rg_id}"
                          "?inc=genres&fmt=json", timeout)
            genres = sorted((rgd.get("genres") or []), key=lambda g: -(g.get("count") or 0))
        except Exception:                            # noqa: BLE001 — dann eben ohne Genre
            pass
    genre = (genres[0].get("name") or "").title() if genres else ""
    # Bei un-exaktem Titel-Treffer (z.B. „… (instrumental)") den EIGENEN gesäuberten
    # Titel behalten — das Album stimmt trotzdem.
    mb_titel = det.get("title", "") or rec.get("title", "")
    return {"kuenstler": _mb_kuenstler(det) or _mb_kuenstler(rec),
            "titel": mb_titel if exakt else titel,
            "album": album, "jahr": jahr,
            "release_id": release_id, "rg_id": rg_id, "genre": genre}


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
    if e.get("genre"):                                # Etappe A: nur BELEGTES Genre
        cmd += ["-metadata", f"genre={e['genre']}"]
    cmd += [tmp]
    try:
        subprocess.run(cmd, capture_output=True, timeout=120,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        if os.path.isfile(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, pfad)
            # ffmpeg hat die Datei NEU geschrieben: Id-Tag sichern (könnte im
            # Remux verloren gehen) und DANACH den Fingerabdruck erneuern —
            # sonst zeigt das gespeicherte fp auf einen Inhalt, den es nicht
            # mehr gibt (Bibliothek 2.0).
            if e.get("idtag"):
                e["idtag"] = _id_tag_schreiben(pfad, key.split("|")[0])
            with _io_lock:
                e["groesse"] = os.path.getsize(pfad)  # Größe in der DB nachziehen (Dubletten-Check!)
                if e.get("fp"):
                    e["fp"] = _fp_von(pfad)
                _geladen_speichern()
    except (OSError, subprocess.SubprocessError):
        pass
    finally:
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except OSError:
            pass


def _cover_holen(release_id, rg_id="", timeout=15):
    """Front-Cover vom Cover Art Archive (das öffentliche Bild-Archiv zu
    MusicBrainz — kein Key nötig). `front-500` ist groß genug für Player und
    TV-Kacheln und klein genug fürs Einbetten.
    Zwei Ebenen + Retry (live gemessen): direkt nach den MusicBrainz-Abrufen
    schlug der erste CAA-Zugriff transient fehl, derselbe Abruf klappte kurz
    darauf — und manche Releases haben kein eigenes Bild, ihre Release-GROUP
    aber schon (Rückfall-Ebene)."""
    import urllib.request
    urls = ([f"https://coverartarchive.org/release/{release_id}/front-500"]
            if release_id else [])
    if rg_id:
        urls.append(f"https://coverartarchive.org/release-group/{rg_id}/front-500")
    for url in urls:
        for versuch in (1, 2):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": MB_UA})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    daten = r.read()
                if 2000 < len(daten) < 10 * 1024 * 1024:   # Plausibilität: echtes Bild
                    return daten
                break                                 # zu klein/groß: nächste Ebene
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break                             # kein Bild auf dieser Ebene
                time.sleep(8)                         # Drossel/5xx: EIN längerer Retry
            except Exception:                        # noqa: BLE001 — Netz
                time.sleep(8)
    # Live gemessen (05.08., Massen-Lauf 0/35): CAA leitet auf archive.org um,
    # und das drosselt SERIEN-Abrufe hart — Einzelabrufe kurz danach liefern
    # dieselben Bilder problemlos. Darum der lange Retry; verpasste Cover holt
    # der nächste Lauf über die gespeicherten mb_release/mb_rg-Ids nach.
    return None


def _cover_in_datei(key, e, bild):
    """Echtes Album-Cover IN die MP3 — ersetzt das YouTube-Thumbnail des
    Downloads (Spec Punkt 5, Etappe A). Nicht-destruktiv wie _tags_in_datei:
    tmp + replace, bei jedem Fehler bleibt die Originaldatei unangetastet."""
    pfad = _pfad_zu_key(key)
    if not (bild and pfad and os.path.isfile(pfad)):
        return
    if not pfad.lower().endswith(".mp3"):
        # JB 05.08.: „Videos können Lieder sein" — Dateiart ist KEIN
        # Ausschluss. Remux wäre GB-teuer, darum Sidecar statt Einbetten.
        sc = _cover_sidecar(key)
        if not sc:
            return                                   # Schlüssel ohne schlichte Id: kein Sidecar
        try:
            os.makedirs(os.path.dirname(sc), exist_ok=True)
            with open(sc, "wb") as f:
                f.write(bild)
            with _io_lock:
                e["cover_album"] = True              # echtes Album-Cover liegt bereit
                _geladen_speichern()
        except OSError:
            pass
        return
    ff = os.path.join(BIN_DIR, "ffmpeg.exe")
    if not os.path.exists(ff):
        return                                       # ohne ffmpeg kein Einbetten
    cover = pfad + ".covertmp.jpg"
    tmp = pfad + ".covertmp.mp3"
    try:
        with open(cover, "wb") as f:
            f.write(bild)
        cmd = [ff, "-y", "-i", pfad, "-i", cover,
               "-map", "0:a", "-map", "1:0", "-c", "copy", "-id3v2_version", "3",
               "-metadata:s:v", "title=Album cover",
               "-metadata:s:v", "comment=Cover (front)", tmp]
        subprocess.run(cmd, capture_output=True, timeout=120,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        if os.path.isfile(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, pfad)
            # Datei neu geschrieben -> Id-Tag sichern, dann fp/Größe erneuern
            # (dieselbe Kette wie in _tags_in_datei, Bibliothek 2.0).
            if e.get("idtag"):
                e["idtag"] = _id_tag_schreiben(pfad, key.split("|")[0])
            with _io_lock:
                e["groesse"] = os.path.getsize(pfad)
                if e.get("fp"):
                    e["fp"] = _fp_von(pfad)
                e["cover_album"] = True               # echtes Album-Cover eingebettet
                _geladen_speichern()
    except (OSError, subprocess.SubprocessError):
        pass
    finally:
        for t in (cover, tmp):                        # Arbeits-Reste immer wegräumen
            try:
                if os.path.exists(t):
                    os.remove(t)
            except OSError:
                pass


_ID_NAME = re.compile(r"[\w-]{1,64}")                 # YouTube-Id, lokal-<hash>, [Id] aus dem Dateinamen


def _id_datei(ordner, vid, endung):
    """`<ordner>/<vid><endung>` für eine schlichte Id, sonst None (Gesamt-
    prüfung S4). Die Id stammt aus der Anfrage (/api/cover, /api/untertitel):
    `..`, eine Laufwerksangabe oder ein UNC-Pfad hätten den Ordner verlassen
    bzw. Windows ein Netzlaufwerk anfragen lassen. Downloads, die nicht von
    YouTube stammen (die ganze URL ist der Schlüssel), fallen hier heraus und
    behalten ihren Rückfall über die Datei in der Bibliothek."""
    if not _ID_NAME.fullmatch(vid or ""):
        return None
    wurzel = os.path.abspath(ordner)
    pfad = os.path.join(wurzel, vid + endung)
    try:
        if os.path.commonpath([wurzel, os.path.abspath(pfad)]) != wurzel:
            return None
    except ValueError:                                # anderes Laufwerk
        return None
    return pfad


def _cover_sidecar(key):
    """Sidecar-Pfad fürs Album-Cover eines VIDEOS (JB 05.08.: „Videos können
    Lieder sein" — die Dateiart ist kein Ausschluss). In die Videodatei
    remuxen wäre GB-teuer; das Bild liegt darum als `<video-id>.jpg` im
    Cover-Ordner — magnetisch über die Id, wie die Untertitel.
    None für einen Schlüssel ohne schlichte Id (s. `_id_datei`)."""
    return _id_datei(os.path.join(ziel_ordner(), "Cover"), key.split("|")[0], ".jpg")


def cover_aus_datei(key):
    """Echtes Album-Cover für /api/cover: aus der MP3 (APIC) oder — bei
    Videos — aus dem Sidecar; Player/Kacheln zeigen es statt des Thumbnails."""
    pfad = _pfad_zu_key(key)
    if pfad and os.path.isfile(pfad) and pfad.lower().endswith(".mp3"):
        try:
            from mutagen.id3 import ID3
            tags = ID3(pfad)
            for k in tags.keys():
                if k.startswith("APIC"):
                    return bytes(tags[k].data)
        except Exception:                            # noqa: BLE001 — kein/valides Tag
            pass
        return None
    sc = _cover_sidecar(key)
    if sc and os.path.isfile(sc):
        try:
            with open(sc, "rb") as f:
                return f.read()
        except OSError:
            pass
    return None


_autotag = {"laeuft": False, "gesamt": 0, "erledigt": 0, "getaggt": 0}
_autotag_lock = threading.Lock()
# Was während eines Laufs angefragt wird (Gesamtprüfung F8): vorher verwarf
# autotag_lauf den Auftrag still, ein Download, der während des Taggens fertig
# wurde, blieb ungetaggt. Jetzt arbeitet der laufende Lauf das am Ende ab.
# Einen Voll-Lauf holt er nur hinter einem Schlüssel-Durchgang nach: während
# eines Voll-Durchgangs ist ein weiterer Voll-Klick schon abgedeckt, was danach
# fertig wird, kommt als Schlüssel (`jetzt_voll` sagt, welcher Durchgang läuft).
_autotag_nachholen = {"keys": set(), "voll": False, "jetzt_voll": False}


def autotag_lauf(keys=None):
    """Auto-Tagging im Hintergrund: Kandidat raten -> MusicBrainz -> DB-Felder
    (kuenstler/album/track/jahr) + Tags in die MP3. Ohne keys: alle Musik ohne Album.
    Läuft schon einer, merkt er sich den Auftrag und holt ihn am Ende nach (F8)."""
    with _autotag_lock:
        if _autotag.get("laeuft"):
            if keys is not None:
                _autotag_nachholen["keys"].update(keys)
            elif not _autotag_nachholen["jetzt_voll"]:
                _autotag_nachholen["voll"] = True
            return
        _autotag.update({"laeuft": True, "gesamt": 0, "erledigt": 0, "getaggt": 0})
        _autotag_nachholen["jetzt_voll"] = keys is None
    sauber_beendet = False
    try:
        while True:                                  # ein Durchgang je Auftrag, Nachgeholtes danach
            # Ohne keys zwei Gruppen: (1) Musik ohne Album -> volle MB-Suche;
            # (2) schon Getaggtes mit gespeicherten MB-Ids, dem nur das Cover
            # fehlt -> NUR Cover nachziehen, ohne neue MB-Suche und ohne die
            # Tags anzufassen (CAA drosselt Serien — live gemessen 0/35; so
            # heilt sich der Rückstand bei jedem späteren Lauf von selbst).
            alle = list(keys) if keys else [k for k, e in _geladen_schnappschuss()
                                            if musik_einstufung._ist_musik(e) and not e.get("album")]
            # Auch Videos (JB 05.08.: „Videos können Lieder sein") — ihr Cover
            # landet als Sidecar; cover_album=True stoppt Wiederholungen.
            nur_cover = [] if keys else [k for k, e in _geladen_schnappschuss()
                                         if e.get("album") and not e.get("cover_album")
                                         and (e.get("mb_release") or e.get("mb_rg")
                                              or e.get("cover_url"))
                                         and k not in alle]
            _autotag["gesamt"] += len(alle) + len(nur_cover)   # Nachhol-Durchgänge zählen dazu
            for k in nur_cover:
                e = _geladen.get(k)
                _autotag["erledigt"] += 1
                if not e or e.get("cover_album"):
                    continue
                bild = _cover_holen(e.get("mb_release", ""), e.get("mb_rg", ""))
                if not bild:
                    bild = _bild_laden(e.get("cover_url") or "")
                if bild:
                    _cover_in_datei(k, e, bild)
                    if e.get("cover_album"):             # ehrlich: nur EINGEBETTETE zählen
                        _autotag["getaggt"] += 1
                time.sleep(2)                            # CAA-Takt (Serien-Drossel)
            for k in alle:
                e = _geladen.get(k)
                _autotag["erledigt"] += 1
                if not e:
                    continue
                ku, ti = musik_einstufung._tag_kandidat(e)
                # Live-Hinweis IMMER aus dem ORIGINAL-Dateititel (Relauf-Falle,
                # live gemessen: der Kandidat kommt aus den schon getaggten
                # Feldern — „(Live On MTV Unplugged)" war da längst abgestreift,
                # und die Live-Regel kam nie zum Zug).
                live = musik_einstufung._ist_live_titel(e.get("titel") or "") or musik_einstufung._ist_live_titel(ti)
                fund = _mb_suche(ku, ti, live_hinweis=live)
                time.sleep(1.5)                          # MusicBrainz-Regel: max 1 Anfrage/Sekunde (+Puffer)
                if not fund:
                    # Build 136: zweiter Versuch ohne Klammer-Zusätze — die sind
                    # der häufigste Grund, warum ein Titel nicht gefunden wird.
                    blank = musik_einstufung._titel_kern(ti)
                    if blank != ti:
                        fund = _mb_suche(ku, blank, live_hinweis=live)
                        time.sleep(1.5)
                # iTunes-Rückfall (JB 05.08., „viele Lieder ohne richtige Cover/
                # Titel"): MusicBrainz fand nichts oder kein Album — die offene
                # iTunes-Suche ergänzt NUR leere Felder (nichts überschreiben).
                if not fund or not fund.get("album"):
                    it = _itunes_suche(ku, musik_einstufung._titel_kern(ti))
                    if not it:
                        # Vertauschte Reihenfolge probieren („Mr. Sandman - The
                        # Chordettes": der Kandidat riet Künstler und Titel
                        # falsch herum). Der strenge Titel+Künstler-Abgleich
                        # macht das SICHER — nur die richtige Reihenfolge trifft.
                        it = _itunes_suche(musik_einstufung._titel_kern(ti), ku)
                        if it:                            # Fund in Wahrheit vertauscht
                            ku, ti = musik_einstufung._titel_kern(ti), ku
                    if it:
                        if not fund:
                            fund = it
                        else:
                            for feld in ("album", "jahr", "genre"):
                                if not fund.get(feld) and it.get(feld):
                                    fund[feld] = it[feld]
                            fund["cover_url"] = it.get("cover_url", "")
                if not fund:
                    continue
                with _io_lock:
                    e["kuenstler"] = fund["kuenstler"] or ku
                    e["album"] = fund["album"]
                    e["track"] = fund["titel"] or ti
                    if fund.get("jahr"):
                        e["jahr"] = fund["jahr"]
                    if fund.get("genre"):                 # Etappe A: nur Belegtes
                        e["genre"] = fund["genre"]
                    # MB-Ids merken: der Cover-Nachzug (oben) braucht sie, um
                    # ohne neue MusicBrainz-Suche ans Bild zu kommen.
                    if fund.get("release_id"):
                        e["mb_release"] = fund["release_id"]
                    if fund.get("rg_id"):
                        e["mb_rg"] = fund["rg_id"]
                    if fund.get("cover_url"):             # iTunes-Artwork für den Nachzug
                        e["cover_url"] = fund["cover_url"]
                    _geladen_speichern()
                _autotag["getaggt"] += 1
                _tags_in_datei(k, e)
                # Etappe A: echtes Album-Cover (MP3: eingebettet, Video: Sidecar —
                # JB 05.08.: Dateiart ist kein Ausschluss). Kette: Cover Art
                # Archive, dann iTunes-Artwork; kein Bild ist kein Fehler.
                if not e.get("cover_album"):
                    bild = None
                    if fund.get("release_id") or fund.get("rg_id"):
                        bild = _cover_holen(fund.get("release_id", ""), fund.get("rg_id", ""))
                    if not bild:
                        bild = _bild_laden(fund.get("cover_url") or e.get("cover_url") or "")
                    if bild:
                        _cover_in_datei(k, e, bild)
            with _autotag_lock:
                if _autotag_nachholen["keys"]:
                    keys = sorted(_autotag_nachholen["keys"])
                    _autotag_nachholen["keys"].clear()
                elif _autotag_nachholen["voll"]:
                    keys = None
                    _autotag_nachholen["voll"] = False
                else:
                    _autotag["laeuft"] = False       # im selben Schritt wie die letzte Prüfung
                    sauber_beendet = True
                    return
                _autotag_nachholen["jetzt_voll"] = keys is None
    finally:
        # Nur nach einer Ausnahme: am normalen Ende ist der Merker schon frei,
        # und ein zweites Freigeben nähme ihn einem inzwischen gestarteten Lauf.
        if not sauber_beendet:
            with _autotag_lock:
                _autotag["laeuft"] = False


def _untertitel_sprachen():
    """Welche Untertitel-Sprachen automatisch mitgeladen werden (JB Punkt 6).

    CFG `untertitel_sprachen` = Liste von Kennungen („de", „en-GB", …);
    „orig" steht für yt-dlps `.*-orig` — die UNübersetzte Auto-Spur des
    Videos (wichtig fürs Karaoke: authentisch, als Romaji angezeigt).
    Ohne eigene Wahl bleibt exakt das Bestandsverhalten: de, en, Original.
    Werte kommen über /api/config von außen — deshalb streng filtern.
    """
    roh = CFG.get("untertitel_sprachen") or []
    sprachen = []
    for s in roh:
        if not isinstance(s, str):
            continue
        s = s.strip()
        if s == "orig":
            sprachen.append(".*-orig")
        elif re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?", s):
            sprachen.append(s)
    return sprachen or ["de", "en", ".*-orig"]


# ---- Untertitel: .vtt neben der Mediendatei finden bzw. nachladen ----

def _vtt_sprache(pfad):
    m = re.search(r"\.([A-Za-z0-9-]+)\.(?:vtt|srt)$", pfad)
    return m.group(1) if m else ""


def _srt_zu_vtt(text):
    """SubRip → WebVTT: Kopfzeile dazu, Komma-Millisekunden → Punkt. Mehr
    unterscheidet die Formate für unseren Player-Parser nicht."""
    text = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", text)
    return "WEBVTT\n\n" + text.lstrip("﻿")


def untertitel_ordner():
    """Ein eigener Ordner für ALLE Untertitel (JB 21.07.: nicht bei den Videos).
    Verknüpfung läuft über die Video-ID im Dateinamen (`<id>.<sprache>.vtt`) —
    magnetisch: überlebt Umbenennen/Verschieben der Videodatei."""
    d = os.path.join(ziel_ordner(), "Untertitel")
    os.makedirs(d, exist_ok=True)
    return d


def untertitel_liste(key):
    """Alle .vtt-Dateien zu einem Bibliotheks-Key als [(pfad, sprache)], sortiert:
    ORIGINAL-Sprache (…-orig, fürs Karaoke) vor Deutsch vor Englisch vor Rest.
    Bevorzugt den Untertitel-Ordner (nach Video-ID); Altbestand neben dem Video
    bleibt Rückfallebene, bis der Einsortier-Lauf ihn verschoben hat.
    Im Untertitel-Ordner wird nur mit einer schlichten Id gesucht (S4, s.
    `_id_datei`); der Rückfall geht über die Bibliothek, nie über die Anfrage:
    erst neben der Datei, dann (Gruppe 6) mit der Id der Datei selbst
    (`_datei_videoid`) im Untertitel-Ordner. So finden auch Downloads, deren
    Schlüssel die ganze URL ist, ihre Untertitel nach dem Einsortieren."""
    vid = key.split("|")[0]
    ordner = untertitel_ordner()

    def im_ordner(v):
        if not _id_datei(ordner, v, ".vtt"):
            return []
        return glob.glob(os.path.join(glob.escape(ordner), glob.escape(v) + ".*.vtt"))
    dateien = im_ordner(vid)
    if not dateien:
        pfad = _pfad_zu_key(key)
        if pfad:
            dateien = glob.glob(glob.escape(os.path.splitext(pfad)[0]) + ".*.vtt")
            datei_vid = "" if dateien else _datei_videoid(pfad)
            if datei_vid and datei_vid != vid:
                dateien = im_ordner(datei_vid)
    if not dateien:
        return []

    def rang(f):
        s = _vtt_sprache(f).lower()
        return 0 if s.endswith("-orig") else (1 if s.startswith("de") else (2 if s.startswith("en") else 3))
    dateien.sort(key=rang)
    return [(f, _vtt_sprache(f)) for f in dateien]


def untertitel_einsortieren():
    """Verschiebt .vtt-Dateien, die noch bei den Videos liegen, in den
    Untertitel-Ordner (`<video-id>.<sprache>.vtt`). Additiv, nie hart löschen:
    liegt am Ziel schon dieselbe Sprache, wandert die Kopie in den Papierkorb."""
    ziel = untertitel_ordner()
    n = 0
    for wurzel, _, dateien in _walk_ohne_rueckhol(ziel_ordner()):
        if os.path.normcase(wurzel) == os.path.normcase(ziel):
            continue                                  # den Zielordner selbst überspringen
        for d in dateien:
            unten = d.lower()
            if not unten.endswith((".vtt", ".srt")):
                continue
            m = re.search(r"\[([\w-]{6,})\]", d)
            if not m:
                continue                              # ohne Video-ID -> Rückfallebene greift
            quelle = os.path.join(wurzel, d)
            zdatei = os.path.join(ziel, f"{m.group(1)}.{_vtt_sprache(d) or 'und'}.vtt")
            try:
                if os.path.exists(zdatei):
                    _in_papierkorb(quelle)            # Dublette -> Papierkorb (nicht hart löschen)
                elif unten.endswith(".srt"):
                    # SubRip unterwegs nach WebVTT wandeln (der Player liest
                    # VTT); das Original geht rückholbar in den Papierkorb.
                    with open(quelle, encoding="utf-8", errors="replace") as f:
                        text = f.read()
                    with open(zdatei, "w", encoding="utf-8") as f:
                        f.write(_srt_zu_vtt(text))
                    _in_papierkorb(quelle)
                else:
                    os.replace(quelle, zdatei)
                n += 1
            except OSError:
                pass
    if n:
        _sag(f"Untertitel einsortiert: {n} .vtt in den Untertitel-Ordner verschoben")
    return n


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


def _vtt_cues(pfad):
    """VTT-Datei -> [(startsekunden, text)], Inline-Tags raus, rollende
    Auto-Untertitel-Dubletten zusammengefasst."""
    try:
        with open(pfad, encoding="utf-8", errors="replace") as fh:
            roh = fh.read()
    except OSError:
        return []
    cues, letzte = [], None
    for block in re.split(r"\n\n+", roh.replace("\r", "")):
        zeilen = [z for z in block.split("\n") if z]
        ti = next((i for i, z in enumerate(zeilen) if "-->" in z), -1)
        if ti < 0:
            continue
        m = re.search(r"(\d+):(\d+):(\d+(?:\.\d+)?)", zeilen[ti])
        if not m:
            continue
        sek = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        import html as _html
        txt = _html.unescape(re.sub(r"<[^>]*>", "", " ".join(zeilen[ti + 1:])))
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt and txt != letzte:
            cues.append((sek, txt))
            letzte = txt
    return cues


def _lrc_cues(lrc):
    """LRCLIB-Text [mm:ss.xx] -> [(startsekunden, text)]."""
    out = []
    for zeile in (lrc or "").split("\n"):
        txt = re.sub(r"\[[^\]]*\]", "", zeile).strip()
        if not txt:
            continue
        for m in re.finditer(r"\[(\d+):(\d+(?:\.\d+)?)\]", zeile):
            out.append((int(m.group(1)) * 60 + float(m.group(2)), txt))
    return out


def transkript_suche(q, limit=40):
    """Volltextsuche über ALLE lokalen Transkripte: heruntergeladene Untertitel
    (.vtt) UND die synchronisierten LRCLIB-Songtexte (Tube-Archivist-Muster).
    Findet, in welchem Titel ein Begriff wann gesagt/gesungen wird.
    -> [{key, titel, quelle, treffer:[{zeit, text}]}] (nur Titel MIT Treffern)."""
    q = (q or "").strip().lower()
    if len(q) < 2:
        return []
    meta_liste, cue_liste = [], []
    for key, e in _geladen_schnappschuss():
        # Build 107 (JB-Fund „nvidia"): TITEL/Künstler/Kanal zählen MIT — im
        # NVIDIA-Video wird „nvidia" nie GESAGT; Meta-Treffer stehen vorn.
        meta_hit = q in " ".join(str(e.get(f) or "") for f in
                                 ("titel", "name", "kuenstler", "uploader")).lower()
        cues, quelle = [], ""
        f, _ = untertitel_datei(key)
        if f:
            cues, quelle = _vtt_cues(f), "Untertitel"
        if not cues and _lyrics.get(key):            # kein .vtt -> LRCLIB-Songtext durchsuchen
            cues, quelle = _lrc_cues(_lyrics[key]), "Lyrics"
        rein = []
        for sek, txt in cues:
            if q in txt.lower():
                rein.append({"zeit": round(sek, 1), "text": txt})
                if len(rein) >= 8:                    # pro Titel höchstens 8 Fundstellen
                    break
        if meta_hit:
            rein.insert(0, {"zeit": 0, "text": "🏷 im Titel/Künstler/Kanal gefunden"})
            meta_liste.append({"key": key, "titel": e.get("titel") or key,
                               "quelle": quelle or "Titel", "treffer": rein})
        elif rein:
            cue_liste.append({"key": key, "titel": e.get("titel") or key,
                              "quelle": quelle, "treffer": rein})
        if len(meta_liste) + len(cue_liste) >= limit:
            break
    return (meta_liste + cue_liste)[:limit]


def untertitel_nachladen(key):
    """Untertitel für einen vorhandenen Titel nachträglich von YouTube holen
    (nur die .vtt, kein Video-Download). Läuft im Hintergrund-Thread."""
    e = _geladen.get(key)
    pfad = _pfad_zu_key(key)
    if not (e and pfad):
        return
    vid = key.split("|")[0]
    url = e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if links._plausible_id(vid) else "")
    ordner = untertitel_ordner()
    if not (url and _id_datei(ordner, vid, "")):      # Ziel nur mit schlichter Id (S4)
        return
    ziel = os.path.join(ordner, vid)                  # -> Untertitel-Ordner, nach Video-ID
    opts = _ydl_basis_opts()
    opts.update({"skip_download": True, "noplaylist": True,
                 "writesubtitles": True, "writeautomaticsub": True,
                 "subtitleslangs": _untertitel_sprachen(), "subtitlesformat": "vtt/best",
                 "outtmpl": {"default": ziel + ".%(ext)s"}})   # .vtt landet im Untertitel-Ordner
    _nebenweg_abruf(opts, url, "untertitel", download=True)   # skip_download: nur Untertitel


# ---- Synchronisierte Lyrics via LRCLIB (lrclib.net, kein API-Key) ----
#      Ergänzt die YouTube-Untertitel fürs Musik-Karaoke: echte, zeilengenaue
#      Songtexte. Rein lesend, Ergebnis-Cache neben dem Code (keine Fremddaten).

LYRICS_CACHE = os.path.join(DATEN_DIR, "lyrics_cache.json")
_lyrics = _json_laden(LYRICS_CACHE, {})
if not isinstance(_lyrics, dict):
    _lyrics = {}


def _lrclib_get(artist, titel, album, dauer):
    """Einen Song bei LRCLIB abfragen -> synced LRC (oder '')."""
    from urllib.parse import urlencode
    basis = "https://lrclib.net/api/"
    kopf = {"User-Agent": "SyncYouTube (https://github.com/schn4ppi/SyncYouTube)"}

    def hol(pfad, params):
        try:
            req = urllib.request.Request(basis + pfad + "?" + urlencode(params), headers=kopf)
            return json.loads(urllib.request.urlopen(req, timeout=12).read().decode("utf-8", "replace"))
        except Exception:                            # noqa: BLE001 — 404/Netz
            return None

    params = {"artist_name": artist, "track_name": titel}
    if album:
        params["album_name"] = album
    if dauer:
        params["duration"] = int(dauer)
    d = hol("get", params)                           # exakter Treffer (mit Dauer-Toleranz serverseitig)
    if not (d and d.get("syncedLyrics")):
        treffer = hol("search", {"artist_name": artist, "track_name": titel}) or []
        d = next((t for t in treffer if t.get("syncedLyrics")), None)
    return (d or {}).get("syncedLyrics") or "" if d else ""


def lyrics_holen(key):
    """Synchronisierte Lyrics zu einem Bibliotheks-Key (LRCLIB), gecacht.
    Leer, wenn kein Künstler/Titel bekannt oder nichts gefunden."""
    e = _geladen.get(key)
    if not e:
        return ""
    if key in _lyrics:
        return _lyrics[key]                          # Cache (auch "" = „nichts gefunden", nicht neu fragen)
    artist = (e.get("kuenstler") or e.get("uploader") or "").strip()
    titel = (e.get("track") or e.get("titel") or "").strip()
    if not (artist and titel):
        return ""
    lrc = _lrclib_get(artist, titel, e.get("album") or "", e.get("dauer") or 0)
    with _io_lock:
        _lyrics[key] = lrc
        _json_speichern(LYRICS_CACHE, _lyrics)
    return lrc


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

# Addon-Nachschub (v1.2.0, JB 05.08.): das Firefox-Addon merkt sich Klicks,
# während die App aus ist, und reicht sie beim nächsten Start nach — die App
# zeigt dann EINMAL „x vorgemerkte Downloads werden geholt" (id-Zähler, das
# UI toastet je id genau einmal; Muster wie _remote).
_addon_nachschub = {"n": 0, "ts": 0, "id": 0}


def addon_nachschub(daten):
    n = int(daten.get("n") or 0)
    if n > 0:
        _addon_nachschub["n"] = n
        _addon_nachschub["ts"] = time.time()
        _addon_nachschub["id"] += 1
    return {"ok": True}


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


# ---- VLC-Motor (Spec Punkt 5, Etappe B Stufe 1): VLC als Ausgabegerät ------
# Der Browser bleibt das Gehirn (Warteschlange, Weiterschalten, Oberfläche) —
# der Ton kommt wahlweise aus einer ferngesteuerten VLC-Instanz auf dem PC
# (python-vlc/libvlc, Spotify-Connect-Muster). Kein VLC installiert ⇒
# ehrlicher Hinweis, der Browser-Player spielt weiter (Rückfall).

_vlc = {"instanz": None, "spieler": None, "key": "", "grund": "", "vol_wunsch": None,
        "hwnd": 0,                                   # Hüllen-Fenster (set_hwnd, Etappe set_hwnd)
        "hwnd_pid": 0,                               # ... und der Prozess, dem es gehört
        "hwnd_spiel": 0,                             # Fenster, in das das LAUFENDE Medium rendert
        "pause_seit": None}                          # Beginn der laufenden Pause (_pause_uhr)
_vlc_lock = threading.RLock()   # RLock: die Selbstheilung wiederholt den Befehl im Lock


_user32_pruefung = None


def _hwnd_lebt(hwnd, pid=0):
    """Lebt das Hüllen-Fenster noch, und gehört es dem gemeldeten Prozess?
    (Befund 24.09.: eine abgestürzte oder geschlossene Hülle hinterließ ihr
    Handle, das nächste Video renderte ins tote Fenster und Filme verloren
    ihr Vollbild.) IsWindow allein reicht nicht — Windows vergibt Handles
    neu —, darum der PID-Abgleich, sobald die Hülle ihre PID mitschickt.
    Scheitert die Prüfung selbst, gilt wie bisher: Handle behalten."""
    global _user32_pruefung
    if not hwnd:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        u32 = _user32_pruefung
        if u32 is None:                              # eigene Bibliothek: argtypes nie global
            u32 = ctypes.WinDLL("user32")
            u32.IsWindow.argtypes = [wintypes.HWND]
            u32.IsWindow.restype = wintypes.BOOL
            u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                                     ctypes.POINTER(wintypes.DWORD)]
            u32.GetWindowThreadProcessId.restype = wintypes.DWORD
            _user32_pruefung = u32
        if not u32.IsWindow(hwnd):
            return False
        if pid:
            besitzer = wintypes.DWORD(0)
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(besitzer))
            return besitzer.value == int(pid)
        return True
    except Exception:                                # noqa: BLE001 — Prüfung ist Kür
        return True


def _hwnd_gueltig():
    """Das gemerkte Hüllen-Fenster, falls es noch lebt — ein totes oder
    fremd gewordenes Handle wird vergessen (0 = VLCs eigenes Fenster)."""
    h = _vlc.get("hwnd") or 0
    if h and not _hwnd_lebt(h, _vlc.get("hwnd_pid") or 0):
        _vlc["hwnd"] = h = 0
        _vlc["hwnd_pid"] = 0
    return h


def _fenster_merken(daten):
    """Befehl 'fenster' der Hülle: das Handle merken — IMMER und vor jedem
    libvlc-Laden (fehlte VLC, ging es bisher verloren, obwohl die Hülle es
    für gemeldet hielt; ein später installiertes VLC bettete nie ein).
    'nur_wenn' = vergleichen und löschen: die Hülle meldet beim Schließen nur
    IHR Fenster ab, nie das einer anderen offenen Hülle. False = unverändert."""
    def zahl(wert):
        try:
            return int(wert or 0)
        except (TypeError, ValueError):
            return 0
    if daten.get("nur_wenn") is not None and zahl(daten["nur_wenn"]) != (_vlc.get("hwnd") or 0):
        return False
    h = zahl(daten.get("hwnd"))
    _vlc["hwnd"] = h
    _vlc["hwnd_pid"] = zahl(daten.get("pid")) if h else 0
    return True


def _vlc_zeigt_bild(key):
    """Zeigt dieser VLC-Titel ein Bild? film:/live: sind Videoströme; ein
    Bibliotheks-Titel ist ein Video, wenn seine Datei keine Audio-Datei ist —
    dieselbe Grenze wie 'dateiart' in bibliothek_liste, nach der die Seite
    ihr Video-Panel zeigt (huelleVideoRect)."""
    if key.startswith(("film:", "live:")):
        return True
    pfad = _pfad_zu_key(key) if key else None
    return bool(pfad) and not pfad.lower().endswith(musik_einstufung.AUDIO_EXT)


def _video_im_panel_pausieren(panel):
    """Hülle zu (JB 24.09.2026: „Pausieren", Musik läuft in jedem Fall
    weiter): läuft gerade ein VIDEO in genau dieses Panel, hart pausieren —
    pausiert, nicht gestoppt, die Stelle bleibt. Sonst liefe es ins zerstörte
    Fenster weiter: hörbar, aber unsichtbar. Maßgeblich ist das Fenster, das
    beim Start des laufenden Mediums galt (hwnd_spiel), nicht das gerade
    angemeldete: set_hwnd wirkt erst beim nächsten Medium, ein Video von vor
    der Anmeldung zeigt VLCs eigenes Fenster und läuft weiter. „Läuft" heißt
    spielt, öffnet oder puffert (ein ladender Film spielte gleich ins Leere).
    set_pause(1) statt toggle: ein schon pausiertes Video bliebe sonst nicht
    stehen. Nur unter _vlc_lock rufen. True = pausiert.

    Ein Jellyfin-Film meldet dabei seine Stelle (Prüfung Runde 2, s.
    _film_stelle_melden): mit der Hülle geht auch die Seite — sie meldet beim
    Entladen selbst, der Server nur als Rückfall, gekappt (Nacharbeit Runde 3)."""
    try:
        panel = int(panel or 0)
    except (TypeError, ValueError):
        return False
    sp = _vlc["spieler"]
    if not panel or sp is None or (_vlc.get("hwnd_spiel") or 0) != panel:
        return False
    key = _vlc.get("key") or ""
    try:
        # Im Schirm (Prüfung Runde 2): _vlc_zeigt_bild sucht eine verschobene
        # Datei per os.walk — warf das, fiel auch das Abmelden aus (HTTP 500).
        if not _vlc_zeigt_bild(key):
            return False
        import vlc
        if sp.get_state() not in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering):
            return False
        sp.set_pause(1)
    except Exception:                                # noqa: BLE001 — abgemeldet wird trotzdem
        return False
    _film_stelle_melden(sp, key)
    return True


# Hülle zu (Nacharbeit Runde 3): die SEITE meldet beim Entladen selbst
# (oberflaeche.py filmAbschied — sie kennt die Mindest-Sehzeit). Der Server wartet
# kurz auf diese Meldung und meldet nur, wenn sie ausbleibt, und dann nur eine
# Stelle UNTER Jellyfins „gesehen"-Grenze — kein „gesehen" ohne Sehzeit-Beleg.
HUELLE_GNADE_S = 2.0         # so lange wartet der Rückfall nach dem Pausieren auf die Seite
HUELLE_VORLAUF_S = 10.0      # so kurz VOR dem Pausieren zählt ihre Meldung mit (pagehide kommt zuerst)
# Jellyfins Grenze, dieselbe wie SEHZEIT in oberflaeche.py (jfMaxResume, jfKurzS,
# jfSpielraumS; Gleichheit am Ergebnis geprüft in test_mindest_sehzeit.py).
JF_MAX_RESUME, JF_KURZ_S, JF_SPIELRAUM_S = 0.9, 300, 30
_seiten_meldung = {}         # Film-Kennung -> time.monotonic() der letzten Meldung der Seite
_seiten_meldung_cv = threading.Condition()


def _seiten_meldung_merken(item_id):
    """Die Seite hat für diesen Film gemeldet (/api/filme/fortschritt) — ein
    wartender Hüllen-Rückfall für denselben Film schweigt dann."""
    if not item_id:
        return
    with _seiten_meldung_cv:
        jetzt = time.monotonic()
        for k in [k for k, t in _seiten_meldung.items() if jetzt - t > 600]:
            del _seiten_meldung[k]                   # nicht endlos wachsen
        _seiten_meldung[item_id] = jetzt
        _seiten_meldung_cv.notify_all()


def _seite_hat_gemeldet(item_id, t0):
    """Wartet bis HUELLE_GNADE_S nach t0 auf eine Meldung der Seite für diesen
    Film. True, wenn eine kam — auch eine bis HUELLE_VORLAUF_S VOR t0."""
    frist = t0 + HUELLE_GNADE_S
    with _seiten_meldung_cv:
        while True:
            if _seiten_meldung.get(item_id, float("-inf")) >= t0 - HUELLE_VORLAUF_S:
                return True
            rest = frist - time.monotonic()
            if rest <= 0:
                return False
            _seiten_meldung_cv.wait(rest)


def _stelle_unter_jf_grenze(pos_s, laenge_s):
    """Die Stelle, die Jellyfin sicher NICHT selbst zum „gesehen"-Haken bringt
    (12.1, UserDataManager.UpdatePlayState: > 90 % der Laufzeit, ab Laufzeit − 1 s,
    unter 5 min Laufzeit schon ab 5 %). Gerechnet wie die Seite: Grenze
    floor(0,9 × (Länge − 30 s)), bei weniger als 300 s: 0. Ohne bekannte Länge
    (libvlc −1/0) lässt sich keine Grenze beweisen: 0. Gerundet wie Math.round."""
    if not laenge_s or laenge_s <= 0:
        return 0
    laufzeit = laenge_s - JF_SPIELRAUM_S
    grenze = 0 if laufzeit < JF_KURZ_S else math.floor(JF_MAX_RESUME * laufzeit)
    return max(0, min(int(math.floor(pos_s + 0.5)), grenze))


def _film_stelle_melden(sp, key):
    """Hülle zu mit einem Jellyfin-Film im Panel (Prüfung Runde 2): die Stelle
    an Jellyfin, über DIESELBE Meldestelle wie /api/filme/fortschritt. Vorher
    stand der Film nur pausiert im Server-VLC — Jellyfin und „Weiterschauen"
    behielten die alte Stelle, und nach der Neustart-Sperre (30 Min) oder beim
    Herunterfahren war sie weg.

    Nacharbeit Runde 3: Das Schließen im Abspann ist dieselbe Art Beenden wie
    Esc (Entscheidung des Hauptagenten, analog zu JBs Regel vom 24.09.); ob es
    „gesehen" ist, entscheidet die Mindest-Sehzeit, und die kennt nur die Seite.
    Sie meldet beim Entladen selbst (filmAbschied). Dieser Rückfall wartet bis
    HUELLE_GNADE_S auf ihre Meldung und schweigt, wenn sie kam. Sonst meldet er
    die Stelle unter Jellyfins Grenze (vorher die rohe Stelle: über 90 % setzte
    Jellyfin „gesehen" selbst), nie „gesehen". Nichts, wenn die Stelle 0 wäre:
    ein Film, der noch öffnet, ein kurzes Stück (Grenze 0) oder eine unbekannte
    Länge — eine 0 setzte nur die Weiterschauen-Stelle zurück.
    Gemeldet wird in einem eigenen Faden: Warten und Jellyfin (bis 15 s) dürfen
    _vlc_lock nicht halten. Unter _vlc_lock rufen (libvlc-Rufe)."""
    if not key.startswith("film:") or len(key) <= 5:
        return
    try:
        ms, laenge_ms = int(sp.get_time() or 0), int(sp.get_length() or 0)
    except Exception:                                # noqa: BLE001 — ohne Stelle nichts zu melden
        return
    pos = _stelle_unter_jf_grenze(ms / 1000, laenge_ms / 1000) if ms > 0 else 0
    if pos <= 0:
        return

    def senden(item_id=key[5:], t0=time.monotonic()):
        if _seite_hat_gemeldet(item_id, t0):
            return                                   # die Seite kennt die Sehzeit: ihr Urteil gilt
        try:
            filme.fortschritt(item_id, pos, gesehen=False)   # scheitert es, reiht filme es ein
        except Exception:                            # noqa: BLE001 — die Hülle ist schon zu
            pass
    threading.Thread(target=senden, daemon=True, name="film-stelle-huelle").start()


def _vlc_reset():
    """Kaputte libvlc-Instanz wegwerfen (JB: „Kann er das selbstständig
    resetten?") — der nächste Befehl baut frisch auf. Nicht-destruktiv:
    betrifft nur den Player-Prozessteil, nie Dateien."""
    for feld in ("spieler", "instanz"):
        obj = _vlc.get(feld)
        if obj is not None:
            try:
                obj.release()
            except Exception:                        # noqa: BLE001 — schon tot ist auch ok
                pass
    _vlc.update(instanz=None, spieler=None, key="", grund="", pause_seit=None)


def _vlc_spieler():
    """libvlc lazy laden; (spieler, "") oder (None, grund). Wird bewusst bei
    jedem Fehlversuch NEU probiert (billig — ImportError kommt sofort), damit
    ein nachträglich installiertes VLC ohne App-Neustart greift."""
    if _vlc["spieler"] is not None:
        return _vlc["spieler"], ""
    try:
        import vlc                       # python-vlc findet libvlc über die VLC-Installation
        inst = vlc.Instance("--intf", "dummy", "--quiet")
        sp = inst.media_player_new() if inst else None
        if sp is None:
            raise RuntimeError("libvlc lieferte keinen Player")
        _vlc.update(instanz=inst, spieler=sp, grund="")
        _vlc_ereignisse_anhaengen(sp)                # auch nach jedem Neuaufbau (Selbstheilung)
        h = _hwnd_gueltig()                          # nur ein noch lebendes Hüllen-Fenster
        if h:                                        # Hüllen-Einbettung überlebt den Neuaufbau
            try:
                sp.set_hwnd(h)
            except Exception:                        # noqa: BLE001 — dann eigenes Fenster
                pass
        return sp, ""
    except Exception:                    # noqa: BLE001 — fehlendes VLC ist der Normalfall
        _vlc["grund"] = ("VLC nicht gefunden — bitte VLC installieren (videolan.org), "
                         "bis dahin spielt der Browser-Player weiter.")
        return None, _vlc["grund"]


# ---- Windows-Medienanmeldung des VLC-Motors (JB-Go 23.09.2026) -------------
# Spielt VLC, kennt Windows den Server als Medienquelle: Titel/Interpret/Cover
# im Medien-Overlay, Medientasten und Overlay-Knöpfe wirken. Vorher meldete
# sich nur der Browser an (Media Session API) — der spielt im VLC-Modus aber
# selbst nichts. Alles WinRT steckt in medien_smtc.py, hier nur die
# Verdrahtung. Die Brücke entsteht erst in main(): ein Import (Tests,
# Werkzeuge) meldet nichts bei Windows an.
_smtc = None


def _smtc_felder():
    """Zusatzfelder JEDER /api/vlc-Antwort (Vertrag 23.09.): smtc = Windows-
    Anmeldung verfügbar, taste = Zähler der ⏭/⏮-Knöpfe aus Windows."""
    b = _smtc
    if b is not None:
        try:
            return b.felder()
        except Exception:                            # noqa: BLE001 — dann eben „nicht verfügbar"
            pass
    return {"smtc": False, "taste": {"n": 0, "was": "", "vor": 0, "zurueck": 0}}


def _smtc_titel(key):
    """Rückfall-Titel für Musik-keys, zu denen die Seite (noch) keine
    Metadaten geschickt hat — dieselbe Wahl wie lyrics_holen (Track vor Titel,
    Künstler vor Kanal). None, wenn der key nicht in der Bibliothek steht
    (Film, Live, unbekannt): dann nimmt die Brücke den key ohne Präfix."""
    e = _geladen.get(key)
    if not e:
        return None
    return {"titel": (e.get("track") or e.get("titel")
                      or musik_einstufung._titel_aus_name(e.get("name", "")) or "").strip(),
            "interpret": (e.get("kuenstler") or e.get("uploader") or "").strip(),
            "album": (e.get("album") or "").strip()}


def _smtc_log(text):
    """Konsole, Protokoll (Stufe WARNING) und dauerhafter Fehlerkanal
    (yt_fehler.jsonl). Die Brücke meldet jeden Text nur einmal."""
    _sag("Windows-Medienanmeldung: " + text, logging.WARNING)
    fehler_merken("", text, "smtc")


def _vlc_laedt():
    """libvlc öffnet oder puffert gerade (Opening/Buffering). vlc_status nennt
    das 'aus'; für Windows ist es kein Ende — sonst verschwände die Sitzung bei
    jedem Titelstart und bei jedem Puffern eines Film- oder Live-Stroms.
    Nur unter _vlc_lock rufen: der Spieler könnte sonst gerade freigegeben werden."""
    sp = _vlc["spieler"]
    if sp is None:
        return False
    try:
        import vlc
        return sp.get_state() in (vlc.State.Opening, vlc.State.Buffering)
    except Exception:                                # noqa: BLE001 — im Zweifel „nicht ladend"
        return False


PAUSE_SPERRE = 30 * 60.0      # s: so lange hält ein PAUSIERTER VLC den Selbst-Neustart höchstens auf
_pause_uhr = time.time        # Wanduhr: eine Pause über den Standby zählt mit; Tests stellen sie


def _vlc_haelt_neustart_auf():
    """Hält der VLC-Motor den Selbst-Neustart auf? Der Neustart ersetzt den
    Prozess samt libvlc und Windows-Sitzung. Beim Browser-Stream hält ihn
    _letzter_stream auf; beim VLC-Motor fragt er hier nach — auch ohne offene
    Seite, dann setzt niemand _letzter_stream. Spielen, Öffnen und Puffern
    halten ihn immer auf. Eine PAUSE hält ihn höchstens PAUSE_SPERRE seit
    ihrem Beginn auf (JB 24.09.2026: „Pause sperrt 30 Min"): der Neustart
    nähme den pausierten Titel mit, ein über Tage pausierter hielte aber jedes
    Code-Update auf. Den Beginn meldet libvlc (_vlc_ereignis) — diese Prüfung
    läuft erst, wenn neuer Code da ist, oft lange nach dem Pausieren. Kam
    keine Meldung, zählt die erste Beobachtung hier. Ist die Sperre gerade
    besetzt, arbeitet jemand am VLC: im Zweifel „hält auf", die 5-s-Schleife
    fragt gleich wieder — warten darf sie hier nicht."""
    if not _vlc_lock.acquire(timeout=0.2):
        return True
    try:
        sp = _vlc["spieler"]
        if sp is None:
            return False
        import vlc
        zustand = sp.get_state()
        if zustand != vlc.State.Paused:
            _vlc["pause_seit"] = None                # Pause vorbei: die nächste zählt neu
            return zustand in (vlc.State.Playing, vlc.State.Opening, vlc.State.Buffering)
        seit = _vlc.get("pause_seit")
        if seit is None:                             # keine libvlc-Meldung: ab jetzt zählen
            seit = _vlc["pause_seit"] = _pause_uhr()
        return _pause_uhr() - seit < PAUSE_SPERRE
    except Exception:                                # noqa: BLE001 — ein kaputter Spieler hält nichts auf
        return False
    finally:
        _vlc_lock.release()


def _vlc_ereignisse_anhaengen(sp):
    """libvlc meldet Ende, Stopp, Fehler, Spielen und Pause selbst. Ohne das
    erführe Windows ein Liedende nur, wenn eine Seite /api/vlc abfragt — bei
    geschlossener Seite (VLC spielt im Server weiter) stünde das Overlay dann
    unbegrenzt auf „spielt" und finge die Play/Pause-Taste ab (Skeptiker-
    Befund 24.09.). Ereignisse statt eines eigenen Takts (Last-Budget).
    Die Pause-Meldung liefert zugleich den Beginn einer Pause für den
    Selbst-Neustart (_vlc_haelt_neustart_auf). Jeder Rückruf bekommt den
    Ereignis-Namen mit: python-vlc hält EINEN Rückruf je Typ, ein zweiter
    event_attach desselben Typs hängte den ersten still ab.
    Fehlt event_manager (Attrappe, altes python-vlc), bleibt es beim Abgleich
    über die Seite."""
    try:
        import vlc
        em = sp.event_manager()
        for name in ("MediaPlayerEndReached", "MediaPlayerStopped",
                     "MediaPlayerEncounteredError", "MediaPlayerPlaying",
                     "MediaPlayerPaused"):
            em.event_attach(getattr(vlc.EventType, name), _vlc_ereignis, name)
    except Exception:                                # noqa: BLE001 — Kür, VLC spielt auch ohne
        pass


def _vlc_ereignis(_ereignis=None, name="", *_):
    """Rückruf auf dem libvlc-eigenen Faden. Darf libvlc NICHT aufrufen (das
    verbietet libvlc dort) und nicht auf _vlc_lock warten: ein Handler hält
    sie womöglich gerade in sp.stop(), und stop kann auf genau diesen Faden
    warten. Darum nur den Beginn einer Pause merken (ein Wert, keine Sperre)
    und einen kurzen Faden anstoßen, der den Status abholt.

    Jede ANDERE Meldung (Spielen, Stopp, Ende, Fehler) beendet die Pause auch
    hier (Prüfung Runde 2): libvlc steht schon auf Paused, bevor seine Meldung
    ankommt — eine Prüfung in diesem Fenster rechnete sonst mit dem Beginn der
    VORIGEN Pause und gab den Neustart womöglich sofort frei."""
    if name == "MediaPlayerPaused":
        _vlc["pause_seit"] = _pause_uhr()            # auch ohne Windows-Brücke
    else:
        _vlc["pause_seit"] = None                    # nur ein Wert: keine Sperre, kein libvlc-Ruf
    if _smtc is None:
        return
    threading.Thread(target=_smtc_aus_vlc, name="VLC-Ereignis", daemon=True).start()


def _smtc_aus_vlc():
    try:
        with _vlc_lock:
            _smtc_nachfuehren(vlc_status())
    except Exception:                                # noqa: BLE001 — Kür, nie den Faden reißen
        pass


def _smtc_nachfuehren(status, gespult=False):
    """Windows-Sitzung auf den VLC-Status ziehen. Blockiert nie (die Brücke
    legt nur den Soll-Zustand ab, WinRT arbeitet in ihrem eigenen Faden)."""
    b = _smtc
    if b is None:
        return
    st = dict(status)
    if st.get("zustand") == "aus" and st.get("key") and _vlc_laedt():
        st["zustand"] = "laedt"
    try:
        b.nachfuehren(st, gespult=gespult)
    except Exception:                                # noqa: BLE001 — Kür, nie den VLC-Befehl reißen
        pass


def _smtc_knopf(was, wert=None):
    """Knopf aus dem Windows-Overlay bzw. Medientaste am VLC ausführen.
    Läuft auf einem kurzen Faden der Brücke, nie auf dem WinRT-Ereignis-Faden
    (der darf nicht auf _vlc_lock warten). PLAY hebt die Pause auf — NICHT
    cmd 'play' ohne key, das scheitert mit „Datei nicht gefunden". STOP kommt
    als 'pause' an (wie die Browser-Seite: das Medium bleibt geladen)."""
    with _vlc_lock:
        sp = _vlc["spieler"]
        if sp is None:
            return
        if was == "play":
            sp.set_pause(0)
        elif was == "pause":
            sp.set_pause(1)
        elif was == "seek":
            sp.set_time(int(max(0.0, float(wert or 0)) * 1000))
        else:
            return
        st = vlc_status()
        # libvlc schaltet asynchron: direkt nach set_pause/set_time meldet es
        # oft noch den alten Stand. Windows soll sofort das Gewollte zeigen —
        # sonst stünde bis zum nächsten Seiten-Takt (oder ohne offene Seite
        # dauerhaft) das Falsche im Overlay.
        if was == "play" and st.get("zustand") == "pause":
            st["zustand"] = "spielt"
        elif was == "pause" and st.get("zustand") == "spielt":
            st["zustand"] = "pause"
        elif was == "seek":
            st["pos"] = max(0.0, float(wert or 0))
        _smtc_nachfuehren(st, gespult=(was == "seek"))


def _smtc_einrichten(**kw):
    """Brücke anlegen (main(), hinter dem Einzel-Instanz-Riegel). Fenster und
    Windows-Anmeldung entstehen erst beim ersten Abspielen im VLC.
    kw nur für Tests (faden/ausfuehren/uhr/nachlauf/log)."""
    global _smtc
    kw.setdefault("log", _smtc_log)
    _smtc = medien_smtc.SmtcBruecke(port=int(CFG.get("port", 8776)), befehl=_smtc_knopf,
                                    titel_nachschlagen=_smtc_titel, **kw)
    return _smtc


def vlc_status():
    """Status-Häppchen für die Oberfläche (1-s-Takt, solange Gerät VLC aktiv)."""
    sp = _vlc["spieler"]
    if sp is None:
        return {"verfuegbar": False, "grund": _vlc["grund"], "key": "", "zustand": "aus",
                **_smtc_felder()}
    import vlc
    zustand = {vlc.State.Playing: "spielt", vlc.State.Paused: "pause",
               vlc.State.Ended: "ende", vlc.State.Error: "fehler"}.get(sp.get_state(), "aus")
    return {"verfuegbar": True, "grund": "", "key": _vlc["key"], "zustand": zustand,
            "pos": max(0, sp.get_time()) / 1000.0,
            "dauer": max(0, sp.get_length()) / 1000.0,
            "vol": max(0, sp.audio_get_volume()),
            "rate": round(sp.get_rate() or 1.0, 2),
            "eingebettet": bool(_vlc.get("hwnd")),
            **_smtc_felder()}


TON_ALIAS = {"de": ("de", "deu", "ger", "german", "deutsch"),
             "en": ("en", "eng", "english", "englisch")}


def _ton_spur_waehlen(sp, wunsch):
    """Tonspur nach Sprach-Wunsch setzen (JB 05.08.: „eine Auswahl generell").
    Spurnamen kommen aus den Container-Metadaten und sind uneinheitlich
    ('deu', 'German', 'Deutsch [Forced]') — darum Alias-Matching. True heißt
    „erledigt" (auch: nur eine Spur / kein Treffer ⇒ Default-Spur behalten);
    False heißt „Liste noch leer, im nächsten Takt wieder" (Start asynchron)."""
    if wunsch in (None, "", "orig"):
        return True
    try:
        spuren = sp.audio_get_track_description() or []
    except Exception:                                # noqa: BLE001 — später erneut
        return False
    if not spuren:
        return False                                 # noch nicht geladen
    if len(spuren) <= 2:                             # nur 'Disable' + eine Spur
        return True
    aliasse = TON_ALIAS.get(wunsch, (wunsch,))
    for tid, name in spuren:
        if tid < 0:
            continue                                 # 'Disable' nie wählen
        n = (name.decode("utf-8", "replace") if isinstance(name, bytes)
             else str(name)).lower()
        if any(a in n for a in aliasse):
            try:
                sp.audio_set_track(tid)
            except Exception:                        # noqa: BLE001 — später erneut
                return False
            return True
    return True                                      # kein Treffer ⇒ Default bleibt


def vlc_kommando(daten):
    """Eingang für /api/vlc sowie den Film- und Live-Start: führt den Befehl
    am VLC-Motor aus (_vlc_kommando_kern) und zieht die Windows-Mediensitzung
    nach. JEDE Antwort trägt smtc + taste (Vertrag 23.09.2026). 'medien' merkt
    Titel/Interpret/Album/Cover für genau einen key und antwortet wie
    'status' — lädt libvlc also nicht nach."""
    cmd = daten.get("cmd") or "status"
    b = _smtc
    if b is not None:
        try:
            if cmd != "fenster":                     # 'fenster' schickt die Hülle, keine Seite
                b.seite_meldet()                     # jemand mit Warteschlange ist da -> ⏭/⏮ frei
            if cmd == "medien":
                b.medien(daten)
        except Exception:                            # noqa: BLE001 — Kür, nie den Befehl reißen
            pass
    if cmd == "medien":
        daten = {"cmd": "status"}
    with _vlc_lock:
        antwort = _vlc_kommando_kern(daten)
        st = antwort
        if cmd == "seek" and not antwort.get("fehler"):
            # libvlc meldet die neue Stelle asynchron — Windows bekommt die
            # gewünschte sofort (Vertrag: Zeitleiste „sofort nach Spulen").
            try:
                st = {**antwort, "pos": max(0.0, float(daten.get("wert") or 0))}
            except (TypeError, ValueError):
                pass
        _smtc_nachfuehren(st, gespult=(cmd == "seek"))
    return {**antwort, **_smtc_felder()}


def _vlc_kommando_kern(daten):
    """Befehl vom Browser an den VLC-Motor; Antwort ist immer der Status.
    'status' lädt libvlc bewusst NICHT nach (der 1-s-Takt soll einen fehlenden
    VLC nicht dauernd neu suchen) — laden tun 'pruefen' (Geräte-Wechsel) und
    'play'."""
    cmd = daten.get("cmd") or "status"
    with _vlc_lock:
        if cmd == "status" and _vlc["spieler"] is None:
            return vlc_status()
        vorher = _vlc.get("hwnd") or 0
        if cmd == "fenster":
            # Hülle zu: ein Video in IHREM Panel anhalten — in derselben
            # Anfrage und unter derselben Sperre wie das Abmelden, damit
            # zwischen Prüfen und Pausieren kein anderer Befehl liegt.
            if daten.get("pausieren_wenn_video"):
                _video_im_panel_pausieren(daten.get("nur_wenn"))
            if not _fenster_merken(daten):           # fremdes Fenster angemeldet: nichts tun
                return vlc_status()
            if _vlc["spieler"] is None and not _vlc["hwnd"]:
                return vlc_status()                  # Abmelden lädt libvlc nicht erst
        frisch = _vlc["spieler"] is None             # Neuaufbau setzt das Handle selbst
        sp, grund = _vlc_spieler()
        if sp is None:
            return {"verfuegbar": False, "grund": grund, "key": "", "zustand": "aus"}
        try:
            if cmd == "play":
                # Hülle weg (abgestürzt, nie abgemeldet)? Dann VLCs eigenes
                # Fenster statt eines toten Ziels — VOR dem Start, set_hwnd
                # wirkt erst beim nächsten Medium.
                if _vlc.get("hwnd") and not _hwnd_gueltig():
                    sp.set_hwnd(0)
                if daten.get("url"):     # Film-Fundament: Netz-Strom (Jellyfin)
                    pfad = ""            # statt lokaler Datei — Token bleibt am PC
                    sp.set_media(_vlc["instanz"].media_new(daten["url"]))
                else:
                    pfad = _pfad_zu_key(daten.get("key") or "")
                    if not (pfad and os.path.isfile(pfad)):
                        return {**vlc_status(), "fehler": "Datei nicht gefunden"}
                    sp.set_media(_vlc["instanz"].media_new(pfad))
                sp.play()
                _vlc["key"] = daten.get("key") or ""
                # Wohin rendert DIESES Medium? set_hwnd wirkt erst beim
                # nächsten; die Hülle hält beim Schließen nur ein Video in
                # ihrem eigenen Panel an (_video_im_panel_pausieren).
                _vlc["hwnd_spiel"] = _vlc.get("hwnd") or 0
                # Sprach-Wunsch fürs Nachziehen merken (die Spur-Liste ist erst
                # NACH dem asynchronen Start da; leer/orig = Datei-Standard).
                _vlc["ton_wunsch"] = (str(daten.get("ton") or "").lower() or None)
                if isinstance(daten.get("vol"), (int, float)):
                    _vlc["vol_wunsch"] = max(0, min(125, int(daten["vol"])))
                    sp.audio_set_volume(_vlc["vol_wunsch"])
                # Wiedergabe-Grundeinstellungen gelten auch am Gerät VLC:
                # Tempo (Etappe C) und — bei Videos — die .vtt als Untertitel-
                # Spur im VLC-Fenster (add_slave lädt sie zur Laufzeit dazu).
                try:
                    rate = float(daten.get("rate") or 0)
                    if 0.25 <= rate <= 4:
                        sp.set_rate(rate)
                except (TypeError, ValueError):
                    pass
                try:                                 # ↻/Merker: an einer Stelle WEITERspielen
                    pos = float(daten.get("pos") or 0)
                    if pos > 0:
                        sp.set_time(int(pos * 1000))
                except (TypeError, ValueError):
                    pass
                # Filme starten im VOLLBILD (JB 05.08.) — aber nur, wenn das
                # Video NICHT in die Hülle eingebettet ist (set_hwnd): dort
                # würde set_fullscreen das Bild aus dem Fenster reißen.
                if daten.get("vollbild") and not _vlc.get("hwnd"):
                    try:
                        sp.set_fullscreen(True)
                    except Exception:                # noqa: BLE001 — Fenster reicht
                        pass
                if daten.get("sub") and not pfad.lower().endswith(".mp3"):
                    subs = untertitel_liste(daten.get("key") or "")
                    if subs:
                        import vlc as _v
                        import urllib.request as _ur
                        uri = "file:" + _ur.pathname2url(subs[0][0])
                        try:
                            sp.add_slave(_v.MediaSlaveType.subtitle, uri, True)
                        except Exception:            # noqa: BLE001 — ohne Untertitel weiterspielen
                            pass
            elif cmd == "toggle":
                sp.pause()               # libvlc: pause() wechselt Pause↔Weiter
            elif cmd == "pause":
                # hart pausieren (Handy-Fernsteuerung). nur_key (Sleep-Timer,
                # JB 24.09. „nur musik"): nur, wenn VLC genau diesen Titel
                # spielt — Film und Musik teilen diesen einen Spieler.
                nur = daten.get("nur_key")
                if not nur or nur == _vlc.get("key"):
                    sp.set_pause(1)
            elif cmd == "stop":
                # nur_key (Filmende, folgenende.md): den Endzustand eines Films
                # freigeben — aber nie die Musik, die den VLC inzwischen hat.
                nur = daten.get("nur_key")
                if not nur or nur == _vlc.get("key"):
                    sp.stop()
                    _vlc["key"] = ""
            elif cmd == "seek":
                sp.set_time(int(float(daten.get("wert") or 0) * 1000))
            elif cmd == "vol":
                _vlc["vol_wunsch"] = max(0, min(125, int(daten.get("wert") or 0)))
                sp.audio_set_volume(_vlc["vol_wunsch"])
            elif cmd == "rate":
                try:
                    sp.set_rate(max(0.25, min(4.0, float(daten.get("wert") or 1))))
                except (TypeError, ValueError):
                    pass
            elif cmd == "standbild":
                # Pause-Schirm (JB 06.08.: „das pause bild nehmen in dem
                # moment vom film"): VLC schreibt den Moment als Schnappschuss,
                # die Oberfläche zeigt ihn hinter dem „Du siehst …"-Text.
                try:
                    sp.video_take_snapshot(
                        0, os.path.join(DATEN_DIR, "vlc_standbild.png"), 0, 0)
                except Exception:                    # noqa: BLE001 — Kür
                    pass
            elif cmd == "spuren":
                # Player-Settings (JB 06.08.: „es fehlen noch settings im
                # player. Untertitel, playback speed"): Ton-+Untertitel-Spuren
                # samt aktiver Wahl und Tempo für das 💬-/⏲-Panel.
                def _liste(rohe):
                    aus = []
                    for tid, name in (rohe or []):
                        n = (name.decode("utf-8", "replace")
                             if isinstance(name, bytes) else str(name))
                        aus.append({"id": tid, "name": n})
                    return aus
                return {**vlc_status(),
                        "ton": _liste(sp.audio_get_track_description()),
                        "sub": _liste(sp.video_get_spu_description()),
                        "ton_aktiv": sp.audio_get_track(),
                        "sub_aktiv": sp.video_get_spu(),
                        "rate": round(sp.get_rate() or 1.0, 2)}
            elif cmd == "spur":
                try:
                    sid = int(daten.get("id") if daten.get("id") is not None else -1)
                except (TypeError, ValueError):
                    sid = None                       # Müll still ignorieren —
                if sid is None:                      # nie in den Reset-Pfad fallen
                    pass
                elif daten.get("art") == "sub":
                    sp.video_set_spu(sid)            # -1 = Untertitel aus
                elif sid >= 0:
                    sp.audio_set_track(sid)          # Ton nie auf 'Disable'
            elif cmd == "fenster":
                # Hüllen-Einbettung (Etappe set_hwnd, JB-Go): das Video
                # rendert IN das übergebene Fenster statt in ein eigenes.
                # hwnd=0 löst die Bindung (Rückweg: separates VLC-Fenster).
                # Gemerkt ist es schon (_fenster_merken); ein frisch gebauter
                # Spieler hat es in _vlc_spieler bereits bekommen, und eine
                # Neu-Anmeldung desselben Fensters (vor jedem Start) lässt
                # den laufenden Spieler in Ruhe.
                h = _hwnd_gueltig()
                if not frisch and h != vorher:
                    sp.set_hwnd(h)
            # Live gemessen (05.08.): ein audio_set_volume, das ankommt, BEVOR
            # libvlc den Audio-Ausgang aufgebaut hat (play startet asynchron),
            # geht verloren — der Titel spielte mit 100 statt der gewünschten
            # Lautstärke. Darum die Wunsch-Lautstärke merken und in jedem
            # Takt nachziehen, bis sie sitzt.
            w = _vlc.get("vol_wunsch")
            if w is not None and sp.audio_get_volume() != w:
                sp.audio_set_volume(w)
            # Ton-Sprache (JB 05.08., Mehrspur-Filme): gleiches Nachzieh-Muster —
            # die Spur-Liste ist erst NACH dem asynchronen Start gefüllt.
            if _vlc.get("ton_wunsch"):
                if _ton_spur_waehlen(sp, _vlc["ton_wunsch"]):
                    _vlc["ton_wunsch"] = None
        except Exception as e:           # noqa: BLE001 — libvlc-Fehler
            # Selbstheilung (JB): kaputte Instanz EINMAL neu aufbauen und den
            # Befehl wiederholen — erst der zweite Fehlschlag wird gemeldet.
            if not daten.get("_wiederholt"):
                _vlc_reset()
                return _vlc_kommando_kern({**daten, "_wiederholt": True})
            return {**vlc_status(), "fehler": str(e)[:200]}
        return vlc_status()


def _datei_fp(pfad):
    """Content-Fingerabdruck (Bibliothek 2.0, JBs „Magnet"-Idee): sha1 über
    erste + letzte 64 KB + Dateigröße (OpenSubtitles-Stil, 2 schnelle Reads).
    Erkennt eine Datei am INHALT — egal wie sie heißt oder wo sie liegt.
    '' bei Fehler/fehlender Datei (Aufrufer behandeln leer als „unbekannt")."""
    try:
        groesse = os.path.getsize(pfad)
        h = hashlib.sha1(str(groesse).encode())
        with open(pfad, "rb") as f:
            h.update(f.read(65536))
            if groesse > 131072:
                f.seek(-65536, os.SEEK_END)
                h.update(f.read(65536))
        return h.hexdigest()
    except OSError:
        return ""


_fp_cache = {}


def _fp_von(pfad):
    """_datei_fp mit (Größe, mtime)-Gedächtnis: unveränderte Dateien werden
    nie doppelt gelesen — so bleibt die Erkennungs-Kette alltagsschnell."""
    try:
        st = os.stat(pfad)
    except OSError:
        return ""
    schluessel = os.path.normcase(os.path.abspath(pfad))
    alt = _fp_cache.get(schluessel)
    if alt and alt[0] == st.st_size and alt[1] == int(st.st_mtime):
        return alt[2]
    fp = _datei_fp(pfad)
    if fp:
        _fp_cache[schluessel] = (st.st_size, int(st.st_mtime), fp)
    return fp


def _id_karten():
    """Nachschlage-Karten aus der geladen-DB: bekannter Pfad -> Video-Id und
    Fingerabdruck -> Video-Id (Stufen 2+3 der Erkennungs-Kette). Bewusst OHNE
    _plausible_id-Filter: auch 'lokal-…'-Import-Ids gehören hinein, damit
    verschobene Importe wiedererkannt werden statt Duplikat-Zeilen zu erzeugen."""
    pfade, fps = {}, {}
    for k, e in _geladen_schnappschuss():
        vid = k.split("|")[0]
        p = e.get("pfad")
        if p:
            pfade[os.path.normcase(os.path.abspath(p))] = vid
        if e.get("fp"):
            fps[e["fp"]] = vid
    return pfade, fps


def _datei_videoid(pfad, karten=None):
    """DIE zentrale Auflösung Datei -> Video-Id (Bibliothek 2.0, Klammern-
    Projekt): [Id] im Namen -> bekannter Pfad in der DB -> Content-
    Fingerabdruck. '' wenn unbekannt. Nur über diese Kette nachschlagen —
    dann funktioniert alles auch, wenn Dateinamen keine [Id] mehr tragen."""
    m = re.search(r"\[([\w-]{6,})\]", os.path.basename(pfad))
    if m:
        return m.group(1)
    pfade, fps = karten if karten is not None else _id_karten()
    vid = pfade.get(os.path.normcase(os.path.abspath(pfad)))
    if vid:
        return vid
    if fps:
        fp = _fp_von(pfad)
        if fp:
            vid = fps.get(fp, "")
            if vid:
                return vid
    return _id_tag_lesen(pfad)                        # Stufe 4: Id-Tag IN der Datei


_TAG_ID = "YTDL_ID"                                   # Tag-Name in allen Containern
_TAG_ORIG = "YTDL_ORIGNAME"                           # ursprünglicher Dateiname (Undo, Build 113)


def _orig_tag(pfad, name=None):
    """Ursprungs-Dateinamen IN der Datei vermerken bzw. lesen (JB: „sind diese
    Dateien ebenfalls in der Datei zu vermerken?"). Nur das ERSTE Mal wird
    geschrieben — der Original ist der Zustand vor unserem ersten Umbenennen.
    Damit funktioniert ein Zurück auch für Dateien, die inzwischen woanders
    liegen (das Protokoll auf Platte kennt nur unsere Pfade)."""
    if name is None:
        return _tag_lesen(pfad, _TAG_ORIG)
    if _tag_lesen(pfad, _TAG_ORIG):
        return True                                   # schon vermerkt: nie überschreiben
    return _tag_schreiben(pfad, _TAG_ORIG, name)


def _tag_schreiben(pfad, schluessel, wert):
    """Einen eigenen Text-Tag IN die Datei schreiben (mutagen in-place, kein
    ffmpeg-Remux). NUR Audio-Container (mp3=ID3-TXXX, m4a=Freeform,
    opus/ogg/flac=Vorbis): Video-Dateien (mp4/webm/mkv) bekommen KEIN Tag —
    mutagen müsste große mp4 oft komplett neu schreiben (GB-Kopien,
    Last-Budget) bzw. kann webm/mkv gar nicht; dort tragen Fingerabdruck +
    DB. Gelesen wird mp4 trotzdem (falls anderswo getaggt).
    WICHTIG: verändert den Dateianfang ⇒ Aufrufer muss das fp DANACH
    (neu) rechnen, nie davor speichern. True nur bei echtem Erfolg."""
    if not wert:
        return False
    ext = os.path.splitext(pfad)[1].lower()
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3, ID3NoHeaderError, TXXX
            try:
                tags = ID3(pfad)
            except ID3NoHeaderError:
                tags = ID3()
            tags.setall("TXXX:" + schluessel, [TXXX(encoding=3, desc=schluessel, text=[wert])])
            tags.save(pfad, v2_version=3)
            return True
        if ext == ".m4a":
            from mutagen.mp4 import MP4
            m = MP4(pfad)
            m["----:com.ytdl:" + schluessel] = [wert.encode("utf-8")]
            m.save()
            return True
        if ext in (".opus", ".ogg", ".flac"):
            from mutagen import File as MFile
            m = MFile(pfad)
            if m is not None:
                m[schluessel] = [wert]
                m.save()
                return True
    except Exception:                                # noqa: BLE001 — kaputte/fremde Datei: still lassen
        pass
    return False


def _tag_lesen(pfad, schluessel):
    """Eigenen Text-Tag aus der Datei lesen ('' wenn keiner)."""
    ext = os.path.splitext(pfad)[1].lower()
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3
            frames = ID3(pfad).getall("TXXX:" + schluessel)
            return str(frames[0].text[0]) if frames and frames[0].text else ""
        if ext in (".m4a", ".mp4", ".mov"):
            from mutagen.mp4 import MP4
            m = MP4(pfad)
            werte = m.tags.get("----:com.ytdl:" + schluessel) if m.tags else None
            return werte[0].decode("utf-8", "ignore") if werte else ""
        if ext in (".opus", ".ogg", ".flac"):
            from mutagen import File as MFile
            m = MFile(pfad)
            werte = m.get(schluessel) if m else None
            return str(werte[0]) if werte else ""
    except Exception:                                # noqa: BLE001
        pass
    return ""


def _id_tag_schreiben(pfad, vid):
    """Video-Id als Tag IN die Datei (Bibliothek 2.0 Schicht 2, Sicherheitsnetz
    fürs Kopieren auf andere Geräte)."""
    if not vid or not links._plausible_id(vid):
        return False
    return _tag_schreiben(pfad, _TAG_ID, vid)


def _id_tag_lesen(pfad):
    """Video-Id aus dem Datei-Tag ('' wenn keins) — erkennt auch Dateien,
    die von einem ANDEREN PC stammen und die unsere DB nie gesehen hat.
    Nur eine plausible Id zählt (Gesamtprüfung S3): der Tag einer fremden
    Datei wird sonst ungeprüft zum Bibliotheks-Schlüssel. Der Schreiber
    (`_id_tag_schreiben`) prüft dasselbe."""
    vid = _tag_lesen(pfad, _TAG_ID)
    return vid if links._plausible_id(vid) else ""


_AUFFAELLIG = re.compile(r"['\"<>`\\\x00-\x1f]")


def auffaellige_schluessel():
    """Bibliotheks-Schlüssel mit Zeichen, die in HTML oder Skript Bedeutung
    haben (Anführungszeichen, spitze Klammern, Backtick, Backslash) oder mit
    Steuerzeichen. NUR melden (Gesamtprüfung S3): die Oberfläche übergibt
    Schlüssel inzwischen nur noch als Daten, und ein Schlüssel ist die
    Identität eines Downloads — umschreiben oder löschen hieße Bestand
    verlieren."""
    return [k for k in _geladen_schluessel() if _AUFFAELLIG.search(k)]


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


# Rückhol-Ordner (Gesamtprüfung S5/S6): was hier liegt, hat die App entfernt,
# aber nicht gelöscht. Einsortieren, Import, Datei-Index und die Suche nach
# schon Geladenem steigen nie hinein, sonst käme es als Bibliothek zurück.
PAPIERKORB_ORDNER = "_Papierkorb"                     # Rückfall, wenn der Windows-Papierkorb scheitert
ENTFERNT_ORDNER = "_entfernt"                         # im Sync-Ziel: aus der Playlist genommene Titel
_RUECKHOL_ORDNER = {PAPIERKORB_ORDNER.lower(), ENTFERNT_ORDNER.lower()}


def _walk_ohne_rueckhol(basis):
    """os.walk ohne die Rückhol-Ordner (auch tiefer liegende)."""
    for wurzel, dirs, dateien in os.walk(basis):
        dirs[:] = [d for d in dirs if d.lower() not in _RUECKHOL_ORDNER]
        yield wurzel, dirs, dateien


def _im_rueckhol_ordner(pfad, basis):
    """Liegt `pfad` unterhalb von `basis` in einem Rückhol-Ordner? Nur die
    Teile unter `basis` zählen (der Download-Ordner selbst darf so heißen)."""
    try:
        rest = os.path.relpath(pfad, basis)
    except ValueError:                                # anderes Laufwerk
        return False
    return any(t.lower() in _RUECKHOL_ORDNER for t in rest.split(os.sep)[:-1])


def _rueckholbar_verschieben(pfad, ordner):
    """Datei nach `ordner` verschieben, nie überschreiben (nummerierter Name;
    os.rename scheitert unter Windows an einem vorhandenen Ziel). Gibt den
    neuen Pfad zurück, OSError geht an den Aufrufer."""
    os.makedirs(ordner, exist_ok=True)
    stamm, ext = os.path.splitext(os.path.basename(pfad))
    for n in range(1, 10_000):
        neu = os.path.join(ordner, stamm + ext if n == 1 else f"{stamm} ({n}){ext}")
        if os.path.lexists(neu):
            continue
        try:
            os.rename(pfad, neu)
            return neu
        except FileExistsError:                       # im selben Augenblick entstanden
            continue
    raise OSError(f"kein freier Name in {ordner}")


def _vorher_sichern(pfad, neuer_inhalt):
    """Vor dem Überschreiben (Gesamtprüfung S11): hat eine vorhandene Datei
    einen anderen Inhalt, liegt sie danach als `<name>.<Zeitstempel>.bak`
    daneben (endet nicht auf .conf, zählt also nicht als WireGuard-Land).
    Nie überschreiben: exklusiv angelegt, bei Kollision nummeriert. Gibt den
    Pfad der Sicherung zurück oder "" (nichts zu sichern); OSError geht an
    den Aufrufer, der dann nicht überschreibt. Verglichen wird mit den Bytes,
    die der Aufrufer schreibt (Textmodus, utf-8: jedes \\n wird os.linesep),
    sonst gälte eine Datei mit \\r\\n nie als gleich."""
    if not os.path.isfile(pfad):
        return ""
    with open(pfad, "rb") as f:
        if f.read() == neuer_inhalt.replace("\n", os.linesep).encode("utf-8"):
            return ""
    stempel = time.strftime("%Y%m%d-%H%M%S")
    for n in range(1, 1000):
        ziel = f"{pfad}.{stempel}{'' if n == 1 else f'-{n}'}.bak"
        try:
            with open(pfad, "rb") as quelle, open(ziel, "xb") as kopie:
                shutil.copyfileobj(quelle, kopie)
            return ziel
        except FileExistsError:
            continue
    raise OSError(f"kein freier Name für die Sicherung von {pfad}")


def _papierkorb_ordner(pfad):
    """`_Papierkorb` im Download-Ordner, wenn die Datei darunter liegt, sonst
    neben der Datei: beides derselbe Datenträger, also ein Umbenennen."""
    basis = os.path.abspath(ziel_ordner())
    p = os.path.abspath(pfad)
    try:
        drinnen = os.path.commonpath([basis, p]) == basis
    except ValueError:                                # anderes Laufwerk
        drinnen = False
    return os.path.join(basis if drinnen else os.path.dirname(p), PAPIERKORB_ORDNER)


_OHNE_PAPIERKORB = {2, 4}                             # DRIVE_REMOVABLE, DRIVE_REMOTE


def _laufwerk_art(wurzel):
    """GetDriveTypeW für eine Laufwerkswurzel wie "C:\\" (0 = unbekannt)."""
    try:
        import ctypes
        return int(ctypes.windll.kernel32.GetDriveTypeW(wurzel))
    except Exception:                                # noqa: BLE001 — kein Windows: unbekannt
        return 0


def _ohne_papierkorb(pfad):
    """Liegt `pfad` auf einem Laufwerk ohne Windows-Papierkorb (Wechseldatenträger,
    Netzlaufwerk, Freigabe)? Dort löscht SHFileOperationW auch mit
    FOF_ALLOWUNDO endgültig und meldet trotzdem Erfolg (Gesamtprüfung S6).
    Eine Freigabe erkennt schon der Pfad, ohne Frage ans Netz."""
    wurzel = os.path.splitdrive(os.path.abspath(pfad))[0]
    if wurzel.endswith(":"):                          # "C:" oder "\\?\C:"
        return _laufwerk_art(wurzel[-2:] + "\\") in _OHNE_PAPIERKORB
    return wurzel.startswith(("\\\\", "//"))


def _rueckholbar_entfernen(pfad):
    """Datei in den Windows-Papierkorb; gibt es auf dem Laufwerk keinen,
    scheitert er oder liegt die Datei danach noch da, rückholbar in den
    Ordner `_Papierkorb` (S6). Nie endgültig löschen (harte Regel 2), keinen
    Dialog öffnen (läuft auch in Hintergrundfäden). Jeder Rückfall wird
    gemeldet (Konsole und yt_fehler.jsonl). Rückgabe: "papierkorb", der neue
    Pfad oder "" (die Datei bleibt, wo sie war)."""
    if _ohne_papierkorb(pfad):
        grund = "Laufwerk ohne Papierkorb"
    elif _in_papierkorb(pfad) and not os.path.lexists(pfad):
        return "papierkorb"
    else:
        grund = "Papierkorb gescheitert"
    try:
        neu = _rueckholbar_verschieben(pfad, _papierkorb_ordner(pfad))
    except OSError as e:
        text = f"{grund}, Datei bleibt liegen: {pfad} ({e})"
        neu = ""
    else:
        text = f"{grund}, rückholbar verschoben: {pfad} -> {neu}"
    _sag(text)
    fehler_merken("", text, "papierkorb", os.path.basename(pfad))
    return neu


def _datei_loeschen(key):
    """Datei zu einem Key rückholbar entfernen (Papierkorb, Rückfall
    `_Papierkorb`, s. _rueckholbar_entfernen) + aus allen Playlists nehmen.
    Der Aufrufer entfernt den DB-Eintrag selbst."""
    _datei_rueckholbar_entfernen(key)
    _aus_playlists_nehmen(key)


def _datei_rueckholbar_entfernen(key):
    """Nur die Datei (Pfadsuche samt Ordnerlauf, dann Papierkorb). Braucht
    keine Sperre: die Einzel-Löschung ruft es ohne _io_lock (F7)."""
    pfad = _pfad_zu_key(key)
    if pfad and os.path.isfile(pfad):
        _rueckholbar_entfernen(pfad)


def _aus_playlists_nehmen(key):
    """Den Key aus allen Playlists nehmen (unter _io_lock rufen)."""
    for pl in _playlists:
        pl["items"] = [x for x in pl.get("items", []) if x != key]


# ---- Playlists (playlists.json): [{id, name, items:[key,...], ts}]

_playlists = _json_laden(PLAYLIST_PFAD, [])
if not isinstance(_playlists, list):
    _playlists = []


def _playlists_speichern():
    with _io_lock:
        _json_speichern(PLAYLIST_PFAD, _playlists)


def sync_ziel_fehler(ordner):
    """JB-Entscheid 25.09.2026 (Gesamtprüfung, Frage 4): Ein Sync-Ziel in der
    Bibliothek oder auf einem Netzwerkpfad wird beim Einrichten abgelehnt.
    Rückgabe: die Meldung oder None. Rein textlich: schon ein `isdir` auf
    einen UNC-Pfad öffnete eine Netzverbindung."""
    roh = (ordner or "").strip().replace("/", "\\")
    if not roh:
        return None                                   # leer = Sync-Ziel entfernen
    if roh.upper().startswith("\\\\?\\UNC\\") or (roh.startswith("\\\\") and not roh.startswith("\\\\?\\")):
        return ("Netzwerkpfade (\\\\server\\…) sind als Sync-Ordner nicht erlaubt. "
                "Bitte ein Laufwerk wählen, etwa den USB-Stick.")
    if roh.startswith("\\\\?\\"):
        roh = roh[4:]                                 # langer lokaler Pfad
    bib = os.path.normcase(os.path.abspath(ziel_ordner()))
    ziel = os.path.normcase(os.path.abspath(roh))
    try:
        drin = os.path.commonpath([bib, ziel]) == bib
    except ValueError:                                # anderes Laufwerk
        drin = False
    if drin:
        return (f"Der Sync-Ordner liegt in der Bibliothek ({ziel_ordner()}). "
                "Bitte einen Ordner außerhalb wählen, etwa auf dem USB-Stick.")
    return None


def playlist_aktion(daten):
    """Ändert eine Playlist; bei `create` Rückgabe der neuen id (F17: die
    Oberfläche riet sonst „die zuletzt gelistete“). Eine abgelehnte
    Sync-Einrichtung liefert {"fehler": …} und ändert nichts."""
    art = daten.get("art")
    neu_id = None
    with _io_lock:
        if art == "create":
            name = (str(daten.get("name") or "")).strip()[:80] or "Playlist"
            neu_id = uuid.uuid4().hex[:8]
            _playlists.append({"id": neu_id, "name": name, "items": [], "ts": time.time()})
        else:
            pl = next((p for p in _playlists if p.get("id") == daten.get("id")), None)
            if not pl:
                return
            if art == "delete":
                _playlists[:] = [p for p in _playlists if p.get("id") != pl["id"]]
            elif art == "rename":
                pl["name"] = (str(daten.get("name") or pl["name"])).strip()[:80] or pl["name"]
            elif art == "add":
                # Build 138 (JB): Doppelte Titel sind ERLAUBT — „Ist ja meine
                # Entscheidung." Vorher verschluckte `k not in pl["items"]`
                # den Wurf stillschweigend: JB zog einen Song hinein, und es
                # passierte einfach nichts. Eine Playlist ist eine
                # Reihenfolge, kein Mengenbegriff.
                k = daten.get("key")
                if k and k in _geladen:
                    pl["items"].append(k)
            elif art == "ersetzen":
                # Setzt die Liste EXAKT — für das Rückgängig nach einem Wurf.
                # Ein „remove" träfe alle Vorkommen eines Titels, nicht nur
                # die gerade hinzugefügten; seit Duplikate erlaubt sind, wäre
                # das die falsche Umkehrung.
                if isinstance(daten.get("items"), list):
                    pl["items"] = [str(k) for k in daten["items"] if str(k) in _geladen]
            elif art == "remove":
                pl["items"] = [x for x in pl["items"] if x != daten.get("key")]
            elif art == "reorder" and isinstance(daten.get("items"), list):
                pl["items"] = [k for k in daten["items"] if k in pl["items"]]
            elif art == "sync_config":
                if isinstance(daten.get("sync_ordner"), str):
                    fehler = sync_ziel_fehler(daten["sync_ordner"])
                    if fehler:
                        return {"fehler": fehler}
                    pl["sync_ordner"] = daten["sync_ordner"].strip()
                if daten.get("sync_modus") in ("kopieren", "spiegeln"):
                    pl["sync_modus"] = daten["sync_modus"]
                if "sync_auto" in daten:              # JB 07.08.: Auto-Sync
                    pl["sync_auto"] = bool(daten["sync_auto"])
        _json_speichern(PLAYLIST_PFAD, _playlists)
    return neu_id


# ---- Wiedergabe-Grundeinstellungen (Spec Punkt 5, Etappe C) -----------------
# Drei Ebenen, jede schlägt die darüber (JB-bestätigt 23.07.):
# global (CFG) → je Playlist/Werk → je Titel („absolut" gemerkt).
# Gespeichert wird nur, was gesetzt ist — leere Ebene heißt „erbt von oben".

WIEDERGABE_SUB = ("aus", "zeilen", "karaoke", "transkript")


def _wiedergabe_saeubern(daten, merge_mit=None):
    """Gültige Werte herausziehen; bei merge_mit werden nur die MITGESCHICKTEN
    Felder ersetzt (Auto-Merken am laufenden Titel darf die anderen nicht
    wegwischen), sonst ersetzt das Ergebnis die Ebene komplett."""
    w = dict(merge_mit or {})
    if "sub" in daten:
        if daten.get("sub") in WIEDERGABE_SUB:
            w["sub"] = daten["sub"]
        else:
            w.pop("sub", None)                        # leer/ungültig = erben
    if "speed" in daten:
        try:
            sp = float(daten.get("speed") or 0)
        except (TypeError, ValueError):
            sp = 0
        if 0.25 <= sp <= 3:
            w["speed"] = sp
        else:
            w.pop("speed", None)
    if "ton" in daten:                                # vorbereitet (Mehrspur kommt mit dem Film-Import)
        ton = str(daten.get("ton") or "").strip().lower()[:8]
        if ton:
            w["ton"] = ton
        else:
            w.pop("ton", None)
    if "sub_groesse" in daten:                        # Untertitel-Größe (global, JB 05.08.:
        try:                                          # „für alle Videos, versionsunabhängig")
            gr = round(float(daten.get("sub_groesse") or 0), 2)
        except (TypeError, ValueError):
            gr = 0
        if 0.5 <= gr <= 3:
            w["sub_groesse"] = gr
        else:
            w.pop("sub_groesse", None)
    if "sub_stil" in daten:
        stil = str(daten.get("sub_stil") or "").strip().lower()
        if stil in ("dunkel", "hell", "gelb", "kontur"):
            w["sub_stil"] = stil
        else:
            w.pop("sub_stil", None)
    if "sub_look" in daten:                           # Disney-Look (JB 05.08.): ein Dict,
        look = daten.get("sub_look")                  # streng geprüft — nur Belegtes
        if isinstance(look, dict):
            sauber = {}
            try:
                g = float(look.get("groesse") or 0)
                if 0.5 <= g <= 3:
                    sauber["groesse"] = round(g, 2)
            except (TypeError, ValueError):
                pass
            if look.get("schrift") in ("standard", "serif", "mono", "casual", "kursiv", "breit"):
                sauber["schrift"] = look["schrift"]
            farbe = str(look.get("farbe") or "")
            if re.fullmatch(r"#[0-9a-fA-F]{6}", farbe):
                sauber["farbe"] = farbe.lower()
            for feld in ("deckkraft", "hg_deckkraft"):
                try:
                    v = float(look.get(feld))
                    if 0 <= v <= 1:
                        sauber[feld] = round(v, 2)
                except (TypeError, ValueError):
                    pass
            if isinstance(look.get("schatten"), bool):
                sauber["schatten"] = look["schatten"]
            if look.get("hg") in ("schwarz", "weiss"):
                sauber["hg"] = look["hg"]
            if sauber:
                w["sub_look"] = sauber
            else:
                w.pop("sub_look", None)
        else:
            w.pop("sub_look", None)                   # '' = Reset
    if "sub_offset" in daten:                         # Untertitel-Versatz in Sekunden (JB 05.08.)
        try:
            off = round(float(daten.get("sub_offset") or 0), 1)
        except (TypeError, ValueError):
            off = 0
        if off and -30 <= off <= 30:
            w["sub_offset"] = off
        else:
            w.pop("sub_offset", None)                 # 0 = Versatz aus
    return w


def wiedergabe_setzen(daten):
    """Eine Ebene setzen: {'global':1}, {'plid':id} oder {'keys':[...]} —
    dazu die Felder sub/speed/ton (fehlend = unangetastet bei merge,
    leer = löschen). merge=1 kommt vom Auto-Merken am laufenden Titel."""
    merge = bool(daten.get("merge"))
    with _io_lock:
        if daten.get("global"):
            with _cfg_lock:
                w = _wiedergabe_saeubern(daten, CFG.get("wiedergabe") if merge else None)
                if w:
                    CFG["wiedergabe"] = w
                else:
                    CFG.pop("wiedergabe", None)
                _cfg_speichern()
                return {"ok": True, "wiedergabe": CFG.get("wiedergabe")}
        if daten.get("plid"):
            pl = next((p for p in _playlists if p.get("id") == daten["plid"]), None)
            if not pl:
                return {"fehler": "Playlist unbekannt"}
            w = _wiedergabe_saeubern(daten, pl.get("wiedergabe") if merge else None)
            if w:
                pl["wiedergabe"] = w
            else:
                pl.pop("wiedergabe", None)
            _json_speichern(PLAYLIST_PFAD, _playlists)
            return {"ok": True, "wiedergabe": pl.get("wiedergabe")}
        keys = [k for k in (daten.get("keys") or []) if k in _geladen]
        for k in keys:
            e = _geladen[k]
            w = _wiedergabe_saeubern(daten, e.get("wiedergabe") if merge else None)
            if w:
                e["wiedergabe"] = w
            else:
                e.pop("wiedergabe", None)
        if keys:
            _geladen_speichern()
        return {"ok": True, "anzahl": len(keys)}


def herz_umschalten(key):
    """❤ Lieblingssong an/aus (JB 05.08.: „zu den lieblingssongs sollte ein
    herz sein"). Aus = Feld ganz raus (die DB bleibt schlank)."""
    with _io_lock:
        e = _geladen.get(key)
        if not e:
            return
        if e.get("herz"):
            e.pop("herz", None)
        else:
            e["herz"] = True
        _geladen_speichern()


def wiedergabe_sub_altlast_raeumen():
    """Einmalige Räumung (JB 05.08.: „wenn ich die einmal an habe, dann sind
    die für alle an"): Früher schrieb JEDER Untertitel-Umschalt-Klick eine
    absolute Je-Titel-Regel — diese Altlast schaltete die Untertitel je nach
    Titel-Vergangenheit „mal an, mal aus". Der Modus gilt jetzt GLOBAL; die
    alten sub-Titelregeln kommen raus, RÜCKWEG liegt wortgleich in
    wiedergabe_sub_altlast.json (nichts wird gelöscht, nur bewegt).
    Bewusste Ausnahmen bleiben möglich: Rechtsklick → „Wiedergabe…"."""
    if CFG.get("wg_sub_migriert"):
        return 0
    gesichert = {}
    with _io_lock:
        for k, e in _geladen_schnappschuss():
            w = e.get("wiedergabe") or {}
            if "sub" in w:
                gesichert[k] = w.pop("sub")
                if not w:
                    e.pop("wiedergabe", None)
        if gesichert:
            _geladen_speichern()
    if gesichert:
        _json_speichern(os.path.join(DATEN_DIR, "wiedergabe_sub_altlast.json"),
                        gesichert)
    with _cfg_lock:
        CFG["wg_sub_migriert"] = True
        _cfg_speichern()
    return len(gesichert)


def _dieselbe_datei(a, b):
    """Zeigen beide Pfade auf dieselbe Datei (Sync-Ordner = Ort der Originale)?"""
    try:
        return os.path.exists(a) and os.path.samefile(a, b)
    except OSError:
        return False


def _quellordner_erreichbar(e):
    """Ist der Ordner erreichbar, in dem die fehlende Quelle eines Eintrags lag
    (ohne gemerkten Pfad: der Download-Ordner)? Nein heißt: Platte oder
    Freigabe ab, die Datei kommt vermutlich zurück (Gesamtprüfung S5)."""
    pfad = e.get("pfad") if isinstance(e.get("pfad"), str) else ""
    ordner = os.path.dirname(pfad) if pfad else ziel_ordner()
    return bool(ordner) and os.path.isdir(ordner)


def _nach_entfernt(ziel, ordner):
    """Datei im Sync-Ziel rückholbar nach `<ordner>/_entfernt` (nie gelöscht,
    nie überschrieben; OSError geht an den Aufrufer)."""
    neu = _rueckholbar_verschieben(ziel, os.path.join(ordner, ENTFERNT_ORDNER))
    _nomedia_sichern(ordner)
    return neu


def _nomedia_sichern(ordner):
    """Leere `.nomedia` in `<ordner>/_entfernt`, falls es den Ordner gibt: ist
    das Ziel ein Handy, nähme der Medienscanner die entfernten Titel sonst
    wieder in die Musik-App auf. Eine vorhandene Datei bleibt, wie sie ist
    (exklusiv angelegt); ein Fehler ist nur Kür."""
    rueck = os.path.join(ordner, ENTFERNT_ORDNER)
    if not os.path.isdir(rueck):
        return
    try:
        with open(os.path.join(rueck, ".nomedia"), "xb"):
            pass
    except OSError:                                   # schon da, oder Ziel nur lesbar
        pass


def playlist_sync(pl):
    """Playlist-Dateien in den Zielordner (Gerät/USB/Handy) kopieren.
    Modus 'spiegeln': aus der Playlist entfernte Titel verlassen das Ziel —
    rückholbar in den Unterordner `_entfernt` (auf Sticks und Handys gibt es
    keinen Papierkorb) und NUR Dateien, die wir selbst dorthin kopiert haben,
    nie fremde Dateien im Ordner (nicht-destruktiv gegenüber JBs Daten).

    Das Merkblatt `sync_kopien` (Gesamtprüfung S5) = {"ordner", "dateien":
    {Schlüssel: Dateiname}} gilt nur für den Zielordner, für den es entstand,
    und nennt nur wirklich kopierte Dateien; eine schon vorhandene gleich
    große Datei im Ziel ist nicht unsere, das Original selbst (Sync-Ordner in
    der Bibliothek) nie. Liegt im Ziel eine fremde Datei gleichen Namens mit
    anderer Größe, wandert sie vor dem Kopieren nach `_entfernt`, statt
    überschrieben zu werden; jeder `_entfernt`-Ordner trägt eine `.nomedia`
    (Gesamtprüfung Gruppe 6). Entfernt werden die Kopien der Schlüssel, die nicht
    mehr in der Playlist stehen, und die alte Kopie eines umbenannten Titels;
    solange die noch im Ziel liegt, merkt sich das Merkblatt ihren Namen unter
    "reste" {alter Name: Schlüssel}. Fehlt eine Quelle (`fehlend` im Ergebnis), bleibt
    ihre Kopie über den Schlüssel geschützt; liegt sie in einem gerade
    unerreichbaren Ordner (Platte ab), wird in diesem Lauf gar nichts
    entfernt, der nächste Lauf mit erreichbarem Ordner holt es nach. Eine alte
    Namensliste `sync_manifest` wird einmal übernommen: ein dort genannter
    Name gilt als unsere Kopie, wenn der Titel in der Playlist steht und die
    Datei im Ziel gleich groß ist."""
    if not pl:
        return {"fehler": "Playlist unbekannt"}
    ordner = (pl.get("sync_ordner") or "").strip()
    if not ordner:
        return {"fehler": "kein Zielordner eingerichtet"}
    try:
        os.makedirs(ordner, exist_ok=True)
    except OSError as e:
        return {"fehler": f"Zielordner nicht erreichbar: {e}"}
    ordner_norm = os.path.normcase(os.path.abspath(ordner))
    kopien = pl.get("sync_kopien") if isinstance(pl.get("sync_kopien"), dict) else {}
    bisher = kopien.get("dateien") if kopien.get("ordner") == ordner_norm else None
    bisher = {str(k): str(n) for k, n in bisher.items()} if isinstance(bisher, dict) else {}
    reste = kopien.get("reste") if kopien.get("ordner") == ordner_norm else None
    reste = {str(n): str(k) for n, k in reste.items()} if isinstance(reste, dict) else {}
    alte_liste = pl.get("sync_manifest") if "sync_kopien" not in pl else None
    alte_namen = set(alte_liste) if isinstance(alte_liste, list) else set()
    items = list(pl.get("items", []))
    in_playlist = set(items)
    idx = _datei_index()
    gewollt = {}                                      # basename -> (Schlüssel, Quellpfad)
    fehlend = 0
    gesperrt = False                                  # Ordner einer fehlenden Quelle unerreichbar
    for key in items:
        e = _geladen.get(key)
        if not e:
            continue
        src = (e.get("pfad") if e.get("pfad") and os.path.isfile(e.get("pfad"))
               else _datei_aus(idx.get(key.split("|")[0]), key.partition("|")[2]))
        if src and os.path.isfile(src):
            gewollt[os.path.basename(src)] = (key, src)
        else:
            fehlend += 1                              # Platte ab, Datei verschoben: kein „entfernt"
            gesperrt = gesperrt or not _quellordner_erreichbar(e)
    neu = {k: n for k, n in bisher.items() if k in in_playlist}   # fehlende/alte bleiben gemerkt
    kopiert = uebersprungen = geloescht = fehler = 0
    for name, (key, src) in gewollt.items():
        ziel = os.path.join(ordner, name)
        eigen = bisher.get(key) == name or name in alte_namen
        neu.pop(key, None)
        try:
            if _dieselbe_datei(ziel, src):
                uebersprungen += 1                    # Ziel IST das Original: nie unsere Kopie
            elif os.path.exists(ziel) and os.path.getsize(ziel) == os.path.getsize(src):
                uebersprungen += 1
                if eigen:
                    neu[key] = name
            else:
                if os.path.lexists(ziel) and not eigen:   # fremde Datei: erst in Sicherheit
                    _nach_entfernt(ziel, ordner)
                shutil.copy2(src, ziel)
                kopiert += 1
                neu[key] = name
        except OSError:
            fehler += 1
            if eigen:
                neu[key] = name
    neu_reste = {}                                    # alte Namen umbenannter Titel, die noch im Ziel liegen
    if pl.get("sync_modus") == "spiegeln":
        geschuetzt = set(gewollt) | set(neu.values())  # Namen, die einem Titel gehören
        aktuell = {k: n for n, (k, _s) in gewollt.items()}
        kandidaten = ([(k, n, False) for k, n in bisher.items()]
                      + [(k, n, True) for n, k in reste.items()])
        for key, name, rest in kandidaten:
            entfernt = key not in in_playlist
            umbenannt = rest or (key in aktuell and aktuell[key] != name)   # Kopie unter altem Namen
            if not (entfernt or umbenannt) or name in geschuetzt:
                continue
            if not gesperrt:                          # gesperrt: erst, wenn der Ordner wieder da ist
                ziel = os.path.join(ordner, name)
                if not os.path.isfile(ziel):
                    continue                          # schon weg
                try:
                    _nach_entfernt(ziel, ordner)
                    geloescht += 1
                    continue
                except OSError:
                    fehler += 1
            if entfernt and not rest:                 # gemerkt: der nächste Lauf versucht es wieder
                neu[key] = name
            else:
                neu_reste[name] = key
    _nomedia_sichern(ordner)                          # auch ein _entfernt von früher
    with _io_lock:
        pl["sync_kopien"] = {"ordner": ordner_norm, "dateien": neu}
        if neu_reste:
            pl["sync_kopien"]["reste"] = neu_reste
        pl.pop("sync_manifest", None)
        pl["sync_ts"] = time.time()
        _json_speichern(PLAYLIST_PFAD, _playlists)
    ergebnis = {"ok": True, "kopiert": kopiert, "uebersprungen": uebersprungen,
                "geloescht": geloescht, "fehler": fehler, "im_ziel": len(gewollt)}
    if fehlend:
        ergebnis["fehlend"] = fehlend
    return ergebnis


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
    for k, e in _geladen_schnappschuss():
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

ABO_PFAD = os.path.join(DATEN_DIR, "abos.json")
_abos = _json_laden(ABO_PFAD, [])
if not isinstance(_abos, list):
    _abos = []


def _abo_flach(url, limit=60):
    """Flacher yt-dlp-Blick auf Kanal/Playlist (ohne Download): info-Dict mit
    entries (id/title/duration/live_status) — Basis für Prüfen und Backkatalog."""
    opts = _ydl_basis_opts()
    opts.update({"extract_flat": "in_playlist", "skip_download": True,
                 "playlistend": limit, "noplaylist": False})
    return _nebenweg_abruf(opts, url, "abo") or {}


def _abo_ids(url, limit=60):
    """Video-IDs eines Kanals / einer Playlist (flach) + Titel + info."""
    info = _abo_flach(url, limit)
    titel = info.get("title") or info.get("uploader") or ""
    ids = [e["id"] for e in (info.get("entries") or []) if e and e.get("id")]
    return ids, titel, info


def _abo_baseline(url, limit=60):
    """Erst-Blick fuer Abo-Anlage/Heilung/Kanal-Knopf mit Fallback-Kette
    (Simulations-Funde Build 91): 1. die /videos-Liste; 2. leer? den
    /shorts-Tab — Shorts-only-Kanaele haben KEINEN videos-Tab; 3. immer noch
    leer? die Uploads-Playlist UU<Kanal-Suffix> — Kuenstler-Topic-Kanaele
    (auto-generiert) haben GAR keine Tabs, nur die tragen die Songs.
    Tab-Titel „Kanal - Videos/Shorts" und „Uploads from X" werden zum reinen
    Namen gesaeubert, sonst landet das im Abo-Namen.
    Rueckgabe (tragende_url, ids, titel, info)."""
    ids, titel, info = _abo_ids(url, limit)
    if not ids and url.endswith("/videos"):
        m = re.search(r"/channel/UC([\w-]{10,})$", url[:-len("/videos")])
        ersatzwege = [url[:-len("videos")] + "shorts"]
        if m:
            ersatzwege.append("https://www.youtube.com/playlist?list=UU" + m.group(1))
        for ersatz in ersatzwege:
            e_ids, e_titel, e_info = _abo_ids(ersatz, limit)
            if e_ids:
                url, ids, titel, info = ersatz, e_ids, e_titel, e_info
                break
    titel = re.sub(r"^Uploads from ", "", re.sub(r" - (Videos|Shorts)$", "", titel or ""))
    return url, ids, titel, info


def kanal_info(url, limit=None):
    """Kanal/Playlist ohne Download aufloesen: Name + Videozahl fuer die
    Rueckfrage vor „ganzen Kanal laden". Kanal-Links werden auf /videos
    normalisiert; bis 5000 Videos (wie der Backkatalog-Deckel). Mixe werden
    nur bis zum Wunsch-Limit aufgeloest (schnell statt Endlos-Sanduhr) und
    als mix:true gemeldet."""
    norm = links._kanal_url((url or "").strip())
    if not norm.lower().startswith(("http://", "https://")):
        return {"fehler": "Bitte einen Kanal- oder Playlist-Link einfuegen."}
    mix = links._ist_mix(norm)
    deckel = links._mix_limit(limit) if mix else 5000
    try:
        norm, ids, titel, info = _abo_baseline(norm, limit=deckel)
    except Exception:                                    # noqa: BLE001 — Nutzer sieht Text
        ids, titel, info = [], "", {}
    if not ids:
        return {"fehler": "Kanal/Playlist nicht erreichbar oder ohne Videos."}
    # Dauer-Summe fuer die Groessen-Schaetzung (Build 105): fehlende Dauern
    # werden mit dem Schnitt der vorhandenen hochgerechnet.
    dauern = [e.get("duration") for e in (info.get("entries") or []) if e and e.get("duration")]
    dauer_summe = 0
    if dauern:
        dauer_summe = int(sum(dauern) + (len(ids) - len(dauern)) * (sum(dauern) / len(dauern)))
    return {"ok": True, "name": titel or norm, "anzahl": len(ids),
            "url": norm, "gedeckelt": (not mix) and len(ids) >= 5000, "mix": mix,
            "dauer_summe": dauer_summe}


def entdecken(playlist_id, seeds=3, je_seed=25):
    """📻 Neues entdecken (Build 99/106, JB): Radio-Mixe zu Titeln einer
    Playlist — oder OHNE Playlist zur GANZEN Bibliothek — aufloesen und NUR
    Unbekanntes zurueckgeben (die Bibliothek ist der Filter, YouTube kann
    Bekanntes nicht ausblenden). Bibliotheks-Seeds sind GEWICHTET: bevorzugt
    oft Gespieltes (plays), hoechstens EIN Seed je Kuenstler (Vielfalt);
    Import-Dateien ohne echte YouTube-Id fallen raus. Titel aus MEHREREN
    Seed-Mixen zuerst; die Seeds laufen parallel."""
    rest = youtube_gesperrt()
    if rest:                                          # F4: während einer Sperre nicht fragen
        return {"fehler": "YouTube bremst gerade (Sperre erkannt). Entdecken geht in etwa "
                          f"{max(1, round(rest / 60))} Minuten wieder."}
    try:
        n_seeds = max(1, min(int(seeds), 5))
        n_je = max(5, min(int(je_seed), 100))
    except (TypeError, ValueError):
        n_seeds, n_je = 3, 25
    quelle = "playlist"
    pl = next((p for p in _playlists if p.get("id") == playlist_id), None)
    if pl and pl.get("items"):
        vids = sorted({k.split("|", 1)[0] for k in pl["items"]})
        seed_ids = random.sample(vids, min(n_seeds, len(vids)))
        name = pl.get("name") or ""
    elif playlist_id:
        return {"fehler": "Playlist leer oder nicht gefunden."}
    else:
        quelle, name = "bibliothek", "deine Bibliothek"
        kand = [(k.split("|", 1)[0], e) for k, e in _geladen_schnappschuss()
                if links._plausible_id(k.split("|", 1)[0]) and not e.get("importiert")]
        if not kand:
            return {"fehler": "Keine YouTube-Titel in der Bibliothek gefunden."}
        # DREI Toepfe (Build 107, JB: „was ich oft hoere muss nichts aussagen —
        # manchmal will ich was, das zu den NEU Hinzugefuegten passt"):
        # Seed 1 aus Meistgehoert, Seed 2 aus den Neuesten, Seed 3 Zufall.
        toepfe = [sorted(kand, key=lambda p: -(p[1].get("plays") or 0))[:15],
                  sorted(kand, key=lambda p: -(p[1].get("ts") or 0))[:15],
                  kand]
        seed_ids, kuenstler = [], set()
        for i in range(n_seeds):
            topf = list(toepfe[i % len(toepfe)])
            random.shuffle(topf)
            for vid, e in topf:                        # max 1 Seed je Kuenstler
                wer = (e.get("kuenstler") or e.get("uploader") or vid).lower()
                if vid in seed_ids or wer in kuenstler:
                    continue
                seed_ids.append(vid)
                kuenstler.add(wer)
                break
        if not seed_ids:
            return {"fehler": "Keine YouTube-Titel in der Bibliothek gefunden."}
    bekannt = {k.split("|", 1)[0] for k in _geladen_schluessel()}

    def _ein_seed(sid):
        if youtube_gesperrt():                        # ein früherer Seed traf auf eine Sperre
            return {}
        return _abo_flach(f"https://www.youtube.com/watch?v={sid}&list=RD{sid}",
                          limit=n_je)

    funde = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        for info in ex.map(_ein_seed, seed_ids):
            for pos, e in enumerate((info or {}).get("entries") or []):
                vid = (e or {}).get("id")
                if not vid or vid in bekannt or vid in seed_ids:
                    continue
                f = funde.setdefault(vid, {"id": vid, "titel": e.get("title") or "",
                                           "dauer": e.get("duration"),
                                           "kanal": e.get("channel") or e.get("uploader") or "",
                                           "score": 0, "pos": pos})
                f["score"] += 1
    liste = sorted(funde.values(), key=lambda f: (-f["score"], f["pos"]))
    return {"ok": True, "name": name, "seeds": len(seed_ids),
            "quelle": quelle, "funde": liste}


_dialog_lock = threading.Lock()


def ordner_waehlen(start=""):
    """Nativen Windows-Ordnerdialog auf DIESEM PC oeffnen (Build 108, JB:
    „man sollte im Fenster einen Ordner waehlen koennen") — der Browser darf
    aus Sicherheitsgruenden keine Pfade liefern, der lokale Server schon.
    Nur ein Dialog gleichzeitig; topmost, damit er nicht hinter dem Browser
    verschwindet."""
    if not _dialog_lock.acquire(blocking=False):
        return {"pfad": "", "fehler": "Es ist schon ein Ordner-Dialog offen."}
    try:
        if start and not os.path.isdir(start):
            start = ""                           # toter Merk-Pfad: Dialog neutral starten
        import tkinter as tk
        from tkinter import filedialog
        wurzel = tk.Tk()
        wurzel.withdraw()
        wurzel.attributes("-topmost", True)
        try:
            pfad = filedialog.askdirectory(title="Zielordner wählen",
                                           initialdir=(start or None)) or ""
        finally:
            wurzel.destroy()
        return {"pfad": pfad.replace("/", os.sep)}
    except Exception:                                # noqa: BLE001 — Dialog-Umgebung fehlt
        return {"pfad": "", "fehler": "Ordner-Dialog nicht verfuegbar."}
    finally:
        _dialog_lock.release()


def pfad_da(pfad=""):
    """Existiert der Ordner GERADE? (Build 109, JB-Failsafe: ein gemerkter
    Sync-Pfad auf abgezogener Platte wird im Fenster nur ausgegraut — und
    von selbst wieder frei, sobald das Laufwerk zurueck ist.)"""
    try:
        return {"da": bool(pfad) and os.path.isdir(pfad)}
    except (ValueError, OSError):                    # kaputte Pfadzeichen o. ae.
        return {"da": False}


_MB_FALLBACK = {"audio": 1.5, "720p": 12, "1080p": 22, "1440p": 35, "2160p": 60,
                "beste": 25, "lokal": 25}


def _mb_pro_min(qualitaet):
    """Erfahrungswert MB je Minute fuer eine Qualitaet — MEDIAN aus den echten
    eigenen Downloads (Build 105, JB: „wie viel lade ich ungefaehr?");
    unter 5 Datenpunkten greifen ehrliche Fallback-Werte."""
    # Ausschnitte zaehlen NICHT mit (Build 144q): sie sind keine Downloads,
    # erben aber die Qualitaet ihres Songs — JBs sechs kleine Test-Clips
    # drueckten den Audio-Median von ~10 auf 2,1 MB/min und haetten jede
    # Groessen-Schaetzung verfaelscht.
    werte = sorted(
        (e["groesse"] / 1e6) / (e["dauer"] / 60)
        for k, e in _geladen_schnappschuss()
        if not _ist_clip(k)
        and e.get("qualitaet") == qualitaet and e.get("groesse") and e.get("dauer")
        and e["dauer"] >= 30 and not e.get("importiert"))
    if len(werte) >= 5:
        return round(werte[len(werte) // 2], 1)
    return _MB_FALLBACK.get(qualitaet, _MB_FALLBACK["beste"])


ADDON_UPDATES_URL = ("https://github.com/schn4ppi/SyncYouTube/releases/"
                     "latest/download/updates.json")
_addon_update_cache = {"ts": 0.0, "info": {}}


def addon_update_info():
    """Neueste Addon-Version aus dem Verteil-Kanal (v1.1.1, JB: das Popup soll
    die aktive Version zeigen „und ob es updates gibt").

    Die APP holt die updates.json — nicht das Addon selbst: so braucht die
    Erweiterung keine neue Host-Berechtigung für github.com (jede neue
    Berechtigung = Warn-Dialog bei allen Nutzern). 1-h-Cache, damit kein
    Dauerfeuer auf GitHub entsteht; offline ⇒ leeres Ergebnis, das Popup
    zeigt dann nur die aktive Version.
    """
    jetzt = time.time()
    if jetzt - _addon_update_cache["ts"] < 3600:
        return _addon_update_cache["info"]
    info = {}
    try:
        with urllib.request.urlopen(ADDON_UPDATES_URL, timeout=6) as r:
            daten = json.loads(r.read().decode("utf-8"))
        eintraege = next(iter((daten.get("addons") or {}).values()), {})
        neuste = (eintraege.get("updates") or [{}])[-1]
        if neuste.get("version"):
            info = {"version": neuste["version"],
                    "link": neuste.get("update_link", "")}
    except Exception:                                # noqa: BLE001 — offline ist kein Fehler
        info = {}
    _addon_update_cache.update(ts=jetzt, info=info)
    return info


# v1.1.2 (JB: „wenn ich eine playlist bereits heruntergeladen habe, wird der
# button nicht zum haken"): komplett eingereihte Listen merken. NUR komplette
# Läufe (ohne von/bis) und NIE Mixe — die sind endlos und nie „fertig".
LISTEN_LOG_PFAD = os.path.join(DATEN_DIR, "listen_log.json")
_listen_log = _json_laden(LISTEN_LOG_PFAD, {})       # list_id -> ts


def _liste_vermerken(url, ganze_liste, von, bis):
    if not ganze_liste or von or bis or links._ist_mix(url):
        return
    m = re.search(r"[?&]list=([\w-]+)", url)
    if m:
        _listen_log[m.group(1)] = time.time()
        _json_speichern(LISTEN_LOG_PFAD, _listen_log)


def addon_hab_liste(lid):
    """Fuer die Erweiterung: wurde diese Playlist schon komplett eingereiht?"""
    return {"da": bool(lid and lid in _listen_log)}


def addon_hab(vid):
    """Fuer die Browser-Erweiterung (Build 98, JB): Ist das Video schon in
    der Bibliothek? Reine Key-Suche ueber _geladen (<id>|<qualitaet>)."""
    vid = str(vid or "").strip()
    if not vid:
        return {"da": False, "formate": []}
    formate = sorted({k.split("|", 1)[1] for k in _geladen_schluessel() if k.split("|", 1)[0] == vid})
    return {"da": bool(formate), "formate": formate}


def _abo_feed_url(info):
    """RSS-Feed zu Kanal/Playlist (Pinchflat-Muster „fast indexing": EIN leichter
    GET je Prüfung statt eines yt-dlp-Laufs). Leer, wenn kein Feed ableitbar."""
    cid = str((info or {}).get("channel_id") or "")
    pid = str((info or {}).get("id") or "")
    if cid.startswith("UC"):
        return "https://www.youtube.com/feeds/videos.xml?channel_id=" + cid
    if pid.startswith(("PL", "UU", "OL")):
        return "https://www.youtube.com/feeds/videos.xml?playlist_id=" + pid
    return ""


def _abo_rss_ids(feed):
    """Video-IDs aus dem YouTube-RSS-Feed (die letzten ~15).
    None = Feed nicht erreichbar (dann übernimmt der Voll-Weg)."""
    try:
        req = urllib.request.Request(feed, headers={"User-Agent": "Mozilla/5.0"})
        xml = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
        return re.findall(r"<yt:videoId>([\w-]+)</yt:videoId>", xml)
    except Exception:                                # noqa: BLE001 — Netz/Format
        return None


def _abo_regel_ok(abo, e):
    """Opt-in-Regeln je Abo (Tube-Archivist-Muster: Shorts/Streams/Filter je
    Kanal konfigurierbar): True = Video darf geladen werden. Standard: alles aus.
    Fehlt ein Datenfeld (z.B. upload_date im Flach-Blick), greift die Regel
    bewusst NICHT — lieber laden als still verlieren."""
    f = (abo.get("filter_titel") or "").strip()
    if f and f.lower() not in (e.get("title") or "").lower():
        return False
    if abo.get("ohne_shorts"):
        d = e.get("duration")
        if (d is not None and d <= 62) or "/shorts/" in (e.get("url") or ""):
            return False
    if abo.get("ohne_streams") and (e.get("live_status") or "") in (
            "is_live", "is_upcoming", "was_live", "post_live"):
        return False
    ab = (abo.get("ab_datum") or "").replace("-", "")
    if ab:
        ud = str(e.get("upload_date") or "")
        if ud and ud < ab:
            return False
    return True


def _playlist_einreihen(name, key):
    """Key in eine Playlist mit diesem NAMEN einreihen — anlegen, falls es
    sie noch nicht gibt; nie doppelt (Build 100: die ✨-Entdecker-Downloads
    sammeln sich in „✨ Entdeckt <Datum>", Discover-Weekly-Muster)."""
    if not name or key not in _geladen:
        return
    with _io_lock:
        pl = next((p for p in _playlists if p.get("name") == name), None)
        if pl is None:
            pl = {"id": uuid.uuid4().hex[:8], "name": name, "items": [], "ts": time.time()}
            _playlists.append(pl)
        if key not in pl["items"]:
            pl["items"].append(key)
    _playlists_speichern()


def _abo_playlist_zuordnen(abo_id, key):
    """Fertige Abo-Downloads landen automatisch in der Playlist des Abos
    (JB 20.07., je Abo eine eigene — Pinchflat: je Quelle eine Sammlung).
    Legt die Playlist beim ersten Treffer an; reiht nie doppelt ein."""
    abo = next((a for a in _abos if a.get("id") == abo_id), None)
    if not abo or key not in _geladen:
        return
    with _io_lock:
        pl = next((p for p in _playlists if p.get("id") == abo.get("playlist_id")), None)
        if pl is None:
            pl = {"id": uuid.uuid4().hex[:8], "name": abo.get("name") or "Abo",
                  "items": [], "ts": time.time()}
            _playlists.append(pl)
            abo["playlist_id"] = pl["id"]
            _json_speichern(ABO_PFAD, _abos)
        if key not in pl["items"]:
            pl["items"].append(key)
        e = _geladen.get(key)                          # Folgen-Nummer merken (CD-Track, JB 21.07.)
        if e is not None:
            e["abo"] = abo_id
            nr = _abo_nr(abo_id, key.split("|")[0])
            if nr:
                e["abo_nr"] = nr
            _geladen_speichern()
    _playlists_speichern()


def abo_aktion(daten):
    art = daten.get("art")
    if art == "create":
        url = (str(daten.get("url") or "")).strip()
        if not url.lower().startswith(("http://", "https://")):
            return {"fehler": "Bitte einen Kanal- oder Playlist-Link angeben."}
        url = links._kanal_url(url)                         # blosser Kanal-Link liefert nur die REITER (Build 91)
        qual = daten.get("qualitaet") if daten.get("qualitaet") in QUALITAETEN else CFG["standard_qualitaet"]
        url, ids, titel, info = _abo_baseline(url)    # Baseline merken, NICHT laden
        abo = {"id": uuid.uuid4().hex[:8], "url": url, "name": titel or url,
               "qualitaet": qual, "bekannt": ids, "ts": time.time(), "neu": 0,
               "feed": _abo_feed_url(info)}
        if not info:
            # YouTube hat nicht geantwortet (Sperre, Netz). Eine leere Baseline
            # hielte beim nächsten Puls jede Folge für neu; also holt der
            # nächste Puls sie nach, ohne zu laden (_abo_heilen, Nacharbeit F4).
            abo["basis_offen"] = True
        with _io_lock:
            _abos.append(abo)
            _json_speichern(ABO_PFAD, _abos)
        return {"ok": True, "id": abo["id"], "name": abo["name"], "basis": len(ids)}
    if art == "delete":
        abo = next((a for a in _abos if a.get("id") == daten.get("id")), None)
        geloescht = 0
        if abo and daten.get("mit_videos"):
            # JB (Build 95): optional die UEBER DIESES ABO geladenen Videos mit
            # entfernen — NUR Inhalte der eigenen Abo-Playlist (Kriterium wie
            # abo_aufraeumen), Datei in den Windows-Papierkorb (wiederherstellbar);
            # manuell Geladenes bleibt unberuehrt.
            pl = next((p for p in _playlists if p.get("id") == abo.get("playlist_id")), None)
            for key in list((pl or {}).get("items") or []):
                if key not in _geladen:
                    continue
                with _io_lock:
                    _datei_loeschen(key)
                    _geladen.pop(key, None)
                geloescht += 1
            with _io_lock:
                if pl is not None:
                    _playlists[:] = [p for p in _playlists if p.get("id") != pl.get("id")]
                _geladen_speichern()
            _playlists_speichern()
        if abo:                                       # Folgen-Cache des Abos ist jetzt Waise
            _abo_index_entfernen(abo.get("id"))
        with _io_lock:
            _abos[:] = [a for a in _abos if a.get("id") != daten.get("id")]
            _json_speichern(ABO_PFAD, _abos)
        return {"ok": True, "geloescht": geloescht}
    if art == "pruefen":
        return {"ok": True, "neu": abos_pruefen()}
    if art == "aendern":                              # Format + Regeln nachträglich (JB 20.07.)
        with _io_lock:
            for a in _abos:
                if a.get("id") != daten.get("id"):
                    continue
                if daten.get("qualitaet") in QUALITAETEN:
                    a["qualitaet"] = daten["qualitaet"]
                for feld in ("filter_titel", "ab_datum"):
                    if feld in daten:
                        a[feld] = str(daten.get(feld) or "").strip()[:120]
                for feld in ("ohne_shorts", "ohne_streams"):
                    if isinstance(daten.get(feld), bool):
                        a[feld] = daten[feld]
                if "loeschen_nach_tagen" in daten:
                    try:
                        a["loeschen_nach_tagen"] = max(0, int(daten.get("loeschen_nach_tagen") or 0))
                    except (TypeError, ValueError):
                        pass
            _json_speichern(ABO_PFAD, _abos)
        return {"ok": True}
    if art == "folgen":                               # Backkatalog fürs Abo-Fenster
        return abo_folgen(daten.get("id") or "", bool(daten.get("aktualisieren")))
    if art == "folgen_laden":                         # markierte Folgen nachladen
        return abo_folgen_laden(daten.get("id") or "", daten.get("vids") or [])
    if art == "erneuern":                             # alles Geladene im Abo-Format neu
        return abo_erneuern(daten.get("id") or "", bool(daten.get("ersetzen")))
    return {"fehler": "unbekannt"}


def _abo_heilen(abo):
    """Bestands-Abo mit blossem Kanal-Link heilen (Build-91-Selbstheilung):
    Abos aus der Zeit vor der _kanal_url-Normalisierung merkten sich nur die
    Kanal-REITER als Baseline („#1 Shorts / #2 Videos" statt Folgen, JB-Fund).
    Heilt in einem Zug: URL auf /videos normalisieren, Baseline NEU holen
    (ohne einen einzigen Download — sonst Lawine: die Reiter-Baseline kennt
    keine echten Video-IDs), Feed neu ableiten, Reiter-Folgen-Cache verwerfen.
    Nicht-destruktiv: schlaegt der Netz-Abruf fehl, bleibt ALLES unveraendert
    (naechster Anlauf beim folgenden Puls). Rueckgabe (ok, geheilt):
    (True, False) = war schon sauber, (True, True) = frisch geheilt,
    (False, False) = Heilung noetig, aber Kanal nicht erreichbar.
    Ebenso geheilt wird ein Abo, dessen Anlage keine Antwort von YouTube
    bekam (`basis_offen`, Nacharbeit F4); ein leerer Kanal zählt dort als
    Antwort."""
    url = str(abo.get("url") or "")
    norm = links._kanal_url(url)
    offen = bool(abo.get("basis_offen"))
    reiter_link = norm != url                         # Alt-Abo: sein Folgen-Cache zeigte Reiter
    if not (reiter_link or offen):
        return True, False
    norm, ids, titel, info = _abo_baseline(norm)
    if not ids and not (offen and info):
        return False, False
    with _io_lock:
        abo["url"] = norm
        abo["bekannt"] = ids                          # Baseline neu, NICHT laden (wie create)
        abo.pop("basis_offen", None)
        abo["feed"] = _abo_feed_url(info) or abo.get("feed") or ""
        if titel and (not abo.get("name") or abo["name"] == url):
            abo["name"] = titel
        abo["geprueft"] = time.time()
        _json_speichern(ABO_PFAD, _abos)
    pfad = os.path.join(ABO_INDEX_ORDNER, f"{abo.get('id')}.json")
    try:
        if reiter_link and os.path.exists(pfad):
            os.remove(pfad)                           # reiner Ableitungs-Cache (zeigte Reiter) — wird frisch geholt
    except OSError:
        pass
    return True, True


def abos_pruefen():
    """Alle Abos auf neue Videos prüfen und Neues in die Warteschlange legen.
    Gibt die Zahl neu eingereihter Videos zurück. Leichter Puls zuerst:
    der RSS-Feed sagt billig, OB es Neues gibt — nur dann läuft der volle
    flat-extract (Details für die Regeln)."""
    gesamt = 0
    for abo in list(_abos):
        if youtube_gesperrt():                        # F4: Sperre -> Pause, der nächste Puls holt nach
            break
        ok, geheilt = _abo_heilen(abo)
        if not ok or geheilt:
            continue                                  # Netz weg ⇒ naechster Puls; geheilt ⇒ Baseline ist sekundenfrisch
        feed = abo.get("feed") or ""
        if feed:
            rss = _abo_rss_ids(feed)
            if rss is not None and set(rss) <= set(abo.get("bekannt") or []):
                with _io_lock:
                    abo["geprueft"] = time.time()
                    _json_speichern(ABO_PFAD, _abos)
                continue
        info = _abo_flach(abo.get("url", ""))
        entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
        if not entries:
            continue
        ids = [e["id"] for e in entries]
        titel = info.get("title") or info.get("uploader") or ""
        bekannt = set(abo.get("bekannt") or [])
        neu = [e for e in entries if e["id"] not in bekannt]
        for e in neu:
            if not _abo_regel_ok(abo, e):
                continue
            url = f"https://www.youtube.com/watch?v={e['id']}"
            if _schon_da(url, abo["qualitaet"]) or schon_geladen(url, abo["qualitaet"]):
                continue
            threading.Thread(target=aufloesen, args=(url, abo["qualitaet"]),
                             kwargs={"abo": abo["id"]}, daemon=True).start()
            gesamt += 1
        with _io_lock:
            abo["bekannt"] = ids
            if not abo.get("feed"):
                abo["feed"] = _abo_feed_url(info)
            if titel and (not abo.get("name") or abo["name"] == abo["url"]):
                abo["name"] = titel
            abo["neu"] = abo.get("neu", 0) + len(neu)
            abo["geprueft"] = time.time()
            _json_speichern(ABO_PFAD, _abos)
    try:
        abo_aufraeumen()                              # Auto-Löschen (Opt-in), gleicher 6-h-Takt
    except Exception:                                 # noqa: BLE001
        pass
    return gesamt


ABO_INDEX_ORDNER = os.path.join(DATEN_DIR, "abo_index")
_ABO_ID_FORM = re.compile(r"[0-9a-f]{8}")             # uuid4().hex[:8], s. abo_aktion("create")


def _abo_index_entfernen(abo_id):
    """Folgen-Cache eines entfernten Abos in den Papierkorb (Gesamtprüfung S1).
    Nur für eine Id in der Form, die `create` vergibt: die Id stammt aus der
    Anfrage, und `..\\`, ein absoluter oder ein UNC-Pfad hätten sonst eine
    beliebige `.json` getroffen. Scheitert der Papierkorb, bleibt der Cache
    liegen (er ist nur abgeleitet und wird nie wieder gelesen)."""
    abo_id = str(abo_id or "")
    if not _ABO_ID_FORM.fullmatch(abo_id):
        return False
    pfad = os.path.join(ABO_INDEX_ORDNER, f"{abo_id}.json")
    return os.path.isfile(pfad) and bool(_in_papierkorb(pfad))


def abo_folgen(abo_id, aktualisieren=False):
    """Kompletter Backkatalog eines Abos (Sonarr-Muster: Episodenliste mit
    Lade-Status). Der Voll-Blick ist teuer (bis 5000 Folgen) -> Datei-Cache
    je Abo in System/abo_index/; aktualisieren=True holt frisch."""
    abo = next((a for a in _abos if a.get("id") == abo_id), None)
    if not abo:
        return {"fehler": "Abo nicht gefunden."}
    ok, _ = _abo_heilen(abo)                          # Alt-Abo? Erst heilen — nie wieder Reiter als „Folgen" zeigen
    if not ok:
        return {"fehler": "Kanal nicht erreichbar — später erneut versuchen."}
    os.makedirs(ABO_INDEX_ORDNER, exist_ok=True)
    pfad = os.path.join(ABO_INDEX_ORDNER, f"{abo_id}.json")
    cache = _json_laden(pfad, {})
    if aktualisieren or not cache.get("folgen"):
        info = _abo_flach(abo.get("url", ""), limit=5000)
        folgen = [{"id": e["id"], "titel": e.get("title") or "",
                   "dauer": e.get("duration"), "live": e.get("live_status") or ""}
                  for e in (info.get("entries") or []) if e and e.get("id")]
        if folgen:
            cache = {"ts": time.time(), "folgen": folgen}
            _json_speichern(pfad, cache)
        elif not cache.get("folgen"):
            return {"fehler": "Kanal nicht erreichbar — später erneut versuchen."}
    nach_vid = {}
    for k in _geladen_schluessel():
        vid, _, q = k.partition("|")
        nach_vid.setdefault(vid, []).append(q)
    out = []
    gesamt = len(cache["folgen"])
    for i, f in enumerate(cache["folgen"]):           # Liste ist neueste-zuerst
        quals = nach_vid.get(f["id"]) or []
        out.append({**f, "nr": gesamt - i,            # CD-Muster: älteste = 1, neueste = gesamt
                    "geladen": bool(quals), "formate": quals,
                    "passend": abo.get("qualitaet") in quals})
    return {"ok": True, "ts": cache.get("ts"), "id": abo_id, "gesamt": gesamt,
            "qualitaet": abo.get("qualitaet"), "folgen": out}


def _abo_nr(abo_id, vid):
    """Folgen-Nummer (CD-Track) eines Videos aus dem Backkatalog-Cache:
    älteste Folge = 1, neueste = Gesamtzahl. 0, wenn nicht im Cache."""
    pfad = os.path.join(ABO_INDEX_ORDNER, f"{abo_id}.json")
    folgen = _json_laden(pfad, {}).get("folgen") or []
    for i, f in enumerate(folgen):
        if f.get("id") == vid:
            return len(folgen) - i
    return 0


def abo_folgen_laden(abo_id, vids):
    """Markierte Backkatalog-Folgen im Abo-Format laden (JB 20.07.: „eigene
    Playlist vervollständigen"). Schon Vorhandenes wird nur der Abo-Playlist
    zugeordnet, nicht neu geladen."""
    abo = next((a for a in _abos if a.get("id") == abo_id), None)
    if not abo:
        return {"fehler": "Abo nicht gefunden."}
    neu, zugeordnet = 0, 0
    for vid in list(vids)[:5000]:
        if not re.fullmatch(r"[\w-]{6,}", str(vid) or ""):
            continue
        url = f"https://www.youtube.com/watch?v={vid}"
        key = f"{vid}|{abo.get('qualitaet')}"
        if key in _geladen:
            _abo_playlist_zuordnen(abo_id, key)
            zugeordnet += 1
            continue
        if _schon_da(url, abo.get("qualitaet")):
            continue
        threading.Thread(target=aufloesen, args=(url, abo.get("qualitaet")),
                         kwargs={"abo": abo_id}, daemon=True).start()
        neu += 1
    return {"ok": True, "neu": neu, "zugeordnet": zugeordnet}


def abo_erneuern(abo_id, ersetzen=False):
    """Alles bisher Geladene des Abos im AKTUELLEN Abo-Format neu holen
    (JB 20.07., nach Format-Wechsel). ersetzen=True: die alte Datei im anderen
    Format wandert NACH dem Erfolg in den Papierkorb (nie vorher!)."""
    abo = next((a for a in _abos if a.get("id") == abo_id), None)
    if not abo:
        return {"fehler": "Abo nicht gefunden."}
    stand = abo_folgen(abo_id)
    if not stand.get("ok"):
        return stand
    qual = abo.get("qualitaet")
    neu = 0
    for f in stand["folgen"]:
        if not f["geladen"] or f["passend"]:
            continue                                  # fehlt ganz oder passt schon
        url = f"https://www.youtube.com/watch?v={f['id']}"
        if _schon_da(url, qual):
            continue
        alte = [f"{f['id']}|{q}" for q in f["formate"] if q != qual] if ersetzen else []
        threading.Thread(target=aufloesen, args=(url, qual),
                         kwargs={"abo": abo_id, "ersetzt": alte}, daemon=True).start()
        neu += 1
    return {"ok": True, "neu": neu}


def abo_aufraeumen():
    """Auto-Löschen alter Abo-Folgen (Opt-in je Abo, loeschen_nach_tagen>0):
    NUR Inhalte der eigenen Abo-Playlist, Datei in den Windows-Papierkorb,
    Eintrag vergessen — nie die übrige Bibliothek anfassen."""
    n = 0
    for abo in list(_abos):
        try:
            tage = int(abo.get("loeschen_nach_tagen") or 0)
        except (TypeError, ValueError):
            tage = 0
        pl = next((p for p in _playlists if p.get("id") == abo.get("playlist_id")), None)
        if tage <= 0 or not pl:
            continue
        grenze = time.time() - tage * 86400
        for key in list(pl.get("items") or []):
            e = _geladen.get(key)
            if not e or (e.get("ts") or time.time()) > grenze:
                continue
            with _io_lock:
                _datei_loeschen(key)                  # Papierkorb + aus allen Playlists
                _geladen.pop(key, None)
            n += 1
    if n:
        _geladen_speichern()
        _playlists_speichern()
        _sag(f"Abo-Aufräumen: {n} alte Folge(n) in den Papierkorb")
    return n


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
    vid = key.split("|")[0]
    if not links._plausible_id(vid):
        return False
    opts = _ydl_basis_opts()
    opts.update({"skip_download": True, "noplaylist": True})
    info = _nebenweg_abruf(opts, f"https://www.youtube.com/watch?v={vid}", "anreichern")
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


_technik_lauf = _LaeuftSchon()


_metadaten_lauf = _LaeuftSchon()


def _hat_metadaten(pfad, ffprobe):
    """True, wenn die Datei bereits einen Titel-Tag hat (dann nichts nachtragen)."""
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format_tags=title",
             "-of", "default=noprint_wrappers=1:nokey=1", pfad],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
        return bool((out.stdout or "").strip())
    except (OSError, subprocess.SubprocessError):
        return True                                   # im Zweifel NICHT anfassen


def metadaten_backfill():
    """Fehlende Titel/Künstler/Datum in tag-losen Dateien nachtragen (Selbstheilung,
    v.a. fuer per Ordner-Import aufgenommene Fremddateien; von der App selbst
    geladene Dateien bekommen die Tags schon beim Download). Quelle ist die
    geladen-DB (yt-dlp-Titel/Uploader/Datum). Non-destruktiv: ffmpeg
    `-c copy` bewahrt Audio UND Cover, geschrieben wird atomar (tmp + replace);
    Dateien, die schon einen Titel-Tag haben, bleiben unberührt."""
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg or not _metadaten_lauf.starten():
        return 0
    ffprobe = os.path.join(BIN_DIR, "ffprobe.exe")
    geheilt = 0
    try:
        idx = _datei_index()
        for key, e in _geladen_schnappschuss():
            titel = (e.get("titel") or "").strip()
            if not titel:
                continue
            p = e.get("pfad")
            pfad = p if (p and os.path.isfile(p)) else _datei_aus(idx.get(key.split("|")[0]), key.partition("|")[2])
            if not pfad or not os.path.isfile(pfad):
                continue
            if _hat_metadaten(pfad, ffprobe):
                continue
            stem, ext = os.path.splitext(pfad)
            tmp = stem + ".mdtmp" + ext
            meta = ["-metadata", "title=" + titel]
            if e.get("uploader"):
                meta += ["-metadata", "artist=" + str(e["uploader"])]
            if e.get("upload_date"):
                meta += ["-metadata", "date=" + str(e["upload_date"])]
            if e.get("url"):
                meta += ["-metadata", "comment=" + str(e["url"])]
            try:
                r = subprocess.run(
                    [ffmpeg, "-y", "-i", pfad, "-c", "copy", "-map_metadata", "0"] + meta + [tmp],
                    capture_output=True, timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                if r.returncode == 0 and os.path.isfile(tmp) and os.path.getsize(tmp) > 0:
                    os.replace(tmp, pfad)
                    geheilt += 1
                elif os.path.exists(tmp):
                    os.remove(tmp)
            except (OSError, subprocess.SubprocessError):
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except OSError:
                    pass
        if geheilt:
            _sag(f"Metadaten nachgetragen: {geheilt} Alt-Datei(en) haben jetzt Titel/Künstler")
    finally:
        _metadaten_lauf.fertig()
    return geheilt


def technik_backfill():
    """Codec/Qualität + Content-Fingerabdruck für vorhandene Dateien nachtragen,
    die es noch nicht haben (ffprobe bzw. 2 schnelle Reads, lokal, offline).
    Läuft einmal im Hintergrund beim Start; danach trägt jeder Eintrag sein fp
    dauerhaft (Bibliothek 2.0: Wiedererkennen ohne [Id] im Namen)."""
    if not _technik_lauf.starten():
        return
    try:
        idx = _datei_index()
        geaendert = False
        for k, e in _geladen_schnappschuss():
            if e.get("acodec") and e.get("fp") and e.get("idtag") is not None:
                continue
            vid = k.split("|")[0]
            pfad = (e.get("pfad") if e.get("pfad") and os.path.isfile(e.get("pfad"))
                    else _datei_aus(idx.get(vid), k.partition("|")[2]))
            if not pfad:
                continue
            if not e.get("acodec"):
                t = _technik(pfad)
                if t:
                    e.update({"vcodec": t.get("vcodec", ""), "acodec": t.get("acodec", ""),
                              "abr": t.get("abr", 0), "asr": t.get("asr", 0),
                              "hoehe": t.get("height", 0) or e.get("hoehe", 0)})
                    geaendert = True
            if e.get("idtag") is None:
                # Id-Tag nur in EIGENE Downloads (nie in importierte Fremd-
                # Dateien schreiben) — und VOR dem fp, weil das Tag den
                # Dateianfang verschiebt. idtag=False heißt: versucht/gelassen,
                # nicht jede Runde neu anfassen.
                if e.get("importiert"):
                    e["idtag"] = False
                else:
                    e["idtag"] = (_id_tag_lesen(pfad) == vid) or _id_tag_schreiben(pfad, vid)
                    if e["idtag"]:
                        e["groesse"] = os.path.getsize(pfad)
                        e["fp"] = _fp_von(pfad)      # Tag hat den Inhalt verschoben
                geaendert = True
            if not e.get("fp"):
                fp = _fp_von(pfad)
                if fp:
                    e["fp"] = fp
                    geaendert = True
        if geaendert:
            _geladen_speichern()
    finally:
        _technik_lauf.fertig()


# ---- Namens-Baukasten (Build 113, JB: „die Art der Beschreibung wählen und
# schieben können"). Wahrheit sind die Tags/DB-Felder; der Dateiname ist nur
# eine Projektion daraus — wie Picard-Naming-Scripts und beets-path-formats.
NAME_BAUSTEINE = {                                    # id -> (Anzeige, Feld)
    "nr":       ("Titelnummer (07)", "track_nr"),
    "kuenstler": ("Künstler", "kuenstler"),
    "titel":    ("Titel", "track"),
    "album":    ("Album", "album"),
    "jahr":     ("Jahr", "jahr"),
    "zusatz":   ("Zusatz (Live/Remix)", "_zusatz"),
    "id":       ("Video-Id [abc123]", "_id"),
}
NAME_STANDARD = ["kuenstler", "titel", "zusatz"]      # JB-Entscheid: Künstler - Titel (Live)
# Klammer-Inhalte, die nur Format/Kanal beschreiben -> raus. „Live/Remix/
# Acoustic/Cover/Instrumental/Remastered" beschreiben die AUFNAHME -> bleiben
# (als Baustein „zusatz").
_NAME_MUELL = re.compile(
    r"(?i)[\(\[]\s*(?:official\s*)?(?:music\s*)?(?:video|audio|hd|hq|full\s*hd|4k|8k|uhd"
    r"|lyrics?|lyric\s*video|visualiz\w*|mv|m/v|clip|videoclip|hq\s*audio|explicit|clean"
    r"|official|offizielles?\s*\w*)\s*[\)\]]")
_NAME_ZUSATZ = re.compile(
    r"(?i)[\(\[]\s*((?:live|akustik|acoustic|unplugged|remix|rmx|cover|instrumental"
    r"|karaoke|remaster\w*|demo|radio\s*edit|extended|edit)[^\)\]]*)\s*[\)\]]")


def _name_teile(e, pfad=""):
    """DB-Eintrag -> Bausteine für den Dateinamen (bereits gesäubert)."""
    roh = e.get("titel") or musik_einstufung._titel_aus_name(os.path.basename(pfad or e.get("name", "")))
    roh = re.sub(r"\s*\[[\w-]{6,}\]", "", roh)        # [Video-Id] gehört nie in den Text
    zusatz = " ".join(f"({m.group(1).strip()})" for m in _NAME_ZUSATZ.finditer(roh))
    rest = _NAME_ZUSATZ.sub(" ", _NAME_MUELL.sub(" ", roh))
    rest = re.sub(r"\s+", " ", rest).strip(" -–—|·,")
    kuenstler = (e.get("kuenstler") or "").strip()
    titel = (e.get("track") or "").strip()
    if not (kuenstler and titel):                     # kein Auto-Tag: aus dem Titel spalten
        for sep in (" - ", " – ", " — "):
            if sep in rest:
                links, rechts = rest.split(sep, 1)
                kuenstler = kuenstler or links.strip()
                titel = titel or rechts.strip()
                break
    nr = e.get("track_nr")
    return {"nr": f"{int(nr):02d}" if str(nr or "").strip().isdigit() else "",
            "kuenstler": kuenstler, "titel": titel or rest,
            "album": (e.get("album") or "").strip(), "jahr": str(e.get("jahr") or "").strip(),
            "zusatz": zusatz, "id": ""}


def _dateiname_bauen(e, pfad="", schema=None):
    """Bausteine in der gewählten Reihenfolge zu EINEM Dateinamen fügen.
    Trenner nach Bedeutung: Künstler - Titel, Nummer davor, Zusatz/Album/Jahr
    in Klammern hinten. Ohne verwertbare Teile: '' (Aufrufer lässt den Namen)."""
    schema = schema or CFG.get("name_schema") or NAME_STANDARD
    t = _name_teile(e, pfad)
    if e.get("_vid"):
        t["id"] = f"[{e['_vid']}]"
    kopf, klammern = [], []
    for baustein in schema:
        wert = t.get(baustein, "")
        if not wert:
            continue
        if baustein in ("zusatz", "album", "jahr", "id"):
            klammern.append(wert if wert.startswith(("(", "[")) else f"({wert})")
        else:
            kopf.append(wert)
    if not kopf:
        return ""
    # Die Titelnummer klebt ohne Gedankenstrich am Rest („07 Künstler - Titel"),
    # alle anderen Kopf-Bausteine werden mit " - " verbunden.
    if schema and schema[0] == "nr" and t.get("nr"):
        text = kopf[0] + " " + " - ".join(kopf[1:]) if len(kopf) > 1 else kopf[0]
    else:
        text = " - ".join(kopf)
    if klammern:
        text += " " + " ".join(klammern)
    return _dateiname_saeubern(text)


def _dateiname_saeubern(text):
    """Windows-sichere, hübsche Fassung (keine verbotenen Zeichen, kein
    Punkt/Leerzeichen am Ende, nicht länger als 150 Zeichen)."""
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:150].strip(" .")


def _migrations_ziel(pfad, e=None, schema=None):
    """Neuer Pfad nach dem Namens-Schema ('' wenn nichts zu tun ist).
    Ohne DB-Eintrag: nur die [Id]-Klammern entfernen (Alt-Verhalten)."""
    ordner, name = os.path.split(pfad)
    stamm, ext = os.path.splitext(name)
    if e is None:
        neu = re.sub(r"\s*\[[\w-]{6,}\]", "", stamm).strip()
    else:
        neu = _dateiname_bauen(e, pfad, schema)
    neu = _dateiname_saeubern(neu or "")
    if not neu or neu == stamm:
        return ""
    return os.path.join(ordner, neu + ext)


def _vtt_geschwister(pfad):
    """Untertitel NEBEN der Mediendatei, die deren Stamm teilen — sie müssen
    bei einer Umbenennung MIT wandern (Stamm-Kopplung, sonst verwaisen sie).
    Auch .srt: yt-dlp liefert je nach Quelle SubRip statt WebVTT — genau so
    verwaiste ein Grim-Dawn-Untertitel (JB-Fund, Kleinkram 05.08.)."""
    stamm = os.path.splitext(pfad)[0]
    treffer = []
    for endung in (".vtt", ".srt"):
        treffer += glob.glob(glob.escape(stamm) + ".*" + endung)
        treffer += glob.glob(glob.escape(stamm) + endung)
    return sorted(treffer)


PROTOKOLL_PFAD = os.path.join(DATEN_DIR, "migration_protokoll.json")


def migration_probelauf(schema=None, keys=None):
    """Umbenenn-Probelauf (schaut NUR, fasst nichts an): je Datei der neue
    Name nach dem gewählten Schema, die mitwandernden .vtt und der
    Sicherheits-Status. Umbenannt wird ausschließlich in migration_anwenden —
    und das erst nach JBs Blick auf diese Liste (Probelauf-Default)."""
    plan, ziele = [], set()
    for k, e in _geladen_schnappschuss():
        if keys and k not in keys:
            continue
        p = e.get("pfad")
        if not (p and os.path.isfile(p)):
            continue
        eintrag_daten = dict(e)
        eintrag_daten["_vid"] = k.split("|")[0]
        ziel = _migrations_ziel(p, eintrag_daten, schema)
        if not ziel:
            continue
        eintrag = {"key": k, "alt": p, "neu": ziel,
                   "vtt": _vtt_geschwister(p), "konflikt": ""}
        if not (e.get("fp") or e.get("idtag")):
            eintrag["konflikt"] = "ohne Sicherheitsnetz (kein fp/Tag) — erst Backfill laufen lassen"
        elif os.path.exists(ziel) or os.path.normcase(ziel) in ziele:
            eintrag["konflikt"] = "Zielname existiert schon (gleicher Titel, andere Fassung?)"
        ziele.add(os.path.normcase(ziel))
        plan.append(eintrag)
    return plan


def migration_anwenden(go=False, schema=None, keys=None):
    """Umbenennen Schritt 2 — läuft NUR mit go=True (nach JBs Blick auf den
    Probelauf). Additiv: nie überschreiben, Konflikte bleiben unangetastet
    liegen, DB (pfad/name) wandert mit, .vtt-Geschwister behalten ihren
    Stamm. Bricht etwas ab, bleiben alte Namen einfach stehen — die
    Erkennungs-Kette (Name/Pfad/fp/Tag) trägt beide Welten."""
    if not go:
        return {"ok": False, "fehler": "Probelauf-Default: ohne go wird nichts umbenannt."}
    umbenannt, uebersprungen, protokoll = 0, 0, []
    for eintrag in migration_probelauf(schema, keys):
        if eintrag["konflikt"]:
            uebersprungen += 1
            continue
        alt, neu = eintrag["alt"], eintrag["neu"]
        try:
            if os.path.exists(neu):
                uebersprungen += 1
                continue
            e = _geladen.get(eintrag["key"])
            # Ursprungsnamen IN die Datei (JB) — VOR dem Umbenennen, damit
            # der Vermerk den echten Originalnamen trägt; danach fp erneuern,
            # weil das Tag den Dateianfang verschiebt.
            if e and not e.get("importiert") and _orig_tag(alt, os.path.basename(alt)):
                if e.get("fp"):
                    e["fp"] = _fp_von(alt)
                try:
                    e["groesse"] = os.path.getsize(alt)
                except OSError:
                    pass
            os.rename(alt, neu)
            protokoll.append([alt, neu])
            alt_stamm = os.path.splitext(alt)[0]
            neu_stamm = os.path.splitext(neu)[0]
            for v in eintrag["vtt"]:
                zv = neu_stamm + v[len(alt_stamm):]
                if not os.path.exists(zv):
                    os.rename(v, zv)
                    protokoll.append([v, zv])
            if e:
                e["pfad"] = neu
                e["name"] = os.path.basename(neu)
                # Build 140 (JB: „Dateinamen sind jetzt umbenannt, doch in der
                # Bibliothek nicht. Warum?"): Die Anzeige hängt am Feld
                # `titel` — das blieb der rohe YouTube-Titel, während die
                # Datei längst anders hieß. Der Dateiname ist die Wahrheit,
                # die JB sieht; die Anzeige folgt ihm. Der ursprüngliche
                # Titel wird dabei GESICHERT statt überschrieben: er ist die
                # Grundlage für Suche und Auto-Tagging.
                if not e.get("titel_orig"):
                    e["titel_orig"] = e.get("titel") or ""
                e["titel"] = musik_einstufung._titel_aus_name(e["name"])
            umbenannt += 1
        except OSError:
            uebersprungen += 1
    if umbenannt:
        # Rückroll-Protokoll AUF PLATTE (Lehre 23.07.: ein Zurück muss immer
        # trivial sein, nie rekonstruiert werden müssen) — additiv je Lauf.
        try:
            laeufe = _json_laden(PROTOKOLL_PFAD, [])
            laeufe.append({"zeit": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "umbenannt": protokoll})
            _json_speichern(PROTOKOLL_PFAD, laeufe)
        except OSError:
            pass
        _geladen_speichern()
        _sag(f"Umbenennen: {umbenannt} Datei(en) neu benannt, {uebersprungen} übersprungen")
    return {"ok": True, "umbenannt": umbenannt, "uebersprungen": uebersprungen}


def migration_laeufe():
    """Was wurde wann umbenannt? (Grundlage für „↩ Rückgängig")"""
    return [{"zeit": lauf.get("zeit", ""), "anzahl": len(lauf.get("umbenannt") or [])}
            for lauf in _json_laden(PROTOKOLL_PFAD, [])]


def migration_rueckgaengig():
    """Den LETZTEN Umbenenn-Lauf zurücknehmen (JB: „man sollte es auch wieder
    rückgängig machen können"). Rückwärts durchs Protokoll; nur wo die Datei
    noch am neuen Ort liegt UND der alte Name frei ist — sonst bleibt der
    Eintrag stehen und wird gemeldet (nie überschreiben)."""
    laeufe = _json_laden(PROTOKOLL_PFAD, [])
    if not laeufe:
        return {"ok": False, "fehler": "Es gibt keinen Umbenenn-Lauf zum Zurücknehmen."}
    lauf = laeufe[-1]
    zurueck, blockiert = 0, 0
    pfad_zu_key = {os.path.normcase(os.path.abspath(e["pfad"])): k
                   for k, e in _geladen_schnappschuss() if e.get("pfad")}
    for alt, neu in reversed(lauf.get("umbenannt") or []):
        try:
            if not os.path.isfile(neu) or os.path.exists(alt):
                blockiert += 1
                continue
            os.rename(neu, alt)
            k = pfad_zu_key.get(os.path.normcase(os.path.abspath(neu)))
            e = _geladen.get(k) if k else None
            if e:
                e["pfad"] = alt
                e["name"] = os.path.basename(alt)
            zurueck += 1
        except OSError:
            blockiert += 1
    if zurueck:
        _geladen_speichern()
    if not blockiert:                                # Lauf ist sauber zurückgenommen
        laeufe.pop()
    else:                                            # Rest vermerken statt Protokoll verlieren
        lauf["umbenannt"] = [pp for pp in (lauf.get("umbenannt") or [])
                             if os.path.isfile(pp[1])]
        if not lauf["umbenannt"]:
            laeufe.pop()
    try:
        _json_speichern(PROTOKOLL_PFAD, laeufe)
    except OSError:
        pass
    _sag(f"Rückgängig: {zurueck} Datei(en) tragen wieder den alten Namen"
         + (f", {blockiert} blockiert" if blockiert else ""))
    return {"ok": True, "zurueck": zurueck, "blockiert": blockiert}


# ---- Downloads-Ordner selbstheilend einsortieren (JB 14.07.): von Hand
# verschobene Dateien wandern anhand ihrer Metadaten zurück in den richtigen
# Kategorie-Ordner (MP3 / 4K+ / Video); was unklar bleibt, kommt nach
# "Sonstiges" statt falsch einsortiert zu werden.

SONSTIGES = "Sonstiges"
_einsortier_lauf = _LaeuftSchon()


def _soll_kategorie(pfad, karten=None):
    """Kategorie einer Datei im Downloads-Ordner: Audio-Endung -> MP3;
    Video -> Höhe aus der geladen-DB (Video-Id über die zentrale Kette) oder
    per ffprobe; '' = keine Mediendatei (nicht anfassen), None = unklar."""
    ext = os.path.splitext(pfad)[1].lower()
    if ext in musik_einstufung.AUDIO_EXT:
        return "MP3"
    if ext not in musik_einstufung.VIDEO_EXT:
        return ""
    vid = _datei_videoid(pfad, karten)
    if vid:
        for k, e in _geladen_schnappschuss():
            if k.split("|")[0] == vid and e.get("hoehe"):
                return _kategorie("", e.get("hoehe"))
    h = _hoehe_ffprobe(pfad)
    return _kategorie("", h) if h else None


def downloads_einsortieren():
    """Bewegt Mediendateien INNERHALB des Downloads-Ordners an ihren Platz.
    Nicht-destruktiv: nie überschreiben (nummerierter Name), .part/.vtt/Bilder
    und frisch geänderte Dateien (<60 s, evtl. noch in Arbeit) bleiben liegen,
    Playlist-Sync-Ziele im Downloads-Ordner sind tabu (Spiegel-Kopien)."""
    if not CFG.get("unterordner", True) or not _einsortier_lauf.starten():
        return 0
    bewegt = 0
    try:
        basis = os.path.abspath(ziel_ordner())
        tabu = [os.path.abspath(p["sync_ordner"]) for p in _playlists if p.get("sync_ordner")]
        karten = _id_karten()                        # einmal bauen, je Datei nachschlagen
        for wurzel, dirs, dateien in _walk_ohne_rueckhol(basis):
            w = os.path.abspath(wurzel)
            if any(w == t or w.startswith(t + os.sep) for t in tabu):
                dirs[:] = []
                continue
            for fn in dateien:
                pfad = os.path.join(wurzel, fn)
                kat = _soll_kategorie(pfad, karten)
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
                    for _k, e in _geladen_schnappschuss():   # Bibliothek kennt sofort den neuen Ort
                        if e.get("pfad") == pfad:
                            e["pfad"] = neu
                            e["name"] = os.path.basename(neu)
                            if kat:
                                e["kategorie"] = kat
                except OSError:
                    continue
        if bewegt:
            _geladen_speichern()
            _sag(f"Downloads einsortiert: {bewegt} Datei(en) an den richtigen Platz bewegt")
    finally:
        _einsortier_lauf.fertig()
    return bewegt


def ordner_importieren():
    """Mediendateien im Downloads-Ordner, die NICHT in der Bibliothek stehen,
    additiv aufnehmen (JB-/Kumpel-Wunsch: „andere Elemente im Ordner erkennen").
    Video-ID aus dem Namen ([id]) wird als Schlüssel genutzt, sonst ein
    stabiler Pfad-Hash; Titel = Dateiname ohne [id]. Löscht/ändert nie etwas."""
    bekannt = set()
    for k, e in _geladen_schnappschuss():
        p = e.get("pfad")
        if p:
            bekannt.add(os.path.normcase(os.path.abspath(p)))
    neu = 0
    frisch = []                                      # Keys dieses Laufs (Auto-Umbenennen)
    karten = _id_karten()
    for wurzel, _, dateien in _walk_ohne_rueckhol(ziel_ordner()):
        for fn in dateien:
            if not fn.lower().endswith(musik_einstufung.AUDIO_EXT + musik_einstufung.VIDEO_EXT):
                continue
            pfad = os.path.join(wurzel, fn)
            if os.path.normcase(os.path.abspath(pfad)) in bekannt:
                continue
            # Zentrale Kette: erkennt auch namenlose Kopien bekannter Dateien
            # am Fingerabdruck -> Dubletten-Schutz unten greift, statt dass
            # eine verschobene Datei eine zweite "lokal-…"-Zeile erzeugt.
            vid = _datei_videoid(pfad, karten) or ("lokal-" + hashlib.md5(
                os.path.abspath(pfad).encode("utf-8")).hexdigest()[:11])
            audio = fn.lower().endswith(musik_einstufung.AUDIO_EXT)
            key = f"{vid}|{'audio' if audio else 'lokal'}"
            if key in _geladen:
                continue
            # Dubletten-Wurzel (JB 14.07.): gibt es die Video-ID schon unter einem
            # ANDEREN Qualitäts-Schlüssel (z.B. mit totem Pfad), gehört die Datei
            # dem Heiler (pfade_heilen) — sonst entstehen zwei Zeilen je Datei.
            if links._plausible_id(vid) and any(k.split("|")[0] == vid for k in _geladen_schluessel()):
                continue
            try:
                groesse = os.path.getsize(pfad)
            except OSError:
                continue
            eintrag = {
                "name": fn, "groesse": groesse, "pfad": pfad,
                "kategorie": "MP3" if audio else musik_einstufung._kat_aus_name(fn),
                "titel": musik_einstufung._titel_aus_name(fn),
                "url": (f"https://www.youtube.com/watch?v={vid}" if links._plausible_id(vid) else ""),
                "qualitaet": "audio" if audio else "lokal",
                "importiert": True, "ts": time.time(),
                "fp": _datei_fp(pfad)}               # Content-Ausweis (Bibliothek 2.0)
            with _io_lock:                           # F6: prüfen und eintragen in einem Schritt
                if key in _geladen:
                    continue
                _geladen[key] = eintrag
            frisch.append(key)
            neu += 1
    if neu:
        _geladen_speichern()
        _sag(f"Ordner-Import: {neu} neue Datei(en) in die Bibliothek aufgenommen")
        if CFG.get("auto_umbenennen"):               # optional (Build 113, Standard AUS)
            r = migration_anwenden(go=True, keys=set(frisch))
            if r.get("umbenannt"):
                _sag(f"Auto-Umbenennen: {r['umbenannt']} importierte Datei(en) "
                     "nach dem Namens-Schema benannt (↩ rückgängig im Namens-Fenster)")
    return neu


_auto_import_zuletzt = 0.0


def _auto_import_anstossen(mindestabstand=60):
    """Ordner still nach neuen Dateien absuchen — im Hintergrund, gedrosselt.
    Ersetzt den Menüpunkt „Dateien aus dem Ordner aufnehmen" (JB: „die Option
    finde ich bescheuert"). Nicht-blockierend: die Bibliothek antwortet sofort,
    Neues erscheint beim nächsten Blick."""
    global _auto_import_zuletzt
    if time.time() - _auto_import_zuletzt < mindestabstand:
        return
    _auto_import_zuletzt = time.time()
    threading.Thread(target=ordner_importieren, daemon=True).start()


def pfade_heilen():
    """Tote 'pfad'-Einträge der geladen-DB reparieren (z.B. nach einem Ordner-
    Umzug wie Stage 3): existiert der gespeicherte Pfad nicht mehr, aber die
    Datei ist per Video-ID im Downloads-Ordner auffindbar, wird der Eintrag
    auf den echten Ort umgeschrieben. Rein additiv, löscht nie etwas."""
    idx = _datei_index()
    geheilt = 0
    for k, e in _geladen_schnappschuss():
        p = e.get("pfad")
        if p and not os.path.isfile(p):
            neu = _datei_aus(idx.get(k.split("|")[0]), k.partition("|")[2])
            if neu:
                e["pfad"] = neu
                e["name"] = os.path.basename(neu)
                geheilt += 1
    if geheilt:
        _geladen_speichern()
        _sag(f"Pfade geheilt: {geheilt} Bibliotheks-Einträge zeigen wieder auf echte Dateien")
    return geheilt


def _dubletten_score(e):
    """Welcher von mehreren Einträgen auf DIESELBE Datei bleibt: echte Downloads
    vor Ordner-Importen, benannte Qualität vor 'lokal', Kanal-Info als Bonus."""
    return ((0 if e.get("importiert") else 4)
            + (0 if e.get("qualitaet") in ("lokal", "") else 2)
            + (1 if e.get("uploader") else 0))


def dubletten_heilen():
    """Selbstheilung (JB 14.07.: „Duplikate in der Bibliothek"): zeigen mehrere
    Bibliotheks-Einträge auf DIESELBE Datei (Alt-Eintrag geheilt + Ordner-Import
    hatte sie schon aufgenommen), bleibt der beste Eintrag; die überzähligen
    Zeilen werden vergessen (Play-Zähler wandert mit, Dateien bleiben unberührt)."""
    gruppen = {}
    for k, e in _geladen_schnappschuss():
        p = e.get("pfad")
        if p and os.path.isfile(p):
            gruppen.setdefault(os.path.normcase(os.path.abspath(p)), []).append(k)
    raus = 0
    with _io_lock:
        for keys in gruppen.values():
            if len(keys) < 2:
                continue
            keys.sort(key=lambda k: (_dubletten_score(_geladen[k]),
                                     _geladen[k].get("plays") or 0,
                                     -(_geladen[k].get("ts") or 0)), reverse=True)
            halter = _geladen[keys[0]]
            for k in keys[1:]:
                e = _geladen.pop(k)
                halter["plays"] = (halter.get("plays") or 0) + (e.get("plays") or 0)
                if e.get("archiviert"):
                    halter["archiviert"] = True
                for pl in _playlists:                 # Playlists auf den Halter umbiegen
                    pl["items"] = [keys[0] if x == k else x for x in pl.get("items", [])]
                raus += 1
        if raus:
            _geladen_speichern()
    if raus:
        _playlists_speichern()
        _sag(f"Dubletten geheilt: {raus} doppelte Bibliothekszeilen zusammengelegt")
    return raus


def _vtt_verwaist(pfad, stems):
    """True, wenn ein .vtt zu KEINER Mediendatei gehört. Namensmuster gehörig:
    <medien-stamm>.<sprache>.vtt (Sprache z.B. de, en, ja-orig) oder nackt
    <medien-stamm>.vtt. Alt-Bug-Doppelungen wie '<stamm>.de.de.vtt' (Index
    zeigte früher auf die .vtt statt aufs Medium) gelten als verwaist."""
    base = pfad[:-4]                                  # ohne ".vtt"
    if base.lower() in stems:
        return False
    base2, _, _ = base.rpartition(".")                # ohne ".<sprache>"
    return not (base2 and base2.lower() in stems)


def untertitel_aufraeumen():
    """Selbstheilung: verwaiste .vtt (kein zugehöriges Video mehr) in den
    Windows-Papierkorb — nie hart löschen. Im Untertitel-Ordner ist die
    Zugehörigkeit die Video-ID im Namen; Altbestand neben Videos per Stamm."""
    ziel = untertitel_ordner()
    vids, stems, legacy = set(), set(), []
    karten = _id_karten()
    for wurzel, _, dateien in _walk_ohne_rueckhol(ziel_ordner()):
        istziel = os.path.normcase(wurzel) == os.path.normcase(ziel)
        for d in dateien:
            p = os.path.join(wurzel, d)
            if d.lower().endswith(musik_einstufung.AUDIO_EXT + musik_einstufung.VIDEO_EXT):
                stems.add(os.path.splitext(p)[0].lower())
                vid = _datei_videoid(p, karten)      # zentrale Kette statt nur [Id]-Name
                if vid:
                    vids.add(vid)
            elif d.lower().endswith(".vtt") and not istziel:
                legacy.append(p)                      # noch nicht einsortiert
    vids |= {k.split("|")[0] for k in _geladen_schluessel()}   # auch verschobene, aber bekannte Videos
    n = 0
    for f in glob.glob(os.path.join(glob.escape(ziel), "*.vtt")):
        vid = os.path.basename(f).split(".")[0]
        if vid not in vids and _in_papierkorb(f):
            n += 1
    for p in legacy:
        if _vtt_verwaist(p, stems) and _in_papierkorb(p):
            n += 1
    if n:
        _sag(f"Untertitel aufgeräumt: {n} verwaiste .vtt in den Papierkorb")
    return n


def _einsortieren_hintergrund():
    """Kurz nach dem Start + alle 6 h aufräumen (Daemon-Thread)."""
    time.sleep(20)
    for fn in (pfade_heilen, dubletten_heilen, ordner_importieren,
               metadaten_backfill, untertitel_einsortieren, untertitel_aufraeumen):
        try:
            fn()                                      # Pfade heilen, fremde Dateien aufnehmen, Metadaten nachtragen
        except Exception:                             # noqa: BLE001
            pass
    while True:
        try:
            downloads_einsortieren()
            ordner_importieren()
        except Exception:                             # noqa: BLE001
            pass
        time.sleep(6 * 3600)


_enrich_lauf = _LaeuftSchon()


def biblio_enrich_alle():
    """Alle Einträge ohne Kanal-Info nachreichern (Hintergrund, sanft gedrosselt)."""
    if not _enrich_lauf.starten():
        return
    try:
        for k in [k for k, e in _geladen_schnappschuss() if not e.get("uploader")]:
            if youtube_gesperrt():                    # F4: Sperre -> Pause, der nächste Lauf holt nach
                break
            e = _geladen.get(k)
            if e and _enrich_eintrag(k, e):
                _geladen_speichern()
            time.sleep(0.4)
    finally:
        _enrich_lauf.fertig()


def _finde_datei(url, e):
    """Datei zu einem DB-Eintrag finden: gespeicherter Pfad, Zielordner/Name,
    zuletzt rekursiv über die eindeutige Video-ID im Dateinamen ('[<id>]')
    — so wird sie auch in Unterordnern gefunden, egal wie groß sie ist."""
    for k in (e.get("pfad"), os.path.join(ziel_ordner(), e.get("name") or "")):
        if k and os.path.isfile(k):
            return k
    vid = links._video_id(url)
    basis = ziel_ordner()
    muster = os.path.join(basis, "**", f"*[[]{glob.escape(vid)}[]]*")
    treffer = [p for p in glob.glob(muster, recursive=True)
               if os.path.isfile(p) and p.lower().endswith(musik_einstufung.AUDIO_EXT + musik_einstufung.VIDEO_EXT)
               and not _im_rueckhol_ordner(p, basis)]
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
        _geladen_speichern()
    return pfad


def db_statistik():
    """Alle je geladenen Downloads für den Gesamt-Counter: Summe + je Kategorie."""
    kat = {}
    for _k, e in _geladen_schnappschuss():
        k = e.get("kategorie")
        if not k:                     # Altbestand ohne Kategorie -> aus Endung raten
            name = (e.get("name") or "").lower()
            k = "MP3" if name.endswith(musik_einstufung.AUDIO_EXT_OHNE_WAV_AAC) else "Video"
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
    vid = links._video_id(url)
    return any(it["id"] != ausser and it["qualitaet"] == qualitaet
               and links._video_id(it["url"]) == vid for it in Q.items)


def _fehltext(exc):
    t = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))      # ANSI-Farben raus
    t = t.replace("ERROR: ", "").strip()
    return t[:300]


# Dauerhafter Fehlerkanal (Befund 07.09.2026): Ein gescheiterter Download
# hinterliess KEINE Spur — der volle yt-dlp-Text lebte nur im Browser und war
# in der Anzeige auf 42 Zeichen gekuerzt. Wer am Telefon fragt »was steht denn
# da?«, konnte es nicht sagen. Muster ist der schon vorhandene Rekorder
# js_fehler.jsonl: eine Zeile je Vorfall, Deckel 200 KB, aeltestes faellt weg.
# Beide Protokolle am DATEN_DIR (Prüfung Runde 2): am SCRIPT_DIR schrieb eine
# --testmodus-Probe in JBs Produktiv-Protokolle. Im Betrieb ist beides derselbe Ordner.
FEHLER_LOG = os.path.join(DATEN_DIR, "yt_fehler.jsonl")
JS_FEHLER_LOG = os.path.join(DATEN_DIR, "js_fehler.jsonl")
_fehler_lock = threading.Lock()


def fehler_merken(url, text, art="", titel="", pfad=None):
    """Einen Fehlschlag dauerhaft festhalten. `pfad` ist ueberschreibbar, damit
    Tests gegen tmp_path messen statt gegen den Produktiv-Ordner (P7)."""
    zeile = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
             "art": str(art or "")[:40],
             "url": str(url or "")[:300],
             "titel": str(titel or "")[:200],
             "text": str(text or "")[:600]}
    return _zeile_anhaengen(pfad or FEHLER_LOG, zeile)


def _zeile_anhaengen(ziel, zeile):
    """Eine JSON-Zeile an ein Protokoll (.jsonl) hängen: unter `_fehler_lock`,
    Deckel 200 KB, das Älteste fällt weg. Gemeinsam für den Fehlerkanal und den
    JS-Rekorder (Gesamtprüfung Gruppe 7: der Rekorder war eine Kopie ohne Sperre)."""
    try:
        with _fehler_lock:
            if os.path.exists(ziel) and os.path.getsize(ziel) > 200_000:
                with open(ziel, encoding="utf-8", errors="replace") as f:
                    rest_z = f.readlines()[-200:]
                # »Die letzten 200 Zeilen« allein deckelt nicht: eine einzelne
                # riesige Zeile (abgeschnittener Fremd-Text ohne Umbruch) bleibt
                # dabei vollstaendig stehen. Deshalb zusaetzlich nach Bytes
                # kuerzen, bis der Rest unter 150 KB liegt.
                while rest_z and sum(len(z.encode("utf-8")) for z in rest_z) > 150_000:
                    rest_z.pop(0)
                with open(ziel, "w", encoding="utf-8") as f:
                    f.writelines(rest_z)
            with open(ziel, "a", encoding="utf-8") as f:
                f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:                                  # Platte voll/gesperrt: nie den Lauf reissen
        pass
    return zeile


def herunterladen(item):
    """Einen Eintrag laden. Fortsetzen (.part) macht yt-dlp automatisch."""
    erzwingen = bool(item.pop("erzwingen", False))
    if not erzwingen:
        fund = schon_geladen(item["url"], item["qualitaet"])
        if fund:                                     # JB-Regel: Name+Größe identisch -> überspringen
            _als_uebersprungen(item, fund)
            Q.speichern()
            return
    elif not _vorhandene_sichern(item):              # „Trotzdem laden“: erst sichern, dann ersetzen
        return
    if item.get("geo_laender") and not item.get("geo_versucht") and CFG.get("geo_vpn"):
        _geo_download(item, erzwingen)
    else:
        _download_lauf(item, erzwingen)
    _sicherung_nennen(item)


def _vorhandene_sichern(item):
    """„Trotzdem laden“ (Gesamtprüfung Gruppe 6): yt-dlp ersetzt die vorhandene
    Datei (overwrites). Vorher wandert sie rückholbar in den Papierkorb (Rückfall
    `_Papierkorb`, _rueckholbar_entfernen). Lässt sie sich nicht sichern, wird
    nichts ersetzt: der Eintrag steht mit Grund auf „fehler“. True = weiter.
    Wohin sie ging, merkt sich der Eintrag (`gesichert`, s. _sicherung_nennen)."""
    fund = schon_geladen(item["url"], item["qualitaet"]) or item.get("datei") or ""
    if not (fund and os.path.isfile(fund)):
        return True
    ort = _rueckholbar_entfernen(fund)
    if ort:
        item["gesichert"] = ort
        return True
    with Q.lock:
        item["status"] = "fehler"
        item["fehler"] = "Die vorhandene Datei ließ sich nicht sichern, darum wurde nichts ersetzt."
    Q.speichern()
    return False


def _sicherung_nennen(item):
    """Nach einem Lauf von „Trotzdem laden“: ist der neue Download gescheitert,
    nennt der Fehlertext, wo die vorher gesicherte Datei liegt (sonst fehlte der
    Titel ohne Hinweis in der Bibliothek). Ein geplanter Neuversuch ist noch
    kein Scheitern; nach einem gelungenen Download wird die Sicherung vergessen."""
    ort = item.get("gesichert")
    if not ort or item.get("status") not in ("fehler", "fertig"):
        return
    with Q.lock:
        if item["status"] == "fertig":
            item.pop("gesichert", None)
            return
        hinweis = ("Die vorherige Datei liegt im Windows-Papierkorb." if ort == "papierkorb"
                   else f"Die vorherige Datei liegt rückholbar unter {ort}.")
        text = (item.get("fehler") or "").strip()
        if hinweis not in text:
            item["fehler"] = f"{text} {hinweis}".strip()
    Q.speichern()


def _zugang_ok(url, extra_opts, timeout=30):
    """Schneller Check (nur Metadaten, ohne Cookies): gibt es mit diesen Optionen
    Zugang zum Video (kein Geo-Fehler, Formate vorhanden)?"""
    opts = _ydl_basis_opts(mit_cookies=False)
    opts.update({"skip_download": True, "noplaylist": True,
                 "quiet": True, "no_warnings": True, "socket_timeout": 20})
    opts.update(extra_opts or {})
    try:
        with _ydl(opts) as y:
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
            item["status"] = "pausiert"
            item["phase"] = ""
            Q.speichern()
            return
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
                _download_lauf(item, erzwingen, mit_cookies=False, extra_opts=kand.opts,
                               geo_lauf=True)
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
_geo_test_lock = threading.Lock()


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


def _download_lauf(item, erzwingen=False, mit_cookies=True, extra_opts=None, geo_lauf=False):
    # Befund 07.09.2026: Der Parameter hiess frueher `geo` und verdeckte damit
    # das Modul `geo` IM GANZEN Funktionskoerper. Im Fehlerzweig stand deshalb
    # `False.ist_geo_fehler(...)` — jeder gewoehnliche Download-Fehler flog als
    # AttributeError aus der Funktion, noch bevor Backoff, DAUERHAFT-Liste oder
    # max_wiederholungen ueberhaupt gefragt wurden. Der ganze Neuversuch-
    # Mechanismus war unerreichbar; aufgefangen hat es erst das Netz in
    # worker_schleife, das den Eintrag stumm auf »fehler« setzte.

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

    def pp_hook(d):
        # Build 125 (JB-Fund „laufende Downloads lassen sich nicht abbrechen"):
        # progress_hooks feuern NUR waehrend des Ladens. Danach uebernimmt
        # ffmpeg — Bild+Ton zusammenfuegen, MP3 wandeln, Cover einbetten — und
        # in genau dieser Phase (Anzeige „Zusammenfuegen") sah niemand mehr
        # nach, ob abgebrochen wurde. Bei grossen Videos ist das die laengste
        # Strecke, also gerade die, in der JB abbricht. Derselbe Abbruch, eine
        # Pruefstelle mehr; die AbbruchError faengt _download_lauf schon ab.
        if item["id"] in Q.abbrueche:
            raise AbbruchError()
        if d.get("status") == "started":
            item["phase"] = "Zusammenfügen"
            Q.speichern()

    opts = _ydl_basis_opts(mit_cookies=mit_cookies)
    opts.update(DROSSEL)            # nur hier bremsen, nicht in den Auflöse-Wegen
    opts.update({
        "outtmpl": os.path.join(ziel_ordner(), "%(title)s [%(id)s].%(ext)s"),
        "format": QUALITAETEN[item["qualitaet"]],
        "noplaylist": True,
        "continuedl": True,
        "progress_hooks": [hook],
        "postprocessor_hooks": [pp_hook],
        "merge_output_format": "mp4",
    })
    # OHNE ffmpeg kann yt-dlp Bild+Ton nicht zusammenfügen -> Videos schlugen fehl
    # (z.B. nackte exe ohne bin\-Ordner). Fallback: fertige Kombi-Formate (progressive),
    # begrenzt auf die gewünschte Höhe — läuft ohne Zusammenfügen, max. ~720p.
    if not _ffmpeg_exe() and item["qualitaet"] != "audio":
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
                     "subtitleslangs": _untertitel_sprachen(), "subtitlesformat": "vtt/best"})

    hat_ff = bool(_ffmpeg_exe())
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
        with _ydl(o) as ydl:
            return ydl.extract_info(item["url"], download=True)

    try:
        try:
            info = _lauf(opts)
        except AbbruchError:
            raise
        except Exception as e:                       # noqa: BLE001 — heilbare Fehler heilen
            if _ist_sperre(e):
                raise                                # kein Cookie-Problem, sondern eine Sperre
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
        try:
            untertitel_einsortieren()                 # mitgeladene .vtt in den Untertitel-Ordner
        except Exception:                             # noqa: BLE001
            pass
        # Build 144i (JB 25.07.): Klammern/Schema NACH dem Einsortieren — die
        # .vtt liegen dann schon Id-keyed im Untertitel-Ordner, das Umbenennen
        # der Mediendatei kann sie also nicht mehr verwaisen lassen.
        auto_umbenennen_nach_download(item)
        autotag_nach_download(item)                   # Build 136 (JB): direkt benennen
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
        if not _ist_sperre(voll):
            fehler_merken(item.get("url"), voll, "download", item.get("titel") or "")
        if geo_lauf:                                 # Geo-Lauf: kein Backoff, die Kette geht weiter
            if _ist_sperre(voll):
                # Abnahme-Mangel 07.09.2026: Genau der Fall, fuer den der
                # Fehlerkanal gebaut wurde, hinterliess keine Spur — oben wird
                # bei einer Sperre nicht gemerkt (das macht sonst der
                # `elif _ist_sperre`-Zweig), und hier kehrt die Funktion vorher
                # zurueck. Ein Geo-Versuch, der an einer Sperre scheitert, ist
                # fuer die Ferndiagnose beim Kumpel besonders wichtig.
                fehler_merken(item.get("url"), voll, "sperre-geo",
                              item.get("titel") or "")
            item["status"] = "fehler"
            Q.speichern()
            return
        if geo.ist_geo_fehler(voll) and not item.get("geo_versucht") and CFG.get("geo_vpn"):
            item["geo_laender"] = geo.laender_aus_fehler(voll)
            item["versuche"] -= 1                     # zählt nicht als Fehlversuch
            item["naechster_versuch"] = 0
            item["status"] = "wartend"                # nächster Lauf geht durch die Geo-Kette
        elif youtube_sperre_vermerken(voll):
            # YouTube sperrt uns aus. Frueher lief so ein Eintrag bis zu
            # max_wiederholungen (Vorgabe 10) erneut los und machte aus der
            # weichen Drossel eine harte Sperre. Jetzt: sofort stoppen, und
            # die Nebenwege pausieren (F4).
            item["status"] = "fehler"
            fehler_merken(item.get("url"), voll, "sperre", item.get("titel") or "")
        elif any(s in item["fehler"].lower() for s in DAUERHAFT):
            item["status"] = "fehler"                # Neuversuch bringt hier nichts
        elif item["versuche"] <= CFG.get("max_wiederholungen", 10):
            warte = BACKOFF[min(item["versuche"] - 1, len(BACKOFF) - 1)]
            item["naechster_versuch"] = time.time() + warte
            item["status"] = "wartend"               # Neuversuch setzt am .part fort
        else:
            item["status"] = "fehler"
    Q.speichern()


def _q_speichern_im_worker():
    """Q.speichern, das den Worker nie tötet (Gesamtprüfung F1). Vorher stand
    das Speichern außerhalb des `try` bzw. im `except`: Scheiterte os.replace
    (etwa während das Dashboard yt_status.json liest), starb der Worker-Faden
    für immer, und sein Eintrag blieb auf „laeuft". Der Stand bleibt im
    Speicher; das nächste Speichern (Ticker, spätestens 5 s) holt ihn nach."""
    try:
        Q.speichern()
    except Exception as e:                           # noqa: BLE001 — Worker darf NIE sterben
        _sag("Warteschlange nicht gespeichert: " + _fehltext(e), logging.WARNING)


def worker_schleife():
    while True:
        item = Q.naechster()
        if item is None:
            time.sleep(1)
            continue
        _q_speichern_im_worker()
        try:
            herunterladen(item)
        except Exception as e:                       # noqa: BLE001 — Worker darf NIE sterben
            # Fund 06.08. (Zombie-„laeuft"): eine unbehandelte Ausnahme riss den
            # Worker-Thread mit in den Tod — der Eintrag blieb für immer auf
            # „laeuft" (und blockierte damit auch den Selbst-Neustart, der auf
            # Leerlauf wartet), und es arbeitete ein Worker weniger. Jetzt wird
            # der Eintrag ehrlich zum „fehler" und der Worker lebt weiter.
            try:
                fehler_merken(item.get("url"), str(e), "worker", item.get("titel") or "")
            except Exception:                        # noqa: BLE001 — auch das darf nicht töten
                pass
            with Q.lock:
                if item.get("status") == "laeuft":
                    item["status"] = "fehler"
                    item["fehler"] = _fehltext(e)
            _q_speichern_im_worker()


_fehler_seit = {}   # item-id -> Zeitpunkt, seit dem der Eintrag „fehler" ist


_prueft_seit = {}   # item-id -> Zeitpunkt, seit dem der Eintrag „prueft"
_prueft_wartet = set()   # item-ids, deren Auflösen noch auf einen Platz wartet (F2)


def queue_heilen():
    """Hängende Aufträge selbst wieder flottmachen (Build 137, JB Punkt 6).

    Ein Eintrag steht auf „prueft", solange yt-dlp die Adresse auflöst. Stirbt
    dieser Hintergrund-Thread — Netzabbruch, Ausnahme in einer Fremdbibliothek,
    hängende Verbindung —, bleibt der Eintrag für immer stehen: aufgegriffen
    wird nur „wartend". Für JB sieht das aus wie ein Download, der ewig
    „prüft" und nie loslegt.

    Nach 5 Minuten ohne Fortschritt wird er deshalb WIEDER EINGEREIHT. Das ist
    bewusst nicht-destruktiv (harte Regel): nichts wird gelöscht, die
    .part-Datei bleibt liegen, der Download setzt fort. Läuft im bestehenden
    Ticker mit — kein neuer Dauerprozess, kein neuer Zeitplan.
    """
    jetzt = time.time()
    with Q.lock:
        offen = {it["id"] for it in Q.items if it.get("status") == "prueft"}
        for tot in [k for k in _prueft_seit if k not in offen]:
            _prueft_seit.pop(tot, None)               # nicht mehr „prueft" -> vergessen
        for it in Q.items:
            if it.get("status") != "prueft":
                continue
            if it["id"] in _prueft_wartet:            # F2: wartet auf einen Platz, hängt nicht
                continue
            seit = _prueft_seit.setdefault(it["id"], jetzt)
            if jetzt - seit < AUFLOESEN_GEDULD_S:     # 5 Minuten Geduld
                continue
            it["status"] = "wartend"
            it["naechster_versuch"] = 0
            it["fehler"] = ""
            _prueft_seit.pop(it["id"], None)
            _sag(f"Warteschlange geheilt: „{(it.get('titel') or it.get('url') or '')[:60]}" + "“ "
                 "hing beim Auflösen und wurde wieder eingereiht.")
    _aufloese_plaetze.haenger_freigeben()             # ihr Platz geht an den nächsten Link
    Q.speichern()


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


# ---- Selbst-Neustart bei Code-Änderung (Build 144m, JB 25.07.) -------------
# JB: „den Haken sollten wir lösen, das sollte immer klappen. Egal ob auf
# Homeserver oder in der Simulation." Wurzel: Die Oberfläche lädt pro Anfrage
# neu (importlib.reload), das Hauptmodul aber nicht — Backend-Änderungen (neue
# Felder, Routen) griffen erst nach einem manuellen Neustart.
# Lösung: Die App merkt sich beim Start die mtime-Signatur ihrer Backend-
# Quelldateien. Ist der Code auf der Platte neuer, ersetzt sie ihren eigenen
# Prozess (os.execv) — Zustand liegt auf der Platte, Port wird frei. Ausgelöst
# in der BESTEHENDEN 5-s-Schleife (kein neuer Timer, Last-Budget), nur bei Ruhe
# (kein Download/Stream) und erst, wenn der Code ein paar Sekunden stabil ist.
# medien_session.py (23.09.2026): der gemeinsame Media-Session-Baustein beider
# Seiten lädt MIT ihnen neu — sonst erreichte eine Änderung daran offene Tabs nie.
# EINE Tabelle für Router, Selbst-Neustart und ui_stand (Gesamtprüfung Gruppe 7):
# vorher stand die Liste dreifach, und fernbedienung.py fehlte in der Liste des
# Selbst-Neustarts, obwohl der Router sie pro Anfrage neu lud.
HEISSE_SEITEN = {                                     # Seite -> Bausteine, die VOR ihr nachladen
    "oberflaeche": ("medien_session",),
    "handy": ("medien_session",),
    "fernbedienung": (),
}
_HEISS_NACHLADBAR = {f"{m}.py" for seite, bausteine in HEISSE_SEITEN.items()
                     for m in (seite, *bausteine)}    # laden pro Anfrage neu -> kein Neustart nötig
NEUSTART_BERUHIGUNG = 3.0                             # s stabil, bevor neu gestartet wird
STREAM_RUHE = 15.0                                   # s ohne Abspielen = sicher
# Ein Transcode zur Zeit (JB zappt): der nächste Wunsch löst den alten ab.
_tc_lock = threading.Lock()
_tc_prozess = None


def _transcode_befehl(url, start=0, vcopy=False):
    """Die ffmpeg-Kommandozeile für den Browser-Player — als REINE Funktion.

    Bewusst herausgezogen (13.08.2026): Solange der Befehl mitten in `do_GET`
    entstand, konnte kein Test ihn ansehen, und der Blocker blieb unsichtbar —
    `cmd[0]` war der bin-ORDNER statt `ffmpeg.exe`, jeder Aufruf starb mit
    `WinError 5`. Jetzt prüft `test_transcode_befehl_startet_ein_programm` das
    Ergebnis direkt. Fehlende Testbarkeit war die eigentliche Ursache."""
    cmd = [_ffmpeg_exe(), "-hide_banner", "-loglevel", "error"]
    if start:
        cmd += ["-ss", str(int(start))]              # Seek VOR dem Input: schnell
    cmd += ["-i", url, "-map", "0:v:0", "-map", "0:a:0?"]
    cmd += (["-c:v", "copy"] if vcopy else
            ["-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
             "-vf", "scale='min(1920,iw)':-2"])
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ac", "2",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "-f", "mp4", "pipe:1"]
    return cmd


def _tc_starten(cmd):
    global _tc_prozess
    with _tc_lock:
        if _tc_prozess is not None and _tc_prozess.poll() is None:
            try:
                _tc_prozess.kill()
            except OSError:
                pass
        _tc_prozess = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return _tc_prozess


def _strom_fehler(e=None):
    """(Status, Körper) für einen Jellyfin-Strom, den Renés Server nicht
    herausgibt — EINE Stelle für Direkt- und Transcoder-Zweig des Browser-
    Proxys: Jellyfins Status (HTTPError) oder 502 (Netz). Nie die Adresse
    (sie trägt das Token)."""
    if isinstance(e, urllib.request.HTTPError):
        return e.code, {"fehler": f"Renés Server gibt den Film nicht heraus "
                                  f"(Jellyfin HTTP {e.code}).",
                        "jellyfin_status": e.code}
    return 502, {"fehler": "Renés Server nicht erreichbar."}


def _strom_vorprobe(url):
    """Gibt Jellyfin den Strom heraus? EIN Byte fragen (Range 0-0): None = ja,
    sonst (Status, Körper) wie _strom_fehler. Für den Transcoder-Zweig
    (Prüfung Runde 1): ffmpeg liest die Adresse selbst, und der Proxy schickte
    200, bevor ffmpeg ein Byte hatte — eine Ablehnung kam beim Browser als 200
    mit leerem Strom an."""
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"Range": "bytes=0-0"}), timeout=30):
            return None
    except urllib.request.HTTPError as e:
        e.close()
        return _strom_fehler(e)
    except OSError:                                  # URLError, Zeitüberschreitung
        return _strom_fehler()


_letzter_stream = 0.0
_START_SIGNATUR = None                               # in main() gesetzt
_neu_sig = None
_neu_sig_seit = 0.0
_neustart_geplant = False
_neustart_lock = threading.Lock()


def _seite_frisch(name):
    """Eine Seite aus HEISSE_SEITEN frisch laden (Bausteine zuerst) und ihr HTML
    liefern — Änderungen erscheinen mit einem Browser-Neuladen, ohne Neustart.
    Scheitert das Neuladen, bleibt die alte, heile Fassung stehen."""
    import importlib
    seite = importlib.import_module(name)
    try:
        for baustein in HEISSE_SEITEN[name]:
            importlib.reload(importlib.import_module(baustein))
        importlib.reload(seite)
    except Exception:                                # noqa: BLE001 — im Zweifel alte Version
        pass
    return seite.HTML


def _ui_stand():
    """mtime der PC-Oberfläche samt ihrer Bausteine: alte Browser-Tabs erneuern
    sich selbst, wenn hier neuer Code liegt (Wurzel-Fix 07.08.)."""
    try:
        return round(max(os.path.getmtime(os.path.join(SCRIPT_DIR, m + ".py"))
                         for m in ("oberflaeche", *HEISSE_SEITEN["oberflaeche"])), 2)
    except OSError:
        return 0


def _quell_signatur():
    """mtime-Summe der Backend-Quelldateien (die NICHT pro Anfrage neu laden)."""
    sig = 0.0
    try:
        for f in os.listdir(SCRIPT_DIR):
            if f.endswith(".py") and f not in _HEISS_NACHLADBAR:
                try:
                    sig += os.path.getmtime(os.path.join(SCRIPT_DIR, f))
                except OSError:
                    pass
    except OSError:
        pass
    return round(sig, 3)


def _code_leerlauf():
    """Kein aktiver Download und kein kürzliches Abspielen — sicher zum Neustart."""
    try:
        if any(i.get("status") in ("laeuft", "prueft") for i in Q.items):
            return False
    except Exception:                                # noqa: BLE001 — im Zweifel NICHT neu starten
        return False
    if _vlc_haelt_neustart_auf():                    # Gerät VLC: nie mitten im Titel, Pause max. 30 Min
        return False
    return (time.time() - _letzter_stream) > STREAM_RUHE


def _selbst_neustart():
    """Den eigenen Prozess durch eine frische Kopie ersetzen. Zustand (Config,
    Warteschlange, DB) liegt auf der Platte; der Port wird durch execv frei und
    sofort wieder belegt. Als exe: die exe neu; als Skript: python + Skript."""
    try:
        Q.speichern()
    except Exception:                                # noqa: BLE001
        pass
    _sag("Code aktualisiert — Selbst-Neustart, der Zustand bleibt erhalten.")
    try:
        if getattr(sys, "frozen", False):
            os.execv(sys.executable, [sys.executable] + sys.argv[1:])
        else:
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except OSError as e:
        globals()["_neustart_geplant"] = False
        _sag(f"Selbst-Neustart nicht möglich: {e}", logging.WARNING)


def _neustart_pruefen():
    """Läuft in der 5-s-Schleife: neuer Code auf der Platte? Dann leise selbst
    neu starten — nach Beruhigungszeit und nur bei Ruhe."""
    global _neu_sig, _neu_sig_seit, _neustart_geplant
    if _neustart_geplant or _START_SIGNATUR is None or not CFG.get("auto_neustart", True):
        return
    sig = _quell_signatur()
    if sig == _START_SIGNATUR:                        # unverändert
        _neu_sig = None
        return
    jetzt = time.time()
    if sig != _neu_sig:                               # (neue) Änderung -> Beruhigungsuhr neu
        _neu_sig = sig
        _neu_sig_seit = jetzt
        return
    if jetzt - _neu_sig_seit < NEUSTART_BERUHIGUNG:   # noch nicht stabil
        return
    if not _code_leerlauf():                          # lädt/spielt gerade -> später
        return
    with _neustart_lock:
        if _neustart_geplant:
            return
        _neustart_geplant = True
    threading.Timer(0.3, _selbst_neustart).start()    # Antwort erst rausgeben lassen


_filme_sync_laeuft = threading.Lock()


def _filme_abzug_anstossen(von_hand=False):
    """Startet EINEN Abzug im Hintergrund — oder gar keinen, wenn schon einer läuft.

    Die EINE Stelle für beide Auslöser (6-h-Ticker und Sync-Knopf). Vorher hatte
    nur der Ticker eine Sperre; der Knopf startete blind einen zweiten Thread.
    `von_hand` (⟳ Abgleichen): die Merkmal-Ruhe gilt nur der Automatik — der
    Knopf hebt sie auf (Prüfung Runde 1), die 403-Drossel nicht."""
    if not _filme_sync_laeuft.acquire(blocking=False):
        return False

    def lauf():
        try:
            if von_hand:
                filme.merkmal_ruhe_aufheben()
            filme.katalog_abzug()          # hält seinen Ausgang selbst fest
        finally:
            _filme_sync_laeuft.release()
    threading.Thread(target=lauf, daemon=True).start()
    return True


def filme_sync_pruefen():
    """6-h-Katalog-Abzug im BESTEHENDEN Ticker (Last-Budget: kein neuer Timer);
    ohne Keyring-Zugang still (der Film-Teil ist dann einfach aus)."""
    if not filme.sync_faellig() or not filme._zugang():
        return
    _filme_abzug_anstossen()


_auto_sync_stand = {}                                 # playlist-id -> zuletzt gesyncte Signatur
_auto_sync_nachholen = {}                             # playlist-id -> (Signatur, frühester nächster Versuch, Pause)
AUTO_SYNC_NACHHOL_S = 300                             # erste Pause nach einem Lauf mit fehlender Quelle
AUTO_SYNC_NACHHOL_MAX_S = 3600                        # verdoppelt sich je Fehlschlag bis hierher


def auto_sync_pruefen():
    """Playlists mit „Automatisch synchronisieren" abgleichen (JB 07.08.).

    Last-Budget-Regel: KEIN eigener Zeitplan — das hängt im bestehenden
    5-s-Ticker und tut nur etwas, wenn sich die Playlist wirklich geändert
    hat UND der Zielordner gerade erreichbar ist (Stick/Platte ab = still
    warten, kein Fehler-Sturm).

    Fehlte beim Lauf eine Quelle (Gesamtprüfung S5), wird die Signatur NICHT
    gemerkt: sonst kopierte der Auto-Sync die Datei nie nach, bis sich die
    Playlist änderte. Der nächste Versuch kommt frühestens nach
    AUTO_SYNC_NACHHOL_S (jeder Lauf durchsucht den ganzen Download-Ordner);
    fehlt die Quelle weiter, verdoppelt sich die Pause bis
    AUTO_SYNC_NACHHOL_MAX_S (eine im Explorer gelöschte Datei fehlt für
    immer). Eine geänderte Playlist läuft sofort und beginnt von vorn.
    """
    # _playlists ist eine LISTE (Fund 07.08.: .values() warf AttributeError —
    # und riss, weil ungefangen, den ganzen Ticker mit; JBs Spiegel-Sync lief
    # deshalb nie und auch der Selbst-Neustart stand still).
    for pl in list(_playlists):
        if not (pl.get("sync_auto") and pl.get("sync_ordner")):
            continue
        sig = (len(pl.get("items") or []), tuple(pl.get("items") or [])[:400],
               pl.get("sync_modus"))
        if _auto_sync_stand.get(pl.get("id")) == sig:
            continue
        warte = _auto_sync_nachholen.get(pl.get("id"))
        if warte and warte[0] == sig and time.time() < warte[1]:
            continue
        if not os.path.isdir(pl["sync_ordner"]):      # Ziel weg ⇒ später erneut
            continue
        try:
            r = playlist_sync(pl)
            if isinstance(r, dict) and r.get("fehlend"):
                pause = (min(warte[2] * 2, AUTO_SYNC_NACHHOL_MAX_S)
                         if warte and warte[0] == sig else AUTO_SYNC_NACHHOL_S)
                _auto_sync_nachholen[pl.get("id")] = (sig, time.time() + pause, pause)
            else:
                _auto_sync_stand[pl.get("id")] = sig
                _auto_sync_nachholen.pop(pl.get("id"), None)
        except Exception:                             # noqa: BLE001 — nächster Takt
            pass


def ticker_schleife():
    """Fortschritt alle 5 s sichern, damit ein Absturz höchstens 5 s Anzeige kostet.

    JEDE Aufgabe einzeln gekapselt (Fund 07.08.): ein Fehler in EINER Aufgabe
    (hier: `.values()` auf der Playlist-LISTE) riss bisher die ganze Schleife
    mit — danach standen still: Fortschritt-Sicherung, Queue-Heilung, der
    Selbst-Neustart und der Film-Abzug. Ein Herzschlag darf nie an einem
    einzelnen Schlag sterben.
    """
    while True:
        time.sleep(5)
        for name, aufgabe in (
                ("speichern", lambda: Q.speichern()
                 if any(it["status"] == "laeuft" for it in Q.items) else None),
                ("fehler", _fehler_aufraeumen),
                ("queue", queue_heilen),              # Build 137: hängende Aufträge
                ("worker", lambda: _worker_start(_worker_soll())),   # F1: tote Worker ersetzen
                ("neustart", _neustart_pruefen),      # Build 144m: neuer Code
                ("filme", filme_sync_pruefen),        # Film-Fundament: 6-h-Abzug
                ("autosync", auto_sync_pruefen)):     # JB 07.08.: Playlist -> Gerät
            try:
                aufgabe()
            except Exception as e:                    # noqa: BLE001 — Takt lebt weiter
                _sag(f"Ticker-Aufgabe {name}: {_fehltext(e)}", logging.WARNING)


# ---------------------------------------------------------------- HTTP-Server

# Vertrauen in Anfragen (Gesamtprüfung S2, 25.09.2026). „Kommt von 127.0.0.1"
# heißt nicht „kommt von JB": jede offene Webseite im Browser schickt von dort.
# Zwei Kopf-Prüfungen vor jedem Riegel:
#  * Host: nur IP-Literale, localhost und der eigene Rechnername, allein oder
#    mit einer Heimnetz-Endung (HEIMNETZ_ENDUNGEN, z. B. jb-pc.fritz.box). Eine
#    Seite, deren Name per DNS-Rebinding auf 127.0.0.1 zeigt, trägt ihren
#    EIGENEN Namen im Host-Kopf und prallt ab. Nachschärfung 25.09.2026: vorher
#    genügte das erste Label, also kam auch jb-pc.fremde-domain.de durch — und
#    wer diese Domain besitzt, kann den Namen auf 127.0.0.1 zeigen lassen.
#  * Origin: fehlt er (urllib aus Tray, SyncFindus, Hülle), ist das kein
#    Browser-Querzugriff. Sonst nur der eigene Ursprung (Host:Port wie im
#    Host-Kopf) oder eine Browser-Erweiterung (das Addon).
# Bewusst KEINE Content-Type-Pflicht: das Addon sendet ohne (background.js).
# Dieselben Schemata gelten für CORS (_cors). ms-browser-extension gab es nur im
# alten Edge (EdgeHTML); der heutige Edge meldet chrome-extension (Gruppe 6).
ERWEITERUNGS_SCHEMATA = ("moz-extension", "chrome-extension")
# Das Dashboard (Tray-Server, SyncDashTray settings_server.PORT) bettet
# /?embed=1 im Rahmen ein; sonst darf nur die App selbst sich einbetten. Das
# Dashboard ist unter beiden Namen des PCs erreichbar (Nachschärfung 25.09.2026).
DASHBOARD_URSPRUENGE = ("http://127.0.0.1:8765", "http://localhost:8765")
EINBETTEN_CSP = "frame-ancestors 'self' " + " ".join(DASHBOARD_URSPRUENGE)
HEIMNETZ_ENDUNGEN = (".local", ".lan", ".home.arpa", ".fritz.box", ".localdomain")
MAX_KOERPER = 2 * 1024 * 1024        # S14: größter angenommener POST-Körper
SEITEN = ("/", "/index.html", "/m", "/koppeln", "/fernbedienung")   # Routen, die eine HTML-Seite liefern
FERNSTEUERUNG_AUS_TEXT = "Fernsteuerung am PC ausgeschaltet."
KOPPEL_API = ("/api/geraet_anmelden", "/api/geraet_status")   # frei; `code` dort ist der Kopplungs-Code
FREIE_SEITEN = ("/m", "/koppeln")                             # auch ohne Zugang (Code-Eingabe, Kopplung)

# Kopplung und Code per Cookie (JB-Entscheid 7a Punkt 1, 25.09.2026; S17, F9).
# Vorher standen Geräte-Token und Code in der Adresse (Verlauf, Lesezeichen,
# Referrer) und im localStorage, und die PC-Oberfläche auf einem gekoppelten
# Gerät schickte bei keinem Aufruf einen Zugang mit (jede API-Anfrage 403).
# Jetzt:
#  * Ein gültiger Token oder Code aus der Adresse oder dem Kopf wird ein
#    HttpOnly-Cookie (SameSite=Strict, Path=/); das Skript der Seite sieht es
#    nie, und jeder Aufruf der Seite trägt es von selbst.
#  * Eine SEITE mit Token oder Code in der Adresse leitet auf dieselbe Adresse
#    ohne den Parameter um. API-Wege antworten direkt (ein Medien-Strom oder
#    ein Bild folgt keiner Umleitung, wenn der Browser keine Cookies nimmt).
#  * Kopf und Adresse bleiben als Rückfall gültig.
#  * Ein ungültiges Cookie (Code erneuert, Gerät getrennt) löscht der Server
#    in der Antwort: sonst schickte die Oberfläche es jede Sekunde mit und
#    liefe nach zehn Sekunden in die Versuchsbremse.
COOKIE_GERAET = "syncyt_geraet"
COOKIE_CODE = "syncyt_code"
# Der Token hält 400 Tage (die Obergrenze der Browser) und verlängert sich
# gleitend: jede Seite (VERLAENGERN_SEITEN), die ein Gerät mit gültigem
# Token-Cookie öffnet, setzt es mit voller Laufzeit neu (Abnahme 25.09.2026;
# vorher lief es 400 Tage nach der Kopplung ab). Ein gekoppelter Fernseher, der
# wenigstens alle 400 Tage einmal öffnet, koppelt also nie neu. Der Code hält
# 30 Tage ab der Eingabe, ohne Verlängerung: ein Handy mit Code gibt ihn danach
# neu ein (offene Frage an JB, ob er länger halten soll).
COOKIE_DAUER = {COOKIE_GERAET: 400 * 24 * 3600, COOKIE_CODE: 30 * 24 * 3600}
VERLAENGERN_SEITEN = ("/", "/index.html", "/m")
_COOKIE_WERT = re.compile(r"[A-Za-z0-9_-]{1,128}")


def cookies_lesen(kopf):
    """Cookie-Kopf als dict; der erste Wert je Name gilt, Kaputtes wird übergangen
    (andere Programme auf demselben Rechner setzen eigene Cookies)."""
    kekse = {}
    for teil in (kopf or "").split(";"):
        name, gleich, wert = teil.partition("=")
        name = name.strip()
        if gleich and name and name not in kekse:
            kekse[name] = wert.strip().strip('"')
    return kekse


def cookie_zeile(name, wert):
    """Set-Cookie-Zeile; ein leerer Wert löscht das Cookie."""
    return (f"{name}={wert}; Max-Age={COOKIE_DAUER[name] if wert else 0}; Path=/; "
            "HttpOnly; SameSite=Strict")
_HOST_MUSTER = re.compile(r"(?:\[(?P<v6>[0-9a-f:.]+)\]|(?P<name>[a-z0-9_.-]+))(?::(?P<port>\d{1,5}))?")


def host_erlaubt(host_kopf):
    """Host-Kopf einer Anfrage prüfen (S2). Kein Kopf = kein Browser (HTTP/1.0,
    Werkzeuge) und damit kein Rebinding-Weg."""
    import ipaddress
    host = (host_kopf or "").strip().lower()
    if not host:
        return True
    m = _HOST_MUSTER.fullmatch(host)
    if not m:
        return False
    if m.group("v6"):
        try:
            ipaddress.IPv6Address(m.group("v6"))
            return True
        except ValueError:
            return False
    name = m.group("name").rstrip(".")
    try:
        ipaddress.IPv4Address(name)
        return True
    except ValueError:
        pass
    if name == "localhost":
        return True
    rechner = (socket.gethostname() or "").strip().lower().split(".")[0]
    return bool(rechner) and name in {rechner} | {rechner + e for e in HEIMNETZ_ENDUNGEN}


def origin_erlaubt(origin, host_kopf):
    """Origin-Kopf prüfen (S2): fehlt er, erlaubt; sonst der eigene Ursprung
    (Host:Port wie im Host-Kopf) oder eine Browser-Erweiterung."""
    origin = (origin or "").strip()
    if not origin:
        return True
    teile = urlparse(origin)
    schema = teile.scheme.lower()
    if schema in ERWEITERUNGS_SCHEMATA:
        return True
    if schema not in ("http", "https") or not host_kopf:
        return False                                  # "null", file:, data: …
    return teile.netloc.lower() == host_kopf.strip().lower()


# ---------------------------------------------------------------- Wer darf was aus dem WLAN?
# JB-Entscheid 7a Punkt 2 (25.09.2026, Gesamtprüfung S10): Ein Gerät im WLAN (mit
# Fernsteuerungs-Code oder Geräte-Token) darf abspielen, suchen, fernsteuern,
# Status und Bibliothek lesen und Downloads anstoßen. Alles, was Dateien löscht
# oder verschiebt, Pfade setzt, config.json oder profile.json schreibt, Profile
# anlegt, Tags oder Metadaten schreibt, Clips erzeugt, Abos oder Playlists
# ändert, WireGuard-Dateien ablegt oder den VPN-Test startet, geht nur vom PC
# selbst (Loopback). Vorher hingen zwölf Einzelprüfungen in zwei Schreibweisen
# an den Routen, und rund zehn verändernde Routen hatten keine.
# Jede Route steht in GENAU einer der beiden Tabellen; der Handler prüft sie vor
# dem Routing (`Handler._lan_tor`). Was in keiner steht, ist aus dem WLAN
# gesperrt (fail-closed). Der Wächter tests/test_wlan_rechte.py liest die Routen
# aus dem Syntaxbaum des Routers und schickt jede mit LAN-Adresse und gültigem
# Code durch den echten Handler.
# LAN_ERLAUBT: (Methode, Pfad) -> (Grund, Prüfer oder None). Ein Prüfer sieht
# die Anfrage-Daten (GET: die Query, je Schlüssel der erste Wert; POST: der
# JSON-Körper) und liefert einen Ablehnungstext, wenn ein Zweig der Route doch
# nur am PC geht. HEAD folgt GET.

def _lan_vlc(daten):
    if daten.get("url") or daten.get("cmd") == "fenster":
        return "Nur am PC: beliebige Adressen im VLC spielen und das Video-Fenster setzen."
    return None


def _lan_biblio(daten):
    # ❤ ist Abspielen-Komfort, „neuladen“ holt einen verschobenen Titel neu
    # (ein Download-Anstoß); löschen, vergessen, Archiv, Explorer, Player … nur am PC.
    if daten.get("art") not in ("herz", "neuladen"):
        return "Nur am PC: die Bibliothek ändern (aus dem WLAN gehen nur ❤ und Neu-Laden)."
    return None


def _lan_action(daten):
    art = daten.get("art")
    if art in ("ordner_offen", "ordner"):
        return "Nur am PC: den Explorer öffnen."
    # „Trotzdem laden“ geht seit Gruppe 6 wieder aus dem WLAN: die vorhandene
    # Datei wandert vorher rückholbar in den Papierkorb (_vorhandene_sichern),
    # es geht also nichts ohne Rückweg verloren.
    return None


def _lan_add(daten):
    roh = daten.get("urls")
    zeilen = links.link_zeilen(roh) if isinstance(roh, str) else []
    if not (len(zeilen) == 1 and links.ist_youtube_link(zeilen[0])):
        return "Aus dem WLAN nur einzelne YouTube-Links (ein Link je Auftrag)."
    if daten.get("ziel_playlist"):
        return "Nur am PC: Titel in eine Playlist einreihen."
    return None


def _lan_kanal_info(daten):
    if not links.ist_youtube_link(str(daten.get("url") or "").strip()):
        return "Aus dem WLAN nur YouTube-Links."
    return None


# Loopback-Sperre für Links vom PC (Fund 06.08., lückenlos seit 25.09.2026, S12):
# eine Adresse, die auf diesen Rechner zeigt, wird nie ein Download — sonst
# erreichte ein Link die eigene Oberfläche oder andere lokale Dienste (Findus,
# Docs). Vorher fing die Sperre nur „localhost“ und die übliche Schreibweise
# der Loopback-Adresse; 127.1, 2130706433, 0x7f000001, 0.0.0.0, Namen unter
# .localhost, Namen, die auf 127.0.0.1 zeigen, und die eigene LAN-Adresse kamen
# durch. Geprüft wird nach der Auflösung. Bleibt: ein Name, der zwischen dieser
# Prüfung und dem Abruf durch yt-dlp umgebogen wird (DNS-Rebinding), fällt
# nicht auf.
_ZAHL_TEIL = re.compile(r"0x[0-9a-f]+|0[0-7]*|[1-9][0-9]*", re.I)


def _zahl_ipv4(text):
    """Die inet_aton-Schreibweisen einer IPv4-Adresse (127.1, 2130706433,
    0x7f000001, 0177.0.0.1) als IPv4Address; None, wenn es keine ist."""
    import ipaddress
    teile = text.split(".")
    if not 1 <= len(teile) <= 4 or not all(_ZAHL_TEIL.fullmatch(t) for t in teile):
        return None
    werte = [int(t, 16) if t[:2].lower() == "0x" else int(t, 8) if len(t) > 1 and t[0] == "0"
             else int(t) for t in teile]
    *vorne, letzte = werte
    if any(w > 255 for w in vorne) or letzte >= 256 ** (4 - len(vorne)):
        return None
    zahl = 0
    for w in vorne:
        zahl = zahl * 256 + w
    return ipaddress.IPv4Address(zahl * 256 ** (4 - len(vorne)) + letzte)


def _namen_aufloesen(host):
    """IP-Adressen eines Namens (eigene Funktion, damit Tests ohne DNS laufen)."""
    try:
        return {str(a[4][0]).split("%")[0] for a in socket.getaddrinfo(host, None)}
    except (OSError, UnicodeError):
        return set()


def _eigene_adressen():
    """Die Adressen dieses Rechners (LAN, auch IPv6) außer Loopback."""
    return _namen_aufloesen(socket.gethostname())


def _adresse_ist_hier(adresse, eigene):
    import ipaddress
    try:
        a = ipaddress.ip_address(str(adresse).split("%")[0])
    except ValueError:
        return False
    if a.is_loopback or a.is_unspecified or str(a) in eigene:
        return True
    if a.version == 6:
        v4 = a.ipv4_mapped or (ipaddress.IPv4Address(int(a)) if int(a) >> 32 == 0 else None)
        if v4 is not None:
            return _adresse_ist_hier(v4, eigene)
        return False
    return a in ipaddress.ip_network("0.0.0.0/8")


def zeigt_auf_diesen_rechner(host):
    """Zeigt ein Link-Host auf den PC selbst? YouTube-Hosts nie (ohne
    Namensauflösung); ein Name, der sich nicht auflösen lässt, gilt als fremd
    (der Download scheitert dann ehrlich in der Liste)."""
    import ipaddress
    host = (host or "").strip().strip("[]").lower().rstrip(".")
    if not host or host == "localhost" or host.endswith(".localhost"):
        return True
    if host in links.YOUTUBE_HOSTS:
        return False
    eigene = _eigene_adressen()
    try:
        adressen = {ipaddress.ip_address(host.split("%")[0])}
    except ValueError:
        zahl = _zahl_ipv4(host)
        adressen = {zahl} if zahl is not None else _namen_aufloesen(host)
    return any(_adresse_ist_hier(a, eigene) for a in adressen)


LAN_ERLAUBT = {
    # Seiten
    ("GET", "/"): ("Oberfläche; gekoppelte Geräte bekommen die volle Seite", None),
    ("GET", "/index.html"): ("Oberfläche (zweiter Name für /)", None),
    ("GET", "/m"): ("Handy-Seite, freier Einstieg mit Code-Eingabe", None),
    ("GET", "/koppeln"): ("Kopplungsseite, frei (Gerät meldet sich an)", None),
    ("GET", "/fernbedienung"): ("Fernbedienung (sendet nur an die eigene Seite)", None),
    # Status und Bibliothek lesen
    ("GET", "/api/status"): ("Status lesen (ohne Code, Pfade und Einstellungen)", None),
    ("GET", "/api/bibliothek"): ("Bibliothek lesen", None),
    ("GET", "/api/playlists"): ("Playlists lesen", None),
    ("GET", "/api/playlist_export"): ("Playlist als M3U lesen", None),
    ("GET", "/api/abos"): ("Abos lesen", None),
    ("GET", "/api/profile"): ("Profile lesen („Wer schaut?“)", None),
    ("GET", "/api/live"): ("Live-Sender lesen", None),
    ("GET", "/api/filme/katalog"): ("Film-Katalog lesen", None),
    ("GET", "/api/filme/zustand"): ("Film-Zustand lesen (Fehler nur als Kurztext)", None),
    ("GET", "/api/filme/reihen"): ("Film-Reihen lesen", None),
    ("GET", "/api/filme/detail"): ("Film-Details lesen", None),
    ("GET", "/api/filme/episoden"): ("Staffeln und Folgen lesen", None),
    ("GET", "/api/filme/mehrwie"): ("ähnliche Filme lesen", None),
    ("GET", "/api/filme/anfragen"): ("eigene Filmwünsche lesen", None),
    # abspielen
    ("GET", "/media"): ("abspielen: Datei-Strom", None),
    ("GET", "/api/cover"): ("abspielen: Cover aus der Datei", None),
    ("GET", "/api/untertitel"): ("abspielen: Untertitel", None),
    ("GET", "/api/lyrics"): ("abspielen: Liedtext", None),
    ("GET", "/api/filme/direkt"): ("abspielen: Film-Strom", None),
    ("GET", "/api/filme/bild"): ("abspielen: Film-Bild", None),
    ("GET", "/api/filme/snippet"): ("abspielen: Vorschau-Szene", None),
    ("POST", "/api/played"): ("abspielen: Wiedergabe mitzählen", None),
    ("POST", "/api/untertitel_laden"): ("abspielen: fehlende Untertitel holen", None),
    ("POST", "/api/filme/fortschritt"): ("abspielen: Stelle und „gesehen“ melden", None),
    ("POST", "/api/filme/merk"): ("abspielen: Film-Merkliste des Profils", None),
    ("POST", "/api/biblio"): ("nur ❤ Lieblingssong und „Erneut herunterladen“", _lan_biblio),
    # fernsteuern
    ("POST", "/api/remote"): ("fernsteuern: Befehl an den PC-Player", None),
    ("POST", "/api/vlc"): ("fernsteuern: VLC-Befehle (ohne fremde Adresse, ohne Fenster)", _lan_vlc),
    ("POST", "/api/filme/play"): ("fernsteuern: Film im VLC am PC", None),
    ("POST", "/api/live/play"): ("fernsteuern: Live-Sender im VLC (nur aus der Senderliste)", None),
    ("GET", "/api/vlc_standbild"): ("fernsteuern: Standbild des VLC", None),
    # suchen
    ("GET", "/api/transkript_suche"): ("suchen: in Untertiteln", None),
    ("GET", "/api/entdecken"): ("suchen: ähnliche Titel entdecken", None),
    ("GET", "/api/filme/wuenschen"): ("suchen: Filme zum Wünschen", None),
    # Downloads anstoßen
    ("POST", "/api/add"): ("Download anstoßen: genau ein YouTube-Link, ohne Playlist-Ziel", _lan_add),
    ("POST", "/api/link_deuten"): ("Download anstoßen: Link deuten (ohne Netz)", None),
    ("GET", "/api/kanal_info"): ("Download anstoßen: Kanal vor dem Laden zählen (nur YouTube)", _lan_kanal_info),
    ("GET", "/api/schaetzfaktoren"): ("Download anstoßen: Größe schätzen", None),
    ("POST", "/api/action"): ("Download-Liste steuern: Pause, Weiter, aus der Liste nehmen", _lan_action),
    ("POST", "/api/filme/anfragen"): ("Filmwunsch an den Film-Server (wie ein Download)", None),
    ("POST", "/api/filme/sync"): ("Film-Katalog neu abrufen (wie Lesen)", None),
    # Kopplung und Fehlerbericht
    ("POST", "/api/geraet_anmelden"): ("Kopplung Schritt 1, frei (höchstens 20 offene Anfragen)", None),
    ("GET", "/api/geraet_status"): ("Kopplung: Token abholen, frei", None),
    ("POST", "/api/js_fehler"): ("Fehlerbericht der Oberfläche (Datei höchstens 200 KB)", None),
}

NUR_PC = {
    ("GET", "/addon.xpi"): "Browser-Erweiterung installiert man am PC",
    ("GET", "/api/addon_hab"): "Browser-Erweiterung am PC",
    ("GET", "/api/addon_hab_liste"): "Browser-Erweiterung am PC",
    ("GET", "/api/addon_update"): "Browser-Erweiterung am PC",
    ("POST", "/api/addon_nachschub"): "Browser-Erweiterung am PC",
    ("GET", "/api/geraete"): "Geräte verwalten (profile.json)",
    ("GET", "/api/geraet_qr"): "Geräte verwalten (profile.json)",
    ("POST", "/api/geraet_bestaetigen"): "Gerät freigeben schreibt profile.json",
    ("POST", "/api/geraet_entfernen"): "Gerät trennen schreibt profile.json",
    ("POST", "/api/profil_anlegen"): "legt ein Profil an (profile.json)",
    ("GET", "/api/ordner_waehlen"): "öffnet einen Dialog am PC und setzt Pfade",
    ("GET", "/api/pfad_da"): "prüft Pfade auf dem PC",
    ("GET", "/api/geo_status"): "Geo-Einstellungen (mit lokalen Pfaden)",
    ("POST", "/api/config"): "schreibt config.json",
    ("POST", "/api/code_erneuern"): "neuer Fernsteuerungs-Code (config.json)",
    ("POST", "/api/wiedergabe"): "Wiedergabe-Regeln schreiben config.json",
    ("POST", "/api/beenden"): "beendet das Programm",
    ("GET", "/api/migration_probelauf"): "Umbenennen verschiebt Dateien",
    ("POST", "/api/umbenennen"): "verschiebt Dateien",
    ("POST", "/api/biblio_enrich"): "schreibt Metadaten",
    ("POST", "/api/autotag"): "schreibt Tags in Dateien",
    ("POST", "/api/clip"): "erzeugt Clips",
    ("POST", "/api/clip_favorit"): "ändert die Bibliothek",
    ("POST", "/api/playlist"): "ändert Playlists, der Spiegel-Sync verschiebt Dateien",
    ("POST", "/api/playlist_import"): "legt Playlists an",
    ("POST", "/api/abo"): "ändert Abos und löscht Abo-Videos",
    ("POST", "/api/geo_wireguard"): "legt WireGuard-Dateien ab und schreibt config.json",
    ("POST", "/api/geo_test"): "startet den VPN-Test",
}


def lan_ablehnung(methode, pfad, daten):
    """Ablehnungstext für eine Anfrage aus dem WLAN, oder None, wenn sie darf."""
    methode = "GET" if methode == "HEAD" else methode
    eintrag = LAN_ERLAUBT.get((methode, pfad))
    if eintrag is None:
        grund = NUR_PC.get((methode, pfad))
        return f"Nur am PC: {grund}." if grund else "Nur am PC."
    pruefer = eintrag[1]
    return pruefer(daten if isinstance(daten, dict) else {}) if pruefer else None


def _cors(handler):
    """CORS nur für Browser-Erweiterungen freigeben (nie für beliebige Webseiten —
    der Server lauscht ohnehin nur auf 127.0.0.1). Erlaubt das Firefox-Addon,
    Links direkt an die Warteschlange zu schicken."""
    origin = handler.headers.get("Origin", "")
    if origin.startswith(tuple(s + "://" for s in ERWEITERUNGS_SCHEMATA)):
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Access-Control-Allow-Headers", "Content-Type")
        handler.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")


def _antwort(handler, code, daten, ctype="application/json", cache=None):
    body = daten if isinstance(daten, bytes) else json.dumps(daten, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", ctype + "; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    if cache:                                         # z. B. Cover: Browser darf behalten
        handler.send_header("Cache-Control", f"max-age={int(cache)}")
    _cors(handler)
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    # S14: Zeitlimit für das LESEN einer Anfrage (Kopf und Körper). Es gilt je
    # Leseschritt: ein Client, der 30 s lang nichts mehr schickt, gibt den
    # Faden frei. Beim Antworten gilt es ebenfalls, und dort wertet sendall es
    # als Gesamtdauer je Schreibaufruf, nicht je Schritt. Kleine Antworten
    # stört das nicht; die Strom-Wege heben es nach dem Kopf auf
    # (_schreib_zeitlimit_aufheben), sonst bräche ein pausierter Film ab.
    timeout = 30
    # Je Anfrage in _hat_zugriff gesetzt (7a Punkt 1); die Vorgaben gelten, wenn
    # eine Anfrage den Riegel nie erreicht (abgewiesener Host, Fehlerseite).
    _neue_cookies = ()
    _zugang_aus_adresse = False

    def handle_one_request(self):
        # Jede Anfrage liest wieder mit Zeitlimit, auch nach einem Strom auf
        # derselben Verbindung (falls der Handler je Keep-Alive spricht).
        try:
            self.connection.settimeout(self.timeout)
        except (AttributeError, OSError):
            pass
        self._neue_cookies = []                       # je Anfrage neu (auch bei Keep-Alive)
        super().handle_one_request()

    def log_message(self, *a):                        # Konsole ruhig halten
        pass

    def end_headers(self):
        # S2: einbetten darf nur das Dashboard (und die App selbst) — für JEDE
        # Antwort, auch die direkt geschriebenen (Medien, Proxy, Export).
        self.send_header("Content-Security-Policy", EINBETTEN_CSP)
        # S17: kein Link und kein nachgeladenes Bild nimmt die Adresse der Seite
        # mit (früher stand dort der Token oder Code).
        self.send_header("Referrer-Policy", "no-referrer")
        for zeile in self._neue_cookies:
            self.send_header("Set-Cookie", zeile)
        super().end_headers()

    def _anfrage_vertraut(self):
        """S2: Host- und Origin-Kopf, vor jedem Riegel und jeder Route."""
        host = self.headers.get("Host", "")
        return host_erlaubt(host) and origin_erlaubt(self.headers.get("Origin"), host)

    def do_OPTIONS(self):                             # CORS-Preflight des Addons
        if not self._anfrage_vertraut():
            return _antwort(self, 403, {"fehler": "Anfrage von fremder Seite abgelehnt."})
        self.send_response(204)
        _cors(self)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def _ist_lokal(self):
        """Der PC selbst (Loopback, auch ::1): die EINE Schreibweise des Riegels (S10)."""
        return ist_loopback(self.client_address[0] if self.client_address else "")

    def _lan_tor(self, methode, daten):
        """S10: Aus dem WLAN nur, was LAN_ERLAUBT zulässt (vor dem Routing).
        None = weiter; sonst der Ablehnungstext."""
        if self._ist_lokal():
            return None
        return lan_ablehnung(methode, urlparse(self.path).path, daten)

    def _zugangsdaten(self):
        """((Token, Herkunft), (Code, Herkunft)): je der erste gefüllte Wert aus
        Adresse, Kopf (X-Geraet/X-Code) oder Cookie (7a Punkt 1)."""
        q = parse_qs(urlparse(self.path).query)
        kekse = cookies_lesen(self.headers.get("Cookie", ""))

        def eins(param, kopf, keks):
            for quelle, wert in (("adresse", (q.get(param) or [""])[0]),
                                 ("kopf", self.headers.get(kopf, "") or ""),
                                 ("cookie", kekse.get(keks, ""))):
                if wert:
                    return wert, quelle
            return "", ""
        return eins("geraet", "X-Geraet", COOKIE_GERAET), eins("code", "X-Code", COOKIE_CODE)

    def _keks_merken(self, name, wert, quelle, gueltig, verlaengern=False):
        """Gültig aus Adresse oder Kopf: Cookie setzen. Gültig aus dem Cookie
        und `verlaengern` (eine Seite öffnet): mit voller Laufzeit neu setzen.
        Ungültig aus dem Cookie: Cookie löschen. Alles andere bleibt, wie es ist."""
        neu_setzen = quelle in ("adresse", "kopf") or (verlaengern and quelle == "cookie")
        if gueltig and neu_setzen and _COOKIE_WERT.fullmatch(wert):
            self._neue_cookies.append(cookie_zeile(name, wert))
        elif not gueltig and quelle == "cookie":
            self._neue_cookies.append(cookie_zeile(name, ""))

    def _geraet_profil(self):
        """Profil des anfragenden Geräts: localhost = im UI gewählt (Query),
        LAN-Gerät = an den Token gebunden (Teilprojekt 3; Token auch aus dem Cookie)."""
        (tok, _quelle), _code = self._zugangsdaten()
        p = profil_geraete.geraet_ok(tok)
        if p:
            return p
        q = parse_qs(urlparse(self.path).query)
        return (q.get("profil") or ["standard"])[0] if self._ist_lokal() else "standard"

    def _hat_zugriff(self):
        """Localhost immer; aus dem LAN: Pairing-Wege frei, sonst NUR mit
        verifiziertem Geräte-Token ODER dem Fernsteuerungs-Code (Riegel-
        PFLICHT, JB: Externe nur mit Zugangsdaten), aus Adresse, Kopf oder
        Cookie. Merkt nebenbei, welche Cookies die Antwort setzt oder löscht
        und ob der Zugang aus der Adresse kam (dann leitet eine Seite um)."""
        self._neue_cookies = []
        self._zugang_aus_adresse = False
        ip = self.client_address[0] if self.client_address else ""
        if self._ist_lokal():
            return True
        if not CFG.get("fernsteuerung"):             # S13: aus heißt aus, sofort und
            return False                             # auch für gekoppelte Geräte
        pfad = urlparse(self.path).path
        if pfad in KOPPEL_API:
            return True                              # Pairing muss VOR dem Token gehen
        frei = pfad in FREIE_SEITEN                  # Code-Eingabe und Koppel-Seite
        (tok, tok_quelle), (code, code_quelle) = self._zugangsdaten()
        if not (tok or code):                        # nichts zu raten: zählt nicht
            return frei
        if not _bremse_versuch(ip):                  # S7: prüfen und belegen in EINEM Schritt
            return frei
        ok = profil = code_ok = None
        try:
            profil = profil_geraete.geraet_ok(tok)
            code_ok = not profil and zugriff_erlaubt(
                ip, CFG.get("fernsteuerung"), CFG.get("fernsteuerung_code") or "", code)
            ok = bool(profil or code_ok)
        finally:
            if ok is None:
                _bremse_freigeben(ip)                # Ausnahme im Vergleich: nichts zählen
            elif ok:
                _bremse_erfolg(ip)
            else:
                _bremse_fehlversuch(ip)
        if tok:                                      # gleitend: nur Seiten, nie die API
            seite = pfad in VERLAENGERN_SEITEN and self.command in ("GET", "HEAD")
            self._keks_merken(COOKIE_GERAET, tok, tok_quelle, bool(profil), verlaengern=seite)
        if code and not profil:
            self._keks_merken(COOKIE_CODE, code, code_quelle, bool(code_ok))
        self._zugang_aus_adresse = bool((profil and tok_quelle == "adresse")
                                        or (code_ok and code_quelle == "adresse"))
        return ok or frei

    def _ohne_zugang_umleiten(self):
        """7a Punkt 1: Token oder Code aus der Adresse ist jetzt ein Cookie; die
        Seite lädt sich ohne den Parameter neu (raus aus Adresszeile, Verlauf
        und Lesezeichen). Alle anderen Parameter (etwa embed=1) bleiben."""
        teile = urlparse(self.path)
        rest = [(k, v) for k, v in parse_qsl(teile.query, keep_blank_values=True)
                if k not in ("geraet", "code")]
        self.send_response(302)
        self.send_header("Location", teile.path + ("?" + urlencode(rest) if rest else ""))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _fernsteuerung_aus(self):
        """S13: aus heißt aus, für jedes Gerät im WLAN, auch ein gekoppeltes.
        Nachschärfung 25.09.2026: das Gerät erfährt es ehrlich, statt „nicht
        gekoppelt“ zu lesen; eine Seite bekommt Text statt JSON."""
        if urlparse(self.path).path in SEITEN:
            return _antwort(self, 403, profil_geraete.FERNSTEUERUNG_AUS_HTML.encode("utf-8"), "text/html")
        return _antwort(self, 403, {"fehler": FERNSTEUERUNG_AUS_TEXT})

    def do_GET(self):
        if not self._anfrage_vertraut():
            return _antwort(self, 403, {"fehler": "Anfrage von fremder Seite abgelehnt."})
        if not self._hat_zugriff():
            if not CFG.get("fernsteuerung"):         # der PC selbst kommt hier nie an
                return self._fernsteuerung_aus()
            # Nicht gekoppeltes LAN-Gerät auf der Startseite? Dann die
            # Pairing-Seite statt einer kalten 403 (Teilprojekt 3).
            if (urlparse(self.path).path in ("/", "/index.html")
                    and CFG.get("fernsteuerung")):   # S13: aus = auch keine Koppel-Seite
                return _antwort(self, 200, profil_geraete.PAIRING_HTML.encode("utf-8"), "text/html")
            return _antwort(self, 403, {"fehler": "Kein Zugriff — Gerät nicht gekoppelt."})
        if self._zugang_aus_adresse and urlparse(self.path).path in SEITEN:
            return self._ohne_zugang_umleiten()
        q = parse_qs(urlparse(self.path).query)
        ablehnung = self._lan_tor(self.command or "GET", {k: v[0] for k, v in q.items() if v})
        if ablehnung:
            return _antwort(self, 403, {"fehler": ablehnung, "nur_pc": True})
        self._get_routen()

    def _get_routen(self):
        """Der GET-Router; Riegel und WLAN-Tor liegen davor in do_GET. Verglichen
        wird wie im Tor und im POST-Router der Pfad ohne Anfrageteil, genau
        (Gruppe 6: vorher teils self.path samt Anfrageteil, teils nur der Anfang)."""
        route = urlparse(self.path).path
        if route == "/koppeln":       # Pairing-Seite direkt
            return _antwort(self, 200, profil_geraete.PAIRING_HTML.encode("utf-8"), "text/html")
        if route == "/fernbedienung":  # Fake-Fernbedienung (JB 07.08.), heiß wie die Oberfläche
            return _antwort(self, 200, _seite_frisch("fernbedienung").encode("utf-8"), "text/html")
        # Der Alias /handy ist entfallen (JB-Entscheid 7a Punkt 8, 25.09.2026): kein
        # Verweis, das README nennt nur /m.
        if route == "/m":                 # schlanke Handy-Oberfläche
            return _antwort(self, 200, _seite_frisch("handy").encode("utf-8"), "text/html")
        if route in ("/", "/index.html"):
            # Query ignorieren (JB 21.07.: Dashboard lädt „/?embed=1" -> Einbettungs-Modus).
            # Oberfläche bei jedem Aufruf FRISCH laden (sonst cacht Python das Modul
            # und Änderungen an oberflaeche.py erscheinen erst nach App-Neustart —
            # ein Browser-Refresh reicht jetzt).
            _antwort(self, 200, _seite_frisch("oberflaeche").encode("utf-8"), "text/html")
        elif route == "/api/status":
            lokal = self._ist_lokal()
            # Nachtprüfung 06.08. (Riegel-Regel „Externe nur mit Zugangsdaten"):
            # der volle Status verriet aus dem LAN den Fernsteuerungs-Code
            # (Widerruf damit wirkungslos) und die ganze Config (Pfade,
            # Proxys). Nicht-lokal bekommt nur, was die Handy-UI braucht.
            # ui_stand: mtime der Oberfläche samt Baustein (_ui_stand).
            ui_stand = _ui_stand()
            # F7: unter Q.lock nur der Schnappschuss der Liste; Platte, Statistik
            # und das Senden (ein langsamer Client im WLAN) laufen ohne Sperre.
            with Q.lock:
                items = [dict(it) for it in Q.items]
            # „lokal“ (7a Punkt 1): die Oberfläche blendet auf Geräten im WLAN
            # die Einstellungen und alle nur-PC-Aktionen aus.
            if lokal:
                _antwort(self, 200, {"items": items, "config": CFG, "lokal": True,
                                     "ziel": ziel_ordner(), "ffmpeg": bool(_ffmpeg_exe()),
                                     "vpn": geo.nordvpn_verfuegbar(), "db": db_statistik(),
                                     "remote": _remote, "fernsteuerung": fernsteuerung_info(),
                                     "addon_nachschub": _addon_nachschub,
                                     "autotag": _autotag, "addon_xpi": bool(_addon_xpi_pfad()),
                                     "ui_stand": ui_stand, "jetzt": time.time()})
            else:
                # „wiedergabe“ (Untertitel-Größe, Tempo je Titel) seit 25.09.2026:
                # ein gekoppelter Fernseher spielt mit JBs Wiedergabe-Regeln.
                harmlos = {k: CFG.get(k) for k in
                           ("standard_qualitaet", "unterordner", "metadaten",
                            "untertitel", "parallel", "wiedergabe")}
                _antwort(self, 200, {"items": items, "config": harmlos, "lokal": False,
                                     "ffmpeg": bool(_ffmpeg_exe()),
                                     "db": db_statistik(),
                                     "ui_stand": ui_stand, "jetzt": time.time()})
        elif route == "/addon.xpi":
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
        elif route == "/api/bibliothek":
            # Build 122 (JB: „Dateien aus dem Ordner aufnehmen sollte
            # selbstständig passieren — merkt man das nicht?"): Wer die
            # Bibliothek ansieht, bekommt sie frisch. Der Ordner-Blick läuft
            # dafür kurz vorher, höchstens einmal pro Minute und im
            # Hintergrund — KEIN Dauerprozess, kein neuer Zeitplan
            # (Last-Budget-Regel), aber in der Praxis merkt man es sofort.
            _auto_import_anstossen()
            # F7: bibliothek_liste arbeitet auf einem Schnappschuss (F6); der
            # Ordnerlauf (_datei_index) und das Senden halten keine Sperre.
            _antwort(self, 200, {"items": bibliothek_liste()})
        elif route == "/api/playlists":
            with _io_lock:                            # F7: Text unter der Sperre, Senden danach
                body = json.dumps({"items": _playlists}, ensure_ascii=False).encode("utf-8")
            _antwort(self, 200, body)
        elif route == "/api/abos":
            with _io_lock:
                body = json.dumps({"items": _abos}, ensure_ascii=False).encode("utf-8")
            _antwort(self, 200, body)
        elif route == "/api/kanal_info":   # ganzen Kanal aufloesen (Name + Videozahl)
            q = parse_qs(urlparse(self.path).query)
            url = (q.get("url") or [""])[0]
            _antwort(self, 200, kanal_info(url, limit=(q.get("limit") or [None])[0]))
        elif route == "/api/cover":       # eingebettetes Album-Cover (Etappe A)
            key = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            bild = cover_aus_datei(key)
            if bild:
                # 1 h Browser-Cache: die Bibliothek malt sich oft neu, das
                # Cover in der Datei ändert sich praktisch nie (JB 05.08.:
                # Kacheln zeigen jetzt das echte Cover — ohne Cache läse der
                # Server bei jedem Filter/Sortieren alle MP3s neu).
                _antwort(self, 200, bild, "image/jpeg", cache=3600)
            else:
                _antwort(self, 404, {"fehler": "kein eingebettetes Cover"})
        # ---- Film-Fundament (Doku/SYNC_FILME_SPEC.md): nur gemappte Felder
        # und lokal gecachte Bilder gehen raus — nie Token/Server-Adresse.
        elif route == "/api/filme/katalog":
            _antwort(self, 200, filme.katalog_lesen())
        elif route == "/api/filme/zustand":
            # Damit ein Ausfall SICHTBAR wird: der 403 vom 06.08. lief sieben
            # Tage, ohne dass irgendetwas davon erzählt hat — auch vom Sofa aus
            # muss man das sehen, die Route ist deshalb nicht lokal-only.
            # ABER: der rohe Fehlertext kann eine urllib-Ausnahme MIT Renés
            # Server-Adresse enthalten. Fremde Geräte im WLAN bekommen deshalb
            # nur die Tatsache, nicht den Wortlaut.
            # Seit 24.09. mit Fehlerart: fremde Geräte bekommen einen Kurztext je
            # Art (ohne Adresse, ohne Rohtext) statt pauschal „nicht erreichbar"
            # — der Ausfall vom 23.09. war erreichbar, er lehnte die Anmeldeform ab.
            z = filme.zustand()
            if not self._ist_lokal() and z.get("fehler"):
                z["fehler"] = filme.FEHLER_ART_TEXT.get(z.get("fehler_art"),
                                                        "Server nicht erreichbar")
            _antwort(self, 200, z)
        elif route == "/api/filme/reihen":
            _antwort(self, 200, filme.reihen(self._geraet_profil()))
        elif route == "/api/filme/detail":
            fid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            d = filme.detail(fid, self._geraet_profil())
            if d:
                _antwort(self, 200, d)
            else:
                _antwort(self, 404, {"fehler": "unbekannter Film"})
        # ---- Teilprojekt 3: Profile + Geräte -------------------------------
        elif route == "/api/profile":
            _antwort(self, 200, {"items": profil_geraete.profil_liste(),
                                 "aktiv": self._geraet_profil()})
        elif route == "/api/geraet_status":   # Pairing-Poll (frei)
            q = parse_qs(urlparse(self.path).query)
            t = profil_geraete.geraet_token_abholen(
                (q.get("id") or [""])[0], (q.get("code") or [""])[0])
            _antwort(self, 200, t or {"wartet": True})
        elif route == "/api/geraete":         # NUR PC: Geräte-Übersicht (NUR_PC)
            _antwort(self, 200, {"items": profil_geraete.geraete_liste(),
                                 "url": f"http://{_lan_ip()}:{int(CFG.get('port', 8776))}/koppeln",
                                 "wlan": bool(CFG.get("fernsteuerung"))})
        elif route == "/api/geraet_qr":       # NUR PC: QR zum Abfotografieren (NUR_PC)
            try:
                import io
                import qrcode
                img = qrcode.make(f"http://{_lan_ip()}:{int(CFG.get('port', 8776))}/koppeln")
                b = io.BytesIO()
                img.save(b, "PNG")
                _antwort(self, 200, b.getvalue(), "image/png")
            except Exception as e:                   # noqa: BLE001 — Link steht daneben
                _antwort(self, 500, {"fehler": f"QR: {e}"})
        elif route == "/api/filme/snippet":   # Hover-Szene (6 s, stumm)
            fid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            clip = filme.snippet_lesen(fid)
            if clip:
                _antwort(self, 200, clip, "video/mp4", cache=86400)
            else:                                     # noch nicht gebacken ⇒ anstoßen
                threading.Thread(target=filme.snippet_backen, args=(fid,),
                                 daemon=True).start()
                _antwort(self, 404, {"wartet": True})
        elif route == "/api/live":           # 📡 Live-Kanäle (kodinerds)
            _antwort(self, 200, {"items": live_tv.kanaele(), "status": live_tv.status()})
        elif route == "/api/filme/wuenschen":  # Seerr-Suche (Teilprojekt 4)
            q = (parse_qs(urlparse(self.path).query).get("q") or [""])[0]
            _antwort(self, 200, {"items": filme.seerr_suche(q)})
        elif route == "/api/filme/anfragen":   # meine Wünsche + Stand
            _antwort(self, 200, {"items": filme.seerr_meine()})
        elif route == "/api/filme/episoden":  # Serien: Staffeln + Folgen
            fid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            # Additiv (24.09.): bei gestörtem Zugang zusätzlich fehler 'zugang'|
            # 'netz' — sonst sah ein 401 aus wie eine Serie ohne Folgen.
            items, fehler = filme.episoden_mit_grund(fid)
            _antwort(self, 200, {"items": items, "fehler": fehler} if fehler
                     else {"items": items})
        elif route == "/api/filme/mehrwie":   # TMDB-Empfehlungen ∩ Katalog
            fid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            _antwort(self, 200, {"items": filme.mehr_wie(fid)})
        elif route == "/api/vlc_standbild":
            try:
                with open(os.path.join(DATEN_DIR, "vlc_standbild.png"), "rb") as f:
                    _antwort(self, 200, f.read(), "image/png")
            except OSError:
                _antwort(self, 404, {"fehler": "kein Standbild"})
        elif route == "/api/filme/direkt":
            # Browser-Player (JB 06.08.: „Ich will wie bei netflix das im
            # Browser öffnen"): der Server PROXYT den Jellyfin-Strom mit
            # Range-Durchreichung — der Token bleibt auf diesem PC, der
            # Client sieht nur diese Adresse. Mit tc=1 (JB-Go: „Geh das
            # serverseitige Transcoding an") wandelt ffmpeg unterwegs:
            # Video bleibt Kopie, wenn der Browser es kann (vcopy=1, z. B.
            # h264+AC3 → nur der Ton wird AAC), sonst libx264; Container
            # wird fragmentiertes MP4 — das spielt jedes <video>.
            q = parse_qs(urlparse(self.path).query)
            # JBs Druck (der Film läuft, weil er ▶ gedrückt hat): durch die
            # Merkmal-Ruhe, höchstens eine Anmeldung je Ruhe (Prüfung Runde 2).
            url = filme.stream_url((q.get("id") or [""])[0], druck=True)
            if not url:
                return _antwort(self, 503, {"fehler": "Anmeldung bei Jellyfin "
                                            "gescheitert — heilt sich nach dem "
                                            "Anmelde-Backoff von selbst."})
            globals()["_letzter_stream"] = time.time()   # Selbst-Neustart wartet
            if (q.get("tc") or ["0"])[0] == "1":
                if not _ffmpeg_exe():
                    return _antwort(self, 503, {"fehler": "ffmpeg fehlt"})
                abgelehnt = _strom_vorprobe(url)
                if abgelehnt:                            # ehrlich wie der Direkt-Zweig; ffmpeg startet nicht
                    return _antwort(self, *abgelehnt)
                try:
                    start = max(0, int(float((q.get("start") or ["0"])[0])))
                except (TypeError, ValueError):
                    start = 0
                cmd = _transcode_befehl(
                    url, start, (q.get("vcopy") or ["0"])[0] == "1")
                proz = _tc_starten(cmd)
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Accept-Ranges", "none")
                self.end_headers()
                _schreib_zeitlimit_aufheben(self)        # S14: Pause darf den Strom nicht töten
                try:
                    while True:
                        stueck = proz.stdout.read(262144)
                        if not stueck:
                            break
                        self.wfile.write(stueck)
                        globals()["_letzter_stream"] = time.time()
                except (OSError, ConnectionError):
                    pass                                 # Client weg — ffmpeg stirbt mit
                finally:
                    try:
                        proz.kill()
                    except OSError:
                        pass
                return
            kopf = {}
            if self.headers.get("Range"):
                kopf["Range"] = self.headers["Range"]
            try:
                req = urllib.request.Request(url, headers=kopf)
                try:
                    r = urllib.request.urlopen(req, timeout=30)
                except urllib.request.HTTPError as e:
                    # Ehrlich statt still (Gegenprüfung 24.09.): HTTPError ist ein
                    # OSError und landete im stillen except unten — es ging GAR
                    # KEINE Antwort raus, der Browser sah nur einen abgebrochenen
                    # Strom. Jetzt Jellyfins Status und ein kurzer Text; nie die
                    # Adresse (sie trägt das Token).
                    e.close()
                    return _antwort(self, *_strom_fehler(e))
                except OSError:                          # URLError, Zeitüberschreitung
                    return _antwort(self, *_strom_fehler())
                with r:
                    self.send_response(r.status)
                    for h in ("Content-Type", "Content-Length",
                              "Content-Range", "Accept-Ranges"):
                        if r.headers.get(h):
                            self.send_header(h, r.headers[h])
                    self.end_headers()
                    _schreib_zeitlimit_aufheben(self)    # S14: Pause darf den Strom nicht töten
                    while True:
                        stueck = r.read(262144)
                        if not stueck:
                            break
                        self.wfile.write(stueck)
                        globals()["_letzter_stream"] = time.time()
            except (OSError, ConnectionError):
                pass                                     # Client weg / Netz — still
        elif route == "/api/filme/bild":
            q = parse_qs(urlparse(self.path).query)
            bild = filme.bild_holen((q.get("id") or [""])[0],
                                    (q.get("art") or ["Primary"])[0])
            if bild:
                _antwort(self, 200, bild, "image/jpeg", cache=86400)
            else:
                _antwort(self, 404, {"fehler": "kein Bild"})
        elif route == "/api/addon_hab_liste":  # Erweiterung: Playlist schon eingereiht? (v1.1.2)
            lid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            _antwort(self, 200, addon_hab_liste(lid))
        elif route == "/api/addon_hab":    # Erweiterung: Video schon in der Bibliothek? (Build 98)
            vid = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            _antwort(self, 200, addon_hab(vid))
        elif route == "/api/addon_update":  # Erweiterung: neueste Kanal-Version (v1.1.1)
            _antwort(self, 200, addon_update_info())
        elif route == "/api/schaetzfaktoren":   # MB/min je Qualitaet (Build 105)
            _antwort(self, 200, {q: _mb_pro_min(q) for q in QUALITAETEN})
        elif route == "/api/ordner_waehlen":    # nativer Ordnerdialog (Build 108), NUR_PC
            start = (parse_qs(urlparse(self.path).query).get("start") or [""])[0]
            _antwort(self, 200, ordner_waehlen(start))
        elif route == "/api/pfad_da":      # Sync-Fenster-Failsafe (Build 109), NUR_PC
            _antwort(self, 200, pfad_da((parse_qs(urlparse(self.path).query).get("pfad") or [""])[0]))
        elif route == "/api/migration_probelauf":   # Umbenennen, NUR Auslese (Build 112/113), NUR_PC
            q = parse_qs(urlparse(self.path).query)
            roh = (q.get("schema") or [""])[0]
            schema = [b for b in roh.split(",") if b in NAME_BAUSTEINE] or None
            plan = migration_probelauf(schema)
            _antwort(self, 200, {"eintraege": plan[:400],
                                 "gesamt": len(plan),
                                 "bereit": sum(1 for x in plan if not x["konflikt"]),
                                 "konflikte": sum(1 for x in plan if x["konflikt"]),
                                 "laeufe": migration_laeufe()[-5:]})
        elif route == "/api/entdecken":    # 📻 Neues entdecken (Build 99)
            q = parse_qs(urlparse(self.path).query)
            _antwort(self, 200, entdecken((q.get("pl") or [""])[0],
                                          seeds=(q.get("seeds") or [3])[0],
                                          je_seed=(q.get("je") or [25])[0]))
        elif route == "/api/playlist_export":
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
        elif route == "/api/geo_status":
            st = geo.status(CFG)
            st["config"] = {k: CFG.get(k) for k in ("geo_vpn", "geo_gratis_proxy")}
            st["proxy_anzahl"] = len(CFG.get("geo_proxies") or [])
            st["test"] = _geo_test
            _antwort(self, 200, st)
        elif route == "/api/lyrics":
            q = parse_qs(urlparse(self.path).query)
            key = (q.get("id") or [""])[0]
            lrc = lyrics_holen(key)
            _antwort(self, 200, {"lrc": lrc, "quelle": "lrclib" if lrc else ""})
        elif route == "/api/transkript_suche":
            q = parse_qs(urlparse(self.path).query)
            _antwort(self, 200, {"treffer": transkript_suche((q.get("q") or [""])[0])})
        elif route == "/api/untertitel":
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
        elif route == "/media":
            key = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
            pfad = _pfad_zu_key(key)
            if pfad and os.path.isfile(pfad):
                _stream_datei(self, pfad)
            else:
                _antwort(self, 404, {"fehler": "Datei nicht gefunden"})
        else:
            _antwort(self, 404, {"fehler": "unbekannt"})

    def do_POST(self):
        # Abgewiesen wird ohne den Körper zu lesen; die Verbindung schließt
        # danach immer (wie bei 400/413), sonst würde ein Körper, der selbst
        # eine Anfrage enthält, bei Keep-Alive als zweite Anfrage gelesen.
        if not self._anfrage_vertraut():
            self.close_connection = True
            return _antwort(self, 403, {"fehler": "Anfrage von fremder Seite abgelehnt."})
        if not self._hat_zugriff():
            self.close_connection = True
            if not CFG.get("fernsteuerung"):         # der PC selbst kommt hier nie an
                return self._fernsteuerung_aus()
            return _antwort(self, 403, {"fehler": "Kein Zugriff — Fernsteuerung aus oder falscher Code."})
        # S14: negative oder unlesbare Länge -> 400, über 2 MB -> 413; in beiden
        # Fällen wird der Körper nicht gelesen und die Verbindung geschlossen.
        roh = (self.headers.get("Content-Length") or "").strip()
        try:
            n = int(roh) if roh else 0
        except ValueError:
            n = -1
        if n < 0:
            self.close_connection = True
            return _antwort(self, 400, {"fehler": "Content-Length ungültig"})
        if n > MAX_KOERPER:
            self.close_connection = True
            return _antwort(self, 413, {"fehler": "Anfrage zu groß (höchstens 2 MB)"})
        try:
            daten = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except ValueError:
            return _antwort(self, 400, {"fehler": "kein JSON"})
        ablehnung = self._lan_tor("POST", daten)
        if ablehnung:
            return _antwort(self, 403, {"fehler": ablehnung, "nur_pc": True})
        self._post_routen(daten)

    def _post_routen(self, daten):
        """Der POST-Router; Riegel, Körper-Prüfung und WLAN-Tor liegen davor in do_POST.
        Verglichen wird der Pfad ohne Anfrageteil, wie im WLAN-Tor (Abnahme
        25.09.2026): vorher lief POST /api/filme/merk?profil=… auf 404."""
        pfad = urlparse(self.path).path
        try:
            if pfad == "/api/remote":            # Befehl vom Handy an den PC-Player
                return _antwort(self, 200, remote_befehl(daten))
            if pfad == "/api/vlc":               # Gerät „VLC": Befehl an den VLC-Motor
                # Nachtprüfung 06.08.: play mit BELIEBIGER url (lokale Datei,
                # LAN-Adresse) und das Fenster-Handle setzt nur der PC selbst
                # (Prüfer _lan_vlc im WLAN-Tor).
                return _antwort(self, 200, vlc_kommando(daten))
            if pfad == "/api/wiedergabe":        # Grundeinstellungen: global/Playlist/Titel
                return _antwort(self, 200, wiedergabe_setzen(daten))
            if pfad == "/api/addon_nachschub":   # Addon reicht Vorgemerktes nach (v1.2.0)
                return _antwort(self, 200, addon_nachschub(daten))
            if pfad == "/api/beenden":
                # Sauberes Beenden aus der Suite (JB 14.07.2026: im Suite-Betrieb gibt es
                # kein eigenes Tray mehr — Steuerung über SyncDashTray/Dashboard). Nur vom
                # eigenen PC (bei aktiver Handy-Fernsteuerung lauscht der Server im WLAN;
                # NUR_PC im WLAN-Tor).
                Q.speichern()
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return _antwort(self, 200, {"ok": True})
            if pfad == "/api/add":
                self._add(daten)
            elif pfad == "/api/action":
                self._action(daten)
            elif pfad == "/api/config":
                # Grundeinstellungen (Zielordner!) schreibt nur der PC selbst (NUR_PC).
                self._config(daten)
            elif pfad == "/api/code_erneuern":   # Knopf „Code erneuern“ (7a Punkt 3, NUR_PC)
                with _cfg_lock:
                    CFG["fernsteuerung_code"] = neuer_fernsteuerungs_code()
                    _cfg_speichern()
                return _antwort(self, 200, fernsteuerung_info())
            elif pfad == "/api/js_fehler":      # Fehler-Rekorder der Oberfläche
                # Derselbe Schreiber wie der Fehlerkanal: Sperre, Deckel 200 KB.
                _zeile_anhaengen(JS_FEHLER_LOG, {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                                                 "text": str(daten.get("text") or "")[:400],
                                                 "quelle": str(daten.get("quelle") or "")[:80],
                                                 "zeile": daten.get("zeile") or 0,
                                                 # 06.09.: Promise-Fehler kamen ohne Ort an (P8)
                                                 "stack": str(daten.get("stack") or "")[:600]})
                return _antwort(self, 200, {"ok": True})
            elif pfad == "/api/played":         # ein Titel wurde abgespielt
                with _io_lock:
                    e = _geladen.get(daten.get("id") or "")
                    if e:
                        e["plays"] = int(e.get("plays", 0)) + 1
                        e["last_play"] = time.time()  # für „Zuletzt gespielt"
                        _geladen_speichern()
            elif pfad == "/api/biblio":
                self._biblio(daten)
            elif pfad == "/api/biblio_enrich":
                threading.Thread(target=biblio_enrich_alle, daemon=True).start()
            elif pfad == "/api/umbenennen":      # Namens-Baukasten anwenden/zurück (Build 113), NUR_PC
                if daten.get("art") == "undo":
                    _antwort(self, 200, migration_rueckgaengig())
                else:
                    schema = [b for b in (daten.get("schema") or []) if b in NAME_BAUSTEINE] or None
                    _antwort(self, 200, migration_anwenden(go=bool(daten.get("go")), schema=schema,
                                                           keys=daten.get("keys") or None))
            elif pfad == "/api/playlist":
                if daten.get("art") == "sync":
                    pl = next((p for p in _playlists if p.get("id") == daten.get("id")), None)
                    return _antwort(self, 200, playlist_sync(pl))
                neu_id = playlist_aktion(daten)
                if isinstance(neu_id, dict):          # abgelehnte Sync-Einrichtung
                    return _antwort(self, 200, neu_id)
                if neu_id:
                    return _antwort(self, 200, {"ok": True, "id": neu_id})
            elif pfad == "/api/geo_wireguard":
                return _antwort(self, 200, self._geo_wireguard(daten))
            elif pfad == "/api/geo_test":
                return _antwort(self, 200, self._geo_test_start(daten))
            elif pfad == "/api/playlist_import":
                return _antwort(self, 200, playlist_import_m3u(daten.get("name"), daten.get("m3u")))
            elif pfad == "/api/link_deuten":      # Build 126: „ein Feld für alles"
                return _antwort(self, 200, links.link_deuten(daten.get("url") or ""))
            elif pfad == "/api/abo":
                return _antwort(self, 200, abo_aktion(daten))
            elif pfad == "/api/clip":
                return _antwort(self, 200, clip_erstellen(daten))
            elif pfad == "/api/clip_favorit":         # Build 144k: Favorit wählen (NUR_PC)
                return _antwort(self, 200, _clip_favorit_setzen(daten.get("id") or ""))
            elif pfad == "/api/untertitel_laden":
                threading.Thread(target=untertitel_nachladen, args=(daten.get("id") or "",), daemon=True).start()
            elif pfad == "/api/autotag":
                threading.Thread(target=autotag_lauf, args=(daten.get("keys"),), daemon=True).start()
            elif pfad == "/api/filme/sync":       # manueller Katalog-Abzug
                # Unter DERSELBEN Sperre wie der 6-h-Ticker. Ohne sie liefen zwei
                # Voll-Abzüge parallel gegen Renés Server — bei 4885 Titeln zehn
                # 1000er-Seiten gleichzeitig — und beide endeten mit
                # `fortschritt_nachreichen()`, das jede Meldung doppelt schickte.
                if not _filme_abzug_anstossen(von_hand=True):
                    return _antwort(self, 200, {"gestartet": False,
                                                "hinweis": "Ein Abzug läuft bereits."})
                return _antwort(self, 200, {"gestartet": True})
            elif pfad == "/api/filme/play":       # Jellyfin-Strom in den LOKALEN VLC
                strom = filme.stream_url(daten.get("id") or "", druck=True)   # JBs Druck
                if not strom:
                    return _antwort(self, 503, {"fehler": "Jellyfin nicht erreichbar "
                                                          "(Zugang/Netz pruefen)."})
                return _antwort(self, 200, vlc_kommando(
                    {"cmd": "play", "url": strom,
                     "key": "film:" + (daten.get("id") or ""),
                     "vol": daten.get("vol"),
                     "pos": daten.get("pos"),          # Weiterschauen ab Spot
                     "vollbild": True,                 # Filme = Kino (JB 05.08.)
                     # globale Sprach-Präferenz (Optionen → Wiedergabe-Standard);
                     # film:-Keys haben keine Titel-Ebene, global genügt.
                     "ton": (CFG.get("wiedergabe") or {}).get("ton")}))
            elif pfad == "/api/filme/merk":       # 🎞 Film-Watchlist an/aus (je Profil)
                return _antwort(self, 200, {"an": filme.merkliste_toggle(
                    daten.get("id") or "", self._geraet_profil())})
            # ---- Teilprojekt 3: Profile + Geräte ---------------------------
            elif pfad == "/api/geraet_anmelden":  # Pairing Schritt 1 (frei)
                return _antwort(self, 200, profil_geraete.geraet_anmelden(
                    daten.get("name") or "") or {"fehler": "Anmeldung gerade nicht möglich"})
            elif pfad == "/api/geraet_bestaetigen":   # NUR PC (Freigabe, NUR_PC)
                return _antwort(self, 200, {"ok": profil_geraete.geraet_bestaetigen(
                    daten.get("id") or "", daten.get("profil") or "standard")})
            elif pfad == "/api/geraet_entfernen":     # NUR PC (Widerruf, NUR_PC)
                return _antwort(self, 200, {"ok": profil_geraete.geraet_entfernen(
                    daten.get("id") or "")})
            elif pfad == "/api/profil_anlegen":
                p = profil_geraete.profil_anlegen(daten.get("name") or "",
                                                  daten.get("emoji") or "")
                return _antwort(self, 200, p or {"fehler": "Name fehlt"})
            elif pfad == "/api/filme/anfragen":   # Wunsch stellen (Teilprojekt 4)
                return _antwort(self, 200, filme.seerr_anfragen(
                    daten.get("tmdb") or 0, daten.get("typ") or "film"))
            elif pfad == "/api/live/play":        # Live-Kanal in den VLC
                # Nachtprüfung 06.08. (SSRF): die URL kommt NICHT vom Client,
                # sondern wird über die Kanal-Liste nachgeschlagen — gespielt
                # wird nur, was die kodinerds-Liste wirklich kennt.
                gewuenscht = daten.get("url") or ""
                if not any(k.get("url") == gewuenscht for k in live_tv.kanaele()):
                    return _antwort(self, 403, {"fehler": "unbekannter Kanal"})
                return _antwort(self, 200, vlc_kommando(
                    {"cmd": "play", "url": gewuenscht,
                     "key": "live:" + (daten.get("name") or ""),
                     "vol": daten.get("vol"), "vollbild": True}))
            elif pfad == "/api/filme/fortschritt":
                # Vor dem Senden merken: ein wartender Hüllen-Rückfall für diesen
                # Film schweigt dann (_film_stelle_melden, Nacharbeit Runde 3).
                _seiten_meldung_merken(str(daten.get("id") or ""))
                return _antwort(self, 200, {"ok": filme.fortschritt(
                    daten.get("id") or "", daten.get("position_s") or 0,
                    bool(daten.get("gesehen")))})
            else:
                return _antwort(self, 404, {"fehler": "unbekannt"})
            _antwort(self, 200, {"ok": True})
        except Exception as e:                       # noqa: BLE001
            _antwort(self, 500, {"fehler": _fehltext(e)})

    def _add(self, daten):
        qualitaet = daten.get("qualitaet") or CFG["standard_qualitaet"]
        ganze_liste = bool(daten.get("ganze_liste"))
        limit = daten.get("limit")                    # Mix-Wunsch-Anzahl (Build 98)
        ziel_pl = str(daten.get("ziel_playlist") or "")[:80]   # Entdeckt-Sammlung (Build 100)
        # Build 127 (JB-Regler): wie viele und von welchem Ende.
        try:
            menge = int(daten.get("menge") or 0) or None
        except (TypeError, ValueError):
            menge = None
        richtung = "alt" if daten.get("richtung") == "alt" else "neu"
        # v1.1.1 (Addon-Playlist-Pfeil, JB: „von was bis was"): Bereich prüfen —
        # >=1, bis>=von; Unsinn wird still zu „kein Bereich".
        def _ganzzahl(name):
            try:
                w = int(daten.get(name) or 0)
                return w if w >= 1 else None
            except (TypeError, ValueError):
                return None
        von, bis = _ganzzahl("von"), _ganzzahl("bis")
        if von and bis and bis < von:
            von, bis = bis, von
        urls = links.link_zeilen(daten.get("urls"))         # dieselbe Zerlegung wie im WLAN-Prüfer
        for url in urls:
            if not url.lower().startswith(("http://", "https://")):
                continue
            # Fund 06.08.: eine aus der EIGENEN Oberfläche gezogene Grafik
            # (http://127.0.0.1:8776/api/cover?…) landete als Pseudo-Download
            # in der Queue und fuhr sich fest. Der PC selbst (localhost, das
            # ganze 127.0.0.0/8, ::1, 0.0.0.0, jede Schreibweise davon, Namen,
            # die dorthin zeigen, die eigene LAN-Adresse) ist nie Download-Ziel.
            try:
                host = urlsplit(url).hostname
            except ValueError:
                continue
            if zeigt_auf_diesen_rechner(host):
                continue
            threading.Thread(target=aufloesen, args=(url, qualitaet, ganze_liste),
                             kwargs={"limit": limit, "ziel_playlist": ziel_pl,
                                     "menge": menge, "richtung": richtung,
                                     "von": von, "bis": bis}, daemon=True).start()

    def _action(self, daten):
        art = daten.get("art")
        # Nachtprüfung 06.08.: Explorer-Fenster öffnet nur der PC selbst —
        # eine LAN-Anfrage startet keine Prozesse auf JBs Rechner (Prüfer
        # _lan_action im WLAN-Tor, seit 25.09.2026 mit 403 statt still).
        if art == "ordner_offen":
            ordner_zeigen()
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
        zeigen = []                                   # F7: Explorer erst nach der Sperre
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
                zeigen.append(it.get("datei"))
        for pfad in zeigen:
            ordner_zeigen(pfad if (pfad and os.path.exists(pfad)) else None)
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
            pfad = os.path.join(ordner, land + ".conf")
            _vorher_sichern(pfad, content)            # S11: vorhandene .conf rückholbar daneben
            with open(pfad, "w", encoding="utf-8") as f:
                f.write(content)
            with _cfg_lock:
                CFG["geo_wireguard_ordner"] = ordner
                _cfg_speichern()
        except OSError as e:
            return {"fehler": str(e)}
        return {"ok": True, "ordner": ordner, "laender": geo.wireguard_laender(ordner)}

    def _geo_test_start(self, daten):
        """Geo-Test starten: probiert die Kette an einem geo-gesperrten Video und
        meldet je Methode Zugang ja/nein (Ergebnisse via /api/geo_status)."""
        if _geo_test.get("laeuft"):
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
        # Prüfen und Setzen in EINEM Schritt, bevor der Faden startet: vorher
        # setzte erst der Faden den Merker, zwei schnelle Klicks starteten zwei Tests.
        if not _zustand_starten(_geo_test, _geo_test_lock, stand=time.time(), url=url, titel=titel,
                                info="", ergebnisse=[]):
            return {"ok": True, "laeuft": True}
        threading.Thread(target=geo_test_lauf, args=(url, titel, laender or []), daemon=True).start()
        return {"ok": True, "laeuft": True}

    def _config(self, daten):
        erlaubt_browser = ("firefox", "chrome", "edge", "keine")
        with _cfg_lock:
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
            if isinstance(daten.get("name_schema"), list):    # Namens-Baukasten (Build 113)
                CFG["name_schema"] = [str(b) for b in daten["name_schema"]
                                      if str(b) in NAME_BAUSTEINE][:len(NAME_BAUSTEINE)]
            if isinstance(daten.get("auto_umbenennen"), bool):
                CFG["auto_umbenennen"] = daten["auto_umbenennen"]
            if isinstance(daten.get("metadaten"), bool):
                CFG["metadaten"] = daten["metadaten"]
            if isinstance(daten.get("fehler_ausblenden_min"), (int, float)):
                CFG["fehler_ausblenden_min"] = max(0, min(120, int(daten["fehler_ausblenden_min"])))
            if daten.get("sponsorblock") in ("", "sponsor", "alle"):
                CFG["sponsorblock"] = daten["sponsorblock"]
            if isinstance(daten.get("untertitel"), bool):
                CFG["untertitel"] = daten["untertitel"]
            if isinstance(daten.get("untertitel_sprachen"), list):   # JB Punkt 6: Sprachwahl
                CFG["untertitel_sprachen"] = [str(s)[:12] for s
                                              in daten["untertitel_sprachen"][:10]]
            if isinstance(daten.get("auto_update"), bool):
                CFG["auto_update"] = daten["auto_update"]
            if isinstance(daten.get("fernsteuerung"), bool):
                CFG["fernsteuerung"] = daten["fernsteuerung"]
                if daten["fernsteuerung"] and not CFG.get("fernsteuerung_code"):
                    CFG["fernsteuerung_code"] = neuer_fernsteuerungs_code()   # Code beim Aktivieren erzeugen
            if isinstance(daten.get("parallel"), int) and 1 <= daten["parallel"] <= 3:
                CFG["parallel"] = daten["parallel"]
                _worker_start(CFG["parallel"])
            _cfg_speichern()

    def _biblio(self, daten):
        key = daten.get("id") or ""
        art = daten.get("art")
        if art == "herz":                            # ❤ Lieblingssong umschalten (JB 05.08.)
            return herz_umschalten(key)
        # Nachtprüfung 06.08.: alles Verändernde (löschen/vergessen) und
        # alles, was Prozesse auf JBs PC startet (extern/ordner), bleibt dem
        # PC selbst vorbehalten (Prüfer _lan_biblio im WLAN-Tor: aus dem WLAN
        # gehen nur ❤ und „neuladen“, seit 25.09.2026 mit 403 statt still).
        # Der Zweig art:'bulk' (Mehrfachauswahl) ist entfallen (Gesamtprüfung
        # Gruppe 7): Seine Oberfläche gab es nicht mehr, er trug aber eine
        # Lösch-Operation. Rückweg: git-Historie.
        if art == "ordner":                          # Datei im Explorer zeigen (markiert)
            e = _geladen.get(key)                    # F7: Ordnerlauf + Explorer ohne Sperre
            if not e:
                return
            vid = key.split("|")[0]
            pfad = e.get("pfad")
            if not (pfad and os.path.exists(pfad)):
                pfad = _datei_aus(_datei_index().get(vid), key.partition("|")[2])
            ordner_zeigen(pfad if (pfad and os.path.exists(pfad)) else None)
            return
        if art == "extern":                          # in VLC / Standardplayer öffnen
            pfad = _pfad_zu_key(key)                 # F7: Ordnerlauf + Player-Start ohne Sperre
            if pfad:
                extern_abspielen(pfad)
            return
        if art == "loeschen":                        # Datei in den Papierkorb + aus Liste
            e = _geladen.get(key)                    # F7: Ordnerlauf + Papierkorb ohne Sperre
            if not e:
                return
            _datei_rueckholbar_entfernen(key)
            with _io_lock:
                _aus_playlists_nehmen(key)
                if _geladen.get(key) is e:           # derweil frisch geladen? Der Eintrag bleibt
                    _geladen.pop(key, None)
                _geladen_speichern()
                _json_speichern(PLAYLIST_PFAD, _playlists)
            return
        with _io_lock:
            e = _geladen.get(key)
            if not e:
                return
            if art == "neuladen":                    # verschobenen/gelöschten Titel neu holen
                vid = key.split("|")[0]
                url = e.get("url") or (f"https://www.youtube.com/watch?v={vid}"
                                       if links._plausible_id(vid) else "")
                quali = e.get("qualitaet") or (key.split("|", 1)[1] if "|" in key else "beste")
                if url:
                    threading.Thread(target=aufloesen, args=(url, quali), daemon=True).start()
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
            _geladen_speichern()


_worker_faeden = []
_worker_lock = threading.Lock()


def _worker_soll():
    return max(1, min(3, int(CFG.get("parallel", 1))))


def _worker_start(soll):
    """Worker nur hochfahren (laufende Threads sanft auslaufen zu lassen wäre
    komplex — überzählige Worker finden schlicht keine Arbeit mehr).
    Gezählt werden nur LEBENDE Fäden (Gesamtprüfung F1): vorher zählte ein
    Zähler auch gestorbene mit, ein toter Worker wurde also nie ersetzt. Der
    Ticker ruft das alle 5 s mit auf."""
    with _worker_lock:
        _worker_faeden[:] = [f for f in _worker_faeden if f.is_alive()]
        while len(_worker_faeden) < soll:
            f = threading.Thread(target=worker_schleife, daemon=True)
            f.start()
            _worker_faeden.append(f)


# ---- Protokoll-Datei (Gesamtprüfung Gruppe 7, Plan Abschnitt 6 Punkt 1) ------
# Unter pythonw (SyncYouTube.bat, Hülle) und in der exe gibt es keine Konsole:
# _sag lief dort ins Leere, jeder Ticker-Fehler ging verloren. Jetzt schreibt
# _sag zusätzlich in yt_protokoll.log im Datenverzeichnis, höchstens 1 MB, dazu
# drei Vorgänger (.1 bis .3, das Älteste fällt weg). Eingerichtet in main(); beim
# blossen Import (Tests, Werkzeuge) entsteht keine Datei.
PROTOKOLL_LOG = os.path.join(DATEN_DIR, "yt_protokoll.log")
PROTOKOLL_GROESSE = 1_000_000
PROTOKOLL_VORGAENGER = 3
_protokoll = logging.getLogger("SyncYouTube")
_protokoll.setLevel(logging.INFO)
_protokoll.propagate = False                        # nicht an den Wurzel-Logger (kein stderr-Rückfall)
_protokoll.addHandler(logging.NullHandler())


def protokoll_einrichten(pfad=None):
    """Die Protokoll-Datei anhängen und den Handler liefern; ein früherer
    Datei-Handler wird dabei ersetzt (nie doppelt schreiben)."""
    for alt in [h for h in _protokoll.handlers if isinstance(h, logging.FileHandler)]:
        _protokoll.removeHandler(alt)
        alt.close()
    handler = logging.handlers.RotatingFileHandler(
        pfad or PROTOKOLL_LOG, maxBytes=PROTOKOLL_GROESSE, backupCount=PROTOKOLL_VORGAENGER,
        encoding="utf-8", delay=True)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    _protokoll.addHandler(handler)
    return handler


def _sag(text, stufe=logging.INFO):
    """Konsole (wo es eine gibt, unter pythonw nicht) und Protokoll-Datei."""
    try:
        if sys.stdout is not None:
            print(text)
    except (OSError, ValueError, AttributeError):
        pass
    try:
        _protokoll.log(stufe, text)
    except Exception:                                # noqa: BLE001 — Protokoll ist nie ein Grund zu scheitern
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
            # Früher meldete JEDER Ausgang „Schon aktuell“ — auch „kein Netz“ und
            # „Release ohne exe“. Solange das Update Opt-in war, sah das nur, wer
            # selbst nachschaute. Als Vorgabe wäre ein dauerhaft kaputter
            # Update-Weg von einem gesunden nicht zu unterscheiden.
            grund = info.get("grund", "aktuell")
            if grund == "offline":
                melde("GitHub war nicht erreichbar — nächster Versuch später.")
            elif grund == "kein-asset":
                melde("Das neueste Release enthält keine passende exe — nichts getauscht.")
            else:
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
    """Auto-Update (Vorgabe AN seit 08.09.2026): kurz nach Start, danach täglich.

    NUR im Leerlauf. Der Tausch beendet den Prozess hart
    (`update.apply_exe_update` → `os._exit(0)`); solange die Entscheidung
    Opt-in war, traf das nur, wer sie selbst eingeschaltet hatte. Als Vorgabe
    träfe es jeden, auch mitten in einem großen Download. Die Warteschlange
    überlebt zwar (beim Start werden „läuft“/„prüft“ wieder zu „wartend“ und
    yt-dlp setzt an der .part-Datei fort), aber ein Abbruch ohne Not bleibt
    ein Abbruch. Ist etwas in Arbeit, wird der Versuch um eine halbe Stunde
    verschoben — kein neuer Zeitplan, derselbe Faden schläft nur kürzer.
    „Leerlauf“ heißt dasselbe wie beim Selbst-Neustart (`_code_leerlauf`, F14):
    kein Download, keine Auflösung, keine Wiedergabe im Browser oder am VLC."""
    time.sleep(90)
    while True:
        wartezeit = 24 * 3600
        if CFG.get("auto_update") and update.frozen_exe():
            if not _code_leerlauf():
                wartezeit = 1800                     # beschäftigt — später nochmal
            else:
                try:
                    update_lauf(_tray_ref[0] if _tray_ref else None)
                except Exception:                    # noqa: BLE001
                    pass
        time.sleep(wartezeit)


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
        ordner_zeigen()

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


def _kennung_log(text):
    """Konsole, Protokoll (Stufe WARNING) und dauerhafter Fehlerkanal
    (yt_fehler.jsonl). windows_kennung meldet nur Probleme."""
    _sag(text, logging.WARNING)
    fehler_merken("", text, "kennung")


def main():
    protokoll_einrichten()                            # als Erstes: ab hier landet jede Meldung in der Datei
    # Windows-Kennung ZUERST, vor jedem Fenster (Microsoft: „before the application
    # presents any UI"). Ohne sie ordnet Windows den pythonw-Prozess der Verknüpfung
    # „IDLE (Python 3.14)" zu (Befund 23.09.). JB 24.09.2026: „Kennung + Startmenü-Eintrag".
    windows_kennung.setze_kennung(log=_kennung_log)
    sys.path.insert(0, SCRIPT_DIR)
    globals()["_START_SIGNATUR"] = _quell_signatur()  # Build 144m: Code-Stand beim Start merken
    n = wiedergabe_sub_altlast_raeumen()              # einmalig (JB 05.08., s. Docstring)
    if n:
        _sag(f"Untertitel-Altlast geräumt: {n} Je-Titel-Regeln → wiedergabe_sub_altlast.json")
    if TESTMODUS:
        # Probe: nichts öffnet sich, nichts bleibt zurück außer dem Probenordner.
        for flag in ("--no-browser", "--no-tray"):
            if flag not in sys.argv:
                sys.argv.append(flag)
        _sag(f"TESTMODUS — alle Daten liegen unter {DATEN_DIR} (Port {CFG.get('port')}). "
             "JBs echte Ordner werden nicht angefasst.")
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
    # Erst hier, hinter dem Einzel-Instanz-Riegel: eine zweite Instanz, die sich
    # gleich wieder beendet, darf die config.json des laufenden Programms nicht
    # anfassen (JB-Regel: geteilter Zustand, zwei Fragen).
    for schluessel, alt, neu in vorgaben_umstellung_festschreiben():
        _sag(f"Neue Vorgabe übernommen: {schluessel} {alt} → {neu} "
             f"(alter Stand liegt als config_vor_stand{VORGABEN_STAND}.json daneben)")
    auffaellig = auffaellige_schluessel()            # S3: nur melden, nie umschreiben
    if auffaellig:
        _sag(f"Hinweis: {len(auffaellig)} Bibliotheks-Schlüssel mit Sonderzeichen "
             f"(bleiben unverändert): {', '.join(repr(k) for k in auffaellig[:5])}")
    if not TESTMODUS:
        # Startmenü-Eintrag „SyncYouTube" mit derselben Kennung: darüber findet Windows
        # Namen und Symbol. Im Hintergrund, idempotent; eine fremde Verknüpfung
        # gleichen Namens bleibt unberührt. Eine Probe legt nie etwas an.
        windows_kennung.startmenue_eintrag(faden=True, log=_kennung_log)
    try:
        # Windows-Medienanmeldung des VLC-Motors: hier nur die Brücke — Fenster
        # und Anmeldung entstehen erst beim ersten Abspielen im VLC (lazy).
        _smtc_einrichten()
    except Exception as e:                           # noqa: BLE001 — nie den Start reißen
        _sag(f"Windows-Medienanmeldung nicht eingerichtet: {e}", logging.WARNING)
    _worker_start(_worker_soll())
    threading.Thread(target=ticker_schleife, daemon=True).start()
    threading.Thread(target=technik_backfill, daemon=True).start()   # Codecs für Alt-Dateien
    threading.Thread(target=titel_abgleich, daemon=True).start()     # Build 141: Anzeige folgt dem Dateinamen
    threading.Thread(target=_abos_hintergrund, daemon=True).start()  # Abos auf neue Videos prüfen
    threading.Thread(target=_einsortieren_hintergrund, daemon=True).start()  # verschobene Dateien zurücksortieren
    update.cleanup_old_exe()                                          # Reste früherer Selbst-Updates
    threading.Thread(target=_update_hintergrund, daemon=True).start()  # Auto-Update (Vorgabe AN, nur im Leerlauf)
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
