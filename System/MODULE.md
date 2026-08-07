# SyncYouTube — Modul-Karte

> **PFLICHT aktuell halten (JB-Dauerregel 20.07.2026):** Jede neue/entfernte Datei hier
> eintragen. Zweck: Zusammenhänge sehen → Ausfälle und redundante Dateien sofort erkennen.
>
> Angelegt 23.07.2026, weil der **Programm-Kanon** (`SyncDashTray/System/programm_kanon.py`)
> die Lücke gemeldet hat: SyncYouTube war das einzige Familien-Programm ohne Modul-Karte.
> Der Inhalt ist **nicht neu erfunden**, sondern aus dem vorhandenen `_ARCHITEKTUR.md` in
> die Familien-Form (Tabelle: Datei → Zweck → Verknüpfung) überführt. `_ARCHITEKTUR.md`
> bleibt als ausführliche Erzählung inkl. Schichtungs-Diagramm daneben stehen.

## Skripte

| Datei | Zweck | Verknüpfung |
|---|---|---|
| `huelle.py` | Programm-Hülle (Spec Stufe 2, JB-Go 05.08.): eigenes Fenster (pywebview) lädt die Oberfläche vom lokalen Server; startet den Server selbst, falls er aus ist | Start über `SyncYouTube-Fenster.bat`; ruft `youtube_app.py` als Subprozess |
| `youtube_app.py` | Das Herzstück: Warteschlange + Worker, HTTP-Server (Port 8776), Download-Logik (yt-dlp), „Schon-geladen"-DB, Bibliothek, Playlists, Abos, Tray, `main()` | importiert `geo`, `oberflaeche`, `handy`; **Einbahn-Regel:** importiert NIE `vpn` direkt |
| `filme.py` | Film-Fundament (`Doku/SYNC_FILME_SPEC.md`, JB-Go 05.08.): Jellyfin-Katalog (Renés Server) als lokaler Spiegel, Bild-Cache, TMDB/OMDb-Anreicherung, Reihen-Engine, Stream-URL für den VLC-Motor, Fortschritts-Queue; Zugangsdaten NUR im Keyring, Token verlässt den Server nie | von `youtube_app` gerufen (`/api/filme/*`, 6-h-Haken in `ticker_schleife`); importiert NIE zurück (Einbahn-Regel wie geo/vpn) |
| `profil_geraete.py` | Teilprojekt 3 (JB-Go 05.08.): Profile („Wer schaut?") + Geräte-Registry mit Pairing-Code-Fluss und je-Gerät-Token (einzeln widerrufbar, an Profil gebunden); `geraet_ok()` = Riegel-Kern für alle Nicht-localhost-Zugriffe; Pairing-Seite (`PAIRING_HTML`). Bewusst nicht `profile.py` (stdlib-Schatten) | von `youtube_app` gerufen (`/api/geraet_*`, `/api/profile`, `/koppeln`, `_hat_zugriff`); importiert NIE zurück |
| `live_tv.py` | 📡 Live-TV (JB-Go 05.08.): lädt + parst die legale kodinerds-clean-M3U (öffentlich-rechtliche m3u8), 24-h-Cache; VLC spielt die Streams direkt | von `youtube_app` gerufen (`/api/live`, `/api/live/play`); importiert NIE zurück |
| `geo.py` | Gestufte Geo-Umgehung (Header-Trick → eigene Proxys → Gratis-Proxys → VPN-Adapter); erkennt und parst Geo-Fehler **provider-unabhängig** | von `youtube_app` gerufen; ruft `vpn` |
| `vpn.py` | Ausschließlich NordVPN-Steuerung (CLI + Insights-Status) — NordVPN-Interna leben nur hier | nur von `geo.py` gerufen (Einbahn-Abhängigkeit seit 09.07.2026) |
| `oberflaeche.py` | Die gesamte PC-Oberfläche als ein HTML/CSS/JS-String; wird bei jedem Seitenaufruf heiß nachgeladen (`importlib.reload`) | von `youtube_app` ausgeliefert; enthält den `LAYOUT_KERN`-Inline-Block (Wächter `test_layout_kern` im Familien-Repo erzwingt Gleichheit mit `SyncDashTray/System/layout_kern.js`) |
| `handy.py` | Schlanke Touch-Oberfläche der Handy-Fernsteuerung (Route `/m`, opt-in mit Code) | von `youtube_app` ausgeliefert |
| `update.py` | Selbst-Aktualisierung: prüft `releases/latest`, lädt die neue Fassung, tauscht sie aus | eigenständig; **MERKE:** Setup-Installationen nie auf die onefile-Form zurückfallen lassen |
| `tools/quellstart_paket.py` | Werkstatt: baut `SyncYouTube-Quellstart.zip` (signiertes python.org-Embeddable + Skripte) für Smart-App-Control-Nutzer (Pete-Fall 07.08.) | von Hand vor einem Release; Ergebnis nach `dist_exe/` |
| `familie.py` | gemeinsamer Kern der Familie (Pfade/json/status) — byte-gleiche Kopie | Wächter `test_familie_kern` im Familien-Repo erzwingt Gleichheit; Verteilung über `vendor_kern.py` |
| `layout_kern.js` | gemeinsamer Layout-Mathe-Kern (Snapping/Überlappung/Viewport-Einpassung, DOM-frei) — vendorte Kopie | Master liegt in `SyncDashTray/System/layout_kern.js` |

## Unterordner

| Ordner | Zweck |
|---|---|
| `tests/` | Verhaltens-Sicherheitsnetz (reine Funktionen, kein Netz/keine Platte). Start: `python tests/test_youtube.py` — läuft auch ohne pytest |
| `browser-addon/` | Universelle Erweiterung für Firefox/Chrome/Edge aus EINEM Code (`build.py`); AMO-signiert, hält sich über `updates.json` selbst aktuell |
| `firefox-addon/` | Firefox-spezifische Altfassung/Signier-Artefakte |
| `abo_index/` | Index-Dateien der Kanal-/Playlist-Abos (Backkatalog, RSS-Puls) |
| `bin/` | mitgelieferte Werkzeuge — **darin Deno**: yt-dlp braucht seit 2026 eine JS-Runtime für YouTubes n-Challenge, sonst „No video formats found" |
| `build/`, `dist/`, `dist_exe/`, `build_tmp/` | PyInstaller-Bauwerk und Ergebnisse (nicht committen) |

## Daten (nicht committen, enthalten JBs Daten)

`config.json` (Einstellungen: Port, Cookies-Browser, Geo, Unterordner) ·
`warteschlange.json` (offene Downloads, überlebt Neustarts, Resume via `.part`) ·
`geladen_log.json` (die Bibliothek = fertige Downloads) · `playlists.json` ·
`abos.json` · `lyrics_cache.json` (LRCLIB-Karaoke) ·
`yt_status.json` (**read-only fürs Dashboard**: Zähler + letzte Datei)

## Doku daneben

`_ARCHITEKTUR.md` (Schichtungs-Diagramm + Aufräum-Fahrplan) ·
`NAECHSTE_SESSION.md` (Übergabe innerhalb dieses Repos) ·
`SyncYouTube.spec` (PyInstaller)
