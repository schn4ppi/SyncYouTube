# -*- coding: utf-8 -*-
"""Programm-Hülle (huelle.py): Ergebnis-Wächter statt Schreibweise.

Befunde vom 24.09.2026 (Analyse „huelle", mit skeptischer Gegenprüfung):

* Hänger beim Neuladen: pywebview baut nach JEDEM Seitenaufbau (auch nach
  location.reload()) das JS-Objekt window.pywebview neu und läuft dafür
  rekursiv über alle öffentlichen Attribute der js_api. Über das öffentliche
  api.video.panel lief es in das .NET-Geflecht des WinForms-Panels
  (Bounds.Empty.Empty…). Dieselbe Falle hatte die Hülle am 07.08. schon einmal
  lahmgelegt (damals über video.fenster.native); der alte Wächter prüfte nur
  die Schreibweise und übersah panel.

Geprüft wird hier das ERGEBNIS: der echte pywebview-Durchlauf (webview.util)
gegen Attrappen der .NET-Module. Das Panel ist ein begrenzter Stolperdraht:
jeder Zugriff auf eine .NET-Eigenschaft zählt und liefert ein frisches Objekt
(wie .NET), ab einer Grenze wirft er. Ohne Grenze hinge die Gegenprobe am
alten Stand, statt rot zu werden: pywebviews Durchlauf-Faden ist kein Daemon,
pytest endete nie.

Nicht hier gemessen: ob der UI-Faden live wirklich stand (GIL + SendMessage
ist eine Vermutung der Analyse). Der Fix entfernt den Durchlauf selbst.
"""
import inspect
import json
import os
import re
import sys
import threading
import types

import pytest

HIER = os.path.dirname(os.path.abspath(__file__))
MODUL_DIR = os.path.dirname(HIER)
for _pfad in (MODUL_DIR, HIER):
    if _pfad not in sys.path:
        sys.path.insert(0, _pfad)

import test_medien_smtc  # noqa: E402  (dieselbe libvlc-Attrappe für die Server-Seite)
from test_medientasten_verhalten import _js_funktion, _lauf, _pc  # noqa: E402

import huelle  # noqa: E402  (Import startet weder Fenster noch Server)
import youtube_app as app  # noqa: E402  (Import startet keinen Server)

vlc_attrappe = test_medien_smtc.vlc_attrappe          # Fixture: nachgebautes python-vlc

HWND = 4242
# Die Abmeldung beim Schließen der Hülle: vergleichen und löschen (nur_wenn)
# und — JB 24.09.2026 „Pausieren" — ein Video in genau diesem Panel anhalten.
ZU = {"cmd": "fenster", "hwnd": 0, "nur_wenn": HWND, "pausieren_wenn_video": True}


# ---------------------------------------------------------------- Attrappen

class Stolperdraht:
    """Ein .NET-Objekt, wie pythonnet es Python zeigt: nicht aufrufbar, mit
    __module__, und jede Eigenschaft liefert ein FRISCHES Objekt derselben Art
    (Bounds.Empty.Empty…, Parent, Controls). Begrenzt: ab GRENZE Zugriffen
    wirft er, damit ein Durchlauf endet (siehe Modul-Doku)."""
    zugriffe = 0
    GRENZE = 60

    def __dir__(self):
        return ["Bounds", "Controls", "Empty", "Parent"]

    def __getattr__(self, name):
        if name.startswith("_"):                     # _serializable & Co.: wie .NET nicht da
            raise AttributeError(name)
        Stolperdraht.zugriffe += 1
        if Stolperdraht.zugriffe > Stolperdraht.GRENZE:
            raise RuntimeError("Stolperdraht: Durchlauf läuft durch das .NET-Geflecht")
        return Stolperdraht()


class Ereignisliste:
    """WinForms-Ereignis (p.MouseMove += handler)."""

    def __init__(self):
        self.handler = []

    def __iadd__(self, f):
        self.handler.append(f)
        return self


class PanelAttrappe(Stolperdraht):
    """System.Windows.Forms.Panel: die Eigenschaften, die huelle.py SETZT,
    sind echt da; alles andere ist Stolperdraht."""

    def __init__(self):
        self.Visible = True
        self.BackColor = None
        self.Location = None
        self.Size = None
        self.MouseMove = Ereignisliste()
        self.MouseDown = Ereignisliste()
        self.Handle = types.SimpleNamespace(ToInt64=lambda: HWND)

    def BringToFront(self):
        pass


class FormAttrappe:
    """Das WinForms-Formular der Hülle: Invoke führt direkt aus und zählt
    (so sieht der Test, ob ein Weg Invoke braucht)."""

    def __init__(self):
        self.panels = []
        self.invokes = 0
        self.Controls = types.SimpleNamespace(Add=self.panels.append)

    def Invoke(self, aktion):
        self.invokes += 1
        aktion()


@pytest.fixture
def dotnet(monkeypatch):
    """System, System.Drawing, System.Windows.Forms als Attrappen (pythonnet
    fehlt im Test oder soll nicht geladen werden)."""
    system = types.ModuleType("System")
    system.Action = lambda f: f
    zeichnen = types.ModuleType("System.Drawing")
    zeichnen.Color = types.SimpleNamespace(Black="schwarz")
    zeichnen.Point = lambda x, y: (x, y)
    zeichnen.Size = lambda w, h: (w, h)
    fenster = types.ModuleType("System.Windows")
    formen = types.ModuleType("System.Windows.Forms")
    formen.Panel = PanelAttrappe
    system.Drawing, system.Windows, fenster.Forms = zeichnen, fenster, formen
    for name, modul in (("System", system), ("System.Drawing", zeichnen),
                        ("System.Windows", fenster), ("System.Windows.Forms", formen)):
        monkeypatch.setitem(sys.modules, name, modul)
    monkeypatch.setattr(Stolperdraht, "zugriffe", 0)


class Netz:
    """urllib.request.urlopen-Attrappe: merkt sich jede Anfrage (Adresse,
    Körper als JSON, Timeout); `fehler` wird bei jeder Anfrage geworfen."""

    def __init__(self, fehler=None):
        self.anfragen = []
        self.fehler = fehler

    def __call__(self, anfrage, timeout=None):
        if isinstance(anfrage, str):
            eintrag = {"url": anfrage, "daten": None}
        else:
            eintrag = {"url": anfrage.full_url,
                       "daten": json.loads(anfrage.data.decode("utf-8")) if anfrage.data else None}
        eintrag["timeout"] = timeout
        eintrag["hauptfaden"] = threading.current_thread() is threading.main_thread()
        self.anfragen.append(eintrag)
        if self.fehler is not None:
            raise self.fehler
        return _Antwort()

    def an_vlc(self):
        return [a["daten"] for a in self.anfragen if a["url"].endswith("/api/vlc")]


