@echo off
chcp 65001 >nul
rem Startet SyncYouTube FENSTERLOS im Hintergrund (pythonw = kein
rem Konsolenfenster) und schliesst sich sofort selbst. Der Browser oeffnet
rem automatisch.
rem Welches Python: zuerst eines aus System\python_pfad.txt (eine Zeile, der
rem Pfad zu pythonw.exe; nur auf diesem PC, nicht im Repo), dann das
rem mitgelieferte (Quellstart-Paket), sonst pythonw aus dem PATH.
cd /d "%~dp0"
set "PY="
if exist "%~dp0System\python_pfad.txt" set /p PY=<"%~dp0System\python_pfad.txt"
if not defined PY set "PY=%~dp0python\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
start "" "%PY%" "%~dp0System\youtube_app.py"
exit
