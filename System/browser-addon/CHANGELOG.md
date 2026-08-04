# Browser-Erweiterung — Änderungsliste

> Diese Liste wird je Version auch als AMO-Versionsnotiz hinterlegt
> (`amo_sign.py` liest den obersten passenden Eintrag beim Einreichen).

## 1.1.1
- Playlists und Mixe lassen sich jetzt direkt von YouTube laden: der ⬇-Pfeil
  (mit gestricheltem Ring) erscheint an Playlist-Karten und am Kopf der
  Playlist-Leiste. Ein Klick fragt „Von–Bis"; bei einem Mix (endlos) werden
  ohne Angabe 50 geladen. Eigener kleiner Dialog — kein Browser-Fenster, das
  sich unterbinden lässt.
- Das Popup zeigt unten die aktive Version und prüft über die App, ob es ein
  Update gibt — mit 1-Klick-Installation (öffnet die signierte Datei, Firefox
  fragt selbst).
- Der grüne Haken flackert nicht mehr kurz zum Download-Pfeil, wenn man den
  Knopf verlässt oder wieder betritt: der Schon-in-der-Bibliothek-Zustand wird
  je Video lokal gemerkt und sofort gesetzt statt jedes Mal neu erfragt.

## 1.1.0
- Der ⬇-Knopf springt in Playlist-Zeilen nicht mehr: je nachdem, ob die Maus
  auf dem Text oder dem Vorschaubild stand, war der Anker ein anderes Element.
  Jetzt ankert der Knopf immer am Vorschaubild — eine Zeile, eine Position.
- Schon geladene Titel sind auf einen Blick erkennbar: der Knopf ist GRÜN mit
  Haken ✓, bevor man klickt (vorher Gold mit Pfeil). Ein Klick darauf blitzt
  rot mit ✗ („hast du schon") und lädt nicht doppelt; bewusstes Nachladen in
  anderem Format weiter über das Rechtsklick-Menü.

## 1.0.9
- Der Knopf springt nicht mehr in die linke obere Bildschirmecke, wenn ein
  Video zu Ende ist. Ursache: Sobald YouTube am Ende den Abspann einblendet
  oder den Player umbaut, hat das Video-Element kurzzeitig keine Maße mehr —
  die Positionsabfrage liefert dann lauter Nullen, und der Knopf wurde an den
  Bildschirmrand geklemmt statt versteckt. Jetzt gilt: ohne brauchbaren Anker
  erscheint der Knopf gar nicht. Außerdem wird er am VIDEO geklemmt statt am
  Bildschirm — er kann dadurch nie mehr neben dem Bild landen.

## 1.0.8
- Eigenes Symbol: die Erweiterung trägt jetzt dasselbe Emblem wie der
  YouTube-Downloader selbst (Familien-Logo). Die S-Rille ist echt
  ausgeschnitten und nimmt darum die Farbe der Firefox-Leiste an — hell
  wie dunkel.

## 1.0.7
- Schon in der Bibliothek: Knopf ist jetzt GELB; Klick darauf blitzt kurz rot
  („hast du schon") und lädt nicht doppelt — anderes Format per Rechtsklick.
- Der ⬇-Knopf verschwindet sofort, wenn die Maus das Video verlässt.
- Firefox-Systemmeldungen sind komplett abschaltbar und standardmäßig AUS
  (der Knopf zeigt ✓/✗ direkt am Video); einschaltbar im Popup.
- Beschreibung verweist auf die Änderungsliste bei den GitHub-Releases.

## 1.0.6
- Der ⬇-Knopf wird grün, wenn das Video schon in der Bibliothek liegt
  (Abfrage an die lokale App, 60-s-Zwischenspeicher).

## 1.0.5
- Hover-Knopf im Popup abschaltbar (Rechtsklick bleibt immer).
- Auf der Videoseite sitzt der Knopf am echten Bild statt an der Letterbox.
- Popup-Fehler behoben, durch den Status und Öffnen-Knopf hängen konnten.

## 1.0.4
- Selbst-Update eingeführt: Firefox holt neue Versionen automatisch über
  die GitHub-Releases (update_url + updates.json).

## 1.0.3
- Hover-Knopf erscheint nur noch, wenn die App wirklich läuft.
- Knopf oben links statt oben rechts — verdeckt keine YouTube-Knöpfe mehr;
  nur echte Vorschaubilder, keine Titel-Links.

## 1.0.1 / 1.0.2
- Frühe Fassungen: Rechtsklick-Menü mit Qualitätswahl + ⬇-Hover-Knopf,
  Verbindungsstatus im Popup.