class _Antwort:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b"{}"


@pytest.fixture
def netz(monkeypatch):
    n = Netz()
    monkeypatch.setattr(huelle.urllib.request, "urlopen", n)
    return n


def _bruecke_mit_panel(form=None):
    """Bruecke wie in main(), das Panel auf dem ECHTEN Codeweg angelegt
    (video_rect mit an=True, wie die Seite es tut)."""
    api = huelle.Bruecke()
    form = form or FormAttrappe()
    api._fenster = types.SimpleNamespace(native=form)
    assert api.video_rect(0, 0, 10, 10, True) is True
    assert form.panels, "Panel nicht angelegt — der Test prüfte sonst nichts"
    return api, form


class PywebviewFenster:
    """Was webview.util.inject_pywebview (pywebview 6.2.1) von einem Fenster
    liest; run_js merkt sich die eingespeisten Skripte."""

    def __init__(self, js_api):
        self._js_api = js_api
        self._functions = {}
        self._expose_lock = threading.Lock()
        self.uid = "master"
        self.js_api_endpoint = None
        self.text_select = self.zoomable = self.draggable = False
        self.easy_drag = self.frameless = False
        self.state = {}
        self.skripte = []
        self.events = types.SimpleNamespace(before_load=threading.Event(),
                                            loaded=threading.Event(),
                                            _pywebviewready=threading.Event())

    def run_js(self, code):
        self.skripte.append(code)


def _durchlauf(obj, weg="", funde=None, gesehen=None):
    """Nachbau der Regeln aus webview/util.py get_functions (6.2.1), für den
    pywebview-freien Wächter: Namen mit _ und Objekte mit _serializable=False
    überspringen, Methoden sammeln, in jedes andere nicht aufrufbare Objekt mit
    __module__ hinabsteigen."""
    funde = [] if funde is None else funde
    gesehen = set() if gesehen is None else gesehen
    if id(obj) in gesehen:
        return funde
    gesehen.add(id(obj))
    for name in dir(obj):
        if name.startswith("_"):
            continue
        attr = getattr(obj, name)
        if not getattr(attr, "_serializable", True):
            continue
        if inspect.ismethod(attr) or inspect.isfunction(attr):
            funde.append(weg + name)
        elif inspect.isclass(attr) or (not callable(attr) and hasattr(attr, "__module__")):
            _durchlauf(attr, weg + name + ".", funde, gesehen)
    return funde


# ------------------------------------------- Befund 1: Hänger beim Neuladen

def test_pywebview_durchlauf_sieht_nur_die_methoden(dotnet, netz):
    """Der ECHTE pywebview-Durchlauf über die js_api der Hülle, NACHDEM das
    Panel existiert (Lage bei jedem Neuladen): er endet, erreicht das Panel
    nie und bietet der Seite genau die gewollten Methoden an."""
    util = pytest.importorskip("webview.util")      # fehlt es: test_js_api_ohne_daten wacht
    api, _ = _bruecke_mit_panel()
    fenster = PywebviewFenster(api)
    Stolperdraht.zugriffe = 0
    util.inject_pywebview("edgechromium", fenster)
    assert fenster.events.loaded.wait(5), "pywebview-Durchlauf endet nicht (Hänger)"
    m = re.search(r"JSON\.parse\('(.*)'\)\);", fenster.skripte[-1])
    assert m, "finish-Skript ohne Funktionsliste"
    funktionen = sorted(f["func"] for f in json.loads(m.group(1)))
    assert funktionen == ["video_melden", "video_rect"], \
        f"die Seite sieht nicht genau die js_api-Methoden: {funktionen}"
    assert Stolperdraht.zugriffe == 0, \
        f"pywebview lief {Stolperdraht.zugriffe}× durch das .NET-Panel (Rekursionsfalle)"


def test_js_api_ohne_daten(dotnet, netz):
    """Pywebview-frei (läuft auch ohne webview): die js_api trägt außer
    Methoden nichts Öffentliches, und der nachgebaute Durchlauf erreicht kein
    .NET-Objekt."""
    api, _ = _bruecke_mit_panel()
    daten = [n for n in dir(api) if not n.startswith("_") and not callable(getattr(api, n))]
    assert daten == [], f"öffentliche Daten an der js_api (pywebview läuft hinein): {daten}"
    Stolperdraht.zugriffe = 0
    try:
        funde = _durchlauf(api)
    except RuntimeError as e:
        pytest.fail(f"Durchlauf erreicht das .NET-Panel: {e}")
    assert sorted(funde) == ["video_melden", "video_rect"], funde
    assert Stolperdraht.zugriffe == 0


def test_videofenster_bleibt_auch_oeffentlich_draussen(dotnet, netz):
    """Zweite Sicherung: hängt künftig jemand das VideoFenster doch wieder
    öffentlich an die js_api, nimmt pywebviews eigener Schalter
    (_serializable = False) es trotzdem aus dem Durchlauf."""
    util = pytest.importorskip("webview.util")
    api, _ = _bruecke_mit_panel()
    fenster = PywebviewFenster(types.SimpleNamespace(video=api._video))
    Stolperdraht.zugriffe = 0
    util.inject_pywebview("edgechromium", fenster)
    assert fenster.events.loaded.wait(5), "pywebview-Durchlauf endet nicht (Hänger)"
    m = re.search(r"JSON\.parse\('(.*)'\)\);", fenster.skripte[-1])
    assert m and json.loads(m.group(1)) == [], "VideoFenster ist für pywebview sichtbar"


class Ereignis:
    """webview.event.Event mit should_lock=True (before_load, closing):
    Handler laufen SYNCHRON im auslösenden Faden, Aufruf-Regeln wie dort
    (ohne Parameter: f(); mit Parameter window: f(fenster))."""

    def __init__(self, fenster):
        self._fenster = fenster
        self._items = []

    def __add__(self, f):
        self._items.append(f)
        return self

    def set(self):
        for f in self._items:
            parameter = inspect.signature(f).parameters
            if not parameter:
                f()
            elif "window" in parameter:
                f(self._fenster)
            else:
                f()


