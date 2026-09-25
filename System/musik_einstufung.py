# -*- coding: utf-8 -*-
"""Musik-Einstufung und Titel-Helfer (Gesamtprüfung Y3, 25.09.2026).

Ist ein Titel ein Lied (`_ist_musik`, `_musik_grad`, `_musik_grade` mit dem
Kanal als Beleg), welche Kategorie verrät der Dateiname (`_kat_aus_name`),
das wievielte Video seines Kanals ist er (`_kanal_nummern`), welche Künstler
und Titel stecken im YouTube-Titel (`_tag_kandidat`, `_titel_blank`,
`_titel_kern`, `_ist_live_titel`, `_titel_aus_name`), dazu die
Datei-Endungen. Alles rein aus den Daten eines Eintrags, ohne Netz, Datei und
Zustand, bis auf die Zeile wortgleich aus youtube_app.py hierher verschoben.

Einbahn wie bei filme und geo: dieses Modul importiert youtube_app nie. Die
App ruft `musik_einstufung.X`; `youtube_app.X` bleibt als Verweis erreichbar
(Tests, Werkzeuge). Ein Test, der etwas davon ersetzt, ersetzt es HIER
(`monkeypatch.setattr(musik_einstufung, ...)`): ein Ersatz an
`youtube_app.X` träfe keinen Aufrufer. Das prüft tests/test_struktur_module.py.
"""
import re

# Datei-Endungen, jede Fassung EINMAL (Gesamtprüfung Y3). Vorher standen die
# Audio-Endungen an fünf Stellen in drei Fassungen. Ob `.wav` und `.aac`
# überall als Audio gelten, ist JB-Frage 7 (Zähler und Auto-Tag änderten sich);
# bis zur Antwort bleibt jede Fassung, wie sie war (Proben:
# tests/test_doppelungen.py::test_audio_endungen_ergebnis_bleibt_gleich).
AUDIO_EXT = (".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav", ".aac")
VIDEO_EXT = (".mp4", ".mkv", ".webm", ".mov", ".avi")
AUDIO_EXT_OHNE_AAC = (".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav")   # Kategorie aus dem Namen
AUDIO_EXT_OHNE_WAV_AAC = (".mp3", ".m4a", ".opus", ".ogg", ".flac")      # Musik-Einstufung, Zähler
MUSIKVIDEO_EXT = (".mp4", ".mkv", ".webm")                               # Videos, die ein Lied sein können


def _titel_aus_name(name):
    t = re.sub(r"\.[^.]+$", "", name or "")          # Endung weg
    t = re.sub(r"\s*\[[\w-]{6,}\]\s*$", "", t)        # [videoid] weg
    return t.strip() or (name or "")


def _kat_aus_name(name):
    n = (name or "").lower()
    return "MP3" if n.endswith(AUDIO_EXT_OHNE_AAC) else "Video"


def _kanal_nummern(eintraege):
    """„Das wievielte Video dieses Kanals ist das?" (JB Punkt 4)

    Ausdrücklich NICHT die Track-Nummer: die heißt „Position innerhalb eines
    Werks" und stünde bei Einzelvideos 500-mal auf 1 — genau JBs Sorge.
    Vorbild ist `abo_nr`, das es für Abo-Folgen schon gibt; dieselbe Zählweise
    (ältestes = 1), nur für JEDEN Kanal statt nur für abonnierte.

    ABGELEITET statt gespeichert: eine einmal geschriebene Nummer würde falsch,
    sobald ein ÄLTERES Video desselben Kanals dazukommt — und falsche Zahlen
    wandern beim Kopieren mit. Ohne Kanal gibt es keine Nummer; lieber keine
    Angabe als eine erfundene.
    """
    nach_kanal = {}
    for x in eintraege:
        kanal = (x.get("uploader") or "").strip().lower()
        if kanal:
            nach_kanal.setdefault(kanal, []).append(x)
    nummer, gesamt = {}, {}
    for liste in nach_kanal.values():
        # Ältestes zuerst; ohne Upload-Datum entscheidet der Ladezeitpunkt,
        # damit die Reihenfolge stabil bleibt statt zufällig zu springen.
        liste.sort(key=lambda x: (x.get("upload_date") or "", x.get("ts") or 0))
        for i, x in enumerate(liste, 1):
            nummer[x["id"]] = i
            gesamt[x["id"]] = len(liste)
    return nummer, gesamt


