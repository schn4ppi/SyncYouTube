# SyncYouTube

Lokaler YouTube-Downloader **und** vollwertiger Musik-/Video-Player mit Bibliothek —
eine einzige Web-Oberfläche auf `http://127.0.0.1:8776`, komplett offline auf dem eigenen PC
(einzige Außenverbindungen: YouTube selbst, MusicBrainz fürs Tagging, die SponsorBlock-Datenbank
und — nur auf Wunsch — der Update-Check gegen dieses GitHub-Repo).

## Features

**Downloads**
- Warteschlange ohne Limit, Qualität je Eintrag (Beste/4K/1440p/1080p/720p/MP3), Playlist-Auflösung
- Auto-Retry mit Backoff + Resume (setzt nach Abbruch/Neustart genau dort fort), Netzwerk-Timeout-Schutz
- Premium/altersbeschränkt über Browser-Cookies (Firefox/Chrome/Edge)
- Dubletten-Erkennung über die Video-ID, „Schon geladen“-Datenbank
- SponsorBlock (Werbung/Intros aus der Datei schneiden), Metadaten + Thumbnail als Cover
- Kanal-/Playlist-**Abos** (holt nur Neues), Ausschnitt/Clip (von–bis, ohne Längenlimit)
- Gestufte Geo-Umgehung: Header-Trick → eigene Proxys → Gratis-Proxys → VPN (Nord/Windscribe/WireGuard)
- Downloads-Ordner heilt sich selbst: von Hand verschobene Dateien wandern automatisch
  zurück nach `MP3` / `4K+` / `Video` (Unklares nach `Sonstiges`)

**Player**
- Steuerleiste **auf dem Video/Cover** (YouTube-Stil): Spulen, Transport, Untertitel, Clip,
  Tempo, Lautstärke, YouTube-Knopf, Vollbild — blendet bei Maus-Ruhe aus
- **Zufall und Wiederholen als getrennte Schalter** (Spotify-Muster, eigene SVG-Icons);
  Einzeltitel zu Ende → automatisch der nächste Bibliotheks-Titel (Autoplay)
- 8 Visualizer (Balken/Spiegel/Welle/Oszilloskop/Radial/Matrix/Spektrogramm), Canvas-Cover-Hintergrund
- Übergänge: Gapless / Crossfade (0–12 s) / Automix · Equalizer + Lautstärke-Angleich
- Untertitel → **Karaoke** (Original-Sprache, japanisch automatisch als **Romaji**) → Transkript,
  fehlende Untertitel lädt die App still von YouTube nach
- YouTube-Kapitel als Sprungmarken, Sleep-Timer, 📻 Endlos-Radio
- Rechtsklick-Menü mit Windows-Ausklapp-Untermenüs, Klick auf die Fläche = Pause, Media-Tasten

**Bibliothek**
- Kacheln / **Alben** (Auto-Tagging via MusicBrainz) / Liste, konfigurierbare Spalten
- Titel per Maus **in die Player-Playlist ziehen**; Playlist als eigenes, andockbares Fenster
- Playlists (öffnen, umsortieren, .m3u-Import/-Export, Geräte-Sync kopieren/spiegeln)
- Smart-Playlists (Regeln), Meistgespielt/Zuletzt, Dublettenfinder, Batch-Tag-Editor
- Rechtsklick-Kontextmenüs wie im Explorer, Mehrfachauswahl (Strg/Shift), Papierkorb statt Löschen

**Oberfläche**
- Fenster-System mit Tabs: Tab herausziehen (füllt die freie Lücke), Tab auf ein anderes
  Fenster ziehen = dort andocken, transluzente Drag-Vorschau
- ✏-Layout-Modus: verschieben mit Platzhalter-Vorschau, 8 Größen-Griffe, Fenster
  überlappen sich nie; Layouts speichern/benennen, ↩ Verlust-Schutz, 5 Looks, Mini-Player
