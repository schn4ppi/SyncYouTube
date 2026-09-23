# -*- coding: utf-8 -*-
"""Werkstatt (nie im Auslieferungsweg): Medientasten und Windows-Medien-Overlay MESSEN.

Entstanden 23.09.2026 bei der Prüfung der Medientasten. Die Seite selbst kann
nicht sehen, was Windows aus ihrer Media Session macht — erst so gemessen fiel
auf, dass Chromium das Album unterschlägt, dass ein abgelöstes Medienelement
einen toten „pausiert"-Eintrag hält und wem Windows die Tasten gibt. Dieses
Werkzeug fragt deshalb Windows' EIGENE Sitzungsliste ab
(GlobalSystemMediaTransportControlsSessionManager — dieselbe Quelle wie das
Medien-Overlay und die Medienkarte in den Schnelleinstellungen).

  python medien_probe.py liste
      Alle Medien-Sitzungen als JSON: App, aktuell (bekommt die Tasten),
      Titel, Interpret, Album, Zustand, Zeitleiste, freigeschaltete Knöpfe.
  python medien_probe.py taste next|prev|pp|stop [--nur-wenn APP-TEIL]
      Drückt eine Medientaste per SendInput: virtuelle Taste + der Scan-Code,
      den eine Tastatur über den HID-Treiber liefert (E0 19 / E0 10 / E0 22 /
      E0 24). Unterschied zu einem Finger auf der Taste: Windows markiert den
      Druck als „injiziert". Mit --nur-wenn wird NUR gedrückt, wenn Windows
      diese App gerade als aktuelle Sitzung führt.
  python medien_probe.py knopf next|prev|play|pause|toggle|stop|seek:SEK APP-TEIL
      Ein Overlay-Knopf gezielt an EINE Sitzung (Try*Async) — derselbe Weg wie
      ein Klick im Windows-Overlay, erreicht keine andere App.

VORSICHT (gemessen 23.09.2026): Eine Medientaste geht an die aktuelle Sitzung
— und Spotify pausiert bei Play/Pause zusätzlich SELBST mit, solange es spielt.
Wer auf JBs PC Tasten drückt, fragt vorher (Spotify läuft dort oft) und prüft
mit `liste` unmittelbar davor, wer aktuell ist. Knöpfe nur an die eigene
Test-Sitzung, nie an fremde Apps.
"""
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes

# PowerShell 5.1 kann WinRT direkt nutzen — kein zusätzliches Paket nötig.
_PS = r"""
param([string]$Befehl = "", [string]$Wer = "")
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$gen = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$typ) { $t = $gen.MakeGenericMethod($typ).Invoke($null, @($op)); $null = $t.Wait(5000); return $t.Result }
$null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType = WindowsRuntime]
$MP = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties]
$mgr = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
$cur = $mgr.GetCurrentSession(); $curId = ""; $curTitel = ""
if ($cur) { $curId = $cur.SourceAppUserModelId; try { $curTitel = (Await ($cur.TryGetMediaPropertiesAsync()) $MP).Title } catch {} }
if ($Befehl) {
    $ziel = $mgr.GetSessions() | Where-Object { $_.SourceAppUserModelId -like "*$Wer*" } | Select-Object -First 1
    if (-not $ziel) { Write-Output (@{ fehler = "keine Sitzung passt zu '$Wer'" } | ConvertTo-Json -Compress); exit 2 }
    $op = switch ($Befehl) {
        "next" { $ziel.TrySkipNextAsync() } "prev" { $ziel.TrySkipPreviousAsync() }
        "play" { $ziel.TryPlayAsync() } "pause" { $ziel.TryPauseAsync() }
        "toggle" { $ziel.TryTogglePlayPauseAsync() } "stop" { $ziel.TryStopAsync() }
        default { if ($Befehl -like "seek:*") { $ziel.TryChangePlaybackPositionAsync([long]([double]$Befehl.Substring(5) * 10000000)) } } }
    Write-Output (@{ befehl = $Befehl; wer = $ziel.SourceAppUserModelId; angenommen = (Await $op ([bool])) } | ConvertTo-Json -Compress)
    exit 0
}
$liste = @()
foreach ($s in $mgr.GetSessions()) {
    $p = $null; try { $p = Await ($s.TryGetMediaPropertiesAsync()) $MP } catch {}
    $pb = $s.GetPlaybackInfo(); $tl = $s.GetTimelineProperties(); $c = $pb.Controls
    $liste += [ordered]@{
        app = $s.SourceAppUserModelId
        aktuell = (($s.SourceAppUserModelId -eq $curId) -and ((-not $p) -or ($p.Title -eq $curTitel)))
        titel = if ($p) { $p.Title } else { $null }; interpret = if ($p) { $p.Artist } else { $null }
        album = if ($p) { $p.AlbumTitle } else { $null }; hat_bild = [bool]($p -and $p.Thumbnail)
        zustand = "$($pb.PlaybackStatus)"
        position_s = [math]::Round($tl.Position.TotalSeconds, 1); ende_s = [math]::Round($tl.EndTime.TotalSeconds, 1)
        stand = $tl.LastUpdatedTime.ToLocalTime().ToString("HH:mm:ss")
        knoepfe = [ordered]@{ play = $c.IsPlayEnabled; pause = $c.IsPauseEnabled; stop = $c.IsStopEnabled
                              weiter = $c.IsNextEnabled; zurueck = $c.IsPreviousEnabled; position = $c.IsPlaybackPositionEnabled } }
}
Write-Output (ConvertTo-Json -InputObject @($liste) -Depth 4)
"""

