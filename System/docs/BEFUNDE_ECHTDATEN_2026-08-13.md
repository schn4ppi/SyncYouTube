# Befunde — Film-Kette gegen echte Daten (13.08.2026)

Renes Jellyfin war vom 06.08. bis 13.08. mit HTTP 403 gesperrt. Nach dem Wegfall der
Sperre lief der erste erfolgreiche Katalog-Abzug: **4885 Eintraege** (3967 Filme,
918 Serien), Jellyfin 10.11.11. Damit lief die Kette zum ersten Mal gegen echte
Daten — vorher nur gegen Attrappen mit wenigen Eintraegen.

Geprueft von 8 Messern (je ein Kettenglied); jeder schwere Befund wurde von einem
zweiten Agenten adversarisch nachgemessen, der ihn zu WIDERLEGEN versuchte. Nur was
die Widerlegung ueberlebt hat, steht hier. 34 Agenten, 0 Ausfaelle.

## Bestaetigt: 23 Befunde

### 1. [SCHWER] Genre-Reihen sind ein ALPHABET-Schnitt, keine Auswahl — JB sieht in keiner Reihe etwas jenseits von "B"

**Stelle:** `SyncYouTube/System/filme.py:557`

**Beleg:** genres[g] = [e for e in alle if g in e["genres"]][:100] — es gibt KEIN sort davor, also gilt die Katalog-Reihenfolge, und die ist Jellyfins SortName (alphabetisch, gemessen: erste 5 Titel '#Zeitgeist','00 Schneider - Im…','00 Schneider - Jag…','2 Fast 2 Furious','2 Guns', letzte 5 '…Zwei sind nicht zu…','Zwei Weihnachtsmän…','Zwei wie Pech und…','Zwielicht','Zwischen allen Lin…'). Gemessene Reihen-Spannen: 'Action' geht von '2 Fast 2 Furious' bis 'Bee and PuppyCat' (Katalog endet bei 'Zwei wie Pech und Schwefel', 1170 Titel) · 'Drama' von '#Zeitgeist' bis 'American History X' (Katalog endet bei 'Zwischen allen Linien', 2347 Titel) · 'Thriller' bis 'Betonrausch' (1151) · 'Comedy' bis 'Blast - Wo die Büffel röhren' (938) · 'Science Fiction' bis 'Chronopolis' (705) · 'Horror' bis 'Der kleine Horrorladen' (417). Ueber alle 50 Reihen zusammen erreichen nur 1933 verschiedene Titel von 4885 (40 %) ueberhaupt eine Reihe.

**Wirkung auf JB:** JB blaettert eine Action-Reihe durch und findet Filme mit Zahlen und A/B im Titel — Interstellar, Matrix, Terminator kommen in KEINER Genre-Reihe vor. Mit einer 3-Eintrag-Attrappe nimmt [:100] alles und die fehlende Sortierung faellt nie auf; erst 1170 Action-Titel machen den Schnitt sichtbar. Das ist dieselbe Familie wie JBs Frage 'Wo sind eigentlich die restlichen Filme von René?'.

**Urteil des Skeptikers:** BESTAETIGT — nicht widerlegbar, reproduziert exakt und wurde in der Gegenprobe schaerfer.

MESSUNGEN (alle mit ../../SyncDashTray/System/venv/Scripts/python.exe -X utf8, gegen die echten 4885 Eintraege):

1) Katalog-Reihenfolge ist alphabetisch (SortName). filme.py:171 ruft /Items OHNE SortBy-Parameter, Jellyfin liefert also SortName aufsteigend. Gemessen erste Titel: '#Zeitgeist', '00 Schneider - Im Wendekreis der Eidechse', '00 Schneider - Jagd auf Nihil Baxter', '2 Fast 2 Furious', '2 Guns' — letzte: 'Zwei sind nicht zu bremsen', 'Zwei Weihnachtsmaenner', 'Zwei wie Pech und Schwefel', 'Zwielicht', 'Zwischen allen Linien'. Deckt sich 1:1 mit dem Beleg des Pruefers.

2) Der ECHTE filme.reihen()-Lauf (filme.einrichten(abspath('.')), _meta_keys -> {} und _http auf AssertionError gepatcht, also garantiert netzfrei; 0,03 s, 1,27 MB Antwort) liefert 50 Reihen a 100 Kacheln. Spannen exakt wie behauptet: Action '2 Fast 2 Furious' -> 'Bee and PuppyCat' (von 1170), Drama '#Zeitgeist' -> 'American History X' (von 2347), Thriller -> 'Betonrausch' (1151), Comedy -> 'Blast - Wo die Bueffel roehren' (938), Science Fiction -> 'Chronopolis' (705), Horror -> 'Der kleine Horrorladen' (417). Abdeckung ueber alle 50 Reihen: 1933 von 4885 verschiedenen Titeln = 39,6 % (Pruefer sagte 40 %).

3) STAERKSTER BELEG — Anfangsbuchstaben-Verteilung der Action-Reihe gegen Action gesamt:
   Reihe (100):   1:4 2:9 3:3 4:2 8:1 9:2 A:47 B:26 T:5 AE:1
   Gesamt (1170): ... A:52 B:69 C:41 D:145 E:24 F:34 G:42 H:38 I:32 J:52 K:42 L:30 M:72 N:21 O:22 P:39 Q:2 R:54 S:113 T:127 U:15 V:23 W:27 X:12 Y:5 Z:12 ...
   C bis Z fehlen vollstaendig. Das ist ein Schnitt, kein Deckel.

4) KEIN Client-Rettungsanker: beide Frontend-Pfade rendern die Server-Liste woertlich, ohne sort/shuffle — oberflaeche.py:3858 (Object.entries(d.genres||{})) und oberflaeche.py:7809 (genresAls mappt + filtert nach Typ). Der Schnitt passiert serverseitig; kein Client koennte die 2952 fehlenden Titel zurueckholen.

5) Blindstelle der Attrappe bestaetigt: tests/test_filme.py:17 FAKE_ITEMS hat 2 Eintraege (nicht mal 3), je ein Genre. Bei [:100] schneidet nichts — die fehlende Sortierung KANN dort nie auffallen.

6) Namentliche Gegenprobe: Interstellar (Abenteuer/Drama/Science Fiction), Matrix, Matrix Reloaded, Terminator, Terminator 2, Inception, Titanic, Fight Club, Pulp Fiction — alle in KEINER Genre-Reihe. Zusatzfund: von 556 Titeln mit Bewertung >= 8,0 erscheinen 255 (46 %) in keiner einzigen Reihe.

ZWEI PRAEZISIERUNGEN AN DER FORMULIERUNG (Substanz bleibt, Ueberschrift leicht ueberzogen):
- "JB sieht in keiner Reihe etwas jenseits von B" stimmt nicht buchstaeblich. Kleinere Genres reichen bis D (Horror -> 'Der kleine Horrorladen', Adventure -> 'Der Graf von Monte Christo', Abenteuer -> 'Die Hoellenfahrt der Poseidon'), und 'The ...'-Titel tauchen auf, weil Jellyfins SortName den Artikel abstreift ('The 6th Day' sortiert unter "6"). Korrekt: je groesser das Genre, desto frueher endet die Reihe — bei Drama (2347) schon bei "Am...".
- "Interstellar unauffindbar" waere falsch: oberflaeche.py:7824 baut auf den Tabs Filme/Serien ein "Alle von A bis Z"-Raster aus dem VOLLEN Katalog (tvKatalogLaden -> /api/filme/katalog). Richtig ist die engere Aussage: in keiner GENRE-REIHE vorhanden.

SCHWERE: bleibt "schwer". Die Genre-Reihen sind die Kernflaeche des Fernsehmodus und als Auswahlmechanismus strukturell funktionslos (60 % des Katalogs unsichtbar, 46 % der gut bewerteten Titel fehlen). Aber nichts stuerzt ab, nichts geht verloren, Renes Server bleibt unberuehrt, und der A-Z-Weg traegt als Rueckfallebene — deshalb kein Blocker.

STELLE bestaetigt: SyncYouTube/System/filme.py:557 — genres[g] = [e for e in alle if g in e["genres"]][:100], kein sort davor. Fix waere ein Einzeiler (sortieren vor dem Schnitt, z. B. nach rating/hinzugefuegt, oder deterministisch mischen). Ich habe KEINEN Code geaendert, keine schreibenden Rufe ausgefuehrt und ausser dem bereits vorliegenden Katalog keine Netzabrufe gegen Renes Server gemacht.

### 2. [SCHWER] Der 100er-Deckel greift VOR dem Typ-Filter des Clients — Serien-Tab zeigt 7 von 41 Horror-Serien

**Stelle:** `SyncYouTube/System/filme.py:557`

**Beleg:** Server deckelt je Genre auf 100 ueber den GEMISCHTEN Katalog; der Client filtert erst danach auf seine Art (oberflaeche.py:7808 genresAls / :7822 kopf = …concat(genresAls(filt,99))). Gemessen: 'Action' Reihe(100) enthaelt 83 Filme + 17 Serien — der Filme-Tab zeigt also 83 von 1027 Action-Filmen. 'Horror' Reihe(100) = 93 Filme + 7 Serien — der Serien-Tab zeigt 7 von 41 Horror-Serien. 'Thriller' 84F/16S bei 1018F/133S im Katalog. 'Drama' 78F/22S bei 1808F/539S. Folge: Filme-Tab 8 Genre-Reihen fallen ganz weg (Sci-Fi & Fantasy, Action & Adventure, Mini-Series, Kids, Game Show, War & Politics, Soap, Travel), 11 weitere zeigen 1-9 Kacheln; Serien-Tab 12 fallen weg (Abenteuer, Liebesfilm, Historie, TV-Film, Kriegsfilm, Musik, Sci-Fi, Biography, Science-Fiction, Erotik, Indie, Talk Show), 10 weitere zeigen 1-9.

**Wirkung auf JB:** Genau JBs Beschwerde vom 07.08. in der Genre-Variante: eine Reihe mit 4-7 Kacheln, obwohl der Server ein Vielfaches hat. Bei 3 Attrappen-Eintraegen ist der Typ-Filter folgenlos, bei 4885 halbiert er jede Reihe.

**Urteil des Skeptikers:** REPRODUZIERT, nicht widerlegbar. Aufruf: filme.reihen("standard") mit monkeypatchtem _http (kein Netz, kein Cache-Schreiben) gegen den echten Katalog (4885 / 3967 Filme / 918 Serien). Gemessene Ausgabe deckt sich exakt mit dem Prueferbeleg: Horror Reihe(100) = 93 Filme + 7 Serien bei 376F/41S im Katalog; Action 83F/17S bei 1027F/143S; Thriller 84F/16S bei 1018F/133S; Drama 78F/22S bei 1808F/539S. Wirkweg im Code eindeutig und einmalig: filme.py:557 schneidet [e for e in alle if g in e["genres"]][:100] ueber die GEMISCHTE Liste (grep findet [:100] genau einmal), youtube_app.py:5387 reicht unveraendert durch, erst oberflaeche.py:7822 filtert per filt(a) auf die Tab-Art. Die Kachel-Ausgabe (oberflaeche.py:7910) schneidet nichts weiter ab.

WICHTIGE KORREKTUR AM BELEG (aufgeblaeht, sonst repariert die Hauptsitzung Korrektes): Die behaupteten "Filme-Tab: 8 Reihen fallen ganz weg" haben ALLE ACHT null Filme im Katalog (Sci-Fi & Fantasy, Action & Adventure, Mini-Series, Kids, Game Show, War & Politics, Soap, Travel = Kat-F 0) — korrektes Verhalten, nicht der Deckel. Ebenso alle zwoelf im Serien-Tab (je Kat-S 0). Von den "11 weitere zeigen 1-9" im Filme-Tab sind ALLE ELF korrekt (Children hat wirklich nur 7 Filme, Reality 5, Martial Arts 8, News 1 ...) — kein einziger beschnitten. Im Serien-Tab sind von 10 kurzen Reihen nur ZWEI echte Deckel-Opfer: Horror (7 von 41) und Familie (8 von 13).

VERWORFENE ENTLASTUNGEN: Home-Tab nicht betroffen (oberflaeche.py:7815 genresAls(a=>a,6) ohne Typ-Filter). A-Z-Raster (oberflaeche.py:7826) rettet die Genre-Ansicht nicht — alphabetisch, nicht genre-gefiltert.

SCHWERE bleibt "schwer": real beschnitten sind 21 Filme-Reihen und 19 Serien-Reihen. Serien-Tab systematisch: Drama 22 von 539 (4 %), Action 17 von 143, Thriller 16 von 133, Krimi 13 von 51, Horror 7 von 41. Beabsichtigt waren laut Kommentar filme.py:551-554 bis zu 100 je Reihe; der Serien-Tab bekommt 7 bis 47. Die Headline-Zahl des Pruefers (7 von 41 Horror-Serien) ist exakt getroffen.

NEBENFUND fuer den Fix: Der Schnitt nimmt die ersten 100 in KATALOG-Reihenfolge, nicht die bestbewerteten (erste acht Horror-Ratings: 6.8, 7.2, 6.61, 7.076, 7.2, 6.4, 5.8, 8.163) — beim Reparieren gleich die Sortierung mitentscheiden.

### 3. [SCHWER] detail() ist der EINZIGE Jellyfin-Leser ohne 401-Wiederholung — und friert den Fehlschlag 14 Tage im Cache ein

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:369`

**Beleg:** Messlauf über 13 echte Titel: die ersten 3 Titel lieferten HTTP 200 (Streams kamen), ab Titel 4 lieferte JEDER Ruf an /Users/{uid}/Items/{id} HTTP 401 — 10 von 13 Titeln endeten mit video_codec='', hoehe=0, audio_kanaele=0, audio_sprachen=[], sub_sprachen=[]. Ursache im Kontrollversuch bewiesen: Sitzung A ruft mit ihrem Token -> HTTP 200; ein zweiter Prozess meldet sich mit derselben DeviceId 'sync-jb' an; A ruft mit demselben Token erneut -> HTTP 401. Gegenprobe, dass der Token an sich hält: 14 aufeinanderfolgende Rufe mit einer frischen Sitzung = 14x HTTP 200, ein zweiter Lauf 15x HTTP 200. katalog_abzug (filme.py:178), bild_holen (filme.py:254) und episoden (filme.py:431) fangen 401 ab und melden sich einmal frisch an; der Block in detail() (filme.py:365-390) tut das nicht.

**Wirkung auf JB:** Sobald ein zweiter Prozess mit derselben DeviceId da ist — Tray, App, Fernbedienung, ein zweites Gerät —, verliert JB auf der Detailseite Qualität, Sound und Untertitel-Sprachen. Und weil der leere Eintrag mit ts=jetzt geschrieben wird, kommt er 14 Tage lang nicht wieder: nachgemessen mit frischer, gültiger Sitzung macht detail('1883') KEINEN einzigen Netz-Ruf mehr und liefert weiter video_codec='' hoehe=0.

**Urteil des Skeptikers:** Vollstaendig reproduziert, live und offline. (1) Code: 401-Heilung existiert in filme.py:178 (katalog_abzug), :254 (bild_holen), :431 (episoden), :827 (_fortschritt_senden) — der Block :368-390 in detail() hat keine. Die Behauptung "einziger Jellyfin-Leser ohne Wiederholung" stimmt woertlich. (2) Kausal live belegt: Token A -> HTTP 200 Streams=10; genau EINE Zweitanmeldung mit derselben DeviceId "sync-jb" -> Token A erneut -> HTTP 401, Token B -> HTTP 200. Basislinie vorher: 8 Detail-Rufe mit einem Token = 8x HTTP 200, das Token haelt also von allein. (3) Ende-zu-Ende durch die ECHTE detail() gegen Renes Server mit totem Token: 401 -> video_codec='' hoehe=0 kanaele=0 audio=[] subs=[], Cache-Eintrag mit ts=jetzt (Alter 0,8 s) geschrieben. Danach mit frischer, gueltiger Sitzung: 0 Netz-Rufe, weiterhin leer. Ohne den vergifteten Cache-Eintrag liefert derselbe Titel mit derselben gueltigen Sitzung h264 / hoehe=816 / 6 Kanaele / audio ['deu','eng'] / subs ['deu','eng','fra','spa','pol','hrv'] — die Daten sind also da und gehen verloren. Offline mit gepatchtem _http gegengeprueft: erst nach META_HALTBAR_S+60 s (14 Tage) geht wieder ein Ruf raus. Kontrast live im selben Lauf: episoden() mit DEMSELBEN toten Token heilt sich (401 -> Anmeldung -> 200 -> 10 Episoden). (4) JBs echter Meta-Cache (nur gelesen) enthaelt bereits 1 von 11 Filmen leer eingefroren ("Die Verurteilten", 21,3 h alt, aus der 403-Sperre) — bleibt bis ~27.08. leer. Kein Pfad im Code loescht oder invalidiert den Meta-Cache. Drei Ungenauigkeiten im Bericht des Pruefers, die den Befund nicht kippen: detail('1883') ist kein gueltiger Aufruf (Titel statt Id) und 1883 ist eine Serie — Serien liefern auch bei HTTP 200 null MediaStreams, hoehe=0 ist dort normal (ich habe deshalb mit einem Film gemessen); der Tray kann den Zweitprozess nicht ausloesen, SYNC_SCRIPTS in mailsync_tray.pyw:51-60 enthaelt kein SyncYouTube-Skript; die "10 von 13 Titeln" konnte ich nicht reproduzieren (meine Basislinie 8/8 = 200), die Zahl hing an einem parallel laufenden Prozess. Realistische Ausloeser bleiben zweite App-Instanz, Quellstart-Paket-Kopie, Entwickler-Sitzung — und prozessintern der Hintergrund-Thread filme.katalog_abzug (youtube_app.py:5732), dessen eigene 401-Heilung ein frisches Token zieht und damit das alte toetet, das ein gleichzeitig laufendes detail() schon haelt. Schwere von "blocker" auf "schwer" korrigiert: es ist stiller, dauerhafter Datenverlust ohne Selbstheilung mit 14 Tagen Halbwertszeit, aber nichts stuerzt ab, die Film-Kette laeuft weiter, die Detailseite rendert, Renes Server nimmt keinen Schaden, und der Schaden ist auf Qualitaets-/Ton-/Untertitel-Anzeige begrenzt (heute 1 von 11 Filmen betroffen). Sofort fixen ja, Arbeit stoppen nein.

### 4. [SCHWER] Jeder Fehlschlag wird als gültiges Ergebnis 14 Tage gecacht — die Selbstheilung greift nicht

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:394`

**Beleg:** Mit gepatchtem _http (kein Netz) gemessen: bei totalem Ausfall (Renés Server aus, TMDB und OMDb weg) liefert detail() beschreibung='' imdb_rating='' video_codec='' hoehe=0 — und schreibt genau das mit ts=jetzt und trailer_v2=True in den Cache. Danach _http auf 'alles heil' umgestellt und erneut gerufen: 'Netz-Rufe: KEINE', Ergebnis unverändert beschreibung='' video_codec='' hoehe=0. Die Auffrischung hängt allein an META_HALTBAR_S = 1209600 s = 14 Tage (filme.py:30).

**Wirkung auf JB:** Ein einziger Ausfallmoment — Renés Server im Neustart, WLAN weg, TMDB-Timeout — macht einen Titel für zwei Wochen dauerhaft leer: keine Inhaltsangabe, keine Besetzung, keine Bewertungen, keine Codecs. Der Docstring von detail() verspricht das Gegenteil ('tote Quelle ⇒ Felder bleiben leer, NIE eine Fehlerseite (Selbstheilungs-Regel)'): Felder leer lassen ist richtig, die Leere 14 Tage festschreiben ist es nicht.

**Urteil des Skeptikers:** REPRODUZIERT — und zusätzlich in JBs echtem Produktions-Cache belegt, nicht nur im Labor.

