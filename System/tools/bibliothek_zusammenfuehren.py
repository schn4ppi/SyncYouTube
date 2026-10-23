# -*- coding: utf-8 -*-
"""Exe-Daten additiv nach System übernehmen; ohne --apply ausschließlich lesen.

Aufruf: python System/tools/bibliothek_zusammenfuehren.py --programm PROGRAMMORDNER
Erst den JSON-Bericht prüfen. --apply sichert geladen_log.json unverändert und
schreibt unter der familie-Sperre. Andere Dateien werden nur verglichen.
Zähler verwenden das Maximum: Die beiden Historien können sich überlappen;
blindes Addieren würde bei jedem erneuten Lauf Wiedergaben erfinden.
"""
import argparse
import copy
import datetime
import errno
import json
import ntpath
import os
from pathlib import Path
import socket
import subprocess
import sys

SYSTEM = Path(__file__).resolve().parents[1]
if str(SYSTEM) not in sys.path:
    sys.path.insert(0, str(SYSTEM))
import familie as fam  # noqa: E402


class ZusammenfuehrungAbgelehnt(Exception):
    """Im Zweifel bleibt der Datenbestand unverändert."""


def _lesen(pfad):
    try:
        roh = pfad.read_bytes()
        return json.loads(roh.decode("utf-8-sig")), roh
    except (OSError, UnicodeError, ValueError) as fehler:
        raise ZusammenfuehrungAbgelehnt(f"{pfad}: nicht sicher lesbar: {fehler}") from fehler


def _vorhanden(wert):
    return wert is not None and wert != "" and wert != [] and wert != {}


def _zaehler(feld):
    return feld in ("plays", "play_count", "aufrufe") or feld.endswith(("_count", "_zaehler"))


def _zahl(wert):
    return isinstance(wert, (int, float)) and not isinstance(wert, bool)


def _vollstaendigkeit(eintrag):
    return sum(_vorhanden(wert) for feld, wert in eintrag.items()
               if not _zaehler(feld) and feld not in ("ts", "last_play"))


def _verbinden(ziel, quelle):
    """Vollständigere Metadaten gewinnen, fehlende Felder und Unterfelder bleiben."""
    quelle_gewinnt = _vollstaendigkeit(quelle) > _vollstaendigkeit(ziel)
    konflikte = []

    def felder(a, b, vorsilbe=""):
        ergebnis = copy.deepcopy(a)
        for feld, wert in b.items():
            name = vorsilbe + feld
            if feld == "importiert":
                # Fehlend bedeutet im gewachsenen Log: regulärer Download.
                # Ein Reimport darf diese Herkunft nicht nachträglich ändern.
                if bool(wert) != bool(a.get(feld, False)):
                    konflikte.append({"feld": name, "ziel": a.get(feld, False),
                                      "quelle": wert, "gewaehlt": a.get(feld, False)})
                continue
            if feld not in a or not _vorhanden(a[feld]):
                ergebnis[feld] = copy.deepcopy(wert)
            elif not _vorhanden(wert) or a[feld] == wert:
                continue
            elif isinstance(a[feld], dict) and isinstance(wert, dict):
                ergebnis[feld] = felder(a[feld], wert, name + ".")
            else:
                if feld in ("pfad", "fp"):
                    # Ein gleicher Schlüssel kann versehentlich den Fingerprint
                    # seiner Clips tragen. Bekannte Zielidentität nie umbiegen.
                    pass
                elif _zahl(a[feld]) and _zahl(wert) and (_zaehler(feld) or feld == "last_play"):
                    ergebnis[feld] = max(a[feld], wert)
                elif feld == "ts" and _zahl(a[feld]) and _zahl(wert) and min(a[feld], wert) > 0:
                    ergebnis[feld] = min(a[feld], wert)
                elif quelle_gewinnt:
                    ergebnis[feld] = copy.deepcopy(wert)
                konflikte.append({"feld": name, "ziel": a[feld], "quelle": wert,
                                  "gewaehlt": ergebnis[feld]})
        return ergebnis

    return felder(ziel, quelle), konflikte


def _identitaeten(eintrag):
    if eintrag.get("pfad"):
        yield "pfad", ntpath.normcase(ntpath.normpath(eintrag["pfad"]))
    if eintrag.get("fp"):
        yield "fp", eintrag["fp"]


def _bibliothek(daten, pfad):
    if not isinstance(daten, dict) or any(not isinstance(e, dict) for e in daten.values()):
        raise ZusammenfuehrungAbgelehnt(f"{pfad}: erwartet ein Objekt aus Bibliothekseinträgen")
    for key, eintrag in daten.items():
        for feld in ("pfad", "fp"):
            if feld in eintrag and eintrag[feld] is not None and not isinstance(eintrag[feld], str):
                raise ZusammenfuehrungAbgelehnt(f"{pfad}: {key}: {feld} ist kein Text")