TASTEN = {"next": (0xB0, 0x19), "prev": (0xB1, 0x10), "stop": (0xB2, 0x24), "pp": (0xB3, 0x22)}


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _U(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def _ps(*args):
    """Das PowerShell-Skript als Skriptblock laufen lassen — ohne Datei auf der
    Platte (die Werkstatt hinterlässt nichts). -EncodedCommand statt stdin:
    über stdin verschluckt PowerShell mehrzeilige Skriptblöcke still."""
    import base64
    aufruf = "& {" + _PS + "} " + " ".join(f"'{a}'" for a in args)
    kodiert = base64.b64encode(aufruf.encode("utf-16-le")).decode("ascii")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-EncodedCommand", kodiert], capture_output=True, timeout=60)
    out = r.stdout.decode("utf-8", "replace").strip()
    try:
        return json.loads(out)
    except ValueError:
        return {"fehler": (out or r.stderr.decode("utf-8", "replace"))[-800:]}


def liste():
    return _ps()


def knopf(befehl, wer):
    return _ps("-Befehl", befehl, "-Wer", wer)


def taste(name):
    vk, scan = TASTEN[name]
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)
    feld = (_INPUT * 2)()
    for i, flags in enumerate((0x0001, 0x0001 | 0x0002)):     # EXTENDEDKEY, dann KEYUP
        feld[i].type = 1
        feld[i].u.ki = _KEYBDINPUT(vk, scan, flags, 0, 0)
    n = user32.SendInput(2, feld, ctypes.sizeof(_INPUT))
    return {"taste": name, "gesendet": n}


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    was = argv[1] if len(argv) > 1 else "liste"
    if was == "liste":
        erg = liste()
    elif was == "taste":
        if "--nur-wenn" in argv:
            wer = argv[argv.index("--nur-wenn") + 1].lower()
            akt = [s for s in liste() if s.get("aktuell")]
            if not akt or wer not in akt[0]["app"].lower():
                print(json.dumps({"abgebrochen": "nicht die aktuelle Sitzung — kein Druck",
                                  "aktuell": akt[0]["app"] if akt else None}, ensure_ascii=False))
                return 1
        erg = taste(argv[2])
        time.sleep(1.5)
        erg = {"druck": erg, "danach": liste()}
    elif was == "knopf":
        erg = knopf(argv[2], argv[3])
        time.sleep(1.2)
        erg = {"knopf": erg, "danach": liste()}
    else:
        print(__doc__)
        return 2
    print(json.dumps(erg, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