class HuellenFenster:
    """Rückgabe der webview-Attrappe von create_window."""

    def __init__(self, js_api):
        self.js_api = js_api
        self.native = None
        self.events = types.SimpleNamespace(before_load=Ereignis(self), closing=Ereignis(self),
                                            closed=Ereignis(self), loaded=Ereignis(self))

    def evaluate_js(self, code):
        pass


@pytest.fixture
def webview_attrappe(monkeypatch):
    """webview-Modul-Attrappe: start() spielt das Fensterleben, das der Test
    in `zustand.leben(fenster)` ablegt, und kehrt dann zurück wie pywebview,
    wenn das Fenster zu ist. frueh() (1,5 s Schlaf) läuft hier nicht.
    `zustand.reihe` hält die Reihenfolge fest; die Windows-Kennung wird dabei
    nur verzeichnet, nie am Testprozess gesetzt."""
    modul = types.ModuleType("webview")
    zustand = types.SimpleNamespace(fenster=None, leben=lambda f: None, start_kw=None, reihe=[])

    def create_window(titel, url, js_api=None, **kw):
        zustand.reihe.append("fenster")
        zustand.fenster = HuellenFenster(js_api)
        return zustand.fenster

    def start(func=None, **kw):
        zustand.reihe.append("start")
        zustand.start_kw = kw
        zustand.leben(zustand.fenster)

    modul.create_window, modul.start = create_window, start
    monkeypatch.setitem(sys.modules, "webview", modul)
    monkeypatch.setattr(huelle, "server_starten", lambda: zustand.reihe.append("server") or True)
    monkeypatch.setattr(huelle.windows_kennung, "setze_kennung",
                        lambda **kw: zustand.reihe.append("kennung") or True)
    return zustand


def test_kennung_vor_jedem_fenster(dotnet, netz, webview_attrappe):
    """JB 24.09.2026 „Kennung + Startmenü-Eintrag": die Hülle meldet sich als
    JBK.SyncYouTube, BEVOR ein Fenster entsteht — auch vor server_starten(),
    dessen Fehlermeldung schon ein Fenster ist (Microsoft: vor jeder Oberfläche)."""
    assert huelle.main() == 0
    assert webview_attrappe.reihe == ["kennung", "server", "fenster", "start"]


def test_panel_verschwindet_vor_jedem_seitenaufbau(dotnet, netz, webview_attrappe):
    """location.reload(): das native Panel liegt über der WebView und
    verdeckte die neu ladende Seite. pywebview feuert before_load vor jedem
    Einspeisen im UI-Faden — dort versteckt die Hülle das Panel, direkt und
    ohne Invoke (kein pagehide aus der Seite: das bräuchte einen js_api-Faden
    plus Invoke auf ein womöglich schließendes Formular)."""
    gesehen = {}

    def leben(fenster):
        form = FormAttrappe()
        fenster.native = form
        assert fenster.js_api.video_rect(0, 0, 10, 10, True) is True
        panel = form.panels[0]
        assert panel.Visible is True
        invokes = form.invokes
        fenster.events.before_load.set()                 # pywebview: Seite lädt neu
        gesehen.update(sichtbar=panel.Visible, invokes=form.invokes - invokes)

    webview_attrappe.leben = leben
    assert huelle.main() == 0
    assert gesehen == {"sichtbar": False, "invokes": 0}, gesehen


def test_before_load_vor_dem_panel_ist_harmlos(dotnet, netz, webview_attrappe):
    """Erster Seitenaufbau: before_load kommt, bevor ein Panel existiert."""
    webview_attrappe.leben = lambda fenster: fenster.events.before_load.set()
    assert huelle.main() == 0


# ------------------------------- Befund 2: Abmelden beim Schließen der Hülle

def _leben_mit_panel(fenster):
    """Fensterleben: die Seite meldet eine Video-Fläche, das Panel entsteht."""
    fenster.native = FormAttrappe()
    assert fenster.js_api.video_rect(0, 0, 10, 10, True) is True


def test_anmeldung_traegt_handle_und_pid(dotnet, netz, webview_attrappe):
    """Die Anmeldung trägt das Handle (ein übersehenes self.hwnd legte die
    Einbettung STILL lahm — melden() verschluckt jede Ausnahme) und die PID,
    gegen die der Server wiederverwendete Handles prüft."""
    webview_attrappe.leben = _leben_mit_panel
    assert huelle.main() == 0
    assert netz.an_vlc()[0] == {"cmd": "fenster", "hwnd": HWND, "pid": os.getpid()}


def test_schliessen_meldet_nur_das_eigene_panel_ab(dotnet, netz, webview_attrappe):
    """Fenster zu (webview.start() kehrt zurück): die Hülle meldet ihr Panel
    ab — im Hauptfaden, mit kurzem Timeout, und nur als „vergleichen und
    löschen": der Server nullt nur, wenn noch DIESES Fenster angemeldet ist
    (eine zweite, neuere Hülle bleibt eingebettet). In DERSELBEN Anfrage bittet
    sie, ein Video in ihrem Panel anzuhalten (JB 24.09.: „Pausieren"; was der
    Server daraus macht, prüft der Abschnitt „Hülle zu" unten)."""
    waehrend = []

    def leben(fenster):
        _leben_mit_panel(fenster)
        waehrend.extend(netz.an_vlc())

    webview_attrappe.leben = leben
    assert huelle.main() == 0
    assert all(d.get("hwnd") for d in waehrend), "abgemeldet, solange das Fenster offen war"
    letzte = netz.anfragen[-1]
    assert letzte["daten"] == ZU, letzte
    assert letzte["timeout"] is not None and letzte["timeout"] <= 2, letzte["timeout"]
    assert letzte["hauptfaden"], "Abmelden gehört in den Hauptfaden (nie in den UI-Faden)"


def test_schliessen_ohne_panel_fragt_nichts(dotnet, netz, webview_attrappe):
    """Nie ein Panel angelegt: nichts abzumelden, keine Anfrage."""
    assert huelle.main() == 0
    assert netz.anfragen == []


