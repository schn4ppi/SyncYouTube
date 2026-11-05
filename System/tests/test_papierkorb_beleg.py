# -*- coding: utf-8 -*-
"""Keine Datei geht still verloren (05.11.2026, dieselbe Lücke wie in SyncFindus).

`SHFileOperationW` mit FOF_ALLOWUNDO löscht eine Datei ab 260 Zeichen vollem Pfad endgültig und
meldet trotzdem 0, gemessen am echten Windows (Gedächtnis `papierkorb-sicher-verschieben`).

Hier läuft die echte `_in_papierkorb`. Nur der Windows-Aufruf selbst ist eine Attrappe
(`windows`): Sie liest aus derselben Struktur wie Windows und baut das gemessene Verhalten nach.
Die harten Links entstehen wirklich auf der Platte. Der echte Papierkorb bleibt unberührt, die
conftest sperrt ihn für die ganze Suite. Ob eine Datei überlebt hat, zeigt ihr Inhalt
(`_fundorte`), nicht ihr Name.
"""
import ast
import ctypes
import glob
import json
import os
import stat
import sys
import types

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402

LANG = "\\\\?\\"
FOF_ALLOWUNDO = 0x40
GEMESSENE_GRENZE = 260
INHALT = b"MUSIK"


def _einheiten(pfad):
    """Pfadlänge, wie Windows sie zählt: in UTF-16-Einheiten."""
    return len(pfad.encode("utf-16-le")) // 2


def _datei(ordner, laenge, endung=".mp3", inhalt=INHALT, vorn=""):
    """Legt in `ordner` eine Datei an, deren voller Pfad genau `laenge` Einheiten lang ist."""
    os.makedirs(LANG + str(ordner), exist_ok=True)
    fuellung = laenge - _einheiten(str(ordner)) - 1 - _einheiten(vorn) - _einheiten(endung)
    assert 0 < fuellung <= 240, f"Der Testordner passt nicht zur Länge {laenge}: {ordner}"
    pfad = os.path.join(str(ordner), vorn + "x" * fuellung + endung)
    assert _einheiten(pfad) == laenge
    with open(LANG + pfad, "wb") as f:
        f.write(inhalt)
    return pfad


def _kurz(ordner, name="Titel [abcdef12345].mp3", inhalt=INHALT):
    """Eine Datei weit unter der Grenze, gleich wie tief der Temp-Ordner liegt."""
    os.makedirs(ordner, exist_ok=True)
    pfad = os.path.join(str(ordner), name)
    assert _einheiten(pfad) < GEMESSENE_GRENZE - 20
    with open(pfad, "wb") as f:
        f.write(inhalt)
    return pfad


def _inhalt(pfad):
    with open(LANG + str(pfad), "rb") as f:
        return f.read()


def _fundorte(wurzel, inhalt=INHALT):
    """Alle Dateien unter `wurzel` mit genau diesem Inhalt, gleich unter welchem Namen."""
    treffer = []
    for ordner, _, namen in os.walk(LANG + str(wurzel)):
        for name in namen:
            with open(os.path.join(ordner, name), "rb") as f:
                if f.read() == inhalt:
                    treffer.append(os.path.join(ordner, name)[len(LANG):])
    return treffer


def _meldungen():
    try:
        with open(app.FEHLER_LOG, encoding="utf-8") as f:
            zeilen = [json.loads(z) for z in f.read().splitlines()]
    except OSError:
        return []
    return [z for z in zeilen if z.get("art") == "papierkorb"]


