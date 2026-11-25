# Lizenzen und Quellcode

Diese Datei gilt für die **aktuelle Fassung v.1.4.5**. Ältere Fassungen bündelten andere
Stände; ihre Angabe steht im jeweiligen [Release](../../releases). Kurzfassung auf der
Startseite: [README](README.md#lizenz).

Warum das hier steht und nicht auf der Startseite: die Aufzählung ist lang, ändert sich
mit jedem Bau und interessiert niemanden, der die App nur benutzen will.

**GPL-3.0-or-later** (siehe [LICENSE](LICENSE)). Diese Lizenz gilt für den eigenen Code
in diesem Repo. Die ausgelieferte `SyncYouTube.exe` v1.4.5 packt zusätzlich fremde
Bibliotheken und drei fertige Programme ein. Die Liste unten ist gemessen, nicht aus dem
Gedächtnis geschrieben: am 25.11.2026 aus der Bauliste von v1.4.1
(`System/build/SyncYouTube/PKG-00.toc` und `PYZ-00.toc`) und den Paket-Angaben der
Bau-Umgebung. Gebaut wird seit v1.4.1 aus einer eigenen Umgebung mit festen Fassungen
(`System/tools/bau_pakete.py`, festgehaltener Stand in `System/tools/bau_stand.txt`);
exe und Quellstart-Paket tragen dieselben Fassungen.

**Es gibt keinen Lizenz-Konflikt.** Jeder Bestandteil ist mit GPL-3.0-or-later
verträglich: GPL-2.0-**or-later** darf auf Version 3 gehoben werden, Apache-2.0 ist
in eine Richtung mit GPLv3 verträglich, und MPL-2.0 trägt dafür eine eigene Klausel.

**Lizenztexte liegen bei.** Seit v1.4.1 legt die Bauvorschrift jeder Verteilung, die in
der exe steckt, ihre Lizenzdateien aus der `.dist-info` bei (in der exe unter
`lizenzen/<Verteilung>/`, 41 Verteilungen), dazu Pythons eigene `LICENSE.txt` unter
`lizenzen/python/`. Bis v1.4.0 lagen nur 13 Texte bei; der damals hier vermerkte offene
Punkt ist damit erledigt.

### Bestandteile mit Copyleft (hier entstehen Pflichten)

| Bestandteil | Fassung | Lizenz |
|---|---|---|
| [FFmpeg](https://ffmpeg.org) (`ffmpeg.exe` + `ffprobe.exe`) | `N-129267-g9ec5cf1aac-20261124` | **GPLv3** (gebaut mit `--enable-gpl --enable-version3`, ohne `--enable-nonfree`) |
| [pykakasi](https://codeberg.org/miurahr/pykakasi) | 2.3.0 | GPL-3.0-or-later |
| [mutagen](https://github.com/quodlibet/mutagen) | 1.48.1 | GPL-2.0-or-later |
| [pystray](https://github.com/moses-palmer/pystray) | 0.19.5 | LGPLv3 |
| [python-vlc](https://github.com/oaubert/python-vlc) | 3.0.21203 | LGPL-2.1-or-later |
| [PyInstaller](https://pyinstaller.org) (Startprogramm der exe) | 6.22.3 | GPL-2.0-or-later mit Bootloader-Ausnahme |

Beim FFmpeg-Programm ist die Angabe genauer als früher: Es ist ausdrücklich ein
**GPLv3**-Build, nicht nur „GPL", weil `--enable-version3` gesetzt ist. Weitergeben darf
man ihn, denn `--enable-nonfree` fehlt.

### Bestandteile mit freizügiger Lizenz

Diese Lizenzen verlangen keine Gegenleistung, wohl aber, dass Copyright-Vermerk und
Lizenztext mit ausgeliefert werden; beides liegt bei (siehe oben). Nach Lizenz gebündelt:

- **Unlicense:** yt-dlp 2026.11.23 · yt-dlp-ejs 0.8.0 (dieses zusätzlich MIT und ISC).
- **MIT:** [Deno](https://deno.com) 2.9.8 (`deno.exe`) · altgraph 0.17.5 · brotli 1.2.1 ·
  charset-normalizer 3.5.3 · curl_cffi 0.17.0 · Deprecated 3.0.1 · jaconv 0.5.0 ·
  jaraco.classes 3.4.0 · jaraco.context 6.1.2 · jaraco.functools 4.6.0 · keyring 25.7.0 ·
  more-itertools 11.2.1 · pefile 2024.8.26 · setuptools 84.2.1 · six 1.17.0 · urllib3 2.8.0.
- **MIT, [pywinrt](https://github.com/pywinrt/pywinrt)** für die Windows-Medienanmeldung
  des VLC-Motors: winrt-runtime 4.2.1 · winrt-Windows.Foundation,
  winrt-Windows.Foundation.Collections, winrt-Windows.Media und
  winrt-Windows.Storage.Streams je 4!10.0.28000.2957 · winrt-Windows.Media.Interop 4.0.0.
  Copyright (c) Microsoft Corporation; Copyright (c) 2021-2026 David Lechner. Seit
  pywinrt 4 bringt jedes Paket seinen Lizenztext selbst mit; eine Kopie liegt zusätzlich
  als `System/lizenzen/pywinrt_LICENSE.txt` bei.
- **MIT-0:** cffi 2.1.1.
- **MIT-CMU:** pillow 13.0.0.
- **BSD (2- oder 3-Klausel):** idna 3.20 · pycparser 3.12 · pywin32-ctypes 0.2.3 ·
  qrcode 8.2 · websockets 17.4 · wrapt 2.5.2.
- **Doppelt lizenziert:** packaging 26.4 (Apache-2.0 oder BSD-2-Clause).
- **Apache-2.0:** requests 2.34.2.
- **MPL-2.0:** certifi 2026.11.20 (das Wurzelzertifikat-Bündel).
- **Python-Lizenz:** typing_extensions 4.16.0 (PSF-2.0) · das Python 3.14.10 der exe
  selbst (PSF-2.0) samt der Teile, die python.org mitliefert, darunter OpenSSL 3.5.9
  (Apache-2.0), Tcl/Tk 9.0 (für den Ordner-Dialog) und SQLite 3.50.4; ihre Texte stehen in
  Pythons `LICENSE.txt`.
- **Gemischt, alles freizügig:** pycryptodomex 3.24.2 (BSD und Public Domain).
- **Von setuptools mitgeliefert** (sie liegen unter `setuptools/_vendor/` und wandern
  darum mit in die exe, ohne eigenständig installiert zu sein): importlib_metadata 8.7.1
  (Apache-2.0) · packaging 26.3 (Apache-2.0 oder BSD-2-Clause) · backports.tarfile 1.2.0 ·
  jaraco.text 4.0.0 · tomli 2.4.0 · wheel 0.46.3 · zipp 3.23.0 (die fünf zuletzt genannten
  MIT).

Nicht mehr in der exe (bis v1.4.0 nur zufällig aus der Umgebung mitgenommen):
numpy, cryptography, chardet, psutil, pyreadline3, PyYAML, simplejson, defusedxml,
pythonnet und clr_loader.

### Microsoft Visual C++-Laufzeit (bis v1.4.0)

Bis v1.4.0 brachte das Paket winrt-runtime 3.2.1 eine eigene `msvcp140.dll` mit (Microsoft
Visual C++-Laufzeit, von Microsoft signiert), die unverändert neben den
winrt-Erweiterungen lag. Sie stand nicht unter MIT, sondern unter den Lizenzbedingungen
von Visual Studio ([REDIST-Liste](https://learn.microsoft.com/en-us/visualstudio/releases/2019/redistribution),
[Redistribute Visual C++ Files](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files)),
und ob die Weitergabe über pywinrt davon gedeckt war, blieb ungeprüft. **Seit v1.4.1
(pywinrt 4) liegt keine `msvcp140.dll` mehr bei**: die Erweiterungen brauchen nur noch
die C-Laufzeit (`vcruntime140.dll`), die Python selbst mitbringt. Der offene Punkt
betrifft damit nur noch die alten Fassungen.

### Quellstart-Paket (`SyncYouTube-Quellstart.zip`)

Das Quellstart-Paket enthält kein PyInstaller, dafür:

- das eingebettete Python von python.org in der Fassung des Bau-Pythons (3.14.10),
  PSF-Lizenz, Text in `python/LICENSE.txt`;
- dieselben Pakete wie die exe, in denselben Fassungen (installiert mit
  `System/tools/bau_stand.txt` als Vorgabe), mit ihren Lizenztexten in `lib/*.dist-info`;
- zusätzlich für den Fenster-Modus (`SyncYouTube-Fenster.bat`):
  [pywebview](https://github.com/r0x0r/pywebview) 6.2.1 (BSD-3-Clause) mit
  pythonnet 3.2.1 (MIT), clr_loader 0.3.1 (MIT), bottle 0.13.4 (MIT), proxy_tools 0.1.0
  (MIT) und colorama 0.4.6 (BSD-3-Clause). proxy_tools bringt keinen eigenen Lizenztext
  mit; seine Lizenz steht nur in den Paket-Angaben (`lib/proxy_tools-0.1.0.dist-info/METADATA`);
- ffmpeg, ffprobe und Deno wie oben, dazu `LICENSE`, diese Datei und das `README.md`.

### Wo der Quellcode liegt

GPL und LGPL verlangen, dass der Quellcode zu dem verfügbar ist, was ausgeliefert wird.

1. **Eigener Code:** vollständig in diesem Repo, dieselbe Fassung wie in der exe.
2. **Python-Bibliotheken:** auf [PyPI](https://pypi.org) unter genau den oben genannten
   Fassungen, soweit dort ein Quell-Archiv liegt. Eine Ausnahme ist geprüft und
   dokumentiert: **pystray 0.19.5** wurde auf PyPI nur als Wheel veröffentlicht, das
   letzte Quell-Archiv trägt 0.19.4. Der Quellcode zu 0.19.5 liegt im Projekt selbst,
   [moses-palmer/pystray](https://github.com/moses-palmer/pystray), Marke `v0.19.5`.
   Das zählt, weil pystray unter LGPLv3 steht und damit tatsächlich eine Pflicht auslöst.
3. **FFmpeg:** Der beigelegte Build stammt aus den Windows-Sammelbuilds von
   [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds), Spielart `win64-gpl`,
   Veröffentlichung [`autobuild-2026-11-24-12-41`](https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-11-24-12-41)
   (Datei `ffmpeg-N-129267-g9ec5cf1aac-win64-gpl.zip`, SHA-256 gegen die `checksums.sha256`
   der Veröffentlichung geprüft). Diese Builds sind von der offiziellen
   [FFmpeg-Downloadseite](https://ffmpeg.org/download.html) verlinkt; das Bau-Rezept steht
   dort in `scripts.d/`, `variants/` und `patches/`. Der FFmpeg-Quellcode selbst ist durch
   die Kennung des Builds eindeutig bestimmt: Git-Stand **`9ec5cf1aac`** im
   [FFmpeg-Repo](https://github.com/FFmpeg/FFmpeg).
4. **Deno:** Quellcode im [Deno-Repo](https://github.com/denoland/deno), Fassung 2.9.8
   (Datei `deno-x86_64-pc-windows-msvc.zip` der Veröffentlichung `v2.9.8`, SHA-256 geprüft,
   von Deno Land Inc. signiert).

Wer die genannten Fassungen nicht selbst holen möchte, bekommt sie auf Nachfrage.
