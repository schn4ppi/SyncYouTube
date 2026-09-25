# Start-Prompt für den nächsten SyncYouTube-Chat (Stand 25.09.2026, nach der Gesamtprüfung)

> **NACHTRAG 25.09.2026 (Abend) — Gesamtprüfung und drei Reparatur-Runden (Zweig `gesamtpruefung`, in main bis `785dd04`).**
> JB-Wunsch: „den Spaghetticode bzw. das Programm prüfen und verbessern“. Erst eine lesende Prüfung (vier
> Bereiche, je ein Gegenprüfer), dann drei Runden im eigenen Worktree, jede Gruppe mit Test zuerst,
> skeptischer Abnahme samt roten Gegenproben in einer Wegwerf-Kopie und Nacharbeit. 119 Commits, Suite
> 615 → **1347 bestanden, 2 übersprungen**; live geprüft nach jedem Einspielen (Oberfläche ohne
> Skriptfehler, 966 Bibliothekseinträge, Kopf-Prüfungen antworten 403, Untermenü, Fernbedienung, Protokoll).
> - **Sicherheit:** Host- und Origin-Prüfung vor jedem Riegel (fremde Webseiten und DNS-Rebinding
>   prallen ab), Einbetten nur durch App und Dashboard, `Referrer-Policy: no-referrer`; Pfade für Abo-Index,
>   Cover und Untertitel nur noch im eigenen Ordner; kein endgültiges Löschen mehr (Papierkorb, sonst
>   rückholbar nach `_Papierkorb`, Playlist-Spiegel nach `_entfernt` mit `.nomedia`); Bibliotheks-Schlüssel
>   und Film-Ids nur noch als `data-`Attribute in Handlern; Versuchsbremse je IP für Code und Geräte-Token,
>   zeitkonstante Vergleiche; Körpergrenze 2 MB, Lese-Zeitlimit (Ströme ohne Schreib-Zeitlimit);
>   Selbst-Update nur mit gültiger Authenticode-Signatur desselben Herausgebers und vorhandener `.sha256`,
>   `build_release.py` baut nicht ohne Signatur-Token.
> - **JB-Entscheide (25.09.):** Sync-Ziel in der Bibliothek oder als Netzwerkpfad wird beim
>   Einrichten abgelehnt (`sync_ziel_fehler`, nachgeholt in `785dd04`); WLAN-Geräte dürfen abspielen, suchen, fernsteuern und YouTube-Links laden,
>   alles andere nur am PC (`LAN_ERLAUBT`/`NUR_PC`, alles nicht Erlaubte ist gesperrt); gekoppelte Geräte
>   bekommen die volle Oberfläche per HttpOnly-Cookie (Einstellungen dort ausgeblendet), Token nicht mehr in
>   Adresse und `localStorage`; neue Codes 10 Zeichen, Knopf „🔄 Code erneuern“ im ⚙-Menü, alter Code gilt
>   bis zum Klick; Neuladen der Seite erst bei Pause oder Titelende; Alias `/handy` entfernt; `--gedaempft`
>   als CSS-Variable; ein Untermenü-Verhalten in allen Kontextmenüs.
> - **Nebenläufigkeit:** `profile.json` unter Sperre (ein Widerruf geht nicht mehr verloren), Speichern über
>   `familie.json_schreiben` mit Wiederholung, eine Sperre für CFG, Worker stirbt nicht mehr am Speichern,
>   höchstens zwei yt-dlp-Auflösungen zugleich (hängende geben ihren Platz nach 5 min ab), 30 min Pause der
>   Serien-Abrufe nach einer YouTube-Sperre, Bibliotheks-DB unter Sperre, keine Sperre über Ordnerläufen
>   oder HTTP-Antworten.
> - **Fehler behoben:** u. a. Zeitleiste der Kopfleiste im VLC-Modus, Film-Merkliste im Fernsehmodus (war
>   immer 404), neue Playlist wird verlässlich gewählt, Film-Details nach Ausfall nach 1 h statt 14 Tagen,
>   Live-TV hängt nicht nach Fehlschlag, Geo-Umgehung trennt keine eigene VPN-Verbindung, ehrliche
>   Meldungen (M3U zu groß, Kopplung gescheitert, Fernsteuerung aus).
> - **Aufräumen:** `/api/importieren`, der Bulk-Zweig, 14 tote JS-Funktionen und tote CSS entfernt (Wächter
>   `tests/test_toter_code.py`); Protokoll `System/yt_protokoll.log` (rotierend, höchstens rund 4 MB);
>   `python tests/test_youtube.py` fährt alle Tests über pytest; Test-Wachen: Daten-Wache per Audit-Hook,
>   Netzsperre für alle Module, frische Zustände je Test, JS-Syntax-Wächter über alle Skript-Blöcke.
> - **Vor dem nächsten Release (nur exe):** einmal am PC mit Netz `update.authenticode_online(<neue
>   signierte exe>)` messen (erwartet Code 0); ohne gesteckten eToken baut `build_release.py` nicht.
> - **Handgriffe am echten Gerät (nicht prüfbar ohne Programmstart):** Handy `/m` nach dem Neustart ohne
>   Code-Eingabe? Abspielen am Handy (Ton, Sperrbildschirm, Vor/Zurück) und am PC; „Code erneuern“, danach
>   `/m` verlangt den neuen Code. Fernseher: alte Adresse (auch mit `?geraet=`) lädt die volle Oberfläche
>   ohne Token in der Adresse; Fernsehmodus, Film, Untertitel, ❤, Merkliste; kein Papierkorb/Ordner/
>   Einstellungen; Browser neu starten bleibt gekoppelt; am PC trennen wirkt sofort; Film über den
>   Browser-Player länger als 30 s pausieren und fortsetzen.
> - **Offen (Vorschläge bzw. JB-Fragen, Stand 25.09.):** Code-Cookie 30 Tage fest oder gleitend; Audio-
>   Endungen `.wav`/`.aac` einheitlich einstufen; eine Audio-Prüfung in der Oberfläche; weitere rohe Ids in
>   Handlern über `data-`; acht CSS-Kandidaten ohne Nennung plus CSS-Wächter mit Auto-Discovery;
>   `_json_laden` bei anhaltender Sperre Speichern verweigern; Struktur-Plan (Module aus `youtube_app.py`,
>   Routentabelle, JS/CSS aus `oberflaeche.py`) noch nicht begonnen.

