"""Startdatei der exe: lädt das Programm als gewöhnliches Modul und startet es.

Warum es sie gibt (25.11.2026): PyInstaller legt das Startskript als eigenen,
gepackten Block in die exe, alle anderen Module ins Python-Archiv. War das
Startskript youtube_app.py selbst, wuchs dieser Block ab 1.4.3 über 512 KiB, und
Avira (samt F-Secure, das Aviras Erkennung nutzt) meldete die exe pauschal als
„TR/ATRAPS.Gen“. Gemessen mit Probebauten: jeder Stand unter 512 KiB sauber, jeder
ab 512 KiB gemeldet, auch 1.4.1 mit bloßem Fülltext. Mit dieser kleinen
Startdatei liegt youtube_app im Archiv wie jedes andere Modul.

Nur für die exe (SyncYouTube.spec); der Quellstart ruft youtube_app.py direkt.
Wächter: tests/test_build_release.py (test_exe_startet_ueber_kleine_startdatei).
"""
import youtube_app

youtube_app.main()
