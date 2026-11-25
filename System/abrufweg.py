# -*- coding: utf-8 -*-
"""Abrufwege zu YouTube und die Ausweich-Leiter bei HTTP 403 (22.11.2026:
„Ja, Leiter + Einstellung").

WARUM. Bis v.1.3.5 galt jeder 403 als Sperre: kein zweiter Versuch, 30 Minuten
Pause. Ein 403 heißt aber oft nur, dass YouTube EINEN Weg zumacht, nicht die
Verbindung: im November 2026 verlangte YouTube für den Client `web_embedded` ein
PO-Token (yt-dlp #17989), andere Clients liefen weiter. Darum versucht die App
dasselbe Video nach einem 403 über einen anderen Weg, jeden Weg höchstens
einmal. Erst wenn alle scheitern, ist es eine echte Sperre.

DIE WEGE (Stand yt-dlp 2026.10.26, `yt_dlp/extractor/youtube/_base.py`):
- `standard`        die Einstellung, wie sie ist (mit den Browser-Cookies, falls an).
- `ohne_embedded`   dieselben Clients ohne `web_embedded` (der Client des
                    November-403). Wirkt nur mit Anmeldung: ohne Anmeldung fragt
                    yt-dlp `web_embedded` ohnehin nicht.
- `ohne_anmeldung`  ohne Cookies; yt-dlp fragt dann `tv_samsung, visionos, web`.
                    Kostet Premium-Qualität, altersbeschränkte Videos und Inhalte
                    nur für Kanalmitglieder.
- `visionos`        nur `visionos`, ohne Cookies (der Client kann keine). Braucht
                    weder JavaScript noch PO-Token: eine ganz andere Client-Familie.
- `tv`              nur `tv_samsung` (unterstützt Cookies, braucht kein PO-Token).
- `android_vr`      nur `android_vr`, ohne Cookies. Für direkte Downloads verlangt
                    er in 2026.10.26 ein PO-Token; GEMESSEN 23.11.2026: ein
                    Audio-Download über ihn endete mit 403, über `visionos` klappte er.

Die automatische Leiter ist `standard, ohne_embedded, ohne_anmeldung, visionos`:
erst der Weg mit dem geringsten Verlust, zuletzt ein ganz anderer Client. Der
Auftrag schlug zuletzt `android_vr` vor; nach der Messung oben steht dort
`visionos`. `android_vr` bleibt als fester Weg wählbar (Besitzer-Liste).

Reine Logik ohne Netz: `youtube_app` ruft `mit_leiter` mit seinem yt-dlp-Aufruf
(Wächter `tests/test_abrufweg.py`).
"""
import copy
import logging
import re
import threading

WEGE = {
    "standard": {"titel": "Standard", "cookies": True, "clients": None},
    "ohne_embedded": {"titel": "ohne web_embedded", "cookies": True,
                      "clients": ("default", "-web_embedded")},
    "ohne_anmeldung": {"titel": "ohne Anmeldung", "cookies": False, "clients": None},
    "visionos": {"titel": "Vision Pro", "cookies": False, "clients": ("visionos",)},
    "tv": {"titel": "TV", "cookies": True, "clients": ("tv_samsung",)},
    "android_vr": {"titel": "Android VR", "cookies": False, "clients": ("android_vr",)},
}
# Reihenfolge für den Knopf „Anderen Weg versuchen“: alle Wege, die Leiter vorn.
KATALOG = ("standard", "ohne_embedded", "ohne_anmeldung", "visionos", "tv", "android_vr")
AUTO_LEITER = ("standard", "ohne_embedded", "ohne_anmeldung", "visionos")
# Einstellung „Abrufweg“: Automatisch = mit Leiter, sonst genau ein fester Weg.
MODI = {"auto": AUTO_LEITER, "ohne_anmeldung": ("ohne_anmeldung",),
        "tv": ("tv",), "android_vr": ("android_vr",)}
STANDARD_MODUS = "auto"

HINWEIS_OHNE_ANMELDUNG = ("Ohne Anmeldung gehen altersbeschränkte Videos und Inhalte "
                          "nur für Kanalmitglieder nicht.")

