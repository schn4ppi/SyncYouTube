# -*- coding: utf-8 -*-
"""Windows-Kennung von SyncYouTube (JB 24.09.2026: „Kennung + Startmenü-Eintrag").

Ohne eigene App-Kennung ordnet Windows einen pythonw-Prozess per Heuristik der
einzigen Startmenü-Verknüpfung auf pythonw.exe zu: „IDLE (Python 3.14)"
(gemessen 23.09. an der Medien-Sitzung des Servers). Zwei Teile beheben das:

* setze_kennung(): der Prozess meldet sich als JBK.SyncYouTube. Früh in main()
  rufen, bevor ein Fenster entsteht (Microsoft: „before the application
  presents any UI"). Gilt je Prozess; Kindprozesse erben sie nicht.
* startmenue_eintrag(): die Verknüpfung „SyncYouTube" im Startmenü des
  Nutzers mit derselben Kennung. Über sie findet Windows zur Kennung Namen und
  Symbol. Idempotent, und eine fremde Verknüpfung gleichen Namens (ohne diese
  Kennung) bleibt unberührt.

Nur ctypes (kein pywin32/comtypes). Alles fail-safe: ein Fehlschlag wird
protokolliert und reißt nie den Start. Importiert nichts aus dem Programm.
"""
import ctypes
import functools
import os
import sys
import threading
import uuid

KENNUNG = "JBK.SyncYouTube"
NAME = "SyncYouTube"
BESCHREIBUNG = "SyncYouTube: YouTube-Downloader und Player"

_CLSID_SHELLLINK = "00021401-0000-0000-C000-000000000046"
_IID_SHELLLINKW = "000214F9-0000-0000-C000-000000000046"
_IID_PERSISTFILE = "0000010B-0000-0000-C000-000000000046"
_IID_PROPERTYSTORE = "886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"
_FMTID_APPUSERMODEL = "9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"    # PKEY_AppUserModel_ID = (…, 5)
_VT_LPWSTR = 31
_PUFFER = 32768


def _ohne_protokoll(text):
    pass


def setze_kennung(log=None, shell32=None):
    """Den eigenen Prozess als JBK.SyncYouTube melden. True, wenn Windows es
    angenommen hat; sonst False und ein Protokolleintrag — nie eine Ausnahme.
    shell32 nur für Tests."""
    log = log or _ohne_protokoll
    try:
        if shell32 is None:
            shell32 = ctypes.windll.shell32
        hr = shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(KENNUNG))
        if int(hr) < 0:
            log(f"Windows-Kennung {KENNUNG} nicht gesetzt (HRESULT {int(hr) & 0xFFFFFFFF:#010x})")
            return False
        return True
    except Exception as e:                                # noqa: BLE001 — nie den Start reißen
        log(f"Windows-Kennung {KENNUNG} nicht gesetzt: {e}")
        return False


def startziel(frozen, executable, skript_dir):
    """Was die Verknüpfung startet: dasselbe wie der gewohnte Start.
    exe: die exe selbst. Quellbetrieb: pythonw.exe neben dem laufenden Python
    (SyncDashTray-venv wie SyncYouTube.bat, oder das eingebettete Python des
    Quellstart-Pakets) mit youtube_app.py — pythonw, damit keine Konsole aufgeht.
    Arbeitsordner: der Programmordner der App (System\\ bzw. neben der exe)."""
    executable = os.path.abspath(executable)
    if frozen:
        return {"ziel": executable, "argumente": "",
                "arbeitsordner": os.path.dirname(executable), "symbol": (executable, 0)}
    ordner, name = os.path.split(executable)
    if name.lower() == "python.exe":
        executable = os.path.join(ordner, "pythonw.exe")
    skript_dir = os.path.abspath(skript_dir)
    return {"ziel": executable,
            "argumente": '"' + os.path.join(skript_dir, "youtube_app.py") + '"',
            "arbeitsordner": skript_dir, "symbol": (executable, 0)}


def startmenue_ordner():
    """Startmenü-Programme des angemeldeten Nutzers (kein Admin nötig)."""
    appdata = os.environ.get("APPDATA")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs") if appdata else None