class Windows:
    """`SHFileOperationW` mit dem gemessenen Verhalten. Die Ablage spielt `$Recycle.Bin`: Ein
    Umbenennen auf demselben Laufwerk, darum bleibt der Link-Zähler gleich, wie im Echten.

    `art`: "gemessen", "loescht_still" (steht für jeden anderen Grund: `NukeOnDelete`, eine Datei
    größer als der Papierkorb, was noch niemand gemessen hat) oder "verweigert" (offene Datei)."""

    def __init__(self, ablage):
        self.ablage = ablage
        self.art = "gemessen"
        self.gesehen = []
        self.im_korb = []

    def __call__(self, zeiger):
        op = zeiger._obj
        pfad = op.pFrom
        self.gesehen.append(pfad)
        if self.art == "verweigert":
            return 124
        endgueltig = (self.art == "loescht_still" or _einheiten(pfad) >= GEMESSENE_GRENZE
                      or not op.fFlags & FOF_ALLOWUNDO)
        if endgueltig:
            os.remove(LANG + pfad)
            return 0
        os.makedirs(self.ablage, exist_ok=True)
        ziel = os.path.join(self.ablage, f"$R{len(self.gesehen)}")
        os.rename(LANG + pfad, ziel)
        self.im_korb.append(ziel)
        return 0


@pytest.fixture
def windows(tmp_path, monkeypatch):
    attrappe = Windows(str(tmp_path / "recycle"))
    monkeypatch.setattr(ctypes.windll.shell32, "SHFileOperationW", attrappe)
    return attrappe


@pytest.fixture
def dl(tmp_path, monkeypatch):
    ordner = tmp_path / "dl"
    (ordner / "MP3").mkdir(parents=True)
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(ordner))
    monkeypatch.setattr(app, "_sag", lambda *a, **k: None)
    return ordner


@pytest.fixture
def ohne_langpfade(monkeypatch):
    """Windows ab Werk (`LongPathsEnabled=0`, auf JBs PC ist es 1): Ein Pfad ab 260 Einheiten
    scheitert, ein neuer Ordner schon ab 248, außer in der Langform `\\\\?\\`. Ein veröffentlichtes
    Programm trifft genau das."""
    def zu_lang(pfad, grenze=GEMESSENE_GRENZE):
        pfad = os.fspath(pfad)
        return not pfad.startswith(LANG) and _einheiten(os.path.abspath(pfad)) >= grenze

    def sperren(name, stellen, grenze=GEMESSENE_GRENZE):
        echt = getattr(os, name)

        def gesperrt(*a, **k):
            for i in stellen:
                if zu_lang(a[i], grenze):
                    raise FileNotFoundError(3, "Der Pfad wurde nicht gefunden", os.fspath(a[i]))
            return echt(*a, **k)
        monkeypatch.setattr(os, name, gesperrt)

    sperren("mkdir", (0,), grenze=GEMESSENE_GRENZE - 12)
    for name, stellen in (("rename", (0, 1)), ("link", (0, 1)), ("stat", (0,)), ("remove", (0,)),
                          ("rmdir", (0,)), ("chmod", (0,))):
        sperren(name, stellen)
    echt_lexists = os.path.lexists
    monkeypatch.setattr(os.path, "lexists", lambda p: not zu_lang(p) and echt_lexists(p))


# ---------------------------------------------------------------- Die gemessene Grenze

@pytest.mark.parametrize("laenge", [260, 261, 275])
def test_ab_260_zeichen_ueberlebt_die_datei(dl, windows, tmp_path, laenge):
    """Der gemessene Verlust: Windows meldet 0, die Datei ist endgültig weg. Jetzt geht der Pfad
    gar nicht erst an Windows, sondern rückholbar nach `_Papierkorb`, und das wird gemeldet."""
    pfad = _datei(dl / "MP3", laenge)
    ort = app._rueckholbar_entfernen(pfad)
    assert _fundorte(tmp_path), "die Datei ist endgültig gelöscht, obwohl Windows Erfolg meldete"
    assert ort == os.path.join(str(dl / "_Papierkorb"), os.path.basename(pfad))
    assert _inhalt(ort) == INHALT and not os.path.lexists(LANG + pfad)
    assert windows.gesehen == [], "ein Pfad ab 260 Zeichen ging an SHFileOperationW"
    assert len(_meldungen()) == 1 and "zu lang" in _meldungen()[0]["text"]


