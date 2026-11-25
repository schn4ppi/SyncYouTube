# -*- coding: utf-8 -*-
"""Die PC-Oberfläche von SyncYouTube — EINE Seite, zusammengesetzt aus Dateien.

Die Teile liegen unter pc_oberflaeche/ (Strukturumbau 25.11.2026; bis dahin stand
alles als ein Python-String von 11.500 Zeilen in dieser Datei):
  seite.html        das Gerüst: Kopf, Körper, Modals, schwebende Flächen; darin
                    die Platzhalter /*@STIL@*/, /*@LAYOUT_KERN@*/, /*@HAUPTSKRIPT@*/
  stil.css          das Stilblatt aus dem Kopf (<style>)
  skript/NN_*.js    das Hauptskript, eine Datei je Hauptbereich; sie werden in der
                    Reihenfolge ihrer Nummer aneinandergehängt und teilen sich
                    EINEN <script>-Block (gemeinsamer Gültigkeitsbereich)
  ../layout_kern.js der Layout-Mathe-Kern, unverändert zwischen LAYOUT_KERN_START
                    und LAYOUT_KERN_END eingesetzt
Die ausgelieferte Seite ist Byte für Byte dieselbe wie vor dem Umbau.

Wird von youtube_app.py unter "/" ausgeliefert und bei jedem Aufruf heiß
nachgeladen (importlib.reload liest die Dateien neu) — Änderungen an jedem Teil
erscheinen mit Browser-F5, ohne App-Neustart. Die Kopfleiste zeigt die
Programmfassung; youtube_app.py setzt sie beim Ausliefern für den Platzhalter
/*APP_VERSION*/ ein.

KOPF-KARTE (Gesamtprüfung O2, 25.09.2026): welcher Bereich wo steht, in der
Reihenfolge des Dokuments. Zeilennummern wandern, darum stehen hier die Titel
der Banner zum Suchen. Ein Banner mit ==== markiert einen Hauptbereich des
Hauptskripts, eines mit ---- einen Unterbereich. Ein Bereich kann zweimal
vorkommen („Fortsetzung“), weil der Code dort gewachsen ist, wo er gebraucht
wurde; jeder Hauptbereich ist eine Datei unter pc_oberflaeche/skript/.
tests/test_oberflaeche_karte.py prüft, dass jedes ====-Banner des Skripts
hier in derselben Reihenfolge steht, und umgekehrt.

  <head>    Skin-Frühstart: setzt die Farbwelt vor dem ersten Bild (kein Aufblitzen).
  <style>   Farbwelt als CSS-Variablen (--akz/--panel/…; ein „Skin" tönt alles um)
            · Command-Bar · TV-Bibliothek · Ausweich-Ordnung der Kopfleiste · Panels
            · Assistent-Modal · Warteschlange · Bibliothek · Spalten-Menü · Player
            · Vollbild-Overlay · Tag-Modus (hell) · Container-Queries (schmale Panels)
  <body>    Einbettungs-Modus (Stil + Skript) · Command-Bar (Link-Feld, Live-Queue,
            Now-Playing, Download-Fenster) · Layout-Leiste · #canvas (die beweglichen
            Fenster) · Modals (Hilfe/Einstellungen/Geo) · #stash mit den Views
  <script>  layout_kern.js zwischen LAYOUT_KERN_START und _END (vendort: nur im
            Master die Vorlage von layout_kern.js ändern)
  <script>  das Hauptskript mit diesen Hauptbereichen:
    ==== Helfer & globaler Zustand
         esc/toast/mb/zeit · Server-Ruf api() und Browser-Speicher lsLesen/
         lsSchreiben/lsWeg · Looks/Skins · Bildschirm-Wächter · Optionen-Zahnrad
    ==== Panels / Docking
         Ansicht-Verlauf (Mausrad) · Verlust-Schutz · Layout-Vorlagen · eigene
         Layouts · Mini-Player · ✏-Layout-Modus
    ==== Warteschlange
         Status laden/malen · Handy-Fernsteuerung · Log
    ==== Command-Bar oben: Download, Live-Queue, Now-Playing, Zwischenablage
         Ein Feld für alles · Mengen-Regler · Link ins Fenster ziehen
    ==== Abos
         Zustand und Server-Ruf (aboPost, aboLaden); die Karten folgen unten
    ==== Filme
         Film-Fundament · Film-Player-Screen · Medientasten im Film · Stelle und
         „gesehen“ melden · Mindest-Sehzeit
    ==== Abos, Fortsetzung
         Karten · Regeln · Backkatalog-Flyout · Prüfen
    ==== Smart-Playlists, Dubletten, Einstellungen speichern
    ==== Geo/VPN-Assistent
    ==== Bibliothek
         Klick-Art · Rahmen-Auswahl · Abspielmodus · Browser-Zeichen · Radio ·
         Sleep-Timer · Ausschnitt/Clip · Alben · Menü-Werkzeuge · Neues entdecken
    ==== Player
         Geschwindigkeit · Untertitel/Karaoke/Transkript · Kapitel · Visualizer ·
         Equalizer · Übergänge · Steuerleiste · Springen · Spulen am Fernseher
    ==== TV-Bibliothek
         Fernbedienung · Geräte koppeln · Profile · Wünsche über Jellyseerr ·
         Hero-Billboard und More-Info · Tasten im TV
    ==== Player, Fortsetzung: Bild-in-Bild und Wiedergabe-Merker
    ==== Gerät VLC
         Wiedergabe-Grundeinstellungen · Medientasten der Tastatur
    ==== Player-Anzeige und Ad-hoc-Playlist
         Titel ins Bild setzen · Rahmen-Auswahl in der Playlist · Werkzeuge ·
         Eigenschaften · Ziehen und Ablegen · Lieblingssongs · Playlist sichern ·
         Transkript-Volltextsuche
    ==== Playlists
         Titel auf eine Playlist ziehen · Sync/.m3u · Namens-Baukasten · Hotkey-Editor
    ==== Init (läuft einmal beim Seiten-Start)
  <body>    Schwebende Flächen (Build 125): Ansicht-Menü, Spalten-Menü, TV-Overlay,
            direkt unter <body>, damit kein Container sie einsperrt.

Seit dem Umbau sind CSS und JavaScript echte Dateien: ein Backslash bleibt dort ein
Backslash, die frühere Falle mit verdoppelten Escapes im Python-String gibt es nicht
mehr. tests/test_oberflaeche_syntax.py übersetzt jeden Skript-Block mit deno."""

