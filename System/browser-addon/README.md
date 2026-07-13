# YouTube-Downloader — Browser-Erweiterung (universell)

Ein Quellcode für **Firefox, Chrome, Edge** (+ alle Chromium-Browser: Opera, Brave, Vivaldi, Arc).

```
browser-addon/
  shared/            <- der EINE Quellcode (background/content/popup + Icons)
  manifest.base.json <- gemeinsame Manifest-Basis
  build.py           <- erzeugt dist/<browser>/ + hochladbare .zip je Browser
  dist/              <- Ergebnis (nicht committen)
  STORE.md           <- Veröffentlichen & Updaten (Stores, Signieren, Auto-Update)
```

## Bauen
```
python build.py
```
Erzeugt `dist/chrome`, `dist/edge`, `dist/firefox` (+ passende `.zip`). Icons werden beim
ersten Lauf als PNG erzeugt (Pillow, im Core-venv vorhanden).

## Was die Erweiterung tut
Auf youtube.com: kleiner ⬇-Hover-Knopf über Videos + Rechtsklick-Menü mit Qualitätswahl →
schickt den Link an die lokale App (`127.0.0.1:8776`, Popup zeigt den Verbindungsstatus).
Spricht **nur** mit dem eigenen PC, kein Fremd-Server.

## Ausprobieren / Veröffentlichen
Siehe **STORE.md** (Entpackt-Laden zum Testen; Store-Upload + Auto-Update-Erklärung).

> Der alte `../firefox-addon/`-Ordner ist der Vorläufer (nur Firefox, SVG-Icon) und kann
> bleiben; die Weiterentwicklung passiert hier in `browser-addon/`.
