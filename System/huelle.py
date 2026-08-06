# -*- coding: utf-8 -*-
"""Programm-Hülle (Medienzentrale-Spec Stufe 2, JB-Go 05.08.2026: „Dann lass
die Programm-Hülle jetzt angehen. go").

Eigenes Fenster statt Browser-Tab: lädt die BESTEHENDE Oberfläche vom lokalen
Server (ein Gesicht, zwei Zugänge — der Server bleibt derselbe, das Handy
erreicht ihn weiter über den Browser/die gehostete Seite). Läuft der Server
noch nicht, startet die Hülle ihn selbst und wartet, bis er antwortet.

Bedienung: F11 = Vollbild (TV-Modus-Grundlage; die eigene TV-Design-Runde
folgt laut Spec separat). Fenster zu = nur die Hülle endet, der Server läuft
weiter (Downloads/VLC spielen weiter — bewusst, wie der Browser-Tab vorher).

NÄCHSTE ETAPPE (nicht hier): VLC-Video per set_hwnd IN dieses Fenster
einbetten — dann ersetzt der VLC-Motor das <video>-Element vollständig und
der Browser-Player kann in der Hülle abgeschaltet werden.
"""
import os
import subprocess
import sys
import time
import urllib.request

PORT = 8776
ADRESSE = f"http://127.0.0.1:{PORT}"


def server_laeuft(timeout=2):
    try:
        with urllib.request.urlopen(f"{ADRESSE}/api/status", timeout=timeout):
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

    def __init__(self):
        self.hwnd = 0
        self.panel = None
        self.gemeldet = False                        # hwnd schon an den Server?
        self.fenster = None                          # pywebview-Fenster (für _js)

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
            self.panel = p
            self.hwnd = int(p.Handle.ToInt64())
        form.Invoke(Action(tu))
        return self.hwnd

    def _js(self, code, drossel_s):
        """JS in der Oberfläche ausführen (best-effort, MouseMove gedrosselt).
        WICHTIG: nie auf dem WinForms-UI-Thread blocken — evaluate_js wartet
        auf die WebView, die gerade den UI-Thread braucht (Deadlock-Fund der
        Nachtprüfung). Darum feuert ein kleiner Daemon-Thread den Ruf ab."""
        jetzt = time.time()
        if drossel_s and jetzt - getattr(self, "_js_zuletzt", 0.0) < drossel_s:
            return
        self._js_zuletzt = jetzt
        fenster = self.fenster
        if fenster is None:
            return

        def tu():
            try:
                fenster.evaluate_js(code)
            except Exception:                        # noqa: BLE001 — Weck-Ruf ist Kür
                pass
        import threading
        threading.Thread(target=tu, daemon=True).start()

    def vorbereiten(self, form):
        """Beim Hüllen-START Panel + hwnd anlegen und melden (JB-Fund: „Player
        ist nicht unten im film" — der Server kannte das Fenster beim ersten
        Play noch nicht und öffnete VLCs EIGENES Vollbild; das Panel blieb
        schwarz). Früh gemeldet = jeder Film rendert von Anfang an IM Fenster."""
        try:
            if not self.hwnd:
                self._anlegen(form)
            self.melden()
        except Exception:                            # noqa: BLE001 — Kür
            pass

    def melden(self):
        """Das Handle EINMAL an den Server geben (überlebt dort auch die
        VLC-Selbstheilung); scheitert der Abruf, beim nächsten Rect erneut."""
        if self.gemeldet or not self.hwnd:
            return
        try:
            import json as _json
            req = urllib.request.Request(
                f"{ADRESSE}/api/vlc",
                data=_json.dumps({"cmd": "fenster", "hwnd": self.hwnd}).encode("utf-8"),
                method="POST")
            with urllib.request.urlopen(req, timeout=3):
                self.gemeldet = True
        except Exception:                            # noqa: BLE001 — nächster Versuch folgt
            pass

    def setzen(self, form, x, y, w, h, an):
        if not self.hwnd:
            if not (an and form is not None):
                return
            self._anlegen(form)
        self.melden()
        from System import Action

        def tu():
            p = self.panel
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
    """js_api der Hülle — die Oberfläche ruft window.pywebview.api.*"""

    def __init__(self):
        self.video = VideoFenster()
        self._fenster = None

    def video_rect(self, x, y, w, h, an):
        """Ziel-Fläche fürs eingebettete VLC-Video (Geräte-Pixel, von der
        Oberfläche mit devicePixelRatio vorgerechnet). an=False versteckt."""
        try:
            form = self._fenster.native if self._fenster else None
            self.video.setzen(form, x, y, w, h, bool(an))
            return True
        except Exception:                            # noqa: BLE001 — Einbettung ist Kür
            return False


def main():
    import webview
    if not server_starten():
        # Ehrlich scheitern statt leeres Fenster: der Nutzer sieht den Grund.
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None, "Der YouTube-Downloader-Server startet nicht (Port 8776).\n"
                  "Bitte einmal über YouTube-Downloader.bat starten.",
            "SyncYouTube", 0x10)
        return 1
    api = Bruecke()
    fenster = webview.create_window(
        "SyncYouTube", ADRESSE, width=1360, height=860,
        background_color="#171310", min_size=(560, 420), js_api=api)
    api._fenster = fenster
    api.video.fenster = fenster                      # für die Maus-Weiterleitung
    # Vollbild (TV): der ⛶-Knopf der Oberfläche nutzt die Fullscreen-API —
    # die trägt im WebView2 genauso wie im Browser; kein Sonderweg nötig.
    def frueh():
        time.sleep(1.5)                              # GUI erst stehen lassen
        api.video.vorbereiten(fenster.native)
    webview.start(frueh, private_mode=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
