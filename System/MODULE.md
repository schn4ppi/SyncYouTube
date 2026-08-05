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
| `geo.py` | Gestufte Geo-Umgehung (Header-Trick → eigene Proxys → Gratis-Proxys → VPN-Adapter); erkennt und parst Geo-Fehler **provider-unabhängig** | von `youtube_app` gerufen; ruft `vpn` |
| `vpn.py` | Ausschließlich NordVPN-Steuerung (CLI + Insights-Status) — NordVPN-Interna leben nur hier | nur von `geo.py` gerufen (Einbahn-Abhängigkeit seit 09.07.2026) |
| `oberflaeche.py` | Die gesamte PC-Oberfläche als ein HTML/CSS/JS-String; wird bei jedem Seitenaufruf heiß nachgeladen (`importlib.reload`) | von `youtube_app` ausgeliefert; enthält den `LAYOUT_KERN`-Inline-Block (Wächter `test_layout_kern` im Familien-Repo erzwingt Gleichheit mit `SyncDashTray/System/layout_kern.js`) |
| `handy.py` | Schlanke Touch-Oberfläche der Handy-Fernsteuerung (Route `/m`, opt-in mit Code) | von `youtube_app` ausgeliefert |
| `update.py` | Selbst-Aktualisierung: prüft `releases/latest`, lädt die neue Fassung, tauscht sie aus | eigenständig; **MERKE:** Setup-Installationen nie auf die onefile-Form zurückfallen lassen |
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