1) Labor-Nachstellung (Kopie des ECHTEN Katalogs mit 4885 Einträgen in einem Temp-Ordner, `filme._http` gepatcht, kein Netz; Skript: C:/Users/janbe/AppData/Local/Temp/claude/C--Users-janbe-Downloads-Jan-Bernd-Claude/a63d3cd1-fd37-4614-9f47-4b975e55a173/scratchpad/mess_detail_cache.py). Testtitel „#Zeitgeist" (tmdb 243684, imdb tt3179568), alle fünf Keyring-Schlüssel vorhanden, also werden die Anreicherungs-Zweige real betreten:
- Phase 1 (totaler Ausfall, 3 gescheiterte Rufe): beschreibung='' imdb_rating='' video_codec='' hoehe=0 cast=0 trailer=0 — und der Cache-Eintrag wird trotzdem geschrieben: ts vor 0.2 s, trailer_v2=True.
- Phase 2 (alles heil, Token-/Backoff-Zustand vorher zurückgesetzt, damit NUR der Cache bremsen kann): „Netz-Rufe: KEINE", Ergebnis unverändert leer.
- Kontrolle (gleicher heiler Patch, nur Cache-Eintrag entfernt): 5 Netz-Rufe, beschreibung='ECHTE INHALTSANGABE', imdb_rating='7.9', video_codec='hevc', hoehe=2160 → der leere Stand in Phase 2 kommt nachweislich vom Cache, nicht vom Prüfaufbau.
- Gegenprobe (ts künstlich auf META_HALTBAR_S + 60 s gealtert): 5 Netz-Rufe, Felder wieder voll → die Auffrischung hängt tatsächlich allein an den 14 Tagen (filme.py:306 prüft nur `not m`, fehlendes `trailer_v2` oder ts-Alter > META_HALTBAR_S = 1209600 s; geschrieben wird unbedingt in filme.py:394).
- Zusatz: schon ein TEIL-Ausfall friert ein — nur TMDB/OMDb tot, Jellyfin heil ⇒ beschreibung='' imdb_rating='' dauerhaft, obwohl codec/hoehe gefüllt sind.

2) Produktions-Beleg (C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme_meta_cache.json, nur gelesen): 15 Titel-Einträge, davon 5 ohne video_codec. Ich habe versucht, die zu entkräften — und 4 davon fallen zu Recht raus: „Always Hamburg", „Born to Bowl", „Die Breslauer Morde", „21 Jump Street" sind SERIEN, und ein Jellyfin-Series-Item hat legitim keine MediaStreams (heute live read-only geprüft: HTTP 200, MediaStreams=0). Übrig bleibt ein echter Fall: „Die Verurteilten" (Film, 143 min), Cache geschrieben am 12.08. 21:39 — mitten in der 403-Sperre — mit video_codec='' hoehe=0 audio_kanaele=0 audio_sprachen=[] sub_sprachen=[]. Derselbe Titel liefert heute live MediaStreams=7, Video ('hevc', 1036). Der leere Stand wird laut ts+14 Tage erst am 26.08.2026 aufgefrischt.

3) Kein Ausweg im Rest der Kette: `filme_meta_cache` wird nur an drei Stellen geschrieben (filme.py:394, :534 tmdb_stimmen, :792 tmdb_titel) — keine davon repariert leere Titel-Einträge; youtube_app.py:5390 ruft `filme.detail(fid, …)` ohne Auffrisch-Parameter, es gibt keine Cache-leeren-Route.