def startmenue_eintrag(ordner=None, ziel=None, log=None, faden=False):
    """Die Verknüpfung „SyncYouTube" anlegen oder nachziehen.

    Ergebnis: "angelegt", "aktualisiert", "unveraendert", "behalten" (eigener
    Eintrag mit einem anderen, noch startbaren Ziel — s. unten), "fremd" (eine
    Verknüpfung gleichen Namens ohne unsere Kennung — bleibt unberührt),
    "kein_ziel" (nichts Startbares) oder "fehler". Protokolliert werden nur
    Probleme. Geschrieben wird über eine Zwischendatei im selben Ordner und
    os.replace: ein Abbruch hinterlässt nie eine halbe Verknüpfung, die beim
    nächsten Start als „fremd" gälte. faden=True: im eigenen Hintergrundfaden
    (eigenes COM-Apartment, der Start wartet nicht); gibt den Faden zurück.
    ordner/ziel nur für Tests und Sonderfälle.

    EINE stabile Regel (Prüfung Runde 2): das Ziel eines eigenen Eintrags
    wechselt nur, wenn das bisherige nicht mehr startet (Programm verschoben,
    exe entfernt). Vorher gewann der letzte Start: ein einziger Start der exe
    (Datenordner = ihr eigener Ordner) stellte den Eintrag auf einen anderen
    Datenbestand um, ein Start mit dem Basis-Python auf ein Python ohne die
    venv-Pakete — bis der nächste Quellstart ihn zurückstellte."""
    if faden:
        t = threading.Thread(target=startmenue_eintrag, name="startmenue-eintrag", daemon=True,
                             kwargs={"ordner": ordner, "ziel": ziel, "log": log})
        t.start()
        return t
    log = log or _ohne_protokoll
    try:
        ordner = ordner or startmenue_ordner()
        if not ordner or not os.path.isdir(ordner):
            log(f"Startmenü-Eintrag: Ordner fehlt ({ordner})")
            return "fehler"
        soll = ziel or startziel(getattr(sys, "frozen", False), sys.executable,
                                 os.path.dirname(os.path.abspath(__file__)))
        if not os.path.isfile(soll["ziel"]):
            log(f"Startmenü-Eintrag: {soll['ziel']} fehlt, kein Eintrag angelegt")
            return "kein_ziel"
        pfad = os.path.join(ordner, NAME + ".lnk")
        with _Apartment():
            ergebnis = "angelegt"
            if os.path.lexists(pfad):
                ist = _lesen(pfad)
                if ist is None or ist["kennung"] != KENNUNG:
                    log(f"Startmenü: {pfad} gehört nicht zu SyncYouTube und bleibt unverändert")
                    return "fremd"
                if _gleich(ist, soll):
                    return "unveraendert"
                if not _gleiches_ziel(ist, soll) and _startbar(ist):
                    return "behalten"
                ergebnis = "aktualisiert"
            zwischen = pfad + ".neu"
            _schreiben(zwischen, soll)
            os.replace(zwischen, pfad)
        return ergebnis
    except Exception as e:                                # noqa: BLE001 — nie den Start reißen
        log(f"Startmenü-Eintrag nicht möglich: {e}")
        return "fehler"


def _pfad(p):
    return os.path.normcase(os.path.normpath(p)) if p else ""


def _gleiches_ziel(ist, soll):
    """Startet der Eintrag dasselbe (Programm, Argumente, Arbeitsordner)?"""
    return (_pfad(ist["ziel"]) == _pfad(soll["ziel"])
            and ist["argumente"] == soll["argumente"]
            and _pfad(ist["arbeitsordner"]) == _pfad(soll["arbeitsordner"]))


def _startbar(ist):
    """Startet der vorhandene Eintrag noch? Das Programm liegt da, und im
    Quellbetrieb auch das Skript aus den Argumenten (youtube_app.py)."""
    if not ist.get("ziel") or not os.path.isfile(ist["ziel"]):
        return False
    skript = (ist.get("argumente") or "").strip().strip('"')
    return not skript.lower().endswith(".py") or os.path.isfile(skript)


def _gleich(ist, soll):
    return (_gleiches_ziel(ist, soll)
            and ist["beschreibung"] == BESCHREIBUNG
            and _pfad(ist["symbol"][0]) == _pfad(soll["symbol"][0])
            and ist["symbol"][1] == soll["symbol"][1])


# ---------------------------------------------------------------- COM per ctypes

class _GUID(ctypes.Structure):
    _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort), ("d3", ctypes.c_ushort),
                ("d4", ctypes.c_ubyte * 8)]


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_ulong)]


class _PROPVARIANT(ctypes.Structure):
    # vt + 3 reservierte WORDs, dann die Werte-Union (hier: der Zeiger pwszVal).
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort),
                ("r3", ctypes.c_ushort), ("wert", ctypes.c_void_p), ("rest", ctypes.c_void_p)]


def _guid(text):
    return _GUID.from_buffer_copy(uuid.UUID(text).bytes_le)


@functools.lru_cache(maxsize=None)
def _ole32():
    # Eigene WinDLL-Instanz: restype/argtypes hier ändern nichts an ctypes.windll.ole32.
    d = ctypes.WinDLL("ole32")
    d.CoInitializeEx.restype = ctypes.c_long        # S_FALSE / RPC_E_CHANGED_MODE ohne Ausnahme
    d.CoCreateInstance.restype = ctypes.HRESULT
    d.PropVariantClear.restype = ctypes.HRESULT
    return d


def _methode(zeiger, index, *argtypes, restype=ctypes.HRESULT):
    """Methode Nr. index aus der vtable einer COM-Schnittstelle (HRESULT < 0 wirft OSError)."""
    vtbl = ctypes.cast(zeiger, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    funktion = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtbl[index])
    return lambda *args: funktion(zeiger, *args)


def _abfragen(zeiger, iid):
    """IUnknown::QueryInterface."""
    ziel = ctypes.c_void_p()
    _methode(zeiger, 0, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))(
        ctypes.byref(_guid(iid)), ctypes.byref(ziel))
    return ziel


