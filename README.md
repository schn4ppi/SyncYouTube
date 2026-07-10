# SyncYouTube

Lokaler YouTube-Downloader **und** vollwertiger Musik-/Video-Player mit Bibliothek —
eine einzige Web-Oberfläche auf `http://127.0.0.1:8776`, komplett offline auf dem eigenen PC
(einzige Außenverbindung: YouTube selbst, MusicBrainz fürs Tagging und die SponsorBlock-Datenbank).

## Features

**Downloads**
- Warteschlange ohne Limit, Qualität je Eintrag (Beste/4K/1440p/1080p/720p/MP3), Playlists-Auflösung
- Auto-Retry mit Backoff + Resume (setzt nach Abbruch/Neustart genau dort fort)
- Premium/altersbeschränkt über Browser-Cookies (Firefox/Chrome/Edge)
- Dubletten-Erkennung über die Video-ID, „Schon geladen"-Datenbank
- SponsorBlock (Werbung/Intros aus der Datei schneiden), Metadaten + Thumbnail als Cover
- Kanal-/Playlist-**Abos** (holt nur Neues), Ausschnitt/Clip (von–bis, ohne Längenlimit)
- Gestufte Geo-Umgehung: Header-Trick → eigene Proxys → Gratis-Proxys → VPN (Nord/Windscribe/WireGuard)

**Player**
- 8 Visualizer (Balken/Spiegel/Welle/Oszilloskop/Radial/Matrix/Spektrogramm), Canvas-Cover-Hintergrund
- Übergänge: Gapless / Crossfade (0–12 s) / Automix (hört aufs Outro) · Equalizer + Lautstärke-Angleich
- Untertitel → **Karaoke** (Original-Sprache, japanisch automatisch als **Romaji**) → Transkript
- YouTube-Kapitel als Sprungmarken, Abspielgeschwindigkeit, Sleep-Timer, 📻 Endlos-Radio
- Rechtsklick-Menü im Player, Klick auf die Fläche = Pause, Media-Tasten

**Bibliothek**
- Kacheln / **Alben** (Auto-Tagging via MusicBrainz) / Liste, konfigurierbare Spalten
- Playlists (öffnen, per Maus umsortieren, .m3u-Import/-Export, Geräte-Sync kopieren/spiegeln)
- Smart-Playlists (Regeln), Meistgespielt/Zuletzt, Dublettenfinder, Batch-Tag-Editor
- Rechtsklick-Kontextmenüs wie im Explorer, Mehrfachauswahl (Strg/Shift), Papierkorb statt Löschen

**Oberfläche**
- Bewegliche, andockbare Fenster mit speicherbaren Layouts, 5 Looks (inkl. Hacker-Grün), Mini-Player
- Sticky Command-Bar: Link einfügen → Download, Live-Warteschlange, Now-Playing, Zwischenablage-Wächter
- Mausrad-Kippen = Ansicht-Verlauf zurück/vor, Link ins Fenster ziehen = Download, ?-Legende

**Extras**
- 📱 Handy-Fernsteuerung im Heim-WLAN (opt-in, Zugangscode, Gerät wählbar wie bei Spotify Connect)
- Browser-Erweiterung für Firefox/Chrome/Edge (`browser-addon/`, ein Code, `build.py` baut Store-Pakete)

## Voraussetzungen / Start

1. **Python 3.12+** und die Pakete:
   ```
   pip install "yt-dlp[default]" pykakasi pystray pillow
   ```
2. **`bin/`-Ordner** neben `youtube_app.py` mit `ffmpeg.exe`, `ffprobe.exe` und `deno.exe`
   (Deno ist Pflicht — ohne JS-Runtime liefert YouTube seit 2026 „No video formats found").
   Die Binärdateien sind nicht im Repo; von den offiziellen Seiten laden (ffmpeg.org, deno.com).
3. Start: `python youtube_app.py` — oder unter Windows die `YouTube-Downloader.bat`
   (Pfad zur eigenen Python-Umgebung anpassen). Oberfläche: `http://127.0.0.1:8776`.

Tests: `python tests/test_youtube.py` (läuft ohne Zusatzpakete, kein Netz).

## Aufbau

| Datei | Zweck |
|---|---|
| `youtube_app.py` | Server, Warteschlange, Download-Logik, Bibliothek, Playlists, Tray |
| `oberflaeche.py` | die komplette PC-Oberfläche (eine Datei, wird heiß nachgeladen) |
| `handy.py` | Touch-Oberfläche der Fernsteuerung (`/m`) |
| `geo.py` / `vpn.py` | gestufte Geo-Umgehung / NordVPN-Steuerung |
| `browser-addon/` | universelle Browser-Erweiterung + Build-Skript |
| `_ARCHITEKTUR.md` | Architektur & Fahrplan |

Konfiguration und alle Nutzerdaten (`config.json`, `geladen_log.json`, `playlists.json`,
`warteschlange.json`, `abos.json`, `Downloads/`) entstehen zur Laufzeit und bleiben lokal —
sie gehören bewusst **nicht** ins Repo.