SCHWERE korrigiert von „blocker" auf „schwer": Der Mechanismus ist real und widerspricht dem Docstring („tote Quelle ⇒ Felder bleiben leer"), aber die Reichweite ist begrenzt — `detail()` läuft nur auf Klick (der Katalog-Abzug holt bewusst KEINE Details nach, filme.py:160-164), es gibt keinen Hintergrund-Sweep, der alle 4885 Titel auf einmal vergiften könnte; gemessen ist heute genau 1 Titel betroffen, nichts wird zerstört, und nach 14 Tagen heilt es von selbst. Die App bleibt benutzbar — es ist ein ernster Selbstheilungs-Defekt mit bis zu 14 Tagen falscher Anzeige, kein Totalausfall.

### 5. [MITTEL] Der OMDb-Tagesdeckel (950) wird nie geführt — er kann gar nicht greifen

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:356`

**Beleg:** _omdb_erlaubt() und der Zähler-Hochlauf ändern nur das lokale Dict aus _meta_cache(); geschrieben wird an filme.py:394 aber ausschliesslich der eigene Titel-Schlüssel (json_aendern mit d.__setitem__(item_id, m)). Gemessen: nach ~8 echten OMDb-Rufen im Messlauf steht in der Datei unverändert omdb_tag='2026-08-06' und omdb_zaehler=16 — bei heutigem Datum 2026-08-13. Da der gespeicherte Tag nie auf heute wechselt, setzt _omdb_erlaubt den Zähler bei JEDEM Ruf im Speicher auf 0 zurück und gibt immer True zurück. Zum Mengen-Bezug: 4868 der 4885 Katalog-Einträge tragen eine IMDb-Id.

**Wirkung auf JB:** Der eingebaute Schutz für Renés/JBs OMDb-Free-Key (1000 Abrufe/Tag) existiert praktisch nicht. Ein kaltes Durchblättern der Bibliothek feuert bis zu 4868 OMDb-Rufe ohne Bremse; der Key ist nach ~1000 für den Rest des Tages tot und alle danach angesehenen Titel bekommen leere IMDb-/Metacritic-/Tomatometer-Werte — die dann laut Befund 2 wieder 14 Tage festhängen. Nebenbei: time.strftime('%Y-%m-%d') ist das LOKALE Datum, OMDb zählt UTC-Tage — zwischen 00:00 und 02:00 Ortszeit liefen Zähler und Anbieter ohnehin auseinander.

**Urteil des Skeptikers:** REPRODUZIERT — der Befund haelt jeder Gegenprobe stand, die behauptete WIRKUNG ist aber ueberzogen.

MECHANISMUS BESTAETIGT (Code + Messung):
- filme.py:279 _meta_cache() oeffnet die Datei bei JEDEM Aufruf neu und gibt ein frisches Dict zurueck (kein Modul-Cache). _omdb_erlaubt (356/287-291) und der Zaehler-Hochlauf (filme.py:356) mutieren damit ein Wegwerf-Dict.
- Geschrieben wird bei filme.py:394 ausschliesslich der eigene Titel-Schluessel (json_aendern, d.__setitem__(item_id, m)). Die einzigen weiteren Schreibstellen auf _pfade["meta"] sind 534 (tmdb_stimmen) und 792 (tmdb_titel). omdb_tag/omdb_zaehler werden NIRGENDS persistiert.

MESSUNG (offline, _http/_meta_keys/_anmelden monkeypatched, Arbeitskopie im Scratchpad; Renes Server und JBs echte Dateien unberuehrt, kein einziger Live-Ruf):
- Datei vor dem Lauf: omdb_tag='2026-08-06', omdb_zaehler=16, heute lokal 2026-08-13.
- Nach 1, 5, 30 Detail-Abrufen: OMDb-Rufe 1/5/30, Datei unveraendert 2026-08-06/16.
- _omdb_erlaubt(frischer Cache) dreimal: (zaehler_vorher=16, zaehler_nachher=0, erlaubt=True) — exakt der behauptete Dauer-Reset.
- 1030 Detail-Abrufe in einem Prozess: 1030 OMDb-Rufe, OMDB_TAGES_DECKEL=950 ueberschritten=True, Datei weiterhin 2026-08-06/16.
- Gegenprobe A (Datei kuenstlich auf heute/999): 0 neue OMDb-Rufe — die Deckel-LOGIK funktioniert, nur wird der Wert nie erreicht.
- Gegenprobe B (alter Tag + 999): 1 Ruf — Reset greift, wie beschrieben.

ECHT-BELEG AUS JBS PRODUKTIVDATEN (unabhaengig von meinem Testlauf):
filme_meta_cache.json wurde zuletzt am 12.08. 21:39 geschrieben; ein Titel-Eintrag von diesem Zeitpunkt traegt ein imdb_rating (= echter OMDb-Ruf nach dem 06.08.). Der persistierte Zaehler steht trotzdem unveraendert bei omdb_tag='2026-08-06', omdb_zaehler=16.

HERKUNFT (erklaert die Fossil-Werte): Build 176 (9fc6213) schrieb noch fam.json_schreiben(_pfade["meta"], cache) — das ganze Dict inkl. Zaehler. Die Umstellung auf json_aendern mit nur dem eigenen Schluessel (Nachtpruefung 06.08.) hat den Deckel still stillgelegt; der 06.08. ist genau der Bruchtag.

MENGEN-BEZUG bestaetigt: 4868 von 4885 Katalog-Eintraegen tragen eine IMDb-Id (gemessen).

WARUM SCHWERE VON "schwer" AUF "mittel" KORRIGIERT:
Die behauptete Wirkung "ein kaltes Durchblaettern der Bibliothek feuert bis zu 4868 OMDb-Rufe ohne Bremse" gibt der Code nicht her. detail() wird nur an drei Stellen gerufen: oberflaeche.py:8067 (Hero-Render, 1x pro TV-Tab), oberflaeche.py:8102 (tvInfo, Klick auf eine Kachel) und oberflaeche.py:3882 (filmePlay, nur falls Meta fehlt). Die Netflix-Hover-Karte holt KEIN Detail, filme.mehr_wie() (565-572) ruft detail() nur fuer denselben Titel (kein Fan-out), und es gibt keine Vorwaerm-/Batch-Schleife ueber den Katalog. Also ein OMDb-Ruf pro NEU geoeffnetem Titel, danach 14 Tage Cache — JB muesste ~1000 verschiedene, noch ungecachte Titel an EINEM Tag oeffnen, um den Free-Key zu verbrennen. Der Schutz ist real und vollstaendig tot (latente Regression, die bei einem Skript-Lauf oder einer kuenftigen Vorwaerm-Funktion sofort zuschlaegt), aber die Katastrophe, die der Pruefer beschreibt, kann heute nicht eintreten.

NICHT VERIFIZIERBAR UND GEGENSTANDSLOS: die UTC-/Lokalzeit-Anmerkung zu time.strftime('%Y-%m-%d'). Ob OMDb UTC-Tage zaehlt, konnte ich nicht messen; solange der Zaehler ueberhaupt nie persistiert wird, spielt die Tagesgrenze keine Rolle. (Zur Kontrolle: lokales Datum und UTC-Datum sind derzeit beide 2026-08-13.)

Messkript: C:/Users/janbe/AppData/Local/Temp/claude/C--Users-janbe-Downloads-Jan-Bernd-Claude/a63d3cd1-fd37-4614-9f47-4b975e55a173/scratchpad/omdbmess/mess_deckel.py — Stelle bestaetigt: C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:287-291 (Pruefung) und :356 (Zaehler) gegen :394 (Schreibweg).

### 6. [SCHWER] Nur 404 wird gemerkt - bei 500/503/Timeout feuert jede Kachel unbegrenzt weiter

**Stelle:** `SyncYouTube/System/filme.py:270`

**Beleg:** Gemessen mit gepatchtem _http, je Fall frischer Zustand: '500 Server-Panne -> 5 Rufe an Renes Server', '503 ueberlastet -> 5 Rufe', '200 leerer Koerper -> 5 Rufe', 'Timeout -> 5 Rufe an Renes Server, .fehlt=False'. Nur '404 kein Bild -> 1 Ruf'. Zeile 270 (`if st != 200 or not roh: return None`) verlaesst die Funktion ohne jeden Merker; katalog_abzug hat mit FEHL_BACKOFF_S (Zeile 29) so eine Bremse, bild_holen hat keine.

**Wirkung auf JB:** Wenn Renes Server hustet (Bibliotheks-Scan, Neustart, Ueberlast), wiederholt jede sichtbare Kachel ihren Ruf bei jedem Seitenaufbau - ohne Pause und ohne Obergrenze. Genau das Haemmern, das den Server letzte Woche dicht gemacht hat.

**Urteil des Skeptikers:** Befund vollstaendig reproduziert, Widerlegung gescheitert. Eigene Messung mit gepatchtem _http, je Fall frischer Cache-Ordner, 5 Aufrufe von bild_holen("abc123","Primary"): 404 -> 1 Ruf und .fehlt=True; 500/502/503/429/200-mit-leerem-Koerper/Timeout -> je 5 Rufe, .fehlt=False; 200 mit Bild -> 1 Ruf. Zeile 270 (if st != 200 or not roh: return None) verlaesst die Funktion tatsaechlich ohne Merker, waehrend katalog_abzug mit FEHL_BACKOFF_S (Zeile 29) eine Bremse hat.

Drei Gegenproben, um den Befund zu kippen:
(1) Bremse im Aufrufer? Nein. youtube_app.py:5526 ruft filme.bild_holen ohne Drossel. Zusaetzlich bestaetigt: der Erfolgsfall sendet cache=86400, der Fehlerfall _antwort(self,404,...) sendet KEIN Cache-Control (_antwort, youtube_app.py:5215) - der Browser fragt also bei jedem Seitenaufbau neu. Die behauptete Wirkungskette haelt.
(2) Bremst die Anmeldesperre indirekt? Nur im falschen Fall. Gemessen: Anmeldung 500 -> 1 Ruf statt 5, Anmeldung 403 -> 1 Ruf statt 5 (_anmelde_sperre_ts, 60s/600s). Der Schutz greift nur, wenn der Server komplett tot ist. Ungebremst bleibt genau die vom Pruefer genannte Lage: Anmeldung gesund, Bild-Endpunkt hustet (Bibliotheks-Scan, Ueberlast).
(3) Mengen-Effekt? Groesser als behauptet. Von 4885 Katalog-Eintraegen haben nur 364 ein zwischengespeichertes Primary-Bild, 4521 wuerden live nachgeladen (683 Cache-Dateien gesamt ueber alle Bild-Arten, davon 12 .fehlt-Merker). Die onerror-Kette Thumb->Backdrop->Poster (oberflaeche.py:7507-7509) verdreifacht jeden Fehlschlag: 20 Kacheln x 3 Arten x 3 Seitenaufbauten ergeben 60 Rufe bei 404 gegenueber 180 Rufen bei 503, Faktor 3,0.

Verschaerfung gegenueber der Behauptung: bei 401 -> Neuanmeldung -> 500 sind es zwei Bild-Rufe plus eine Anmeldung je Aufruf (gemessen 10 Bild-Rufe + 5 Anmeldungen fuer 5 Aufrufe), weil der 401-Wiederholweg (Zeilen 254-260) in dieselbe merkerlose Zeile 270 laeuft.

Live lesend gegengeprueft (8 Rufe, 1,5 s Pause): Renes Server liefert im gesunden Zustand HTTP 200 mit 420-1414 KB je Bild - der Normalbetrieb ist unauffaellig, der Befund betrifft ausschliesslich das Fehlerverhalten.

Schwere bleibt "schwer" und wird nicht abgestuft: es handelt sich um einen unbegrenzten, pausenlosen Verstaerker ausgehender Rufe gegen fremdes Eigentum, die Angriffsflaeche umfasst 4521 ungecachte Titel (13563 Rufe je Seitenaufbau bei durchgaengigem 503), und genau dieses Haemmern hat Renes Server vom 06.08. bis 13.08. mit HTTP 403 gesperrt. Kein Code geaendert, Bilder-Cache unveraendert bei 683 Dateien.

### 7. [MITTEL] Der Bilder-Cache waechst unbegrenzt: keine Obergrenze, keine Alterung, kein Aufraeumen

**Stelle:** `SyncYouTube/System/filme.py:272`

**Beleg:** Produktions-Ordner filme_bilder heute: 671 Bilder + 12 Marker = 289,8 MB, und das fuer nur 389 der 4885 Titel (8%). Gemessene Mittelwerte: Primary 441,6 KB, Backdrop 576,5 KB, Thumb 360,6 KB, groesste Datei 2,33 MB. Mit den live gemessenen Trefferquoten (100/83/67%) ergibt das fuer den Vollbestand 2,06 + 2,24 + 1,12 = 5,41 GB in ~11.600 Dateien. Eine Suche nach Aufraeum-Code (grep ueber alle .py nach filme_bilder / _pfade['bilder']) findet ausser einrichten(), dem Lesen und dem Schreiben nichts - es gibt keine Loesch-, Alterungs- oder Deckel-Logik.

**Wirkung auf JB:** Nur durchs Stoebern fuellt SyncYouTube still ueber 5 GB auf JBs Systemplatte, und Renes Bibliothek waechst weiter. Niemand meldet das, es gibt keinen Deckel und keinen Knopf zum Verkleinern.

**Urteil des Skeptikers:** WIDERLEGUNG GESCHEITERT — der Befund ist echt und in jedem Einzelteil reproduziert. Die Schwere stufe ich von "schwer" auf "mittel" herunter, weil die behauptete Wirkung auf JB (Systemplatte laeuft still voll) der Messung nicht standhaelt.

1) ZAHLEN EXAKT NACHGEMESSEN (C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\filme_bilder)
671 Bilder + 12 Marker = 289,8 MB. Mittelwerte: Primary 441,6 KB (389 Stk), Backdrop 576,5 KB (108), Thumb 360,6 KB (174); groesste Datei 2,33 MB (aefe81358c21546835056e92d5b86e35_Backdrop.jpg). 452 verschiedene Item-IDs bei 4885 Katalog-Eintraegen. Alle Werte des Pruefers stimmen auf die Nachkommastelle.

2) KEIN AUFRAEUM-CODE — breiter gesucht als der Pruefer
Grep ueber alle .py nach os.remove/os.unlink/shutil.rmtree/send2trash: kein einziger Treffer auf filme_bilder (die Treffer in youtube_app.py sind Papierkorb fuer Mediendateien, Playlist-Spiegelung, ffmpeg-tmp, Abo-Index). Grep nach Aufraeum-Vokabular (aufraeum|bereinig|prune|evict|lru|max_bytes|cache_limit|alterung|verfall|disk_usage|free_space): nichts fuer den Bilder-Cache. Auch der Nacht-Waechter in SyncDashTray faellt aus: SyncYouTube ist dort ueberall ausgeklammert (eigenes Repo, gate_ruff.py:9, programm_kanon.py:54). filme.py kennt den Pfad an genau drei Stellen: einrichten (Z. 41), Lesen (Z. 235-238), Schreiben (Z. 263/272-273).

3) LIVE-GEGENPROBE (Cache auf Scratchpad umgebogen, JBs Produktions-Cache nachweislich unberuehrt bei 671+12 = 289,8 MB)
12 kalte Zufallstitel geholt, Cache-Summe wuchs monoton 0 -> 5.113.721 Bytes, nichts wurde je geraeumt oder ueberschrieben. Mittel 426,1 KB — damit ist belegt, dass der Produktions-Mittelwert kein Artefakt einer Bulk-Sitzung ist, sondern repraesentativ.

4) DIE HOCHRECHNUNG IST EHER ZU NIEDRIG
Trefferquoten selbst gemessen (8 kalte Titel, je Backdrop+Thumb): Backdrop 8/8 = 100 % (Pruefer: 83 %), Thumb 7/8 = 88 % (Pruefer: 67 %), 1 .fehlt-Marker. Mit meinen Werten: Primary 1,99 + Backdrop 2,01 + Thumb 1,83 = 5,83 GB statt der behaupteten 5,41 GB.

5) ZUSATZBELEG, der den Befund stuetzt: filme.py:252 ruft /Items/<id>/Images/<art> OHNE maxWidth- oder quality-Parameter — es kommen Jellyfin-Originale (bis 2,33 MB) fuer Kacheln, die im Raster wenige hundert Pixel breit sind.

WARUM TROTZDEM NUR "MITTEL":
a) "unbegrenzt" ist sachlich unpraezise. Die Obergrenze ist Katalog x 3 Bildarten, heute ~5,8 GB; sie waechst nur mit Renes Bibliothek, nicht endlos.
b) Die behauptete Wirkung stimmt nicht. Gemessen: C: hat 3725 GB gesamt, 1841 GB frei. 5,83 GB sind 0,32 % des freien Platzes. Das ist kein Platzproblem fuer JB.
c) Tempo: 8 Tage Nutzung ergaben 290 MB, und 535 der 683 Dateien entstanden an EINEM Tag (06.08., Bulk-Sitzung); an normalen Tagen 15-33 Dateien.

WAS DIE HAUPTSITZUNG STATTDESSEN BEACHTEN SOLLTE (aus meiner Messung, nicht aus dem Prueferbericht):
- Der GB-Sprung ist mit einem Handgriff erreichbar: oberflaeche.py:7818-7828 baut fuer die Reiter "filme"/"serien" ein A-Z-Raster ueber den GANZEN Katalog ohne slice ("Alle von A bis Z (3967)"), die Kacheln haben loading="lazy" — einmal durchscrollen holt alle Poster. Der Deckel fehlt also an einer Stelle, die der Nutzer taeglich erreicht.
- Der schmerzhaftere Teil der fehlenden Alterung ist nicht der Platz, sondern die Dauerhaftigkeit: Das Lesen (filme.py:236-238) prueft kein mtime, ein von Rene geaendertes Poster bleibt bei JB fuer immer alt. Und die Negativ-Marker (filme.py:244-246) verfallen nie — fuegt Rene spaeter ein Thumb hinzu, sieht JB es nie wieder. Das ist ein echter Sichtbarkeits-Fehler, kein reines Speicher-Thema.
- Guenstigster Hebel waere ein maxWidth am Bild-Ruf (filme.py:252), das senkt Volumen und Ladezeit auf einen Schlag; Deckel/Alterung koennen dann klein ausfallen.

### 8. [SCHWER] "▶ Weiterschauen" startet bei den Simpsons Bonus-Material statt der Pilotfolge

**Stelle:** `SyncYouTube/System/filme.py:447`

**Beleg:** filme.episoden('602e3c565c6293294d5c3f484499b679')  # Die Simpsons, 553 Folgen
Jellyfin roh, erste 4: [(1,1,'Es weihnachtet schwer'), (1,2,'Bart wird ein Genie'), (1,3,'Der Versager'), (1,4,'Eine ganz normale Familie')]
unsere Ausgabe, erste 4: [(1,0,'die.simpsons.s05.bonus.nicht.benutzte.szenen.'), (1,0,'atg-simpsons2101'), (1,1,'Es weihnachtet schwer'), (1,2,'Bart wird ein Genie')]
Rohdaten der zwei Ausreißer: {"Name":"die.simpsons.s05.bonus.nicht.benutzte.szenen.aus.staffel.5.en", "ParentIndexNumber":1, "IndexNumber":null, "SeasonName":"Season 5"} und {"Name":"atg-simpsons2101", "ParentIndexNumber":1, "IndexNumber":null, "SeasonName":"Season 21"}
Nachgestellte Frontend-Logik (oberflaeche.py:8121, eps.find(x=>!x.gesehen)): 'Weiterschauen' spielt S1F0 'die.simpsons.s05.bonus.nicht.benutzte.szenen.aus.staffel.5.en'

**Wirkung auf JB:** JB drückt auf der größten Serie der Bibliothek ▶ und bekommt nicht benutzte Szenen aus Staffel 5 statt "Es weihnachtet schwer". Ursache: IndexNumber fehlt ⇒ `it.get("IndexNumber") or 0` macht Folge 0 daraus, und der Sortierschlüssel (1,0) zieht die Datei VOR die Pilotfolge. Weil JB nichts als gesehen markiert hat, greift immer der Zweig "erste ungesehene Folge" — der Fehler tritt also bei jedem Öffnen auf, nicht nur einmal.

**Urteil des Skeptikers:** ECHT — 1:1 reproduziert, Mechanismus am Rohdatensatz belegt, alle Widerlegungsversuche gescheitert.

REPRODUKTION (live, nur lesende Rufe):
filme.episoden('602e3c565c6293294d5c3f484499b679') -> 553 Folgen in 0,98 s.
Unsere Ausgabe, erste 4: (1,0,'die.simpsons.s05.bonus.nicht.benutzte.szenen.aus.staffel.5.en'), (1,0,'atg-simpsons2101'), (1,1,'Es weihnachtet schwer'), (1,2,'Bart wird ein Genie').
Katalog bestaetigt die ID: {"id":"602e3c565c6293294d5c3f484499b679","titel":"Die Simpsons","typ":"serie","jahr":1989} — die groesste Serie der Bibliothek (918 Serien gesamt).

MECHANISMUS AM ROHDATENSATZ (HTTP 200, 933.592 Bytes, 553 Items):
Jellyfins EIGENE Reihenfolge ist korrekt — Server-Position 1..6 = S1F1..S1F6 ('Es weihnachtet schwer' zuerst). Genau zwei Items haben IndexNumber: null; sie stehen serverseitig auf Position 82 und 442:
  {"Name":"die.simpsons.s05.bonus.nicht.benutzte.szenen.aus.staffel.5.en","ParentIndexNumber":1,"IndexNumber":null,"SeasonName":"Season 5"}
  {"Name":"atg-simpsons2101","ParentIndexNumber":1,"IndexNumber":null,"SeasonName":"Season 21"}
Jellyfin meldet fuer beide ParentIndexNumber 1, obwohl SeasonName "Season 5"/"Season 21" sagt. filme.py:447 (`it.get("IndexNumber") or 0`) macht daraus folge=0; der Sortierschluessel (1,0) in filme.py:451 zieht sie vor die Pilotfolge. Unser out.sort() zerstoert damit eine bereits richtige Server-Reihenfolge.

WIDERLEGUNGSVERSUCHE — ALLE GESCHEITERT:
1. Filtert die API-Schicht die F0-Items weg? Nein: youtube_app.py:5440 reicht filme.episoden(fid) ungefiltert durch (_antwort(self, 200, {"items": filme.episoden(fid)})).
2. Ist der Knopf konditional? Nein: oberflaeche.py:8167 rendert fuer d.typ==='serie' bedingungslos `<button onclick="tvSerienPlay()">▶ Weiterschauen</button>` — keine Alternative, kein "Von vorne" bei Serien.
3. Greift vielleicht der Resume-Zweig (position_s>0) und rettet die Lage? Nein — ueber alle 553 Folgen gemessen: 0 gesehen, 0 mit position_s>0. Der Zweig "erste ungesehene" feuert deterministisch bei jedem Oeffnen.
4. Nachstellung der Frontend-Logik oberflaeche.py:8121 (eps.find(x=>x.position_s>0&&!x.gesehen)||eps.find(x=>!x.gesehen)||eps[0]) gegen die ECHTEN Daten waehlt: (1, 0, 'die.simpsons.s05.bonus.nicht.benutzte.szenen.aus.staffel.5.en'). Exakt wie behauptet.
Zusatz: die Detailseite ist laut Kommentar oberflaeche.py:8091 auch OHNE Fernsehmodus erreichbar — der Fehler ist nicht auf den TV-Modus beschraenkt. Die Folgenliste zeigt die Stoerer zusaetzlich als "F0 · die.simpsons…" oben in Staffel 1 (oberflaeche.py:8202).

SCHWERE: "schwer" bestaetigt. Der primaere Aktionsknopf der groessten Serie der Bibliothek spielt deterministisch, bei jedem Oeffnen, falschen Inhalt (Bonus-Rohmaterial mit Dateinamen als Titel) statt der Pilotfolge. Kein Datenverlust, Umgehung durch manuelle Folgenwahl moeglich — deshalb kein blocker.

EINORDNUNG DER VERBREITUNG (Stichprobe 25 zufaellige Serien, Seed 42, 0,4 s Pause zwischen Rufen): 1 von 25 trifft den F0-Fall — Die Simpsons. Dabei fiel ein ZWEITER Fall DERSELBEN WURZEL auf, den der Pruefer nicht nennt: BoJack Horseman waehlt S0F1 'Sabrinas Weihnachtswunsch' (Staffel 0 = Specials sortiert vor Staffel 1). Empfehlung an die Hauptsitzung: die Wurzel beheben — Items ohne IndexNumber und Staffel 0 ans ENDE statt an den Anfang sortieren (bzw. Jellyfins Server-Reihenfolge nicht ueberschreiben) — statt nur den Simpsons-Fall.

Kein Code geaendert, nichts geschrieben, keine Konfiguration angefasst, keine Prozesse beruehrt. 27 lesende Rufe mit Pausen, kein erneuter Voll-Abzug. Messskripte: C:\Users\janbe\AppData\Local\Temp\claude\C--Users-janbe-Downloads-Jan-Bernd-Claude\a63d3cd1-fd37-4614-9f47-4b975e55a173\scratchpad\m3.py, m4.py, m5.py. Betroffene Stellen: C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\filme.py:447 und :451, C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\oberflaeche.py:8113 und :8121.

### 9. [MITTEL] Fehlende Folgennummer wird zu "F0" — 378 von 1762 Episoden (21,5 %) landen im selben Sammelbecken

**Stelle:** `SyncYouTube/System/filme.py:447`

**Beleg:** filme.episoden('0cf35bb0e77c9aeb790177da68c1a94d')  # Pokémon, 850 Folgen
roh: ohne IndexNumber = 376 von 850
folge==0 je Staffel: {0: 43, 1: 18, 2: 64, 3: 59, 4: 48, 5: 35, 6: 60, 7: 48, 8: 1}
größte Schlüssel-Gruppen (Anzahl, (staffel,folge)): [(64,(2,0)), (60,(6,0)), (59,(3,0)), (48,(7,0)), (48,(4,0)), (43,(0,0)), (35,(5,0)), (18,(1,0))]
So erscheinen die ersten drei Kacheln der Staffel 1 (oberflaeche.py:8202, `F${e.folge} · titel`):
  'F0 · 100.Pokemon.-.Feiertag.mit.Hindernissen'
  'F0 · 183.Pokemon.-.Geister.in.Teak.City'
  'F0 · 184.Pokemon.-.Von.Geist.zu.Geist'
über alle 1762 gemessenen Episoden: folge==0 gesamt = 378

**Wirkung auf JB:** Die Staffel 1 von Pokémon beginnt mit Folge 100, 183, 184 — alle als "F0" beschriftet. 64 Folgen der Staffel 2 tragen dieselbe Nummer F0; ihre Reihenfolge ist damit reiner Zufall (Python sortiert stabil, also gilt Jellyfins eigene Reihenfolge — und die ist nachweislich ungeordnet, siehe Rick and Morty). JB kann in solchen Serien weder die Folge wiederfinden, bei der er war, noch der Reihe nach schauen. Wurzel: `or 0` macht "Nummer fehlt" und "Nummer ist 0" ununterscheidbar.

**Urteil des Skeptikers:** Kern reproduziert, Schwere-Begruendung widerlegt.

REPRODUZIERT (1:1): filme.episoden('0cf35bb0e77c9aeb790177da68c1a94d') -> 850 Episoden, folge==0 = 376; Verteilung je Staffel {0:43,1:18,2:64,3:59,4:48,5:35,6:60,7:48,8:1} identisch zur Behauptung; erste drei Kacheln der Staffel 1: 'F0 . 100.Pokemon.-.Feiertag.mit.Hindernissen', 'F0 . 183.Pokemon.-.Geister.in.Teak.City', 'F0 . 184.Pokemon.-.Von.Geist.zu.Geist'.

URSACHE HART BELEGT (ueber die Behauptung hinaus): Rohabruf /Shows/{id}/Episodes zeigt 'IndexNumber-Schluessel FEHLT: 376' und 'IndexNumber == 0 (echt): 0'. Es gibt also keine legitimen Nullen — filme.py:447 `it.get("IndexNumber") or 0` verschmilzt nachweislich "fehlt" mit "ist 0". Anzeige ungeschuetzt: oberflaeche.py:8202 `F${e.folge}` ohne Fallunterscheidung; youtube_app.py:5440 reicht filme.episoden() unveraendert durch. Sortierung (staffel, folge) zieht den Nullen-Block vor die echte Folge 1: Staffel 1 hat 100 Folgen, Kacheln 1-18 sind F0 (Episoden 183-196), erst Position 19 ist 'F1 . Pika-Pikachu'.

WIDERLEGT TEIL 1 — die 21,5 %: 376 der 378 stammen aus einer einzigen Serie. Zwei unabhaengige Zufallsstichproben (Seed 4711: 25 Serien / 841 Episoden; Seed 999: 14 Serien / 570 Episoden; zusammen 39 Serien / 1411 Episoden, darunter Akte X 217, Beavis and Butt-Head 196, InuYasha 110, New Girl 146) ergaben NULL Treffer, 0,00 %. Das Problem ist punktuell in schlecht eingelesenen Serien, kein Flaechenproblem der Bibliothek.

WIDERLEGT TEIL 2 — "Reihenfolge ist reiner Zufall": Pythons stabile Sortierung erhaelt Jellyfins Reihenfolge, und Jellyfin liefert lexikografisch nach Dateiname; die Dateinamen tragen fuehrende Episodennummern. Messung: 'lexikografisch aufsteigend? True' und 'fuehrende Nummern ... aufsteigend? True' fuer Staffel 1 (18/18) und Staffel 2 (64/64). Die Folgen stehen in korrekter Sendereihenfolge — JB KANN der Reihe nach schauen, er kann die Nummer nur nicht am Etikett ablesen. Die behauptete Wirkung ist damit zur Haelfte falsch.

VERBLEIBENDER SCHADEN: Pokemon Staffel 1 oeffnet mit Episode 183 statt "Pika-Pikachu"; 18 bzw. 64 gleich beschriftete F0-Kacheln sind zum Wiederfinden untauglich.

Deshalb mittel statt schwer: Wurzel korrekt benannt und fixwuerdig (IndexNumber als None durchreichen, Etikett und Sortierung trennen), aber Reichweite um rund zwei Groessenordnungen kleiner als behauptet und Reihenfolge intakt.

Nur lesende Rufe, ca. 45 Abrufe mit 0,6 s Pause, kein Code geaendert. Messskripte: C:\Users\janbe\AppData\Local\Temp\claude\C--Users-janbe-Downloads-Jan-Bernd-Claude\a63d3cd1-fd37-4614-9f47-4b975e55a173\scratchpad\m1.py bis m6.py

### 10. [BLOCKER] Transcode-Weiche startet nie: _ffmpeg_pfad() liefert den Ordner, die Route ruft ihn als Programm auf

**Stelle:** `C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\youtube_app.py:5467`

**Beleg:** youtube_app.py:332 `return BIN_DIR if os.path.exists(exe) else None` — also der ORDNER. youtube_app.py:5467 `ff = _ffmpeg_pfad()`, :5474 `cmd = [ff, "-hide_banner", ...]`, :5484 `_tc_starten(cmd)` → `subprocess.Popen([<...>\System\bin, ...])`. Gemessen mit dem echten Befehlsaufbau und der echten Stream-URL: `PermissionError: [WinError 5] Zugriff verweigert   [cmd[0] = C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\bin]`. Derselbe Befehl mit `bin\ffmpeg.exe` als cmd[0] laeuft sofort: 'Lola rennt: vcopy=False start=0s -> erste Bytes nach 1.3 s, 56 KB in 1.3 s', 'Lincoln: vcopy=False start=1800s -> erste Bytes nach 3.2 s', 'Snakes on a Plane: vcopy=True -> erste Bytes nach 1.2 s'. (Die anderen Aufrufer sind korrekt: Zeile 550 gibt den Ordner an yt-dlp als ffmpeg_location, Zeile 3849 baut sich den exe-Pfad selbst.)

**Wirkung auf JB:** Die Weiche, die 18 von 20 gemessenen Titeln (90 %, alles mit AC3/E-AC3/DTS/HEVC) bedienen soll, wirft eine Ausnahme im Anfragen-Thread; do_GET hat keinen Auffang-Block, der Client bekommt gar keine Antwort. Das <video> feuert daraufhin sein error-Ereignis, und die Selbstheilungs-Kette (oberflaeche.py:4024) macht den Fehler unsichtbar, indem sie auf VLC umschaltet — deshalb ist es nie aufgefallen. Ergebnis: der Netflix-Weg im Browser existiert praktisch nicht, JB landet fast immer im VLC-Fenster; vom Handy aus startet VLC auf dem PC im anderen Raum.

**Urteil des Skeptikers:** Nicht widerlegbar — jeder Schritt unabhaengig nachgemessen, alle Widerlegungsversuche gescheitert.

BELEGE (eigene Messung):
1. _ffmpeg_pfad() liefert nachweislich den Ordner: "C:\...\System\bin", isdir=True, isfile=False.
2. bin\ffmpeg.exe existiert (144 MB) — die Route bricht also NICHT vorher bei "if not ff" ab, der Popen wird erreicht.
3. Echter Befehlsaufbau 1:1 aus youtube_app.py:5474-5483, Popen 1:1 aus _tc_starten (5048-5050):
   cmd[0]=BIN_DIR  -> PermissionError: [WinError 5] Zugriff verweigert
   cmd[0]=ffmpeg.exe -> Popen OK, pid 2444
4. Gegen den ECHTEN Jellyfin-Strom (Titel "#Zeitgeist", read-only, ein Strom, sofort gekillt):
   Ordner -> PermissionError [WinError 5]; exe -> erste Bytes nach 2.3 s, 65536 Bytes.
   Damit ist cmd[0] der EINZIGE Defekt, der Rest der Transcode-Kette ist gesund.
5. Kein Auffang-Block: AST-Analyse von do_GET (Zeilen 5270-5624) zeigt im Rumpf 5 If, kein Try.
   Der try bei 5470 deckt nur das start-Parsen (except TypeError/ValueError bei 5472);
   _tc_starten bei 5484 steht blank; der zweite try bei 5489 beginnt erst NACH dem Absturzpunkt.
6. Server-Bauform nachgestellt (ThreadingHTTPServer + BaseHTTPRequestHandler, kein
   handle_error-Override — wie im Original bei 5227/6211): der Client sieht
   "RemoteDisconnected: Remote end closed connection without response", also gar keine Antwort.
   Das <video> feuert daraufhin sein error-Ereignis — genau wie behauptet.
7. tc=1 ist KEIN toter Code: oberflaeche.py:3894 setzt tvpTc=true fuer jeden Titel ausserhalb
   der Huelle, den der Browser nicht direkt kann; zusaetzlich schaltet die Selbstheilung bei
   4017 nach einem <video>-Fehler auf Transcode, und 4023/4024 faellt dann auf VLC zurueck.

SCHWERE bestaetigt, sogar unterschaetzt: eigene Zufallsstichprobe (seed 42) von 25 echten
Titeln ueber den Jellyfin-Einzelabruf ergab 24/25 = 96 % Transcode-Bedarf (Pruefer sagte 90 %).
Alles mit AC3/E-AC3/DTS scheitert an aOk, HEVC zusaetzlich an vOk. Nur "The Big Picture"
(h264/aac) ging direkt.

VERSTAERKEND (eigener Nebenfund fuer die Hauptsitzung): in filme_katalog.json sind
video_codec und audio_codec bei ALLEN 4885 Eintraegen leer. Wo filmePlay seine Metadaten aus
Listen-/Hero-Daten statt aus /api/filme/detail zieht, ist filmeBrowserKann deshalb immer
falsch — dann laeuft selbst der eine Direct-Play-Titel in den kaputten Zweig.

EINSCHRAENKUNG (fairerweise): JB sieht kein schwarzes Bild, die Selbstheilung bei
oberflaeche.py:4024 schaltet auf VLC — genau deshalb fiel es nie auf. Das mindert den Befund
nicht: der Browser-/Netflix-Weg existiert praktisch nicht, vom Handy aus startet VLC auf dem
PC im anderen Raum. blocker bleibt richtig.

FIX-HINWEIS: nur youtube_app.py:5467 braucht den exe-Pfad. _ffmpeg_pfad() selbst DARF nicht
geaendert werden — Zeile 550 gibt den Ordner bewusst als ffmpeg_location an yt-dlp, Zeile 3849
baut sich ffmpeg.exe/ffprobe.exe selbst zusammen. Beide sind korrekt.

### 11. [KLEIN] Der Direkt-Proxy verschluckt jeden Jellyfin-Fehler und antwortet gar nicht

**Stelle:** `C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\youtube_app.py:5522`

**Beleg:** youtube_app.py:5509 `urllib.request.urlopen(req, timeout=30)`, :5522 `except (OSError, ConnectionError): pass`. urllib.error.HTTPError IST ein OSError — live belegt: Aufruf von stream_url() auf eine SERIEN-ID (Serie '4 Blocks') ergibt `HTTPError 500 (Internal Server Error) — Typ HTTPError, OSError? True`, leere ID ergibt `HTTPError 404`. Nachbau der Route 1:1 auf 127.0.0.1: 'Jellyfin antwortet 200 -> Client sieht: HTTP 200, Body b\'hallo\'' / 'Jellyfin antwortet 500 -> Client sieht: RemoteDisconnected: Remote end closed connection without response'.

**Wirkung auf JB:** Bei jedem Serverfehler bekommt der Browser eine abgebrochene Verbindung statt einer Fehlermeldung — im Log steht nichts, im Bild ist es schwarz. Erreichbar mit echten Daten: die Hover-Karte im Fernsehmodus hat einen eigenen ▶-Knopf (oberflaeche.py:7514), und `reihen()` liefert Serien in Top/Neu/Genres mit aus — 918 Serien im Katalog. Ein Klick darauf schickt die Serien-ID in den Abspielweg, Jellyfin antwortet 500, der Nutzer sieht nichts.

**Urteil des Skeptikers:** Der Mechanismus ist echt und reproduziert — die Wirkungskette und damit die Schwere nicht.

BESTÄTIGT: Ich habe die ECHTE youtube_app.Handler-Klasse gestartet (kein Nachbau) und nur filme.stream_url auf einen lokalen Fake-Jellyfin gezeigt. Ergebnis: Jellyfin 200 -> "HTTP 200 OK, Body b'HALLO-VIDEO-BYTES'"; Jellyfin 500/404/401 -> jeweils "RemoteDisconnected: Remote end closed connection without response". Gegenprobe: "HTTPError ist OSError? True", MRO "HTTPError -> URLError -> OSError -> ...". Es gibt kein äußeres try/except in do_GET, der getroffene elif-Zweig fällt ohne Antwort aus der Kette, und log_message ist auf pass überschrieben — "im Log steht nichts" trifft zu. Der Kernsatz der Behauptung stimmt also wörtlich.

WIDERLEGT (Erreichbarkeit): Die behauptete Auslöser-Kette "Hover-▶ auf eine Serie -> Serien-ID in den Abspielweg -> 500 -> Zeile 5522" führt nachweislich NICHT dorthin. filmePlay() verzweigt über filmeBrowserKann() (oberflaeche.py:3873; verlangt h264/avc/vp8/vp9/av1 UND aac/mp3/opus/vorbis/flac). Live an der echten ID von "4 Blocks" gemessen: video_codec='' audio_codec='' -> filmeBrowserKann=False (eine Serie hat keine MediaStreams). Damit geht der Klick im Browser in den tc=1-ffmpeg-Zweig, in der Hülle zu filmePlayVlc — der Plain-Proxy bei 5509 wird nie erreicht. Die HTTPError 500 auf die Serien-ID habe ich bestätigt, sie landet nur in einem anderen Zweig. Stichprobe von 20 echten Titeln: 18x ac3/eac3/dts/mp3 -> browserKann=False, nur 2/20 (h264+aac, z. B. "The Book of Mormon on Broadway") erreichen den Plain-Proxy, also ~10 % der Bibliothek. Auch "#Zeitgeist" (h264+ac3) geht in den tc-Zweig.

WIDERLEGT (Wirkung auf JB): "im Bild ist es schwarz / der Nutzer sieht nichts" stimmt nicht. oberflaeche.py:4016-4024 hängt am <video> eine Selbstheilungs-Kette: bei error und !tvpTc Toast "Format sperrt sich — der Transcoder übernimmt" + Umschalten auf tc=1, danach Toast "Browser kann dieses Format nicht — VLC übernimmt" + filmePlayVlc. Ein abgerissener Ladevorgang feuert genau dieses error-Event. Zusätzlich ist der Totalausfall bereits sauber behandelt: schlägt _anmelden() fehl, liefert stream_url() None und die Route antwortet mit 503 im Klartext (youtube_app.py:5462).

MESSLÜCKE (ehrlich): Einen echten Jellyfin-Fehler auf dem Plain-Proxy-Pfad konnte ich mit echten Daten nicht erzeugen — gültiger Titel durch den echten Handler -> "HTTP 206, Body-Laenge=2", verfälschter Key -> ebenfalls 206 (der Stream-Endpunkt erzwingt den Key nicht). Der Auslöser dort bleibt hypothetisch (Verbindungsabriss mitten im Strom, veralteter Katalog-Eintrag) und ist nur gegen den lokalen Fake belegt. Mein tc=1-Test war unbrauchbar (PermissionError WinError 5 — ffmpeg startet in der Sandbox nicht) und zählt nicht.

FAZIT: Echter, aber kleiner Befund. Der bleibende Kern ist eine Robustheits-/Diagnose-Lücke: der except-Zweig unterscheidet nicht zwischen "Client ist weg" (legitim, da ist niemand mehr zum Antworten) und "Jellyfin hat vor dem ersten Byte gepatzt" (sollte 502/503 + Logzeile geben). Nicht "schwer", weil der Pfad nur ~10 % der Titel betrifft, der behauptete Alltags-Auslöser dort gar nicht ankommt, der Client bereits sichtbar zurückfällt und der Komplettausfall schon eine saubere 503 liefert.

### 12. [SCHWER] Jede Serien-Folge faellt aus der Weiche, weil Folgen-IDs nicht im Katalog stehen

**Stelle:** `C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\filme.py:298`

**Beleg:** filme.py:298 sucht `next((x for x in katalog_lesen()["eintraege"] if x["id"] == item_id), None)`, der Abzug holt aber nur `IncludeItemTypes=Movie,Series`. Gemessen an der ersten Folge von '4 Blocks': `Episode-ID im Katalog-Spiegel: False`, `filme.detail(episode) -> None` → Route youtube_app.py:5393 antwortet 404 mit `{"fehler": "unbekannter Film"}`. In oberflaeche.py:3882 wird das trotzdem per `.json()` gelesen und ist WAHR, also greift :3891 `if(meta&&!inHuelle)` und schaltet auf Transcode mit tvpTcVcopy=false. Der Strom selbst waere in Ordnung: `stream_url(Folge)` → `HTTP 206 video/x-matroska bytes 0-511/1133556613`, Laufzeit laut episoden() 51 min.

**Wirkung auf JB:** Fuer Folgen wird immer die schwerste Gangart gewaehlt (voller libx264-Lauf), obwohl viele Folgen h264 sind; zugleich ist tvpMeta nur `{titel:''}` — der Player zeigt keinen Titel, `metaDauer` ist 0, und damit ist die Zeitleiste tot. Zusammen mit Befund 1 heisst das: jede Folge einer der 918 Serien endet im VLC.

**Urteil des Skeptikers:** Nicht widerlegbar — jede Stufe der Kette selbst nachgemessen, alle bestätigt.

1) Katalog enthält keine Folgen. `filme.katalog_lesen()` liefert 4885 Einträge, Typen exakt `{'film': 3967, 'serie': 918}` — kein einziger Episode-Eintrag. Ursache strukturell in filme.py:172 (`&IncludeItemTypes=Movie,Series`). Breit gegengeprüft, nicht nur an '4 Blocks': Stichprobe von 500 echten Folgen vom Server (`IncludeItemTypes=Episode`, HTTP 200) → „davon im Katalog: 0". Der Server meldet `TotalRecordCount` = 35344 Folgen, von denen keine im Spiegel steht.

2) `filme.detail()` fällt durch. Gemessen: `filme.detail('021967a5ada8be976c57b1d14ea9f127')` (4 Blocks S1F1) → `None`; über 20 zufällige Folgen der 500er-Stichprobe: „None bei 20/20". Gegenprobe Serie selbst: `filme.detail('c2ebca913c896d4de8b45047a367ea35')` → typ `serie`, liefert ein Objekt. Der Unterschied liegt also wirklich an der fehlenden ID, nicht an einem anderen Fehler.

3) Route und Weiche. youtube_app.py:5388-5394 gibt bei `d is None` hart `404 {"fehler": "unbekannter Film"}`. In oberflaeche.py:3882 wird ohne `r.ok`-Prüfung `.json()` gelesen; ich habe gegengeprüft, dass es KEINEN globalen fetch-Wrapper gibt, der bei 404 wirft (Suche nach `window.fetch =` / Wrapper: kein Treffer). `meta` ist damit das Fehlerobjekt und wahr. `filmeBrowserKann` (3874) findet leeres `video_codec`/`audio_codec` → false, also greift 3891 `if(meta&&!inHuelle)` → `tvpTc=true`, `tvpTcVcopy=false`.

4) Der Aufrufweg ist echt. `filmePlay()` bekommt Folgen-IDs an zwei Stellen: oberflaeche.py:8200 (Folgen-Kacheln der Staffel) und :8122 (`tvSerienPlay`, der ▶-Knopf auf jeder Serie) — beide aus `filme.episoden()`. Der andere Aufrufer (:7514, Hover-Karte) arbeitet mit Katalog-IDs und ist nicht betroffen. In `tvFilmPlayer` (3958) greift auch der Meta-Rückfall nicht: `tvInfoDaten.d.id` ist die SERIEN-ID, nie die Folgen-ID → `tvpMeta={titel:''}`.

5) Wirkung ist real und messbar teuer. Echte Codec-Verteilung aus 150 Folgen mit MediaStreams: Video `{h264: 126, hevc: 23, mpeg4: 1}`, Audio `{aac: 128, dts: 12, ac3: 8, eac3: 1, mp3: 1}`. Direct-Play-fähig nach der eigenen Weiche: 118/150 (79 %) — die laufen heute stattdessen durch vollen libx264. h264 und damit `-c:v copy`-fähig: 126/150 (84 %) — `tvpTcVcopy=false` verwirft auch das. Der Strom selbst ist in Ordnung: `stream_url(Folge)` → HTTP 206, `video/x-matroska`, `bytes 0-511/1133556613`; `/api/filme/direkt` (youtube_app.py:5450) fragt den Katalog gar nicht, deshalb spielt es überhaupt. Tote Zeitleiste bestätigt: `dauer:tvpTc?metaDauer:...` (3952) mit `metaDauer=0` → in `tvpTick` (4187) bleibt `if(f&&tvpDauer)` aus, Anzeige „0:00 / 0:00", kein Fortschrittsbalken, kein Titel. Dabei LIEGT die Laufzeit vor — `episoden()` liefert `laufzeit_min: 51` — sie wird nur nie weitergereicht.

Eine Präzisierung am Prüfer-Text, die den Befund aber nicht kippt: „jede Folge endet im VLC" stimmt nur in der pywebview-Hülle (dort ist `inHuelle` wahr und 3891 greift nicht, es fällt auf `filmePlayVlc`). Im normalen Browser endet es NICHT im VLC, sondern im vollen libx264-Transcode. Beide Ausgänge sind falsch — im Browser teuer und mit toter Leiste, in der Hülle wird für die 79 % Direct-Play-fähigen Folgen der leichte <video>-Weg übersprungen.

Schwere bleibt „schwer": betrifft 100 % der Folgen aller 918 Serien (35344 Stück), also die komplette Serien-Hälfte der Medienzentrale, mit dauerhafter CPU-Last und sichtbar kaputtem Player-Kopf. Nicht „blocker", weil die Folge trotzdem abspielt (206-Strom belegt) — es ist der falsche und teure Weg, kein Ausfall.

### 13. [SCHWER] Fortschritt verschwindet spurlos, wenn ein Stopp waehrend des Nachreichens danebengeht (Lesen-Aendern-Schreiben ohne Sperre)

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:877`

**Beleg:** m5_korrektur.py, Abschnitt O2: 8 liegengebliebene Meldungen im Nachreichen (150 ms Latenz je Ruf), nach 0,4 s ein Film-Stopp, dessen EINER Ruf mit 500 scheitert. Ausgabe: 'Versuch 1..5: Queue danach=0 [] | Stopp spurlos verloren: True' -> 5 von 5. Mechanik: fortschritt_nachreichen liest die Queue in Zeile 866, arbeitet minutenlang mit dieser ALTEN Liste und schreibt in Zeile 877 'rest' zurueck; der zwischenzeitlich von fortschritt() (Zeile 859) angehaengte Eintrag wird dabei ueberschrieben. Beide nutzen fam.json_schreiben. Gegenprobe im selben Modul: der Meta-Cache nutzt in Zeile 394/534/792 korrekt fam.json_aendern, mit dem Kommentar 'Zwei-Fragen-Regel (Nachtpruefung 06.08.): mehrere Server-Threads schreiben den Meta-Cache'. Die Queue und die Merkliste wurden dabei vergessen (grep: json_aendern 3x Meta, json_schreiben 2x Queue + 1x Merkliste).

**Wirkung auf JB:** JB beendet einen Film bei Minute 42, genau waehrend der 6-h-Abzug seine Restmeldungen nachreicht. Der Spot ist danach weder bei Rene noch lokal gemerkt: 'Weiterschauen ab 42 min' verschwindet beim naechsten Katalog-Abzug, der Film faengt wieder bei 0 an. Das Fenster ist nicht Millisekunden gross, sondern die gesamte Laufzeit des Nachreichens (gemessen 2,41 s bei 10 Eintraegen und 200 ms Latenz; im Code steht _http(timeout=15) je Ruf, also bis 15 s * Anzahl bei haengendem Server).

**Urteil des Skeptikers:** Unabhaengig reproduziert, nicht widerlegt. Eigene Sandbox-Messung (filme.einrichten auf Temp-Ordner, _http als Attrappe, urllib.request.urlopen hart blockiert — kein Live-Zugriff auf Renes Server): 8 liegengebliebene Meldungen à 150 ms, nach 0,4 s ein Film-Stopp mit HTTP 500 => 'Queue danach=0 []', 5/5 verloren. Zwei Gegenproben schliessen ein Phantom aus: (B) derselbe Stopp OHNE paralleles Nachreichen => Eintrag NEU bleibt, 0/5; (C) alte Eintraege scheitern ebenfalls => geschafft=0 => gar kein Schreibvorgang, 0/5. Damit ist die Ursache exakt der beschriebene Pfad: fortschritt_nachreichen liest die Queue (Zeile 866), arbeitet mit der alten Liste und schreibt in Zeile 877 'rest' zurueck; geschrieben wird genau dann, wenn mindestens ein Ruf gelang, und dieser Schreibvorgang ueberbuegelt den zwischenzeitlich von fortschritt() angehaengten Eintrag. Nebenlaeufigkeit ist real: youtube_app.py laeuft als ThreadingHTTPServer (POST /api/filme/fortschritt im Handler-Thread), katalog_abzug startet in youtube_app.py:5732 als eigener Thread und ruft fortschritt_nachreichen() in filme.py:202; grep nach Lock/RLock in filme.py ist leer. Inkonsistenz bestaetigt: 3x fam.json_aendern (Meta-Cache), 2x fam.json_schreiben (Queue) + 1x (Merkliste, filme.py:490 — gleiche Bauform, beim Fix mitnehmen). Wirkung bestaetigt: reihen() (filme.py:500) speist 'Weiterschauen' allein aus katalog_lesen(), position_s stammt ausschliesslich aus Jellyfins PlaybackPositionTicks (Zeile 144/449) — es gibt keinen lokalen Ersatzspeicher, ein verlorener Queue-Eintrag ist endgueltig weg. HERABSTUFUNG blocker -> schwer, weil zwei Teile des Belegs uebertrieben sind: (1) 'Fenster bis 15 s * Anzahl bei haengendem Server' stimmt nicht — haengen die Rufe und scheitern dann, ist geschafft=0 und es wird ueberhaupt nicht geschrieben (gemessen: 8 Eintraege, alle scheitern => Queue-Schreibvorgaenge=0, KEIN Fenster); ein langsam scheiternder Stopp macht den Verlust sogar unwahrscheinlicher, weil das Anhaengen dann erst nach dem Schreiben passiert. (2) Bei leerer Queue ist das Fenster null (gemessen: Dauer 0,00 s, Schreibvorgaenge=0) — die Live-Datei filme_fortschritt_queue.json ist heute '[]', der Fehler schlaeft also und wacht erst nach einem Ausfall auf. Zudem ist mein Versuch gescheitert, einen harmloseren Ausloeser zu finden: die im Code dokumentierte Token-Entwertung (gleiche DeviceId, Fund 05.08.) plus aktive Anmeldesperre ergab 0/5 Verluste, weil das 401 den ersten Eintrag scheitern laesst und damit in den sicheren Zweig fuehrt. Es bleibt eine Vierfach-Bedingung (Queue nicht leer + Abzug laeuft + Stopp im 0,8–6-s-Fenster + Stopp scheitert schnell, waehrend mindestens ein alter Ruf gelingt) — kein Alltagsfall, aber genau die Lage nach einem Ausfall wie dem 403 vom 06.–13.08., wenn die Queue voll ist und der Server beim Wiederanlaufen wackelt. Der Verlust ist still, unumkehrbar und verletzt die Zwei-Fragen-Regel, die dasselbe Modul beim Meta-Cache korrekt anwendet; Behebung ist eine Zeile (fam.json_aendern). Kein Projektcode geaendert, Live-Dateien unberuehrt (Zeitstempel 05.08., git status sauber).

### 14. [SCHWER] Der Sync-Knopf laeuft ohne Sperre — zwei Katalog-Abzuege und zwei Nachreich-Laeufe gleichzeitig, jede Meldung doppelt zu Rene

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/youtube_app.py:5732`

**Beleg:** Code-Lesen: youtube_app.py:5141 (filme_sync_pruefen) startet katalog_abzug UNTER der Sperre _filme_sync_laeuft; youtube_app.py:5732 (/api/filme/sync, der Knopf in der Oberflaeche) startet exakt dieselbe Funktion mit 'threading.Thread(target=filme.katalog_abzug, daemon=True).start()' — ohne jede Sperre. Messung m5_korrektur.py, Abschnitt X: zwei gleichzeitige fortschritt_nachreichen() bei 6 liegengebliebenen Meldungen -> Ausgabe '6 liegengebliebene Meldungen -> 12 POST an Renes Server, 6 davon DOPPELT'.

**Wirkung auf JB:** Klickt JB den Sync-Knopf, waehrend der 6-h-Abzug schon laeuft, laufen zwei Voll-Abzuege parallel gegen fremdes Eigentum — beim heutigen Bestand sind das statt 5 Seiten a 1000 Titeln (11 s) zehn solche Rufe gleichzeitig — und jede liegengebliebene Fortschritts-Meldung geht doppelt raus. Das ist genau das Haemmer-Muster, das am 06.08. in die 403-Sperre gefuehrt hat.

**Urteil des Skeptikers:** Befund reproduziert exakt, Widerlegung gescheitert. Alle Messungen mit gepatchtem _http, nichts live, echte Dateien nachweislich unveraendert (queue mtime 5.8., katalog 4885 Eintraege unangetastet).

STRUKTUR BESTAETIGT: Sperre _filme_sync_laeuft kommt in youtube_app.py nur an 3 Stellen vor (5130 Anlage, 5138 acquire, 5143 release), alle drei in filme_sync_pruefen. Endpunkt /api/filme/sync bei 5732 startet filme.katalog_abzug nackt per threading.Thread. filme.py enthaelt UEBERHAUPT keine Sperre (grep "Lock|threading" -> leer), also kein innerer Schutz.

MESSUNG A (zwei gleichzeitige fortschritt_nachreichen(), 6 Meldungen): "Rueckgabe Lauf A: 6 / Lauf B: 6", "POST an /Playing/Progress: 12", "davon DOPPELT: 6" — Zahl des Pruefers auf den Punkt.
MESSUNG B (zwei gleichzeitige katalog_abzug()): "Items-Seiten-Rufe an Rene: 10 (ein Abzug allein braucht 5)" — wie behauptet.

WIDERLEGUNGS-VERSUCHE ALLE GESCHEITERT: (1) Keine Entprellung in der Oberflaeche — filmeSync() in oberflaeche.py:4254 schickt je Klick ein POST ohne Knopf-Sperre, also rennen sogar zwei Klicks gegeneinander. (2) ThreadingHTTPServer (youtube_app.py:6211) serialisiert nichts, Arbeit laeuft ohnehin im eigenen Thread ausserhalb der Anfrage. (3) Zeitfenster real offen: sync_faellig() liest den "stand", der erst AM ENDE eines Abzugs geschrieben wird — waehrend der Knopf-Abzug laeuft, haelt der Ticker den Sync weiter fuer faellig.

ZWEI KORREKTUREN AN DER DARSTELLUNG:
(a) UEBERZOGEN: Die 403-Kausalitaet ("genau das Haemmer-Muster vom 06.08.") ist NICHT gemessen. Ich habe das 401-Szenario nachgestellt (gleiche DeviceId, Token gegenseitig entwertet): "davon ANMELDUNGEN: 2", beide Abzuege ok:True/4885. neu_angemeldet begrenzt Neuanmeldung auf einmal je Abzug, _sitzung wird geteilt, _anmelde_sperre_ts bremst (600 s bei 403). Also Verdopplung der Last, KEIN eskalierender Sturm. Hauptsitzung darf den 403-Satz nicht als belegt behandeln.
(b) UNTERSCHAETZT: Die doppelten POSTs sind weitgehend idempotent (gleiche Position, gleiche PlayedItems-Markierung). Der echte Schaden derselben Wurzel — Lesen-Aendern-Schreiben auf der Queue ohne Sperre, fam.json_schreiben statt fam.json_aendern — ist DATENVERLUST: legt fortschritt() eine Meldung ab, waehrend fortschritt_nachreichen() sendet, ueberschreibt der Nachreich-Lauf sie. Gemessen: "Queue am Ende: []", "-> NEUER_FILM noch da? NEIN - VERLOREN". Bricht die Zusage im eigenen Docstring ("nichts geht verloren") und JBs Dauerregel fuer geteilten Zustand.

Mess-Skripte: scratchpad\skeptiker_schreibwege.py, skeptiker_401.py, skeptiker_verlust.py

### 15. [MITTEL] Ein dauerhaft abgelehnter Eintrag friert die ganze Warteschlange fuer immer ein

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:869`

**Beleg:** m1_grund.py, Abschnitt B: Queue mit drei Eintraegen, der erste antwortet dauerhaft 404 (Film bei Rene geloescht/ersetzt), die anderen beiden 204. Ausgabe: 'Runde 1: nachgereicht=0, Queue=[GELOESCHT, ad8edbbd8, fe500d27e]' — identisch in Runde 2 und 3, insgesamt nur 3 Netz-Rufe. Grund: Zeile 870 'if rest:' haelt die Reihenfolge, also wird nach dem ersten Fehlschlag KEIN weiterer Eintrag mehr versucht, und ein Eintrag verlaesst die Queue nur bei Erfolg — es gibt weder einen Zaehler fuer Versuche noch eine Alterung (das Feld 'ts' wird nirgends ausgewertet, Vorkommen von "ts" im Modul: 3, alle beim Anlegen).

**Wirkung auf JB:** Ein einziger nicht mehr existierender Film blockiert dauerhaft ALLE spaeteren Fortschritte: sie stapeln sich unbegrenzt hinter ihm und erreichen Renes Server nie mehr. JB merkt es daran, dass 'Weiterschauen' auf seinen anderen Geraeten still einfriert. Anmerkung zur Ehrlichkeit: dass Jellyfin bei unbekannter ItemId wirklich 4xx antwortet, konnte ich nicht pruefen (das waere ein schreibender Ruf); belegt ist der Einfrier-Mechanismus fuer JEDE dauerhafte Ablehnung.

**Urteil des Skeptikers:** ECHT — aber die Schwere ist überzogen und die behauptete Wirkung auf JB ist messbar FALSCH.

## Was ich reproduzieren konnte (eigenes Skript, Netz gepatcht, Renés Server nicht angefasst)

Der Einfrier-Mechanismus stimmt exakt, Zeile für Zeile bestätigt (filme.py:869-877):

Messung A1 — Queue [GELOESCHT(404), GUT-ad8edbb(204), GUT-fe500d2(204)]:
```
Runde 1: nachgereicht=0 netzrufe_diese_runde=1 Queue=['GELOESCHT-bei-Rene', 'GUT-ad8edbb', 'GUT-fe500d2']
Runde 2: nachgereicht=0 netzrufe_diese_runde=1 Queue=[... identisch ...]
Runde 3: nachgereicht=0 netzrufe_diese_runde=1 Queue=[... identisch ...]
Netz-Rufe gesamt: 3 -> ['GELOESCHT-bei-Rene', 'GELOESCHT-bei-Rene', 'GELOESCHT-bei-Rene']
```
Die beiden guten Einträge werden NIE versucht — `if rest:` (Zeile 870) hält die Reihenfolge.

Messung A2 — 203 Runden: `Queue=['GELOESCHT-bei-Rene', 'GUT-ad8edbb', 'GUT-fe500d2'] (Laenge 3)`, insgesamt 203 Netz-Rufe statt 609. Kein Eintrag verlässt die Queue je ohne Erfolg.

Messung A3 — Alterung: `ts` aller Einträge auf 400 Tage alt gesetzt → `Alterung greift: NEIN`. Es gibt weder Versuchszähler noch Verfall; `ts` wird tatsächlich nirgends ausgewertet.

Messung B3 — spätere Ausfälle stapeln sich dahinter und gehen mit unter:
```
Queue nach 5 Ausfall-Meldungen: Laenge=7
Server zurueck, nachreichen -> nachgereicht=0, Queue-Laenge=7
```
Auch `_http` bestätigt die Dauerhaftigkeit: es fängt HTTPError ab und GIBT den Code ZURÜCK (filme.py:82-83), 404 landet also in `return st in (200, 204)` → False, ohne Ausnahme, ohne Sonderbehandlung.

Damit ist die Kernaussage „ein dauerhaft abgelehnter Eintrag friert die Warteschlange für immer ein" belegt. Auch der Docstring-Versprecher in filme.py:849-850 („nichts geht verloren") ist in diesem Fall unwahr.

