# -*- coding: utf-8 -*-
"""Links deuten, rein aus der Adresse (Gesamtprüfung Y2, 25.09.2026).

Was ein Link ist (Video, Playlist, Mix, Kanal), welche Kanal-Adresse yt-dlp
bekommt, welche Video-Id darin steckt und ob er genau auf einen YouTube-Host
zeigt. Alles ohne Netz, ohne Datei und ohne Zustand: reine Funktionen, bis
auf die Zeile wortgleich aus youtube_app.py hierher verschoben.

Einbahn wie bei filme und geo: dieses Modul importiert youtube_app nie. Die
App ruft `links.X`; `youtube_app.X` bleibt als Verweis erreichbar (Tests,
Werkzeuge). Ein Test, der etwas davon ersetzt, ersetzt es HIER
(`monkeypatch.setattr(links, ...)`): ein Ersatz an `youtube_app.X` träfe
keinen Aufrufer. Das prüft tests/test_struktur_module.py.
"""
import re
from urllib.parse import parse_qs, urlparse, urlsplit


def ist_einzelvideo(url):
    """watch?v=…&list=… heißt: JB will DIESES Video, nicht die ganze Liste.
    Nur reine Playlist-Links (/playlist?list=…) werden komplett übernommen."""
    try:
        p = urlparse(url)
        qs = parse_qs(p.query)
        return bool(qs.get("v")) or "/playlist" not in p.path
    except ValueError:
        return True


# Kanal-Links, EINE Regel für link_deuten und _kanal_url (Gesamtprüfung Gruppe 7,
# vorher wortgleich zweimal): Eine Unterseite ist eindeutig und bleibt, wie sie
# ist; die blosse Kanal-Wurzel ist mehrdeutig (laden oder abonnieren?).
_KANAL_UNTERSEITEN = ("/videos", "/streams", "/shorts", "/playlists", "/featured", "/live")
_KANAL_WURZEL = re.compile(r"^/(@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)$")


def link_deuten(url):
    """Was will JB mit diesem Link? (Build 126 — „ein Feld für alles")

    Bisher gab es drei zu ähnliche Knöpfe: ⬇ Download, 📺 ganzer Kanal,
    📡 Abonnieren. JBs Ziel: EIN Feld, Enter genügt, die App erkennt den Typ
    selbst — und fragt NUR, wo die Absicht wirklich offen ist.

    Wirklich offen ist genau zweierlei, alles andere ist ableitbar:
      * ein blosser Kanal-Link — laden oder abonnieren?
      * watch?v=…&list=… — dieses eine Video oder die ganze Liste?
    Mixe (list=RD…) haben ihre eigene Anzahl-Frage (Build 98), die bleibt.

    Rein aus der URL, ohne Netz: schnell, testbar, funktioniert offline.
    Rückgabe: {typ, eindeutig, frage, optionen[{id,text,standard}]}
    """
    roh = (url or "").strip()
    if not roh.lower().startswith(("http://", "https://")):
        return {"typ": "unbekannt", "eindeutig": False, "frage": "", "optionen": []}
    try:
        p = urlparse(roh)
        qs = parse_qs(p.query)
    except ValueError:
        return {"typ": "unbekannt", "eindeutig": False, "frage": "", "optionen": []}

    eindeutig = {"eindeutig": True, "frage": "", "optionen": []}
    host = (p.netloc or "").lower()
    if not any(h in host for h in ("youtube.com", "youtu.be")):
        return dict(typ="video", **eindeutig)         # fremde Seite: normaler Download

    if _ist_mix(roh):                                 # endlos, eigene Anzahl-Frage
        return dict(typ="mix", **eindeutig)

    pfad = (p.path or "").rstrip("/")
    low = pfad.lower()
    if qs.get("v"):
        if qs.get("list"):                            # MEHRDEUTIG: eines oder alle?
            return {"typ": "video_in_playlist", "eindeutig": False,
                    "frage": "Dieser Link zeigt ein Video AUS einer Playlist.",
                    "optionen": [{"id": "eines", "text": "Nur dieses Video", "standard": True},
                                 {"id": "alle", "text": "Die ganze Playlist", "standard": False}]}
        return dict(typ="video", **eindeutig)
    if "/playlist" in low:
        return dict(typ="playlist", **eindeutig)
    if "youtu.be" in host or low.startswith("/shorts/") or "/watch" in low:
        return dict(typ="video", **eindeutig)
    if low.endswith(_KANAL_UNTERSEITEN):
        return dict(typ="kanal", **eindeutig)         # Unterseite = klar: laden
    if _KANAL_WURZEL.match(pfad):
        return {"typ": "kanal", "eindeutig": False,   # MEHRDEUTIG: laden oder abo?
                "frage": "Das ist ein Kanal.",
                "optionen": [{"id": "abo", "text": "Abonnieren (neue Folgen kommen von allein)",
                              "standard": True},
                             {"id": "laden", "text": "Alle Videos jetzt laden", "standard": False}]}
    return dict(typ="video", **eindeutig)


