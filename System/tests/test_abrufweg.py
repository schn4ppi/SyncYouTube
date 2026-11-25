"""Ausweich-Leiter bei HTTP 403 und Einstellung „Abrufweg“ (22.11.2026:
„Ja, Leiter + Einstellung").

Geprüft wird ohne Netz: die Leiter selbst (`abrufweg.py`) und ihr Einbau in
`_download_lauf` und `_info_abrufen` mit einer yt-dlp-Attrappe, die je nach
Optionen (Cookies, Player-Clients) antwortet.

Nicht gemessen (P6): ob YouTube auf einem anderen Weg tatsächlich liefert,
wenn ein Weg gesperrt ist (das zeigt nur ein echter 403), und ob `android_vr`
ohne PO-Token für jedes Video HLS-Formate hat.
"""
import contextlib
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import abrufweg  # noqa: E402
import youtube_app as app  # noqa: E402

E403 = "ERROR: unable to download video data: HTTP Error 403: Forbidden"
E429 = "ERROR: unable to download video data: HTTP Error 429: Too Many Requests"
BOT = ("ERROR: [youtube] abc: Sign in to confirm you're not a bot. Use --cookies-from-browser "
       "or --cookies for the authentication.")
ALTER = "ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users."
NETZ = "ERROR: unable to download video data: <urlopen error timed out>"
MIT_COOKIES = {"quiet": True, "cookiesfrombrowser": ("firefox",)}


@pytest.fixture(autouse=True)
def _frisch():
    abrufweg.vergessen()
    yield
    abrufweg.vergessen()


def _weg_von(opts):
    """Welcher Weg steckt in diesen Optionen? (für die Attrappe; die Tests laden
    immer mit Cookies, also heißt »ohne Cookies« ein Weg ohne Anmeldung)"""
    clients = tuple(((opts.get("extractor_args") or {}).get("youtube") or {}).get("player_client") or ())
    merkmal = (clients, "cookiesfrombrowser" in opts)
    for name, w in abrufweg.WEGE.items():
        if (tuple(w["clients"] or ()), w["cookies"]) == merkmal:
            return name
    return f"unbekannt{merkmal}"


# ------------------------------------------------------------------ die Wege

def test_standard_laesst_die_optionen_wie_sie_sind():
    neu = abrufweg.anwenden(MIT_COOKIES, "standard")
    assert neu == MIT_COOKIES and neu is not MIT_COOKIES


def test_ohne_embedded_behaelt_die_cookies_und_nimmt_web_embedded_raus():
    neu = abrufweg.anwenden(MIT_COOKIES, "ohne_embedded")
    assert neu["cookiesfrombrowser"] == ("firefox",)
    assert neu["extractor_args"]["youtube"]["player_client"] == ["default", "-web_embedded"]


@pytest.mark.parametrize("name, clients", [("ohne_anmeldung", None), ("visionos", ["visionos"]),
                                           ("android_vr", ["android_vr"])])
def test_wege_ohne_anmeldung_lassen_die_cookies_weg(name, clients):
    neu = abrufweg.anwenden(MIT_COOKIES, name)
    assert "cookiesfrombrowser" not in neu
    assert (neu.get("extractor_args") or {}).get("youtube", {}).get("player_client") == clients
    assert MIT_COOKIES == {"quiet": True, "cookiesfrombrowser": ("firefox",)}, "Original verändert"


def test_vorhandene_extractor_args_bleiben_erhalten():
    opts = {"extractor_args": {"youtube": {"lang": ["de"]}, "generic": {"x": ["1"]}}}
    neu = abrufweg.anwenden(opts, "tv")
    assert neu["extractor_args"] == {"youtube": {"lang": ["de"], "player_client": ["tv_samsung"]},
                                     "generic": {"x": ["1"]}}
    assert opts["extractor_args"]["youtube"] == {"lang": ["de"]}, "Original verändert"


# ------------------------------------------------------------------ die Leiter

