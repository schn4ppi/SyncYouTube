# Browser-Erweiterung — Änderungsliste

> Diese Liste wird je Version auch als AMO-Versionsnotiz hinterlegt
> (`amo_sign.py` liest den obersten passenden Eintrag beim Einreichen).

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
