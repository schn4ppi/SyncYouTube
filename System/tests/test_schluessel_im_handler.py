# -*- coding: utf-8 -*-
"""Bibliotheks-Schlüssel nie roh im Handler (Gesamtprüfung S3, 25.09.2026).

Ein Bibliotheks-Schlüssel ist nicht garantiert harmlos: bei Links, die nicht
von YouTube stammen, ist er die ganze Adresse, und beim Ordner-Import kam er
aus einem Tag in der Datei. Landet er roh (oder nur mit `esc`) in einem
`onclick="…('${key}')"`, wird er vor der Ausführung wieder dekodiert und ist
Teil des Skripts. Der Weg ist darum: `data-key="${esc(key)}"` und im Handler
`this.dataset.key`.

Der Wächter RENDERT die echten Zeilen-Bausteine der Oberfläche und der
Handy-Seite mit deno — mit einem Schlüssel, der ' " < enthält — und liest das
Ergebnis mit einem HTML-Parser (wie der Browser: Attributwerte dekodiert):
  * kein Handler-Attribut (on…) enthält den Schlüssel, weder roh noch
    maskiert;
  * jedes data-key/data-id trägt den Schlüssel unverfälscht;
  * kein Attributname entsteht, der nicht im Baustein steht (ein Ausbruch aus
    einem Attribut erzeugt sonst neue Attribute);
  * jedes Element, dessen Handler this.dataset.key liest, trägt data-key.
Fehlt deno (System/bin ist gitignored), wird sichtbar übersprungen.
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import youtube_app as app  # noqa: E402
from test_medientasten_verhalten import _handy, _js_funktion, _lauf, _pc  # noqa: E402

SCHLUESSEL = "Qk1'\"<b>x|audio"
BILD = "https://i.example/bild\"x'<y.jpg"

# Ein Element, das sich wie im Browser verhält, soweit die Bausteine es brauchen:
# textContent -> innerHTML maskiert & < > (Anführungszeichen NICHT, wie im Browser).
DOM = r"""
function _el(){ return { className:'', style:{}, onclick:null, _html:'', dataset:{},
  set textContent(v){ this._html=String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); },
  set innerHTML(v){ this._html=String(v); }, get innerHTML(){ return this._html; },
  remove(){}, appendChild(){}, querySelectorAll(){ return []; },
  classList:{add(){},remove(){},toggle(){}} }; }
const _angehaengt=[];
document.createElement=()=>_el();
document.body={appendChild(e){ _angehaengt.push(e); }};
"""


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, attrs))

    handle_startendtag = handle_starttag


def _pruefen(html, mindestens=1):
    """Die vier Zusagen aus dem Kopf dieser Datei an einem gerenderten Stück."""
    p = _Tags()
    p.feed(html)
    p.close()
    assert p.tags, "nichts gerendert"
    mit_key = 0
    for tag, attrs in p.tags:
        werte = dict(attrs)
        for name, wert in attrs:
            wert = wert or ""
            assert re.fullmatch(r"[a-z][a-z0-9-]*", name), f"Ausbruch: Attribut {name!r} in <{tag}>"
            if name.startswith("on"):
                assert "Qk1" not in wert, f"Schlüssel im Handler <{tag} {name}={wert!r}>"
                if "dataset.key" in wert:
                    assert werte.get("data-key") == SCHLUESSEL, f"<{tag} {name}> ohne data-key"
                    mit_key += 1
            if name in ("data-key", "data-id"):
                assert wert == SCHLUESSEL, f"<{tag} {name}={wert!r}> verfälscht"
    assert mit_key >= mindestens, f"nur {mit_key} Handler lesen data-key: {html[:300]}"
    return p.tags


def _eintrag(**extra):
    x = {"id": SCHLUESSEL, "titel": "Titel", "uploader": "Kanal", "vorhanden": True,
         "thumb": BILD, "cover_album": True, "herz": False, "dauer": 60, "groesse": 1000,
         "qualitaet": "audio", "kategorie": "MP3"}
    x.update(extra)
    return x


PC_STUBS = """
function zeit(){return '1:00';} function mb(){return '1 MB';} function ytdatum(){return '';}
function technikText(){return '';} function kachelInfo(){return 'Info';} function pfeil(){return '';}
function sichtbareCols(){return ['status','dauer'];} function toast(){}
const COLDEF={kategorie:{l:'Kat',t:x=>x.kategorie||''}, qualitaet:{l:'Q',t:x=>x.qualitaet||''},
  status:{l:'Status',t:()=>''}, dauer:{l:'Dauer',t:()=>'1:00'}};