import glob
import os
import sys

from medien_session import einsetzen as _medien_einsetzen   # Media-Session-Baustein (mit handy.py geteilt)

# Beim Quellstart liegen die Teile neben dieser Datei, in der exe im Entpackordner
# (SyncYouTube.spec nimmt pc_oberflaeche/ und layout_kern.js als Daten mit).
_HIER = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
TEILE = os.path.join(_HIER, "pc_oberflaeche")
LAYOUT_KERN = os.path.join(_HIER, "layout_kern.js")


def skript_dateien():
    """Die Dateien des Hauptskripts in der Reihenfolge ihrer Nummer."""
    return sorted(glob.glob(os.path.join(TEILE, "skript", "*.js")))


def teil_dateien():
    """Jede Datei, aus der die Seite entsteht (für den Stand alter Browser-Tabs)."""
    return [os.path.join(TEILE, "seite.html"), os.path.join(TEILE, "stil.css"),
            LAYOUT_KERN, *skript_dateien()]


def _lesen(pfad):
    with open(pfad, encoding="utf-8") as f:
        return f.read()


def _einsetzen(vorlage, platzhalter, text):
    """Genau einmal einsetzen. Fehlt der Platzhalter oder steht er doppelt, ist das
    ein Fehler: lieber laut als eine halbe Seite."""
    if vorlage.count(platzhalter) != 1:
        raise ValueError(f"Platzhalter {platzhalter} steht {vorlage.count(platzhalter)}-mal in seite.html")
    return vorlage.replace(platzhalter, text, 1)


def seite_bauen():
    skripte = skript_dateien()
    if not skripte:
        raise FileNotFoundError(f"keine Skript-Dateien unter {TEILE}")
    html = _lesen(os.path.join(TEILE, "seite.html"))
    html = _einsetzen(html, "/*@STIL@*/", _lesen(os.path.join(TEILE, "stil.css")))
    html = _einsetzen(html, "/*@LAYOUT_KERN@*/", _lesen(LAYOUT_KERN))
    return _einsetzen(html, "/*@HAUPTSKRIPT@*/", "".join(_lesen(p) for p in skripte))


# Rohvorlage unter eigenem Namen: scheitert beim heißen Nachladen das Einsetzen
# des Bausteins, bleibt HTML die alte, heile Seite (sonst lieferte der Server eine
# Vorlage ohne Baustein aus — Oberfläche tot; Prüf-Befund 24.09.2026).
_HTML_ROH = seite_bauen()
HTML = _medien_einsetzen(_HTML_ROH)   # /*MEDIEN_SESSION_JS*/ -> gemeinsamer Baustein