## Was ich WIDERLEGT habe (deshalb Abstufung schwer → mittel)

1) Die behauptete Wirkung stimmt nicht. Der Prüfer schreibt, JB merke es daran, dass „Weiterschauen auf seinen anderen Geräten still einfriert". Gemessen (B1/B2): NEUE Fortschritte gehen an der Queue komplett vorbei — `fortschritt()` sendet zuerst direkt und hängt nur bei Fehlschlag an:
```
fortschritt('NEU-heute-abend') -> True   Netz-Rufe: ['NEU-heute-abend']
Queue danach: ['GELOESCHT', 'ALT-1']   (unveraendert)
Nach 20 weiteren erfolgreichen Meldungen: Queue-Laenge=2
```
Weiterschauen funktioniert also normal weiter. Betroffen ist AUSSCHLIESSLICH der Rückstau aus Ausfall-Fenstern (verlorene Resume-Positionen von Filmen, die JB bei nicht erreichbarem Server geschaut hat) — ärgerlich, aber kein stiller Totalausfall. Die Queue wächst auch nicht unbegrenzt, solange der Server erreichbar ist.

2) Der vorgeschlagene Auslöser ist vom Server-Vertrag nicht gedeckt. Der Prüfer gibt selbst zu, „404 bei gelöschtem Film" nicht geprüft zu haben. Ich habe es rein LESEND geprüft, direkt an Renés Server (10.11.11) über die OpenAPI-Beschreibung:
```
POST /Sessions/Playing/Progress: Antworten = ['204', '401', '403', '503']
POST /Sessions/Playing:          Antworten = ['204', '401', '403', '503']
POST /Sessions/Playing/Stopped:  Antworten = ['204', '401', '403', '503']
```
Kein 404, kein 400. Zum Vergleich zeigt derselbe Server auf LESENDEN Item-Endpunkten sehr wohl harte Ablehnungen (also liegt es nicht an meiner Messung):
```
GET Items/<echte id>          -> HTTP 200, 18075 Bytes
GET Items/<unbekannte guid>   -> HTTP 404 "Not Found"
GET Items/kein-guid-hier      -> HTTP 400 "The value 'kein-guid-hier' is not valid."
```
Alle vier deklarierten Antworten des Fortschritts-Endpunkts sind ungefährlich: 204 = Erfolg, 401 wird nachweislich geheilt (Code filme.py:827-841, abgedeckt von test_token_invalidiert_einmal_neu_anmelden), 403 und 503 sind serverweit und vorübergehend — sie treffen ALLE Einträge gleich und lösen sich beim nächsten Lauf.