def test_automatische_leiter_mit_cookies():
    """Die letzte Stufe ist visionos, nicht android_vr: gemessen 23.11.2026
    scheiterte ein Audio-Download über android_vr mit 403 (PO-Token-Pflicht),
    über visionos klappte er."""
    assert abrufweg.leiter("auto", True) == ["standard", "ohne_embedded", "ohne_anmeldung", "visionos"]


def test_ohne_cookies_fallen_gleich_wirkende_wege_weg():
    """Ohne Anmeldung sind Standard, ohne web_embedded und ohne Anmeldung
    derselbe Weg: er wird nur einmal versucht."""
    assert abrufweg.leiter("auto", False) == ["standard", "visionos"]


@pytest.mark.parametrize("modus", ["ohne_anmeldung", "tv", "android_vr"])
def test_fester_abrufweg_ist_genau_ein_weg(modus):
    assert abrufweg.leiter(modus, True) == [modus]


def test_unbekannter_modus_heisst_automatisch():
    assert abrufweg.leiter("quatsch", True) == list(abrufweg.AUTO_LEITER)


def test_der_zuletzt_erfolgreiche_weg_kommt_zuerst():
    assert abrufweg.leiter("auto", True, letzter="ohne_anmeldung") == [
        "ohne_anmeldung", "standard", "ohne_embedded", "visionos"]


def test_fester_modus_ignoriert_den_letzten_weg():
    assert abrufweg.leiter("tv", True, letzter="android_vr") == ["tv"]


def test_naechster_weg_fuer_den_knopf():
    assert abrufweg.naechster(["standard"], True) == "ohne_embedded"
    assert abrufweg.naechster(list(abrufweg.AUTO_LEITER), True) == "tv"
    assert abrufweg.naechster(list(abrufweg.KATALOG), True) is None
    # ohne Cookies wirken standard/ohne_embedded/ohne_anmeldung gleich
    assert abrufweg.naechster(["standard"], False) == "visionos"


@pytest.mark.parametrize("text, erwartet", [
    (E403, True), ("HTTP Error 403: Forbidden", True), ("403 Forbidden", True),
    (E429, False), (BOT, False), (NETZ, False), ("Video dQw403abcXY fehlt", False),
])
def test_was_ein_403_ist(text, erwartet):
    assert abrufweg.ist_403(text) is erwartet


def _aufruf(antworten, gesehen):
    """Attrappe des yt-dlp-Aufrufs: antworten[weg] = Text (Ausnahme) oder Ergebnis."""
    def aufruf(opts):
        weg = _weg_von(opts)
        gesehen.append(weg)
        antwort = antworten.get(weg, {"title": "ok"})
        if isinstance(antwort, str):
            raise RuntimeError(antwort)
        return antwort
    return aufruf


@pytest.mark.parametrize("stufe", [0, 1, 2, 3])
def test_jede_stufe_kann_retten(stufe):
    """403 auf den Stufen vor `stufe`, dann klappt es: genau diese Wege, je einmal."""
    wege = abrufweg.leiter("auto", True)
    antworten = {w: E403 for w in wege[:stufe]}
    gesehen, versucht = [], []
    ergebnis, weg = abrufweg.mit_leiter(MIT_COOKIES, _aufruf(antworten, gesehen), wege,
                                        versucht=versucht)
    assert weg == wege[stufe] and ergebnis == {"title": "ok"}
    assert gesehen == wege[:stufe + 1] == versucht
    assert len(set(gesehen)) == len(gesehen), "ein Weg wurde zweimal versucht"


def test_kein_weg_wird_zweimal_versucht_und_am_ende_ist_es_eine_sperre():
    wege = abrufweg.leiter("auto", True)
    gesehen = []
    with pytest.raises(abrufweg.LeiterFehler) as fehler:
        abrufweg.mit_leiter(MIT_COOKIES, _aufruf({w: E403 for w in wege}, gesehen), wege)
    assert gesehen == wege
    text = str(fehler.value)
    assert app._ist_sperre(text), "nach allen Stufen muss die Sperr-Pause greifen"
    for w in wege:
        assert abrufweg.WEGE[w]["titel"] in text