def test_entf_in_der_bibliothek_verliert_keine_lange_datei(dl, windows, tmp_path):
    """Der Weg, den JB jeden Tag nimmt: Der Titel verschwindet aus den Listen, die Datei bleibt
    rückholbar."""
    pfad = _datei(dl / "MP3", 260)
    key = "abcdef12345|audio"
    app._geladen[key] = {"name": os.path.basename(pfad), "pfad": pfad}
    app._playlists.append({"id": "pl1", "name": "P", "items": [key]})
    app._datei_loeschen(key)
    assert len(_fundorte(tmp_path)) == 1, "die Datei ist endgültig gelöscht"
    assert windows.gesehen == [] and app._playlists[-1]["items"] == []


def test_bei_259_zeichen_nimmt_windows_die_datei(dl, windows):
    """Eine Einheit unter der Grenze bleibt alles beim Windows-Papierkorb, ohne Spur daneben."""
    pfad = _datei(dl / "MP3", 259)
    assert app._rueckholbar_entfernen(pfad) == "papierkorb"
    assert windows.gesehen == [pfad] and _inhalt(windows.im_korb[0]) == INHALT
    assert not (dl / "_Papierkorb").exists(), "der zweite Name blieb liegen"
    assert os.stat(windows.im_korb[0]).st_nlink == 1
    assert not _meldungen()


def test_emoji_zaehlt_wie_bei_windows_doppelt(dl, windows, tmp_path):
    """YouTube-Titel tragen Emojis. Für Python ist so eines ein Zeichen, für Windows zwei: Mit
    `len()` stünde dieser Pfad bei 259 und ginge an Windows, das bei 260 endgültig löscht."""
    pfad = _datei(dl / "MP3", 260, vorn="😀")
    assert len(pfad) == 259
    app._rueckholbar_entfernen(pfad)
    assert windows.gesehen == [] and len(_fundorte(tmp_path)) == 1


def test_relativer_pfad_zaehlt_mit_dem_ganzen_weg(dl, windows, monkeypatch):
    """Ein relativer Download-Ordner aus der config.json: Der kurze Text täuscht, Windows sieht
    den ganzen Weg."""
    pfad = _datei(dl / "MP3", 260)
    monkeypatch.chdir(dl / "MP3")
    assert app._in_papierkorb(os.path.basename(pfad)) is False
    assert windows.gesehen == [] and _inhalt(pfad) == INHALT


def test_windows_aufruf_laesst_selbst_keinen_langen_pfad_durch(dl, windows):
    """Die Grenze gilt an der Stelle des Aufrufs, nicht nur eine Ebene darüber."""
    pfad = _datei(dl / "MP3", 260)
    assert app._in_papierkorb(pfad) is False
    assert windows.gesehen == [] and _inhalt(pfad) == INHALT


def test_name_ohne_gueltiges_utf16_bringt_nichts_ins_stolpern():
    """Windows erlaubt Namen mit einem einzelnen Surrogat, und `os.walk` liefert sie so. Eine
    Ausnahme hier bräche den ganzen Aufräum-Lauf ab."""
    assert app._pfad_einheiten("C:\\x\\a\ud800.mp3") == 11


# ---------------------------------------------------------------- Die direkten Aufrufer

def _untertitel(ordner, endung, lang, inhalt=INHALT):
    return _datei(ordner, 260, endung, inhalt) if lang else _kurz(ordner, "Clip" + endung, inhalt)


def _dublette_neben_dem_video(dl, _monkeypatch, lang):
    (dl / "Untertitel").mkdir()
    (dl / "Untertitel" / "abcdef12345.de.vtt").write_text("WEBVTT\n\nschon da", encoding="utf-8")
    return _untertitel(dl / "Video", " [abcdef12345].de.vtt", lang), app.untertitel_einsortieren


def _srt_neben_dem_video(dl, _monkeypatch, lang):
    srt = b"1\n00:00:01,000 --> 00:00:02,000\nHallo\n"
    return _untertitel(dl / "Video", " [abcdef12345].en.srt", lang, srt), app.untertitel_einsortieren


def _waise_im_untertitel_ordner(dl, _monkeypatch, lang):
    return _untertitel(dl / "Untertitel", ".de.vtt", lang), app.untertitel_aufraeumen