# Müll-Klammern aus YouTube-Titeln: [Official Video], (Lyrics), [4K Upgrade] …
_TITEL_MUELL = re.compile(
    r"(?i)[\(\[](official|video|audio|lyric|lyrics|hd|hq|4k|8k|remaster|visualizer"
    r"|mv|m/v|full album|live|explicit|clean)[^\)\]]*[\)\]]")


def _tag_kandidat(e):
    """Aus YouTube-Titel + Kanal einen (kuenstler, titel)-Kandidaten raten.
    'Green Day - Boulevard … [Official Video]' -> ('Green Day', 'Boulevard …')."""
    t = _TITEL_MUELL.sub(" ", e.get("titel") or "")
    t = re.sub(r"\s+", " ", t).strip(" -–—|")
    ku = ""
    for sep in (" - ", " – ", " — ", ": "):
        if sep in t:
            ku, t = t.split(sep, 1)
            break
    if not ku:                                        # kein 'Künstler - Titel' -> Kanalname säubern
        ku = re.sub(r"(?i)\s*-\s*topic$|vevo$", "", e.get("uploader") or "").strip()
    return ku.strip(), t.strip(" -–—|")


def _titel_blank(t):
    """Titel für einen ZWEITEN Suchversuch von allen Klammer-Zusätzen befreien.

    Build 136 (JB-Frage „wieso sind mehrere Titel noch nicht korrekt
    benannt?"): _TITEL_MUELL kennt nur BEKANNTE Zusätze (official, lyrics,
    live …). Alles andere bleibt stehen und lässt die MusicBrainz-Suche ins
    Leere laufen — in JBs Bibliothek etwa „(Traduzione Italiana)" oder
    „(from The Wildlife Concert)". Für die Suche ist ein Klammerzusatz fast
    nie Teil des echten Titels; und wenn doch, findet MusicBrainz ihn auch
    ohne. Bleibt nichts übrig, wird der Originaltitel behalten — ein leerer
    Suchbegriff wäre nutzlos.
    """
    roh = (t or "").strip()
    ohne = re.sub(r"[\(\[][^\)\]]*[\)\]]", " ", roh)
    ohne = re.sub(r"\s+", " ", ohne).strip(" -–—|,")
    return ohne or roh


_ANHAENGSEL = re.compile(
    r"\s*[-–—|]\s*(official([ \w]*)?|music video|lyric(s| video)?|audio|video|"
    r"hd|4k( hd)?|remaster(ed)?( \d{4})?|visuali[sz]er)\s*$", re.IGNORECASE)


def _titel_kern(t):
    """Klammer-Zusätze UND bekannte Bindestrich-Anhängsel abstreifen (JB-Fund
    05.08.: „Running Up That Hill - Official Music Video" fand nichts, weil
    das Anhängsel keine Klammer ist). Mehrfach, bis nichts mehr passt."""
    t = _titel_blank(t)
    for _ in range(3):
        neu = _ANHAENGSEL.sub("", t).strip(" -–—|,")
        if neu == t or not neu:
            break
        t = neu
    return t


def _ist_live_titel(t):
    """Sagt der QUELL-Titel selbst, dass es eine Live-Aufnahme ist? (JB 05.08.,
    Nirvana-Fall: „Live On MTV Unplugged" — dann ist das offizielle LIVE-Album
    die richtige Quelle, nicht das Studio-Album.) Wortgrenzen, damit „Alive"
    oder „Delivery" nicht zünden."""
    return bool(re.search(r"\b(live|unplugged|konzert|concert|acoustic session)\b",
                          (t or "").casefold()))