def _abweichungen(quelle, ziel, vorsilbe=""):
    """Nur Feldnamen berichten; Konfiguration kann Zugangsdaten enthalten."""
    if isinstance(quelle, dict) and isinstance(ziel, dict):
        namen = []
        for key in sorted(quelle.keys() | ziel.keys()):
            if key not in quelle or key not in ziel:
                namen.append(vorsilbe + key)
            else:
                namen.extend(_abweichungen(quelle[key], ziel[key], vorsilbe + key + "."))
        return namen
    return [] if quelle == ziel else [vorsilbe.rstrip(".") or "gesamter Inhalt"]


def planen(programm):
    programm = Path(programm).resolve()
    system = programm / "System"
    quelle = programm / "geladen_log.json"
    ziel = system / quelle.name
    if not system.is_dir() or quelle.resolve() == ziel.resolve():
        raise ZusammenfuehrungAbgelehnt("Quelle und System-Ziel müssen getrennte vorhandene Orte sein")
    q, q_roh = _lesen(quelle)
    z, z_roh = _lesen(ziel)
    _bibliothek(q, quelle)
    _bibliothek(z, ziel)
    neu = copy.deepcopy(z)
    index = {}

    def indexieren(key, eintrag):
        for identitaet in _identitaeten(eintrag):
            index.setdefault(identitaet, set()).add(key)

    for key, eintrag in neu.items():
        indexieren(key, eintrag)
    bericht = {"programm": str(programm), "modus": "Probelauf", "quelle_eintraege": len(q),
               "ziel_eintraege": len(z), "neu": [], "dubletten": [], "konflikte": [],
               "aktualisiert": [], "nicht_uebernommen": [], "andere_dateien": [],
               "regel": "Vollständigere Metadaten; bei Gleichstand System. Zähler/last_play Maximum, "
                        "ts frühester Wert. Bekannte Zielpfade/Fingerprints bleiben. Neue ohne Datei "
                        "werden übersprungen. Abweichende Zähler bei getrennten Historien manuell prüfen."}
    for key, eintrag in q.items():
        treffer = {key} if key in neu else set()
        for identitaet in _identitaeten(eintrag):
            treffer.update(index.get(identitaet, ()))
        if len(treffer) > 1 and key not in neu:
            bericht["konflikte"].append({"quelle": key, "ziele": sorted(treffer),
                                         "aktion": "mehrdeutig; wird übersprungen"})
            bericht["nicht_uebernommen"].append(key)
            continue
        if not treffer:
            if not eintrag.get("pfad") or not Path(eintrag["pfad"]).is_file():
                bericht["konflikte"].append({"quelle": key, "pfad": eintrag.get("pfad"),
                    "aktion": "unbekannter Eintrag, Datei fehlt; separat prüfen, wird übersprungen"})
                bericht["nicht_uebernommen"].append(key)
                continue
            neu[key] = copy.deepcopy(eintrag)
            indexieren(key, eintrag)
            bericht["neu"].append(key)
            continue
        ziel_key = key if key in neu else next(iter(treffer))
        bericht["dubletten"].append({"quelle": key, "ziel": ziel_key})
        verbunden, konflikte = _verbinden(neu[ziel_key], eintrag)
        if konflikte or len(treffer) > 1:
            konflikt = {"quelle": key, "ziel": ziel_key, "felder": konflikte}
            if len(treffer) > 1:
                konflikt["weitere_pfad_fp_treffer"] = sorted(treffer - {ziel_key})
                konflikt["hinweis"] = "Exakter Schlüssel hat Vorrang; andere Einträge bleiben getrennt."
            bericht["konflikte"].append(konflikt)
        if verbunden != neu[ziel_key]:
            neu[ziel_key] = verbunden
            indexieren(ziel_key, verbunden)
            bericht["aktualisiert"].append(ziel_key)
    namen = sorted({p.name for ort in (programm, system) for p in ort.glob("*.json")}
                   - {"geladen_log.json"})
    for name in namen:
        a, b = programm / name, system / name
        if not a.exists() or not b.exists():
            if a.exists():
                bericht["andere_dateien"].append({"datei": name, "unterschied": "fehlt in System",
                    "vorschlag": "Inhalt und Schema separat prüfen; keine automatische Übernahme."})
            continue
        try:
            qa, _ = _lesen(a)
            zb, _ = _lesen(b)
            unterschied = _abweichungen(qa, zb)
        except ZusammenfuehrungAbgelehnt as fehler:
            unterschied = [str(fehler)]
        if unterschied:
            if name == "warteschlange.json":
                vorschlag = "Aufträge einzeln nach URL/Qualität prüfen; erledigte Aufträge nicht erneut starten."
            elif name.startswith("filme_"):
                vorschlag = "Film-IDs und Zeitstände separat vergleichen; Bibliothek/Anmeldedaten nicht ersetzen."
            elif name == "config.json":
                vorschlag = "Nur ausdrücklich gewünschte Einstellungen feldweise nach System übertragen."
            else:
                vorschlag = "Inhalt und Schema separat prüfen; keine automatische Übernahme."
            bericht["andere_dateien"].append({"datei": name, "abweichende_felder": unterschied,
                                              "vorschlag": vorschlag})
    bericht["ergebnis_eintraege"] = len(neu)
    bericht["anzahl"] = {name: len(bericht[name]) for name in ("neu", "dubletten", "konflikte")}
    return {"bericht": bericht, "quelle": quelle, "ziel": ziel, "q_roh": q_roh,
            "z_roh": z_roh, "ziel_daten": z, "ergebnis": neu}