def _waise_neben_dem_video(dl, _monkeypatch, lang):
    return _untertitel(dl / "Video", ".de.vtt", lang), app.untertitel_aufraeumen


def _abo_cache(dl, monkeypatch, lang):
    index = str(dl / "abo_index")
    if lang:
        index += "\\" + "i" * (245 - _einheiten(index))
    os.makedirs(LANG + index)
    monkeypatch.setattr(app, "ABO_INDEX_ORDNER", index)
    pfad = os.path.join(index, "a1b2c3d4.json")
    assert not lang or _einheiten(pfad) == 260
    with open(LANG + pfad, "wb") as f:
        f.write(INHALT)
    return pfad, lambda: app._abo_index_entfernen("a1b2c3d4")


DIREKTE_AUFRUFER = [_dublette_neben_dem_video, _srt_neben_dem_video, _waise_im_untertitel_ordner,
                    _waise_neben_dem_video, _abo_cache]


@pytest.mark.parametrize("welt", DIREKTE_AUFRUFER, ids=lambda w: w.__name__.strip("_"))
def test_direkter_aufrufer_verliert_keine_lange_datei(dl, windows, monkeypatch, tmp_path, welt):
    """Fünf Stellen riefen `_in_papierkorb` ohne jede Nachprüfung. Untertitel sind die längsten
    Namen im Download-Ordner: Sie tragen den Titel und dazu noch die Sprache."""
    pfad, lauf = welt(dl, monkeypatch, True)
    inhalt = _inhalt(pfad)
    lauf()
    assert _fundorte(tmp_path, inhalt), "die Datei ist endgültig gelöscht"
    assert windows.gesehen == []


@pytest.mark.parametrize("welt", DIREKTE_AUFRUFER, ids=lambda w: w.__name__.strip("_"))
def test_direkter_aufrufer_verliert_auf_einem_stick_nichts(dl, windows, monkeypatch, tmp_path, welt):
    """Dieselben Stellen umgingen auch die Laufwerksprüfung: Auf Wechseldatenträgern gibt es
    keinen Papierkorb, dort löscht Windows endgültig und meldet Erfolg. Kurze Pfade, sonst
    hielte schon die Grenze am Windows-Aufruf die Datei auf."""
    monkeypatch.setattr(app, "_laufwerk_art", lambda wurzel: 2)
    windows.art = "loescht_still"
    pfad, lauf = welt(dl, monkeypatch, False)
    inhalt = _inhalt(pfad)
    lauf()
    assert _fundorte(tmp_path, inhalt), "die Datei ist endgültig gelöscht"
    assert windows.gesehen == []


def test_kurze_untertitel_gehen_weiter_in_den_windows_papierkorb(dl, windows):
    """Der Normalfall bleibt: Eine verwaiste .vtt landet im Windows-Papierkorb und zählt."""
    pfad = _kurz(dl / "Untertitel", "verwaist.de.vtt")
    assert app.untertitel_aufraeumen() == 1
    assert windows.gesehen == [pfad] and not (dl / "_Papierkorb").exists()


# ---------------------------------------------------------------- Der Beleg über den zweiten Namen

def test_windows_loescht_still_die_datei_liegt_im_rueckfall(dl, windows):
    """Jeder Grund außer der Pfadlänge: Windows meldet 0, die Datei ist weg, aus dem Papierkorb
    käme sie nie zurück. Der zweite Name in `_Papierkorb` hält sie am Leben, und die Rückgabe sagt
    nicht „papierkorb“, sondern wo sie wirklich liegt."""
    windows.art = "loescht_still"
    pfad = _kurz(dl / "MP3")
    ort = app._rueckholbar_entfernen(pfad)
    assert ort == os.path.join(str(dl / "_Papierkorb"), os.path.basename(pfad))
    assert _inhalt(ort) == INHALT and windows.gesehen == [pfad]
    assert os.stat(ort).st_nlink == 1
    assert len(_meldungen()) == 1
    text = _meldungen()[0]["text"]
    assert "endgültig" in text and ort in text, f"die Meldung nennt den Ort nicht: {text}"