@pytest.mark.parametrize("drossel", [E429, BOT])
def test_429_und_bot_ohne_leiter(drossel):
    gesehen = []
    with pytest.raises(RuntimeError, match="429|bot"):
        abrufweg.mit_leiter(MIT_COOKIES, _aufruf({"standard": drossel}, gesehen),
                            abrufweg.leiter("auto", True))
    assert gesehen == ["standard"]


def test_drossel_auf_einer_spaeteren_stufe_bricht_die_leiter_ab():
    gesehen = []
    with pytest.raises(RuntimeError, match="429"):
        abrufweg.mit_leiter(MIT_COOKIES, _aufruf({"standard": E403, "ohne_embedded": E429}, gesehen),
                            abrufweg.leiter("auto", True))
    assert gesehen == ["standard", "ohne_embedded"]


def test_gewoehnlicher_fehler_geht_ohne_leiter_hinaus():
    gesehen = []
    with pytest.raises(RuntimeError, match="timed out"):
        abrufweg.mit_leiter(MIT_COOKIES, _aufruf({"standard": NETZ}, gesehen),
                            abrufweg.leiter("auto", True))
    assert gesehen == ["standard"]


def test_fester_weg_meldet_den_originalfehler():
    with pytest.raises(RuntimeError, match="403"):
        abrufweg.mit_leiter(MIT_COOKIES, _aufruf({"tv": E403}, []), ["tv"])


def test_erfolg_wird_gemerkt_und_beim_naechsten_video_zuerst_versucht():
    wege = abrufweg.leiter("auto", True)
    abrufweg.mit_leiter(MIT_COOKIES, _aufruf({"standard": E403, "ohne_embedded": E403}, []), wege)
    assert abrufweg.zuletzt() == "ohne_anmeldung"
    gesehen = []
    abrufweg.mit_leiter(MIT_COOKIES, _aufruf({}, gesehen),
                        abrufweg.leiter("auto", True, letzter=abrufweg.zuletzt()))
    assert gesehen == ["ohne_anmeldung"]


def test_ohne_anmeldung_sagt_was_dann_nicht_geht():
    """Scheitert der Weg ohne Cookies an einer Altersgrenze, sagt die Meldung,
    warum — statt still zu scheitern."""
    wege = abrufweg.leiter("auto", True)
    antworten = {w: E403 for w in wege}
    antworten["ohne_anmeldung"] = ALTER
    with pytest.raises(abrufweg.LeiterFehler) as fehler:
        abrufweg.mit_leiter(MIT_COOKIES, _aufruf(antworten, []), wege)
    assert abrufweg.HINWEIS_OHNE_ANMELDUNG in str(fehler.value)
    assert "confirm your age" in str(fehler.value)


def test_abbruch_geht_sofort_hinaus():
    class Abbruch(Exception):
        pass

    def aufruf(opts):
        raise Abbruch()
    with pytest.raises(Abbruch):
        abrufweg.mit_leiter(MIT_COOKIES, aufruf, abrufweg.leiter("auto", True), durchlassen=(Abbruch,))


# ------------------------------------------------------- Einbau in die App

class _YdlAttrappe:
    """Statt `app._ydl`: antwortet je Weg aus `antworten`, notiert jeden Weg."""

    def __init__(self, antworten):
        self.antworten = antworten
        self.wege = []

    def __call__(self, opts):
        attrappe = self

        class Ydl:
            def extract_info(self, url, download=False):
                weg = _weg_von(opts)
                attrappe.wege.append(weg)
                antwort = attrappe.antworten.get(weg, {"title": "Titel", "requested_downloads": []})
                if isinstance(antwort, str):
                    raise RuntimeError(antwort)
                return antwort

        @contextlib.contextmanager
        def cm():
            yield Ydl()
        return cm()