def _kanal_url(url):
    """Kanal-Link auf die Video-Liste normalisieren, damit yt-dlp ALLE Videos
    listet — ein blosses /@name liefert sonst nur die Kanal-Reiter (belegt:
    /@MrBeast -> 2 Reiter, /@MrBeast/videos -> die Videos). Playlist-/Watch-/
    schon-Unterseiten-Links bleiben unveraendert."""
    try:
        p = urlparse(url)
    except ValueError:
        return url
    if "youtube.com" not in (p.netloc or "").lower():
        return url
    path = (p.path or "").rstrip("/")
    low = path.lower()
    if parse_qs(p.query).get("v") or "/playlist" in low or "/watch" in low:
        return url
    if low.endswith(_KANAL_UNTERSEITEN):
        return url
    if _KANAL_WURZEL.match(path):
        return "https://www.youtube.com" + path + "/videos"
    return url


def _liste_zuschneiden(eintraege, menge, richtung="neu"):
    """Auswahl aus einer aufgelösten Liste (Build 127, JB-Regler).

    yt-dlp liefert Kanäle und Playlists NEUESTE ZUERST. „Die 20 ältesten"
    heißt also: vom anderen Ende nehmen. Danach wird chronologisch geladen
    (älteste zuerst) — dieselbe Logik wie beim Abo-Backkatalog, damit eine
    Serie in der Reihenfolge ankommt, in der man sie ansieht.
    Ohne Menge bleibt alles unangetastet (Verhalten wie bisher).
    """
    liste = [e for e in (eintraege or []) if e]
    if not menge or menge <= 0:
        return liste
    if richtung == "alt":
        return list(reversed(liste))[:menge]
    return liste[:menge]


def _video_id(url):
    m = re.search(r"[?&]v=([\w-]{6,})", url) or re.search(r"youtu\.be/([\w-]{6,})", url)
    return m.group(1) if m else url


def _plausible_id(vid):
    """Sieht das nach einer echten YouTube-Id aus? Build 123 (JB-Fund:
    „denke er verwechselt lokal… mit einem Link"): unsere EIGENEN Kunst-Ids
    für Ordner-Funde („lokal-…") passten auf das Muster — importierte Dateien
    bekamen dadurch eine erfundene YouTube-Adresse angehängt."""
    vid = vid or ""
    if vid.startswith("lokal-"):
        return False
    return bool(re.fullmatch(r"[\w-]{6,20}", vid))


def _ist_mix(url):
    """YouTube-Mix/Radio? (list=RD…/RDMM/RDCLAK — dynamisch, endlos, an ein
    Start-Video gebunden; UL = alter Uploads-Mix)."""
    return bool(re.search(r"[?&]list=(RD|UL)", url or ""))


def _mix_limit(wunsch):
    """Wunsch-Anzahl fuer einen Mix: 1..500, sonst Default 50 (Build 98, JB:
    einstellbar; „alle" gibt es bei Mixen bewusst NICHT — sie sind endlos und
    nicht-deterministisch, JB mass 1877 vs 563 fuer denselben Mix)."""
    try:
        n = int(wunsch)
    except (TypeError, ValueError):
        return 50
    return 50 if n <= 0 else min(n, 500)


# Links aus dem WLAN (JB-Entscheid 7a Punkt 7, 25.09.2026; S12, S19): nur genau
# EIN YouTube-Link. Der Host wird exakt verglichen, nie als Teilzeichenkette
# (youtube.com.angreifer.de, …/?u=youtube.com). Ein Zeilenumbruch oder Leerraum
# im Link hieße: mehrere Adressen in einem Feld — `_add` teilt an Zeilen. Vom PC
# bleibt jeder http(s)-Link erlaubt, der nicht auf den PC selbst zeigt.
# Abnahme 25.09.2026: Prüfer und Router zerlegen das Feld mit DERSELBEN Funktion
# (`link_zeilen`). Vorher prüfte `_lan_add` das ganze Feld als einen Link, und
# `_add` teilte mit `splitlines()` auch an U+2028, U+2029 und U+0085: ein
# YouTube-Link mit angehängtem Trenner brachte einen zweiten, beliebigen Link
# in die Warteschlange.
YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
                           "youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com"})
_KEIN_LINK_ZEICHEN = frozenset({"Zl", "Zp", "Cc", "Cf"})   # Trenner, Steuer- und Formatzeichen


def link_zeilen(roh):
    """Das Link-Feld von /api/add als Liste einzelner Links, genau so, wie
    `_add` es einreiht (jede nicht leere Zeile, ohne Rand-Leerraum)."""
    return [u.strip() for u in (roh or "").splitlines() if u.strip()]


def ist_youtube_link(url):
    """Genau ein http(s)-Link auf einen YouTube-Host (exakt), ohne Leerraum,
    Zeilentrenner, Steuer- oder Formatzeichen, Backslash, Anmeldedaten oder
    fremden Port."""
    import unicodedata
    if not isinstance(url, str) or not url:
        return False
    if any(ord(z) < 0x21 or z in "\\\x7f" or z.isspace()
           or unicodedata.category(z) in _KEIN_LINK_ZEICHEN for z in url):
        return False
    try:
        teile = urlsplit(url)
        port = teile.port
    except ValueError:
        return False
    if teile.scheme.lower() not in ("http", "https") or port not in (None, 80, 443):
        return False
    if teile.username is not None or teile.password is not None:
        return False
    return (teile.hostname or "").rstrip(".") in YOUTUBE_HOSTS