Ehrliche Einschränkung: ein undeklariertes HTTP 500 (Jellyfin stolpert intern über ein gelöschtes Item) würde denselben Einfrier-Effekt auslösen und taucht in der OpenAPI naturgemäß nicht auf. Das kann ich ohne schreibenden Ruf nicht ausschließen — geprüft habe ich es NICHT, weil das Renés Server verändern würde.

3) Kein Live-Befund. JBs echte Queue ist leer: `filme_fortschritt_queue.json` enthält `[]` (Stand 05.08.). Es gibt aktuell keinen steckengebliebenen Eintrag.

## Verdikt

Der Defekt ist echt und billig zu beheben: Die Schleife braucht (a) Überspringen statt Reihenfolge-Halt oder wenigstens (b) einen Versuchszähler und einen Verfall über das bereits geschriebene Feld `ts`. Aber „schwer" wäre für die Hauptsitzung irreführend — es gibt keinen belegten Auslöser, das laufende Weiterschauen ist nachweislich nicht betroffen, und der Schaden beschränkt sich auf Resume-Positionen aus Ausfall-Fenstern. Deshalb: mittel.

Stelle: C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:869-877 (Reihenfolge-Halt + fehlender Verfall), Kontext filme.py:849-860 (`fortschritt`) und filme.py:82-83 (`_http` gibt Fehlercodes zurück, statt zu werfen).

### 16. [MITTEL] Merkliste: gleichzeitige Klicks loeschen sich gegenseitig — ein ganzes Profil kann verschwinden

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:490`

**Beleg:** m6_merk_rate.py mit echten Katalog-IDs, je 20 Durchlaeufe. (A) 4 Herzen mit 5 ms Klickabstand: 1 von 20 Durchlaeufen verliert ein Herz. (B) 4 Herzen ohne Abstand (vier parallele fetch, ThreadingHTTPServer bedient sie echt parallel): '20 von 20 Durchlaeufen mit Verlust, insgesamt 60 von 80 Klicks weg' — jedes Mal genau 3 von 4. (C) PC-Profil und Kinder-Profil gleichzeitig: 'in 20 von 20 Durchlaeufen fehlte ein ganzes PROFIL in der Datei' (Ausgabe m2: Datei danach {'kinder': 1}). (D) Gegenprobe sequentiell: 4 von 4 gespeichert. Ursache: merkliste_toggle liest die Datei in Zeile 476, aendert und schreibt in Zeile 490 mit fam.json_schreiben — die ganze Datei, alle Profile, ohne Sperre.

**Wirkung auf JB:** Zwei Geraete (PC und Fernseh-/Handy-Profil), die im selben Moment ein Herz setzen, koennen die komplette Merkliste des jeweils anderen Profils ausloeschen — nicht einen Eintrag, sondern den ganzen Schluessel. Ohne Rueckweg, denn die Merkliste ist rein lokal und wird nirgends gespiegelt.

**Urteil des Skeptikers:** ECHT im Kern, aber die behauptete Wirkung ist widerlegt — deshalb Schwere von "schwer" auf "mittel" korrigiert.

WAS ICH REPRODUZIEREN KONNTE (eigene Messung, nicht die des anderen Prüfers)

Der verlorene Schreibvorgang ist real und überlebt den echten Netzweg. Ich habe einen ThreadingHTTPServer mit derselben Handler-Voreinstellung wie die App gebaut (youtube_app.py:6211 nutzt ThreadingHTTPServer; `protocol_version` ist NIRGENDS gesetzt, also HTTP/1.0 ohne keep-alive — jede Anfrage bekommt einen eigenen Thread, eine Serialisierung über die Verbindung gibt es also nicht) und darüber echte POSTs auf die echte `filme.merkliste_toggle` geschickt, mit echten Katalog-IDs:

  4 Herzen, ein Profil, über echtes HTTP:
    Abstand   0 ms: 20/20 Runden mit Verlust,  57/80 Klicks weg
    Abstand   1 ms:  6/20 Runden mit Verlust,   6/80 Klicks weg
    Abstand   5 ms:  4/20 Runden mit Verlust,   4/80 Klicks weg
    Abstand  20 ms:  0/20                        0/80
    Abstand  50/100 ms: 0/20                     0/80

Ohne künstliche Barriere, nur mit gleichzeitigem Start, direkt auf der Funktion: 30/30 Runden mit Verlust, 90/120 Klicks weg. Die Ursache steht wie behauptet in filme.py: Lesen in Zeile 476, Schreiben in Zeile 490 über `fam.json_schreiben` — die ganze Datei, ohne Sperre. Das Zeitfenster Lesen→Schreiben habe ich gemessen: Median 1,04 ms (Lesen 0,53 / Schreiben 0,51 ms). Genau das ist die Kollisionsbreite, und sie deckt sich exakt mit dem Verlaufen der Verlustrate zwischen 5 und 20 ms. Die Familie hat für genau diesen Fall bereits das Werkzeug `fam.json_aendern` (familie.py:121, dort mit der Messung "5 von 8 Einträgen waren am Ende weg" begründet) — `merkliste_toggle` ist der einzige Schreiber der Datei und nutzt es nicht. Das ist ein handfester Verstoß gegen die Dauerregel "Kann eine Änderung verloren gehen? → json_aendern".

WAS ICH WIDERLEGT HABE (die behauptete Wirkung auf JB)

Die Aussage "kann die komplette Merkliste des jeweils anderen Profils auslöschen — nicht einen Eintrag, sondern den ganzen Schlüssel" ist FALSCH. Gegentest mit maximalem Gleichzeitigkeitsdruck, 200 Runden: Kinder-Profil mit 8 bestehenden Einträgen, dazu 4 parallele PC-Klicks:
    Kinder-Profil ganz weg:        0/200
    Kinder-Profil teilweise weg:   0/200
    PC-Klicks verloren:          600/800
    Datei ungültig (kaputtes JSON): 0/200

Ein bestehendes Profil geht nie verloren, weil beide Schreiber denselben Grundstand lesen und ihn mitschreiben. Der "ganze Schlüssel verschwindet" nur in einem einzigen Sonderfall: wenn das Profil in genau derselben Millisekunde ERSTMALIG angelegt wird — dann ist der verlorene Schlüssel identisch mit dem einen verlorenen Klick. Belegt: bei etabliertem PC-Profil (8 Einträge) und brandneuem Kinder-Klick ging 90/200 mal der neue Kinder-Eintrag verloren, der PC-Bestand von 8 Einträgen aber kein einziges Mal. Der Prüfer hat mit LEERER Datei gemessen; sein Ergebnis {'kinder': 1} zeigt nicht den Verlust eines Profils, sondern den Verlust eines einzelnen Klicks, der zufällig der erste war.

Zusätzlich widerlegt: Datenverfall gibt es nicht. Die Datei war in 400 Läufen nie ungültiges JSON — der atomare Schreibweg (eigener tmp-Name je Thread) hält. Es geht ausschließlich der zuletzt gelesene Stand verloren, nie ein halber.

WARUM TROTZDEM ECHT UND WARUM NUR "MITTEL"

Echt, weil der Schaden still ist: die Oberfläche (oberflaeche.py:8126, `tvMerk`) meldet nach dem 200er unbeirrt "Auf deiner Liste", während der Eintrag in der Datei fehlt — JB merkt es erst, wenn das Herz später weg ist. Und die Merkliste ist rein lokal, es gibt keinen Rückweg.

Nur "mittel", weil der maximale Schaden genau EIN Herz je Kollision ist, kein Bestand und keine Liste; weil die Oberfläche pro Klick genau eine Anfrage abschickt (kein Weg feuert mehrere parallel), also zwei Geräte innerhalb von ~1–5 ms treffen müssen — ab 20 ms Abstand 0 Verluste in 80 Klicks; und weil JBs echte Datei heute `[]` ist, also noch nichts zu verlieren hat. Ein "schwer"/"blocker" wäre gerechtfertigt bei Verlust bestehender Daten oder kaputter Datei — beides habe ich in 400 Läufen nicht erzeugen können.

FIX-RICHTUNG FÜR DIE HAUPTSITZUNG (ich habe nichts geändert): filme.py:470–490 auf `fam.json_aendern(_pfade["merk"], aenderung)` umstellen; das Ergebnis "ist jetzt gemerkt" muss aus der Änderungsfunktion herauskommen, und der Fall "Sperre nicht bekommen" (Rückgabe None) muss ehrlich als Fehlschlag an die Oberfläche gehen, statt einen Erfolgs-Toast zu zeigen.

Geprüfte Stellen: C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:457-491 · youtube_app.py:5748 (Route, ohne Sperre) · youtube_app.py:6211 (ThreadingHTTPServer) · familie.py:74-121 (json_schreiben / json_aendern) · oberflaeche.py:8126 (tvMerk). Messskripte im Scratchpad: C:/Users/janbe/AppData/Local/Temp/claude/C--Users-janbe-Downloads-Jan-Bernd-Claude/a63d3cd1-fd37-4614-9f47-4b975e55a173/scratchpad/skeptiker_merk.py, skeptiker_http.py, skeptiker_schwere.py. Alle Messungen liefen in einem Scratch-Ordner; JBs echte filme_merkliste.json ist unverändert (Zeitstempel 05.08. 22:56, Inhalt `[]`), es gab keinen Ruf an Renés Server.

### 17. [SCHWER] esc() ist nicht attribut-sicher — ein echter Serientitel mit Anführungszeichen zerlegt das HTML-Tag

**Stelle:** `SyncYouTube/System/oberflaeche.py:3861`

**Beleg:** esc() (oberflaeche.py:2051) setzt textContent und liest innerHTML zurück — das maskiert nur & < > , NICHT das Anführungszeichen. Der Katalog enthält genau einen solchen Titel: 'Der Fall "Air Cocaine" - Schmuggler in 10000 Meter Höhe' (id 5d2a6bb2ea…, typ serie) — und er steckt in /api/filme/reihen (offline geprüft: in_reihen True). Die erzeugte Zeile lautet: <div class="f-kachel" onclick="tvInfo('5d2a…')" title="Der Fall "Air Cocaine" - Schmuggler in 10000 Meter Höhe (2025)">. Durch html.parser gejagt: Parser sieht <div> mit 12 Attributen statt 3 — class='f-kachel', onclick=…, title='Der Fall ', dann air=None, cocaine"=None, -=None, schmuggler=None, in=None, 10000=None, meter=None, höhe=None, (2025)"=None. Dasselbe ungeschützte Muster in der TV-Info-Seite: Zeile 8200 title="${esc(e.titel)}" (Folgentitel) und 8208 title="${esc(t.name)}" (Trailer-Namen) — in meiner Stichprobe von 205 echten Folgen kam kein " vor, die Stelle ist aber unbewacht.

**Wirkung auf JB:** JB sieht im 🎬-Filme-Fenster bei dieser Serie nur den Tooltip 'Der Fall ' und einen kaputten DOM-Knoten. Schwerer wiegt das Muster: Titel kommen von Renés Server, sind also fremde Daten. Ein Titel mit " und einem onerror=/onmouseover=-Anhang würde ab da beliebiges JavaScript in JBs Oberfläche ausführen. Ein attribut-sicheres escAttr() (zusätzlich " und ' ersetzen) schließt beide Löcher.

**Urteil des Skeptikers:** Bestaetigt — ich habe versucht, den Befund zu kippen, und bin an jeder Stelle gescheitert. Alle vier moeglichen Widerlegungen habe ich einzeln gemessen und alle vier fallen aus.

1) esc() maskiert das Anfuehrungszeichen wirklich nicht — im ECHTEN Browser gemessen, nicht theoretisch hergeleitet. Ich habe die Zeile oberflaeche.py:2051 woertlich (per Python-Stringvergleich als 1:1-identisch nachgewiesen) in eine Messseite kopiert und ueber einen lokalen Static-Server im Browser-Pane ausgefuehrt:
   esc('a"b')   = 'a"b'        (Anfuehrungszeichen bleibt roh)
   esc("a'b")   = "a'b"        (Hochkomma bleibt roh)
   esc('a&<>b') = 'a&amp;&lt;&gt;b'   (nur diese drei werden maskiert)
Das ist korrektes Textknoten-Serialisieren von innerHTML — und damit textsicher, aber eben nicht attributsicher.

2) Der Titel existiert und ist genau einer. Ueber alle 4885 Katalog-Eintraege: exakt 1 Titel mit ", naemlich 'Der Fall "Air Cocaine" - Schmuggler in 10000 Meter Hoehe' (typ serie, id 5d2a6bb2ea…, jahr 2025, rating 8.1, fsk TV-14). Zusaetzlich 100 Titel mit einfachem Hochkomma (Carlito's Way, Bob's Burgers, Bram Stoker's Dracula …) — die sind im title-Attribut ungefaehrlich, weil das Attribut doppelt gequotet ist, waeren aber im gleichen Muster bei einfach gequoteten Attributen sofort toedlich.

3) Der Eintrag erreicht die Anzeige wirklich — die Reihen-Kette laeuft, kein toter Pfad. filme.reihen() offline gefahren (fuer den Test _http hart abgeklemmt, kein Ruf an Renes Server): der Eintrag liegt in genres/Documentary an Index 37, also weit innerhalb der 100er-Deckelung — er wird ausgeliefert. Und filmeLaden() ist lebendiger Code, nicht Altlast: Aufruf in oberflaeche.py:2494, sobald das Filme-Fenster aktiv ist, plus oberflaeche.py:4256 acht Sekunden nach jedem Abgleich. Die Reihe Documentary wird ueber .concat(Object.entries(d.genres)) mitgerendert.

4) Der Browser zerlegt das Tag tatsaechlich. Exakt die Zeilen 3861-3863 (nach Zeilenumbruch-Normierung als identisch zur Quelle verifiziert) mit dem echten Eintrag durch innerHTML gejagt, dann das reale DOM ausgelesen:
   Attributzahl: 15 statt 3
   Attribute: class="f-kachel", onclick="tvInfo('5d2a…')", title="Der Fall ", air="", cocaine"="", -="", schmuggler="", in="", 10000="", meter="", hoehe="", (2025)="", ·="", ★8.1="", tv-14"=""
   title-Wert, den JB als Tooltip sieht: "Der Fall "  (statt 'Der Fall "Air Cocaine" - Schmuggler in 10000 Meter Hoehe (2025) · ★8.1 · TV-14')

KORREKTUR am Beleg des Pruefers (Substanz unberuehrt): er nennt 12 Attribute, gemessen sind es 15. Er hatte in seiner erzeugten Zeile den Rating-/FSK-Anhang weggelassen; die drei Zusatz-Truemmer ·, ★8.1 und tv-14" kommen noch dazu. Der Kern — Tag zerlegt, Tooltip auf 'Der Fall ' abgeschnitten — stimmt exakt.

PRAEZISIERUNG bei der Wirkung, in beide Richtungen: der sichtbare Schaden heute ist kleiner als "kaputter DOM-Knoten" klingt. Der Kachel-Titel .f-ktitel steht korrekt und vollstaendig da (Textknoten, dort greift esc() richtig), das <img> bleibt innerhalb der Kachel, die Kachel klappt nicht zusammen. Kaputt ist nur der Tooltip — bei 1 von 4885 Eintraegen.

Schwer wird es durch die zweite Haelfte, und die habe ich als Gegenprobe scharf gemessen, nicht behauptet: es ist echte Attribut-Injektion, nicht blosses Abschneiden. Mit dem synthetischen Titel Kino" onmouseover="…" x=" baut der Browser ein echtes onmouseover-Attribut (hasAttribute('onmouseover') === true), und ein dispatchtes mouseover fuehrt den Code aus — meine Testvariable sprang von "nicht ausgeloest" auf "JS AUSGEFUEHRT". Es gibt weder eine Content-Security-Policy im Programm noch einen attributsicheren Helfer (grep nach Content-Security-Policy / escAttr / escApos: null Treffer), also bremst nichts. Titel sind Fremddaten von Renes Server, letztlich aus TMDB-Scraping, wo Dritte Titel editieren koennen. Damit bleibt "schwer" richtig.

Dasselbe ungeschuetzte Muster steckt an sieben weiteren Stellen: 3696, 4279, 6309, 6310, 6344 (lokale Bibliothek) und 8200/8208 (Folgentitel und Trailer-Namen, ebenfalls Renes Daten). Die TV-Hauptkacheln bei 7921 sind sauber — die setzen gar kein title-Attribut.

Reproduktion: Testseiten in C:\Users\janbe\AppData\Local\Temp\claude\C--Users-janbe-Downloads-Jan-Bernd-Claude\a63d3cd1-fd37-4614-9f47-4b975e55a173\scratchpad\messung.html und quelltreu2.html; Fundstellen C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\oberflaeche.py:2051 (esc), :3861 (Filme-Kachel), :8200 und :8208 (TV-Info).

### 18. [SCHWER] Die TV-Suche findet nur 1964 von 4885 Titeln — 60 % des Katalogs sind über 🔍 unauffindbar

**Stelle:** `SyncYouTube/System/oberflaeche.py:7850`

**Beleg:** tvReihenFuer() baut den Such-Korpus im Tab 'suche' aus [...f.top, ...f.neu, ...Object.values(f.genres)] — nicht aus tvKatalog. Offline nachgerechnet über die echten reihen(): top 30 + neu 20 + 50 Genre-Reihen à höchstens 100 (Deckel in filme.py:557) ergeben dedupliziert 1964 Einträge; 2921 Titel fehlen. Gegenprobe mit echten Suchwörtern: 'matrix' → TV-Suche findet 1 von 4 im Katalog, 'tatort' → 0 von 1, 'herr der ringe' → 4 von 4. Unauffindbar sind z. B. 'Angst essen Seele auf', 'Arctic', 'Armand', 'Auf der anderen Seite'. Die Variable tvKatalog wird nur in den Tabs 'filme'/'serien' überhaupt geladen (Zeile 7823).

**Wirkung auf JB:** JB tippt vom Sofa aus einen Film, den René nachweislich hat, und bekommt 'Hier ist noch nichts' — die naheliegende Reaktion ist, ihn über Jellyseerr nochmal zu wünschen, obwohl er längst auf dem Server liegt. Fix ist klein: im Such-Tab tvKatalog laden und darüber filtern (der Katalog liegt ohnehin schon im Browser, sobald man einmal im Filme-Tab war).

**Urteil des Skeptikers:** Unabhaengig reproduziert, Zahl fuer Zahl identisch. Messweg: youtube_app.py:5386 reicht /api/filme/reihen unveraendert aus filme.reihen() durch, also ist der Browser-Zustand tvFilmReihen exakt offline nachrechenbar. filme.reihen() gegen die echten 4885 Eintraege gelaufen, _http vorher auf (599,'') gepatcht (garantiert kein Ruf an Rene/TMDB). Ergebnis: top 30, neu 20, genres 50 (alle bei 100 gedeckelt, filme.py:557), weiterschauen 3, merkliste 0. Such-Korpus wie in oberflaeche.py:7850 gebildet ([...top, ...neu, ...Object.values(genres)], Dedup nach id): roh 3189 -> dedupliziert 1964. Katalog 4885, fehlend 2921 = 59,8 % (2552 Filme, 369 Serien). tvKatalog kommt im Such-Zweig nicht vor und wird nur in Zeile 7823 (Tabs filme/serien) geladen. Wort-Gegenprobe mit dem echten JS-Filter (titel.lower().includes(q)): 'matrix' 1 von 4, 'tatort' 0 von 1, 'herr der ringe' 4 von 4, 'arctic' 0 von 1 - alle vier Prueferwerte bestaetigt; zusaetzlich staerker: 'james bond' 0 von 25. Weitere Unauffindbare: Ferris macht Blau, Vergessene Welt: Jurassic Park, Shape of Water, Die Goetter muessen verrueckt sein. ZWEI KORREKTUREN an der Beschreibung, die den Befund nicht kippen: (1) Die behauptete Meldung 'Hier ist noch nichts' erscheint im Such-Tab NICHT - oberflaeche.py:7901 unterdrueckt sie dort ((tvTab==='suche'?'':...)); JB sieht ein leeres Suchfeld ohne jede Erklaerung und ohne Hinweis, dass Enter den Gesamtkatalog abfragt (dieser Hinweis steht nur im Titel der Wunsch-Reihe, die erst NACH dem Enter erscheint). (2) Versehentliches Nachwuenschen ist gedaempft: seerr_suche (filme.py:713) uebernimmt mediaInfo.status, tvAnfrage blockt Status 'da'. Der Weg endet aber in einer Sackgasse - die Meldung lautet '✔ Gibt es schon - such den Titel im Katalog', also genau die Suche, die den Titel nicht findet. Schwere bleibt 'schwer', kein Blocker: das A-Z-Raster in den Tabs Filme/Serien listet den ganzen Katalog, die Titel sind also erreichbar, nur nicht suchbar - vom Sofa mit Fernbedienung durch 3967 Kacheln zu blaettern ist jedoch kein Ersatz. Kein Code geaendert, kein Ruf an Renes Server.

### 19. [SCHWER] Der Filme-Tab baut 6128 Kacheln in EINEM innerHTML — 2,15 MB HTML und 6128 Bild-Rufe

**Stelle:** `SyncYouTube/System/oberflaeche.py:7826`

**Beleg:** Mit den echten Zahlen nachgerechnet: Tab 'filme' liefert 44 Reihen — Top 10 + 42 Genre-Reihen (auf Filme gefiltert, z. B. Drama 78, Action 83, Thriller 84) + das A–Z-Raster mit 3967 Kacheln. Kacheln gesamt 6128, jede mit einem <img loading="lazy" src="/api/filme/bild?id=…"> plus dreistufiger onerror-Kette. Allein die A–Z-Zeichenkette misst 2 153 591 Zeichen = 2,15 MB (Tab 'serien': 918 Kacheln, 0,49 MB). Dazu holt tvKatalogLaden (7766) /api/filme/katalog, das in youtube_app.py:5385 den vollständigen katalog_lesen() zurückgibt — 2,43 MB. Scrollhöhe des Rasters aus der CSS-Regel (Zeile 192, width:calc((100vw-152px)/6), 16:9-Bild, 2 Titelzeilen): bei 1920 px 662 Rasterzeilen à ~212 px ≈ 140 000 px, also ~130 Bildschirmhöhen; bei 760 px Breite ~218 000 px. Es gibt keine A–Z-Sprungnavigation. Zusätzlich stehen 1396 Filme mehrfach im selben DOM (Maximum 6×, z. B. 'The 6th Day', 'Alles steht Kopf'), weil sie in mehreren Genre-Reihen auftauchen.

**Wirkung auf JB:** Der Filme-Tab ist die Stelle, an der JBs Anti-Scroll-Regel bricht — nicht ein bisschen, sondern um zwei Größenordnungen. Bis 'Zwielicht' sind es 130 Bildschirme. Vorschlag (unbestätigt, gehört JB zur Entscheidung): A–Z in Buchstaben-Blöcke schneiden und nur den gewählten Buchstaben rendern, oder das Raster stückweise nachladen.

**Urteil des Skeptikers:** Reproduziert, unabhaengig gemessen — Befund haelt stand. Nachbau der exakten tvMalen()-Zeichenkette (oberflaeche.py:7904) gegen den echten Katalog, mit filme.reihen() offline (_http und fam.json_schreiben/json_aendern gesperrt, kein Ruf an Renes Server), danach im echten Browser gerendert.

BESTAETIGT: Tab 'filme' = 44 Reihen (Top 10 + 42 Genre + A-Z), 6128 Kacheln, 6128 <img> (im Live-DOM nachgezaehlt: reihen 44, kachelnGesamt 6128, imgGesamt 6128); Genre-Zahlen Drama 78 / Action 83 / Thriller 84 identisch; A-Z-Raster 3967 Kacheln; Serien-Tab 918 Kacheln / 495056 Zeichen; 1396 IDs mehrfach im DOM, max 6x, Spitzenreiter 'The 6th Day' und 'Alles steht Kopf' — exakt wie behauptet; EINE einzige innerHTML-Zuweisung (oberflaeche.py:7904); keine A-Z-Sprungnavigation, kein content-visibility, kein IntersectionObserver (grep negativ).

DREI KORREKTUREN AN DEN ZAHLEN DES PRUEFERS:
1) HTML-Menge groesser als in der Ueberschrift: A-Z-Reihe 2161812 Zeichen (Pruefer 2153591, 0,4% daneben), aber die GESAMTE Zuweisung ist 3344686 Zeichen = 3,19 MiB bei 18665 DOM-Knoten. Zusaetzlich malt der Tab ZWEIMAL: tvReihenFuer gibt bei tvKatalog===null erst nur den Kopf zurueck (1,13 MiB / 2161 Kacheln), holt den Katalog und wirft dieses DOM fuer die 3,19 MiB weg.
2) Katalog-Nutzlast ist 1991043 Bytes = 1,90 MiB, NICHT 2,43 MB. Der Pruefer hat die eingerueckte Dateigroesse von filme_katalog.json (2434605 B) genommen; _antwort serialisiert neu mit json.dumps(ensure_ascii=False) — 22% kleiner als behauptet.
3) '6128 Bild-Rufe' ist unpraezise: alle 6128 <img> tragen loading="lazy" (DOM: mitLazy 6128), der Browser feuert beim Anstrich also nicht 6128 Requests, sondern laedt beim Scrollen nach. Umgekehrt kann die Summe 6128 UEBERSTEIGEN: alle 6128 tragen die dreistufige onerror-Kette (dreistufigeKette 6128), also bis zu 3 Rufe je Kachel ohne Thumb — und die gehen an Renes Server.

SCROLLHOEHE IST SCHLIMMER ALS BEHAUPTET: Der Pruef-Browser meldet innerWidth 0 (bekannte Falle, dort kam proZeile faelschlich als 1 heraus), darum viewport-freie Geometrie-Probe mit allen Massen in px 1:1 aus oberflaeche.py (Zeile 46 box-sizing:border-box, 173 padding 6/48/40, 174/175 gap 8 + padding 6/8/10, 176 border 3 + padding 3, 196 aspect-ratio 16/9, 200/253 Titel min-height 2.6em bei 15px). Gemessen: 1920px -> 6 pro Zeile, 662 Rasterzeilen x 224px = 148288 px = 148 Bildschirme (Pruefer ~140000 px / ~130); 1366px -> 5 pro Zeile, 794 Zeilen = 156418 px; 760px -> 3 pro Zeile, 1323 Zeilen = 235494 px = 235 Bildschirme (Pruefer ~218000). Die 43 Bandreihen kommen obendrauf. Der Pruefer hat konservativ gerechnet, nicht uebertrieben.

Zeitmass nur als Untergrenze (Layout im Pane entartet): innerHTML-Zuweisung 79,5 ms, Layout danach 74,3 ms — schon ohne echte Bilder ~150 ms blockierter Hauptthread.

SCHWERE: bleibt 'schwer'. Kein Absturz, kein Datenverlust — aber JBs Anti-Scroll-Regel bricht um zwei Groessenordnungen, und das zeigt sich erst mit den echten 3967 Filmen; mit einer 3-Eintrag-Attrappe waere es nie aufgefallen. Kein Blocker, weil der Tab funktioniert und nichts kaputtgeht.

### 20. [SCHWER] Der Ausfall ist fuer JB komplett unsichtbar — kein Log, kein Status, keine Anzeige

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/youtube_app.py:5133`

