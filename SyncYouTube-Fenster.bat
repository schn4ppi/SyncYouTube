@echo off
chcp 65001 >nul
rem SyncYouTube als eigenes Fenster (Programm-Huelle).
rem Startet den App-Server selbst, falls er nicht laeuft.
rem Welches Python: zuerst eines aus System\python_pfad.txt (eine Zeile, der
rem Pfad zu pythonw.exe; nur auf diesem PC, nicht im Repo), dann das
rem mitgelieferte (Quellstart-Paket), sonst pythonw aus dem PATH.
cd /d "%~dp0"
set "PY="
if exist "%~dp0System\python_pfad.txt" set /p PY=<"%~dp0System\python_pfad.txt"
if not defined PY set "PY=%~dp0python\pythonw.exe"
if not exist "%PY%" set "PY=pythonw"
start "" "%PY%" "%~dp0System\huelle.py"