_DROSSEL = ("not a bot", "captcha", "too many requests", "rate-limited", "rate limited",
            "http error 429")
_ZAHL_429 = re.compile(r"(?<![0-9a-z])429(?![0-9a-z])")
_ZAHL_403 = re.compile(r"(?<![0-9a-z])403(?![0-9a-z])")

_zuletzt = None
_zuletzt_lock = threading.Lock()


def ist_drossel(text):
    """429 oder Bot-Abfrage: YouTube bremst die Verbindung. Keine Leiter, ein
    anderer Weg bestätigte nur das Muster."""
    t = str(text).lower()
    return any(s in t for s in _DROSSEL) or bool(_ZAHL_429.search(t))


def ist_403(text):
    """Ein 403, der nicht zugleich eine Drossel ist: Anlass für die Leiter."""
    t = str(text).lower()
    if ist_drossel(t):
        return False
    return "forbidden" in t or bool(_ZAHL_403.search(t))


def wirkung(name, hat_cookies):
    """Was ein Weg tatsächlich an yt-dlp gibt: (mit Cookies?, Clients). Zwei Wege
    mit gleicher Wirkung sind derselbe Weg und werden nie beide versucht."""
    weg = WEGE[name]
    cookies = bool(hat_cookies and weg["cookies"])
    clients = tuple(weg["clients"] or ("default",))
    if not cookies and clients == ("default", "-web_embedded"):
        clients = ("default",)                       # ohne Anmeldung fragt yt-dlp web_embedded nicht
    return cookies, clients


def anwenden(opts, name):
    """Neue yt-dlp-Optionen für den Weg `name`; `opts` bleibt unberührt."""
    weg = WEGE[name]
    neu = dict(opts)
    if not weg["cookies"]:
        neu.pop("cookiesfrombrowser", None)
    if weg["clients"]:
        args = copy.deepcopy(neu.get("extractor_args") or {})
        args.setdefault("youtube", {})["player_client"] = list(weg["clients"])
        neu["extractor_args"] = args
    return neu


def zuletzt():
    with _zuletzt_lock:
        return _zuletzt


def merken(name):
    """Der Weg, der zuletzt geklappt hat; die automatische Leiter nimmt ihn
    beim nächsten Video zuerst (nur im Speicher, ein Neustart fängt vorn an)."""
    global _zuletzt
    with _zuletzt_lock:
        _zuletzt = name


def vergessen():
    merken(None)


def _ohne_doppelte(namen, hat_cookies, schon=()):
    gesehen = {wirkung(n, hat_cookies) for n in schon if n in WEGE}
    aus = []
    for n in namen:
        w = wirkung(n, hat_cookies)
        if w not in gesehen:
            gesehen.add(w)
            aus.append(n)
    return aus


def leiter(modus, hat_cookies, letzter=None):
    """Die Wege in der Reihenfolge, in der sie versucht werden."""
    namen = list(MODI.get(modus) or MODI[STANDARD_MODUS])
    if len(namen) > 1 and letzter in namen:
        namen.remove(letzter)
        namen.insert(0, letzter)
    return _ohne_doppelte(namen, hat_cookies)


def naechster(versucht, hat_cookies):
    """Der erste Weg aus KATALOG, der anders wirkt als alle versuchten; sonst None."""
    rest = _ohne_doppelte(KATALOG, hat_cookies, schon=versucht)
    return rest[0] if rest else None


