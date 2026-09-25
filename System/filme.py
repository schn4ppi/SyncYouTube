# -*- coding: utf-8 -*-
"""Film-Fundament (Doku/SYNC_FILME_SPEC.md, JB-Go 05.08.2026): die
Jellyfin-Bibliothek von Renés Server als lokaler Katalog-Spiegel + Bilder +
TMDB/OMDb-Anreicherung + Reihen-Engine + Abspielweg über den VLC-Motor.

Regeln (Spec „Zugriff & Sicherheit"):
- Zugangsdaten NUR im Windows-Keyring (Sync-Jellyfin / Sync-TMDB / Sync-OMDb).
- Der Jellyfin-Token verlässt diesen Server nie: Clients bekommen nur die
  gemappten Katalog-Felder und Bilder aus dem lokalen Cache; die Stream-URL
  mit Token geht ausschließlich an den LOKALEN VLC.
- Einbahn-Regel wie geo/vpn: dieses Modul importiert NIE youtube_app.
- Alle Netz-Zugriffe laufen über _http() — Tests patchen genau diese Funktion
  und gehen nie ins Netz.
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import familie as fam

_pfade = {}                                # gesetzt von einrichten()
_sitzung = {}                              # {"token","user_id","version"}
_fehlversuch_ts = 0.0                      # letzter GESCHEITERTER Abzug (Backoff)
_anmelde_sperre_ts = 0.0                   # Anmelde-Backoff (403 ⇒ 10 min Ruhe)
_merkmal_ruhe_ts = 0.0                     # Ruhe nach abgelehnter Anmeldeform (nur die Automatik)
_druck_sitzung = {"ruhe": 0.0, "sitzung": None}   # JBs EINE Anmeldung je Ruhe (s. _druck_in_ruhe)
_anmelde_lock = threading.Lock()           # EINE Anmeldung zur Zeit (s. _anmelden)
_datei_locks = {}                          # je Pfad ein Lock (s. _json_aendern)
_datei_locks_lock = threading.Lock()
FEHL_BACKOFF_S = 30 * 60                   # nach Fehlschlag frühestens in 30 min wieder
FEHL_BACKOFF_MAX_S = 6 * 3600              # Staffel 30 min, 1 h, 2 h, 4 h, dann 6 h
META_HALTBAR_S = 14 * 24 * 3600            # Ratings altern langsam (Spec)
META_UNVOLLSTAENDIG_S = 3600               # nach einem Ausfall von TMDB/OMDb (F12)
EICHEN_VERSUCHE = 8                        # TMDB-Stimmen: Versuche je reihen() (F13)
EICHEN_PAUSE_S = 3600                      # nach Netz-/Serverfehler ruht das Eichen
EICHEN_FEHL_RUHE_S = 24 * 3600             # ein unbekannter Titel (404) ruht einen Tag
OMDB_TAGES_DECKEL = 950                    # Free-Key: 1.000/Tag — Puffer lassen
GERAET_KOPF = ('MediaBrowser Client="Sync", Device="SyncYouTube", '
               'DeviceId="sync-jb", Version="1.0"')
USER_AGENT = "SyncYouTube/1.0 (Sync-Familie, Film-Fundament)"
# Warum ein Jellyfin-Ruf scheiterte. Vor dem 24.09.2026 gab es nur EINEN Text
# („antwortet nicht"), und der passte auf den echten Fall gerade nicht: Renés
# Server antwortete, er lehnte nur die Anmeldeform ab.
ART_MERKMAL = "merkmal_abgelehnt"          # Anmeldung 200, Abruf mit frischem Token wieder 401
ART_ANMELDUNG = "anmeldung_abgelehnt"      # AuthenticateByName 401: Benutzer/Passwort
ART_DROSSEL = "drossel"                    # AuthenticateByName 403: Renés Sperre, vorübergehend
ART_NETZ = "netz"                          # Zeitüberschreitung, Verbindung, DNS
ART_SERVER = "server"                      # 5xx, sonstiger Status, unlesbare Antwort
ART_KEIN_ZUGANG = "kein_zugang"            # nichts im Keyring
ZUGANG_ARTEN = (ART_MERKMAL, ART_ANMELDUNG, ART_DROSSEL, ART_KEIN_ZUGANG)
# Kurztexte ohne Adresse und ohne Rohtext: die dürfen auch an fremde Geräte im
# WLAN (die Zustands-Route maskiert den rohen Fehlertext, s. youtube_app).
FEHLER_ART_TEXT = {
    # Prüfung Runde 2: dieselbe Lage entsteht, wenn zwei SyncYouTube-Prozesse
    # (exe und Quellstart) mit derselben DeviceId laufen — beide Ursachen nennen.
    ART_MERKMAL: ("Renés Server lehnt die Anmeldeform ab (HTTP 401 trotz frischer Anmeldung) "
                  "— oder ein zweites SyncYouTube nutzt dieselbe Gerätekennung"),
    ART_ANMELDUNG: "Renés Server lehnt Benutzer oder Passwort ab (HTTP 401 bei der Anmeldung)",
    ART_DROSSEL: "Renés Server bremst gerade die Anmeldung (HTTP 403, vorübergehend)",
    ART_NETZ: "Renés Server nicht erreichbar",
    ART_SERVER: "Renés Server antwortet fehlerhaft",
    ART_KEIN_ZUGANG: "Kein Jellyfin-Zugang im Keyring (Sync-Jellyfin)",
}
MERKMAL_RUHE_S = 600                       # frisches Token abgelehnt ⇒ 10 min keine AUTOMATISCHE Anmeldung
_anmelde_art = ""                          # Grund der letzten gescheiterten Anmeldung
GENRE_JE_TYP = 100                         # Filme UND Serien je bis hierhin (s. reihen())
# Renés Bibliothek ist ZWEISPRACHIG getaggt (gemessen 13.08.2026 an 4885 Titeln):
# dieselbe Kategorie steht mal englisch, mal deutsch am Werk. Ohne Zusammenführung
# entstehen zwei Reihen für dieselbe Sache, und die Rangfolge stimmt nicht —
# „Komödie" hat in Wahrheit 1453 Titel (938 + 515) und gehört auf Platz 3, stand
# aber aufgeteilt auf den Plätzen 4 und 8. Deutsch gewinnt, weil die Oberfläche
# deutsch ist. Nur EINDEUTIGE Sprachpaare, keine inhaltlichen Umgruppierungen:
# „Sci-Fi & Fantasy" und „Action & Adventure" sind Jellyfins Serien-Mischgenres
# und bleiben eigenständig, „Anime" bleibt neben „Animation" stehen.
GENRE_GLEICH = {
    "Comedy": "Komödie",
    "Adventure": "Abenteuer",
    "Crime": "Krimi",
    "Family": "Familie",
    "War": "Kriegsfilm",
    "History": "Historie",
    "Documentary": "Dokumentarfilm",
    "Romance": "Liebesfilm",
    "Science-Fiction": "Science Fiction",
    "Sci-Fi": "Science Fiction",
    "Children": "Kinder",
    "Kids": "Kinder",
    "Music": "Musik",
    "Sport": "Sport",
    "Biography": "Biografie",
}


def genre_name(g):
    """Ein Genre auf seinen Anzeigenamen bringen (Sprach-Dubletten zusammen)."""
    return GENRE_GLEICH.get(g, g)


def _json_aendern(pfad, aenderung, standard=None):
    """`fam.json_aendern` — aber die eigenen Threads stellen sich vorher an.

    Die Dateisperre des Familien-Kerns schützt gegen andere PROZESSE, und sie ist
    bewusst nicht-destruktiv: Wer sie nach 5 s nicht bekommt, lässt seine Änderung
    lieber aus, als fremde Arbeit zu überschreiben. Drängeln aber viele Threads
    DESSELBEN Prozesses um dieselbe Datei, verhungert einer — gemessen 13.08.2026
    bei 24 gleichzeitigen Herz-Klicks: 23 kamen an, einer fiel still weg. Der
    Server ist mehrfädig (jede Kachel eine Anfrage), also ist das kein Laborfall.

    Ein Lock je Pfad ordnet die eigenen Fäden, bevor sie um die Datei ringen —
    danach ist immer höchstens einer im Rennen und die 5 s reichen sicher."""
    with _pfad_lock(pfad):
        return fam.json_aendern(pfad, aenderung, standard=standard)


def _pfad_lock(pfad):
    """Der Lock je Pfad (s. _json_aendern) — auch für einen Schreiber, der die
    ganze Datei ersetzt (Katalog-Abzug), damit er nicht zwischen Lesen und
    Schreiben einer Änderung fällt."""
    with _datei_locks_lock:
        return _datei_locks.setdefault(str(pfad), threading.Lock())


def einrichten(daten_dir):
    """Pfade setzen (DATEN_DIR des Servers — die Testmodus-Weiche greift mit)."""
    _pfade["katalog"] = os.path.join(daten_dir, "filme_katalog.json")
    _pfade["meta"] = os.path.join(daten_dir, "filme_meta_cache.json")
    _pfade["queue"] = os.path.join(daten_dir, "filme_fortschritt_queue.json")
    _pfade["bilder"] = os.path.join(daten_dir, "filme_bilder")
    _pfade["merk"] = os.path.join(daten_dir, "filme_merkliste.json")
    _pfade["snippets"] = os.path.join(daten_dir, "filme_snippets")
    _pfade["zustand"] = os.path.join(daten_dir, "filme_zustand.json")


# ---------------------------------------------------------------- Zugang/Netz

def _zugang():
    try:
        import keyring
        url = keyring.get_password("Sync-Jellyfin", "url")
        ben = keyring.get_password("Sync-Jellyfin", "benutzer")
        pw = keyring.get_password("Sync-Jellyfin", "passwort")
        if url and ben and pw:
            return {"url": url.rstrip("/"), "benutzer": ben, "passwort": pw}
    except Exception:                      # noqa: BLE001 — ehrlich: kein Zugang
        pass
    return None


def _meta_keys():
    try:
        import keyring
        return {"tmdb": keyring.get_password("Sync-TMDB", "api_key") or "",
                "omdb": keyring.get_password("Sync-OMDb", "api_key") or ""}
    except Exception:                      # noqa: BLE001
        return {"tmdb": "", "omdb": ""}


def _http(url, daten=None, kopf=None, timeout=15):
    """DER eine Netz-Zugang (Tests patchen genau diese Funktion)."""
    req = urllib.request.Request(url, method="POST" if daten is not None else "GET")
    for k, v in (kopf or {}).items():
        req.add_header(k, v)
    body = json.dumps(daten).encode("utf-8") if daten is not None else None
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, body, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"{}"


def _kopf(token=""):
    """Der Ausweis, der an JEDE Jellyfin-Anfrage gehört — nicht nur an die Anmeldung.

    Renés Server läuft seit dem Update zwischen 20.09. und 24.09.2026 auf
    Jellyfin 12.1.0. Die Anmeldung trug schon beide Kopf-Formen, jeder Datenabruf
    danach aber das Token nur im alten `X-Emby-Token`. Die Anmeldung gelang, jeder
    Abruf bekam 401, auch mit dem ganz frischen Token (51 Fehlversuche „Items-Abruf
    HTTP 401"). SyncFindus schickt gegen denselben Server und dasselbe Konto diese
    Form (`_ausweis_koepfe`) und lief durch. Die Wurzel: beim 10.11-Update am 06.08.
    wurde nur die Anmeldung nachgezogen — es gab keine gemeinsame Kopf-Funktion.

    Beide Formen zu schicken kostet nichts und trägt über den Übergang: ein älterer
    Server liest `X-Emby-Token`, ein neuer das Token im `Authorization`-Kopf.
    Nach einer Neuanmeldung IMMER den ganzen Satz neu bauen: ein altes Token im
    `Authorization`-Kopf überstimmt ein neues in `X-Emby-Token`."""
    kopf = {"Authorization": GERAET_KOPF + (f', Token="{token}"' if token else ""),
            "X-Emby-Authorization": GERAET_KOPF,
            "User-Agent": USER_AGENT}
    if token:
        kopf["X-Emby-Token"] = token
    return kopf


def _server_version_public(url):
    """Server-Version OHNE Anmeldung (GET /System/Info/Public) — für ehrliche
    Fehlertexte, wenn angemeldete Rufe abgelehnt werden. '?' bei jeder Störung."""
    try:
        st, roh = _http(url + "/System/Info/Public", timeout=10)
        if st == 200:
            return str(json.loads(roh or b"{}").get("Version") or "?")
    except Exception:                      # noqa: BLE001 — Version ist Kür
        pass
    return "?"


def _anmelden(druck=False):
    """Die aktuelle Sitzung als KOPIE (Token, Benutzer-Id, Version) oder None.

    Eine Kopie, kein Verweis auf `_sitzung`: ein anderer Faden kann die Sitzung
    jederzeit erneuern — wer mitten im Ruf ist, soll sein Token behalten und bei
    einem 401 genau dieses als abgelehnt melden (s. `_neu_anmelden`).
    `druck=True`: JBs ausdrücklicher Druck (Film starten, Browser-Strom) darf die
    Merkmal-Ruhe übergehen — aber nur mit EINER Anmeldung je Ruhe (s.
    `_druck_in_ruhe`), nie in der 403-Drossel (s. _anmelden_ungesperrt)."""
    kopie = dict(_sitzung)
    if kopie.get("token"):
        return kopie
    # EINE Anmeldung zur Zeit — der Sturm passt in EINEN Prozess.
    #
    # Der Kommentar unten schrieb den 403 vom 06.08. den „Zweitprozessen" zu.
    # Nachgemessen am 13.08.: Er entsteht schon hier. Der Fernsehmodus lädt
    # dutzende Kacheln gleichzeitig; jede ruft `bild_holen`, alle sehen im selben
    # Moment „kein Token" und melden sich an. Jede Anmeldung mit derselben
    # DeviceId entwertet die vorherige, deren Besitzer daraufhin 401 bekommt und
    # sich WIEDER anmeldet — genau die Kaskade, die Renés Server sieben Tage lang
    # aussperrte. Mit der Sperre meldet sich einer an, alle anderen nehmen dessen
    # Token (zweite Prüfung IN der Sperre, weil der Erste inzwischen fertig ist).
    with _anmelde_lock:
        if _sitzung.get("token"):
            return dict(_sitzung)
        if druck and time.time() < _merkmal_ruhe_ts:
            return _druck_in_ruhe()
        s = _anmelden_ungesperrt()
        return dict(s) if s else None


def _druck_in_ruhe():
    """JBs Druck in der Merkmal-Ruhe — NUR unter `_anmelde_lock` rufen.

    Höchstens EIN Anmeldeversuch je Ruhe (Prüfung Runde 2). Vorher meldete sich
    jeder stream_url-Ruf an, sobald die Sitzung leer war: auch die Hover-Vorschau
    und jede Range-Anfrage des Browser-Players. Die Automatik bekam mit dem
    frischen Token 401 und verwarf die Sitzung wieder — gemessen eine Anmeldung
    je Runde, der Sturm, den die Ruhe verhindern soll. Jetzt bekommt jeder
    weitere Druck derselben Ruhe die Sitzung dieser einen Anmeldung, auch wenn
    die Automatik sie inzwischen verworfen hat: ein laufender Browser-Film holt
    seine nächste Range-Anfrage mit demselben Token. Eine neue Ruhe (neuer
    Zeitstempel) gibt wieder genau einen Versuch.

    Verbraucht ist der Versuch nur, wenn Jellyfin wirklich geantwortet hat
    (Prüfung Runde 3): Erfolg, 401 (Benutzer/Passwort) oder 403 (Drossel). Bei
    Netzfehler, 5xx oder 200 ohne Token bleibt er frei — sonst sperrte ein
    Netz-Wackler jeden Film-Start bis zum Ende der Ruhe (bis 10 Min), gegen
    JBs Entscheid „Film-Start darf trotz Ruhe". Der normale 60-s-Backoff
    (_anmelde_sperre_ts) gilt weiter."""
    ruhe = _merkmal_ruhe_ts
    if _druck_sitzung["ruhe"] != ruhe:
        if time.time() < _anmelde_sperre_ts:   # Backoff/403-Drossel: kein Versuch, der eine bleibt frei
            return None
        vorher = _druck_sitzung["ruhe"]
        _druck_sitzung["ruhe"] = ruhe
        s = _anmelden_ungesperrt(merkmal_ruhe=False)
        _druck_sitzung["sitzung"] = dict(s) if s else None
        if not s and _anmelde_art not in (ART_ANMELDUNG, ART_DROSSEL):
            _druck_sitzung["ruhe"] = vorher      # Jellyfin hat nicht geantwortet: der Versuch bleibt frei
    s = _druck_sitzung["sitzung"]
    return dict(s) if s else None


def _anmelden_ungesperrt(merkmal_ruhe=True):
    """Anmelden — NUR unter `_anmelde_lock` rufen. Merkt bei einem Fehlschlag in
    `_anmelde_art`, warum (für die ehrliche Anzeige)."""
    global _anmelde_sperre_ts, _anmelde_art
    # Anmelde-Backoff (Fund 06.08.): Nach einem Fehlschlag ist RUHE —
    # 403 = 10 Minuten (Anmeldesperre ausklingen lassen), sonst 60 s.
    # Der Grund bleibt der, der die Ruhe ausgelöst hat.
    if time.time() < _anmelde_sperre_ts:
        return None
    # Merkmal-Ruhe (Prüfung Runde 1): hält nur die AUTOMATIK zurück (Kacheln,
    # Bilder, Folgenlisten, 6-h-Abzug) — JBs ausdrückliche Drücke nicht.
    if merkmal_ruhe and time.time() < _merkmal_ruhe_ts:
        _anmelde_art = ART_MERKMAL
        return None
    z = _zugang()
    if not z:
        _anmelde_art = ART_KEIN_ZUGANG
        return None
    try:
        # Beide Kopf-Formen (10.11 kündigte X-Emby-Authorization ab), s. _kopf.
        st, roh = _http(z["url"] + "/Users/AuthenticateByName",
                        daten={"Username": z["benutzer"], "Pw": z["passwort"]},
                        kopf=_kopf())
    except Exception:                      # noqa: BLE001 — Server aus/Netz weg
        _anmelde_sperre_ts = time.time() + 60
        _anmelde_art = ART_NETZ
        return None
    if st != 200:
        # 403 ist auf Renés Server eine VORÜBERGEHENDE Drossel gehäufter
        # Anmeldungen (06.08., SyncFindus 28.08.) — kein Dauerzustand.
        _anmelde_sperre_ts = time.time() + (600 if st == 403 else 60)
        _anmelde_art = {401: ART_ANMELDUNG, 403: ART_DROSSEL}.get(st, ART_SERVER)
        return None
    try:
        d = json.loads(roh or b"{}")
        token = d.get("AccessToken") or ""
        uid = (d.get("User") or {}).get("Id") or ""
    except (ValueError, AttributeError):
        token = uid = ""
    if not token:
        # 200 ohne lesbares Token (Wartungs- oder Proxy-Seite): ein Fehlschlag,
        # keine Sitzung mit leerem Token — und keine Ausnahme, die den Abzug
        # am Backoff vorbei sofort wieder anstoßen ließe.
        _anmelde_sperre_ts = time.time() + 60
        _anmelde_art = ART_SERVER
        return None
    _sitzung.update(token=token, user_id=uid)
    _anmelde_art = ""
    try:
        st, roh = _http(z["url"] + "/System/Info", kopf=_kopf(token))
        _sitzung["version"] = (json.loads(roh).get("Version") or "?") if st == 200 else "?"
    except Exception:                      # noqa: BLE001 — Version ist Kür
        _sitzung["version"] = "?"
    return _sitzung


def _neu_anmelden(abgelehnt):
    """Nach einem 401 mit dem Token `abgelehnt`: frisch anmelden — außer ein
    anderer Faden hat das längst getan.

    Vorher stand `_sitzung.clear()` AUSSERHALB der Sperre (Nebenfund 24.09.): ein
    Faden mit veraltetem Token warf das frische Token eines anderen Fadens weg
    und meldete sich erneut an. Wegen derselben DeviceId entwertete das den
    anderen — die Kaskade vom 13.08. Vergleich, Verwerfen und Neuanmeldung
    stehen deshalb in EINER Sperre.

    Rückgabe `(sitzung|None, eigen)`: `eigen` = hier frisch angemeldet. Nur ein
    eigenes Token taugt als Beleg für „Anmeldeform abgelehnt" (s. _jellyfin_ruf);
    das eines anderen Fadens prüft dieser selbst (Prüfung Runde 1)."""
    with _anmelde_lock:
        aktuell = _sitzung.get("token")
        if aktuell and aktuell != abgelehnt:
            return dict(_sitzung), False
        _sitzung.clear()
        s = _anmelden_ungesperrt()
        return (dict(s) if s else None), True


def _merkmal_abgelehnt(token):
    """Auch das FRISCH ausgestellte Token wurde abgelehnt: eine weitere Anmeldung
    hilft nicht (so sah der Ausfall ab dem 23.09. aus). Das Token verwerfen — nur
    wenn es noch das aktuelle ist — und 10 Minuten keine Anmeldung, statt dass
    jede Kachel und jede Folgenliste Renés Server mit neuen Anmeldungen bedrängt
    (dasselbe Konto nutzt SyncFindus: dessen Drossel wäre mitbetroffen).
    Die Ruhe gilt nur der Automatik: ⟳ Abgleichen hebt sie auf
    (merkmal_ruhe_aufheben), JBs Druck (Film-Start, Browser-Strom) meldet sich
    einmal je Ruhe trotzdem an (stream_url mit druck=True, s. _druck_in_ruhe)."""
    global _merkmal_ruhe_ts, _anmelde_art
    with _anmelde_lock:
        if _sitzung.get("token") == token:
            _sitzung.clear()
        _merkmal_ruhe_ts = max(_merkmal_ruhe_ts, time.time() + MERKMAL_RUHE_S)
        _anmelde_art = ART_MERKMAL


def merkmal_ruhe_aufheben():
    """⟳ Abgleichen (JBs Druck) darf es jederzeit versuchen: die Merkmal-Ruhe
    endet. Die 403-Drossel bleibt — sie ist Renés Sperre, nicht unsere."""
    global _merkmal_ruhe_ts
    with _anmelde_lock:
        _merkmal_ruhe_ts = 0.0


def _jellyfin_ruf(pfad, daten=None, timeout=15):
    """DER Weg für jeden angemeldeten Jellyfin-Abruf: Ausweis an jeder Anfrage,
    bei 401 EINMAL frisch anmelden und mit NEU gebauten Köpfen wiederholen.

    `pfad` beginnt mit '/'; `{uid}` wird durch die Benutzer-Id der Sitzung
    ersetzt (die kann sich bei der Neuanmeldung nicht ändern, wird aber trotzdem
    je Versuch neu eingesetzt). Rückgabe `(status, roh, art, ausnahme)`:
    `art` ist '' wenn der Server geantwortet hat (der Aufrufer wertet den Status),
    sonst eine ART_*-Fehlerart; `ausnahme` trägt nur bei Netzfehlern den Text.

    „Anmeldeform abgelehnt" (samt Ruhe) erst nach ZWEI eigenen, frisch geholten
    und abgelehnten Tokens in DIESEM Ruf (Prüfung Runde 1): Ein zweiter Prozess
    mit derselben DeviceId (etwa die Quellstart-Kopie) kann sich zwischen
    Neuanmeldung und Wiederholung anmelden und unser frisches Token entwerten —
    einmal ist Zufall, die Gegenprobe-Anmeldung klärt es. Ein Token, das ein
    ANDERER Faden geholt hat, ist gar kein Beleg: dann scheitert nur dieser Ruf
    (Art merkmal_abgelehnt für die Anzeige, aber ohne Ruhe)."""
    z = _zugang()
    if not z:
        return 0, b"", ART_KEIN_ZUGANG, ""
    s = _anmelden()
    if not s:
        return 0, b"", _anmelde_art or ART_NETZ, ""
    wiederholt = False
    eigen = False                          # Token aus UNSERER Neuanmeldung in diesem Ruf?
    eigene_abgelehnt = 0
    while True:
        token = s.get("token") or ""
        try:
            st, roh = _http(z["url"] + pfad.replace("{uid}", s.get("user_id") or ""),
                            daten=daten, kopf=_kopf(token), timeout=timeout)
        except Exception as e:             # noqa: BLE001 — Netz weg / Zeitüberschreitung
            return 0, b"", ART_NETZ, str(e) or type(e).__name__
        if st != 401:
            return st, roh, "", ""
        if eigen:
            eigene_abgelehnt += 1
            if eigene_abgelehnt >= 2:
                _merkmal_abgelehnt(token)
                return st, roh, ART_MERKMAL, ""
        elif wiederholt:
            # Das frische Token eines ANDEREN Fadens wurde abgelehnt: für die
            # Anzeige ein Zugangsproblem (sonst hieße eine leere Folgenliste
            # „Serie ohne Folgen"), aber kein Beleg — keine Ruhe, kein Verwerfen;
            # der andere Faden prüft sein Token selbst.
            return st, roh, ART_MERKMAL, ""
        # Token von einer zweiten Sitzung entwertet (gleiche DeviceId, live
        # gefunden 05.08.) ⇒ frisch anmelden und wiederholen.
        wiederholt = True
        s, eigen = _neu_anmelden(token)
        if not s:
            return st, roh, _anmelde_art or ART_NETZ, ""


# ---------------------------------------------------------------- Katalog

def _eintrag(it):
    """Jellyfin-Item → unser Katalog-Eintrag. WICHTIG (Token-Wächter): NUR die
    hier gemappten Felder verlassen den Server — nie das rohe Objekt."""
    stroeme = it.get("MediaStreams") or []
    ud = it.get("UserData") or {}
    ticks = it.get("RunTimeTicks") or 0
    return {"id": it.get("Id") or "", "titel": it.get("Name") or "",
            "typ": "serie" if it.get("Type") == "Series" else "film",
            "jahr": it.get("ProductionYear"), "genres": it.get("Genres") or [],
            "fsk": it.get("OfficialRating") or "", "rating": it.get("CommunityRating"),
            "laufzeit_min": round(ticks / 600_000_000) if ticks else None,
            "imdb": (it.get("ProviderIds") or {}).get("Imdb") or "",
            "tmdb": (it.get("ProviderIds") or {}).get("Tmdb") or "",
            "video_codec": next((s.get("Codec") for s in stroeme
                                 if s.get("Type") == "Video"), ""),
            "audio_codec": next((s.get("Codec") for s in stroeme
                                 if s.get("Type") == "Audio"), ""),
            "bild_tag": (it.get("ImageTags") or {}).get("Primary") or "",
            "hinzugefuegt": it.get("DateCreated") or "",
            "position_s": round((ud.get("PlaybackPositionTicks") or 0) / 10_000_000),
            "gesehen": bool(ud.get("Played"))}


_ID_FORM = re.compile(r"^[0-9a-fA-F-]{16,64}$")


# Jellyfin-Routen (Stand 25.09.2026, am Quelltext v12.1 geprüft): die alten Formen
# /Users/{uid}/Items, /Users/{uid}/Items/{id} und /Users/{uid}/PlayedItems/{id}
# beantwortet 12.1 noch, aber als [Obsolete] und aus der API-Beschreibung
# ausgeblendet (ItemsController.cs:721-723, UserLibraryController.cs:117-120,
# PlaystateController.cs:120-124). Laut Release-Notiz v12.0 dürfen solche Routen
# in jeder Hauptversion ohne Vorwarnung fallen. Die Nachfolger gibt es seit
# 10.10.7 (also auch auf „JB Zuhause", 10.11.11); die Alt-Route ruft in 12.1
# wörtlich die neue auf, die Antwortform ist dieselbe. Die Benutzer-Id geht als
# Merkmal `userId` mit — eine fremde wäre 403 (RequestHelpers.GetUserId).
def _titel_pfad(item_id):
    """GET /Items/{id}?userId= — ein Titel samt UserData und MediaStreams
    (UserLibraryController.GetItem, Antwort BaseItemDto)."""
    return "/Items/" + urllib.parse.quote(str(item_id), safe="") + "?userId={uid}"


def _folge_holen(item_id):
    """Eine EPISODE direkt bei Jellyfin nachschlagen (steht nie im Spiegel).

    Der Katalog-Abzug holt `IncludeItemTypes=Movie,Series` — Folgen sind absichtlich
    nicht dabei (bei Renés Bestand wären das zehntausende Einträge; die Simpsons
    allein haben 553). Folge: `detail(folgen_id)` fand nichts und gab None zurück,
    die Route antwortete 404 mit `{"fehler": …}` — und die Oberfläche las dieses
    Fehler-Objekt als gültige Meta. Ergebnis für JB (gemessen 13.08.2026): beim
    Abspielen einer Folge blieb der Titel leer, die Zeitleiste tot (Dauer 0), und
    die Weiche wählte immer die schwerste Gangart (voller libx264-Lauf), obwohl
    viele Folgen h264 sind und kopiert werden könnten.

    Kein Cache nötig: Der Ruf passiert genau einmal beim Öffnen einer Folge.
    Die ID-Form wird geprüft, damit ein fremdes Gerät im WLAN nicht mit
    beliebigen Zeichenketten Rufe an Renés Server auslösen kann."""
    if not item_id or not _ID_FORM.match(item_id):
        return None
    # Mit 401-Heilung wie jeder andere Weg (bis 24.09. fehlte sie hier: ein
    # entwertetes Token ließ jede Folge als „Film nicht gefunden" enden).
    st, roh, art, _ = _jellyfin_ruf(_titel_pfad(item_id))
    if art or st != 200:
        return None
    try:
        it = json.loads(roh)
    except ValueError:
        return None
    if not isinstance(it, dict) or not it.get("Id"):
        return None
    e = _eintrag(it)
    if it.get("Type") == "Episode":
        # Sprechender Titel wie in der Folgenliste: „Dark · S1 F3 — Gestern und heute"
        teile = [it.get("SeriesName") or ""]
        st_nr, fo_nr = it.get("ParentIndexNumber"), it.get("IndexNumber")
        if st_nr is not None and fo_nr is not None:
            teile.append(f"S{st_nr} F{fo_nr}")
        e["titel"] = " · ".join([t for t in teile if t]) + (
            f" — {it.get('Name')}" if it.get("Name") else "")
        e["typ"] = "folge"
        e["serie_id"] = it.get("SeriesId") or ""
    return e


def _zustand_merken(erg):
    """Den Ausgang JEDES Abzugs auf Platte festhalten — und zwar hier.

    Der Ausfall vom 06.–13.08.2026 blieb sieben Tage unbemerkt, obwohl
    `katalog_abzug()` sein Scheitern sauber zurückgab: beide Aufrufstellen
    warfen den Rückgabewert weg. Die Oberfläche sah normal aus, der Spiegel
    wurde nur nicht mehr jünger — gutes Ausfall-Verhalten hat den Ausfall
    unsichtbar gemacht. Konsequenz: Der Zustand gehört nicht in die Hand des
    Aufrufers (der ihn vergessen kann), sondern in den Abzug selbst; und er
    muss den Prozess überleben, weil die App sich bei jeder Code-Änderung
    selbst neu startet und ein Prozess-Merker damit ständig vergisst."""
    def _setzen(d):
        jetzt = time.time()
        d["letzter_versuch"] = jetzt
        if erg.get("ok"):
            d["letzter_erfolg"] = jetzt
            d["anzahl"] = erg.get("anzahl") or 0
            d["fehler"] = ""
            d["fehlversuche"] = 0
        else:
            d["fehler"] = erg.get("fehler") or "unbekannt"
            # Die Fehlerart (24.09.): „antwortet nicht" passte auf den echten
            # Ausfall nicht — der Server antwortete, er lehnte die Anmeldeform ab.
            d["fehler_art"] = erg.get("art") or ART_SERVER
            try:
                d["fehlversuche"] = int(d.get("fehlversuche") or 0) + 1
            except (TypeError, ValueError):
                d["fehlversuche"] = 1
            d.setdefault("fehler_seit", jetzt)
        if erg.get("ok"):
            d.pop("fehler_seit", None)
            d.pop("fehler_art", None)
        # Die TATSÄCHLICHE Server-Version, sobald bekannt — auch aus einem
        # Fehlschlag (/System/Info/Public). Der Spiegel zeigte sonst weiter
        # „10.11.11", während Renés Server längst 12.1.0 war.
        version = erg.get("server_version")
        if version and version != "?":
            d["server_version"] = version
    try:
        _json_aendern(_pfade["zustand"], _setzen, standard={})
    except (OSError, ValueError):          # Melden darf den Abzug nie kippen
        pass
    return erg


def zustand():
    """Wie es um den Spiegel steht — für Anzeige und Dashboard.

    `still_seit_s` ist die Zeit seit dem letzten ERFOLG (nicht seit dem letzten
    Versuch): genau die Größe, die beim 403-Ausfall niemand sah."""
    d = _zustand_lesen()
    kat = katalog_lesen()
    stand = kat.get("stand") or 0
    erfolg = d.get("letzter_erfolg") or stand
    fehler = d.get("fehler") or ""
    return {
        "stand": stand,
        "anzahl": len(kat.get("eintraege") or []),
        "server_version": d.get("server_version") or kat.get("server_version") or "?",
        "letzter_erfolg": erfolg,
        "letzter_versuch": d.get("letzter_versuch") or 0,
        "fehler": fehler,
        # Ein Zustand von vor dem 24.09. hat keine Art: keine erfundene
        # Einordnung — Anzeige und Maskierung bleiben dann wie bisher.
        "fehler_art": (d.get("fehler_art") or "") if fehler else "",
        "fehlversuche": d["fehlversuche"],
        "still_seit_s": max(0.0, time.time() - erfolg) if erfolg else 0.0,
        "zugang": bool(_zugang()),
    }


def _zustand_lesen():
    """filme_zustand.json robust lesen — eine kaputte Datei darf weder die
    Anzeige noch den Backoff umwerfen."""
    d = fam.json_laden(_pfade.get("zustand") or "", {}) or {}
    if not isinstance(d, dict):
        d = {}
    try:
        d["fehlversuche"] = max(0, int(d.get("fehlversuche") or 0))
    except (TypeError, ValueError):
        d["fehlversuche"] = 0
    try:
        d["letzter_versuch"] = float(d.get("letzter_versuch") or 0)
    except (TypeError, ValueError):
        d["letzter_versuch"] = 0.0
    return d


def katalog_abzug():
    """Voll-Abzug → filme_katalog.json (atomar; scheitert er, bleibt der alte
    Spiegel stehen — Ausfall-Verhalten laut Spec). Der Ausgang wird IMMER in
    `filme_zustand.json` festgehalten, siehe `_zustand_merken`.

    Nichts fliegt ungezählt heraus (Nebenfund 24.09.): eine Ausnahme ließ
    früher weder Zustand noch Backoff zurück, und der 5-s-Ticker stieß den
    nächsten Abzug sofort an — bei einer Anmelde-Ausnahme alle 5 Sekunden."""
    try:
        erg = _katalog_abzug()
    except Exception as e:                 # noqa: BLE001 — zählen statt ausbrechen
        erg = _abzug_gescheitert(ART_SERVER, f"Abzug abgebrochen ({type(e).__name__})")
    return _zustand_merken(erg)


def _abzug_gescheitert(art, fehler, url=""):
    """Fehlschlag mit Backoff. Bei abgelehnter Anmeldeform zusätzlich die
    Server-Version ohne Anmeldung holen: dann ist die Ursache sofort benannt
    (der Ausfall vom 23.09. hätte „Jellyfin 12.1.0" gezeigt statt „10.11.11")."""
    global _fehlversuch_ts
    _fehlversuch_ts = time.time()
    erg = {"ok": False, "anzahl": 0, "art": art, "fehler": fehler}
    if art == ART_MERKMAL and url:
        erg["server_version"] = _server_version_public(url)
    return erg


def _katalog_abzug():
    global _fehlversuch_ts
    z = _zugang()
    if not z:                              # kein Backoff: Einrichtung fehlt nur
        return {"ok": False, "anzahl": 0, "art": ART_KEIN_ZUGANG,
                "fehler": "Kein Zugang im Keyring (Sync-Jellyfin)."}
    s = _anmelden()
    if not s:
        art = _anmelde_art or ART_NETZ
        return _abzug_gescheitert(art, FEHLER_ART_TEXT.get(art) or "Anmeldung fehlgeschlagen.",
                                  z["url"])
    # Live gemessen (05.08., Renés Server): der Voll-Abzug in EINEM Ruf läuft
    # in jeden Timeout (>300 s), und MediaStreams ist das teure Feld (63 s für
    # 200 Titel MIT, 57 s für 1000 OHNE). Darum: seitenweise à 1000 ohne
    # MediaStreams (~5 min gesamt, fair gegenüber Renés Rechner) — die Codecs
    # holt detail() je Titel einzeln nach und cacht sie.
    felder = ("Genres,ProviderIds,ProductionYear,OfficialRating,"
              "CommunityRating,RunTimeTicks,DateCreated")
    eintraege, start, gesamt = [], 0, None
    while gesamt is None or start < gesamt:
        # 401 heilt _jellyfin_ruf selbst (einmal frisch anmelden, alle Köpfe neu).
        # GET /Items?userId= (ItemsController.GetItems, Antwort QueryResult mit
        # Items + TotalRecordCount) statt der veralteten /Users/{uid}/Items.
        st, roh, art, ausnahme = _jellyfin_ruf(
            "/Items?userId={uid}&Recursive=true"
            f"&IncludeItemTypes=Movie,Series&Fields={felder}"
            f"&StartIndex={start}&Limit=1000", timeout=180)
        if art == ART_MERKMAL:
            return _abzug_gescheitert(art, "Items-Abruf HTTP 401 trotz frischer Anmeldung "
                                           "(Anmeldeform abgelehnt)", z["url"])
        if art:
            return _abzug_gescheitert(art, f"Items-Abruf: {ausnahme}" if ausnahme
                                      else FEHLER_ART_TEXT.get(art) or "Anmeldung fehlgeschlagen.")
        if st != 200:
            return _abzug_gescheitert(ART_SERVER, f"Items-Abruf HTTP {st}")
        try:
            d = json.loads(roh)
            seite = d.get("Items") or []
            neue = [_eintrag(it) for it in seite]
            gesamt = d.get("TotalRecordCount") or len(seite)
        except (ValueError, AttributeError, TypeError):
            # 200 ohne lesbares JSON (Wartungs- oder Proxy-Seite): zählen und
            # warten, nicht mit einer Ausnahme am Backoff vorbei.
            return _abzug_gescheitert(ART_SERVER, "Items-Abruf: unlesbare Antwort (kein JSON)")
        if not seite:
            break
        eintraege.extend(neue)
        start += 1000
    # Die Version der Sitzung, die die letzte Seite geholt hat (nach einer
    # Neuanmeldung steht sie in _sitzung, nicht in der Kopie vom Anfang).
    version = _sitzung.get("version") or s.get("version") or "?"
    # Unter derselben Sperre wie _spiegel_nachziehen: sonst schriebe eine Meldung,
    # die den ALTEN Spiegel las, ihn nach diesem Abzug zurück.
    with _pfad_lock(_pfade["katalog"]):
        fam.json_schreiben(_pfade["katalog"], {
            "stand": time.time(), "server_version": version,
            "eintraege": eintraege})
    _fehlversuch_ts = 0.0                  # Erfolg löst den Backoff
    try:
        fortschritt_nachreichen()          # liegengebliebene Meldungen mitnehmen
    except Exception:                      # noqa: BLE001 — der Abzug selbst ist gelungen
        pass
    return {"ok": True, "anzahl": len(eintraege), "fehler": "", "server_version": version}


def katalog_lesen():
    try:
        with open(_pfade["katalog"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"stand": 0, "server_version": "?", "eintraege": []}


def backoff_s(fehlversuche):
    """Wartezeit nach `fehlversuche` Fehlschlägen in Folge: 30 min, 1 h, 2 h,
    4 h, dann höchstens 6 h (so fällt die Automatik nie ganz aus)."""
    try:
        n = int(fehlversuche or 0)
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        return 0
    return min(FEHL_BACKOFF_S * 2 ** min(n - 1, 16), FEHL_BACKOFF_MAX_S)


def sync_faellig(alter_s=6 * 3600):
    """Fällig nach 6 h — aber NIE direkt nach einem Fehlschlag: sonst hämmert
    der 5-s-Ticker bei totem/langsamem Server in Dauerschleife auf Renés
    Rechner ein (live fast passiert am 05.08. — Timeout-Lauf und der Ticker
    stieß sofort den nächsten an). Backoff = Selbstheilungs-Regel.

    Seit 24.09. mit Gedächtnis: Der Backoff stand nur im Prozess-Speicher, und
    die App startet sich bei jeder Code-Änderung selbst neu — danach war der
    Abzug sofort wieder fällig (51 Versuche in gut 18 Stunden). Jetzt zählen
    `fehlversuche` und `letzter_versuch` aus filme_zustand.json, gestaffelt
    (backoff_s). Der Knopf ⟳ Abgleichen fragt hier nicht nach: er bleibt frei."""
    jetzt = time.time()
    if jetzt - _fehlversuch_ts < FEHL_BACKOFF_S:
        return False
    d = _zustand_lesen()
    zuletzt = d["letzter_versuch"]
    # Ein Zeitstempel weit in der Zukunft (Uhr verstellt) darf nicht ewig sperren.
    if d["fehlversuche"] and zuletzt <= jetzt + 60 and jetzt - zuletzt < backoff_s(d["fehlversuche"]):
        return False
    return (jetzt - (katalog_lesen().get("stand") or 0)) >= alter_s


# ---------------------------------------------------------------- Bilder

def bild_holen(item_id, art="Primary"):
    """Bild aus dem Platten-Cache, sonst von Jellyfin holen und ablegen.
    Dateiname strikt gefiltert — eine Item-Id ist nie ein Pfad, und die
    Bild-Art nur aus der Jellyfin-Palette (kommt vom Client!)."""
    sauber = re.sub(r"[^A-Za-z0-9]", "", item_id or "")
    if not sauber or sauber != (item_id or ""):
        return None
    if art not in ("Primary", "Backdrop", "Thumb", "Logo", "Banner"):
        return None
    pfad = os.path.join(_pfade["bilder"], f"{sauber}_{art}.jpg")
    try:
        with open(pfad, "rb") as f:
            return f.read()
    except OSError:
        pass
    # Negativ-Cache: hat ein Titel z. B. kein Thumb, merkt eine Marker-Datei
    # das — sonst feuert JEDER Reihen-Aufbau die 404-Kaskade der Bild-Kette
    # (Thumb→Backdrop→Poster) erneut gegen Renés Server.
    fehlt = pfad + ".fehlt"
    if os.path.exists(fehlt):
        return None
    st, roh, fehlart, _ = _jellyfin_ruf(f"/Items/{sauber}/Images/{art}")
    if fehlart:                            # Netz/Zugang: NICHT negativ cachen,
        return None                        # nächster Versuch frei
    os.makedirs(_pfade["bilder"], exist_ok=True)
    if st == 404:                          # Titel HAT dieses Bild nicht ⇒ merken
        try:
            open(fehlt, "wb").close()
        except OSError:
            pass
        return None
    if st != 200 or not roh:
        return None
    with open(pfad, "wb") as f:
        f.write(roh)
    return roh


# ---------------------------------------------------------------- Anreicherung

def _meta_cache():
    try:
        with open(_pfade["meta"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _omdb_erlaubt(cache):
    heute = time.strftime("%Y-%m-%d")
    if cache.get("omdb_tag") != heute:
        cache["omdb_tag"], cache["omdb_zaehler"] = heute, 0
    return (cache.get("omdb_zaehler") or 0) < OMDB_TAGES_DECKEL


def detail(item_id, profil="standard"):
    """Spiegel-Eintrag + TMDB/OMDb-Anreicherung (on demand, 14-Tage-Cache).
    Fehlender Key oder tote Quelle ⇒ Felder bleiben leer, NIE eine Fehlerseite
    (Selbstheilungs-Regel). Ein Ausfall (Netzfehler, Antwort außer 200/404,
    auch 429, oder der OMDb-Tagesdeckel) markiert den Eintrag `unvollstaendig`;
    der hält nur eine Stunde (F12). Jeder OMDb-Abruf zählt im selben
    Schreibvorgang in `omdb_zaehler`, sonst griffe der Tagesdeckel nie."""
    e = next((x for x in katalog_lesen()["eintraege"] if x["id"] == item_id), None)
    if not e:
        e = _folge_holen(item_id)
    if not e:
        return None
    cache = _meta_cache()
    m = cache.get(item_id) or {}
    # "trailer_v2" ist der Feld-Versions-Marker: ältere Cache-Einträge werden
    # einmal frisch geholt (Netflix-Detailseite Build 184; v2 = Trailer-Fix:
    # language=de-DE filterte auch die VIDEOS auf Deutsch ⇒ meist leer).
    haltbar = META_UNVOLLSTAENDIG_S if m.get("unvollstaendig") else META_HALTBAR_S
    if not m or "trailer_v2" not in m or time.time() - (m.get("ts") or 0) > haltbar:
        m = {"ts": time.time(), "beschreibung": "", "cast": [],
             "empfehlungen_tmdb": [], "imdb_rating": "", "metacritic": "",
             "tomatometer": "", "tagline": "", "regie": [], "drehbuch": [],
             "trailer": [], "trailer_v2": True, "hoehe": 0, "audio_kanaele": 0,
             "audio_sprachen": [], "sub_sprachen": []}
        unvollstaendig = False
        omdb_rufe = 0
        keys = _meta_keys()
        if keys.get("tmdb") and e.get("tmdb"):
            art = "tv" if e["typ"] == "serie" else "movie"
            try:
                st, roh = _http(f"https://api.themoviedb.org/3/{art}/{e['tmdb']}"
                                f"?api_key={keys['tmdb']}&language=de-DE"
                                f"&append_to_response=credits,recommendations,videos"
                                f"&include_video_language=de,en,null")
                if st == 200:
                    d = json.loads(roh)
                    m["beschreibung"] = d.get("overview") or ""
                    m["tagline"] = d.get("tagline") or ""
                    m["cast"] = [c.get("name") or "" for c in
                                 (d.get("credits") or {}).get("cast") or []][:12]
                    crew = (d.get("credits") or {}).get("crew") or []
                    m["regie"] = [c.get("name") for c in crew
                                  if c.get("job") == "Director"][:3]
                    m["drehbuch"] = [c.get("name") for c in crew
                                     if c.get("job") in ("Writer", "Screenplay",
                                                         "Story", "Novel")][:3]
                    m["trailer"] = [{"key": v.get("key"), "name": v.get("name") or "Trailer"}
                                    for v in (d.get("videos") or {}).get("results") or []
                                    if v.get("site") == "YouTube"
                                    and v.get("type") in ("Trailer", "Teaser")][:6]
                    m["empfehlungen_tmdb"] = [str(x.get("id")) for x in
                                              (d.get("recommendations") or {})
                                              .get("results") or []]
                elif st != 404:            # 404 = Titel gibt es dort nicht (endgültig)
                    unvollstaendig = True
            except Exception:              # noqa: BLE001 — Reihe kommt ohne TMDB
                unvollstaendig = True
        if keys.get("omdb") and e.get("imdb") and not _omdb_erlaubt(cache):
            unvollstaendig = True          # Tagesdeckel: später nachholen
        elif keys.get("omdb") and e.get("imdb"):
            try:
                st, roh = _http(f"https://www.omdbapi.com/?i={e['imdb']}"
                                f"&apikey={keys['omdb']}")
                omdb_rufe += 1
                if st == 200:
                    d = json.loads(roh)
                    # OMDb schreibt fehlende Werte wörtlich als "N/A" — das
                    # gehört nicht in die Anzeige (live gesehen: „MC N/A").
                    def _wert(v):
                        return "" if (v or "").strip().upper() == "N/A" else (v or "")
                    m["imdb_rating"] = _wert(d.get("imdbRating"))
                    m["metacritic"] = _wert(d.get("Metascore"))
                    m["tomatometer"] = _wert(next(
                        (r.get("Value") for r in d.get("Ratings") or []
                         if "Rotten" in (r.get("Source") or "")), ""))
                elif st != 404:
                    unvollstaendig = True
            except Exception:              # noqa: BLE001 — Zahl fehlt dann eben
                unvollstaendig = True
        if unvollstaendig:
            m["unvollstaendig"] = True
        # Technik kommt seit dem Seiten-Abzug nicht mehr im Spiegel mit
        # (teuerstes Feld, live gemessen — s. katalog_abzug): je Titel EIN
        # Einzel-Abruf: Codecs, Auflösung, Ton-Kanäle/-Sprachen, Untertitel-
        # Sprachen (Netflix-Detailseite: Qualität · Sound · Untertitel).
        m["video_codec"] = e.get("video_codec") or ""
        m["audio_codec"] = e.get("audio_codec") or ""
        try:
            st, roh, fehlart, _ = _jellyfin_ruf(_titel_pfad(item_id))
            if st == 200 and not fehlart:
                voll = json.loads(roh)
                for strom in voll.get("MediaStreams") or []:
                    art2 = strom.get("Type")
                    if art2 == "Video":
                        m["video_codec"] = m["video_codec"] or strom.get("Codec") or ""
                        m["hoehe"] = max(m.get("hoehe") or 0, strom.get("Height") or 0)
                    elif art2 == "Audio":
                        m["audio_codec"] = m["audio_codec"] or strom.get("Codec") or ""
                        m["audio_kanaele"] = max(m.get("audio_kanaele") or 0,
                                                 strom.get("Channels") or 0)
                        sp = strom.get("Language") or ""
                        if sp and sp not in m["audio_sprachen"]:
                            m["audio_sprachen"].append(sp)
                    elif art2 == "Subtitle":
                        sp = strom.get("Language") or ""
                        if sp and sp not in m["sub_sprachen"]:
                            m["sub_sprachen"].append(sp)
        except Exception:              # noqa: BLE001 — Technik ist Kür
            pass
        # Zwei-Fragen-Regel (Nachtprüfung 06.08.): mehrere Server-Threads
        # schreiben den Meta-Cache — json_aendern mischt NUR den eigenen
        # Schlüssel ein, statt fremde frische Einträge zu überschreiben. Der
        # OMDb-Zähler zählt dort auf den Stand der Datei weiter (F12).
        def _eintragen(d):
            d[item_id] = m
            if omdb_rufe:
                heute = time.strftime("%Y-%m-%d")
                if d.get("omdb_tag") != heute:
                    d["omdb_tag"], d["omdb_zaehler"] = heute, 0
                d["omdb_zaehler"] = (d.get("omdb_zaehler") or 0) + omdb_rufe
        _json_aendern(_pfade["meta"], _eintragen, standard={})
    return {**e, "beschreibung": m.get("beschreibung") or "",
            "cast": m.get("cast") or [],
            "empfehlungen_tmdb": m.get("empfehlungen_tmdb") or [],
            "imdb_rating": m.get("imdb_rating") or "",
            "metacritic": m.get("metacritic") or "",
            "tomatometer": m.get("tomatometer") or "",
            "video_codec": m.get("video_codec") or e.get("video_codec") or "",
            "audio_codec": m.get("audio_codec") or e.get("audio_codec") or "",
            "tagline": m.get("tagline") or "", "regie": m.get("regie") or [],
            "drehbuch": m.get("drehbuch") or [], "trailer": m.get("trailer") or [],
            "hoehe": m.get("hoehe") or 0,
            "audio_kanaele": m.get("audio_kanaele") or 0,
            "audio_sprachen": m.get("audio_sprachen") or [],
            "sub_sprachen": m.get("sub_sprachen") or [],
            "gemerkt": item_id in merkliste_lesen(profil)}


# ---------------------------------------------------------------- Serien

def episoden(serien_id):
    """Alle Episoden einer Serie (JB-Go „weiter mit den serien episoden"):
    EIN Jellyfin-Ruf über /Shows/{id}/Episodes — liefert Staffel-/Folgen-
    Nummern und den Seh-Stand gleich mit. On demand, kein Cache: der
    Gesehen-Stand soll frisch sein. Rückgabe bleibt eine LISTE; wer wissen
    muss, warum sie leer ist, ruft `episoden_mit_grund`."""
    return episoden_mit_grund(serien_id)[0]


def episoden_mit_grund(serien_id):
    """Wie `episoden`, dazu der Grund einer leeren Liste (Befund 24.09.):
    '' = die Serie hat (bei Jellyfin) keine Folgen, 'zugang' = Renés Server
    lehnt uns ab, 'netz' = nicht erreichbar oder unbrauchbare Antwort.

    Vorher kam jeder Fehler als leere Liste an, und die Oberfläche zeigte eine
    Serie ohne Folgen — genau so sah der 401-Ausfall ab dem 23.09. aus."""
    sauber = re.sub(r"[^A-Za-z0-9]", "", serien_id or "")
    if not sauber:
        return [], ""
    st, roh, art, _ = _jellyfin_ruf(
        f"/Shows/{sauber}/Episodes?userId={{uid}}&Fields=RunTimeTicks", timeout=30)
    if art:
        return [], "zugang" if art in ZUGANG_ARTEN else "netz"
    if st == 403:                          # angemeldet, aber nicht berechtigt
        return [], "zugang"
    if 400 <= st < 500:                    # unbekannte Serie / falsche Kennung
        return [], ""
    if st != 200:
        return [], "netz"
    try:
        items = json.loads(roh).get("Items") or []
    except (ValueError, AttributeError):   # Wartungs-/Proxy-Seite statt JSON
        return [], "netz"
    out = []
    for it in items:
        ud = it.get("UserData") or {}
        ticks = it.get("RunTimeTicks") or 0
        out.append({"id": it.get("Id") or "", "titel": it.get("Name") or "",
                    "staffel": it.get("ParentIndexNumber") or 0,
                    "folge": it.get("IndexNumber") or 0,
                    "laufzeit_min": round(ticks / 600_000_000) if ticks else None,
                    "position_s": round((ud.get("PlaybackPositionTicks") or 0) / 10_000_000),
                    "gesehen": bool(ud.get("Played"))})
    out.sort(key=lambda e: (e["staffel"], e["folge"]))
    return out, ""


# ---------------------------------------------------------------- Merkliste

def merkliste_lesen(profil="standard"):
    """Je PROFIL eine Liste (Teilprojekt 3). Altbestand (nackte Liste aus
    Build 181) wandert stillschweigend zum Standard-Profil."""
    try:
        with open(_pfade["merk"], encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return []
    if isinstance(d, list):                # Altformat → Standard-Profil
        return d if profil == "standard" else []
    return d.get(profil or "standard") or []


def merkliste_toggle(item_id, profil="standard"):
    """Film-Watchlist (JB-Go): LOKALE Liste je Profil — ausfallfest; ein
    Jellyfin-Favoriten-Sync wäre ein späterer Kandidat (unbestätigt).
    Rückgabe: ist der Titel JETZT gemerkt?"""
    profil = profil or "standard"
    try:
        with open(_pfade["merk"], encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    if isinstance(d, list):                # Altformat einmalig heben
        d = {"standard": d}
    # Unter Sperre kippen (JB-Dauerregel „geteilter Zustand, zwei Fragen"):
    # PC, Fernsehmodus und Handy schreiben in dieselbe Datei. Ohne Sperre
    # überschrieben sich zwei gleichzeitige Herz-Klicks — und zwar nicht nur
    # einen Eintrag, sondern den ganzen Profil-Schlüssel des anderen (gemessen
    # 13.08.2026). Der frisch geladene Stand IN der Sperre entscheidet, nicht
    # der vorher gelesene.
    ergebnis = {}

    def _kippen(gd):
        if isinstance(gd, list):           # Altformat einmalig heben
            gd = {"standard": gd}
        ids = list(gd.get(profil) or [])
        if item_id in ids:
            ids.remove(item_id)
            ergebnis["an"] = False
        else:
            ids.append(item_id)
            ergebnis["an"] = True
        gd[profil] = ids
        return gd

    if _json_aendern(_pfade["merk"], _kippen, standard={}) is None:
        return item_id in (d.get(profil) or [])   # Sperre besetzt: Stand bleibt
    return ergebnis.get("an", False)


# ---------------------------------------------------------------- Reihen

def reihen(profil="standard"):
    """Home-Reihen aus dem Spiegel, damit die Anzeige auch bei Renés Ausfall
    steht (Spec „Ausfall-Verhalten"). Einziger Netzweg: das Eichen der Top-
    Kandidaten mit TMDB-Stimmen, gedeckelt auf EICHEN_VERSUCHE Abrufe je Aufruf
    (Versuche, nicht Erfolge; F13). Nach einem Netz- oder Serverfehler ruht es
    EICHEN_PAUSE_S, ein bei TMDB unbekannter Titel EICHEN_FEHL_RUHE_S."""
    alle = katalog_lesen()["eintraege"]
    weiter = [e for e in alle if e["position_s"] > 0 and not e["gesehen"]]
    # Top als BAYES-SCORE (JB-Go): Jellyfin hat keinen Vote-Count, darum
    # holen wir TMDB-Stimmen für die Roh-Kandidaten (einmalig gecacht, max 8
    # Abrufe je Lauf — Top wird über wenige Aufrufe komplett geeicht).
    # score = v/(v+m)*R + m/(v+m)*C  (m=500 Prior-Stimmen, C=6.8 Prior-Note);
    # ohne Stimmen kommt keiner über den Prior — Ein-Stimmen-★10 sind tot.
    cache = _meta_cache()
    stimmen = cache.get("tmdb_stimmen") or {}
    fehl = dict(cache.get("tmdb_stimmen_fehl") or {})
    keys = _meta_keys()
    # 120 Kandidaten, damit nach dem Filme/Serien-Filter der Tabs (JB 06.08.:
    # „Filme und Serien sind ihren eigenen tabs eigen zu listen") je Seite
    # noch 10 übrig bleiben; geeicht wird weiter mit 8 Abrufen je Lauf.
    kand = sorted((e for e in alle if e.get("rating") and not e["gesehen"]),
                  key=lambda e: e["rating"], reverse=True)[:120]
    jetzt = time.time()
    neu, versuche, pause = 0, 0, 0.0
    offen = keys.get("tmdb") and jetzt >= (cache.get("tmdb_stimmen_pause") or 0)
    for e in (kand if offen else ()):
        t = e.get("tmdb")
        if not t or t in stimmen or jetzt - (fehl.get(t) or 0) < EICHEN_FEHL_RUHE_S:
            continue
        if versuche >= EICHEN_VERSUCHE:
            break
        versuche += 1
        art = "tv" if e["typ"] == "serie" else "movie"
        try:
            st, roh = _http(f"https://api.themoviedb.org/3/{art}/{t}"
                            f"?api_key={keys['tmdb']}")
            if st == 200:
                d2 = json.loads(roh)
                stimmen[t] = [d2.get("vote_count") or 0, d2.get("vote_average") or 0]
                fehl.pop(t, None)
                neu += 1
            elif st == 404:                # TMDB kennt den Titel nicht: einen Tag Ruhe
                fehl[t] = jetzt
            else:                          # 401, 429, 5xx: TMDB hat gerade ein Problem
                pause = jetzt + EICHEN_PAUSE_S
                break
        except Exception:                  # noqa: BLE001 — Netz weg: eine Stunde Ruhe
            pause = jetzt + EICHEN_PAUSE_S
            break
    if versuche:
        def _mischen(d):
            alt = d.get("tmdb_stimmen") or {}
            alt.update(stimmen)
            d["tmdb_stimmen"] = alt
            d["tmdb_stimmen_fehl"] = {k: v for k, v in fehl.items()
                                      if jetzt - v < EICHEN_FEHL_RUHE_S and k not in alt}
            if pause:
                d["tmdb_stimmen_pause"] = pause
        _json_aendern(_pfade["meta"], _mischen, standard={})

    def _score(e):
        s = stimmen.get(e.get("tmdb") or "")
        if s and s[0]:
            v, r = float(s[0]), float(s[1])
            return (v / (v + 500.0)) * r + (500.0 / (v + 500.0)) * 6.8
        # Ohne Stimmen kommt niemand über den Prior — und ohne Bewertung
        # (79 der 4885 echten Einträge) darf es keinen Absturz geben: die
        # Genre-Reihen sortieren seit 13.08. den GANZEN Katalog, nicht mehr
        # nur die 120 bewerteten Kandidaten.
        try:
            return min(float(e.get("rating") or 0.0), 6.8)
        except (TypeError, ValueError):
            return 0.0
    # 30 statt 10: die Tabs Filme/Serien filtern clientseitig auf ihre Art
    # und schneiden dann auf 10 — so bleibt jede Seite eine echte Top-10.
    top = sorted(kand, key=_score, reverse=True)[:30]
    neu = sorted((e for e in alle if e.get("hinzugefuegt")),
                 key=lambda e: e["hinzugefuegt"], reverse=True)[:20]
    # JB 06.08.: „nur <20 actionfilme … bei 4000 filmen?" — ALLE Genres
    # (häufigste zuerst). Drei Dinge, die erst der Lauf gegen Renés echte 4885
    # Titel sichtbar gemacht hat (13.08.2026, alle drei einzeln nachgemessen):
    #
    # 1. Der Deckel schnitt ein ALPHABET ab, keine Auswahl. Der Spiegel kommt in
    #    Jellyfins SortName-Reihenfolge; `[:100]` ohne sort lieferte deshalb je
    #    Genre nur den Anfang des Alphabets — „Action" reichte von „2 Fast 2
    #    Furious" bis „Bee and PuppyCat", Interstellar/Matrix/Terminator kamen in
    #    KEINER Reihe vor. Über alle Reihen zusammen erreichten nur 1933 der 4885
    #    Titel (40 %) überhaupt eine Kachel. Jetzt entscheidet derselbe Bayes-
    #    Score wie bei „Top": die Reihe zeigt das Beste des Genres.
    # 2. Der Deckel griff VOR dem Typ-Filter der Oberfläche. Der Client filtert
    #    jede Reihe auf seinen Tab (Filme/Serien) — aus 100 gemischten wurden im
    #    Serien-Tab 7 von 41 Horror-Serien. Jetzt wird JE TYP gedeckelt, damit
    #    beide Tabs eine volle Reihe bekommen.
    # 3. Sprach-Dubletten (s. GENRE_GLEICH oben).
    haeufig = {}
    for e in alle:
        for g in {genre_name(g) for g in e["genres"]}:
            haeufig[g] = haeufig.get(g, 0) + 1
    genres = {}
    for g, _ in sorted(haeufig.items(), key=lambda kv: kv[1], reverse=True):
        drin = [e for e in alle if g in {genre_name(x) for x in e["genres"]}]
        drin.sort(key=_score, reverse=True)
        filme_ = [e for e in drin if e["typ"] != "serie"][:GENRE_JE_TYP]
        serien = [e for e in drin if e["typ"] == "serie"][:GENRE_JE_TYP]
        # zurück in Score-Reihenfolge, damit die Reihe im gemischten Desktop-Blick
        # nicht erst alle Filme und dann alle Serien zeigt
        genres[g] = sorted(filme_ + serien, key=_score, reverse=True)
    merk_ids = merkliste_lesen(profil)
    merk = sorted((e for e in alle if e["id"] in set(merk_ids)),
                  key=lambda e: merk_ids.index(e["id"]))
    return {"weiterschauen": weiter, "top": top, "neu": neu, "genres": genres,
            "merkliste": merk}


def mehr_wie(item_id):
    """TMDB-Empfehlungen ∩ Katalog — nur was Renés Server WIRKLICH hat."""
    d = detail(item_id)
    if not d:
        return []
    ids = set(d.get("empfehlungen_tmdb") or [])
    return [e for e in katalog_lesen()["eintraege"]
            if e["tmdb"] and e["tmdb"] in ids and e["id"] != item_id]


# ---------------------------------------------------------------- Snippets
# Hover-Szenen-Snippet (JB-Go, Recherche 05.08.): Netflix-Prinzip „nach dem
# Setup, vor den Spoilern" — deterministisch bei 27 % der Laufzeit, 6 s,
# stumm, klein. ffmpeg seekt per Range direkt auf der Jellyfin-Stream-URL
# (kein Vollabruf); der Token bleibt am PC, der Client sieht nur die Datei.

_snippet_laeuft = set()


def snippet_pfad(item_id):
    sauber = re.sub(r"[^A-Za-z0-9]", "", item_id or "")
    return os.path.join(_pfade["snippets"], f"{sauber}.mp4") if sauber else ""


def snippet_backen(item_id):
    """Einmalig je Titel; still bei jedem Fehler (Vorschau ist Kür)."""
    pfad = snippet_pfad(item_id)
    if not pfad or os.path.exists(pfad) or item_id in _snippet_laeuft:
        return False
    e = next((x for x in katalog_lesen()["eintraege"] if x["id"] == item_id), None)
    strom = stream_url(item_id)
    if not (e and strom):
        return False
    start = max(60, int((e.get("laufzeit_min") or 30) * 60 * 0.27))
    _snippet_laeuft.add(item_id)
    try:
        import subprocess
        os.makedirs(_pfade["snippets"], exist_ok=True)
        tmp = pfad + ".tmp.mp4"
        # ffmpeg IMMER absolut aus System/bin (Fund 07.08.: nackt "ffmpeg"
        # hängt am Prozess-PATH — und ein Fehllauf hinterließ die
        # Müll-Datei "-movflags" im System-Ordner).
        ff = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg.exe")
        if not os.path.exists(ff):
            ff = "ffmpeg"
        subprocess.run(
            [ff, "-y", "-ss", str(start), "-i", strom, "-t", "6", "-an",
             "-vf", "scale=480:-2", "-movflags", "+faststart", tmp],
            capture_output=True, timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if os.path.exists(tmp) and os.path.getsize(tmp) > 10_000:
            os.replace(tmp, pfad)
            return True
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:                      # noqa: BLE001 — Vorschau ist Kür
        pass
    finally:
        _snippet_laeuft.discard(item_id)
    return False


def snippet_lesen(item_id):
    """Fertiges Snippet als Bytes; None stößt (einmalig) das Backen an."""
    pfad = snippet_pfad(item_id)
    if pfad and os.path.exists(pfad):
        with open(pfad, "rb") as f:
            return f.read()
    return None


# ---------------------------------------------------------------- Jellyseerr
# Teilprojekt 4 (JB-Go „weiter mit teilprojekt 4, den requests über
# jellyseerr"): Film-/Serien-Wünsche gehen an Renés Jellyseerr (dahinter
# Radarr + Sonarr). Anmeldung mit JBs JELLYFIN-Konto (ein Konto für alles,
# live sondiert 05.08.: 200, Rechte 176); Session-Cookie mit 401/403-Heilung.
# 1080p-Wünsche → René; der 4K-Stack bei JB ist ein späteres Teilprojekt.

_seerr = {"cookie": ""}
SEERR_STATUS = {5: "da", 4: "teils", 3: "kommt", 2: "kommt", 1: ""}


def _seerr_url():
    try:
        import keyring
        return (keyring.get_password("Sync-Jellyseerr", "url") or "").rstrip("/")
    except Exception:                      # noqa: BLE001
        return ""


def _seerr_http(url, daten=None, kopf=None, timeout=20):
    """Eigener Netz-Zugang für Seerr (Tests patchen ihn): liefert zusätzlich
    das Set-Cookie der Antwort (Session)."""
    req = urllib.request.Request(url, method="POST" if daten is not None else "GET")
    for k, v in (kopf or {}).items():
        req.add_header(k, v)
    body = json.dumps(daten).encode("utf-8") if daten is not None else None
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, body, timeout=timeout) as r:
            return r.status, r.read(), (r.headers.get("Set-Cookie") or "")
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"{}", ""


def _seerr_anmelden():
    z = _zugang()
    basis = _seerr_url()
    if not (z and basis):
        return False
    try:
        st, _, keks = _seerr_http(basis + "/api/v1/auth/jellyfin",
                                  daten={"username": z["benutzer"],
                                         "password": z["passwort"]})
    except Exception:                      # noqa: BLE001
        return False
    if st != 200 or not keks:
        return False
    _seerr["cookie"] = keks.split(";")[0]
    return True


def _seerr_ruf(pfad, daten=None):
    """Seerr-Aufruf mit Sitzung; abgelaufene Sitzung wird EINMAL geheilt."""
    basis = _seerr_url()
    if not basis:
        return 0, {}
    if not _seerr["cookie"] and not _seerr_anmelden():
        return 0, {}
    for versuch in (1, 2):
        try:
            st, roh, _ = _seerr_http(basis + pfad, daten=daten,
                                     kopf={"Cookie": _seerr["cookie"]})
        except Exception:                  # noqa: BLE001
            return 0, {}
        if st in (401, 403) and versuch == 1:
            _seerr["cookie"] = ""
            if not _seerr_anmelden():
                return st, {}
            continue
        try:
            return st, json.loads(roh or b"{}")
        except ValueError:
            return st, {}
    return 0, {}


def seerr_suche(q):
    """Suche im GANZEN Katalog (TMDB via Seerr) — mit ehrlichem Status:
    da / teils / kommt (angefragt) / '' (wünschbar)."""
    if not (q or "").strip():
        return []
    st, d = _seerr_ruf("/api/v1/search?query=" + urllib.parse.quote(q.strip()))
    if st != 200:
        return []
    out = []
    for x in d.get("results") or []:
        if x.get("mediaType") not in ("movie", "tv"):
            continue
        mi = x.get("mediaInfo") or {}
        datum = x.get("releaseDate") or x.get("firstAirDate") or ""
        out.append({"tmdb": x.get("id"),
                    "typ": "film" if x.get("mediaType") == "movie" else "serie",
                    "titel": x.get("title") or x.get("name") or "",
                    "jahr": (datum or "")[:4],
                    "poster": ("https://image.tmdb.org/t/p/w300" + x["posterPath"])
                              if x.get("posterPath") else "",
                    "status": SEERR_STATUS.get(mi.get("status") or 0, "")})
    return out[:20]


def seerr_anfragen(tmdb, typ):
    """Den Wunsch stellen. Serien: alle Staffeln (JBs Wunsch-Fluss simpel
    halten); 409 = gibt es schon — ehrlich melden, kein Fehlerkasten."""
    daten = {"mediaType": "movie" if typ != "serie" else "tv", "mediaId": int(tmdb)}
    if typ == "serie":
        daten["seasons"] = "all"
    st, d = _seerr_ruf("/api/v1/request", daten=daten)
    if st in (200, 201):
        return {"ok": True, "fehler": ""}
    if st == 409:
        return {"ok": False, "fehler": "Schon angefragt oder vorhanden."}
    return {"ok": False, "fehler": f"Anfrage fehlgeschlagen (HTTP {st})."}


def seerr_meine(n=20):
    """Die letzten Wünsche mit Stand — Titel aus dem eigenen Katalog; noch
    nicht gespiegelte Wünsche bekommen ihren Titel EINMALIG von TMDB
    (Seerr liefert nur die Id — „Wunsch (TMDB 10564)" hilft am TV niemandem)."""
    st, d = _seerr_ruf(f"/api/v1/request?take={int(n)}&sort=added")
    if st != 200:
        return []
    kat = {e["tmdb"]: e for e in katalog_lesen()["eintraege"] if e.get("tmdb")}
    cache = _meta_cache()
    tt = cache.get("tmdb_titel") or {}
    keys = _meta_keys()
    neu = False
    out = []
    for r in d.get("results") or []:
        m = r.get("media") or {}
        tmdb = str(m.get("tmdbId") or "")
        typ = "film" if m.get("mediaType") == "movie" else "serie"
        e = kat.get(tmdb)
        titel = (e or {}).get("titel") or tt.get(tmdb) or ""
        if not titel and keys.get("tmdb") and tmdb:
            art = "movie" if typ == "film" else "tv"
            try:
                st2, roh2 = _http(f"https://api.themoviedb.org/3/{art}/{tmdb}"
                                  f"?api_key={keys['tmdb']}&language=de-DE")
                if st2 == 200:
                    d2 = json.loads(roh2)
                    titel = d2.get("title") or d2.get("name") or ""
                    if titel:
                        tt[tmdb] = titel
                        neu = True
            except Exception:              # noqa: BLE001 — Nummer bleibt Rückfall
                pass
        out.append({"tmdb": tmdb, "typ": typ,
                    "titel": titel or f"Wunsch (TMDB {tmdb})",
                    "id": (e or {}).get("id") or "",
                    "status": SEERR_STATUS.get(m.get("status") or 0, "kommt")})
    if neu:
        def _mischen(d):
            alt = d.get("tmdb_titel") or {}
            alt.update(tt)
            d["tmdb_titel"] = alt
        _json_aendern(_pfade["meta"], _mischen, standard={})
    return out


# ---------------------------------------------------------------- Abspielen

# Wie das Token in die Strom-Adresse kommt (Befund 4 vom 24.09., am 25.09. am
# Quelltext v12.1 beantwortet, live nicht gemessen): Jellyfin 12.1 liest in der
# Adresse nur `ApiKey` (AuthorizationContext.cs:103-106); `api_key` nur mit dem
# Legacy-Schalter (:108-111), den die Migration DisableLegacyAuthorization beim
# Update abschaltet — bei René nachweislich aus. Weil der Strom-Endpunkt anonym
# ist (VideosController ohne [Authorize]), lief der Film mit `api_key` trotzdem,
# aber ohne Konto. `ApiKey` lesen auch 10.10.7 und 10.11.11. Gilt für ALLE
# Verbraucher: VLC, Browser-Proxy (samt ffmpeg-Umwandlung) und Szenen-Vorschau.
STROM_TOKEN_PARAM = "ApiKey"


def _strom_adresse(basis, item_id, token):
    """DIE eine Stelle, an der eine Strom-Adresse entsteht: VLC-Start, Browser-
    Proxy (/api/filme/direkt, samt ffmpeg-Umwandlung) und Szenen-Vorschau
    bekommen alle, was hier gebaut wird. Die Kennung wird kodiert — sie kommt
    vom Client, und mit `../` hätte sie sonst eine beliebige andere Jellyfin-
    Route mit unserem Token angesteuert."""
    return (f"{basis}/Videos/{urllib.parse.quote(str(item_id or ''), safe='')}/stream"
            f"?static=true&{STROM_TOKEN_PARAM}={urllib.parse.quote(token or '', safe='')}")


def stream_url(item_id, druck=False):
    """Direct-Play-URL für den LOKALEN VLC (Token in der URL ist ok, weil sie
    diesen PC nie verlässt — Clients bekommen sie NICHT).

    `druck=True` NUR für JBs ausdrückliche Drücke: VLC-Start und Browser-Proxy.
    Die kommen durch die Merkmal-Ruhe (Prüfung Runde 1: vorher 503 für 10
    Minuten), mit höchstens einer Anmeldung je Ruhe (Runde 2, s. _druck_in_ruhe).
    Ohne `druck` (Hover-Vorschau, jede Automatik) hält die Ruhe sie auf — vorher
    war stream_url ganz ausgenommen, und die Vorschau meldete sich mit an.
    Die 403-Drossel gilt immer."""
    s = _anmelden(druck=druck)
    z = _zugang()
    if not (s and z):
        return None
    return _strom_adresse(z["url"], item_id, s["token"])


def _queue_lesen():
    try:
        with open(_pfade["queue"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


# Warum eine Meldung nicht ankam — der Unterschied entscheidet, ob das
# Nachreichen weitermachen darf (Muster SyncFindus zubringer_jellyfin.py,
# 17.09.2026). 401/403/408/429 sind KEIN kaputter Eintrag: das sind Zugang,
# Drossel oder Zeit — da lohnt der nächste Lauf.
SENDE_OK = "ok"
SENDE_KAPUTT = "kaputt"                    # 4xx: DIESE Meldung geht nie durch
SENDE_SERVER = "server"                    # Netz, Zugang, 5xx: später erneut


def _sende_grund(st):
    if st in (200, 204):
        return SENDE_OK
    if 400 <= (st or 0) < 500 and st not in (401, 403, 408, 429):
        return SENDE_KAPUTT
    return SENDE_SERVER


def _fortschritt_senden_mit_grund(item_id, position_s, gesehen=False, nur_gesehen=False):
    """Stelle (Progress) und ggf. „gesehen" (PlayedItems) melden; Rückgabe SENDE_*.

    Live gefunden (05.08.): Jellyfin wirft das alte Token weg, sobald sich
    dieselbe DeviceId neu anmeldet — die Heilung (EINMAL frisch anmelden und
    wiederholen) steckt seit 24.09. für alle Wege in _jellyfin_ruf, auch für
    PlayedItems. Dessen Status wurde bis 24.09. gar nicht geprüft: scheiterte
    nur dieser Ruf, ging „gesehen" still verloren (folgenende.md Befund 3).
    `nur_gesehen`: beim Nachreichen zählt bei „gesehen" nur PlayedItems — eine
    alte Stelle soll nichts Neueres überschreiben."""
    if not nur_gesehen:
        st, _, art, _ = _jellyfin_ruf("/Sessions/Playing/Progress",
                                      daten={"ItemId": item_id,
                                             "PositionTicks": int(position_s) * 10_000_000,
                                             "IsPaused": False})
        if art:                            # Netz/Zugang ⇒ Queue
            return SENDE_SERVER
        grund = _sende_grund(st)
        if grund != SENDE_OK or not gesehen:
            return grund
    # POST /UserPlayedItems/{id}?userId= (PlaystateController.MarkPlayedItem,
    # Antwort 200 mit UserItemDataDto) statt der veralteten
    # /Users/{uid}/PlayedItems/{id}.
    st, _, art, _ = _jellyfin_ruf(
        "/UserPlayedItems/" + urllib.parse.quote(str(item_id), safe="") + "?userId={uid}",
        daten={})
    if art:
        return SENDE_SERVER
    return _sende_grund(st)


def fortschritt(item_id, position_s, gesehen=False):
    """Fortschritt an Jellyfin melden; scheitert es, wandert die Meldung in die
    Queue und geht beim nächsten Erfolg/Abzug nach (nichts geht verloren).
    Weist Jellyfin die Meldung selbst ab (4xx), wird sie als `abgewiesen`
    gemerkt: nie wieder gesendet, aber auch nicht still verworfen.
    `ts` ist der Zeitpunkt der MELDUNG (vor dem Senden), nicht der des
    Scheiterns: nur so ordnet das Nachreichen sie richtig ein."""
    ts = time.time()
    grund = _fortschritt_senden_mit_grund(item_id, position_s, gesehen)
    if grund == SENDE_OK:
        _aeltere_erledigt(item_id, position_s, gesehen, ts)
        try:
            _spiegel_nachziehen(item_id, position_s, gesehen)
        except Exception:                  # noqa: BLE001 — die Meldung selbst ist angekommen
            pass
        return True
    neu = {"item": item_id, "position_s": int(position_s),
           "gesehen": bool(gesehen), "ts": ts}
    if grund == SENDE_KAPUTT:
        neu["abgewiesen"] = True
    _json_aendern(_pfade["queue"], lambda q: (q or []) + [neu], standard=[])
    return False


class _SpiegelUnveraendert(Exception):
    """Bricht json_aendern ab, ohne zu schreiben (nichts nachzuziehen)."""


def _spiegel_nachziehen(item_id, position_s, gesehen):
    """Nach einer ANGENOMMENEN Meldung den Eintrag im Katalog-Spiegel nachziehen
    (folgenende.md, Gegenprüfung Punkt 6). reihen() und detail() lesen den
    Spiegel, und der nächste Abzug kommt erst in 6 h — seit 23.09. scheitert er
    ganz; „Weiterschauen" und die Film-Info blieben so lange falsch. Wie
    Jellyfin: „gesehen" heißt Stelle 0; eine bloße Stelle ändert „gesehen" nicht.
    Folgen stehen nicht im Spiegel (dort nur Filme und Serien): dann, wie bei
    einem schon stimmenden Eintrag, bleibt die Datei unberührt. Rückgabe: ob
    geschrieben wurde."""
    if not any(isinstance(e, dict) and e.get("id") == item_id
               for e in katalog_lesen().get("eintraege") or []):
        return False
    soll = {"position_s": 0, "gesehen": True} if gesehen else {"position_s": int(position_s)}

    def _aendern(k):
        treffer = [e for e in ((k or {}).get("eintraege") or [])
                   if isinstance(e, dict) and e.get("id") == item_id]
        if not treffer or all(all(e.get(f) == w for f, w in soll.items()) for e in treffer):
            raise _SpiegelUnveraendert
        for e in treffer:
            e.update(soll)
        return k
    try:
        return _json_aendern(_pfade["katalog"], _aendern) is not None
    except _SpiegelUnveraendert:
        return False


def _aeltere_erledigt(item_id, position_s, gesehen, ts):
    """Direkt gelungen (Prüfung Runde 1): ältere Einträge desselben Titels in
    der Warteschlange sind damit erledigt. Vorher blieben sie liegen, und das
    Nachreichen (am Ende des nächsten Abzugs, bis zu 6 h später) schickte die
    ALTE Stelle hinterher.

    Ein älteres „gesehen" ist durch eine bloße Stelle NICHT erledigt: es bleibt,
    und die neue Stelle kommt dahinter noch einmal in die Warteschlange — so
    schickt das Nachreichen beides in der Reihenfolge der Meldungen (erst
    „gesehen", dann die neuere Stelle). Abgewiesene Einträge bleiben, wie sie
    sind. Gleiche Sperre wie beim Nachreichen (_json_aendern)."""
    def betroffen(x):
        return (isinstance(x, dict) and x.get("item") == item_id
                and not x.get("abgewiesen") and _q_ts(x) < ts)
    if not any(betroffen(x) for x in _queue_lesen()):
        return                             # der Normalfall: nichts anzufassen

    def _aendern(liste):
        neu, gesehen_offen = [], False
        for x in liste or []:
            if betroffen(x):
                if gesehen or not x.get("gesehen"):
                    continue               # durch die neue Meldung erledigt
                gesehen_offen = True
            neu.append(x)
        if gesehen_offen:
            neu.append({"item": item_id, "position_s": int(position_s),
                        "gesehen": False, "ts": ts})
        return neu
    _json_aendern(_pfade["queue"], _aendern, standard=[])


def _q_schluessel(m):
    return (m.get("item"), int(m.get("position_s") or 0), bool(m.get("gesehen")),
            round(float(m.get("ts") or 0), 3))


def _q_ts(m):
    try:
        return float(m.get("ts") or 0)
    except (TypeError, ValueError):
        return 0.0


def fortschritt_nachreichen():
    """Liegengebliebene Meldungen senden; bei erneutem Fehlschlag bleibt der
    Rest liegen. Gibt die Zahl der erfolgreich nachgereichten zurück.

    Lesen — Senden — GEZIELT entfernen, statt die ganze Datei zurückzuschreiben:
    Der alte Weg las die Warteschlange, sendete (dauert), und schrieb dann den
    Rest über den inzwischen aktuellen Stand. Wer in diesen Sekunden einen Film
    stoppte, verlor seinen Spot spurlos (gemessen 13.08.2026 — genau während des
    6-h-Abzugs, der ja mit `fortschritt_nachreichen()` endet).

    Seit 24.09. (Gegenprüfung folgenende.md):
    - Je Titel zählt nur die JÜNGSTE Stelle; ältere sind mit ihr erledigt.
      Vorher ging jede in Reihenfolge raus, und eine alte Stelle überschrieb
      eine neuere desselben Titels.
    - Bei „gesehen" nur PlayedItems, keine alte Stelle.
    - Ein „gesehen" geht nie verloren (Prüfung Runde 1): liegt irgendwo in der
      Gruppe eines, geht zuerst PlayedItems raus, danach die jüngste Stelle —
      nur wenn sie jünger ist als das „gesehen". Vorher nahm das Nachreichen
      nur die jüngste Meldung, und ein älteres „gesehen" verschwand mit ihr.
    - Ein Eintrag, den Jellyfin mit 4xx abweist, wird als `abgewiesen`
      markiert und übersprungen, statt über `break` alle dahinter aufzuhalten
      — still, denn die Warteschlange zeigt niemand an. Gelöscht wird er nicht.

    Bewusste Richtung: Im Zweifel lieber doppelt melden als verlieren. Einen
    Fortschritt zu setzen ist idempotent — ihn zu verlieren nicht."""
    offen = [m for m in _queue_lesen()
             if isinstance(m, dict) and m.get("item") and not m.get("abgewiesen")]
    gruppen = {}
    for m in offen:
        gruppen.setdefault(m["item"], []).append(m)
    geschafft, erledigt, kaputt = 0, set(), set()
    server_problem = False
    for gruppe in sorted(gruppen.values(), key=lambda g: max(map(_q_ts, g))):
        juengste = max(gruppe, key=_q_ts)
        gesehen = [x for x in gruppe if x.get("gesehen")]
        schritte = []                      # (Meldung, nur „gesehen"?) in Meldungs-Reihenfolge
        if gesehen:
            g = max(gesehen, key=_q_ts)
            schritte.append((g, True))
            if _q_ts(juengste) > _q_ts(g):
                schritte.append((juengste, False))
        else:
            schritte.append((juengste, False))
        angekommen = False
        for m, nur_gesehen in schritte:
            # Eine bloße Stelle erledigt nie ein „gesehen" (Prüfung Runde 2):
            # sonst löschte die angekommene jüngere Stelle ein „gesehen", das
            # Jellyfin eben abgewiesen hatte — statt es als abgewiesen zu merken.
            teil = {_q_schluessel(x) for x in gruppe
                    if _q_ts(x) <= _q_ts(m) and (nur_gesehen or not x.get("gesehen"))} - erledigt
            grund = _fortschritt_senden_mit_grund(
                m["item"], m.get("position_s") or 0, nur_gesehen, nur_gesehen=nur_gesehen)
            if grund == SENDE_OK:
                erledigt |= teil
                angekommen = True
            elif grund == SENDE_KAPUTT:
                kaputt |= teil
            else:
                server_problem = True      # Server hat ein Problem: nächster Lauf
                break
        if server_problem:
            break
        geschafft += angekommen
    if erledigt or kaputt:
        def _aufraeumen(liste):
            neu = []
            for x in liste or []:
                if isinstance(x, dict) and x.get("item"):
                    k = _q_schluessel(x)
                    if k in erledigt:
                        continue
                    if k in kaputt:
                        x = dict(x, abgewiesen=True)
                neu.append(x)
            return neu
        _json_aendern(_pfade["queue"], _aufraeumen, standard=[])
    return geschafft