- Sticky Command-Bar: Link einfügen → Download, Live-Warteschlange (Klick = Pause, ✖ = abbrechen),
  großer Mini-Player mit Spulleiste, Zwischenablage-/Einfügen-Erkennung
- Mausrad-Kippen = Ansicht-Verlauf zurück/vor, Link ins Fenster ziehen = Download, ?-Legende

**Extras**
- 📱 Handy-Fernsteuerung im Heim-WLAN (opt-in, Zugangscode, Gerät wählbar wie bei Spotify Connect)
- Browser-Erweiterung für Firefox/Chrome/Edge (`System/browser-addon/`, ein Code; die signierte
  Firefox-`.xpi` liegt beim Release und ist über das Tray-Menü/die Einstellungen installierbar)
- **Selbst-Update** (opt-in, Standard aus): die exe prüft täglich dieses Repo, lädt verifiziert
  (SHA256-Abgleich gegen das `.sha256`-Asset) und tauscht sich ohne Adminrechte selbst

## Voraussetzungen / Start (aus dem Quellcode)

1. **Python 3.12+** und die Pakete:
   ```
   pip install "yt-dlp[default]" pykakasi pystray pillow
   ```
2. **`System/bin/`-Ordner** mit `ffmpeg.exe`, `ffprobe.exe` und `deno.exe`
   (Deno ist Pflicht — ohne JS-Runtime liefert YouTube seit 2026 „No video formats found“).
   Die Binärdateien sind nicht im Repo; von den offiziellen Seiten laden (ffmpeg.org, deno.com).
3. Start: `python System/youtube_app.py` — oder unter Windows die `SyncYouTube.bat`
   (Pfad zur eigenen Python-Umgebung anpassen). Oberfläche: `http://127.0.0.1:8776`.

Tests: `python System/tests/test_youtube.py` (läuft ohne Zusatzpakete, kein Netz).

## Aufbau

| Datei | Zweck |
|---|---|
| `System/youtube_app.py` | Server, Warteschlange, Download-Logik, Bibliothek, Playlists, Tray |
| `System/oberflaeche.py` | die komplette PC-Oberfläche (eine Datei, wird heiß nachgeladen) |
| `System/handy.py` | Touch-Oberfläche der Fernsteuerung (`/m`) |
| `System/geo.py` / `System/vpn.py` | gestufte Geo-Umgehung / NordVPN-Steuerung |
| `System/update.py` | Selbst-Update der exe (Repo-Pin, SHA256-Verifikation, Rollback) |
| `System/browser-addon/` | universelle Browser-Erweiterung + Build-/Signier-Skripte |
| `System/_ARCHITEKTUR.md` | Architektur & Fahrplan |

Konfiguration und alle Nutzerdaten (`config.json`, `geladen_log.json`, `playlists.json`,
`warteschlange.json`, `abos.json`, `Downloads/`) entstehen zur Laufzeit und bleiben lokal —
sie gehören bewusst **nicht** ins Repo.

## Download (Windows, ohne Python)

Unter **Releases** liegt die all-inclusive `SyncYouTube.exe` (ffmpeg/ffprobe/deno eingebaut):
herunterladen, starten, fertig. Daneben das `.sha256`-Asset zum Prüfen und die signierte
Firefox-Erweiterung. Updates holt die exe auf Wunsch selbst (Einstellungen → „Selbst-Update“,
oder Tray → „Nach Updates suchen…“).

## Lizenz

**GPL-3.0-or-later** (siehe [LICENSE](LICENSE)). Enthaltene/beigelegte Komponenten:
[yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense),
[pykakasi](https://codeberg.org/miurahr/pykakasi) (GPL-3.0),
[FFmpeg](https://ffmpeg.org) (GPL-Build, Quellcode über ffmpeg.org),
[Deno](https://deno.com) (MIT), pystray/Pillow (LGPL/MIT-HPND).
