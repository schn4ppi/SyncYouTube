# Übergabe an die nächste SyncYouTube-Session

> **06.09.2026: ÄLTERER Stand (23.07., Build 144).** Die aktuelle Übergabe ist `NAECHSTER_PROMPT.md` daneben (05.08., Build 171). Am 06.09. nach `System/docs/` verschoben, damit die Datei versioniert ist (Befund SyncYouTube-05).

> **STAND 23.07.2026 — Build 144, 101/101 Tests grün.**
> **JB-Punkte 1, 2 und 7 sind erledigt** (Rahmen-Auswahl · Playlist sichern
> beim Hineinziehen · Einstellung für den Rahmen). Punkt 5 hat JB am 23.07.
> in der Bauform präzisiert: **zwei Achsen statt vier Reitern** — Format
> (MP3/Video/4K+) bleibt, dazu EIN Umschalter „nur Lieder". Vorher muss die
> Musik-Erkennung gehärtet werden, sie hat zwei gemessene Löcher (bei MP3
> gibt es gar keine Unterscheidung; bei Videos hängt sie am Dateinamen, den
> die Migration gerade verändert hat). Details im Start-Prompt.
> Der vollständige Start-Prompt mit allen offenen Punkten, den Messwerten und
> den FALLEN steht in **`System/NAECHSTER_PROMPT.md`** — dort zuerst lesen,
> nicht neu diagnostizieren.
>
> Erledigt: Punkt 1–4 des alten Plans komplett, aus Punkt 6 der Abbruch-Fehler
> und die Warteschlangen-Selbstheilung, Addon 1.0.9 released.
> JB hat zuletzt abgenommen: „Bibliothek funktioniert tadellos!"
>
> **Build 144 — Rahmen-Auswahl in der Player-Playlist ERLEDIGT (Punkt 1)**,
> zusammen mit der Einstellung dafür (Punkt 7). Der Code aus Build 139 war
> in Ordnung, er kam nur nie zum Zug: das Band startete nur auf freier Fläche,
> und eine LISTE hat keine — `.pl-queue` wächst mit ihrem Inhalt, gemessen
> 0 px frei bei 3 wie bei 14 Titeln. Jetzt Explorer-Muster (markierte Zeile
> verschieben, sonst Rahmen). Beim Messen fiel ein zweiter Fehler auf:
> `plqMark()` wischte jede gezogene Auswahl beim Loslassen wieder weg.
> **Die frühere Erklärung „Prüfumgebung hat keine Ausdehnung" war falsch** —
> in Wahrheit startet der Browser-Pane mit Viewport 0×0 (siehe FALLEN im
> Start-Prompt).
>
> Danach in JBs Reihenfolge: Playlist speichern/aktualisieren beim Ziehen ·
> Spotify-„+" für Lieblingssongs · Videonummer je Kanal (NICHT als
> Track-Nummer!) · Video-/Song-Einteilung nach Inhalt · Untertitel-Sprachwahl ·
> Bereich neben der Playlist als Ablage · Testmodus außerhalb JBs Ordner ·
> Punkt 5 der Spec (VLC, Cover, Hörbücher) · Hotkey-Editor.