def test_schliessen_bei_totem_server_endet_trotzdem(dotnet, monkeypatch, webview_attrappe):
    """Server aus: das Abmelden scheitert still, main() endet sofort mit 0."""
    import time
    import urllib.error
    netz = Netz(fehler=urllib.error.URLError("Verbindung abgelehnt"))
    monkeypatch.setattr(huelle.urllib.request, "urlopen", netz)
    webview_attrappe.leben = _leben_mit_panel
    t0 = time.monotonic()
    assert huelle.main() == 0
    assert time.monotonic() - t0 < 3
    assert netz.an_vlc()[-1] == ZU


# ------------------------------------------ Befund 2: Server-Seite (/api/vlc)

@pytest.fixture
def fenster_welt(monkeypatch):
    """Die Fenster-Prüfung des Servers als Attrappe: {hwnd: pid} sind die
    lebenden Fenster. Modelliert beide Unterschiede, um die es geht: tot
    gegen lebend UND lebend, aber einem anderen Prozess gehörend (Windows
    vergibt Handles neu). raising=False: am alten Stand fehlt die Prüfung,
    der Test wird dann am Verhalten rot, nicht am Namen."""
    welt = {}

    def lebt(hwnd, pid=0):
        return hwnd in welt and (not pid or welt[hwnd] == pid)

    monkeypatch.setattr(app, "_hwnd_lebt", lebt, raising=False)
    return welt


def _ruf_index(sp, anfang):
    return next(i for i, r in enumerate(sp.rufe) if r[0] == anfang)


def test_fenster_wird_gemerkt_auch_wenn_vlc_fehlt(monkeypatch, vlc_attrappe, fenster_welt):
    """VLC fehlt beim Anmelden: das Handle wurde bisher verworfen, die Hülle
    hielt es trotzdem für gemeldet (HTTP 200) — ein später installiertes VLC
    bettete nie ein."""
    fenster_welt[HWND] = 77
    monkeypatch.setitem(sys.modules, "vlc", None)                 # VLC (noch) nicht da
    st = app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    assert st["verfuegbar"] is False
    assert app._vlc["hwnd"] == HWND, "Handle verworfen, weil libvlc fehlte"
    monkeypatch.setitem(sys.modules, "vlc", vlc_attrappe)         # VLC nachinstalliert
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    sp = app._vlc["spieler"]
    assert ("hwnd", HWND) in sp.rufe and _ruf_index(sp, "hwnd") < _ruf_index(sp, "play")
    assert st["eingebettet"] is True


def test_abmelden_laedt_libvlc_nicht(monkeypatch, vlc_attrappe):
    """Abmelden (hwnd 0) ohne laufenden Spieler: nur vergessen, libvlc nicht laden."""
    geladen = []
    echt = vlc_attrappe.Instance
    monkeypatch.setattr(vlc_attrappe, "Instance", lambda *a: geladen.append(a) or echt(*a))
    app._vlc["hwnd"] = HWND
    app.vlc_kommando({"cmd": "fenster", "hwnd": 0, "nur_wenn": HWND})
    app.vlc_kommando({"cmd": "fenster", "hwnd": 0})
    assert geladen == [] and app._vlc["spieler"] is None
    assert app._vlc["hwnd"] == 0


def test_abmelden_trifft_nur_das_eigene_fenster(vlc_attrappe, fenster_welt):
    """Zwei Hüllen (oder eine neue, bevor die alte endet): das Schließen der
    alten darf das Panel der neuen nicht abmelden."""
    fenster_welt.update({HWND: 77, 5151: 88})
    app.vlc_kommando({"cmd": "fenster", "hwnd": 5151, "pid": 88})   # die neuere Hülle
    sp = app._vlc["spieler"]
    st = app.vlc_kommando({"cmd": "fenster", "hwnd": 0, "nur_wenn": HWND})   # alte geht zu
    assert app._vlc["hwnd"] == 5151 and st["eingebettet"] is True
    assert ("hwnd", 0) not in sp.rufe
    st = app.vlc_kommando({"cmd": "fenster", "hwnd": 0, "nur_wenn": 5151})   # neue geht zu
    assert app._vlc["hwnd"] == 0 and st["eingebettet"] is False
    assert ("hwnd", 0) in sp.rufe


def test_totes_fenster_wird_vor_dem_start_verworfen(monkeypatch, vlc_attrappe, fenster_welt):
    """Hülle abgestürzt (nie abgemeldet): das nächste Video rendert nicht ins
    tote Fenster, sondern in VLCs eigenes — und Filme bekommen ihr Vollbild
    zurück, das ein gesetztes Handle unterdrückt."""
    monkeypatch.setattr(vlc_attrappe.Spieler, "set_fullscreen",
                        lambda self, an: self.rufe.append(("vollbild", an)), raising=False)
    fenster_welt[HWND] = 77
    app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    sp = app._vlc["spieler"]
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3", "vollbild": True})
    assert st["eingebettet"] is True and ("vollbild", True) not in sp.rufe
    del fenster_welt[HWND]                                        # Hülle weg
    sp.rufe.clear()
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3", "vollbild": True})
    assert ("hwnd", 0) in sp.rufe, "totes Handle nicht verworfen"
    assert _ruf_index(sp, "hwnd") < _ruf_index(sp, "media") < _ruf_index(sp, "play")
    assert st["eingebettet"] is False and app._vlc["hwnd"] == 0
    assert ("vollbild", True) in sp.rufe, "ohne Hülle gehört der Film wieder ins Vollbild"


def test_fremdes_fenster_mit_gleicher_nummer_gilt_als_tot(vlc_attrappe, fenster_welt):
    """Windows hat die Nummer neu vergeben: das Fenster lebt, gehört aber
    einem anderen Prozess — nicht hineinrendern."""
    fenster_welt[HWND] = 77
    app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    fenster_welt[HWND] = 99                                       # fremder Prozess
    st = app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    assert st["eingebettet"] is False and app._vlc["hwnd"] == 0


def test_neuanmeldung_desselben_fensters_laesst_den_spieler_in_ruhe(vlc_attrappe, fenster_welt):
    """Die Seite meldet das Panel vor JEDEM Start neu an (Befund 4): dasselbe
    Fenster noch einmal darf den laufenden Spieler nicht anfassen; ein
    anderes (neue Hülle) wird gesetzt."""
    fenster_welt.update({HWND: 77, 5151: 88})
    app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    sp = app._vlc["spieler"]
    sp.rufe.clear()
    st = app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    assert sp.rufe == [] and st["eingebettet"] is True
    app.vlc_kommando({"cmd": "fenster", "hwnd": 5151, "pid": 88})
    assert sp.rufe == [("hwnd", 5151)]