@pytest.fixture
def welt(monkeypatch, tmp_path):
    monkeypatch.setitem(app.CFG, "cookies_browser", "firefox")
    monkeypatch.setitem(app.CFG, "abrufweg", "auto")
    monkeypatch.setitem(app.CFG, "untertitel", False)
    monkeypatch.setattr(app.Q, "speichern", lambda *a, **k: None)
    monkeypatch.setattr(app, "FEHLER_LOG", str(tmp_path / "yt_fehler.jsonl"))
    monkeypatch.setattr(app, "geladen_merken", lambda item: None)
    monkeypatch.setattr(app, "untertitel_einsortieren", lambda: None)
    monkeypatch.setattr(app, "autotag_nach_download", lambda item: None)
    monkeypatch.setattr(app, "_technik", lambda pfad: {})
    monkeypatch.setattr(app, "ziel_ordner", lambda: str(tmp_path))
    monkeypatch.setattr(app, "DROSSEL", {})
    monkeypatch.setattr(app, "_youtube_gesperrt_bis", 0.0)   # die Sperr-Pause bleibt im Test

    def setzen(antworten):
        attrappe = _YdlAttrappe(antworten)
        monkeypatch.setattr(app, "_ydl", attrappe)
        return attrappe
    return setzen


def _item():
    return {"id": "leiter1", "qualitaet": "720p", "status": "laeuft", "titel": "Probe",
            "url": "https://www.youtube.com/watch?v=ABCdef12345", "prozent": 0.0,
            "geladen": 0, "gesamt": 0, "geschw": 0, "phase": "", "versuche": 0,
            "fehler": "", "naechster_versuch": 0, "datei": ""}


def test_download_rettet_sich_ueber_den_naechsten_weg(welt):
    attrappe = welt({"standard": E403})
    item = _item()
    app._download_lauf(item)
    assert item["status"] == "fertig", item.get("fehler")
    assert attrappe.wege == ["standard", "ohne_embedded"]
    assert item["weg"] == "ohne_embedded"


def test_download_nach_allen_stufen_ist_eine_sperre(welt):
    attrappe = welt({w: E403 for w in abrufweg.KATALOG})
    item = _item()
    app._download_lauf(item)
    assert attrappe.wege == list(abrufweg.AUTO_LEITER)
    assert item["status"] == "fehler" and not item["naechster_versuch"]
    assert app.youtube_gesperrt() > 0, "nach allen Stufen greift die 30-Minuten-Pause"
    assert item["weg_naechster"] == "tv", "der Knopf bietet den noch nicht versuchten Weg an"
    assert abrufweg.HINWEIS_OHNE_ANMELDUNG in item["fehler"] or "ohne Anmeldung" in item["fehler"]


def test_download_bei_429_ohne_leiter(welt):
    attrappe = welt({"standard": E429})
    item = _item()
    app._download_lauf(item)
    assert attrappe.wege == ["standard"]
    assert item["status"] == "fehler"


def test_download_mit_festem_abrufweg(welt, monkeypatch):
    monkeypatch.setitem(app.CFG, "abrufweg", "tv")
    attrappe = welt({})
    item = _item()
    app._download_lauf(item)
    assert attrappe.wege == ["tv"] and item["status"] == "fertig"


def test_knopf_anderen_weg_versuchen(welt):
    """Nach dem Scheitern aller Leiter-Stufen: der Knopf setzt den nächsten Weg,
    und der nächste Lauf versucht genau ihn."""
    attrappe = welt({w: E403 for w in abrufweg.AUTO_LEITER})
    item = _item()
    app._download_lauf(item)
    assert item["weg_naechster"] == "tv" and item["weg_naechster_titel"] == "TV"
    app.Q.items.append(item)
    try:
        app.Handler._action(None, {"art": "anderer_weg", "id": item["id"]})
    finally:
        app.Q.items.remove(item)
    assert item["status"] == "wartend" and item["weg_wunsch"] == "tv"
    attrappe.wege.clear()
    item["status"] = "laeuft"
    app._download_lauf(item)
    assert attrappe.wege == ["tv"] and item["status"] == "fertig"


