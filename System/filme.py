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
import time
import urllib.error
import urllib.parse
import urllib.request

import familie as fam

_pfade = {}                                # gesetzt von einrichten()
_sitzung = {}                              # {"token","user_id","version"}
_fehlversuch_ts = 0.0                      # letzter GESCHEITERTER Abzug (Backoff)
_anmelde_sperre_ts = 0.0                   # Anmelde-Backoff (403 ⇒ 10 min Ruhe)
FEHL_BACKOFF_S = 30 * 60                   # nach Fehlschlag frühestens in 30 min wieder
META_HALTBAR_S = 14 * 24 * 3600            # Ratings altern langsam (Spec)
OMDB_TAGES_DECKEL = 950                    # Free-Key: 1.000/Tag — Puffer lassen
GERAET_KOPF = ('MediaBrowser Client="Sync", Device="SyncYouTube", '
               'DeviceId="sync-jb", Version="1.0"')
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


def _anmelden():
    global _anmelde_sperre_ts
    if _sitzung.get("token"):
        return _sitzung
    # Anmelde-Backoff (Fund 06.08.: Anmelde-STURM — Zweitprozesse mit gleicher
    # DeviceId invalidierten sich gegenseitig die Tokens, jede Heilung meldete
    # sich neu an, bis der Server 403 sperrte). Nach einem Fehlschlag ist
    # RUHE: 403 = 10 Minuten (Anmeldesperre ausklingen lassen), sonst 60 s.
    if time.time() < _anmelde_sperre_ts:
        return None
    z = _zugang()
    if not z:
        return None
    try:
        # Jellyfin 10.11 (Renés Server-Update 06.08.): der alte
        # X-Emby-Authorization-Kopf ist abgekündigt — beide Formen senden.
        st, roh = _http(z["url"] + "/Users/AuthenticateByName",
                        daten={"Username": z["benutzer"], "Pw": z["passwort"]},
                        kopf={"X-Emby-Authorization": GERAET_KOPF,
                              "Authorization": GERAET_KOPF})
    except Exception:                      # noqa: BLE001 — Server aus/Netz weg
        _anmelde_sperre_ts = time.time() + 60
        return None
    if st != 200:
        _anmelde_sperre_ts = time.time() + (600 if st == 403 else 60)
        return None
    d = json.loads(roh or b"{}")
    _sitzung.update(token=d.get("AccessToken") or "",
                    user_id=(d.get("User") or {}).get("Id") or "")
    try:
        st, roh = _http(z["url"] + "/System/Info",
                        kopf={"X-Emby-Token": _sitzung["token"]})
        _sitzung["version"] = (json.loads(roh).get("Version") or "?") if st == 200 else "?"
    except Exception:                      # noqa: BLE001 — Version ist Kür
        _sitzung["version"] = "?"
    return _sitzung


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
    s = _anmelden()
    if not s:
        return None
    try:
        st, roh = _http(f"{_zugang()['url']}/Users/{s['user_id']}/Items/{item_id}",
                        kopf={"X-Emby-Token": s["token"]})
    except Exception:                          # noqa: BLE001 — Netz weg
        return None
    if st != 200:
        return None
    try:
        it = json.loads(roh)
    except ValueError:
        return None
    if not it.get("Id"):
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
            d["fehlversuche"] = int(d.get("fehlversuche") or 0) + 1
            d.setdefault("fehler_seit", jetzt)
        if erg.get("ok"):
            d.pop("fehler_seit", None)
    try:
        fam.json_aendern(_pfade["zustand"], _setzen, standard={})
    except (OSError, ValueError):          # Melden darf den Abzug nie kippen
        pass
    return erg


