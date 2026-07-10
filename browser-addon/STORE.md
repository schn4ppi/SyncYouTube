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

**Automatisierung (später):** Der Upload lässt sich per Store-API skripten, dann kann Claude
Versionsbumps + Upload komplett übernehmen. Dafür braucht es **einmalig** Zugangsdaten:
- Chrome: OAuth-Client + Refresh-Token (Chrome Web Store API).
- Edge: Publisher-API-Key.
- Firefox: AMO-API-Credentials (JWT).
Diese kommen — wie GitHub/Web.de — **nur in den Windows-Anmeldeinformationsspeicher / keyring**,
nie in eine Datei. Bis dahin macht Claude das Packen, den Upload klickt JB.

## Store-Texte (Vorlage)
**Kurzbeschreibung:** YouTube-Videos mit einem Klick an deinen lokalen YouTube-Downloader schicken.

**Beschreibung:** Diese Erweiterung ergänzt den lokalen „YouTube-Downloader" (läuft auf deinem PC
unter 127.0.0.1:8776). Auf youtube.com erscheint beim Überfahren eines Videos ein kleiner
⬇-Knopf, und per Rechtsklick kannst du die Qualität wählen — der Link landet direkt in der
Download-Warteschlange der App. Es werden keine Daten an Dritte gesendet; die Erweiterung
kommuniziert ausschließlich mit der lokalen App auf deinem eigenen Rechner.

**Kategorie:** Produktivität. **Datenschutz:** keine Datensammlung.
