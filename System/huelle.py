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
    webview.create_window(
        "SyncYouTube", ADRESSE, width=1360, height=860,
        background_color="#171310", min_size=(560, 420))
    # Vollbild (TV): der ⛶-Knopf der Oberfläche nutzt die Fullscreen-API —
    # die trägt im WebView2 genauso wie im Browser; kein Sonderweg nötig.
    webview.start(private_mode=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
