# YouTube-Downloader — Architektur & Aufräum-Fahrplan

Kurzüberblick, damit die „Ordnung" nachvollziehbar bleibt und der Umbau
Schritt für Schritt läuft (kein Blind-Refactor an einer produktiv genutzten App).

## Module & Schichtung

```
youtube_app.py        Herzstück: Warteschlange, Worker, HTTP-Server, Download-
                      Logik, „Schon-geladen"-DB, Bibliothek, Playlists, Tray, main()
   │  importiert
   ▼
geo.py                Gestufte Geo-Umgehung (Header-Trick → eigene Proxys →
                      Gratis-Proxys → VPN-Adapter). Erkennt/parst Geo-Fehler.
   │  importiert
   ▼
vpn.py                Nur NordVPN-Steuerung (CLI + Insights-Status).

oberflaeche.py        Gesamte PC-Oberfläche (HTML/CSS/JS als ein String).
                      Wird bei jedem Seitenaufruf heiß nachgeladen (importlib.reload).
handy.py              Schlanke Touch-Oberfläche der Handy-Fernsteuerung (unter /m).

tests/test_youtube.py Verhaltens-Sicherheitsnetz (reine Funktionen, kein Netz/Platte).
                      Start:  python tests/test_youtube.py   (auch ohne pytest), 17 Tests.
browser-addon/        Universelle Erweiterung (FF/Chrome/Edge aus 1 Code, build.py).
```

**Stand Build 33 (09.07.2026) — gebaut & getestet:** Bibliothek (Icon-Karten, ⋯/Rechtsklick-
Menü, Alben-Ansicht, Dubletten, Batch-Tags), Playlists (Öffnen/Drag-Reorder/⋯/Mixe),
Player (8 Visualizer, 5 Looks, EQ, Crossfade/Gapless/Automix, Canvas, Radio, Speed, Sleep-
Timer, Kapitel, Untertitel/Karaoke/Transkript, Clip, Media-Tasten), Command-Bar 50/50
(URL+Download links, Live-Queue rechts, Now-Playing, Zwischenablage-Wächter, Drag&Drop-Link),
SponsorBlock, Kanal/Playlist-Abos, Smart-Playlists, Auto-Tagging (MusicBrainz)+Alben,
Fernsteuerung (opt-in, Code, /m), Log-View, Layouts speichern, Mini-Player, Einstellungs-Modal,
Ansicht-Verlauf (Mausrad). Offen: .exe (auf JBs Beta-Signal) → GitHub → VPN-Test →
Dashboard-Karte (Core, nur auf Go). Nur JB-bestätigte Punkte, siehe Memory-Audit.

**Regel (seit 09.07.2026):** Einbahn-Abhängigkeit `youtube_app → geo → vpn`.
Geo-Fehler-Erkennung lebt in `geo.py` (provider-unabhängig), NordVPN-Interna
ausschließlich in `vpn.py`. `youtube_app` importiert **kein** `vpn` mehr direkt.

## Daten-/Statusdateien (nicht committen — enthalten JBs Daten)

| Datei | Zweck |
|-------|-------|
| `config.json` | Einstellungen (Port, Cookies-Browser, Geo, Unterordner …) |
| `warteschlange.json` | offene Downloads (überlebt Neustarts, Resume via .part) |
| `geladen_log.json` | „Datenbank" fertiger Downloads = die Bibliothek |
| `playlists.json` | Playlists + Sync-Ordner/-Manifest |
| `yt_status.json` | **read-only fürs Dashboard** (Zähler + letzte Datei) |

## Suite-Anbindung (Konvention aus Core/dashboard.py)

Jedes Modul schreibt eine `*_status.json`; das Dashboard liest sie und rendert
eine Karte + Link zum lokalen Modul-Server. YouTube schreibt bereits
`yt_status.json` (Port 8776). **Offen:** die Dashboard-Karte selbst (das wäre
eine Änderung an `Core/dashboard.py` — sensibel, nur auf JBs Go). Tray-Eintrag
analog. So bleibt jedes Modul autark lauffähig, aber über EIN System gekoppelt.

## Aufräum-Fahrplan (Reihenfolge, JB-bestätigt)

1. **Saubere Basis** ← *hier sind wir*
   - [x] Test-Sicherheitsnetz angelegt (11 Tests grün).
   - [x] geo/vpn entkoppelt (Einbahn-Schichtung, live verifiziert).
   - [ ] `oberflaeche.py` in klar kommentierte Abschnitte gliedern (der große
         JS-Block ist der eigentliche „Spaghetti"-Kandidat) — Verhalten erhalten,
         durch das Netz + Browser-Tests abgesichert.
   - [ ] Optionen in Reiter-Gruppen, Bibliotheks-Leiste in ein „⚙ Ansicht"-Menü.
2. **Standalone .exe** (PyInstaller, `bin/` mitbündeln) — erst kurz vor Beta.
3. **GitHub** veröffentlichen (JBs GitHub-Desktop-Login, kein Token-Tippen).
4. **VPN** real testen (JB richtet Dienste ein, parallel).

## Feature-Backlog (JB-bestätigt, nach der sauberen Basis)

- **Player-Upgrade:** [x] Radio-Modus (📻) · [x] Visualizer (Balken/Welle/Oszi, 📊) ·
  [x] 5 Looks (Terracotta/Hell/Hacker/Neon/Ozean) · [ ] Crossfade/Gapless/Automix ·
  [ ] Canvas (Loop-Video). (Build 17)
- **Bibliothek:** Smart-/Auto-Playlists (Regel-basiert) · Dublettenfinder ·
  Batch-Tag-Editor · automatische Metadaten-Nachpflege.
- **Downloads:** SponsorBlock (Werbung/Intros auto-überspringen bzw. rausschneiden) ·
  Ausschnitt „von–bis" (wie ein Twitch-Clip) · Kanal/Playlist abonnieren ·
  Untertitel + Auto-Transkription (nur Text).
- **Handy-Fernsteuerung** mit Geräte-Wahl (wie Spotify Connect) — braucht
  LAN-Freigabe + Zugangscode (passt zum Online-/LANoMAT-Plan).
- **Browser-Erweiterung** (ein MV3-Code für Firefox/Chrome/Edge + Chromium-Derivate;
  Safari nur mit Mac/Apple-Account) + Store-Upload/Auto-Update von Claude gemanaged.