def test_windows_verweigert_die_datei_wandert_in_den_rueckfall(dl, windows):
    """Offene Datei: Windows antwortet 124 und tut nichts. Es bleibt genau ein Name übrig."""
    windows.art = "verweigert"
    pfad = _kurz(dl / "MP3")
    ort = app._rueckholbar_entfernen(pfad)
    assert ort == os.path.join(str(dl / "_Papierkorb"), os.path.basename(pfad))
    assert not os.path.lexists(pfad) and os.stat(ort).st_nlink == 1
    assert os.listdir(dl / "_Papierkorb") == [os.path.basename(pfad)]


def test_erfolg_laesst_einen_gefuellten_rueckfall_ordner_stehen(dl, windows):
    alt = dl / "_Papierkorb" / "alt.mp3"
    alt.parent.mkdir()
    alt.write_bytes(b"ALT")
    assert app._rueckholbar_entfernen(_kurz(dl / "MP3")) == "papierkorb"
    assert os.listdir(dl / "_Papierkorb") == ["alt.mp3"] and alt.read_bytes() == b"ALT"


def test_ohne_zweiten_namen_wird_windows_nicht_gefragt(dl, windows, monkeypatch):
    """FAT und exFAT kennen keine harten Links. Ohne Beleg darf Windows nicht ran, die Datei
    wandert gleich rückholbar nach `_Papierkorb`."""
    def kein_link(*a, **k):
        raise OSError("Das Dateisystem kennt keine harten Links")
    monkeypatch.setattr(os, "link", kein_link)
    pfad = _kurz(dl / "MP3")
    ort = app._rueckholbar_entfernen(pfad)
    assert windows.gesehen == []
    assert ort == os.path.join(str(dl / "_Papierkorb"), os.path.basename(pfad))
    assert _inhalt(ort) == INHALT and len(_meldungen()) == 1


def test_ohne_aussage_des_zaehlers_faellt_der_letzte_name_nie(dl, windows, tmp_path, monkeypatch):
    """Ein Dateisystem legt harte Links an, führt den Zähler aber nicht: Er bleibt bei 1, „gleich
    geblieben“ belegt dann nichts. Der zweite Name darf nur fallen, wenn der Zähler noch einen
    anderen Namen zeigt."""
    windows.art = "loescht_still"
    echt = os.stat
    monkeypatch.setattr(os, "stat", lambda p, **k: (types.SimpleNamespace(st_nlink=1)
                                                    if "_Papierkorb" in str(p) else echt(p, **k)))
    app._rueckholbar_entfernen(_kurz(dl / "MP3"))
    assert _fundorte(tmp_path), "die Datei ist endgültig gelöscht"


def test_schreibschutz_laesst_keinen_zweiten_namen_zurueck(dl, windows):
    """Schreibschutz gilt für die Datei, nicht für den Namen, und sperrt auch das Entfernen des
    zweiten Namens. Sonst läge die Datei im Papierkorb und zugleich in `_Papierkorb`."""
    pfad = _kurz(dl / "MP3")
    os.chmod(pfad, stat.S_IREAD)
    assert app._rueckholbar_entfernen(pfad) == "papierkorb"
    assert not (dl / "_Papierkorb").exists()
    assert os.stat(windows.im_korb[0]).st_nlink == 1


def test_gerettete_datei_ueberschreibt_nichts(dl, windows):
    windows.art = "loescht_still"
    pfad = _kurz(dl / "MP3")
    alt = dl / "_Papierkorb" / os.path.basename(pfad)
    alt.parent.mkdir()
    alt.write_bytes(b"ALT")
    ort = app._rueckholbar_entfernen(pfad)
    assert alt.read_bytes() == b"ALT" and _inhalt(ort) == INHALT
    assert os.path.basename(ort) == os.path.splitext(os.path.basename(pfad))[0] + " (2).mp3"


# ---------------------------------------------------------------- Windows ab Werk

