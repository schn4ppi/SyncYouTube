# Browser-Erweiterung — Veröffentlichen & Updaten

Ein Quellcode (`shared/`), ein Basis-Manifest (`manifest.base.json`).
`python build.py` erzeugt fertige, hochladbare Pakete + Zips in `dist/`:

| Browser | Paket | läuft außerdem auf |
|---|---|---|
| **Chrome** | `dist/ytdl-chrome-*.zip` | Opera, Brave, Vivaldi, Arc (alle Chromium) |
| **Edge** | `dist/ytdl-edge-*.zip` | (identisch zu Chrome, eigener Store) |
| **Firefox** | `dist/ytdl-firefox-*.zip` | — |

Die Erweiterung spricht ausschließlich mit `http://127.0.0.1:8776` (der lokalen App).
Kein Tracking, keine Fremd-Server — das ist bei der Store-Prüfung ein klarer Pluspunkt.

## Sofort ausprobieren (ohne Store)
- **Chrome/Edge:** `chrome://extensions` → Entwicklermodus an → „Entpackt laden" → `dist/chrome` (bzw. `dist/edge`).
- **Firefox:** `about:debugging#/runtime/this-firefox` → „Temporäres Add-on laden" → `dist/firefox/manifest.json`.

## In die Stores (einmalig je Store ein Entwickler-Konto)
1. **Chrome Web Store** — Konto **einmalig 5 $** (JB hat bezahlt ✅).
   `chrome.google.com/webstore/devconsole` → „Neues Element" → `ytdl-chrome-*.zip` hochladen →
   Beschreibung/Screenshots (Texte unten) → zur Prüfung senden (i.d.R. 1–3 Tage).
2. **Microsoft Edge Add-ons** — Konto **kostenlos**.
   `partner.microsoft.com/dashboard/microsoftedge` → `ytdl-edge-*.zip`.
3. **Firefox AMO** — Konto **kostenlos**.
   `addons.mozilla.org/developers` → `ytdl-firefox-*.zip`. AMO **signiert automatisch**.
   Alternativ **selbst gehostet**: AMO signiert die `.xpi`, du hängst eine `update_url` ins Manifest
   und hostest die Datei selbst (nur Firefox erlaubt das — Chrome/Edge nur über den Store).
4. **Safari** — geht **nicht** aus diesem Code direkt: braucht einen **Mac** + Xcode
   (`xcrun safari-web-extension-converter dist/chrome`) + Apple-Developer-Account (99 $/Jahr).
   Separater Zweig, erst wenn ein Mac verfügbar ist.

## Wie Updates laufen (JB-Ziel: von Claude gemanaged)
1. In `manifest.base.json` die `version` erhöhen (z. B. `1.0.1`).
2. `python build.py` → neue Zips in `dist/`.
3. Neues Zip im jeweiligen Store hochladen → **die Browser aktualisieren die Nutzer automatisch**
   (kein Zutun der Nutzer). Firefox-selbst-gehostet: neue `.xpi` + `updates.json` austauschen.

### Firefox-Selbst-Update (AKTIV seit v1.0.4, 22.07.2026)
Das Firefox-Manifest trägt `browser_specific_settings.gecko.update_url` →
`https://github.com/schn4ppi/SyncYouTube/releases/latest/download/updates.json`.
Firefox fragt diese Adresse regelmäßig ab und installiert neue signierte Versionen
**selbst** — nie wieder xpi von Hand ziehen. Damit die Kette hält, MUSS **jedes**
GitHub-Release zwei Addon-Assets tragen (Release-Checkliste!):
- `ytdl-firefox-vX.Y.Z-signiert.xpi` (die aktuelle signierte Erweiterung)
- `updates.json` (erzeugt `amo_sign.py` automatisch nach dem Signieren,
  inkl. `sha256`-Hash der xpi; zeigt per `releases/latest/download/…` auf die xpi)

Auch wenn ein App-Release KEINE neue Addon-Version bringt: die zuletzt signierte
xpi + updates.json unverändert wieder mit hochladen, sonst läuft `latest/download`
ins Leere (Firefox behält dann still die installierte Version — heilt sich beim
nächsten vollständigen Release).

**Einmaliger Umstieg:** Versionen ≤ 1.0.3 haben noch KEIN `update_url` und erfahren
von Updates nie — die v1.0.4 einmal von Hand installieren (xpi auf `about:addons`
ziehen), ab dann updatet Firefox selbst.

**Automatisierung:** Der Upload lässt sich per Store-API skripten, dann kann Claude
Versionsbumps + Upload komplett übernehmen. Dafür braucht es **einmalig** Zugangsdaten:
- Chrome: OAuth-Client + Refresh-Token (Chrome Web Store API) — noch offen.
- Edge: Publisher-API-Key — noch offen.
- **Firefox: FERTIG GEBAUT → `amo_sign.py`** (siehe unten).
Diese kommen — wie GitHub/Web.de — **nur in den Windows-Anmeldeinformationsspeicher / keyring**,
nie in eine Datei.

## Firefox-Automatik: `amo_sign.py`

Einmalige Einrichtung (JB, ~2 Minuten):
1. https://addons.mozilla.org/de/developers/addon/api/key/ → „Schlüssel erzeugen"
2. `..\..\Core\venv\Scripts\python.exe amo_sign.py --schluessel` → Aussteller + Secret
   eingeben (Eingabe unsichtbar, landet nur im Windows-Keyring).

Danach je Release nur noch:
```
python build.py                                   # neue Zips bauen
..\..\Core\venv\Scripts\python.exe amo_sign.py    # hochladen (Kanal: listed)
```
- `--kanal unlisted` = **selbst verteilt**: AMO signiert automatisch in Minuten,
  das Skript lädt die fertige `.xpi` nach `dist/` — dauerhaft installierbar,
  darf mit ins GitHub-Release. (JBs Add-on läuft auf diesem Kanal.)
- `--status` = Versionen + Prüf-Status abfragen.
- `--holen` = neueste fertig signierte `.xpi` nach `dist/` laden
  (dauerhaft installieren: Datei in Firefox auf `about:addons` ziehen).

## Store-Texte (Vorlage)
**Kurzbeschreibung:** YouTube-Videos mit einem Klick an deinen lokalen YouTube-Downloader schicken.

**Beschreibung:** Diese Erweiterung ergänzt den lokalen „YouTube-Downloader" (läuft auf deinem PC
unter 127.0.0.1:8776). Auf youtube.com erscheint beim Überfahren eines Videos ein kleiner
⬇-Knopf, und per Rechtsklick kannst du die Qualität wählen — der Link landet direkt in der
Download-Warteschlange der App. Es werden keine Daten an Dritte gesendet; die Erweiterung
kommuniziert ausschließlich mit der lokalen App auf deinem eigenen Rechner.

**Kategorie:** Produktivität. **Datenschutz:** keine Datensammlung.