def test_neuaufbau_setzt_totes_fenster_nicht(vlc_attrappe, fenster_welt):
    """Selbstheilung baut den Spieler neu: ein inzwischen totes Handle wird
    dabei nicht mehr übernommen."""
    fenster_welt[HWND] = 77
    app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    app._vlc_reset()
    del fenster_welt[HWND]
    app.vlc_kommando({"cmd": "play", "key": "abc|mp3"})
    sp = app._vlc["spieler"]
    assert ("hwnd", HWND) not in sp.rufe and app._vlc["hwnd"] == 0


@pytest.mark.skipif(sys.platform != "win32", reason="prüft echte Windows-Fenster")
def test_fensterpruefung_am_echten_fenster():
    """_hwnd_lebt gegen ein ECHTES (unsichtbares, reines Nachrichten-)Fenster
    dieses Prozesses: lebt + eigene PID ja, fremde PID nein, zerstört nein."""
    import ctypes
    from ctypes import wintypes
    u32 = ctypes.WinDLL("user32", use_last_error=True)
    u32.CreateWindowExW.restype = wintypes.HWND
    u32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                    wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                    wintypes.HINSTANCE, wintypes.LPVOID]
    u32.DestroyWindow.argtypes = [wintypes.HWND]
    nur_nachrichten = wintypes.HWND(-3)                           # HWND_MESSAGE
    h = u32.CreateWindowExW(0, "STATIC", "yt-huelle-test", 0, 0, 0, 0, 0,
                            nur_nachrichten, None, None, None)
    assert h, f"Testfenster nicht angelegt (Fehler {ctypes.get_last_error()})"
    try:
        assert app._hwnd_lebt(h, os.getpid()) is True
        assert app._hwnd_lebt(h, 0) is True, "ohne PID (alte Hülle) zählt nur IsWindow"
        assert app._hwnd_lebt(h, os.getppid()) is False, "fremde PID muss als tot gelten"
    finally:
        u32.DestroyWindow(h)
    assert app._hwnd_lebt(h, os.getpid()) is False, "zerstörtes Fenster lebt nicht"
    assert app._hwnd_lebt(0, os.getpid()) is False


# ------------------- Befund 4: Neu-Anmeldung nach einem Server-Selbst-Neustart
# Die Hülle meldete ihr Panel nur EINMAL an. Nach jedem Selbst-Neustart des
# Servers (neuer Backend-Code, Update) ist das Handle dort weg; das erste
# Video danach öffnete VLCs eigenes Fenster, Filme im Vollbild. Die Seite
# meldet darum in der Hülle VOR jedem VLC-Start neu an (video_melden).

def test_video_melden_meldet_erneut(dotnet, netz):
    """melden() ist einmalig; video_melden() setzt das zurück und meldet neu."""
    api, _ = _bruecke_mit_panel()
    assert len(netz.an_vlc()) == 1
    api._video.melden()
    assert len(netz.an_vlc()) == 1, "melden() bleibt einmalig"
    assert api.video_melden() is True
    assert netz.an_vlc() == [{"cmd": "fenster", "hwnd": HWND, "pid": os.getpid()}] * 2


def test_video_melden_legt_fehlendes_panel_an(dotnet, netz):
    """frueh() fand 1,5 s nach dem Start noch kein Formular: dann entsteht das
    Panel beim ersten video_melden, damit schon das erste Video einbettet."""
    api = huelle.Bruecke()
    form = FormAttrappe()
    api._fenster = types.SimpleNamespace(native=form)
    assert api.video_melden() is True
    assert form.panels and form.panels[0].Visible is False, "Panel angelegt, aber unsichtbar"
    assert netz.an_vlc() == [{"cmd": "fenster", "hwnd": HWND, "pid": os.getpid()}]


def test_video_melden_ohne_fenster_und_ohne_server_still(dotnet, monkeypatch):
    """Kein Fenster, Server aus: False, keine Ausnahme (die Seite startet trotzdem)."""
    import urllib.error
    monkeypatch.setattr(huelle.urllib.request, "urlopen",
                        Netz(fehler=urllib.error.URLError("aus")))
    assert huelle.Bruecke().video_melden() is False
    api, _ = _bruecke_mit_panel()
    assert api.video_melden() is False


SEITE = r"""
var plVol=80, tvpWechselGen=0, tvpWechsel=null, tvpModusNaechster=null, tvpModus='browser',
    tvpOffen=false, tvpIdAkt='', tvInfoDaten=null;
const HUELLE_MELDEN_MS=50;                       // statt 3 s: der Test wartet nicht
function toast(t){ _log.push('toast:'+t); }
function tvFilmPlayer(){ _log.push('fernbedienung'); }
async function smtcTaste(){}
globalThis.fetch=async(url,opt)=>{
  const k=opt&&opt.body?JSON.parse(opt.body):{};
  _log.push('fetch:'+url+(k.cmd?':'+k.cmd:''));
  return {json:async()=>({verfuegbar:true, zustand:'spielt'})};
};
function huelle(melden){ window.pywebview={api:Object.assign({video_rect(){}},
  melden?{video_melden:melden}:{})}; }
// Anmeldung wie ein echter js_api-Ruf: fertig erst nach einem Makrotask.
// Ohne await stünde der Start im Protokoll VOR 'gemeldet'.
const langsam=()=>new Promise(r=>setTimeout(()=>{ _log.push('gemeldet'); r(true); },5));
async function fall(f){ _log.length=0; await f(); await new Promise(r=>setTimeout(r,20));
  return _log.slice(); }
"""