class LeiterFehler(Exception):
    """Alle Wege der Leiter sind gescheitert. Der Text sagt es auf Deutsch,
    nennt jeden Weg mit seinem Fehler und behält „403“, damit die
    Sperr-Erkennung greift (`youtube_app._ist_sperre`)."""

    def __init__(self, versuche, hat_cookies=True):
        self.versuche = list(versuche)
        # Der Hinweis steht VOR den Einzelheiten: die Anzeige kürzt Fehler auf
        # 300 Zeichen (`youtube_app._fehltext`), der volle Text steht im Fehlerkanal.
        n = len(self.versuche)
        text = f"YouTube hat {'beide' if n == 2 else f'alle {n}'} Abrufwege abgelehnt (HTTP 403)."
        # Nur wer angemeldet war, verliert auf einem Weg ohne Cookies etwas; wer
        # ohne Anmeldung lädt, hätte den Satz nur als Rätsel gelesen (ein Nutzer, 24.11.2026).
        if hat_cookies and any(not WEGE[n]["cookies"] for n, _ in self.versuche):
            text += " " + HINWEIS_OHNE_ANMELDUNG
        teile = [f"{WEGE[n]['titel']}: {_anzeige(t)}" for n, t in self.versuche]
        super().__init__(text + " (" + "; ".join(teile) + ")")


def _kurz(text):
    t = re.sub(r"\x1b\[[0-9;]*m", "", str(text)).replace("ERROR: ", "").strip()
    return t if len(t) <= 90 else t[:87] + "…"


def _anzeige(text):
    """Ein Weg in der Fehlermeldung: ein schlichter 403 heißt nur „403“ (der
    englische yt-dlp-Satz ist für den Nutzer Rauschen und sprengte die 300
    Zeichen der Anzeige); jeder andere Fehler bleibt im Wortlaut, etwa die
    Altersgrenze. Das Protokoll behält über `_kurz` den vollen Satz."""
    return "403" if ist_403(text) else _kurz(text)


def mit_leiter(opts, aufruf, wege, durchlassen=(), abgebrochen=lambda: False,
               versucht=None, melden=None, vor_wechsel=None):
    """`aufruf(opts)` über die Wege `wege`. Rückgabe: (Ergebnis, Weg).

    Ein gewöhnlicher Fehler des ersten Wegs und jede Drossel (429, Bot) gehen
    unverändert hinaus. Nach einem 403 kommt der nächste Weg dran, jeder genau
    einmal; dort zählt jeder Fehler als gescheitert. Scheitern alle, fliegt
    `LeiterFehler` (bei nur einem Weg der Original-Fehler). `versucht` sammelt
    die Namen der versuchten Wege, `melden(weg, text)` hört jeden Fehlschlag,
    `vor_wechsel(stufe, anzahl, weg)` hört jeden Wechsel (Stufe ab 2)."""
    versuche = []
    letzter_fehler = None
    for i, name in enumerate(wege):
        if versucht is not None:
            versucht.append(name)
        if i and vor_wechsel is not None:
            vor_wechsel(i + 1, len(wege), name)
        try:
            ergebnis = aufruf(anwenden(opts, name))
        except durchlassen:
            raise
        except Exception as e:                       # noqa: BLE001 — jeder Fehler entscheidet über die Leiter
            text = str(e)
            if abgebrochen() or ist_drossel(text) or (i == 0 and not ist_403(text)):
                raise
            versuche.append((name, text))
            letzter_fehler = e
            if melden is not None:
                melden(name, text)
            continue
        merken(name)
        return ergebnis, name
    if len(versuche) == 1 and letzter_fehler is not None:
        raise letzter_fehler
    raise LeiterFehler(versuche, hat_cookies=bool(opts.get("cookiesfrombrowser")))


# ------------------------------------------------------- Einbau in youtube_app
#
# Die App ruft nur die Funktionen unten; im Hauptskript stehen bloß Aufrufe.
# GEMESSEN 23.11.2026 (zwölf Bauten bei VirusTotal): Stand diese Logik direkt im
# Hauptskript youtube_app.py, meldete Avira die exe als „TR/ATRAPS.Gen“ (eine
# Heuristik, die erst beim Zusammenspiel mehrerer neuer Teile anschlug); im
# Modul allein blieb sie still. Das Hauptskript legt PyInstaller als einzigen
# Code außerhalb des gepackten Modularchivs ab.