> **NACHTRAG 25.09.2026 — Nacharbeit der Prüfung Runde 3 (nacharbeit_r3_yt).** Grundlage:
> JBs Esc-Regel vom 24.09. („gesehen" ab 90 % auch bei Esc/⏭) und die Mindest-Sehzeit.
> Entscheidung des Hauptagenten (analog): das Schließen der Hülle im Abspann ist dieselbe Art
> Beenden wie Esc. Jeweils Test zuerst (am alten Stand rot), dann Fix.
> - **Hülle zu:** Die SEITE meldet beim Entladen selbst (`oberflaeche.py` `filmAbschied` an
>   `pagehide`, über die EINE Meldestelle, `fetch` mit `keepalive`) — sie kennt die Sehzeit.
>   Der Server-Rückfall (`youtube_app._film_stelle_melden`) wartet bis `HUELLE_GNADE_S` (2 s)
>   auf diese Meldung (die Route `/api/filme/fortschritt` merkt sie, auch bis
>   `HUELLE_VORLAUF_S` = 10 s VOR dem Pausieren) und schweigt dann. Kommt keine, meldet er die
>   Stelle unter Jellyfins Grenze (`_stelle_unter_jf_grenze`: 0,9 × (Länge − 30 s), dieselbe
>   Rechnung wie die Seite, am Ergebnis gleich geprüft), nie „gesehen"; nichts bei
>   unbekannter Länge oder kurzem Stück (Grenze 0). Geprüft mit dem Jellyfin-12.1-Orakel:
>   Hülle zu bei 95 % hakt bei keiner Laufzeit ± 30 s.
> - **Esc ohne Fernbedienung:** Dauer und Stelle kommen vom VLC-Status (vor dem Stopp), nie
>   „gesehen", Stelle unter der Grenze. Allgemein: ohne bekannte Dauer geht NICHTS hinaus
>   (vorher ungekappt; Toast „🎬 Film beendet.").
> - **Gedrosselter VLC-Takt:** ein Sprung ist, was mehr als 3 s SCHNELLER lief als die
>   Wanduhr × Tempo (größeres der beiden Tempi; `SEHZEIT.uhr`) — ein im verdeckten Tab
>   durchgeschauter Film zählt (Probe P3: vorher gemeldet 0, ohne „gesehen").
> - **Natürliches Ende:** erfüllt (a), sobald es hinter 0,9 × (Dauer − 30 s) liegt (Transcoder:
>   Dauer auf Minuten gerundet, ein 151-s-Stück hieß nie „gesehen"); ein Strom, der mitten im
>   Film abreißt, bleibt eine Stelle.
> - **Kleinere:** `tvpLandePos` nimmt `SEHZEIT.jfMaxResume`; die Schwellen stehen im Code als
>   „von JB zu bestätigen"; `filme._druck_in_ruhe` verbraucht den einen Versuch je Ruhe nur,
>   wenn Jellyfin antwortete (Erfolg/401/403) — ein Netz-Wackler sperrt den Film-Start nicht
>   mehr bis zu 10 Min; Protokolle im Testmodus per Kindlauf verhaltensgeprüft; „gesehen"-Route
>   im Test über Pfad + Merkmale statt Zeichenkette.
> - **Test-Wachen** (`tests/conftest.py`): Schlüsselbund und Netz des Film-Teils (`_zugang`,
>   `_meta_keys`, `_seerr_url`, `_http`, `_seerr_http`) sind für die GANZE Sitzung laut
>   gesperrt, auch im Hintergrundfaden; Film-Pfade je Test in `tmp_path`; die Sperren werden
>   vor und nach jedem Test neu gesetzt, weil ein `importlib.reload(filme)` (test_filme,
>   „Zustand überlebt den Neustart") die echten Funktionen zurückbringt. **Befunde dabei:**
>   vier Tests lasen JBs echten TMDB-Schlüssel aus dem Schlüsselbund und reichten ihn an ihre
>   Attrappe (kein Netzruf, nur die Attrappe verhinderte ihn), und der Neulade-Test las danach
>   über `zustand()` den echten Jellyfin-Zugang — in jedem vollen Lauf, nur lesend; beides
>   behoben. Die Jellyfin-Attrappen melden unerwartete Rufe laut
>   (`test_filme.UNERWARTETE_RUFE`): sieben still als Netzfehler verschluckte Fälle aufgedeckt
>   und repariert.
> - **Prüf-Fläche:** volle Suite 615 grün (vorher 600); 24 Gegenproben in einer Wegwerf-Kopie
>   (`%TEMP%\yt_r4_gp`, nur getrackte Dateien + deno, Schlüsselbund und Netz dort an der Quelle
>   stillgelegt), alle rot aus dem erwarteten Grund; `node --check` aller 5 Skript-Blöcke ok;
>   ruff ohne neue Befunde. **Vorfall:** Die erste Fassung der Gegenprobe G21 schaltete nur
>   die Schlüsselbund-Sperren ab — ihr Kindlauf las dabei JBs Jellyfin-Zugang aus dem
>   Schlüsselbund (nur lesend, nichts ausgegeben); das Netz blieb gesperrt, kein Ruf an Renés
>   Server. Seitdem das zweite Netz in der Kopie.
> - **Nicht live gemessen:** ob WebView2 beim Schließen der Hülle `pagehide` feuert und die
>   keepalive-Meldung vor dem Prozessende ankommt — sonst greift der Rückfall, und im Abspann
>   gibt es dann KEIN „gesehen", nur die Grenze (Probe: Hülle im Abspann schließen, Kachel ✓?).
> - **Grenzen:** F5 oder Tab zu bei einem VLC-Film im Abspann meldet nach der Regel „gesehen",
>   obwohl der Film im VLC weiterläuft. Ohne bekannte Dauer merkt die Seite eine Folgen-Stelle
>   nur lokal. Im gedrosselten Takt kann die Sehzeit höchstens um die verstrichene Wanduhr ×
>   Tempo zu hoch liegen (z. B. ein Sprung über das Windows-Overlay im verdeckten Tab).
> - **Bewusst nicht geändert:** (i) „kein echtes Stück unter der Grenze ⇒ Grenze statt
>   Startstelle" (Vorschlag der Prüfung): widerspräche JBs Beispiel 3 (ab 50 %, sofort ans
>   Ende ⇒ die Startstelle ist der ehrliche Wiedereinstieg); die Ursache (gedrosselter Takt)
>   ist behoben. (ii) Die gemeldete Stelle bleibt „letzte echt geschaute Stelle UNTER der
>   Grenze": die Alternative min(Ende des letzten Stücks, Grenze) meldete im Testfall (b)
>   2133 s, eine Stelle, die nie geschaut wurde (Sprung von 60 s auf 2140 s). (iii)
>   `IsPaused:true` bzw. `Stopped` bei verweigertem „gesehen" (Vorschlag, unbestätigt): die
>   Kappung hängt an Jellyfins Leerlauf-Stopp (in 12.1 mit der zuletzt gemeldeten Stelle, für
>   10.11 unbelegt) — erst live messen, wenn der Zugang wieder geht.
> - **JB-Fragen:** (1) Übernimmt die Musik den VLC im Abspann (kein eigenes Ende), geht nur
>   die Grenze hinaus, nie „gesehen" — „Hülle zu" zählt jetzt wie Esc. Soll auch die
>   Musik-Übernahme bei reichender Sehzeit „gesehen" sein? (2) Kurze Stücke (unter 5,5 min)
>   ohne „gesehen": die Seite meldet Stelle 0 (Weiterschauen weg), der Hüllen-Rückfall gar
>   nichts — so lassen, nie melden, oder wie früher Jellyfins Kurz-Regel („gesehen" ab 5 %)?
>   (3) Die Schwellen der Mindest-Sehzeit (5 min, 50 %, 3 s, 30 s Spielraum) bestätigen.
>   (4) Startmenü-Regel (Nachtrag „nacharbeit_r2" unten).

> **NACHTRAG 25.09.2026 — Jellyfin 12: ApiKey und Nachfolge-Routen (Runde 3, yt:jellyfin12).**
> Grundlage: Beleg mit Gegenprüfung am Quelltext v12.1 (nicht live gemessen, kein Netz zu
> Renés Server). Jellyfin 12.1 liest das Token nur noch aus `Authorization: MediaBrowser …,
> Token=…` oder `?ApiKey=`; `api_key`, `X-Emby-Token` und `X-Emby-Authorization` übergeht es
> still, weil die Migration DisableLegacyAuthorization den Legacy-Schalter beim Update
> abschaltet (`AuthorizationContext.cs:84-111`).
> - **Strom-Adresse:** `filme.STROM_TOKEN_PARAM = "ApiKey"` (EINE Stelle). Mit `api_key` lief
>   der Film trotzdem, weil `/Videos/{id}/stream` anonym ist — aber ohne Konto, durch eine
>   Lücke, die Jellyfin schließen will (jellyfin#13984). Gilt für VLC-Start, Browser-Proxy
>   `/api/filme/direkt` (ohne und mit `tc=1`: Vorprobe + ffmpeg) und Szenen-Vorschau.
>   `ApiKey` lesen auch 10.10.7 und 10.11.11.
> - **Routen:** Katalog `GET /Items?userId=`, Titel (`_folge_holen`, Technik in `detail`)
>   über `filme._titel_pfad` → `GET /Items/{id}?userId=`, „gesehen" `POST
>   /UserPlayedItems/{id}?userId=`. Die Alt-Routen beantwortet 12.1 noch, aber als
>   [Obsolete] und ohne Vorwarnung entfernbar (Release-Notiz v12.0); die Alt-Route ruft in
>   12.1 wörtlich die neue auf, gleiche Antwortform. DELETE PlayedItems und
>   `/Users/{uid}/Items/{id}/UserData` nutzt SyncYouTube nicht.
> - **Prüf-Fläche:** `JellyfinAttrappe` (tests/test_filme.py) modelliert 12.1: Token aus
>   Kopf oder `ApiKey` (`api_key` ⇒ anonym, 10.11 liest beides), Alt-Routen antworten
>   weiter und landen in `veraltet`, fremde `userId` ⇒ 403, Strom anonym mit Konto-Mitschnitt
>   (`stroeme`). Neu: `test_jellyfin12_jeder_weg_ruft_die_nachfolge_route`,
>   `test_jellyfin12_strom_adresse_gehoert_zu_jbs_konto` (beide auch gegen 10.11) und
>   `test_jellyfin_zugang.test_jellyfin12_jeder_strom_verbraucher_holt_mit_jbs_konto`
>   (fünf echte Abrufe der vier Verbraucher). Am alten Stand 5 rot; 14 Gegenproben in
>   `%TEMP%\yt_r3_gp_jf12` (nur getrackte Dateien), alle rot.
> - **Falle:** Eine `AssertionError` der Attrappe („unerwarteter Pfad") verschluckt
>   `_jellyfin_ruf` als Netzfehler. Ein Schlüssel in `antworten`, der die Nachfolge-Form
>   nicht trifft, testet darum still den Netz-Zweig — die Schlüssel sind jetzt
>   `/Items?`, `/Items/<id>?`, `/UserPlayedItems/`. *Seit der Nacharbeit Runde 3 entschärft:*
>   beide Attrappen tragen jeden unerwarteten Ruf in `test_filme.UNERWARTETE_RUFE` ein, die
>   Fixture macht den Test am Ende rot (fand sofort sieben stille Fälle, s. Nachtrag oben).
> - **Offen:** (1) Live nicht gemessen: ob Renés Vorschaltschutz `?ApiKey=` wie `?api_key=`
>   durchlässt. Lesende Proben dafür (nur nach Rückfrage): `GET /Users/Me?ApiKey=<token>` ohne
>   Kopf ⇒ 200, `GET /Users/Me?api_key=<token>` ⇒ 401, und (Nacharbeit Runde 3) direkt am
>   Strom-Pfad `GET {jf}/Videos/{film}/stream?static=true&ApiKey=<token>` mit `Range:
>   bytes=0-0` ⇒ 206 — sie beweist nicht, dass Jellyfin ApiKey liest (das zeigen die
>   /Users/Me-Proben), wohl aber, dass der Vorschaltschutz den Strom-Pfad mit ApiKey
>   durchlässt; sonst fielen VLC, Browser-Proxy, Umwandlung und Vorschau gleichzeitig aus
>   (EINE Stelle, kein Rückfall). Vorschlag (unbestätigt): bei 401/403 am Strom einmal mit
>   `api_key` nachfragen. (2) Vorschlag (unbestätigt): nach der
>   letzten Stellen-Meldung `POST /Sessions/Playing/Stopped {ItemId, PositionTicks}` senden
>   (PlaystateController.cs:247-249). SyncYouTube schickt nie ein Stopped; Jellyfins
>   Leerlauf-Wächter räumt die Wiedergabe erst nach 5 bis 10 Minuten ab (in 12.1 mit der
>   zuletzt gemeldeten Stelle, PR #17631). So lange steht sie in Renés Dashboard, und ein
>   „gesehen" mit Stelle unter 90 % bekäme dabei den Weiterschauen-Punkt zurück (seit der
>   Mindest-Sehzeit selten). Nicht gebaut. VERMUTUNG aus der Gegenprüfung (jellyfin12.json,
>   PR #17631): in 10.11 schrieb die Aufräumung ungenutzter Wiedergaben eine hochgerechnete
>   Stelle — Weiterschauen-Stellen aus der Zeit vor Renés Update können darum 5 bis 10 Minuten
>   zu weit liegen. Nichts gebaut. (3) Vorschlag (unbestätigt): `X-Emby-Authorization`
>   in `_kopf` weglassen (wirkt in 12 ohne Legacy-Schalter nicht mehr).

> **NACHTRAG 25.09.2026 — Mindest-Sehzeit (Runde 3, yt:mindest_sehzeit, 39cdc63).** JB-Idee
> 24.09.: „… sozusagen einen mindest timer um festzulegen - bedenken wenn ab einer bestimmten
> stelle weiter, bzw angefangen wird". „gesehen" nur bei (a) Stelle ≥ 90 % UND (b) in DIESER
> Wiedergabe geschaut W ≥ min(5 min, 50 % × (90 % der Dauer − Startstelle)); W = Spiel-
> Intervalle in Medienzeit, ein Schritt über 3 s ist ein Sprung. Regel an EINER Stelle
> (`oberflaeche.py`: `SEHZEIT`, `sehzeitUrteil`), gemessen im Browser per `timeupdate`
> (`tvpVideoVerdrahten`), im VLC im 1-s-Takt (`tvpTick`); gilt über die EINE Meldestelle für
> Ende, Esc und ⏭. Ein Sprung ans Ende zählt also nicht mehr als gesehen.
> - **Jellyfin hakt nicht selbst:** Jellyfin 12.1 setzt bei JEDER Progress-Meldung Played ab
>   > 90 % der Laufzeit, ab Laufzeit − 1 s und bei Laufzeiten unter 5 min schon ab 5 %
>   (`UserDataManager.UpdatePlayState`, Beleg mit Zeilen im Commit). Verweigert die Seite
>   „gesehen", meldet sie darum die letzte echt geschaute Stelle unter 0,9 × (Dauer − 30 s)
>   (kurze Stücke: 0). Esc-Toast: „zu wenig geschaut für „gesehen", gemerkt bei …".
>   Nebenfolge: übernimmt die Musik den VLC im Abspann, geht die Grenze statt der Stelle hinaus.
> - Prüf-Fläche: `tests/test_mindest_sehzeit.py` (10, deno mit echtem Seiten-JS, Jellyfin-
>   12.1-Orakel über jede Laufzeit ± 30 s), 21 Gegenproben (`%TEMP%\yt_r3_gp_ms`), alle rot.
>   Volle Suite 597 grün (vorher 587).
> - **Offen:** (1), (2) und (4) sind in der Nacharbeit Runde 3 behoben (s. Nachtrag oben).
>   (3) Kennt Jellyfin keine Laufzeit, setzt JEDE Meldung Played. (5) Live nicht gemessen
>   (Renés Jellyfin HTTP 401; `timeupdate` im verdeckten Tab).
>
> **NACHTRAG 25.09.2026 — Nacharbeit der Prüfung Runde 2 (nacharbeit_r2).** Gebaut,
> jeweils Test zuerst (am alten Stand rot), dann Fix, dazu je Sicherung eine rote Gegenprobe
> in einer Wegwerf-Kopie (`%TEMP%\yt_r3_na_kopie`, 28 Proben, alle rot; nur Git-getrackte
> Dateien kopiert, keine Nutzerdaten). Volle Suite: 587 grün (vorher 562).
> - **Merkmal-Ruhe dicht** (`filme.py` `_druck_in_ruhe`, `stream_url(druck=…)`): die
>   Hover-Vorschau (`snippet_backen`) hält die Ruhe ein; VLC-Start und Browser-Proxy sind
>   JBs Druck — höchstens EINE Anmeldung je Ruhe, jeder weitere Druck derselben Ruhe nimmt
>   das Token dieser Anmeldung (ein laufender Browser-Film holt seine Range-Anfragen weiter).
>   Folge: Startet JB in derselben Ruhe einen zweiten Film und ist das eine Token inzwischen
>   entwertet, scheitert dieser Start bis zum Ende der Ruhe (höchstens 10 Min) oder bis
>   ⟳ Abgleichen. Die Anzeige nennt jetzt beide Ursachen („oder ein zweites SyncYouTube
>   nutzt dieselbe Gerätekennung"). **JB-Frage offen:** eigene DeviceId je Prozess wie
>   SyncFindus (auf Renés Server entsteht dann je Programmstart ein Gerät)?
> - **Filmende ohne Vorschau-Karte** (`oberflaeche.py` `filmLokalNachziehen` → `tvMalen({vorschau:false})`):
>   Reihen und Hero werden neu gezeichnet, die Fokus-Kachel bekommt aber keine Hover-Karte
>   mit stummem Endlos-Clip mehr — mit und ohne Sleep (Zustand vor 3bd24a9). Der
>   Sleep-Wächter `test_film_ende.py` fährt tvMalen/tvFokusMalen/snippetAn jetzt ECHT
>   (Blindheits-Probe: dasselbe DOM zählt Karte + Clip, wenn JB den Fokus bewegt).
>   **Nicht gemessen:** ob Chromium nach dem Schließen des Players einen Maus-„Hover" auf
>   die Kachel unter dem ruhenden Zeiger auslöst (dann käme die Karte wie bei jedem Hover).
> - **Hülle zu meldet die Film-Stelle** (`youtube_app.py` `_film_stelle_melden`): nach dem
>   Pausieren geht die Stelle eines Jellyfin-Films über `filme.fortschritt` an Jellyfin (im
>   eigenen Faden, nie unter `_vlc_lock`; nur eine echte Stelle > 0). **„gesehen" NICHT.**
>   *(Berichtigt in der Nacharbeit Runde 3, s. Nachtrag oben: „EINE Zeile" stimmte nicht —
>   Jellyfin setzte über 90 % selbst „gesehen", die rohe Stelle entschied es also schon. Seit
>   der Nacharbeit meldet die Seite beim Entladen selbst, der Server kappt nur noch.)*
> - **Startmenü: eine stabile Regel** (`windows_kennung.py` `_startbar`): das Ziel des eigenen
>   Eintrags wechselt nur, wenn das bisherige nicht mehr startet (Programm verschoben, exe
>   entfernt). Ergebnis „behalten" statt „aktualisiert" — ein Start der exe oder des
>   Basis-Pythons stellt den Quellstart-Eintrag nicht mehr um (und umgekehrt).
>   **Grenze der Regel (Prüfung Runde 3):** „startbar" heißt nur, dass Ziel und
>   youtube_app.py als Dateien da sind. Entsteht der Eintrag einmal über ein Basis-Python ohne
>   die venv-Pakete (JB hat ihn gelöscht, erster Start auf einem frischen Rechner), bleibt er
>   dort und startet die App nicht. Auf JBs PC zeigt er auf das venv-pythonw (früher live
>   gelesen). Vorschlag (unbestätigt): für .py-Einträge nur ein Python mit pyvenv.cfg daneben
>   oder das eingebettete Python des Quellstart-Pakets als startbar werten. **JB-Frage:**
>   „der erste Eintrag gewinnt" (heute) oder „Quellbetrieb/venv hat Vorrang"?
> - Kleinere: abgewiesenes „gesehen" bleibt als `abgewiesen` liegen, auch wenn die jüngere
>   Stelle ankommt; langsamer VLC-Start wird nach 8 Takten nicht mehr gestoppt (Zustand vor
>   3bd24a9; gestoppt wird nur bei `ende` oder wenn der Film lief); der Freigabe-Stopp mit
>   `nur_key` überholt keinen wartenden Musik-Start mehr; jede libvlc-Meldung außer „Pause"
>   löscht den Pause-Beginn; `yt_fehler.jsonl`/`js_fehler.jsonl` am `DATEN_DIR`;
>   „Weiterschauen" behält die Meldungen dieser Seite auch in frisch geladenen Reihen
>   (`filmReihenAnwenden`; gilt je Seiten-Sitzung, nach F5 wieder der Spiegel).
> - **Test-Wachen** (`tests/conftest.py`, geprüft in `tests/test_wachen.py`): Startmenü in
>   JEDEM Test gesperrt und laut (auch im Hintergrundfaden), yt-dlps eigene Firefox-Suche
>   umgebogen, `youtube_app` früh importiert. Nebenfund dabei: `pytest tests/test_jellyfin_zugang.py
>   -k zustand_route` allein las JBs echte `filme_zustand.json` (der lazy Import rief
>   `filme.einrichten(System\)` NACH dem des Tests) — nur lesend, jetzt behoben.
> - **Firefox-Modus:** JBs Profil hat ein `cookies.sqlite-shm` (32 KB, nur Größe gelesen) —
>   starkes Indiz für den Normalmodus, nicht exklusiv. `test_cookies_wal.py` prüft jetzt beide.
>
> **Aus der Prüfung nachgetragen (Übergabe fehlte):**
> - **Folgen-/Filmende (3bd24a9):** „gesehen" ab 90 % bei Ende, Esc und ⏭ (seit 39cdc63 dazu
>   die Mindest-Sehzeit, s. oben); Sleep: nach einem
>   Filmende startet nichts (`nachFilmEnde`). Prüf-Fläche: deno mit echtem Seiten-JS +
>   Jellyfin-/libvlc-Attrappen; live NICHT gemessen (Renés Jellyfin setzt „gesehen"? bleibt
>   libvlc am Netz-Strom-Ende in `ende`?). **JB-Fragen offen:** Live-TV am Stromende
>   schließen?; Profile und Gäste („gesehen" je Profil?); soll der Spiegel auch beim
>   Nachreichen aus der Warteschlange nachziehen?; ⏮ im Abspann meldet die laufende Folge
>   als gesehen (Jellyfin-konform, von JB nicht ausdrücklich bestätigt); Esc ohne offene
>   Fernbedienung (Seite neu geladen) meldet nie „gesehen" (seit der Nacharbeit Runde 3 mit
>   Dauer und Stelle aus dem VLC-Status und unter Jellyfins Grenze, s. Nachtrag oben).
> - **„Pause sperrt 30 Min" (449e163, `youtube_app.py` `PAUSE_SPERRE`/`_vlc_haelt_neustart_auf`):**
>   Offen: Probe mit echtem libvlc (VLC pausieren, eine Backend-.py ändern, der Neustart muss
>   rund 30 Min warten); ein pausierter Film schließt sich nach 30 Min beim Neustart weiterhin
>   (Option D nicht gebaut).
> - **Tempo/Stumm beim Folgenwechsel (c4b938a, JB „Behalten"):** gebaut für ⏭/⏮. Offen
>   (JB-Richtung): Stumm im VLC (kein Server-Befehl), Tempo beim Rückfall zum VLC; Edge und
>   VLC nicht live gemessen.
> - **Kennung (e10e2d9):** Medien-Overlay und Medientasten mit `JBK.SyncYouTube` live nicht
>   gemessen (`tools/medien_probe.py liste`, vor jedem Tastendruck fragen — Spotify). Die
>   Hülle trägt dieselbe Kennung: eine angeheftete Hülle startet Server + Browser
>   (Vorschlag, unbestätigt: RelaunchCommand am Hüllen-Fenster).
> - **Hülle zu (53352ce):** Fortsetzen per Handy/Medientaste spielt ins zerstörte Panel (Ton
>   ohne Bild; ↻ startet sichtbar neu) — eigener Auftrag. Musikvideos im Panel werden
>   pausiert (JB-Frage offen, Tragweite im Bestand gering).
>
> **Aufräumen offen (JB-Freigabe):** Wegwerf-Ordner der Prüfrunden in `%TEMP%`
> (`yt_r2_*`, `yt_r3_na*`, zusammen rund 1,1 GB (gemessen 25.09.); `yt_r2_cw` und `yt_r2_hz_kopie` enthalten
> Kopien von config.json u. a.) — Papierkorb, nicht löschen. Im Startmenü liegt ein toter
> Eintrag „Claude Dashboard" (Ziel `…\Claude Sync\SyncEngine\…\pythonw.exe`, seit Stage 3
> weg; Vorschlag, unbestätigt: rückholbar ins Archiv).

> **NACHTRAG 23./24.09.2026 — Medientasten: gemessen, wo sie wirken, und ausgebaut
> (Film/Serien, Handy-Sperrbildschirm, VLC über den Server).**
>
> **Wo die Medientasten wirken (live gemessen, echte Tastendrücke per SendInput mit
> Tastatur-Scan-Codes, Wirkung in Windows' eigener Sitzungsliste abgelesen):**
> Edge, Firefox und die Programm-Hülle (WebView2, Windows nennt sie
> „msedgewebview2.exe") — Weiter, Zurück, Play/Pause auch mit Fenster im Hintergrund.
> Die Erwartung der Übergabe, eine eingebettete WebView melde nichts an, war falsch;
> globale Hotkeys in der Hülle sind NICHT nötig. Gerät VLC: ohne Server-Anmeldung kennt
> Windows die Seite nicht (gemessen) — deshalb jetzt `medien_smtc.py` (pywinrt, JB-Go
> 23.09.): der Server meldet VLC selbst an (Titel, Interpret, **Album**, Cover,
> Zeitleiste), Weiter/Zurück laufen als `taste`-Zähler zur Seite. Live Ende zu Ende 8/8.
> **Wer die Taste bekommt, entscheidet Windows:** eine neu entstehende Sitzung wird
> „aktuell", danach behält Spotify sie, solange es spielt — und Spotify pausiert bei
> Play/Pause zusätzlich SELBST mit, solange es spielt (pausiert startet es nicht).
> Das Windows-Overlay konnte ich nicht fotografieren (das Bildschirm-Werkzeug schwärzt
> System-Flächen); Beleg ist die Sitzungsliste (dieselbe Quelle wie Overlay/Medienkarte).
>
> **Gebaut (JB-Entscheidungen 23.09.):** gemeinsamer Baustein `medien_session.py`
> (PC + Handy, per Platzhalter eingesetzt); EINE Weiche in `oberflaeche.py`: Film offen
> → Film, Gerät VLC → Server, sonst `<audio>`. Serien: ⏭ = nächste Folge, ⏮ = JBs Regel
> „Variante C, x = 3 s" (Vorfolge an gemerkter Stelle, zu Ende geschaut/≥ 90 %/≤ 30 s →
> Anfang; 2. Druck Anfang; dann Musik-Regel). Einzelfilm: kein ⏭/⏮ (bewusst, kein
> Knopf, der ins Leere greift). Musik läuft beim Filmstart weiter („wie bisher"), die
> Tasten gehören dem Film. Handy `/m`: Sperrbildschirm-Steuerung nur im Modus „Handy".
> Mit repariert: VLC-Play schickte `play` ohne Titel; VLC per Taste nicht anzuhalten;
> Zeitleiste hinkte nach Sprüngen/Tempo; Crossfade-Übernahme meldete „paused"; Pause
> mitten im Crossfade ließ den nächsten Titel weiterspielen; leere Warteschlange ließ
> Crossfade/VLC weiterlaufen; Radio-⏭ lief ans Listenende; K/N/P starteten Musik unter
> dem Film; Handy-Titelende schaltete den PC weiter; ein abgelöstes Medienelement hielt
> einen toten „pausiert"-Eintrag (VLC-Wechsel doppelt, Handy-Sperrbildschirm tot) —
> `medienSitzung().freigeben()`. Nebenbei: bei Folgen kam die Film-Meta nie im Player an
> (tote Zeitleiste im Transcode) — jetzt durchgereicht.
>
> **Prüfung:** Wächter `tests/test_medientasten_verhalten.py` + `test_medientasten_randfaelle.py`
> (führen das echte JS mit deno aus, rote Gegenproben je Wächter) und
> `tests/test_medien_smtc.py`; SyncYouTube-Suite 354 grün (Stand 24.09.); Live im
> echten Edge 21/21 (Musik, Crossfade, Radio, Film mit eigener Videodatei als Quelle),
> Freigabe 8/8, Server-VLC 8/8, Hülle im VLC-Modus ohne Doppel-Eintrag.
> Messwerkzeug für die nächste Runde: `System/tools/medien_probe.py` (liste · taste
> `--nur-wenn` · knopf) — **vor jedem Tastendruck fragen, Spotify läuft bei JB oft.**
>
> **Runde 2 (24.09.): skeptische Prüfung + echte Tasten.** Ein Prüf-Workflow (drei
> Blickwinkel, jeder Befund von einem unabhängigen Widerleger angegriffen) fand 22
> haltbare Randfälle; alle behoben und in `tests/test_medientasten_randfaelle.py`
> festgenagelt (u. a. 2. ⏮ während die Vorfolge lädt, Esc während eines Wechsels,
> Server-⏭ wirkte in jedem offenen Tab, mehrere schnelle Drücke schrumpften zu einem).
> **Echte Tastendrücke** (Spotify + Firefox von JB pausiert, vor jedem Druck geprüft):
> Musik 4/4, Serie 4/4, VLC über den Server 3/3. Zwei echte Fehler, die nur so zu
> finden waren: (a) **Mit Fokus auf dem Fenster kommt eine Medientaste ZWEIMAL an**
> (Windows-Sitzung + keydown): VLC-⏯ pausierte und die Seite schaltete sofort zurück,
> VLC-⏭ sprang zwei Titel. Jetzt wirkt der keydown-Rückfall nur, wenn es keine
> SyncYouTube-Sitzung bei Windows gibt (`medienTasteHatSitzung`). (b) **Nach einem
> Folgenwechsel gab Windows bei der nächsten Pause die „aktuelle Sitzung" an Firefox
> ab** — der nächste ⏯ hätte Firefox gestartet (auch ohne Taste reproduziert; Musik
> nicht betroffen). Ursache: das alte `<video>` wurde geleert, bevor die neue Folge
> spielte. Jetzt verstummt es sofort und wird erst bei `playing` der neuen geleert
> (`tvpAbgeloestFreigeben`); 7 Varianten gemessen, danach blieb Edge in allen aktuell.
> Hinweis zur Zurück-Regel: 2× ⏮ nach einem ⏭ landet regelgerecht in der VORVORIGEN
> Folge, weil der ⏭ die Stelle der Vorfolge (wenige Sekunden = „kaum angefangen") merkt.
>
> **Offen / nicht gemessen:** (1) **Transcoder-Sprung:** im Transcoder-Modus setzt ein
> Sprung eine neue Quelle im SELBEN `<video>` (`tvpSpringeAuf`, Selbstheilung auf den
> Transcoder) — gemessen löst genau das dieselbe Windows-Herabstufung aus (Variante V5).
> Behebung wäre ein Element-Tausch beim Springen (tieferer Umbau, nicht gemacht).
> (2) Handy-Sperrbildschirm auf einem
> ECHTEN Handy (Android/iOS) — nur im Desktop-Browser gemessen. (3) Film-Teil gegen
> Renés Jellyfin: letzter erfolgreicher Abruf vor der Störung am 20.09. um 14:52;
> zwischen dem 20.09. (14:52) und dem 24.09. (14:20) hat René auf Jellyfin 12.1.0
> aktualisiert, danach bekam jeder Datenabruf „Items-Abruf HTTP 401" (51 Fehlversuche),
> die Folgenliste kam leer. Ursache und Behebung am 24.09.: Jellyfin 12 verlangt das
> Token im Authorization-Kopf (Commit a60f93e). Seitdem läuft der Katalog-Abzug wieder
> (`System/filme_zustand.json`: letzter Erfolg 24.09. 18:01, 5118 Einträge, kein
> Fehler; `filme_katalog.json` meldet server_version 12.1.0). Die Medientasten-Prüfung
> selbst lief mit eigener Videodatei + Attrappe der Folgenliste. (4) Windows zeigt die
> Hülle als „msedgewebview2.exe". Die gemessene Kennung des Servers
> „Microsoft.AutoGenerated.{9C659DC1…}" gehört zur Startmenü-Verknüpfung
> „IDLE (Python 3.14)": Ohne eigene App-Kennung ordnete Windows den pythonw-Prozess
> der einzigen Verknüpfung auf die pythonw.exe des Basis-Pythons zu. Seit 24.09. (Commit e10e2d9) meldet
> sich der Server als `JBK.SyncYouTube` und legt den Startmenü-Eintrag „SyncYouTube"
> mit dieser Kennung an (vorhanden seit 24.09. 21:17, Ziel pythonw + youtube_app.py,
> nur gelesen). Wie Windows' Medien-Overlay ihn jetzt benennt, ist nicht gemessen
> (dafür braucht es einen echten Tastendruck).
> **Startdateien (24.09., JB: „am besten nur eine [der beiden gleichen]"):**
> „SyncYouTube (ohne Fenster).vbs" liegt im Familien-Archiv
> (`_Archiv\SyncYouTube-Startdatei_2026-09-24\`, Rückholbefehl in `_Archiv\REGISTER.md`).
> Oben bleiben `SyncYouTube.exe`, `SyncYouTube.bat` und `SyncYouTube-Fenster.bat`;
> ohne Aufblitzen startet der Startmenü-Eintrag „SyncYouTube" — die Variante, mit der er
> angelegt wurde (Quellstart oder exe); sein Ziel wechselt nur, wenn es nicht mehr startet
> (seit 25.09., vorher gewann der letzte Start).
> **Offen (Ordnung):** Oben liegen noch drei Laufzeit-Reste vom 21.07.
> (`geladen_log.json`, `warteschlange.json` mit leerer Liste, `yt_status.json` ohne
> Zähler); die lebenden Dateien liegen in `System\`. Nicht archiviert, weil die obere
> `geladen_log.json` 5 ihrer 22 Einträge hat, die in `System\geladen_log.json` fehlen
> (`UWgzB5B_fjM|lokal`, `NRTCn3eUFTM|audio`, `aqz-KE-bpKQ|lokal`, `2rBLRkgac6w|lokal`,
> `OMOGaugKpzs|lokal`). Alle fünf zeigen auf Dateien, die es nicht mehr gibt; dieselben
> Video-Kennungen stehen unten unter anderer Qualität. Entscheidung offen: die drei
> Dateien trotzdem rückholbar ins `_Archiv` (Vorschlag, unbestätigt) oder die fünf
> Einträge vorher unten nachtragen.
> **Firefox-Cookies samt WAL (24.09., Lehre aus SyncFindus):** yt-dlp 2026.08.19 kopiert
> beim Cookie-Lesen nur `cookies.sqlite`, nicht das `-wal` (`yt_dlp/cookies.py`,
> `_open_database_copy`); frische Anmelde-Cookies nach einem neuen YouTube-Login fehlten
> deshalb. Jetzt entsteht jeder YoutubeDL in `youtube_app._ydl`: `cookie_kopie.firefox_profil`
> legt vorher eine vollständige Kopie in einen frischen Temp-Ordner (Hauptdatei und `-wal`
> nur als Datei gelesen, WAL-Kopf-Vergleich, Backup-API, Rollback-Modus) und gibt yt-dlp
> dessen Pfad als Profil; danach ist der Ordner weg. Jeder Fehler führt still auf den
> alten Weg `("firefox",)`. Wächter `tests/test_cookies_wal.py` (25 Tests, 14 rote
> Gegenproben); `tests/conftest.py` hält die Profilsuche in JEDEM Test von JBs echtem
> Firefox fern. **Nicht gemessen:** ein Lauf mit JBs echtem Profil gegen YouTube (Tests
> dürfen beides nicht). Exklusiv-Sperre: JBs Profil hat ein `-shm`, also sehr
> wahrscheinlich Normalmodus; der Test prüft seit 25.09. beide Fälle. **Falle:** Pythons `Connection.backup` direkt auf eine fremd gesperrte
> Datenbank kehrt nie zurück — es wiederholt „database is locked" endlos (Gegenprobe nach
> 600 s abgebrochen).
> **Nebenbefunde (nicht behoben):** Die Hülle HÄNGT (UI-Faden reagiert nicht), wenn die
> Seite im Gerät VLC neu geladen wird (einmal gemessen; die Selbst-Erneuerung lädt
> neu, wenn sich oberflaeche.py ändert). ~~Die Hülle meldet ihr Video-Panel beim
> Schließen nicht ab~~ (behoben: 06b4098, seit 53352ce samt Pause). Crossfade blendet auf 100 % ein und
> springt dann auf die eingestellte Lautstärke; Sleep-Timer „nach diesem Titel" und
> Wiederholen-eins werden von Crossfade/Gapless übergangen. ~~Folgenende wird nie als
> gesehen gemeldet~~ (behoben: 3bd24a9).

> **NACHTRAG 08.09.2026 (spät) — v.1.2.5 veröffentlicht: das erste Release mit
> Selbst-Update als Vorgabe.**
>
> `SyncYouTube.exe` 199,8 MB, EV-signiert (JBK-Holding, Sectigo, RFC-3161-Zeitstempel,
> `Status: Valid`), SHA-256 `bc2e1e06…`. Sechs Anhänge wie immer: exe + `.sha256`,
> Quellstart-ZIP + `.sha256`, `updates.json` und die signierte `.xpi` (die beiden
> letzten müssen bei JEDEM Release dabei sein, sonst läuft der Addon-Update-Kanal
> über `latest/download` ins Leere).
>
> **Live geprüft gegen das echte Release**, nicht nur gegen die Quelle:
> `update.check_release("1.2.4")` meldet `available=True`, Version 1.2.5, und
> wählt `SyncYouTube.exe.sha256` — nicht die Prüfsumme des Quellstart-Pakets.
> `check_release("1.2.5")` meldet `aktuell`. Die veröffentlichte Prüfsumme stimmt
> mit der gebauten Datei überein. Die gebaute exe wurde im Testmodus gestartet und
> zeigt `vorgaben_stand: 1` sowie die fünf zuvor verlorenen Schlüssel.
>
> **Dabei repariert, mein eigener Fehler:** Die Release-Notizen von sechs Fassungen
> trugen verstümmelte Umlaute („trÃ¤gt“ statt „trägt“) — der Text war beim Schreiben
> durch eine Leitung gelaufen, die ihn als cp1252 statt UTF-8 gelesen hat.
> Zurückgerechnet und einzeln nachgeprüft; alle 18 Releases sind jetzt sauber.
> **Merke:** Release-Notizen NUR über `gh release create/edit --notes-file` mit einer
> UTF-8-Datei schreiben, nie über die Befehlszeile.
>
> **VirusTotal ist seit v.1.2.6 erledigt** und kein Handgriff mehr:
> `SyncDashTray/System/virustotal_pruefen.py` schlägt erst per Prüfsumme nach und
> lädt nur mit `--hochladen` hoch (große Dateien über die eigens angeforderte
> Adresse — unsere exe fällt immer über die 32-MB-Grenze). Ergebnis für v.1.2.6:
> exe **0 von 64**, Quellstart-ZIP **0 von 75**, Signatur von VirusTotal als
> gültig erkannt, Microsoft `undetected`. Links stehen im Release.
> **SyncManga 0.4.4 ebenfalls gescannt:** Setup 0 von 75, exe 1 von 75 (allein
> APEX, ein Maschinenlern-Motor mit generischem Urteil; Microsoft war im Juli
> noch ein Treffer und ist jetzt sauber — die Signatur wirkt).
> **Offen bleiben SyncYouTube v.1.2.4 und v.1.2.5** (beide überholt, je ein
> 200-MB-Upload).
> **FALLE:** Im `cmdkey`-Passwort-Prompt fügt Strg+V NICHT ein, es tippt `0x16`.
> Deshalb `virustotal_pruefen.py --schluessel-setzen` benutzen — das prüft die
> Form (64 Hexzeichen) und speichert nur, was wirklich einer ist.

> **NACHTRAG 08.09.2026 — Einheitlichkeit, Signatur, Lizenz, Beschreibungen.**
> Stand danach: **v.1.2.4 signiert veröffentlicht; 284 Tests grün** (Stand
> 08.09.2026 abends, nach der Vorgaben-Runde).
>
> 1. **Gleiche Dinge sind jetzt gleich groß** (JB am Screenshot: *„wieso haben
>    nicht alle videos die gleiche hoehe?"*). Gemessen vorher: Kachelbilder 142
>    **oder** 250 px, Titel 17 **oder** 34 px, 32 Bedienelemente in **elf**
>    Höhen. Ursache bei den Kacheln: `aspect-ratio:16/9` am Rahmen hat **nie**
>    gegriffen, weil `.kachel` ein Spalten-Flex ist und seine Kinder damit
>    `min-height:auto` haben — ein quadratisches Album-Bild gewinnt. Die
>    16:9-Bilder sahen nur zufällig richtig aus. Jetzt `flex:none;min-height:0`.
>    Bedienelemente über zwei Tokens (`--pille-h` 24, `--feld-h` 32), fünf
>    bewusste Gruppen. Wächter `test_einheitliche_groessen` (Quelle, browserfrei).
> 2. **EV-Signatur ist der Grund, warum die GitHub-Fassung bei Kumpels nach
>    Tagen ausfiel** — Defender nahm Teile in Quarantäne. v.1.2.4 ist die erste
>    mit Sectigo-Zertifikat (JBK-Holding) und RFC-3161-Zeitstempel, `Status:
>    Valid`. Bauweg: `System/build_release.py` — bauen, signieren, **erst dann**
>    Prüfsumme, nach oben kopieren; bricht ab, wenn ein Schritt fehlt.
> 3. **Lizenz-Abschnitt** auf acht Zeilen gekürzt (JB: *„Wieso ist der Lizenz
>    Abschnitt ein eigener Aufsatz?"*), Einzelheiten in `LIZENZEN.md` — 47
>    mitgelieferte Bestandteile, vorher waren fünf genannt. Wächter
>    `test_syncyoutube_lizenzen` misst gegen die PyInstaller-Stückliste.
> 4. **Beschreibungen** standen immer in den Dateien, wurden nur nie gelesen.
>    Dritte Stufe der Kaskade in `SyncFindus/System/zubringer_clips.py` liest
>    sie per ffprobe aus den Tags: **129 von 148 im Probelauf** (vorher 0).
>
> **ENTSCHIEDEN am 08.09.2026 abends** (JB: *„selbst-update standardmäßig an,
> cookies aus“*) — **und die zweite Hälfte wenige Minuten später
> zurückgenommen** (*„cookies wieder an, das Risiko ist zu groß“*). Es gilt
> also: `auto_update` steht auf **True**, `cookies_browser` bleibt bei
> **„firefox“**. Der Rückzieher war richtig, und der eigene Code sagt warum:
> ohne Cookies wählt yt-dlp die nicht angemeldeten Vorgabe-Zugangswege, also
> genau die, gegen die YouTube sperrt (`_ist_sperre`, 403-Runde 07.09.2026).
> Zum Zeitpunkt der Rücknahme war gemessen keine einzige Installation
> umgestellt, deshalb genügte das Entfernen des Eintrags aus
> `VORGABEN_UMSTELLUNG` — kein Rück-Umstellungs-Schritt nötig.
>
> Wichtiger als der eine Wert ist, was die Prüfung dabei ans Licht brachte:
> - Eine reine Vorgaben-Änderung hätte **niemanden** erreicht. `config_laden`
>   lässt die gespeicherte `config.json` gewinnen, und die hat wirklich jeder —
>   das Programm schreibt sie beim Start selbst. In JBs eigener Datei stand
>   `auto_update: false`. Deshalb gibt es jetzt `VORGABEN_STAND` +
>   `_vorgaben_nachziehen`: der neue Wert (nur `auto_update`) wird **einmalig**
>   auch in bestehende Installationen gezogen, aber nur dort, wo noch der alte
>   Auslieferungswert steht, und mit einer Sicherung `config_vor_stand1.json`.
>   Die Cookie-Wahl fasst die Umstellung ausdrücklich NICHT an.
>   **Live belegt:** am 08.09. um 20:12 hat der Tray SyncYouTube normal
>   gestartet; die Umstellung lief dabei auf JBs echtem Rechner und tat genau
>   das — `auto_update` false → true, `cookies_browser` unverändert `firefox`,
>   `config_vor_stand1.json` daneben. **Achtung:** das gilt für
>   Quellcode-Installationen. Die veröffentlichte exe v.1.2.4 wurde vor der
>   Entscheidung gebaut und trägt `auto_update: False` im Code; sie zieht
>   nichts nach. Das kommt erst mit dem nächsten Release.
> - **Fünf Einstellungen überlebten bisher keinen Neustart.** Der Filter
>   `if k in STANDARD_CONFIG` warf `name_schema`, `auto_umbenennen`,
>   `untertitel_sprachen`, `wiedergabe` und `wg_sub_migriert` weg — alles
>   Schlüssel, die das Programm selbst schreibt. Namensschema, Auto-Umbenennen,
>   Untertitel-Sprachen und die global gemerkte Untertitel-Größe standen nach
>   jedem Start wieder auf Anfang. Jetzt in `STANDARD_CONFIG`, mit Auto-Discovery-
>   Wächter (`test_vorgaben`).
>
> **WARTET AUF JB — zwei Entscheidungen, nichts davon begonnen:**
> - **`SyncManga-Setup.exe` hat keine `.sha256` im Release** (beim Scan
>   aufgefallen). Der Standard verlangt zu jeder ausgelieferten Datei eine
>   Prüfsumme. Nachreichen ist ein Eingriff in ein veröffentlichtes Release —
>   JBs Entscheidung.
> - **Scharfer Clips-Lauf in SyncFindus**, damit die 129 Beschreibungen ins
>   Register wandern. Der Probelauf hat nichts geschrieben.
>
> **ZU KLÄREN, weil die Prüfung es aufwarf (Richtungsfragen, nicht gebaut):**
> - **Der Updater prüft die Signatur der geladenen exe nicht** — nur Größe und
>   SHA256, und beide stammen aus derselben Quelle. Ein versehentlich unsignierter
>   Release ginge jetzt automatisch an alle. Eine Authenticode-Prüfung vor dem
>   Tausch wäre der Riegel, ist aber eine eigene Runde.
> - **`build_release.py` warnt nur, wenn der eToken fehlt, statt abzubrechen.**
>   Fail-closed wäre sicherer, verböte aber jeden Bau ohne gesteckten Token —
>   das ist JBs Entscheidung, keine Aufräumarbeit.
> - **Eine bereits ausgefallene Installation heilt das alles nicht.** Liegt die
>   alte exe beim Freund in Quarantäne, läuft sie nicht und kann sich auch nicht
>   selbst aktualisieren. Er muss v.1.2.4 einmal von Hand holen; ab dann trägt
>   das Selbst-Update.
>
> **FALLE aus dieser Runde (auch im Lehrbuch, L71):** Ein Wächter, der die
> Quelle liest, misst leicht die **Erklärung statt der Sache**. Meine erste
> rote Gegenprobe war grün, obwohl die Zusage weg war — der Kommentar
> *innerhalb* der CSS-Regel enthielt den gesuchten Text. Kommentare vor dem
> Prüfen herausschneiden, Namen an Wortgrenzen vergleichen, bei mehreren
> Treffern den **exakten** Selektor nehmen, und die Gegenprobe an der echten
> Datei fahren (Prüfsumme vorher/nachher).

> **NACHTRAG 07.09.2026 — die 403-Runde. MUSS in den nächsten Bau.**
> Sieben gemessene Befunde, alle repariert, 264 Tests grün (vorher 246):
>
> 1. **yt-dlp stand auf 2026.07.04.** In dieser Fassung ist `android_vr` der
>    erste Vorgabe-Zugangsweg (`YoutubeIE._DEFAULT_CLIENTS`), und YouTube weist
>    den seit dem 17./18.08.2026 mit HTTP 403 ab (yt-dlp-Fehler 17456, behoben
>    in 2026.08.19). Die Familien-venv steht jetzt auf **2026.08.19**
>    (`_DEFAULT_CLIENTS` = `('visionos', 'web')`), der Pin in
>    `SyncDashTray/System/requirements.txt` ist nachgezogen. Der Bau nimmt
>    yt-dlp über `collect_all('yt_dlp')` aus der venv, es reicht also, neu zu
>    bauen. Wächter: `test_yt_dlp_kennt_android_vr_nicht_mehr_als_vorgabe`.
> 2. **Der Parameter `geo` in `_download_lauf` verdeckte das Modul `geo`.** Im
>    Fehlerzweig stand damit `False.ist_geo_fehler(...)`: jeder gewöhnliche
>    Download-Fehler flog als `AttributeError` aus der Funktion, bevor Backoff,
>    `DAUERHAFT`-Liste oder `max_wiederholungen` überhaupt gefragt wurden. Der
>    komplette Neuversuch-Mechanismus war unerreichbar, aufgefangen hat es erst
>    das Netz in `worker_schleife`. Parameter heißt jetzt `geo_lauf`.
> 3. **Eine Sperre wurde als Cookie-Problem geheilt.** YouTube hängt an jede
>    Bot-Meldung `YoutubeIE._youtube_login_hint` an — darin stehen »cookie« UND
>    »browser«, also warf `_ist_cookie_fehler` die Cookies weg und lief sofort
>    erneut los; ohne Cookies wählt yt-dlp aber genau die gesperrten Wege. Neu:
>    `_ist_sperre()` greift VOR der Cookie-Prüfung, ein gesperrter Eintrag geht
>    nicht in den Backoff.
> 4. **Gegen YouTube bremste nichts** (gegen MusicBrainz an sieben Stellen).
>    `_ydl_basis_opts` hat jetzt `sleep_interval` 2, `max_sleep_interval` 8,
>    `sleep_interval_requests` 1. Fehlschläge landen dauerhaft in
>    `System/yt_fehler.jsonl` (Muster `js_fehler.jsonl`, Deckel 200 KB), und
>    die Anzeige übersetzt Bot-Verdacht, 429 und 403 verständlich.
>
> **Das erklärt aber NICHT das Zeitmuster bei JBs Kumpel** („geht nach ein paar
> Tagen nicht mehr"). Dessen Ursache ist der Windows-Defender, der die
> unsignierte PyInstaller-Datei nach einem Muster-Update in Quarantäne setzt.
> Die Lösung dafür ist die EV-Signatur beim nächsten Bau — der Hardware-Token
> muss dafür stecken (`signieren.py --status` meldete am 07.09. »Zertifikate:
> keines«).

> **06.09.2026:** Dies ist DIE aktuelle Übergabe von SyncYouTube (Stand 05.08., Build 171). Am 06.09. aus `System/` nach `System/docs/` verschoben, damit sie versioniert ist (Whitelist-.gitignore gibt nur `System/docs/*.md` frei; Befund SyncYouTube-05). Der ältere Stand vom 23.07. liegt daneben in `NAECHSTE_SESSION.md`.

> **NACHTRAG 05.08. (fünfte Runde, Builds 169–171, JB: „Keine Fragen,
> abarbeiten"):** Untertitel am Gerät VLC geheilt (vlcPosGeschaetzt treibt
> subTick; vlcKarLauf-Bildtakt) · Versatz kompakt (‹ › + ±-Schrittweite
> 0,1/0,5/1/5) · **Disney-Untertitel-Panel** (Live-Vorschau, 6 Schriften,
> Farben, Deckkraft, Schatten, Hintergrund, Reset; Look = `sub_look`-Dict
> Server-global; alte Presets migriert; FERNBEDIENUNG: Pfeil-Fokus im
> Panel) · Play-Symbol sofort, ±10 s immer in der Leiste · Karaoke-Wischer:
> Sing-Dauer gedeckelt (Instrumental-Lücken) · **GROSSE ETAPPE Stufe A
> GEBAUT: VLC-Video ins Hüllen-Fenster** — Server `cmd=fenster` (hwnd,
> überlebt Selbstheilung, 0=Rückweg, Status `eingebettet`), Hülle =
> WinForms-Panel per form.Invoke im UI-Thread (**MERKE: rohes
> CreateWindowExW im js_api-Worker stirbt mit dem Thread!**), UI meldet
> Fläche aus vlcTick (huelleVideoRect, dpr, Leiste bleibt frei).
> **OFFEN: JBs Sichttest** (SyncYouTube-Fenster.bat → Gerät VLC → Video);
> danach Feinjustage (DPI/Ränder), Browser-Player in der Hülle abschalten
> (Ein-Player-Ziel), TV-Design-Runde.

> **NACHTRAG 05.08. (vierte Runde, Builds 165–168):** **VLC = Browser-Optik
> (165):** VLC-Ansicht rendert pl-vizwrap + plBarHTML; plbTick/posMerkerMalen/
> plbSpringen/plbSeek* lesen am Gerät VLC den 1-s-Status; ↻ im Rechtsklick.
> **Untertitel-Panel am 💬 (166/167, JBs Vorbild-Bilder):** Modus (OHNE
> Transkript — das lebt in den Optionen), Sprache dedupliziert (xx-orig
> verdeckt xx), Größe als gestaffelte Aa, Stil-Presets IM eigenen Look,
> Versatz ±0,1/±0,5/±1/±5; Größe+Stil SERVER-global (Wiedergabe-Regel
> sub_groesse/sub_stil — versionsfest), Versatz je Titel; Panel mit direkten
> Listenern + eigener pointerdown-Schlucker (JB: „kann nichts anklicken").
> **Programm-Hülle Grundstein (168, JB-GO):** `System/huelle.py` (pywebview
> 6.2.1, zentrale venv) + `SyncYouTube-Fenster.bat` — eigenes Fenster lädt
> die Oberfläche, startet den Server bei Bedarf; Whitelist-.gitignore
> erweitert. Build 169: Untertitel am Gerät VLC geheilt (vlcPosGeschaetzt
> als geräte­feste Zeit-Quelle in subTick + vlcKarLauf-Bildtakt), Versatz-
> Zeile kompakt (‹ › + ±-Schrittweiten-Knopf 0,1/0,5/1/5).
> **NÄCHSTE ETAPPE = VLC-set_hwnd-Einbettung ins Hüllen-Fenster (JB-GO
> 05.08. erteilt: „Ansonsten go")**
> (Video eingebettet, Browser-Player fällt in der Hülle weg — JBs
> Ein-Player-Ziel), danach die eigene TV-Design-Runde. Handy/j-bk.org
> behalten den Browser-Weg (derselbe Server).

> **NACHTRAG 05.08. (dritte Runde, Builds 159–163, JBs Bilder-Paket):**
> **Layout-Reflow (159):** `LK.entklemmen` im geteilten layout_kern (Master
> SyncDashTray + byte-gleicher Inline-Block!) — die Minima-Klemme schob bei
> schmalem Fenster Panels untereinander; jetzt Zeilenumbruch in Lese-
> Reihenfolge, Basis bleibt heilig. **VLC-Ansicht (160):** Cover groß wie im
> normalen Player, Knopf heißt immer „🖥 VLC" (Toggle), Selbstheilung
> (RLock + Reset + Wiederholung, UI verbindet bei „fehler" einmal selbst neu),
> ↻-Knopf, ✂ Clip (Dauer/Pos aus VLC-Status), Wiedergabe-Merker (gelber
> Strich, ytdl_pos_v1). **Live-Titel-Regel (161):** sagt der QUELL-Titel
> live/unplugged, gewinnen offizielle Live-Alben (Nirvana → „MTV Unplugged in
> New York"); ohne Marker bleiben sie verboten; `live_hinweis` trägt die Info
> in den Blank-Zweitversuch. **Untertitel-Versatz (162):** , und . = ±0,5 s,
> je Titel absolut gemerkt (Regel `sub_offset`), zentral in subTick.
> **iTunes-Rückfall (163):** offene iTunes-Suche ergänzt NUR leere Felder
> (Album/Jahr/Genre) + 600×600-Artwork hinter dem CAA (`cover_url` am
> Eintrag, nur_cover-Zweig kennt sie); Treffer nur bei Titel+Künstler-
> Abgleich (exakt/Präfix). **MERKE:** Früher getaggte Titel behalten alte
> Album-Wahlen — Reparatur nur über gezielten keys-Relauf; Radar-Kandidaten
> für den Rest: AcoustID (Key nötig, JB-Frage) + Whisper-Wort-Karaoke
> (lokal, autark) in `Doku/IDEEN_RADAR.md`.

> **NACHTRAG 05.08. (zweite Runde, Builds 154–158 + Addon v1.2.0):** JBs
> Fragen-Paket komplett. **Addon v1.2.0 signiert + im Kanal (Außen-Verifikation
> hash-exakt `3b4fd448…`): Offline-Warteschlange** — Klicks ohne laufende App
> landen persistent in storage.local (`ytdl_merk`, Schlüssel `<id>|<quali>`
> bzw. `liste:<lid>` OHNE v= — Mix-Falle!), gelbes „…" (Klasse `merk`),
> Klick entfernt; Minuten-alarm+ping flushen, App toastet via
> `/api/addon_nachschub`. Review (28 Agenten) fand 12 echte Fehler vorab;
> Node-Harness (Scratchpad-Muster) beweist die Flows gegen das echte
> background.js. **Album-Wahl-Wurzelfix (155):** `_mb_norm_titel`
> (MB-Typografie), kein `NOT secondarytype:*` mehr (warf Originale raus),
> ALBUM-zentrierte Wahl über alle exakten Treffer (Suche limit 100),
> Soundtrack = kanonisch. **Video-Cover als Sidecar `Cover/<id>.jpg` (156)**
> — Dateiart ist KEIN Musik-Kriterium (JB). Bibliothek: 46 Cover, 43 Genres.
> **VLC-Rest (154):** set_rate (Play/Menü/Hotkeys) + .vtt als add_slave-Spur.
> **UI (157):** Eigenschaften wie iTunes, Untertitel-Größe/Presets
> (`ytdl_substil`), Kern-Knöpfe ohne bo-Kaskade, Vollbild-Knöpfe 46 px.
> **MERKE:** Animals-Fall = MB-Re-Recordings (nicht heilbar ohne Akustik);
> `melden(..., erzwingen)` übergeht den notify-Schalter NUR für den
> Kontextmenü-Weg.

> **STAND: Builds 125–152, 154/154 Tests grün, Addon v1.1.2 live abgenommen.**
> JBs Marschbefehl 05.08. („Testmodus → großer Spec-Block → Hotkey-Editor →
> Kleinkram, alles go ohne Pause") ist KOMPLETT abgearbeitet:
>
> - **Build 147 Testmodus**: `--testmodus [pfad]` legt ALLE Zustandsdateien
>   (DATEN_DIR) in einen Probe-Ordner, Port 8779, Fernsteuerung+Selbst-Neustart
>   aus; bewiesen: Probe-Daten landen nur dort, echte DB unberührt.
> - **Build 148 Etappe A (Cover+Genre)**: MusicBrainz liefert release_id/rg_id/
>   genre (Genres leben an der RELEASE-GROUP, live gemessen — eigener
>   RG-Lookup als Rückfall); Cover Art Archive front-500 mit Retry +
>   RG-Fallback; ffmpeg bettet APIC ein (covertmp+os.replace); /api/cover;
>   Player-Cover echt mit Thumbnail-Rückfall; Genre in ID3 (TCON) + Spalte.
> - **Build 149 Etappe B (VLC-Motor Stufe 1)**: Gerät „VLC" im Spotify-Connect-
>   Muster — Browser bleibt das Gehirn, Ton aus ferngesteuerter libvlc-Instanz
>   (`/api/vlc`, python-vlc in der venv; VLC 3.0.21 auf dem PC). Geräte-Knopf
>   im Player, VLC-Ansicht (Cover + schlanke Fernbedienung, 1-s-Takt),
>   Titelende → playerAdvance genau einmal (vlcEndeFuer). Ohne VLC: toast +
>   Browser-Rückfall. **MERKE (live gemessen):** libvlc VERLIERT
>   audio_set_volume vor dem asynchronen Aufbau des Audio-Ausgangs —
>   Wunsch-Lautstärke (`vol_wunsch`) wird im Takt nachgezogen, bis sie sitzt.
> - **Build 150 Etappe C (Wiedergabe-Grundeinstellungen)**: drei Ebenen
>   global (CFG) → Playlist → Titel („absolut"), leere Ebene erbt; Felder
>   sub/speed sofort wirksam, ton vorbereitet (Mehrspur kommt mit dem
>   Film-Import). Auto-Merken am laufenden Titel (merge lässt fremde Felder
>   stehen). Einstiege: Rechtsklick (auch Mehrfach-Auswahl = „Eigenschaften
>   setzen"), Playlist-Werkzeuge, Optionen. `/api/wiedergabe`.
> - **Build 151 Hotkey-Editor**: Player-Tasten als TABELLE (HK_DEF +
>   localStorage `ytdl_hotkeys`), 18 Aktionen remapbar, Editor in den Optionen
>   (Taste drücken, Esc bricht ab, Kollisions-Wache, Alle-Standard); Legende
>   (?) liest die ECHTE Belegung. Fest: Medientasten, Ziffern, Strg+Pfeile,
>   Listen-Tasten.
> - **Build 152 Kleinkram**: .srt-Stamm-Kopplung (yt-dlp liefert je nach
>   Quelle SubRip; Einsortieren wandelt nach WebVTT, Original in den
>   Papierkorb — der real verwaiste Grim-Dawn-Untertitel ist geheilt);
>   Klick ins Leere räumt die Playlist-Auswahl (Explorer-Muster).
> - **Builds 153/153b Auto-Tagging-Bilanz**: 51/72 getaggt, Nur-Songs-Filter
>   zeigt 83 Titel (Purple Rain & Co. repariert), 23 Genres, alle 6 MP3s mit
>   verfügbarem CAA-Bild tragen es eingebettet (3 Rest = echte 404 beider
>   Ebenen ⇒ Thumbnail-Rückfall). Wurzel-Fixes: Lauf speichert mb_release/
>   mb_rg und zieht fehlende Cover künftig OHNE neue MB-Suche nach; Cover
>   werden NUR für .mp3-Pfade angefragt (26 der 29 Kandidaten waren Videos —
>   weggeworfene CAA-Last, die die Drossel provozierte); getaggt zählt nur
>   echte Einbettungen. **MERKE:** _cover_in_datei ist bewusst MP3-only;
>   „Heroes" bekam ein falsches Album (Studio-Album-Heuristik vs.
>   MB-Sonderzeichen „“Heroes“") — Heuristik-Umbau nur mit JB-Go.
>
> **Selbst-Neustart (144m) trägt:** Backend-Änderungen deployen sich selbst
> (mtime-Signatur, nur im Leerlauf); oberflaeche.py lädt ohnehin heiß.
> **Offen als Nächstes:** Hörbücher/CDs (Etappe 2 der Medienzentrale-Spec:
> Werke-Import), Programm-Hülle (pywebview) + TV-Modus; Installer-Paket
> v1.3.0 wartet weiter auf das SyncManga-v0.4.1-Rezept.

> **Addon v1.1.2 — VON JB LIVE ABGENOMMEN (04.08.): „mix pfeil funktioniert,
> playlist ebenso" + „playlist haken funktioniert."** Kanal liefert v1.1.2
> (Außen-Verifikation, Hash exakt). v1.1.2: Ring-Pfeil wird grün ✓ bei schon
> komplett eingereihter Playlist (`listen_log.json`, `/api/addon_hab_liste` —
> Route VOR `addon_hab`, startswith-Falle!); Klick verweigert nicht, sondern
> öffnet den Dialog mit Hinweis (Nachladen bleibt möglich); Mixe nie Haken.
> Das Log kennt nur Läufe AB v1.1.2 — Altbestand ist nicht rückwirkend grün.
> v1.1.1 (Commits 55c19de + ef1514e): Playlist-⬇ (gestrichelter
> Ring) an Playlist-Karten + Panel-Kopf, Klick fragt **Von–Bis** im eigenen
> Dialog (kein prompt — Firefox-Dialogsperre!); Mix ohne „Bis" = 50 ab „Von".
> App: `/api/add` nimmt von/bis (`playliststart/playlistend`), Mix-Klemme
> 1..500 gilt auch für bis; leerer Bereich hinterlässt einen ehrlichen
> Fehler-Eintrag. Popup zeigt **aktive Version + Update mit 1-Klick**
> (`/api/addon_update`, App holt die Kanal-updates.json — keine neue
> Host-Berechtigung). Hab-Zustand je Video lokal (60 s) → kein ⬇-Flackern.
> **Adversarialer Review (28 Agenten) fand 9 echte Fehler VOR der Signierung**,
> der wichtigste: Mix vom Panel-Kopf wäre STILL gescheitert
> (playlist?list=RD… ist „unviewable" — Mixe brauchen die watch?v=…&list=-Form).
> Sammel-Wächter `test_review_fixes_v111`. **MERKE fürs nächste Mal:**
> `window.prompt/confirm/alert` im Addon IMMER vermeiden (Sperre), Klick-Timer
> am geteilten Knopf IMMER gegen curUrl/curListe bewachen.

> **Addon v1.1.0 (25.07., JB mit Bildern):** (a) Der ⬇-Knopf **sprang** in
> Playlist-Zeilen (Text-Treffer vs. Thumbnail-Treffer = zwei Anker; es gibt
> nur EINEN Knopf, kein Duplikat) — jetzt ankert er immer am **Vorschaubild**.
> (b) Bibliothek-Titel sind **vorher grün mit ✓**; Klick blitzt **rot mit ✗**
> (vorher Gold + nur Farbwechsel). Gebaut (chrome/edge/firefox), 2 Wächter;
> **Signiert + im Kanal (25.07./04.08.):** unlisted-Validierung 0 Fehler, xpi
> signiert, Asset-Tausch im v.1.2.2-Release (neue xpi + updates.json, alte xpi
> bleiben additiv); von AUSSEN verifiziert: `latest/download/updates.json`
> liefert v1.1.0, xpi-Hash stimmt (`e25bf34e…`). Firefox holt es beim nächsten
> Update-Check von selbst. **MERKE:** `amo_sign.py` ohne Flag geht an „listed"
> (strengere Prüfung, schlug fehl, nichts angelegt) — JBs Kanal ist
> `--kanal unlisted`. **Nebenbei 144q:** `_mb_pro_min`
> zählt Ausschnitte nicht mehr (JBs Mini-Clips kippten den Audio-Median auf
> 2,1 MB/min) und `test_mb_pro_min` ist von der echten DB isoliert (wurde rot
> ohne Code-Fehler — Tests lesen nie echte Daten ergebnisrelevant).
> **OFFEN (JB-Frage im Chat): Playlist-Download-Pfeil** — ganze Playlist still
> laden; beim **Mix/Radio** Anzahl nötig: fragt das **Addon selbst** (kleiner
> Dialog) oder öffnet es die **App** (vorhandene Anzahl-Frage)? Danach bauen +
> signieren + Asset-Tausch.
> **Firefox-Einfrieren bei Shorts (JB):** Symptom „Fenster bewegen beendet es"
> = Compositor/Hardwarebeschleunigung, sehr wahrscheinlich NICHT das Addon
> (ein gedrosselter mousemove-Listener, ein Knopf, kein Observer). JB-Test:
> Addon kurz deaktivieren → friert es weiter, Hardwarebeschleunigung in den
> Firefox-Einstellungen abschalten (Leistung → Haken raus → HW-Beschleunigung
> aus, Neustart).

> **Eigenständiger Player passt ohne Scrollen (Build 144p, JB Bild 1 vs. 2):**
> Im neuen Tab nahm das 16:9-Video (`flex:0 0 auto` + `max-height:100cqb`) bei
> breitem Panel die volle Kartenhöhe und drückte die Playlist raus (Scroll).
> Jetzt `flex:0 1 auto` — das Video schrumpft (Pillarbox, Bild bleibt 16:9 via
> object-fit), Playlist bleibt sichtbar, kein Scroll. Scoped
> `body:not(.mini):not(.embed)`, Embed/Mini unberührt. Live gemessen bei
> 1858×700 / 1200×760 / 560×820.
> **Logo im neuen Tab** + **Icon-Flackern alle 5 s** waren von der PARALLELEN
> Session gefixt (Logo: Embed nur im iframe; libPoll zeichnet nur bei Änderung)
> — mein 144o-Commit hatte diese fremde Arbeit versehentlich mit eingesammelt
> (geteilter-Index-Falle). Beide live geprüft, funktionieren.

> **Favorit-Modell überarbeitet (Build 144o, JB 25.07.):** Der Favorit ist der
> EINE Repräsentant einer Gruppe — wählbar zwischen **Hauptsong und jedem
> Ausschnitt** (vorher nur Clips). Nur der Favorit ist die Kachel, wird
> abgespielt und zählt im Zufall/Radio; die Alternativen liegen im Rechtsklick.
> Standard = Hauptsong; neuer Clip wird automatisch Favorit. Ist ein Clip der
> Favorit, wird der **Clip die Kachel** (mit ✂ oben rechts im Thumbnail), der
> Hauptsong rückt in den Rechtsklick und ist dort **nicht löschbar** (🔒).
> Backend-Felder: `gruppe`, `ist_favorit`, `hat_geschwister`. **An JBs echter
> Bibliothek gemessen.** Dazu 144n: Ausschnitt-Löschen nutzt jetzt einen
> app-eigenen Dialog (`frageModal`), den der Firefox-„Dialoge unterbinden"-Haken
> nicht abschalten kann.
> **Der Selbst-Neustart (144m) hat sich live bewährt:** die 144o-Backend-
> Änderung übernahm JBs Server von allein, ohne manuellen Neustart.

> **Der „Neustart-Haken" ist gelöst (Build 144m):** Backend-Änderungen brauchten
> bisher einen manuellen Neustart (die Oberfläche lädt pro Anfrage neu, das
> Hauptmodul nicht). Jetzt merkt sich die App die mtime-Signatur ihrer
> Backend-`.py` und **ersetzt ihren eigenen Prozess** (`os.execv`), sobald der
> Code auf der Platte neuer ist — eingehängt in die bestehende 5-s-Schleife
> (`ticker_schleife`, kein neuer Timer), nur bei Ruhe (kein Download/Stream),
> mit Beruhigungszeit. Zustand überlebt (liegt auf der Platte). Off-Schalter
> `CFG.auto_neustart` (Standard an). **Aktiviert sich erst nach EINEM manuellen
> Neustart** (der laufende Server hat das Feature noch nicht) — danach nie
> wieder manuell. `os.execv` real geprüft (Windows), 6 Unit-Tests.

> **JB-Funde 25.07. (Build 144i/144j) — erledigt:**
> - **YouTube-Rechtsklick** sprang nicht zur Stelle → ruft jetzt `playerYoutube`
>   (`&t=…s`); der Werkzeug-Knopf konnte es längst.
> - **Clip meldete „fehlgeschlagen", obwohl erstellt** → `schnittSpeichern` prüfte
>   eine nie deklarierte Variable `info`; der Erfolgspfad warf, der catch log als
>   Fehler. Jetzt `plInfo()`. Kein Dashboard-Problem, das trat überall auf.
> - **Datei behielt den `[Video-Id]`-Titel** → zwei Lücken: das Download-Template
>   schreibt `[%(id)s]`, und KEIN Download-Pfad hat je umbenannt (nur der
>   Ordner-Import). Neu: `auto_umbenennen_nach_download` läuft im Fertig-Hook
>   (nicht-destruktiv, reversibel, gated auf `auto_umbenennen` = bei JB an); der
>   Clip säubert seinen Namen selbst. **WIRKT ERST NACH APP-NEUSTART**
>   (youtube_app.py lädt nicht heiß nach).
> - **Abspielart neu (Build 144l, JB mit Bildern):** das 🎶-Symbol hieß „nur
>   Musik", filterte aber nach FORMAT (nur Ton/MP3) — „Every Breath You Take"
>   und „Purple Rain" (Videos) fielen raus, Comedy-MP3s blieben. Jetzt EIN
>   Menü am ▶-Symbol mit vier Klartext-Optionen: **Alles · Nur Ton · Nur Video
>   · Nur Songs**. „Nur Songs" ist die Inhalts-Achse (`musik!=='nein'`), nimmt
>   Video-Songs mit, wirft Comedy/Trailer/Gaming raus — wirkt überall
>   (`artPasst`: Raster, Radio, Autoplay). Die vergrabene „nur Lieder"-Checkbox
>   ist weg (gefoldet). **„Nur Songs" braucht die Einstufung aus 144h → erst
>   nach App-Neustart; bis dahin zeigt es sicher alles.**
> - **Ausschnitte gehören jetzt zum Song (Build 144k, JB mit Bild):** sechs
>   Test-Clips müllten das Raster zu. Jetzt: Clips tragen `|clip` im Schlüssel
>   und gehören ihrem Song; **versteckt im Raster** (93→87 Kacheln bei JB),
>   **Rechtsklick auf den Song → „✂ Ausschnitte (N)"** (Favorit ⭐ wählen,
>   abspielen, Papierkorb). **Nur der Favorit zählt im Zufall/Radio**
>   (`radioKandidaten`: `!x.clip||x.clip_favorit`); die übrigen Clips raus,
>   der volle Song bleibt. Favorit = eigene Wahl, sonst der neuste; ein neuer
>   Clip wird automatisch Favorit. Backend `/api/clip_favorit`. An JBs echter
>   Bibliothek gemessen (read-only). **Sichtbar erst nach App-Neustart.**
> - **Embed-Player füllte die Dashboard-Kachel nicht** (Bild 3): bei ausgelagerter
>   Playlist (`plq-extern`) blieben 102 px leer → Medienfläche füllt jetzt, 16:9
>   bleibt (object-fit). **OFFEN/PRÜFEN:** Bild 3 könnte auch der **standalone
>   Mini-Modus** (🔳-Knopf) sein — den habe ich NICHT angefasst (dort ist die
>   Leiste bewusst kompakt, max-height 96 px). JB fragen, welche Ansicht gemeint
>   war, falls es im Mini weiter klein aussieht.

## Sofort weitermachen bei — JBs eigene Reihenfolge

1. ~~**Player-Playlist: Rahmen-Auswahl geht nicht.**~~ **ERLEDIGT (Build 144),
   Ursache gefunden und live belegt.** Der Code aus Build 139 war in Ordnung —
   er kam nur nie zum Zug: `plqBandStart` stieg auf jeder `.pl-item` aus
   („auf einer Zeile hat Ziehen Vorrang"), und diese Bedingung stammte aus dem
   Muster der BIBLIOTHEK, wo zwischen den Kacheln viel freie Fläche liegt.
   **Eine Liste hat diese Fläche nie:** am echten Fenster gemessen ist
   `.pl-queue` bei 14 Titeln randvoll (362 px Inhalt in 150 px Sicht) und
   schrumpft bei 3 Titeln auf exakt ihre Zeilenhöhe (76 px) — **freie Höhe
   0 px in beiden Fällen**, weil die Liste mit ihrem Inhalt wächst
   (`flex:0 1 auto` + `max-height`). Jeder Punkt lag auf einer Zeile, das Band
   konnte nie starten. Denselben Fund gab es im Abo-Fenster schon einmal
   (Build 94: „die Zeilen sind vollbreit, freie Fläche gibt es kaum").
   Jetzt Explorer-Muster: eine **markierte** Zeile greift man zum Verschieben,
   auf jeder anderen zieht man einen Rahmen auf; der native HTML5-Drag wird
   dabei abgewürgt (`plqDragStart` → `preventDefault`), sonst frisst er die
   Bewegung. **Zweiter Fund beim Messen:** `plqMark()` malte nur den
   Fokus-Eintrag `plqSel` an und wischte jede gezogene Auswahl beim Loslassen
   wieder weg (traf auch den Strg-Klick) — `sel` hatte zwei Wahrheiten, jetzt
   eine. Wächter: `test_rahmen_in_der_playlist_startet_auch_auf_einer_zeile`,
   `test_playlist_umsortieren_bleibt_neben_dem_rahmen`,
   `test_playlist_markierung_zeigt_die_ganze_auswahl`.
   **JB-Abnahme mit echter Maus (23.07.): „ansonsten funktioniert das fenster
   ziehen jetzt."** Dazu eine Nachforderung, erledigt in **Build 144c**:
   *„wie in bibliothek soll der fenster ziehen modus in player/playlist schon
   ein/zwei reihen darüber funktionieren können."* Der Zuhörer hängt jetzt
   auch am BEHÄLTER über der Liste (`.pl-side` im Player, die Karte im
   herausgelösten Fenster) — dieselbe Nachforderung gab es für die Bibliothek
   schon einmal (Build 143, JB damals: „das ist frustrierend"). Getroffen und
   gescrollt wird weiter die LISTE, sonst schöbe das Rand-Nachschieben am
   falschen Element; `plqZugLaeuft` verhindert, dass aus den zwei mithörenden
   Ebenen zwei Bänder werden. **Nebenbefund:** in der Bibliothek hängt der
   Zuhörer an `libinhalt` UND an der Karte, dort entstehen tatsächlich zwei
   Bänder übereinander — unschädlich (gleiches Ergebnis, doppelte Arbeit),
   aber eine Aufräum-Gelegenheit (**in Build 144e mit geheilt**). Wächter:
   `test_rahmen_darf_oberhalb_der_playlist_beginnen`.
   **Die allgemeine Regel dahinter (Build 144e, JB mit Bild):** „genauso wie
   oben, sollte man auch von UNTEN ein fenster ziehen können … solange es in
   dem fenster ist, ist ein feld ziehen gewährleistet." Gemessen war das
   Gegenteil, bei Playlist UND Bibliothek aus derselben Wurzel: **die Karte
   ist nur so hoch wie ihr INHALT, nicht wie das Panel** — im Playlist-Fenster
   231 px Schwarz darunter ohne jeden Zuhörer, in der auf einen Treffer
   gefilterten Bibliothek 105 px. Bei voller Bibliothek fällt es nicht auf,
   weil der Inhalt länger ist als das Panel; deshalb kam es erst mit JBs Bild
   ans Licht. **Das Fenster ist der `panel-body`** — der hört jetzt bei beiden
   mit. Abgesichert: kein Band auf der Videofläche, keins ohne sichtbare
   eigene Liste (Reiter-Panels), nur EIN Band trotz mehrerer mithörender
   Ebenen. Wächter: `test_rahmen_gilt_im_ganzen_fenster`.
   **Aufräum-Gelegenheit (belegt, nicht erledigt):** in `test_youtube.py`
   stehen noch **21 feste Zeichenfenster** der Form `quelle[i:i+1800]`. Sie
   werden still grün, wenn eine Funktion wächst — an einem Tag dreimal
   zugeschlagen. Ersatz steht bereit: `_funktionsende(quelle, start)`.
1b. **OFFEN und der nächste Griff: die Playlist IM Player füllt ihr Panel
   nicht** (JB mit Bild, 23.07.: „jetzt ist playlist nur noch ein kleines
   fenster, das sollte dynamisch bis zum unteren rand von playlist gehen").
   Für das herausgelöste Playlist-**Fenster** ist es in Build 144f erledigt
   (Liste füllt die Karte, totes Schwarz von 183–523 px auf 14 px).
   Im **Player** ist es NICHT gelöst — vier CSS-Wege sind gescheitert, jeder
   live gemessen: nur die Spalte wachsen lassen ⇒ Liste 57 px und Überlauf bei
   420 px · Deckel `max-height:62%` ⇒ Verhältnis kippt auf 2,2–3,7 ·
   `width:auto` ⇒ Video kollabiert auf 128×72 px · Video schrumpfen lassen
   (`flex:0 1 auto`) ⇒ Liste läuft aus der Karte.
   **Ursache:** Im vertikalen Layout konkurrieren ein 16:9-Video mit fester
   Höhe und die Liste um dieselbe Höhe; `aspect-ratio` verträgt sich schlecht
   mit `flex-shrink`. Im HORIZONTALEN Layout ist es längst richtig (Liste
   354 px, füllt die Spalte, kein Scrollen) — genau das zeigt: es braucht
   einen **echten Mechanismus** statt einer weiteren CSS-Heuristik.
   **ERLEDIGT DURCH ZUFRIEDENHEIT (JB 05.08.): „die position vom player
   gefällt mir, hat schon länger keine probleme mehr damit."** Der
   Trenner-Vorschlag ist damit vom Tisch; kein Bau nötig. Sollte das Thema
   je wiederkommen, liegen die vier gemessenen CSS-Sackgassen oben als
   Warnung — dann Trenner, keine fünfte CSS-Heuristik.
2. ~~**Playlist speichern/aktualisieren**, wenn man Titel in eine gerade
   laufende Playlist zieht (JB: „ganz dezent irgendwo").~~ **ERLEDIGT
   (Build 144).** Es fehlte die Verbindung: `plPlaySel` gab an `playerPlay`
   nur den **Namen** der Playlist mit, nie ihre **Id** — der Player konnte
   also gar nicht wissen, wohin er zurückspeichern soll. Jetzt merkt sich
   `playerState.plid` die Herkunft, und ein 💾-Knopf erscheint **nur**, wenn
   die Warteschlange von der gespeicherten Playlist abweicht (Calm-Design);
   er hängt an beiden Sichten (eingebauter Player + herausgelöstes Fenster).
   Drei Entscheidungen, die man kennen muss:
   · **„Geändert?" wird VERGLICHEN, nicht gemerkt** (`plqGeaendert` prüft
     gegen `plState`) — ein Merker müsste an jeder künftigen Änderungsstelle
     gesetzt werden und wird dort vergessen.
   · **Mischen zählt nicht als Änderung** (Vergleich als sortierte Multimenge)
     — sonst stünde nach jedem Zufalls-Start sofort „geändert" da.
   · **Sichern ist nicht-destruktiv:** die Reihenfolge der Playlist bleibt,
     Entferntes fällt raus, Neues hängt hinten an. Wer bei gemischter
     Wiedergabe etwas hineinzieht, zerschießt so nie seine Ordnung.
   Wächter: `test_playlist_folgt_dem_hineingezogenen_titel`,
   `test_playlist_sichern_zerstoert_die_reihenfolge_nicht`.
3. ~~**Spotify-artiges „+" im Player oben** für eine Lieblingssongs-Playlist.~~
   **ERLEDIGT (Build 144d).** Der ＋-Knopf sitzt direkt unter dem Titel in der
   Player-Steuerung — wie bei Spotify, wo das Zeichen beim laufenden Stück
   steht und nicht in einem Menü. Er zeigt den Zustand (＋ noch nicht drin,
   ✓ drin, farbig hinterlegt) und nimmt beim zweiten Klick wieder heraus.
   **Bewusst keine neue Datenstruktur:** „♥ Lieblingssongs" ist eine ganz
   normale Playlist und damit sofort abspielbar, als .m3u exportierbar, aufs
   Handy synchronisierbar und im Playlist-Menü sichtbar. Eine eigene
   Favoriten-Liste daneben wäre ein zweiter Mechanismus für dieselbe Sache.
   Sie entsteht beim ERSTEN Klick von selbst — sonst wäre der Knopf beim
   ersten Mal eine Sackgasse. Wächter: `test_lieblingssongs_knopf_im_player`.
4. ~~**Videonummer je Kanal als eigenes Feld.**~~ **ERLEDIGT (Build 144g).**
   `_kanal_nummern()` zählt wie `abo_nr` (ältestes = 1, nach Upload-Datum),
   nur für JEDEN Kanal statt nur für abonnierte; eine echte `abo_nr` hat
   Vorrang, weil sie über den ganzen Kanal zählt. **Abgeleitet statt
   gespeichert** — eine geschriebene Nummer würde falsch, sobald ein älteres
   Video desselben Kanals dazukommt.
   **Der Messwert hat die Anzeige geändert:** an JBs Bibliothek bekommen 84
   von 86 Titeln eine Nummer, aber **69 davon wären „#1"** gewesen, weil er
   von den meisten Kanälen genau ein Video hat — das hätte ausgesehen wie
   genau die „500× die 1". Deshalb erscheint eine abgeleitete Nummer nur,
   wenn es beim selben Kanal etwas zu ordnen gibt („#2 von 5"); jetzt zeigen
   23 von 86 eine Nummer, der Rest bleibt leer.
   Wächter: `test_kanal_nummer_ist_keine_tracknummer`,
   `test_kanal_nummer_weicht_der_echten_abo_nummer`.
   **MERKE:** `youtube_app.py` lädt nicht heiß nach — die Spalte füllt sich
   erst nach einem App-Neustart mit Daten.
5. **Video-/Song-Einteilung soll nach INHALT gehen, nicht nach Dateiformat**
   (JB-Bild: die drei Kategorie-Symbole). Heute entscheidet allein
   `_kategorie()` beim Download: `audio` → „MP3", ab 2160p → „4K+", sonst
   „Video". Ein Musikvideo ist damit ein „Video", obwohl es ein LIED ist —
   JB: „der Video- und Song-Modus soll wirklich Lieder nehmen, nicht nur
   Videos und MP3."
   Der Baustein dafür ist schon da: `_ist_musik()` erkennt seit Build 140
   auch Musikvideos (VEVO-/„- Topic"-Kanäle, Muster „Künstler - Titel") und
   trifft in JBs Bibliothek 51 zusätzliche Titel. Dieses Wissen muss jetzt in
   die **Filter und die Sortierung** der Oberfläche, nicht nur ins
   Auto-Tagging.
   **BAUFORM ENTSCHIEDEN (JB 23.07., seine eigene Frage — sie ist besser als
   mein erster Vorschlag und ersetzt ihn):** *„wenn ich von Video zu MP3
   wechsle, auch die Option zu only Lieder … also ein extra Knopf."*
   Also **zwei getrennte Achsen statt einer vermischten Liste**:
   - Achse FORM (bleibt, wie sie ist): Alles · MP3 · Video · 4K+
   - Achse INHALT (neu, EIN Umschalter): „♪ nur Lieder" an/aus
   Daraus ergeben sich JBs Kombinationen von selbst — „Video + nur Lieder" =
   Musikvideos, „MP3 + nur Lieder" = Musik-Ton, ohne Umschalter = alles.
   Mein alter Vorschlag („Alles/Musik/Nur Ton/Videos" als vier Reiter) hat die
   beiden Achsen vermischt und hätte mehr Knöpfe gekostet — JBs Fassung ist
   EIN Knopf und passt zur Knopf-Diät (Builds 116–118).
   **VORHER MESSEN — die Erkennung trägt den Filter, und sie hat zwei Löcher**
   (gemessen 23.07. an JBs 86 Titeln):
   - Verteilung heute: MP3 17 von 17 „Lieder", Video 50 von 64, 4K+ 2 von 5 —
     insgesamt 69 Lieder, 17 Nicht-Lieder.
   - **Loch 1: Bei MP3 gibt es gar keine Unterscheidung.** `_ist_musik()`
     liefert für JEDE Audiodatei `True` (youtube_app.py:1143). „17 von 17" ist
     deshalb keine Messung, sondern eine Setzung — Comedy, Podcasts und
     Hörbücher rutschen als „Lied" durch (in der Bibliothek z. B. „Louis C.K -
     If Murder Was Legal.mp3"). Der Filter „MP3 + nur Lieder" ändert heute
     also NICHTS.
   - **Loch 2: Bei Videos hängt die Erkennung am Dateinamen** („Künstler -
     Titel") — und der wurde gerade migriert. „SHANIA TWAIN You're Still The
     One Live 1999 HD.mp4" gilt jetzt als KEIN Lied, weil beim Umbenennen aus
     drei Leerzeichen kein „ - " wurde. Solche Titel verschwänden aus
     „nur Lieder", obwohl sie hineingehören.
   **ERLEDIGT (Build 144h)** — in genau dieser Reihenfolge: erst die Erkennung
   gehärtet, dann der Schalter. `_musik_grad()` hat jetzt drei Stufen (belegt /
   wahrscheinlich / nein), `_musik_grade()` liest zusätzlich den **Kanal** mit.
   Zwei Messungen an der echten Bibliothek haben den Bau unterwegs korrigiert,
   beide Richtung „lieber ein Titel zu viel": die strenge Fassung verlor drei
   echte Lieder (Elmer Bernstein, Mateus Asato, Shania Twain), danach fielen
   noch acht heraus, deren Dateiname nur den Titel trägt („The Boxer",
   „Rocky Mountain High") — die rettet der Kanal-Beleg.
   **Stand: 14 belegt · 58 wahrscheinlich · 14 nein, der Filter zeigt 72.**
   Korrekt draußen: Trailer, Gaming-Clips, der Blender-Kurzfilm, NVIDIA-Technik.
   **Noch falsch draußen (4):** Chicago Band, Shania Twain (Fremd-Upload),
   Wulfin86, Rock & Roll Hall of Fame — ihr Kanal hat kein zweites Lied. Das
   löst erst ein MusicBrainz-Treffer, also **das Auto-Tagging einmal über die
   ganze Bibliothek laufen lassen** (⚙ Ansicht → Metadaten). Danach sind sie
   „belegt" und der Filter stimmt.
   Wächter: `test_musik_grad_trennt_beleg_von_vermutung`,
   `test_nur_lieder_ist_eine_zweite_achse`.
   Die drei Ablage-Kategorien bleiben unberührt — es geht um die ANSICHT.
6. ~~**Untertitel: Sprachwahl**, wenn automatisches Laden eingeschaltet ist.~~
   **ERLEDIGT (Build 146).** `_untertitel_sprachen()` als die eine Wahrheit
   (beide Lade-Stellen; „orig" = `.*-orig`, die unübersetzte Auto-Spur —
   braucht das Karaoke). Einstellungen: Haken de/en/Original + Freitext für
   weitere Kennungen. Ohne Wahl exakt das Bestandsverhalten. Live am Server
   gemessen (Config danach zurückgesetzt), 144/144.
7. ~~**Einstellung zum Umschalten der Rahmen-Auswahl.**~~ **ERLEDIGT
   (Build 144)** — ⚙ Ansicht → „Playlist-Rahmen": „ab der Zeile" (Standard,
   neues Verhalten) oder „nur auf freier Fläche" (Stand vor Build 144).
   Der Umschalter ist zugleich der Rückweg, falls JB das Greifen unmarkierter
   Zeilen zum Verschieben doch vermisst.
8. ~~**Bereich neben der Playlist als Ablage.**~~ **GESTRICHEN (JB 05.08.).**
   Der Anlass (leerer Platz im Playlist-Fenster) existiert seit Build 144f
   nicht mehr, und den Nutzen (Titel parken) deckt die Warteschlange samt
   Playlist-Rückspeichern ab — eine Ablage wäre ein zweiter Mechanismus für
   dieselbe Sache. Falls JB je „merken, aber nicht einsortieren" vermisst:
   schlanke „📌 Später"-Playlist über den Rechtsklick, kein neues UI-Konzept.
9. Aus dem alten Plan: **Testmodus außerhalb JBs Ordner**, **Punkt 5 der Spec**
   (VLC-Motor, Album-Cover eingebettet, Hörbücher/CDs,
   Wiedergabe-Grundeinstellungen, Programm-Hülle mit TV-Modus), **Hotkey-Editor**.

**Metadaten — was noch fehlt** (JB fragte danach, Empfehlung abgestimmt):
Genre (kommt aus MusicBrainz mit, wird für die TV-Bibliothek gebraucht),
Cover eingebettet statt YouTube-Thumbnail, Kanal/Uploader als eigenes Feld für
Nicht-Musik, Aufnahmedatum, Kapitelmarken für Hörbücher. Leitsatz: **nur
schreiben, was belegt ist** — falsche Tags wandern beim Kopieren mit und sind
schwerer zu korrigieren als fehlende.

## FALLEN, die diese Runde Zeit gekostet haben — bitte lesen

- **Containment sperrt schwebende Flächen ein.** `container-type` (an
  `.libbar`, `.cmd-now`, `.panel-body`, `.pl-media`) macht das Element zum
  eigenen Stapel-Kontext: ein z-index darin gilt nur intern. Gemessen lag ein
  Menü mit **6100 unter einem Panel mit 14**; sogar `position:fixed` wäre
  eingesperrt. **Schwebende Flächen gehören an den `<body>`.** Wächter:
  `test_schwebende_flaechen_nicht_im_kaefig`.
- **CSS-Kommentare schachteln nicht.** Mir sind ZWEIMAL drei `*/` in einem
  Block passiert; danach lief Prosa als CSS und der Parser verwarf die
  folgende Regel **stillschweigend**. Im Quelltext sieht das harmlos aus, nur
  eine Live-Messung findet es. Wächter:
  `test_css_kommentare_sind_sauber_geschlossen`.
- **Auch PANELS tragen `data-id`** — Selektoren für Kacheln/Zeilen entsprechend
  schärfen (`.kachel[data-id]`), sonst greift man das falsche Element.
- **Feste Höhe schlägt `aspect-ratio`.** Sind Breite UND Höhe vorgegeben, wird
  das Verhältnis ignoriert. Und in einer ZEILEN-Karte streckt `align-items`
  den Rahmen, solange `align-self` fehlt.
- **Die Prüfumgebung kann zwei Dinge nicht:** Screenshots (der Browser-Pane
  zeichnet keine Bilder, solange er nicht angezeigt wird — und ohne
  vorherigen Screenshot verweigert auch `left_click_drag` den Dienst) und
  echtes Vollbild (`requestFullscreen` ohne Nutzergeste verboten). Für
  Optik-Fragen eine HTML-Vorschau bauen und JB schicken.
- **KORREKTUR zur Übergabe von Build 143** („die Player-Playlist hat in der
  Prüfumgebung keine Ausdehnung"): Das stimmte so nicht, und die Fehldeutung
  hat Punkt 1 eine ganze Runde gekostet. **Zwei getrennte Gründe:**
  1. Der Browser-Pane startet mit `innerWidth/innerHeight = 0` — nicht die
     Playlist war 0 breit, die GANZE Seite war es. Heilung: einmal
     `resize_window` mit ausdrücklichen Werten (`width:1280, height:860`);
     der Voreinstellungs-Wert „desktop" übernimmt die native Größe und damit
     wieder die Null.
  2. Danach bleibt `.pl-queue` trotzdem unsichtbar, weil eine
     **Container-Query** sie ausblendet: `@container plcard (max-height:330px)`
     versteckt Playlist/Kapitel/Lyrics, und das Player-Panel ist im
     Standard-Layout nur 249 px hoch. Erst ein größeres Panel (per
     `pane.style.height`) bringt die Liste in Sicht.
  **Merke:** Ein Element mit Breite 0 in dieser Umgebung ist zuerst ein
  Verdacht gegen die Umgebung, nicht gegen den Code — Viewport messen, bevor
  man „nicht prüfbar" in die Übergabe schreibt.
- **Maus-Gesten ohne Screenshot messen:** echte `PointerEvent`s über
  `dispatchEvent` durch dieselbe Handler-Kette schicken (pointerdown aufs
  Element unter dem Punkt, pointermove/pointerup an `document`). Das beweist
  die JS-Logik; für den nativen HTML5-Drag zusätzlich ein `DragEvent`
  ('dragstart') feuern und `defaultPrevented` messen.
- **Tests fassen NIE echte Daten an.** Bewährt: `playerPlay`, `plApi`,
  `_json_speichern` abfangen; danach `playlists.json` bzw. `geladen_log.json`
  gegenprüfen. Vor dem Titel-Abgleich wurde die DB nach `%TEMP%` gesichert.

## Was die Runde 125–143 gebracht hat (Kurzfassung)

**Kopfleiste fertig (125):** Wurzel war der Containment-Käfig oben; dazu eine
dokumentierte Ausweich-Ordnung — Zähler weicht zuerst, Warnung und
Status-Punkt bleiben, Player behält ein Mindestmaß, Symbol-Spalte bleibt
senkrecht. **125b:** Abbruch greift auch während „Zusammenfügen"
(`postprocessor_hooks` fehlten). **126/127:** ein Feld für alles
(`link_deuten`), Mengen-Regler mit älteste/neueste, Abos entdoppelt.
**128:** `menuSchliesser` benutzte sein Argument nie — Außenklick schließt
jetzt jedes Menü. **129:** toter Selektor `.counter` (Element heißt
`cmd-count`) — Zähler-Tooltip schwebt wieder. **130–133:** Vollbild-Overlay,
16:9 am Rahmen, Spul-Einblender, Browser-Zeichen im Status-Punkt.
**134–136:** Klick-Art einstellbar, Geräte-Symbol, Ziehen auf Playlists,
Rahmen-Auswahl, Bild oben, Auto-Tagging direkt nach dem Download.
**137–141:** Werkzeuge im eingebauten Player, Warteschlange heilt hängende
„prueft"-Aufträge, doppelte Titel erlaubt, Musikvideos gelten als Musik
(51 in JBs Bibliothek), Titel folgen den Dateinamen (52 von 86 angeglichen).
**142/143:** Auswahl-Verhalten wie im Explorer — Anfasser nennt die Anzahl,
Klick ins Leere räumt ab, Bulk-Leiste von 9 Knöpfen auf **null**, dafür ein
＋ neben der Playlist-Liste.

---

> JB kopiert diesen Text als erste Nachricht in einen neuen Chat.

---

Mach bei SyncYouTube weiter (eigenes Repo `schn4ppi/SyncYouTube`, Branch `main`,
Port 8776 = meine laufende Instanz — nie killen, Neustart über `/api/beenden` +
`pythonw System\youtube_app.py --no-browser`, cwd = `SyncYouTube`).

**Lies zuerst:** diese Datei ganz, dann `SyncYouTube/System/NAECHSTE_SESSION.md`,
`Doku/SYNCYOUTUBE_MEDIENZENTRALE_SPEC.md` (großes Zielbild) und die letzten
Abschnitte in `SyncDashTray/System/docs/ABNAHME.md`.

## Was Build 125 gelöst hat (23.07., alles live gemessen)

Die Kopfleiste ist fertig. Alle drei Fehler hatten belegbare Wurzeln:

- **Ansicht-Menü hinter den Panels.** Die Vermutung aus der letzten Übergabe
  war richtig, nur der Verdächtige war ein anderer: nicht transform/filter,
  sondern **`container-type:inline-size` an `.libbar`** (seit Build 122 für
  die schmalen Leisten). Containment macht das Element zum eigenen
  Stapel-Kontext — ein z-index darin zählt nur gegen Geschwister im selben
  Kasten, und der Kasten steckte im Bibliotheks-Panel mit **z-index 14**.
  Deshalb half die 6100 aus Build 124 nicht; sogar `position:fixed` wäre
  darin eingesperrt gewesen. Gemessen: Menü offen (272×321 px), Klick in
  seine Mitte traf `DIV.kopfzeile`, ein fremdes Panel.
  **Lösung:** beide `.colmenu` wohnen jetzt direkt unter `<body>` und werden
  per `popoverBei()` am Knopf ausgerichtet — wie `.panelmenu`/`.itemmenu`
  längst. Der Audit über alle schwebenden Flächen ergab: **alle anderen
  hängen bereits am body**, es gab keine weiteren Ausreißer.
- **Symbol-Spalte kippte.** `@media(max-width:660px)` drehte `.cmd-side` auf
  `flex-direction:row`. Bei 476 px lagen die 4 Knöpfe nebeneinander und
  waren 121 statt 28 px breit — genau der Platz, der dem Player fehlte.
  Regel entfernt; senkrecht ist ihre schmalste Form.
- **„Statistik überlappt den Player".** Umgekehrte Blickrichtung: Statistik
  und Symbole sind `flex:none`, der Player hatte `min-width:0` — also gab
  nur er nach. Bei 360 px war er auf **69 px** gequetscht und sein Inhalt
  lief **135 px** heraus, mitten unter die Statistik.

**Die gemeinsame Wurzel war die fehlende Ausweich-Ordnung** — sie steht
jetzt dokumentiert im CSS: Zähler weicht zuerst (rein informativ), Warnung
und API-Punkt bleiben (ein Statuszeichen darf nie still verschwinden),
Player bleibt ganz (`min-width:220px`), Symbol-Spalte bleibt senkrecht.
Der Zähler steht dafür **immer** im ⚙-Menü als Zeile „Geladen" — nicht nur
wenn er oben fehlt, damit „ausgeblendet ≠ unerreichbar" nicht selbst an
einer Breiten-Regel hängt. Dazu: „⚙ Ansicht" rechtsbündig via
`margin-left:auto` (ein Abstandhalter wirkt nur in SEINER Zeile — die
Leiste darf umbrechen, gemessen 118 px Lücke).

**Messwerte nach dem Fix** bei 1280/975/700/476/360: Menü an drei Punkten
klickbar, im Fenster; Player 486/327/220/292/279 px, kein Überlauf;
Symbol-Spalte überall senkrecht; kein Querscrollen; Konsole fehlerfrei.

**Abbruch-Fehler (war Punkt 6):** Die Übergabe nannte `cancel/stop/remove` —
die gibt es in `/api/action` gar nicht, sie heißen `pause`/`weiter`/
`entfernen`, und die Oberfläche sendet genau die. Der Abbruch-Weg war
intakt. Die echte Lücke: die yt-dlp-Optionen trugen nur `progress_hooks`,
also griff während der **Nachbearbeitung** (ffmpeg-Merge, MP3, Cover —
Anzeige „Zusammenfügen") kein Abbruch. Jetzt zusätzlich
`postprocessor_hooks` mit derselben Prüfung.

**Neue Wächter-Tests** (64/64 grün): `test_schwebende_flaechen_nicht_im_kaefig`
liest die Käfig-Klassen aus dem CSS und den Baum aus dem HTML — gilt damit
automatisch für jede künftige Fläche und jeden künftigen Käfig;
`test_kopfleiste_symbolspalte_bleibt_senkrecht`,
`test_kopfleiste_player_hat_mindestmass`,
`test_abbruch_greift_auch_beim_zusammenfuegen`.

**Merkposten für künftige Arbeit:** `.cmd-now`, `.panel-body` und `.pl-media`
tragen ebenfalls `container-type`. Wer dort eine schwebende Fläche einbaut
(z. B. die ⋯-Werkzeuge im eingebauten Player aus Punkt 4!), muss sie an den
`<body>` hängen — sonst schlägt der Wächter-Test zu. Das ist Absicht.

---

## 1. Kopfleiste — ERLEDIGT (Build 125), siehe oben

Die Kopfleiste hat in mehreren Runden Fehler gezeigt, immer dieselbe Wurzel:
**es fehlt eine Regel, was bei Platzmangel wohin ausweicht.**

- **Symbol-Spalte kippt** (JB-Bild): Abo/Tag-Nacht/Hilfe/Einstellungen sind als
  SENKRECHTE Leiste gedacht, werden bei schmalem Fenster aber von der
  Statistik-Spalte gequetscht und liegen dann nebeneinander. Feste Anordnung
  geben, die auch schmal hält.
- **Statistik-Spalte überlappt den Player**, wenn das Fenster sehr klein wird.
- **Ansicht-Menü liegt hinter den Panels** — Ebene wurde auf 6100 gehoben
  (Build 124), der Treffer-Test besteht TROTZDEM nicht. Verdacht: ein
  Eltern-Element öffnet einen eigenen Stapel-Kontext, gegen den ein höherer
  z-index nicht hilft (transform/filter/will-change/opacity am Panel prüfen).
  Danach ALLE schwebenden Flächen einmal durchgehen (JB: „schau ob es noch
  andere solcher Ausreißer gibt") — Menüs, Flyouts, Popups: Ebene + Position.
- **„⚙ Ansicht" darf rechtsbündig sitzen** (JB-Wunsch).
- Prüfen bei MEHREREN Breiten: 1280 / 975 / 700 / 476 — bei 1280 ist meist
  alles heil, die Fehler zeigen sich erst darunter.

## Was Build 126 gelöst hat — „ein Feld für alles"

Enter im Feld genügt jetzt. Die Deutung liegt als **`link_deuten()`** im
Backend (`youtube_app.py`) — eine Wahrheit, rein aus der URL, **ohne Netz**.
Die Regeln gab es längst verstreut (`ist_einzelvideo`, `_kanal_url`,
`_ist_mix`); die Oberfläche hat sie vorher mit `toLowerCase`-Suchen nachgebaut.

Gefragt wird nur bei den zwei echten Mehrdeutigkeiten: **Kanal-Link**
(laden oder abonnieren?) und **`watch?v=…&list=…`** (eines oder alle?).
Wortlos gehandelt wird bei: Video, Shorts, youtu.be, reine Playlist,
Kanal-Unterseite (`/videos`, `/streams`, …), fremde Seiten (Vimeo & Co.).
Mixe behalten ihre Anzahl-Frage aus Build 98 — es gibt keine zweite daneben.

Die Rückfrage ist ein Menü am Feld (statt `confirm`-Kästen) mit Haken
„Immer so". Gemerkt wird in der Config (`link_antwort_kanal`,
`link_antwort_playlist`); im ⚙-Menü stehen beide als Umschalter samt
„fragen" — **eine gemerkte Antwort darf nie zur Sackgasse werden**.

Der **📺-Knopf ist entfallen**: ein Playlist-/Kanal-Link löst denselben Weg
von selbst aus (weiterhin mit Anzahl + Größenschätzung, damit nicht wortlos
500 Downloads starten). Nichts wurde unerreichbar.

**Live belegt:** alle 10 Linkformen über `/api/link_deuten` korrekt gedeutet;
Weiche für 5 eindeutige Fälle geprüft (`linkAusfuehren` abgefangen, es wurde
nichts geladen); voller Kreis fragt → gemerkt → handelt → zurückgestellt →
fragt wieder; Config danach wieder leer.

**Merker (Triple-String-Falle):** `\'` wird von Python zu `'` und zerlegt den
JS-String — in HTML-Attributen `\\'` schreiben. `node --check` hat es gefangen.

---

## 2. Ein Feld für alles — ERLEDIGT (Build 126), siehe oben

Download / Playlist laden / Abonnieren sind drei zu ähnliche Knöpfe. Ziel: EIN
Feld, Enter genügt, die App erkennt den Typ am Link. Nachgefragt wird NUR bei
echter Mehrdeutigkeit (Kanal: laden oder abonnieren? Video-in-Playlist: eines
oder alle?), mit gemerkter Standardantwort. Links aus dem Browser ins Feld
ziehen funktioniert bereits.

## 3. Vollbild + Seitenverhältnis

Vollbild-Overlay wie Netflix/Disney (erscheint bei Mausbewegung, weg nach ~3 s,
nur das Wichtigste: Play/Pause, ±10 s, Zeitleiste, Untertitel, nächster Titel,
Beenden). **16:9 FEST** — JB ausdrücklich: echtes Maß je Video = Nogo, das Bild
darf nicht springen. Andere Verhältnisse zusätzlich als Layout-Option.

## 4. Interaktions-Paket (JB-Wünsche gesammelt)

- Titel auf Playlists ziehen; auf „keine Playlist" fallen lassen = neue anlegen;
  Mehrfachauswahl zusammen ziehen; **Rückgängig** dafür.
- **Rahmen-Auswahl mit der Maus** wie in Windows / wie in der Abo-Ansicht.
- **Einstellung Einfach- vs. Doppelklick zum Abspielen** (Doppelklick Standard —
  JBs Kumpel bevorzugt Einfachklick; JB: Doppelklick fühlt sich nativer an und
  stört die Auswahl nicht).
- **⋯-Werkzeuge auch im eingebauten Player** (gibt es bisher nur im
  herausgelösten Playlist-Fenster).
- **Sichtbares Geräte-Symbol** für die Fernsteuerung (Funktion existiert bereits:
  ⚙ → „📱 Fernsteuerung"; Handy im selben WLAN steuert den PC-Player ODER
  streamt selbst — Spotify-Connect-Muster).

## 5. Danach (aus der Medienzentrale-Spec, alles JB-bestätigt)

- **VLC als Motor** (Stufe 1 ferngesteuert über python-vlc, Gerät „VLC" in
  `/api/remote`; „VLC nicht gefunden" ⇒ Hinweis + Browser-Player als Rückfall).
- **Album-Cover statt YouTube-Thumbnail**, eingebettet in die Datei (Cover Art
  Archive über MusicBrainz; dazu Songtext von LRCLIB und Genre).
- **Hörbücher/CDs (Etappe 2)**: Werk-Erkennung aus Ordnern, perfekte
  Track-Reihenfolge (Tags → Dateinamen → Online-Trackliste; bei Widerspruch NIE
  raten, sondern in die Prüf-Liste), Ganze-CD-Erkennung über den Dauern-Vektor.
- Wiedergabe-Grundeinstellungen (global → Werk → Titel gemerkt), Spur-Inventar
  für Filme, dann Programm-Hülle (pywebview) mit TV-Modus.

## 6. Reparaturen, die nebenbei auffielen

- ~~Laufende Downloads lassen sich nicht abbrechen~~ — **ERLEDIGT (Build 125b)**,
  siehe oben. Offen bleibt eine zweite Lücke derselben Art: während des
  **Auflösens** (`aufloesen()`, Metadaten holen) gibt es noch keinen
  Abbruch-Weg. Bisher nicht von JB gemeldet, aber dieselbe Bauart.
- **Warteschlange gegen tote Aufträge selbst heilen** (JB: „finde ich gut").
- **Testmodus, der Proben außerhalb JBs echter Ordner fährt** (JB: „finde ich
  gut"). Hintergrund: ein Auto-Import-Test legte eine Probedatei in `Downloads/`;
  Datei, DB-Eintrag und sogar ein Warteschlangen-Auftrag mit erfundener Adresse
  blieben JB sichtbar. Alles bereinigt — technisch verhindern.

## Wartet auf JB — LEER (alle vier von JB abgesegnet, 23.07.)

JB wörtlich: „Die hier segne ich ab." Damit ist die Liste abgearbeitet:

- ~~Probelauf-Klick im Namens-Baukasten~~ — **war zum Zeitpunkt der Abnahme
  bereits angewendet**, die Übergabe war an dieser Stelle veraltet. Das
  Protokoll (`migration_protokoll.json`) trägt genau einen Lauf,
  **23.07.2026 12:05:59, 86 umbenannte Dateien** (79 Medien + mitgewanderte
  Untertitel). Frisch nachgemessen über `/api/migration_probelauf`:
  **0 Kandidaten, 0 Konflikte** — es gibt nichts mehr umzubenennen. Gegenprobe
  auf der Platte: von 108 Dateien trägt nur noch eine eine `[Video-Id]`
  (siehe „Kleine offene Funde"), und alle 86 DB-Pfade zeigen auf existierende
  Dateien. Ein Zurück gibt es weiterhin (⚙ → 🏷 Namens-Baukasten → ↩).
- ~~Kachel-Knöpfe mit echter Maus~~ — von JB bestätigt.
- ~~Karaoke-Wischer an einem echten Lied~~ — von JB bestätigt.
- ~~Firefox-Erweiterung abholen~~ — von JB bestätigt (Kanal liefert 1.0.9).

## Kleine offene Funde (nebenbei gemessen, 23.07.)

- **Ein verwaister Untertitel:** `Downloads/Grim Dawn ｜ Top Tips in 2026 ｜
  v1.3 July 2026 [3dfcRAPHIqA].en.srt` liegt direkt im Downloads-Ordner,
  während sein Video längst umbenannt in `Video/` bzw. `4K+/` liegt. Die
  Migration konnte ihn nicht mitnehmen, weil `_vtt_geschwister()` nur `.vtt`
  im GLEICHEN Ordner sucht (`.srt` und Nachbarordner fallen durch). Nicht
  dringend, aber die Stamm-Kopplung ist an dieser Stelle löchrig.
- **Klick ins Leere räumt in der Playlist nicht ab.** In der Bibliothek macht
  Build 142 das (Explorer-Verhalten), die Playlist hat den Zweig nicht — dort
  fällt es erst jetzt auf, wo eine Rahmen-Auswahl auch sichtbar bleibt.
  Bewusst NICHT mitgebaut (Scope), aber JB wird es bemerken.

## Stand der letzten Builds

110–113 Bibliothek 2.0 Etappe 1 (Erkennungs-Kette Name→Pfad→Fingerabdruck→Tag,
Id-Tags via mutagen, Migrations-Probelauf, Namens-Baukasten mit Undo) ·
114 Bildschirm-Wächter · 115 Karaoke-Wischer · 116–118 Knopf-Diät (359 → 43
sichtbare Knöpfe) · 119 Menüs bleiben im Fenster · 120 Regression behoben ·
121 Steuerzentrale oben behält alles, Bild trägt nur Bild-Sachen ·
122 Ordner-Import läuft von allein · 123 „lokal…" ist keine YouTube-Kennung ·
124 Steuerzentrale läuft nicht mehr über, Ausgeblendetes bleibt erreichbar ·
**125 Kopfleiste fertig** (Stapel-Käfig aufgelöst, Ausweich-Ordnung, Ansicht
rechtsbündig) · **125b Abbruch greift auch beim Zusammenfügen** ·
**126 ein Feld für alles** (link_deuten, Rückfrage nur bei echter
Mehrdeutigkeit, 📺-Knopf entfallen).

## Harte Regeln (aus CLAUDE.md — gelten immer)

- Nicht-destruktiv, Probelauf-Default, Papierkorb statt löschen.
- **Anti-Scroll/magnetisch**: nichts darf aus dem Fenster laufen — weder mobil
  noch Desktop noch Browser. Höchstmaße an die POSITION koppeln; NICHT auf
  ResizeObserver/requestAnimationFrame verlassen (feuern nicht in jeder
  Umgebung — live nachgewiesen).
- **Ausgeblendet ≠ unerreichbar**: was eine Breiten-Regel versteckt, MUSS in
  einem Menü auftauchen.
- **Last-Budget**: keine neuen Dauerprozesse, keine neuen Zeitpläne.
- Tests `System/tests/test_youtube.py` (60/60) — Tests ersetzen `_geladen`
  KOMPLETT, schreiben nie in die echte DB (Vorfall 23.07.: ein Test benannte
  79 echte Dateien um; vollständig zurückgerollt).
- Verifikation ist Pflicht: Tests + `py_compile` + node-Syntaxcheck + echter
  Lauf + Live-Messung im Browser. Nie „behoben" melden, was nicht gemessen ist.
- Commit-Messages über `-F <datei>` (PowerShell zerlegt sonst Anführungszeichen),
  Dateien gezielt mit `git add <pfad>`, nie `add -A`.
- Heißes Nachladen gilt NUR für `oberflaeche.py`; Änderungen an
  `youtube_app.py` brauchen einen App-Neustart.