let libAuswahl=new Set(), libPlaylistView=true, libKompakt=false, libsort={key:'titel'};
"""


def _esc_funktion(q):
    """esc() wörtlich: der Klammer-Scanner von `_js_funktion` stolpert über
    die Regex-Literale mit Anführungszeichen darin."""
    m = re.search(r"^function esc[(]t[)][{].*?[}]$", q, re.M | re.S)
    assert m, "esc() fehlt"
    return m.group(0)


def _pc_teile(*namen):
    q = _pc()
    return [_esc_funktion(q) if n == "esc" else _js_funktion(q, n) for n in namen]


def test_kachel_und_liste_tragen_den_schluessel_nur_als_daten(tmp_path):
    teile = _pc_teile("esc", "herzKnopf", "aktBtnsKachel", "aktBtnsListe", "dragAttrs",
                      "kachel", "listeTab")
    eintraege = [_eintrag(), _eintrag(vorhanden=False, cover_album=False)]
    (e,) = _lauf(tmp_path, DOM, PC_STUBS, *teile,
                 f"const arr={json.dumps(eintraege)};"
                 "aus({kachel: arr.map(kachel).join(''), liste: listeTab(arr)});")
    _pruefen(e["kachel"], mindestens=8)
    _pruefen(e["liste"], mindestens=8)


def test_dubletten_eigenschaften_und_transkript_suche(tmp_path):
    teile = _pc_teile("esc", "dubBody", "eigenschaften", "tsuchLauf")
    eintrag, key = json.dumps(_eintrag()), json.dumps(SCHLUESSEL)
    lauf = [
        "function dublettenGruppen(){return [{typ:'Video mehrfach',titel:'T',items:["
        + eintrag + "," + eintrag + "]}];}",
        "function libFind(){return " + eintrag + ";}",
        "function tsMarkiere(t){return esc(t);}",
        "_els['tsuche-inp']={value:'hallo'}; _els['tsuche-body']=_el();",
        "globalThis.fetch=async()=>({json:async()=>({treffer:[{key:" + key
        + ",titel:'T',treffer:[{zeit:12,text:'hallo'}]}]})});",
        "eigenschaften(" + key + ");",
        "await tsuchLauf();",
        "aus({dub: dubBody(), eig: _angehaengt[0].innerHTML, ts: _els['tsuche-body'].innerHTML});"]
    (e,) = _lauf(tmp_path, DOM, PC_STUBS, *teile, *lauf)
    _pruefen(e["dub"], mindestens=2)
    _pruefen(e["eig"], mindestens=2)
    _pruefen(e["ts"], mindestens=1)


def test_handy_liste(tmp_path):
    q = _handy()
    teile = [_esc_funktion(q), _js_funktion(q, "malen")]
    (e,) = _lauf(tmp_path, DOM, *teile,
                 "_els['suche']={value:''}; _els['liste']=_el();",
                 f"let daten=[{json.dumps(_eintrag())}];",
                 "malen(); aus({html: _els['liste'].innerHTML});")
    tags = _pruefen(e["html"], mindestens=1)
    bilder = [dict(a) for t, a in tags if t == "img"]
    assert bilder and bilder[0]["src"] == BILD, "esc der Handy-Seite muss Anführungszeichen maskieren"


# --------------------------------------------------------------- Zulauf 1: Datei-Tag

def test_id_tag_wird_nur_als_plausible_id_uebernommen(monkeypatch, tmp_path):
    """Der Schreiber prüft `_plausible_id`, der Leser tat es nicht: ein Tag aus
    einer fremden Datei wurde ungeprüft zum Schlüssel."""
    datei = tmp_path / "lied.mp3"
    datei.write_bytes(b"")
    monkeypatch.setattr(app, "_tag_lesen", lambda pfad, schluessel: SCHLUESSEL)
    assert app._id_tag_lesen(str(datei)) == ""
    monkeypatch.setattr(app, "_tag_lesen", lambda pfad, schluessel: "lokal-abc123")
    assert app._id_tag_lesen(str(datei)) == "", "eigene Kunst-Ids sind keine Video-Ids"
    monkeypatch.setattr(app, "_tag_lesen", lambda pfad, schluessel: "dQw4w9WgXcQ")
    assert app._id_tag_lesen(str(datei)) == "dQw4w9WgXcQ"


def test_auffaellige_schluessel_werden_nur_gemeldet(monkeypatch):
    """Abweichende Schlüssel im Bestand: melden, nie löschen oder umschreiben."""
    bestand = {"dQw4w9WgXcQ|audio": {"titel": "a"},
               "https://example.org/v/1|beste": {"titel": "b"},
               SCHLUESSEL: {"titel": "c"},
               "zeile\numbruch|audio": {"titel": "d"}}
    monkeypatch.setattr(app, "_geladen", json.loads(json.dumps(bestand)))
    assert sorted(app.auffaellige_schluessel()) == sorted([SCHLUESSEL, "zeile\numbruch|audio"])
    assert app._geladen == bestand, "der Bestand bleibt unverändert"
