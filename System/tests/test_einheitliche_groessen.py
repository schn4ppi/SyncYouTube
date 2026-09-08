# -*- coding: utf-8 -*-
"""Waechter: gleiche Dinge sind gleich gross (JB 08.09.2026).

JB am Screenshot: *»wieso haben nicht alle videos die gleiche hoehe? Wieso sind
einige tooltips groesser als andere? Einheitlichkeit ist super wichtig!«*

GEMESSEN im laufenden Programm, bevor etwas geaendert wurde:
  * Kachelbilder 142 px ODER 250 px hoch — ein quadratisches Album-Bild machte die
    Kachel 108 px hoeher als ein 16:9-Vorschaubild. Das `aspect-ratio:16/9` am
    Rahmen hat NIE gegriffen: `.kachel` ist ein Spalten-Flex, seine Kinder haben
    damit `min-height:auto`, und der Inhalt gewinnt gegen das Seitenverhaeltnis.
    Die 16:9-Bilder sahen nur richtig aus, weil ihre eigene Form zufaellig passte.
  * Kacheltitel 17 px ODER 34 px — ohne Mindesthoehe rutscht die Infozeile je nach
    Titellaenge um eine Zeile.
  * 32 sichtbare Bedienelemente in ELF Hoehen: 20, 21, 22, 24, 25, 26, 28, 30, 31,
    33, 37 px. Nebeneinander liegende Knoepfe unterschieden sich um einen Pixel,
    weil die Hoehe aus Polsterung plus Zeilenhoehe entstand statt gesetzt zu sein.

Danach: Bilder alle 142, Titel alle 34, Kacheln alle 217 px; Bedienelemente in fuenf
Gruppen, und die fuenf sind Absicht (Pillen 24, Panel-Reiter 28, Transport 30 und 37
fuer den Abspiel-Knopf, Bedienzeile 32).

Geprueft wird hier die QUELLE, nicht das Erzeugnis: ein Waechter, der den Browser
braucht, liefe im Gate nicht mit. Die Zahlen oben stammen aus einer echten Messung
mit Playwright gegen die laufende App.

ROTE GEGENPROBE (08.09.2026, jede an der echten Datei gefahren und byte-genau
zurueckgeschrieben - Pruefsumme vorher/nachher gleich):
  * `flex:none;min-height:0` aus `.thumbwrap` entfernt  => Bild-Test faellt
  * `min-height:2.64em` aus `.ktitel` entfernt          => Titel-Test faellt
  * `height:33px` in `.tog` zurueckgeschrieben          => Token-Test faellt
  * Token `--feld-h` geloescht                          => Token-Existenz faellt
Die erste Fassung dieser Gegenprobe war GRUEN, obwohl die Zusage weg war: der
Waechter las den erklaerenden Kommentar INNERHALB der Regel als Deklaration.
Siehe `_ohne_kommentar` - ein Waechter, der die Erklaerung statt der Sache prueft,
meldet Gesundheit, die es nicht gibt.
"""
import os
import re

HIER = os.path.dirname(os.path.abspath(__file__))
OBERFLAECHE = os.path.join(os.path.dirname(HIER), "oberflaeche.py")

# Klassen, deren Hoehe aus den Tokens kommen MUSS. Wer hier eine feste Pixelhoehe
# einträgt, baut die naechste Ungleichheit.
TOKEN_PFLICHT = (".tog", ".cmd-dl", ".cmd-qual", ".cmd-url", ".btn.mini",
                 ".dlbox-tab", "#libsuche", "#libsort", "#plsel")


def _quelle() -> str:
    with open(OBERFLAECHE, encoding="utf-8") as f:
        return f.read()


def _ohne_kommentar(rumpf):
    """Nur die Deklarationen einer Regel - Kommentare heraus.

    Die dritte Gegenprobe war GRUEN, obwohl ich `min-height:0` aus `.thumbwrap`
    entfernt hatte: der erklaerende Kommentar steht INNERHALB der geschweiften
    Klammern und schreibt »min-height:0 und flex:none geben dem Seitenverhaeltnis
    die Entscheidung zurueck«. Der Waechter las meinen eigenen Fliesstext als
    Zusage. Ein Waechter, der die Erklaerung statt der Sache prueft, ist blind.
    """
    return re.sub(r"/\*.*?\*/", "", rumpf, flags=re.S)


def _selektor(roh):
    """Der reine Selektor einer Regel - ohne den Kommentar, der davor steht.

    Der Regel-Ausdruck laesst im Selektor Zeilenumbrueche zu (mehrzeilige
    Selektorlisten gibt es wirklich). Damit wandert aber auch ein `/* ... */`
    ueber der Regel in den Selektor, und der exakte Vergleich schlaegt fehl:
    `.ktitel` hiess fuer den Waechter `/* Immer zwei Zeilen hoch ... */ .ktitel`.
    Gefunden hat das erst die Messung, welche Selektoren wirklich ankommen.
    """
    return roh.split("*/")[-1].strip()