**Beleg:** filme_sync_pruefen() verwirft den Rueckgabewert von katalog_abzug(). Gemessener Lauf mit einem Abzug, der {'ok': False, 'fehler': 'Items-Abruf HTTP 403'} liefert: "Fall 1 abzug gerufen: 1 / stdout: '' / stderr: '' / yt_status.json angefasst: False". grep nach print|_sag|logging|status_schreiben|toast|warn in filme.py: KEIN Treffer (878 Zeilen ohne eine einzige Meldung). SyncYouTube ist das einzige Sync-Programm ohne System/status.json (12 andere haben eine: SyncBackup, SyncBelege, SyncCloud, SyncDashTray, SyncDocs, SyncFinanzen, SyncFindus, SyncFotos, SyncIdeen, SyncKontakte, SyncMail, SyncManga). Die Dashboard-Karte liest laut dashboard.py:43-44 nur yt_status.json (Download-Zaehler) und geladen_log.json — nichts ueber Filme. Einzige Spur des Ausfalls auf der Platte: filme_meta_cache.json hat 14 Detail-Abrufe am 06.08., 1 am 12.08., nichts dazwischen, omdb_tag eingefroren auf 2026-08-06; Bilder-Cache: 535 Dateien am 06.08., 15 am 07.08., 0 am 08.-11.08.

**Wirkung auf JB:** Genau das ist der Grund, warum 7 Tage niemandem auffielen. Der Spiegel zeichnet weiter, die Poster kommen aus dem Platten-Cache, nur 'Neu auf dem Server' waechst still nicht mehr. Es gibt keinen Kanal, ueber den das Programm JB von einem Ausfall erzaehlen KOENNTE — auch nicht Tray oder Dashboard.