def test_seite_meldet_das_panel_vor_jedem_vlc_start(tmp_path):
    """Das ECHTE Seiten-JS (deno): in der Hülle wartet jeder VLC-Start (Musik
    und Video über /api/vlc, Film über /api/filme/play, Live-TV über
    /api/live/play) auf video_melden; ein kaputter, hängender oder fehlender
    Ruf hält den Start nie auf; im Browser passiert nichts Neues."""
    q = _pc()
    teile = _start_zaehler(q) + [_js_funktion(q, n) for n in (
        "huelleMelden", "vlcBefehl", "filmePlayVlc", "tvLivePlay")]
    (e,) = _lauf(tmp_path, SEITE, *teile, r"""
const erg={};
huelle(langsam);
erg.musik=await fall(()=>vlcBefehl('play',{key:'k'}));
erg.status=await fall(()=>vlcBefehl('status'));
erg.film=await fall(()=>filmePlayVlc('f1',0,{titel:'F'},0));
erg.live=await fall(()=>tvLivePlay({url:'u',name:'N'}));
huelle(()=>Promise.reject(new Error('kaputt')));
erg.abgelehnt=await fall(()=>vlcBefehl('play',{key:'k'}));
huelle(()=>{ throw new Error('sofort'); });
erg.wirft=await fall(()=>vlcBefehl('play',{key:'k'}));
huelle(()=>new Promise(()=>{}));
erg.haengt=await fall(()=>vlcBefehl('play',{key:'k'}));
huelle(null);
erg.alte_huelle=await fall(()=>vlcBefehl('play',{key:'k'}));
delete globalThis.pywebview;
erg.browser=await fall(()=>vlcBefehl('play',{key:'k'}));
erg.browser_film=await fall(()=>filmePlayVlc('f1',0,{titel:'F'},0));
aus(erg);
""")
    assert e["musik"] == ["gemeldet", "fetch:/api/vlc:play"], e["musik"]
    assert e["status"] == ["fetch:/api/vlc:status"], "nur Starts melden an, nicht der Takt"
    assert e["film"] == ["gemeldet", "fetch:/api/filme/play", "fernbedienung"], e["film"]
    assert e["live"] == ["gemeldet", "fetch:/api/live/play", "fernbedienung"], e["live"]
    for fall in ("abgelehnt", "wirft", "haengt", "alte_huelle", "browser"):
        assert e[fall] == ["fetch:/api/vlc:play"], (fall, e[fall])
    assert e["browser_film"] == ["fetch:/api/filme/play", "fernbedienung"], e["browser_film"]


def _start_zaehler(q):
    """Die Zähler-Zeile der Seite (überholte VLC-Starts), falls es sie gibt — am
    alten Stand fehlt sie, dann läuft der Rot-Lauf ohne sie."""
    m = re.search(r"^let vlcStartGen.*$", q, re.M)
    return [m.group(0)] if m else []


WETTLAUF = r"""
var plVol=80, tvpWechselGen=0, tvpWechsel=null, tvpModusNaechster=null, tvpModus='browser',
    tvpOffen=false, tvpIdAkt='', tvInfoDaten=null;
const HUELLE_MELDEN_MS=3000;
const spur=[]; let serverKey='';                 // der EINE VLC am PC
function toast(t){ spur.push('toast:'+t); }
function tvFilmPlayer(id,titel){ spur.push('fernbedienung:'+(id||titel)); }
async function smtcTaste(){}
globalThis.fetch=async(url,opt)=>{
  const k=opt&&opt.body?JSON.parse(opt.body):{};
  if(url==='/api/filme/play'){ serverKey='film:'+k.id; spur.push('server-play:'+k.id); }
  else if(url==='/api/live/play'){ serverKey='live:'+k.name; spur.push('server-live:'+k.name); }
  else if(url==='/api/vlc'&&k.cmd==='play'){ serverKey=k.key; spur.push('server-play:'+k.key); }
  else if(url==='/api/vlc'&&k.cmd==='stop'){ serverKey=''; spur.push('server-stop'); }
  return {json:async()=>({verfuegbar:true, zustand:'spielt', key:serverKey})};
};
// Jede Anmeldung ist ein eigener js_api-Faden: wann sie zurückkehrt, ist offen.
const dauern=[];
window.pywebview={api:{video_rect(){}, video_melden(){ const ms=dauern.shift();
  return new Promise(r=>setTimeout(()=>r(true),ms)); }}};
const warte=ms=>new Promise(r=>setTimeout(r,ms));
function folge(id){ const gen=++tvpWechselGen; tvpWechsel={gen,id};
  return filmePlayVlc(id,0,{titel:id},gen); }
async function fall(f){ spur.length=0; serverKey=''; await f(); await warte(60);
  return {spur:spur.slice(), key:serverKey}; }
"""


def test_ueberholter_start_in_der_huelle_wuergt_den_neueren_nicht_ab(tmp_path):
    """Prüfung Runde 1 (mittel): Seit d44a709 wartet jeder VLC-Start in der Hülle
    auf video_melden (bis 3 s, je Anmeldung ein eigener js_api-Faden). Kehrt
    die ältere Anmeldung NACH der jüngeren zurück, startete der ältere Titel
    als letzter. Gemessen am alten Stand: zwei Folgenwechsel A, B — VLC spielte
    B, dann A, dann stoppte der Überholt-Schutz A: VLC aus, die Oberfläche
    zeigte die Fernbedienung von B. Jetzt schickt ein Start, der während der
    Anmeldung überholt wurde (neuerer Start, Esc, Stopp), gar nichts."""
    q = _pc()
    teile = _start_zaehler(q) + [_js_funktion(q, n) for n in (
        "huelleMelden", "vlcBefehl", "filmePlayVlc", "tvLivePlay")]
    (e,) = _lauf(tmp_path, WETTLAUF, *teile, r"""
const erg={};
dauern.push(40,5);                                   // A meldet langsam, B schnell
erg.folgen=await fall(async()=>{ const a=folge('A'); await warte(10); await Promise.all([a,folge('B')]); });
dauern.push(40);                                     // Esc (filmStopp zählt hoch) während A meldet
erg.esc=await fall(async()=>{ const a=filmePlayVlc('A',0,{titel:'A'}); await warte(10);
  tvpWechselGen++; await a; });
dauern.push(40,5);
erg.musik=await fall(async()=>{ const a=vlcBefehl('play',{key:'m1'}); await warte(10);
  const r=await Promise.all([a,vlcBefehl('play',{key:'m2'})]); spur.push('erster:'+JSON.stringify(r[0])); });
dauern.push(40);                                     // Gerät gewechselt / Liste leer: stop während m1 meldet
erg.stopp=await fall(async()=>{ const a=vlcBefehl('play',{key:'m1'}); await warte(10);
  await Promise.all([a,vlcBefehl('stop')]); });
dauern.push(40,5);
erg.live=await fall(async()=>{ const a=tvLivePlay({url:'u1',name:'L1'}); await warte(10);
  await Promise.all([a,tvLivePlay({url:'u2',name:'L2'})]); });
aus(erg);
""")
    assert e["folgen"] == {"spur": ["server-play:B", "fernbedienung:B"], "key": "film:B"}, e["folgen"]
    assert e["esc"] == {"spur": [], "key": ""}, e["esc"]
    assert e["musik"] == {"spur": ["server-play:m2", "erster:null"], "key": "m2"}, e["musik"]
    assert e["stopp"] == {"spur": ["server-stop"], "key": ""}, e["stopp"]
    assert e["live"] == {"spur": ["server-live:L2", "fernbedienung:L2"], "key": "live:L2"}, e["live"]