def _regel(text, klasse):
    """Der Rumpf der GRUNDREGEL dieser Klasse - der Regel, deren Selektor genau sie ist.

    Drei Fallen lagen hier hintereinander, jede fand erst eine Messung:

    1. Teilstring statt Wortgrenze: die erste Fassung suchte `".ktitel" in selektor`
       und traf `#tv .tv-ktitel` aus dem Fernsehmodus - sie pruefte die falsche
       Regel und meldete einen Mangel, den es nicht gab.
    2. Erste statt Grund-Regel: danach traf sie `.kacheln.kompakt .ktitel`, weil die
       Kompakt-Ansicht frueher in der Datei steht. Diese Regel setzt nur eine
       Schriftgroesse; die Hoehen-Zusagen stehen in der Grundregel weiter unten.
    3. Kommentar im Selektor: siehe `_selektor`.

    Deshalb: erst die Regel mit dem exakt gleichen Selektor, sonst die erste, die
    die Klasse ueberhaupt wortgenau traegt.
    """
    muster = re.compile(r"(?<![\w.#-])" + re.escape(klasse) + r"(?![\w-])")
    passend = [(_selektor(tr.group(1)), _ohne_kommentar(tr.group(2)))
               for tr in re.finditer(r"([^{}\n][^{}]*)\{([^}]*)\}", text)
               if muster.search(tr.group(1))]
    for selektor, rumpf in passend:
        if selektor == klasse:
            return rumpf
    return passend[0][1] if passend else ""


def test_die_groessen_tokens_gibt_es():
    """Zwei Groessen, an einer Stelle definiert — nicht elf ueber die Datei verstreut."""
    t = _quelle()
    assert "--pille-h:" in t, "Token fuer die Pillen-Hoehe fehlt"
    assert "--feld-h:" in t, "Token fuer die Feld-Hoehe fehlt"


def test_kachelbild_haelt_sein_seitenverhaeltnis():
    """`aspect-ratio` allein genuegt im Flex-Kind NICHT — min-height:0 muss dazu."""
    rumpf = _regel(_quelle(), ".thumbwrap")
    assert "aspect-ratio" in rumpf, ".thumbwrap braucht ein Seitenverhaeltnis"
    assert "min-height:0" in rumpf.replace(" ", ""), (
        "Ohne min-height:0 gewinnt der Bildinhalt gegen das Seitenverhaeltnis — "
        "quadratische Album-Bilder machen die Kachel dann 108 px hoeher")
    assert "flex:none" in rumpf.replace(" ", ""), (
        "Ohne flex:none darf der Rahmen als Flex-Kind wachsen")


def test_kacheltitel_ist_immer_zwei_zeilen_hoch():
    """Sonst rutscht die Infozeile je nach Titellaenge um eine Zeile."""
    rumpf = _regel(_quelle(), ".ktitel")
    assert "-webkit-line-clamp:2" in rumpf.replace(" ", ""), "Titel muss bei zwei Zeilen enden"
    assert "min-height" in rumpf, (
        "Ohne Mindesthoehe ist ein einzeiliger Titel 17 px, ein zweizeiliger 34 px")


def test_bedienelemente_nutzen_die_groessen_tokens():
    """Keine feste Pixelhoehe auf den Elementen, die nebeneinander stehen.

    Auto-Discovery: jede Regel der Datei wird angesehen; eine feste `height:NNpx`
    auf einem der bewachten Selektoren ist der Befund. Handliste waere hier falsch,
    weil die Datei staendig waechst."""
    t = _quelle()
    schuldige = []
    for treffer in re.finditer(r"([^{}\n][^{}]*)\{([^}]*)\}", t):
        sel = _selektor(treffer.group(1))
        rumpf = _ohne_kommentar(treffer.group(2)).replace(" ", "")
        if "::" in sel:
            continue                    # Pseudo-Elemente sind Striche und Punkte,
                                        # keine Bedienelemente — ein 4-px-Indikator
                                        # unter dem Umschalter hat mich zuerst erwischt
        if not any(re.search(r"(?<![\w.#-])" + re.escape(k) + r"(?![\w-])", sel)
                   for k in TOKEN_PFLICHT):
            continue
        feste = re.search(r"(?<!min-)(?<!max-)height:(\d+)px", rumpf)
        if feste:
            schuldige.append(f"{sel[:60]} -> height:{feste.group(1)}px")
    assert not schuldige, (
        "Diese Regeln setzen wieder eine eigene Hoehe statt --pille-h/--feld-h:\n  "
        + "\n  ".join(schuldige))