def _freigeben(*zeiger):
    """IUnknown::Release für jeden gültigen Zeiger."""
    for z in zeiger:
        if z is not None and z.value:
            _methode(z, 2, restype=ctypes.c_ulong)()


def _shelllink():
    zeiger = ctypes.c_void_p()
    _ole32().CoCreateInstance(ctypes.byref(_guid(_CLSID_SHELLLINK)), None, 1,  # CLSCTX_INPROC_SERVER
                              ctypes.byref(_guid(_IID_SHELLLINKW)), ctypes.byref(zeiger))
    return zeiger


def _kennung_schluessel():
    return _PROPERTYKEY(_guid(_FMTID_APPUSERMODEL), 5)


class _Apartment:
    """COM für diesen Faden einrichten und — nur wenn WIR es eingerichtet haben —
    wieder abmelden. Ein Faden mit anderem Apartment (RPC_E_CHANGED_MODE) geht
    auch: CShellLink ist für beide Modelle registriert."""

    def __enter__(self):
        self._abmelden = _ole32().CoInitializeEx(None, 2) in (0, 1)   # COINIT_APARTMENTTHREADED
        return self

    def __exit__(self, *fehler):
        if self._abmelden:
            _ole32().CoUninitialize()
        return False


# IShellLinkW-vtable: 3 GetPath · 6 GetDescription · 7 SetDescription ·
# 8 GetWorkingDirectory · 9 SetWorkingDirectory · 10 GetArguments · 11 SetArguments ·
# 16 GetIconLocation · 17 SetIconLocation · 20 SetPath.
# IPersistFile: 5 Load · 6 Save.  IPropertyStore: 5 GetValue · 6 SetValue · 7 Commit.

def _lesen(pfad):
    """Die vorhandene Verknüpfung lesen; None, wenn sie keine lesbare Verknüpfung ist."""
    link = _shelllink()
    datei = store = None
    try:
        datei = _abfragen(link, _IID_PERSISTFILE)
        try:
            _methode(datei, 5, ctypes.c_wchar_p, ctypes.c_ulong)(pfad, 0)      # STGM_READ
        except OSError:
            return None
        W, N = ctypes.c_wchar_p, ctypes.c_int

        def text(index):
            puffer = ctypes.create_unicode_buffer(_PUFFER)
            _methode(link, index, W, N)(puffer, _PUFFER)
            return puffer.value
        ziel = ctypes.create_unicode_buffer(_PUFFER)
        _methode(link, 3, W, N, ctypes.c_void_p, ctypes.c_ulong)(ziel, _PUFFER, None, 0x4)  # SLGP_RAWPATH
        symbol, symbol_nr = ctypes.create_unicode_buffer(_PUFFER), ctypes.c_int()
        _methode(link, 16, W, N, ctypes.POINTER(ctypes.c_int))(symbol, _PUFFER, ctypes.byref(symbol_nr))
        ist = {"ziel": ziel.value, "beschreibung": text(6), "arbeitsordner": text(8),
               "argumente": text(10), "symbol": (symbol.value, symbol_nr.value)}
        store = _abfragen(link, _IID_PROPERTYSTORE)
        wert = _PROPVARIANT()
        _methode(store, 5, ctypes.POINTER(_PROPERTYKEY), ctypes.POINTER(_PROPVARIANT))(
            ctypes.byref(_kennung_schluessel()), ctypes.byref(wert))
        try:
            ist["kennung"] = (ctypes.wstring_at(wert.wert)
                              if wert.vt == _VT_LPWSTR and wert.wert else None)
        finally:
            _ole32().PropVariantClear(ctypes.byref(wert))
        return ist
    finally:
        _freigeben(store, datei, link)


def _schreiben(pfad, soll):
    """Neue Verknüpfung mit Ziel, Argumenten, Arbeitsordner, Beschreibung,
    Symbol und System.AppUserModel.ID nach pfad speichern."""
    link = _shelllink()
    datei = store = None
    W = ctypes.c_wchar_p
    try:
        _methode(link, 20, W)(soll["ziel"])
        _methode(link, 11, W)(soll["argumente"])
        _methode(link, 9, W)(soll["arbeitsordner"])
        _methode(link, 7, W)(BESCHREIBUNG)
        _methode(link, 17, W, ctypes.c_int)(soll["symbol"][0], soll["symbol"][1])
        store = _abfragen(link, _IID_PROPERTYSTORE)
        text = ctypes.create_unicode_buffer(KENNUNG)
        wert = _PROPVARIANT(vt=_VT_LPWSTR, wert=ctypes.addressof(text))
        _methode(store, 6, ctypes.POINTER(_PROPERTYKEY), ctypes.POINTER(_PROPVARIANT))(
            ctypes.byref(_kennung_schluessel()), ctypes.byref(wert))    # SetValue kopiert
        _methode(store, 7)()
        datei = _abfragen(link, _IID_PERSISTFILE)
        _methode(datei, 6, W, ctypes.c_int)(pfad, 1)
    finally:
        _freigeben(store, datei, link)