> **SPEC (23.07., JB-bestätigt): `Doku/SYNCYOUTUBE_MEDIENZENTRALE_SPEC.md`** —
> bündelt Bibliothek 2.0 + Hörbuch/CD-Import (perfekte Reihenfolge) +
> Wiedergabe-Grundeinstellungen (3 Ebenen) + **VLC-Motor** („eigenes Programm
> mit VLC, Auslese in unserer Oberfläche") + simultane Oberflächen
> (Browser UND Programm-Hülle parallel) + TV/Handy/Desktop + Familien-
> Hüllen-Weiche (Kandidat). Etappenplan dort; 4 Punkte warten auf
> JB-Einzelbestätigung (im Spec-Kopf markiert). **Addon-Kanal liefert v1.0.7**
> (Asset-Tausch im v.1.2.2-Release, Hash außen verifiziert).

> **ETAPPE 1 GEBAUT (Builds 110–112, 23.07. nachts):** zentrale Kette
> `_datei_videoid` (Name→DB-Pfad→fp→Tag) ersetzt 4/5 [Id]-Stellen; fp-Backfill
> (79/79 echt); Id-Tags in Audio-Dateien (18 getaggt, Videos bewusst nicht —
> GB-Rewrite/Last-Budget); Migrations-Probelauf: 79 bereit, 0 Konflikte →
> **ANGEWENDET am 23.07.2026 um 12:05:59, 86 Dateien umbenannt** (79 Medien +
> mitgewanderte Untertitel); JB hat es am 23.07. ausdrücklich abgesegnet.
> `System/migration_probelauf.md` ist damit nur noch Beleg, kein Auftrag.
> Nachgemessen 23.07.: Probelauf liefert **0 Kandidaten, 0 Konflikte**, alle
> 86 DB-Pfade zeigen auf existierende Dateien. Neue Downloads tragen kein
> [Id] mehr (Build 113). Zurück geht es über ⚙ → 🏷 Namens-Baukasten → ↩
> (`/api/umbenennen` mit `art:"undo"`, nur von 127.0.0.1 erreichbar);
> Rückroll-Protokoll liegt in `System/migration_protokoll.json`.
> **Vorfall 23.07. (behoben):** Erst-Testlauf benannte die echten 79 um —
> vollständig zurückgerollt; Tests ersetzen `_geladen` seitdem komplett
> (NIE in die echte DB einfügen!). Details: ABNAHME.md.

## 🎯 NÄCHSTE RUNDE (JB-Go 23.07.): „Bibliothek 2.0" — Klammern + Abgleich + Ordner

JB hat das Paket erweitert (alle 3 bestätigt) + eine Vision benannt:
- **YouTube-Abgleich für Importe — NACHGESCHÄRFT (JB 23.07.: „500 Titel =
  großer Aufwand für den User? Kann der Downloader das selber lösen?"):
  JA — SyncDocs-⚡-Muster:** EINDEUTIGE Treffer (Titel passt + Dauer ±2 s +
  nur EIN Kandidat) verknüpft die App AUTOMATISCH (nur DB-Verknüpfung =
  nicht-destruktiv, Selbstheilung-statt-UI-Regel); in die Prüf-Liste kommen
  NUR Mehrdeutige/Nicht-Gefundene. Bei 500 Importen sieht JB also z. B.
  „462 automatisch zugeordnet, 38 zum Prüfen". Ordner: ganze Ordner rein =
  Downloads-Ordner heute + „Weitere Bibliotheks-Ordner" (unten). JB-Ansage
  „solltest du noch testen" ⇒ Runde MIT echten Import-Läufen verifizieren.
- **„Weitere Bibliotheks-Ordner"** (Einstellungen): zusätzliche Orte (2. Platte,
  NAS/SMB — auch ein freigegebener Jellyfin-Medienordner) werden wie der
  Downloads-Ordner gescannt; offline ⇒ bestehender „verschoben"-Status.
- **VISION (JB wörtlich sinngemäß): Jellyfin fällt weg** — „die Oberfläche
  finde ich minderwertig". **Konkretisiert (JB 23.07.): Auf dem Fernseher
  soll der Downloader „praktisch nur eine Bibliothek mit Player" sein —
  einfach zu steuern, mit GENRES, mit COVERN.** Bausteine: Cover existieren
  (Kachel-Ansicht), Genre fehlt (kommt sinnvoll aus dem YouTube-Abgleich/
  Metadaten mit); Handy-Fernsteuerung („wie Spotify Connect", handy.py) als
  Steuer-Weg — TV zeigt, Handy steuert; TV-Modus/10-Fuß-Ansicht (reduzierte
  Oberfläche: NUR Bibliothek+Player, große Kacheln, Pfeil-Navigation) als
  eigene spätere Stufe designen (NICHT in dieser Runde bauen).

### Kern: Klammern-Projekt — [Video-Id] raus aus den Dateinamen

3-Schichten-Design (JB hat zugestimmt; Vergleich: Plex/Jellyfin = DB+Pfad,
MusicBee/iTunes = DB+Tags in der Datei, Tube Archivist = Id im Namen wie wir
heute; JBs „Magnet"-Idee = Content-Fingerprint):
1. **Fingerabdruck-DB (primär):** je Eintrag pfad/groesse/mtime + fp
   (sha1 über erste+letzte 64 KB + Größe, OpenSubtitles-Stil). Scan-Kette:
   bekannter Pfad → Name-Match → Fingerprint → Tag-Lesen (nur Unbekanntes)
   → „Sonstiges". Alltag dadurch GLEICH schnell wie heute.
2. **Video-Id als Tag in der Datei** (Sicherheitsnetz fürs Kopieren auf
   andere Geräte): mutagen in-place (steckt in der exe), KEIN ffmpeg-Remux.
3. **Namen sauber:** neue Downloads ohne [Id]; Migration benennt Bestand um
   — ADDITIV + Probelauf-Default, Umbenennen als LETZTER Schritt erst nach
   JBs Blick auf den Probelauf; .vtt-Untertitel MIT umbenennen (Stamm-
   Kopplung!). Bricht etwas ab: Klammern bleiben stehen, alles läuft weiter.
Umbau-Stellen: die 5 [Id]-Lese-Stellen (Zeilen ~618/1059/2119/2202/2322 in
youtube_app.py, Stand Build 102) auf EINE zentrale Auflösung; TDD Pflicht;
Produktiv-Bibliothek = Vorsicht (HARTE REGEL nicht-destruktiv).

> Stand 22.07.2026 nachts (Abo-Fix- + Flyout-Runde). Vorgänger-Stand komplett erledigt.

## Aktuellstes Release: v.1.2.2 (Id 358219263, exe-SHA `0563381f…ce0b`)

Sammelt Build 98 (Mix-Anzahl wählbar 1–500, erst fragen dann 1,9-s-Auflösung;
/api/addon_hab) + **Addon v1.0.6 im Kanal** (grüner Hover-Knopf wenn schon
geladen — updates.json liefert v1.0.6, JB + Kumpel bekommen es automatisch).
**Dazu Build 101 (1bc442e): ✂-Schneide-Leiste** — A/B-Griffe ziehbar,
Player springt live mit, Wiedergabe endet an B; speichern unverändert
nicht-destruktiv (/api/clip). Live belegt am 8:35-Video (206 s/103 s exakt,
Auto-Pause); JBs erster echter Speichern-Klick = ffmpeg-Vollbeweis.
**Danach auf main (fürs nächste Release v.1.2.3 einsammeln): Build 99+100
„✨ Neues entdecken"** (f0fe899 + 9624917, Discover-Weekly-Muster) —
Radio-Mixe zu Playlist-Titeln, Bibliothek als Filter; ✨-Knopf in der
Bibliotheks-Leiste, „▶ Auf YouTube durchhören" (watch_videos → temporäre
list=TLGG-Playlist, live bestätigt; Wächter-Kandidat falls YouTube den Weg
kappt), Downloads sammeln sich in „✨ Entdeckt DD.MM." (ziel_playlist-
Mechanik im Fertig-Hook). Echt belegt: 14–47 Funde je Würfelung in ~5 s.
Offen: VirusTotal v.1.2.2 (JB-Klick); JBs erster echter Entdecker-Download
= Vollbeweis des Playlist-Hooks; JB-Entscheid [Id]-Klammern→Metadaten
(eigenes Projekt, 5 Lese-Stellen + Migration).

## Vorheriges Release: v.1.2.1 (Id 357599175, exe-SHA `4cc12e57…fb8a3`)

Wartungs-Release, sammelt Build 96 (Mini-Abos-Reiter) + 97 (Vollbild-Guard +
Mini-Player-Höhenkette) — beide vorab von JB real abgenommen. Assets wie
immer: exe + .sha256 + xpi v1.0.5 + updates.json (Kanal trägt weiter, von
außen verifiziert). v.1.2.0 als überholt markiert; Updater-Kette
1.2.0→1.2.1 live, 1.2.1 = „schon aktuell". Offen: VirusTotal-Einreichung
(JB-Klick, neuer Hash, Link im Body).

## Vorheriges Release: v.1.2.0 (Id 357535229, exe-SHA `c3c1a69d…e234c`)

Sammelt Build 92 (Layout-Basis-Anker), 93 (Backkatalog-Flyout + Windows-
Auswahl + Mengen-Staffel + YT-Timestamp), 94 (Flyout-Nachschliff) und 95
(Trennlinien/Scrollbalken-Abstand, Abo-Löschen wahlweise MIT Videos in den
Papierkorb, 🔗 Link-kopieren ohne Zeitstempel) + Addon v1.0.5 (Hover-Knopf
im Popup abschaltbar, Knopf am echten Videobild, Popup-notify-Bug weg).
**WICHTIG: v.1.2.0 ERSETZT das kurzlebige v.1.1.10** (JB-Fund: GitHub
sortiert Tags lexikalisch — 1.1.10 rutschte unter 1.1.2; Tag v.1.1.10 ist
gelöscht, Release-Id blieb). **Regel ab jetzt: keine zweistelligen
Patch-Nummern** — lieber Minor hochziehen. Alle Release-Namen auf
„SyncYouTube v.X.Y.Z" vereinheitlicht. Updater-Ketten von 1.1.9 UND 1.1.10
→ 1.2.0 live geprüft. **Addon-Selbst-Update läuft scharf:** installierte
v1.0.4 zieht v1.0.5 automatisch über updates.json (erster Realfall).
Offen: VirusTotal-Einreichung (JB-Klick, Hash-Link im Body); JBs Abo-Liste
ist leer (JB hat KateBush beim Testen des alten 🗑 entfernt — bei Bedarf
einfach neu abonnieren, der create-Pfad ist geheilt).

## Zuletzt passiert (diese Runde)

- **Build 91 (Commit 938e79b): Abo-Reiter-Bug behoben.** Abos auf bloße
  Kanal-Links zeigten nur die 2 Kanal-Reiter statt Folgen. create nutzt jetzt
  `_kanal_url()` + `_abo_baseline()` (Fallback-Kette /videos → /shorts →
  Uploads-Playlist UU…); `_abo_heilen()` repariert Bestands-Abos selbst
  (im Abo-Wächter, 30 s nach Start + 6-h-Puls) — Lawinen-Schutz: Baseline wird
  beim Heilen NEU gesetzt, kein einziger Auto-Download. JBs KateBush-Abo hat
  sich live geheilt (abos.json trägt /videos + 56 echte Video-IDs).
- **Addon v1.0.4 (Commit 20ef612): Firefox-Selbst-Update AKTIV.**
  `update_url` → `releases/latest/download/updates.json`; `amo_sign.py`
  erzeugt updates.json (mit xpi-sha256) automatisch nach dem Signieren.
  **Release-Pflicht ab jetzt: JEDES Release trägt die aktuelle signierte
  xpi + updates.json als Assets** (sonst läuft latest/download ins Leere).
  Details: `browser-addon/STORE.md`.
- **v.1.1.9 released** (Tag `v.1.1.9`, sammelt Build 90+91 + Addon v1.0.4;
  Build 89 ging schon mit v.1.1.8 raus). exe-SHA256 `c3924156…321f52`.
- **Build 92 (Commit 3da1092): Layout-Drift beseitigt (JB-Fund nach dem
  Neustart: „alles ein wenig bewegt").** Wurzelursache seit Build 85:
  Reload/Resize skalierten inkrementell und speicherten gerundete Pixel
  sofort übers Original (1–2 px Drift JE Zyklus, live gemessen; Extremfall
  0-Viewport → 320er-Minima zementiert). Jetzt Basis-Anker: Nutzer-Anordnung
  liegt unantastbar als `L.basis`, Anzeige = einmalige Projektion; nur echte
  Geometrie-Änderungen setzen die Basis neu (Signatur-Erkennung in
  saveLayout). Live bewiesen: Resize-Zyklen + Reload pixelexakt. Quellcode
  wird heiß ausgeliefert (JB: einmal F5); **exe-Nutzer bekommen den Fix erst
  mit dem nächsten Release (v.1.1.10) — Build 92 liegt dafür bereit.**

- **Build 93 (Commit e203f38): Backkatalog-Flyout + Windows-Auswahl +
  Mengen-Staffel + YT-Timestamp** (JB-Design-Go mit 3 Entscheiden). Flyout am
  📜-Knopf (bis 820 px, Viewport-geklemmt auch bei Resize), Auswahl wie
  Windows (Klick/Strg/Shift/Strg+A/Esc/Rubberband), Staffel 10/25/50/100/
  Alle auf die gefilterte Sicht mit Richtungs-Schalter (Standard älteste
  zuerst), Player-YouTube-Knopf springt zu &t=<Position>s. Live verifiziert
  am echten 56-Folgen-Backkatalog (folgen_laden gestubbt, keine echten
  Downloads im Test).

## Nach dem Release dazugekommen (fürs NÄCHSTE Release einsammeln)

- **Build 96 (d1111e7):** Abos-Reiter fehlte im Mini-Modus-Download-Panel.
- **Build 97 (5ac3c47):** Vollbild hält jetzt (canvasAnpassen ruht während
  `document.fullscreenElement` — Vollbild-Resize warf das Video sonst sofort
  raus) + Mini-Player füllt die 188px-Leiste (Höhen-Kette + min-width 340).
  **Beides von JB real abgenommen (23.07.): „passt beides".**

## GEPLANT (JB-Go 23.07.): Installer-Paket wie SyncManga — als v.1.3.0

JB-Entscheid: Sobald SyncManga v0.4.1 (Inno-Setup-Installer + PyInstaller-
onedir + Microsoft-False-Positive-Meldung) GRÜN ist, übernimmt SyncYouTube
das erprobte Rezept. **Ab sofort gilt: FP-Meldung an Microsoft gehört in
JEDE Release-Runde** (Ablauf kommt aus der Manga-Session).
SyncYouTube-Sonderbaustellen (Vorschläge, beim Bau final bestätigen):
1. **Auto-Updater umbauen** (größter Brocken): statt exe-Selbsttausch →
   Setup laden, Hash prüfen, `/SILENT` ausführen; Migrations-Brücke für
   Bestands-Nutzer der Einzeldatei-exe. TDD auf update.py (Testbasis gut).
2. **Installationsort beschreibbar:** Benutzer-Setup nach
   `%LOCALAPPDATA%\Programs` (kein Admin, SCRIPT_DIR bleibt beschreibbar —
   Datenpfad-Code unangetastet, Verhalten erhalten).
3. onedir entschärft zusätzlich: UPX beim Umstieg ABSCHALTEN (upx=True in
   SyncYouTube.spec ist ein eigener AV-Trigger) + schnellerer Start (kein
   200-MB-Temp-Entpacken je Start).
4. Azure Trusted Signing = Familien-Abo (signiert Manga + YouTube + alle
   künftigen exes) — richtet JB gemeinsam mit einer Session ein.

## Offen / für kommende Sessions

- **JB-Einmal-Schritt:** ytdl-firefox-v1.0.4-signiert.xpi einmal von Hand
  installieren (auf about:addons ziehen) — Versionen ≤1.0.3 kennen den
  Update-Kanal nicht. Ab dann updatet Firefox selbst.
- **Erneuern/Auto-Löschen** weiterhin nur als Unit-Pfad geprüft — bei
  Gelegenheit einmal end-to-end (Format wechseln → Erneuern (ersetzen) →
  Papierkorb prüfen).
- **VPN-/Geo-Live-Test** weiter offen (JB testet Dienste).
- Chrome/Edge-Store-Upload weiter offen (API-Keys fehlen, STORE.md).

## Bekannte Merkposten

- yt-dlp braucht Deno (`System\bin\`), sonst „No video formats found".
- Port 8776 = JBs laufende Instanz (pythonw) → nie killen; Neustart über
  `/api/beenden` + Starter-bat/vbs (`--no-browser` für Wartungs-Neustarts).
- Release-Pipeline: exe (PyInstaller `System/SyncYouTube.spec`, --distpath
  dist_exe) → isolierter Rauchtest (Temp-Ordner mit config.json Port 8779,
  `--no-browser --no-tray`) → sha256 → Tag `v.X.Y.Z` (mit Punkt!) → Release
  per API (Token via `git credential fill`) → Assets exe/.sha256/xpi/
  updates.json → Vorgänger „Ueberholt"-Zeile → VirusTotal-URL-Scan →
  README/Screenshot prüfen.
