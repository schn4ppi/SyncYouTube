# -*- coding: utf-8 -*-
"""Programm-Hülle (Medienzentrale-Spec Stufe 2, JB-Go 05.08.2026: „Dann lass
die Programm-Hülle jetzt angehen. go").

Eigenes Fenster statt Browser-Tab: lädt die BESTEHENDE Oberfläche vom lokalen
Server (ein Gesicht, zwei Zugänge — der Server bleibt derselbe, das Handy
erreicht ihn weiter über den Browser/die gehostete Seite). Läuft der Server
noch nicht, startet die Hülle ihn selbst und wartet, bis er antwortet.

Bedienung: F11 = Vollbild (TV-Modus-Grundlage; die eigene TV-Design-Runde
folgt laut Spec separat). Fenster zu = nur die Hülle endet, der Server läuft
weiter (Downloads und Musik im VLC laufen weiter — bewusst, wie der
Browser-Tab vorher). Nur ein Video, das gerade in IHR Panel spielt, hält der
Server beim Schließen an (JB 24.09.2026: „Pausieren"; sonst liefe es hörbar,
aber unsichtbar weiter).

VLC-Video: Die Hülle bettet das Bild des VLC-Motors in ein WinForms-Panel
dieses Fensters ein und meldet es dem Server über /api/vlc (Befehl
`fenster`, siehe Bruecke/_video unten).

Adresse: Der Port kommt aus der config.json des Servers neben dieser Datei
(dort legt der Quellstart seine Einstellungen ab), Rückfall 8776 (F25).
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

import windows_kennung

STANDARD_PORT = 8776
CONFIG_PFAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _port():
    """Port aus der config.json des Servers; bei fehlender, kaputter oder
    unsinniger Angabe 8776 (F25: vorher fest 8776, ein anderer Port in den
    Einstellungen ließ die Hülle ins Leere laufen)."""
    try:
        with open(CONFIG_PFAD, encoding="utf-8") as f:
            port = int(json.load(f).get("port") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return STANDARD_PORT
    return port if 0 < port < 65536 else STANDARD_PORT


def adresse():
    return f"http://127.0.0.1:{_port()}"


def server_laeuft(timeout=2):
    try:
        with urllib.request.urlopen(f"{adresse()}/api/status", timeout=timeout):
            return True
    except Exception:                                # noqa: BLE001 — aus/startet noch
        return False


def server_starten():
    """Den bestehenden App-Server starten (falls aus) — gleiche Startform wie
    der Tray (pythonw, --no-browser, cwd = SyncYouTube-Wurzel)."""
    if server_laeuft():
        return True
    hier = os.path.dirname(os.path.abspath(__file__))
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    subprocess.Popen([pythonw, os.path.join(hier, "youtube_app.py"), "--no-browser"],
                     cwd=os.path.dirname(hier),
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(60):                              # bis ~12 s warten
        if server_laeuft():
            return True
        time.sleep(0.2)
    return False


class VideoFenster:
    """Etappe set_hwnd (JB-Go 05.08.): ein natives Kind-Fenster IM
    Hüllen-Fenster, in das der Server-VLC sein Video rendert — das Video ist
    damit Teil des Players statt eines separaten VLC-Fensters (Fernseher!).
    Die Oberfläche meldet die Ziel-Fläche über die js_api (video_rect)."""

    # WICHTIG (Hüllen-Hänger 07.08. + 24.09.): pywebview läuft nach JEDEM
    # Seitenaufbau (auch location.reload()) rekursiv über alle öffentlichen
    # Attribute der js_api. Über ein öffentliches WinForms-Objekt (07.08.:
    # fenster.native, 24.09.: panel) gerät es in .NET-Selbstbezüge
    # (Bounds.Empty.Empty…) und endet nie. Darum ist hier ALLES privat
    # (_unterstrich), und dieser Schalter nimmt das ganze Objekt zusätzlich
    # aus dem Durchlauf (pywebviews eigener Ausschluss, webview/util.py).
    # Wächter: tests/test_huelle.py fährt den echten Durchlauf.
    _serializable = False

    def __init__(self):
        self._hwnd = 0
        self._panel = None
        self._gemeldet = False                       # hwnd schon an den Server?
        self._fenster = None                         # pywebview-Fenster (Maus-Weiterleitung)
        # EINE Anlage zur Zeit (Prüfung Runde 1): frueh(), video_rect und
        # video_melden laufen je in einem eigenen Faden; zwei gleichzeitige
        # Rufe legten zwei Panels an, und der Server behielt womöglich das
        # unsichtbare. Kein Deadlock: der UI-Faden nimmt diese Sperre nie
        # (Invoke wartet auf ihn, er nicht auf uns).
        self._anlage_sperre = threading.Lock()

    def _anlegen(self, form):
        # WICHTIG (live gemessen): ein rohes CreateWindowExW aus dem js_api-
        # Worker-Thread stirbt mit seinem Thread — ein Fenster gehört seinem
        # Erzeuger-Thread. Darum ein WinForms-Panel, per Invoke im UI-Thread
        # des Formulars angelegt: es lebt so lange wie das Hüllen-Fenster.
        from System import Action                    # pythonnet (pywebview[winforms])
        from System.Drawing import Color

        def tu():
            from System.Windows.Forms import Panel
            p = Panel()
            p.BackColor = Color.Black
            p.Visible = False
            form.Controls.Add(p)
            p.BringToFront()                         # ÜBER der WebView (Video-Fläche)
            # JB-Fund 06.08. („Wenn ich mit maus über den screen hover, dann
            # sollte auch die bar angezeigt werden"): das NATIVE Panel liegt
            # über der WebView — Mausbewegungen übers Video erreichen das
            # Browser-Overlay nie. Darum reicht die Hülle sie selbst weiter:
            # Bewegung weckt die Leiste (gedrosselt), Klick = Pause/Weiter
            # (Netflix-Verhalten).
            p.MouseMove += lambda s, e: self._js("tvpWach&&tvpWach()", 0.3)
            p.MouseDown += lambda s, e: self._js(
                "tvpWach&&tvpWach();vlcBefehl&&vlcBefehl('toggle')", 0)
            self._panel = p
            self._hwnd = int(p.Handle.ToInt64())
        form.Invoke(Action(tu))
        return self._hwnd

    def _panel_sichern(self, form):
        """Panel anlegen, falls noch keins da ist — Prüfung und Anlage unter
        EINER Sperre (die zweite Prüfung darin sieht das Panel des ersten)."""
        with self._anlage_sperre:
            if not self._hwnd:
                self._anlegen(form)
        return self._hwnd

    def _js(self, code, drossel_s):
        """JS in der Oberfläche ausführen (best-effort, MouseMove gedrosselt).
        WICHTIG: nie auf dem WinForms-UI-Thread blocken — evaluate_js wartet
        auf die WebView, die gerade den UI-Thread braucht (Deadlock-Fund der
        Nachtprüfung). Darum feuert ein kleiner Daemon-Thread den Ruf ab."""
        jetzt = time.time()
        if drossel_s and jetzt - getattr(self, "_js_zuletzt", 0.0) < drossel_s:
            return
        self._js_zuletzt = jetzt
        fenster = self._fenster
        if fenster is None:
            return

        def tu():
            try:
                fenster.evaluate_js(code)
            except Exception:                        # noqa: BLE001 — Weck-Ruf ist Kür
                pass
        threading.Thread(target=tu, daemon=True).start()

    def vorbereiten(self, form):
        """Beim Hüllen-START Panel + hwnd anlegen und melden (JB-Fund: „Player
        ist nicht unten im film" — der Server kannte das Fenster beim ersten
        Play noch nicht und öffnete VLCs EIGENES Vollbild; das Panel blieb
        schwarz). Früh gemeldet = jeder Film rendert von Anfang an IM Fenster."""
        try:
            self._panel_sichern(form)
            self.melden()
        except Exception:                            # noqa: BLE001 — Kür
            pass

    def melden(self):
        """Das Handle EINMAL an den Server geben (überlebt dort auch die
        VLC-Selbstheilung); scheitert der Abruf, beim nächsten Rect erneut."""
        if self._gemeldet or not self._hwnd:
            return
        try:
            # pid: der Server prüft vor jedem Einbetten, ob das Fenster noch
            # lebt UND diesem Prozess gehört (Windows vergibt Handles neu).
            with self._an_server({"cmd": "fenster", "hwnd": self._hwnd,
                                  "pid": os.getpid()}, timeout=3):
                self._gemeldet = True
        except Exception:                            # noqa: BLE001 — nächster Versuch folgt
            pass

    def abmelden(self):
        """Hülle zu: das Panel beim Server abmelden (Befund 24.09.: sonst
        zeigte _vlc['hwnd'] auf ein zerstörtes Fenster — das nächste Video
        renderte ins Leere, Filme verloren ihr Vollbild). 'nur_wenn' =
        vergleichen und löschen: der Server nullt nur, solange noch DIESES
        Fenster angemeldet ist; eine zweite offene Hülle bleibt eingebettet.
        'pausieren_wenn_video' (JB 24.09.2026: „Pausieren"): spielt gerade
        ein Video in DIESES Panel, hält der Server es an — er entscheidet das
        in derselben Anfrage unter seiner VLC-Sperre (kein Wettlauf zwischen
        Status-Abfrage und Pause); Musik läuft weiter.
        Läuft nach webview.start() im Hauptfaden — nie im closing-Handler,
        der synchron im UI-Faden läuft (fröre das Fenster bis zum Timeout
        ein). Server aus = nichts abzumelden, Fehler still."""
        if not self._hwnd:
            return
        try:
            with self._an_server({"cmd": "fenster", "hwnd": 0, "nur_wenn": self._hwnd,
                                  "pausieren_wenn_video": True}, timeout=2):
                pass
        except Exception:                            # noqa: BLE001 — Server aus/zu langsam
            pass
        self._gemeldet = False

    @staticmethod
    def _an_server(daten, timeout):
        import json as _json
        req = urllib.request.Request(f"{adresse()}/api/vlc",
                                     data=_json.dumps(daten).encode("utf-8"), method="POST")
        return urllib.request.urlopen(req, timeout=timeout)

    def verstecken(self):
        """pywebview-Ereignis before_load: vor JEDEM Seitenaufbau (auch
        location.reload() der Selbst-Erneuerung) das native Panel verstecken —
        sonst verdeckt es die neu ladende Seite, bis die ihre Fläche frisch
        meldet. before_load läuft SYNCHRON im UI-Faden (Event(…, True)), darum
        direkt und ohne Invoke. Bewusst kein pagehide aus der Seite: das
        bräuchte einen js_api-Faden plus Invoke auf ein womöglich schließendes
        Formular (Prozessende hinge)."""
        p = self._panel
        if p is None:
            return
        try:
            p.Visible = False
        except Exception:                            # noqa: BLE001 — Kür, nie das Laden stören
            pass

    def setzen(self, form, x, y, w, h, an):
        if not self._hwnd:
            if not (an and form is not None):
                return
            self._panel_sichern(form)
        self.melden()
        from System import Action

        def tu():
            p = self._panel
            if p is None:
                return
            if an and w > 0 and h > 0:
                from System.Drawing import Point, Size
                p.Location = Point(int(x), int(y))
                p.Size = Size(int(w), int(h))
                p.Visible = True
                p.BringToFront()
            else:
                p.Visible = False
        form.Invoke(Action(tu))


class Bruecke:
    """js_api der Hülle — die Oberfläche ruft window.pywebview.api.*
    REGEL: außer Methoden nichts Öffentliches (siehe VideoFenster)."""

    def __init__(self):
        self._video = VideoFenster()
        self._fenster = None

    def video_rect(self, x, y, w, h, an):
        """Ziel-Fläche fürs eingebettete VLC-Video (Geräte-Pixel, von der
        Oberfläche mit devicePixelRatio vorgerechnet). an=False versteckt."""
        try:
            form = self._fenster.native if self._fenster else None
            self._video.setzen(form, x, y, w, h, bool(an))
            return True
        except Exception:                            # noqa: BLE001 — Einbettung ist Kür
            return False

    def video_melden(self):
        """Die Seite ruft das VOR jedem VLC-Start (Befund 24.09.): das Panel
        beim Server (neu) anmelden. Die einmalige Anmeldung reichte nicht —
        nach jedem Selbst-Neustart des Servers ist das Handle dort weg, und
        das erste Video öffnete VLCs eigenes Fenster. Fehlt das Panel noch
        (frueh() fand kein Formular), entsteht es hier. True = angemeldet."""
        try:
            v = self._video
            v._gemeldet = False
            form = self._fenster.native if self._fenster else None
            if form is not None:
                v.vorbereiten(form)                  # Panel bei Bedarf anlegen + melden
            else:
                v.melden()
            return bool(v._gemeldet)
        except Exception:                            # noqa: BLE001 — Einbettung ist Kür
            return False


def main():
    # Vor jedem Fenster (auch der Fehlermeldung unten): dieselbe Kennung wie der
    # Server, damit Windows das Hüllen-Fenster als „SyncYouTube" führt (Taskleiste).
    # Die Medien-Sitzung des WebView2 läuft in dessen eigenem Prozess und erbt
    # sie nicht (JB 24.09.2026: „Kennung + Startmenü-Eintrag").
    windows_kennung.setze_kennung()
    import webview
    if not server_starten():
        # Ehrlich scheitern statt leeres Fenster: der Nutzer sieht den Grund.
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, f"Der SyncYouTube-Server startet nicht (Port {_port()}).\n"
                  "Bitte einmal über SyncYouTube.bat starten.",
            "SyncYouTube", 0x10)
        return 1
    api = Bruecke()
    fenster = webview.create_window(
        "SyncYouTube", adresse(), width=1360, height=860,
        background_color="#171310", min_size=(560, 420), js_api=api)
    api._fenster = fenster
    api._video._fenster = fenster                    # für die Maus-Weiterleitung
    fenster.events.before_load += api._video.verstecken   # Neuladen: Panel weg
    # Vollbild (TV): der ⛶-Knopf der Oberfläche nutzt die Fullscreen-API —
    # die trägt im WebView2 genauso wie im Browser; kein Sonderweg nötig.
    def frueh():
        time.sleep(1.5)                              # GUI erst stehen lassen
        api._video.vorbereiten(fenster.native)
    webview.start(frueh, private_mode=False)
    api._video.abmelden()                            # Fenster zu: Panel beim Server abmelden
    return 0


if __name__ == "__main__":
    sys.exit(main())
