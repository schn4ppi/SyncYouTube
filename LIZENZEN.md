# Lizenzen und Quellcode

Diese Datei gilt für die **aktuelle Fassung v.1.2.4**. Ältere Fassungen bündelten andere
Stände; ihre Angabe steht im jeweiligen [Release](../../releases). Kurzfassung auf der
Startseite: [README](README.md#lizenz).

Warum das hier steht und nicht auf der Startseite: die Aufzählung ist lang, ändert sich
mit jedem Bau und interessiert niemanden, der die App nur benutzen will.

**GPL-3.0-or-later** (siehe [LICENSE](LICENSE)). Diese Lizenz gilt für den eigenen Code
in diesem Repo. Die ausgelieferte `SyncYouTube.exe` v1.2.4 packt zusätzlich fremde
Bibliotheken und drei fertige Programme ein; die Liste unten ist aus der Bauliste des
Builds (`System/build/SyncYouTube/Analysis-00.toc`) und den Paket-Angaben der
Python-Umgebung gemessen, nicht aus dem Gedächtnis geschrieben.

**Es gibt keinen Lizenz-Konflikt.** Jeder Bestandteil ist mit GPL-3.0-or-later
verträglich: GPL-2.0-**or-later** darf auf Version 3 gehoben werden, Apache-2.0 ist
in eine Richtung mit GPLv3 verträglich, und MPL-2.0 trägt dafür eine eigene Klausel.

### Bestandteile mit Copyleft (hier entstehen Pflichten)

| Bestandteil | Fassung | Lizenz |
|---|---|---|
| [FFmpeg](https://ffmpeg.org) (`ffmpeg.exe` + `ffprobe.exe`) | `N-125505-gc57660fb18-20260708` | **GPLv3** (gebaut mit `--enable-gpl --enable-version3`, ohne `--enable-nonfree`) |
| [pykakasi](https://codeberg.org/miurahr/pykakasi) | 2.3.0 | GPL-3.0-or-later |
| [mutagen](https://github.com/quodlibet/mutagen) | 1.48.1 | GPL-2.0-or-later |
| [pystray](https://github.com/moses-palmer/pystray) | 0.19.5 | LGPLv3 |
| [python-vlc](https://github.com/oaubert/python-vlc) | 3.0.21203 | LGPL-2.1-or-later |
| [PyInstaller](https://pyinstaller.org) (Startprogramm der exe) | 6.21.0 | GPL-2.0-or-later mit Bootloader-Ausnahme |

Beim FFmpeg-Programm ist die Angabe genauer als früher: Es ist ausdrücklich ein
**GPLv3**-Build, nicht nur „GPL", weil `--enable-version3` gesetzt ist. Weitergeben darf
man ihn, denn `--enable-nonfree` fehlt.

### Bestandteile mit freizügiger Lizenz

Diese Lizenzen verlangen keine Gegenleistung, wohl aber, dass **Copyright-Vermerk und
Lizenztext mit ausgeliefert werden** — Namensnennung allein genügt nicht. Ehrlich gesagt:
in der heutigen `SyncYouTube.exe` liegen nur zehn dieser Lizenztexte bei, für die übrigen
fehlen sie. Das ist ein offener Punkt und kein erledigter. Bis er behoben ist, stehen
Name, Fassung und Lizenz wenigstens hier, und jede Fassung ist über die unten genannten
Quellen samt ihrem Lizenztext auffindbar. Nach Lizenz gebündelt:

- **Unlicense:** yt-dlp 2026.8.19 · yt-dlp-ejs 0.8.0 (dieses zusätzlich MIT und ISC).
- **MIT:** [Deno](https://deno.com) 2.9.2 (`deno.exe`) · altgraph 0.17.5 · brotli 1.2.0 ·
  cffi 2.0.0 · charset-normalizer 3.4.7 · clr_loader 0.3.1 · curl_cffi 0.15.0 ·
  Deprecated 1.3.1 · jaconv 0.5.0 · jaraco.classes 3.4.0 · jaraco.context 6.1.2 ·
  jaraco.functools 4.5.0 · keyring 25.7.0 · more-itertools 11.1.0 · pefile 2024.8.26 ·
  pythonnet 3.1.0 · PyYAML 6.0.3 · setuptools 82.0.1 · six 1.17.0 · urllib3 2.7.0.
- **MIT-CMU:** pillow 12.2.0 (die Angabe „MIT-HPND" hier war falsch).
- **BSD (2- oder 3-Klausel, 0BSD):** chardet 7.6.0 · idna 3.18 · psutil 7.2.2 ·
  pycparser 3.0 · pyreadline3 3.5.6 · pywin32-ctypes 0.2.3 · qrcode 8.2 ·
  websockets 16.0 · wrapt 2.2.2.
- **Doppelt lizenziert:** cryptography 49.0.0 (Apache-2.0 oder BSD-3-Clause) ·
  packaging 26.2 (Apache-2.0 oder BSD-2-Clause) · simplejson 4.1.1 (MIT oder AFL-2.1).
- **Apache-2.0:** requests 2.34.2.
- **MPL-2.0:** certifi 2026.6.17 (das Wurzelzertifikat-Bündel).
- **Python-Lizenz:** defusedxml 0.7.1 (PSF) · typing_extensions 4.16.0 (PSF-2.0).
- **Gemischt, alles freizügig:** numpy 2.5.1 (BSD-3-Clause, 0BSD, MIT, Zlib, CC0-1.0) ·
  pycryptodomex 3.23.0 (BSD und Public Domain).
- **Von setuptools mitgeliefert** (sie liegen unter `setuptools/_vendor/` und wandern
  darum mit in die exe, ohne eigenständig installiert zu sein): importlib_metadata 8.7.1
  (Apache-2.0) · backports.tarfile 1.2.0 · tomli 2.4.0 · wheel 0.46.3 · zipp 3.23.0
  (die vier zuletzt genannten MIT).

### Wo der Quellcode liegt

GPL und LGPL verlangen, dass der Quellcode zu dem verfügbar ist, was ausgeliefert wird.

1. **Eigener Code:** vollständig in diesem Repo, dieselbe Fassung wie in der exe.
2. **Python-Bibliotheken:** auf [PyPI](https://pypi.org) unter genau den oben genannten
   Fassungen, soweit dort ein Quell-Archiv liegt. Eine Ausnahme ist geprüft und
   dokumentiert: **pystray 0.19.5** wurde auf PyPI nur als Wheel veröffentlicht, das
   letzte Quell-Archiv trägt 0.19.4. Der Quellcode zu 0.19.5 liegt im Projekt selbst,
   [moses-palmer/pystray](https://github.com/moses-palmer/pystray), Marke `v0.19.5`.
   Das zählt, weil pystray unter LGPLv3 steht und damit tatsächlich eine Pflicht auslöst.
3. **FFmpeg:** Der beigelegte Build stammt nicht von uns. Seine Konfigurations-Zeile
   (`--prefix=/ffbuild/prefix`, crosstool-NG-Werkzeugkette, `--extra-version=20260708`)
   ist die der Windows-Sammelbuilds von
   [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) in der Spielart
   `win64-gpl`; diese Builds sind von der offiziellen
   [FFmpeg-Downloadseite](https://ffmpeg.org/download.html) verlinkt. Das Bau-Rezept
   steht dort in `scripts.d/`, `variants/` und `patches/`. Der FFmpeg-Quellcode selbst
   ist durch die Kennung des Builds eindeutig bestimmt: Git-Stand **`c57660fb18`** im
   [FFmpeg-Repo](https://github.com/FFmpeg/FFmpeg). Ehrlicher Vorbehalt: die genaue
   Herunterlade-Adresse dieser Datei ist nicht protokolliert, und derselbe Bauplan wird
   auch vom Ableger [yt-dlp/FFmpeg-Builds](https://github.com/yt-dlp/FFmpeg-Builds)
   benutzt. Beim nächsten Austausch der Datei gehört die Adresse der geladenen
   Veröffentlichung hier hinein.
4. **Deno:** Quellcode im [Deno-Repo](https://github.com/denoland/deno), Fassung 2.9.2.

Wer die genannten Fassungen nicht selbst holen möchte, bekommt sie auf Nachfrage.