def _ist_musik(e):
    """Ist das ein Musiktitel? (Build 140 — JB: „Es sind zwar Videos, aber es
    sind Videos von Liedern. Ich finde da sollte es so gelten.")

    Vorher zählte nur das Dateiformat, also lief das Auto-Tagging für
    Musikvideos nie. Jetzt gelten zusätzlich zwei Merkmale, an denen man ein
    Musikvideo zuverlässig erkennt:
      · der Kanal ist ein VEVO- oder „… - Topic"-Kanal (die legt YouTube
        selbst für Labels bzw. automatisch für Musik an),
      · der Name folgt dem Muster „Künstler - Titel".
    Bewusst NICHT jedes Video: sonst befragt die App MusicBrainz zu jedem
    Let's Play und bekommt Zufallstreffer statt Daten.
    """
    n = (e.get("name") or "").lower()
    if e.get("kategorie") == "MP3" or n.endswith(AUDIO_EXT_OHNE_WAV_AAC):
        return True
    if not n.endswith(MUSIKVIDEO_EXT):
        return False
    up = (e.get("uploader") or "").strip().lower()
    if up.endswith("- topic") or up.endswith("vevo"):
        return True
    # „Künstler - Titel": ein Bindestrich mit Leerzeichen, und beide Seiten
    # tragen Text (die Regel steht einmal, in _ist_musik_muster).
    return _ist_musik_muster(e)


# Build 144h (JB Punkt 5): „der Video- und Song-Modus soll wirklich Lieder
# nehmen, nicht nur Videos und MP3."
# Wörter, die ein Werk als NICHT-Lied ausweisen. Bewusst kurz und auf das
# beschränkt, was in JBs Bibliothek und bei YouTube üblich ist — eine lange
# Wortliste wäre Pflegearbeit und träfe irgendwann echte Liedtitel.
_KEIN_LIED = re.compile(
    r"(?i)\b(?:trailer|teaser|gameplay|let'?s\s*play|walkthrough|review|tutorial"
    r"|podcast|interview|documentary|dokumentation|short\s*film|kurzfilm"
    r"|full\s*(?:movie|album|episode)|folge\s*\d+|stream\s*highlights?)\b")
# Länger als das ist kein einzelnes Lied mehr, sondern Mitschnitt, Hörbuch,
# Podcast oder ein ganzes Album am Stück. 20 Minuten ist großzügig gewählt —
# das längste Stück in JBs Bibliothek liegt weit darunter (gemessen: genau
# ein Titel über 20 min, und der ist keiner).
_LIED_MAXDAUER = 1200


def _musik_grad(e):
    """Wie sicher ist es ein LIED? „belegt" / „wahrscheinlich" / „nein".

    Warum drei Stufen statt ja/nein: An JBs 86 Titeln gemessen haben nur 11
    einen MusicBrainz-Treffer (kuenstler+track) und 3 einen VEVO-/„- Topic"-
    Kanal. Ein Filter, der nur Belegtes zeigt, wäre fast leer; einer, der jede
    Vermutung mitnimmt, holt Animationsfilme und Gaming-Clips herein. Also
    beides trennen und die Oberfläche sagen lassen, worauf sie sich stützt.

    Ausdrücklich NICHT mehr: „Audiodatei = Musik". Das war eine Setzung, keine
    Messung — Comedy, Podcasts und Hörbücher liegen genauso als MP3 vor
    (in JBs Bibliothek z. B. ein Gaming-Clip und ein Louis-C.K.-Mitschnitt).
    """
    kuenstler = (e.get("kuenstler") or "").strip()
    track = (e.get("track") or "").strip()
    up = (e.get("uploader") or "").strip().lower()
    if (kuenstler and track) or up.endswith(("- topic", "vevo")):
        return "belegt"                      # Beleg schlägt jede Heuristik
    name = e.get("name") or ""
    if _KEIN_LIED.search(name) or _KEIN_LIED.search(e.get("titel_orig") or ""):
        return "nein"
    if (e.get("dauer") or 0) > _LIED_MAXDAUER:
        return "nein"
    # Abwägung, an JBs Bibliothek gemessen und danach korrigiert: Ein Filter
    # ist eine ANSICHT, er schreibt nichts. Ein Titel zu viel ist ein
    # Schönheitsfehler — ein fehlendes Lied fällt auf und ärgert. Die erste,
    # strengere Fassung verlangte auch von Audiodateien das Muster
    # „Künstler - Titel" und verlor damit drei echte Lieder (Elmer Bernstein,
    # Mateus Asato, Shania Twain). Also: eine Audiodatei ohne Ausschlussgrund
    # zählt als wahrscheinlich; bei Videos braucht es weiter ein Indiz.
    n = (e.get("name") or "").lower()
    if e.get("kategorie") == "MP3" or n.endswith(AUDIO_EXT_OHNE_WAV_AAC):
        return "wahrscheinlich"
    if _ist_musik_muster(e):
        return "wahrscheinlich"
    return "nein"