**Urteil des Skeptikers:** Reproduziert, nicht widerlegt. Eigene Messung mit gepatchtem filme._http (403 auf Items-Abruf, kein Netz-Ruf an Renes Server): katalog_abzug() liefert {'ok': False, 'anzahl': 0, 'fehler': 'Items-Abruf HTTP 403'}, dabei stdout='' , stderr='', 0 geaenderte Dateien, keine status.json. Ueber die echte Aufrufstelle youtube_app.filme_sync_pruefen() gemessen: 'Abzug gerufen: 1 / stdout: "" / stderr: "" / Dateien geaendert: [] / _sag-Meldungen: []'. youtube_app.py:5141 ruft filme.katalog_abzug() ohne Zuweisung; die Ticker-Kapsel (youtube_app.py:5196) faengt nur AUSNAHMEN — Gegenprobe: laesst man den Abzug werfen, erscheint ein Traceback auf stderr, der 403-Weg gibt aber ein Dict zurueck und wirft nie. Normalstart ist pythonw.exe (SyncYouTube.bat), also ohne Konsole: auch dieser Traceback erreichte niemanden. grep -E "print\(|_sag|logging|status_schreiben|toast|warn" filme.py liefert Exit 1 (kein Treffer, 878 Zeilen). SyncYouTube/System/status.json existiert nicht (12 andere Programme haben eine); yt_status.json enthaelt gemessen nur stand/zaehler.fertig/letzte_datei; das In-App-Log speist sich ausschliesslich aus der Download-Warteschlange (oberflaeche.py:3459 logDiff). Der Programm-Kanon greift nicht: die Status-Regel (programm_kanon.py:431) gilt nur "if programm in im_tray_rhythmus()", SyncYouTube laeuft nicht ueber SYNC_SCRIPTS. ZUSATZBEFUND ueber die Behauptung hinaus: youtube_app.py:5731-5733 beantwortet den MANUELLEN Abzug sofort mit {"gestartet": True}, die Oberflaeche meldet toast('Katalog-Abzug gestartet') (oberflaeche.py:4255) — JB haette waehrend der Sperre auf "Abgleichen" druecken koennen und eine Erfolgsmeldung erhalten. Ausserdem prueft tests/test_filme.py:88 genau den Rueckgabewert (r["ok"] is False), den die Produktion wegwirft. Platten-Spuren bestaetigt: Detail-Abrufe je Tag {06.08.: 14, 12.08.: 1, 13.08.: 2}, omdb_tag eingefroren 2026-08-06, Bilder-Cache {05.08.: 76, 06.08.: 535, 07.08.: 15, 12.08.: 33, 13.08.: 24} — 08.-11.08. fehlt vollstaendig. ZWEI KORREKTUREN: (1) "keine Anzeige" ist zu absolut — es existiert genau ein Kanal: oberflaeche.py:1892 <span id="filme-stand" class="hinweis">, gefuellt in oberflaeche.py:3856 mit "Stand <Datum> · Server <Version>"; waehrend der Sperre haette dort "Stand 06.08.2026" gestanden. Das ist keine Fehlermeldung, sondern ein passives Datum in 11,5px Grau (.hinweis #6a5c52, oberflaeche.py:788) und existiert NUR in der alten Filme-Karte, nicht im Fernsehmodus (tvKatalogLaden, oberflaeche.py:7765, zeigt keinen Stand). Der Satz "es gibt keinen Kanal, ueber den das Programm JB erzaehlen KOENNTE" ist damit falsch, der Kern des Befundes bleibt. (2) Schwere blocker -> schwer: die Kette lief weiter, der alte Spiegel blieb unversehrt (spec-konform), nichts ging verloren, und die Selbstheilung (30-min-Backoff + 6-h-Takt) hat den Abzug heute ohne Eingriff wieder durchgebracht (Katalog-Stand 13.08. 18:33, 4885 Eintraege). Beobachtbarkeits-Defekt mit sieben Tagen belegter Blindheit — schwer, aber weder Funktion noch Daten blockierend.

### 21. [MITTEL] Fernsehmodus zeigt den Katalog-Stand gar nicht, der Filme-Tab nur als graues Datum ohne Alterswarnung

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/oberflaeche.py:3855`

**Beleg:** Einzige Stelle: filmeLaden() setzt #filme-stand auf 'Stand '+Datum+' · Server '+Version (oberflaeche.py:1892 span class="hinweis", 3854-3856) — reiner Text, keine Schwelle, keine Farbe. Der Fernsehmodus laedt ueber tvKatalogLaden() (oberflaeche.py:7766) NUR .eintraege und zeigt keinen Stand. Bei 7 Tagen Sperre haette dort 'Stand 06.08.2026, 13:45' gestanden — im TV gar nichts.

**Wirkung auf JB:** JB sieht im Fernsehmodus eine vollstaendig normale Netflix-Oberflaeche, waehrend der Spiegel eine Woche alt ist. Ein alter Spiegel sieht exakt aus wie ein frischer.

**Urteil des Skeptikers:** Reproduziert, nicht widerlegbar. Messung mit den VERBATIM aus oberflaeche.py extrahierten Stellen gegen die echten 4885 Eintraege (Harness scratchpad/messung.mjs, node): Der Filme-Tab rendert fuer frisch / 7 Tage / 90 Tage exakt dasselbe Format — "Stand 13.8.2026, 18:33:32 · Server 10.11.11" vs. "Stand 6.8.2026, …" vs. "Stand 15.5.2026, …" — die Zeile oberflaeche.py:3856 prueft nur `kat.stand` auf Wahrheitswert, kennt keine Alters-Schwelle; die Klasse bleibt `hinweis` (CSS oberflaeche.py:788, color:#6a5c52, unveraendert grau). Der Fernsehmodus: tvKatalogLaden (oberflaeche.py:7765) liefert bei einer Serverantwort mit den Feldern ["stand","server_version","eintraege"] ein reines Array — tvKatalog.length=4885, tvKatalog.stand=undefined, tvKatalog.server_version=undefined. Stand wird also verworfen. Gegenprobe auf alternative Anzeigewege, alle negativ: filme.reihen() gibt nur weiterschauen/top/neu/genres/merkliste zurueck (filme.py:561), keinen Stand; yt_status.json enthaelt nur Download-Zaehler (gelesen: stand/zaehler/letzte_datei), kein Film-Feld; der 6-h-Ticker verwirft das Abzugs-Ergebnis (youtube_app.py:5141), und /api/filme/sync antwortet immer {"gestartet": True} (youtube_app.py:5732), so dass auch der Handknopf einen Fehlschlag nicht melden kann. Das Muster fehlt also wirklich, obwohl die App es andernorts hat (orangefarbener Hinweis oberflaeche.py:9848). Schwere von blocker auf mittel korrigiert: kein Datenverlust, kein Absturz, keine Fehlhandlung. katalog_abzug() laesst den alten Spiegel bewusst stehen (Docstring filme.py:148 "Ausfall-Verhalten laut Spec"), der 6-h-Ticker mit 30-min-Backoff (filme.sync_faellig, filme.py:214) heilt selbst — heute live belegt, 4885 Eintraege nach 7 Tagen Sperre. Der Filme-Tab zeigt das Datum immerhin, und ein wirklich toter Server faellt spaetestens beim Abspielen auf (503 "Jellyfin nicht erreichbar", youtube_app.py:5737). Fehlend ist eine Warn-Schwelle plus Anzeige im TV-Kopf, nicht ein Datenweg.

### 22. [KLEIN] Ein Absturz im Abzug-Thread umgeht die sorgfaeltige Ticker-Kapsel

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/youtube_app.py:5138`

**Beleg:** filme_sync_pruefen startet einen daemon-Thread; das try/except der ticker_schleife (Zeile 5196-5199, 'Ticker-Aufgabe {name}: ...') umschliesst nur das STARTEN. Gemessen mit einem katalog_abzug, das RuntimeError wirft: stdout '', kein 'Ticker-Aufgabe filme'-Text, stattdessen stderr "Exception in thread Thread-2 (lauf): Traceback ...". Start laut SyncYouTube.bat: start "" ...pythonw.exe — ohne Konsole; _sag() (youtube_app.py:6076) prueft selbst auf sys.stdout is None.

**Wirkung auf JB:** Die Lehre aus dem 07.08.-Fund ('ein Herzschlag darf nie an einem einzelnen Schlag sterben') greift fuer den Film-Abzug nicht: der Takt lebt zwar weiter, aber der Fehler landet in einem Thread-Traceback, den unter pythonw niemand je sieht.

**Urteil des Skeptikers:** Mechanismus reproduziert, behauptete Wirkung widerlegt.

REPRODUZIERT (Test A, echte unveraenderte ticker_schleife im --testmodus, nur filme.katalog_abzug wirft RuntimeError): stdout = '', "Ticker-Aufgabe filme" im Ausgabestrom = False, stderr = 'Exception in thread Thread-2 (lauf): Traceback ...'. Gegenprobe Test B (Ausnahme SYNCHRON vor dem Thread-Start): stdout = 'Ticker-Aufgabe filme: PROBE-B: synchron geplatzt' — die Kapsel greift auf dem synchronen Weg und wird auf dem Thread-Weg tatsaechlich umgangen. Struktur bestaetigt: youtube_app.py:5138-5145, lauf() hat nur try/finally, kein except; das try/except der Schleife (5195-5199) umschliesst nur das Starten.

WIDERLEGT — die behauptete Wirkung ("Lehre vom 07.08. greift nicht", "Fehler den niemand je sieht") haelt drei Messungen nicht stand:
1. Der Takt stirbt nicht: t.is_alive() == True nach dem Absturz. Die 07.08.-Lehre zielt auf das Sterben der Schleife; das ist hier strukturell unmoeglich, weil der Absturz in einem separaten Thread liegt und die Schleife nie erreicht.
2. Keine haengende Sperre: _filme_sync_laeuft.locked() == False — das finally gibt frei, der naechste Takt versucht es erneut, gleiche 5-s-Kadenz wie im gekapselten Fall. Selbstheilung intakt.
3. Entscheidend: die Unsichtbarkeit unter pythonw stammt NICHT von der fehlenden Kapsel. Test C mit sys.stdout = None: _sag meldet "kein Absturz, Ausgabe verworfen". Die KORREKTE Kapsel wuerde also eine Meldung erzeugen, die JB genauso nie sieht. Beide Startwege sind pythonw ohne Mitschnitt: SyncYouTube.bat (start "" ...pythonw.exe) und SyncDashTray/System/settings_server.py:861-864 (pythonw.exe, creationflags=0x08000000, Popen OHNE Pipes). Weitere Senken ausgeschlossen: kein logging/keine Umleitung (einziger Treffer der Suche nach logging|sys.stderr|freopen|\.log ist sys.stdout in _sag, youtube_app.py:6079), kein eigener excepthook (Suche: keiner), _fehltext (youtube_app.py:4613-4616) ist reine Zeichenketten-Formatierung ohne Nebenwirkung, yt_status.json (geschrieben youtube_app.py:255) traegt nur Warteschlangen-Zaehler, keine Ticker-Fehler.

Im einzigen Modus mit sichtbarer Ausgabe (Konsolen-Start) ist der Thread-Traceback sogar aussagekraeftiger als die Kapsel-Zeile, weil _fehltext auf 300 Zeichen kuerzt und den Traceback verwirft.

EINSTUFUNG: echt = true, weil der Code-Pfad exakt so ist wie beschrieben und die Kapsel nicht abdeckt, was sie abzudecken scheint — ein latenter Struktur-/Konsistenzfehler, der an dem Tag real wird, an dem _sag eine echte Senke bekommt (Logdatei oder UI-Zeile). Schwere von "schwer" auf "klein" korrigiert: der messbare Unterschied fuer JB ist heute null (kein Herzschlag-Verlust, keine Sperre, keine Backoff-Differenz, keine Sichtbarkeits-Differenz).

NICHT durch diesen Befund verursacht, aber beim Messen aufgefallen und einer eigenen Pruefung wert: eine unerwartet durchschlagende Ausnahme in katalog_abzug setzt _fehlversuch_ts nicht (das passiert nur auf den geregelten return-Pfaden), damit greift der Backoff aus filme.py:214 nicht und der 5-s-Ticker stoesst sofort den naechsten Versuch gegen Renes Server an. Das verhaelt sich mit und ohne Kapsel identisch, ist also ein eigener Befund, kein Argument fuer diesen.

Verifikation: Probe-Skript C:\Users\janbe\AppData\Local\Temp\claude\C--Users-janbe-Downloads-Jan-Bernd-Claude\a63d3cd1-fd37-4614-9f47-4b975e55a173\scratchpad\probe_ticker.py, gelaufen mit -X utf8 im --testmodus (ausserhalb von JBs Datenordner). Kein Code geaendert, keine Rufe an Renes Server, kein Server gestartet (main() nie aufgerufen; die Prozesse auf 8776/8779 laufen seit 18:38 bzw. 18:51 und stammen nicht von dieser Probe).

### 23. [MITTEL] Anmelde-Wettlauf im EIGENEN Prozess: 12 gleichzeitige Poster erzeugen 24 Anmeldungen und 1 von 12 Bildern

**Stelle:** `C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:85`

**Beleg:** _anmelden() hat keine Sperre; youtube_app nutzt ThreadingHTTPServer (Zeile 6211) = ein Thread je Anfrage, und jeder Bild-/Detail-/Play-Ruf geht durch _anmelden(). Messung mit Attrappe, die den Unterschied modelliert (Jellyfin haelt je DeviceId nur das juengste Token gueltig — so der Code-Kommentar filme.py:828-830, live gefunden 05.08.): '12 Poster gleichzeitig nach einem Neustart: Anmeldungen gegen Renes Server: 24 (noetig waere 1); Bild-Rufe: 24, davon mit totem Token abgewiesen (401): 23; Poster geliefert: 1 von 12; je Poster im Schnitt 2.0 Anmeldungen'. Das Zeitfenster ist live gemessen: eine echte Anmeldung dauert 504 ms, so lange steht _sitzung leer. Mengen-Bezug: 4885 Katalog-Eintraege stehen 683 Cache-Dateien in filme_bilder gegenueber (~86 % der Titel haben kein Poster im Cache).

**Wirkung auf JB:** Das ist derselbe Anmelde-Sturm, den der Kommentar in filme.py:89-92 den 'Zweitprozessen' zuschreibt — er passt vollstaendig in EINEN Prozess und ist der plausibelste Erzeuger der 403-Sperre vom 06.08. Nebenbei: nach jedem Selbst-Neustart bleiben beim ersten Bild-Band 11 von 12 Kacheln leer, ohne Meldung.

**Urteil des Skeptikers:** Der MECHANISMUS ist echt und ich habe ihn unabhaengig nachgestellt — die ZAHLEN und die behauptete Wirkung auf JB sind dagegen live widerlegt. Ich stufe deshalb von "schwer" auf "mittel" zurueck.

BESTAETIGT (Code + eigene Messung):
_anmelden() (filme.py:85-120) hat keine Sperre; youtube_app.py:6211 ist ein ThreadingHTTPServer, do_GET (youtube_app.py:5270) serialisiert nichts, und die Poster-Route (youtube_app.py:5524-5527) ruft filme.bild_holen direkt, das bei Cache-Fehlschlag in _anmelden() geht (filme.py:247). Meine Attrappen-Messung, Kontrollgruppe ohne Token-Invalidierung: 1 gleichzeitig -> 1 Anmeldung, 2 -> 2, 6 -> 6, 12 -> 12 Anmeldungen (noetig waere je 1). Gegenprobe seriell: 12 nacheinander -> 1 Anmeldung, 12/12 Poster. Der Wettlauf ist also allein die Ursache. Die Vorbedingung stimmt sogar staerker als behauptet: 4885 Katalog-Eintraege gegen 389 _Primary.jpg im Cache; ueber den ganzen Katalog haben nur 364/4885 = 7,5 % ein Bild oder einen .fehlt-Merker. In den ersten Baendern verfehlen 7 von 20 ("neu") bzw. 8 von 20 ("top") den Cache — ein Ansturm von ~6-8 gleichzeitigen Anmeldungen je App-Start ist real.

WIDERLEGT (live gegen jelly.reneil.org, 2 Anmeldungen + 5 lesende GETs, mit Pausen):
Die Attrappe des Pruefers wendet die Token-Invalidierung auf die BILD-Route an. Die Invalidierung selbst existiert — Anmeldung A, dann Anmeldung B mit derselben DeviceId, danach /System/Info mit Token A -> HTTP 401, mit Token B -> HTTP 200. ABER die Bild-Route prueft gar kein Token: /Items/{id}/Images/Primary lieferte mit dem toten Token A HTTP 200 (899380 Byte), mit einem Muell-Token 200, und ganz OHNE Token-Kopf ebenfalls 200. Zum Vergleich ohne Token: Detail-Route 401, Episoden-Route 401, Items-Liste 401. Damit faellt:
- "24 Anmeldungen": das Verdoppeln kommt nur aus dem 401-Wiederholzweig in bild_holen (filme.py:254). Der kann auf dieser Route nie ausloesen. Korrigiert gemessen: 12, nicht 24.
- "Bild-Rufe 24, davon 23 mit totem Token abgewiesen (401)": auf dieser Route sind 0 moeglich.
- "Poster geliefert: 1 von 12" bzw. "11 von 12 Kacheln bleiben leer, ohne Meldung": widerlegt, korrigiert gemessen 12/12 geliefert, 401 auf Bild = 0. JB sieht keine leeren Kacheln.
- "eine echte Anmeldung dauert 504 ms": heute live 0,25-0,28 s. Das Zeitfenster bleibt offen, ist aber halb so gross.
- "683 Cache-Dateien, ~86 %": 683 enthaelt Thumb (174), Backdrop (108) und .fehlt (12); echte Poster 389, echter Fehlschlag 92,5 %. Zugunsten des Befunds ungenau.
Auch die Behauptung "plausibelster Erzeuger der 403-Sperre vom 06.08." ist unbelegt und von mir nicht pruefbar; 6-8 Anmeldungen je App-Start sind kein Sturm.

WAS UEBRIG BLEIBT und den Rest-Schweregrad traegt: Jede ueberzaehlige Anmeldung entwertet das vorige Token serverseitig (live belegt). Ein token-pflichtiger Ruf, der in den Ansturm faellt, verliert dadurch echt — und detail() hat KEINEN Wiederholzweig (filme.py:365-390, anders als katalog_abzug, episoden, _fortschritt_senden). Der Hero ruft beim Seitenaufbau genau einmal detail() (oberflaeche.py:8067), gleichzeitig mit dem ersten Bild-Band. Modell-Messung (8 Poster + 1 Hero-Detail, 20 Laeufe): in 7 von 20 Laeufen Detail-401 und Technik verloren (hoehe=0, kanaele=0, sub=[]). Deterministische Gegenprobe: nach dem 401 schreibt fam.json_aendern (filme.py:394) den LEEREN Stand unbedingt in den Meta-Cache, mit ts — Aufloesung, Ton-Kanaele und Untertitel-Sprachen fehlen dann 14 Tage lang (META_HALTBAR_S), ohne Meldung und ohne erneuten Versuch. Das ist eine echte, sich selbst festschreibende Nutzerwirkung, nur eine andere als die behauptete.

Fazit fuer die Hauptsitzung: die Sperre in _anmelden() ist berechtigt (Einzeiler), die Begruendung im Befund aber austauschen — es geht nicht um leere Poster-Kacheln, sondern um ~6-8 unnoetige Anmeldungen je App-Start gegen Renes Server und um den fehlenden 401-Wiederholzweig in detail(), der die Technik-Daten fuer 14 Tage leer einfriert. Messkripte: C:\Users\janbe\AppData\Local\Temp\claude\C--Users-janbe-Downloads-Jan-Bernd-Claude\a63d3cd1-fd37-4614-9f47-4b975e55a173\scratchpad\ (race_bild.py, token_modell.py, bild_anonym.py, race_korrigiert.py, detail_im_sturm.py, cache_vergiftung.py). Kein Code geaendert, nichts geloescht, nur lesende Live-Rufe.

## Kleinere Befunde: 50

- **[mittel]** Bayes kippt bei kaltem Stimmen-Cache in eine Ehrlich-Brothers-Top-10 — min(rating, 6.8) macht ALLE Ungeeichten gleich  (`SyncYouTube/System/filme.py:541`)
  - Heute unsichtbar, weil der Cache warm ist (0 HTTP-Rufe je Lauf gemessen). Aber jeder Cache-Verlust, ein fehlender TMDB-Key oder ein groesserer Katalog-Zuwachs setzt JB fuer 15 Home-Ladungen eine Top-10 aus Zaubershows und Bowling-Dokus vor. Gegen eine Attrappe faellt das nie auf, weil dort niemand 1-Stimmen-Titel mit rating 10 erfindet — im echten Katalog gibt es 14 davon.
- **[mittel]** Der Kandidaten-Vorfilter ist die rohe Bewertung — 2 Titel fliegen bei Gleichstand willkuerlich raus, Filme starten mit 40 statt 4806 Bewerbern  (`SyncYouTube/System/filme.py:512`)
  - Der Filme-Tab zieht seine Top-10 aus nur 40 Bewerbern. Ein Film mit roher Jellyfin-Note 8.4 und 30.000 TMDB-Stimmen kann die Top nie erreichen, obwohl sein Bayes-Score ueber dem der aufgenommenen Serien laege — der Tuerwaechter ist genau die Zahl, die der Score eigentlich korrigieren soll.
- **[mittel]** 50 Genre-Reihen fuer ~35 Begriffe: deutsche und englische Label stehen als getrennte, ueberschneidungsfreie Reihen nebeneinander  (`SyncYouTube/System/filme.py:555`)
  - JB scrollt an zwei Komoedien-Reihen vorbei, von denen keine die Komoedien zeigt, sondern jede eine Haelfte — und die kleinen Splitter ('Sci-Fi' 6, 'Science-Fiction' 2) sehen aus wie kaputte Reihen. Eine Attrappe hat ein Genre-Vokabular, Renés Bibliothek zwei.
- **[mittel]** 1,33 MB unkomprimiert je Aufruf — davon 1,2 MB, die die Home-Ansicht gar nicht zeigt, und ein Herz-Klick holt alles neu  (`SyncYouTube/System/filme.py:561`)
  - Auf dem Handy oder dem gekoppelten Fernseh-Geraet kostet jedes Herz-Antippen 1,33 MB und eine sichtbare Wartezeit. Bei einer 3-Eintrag-Attrappe waeren es 2 KB.
- **[klein]** Weiterschauen ist alphabetisch statt zuletzt-gesehen sortiert und kann Serien prinzipiell nie enthalten  (`SyncYouTube/System/filme.py:500`)
  - Die Netflix-Referenz-Reihe ordnet nach zuletzt gesehen — hier steht der Film ganz vorn, der zufaellig mit A anfaengt. Und eine halb geschaute Serie taucht nie in Weiterschauen auf, obwohl der Fernsehmodus (oberflaeche.py:8120) genau dafuer eine Fortsetz-Logik ueber Episoden hat.
- **[klein]** Nur die Merkliste ist profilabhaengig — weiterschauen/top/neu sind fuer jedes Profil identisch  (`SyncYouTube/System/filme.py:558`)
  - Robust gebaut, kein Absturz — aber sobald ein zweites Profil existiert, sieht der Zweitnutzer JBs angefangene Filme in seinem Weiterschauen, weil der Fortschritt am EINEN Jellyfin-Konto haengt. Fiel bisher nicht auf, weil es nur ein Profil gibt.
- **[klein]** Datums-Sortierung vergleicht Zeichenketten mit unterschiedlich langen Nachkommastellen — heute folgenlos, aber die Vergleichsregel ist falsch  (`SyncYouTube/System/filme.py:545`)
  - Heute kein sichtbarer Schaden — ehrlich gemessen, nicht vermutet. Die Fehlordnung kann nur innerhalb derselben Sekunde auftreten und ist damit kosmetisch; ein Fix waere trotzdem billig (auf die ersten 19 Zeichen plus float-Bruchteil sortieren).
- **[klein]** Die Desktop-Reihe heisst "Top 10", zeigt aber 30 Kacheln gemischt aus Filmen und Serien  (`SyncYouTube/System/oberflaeche.py:3857`)
  - Auf der Desktop-Filme-Seite steht eine Reihe mit dem Titel 'Top 10' und 30 Eintraegen. Die 30 sind Absicht (der Server liefert bewusst 30, damit die TV-Tabs filtern koennen) — die Desktop-Ansicht hat den Schnitt nur nicht mitbekommen.
- **[mittel]** Mengen-Effekt: der Meta-Cache ist EINE Datei — voll bestückt 9,4 MB, die bei jedem neuen Titel komplett neu geschrieben wird  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:279`)
  - Heute unauffällig, weil erst 17 von 4885 Titeln im Cache stehen — genau der Effekt, den eine kleine Attrappe nie zeigt. Je mehr JB schaut, desto träger wird die Detailseite: der TV-Hero ruft detail() bei jedem Neuzeichnen (oberflaeche.py:8067), und beim Befüllen serialisiert die Sperre alle Threads auf ~185 ms je neuem Titel.
- **[mittel]** Ein echter Katalog-Eintrag trägt eine ganze URL statt einer TMDB-Id — sie wird ungeprüft in die TMDB-Adresse geklebt  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:316`)
  - Der Titel bleibt ohne Inhaltsangabe, Besetzung, Trailer und Empfehlungen — und das Nichts wird nach Befund 2 zwei Wochen gecacht. Dieselbe ungeprüfte Id geht auch in die Bayes-Stimmen von reihen() (filme.py:521) und in den Abgleich von mehr_wie(), wo sie nie treffen kann. Eine Attrappe mit 3 sauberen Ids findet so etwas nie; ein echter Jellyfin-Bestand enthält eben genau einen von Hand falsch gepflegten Eintrag.
- **[mittel]** 'Erste Tonspur gewinnt' trifft bei echten Mehrspur-Dateien die falsche — Kanalzahl passt nicht zum gemeldeten Codec  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:379`)
  - Die Netflix-Detailseite zeigt 'ac3 5.1' für eine Tonspur, die in Wahrheit ac3 2.0 ist — eine Angabe, die JB glaubt und die nicht stimmt. Der Direct-Play-Schalter urteilt auf derselben schmalen Grundlage. Zur Einordnung, damit die Priorität ehrlich bleibt: in einer Stichprobe von 15 Filmen wäre ohnehin nur 1 (7 %) direkt browserfähig — der Anzeigefehler wiegt hier schwerer als der verlorene Direct Play.
- **[klein]** Der Rückgabewert des Cache-Schreibers wird nicht geprüft — eine verlorene Sperre fällt still unter den Tisch  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:394`)
  - Wenn es doch einmal eintritt (der Schreibvorgang wächst mit dem Cache auf ~185 ms, 48 gleichzeitige Threads brauchten schon 12,7 s), wird der Titel nicht gecacht und beim nächsten Öffnen komplett neu geholt — TMDB, OMDb und Renés Server. Unter Last also ausgerechnet dann mehr Verkehr, wenn ohnehin viel los ist. Kein akuter Schaden, aber ein blinder Fleck.
- **[mittel]** Der .fehlt-Marker gilt ewig, und bild_tag wird ignoriert - nachgelieferte Bilder erreichen JB nie  (`SyncYouTube/System/filme.py:244`)
  - Jellyfin holt Artwork nach dem Import verzoegert nach. Wer einen Titel in genau diesem Fenster ansieht, bekommt fuer immer kein Thumb - und wenn Rene ein Poster austauscht, zeigt SyncYouTube bis in alle Ewigkeit das alte. Das widerspricht dem Selbstheilungs-Anspruch: der Fehler haelt sich selbst am Leben.