def test_gleichzeitige_anmeldungen_legen_genau_ein_panel_an(dotnet, netz, monkeypatch):
    """Prüfung Runde 1 (niedrig): vorbereiten() (frueh), setzen() (video_rect)
    und video_melden() prüfen `if not self._hwnd` und legen danach ohne Sperre
    an — jeder in seinem eigenen Faden. Überlappen sich zwei, bevor ein Panel
    existiert, entstehen ZWEI Panels, und der Server behält womöglich das
    unsichtbare. Die Attrappe modelliert den Unterschied: jedes Panel hat seine
    eigene Handle-Nummer, und Invoke hat EINEN UI-Faden, der gerade beschäftigt
    ist, bis beide Rufe angekommen sind (höchstens 0,5 s)."""
    nummern = iter(range(5001, 5100))

    class ZaehlPanel(PanelAttrappe):
        def __init__(self):
            super().__init__()
            n = next(nummern)
            self.Handle = types.SimpleNamespace(ToInt64=lambda: n)
    monkeypatch.setattr(sys.modules["System.Windows.Forms"], "Panel", ZaehlPanel)

    class BeschaeftigteForm(FormAttrappe):
        def __init__(self):
            super().__init__()
            self._ui = threading.Lock()
            self._beide = threading.Barrier(2, timeout=0.5)

        def Invoke(self, aktion):
            self.invokes += 1
            try:
                self._beide.wait()
            except threading.BrokenBarrierError:
                pass
            with self._ui:
                aktion()

    for zweiter in ("video_rect", "frueh"):
        api = huelle.Bruecke()
        form = BeschaeftigteForm()
        api._fenster = types.SimpleNamespace(native=form)
        netz.anfragen.clear()
        wege = {"video_rect": lambda: api.video_rect(0, 0, 10, 10, True),
                "frueh": lambda: api._video.vorbereiten(form)}
        faeden = [threading.Thread(target=api.video_melden),
                  threading.Thread(target=wege[zweiter])]
        for f in faeden:
            f.start()
        for f in faeden:
            f.join(5)
        assert not any(f.is_alive() for f in faeden), "Hänger"
        gemeldet = {d["hwnd"] for d in netz.an_vlc()}
        assert len(form.panels) == 1, (zweiter, f"{len(form.panels)} Panels angelegt")
        assert gemeldet == {api._video._hwnd}, (zweiter, gemeldet, api._video._hwnd)


# -------- Hülle zu, während darin ein Video über VLC läuft (JB 24.09.2026)
# JB: „Pausieren" (Musik läuft in jedem Fall weiter). Bisher meldete die Hülle
# ihr Panel nur ab: das Video lief im Server-VLC weiter, sein Bild ins
# zerstörte Panel — hörbar, aber unsichtbar. Jetzt entscheidet der Server in
# DERSELBEN Anfrage, unter derselben Sperre (kein Wettlauf zwischen
# Status-Abfrage und Pause): läuft ein VIDEO in genau DIESES Panel, pausiert er
# es — pausiert, nicht gestoppt, die Stelle bleibt. Musik, ein Video in VLCs
# eigenem Fenster und eines im Panel einer anderen Hülle bleiben unberührt.
#
# Die Attrappe modelliert den Unterschied, auf den es ankommt: set_hwnd wirkt
# erst beim NÄCHSTEN Medium (libvlc). Ein Video, das vor der Anmeldung eines
# Panels startete, bleibt in VLCs eigenem Fenster, auch wenn das Handle danach
# gesetzt ist — „eingebettet" im Status sagt darum nicht, wohin das LAUFENDE
# Bild geht.

FILM = {"key": "film:f1", "url": "http://jellyfin.test/strom"}
LIVE = {"key": "live:Das Erste", "url": "http://live.test/strom"}


@pytest.fixture
def video(vlc_attrappe, tmp_path):
    """Ein Bibliotheks-Video (dieselbe Grenze wie die Seite: die Datei ist
    keine Audio-Datei, dateiart 'video')."""
    datei = tmp_path / "clip.mp4"
    datei.write_bytes(b"x" * 10)
    app._geladen["vid|beste"] = {"pfad": str(datei), "titel": "Ein Video"}
    return {"key": "vid|beste"}


def _spielt_im_panel(fenster_welt, start):
    """Panel angemeldet, DANACH gestartet: das Bild geht ins Panel."""
    fenster_welt[HWND] = 77
    app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    st = app.vlc_kommando({"cmd": "play", **start})
    assert st["zustand"] == "spielt" and st["eingebettet"] is True, st
    sp = app._vlc["spieler"]
    sp.rufe.clear()
    return sp


def _angehalten(sp):
    return [r for r in sp.rufe if r[0] in ("pause", "toggle", "stop")]


@pytest.mark.parametrize("art", ["bibliothek", "film", "live"])
def test_huelle_zu_pausiert_das_video_in_ihrem_panel(video, fenster_welt, art):
    """Bibliotheks-Video, Jellyfin-Film und Live-TV im Panel: pausiert (nicht
    gestoppt — der Titel bleibt geladen, JB kann an der Stelle weiter), und
    das Panel ist abgemeldet."""
    start = {"bibliothek": video, "film": FILM, "live": LIVE}[art]
    sp = _spielt_im_panel(fenster_welt, start)
    st = app.vlc_kommando(dict(ZU))
    assert _angehalten(sp) == [("pause", 1)], f"{art}: {sp.rufe}"
    assert st["zustand"] == "pause", f"{art}: das Video läuft ins zerstörte Panel weiter"
    assert app._vlc["hwnd"] == 0 and st["eingebettet"] is False
    assert app._vlc["key"] == start["key"], "gestoppt statt pausiert"


