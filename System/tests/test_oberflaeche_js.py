# -*- coding: utf-8 -*-
"""Wächter für die Oberfläche (oberflaeche.py, JS inline): jede Top-Level-Funktion,
die `info` benutzt, muss `info` auch selbst deklarieren (Parameter, const/let
oder Zuweisung). Befund SyncYouTube-12, 06.09.2026: Der Fehler-Rekorder hielt
nur »Promise: ReferenceError: info is not defined« fest, ohne Ort. Undeklariert
lasen `info` damals zwei Funktionen, `plSyncNow()` und `ordnerImportieren()`;
beide sind in 3b6a084 repariert. Ausgelöst hat den Eintrag sehr wahrscheinlich
`plSyncNow()` (Playlist-Menü „⇄ Jetzt synchronisieren“): Nach dem Sync warf
die Erfolgsmeldung, der catch-Zweig warf noch einmal, die Liste wurde nicht
neu geladen. `ordnerImportieren()` hatte seit Build 122 (60a55df, 23.07.2026)
keinen Aufrufer mehr und konnte gar nicht laufen. (Berichtigt in der
Gesamtprüfung 25.09.2026; vorher stand hier `ordnerImportieren()` als Ursache.)
Auto-Discovery über alle Funktionen, kein Netz, kein Server (P6/P7)."""
import os
import re

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUELLE = os.path.join(MODUL_DIR, "oberflaeche.py")
_FUNKTIONS_KOPF = re.compile(r"^(?:async )?function\s+(\w+)\s*\(([^)]*)\)", re.M)
# Echte Bezeichner-Nutzung: nicht Teil von `tv-info`, `.info`, `'plinfo'`, `#info`.
_NUTZUNG = re.compile(r"(?<![\w\-.'\"#$])info(?![\w\-])")
_DEKLARIERT = re.compile(r"\b(?:const|let|var)\s+info\b|\binfo\s*=[^=]|\binfo\s*,|,\s*info\s*=")


def _funktionen(text):
    """(Name, Parameter, Rumpf) je Top-Level-Funktion — der Rumpf reicht bis zum
    nächsten Funktionskopf (Spalte 0), das genügt für den Deklarations-Blick."""
    koepfe = list(_FUNKTIONS_KOPF.finditer(text))
    for i, k in enumerate(koepfe):
        ende = koepfe[i + 1].start() if i + 1 < len(koepfe) else len(text)
        yield k.group(1), k.group(2), text[k.end():ende]


def _undeklarierte_info_nutzer(text):
    treffer = []
    for name, params, rumpf in _funktionen(text):
        if not _NUTZUNG.search(rumpf):
            continue
        if _NUTZUNG.search(params) or _DEKLARIERT.search(rumpf):
            continue
        treffer.append(name)
    return treffer


def test_gegenprobe_undeklariertes_info_wird_gefunden():
    kaputt = ("function a(){ const info=1; if(info)x(); }\n"
              "async function b(){ try{ if(info)info.textContent='x'; }catch(e){} }\n"
              "function c(info){ info.x=1; }\n")
    assert _undeklarierte_info_nutzer(kaputt) == ["b"]


def test_jede_funktion_deklariert_ihr_info():
    with open(QUELLE, encoding="utf-8") as f:
        text = f.read()
    schuldige = _undeklarierte_info_nutzer(text)
    assert not schuldige, (
        f"`info` wird ohne Deklaration benutzt in: {schuldige} — im Browser ein "
        "ReferenceError, den der Rekorder nur ohne Ort festhält (Befund SyncYouTube-12)")
