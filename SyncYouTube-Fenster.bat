@echo off
chcp 65001 >nul
rem SyncYouTube als eigenes Fenster (Programm-Huelle, Spec Stufe 2, JB-Go 05.08.2026)
rem Startet den App-Server selbst, falls er nicht laeuft.
start "" "%~dp0..\SyncDashTray\System\venv\Scripts\pythonw.exe" "%~dp0System\huelle.py"