def abrufen(opts, aufruf, modus, item=None, geo_lauf=False, url="", durchlassen=(),
            abgebrochen=lambda: False, sag=None):
    """Ein yt-dlp-Aufruf über die passenden Wege; Rückgabe: das Ergebnis.

    Der Geo-Lauf bleibt beim Standard (er probiert schon Länder und Proxys
    durch); ein vom Knopf gewählter Weg (`weg_wunsch`) gilt allein. Mit `item`
    (Download) pflegt er dessen Felder `wege_versucht` und `weg`. `sag(text,
    stufe)` schreibt jeden gescheiterten Weg ins Protokoll (Ferndiagnose)."""
    if geo_lauf:
        wege = ["standard"]
    elif item is not None and item.get("weg_wunsch") in WEGE:
        wege = [item["weg_wunsch"]]
    else:
        wege = leiter(modus, bool(opts.get("cookiesfrombrowser")), zuletzt())
    url = url or (item or {}).get("url", "")

    def melden(weg, text):
        if sag is not None:
            sag(f"Abrufweg „{WEGE[weg]['titel']}“ gescheitert bei {url}: {_kurz(text)}",
                logging.WARNING)

    def wechsel(stufe, anzahl, weg):
        # Für die Anzeige: Ohne diese Felder sah ein Wechsel aus wie ein Download,
        # der bei 0 % hängt (ein Nutzer, 24.11.2026). Der Fortschritt des gescheiterten
        # Wegs wird genullt, damit die Zeile den Wechsel statt alter Prozente zeigt.
        item.update(weg_stufe=stufe, weg_stufen=anzahl, weg_titel=WEGE[weg]["titel"],
                    geladen=0, prozent=0.0, geschw=0, eta=None, phase="")

    ergebnis, weg = mit_leiter(opts, aufruf, wege, durchlassen=durchlassen, abgebrochen=abgebrochen,
                               versucht=None if item is None else item["wege_versucht"],
                               melden=melden, vor_wechsel=None if item is None else wechsel)
    if item is not None:
        item["weg"] = weg
        item["weg_titel"] = WEGE[weg]["titel"]
    return ergebnis


def eintrag_vorbereiten(item):
    """Vor jedem Download-Lauf. Wählt der Knopf den Weg, wächst die Liste der
    versuchten Wege über die Klicks hinweg; sonst böte der Knopf nach „TV“
    wieder „Standard“ an."""
    if not item.get("weg_wunsch"):
        item["wege_versucht"] = []
    item.setdefault("wege_versucht", [])
    for k in ("weg_naechster", "weg_naechster_titel", "weg", "weg_titel", "weg_stufe", "weg_stufen"):
        item.pop(k, None)


def fehlschlag(item, text, hat_cookies):
    """Nach einem gescheiterten Download: bei einem 403 den Weg für den Knopf
    „Anderen Weg versuchen“ vormerken (Name und Anzeige-Titel)."""
    if not ist_403(text):
        return
    name = naechster(item.get("wege_versucht") or [], hat_cookies)
    item["weg_naechster"] = name or ""
    item["weg_naechster_titel"] = WEGE[name]["titel"] if name else ""


def knopf_anderer_weg(item):
    """Knopf „Anderen Weg versuchen“ an einem 403: genau den vorgemerkten Weg,
    einmal (die Leiter ist dann aus). True, wenn der Eintrag wieder wartet."""
    if item.get("status") != "fehler" or item.get("weg_naechster") not in WEGE:
        return False
    item["weg_wunsch"] = item.pop("weg_naechster")
    item.pop("weg_naechster_titel", None)
    item.update(status="wartend", versuche=0, naechster_versuch=0, fehler="")
    return True


def zuruecksetzen(item):
    """„Weiter“ fängt wieder mit der Einstellung an."""
    for k in ("weg_wunsch", "wege_versucht", "weg_naechster", "weg_naechster_titel"):
        item.pop(k, None)


def modus_setzen(cfg, wert):
    """Einstellung „Abrufweg“ übernehmen, wenn der Wert bekannt ist; eine neue
    Wahl fängt ohne gemerkten Weg an."""
    if wert not in MODI:
        return
    if cfg.get("abrufweg") != wert:
        vergessen()
    cfg["abrufweg"] = wert