def zustand():
    """Wie es um den Spiegel steht — für Anzeige und Dashboard.

    `still_seit_s` ist die Zeit seit dem letzten ERFOLG (nicht seit dem letzten
    Versuch): genau die Größe, die beim 403-Ausfall niemand sah."""
    d = fam.json_laden(_pfade.get("zustand") or "", {}) or {}
    kat = katalog_lesen()
    stand = kat.get("stand") or 0
    erfolg = d.get("letzter_erfolg") or stand
    return {
        "stand": stand,
        "anzahl": len(kat.get("eintraege") or []),
        "server_version": kat.get("server_version") or "?",
        "letzter_erfolg": erfolg,
        "letzter_versuch": d.get("letzter_versuch") or 0,
        "fehler": d.get("fehler") or "",
        "fehlversuche": int(d.get("fehlversuche") or 0),
        "still_seit_s": max(0.0, time.time() - erfolg) if erfolg else 0.0,
        "zugang": bool(_zugang()),
    }


def katalog_abzug():
    """Voll-Abzug → filme_katalog.json (atomar; scheitert er, bleibt der alte
    Spiegel stehen — Ausfall-Verhalten laut Spec). Der Ausgang wird IMMER in
    `filme_zustand.json` festgehalten, siehe `_zustand_merken`."""
    return _zustand_merken(_katalog_abzug())


def _katalog_abzug():
    global _fehlversuch_ts
    z = _zugang()
    if not z:                              # kein Backoff: Einrichtung fehlt nur
        return {"ok": False, "anzahl": 0,
                "fehler": "Kein Zugang im Keyring (Sync-Jellyfin)."}
    s = _anmelden()
    if not s:
        _fehlversuch_ts = time.time()
        return {"ok": False, "anzahl": 0, "fehler": "Anmeldung fehlgeschlagen."}
    # Live gemessen (05.08., Renés Server): der Voll-Abzug in EINEM Ruf läuft
    # in jeden Timeout (>300 s), und MediaStreams ist das teure Feld (63 s für
    # 200 Titel MIT, 57 s für 1000 OHNE). Darum: seitenweise à 1000 ohne
    # MediaStreams (~5 min gesamt, fair gegenüber Renés Rechner) — die Codecs
    # holt detail() je Titel einzeln nach und cacht sie.
    felder = ("Genres,ProviderIds,ProductionYear,OfficialRating,"
              "CommunityRating,RunTimeTicks,DateCreated")
    eintraege, start, gesamt = [], 0, None
    neu_angemeldet = False
    while gesamt is None or start < gesamt:
        try:
            st, roh = _http(f"{z['url']}/Users/{s['user_id']}/Items?Recursive=true"
                            f"&IncludeItemTypes=Movie,Series&Fields={felder}"
                            f"&StartIndex={start}&Limit=1000",
                            kopf={"X-Emby-Token": s["token"]}, timeout=180)
        except Exception as e:             # noqa: BLE001
            _fehlversuch_ts = time.time()
            return {"ok": False, "anzahl": 0, "fehler": f"Items-Abruf: {e}"}
        if st == 401 and not neu_angemeldet:
            # Token von einer zweiten Sitzung invalidiert (gleiche DeviceId,
            # live gefunden 05.08.) ⇒ EINMAL frisch anmelden, Seite wiederholen.
            neu_angemeldet = True
            _sitzung.clear()
            s = _anmelden()
            if s:
                continue
            _fehlversuch_ts = time.time()
            return {"ok": False, "anzahl": 0, "fehler": "Anmeldung fehlgeschlagen."}
        if st != 200:
            _fehlversuch_ts = time.time()
            return {"ok": False, "anzahl": 0, "fehler": f"Items-Abruf HTTP {st}"}
        d = json.loads(roh)
        seite = d.get("Items") or []
        if not seite:
            break
        eintraege.extend(_eintrag(it) for it in seite)
        gesamt = d.get("TotalRecordCount") or len(seite)
        start += 1000
    fam.json_schreiben(_pfade["katalog"], {
        "stand": time.time(), "server_version": s.get("version") or "?",
        "eintraege": eintraege})
    _fehlversuch_ts = 0.0                  # Erfolg löst den Backoff
    fortschritt_nachreichen()              # liegengebliebene Meldungen mitnehmen
    return {"ok": True, "anzahl": len(eintraege), "fehler": ""}