def test_aufloesen_nimmt_die_leiter_auch(welt):
    attrappe = welt({"standard": E403, "ohne_embedded": {"title": "Video", "id": "ABCdef12345"}})
    info = app._info_abrufen("https://www.youtube.com/watch?v=ABCdef12345", dict(MIT_COOKIES))
    assert info["title"] == "Video"
    assert attrappe.wege == ["standard", "ohne_embedded"]


def test_einstellung_abrufweg_wird_geprueft(monkeypatch):
    monkeypatch.setitem(app.CFG, "abrufweg", "auto")
    monkeypatch.setattr(app, "_cfg_speichern", lambda: None)
    app.Handler._config(None, {"abrufweg": "tv"})
    assert app.CFG["abrufweg"] == "tv"
    app.Handler._config(None, {"abrufweg": "quatsch"})
    assert app.CFG["abrufweg"] == "tv", "ein unbekannter Wert wird nicht übernommen"


def test_meldung_ist_deutsch_und_passt_in_die_anzeige():
    """Nach allen Wegen: deutscher Satz vorn, je Weg nur „403“, und das Ganze
    passt in die 300 Zeichen der Anzeige (vorher mitten im Wort abgeschnitten)."""
    wege = abrufweg.leiter("auto", True)
    with pytest.raises(abrufweg.LeiterFehler) as fehler:
        abrufweg.mit_leiter(MIT_COOKIES, _aufruf({w: E403 for w in wege}, []), wege)
    text = str(fehler.value)
    assert text.startswith(f"YouTube hat alle {len(wege)} Abrufwege abgelehnt (HTTP 403).")
    assert "unable to download" not in text
    assert len(app._fehltext(text)) == len(text) <= 300


def test_hinweis_ohne_anmeldung_nur_wer_angemeldet_war():
    wege = abrufweg.leiter("auto", False)
    assert len(wege) > 1

    def immer_403(opts):                             # _weg_von kennt nur Läufe mit Cookies
        raise RuntimeError(E403)
    with pytest.raises(abrufweg.LeiterFehler) as fehler:
        abrufweg.mit_leiter({}, immer_403, wege)
    assert abrufweg.HINWEIS_OHNE_ANMELDUNG not in str(fehler.value)
    assert app._ist_sperre(str(fehler.value))


def test_wechsel_wird_fuer_die_anzeige_gemeldet(welt, monkeypatch):
    """Während des Wechsels stehen Stufe, Anzahl und Weg am Eintrag, und der
    Fortschritt des gescheiterten Wegs ist genullt."""
    attrappe = welt({"standard": E403, "ohne_embedded": E403})
    item = _item()
    gesehen = []

    def beobachter(opts):
        gesehen.append((item.get("weg_stufe"), item.get("weg_stufen"),
                        item.get("weg_titel"), item["prozent"]))
        item["prozent"] = 37.0                       # der Weg hat schon etwas geladen
        return attrappe(opts)
    monkeypatch.setattr(app, "_ydl", beobachter)
    app._download_lauf(item)
    assert item["status"] == "fertig", item.get("fehler")
    assert gesehen == [(None, None, None, 0.0), (2, 4, "ohne web_embedded", 0.0),
                       (3, 4, "ohne Anmeldung", 0.0)]
    assert item["weg"] == "ohne_anmeldung" and item["weg_titel"] == "ohne Anmeldung"


def test_neuer_lauf_vergisst_den_alten_wechsel():
    item = {"weg": "visionos", "weg_titel": "Vision Pro", "weg_stufe": 4, "weg_stufen": 4}
    abrufweg.eintrag_vorbereiten(item)
    assert not {"weg", "weg_titel", "weg_stufe", "weg_stufen"} & set(item)


def test_vorgabe_ist_automatisch():
    assert app.STANDARD_CONFIG["abrufweg"] == "auto" == abrufweg.STANDARD_MODUS
