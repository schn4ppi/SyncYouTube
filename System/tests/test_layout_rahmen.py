# -*- coding: utf-8 -*-
"""Waechter: nichts ragt aus der Flaeche (JB-Fund 08.09.2026).

JB: *„wenn ich das fenster bestimmt klein mache, dann geht der mini player ueber
die grenzen, das darf nicht passieren."*

GEMESSEN im echten Browser (Playwright, echte Groessenaenderungen), VOR der
Reparatur - Fensterbreite, dann Ueberstand des Player-Fensters:

  |  Fenster | Flaeche | rechts hinaus | unten hinaus     |
  |----------|---------|---------------|------------------|
  |  700 px  |  700    | keiner        | keiner           |
  |  560 px  |  560    | **23 px**     | 84 px (beide)    |
  |  430 px  |  430    | **65 px**     | 153 px (beide)   |
  |  360 px  |  360    | **88 px**     | 193 px (beide)   |

URSACHE: `LK.skaliere` klemmt die BREITE auf das Minimum (220) hoch, skaliert
die POSITION aber weiter mit. Bei 430 px stand der Player auf x=275 mit
Breite 220 - macht 495 auf einer 410 px breiten Flaeche. `LK.entklemmen` half
nicht: die beiden Fenster BERUEHRTEN sich nur (x = Rechtskante des Nachbarn),
und Beruehrung ist im Kern ausdruecklich keine Kollision.

Die senkrechte Haelfte stand schon VOR der Reparatur ueber (84/153/193 px bei
BEIDEN Fenstern) - nur fiel es weniger auf, weil oben noch etwas zu sehen war.
`#canvas` hatte `overflow:hidden` und hat es einfach abgeschnitten.

REPARIERT in zwei Schritten:
  1. `LK.inDenRahmen` (gemeinsamer Layout-Kern) holt jedes Fenster zurueck in
     die Flaeche - VOR `entklemmen`, damit dessen Zeilenumbruch die dadurch
     entstehenden Ueberlappungen normal aufloest, und danach noch einmal.
  2. Die Flaeche darf senkrecht rollen (`overflow-y:auto`). Waagerecht bleibt
     `hidden`, dort ragt ja nichts mehr hinaus. Ein Rollbalken, den es nur im
     Notfall gibt, ist besser als Inhalt, den niemand erreicht.

NACHHER gemessen: waagerecht bei KEINER Groesse Ueberstand, senkrecht alles
erreichbar (nach unten gerollt ist das zweite Fenster sichtbar), und oberhalb
von 700 px gibt es gar keinen Rollbalken - dort aendert sich nichts.

Hier wird die QUELLE geprueft, damit der Waechter im Gate ohne Browser laeuft.
Das Verhalten selbst deckt `test_layout_kern` im Familien-Repo ab (dort laeuft
der Kern echt unter node).

ROTE GEGENPROBE (08.09.2026 gefahren, Datei byte-genau zurueckgeschrieben):
beide `LK.inDenRahmen`-Aufrufe entfernt => Verdrahtungs-Test faellt;
`overflow-y:auto` auf `hidden` zurueckgedreht => CSS-Test faellt.
"""
import io
import os
import re

HIER = os.path.dirname(os.path.abspath(__file__))
OBERFLAECHE = os.path.join(os.path.dirname(HIER), "oberflaeche.py")


def _quelle():
    with io.open(OBERFLAECHE, encoding="utf-8") as f:
        return f.read()


def _ohne_kommentar(text):
    """Kommentare raus, bevor gemessen wird.

    Sonst prueft der Waechter die Erklaerung statt der Sache - genau das ist am
    08.09.2026 schon einmal passiert (Lehrbuch L71): eine rote Gegenprobe blieb
    gruen, weil der erklaerende Text die gesuchte Zeichenkette enthielt."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


def _funktion(name, danach):
    """Der Rumpf einer JS-Funktion: von ihrem Kopf bis zum Kopf der naechsten."""
    t = _quelle()
    i = t.index("function %s(" % name)
    j = t.index("function %s(" % danach, i)
    return _ohne_kommentar(t[i:j])


def test_die_projektion_holt_alles_in_den_rahmen():
    """Zweimal klemmen, und `entklemmen` liegt dazwischen.

    Die Reihenfolge ist der Kern der Reparatur: klemmt man erst NACH dem
    Entklemmen, ueberlappen die zurueckgezogenen Fenster einander, ohne dass
    der Zeilenumbruch das noch aufloest."""
    rumpf = _funktion("layoutProjizieren", "layoutAnViewport")
    stellen = [m.start() for m in re.finditer(r"LK\.inDenRahmen\s*\(", rumpf)]
    entklemmt = [m.start() for m in re.finditer(r"LK\.entklemmen\s*\(", rumpf)]
    assert len(stellen) >= 2, (
        "layoutProjizieren muss LK.inDenRahmen zweimal rufen (vor und nach dem "
        "Entklemmen) - gefunden: %d" % len(stellen))
    assert entklemmt, "LK.entklemmen fehlt in layoutProjizieren"
    assert stellen[0] < entklemmt[0] < stellen[-1], (
        "Reihenfolge falsch: erst in den Rahmen holen, dann entklemmen, dann "
        "noch einmal klemmen")


def test_der_kern_kennt_die_rahmen_klemme():
    """Der Inline-Block muss die Funktion wirklich enthalten - sonst wirft der
    Aufruf zur Laufzeit einen Fehler, den niemand sieht."""
    t = _quelle()
    block = t.split("/*LAYOUT_KERN_START*/", 1)[1].split("/*LAYOUT_KERN_END*/", 1)[0]
    assert "LK.inDenRahmen=function" in block, (
        "Der eingebettete Layout-Kern hat die Rahmen-Klemme nicht - aus dem "
        "Master SyncDashTray/System/layout_kern.js neu einsetzen")


def test_die_flaeche_schneidet_nicht_mehr_ab():
    """Waagerecht `hidden` (dort ragt nichts hinaus), senkrecht `auto`."""
    t = _quelle()
    treffer = re.search(r"#canvas\{([^}]*)\}", t)
    assert treffer, "#canvas-Regel nicht gefunden"
    rumpf = _ohne_kommentar(treffer.group(1)).replace(" ", "")
    assert "overflow-y:auto" in rumpf, (
        "Ohne senkrechtes Rollen wird bei kleinen Fenstern abgeschnitten: bei "
        "560x560 bleiben der Flaeche 236 px, zwei Fenster brauchen mit ihrer "
        "Mindesthoehe aber 320")
    assert "overflow-x:hidden" in rumpf, (
        "Waagerecht soll NICHT gerollt werden - dort sorgt LK.inDenRahmen dafuer, "
        "dass es nichts zu rollen gibt")
    assert not re.search(r"(?<![\w-])overflow:hidden", rumpf), (
        "Das pauschale overflow:hidden war die Ursache des Abschneidens")