def katalog_lesen():
    try:
        with open(_pfade["katalog"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"stand": 0, "server_version": "?", "eintraege": []}


def sync_faellig(alter_s=6 * 3600):
    """Fällig nach 6 h — aber NIE direkt nach einem Fehlschlag: sonst hämmert
    der 5-s-Ticker bei totem/langsamem Server in Dauerschleife auf Renés
    Rechner ein (live fast passiert am 05.08. — Timeout-Lauf und der Ticker
    stieß sofort den nächsten an). Backoff = Selbstheilungs-Regel."""
    if time.time() - _fehlversuch_ts < FEHL_BACKOFF_S:
        return False
    return (time.time() - (katalog_lesen().get("stand") or 0)) >= alter_s


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
    s = _anmelden()
    z = _zugang()
    if not (s and z):
        return None
    try:
        st, roh = _http(f"{z['url']}/Items/{sauber}/Images/{art}",
                        kopf={"X-Emby-Token": s["token"]})
        if st == 401:                      # Token invalidiert ⇒ einmal frisch
            _sitzung.clear()
            s = _anmelden()
            if not s:
                return None
            st, roh = _http(f"{z['url']}/Items/{sauber}/Images/{art}",
                            kopf={"X-Emby-Token": s["token"]})
    except Exception:                      # noqa: BLE001 — Netzfehler: NICHT
        return None                        # negativ cachen, nächster Versuch frei
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
    (Selbstheilungs-Regel)."""
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
    if not m or "trailer_v2" not in m or time.time() - (m.get("ts") or 0) > META_HALTBAR_S:
        m = {"ts": time.time(), "beschreibung": "", "cast": [],
             "empfehlungen_tmdb": [], "imdb_rating": "", "metacritic": "",
             "tomatometer": "", "tagline": "", "regie": [], "drehbuch": [],
             "trailer": [], "trailer_v2": True, "hoehe": 0, "audio_kanaele": 0,
             "audio_sprachen": [], "sub_sprachen": []}
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
            except Exception:              # noqa: BLE001 — Reihe kommt ohne TMDB
                pass
        if keys.get("omdb") and e.get("imdb") and _omdb_erlaubt(cache):
            try:
                st, roh = _http(f"https://www.omdbapi.com/?i={e['imdb']}"
                                f"&apikey={keys['omdb']}")
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
                    cache["omdb_zaehler"] = (cache.get("omdb_zaehler") or 0) + 1
            except Exception:              # noqa: BLE001 — Zahl fehlt dann eben
                pass
        # Technik kommt seit dem Seiten-Abzug nicht mehr im Spiegel mit
        # (teuerstes Feld, live gemessen — s. katalog_abzug): je Titel EIN
        # Einzel-Abruf: Codecs, Auflösung, Ton-Kanäle/-Sprachen, Untertitel-
        # Sprachen (Netflix-Detailseite: Qualität · Sound · Untertitel).
        m["video_codec"] = e.get("video_codec") or ""
        m["audio_codec"] = e.get("audio_codec") or ""
        s = _anmelden()
        z = _zugang()
        if s and z:
            try:
                st, roh = _http(f"{z['url']}/Users/{s['user_id']}/Items/{item_id}",
                                kopf={"X-Emby-Token": s["token"]})
                if st == 200:
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
        # Schlüssel ein, statt fremde frische Einträge zu überschreiben.
        fam.json_aendern(_pfade["meta"],
                         lambda d: d.__setitem__(item_id, m), standard={})
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
    Gesehen-Stand soll frisch sein."""
    s = _anmelden()
    z = _zugang()
    if not (s and z):
        return []
    sauber = re.sub(r"[^A-Za-z0-9]", "", serien_id or "")
    if not sauber:
        return []
    url = (f"{z['url']}/Shows/{sauber}/Episodes?userId={s['user_id']}"
           f"&Fields=RunTimeTicks")
    try:
        st, roh = _http(url, kopf={"X-Emby-Token": s["token"]}, timeout=30)
        if st == 401:                      # Token invalidiert ⇒ einmal frisch
            _sitzung.clear()
            s = _anmelden()
            if not s:
                return []
            st, roh = _http(url, kopf={"X-Emby-Token": s["token"]}, timeout=30)
    except Exception:                      # noqa: BLE001 — Ausfall = leere Liste
        return []
    if st != 200:
        return []
    out = []
    for it in json.loads(roh).get("Items") or []:
        ud = it.get("UserData") or {}
        ticks = it.get("RunTimeTicks") or 0
        out.append({"id": it.get("Id") or "", "titel": it.get("Name") or "",
                    "staffel": it.get("ParentIndexNumber") or 0,
                    "folge": it.get("IndexNumber") or 0,
                    "laufzeit_min": round(ticks / 600_000_000) if ticks else None,
                    "position_s": round((ud.get("PlaybackPositionTicks") or 0) / 10_000_000),
                    "gesehen": bool(ud.get("Played"))})
    out.sort(key=lambda e: (e["staffel"], e["folge"]))
    return out


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

    if fam.json_aendern(_pfade["merk"], _kippen, standard={}) is None:
        return item_id in (d.get(profil) or [])   # Sperre besetzt: Stand bleibt
    return ergebnis.get("an", False)


# ---------------------------------------------------------------- Reihen

def reihen(profil="standard"):
    """Home-Reihen rein aus dem Spiegel — kein Netz, damit die Anzeige auch
    bei Renés Ausfall steht (Spec „Ausfall-Verhalten")."""
    alle = katalog_lesen()["eintraege"]
    weiter = [e for e in alle if e["position_s"] > 0 and not e["gesehen"]]
    # Top als BAYES-SCORE (JB-Go): Jellyfin hat keinen Vote-Count, darum
    # holen wir TMDB-Stimmen für die Roh-Kandidaten (einmalig gecacht, max 8
    # neue Abrufe je Lauf — Top wird über wenige Aufrufe komplett geeicht).
    # score = v/(v+m)*R + m/(v+m)*C  (m=500 Prior-Stimmen, C=6.8 Prior-Note);
    # ohne Stimmen kommt keiner über den Prior — Ein-Stimmen-★10 sind tot.
    cache = _meta_cache()
    stimmen = cache.get("tmdb_stimmen") or {}
    keys = _meta_keys()
    # 120 Kandidaten, damit nach dem Filme/Serien-Filter der Tabs (JB 06.08.:
    # „Filme und Serien sind ihren eigenen tabs eigen zu listen") je Seite
    # noch 10 übrig bleiben; geeicht wird weiter mit 8 Abrufen je Lauf.
    kand = sorted((e for e in alle if e.get("rating") and not e["gesehen"]),
                  key=lambda e: e["rating"], reverse=True)[:120]
    neu = 0
    for e in kand:
        t = e.get("tmdb")
        if not t or t in stimmen or not keys.get("tmdb") or neu >= 8:
            continue
        art = "tv" if e["typ"] == "serie" else "movie"
        try:
            st, roh = _http(f"https://api.themoviedb.org/3/{art}/{t}"
                            f"?api_key={keys['tmdb']}")
            if st == 200:
                d2 = json.loads(roh)
                stimmen[t] = [d2.get("vote_count") or 0, d2.get("vote_average") or 0]
                neu += 1
        except Exception:                  # noqa: BLE001 — nächster Lauf holt nach
            pass
    if neu:
        def _mischen(d):
            alt = d.get("tmdb_stimmen") or {}
            alt.update(stimmen)
            d["tmdb_stimmen"] = alt
        fam.json_aendern(_pfade["meta"], _mischen, standard={})

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
        fam.json_aendern(_pfade["meta"], _mischen, standard={})
    return out


# ---------------------------------------------------------------- Abspielen

def stream_url(item_id):
    """Direct-Play-URL für den LOKALEN VLC (Token in der URL ist ok, weil sie
    diesen PC nie verlässt — Clients bekommen sie NICHT)."""
    s = _anmelden()
    z = _zugang()
    if not (s and z):
        return None
    return f"{z['url']}/Videos/{item_id}/stream?static=true&api_key={s['token']}"


def _queue_lesen():
    try:
        with open(_pfade["queue"], encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _fortschritt_senden(item_id, position_s, gesehen):
    s = _anmelden()
    z = _zugang()
    if not (s and z):
        return False
    try:
        st, _ = _http(z["url"] + "/Sessions/Playing/Progress",
                      daten={"ItemId": item_id,
                             "PositionTicks": int(position_s) * 10_000_000,
                             "IsPaused": False},
                      kopf={"X-Emby-Token": s["token"]})
        if st == 401:
            # Live gefunden (05.08.): Jellyfin wirft das alte Token weg, sobald
            # sich dieselbe DeviceId neu anmeldet (z. B. eine zweite Sitzung).
            # Selbstheilung: EINMAL frisch anmelden und wiederholen.
            _sitzung.clear()
            s = _anmelden()
            if not s:
                return False
            st, _ = _http(z["url"] + "/Sessions/Playing/Progress",
                          daten={"ItemId": item_id,
                                 "PositionTicks": int(position_s) * 10_000_000,
                                 "IsPaused": False},
                          kopf={"X-Emby-Token": s["token"]})
    except Exception:                      # noqa: BLE001 — Netz weg ⇒ Queue
        return False
    if gesehen and st in (200, 204):
        try:
            _http(f"{z['url']}/Users/{s['user_id']}/PlayedItems/{item_id}",
                  daten={}, kopf={"X-Emby-Token": s["token"]})
        except Exception:                  # noqa: BLE001 — Position zaehlt schon
            pass
    return st in (200, 204)


def fortschritt(item_id, position_s, gesehen=False):
    """Fortschritt an Jellyfin melden; scheitert es, wandert die Meldung in die
    Queue und geht beim nächsten Erfolg/Abzug nach (nichts geht verloren)."""
    if _fortschritt_senden(item_id, position_s, gesehen):
        return True
    neu = {"item": item_id, "position_s": int(position_s),
           "gesehen": bool(gesehen), "ts": time.time()}
    fam.json_aendern(_pfade["queue"], lambda q: (q or []) + [neu], standard=[])
    return False


def _q_schluessel(m):
    return (m.get("item"), int(m.get("position_s") or 0), bool(m.get("gesehen")),
            round(float(m.get("ts") or 0), 3))


def fortschritt_nachreichen():
    """Liegengebliebene Meldungen senden; bei erneutem Fehlschlag bleibt der
    Rest liegen. Gibt die Zahl der erfolgreich nachgereichten zurück.

    Lesen — Senden — GEZIELT entfernen, statt die ganze Datei zurückzuschreiben:
    Der alte Weg las die Warteschlange, sendete (dauert), und schrieb dann den
    Rest über den inzwischen aktuellen Stand. Wer in diesen Sekunden einen Film
    stoppte, verlor seinen Spot spurlos (gemessen 13.08.2026 — genau während des
    6-h-Abzugs, der ja mit `fortschritt_nachreichen()` endet).

    Bewusste Richtung: Im Zweifel lieber doppelt melden als verlieren. Einen
    Fortschritt zu setzen ist idempotent — ihn zu verlieren nicht."""
    q = _queue_lesen()
    geschafft, erledigt = 0, []
    for m in q:
        if not _fortschritt_senden(m["item"], m["position_s"], m.get("gesehen")):
            break                          # Reihenfolge halten: Rest bleibt liegen
        geschafft += 1
        erledigt.append(_q_schluessel(m))
    if erledigt:
        weg = set(erledigt)
        fam.json_aendern(
            _pfade["queue"],
            lambda liste: [m for m in (liste or []) if _q_schluessel(m) not in weg],
            standard=[])
    return geschafft