- **[mittel]** PNG-Bilder werden als .jpg abgelegt und als image/jpeg ausgeliefert  (`SyncYouTube/System/filme.py:235`)
  - Auf 4885 Titel hochgerechnet rund 50 Poster mit falsch deklariertem Typ. Browser raten den Typ und zeigen sie meist trotzdem; wer aber 'Bild speichern unter' waehlt, bekommt eine .jpg-Datei, die keine ist, und strengere Anzeiger (Huelle, Handy-Ansicht) koennen sie verweigern. Bei Logos faellt zusaetzlich die Transparenz-Zusage weg.
- **[mittel]** Jedes Geraet im WLAN kann unbegrenzt 0-Byte-Marker anlegen und Rufe an Renes Server ausloesen  (`SyncYouTube/System/youtube_app.py:5524`)
  - Ein falsch konfigurierter oder neugieriger Nachbar im WLAN kann den Ordner mit beliebig vielen leeren Dateien zumuellen und - schwerer - SyncYouTube als ungedrosselten Weiterleiter auf Renes fremden Server benutzen. Ein Durchlauf 'Banner fuer alle 4885 Titel' kostet bei gemessenen 0,099 s je 404 rund 8 Minuten Dauerfeuer.
- **[mittel]** Das Schreiben ist weder atomar noch abgesichert - eine halb geschriebene Datei gilt danach fuer immer als gueltiges Bild  (`SyncYouTube/System/filme.py:272`)
  - Volle Platte, ein hartes Beenden der App oder ein Absturz mitten in einem 2,3-MB-Backdrop hinterlaesst ein dauerhaft kaputtes Bild, das sich nie selbst repariert - JB sieht eine graue Kachel oder ein zerhacktes Poster und kein Neustart hilft. Bei voller Platte fliegt zusaetzlich der OSError bis in den HTTP-Thread, statt sauber mit 404 zu antworten.
- **[klein]** Banner gibt es auf Renes Server ueberhaupt nicht, Logo und Banner werden von der Oberflaeche nie angefordert  (`SyncYouTube/System/filme.py:233`)
  - Die Whitelist bietet zwei Arten an, die niemand nutzt und von denen eine garantiert leer ist. Kein Schaden im Alltag, aber die Angriffsflaeche aus dem vorigen Befund und 4885 moegliche Leerlauf-Rufe haengen genau daran.
- **[mittel]** Specials (Staffel 0) sortieren VOR Staffel 1, der Knopf heißt "Staffel ?", und die Staffel-Vorauswahl bleibt falsch stehen  (`SyncYouTube/System/filme.py:451`)
  - Das Staffel-Band beginnt mit einem Knopf "Staffel ?" statt "Specials", und ▶ spielt ein Special, während optisch Staffel 1 markiert bleibt — JB sieht markiert "Staffel 1", bekommt aber ein Special. Netflix/Disney zeigen Specials hinten; hier stehen sie vorn. Beides ist eine Folge davon, dass 0 im Sortierschlüssel wie eine echte Staffel und im Frontend wie "kein Wert" behandelt wird.
- **[mittel]** Doppelt vorhandene Dateien werden zu doppelten Kacheln — kein Zusammenführen bei gleicher Staffel/Folge  (`SyncYouTube/System/filme.py:451`)
  - In vier Staffeln der Simpsons steht dieselbe Folge zweimal nebeneinander im Folgen-Band, einmal davon ohne Laufzeitangabe. JB weiß nicht, welche der beiden Kacheln die brauchbare Datei ist, und ein Klick auf die falsche kann eine kaputte/unvollständige Datei starten. Die Kette hat keine Zusammenführung bei gleichem (Staffel, Folge).
- **[mittel]** Serverausfall ist von "Serie hat keine Folgen" nicht zu unterscheiden — die Kette schweigt  (`SyncYouTube/System/filme.py:439`)
  - Genau in der Lage vom 06.–13.08. (403-Sperre) hätte JB nicht "Server nicht erreichbar" gesehen, sondern jede Serie ohne Staffel-Band und den Hinweis "🎬 Keine Folgen gefunden." — also eine leer aussehende, scheinbar kaputte Bibliothek statt einer ehrlichen Ausfallmeldung. Dazu: der Neuanmelde-Versuch greift genau EINMAL; das zweite 401 endet still in []. Die Wiederanmeldung selbst funktioniert (live bewiesen), kostet unter paralleler Last aber 3 zusätzliche Rufe pro Serienöffnung und speist damit denselben Anmelde-Sturm, der am 06.08. zur Sperre führte.
- **[mittel]** Nur 8 % der übertragenen Bytes werden benutzt — 1,4 MB von Renés Server je Öffnen einer großen Serie  (`SyncYouTube/System/filme.py:427`)
  - Jedes Öffnen einer Serien-Detailseite zieht bis zu 1,4 MB über Renés Leitung, von denen 92 % (BackdropImageTags, ImageBlurHashes, ParentLogoImageTag, SeriesPrimaryImageTag …) sofort weggeworfen werden. Bei 918 Serien und einem Menschen, der im Fernsehmodus durch die Bibliothek blättert, ist das die teuerste Einzelbewegung der ganzen Film-Kette — und sie trifft fremdes Eigentum. Allein EnableImages=false halbiert sie, ohne dass ein Feld verlorengeht, das wir lesen.
- **[mittel]** Ein Serien-Öffnen löst 100 Bild-Rufe an Renés Server aus — der Bild-Cache kennt keine einzige Episode  (`SyncYouTube/System/oberflaeche.py:8201`)
  - Ein einziger Klick auf Pokémon feuert 100 Bildabrufe gegen Renés Rechner, ohne Staffelung und ohne Lazy-Grenze über das sichtbare Fenster hinaus. Mit der 3-Episoden-Attrappe waren das 3 Rufe — der Effekt konnte im Test gar nicht auffallen. Für JB heißt das: die Detailseite baut sich bei großen Staffeln spürbar langsam auf, und für René heißt es eine Lastspitze pro Klick.
- **[klein]** Rohe Dateinamen erscheinen unverändert als Episodentitel  (`SyncYouTube/System/filme.py:445`)
  - Auf dem Fernseher steht "F0 · 057.Pokemon.-.Pokmon.Paparazzi" statt "F57 · Pokémon Paparazzi" — inklusive verschluckter Umlaute ("Pokmon"), weil der Dateiname sie nie hatte. Das ist Datenqualität auf Renés Seite, aber die Kette reicht sie ungefiltert bis auf JBs Bildschirm durch; ein Titel von 88 Zeichen sprengt zusätzlich die Kachel.
- **[klein]** Unsinnige Id erzeugt trotzdem einen Ruf an Renés Server  (`SyncYouTube/System/filme.py:424`)
  - Kein Sicherheitsproblem — der Ausbruch ist sauber blockiert, und der Test hat recht. Aber jede Fehleingabe am Endpunkt /api/filme/episoden?id=… kostet einen Ruf an fremdes Eigentum; eine Format-Prüfung (32 Hex-Zeichen) würde ihn ohne Netzweg beantworten.
- **[mittel]** Codec-Fehlschlag aus der Sperrzeit steht 14 Tage im Meta-Cache und verstellt die Weiche  (`C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\filme.py:308`)
  - 'Die Verurteilten' bleibt bis rund zum 27.08. auf 'kein Codec bekannt' — die Weiche schickt den Titel immer in den Transcode, und die Detailseite zeigt weder HD-Abzeichen (tvQualitaet(0) = '') noch Ton-Angabe. Das trifft alles, was waehrend eines Ausfalls einmal angesehen wurde: der Fehlschlag ueberlebt die Heilung des Servers um zwei Wochen.
- **[mittel]** Der Direkt-Strom bricht nach 30 s Stille still ab, obwohl der Laengen-Kopf mehr versprochen hat  (`C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\youtube_app.py:5509`)
  - Ein 30-Sekunden-Haenger bei Rene (Neustart, Netz, Plattenschlaf) beendet den Film mitten im Bild. Der Browser sieht einen abgeschnittenen Koerper zu einer versprochenen Laenge, meldet Medienfehler — und die Selbstheilungs-Kette wirft JB dann in den (kaputten) Transcode und weiter in VLC, statt einfach an derselben Stelle mit einem neuen Range-Ruf weiterzumachen.
- **[mittel]** Zeitleiste tot und Titel leer, wenn der Film nicht ueber Infoseite oder Hero gestartet wurde  (`C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\oberflaeche.py:3958`)
  - Im Transcode-Modus — also bei 90 % der Titel — laesst sich per Klick auf den Balken nicht springen und die Zeitanzeige bleibt leer, sobald man aus der Kachel-Hover-Karte heraus startet. ±10 s geht zwar (tvpRel nutzt 1e9 als Ersatzlaenge), kostet aber jedes Mal einen kompletten ffmpeg-Neustart: gemessen 1,2 s (vcopy) bis 3,2 s (Sprung auf Minute 30) schwarzes Bild pro Tastendruck.
- **[klein]** Im Browser-Player gibt es keine Ton- und Untertitelwahl, ffmpeg nimmt hart die erste Tonspur  (`C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\oberflaeche.py:3944`)
  - Wer Original-Ton oder Untertitel will, kommt im Browser nicht heran — die Bibliothek bietet es (mehr als drei Viertel der Titel sind zweisprachig), der Player nicht. Dass es meist trotzdem passt, ist Glueck: Rene legt die deutsche Spur zuerst ab. Bei einer Datei mit englischer Spur 0 laeuft der Film ohne Ausweg auf Englisch.
- **[klein]** Der Direct-Play-Strom braucht auf Renes Server ueberhaupt kein Token  (`C:\Users\janbe\Downloads\Jan-Bernd\Claude\SyncYouTube\System\filme.py:798`)
  - Fuer unsere Kette ist das ein Stueck Robustheit (ein invalidiertes Token bricht das Abspielen nicht), aber die Begruendung im Code stimmt nicht: wer eine Item-ID kennt, zieht den Film ohne Anmeldung. Das ist Renes Server-Einstellung, nicht unser Fehler — gehoert aber ihm gesagt, bevor jemand die Weiche darauf aufbaut.
- **[mittel]** Absturz oder Fensterschliessen mitten im Nachreichen -> alles wird beim naechsten Mal erneut gesendet  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:876`)
  - Beendet JB die App waehrend des Nachreichens (oder faellt die App aus), bekommt Renes Server dieselben Positionen ein zweites Mal. Fuer die reine Position harmlos, fuer 'gesehen' aber eine erneute Als-gesehen-Markierung auf fremdem Server.
- **[mittel]** Antwortet der Server mit 200 und HTML statt JSON, fliegt fortschritt() mit einer Ausnahme raus — der Spot ist weder gesendet noch gemerkt  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:111`)
  - Genau der Fall einer Wartungs-/Proxy-Seite (Cloudflare, Reverse-Proxy-Fehlerseite mit Status 200) — also die Nachbarschaft dessen, was vom 06.–13.08. passiert ist. Statt in die Warteschlange zu wandern, ist der Fortschritt einfach weg.
- **[klein]** 'gesehen' geht still verloren, wenn nur der PlayedItems-Ruf scheitert  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:842`)
  - Ein zu Ende gesehener Film bliebe auf Renes Server ungesehen, ohne dass irgendetwas nachfasst. Heute ungefaehrlich, weil die Oberflaeche das Feld nie setzt — aber die Falle liegt scharf da, sobald jemand das Als-gesehen-Melden einbaut.
- **[klein]** Nicht-numerische Position reisst fortschritt() ab, statt in die Warteschlange zu gehen  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:857`)
  - Heute schickt die Oberflaeche immer eine Zahl (Math.round), der Weg ist also kalt. Kritischer ist der Randwert daneben: eine leere ItemId (youtube_app.py:5784 nimmt 'daten.get("id") or ""') landet als Eintrag in der Queue und wird damit zum Kandidaten fuer den Einfrier-Befund oben.
- **[klein]** Ein kaputter Queue-Eintrag laesst den 6-h-Abzug still sterben  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:872`)
  - Der Katalog selbst ist da (er wird in Zeile 198 vorher geschrieben), aber der Sync-Thread stirbt danach lautlos — kein Fehler im Dashboard, kein Eintrag irgendwo. Braucht allerdings erst eine beschaedigte Queue-Datei; regulaer schreibt nur fortschritt() dort hinein.
- **[klein]** Warteschlange ohne Deckel, ohne Entdopplung, ohne Alterung — und die Kosten wachsen quadratisch  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:856`)
  - Allein harmlos, gefaehrlich im Verbund mit dem Einfrier-Befund: sobald ein Eintrag klemmt, waechst die Datei unbegrenzt weiter und jede weitere Meldung wird langsamer. Und beim ersten gelungenen Abzug nach laengerem Ausfall gehen alle Meldungen in einem Rutsch ohne Pause an Renes Rechner.
- **[klein]** Merkliste nimmt alles an: leere ID, Phantasie-IDs, beliebige Profilnamen — nie gegen den Katalog geprueft  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:482`)
  - Ein Fehlklick ohne ID (youtube_app.py:5749 reicht 'daten.get("id") or ""' durch) legt einen leeren Eintrag in JBs Merkliste, den nichts wieder aufraeumt. Bei Rene geloeschte Filme bleiben als Leichen in der Liste.
- **[klein]** Kein Aufrufer erfaehrt, ob das Merken/Melden ueberhaupt gespeichert wurde  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:859`)
  - Scheitert das Schreiben, meldet fortschritt() zwar False, aber niemand sieht es: kein Toast, kein Log, kein Wiederholversuch. JB erfaehrt vom Verlust erst, wenn 'Weiterschauen' beim naechsten Mal fehlt.
- **[mittel]** D-Pad-Sprung in das A–Z-Raster misst 3967 Kacheln pro Tastendruck  (`SyncYouTube/System/oberflaeche.py:8283`)
  - Genau die Bedienung, für die der Fernsehmodus gebaut ist — Pfeiltaste auf der Fernbedienung — trifft im Filme-Tab die teuerste Stelle. Ohne Browser kann ich die Millisekunden nicht messen, die Anzahl der Layout-Messungen ist aber ein reiner Code-plus-Daten-Befund. Ein Deckel (nur die Kacheln des sichtbaren Bereichs vermessen) wäre lokal und verhaltenserhaltend.
- **[mittel]** fsk wird roh als Badge angezeigt — 64 Einträge tragen ganze MPAA-Sätze, der längste 168 Zeichen  (`SyncYouTube/System/oberflaeche.py:7519`)
  - Bei diesen 64 Titeln steht statt eines kleinen Kästchens ein umbrochener Absatz in der Hover-Karte und in der Info-Zeile — die Karte wächst in der Höhe, ihre fixed-Positionierung (7536) rechnet dagegen an. Eine Normalisierung im Zubringer (filme.py:_eintrag: 'Rated R for …' → 'R', 'FSK--' → leer) heilt Anzeige und Datenbestand gleichzeitig.
- **[mittel]** video_codec und audio_codec sind bei ALLEN 4885 Einträgen leer — die Browser-Weiche entscheidet blind  (`SyncYouTube/System/filme.py:165`)
  - Scheitert der Einzel-Abruf von detail() (genau das war vom 06.–13.08. der 403-Fall), gibt es kein Direct Play im Browser, und der Transcode-Weg re-encodiert mit libx264 auch dann komplett, wenn die Datei bereits h264 ist — volle CPU-Last für nichts. Zweitens erklärt es das leere 'Ton:'-Feld auf der Info-Seite (tvTon, 8144). Der Zubringer, nicht die Oberfläche, ist hier die Wurzel.
- **[mittel]** Die Hover-Karte behauptet bei jedem Titel 'HD' — die Info-Seite derselben Oberfläche widerspricht  (`SyncYouTube/System/oberflaeche.py:7520`)
  - JB bekommt in einer Oberfläche zwei widersprüchliche Aussagen über dieselbe Datei; bei SD-Material ist die Kachel-Aussage schlicht falsch. Entweder das Badge aus hoehe ableiten (dann muss hoehe in den Katalog) oder es auf der Karte weglassen.
- **[klein]** 125 Einträge ohne Laufzeit erzeugen ein leeres <span> in der Meta-Zeile, 3 eine völlig leere  (`SyncYouTube/System/oberflaeche.py:7502`)
  - Kosmetisch: eine Lücke in der Karte, eine leere Zeile in der Info. Die drei nackten Einträge sind zugleich der Fingerzeig auf schlecht erkannte Dateien auf Renés Server (Dateinamen als Titel) — für JB eher ein Hinweis als ein Fehler.
- **[klein]** Bei Serien zeigt die Karte die FOLGEN-Länge, als wäre es die Länge des Titels  (`SyncYouTube/System/oberflaeche.py:7502`)
  - Heute harmlos, weil position_s bei allen 918 Serien 0 ist (nur 3 Filme stehen überhaupt auf 'Weiterschauen': Aladin 6 %, Der Pagemaster 22 %, Die Verurteilten 7 %). Sobald JB eine Serie anfängt, wird der Balken falsch. Ein '~45 Min./Folge' statt '45 Min.' wäre ehrlich.
- **[klein]** Das A–Z-Raster beginnt nicht bei A — localeCompare sortiert Leerzeichen, ¡, [ und # nach vorn  (`SyncYouTube/System/oberflaeche.py:7825`)
  - JB scrollt an den Anfang und sieht Sonderzeichen statt A. Die drei Fremdschrift-Titel sind bei 130 Bildschirmhöhen Scrollweg praktisch versteckt. Ein .trim() im Zubringer und eine Sortierung nach normalisiertem Titel räumen beides auf.
- **[klein]** Kacheln zeigen nur den Titel — 104 Einträge sind dadurch nicht unterscheidbar  (`SyncYouTube/System/oberflaeche.py:7790`)
  - Im A–Z-Raster stehen drei identisch beschriftete 'Godzilla'-Kacheln nebeneinander; welche die 1954er ist, verrät nur das Poster. Das Jahr in tvFilmReihe mitzunehmen und unter den Titel zu setzen wäre ein Zweizeiler.
- **[klein]** Einzelstimmen-Bewertungen erscheinen ungefiltert als ★ 10.0  (`SyncYouTube/System/oberflaeche.py:8054`)
  - Die Detailseite verspricht bei No-Name-Titeln Bestnoten, die Top-10-Reihe sagt dazu (richtigerweise) nichts. Wer nach ★ geht, wird in die Irre geführt. Entweder denselben _score anzeigen oder das Sternchen ohne Stimmenzahl weglassen.
- **[mittel]** Handbetrieb kann die 10-Minuten-Sperre nicht durchbrechen und meldet trotzdem Erfolg  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/youtube_app.py:5731`)
  - JBs einziger Hebel gegen den Ausfall — der Knopf ⟳ Abgleichen — meldet Erfolg, waehrend nichts passiert, und zwar bis zu 10 Minuten lang. Es gibt keinen Weg, die Sperre zu loesen, ausser die App neu zu starten. Ein zweiter, dritter Klick aendert nichts und sagt es auch nicht.
- **[mittel]** Mengen-Effekt: der Ticker zerlegt alle 5 s 2,4 MB JSON, um EINEN Zeitstempel zu lesen  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:214`)
  - Mit der 2-Eintrag-Attrappe der Tests ist das unmessbar klein; mit Renes echter Bibliothek laeuft ein Dauerverbrauch mit, der mit jedem neuen Film steigt — und ausgerechnet der gesunde Zustand ist der teure.
- **[mittel]** Zweiter 401 im seitenweisen Abzug bleibt ungeheilt — 4885 Eintraege sind 5 Seiten, die Attrappe hat 1  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:168`)
  - Genau die Token-Kaskade aus dem Wettlauf-Befund erzeugt WIEDERHOLTE 401 — der Abzug dauert real 11 s ueber 5 Seiten, Zeit genug fuer eine zweite Invalidierung. Dann faellt der ganze Lauf durch und der naechste Versuch kommt erst 30 Minuten spaeter.
- **[klein]** Backoff-Zustand lebt nur im Prozess — und die App startet sich bei jeder Code-Aenderung selbst neu  (`C:/Users/janbe/Downloads/Jan-Bernd/Claude/SyncYouTube/System/filme.py:27`)
  - Jeder Neustart erlaubt sofort einen frischen Anmeldeversuch und setzt beide Ruhepausen auf null. Waehrend einer laufenden Bruteforce-Sperre heisst das: jede Code-Aenderung schickt einen weiteren Fehlversuch los. Zusammen mit den 336 Abzug- und bis zu 84 Fernseh-Anmeldungen kommen ueber 7 Tage rund 420+ Fehlanmeldungen zusammen — Verdacht (unbelegt, nicht nachgestellt, weil verboten): der Heilungs-Takt selbst kann die Sperre am Leben gehalten haben.