def _musik_grade(eintraege):
    """Einstufung für eine ganze Liste — mit dem Kanal als zusätzlichem Beleg.

    Nötig, weil `_musik_grad` je Eintrag urteilt und dabei genau die Lieder
    verliert, deren Dateiname keinen Künstler trägt. An JBs Bibliothek
    gemessen fielen so acht echte Lieder heraus („The Boxer", „Rocky Mountain
    High", „Sunshine on My Shoulders" …) — sie stehen als reiner Titel da.

    Der Kanal weiß es aber: Trägt von demselben Uploader mindestens EIN Titel
    einen Beleg (MusicBrainz-Treffer, VEVO-/„- Topic"-Kanal) ODER das Muster
    „Künstler - Titel", dann ist das ein Musik-Kanal, und seine übrigen Titel
    sind wahrscheinlich Lieder. Genau das rettet „The Boxer" über „Simon &
    Garfunkel - I Am A Rock" und „Rocky Mountain High" über „John Denver -
    Leaving on a Jet Plane".

    Der Auslöser ist bewusst NICHT „hat irgendeinen wahrscheinlichen Titel":
    dann würde eine einzige MP3 einen Gaming-Kanal zum Musik-Kanal machen
    (gemessen an „Asmongold Clips", dessen MP3 kein Künstler-Muster trägt).
    """
    grade = {}
    musik_kanaele = set()
    for k, e in eintraege.items() if isinstance(eintraege, dict) else eintraege:
        g = _musik_grad(e)
        grade[k] = g
        up = (e.get("uploader") or "").strip().lower()
        if up and (g == "belegt" or (g != "nein" and _ist_musik_muster(e))):
            musik_kanaele.add(up)
    if musik_kanaele:
        paare = eintraege.items() if isinstance(eintraege, dict) else eintraege
        for k, e in paare:
            if grade.get(k) != "nein":
                continue
            up = (e.get("uploader") or "").strip().lower()
            if up not in musik_kanaele:
                continue
            # Ausschlussgründe bleiben Ausschlussgründe — ein Trailer auf
            # einem Musik-Kanal ist trotzdem kein Lied.
            if _KEIN_LIED.search(e.get("name") or "") or _KEIN_LIED.search(e.get("titel_orig") or ""):
                continue
            if (e.get("dauer") or 0) > _LIED_MAXDAUER:
                continue
            grade[k] = "wahrscheinlich"
    return grade


def _ist_musik_muster(e):
    """Nur das Namensmuster „Künstler - Titel" (ohne Format-Annahme): ein
    Bindestrich mit Leerzeichen, links 2 bis 40 Zeichen, rechts mindestens 2.
    Die EINE Fassung der Regel, auch für _ist_musik (Gesamtprüfung Gruppe 7)."""
    stamm = re.sub(r"\.[a-z0-9]{2,4}$", "", e.get("name") or "")
    teile = re.split(r"\s+[-–—]\s+", stamm, maxsplit=1)
    return (len(teile) == 2 and 2 <= len(teile[0].strip()) <= 40
            and len(teile[1].strip()) >= 2)
