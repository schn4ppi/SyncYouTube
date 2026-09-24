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

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import huelle  # noqa: E402  (Import startet weder Fenster noch Server)

HWND = 4242


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
    assert funktionen == ["video_rect"], \
        f"die Seite sieht mehr als die js_api-Methoden: {funktionen}"
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
    assert sorted(funde) == ["video_rect"], funde
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
    wenn das Fenster zu ist. frueh() (1,5 s Schlaf) läuft hier nicht."""
    modul = types.ModuleType("webview")
    zustand = types.SimpleNamespace(fenster=None, leben=lambda f: None, start_kw=None)

    def create_window(titel, url, js_api=None, **kw):
        zustand.fenster = HuellenFenster(js_api)
        return zustand.fenster

    def start(func=None, **kw):
        zustand.start_kw = kw
        zustand.leben(zustand.fenster)

    modul.create_window, modul.start = create_window, start
    monkeypatch.setitem(sys.modules, "webview", modul)
    monkeypatch.setattr(huelle, "server_starten", lambda: True)
    return zustand


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