_PROZESS_ABFRAGE = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$prozesse = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -ieq 'SyncYouTube.exe' -or
    $_.CommandLine -match '(?i)(?:^|[\\/\s"''])youtube_app\.py(?=[\s"'']|$)' -or
    ($_.Name -match '^python.*\.exe$' -and -not $_.CommandLine)
} | ForEach-Object { "$($_.Name) (PID $($_.ProcessId))" })
ConvertTo-Json -InputObject $prozesse -Compress
"""


def stillstand_pruefen():
    """Keine Prozesse beenden, keine HTTP-Anfrage; unsichere Prüfung verweigert --apply."""
    if os.name != "nt":
        raise ZusammenfuehrungAbgelehnt("--apply benötigt die Windows-Prozessprüfung")
    try:
        lauf = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                               _PROZESS_ABFRAGE], capture_output=True, encoding="utf-8",
                              timeout=20, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        prozesse = json.loads(lauf.stdout.lstrip("\ufeff"))
        if not isinstance(prozesse, list):
            raise ValueError("Prozessantwort ist keine Liste")
    except (OSError, ValueError, subprocess.SubprocessError) as fehler:
        raise ZusammenfuehrungAbgelehnt(f"Prozesse nicht sicher prüfbar: {fehler}") from fehler
    if prozesse:
        raise ZusammenfuehrungAbgelehnt("SyncYouTube/Python läuft: " + ", ".join(prozesse))
    for familie, adresse in ((socket.AF_INET, ("0.0.0.0", 8776)),
                             (socket.AF_INET6, ("::", 8776))):
        try:
            with socket.socket(familie, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                sock.bind(adresse)
        except OSError as fehler:
            if familie == socket.AF_INET6 and fehler.errno in (errno.EAFNOSUPPORT, errno.EPROTONOSUPPORT):
                continue
            raise ZusammenfuehrungAbgelehnt(f"Port 8776 belegt oder nicht sicher prüfbar: {fehler}") from fehler


def anwenden(plan):
    stillstand_pruefen()
    if plan["ergebnis"] == plan["ziel_daten"]:
        return None
    sicherung = None

    def schreiben(aktuell):
        nonlocal sicherung
        stillstand_pruefen()
        if (aktuell != plan["ziel_daten"] or plan["ziel"].read_bytes() != plan["z_roh"]
                or plan["quelle"].read_bytes() != plan["q_roh"]):
            raise ZusammenfuehrungAbgelehnt("Bestand seit dem Probelauf geändert; erneut prüfen")
        zeit = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        sicherung = plan["ziel"].with_name(plan["ziel"].name + f".vor-zusammenfuehrung-{zeit}.bak")
        with sicherung.open("xb") as datei:
            datei.write(plan["z_roh"])
            datei.flush()
            os.fsync(datei.fileno())
        return plan["ergebnis"]

    if fam.json_aendern(str(plan["ziel"]), schreiben, streng=True) is None:
        raise ZusammenfuehrungAbgelehnt(f"Sperre oder Schreiben fehlgeschlagen; Sicherung: {sicherung}")
    return sicherung


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--programm", type=Path, default=SYSTEM.parent)
    parser.add_argument("--apply", action="store_true", help="nach Sicherung ausschließlich geladen_log.json ändern")
    args = parser.parse_args(argv)
    try:
        plan = planen(args.programm)
        if args.apply:
            sicherung = anwenden(plan)
            plan["bericht"]["modus"] = "Angewendet"
            plan["bericht"]["sicherung"] = str(sicherung) if sicherung else "keine Änderung nötig"
        print(json.dumps(plan["bericht"], ensure_ascii=False, indent=2))
        return 0
    except (ZusammenfuehrungAbgelehnt, OSError) as fehler:
        print(f"Abgelehnt: {fehler}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
