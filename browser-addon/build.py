# -*- coding: utf-8 -*-
"""Baut die Browser-Erweiterung aus EINEM Quellcode für alle Browser.

Ein gemeinsamer Code (shared/) + eine Basis (manifest.base.json). Pro Browser
wird nur der Manifest-Unterschied ergänzt und ein fertiges, hochladbares Paket
(+ .zip) in dist/ erzeugt:
  - chrome/  : MV3 mit service_worker  (auch für Edge, Opera, Brave, Vivaldi, Arc)
  - edge/    : identisch zu chrome (eigener Store)
  - firefox/ : MV3 mit background.scripts + gecko-Einstellungen

Aufruf:  python build.py        (erzeugt Icons bei Bedarf, dann alle Pakete)

Safari geht NICHT aus diesem Code direkt — Apple braucht einen Mac + Xcode
(`safari-web-extension-converter`) + Developer-Account. Siehe STORE.md.
"""
import json
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(HERE, "shared")
DIST = os.path.join(HERE, "dist")

# Nur diese Felder unterscheiden sich zwischen den Browsern:
VARIANTEN = {
    "chrome":  {"background": {"service_worker": "background.js"}},
    "edge":    {"background": {"service_worker": "background.js"}},
    "firefox": {"background": {"scripts": ["background.js"]},
                "browser_specific_settings": {
                    "gecko": {"id": "youtube-downloader@jbk.local", "strict_min_version": "115.0"}}},
}


def icons_erzeugen():
    """Store-taugliche PNG-Icons (Chrome mag kein SVG) — dasselbe Download-Motiv wie der Tray."""
    from PIL import Image, ImageDraw
    ordner = os.path.join(SHARED, "icons")
    os.makedirs(ordner, exist_ok=True)
    for s in (16, 32, 48, 128):
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((s * .06, s * .06, s * .94, s * .94),
                  fill=(28, 24, 20, 255), outline=(214, 119, 86, 255), width=max(2, int(s * .06)))
        d.rectangle((s * .45, s * .26, s * .55, s * .55), fill=(214, 119, 86, 255))     # Pfeil-Schaft
        d.polygon([(s * .5, s * .72), (s * .30, s * .48), (s * .70, s * .48)], fill=(214, 119, 86, 255))
        d.rectangle((s * .33, s * .77, s * .67, s * .83), fill=(201, 149, 43, 255))     # Ablage
        img.save(os.path.join(ordner, f"icon{s}.png"))
    print("Icons erzeugt (16/32/48/128 px).")


def baue(browser, extra):
    with open(os.path.join(HERE, "manifest.base.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    manifest.update(extra)
    ziel = os.path.join(DIST, browser)
    if os.path.exists(ziel):
        shutil.rmtree(ziel)
    shutil.copytree(SHARED, ziel)
    with open(os.path.join(ziel, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    zpfad = os.path.join(DIST, f"ytdl-{browser}-v{manifest['version']}.zip")
    with zipfile.ZipFile(zpfad, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(ziel):
            for fn in files:
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, ziel))
    print(f"  {browser:8s} -> dist/{browser}/  +  {os.path.basename(zpfad)}")


def main():
    os.makedirs(DIST, exist_ok=True)
    if not os.path.exists(os.path.join(SHARED, "icons", "icon128.png")):
        icons_erzeugen()
    print("Baue Pakete:")
    for browser, extra in VARIANTEN.items():
        baue(browser, extra)
    print("\nFertig. Zum Ausprobieren: den passenden dist/<browser>-Ordner ungepackt laden\n"
          "(Chrome/Edge: chrome://extensions -> Entwicklermodus -> 'Entpackt laden';\n"
          " Firefox: about:debugging -> 'Temporär laden'). Store-Upload: STORE.md.")


if __name__ == "__main__":
    main()
