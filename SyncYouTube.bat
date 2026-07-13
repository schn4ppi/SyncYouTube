@echo off
rem Startet SyncYouTube FENSTERLOS im Hintergrund (pythonw = kein
rem Konsolenfenster) und schliesst sich sofort selbst. Der Browser oeffnet
rem automatisch; die App laeuft weiter im Tray (Symbol unten rechts:
rem Oeffnen / Downloads-Ordner / Beenden).
cd /d "%~dp0"
start "" "%~dp0..\SyncDashboard\System\venv\Scripts\pythonw.exe" "%~dp0System\youtube_app.py"
exit