def test_ohne_langpfade_wandert_die_datei_trotzdem(dl, windows, ohne_langpfade):
    """Ohne die Langform scheiterte der Rückfall an genau den Dateien, für die er jetzt da ist.
    Die Rückgabe bleibt ein normaler Pfad: Sie landet in Meldungen und im Eintrag."""
    pfad = _datei(dl / "MP3", 260)
    ort = app._rueckholbar_entfernen(pfad)
    assert ort == os.path.join(str(dl / "_Papierkorb"), os.path.basename(pfad))
    assert _inhalt(ort) == INHALT and windows.gesehen == []


def test_ohne_langpfade_rettet_der_zweite_name_auch_am_ziel(tmp_path, dl, windows, ohne_langpfade):
    """Außerhalb des Download-Ordners liegt `_Papierkorb` neben der Datei. Der Pfad wird dadurch
    12 Einheiten länger: Die Quelle ist erlaubt, ihr zweiter Name läge jenseits der Grenze."""
    pfad = _datei(tmp_path / "anderswo", 255)
    windows.art = "loescht_still"
    ort = app._rueckholbar_entfernen(pfad)
    assert ort == os.path.join(str(tmp_path / "anderswo" / "_Papierkorb"), os.path.basename(pfad))
    assert _einheiten(ort) == 267 and _inhalt(ort) == INHALT


def test_zweiter_name_scheitert_nicht_an_der_ordnergrenze(tmp_path, dl, windows, ohne_langpfade):
    """Ein neuer Ordner scheitert ohne die Langform schon ab 248 Einheiten: `_Papierkorb` neben
    dieser Datei hat 252. Ohne Ordner kein zweiter Name, und ohne den fragt niemand Windows."""
    ordner = str(tmp_path / "anderswo") + "\\"
    ordner += "t" * (240 - _einheiten(ordner))
    pfad = _datei(ordner, 259)
    assert app._rueckholbar_entfernen(pfad) == "papierkorb"
    assert windows.gesehen == [pfad]


def test_kurzer_pfad_bleibt_wie_er_ist(dl):
    pfad = os.path.join(str(dl), "Titel.mp3")
    assert app._lang(pfad) == pfad


def test_langform_einer_freigabe():
    """Eine Freigabe hat eine eigene Langform: `\\\\?\\\\server` wäre ein anderer Pfad. Reine
    Zeichenkette, hier geht nichts ans Netz."""
    rest = "unc-probe.invalid\\freigabe\\" + "x" * 250 + ".mp3"
    assert app._lang("\\\\" + rest) == "\\\\?\\UNC\\" + rest


# ---------------------------------------------------------------- Wächter

def _rufer(quelltext, gerufen):
    """Namen der Funktionen, die `gerufen` aufrufen: der Aufruf zählt, nicht die Erwähnung."""
    funde = set()
    for funktion in ast.walk(ast.parse(quelltext)):
        if isinstance(funktion, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for knoten in ast.walk(funktion):
                if isinstance(knoten, ast.Call):
                    ziel = knoten.func
                    if getattr(ziel, "id", getattr(ziel, "attr", "")) == gerufen:
                        funde.add(funktion.name)
    return funde


def _rufer_im_programm(gerufen):
    funde = {}
    for datei in glob.glob(os.path.join(MODUL_DIR, "*.py")):
        with open(datei, encoding="utf-8") as f:
            for name in _rufer(f.read(), gerufen):
                funde[name] = os.path.basename(datei)
    return funde


def test_nur_der_beleg_weg_ruft_den_windows_papierkorb():
    """Fünf direkte Aufrufer waren die Lücke. Wer eine Datei entfernt, geht über
    `_rueckholbar_entfernen`, nie an der Prüfung des Ergebnisses vorbei."""
    assert _rufer_im_programm("_in_papierkorb") == {"_papierkorb_mit_beleg": "youtube_app.py"}
    assert _rufer_im_programm("SHFileOperationW") == {"_in_papierkorb": "youtube_app.py"}


def test_gegenprobe_direkter_aufrufer_wird_gefunden():
    quelle = ("def aufraeumen(p):\n    return _in_papierkorb(p)\n"
              "def nur_erwaehnt():\n    return '_in_papierkorb'\n")
    assert _rufer(quelle, "_in_papierkorb") == {"aufraeumen"}