def test_huelle_zu_laesst_musik_weiterspielen(vlc_attrappe, fenster_welt):
    """Musik (Audio-Datei) im Gerät VLC: läuft weiter, nur das Panel geht."""
    sp = _spielt_im_panel(fenster_welt, {"key": "abc|mp3"})
    st = app.vlc_kommando(dict(ZU))
    assert _angehalten(sp) == [], sp.rufe
    assert st["zustand"] == "spielt" and app._vlc["hwnd"] == 0


def test_huelle_zu_pausiert_kein_video_einer_anderen_huelle(video, fenster_welt):
    """Das Video läuft im Panel einer anderen (neueren) Hülle, die alte geht
    zu: nichts pausieren, nichts abmelden."""
    fenster_welt.update({HWND: 77, 5151: 88})
    app.vlc_kommando({"cmd": "fenster", "hwnd": 5151, "pid": 88})
    app.vlc_kommando({"cmd": "play", **video})
    sp = app._vlc["spieler"]
    sp.rufe.clear()
    st = app.vlc_kommando(dict(ZU))
    assert sp.rufe == [] and st["zustand"] == "spielt"
    assert app._vlc["hwnd"] == 5151 and st["eingebettet"] is True


def test_huelle_zu_haelt_ein_video_in_vlcs_eigenem_fenster_nicht_an(video, fenster_welt):
    """Das Video lief schon, bevor die Hülle ihr Panel anmeldete (etwa ein
    Film vom Handy, im Vollbild): set_hwnd wirkt erst beim nächsten Medium,
    das Bild ist in VLCs eigenem Fenster und bleibt beim Schließen der Hülle
    sichtbar — nicht anhalten, obwohl der Status 'eingebettet' meldet."""
    fenster_welt[HWND] = 77
    app.vlc_kommando({"cmd": "play", **FILM})
    st = app.vlc_kommando({"cmd": "fenster", "hwnd": HWND, "pid": 77})
    assert st["eingebettet"] is True
    sp = app._vlc["spieler"]
    sp.rufe.clear()
    st = app.vlc_kommando(dict(ZU))
    assert _angehalten(sp) == [] and st["zustand"] == "spielt", sp.rufe
    assert app._vlc["hwnd"] == 0


def test_huelle_zu_pausiert_ihr_video_auch_nach_anmeldung_einer_neuen(video, fenster_welt):
    """Das Video läuft im Panel der alten Hülle; eine neue meldet sich an (ihr
    Handle gilt erst ab dem nächsten Medium). Die alte geht zu: ihr Video
    pausiert, die Anmeldung der neuen bleibt."""
    sp = _spielt_im_panel(fenster_welt, video)
    fenster_welt[5151] = 88
    app.vlc_kommando({"cmd": "fenster", "hwnd": 5151, "pid": 88})
    sp.rufe.clear()
    st = app.vlc_kommando(dict(ZU))
    assert _angehalten(sp) == [("pause", 1)], sp.rufe
    assert app._vlc["hwnd"] == 5151 and st["eingebettet"] is True


@pytest.mark.parametrize("zustand", ["O", "B"])                  # Opening, Buffering
def test_huelle_zu_pausiert_auch_ein_ladendes_video(video, fenster_welt, zustand):
    """Ein Film, der gerade öffnet oder puffert (Jellyfin-Strom), läuft
    gleich weiter — ins zerstörte Panel. Auch er wird angehalten."""
    sp = _spielt_im_panel(fenster_welt, FILM)
    sp.zustand = zustand
    app.vlc_kommando(dict(ZU))
    assert _angehalten(sp) == [("pause", 1)], sp.rufe


def test_huelle_zu_setzt_ein_pausiertes_video_nicht_fort(video, fenster_welt):
    """Schon pausiert: bleibt pausiert (ein Umschalten per toggle hätte es
    gerade beim Schließen fortgesetzt)."""
    sp = _spielt_im_panel(fenster_welt, video)
    app.vlc_kommando({"cmd": "pause"})
    sp.rufe.clear()
    st = app.vlc_kommando(dict(ZU))
    assert st["zustand"] == "pause" and ("toggle",) not in sp.rufe and ("pause", 0) not in sp.rufe


def test_abmelden_ohne_pausen_wunsch_haelt_nichts_an(video, fenster_welt):
    """Der Wunsch kommt nur von der schließenden Hülle: eine Abmeldung ohne
    ihn (ältere Hülle) meldet nur ab, wie bisher."""
    sp = _spielt_im_panel(fenster_welt, video)
    st = app.vlc_kommando({"cmd": "fenster", "hwnd": 0, "nur_wenn": HWND})
    assert _angehalten(sp) == [] and st["zustand"] == "spielt" and app._vlc["hwnd"] == 0


class ServerNetz(Netz):
    """urlopen-Attrappe, die /api/vlc an den ECHTEN Server-Befehl reicht
    (im selben Prozess): der Test prüft den Vertrag zwischen Hülle und Server
    am Ergebnis — spielt das Video nach dem Schließen noch?"""

    def __call__(self, anfrage, timeout=None):
        antwort = super().__call__(anfrage, timeout)
        letzte = self.anfragen[-1]
        if letzte["url"].endswith("/api/vlc") and letzte["daten"]:
            app.vlc_kommando(letzte["daten"])
        return antwort


@pytest.mark.parametrize("art", ["video", "musik"])
def test_huelle_schliessen_pausiert_video_und_laesst_musik(dotnet, monkeypatch, webview_attrappe,
                                                           video, fenster_welt, art):
    """Ende zu Ende: die Hülle legt ihr Panel an und meldet es an, ein Titel
    startet hinein, das Fenster geht zu (webview.start kehrt zurück). Danach
    ist das Panel abgemeldet; ein Video steht auf Pause, Musik spielt weiter."""
    netz = ServerNetz()
    monkeypatch.setattr(huelle.urllib.request, "urlopen", netz)
    fenster_welt[HWND] = os.getpid()                             # das Panel lebt in DIESEM Prozess
    start = video if art == "video" else {"key": "abc|mp3"}

    def leben(fenster):
        _leben_mit_panel(fenster)
        st = app.vlc_kommando({"cmd": "play", **start})
        assert st["eingebettet"] is True and st["zustand"] == "spielt", st

    webview_attrappe.leben = leben
    assert huelle.main() == 0
    st = app.vlc_status()
    assert app._vlc["hwnd"] == 0, "Panel nicht abgemeldet"
    assert st["zustand"] == ("pause" if art == "video" else "spielt"), (art, st["zustand"])
