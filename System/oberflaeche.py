# -*- coding: utf-8 -*-
"""Die komplette PC-Oberfläche von SyncYouTube — EINE Seite, CSS+JS inline.

Wird von youtube_app.py unter "/" ausgeliefert und bei jedem Aufruf heiß
nachgeladen (importlib.reload) — Änderungen hier erscheinen mit Browser-F5,
ohne App-Neustart. Der sichtbare Baustand steht unten in der Layout-Leiste
("Build …") und wird bei jeder Änderung hochgezählt.

AUFBAU (Banner mit ==== markieren die Hauptbereiche, ---- die Unterbereiche):

  <style>   Farbwelt als CSS-Variablen (--akz/--panel/…; ein „Skin" tönt alles um)
            · Command-Bar · Panels/Fenster · Modals · Warteschlange · Bibliothek
            · Spalten-Menü · Player · Tag-Modus · Container-Queries (schmale Panels)

  <body>    Command-Bar (Link->Download, Live-Queue, Now-Playing) · Layout-Leiste
            · #canvas (die beweglichen Fenster) · Modals (Hilfe/Einstellungen/Geo)
            · #stash mit den Views: add/queue/done/log/lib/player

  <script>  Helfer (esc/mb/zeit) · Looks/Skins · Optionen-Zahnrad
            · Panels/Docking/Snapping + Ansicht-Verlauf (Mausrad) + Layouts
              (Vorlagen/Meine/↩ Vorheriges = Verlust-Schutz wie im Dashboard) + Mini
            · Warteschlange/Status (laden/malen) · Fernsteuerung · Log
            · Command-Bar-Logik + Drag&Drop-Link · Abos · Smart-Playlists · Dubletten
            · Geo/VPN-Assistent · Bibliothek (Ansichten/Spalten/Auswahl/Alben)
            · Abspielmodi/Radio/Sleep/Clip · Kontextmenüs (Explorer-Stil)
            · Player (Speed/Untertitel+Karaoke/Kapitel/Visualizer/EQ/Übergänge/Canvas)
            · Playlists (+Sync/.m3u) · Tastatur · Init (ganz unten)

WICHTIGE FALLE: Dies ist ein Python-Triple-String — ein \\ in JS/HTML muss
verdoppelt werden (\\n, \\d, \\s), sonst frisst Python das Escape und das
JavaScript ist kaputt (node --check nach jeder Änderung laufen lassen!)."""

HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YouTube-Downloader</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 112'%3E%3Cpath d='M 10 96.6 A 100 100 0 0 0 110 96.6 A 100 100 0 0 0 60 10 A 100 100 0 0 0 10 96.6 Z' fill='%23d65f5f'/%3E%3Cpath d='M 73 34 C 70 26 57 23 49 26 C 40 29 38 37 41 44 C 44 51 54 53 60 55 C 68 57 75 61 75 69 C 75 79 65 85 55 84 C 46 83 40 78 39 71' fill='none' stroke='%23f3ede2' stroke-width='14' stroke-linecap='round'/%3E%3C/svg%3E">

<script>(function(){try{var s=localStorage.getItem('ytdl_skin');
  if(!s&&localStorage.getItem('ytdl_theme')==='light')s='hell';   // alte Einstellung übernehmen
  var cls={hell:'light',hacker:'theme-hacker',neon:'theme-neon',ozean:'theme-ozean'}[s];
  if(cls)document.documentElement.classList.add(cls);}catch(e){}})();</script>
<style>
*{box-sizing:border-box}
/* Farbwelt als Variablen — ein „Look" setzt nur diese um (Standard = Terracotta).
   So bleibt das Standard-Aussehen exakt gleich, neue Looks tönen alles konsistent. */
:root{--akz:#c9952b;--akz2:#e0b878;--akzbg:#2a2016;--head:#d67756;--bg:#141110;--panel:#1c1814;--panelln:#2a2522}
html.theme-hacker{--akz:#37f000;--akz2:#8dff6a;--akzbg:#0f2410;--head:#37f000;--bg:#060a06;--panel:#0b140b;--panelln:#18391b}
html.theme-neon{--akz:#ff3ad6;--akz2:#79f5ff;--akzbg:#251236;--head:#ff3ad6;--bg:#0a0812;--panel:#140f22;--panelln:#2c2047}
html.theme-ozean{--akz:#2ba6ff;--akz2:#7ad4ff;--akzbg:#0e2740;--head:#3ec2ff;--bg:#060e18;--panel:#0b1a2b;--panelln:#153450}
html.theme-hacker h1,html.theme-hacker .card h2,html.theme-hacker .modal-head b{font-family:Consolas,"Courier New",monospace}
/* Anti-Scroll (JB 22.07.): die SEITE selbst scrollt nie — Body ist eine Flex-Spalte,
   die Command-Bar bleibt fix, der Canvas füllt den Rest; gescrollt wird nur INNEN
   in den Fenstern (Bibliothek/Playlist/…). */
html{height:100%}
body{font-family:system-ui,Segoe UI,sans-serif;margin:0;background:var(--bg);color:#eee;
  height:100vh;display:flex;flex-direction:column;overflow:hidden}
.topbar{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:16px 18px 6px}
h1{font-size:17px;margin:6px 0 2px;color:var(--head);text-transform:uppercase;letter-spacing:.05em}
.sub{color:#8a7d74;font-size:12px}
.apistat{display:flex;align-items:center;gap:6px;font-size:12px;color:#8a7d74;margin-top:4px}
/* Build 133 (JB): Der Status-Punkt trägt jetzt das Zeichen des Browsers, in
   dem die Oberfläche läuft — Firefox die Erdkugel, Chrome den Ring, Edge den
   Bogen, Safari den Kompass. Der Kern in der Mitte ist der eigentliche
   Status: grün = App erreichbar, rot = getrennt. So sagt EIN Zeichen beides,
   statt dass ein nackter Punkt nur die halbe Geschichte erzählt.
   Die Formen sind bewusst eigene, vereinfachte Andeutungen — keine
   Marken-Dateien, nur so viel Umriss, dass man den Browser wiedererkennt. */
.apidot{width:16px;height:16px;display:inline-flex;flex:none;align-items:center;justify-content:center}
.apidot svg{width:16px;height:16px;display:block}
.apikern{fill:#6fcf7f}                                 /* Status: verbunden */
.apidot.bad .apikern{fill:#e08a6a}                     /* Status: getrennt */
.apiring{fill:none;stroke:currentColor;opacity:.75}
.apidot{color:#8a7d74}
html.light .apidot{color:#a89a8e}
.tools{display:flex;align-items:center;gap:8px;padding-top:6px;flex:none}
.iconbtn{width:34px;height:34px;border-radius:9px;border:1px solid #3a332e;background:#171310;color:#eee;
  font-size:16px;cursor:pointer;line-height:1}
.iconbtn:hover{border-color:var(--akz)}
/* Build 129 (JB-Fund „Formatierung wieder gekippt"): Diese Regeln hingen am
   Selektor `.counter` — eine KLASSE, die es nirgends gibt. Der Zähler heisst
   im HTML `class="cmd-count" id="counter"`; beim Umbau der Steuerzentrale
   wurde die Klasse umbenannt, die Regeln blieben auf dem alten Namen stehen.
   Da `.counter` nichts traf, griff weder `display:none` noch
   `position:absolute`: die Aufschlüsselung war ein normales Inline-Element
   im Fluss und blähte die Statistik-Spalte dauerhaft auf 98 px auf, statt
   beim Überfahren darüber zu schweben (live gemessen: display:inline,
   position:static). Jetzt am echten Element. Die frühere Pillen-Optik ist
   NICHT wiedergekommen — sie war seit dem Umbau ohnehin aus, und das
   Aussehen soll sich durch eine Fehlerbehebung nicht ändern. */
.cmd-count .tip{display:none;position:absolute;right:0;top:calc(100% + 8px);z-index:200;min-width:190px;
  background:#211b16;border:1px solid #3a332e;border-radius:10px;padding:9px 11px;
  box-shadow:0 8px 24px rgba(0,0,0,.5);text-align:left;cursor:default}
.cmd-count:hover .tip,.cmd-count:focus .tip,.cmd-count:focus-within .tip{display:block}
.tiptitel{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#8a7d74;margin-bottom:6px}
.tiprow{display:flex;justify-content:space-between;gap:16px;font-size:13px;padding:2px 0;color:#d7c7bd}
.tiprow b{color:#eee;font-weight:600}
.tipsep{height:1px;background:#3a332e;margin:7px 0 6px}
/* ---- Sticky Command-Bar (oben, hacker/monospace) — 50/50: links Eingabe+Player, rechts Downloads ---- */
#cmdbar{flex:none;z-index:400;background:var(--panel);border-bottom:1px solid var(--panelln);
  padding:6px 12px;font-family:Consolas,"Courier New",monospace;box-shadow:0 2px 12px rgba(0,0,0,.4)}
/* FESTE Command-Bar-Höhe (JB 21.07.: „muss fix sein, egal wie und wo") — kein
   Reiter, kein Modus, kein Inhalt ändert sie; die rechte Seite scrollt intern. */
.cmd-main{display:flex;gap:14px;align-items:stretch;height:188px}
.cmd-left{flex:1 1 50%;min-width:0;display:flex;flex-direction:column;gap:6px;justify-content:center}
.cmd-right{flex:1 1 46%;min-width:0;border-left:1px solid var(--panelln);padding-left:12px;display:flex;flex-direction:column;gap:5px}
/* Fest eingebettetes Download-Fenster in der Command-Bar */
.dlbox-tabs{display:flex;gap:2px;flex:none;align-items:center}
.dlbox-tab{background:none;border:0;color:#8a7d74;font:inherit;font-size:12px;padding:3px 9px;border-radius:7px 7px 0 0;cursor:pointer}
.dlbox-tab:hover{color:#d7c7bd}
.dlbox-tab.an{background:var(--panel2,#241f1b);color:var(--akz2)}
.dlbox-tabs .spacer{flex:1}
.dlbox-action{padding:2px 9px!important;font-size:11px!important}
/* Build 122 (JB): im Mini-Modus dürfen die Reiter (Downloads/Fertig/Log/Abos)
   flacher sein — jeder gesparte Pixel geht an die Liste darunter. */
body.mini .dlbox-tab{font-size:11px;padding:1px 7px}
body.mini .dlbox-action{padding:1px 7px!important;font-size:10.5px!important}
/* Build 122 (JB: „wenn die Bibliothek kleiner wird, sollten unwichtige Reiter
   ausgeblendet werden, wie bei der Manga-Leseliste"). Reihenfolge wie auf
   Handy/Tablet üblich: zuerst geht das WORT (Symbol bleibt), dann das
   Seltene, zuletzt bleibt der Kern. Der Kern ist: Suchen, Ansicht,
   Playlist-Auswahl, Abspielen — alles andere ist erreichbar über die Menüs.
   Umgesetzt über Container-Abfragen, damit es an der BREITE DES FENSTERS
   hängt und nicht am Bildschirm (die Bibliothek ist ein andockbares Panel). */
.libbar{container-type:inline-size}
@container (max-width: 560px){
  .plbar .btn .btxt,.libbar .btn .btxt{display:none}      /* nur noch Symbole */
  .plbar span:first-child{display:none}                    /* das Wort „Playlist:" */
}
@container (max-width: 430px){
  #libsort{display:none}                                   /* Sortieren steckt im Ansicht-Menü */
}
@container (max-width: 340px){
  /* Build 124 (JB: „Mixer und Entdecken verschwinden gleichzeitig, wo finde
     ich die dann?"): sie verschwinden nur aus der LEISTE — plWerkzeuge()
     hängt sie dann oben ins ⋯-Menü. Nichts ist unerreichbar. */
  .plbar .btn:not(#plwerkbtn){display:none}
}
/* Höhe kommt aus der linken Steuerspalte (cmd-main align-items:stretch) — so ist
   die Command-Bar in Voll- UND Mini-Modus EXAKT gleich hoch, nichts springt (JB 21.07.). */
.dlbox-body{flex:1 1 auto;min-height:0;overflow:auto;background:var(--panel2,#1c1815);border-radius:0 8px 8px 8px}
.dlbox-body::-webkit-scrollbar{width:6px}.dlbox-body::-webkit-scrollbar-thumb{background:var(--panelln);border-radius:3px}
.dlbox-body .card{margin:0;background:transparent;border:0;padding:6px 10px}
/* ---- TV-Bibliothek (Sync Teilprojekt 2 v1, JB: „erledige alle aufgaben von
   der roadmap") — 10-Fuß-Regeln der Medienzentrale-Spec: große Schrift,
   Cover-Reihen, reine Pfeil-Navigation mit deutlichem Fokus-Rahmen, dunkles
   Theme, fixe Kopfleiste (Anti-Scroll: nur die Reihen bewegen sich). ---- */
/* Netflix-Farbwelt NUR im TV-Modus (Nachtprüfung 06.08., JB: „Copycat …
   Warum ist bei uns alles ähnlich aber nicht gleich?"): neutrales
   #141414-Schwarz statt der warmen Familien-Brauntöne, EIN Brand-Rot. */
#tv{position:fixed;inset:0;z-index:900;display:none;flex-direction:column;
  background:#141414;color:#fff;font-size:22px;overflow:hidden}
#tv-kopf{display:flex;gap:6px;align-items:center;padding:18px 28px;flex:0 0 auto;
  background:linear-gradient(#141414 70%,transparent)}
#tv-kopf .tvtab{font-size:22px;padding:8px 18px;border-radius:999px;background:none;
  border:2px solid transparent;color:#b3b3b3;cursor:pointer;white-space:nowrap}
#tv-kopf .tvtab.akt{color:#fff;font-weight:700}
#tv-kopf .tvtab.tv-fokus,#tv .tv-kachel.tv-fokus{border-color:#fff;outline:none}
#tv-kopf .tvzu{margin-left:auto;font-size:22px;background:none;border:2px solid transparent;
  border-radius:999px;color:#b3b3b3;padding:8px 16px;cursor:pointer}
/* Mehr Rand beidseits (JB 07.08.: Fokus-Rahmen der ERSTEN Kachel war links
   abgeschnitten — „etwas mehr zentrieren die beiden seiten"). */
#tv-inhalt{flex:1;overflow-y:auto;padding:6px 48px 40px}
#tv .tv-rtitel{font-size:22px;font-weight:600;color:#e5e5e5;margin:18px 2px 10px}
#tv .tv-band{display:flex;gap:8px;overflow-x:auto;padding:6px 8px 10px;scrollbar-width:none}
#tv .tv-band.wrap{flex-wrap:wrap;overflow-x:visible}   /* „Alle A–Z"-Raster */
#tv .tv-kachel{flex:0 0 auto;width:150px;cursor:pointer;border:3px solid transparent;
  border-radius:8px;padding:3px;position:relative;transition:transform .25s}
/* Netflix-Zoom: D-Pad-Fokus tritt DEUTLICH hervor (10-Fuß), Maus-Hover nur
   sanft — die große Ansicht übernimmt die Hover-Karte. */
#tv .tv-kachel.tv-fokus{transform:scale(1.3);z-index:5}
#tv .tv-band:not(.wrap) .tv-kachel:hover{transform:scale(1.06);z-index:5}
/* Filme/Serien QUER in 16:9 (JB 06.08.: „Das ist immer noch nicht 16:9.
   Warum?" + Netflix-Referenz): Backdrop-Kacheln, sanfter Zoom — die große
   Ansicht übernimmt die Hover-Karte. */
/* Responsive Spalten (JB 07.08.: „der Film soll am anfang und am ende
   komplett anfangen und abschließen — für alle Displaygrößen"): die
   Kachelbreite rechnet sich aus dem Viewport, sodass IMMER eine ganze
   Anzahl in die Bahn passt — wie bei Netflix 6/5/4/3 Spalten je Breite.
   112px = Seitenränder (2×48) + Band-Innenabstand (2×8). */
#tv .tv-kachel.f16{width:calc((100vw - 152px)/6)}
@media(max-width:1499px){#tv .tv-kachel.f16{width:calc((100vw - 144px)/5)}}
@media(max-width:1099px){#tv .tv-kachel.f16{width:calc((100vw - 136px)/4)}}
@media(max-width:799px){#tv .tv-kachel.f16{width:calc((100vw - 128px)/3)}}
#tv .tv-kachel.f16 img{height:auto;aspect-ratio:16/9}
#tv .tv-kachel.f16.tv-fokus,#tv .tv-band:not(.wrap) .tv-kachel.f16:hover{transform:scale(1.06)}
/* Karte offen: Quell-Kachel sofort ohne Zoom (transition aus, sonst misst
   die Karten-Platzierung die noch gezoomte Geometrie). */
#tv .tv-kachel.hk-quelle{transform:none!important;transition:none!important}
#tv .tv-kachel .tv-kbalken{height:4px;border-radius:2px;background:rgba(255,255,255,.3);margin:5px 8px 0}
#tv .tv-kachel .tv-kbalken div{height:100%;border-radius:2px;background:#e50914}
/* Blätter-Pfeile an den Reihen-Enden (JB: „Mit pfeil nach rechts sollte
   doch immer mehr erscheinen") — sichtbar beim Verweilen, wie Netflix. */
#tv .tv-reihe{position:relative}
#tv .tv-pfeil{position:absolute;width:46px;top:48px;bottom:36px;border:none;cursor:pointer;
  background:rgba(20,20,20,.55);color:#fff;font-size:38px;z-index:6;opacity:0;
  transition:opacity .2s;border-radius:4px;display:flex;align-items:center;justify-content:center}
#tv .tv-reihe:hover .tv-pfeil{opacity:1}
#tv .tv-pfeil.links{left:-40px}
#tv .tv-pfeil.rechts{right:-40px}
#tv .tv-pfeil:hover{background:rgba(20,20,20,.85)}
#tv .tv-seiten{position:absolute;right:4px;top:26px;display:flex;gap:2px;
  opacity:0;transition:opacity .2s}
#tv .tv-reihe:hover .tv-seiten{opacity:1}
#tv .tv-seiten span{width:12px;height:2px;background:#4d4d4d}
#tv .tv-seiten span.an{background:#aaa}
#tv .tv-dauer{position:absolute;top:8px;right:8px;z-index:2;font-size:13px;
  color:#fff;background:rgba(12,10,9,.7);border-radius:5px;padding:1px 7px}
/* Hover-Karte (Netflix-Referenzbilder 06.08.): schwebende Quer-Karte über
   der Kachel — 16:9-Clip oben, Knopfzeile, Fortschritt/Meta, Genre-Tags. */
.tv-hoverkarte{position:fixed;z-index:930;background:#181818;border-radius:6px;
  overflow:hidden;box-shadow:0 12px 44px rgba(0,0,0,.85);cursor:pointer;
  animation:hkAuf .18s ease-out;padding-bottom:12px}
@keyframes hkAuf{from{transform:scale(.75);opacity:.4}to{transform:scale(1);opacity:1}}
.tv-hoverkarte .hk-bild{position:relative;aspect-ratio:16/9;background:#000}
.tv-hoverkarte .hk-bild img,.tv-hoverkarte .tv-snip{position:absolute;inset:0;
  width:100%;height:100%;object-fit:cover;display:block}
.tv-hoverkarte .hk-titel{position:absolute;left:12px;bottom:8px;right:12px;z-index:2;
  font-size:17px;font-weight:700;color:#fff;text-shadow:0 1px 6px rgba(0,0,0,.9);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tv-hoverkarte .hk-zeile{display:flex;gap:8px;align-items:center;padding:10px 12px 6px}
.tv-hoverkarte .hk-ib{width:36px;height:36px;border-radius:50%;border:2px solid rgba(255,255,255,.5);
  background:rgba(42,42,42,.9);color:#fff;font-size:16px;cursor:pointer;line-height:1}
.tv-hoverkarte .hk-ib:hover{border-color:#fff}
.tv-hoverkarte .hk-ib svg{width:16px;height:16px;fill:currentColor;vertical-align:middle}
.tv-hoverkarte .hk-play{background:#fff;color:#111;border-color:#fff}
.tv-hoverkarte .hk-rechts{margin-left:auto}
.tv-hoverkarte .hk-balken{display:flex;gap:10px;align-items:center;padding:4px 12px 0;
  font-size:13px;color:#b3b3b3}
.tv-hoverkarte .hk-spur{flex:1;height:4px;border-radius:2px;background:rgba(255,255,255,.3)}
.tv-hoverkarte .hk-spur div{height:100%;border-radius:2px;background:#e50914}
.tv-hoverkarte .hk-meta{display:flex;gap:10px;align-items:center;padding:4px 12px 0;
  font-size:13px;color:#d2d2d2}
.tv-hoverkarte .hk-fsk{border:1px solid rgba(255,255,255,.4);padding:0 6px;font-size:12px}
.tv-hoverkarte .hk-hd{border:1px solid rgba(255,255,255,.4);border-radius:3px;padding:0 4px;font-size:11px}
.tv-hoverkarte .hk-tags{padding:6px 12px 0;font-size:13px;color:#fff}
#tv .tv-kachel img{width:100%;height:216px;object-fit:cover;border-radius:6px;
  background:#2a2a2a;display:block}                    /* leichte Rundung (JB 06.08.) */
#tv .tv-kachel.quer img{height:96px}
#tv .tv-kachel.quer{width:170px}
#tv .tv-ktitel{font-size:15px;margin-top:6px;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;text-align:center}
#tv .tv-leer{color:#8a7d74;font-size:18px;padding:30px 4px}
#tv-suche{font-size:26px;padding:12px 20px;border-radius:12px;border:2px solid #3a322b;
  background:#171310;color:#fff;width:min(600px,80%);margin:10px 0}
/* Hero-Billboard (JB 05.08. mit Netflix-Referenzbildern: „der headline film
   ist zu sehr gequetscht") — hoch, randlos, Titel riesig, Bild läuft frei
   nach rechts; Text bleibt lesbar über einem Links- + Unten-Verlauf. */
#tv-hero{position:relative;min-height:56vh;margin:0 -28px 8px;overflow:hidden;
  display:flex;align-items:flex-end;background:#0c0a09}
#tv-hero .hero-bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
#tv-hero::after{content:'';position:absolute;inset:0;
  background:linear-gradient(90deg,rgba(12,10,9,.96) 6%,rgba(12,10,9,.55) 40%,transparent 68%),
             linear-gradient(0deg,#0c0a09 0,transparent 24%)}
#tv-hero .hero-text{position:relative;z-index:1;max-width:46%;padding:0 28px 5vh 28px}
#tv-hero .hero-titel{font-size:clamp(40px,4.6vw,74px);font-weight:900;line-height:1.05;
  margin-bottom:14px;text-shadow:0 2px 14px rgba(0,0,0,.65);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
#tv-hero .hero-meta{font-size:18px;color:#d8cec4;margin-bottom:12px}
#tv-hero .hero-besch{font-size:18px;color:#e6ddd2;max-width:640px;
  display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
#tv-hero .hero-btns{display:flex;gap:12px;margin-top:18px}
.tv-btn{font-size:22px;padding:10px 26px;border-radius:4px;cursor:pointer;
  border:3px solid transparent;background:#f2ece5;color:#171310;font-weight:700}
.tv-btn.zart{background:rgba(109,109,110,.7);color:#fff}
.tv-btn.akt{background:rgba(232,176,75,.35)}          /* gewählte Staffel */
.tv-btn.tv-fokus{border-color:#fff}
/* Film-Player (Build 188, Netflix-Layout nach JBs Bildern): Leiste unten
   über volle Breite, ← oben links; Inaktivität blendet aus; Pause-Idle. */
#tv-player{position:fixed;inset:0;z-index:970;display:none;background:#0c0a09;color:#f2ece5}
#tv-player .tvp-bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.28}
#tv-player .tvp-video{position:absolute;inset:0;width:100%;height:100%;
  object-fit:contain;background:#000}                  /* Browser-Player (Netflix-Weg) */
#tv-player .tvp-standbild{position:absolute;inset:0;width:100%;height:100%;
  object-fit:contain;background:#000}                  /* Pause-Moment (VLC-Schnappschuss) */
#tv-player .tvp-ui{position:absolute;inset:0;z-index:1;transition:opacity .5s}
#tv-player.idle .tvp-zurueck,#tv-player.idle .tvp-unten{opacity:0;pointer-events:none}
#tv-player.idle #tvp-panel{display:none!important}
/* Settings-Panel (Netflix-Referenz „Playback Speed"): dunkle Karte über der
   Leiste rechts — Tempo-Reihe bzw. Ton-/Untertitel-Spalten. */
#tvp-panel{position:absolute;right:28px;bottom:130px;background:#1c1c1c;border-radius:10px;
  padding:16px 20px;box-shadow:0 8px 30px rgba(0,0,0,.7);z-index:6;max-width:560px}
#tvp-panel .tvpp-titel{font-weight:700;font-size:17px;margin-bottom:10px;color:#fff}
#tvp-panel .tvpp-reihe{display:flex;gap:6px;align-items:center}
#tvp-panel .tvpp-spalten{display:flex;gap:28px;max-height:300px;overflow:auto}
#tvp-panel .tvpp-knopf{display:block;background:none;border:none;color:#ddd;font-size:15px;
  padding:6px 10px;border-radius:6px;cursor:pointer;text-align:left;white-space:nowrap}
#tvp-panel .tvpp-reihe .tvpp-knopf{display:inline-block}
#tvp-panel .tvpp-knopf:hover{background:#333}
#tvp-panel .tvpp-knopf.an{color:#fff;font-weight:700}
#tvp-panel .tvpp-knopf.tv-fokus{background:#333;box-shadow:inset 0 0 0 2px #fff}
#tvp-panel .tvpp-leer{color:#8a8a8a;font-size:14px}
#tv-player .tvp-zurueck{position:absolute;top:22px;left:26px;font-size:34px;background:none;
  border:none;color:#fff;cursor:pointer;transition:opacity .5s}
#tv-player .tvp-unten{position:absolute;left:0;right:0;bottom:0;padding:14px 30px 20px;
  background:linear-gradient(0deg,rgba(12,10,9,.9),transparent);transition:opacity .5s}
#tv-player .tvp-balkenzeile{display:flex;align-items:center;gap:16px;margin-bottom:10px}
#tv-player .tvp-balkenwrap{flex:1;padding:10px 0;cursor:pointer}
#tv-player .tvp-balken{height:5px;background:rgba(255,255,255,.28);border-radius:3px;overflow:hidden}
#tv-player .tvp-balken div{height:100%;width:0;background:#e50914}
#tv-player .tvp-zeit{font-size:16px;color:#fff;white-space:nowrap}
#tv-player .tvp-reihe{display:flex;align-items:center;gap:16px}
#tv-player .tvp-ib{background:none;border:none;color:#fff;font-size:26px;cursor:pointer;
  display:inline-flex;align-items:center}
#tv-player .tvp-ib svg{width:30px;height:30px;fill:#fff}
#tv-player .tvp-mtitel{position:absolute;left:50%;transform:translateX(-50%);
  font-size:18px;font-weight:700;white-space:nowrap;max-width:42%;
  overflow:hidden;text-overflow:ellipsis}
#tv-player .tvp-rechts{margin-left:auto}
#tv-player .tvp-lade{position:absolute;left:50%;top:44%;transform:translate(-50%,-50%);
  display:flex;flex-direction:column;align-items:center;gap:14px;color:#d8cec4;font-size:18px}
#tv-player .tvp-spin{width:54px;height:54px;border-radius:50%;border:5px solid rgba(255,255,255,.2);
  border-top-color:#e50914;animation:tvpdreh 1s linear infinite}
@keyframes tvpdreh{to{transform:rotate(360deg)}}
#tv-player .tvp-idle{position:absolute;left:6vw;top:30vh;max-width:640px;display:none;
  flex-direction:column;gap:10px}
/* Pause-Text liegt ÜBER dem stehenden Filmbild (JB 07.08.): weiß mit
   leichtem Schatten — lesbar auf jedem Untergrund, kein Dimmen. */
#tv-player .tvp-idle{text-shadow:0 1px 8px rgba(0,0,0,.9)}
#tv-player .tvp-idle-klein{font-size:19px;color:#fff}
#tv-player .tvp-idle-titel{font-size:56px;font-weight:900;line-height:1.05;color:#fff}
#tv-player .tvp-idle-meta{font-size:20px;color:#fff;font-weight:700}
#tv-player .tvp-idle-besch{font-size:17px;color:#f0f0f0}
#tv-player .tvp-idle-paused{position:fixed;right:6vw;bottom:10vh;font-size:22px;
  color:#fff;text-shadow:0 1px 8px rgba(0,0,0,.9)}
/* TV-Profil-Dialog (eigener statt prompt(), JB: „bau den") */
#tv-dialog{position:fixed;inset:0;z-index:980;display:none;align-items:center;
  justify-content:center;background:rgba(8,6,5,.82);color:#f2ece5}
#tv-dialog .dlg{background:#141110;border-radius:14px;padding:32px 38px;
  width:min(560px,92vw);text-align:center;box-shadow:0 14px 70px rgba(0,0,0,.85)}
#tv-dialog input{font-size:26px;padding:12px 20px;border-radius:12px;
  border:2px solid #3a322b;background:#171310;color:#fff;width:80%;text-align:center}
#tv-dialog input:focus{border-color:#e8b04b;outline:none}
#tv-dialog .emojis{display:flex;gap:10px;justify-content:center;margin:20px 0;flex-wrap:wrap}
#tv-dialog .emo{font-size:38px;padding:6px 12px;border-radius:12px;
  border:3px solid transparent;background:#221c17;cursor:pointer}
#tv-dialog .emo.akt{background:rgba(232,176,75,.35)}
#tv-dialog .emo.tv-fokus{border-color:#e8b04b}
/* „Wer schaut?" (Teilprojekt 3): große Profil-Kacheln in der Mitte */
#tv .tv-profil{width:150px;text-align:center}
#tv .tv-pemoji{font-size:84px;line-height:1.4;background:#221c17;border-radius:14px;padding:14px 0}
/* More-Info als ZENTRIERTES Modal (JB mit Netflix-Bildern: „es sollte etwas
   zentrierter sein, so wie bei netflix eben") — Karte über abgedunkeltem
   Hintergrund, X oben rechts, Kopfbild mit Titel + Balken + Knopfzeile. */
#tv-info{position:fixed;inset:0;z-index:950;display:none;align-items:flex-start;
  justify-content:center;background:rgba(8,6,5,.74);color:#f2ece5;
  overflow-y:auto;padding:4vh 0}
#tv-info .info-karte{width:min(940px,94vw);margin:auto;background:#141110;
  border-radius:14px;overflow:hidden;box-shadow:0 14px 70px rgba(0,0,0,.85)}
#tv-info .info-kopf{position:relative;aspect-ratio:16/9;min-height:240px;overflow:hidden}
#tv-info .info-kopf img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
#tv-info .info-kopf::after{content:'';position:absolute;inset:0;
  background:linear-gradient(0deg,#141110 3%,transparent 52%)}
#tv-info .info-x{position:absolute;top:14px;right:14px;z-index:2;width:44px;height:44px;
  border-radius:50%;background:rgba(12,10,9,.75);color:#fff;border:3px solid transparent;
  font-size:20px;cursor:pointer}
#tv-info .info-x.tv-fokus{border-color:#e8b04b}
/* Netflix-Fluss (JB-Fund: „Die Leiste … wird vom Filmtext verdeckt"): Titel,
   Balken und Knöpfe stapeln sich als FLEX-SPALTE von unten — nichts kann
   mehr überlappen, egal wie viele Zeilen der Titel braucht. */
#tv-info .info-kopf-inhalt{position:absolute;left:34px;right:34px;bottom:20px;z-index:1;
  display:flex;flex-direction:column;gap:12px;align-items:flex-start}
#tv-info .info-titel{font-size:clamp(30px,3.4vw,48px);font-weight:900;line-height:1.05;
  text-shadow:0 2px 12px rgba(0,0,0,.8);max-width:75%}
#tv-info .info-kopfzeile{width:100%}
#tv-info .info-body{padding:20px 34px 34px;font-size:18px}
#tv-info .info-spalten{display:grid;grid-template-columns:1.7fr 1fr;gap:8px 30px;margin-bottom:6px}
#tv-info .info-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
#tv-info .info-grid .tv-kachel{width:auto}
/* JB-Fund 06.08. („die Bilder haben unterschiedliche größen"): die
   Info-Seite hängt an <body>, NICHT in #tv — die #tv-Kachelregeln
   (width:100%) griffen hier nie und jedes Bild kam in Rohgröße. */
#tv-info .tv-kachel img{width:100%;object-fit:cover;border-radius:6px;
  background:#2a2a2a;display:block}
#tv-info .info-grid .tv-kachel img{height:auto;aspect-ratio:16/9}
#tv-info .info-meta{font-size:18px;color:#d8cec4;margin-bottom:10px}
#tv-info .info-besch{color:#e6ddd2;margin-bottom:12px}
#tv-info .info-neben{font-size:16px;color:#a99d92;margin:4px 0}
#tv-info .info-btns{display:flex;gap:12px;margin:14px 0 6px;flex-wrap:wrap}
#tv-info .info-badge{border:1px solid #8a7d74;border-radius:4px;padding:1px 8px;
  font-size:15px;color:#d8cec4;vertical-align:1px}
#tv-info .info-punkt{margin:0 10px;color:#6b6058}
#tv-info .info-progresswrap{display:flex;align-items:center;gap:12px;max-width:520px;margin:10px 0 2px}
#tv-info .info-progress{flex:1;height:5px;background:#3a322b;border-radius:3px;overflow:hidden}
#tv-info .info-progress div{height:100%;background:#e50914}
#tv-info .info-rest{font-size:15px;color:#b9aea4;white-space:nowrap}
#tv-info .info-tagline{font-style:italic;color:#b9aea4;margin:6px 0;font-size:18px}
#tv-info .info-ueber{margin-top:26px;padding-top:8px;border-top:1px solid #2a241f;color:#b9aea4}
#tv-info .info-ueber .info-neben{font-size:15px}
/* ❤ Lieblingssongs (JB 05.08.): Herz-Badge auf der Kachel + rote Toggles */
.herzbadge{position:absolute;top:6px;left:6px;color:#e5484d;font-size:15px;
  text-shadow:0 1px 3px rgba(0,0,0,.7);pointer-events:none}
.ib.herz.an,.mp-btn.herz.an{color:#e5484d}
/* Filme (Film-Fundament): Poster-Bänder wie bei den Streamern — die REIHE
   scrollt horizontal in sich (Anti-Scroll: die Seite selbst wächst nicht). */
#view-filme .f-rtitel{font-weight:700;margin:10px 2px 6px;font-size:14px}
#view-filme .f-band{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px}
#view-filme .f-kachel{flex:0 0 auto;width:108px;cursor:pointer}
#view-filme .f-kachel img{width:108px;height:162px;object-fit:cover;border-radius:8px;background:#221c17;display:block}
#view-filme .f-kachel:hover img{outline:2px solid var(--akzent,#e8b04b)}
#view-filme .f-ktitel{font-size:11px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* Abos im kompakten Download-Fenster: kleiner + ohne die lange Erklärung, damit
   man nicht scrollen muss (JB 21.07.). */
.dlbox-body #view-abos{font-size:11.5px}
.dlbox-body #view-abos .hinweis{display:none}
.dlbox-body #view-abos .zeile{gap:5px;margin-bottom:6px}
.dlbox-body #view-abos input,.dlbox-body #view-abos select,.dlbox-body #view-abos .btn{font-size:11.5px;padding:4px 8px}
.dlbox-body #view-abos .abo-liste{gap:5px}
.dlbox-body #view-abos .abo-card{padding:5px 8px}
.dlbox-body #view-abos .abo-name{font-size:12px}
.dlbox-body #view-abos .abo-regeln,.dlbox-body #view-abos .abo-f{font-size:11px}
/* Mini: statt der Download-Reiter sitzt hier der eingebettete Mini-Player */
#cmd-mini:empty{display:none}
#cmd-mini{display:flex;flex-direction:column;flex:1;min-height:0}
body.mini #cmd-mini #view-player{height:100%}
html.light .dlbox-tab.an{background:#efe7de}
html.light .dlbox-body{background:#f3ede4}
.cmd-row1,.cmd-row2,.cmd-rowadd{display:flex;align-items:center;gap:8px}
.cmd-rowadd .cmd-url{flex:1;min-width:120px}
.cmd-row2 .spacer{flex:1}
.cmd-logo{display:inline-flex;align-items:center;gap:7px;font-size:14px;white-space:nowrap;flex:none}
.cmd-logo .emblem{flex:none}
.cmd-logo b{font-weight:600;letter-spacing:.01em;color:#e9ded3}
html.light .cmd-logo b{color:#3a322c}
.cmd-logo .sg{stroke:#141110}                        /* S-Rille = Seiten-Hintergrund, folgt Tag/Nacht */
html.light .cmd-logo .sg{stroke:#f3ede2}
.cmd-url{flex:1;min-width:80px;background:#0e0c0a;border:1px solid var(--panelln);border-radius:7px;
  color:#e7dccf;padding:5px 10px;font:inherit;font-size:12px}
.cmd-url:focus{outline:none;border-color:var(--akz)}
.cmd-qual{background:#0e0c0a;border:1px solid var(--panelln);border-radius:7px;color:#d7c7bd;padding:4px 6px;font:inherit;font-size:12px}
.cmd-dl{background:var(--akzbg);border:1px solid var(--akz);border-radius:7px;color:var(--akz2);
  padding:5px 12px;font:inherit;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
.cmd-dl:hover{filter:brightness(1.18)}
/* Mini-Player (JB 13.07.): füllt den linken Block — große Spotify-artige
   Knöpfe oben, Titel darunter, Spulleiste unten; rechts Zähler + vertikale Knöpfe */
.cmd-row2{align-items:stretch;gap:10px}
/* Command-Bar-Player als eigene, wertige Karte (JB 21.07.): Rahmen, dezenter
   Hintergrund, runde Ecken; läuft etwas, glimmt der Rahmen in Programm-Rot. */
/* Build 125 (JB-Fund „Statistik überlappt den Player", gemessen bei 360 px):
   Statistik und Symbol-Spalte sind flex:none und geben NIE nach — also
   schrumpfte allein der Player, auf 69 px, und sein Inhalt lief 135 px
   heraus, mitten unter die Statistik. Der Player ist der KERN und bekommt
   deshalb ein Mindestmaß; ausweichen muss jetzt etwas anderes (siehe die
   Ausweich-Ordnung bei .cmd-stat weiter unten). */
.cmd-now{flex:1;min-width:220px;display:flex;flex-direction:column;justify-content:center;gap:6px;font-size:12px;color:#9a8d84;
  border:1px solid #2e2823;border-radius:12px;padding:7px 14px;background:rgba(255,255,255,.022)}
.cmd-now.spielt{border-color:rgba(214,95,95,.45);box-shadow:0 0 0 1px rgba(214,95,95,.12),0 4px 16px rgba(0,0,0,.25)}
.cmd-now.dropziel{outline:2px dashed var(--akz);outline-offset:2px}
/* Build 136: dieselbe Rueckmeldung fuer die ganze Player-Karte. */
#pl-card.dropziel{outline:2px dashed var(--akz);outline-offset:-3px;border-radius:12px}
/* Build 124 (JB-Fund, gemessen: die Knopfreihe braucht 449 px und hat bei
   975 px Fensterbreite nur 297 → sie quoll über den Rahmen). Jetzt räumt die
   Steuerzentrale gestaffelt auf, statt überzulaufen. Reihenfolge: zuerst das
   Seltene (Cover-Stil, Link, YouTube), dann die Lautstärke (liegt auch im
   Player), zuletzt bleibt der Kern: Zufall · Zurück · Play · Vor ·
   Wiederholen · Radio. ALLES Ausgeblendete bleibt per Rechtsklick in den
   Player erreichbar (Kontextmenü) — nichts verschwindet ersatzlos. */
.cmd-now{container-type:inline-size}
.cmd-now .mp-row{flex-wrap:nowrap;min-width:0;overflow:hidden}
@container (max-width: 430px){ .cmd-now .mp-art,.cmd-now .mp-btn[title^="YouTube-Link"]{display:none} }
@container (max-width: 380px){ .cmd-now .mp-yt{display:none} }
@container (max-width: 330px){ .cmd-now .mp-vol{display:none} }
@container (max-width: 260px){ .cmd-now .mp-radio{display:none} }
/* Build 121 (JB-Entscheid): Die Leiste oben ist die STEUERZENTRALE und
   behält IMMER alles — sie ist der Ort, an dem JB sich wohlfühlt (Spotify-
   Muster: eine Steuerung, immer dieselbe Stelle, verschwindet nie). Die
   Doppelung wird nicht mehr durch Wegnehmen gelöst, sondern durch
   Zuständigkeit: oben „was spiele ich", im Bild nur „wie sehe ich es"
   (Untertitel/Schnitt/Tempo/Bild-in-Bild/Vollbild — Netflix-Muster,
   erscheint bei Mausbewegung). Die frühere Ausblend-Regel ist damit weg. */
html.light .cmd-now{border-color:#e3d8cc;background:rgba(0,0,0,.02)}
.cmd-nowtitel{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;font-size:12.5px;color:#d7c7bd;font-weight:500}
.cmd-nolabel{color:#6a5c52}
.cmd-seekline{display:flex;align-items:center;gap:8px}
.cmd-time{flex:none;font-size:11px;color:#8a7d74;min-width:36px;text-align:center;font-variant-numeric:tabular-nums}
#cmd-seek{flex:1;min-width:60px;height:14px;accent-color:var(--akz);cursor:pointer;margin:0}
#cmd-seek:disabled{opacity:.35;cursor:default}
/* Build 131 (JB): Zähler und API-Punkt stehen NEBENeinander, direkt neben dem
   Mini-Player — nicht mehr als schmale Säule mit dem Zähler oben und dem
   Punkt weit darunter. Seit der Tooltip wieder schwebt (Build 129) ist der
   Zähler nur noch 26 px breit; eine eigene Spalte über die volle Zeilenhöhe
   für zwei winzige Zeichen sah verloren aus und kostete den Player Platz.
   Die Ausweich-Ordnung bleibt unberührt: unter 430 px weicht der Zähler,
   Warnung und Punkt bleiben stehen. */
/* Build 132: .cmd-stat als eigene Spalte ist entfallen — Zähler und Punkt
   wohnen in der ersten Reihe (JB). Der Zähler bringt hier seinen eigenen
   Abstand mit; der Tooltip klappt weiterhin unter ihm auf. */
.cmd-row1 #counter{margin-left:4px}
.cmd-row1 .apidot{margin-right:2px}
.cmd-side{display:flex;flex-direction:column;justify-content:center;gap:3px;flex:none}
/* Transport-Knöpfe: selbst gezeichnete SVGs, Spotify-Größe; aktiver Toggle =
   Akzentfarbe + Punkt darunter, inaktiv = neutral (JB 13.07.) */
.mp-row{display:flex;align-items:center;gap:8px}
.mp-btn{display:inline-flex;align-items:center;justify-content:center;background:none;border:0;
  color:#d7c7bd;cursor:pointer;width:30px;height:30px;padding:0;border-radius:50%;flex:none;font-size:14px}
.mp-btn svg{width:20px;height:20px;fill:currentColor;display:block}
.mp-btn:hover{color:#fff;transform:scale(1.08)}
.mp-play{width:37px;height:37px;background:#e7dccf;color:#171310}
.mp-play:hover{background:#fff;color:#171310}
.mp-play svg{width:21px;height:21px}
.mp-tog{color:#8a7d74;position:relative}
.mp-tog.an{color:var(--akz)}
.mp-tog.an::after{content:'';position:absolute;left:50%;bottom:0;width:4px;height:4px;border-radius:50%;
  background:var(--akz);transform:translateX(-50%)}
.mp-radio{font-size:15px}
.mp-art{width:auto;min-width:30px;padding:0 5px;font-size:13px;border-radius:15px}
html.light .mp-btn{color:#5a4f47} html.light .mp-btn:hover{color:#2a2016}
html.light .mp-play{background:#2a2016;color:#fff} html.light .mp-play:hover{background:#000;color:#fff}
html.light .mp-tog{color:#a89a8e}
html.light .cmd-nowtitel{color:#4a3f37}
.cmd-count{color:#d7c7bd;white-space:nowrap;position:relative;cursor:default;font-size:12px;flex:none}
.cmd-count b{color:var(--akz2);font-weight:700}
.iconbtn.sm{width:28px;height:28px;font-size:14px;flex:none}
/* Download-Liste (rechte Spalte): eine Zeile je Download, Klick = Pause/Fortsetzen */
.cmd-queue{display:flex;flex-direction:column;gap:3px}
.cmd-empty{color:#6a5c52;font-size:11px;padding:2px 0}
.dlrow{display:flex;align-items:center;gap:8px;cursor:pointer;padding:3px 5px;border-radius:6px}
.dlrow:hover{background:#0e0c0a}
.dlrow.laeuft{background:rgba(255,255,255,.02)}
.dlic{flex:none;font-size:11px}
.dltitel{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#d7c7bd;font-size:11.5px}
.dlbar{flex:none;width:90px;height:6px;background:#241f1b;border-radius:99px;overflow:hidden}
.dlbar i{display:block;height:100%;background:var(--akz);border-radius:99px;transition:width .5s}
.dlrow.fehler .dlbar i{background:#e08a6a}.dlrow.pausiert .dlbar i{background:#8a7d74}
.dlpct{flex:none;color:#8a7d74;font-size:10.5px;min-width:44px;text-align:right}
.dlx{flex:none;background:none;border:0;color:#6a5c52;cursor:pointer;font-size:11px;padding:0 3px;border-radius:4px}
.dlx:hover{color:#e08a6a;background:#0e0c0a}
.cmd-clip{margin-top:6px;align-items:center;gap:8px;font-size:11.5px;color:var(--akz2);
  background:var(--akzbg);border:1px solid var(--akz);border-radius:7px;padding:4px 9px;display:flex}
.clipurl{color:#d7c7bd;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
@media(max-width:660px){.cmd-main{flex-direction:column;height:auto}
  .cmd-right{border-left:0;border-top:1px solid var(--panelln);padding-left:0;padding-top:6px;max-height:96px}}
/* ---- AUSWEICH-ORDNUNG der Kopfleiste (Build 125) ----------------------
   Die Kopfleiste hat über mehrere Runden immer denselben Fehler gezeigt,
   weil eine Regel fehlte: WAS weicht bei Platzmangel WOHIN aus? Ohne diese
   Rangfolge gibt immer das nach, was zufällig `flex:1` trägt — hier der
   Player. Die Ordnung lautet ab jetzt, vom Nachgiebigsten zum Festesten:

   1. Der ZÄHLER weicht zuerst (reine Information). Er ist danach im
      ⚙-Menü als Zeile „Geladen" abzulesen — dort steht er IMMER, nicht
      nur wenn er hier fehlt (JB-Regel: ausgeblendet ≠ unerreichbar; eine
      Zeile, die immer da ist, kann auch nie durch eine Breiten-Regel
      verlorengehen).
   2. WARNUNG (⚠ bin-Ordner) und API-Punkt bleiben. Ein Statuszeichen darf
      nie still verschwinden — sonst hält JB einen Fehler für Normalbetrieb.
   3. Der PLAYER bleibt ganz (min-width:220px, siehe oben) — er ist der
      Kern der Steuerzentrale.
   4. Die SYMBOL-SPALTE bleibt senkrecht und 28 px schmal. Sie war früher
      bei ≤660 px auf flex-direction:row gedreht; gemessen bei 476 px lag
      sie dann 121 px breit nebeneinander (JB-Bild) und fraß genau den
      Platz, der dem Player fehlte. Senkrecht ist ihre schmalste Form —
      die Drehung war ein Eigentor. */
@media(max-width:430px){ #counter{display:none} }
/* Build 132: Die erste Reihe trägt seit dem Umzug von Punkt und Zähler mehr
   Inhalt. Gemessen bei 373 px: sie brauchte 361 px in einem 336-px-Kasten
   und lief heraus. Zuerst weicht der WORTLAUT des Logos (141 px) — das
   Emblem bleibt und trägt die Wiedererkennung, der Name steht ohnehin im
   Fenstertitel. `flex-wrap` ist das Netz darunter: sollte es trotzdem einmal
   eng werden, bricht die Reihe um, statt aus dem Fenster zu laufen. */
.cmd-row1{flex-wrap:wrap}
@media(max-width:520px){ .cmd-logo b{display:none} }
html.light #cmdbar{background:#fff;border-color:#e6ddd3}
html.light .cmd-url,html.light .cmd-qual{background:#f7f3ee;border-color:#e0d7cc;color:#4a3f37}
html.light .dlrow:hover{background:#f3ede7}
html.light .dltitel,html.light .cmd-count{color:#5a4f47}
html.light .dlbar{background:#e6ddd3}
/* Layout-Werkzeuge-Leiste NUR im ✏-Modus (sonst kein toter Raum, JB 21.07.) */
#layoutbar{display:none;flex:none;gap:10px;align-items:center;flex-wrap:wrap;padding:6px 18px 8px;font-size:12px;color:#8a7d74}
body.layoutedit #layoutbar{display:flex}
#layoutbar select{max-width:230px}
/* Mini-Player-Modus: der Player sitzt kompakt eingebettet in der Command-Bar
   (#cmd-mini) — Seitenliste weg, Karte flach (JB 21.07.). */
body.mini #view-player .pl-side{display:none}
/* JB 04.08.: im Mini ist die Playlist IMMER ein eigenes Fenster — der
   Eingliedern-Knopf würde sie in die (ausgeblendete) Seitenliste schieben. */
body.mini #plq-zurueck{display:none}
/* Mini-Player fuellt die Leiste (Build 97, JB: „warum so mini?") — die Karte
   bekam nie die Hoehe der Zone, das Video rendere in Naturgroesse klein in
   der Ecke; ohne Titel kollabierte die Box sogar auf 0 Breite. */
body.mini #view-player .card{flex-direction:row;height:100%}
body.mini .pl-media{min-height:0;height:100%;flex:1 1 auto;display:flex;align-items:center;justify-content:center}
body.mini .pl-media video,body.mini .pl-media audio{height:100%;max-height:100%;width:auto;max-width:100%}
body.mini .cmd-right{min-width:340px}
/* Drag&Drop-Ziel (Link ins Fenster ziehen) */
body.dragziel::after{content:"⬇ Link hier loslassen = Download";position:fixed;inset:8px;z-index:9000;
  border:3px dashed var(--akz);border-radius:16px;background:rgba(0,0,0,.35);color:var(--akz2);
  display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:700;pointer-events:none}
/* Hilfe-Legende */
.legbody{padding:12px 16px 18px;max-height:80vh;overflow:auto}
.legsec{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--akz);margin:12px 0 4px;font-weight:700}
.legsec:first-child{margin-top:0}
.legrow{font-size:12.5px;color:#cfc2b8;line-height:1.65;padding:2px 0}
.legrow b{color:var(--akz2);font-weight:600}
html.light .legrow{color:#4a3f38}
#layoutbar .btn{padding:5px 11px}
#canvas{position:relative;width:100%;flex:1;min-height:0;overflow:hidden;padding:2px 10px 8px}

/* ---- Panels (bewegliche Fenster) ---- */
.panel{position:absolute;background:var(--panel);border:1px solid var(--panelln);border-radius:12px;display:flex;
  flex-direction:column;overflow:hidden;box-shadow:0 6px 22px rgba(0,0,0,.42);min-width:190px;min-height:130px}
.panel.dragging{opacity:.93;box-shadow:0 14px 36px rgba(0,0,0,.6)}
.panel-head{display:flex;align-items:center;gap:6px;padding:6px 8px;background:#171310;
  border-bottom:1px solid var(--panelln);cursor:grab;touch-action:none;user-select:none}
.panel-head:active{cursor:grabbing}
.panel-tabs{display:flex;gap:4px;flex:1;min-width:0;overflow:hidden}
.ptab{padding:5px 12px;border-radius:8px;border:1px solid transparent;background:transparent;color:#a99a90;
  font:inherit;font-size:12.5px;cursor:pointer;white-space:nowrap;touch-action:none}
.ptab.an{background:var(--akzbg);border-color:#6b4a2a;color:var(--akz2);font-weight:600}
.ptab:hover{color:var(--akz)}
.panel-grip{color:#6a5c52;font-size:13px;padding:0 5px;cursor:grab;letter-spacing:-2px}
.panel-menu{flex:none;width:26px;height:22px;border-radius:6px;border:1px solid #3a332e;background:var(--panel);
  color:#a99a90;cursor:pointer;font-size:14px;line-height:1;padding:0}
.panel-menu:hover{border-color:var(--akz);color:var(--akz2)}
.panelmenu{position:fixed;z-index:6000;background:#211b16;border:1px solid #3a332e;border-radius:9px;
  padding:5px;min-width:190px;box-shadow:0 8px 26px rgba(0,0,0,.55);display:flex;flex-direction:column;gap:2px}
.panelmenu button{text-align:left;background:transparent;border:0;color:#d7c7bd;padding:6px 9px;border-radius:6px;
  cursor:pointer;font:inherit;font-size:12.5px}
.panelmenu button:hover{background:var(--akzbg);color:var(--akz2)}
.optrow{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:6px 8px;font-size:13px;color:#d7c7bd}
.optrow select{font:inherit;font-size:12px;background:#171310;border:1px solid #3a332e;border-radius:6px;color:#eee;padding:3px 6px}
html.light .optrow{color:#4a3f38}html.light .optrow select{background:#fbf8f4;border-color:#d9cfc4;color:#2a2320}
html.light .panel-menu{background:#fff;border-color:#d9cfc4;color:#7a6e64}
html.light .panelmenu{background:#fff;border-color:#e6ddd3;box-shadow:0 8px 26px rgba(120,90,60,.2)}
html.light .panelmenu button{color:#4a3f38}html.light .panelmenu button:hover{background:#f3e7d6;color:#8a5a1e}
.panel-body{flex:1;overflow:auto;padding:14px 16px;container-type:inline-size}
/* Loch-Fix (Build 84): die Bibliotheks-Werkzeugleiste ist sticky top:0 — mit
   Body-padding-top klebt sie UNTER dem Padding, gescrolltes Grid schaut im
   14px-Streifen darüber durch. Nur beim aktiven Bibliotheks-View das Top-Padding
   weg, dann sitzt die Leiste bündig am Kopf und deckt oben lückenlos ab. */
.panel-body:has(#view-lib){padding-top:0}
.panel-body .card{background:transparent;border:0;padding:0;margin:0 0 16px}
.panel-body .card:last-child{margin-bottom:0}
/* ✏-Layout-Modus (wie im Dashboard, JB 13.07.): Größen-Griffe an allen 8 Seiten/
   Ecken, aber NUR im Bearbeiten-Modus sichtbar — sonst verstellt man nichts aus
   Versehen. Im Modus bekommen die Fenster eine gestrichelte Kontur. */
.rgriff{position:absolute;z-index:12;display:none;touch-action:none}
body.layoutedit .rgriff{display:block}
.r-n{top:-3px;left:10px;right:10px;height:8px;cursor:n-resize}
.r-s{bottom:-3px;left:10px;right:10px;height:8px;cursor:s-resize}
.r-e{right:-3px;top:10px;bottom:10px;width:8px;cursor:e-resize}
.r-w{left:-3px;top:10px;bottom:10px;width:8px;cursor:w-resize}
.r-ne{top:-4px;right:-4px;width:14px;height:14px;cursor:ne-resize}
.r-nw{top:-4px;left:-4px;width:14px;height:14px;cursor:nw-resize}
.r-sw{bottom:-4px;left:-4px;width:14px;height:14px;cursor:sw-resize}
.r-se{bottom:-4px;right:-4px;width:16px;height:16px;cursor:se-resize}
.r-se::after{content:'';position:absolute;right:4px;bottom:4px;width:9px;height:9px;
  border-right:2px solid var(--akz);border-bottom:2px solid var(--akz);border-radius:0 0 4px 0}
/* Kontur INNEN (offset negativ): außenliegend sah sie bei exakt anliegenden
   Fenstern wie eine Mini-Überlappung aus (JB 14.07.) */
body.layoutedit .panel{outline:1px dashed var(--akz);outline-offset:-3px;
  transition:left .12s ease-out, top .12s ease-out}    /* Ausweichen wirkt weich */
body.layoutedit .panel.dragging{transition:none}       /* das gezogene folgt der Maus direkt */
/* Platzhalter beim Ziehen im ✏-Modus: zeigt fest die eingerastete Zielposition */
.platzhalter-fenster{position:absolute;z-index:9500;pointer-events:none;border-radius:12px;
  border:2px dashed var(--akz);background:rgba(201,149,43,.07)}
body.nosel, body.nosel *{user-select:none!important}  /* beim Ziehen keinen Text markieren */
/* Playlist als eigenes Fenster: große Liste, Seitenliste im Player verschwindet */
.plq-gross{flex:1;max-height:none;min-height:0}
/* Playlist abgespalten: der Player ist NUR noch Video — die komplette
   Seitenfläche verschwindet (JB 14.07.), Steuerung liegt auf dem Video. */
body.plq-extern #view-player .pl-side{display:none}
#plq-btn.an{border-color:var(--akz);color:var(--akz2)}
#layoutedit-btn.an{border-color:var(--akz);color:var(--akz2);background:var(--akzbg)}
/* Transluzente Tab-Vorschau beim Herausziehen (wie Browser-Tab-Drag) */
.tabghost{position:fixed;z-index:9999;width:230px;height:150px;pointer-events:none;opacity:.6;
  background:var(--panel);border:1px solid var(--akz);border-radius:12px;overflow:hidden;
  box-shadow:0 14px 40px rgba(0,0,0,.5)}
.tabghost-kopf{padding:6px 10px;font-size:12px;color:var(--akz2);border-bottom:1px solid var(--panelln);background:#171310}
.tabghost-body{padding:10px;font-size:11px;color:#8a7d74}
.dockpending{outline:2px dashed rgba(201,149,43,.55);outline-offset:-5px}
.dockhint{position:absolute;inset:0;background:rgba(201,149,43,.18);border:2px dashed var(--akz);border-radius:12px;
  display:flex;align-items:center;justify-content:center;color:var(--akz2);font-size:14px;font-weight:600;
  pointer-events:none;z-index:5;text-align:center;padding:12px}
.dockhint.ready{background:rgba(63,122,72,.24);border-color:#6fcf7f;border-style:solid;color:#9be0ab}

/* ---- Assistent-Modal ---- */
.modal{position:fixed;inset:0;z-index:5000;background:rgba(0,0,0,.55);display:flex;
  align-items:flex-start;justify-content:center;padding:30px 14px;overflow:auto}
.modal-box{background:var(--panel);border:1px solid var(--panelln);border-radius:14px;max-width:780px;width:100%;
  box-shadow:0 16px 50px rgba(0,0,0,.6)}
.modal-head{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 16px;
  border-bottom:1px solid var(--panelln);position:sticky;top:0;background:var(--panel);border-radius:14px 14px 0 0}
.modal-head b{color:var(--head);font-size:15px}
#geowiz-body{padding:14px 16px 20px}
.gcmp{width:100%;border-collapse:collapse;font-size:12px;margin:6px 0 12px}
.gcmp th,.gcmp td{border-bottom:1px solid var(--panelln);padding:6px 8px;text-align:left;vertical-align:top}
.gcmp th{color:#8a7d74;text-transform:uppercase;font-size:10px;letter-spacing:.03em}
.gcmp .ja{color:#6fcf7f}.gcmp .nein{color:#e08a6a}.gcmp .teils{color:#e6c34a}
.gsec{border:1px solid var(--panelln);border-radius:10px;margin:8px 0;overflow:hidden}
.gsec>summary{cursor:pointer;padding:9px 12px;font-weight:600;font-size:13px;list-style:none;
  display:flex;justify-content:space-between;gap:8px;align-items:center;background:#171310}
.gsec[open]>summary{border-bottom:1px solid var(--panelln)}
.gsec .ginner{padding:10px 12px;font-size:12.5px;color:#cfc2b8;line-height:1.6}
.gsec ol{margin:6px 0 6px 18px;padding:0}.gsec li{margin:3px 0}
.gstat{font-size:11px;padding:1px 8px;border-radius:999px;border:1px solid #3a332e;white-space:nowrap}
.gstat.ok{color:#6fcf7f;border-color:#2f5a34}.gstat.no{color:#8a7d74}
.gwg textarea{width:100%;min-height:90px;font-family:Consolas,monospace;font-size:11px}
.gzeile{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
.gtestrow{display:flex;justify-content:space-between;gap:10px;padding:4px 0;border-bottom:1px solid #241f1b;font-size:13px}
a.glink{color:var(--akz2);text-decoration:none;border-bottom:1px dotted #6b4a2a}a.glink:hover{color:var(--akz)}
html.light .modal-box,html.light .modal-head{background:#fff;border-color:#e6ddd3}
.eig-tab{width:100%;border-collapse:collapse;font-size:13px}
.eig-tab td{padding:5px 8px;border-bottom:1px solid var(--panelln);vertical-align:top}
.eig-tab td.k{opacity:.62;white-space:nowrap;width:36%}
.eig-tab td.v{word-break:break-word}
.eig-tab a{color:var(--akzent,#d65f5f)}
html.light .gsec,html.light .gsec>summary{background:#faf6f1;border-color:#e6ddd3}
html.light .gsec .ginner{color:#4a3f38}
html.light .gcmp th,html.light .gcmp td{border-color:#ece3d9}

.card{background:var(--panel);border:1px solid var(--panelln);border-radius:12px;padding:14px 16px;margin-bottom:14px}
.card h2{font-size:13px;margin:0 0 10px;color:var(--head);text-transform:uppercase;letter-spacing:.04em}
textarea{width:100%;min-height:64px;background:#171310;border:1px solid #3a332e;border-radius:8px;
  color:#eee;padding:8px 10px;font:inherit;font-size:13px;resize:vertical}
textarea:focus,input:focus,select:focus{outline:none;border-color:var(--akz)}
.zeile{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
select,input[type=text]{background:#171310;border:1px solid #3a332e;border-radius:8px;color:#eee;
  padding:6px 10px;font:inherit;font-size:13px}
.btn:disabled{opacity:.45;cursor:default}
.btn{padding:7px 14px;border-radius:8px;border:1px solid #3a332e;background:#171310;color:#eee;
  font:inherit;font-size:13px;cursor:pointer}
.btn:hover{border-color:var(--akz)}
.btn.haupt{border-color:#6b4a2a;background:var(--akzbg);color:var(--akz2);font-weight:600}
.btn.haupt:hover{border-color:var(--akz)}
.btn.mini{padding:3px 9px;font-size:12px;border-radius:7px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 2px}
.chip{padding:3px 11px;border-radius:999px;font-size:12px;border:1px solid #3a332e;background:#171310;color:#d7c7bd}
.chip b{font-weight:600}
.chip.laeuft b{color:#e6c34a}.chip.fertig b{color:#6fcf7f}.chip.fehler b{color:#e08a6a}
.eintrag{padding:10px 0;border-bottom:1px solid #241f1b}
.eintrag:last-child{border-bottom:0}
.kopf{display:flex;justify-content:space-between;gap:10px;align-items:baseline}
.titel{font-size:14px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.pill{flex:none;padding:1px 9px;border-radius:999px;font-size:11px;border:1px solid #3a332e;color:#9aa}
.pill.laeuft{color:#e6c34a;border-color:#5a4a2f}
.pill.fertig{color:#6fcf7f;border-color:#2f5a34}
.pill.fehler{color:#e08a6a;border-color:#6b3a2f}
.pill.pausiert{color:#f0a35e;border-color:#6b4a2a}
.pill.uebersprungen{color:#9ec49a;border-color:#3f5a44}
.balken{height:7px;background:#241f1b;border-radius:99px;margin:8px 0 6px;overflow:hidden}
.balken i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--head),var(--akz));transition:width .6s}
.balken.fertig i{background:#3f7a48}
.info{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:12px;color:#8a7d74}
.info .fehltext{color:#e08a6a;white-space:normal}
.aktionen{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.qtag{font-size:11px;color:var(--akz);border:1px solid #4a3f2a;border-radius:6px;padding:0 6px;flex:none}

/* ---- Warteschlange: eine Zeile pro Download, ausklappbar (Terminal-Look) ---- */
.qline{display:flex;align-items:center;gap:8px;font-family:Consolas,"Courier New",monospace;font-size:12.5px;
  padding:3px 5px;border-radius:5px;cursor:pointer;white-space:nowrap;overflow:hidden;border-bottom:1px solid #201b17}
.qline:hover{background:#171310}
.qtri{color:#6a5c52;width:11px;flex:none}
.qbar{color:#6fcf7f;letter-spacing:-1px;flex:none;font-size:11px}
.qline.laeuft .qbar{color:#e6c34a}
.qline.fehler .qbar,.qline.fehler .qrechts{color:#e08a6a}
.qline.wartend .qbar,.qline.pausiert .qbar{color:#8a7d74}
.qline.uebersprungen .qbar{color:#9ec49a}
.qline.laeuft .qrechts{color:#e6c34a}
.qtitel{overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0;color:#d7c7bd}
.qrechts{color:#8a7d74;flex:none;font-size:11px}
.qdetail{padding:4px 6px 9px 24px;font-size:12px;color:#8a7d74}
.qdinfo{margin-bottom:5px;white-space:normal;word-break:break-word}
.qdinfo .fehltext{color:#e08a6a}
.leer{color:#6a5c52;font-size:13px;text-align:center;padding:12px 0}
details.einst{margin-bottom:14px}
details.einst summary{cursor:pointer;color:#8a7d74;font-size:13px;user-select:none}
details.einst summary:hover{color:var(--akz)}
.einstgrid{display:grid;grid-template-columns:auto 1fr;gap:8px 12px;align-items:center;margin-top:10px;font-size:13px}
.hinweis{font-size:11.5px;color:#6a5c52;line-height:1.5;margin-top:10px}
.kopfzeile{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}
@media(max-width:560px){.titel{white-space:normal}}

/* ---- Bibliothek ---- */
/* Kopfzeile (Suche/Sortierung/Playlist-Leiste) beim Scrollen sichtbar halten (JB 14.07.):
   die zwei .libbar-Leisten stecken in .libhead, das im Fenster-Scroll (.panel-body) oben
   klebt — nur die Titelliste (#libinhalt) scrollt darunter weg. */
.libhead{position:sticky;top:0;z-index:30;background:var(--panel);padding-top:8px;margin-top:0}
.libbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
#libsuche{flex:1;min-width:130px}
.libbar .spacer{flex:1}
.chk{display:flex;align-items:center;gap:6px;font-size:12px;color:#8a7d74;cursor:pointer;white-space:nowrap}
.viewbtn{width:36px;height:33px;border-radius:8px;border:1px solid #3a332e;background:#171310;color:#d7c7bd;cursor:pointer;font-size:16px}
.tog{height:33px;padding:0 12px;border-radius:8px;border:1px solid #3a332e;background:#171310;color:#d7c7bd;cursor:pointer;font-size:13px}
.viewbtn.an,.tog.an{border-color:var(--akz);color:var(--akz2);background:var(--akzbg)}
.viewbtn:hover,.tog:hover{border-color:var(--akz)}
.tog:disabled{opacity:.6;cursor:default}
.kacheln{display:grid;grid-template-columns:repeat(auto-fill,minmax(208px,1fr));gap:14px}
.kacheln.kompakt{grid-template-columns:repeat(auto-fill,minmax(124px,1fr));gap:8px}
.kacheln.kompakt .kbody{padding:5px 7px;gap:4px}
.kacheln.kompakt .ktitel{font-size:11px}
.kacheln.kompakt .kinfo,.kacheln.kompakt .kakt{display:none}
.kacheln.kompakt .kdauer{font-size:10px;padding:0 4px}
.kachel{background:#171310;border:1px solid var(--panelln);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;position:relative}
.kachel.weg{opacity:.5;filter:grayscale(.65)}
.kachel.sel{outline:2px solid var(--akz);outline-offset:-1px}
.kachel.sel::before{content:'✓';position:absolute;left:6px;top:6px;z-index:3;width:20px;height:20px;
  border-radius:5px;background:var(--akz);color:#1a1512;font-size:13px;font-weight:700;
  display:flex;align-items:center;justify-content:center}
.thumbwrap{position:relative;aspect-ratio:16/9;background:#0e0c0a;cursor:pointer}
.thumbwrap::before{content:'▶';position:absolute;inset:0;z-index:2;display:flex;align-items:center;justify-content:center;
  color:#fff;font-size:26px;opacity:0;transition:opacity .12s;text-shadow:0 2px 8px rgba(0,0,0,.7);pointer-events:none}
.thumbwrap:hover::before{opacity:.92}
.thumb{width:100%;height:100%;object-fit:cover;display:block}
.thumbwrap.platzhalter::after{content:'▶';position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#3a332e;font-size:34px}
.kdauer{position:absolute;right:6px;bottom:6px;background:rgba(0,0,0,.8);color:#fff;font-size:11px;padding:1px 6px;border-radius:5px}
.wegbadge{position:absolute;left:6px;top:6px;background:rgba(0,0,0,.78);color:#f0a35e;font-size:11px;padding:1px 7px;border-radius:5px;border:1px solid #6b4a2a}
/* Build 144o: ✂-Abzeichen oben rechts auf einer Ausschnitt-Kachel (JB). */
.clip-schere{position:absolute;right:6px;top:6px;background:rgba(0,0,0,.8);color:var(--akz2);font-size:12px;line-height:1;padding:3px 5px;border-radius:6px;border:1px solid var(--akz)}
.clip-row .clip-schutz{cursor:default}
.kbody{padding:9px 10px;display:flex;flex-direction:column;gap:6px;flex:1}
.ktitel{font-size:13px;font-weight:600;line-height:1.32;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.kinfo{font-size:11.5px;color:#8a7d74;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:auto}
/* Build 116 (JB, „zu viele Knöpfe"): Kachel-Aktionen ruhen, bis die Maus
   auf der Kachel ist (oder sie den Tastatur-Fokus hat / ausgewählt ist).
   Gemessen: 78 Kacheln x 4 Knöpfe = 312 Knöpfe waren DAUERHAFT sichtbar —
   das ist der Kern der Überladung, nicht die Leisten. So machen es
   Spotify/Apple Music/YouTube Music auch. Der Platz bleibt reserviert
   (visibility statt display), damit nichts springt. Auf Touch-Geräten,
   die kein Hover kennen, bleiben sie sichtbar. */
/* Build 117 (JB-Fund): die Knöpfe verstecken, aber ihren Platz behalten,
   bringt NICHTS — es blieb ein leerer Block stehen. Jetzt liegen sie als
   Overlay ÜBER dem unteren Kachelrand (kein Platz im Fluss) und erscheinen
   beim Überfahren; die Kachel wird dadurch spürbar kompakter. */
.kachel{position:relative}
.kakt{display:flex;gap:4px;flex-wrap:wrap;align-items:center;
  position:absolute;left:0;right:0;bottom:0;padding:8px 10px;margin:0;
  background:linear-gradient(to top,rgba(0,0,0,.94),rgba(0,0,0,.8) 62%,rgba(0,0,0,0));
  visibility:hidden;opacity:0;transition:opacity .12s}
.kachel:hover .kakt,.kachel:focus-within .kakt,.kachel.sel .kakt{visibility:visible;opacity:1}
/* Touch kennt kein Überfahren: dort stehen sie wieder normal im Fluss. */
@media (hover:none){.kakt{position:static;background:none;padding:0;visibility:visible;opacity:1}}
/* Icon-Knöpfe (Spotify/iTunes-Stil): klein, ruhig, sprechend */
.ib{width:28px;height:26px;border-radius:7px;border:1px solid var(--panelln);background:#171310;color:#d7c7bd;
  cursor:pointer;font-size:13px;line-height:1;padding:0;display:inline-flex;align-items:center;justify-content:center;text-decoration:none}
.ib:hover{border-color:var(--akz);color:var(--akz2)}
.ib.play{color:#6fcf7f;border-color:#2f5a34}.ib.play:hover{color:#8fe0a0}
html.light .ib{background:#fbf8f4;border-color:#e0d7cc;color:#5a4f47}
html.light .ib:hover{border-color:var(--akz);color:#8a5a1e}
.lakt{display:flex;gap:4px;justify-content:flex-end}
/* Aufklapp-Menü „⋯" am Bibliotheks-Eintrag */
.itemmenu{position:fixed;z-index:9000;min-width:210px;background:#1c1712;border:1px solid #3a332e;border-radius:10px;
  padding:5px;box-shadow:0 10px 30px rgba(0,0,0,.55);display:flex;flex-direction:column;gap:2px}
.itemmenu button{text-align:left;background:none;border:0;color:#e7dccf;font-size:12.5px;padding:7px 10px;border-radius:7px;cursor:pointer;white-space:nowrap}
.itemmenu button:hover{background:#2a2118;color:var(--akz2)}
html.light .itemmenu{background:#fffdfa;border-color:#e0d7cc;box-shadow:0 10px 30px rgba(0,0,0,.15)}
html.light .itemmenu button{color:#4a3f37}
html.light .itemmenu button:hover{background:#f3ebdf;color:#8a5a1e}
/* Build 144k: Ausschnitt-Untermenü — je Zeile Favorit-Stern, Titel, Papierkorb. */
.clip-sub{max-height:min(60vh,340px);overflow:auto}
.clip-row{display:flex;align-items:center;gap:2px}
.clip-row .clip-play{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.clip-row .clip-fav,.clip-row .clip-del{flex:none;padding:7px 8px}
.clip-row .clip-fav.an{color:var(--akz2)}
.clip-meta{color:#8a7d74;font-size:11px;margin-left:4px}
.km-leer{color:#8a7d74;font-size:12px;padding:7px 10px}
/* Abos */
.abo-liste{display:flex;flex-direction:column;gap:8px;margin-top:8px}
.abo-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#d7c7bd;font-weight:600}
.abo-meta{color:#8a7d74;font-size:11px;flex:none}
/* Abo-Karte (Sonarr-Muster: Quelle + Episodenliste mit Lade-Status) */
.abo-card{border:1px solid #241f1b;border-radius:10px;padding:8px 10px}
.abo-kopf{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.abo-qsel{font-size:12px}
.abo-regeln{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px;padding-top:8px;
  border-top:1px dashed #241f1b;font-size:12px;color:#b7a89e}
.abo-regeln label{display:flex;gap:4px;align-items:center;white-space:nowrap}
.abo-regeln input[type=text]{width:130px}
.abo-fkopf{display:flex;gap:6px;align-items:center;margin-top:8px;flex-wrap:wrap}
.abo-fkopf input[type=text]{flex:1;min-width:110px}
.abo-fliste{max-height:420px;overflow:auto;margin-top:6px;display:flex;flex-direction:column;gap:1px}
.abo-f{display:flex;gap:8px;align-items:center;padding:3px 6px;border-radius:6px;cursor:pointer;font-size:12.5px;flex:none;user-select:none}
.abo-f:hover{background:#241f1b}
.abo-f.fehlt{opacity:.45}                      /* verfügbar, aber noch nicht geladen -> ausgegraut (JB) */
.abo-f.sel{background:#2e2620;outline:1px solid var(--akz)}
/* Backkatalog-Flyout (Build 93, JB): eigenes grosses Fenster AM 📜-Knopf statt
   Inline-Ausklappen in der engen Box — schwebend + fixiert (Anti-Scroll), wird
   IMMER in den Viewport geklemmt, nur die Folgen-Liste scrollt innen.
   Build 95 (JB-Griff 2): schmaler Scrollbalken mit Abstand zur Zeit-Spalte +
   hauchduenne Trennlinien zwischen den Zeilen. */
.abo-flyout .abo-fliste{padding-right:10px}
.abo-flyout .abo-fliste::-webkit-scrollbar{width:6px}
.abo-flyout .abo-fliste::-webkit-scrollbar-thumb{background:var(--panelln);border-radius:3px}
.abo-flyout .abo-f{border-bottom:1px solid rgba(255,255,255,.045);border-radius:0}
.abo-flyout .abo-f:last-child{border-bottom:none}
html.light .abo-flyout .abo-f{border-bottom-color:rgba(0,0,0,.055)}
.abo-flyout{position:fixed;z-index:900;background:var(--panel);border:1px solid var(--panelln);
  border-radius:12px;box-shadow:0 14px 42px rgba(0,0,0,.55);display:flex;flex-direction:column;
  padding:10px 12px;min-width:340px}
.abo-flyout .abo-fkopf{position:sticky;top:0}
.abo-flyout .abo-folgen{flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
.abo-flyout .abo-fliste{flex:1 1 auto;min-height:0;max-height:none;overflow:auto;position:relative;user-select:none}
.abo-fly-titel{display:flex;gap:8px;align-items:center;margin-bottom:6px;font-weight:600;color:#d7c7bd}
.abo-fly-titel .spacer{flex:1}
.abo-staffel{display:flex;gap:4px;align-items:center;flex-wrap:wrap;margin:4px 0 6px;font-size:12px;color:#8a7d74}
.abo-staffel .btn.mini{padding:2px 8px}
/* Auswahl-Leiste (Build 103, JB: „wo lad ich die Markierten runter?") —
   erscheint UNTEN im Backkatalog-Fenster, sobald etwas markiert ist
   (gleiches Muster wie die Sammel-Leiste der Bibliothek). */
.abo-selbar{display:flex;gap:8px;align-items:center;margin-top:6px;padding:7px 10px;
  background:var(--akzbg);border:1px solid var(--akz);border-radius:9px;
  font-size:12.5px;color:var(--akz2);flex:none}
.abo-selbar b{color:#e9ded3}
.abo-band{position:fixed;z-index:901;border:1px solid var(--akz);background:rgba(201,149,43,.14);
  border-radius:3px;pointer-events:none}
/* ✂-Schneide-Leiste (Build 101, JB): zwei ZIEHBARE Griffe statt Eingabefelder;
   Ziehen springt den Player live an die Stelle, die Wiedergabe endet an B. */
.schnitt-spur{position:relative;height:30px;background:var(--panelln);border-radius:8px;
  margin:10px 4px 4px;cursor:pointer;user-select:none;touch-action:none}
.schnitt-bereich{position:absolute;top:0;bottom:0;background:rgba(201,149,43,.30);
  border:1px solid var(--akz);border-radius:8px;pointer-events:none}
.schnitt-griff{position:absolute;top:-4px;width:18px;height:38px;margin-left:-9px;
  background:var(--akz);border-radius:9px;cursor:ew-resize;box-shadow:0 2px 8px rgba(0,0,0,.4);
  display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#1c1814}
.schnitt-griff:hover{transform:scaleY(1.06)}
.schnitt-zeiten{display:flex;justify-content:space-between;font-size:12px;color:var(--akz2);
  padding:2px 6px 0}
html.light .schnitt-spur{background:#e3d8cc}
/* Wiedergabe-Merker (Build 102, JB): gelber Strich = „hier war ich zuletzt";
   Klick springt hin — der Titel startet aber IMMER normal bei 0. */
.pl-barseek{position:relative}
.plb-merker{position:absolute;top:50%;width:3px;height:16px;transform:translate(-50%,-50%);
  background:var(--akz);border-radius:2px;cursor:pointer;z-index:3;box-shadow:0 1px 4px rgba(0,0,0,.5)}
.plb-merker:hover{transform:translate(-50%,-50%) scaleY(1.3)}
html.light .abo-flyout{background:#faf5ec;border-color:#e3d8cc;box-shadow:0 14px 42px rgba(90,70,40,.25)}
.abo-ft{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.abo-fd{color:#8a7d74;font-size:11px;flex:none}
.abo-nr{color:#8a7d74;font-size:11px;flex:none;min-width:34px;text-align:right;font-variant-numeric:tabular-nums}
.pl-nr{color:var(--akz2);font-size:11px;font-variant-numeric:tabular-nums}
#toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(12px);z-index:9500;
  background:#241f1b;color:#f0e6dc;padding:9px 16px;border-radius:10px;font-size:13px;box-shadow:0 6px 24px rgba(0,0,0,.5);
  opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;max-width:80vw}
#toast.an{opacity:1;transform:translateX(-50%) translateY(0)}
html.light #toast{background:#3a322c}
/* Build 142: Bei mehreren Titeln sieht der Anfasser wie ein STAPEL aus —
   dieselbe Bildsprache wie im Explorer, damit sofort klar ist, dass
   mehr als einer mitreist. */
.ziehghost.stapel{box-shadow:3px 3px 0 -1px var(--panel),3px 3px 0 0 var(--akz),
  6px 6px 0 -1px var(--panel),6px 6px 0 0 var(--akz);font-weight:600}
.ziehghost{position:fixed;top:-999px;left:-999px;pointer-events:none;z-index:9999;
  background:#241f1b;color:#f0e6dc;padding:5px 10px;border-radius:8px;font-size:12.5px;
  max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;box-shadow:0 4px 14px rgba(0,0,0,.5)}
html.light .ziehghost{background:#3a322c}
/* Transkript-Volltextsuche: Ergebnis-Overlay */
#tsuche-ov{position:fixed;inset:0;z-index:9400;background:rgba(0,0,0,.55);display:none;align-items:flex-start;justify-content:center}
#tsuche-ov.an{display:flex}
.tsuche-box{background:var(--panel);margin-top:6vh;width:min(720px,94vw);max-height:84vh;overflow:auto;
  border-radius:14px;box-shadow:0 12px 48px rgba(0,0,0,.6);padding:0}
.tsuche-kopf{position:sticky;top:0;background:var(--panel);display:flex;gap:8px;align-items:center;
  padding:14px 16px;border-bottom:1px solid #241f1b}
.tsuche-kopf input{flex:1}
.tsuche-body{padding:8px 12px 16px}
.tsuche-treffer{margin:10px 0;border-left:2px solid var(--akz);padding-left:10px}
.tsuche-t-titel{font-weight:600;font-size:13.5px;margin-bottom:3px}
.tsuche-z{display:block;width:100%;text-align:left;background:none;border:0;color:var(--txt);
  font-size:12.5px;padding:3px 4px;border-radius:6px;cursor:pointer}
.tsuche-z:hover{background:#241f1b}
.tsuche-z .zt{color:var(--akz2);font-variant-numeric:tabular-nums;margin-right:8px}
.tsuche-z mark{background:rgba(230,160,70,.35);color:inherit;border-radius:3px}
html.light .tsuche-z:hover{background:#efe7de}
.abo-b{font-size:10.5px;border-radius:5px;padding:1px 5px;flex:none}
.abo-b.ok{background:#1d3020;color:#9ec49a}
.abo-b.anders{background:#3a2a16;color:#e8b45a}   /* in ANDEREM Format geladen (JB: Markierung) */
html.light .abo-card{border-color:#e3d8cc}
html.light .abo-regeln{border-color:#e3d8cc}
html.light .abo-f:hover{background:#efe7de}
html.light .abo-f.sel{background:#f3e2c8}
/* Smart-Playlists-Popover */
.sm-titel{font-size:11px;color:#8a7d74;padding:2px 6px 6px;text-transform:uppercase;letter-spacing:.03em}
.sm-row{display:flex;align-items:center;gap:6px;padding:2px 4px}
.sm-play{flex:1;text-align:left;background:none;border:0;color:#e7dccf;cursor:pointer;font:inherit;font-size:12.5px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:3px 4px;border-radius:6px}
.sm-play:hover{background:var(--akzbg);color:var(--akz2)}
.sm-cnt{color:#8a7d74;font-size:11px;flex:none}
.sm-leer{color:#6a5c52;font-size:12px;padding:3px 6px}
.sm-sep{height:1px;background:var(--panelln);margin:6px 0}
.sm-form{padding:2px 4px}
.sm-name{width:100%;background:#0e0c0a;border:1px solid var(--panelln);border-radius:6px;color:#e7dccf;padding:5px 8px;font:inherit;font-size:12px;margin-bottom:6px}
.sm-grid{display:grid;grid-template-columns:auto 1fr;gap:5px 8px;align-items:center;font-size:12px;color:#9a8d84;margin-bottom:7px}
.sm-sel,.sm-num{background:#0e0c0a;border:1px solid var(--panelln);border-radius:6px;color:#d7c7bd;padding:3px 6px;font:inherit;font-size:12px}
html.light .sm-name,html.light .sm-sel,html.light .sm-num{background:#f7f3ee;border-color:#e0d7cc;color:#4a3f37}
/* Dublettenfinder */
.dub-grp{border:1px solid var(--panelln);border-radius:8px;padding:6px 8px;margin:5px 4px}
.dub-kopf{font-size:12px;color:#d7c7bd;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-bottom:3px}
.dub-typ{color:#8a7d74;font-size:10px}
.dub-item{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:2px 0}
.dub-q{font-size:11px;color:#9a8d84}
/* Equalizer-Popover */
/* Jede EQ-Spalte: dB-Wert oben, Regler mittig, Frequenz DIREKT darunter —
   feste Spaltenbreite, damit Beschriftung und Regler exakt fluchten (JB 13.07.) */
.eq-row{display:flex;gap:6px;justify-content:center;padding:8px 4px}
.eq-band{display:flex;flex-direction:column;align-items:center;gap:4px;width:42px;flex:none}
.eq-sl{-webkit-appearance:slider-vertical;appearance:slider-vertical;writing-mode:vertical-lr;direction:rtl;width:22px;height:92px;accent-color:var(--akz);margin:0}
.eq-val{font-size:10px;color:#9a8d84;min-height:12px}
.eq-lab{font-size:10.5px;color:#c9bcae;white-space:nowrap}
.eq-presets{display:flex;gap:4px;flex-wrap:wrap;padding:4px;justify-content:center}
/* Log-Ansicht */
.logliste{display:flex;flex-direction:column;gap:1px;font-family:Consolas,"Courier New",monospace;font-size:12px}
.logrow{display:flex;gap:8px;padding:2px 0;border-bottom:1px solid #201b17}
.logt{color:#6a5c52;flex:none}
.logx{color:#d7c7bd;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.logrow.fertig .logx{color:#9ec49a}.logrow.fehler .logx{color:#e08a6a}.logrow.laeuft .logx{color:#e6c34a}
html.light .logrow{border-color:#ece3d9}html.light .logt{color:#a89a8e}html.light .logx{color:#5a4f47}
/* Equalizer-Norm + Kapitel */
.eq-norm{display:flex;align-items:center;gap:7px;font-size:12px;color:#c9bcae;padding:5px 6px 2px}
.pl-kapitel{max-height:150px;overflow-y:auto;margin-top:6px;border-top:1px solid #241f1b;padding-top:4px}
.kap-titel{font-size:11px;color:#8a7d74;text-transform:uppercase;letter-spacing:.03em;padding:2px 4px}
.kap{font-size:12px;color:#d7c7bd;padding:4px 6px;border-radius:6px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kap:hover{background:var(--akzbg);color:var(--akz2)}
.kap-z{color:#8a7d74;font-family:Consolas,monospace;font-size:11px;margin-right:6px}
html.light .kap:hover{color:#8a5a1e}html.light .pl-kapitel{border-color:#ece3d9}
/* Untertitel-Overlay (Zeile) + Karaoke + Transkript */
.pl-subzeile{position:absolute;left:6%;right:6%;bottom:58px;z-index:3;text-align:center;pointer-events:none}
/* Untertitel-Look (JB 05.08., Disney-Muster): ALLE Optionen als CSS-Variablen
   — Größe (--sub-skala, auch Karaoke/TV), Schrift, Textfarbe+Deckkraft,
   Hintergrund, Schatten. Gesetzt von subLookAuf(); Karaoke behält seine
   Wischer-Farben. */
.pl-subzeile .subtxt{display:inline-block;background:var(--sub-hg,rgba(0,0,0,.68));
  color:var(--sub-farbe,#fff);padding:4px 12px;border-radius:8px;
  font-size:calc(15px*var(--sub-skala,1));line-height:1.4;
  font-family:var(--sub-schrift,inherit);text-shadow:var(--sub-schatten,none)}
/* Schriftart wirkt auch im Karaoke (JB 05.08.) — die Farben dort gehören
   weiter dem Wischer. */
.pl-subzeile .kar-akt,.pl-subzeile .kar-neben{font-family:var(--sub-schrift,inherit)}
.pl-subzeile.karaoke{top:6%;bottom:58px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px}
.kar-neben{color:rgba(255,255,255,.45);font-size:calc(15px*var(--sub-skala,1));max-width:92%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kar-akt{color:var(--akz2);font-size:calc(23px*var(--sub-skala,1));font-weight:700;text-align:center;max-width:94%;line-height:1.3}
/* Karaoke-Mitleuchten (nur LRCLIB): schon gesungene Wörter hell/akzentuiert,
   kommende gedimmt — der Fortschritt „läuft" durch die Zeile (JB 21.07.). */
/* Build 115 (JB): echte Karaoke-Maschine — die Farbe LÄUFT durch das Wort
   (Wischer von links nach rechts), statt Wörter hart umzuschalten. Technik:
   Farbverlauf als Text-Füllung, Kante über --p (0…1) gesteuert. --p wird je
   Bild neu gesetzt, darum hier KEINE transition (die würde nachhinken). */
.kar-akt.lrc .kw{
  --p:0;
  background-image:linear-gradient(90deg,var(--akz2) 0%,var(--akz2) calc(var(--p)*100%),
                   rgba(255,255,255,.38) calc(var(--p)*100%),rgba(255,255,255,.38) 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  -webkit-text-fill-color:transparent;
  text-shadow:none}                                  /* Rand würde die Füllung überdecken */
.kar-akt.lrc .kw.aktiv{filter:drop-shadow(0 0 9px var(--akz))}   /* Wort, das gerade dran ist */
.kar-akt.lrc{text-shadow:none}
html.light .kar-akt.lrc .kw{
  background-image:linear-gradient(90deg,var(--akz2) 0%,var(--akz2) calc(var(--p)*100%),
                   rgba(0,0,0,.35) calc(var(--p)*100%),rgba(0,0,0,.35) 100%)}
/* Schwarzer Buchstaben-Rand: Untertitel/Karaoke auf JEDER Fläche lesbar (JB-Wunsch) */
.subtxt,.kar-akt,.kar-neben{
  text-shadow:-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000,
              -1px 0 0 #000, 1px 0 0 #000, 0 -1px 0 #000, 0 1px 0 #000, 0 2px 8px rgba(0,0,0,.85)}
.pl-lyrics{max-height:190px;overflow-y:auto;margin-top:6px;border-top:1px solid #241f1b;padding-top:4px}
.lyr{font-size:12px;color:#9a8d84;padding:3px 6px;border-radius:6px;cursor:pointer}
.lyr:hover{background:var(--akzbg)}
.lyr.akt{color:var(--akz2);background:var(--akzbg)}
html.light .lyr{color:#7a6e64}html.light .pl-lyrics{border-color:#ece3d9}
/* Canvas: langsam zoomendes, weichgezeichnetes Cover als lebender Hintergrund */
.pl-canvas{position:absolute;inset:-12%;z-index:0;background-size:cover;background-position:center;
  filter:blur(20px) brightness(.5) saturate(1.2);animation:plCanvas 26s ease-in-out infinite alternate;pointer-events:none}
@keyframes plCanvas{from{transform:scale(1) translate(0,0)}to{transform:scale(1.16) translate(2%,-2%)}}
/* Alben-Ansicht */
.albgrp{margin-bottom:18px}
.albkopf{display:flex;align-items:center;gap:9px;padding:6px 2px;margin-bottom:9px;border-bottom:1px solid var(--panelln)}
.albtitel{font-weight:700;font-size:13.5px;color:var(--akz2)}
.albku{font-size:12px;color:#d7c7bd}
.albn{font-size:11px;color:#8a7d74;margin-left:auto;white-space:nowrap}
html.light .albku{color:#5a4f47}
.libwrap{overflow-x:auto}
.libtab{width:100%;border-collapse:collapse;font-size:13px}
.libtab th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:#8a7d74;padding:7px 8px;border-bottom:1px solid var(--panelln);white-space:nowrap}
.libtab td{padding:6px 8px;border-bottom:1px solid #241f1b;vertical-align:middle}
.libtab tr.weg td{opacity:.5}
.ltitel{display:flex;align-items:center;gap:9px;min-width:0;max-width:340px}
.lthumb{width:52px;height:30px;object-fit:cover;border-radius:4px;flex:none;background:#0e0c0a}
.ltxt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.libtab td.num{white-space:nowrap;color:#b7a99e}
.lstatus.ok{color:#6fcf7f}.lstatus.weg2{color:#f0a35e}
.libtab tr.sel td{background:var(--akzbg)}
.libtab tr{cursor:default}
.libtab.kompakt td{padding:2px 6px;font-size:11px}
.libtab.kompakt .lthumb{width:32px;height:19px}
.libtab.kompakt .ltitel{max-width:230px;gap:6px}
.libleer{color:#6a5c52;text-align:center;padding:26px 0;font-size:13px}
.plbar{margin-top:-4px}
.libbulk{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:12px;padding:7px 10px;
  border:1px solid #6b4a2a;background:#241b12;border-radius:9px;font-size:12px;color:var(--akz2)}
#layoutbar .spacer{flex:1}
#buildmark{font-size:11px;color:#5a4f47;font-family:Consolas,monospace}
html.light .libbulk{background:#f6ecdd;border-color:#d8b98a;color:#8a5a1e}
html.light .libtab tr.sel td{background:#f3e7d6}
html.light #buildmark{color:#a89a8e}
.th-sort{cursor:pointer;user-select:none;white-space:nowrap}
.th-sort:hover{color:var(--akz)}.th-sort.akt{color:var(--akz)}

/* ---- Spalten-Menü ---- */
.colmenuwrap{position:relative}
/* Build 125 (JB-Wunsch): „⚙ Ansicht" rechtsbündig. margin-left:auto schiebt
   den Knopf ans rechte Ende SEINER Zeile — auch wenn die Leiste umbricht. */
.libbar .colmenuwrap{margin-left:auto}
/* Build 125 — WURZEL des Dauerfehlers „Ansicht liegt hinter den Panels":
   Build 124 hatte die Ebene auf 6100 gehoben, und der Treffer-Test schlug
   TROTZDEM fehl. Gemessen am 23.07.: Das Menü hing als Kind in .libbar, und
   .libbar trägt seit Build 122 `container-type:inline-size` für die schmalen
   Leisten. Containment macht das Element zum eigenen Stapel-Kontext — ein
   z-index darin wird NUR gegen Geschwister im selben Kasten verglichen, und
   der ganze Kasten steckt im Bibliotheks-Panel mit z-index 14. Gegen ein
   Panel mit z-index 35 oder 62 hilft deshalb keine noch so hohe Zahl; sogar
   `position:fixed` wäre in den Kasten eingesperrt gewesen.
   Lösung ist nicht eine größere Zahl, sondern der richtige Ort: die Menüs
   hängen jetzt beim Öffnen am <body> (menuAnBody) und werden per
   popoverBei() an ihrem Knopf ausgerichtet — genau wie .panelmenu und
   .itemmenu es längst tun. Der Wächter-Test test_schwebende_flaechen_
   nicht_im_kaefig hält die Regel für alle künftigen Flächen fest. */
.colmenu{position:fixed;z-index:6100;background:#211b16;border:1px solid #3a332e;
  border-radius:10px;padding:9px 10px;min-width:220px;box-shadow:0 8px 24px rgba(0,0,0,.5)}
.colmenu-titel{font-size:11px;color:#8a7d74;margin-bottom:7px;line-height:1.4}
.colrow{display:flex;align-items:center;gap:5px;padding:2px 0;font-size:13px}
/* ⚙ Ansicht-Menü (konsolidierte Bibliotheks-Werkzeuge) */
#libansicht{min-width:238px}
.mzeile{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:4px 6px;font-size:12.5px;color:#d7c7bd}
.mbtn{display:block;width:100%;text-align:left;background:none;border:0;color:#e7dccf;font-size:12.5px;
  padding:6px 8px;border-radius:6px;cursor:pointer;font-family:inherit}
.mbtn:hover{background:var(--akzbg);color:var(--akz2)}
.mbtn.an{background:var(--akzbg);color:var(--akz2)}
.msep{height:1px;background:var(--panelln);margin:5px 0}
html.light .mbtn{color:#4a3f37}html.light .mzeile{color:#5a4f47}
.colmv{width:22px;height:22px;border-radius:5px;border:1px solid #3a332e;background:#171310;color:#d7c7bd;
  cursor:pointer;font-size:9px;line-height:1;flex:none}
.colmv:disabled{opacity:.35;cursor:default}
.colrow label{display:flex;align-items:center;gap:6px;cursor:pointer;flex:1;color:#d7c7bd}

/* ---- Player ---- */
#view-player{height:100%}
#view-player .card{display:flex;flex-direction:column;height:100%;gap:8px;
  container-type:size;container-name:plcard}
.pl-media{flex:1;background:#0e0c0a;border-radius:10px;min-height:72px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;overflow:hidden;gap:8px;padding:8px}
/* Build 130 (JB ausdrücklich): „16:9 FEST — echtes Maß je Video = Nogo, das
   Bild darf nicht springen." Das Bildfeld hängt deshalb an einem festen
   Seitenverhältnis und NICHT an den Maßen des jeweiligen Videos; ein 4:3-Clip
   bekommt seitliche Balken (object-fit:contain), statt den Rahmen zu
   verformen und beim Titelwechsel alles verrutschen zu lassen.
   Das Verhältnis steckt in --pl-ar und ist umschaltbar (Layout-Option);
   16/9 ist der Standard. max-height hält das Bild im verfügbaren Raum,
   margin:auto zentriert es darin. */
/* max-height in cqb statt Prozent: der Rahmen hat height:auto, und ein
   Prozentwert gegen eine automatische Elternhöhe ist unbestimmt — er wurde
   ignoriert, das Bild lief in sehr flachen Karten unten heraus (gemessen:
   618 px Bild in 260 px Karte). cqb misst gegen die KARTE, die eine feste
   Höhe hat (container-type:size liegt dort). */
.pl-media video{width:100%;height:auto;aspect-ratio:var(--pl-ar,16/9);max-height:100cqb;margin:auto;
  border-radius:8px;background:#000;object-fit:contain}
/* „Natürlich" gibt das feste Maß bewusst auf — für den seltenen Fall, dass
   jemand ein Hochkant-Video formatfüllend sehen will. */
.pl-media.ar-frei video{aspect-ratio:auto;height:100%}
.pl-media audio{width:100%;flex:none;position:relative;z-index:2}
/* Visualizer: Canvas als animierter Hintergrund hinter dem Cover, Audio-Leiste oben drüber */
.pl-media{position:relative;container-type:inline-size;container-name:plmedia}
/* Player-Rahmen: festes Seitenverhältnis, obenbündig (Builds 132/136/138)
   JB-Weg dahin, damit es niemand wieder aufweicht:
   132 „ist das 16:9?" — nein: das Maß hing nur am <video>, der schwarze
       Rahmen drumherum war frei und liess oben/unten tote Streifen stehen.
   136 „das Bild sollte oben angesetzt sein" — margin:0 auto statt auto und
       align-self:flex-start; vorher stand über dem Bild derselbe Leerraum
       wie darunter und die Playlist rutschte ans Kartenende.
   138 „jetzt ist der Player nicht mehr 16:9" — bei einem AUDIO-Titel gibt es
       gar kein <video>, nur ein quadratisches Cover; der Kasten wuchs damit
       über die volle Panel-Höhe. Jetzt trägt der RAHMEN das Verhältnis.
   Zwei gemessene Fallen: eine feste Höhe schlägt aspect-ratio (mit
   height:100% blieb der Rahmen 700x900), und in einer ZEILEN-Karte streckt
   align-items den Rahmen, solange align-self fehlt.
   `width:100%` + `height:auto` lässt die Breite die Höhe bestimmen;
   `max-height:100cqb` misst gegen die Karte (container-type:size liegt dort)
   und fängt sehr flache Panels ab. JB ausdrücklich: „wenn der Player kleiner
   wird bleibt halt darunter ein grosses Loch" — das Loch ist gewollt.
   body:not(.mini):not(.embed) grenzt Mini-Player und Einbett-Modus aus, die
   ihre eigenen, bewusst anderen Höhenketten haben (Build 97/121). */
/* Build 144p (JB 25.07., Bild 1 vs. 2): Im eigenständigen Player muss das
   16:9-Bild OHNE Scrollen in den Viewport passen und Titel + Playlist sichtbar
   lassen. Vorher stand das Video auf `flex:0 0 auto` mit `max-height:100cqb` —
   bei einem breiten Panel nahm es die volle Kartenhöhe (width:100% → hohe
   16:9-Höhe) und drückte die Playlist aus dem Bild (Scroll, Bild 2).
   Jetzt darf es SCHRUMPFEN (`flex:0 1 auto`): reicht die Höhe nicht, wird das
   Bild flacher UND schmaler — das <video> behält sein 16:9 (object-fit:contain)
   und bekommt seitliche Balken (Pillarbox, Bild 1). Die Playlist-Seite ist
   `flex:none` (Zeile ~915), behält also ihren Platz. JBs gewolltes „Loch"
   unter einem kleinen Player bleibt: passt das 16:9 hinein, schrumpft nichts.
   Live gemessen: kein Scroll bei 1858×700 / 1100×760 / 560×820. */
body:not(.mini):not(.embed) #view-player .card .pl-media{
  flex:0 1 auto;aspect-ratio:var(--pl-ar,16/9);width:100%;height:auto;
  min-height:120px;margin:0 auto;align-self:flex-start}
body:not(.mini):not(.embed) #view-player .card .pl-media.ar-frei{
  height:100%;flex:1;align-self:stretch}
.pl-viz{position:absolute;inset:0;width:100%;height:100%;z-index:0;display:none}
.pl-media.viz-an .pl-viz{display:block}
.pl-vizwrap{position:relative;z-index:1;flex:1;display:flex;align-items:center;justify-content:center;min-height:0;overflow:hidden}
.pl-cover{max-width:96%;max-height:100%;border-radius:10px;object-fit:contain}
/* Gerät „VLC" (Etappe B, JB 05.08.: „identisch aussehen"): die VLC-Ansicht
   nutzt dieselben Bausteine wie die Audio-Ansicht (pl-vizwrap + pl-bar) —
   eigenes CSS braucht nur noch der leuchtende Geräte-Knopf. */
#pl-geraet.an{color:var(--akz2);border-color:var(--akz2)}
/* Untertitel-Panel (JB 05.08., Netflix-Bild): Zeilen klar getrennt, Knöpfe
   rechtsbündig; die Aa-Knöpfe zeigen ihre Wahl im EIGENEN Look. */
#subfly .subm-zeile{display:flex;align-items:center;justify-content:space-between;gap:10px;
  padding:8px 6px;border-bottom:1px solid rgba(255,255,255,.09)}
#subfly .subm-zeile:last-child{border-bottom:none}
#subfly .subm-knoepfe{display:flex;gap:4px;flex-wrap:wrap;align-items:center;justify-content:flex-end}
#subfly .btn.an{outline:2px solid var(--akz2);outline-offset:1px}
.pl-side{display:flex;flex-direction:column;flex:none;min-height:0;min-width:0}
/* Build 144f (JB mit Bild): „jetzt ist playlist nur noch ein kleines fenster,
   das sollte dynamisch bis zum unteren rand von playlist gehen."
   ERLEDIGT fuer das herausgeloeste Playlist-FENSTER (Regel unten). Fuer die
   Playlist IM Player steht es bewusst NOCH OFFEN: vier CSS-Wege sind daran
   gescheitert, jeder live gemessen (Zahlen in NAECHSTER_PROMPT.md).
   Kurzfassung: im vertikalen Layout konkurrieren ein 16:9-Video mit fester
   Hoehe und die Liste um dieselbe Hoehe. Wer der Liste Platz gibt, nimmt ihn
   dem Video; `aspect-ratio` vertraegt sich schlecht mit `flex-shrink`, und
   jeder Versuch kippte entweder das Seitenverhaeltnis, liess das Video auf
   128x72 px kollabieren oder die Liste aus der Karte laufen.
   Im HORIZONTALEN Layout ist es laengst richtig (gemessen: Liste 354 px,
   fuellt die Spalte, kein Scrollen) — genau das belegt, dass die Aufteilung
   einen echten Mechanismus braucht (ziehbarer Trenner oder gemerkte
   Aufteilung), keine weitere CSS-Heuristik. */
/* Das herausgelöste Playlist-Fenster: seine Karte trägt height:100%, aber
   `#view-plq` selbst hatte keine Höhe — 100 % von auto ist auto, deshalb war
   die Karte nur inhaltshoch (gemessen 132 px in einem 420 px hohen Panel). */
#view-plq{height:100%;min-height:0;display:flex;flex-direction:column}
#view-plq>.card{flex:1 1 auto;min-height:0}
/* Und die Liste füllt die Karte. `.plq-gross` (Zeile ~399) will das längst,
   verliert aber gegen `.pl-queue{max-height:150px}` — gleiche Spezifität, und
   die spätere Regel gewinnt. Die Id hebt das auf; dieselbe Falle ist beim
   Zu-klein-Verhalten weiter unten schon einmal dokumentiert. */
#view-plq>.card>.pl-queue{flex:1 1 auto;max-height:none;min-height:0}
/* HORIZONTAL: Video links, Titel/Steuerung/Playlist rechts */
#view-player .card.pl-horizontal{flex-direction:row}
.card.pl-horizontal .pl-media{height:100%}
.card.pl-horizontal .pl-side{width:200px;flex:none;height:100%}
.card.pl-horizontal .pl-side .pl-queue{flex:1;max-height:none}
/* erst wenn WIRKLICH zu schmal fürs Horizontale -> zurück auf vertikal */
@container (max-width:330px){
  #view-player .card.pl-horizontal{flex-direction:column}
  .card.pl-horizontal .pl-media{height:auto}
  .card.pl-horizontal .pl-side{width:auto;height:auto}
  .card.pl-horizontal .pl-side .pl-queue{flex:none;max-height:150px}
}
/* Dashboard-Embed, Video oben (JB 22.07.): die Videofläche NICHT den ganzen Rest fressen
   lassen (das erzeugte die großen schwarzen Balken), sondern an ~16:9 binden — dann füllt
   das Video sie fast randlos. Der frei werdende Platz geht an die Playlist. Ein bisschen
   Letterbox bei Nicht-16:9 bleibt (ok). max-height deckelt für kurze/breite Rahmen. */
body.embed #view-player .card:not(.pl-horizontal) .pl-media{flex:none;aspect-ratio:16/9;max-height:70%}
body.embed #view-player .card:not(.pl-horizontal) .pl-side{flex:1;min-height:0}
body.embed #view-player .card:not(.pl-horizontal) .pl-side .pl-queue{flex:1;max-height:none}
/* Build 144j (JB 25.07., mit Bild: „die fläche rechts oben sollte ausgefüllt
   sein vom player"): Im Dashboard ist die Playlist als eigener Tab ausgelagert
   (body.plq-extern) — dann hat der Player NUR Video/Cover und keine Playlist,
   die den Rest füllt. Gemessen blieben 102 px leer unter der Medienfläche.
   Ohne konkurrierende Playlist ist das Füllen gefahrlos (anders als der Player-
   Fall aus 144f): Das <video>/.pl-cover behält sein 16:9 über object-fit:contain,
   die FLÄCHE wächst nur mit und bekommt bei Bedarf schmale Balken. Regeln nach
   den obigen, damit sie bei ausgelagerter Playlist gewinnen. */
body.embed.plq-extern #view-player{height:100%;display:flex;flex-direction:column}
body.embed.plq-extern #view-player>.card{flex:1 1 auto;min-height:0}
body.embed.plq-extern #view-player .card:not(.pl-horizontal) .pl-media{flex:1 1 auto;max-height:none;min-height:0}
/* Zu-klein-Verhalten (JB 14.07., Muster Video.js/Media Chrome/VLC): Knöpfe haben
   Vorrang — die Videofläche gibt zuerst nach, dann fallen Playlist/Titel weg,
   und in der Video-Leiste verschwinden Sekundär-Knöpfe GESTUFT (bo3→bo2→bo1);
   alles Ausgeblendete bleibt übers Rechtsklick-Menü erreichbar. */
@container plcard (max-height:330px){
  /* #view-player erhöht die Spezifität — die Basisregel .pl-queue{display:flex}
     steht später im Stylesheet und würde sonst gewinnen. */
  #view-player .pl-queue,#view-player .pl-kapitel,#view-player .pl-lyrics{display:none}
}
@container plcard (max-height:200px){
  .pl-titel{display:none}
  .pl-media{min-height:0}
}
@container plcard (max-width:380px){
  .pl-hint{display:none}
}
/* Stufen pixel-genau vermessen (14.07.): volle Leiste braucht 537px, ohne
   YouTube-TEXT 486, ohne Stufe 3 343, ohne Stufe 2 151 — Schwellen knapp
   darüber, damit so viel wie möglich sichtbar bleibt (JB: „Auge isst mit"). */
@container plmedia (max-width:548px){ .pl-bar .bo-yttxt{display:none} }
@container plmedia (max-width:496px){ .pl-bar .bo3{display:none} }
@container plmedia (max-width:353px){ .pl-bar .bo2{display:none} }
@container plmedia (max-width:161px){ .pl-bar .bo1,.pl-bar .pl-btime{display:none} }
.pl-leer{color:#6a5c52;font-size:13px;text-align:center;padding:24px}
.pl-titel{font-weight:600;font-size:14px;margin:10px 0 6px;flex:none}
.pl-ctrl{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:8px;flex:none}
/* Build 144d: der Lieblings-Knopf zeigt seinen Zustand über die FARBE, nicht
   über einen zweiten Knopf daneben — leer heisst „noch nicht drin". */
.pl-lieb{min-width:30px;font-weight:700}
.pl-lieb.an{background:var(--akz);border-color:var(--akz);color:#1b1512}
/* Steuerleiste AUF dem Video/Cover (YouTube-Stil, JB 13.07.): Spulleiste oben,
   Transport links, Werkzeuge rechts; blendet bei Maus-Ruhe aus (.baridle). */
.pl-bar{position:absolute;left:0;right:0;bottom:0;z-index:6;display:flex;flex-direction:column;gap:1px;
  padding:4px 10px 7px;background:linear-gradient(transparent,rgba(0,0,0,.82));transition:opacity .25s}
.pl-media.baridle .pl-bar{opacity:0;pointer-events:none}
.pl-media.baridle{cursor:none}
/* ---- Vollbild-Overlay (Build 130, JB Punkt 3) -----------------------------
   Netflix-/Disney-Muster: die Leiste erscheint bei Mausbewegung und geht nach
   ~3 s wieder weg (das macht schon .baridle). Neu ist, WAS im Vollbild steht.
   Grund: Zufall/Vor/Zurück/Wiederholen wohnen seit Build 121 oben in der
   Steuerzentrale — die ist im Vollbild aber nicht sichtbar. Ohne eigene
   Knöpfe käme man dort also nicht zum nächsten Titel und nicht zurück.
   Deshalb blendet das Vollbild genau das Wichtigste EIN (±10 s, nächster
   Titel, Beenden) und die Nebensachen AUS (Clip, Tempo, Bild-in-Bild).
   Nichts davon geht verloren: die Tastenkürzel gelten im Vollbild weiter
   (S Untertitel, Shift+,/. Tempo, ↑/↓ Lautstärke), und beim Verlassen ist
   die volle Leiste sofort wieder da. */
/* Spul-Einblender (Build 132): erscheint auf der Seite, in die gesprungen
   wird, und verblasst von selbst. pointer-events:none — er ist Rückmeldung,
   kein Knopf, und darf einen Klick ins Bild nie abfangen. */
.pl-sprung{position:absolute;top:50%;transform:translateY(-50%);z-index:7;pointer-events:none;
  display:flex;flex-direction:column;align-items:center;gap:2px;
  background:rgba(0,0,0,.55);border-radius:999px;padding:14px 18px;color:#fff;
  font-size:12px;font-weight:600;animation:sprungWeg .7s ease-out forwards}
/* Build 139 (JB: „koennen wie bei YouTube etwas zentraler sein"): naeher an
   die Mitte geholt. Bei YouTube liegen die Doppeltipp-Flaechen bei etwa
   einem Viertel der Breite - dort sucht das Auge sie, nicht am Bildrand. */
.pl-sprung.links{left:25%}
.pl-sprung.rechts{right:25%}
.pl-sprung svg{width:26px;height:26px;fill:#fff}
@keyframes sprungWeg{0%{opacity:0;transform:translateY(-50%) scale(.86)}
  18%{opacity:1;transform:translateY(-50%) scale(1)}
  70%{opacity:1}100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.pl-sprung{animation:none;opacity:.9}}
/* Spul-Anzeige am Fernseher (JB 05.08.): ⏪/⏩ + Geschwindigkeit, oben mittig
   wie bei den Streamern — reine Rückmeldung, nimmt keine Klicks an. */
#pl-spul{position:absolute;top:10%;left:50%;transform:translateX(-50%);z-index:7;
  pointer-events:none;display:flex;align-items:center;gap:10px;color:#fff;
  background:rgba(0,0,0,.55);border-radius:999px;padding:10px 20px;
  font-size:20px;font-weight:700}
#pl-spul svg{width:30px;height:30px;fill:currentColor}
.nur-vollbild{display:none}
.pl-media:fullscreen .nur-vollbild{display:inline-flex;align-items:center;justify-content:center}
.pl-media:fullscreen .weg-im-vollbild{display:none}
.pl-media:fullscreen .pl-bar{padding-bottom:14px}      /* Daumenbreite zum Bildrand */
/* Vollbild = Sofa-/TV-Abstand (JB 05.08., Netflix-Muster): Kern-Knöpfe,
   Zeit und Spul-Leiste deutlich größer, damit man sie von weitem trifft. */
.pl-media:fullscreen .pl-barrow .mp-btn{width:46px;height:46px}
.pl-media:fullscreen .pl-barrow .mp-btn svg{width:32px;height:32px}
.pl-media:fullscreen .pl-bsp{font-size:24px;padding:6px 10px}
.pl-media:fullscreen .pl-btime{font-size:18px}
.pl-media:fullscreen .pl-barseek input{height:18px}
.pl-media:fullscreen .pl-bvol{width:120px}
.pl-media:fullscreen video{border-radius:0}
.pl-barseek{display:flex;align-items:center;gap:8px}
.pl-barseek input{flex:1;height:12px;accent-color:var(--akz);cursor:pointer;margin:0;min-width:40px}
.pl-barrow{display:flex;align-items:center;gap:6px}
.pl-barrow .mp-btn{color:#eee;width:27px;height:27px}
.pl-barrow .mp-btn:hover{color:#fff}
.pl-barrow .mp-btn svg{width:19px;height:19px}
.pl-barrow .mp-tog{color:rgba(255,255,255,.55)}
.pl-barrow .mp-tog.an{color:var(--akz2)}
.pl-btime{color:#ddd;font-size:11.5px;font-variant-numeric:tabular-nums;white-space:nowrap;flex:none}
.pl-bsp{color:#eee;background:none;border:1px solid rgba(255,255,255,.3);border-radius:6px;
  font-size:11.5px;padding:2px 7px;cursor:pointer;flex:none}
.pl-bsp:hover{border-color:#fff}
.pl-bsp.an{border-color:var(--akz);color:var(--akz2)}
.pl-bspacer{flex:1}
.pl-bvolwrap{display:flex;align-items:center;gap:4px;color:#eee;font-size:12px;flex:none}
.pl-bvol{width:64px;height:10px;accent-color:#fff;cursor:pointer;margin:0}
/* Untermenüs im Rechtsklick-Menü: Liste mit Haken + optionales Suchfeld */
.km-check{color:var(--akz2);margin-right:6px}
/* WICHTIG: flex-column, sonst fließen die <button> als inline-Blöcke NEBENEINANDER */
.km-sub{display:flex;flex-direction:column;gap:2px;max-height:240px;overflow-y:auto}
.km-sub button{text-align:left}
.km-such{display:block;width:calc(100% - 12px);box-sizing:border-box;margin:4px 6px;background:#0e0c0a;
  border:1px solid var(--panelln);border-radius:6px;color:#e7dccf;padding:4px 8px;font-size:12px}
html.light .km-such{background:#f7f3ee;border-color:#e0d7cc;color:#4a3f37}
/* Windows-artiges Ausklappen: Eintrag mit ▸ rechts, Flyout erscheint daneben */
.km-hatsub{display:flex;align-items:center;justify-content:space-between;gap:12px}
.km-pfeil{color:#8a7d74;font-size:10px;flex:none}
.km-flyout{min-width:180px}
/* YouTube-Knöpfe + Lautstärke im Mini-Player */
.mp-vol{margin-left:auto;color:#8a7d74}
.mp-vol .pl-bvol{accent-color:var(--akz)}
.mp-yt svg{width:20px;height:20px}
.pl-byt{display:inline-flex;align-items:center;gap:5px}
.pl-byt svg{width:15px;height:15px;fill:currentColor;display:block}
.muted2{font-size:12px;color:#8a7d74}
.pl-queue{display:flex;flex-direction:column;gap:2px;max-height:150px;overflow:auto;flex:0 1 auto;min-height:0}
/* flex:none ist PFLICHT: sonst schrumpfen viele Einträge (z.B. 40 vom Radio)
   unter ihre Texthöhe und die Liste sieht „zerhackt" aus (JB-Fund 13.07.) */
.pl-item{font-size:12px;color:#d7c7bd;padding:4px 7px;border-radius:6px;cursor:pointer;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;flex:none}
.pl-item:hover{background:#241f1b}
.pl-item.sel{background:var(--akzbg);box-shadow:inset 0 0 0 1px var(--akz)}
.pl-item:focus{outline:1px solid var(--akz);outline-offset:-1px}
.pl-item:focus-visible{outline:2px solid var(--akz)}
.pl-item.akt{background:var(--akzbg);color:var(--akz2)}
.pl-item.artaus{opacity:.35}                          /* per 🎶/🎬 weggefiltert */

/* ---- Tag-Modus (hell) ---- */
html.light body{background:#f4efe9;color:#2a2320}
html.light h1,html.light .card h2{color:#b5502a}
html.light .sub,html.light .info,html.light details.einst summary,html.light .apistat,
html.light #layoutbar{color:#7a6e64}
html.light .card,html.light .panel{background:#fff;border-color:#e6ddd3}
html.light .panel-head{background:#f3ede7;border-color:#e6ddd3}
html.light .ptab{color:#8a7d74}
html.light .ptab.an{background:#f3e7d6;border-color:#d8b98a;color:#8a5a1e}
html.light .panel-grip{border-color:#b8ab9f;color:#b8ab9f}
html.light .panel-body .card{background:transparent}
html.light textarea,html.light select,html.light input[type=text],
html.light .btn,html.light .iconbtn,html.light .chip,
html.light .viewbtn,html.light .tog{
  background:#fbf8f4;border-color:#d9cfc4;color:#2a2320}
html.light .btn.haupt{background:#f3e7d6;border-color:#d8b98a;color:#8a5a1e}
html.light .viewbtn.an,html.light .tog.an{background:#f3e7d6;border-color:#d8b98a;color:#8a5a1e}
html.light .cmd-count .tip{background:#fff;border-color:#e6ddd3;box-shadow:0 8px 24px rgba(120,90,60,.18)}
html.light .tiprow{color:#5a4f47}html.light .tiprow b{color:#2a2320}
html.light .tiptitel,html.light .chk{color:#8a7d74}html.light .tipsep{background:#e6ddd3}
html.light .chip{color:#5a4f47}
html.light .eintrag{border-color:#ece3d9}
html.light .balken{background:#eadfd4}
html.light .pill{color:#6f635b;border-color:#d9cfc4}
html.light .pill.fertig{color:#2e8b47;border-color:#a9d8b4}
html.light .pill.laeuft{color:#a8841a;border-color:#e0cf8a}
html.light .pill.fehler{color:#c0492a;border-color:#e6b3a3}
html.light .pill.pausiert{color:#b96a1e;border-color:#e6c69a}
html.light .pill.uebersprungen{color:#3f7a44;border-color:#a9d8b4}
html.light .qtag{color:#9a6a12;border-color:#d8b98a}
html.light .kachel{background:#fdfaf6;border-color:#e6ddd3}
html.light .thumbwrap,html.light .lthumb{background:#efe7de}
html.light .thumbwrap.platzhalter::after{color:#c9bcae}
html.light .libtab th{color:#8a7d74;border-color:#e6ddd3}
html.light .libtab td{border-color:#ece3d9}html.light .libtab td.num{color:#7a6e64}
html.light .leer,html.light .hinweis{color:#9a8d84}
html.light .colmenu{background:#fff;border-color:#e6ddd3;box-shadow:0 8px 24px rgba(120,90,60,.18)}
html.light .colrow label,html.light .colmv{color:#2a2320}
html.light .colmv{background:#fbf8f4;border-color:#d9cfc4}
html.light .pl-media{background:#efe7de}
html.light .pl-item{color:#5a4f47}html.light .pl-item:hover{background:#f3ede7}
html.light .pl-item.akt{background:#f3e7d6;color:#8a5a1e}

/* Inhalte passen sich der Fenstergröße an (Container-Queries) — MUSS am Ende
   stehen, damit diese Regeln die Basis-Regeln überschreiben (gleiche Spezifität). */
@container (max-width:270px){
  .card h2{font-size:12px}
  .qline{font-size:11.5px;gap:6px}
  .balken{height:4px;margin:6px 0 5px}
  .info{font-size:11px}
  .aktionen .btn.mini{padding:2px 6px;font-size:11px}
  .kacheln{grid-template-columns:1fr}
  .einstgrid{grid-template-columns:1fr;gap:3px 0}
  .einstgrid>span{margin-top:6px;color:#8a7d74;font-size:11px}
  .libbar{gap:6px}
}
@container (max-width:200px){
  .qbar{display:none}
  .qrechts{font-size:10px}
  .info{display:none}
  .kopf .qtag{display:none}
  .chip{padding:2px 8px;font-size:11px}
  .card h2{font-size:11px}
}
</style>
</head>
<body>
<!-- Einbettungs-Modus (JB 21.07.2026: „ein Browser, ein Browser"): im Dashboard-iframe
     (?embed=1) nur Logo + Build-Marke ausblenden. Die Layout-Leiste (✏ Layout,
     🔳 Mini) BLEIBT — JB braucht sie auch im Dashboard (21.07.). -->
<style>body.embed .cmd-logo,body.embed #buildmark{display:none}</style>
<script>/* embed nur im echten iframe (Dashboard). Ein neuer Tab schleppt ?embed=1 mit,
   ist aber KEIN iframe -> dort das Logo zeigen (JB 25.07.). window.top!==self ist
   cross-origin-sicher (nur Referenzvergleich, kein Property-Zugriff). */
if(location.search.indexOf('embed=1')>=0 && window.top!==window.self)document.body.classList.add('embed');</script>
<div id="cmdbar">
  <div class="cmd-main">
    <div class="cmd-left">
      <div class="cmd-row1">
        <span class="cmd-logo" title="YouTube-Downloader — Sync-Familie">
          <svg class="emblem" viewBox="0 0 120 112" width="26" height="24" aria-hidden="true">
            <defs><linearGradient id="ytemb" x1="0" y1="0" x2="0.35" y2="1">
              <stop offset="0" stop-color="#e7a2a2"/><stop offset="0.55" stop-color="#d65f5f"/><stop offset="1" stop-color="#8d3e3e"/>
            </linearGradient></defs>
            <path d="M 10 96.6 A 100 100 0 0 0 110 96.6 A 100 100 0 0 0 60 10 A 100 100 0 0 0 10 96.6 Z" fill="url(#ytemb)"/>
            <path class="sg" d="M 73 34 C 70 26 57 23 49 26 C 40 29 38 37 41 44 C 44 51 54 53 60 55 C 68 57 75 61 75 69 C 75 79 65 85 55 84 C 46 83 40 78 39 71"
                  fill="none" stroke="#141110" stroke-width="14" stroke-linecap="round"/>
          </svg><b>YouTube-Downloader</b></span>
        <span class="spacer"></span>
        <!-- Build 132 (JB): Status-Punkt und Zähler stehen jetzt hier oben in
             der ersten Reihe — Punkt links von „Layout", Zähler rechts von
             „Mini". Sie brauchten unten neben dem Player eine eigene Spalte,
             die dem Bild Platz wegnahm; hier liegen sie auf der ruhigen
             Kopfzeile, wo Statuszeichen üblicherweise wohnen. -->
        <!-- Build 134 (JB Punkt 4): sichtbares Geräte-Symbol für die
             Fernsteuerung. Die Funktion gab es längst, sie lag aber im
             ⚙-Menü — niemand vermutet ein Handy hinter einem Zahnrad.
             Sichtbar wird das Symbol nur, wenn die Fernsteuerung LÄUFT
             (Calm-Design: keine Anzeige ohne Anlass); ausgeschaltet bleibt
             sie über das ⚙ erreichbar wie bisher. -->
        <button class="btn mini" id="fern-symbol" onclick="fernFenster(event)" style="display:none"
                title="Fernsteuerung läuft — Code und Handy-Link anzeigen">📱</button>
        <span class="apidot bad" id="apidot" title="API-Status"></span>
        <button class="btn mini" id="layoutedit-btn" onclick="layoutEditToggle()"
                title="Layout bearbeiten: Werkzeuge ausklappen, Fenster verschieben &amp; an 8 Griffen ziehen (ohne Überlappen) — AUS: Ziehen dockt nur als Tab an">✏ Layout</button>
        <button class="btn mini" id="mini-btn" onclick="miniToggle()" title="Mini-Player: schrumpft auf Cover + Regler, bleibt oben eingebettet">🔳 Mini</button>
        <span class="cmd-count" id="counter" tabindex="0" title="Gesamtzahl aller je geladenen Dateien — drüberfahren für die Aufschlüsselung">⬇ <b id="counter_num">0</b><span class="tip" id="counter_tip"></span></span>
        <span id="ffwarn" style="display:none;color:#e08a6a;font-size:11.5px;white-space:nowrap"
              title="ffmpeg.exe, ffprobe.exe und deno.exe müssen im Ordner „bin&quot; NEBEN der App liegen (im Komplett-Zip enthalten). Ohne ffmpeg: Videos nur bis ~720p, kein MP3, kein Cover.">⚠ bin-Ordner fehlt</span>
        <span id="buildmark" title="Baustand — bei Problemen prüfen, ob dieser aktuell ist">Build 2026-07-14 · 143</span>
      </div>
      <div class="cmd-rowadd">
        <!-- Build 126 (JB: „drei zu ähnliche Knöpfe"): EIN Feld für alles.
             Video, Playlist, Kanal, Mix — Enter genügt, den Rest erkennt die
             App am Link. Der frühere 📺-Knopf ist damit überflüssig: ein
             Playlist-/Kanal-Link löst denselben Weg von selbst aus, und wer
             bei einem Video-in-Playlist-Link doch alles will, bekommt genau
             dafür die Rückfrage. Nichts ist unerreichbar geworden. -->
        <input id="cmd-url" class="cmd-url" placeholder="🔗 Video, Playlist oder Kanal einfügen — Enter genügt"
               title="Erkennt selbst, was der Link ist. Nur bei echter Mehrdeutigkeit wird gefragt (Kanal: laden oder abonnieren? Video aus einer Playlist: eines oder alle?) — die Antwort lässt sich merken und unter ⚙ wieder umstellen."
               onkeydown="if(event.key==='Enter')cmdDownload()">
        <select id="cmd-qual" class="cmd-qual" title="Qualität (Auswahl wird gemerkt)" onchange="qualMerken(this.value)">
          <option value="beste">Beste</option><option value="2160p">2160p</option>
          <option value="1440p">1440p</option><option value="1080p">1080p</option>
          <option value="720p">720p</option><option value="audio">MP3</option>
        </select>
        <button class="cmd-dl" onclick="cmdDownload()" title="Laden — erkennt selbst, ob Video, Playlist, Kanal oder Mix">⬇ Laden</button>
      </div>
      <div class="cmd-row2">
        <div class="cmd-now" id="cmd-now" ondragover="cmdNowOver(event)" ondragleave="cmdNowLeave(event)" ondrop="cmdNowDrop(event)"
             title="Titel aus der Bibliothek hierher ziehen = in die Playlist einreihen"><span class="cmd-nolabel">// nichts läuft</span></div>
        <!-- Build 132: Die frühere Statistik-Spalte ist entfallen — ihr Inhalt
             wohnt oben in der ersten Reihe. Der Player bekommt den Platz. -->
        <div class="cmd-side">
          <button class="iconbtn sm" onclick="abosZeigen()" title="Abos: Kanäle/Playlists abonnieren, Backkatalog, Format &amp; Regeln je Abo (Reiter im Download-Fenster)">📡</button>
          <button class="iconbtn sm" id="theme" onclick="themeToggle()" title="Tag-/Nacht-Modus schnell umschalten">🌙</button>
          <button class="iconbtn sm" onclick="hilfeModal(true)" title="Legende: alle Knöpfe, Gesten &amp; Tasten erklärt">?</button>
          <button class="iconbtn sm" id="optbtn" onclick="optionenToggle(event)" title="Optionen (Look, Crossfade, Sleep-Timer, Fenster-Abstand …)">⚙</button>
        </div>
      </div>
    </div>
    <!-- Fest eingebettetes Download-Fenster (JB 21.07.): vier Reiter, oben rechts
         verankert. Im Mini-Modus löst es sich und wandert unter die Playlist. -->
    <div class="cmd-right" id="dlbox">
      <div class="dlbox-tabs" id="dlbox-tabs">
        <button class="dlbox-tab an" data-dlt="queue" onclick="dlboxTab('queue')">Downloads</button>
        <button class="dlbox-tab" data-dlt="done" onclick="dlboxTab('done')">Fertig</button>
        <button class="dlbox-tab" data-dlt="log" onclick="dlboxTab('log')">Log</button>
        <button class="dlbox-tab" data-dlt="abos" onclick="dlboxTab('abos')">📡 Abos</button>
        <span class="spacer"></span>
        <button class="btn mini dlbox-action" id="dlbox-action"></button>
      </div>
      <div class="dlbox-body" id="dlbox-body"></div>
      <div id="cmd-mini"></div>
    </div>
  </div>
  <div id="cmd-clip" class="cmd-clip" style="display:none"></div>
</div>

<!-- Layout-Werkzeuge: NUR im ✏-Modus sichtbar (✏ Layout / 🔳 Mini / Build sind
     jetzt oben in der Command-Bar — JB 21.07., mehr Platz unten). -->
<div id="layoutbar">
  <label style="font-size:12px;color:#8a7d74">Layout:</label>
  <select id="layoutsel" onchange="layoutWaehlen(this.value)" title="Vorlagen &amp; deine gespeicherten Layouts"></select>
  <button class="btn mini" onclick="layoutSpeichern()" title="Aktuelle Fenster-Anordnung unter einem Namen speichern">💾 Speichern</button>
  <button class="btn mini" onclick="layoutLoeschen()" title="Das gewählte gespeicherte Layout löschen">🗑</button>
  <button class="btn mini" onclick="layoutVorheriges()" title="Vorherige Fenster-Anordnung zurückholen — nochmal klicken wechselt wieder vor">↩ Vorheriges</button>
  <button class="btn mini" onclick="layoutAufraeumen()" title="Alle Fenster ordentlich nebeneinander">▦ Aufräumen</button>
  <span><b>Tipp:</b> Rechtsklick öffnet überall Menüs · Ziehen ohne ✏ dockt nur als Tab an</span>
</div>

<div id="canvas"></div>

<div id="hilfemodal" class="modal" style="display:none" onclick="if(event.target===this)hilfeModal(false)">
  <div class="modal-box">
    <div class="modal-head"><b>? Legende — so bedienst du alles</b>
      <button class="btn mini" onclick="hilfeModal(false)">✕ Schließen</button></div>
    <div class="legbody">
      <div class="legsec">🖱 Gesten</div>
      <div class="legrow"><b>Klick</b> auf Video/Cover im Player = Pause/Weiter · auf einen Download im <b>Downloads</b>-Reiter = Pause/Fortsetzen</div>
      <div class="legrow"><b>Rechtsklick</b> auf Titel in der Bibliothek ODER in den Player = Menü mit allen Aktionen</div>
      <div class="legrow"><b>Mausrad kippen</b> (links/rechts) = zurück/vor zur vorherigen Ansicht — wie im Browser</div>
      <div class="legrow"><b>Ziehen</b>: Link aus dem Browser ins Fenster = Download · Titel in Playlist-Ansicht/Player-Warteschlange = umsortieren · Fenster auf ein anderes ziehen = als Tab andocken (schnappt sonst zurück) · Tab auf ein anderes Fenster ziehen = dort als Tab andocken · Tab auf Freifläche = eigenes Fenster, das die Lücke dort ausfüllt (andere Fenster bleiben stehen)</div>
      <div class="legrow"><b>✏ Layout</b> (unten): Fenster frei verschieben + an 8 Griffen die Größe ziehen — das bewegte Fenster hat Vorfahrt, die anderen weichen aus, nichts überlappt; nochmal klicken beendet den Modus</div>
      <div class="legrow"><b>🎶 Playlist</b> (im Player): Player-Playlist als eigenes Fenster herauslösen — andockbar wie jeder Tab. Titel aus der Bibliothek <b>hineinziehen</b> = einreihen (auf einen Eintrag = an der Stelle, auf die Fläche = ans Ende)</div>
      <div class="legrow"><b>Strg-/Shift-Klick</b> in der Bibliothek = mehrere markieren (Leiste mit Sammel-Aktionen erscheint)</div>
      <div class="legsec">▶ Player</div>
      <div class="legrow">Steuerung liegt <b>auf dem Video/Cover</b> (erscheint bei Mausbewegung): Zufall 🔀 und Wiederholen 🔁 sind <b>getrennte Schalter</b> — farbig mit Punkt = an, 🔁 nochmal klicken = nur diesen Titel (Zeichen zeigt eine kleine 1)</div>
      <div class="legrow">Rechts auf der Leiste: <b>💬</b> Untertitel/Karaoke (Musik zeigt echte, mitleuchtende Songtexte via LRCLIB; sonst YouTube-Untertitel, still nachgeladen) · <b>✂</b> Clip schneiden · <b>1×</b> Geschwindigkeit · 🔊 Lautstärke · <b>YouTube</b> öffnet das Video · <b>⧉</b> Bild-in-Bild · <b>⛶</b> Vollbild</div>
      <div class="legrow">Einzeltitel zu Ende = automatisch der <b>nächste Titel der Bibliothek</b> (bei 🔀 ein zufälliger; Playlists stoppen wie gehabt am Ende)</div>
      <div class="legrow"><b>Rechtsklick in den Player</b> = alles Weitere: Visualizer-Liste, Geschwindigkeit, Untertitel-Sprachen, Equalizer, Playlist, VLC …</div>
      <div class="legsec">📚 Bibliothek</div>
      <div class="legrow">Auf einer Kachel erscheinen beim <b>Überfahren</b>: <b>▶</b> abspielen · <b>＋</b> zu Playlist · <b>📁</b> im Ordner zeigen · <b>⋯</b> mehr (auf Touch stehen sie fest da)</div>
      <div class="legrow"><b>⚙ Ansicht</b> bündelt alles zur Darstellung: <b>▪▪/⊞/▤/☰</b> Kompakt/Kacheln/Alben/Liste, Filter, Spalten, Archiv, Mehrfach-Auswahl, Dubletten, Auto-Tagging, Ordner-Import</div>
      <div class="legrow"><b>Suchen</b> durchsucht Titel/Künstler/Kanal — findet es nichts, sucht es von selbst im <b>gesprochenen Text</b> (Untertitel/Songtexte) weiter und zeigt die Treffer darunter</div>
      <div class="legrow"><b>📃 Öffnen</b> zeigt eine Playlist (Ziehen = Reihenfolge) · <b>🎛 Mixer</b> Endlos-Radio/Meistgespielt/Zuletzt/Smart · <b>🔎 Text</b> durchsucht die Untertitel/Transkripte ALLER Videos (Klick auf einen Treffer springt an die Stelle)</div>
      <div class="legsec">⬇ Downloads &amp; Abos</div>
      <div class="legrow">Oben rechts das feste <b>Download-Fenster</b>: <b>Downloads</b> (was gerade lädt/wartet, Klick = Pause, <b>✖</b> = abbrechen — Dateien bleiben) · <b>Fertig</b> · <b>Log</b> (Übersicht + Ereignisse). Laden: Link/Playlist oben einfügen + <b>⬇ Download</b>. <b>📡</b> öffnet die <b>Abos</b> (Kanäle/Playlists abonnieren, Backkatalog nachladen, Format &amp; Regeln je Abo).</div>
      <div class="legsec">⌨ Tasten (wenn nicht in einem Eingabefeld)</div>
      <div class="legrow"><b>Leertaste/K</b> Pause/Weiter · <b>J/L</b> −/+10 s · <b>←/→</b> −/+5 s · <b>↑/↓</b> Lautstärke · <b>N/P</b> nächster/voriger Titel · <b>M</b> stumm · <b>F</b> Vollbild · <b>I</b> Bild-in-Bild · <b>S</b> Untertitel · <b>?</b> diese Legende · <b>Strg+←/→</b> &amp; <b>Medientasten</b> weiterhin</div>
      <div class="legsec">⚡ Command-Bar oben</div>
      <div class="legrow">Links: Link/Playlist einfügen + <b>⬇ Download</b> · Mini-Player (🔀 ⏮ ⏯ ⏭ 🔁 📻, Titel darunter, <b>Spulleiste</b> — ziehen = spulen · <b>🎶/🎬</b> was spielt: nur Musik / nur Videos / beides · Titel aus der Bibliothek auf den Player ziehen = einreihen). Rechts das Download-Fenster. <b>🔗</b> Kopierte YouTube-Links werden automatisch erkannt. <b>🔳 Mini</b>: Player klein &amp; eingebettet oben, Bibliothek + Playlist + Downloads darunter.</div>
    </div>
  </div>
</div>

<div id="settingsmodal" class="modal" style="display:none" onclick="if(event.target===this)settingsZu()">
  <div class="modal-box">
    <div class="modal-head"><b>⚙ Einstellungen</b>
      <button class="btn mini" onclick="settingsZu()">✕ Schließen</button></div>
    <div id="settingsbody" style="padding:14px 16px 20px;max-height:80vh;overflow:auto"></div>
  </div>
</div>

<div id="geowiz" class="modal" style="display:none" onclick="if(event.target===this)geoWizZu()">
  <div class="modal-box">
    <div class="modal-head"><b>🌍 Geo/VPN einrichten</b>
      <button class="btn mini" onclick="geoWizZu()">✕ Schließen</button></div>
    <div id="geowiz-body">lade…</div>
  </div>
</div>

<div id="stash" style="display:none">
  <div id="view-add">
    <div class="card">
      <h2>Hinzufügen</h2>
      <textarea id="urls" placeholder="YouTube-Links hier einfügen — einer pro Zeile.
Playlist-Link (…/playlist?list=…) übernimmt die ganze Liste."></textarea>
      <div class="zeile">
        <label for="qual" style="font-size:13px;color:#8a7d74">Qualität</label>
        <select id="qual">
          <option value="beste">Beste verfügbare</option>
          <option value="2160p">4K (2160p)</option>
          <option value="1440p">1440p</option>
          <option value="1080p">1080p</option>
          <option value="720p">720p</option>
          <option value="audio">Nur Audio (MP3)</option>
        </select>
        <button class="btn haupt" onclick="hinzufuegen()" title="Eingefügte Links in die Download-Warteschlange stellen (Strg+Enter)">In die Warteschlange</button>
      </div>
    </div>

    <div class="card">
      <div class="kopfzeile"><h2>🔔 Abos</h2>
        <button class="btn mini" onclick="ensureView('abos')" title="Abo-Fenster öffnen: abonnieren, Backkatalog nachladen, Format &amp; Regeln je Abo">📡 Abo-Fenster öffnen</button></div>
      <div class="hinweis">Kanäle/Playlists abonnieren, ältere Folgen nachladen, Format und Regeln je Abo —
        alles im Abo-Fenster (andockbar wie jeder Tab).</div>
    </div>

    <div class="card" id="settingscard">
        <div class="einstgrid">
          <span>Zielordner</span><input type="text" id="cfg_ziel">
          <span>Unterordner</span>
          <select id="cfg_ordner">
            <option value="1">nach Kategorie (MP3 / 4K+ / Video)</option>
            <option value="0">aus (alles in einen Ordner)</option>
          </select>
          <span>Metadaten in Dateien</span>
          <select id="cfg_meta">
            <option value="1">an (Titel, Künstler, Datum …)</option>
            <option value="0">aus</option>
          </select>
          <span>Premium-Cookies aus</span>
          <select id="cfg_browser">
            <option value="firefox">Firefox</option>
            <option value="chrome">Chrome</option>
            <option value="edge">Edge</option>
            <option value="keine">keine (ohne Konto laden)</option>
          </select>
          <span>Gleichzeitige Downloads</span>
          <select id="cfg_parallel"><option>1</option><option>2</option><option>3</option></select>
          <span>Geo-Sperren umgehen</span>
          <select id="cfg_geo">
            <option value="1">automatisch (alle Wege durchprobieren)</option>
            <option value="0">aus</option>
          </select>
          <span>Gratis-Proxys nutzen</span>
          <select id="cfg_geoproxyfrei">
            <option value="1">ja (kostenlos, aber wackelig)</option>
            <option value="0">nein</option>
          </select>
          <span>Eigene Proxys<br><small style="color:#6a5c52">optional</small></span>
          <textarea id="cfg_geoproxies" style="min-height:44px" placeholder="je Zeile ein Proxy, z.B.
GB=socks5://1.2.3.4:1080   (nur fürs Land)
socks5://5.6.7.8:1080      (für alle Länder)"></textarea>
          <span>WireGuard-Ordner<br><small style="color:#6a5c52">optional (z.B. ProtonVPN Free)</small></span>
          <input type="text" id="cfg_geowg" placeholder="Ordner mit .conf-Dateien, benannt nach Land (GB.conf …)">
          <span>VPN einrichten</span>
          <button class="btn" onclick="geoWizOffen()" style="justify-self:start">🌍 Assistent öffnen (Vergleich · Anleitung · Test)</button>
          <span>Standard-Qualität</span>
          <select id="cfg_qual">
            <option value="beste">Beste verfügbare</option><option value="2160p">4K</option>
            <option value="1440p">1440p</option><option value="1080p">1080p</option>
            <option value="720p">720p</option><option value="audio">Nur Audio</option>
          </select>
          <span>Untertitel laden</span>
          <select id="cfg_subs">
            <option value="1">an (auch automatische)</option>
            <option value="0">aus</option>
          </select>
          <!-- JB Punkt 6: Sprachwahl fürs automatische Laden. „Original" =
               die unübersetzte Auto-Spur des Videos (Karaoke/Romaji). -->
          <span>Untertitel-Sprachen<br><small style="color:#6a5c52">wirkt nur, wenn „laden" an ist</small></span>
          <span id="cfg_subs_sprachen" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
            <label class="chk" style="margin:0"><input type="checkbox" id="cfg_sub_de" checked style="width:auto"> Deutsch</label>
            <label class="chk" style="margin:0"><input type="checkbox" id="cfg_sub_en" checked style="width:auto"> Englisch</label>
            <label class="chk" style="margin:0" title="Die unübersetzte Original-Spur des Videos — braucht das Karaoke (Romaji)"><input type="checkbox" id="cfg_sub_orig" checked style="width:auto"> Original</label>
            <input id="cfg_sub_extra" placeholder="weitere: ja, es" style="width:110px" title="Weitere Sprach-Kennungen, mit Komma (z. B. ja, es, fr)">
          </span>
          <span>SponsorBlock<br><small style="color:#6a5c52">Werbung rausschneiden</small></span>
          <select id="cfg_sponsor">
            <option value="">aus</option>
            <option value="sponsor">nur Werbung entfernen</option>
            <option value="alle">Werbung + Intro/Outro/… entfernen</option>
          </select>
        </div>
        <div class="zeile"><label for="cfg_autoupdate">Selbst-Update der exe</label>
          <select id="cfg_autoupdate" title="Opt-in: die gepackte exe prüft täglich das GitHub-Release, lädt verifiziert (SHA256) und tauscht sich selbst. Im Quellcode-Modus ohne Wirkung — dort aktualisiert git.">
            <option value="0">aus (Standard)</option>
            <option value="1">automatisch aktualisieren</option>
          </select>
        </div>
        <div class="zeile"><button class="btn" onclick="configSpeichern()">Speichern</button>
          <span id="cfg_meldung" style="font-size:12px;color:#9ec49a"></span></div>
        <div class="hinweis">Premium-Qualität &amp; altersbeschränkte Videos funktionieren über die
          Browser-Cookies — dafür in dem Browser bei YouTube angemeldet sein. Abgebrochene Downloads
          werden automatisch neu gestartet und setzen an der Abbruchstelle fort. Dubletten werden an
          der Video-Kennung erkannt und übersprungen. Thumbnail wird als Cover eingebettet.
          Geo-Sperren umgehen probiert automatisch der Reihe nach: Header-Trick (gratis) → eigene Proxys →
          Gratis-Proxys → VPN (NordVPN/Windscribe/WireGuard, falls vorhanden). Ohne Einrichtung greifen die
          kostenlosen Stufen; mit eigenen Proxys/VPN wird es zuverlässiger. Über fremde Proxys werden NIE
          deine Konto-Cookies gesendet. „Entfernen“ löscht nur den Listeneintrag, nie Dateien.</div>
        <div class="zeile" style="margin-top:10px"><b>🧩 Browser-Erweiterung</b></div>
        <div class="hinweis">Schickt YouTube-Videos per Rechtsklick oder Hover-Knopf direkt hierher
          (auch über das Tray-Menü erreichbar).
          <a id="addon_lokal" href="/addon.xpi" style="display:none;color:var(--akz2)">🦊 Firefox: jetzt installieren</a>
          <a href="https://github.com/schn4ppi/SyncYouTube/releases/latest" target="_blank" rel="noreferrer"
             style="color:var(--akz2)">Alle Browser: neueste Version auf GitHub</a>.
          Falls Firefox die Datei nur herunterlädt: einfach auf about:addons ziehen.</div>
    </div>
  </div>

  <div id="view-queue">
    <div class="card"><div id="liste"></div></div>
  </div>

  <div id="view-done">
    <div class="card"><div id="fertigliste"></div></div>
  </div>

  <div id="view-log">
    <div class="card">
      <div class="chips" id="logchips"></div>
      <div id="logliste" class="logliste"></div>
    </div>
  </div>

  <div id="view-lib">
    <div class="card">
      <div class="libhead">
      <div class="libbar">
        <input type="text" id="libsuche" placeholder="Suchen…" oninput="libMalen()"
               onkeydown="if(event.key==='Enter')transkriptSuche()">
        <select id="libsort" onchange="setSortSelect(this.value)" title="Sortieren nach"></select>
        <!-- Build 125 (JB-Wunsch): „⚙ Ansicht" sitzt rechtsbündig — über
             margin-left:auto (siehe CSS), nicht über einen Abstandhalter.
             Die Leiste darf umbrechen (flex-wrap); ein Abstandhalter wirkt
             dann nur in SEINER Zeile und ließe den Knopf in der nächsten
             Zeile wieder links stehen (live gemessen: 118 px Lücke). -->
        <div class="colmenuwrap">
          <button class="tog" id="libansichtbtn" onclick="ansichtToggle(event)" title="Darstellung, Filter, Spalten, Archiv, Auswahl, Dubletten …">⚙ Ansicht</button>
        </div>
      </div>
      <div id="libbulk" class="libbulk" style="display:none"></div>
      <div class="libbar plbar">
        <!-- Build 118 (JB): „Neue Playlist" steckt jetzt IM Auswahlfeld,
             Öffnen/Schließen ist ein Pfeil, Abspielen ein reiner Play-Knopf —
             aus vier Textknöpfen werden drei Symbole. -->
        <span style="font-size:12px;color:#8a7d74">Playlist:</span>
        <!-- Build 135 (JB Punkt 4): Titel lassen sich hierher ZIEHEN. Ist eine
             Playlist gewählt, landen sie darin; steht „— keine —", entsteht
             eine neue. Mehrfachauswahl reist mit, und ein Rückgängig gibt es
             auch — Einreihen ist zwar harmlos, aber 50 Titel von Hand wieder
             herauszunehmen wäre es nicht. -->
        <select id="plsel" onchange="plWahl()" ondragover="plselDragOver(event)"
                ondragleave="plselDragLeave(event)" ondrop="plselDrop(event)"
                title="Playlist wählen — Auswahl zeigt sie sofort in der Bibliothek. Titel hierher ziehen reiht sie ein; auf „— keine —" fallen lassen legt eine neue an."></select>
        <!-- Build 143 (JB): „vielleicht ein + stattdessen bei Playlist selbst?
             Wenn ich auf Playlist: klicke, dann sollte neben den Playlists ein
             Plus sein das für Hinzufügen steht. Ist intuitiv." — Genau hier
             steht es jetzt, direkt neben der Liste. Es zeigt dieselbe Auswahl
             wie das ＋ an jeder Kachel, nur für alles Markierte. -->
        <button class="btn mini" id="plplus" onclick="bulkPlaylist(event)"
                title="Markierte Titel zu einer Playlist hinzufügen — auch zu einer neuen">＋</button>
        <button class="ib" id="plviewbtn" onclick="plView()" title="Titel dieser Playlist unten in der Bibliothek anzeigen (nochmal = zurück zur ganzen Bibliothek)">📃</button>
        <button class="ib" id="plwerkbtn" onclick="plWerkzeuge(event)" title="Umbenennen · Löschen · Sync · .m3u-Export/-Import">⋯</button>
        <input type="file" id="m3ufile" accept=".m3u,.m3u8" style="display:none" onchange="plImport(this)">
        <span class="spacer"></span>
        <button class="btn mini" onclick="entdeckerOeffnen()" title="✨ Neues entdecken: YouTube-Radios zu Titeln der oben gewählten Playlist — alles, was du schon hast, wird herausgefiltert">✨ Entdecken</button>
        <button class="btn mini" onclick="mixeMenu(event)" title="Alles zum Zusammenstellen: 📻 Endlos-Radio · Meistgespielt · Zuletzt · Gefilterte · Smart-Playlists">🎛 Mixer</button>
        <span id="plinfo" style="font-size:12px;color:#9ec49a"></span>
      </div>
      </div>
      <div id="libinhalt"></div>
    </div>
  </div>

  <div id="view-player">
    <!-- Build 136 (JB): Die GANZE Player-Karte nimmt gezogene Titel an — auf
         dem Bild, über dem Bild und auf der freien Fläche darunter. Vorher
         war nur das Bild selbst Fallziel; wer knapp danebenzielte, verlor
         den Zug ins Leere. Das Ziel ist so groß wie die Fläche, die man
         meint. -->
    <div class="card" id="pl-card" oncontextmenu="return playerKontext(event)"
         ondragover="plMediaOver(event)" ondragleave="plKarteLeave(event)" ondrop="plMediaDrop(event)">
      <div class="pl-media" id="pl-media" ondragover="plMediaOver(event)" ondrop="plMediaDrop(event)" title="Titel aus der Bibliothek hierher ziehen = abspielen / einreihen (Ad-hoc-Playlist, nichts wird gespeichert)"><div class="pl-leer">Kein Titel gewählt — in der Bibliothek auf ▶ klicken.</div></div>
      <div class="pl-side">
        <div class="pl-titel" id="pl-titel"></div>
        <div class="pl-ctrl">
          <!-- Build 144d (JB Punkt 3): „Spotify-artiges ＋ im Player oben für
               eine Lieblingssongs-Playlist." Steht bewusst direkt unter dem
               Titel — wie bei Spotify, wo das Zeichen beim laufenden Stück
               sitzt und nicht in einem Menü. -->
          <button class="btn mini pl-lieb" id="pl-lieb" style="display:none" onclick="lieblingToggle()">＋</button>
          <!-- Steuerung lebt AUF dem Video (Leiste unten, YouTube-Stil) + im
               Rechtsklick-Menü — hier bleibt nur, was die Anordnung betrifft. -->
          <button class="btn mini" onclick="playerLayoutToggle()" title="Anordnung wechseln: Video oben ↔ Video links (Playlist rechts)">⇆ Layout</button>
          <!-- Etappe B (Spec Punkt 5): Ausgabegerät im Spotify-Connect-Muster.
               Der Browser bleibt das Gehirn (Warteschlange, Weiterschalten) —
               der Ton kommt wahlweise aus einer ferngesteuerten VLC-Instanz
               auf dem PC. Ohne installiertes VLC: ehrlicher Hinweis + Browser. -->
          <button class="btn mini" id="pl-geraet" onclick="geraetWechsel()"
                  title="Ausgabegerät wechseln: Browser ↔ VLC auf diesem PC — VLC spielt jedes Format und läuft unabhängig vom Browser-Fenster weiter; ohne installiertes VLC bleibt der Browser-Player">🔊 Browser</button>
          <button class="btn mini" id="plq-btn" onclick="plqFenster()" title="Player-Playlist als eigenes Fenster herauslösen / wieder eingliedern — als Fenster ist sie andockbar wie jeder Tab">🎶 Playlist</button>
          <!-- Build 137 (JB Punkt 4): „⋯-Werkzeuge auch im eingebauten
               Player (gibt es bisher nur im herausgelösten Playlist-Fenster)".
               Genau dieselbe Liste wie dort — wer die Playlist NICHT
               herauslöst, kam sonst nur über den Rechtsklick daran, und den
               muss man erst einmal erraten. -->
          <button class="btn mini" id="pl-werkbtn" onclick="plWerkzeugeImPlayer(event)"
                  title="Werkzeuge: Warteschlange sortieren, Duplikate entfernen, als Playlist speichern · Playlist umbenennen, Sync, .m3u">⋯ Werkzeuge</button>
          <!-- Build 144 (JB Punkt 2): derselbe Hinweis wie im herausgelösten
               Playlist-Fenster — wer die Playlist NICHT herauslöst, käme sonst
               nicht daran. Erscheint nur bei echter Abweichung. -->
          <button class="btn mini plq-sichern" style="display:none" onclick="plqSichern()"
                  title="Die Änderungen an dieser Warteschlange in die gespeicherte Playlist übernehmen (Reihenfolge der Playlist bleibt, Neues kommt ans Ende)">💾 sichern</button>
          <span class="muted2" id="pl-pos"></span>
          <span class="muted2 pl-hint" style="font-size:11px">· Rechtsklick = alle Optionen</span>
        </div>
        <div class="pl-kapitel" id="pl-kapitel" style="display:none"></div>
        <div class="pl-lyrics" id="pl-lyrics" style="display:none"></div>
        <div class="pl-queue" id="pl-queue" ondragover="plqZielOver(event)" ondrop="plqZielDrop(event)"
             title="Titel aus der Bibliothek hierher ziehen = einreihen"></div>
      </div>
    </div>
  </div>

  <div id="view-plq">
    <div class="card" style="height:100%;display:flex;flex-direction:column">
      <div class="kopfzeile"><h2 id="plq-titel">Playlist</h2><span class="muted2" id="plq-anzahl"></span>
        <!-- Build 144 (JB Punkt 2, „ganz dezent irgendwo"): erscheint NUR, wenn
             die Warteschlange von ihrer gespeicherten Playlist abweicht. -->
        <button class="btn mini plq-sichern" style="display:none" onclick="plqSichern()"
                title="Die Änderungen an dieser Warteschlange in die gespeicherte Playlist übernehmen (Reihenfolge der Playlist bleibt, Neues kommt ans Ende)">💾 sichern</button>
        <span class="spacer"></span>
        <button class="btn mini" onclick="plqWerkzeuge(event)" title="Warteschlangen-Werkzeuge: als Playlist speichern · sortieren · Duplikate entfernen · leeren">⋯ Werkzeuge</button>
        <!-- v1.1.2-Nachtrag (JB): im MINI-Modus ausgeblendet — dort gibt es
             keine Playlist-Seitenliste, Eingliedern ließe die Playlist ins
             Nichts verschwinden (CSS body.mini + Riegel in plqFenster). -->
        <button class="btn mini" id="plq-zurueck" onclick="plqFenster()" title="Playlist wieder in den Player eingliedern — der Player bekommt seine Breite zurück">⧉ In den Player</button></div>
      <div class="pl-queue plq-gross" id="pl-queue-win" ondragover="plqZielOver(event)" ondrop="plqZielDrop(event)"
           title="Titel aus der Bibliothek hierher ziehen = einreihen"></div>
    </div>
  </div>

  <div id="view-filme">
    <!-- Film-Fundament (Doku/SYNC_FILME_SPEC.md, Etappe 7): Anzeige-Minimum
         als Beweis der Reihen-Engine — das TV-Design ist Teilprojekt 2. -->
    <div class="card">
      <div class="zeile" style="align-items:center">
        <b style="flex:1">🎬 Filme</b>
        <span id="filme-stand" class="hinweis"></span>
        <button class="btn" onclick="filmeSync()" title="Katalog jetzt von Jellyfin abziehen (läuft sonst alle 6 h)">⟳ Abgleichen</button>
      </div>
      <div id="filme-reihen"></div>
    </div>
  </div>

  <div id="view-abos">
    <div class="card">
      <!-- Build 127 (JB: „bei Abos kann das Link-Feld weg"): Das zweite
           Eingabefeld ist entfallen — abonniert wird über das EINE Feld
           oben, ein Kanal-Link fragt dort ohnehin „laden oder abonnieren?".
           Ein Weg statt zwei; der Knopf hier führt nur noch dorthin. -->
      <div class="zeile">
        <button class="btn mini" onclick="aboAbonnierenHin()"
                title="Springt zum Feld oben — dort einen Kanal-Link einfügen und Enter drücken">＋ Abonnieren</button>
        <span class="spacer"></span>
      </div>
      <div id="abo-liste" class="abo-liste"></div>
      <div class="hinweis"><b>Abonnieren:</b> Kanal-Link oben ins Feld, Enter — dann „Abonnieren" wählen.
        Die aktuellen Videos werden dabei nur „gemerkt“ (nicht geladen); automatisch
        geholt wird nur, was danach neu erscheint (Start + alle 6&nbsp;Stunden, leichter RSS-Puls).
        <b>Je Abo:</b> das Format-Feld in der Zeile ändert die Qualität ab der nächsten Prüfung;
        unter ⚙ liegen die Regeln (Titel-Filter, Stichtag, Shorts/Streams, Auto-Löschen) und
        „🔁 Erneuern“ — damit holt man alles bisher Geladene im neuen Format,
        wahlweise unter Behalten der alten Datei oder mit Ersetzen (die alte geht
        erst NACH dem Erfolg in den Papierkorb).
        📜 zeigt den kompletten Backkatalog: Ausgegrautes ist noch nicht geladen — Doppelklick oder
        markieren&nbsp;+&nbsp;„⬇ Auswahl laden“ holt es nach. Fertige Abo-Downloads landen automatisch
        in der Playlist des Abos.</div>
    </div>
  </div>
</div>

<script>
/*LAYOUT_KERN_START*/
/* layout_kern.js — gemeinsamer Layout-Mathe-Kern der Sync-Familie
   (Overlay-Projekt, JB-Go 22.07.2026: "layout_kern go, eigenes Projekt").

   REINE Funktionen, KEIN DOM, KEIN localStorage: Rechtecke rein ({x,y,w,h,id}),
   Rechtecke/Werte raus. Jede Oberflaeche behaelt ihr eigenes Rendering und
   Aussehen (JB: "YouTube gefaellt mir wie es gerade aussieht") — geteilt wird
   nur die Geometrie: Kanten-Magnet (Snapping), Ueberlappungs-Pruefung, uniforme
   Viewport-Einpassung mit Minima. Die Formeln sind ORIGINALGETREU aus dem
   SyncYouTube-Canvas extrahiert (Verhalten per Konstruktion erhalten); der
   Aequivalenz-Waechter test_layout_kern prueft das gegen Referenzvektoren.

   MASTER: SyncDashTray/System/layout_kern.js (vendor_kern verteilt Kopien).
   In SyncYouTube lebt der Kern als markierter Inline-Block in oberflaeche.py
   (LAYOUT_KERN_START/_END — exe-sicher, kein Laufzeit-Dateizugriff); der
   Waechter erzwingt Byte-Gleichheit von Block und Master. */
(function(root){
"use strict";
var LK={};

/* Ueberlappen sich zwei Rechtecke? (Kanten-Beruehrung = KEIN Ueberlappen) */
LK.ueberlappt=function(a,b){
  return a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;
};

/* Kollidiert der Kasten (x,y,w,h) mit einem ANDEREN Rechteck der Liste? */
LK.kollidiert=function(rects,selbstId,x,y,w,h){
  return rects.some(function(o){
    return o.id!==selbstId && x<o.x+o.w && x+w>o.x && y<o.y+o.h && y+h>o.y;
  });
};

/* Die NAECHSTE Kante im Fangradius T — sonst die Ausgangsposition. */
LK.naechsteKante=function(pos,kandidaten,T){
  var best=pos,bestD=T+0.001;
  for(var i=0;i<kandidaten.length;i++){
    var d=Math.abs(pos-kandidaten[i]);
    if(d<bestD){bestD=d; best=kandidaten[i];}
  }
  return best;
};

/* Kanten-Magnet beim Ziehen: Rand, Kanten-Ausrichtung mit Nachbarn und Anlegen
   mit Gap. Liefert die gefangene Position {x,y} (mutiert nichts). */
LK.snapXY=function(p,rects,cw,ch,gap,T){
  if(T==null)T=16;
  var xk=[0,cw-p.w], yk=[0,ch-p.h];
  rects.forEach(function(o){
    if(o.id===p.id)return;
    xk.push(o.x, o.x+o.w-p.w, o.x-gap-p.w, o.x+o.w+gap);
    yk.push(o.y, o.y+o.h-p.h, o.y-gap-p.h, o.y+o.h+gap);
  });
  return {x:LK.naechsteKante(p.x,xk,T), y:LK.naechsteKante(p.y,yk,T)};
};

/* Uniforme Skalierung ALLER Rechtecke um (rx,ry) mit Minima-Klemme — Adjazenz
   bleibt, nichts rutscht ins Negative. Mutiert die Objekte (wie das Original). */
LK.skaliere=function(rects,rx,ry,minW,minH){
  rects.forEach(function(p){
    p.x=Math.max(0,Math.round(p.x*rx)); p.y=Math.max(0,Math.round(p.y*ry));
    p.w=Math.max(minW,Math.round(p.w*rx)); p.h=Math.max(minH,Math.round(p.h*ry));
  });
};

/* Reflow nach dem Klemmen (JB-Bild 05.08.2026): skaliere() klemmt Masse auf
   Minima, skaliert die Positionen aber weiter — bei stark verkleinertem
   Viewport rutschen geklemmte Fenster unter ihre Nachbarn (live: breites
   Basis-Layout, Fenster ~530px schmal). Der Reflow behaelt die
   LESE-REIHENFOLGE (y, dann x) und schiebt jedes kollidierende Fenster auf
   den naechsten freien Platz: erst rechts neben den Partner, passt es nicht
   mehr in die Breite, in die naechste Zeile ("dynamisch anpassbar, die
   Anordnung bleibt"). Rundungs-Beruehrungen (<=3px) gelten nicht als
   Kollision, sonst zerlegte der Reflow gap-0-Layouts. Mutiert die Objekte;
   die BASIS des Aufrufers bleibt unangetastet. */
LK.entklemmen=function(rects,cw,gap){
  gap=Math.max(0,gap||0);
  var tol=3;
  function stoert(a,b){
    return a.x<b.x+b.w-tol&&a.x+a.w>b.x+tol&&a.y<b.y+b.h-tol&&a.y+a.h>b.y+tol;
  }
  var fertig=[];
  rects.slice().sort(function(a,b){return (a.y-b.y)||(a.x-b.x);}).forEach(function(p){
    var schutz=0;
    while(schutz++<200){
      var k=null;
      for(var i=0;i<fertig.length;i++){ if(stoert(p,fertig[i])){k=fertig[i];break;} }
      if(!k)break;
      var nx=k.x+k.w+gap;
      if(nx+p.w<=cw){ p.x=nx; }
      else { p.x=0; p.y=k.y+k.h+gap; }
    }
    fertig.push(p);
  });
};

/* Layout in einen Ziel-Viewport einpassen: Bezug = gemerkte Speichergroesse
   (ref) oder — bei Alt-Layouts ohne Bezug — die eigene Bounding-Box. Skaliert
   nur bei Abweichung > schwelle (Default 1%). Rueckgabe: true wenn skaliert. */
LK.passeInViewport=function(rects,ref,ziel,minW,minH,schwelle){
  if(schwelle==null)schwelle=0.01;
  if(!rects||!rects.length||!ziel)return false;
  if(!(ref&&ref.cw>0&&ref.ch>0)){
    var maxR=Math.max.apply(null,rects.map(function(p){return p.x+p.w;}));
    var maxB=Math.max.apply(null,rects.map(function(p){return p.y+p.h;}));
    ref={cw:Math.max(320,maxR), ch:Math.max(320,maxB)};
  }
  var rx=ziel.cw/ref.cw, ry=ziel.ch/ref.ch;
  if(Math.abs(rx-1)>schwelle||Math.abs(ry-1)>schwelle){
    LK.skaliere(rects,rx,ry,minW,minH);
    return true;
  }
  return false;
};

if(typeof module!=="undefined"&&module.exports)module.exports=LK;
if(root)root.LK=LK;
})(typeof window!=="undefined"?window:null);
/*LAYOUT_KERN_END*/
</script>

<script>
/* ================= Helfer & globaler Zustand ================= */
let daten = null;                                    // letzter /api/status (Sekundentakt via laden())

function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML;}
let _toastTimer=null;
function toast(text){                                  // kurze, dezente Rückmeldung (calm — kein Alert-Stopp)
  let t=document.getElementById('toast');
  if(!t){t=document.createElement('div'); t.id='toast';}
  // Fullscreen-Falle (JB 05.08.): der Browser rendert im Vollbild NUR das
  // Fullscreen-Element samt Kindern — ein Toast am <body> wäre im
  // Fernsehmodus/Player-Vollbild unsichtbar. Darum dorthin hängen, wo
  // gerade wirklich gerendert wird.
  const ziel=document.fullscreenElement||document.body;
  if(t.parentNode!==ziel)ziel.appendChild(t);
  t.textContent=text; t.classList.add('an');
  clearTimeout(_toastTimer); _toastTimer=setTimeout(()=>t.classList.remove('an'),2600);
}
function mb(b){if(!b)return'–';if(b>=1e9)return(b/1e9).toFixed(2)+' GB';return(b/1e6).toFixed(1)+' MB';}
function tempo(b){return b?(b/1e6).toFixed(1)+' MB/s':'';}
function zeit(s){if(s==null)return'';s=Math.round(s);const m=Math.floor(s/60),h=Math.floor(m/60);
  if(h)return h+':'+String(m%60).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
  return m+':'+String(s%60).padStart(2,'0');}

/* ---- Looks/Themes: ein „Skin" setzt nur die Farb-Variablen um ---- */
const SKINS=[['terracotta','Terracotta (Nacht)',''],['hell','Hell (Tag)','light'],
  ['hacker','Hacker-Grün','theme-hacker'],['neon','Neon','theme-neon'],['ozean','Ozean','theme-ozean']];
function aktuellerSkin(){
  const h=document.documentElement;
  for(const s of SKINS)if(s[2]&&h.classList.contains(s[2]))return s[0];
  return 'terracotta';
}
function applySkin(name){
  const h=document.documentElement, def=SKINS.find(s=>s[0]===name)||SKINS[0];
  SKINS.forEach(s=>{if(s[2])h.classList.remove(s[2]);});
  if(def[2])h.classList.add(def[2]);
  try{localStorage.setItem('ytdl_skin',def[0]);}catch(e){}
  themeIcon();
  const sel=document.getElementById('opt_skin'); if(sel)sel.value=def[0];
  if(window.vizFarbeAktualisieren)vizFarbeAktualisieren();   // Visualizer folgt dem Akzent
}
function setSkin(name){applySkin(name);}
function themeToggle(){                                 // 🌙/☀ = schneller Tag/Nacht-Wechsel
  applySkin(document.documentElement.classList.contains('light')?'terracotta':'hell');
}
// Vom Dashboard eingebettet (JB 22.07.): dessen Tag/Nacht uebernehmen — nur die Hell-Klasse
// direkt schalten, OHNE die gespeicherte Skin-Wahl (ytdl_skin) zu ueberschreiben (nicht persistent).
window.addEventListener('message',function(e){if(e&&e.data&&e.data.dashTheme)document.documentElement.classList.toggle('light',e.data.dashTheme==='light')});
function themeIcon(){
  const b=document.getElementById('theme');
  if(b)b.textContent=document.documentElement.classList.contains('light')?'☀':'🌙';
}

/* Popover an einem Knopf platzieren und IMMER komplett im Bildschirm halten
   (klappt nach oben, wenn unten kein Platz ist; bleibt links/rechts im Bild). */
function popoverBei(m,r){
  const vw=window.innerWidth, vh=window.innerHeight, w=m.offsetWidth, h=m.offsetHeight;
  const left=Math.max(8, Math.min(r.left, vw-w-8));
  let top=r.bottom+6; if(top+h>vh-8) top=r.top-h-6;     // nach oben klappen
  top=Math.max(8, Math.min(top, vh-h-8));
  m.style.left=left+'px'; m.style.top=top+'px';
  nachVorn(m);                                         // Build 139: zuletzt geoeffnet = oben
  imBlick(m);
}

/* ---- Bildschirm-Wächter (Build 114, JB: „Ansicht geht aus dem Bildschirm
   raus, das darf NIE passieren — weder mobil, noch Desktop, noch Browser").
   Wurzel-Lösung statt Einzelfall-Flicken: jedes schwebende Element wird
   geklemmt (Position + Höchstmaße) UND bei jeder späteren Inhalts-Änderung
   erneut geprüft — genau da riss es vorher (Listen, die nachgeladen werden,
   wuchsen über die berechnete Höhe hinaus). Zu viel Inhalt scrollt IM
   Element, statt aus dem Bild zu laufen (Anti-Scroll-Regel: die Seite
   scrollt nie, nur der Inhalt). ---- */
const SCHWEBEND='.abo-flyout,.panelmenu,.itemmenu,.colmenu,.popover,.modal-box';
/* Info-Zeile der Bibliotheksleiste (Build 139, JB-Fund: „eingereiht (3
   Titel)" stand dauerhaft da, nach F5 war es weg — „war da etwas stuck?").
   Nein: die Meldung wurde gesetzt und NIE zurueckgenommen. Ein Ereignis ist
   vorbei, sobald man es gelesen hat; eine Fortschritts-Meldung („laeuft
   noch") dagegen soll bleiben, bis sie abgeloest wird. Genau diese zwei
   Faelle trennt `bleibt`. */
let _plInfoWeg=null;
function plInfo(text,bleibt){
  const el=document.getElementById('plinfo'); if(!el)return;
  el.textContent=text||'';
  clearTimeout(_plInfoWeg);
  if(text&&!bleibt)_plInfoWeg=setTimeout(()=>{
    const e=document.getElementById('plinfo'); if(e)e.textContent='';},6000);
}

/* Hoechstmasse fuer schwebende Flaechen (Build 139, JB-Wunsch).
   Eine Menue-Spalte wird jenseits von ~1000 px nicht besser lesbar, nur
   breiter - lange Zeilen sind muehsamer zu lesen als kurze. Die Zahlen sind
   deshalb bewusst am Lesbaren orientiert, nicht am verfuegbaren Platz. */
const MAX_FLY={b:1000,h:820};

/* Zuletzt geoeffnetes Fenster liegt oben (Build 139, JB-Fund: der
   Namens-Baukasten verschwand hinter dem Optionen-Menue). Die Ebenen waren
   statisch und willkuerlich verteilt - .abo-flyout 900, .modal 5000,
   .panelmenu 6000, .itemmenu 9000 -, also entschied nicht die Reihenfolge
   des Oeffnens, sondern die Bauart der Flaeche. Ein gemeinsamer Zaehler
   dreht das um: wer zuletzt aufgeht, liegt vorn. Startwert ueber allen
   festen Werten, damit nichts Altes dazwischenfunkt. */
let _flyZ=9500;
function nachVorn(el){ if(el)el.style.zIndex=(++_flyZ); }

function imBlick(el,rand){
  // Kern der Garantie: die HÖCHSTMASSE werden an die POSITION gekoppelt
  // (maxHeight = Platz unter dem Element, maxWidth = Platz rechts davon).
  // Damit kann später nachgeladener Inhalt gar nicht mehr aus dem Bild
  // wachsen — er scrollt innen. Bewusst OHNE ResizeObserver/rAF: die feuern
  // nicht in jeder Umgebung (live nachgemessen: in eingebetteten Ansichten
  // ohne eigene Bildfolge kommt KEINE Meldung an, Build 114).
  if(!el||!el.isConnected)return;
  rand=rand||10;
  const vw=window.innerWidth, vh=window.innerHeight;
  const r=el.getBoundingClientRect();
  let l=parseFloat(el.style.left); if(isNaN(l))l=r.left;
  let t=parseFloat(el.style.top);  if(isNaN(t))t=r.top;
  // Was der Inhalt gerne hätte; passt es unterhalb nicht, erst nach oben
  // rutschen (Platz schaffen) und dann erst deckeln.
  const wunschH=Math.max(el.scrollHeight, r.height), wunschB=Math.max(el.scrollWidth, r.width);
  if(t+wunschH>vh-rand) t=Math.max(rand, vh-rand-wunschH);
  if(l+wunschB>vw-rand) l=Math.max(rand, vw-rand-wunschB);
  t=Math.max(rand, Math.min(t, vh-rand-1));
  l=Math.max(rand, Math.min(l, vw-rand-1));
  el.style.top=t+'px'; el.style.left=l+'px';
  // Build 139 (JB): zusaetzlich eine absolute Obergrenze. Die Kopplung an die
  // Position allein ergibt auf einem Ultrawide im Vollbild ein 3000 px
  // breites Menue - JB: „sie sollten auch eine Standardgroesse haben, nicht
  // unendlich gross werden". Es gilt das KLEINERE von beidem: der Platz, der
  // da ist, und das Mass, das noch lesbar ist.
  el.style.maxHeight=Math.min(vh-t-rand, MAX_FLY.h)+'px';
  el.style.maxWidth=Math.min(vw-l-rand, MAX_FLY.b)+'px';
  if(getComputedStyle(el).overflowY==='visible')el.style.overflowY='auto';
}
function menuAnBody(m,knopf){
  // Build 125: Eine schwebende Fläche gehört an den <body>. Bleibt sie im
  // Baum ihres Knopfes hängen, genügt EIN Vorfahre mit Containment oder
  // transform/filter, und sie sitzt in einem fremden Stapel-Kontext fest —
  // dann hilft kein z-index mehr (live gemessen: 6100 lag unter 14).
  // Der Knopf wird gemerkt, damit Resize sie wieder an ihm ausrichten kann.
  if(m.parentNode!==document.body)document.body.appendChild(m);
  if(knopf)m._anker=knopf;
  if(m._anker&&m._anker.isConnected)popoverBei(m, m._anker.getBoundingClientRect());
}
function menuInsBild(m,rand){
  // Build 119 (JB-Fund): aufklappende Menüs (Ansicht/Spalten) hängen als
  // absolut positionierte Kinder AN ihrem Knopf — sitzt der weit rechts,
  // ragen sie aus dem Fenster. Erst nach links ausrichten; reicht das nicht
  // (Menü breiter als der Platz daneben), wird es freigestellt und vom
  // Bildschirm-Wächter geklemmt. Gilt für alle .colmenu-Menüs.
  if(!m||m.style.display==='none')return;
  rand=rand||10;
  m.style.position=''; m.style.left=''; m.style.right='';
  m.style.top=''; m.style.maxWidth=''; m.style.maxHeight='';
  let r=m.getBoundingClientRect();
  if(r.right>window.innerWidth-rand){                 // nach links ausrichten
    m.style.left='auto'; m.style.right='0';
    r=m.getBoundingClientRect();
  }
  if(r.left<rand||r.right>window.innerWidth-rand||r.bottom>window.innerHeight-rand){
    const merk=r;                                     // Startpunkt merken
    m.style.position='fixed'; m.style.left=merk.left+'px'; m.style.top=merk.top+'px';
    m.style.right='auto';
    imBlick(m,rand);
  }
}
function alleImBlick(){
  document.querySelectorAll(SCHWEBEND).forEach(e=>imBlick(e));
  document.querySelectorAll('.colmenu').forEach(m=>{
    if(m.style.display!=='none')menuAnBody(m);         // Build 125: wieder an den Knopf
  });
}
window.addEventListener('resize',alleImBlick);
document.addEventListener('DOMContentLoaded',alleImBlick);

/* ---- Optionen-Zahnrad (sammelt allgemeine Einstellungen) ---- */
function optionenToggle(ev){
  ev.stopPropagation();
  const alt=document.getElementById('optionen'); if(alt){alt.remove(); return;}
  const m=document.createElement('div'); m.className='panelmenu'; m.id='optionen'; m.style.minWidth='250px';
  const fmin=(daten&&daten.config)?String(daten.config.fehler_ausblenden_min||0):'5';
  m.innerHTML=
    '<div style="font-size:11px;color:#8a7d74;padding:2px 6px 6px">Optionen</div>'+
    '<div class="optrow"><span>Look</span><select id="opt_skin" onchange="setSkin(this.value)">'+
      SKINS.map(s=>'<option value="'+s[0]+'">'+s[1]+'</option>').join('')+'</select></div>'+
    '<div class="optrow" style="display:block"><div style="display:flex;justify-content:space-between">'+
      '<span>Fenster-Abstand</span><span id="gapval">'+fensterAbstand()+' px</span></div>'+
      '<input type="range" min="0" max="24" value="'+fensterAbstand()+'" style="width:100%;margin-top:4px" oninput="setGap(this.value)"></div>'+
    '<div class="optrow"><span>Fehler ausblenden</span>'+
      '<select id="opt_fehler" onchange="setFehlerMin(this.value)">'+
        '<option value="0">nie</option><option value="2">nach 2 min</option>'+
        '<option value="5">nach 5 min</option><option value="15">nach 15 min</option></select></div>'+
    '<div class="optrow"><span>Übergang zwischen Titeln</span><select id="opt_ueb" onchange="setUebergang(this.value)">'+
      '<option value="normal">Standard</option><option value="gapless">Gapless (nahtlos)</option>'+
      '<option value="crossfade">Crossfade (überblenden)</option><option value="automix">Automix (intelligent)</option></select></div>'+
    '<div class="optrow" id="xfrow" style="display:'+((uebergang==='crossfade'||uebergang==='automix')?'block':'none')+'">'+
      '<div style="display:flex;justify-content:space-between;width:100%">'+
      '<span>Überblend-Dauer</span><span id="xfval">'+(crossfadeSek?crossfadeSek+' s':'aus')+'</span></div>'+
      '<input type="range" min="0" max="12" value="'+crossfadeSek+'" style="width:100%;margin-top:4px" oninput="setCrossfade(this.value)"></div>'+
    '<div class="optrow"><span>Lautstärke angleichen</span><label class="chk"><input type="checkbox" id="opt_norm" '+
      (normAn?'checked':'')+' onchange="normSetzen(this.checked)"> Titel gleich laut</label></div>'+
    // Build 130 (JB): 16:9 ist FEST der Standard, damit das Bild beim
    // Titelwechsel nicht springt. Die anderen Verhältnisse stehen als
    // Layout-Option daneben — „Natürlich" heisst ausdrücklich, dass es
    // wieder springen darf.
    // Build 132 (JB): Sprungweite der Pfeiltasten. 5 s ist der Standard, weil
    // YouTube es so macht — belegt in dessen Tastenkürzel-Hilfe.
    // Build 134 (JB Punkt 4): Einfach- oder Doppelklick zum Abspielen.
    '<div class="optrow"><span>Abspielen per</span><select id="opt_klick" onchange="klickArtSetzen(this.value)" '+
      'title="Doppelklick stört die Auswahl nicht — Einfachklick ist schneller">'+
      '<option value="doppel">Doppelklick</option><option value="einfach">Einfachklick</option></select></div>'+
    // Build 144 (JB Punkt 7): In der Playlist teilen sich Rahmen-Auswahl und
    // Umsortieren dieselben Zeilen — eine Liste hat keine freie Fläche.
    // Standard „ab der Zeile": markierte Titel greift man zum Verschieben,
    // auf allen anderen zieht man einen Rahmen auf (Explorer-Muster).
    '<div class="optrow"><span>Playlist-Rahmen</span><select id="opt_plqrahmen" onchange="plqRahmenArtSetzen(this.value)" '+
      'title="Ab der Zeile: markierte Titel bleiben zum Verschieben greifbar · Nur auf freier Fläche: Ziehen hat überall Vorrang (Stand vor Build 144)">'+
      '<option value="auto">ab der Zeile</option><option value="frei">nur auf freier Fläche</option></select></div>'+
    '<div class="optrow"><span>Pfeiltasten springen</span><span><input type="number" id="opt_sprung" min="1" max="60" '+
      'style="width:56px" onchange="sprungWeiteSetzen(this.value)" title="Sekunden pro Druck auf ←/→ (J/L bleiben bei 10 s)"> s</span></div>'+
    '<div class="optrow"><span>Seitenverhältnis</span><select id="opt_ar" onchange="seitenverhaeltnisSetzen(this.value)">'+
      PL_AR.map(a=>'<option value="'+a[0]+'">'+a[1]+'</option>').join('')+'</select></div>'+
    '<div class="optrow"><span>Canvas-Hintergrund</span><label class="chk"><input type="checkbox" id="opt_canvas" '+
      (canvasAn?'checked':'')+' onchange="setCanvas(this.checked)"> animiertes Cover</label></div>'+
    // Untertitel-Stil (JB 05.08., wie Amazon/Netflix): Größe fürs Sofa/TV,
    // Preset für die Optik — gilt für Untertitel-Zeilen UND Karaoke-Größe.
    // Modus inkl. TRANSKRIPT lebt hier (JB 05.08.: im Player-Panel nur noch
    // aus/Untertitel/Karaoke — Taste S wechselt weiter durch alle vier).
    '<div class="optrow"><span>Untertitel-Modus</span><select id="opt_submode" onchange="subModusSetzen(this.value)">'+
      '<option value="aus">aus</option><option value="zeilen">Untertitel</option>'+
      '<option value="karaoke">Karaoke</option><option value="transkript">Transkript</option></select></div>'+
    '<div class="optrow"><span>Untertitel-Darstellung</span><button class="btn mini" onclick="subMenu(event)" '+
      'title="Größe, Schrift, Farben, Schatten, Hintergrund, Versatz — mit Live-Vorschau (Disney-Muster)">💬 einstellen…</button></div>'+
    '<div class="optrow"><span>Sleep-Timer</span><span><select id="opt_sleep" onchange="sleepSetzen(this.value)">'+
      '<option value="0">aus</option><option value="15">15 min</option><option value="30">30 min</option>'+
      '<option value="60">60 min</option><option value="titel">nach diesem Titel</option></select>'+
      '<span id="sleepval" style="color:#8a7d74;font-size:11px;margin-left:6px"></span></span></div>'+
    '<div class="optrow"><span>Dateinamen</span><button class="btn mini" onclick="namenFenster()" title="Bausteine wählen und schieben, Probelauf ansehen, anwenden oder zurücknehmen">🏷 Namens-Baukasten</button></div>'+
    // Etappe C (Spec Punkt 5): globale Grundeinstellungen — unterste geteilte
    // Ebene; Playlist- und Titel-Regeln gehen vor (drei Ebenen, JB 23.07.).
    '<div class="optrow"><span>Wiedergabe-Standard</span><button class="btn mini" onclick="wgGlobalDialog()" '+
      'title="Untertitel/Karaoke, Geschwindigkeit und (vorbereitet) Ton-Sprache als Standard für alle Titel — Playlist- und Titel-Regeln gehen vor">🎚 ändern…</button></div>'+
    '<div class="optrow"><span>Player-Tasten</span><button class="btn mini" onclick="hotkeyEditor()" '+
      'title="Tastenkürzel des Players selbst belegen — ? zeigt die Legende mit der aktuellen Belegung">⌨ Hotkeys…</button></div>'+
    // Build 125: Der Zähler weicht in schmalen Fenstern aus der Kopfleiste
    // (Ausweich-Ordnung). Damit „ausgeblendet ≠ unerreichbar" nicht an einer
    // Breiten-Regel hängt, steht er hier IMMER — bei jeder Fenstergröße.
    '<div class="optrow"><span>Geladen</span><span style="color:var(--akz2);font-weight:700">'+
      (document.getElementById('counter_num')||{textContent:'0'}).textContent+'</span></div>'+
    // Build 127: Die Link-Umschalter sind wieder raus — ohne „immer so"-Haken
    // gibt es nichts umzustellen, und ein Schalter für etwas, das immer
    // gefragt wird, wäre ein Knopf ohne Aufgabe (JB: wenige Knöpfe).
    '<div class="optrow"><span>Alle Einstellungen</span><button class="btn mini" onclick="einstellungenOeffnen()">⚙ Öffnen</button></div>'+
    // JB 05.08.: Fernsehmodus auch HIER — er betrifft den Player, also gehört
    // er zusätzlich in dessen Optionen (Ansicht-Menü hat ihn ebenfalls, oben).
    '<div class="optrow"><span>📺 Fernsehmodus</span><button class="btn mini" onclick="fernsehModus()">Start</button></div>'+
    '<div class="optrow"><span>📱 Fernsteuerung</span><button class="btn mini" id="fernbtn" onclick="fernToggle()">…</button></div>'+
    // Teilprojekt 3: Geräte koppeln (QR/Code) + freigeben/trennen — nur am PC.
    '<div class="optrow"><span>📺 Geräte (TV/Handy)</span><button class="btn mini" onclick="geraeteDialog()">Koppeln…</button></div>'+
    '<div id="ferninfo" style="font-size:11px;color:#8a7d74;padding:0 8px 6px"></div>';
  document.body.appendChild(m);
  const sel=m.querySelector('#opt_fehler'); if(sel)sel.value=fmin;
  const ar=m.querySelector('#opt_ar');
  if(ar){try{ar.value=localStorage.getItem('ytdl_ar')||'16/9';}catch(e){ar.value='16/9';}}
  const sp=m.querySelector('#opt_sprung'); if(sp)sp.value=sprungWeite();
  const kl=m.querySelector('#opt_klick'); if(kl)kl.value=klickArt();
  const pr=m.querySelector('#opt_plqrahmen'); if(pr)pr.value=plqRahmenArt();
  const sk=m.querySelector('#opt_skin'); if(sk)sk.value=aktuellerSkin();
  const slp=m.querySelector('#opt_sleep'); if(slp)slp.value=sleepTitelende?'titel':'0'; sleepLabel();
  const ub=m.querySelector('#opt_ueb'); if(ub)ub.value=uebergang;
  subStilInit();                                       // Untertitel-Stil-Selects mit gemerktem Stand
  fernInfoMalen();
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  setTimeout(()=>document.addEventListener('pointerdown',function zu(e2){
    if(!m.contains(e2.target)&&e2.target.id!=='optbtn'){m.remove(); document.removeEventListener('pointerdown',zu);}},true),0);
}
function setGap(v){try{localStorage.setItem('ytdl_gap',v);}catch(e){} const g=document.getElementById('gapval'); if(g)g.textContent=v+' px';}
async function setFehlerMin(v){
  try{await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fehler_ausblenden_min:parseInt(v,10)})});}catch(e){}
}

/* ================= Panels / Docking ================= */
const VIEWS={add:'➕ Hinzufügen', queue:'⬇ Downloads', done:'✅ Fertig', log:'📜 Log', lib:'📚 Bibliothek', player:'▶ Player', plq:'🎶 Playlist', abos:'📡 Abos', filme:'🎬 Filme'};
const DLV=['queue','done','log','abos'];             // Download-Views: fest im dlbox (normal) / Canvas-Panel (mini). Hinzufügen läuft über „Link einfügen" oben
const DLACTION={queue:["📂 Zielordner","aktion('','ordner_offen')"],
                done:["🧹 Aufräumen","aktion('','queue_aufraeumen')"],
                log:["Leeren","logLeeren()"], abos:["🔄 Jetzt prüfen","aboPruefen(this)"]};
let dlboxAktiv='queue';
function dlboxTab(v){ if(!DLV.includes(v))return; dlboxAktiv=v; dlboxRender(); }
function abosZeigen(){                                 // 📡: Abos-Reiter zeigen (normal im dlbox, mini im mdl-Fenster)
  if(miniAn){const p=L.panels.find(x=>(x.views||[]).includes('abos')); if(p){p.active='abos'; renderPanels();} aboLaden(); return;}
  dlboxTab('abos'); aboLaden();
}
function dlboxRender(){
  const box=document.getElementById('dlbox'), body=document.getElementById('dlbox-body');
  const tabs=document.getElementById('dlbox-tabs'), cm=document.getElementById('cmd-mini');
  if(!box||!body)return;
  if(miniAn){
    // Mini: Download-Views leben im Canvas; das eingebettete Fenster wird zum
    // Mini-Player (oben, eingebettet, überdeckt nichts — JB 21.07.).
    if(tabs)tabs.style.display='none'; body.style.display='none';
    const pl=document.getElementById('view-player');
    if(cm&&pl&&pl.parentNode!==cm)cm.appendChild(pl);
    return;
  }
  if(tabs)tabs.style.display=''; body.style.display=''; if(cm)cm.innerHTML='';
  document.querySelectorAll('#dlbox-tabs .dlbox-tab').forEach(t=>t.classList.toggle('an',t.dataset.dlt===dlboxAktiv));
  const act=document.getElementById('dlbox-action'), a=DLACTION[dlboxAktiv];   // Aktion oben in der Reiter-Leiste
  if(act&&a){act.textContent=a[0]; act.setAttribute('onclick',a[1]); act.style.display='';}
  else if(act)act.style.display='none';
  const stash=document.getElementById('stash');
  DLV.forEach(v=>{if(v!==dlboxAktiv){const n=document.getElementById('view-'+v); if(n&&n.parentNode===body)stash.appendChild(n);}});
  const node=document.getElementById('view-'+dlboxAktiv);
  if(node&&node.parentNode!==body)body.appendChild(node);
  if(dlboxAktiv==='abos')aboLaden();
}
const LKEY='ytdl_layout_v5';
let L=ladeLayout(), libTimer=null;

function defaultLayout(){
  // Füllt den Bildschirm: Höhe aus dem Fenster statt fixer 660px (JB 14.07.:
  // „Vorlagen schlagen alte Größen vor"), Abstände = eingestellter Gap (Standard 0).
  const W=window.innerWidth, g=Math.max(0,fensterAbstand());
  const bw=Math.max(320, W-16), H=_canvasH();          // Panels füllen genau den Canvas (kein Seiten-Scroll)
  // Downloads (Hinzufügen/Warteschlange/Fertig/Log) leben jetzt fest eingebettet
  // in der Command-Bar (#dlbox) — der Canvas trägt nur noch Bibliothek + Player
  // (JB 21.07.). Bibliothek ist die Hauptfläche, Player als Spalte rechts.
  if(W>1180){
    const plW=Math.max(340, Math.round(bw*0.33));
    const libW=bw-plW-g;
    return {z:30,panels:[
      {id:'p4',x:8,          y:8, w:libW, h:H, views:['lib'],    active:'lib',    zi:14},
      {id:'p5',x:8+libW+g,   y:8, w:plW,  h:H, views:['player'], active:'player', zi:15},
    ]};
  }
  if(W>760){
    return {z:20,panels:[
      {id:'p4',x:8, y:8, w:bw, h:H, views:['lib','player'], active:'lib', zi:14},
    ]};
  }
  return {z:12,panels:[
    {id:'p4',x:8,y:8,w:bw,h:H,views:['lib','player'],active:'lib',zi:11},
  ]};
}
function ladeLayout(){
  try{localStorage.removeItem('ytdl_layout_vormini');}catch(e){}   // frischer Start = kein Mini-Rest
  try{const s=JSON.parse(localStorage.getItem(LKEY)||'null');
    if(s&&s.panels){
      delete s.mini;                                 // Mini-Layout nie als Hauptlayout übernehmen
      s.panels=s.panels.filter(p=>!['pmini','mlib','mplq','mdl'].includes(p.id));   // Mini-Fenster nie mitladen
      // Migration (JB 21.07.): Download-Views leben jetzt im festen dlbox, nicht
      // mehr im Canvas — aus Alt-Layouts entfernen, leere Fenster fallen weg.
      s.panels.forEach(p=>{p.views=(p.views||[]).filter(v=>!DLV.includes(v)); if(!p.views.includes(p.active))p.active=p.views[0];});
      s.panels=s.panels.filter(p=>p.views&&p.views.length);
      // Reload während Mini: der Player hing in der Mini-Karte — als Tab ins
      // größte Fenster zurück, sonst legt ensurePlayer später ein neues Fenster an
      if(s.panels.length&&!s.panels.some(p=>(p.views||[]).includes('player'))){
        const g=s.panels.reduce((a,b)=>(a.w*a.h>=b.w*b.h?a:b));
        (g.views=g.views||[]).push('player');
      }
    }
    if(s&&s.panels&&s.panels.length&&alleViews(s))return s;}catch(e){}
  return defaultLayout();
}
function alleViews(s){
  const drin=new Set(); s.panels.forEach(p=>(p.views||[]).forEach(v=>drin.add(v)));
  return drin.has('lib');   // Kern: Bibliothek (Downloads sind fest im dlbox)
}
function ensurePlayer(){
  if(miniAn){renderPanels(); return null;}             // Mini: Player sitzt eingebettet in #cmd-mini
  let p=L.panels.find(pp=>pp.views.includes('player'));
  if(!p){
    const r=document.getElementById('canvas').getBoundingClientRect();
    // kollisionsfrei platzieren (JB-Fund 14.07.: fixe Position 120/70 lag über der Bibliothek)
    const w=Math.min(420,Math.max(300,Math.round(r.width)-16)), h=540;
    const pos=freiePosition(w,h,Math.max(8,Math.round(r.width)-w-8),8);
    p={id:'p'+(++L.z),x:pos.x,y:pos.y,w,h,views:['player'],active:'player',zi:++L.z};
    L.panels.push(p);
  }
  p.active='player'; bringFront(p); merkeView(p.id,'player'); renderPanels(); return p;
}
function ensureView(view){
  // Eine Ansicht sichtbar machen: existiert sie als Tab, nach vorn holen — sonst
  // ein neues Fenster SICHTBAR oben öffnen (überlappt kurz, per bringFront vorn;
  // freiePosition würde es bei vollem Canvas unter den Falz schieben, JB-Fund 21.07.).
  let p=L.panels.find(pp=>pp.views.includes(view));
  if(!p){
    const r=document.getElementById('canvas').getBoundingClientRect();
    const w=Math.min(560,Math.max(340,Math.round(r.width)-16));
    const h=Math.min(620,Math.max(360,Math.round(r.height)-16));
    const x=Math.max(8,Math.round((r.width-w)/2));      // mittig, im sichtbaren Bereich
    p={id:'p'+(++L.z),x,y:16,w,h,views:[view],active:view,zi:++L.z};
    L.panels.push(p);
  }
  p.active=view; bringFront(p); merkeView(p.id,view); renderPanels();
  const el=panelEl(p.id); if(el)el.scrollIntoView({block:'nearest',behavior:'smooth'});
  return p;
}
function _geoSig(){return JSON.stringify((L&&L.panels||[]).map(p=>[p.id,p.x,p.y,p.w,p.h]));}
function saveLayout(){
  if(L&&L.mini)return;                                 // Mini ist transient — nie als Hauptlayout speichern
  // Basis-Anker (Build 92, JB-Fund „alles ein wenig bewegt"): NUR eine ECHTE
  // Geometrie-Änderung (Ziehen/Resize/Docken/Vorlage) wird zur neuen Wahrheit.
  // Auto-Projektionen (Reload/Fenster-Resize) speichern sonst gerundete Pixel
  // übers Original — jeder Zyklus driftet 1-2 px, über Tage wandert alles.
  const sig=_geoSig();
  if(_autoProj){_autoProj=false;}
  else if(sig!==_lastSig&&!miniAn){
    const m=_vpMasse();
    if(m){L.basis={vp:m,panels:L.panels.map(p=>({id:p.id,x:p.x,y:p.y,w:p.w,h:p.h}))}; L.vp=m;}
  }
  _lastSig=sig;
  try{localStorage.setItem(LKEY,JSON.stringify(L));}catch(e){}
}
function layoutReset(){layoutMerken();L=defaultLayout();renderPanels();}
function panelEl(id){return document.querySelector('.panel[data-id="'+id+'"]');}
function bringFront(p){p.zi=++L.z;const el=panelEl(p.id);if(el)el.style.zIndex=p.zi;}

function renderPanels(){
  const canvas=document.getElementById('canvas'), stash=document.getElementById('stash');
  Object.keys(VIEWS).forEach(v=>{const n=document.getElementById('view-'+v); if(n.parentNode!==stash)stash.appendChild(n);});
  const ids=L.panels.map(p=>p.id);
  [...canvas.querySelectorAll('.panel')].forEach(el=>{if(!ids.includes(el.dataset.id))el.remove();});
  L.panels.forEach(p=>{
    if(!p.views.includes(p.active))p.active=p.views[0];
    let el=panelEl(p.id);
    if(!el){
      el=document.createElement('div'); el.className='panel'; el.dataset.id=p.id;
      el.innerHTML='<div class="panel-head"><div class="panel-tabs"></div>'+
                   '<button class="panel-menu" title="Fenster-Menü: andocken, herauslösen, aufräumen">⋯</button></div>'+
                   '<div class="panel-body"></div>'+
                   ['n','s','e','w','ne','nw','se','sw'].map(r=>`<div class="rgriff r-${r}" data-r="${r}"></div>`).join('');
      canvas.appendChild(el);
      bindPanel(el,p.id);
    }
    el.style.left=p.x+'px'; el.style.top=p.y+'px'; el.style.width=p.w+'px'; el.style.height=p.h+'px'; el.style.zIndex=p.zi||10;
    const tabsEl=el.querySelector('.panel-tabs');
    tabsEl.innerHTML=p.views.map(v=>`<button class="ptab ${v===p.active?'an':''}" data-view="${v}">${VIEWS[v]}</button>`).join('');
    [...tabsEl.querySelectorAll('.ptab')].forEach(t=>bindTab(t,p.id));
    const body=el.querySelector('.panel-body'), node=document.getElementById('view-'+p.active);
    if(node.parentNode!==body)body.appendChild(node);
  });
  const libSichtbar=L.panels.some(p=>p.active==='lib');
  if(libSichtbar){if(!libTimer){libLaden();libTimer=setInterval(libPoll,5000);}}
  else{clearInterval(libTimer);libTimer=null;}
  if(L.panels.some(p=>p.active==='abos'))aboLaden();   // Abo-Fenster sichtbar -> Stand auffrischen
  if(L.panels.some(p=>p.active==='filme'))filmeLaden(); // Filme-Fenster sichtbar -> Reihen laden
  // Playlist als eigenes Fenster? Dann blendet der Player seine Seitenliste aus.
  const plqExtern=L.panels.some(p=>p.views.includes('plq'));
  document.body.classList.toggle('plq-extern',plqExtern);
  const pb=document.getElementById('plq-btn'); if(pb)pb.classList.toggle('an',plqExtern);
  dlboxRender();                                       // Download-Views ins feste Fenster (normal) hosten
  renderPlayerQueue();
  saveLayout();
}
/* Fenster-Resize (JB 22.07.): die Canvas-Fenster (Bibliothek/Player/…) wachsen
   proportional mit — kein manuelles Layout-Neuwählen mehr. Alle Kanten skalieren
   gleich, Adjazenz bleibt (keine Lücken/Überlappungen). Eingebettete Command-Bar-
   Fenster regelt das CSS selbst. */
let _autoProj=false, _lastSig='', _resizeT=null;
function _canvasH(){                                    // nutzbare Canvas-Höhe (Seite scrollt nicht)
  const c=document.getElementById('canvas');
  return Math.max(320, (c&&c.clientHeight?c.clientHeight:window.innerHeight-210) - 16);
}
function _vpMasse(){
  const c=document.getElementById('canvas'); if(!c)return null;
  return {cw:Math.max(320, c.clientWidth-20), ch:Math.max(320, c.clientHeight-16)};
}
function canvasAnpassen(){
  // Vollbild loest SELBST ein resize aus (Build 97, JB: „geht sofort wieder
  // raus") — renderPanels haengt die Views kurz in den Stash um, und ein
  // Element, das den DOM verlaesst, beendet das Vollbild augenblicklich.
  // Waehrend Vollbild: nichts umbauen; beim Verlassen kommt das naechste
  // resize und passt normal an.
  if(document.fullscreenElement)return;
  if(miniAn){ L=miniLayoutBauen(); renderPanels(); return; }
  const m=_vpMasse(); if(!m)return;
  if(L.vp&&Math.abs(m.cw/L.vp.cw-1)<0.008&&Math.abs(m.ch/L.vp.ch-1)<0.008)return;   // kaum Änderung seit letzter Projektion
  _autoProj=true; layoutProjizieren(); renderPanels();
}
/* Anzeige = Projektion der BASIS auf den aktuellen Viewport (Build 92).
   Vorher skalierten Reload/Resize das Layout inkrementell und speicherten die
   gerundeten Pixel sofort zurück — messbar 1-2 px Drift JE Zyklus (Extremfall:
   Laden im 0-Viewport quetschte alles auf die 320er-Minima und zementierte das).
   Jetzt bleibt die vom Nutzer gebaute Anordnung als L.basis unangetastet stehen;
   jede Anpassung rechnet EINMAL von dieser Basis (Mathe: layout_kern) — Fenster
   hin- und herziehen oder neu laden landet wieder EXAKT auf den alten Kanten. */
function layoutProjizieren(){
  if(miniAn)return;
  const m=_vpMasse(); if(!m||!L||!L.panels||!L.panels.length)return;
  if(!(L.basis&&L.basis.vp&&L.basis.vp.cw>0&&L.basis.vp.ch>0&&L.basis.panels&&L.basis.panels.length)){
    let ref=(L.vp&&L.vp.cw>0&&L.vp.ch>0)?L.vp:null;    // Alt-Layout ohne Basis: einmalig verankern
    if(!ref){
      const maxR=Math.max.apply(null,L.panels.map(p=>p.x+p.w));
      const maxB=Math.max.apply(null,L.panels.map(p=>p.y+p.h));
      ref={cw:Math.max(320,maxR), ch:Math.max(320,maxB)};
    }
    L.basis={vp:ref, panels:L.panels.map(p=>({id:p.id,x:p.x,y:p.y,w:p.w,h:p.h}))};
  }
  const b=L.basis, kopie=b.panels.map(g=>({id:g.id,x:g.x,y:g.y,w:g.w,h:g.h}));
  LK.skaliere(kopie, m.cw/b.vp.cw, m.ch/b.vp.ch, 220, 160);
  // JB-Bild 05.08.: die Minima-Klemme schob geklemmte Fenster unter ihre
  // Nachbarn (schmales Fenster + breite Basis). Der Reflow ordnet NUR die
  // Projektion — die Basis (JBs gebaute Anordnung) bleibt unangetastet.
  LK.entklemmen(kopie, m.cw, Math.max(0,fensterAbstand()));
  L.panels.forEach(p=>{const g=kopie.find(x=>x.id===p.id); if(g){p.x=g.x; p.y=g.y; p.w=g.w; p.h=g.h;}});
  L.vp=m;
}
function layoutAnViewport(){_autoProj=true; layoutProjizieren();}
window.addEventListener('resize',()=>{clearTimeout(_resizeT); _resizeT=setTimeout(canvasAnpassen,90);});

/* ---- Ansicht-Verlauf: Mausrad links = zurück (Vergangenheit), rechts = vor (Gegenwart).
   Springt zu der Ansicht, in der man vorher war — auch über Fenster hinweg
   (z.B. Video -> direkt zurück in die Bibliothek). ---- */
let viewHist=[], viewPos=-1, histSperre=false, histWheelTs=0;
function merkeView(pid,view){
  if(histSperre)return;
  const cur=viewHist[viewPos];
  if(cur&&cur.pid===pid&&cur.view===view)return;      // gleiche Station nicht doppelt
  viewHist=viewHist.slice(0,viewPos+1); viewHist.push({pid,view});
  if(viewHist.length>60)viewHist.shift();
  viewPos=viewHist.length-1;
}
function histSpring(d){
  for(let np=viewPos+d; np>=0&&np<viewHist.length; np+=d){
    const h=viewHist[np], p=L.panels.find(x=>x.id===h.pid);
    if(p&&p.views.includes(h.view)){                  // Station existiert noch?
      viewPos=np; histSperre=true;
      p.active=h.view; bringFront(p); renderPanels(); histSperre=false; return;
    }
  }
}
function hatHScroll(el){                              // echtes horizontales Scrollen nicht kapern
  for(let n=el; n&&n.nodeType===1&&n!==document.body; n=n.parentElement){
    if(n.scrollWidth>n.clientWidth+4){const o=getComputedStyle(n).overflowX; if(o==='auto'||o==='scroll')return true;}
  }
  return false;
}
window.addEventListener('wheel',e=>{
  if(Math.abs(e.deltaX)<=Math.abs(e.deltaY)||Math.abs(e.deltaX)<12)return;
  if(hatHScroll(e.target))return;
  if(Date.now()-histWheelTs<250)return; histWheelTs=Date.now();   // ein Sprung je Kipp-Geste
  e.preventDefault();
  histSpring(e.deltaX<0?-1:1);
},{passive:false});

function bindPanel(el,id){
  el.addEventListener('pointerdown',()=>{const p=L.panels.find(x=>x.id===id);if(p){bringFront(p); merkeView(id,p.active);}},true);
  el.querySelector('.panel-head').addEventListener('pointerdown',e=>{
    if(e.target.closest('.ptab')||e.target.closest('.panel-menu'))return;  // eigene Logik
    const p=L.panels.find(x=>x.id===id); if(p)startMove(el,p,e);
  });
  el.querySelector('.panel-menu').addEventListener('click',e=>{e.stopPropagation(); panelMenu(id,e.currentTarget);});
  el.querySelectorAll('.rgriff').forEach(g=>g.addEventListener('pointerdown',e=>{
    e.stopPropagation(); const p=L.panels.find(x=>x.id===id); if(p)startResize(el,p,e,g.dataset.r);
  }));
}

function panelMenu(id,btn){
  document.querySelectorAll('.panelmenu').forEach(m=>m.remove());
  const p=L.panels.find(x=>x.id===id); if(!p)return;
  const eintraege=[];
  L.panels.filter(o=>o.id!==id).forEach(o=>
    eintraege.push(['⧉ Andocken an „'+o.views.map(v=>VIEWS[v]).join(' / ')+'"', ()=>dockPanel(id,o.id)]));
  if(p.views.length>1)
    eintraege.push(['⇱ Aktiven Tab herauslösen', ()=>tearOut(id,p.active,90,90)]);
  eintraege.push(['▦ Alle Fenster aufräumen', ()=>layoutAufraeumen()]);
  const m=document.createElement('div'); m.className='panelmenu';
  m.innerHTML=eintraege.map((e,i)=>`<button data-i="${i}">${esc(e[0])}</button>`).join('');
  document.body.appendChild(m);
  const r=btn.getBoundingClientRect();
  m.style.left=Math.min(r.left, window.innerWidth-m.offsetWidth-8)+'px';
  m.style.top=(r.bottom+4)+'px';
  m.querySelectorAll('button').forEach(b=>b.onclick=()=>{eintraege[+b.dataset.i][1](); m.remove();});
  setTimeout(()=>document.addEventListener('pointerdown',function zu(ev){
    if(!m.contains(ev.target)){m.remove(); document.removeEventListener('pointerdown',zu);}},true),0);
}

/* ---- Verlust-Schutz (JB 13.07.2026, wie im Dashboard — ein System): vor jedem Layout-
   Wechsel (Vorlage, eigenes Layout, Aufräumen, Reset) wird die aktuelle Anordnung gemerkt.
   ↩ Vorheriges TAUSCHT mit der gemerkten -> nochmal ↩ wechselt wieder vor.
   Nichts geht mit EINEM Klick verloren. ---- */
const LPREV='ytdl_layout_prev_v1';
function layoutMerken(){try{localStorage.setItem(LPREV,JSON.stringify(L));}catch(e){}}
function layoutVorheriges(){
  let prev=null; try{prev=JSON.parse(localStorage.getItem(LPREV)||'null');}catch(e){}
  if(prev&&prev.panels)prev.panels=prev.panels.filter(p=>p.id!=='pmini');
  if(!prev||!prev.panels||!prev.panels.length){alert('Noch kein vorheriges Layout gemerkt — es wird bei jedem Layout-Wechsel automatisch gesichert.');return;}
  miniVerlassen();
  const cur=JSON.stringify(L);
  L=prev; renderPanels(); saveLayout();
  try{localStorage.setItem(LPREV,cur);}catch(e){}
}

/* ---- Layout-Vorlagen ---- */
function layoutAufraeumen(){
  layoutMerken();
  const bw=Math.max(320,window.innerWidth-20), n=L.panels.length||1;
  const cols=Math.min(n, bw>1180?3:(bw>760?2:1)), rows=Math.ceil(n/cols), gap=Math.max(10,fensterAbstand());
  const cw=Math.floor((bw-(cols-1)*gap)/cols);
  const ch=Math.max(200, Math.floor((_canvasH()-(rows-1)*gap)/rows));
  L.panels.forEach((p,i)=>{const c=i%cols, r=Math.floor(i/cols);
    p.x=10+c*(cw+gap); p.y=8+r*(ch+gap); p.w=cw; p.h=ch;});
  renderPanels();
}
function layoutVorlage(name){
  layoutMerken(); miniVerlassen();
  const bw=Math.max(320,window.innerWidth-16);
  if(name==='youtube'){
    // Bildschirm füllend, Abstände = Gap (Standard 0) — keine alten Festmaße mehr
    const g=Math.max(0,fensterAbstand());
    const vidW=Math.round(bw*0.60), sideW=bw-vidW-g, H2=_canvasH();
    L={z:40,panels:[
      {id:'p1',x:8,y:8,w:vidW,h:H2,views:['player'],active:'player',zi:14},
      {id:'p3',x:8+vidW+g,y:8,w:sideW-8,h:H2,views:['lib'],active:'lib',zi:15},
    ]};
  }else if(name==='tabs'){
    L={z:20,panels:[{id:'p1',x:8,y:8,w:bw,h:_canvasH(),
      views:['lib','player'],active:'lib',zi:11}]};
  }else{ L=defaultLayout(); }
  renderPanels();
}

/* ---- Eigene Layouts speichern/laden (localStorage) ---- */
function meineLayouts(){try{return JSON.parse(localStorage.getItem('ytdl_layouts_v1'))||{};}catch(e){return {};}}
function layoutSelectFuellen(){
  const sel=document.getElementById('layoutsel'); if(!sel)return;
  const eigene=meineLayouts();
  sel.innerHTML='<optgroup label="Vorlagen">'+
      '<option value="v:standard">Standard</option>'+
      '<option value="v:youtube">YouTube-Stil (Video groß)</option>'+
      '<option value="v:tabs">Alles als Tabs</option></optgroup>'+
    (Object.keys(eigene).length?('<optgroup label="Meine Layouts">'+
      Object.keys(eigene).sort().map(n=>`<option value="m:${esc(n)}">${esc(n)}</option>`).join('')+'</optgroup>'):'');
  // zuletzt gewählte Anordnung im Select anzeigen (überlebt den Reload, JB 14.07.)
  try{const merk=localStorage.getItem('ytdl_layout_wahl');
    if(merk&&[...sel.options].some(o=>o.value===merk))sel.value=merk;}catch(e){}
}
function layoutWaehlen(v){
  if(!v)return;
  try{localStorage.setItem('ytdl_layout_wahl',v);}catch(e){}
  if(v.startsWith('v:'))layoutVorlage(v.slice(2));
  else if(v.startsWith('m:')){const l=meineLayouts()[v.slice(2)];
    if(l){layoutMerken(); miniVerlassen(); L=JSON.parse(JSON.stringify(l));
      L.panels=L.panels.filter(p=>p.id!=='pmini'); layoutAnViewport(); renderPanels(); saveLayout();}}
}
function layoutSpeichern(){
  const n=prompt('Name für diese Fenster-Anordnung:'); if(!n||!n.trim())return;
  const eigene=meineLayouts(); eigene[n.trim()]=JSON.parse(JSON.stringify(L));
  try{localStorage.setItem('ytdl_layouts_v1',JSON.stringify(eigene));}catch(e){}
  layoutSelectFuellen(); document.getElementById('layoutsel').value='m:'+n.trim();
}
function layoutLoeschen(){
  const sel=document.getElementById('layoutsel'), v=sel.value;
  if(!v.startsWith('m:')){alert('Bitte oben eines DEINER gespeicherten Layouts wählen.');return;}
  const name=v.slice(2); if(!confirm('Layout „'+name+'" löschen?'))return;
  const eigene=meineLayouts(); delete eigene[name];
  try{localStorage.setItem('ytdl_layouts_v1',JSON.stringify(eigene));}catch(e){}
  layoutSelectFuellen();
}

/* ---- Mini-Player-Modus (JB 21.07.): Player schrumpft zur kleinen Karte oben
   rechts, und der Bildschirm wird zur Hör-Arbeitsfläche — Bibliothek füllt
   links, die Playlist-Warteschlange steht als schmale Spalte rechts darunter
   (Spotify/Plexamp-Muster: „Now Playing"-Queue rechts). Das Vor-Mini-Layout
   wird gemerkt und beim Zurückschalten exakt wiederhergestellt. ---- */
let miniAn=false, miniVor=null;
const VORMINI='ytdl_layout_vormini';
function miniLayoutBauen(){
  const c=document.getElementById('canvas');
  const cw=(c?c.clientWidth:window.innerWidth)||window.innerWidth;
  const ch=Math.max(360,(c?c.clientHeight:window.innerHeight-96)||520);
  const g=Math.max(0,fensterAbstand());
  const mw=Math.min(380,Math.max(240,cw-16));         // Breite der Mini-Karte = Breite der Playlist-Spalte
  // übrige Views (nicht player/plq/Downloads) als Tabs auf das große Bibliotheks-
  // Fenster — die Download-Views bekommen ihr eigenes Fenster (mdl, unter der Playlist).
  const rest=[]; (miniVor?miniVor.panels:L.panels).forEach(p=>(p.views||[]).forEach(v=>{
    if(v!=='player'&&v!=='plq'&&!DLV.includes(v)&&!rest.includes(v))rest.push(v);}));
  if(!rest.includes('lib'))rest.unshift('lib');
  const libViews=['lib',...rest.filter(v=>v!=='lib')];
  const libW=Math.max(240,cw-mw-g-16);
  // Mini-Layout (JB 21.07.): Bibliothek links groß; rechts als Spalte die
  // Playlist OBEN und darunter das gelöste Download-Fenster (gestapelt). Die
  // Mini-Karte ist position:fixed oben rechts (über der Command-Bar).
  const oben=Math.round((ch-16-g)*0.5);               // Playlist obere Hälfte
  // Kein pmini-Fenster mehr: der Mini-Player sitzt eingebettet oben in der
  // Command-Bar (#cmd-mini) und überdeckt nichts (JB 21.07.).
  return {z:60,mini:true,panels:[
    {id:'mlib',x:8,y:8,w:libW,h:ch-16,views:libViews,active:'lib',zi:20},
    {id:'mplq',x:8+libW+g,y:8,w:mw,h:oben,views:['plq'],active:'plq',zi:21},
    {id:'mdl', x:8+libW+g,y:8+oben+g,w:mw,h:ch-16-oben-g,views:['queue','done','log','abos'],active:'queue',zi:22},
  ]};
}
function miniToggle(){
  const b=document.getElementById('mini-btn');
  if(!miniAn){
    miniVor=JSON.parse(JSON.stringify(L));             // echtes Layout merken (Session + Reload-Fallback)
    try{localStorage.setItem(VORMINI,JSON.stringify(miniVor));}catch(e){}
    document.body.classList.add('mini');
    L=miniLayoutBauen(); miniAn=true; renderPanels();
    if(b){b.classList.add('an'); b.textContent='🔳 Voll';}
  }else{
    document.body.classList.remove('mini'); miniAn=false;
    let vor=miniVor;
    if(!vor){try{vor=JSON.parse(localStorage.getItem(VORMINI)||'null');}catch(e){}}
    if(vor&&vor.panels){delete vor.mini; vor.panels=vor.panels.filter(p=>p.id!=='pmini'); L=vor;}
    else L=defaultLayout();
    miniVor=null; try{localStorage.removeItem(VORMINI);}catch(e){}
    layoutAnViewport();                                // Fenster im Mini resized? Basis-Projektion statt roher Alt-Pixel
    renderPanels();
    if(b){b.classList.remove('an'); b.textContent='🔳 Mini';}
  }
}
function miniVerlassen(){                              // Layout-Wechsel beendet den Mini-Modus (Aufrufer setzt neues L)
  if(!miniAn)return;
  miniAn=false; miniVor=null; document.body.classList.remove('mini');
  try{localStorage.removeItem(VORMINI);}catch(e){}
  const b=document.getElementById('mini-btn'); if(b){b.classList.remove('an'); b.textContent='🔳 Mini';}
}

function dockZiel(draggedId){
  // Andock-Ziel per FLÄCHEN-ÜBERLAPPUNG (robust, nicht Cursor-Punkt): das Fenster
  // mit der größten Überlappung, wenn diese über 25% des gezogenen Fensters liegt.
  const de=panelEl(draggedId); if(!de)return null;
  const dp=de.getBoundingClientRect(), flaeche=dp.width*dp.height||1;
  let best=null,bestOv=0;
  L.panels.forEach(p=>{
    if(p.id===draggedId)return;
    const el=panelEl(p.id); if(!el)return;
    const r=el.getBoundingClientRect();
    const ox=Math.max(0,Math.min(dp.right,r.right)-Math.max(dp.left,r.left));
    const oy=Math.max(0,Math.min(dp.bottom,r.bottom)-Math.max(dp.top,r.top));
    const ov=ox*oy;
    if(ov>bestOv){bestOv=ov;best=p;}
  });
  return (best && bestOv>0.25*flaeche) ? best.id : null;
}
function clearDock(){document.querySelectorAll('.dockpending').forEach(e=>e.classList.remove('dockpending'));
  const d=document.getElementById('dockhint'); if(d)d.remove();}
function dockOverlay(id,text,ready){
  clearDock();
  const el=panelEl(id); if(!el)return;
  el.classList.add('dockpending');
  const d=document.createElement('div'); d.className='dockhint'+(ready?' ready':''); d.id='dockhint';
  d.textContent=text; el.appendChild(d);
}

function fensterAbstand(){let v=NaN; try{v=parseInt(localStorage.getItem('ytdl_gap'),10);}catch(e){} return isNaN(v)?0:v;}
// Fenster „kleben": die linke/obere Kante des gezogenen Fensters an sinnvolle
// Positionen fangen — Rand, Kanten-Ausrichtung mit Nachbarn, und Anlegen mit
// eingestelltem Abstand (Gap). So sitzen Fenster sauber nebeneinander.
function naechsteKante(pos, kandidaten, T){          // die NÄCHSTE Kante im Fangradius (Mathe: layout_kern)
  return LK.naechsteKante(pos, kandidaten, T);
}
function snapKanten(p){                               // kräftiger Magnet (JB: „haften!") — Mathe: layout_kern
  const c=document.getElementById('canvas');
  const s=LK.snapXY(p, L.panels, c.clientWidth, c.clientHeight, fensterAbstand(), 16);
  p.x=s.x; p.y=s.y;
}

/* ---- ✏-Layout-Modus (JB 13.07., Muster wie im Dashboard): AUS = Ziehen ist
   NUR die Tab-Geste (über ein Fenster halten -> andocken; sonst schnappt es an
   seinen Platz zurück, das Layout bleibt unangetastet). AN = Ziehen verschiebt,
   8 Griffe ändern die Größe — und Fenster können sich dabei NIE überlappen. */
let layoutEdit=false;
function layoutEntwirren(){                           // Überlappungen auflösen (vorderstes gewinnt)
  [...L.panels].sort((a,b)=>(b.zi||0)-(a.zi||0)).forEach(p=>verdraenge(p));
  panelsPos(); saveLayout();
}
function layoutEditToggle(){
  layoutEdit=!layoutEdit;
  document.body.classList.toggle('layoutedit',layoutEdit);
  const b=document.getElementById('layoutedit-btn'); if(b)b.classList.toggle('an',layoutEdit);
  clearDock();
  if(layoutEdit)layoutEntwirren();                    // beim Einschalten: Altlasten entwirren
}
function kollidiert(p,x,y,w,h){                       // überlappt der Kasten ein anderes Fenster? (layout_kern)
  return LK.kollidiert(L.panels, p.id, x, y, w, h);
}
function ueberlappt(a,b){return LK.ueberlappt(a,b);}
/* Verdrängen (JB 13.07.: „das bewegte Fenster muss Priorität haben"): alle
   Fenster, die dem priorisierten im Weg stehen, weichen mit der KLEINSTEN
   möglichen Verschiebung aus (rechts/links/unter/über, notfalls nach unten —
   da ist immer Platz, die Seite scrollt). Kettenreaktionen sind begrenzt,
   und niemand schiebt das priorisierte Fenster zurück. */
function verdraenge(p,fest,tiefe){
  fest=fest||new Set([p.id]); tiefe=tiefe||0;
  if(tiefe>6)return;
  const c=document.getElementById('canvas'), cw=c?c.clientWidth:window.innerWidth;
  const gap=Math.max(0,fensterAbstand());
  L.panels.forEach(o=>{
    if(fest.has(o.id)||!ueberlappt(p,o))return;
    const rechts=p.x+p.w+gap, links=p.x-o.w-gap, unten=p.y+p.h+gap, oben=p.y-o.h-gap;
    const kand=[
      {x:rechts,y:o.y,d:rechts-o.x,        ok:rechts+o.w<=cw},
      {x:links, y:o.y,d:o.x-links,         ok:links>=0},
      {x:o.x,   y:unten,d:unten-o.y,       ok:true},
      {x:o.x,   y:oben, d:o.y-oben,        ok:oben>=0},
    ].filter(k=>k.ok).sort((a,b)=>Math.abs(a.d)-Math.abs(b.d));
    // Ausweichplatz darf NICHT auf einem bereits fixierten Fenster landen —
    // sonst entstehen genau die Rest-Überlappungen, die JB gesehen hat (14.07.).
    let z=kand.find(k=>!L.panels.some(q=>fest.has(q.id)&&q.id!==o.id
      &&k.x<q.x+q.w&&k.x+o.w>q.x&&k.y<q.y+q.h&&k.y+o.h>q.y));
    if(!z){                                           // nirgendwo frei -> unter ALLES (immer frei)
      const tiefstes=Math.max(0,...L.panels.filter(q=>q.id!==o.id).map(q=>q.y+q.h));
      z={x:Math.max(0,Math.min(o.x,cw-o.w)), y:tiefstes+gap};
    }
    o.x=Math.max(0,z.x); o.y=Math.max(0,z.y);
    fest.add(o.id);
    verdraenge(o,fest,tiefe+1);                       // wer ausweicht, schiebt ggf. weiter
  });
}
function panelsPos(){L.panels.forEach(o=>{const e2=panelEl(o.id);
  if(e2){e2.style.left=o.x+'px'; e2.style.top=o.y+'px';}});}

/* MAGNET (JB 14.07.: „Andocken heißt magnetische Fenster — nichts bleibt in
   der Luft"): die nächstgelegene BÜNDIGE Anlege-Position an einem Nachbarn
   oder Rand, egal wie weit weg — die Gleit-Koordinate folgt der Maus, sodass
   man die Höhe/Seite selbst wählt. Nur kollisionsfreie Plätze zählen. */
function magnetPos(p,x,y){
  const c=document.getElementById('canvas'), cw=c?c.clientWidth:window.innerWidth;
  const gap=Math.max(0,fensterAbstand());
  const kand=[];
  L.panels.forEach(o=>{
    if(o.id===p.id)return;
    const yk=Math.max(Math.max(0,o.y-p.h+24), Math.min(y, o.y+o.h-24));   // mind. 24px Kontakt
    kand.push({x:o.x+o.w+gap, y:yk});                 // rechts an o
    kand.push({x:o.x-p.w-gap, y:yk});                 // links an o
    const xk=Math.max(Math.max(0,o.x-p.w+24), Math.min(x, o.x+o.w-24));
    kand.push({x:xk, y:o.y+o.h+gap});                 // unter o
    kand.push({x:xk, y:o.y-p.h-gap});                 // über o
  });
  kand.push({x:0, y:Math.max(0,y)});                  // Ränder
  kand.push({x:Math.max(0,cw-p.w), y:Math.max(0,y)});
  kand.push({x:Math.max(0,Math.min(x,cw-p.w)), y:0});
  let best=null, bd=Infinity;
  for(const k of kand){
    if(k.x<0||k.y<0||k.x+p.w>cw)continue;
    if(kollidiert(p,k.x,k.y,p.w,p.h))continue;
    const d=(k.x-x)*(k.x-x)+(k.y-y)*(k.y-y);
    if(d<bd){bd=d; best=k;}
  }
  return best;
}

/* Nächste FREIE Position für ein neues Fenster (w×h) nahe dem Wunschpunkt —
   bewegt NICHTS anderes (JB 14.07.: „die Ordnung darf sich nicht ändern").
   Kandidaten sind bündige Anlege-Positionen an Nachbarn/Rand (Abstand = gap,
   Standard 0); ist nirgendwo Platz, geht es unter das unterste Fenster. */
function freiePosition(w,h,zx,zy){
  const c=document.getElementById('canvas'), cw=c?c.clientWidth:window.innerWidth;
  const gap=Math.max(0,fensterAbstand());
  const xs=new Set([0, Math.max(0,cw-w), Math.max(0,Math.min(zx,cw-w))]);
  const ys=new Set([0, Math.max(0,zy)]);
  L.panels.forEach(o=>{
    xs.add(o.x); xs.add(o.x+o.w+gap); xs.add(Math.max(0,o.x-w-gap));
    ys.add(o.y); ys.add(o.y+o.h+gap); ys.add(Math.max(0,o.y-h-gap));
  });
  let best=null, bestD=Infinity;
  for(const x of xs)for(const y of ys){
    if(x<0||y<0||x+w>cw)continue;
    if(L.panels.some(o=>x<o.x+o.w&&x+w>o.x&&y<o.y+o.h&&y+h>o.y))continue;
    const d=(x-zx)*(x-zx)+(y-zy)*(y-zy);
    if(d<bestD){bestD=d; best={x,y};}
  }
  if(best)return best;
  const tiefstes=Math.max(0,...L.panels.map(o=>o.y+o.h));
  return {x:Math.max(0,Math.min(zx,cw-w)), y:tiefstes+gap};
}

/* Größtes freies Rechteck um einen Punkt (JB 14.07.: der herausgezogene Tab
   hat VORRANG am Ablagepunkt und FÜLLT dort die Lücke — bündig an allen
   Nachbarn, keine großen Abstände, keine Fantasie-Festgröße):
   erst die x-Grenzen aus Fenstern, die den Punkt vertikal enthalten,
   dann die y-Grenzen aus allem, was in diesen x-Bereich ragt. */
function freiesRechteck(px,py){
  const c=document.getElementById('canvas'), cw=c?c.clientWidth:window.innerWidth;
  const gap=Math.max(0,fensterAbstand());
  let l=0, r=cw;
  L.panels.forEach(o=>{
    if(py>=o.y&&py<o.y+o.h){
      if(o.x+o.w<=px)l=Math.max(l,o.x+o.w+gap);
      else if(o.x>=px)r=Math.min(r,o.x-gap);
    }
  });
  let t=0, b=Infinity;
  L.panels.forEach(o=>{
    if(o.x<r&&o.x+o.w>l){
      if(o.y+o.h<=py)t=Math.max(t,o.y+o.h+gap);
      else if(o.y>=py)b=Math.min(b,o.y-gap);
    }
  });
  if(b===Infinity){
    const tiefstes=Math.max(_canvasH(),...L.panels.map(o=>o.y+o.h));
    b=Math.max(t+130,tiefstes);
  }
  return {x:l, y:t, w:r-l, h:b-t};
}

function startMove(el,p,e){
  e.preventDefault(); bringFront(p); el.classList.add('dragging');
  document.body.classList.add('nosel');               // beim Ziehen keinen Text markieren
  try{el.setPointerCapture(e.pointerId);}catch(_){}
  const sx=e.clientX,sy=e.clientY,ox=p.x,oy=p.y;
  let ziel=null, ph=null, zx=ox, zy=oy;
  function mv(ev){
    const c=document.getElementById('canvas');
    p.x=ox+ev.clientX-sx; p.y=oy+ev.clientY-sy;
    p.x=Math.max(0, Math.min(p.x, Math.max(0, c.clientWidth-p.w)));   // nie aus dem Bild
    p.y=Math.max(0, p.y);
    el.style.left=p.x+'px'; el.style.top=p.y+'px';    // Fenster folgt der Maus ROH = fühlt sich fest an
    if(layoutEdit){
      // Dashboard-Muster (JB: „im Dashboard viel besser"): nichts wackelt live —
      // ein PLATZHALTER zeigt die eingerastete Zielposition, gelandet wird beim
      // Loslassen; erst dann weichen die anderen aus.
      // MAGNET: Ziel = nächste bündige Anlege-Position (nie „in der Luft"),
      // Feinausrichtung über snapKanten (bündige Kanten mit Nachbarn)
      let t=magnetPos(p,p.x,p.y)||{x:p.x,y:p.y};
      const fein={id:p.id, x:t.x, y:t.y, w:p.w, h:p.h};
      snapKanten(fein);
      if(!kollidiert(p,fein.x,fein.y,p.w,p.h))t=fein;
      zx=Math.max(0, Math.min(t.x, Math.max(0, c.clientWidth-p.w))); zy=Math.max(0, t.y);
      if(!ph){ph=document.createElement('div'); ph.className='platzhalter-fenster'; c.appendChild(ph);}
      ph.style.left=zx+'px'; ph.style.top=zy+'px'; ph.style.width=p.w+'px'; ph.style.height=p.h+'px';
    }else{
      const t=dockZiel(p.id);                         // Tab-Geste: stark überlappt = andocken
      if(t!==ziel){ ziel=t; clearDock(); if(t)dockOverlay(t,'Loslassen: als Tab andocken',true); }
    }
  }
  function up(){
    document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
    el.classList.remove('dragging'); clearDock();
    document.body.classList.remove('nosel');
    try{el.releasePointerCapture(e.pointerId);}catch(_){}
    if(ph)ph.remove();
    if(layoutEdit){                                   // auf dem Platzhalter landen, Rest weicht aus
      p.x=zx; p.y=zy;
      verdraenge(p); panelsPos(); saveLayout();
      return;
    }
    if(ziel){ dockPanel(p.id,ziel); return; }
    p.x=ox; p.y=oy;                                   // nichts angedockt -> sanft zurückschnappen
    el.style.transition='left .18s ease-out, top .18s ease-out';
    el.style.left=ox+'px'; el.style.top=oy+'px';
    setTimeout(()=>{el.style.transition='';},200);
  }
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
}

function startResize(el,p,e,richtung){
  e.preventDefault(); try{el.setPointerCapture(e.pointerId);}catch(_){}
  document.body.classList.add('nosel');
  const sx=e.clientX,sy=e.clientY,ox=p.x,oy=p.y,ow=p.w,oh=p.h;
  const r=richtung||'se';
  const dxs=r.includes('e')?1:(r.includes('w')?-1:0); // welche Kanten bewegen sich mit?
  const dys=r.includes('s')?1:(r.includes('n')?-1:0);
  const prop=(p.active==='player'&&r==='se'), aspect=ow/Math.max(1,oh);   // Player-Ecke: proportional
  function mv(ev){
    const c=document.getElementById('canvas'), T=12;
    const dx=ev.clientX-sx, dy=ev.clientY-sy;
    let nx=ox, ny=oy, nw=ow, nh=oh;
    if(dxs===1)nw=ow+dx; else if(dxs===-1){nw=ow-dx; nx=ox+dx;}
    if(dys===1)nh=oh+dy; else if(dys===-1){nh=oh-dy; ny=oy+dy;}
    if(prop)nh=Math.round(nw/aspect);
    // Mindestgrößen — bei links/oben wandert die Position entsprechend zurück
    if(nw<190){ if(dxs===-1)nx-=190-nw; nw=190; }
    if(nh<130){ if(dys===-1)ny-=130-nh; nh=130; }
    if(nx<0){nw+=nx; nx=0;}                           // nie aus dem Bild
    if(ny<0){nh+=ny; ny=0;}
    nw=Math.min(nw, c.clientWidth-nx);
    // die BEWEGTE Kante an Nachbar-Kanten/Rand kleben
    const xs=[0,c.clientWidth], ys=[0,c.clientHeight];
    L.panels.forEach(o=>{if(o.id!==p.id){xs.push(o.x,o.x+o.w); ys.push(o.y,o.y+o.h);}});
    if(dxs===1){for(const l of xs){if(Math.abs(nx+nw-l)<=T){nw=l-nx;break;}}}
    if(dxs===-1){for(const l of xs){if(Math.abs(nx-l)<=T){nw+=nx-l; nx=l;break;}}}
    if(dys===1){for(const l of ys){if(Math.abs(ny+nh-l)<=T){nh=l-ny;break;}}}
    if(dys===-1){for(const l of ys){if(Math.abs(ny-l)<=T){nh+=ny-l; ny=l;break;}}}
    nw=Math.max(190,nw); nh=Math.max(130,nh);
    // NIE überlappen (JB): kollidiert der neue Kasten, bleibt die letzte gültige Größe
    if(!kollidiert(p,nx,ny,nw,nh)){p.x=nx; p.y=ny; p.w=nw; p.h=nh;}
    el.style.left=p.x+'px'; el.style.top=p.y+'px';
    el.style.width=p.w+'px'; el.style.height=p.h+'px';
  }
  function up(){document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
    document.body.classList.remove('nosel');
    try{el.releasePointerCapture(e.pointerId);}catch(_){} saveLayout();}
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
}

function bindTab(t,panelId){
  t.addEventListener('pointerdown',e=>{
    const p=L.panels.find(x=>x.id===panelId); if(!p)return;
    const view=t.dataset.view;
    if(p.views.length<2){                 // Einzel-Fenster: am NAMEN ziehen = Fenster bewegen
      startMove(panelEl(panelId),p,e);    // (auf ein anderes Fenster ziehen dockt an)
      return;
    }
    e.stopPropagation();
    const sx=e.clientX, sy=e.clientY; let moved=false, ghost=null, ueberPanel=null;
    function mv(ev){
      if(!moved&&Math.hypot(ev.clientX-sx,ev.clientY-sy)>18){
        moved=true;                                   // transluzente Vorschau wie beim Browser-Tab-Drag
        document.body.classList.add('nosel');
        ghost=document.createElement('div'); ghost.className='tabghost';
        // Vorschau im Seitenverhältnis des Quellfensters (das neue Fenster
        // bekommt später exakt dessen Größe)
        ghost.style.width=Math.max(160,Math.min(320,Math.round(p.w*0.35)))+'px';
        ghost.style.height=Math.max(110,Math.min(220,Math.round(p.h*0.35)))+'px';
        ghost.innerHTML='<div class="tabghost-kopf">'+esc(VIEWS[view]||view)+'</div>'+
                        '<div class="tabghost-body" id="tabghost-txt">Loslassen = eigenes Fenster hier</div>';
        document.body.appendChild(ghost);
      }
      if(!ghost)return;
      ghost.style.left=(ev.clientX-115)+'px'; ghost.style.top=(ev.clientY-14)+'px';
      // Über einem anderen Fenster? Dann wird der Tab DORT angedockt (JB 14.07.)
      const z=panelUnter(ev.clientX,ev.clientY,panelId);
      if((z&&z.id)!==(ueberPanel&&ueberPanel.id)){
        ueberPanel=z; clearDock();
        if(z)dockOverlay(z.id,'Loslassen: Tab hier andocken',true);
        const tx=document.getElementById('tabghost-txt');
        if(tx)tx.textContent=z?('→ als Tab in „'+(z.views.map(v=>VIEWS[v]).join(' / '))+'"'):'Loslassen = eigenes Fenster hier';
      }
    }
    function up(ev){
      document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
      if(ghost)ghost.remove(); clearDock();
      document.body.classList.remove('nosel');
      if(!moved){ p.active=view; bringFront(p); merkeView(panelId,view); renderPanels(); return; }   // Klick = Tab wechseln
      if(ueberPanel){                                 // Tab wandert in das andere Fenster
        p.views=p.views.filter(v=>v!==view); if(p.active===view)p.active=p.views[0];
        if(!ueberPanel.views.includes(view))ueberPanel.views.push(view);
        ueberPanel.active=view; ueberPanel.zi=++L.z;
        renderPanels(); return;
      }
      tearOut(panelId,view,ev.clientX,ev.clientY);    // auf Freifläche = eigenes Fenster
    }
    document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
  });
}

function panelUnter(x,y,ausser){                      // oberstes Fenster unter dem Cursor
  let best=null;
  for(const p of L.panels){
    if(p.id===ausser)continue;
    const el=panelEl(p.id); if(!el)continue;
    const r=el.getBoundingClientRect();
    if(x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom&&(!best||(p.zi||0)>(best.zi||0)))best=p;
  }
  return best;
}

function tearOut(panelId,view,cx,cy){
  const p=L.panels.find(x=>x.id===panelId); if(!p||p.views.length<2)return;
  p.views=p.views.filter(v=>v!==view); if(p.active===view)p.active=p.views[0];
  const r=document.getElementById('canvas').getBoundingClientRect();
  const px=Math.max(0,cx-r.left), py=Math.max(0,cy-r.top);
  // Der Tab hat VORRANG am Ablagepunkt: er FÜLLT dort die freie Lücke
  // (bündig an allen Nachbarn) — kein anderes Fenster bewegt sich, das
  // restliche Layout bleibt identisch (JB 14.07.).
  // Liegt der Punkt AUF einem Fenster (z.B. überm eigenen Quellfenster
  // losgelassen), gibt es dort keine Lücke -> nächste freie Stelle in Quellgröße.
  const belegt=L.panels.some(o=>px>=o.x&&px<o.x+o.w&&py>=o.y&&py<o.y+o.h);
  let rect=belegt?null:freiesRechteck(px,py);
  if(!rect||rect.w<190||rect.h<130){                  // keine/zu kleine Lücke
    const pos=freiePosition(p.w,p.h,px-70,py-14);
    rect={x:pos.x, y:pos.y, w:p.w, h:p.h};
  }
  L.panels.push({id:'p'+(++L.z), x:rect.x, y:rect.y, w:rect.w, h:rect.h,
                 views:[view], active:view, zi:++L.z});
  renderPanels();
}

/* Player-Playlist als eigenes Fenster herauslösen / wieder in den Player holen.
   Als Fenster ist sie normal andockbar (Tab-System) — so lassen sich Player
   und Playlist frei kombinieren oder getrennt anordnen (JB 13.07.). */
function plqFenster(){
  // JB 04.08.: im Mini-Modus ist die Playlist FEST ein eigenes Fenster —
  // Eingliedern schöbe sie in die ausgeblendete Seitenliste (weg wäre sie).
  // Riegel zusätzlich zum versteckten Knopf, falls ein anderer Weg ruft.
  if(miniAn){toast('Im Mini-Modus bleibt die Playlist ein eigenes Fenster.');return;}
  // Abspalten OHNE dass sich irgendetwas bewegt (JB 14.07.): die Playlist
  // bekommt den RECHTEN STREIFEN des Player-Fensters, der Player wird nur
  // schmaler — alle anderen Fenster bleiben exakt stehen. Eingliedern gibt
  // dem Player die Breite zurück, wenn die Playlist noch daneben klebt.
  const gap=Math.max(0,fensterAbstand());
  const pl=L.panels.find(p=>p.views.includes('player'));
  const drin=L.panels.find(p=>p.views.includes('plq'));
  if(drin){
    if(drin.views.length===1&&pl
       &&Math.abs(drin.x-(pl.x+pl.w+gap))<=14&&Math.abs(drin.y-pl.y)<=14)
      pl.w=pl.w+gap+drin.w;                           // Streifen zurück an den Player
    drin.views=drin.views.filter(v=>v!=='plq');
    if(!drin.views.length)L.panels=L.panels.filter(p=>p.id!==drin.id);
    else if(drin.active==='plq')drin.active=drin.views[0];
    renderPanels(); return;
  }
  const W=260;
  let neu;
  if(pl && pl.w>=190+W+gap){
    pl.w=pl.w-W-gap;
    neu={id:'p'+(++L.z), x:pl.x+pl.w+gap, y:pl.y, w:W, h:pl.h, views:['plq'], active:'plq', zi:++L.z};
    L.panels.push(neu);
  }else{                                              // Player zu schmal -> nächste freie Stelle daneben
    const H=Math.max(320, pl?pl.h:420);
    const pos=freiePosition(W, H, pl?pl.x+pl.w+gap:40, pl?pl.y:20);
    neu={id:'p'+(++L.z), x:pos.x, y:pos.y, w:W, h:H, views:['plq'], active:'plq', zi:++L.z};
    L.panels.push(neu);
  }
  renderPanels();
}

function dockPanel(srcId,tgtId){
  const src=L.panels.find(p=>p.id===srcId), tgt=L.panels.find(p=>p.id===tgtId);
  if(!src||!tgt)return;
  src.views.forEach(v=>{if(!tgt.views.includes(v))tgt.views.push(v);});
  tgt.active=src.active; tgt.zi=++L.z;
  L.panels=L.panels.filter(p=>p.id!==srcId);
  renderPanels();
}

function zeigeView(view){
  const p=L.panels.find(pp=>pp.views.includes(view)); if(!p)return;
  p.active=view; bringFront(p); renderPanels();
}

/* ================= Warteschlange ================= */
const PILLS={wartend:'wartet',prueft:'prüfe…',laeuft:'lädt',pausiert:'pausiert',fertig:'fertig',
  fehler:'Fehler',uebersprungen:'übersprungen'};

let offeneQueue=new Set();
function qToggle(id){ if(offeneQueue.has(id))offeneQueue.delete(id); else offeneQueue.add(id); malen(); }
function balkenAscii(proz,n){ n=n||12; const f=Math.max(0,Math.min(n,Math.round((proz||0)/100*n))); return '█'.repeat(f)+'░'.repeat(n-f); }
function kurzfehler(t){
  t=(t||'').replace(/\\s+/g,' ').trim(); const l=t.toLowerCase();
  if(l.includes('available in your country'))return 'geo-gesperrt';
  if(l.includes('private video'))return 'privat';
  if(l.includes('video unavailable'))return 'nicht verfügbar';
  if(l.includes('sign in to confirm your age'))return 'altersbeschränkt';
  if(l.includes('has been removed')||l.includes('no longer available'))return 'entfernt';
  if(l.includes('cookie'))return 'Cookie-Fehler';
  if(l.includes('nordvpn'))return 'VPN nötig';
  return t.length>42?t.slice(0,42)+'…':(t||'Fehler');
}
function reihe(it){
  const jetzt=daten.jetzt;
  const fertigartig=(it.status==='fertig'||it.status==='uebersprungen');
  const proz=fertigartig?100:(it.prozent||0);
  const auf=offeneQueue.has(it.id);
  let rechts='';
  if(it.status==='laeuft'){
    if(!it.geladen&&it.phase&&(it.phase.startsWith('VPN')||it.phase.startsWith('Geo')))rechts='🌍 '+it.phase.replace(/^Geo: /,'');
    else rechts=`${proz.toFixed(0)}%`+(it.geschw?' '+tempo(it.geschw):'')+(it.eta!=null?' '+zeit(it.eta):'');
  }else if(it.status==='wartend'&&it.naechster_versuch>jetzt)rechts='retry '+Math.max(1,Math.round(it.naechster_versuch-jetzt))+'s';
  else if(it.status==='fehler')rechts=kurzfehler(it.fehler);
  else if(fertigartig)rechts=it.gesamt?mb(it.gesamt):'ok';
  else if(it.status==='wartend')rechts='queued';
  else if(it.status==='prueft')rechts='…';
  // Fertig-Zeilen sind abspielbar (JB 22.07.): Doppelklick spielt, Klick fokussiert
  // (tabindex) -> Enter spielt, Entf entfernt den Eintrag (Datei bleibt).
  const fx=fertigartig?` tabindex="0" data-fid="${it.id}" ondblclick="fertigPlay('${it.id}')"`:'';
  const tip=fertigartig?'Doppelklick/Enter = abspielen · Entf = Eintrag entfernen (Datei bleibt) · Klick = Details':esc(it.titel);
  const zeile=`<div class="qline ${it.status}"${fx} onclick="qToggle('${it.id}')" title="${tip}">`+
    `<span class="qtri">${auf?'▾':'▸'}</span>`+
    `<span class="qbar">[${balkenAscii(proz)}]</span>`+
    `<span class="qtitel">${esc(it.titel)}</span>`+
    `<span class="qrechts">${esc(rechts)}</span></div>`;
  if(!auf)return zeile;
  const k=[];
  if(it.status==='laeuft')k.push(['pause','⏸ Pause']);
  if(it.status==='wartend'){k.push(['pause','⏸ Pause'],['hoch','⏫ Hoch']);
    if(it.naechster_versuch>jetzt)k.push(['sofort','⚡ Sofort']);}
  if(it.status==='pausiert'||it.status==='fehler')k.push(['weiter','▶ Weiter']);
  if(it.status==='uebersprungen')k.push(['weiter','▶ Trotzdem']);
  if(fertigartig)k.push(['ordner','📂 Ordner']);
  k.push(['entfernen','✖ Entfernen']);               // geht auch bei Laufenden: bricht ab + nimmt raus
  let knoepfe=k.map(([a,t])=>`<button class="btn mini" onclick="event.stopPropagation();aktion('${it.id}','${a}')">${t}</button>`).join('');
  if(fertigartig)knoepfe=`<button class="btn mini" onclick="event.stopPropagation();fertigPlay('${it.id}')" title="Im Player abspielen">▶ Abspielen</button>`+knoepfe;
  let det='';
  if(it.status==='laeuft')det=`${mb(it.geladen)} / ${mb(it.gesamt)}`+(it.phase?' · '+esc(it.phase):'');
  else if(it.status==='fehler')det=`<span class="fehltext">${esc(it.fehler||'unbekannter Fehler')}</span>`;
  else if(fertigartig&&it.datei)det=esc(it.datei.split('\\\\').pop());
  else if(it.dauer)det='Länge '+zeit(it.dauer);
  return zeile+`<div class="qdetail"><div class="qdinfo">${esc(it.qualitaet)}`+
    `${it.kategorie?' · '+esc(it.kategorie):''}${det?' · '+det:''}</div>`+
    `<div class="aktionen">${knoepfe}</div></div>`;
}

/* Fertig-Eintrag im Player abspielen (JB 22.07.): aus der Download-URL die
   Video-ID ziehen und den passenden Bibliotheks-Key finden — exakt (id|qualitaet),
   sonst irgendein vorhandenes Format desselben Videos. */
function fertigVid(url){
  const m=(url||'').match(/(?:v=|youtu\\.be\\/|shorts\\/|embed\\/)([A-Za-z0-9_-]{6,})/);
  return m?m[1]:null;
}
function fertigPlay(qid){
  const it=((daten&&daten.items)||[]).find(x=>x.id===qid); if(!it)return;
  const vid=fertigVid(it.url);
  if(!vid){toast('Kein Video-Link an diesem Eintrag.');return;}
  let x=libFind(vid+'|'+it.qualitaet);
  if(!x||!x.vorhanden)x=(libdaten||[]).find(e=>e.id.indexOf(vid+'|')===0&&e.vorhanden);
  if(!x){toast('Noch nicht in der Bibliothek — kurz nach dem Download-Ende erneut versuchen.');return;}
  ensurePlayer(); playerPlay([x.id]);
}

function counterMalen(z){
  const db=daten.db||{gesamt:0,kategorien:{}};
  document.getElementById('counter_num').textContent=db.gesamt;
  const kat=db.kategorien||{};
  const KL={'MP3':'🎵 MP3','4K+':'🎬 4K+ Video','Video':'🎬 Video'};
  const reihen=Object.keys(KL).filter(k=>kat[k]).map(k=>
    `<div class="tiprow"><span>${KL[k]}</span><b>${kat[k]}</b></div>`).join('')
    ||'<div class="tiprow"><span>noch nichts geladen</span><b>0</b></div>';
  const live=[];
  if(z.laeuft)live.push(['lädt gerade',z.laeuft]);
  if(z.wartend+z.prueft)live.push(['in der Warteschlange',z.wartend+z.prueft]);
  if(z.pausiert)live.push(['pausiert',z.pausiert]);
  if(z.fehler)live.push(['Fehler',z.fehler]);
  const liveHtml=live.length?('<div class="tipsep"></div>'+live.map(([l,n])=>
    `<div class="tiprow"><span>${l}</span><b>${n}</b></div>`).join('')):'';
  document.getElementById('counter_tip').innerHTML=
    `<div class="tiptitel">Insgesamt geladen</div>${reihen}${liveHtml}`;
}

function malen(){
  if(!daten)return;
  const items=daten.items;
  const ende=['fertig','uebersprungen'];
  const aktiv=items.filter(i=>!ende.includes(i.status));
  const fertig=items.filter(i=>ende.includes(i.status));
  const z={laeuft:0,wartend:0,pausiert:0,fehler:0,prueft:0,uebersprungen:0};
  items.forEach(i=>{if(z[i.status]!=null)z[i.status]++;});
  // Zähler nicht mehr in den Downloads (JB 21.07.: sieht man an den Reitern) —
  // stattdessen als Übersicht oben im Log.
  const lc=document.getElementById('logchips'); if(lc)lc.innerHTML=
    `<span class="chip"><b>${(daten.db||{}).gesamt||0}</b> insgesamt</span>`+
    `<span class="chip laeuft"><b>${z.laeuft}</b> lädt</span>`+
    `<span class="chip"><b>${z.wartend+z.prueft}</b> wartet</span>`+
    `<span class="chip fertig"><b>${fertig.length-z.uebersprungen}</b> fertig</span>`+
    (z.uebersprungen?`<span class="chip"><b>${z.uebersprungen}</b> übersprungen</span>`:'')+
    (z.fehler?`<span class="chip fehler"><b>${z.fehler}</b> Fehler</span>`:'')+
    (z.pausiert?`<span class="chip"><b>${z.pausiert}</b> pausiert</span>`:'');
  document.getElementById('liste').innerHTML=
    aktiv.length?aktiv.map(reihe).join(''):'<div class="leer">Keine aktiven Downloads — oben einen Link einfügen und laden.</div>';
  // Fokus in der Fertig-Liste über das Neu-Rendern retten (der Status-Ticker
  // malt alle paar Sekunden — sonst verlöre Entf/Enter seinen Bezug, JB 22.07.)
  const af=document.activeElement, fid=(af&&af.dataset)?af.dataset.fid:null;
  document.getElementById('fertigliste').innerHTML=
    fertig.length?fertig.slice().reverse().map(reihe).join(''):'<div class="leer">Noch nichts fertig.</div>';
  if(fid){const nb=document.querySelector('#fertigliste [data-fid="'+fid+'"]'); if(nb)nb.focus();}
  counterMalen(z);
  const fw=document.getElementById('ffwarn'); if(fw)fw.style.display=daten.ffmpeg?'none':'';   // ffmpeg-Warnung sichtbar!
  const al=document.getElementById('addon_lokal'); if(al)al.style.display=daten.addon_xpi?'':'none';
  cmdNowRender();                                      // „Now Playing"-Mini oben mitversorgen
  logDiff(items);                                      // Ereignisse in den Log schreiben
  autotagStatus();                                     // Auto-Tagging-Fortschritt anzeigen
  const sub=document.getElementById('sub'); if(sub)sub.textContent=
    `Zielordner: ${daten.ziel}`+(daten.ffmpeg?'':' · ⚠ ffmpeg fehlt — hohe Qualitäten eingeschränkt');
}

function apiStatus(ok){
  const d=document.getElementById('apidot');
  if(d){
    d.className='apidot'+(ok?'':' bad');
    if(!d.firstChild)d.innerHTML=browserZeichen();      // einmal zeichnen, dann nur umfärben
    d.title=(ok?'API verbunden · 127.0.0.1:8776':'API getrennt — läuft die App?')
            +' · Browser: '+browserName();
  }
  const t=document.getElementById('apitext'); if(t)t.textContent=ok?'API verbunden · 127.0.0.1:8776':'API getrennt — läuft die App?';
  // Build 134: Das Geräte-Symbol hängt am Datenstand, nicht am ⚙-Menü —
  // sonst erschiene es erst, wenn jemand die Einstellungen öffnet.
  try{fernInfoMalen();}catch(e){}
}

let cfgInit=false;
function configFuellen(){
  if(cfgInit||!daten)return; cfgInit=true;
  document.getElementById('cfg_ziel').value=daten.config.ziel_ordner||daten.ziel;
  document.getElementById('cfg_ordner').value=daten.config.unterordner?'1':'0';
  document.getElementById('cfg_meta').value=daten.config.metadaten?'1':'0';
  document.getElementById('cfg_browser').value=daten.config.cookies_browser;
  document.getElementById('cfg_parallel').value=daten.config.parallel;
  document.getElementById('cfg_geo').value=daten.config.geo_vpn?'1':'0';
  document.getElementById('cfg_geoproxyfrei').value=daten.config.geo_gratis_proxy?'1':'0';
  document.getElementById('cfg_geoproxies').value=(daten.config.geo_proxies||[]).join('\\n');
  document.getElementById('cfg_geowg').value=daten.config.geo_wireguard_ordner||'';
  document.getElementById('cfg_qual').value=daten.config.standard_qualitaet;
  document.getElementById('cfg_sponsor').value=daten.config.sponsorblock||'';
  document.getElementById('cfg_subs').value=daten.config.untertitel?'1':'0';
  // JB Punkt 6: Sprachwahl. Ohne gespeicherte Wahl gilt der Standard de/en/orig.
  const sp=(daten.config.untertitel_sprachen&&daten.config.untertitel_sprachen.length)
    ?daten.config.untertitel_sprachen:['de','en','orig'];
  document.getElementById('cfg_sub_de').checked=sp.includes('de');
  document.getElementById('cfg_sub_en').checked=sp.includes('en');
  document.getElementById('cfg_sub_orig').checked=sp.includes('orig');
  document.getElementById('cfg_sub_extra').value=sp.filter(s=>!['de','en','orig'].includes(s)).join(', ');
  document.getElementById('cfg_autoupdate').value=daten.config.auto_update?'1':'0';
  document.getElementById('qual').value=daten.config.standard_qualitaet;
  const cq=document.getElementById('cmd-qual'); if(cq)cq.value=daten.config.standard_qualitaet;
}

async function laden(){
  try{
    const r=await fetch('/api/status');
    daten=await r.json();
    apiStatus(true); configFuellen(); malen();
    remoteAusfuehren(daten.remote);                    // Befehle vom Handy ausführen
    nachschubMelden(daten.addon_nachschub);            // Addon-Vormerkungen (v1.2.0)
    subStilVomServer();                                // Untertitel-Stil: Server-Stand gewinnt
    uiStandPruefen(daten.ui_stand);                    // alte Tabs erneuern sich selbst
  }catch(e){apiStatus(false);}
}
/* Selbst-Erneuerung (Wurzel-Fix 07.08.: JB testete mehrfach mit einem TAGE
   alten Tab — die Oberfläche lädt heiß vom Server, aber nur bei einem
   RELOAD, den nie jemand machte). Ändert sich der Stand der Oberfläche auf
   der Platte, lädt die Seite sich selbst neu — sanft: nie mitten im Film,
   in einem Dialog oder beim Tippen, höchstens einmal je Minute. */
let uiStand=null;
function uiStandPruefen(stand){
  if(!stand)return;
  if(uiStand===null){uiStand=stand; return;}
  if(stand===uiStand)return;
  const tippt=document.activeElement&&['INPUT','TEXTAREA'].includes(document.activeElement.tagName);
  if(tvpOffen||tvInfoOffen||tvDialogOffen||tippt)return;
  const letzter=+sessionStorage.getItem('ui_reload_ts')||0;
  if(Date.now()-letzter<60000)return;
  sessionStorage.setItem('ui_reload_ts',String(Date.now()));
  location.reload();
}
/* Addon-Nachschub (v1.2.0, JB): „eine kurze Info, dass jetzt x Downloads
   getätigt werden" — je id genau EIN Toast (Muster wie _remoteN: beim
   Seitenstart nur merken, Altes nicht nachplappern). */
let _nachschubId=null;
function nachschubMelden(a){
  if(!a)return;
  if(_nachschubId===null){_nachschubId=a.id; return;}
  if(a.id===_nachschubId)return; _nachschubId=a.id;
  if(a.n)toast('⬇ '+a.n+' vorgemerkte Downloads aus dem Firefox-Addon werden geholt.');
}
/* ---- Handy-Fernsteuerung: Befehle vom Handy am PC-Player ausführen ---- */
let _remoteN=null;
function remoteAusfuehren(r){
  if(!r)return;
  if(_remoteN===null){_remoteN=r.n; return;}           // beim Start nur merken, alten Befehl nicht ausführen
  if(r.n===_remoteN)return; _remoteN=r.n;
  const el=document.getElementById('pl-el');
  if(r.cmd==='playkey'&&r.key)playerPlay([r.key]);
  else if(r.cmd==='play')plTogglePlay();               // 'play' vom Handy = togglen (Browser ODER Gerät VLC)
  else if(r.cmd==='pause'){if(vlcAktiv())vlcBefehl('pause'); else if(el)el.pause();}
  else if(r.cmd==='next')playerNext();
  else if(r.cmd==='prev')playerPrev();
}
async function fernToggle(){
  const an=!(daten&&daten.fernsteuerung&&daten.fernsteuerung.aktiv);
  await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fernsteuerung:an})});
  await laden(); fernInfoMalen();
  if(an)alert('Fernsteuerung aktiviert.\\n\\nBitte die App EINMAL neu starten (Tray → Beenden → neu öffnen), '+
    'damit sie im WLAN erreichbar wird. Danach steht hier im ⚙ der Code + der Handy-Link.\\n\\n'+
    'Zugriff nur mit Code — Standard bleibt sonst dein PC allein.');
}
function fernFenster(ev){
  // Build 134: zeigt Code + Handy-Link direkt an der Kopfleiste, ohne den
  // Umweg über das Zahnrad. Schwebende Fläche => an den <body> (Build-125-Regel).
  const f=daten&&daten.fernsteuerung; if(!f)return;
  if(menuGeradeZu(ev.currentTarget))return;            // 2. Klick = zu
  document.querySelectorAll('#fernfly').forEach(x=>x.remove());
  const m=document.createElement('div'); m.className='panelmenu'; m.id='fernfly';
  m.style.minWidth='280px';
  m.innerHTML='<div style="font-size:11.5px;color:#8a7d74;padding:2px 6px 7px">📱 Fernsteuerung läuft</div>'+
    '<div class="mzeile"><span>Code</span><b style="color:var(--akz2);letter-spacing:.08em">'+esc(f.code||'')+'</b></div>'+
    (f.url?'<div class="mzeile"><span>Am Handy öffnen</span><b style="font-size:11.5px">'+esc(f.url)+'</b></div>'
          :'<div class="mzeile"><span style="font-size:11.5px">Handy-Link erscheint nach einem App-Neustart</span></div>')+
    '<div class="msep"></div>'+
    '<button class="mbtn" onclick="document.getElementById(\\'fernfly\\').remove();fernToggle()">Fernsteuerung ausschalten</button>';
  document.body.appendChild(m);
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  menuSchliesser(m);
}
function fernInfoMalen(){
  const b=document.getElementById('fernbtn'), info=document.getElementById('ferninfo');
  const f=daten&&daten.fernsteuerung;
  // Das Symbol in der Kopfleiste erscheint nur bei laufender Fernsteuerung.
  const sym=document.getElementById('fern-symbol');
  if(sym)sym.style.display=(f&&f.aktiv)?'':'none';
  if(b)b.textContent=(f&&f.aktiv)?'An — ausschalten':'Aus — einschalten';
  if(info){
    if(f&&f.aktiv)info.innerHTML='Code: <b style="color:var(--akz2)">'+esc(f.code||'')+'</b>'+
      (f.url?'<br>Handy-Link: <b>'+esc(f.url)+'</b> (im selben WLAN öffnen)':'<br>(nach App-Neustart erscheint hier der Handy-Link)');
    else info.textContent='Aus — nur dein PC hat Zugriff (127.0.0.1).';
  }
}

async function hinzufuegen(){
  const box=document.getElementById('urls');
  const urls=box.value.trim(); if(!urls)return;
  await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({urls,qualitaet:document.getElementById('qual').value})});
  box.value=''; laden();
}
async function aktion(id,art){
  await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id,art})});
  laden();
}

/* ---- Log: Ereignisse (Start/Fertig/Fehler/Übersprungen) aus der Queue ableiten ---- */
let logEintraege=[], _logStatus={}, _logInit=false;
function logPush(text,typ){
  logEintraege.unshift({t:Date.now(), text, typ:typ||''});
  if(logEintraege.length>200)logEintraege.length=200;
  logMalen();
}
function logDiff(items){
  const jetzt={}; (items||[]).forEach(i=>{jetzt[i.id]=i.status;});
  if(_logInit)(items||[]).forEach(i=>{
    const alt=_logStatus[i.id]; if(alt===i.status)return;
    const kurz=(i.titel||'…').slice(0,50);
    if(i.status==='laeuft'&&alt!=='pausiert')logPush('▶ gestartet: '+kurz,'laeuft');
    else if(i.status==='fertig')logPush('✓ fertig: '+kurz,'fertig');
    else if(i.status==='fehler')logPush('✗ Fehler: '+kurz+(i.fehler?' — '+i.fehler:''),'fehler');
    else if(i.status==='uebersprungen')logPush('⏭ übersprungen (schon geladen): '+kurz,'');
    else if(i.status==='pausiert')logPush('⏸ pausiert: '+kurz,'');
  });
  _logStatus=jetzt; _logInit=true;
}
function logMalen(){
  const el=document.getElementById('logliste'); if(!el)return;
  if(!logEintraege.length){el.innerHTML='<div class="leer" style="text-align:left">Noch keine Ereignisse in dieser Sitzung. Hier erscheinen Downloads, sobald sie starten, fertig werden oder fehlschlagen — die Übersicht oben zeigt den Gesamtstand.</div>'; return;}
  el.innerHTML=logEintraege.map(e=>{
    const t=new Date(e.t).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
    return `<div class="logrow ${e.typ}"><span class="logt">${t}</span><span class="logx">${esc(e.text)}</span></div>`;
  }).join('');
}
function logLeeren(){logEintraege=[]; logMalen();}

/* Auto-Tagging-Fortschritt (aus /api/status) in plinfo + Log */
let _atWarAktiv=false;
function autotagStatus(){
  const at=daten&&daten.autotag; if(!at)return;
  const info=document.getElementById('plinfo');
  if(at.laeuft)plInfo(`🏷 Auto-Tagging läuft … ${at.erledigt}/${at.gesamt} geprüft · ${at.getaggt} getaggt`, true);
  if(_atWarAktiv&&!at.laeuft){
    logPush('🏷 Auto-Tagging fertig: '+at.getaggt+' von '+at.gesamt+' Titeln getaggt','fertig');
    if(info)info.textContent='🏷 Auto-Tagging fertig — '+at.getaggt+' getaggt ✓';
    libLaden();                                        // neue Künstler/Album-Felder anzeigen
  }
  _atWarAktiv=!!at.laeuft;
}

/* Einstellungen als Modal (aus dem ⚙-Zahnrad). Die Karte lebt aus HTML-Gründen erst
   in #view-add und wird beim Start einmalig ins Modal umgezogen. */
function einstellungenModalInit(){
  const card=document.getElementById('settingscard'), body=document.getElementById('settingsbody');
  if(card&&body&&card.parentNode!==body)body.appendChild(card);
}
function einstellungenOeffnen(){
  const alt=document.getElementById('optionen'); if(alt)alt.remove();
  einstellungenModalInit();
  const m=document.getElementById('settingsmodal'); if(m)m.style.display='flex';
}
function settingsZu(){const m=document.getElementById('settingsmodal'); if(m)m.style.display='none';}
function hilfeModal(an){const m=document.getElementById('hilfemodal'); if(m)m.style.display=an?'flex':'none';}

/* ---- Command-Bar oben: Download, Live-Queue, Now-Playing, Zwischenablage ---- */
function qualMerken(v){                               // Qualitätswahl fuer naechsten Start sichern
  fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({standard_qualitaet:v})});
  const a=document.getElementById('cmd-qual'), b=document.getElementById('qual');
  if(a)a.value=v; if(b)b.value=v;
}
/* ---- Ein Feld für alles (Build 126) ---------------------------------------
   JB: „Download / Playlist laden / Abonnieren sind drei zu ähnliche Knöpfe."
   Jetzt genügt Enter im Feld — den Typ erkennt die App am Link (link_deuten
   im Backend, EINE Wahrheit, ohne Netz). Gefragt wird nur, wo die Absicht
   wirklich offen ist: Kanal = laden oder abonnieren, watch?v=…&list= = eines
   oder alle. Die Antwort lässt sich merken und im ⚙-Menü wieder umstellen. */
async function cmdDownload(){
  const inp=document.getElementById('cmd-url'); const url=(inp.value||'').trim(); if(!url)return;
  let d=null;
  try{const r=await fetch('/api/link_deuten',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url})}); d=await r.json();}catch(e){}
  if(!d||d.typ==='unbekannt'){toast('Das sieht nicht nach einer Adresse aus — bitte einen Link einfügen.');return;}
  if(d.eindeutig) linkAusfuehren(url,d.typ,null); else linkFrage(d,url);
}
async function linkAusfuehren(url,typ,wahl){
  const q=document.getElementById('cmd-qual').value;
  if(typ==='kanal'&&wahl==='abo'){                     // abonnieren statt laden
    toast('📡 Kanal wird abonniert …');
    let r=null; try{r=await (await fetch('/api/abo',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({art:'create',url,qualitaet:q})})).json();}catch(e){}
    if(!r||r.fehler){toast((r&&r.fehler)||'Abo ließ sich nicht anlegen.');return;}
    cmdFeldLeeren(); toast('📡 Abonniert: „'+(r.name||'Kanal')+'" — neue Folgen kommen von allein.');
    try{abosZeigen();}catch(e){}
    return;
  }
  // Alles, was eine ganze Sammlung ist, geht über den bewährten Weg mit
  // Anzahl + Größenschätzung + Rückfrage (ganzerKanal) — der zeigt vorher,
  // was auf JB zukommt, statt wortlos 500 Downloads zu starten.
  if(typ==='playlist'||typ==='mix'||typ==='kanal'||(typ==='video_in_playlist'&&wahl==='alle')){
    ganzerKanal(null,url); return;
  }
  await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({urls:url,qualitaet:q,ganze_liste:false})});
  cmdFeldLeeren(); laden();
}
function cmdFeldLeeren(){
  const inp=document.getElementById('cmd-url'); if(inp)inp.value='';
  try{cmdClipVerstecken();}catch(e){}
}
function linkFrage(d,url){
  // Schwebende Fläche: gehört an den <body> (Build-125-Regel — sonst sperrt
  // ein Eltern-Element mit Containment sie in seinen Stapel-Kontext ein).
  document.querySelectorAll('#linkfrage').forEach(x=>x.remove());
  const m=document.createElement('div'); m.className='panelmenu'; m.id='linkfrage';
  m.style.minWidth='300px';
  // Build 127 (JB): KEIN „immer so"-Haken. JB: „diese Abfrage ist meiner
  // Meinung nach immer relevant" — bei einem Kanal will man mal abonnieren
  // und mal laden, das hängt am Kanal und nicht an einer Voreinstellung.
  // Eine gemerkte Antwort wäre hier kein Komfort, sondern eine Falle.
  m.innerHTML='<div style="font-size:11.5px;color:#8a7d74;padding:2px 6px 7px">'+esc(d.frage)+'</div>'+
    d.optionen.map(o=>'<button class="mbtn" data-id="'+o.id+'">'+esc(o.text)+'</button>').join('');
  document.body.appendChild(m);
  const feld=document.getElementById('cmd-url');
  popoverBei(m, feld.getBoundingClientRect());
  m.querySelectorAll('.mbtn').forEach(b=>b.onclick=()=>{
    m.remove(); linkAusfuehren(url,d.typ,b.dataset.id);
  });
  menuSchliesser(m);
}
/* „Ganzen Kanal laden" (JB 22.07.): Kanal-Link auflösen (Backend normalisiert
   /@name -> /videos, sonst kämen nur die Reiter), Anzahl zeigen, nach Rückfrage
   ALLE Videos in die Warteschlange (ganze_liste=true; schon Geladenes wird
   übersprungen). Funktioniert auch für reine Playlist-Links. */
/* Größen-Schätzung (Build 105, JB: „wenn ich 5000 Songs lade und auf einmal
   10 TB laden muss, habe ich ein Problem") — MB/min je Qualität kommen als
   MEDIAN aus den ECHTEN eigenen Downloads (Fallback-Erfahrungswerte, wenn
   zu wenig Daten). Ehrlich als „≈"-Schätzung beschriftet. */
let _mbFaktoren=null;
fetch('/api/schaetzfaktoren').then(r=>r.json()).then(d=>{_mbFaktoren=d;}).catch(()=>{});
function groesseSchaetzen(dauerSek,qual){
  if(!dauerSek||!_mbFaktoren||!_mbFaktoren[qual])return '';
  const mb=dauerSek/60*_mbFaktoren[qual];
  const txt=mb>=1024?((mb/1024).toFixed(1)+' GB'):(Math.round(mb)+' MB');
  return '\\n≈ '+txt+' (Erfahrungswert deiner Bibliothek)';
}
async function ganzerKanal(btn,urlAus){
  // Build 126: nimmt die Adresse jetzt auch als Parameter entgegen — das
  // eine Feld ruft den Weg direkt auf, statt dass er selbst im Feld nachsieht.
  const inp=document.getElementById('cmd-url');
  const url=(urlAus||inp.value||'').trim();
  if(!url){toast('Erst einen Kanal- oder Playlist-Link oben einfügen.');return;}
  // Mix/Radio (Build 98, JB): ERST die Wunsch-Anzahl fragen, DANN nur so viele
  // aufloesen — Mixe sind endlos + nicht-deterministisch (JB mass 1877 vs 563),
  // die Voll-Aufloesung war eine 20-s-Sanduhr fuer eine falsche Zahl.
  const mix=/[?&]list=(RD|UL)/.test(url);
  let limit=null;
  if(mix){
    const w=prompt('YouTube-Mix (Radio) erkannt — der ist endlos.\\n\\nWie viele Titel ab dem Startvideo laden? (1–500)','50');
    if(w===null)return;
    limit=Math.max(1,Math.min(500,parseInt(w,10)||50));
  }
  if(btn){btn.disabled=true; btn.dataset.alt=btn.textContent; btn.textContent='⏳';}
  toast(mix?('🔎 Mix wird aufgelöst (erste '+limit+' Titel)…'):'🔎 Kanal wird aufgelöst…');
  let d=null;
  try{const r=await fetch('/api/kanal_info?url='+encodeURIComponent(url)+(mix?('&limit='+limit):'')); d=await r.json();}catch(e){}
  if(btn){btn.disabled=false; btn.textContent=btn.dataset.alt||'📺';}
  if(!d||!d.ok){toast((d&&d.fehler)||'Kanal/Playlist nicht gefunden.'); return;}
  const q=document.getElementById('cmd-qual').value;
  if(d.mix){                                           // Mix: endlos, Anzahl steht schon fest
    const gr=groesseSchaetzen(d.dauer_summe,q);
    const qtext=({beste:'Beste',audio:'MP3'}[q])||q;
    if(!confirm('„'+d.name+'"\\n\\nDie ersten '+d.anzahl+' Titel des Mixes (ab dem Startvideo) in Qualität '+qtext+' laden?'+gr+'\\nSchon geladene werden übersprungen.'))return;
    await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({urls:d.url,qualitaet:q,ganze_liste:true,limit:limit})});
    cmdFeldLeeren(); laden();
    try{dlboxTab('queue');}catch(e){}
    toast('📺 „'+d.name+'": '+d.anzahl+' Titel werden geladen.');
    return;
  }
  mengenRegler(d,q);                                   // Build 127: JBs Regler
}
/* ---- Mengen-Regler (Build 127) --------------------------------------------
   JB: „ich würde gerne einen Regler haben bei alle Videos jetzt laden (das
   soll anzeigen wie viele Videos es insgesamt sind und die Option
   älteste/neueste zuerst ist relevant)."
   Der frühere confirm-Kasten konnte nur ganz oder gar nicht. Jetzt steht die
   Gesamtzahl da, der Regler wählt die Menge, und die Richtung entscheidet,
   von WELCHEM Ende gezählt wird — bei einer Serie will man die ältesten,
   bei einem Nachrichtenkanal die neuesten. Dasselbe Begriffspaar wie im
   Abo-Backkatalog (⏮/⏭), damit es sich überall gleich anfühlt. */
function mengenRegler(d,q){
  document.querySelectorAll('#mengenregler').forEach(x=>x.remove());
  const gesamt=d.anzahl;
  let menge=gesamt, richtung='alt';                    // Standard: alles, chronologisch
  const m=document.createElement('div'); m.className='panelmenu'; m.id='mengenregler';
  m.style.minWidth='330px';
  m.innerHTML=
    '<div style="font-size:12.5px;color:#e7dccf;padding:2px 6px 1px;font-weight:600">'+esc(d.name)+'</div>'+
    '<div style="font-size:11.5px;color:#8a7d74;padding:0 6px 8px">'+gesamt+(d.gedeckelt?'+':'')+' Videos gefunden'+
      (d.gedeckelt?' (Obergrenze erreicht)':'')+'</div>'+
    '<div style="padding:0 6px"><input type="range" id="mr-range" min="1" max="'+gesamt+'" value="'+gesamt+'" style="width:100%"></div>'+
    '<div class="mzeile"><span id="mr-zahl" style="color:var(--akz2);font-weight:700"></span>'+
      '<span id="mr-groesse" style="font-size:11px;color:#8a7d74"></span></div>'+
    '<div class="msep"></div>'+
    '<div class="mzeile"><span>Reihenfolge</span><span style="display:flex;gap:3px">'+
      '<button class="btn mini" id="mr-alt" title="Vom Anfang des Kanals — für Serien, die man der Reihe nach sieht">⏮ älteste</button>'+
      '<button class="btn mini" id="mr-neu" title="Die neuesten Videos zuerst">⏭ neueste</button></span></div>'+
    '<div class="msep"></div>'+
    '<button class="mbtn" id="mr-los"></button>';
  document.body.appendChild(m);
  const feld=document.getElementById('cmd-url');
  popoverBei(m, feld.getBoundingClientRect());
  const range=m.querySelector('#mr-range');
  const malen=()=>{
    menge=parseInt(range.value,10)||1;
    const alle=(menge>=gesamt);
    m.querySelector('#mr-zahl').textContent=alle?('alle '+gesamt):(menge+' von '+gesamt);
    // Größe anteilig schätzen: die Dauer-Summe gilt für ALLE Videos.
    const anteil=d.dauer_summe?Math.round(d.dauer_summe*menge/gesamt):0;
    m.querySelector('#mr-groesse').textContent=(groesseSchaetzen(anteil,q)||'').replace(/^\\n/,'');
    m.querySelector('#mr-alt').classList.toggle('an',richtung==='alt');
    m.querySelector('#mr-neu').classList.toggle('an',richtung==='neu');
    m.querySelector('#mr-los').textContent='⬇ '+(alle?('alle '+gesamt):(menge+''))+' laden — '+
      (richtung==='alt'?'älteste zuerst':'neueste zuerst');
  };
  range.oninput=malen;
  m.querySelector('#mr-alt').onclick=()=>{richtung='alt'; malen();};
  m.querySelector('#mr-neu').onclick=()=>{richtung='neu'; malen();};
  m.querySelector('#mr-los').onclick=async()=>{
    m.remove();
    await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({urls:d.url,qualitaet:q,ganze_liste:true,
                           menge:(menge>=gesamt?0:menge),richtung})});
    cmdFeldLeeren(); laden();
    try{dlboxTab('queue');}catch(e){}
    toast('📺 „'+d.name+'": '+menge+' Videos werden geladen ('+(richtung==='alt'?'älteste':'neueste')+' zuerst). Schon geladene werden übersprungen.');
  };
  malen();
  menuSchliesser(m);
}
async function appBeenden(){
  if(!confirm('SyncYouTube komplett beenden?\\n\\nLaufende Downloads werden pausiert (setzen beim naechsten Start fort). Auch der Hintergrund-Dienst wird geschlossen.'))return;
  try{await fetch('/api/beenden',{method:'POST'});}catch(e){}
  document.body.innerHTML='<div style="padding:40px;font:16px system-ui;color:#c9bcae">SyncYouTube wurde beendet. Dieses Fenster kann geschlossen werden.</div>';
}
function cmdDlRow(i){                                  // eine Download-Zeile (Dateiname + Balken), Klick = Pause
  const p=Math.round(i.prozent||0);
  const ic={laeuft:'⏬',wartend:'⏳',pausiert:'⏸',fehler:'⚠',prueft:'🔎'}[i.status]||'•';
  const rechts=i.status==='laeuft'?(p+'%'):(i.status==='fehler'?'Fehler':(i.status==='pausiert'?'Pause':(i.status==='prueft'?'prüft':'wartet')));
  return `<div class="dlrow ${i.status}" onclick="dlKlick('${i.id}','${i.status}')" title="${esc(i.titel||'')} — Klick: Pause / Fortsetzen">`+
    `<span class="dlic">${ic}</span>`+
    `<span class="dltitel">${esc((i.titel||'…').slice(0,70))}</span>`+
    `<span class="dlbar"><i style="width:${p}%"></i></span>`+
    `<span class="dlpct">${esc(rechts)}</span>`+
    `<button class="dlx" onclick="event.stopPropagation();aktion('${i.id}','entfernen')" title="Abbrechen &amp; aus der Warteschlange entfernen (Dateien bleiben)">✖</button></div>`;
}
function cmdQueueRender(items){                        // rechte Spalte: alle aktiven Downloads untereinander
  const el=document.getElementById('cmd-queue'); if(!el)return;
  const aktiv=(items||[]).filter(i=>i.status!=='fertig'&&i.status!=='uebersprungen');
  el.innerHTML=aktiv.length?aktiv.slice(0,40).map(cmdDlRow).join(''):'<span class="cmd-empty">// keine aktiven Downloads</span>';
}
function dlKlick(id,status){                           // Download anhalten / fortsetzen
  if(status==='laeuft')aktion(id,'pause');
  else if(status==='pausiert'||status==='fehler')aktion(id,'weiter');
}
/* „Now Playing"-Mini in der Command-Bar: Steuerung + Titel, darunter Spulleiste
   mit Zeitanzeige (JB 13.07.). malen() ruft das jede Sekunde — damit die
   Spulleiste beim Ziehen nicht unter der Maus weggerendert wird, baut die
   Funktion das HTML nur bei ECHTER Änderung neu (Signatur-Vergleich); die
   laufende Zeit frischt cmdSeekTick() gezielt per textContent auf. */
let cmdNowSig='', cmdSeekAktiv=false;
function cmdNowRender(){
  const el=document.getElementById('cmd-now'); if(!el)return;
  // Build 117 (JB-Go): dieselben Transport-Knöpfe standen doppelt da — hier
  // UND im Player. Ist der Player offen, führt er; die Kopfleiste behält nur
  // Titel, Zeitleiste, Lautstärke und Radio (die hat der Player nicht).
  // Build 120 (JB-Fund): NICHT auf das Audio-Element prüfen — das entsteht
  // beim Abspielen auch ohne sichtbaren Player, dann verschwanden hier alle
  // Knöpfe, obwohl es keinen Ersatz gab. Es zählt nur die wirklich SICHTBARE
  // Player-Fläche.
  const pmedia=document.getElementById('pl-media');
  const playerSichtbar=!!(pmedia&&pmedia.getBoundingClientRect().height>40
                          &&getComputedStyle(pmedia).display!=='none');
  document.body.classList.toggle('hat-player', playerSichtbar);
  const k=playerState.queue[playerState.idx], x=k?libFind(k):null;
  el.classList.toggle('spielt', !!x);                  // Rahmen glimmt, wenn etwas läuft
  const sig=[k||'',x?x.titel:''].join('|');            // Play/Pause & Toggles zieht transportRender nach
  if(sig===cmdNowSig){transportRender();cmdSeekTick();return;}
  cmdNowSig=sig;
  const titel=x?`<div class="cmd-nowtitel" title="${esc(x.titel)}">♪ ${esc((x.titel||'').slice(0,90))}</div>`
               :'<div class="cmd-nowtitel cmd-nolabel">// nichts läuft — ▶ startet die Bibliothek</div>';
  el.innerHTML=`<div class="mp-row">`+
    `<button class="mp-btn mp-tog" data-tr="shuffle" onclick="shuffleToggle()">${ico('shuffle')}</button>`+
    `<button class="mp-btn" onclick="playerPrev()" title="Vorheriger">${ico('prev')}</button>`+
    `<button class="mp-btn mp-play" data-tr="pp" onclick="cmdPlayPause()">${ico('play')}</button>`+
    `<button class="mp-btn" onclick="playerNext()" title="Nächster">${ico('next')}</button>`+
    `<button class="mp-btn mp-tog" data-tr="repeat" onclick="repeatCycle()">${ico('repeat')}</button>`+
    `<button class="mp-btn mp-tog mp-radio" data-tr="radio" onclick="radioStart()" title="📻 Radio — endloser Mix aus deiner Bibliothek">📻</button>`+
    `<button class="mp-btn mp-tog herz${(libFind(aktKey())||{}).herz?' an':''}" data-tr="herz" onclick="herzToggle(aktKey())" title="❤ Lieblingssong an/aus">${(libFind(aktKey())||{}).herz?'♥':'♡'}</button>`+
    `<button class="mp-btn mp-tog mp-art" data-tr="art" onclick="playArtMenu(event)"></button>`+
    `<button class="mp-btn mp-yt" onclick="playerYoutube()" title="Diesen Titel auf YouTube öffnen — springt zur aktuellen Stelle">${ico('yt')}</button>`+
    `<button class="mp-btn" onclick="playerLinkKopieren()" title="YouTube-Link kopieren (zum Teilen, OHNE Zeitstempel)">🔗</button>`+
    `<span class="pl-bvolwrap mp-vol">🔊<input type="range" class="pl-bvol" min="0" max="100" value="${plVol}" oninput="plbVol(this.value)" title="Lautstärke"></span>`+
    `</div>`+titel+
    `<div class="cmd-seekline"><span class="cmd-time" id="cmd-t0">0:00</span>`+
    `<input type="range" id="cmd-seek" min="0" max="1000" value="0" disabled `+
    `title="Im Lied spulen" oninput="cmdSeekDrag(this.value)" onchange="cmdSeekEnd(this.value)" `+
    `onpointerdown="cmdSeekAktiv=true" onpointerup="cmdSeekAktiv=false">`+
    `<span class="cmd-time" id="cmd-t1">0:00</span></div>`;
  transportRender(); cmdSeekTick();
}
function cmdSeekDrag(v){                               // beim Ziehen läuft nur die Zeitanzeige mit
  const pe=document.getElementById('pl-el');
  const t0=document.getElementById('cmd-t0');
  if(pe&&pe.duration&&t0)t0.textContent=zeit(v/1000*pe.duration);
}
function cmdSeekEnd(v){                                // losgelassen -> wirklich spulen
  const pe=document.getElementById('pl-el');
  if(pe&&pe.duration)pe.currentTime=v/1000*pe.duration;
  cmdSeekAktiv=false;
}
function cmdSeekTick(){                                // Position/Zeiten nachführen (auch via setInterval)
  const s=document.getElementById('cmd-seek'), t0=document.getElementById('cmd-t0'),
        t1=document.getElementById('cmd-t1'), pe=document.getElementById('pl-el');
  if(!s||!t0||!t1)return;
  if(!pe||!pe.duration){s.value=0;s.disabled=true;t0.textContent='0:00';t1.textContent='0:00';return;}
  s.disabled=false;
  if(!cmdSeekAktiv){s.value=Math.round(pe.currentTime/pe.duration*1000);t0.textContent=zeit(pe.currentTime);}
  t1.textContent=zeit(pe.duration);
}
setInterval(cmdSeekTick,500);
function cmdPlayPause(){
  if(vlcAktiv()){plTogglePlay(); return;}    // Gerät VLC: derselbe Weg wie überall
  const pe=document.getElementById('pl-el');
  if(!pe){ if(libdaten.length)playGefilterte(); return; }   // nichts läuft -> Bibliothek starten (bei 🔀 gemischt)
  if(pe.paused)pe.play(); else pe.pause();
  cmdNowRender();
}
/* Zwischenablage-Wächter (JDownloader-Stil): YouTube-Link erkannt -> anbieten.
   WICHTIG: nur lesen, wenn der Browser das OHNE Rückfrage erlaubt — sonst zeigt
   z.B. Firefox bei jedem Fenster-Fokus ein „Einfügen"-Popup an der Maus, das
   den ersten Klick/Rechtsklick schluckt (JB 13.07.). Wo die Erlaubnis fehlt,
   greift stattdessen die Einfügen-Erkennung: Strg+V irgendwo in der App. */
let cmdClipLast='';
async function cmdClipCheck(){
  try{
    if(!navigator.permissions)return;
    const p=await navigator.permissions.query({name:'clipboard-read'});
    if(p.state!=='granted')return;                     // würde nachfragen -> lieber gar nicht
    const t=((await navigator.clipboard.readText())||'').trim();
    if(t&&t!==cmdClipLast&&/(?:youtube\\.com|youtu\\.be)\\//i.test(t)){cmdClipLast=t; cmdClipZeigen(t);}
  }catch(e){}                                          // Browser kennt die Abfrage nicht (Firefox) -> still lassen
}
document.addEventListener('paste',(e)=>{               // Strg+V in der App = Link anbieten
  try{
    const t=((e.clipboardData||{}).getData('text')||'').trim();
    if(t&&/(?:youtube\\.com|youtu\\.be)\\//i.test(t)&&(e.target||{}).id!=='cmd-url'){cmdClipLast=t; cmdClipZeigen(t);}
  }catch(e2){}
});
function cmdClipZeigen(url){
  const b=document.getElementById('cmd-clip'); if(!b)return;
  b.style.display='flex';
  b.innerHTML=`🔗 Link erkannt: <span class="clipurl">${esc(url)}</span>`+
    `<button class="btn mini" onclick="cmdClipAdd()">⬇ hinzufügen</button>`+
    `<button class="btn mini" onclick="cmdClipVerstecken()">✕</button>`;
}
function cmdClipAdd(){document.getElementById('cmd-url').value=cmdClipLast; cmdClipVerstecken(); cmdDownload();}
function cmdClipVerstecken(){const b=document.getElementById('cmd-clip'); if(b)b.style.display='none';}
window.addEventListener('focus',cmdClipCheck);

/* ---- Link ins Fenster ziehen = Download (aus dem Browser / einer Textstelle) ---- */
document.addEventListener('dragover',e=>{
  const ty=e.dataTransfer&&[...e.dataTransfer.types];
  if(ty&&(ty.includes('text/uri-list')||ty.includes('text/plain'))){e.preventDefault(); document.body.classList.add('dragziel');}
});
document.addEventListener('dragleave',e=>{
  if(e.clientX<=0||e.clientY<=0||e.clientX>=window.innerWidth||e.clientY>=window.innerHeight)document.body.classList.remove('dragziel');
});
document.addEventListener('drop',async e=>{
  document.body.classList.remove('dragziel');
  if(!e.dataTransfer)return;
  const url=(e.dataTransfer.getData('text/uri-list')||e.dataTransfer.getData('text/plain')||'').trim().split(/\\s+/)[0];
  if(!/^https?:\\/\\//i.test(url))return;              // interne Drags (Umsortieren) haben keinen http-Text
  e.preventDefault();
  const q=(document.getElementById('cmd-qual')||{}).value||'beste';
  try{await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({urls:url,qualitaet:q})});}catch(err){}
  plInfo('⬇ Per Drag&Drop hinzugefügt: '+url.slice(0,48));
  laden();
});

/* ---- Abos: Kanäle/Playlists abonnieren (neue Videos werden automatisch geholt).
   Abo-Fenster nach Sonarr-Muster: Karte je Abo mit Format-Wahl, Regeln (⚙) und
   Backkatalog (📜) — fehlende Folgen ausgegraut, per Doppelklick/Auswahl nachladbar. ---- */
let aboState=[], aboOffen={}, aboLetzterKlick={};
async function aboPost(daten){
  const r=await fetch('/api/abo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(daten)});
  return await r.json();
}
async function aboLaden(){try{const r=await fetch('/api/abos'); aboState=(await r.json()).items||[]; aboMalen();}catch(e){}}
/* ---- Filme (Film-Fundament, Doku/SYNC_FILME_SPEC.md Etappe 7) --------------
   Anzeige-Minimum: die serverseitigen Reihen als Poster-Bänder, Klick spielt
   den Jellyfin-Strom im LOKALEN VLC. Das eigentliche TV-Design ist
   Teilprojekt 2 — hier geht es um den sichtbaren Beweis der Engine. */
async function filmeLaden(){
  const ziel=document.getElementById('filme-reihen'); if(!ziel)return;
  try{
    const r=await fetch('/api/filme/reihen'); const d=await r.json();
    const stand=document.getElementById('filme-stand');
    const kat=await (await fetch('/api/filme/katalog')).json();
    if(stand)stand.textContent=kat.stand?('Stand '+new Date(kat.stand*1000).toLocaleString('de-DE')+' · Server '+(kat.server_version||'?')):'';
    const reihen=[['Weiterschauen',d.weiterschauen],['Top 10',d.top],['Neu auf dem Server',d.neu]]
      .concat(Object.entries(d.genres||{}));
    const html=reihen.filter(([,liste])=>liste&&liste.length).map(([name,liste])=>
      `<div class="f-reihe"><div class="f-rtitel">${esc(name)}</div><div class="f-band">`+
      liste.map(e=>`<div class="f-kachel" onclick="tvInfo('${esc(e.id)}')" title="${esc(e.titel)}${e.jahr?' ('+e.jahr+')':''}${e.rating?' · ★'+e.rating.toFixed(1):''}${e.fsk?' · '+esc(e.fsk):''}">`+
        `<img loading="lazy" src="/api/filme/bild?id=${encodeURIComponent(e.id)}" onerror="this.style.visibility='hidden'">`+
        `<div class="f-ktitel">${esc(e.titel)}</div></div>`).join('')+
      `</div></div>`).join('');
    ziel.innerHTML=html||'<div class="hinweis">Kein Film-Katalog. Jellyfin-Zugang im Windows-Keyring (Sync-Jellyfin) einrichten, dann ⟳ Abgleichen.</div>';
  }catch(e){ziel.innerHTML='<div class="hinweis">Filme-Reihen nicht erreichbar.</div>';}
}
/* Browser-Player-Weiche (JB 06.08.: „kein externes fenster … wie bei
   netflix im Browser"): Codecs, die der Browser selbst dekodiert
   (h264/vp9/av1 + aac/mp3/opus …), laufen als <video> über den
   Server-Proxy /api/filme/direkt — ganz ohne VLC-Fenster. HEVC/AC3/DTS
   kann KEIN Browser ohne Transcoding: dort übernimmt weiter der VLC. */
function filmeBrowserKann(d){
  const v=((d&&d.video_codec)||'').toLowerCase(), a=((d&&d.audio_codec)||'').toLowerCase();
  const vOk=['h264','avc','vp8','vp9','av1'].some(x=>v.includes(x));
  const aOk=['aac','mp3','opus','vorbis','flac'].some(x=>a.includes(x));
  return vOk&&aOk;
}
async function filmePlay(id,pos){
  let meta=(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.id===id)?tvInfoDaten.d
          :(typeof tvHeroDaten!=='undefined'&&tvHeroDaten&&tvHeroDaten.id===id)?tvHeroDaten:null;
  if(!meta){try{meta=await (await fetch('/api/filme/detail?id='+encodeURIComponent(id))).json();}catch(e){}}
  const inHuelle=!!window.pywebview;
  if(meta&&filmeBrowserKann(meta)){
    tvpModus='browser'; tvpTc=false;                   // Direct Play im <video>
    tvFilmPlayer(id,(meta.titel||''),pos||0);
    return;
  }
  if(meta&&!inHuelle){
    // JB-Go 06.08. („Geh das serverseitige Transcoding an"): im Browser
    // wandelt ffmpeg unterwegs — h264 bleibt Kopie (nur Ton→AAC), Rest
    // wird libx264. In der HÜLLE bleibt der eingebettete VLC der starke
    // Weg (spielt alles nativ, null Transcode-Last).
    tvpModus='browser'; tvpTc=true;
    tvpTcVcopy=['h264','avc'].some(x=>((meta.video_codec||'').toLowerCase()).includes(x));
    tvFilmPlayer(id,(meta.titel||''),pos||0);
    return;
  }
  filmePlayVlc(id,pos);
}
async function filmePlayVlc(id,pos){
  tvpModus='vlc';
  // Vollbild-Ordnung (JB: „nicht im Vordergrund"): erst das BROWSER-Vollbild
  // verlassen — sonst kämpfen zwei Fullscreens und das VLC-Bild liegt hinten.
  if(document.fullscreenElement){try{document.exitFullscreen();}catch(e){}}
  try{
    const r=await fetch('/api/filme/play',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id, vol:plVol, pos:pos||0})});
    const d=await r.json();
    if(d.fehler){toast('🎬 '+d.fehler); return;}
    const titel=(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.titel)||'';
    tvFilmPlayer(id,titel,pos||0);                     // die Fernbedienung (Build 187)
  }catch(e){toast('🎬 Abspielen fehlgeschlagen.');}
}
/* ---- Film-Player-Screen (Build 187) ---------------------------------------
   JB: „der Player hat keine controls, kein play, kein exit …" — das
   VLC-Vollbild ist ein NACKTES Renderfenster (libvlc hat keine UI). Dieses
   Overlay ist die Fernbedienung dazu: eigener 1-s-Status-Takt, Play/Pause,
   ±10 s, klickbarer Balken, Lautstärke, Beenden. Tasten: Leertaste/Enter =
   Pause · ←/→ = ±10 s · ↑/↓ = Lautstärke · Esc = Beenden. */
let tvpTimer=null, tvpPos=0, tvpDauer=0, tvpOffen=false, tvpLief=false, tvpTicks=0;
let tvpMeta=null, tvpAktiv=0;                          // Idle-Uhr (Netflix-Auto-Hide)
let tvpModus='vlc', tvpIdAkt='';                       // Browser-<video> oder VLC
let tvpTc=false, tvpTcOffset=0, tvpTcVcopy=false;      // Transcode-Strom (JB-Go)
function tvpDirektSrc(start){
  return '/api/filme/direkt?id='+encodeURIComponent(tvpIdAkt)+
    (tvpTc?('&tc=1'+(tvpTcVcopy?'&vcopy=1':'')+'&start='+Math.max(0,Math.round(start||0))):'');
}
/* Eine Fernbedienung, zwei Motoren: im Browser-Modus steuern die Befehle
   das <video>-Element direkt, sonst gehen sie an den VLC. Beim
   Transcode-Strom beginnt jedes <video> bei 0 — tvpTcOffset rechnet die
   echte Film-Position dazu, Seek startet den Strom an neuer Stelle. */
async function tvpBefehl(cmd,daten){
  if(tvpModus!=='browser')return vlcBefehl(cmd,daten);
  const v=document.getElementById('tvp-video');
  if(!v)return {zustand:'aus', key:'', verfuegbar:true};
  if(cmd==='toggle'){if(v.paused)v.play().catch(()=>{}); else v.pause();}
  else if(cmd==='seek'){
    const ziel=(daten&&daten.wert)||0;
    if(tvpTc){tvpTcOffset=ziel; v.src=tvpDirektSrc(ziel); v.play().catch(()=>{});}
    else{try{v.currentTime=ziel;}catch(e){}}
  }
  else if(cmd==='vol')v.volume=Math.max(0,Math.min(1,((daten&&daten.wert)||0)/100));
  else if(cmd==='rate')v.playbackRate=(daten&&daten.wert)||1;
  else if(cmd==='stop'){v.pause(); v.removeAttribute('src'); try{v.load();}catch(e){}}
  else if(cmd==='spuren')return {ton:[],sub:[],rate:v.playbackRate||1};
  const aus=v.ended||!v.currentSrc;
  const metaDauer=(tvpMeta&&tvpMeta.laufzeit_min)?tvpMeta.laufzeit_min*60:0;
  return {zustand:aus?'aus':(v.paused?'pause':'spielt'),
          key:aus?'':'film:'+tvpIdAkt,
          pos:(tvpTc?tvpTcOffset:0)+(v.currentTime||0),
          dauer:tvpTc?metaDauer:(isFinite(v.duration)?v.duration:metaDauer),
          verfuegbar:true};
}
function tvFilmPlayer(id,titel,pos){
  tvpOffen=true; tvpPos=pos||0; tvpDauer=0; tvpLief=false; tvpTicks=0; tvpAktiv=Date.now();
  tvpIdAkt=id;
  tvpMeta=(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.id===id)?tvInfoDaten.d
         :(typeof tvHeroDaten!=='undefined'&&tvHeroDaten&&tvHeroDaten.id===id)?tvHeroDaten
         :{titel:titel||''};                           // Hero-Start: Meta trotzdem da
  let el=document.getElementById('tv-player');
  if(!el){el=document.createElement('div'); el.id='tv-player';}
  (document.fullscreenElement||document.body).appendChild(el);
  el.style.display='flex';
  // Netflix-Layout (JBs Player-Bilder): ← oben links, Leiste UNTEN über die
  // volle Breite (roter Balken + Zeit rechts), darunter ⏯ ±10 🔊 links und
  // der Titel mittig. Bei Inaktivität blendet alles aus (tvpIdleTick).
  // Browser-Modus: das <video> IST das Bild (Netflix-Weg, JB 06.08.) —
  // Pause zeigt automatisch das echte Standbild des Films.
  if(tvpModus==='browser'&&tvpTc)tvpTcOffset=pos||0;   // Strom startet AB pos
  const medien=tvpModus==='browser'
    ?`<video id="tvp-video" class="tvp-video" autoplay playsinline `+
     `src="${tvpDirektSrc(pos||0)}"></video>`
    :`<img class="tvp-bg" src="/api/filme/bild?id=${encodeURIComponent(id)}&art=Backdrop" onerror="this.style.visibility='hidden'">`;
  el.innerHTML=
    medien+
    `<img id="tvp-standbild" class="tvp-standbild" style="display:none">`+
    `<div class="tvp-ui">`+
      `<button class="tvp-zurueck" onclick="filmStopp()" title="Beenden (Esc)">←</button>`+
      `<div class="tvp-unten">`+
        `<div class="tvp-balkenzeile"><div class="tvp-balkenwrap" onclick="tvpSeek(event)">`+
          `<div class="tvp-balken"><div id="tvp-fuell"></div></div></div>`+
          `<span id="tvp-zeit" class="tvp-zeit">–</span></div>`+
        `<div class="tvp-reihe">`+
          `<button class="tvp-ib" id="tvp-pp" onclick="tvpBefehl('toggle');setTimeout(tvpTick,300)" title="Pause/Weiter (Leertaste)">${ico('pause')}</button>`+
          `<button class="tvp-ib" onclick="tvpRel(-10)" title="10 s zurück">${ico('r10')}</button>`+
          `<button class="tvp-ib" onclick="tvpRel(10)" title="10 s vor">${ico('f10')}</button>`+
          `<span class="pl-bvolwrap" style="color:#fff">🔊<input type="range" class="pl-bvol" min="0" max="100" value="${plVol}" oninput="plbVol(this.value);tvpBefehl('vol',{wert:plVol})"></span>`+
          `<div class="tvp-mtitel">${esc(tvpMeta.titel||'')}</div>`+
          `<span class="tvp-rechts">`+
            `<button class="tvp-ib" onclick="tvpPanel('spuren')" title="Ton & Untertitel">${ico('sub')}</button>`+
            `<button class="tvp-ib" onclick="tvpPanel('tempo')" title="Wiedergabetempo">${ico('speed')}</button>`+
            `<button class="tvp-ib" onclick="tvpVollbild()" title="Vollbild an/aus">${ico('full')}</button>`+
            `<button class="tvp-ib" onclick="filmStopp()" title="Beenden (Esc)">${ico('kreuz')}</button>`+
          `</span>`+
        `</div>`+
      `</div>`+
      `<div id="tvp-panel" style="display:none"></div>`+
      `<div class="tvp-lade" id="tvp-lade"><div class="tvp-spin"></div>`+
        `<span id="tvp-lade-text">${pos>0?'Springt zu '+zeit(pos)+' …':'Lädt …'}</span></div>`+
      `<div class="tvp-idle" id="tvp-idle" style="display:none">`+
        `<div class="tvp-idle-klein">Du siehst</div>`+
        `<div class="tvp-idle-titel">${esc(tvpMeta.titel||'')}</div>`+
        `<div class="tvp-idle-meta">${[tvpMeta.jahr,esc(tvpMeta.fsk||''),tvpMeta.laufzeit_min?tvpMeta.laufzeit_min+' min':''].filter(Boolean).join('   ')}</div>`+
        `<div class="tvp-idle-besch">${esc((tvpMeta.beschreibung||'').slice(0,220))}</div>`+
        `<div class="tvp-idle-paused">Pausiert</div>`+
      `</div>`+
    `</div>`;
  ['pointermove','pointerdown','keydown'].forEach(evn=>el.addEventListener(evn,tvpWach));
  if(tvpModus==='browser'){
    const v=document.getElementById('tvp-video');
    if(v){
      v.volume=Math.max(0,Math.min(1,plVol/100));
      if(pos>0&&!tvpTc)v.addEventListener('loadedmetadata',()=>{try{v.currentTime=pos;}catch(e){}},{once:true});
      v.addEventListener('error',()=>{                 // Selbstheilungs-Kette:
        if(!tvpOffen)return;                           // direkt → Transcoder → VLC
        if(!tvpTc){
          toast('🎬 Format sperrt sich — der Transcoder übernimmt.');
          tvpTc=true; tvpTcVcopy=false; tvpTcOffset=tvpPos||pos||0;
          v.src=tvpDirektSrc(tvpTcOffset); v.play().catch(()=>{});
          return;
        }
        toast('🎬 Browser kann dieses Format nicht — VLC übernimmt.');
        tvpZu(); filmePlayVlc(id,pos);
      });
      v.addEventListener('click',ev=>{ev.stopPropagation(); tvpWach();
        tvpBefehl('toggle'); setTimeout(tvpTick,200);});   // Netflix: Klick = Pause
    }
  }
  // Die VLC-Fernbedienung geht NUR bei MEHREREN Monitoren selbst ins
  // Vollbild (auf einem verdeckte sie das VLC-Bild); der BROWSER-Player
  // darf immer — sein Bild liegt ja IM Overlay.
  try{
    if((tvpModus==='browser'||screen.isExtended)&&el.requestFullscreen)
      el.requestFullscreen().catch(()=>{});
  }catch(e){}
  if(!tvpTimer)tvpTimer=setInterval(tvpTick,1000);
  setTimeout(tvpTick,600);
}
function tvpWach(){
  tvpAktiv=Date.now();
  const el=document.getElementById('tv-player'); if(el)el.classList.remove('idle');
  const idle=document.getElementById('tvp-idle'); if(idle)idle.style.display='none';
}
/* Player-Settings (JB 06.08.: „es fehlen noch settings im player. Untertitel,
   playback speed, Vollbild") — Panels im Netflix-Stil über der Leiste. */
let tvpRateWert=1, tvppFokus=0;
function tvppFokusMalen(kn){
  kn.forEach((k,i)=>k.classList.toggle('tv-fokus',i===tvppFokus));
  const z=kn[tvppFokus]; if(z&&z.scrollIntoView)z.scrollIntoView({block:'nearest'});
}
async function tvpPanel(art){
  const p=document.getElementById('tvp-panel'); if(!p)return;
  tvpWach(); tvppFokus=0;
  if(p.dataset.art===art&&p.style.display!=='none'){p.style.display='none'; return;}
  p.dataset.art=art;
  if(art==='tempo'){
    p.innerHTML='<div class="tvpp-titel">Wiedergabetempo</div><div class="tvpp-reihe">'+
      [0.5,0.75,1,1.25,1.5].map(x=>`<button class="tvpp-knopf${Math.abs(x-tvpRateWert)<0.01?' an':''}"`+
        ` onclick="tvpRate(${x})">${x===1?'1x (Normal)':x+'x'}</button>`).join('')+'</div>';
  }else{
    p.innerHTML='<div class="tvpp-titel">Lädt …</div>'; p.style.display='block';
    let s={}; try{s=await tvpBefehl('spuren')||{};}catch(e){}
    // Race (Nachtprüfung): wurde das Panel während des Ladens geschlossen
    // oder umgeschaltet, das späte Ergebnis NICHT mehr malen.
    if(p.dataset.art!=='spuren'||p.style.display==='none')return;
    tvpRateWert=s.rate||tvpRateWert;
    const li=(arr,aktiv,art2)=>(arr||[]).filter(t=>art2==='sub'||t.id>=0).map(t=>
      `<button class="tvpp-knopf${t.id===aktiv?' an':''}" onclick="tvpSpur('${art2}',${t.id})">`+
      esc(art2==='sub'&&t.id<0?'Aus':(t.name||('Spur '+t.id)))+'</button>').join('');
    p.innerHTML='<div class="tvpp-spalten">'+
      `<div><div class="tvpp-titel">Ton</div>${li(s.ton,s.ton_aktiv,'ton')||'<span class="tvpp-leer">keine Spuren</span>'}</div>`+
      `<div><div class="tvpp-titel">Untertitel</div>${li(s.sub,s.sub_aktiv,'sub')||'<span class="tvpp-leer">keine</span>'}</div>`+
      '</div>';
  }
  p.style.display='block';
}
async function tvpSpur(art,id){
  try{await vlcBefehl('spur',{art,id});}catch(e){}     // Spuren gibt es nur im VLC
  const p=document.getElementById('tvp-panel'); if(p)p.style.display='none';
  tvpPanel('spuren');                                  // neu öffnen = frische Häkchen
}
async function tvpRate(w){
  tvpRateWert=w;
  try{await tvpBefehl('rate',{wert:w});}catch(e){}
  const p=document.getElementById('tvp-panel'); if(p)p.style.display='none';
  tvpPanel('tempo');
}
function tvpVollbild(){
  const el=document.getElementById('tv-player'); if(!el)return;
  if(document.fullscreenElement){try{document.exitFullscreen();}catch(e){}}
  else if(el.requestFullscreen)el.requestFullscreen().catch(()=>{});
}
function tvpIdleTick(spielt){
  // Netflix-Verhalten (JB-Bilder): Inaktivität blendet die Leiste aus; wer in
  // PAUSE verharrt, bekommt den ruhigen „Du siehst …"-Schirm (Bild 3).
  const el=document.getElementById('tv-player'); if(!el)return;
  const still=Date.now()-tvpAktiv>3500;
  el.classList.toggle('idle',still);
  const idle=document.getElementById('tvp-idle');
  if(!idle)return;
  const zeigen=still&&!spielt;
  // JB 07.08.: „kein neues bild — das pause gehaltene Bild nehmen und den
  // Text darüberlegen." Im Browser-Modus steht das <video> selbst als
  // Standbild, der Text liegt einfach darüber. NUR in der HÜLLE mit VLC
  // (natives Panel, Text kann nicht darüber) ersetzt ein frischer
  // Schnappschuss den Moment.
  const bg=document.getElementById('tvp-standbild');
  const huelleVlc=tvpModus!=='browser'&&!!window.pywebview;
  if(zeigen&&idle.style.display==='none'&&huelleVlc){
    vlcBefehl('standbild').then(()=>{
      if(bg){
        bg.src='/api/vlc_standbild?t='+Date.now();
        // gleiche Fläche wie das Video-Panel (bis zur Leiste) — sonst
        // springt die Bildgröße beim Pause-Schirm (JB 07.08.).
        const u=document.querySelector('#tv-player .tvp-unten');
        if(u)bg.style.bottom=(innerHeight-u.getBoundingClientRect().top)+'px';
      }
    }).catch(()=>{});
  }
  idle.style.display=zeigen?'flex':'none';
  if(bg)bg.style.display=(zeigen&&huelleVlc)?'block':'none';
}
function tvpZu(){
  tvpOffen=false; tvpModus='vlc'; tvpTc=false; tvpTcOffset=0;   // nie hängen lassen
  if(tvpTimer){clearInterval(tvpTimer); tvpTimer=null;}
  const api=window.pywebview&&window.pywebview.api;   // Hüllen-Bild freigeben
  if(api&&api.video_rect){try{api.video_rect(0,0,0,0,false);}catch(e){}}
  const el=document.getElementById('tv-player');
  if(el){
    if(document.fullscreenElement===el){try{document.exitFullscreen();}catch(e){}}
    el.style.display='none'; el.innerHTML='';
  }
}
async function tvpTick(){
  if(!tvpOffen)return;
  let s=null;
  try{s=await tvpBefehl('status');}catch(e){return;}
  if(!s)return;
  if(s.zustand==='spielt')tvpLief=true;
  tvpTicks++;
  // JB-Fund: vlcKeyLetzter setzte nur der Geräte-VLC-Takt — ohne ihn war
  // filmStopp/Esc/← ein stiller No-op. Der Film-Takt pflegt ihn jetzt selbst.
  vlcKeyLetzter=s.key||vlcKeyLetzter; vlcSpielt=(s.zustand==='spielt');
  tvpIdleTick(s.zustand==='spielt');
  // Ende-Erkennung mit ANLAUF-GNADE (live gefunden: der erste Tick kam vor
  // VLCs „spielt" und schloss die Fernbedienung sofort wieder): erst
  // schließen, wenn der Film nachweislich lief oder der Start nie kam.
  if((!/^(film|live):/.test(s.key||'')||s.zustand==='aus')&&(tvpLief||tvpTicks>8)){
    tvpZu();
    if(tvInfoOffen)tvInfoMalen();
    return;
  }
  tvpPos=s.pos||tvpPos; tvpDauer=s.dauer||tvpDauer;
  // Lade-Spinner (JB-Go): sichtbar, bis der Film WIRKLICH spielt — deckt den
  // langsamen Index-/Seek-Anlauf mancher Container über die Leitung ehrlich ab.
  const lade=document.getElementById('tvp-lade');
  if(lade)lade.style.display=(s.zustand==='spielt'||(tvpLief&&s.zustand==='pause'))?'none':'flex';
  const pp=document.getElementById('tvp-pp'); if(pp)pp.innerHTML=ico(s.zustand==='spielt'?'pause':'play');
  // In der PROGRAMM-HÜLLE ist die Bedienung IM Player (JB): das eingebettete
  // VLC-Bild bekommt die Fläche BIS zur Leisten-Oberkante gemeldet.
  // Nachtprüfung 06.08.: das NATIVE Panel verdeckte Settings-Panel,
  // Lade-Spinner und Pause-Schirm — darum: Fläche endet auch an der
  // Panel-Oberkante, und solange Spinner/Pause-Schirm sichtbar sind,
  // wird das Panel ganz versteckt (der Browser zeigt Backdrop + Overlay).
  const api=window.pywebview&&window.pywebview.api;
  if(api&&api.video_rect&&tvpModus==='browser'){
    try{api.video_rect(0,0,0,0,false);}catch(e){}      // <video> rendert selbst
  }else if(api&&api.video_rect){
    const u=document.querySelector('#tv-player .tvp-unten');
    const dpr=window.devicePixelRatio||1;
    // JB 07.08.: „das bild wird plötzlich größer wenn die Bedienung
    // ausblendet" — die Leisten-Fläche bleibt jetzt IMMER reserviert
    // (auch im Idle nur Inhalte ausgeblendet), das Bild ist konstant.
    let bis=u?u.getBoundingClientRect().top:window.innerHeight;
    const pan=document.getElementById('tvp-panel');
    if(pan&&pan.style.display!=='none')
      bis=Math.min(bis,pan.getBoundingClientRect().top);
    const idle2=document.getElementById('tvp-idle');
    const spinner=lade&&lade.style.display!=='none';
    const pauseSchirm=idle2&&idle2.style.display!=='none';
    if(spinner||pauseSchirm){try{api.video_rect(0,0,0,0,false);}catch(e){}}
    else{try{api.video_rect(0,0,Math.round(innerWidth*dpr),Math.round(bis*dpr),true);}catch(e){}}
  }
  const f=document.getElementById('tvp-fuell');
  if(f&&tvpDauer)f.style.width=Math.min(100,tvpPos/tvpDauer*100)+'%';
  const z=document.getElementById('tvp-zeit'); if(z)z.textContent=zeit(tvpPos)+' / '+zeit(tvpDauer);
}
function tvpLadeZeigen(text){
  const l=document.getElementById('tvp-lade'), t=document.getElementById('tvp-lade-text');
  if(t)t.textContent=text; if(l)l.style.display='flex';
}
function tvpRel(s){
  tvpPos=Math.max(0,Math.min(tvpDauer||1e9,tvpPos+s));
  if(tvpModus!=='browser')tvpLadeZeigen('Springt zu '+zeit(tvpPos)+' …');
  tvpBefehl('seek',{wert:tvpPos});
  setTimeout(tvpTick,300);
}
function tvpSeek(ev){
  const wrap=ev.currentTarget.querySelector('.tvp-balken');
  const r=wrap.getBoundingClientRect();
  if(!tvpDauer||!r.width)return;
  tvpPos=Math.max(0,Math.min(tvpDauer,(ev.clientX-r.left)/r.width*tvpDauer));
  if(tvpModus!=='browser')tvpLadeZeigen('Springt zu '+zeit(tvpPos)+' …');
  tvpBefehl('seek',{wert:tvpPos});
  setTimeout(tvpTick,300);
}
/* Film beenden (JB 05.08.: „auch beendet werden können mit escape") — meldet
   den Spot an Jellyfin UND lokal, damit „Weiterschauen ab …" SOFORT stimmt,
   ohne auf den nächsten Katalog-Abzug zu warten. */
function filmLaeuft(){return vlcSpielt&&/^(film|live):/.test(vlcKeyLetzter||'');}
async function filmStopp(){
  if((vlcKeyLetzter||'').startsWith('live:')){         // 📡 Live: nur stoppen
    vlcBefehl('stop');
    if(typeof tvpZu==='function')tvpZu();
    const tvL=document.getElementById('tv');
    if(tvL&&tvL.style.display!=='none'&&!document.fullscreenElement){
      try{tvL.requestFullscreen&&tvL.requestFullscreen().catch(()=>{});}catch(e){}
    }
    toast('📡 Live beendet.');
    return;
  }
  const id=(vlcKeyLetzter||'').slice(5); if(!id)return;
  const pos=Math.round((tvpOffen?tvpPos:vlcPosGeschaetzt())||0);
  tvpBefehl('stop'); vlcKeyLetzter=''; vlcSpielt=false;
  try{fetch('/api/filme/fortschritt',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id, position_s:pos})}).catch(()=>{});}catch(e){}
  const merk=e=>{if(e&&e.id===id)e.position_s=pos;};
  if(tvFilmReihen){Object.values(tvFilmReihen).forEach(v=>{
    if(Array.isArray(v))v.forEach(merk);
    else if(v&&typeof v==='object')Object.values(v).forEach(a=>Array.isArray(a)&&a.forEach(merk));});}
  if(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.id===id){tvInfoDaten.d.position_s=pos; tvInfoMalen();}
  if(typeof tvpZu==='function')tvpZu();               // Fernbedienung mit abräumen
  // Zurück ins TV-Vollbild, wenn der Fernsehmodus offen ist (die Esc-Taste
  // ist die nötige Nutzer-Geste).
  const tv=document.getElementById('tv');
  if(tv&&tv.style.display!=='none'&&!document.fullscreenElement){
    try{tv.requestFullscreen&&tv.requestFullscreen().catch(()=>{});}catch(e){}
  }
  toast('🎬 Film beendet — gemerkt bei '+zeit(pos)+'.');
  // ← bringt IMMER zur Detailansicht zurück (JB) — auch wenn sie zu war.
  if(!tvInfoOffen&&id)tvInfo(id);
}
document.addEventListener('keydown',ev=>{
  // Esc beendet den laufenden Film — überall, außer ein Menü/Panel liegt oben
  // (die schließen sich selbst zuerst; das TV regelt seine Ebenen in tvKey).
  if(ev.key!=='Escape'||!filmLaeuft())return;
  const tv=document.getElementById('tv');
  if(tv&&tv.style.display!=='none')return;             // tvKey ist zuständig
  if(document.querySelector('.itemmenu,.panelmenu'))return;
  ev.preventDefault(); filmStopp();
});
async function filmeSync(){
  try{await fetch('/api/filme/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    toast('🎬 Katalog-Abzug gestartet — dauert bei großen Bibliotheken etwas.');
    setTimeout(filmeLaden, 8000);
  }catch(e){toast('🎬 Abzug nicht erreichbar.');}
}
function aboVor(ts){
  if(!ts)return '';
  const m=Math.max(0,Math.round((Date.now()/1000-ts)/60));
  return m<60?('vor '+m+' min'):(m<2880?('vor '+Math.round(m/60)+' h'):('vor '+Math.round(m/1440)+' Tagen'));
}
const ABO_Q={beste:'Beste','1080p':'1080p','720p':'720p','1440p':'1440p','2160p':'4K',audio:'MP3'};
function aboMalen(){
  const el=document.getElementById('abo-liste'); if(!el)return;
  const fly=document.getElementById('abo-flyout');   // Abo weg (gelöscht)? Waisen-Flyout schließen
  if(fly&&!aboState.some(a=>a.id===fly.dataset.abo)){fly.remove(); document.removeEventListener('pointerdown',aboFlyoutAussen,true);}
  if(!aboState.length){el.innerHTML='<div class="leer" style="text-align:left;padding:6px 0">Noch keine Abos.</div>'; return;}
  el.innerHTML=aboState.map(a=>aboKarteHTML(a)).join('');
  aboState.forEach(a=>{const o=aboOffen[a.id]; if(o&&o.auf)aboFolgenMalen(a.id);});
}
function aboKarteHTML(a){
  const o=aboOffen[a.id]||{};
  const qsel=`<select class="abo-qsel" title="Download-Format dieses Abos (gilt ab der nächsten Prüfung; Bisheriges unter ⚙ erneuerbar)" onchange="aboQualitaet('${a.id}',this.value)">`+
    Object.keys(ABO_Q).map(q=>`<option value="${q}" ${q===a.qualitaet?'selected':''}>${ABO_Q[q]}</option>`).join('')+'</select>';
  return `<div class="abo-card" data-abo="${a.id}">
    <div class="abo-kopf">
      <span class="abo-name" title="${esc(a.url)}">📡 ${esc(a.name||a.url)}</span>
      ${qsel}
      <span class="abo-meta">${a.neu?('+'+a.neu+' geholt · '):''}${a.geprueft?('geprüft '+aboVor(a.geprueft)):''}</span>
      <button class="ib" title="Abo-Playlist im Player abspielen" onclick="aboAbspielen('${a.id}')">▶</button>
      <button class="ib ${o.auf?'an':''}" title="Backkatalog: alle Folgen des Kanals als eigenes Fenster — Ausgegrautes ist noch nicht geladen" onclick="aboFolgenToggle('${a.id}',event)">📜</button>
      <button class="ib ${o.regeln?'an':''}" title="Regeln: Titel-Filter, Stichtag, Shorts/Streams, Auto-Löschen, Format-Erneuern" onclick="aboRegelnToggle('${a.id}')">⚙</button>
      <button class="ib" title="Abo entfernen — mit oder ohne die geladenen Videos" onclick="aboDelete('${a.id}',event)">🗑</button>
    </div>
    ${o.regeln?aboRegelnHTML(a):''}
  </div>`;
}
function aboRegelnHTML(a){
  return `<div class="abo-regeln">
    <label title="Nur Videos laden, deren Titel diesen Text enthält (leer = alle)">Titel enthält
      <input type="text" value="${esc(a.filter_titel||'')}" onchange="aboRegel('${a.id}','filter_titel',this.value)"></label>
    <label title="Nur Videos ab diesem Datum laden (leer = alle)">ab
      <input type="date" value="${esc(a.ab_datum||'')}" onchange="aboRegel('${a.id}','ab_datum',this.value)"></label>
    <label title="Kurzvideos (≤ 62 s) überspringen"><input type="checkbox" ${a.ohne_shorts?'checked':''}
      onchange="aboRegel('${a.id}','ohne_shorts',this.checked)"> keine Shorts</label>
    <label title="Livestreams und Premieren überspringen"><input type="checkbox" ${a.ohne_streams?'checked':''}
      onchange="aboRegel('${a.id}','ohne_streams',this.checked)"> keine Streams</label>
    <label title="Folgen der Abo-Playlist nach X Tagen automatisch in den Papierkorb (0 = aus)">löschen nach
      <input type="number" min="0" max="3650" style="width:58px" value="${a.loeschen_nach_tagen||0}"
        onchange="aboRegel('${a.id}','loeschen_nach_tagen',parseInt(this.value,10)||0)"> Tagen</label>
    <span class="spacer"></span>
    <button class="btn mini" onclick="aboErneuern('${a.id}',false)"
      title="Alles bereits Geladene zusätzlich im aktuellen Abo-Format holen — alte Dateien bleiben">🔁 Erneuern (behalten)</button>
    <button class="btn mini" onclick="aboErneuern('${a.id}',true)"
      title="…und die alte Datei im anderen Format NACH dem Erfolg in den Papierkorb legen">🔁 Erneuern (ersetzen)</button>
  </div>`;
}
async function aboRegel(id,feld,wert){const d={art:'aendern',id}; d[feld]=wert; await aboPost(d); aboLaden();}
async function aboQualitaet(id,q){await aboPost({art:'aendern',id,qualitaet:q}); aboLaden();}
function aboRegelnToggle(id){const o=aboOffen[id]=aboOffen[id]||{zeige:300,sel:new Set()}; o.regeln=!o.regeln; aboMalen();}
/* ---- Backkatalog-Flyout (Build 93, JB): grosses Fenster am 📜-Knopf, nie aus
   dem Viewport. Nur EINES gleichzeitig; Esc/Aussenklick schliesst. ---- */
function aboFolgenToggle(id,ev){
  const o=aboOffen[id]=aboOffen[id]||{zeige:300,sel:new Set()};
  if(o.auf){aboFlyoutZu(); return;}
  aboFlyoutZu();                                       // evtl. offenes anderes Abo zu
  o.auf=true;
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='abo-flyout'; fly.dataset.abo=id; fly.tabIndex=-1;
  const a=aboState.find(x=>x.id===id)||{};
  fly.innerHTML=`<div class="abo-fly-titel">📜 ${esc(a.name||'Backkatalog')}<span class="spacer"></span>
      <button class="ib" title="Schliessen (Esc)" onclick="aboFlyoutZu()">✕</button></div>
    <div class="abo-folgen" id="abo-folgen-${id}"></div>`;
  document.body.appendChild(fly); nachVorn(fly);
  const anker=ev&&ev.currentTarget?ev.currentTarget.getBoundingClientRect():{left:80,bottom:80,top:60};
  aboFlyoutPositionieren(fly,anker);
  fly.addEventListener('keydown',e=>aboFlyoutTasten(e,id));
  setTimeout(()=>document.addEventListener('pointerdown',aboFlyoutAussen,true),0);
  fly.focus();
  aboMalen();
  if(o.folgen)aboFolgenMalen(id); else aboFolgenLaden(id,false);
}
function aboFlyoutPositionieren(fly,anker){
  // JB (Build 94): rechtsbuendig UNTER dem eingebetteten Downloads-Fenster
  // (dlbox) andocken und bis zur Unterkante nutzen — richtig gross, aber
  // IMMER komplett lesbar (lesbar schlaegt andocken: bei Zwergfenstern
  // wandert es hoch, statt unlesbar zu quetschen).
  const vw=window.innerWidth, vh=window.innerHeight, R=12, MINH=260;
  const db=document.getElementById('dlbox');
  const dbr=db?db.getBoundingClientRect():null;
  const w=Math.min(820, Math.max(340, Math.round(vw*0.75)), vw-2*R);
  let x, y;
  if(dbr&&dbr.bottom<vh-R-MINH){
    x=vw-R-w;                                          // rechte Kante fluchtet mit der dlbox
    y=Math.round(dbr.bottom+6);
  }else{
    x=Math.round((anker&&anker.left)||R); y=Math.round(((anker&&anker.bottom)||R)+6);
  }
  let h=vh-R-y;                                        // bis zur Unterkante ausnutzen
  if(h<MINH){y=Math.max(R, vh-R-MINH); h=vh-R-y;}      // zu eng? hochziehen statt quetschen
  x=Math.max(R, Math.min(x, vw-R-w));
  fly.style.left=x+'px'; fly.style.top=y+'px'; fly.style.width=w+'px'; fly.style.height=h+'px';
  imBlick(fly,R);                                      // Sicherheitsnetz (Build 114)
}
function aboFlyoutZu(){
  const fly=document.getElementById('abo-flyout');
  if(fly){const id=fly.dataset.abo; if(aboOffen[id])aboOffen[id].auf=false; fly.remove();}
  document.removeEventListener('pointerdown',aboFlyoutAussen,true);
  aboMalen();
}
function aboFlyoutAussen(e){
  const fly=document.getElementById('abo-flyout'); if(!fly)return;
  if(fly.contains(e.target)||e.target.closest('.itemmenu'))return;   // Rechtsklick-Menü gehört dazu
  aboFlyoutZu();
}
function aboFlyoutNachklemmen(){                       // Fenster-Resize: Flyout bleibt komplett lesbar
  const fly=document.getElementById('abo-flyout'); if(!fly)return;
  const vw=window.innerWidth, vh=window.innerHeight, R=12;
  const w=Math.min(parseInt(fly.style.width,10)||600, vw-2*R), h=Math.min(parseInt(fly.style.height,10)||400, vh-2*R);
  fly.style.width=w+'px'; fly.style.height=h+'px';
  fly.style.left=Math.max(R,Math.min(parseInt(fly.style.left,10)||R, vw-R-w))+'px';
  fly.style.top =Math.max(R,Math.min(parseInt(fly.style.top,10)||R, vh-R-h))+'px';
}
window.addEventListener('resize',aboFlyoutNachklemmen);
function aboFlyoutTasten(e,id){
  const o=aboOffen[id]; if(!o)return;
  const imFeld=/^(INPUT|SELECT|TEXTAREA)$/.test((e.target.tagName||''));
  if(e.key==='Escape'){
    if(o.sel.size&&!imFeld){o.sel.clear(); aboFolgenMalen(id);}
    else aboFlyoutZu();
    e.stopPropagation();
  }else if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='a'&&!imFeld){
    e.preventDefault();
    aboGefiltert(id).forEach(x=>o.sel.add(x.id));      // Strg+A = die ganze gefilterte Sicht
    aboFolgenMalen(id);
  }
}
function aboGefiltert(id){
  const o=aboOffen[id]||{}; const alle=o.folgen||[];
  const f=(o.filter||'').toLowerCase();
  let liste=f?alle.filter(x=>(x.titel||'').toLowerCase().includes(f)):alle;
  if(o.nur==='fehlt')liste=liste.filter(x=>!x.geladen);
  else if(o.nur==='da')liste=liste.filter(x=>x.geladen);
  return liste;
}
async function aboFolgenLaden(id,frisch){
  const o=aboOffen[id]; if(!o)return;
  o.laedt=true; aboFolgenMalen(id);
  const d=await aboPost({art:'folgen',id,aktualisieren:!!frisch});
  o.laedt=false;
  if(d.fehler){o.fehler=d.fehler;}
  else{o.fehler=''; o.folgen=d.folgen||[]; o.qual=d.qualitaet; o.ts=d.ts;}
  aboFolgenMalen(id);
}
function aboFolgenMalen(id){
  const box=document.getElementById('abo-folgen-'+id); if(!box)return;
  const o=aboOffen[id];
  if(o.laedt){box.innerHTML='<div class="leer">Hole Folgen-Liste vom Kanal… (bei großen Kanälen dauert das etwas)</div>'; return;}
  if(o.fehler){box.innerHTML='<div class="leer">'+esc(o.fehler)+'</div>'; return;}
  const alle=o.folgen||[];
  const liste=aboGefiltert(id);
  const fehlen=alle.filter(x=>!x.geladen).length;
  const fq=q=>ABO_Q[q]||q;
  const zeilen=liste.slice(0,o.zeige).map(x=>{
    const badge=x.geladen?(x.passend
      ?`<span class="abo-b ok" title="im Abo-Format geladen">✓ ${x.formate.map(fq).join('·')}</span>`
      :`<span class="abo-b anders" title="in ANDEREM Format geladen — ⚙ → Erneuern holt das Abo-Format">≠ ${x.formate.map(fq).join('·')}</span>`):'';
    return `<div class="abo-f ${x.geladen?'':'fehlt'} ${o.sel.has(x.id)?'sel':''}" data-vid="${x.id}"
      onclick="aboFolgeKlick(event,'${id}','${x.id}')" ondblclick="aboFolgenHolen('${id}',['${x.id}'])"
      oncontextmenu="return aboFolgeKontext(event,'${id}','${x.id}')"
      title="Folge ${x.nr} von ${alle.length}${x.geladen?' — geladen, Doppelklick lädt ggf. im Abo-Format nach':' — noch nicht geladen, Doppelklick lädt im Abo-Format'}">
      <span class="abo-nr" title="Folge ${x.nr} (älteste = 1, neueste = ${alle.length})">#${x.nr}</span>
      <span class="abo-ft">${esc(x.titel)}</span>${x.dauer?'<span class="abo-fd">'+zeit(x.dauer)+'</span>':''}${badge}</div>`;
  }).join('');
  const fehltSicht=liste.filter(x=>!x.geladen).length;
  const staffel=[10,25,50,100].map(n=>
    `<button class="btn mini" onclick="aboFehlendeLaden('${id}',${n})" ${fehltSicht?'':'disabled'}
       title="Die ${o.richtung==='neu'?'neuesten':'ältesten'} ${n} noch fehlenden Folgen der aktuellen Sicht laden">${n}</button>`).join('');
  box.innerHTML=`<div class="abo-fkopf">
      <input type="text" placeholder="Folgen durchsuchen…" value="${esc(o.filter||'')}"
        oninput="aboOffen['${id}'].filter=this.value;aboOffen['${id}'].zeige=300;aboFolgenMalen('${id}')">
      <select onchange="aboOffen['${id}'].nur=this.value;aboFolgenMalen('${id}')" title="Anzeige filtern">
        <option value="">alle (${alle.length})</option>
        <option value="fehlt" ${o.nur==='fehlt'?'selected':''}>fehlende (${fehlen})</option>
        <option value="da" ${o.nur==='da'?'selected':''}>geladene (${alle.length-fehlen})</option></select>
      <button class="btn mini" onclick="aboAuswahlLaden('${id}')" ${o.sel.size?'':'disabled'}
        title="Markierte Folgen im Abo-Format in die Warteschlange (Klick = diese, Strg+Klick = dazu/weg, Shift = Bereich, Strg+A = alle, Rahmen aufziehen = viele)">⬇ Auswahl (${o.sel.size})</button>
      <button class="ib" title="Folgen-Liste frisch vom Kanal holen${o.ts?' (Stand '+aboVor(o.ts)+')':''}" onclick="aboFolgenLaden('${id}',true)">🔄</button>
    </div>
    <div class="abo-staffel">⬇ Fehlende laden: ${staffel}
      <button class="btn mini" onclick="aboAlleFehlenden('${id}')" ${fehltSicht?'':'disabled'}
        title="ALLE noch fehlenden Folgen der aktuellen Sicht laden">Alle (${fehltSicht})</button>
      <button class="btn mini" onclick="aboOffen['${id}'].richtung=aboOffen['${id}'].richtung==='neu'?'alt':'neu';aboFolgenMalen('${id}')"
        title="Reihenfolge der Mengen-Knöpfe umschalten">${o.richtung==='neu'?'⏭ neueste zuerst':'⏮ älteste zuerst'}</button>
    </div>
    <div class="abo-fliste" onpointerdown="aboBandStart(event,'${id}')">${zeilen||'<div class="leer">nichts gefunden</div>'}</div>
    ${liste.length>o.zeige?`<button class="btn mini" style="margin-top:4px" onclick="aboOffen['${id}'].zeige+=600;aboFolgenMalen('${id}')">… mehr anzeigen (${liste.length-o.zeige} weitere)</button>`:''}
    ${o.sel.size?`<div class="abo-selbar">🎯 <b>${o.sel.size}</b> markiert
      <span class="spacer"></span>
      <button class="btn mini" onclick="aboAuswahlLaden('${id}')" title="Die markierten Folgen im Abo-Format in die Warteschlange">⬇ ${o.sel.size} laden</button>
      <button class="btn mini" onclick="aboOffen['${id}'].sel.clear();aboFolgenMalen('${id}')" title="Auswahl aufheben (Esc)">✕</button></div>`:''}`;
}
function aboFolgeKlick(ev,id,vid){
  // Windows-Semantik (Build 93, JB-Entscheid): Klick = NUR diese, Strg+Klick =
  // dazu/weg, Shift = Bereich (ersetzt; mit Strg additiv). Anker bleibt beim
  // Shift-Klick stehen — wie im Explorer.
  const o=aboOffen[id]; if(!o)return;
  if(o._bandLief)return;                               // der Klick war das Ende eines Band-Zugs
  const box=ev.currentTarget.parentElement;
  const sichtbar=[...box.querySelectorAll('.abo-f')].map(n=>n.dataset.vid);
  if(ev.shiftKey&&aboLetzterKlick[id]){
    const i1=sichtbar.indexOf(aboLetzterKlick[id]), i2=sichtbar.indexOf(vid);
    if(!ev.ctrlKey&&!ev.metaKey)o.sel.clear();
    if(i1>=0&&i2>=0)sichtbar.slice(Math.min(i1,i2),Math.max(i1,i2)+1).forEach(v=>o.sel.add(v));
  }else if(ev.ctrlKey||ev.metaKey){
    if(o.sel.has(vid))o.sel.delete(vid); else o.sel.add(vid);
    aboLetzterKlick[id]=vid;
  }else{
    o.sel.clear(); o.sel.add(vid);
    aboLetzterKlick[id]=vid;
  }
  aboFolgenMalen(id);
}
/* Rahmen aufziehen (Rubberband, Build 94): startet AUCH auf einer Zeile —
   JB-Fund: die Zeilen sind vollbreit, freie Flaeche gibt es kaum. Erst ab
   5 px Bewegung wird es ein Band (darunter bleibt es ein normaler Klick);
   nach einem Band wird der nachlaufende click der Startzeile geschluckt.
   Mit Strg additiv zur bestehenden Auswahl. */
function aboBandStart(ev,id){
  if(ev.button!==0||ev.target.closest('button')||ev.target.closest('input')||ev.target.closest('select'))return;
  const o=aboOffen[id]; if(!o)return;
  const liste=ev.currentTarget.closest('.abo-fliste')||ev.currentTarget;
  const basis=new Set(ev.ctrlKey||ev.metaKey?[...o.sel]:[]);
  const x0=ev.clientX, y0=ev.clientY; let band=null;
  function mv(e){
    if(!band){
      if(Math.abs(e.clientX-x0)<5&&Math.abs(e.clientY-y0)<5)return;   // erst ab 5 px ein Band
      band=document.createElement('div'); band.className='abo-band'; document.body.appendChild(band);
    }
    const l=Math.min(x0,e.clientX), t=Math.min(y0,e.clientY),
          r=Math.max(x0,e.clientX), b=Math.max(y0,e.clientY);
    band.style.left=l+'px'; band.style.top=t+'px';
    band.style.width=(r-l)+'px'; band.style.height=(b-t)+'px';
    const lr=liste.getBoundingClientRect();                           // Rand-Nachschieben bei langen Listen
    if(e.clientY>lr.bottom-18)liste.scrollTop+=14;
    else if(e.clientY<lr.top+18)liste.scrollTop-=14;
    o.sel=new Set(basis);
    [...liste.querySelectorAll('.abo-f')].forEach(n=>{
      const q=n.getBoundingClientRect();
      if(q.left<r&&q.right>l&&q.top<b&&q.bottom>t)o.sel.add(n.dataset.vid);
      n.classList.toggle('sel',o.sel.has(n.dataset.vid));
    });
  }
  function up(){
    document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
    if(band){
      band.remove(); o._bandLief=true;                                // nachlaufenden Zeilen-click schlucken
      setTimeout(()=>{o._bandLief=false;},0);
      aboFolgenMalen(id);                                             // Zaehler im Kopf nachziehen
    }
  }
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
}
function aboFehlendeLaden(id,n){
  // Mengen-Staffel (Build 93): die naechsten n fehlenden der AKTUELLEN Sicht —
  // Liste ist neueste-zuerst; Standard laedt chronologisch (aelteste zuerst).
  const o=aboOffen[id]; if(!o)return;
  let fehlt=aboGefiltert(id).filter(x=>!x.geladen);
  if(o.richtung!=='neu')fehlt=fehlt.slice().reverse();
  const vids=fehlt.slice(0,n).map(x=>x.id);
  if(!vids.length){alert('Nichts offen — alles in dieser Sicht ist geladen.');return;}
  aboFolgenHolen(id,vids);
}
function aboFolgeKontext(ev,id,vid){
  ev.preventDefault();
  const o=aboOffen[id]||{sel:new Set()};
  const eintraege=[['⬇ Im Abo-Format laden',()=>aboFolgenHolen(id,[vid])]];
  if(o.sel.size)eintraege.push(['⬇ Auswahl laden ('+o.sel.size+')',()=>aboAuswahlLaden(id)]);
  eintraege.push(['▶ Auf YouTube öffnen',()=>window.open('https://www.youtube.com/watch?v='+vid,'_blank','noreferrer')]);
  kontextMenuBauen(ev,eintraege);
  return false;
}
async function aboFolgenHolen(id,vids){
  const d=await aboPost({art:'folgen_laden',id,vids});
  if(d.fehler){alert(d.fehler);return;}
  const o=aboOffen[id]; if(o){vids.forEach(v=>o.sel.delete(v));}
  laden();
  setTimeout(()=>aboFolgenLaden(id,false),1500);   // Status-Punkte nachziehen
}
function aboAuswahlLaden(id){
  const o=aboOffen[id]; if(!o||!o.sel.size)return;
  const vids=[...o.sel]; o.sel.clear();
  aboFolgenHolen(id,vids);
}
function aboAlleFehlenden(id){
  const o=aboOffen[id]; if(!o)return;
  const fehlt=aboGefiltert(id).filter(x=>!x.geladen);                // Sicht-bezogen wie die Staffel (Build 93)
  if(!fehlt.length){alert('Nichts offen — alles in dieser Sicht ist geladen.');return;}
  const abo=aboState.find(a=>a.id===id)||{};
  const gr=groesseSchaetzen(fehlt.reduce((s,x)=>s+(x.dauer||0),0),abo.qualitaet||'beste');
  if(!confirm(fehlt.length+' fehlende Folge(n) im Abo-Format in die Warteschlange legen?'+gr))return;
  aboFolgenHolen(id,fehlt.map(x=>x.id));
}
async function aboErneuern(id,ersetzen){
  const was=ersetzen?'Die alte Datei im anderen Format wandert NACH dem Erfolg in den Papierkorb.'
                    :'Alte Dateien bleiben zusätzlich erhalten.';
  if(!confirm('Alles bereits Geladene dieses Abos im aktuellen Abo-Format neu laden? '+was))return;
  const d=await aboPost({art:'erneuern',id,ersetzen});
  alert(d.fehler||(d.neu?d.neu+' Folge(n) eingereiht.':'Nichts zu erneuern — alles passt schon.'));
  laden();
}
async function aboAbspielen(id){
  const a=aboState.find(x=>x.id===id);
  if(!a||!a.playlist_id){alert('Noch keine fertigen Abo-Downloads — die Playlist entsteht mit dem ersten.');return;}
  await plLaden();
  const sel=document.getElementById('plsel'); if(sel)sel.value=a.playlist_id;
  ensurePlayer(); plPlaySel();
}
function aboAbonnierenHin(){
  // Build 127: Es gibt nur noch EIN Eingabefeld. Der Knopf im Abo-Reiter
  // führt dorthin, statt ein zweites daneben zu stellen.
  const inp=document.getElementById('cmd-url');
  if(!inp){toast('Das Eingabefeld oben ist gerade nicht sichtbar.');return;}
  inp.focus(); inp.select();
  toast('Kanal-Link hier einfügen und Enter — dann „Abonnieren" wählen.');
}
function aboDelete(id,ev){
  // Build 95 (JB): beim Entfernen wahlweise die ueber DIESES Abo geladenen
  // Videos mit in den Windows-Papierkorb (nur Abo-Playlist-Inhalte,
  // wiederherstellbar) — manuell Geladenes bleibt immer unberuehrt.
  kontextMenuBauen(ev,[
    ['🗑 Nur das Abo entfernen (Videos bleiben)', async()=>{
      await aboPost({art:'delete',id}); aboLaden();
    }],
    ['🗑 Abo + geladene Videos in den Papierkorb', async()=>{
      if(!confirm('Auch alle über dieses Abo geladenen Videos in den Windows-Papierkorb legen? Manuell Geladenes bleibt.'))return;
      const d=await aboPost({art:'delete',id,mit_videos:true});
      toast('🗑 '+(d.geloescht||0)+' Datei(en) in den Papierkorb');
      aboLaden(); libLaden();
    }],
  ]);
}
async function aboPruefen(btn){
  const t=btn&&btn.textContent; if(btn){btn.disabled=true; btn.textContent='prüfe…';}
  try{const r=await fetch('/api/abo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({art:'pruefen'})});
    const d=await r.json(); alert(d.neu?(d.neu+' neue(s) Video(s) in die Warteschlange gelegt.'):'Keine neuen Videos.');
  }catch(e){alert('Prüfen fehlgeschlagen.');}
  if(btn){btn.disabled=false; btn.textContent=t;} aboLaden(); laden();
}

/* ---- Smart-/Auto-Playlists: Regel-basiert, füllen sich selbst aus der Bibliothek ---- */
let smartListen=[]; try{smartListen=JSON.parse(localStorage.getItem('ytdl_smart'))||[];}catch(e){}
if(!Array.isArray(smartListen))smartListen=[];
function smartSpeichern(){try{localStorage.setItem('ytdl_smart',JSON.stringify(smartListen));}catch(e){}}
function smartBerechnen(rules){
  let arr=libdaten.filter(x=>x.vorhanden&&!x.blacklist);
  if(rules.kat==='MP3')arr=arr.filter(x=>x.kategorie==='MP3'||(!x.vcodec&&x.acodec));
  else if(rules.kat==='Video')arr=arr.filter(x=>!(x.kategorie==='MP3'||(!x.vcodec&&x.acodec)));
  if(rules.gespielt==='nie')arr=arr.filter(x=>!((x.plays||0)>0));
  else if(rules.gespielt==='ja')arr=arr.filter(x=>(x.plays||0)>0);
  if(rules.tage>0){const g=Date.now()/1000-rules.tage*86400; arr=arr.filter(x=>(x.ts||0)>=g);}
  if(rules.sort==='plays')arr.sort((a,b)=>(b.plays||0)-(a.plays||0));
  else if(rules.sort==='last_play')arr.sort((a,b)=>(b.last_play||0)-(a.last_play||0));
  else arr.sort((a,b)=>(b.ts||0)-(a.ts||0));
  if(rules.limit>0)arr=arr.slice(0,rules.limit);
  return arr.map(x=>x.id);
}
function smartPlay(id){
  const s=smartListen.find(x=>x.id===id); if(!s)return;
  const ids=smartBerechnen(s.rules);
  if(!ids.length){alert('„'+s.name+'" ist gerade leer (keine passenden Titel).');return;}
  if(playShuffle)mische(ids); playerPlay(ids,0,'✨ '+s.name);
}
function smartLoeschen(id){smartListen=smartListen.filter(s=>s.id!==id); smartSpeichern(); smartPopover(null,true);}
function smartNeu(){
  const name=(document.getElementById('sm-name').value||'').trim()||'Smart-Playlist';
  const rules={kat:document.getElementById('sm-kat').value, gespielt:document.getElementById('sm-gespielt').value,
    tage:parseInt(document.getElementById('sm-tage').value,10)||0, sort:document.getElementById('sm-sort').value,
    limit:parseInt(document.getElementById('sm-limit').value,10)||0};
  smartListen.push({id:Math.random().toString(36).slice(2,8), name, rules});
  smartSpeichern(); smartPopover(null,true);
}
function smartPopover(ev,neuzeichnen){
  const alt=document.getElementById('smartpop');
  if(alt&&!neuzeichnen){alt.remove(); return;}                 // zweiter Klick = schließen
  const pos=alt?{left:alt.style.left,top:alt.style.top}:null; if(alt)alt.remove();
  const m=document.createElement('div'); m.className='panelmenu'; m.id='smartpop'; m.style.minWidth='288px';
  const gespieltO=[['all','egal'],['nie','nie gespielt'],['ja','schon gespielt']];
  const katO=[['all','alle'],['MP3','nur MP3'],['Video','nur Video']];
  const sortO=[['neu','neueste zuerst'],['plays','meistgespielt'],['last_play','zuletzt gespielt']];
  const sel=(id,opts)=>`<select id="${id}" class="sm-sel">`+opts.map(o=>`<option value="${o[0]}">${o[1]}</option>`).join('')+`</select>`;
  const liste=smartListen.length?smartListen.map(s=>
    `<div class="sm-row"><button class="sm-play" onclick="smartPlay('${s.id}')" title="Abspielen">▶ ${esc(s.name)}</button>`+
    `<span class="sm-cnt">${smartBerechnen(s.rules).length}</span>`+
    `<button class="ib" onclick="smartLoeschen('${s.id}')" title="Löschen">🗑</button></div>`).join(''):
    '<div class="sm-leer">Noch keine Smart-Playlist.</div>';
  m.innerHTML=`<div class="sm-titel">✨ Smart-Playlists</div>${liste}<div class="sm-sep"></div>`+
    `<div class="sm-form"><input id="sm-name" class="sm-name" placeholder="Name…">`+
    `<div class="sm-grid"><span>Art</span>${sel('sm-kat',katO)}<span>Gespielt</span>${sel('sm-gespielt',gespieltO)}`+
    `<span>Sortierung</span>${sel('sm-sort',sortO)}`+
    `<span>Nur letzte Tage</span><input id="sm-tage" class="sm-num" type="number" min="0" value="0" title="0 = egal">`+
    `<span>Höchstens</span><input id="sm-limit" class="sm-num" type="number" min="0" value="50" title="0 = alle"></div>`+
    `<button class="btn mini" onclick="smartNeu()">＋ Speichern</button></div>`;
  document.body.appendChild(m);
  if(pos){m.style.left=pos.left; m.style.top=pos.top;}
  else{const r=ev.currentTarget.getBoundingClientRect();
    popoverBei(m,r);}
  if(!smartPopover._zu){smartPopover._zu=true;
    setTimeout(()=>document.addEventListener('pointerdown',function zu(e2){
      const p=document.getElementById('smartpop');
      if(p&&!p.contains(e2.target)&&!(e2.target.closest&&e2.target.closest('[onclick*="smartPopover"]'))){
        p.remove(); document.removeEventListener('pointerdown',zu); smartPopover._zu=false;}},true),0);}
}

/* ---- Dublettenfinder: gleiches Video mehrfach (versch. Qualitäten) / gleicher Titel ---- */
function dubNorm(t){return (t||'').toLowerCase().replace(/\\[[^\\]]*\\]|\\([^)]*\\)/g,'')
  .replace(/official|video|audio|lyrics?|hd|4k|mv/g,'').replace(/[^a-z0-9]+/g,' ').trim();}
function dublettenGruppen(){
  const byVid={}, byTitel={};
  libdaten.forEach(x=>{ (byVid[x.videoid]=byVid[x.videoid]||[]).push(x);
    const n=dubNorm(x.titel); if(n)(byTitel[n]=byTitel[n]||[]).push(x); });
  const gruppen=[], gesehen=new Set();
  Object.values(byVid).forEach(g=>{ if(g.length>1){gruppen.push({typ:'Video mehrfach',titel:g[0].titel,items:g}); g.forEach(i=>gesehen.add(i.id));} });
  Object.values(byTitel).forEach(g=>{
    const vids=new Set(g.map(i=>i.videoid));
    if(vids.size>1){ const items=g.filter(i=>!gesehen.has(i.id)); if(items.length>1)gruppen.push({typ:'gleicher Titel',titel:g[0].titel,items}); }
  });
  return gruppen;
}
function dubBody(){
  const gruppen=dublettenGruppen();
  if(!gruppen.length)return '<div class="sm-titel">⧉ Dubletten</div><div class="sm-leer">Keine Doppelten gefunden. 🎉</div>';
  return '<div class="sm-titel">⧉ Dubletten — '+gruppen.length+' Gruppe(n)</div>'+gruppen.map(g=>
    `<div class="dub-grp"><div class="dub-kopf">${esc(g.titel.slice(0,46))} <span class="dub-typ">· ${g.typ}</span></div>`+
    g.items.map(x=>`<div class="dub-item"><span class="dub-q">${esc(x.qualitaet)} · ${mb(x.groesse)}${x.vorhanden?'':' · verschoben'}</span>`+
      `<button class="ib" title="In den Papierkorb" onclick="dubDelete('${x.id}')">🗑</button></div>`).join('')+`</div>`).join('');
}
async function ordnerImportieren(){
  plInfo('📥 Ordner wird durchsucht …', true);        // Fortschritt: bleibt
  try{
    const r=await fetch('/api/importieren',{method:'POST'}); const d=await r.json();
    if(info)info.textContent=d.neu?('📥 '+d.neu+' neue Datei(en) aufgenommen ✓'):'📥 Nichts Neues im Ordner gefunden';
    libLaden();
  }catch(e){ if(info)info.textContent='📥 Import fehlgeschlagen'; }
}
function dublettenPopover(ev){
  const alt=document.getElementById('dubpop'); if(alt){alt.remove(); return;}     // zweiter Klick = zu
  const m=document.createElement('div'); m.className='panelmenu'; m.id='dubpop';
  m.style.minWidth='340px'; m.style.maxHeight='70vh'; m.style.overflowY='auto';
  m.innerHTML=dubBody(); document.body.appendChild(m);
  const r=ev.currentTarget.getBoundingClientRect();
  popoverBei(m,r);
  setTimeout(()=>document.addEventListener('pointerdown',function zu(e2){const p=document.getElementById('dubpop');
    if(p&&!p.contains(e2.target)&&!(e2.target.closest&&e2.target.closest('[onclick*="dublettenPopover"]'))){
      p.remove(); document.removeEventListener('pointerdown',zu);}},true),0);
}
async function dubDelete(id){
  const x=libFind(id)||{titel:''};
  if(!confirm('„'+(x.titel||'').slice(0,40)+'" ('+x.qualitaet+') in den Papierkorb?'))return;
  await fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,art:'loeschen'})});
  await libLaden(); const m=document.getElementById('dubpop'); if(m)m.innerHTML=dubBody();   // in place neu füllen
}
async function configSpeichern(){
  await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      ziel_ordner:document.getElementById('cfg_ziel').value,
      unterordner:document.getElementById('cfg_ordner').value==='1',
      metadaten:document.getElementById('cfg_meta').value==='1',
      cookies_browser:document.getElementById('cfg_browser').value,
      parallel:parseInt(document.getElementById('cfg_parallel').value,10),
      geo_vpn:document.getElementById('cfg_geo').value==='1',
      geo_gratis_proxy:document.getElementById('cfg_geoproxyfrei').value==='1',
      geo_proxies:document.getElementById('cfg_geoproxies').value.split('\\n').map(s=>s.trim()).filter(Boolean),
      geo_wireguard_ordner:document.getElementById('cfg_geowg').value,
      standard_qualitaet:document.getElementById('cfg_qual').value,
      sponsorblock:document.getElementById('cfg_sponsor').value,
      untertitel:document.getElementById('cfg_subs').value==='1',
      untertitel_sprachen:(()=>{                       // JB Punkt 6: Sprachwahl
        const sp=[];
        if(document.getElementById('cfg_sub_de').checked)sp.push('de');
        if(document.getElementById('cfg_sub_en').checked)sp.push('en');
        if(document.getElementById('cfg_sub_orig').checked)sp.push('orig');
        document.getElementById('cfg_sub_extra').value.split(',')
          .map(s=>s.trim()).filter(Boolean).forEach(s=>sp.push(s));
        return sp;
      })(),
      auto_update:document.getElementById('cfg_autoupdate').value==='1'})});
  document.getElementById('cfg_meldung').textContent='Gespeichert ✓';
  setTimeout(()=>document.getElementById('cfg_meldung').textContent='',2500);
  laden();
}

/* ================= Geo/VPN-Assistent ================= */
let geoStatus=null, geoTestTimer=null;
const GEOVERGLEICH=[
  ['Gratis-Proxy (auto)','gratis','–','wechselnd','manchmal','nichts (schon an)'],
  ['Eigener Proxy','je nach Quelle','je nach Quelle','frei wählbar','ja, wenn dort','Adresse eintragen'],
  ['Windscribe Free','gratis','10 GB/Monat','viele','meist ja','Konto + App'],
  ['ProtonVPN Free','gratis','unbegrenzt','wenige','meist nein','Konto + WireGuard'],
  ['NordVPN','Abo (bezahlt)','unbegrenzt','alle','ja','App + Login'],
];
const GEOLANDER=[['GB','Großbritannien'],['US','USA'],['IE','Irland'],['CA','Kanada'],['NL','Niederlande'],
  ['DE','Deutschland'],['FR','Frankreich'],['JP','Japan'],['AU','Australien'],['CH','Schweiz'],
  ['AT','Österreich'],['PL','Polen'],['RO','Rumänien'],['SE','Schweden'],['ES','Spanien'],['IT','Italien']];

function geoWizOffen(){document.getElementById('geowiz').style.display='flex'; geoStatusLaden(true);}
function geoWizZu(){document.getElementById('geowiz').style.display='none'; clearInterval(geoTestTimer); geoTestTimer=null;}
async function geoStatusLaden(voll){
  try{
    const r=await fetch('/api/geo_status'); geoStatus=await r.json();
    const t=geoStatus.test||{};
    if(voll || !document.getElementById('geotest')) geoWizMalen();
    else { const g=document.getElementById('geotest'); if(g)g.innerHTML=geoTestHtml(t); }
    if(t.laeuft && !geoTestTimer) geoTestTimer=setInterval(()=>geoStatusLaden(false),1500);
    if(!t.laeuft && geoTestTimer){ clearInterval(geoTestTimer); geoTestTimer=null; geoWizMalen(); }
  }catch(e){}
}
function gstat(ok){return ok?'<span class="gstat ok">✓ erkannt</span>':'<span class="gstat no">nicht erkannt</span>';}
function ukfarbe(v){const c=v.indexOf('ja')===0?'ja':((v.indexOf('meist nein')===0||v==='nein')?'nein':'teils'); return `<span class="${c}">${v}</span>`;}
function gsec(titel,ok,inner){
  return `<details class="gsec"><summary><span>${titel}</span>${ok?'<span class="gstat ok">✓ eingerichtet</span>':'<span class="gstat no">offen</span>'}</summary><div class="ginner">${inner}</div></details>`;
}
function geoWgForm(){
  return `<div class="gwg"><textarea id="geowg-content" placeholder="[Interface]\\nPrivateKey = …\\n[Peer]\\nEndpoint = …"></textarea>
    <div class="gzeile"><label style="font-size:12px;color:#8a7d74">Land der Config</label>
    <select id="geowg-land">${GEOLANDER.map(([c,n])=>`<option value="${c}">${n} (${c})</option>`).join('')}</select>
    <button class="btn mini" onclick="geoWgImport()">importieren</button>
    <span id="geowg-msg" style="font-size:12px;color:#9ec49a"></span></div></div>`;
}
function geoTestHtml(t){
  t=t||{};
  if((!t.ergebnisse||!t.ergebnisse.length)&&!t.info)return '<div style="font-size:12px;color:#6a5c52;margin-top:6px">Noch nicht getestet.</div>';
  const rows=(t.ergebnisse||[]).map(e=>`<div class="gtestrow"><span>${esc(e.name)}</span><span>${e.ok===null?'… prüft':(e.ok?'<b style="color:#6fcf7f">✓ Zugang</b>':'<span style="color:#e08a6a">✗</span>')}</span></div>`).join('');
  const info=t.info?`<div style="margin-top:6px;font-size:12px;color:${/Zugang über/.test(t.info)?'#6fcf7f':'#e6c34a'}">${esc(t.info)}</div>`:'';
  return (t.titel?`<div style="font-size:11px;color:#8a7d74;margin-top:6px">Testvideo: ${esc(t.titel)}</div>`:'')+rows+info;
}
function geoWizMalen(){
  const s=geoStatus||{}, cfg=s.config||{}, t=s.test||{};
  const vgl=`<div class="libwrap"><table class="gcmp"><thead><tr><th>Weg</th><th>Kosten</th><th>Datenlimit</th><th>Länder</th><th>UK gratis?</th><th>Aufwand</th></tr></thead><tbody>`+
    GEOVERGLEICH.map(r=>`<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${ukfarbe(r[4])}</td><td>${r[5]}</td></tr>`).join('')+`</tbody></table></div>`;
  const erkannt=`<div style="font-size:12px;color:#8a7d74;margin:4px 0 10px">Auf diesem PC erkannt: `+
    `NordVPN ${s.nordvpn?'✓':'✗'} · Windscribe ${s.windscribe?'✓':'✗'} · WireGuard-Programm ${s.wireguard_exe?'✓':'✗'}`+
    (s.aktiver_adapter?` · <b style="color:#6fcf7f">aktiv: ${esc(s.aktiver_adapter)}</b>`:'')+
    ((s.wireguard_laender||[]).length?` · WireGuard-Länder: ${s.wireguard_laender.join(', ')}`:'')+`</div>`;
  const abschnitte=[
    gsec('🟢 Gratis-Proxy (0 Aufwand — läuft automatisch)', !!cfg.geo_gratis_proxy,
      `<p>Die App holt bei einem gesperrten Video kostenlose Proxys im Zielland und probiert sie durch — nichts einzurichten.</p>
       <p>Status: ${cfg.geo_gratis_proxy?'<b style="color:#6fcf7f">aktiv</b>':'<b style="color:#e08a6a">aus</b> — im Zahnrad „Gratis-Proxys" auf ja'}. Eigene Proxys eingetragen: ${s.proxy_anzahl||0}.</p>`),
    gsec('🔵 Windscribe Free — Tipp für UK (gratis, CLI)', !!s.windscribe,
      `<ol><li><a class="glink" href="https://windscribe.com/signup" target="_blank" rel="noreferrer">windscribe.com</a> — kostenloses Konto (10 GB/Monat).</li>
       <li>Windscribe für Windows installieren, einmal anmelden.</li>
       <li>Fertig — die App erkennt <code>windscribe-cli</code> und verbindet bei Bedarf automatisch.</li></ol>
       Status: ${gstat(s.windscribe)}`),
    gsec('🟣 ProtonVPN Free — gratis & unbegrenzt (WireGuard)', (s.wireguard_laender||[]).length>0,
      `<ol><li><a class="glink" href="https://protonvpn.com/free-vpn" target="_blank" rel="noreferrer">protonvpn.com</a> — kostenloses Konto.</li>
       <li><a class="glink" href="https://www.wireguard.com/install/" target="_blank" rel="noreferrer">WireGuard für Windows</a> installieren.</li>
       <li>Im Proton-Konto → Downloads → WireGuard-Config für ein Land erzeugen; die <code>.conf</code> öffnen und den Text kopieren.</li>
       <li>Hier einfügen, Land wählen, „importieren" — die App legt sie richtig benannt ab und trägt den Ordner ein.</li></ol>
       ${geoWgForm()}
       <div style="font-size:11px;color:#6a5c52;margin-top:6px">Hinweis: WireGuard braucht beim Verbinden Windows-Adminrechte (einmalige Abfrage). UK ist im Gratis-Tarif meist nicht dabei.</div>`),
    gsec('⚫ NordVPN — falls du ein Abo hast', !!s.nordvpn,
      `<ol><li><a class="glink" href="https://nordvpn.com/download/windows" target="_blank" rel="noreferrer">NordVPN für Windows</a> installieren + anmelden.</li>
       <li>Fertig — die App steuert es per Kommandozeile.</li></ol>Status: ${gstat(s.nordvpn)}`),
    gsec('⚪ Eigener Proxy (SSH-Tunnel, Mullvad-SOCKS, …)', (s.proxy_anzahl||0)>0,
      `<p>Im Zahnrad unter „Eigene Proxys" eintragen, z.B.:</p>
       <pre style="font-size:11px;color:#cfc2b8;white-space:pre-wrap">GB=socks5://127.0.0.1:1080\nsocks5://5.6.7.8:1080</pre>
       <p>Funktioniert mit jeder SOCKS5/HTTP-Adresse — auch ein <code>ssh -D 1080 user@server-in-UK</code>-Tunnel. Eingetragen: ${s.proxy_anzahl||0}.</p>`),
  ].join('');
  document.getElementById('geowiz-body').innerHTML=
    `<p style="font-size:12.5px;color:#a99a90;margin:0 0 8px">Alle Wege sind gleichzeitig nutzbar — die App probiert von gratis nach aufwändig durch, bis einer Zugang gibt. Richte einen oder mehrere ein.</p>`+
    vgl+erkannt+abschnitte+
    `<div class="gsec" style="border-color:#6b4a2a" open><div class="ginner"><b>🌍 Test</b> — prüft an einem geo-gesperrten Video deiner Warteschlange, welcher Weg Zugang gibt:
       <div class="gzeile"><button class="btn" onclick="geoTestStart()" ${t.laeuft?'disabled':''}>${t.laeuft?'testet…':'Jetzt testen'}</button></div>
       <div id="geotest">${geoTestHtml(t)}</div></div></div>`;
}
async function geoWgImport(){
  const content=document.getElementById('geowg-content').value, land=document.getElementById('geowg-land').value;
  const msg=document.getElementById('geowg-msg'); msg.textContent='…';
  try{
    const r=await fetch('/api/geo_wireguard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content,land})});
    const d=await r.json();
    if(d.fehler){msg.style.color='#e08a6a';msg.textContent=d.fehler;}
    else{msg.style.color='#9ec49a';msg.textContent='importiert ✓ — Länder: '+(d.laender||[]).join(', ');}
  }catch(e){msg.style.color='#e08a6a';msg.textContent='Fehler';}
  laden();
}
async function geoTestStart(){
  try{const r=await fetch('/api/geo_test',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    const d=await r.json(); if(d.fehler){alert(d.fehler);return;}}catch(e){}
  geoStatusLaden(true);
  if(!geoTestTimer)geoTestTimer=setInterval(()=>geoStatusLaden(false),1500);
}

/* ================= Bibliothek ================= */
let libdaten=[], libModus='kachel', libArchiv=false;
let libAuswahl=new Set(), libSelectMode=false, libLastClick=null;
let libPlaylistView='';   // Wenn gesetzt: Bibliothek zeigt NUR diese Playlist (in ihrer Reihenfolge)

function libSelectToggle(){
  libSelectMode=!libSelectMode; if(!libSelectMode)libAuswahl.clear();
  document.getElementById('libselbtn').classList.toggle('an',libSelectMode);
  libMalen();
}
function libSelektierend(ev){return libSelectMode||ev.ctrlKey||ev.metaKey||ev.shiftKey;}
function libSelectClick(ev,id){
  const arr=libGefiltert();
  if(ev.shiftKey&&libLastClick){
    const i1=arr.findIndex(x=>x.id===libLastClick), i2=arr.findIndex(x=>x.id===id);
    if(i1>=0&&i2>=0){const a=Math.min(i1,i2), b=Math.max(i1,i2);
      for(let i=a;i<=b;i++)libAuswahl.add(arr[i].id);}
  }else if(ev.ctrlKey||ev.metaKey||libSelectMode){
    if(libAuswahl.has(id))libAuswahl.delete(id); else libAuswahl.add(id);
    libLastClick=id;
  }else{ libAuswahl.clear(); libAuswahl.add(id); libLastClick=id; }
  libMalen();
}
function thumbClick(ev,id){
  if(libSelektierend(ev)){ev.stopPropagation(); libSelectClick(ev,id); return;}
  const x=libFind(id);
  if(x&&x.vorhanden)playerPlay([id]); else biblioNeuladen(id);
}
/* ---- Klick-Art zum Abspielen (Build 134, JB Punkt 4) ---------------------
   JB: „Einstellung Einfach- vs. Doppelklick zum Abspielen (Doppelklick
   Standard — JBs Kumpel bevorzugt Einfachklick; JB: Doppelklick fühlt sich
   nativer an und stört die Auswahl nicht)."
   Die Begründung ist auch der Grund für den Standard: bei Einfachklick
   kollidiert Abspielen mit dem Auswählen. Deshalb bleibt Doppelklick
   voreingestellt — wer den Einfachklick will, stellt ihn um. Gemerkt wird
   lokal, denn es ist eine Bedien-Vorliebe des Menschen am Gerät, keine
   Programm-Einstellung. */
function klickArt(){
  let v='doppel'; try{v=localStorage.getItem('ytdl_klickart')||'doppel';}catch(e){}
  return v==='einfach'?'einfach':'doppel';
}
function klickArtSetzen(v){
  try{localStorage.setItem('ytdl_klickart',v==='einfach'?'einfach':'doppel');}catch(e){}
  toast(v==='einfach'?'▶ Einfachklick spielt ab.':'▶ Doppelklick spielt ab (Einfachklick wählt aus).');
}
/* ---- Rahmen-Auswahl in der Bibliothek (Build 135, JB Punkt 4) ------------
   JB: „Rahmen-Auswahl mit der Maus wie in Windows / wie in der Abo-Ansicht."
   Dort gibt es das seit Build 94 (aboBandStart) — die Bibliothek bekommt
   bewusst DIESELBEN Eigenschaften, damit sich beides gleich anfühlt: erst ab
   5 px Bewegung wird daraus ein Band (darunter bleibt es ein normaler
   Klick), Strg erweitert die bestehende Auswahl, und der nachlaufende Klick
   der Startkachel wird geschluckt.
   Ein Unterschied ist nötig: Kacheln sind ziehbar (draggable). Ein Zug auf
   einer Kachel muss deshalb ein ZIEHEN bleiben — das Band startet nur auf
   freier Fläche, sonst könnte man Titel nicht mehr auf Playlists ziehen. */
let libBandLief=false;
let libBandLaeuft=false;                               // ein Zug ist unterwegs (Zuhoerer haengt an drei Ebenen)
function libBandStart(ev){
  if(ev.button!==0)return;
  if(ev.target.closest('button,a,input,select'))return;
  // Gezielt .kachel/tr: auch PANELS tragen ein data-id (gemessen) — ein
  // unspezifisches [data-id] haette den Zug schon am Panel abgefangen.
  if(ev.target.closest('.kachel[data-id],tr[data-id]'))return;   // auf einer Kachel: Ziehen hat Vorrang
  // Build 144e: Der Zuhoerer haengt jetzt auch am panel-body (leerer Bereich
  // unter den Kacheln). Getroffen und gescrollt wird trotzdem `libinhalt` —
  // sonst schoebe das Rand-Nachschieben am falschen Element. Ohne sichtbaren
  // Inhalt springt nichts an (ein Panel kann mehrere Ansichten tragen).
  const beh=ev.currentTarget;
  const flaeche=(beh.id==='libinhalt')?beh
    :[...beh.querySelectorAll('#libinhalt')].find(n=>n.offsetParent);
  if(!flaeche)return;
  if(libBandLaeuft)return;                             // zwei Ebenen hoeren mit -> nur EIN Band
  libBandLaeuft=true;
  const basis=new Set(ev.ctrlKey||ev.metaKey?[...libAuswahl]:[]);
  const x0=ev.clientX, y0=ev.clientY; let band=null;
  function mv(e){
    if(!band){
      if(Math.abs(e.clientX-x0)<5&&Math.abs(e.clientY-y0)<5)return;
      // Build 143 (JB-Bild): Ohne das hier markiert der Browser beim
      // Aufziehen den TEXT der Kacheln mit (blau hinterlegt) — der
      // Rahmen soll aber Titel waehlen, nicht Buchstaben.
      document.body.classList.add('nosel');
      band=document.createElement('div'); band.className='abo-band'; document.body.appendChild(band);
    }
    const l=Math.min(x0,e.clientX), t=Math.min(y0,e.clientY),
          r=Math.max(x0,e.clientX), b=Math.max(y0,e.clientY);
    band.style.left=l+'px'; band.style.top=t+'px';
    band.style.width=(r-l)+'px'; band.style.height=(b-t)+'px';
    const fr=flaeche.getBoundingClientRect();           // Rand-Nachschieben wie im Abo-Fenster
    if(e.clientY>fr.bottom-18)flaeche.scrollTop+=14;
    else if(e.clientY<fr.top+18)flaeche.scrollTop-=14;
    libAuswahl=new Set(basis);
    flaeche.querySelectorAll('.kachel[data-id],tr[data-id]').forEach(n=>{
      const q=n.getBoundingClientRect();
      if(q.left<r&&q.right>l&&q.top<b&&q.bottom>t)libAuswahl.add(n.dataset.id);
      n.classList.toggle('sel',libAuswahl.has(n.dataset.id));
    });
  }
  function up(){
    document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
    document.body.classList.remove('nosel'); libBandLaeuft=false;
    if(band){
      band.remove(); libBandLief=true;
      setTimeout(()=>{libBandLief=false;},0);
      libMalen();                                      // Auswahl-Leiste/Zähler nachziehen
    }else if(libAuswahl.size&&!basis.size){
      // Build 142 (JB): Ein KLICK auf freie Fläche (kein Zug) räumt die
      // Auswahl ab — so macht es der Explorer. Vorher blieb sie samt
      // Bulk-Leiste stehen, obwohl man erkennbar danebengeklickt hatte.
      // Mit Strg gedrückt (basis gefüllt) bleibt sie natürlich erhalten.
      libAuswahl.clear(); libMalen();
    }
  }
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
}
function kachelClick(ev,id){
  if(libBandLief)return;                               // der Klick war das Ende eines Band-Zugs
  if(ev.target.closest('button,a,input'))return;
  // Auswählen hat Vorrang: Strg/Umschalt und der Mehrfach-Auswahl-Modus
  // bleiben unberührt, sonst könnte man nichts mehr markieren.
  if(libSelektierend(ev)){ ev.preventDefault(); libSelectClick(ev,id); return; }
  if(klickArt()==='einfach'){ ev.preventDefault(); playerPlay([id]); }
}
function kachelDblClick(ev,id){
  if(ev.target.closest('button,a,input'))return;
  if(libSelektierend(ev))return;                       // im Auswahl-Modus nie abspielen
  if(klickArt()==='doppel'){ ev.preventDefault(); playerPlay([id]); }
}
function delEinzeln(id){
  const x=libFind(id)||{titel:''};
  if(confirm('„'+(x.titel||'').slice(0,40)+'“ in den Papierkorb verschieben?\\nDie Datei wird gelöscht (aus dem Windows-Papierkorb wiederherstellbar).'))
    biblio(id,'loeschen');
}
async function bulkAktion(op){
  const keys=[...libAuswahl]; if(!keys.length)return;
  if(op==='loeschen'&&!confirm(keys.length+' Titel in den Papierkorb verschieben?\\nDie Dateien werden gelöscht (aus dem Windows-Papierkorb wiederherstellbar).'))return;
  await fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({art:'bulk',op,keys})});
  libAuswahl.clear(); libLaden();
}
function bulkPlay(){ const arr=libGefiltert().filter(x=>libAuswahl.has(x.id)&&x.vorhanden).map(x=>x.id);
  if(arr.length)playerPlay(arr,0,'Auswahl'); }
async function bulkTags(){                              // Batch-Tag-Editor: Kanal + Titel suchen/ersetzen
  const keys=[...libAuswahl]; if(!keys.length)return;
  const uploader=prompt('Kanal / Künstler für alle '+keys.length+' Titel setzen?\\n(leer lassen = unverändert)','');
  if(uploader===null)return;
  const suchen=prompt('Im Titel suchen … (leer = nichts am Titel ändern)\\nz.B.  [Official Video]','');
  if(suchen===null)return;
  const ersetzen=suchen?(prompt('… ersetzen durch (leer = löschen):','')||''):'';
  const felder={}; if(uploader.trim())felder.uploader=uploader.trim();
  if(suchen){felder.titel_suchen=suchen; felder.titel_ersetzen=ersetzen;}
  if(!felder.uploader&&!felder.titel_suchen)return;
  await fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({art:'bulk',op:'tag',keys,felder})});
  libAuswahl.clear(); libLaden();
}
async function bulkMetadaten(){                         // Auto-Metadaten für die Auswahl neu von YouTube laden
  const keys=[...libAuswahl]; if(!keys.length)return;
  await fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({art:'bulk',op:'enrich',keys})});
  plInfo('Metadaten für '+keys.length+' Titel werden nachgeladen …', true);
  libAuswahl.clear(); libMalen(); setTimeout(libLaden,4000);
}
function bulkPlaylist(ev){
  // Build 142 (JB): „Wenn ich + Playlist anklicke, dann sollte die Option
  // kommen zu welcher Playlist ich die hinzufügen soll." Vorher verlangte es
  // eine oben VORGEWÄHLTE Liste und brach sonst mit einer Meldung ab — man
  // musste also erst woanders etwas einstellen, um hier klicken zu dürfen.
  // Jetzt dieselbe Auswahl wie am ＋ jeder Kachel (plOptionen), inklusive
  // „Neue Playlist…", nur eben für die ganze Markierung.
  const keys=[...libAuswahl]; if(!keys.length)return;
  const rein=async(id)=>{
    const p=plState.find(x=>x.id===id);
    const vorher=((p&&p.items)||[]).slice();
    for(const k of keys)await plApi({art:'add',id,key:k});
    plLetzterWurf={id,vorher,plNeu:false};
    toastMitZurueck(keys.length+' Titel → „'+((plState.find(x=>x.id===id)||{}).name||'Playlist')+'"',
                    'plZurueck()');
  };
  const opt=plState.map(p=>[p.name+' ('+p.items.length+')', false, ()=>rein(p.id)]);
  opt.push(['＋ Neue Playlist…', false, async()=>{
    const n=prompt('Name der neuen Playlist:'); if(!n||!n.trim())return;
    await plApi({art:'create',name:n.trim()});
    const id=(plState[plState.length-1]||{}).id; if(id)rein(id);}]);
  kmListe(kontextMenuBauen(ev||window.event,[]), '＋ '+keys.length+' Titel in …', opt);
}

/* ---- Abspielmodus (zyklisch), Shuffle, Meistgespielt, Zuletzt ---- */
function mische(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
// max. 5 Modi; klicken wechselt Icon + Verhalten
/* Abspielmodus wie bei Spotify: ZWEI getrennte Toggles statt eines 4-Stufen-
   Zyklus (JB 13.07.: „▶ sah aus wie Play, 🔁/🔂 zu klein, Modus nicht erkennbar").
   playShuffle = Zufall an/aus · playRepeat = aus/alle/eins. Die Knöpfe sind
   selbst gezeichnete SVGs (currentColor), aktiv = Akzentfarbe + Punkt darunter. */
/* Fehler-Rekorder (JB 06.08.: „stürzt ab wenn ich ansicht klicke" — hier
   nicht reproduzierbar): JEDER JS-Fehler landet ab jetzt im Server-Log
   (System/js_fehler.jsonl), damit der nächste Absturz eine Spur hat. */
window.addEventListener('error',ev=>{
  try{fetch('/api/js_fehler',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:String(ev.message||'').slice(0,400),
      quelle:String(ev.filename||'').slice(-80), zeile:ev.lineno||0})}).catch(()=>{});}catch(e){}
});
window.addEventListener('unhandledrejection',ev=>{
  try{fetch('/api/js_fehler',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:('Promise: '+String(ev.reason||'')).slice(0,400)})}).catch(()=>{});}catch(e){}
});
const ICONS={
  play:'M8 5v14l11-7z',
  pause:'M6 5h4v14H6zm8 0h4v14h-4z',
  prev:'M6 6h2v12H6zm12 0v12l-8.5-6z',
  next:'M16 6h2v12h-2zM6 6l8.5 6L6 18z',
  shuffle:'M10.59 9.17 5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z',
  repeat:'M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z',
  repeat1:'M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4zm-4-2V9h-1l-2 1v1h1.5v4H13z',
  yt:'M21.6 7.2c-.2-.9-.9-1.6-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4c-.9.2-1.6.9-1.8 1.8C2 8.8 2 12 2 12s0 3.2.4 4.8c.2.9.9 1.6 1.8 1.8 1.6.4 7.8.4 7.8.4s6.2 0 7.8-.4c.9-.2 1.6-.9 1.8-1.8.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3z',
  // Build 132 (JB: „die blauen Pfeile sehen schlecht aus, kannst du die vom
  // Stil identisch hinbekommen wie den play button?"). Das waren Emoji (⏪/⏩)
  // — die zeichnet jedes System anders und bringt oft eigene Farbe mit, hier
  // Blau. Jetzt gefüllte SVG-Dreiecke wie play/prev/next, also dieselbe
  // Form-Sprache und dieselbe Farbe wie der Rest der Leiste.
  back:'M11 12 19 6.5v11L11 12zm-8 0 8-5.5v11L3 12z',
  // Netflix-Parität (Nachtprüfung 06.08.): monochrome Flat-SVGs statt Emoji
  // an Karte + Player-Settings — Emoji bringen eigene Farben/Formen mit.
  plus:'M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z',
  chevron:'M12 15.5 4.5 8l1.4-1.4L12 12.7l6.1-6.1L19.5 8z',
  info2:'M11 10h2v7h-2zm0-3h2v2h-2zM12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16z',
  sub:'M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm2 8h6v2H6zm8 0h4v2h-4zM6 15h3v2H6zm5 0h7v2h-7z',
  speed:'M12 4a9 9 0 0 0-9 9 8.9 8.9 0 0 0 1.2 4.5l1.7-1A7 7 0 1 1 19 13a7 7 0 0 1-.9 3.4l1.7 1A9 9 0 0 0 12 4zm-1 9a1.5 1.5 0 0 0 2.4 1.2l4.2-3.2-5-1.4A1.5 1.5 0 0 0 11 13z',
  full:'M4 4h6v2H6v4H4V4zm10 0h6v6h-2V6h-4V4zM4 14h2v4h4v2H4v-6zm14 0h2v6h-6v-2h4v-4z',
  kreuz:'m6 5 6 6 6-6 1.4 1.4L13.4 12l6 6L18 19.4l-6-6-6 6L4.6 18l6-6-6-6z',
  fwd:'M13 12 5 17.5v-11L13 12zm8 0-8 5.5v-11L21 12z'};
const ICONS_VOLL={
  // 10-Sekunden-Kreispfeile (JB 05.08., Bild): unmissverständlich ±10 s —
  // die alten ⏪/⏩-Doppeldreiecke lasen sich wie voriger/nächster Titel.
  r10:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/><text x="12" y="16.5" text-anchor="middle" font-size="7.5" font-weight="700" fill="currentColor" stroke="none">10</text></svg>',
  f10:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/><text x="12" y="16.5" text-anchor="middle" font-size="7.5" font-weight="700" fill="currentColor" stroke="none">10</text></svg>'};
function ico(n){return ICONS_VOLL[n]||('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+ICONS[n]+'"/></svg>');}

/* ---- Browser-Zeichen für den Status-Punkt (Build 133, JB-Wunsch) ----------
   Reihenfolge der Prüfung ist wichtig: Edge und Chrome tragen beide „Chrome"
   im User-Agent, Safari steht auch in Chromes Kennung. Deshalb wird von der
   spezifischsten Kennung zur allgemeinsten geprüft — sonst wäre jeder
   Browser ein Chrome. */
function browserArt(){
  const ua=navigator.userAgent||'';
  if(/Firefox\\//.test(ua))                    return 'firefox';
  if(/Edg\\//.test(ua))                        return 'edge';
  if(/OPR\\//.test(ua))                        return 'opera';
  if(/Chrome\\//.test(ua))                     return 'chrome';
  if(/Safari\\//.test(ua))                     return 'safari';
  return 'sonst';
}
function browserName(){
  return {firefox:'Firefox',edge:'Edge',opera:'Opera',chrome:'Chrome',
          safari:'Safari',sonst:'unbekannt'}[browserArt()];
}
function browserZeichen(){
  const art=browserArt();
  const kern='<circle class="apikern" cx="12" cy="12" r="4.6"/>';
  // Firefox: JB-Korrektur — ein Kreis mit Meridianen ist ein GENERISCHER
  // Globus, kein Firefox. Erkennbar macht das Zeichen der Fuchsschweif, der
  // sich um die Kugel legt und oben in einer Spitze ausläuft. Deshalb: ein
  // fast geschlossener, kräftiger Bogen (der Schweif) mit Flammenzunge —
  // und der Kern in der Mitte ist die Erdkugel, die die Statusfarbe trägt.
  if(art==='firefox')
    // JB-Vorlage: Der Fuchs windet sich um die blaue ERDKUGEL — und genau
    // die trägt die Statusfarbe. Der Schweif ist ein kräftiger Bogen, der
    // oben rechts in der Flammenspitze ausläuft; die Kugel füllt die Mitte
    // deutlich größer als bei den anderen Zeichen, weil sie beim Firefox-
    // Logo das beherrschende Element ist.
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<circle class="apikern" cx="11.6" cy="12.4" r="6.4"/>'+
      '<path class="apiring" d="M17.2 5.6a9 9 0 1 0 2.4 4.9" stroke-width="2.8" stroke-linecap="round"/>'+
      '<path d="M15.4 2.6 21.4 4.9l-2.2 5.2-1.6-3.6z" fill="currentColor" opacity=".8"/>'+
      '</svg>';
  // Chrome: drei Segmente mit Fugen (statt eines glatten Rings) — das ist
  // das, was man auf kleiner Fläche als Chrome liest. Der Kern sitzt dort,
  // wo sonst das Blau steckt: genau die Stelle, die JB benannt hat.
  if(art==='chrome'||art==='opera')
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<path class="apiring" d="M12.9 3.05A9 9 0 0 1 20.5 15.6" stroke-width="2.6" stroke-linecap="round"/>'+
      '<path class="apiring" d="M18.6 18.7A9 9 0 0 1 5.2 16.9" stroke-width="2.6" stroke-linecap="round"/>'+
      '<path class="apiring" d="M4.2 14.7A9 9 0 0 1 10.6 3.2" stroke-width="2.6" stroke-linecap="round"/>'+
      kern+'</svg>';
  // Edge: der offene Bogen.
  if(art==='edge')
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<path class="apiring" d="M20 15a9 9 0 1 0-8 5.9" stroke-width="2.2" stroke-linecap="round"/>'+kern+'</svg>';
  // Safari: JB stellte frei, ob die blaue Scheibe oder die Nadel den Status
  // trägt. Die NADEL — die blaue Scheibe wäre bei 16 px eine große Farbfläche,
  // die den ganzen Kopfbereich einfärbt; ein rot leuchtender Kreis dieser
  // Größe sähe nach Alarm aus, obwohl nur die Verbindung fehlt. Die Nadel ist
  // klein, liegt in der Mitte und ist beim echten Logo ohnehin das rote Teil.
  if(art==='safari')
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<circle class="apiring" cx="12" cy="12" r="9" stroke-width="1.8"/>'+
      '<path class="apikern" d="M16.8 7.2 13.9 13.9 7.2 16.8 10.1 10.1z"/>'+
      '</svg>';
  return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
    '<circle class="apiring" cx="12" cy="12" r="9" stroke-width="1.6"/>'+kern+'</svg>';
}
let playShuffle=false, playRepeat='aus';               // 'aus' | 'alle' | 'eins'
try{
  playShuffle=localStorage.getItem('ytdl_shuffle')==='1';
  const r=localStorage.getItem('ytdl_repeat'); if(r==='alle'||r==='eins')playRepeat=r;
  // Migration vom alten 4-Stufen-Modus (einmalig, solange die neuen Keys fehlen)
  if(localStorage.getItem('ytdl_shuffle')===null&&localStorage.getItem('ytdl_repeat')===null){
    const alt=localStorage.getItem('ytdl_playmode');
    if(alt==='zufall')playShuffle=true;
    if(alt==='alle'||alt==='eins')playRepeat=alt;
  }
}catch(e){}
/* Abspielart (Build 144l, JB 25.07.): EINE Auswahl mit vier Klartext-Optionen
   statt des durchklickenden Symbols, das „nur Musik" hiess aber nach FORMAT
   filterte (Video-Songs fielen raus, Comedy-MP3s blieben).
     Alles · Nur Ton (MP3) · Nur Video · Nur Songs.
   „Nur Songs" ist die INHALTS-Achse: Lieder, egal ob MP3 oder Video-Song —
   stützt sich auf die Musik-Einstufung (`musik`) aus dem Backend (Build 144h).
   Wirkt überall gleich (Raster, Radio, Autoplay), weil alle über artPasst
   gehen; ausgewählte Playlists spielen weiter wörtlich. */
const PLAYART=[
  ['alle','🎬🎵','Alles','Ton und Video, jeder Inhalt'],
  ['mp3','🎧','Nur Ton','nur Audiodateien (MP3/m4a …)'],
  ['video','🎬','Nur Video','nur Videodateien'],
  ['songs','🎵','Nur Songs','Lieder — egal ob MP3 oder Video-Song; Trailer, Gaming-Clips, Comedy und Podcasts bleiben draussen']];
let playArt='alle';
try{const v=localStorage.getItem('ytdl_playart'); if(PLAYART.some(o=>o[0]===v))playArt=v;}catch(e){}
function playArtMenu(ev){
  aktionsMenu(ev, PLAYART.map(o=>[(o[0]===playArt?'✓ ':'　')+o[1]+' '+o[2], ()=>playArtSetzen(o[0])]));
}
function playArtSetzen(v){
  playArt=v; try{localStorage.setItem('ytdl_playart',v);}catch(e){}
  transportRender(); libMalen(); renderPlayerQueue();  // Ansicht + Queue folgen sofort
  const o=PLAYART.find(o=>o[0]===v)||PLAYART[0];
  toast('▶ '+o[1]+' '+o[2]);
}
// Hat die Bibliothek überhaupt schon Musik-Einstufungen? Vor dem App-Neustart
// (youtube_app.py lädt nicht heiss nach) fehlt das Feld — dann darf „Nur
// Songs" NICHT alles wegfiltern, sonst sähe die Bibliothek leer aus.
function musikBekannt(){return (libdaten||[]).some(x=>x.musik);}
function artPasst(x){
  if(playArt==='alle')return true;
  if(playArt==='songs')return !musikBekannt()||(!!x.musik&&x.musik!=='nein');
  const audio=x.dateiart?x.dateiart==='audio':(x.kategorie==='MP3');
  return playArt==='mp3'?audio:!audio;
}
function shuffleToggle(){playShuffle=!playShuffle;
  try{localStorage.setItem('ytdl_shuffle',playShuffle?'1':'0');}catch(e){}
  transportRender();}
function repeatCycle(){playRepeat=(playRepeat==='aus')?'alle':(playRepeat==='alle'?'eins':'aus');
  try{localStorage.setItem('ytdl_repeat',playRepeat);}catch(e){}
  transportRender();}
/* Zieht NUR die Zustände der Transport-Knöpfe nach (classList/innerHTML des
   einzelnen Knopfs) — kein Neuaufbau der Leiste, darum reagiert der Klick sofort. */
function transportRender(){
  const pe=document.getElementById('pl-el');
  document.querySelectorAll('[data-tr="shuffle"]').forEach(b=>{
    b.classList.toggle('an',playShuffle); b.title='Zufall: '+(playShuffle?'AN':'aus');});
  document.querySelectorAll('[data-tr="repeat"]').forEach(b=>{
    b.classList.toggle('an',playRepeat!=='aus');
    b.innerHTML=ico(playRepeat==='eins'?'repeat1':'repeat');
    b.title='Wiederholen: '+(playRepeat==='aus'?'aus':(playRepeat==='alle'?'alle Titel':'nur dieser Titel'))+' (klicken: aus → alle → einer)';});
  // DER Wurm (JB 05.08., „wechselt kurz und springt zurück"): dieser Maler
  // läuft im 1-s-Takt und las NUR das <audio>-Element — am Gerät VLC gibt es
  // keins, also übermalte er den richtigen Zustand sofort wieder mit ▶.
  const spielt=vlcAktiv()?vlcSpielt:!!(pe&&!pe.paused);
  document.querySelectorAll('[data-tr="pp"]').forEach(b=>{
    b.innerHTML=ico(spielt?'pause':'play');
    b.title=spielt?'Pause':'Abspielen';});
  document.querySelectorAll('[data-tr="radio"]').forEach(b=>b.classList.toggle('an',radioAktiv));
  document.querySelectorAll('[data-tr="art"]').forEach(b=>{
    const o=PLAYART.find(o=>o[0]===playArt)||PLAYART[0];
    b.classList.toggle('an',playArt!=='alle');
    b.textContent=o[1];                                 // aktuelles Symbol
    b.title='Was spielt: '+o[2]+' — klicken für die Auswahl (Alles · Nur Ton · '+
      'Nur Video · Nur Songs). Gilt überall: Bibliothek, Playlists (übersprungene '+
      'Titel bleiben gedimmt drin), Radio und Autoplay.';
  });
}
function queueIdxPassend(start,dir){
  const q=playerState.queue;
  for(let i=start;i>=0&&i<q.length;i+=dir){
    const x=libFind(q[i]);
    if(x&&x.vorhanden&&artPasst(x))return i;
  }
  return -1;
}
function playerAdvance(){                             // automatisch nach Titel-Ende
  if(sleepTitelende){sleepAusloesen(); return;}      // Sleep-Timer „nach diesem Titel"
  if(radioAktiv){                                    // Radio läuft linear + füllt endlos nach
    radioNachfuellen();
    if(playerState.idx<playerState.queue.length-1)playerState.idx++;
    renderPlayerMedia(); return;
  }
  if(playRepeat==='eins'){renderPlayerMedia(); return;}   // gleichen Titel wiederholen
  if(playShuffle&&playerState.queue.length>1){            // Zufall: anderer PASSENDER Titel
    const kand=playerState.queue.map((k,i)=>i)
      .filter(i=>i!==playerState.idx&&(x=>x&&x.vorhanden&&artPasst(x))(libFind(playerState.queue[i])));
    if(kand.length){playerState.idx=kand[Math.floor(Math.random()*kand.length)]; renderPlayerMedia();}
    return;
  }
  let n=queueIdxPassend(playerState.idx+1,1);             // nächster passender in der Reihe
  if(n<0&&playRepeat==='alle')n=queueIdxPassend(0,1);
  if(n>=0){playerState.idx=n; renderPlayerMedia();}
  else if(playerState.queue.length<=1)naechstesAusBibliothek();
  // sonst: Playlist (nach Abspielart) zu Ende -> Stopp
}

/* Einzeltitel ohne Playlist zu Ende (JB 14.07.): weiterspielen wie YouTube-
   Autoplay — der NÄCHSTE Titel der aktuellen Bibliotheks-Ansicht (Suche/
   Filter/Sortierung zählen), bei Zufall ein zufälliger; Blacklist bleibt
   außen vor. Am Ende der Bibliothek stoppt es ehrlich. */
function naechstesAusBibliothek(){
  const k=aktKey();
  const pool=libGefiltert().filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x));
  if(!pool.length)return;
  let nk=null;
  if(playShuffle){
    const kand=pool.filter(x=>x.id!==k);
    if(kand.length)nk=kand[Math.floor(Math.random()*kand.length)].id;
  }else{
    const i=pool.findIndex(x=>x.id===k);
    if(i>=0&&i<pool.length-1)nk=pool[i+1].id;      // der Nächste in der Ansicht
    else if(i<0)nk=pool[0].id;                     // aktueller nicht in der Ansicht -> von vorn
  }
  if(!nk)return;
  playerState.queue=[nk]; playerState.idx=0; playerState.quelle='Bibliothek';
  renderPlayerMedia();
}
function playMostPlayed(){
  let arr=libdaten.filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x))
    .sort((a,b)=>(b.plays||0)-(a.plays||0)).slice(0,100).map(x=>x.id);
  if(!arr.length){alert('Noch nichts abgespielt.');return;}
  if(playShuffle)mische(arr); playerPlay(arr,0,'★ Meistgespielt');
}
function playLetzte(){                                // „Zuletzt gespielt"
  const arr=libdaten.filter(x=>x.vorhanden&&(x.last_play||0)>0&&artPasst(x))
    .sort((a,b)=>(b.last_play||0)-(a.last_play||0)).slice(0,100).map(x=>x.id);
  if(!arr.length){alert('Noch nichts abgespielt.');return;}
  playerPlay(arr,0,'🕘 Zuletzt gespielt');
}

/* ---- 📻 Radio: endloser, personalisierter Zufalls-Stream ---- */
let radioAktiv=false;
// Build 144o (JB): „der favorit wird immer abgespielt." Im Zufalls-/Radio-Pool
// zählt nur der Favorit-Repräsentant jeder Gruppe (Hauptsong oder Clip).
function radioKandidaten(){const fb=libdaten.some(x=>typeof x.ist_favorit!=='undefined');
  return libdaten.filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x)&&(!fb||x.ist_favorit));}
function radioPick(anzahl,vermeiden){
  const pool=radioKandidaten(); if(!pool.length)return [];
  // Vermeidungs-Fenster nie größer als der Pool minus 1 — sonst blockiert es bei
  // kleiner Bibliothek ALLE Titel und es käme nichts mehr (Bug 09.07.).
  const maxMeiden=Math.min(pool.length-1, 30);
  const letzte=new Set((vermeiden||[]).slice(-maxMeiden)), out=[];
  let schutz=anzahl*50;                               // Sicherung gegen Endlosschleife
  while(out.length<anzahl && schutz-->0){
    // gewichtete Wahl: beliebtere Titel häufiger (Gewicht = 1 + Abspielungen), aber alles möglich
    const gesamt=pool.reduce((s,x)=>s+1+(x.plays||0),0);
    let r=Math.random()*gesamt, pick=pool[0];
    for(const x of pool){r-=1+(x.plays||0); if(r<=0){pick=x;break;}}
    if(letzte.has(pick.id))continue;                 // keine kurzfristige Wiederholung
    out.push(pick.id); letzte.add(pick.id);
    if(letzte.size>maxMeiden)letzte.delete([...letzte][0]);
  }
  return out;
}
function radioStart(){
  const erste=radioPick(40,[]);
  if(!erste.length){alert('Noch keine abspielbaren Titel — lade erst etwas herunter.');return;}
  radioAktiv=true;
  playerState.queue=erste; playerState.idx=0; playerState.quelle='📻 Radio';
  ensurePlayer(); renderPlayerMedia();
  plInfo('📻 Radio läuft — endloser Mix aus deiner Bibliothek', true);   // Zustand
}
function radioNachfuellen(){                          // hält den Stream unendlich am Laufen
  if(radioAktiv && playerState.idx>=playerState.queue.length-2){
    const mehr=radioPick(20, playerState.queue.slice(-30));
    if(mehr.length)playerState.queue=playerState.queue.concat(mehr);
  }
}

/* ---- Sleep-Timer (Nutzer schaltet ein/aus) ---- */
let sleepTimer=null, sleepTitelende=false, sleepEndeZeit=0;
function sleepSetzen(v){
  clearTimeout(sleepTimer); sleepTimer=null; sleepTitelende=false; sleepEndeZeit=0;
  if(v==='titel'){sleepTitelende=true;}
  else{const min=parseInt(v,10)||0; if(min>0){sleepEndeZeit=Date.now()+min*60000; sleepTimer=setTimeout(sleepAusloesen,min*60000);}}
  sleepLabel();
}
function sleepAusloesen(){const el=document.getElementById('pl-el'); if(el)el.pause();
  sleepTimer=null; sleepEndeZeit=0; sleepTitelende=false; sleepLabel();}
function sleepLabel(){const l=document.getElementById('sleepval'); if(!l)return;
  l.textContent=sleepTitelende?'· nach diesem Titel':(sleepEndeZeit?('· noch '+Math.max(1,Math.round((sleepEndeZeit-Date.now())/60000))+' min'):'');}

/* ---- Ausschnitt/Clip: vorne + hinten schneiden -> ein Video (ffmpeg, ohne Längenlimit) ---- */
/* ✂-Schneide-Leiste (Build 101, JB: „zwei Regler ziehen können") — ersetzt die
   alten mm:ss-Eingabefelder. Griff ziehen springt den Player LIVE an die
   Stelle (B-Griff kurz davor, damit man das Ende hört); läuft die Wiedergabe
   in die B-Marke, pausiert sie. ✂ speichert wie bisher nicht-destruktiv
   als NEUEN Bibliothekseintrag (das Original bleibt). */
let schnitt=null;                                      // {id,a,b,dauer}
async function clipDialog(id){
  if(!id){alert('Kein Titel gewählt.');return;}
  if(aktKey()!==id){playerPlay([id]); await new Promise(r=>setTimeout(r,500));}
  // Am Gerät VLC gibt es kein <audio>-Element — Dauer/Position kommen aus
  // dem letzten VLC-Status (JB 05.08.: ✂ auch im VLC-Modus).
  let dauer, curT;
  if(vlcAktiv()&&aktKey()===id&&vlcDauerLetzte){
    dauer=vlcDauerLetzte; curT=vlcPosLetzte||0;
  }else{
    const el=document.getElementById('pl-el');
    if(!el||!isFinite(el.duration)||!el.duration){toast('Titel lädt noch — gleich nochmal ✂ drücken.');return;}
    dauer=el.duration; curT=el.currentTime;
  }
  schnittZu();
  schnitt={id, a:0, b:(curT>1&&curT<dauer-1)?curT:dauer, dauer};
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='schnitt-fly'; fly.tabIndex=-1; fly.style.height='auto';
  fly.innerHTML='<div class="abo-fly-titel">✂ Ausschnitt wählen<span class="spacer"></span>'+
    '<button class="ib" title="Schließen (Esc)" onclick="schnittZu()">✕</button></div>'+
    '<div class="schnitt-spur" id="schnitt-spur">'+
      '<div class="schnitt-bereich" id="schnitt-bereich"></div>'+
      '<div class="schnitt-griff" id="schnitt-a" title="Anfang ziehen — der Player springt mit">A</div>'+
      '<div class="schnitt-griff" id="schnitt-b" title="Ende ziehen — der Player springt kurz davor">B</div></div>'+
    '<div class="schnitt-zeiten"><span id="schnitt-za"></span><span id="schnitt-zl"></span><span id="schnitt-zb"></span></div>'+
    '<div class="abo-staffel" style="margin-top:8px"><span style="opacity:.7">Wiedergabe endet an B.</span><span class="spacer"></span>'+
      '<button class="btn mini" onclick="schnittVorhoeren()" title="Den gewählten Bereich von A an abspielen">▶ Bereich</button>'+
      '<button class="btn mini" onclick="schnittSpeichern(this)" title="Bereich als NEUEN Titel speichern — das Original bleibt unangetastet">✂ Ausschnitt speichern</button></div>';
  document.body.appendChild(fly); nachVorn(fly);
  const m=document.querySelector('.pl-media'), r0=m?m.getBoundingClientRect():null;
  const w=Math.min(560, window.innerWidth-24);
  fly.style.width=w+'px';
  fly.style.left=Math.max(12,Math.min((r0?r0.left+(r0.width-w)/2:12), window.innerWidth-12-w))+'px';
  fly.style.top=Math.max(12,(r0?Math.min(r0.bottom-140, window.innerHeight-160):window.innerHeight/2))+'px';
  fly.addEventListener('keydown',e=>{if(e.key==='Escape'){schnittZu(); e.stopPropagation();}});
  ['schnitt-a','schnitt-b'].forEach(g=>document.getElementById(g).addEventListener('pointerdown',schnittDrag));
  el.addEventListener('timeupdate',schnittTick);
  fly.focus();
  schnittMalen();
}
function schnittZu(){
  const f=document.getElementById('schnitt-fly'); if(f)f.remove();
  const el=document.getElementById('pl-el'); if(el)el.removeEventListener('timeupdate',schnittTick);
  schnitt=null;
}
function schnittTick(){
  const el=document.getElementById('pl-el');
  if(!schnitt||!el)return;
  if(aktKey()!==schnitt.id){schnittZu();return;}       // Titel gewechselt -> Leiste weg
  if(el.currentTime>=schnitt.b&&!el.paused)el.pause(); // „…und beendet" (JB)
}
function schnittMalen(){
  if(!schnitt)return;
  const spur=document.getElementById('schnitt-spur'); if(!spur)return;
  const w=spur.clientWidth, pa=schnitt.a/schnitt.dauer*w, pb=schnitt.b/schnitt.dauer*w;
  const ber=document.getElementById('schnitt-bereich');
  ber.style.left=pa+'px'; ber.style.width=Math.max(2,pb-pa)+'px';
  document.getElementById('schnitt-a').style.left=pa+'px';
  document.getElementById('schnitt-b').style.left=pb+'px';
  document.getElementById('schnitt-za').textContent='A '+zeit(schnitt.a);
  document.getElementById('schnitt-zb').textContent='B '+zeit(schnitt.b);
  document.getElementById('schnitt-zl').textContent='Länge '+zeit(Math.max(0,schnitt.b-schnitt.a));
}
function schnittDrag(ev){
  if(!schnitt)return;
  ev.preventDefault(); ev.stopPropagation();
  const griffA=ev.currentTarget.id==='schnitt-a';
  const spur=document.getElementById('schnitt-spur');
  const el=document.getElementById('pl-el');
  function mv(e){
    const r=spur.getBoundingClientRect();
    const t=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width))*schnitt.dauer;
    if(griffA)schnitt.a=Math.min(t,schnitt.b-1);
    else schnitt.b=Math.max(t,schnitt.a+1);
    if(el){el.currentTime=griffA?schnitt.a:Math.max(schnitt.a,schnitt.b-1.5);}   // live mithören
    schnittMalen();
  }
  function up(){document.removeEventListener('pointermove',mv);document.removeEventListener('pointerup',up);}
  document.addEventListener('pointermove',mv);document.addEventListener('pointerup',up);
  mv(ev);
}
function schnittVorhoeren(){
  const el=document.getElementById('pl-el');
  if(!schnitt||!el)return;
  el.currentTime=schnitt.a; el.play();
}
async function schnittSpeichern(btn){
  if(!schnitt)return;
  const daten={id:schnitt.id, start:schnitt.a>0.5?zeit(schnitt.a):'', ende:schnitt.b<schnitt.dauer-0.5?zeit(schnitt.b):''};
  if(btn){btn.disabled=true; btn.textContent='⏳ …';}
  plInfo('✂ Ausschnitt wird erstellt …', true);
  try{
    const r=await fetch('/api/clip',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(daten)});
    const d=await r.json();
    // Build 144i (JB 25.07.: „zeigt dass er es geschafft hat, aber die
    // Fehlermeldung"): Hier wurde eine NIE deklarierte Variable geprüft — der
    // Erfolgspfad warf dadurch einen ReferenceError, der unten im catch als
    // „fehlgeschlagen" ankam, obwohl die Datei längst da war.
    // plInfo() ist der richtige Weg (wie überall sonst im Player).
    if(d.fehler){plInfo(''); alert('Ausschnitt: '+d.fehler); if(btn){btn.disabled=false;btn.textContent='✂ Ausschnitt speichern';}}
    else{plInfo('✂ Ausschnitt erstellt: '+d.name); toast('✂ '+d.name); libLaden(); schnittZu();}
  }catch(e){alert('Ausschnitt fehlgeschlagen (App erreichbar?).'); if(btn){btn.disabled=false;btn.textContent='✂ Ausschnitt speichern';}}
}

function ext(n){const m=(n||'').match(/\\.([a-z0-9]+)$/i); return m?m[1].toUpperCase():'–';}
// Wählbare Spalten (= „Reiter"): Beschriftung, Text-Funktion, Sortier-Funktion
const COLDEF={
  kategorie:{l:'Kategorie', t:x=>x.kategorie, s:x=>x.kategorie||''},
  qualitaet:{l:'Qualität', t:x=>x.qualitaet, s:x=>x.qualitaet||''},
  technik:{l:'Codec / Audio', t:x=>technikText(x), s:x=>x.abr||0},
  groesse:{l:'Größe', t:x=>mb(x.groesse), s:x=>x.groesse||0},
  dauer:{l:'Dauer', t:x=>x.dauer?zeit(x.dauer):'–', s:x=>x.dauer||0},
  uploader:{l:'Kanal', t:x=>x.uploader||'–', s:x=>x.uploader||''},
  kuenstler:{l:'Künstler', t:x=>x.kuenstler||'–', s:x=>x.kuenstler||''},
  album:{l:'Album', t:x=>x.album||'–', s:x=>x.album||''},
  upload_date:{l:'Datum', t:x=>ytdatum(x.upload_date)||'–', s:x=>x.upload_date||''},
  status:{l:'Status', t:x=>x.vorhanden?'vorhanden':'verschoben', s:x=>x.vorhanden?1:0},
  abr:{l:'Bitrate', t:x=>x.abr?x.abr+' kbps':'–', s:x=>x.abr||0},
  asr:{l:'Samplerate', t:x=>x.asr?Math.round(x.asr/1000)+' kHz':'–', s:x=>x.asr||0},
  hoehe:{l:'Auflösung', t:x=>x.hoehe?x.hoehe+'p':'–', s:x=>x.hoehe||0},
  videoid:{l:'Video-ID', t:x=>x.videoid, s:x=>x.videoid||''},
  added:{l:'Hinzugefügt', t:x=>x.ts?new Date(x.ts*1000).toLocaleDateString('de-DE'):'–', s:x=>x.ts||0},
  plays:{l:'Abspielungen', t:x=>String(x.plays||0), s:x=>x.plays||0},
  folge:{l:'Folge #', t:x=>x.abo_nr?('#'+x.abo_nr):'–', s:x=>x.abo_nr||0},
  // Build 144g (JB Punkt 4): „Videonummer je Kanal" — ausdrücklich NICHT die
  // Track-Nummer (die stünde bei Einzelvideos 500-mal auf 1). Bei Abos ist es
  // die echte Nummer aus dem Backkatalog, sonst die Position innerhalb der
  // Videos dieses Kanals hier. „von" macht die Bezugsgröße sichtbar.
  // An JBs echter Bibliothek gemessen: 69 von 84 Titeln stünden auf „#1" —
  // nicht als Track-Nummer, sondern weil er von den meisten Kanälen genau EIN
  // Video hat. Angezeigt sähe das aus wie die befürchtete „500× die 1".
  // Deshalb: eine abgeleitete Nummer erscheint nur, wenn es beim selben Kanal
  // etwas zu ordnen GIBT. Die echte Abo-Nummer steht immer — sie zählt über
  // den ganzen Kanal und sagt auch bei einem einzelnen Video etwas aus.
  kanalnr:{l:'Kanal #', t:x=>x.abo_nr?('#'+x.abo_nr)
                          :(x.kanal_von>1?('#'+x.kanal_nr+' von '+x.kanal_von):'–'),
           s:x=>x.kanal_nr||0},
  // Etappe A (Spec Punkt 5): Genre aus MusicBrainz — Grundlage der TV-Bibliothek.
  genre:{l:'Genre', t:x=>x.genre||'–', s:x=>(x.genre||'').toLowerCase()},
  ext:{l:'Endung', t:x=>ext(x.name), s:x=>ext(x.name)}
};
const COLALL=Object.keys(COLDEF);
const COLDEFAULT=['kategorie','qualitaet','technik','groesse','dauer','uploader','upload_date','status'];
let libcols=ladeCols(), libsort=ladeSort();

function ladeCols(){
  let cfg=null; try{cfg=JSON.parse(localStorage.getItem('ytdl_libcols_v1'));}catch(e){}
  if(Array.isArray(cfg)&&cfg.every(c=>c&&COLALL.includes(c.key))){
    COLALL.forEach(k=>{if(!cfg.find(c=>c.key===k))cfg.push({key:k,sichtbar:false});});
    return cfg.filter(c=>COLALL.includes(c.key));
  }
  return COLALL.map(k=>({key:k,sichtbar:COLDEFAULT.includes(k)}));
}
function saveCols(){try{localStorage.setItem('ytdl_libcols_v1',JSON.stringify(libcols));}catch(e){}}
function sichtbareCols(){return libcols.filter(c=>c.sichtbar).map(c=>c.key);}
function ladeSort(){try{const s=JSON.parse(localStorage.getItem('ytdl_libsort_v1'));if(s&&s.key)return s;}catch(e){}return {key:'neu',dir:-1};}
function saveSort(){try{localStorage.setItem('ytdl_libsort_v1',JSON.stringify(libsort));}catch(e){}}

let _libSig=null;
async function libLaden(){
  // Ausdruecklicher Aufruf (Aktion, Auswahl aufheben, Menue frisch): IMMER zeichnen.
  try{const r=await fetch('/api/bibliothek'); const txt=await r.text(); _libSig=txt;
      const d=JSON.parse(txt); libdaten=d.items||[]; libMalen();}catch(e){}
}
async function libPoll(){
  // Der 5-Sekunden-Takt baute bisher IMMER das ganze Bibliotheks-innerHTML neu auf
  // -- dabei werden alle <img> neu erzeugt, und Thumbnails ohne Browser-Cache laden
  // sichtbar nach (Flackern alle 5 s, JB 25.07.: „ein paar, John Waite …"). Jetzt
  // im Takt nur zeichnen, wenn sich die Antwort WIRKLICH geaendert hat.
  try{const r=await fetch('/api/bibliothek'); const txt=await r.text();
      if(txt===_libSig)return; _libSig=txt;
      const d=JSON.parse(txt); libdaten=d.items||[]; libMalen();}catch(e){}
}
function libAnsicht(m){
  libModus=m;
  document.getElementById('vb-kachel').classList.toggle('an',m==='kachel');
  document.getElementById('vb-alben').classList.toggle('an',m==='alben');
  document.getElementById('vb-liste').classList.toggle('an',m==='liste');
  libMalen();
}
function libArchivToggle(){
  libArchiv=!libArchiv;
  const b=document.getElementById('libarchivbtn');
  b.classList.toggle('an',libArchiv); b.textContent=libArchiv?'← Zurück zur Bibliothek':'🗄 Archiv anzeigen';
  libMalen();
}
async function libEnrich(btn){
  btn.disabled=true; const t=btn.textContent; btn.textContent='lädt…';
  try{await fetch('/api/biblio_enrich',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});}catch(e){}
  setTimeout(()=>{btn.disabled=false; btn.textContent=t; libLaden();},2000);
}
function ytdatum(d){if(!d||d.length!==8)return'';return d.slice(6,8)+'.'+d.slice(4,6)+'.'+d.slice(0,4);}
function technikText(x){
  // Nach der WIRKLICH servierten Datei entscheiden (dateiart vom Server):
  // fehlt das Video und es gibt nur die MP3, gehört die Audio-Ansicht
  // (Cover+Visualizer) her — statt schwarzem Video-Element (JB 14.07.).
  const istAudio=x.dateiart?x.dateiart==='audio':((x.kategorie==='MP3')||(!x.vcodec&&x.acodec));
  const p=[];
  if(istAudio){
    if(x.acodec)p.push(x.acodec.toUpperCase());
    if(x.abr)p.push(x.abr+' kbps');
    if(x.asr)p.push(Math.round(x.asr/1000)+' kHz');
  }else{
    if(x.vcodec)p.push(x.vcodec.toUpperCase());
    if(x.hoehe)p.push(x.hoehe+'p');
    if(x.acodec)p.push(x.acodec.toUpperCase());
  }
  return p.join(' · ')||'–';
}

function sortVal(x,key){
  if(key==='neu')return x.ts||0;
  if(key==='titel')return (x.titel||'').toLowerCase();
  const d=COLDEF[key]; return d?d.s(x):0;
}
function libGefiltert(){
  const q=(document.getElementById('libsuche').value||'').toLowerCase().trim();
  // Playlist-Ansicht: nur die Titel dieser Playlist, in Playlist-Reihenfolge (keine Sortierung).
  if(libPlaylistView){
    const p=plState.find(x=>x.id===libPlaylistView);
    let arr=(p?p.items:[]).map(k=>libFind(k)).filter(Boolean).filter(artPasst);
    if(q)arr=arr.filter(x=>(x.titel+' '+(x.uploader||'')).toLowerCase().includes(q));
    return arr;
  }
  const f=document.getElementById('libfilter').value;
  const hide=document.getElementById('libhidegray').checked;
  // Build 144o (JB): Es erscheint nur der FAVORIT jeder Gruppe als Kachel
  // (Hauptsong ODER ein Ausschnitt); die Alternativen liegen im Rechtsklick.
  // Solange die API das Feld noch nicht liefert (kurz vor dem Selbst-Neustart),
  // NICHT filtern — sonst sähe die Bibliothek leer aus.
  // Build 144l: „Nur Songs" steckt in der Abspielart (artPasst), wirkt überall.
  const favBekannt=libdaten.some(x=>typeof x.ist_favorit!=='undefined');
  let arr=libdaten.filter(x=>!favBekannt||x.ist_favorit).filter(x=>!!x.archiviert===libArchiv).filter(artPasst);
  if(f==='vorhanden')arr=arr.filter(x=>x.vorhanden);
  else if(f==='verschoben')arr=arr.filter(x=>!x.vorhanden);
  else if(f==='herz')arr=arr.filter(x=>x.herz);        // ❤ Lieblingssongs (JB 05.08.)
  if(hide&&!libArchiv)arr=arr.filter(x=>x.vorhanden);
  if(q)arr=arr.filter(x=>(x.titel+' '+(x.uploader||'')).toLowerCase().includes(q));
  const key=libsort.key, dir=libsort.dir;
  arr.sort((a,b)=>{
    let va=sortVal(a,key), vb=sortVal(b,key), c;
    if(typeof va==='number')c=va-vb; else c=String(va).localeCompare(String(vb));
    c=dir<0?-c:c;
    if(c===0&&key!=='titel')return (a.titel||'').localeCompare(b.titel||'');   // Sekundär immer Titel
    return c;
  });
  return arr;
}
function fuelleSortSelect(){
  const sel=document.getElementById('libsort'); if(!sel)return;
  const opts=[['neu','Neueste zuerst'],['titel','Titel A–Z']].concat(sichtbareCols().map(k=>[k,COLDEF[k].l]));
  sel.innerHTML=opts.map(([k,l])=>`<option value="${k}">${l}</option>`).join('');
  sel.value=opts.find(o=>o[0]===libsort.key)?libsort.key:'neu';
}
function setSortSelect(v){libsort={key:v,dir:v==='neu'?-1:1}; saveSort(); libMalen();}
function setSort(key){
  if(libsort.key===key)libsort.dir=-libsort.dir; else libsort={key,dir:key==='neu'?-1:1};
  saveSort(); libMalen();
}
function pfeil(key){return libsort.key===key?(libsort.dir<0?' ▼':' ▲'):'';}

function colMenuToggle(ev){ if(ev)ev.stopPropagation();
  const m=document.getElementById('libcolmenu'); const zu=m.style.display==='none';
  m.style.display=zu?'block':'none';
  // Build 125: erst zeichnen (sonst misst popoverBei eine leere Box), dann
  // an den <body> hängen und am Knopf ausrichten.
  // Build 125: Das Spalten-Menü löst das Ansicht-Menü ab, statt sich darüber
  // zu legen (gemessen: beide offen überlappten sich). Genauso machen es die
  // Nachbar-Einträge „Dubletten" und „Auto-Tagging" mit ansichtZu().
  // Anker bleibt der ⚙-Knopf — der ist immer sichtbar, der Menüeintrag nicht.
  if(zu){ansichtZu(); colMenuMalen();
    menuAnBody(m, document.getElementById('libansichtbtn'));}}
function colMenuMalen(){
  const m=document.getElementById('libcolmenu');
  m.innerHTML='<div class="colmenu-titel">Spalten — Häkchen = anzeigen, Pfeile = Reihenfolge.<br>Klick auf eine Spaltenüberschrift sortiert danach.</div>'+
    libcols.map((c,i)=>`<div class="colrow">
      <button class="colmv" onclick="colMove(${i},-1)" ${i===0?'disabled':''}>▲</button>
      <button class="colmv" onclick="colMove(${i},1)" ${i===libcols.length-1?'disabled':''}>▼</button>
      <label><input type="checkbox" ${c.sichtbar?'checked':''} onchange="colToggle('${c.key}')"> ${COLDEF[c.key].l}</label>
    </div>`).join('');
}
function colMove(i,d){const j=i+d; if(j<0||j>=libcols.length)return; const t=libcols[i]; libcols[i]=libcols[j]; libcols[j]=t; saveCols(); colMenuMalen(); libMalen();}
function colToggle(key){const c=libcols.find(x=>x.key===key); if(c)c.sichtbar=!c.sichtbar; saveCols(); colMenuMalen(); libMalen();}

function bulkMalen(){
  const bulk=document.getElementById('libbulk'); if(!bulk)return;
  // Das ＋ neben der Playlist-Liste erscheint nur, wenn es etwas
  // hinzuzufuegen GIBT — sonst waere es ein Knopf ohne Aufgabe.
  const plus=document.getElementById('plplus');
  if(plus)plus.style.display=libAuswahl.size?'':'none';
  if(!libAuswahl.size){bulk.style.display='none'; bulk.innerHTML=''; return;}
  bulk.style.display='';
  // Build 143 (JB, JEDEN Knopf einzeln durchgegangen): Abspielen -> Ziehen in
  // den Player; Tags/Metadaten -> passiert automatisch, Einzelfaelle per
  // Rechtsklick; Archivieren/Aus Archiv/Loeschen -> Rechtsklick kann es
  // besser; Aufheben -> Klick ins Leere. Damit blieb kein einziger Knopf
  // uebrig, der seine Zeile wert waere. JB: „Die simplen Dinge sind oft die
  // schoensten." Es bleibt die reine Anzeige, WIE VIELE markiert sind.
  bulk.innerHTML=`<b>${libAuswahl.size} ausgewählt</b>`+
    `<span class="muted2" style="font-size:11.5px">· ziehen = in den Player oder auf „Playlist:" · Rechtsklick = alles Weitere · Klick ins Leere hebt auf</span>`;
}
function libMalen(){
  fuelleSortSelect();
  document.getElementById('libselbtn').classList.toggle('an',libSelectMode);
  bulkMalen();
  const el=document.getElementById('libinhalt'); if(!el)return;
  const arr=libGefiltert();
  if(!arr.length){
    // Build 118 (JB: „Warum ist Suchen nicht automatisch Text? Wenn man nichts
    // findet, könnte es doch automatisch kommen"): steht ein Suchwort im Feld
    // und die Bibliothek gibt nichts her, wird OHNE Zutun im gesprochenen Text
    // weitergesucht — das Ergebnis erscheint direkt hier darunter.
    const q=(document.getElementById('libsuche').value||'').trim();
    if(q.length>1&&!libPlaylistView&&!libArchiv){
      el.innerHTML='<div class="libleer">Nichts im Titel gefunden — ich schaue im gesprochenen Text …</div>';
      clearTimeout(window._volltextTimer);
      window._volltextTimer=setTimeout(async()=>{                 // erst wenn das Tippen ruht
        if(((document.getElementById('libsuche')||{}).value||'').trim()!==q)return;
        try{
          const r=await fetch('/api/transkript_suche?q='+encodeURIComponent(q));
          const d=await r.json(); const tr=d.items||d||[];
          const box=document.getElementById('libinhalt'); if(!box)return;
          box.innerHTML=tr.length
            ?'<div class="libleer">Im Titel nichts — aber '+tr.length+' Titel sagen/singen „'+esc(q)+'":</div>'+
             '<div style="padding:0 10px 10px">'+tr.slice(0,25).map(x=>
               '<div class="mbtn" style="text-align:left" onclick="transkriptSuche()">🔎 '+esc(x.titel||'')+
               ' <span style="color:#8a7d74">('+((x.treffer||[]).length)+'×'+
               (x.quelle?' · '+esc(x.quelle):'')+')</span></div>').join('')+'</div>'
            :'<div class="libleer">Nichts gefunden — weder im Titel noch im gesprochenen Text.</div>';
        }catch(e){}
      },600);
      return;
    }
    el.innerHTML='<div class="libleer">'+(libPlaylistView?'Diese Playlist ist noch leer — füge mit ＋ Titel hinzu.':libArchiv?'Archiv ist leer.':'Nichts gefunden — lade etwas herunter oder ändere den Filter.')+'</div>'; return;}
  el.innerHTML = libModus==='kachel' ? kacheln(arr) : libModus==='alben' ? albenHTML(arr) : listeTab(arr);
  // Build 135: Rahmen-Auswahl aufziehen. Der Zuhörer sitzt am Behälter, nicht
  // an den Kacheln — er soll ja gerade auf FREIER Fläche anspringen.
  el.onpointerdown=libBandStart;
  // Build 143 (JB: „ich kann immer noch kein Fenster ziehen von einer Reihe
  // ueber der Bibliothek, das ist frustrierend"). Gemessen: ueber der ersten
  // Kachelreihe liegt gar nicht mehr libinhalt, sondern die KARTE — dort kam
  // der Zuhoerer nie an. Jetzt hoert die ganze Bibliotheks-Karte mit;
  // Bedienelemente filtert libBandStart ohnehin heraus.
  const karte=el.closest('.card'); if(karte)karte.onpointerdown=libBandStart;
  /* Build 144e (JB mit Bild, dieselbe Regel wie in der Playlist): „solange es
     in dem fenster ist, ist ein feld ziehen gewaehrleistet." Auch hier endet
     die Karte am Inhalt — bei der auf einen Treffer gefilterten Bibliothek
     gemessen 105 px Schwarz darunter, ohne Zuhoerer. Das Fenster ist der
     `panel-body`. */
  const koerper=el.closest('.panel-body'); if(koerper)koerper.onpointerdown=libBandStart;
}

/* ---- Alben-Ansicht: nach Künstler/Album gruppiert (Felder aus dem Auto-Tagging) ---- */
let _albGruppen=[];
function albPlay(i){const g=_albGruppen[i]; if(g)playerPlay(g.filter(x=>x.vorhanden).map(x=>x.id),0);}
function albenHTML(arr){
  const gr=new Map(); const rest=[];
  arr.forEach(x=>{
    if(x.album){const k=(x.kuenstler||x.uploader||'?')+'|||'+x.album;
      if(!gr.has(k))gr.set(k,[]); gr.get(k).push(x);}
    else rest.push(x);
  });
  _albGruppen=[];
  let h='';
  [...gr.entries()].sort((a,b)=>a[0].localeCompare(b[0])).forEach(([k,g])=>{
    const i=_albGruppen.push(g)-1, teile=k.split('|||');
    h+=`<div class="albgrp"><div class="albkopf">`+
      `<button class="ib play" onclick="albPlay(${i})" title="Album abspielen">▶</button>`+
      `<span class="albtitel">${esc(teile[1])}</span><span class="albku">${esc(teile[0])}</span>`+
      `<span class="albn">${g.length} Titel${g[0].jahr?' · '+esc(g[0].jahr):''}</span></div>`+kacheln(g)+`</div>`;
  });
  if(rest.length)
    h+=`<div class="albgrp"><div class="albkopf"><span class="albtitel" style="color:#8a7d74">Ohne Album-Info</span>`+
      `<span class="albn">${rest.length} Titel — Tags holen: ⚙ Ansicht → 🏷 Auto-Tagging</span></div>`+kacheln(rest)+`</div>`;
  return h||'<div class="libleer">Nichts gefunden.</div>';
}

/* Auto-Tagging anstoßen (alles ohne Album bzw. die aktuelle Auswahl) */
async function autotagAlle(){
  if(!confirm('Auto-Tagging: Musik ohne Album-Info bei MusicBrainz nachschlagen und\\nKünstler / Titel / Album eintragen (auch in die MP3-Dateien).\\n\\nLäuft im Hintergrund, ca. 1 Titel pro Sekunde. Starten?'))return;
  await fetch('/api/autotag',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
}
async function bulkAutotag(){
  const keys=[...libAuswahl]; if(!keys.length)return;
  await fetch('/api/autotag',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({keys})});
  libAuswahl.clear(); libMalen();
}
// Symbol für die Art des Titels: 🎵 Musik/MP3, 🎬 hochauflösend, 🎥 normales Video.
function katIcon(x){
  const audio=(x.kategorie==='MP3')||(!x.vcodec&&x.acodec);
  if(audio)return '🎵';
  if((x.hoehe||0)>=2160||x.kategorie==='4K+')return '🎬';
  return '🎥';
}
// Schlanke Info-Zeile im Spotify-Stil: Symbol · Dauer · Größe · Kanal.
function kachelInfo(x){
  const teile=[];
  if(x.dauer)teile.push(zeit(x.dauer));
  teile.push(mb(x.groesse));
  const wer=x.kuenstler||x.uploader;                   // getaggter Künstler schlägt den Kanalnamen
  if(wer)teile.push(esc(wer));
  return katIcon(x)+' '+teile.join(' · ');
}
// Wenige, ruhige Icon-Knöpfe. Alles Weitere steckt im „⋯"-Menü (aufgeräumt).
/* ❤ Lieblingssongs (JB 05.08.: „zu den lieblingssongs sollte ein herz sein") */
function herzKnopf(x){
  return `<button class="ib herz${x.herz?' an':''}" onclick="event.stopPropagation();herzToggle('${x.id}')" `+
    `title="${x.herz?'❤ Lieblingssong — Herz entfernen':'Als Lieblingssong markieren'}">${x.herz?'♥':'♡'}</button>`;
}
async function herzToggle(id){
  const x=libFind(id); if(!x)return;
  x.herz=!x.herz;                                      // sofort sichtbar, Server zieht nach
  try{fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id, art:'herz'})}).catch(()=>{});}catch(e){}
  document.querySelectorAll('[data-tr="herz"]').forEach(b=>{
    if(aktKey()===id){b.textContent=x.herz?'♥':'♡'; b.classList.toggle('an',!!x.herz);}});
  libMalen();
}
function aktBtnsKachel(x){
  let b='';
  if(x.vorhanden){
    b+=`<button class="ib play" onclick="event.stopPropagation();playerPlay(['${x.id}'])" title="Abspielen">▶</button>`;
    b+=herzKnopf(x);
    b+=`<button class="ib" onclick="plAddMenu(event,'${x.id}')" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
    b+=`<button class="ib" onclick="event.stopPropagation();biblio('${x.id}','ordner')" title="Im Ordner zeigen">📁</button>`;
  }else{
    b+=`<button class="ib" onclick="event.stopPropagation();biblioNeuladen('${x.id}')" title="Fehlende Datei erneut laden">⬇</button>`;
    b+=`<button class="ib" onclick="plAddMenu(event,'${x.id}')" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
  }
  b+=`<button class="ib" onclick="libItemMenu(event,'${x.id}')" title="Mehr… (auch per Rechtsklick)">⋯</button>`;
  return b;
}
/* ---- Menü-Werkzeuge (Explorer-Stil) ---- */
function menuSchliesser(m){                            // Außenklick schließt Menü + offene Flyouts
  // Build 128 (JB-Fund: „das Fenster ging eben nicht weg, auch wenn ich
  // nichts angewählt habe"). Wurzel: diese Funktion nahm `m` entgegen und
  // benutzte es NIE — sie räumte hartkodiert nur `.itemmenu` weg. Wer sie
  // mit einer anderen Klasse aufrief (die Link-Rückfrage und der
  // Mengen-Regler sind `.panelmenu`), bekam stillschweigend gar kein
  // Schließen. Jetzt schließt sie das übergebene Menü mit — damit gilt sie
  // für JEDEN künftigen Aufrufer, egal welche Klasse er wählt.
  setTimeout(()=>{
    const zu=(e2)=>{
      const t=e2.target;
      const drin=t&&t.closest&&(t.closest('.itemmenu')||(m&&m.contains(t)));
      if(drin)return;                                 // Klick INS Menü: offen lassen
      // Toggle-Gedächtnis (JB 05.08.: „wenn ich es nochmal anklicke, dann
      // sollte es sich schließen"): dieses pointerdown räumt das Menü weg —
      // kommt gleich der click desselben Knopfs, darf der NICHT neu öffnen.
      _menuZuKnopf=(t&&t.closest)?t.closest('button'):null; _menuZuTs=Date.now();
      document.querySelectorAll('.itemmenu').forEach(x=>x.remove());
      if(m)m.remove();
      document.removeEventListener('pointerdown',zu,true);
      document.removeEventListener('keydown',esc,true);
    };
    // Esc schließt ebenfalls — dasselbe Bedürfnis („weg damit"), nur über
    // die Tastatur; sonst bliebe das Fenster bei reiner Tastaturbedienung.
    const esc=(e2)=>{ if(e2.key==='Escape')zu({target:document.body}); };
    document.addEventListener('pointerdown',zu,true);
    document.addEventListener('keydown',esc,true);
  },0);
}
let _menuZuKnopf=null, _menuZuTs=0;                    // s. menuSchliesser (Toggle)
function menuGeradeZu(knopf){
  // Wahr, wenn der Außenklick-Schließer das Menü soeben über GENAU diesen
  // Knopf weggeräumt hat — dann ist der laufende click das Zumachen.
  if(_menuZuKnopf&&knopf===_menuZuKnopf&&Date.now()-_menuZuTs<400){_menuZuKnopf=null; return true;}
  return false;
}
function aktionsMenu(ev,eintraege){                    // generisches Klick-Menü an einem Knopf
  ev.stopPropagation();
  if(menuGeradeZu(ev.currentTarget))return;            // 2. Klick = schließen (JB 05.08.)
  document.querySelectorAll('.itemmenu').forEach(m=>m.remove());
  const m=document.createElement('div'); m.className='itemmenu';
  m.innerHTML=eintraege.map((e,i)=>`<button data-i="${i}">${e[0]}</button>`).join('');
  document.body.appendChild(m);
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  m.querySelectorAll('button').forEach(b=>b.onclick=(e2)=>{e2.stopPropagation(); const f=eintraege[+b.dataset.i][1]; m.remove(); f();});
  menuSchliesser(m);
}
function ansichtToggle(ev){ if(ev)ev.stopPropagation();
  const m=document.getElementById('libansicht'); const zu=m.style.display==='none';
  m.style.display=zu?'block':'none';
  if(zu)menuAnBody(m, document.getElementById('libansichtbtn'));   // Build 125: frei am <body>
  if(zu){const s=(e2)=>{if(!m.contains(e2.target)&&e2.target.id!=='libansichtbtn'&&!e2.target.closest('#libcolmenu')){
      ansichtZu(); document.removeEventListener('pointerdown',s,true);}};
    setTimeout(()=>document.addEventListener('pointerdown',s,true),0);}
}
function ansichtZu(){const m=document.getElementById('libansicht'); if(m)m.style.display='none';}
function plWerkzeuge(ev){
  // Build 124 (JB): Was die schmale Leiste ausblendet, taucht HIER oben auf —
  // ausgeblendet heißt nie unerreichbar. Sichtbar in der Leiste? Dann nicht
  // doppelt anbieten.
  const versteckt=el=>{const e=document.querySelector(el);
    return !e||getComputedStyle(e).display==='none'||e.getBoundingClientRect().width<2;};
  const extra=[];
  if(versteckt('.plbar .btn[onclick*="mixeMenu"]'))extra.push(['🎛 Mixer…', mixeMenu]);
  aktionsMenu(ev,extra.concat([
  ['📻 Neues entdecken', entdeckerOeffnen],
  ['✎ Umbenennen', plRename],
  ['🗑 Löschen', plDelete],
  ['⇄ Sync einrichten…', plSyncConfig],
  ['⇄ Jetzt synchronisieren', ()=>plSyncNow()],
  ['⤓ Als .m3u exportieren', plExport],
  ['⤒ .m3u importieren…', ()=>document.getElementById('m3ufile').click()]]));}

/* ---- 📻 Neues entdecken (Build 99, JB): Radio-Mixe zu Titeln der gewählten
   Playlist, alles Bekannte gefiltert — nur NEUE Songs, mit Anhören + Laden.
   Fenster im Backkatalog-Stil, rechts unter der Download-Box angedockt. ---- */
async function entdeckerOeffnen(){
  // Build 106 (JB): ohne gewählte Playlist nimmt der Entdecker die GANZE
  // Bibliothek als Quelle (Seeds gewichtet nach dem, was du wirklich hörst).
  const sel=document.getElementById('plsel');
  const pid=sel&&sel.value; const pl=plState.find(p=>p.id===pid);
  entdeckerZu();
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='ent-flyout'; fly.tabIndex=-1;
  fly.innerHTML='<div class="abo-fly-titel">📻 Neues entdecken: '+esc(pl?(pl.name||''):'deine Bibliothek')+
    '<span class="spacer"></span><button class="ib" title="Neu würfeln (andere Zufalls-Titel als Radio-Start)" onclick="entdeckerLaden()">🔄</button>'+
    '<button class="ib" title="Schließen (Esc)" onclick="entdeckerZu()">✕</button></div>'+
    '<div id="ent-inhalt" class="abo-folgen"><div class="leer">📡 Radios zu deinen Titeln werden aufgelöst…</div></div>';
  document.body.appendChild(fly); nachVorn(fly);
  aboFlyoutPositionieren(fly,null);
  fly.addEventListener('keydown',e=>{if(e.key==='Escape'){entdeckerZu(); e.stopPropagation();}});
  setTimeout(()=>document.addEventListener('pointerdown',entdeckerAussen,true),0);
  fly.focus(); fly.dataset.pl=pl?pid:'';
  entdeckerLaden();
}
function entdeckerZu(){
  const f=document.getElementById('ent-flyout'); if(f)f.remove();
  document.removeEventListener('pointerdown',entdeckerAussen,true);
}
function entdeckerAussen(e){
  const f=document.getElementById('ent-flyout'); if(!f)return;
  if(f.contains(e.target)||e.target.closest('.itemmenu'))return;
  entdeckerZu();
}
async function entdeckerLaden(){
  const fly=document.getElementById('ent-flyout'); if(!fly)return;
  const box=document.getElementById('ent-inhalt');
  box.innerHTML='<div class="leer">📡 Radios zu deinen Titeln werden aufgelöst… (ein paar Sekunden)</div>';
  let d=null;
  try{const r=await fetch('/api/entdecken?pl='+encodeURIComponent(fly.dataset.pl)+'&seeds=3&je=25'); d=await r.json();}catch(e){}
  if(!d||!d.ok){box.innerHTML='<div class="leer">'+esc((d&&d.fehler)||'Entdecken fehlgeschlagen — später erneut.')+'</div>'; return;}
  if(!d.funde.length){box.innerHTML='<div class="leer">Nichts Neues gefunden — 🔄 würfelt andere Radio-Startpunkte.</div>'; return;}
  const q=document.getElementById('cmd-qual').value;
  const quelleText=d.quelle==='bibliothek'?' (Radio-Start gemischt: Meistgehört + neu Hinzugefügt + Zufall, je Künstler einer)':'';
  const zeilen=d.funde.map(f=>
    '<div class="abo-f" data-vid="'+f.id+'">'+
    (f.score>1?'<span class="abo-nr" title="Kam in '+f.score+' der '+d.seeds+' Radios vor — starkes Signal">'+f.score+'×</span>':'<span class="abo-nr"></span>')+
    '<span class="abo-ft">'+esc(f.titel)+(f.kanal?' <span style="opacity:.55">· '+esc(f.kanal)+'</span>':'')+'</span>'+
    (f.dauer?'<span class="abo-fd">'+zeit(f.dauer)+'</span>':'')+
    '<button class="ib" title="Auf YouTube anhören" onclick="window.open(\\'https://www.youtube.com/watch?v='+f.id+'\\',\\'_blank\\',\\'noreferrer\\')">▶</button>'+
    '<button class="ib" title="In die Warteschlange laden" onclick="entdeckerHolen(this,\\''+f.id+'\\')">⬇</button>'+
    '</div>').join('');
  box.innerHTML='<div class="abo-staffel" title="'+esc(quelleText.trim())+'">'+d.funde.length+' neue Titel aus '+d.seeds+' Radios — nichts davon ist in deiner Bibliothek.'+
    '<span class="spacer"></span>'+
    '<button class="btn mini" onclick="entdeckerDurchhoeren()" title="Alle Funde als temporäre YouTube-Playlist öffnen und am Stück durchhören (max. 50)">▶ Auf YouTube durchhören</button>'+
    '<button class="btn mini" onclick="entdeckerAlle()" title="Alle Funde laden — sie sammeln sich in der Playlist „✨ Entdeckt (Datum)"">⬇ Alle ('+d.funde.length+')</button></div>'+
    '<div class="abo-fliste">'+zeilen+'</div>';
  fly.dataset.qual=q;
}
function entdeckerPlName(){
  const d=new Date();
  return '✨ Entdeckt '+String(d.getDate()).padStart(2,'0')+'.'+String(d.getMonth()+1).padStart(2,'0')+'.';
}
function entdeckerDurchhoeren(){
  // Build 100 (JB): alle Funde als TEMPORAERE YouTube-Playlist am Stück hören —
  // der watch_videos-Trick baut daraus eine echte list=TL…-Playlist (max 50).
  const fly=document.getElementById('ent-flyout'); if(!fly)return;
  const vids=[...fly.querySelectorAll('.abo-f')].map(z=>z.dataset.vid).slice(0,50);
  if(!vids.length)return;
  window.open('https://www.youtube.com/watch_videos?video_ids='+vids.join(','),'_blank','noreferrer');
}
async function entdeckerHolen(btn,vid){
  const q=(document.getElementById('cmd-qual')||{}).value||'beste';
  await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({urls:'https://www.youtube.com/watch?v='+vid,qualitaet:q,ziel_playlist:entdeckerPlName()})});
  if(btn){btn.textContent='✓'; btn.disabled=true;}
  const z=btn&&btn.closest('.abo-f'); if(z)z.style.opacity=.45;
  laden();
}
async function entdeckerAlle(){
  const fly=document.getElementById('ent-flyout'); if(!fly)return;
  const zeilen=[...fly.querySelectorAll('.abo-f')];
  const vids=zeilen.map(z=>z.dataset.vid);
  if(!vids.length)return;
  const dsum=zeilen.reduce((s,z)=>{const t=z.querySelector('.abo-fd'); if(!t)return s;
    const teile=t.textContent.split(':').map(Number); return s+teile.reduce((a,b)=>a*60+b,0);},0);
  const gr=groesseSchaetzen(dsum,(document.getElementById('cmd-qual')||{}).value||'beste');
  if(!confirm(vids.length+' neue Titel laden? Sie sammeln sich in der Playlist „'+entdeckerPlName()+'".'+gr))return;
  const q=(document.getElementById('cmd-qual')||{}).value||'beste';
  await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({urls:vids.map(v=>'https://www.youtube.com/watch?v='+v).join('\\n'),qualitaet:q,ziel_playlist:entdeckerPlName()})});
  toast('📻 '+vids.length+' Titel eingereiht → „'+entdeckerPlName()+'"'); entdeckerZu(); laden();
  try{dlboxTab('queue');}catch(e){}
}
function mixeMenu(ev){
  const r=ev.currentTarget.getBoundingClientRect();    // Rect merken, der Knopf-Kontext geht im Menü verloren
  // Build 117 (JB): Radio lag doppelt (Kopfleiste UND Bibliotheks-Leiste).
  // Es ist eine Mix-Art wie die anderen ⇒ es gehört hierher; oben bleibt der
  // 📻-Knopf am Transport, hier ist der Weg über den Mixer.
  aktionsMenu(ev,[
    ['📻 Endlos-Radio', radioStart],
    ['★ Meistgespielt', playMostPlayed],
    ['🕘 Zuletzt gespielt', playLetzte],
    ['▶ Gefilterte abspielen', playGefilterte],
    ['✨ Smart-Playlists…', ()=>smartPopover({currentTarget:{getBoundingClientRect:()=>r}})]]);
}

/* „Zu Playlist" — Auswahl-Liste direkt am Titel (kein Dropdown-Vorwählen nötig) */
function plAddListe(m,key){
  // Ab 9 Playlists erscheint ein Suchfeld (tippen filtert die Liste live).
  const suche=plState.length>8
    ?'<input class="km-such" placeholder="Playlist suchen…" onclick="event.stopPropagation()" '+
     'oninput="const q=this.value.toLowerCase();this.parentNode.querySelectorAll(\\'button[data-pl]\\').forEach(b=>{if(b.dataset.pl!==\\'__neu\\')b.style.display=b.textContent.toLowerCase().includes(q)?\\'\\':\\'none\\'})">'
    :'';
  m.innerHTML='<div class="sm-titel">＋ Zu Playlist hinzufügen</div>'+suche+'<div class="km-sub">'+
    plState.map(p=>`<button data-pl="${p.id}">${esc(p.name)} <span style="color:#8a7d74">(${p.items.length})</span></button>`).join('')+
    '<button data-pl="__neu">＋ Neue Playlist…</button></div>';
  m.querySelectorAll('button').forEach(b=>b.onclick=async(e2)=>{
    e2.stopPropagation();
    let id=b.dataset.pl;
    if(id==='__neu'){
      const n=prompt('Name der neuen Playlist:'); if(!n||!n.trim()){m.remove();return;}
      await plApi({art:'create',name:n.trim()}); id=(plState[plState.length-1]||{}).id;
    }
    if(id){ await plApi({art:'add',id,key});
      const p=plState.find(x=>x.id===id), t=libFind(key);
      if(p)plInfo('„'+((t&&t.titel)||'').slice(0,22)+'" → '+p.name+' ✓'); }
    m.remove();
  });
}
function plAddMenu(ev,key){
  ev.stopPropagation();
  if(menuGeradeZu(ev.currentTarget))return;            // 2. Klick = zu (JB 05.08.)
  document.querySelectorAll('.itemmenu').forEach(x=>x.remove());
  const m=document.createElement('div'); m.className='itemmenu'; document.body.appendChild(m);
  plAddListe(m,key);
  popoverBei(m,(ev.currentTarget||ev.target).getBoundingClientRect());
  menuSchliesser(m);
}

// Kontext-/⋯-Menü am Titel (Explorer-Stil; Einträge mit 'bleib' tauschen nur den Inhalt).
function libItemMenu(ev,id){
  ev.stopPropagation();
  if(ev.currentTarget&&menuGeradeZu(ev.currentTarget))return;   // 2. Klick = zu
  document.querySelectorAll('.itemmenu').forEach(m=>m.remove());
  const x=libFind(id); if(!x)return;
  const eintraege=[];
  if(!x.vorhanden)eintraege.push(['⬇ Erneut herunterladen', ()=>biblioNeuladen(id)]);
  if(x.vorhanden)eintraege.push(['▶ Abspielen', ()=>playerPlay([id])]);
  if(x.vorhanden)eintraege.push(['⏭ Als Nächstes abspielen', ()=>queueAlsNaechstes(id)]);
  if(x.vorhanden)eintraege.push(['➕ Ans Ende der Warteschlange', ()=>queueAnsEnde(id)]);
  eintraege.push(['＋ Zu Playlist…', (m)=>plAddListe(m,id), 'bleib']);
  if(x.vorhanden)eintraege.push(['📁 Im Ordner zeigen', ()=>biblio(id,'ordner')]);
  if(x.url)eintraege.push(['↗ Auf YouTube öffnen', ()=>window.open(x.url,'_blank','noreferrer')]);
  if(x.vorhanden)eintraege.push(['✂ Ausschnitt schneiden…', ()=>clipDialog(id)]);
  // Build 144k (JB: „Rechtsklick auf den song = welcher der ausschnitte ist
  // der favorit?"): Die Ausschnitte dieses Songs wohnen HIER, nicht als
  // eigene Kacheln. ⭐ markiert den Favoriten; der zählt allein im Zufall.
  // Build 144o: hat die Gruppe Alternativen (Hauptsong + Clips)? Dann hier
  // wählen, welcher der Favorit ist — Hauptsong oder Ausschnitt.
  if(x.hat_geschwister){
    const clips=gruppeVon(id).filter(c=>c.clip).length;
    eintraege.push(['✂ Ausschnitte ('+clips+')', (m)=>gruppeListe(m,id), 'bleib']);
  }
  eintraege.push([x.archiviert?'↩ Aus dem Archiv holen':'🗄 Ins Archiv legen', ()=>biblio(id, x.archiviert?'entarchiv':'archiv')]);
  eintraege.push([x.blacklist?'✓ Für Meistgespielt zulassen':'🚫 Von Meistgespielt ausschließen', ()=>biblio(id, x.blacklist?'unblacklist':'blacklist')]);
  if(libPlaylistView)eintraege.push(['✖ Aus dieser Playlist entfernen', ()=>plRemove(id)]);
  // Etappe C (Spec Punkt 5): Wiedergabe-Regeln je Titel — ist der Titel Teil
  // einer Mehrfach-Auswahl, reist die GANZE Auswahl mit (Explorer-Muster,
  // dieselbe Regel wie beim Ziehen) = JBs „Eigenschaften setzen" in Masse.
  const wgKeys=(libAuswahl.has(id)&&libAuswahl.size>1)?[...libAuswahl]:[id];
  eintraege.push(['🎚 Wiedergabe…'+(wgKeys.length>1?' ('+wgKeys.length+' Titel)':''),
    ()=>wiedergabeDialog({keys:wgKeys}, wgKeys.length>1?wgKeys.length+' Titel':(x.titel||'Titel'))]);
  eintraege.push(['ℹ Eigenschaften…', ()=>eigenschaften(id)]);
  eintraege.push(['🗑 In den Papierkorb', ()=>delEinzeln(id)]);
  const m=document.createElement('div'); m.className='itemmenu';
  m.innerHTML=eintraege.map((e,i)=>`<button data-i="${i}">${e[0]}</button>`).join('');
  document.body.appendChild(m);
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  m.querySelectorAll('button').forEach(b=>b.onclick=(e2)=>{
    e2.stopPropagation(); const ent=eintraege[+b.dataset.i];
    if(ent[2]==='bleib'){ent[1](m); return;}          // Untermenü: Inhalt tauschen, offen bleiben
    ent[1](); m.remove();
  });
  menuSchliesser(m);
}
/* Build 144n (JB 25.07.): app-eigener Ja/Nein-Dialog. Das native confirm()
   lässt sich im Browser abschalten („diese Handlung unterbinden") — dann kam
   keine Rückfrage mehr und das Löschen ging ins Leere. Ein Modal auf dem
   `<body>` unterliegt dieser Sperre NICHT. */
function frageModal(text, jaLabel, onJa){
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML='<div class="modal-box" style="max-width:430px"><div class="modal-head"><b>Bitte bestätigen</b>'
    +'<button class="ib" title="Abbrechen" onclick="this.closest(\\'.modal\\').remove()">✕</button></div>'
    +'<div style="padding:16px;line-height:1.5">'+esc(text).replace(/\\n/g,'<br>')+'</div>'
    +'<div style="padding:0 16px 16px;display:flex;gap:8px;justify-content:flex-end">'
    +'<button class="btn mini" data-nein>Abbrechen</button>'
    +'<button class="btn mini" data-ja style="background:var(--akz);border-color:var(--akz);color:#1b1512">'+esc(jaLabel||'OK')+'</button>'
    +'</div></div></div>';
  ov.onclick=e=>{if(e.target===ov)ov.remove();};
  ov.querySelector('[data-nein]').onclick=()=>ov.remove();
  ov.querySelector('[data-ja]').onclick=()=>{ov.remove(); onJa&&onJa();};
  document.body.appendChild(ov);
  try{ov.querySelector('[data-ja]').focus();}catch(e){}
}
/* Build 144k (JB): die Ausschnitte eines Songs — sie teilen seine Video-Id.
   Der Favorit (⭐) zählt allein im Zufall; hier wählt man ihn, spielt einen
   Ausschnitt oder wirft ihn in den Papierkorb. */
function gruppeVon(id){                                 // alle Eintraege der Gruppe (Hauptsong + Clips)
  const x=libFind(id); const g=(x&&x.gruppe)||(id||'').split('|')[0];
  return libdaten.filter(c=>((c.gruppe)||(c.id||'').split('|')[0])===g);
}
function gruppeListe(m,id){
  // Hauptsong zuerst, dann Clips (neuste oben). Der ⭐ markiert den Favoriten —
  // die sichtbare, abgespielte Kachel. Der Hauptsong ist NICHT löschbar
  // (JB: „das hauptvideo bleibt jedoch immer erhalten").
  const alle=gruppeVon(id).slice().sort((a,b)=>{
    if(!a.clip&&b.clip)return -1; if(a.clip&&!b.clip)return 1; return (b.ts||0)-(a.ts||0);});
  const rows=alle.map(c=>{
    const fav=c.ist_favorit;
    const label=c.clip?esc(c.titel||'Ausschnitt'):('🎵 '+esc(c.titel||'Hauptsong'));
    return '<div class="clip-row" data-k="'+c.id+'">'
      +'<button class="clip-fav'+(fav?' an':'')+'" data-act="fav" title="'+(fav?'Ist der Favorit — wird angezeigt & abgespielt':'Als Favorit setzen (wird angezeigt & abgespielt)')+'">'+(fav?'⭐':'☆')+'</button>'
      +'<button class="clip-play" data-act="play" title="Abspielen">▶ '+label+(c.dauer?' <span class="clip-meta">'+zeit(c.dauer)+'</span>':'')+'</button>'
      +(c.clip?'<button class="clip-del" data-act="del" title="Ausschnitt in den Papierkorb">🗑</button>'
              :'<span class="clip-del clip-schutz" title="Der Hauptsong bleibt immer erhalten">🔒</span>')
      +'</div>';
  }).join('')||'<div class="km-leer">nichts</div>';
  m.innerHTML='<div class="sm-titel">⭐ Favorit — wird angezeigt & abgespielt</div><div class="km-sub clip-sub">'+rows+'</div>';
  m.querySelectorAll('.clip-row button[data-act]').forEach(b=>b.onclick=async(e2)=>{
    e2.stopPropagation();
    const row=b.closest('.clip-row'), k=row.dataset.k, act=b.dataset.act;
    if(act==='play'){playerPlay([k]); m.remove(); return;}
    if(act==='fav'){
      await fetch('/api/clip_favorit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:k})});
      await libLaden(); if(document.body.contains(m))gruppeListe(m,id); return;   // frisch neu malen
    }
    if(act==='del'){
      frageModal('Diesen Ausschnitt in den Papierkorb verschieben?\\nAus dem Windows-Papierkorb wiederherstellbar.', '🗑 In den Papierkorb', async()=>{
        await fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:k,art:'loeschen'})});
        await libLaden();
        if(document.body.contains(m)&&gruppeVon(id).length>1)gruppeListe(m,id); else m.remove();
        toast('🗑 Ausschnitt in den Papierkorb.');
      });
      return;
    }
  });
}
/* Playlist-Ansicht: Titel mit der Maus umsortieren (speichert die neue Reihenfolge) */
let plvVon=null;
function plvDragStart(e,key){plvVon=key; e.dataTransfer.effectAllowed='move';}
function plvDragOver(e){if(libPlaylistView){e.preventDefault(); e.dataTransfer.dropEffect='move';}}
async function plvDrop(e,key){
  e.preventDefault();
  if(!libPlaylistView||!plvVon||plvVon===key){plvVon=null;return;}
  const p=plState.find(x=>x.id===libPlaylistView); if(!p){plvVon=null;return;}
  const items=p.items.slice(), von=items.indexOf(plvVon), zu=items.indexOf(key);
  if(von<0||zu<0){plvVon=null;return;}
  items.splice(von,1); items.splice(zu,0,plvVon);
  plvVon=null;
  await plApi({art:'reorder',id:libPlaylistView,items});   // Backend speichert die Reihenfolge
  libMalen();
}
function dragAttrs(id){
  // Titel sind IMMER ziehbar (in die Player-Playlist, JB 13.07.); in der
  // Playlist-Ansicht zusätzlich als Umsortier-Ziel.
  const basis=` draggable="true" ondragstart="libDragStart(event,'${id}')"`;
  return basis+(libPlaylistView?` ondragover="plvDragOver(event)" ondrop="plvDrop(event,'${id}')"`:'');
}
function libDragStart(ev,id){
  try{ev.dataTransfer.setData('ytdl/key',id);}catch(e){}   // fürs Fallenlassen in der Player-Playlist
  ev.dataTransfer.effectAllowed='copyMove';
  ziehTooltip(ev,id);                                      // kleiner Text-Anfasser statt großem Bild (JB 21.07.)
  if(libPlaylistView)plvDragStart(ev,id);                  // Reihenfolge ziehen wie bisher
}
/* Drag-Ghost: nur der Titel als kleiner Tooltip mitgezogen — nicht das ganze
   Kachelbild (JB 21.07.: „nur der Text, nicht das Bild bewegt sich"). */
function ziehTooltip(ev,id){
  // Build 142 (JB): Bei mehreren Markierten zeigte der Anfasser nur den
  // Titel, den man zufällig gegriffen hatte — man sah nicht, dass acht
  // Stück mitreisen. Windows stapelt dafür die Symbole mit einem
  // Zähler-Abzeichen, macOS macht es genauso mit rotem Abzeichen;
  // gemeinsam ist beiden: die ANZAHL steht dran. Genau das hier auch.
  const mehrere=libAuswahl.has(id)&&libAuswahl.size>1;
  const x=libFind(id);
  const t=mehrere ? (libAuswahl.size+' ausgewählte Titel')
                  : (x?(x.titel||id):id);
  const g=document.createElement('div'); g.className='ziehghost'+(mehrere?' stapel':'');
  g.textContent=(mehrere?'🎵🎵 ':'🎵 ')+t;
  document.body.appendChild(g);
  try{ev.dataTransfer.setDragImage(g,12,12);}catch(e){}
  setTimeout(()=>g.remove(),0);                            // Browser hat das Bild bereits kopiert
}

/* Generischer Menü-Bauer: an Mausposition (clientX) oder an einem Knopf (currentTarget).
   Einträge mit drittem Element 'bleib' tauschen nur den Inhalt (Untermenü). */
/* Kontextmenü mit Windows-Ausklapp-Untermenüs (JB 13.07.): Einträge der Form
   [Label, fn] klicken normal; [Label, optionenOderFunktion, 'sub'] zeigen ▸
   und klappen bei Hover/Klick RECHTS DANEBEN ein Flyout aus (Haken = aktiv). */
function kontextMenuBauen(pos, eintraege){
  // ⋯-Knöpfe (kein Rechtsklick): 2. Klick schließt statt neu zu öffnen.
  if(pos.clientX===undefined&&pos.currentTarget&&menuGeradeZu(pos.currentTarget))return;
  document.querySelectorAll('.itemmenu').forEach(m=>m.remove());
  const m=document.createElement('div'); m.className='itemmenu';
  m.innerHTML=eintraege.map((e,i)=>e[2]==='sub'
    ?`<button data-i="${i}" class="km-hatsub">${e[0]}<span class="km-pfeil">▸</span></button>`
    :`<button data-i="${i}">${e[0]}</button>`).join('');
  document.body.appendChild(m);
  const r=(pos.clientX!==undefined)
    ?{left:pos.clientX,right:pos.clientX,top:pos.clientY,bottom:pos.clientY}
    :pos.currentTarget.getBoundingClientRect();
  popoverBei(m,r);
  let flyTimer=null;
  const flyZu=()=>document.querySelectorAll('.km-flyout').forEach(f=>f.remove());
  const flyAuf=(b,ent)=>{
    flyZu();
    const f=document.createElement('div'); f.className='itemmenu km-flyout';
    const opt=(typeof ent[1]==='function')?ent[1]():ent[1];   // Optionen erst beim Öffnen holen (frischer Zustand)
    kmFuellen(f, ent[0].replace(' ▸',''), opt, ()=>{flyZu(); m.remove();});
    document.body.appendChild(f);
    const br=b.getBoundingClientRect(), mr=m.getBoundingClientRect();
    let left=mr.right+2;                                      // rechts daneben; kein Platz -> links
    if(left+f.offsetWidth>window.innerWidth-8)left=Math.max(8, mr.left-f.offsetWidth-2);
    const top=Math.max(8, Math.min(br.top-4, window.innerHeight-f.offsetHeight-8));
    f.style.left=left+'px'; f.style.top=top+'px';
  };
  m.querySelectorAll('button').forEach(b=>{
    const ent=eintraege[+b.dataset.i];
    if(ent[2]==='sub'){
      b.onmouseenter=()=>{clearTimeout(flyTimer); flyTimer=setTimeout(()=>flyAuf(b,ent),150);};
      b.onmouseleave=()=>clearTimeout(flyTimer);
      b.onclick=(e2)=>{e2.stopPropagation(); flyAuf(b,ent);};
    }else{
      b.onmouseenter=()=>{clearTimeout(flyTimer); flyTimer=setTimeout(flyZu,300);};
      b.onmouseleave=()=>clearTimeout(flyTimer);
      b.onclick=(e2)=>{
        e2.stopPropagation();
        if(ent[2]==='bleib'){ent[1](m); return;}
        ent[1](); flyZu(); m.remove();
      };
    }
  });
  menuSchliesser(m);
  return m;
}

/* Füllt ein Menü-Element mit einer Auswahl-Liste: Haken = aktiv, ab 9 Einträgen
   erscheint ein Suchfeld (JB-Frage Playlists: kostet nichts, kommt nur bei Bedarf). */
function kmFuellen(f,titel,optionen,fertig){           // optionen: [Label, aktiv?, fn]
  const suche=optionen.length>8?'<input class="km-such" placeholder="Suchen…">':'';
  f.innerHTML='<div class="sm-titel">'+titel+'</div>'+suche+'<div class="km-sub">'+
    optionen.map((o,i)=>`<button data-i="${i}"><span class="km-check"${o[1]?'':' style="visibility:hidden"'}>✓</span>${esc(o[0])}</button>`).join('')+'</div>';
  const inp=f.querySelector('.km-such');
  if(inp){inp.onclick=(e)=>e.stopPropagation();
    inp.oninput=()=>{const q=inp.value.toLowerCase();
      f.querySelectorAll('.km-sub button').forEach(b=>{b.style.display=b.textContent.toLowerCase().includes(q)?'':'none';});};}
  f.querySelectorAll('.km-sub button').forEach(b=>b.onclick=(e2)=>{
    e2.stopPropagation(); optionen[+b.dataset.i][2](); fertig();});
}
function kmListe(m,titel,optionen){if(!m)return; kmFuellen(m,titel,optionen,()=>m.remove());}   // m fehlt = Toggle hat geschlossen

/* Rechtsklick im PLAYER: Menü für den laufenden Titel (pausiert nichts, startet nichts neu) */
function playerKontext(ev){
  ev.preventDefault(); ev.stopPropagation();
  const k=aktKey(); if(!k)return false;
  const x=libFind(k)||{};
  const el=document.getElementById('pl-el');
  const pos={clientX:ev.clientX, clientY:ev.clientY};   // fürs EQ-Popover an der Mausposition
  const eintraege=[];
  eintraege.push([(el&&!el.paused)?'⏸ Pause':'▶ Weiter / Pause', plTogglePlay]);
  eintraege.push(['⏮ Vorheriger Titel', playerPrev]);
  eintraege.push(['⏭ Nächster Titel', playerNext]);
  if(plGeraet==='vlc')eintraege.push(['↻ VLC neu verbinden', vlcNeustart]);
  // Untermenüs klappen wie in Windows RECHTS aus (Hover oder Klick), Haken = aktiv
  eintraege.push(['＋ Zu Playlist', ()=>plOptionen(k), 'sub']);
  eintraege.push(['🎶 Warteschlange', queueWerkzeugListe, 'sub']);
  eintraege.push(['📊 Visualizer', ()=>VIZMODES.map(v=>[v[2], v[0]===vizMode, ()=>{vizMode=v[0];
      try{localStorage.setItem('ytdl_viz',vizMode);}catch(e){} vizModeRender();}]), 'sub']);
  eintraege.push(['⚡ Geschwindigkeit ('+playSpeed+'×)', ()=>
    [0.5,0.75,1,1.25,1.5,2].map(s=>[s+'×', s===playSpeed, ()=>speedWaehlen(s)]), 'sub']);
  eintraege.push(['💬 Untertitel', ()=>{
    const opt=SUBMODES.map(sm=>[sm[2], sm[0]===subMode, ()=>subModusSetzen(sm[0])]);
    if(subSprachen.length>1)opt.push(['🌐 Sprache: '+(subLang||'?')+' → nächste', false, subSpracheWechsel]);
    if(subCues)opt.push(['あ→a Romaji: '+(subRomaji?'AN':'aus'), subRomaji, subRomajiToggle]);
    return opt;}, 'sub']);
  eintraege.push(['🎚 Equalizer…', ()=>eqPopover({currentTarget:{getBoundingClientRect:
    ()=>({left:pos.clientX,right:pos.clientX,top:pos.clientY,bottom:pos.clientY})}})]);
  if(x.vorhanden)eintraege.push(['✂ Ausschnitt schneiden…', ()=>clipDialog(k)]);
  if(x.vorhanden)eintraege.push(['📁 Im Ordner zeigen', ()=>biblio(k,'ordner')]);
  // Build 144i (JB 25.07.: „auf youtube öffnen mit rechtsklick geht nicht zum
  // moment wo man gerade ist"): playerYoutube() hängt &t=<Position>s an — genau
  // wie der Werkzeug-Knopf. Nur HIER, im Player-Rechtsklick, wo es eine
  // laufende Stelle gibt (in der Bibliothek gibt es keine).
  if(x.url)eintraege.push(['↗ Auf YouTube öffnen (an dieser Stelle)', playerYoutube]);
  eintraege.push(['⧉ In VLC / extern öffnen', playerExtern]);
  eintraege.push(['ℹ Eigenschaften…', ()=>eigenschaften(k)]);
  kontextMenuBauen(ev, eintraege);
  return false;
}

// Rechtsklick auf einen Titel = dasselbe Menü an der Mausposition (wie im Explorer)
function kachelKontext(ev,id){
  ev.preventDefault();
  libItemMenu({stopPropagation(){}, currentTarget:{getBoundingClientRect:
    ()=>({left:ev.clientX, right:ev.clientX, top:ev.clientY, bottom:ev.clientY})}}, id);
  return false;
}
function kachel(x){
  const dauer=x.dauer?`<span class="kdauer">${zeit(x.dauer)}</span>`:'';
  const weg=x.vorhanden?'':'<span class="wegbadge">verschoben</span>';
  // JB 05.08.: „die ganzen Lieder haben in der Bibliothek immer noch das
  // thumbnail von youtube als Bild. Warum nicht das Albumcover?" — Kacheln
  // zeigen das ECHTE Album-Cover (/api/cover), sobald eins getaggt ist;
  // scheitert der Abruf, fällt das Bild aufs Thumbnail zurück (Player-Muster).
  const kaputt="this.style.display='none';this.parentNode.classList.add('platzhalter')";
  const rueckfall=(x.cover_album&&x.thumb)
    ?`this.onerror=function(){${kaputt}};this.src='${esc(x.thumb)}'`
    :kaputt;
  const quelle=x.cover_album?`/api/cover?id=${encodeURIComponent(x.id)}`:(x.thumb?esc(x.thumb):'');
  const thumb=quelle?`<img class="thumb" src="${quelle}" loading="lazy" draggable="false" onerror="${rueckfall}">`:'';
  // Build 144o (JB): kleine ✂ oben rechts, wenn diese Kachel ein Ausschnitt ist
  // (der Hauptsong liegt dann im Rechtsklick) — damit man es auf einen Blick sieht.
  const schere=x.clip?'<span class="clip-schere" title="Ausschnitt — der Hauptsong liegt im Rechtsklick">✂</span>':'';
  const herz=x.herz?'<span class="herzbadge" title="❤ Lieblingssong">♥</span>':'';
  const sel=libAuswahl.has(x.id)?' sel':'';
  // Ausführliche Details nur noch als Tooltip auf der Info-Zeile (Kachel bleibt ruhig).
  const det=[COLDEF.kategorie.t(x),COLDEF.qualitaet.t(x),technikText(x),mb(x.groesse),
             x.dauer?zeit(x.dauer):'',x.uploader||'',ytdatum(x.upload_date)].filter(Boolean).join('  ·  ');
  return `<div class="kachel ${x.vorhanden?'':'weg'}${sel}" data-id="${x.id}" onclick="kachelClick(event,'${x.id}')" ondblclick="kachelDblClick(event,'${x.id}')" oncontextmenu="return kachelKontext(event,'${x.id}')"${dragAttrs(x.id)}>
    <div class="thumbwrap ${quelle?'':'platzhalter'}" onclick="thumbClick(event,'${x.id}')" title="Abspielen">${thumb}${dauer}${weg}${schere}${herz}</div>
    <div class="kbody">
      <div class="ktitel" title="${esc(x.titel)}">${esc(x.titel)}</div>
      <div class="kinfo" title="${esc(det)}">${kachelInfo(x)}</div>
      <div class="kakt">${aktBtnsKachel(x)}</div>
    </div>
  </div>`;
}
let libKompakt=false;
function libKompaktToggle(){libKompakt=!libKompakt;
  document.getElementById('vb-kompakt').classList.toggle('an',libKompakt); libMalen();}
function kacheln(arr){return '<div class="kacheln'+(libKompakt?' kompakt':'')+'">'+arr.map(kachel).join('')+'</div>';}
function aktBtnsListe(x){
  let b='<div class="lakt">';
  if(x.vorhanden){
    b+=`<button class="ib play" onclick="event.stopPropagation();playerPlay(['${x.id}'])" title="Abspielen">▶</button>`;
    b+=herzKnopf(x);
    b+=`<button class="ib" onclick="plAddMenu(event,'${x.id}')" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
    b+=`<button class="ib" onclick="event.stopPropagation();biblio('${x.id}','ordner')" title="Im Ordner zeigen">📁</button>`;
  }else{
    b+=`<button class="ib" onclick="event.stopPropagation();biblioNeuladen('${x.id}')" title="Erneut laden">⬇</button>`;
    b+=`<button class="ib" onclick="plAddMenu(event,'${x.id}')" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
  }
  b+=`<button class="ib" onclick="libItemMenu(event,'${x.id}')" title="Mehr…">⋯</button>`;
  return b+'</div>';
}
function listeTab(arr){
  const cols=sichtbareCols();
  const heads=`<th class="th-sort ${libsort.key==='titel'?'akt':''}" onclick="setSort('titel')">Titel${pfeil('titel')}</th>`+
    cols.map(k=>`<th class="th-sort ${libsort.key===k?'akt':''}" onclick="setSort('${k}')">${COLDEF[k].l}${pfeil(k)}</th>`).join('')+'<th></th>';
  const rows=arr.map(x=>{
    const th=x.thumb?`<img class="lthumb" src="${esc(x.thumb)}" loading="lazy" draggable="false" style="cursor:pointer" onclick="event.stopPropagation();thumbClick(event,'${x.id}')" onerror="this.style.visibility='hidden'">`:'<span class="lthumb"></span>';
    const tds=cols.map(k=>{
      if(k==='status')return `<td class="lstatus ${x.vorhanden?'ok':'weg2'}">${x.vorhanden?'vorhanden':'verschoben'}</td>`;
      return `<td class="num">${esc(String(COLDEF[k].t(x)))}</td>`;
    }).join('');
    const sel=libAuswahl.has(x.id)?' sel':'';
    return `<tr class="${x.vorhanden?'':'weg'}${sel}" data-id="${x.id}" onclick="kachelClick(event,'${x.id}')" ondblclick="kachelDblClick(event,'${x.id}')" oncontextmenu="return kachelKontext(event,'${x.id}')"${dragAttrs(x.id)}><td><div class="ltitel">${th}<span class="ltxt" title="${esc(x.titel)}">${esc(x.titel)}</span></div></td>${tds}<td class="num">${aktBtnsListe(x)}</td></tr>`;
  }).join('');
  return `<div class="libwrap"><table class="libtab${libKompakt?' kompakt':''}"><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

/* ================= Player ================= */
// plid (Build 144, JB Punkt 2): Kommt die Warteschlange aus einer GESPEICHERTEN
// Playlist, merkt sich der Player deren Id — vorher reiste nur der Anzeige-Name
// mit, und damit war gar nicht bekannt, wohin man zurueckspeichern koennte.
let playerState={queue:[],idx:-1,quelle:'',plid:''};
let playerLayout='horizontal';   // Standard: Video links, Playlist rechts (JB-Favorit)
// Dashboard-Embed (?embed=1): standardmäßig Video OBEN, Playlist UNTEN (JB 22.07.). Die
// GETEILTE localStorage-Preferenz bewusst NICHT lesen, damit die Standalone-Wahl nicht ins
// Embed leckt (und der Toggle unten schreibt im Embed auch nichts zurück).
const _plEmbed=(typeof location!=='undefined'&&location.search.indexOf('embed=1')>=0);
if(_plEmbed){playerLayout='vertikal';}
else{try{const v=localStorage.getItem('ytdl_player_layout'); if(v)playerLayout=v;}catch(e){}}
function playerLayoutSet(){
  const card=document.getElementById('pl-card');
  if(card)card.classList.toggle('pl-horizontal', playerLayout==='horizontal');
}
function playerLayoutToggle(){
  playerLayout=(playerLayout==='horizontal')?'vertikal':'horizontal';
  if(!_plEmbed){try{localStorage.setItem('ytdl_player_layout',playerLayout);}catch(e){}}  // Embed: nur für die Sitzung
  playerLayoutSet();
}
function libFind(k){return libdaten.find(x=>x.id===k);}
function playerPlay(keys,start,quelle,plid){
  if(!(libdaten||[]).length){                          // Bibliothek noch nicht geladen -> erst holen,
    libLaden().then(()=>playerPlay(keys,start,quelle,plid));// sonst filtert der Check ALLES raus und der
    return;                                            // Player bleibt schwarz (JB-Fund 14.07.)
  }
  keys=(keys||[]).filter(k=>{const x=libFind(k); return x&&x.vorhanden;});
  if(!keys.length){alert('Nichts Abspielbares — die Datei fehlt (verschoben/gelöscht).');return;}
  // Genau den LAUFENDEN Titel nochmal angeklickt -> nicht neu starten, sondern Pause/Play
  if(vlcAktiv() && keys.length===1 && keys[0]===aktKey()){ plTogglePlay(); return; }
  const el=document.getElementById('pl-el');
  if(el && keys.length===1 && keys[0]===aktKey()){ if(el.paused)el.play(); else el.pause(); return; }
  radioAktiv=false;                                  // manueller Start beendet den Radio-Stream
  playerState.queue=keys; playerState.idx=start||0;
  playerState.quelle=quelle||'Bibliothek';           // Name fürs Playlist-Fenster (JB 21.07.)
  playerState.plid=plid||'';                         // nur gesetzt bei einer GESPEICHERTEN Playlist
  ensurePlayer(); renderPlayerMedia();
}
function playGefilterte(){
  let ids=libGefiltert().filter(x=>x.vorhanden&&artPasst(x)).map(x=>x.id);
  if(playShuffle)mische(ids);
  playerPlay(ids,0);
}
function aktKey(){return playerState.queue[playerState.idx];}
function playerNext(){
  const n=queueIdxPassend(playerState.idx+1,1);        // Abspielart 🎶/🎬 zählt mit
  if(n>=0){playerState.idx=n; renderPlayerMedia();}
  // Nur EIN Titel in der Playlist (bzw. nichts Passendes mehr dahinter)?
  // ⏭ geht weiter durch die Bibliothek — wie das automatische Titelende.
  else if(playerState.queue.length<=1)naechstesAusBibliothek();
}
function playerPrev(){
  // Standard-Player-Verhalten (JB 05.08., wie Spotify/YT Music): läuft der
  // Titel schon (>3 s), springt ⏮ erst an den ANFANG; erst ein zweiter
  // Druck geht zum vorigen Titel. Deckt auch Wiederholen-eins ab.
  const el0=document.getElementById('pl-el');
  const pos=vlcAktiv()?vlcPosLetzte:(el0?el0.currentTime:0);
  if(pos>3){
    if(vlcAktiv()){vlcPosLetzte=0; vlcBefehl('seek',{wert:0});}
    else if(el0)el0.currentTime=0;
    return;
  }
  const n=queueIdxPassend(playerState.idx-1,-1);
  if(n>=0){playerState.idx=n; renderPlayerMedia();}
  // Symmetrisch zu playerNext (JB 14.07.: 'ich kann nur vor, nicht zurück, ohne Playlist'):
  // Einzeltitel / nichts Passendes davor -> ⏮ geht in der Bibliothek einen zurück.
  else if(playerState.queue.length<=1)vorherigesAusBibliothek();
}
/* Gegenstück zu naechstesAusBibliothek: der VORHERIGE Titel der aktuellen Ansicht
   (Suche/Filter/Sortierung zählen). Bei Zufall ein zufälliger; am Anfang stoppt es ehrlich. */
function vorherigesAusBibliothek(){
  const k=aktKey();
  const pool=libGefiltert().filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x));
  if(!pool.length)return;
  let pk=null;
  if(playShuffle){
    const kand=pool.filter(x=>x.id!==k);
    if(kand.length)pk=kand[Math.floor(Math.random()*kand.length)].id;
  }else{
    const i=pool.findIndex(x=>x.id===k);
    if(i>0)pk=pool[i-1].id;                         // der Vorherige in der Ansicht
    else if(i<0)pk=pool[pool.length-1].id;          // aktueller nicht in der Ansicht -> ans Ende
  }
  if(!pk)return;
  playerState.queue=[pk]; playerState.idx=0; playerState.quelle='Bibliothek';
  renderPlayerMedia();
}
function playerExtern(){const k=aktKey(); if(k)biblio(k,'extern');}
function playerYoutube(){
  // Build 93 (JB): YouTube genau DA oeffnen, wo der Player gerade steht (&t=…s);
  // unter 4 s bleibt der Link sauber ohne Zeitangabe. (Der Parameter steuert
  // NUR das Abspielen — ein Download ueber die App laedt immer das GANZE Video.)
  const x=libFind(aktKey()); if(!x||!x.url)return;
  const el=document.getElementById('pl-el');
  const s=el&&isFinite(el.currentTime)?Math.floor(el.currentTime):0;
  const url=s>3?x.url+(x.url.includes('?')?'&':'?')+'t='+s+'s':x.url;
  window.open(url,'_blank','noreferrer');
}
function playerLinkKopieren(){
  // Build 95 (JB): Link zum TEILEN — bewusst OHNE Zeitstempel (x.url ist die
  // gespeicherte saubere watch-URL; das t haengt nur playerYoutube beim Oeffnen an).
  const x=libFind(aktKey()); if(!x||!x.url){toast('Kein Titel im Player');return;}
  try{navigator.clipboard.writeText(x.url); toast('🔗 Link kopiert (ohne Zeitstempel)');}
  catch(e){prompt('Link zum Kopieren:',x.url);}
}

/* ---- Abspielgeschwindigkeit ---- */
let playSpeed=1; try{const v=parseFloat(localStorage.getItem('ytdl_speed')); if(v>=0.25&&v<=3)playSpeed=v;}catch(e){}
function speedAnwenden(){const el=document.getElementById('pl-el'); if(el)el.playbackRate=playSpeed;
  try{localStorage.setItem('ytdl_speed',playSpeed);}catch(e){}
  const b=document.getElementById('plb-speed'); if(b)b.textContent=playSpeed+'×';}

/* ---- Untertitel / Karaoke / Transkript (aus .vtt neben der Datei) ---- */
const SUBMODES=[['aus','💬','aus'],['zeilen','💬','Untertitel (eine Zeile)'],
  ['karaoke','🎤','Karaoke — Zeilen laufen zeitsynchron mit'],['transkript','📜','Transkript (Text, Klick springt)']];
let subMode='aus', subCues=null, subLang='', subIdx=-1;   // Standard AUS (keine .vtt-Flut; Karaoke-Knopf holt sie bei Bedarf)
let subSprachen=[], subLangWahl='', subRomaji=true;   // Romaji standardmäßig AN (Karaoke authentisch lesbar)
try{const v=localStorage.getItem('ytdl_submode'); if(SUBMODES.some(m=>m[0]===v))subMode=v;}catch(e){}
try{const v=localStorage.getItem('ytdl_subromaji'); if(v!==null)subRomaji=v==='1';}catch(e){}
function vttZeit(s){const p=s.split(':').map(parseFloat); return p.length===3?p[0]*3600+p[1]*60+p[2]:p[0]*60+p[1];}
function parseVTT(t){
  // WebVTT -> [{start, ende, text}]; Inline-Tags (<c>, <00:00:01.960>) raus,
  // rollende Dubletten der YouTube-Auto-Untertitel zusammenfassen.
  const cues=[];
  for(const block of (t||'').replace(/\\r/g,'').split(/\\n\\n+/)){
    const zeilen=block.split('\\n').filter(Boolean);
    const ti=zeilen.findIndex(z=>z.includes('-->'));
    if(ti<0)continue;
    const m=zeilen[ti].match(/([\\d:.]+)\\s*-->\\s*([\\d:.]+)/);
    if(!m)continue;
    const txt=zeilen.slice(ti+1).join(' ').replace(/<[^>]*>/g,'').replace(/\\s+/g,' ').trim();
    if(!txt)continue;
    const s=vttZeit(m[1]), e=vttZeit(m[2]);
    if(cues.length&&cues[cues.length-1].text===txt){cues[cues.length-1].ende=e; continue;}
    cues.push({start:s, ende:e, text:txt});
  }
  return cues;
}
function parseLRC(t){
  // LRCLIB-Format: [mm:ss.xx] Text (mehrere Zeitmarken je Zeile möglich).
  // -> [{start, ende, text}] wie parseVTT; ende = Beginn der nächsten Zeile.
  const roh=[];
  for(const zeile of (t||'').split(/\\r?\\n/)){
    const txt=zeile.replace(/\\[[^\\]]*\\]/g,'').trim();   // alle [..]-Marken (Zeit + Meta) raus
    let m; const re=/\\[(\\d+):(\\d+(?:\\.\\d+)?)\\]/g;
    while((m=re.exec(zeile))){roh.push({start:parseInt(m[1],10)*60+parseFloat(m[2]), text:txt});}
  }
  roh.sort((a,b)=>a.start-b.start);
  const cues=roh.filter(c=>c.text);                    // Leerzeilen als Marker droppen
  cues.forEach((c,i)=>c.ende=i+1<cues.length?cues[i+1].start:c.start+5);
  return cues;
}
async function subLaden(key){
  subCues=null; subLang=''; subIdx=-1; subAnzeigen();
  try{
    // 1) Musik-Karaoke: erst LRCLIB (echte, zeilengenaue Songtexte) — nur wenn
    //    Untertitel/Karaoke überhaupt an ist, spart Netz.
    if(subMode!=='aus'){
      try{
        const rl=await fetch('/api/lyrics?id='+encodeURIComponent(key));
        if(rl.ok){const dl=await rl.json();
          if(dl.lrc){const cl=parseLRC(dl.lrc); if(cl.length){subCues=cl; subLang='LRC';}}}
      }catch(e){}
    }
    // 2) Fallback: YouTube-Untertitel (auch für Sprachwahl/Romaji/Transkript)
    let u='/api/untertitel?id='+encodeURIComponent(key);
    if(subLangWahl)u+='&lang='+encodeURIComponent(subLangWahl);   // Wunsch; Server fällt sonst auf Beste zurück
    if(subRomaji)u+='&romaji=1';                                  // greift nur bei ja/…-orig
    const r=await fetch(u);
    if(r.ok){
      const d=await r.json();
      const c=parseVTT(d.vtt);
      if(c.length&&!subCues){subCues=c; subLang=d.lang||'';}      // LRCLIB hat Vorrang, wenn vorhanden
      subSprachen=d.sprachen||[];
    }else subSprachen=[];
  }catch(e){}
  // Standardmäßig da sein (JB 14.07.: „direkt Karaoke go"): fehlen Untertitel
  // beim Abspielen, IMMER still von YouTube vorladen (1× je Titel und Sitzung) —
  // der erste Karaoke-Klick trifft dann schon auf fertige Zeilen.
  if(!subCues&&subMode!=='aus')subNachladen();       // nur laden, wenn Untertitel/Karaoke wirklich an ist
  subAnzeigen();
}
function subSpracheWechsel(){                          // zyklisch durch alle .vtt-Sprachen des Titels
  if(subSprachen.length<2)return;
  const i=subSprachen.indexOf(subLang);
  subLangWahl=subSprachen[(i+1)%subSprachen.length];
  const k=aktKey(); if(k)subLaden(k);
}
function subSpracheSetzen(l){                          // direkte Wahl (Untertitel-Panel)
  subLangWahl=l; const k=aktKey(); if(k)subLaden(k);
}
/* Untertitel-Panel am 💬-Knopf (JB 05.08., Amazon/Netflix-Muster): ALLE
   Untertitel-Einstellungen direkt im Player — Modus, Sprache, Größe, Stil,
   Versatz. Gilt für Browser UND Gerät VLC; die Optionen-Zeile bleibt als
   Zweitweg, Taste S wechselt weiter schnell den Modus. */
function subMenu(ev){
  ev.stopPropagation();
  if(menuGeradeZu(ev.currentTarget))return;            // 2. Klick aufs 💬 = zu
  document.querySelectorAll('#subfly').forEach(x=>x.remove());
  const m=document.createElement('div'); m.className='panelmenu'; m.id='subfly';
  m.style.minWidth='280px';
  // Robust gegen fremde Schließer/Capture-Listener: eigene pointerdowns
  // verlassen das Panel nie (JB: „kann eh nichts anklicken").
  m.addEventListener('pointerdown',e=>e.stopPropagation());
  const fuellen=()=>{
    m.innerHTML='';
    // Live-VORSCHAU (Disney: „Subtitles will appear like this") — dieselben
    // CSS-Variablen wie die echte Anzeige, jede Wahl wirkt sofort sichtbar.
    // Feste Höhe (JB 05.08.: „das Fenster wird größer und kleiner") — die
    // Vorschau-Box bleibt gleich groß, der Text skaliert darin.
    const vs=document.createElement('div');
    vs.className='pl-subzeile';
    vs.style.cssText='position:static;display:flex;align-items:center;justify-content:center;'+
      'height:56px;overflow:hidden;padding:0 6px 6px;pointer-events:none';
    const vspan=document.createElement('span'); vspan.className='subtxt';
    vspan.textContent='So sehen Untertitel aus';
    vs.appendChild(vspan); subLookAuf(vs); m.appendChild(vs);
    const reihe=(name)=>{
      const z=document.createElement('div'); z.className='subm-zeile';
      const s=document.createElement('span'); s.textContent=name; z.appendChild(s);
      const w=document.createElement('span'); w.className='subm-knoepfe'; z.appendChild(w);
      m.appendChild(z); return w;};
    const kn=(wrap,label,aktiv,tun,stil,titel)=>{
      const b=document.createElement('button'); b.className='btn mini'+(aktiv?' an':'');
      b.textContent=label; if(stil)b.style.cssText=stil; if(titel)b.title=titel;
      b.addEventListener('click',e=>{e.stopPropagation();
        const idx=[...m.querySelectorAll('button')].indexOf(b);
        tun(); fuellen();
        const alle=[...m.querySelectorAll('button')];   // Fokus überlebt das Neu-Malen (Fernbedienung)
        (alle[Math.min(idx,alle.length-1)]||alle[0]).focus();});
      wrap.appendChild(b);};
    const punkt=(wrap,farbe,aktiv,tun,titel)=>kn(wrap,'',aktiv,tun,
      'width:18px;height:18px;border-radius:50%;padding:0;background:'+farbe+
      ';border:1px solid #777',titel);
    // Modus — OHNE Transkript (JB: lebt in den Optionen; Taste S kann alles)
    let w=reihe('Modus');
    [['aus','aus'],['zeilen','Untertitel'],['karaoke','Karaoke']]
      .forEach(md=>kn(w,md[1],subMode===md[0],()=>subModusSetzen(md[0])));
    // Sprache dedupliziert (xx-orig verdeckt xx)
    const sichtbar=subSprachen.filter(l=>!subSprachen.includes(l+'-orig'));
    if(sichtbar.length>1){
      w=reihe('Sprache');
      sichtbar.forEach(l=>kn(w,l,l===subLang||(l===subLang+'-orig'),()=>subSpracheSetzen(l)));
    }
    // Größe (gestaffelte Aa)
    w=reihe('Größe');
    [['0.8',10,'klein'],['1',13,'mittel'],['1.35',16,'groß'],['1.8',19,'riesig (TV)']]
      .forEach(g=>kn(w,'Aa',String(subStil.groesse)===g[0],
        ()=>subStilSetzen('groesse',g[0]),'font-size:'+g[1]+'px;padding:1px 7px',g[2]));
    // Schriftarten (Disney: „unterschiedliche Schriftzüge") — Aa im echten Font
    w=reihe('Schrift');
    Object.keys(SUB_SCHRIFTEN).forEach(s=>kn(w,'Aa',subStil.schrift===s,
      ()=>subStilSetzen('schrift',s),
      "font-family:"+SUB_SCHRIFTEN[s].replace(/"/g,"'")+';padding:1px 7px',s));
    // JB 05.08.: bei KARAOKE greifen Farbe/Deckkraft/Hintergrund nicht (die
    // Farben gehören dem Wischer) — diese Zeilen verschwinden dann, statt zu
    // enttäuschen; Größe/Schrift/Versatz wirken auch im Karaoke.
    const zyklus=(wrap,stufen,istAktiv,tun,titel)=>{
      const i=stufen.findIndex(s=>istAktiv(s[0]));
      const jetzt=stufen[Math.max(0,i)];
      kn(wrap,jetzt[1],false,()=>tun(stufen[(Math.max(0,i)+1)%stufen.length][0]),
         'min-width:44px',titel+' — Klick wechselt zur nächsten Stufe');};
    if(subMode!=='karaoke'){
      w=reihe('Farbe');
      ['#ffffff','#111111','#3b6df0','#38d1c8','#59c93c','#ffe94a','#e04343','#c94fc9']
        .forEach(f=>punkt(w,f,subStil.farbe===f,()=>subStilSetzen('farbe',f),f));
      // Kompakt (JB: „zu viel Text in der Zeile"): Deckkraft-Stufen als EIN
      // Zyklus-Knopf statt Knopfreihe.
      w=reihe('Deckkraft');
      zyklus(w,[[1,'100%'],[0.75,'75%'],[0.5,'50%']],v=>subStil.deckkraft===v,
             v=>subStilSetzen('deckkraft',v),'Text-Deckkraft');
      kn(w,'Schatten',subStil.schatten,()=>subStilSetzen('schatten',!subStil.schatten),
         'margin-left:8px','Schlagschatten hinter der Schrift');
      w=reihe('Hintergrund');
      punkt(w,'#000',subStil.hg==='schwarz',()=>subStilSetzen('hg','schwarz'),'schwarz');
      punkt(w,'#fff',subStil.hg==='weiss',()=>subStilSetzen('hg','weiss'),'weiß');
      zyklus(w,[[0.7,'70%'],[1,'100%'],[0,'aus'],[0.25,'25%'],[0.5,'50%']],
             v=>subStil.hg_deckkraft===v,v=>subStilSetzen('hg_deckkraft',v),
             'Hintergrund-Deckkraft (aus = nur Schrift)');
    }
    // Versatz kompakt: ‹ Wert › + Schrittweiten-Knopf (0,1/0,5/1/5)
    w=reihe('Versatz');
    const st=String(subSchritt).replace('.',',');
    kn(w,'‹',false,()=>subOffsetSchieben(-subSchritt),'padding:2px 11px',
       'Text kommt '+st+' s später');
    const anz=document.createElement('b');
    anz.style.cssText='min-width:46px;text-align:center;color:var(--akz2)';
    anz.textContent=(subOffset>0?'+':'')+subOffset.toFixed(1).replace('.',',')+' s';
    w.appendChild(anz);
    kn(w,'›',false,()=>subOffsetSchieben(subSchritt),'padding:2px 11px',
       'Text kommt '+st+' s früher — je Titel gemerkt');
    kn(w,'± '+st,false,()=>{
      const stufen=[0.1,0.5,1,5];
      subSchritt=stufen[(stufen.indexOf(subSchritt)+1)%stufen.length];
    },'padding:2px 7px;opacity:.8','Schrittweite wechseln: 0,1 → 0,5 → 1 → 5 s');
    // Reset — dezent unten (Disney-Muster)
    const rz=document.createElement('div');
    rz.style.cssText='text-align:center;padding:9px 0 3px';
    const rb=document.createElement('button'); rb.className='btn mini';
    rb.style.opacity='.7'; rb.textContent='Zurücksetzen';
    rb.title='Alle Untertitel-Darstellungs-Optionen auf den Standard';
    rb.addEventListener('click',e=>{e.stopPropagation(); subStilReset(); fuellen();});
    rz.appendChild(rb); m.appendChild(rz);
  };
  fuellen();
  // Fernbedienung/Tastatur (JB: „für eine Fernbedienung kompatibel"):
  // Pfeile bewegen den Fokus durch die Knöpfe, Enter wählt, Esc schließt.
  m.addEventListener('keydown',e=>{
    const alle=[...m.querySelectorAll('button')];
    const i=alle.indexOf(document.activeElement);
    if(e.key==='ArrowRight'||e.key==='ArrowDown'){
      e.preventDefault(); e.stopPropagation(); (alle[i+1]||alle[0]).focus();}
    else if(e.key==='ArrowLeft'||e.key==='ArrowUp'){
      e.preventDefault(); e.stopPropagation(); (alle[i-1]||alle[alle.length-1]).focus();}
  });
  document.body.appendChild(m);
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  setTimeout(()=>{const b1=m.querySelector('button'); if(b1)b1.focus();},0);
  menuSchliesser(m);
}
function subRomajiToggle(){
  subRomaji=!subRomaji;
  try{localStorage.setItem('ytdl_subromaji',subRomaji?'1':'0');}catch(e){}
  const k=aktKey(); if(k)subLaden(k);
}
let subLaedt=false;                                    // läuft gerade ein Untertitel-Download?
/* Untertitel-Look (JB 05.08., Disney-Muster: „alle Optionen, unterschiedliche
   Schriftzüge"): Größe, Schriftart, Textfarbe+Deckkraft, Schatten,
   Hintergrund+Deckkraft — gemerkt je Browser UND Server-global (versionsfest).
   Die alten 4 Presets werden beim Laden in Look-Felder übersetzt. */
const SUB_STANDARD={groesse:1, schrift:'standard', farbe:'#ffffff', deckkraft:1,
                    schatten:false, hg:'schwarz', hg_deckkraft:0.7};
const SUB_SCHRIFTEN={standard:'system-ui,"Segoe UI",sans-serif', serif:'Georgia,"Times New Roman",serif',
                     mono:'Consolas,"Courier New",monospace', casual:'"Comic Sans MS","Segoe Print",cursive',
                     kursiv:'"Segoe Script","Brush Script MT",cursive', breit:'"Arial Black","Segoe UI",sans-serif'};
let subStil=Object.assign({},SUB_STANDARD);
function subPresetZuLook(p){
  return {dunkel:{}, hell:{farbe:'#111111',hg:'weiss',hg_deckkraft:0.9},
          gelb:{farbe:'#ffe94a',hg_deckkraft:0.78},
          kontur:{schatten:true,hg_deckkraft:0}}[p]||{};
}
try{const v=JSON.parse(localStorage.getItem('ytdl_substil')||'{}')||{};
  if(v.preset)Object.assign(subStil, subPresetZuLook(v.preset));   // Alt-Migration
  for(const f in SUB_STANDARD)if(v[f]!==undefined)subStil[f]=v[f];
  subStil.groesse=parseFloat(subStil.groesse)||1;}catch(e){}
function _hexRgba(hex,a){
  const n=parseInt((hex||'#ffffff').slice(1),16);
  return 'rgba('+((n>>16)&255)+','+((n>>8)&255)+','+(n&255)+','+a+')';
}
function subStilAnwenden(){
  const ov=document.getElementById('pl-sub-anzeige'); if(!ov)return;
  subLookAuf(ov);
}
function subLookAuf(el){                               // Look als CSS-Variablen (auch Vorschau)
  el.style.setProperty('--sub-skala', subStil.groesse);
  el.style.setProperty('--sub-farbe', _hexRgba(subStil.farbe, subStil.deckkraft));
  el.style.setProperty('--sub-hg', subStil.hg_deckkraft<=0?'transparent'
    :(subStil.hg==='weiss'?'rgba(255,255,255,'+subStil.hg_deckkraft+')'
                          :'rgba(0,0,0,'+subStil.hg_deckkraft+')'));
  el.style.setProperty('--sub-schrift', SUB_SCHRIFTEN[subStil.schrift]||SUB_SCHRIFTEN.standard);
  el.style.setProperty('--sub-schatten', subStil.schatten
    ?'0 0 5px #000,0 2px 3px #000,-1px -1px 2px #000,1px -1px 2px #000':'none');
}
function subStilSetzen(feld,wert){
  if(feld==='groesse'||feld==='deckkraft'||feld==='hg_deckkraft')wert=parseFloat(wert)||0;
  if(feld==='groesse'&&!wert)wert=1;
  if(feld==='schatten')wert=!!wert;
  subStil[feld]=wert;
  try{localStorage.setItem('ytdl_substil',JSON.stringify(subStil));}catch(e){}
  // Server-global (JB: gilt für alle Videos, überlebt jede Version).
  fetch('/api/wiedergabe',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({global:1,merge:1,sub_look:subStil})}).catch(()=>{});
  subStilAnwenden();
}
function subStilReset(){
  subStil=Object.assign({},SUB_STANDARD);
  try{localStorage.setItem('ytdl_substil',JSON.stringify(subStil));}catch(e){}
  fetch('/api/wiedergabe',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({global:1,merge:1,sub_look:''})}).catch(()=>{});
  subStilAnwenden();
}
/* Beim Seitenstart gewinnt der SERVER-Stand (überlebt Versionen/Browser);
   localStorage bleibt der schnelle Zwischenspeicher. */
let _subStilServer=false;
function subStilVomServer(){
  if(_subStilServer||!daten||!daten.config)return;
  _subStilServer=true;
  const g=(daten.config.wiedergabe)||{};
  if(g.sub_look&&typeof g.sub_look==='object'){       // neuer Look gewinnt
    for(const f in SUB_STANDARD)if(g.sub_look[f]!==undefined)subStil[f]=g.sub_look[f];
    subStil.groesse=parseFloat(subStil.groesse)||1;
  }else{                                              // Alt-Felder migrieren
    if(g.sub_groesse)subStil.groesse=parseFloat(g.sub_groesse)||subStil.groesse;
    if(g.sub_stil)Object.assign(subStil, subPresetZuLook(g.sub_stil));
  }
  subStilAnwenden();
}
function subStilInit(){
  const md=document.getElementById('opt_submode'); if(md)md.value=subMode;
}
function subAnzeigen(){
  subStilAnwenden();                                   // Stil folgt jedem Neuaufbau des Elements
  const m=SUBMODES.find(x=>x[0]===subMode)||SUBMODES[0];
  const b=document.getElementById('plb-sub');           // Knopf in der Leiste auf dem Video
  if(b){b.textContent=m[1];
    b.title='Untertitel: '+m[2]+(subCues?(' · '+(subLang||'?')):' — werden bei Bedarf automatisch geladen')+' (klicken zum Wechseln)';
    b.classList.toggle('an',subMode!=='aus'&&!!subCues);}
  const ov=document.getElementById('pl-sub-anzeige');
  if(ov){ov.className='pl-subzeile'+(subMode==='karaoke'?' karaoke':'');
    // Sichtbares Feedback (JB 21.07.): beim Laden „⏳", damit nicht „nichts passiert" wirkt.
    const warte=subLaedt&&!subCues&&(subMode==='zeilen'||subMode==='karaoke');
    ov.style.display=((subCues||warte)&&(subMode==='zeilen'||subMode==='karaoke'))?'':'none';
    ov.innerHTML=warte?'<span class="subtxt" style="opacity:.7">⏳ Untertitel werden geladen …</span>':'';}
  const ly=document.getElementById('pl-lyrics');
  if(ly){
    if(subCues&&subMode==='transkript'){
      ly.style.display='';
      ly.innerHTML='<div class="kap-titel">📜 Transkript'+(subLang?' · '+subLang:'')+'</div>'+
        subCues.map((c,i)=>`<div class="lyr" data-i="${i}" onclick="kapSpring(${c.start})"><span class="kap-z">${zeit(c.start)}</span>${esc(c.text)}</div>`).join('');
    }else{ly.style.display='none'; ly.innerHTML='';}
  }
  subIdx=-1;
}
function subModusSetzen(mode){
  subMode=mode;
  if(typeof subModeSitzung!=='undefined')subModeSitzung=mode;   // Sitzungs-Standard mitziehen
  try{localStorage.setItem('ytdl_submode',subMode);}catch(e){}
  // Blink-Wurzel 2 + JB 05.08. („wenn ich die einmal an habe, dann sind die
  // für alle an"): der Umschalter gilt GLOBAL — früher schrieb er eine
  // Absolut-Regel je Titel, und Titel mit alter „aus"-Regel schalteten die
  // Untertitel wieder ab. Ausnahmen je Titel/Playlist setzt weiter der
  // Rechtsklick-Dialog „Wiedergabe…" (bewusst, nicht als Nebenwirkung).
  fetch('/api/wiedergabe',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({global:1,merge:1,sub:mode})}).catch(()=>{});
  if(typeof daten!=='undefined'&&daten&&daten.config)  // sofort wirksam, ohne Poll
    daten.config.wiedergabe=Object.assign({},daten.config.wiedergabe||{},{sub:mode});
  if(subMode!=='aus'&&!subCues)subNachladen();         // fehlen welche -> still holen, KEIN Popup
  subAnzeigen();
  const el=document.getElementById('pl-el');           // Wischer sofort mitnehmen (Build 115)
  if(subMode==='karaoke'&&el&&!el.paused)karLauf(el);
}
function subCycle(){
  const i=SUBMODES.findIndex(x=>x[0]===subMode);
  subModusSetzen(SUBMODES[(i+1)%SUBMODES.length][0]);
}
/* Untertitel fehlen auf der Platte -> automatisch im Hintergrund von YouTube
   nachladen (JB 13.07.: „Ich will keine Fenster aufploppen sehen"). Je Titel
   nur einmal pro Sitzung versucht; das Ergebnis holt subLaden zeitversetzt ab. */
let subAutoVersucht=new Set();
async function subNachladen(){
  const k=aktKey(); if(!k||subAutoVersucht.has(k))return;
  subAutoVersucht.add(k);
  subLaedt=true; subAnzeigen();                         // sofort „⏳ …" zeigen (JB 21.07.)
  try{await fetch('/api/untertitel_laden',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:k})});}catch(e){}
  // Statt starrer Zeitpunkte: nachfragen, BIS die .vtt da ist (max ~40 s) und dann anzeigen.
  for(let i=0;i<20;i++){
    await new Promise(r=>setTimeout(r,2000));
    if(aktKey()!==k){subLaedt=false; return;}          // Titel gewechselt -> abbrechen
    try{
      const r=await fetch('/api/untertitel?id='+encodeURIComponent(k));
      if(r.ok){const d=await r.json(); const c=parseVTT(d.vtt);
        if(c.length){subCues=c; subLang=d.lang||''; subSprachen=d.sprachen||[];
          subLaedt=false; subAnzeigen(); return;}}
    }catch(e){}
  }
  subLaedt=false;                                        // nichts gefunden -> ehrlich melden
  subAutoVersucht.delete(k);                             // erneuter Versuch später erlaubt
  if(aktKey()===k){subAnzeigen();
    if(subMode!=='aus')toast('Für diesen Titel sind keine Untertitel verfügbar.');}
}
function karWorte(text){                                // Zeile in Wort-Spans zerlegen (fürs Mitleuchten)
  return (text||'').split(/(\\s+)/).map(w=>/\\S/.test(w)?'<span class="kw">'+esc(w)+'</span>':esc(w)).join('');
}
let karRAF=0;
function karLauf(el){
  // Build 115: der Wischer braucht den Bildtakt — 'timeupdate' feuert nur
  // ~4x/s (sichtbares Stufen). Läuft NUR während Karaoke-Wiedergabe und
  // stellt sich bei Pause/Moduswechsel selbst ab (Last-Budget).
  if(!window.requestAnimationFrame)return;
  cancelAnimationFrame(karRAF);
  const schritt=()=>{
    if(!el||el.paused||subMode!=='karaoke'){karRAF=0; return;}
    subTick(el);
    karRAF=requestAnimationFrame(schritt);
  };
  karRAF=requestAnimationFrame(schritt);
}
/* Untertitel-/Karaoke-Versatz (JB 05.08., House-of-the-Rising-Sun-Fall:
   „der karaoke text ist nicht exakt"): ±0,5-s-Schritte über , und . —
   je Titel ABSOLUT gemerkt (Wiedergabe-Regel sub_offset, Etappe-C-Speicher).
   Positiv = Text kommt früher, negativ = später. */
let subOffset=0, subSchritt=0.5;                       // Schrittweite fürs Versatz-Panel
function subOffsetSchieben(d){
  subOffset=Math.max(-30,Math.min(30,Math.round((subOffset+d)*10)/10));
  toast('💬 Untertitel-Versatz '+(subOffset>0?'+':'')+subOffset.toFixed(1).replace('.',',')+' s'+
        (subOffset===0?' (aus)':''));
  wiedergabeMerken({sub_offset:subOffset});
  subIdx=-1;                                           // Zeile neu suchen
}
function subTick(el){
  if(!subCues||subMode==='aus')return;
  // Blink-Wurzel 1 (JB 05.08.: „untertitel blinken mal an, mal aus"): ohne
  // gültige Uhr NICHT malen. subTick(null) aus dem VLC-Takt traf früher ein
  // Video im Browser-Element (vlcAktiv()=false, el=null) → t=0 → keine Zeile
  // gefunden → Anzeige leergewischt; das nächste timeupdate malte sie neu —
  // exakt das 1-Hz-Blinken.
  if(!el&&!vlcAktiv())return;
  // Zeit-Quelle je Gerät: Browser = <audio>/<video>, VLC = geschätzte
  // Status-Zeit (JB-Fund 05.08.: am Gerät VLC kam nie ein Untertitel).
  const t=(vlcAktiv()?vlcPosGeschaetzt():(el?el.currentTime:0))+(subOffset||0);
  let i=subIdx;
  if(i<0||i>=subCues.length||t<subCues[i].start||t>=subCues[i].ende)
    i=subCues.findIndex(c=>t>=c.start&&t<c.ende);
  const ov=document.getElementById('pl-sub-anzeige');
  const istLrc=(subLang==='LRC');
  if(i!==subIdx){                                       // Zeile gewechselt -> neu aufbauen
    subIdx=i;
    if(i<0){ if(ov&&subMode!=='transkript')ov.innerHTML=''; }
    else if(subMode==='zeilen'&&ov){
      ov.innerHTML='<span class="subtxt">'+esc(subCues[i].text)+'</span>';
    }else if(subMode==='karaoke'&&ov){
      const prev=subCues[i-1], next=subCues[i+1];
      // Bei LRCLIB die aktive Zeile in Wörter zerlegt (Mitleuchten, JB 21.07.);
      // bei YouTube-Untertiteln normale Zeile (Wort-Timing dort unzuverlässig).
      ov.innerHTML='<div class="kar-neben">'+(prev?esc(prev.text):'&nbsp;')+'</div>'+
        '<div class="kar-akt'+(istLrc?' lrc':'')+'">'+(istLrc?karWorte(subCues[i].text):esc(subCues[i].text))+'</div>'+
        '<div class="kar-neben">'+(next?esc(next.text):'&nbsp;')+'</div>';
    }else if(subMode==='transkript'){
      const ly=document.getElementById('pl-lyrics');
      if(ly){ly.querySelectorAll('.lyr.akt').forEach(x=>x.classList.remove('akt'));
        const z=ly.querySelector('.lyr[data-i="'+i+'"]');
        if(z){z.classList.add('akt'); z.scrollIntoView({block:'nearest'});}}
    }
  }
  // Wort-Mitleuchten INNERHALB der aktiven LRCLIB-Zeile — jeder Tick, per Zeit
  // interpoliert (LRCLIB liefert Zeilen-, kein Wort-Timing -> gleichmäßig gefüllt).
  if(subMode==='karaoke'&&istLrc&&i>=0&&ov){
    // Build 115 (JB, „wie bei einer echten Karaoke-Maschine"): der Wischer
    // läuft KONTINUIERLICH durch die Zeile. Die Zeit wird nicht gleichmäßig
    // auf die Wörter verteilt, sondern nach WORTLÄNGE gewichtet — lange
    // Wörter brauchen länger, das trifft den Silben-Rhythmus deutlich besser
    // (echte Silben-Zeiten liefert die Textquelle leider nicht mit).
    // JB 05.08.: LRC kennt keine Endzeiten — „ende" ist der Start der
    // NÄCHSTEN Zeile. Bei langen Instrumental-Beats kroch der Wischer über
    // die ganze Lücke. Deckel: realistische Sing-Dauer aus der Zeilenlänge
    // (~90 ms je Zeichen, mind. 1,5 s); danach bleibt die Zeile fertig
    // gefärbt stehen, bis die nächste beginnt.
    const c=subCues[i],
          dauer=Math.min((c.ende-c.start)||1, Math.max(1.5, (c.text||'').length*0.09));
    const p=Math.max(0,Math.min(1,(t-c.start)/dauer));
    const kw=ov.querySelectorAll('.kar-akt .kw');
    if(kw.length){
      if(!ov._karGewicht||ov._karFuer!==i){          // Gewichte je Zeile einmal rechnen
        let summe=0; const g=[];
        kw.forEach(s=>{const l=Math.max(1,(s.textContent||'').trim().length); g.push(l); summe+=l;});
        ov._karGewicht=g.map(l=>l/summe); ov._karFuer=i;
      }
      let vorher=0;
      ov._karGewicht.forEach((anteil,n)=>{
        const lokal=Math.max(0,Math.min(1,(p-vorher)/(anteil||1)));
        kw[n].style.setProperty('--p',lokal);
        kw[n].classList.toggle('aktiv',lokal>0&&lokal<1);
        vorher+=anteil;
      });
    }
  }
}

/* ---- YouTube-Kapitel: klickbare Sprungmarken ---- */
function renderKapitel(x){
  const el=document.getElementById('pl-kapitel'); if(!el)return;
  const k=(x&&x.kapitel)||[];
  if(!k.length){el.style.display='none'; el.innerHTML=''; return;}
  el.style.display='';
  el.innerHTML='<div class="kap-titel">📖 Kapitel</div>'+k.map(c=>
    `<div class="kap" onclick="kapSpring(${c.start})"><span class="kap-z">${zeit(c.start)}</span> ${esc(c.titel||'')}</div>`).join('');
}
function kapSpring(s){const el=document.getElementById('pl-el'); if(el){el.currentTime=s; el.play();}}

/* ---- Visualizer (Web Audio): mehrere Stile, Farbe folgt dem aktiven Look ---- */
const VIZMODES=[['balken','📊','Balken'],['spiegel','🪞','Spiegel-Balken'],['welle','〰','Welle'],
  ['oszi','📈','Oszilloskop'],['radial','🎯','Radial'],['matrix','🟩','Matrix-Regen'],
  ['spektro','🌈','Spektrogramm'],['aus','▫','Aus']];
let vizMode='balken';
try{const v=localStorage.getItem('ytdl_viz'); if(v&&VIZMODES.some(m=>m[0]===v))vizMode=v;}catch(e){}
let audioCtx=null, vizAnalyser=null, vizSrc=null, vizGain=null, normGain=null, vizEl=null, vizRAF=null, vizFarbe='#c9952b';
let normAn=false; try{normAn=localStorage.getItem('ytdl_norm')==='1';}catch(e){}
function normSetzen(an){ normAn=!!an; try{localStorage.setItem('ytdl_norm',normAn?'1':'0');}catch(e){}
  if(!normAn&&normGain){try{normGain.gain.value=1;}catch(e){}} }
function vizFarbeAktualisieren(){
  try{vizFarbe=(getComputedStyle(document.documentElement).getPropertyValue('--akz')||'').trim()||'#c9952b';}catch(e){}
}
/* ---- Equalizer: 5 Peaking-Filter im Audio-Graphen (nutzt denselben Ctx) ---- */
const EQ_BANDS=[60,250,1000,4000,12000], EQ_LABELS=['60','250','1k','4k','12k'];
const EQ_PRESETS={'Flat':[0,0,0,0,0],'Bass':[7,4,0,0,0],'Höhen':[0,0,0,4,7],'Stimme':[-2,0,4,3,0],'Rock':[5,2,-1,3,5]};
let eqFilters=[], eqWerte=[0,0,0,0,0];
try{const v=JSON.parse(localStorage.getItem('ytdl_eq')); if(Array.isArray(v)&&v.length===5)eqWerte=v.map(n=>+n||0);}catch(e){}
function eqSetzen(i,db){ db=Math.max(-12,Math.min(12,Math.round(+db||0))); eqWerte[i]=db;
  if(eqFilters[i]){try{eqFilters[i].gain.value=db;}catch(e){}}
  try{localStorage.setItem('ytdl_eq',JSON.stringify(eqWerte));}catch(e){}
  const l=document.getElementById('eqval'+i); if(l)l.textContent=(db>0?'+':'')+db;
}
function eqPreset(name){ (EQ_PRESETS[name]||EQ_PRESETS.Flat).forEach((db,i)=>{
  eqSetzen(i,db); const s=document.getElementById('eqsl'+i); if(s)s.value=db; }); }
function eqPopover(ev){
  const alt=document.getElementById('eqpop'); if(alt){alt.remove(); return;}
  const m=document.createElement('div'); m.className='panelmenu'; m.id='eqpop'; m.style.minWidth='240px';
  m.innerHTML='<div class="sm-titel">🎚 Equalizer</div><div class="eq-row">'+
    EQ_BANDS.map((f,i)=>`<div class="eq-band"><span class="eq-val" id="eqval${i}">${(eqWerte[i]>0?'+':'')+(eqWerte[i]||0)}</span>`+
      `<input id="eqsl${i}" class="eq-sl" type="range" min="-12" max="12" step="1" value="${eqWerte[i]||0}" oninput="eqSetzen(${i},this.value)">`+
      `<span class="eq-lab">${EQ_LABELS[i]} Hz</span></div>`).join('')+
    '</div><div class="eq-presets">'+Object.keys(EQ_PRESETS).map(n=>`<button class="btn mini" onclick="eqPreset('${n}')">${n}</button>`).join('')+'</div>'+
    '<label class="eq-norm"><input type="checkbox" '+(normAn?'checked':'')+' onchange="normSetzen(this.checked)"> 🔊 Lautstärke angleichen (Titel gleich laut)</label>';
  document.body.appendChild(m);
  const r=ev.currentTarget.getBoundingClientRect();
  popoverBei(m,r);
  setTimeout(()=>document.addEventListener('pointerdown',function zu(e2){const p=document.getElementById('eqpop');
    if(p&&!p.contains(e2.target)&&!(e2.target.closest&&e2.target.closest('[onclick*="eqPopover"]'))){p.remove();document.removeEventListener('pointerdown',zu);}},true),0);
}

// Audio-Element in den Web-Audio-Graphen hängen: src -> gain -> EQ… -> analyser -> Ausgang.
// gain dient dem sanften Ausblenden beim Crossfade. Wichtig: Ton MUSS immer die
// Destination erreichen (sonst stumm), auch wenn Analyser/Gain/EQ scheitern.
function vizVerbinde(el){
  if(el===vizEl)return;
  const AC=window.AudioContext||window.webkitAudioContext; if(!AC)return;
  try{
    audioCtx=audioCtx||new AC();
    if(audioCtx.state==='suspended')audioCtx.resume();
    const src=audioCtx.createMediaElementSource(el);   // ein Element = genau ein Source-Node
    if(vizSrc){try{vizSrc.disconnect();}catch(e){}}
    if(normGain){try{normGain.disconnect();}catch(e){}}
    if(vizGain){try{vizGain.disconnect();}catch(e){}}
    if(vizAnalyser){try{vizAnalyser.disconnect();}catch(e){}}
    vizSrc=src;
    try{
      normGain=audioCtx.createGain(); normGain.gain.value=1;   // Lautstärke-Angleich (Auto-Level)
      vizGain=audioCtx.createGain(); vizGain.gain.value=1;     // Crossfade-Ausblenden
      vizAnalyser=audioCtx.createAnalyser(); vizAnalyser.fftSize=256; vizAnalyser.smoothingTimeConstant=0.8;
      // Equalizer-Kette: je Band ein Peaking-Filter
      eqFilters=EQ_BANDS.map((f,i)=>{const bq=audioCtx.createBiquadFilter();
        bq.type='peaking'; bq.frequency.value=f; bq.Q.value=1; bq.gain.value=eqWerte[i]||0; return bq;});
      // Graph: src -> normGain -> vizGain -> EQ… -> analyser -> Ausgang
      src.connect(normGain); normGain.connect(vizGain);
      let prev=vizGain; eqFilters.forEach(bq=>{prev.connect(bq); prev=bq;});
      prev.connect(vizAnalyser); vizAnalyser.connect(audioCtx.destination);
    }catch(e){ vizAnalyser=null; vizGain=null; normGain=null; eqFilters=[]; try{src.connect(audioCtx.destination);}catch(e2){} }
    vizEl=el;
  }catch(e){ vizAnalyser=null; }                        // Element spielt normal weiter
}
function vizModeRender(){
  const m=VIZMODES.find(x=>x[0]===vizMode)||VIZMODES[0], b=document.getElementById('pl-viz-btn');
  if(b){b.textContent=m[1]; b.title='Visualizer: '+m[2]+' (klicken zum Wechseln)'; b.classList.toggle('an',vizMode!=='aus');}
  const media=document.getElementById('pl-media'); if(media)media.classList.toggle('viz-an',vizMode!=='aus');
}
function vizStart(){ if(!vizRAF)vizLoop(); }
let vizMatrixDrops=null;
function vizLoop(){
  vizRAF=requestAnimationFrame(vizLoop);
  // Lautstärke-Angleich (läuft unabhängig vom Visualizer): Ausgangs-RMS langsam auf ein Ziel regeln.
  if(normAn && normGain && vizAnalyser){
    const buf=new Uint8Array(vizAnalyser.fftSize); vizAnalyser.getByteTimeDomainData(buf);
    let s=0; for(let i=0;i<buf.length;i++){const v=(buf[i]-128)/128; s+=v*v;}
    const rms=Math.sqrt(s/buf.length);
    if(rms>0.02){ const ziel=Math.max(0.3, Math.min(3, normGain.gain.value*(0.18/rms)));
      normGain.gain.value += (ziel-normGain.gain.value)*0.03; }   // langsam = kein Pumpen
  }
  const cv=document.getElementById('pl-viz'); if(!cv)return;
  if(cv.width!==cv.clientWidth)cv.width=cv.clientWidth;
  if(cv.height!==cv.clientHeight)cv.height=cv.clientHeight;
  const g=cv.getContext('2d'), W=cv.width, H=cv.height;
  const persist=(vizMode==='matrix'||vizMode==='spektro');   // diese Modi bauen auf dem Bild auf
  if(!vizAnalyser||vizMode==='aus'){g.clearRect(0,0,W,H);return;}
  if(!persist)g.clearRect(0,0,W,H);

  if(vizMode==='oszi'){                                // Oszilloskop = Wellenform der Zeit
    const buf=new Uint8Array(vizAnalyser.fftSize); vizAnalyser.getByteTimeDomainData(buf);
    g.lineWidth=2; g.strokeStyle=vizFarbe; g.beginPath();
    for(let i=0;i<buf.length;i++){const x=i/(buf.length-1)*W, y=(buf[i]/255)*H; i?g.lineTo(x,y):g.moveTo(x,y);}
    g.stroke(); return;
  }
  const bins=new Uint8Array(vizAnalyser.frequencyBinCount); vizAnalyser.getByteFrequencyData(bins);

  if(vizMode==='welle'){                               // gefüllte Frequenz-Silhouette
    const n=bins.length; g.fillStyle=vizFarbe; g.globalAlpha=0.85; g.beginPath(); g.moveTo(0,H);
    for(let i=0;i<n;i++){const x=i/(n-1)*W, y=H-(bins[i]/255)*H; g.lineTo(x,y);}
    g.lineTo(W,H); g.closePath(); g.fill(); g.globalAlpha=1; return;
  }
  if(vizMode==='spiegel'){                             // Balken von der Mitte nach oben UND unten
    const n=Math.min(bins.length,48), bw=W/n, mid=H/2; g.fillStyle=vizFarbe;
    for(let i=0;i<n;i++){const h=(bins[i]/255)*mid; g.fillRect(i*bw+1, mid-h, Math.max(1,bw-2), h*2);}
    return;
  }
  if(vizMode==='radial'){                              // Strahlen im Kreis aus der Mitte
    const cx=W/2, cy=H/2, R=Math.min(W,H)*0.16, n=Math.min(bins.length,64);
    g.strokeStyle=vizFarbe; g.lineWidth=Math.max(1.5,W/n/2.4);
    for(let i=0;i<n;i++){const a=(i/n)*Math.PI*2, len=R+(bins[i]/255)*Math.min(W,H)*0.33;
      g.beginPath(); g.moveTo(cx+Math.cos(a)*R, cy+Math.sin(a)*R);
      g.lineTo(cx+Math.cos(a)*len, cy+Math.sin(a)*len); g.stroke();}
    return;
  }
  if(vizMode==='matrix'){                              // „Matrix"-Regen, Tempo pulsiert mit dem Pegel
    const fh=14, cols=Math.max(1,Math.floor(W/fh));
    if(!vizMatrixDrops||vizMatrixDrops.length!==cols)vizMatrixDrops=Array.from({length:cols},()=>Math.random()*H/fh);
    g.fillStyle='rgba(0,0,0,0.12)'; g.fillRect(0,0,W,H);    // sanftes Nachleuchten (Trails)
    let pegel=0; for(let i=0;i<bins.length;i++)pegel+=bins[i]; pegel=pegel/bins.length/255;
    g.fillStyle=vizFarbe; g.font=fh+'px Consolas, monospace';
    for(let i=0;i<cols;i++){
      g.fillText(String.fromCharCode(0x30A0+Math.floor(Math.random()*96)), i*fh, vizMatrixDrops[i]*fh);
      vizMatrixDrops[i]+=0.5+pegel*2.4;
      if(vizMatrixDrops[i]*fh>H+40 || (vizMatrixDrops[i]*fh>H && Math.random()>0.975))vizMatrixDrops[i]=0;
    }
    return;
  }
  if(vizMode==='spektro'){                             // Spektrogramm-Wasserfall (scrollt nach links)
    try{g.putImageData(g.getImageData(2,0,Math.max(1,W-2),H),0,0);}catch(e){}
    const n=bins.length;
    for(let y=0;y<H;y++){const v=bins[Math.floor((1-y/H)*(n-1))]/255;
      g.fillStyle='hsl('+(200-160*v)+',90%,'+(8+52*v)+'%)'; g.fillRect(W-2,y,2,1);}
    return;
  }
  const n=Math.min(bins.length,48), bw=W/n;            // Balken (Standard)
  g.fillStyle=vizFarbe;
  for(let i=0;i<n;i++){const h=(bins[i]/255)*H; g.fillRect(i*bw+1, H-h, Math.max(1,bw-2), h);}
}
/* ---- Übergänge: Standard / Gapless (nahtlos) / Crossfade / Automix ---- */
let crossfadeSek=0, xfNext=null, adoptEl=null;
try{const v=parseInt(localStorage.getItem('ytdl_crossfade'),10); if(!isNaN(v))crossfadeSek=Math.max(0,Math.min(12,v));}catch(e){}
let uebergang='normal';
try{const v=localStorage.getItem('ytdl_uebergang');
  if(['normal','gapless','crossfade','automix'].includes(v))uebergang=v;
  else if(crossfadeSek>0)uebergang='crossfade';        // alte Crossfade-Einstellung übernehmen
}catch(e){}
function setUebergang(v){
  uebergang=v; try{localStorage.setItem('ytdl_uebergang',v);}catch(e){}
  const r=document.getElementById('xfrow'); if(r)r.style.display=(v==='crossfade'||v==='automix')?'block':'none';
}
/* Canvas: animiertes, weichgezeichnetes Cover als lebender Hintergrund (Spotify-Canvas-Gefühl) */
let canvasAn=false; try{canvasAn=localStorage.getItem('ytdl_canvas')==='1';}catch(e){}
function setCanvas(an){canvasAn=!!an; try{localStorage.setItem('ytdl_canvas',canvasAn?'1':'0');}catch(e){} canvasAnwenden();}
function canvasAnwenden(){
  const media=document.getElementById('pl-media'); if(!media)return;
  let c=document.getElementById('pl-canvas');
  const x=libFind(aktKey());
  const soll=canvasAn&&x&&x.thumb&&media.querySelector('audio');   // nur bei Audio (Video hat eigenes Bild)
  if(!soll){if(c)c.remove(); return;}
  if(!c){c=document.createElement('div'); c.id='pl-canvas'; c.className='pl-canvas'; media.prepend(c);}
  c.style.backgroundImage='url("'+x.thumb+'")';
}
function setCrossfade(v){
  crossfadeSek=Math.max(0,Math.min(12,parseInt(v,10)||0));
  try{localStorage.setItem('ytdl_crossfade',crossfadeSek);}catch(e){}
  const l=document.getElementById('xfval'); if(l)l.textContent=crossfadeSek?crossfadeSek+' s':'aus';
}
function xfAbbrechen(){                                // laufenden Übergang verwerfen, Lautstärke zurück
  if(xfNext){try{xfNext.pause();}catch(e){} xfNext=null;}
  if(vizGain){try{vizGain.gain.value=1;}catch(e){}}
}
function xfNaechsterIndex(){
  let ni=playerState.idx+1;
  if(radioAktiv){ radioNachfuellen(); return ni<playerState.queue.length?ni:-1; }
  if(ni<playerState.queue.length)return ni;
  return playRepeat==='alle'?0:-1;                     // „Alle wiederholen" blendet in den Anfang
}
function xfIstAudio(key){const x=libFind(key); return !!(x&&x.vorhanden&&((x.kategorie==='MP3')||(!x.vcodec&&x.acodec)));}
function starteCrossfade(cur, restSek){
  const ni=xfNaechsterIndex(); if(ni<0)return;
  const key=playerState.queue[ni]; if(!xfIstAudio(key))return;    // nur Audio in Audio überblenden
  const dauer=Math.max(0.3, Math.min(crossfadeSek, restSek));
  xfNext=new Audio('/media?id='+encodeURIComponent(key)); xfNext.volume=0; xfNext._ni=ni; xfNext._key=key;
  xfNext.play().catch(()=>{});
  const t0=performance.now();
  (function ramp(){                                    // aktuellen Titel aus-, nächsten einblenden
    if(!xfNext)return;
    const p=Math.min(1,(performance.now()-t0)/(dauer*1000));
    if(vizGain){try{vizGain.gain.value=1-p;}catch(e){}} else {try{cur.volume=1-p;}catch(e){}}
    try{xfNext.volume=p;}catch(e){}
    if(p<1)requestAnimationFrame(ramp);
  })();
}
function xfUebernehmen(){                              // Titel-Ende: vorbereitetes Element übernehmen
  if(!xfNext)return false;
  adoptEl=xfNext; xfNext=null; adoptEl.volume=1;
  if(adoptEl.paused)adoptEl.play().catch(()=>{});      // Gapless: gepuffertes Element startet SOFORT
  playerState.idx=adoptEl._ni;
  renderPlayerMedia(); return true;
}
function gaplessPreload(){                             // nächsten Titel nur PUFFERN (nicht abspielen)
  const ni=xfNaechsterIndex(); if(ni<0)return;
  const key=playerState.queue[ni]; if(!xfIstAudio(key))return;
  xfNext=new Audio('/media?id='+encodeURIComponent(key));
  xfNext.preload='auto'; xfNext._ni=ni; xfNext._key=key;
}
function uebergangTick(el){                            // ein Ticker für alle Übergangs-Arten
  if(!el.duration||el._xf)return;
  const rest=el.duration-el.currentTime;
  if(uebergang==='crossfade'&&crossfadeSek>0&&rest<=crossfadeSek){
    el._xf=true; starteCrossfade(el,rest);
  }else if(uebergang==='gapless'&&rest<=12&&!xfNext){
    gaplessPreload();
  }else if(uebergang==='automix'&&rest<=Math.max(16,(crossfadeSek||6)+4)){
    // Automix: wird das Outro leise (RMS fällt), JETZT weich überblenden — sonst spätestens kurz vor Ende
    let rms=1;
    if(vizAnalyser){const buf=new Uint8Array(vizAnalyser.fftSize); vizAnalyser.getByteTimeDomainData(buf);
      let s=0; for(let i=0;i<buf.length;i++){const v=(buf[i]-128)/128; s+=v*v;} rms=Math.sqrt(s/buf.length);}
    if(rms<0.06||rest<=Math.max(4,crossfadeSek||6)){el._xf=true; starteCrossfade(el,Math.min(rest,crossfadeSek||6));}
  }
}
/* ---- Steuerleiste AUF dem Video/Cover (JB 13.07.: „wie bei YouTube, Clip wie
   bei Twitch") — ersetzt die native Browser-Leiste bei Video UND Audio.
   Blendet bei Maus-Ruhe aus (nur solange abgespielt wird). ---- */
let plVol=100; try{const v=parseInt(localStorage.getItem('ytdl_vol'),10); if(v>=0&&v<=100)plVol=v;}catch(e){}
let plbSeekAktiv=false, plbIdleTimer=null;
function plBarHTML(istVideo){
  // onclick=stopPropagation: transportRender ersetzt beim Klick das Icon im
  // Knopf — das geklickte SVG ist dann schon aus dem DOM und der closest()-
  // Check in media.onclick griffe ins Leere -> Video pausierte (JB 13.07.).
  // Die Leiste schluckt ihre Klicks deshalb selbst, bevor sie die Fläche erreichen.
  return `<div class="pl-bar" id="pl-bar" onclick="event.stopPropagation()">`+
   `<div class="pl-barseek"><span class="pl-btime" id="plb-t0">0:00</span>`+
    `<input type="range" id="plb-seek" min="0" max="1000" value="0" title="Spulen" `+
      `oninput="plbSeekDrag(this.value)" onchange="plbSeekEnd(this.value)" `+
      `onpointerdown="plbSeekAktiv=true" onpointerup="plbSeekAktiv=false">`+
    `<span class="pl-btime" id="plb-t1">0:00</span></div>`+
   `<div class="pl-barrow">`+
    // Build 121 (JB-Entscheid): Im Bild lebt nur noch, was zum BILD gehört.
    // Play/Pause bleibt (der eine Griff, den man im Video erwartet — und ein
    // Klick ins Bild tut dasselbe); Zufall/Vor/Zurück/Wiederholen/Cover-Stil
    // stehen oben in der Steuerzentrale, die nie verschwindet.
    // Build 130: ±10 s und „nächster Titel" gibt es NUR im Vollbild — dort
    // fehlt die Steuerzentrale oben, die das sonst übernimmt.
    // JB 05.08. (Disney/Netflix-Bilder): ±10 s gehören IMMER in die Leiste,
    // nicht nur im Vollbild — fürs Sofa sind die Pfeiltasten zu weit weg.
    // JB 05.08.: „im videoplayer im fernseher ist vor und zurückspulen mit
    // höherer geschwindigkeit … schon << und >>. Am PC sollte es jedoch
    // nächster und vorheriger Track sein. PC ist halt anders als fernseher."
    // — Beide Paare stehen in der Leiste, CSS tauscht sie im Vollbild.
    `<button class="mp-btn weg-im-vollbild" id="plb-prev" onclick="playerPrev()" title="Voriger Titel — läuft der Titel schon, erst an den Anfang (Taste P)">${ico('prev')}</button>`+
    `<button class="mp-btn nur-vollbild" id="plb-rew" onclick="spulen(-1)" title="Zurückspulen — nochmal drücken: schneller (bis 32×), Play hält an der Stelle">${ico('back')}</button>`+
    `<button class="mp-btn" id="plb-back10" onclick="plbSpringen(-10)" title="10 Sekunden zurück (Taste J)">${ico('r10')}</button>`+
    `<button class="mp-btn" data-tr="pp" onclick="plTogglePlay()">${ico('play')}</button>`+
    `<button class="mp-btn" id="plb-fwd10" onclick="plbSpringen(10)" title="10 Sekunden vor (Taste L)">${ico('f10')}</button>`+
    `<button class="mp-btn nur-vollbild" id="plb-ffw" onclick="spulen(1)" title="Vorspulen — nochmal drücken: schneller (bis 32×), Play hält an der Stelle">${ico('fwd')}</button>`+
    `<button class="mp-btn weg-im-vollbild" id="plb-next" onclick="playerNext()" title="Nächster Titel (Taste N)">${ico('next')}</button>`+
    `<span class="pl-bspacer"></span>`+
    // JB 05.08. (Netflix/YouTube-Muster): Untertitel + Lautstärke gehören zum
    // KERN — sie überleben jede Player-Größe (keine bo-Ausblende-Klasse).
    `<button class="pl-bsp" id="plb-sub" onclick="subMenu(event)" title="Untertitel: Modus, Sprache, Größe, Stil, Versatz (Taste S wechselt schnell den Modus)">💬</button>`+
    `<button class="pl-bsp bo3 weg-im-vollbild" onclick="clipDialog(aktKey())" title="✂ Ausschnitt schneiden (wie ein Twitch-Clip)">✂</button>`+
    // JB 05.08.: am Fernseher (Vollbild) gehört ↻ (VLC neu verbinden) an die
    // Stelle der Schere — sichtbar nur am Gerät VLC.
    `<button class="pl-bsp nur-vollbild" onclick="vlcNeustart()" style="${plGeraet==='vlc'?'':'display:none'}" title="VLC neu verbinden: frisch starten und an der letzten Stelle weiterspielen">↻</button>`+
    `<button class="pl-bsp bo3 weg-im-vollbild" id="plb-speed" onclick="speedMenu(event)" title="Geschwindigkeit wählen">${playSpeed}×</button>`+
    `<span class="pl-bvolwrap">🔊<input type="range" class="pl-bvol" min="0" max="100" value="${plVol}" oninput="plbVol(this.value)" title="Lautstärke"></span>`+
    // YouTube-Öffnen und Link-Kopieren beziehen sich auf den TITEL, nicht auf
    // die Darstellung ⇒ sie stehen oben in der Steuerzentrale (Build 121).
    (istVideo?`<button class="pl-bsp bo2 weg-im-vollbild" onclick="plbPip()" title="Bild-in-Bild: Video schwebt über allen Fenstern (Taste I)">⧉</button>`:'')+
    (istVideo?`<button class="pl-bsp weg-im-vollbild" onclick="plbFullscreen()" title="Vollbild (Taste F)">⛶</button>`:'')+
    // Im Vollbild wird aus „Vollbild" ein deutliches „Beenden" (JB: Beenden
    // gehört zum Wichtigsten) — sonst sucht man im randlosen Bild den Ausweg.
    (istVideo?`<button class="pl-bsp nur-vollbild" id="plb-exitfs" onclick="plbFullscreen()" title="Vollbild beenden (Taste F oder Esc)">✕</button>`:'')+
   `</div></div>`;
}
function plTogglePlay(){
  // Streamer-Muster: Läuft gerade der Spul-Modus, beendet Play/OK NUR das
  // Spulen — es läuft an der Stelle weiter (pausiert wurde ja nie).
  if(spulWeg){spulStopp(); return;}
  if(vlcAktiv()){
    // JB 05.08.: das Symbol muss SOFORT umspringen — nicht erst mit dem
    // nächsten 1-s-Status (der korrigiert, falls der Befehl scheiterte).
    vlcSpielt=!vlcSpielt;
    document.querySelectorAll('[data-tr="pp"]').forEach(b=>{
      b.innerHTML=ico(vlcSpielt?'pause':'play');
      b.title=vlcSpielt?'Pause':'Abspielen';});
    vlcBefehl('toggle'); return;}
  const el=document.getElementById('pl-el'); if(el){if(el.paused)el.play(); else el.pause();}}
/* ---- Springen mit sichtbarer Rückmeldung (Build 132) ----------------------
   JB: „Wenn ich Pfeiltasten drücke, dann will ich wie in YouTube sehen, dass
   ich ein paar Sekunden vorgespult habe."
   Recherche dazu: dass die Pfeiltasten bei YouTube 5 Sekunden springen, ist
   belegt (support.google.com — Keyboard shortcuts). Für die genaue Optik der
   Desktop-Rückmeldung fand sich keine belastbare Quelle; gebaut ist deshalb
   das dokumentierte Muster aus YouTubes Doppeltipp-Bedienung und aus
   Netflix/Disney: ein kurzer Einblender auf der Seite, in die gesprungen
   wird, mit Pfeil und Sekundenzahl. Er verblasst nach ~700 ms von selbst und
   nimmt keine Klicks an — reine Rückmeldung, kein Bedienelement. */
let _sprungWeg=null, _sprungSumme=0, _sprungTimer=null;
function sprungZeigen(s){
  const media=document.getElementById('pl-media'); if(!media)return;
  // Schnell hintereinander gedrückt? Dann zählt der Einblender mit, statt zu
  // flackern — genau wie man es von YouTube kennt.
  if(_sprungWeg && Math.sign(_sprungSumme)===Math.sign(s)) _sprungSumme+=s; else _sprungSumme=s;
  if(_sprungWeg){_sprungWeg.remove(); _sprungWeg=null;}
  const d=document.createElement('div');
  d.className='pl-sprung '+(s<0?'links':'rechts');
  d.innerHTML=ico(s<0?'r10':'f10')+'<span>'+Math.abs(_sprungSumme)+' s</span>';
  media.appendChild(d); _sprungWeg=d;
  clearTimeout(_sprungTimer);
  _sprungTimer=setTimeout(()=>{if(_sprungWeg){_sprungWeg.remove(); _sprungWeg=null;} _sprungSumme=0;},700);
}
function plbSpringen(s,leise){                         // Build 130: ±x s im Vollbild-Overlay
  if(vlcAktiv()){                                     // Gerät VLC: über den Status springen
    if(!vlcDauerLetzte)return;
    vlcPosLetzte=Math.max(0,Math.min(vlcDauerLetzte,vlcPosLetzte+s));
    vlcBefehl('seek',{wert:vlcPosLetzte});
    if(!leise)sprungZeigen(s);
    return;
  }
  const el=document.getElementById('pl-el');
  if(!el||!el.duration)return;
  el.currentTime=Math.max(0,Math.min(el.duration,el.currentTime+s));
  if(!leise)sprungZeigen(s);
}
/* ---- Spulen am Fernseher (JB 05.08.) --------------------------------------
   „im videoplayer im fernseher ist vor und zurückspulen mit höherer
   geschwindigkeit als 10 sec vor und zurück schon << und >>." — Im Vollbild
   sind ⏪/⏩ deshalb ein Spul-Modus wie bei den Streamern: jeder Druck in
   dieselbe Richtung erhöht die Geschwindigkeit (4× → 8× → 16× → 32×), die
   Gegenrichtung dreht um, Play/OK beendet das Spulen und es läuft an der
   Stelle normal weiter. Technisch springt ein Halbsekunden-Takt über
   plbSpringen — das funktioniert für <video> UND das Gerät VLC identisch
   (echtes Rückwärts-Abspielen kann keiner von beiden), und man hört beim
   Spulen kurze Schnipsel, wie am Videorekorder — man weiß, wo man ist. */
let spulWeg=0, spulStufe=0, spulTimer=null;
const SPUL_FAKTOREN=[0,4,8,16,32];
function spulAnzeige(){
  const m=document.getElementById('pl-media'); if(!m)return;
  let d=document.getElementById('pl-spul');
  if(!spulWeg){ if(d)d.remove(); return; }
  if(!d){ d=document.createElement('div'); d.id='pl-spul'; m.appendChild(d); }
  d.innerHTML=ico(spulWeg<0?'back':'fwd')+'<span>'+SPUL_FAKTOREN[spulStufe]+'×</span>';
}
function spulStopp(){
  if(spulTimer){clearInterval(spulTimer); spulTimer=null;}
  spulWeg=0; spulStufe=0; spulAnzeige();
}
function spulTick(){
  if(!spulWeg)return spulStopp();
  plbSpringen(spulWeg*SPUL_FAKTOREN[spulStufe]*0.5, true);
  // Am Anfang bzw. Ende des Titels ist Schluss (das Titel-Ende selbst
  // behandelt weiter der normale Weiterschalt-Weg, nicht das Spulen).
  if(vlcAktiv()){
    if(spulWeg<0 ? vlcPosLetzte<=0.5 : (vlcDauerLetzte&&vlcPosLetzte>=vlcDauerLetzte-1)) spulStopp();
  }else{
    const el=document.getElementById('pl-el');
    if(!el||!el.duration||(spulWeg<0?el.currentTime<=0.5:el.currentTime>=el.duration-1)) spulStopp();
  }
}
function spulen(richtung){
  if(spulWeg===richtung) spulStufe=Math.min(spulStufe+1, SPUL_FAKTOREN.length-1);
  else { spulWeg=richtung; spulStufe=1; }
  spulAnzeige();
  if(!spulTimer)spulTimer=setInterval(spulTick, 500);
}
// Vollbild verlassen = Spulen beenden (die Knöpfe dafür sind dann weg).
document.addEventListener('fullscreenchange', ()=>{ if(!document.fullscreenElement) spulStopp(); });
/* Sprungweite der Pfeiltasten (JB-Wunsch: einstellbar). YouTube nimmt 5 s —
   das bleibt der Standard, damit sich die Tasten vertraut anfühlen. */
function sprungWeite(){
  let v=5; try{v=parseInt(localStorage.getItem('ytdl_sprung'),10)||5;}catch(e){}
  return Math.max(1,Math.min(60,v));
}
function sprungWeiteSetzen(v){
  const n=Math.max(1,Math.min(60,parseInt(v,10)||5));
  try{localStorage.setItem('ytdl_sprung',n);}catch(e){}
  toast('⏩ Pfeiltasten springen '+n+' Sekunden.');
}
/* Seitenverhältnis des Bildfelds (Build 130). JB will 16:9 FEST, damit das
   Bild beim Titelwechsel nicht springt; die anderen Werte sind die
   Layout-Option daneben. Gemerkt wird lokal — es ist eine Ansichts-Sache,
   keine Programm-Einstellung. */
const PL_AR=[['16/9','16:9 (Standard)'],['4/3','4:3'],['21/9','21:9 Kino'],['frei','Natürlich (springt)']];
function arAnlegen(m,v){
  // --pl-ar fürs aspect-ratio, --pl-arn als ZAHL fürs Rechnen in calc()
  // (ein „16/9" liesse sich dort nicht als Faktor verwenden).
  m.classList.toggle('ar-frei',v==='frei');
  m.style.setProperty('--pl-ar', v==='frei'?'auto':v);
  const teile=String(v).split('/');
  const zahl=(teile.length===2&&+teile[1])?(+teile[0]/+teile[1]):1.7778;
  m.style.setProperty('--pl-arn', zahl.toFixed(4));
}
function seitenverhaeltnisSetzen(v){
  try{localStorage.setItem('ytdl_ar',v);}catch(e){}
  const m=document.getElementById('pl-media'); if(!m)return;
  arAnlegen(m,v);
  toast('🖵 Seitenverhältnis: '+((PL_AR.find(a=>a[0]===v)||[])[1]||v));
}
function seitenverhaeltnisAnwenden(){                  // beim Aufbau des Players
  let v='16/9'; try{v=localStorage.getItem('ytdl_ar')||'16/9';}catch(e){}
  const m=document.getElementById('pl-media'); if(m)arAnlegen(m,v);
}
function plbSeekDrag(v){const el=document.getElementById('pl-el'), t=document.getElementById('plb-t0');
  const d=vlcAktiv()?vlcDauerLetzte:(el&&el.duration);
  if(d&&t)t.textContent=zeit(v/1000*d);}
function plbSeekEnd(v){
  if(vlcAktiv()){
    if(vlcDauerLetzte){vlcPosLetzte=v/1000*vlcDauerLetzte; vlcBefehl('seek',{wert:vlcPosLetzte});}
    plbSeekAktiv=false; return;
  }
  const el=document.getElementById('pl-el');
  if(el&&el.duration)el.currentTime=v/1000*el.duration; plbSeekAktiv=false;}
function plbVol(v){plVol=Math.max(0,Math.min(100,+v||0));
  try{localStorage.setItem('ytdl_vol',plVol);}catch(e){}
  if(vlcAktiv())vlcBefehl('vol',{wert:plVol});   // Gerät VLC hört auf dieselbe Lautstärke
  const el=document.getElementById('pl-el'); if(el)el.volume=plVol/100;
  // Mini-Player- und Video-Leisten-Regler zeigen immer denselben Stand
  document.querySelectorAll('.pl-bvol').forEach(s=>{if(+s.value!==plVol)s.value=plVol;});}
function plbFullscreen(){const m=document.getElementById('pl-media'); if(!m)return;
  if(document.fullscreenElement)document.exitFullscreen();
  else if(m.requestFullscreen)m.requestFullscreen();}
/* ---- TV-Bibliothek (Sync Teilprojekt 2 v1) --------------------------------
   JB: „erledige alle aufgaben von der roadmap" — der Fernsehmodus öffnet
   jetzt die eigene 10-Fuß-Ansicht: Menü-Schnitt A (Home · Filme · Serien ·
   Neu & Beliebt · ❤ · YouTube · Musik · Suche), Poster-Reihen, reine
   Pfeil-/Fernbedienungs-Navigation (Enter wählt, Esc/Zurück schließt).
   Enter auf einen Film startet ihn im VLC (Film-Fundament); Enter auf einen
   Titel spielt ihn im Player. Feinschliff-Runden folgen mit JBs Blick. */
const TV_TABS=[['suche','🔍'],['home','Home'],['filme','Filme'],['serien','Serien'],
  ['neu','Neu & Beliebt'],['live','📡 Live'],['herz','❤ Favoriten'],['yt','▶ YouTube'],['musik','🎵 Musik']];
let tvTab='home', tvFokus={r:0,i:0}, tvReihenListe=[], tvFilmReihen=null;
function fernsehModus(){
  if(typeof ansichtZu==='function')ansichtZu();
  const o=document.getElementById('optionen'); if(o)o.remove();
  tvOeffnen();
}
/* Hover-Karte (JB: „siehst du den unterschied?", Netflix-Referenz): nach
   800 ms Verweilen expandiert die Kachel zur QUER-Karte — 16:9-Snippet
   (ffmpeg-Bäcker, Fallback Backdrop-Bild) oben, darunter Knopfzeile
   ▶ / ＋ / ⌄, dann Fortschritt „X von Y min" ODER Meta (FSK · Dauer) und
   Genre-Tags. Die Karte schwebt FIXED über der Reihe (das Band clippt
   sonst vertikal) und hängt im Vollbild am fullscreenElement. */
let snipTimer=null;
function snippetAn(kachel){
  const fid=kachel&&kachel.dataset&&kachel.dataset.fid; if(!fid)return;
  clearTimeout(snipTimer);
  snipTimer=setTimeout(()=>{
    // Nachtprüfung 06.08.: Timer traf eine ABGEHÄNGTE Kachel (Reihe neu
    // gemalt) oder feuerte, während die Info-Seite schon offen war —
    // die Karte hing dann hinter der Info bzw. das Sync-Intervall verwaiste.
    if(tvInfoOffen||!kachel.isConnected)return;
    if(document.querySelector('.tv-hoverkarte[data-fid="'+CSS.escape(fid)+'"]'))return;
    snippetAus();
    const r=+kachel.dataset.r, i=+kachel.dataset.i;
    const e=((tvReihenListe[r]||[])[1]||[])[i]||{};
    // JB 06.08. („Man sieht noch … im hintergrund. Das soll das alte fenster
    // komplett verdecken"): ERST die Quell-Kachel entzoomen (hk-quelle,
    // transition aus), DANN messen — sonst platziert sich die Karte auf die
    // gezoomte Geometrie und die Kachel lugt nach dem Schrumpfen hervor.
    document.querySelectorAll('.hk-quelle').forEach(x=>x.classList.remove('hk-quelle'));
    kachel.classList.add('hk-quelle');
    const w=Math.max(320, Math.round(kachel.getBoundingClientRect().width*1.5));
    const kt=document.createElement('div');
    kt.className='tv-hoverkarte'; kt.dataset.fid=fid;
    kt.style.width=w+'px';
    kt.style.left='-9999px'; kt.style.top='-9999px';   // erst messen, dann setzen
    const dauer=e.dauer?(e.dauer>=60?Math.floor(e.dauer/60)+' Std. '+(e.dauer%60)+' Min.'
                                    :e.dauer+' Min.'):'';
    const proz=(e.pos>30&&e.dauer)?Math.min(99,Math.round(e.pos/(e.dauer*60)*100)):0;
    const fi=encodeURIComponent(fid);
    kt.innerHTML=
      `<div class="hk-bild"><img src="/api/filme/bild?id=${fi}&art=Thumb" `+
        `onerror="if(!this.dataset.s){this.dataset.s=1;this.src='/api/filme/bild?id=${fi}&art=Backdrop'}`+
        `else{this.onerror=null;this.src='/api/filme/bild?id=${fi}'}">`+
      `<video class="tv-snip" muted loop autoplay playsinline `+
        `src="/api/filme/snippet?id=${fi}" onerror="this.remove()"></video>`+
      `<div class="hk-titel">${esc(e.name||'')}</div></div>`+
      `<div class="hk-zeile">`+
      `<button class="hk-ib hk-play" onclick="event.stopPropagation();snippetAus();filmePlay('${esc(fid)}',${e.pos||0})" title="Abspielen">${ico('play')}</button>`+
      `<button class="hk-ib" onclick="event.stopPropagation();tvMerk('${esc(fid)}')" title="Zur Liste">${ico('plus')}</button>`+
      `<button class="hk-ib hk-rechts" onclick="event.stopPropagation();snippetAus();tvInfo('${esc(fid)}')" title="Mehr Infos">${ico('chevron')}</button></div>`+
      (proz?`<div class="hk-balken"><div class="hk-spur"><div style="width:${proz}%"></div></div>`+
            `<span>${Math.round(e.pos/60)} von ${e.dauer} Min.</span></div>`
           :`<div class="hk-meta">${(e.fsk?`<span class="hk-fsk">${esc(e.fsk)}</span>`:'')}`+
            `<span>${esc(dauer)}</span><span class="hk-hd">HD</span></div>`)+
      ((e.genres&&e.genres.length)?`<div class="hk-tags">${esc(e.genres.slice(0,3).join(' · '))}</div>`:'');
    kt.onclick=()=>{snippetAus(); tvInfo(fid);};
    kt.onmouseleave=()=>snippetAus();
    (document.fullscreenElement||document.body).appendChild(kt);
    // Die fixed-Karte KLEBT an ihrer Kachel: ein Sync-Takt zieht die
    // Position nach (Hero/Bilder laden nach, Bänder scrollen — einmalige
    // Messungen hingen live neben der Kachel; gemessen 06.08.). Verwaiste
    // Kacheln (Reihe neu gemalt) schließen die Karte.
    const setzen=()=>{
      if(!kachel.isConnected){snippetAus(); return;}
      const kr=kachel.getBoundingClientRect();
      // offsetHeight statt gBCR: die Aufzoom-Animation skaliert die Karte —
      // gBCR maß die halbfertige Höhe und die Karte RUCKTE am Ende nach
      // oben (JB-Fund 06.08. früh). offsetHeight ignoriert transform.
      const h=kt.offsetHeight||240;
      kt.style.left=Math.max(8, Math.min(innerWidth-w-8, kr.left+kr.width/2-w/2))+'px';
      kt.style.top=Math.max(8, Math.min(innerHeight-h-8, kr.top+kr.height/2-h/2))+'px';
    };
    kt._sync=setInterval(setzen,120);                  // VOR setzen() — sonst Waise
    setzen();
  },450);                                              // Netflix reagiert nach ~450 ms
}
function snippetAus(){
  clearTimeout(snipTimer);
  document.querySelectorAll('.tv-hoverkarte').forEach(x=>{
    if(x._sync)clearInterval(x._sync);
    x.remove();});
  document.querySelectorAll('.hk-quelle').forEach(x=>x.classList.remove('hk-quelle'));
}
let _snipVerkabelt=false;
function snippetVerkabeln(){
  if(_snipVerkabelt)return; _snipVerkabelt=true;
  const inhalt=document.getElementById('tv-inhalt'); if(!inhalt)return;
  inhalt.addEventListener('mouseover',ev=>{
    const k=ev.target.closest&&ev.target.closest('.tv-kachel[data-fid]');
    if(k&&!document.querySelector('.tv-hoverkarte[data-fid="'+CSS.escape(k.dataset.fid)+'"]')){
      snippetAus(); snippetAn(k);}
    const reihe=ev.target.closest&&ev.target.closest('.tv-reihe');
    if(reihe)tvSeitenMalen(reihe);                     // Striche beim Verweilen
  });
  inhalt.addEventListener('scroll',ev=>{               // Band gescrollt → Striche nachziehen
    const b=ev.target;
    if(b&&b.classList&&b.classList.contains('tv-band'))tvSeitenMalen(b.closest('.tv-reihe'));
  },true);
  inhalt.addEventListener('mouseout',ev=>{
    const k=ev.target.closest&&ev.target.closest('.tv-kachel[data-fid]');
    const zu=ev.relatedTarget;
    // Die Karte liegt AUSSERHALB der Kachel — Wandern auf die Karte ist kein Verlassen.
    if(k&&!k.contains(zu)&&!(zu&&zu.closest&&zu.closest('.tv-hoverkarte')))snippetAus();
  });
}
async function tvOeffnen(){
  const tv=document.getElementById('tv'); if(!tv)return;
  snippetVerkabeln();
  tv.style.display='flex'; tvTab='home'; tvFokus={r:0,i:0};
  document.addEventListener('keydown',tvKey,true);     // capture: Hotkeys treten zurück
  try{if(!document.fullscreenElement&&tv.requestFullscreen)tv.requestFullscreen().catch(()=>{});}catch(e){}
  await tvProfileLaden();
  // „Wer schaut?" nur, wenn es WIRKLICH etwas zu wählen gibt (calm) oder die
  // gemerkte Wahl nicht mehr existiert.
  const gilt=(tvProfile||[]).some(p=>p.id===tvProfil());
  if((tvProfile||[]).length>1||!gilt){tvProfilWahl(); return;}
  tvLaden();
}
function tvZu(){
  const tv=document.getElementById('tv'); if(!tv)return;
  snippetAus();                                        // Karte + Sync-Takt abräumen
  tvInfoStapel=[];                                     // sonst öffnet tvInfoZu wieder
  if(typeof tvInfoZu==='function')tvInfoZu();          // Info-Seite räumt mit ab
  tv.style.display='none';
  document.removeEventListener('keydown',tvKey,true);
  if(document.fullscreenElement===tv)document.exitFullscreen().catch(()=>{});
}
async function tvLaden(){
  tvProfilModus=false;
  try{tvFilmReihen=await (await fetch('/api/filme/reihen?profil='+encodeURIComponent(tvProfil()))).json();}
  catch(e){tvFilmReihen={weiterschauen:[],top:[],neu:[],genres:{}};}
  tvMalen();
}
function tvKopfMalen(){
  const k=document.getElementById('tv-kopf');
  const p=(tvProfile||[]).find(x=>x.id===tvProfil())||{emoji:'👤',name:''};
  k.innerHTML=TV_TABS.map(([id,name])=>
    `<button class="tvtab${tvTab===id?' akt':''}" data-tv="${id}" onclick="tvTabWahl('${id}')">${name}</button>`).join('')+
    `<button class="tvzu" onclick="tvProfilWahl()" title="Profil wechseln — ${esc(p.name)}" style="margin-left:auto">${p.emoji}</button>`+
    `<button class="tvzu" style="margin-left:0" onclick="tvZu()" title="Fernsehmodus verlassen (Esc)">✕</button>`;
}
/* ---- Geräte koppeln (Teilprojekt 3, nur am PC) ----------------------------
   Fluss: Neues Gerät öffnet die LAN-Adresse (QR abfotografieren) → sieht die
   Pairing-Seite mit GROSSEM Code → JB gibt HIER frei (Profil zuordnen) → das
   Gerät holt sich seinen eigenen Token und lädt die volle Oberfläche.
   Jeder Token ist einzeln widerrufbar (🗑 Trennen). */
async function geraeteDialog(){
  const o=document.getElementById('optionen'); if(o)o.remove();
  document.querySelectorAll('#gerdlg').forEach(x=>x.remove());
  const m=document.createElement('div'); m.className='panelmenu'; m.id='gerdlg';
  m.style.minWidth='330px'; m.style.maxWidth='380px';
  m.innerHTML='<div class="sm-titel">📺 Geräte koppeln</div><div id="gerdlg-body" style="padding:6px">Lade…</div>';
  document.body.appendChild(m);
  m.style.left='50%'; m.style.top='16%'; m.style.transform='translateX(-50%)'; m.style.position='fixed';
  menuSchliesser(m);
  geraeteMalen();
}
async function geraeteMalen(){
  const body=document.getElementById('gerdlg-body'); if(!body)return;
  let d={items:[],url:'',wlan:false};
  try{d=await (await fetch('/api/geraete')).json();}catch(e){}
  let profile=[];
  try{profile=((await (await fetch('/api/profile')).json())||{}).items||[];}catch(e){}
  const optionen=profile.map(p=>`<option value="${esc(p.id)}">${p.emoji} ${esc(p.name)}</option>`).join('');
  const wartend=d.items.filter(g=>!g.verifiziert), fest=d.items.filter(g=>g.verifiziert);
  body.innerHTML=
    (d.wlan
      ?`<div style="text-align:center"><img src="/api/geraet_qr" style="width:170px;height:170px;border-radius:8px;background:#fff;padding:6px"><br>`+
       `<span style="font-size:12px;color:#8a7d74">Mit dem Gerät abfotografieren oder öffnen:<br><b>${esc(d.url)}</b></span></div>`
      :`<div style="font-size:13px;color:#c9803f;padding:4px 2px">⚠ Die Fernsteuerung ist AUS — kein Gerät erreicht den Server. `+
       `Erst oben unter „📱 Fernsteuerung" einschalten, dann koppeln.</div>`)+
    (wartend.length?'<div class="sm-titel" style="margin-top:8px">Wartet auf Freigabe</div>'+wartend.map(g=>
      `<div class="optrow"><span>${esc(g.name)} — Code <b style="color:var(--akz2)">${esc(g.code)}</b></span>`+
      `<span><select id="gpr-${esc(g.id)}" class="btn mini">${optionen}</select> `+
      `<button class="btn mini" onclick="geraetFreigeben('${esc(g.id)}')">✓ Freigeben</button></span></div>`).join(''):'')+
    (fest.length?'<div class="sm-titel" style="margin-top:8px">Gekoppelt</div>'+fest.map(g=>{
      const p=profile.find(x=>x.id===g.profil)||{emoji:'👤',name:g.profil};
      return `<div class="optrow"><span>${esc(g.name)} · ${p.emoji} ${esc(p.name)}</span>`+
      `<button class="btn mini" onclick="geraetTrennen('${esc(g.id)}')">🗑 Trennen</button></div>`;}).join(''):'')+
    (!wartend.length&&!fest.length&&d.wlan?'<div style="font-size:13px;color:#8a7d74;padding:6px 2px">Noch kein Gerät angemeldet — sobald eines die Adresse öffnet, erscheint es hier mit seinem Code.</div>':'');
  if(wartend.length)setTimeout(geraeteMalen,4000);     // frisch halten, solange gewartet wird
}
async function geraetFreigeben(id){
  const sel=document.getElementById('gpr-'+id);
  try{await fetch('/api/geraet_bestaetigen',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id, profil:(sel&&sel.value)||'standard'})});
    toast('📺 Gerät freigegeben — es verbindet sich gleich von selbst.');
  }catch(e){toast('📺 Freigeben fehlgeschlagen.');}
  geraeteMalen();
}
async function geraetTrennen(id){
  try{await fetch('/api/geraet_entfernen',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({id})});
    toast('📺 Gerät getrennt — der Zugang ist sofort wertlos.');
  }catch(e){toast('📺 Trennen fehlgeschlagen.');}
  geraeteMalen();
}
/* ---- Profile („Wer schaut?", Teilprojekt 3) ------------------------------- */
let tvProfile=null, tvProfilModus=false;
function tvProfil(){try{return localStorage.getItem('ytdl_profil')||'standard';}catch(e){return 'standard';}}
async function tvProfileLaden(){
  try{tvProfile=((await (await fetch('/api/profile')).json())||{}).items||[];}
  catch(e){tvProfile=[{id:'standard',name:'JB',emoji:'🦊'}];}
}
function tvProfilWahl(){
  tvProfilModus=true; tvFokus={r:0,i:0};
  const inhalt=document.getElementById('tv-inhalt');
  document.getElementById('tv-kopf').innerHTML='';
  inhalt.innerHTML=`<div class="tv-werschaut"><div class="tv-rtitel" style="font-size:34px;text-align:center;margin-top:8vh">Wer schaut?</div>`+
    `<div class="tv-band" style="justify-content:center;margin-top:30px">`+
    (tvProfile||[]).map((p,i)=>`<div class="tv-kachel tv-profil" data-pr="${i}" onclick="tvProfilSetzen('${esc(p.id)}')">`+
      `<div class="tv-pemoji">${p.emoji}</div><div class="tv-ktitel" style="font-size:18px">${esc(p.name)}</div></div>`).join('')+
    `<div class="tv-kachel tv-profil" data-pr="${(tvProfile||[]).length}" onclick="tvProfilNeu()">`+
      `<div class="tv-pemoji">＋</div><div class="tv-ktitel" style="font-size:18px">Neues Profil</div></div>`+
    `</div></div>`;
  tvProfilFokusMalen();
}
function tvProfilFokusMalen(){
  document.querySelectorAll('#tv .tv-fokus').forEach(x=>x.classList.remove('tv-fokus'));
  const alle=document.querySelectorAll('#tv [data-pr]');
  const z=alle[Math.max(0,Math.min(alle.length-1,tvFokus.i))];
  if(z){z.classList.add('tv-fokus'); z.scrollIntoView({block:'nearest',inline:'nearest'});}
}
function tvProfilSetzen(id){
  try{localStorage.setItem('ytdl_profil',id);}catch(e){}
  tvProfilModus=false; tvTab='home'; tvFokus={r:0,i:0};
  tvFilmReihen=null; tvLaden();
}
/* Eigener TV-Dialog fürs Profil-Anlegen (JB: „bau den") — der native
   prompt() warf den Browser aus dem Vollbild. Name + Emoji-Reihe, komplett
   per Fernbedienung bedienbar (Ebenen: Feld → Emojis → Knöpfe). */
let tvDialogOffen=false, tvDlgFokus={r:0,i:0}, tvDlgEmoji='🦊';
const TV_EMOJIS=['🦊','🦁','🐼','🐸','🦄','🐯','🐙','🤖'];
function tvProfilNeu(){
  tvDialogOffen=true; tvDlgEmoji='🦊'; tvDlgFokus={r:0,i:0};
  let el=document.getElementById('tv-dialog');
  if(!el){el=document.createElement('div'); el.id='tv-dialog';}
  (document.fullscreenElement||document.body).appendChild(el);   // Fullscreen-Regel
  el.style.display='flex';
  el.innerHTML=`<div class="dlg"><div class="tv-rtitel" style="margin-top:0">Neues Profil</div>`+
    `<input id="tv-dlg-name" placeholder="Name" maxlength="24" autocomplete="off">`+
    `<div class="emojis">${TV_EMOJIS.map((e,i)=>
      `<button class="emo${e===tvDlgEmoji?' akt':''}" data-emo="${i}" onclick="tvDlgEmojiWahl(${i})">${e}</button>`).join('')}</div>`+
    `<div class="info-btns" style="justify-content:center">`+
      `<button class="tv-btn" data-dlg="0" onclick="tvDlgAnlegen()">✓ Anlegen</button>`+
      `<button class="tv-btn zart" data-dlg="1" onclick="tvDialogZu()">✕ Abbrechen</button>`+
    `</div></div>`;
  const inp=document.getElementById('tv-dlg-name'); if(inp)inp.focus();
}
function tvDialogZu(){
  tvDialogOffen=false;
  const el=document.getElementById('tv-dialog'); if(el){el.style.display='none'; el.innerHTML='';}
}
function tvDlgEmojiWahl(i){
  tvDlgEmoji=TV_EMOJIS[i]||'🦊';
  document.querySelectorAll('#tv-dialog .emo').forEach((b,j)=>b.classList.toggle('akt',j===i));
}
async function tvDlgAnlegen(){
  const inp=document.getElementById('tv-dlg-name');
  const name=(inp&&inp.value.trim())||'';
  if(!name){toast('👤 Bitte erst einen Namen eingeben.'); if(inp)inp.focus(); return;}
  try{
    const p=await (await fetch('/api/profil_anlegen',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name, emoji:tvDlgEmoji})})).json();
    if(p&&p.id){tvDialogZu(); await tvProfileLaden(); tvProfilSetzen(p.id); return;}
  }catch(e){}
  toast('👤 Profil anlegen fehlgeschlagen.');
}
function tvDlgFokusMalen(){
  document.querySelectorAll('#tv-dialog .tv-fokus').forEach(x=>x.classList.remove('tv-fokus'));
  if(tvDlgFokus.r===0){const i2=document.getElementById('tv-dlg-name'); if(i2)i2.focus(); return;}
  const zeile=tvDlgFokus.r===1
    ?document.querySelectorAll('#tv-dialog .emo')
    :document.querySelectorAll('#tv-dialog [data-dlg]');
  tvDlgFokus.i=Math.max(0,Math.min(zeile.length-1,tvDlgFokus.i));   // Klemme zurückschreiben
  const z=zeile[tvDlgFokus.i];
  if(!z)return;
  if(document.activeElement&&document.activeElement.id==='tv-dlg-name')document.activeElement.blur();
  z.classList.add('tv-fokus'); z.scrollIntoView({block:'nearest'});
}
function tvTabWahl(id){tvTab=id; tvFokus={r:0,i:0};
  if(id==='herz'&&tvWuensche===null)tvWuenscheLaden().then(tvMalen);  // Wünsche einmalig ziehen
  if(id==='live'&&tvLive===null)tvLiveLaden();                        // Kanäle einmalig ziehen
  tvMalen();}
/* 📡 Live (JB-Go): kodinerds-Legal-Liste, VLC spielt m3u8 direkt. */
let tvLive=null, tvKatalog=null;
async function tvKatalogLaden(){
  try{tvKatalog=((await (await fetch('/api/filme/katalog')).json())||{}).eintraege||[];}
  catch(e){tvKatalog=[];}
  tvMalen();
}
async function tvLiveLaden(){
  try{tvLive=((await (await fetch('/api/live')).json())||{}).items||[];}catch(e){tvLive=[];}
  tvMalen();
}
async function tvLivePlay(e){
  if(document.fullscreenElement){try{document.exitFullscreen();}catch(x){}}
  try{
    const r=await (await fetch('/api/live/play',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url:e.url, name:e.name, vol:plVol})})).json();
    if(r.fehler){toast('📡 '+r.fehler); return;}
    tvFilmPlayer('',e.name);                           // Fernbedienung ohne Seek-Ziel
  }catch(x){toast('📡 Kanal nicht erreichbar.');}
}
function tvTitelReihe(name,arr){return [name, arr.map(x=>({art:'titel',id:x.id,
  name:x.titel, bild:x.cover_album?('/api/cover?id='+encodeURIComponent(x.id)):(x.thumb||''),
  quer:!x.cover_album}))];}
// Bild-Kette (JB 06.08.: „welche Bilder hast du genommen? Gibt es keine
// Coverbilder in der 16:9 ansicht?"): Jellyfins „Thumb" IST das echte
// 16:9-Quer-Cover — Backdrops sind bei vielen Titeln nur automatische
// Video-Standbilder. Reihenfolge: Thumb → Backdrop → Poster.
function tvFilmReihe(name,arr){return [name, (arr||[]).map(e=>({art:'film',id:e.id,
  name:e.titel,
  bild:'/api/filme/bild?id='+encodeURIComponent(e.id)+'&art=Thumb',
  bild2:'/api/filme/bild?id='+encodeURIComponent(e.id)+'&art=Backdrop',
  bild3:'/api/filme/bild?id='+encodeURIComponent(e.id),   // Poster zuletzt
  fsk:e.fsk||'', dauer:e.laufzeit_min||0, pos:e.position_s||0,
  genres:e.genres||[], typ:e.typ||'film'}))];}
function tvReihenFuer(){
  const f=tvFilmReihen||{weiterschauen:[],top:[],neu:[],genres:{}};
  const lib=(typeof libdaten!=='undefined'&&libdaten)||[];
  const da=lib.filter(x=>x.vorhanden);
  const audio=x=>x.dateiart?x.dateiart==='audio':(x.kategorie==='MP3');
  const zuletzt=[...da].filter(x=>x.last_play).sort((a,b)=>b.last_play-a.last_play);
  const meist=[...da].filter(x=>x.plays).sort((a,b)=>b.plays-a.plays);
  const neuste=[...da].sort((a,b)=>(b.ts||0)-(a.ts||0));
  const nurFilm=a=>(a||[]).filter(e=>e.typ==='film'), nurSerie=a=>(a||[]).filter(e=>e.typ==='serie');
  // JB 06.08.: Server liefert top 30 (Bayes) — jede Ansicht filtert ihre Art
  // und schneidet erst DANN auf 10, damit der Filme-Tab eine echte Top-10 hat.
  const genresAls=(filt,n)=>Object.entries(f.genres||{}).map(([g,a])=>[g,filt(a)])
    .filter(([,a])=>a.length).slice(0,n).map(([g,a])=>tvFilmReihe(g,a));
  if(tvTab==='home')return [
    tvFilmReihe('Weiterschauen',f.weiterschauen),
    tvFilmReihe('🎞 Meine Liste',f.merkliste),
    tvFilmReihe('Top 10',(f.top||[]).slice(0,10)),
    tvFilmReihe('Neu auf dem Server',f.neu)]
    .concat(genresAls(a=>a,6))
    .concat([tvTitelReihe('❤ Lieblingssongs',da.filter(x=>x.herz).slice(0,20)),
    tvTitelReihe('Zuletzt gespielt',zuletzt.slice(0,20))]);
  if(tvTab==='filme'||tvTab==='serien'){
    // JB: „Wo sind eigentlich die restlichen Filme von René?" — die Reihen
    // deckeln bei 10–15; hier kommt der GANZE Katalog als A–Z-Raster dazu.
    const filt=tvTab==='filme'?nurFilm:nurSerie;
    const kopf=[tvFilmReihe('Top 10',filt(f.top).slice(0,10))].concat(genresAls(filt,99));
    if(tvKatalog===null){tvKatalogLaden(); return kopf;}
    const alle=tvKatalog.filter(e=>e.typ===(tvTab==='filme'?'film':'serie'))
      .sort((a,b)=>(a.titel||'').localeCompare(b.titel||'','de'));
    const azReihe=tvFilmReihe(`Alle von A bis Z (${alle.length})`,alle);
    azReihe[2]='wrap';                                 // Raster statt Band
    return kopf.concat([azReihe]);
  }
  if(tvTab==='neu')return [tvFilmReihe('Neu auf dem Server',f.neu),
    tvFilmReihe('Top 10',(f.top||[]).slice(0,10))];
  if(tvTab==='live'){
    const gr={};
    (tvLive||[]).forEach(k=>{(gr[k.gruppe||'Sender']=gr[k.gruppe||'Sender']||[]).push(k);});
    return Object.entries(gr).slice(0,8).map(([g,ks])=>[g, ks.slice(0,25).map(k=>({
      art:'live', name:k.name, url:k.url, bild:k.logo||'', quer:true}))]);
  }
  if(tvTab==='herz')return [tvFilmReihe('🎞 Meine Liste',f.merkliste),
    tvWunschReihe('⏳ Meine Wünsche',tvWuensche||[]),
    tvTitelReihe('❤ Lieblingssongs',da.filter(x=>x.herz))];
  if(tvTab==='yt')return [tvTitelReihe('Zuletzt geladen',neuste.filter(x=>!audio(x)).slice(0,20)),
    tvTitelReihe('Zuletzt gespielt',zuletzt.filter(x=>!audio(x)).slice(0,20)),
    tvTitelReihe('Meistgespielt',meist.filter(x=>!audio(x)).slice(0,20))];
  if(tvTab==='musik')return [tvTitelReihe('❤ Lieblingssongs',da.filter(x=>x.herz&&audio(x))),
    tvTitelReihe('Meistgespielt',meist.filter(audio).slice(0,20)),
    tvTitelReihe('Zuletzt gespielt',zuletzt.filter(audio).slice(0,20))];
  if(tvTab==='suche'){
    const q=(document.getElementById('tv-suche')||{value:''}).value.trim().toLowerCase();
    if(!q)return [];
    const filme=[...(f.top||[]),...(f.neu||[]),...[].concat(...Object.values(f.genres||{}))];
    const gesehen=new Set(); const treffF=filme.filter(e=>{if(gesehen.has(e.id))return false;
      gesehen.add(e.id); return (e.titel||'').toLowerCase().includes(q);});
    return [tvFilmReihe('Filme & Serien',treffF.slice(0,20)),
      tvTitelReihe('Deine Bibliothek',da.filter(x=>(x.titel||'').toLowerCase().includes(q)).slice(0,20)),
      tvWunschReihe('➕ Wünschen — ganzer Katalog (Enter im Suchfeld)',tvSeerrErgebnis||[])];
  }
  return [];
}
/* ---- Wünsche über Jellyseerr (Teilprojekt 4) ------------------------------
   Enter im Suchfeld fragt Renés Jellyseerr (dahinter Radarr/Sonarr) — die
   Treffer zeigen ehrlich ihren Stand: ✔ da · ◐ teils · ⏳ kommt · ➕ wünschbar.
   Enter auf ➕ stellt den Wunsch (Serien: alle Staffeln). Bewusst NUR auf
   Enter, nicht je Tastendruck — wir hämmern nicht auf Renés Server. */
let tvSeerrErgebnis=null, tvWuensche=null;
function tvWunschReihe(name,arr){
  const BADGE={da:'✔ ',teils:'◐ ',kommt:'⏳ ','':'➕ '};
  return [name, (arr||[]).map(e=>({art:'seerr', tmdb:e.tmdb, typ:e.typ, status:e.status,
    id:e.id||'', name:(BADGE[e.status]||'')+e.titel+(e.jahr?' ('+e.jahr+')':''),
    bild:e.poster||(e.id?('/api/filme/bild?id='+encodeURIComponent(e.id)):'')}))];
}
async function tvSeerrSuche(){
  const s=document.getElementById('tv-suche'); if(!s||!s.value.trim())return;
  toast('🔍 Frage den ganzen Katalog an…');
  try{tvSeerrErgebnis=((await (await fetch('/api/filme/wuenschen?q='+encodeURIComponent(s.value.trim()))).json())||{}).items||[];}
  catch(e){tvSeerrErgebnis=[];}
  if(!tvSeerrErgebnis.length)toast('🔍 Nichts gefunden — oder Renés Wunsch-Server ist gerade aus.');
  tvMalen();
}
async function tvWuenscheLaden(){
  try{tvWuensche=((await (await fetch('/api/filme/anfragen')).json())||{}).items||[];}
  catch(e){tvWuensche=[];}
}
async function tvAnfrage(e){
  if(e.status==='da'){toast('✔ Gibt es schon — such den Titel im Katalog.'); return;}
  if(e.status==='kommt'||e.status==='teils'){toast('⏳ Ist schon angefragt — kommt.'); return;}
  try{
    const r=await (await fetch('/api/filme/anfragen',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({tmdb:e.tmdb, typ:e.typ})})).json();
    if(r.ok){toast('➕ Wunsch gestellt — René lädt ihn, sobald er kann.'); e.status='kommt'; tvMalen();}
    else toast('➕ '+(r.fehler||'Anfrage fehlgeschlagen.'));
  }catch(x){toast('➕ Anfrage nicht erreichbar.');}
}
function tvMalen(){
  tvKopfMalen();
  const inhalt=document.getElementById('tv-inhalt');
  tvReihenListe=tvReihenFuer().filter(([,items])=>items.length);
  const suche=tvTab==='suche'
    ?`<input id="tv-suche" placeholder="Titel suchen…" oninput="tvMalen()" autocomplete="off">`:'';
  const hero=(tvTab==='home')?'<div id="tv-hero"></div>':'';
  if(!tvReihenListe.length){
    inhalt.innerHTML=hero+suche+(tvTab==='suche'?'':'<div class="tv-leer">Hier ist noch nichts — '+
      (tvTab==='herz'?'markiere Songs mit dem ♡-Herz.':'der Film-Katalog füllt sich über 🎬 Filme → ⟳ Abgleichen.')+'</div>');
  }else{
    inhalt.innerHTML=hero+suche+tvReihenListe.map((reihe,r)=>{
      const [name,items]=reihe;
      const pfeile=reihe[2]==='wrap'?'':`<button class="tv-pfeil links" onclick="tvBlaettern(this,-1)" tabindex="-1">‹</button>`+
        `<button class="tv-pfeil rechts" onclick="tvBlaettern(this,1)" tabindex="-1">›</button>`+
        `<div class="tv-seiten"></div>`;
      return `<div class="tv-reihe"><div class="tv-rtitel">${esc(name)}</div><div class="tv-band${reihe[2]==='wrap'?' wrap':''}">`+
      items.map((e,i)=>{
        const film=e.art==='film'&&e.id;
        // Netflix-Referenz (JB 06.08.): 16:9-Cover-Kette Thumb→Backdrop→
        // Poster, Fortschrittsbalken unter angefangenen Titeln.
        const fb=film&&e.bild2
          ?` onerror="if(!this.dataset.s){this.dataset.s=1;this.src='${e.bild2}'}`+
           `else if(this.dataset.s==1){this.dataset.s=2;this.src='${e.bild3}'}`+
           `else this.style.visibility='hidden'"`
          :` onerror="this.style.visibility='hidden'"`;
        const balken=(film&&e.pos>30&&e.dauer)
          ?`<div class="tv-kbalken"><div style="width:${Math.min(99,Math.round(e.pos/(e.dauer*60)*100))}%"></div></div>`:'';
        return `<div class="tv-kachel${e.quer?' quer':''}${film?' f16':''}" data-r="${r}" data-i="${i}"${film?` data-fid="${esc(e.id)}"`:''} onclick="tvKachelKlick(event,${r},${i})">`+
        (e.bild?`<img loading="lazy" src="${e.bild}"${fb}>`:'<img>')+balken+
        `<div class="tv-ktitel">${esc(e.name)}</div></div>`;}).join('')+`</div>${pfeile}</div>`;}).join('');
  }
  const s=document.getElementById('tv-suche');
  if(s&&tvTab==='suche'){const v=s.value; s.focus(); s.value=''; s.value=v;
    tvFokus={r:-1,i:Math.max(0,TV_TABS.findIndex(t=>t[0]===tvTab))};}   // Fokus gehört dem Feld
  if(tvTab==='home')tvHeroMalen();                     // Billboard lädt asynchron nach
  tvFokusMalen();
}
function tvFokusMalen(){
  document.querySelectorAll('#tv .tv-fokus').forEach(x=>x.classList.remove('tv-fokus'));
  // Suchfeld loslassen, sobald der Fokus in den Reihen ist (Fokus-Falle).
  const feld=document.getElementById('tv-suche');
  if(feld&&tvFokus.r>=0&&document.activeElement===feld)feld.blur();
  if(tvFokus.r<0)snippetAus();                         // Kopf/Hero: keine Karte
  if(tvFokus.r===-2){                                  // Hero-Billboard-Knöpfe
    const b=document.querySelector(`#tv-hero [data-hero="${Math.max(0,Math.min(1,tvFokus.i))}"]`);
    if(b){b.classList.add('tv-fokus'); b.scrollIntoView({block:'nearest',inline:'nearest'});}
    return;
  }
  if(tvFokus.r<0){                                     // Kopfleiste
    const tabs=document.querySelectorAll('#tv-kopf .tvtab');
    const b=tabs[Math.max(0,Math.min(tabs.length-1,tvFokus.i))];
    if(b){b.classList.add('tv-fokus'); b.scrollIntoView({block:'nearest',inline:'nearest'});}
    return;
  }
  const k=document.querySelector(`#tv .tv-kachel[data-r="${tvFokus.r}"][data-i="${tvFokus.i}"]`);
  if(k){k.classList.add('tv-fokus'); k.scrollIntoView({block:'nearest',inline:'nearest'});
    snippetAus(); snippetAn(k);}                       // D-Pad-Fokus = Hover (Fernbedienung)
}
function tvHeroDa(){return !!document.querySelector('#tv-hero [data-hero]');}
function tvKachelKlick(ev,r,i){
  // Netflix-Verhalten (JB-Fund: „ganz rechts … bewegt er die ganze reihe"):
  // eine ANGESCHNITTENE Kachel blättert die Reihe eine Seite weiter, nur
  // eine voll sichtbare öffnet. JB-Fund 06.08. („der mit gelber umrandung
  // macht nichts"): die FOKUS-Kachel ragte durch ihren Zoom über den
  // Band-Rand und galt als angeschnitten — am Anschlag blätterte nichts,
  // der Klick war tot. Die Toleranz rechnet den Zoom mit, und wer nicht
  // blättern KANN, öffnet.
  const k=ev.currentTarget, band=k.closest('.tv-band');
  if(band&&!band.classList.contains('wrap')){
    const kr=k.getBoundingClientRect(), br=band.getBoundingClientRect();
    const tol=8+kr.width*0.18;                       // Zoom-Überhang (scale ≤1.3)
    const kannRechts=band.scrollLeft+band.clientWidth<band.scrollWidth-4;
    const kannLinks=band.scrollLeft>4;
    if(kr.right>br.right+tol&&kannRechts){band.scrollBy({left:band.clientWidth*0.85,behavior:'smooth'}); return;}
    if(kr.left<br.left-tol&&kannLinks){band.scrollBy({left:-band.clientWidth*0.85,behavior:'smooth'}); return;}
  }
  tvWahl(r,i);
}
function tvKlonSichern(band){
  // Reihen-Anfang EINMAL hinter das Ende klonen (Kreis-Bahn).
  if(band.dataset.klon)return;
  if(!band.dataset.origBreite)band.dataset.origBreite=band.scrollWidth;
  [...band.children].forEach(k=>{
    const c=k.cloneNode(true); c.classList.remove('tv-fokus','hk-quelle');
    band.appendChild(c);});
  band.dataset.klon='1';
}
function tvBlaettern(btn,dir){
  const band=btn.parentElement&&btn.parentElement.querySelector('.tv-band');
  if(!band)return;
  // ENDLOS-KREIS NUR VORWÄRTS (JB 07.08., präzisiert: „1-2-3-4-5-1-2-…" —
  // vor dem Ende klont sich der Reihen-Anfang einmal hinten an, es geht
  // nahtlos weiter. RÜCKWÄRTS läuft es nur bis zur echten Position 1:
  // „5-4-3-2-1 und da hört es auf" — wer gerade über die Kante kam, kann
  // durch sie zurück; der stille Kreis-Schluss springt deshalb erst am
  // ENDE des Klon-Teils, nicht sofort.
  if(!band.dataset.origBreite)band.dataset.origBreite=band.scrollWidth;
  const W=+band.dataset.origBreite;
  if(dir>0&&band.scrollLeft+band.clientWidth*2>=band.scrollWidth)
    tvKlonSichern(band);
  if(dir<0&&band.scrollLeft<=8)return;                 // Position 1: kein Links-Weg
  // Kachelbündig blättern (JB 07.08.): Schritt = GANZE Kachelspalten und
  // das Ziel rastet auf eine Kachelkante — links beginnt immer eine
  // Kachel komplett, auf jeder Displaygröße.
  const k0=band.querySelector('.tv-kachel');
  const schritt=k0?(k0.getBoundingClientRect().width+8):band.clientWidth*0.85;
  const proSeite=Math.max(1,Math.floor((band.clientWidth+8)/schritt));   // letzte Kachel hat keinen Gap
  const ziel=Math.max(0,Math.round((band.scrollLeft+dir*proSeite*schritt)/schritt)*schritt);
  band.scrollTo({left:ziel,behavior:'smooth'});
  setTimeout(()=>{
    const spaet=Math.max(W, 2*W-band.clientWidth*1.5);
    if(band.scrollLeft>=spaet)band.scrollLeft-=W;      // stiller Kreis-Schluss (spät)
    tvSeitenMalen(btn.parentElement);
  },600);
}
function tvSeitenMalen(reihe){
  // Seiten-Striche oben rechts (Netflix): wie weit bin ich in der Reihe?
  // Mit Klon-Teil (Endlos-Kreis) zählt nur die ORIGINAL-Breite; die
  // Position rechnet modulo — der Kreis hat keine Enden.
  if(!reihe||!reihe.querySelector)return;
  const band=reihe.querySelector('.tv-band'), box=reihe.querySelector('.tv-seiten');
  if(!band||!box||band.classList.contains('wrap'))return;
  // JB 07.08.: passt ALLES in den Rahmen, braucht es weder Pfeile noch
  // Striche — die Reihe ist dann keine Bahn, sondern ein Regal.
  const passt=!band.dataset.klon&&band.scrollWidth<=band.clientWidth+4;
  reihe.querySelectorAll('.tv-pfeil').forEach(p=>p.style.display=passt?'none':'');
  if(passt){box.innerHTML=''; return;}
  // Am echten Anfang gibt es keinen Links-Weg (JB: „Erste Position geht
  // nicht nach links") — der ◀ verschwindet dort wie bei Netflix.
  const links=reihe.querySelector('.tv-pfeil.links');
  if(links)links.style.display=band.scrollLeft<=8?'none':'';
  const W=+(band.dataset.origBreite||band.scrollWidth);
  const n=Math.ceil(W/Math.max(1,band.clientWidth));
  if(n<2||n>24){box.innerHTML=''; return;}
  const max=Math.max(1,W-band.clientWidth);
  const pos=Math.min(band.scrollLeft%W,max);
  const akt=Math.min(n-1,Math.round((pos/max)*(n-1)));
  box.innerHTML=Array.from({length:n},(_,i)=>`<span${i===akt?' class="an"':''}></span>`).join('');
}
function tvWahl(r,i){
  snippetAus();                                        // Karte nie hinter Info/Player
  const e=(tvReihenListe[r]||[])[1]&&tvReihenListe[r][1][i]; if(!e)return;
  if(e.art==='live'){tvLivePlay(e); return;}           // 📡 Kanal (JB-Go)
  if(e.art==='seerr'){                                 // Wunsch-Kachel (Teilprojekt 4)
    if(e.status==='da'&&e.id)tvInfo(e.id);             // schon da + im Spiegel -> Info
    else tvAnfrage(e);
    return;
  }
  if(e.art==='film'){tvInfo(e.id);}                    // Netflix-Muster: erst die Info-Seite
  else{tvZu(); playerPlay([e.id]);}
}
/* ---- Hero-Billboard + More-Info (JB-Go: „weiter mit dem tv feinschliff,
   hero und more-info seite") ---------------------------------------------- */
let tvHeroId='', tvHeroDaten=null, tvInfoOffen=false, tvInfoFokus={r:0,i:0}, tvInfoMehr=[], tvInfoId='';
let tvInfoStapel=[];                                   // „Mehr wie das"-Rückweg (Netflix)
function tvMetaZeile(d){
  const teile=[];
  if(d.jahr)teile.push(d.jahr);
  if(d.fsk)teile.push(esc(d.fsk));
  if(d.laufzeit_min)teile.push(d.laufzeit_min+' min');
  if(d.rating)teile.push('★ '+(+d.rating).toFixed(1));
  if(d.imdb_rating)teile.push('IMDb '+esc(d.imdb_rating));
  if(d.metacritic)teile.push('MC '+esc(d.metacritic));
  if(d.tomatometer)teile.push('🍅 '+esc(d.tomatometer));
  return teile.join('  ·  ');
}
async function tvHeroMalen(){
  const box=document.getElementById('tv-hero'); if(!box)return;
  const f=tvFilmReihen||{};
  const kand=(f.weiterschauen&&f.weiterschauen[0])||(f.top&&f.top[0])||(f.neu&&f.neu[0]);
  if(!kand){box.style.display='none'; return;}
  tvHeroId=kand.id;
  let d=kand;
  try{d=await (await fetch('/api/filme/detail?id='+encodeURIComponent(kand.id))).json();}catch(e){}
  tvHeroDaten=d;                                       // Meta für den Player (Hero-Direktstart)
  if(!document.getElementById('tv-hero'))return;       // Tab inzwischen gewechselt
  box.innerHTML=
    `<img class="hero-bg" src="/api/filme/bild?id=${encodeURIComponent(kand.id)}&art=Backdrop" `+
      `onerror="this.onerror=null;this.src='/api/filme/bild?id=${encodeURIComponent(kand.id)}'">`+
    `<div class="hero-text"><div class="hero-titel">${esc(d.titel||'')}</div>`+
    `<div class="hero-meta">${tvMetaZeile(d)}</div>`+
    `<div class="hero-besch">${esc(d.beschreibung||'')}</div>`+
    `<div class="hero-btns">`+
      (kand.typ==='serie'
        ?`<button class="tv-btn" data-hero="0" onclick="tvInfo('${esc(kand.id)}')">▶ Weiterschauen</button>`
        :`<button class="tv-btn" data-hero="0" onclick="filmePlay('${esc(kand.id)}')">▶ Abspielen</button>`)+
      `<button class="tv-btn zart" data-hero="1" onclick="tvInfo('${esc(kand.id)}')">ℹ Mehr Infos</button>`+
    `</div></div>`;
}
let tvInfoDaten=null, tvInfoStaffel=0;                 // {d, mw, eps} der offenen Info
async function tvInfo(id){
  // „Mehr wie das"-Rückweg: der vorige Film kommt auf den Stapel — Esc
  // führt erst zu IHM zurück, dann erst ganz raus (Netflix-Verhalten).
  if(tvInfoOffen&&tvInfoId&&tvInfoId!==id)tvInfoStapel.push(tvInfoId);
  tvInfoId=id; tvInfoOffen=true; tvInfoFokus={r:0,i:0}; tvInfoDaten=null; tvInfoStaffel=0;
  // Die Detailseite gibt es auch OHNE TV-Modus (JB 05.08.: Klick im
  // 🎬-Fenster öffnet sie) — dann übernimmt tvKey nur für sie.
  document.addEventListener('keydown',tvKey,true);
  const el=document.getElementById('tv-info');
  // Fullscreen-Falle (JB-Fund): im Fernsehmodus rendert der Browser NUR das
  // Vollbild-Element (#tv) samt Kindern — als Geschwister unter <body>
  // erschien die Info erst NACH dem Vollbild („öffnet sich im Browser").
  // Darum die Seite dorthin umhängen, wo gerade gerendert wird.
  const ziel=document.fullscreenElement||document.body;
  if(el.parentNode!==ziel)ziel.appendChild(el);
  el.style.display='flex';
  el.innerHTML='<div class="info-body" style="font-size:24px;padding:60px">Lade…</div>';
  let d=null, mw=[], eps=[];
  try{d=await (await fetch('/api/filme/detail?id='+encodeURIComponent(id)+'&profil='+encodeURIComponent(tvProfil()))).json();}catch(e){}
  try{mw=((await (await fetch('/api/filme/mehrwie?id='+encodeURIComponent(id))).json())||{}).items||[];}catch(e){}
  if(d&&d.typ==='serie'){                              // Staffeln + Folgen (JB-Go)
    try{eps=((await (await fetch('/api/filme/episoden?id='+encodeURIComponent(id))).json())||{}).items||[];}catch(e){}
  }
  if(!tvInfoOffen||tvInfoId!==id)return;               // inzwischen geschlossen/weiter
  if(!d||d.fehler){el.innerHTML='<div class="info-body" style="padding:60px">Film nicht gefunden. (Esc = zurück)</div>'; return;}
  tvInfoDaten={d,mw,eps}; tvInfoMehr=mw;
  const st=[...new Set(eps.map(e=>e.staffel))];
  tvInfoStaffel=st.includes(1)?1:(st[0]||0);
  // Weiterschauen-Logik: erst die angefangene Folge, sonst die erste ungesehene
  const weiter=eps.find(e=>e.position_s>0&&!e.gesehen)||eps.find(e=>!e.gesehen);
  if(weiter)tvInfoStaffel=weiter.staffel||tvInfoStaffel;
  tvInfoMalen();
}
function tvSerienPlay(){
  // ▶ auf einer Serie = Netflix-Verhalten: angefangene Folge, sonst erste
  // ungesehene, sonst die allererste.
  const eps=(tvInfoDaten&&tvInfoDaten.eps)||[];
  const e=eps.find(x=>x.position_s>0&&!x.gesehen)||eps.find(x=>!x.gesehen)||eps[0];
  if(e)filmePlay(e.id); else toast('🎬 Keine Folgen gefunden.');
}
async function tvMerk(id){
  try{
    const r=await (await fetch('/api/filme/merk?profil='+encodeURIComponent(tvProfil()),
      {method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({id})})).json();
    if(tvInfoDaten)tvInfoDaten.d.gemerkt=!!r.an;
    toast(r.an?'🎞 Auf deiner Liste.':'🎞 Von der Liste genommen.');
    tvInfoMalen();
    tvFilmReihen=null; tvLadenStill();                 // Home-Reihe frisch ziehen
  }catch(e){toast('🎞 Merken fehlgeschlagen.');}
}
async function tvLadenStill(){
  try{tvFilmReihen=await (await fetch('/api/filme/reihen?profil='+encodeURIComponent(tvProfil()))).json();}catch(e){}
}
function tvStaffel(n){tvInfoStaffel=n; tvInfoFokus={r:1,i:0}; tvInfoMalen();}
function tvQualitaet(h){return h>=2000?'4K':h>=1000?'HD':h>=720?'720p':'';}   // 1040 = anamorphes HD
function tvTon(d){
  const k=d.audio_kanaele||0;
  const kanal=k>=8?'7.1':k>=6?'5.1':k===2?'Stereo':'';
  const spr=(d.audio_sprachen||[]).join(', ');
  return [spr,kanal,(d.audio_codec||'').toUpperCase()].filter(Boolean).join(' · ');
}
function tvInfoMalen(){
  // Netflix-/Disney-Muster am Fernseher (JBs Liste 05.08. = exakt deren
  // Detailseite): Titel groß, Fortschrittsbalken mit dem Spot, Weiterschauen/
  // Von vorne, ＋ Liste, Meta-Badges (FSK/Qualität), Klappentext, Besetzung/
  // Genres/Ton/Untertitel, Staffeln, Mehr wie das, Trailer & mehr, und unten
  // der „Über“-Block (Regie · Besetzung · Drehbuch · Genres · Dieser Film
  // ist · Altersfreigabe).
  const el=document.getElementById('tv-info');
  if(!el||!tvInfoDaten)return;
  const {d,mw,eps}=tvInfoDaten, id=tvInfoId;
  const staffeln=[...new Set(eps.map(e=>e.staffel))];
  const folgen=eps.filter(e=>e.staffel===tvInfoStaffel);
  const dauerS=(d.laufzeit_min||0)*60;
  const prozent=(d.position_s>0&&dauerS)?Math.min(99,Math.round(d.position_s/dauerS*100)):0;
  const posMin=Math.round((d.position_s||0)/60);
  const q=tvQualitaet(d.hoehe), ton=tvTon(d), subs=(d.sub_sprachen||[]).join(', ');
  const badges=[d.jahr||'', d.fsk?`<span class="info-badge">${esc(d.fsk)}</span>`:'',
    d.laufzeit_min?d.laufzeit_min+' min':'', q?`<span class="info-badge">${q}</span>`:'',
    d.rating?'★ '+(+d.rating).toFixed(1):'', d.imdb_rating?'IMDb '+esc(d.imdb_rating):'',
    d.tomatometer?'🍅 '+esc(d.tomatometer):''].filter(Boolean).join('<span class="info-punkt">·</span>');
  const knoepfe=(d.typ==='serie'
    ?`<button class="tv-btn" data-info="0" onclick="tvSerienPlay()">▶ Weiterschauen</button>`
    :(d.position_s>30
      ?`<button class="tv-btn" data-info="0" onclick="filmePlay('${esc(id)}',${d.position_s})">▶ Weiterschauen</button>`+
       `<button class="tv-btn zart" data-info="1" onclick="filmePlay('${esc(id)}',0)">↻ Von vorne</button>`
      :`<button class="tv-btn" data-info="0" onclick="filmePlay('${esc(id)}')">▶ Abspielen</button>`))+
    `<button class="tv-btn zart" data-info="2" onclick="tvMerk('${esc(id)}')">${d.gemerkt?'✓ Gemerkt':'＋ Meine Liste'}</button>`;
  const dieserFilm=d.tagline||((d.genres||[]).slice(0,3).join(' · '));
  const querBild=(eid)=>`<img loading="lazy" src="/api/filme/bild?id=${encodeURIComponent(eid)}&art=Backdrop" `+
    `onerror="this.onerror=null;this.src='/api/filme/bild?id=${encodeURIComponent(eid)}'">`;
  el.innerHTML=`<div class="info-karte">`+
    `<div class="info-kopf">${querBild(id)}`+
      `<button class="info-x" data-info="9" onclick="tvInfoZu()" title="Schließen (Esc)">✕</button>`+
      `<div class="info-kopf-inhalt">`+
        `<div class="info-titel">${esc(d.titel||'')}</div>`+
        (prozent?`<div class="info-progresswrap"><div class="info-progress"><div style="width:${prozent}%"></div></div>`+
          `<span class="info-rest">${posMin} von ${d.laufzeit_min} min</span></div>`:'')+
        `<div class="info-btns info-kopfzeile">${knoepfe}</div>`+
      `</div></div>`+
    `<div class="info-body">`+
      `<div class="info-spalten"><div>`+
        `<div class="info-meta">${badges}</div>`+
        (d.tagline?`<div class="info-tagline">„${esc(d.tagline)}“</div>`:'')+
        `<div class="info-besch">${esc(d.beschreibung||'')}</div>`+
      `</div><div>`+
        (d.cast&&d.cast.length?`<div class="info-neben"><b>Besetzung:</b> ${esc(d.cast.slice(0,5).join(', '))}</div>`:'')+
        (d.genres&&d.genres.length?`<div class="info-neben"><b>Genres:</b> ${esc(d.genres.join(', '))}</div>`:'')+
        (dieserFilm?`<div class="info-neben"><b>${d.typ==='serie'?'Diese Serie ist':'Dieser Film ist'}:</b> ${esc(dieserFilm)}</div>`:'')+
        (ton?`<div class="info-neben"><b>Ton:</b> ${esc(ton)}</div>`:'')+
        (subs?`<div class="info-neben"><b>Untertitel:</b> ${esc(subs)}</div>`:'')+
      `</div></div>`+
      (staffeln.length?`<div class="tv-rtitel" style="margin-top:14px">Staffeln</div><div class="tv-band">`+
        staffeln.map(n=>`<button class="tv-btn zart${n===tvInfoStaffel?' akt':''}" data-st="${n}" onclick="tvStaffel(${n})">Staffel ${n||'?'}</button>`).join('')+`</div>`+
        `<div class="tv-band">`+folgen.map((e,i)=>
          `<div class="tv-kachel quer" data-ep="${i}" onclick="filmePlay('${esc(e.id)}',${e.position_s>30&&!e.gesehen?e.position_s:0})" title="${esc(e.titel)}">`+
          `<img loading="lazy" src="/api/filme/bild?id=${encodeURIComponent(e.id)}" onerror="this.style.visibility='hidden'">`+
          `<div class="tv-ktitel">${e.gesehen?'✓ ':''}F${e.folge} · ${esc(e.titel)}${e.position_s>0&&!e.gesehen?' ⏸':''}</div></div>`).join('')+`</div>`:'')+
      (mw.length?`<div class="tv-rtitel" style="margin-top:16px">Mehr wie das</div><div class="info-grid">`+
        mw.slice(0,9).map((e,i)=>`<div class="tv-kachel" data-mw="${i}" onclick="tvInfo('${esc(e.id)}')">`+
          querBild(e.id)+(e.laufzeit_min?`<span class="tv-dauer">${Math.floor(e.laufzeit_min/60)}h ${e.laufzeit_min%60}m</span>`:'')+
          `<div class="tv-ktitel">${esc(e.titel)}</div></div>`).join('')+`</div>`:'')+
      (d.trailer&&d.trailer.length?`<div class="tv-rtitel" style="margin-top:16px">Trailer & mehr</div><div class="info-grid">`+
        d.trailer.map((t,i)=>`<div class="tv-kachel" data-trl="${i}" onclick="window.open('https://www.youtube.com/watch?v=${esc(t.key)}','_blank')" title="${esc(t.name)}">`+
          `<img loading="lazy" src="https://i.ytimg.com/vi/${esc(t.key)}/mqdefault.jpg" style="aspect-ratio:16/9;height:auto" onerror="this.style.visibility='hidden'">`+
          `<div class="tv-ktitel">▶ ${esc(t.name)}</div></div>`).join('')+`</div>`:'')+
      `<div class="info-ueber"><div class="tv-rtitel">Über ${esc(d.titel||'')}</div>`+
        ((d.regie||[]).length?`<div class="info-neben"><b>Regie:</b> ${esc(d.regie.join(', '))}</div>`:'')+
        (d.cast&&d.cast.length?`<div class="info-neben"><b>Besetzung:</b> ${esc(d.cast.join(', '))}</div>`:'')+
        ((d.drehbuch||[]).length?`<div class="info-neben"><b>Drehbuch:</b> ${esc(d.drehbuch.join(', '))}</div>`:'')+
        (d.genres&&d.genres.length?`<div class="info-neben"><b>Genres:</b> ${esc(d.genres.join(', '))}</div>`:'')+
        (dieserFilm?`<div class="info-neben"><b>${d.typ==='serie'?'Diese Serie ist':'Dieser Film ist'}:</b> ${esc(dieserFilm)}</div>`:'')+
        (d.fsk?`<div class="info-neben"><b>Altersfreigabe:</b> <span class="info-badge">${esc(d.fsk)}</span></div>`:'')+
      `</div>`+
    `</div></div>`;
  tvInfoFokusMalen();
}
function tvInfoZu(){
  if(tvInfoStapel.length){tvInfo(tvInfoStapel.pop()); return;}   // erst zurückblättern
  tvInfoOffen=false; tvInfoDaten=null;
  const el=document.getElementById('tv-info'); if(el){el.style.display='none'; el.innerHTML='';}
  const tv=document.getElementById('tv');              // ohne TV: Tasten wieder frei
  if(!tv||tv.style.display==='none')document.removeEventListener('keydown',tvKey,true);
}
function tvInfoEbenen(){
  // Generische Fokus-Zeilen der Info-Seite: Knöpfe → Staffeln → Folgen →
  // Mehr-wie. Leere Zeilen fallen raus — die Navigation bleibt lückenlos.
  return [
    // Sortiert nach data-info: der ✕ (9) steht im DOM zuerst (Kopf), soll
    // aber der LETZTE Fokus der Knopf-Zeile sein — Start ist ▶.
    [...document.querySelectorAll('#tv-info [data-info]')].sort((a,b)=>(+a.dataset.info)-(+b.dataset.info)),
    [...document.querySelectorAll('#tv-info [data-st]')],
    [...document.querySelectorAll('#tv-info [data-ep]')],
    [...document.querySelectorAll('#tv-info [data-mw]')],
    [...document.querySelectorAll('#tv-info [data-trl]')],
  ].filter(a=>a.length);
}
function tvInfoFokusMalen(){
  document.querySelectorAll('#tv-info .tv-fokus').forEach(x=>x.classList.remove('tv-fokus'));
  const eb=tvInfoEbenen();
  if(!eb.length)return;
  tvInfoFokus.r=Math.max(0,Math.min(eb.length-1,tvInfoFokus.r));
  tvInfoFokus.i=Math.max(0,Math.min(eb[tvInfoFokus.r].length-1,tvInfoFokus.i));
  const ziel=eb[tvInfoFokus.r][tvInfoFokus.i];
  if(ziel){ziel.classList.add('tv-fokus'); ziel.scrollIntoView({block:'nearest',inline:'nearest'});}
}
function tvKey(ev){
  const tv=document.getElementById('tv');
  const tvOffen=tv&&tv.style.display!=='none';
  if(!tvOffen&&!tvInfoOffen&&!tvDialogOffen&&!tvpOffen)return;  // Overlays auch ohne TV
  // Film-Fernbedienung offen? Sie hat Vorrang vor allen Ebenen.
  if(tvpOffen){
    let getan=true;
    tvpWach();                                         // jede Taste weckt die Leiste
    const pan=document.getElementById('tvp-panel');
    if(pan&&pan.style.display!=='none'){
      // Offenes Settings-Panel (Nachtprüfung 06.08.: Esc beendete den GANZEN
      // Film, Pfeile seekten blind weiter): Pfeile wandern durch die Knöpfe,
      // Enter wählt, Esc schließt NUR das Panel.
      const kn=[...pan.querySelectorAll('.tvpp-knopf')];
      if(ev.key==='Escape'||ev.key==='Backspace')pan.style.display='none';
      else if(ev.key==='ArrowDown'||ev.key==='ArrowRight'){tvppFokus=Math.min(kn.length-1,tvppFokus+1); tvppFokusMalen(kn);}
      else if(ev.key==='ArrowUp'||ev.key==='ArrowLeft'){tvppFokus=Math.max(0,tvppFokus-1); tvppFokusMalen(kn);}
      else if(ev.key==='Enter'){const z=kn[Math.max(0,Math.min(kn.length-1,tvppFokus))]; if(z)z.click();}
      else getan=false;
      if(getan){ev.preventDefault(); ev.stopPropagation();}
      return;
    }
    if(ev.key==='Escape')filmStopp();
    else if(ev.key===' '||ev.key==='Enter'){tvpBefehl('toggle'); setTimeout(tvpTick,300);}
    else if(ev.key==='ArrowLeft')tvpRel(-10);
    else if(ev.key==='ArrowRight')tvpRel(10);
    else if(ev.key==='ArrowUp'){plbVol(Math.min(100,plVol+5)); tvpBefehl('vol',{wert:plVol});}
    else if(ev.key==='ArrowDown'){plbVol(Math.max(0,plVol-5)); tvpBefehl('vol',{wert:plVol});}
    else if(ev.key==='s'||ev.key==='S')tvpPanel('spuren');   // Sofa-Weg zu den Settings
    else getan=false;
    if(getan){ev.preventDefault(); ev.stopPropagation();}
    return;
  }
  // Profil-Dialog: eigene Ebenen (Feld → Emojis → Knöpfe), Tippen bleibt frei.
  if(tvDialogOffen){
    let getan=true;
    const imFeld=ev.target&&ev.target.id==='tv-dlg-name';
    if(ev.key==='Escape')tvDialogZu();
    else if(imFeld&&ev.key==='Enter')tvDlgAnlegen();
    else if(imFeld&&ev.key!=='ArrowDown'){getan=false;}          // tippen lassen
    else if(ev.key==='ArrowDown'){tvDlgFokus={r:Math.min(2,(imFeld?0:tvDlgFokus.r)+1),i:0}; tvDlgFokusMalen();}
    else if(ev.key==='ArrowUp'){tvDlgFokus={r:Math.max(0,tvDlgFokus.r-1),i:0}; tvDlgFokusMalen();}
    else if(ev.key==='ArrowLeft'){tvDlgFokus.i=Math.max(0,tvDlgFokus.i-1); tvDlgFokusMalen();}
    else if(ev.key==='ArrowRight'){tvDlgFokus.i=tvDlgFokus.i+1; tvDlgFokusMalen();}
    else if(ev.key==='Enter'){
      const zeile=tvDlgFokus.r===1?document.querySelectorAll('#tv-dialog .emo')
                                  :document.querySelectorAll('#tv-dialog [data-dlg]');
      const z=zeile[Math.max(0,Math.min(zeile.length-1,tvDlgFokus.i))]; if(z)z.click();
    }
    else getan=false;
    if(getan){ev.preventDefault(); ev.stopPropagation();}
    return;
  }
  // Info-Seite offen? Dann navigiert die Fernbedienung DORT (eigene Ebene).
  if(tvInfoOffen){
    let getan=true;
    const eb=tvInfoEbenen();
    if(ev.key==='Escape'||ev.key==='Backspace'){
      if(filmLaeuft())filmStopp();                     // Esc beendet erst den FILM
      else tvInfoZu();
    }
    else if(ev.key==='ArrowLeft')tvInfoFokus.i=Math.max(0,tvInfoFokus.i-1);
    else if(ev.key==='ArrowRight')tvInfoFokus.i=tvInfoFokus.i+1;   // Malen klemmt
    else if(ev.key==='ArrowDown')tvInfoFokus={r:tvInfoFokus.r+1,i:0};
    else if(ev.key==='ArrowUp')tvInfoFokus={r:Math.max(0,tvInfoFokus.r-1),i:0};
    else if(ev.key==='Enter'){
      const zeile=eb[Math.max(0,Math.min(eb.length-1,tvInfoFokus.r))]||[];
      const el2=zeile[Math.max(0,Math.min(zeile.length-1,tvInfoFokus.i))];
      if(el2)el2.click();
    }
    else getan=false;
    if(getan){ev.preventDefault(); ev.stopPropagation(); if(tvInfoOffen)tvInfoFokusMalen();}
    return;
  }
  if(tvProfilModus){                                   // „Wer schaut?"-Ebene
    let getan=true;
    const alle=document.querySelectorAll('#tv [data-pr]');
    if(ev.key==='ArrowLeft')tvFokus.i=Math.max(0,tvFokus.i-1);
    else if(ev.key==='ArrowRight')tvFokus.i=Math.min(alle.length-1,tvFokus.i+1);
    else if(ev.key==='Enter'){const z=alle[Math.max(0,Math.min(alle.length-1,tvFokus.i))]; if(z)z.click();}
    else if(ev.key==='Escape'||ev.key==='Backspace')tvZu();
    else getan=false;
    if(getan){ev.preventDefault(); ev.stopPropagation(); if(tvProfilModus)tvProfilFokusMalen();}
    return;
  }
  if(ev.target&&ev.target.id==='tv-suche'){
    // Nachtprüfung 06.08. („Fokus-Falle"): das Feld hielt den DOM-Fokus für
    // immer — Enter suchte statt zu öffnen, Ergebnisse waren per D-Pad
    // unerreichbar. Jetzt: Pfeil runter/hoch VERLÄSST das Feld (blur),
    // danach navigiert das D-Pad normal und Enter öffnet die Kachel.
    if(ev.key==='Enter'){ev.preventDefault(); ev.stopPropagation(); tvSeerrSuche(); return;}
    if(['ArrowDown','ArrowUp','Escape'].includes(ev.key))ev.target.blur();
    else return;                                       // tippen lassen
  }
  const tabs=TV_TABS.length;
  const reihe=()=> (tvReihenListe[tvFokus.r]||[[],[]])[1]||[];
  let getan=true;
  if(ev.key==='Escape'||ev.key==='Backspace'){
    if(ev.key==='Escape'&&filmLaeuft())filmStopp();    // Esc beendet erst den FILM
    else if(tvFokus.r>=0&&ev.key==='Backspace'){tvFokus={r:-1,i:TV_TABS.findIndex(t=>t[0]===tvTab)};}
    else tvZu(); }
  else if(ev.key==='ArrowLeft'){ if(tvFokus.r===-2)tvFokus.i=Math.max(0,tvFokus.i-1); else tvFokus.i=Math.max(0,tvFokus.i-1); }
  else if(ev.key==='ArrowRight'){ if(tvFokus.r===-2)tvFokus.i=Math.min(1,tvFokus.i+1); else if(tvFokus.r<0)tvFokus.i=Math.min(tabs-1,tvFokus.i+1); else tvFokus.i=Math.min(reihe().length-1,tvFokus.i+1); }
  else if(ev.key==='ArrowUp'){
    if(tvFokus.r===0){tvFokus=tvHeroDa()?{r:-2,i:0}:{r:-1,i:TV_TABS.findIndex(t=>t[0]===tvTab)};}
    else if(tvFokus.r===-2){tvFokus={r:-1,i:TV_TABS.findIndex(t=>t[0]===tvTab)};}
    else if(tvFokus.r>0){tvFokus.r--; tvFokus.i=Math.min(tvFokus.i,Math.max(0,(tvReihenListe[tvFokus.r][1]||[]).length-1));}
  }
  else if(ev.key==='ArrowDown'){
    if(tvFokus.r===-1){tvFokus=tvHeroDa()?{r:-2,i:0}:{r:0,i:0};}
    else if(tvFokus.r===-2){tvFokus={r:0,i:0};}
    else if(tvFokus.r<tvReihenListe.length-1){tvFokus.r++; tvFokus.i=Math.min(tvFokus.i,Math.max(0,(tvReihenListe[tvFokus.r][1]||[]).length-1));}
  }
  else if(ev.key==='Enter'){
    if(tvFokus.r===-2){const b=document.querySelector(`#tv-hero [data-hero="${tvFokus.i}"]`); if(b)b.click();}
    else if(tvFokus.r<0){tvTabWahl(TV_TABS[Math.max(0,tvFokus.i)][0]); tvFokus={r:-1,i:tvFokus.i};}
    else tvWahl(tvFokus.r,tvFokus.i);
  }
  else getan=false;
  if(getan){ev.preventDefault(); ev.stopPropagation(); tvFokusMalen();}
}
function plbPip(){                                     // natives Bild-in-Bild (JB 21.07.)
  const el=document.getElementById('pl-el');
  if(!el||el.tagName!=='VIDEO'){toast('Bild-in-Bild geht nur bei Videos.');return;}
  const istFirefox=/firefox/i.test(navigator.userAgent);
  try{
    if(document.pictureInPictureElement)document.exitPictureInPicture();
    else if(el.requestPictureInPicture&&document.pictureInPictureEnabled!==false)el.requestPictureInPicture();
    else if(istFirefox)toast('Firefox: nutze den kleinen Bild-in-Bild-Knopf, der beim Überfahren am Video erscheint (die Schnittstelle ist per Knopf gesperrt).');
    else toast('Dein Browser kann kein Bild-in-Bild.');
  }catch(e){
    toast(istFirefox?'Firefox: nutze den eigenen Bild-in-Bild-Knopf am Video (rechts am Rand beim Überfahren).'
                    :'Bild-in-Bild nicht möglich.');
  }
}
/* ---- Wiedergabe-Merker (Build 102, JB): je Titel die letzte Stelle merken.
   Gelber Strich auf der Leiste zeigt sie, KLICK springt hin — standardmäßig
   wirkt der Merker NICHT (jeder Titel startet normal bei 0). Anfang (<20 s)
   und fast-Ende löschen den Merker; Deckel 800 Einträge (älteste fliegen). */
let _posMerk={}; try{_posMerk=JSON.parse(localStorage.getItem('ytdl_pos_v1'))||{};}catch(e){}
let _posMerkTs=0;
function posMerken(){
  const el=document.getElementById('pl-el'); const k=aktKey();
  if(!el||!k||!isFinite(el.duration)||!el.duration)return;
  const t=el.currentTime;
  // Build 104 (JB-Fund „sehe den Strich nicht"): am ANFANG (<20 s) den Merker
  // IN RUHE lassen — nach jedem Titelwechsel steht man zwangslaeufig bei 0,
  // und der 5-s-Takt loeschte den Merker genau dann, bevor man ihn je sah.
  // Geloescht wird nur noch am fast-Ende (durchgehoert = Merker sinnlos).
  if(t>20&&t<el.duration-20)_posMerk[k]={t:Math.floor(t),ts:Date.now()};
  else if(t>=el.duration-20)delete _posMerk[k];
  const keys=Object.keys(_posMerk);
  if(keys.length>800)keys.sort((a,b)=>(_posMerk[a].ts||0)-(_posMerk[b].ts||0))
    .slice(0,keys.length-800).forEach(x=>delete _posMerk[x]);
  try{localStorage.setItem('ytdl_pos_v1',JSON.stringify(_posMerk));}catch(e){}
}
window.addEventListener('beforeunload',posMerken);
function posMerkerMalen(){
  const seek=document.getElementById('plb-seek'); const wrap=seek&&seek.parentElement;
  if(!wrap)return;
  let m=document.getElementById('plb-merker');
  const el=document.getElementById('pl-el'); const k=aktKey();
  const eintrag=k&&_posMerk[k];
  // Gerät VLC (JB: identische Leiste): Dauer/Position aus dem 1-s-Status.
  const vlc=vlcAktiv();
  const dauer=vlc?vlcDauerLetzte:(el&&isFinite(el.duration)?el.duration:0);
  const pos=vlc?vlcPosLetzte:(el?el.currentTime:0);
  const nah=eintrag&&dauer&&Math.abs(pos-eintrag.t)<3;   // Playhead klebt drauf -> ausblenden
  if(!eintrag||!dauer||nah){if(m)m.remove();return;}
  if(!m){
    m=document.createElement('div'); m.id='plb-merker'; m.className='plb-merker';
    m.addEventListener('click',e=>{e.stopPropagation();
      const el2=document.getElementById('pl-el'), k2=aktKey();
      if(!k2||!_posMerk[k2])return;
      const ziel=Math.max(0,_posMerk[k2].t-3);           // 3 s Anlauf (Build 105)
      if(vlcAktiv()){vlcPosLetzte=ziel; vlcBefehl('seek',{wert:ziel});}
      else if(el2)el2.currentTime=ziel;
      toast('↦ zurück zu '+zeit(_posMerk[k2].t)+' (mit Anlauf)');});
    wrap.appendChild(m);
  }
  const sr=seek.getBoundingClientRect(), wr=wrap.getBoundingClientRect();
  m.style.left=(sr.left-wr.left+sr.width*(eintrag.t/dauer))+'px';
  m.title='Zuletzt warst du hier: '+zeit(eintrag.t)+' — Klick springt hin';
}
function plbTick(){                                    // Position/Zeit der Leiste nachführen
  const el=document.getElementById('pl-el'), s=document.getElementById('plb-seek'),
        t0=document.getElementById('plb-t0'), t1=document.getElementById('plb-t1');
  if(!s||!t0||!t1)return;
  if(Date.now()-_posMerkTs>5000){_posMerkTs=Date.now(); posMerken();}   // Merker-Takt (Build 102)
  posMerkerMalen();
  if(vlcAktiv()){                                     // Gerät VLC: Werte aus dem 1-s-Status
    if(!vlcDauerLetzte){s.value=0;t0.textContent='0:00';t1.textContent='0:00';return;}
    if(!plbSeekAktiv){s.value=Math.round(vlcPosLetzte/vlcDauerLetzte*1000);t0.textContent=zeit(vlcPosLetzte);}
    t1.textContent=zeit(vlcDauerLetzte);
    return;
  }
  if(!el||!el.duration){s.value=0;t0.textContent='0:00';t1.textContent='0:00';return;}
  if(!plbSeekAktiv){s.value=Math.round(el.currentTime/el.duration*1000);t0.textContent=zeit(el.currentTime);}
  t1.textContent=zeit(el.duration);
}
setInterval(plbTick,500);
function speedMenu(ev){                                // Geschwindigkeit als Liste (Haken = aktiv)
  ev.stopPropagation();
  kmListe(kontextMenuBauen(ev,[]),'⚡ Geschwindigkeit',
    [0.5,0.75,1,1.25,1.5,2].map(s=>[s+'×', s===playSpeed, ()=>speedWaehlen(s)]));
}
function plBarIdleInit(media,el){                      // Leiste ruht die Maus -> ausblenden (nur beim Abspielen)
  clearTimeout(plbIdleTimer);
  media.classList.remove('baridle');
  const wecken=()=>{media.classList.remove('baridle'); clearTimeout(plbIdleTimer);
    plbIdleTimer=setTimeout(()=>{if(!el.paused)media.classList.add('baridle');},3000);};  // JB: „weg nach ~3 s"
  media.onpointermove=wecken;
  media.onpointerleave=()=>{if(!el.paused)media.classList.add('baridle');};
  el.addEventListener('pause',()=>media.classList.remove('baridle'));
  wecken();
}

/* ---- Gerät „VLC" (Spec Punkt 5, Etappe B Stufe 1) ------------------------
   Spotify-Connect-Muster: die Oberfläche bleibt das Gehirn (Warteschlange,
   Weiterschalten, Abspielart), der Ton kommt aus einer ferngesteuerten
   VLC-Instanz auf dem PC (/api/vlc → python-vlc). Titelende meldet der
   1-s-Status-Takt, dann greift dieselbe playerAdvance-Logik wie im Browser.
   VLC nicht installiert ⇒ Hinweis (toast) + Browser-Player als Rückfall. */
let plGeraet=localStorage.getItem('ytdl_geraet')||'browser';
let vlcTimer=null, vlcEndeFuer='', vlcRateLetzte=1;
/* DIE eine Wahrheit „spielt gerade über VLC?" (JB 05.08.): Gerät VLC gewählt
   UND der aktuelle Titel läuft dort wirklich — Videos OHNE Hülle spielen im
   Browser-Element (VLC kann sein Bild nicht in eine Webseite einbetten),
   Audio immer über VLC, in der Hülle alles. */
function vlcAktiv(){
  if(plGeraet!=='vlc')return false;
  const x=libFind(aktKey()); if(!x)return false;
  const istAudio=x.dateiart?x.dateiart==='audio':((x.kategorie==='MP3')||(!x.vcodec&&x.acodec));
  return istAudio||!!window.pywebview;
}
async function vlcBefehl(cmd,extra){
  try{
    const r=await fetch('/api/vlc',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(Object.assign({cmd:cmd},extra||{}))});
    return await r.json();
  }catch(e){return null;}
}
async function geraetWechsel(){
  if(plGeraet==='vlc'){
    plGeraet='browser'; try{localStorage.setItem('ytdl_geraet','browser');}catch(e){}
    vlcBefehl('stop'); geraetMalen(); if(aktKey())renderPlayerMedia();
    return;
  }
  const s=await vlcBefehl('pruefen');                 // lädt libvlc; ehrlicher Rückfall
  if(!s||!s.verfuegbar){toast((s&&s.grund)||'VLC nicht erreichbar — der Browser-Player spielt weiter.'); return;}
  plGeraet='vlc'; try{localStorage.setItem('ytdl_geraet','vlc');}catch(e){}
  geraetMalen(); if(aktKey())renderPlayerMedia();
}
function geraetMalen(){
  // JB 05.08.: „Warum nicht einfach nur VLC?" — der Knopf heißt immer
  // 🖥 VLC und leuchtet, wenn VLC das Ausgabegerät ist (Toggle-Optik).
  document.querySelectorAll('#pl-geraet').forEach(b=>{
    b.textContent='🖥 VLC';
    b.classList.toggle('an',plGeraet==='vlc');
    b.title=plGeraet==='vlc'
      ?'VLC ist das Ausgabegerät (läuft unabhängig vom Browser-Fenster) — Klick schaltet zurück auf den Browser-Player'
      :'Auf VLC abspielen (dieser PC): läuft auch ohne Browser-Fenster weiter — Klick schaltet um; ohne installiertes VLC bleibt der Browser-Player';
  });
}
function renderPlayerVlc(media,x,k){
  // JB 05.08.: „Ich will, dass die identisch aussehen" — die VLC-Ansicht
  // nutzt EXAKT die normale Player-Leiste (plBarHTML); nur der Ton kommt aus
  // VLC. Kein Hinweistext (der Tooltip am 🖥-VLC-Knopf erklärt es). Die
  // Leisten-Funktionen (Seek/Zeit/±10s/Merker/Play-Symbol) sind VLC-fähig
  // und lesen den 1-s-Status statt des <audio>-Elements.
  const fb=x.thumb?`this.onerror=function(){this.style.display='none'};this.src='${esc(x.thumb)}'`
                  :`this.style.display='none'`;
  const t=`<img class="pl-cover" src="/api/cover?id=${encodeURIComponent(k)}" style="cursor:pointer" onerror="${fb}">`;
  media.innerHTML=`<canvas id="pl-viz" class="pl-viz"></canvas><div class="pl-vizwrap">${t}</div>`+
    `<div class="pl-subzeile" id="pl-sub-anzeige" style="display:none"></div>`+plBarHTML(false);
  media.classList.remove('viz-an');
  media.onclick=ev=>{                                  // Klick in die Fläche = Pause/Weiter
    if(ev.target.closest&&ev.target.closest('.pl-bar'))return;
    plTogglePlay();
  };
  vlcEndeFuer='';
  // Wiedergabe-Regeln (Etappe C) gelten auch hier: effektives Tempo mitgeben,
  // und bei eingeschalteten Untertiteln lädt VLC die .vtt als eigene Spur.
  const w=wiedergabeFuer(x);
  vlcRateLetzte=w.speed||playSpeed||1;
  vlcBefehl('play',{key:k,vol:plVol,rate:vlcRateLetzte,sub:subMode!=='aus',ton:w.ton||''}).then(s=>{
    if(s&&!s.verfuegbar){                              // VLC unterwegs verschwunden -> Rückfall
      toast(s.grund||'VLC nicht gefunden — der Browser-Player übernimmt.');
      plGeraet='browser'; try{localStorage.setItem('ytdl_geraet','browser');}catch(e){}
      geraetMalen(); renderPlayerMedia();
    }else if(s&&s.fehler)toast('VLC: '+s.fehler);
  });
  if(!vlcTimer)vlcTimer=setInterval(vlcTick,1000);
}
let vlcPosLetzte=0, vlcDauerLetzte=0, vlcHeilt=false, vlcPosTs=0, vlcSpielt=false, vlcKeyLetzter='';
function vlcPosGeschaetzt(){
  // Zwischen zwei Status-Takten weiterzählen — Untertitel/Karaoke laufen
  // sonst nur im 1-s-Ruck (JB: „untertitel an, aber kommt kein untertitel":
  // ohne <audio>-Element trieb NICHTS die Anzeige).
  return vlcPosLetzte+(vlcSpielt?((Date.now()-vlcPosTs)/1000)*(vlcRateLetzte||1):0);
}
function vlcKarLauf(){
  // Untertitel im Bildtakt am Gerät VLC — für ALLE Modi, nicht nur Karaoke
  // (Blink-Fix 05.08.: der 1-s-Status allein ließ Zeilen an den Cue-Grenzen
  // flackern und Cues unter 1 s ganz ausfallen).
  if(!window.requestAnimationFrame)return;
  cancelAnimationFrame(karRAF);
  const schritt=()=>{
    if(plGeraet!=='vlc'||!vlcAktiv()||!vlcSpielt||subMode==='aus'){karRAF=0; return;}
    subTick(null);
    karRAF=requestAnimationFrame(schritt);
  };
  karRAF=requestAnimationFrame(schritt);
}
function vlcNeustart(){
  // ↻ (JB: „Gibt es einen reload knopf wenn etwas abstürzt?"): VLC frisch
  // starten und an der letzten Stelle weiterspielen (3 s Anlauf).
  const k=aktKey(); if(!k)return;
  const w=wiedergabeFuer(libFind(k));
  const pos=Math.max(0,(vlcPosLetzte||0)-3);
  vlcBefehl('play',{key:k,vol:plVol,rate:(w.speed||playSpeed||1),sub:subMode!=='aus',pos,ton:w.ton||''});
  toast('↻ VLC neu verbunden'+(pos>0?' — weiter bei '+zeit(pos):''));
}
/* Etappe set_hwnd (JB-Go): läuft die Oberfläche in der PROGRAMM-HÜLLE
   (window.pywebview), meldet sie die Player-Fläche — der Server-VLC rendert
   sein Video dann IN das Hüllen-Fenster statt in ein eigenes. Die Leiste
   bleibt frei (Fläche endet an ihrer Oberkante); Geräte-Pixel via dpr. */
let _hRectSig='';
function huelleVideoRect(s){
  const api=window.pywebview&&window.pywebview.api;
  if(!api||!api.video_rect)return;
  const x=libFind(aktKey());
  const video=x&&(x.dateiart?x.dateiart!=='audio':(x.kategorie!=='MP3'));
  const wrap=document.querySelector('#pl-media .pl-vizwrap');
  const an=!!(vlcAktiv()&&video&&wrap&&s&&s.verfuegbar&&s.zustand!=='aus');
  let sig='aus', args=[0,0,0,0,false];
  if(an){
    const r=wrap.getBoundingClientRect();
    const bar=document.querySelector('#pl-media .pl-bar');
    let unten=r.bottom;
    if(bar){const br=bar.getBoundingClientRect();
      if(br.height>0&&br.top<unten)unten=Math.max(r.top,br.top);}
    const dpr=window.devicePixelRatio||1;
    args=[Math.round(r.left*dpr),Math.round(r.top*dpr),
          Math.round(r.width*dpr),Math.round(Math.max(0,unten-r.top)*dpr),true];
    sig=args.join(',');
  }
  if(sig===_hRectSig)return;                          // nur Änderungen melden
  _hRectSig=sig;
  try{api.video_rect(args[0],args[1],args[2],args[3],args[4]);}catch(e){}
}
async function vlcTick(){
  if(plGeraet!=='vlc'){clearInterval(vlcTimer); vlcTimer=null; huelleVideoRect(null); return;}
  const s=await vlcBefehl('status'); if(!s||!s.verfuegbar)return;
  huelleVideoRect(s);
  if(s.rate)vlcRateLetzte=s.rate;
  if(s.dauer)vlcDauerLetzte=s.dauer;
  vlcKeyLetzter=s.key||'';
  vlcSpielt=(s.zustand==='spielt');
  if(vlcSpielt){
    // Blink-Wurzel 3 (Uhr-Klemme): der frische Status hängt oft ein paar
    // hundert ms HINTER der weiterlaufenden Schätz-Uhr — kleine Rücksprünge
    // warfen die Untertitel-Zeile kurz aus ihrem Zeitfenster (leer, nächster
    // Takt wieder da = Flackern an Zeilen-Grenzen). Nur echte Sprünge
    // (Seek/Drift > 1,5 s) setzen die Uhr zurück.
    const gesch=vlcPosGeschaetzt();
    if(!(s.pos<gesch&&gesch-s.pos<1.5)){vlcPosLetzte=s.pos; vlcPosTs=Date.now();}
  }
  // Untertitel am Gerät VLC: der Bildtakt (vlcKarLauf, jetzt für ALLE Modi)
  // treibt die Anzeige weich; der 1-s-Takt bleibt Fallback — aber nur mit
  // gültiger VLC-Uhr (Blink-Wurzel 1: nie mit t=0 malen).
  if(subMode!=='aus'&&subCues&&vlcAktiv())subTick(null);
  if(subMode!=='aus'&&vlcSpielt&&!karRAF)vlcKarLauf();
  // Die NORMALE Player-Leiste spiegelt den VLC-Zustand (JB: identische
  // Optik): Play/Pause-Symbol überall, Tempo-Knopf zeigt die echte Rate.
  document.querySelectorAll('[data-tr="pp"]').forEach(b=>{
    b.innerHTML=ico(s.zustand==='spielt'?'pause':'play');
    b.title=s.zustand==='spielt'?'Pause':'Abspielen';});
  const sb=document.getElementById('plb-speed');
  if(sb)sb.textContent=(s.rate||1)+'×';
  // Selbstheilung: meldet libvlc FEHLER, einmal automatisch neu verbinden
  // (der Server baut die Instanz frisch); erst der zweite Fehler bleibt stehen.
  if(s.zustand==='fehler'&&s.key===aktKey()&&!vlcHeilt){vlcHeilt=true; vlcNeustart(); return;}
  if(s.zustand==='spielt')vlcHeilt=false;
  // Wiedergabe-Merker („wo war ich zuletzt") — derselbe Speicher wie im
  // Browser-Player (ytdl_pos_v1), gleicher 5-s-Takt; gemalt wird er von
  // posMerkerMalen über den normalen Leisten-Ticker.
  const mk=aktKey();
  if(mk&&s.dauer&&s.zustand==='spielt'&&Date.now()-_posMerkTs>5000){
    _posMerkTs=Date.now();
    if(s.pos>20&&s.pos<s.dauer-20)_posMerk[mk]={t:Math.floor(s.pos),ts:Date.now()};
    else if(s.pos>=s.dauer-20)delete _posMerk[mk];
    try{localStorage.setItem('ytdl_pos_v1',JSON.stringify(_posMerk));}catch(e){}
  }
  // Titelende: genau EINMAL weiterschalten (der Ended-Zustand bleibt in libvlc
  // stehen, bis etwas Neues spielt — ohne die Merker-Variable liefe die
  // Warteschlange bei leerem Ende im 1-s-Takt immer weiter).
  if(s.zustand==='ende'&&s.key&&s.key===aktKey()&&vlcEndeFuer!==s.key){
    vlcEndeFuer=s.key; playerAdvance();
  }
}
/* ---- Wiedergabe-Grundeinstellungen (Spec Punkt 5, Etappe C) --------------
   Drei Ebenen, jede schlägt die darüber (JB-bestätigt 23.07.):
   global (Einstellungen) → je Playlist → je Titel. Änderungen am LAUFENDEN
   Titel merkt sich der Player für genau diesen Titel („absolut") — die
   Sitzungs-Standards (localStorage) bleiben die unterste Ebene, damit sich
   für Titel ohne eigene Regel nichts ändert. Ton-Sprache ist vorbereitet
   und greift, sobald der Film-Import Mehrspur-Dateien bringt. */
let subModeSitzung=subMode;
function wiedergabeFuer(x){
  const p=(playerState.plid&&((plState.find(q=>q.id===playerState.plid)||{}).wiedergabe))||{};
  const g=(daten&&daten.config&&daten.config.wiedergabe)||{};
  const t=(x&&x.wiedergabe)||{};
  return {sub:t.sub||p.sub||g.sub||'', speed:t.speed||p.speed||g.speed||0, ton:t.ton||p.ton||g.ton||'',
          sub_offset:t.sub_offset||p.sub_offset||g.sub_offset||0};
}
function wiedergabeAnwenden(x,el){
  const w=wiedergabeFuer(x);
  const sub=w.sub||subModeSitzung;                     // keine Regel -> Sitzungs-Standard
  if(sub!==subMode){subMode=sub; subAnzeigen();}
  subOffset=w.sub_offset||0;                           // gemerkter Untertitel-Versatz je Titel
  const sp=w.speed||playSpeed;
  if(el)el.playbackRate=sp;
  const b=document.getElementById('plb-speed'); if(b)b.textContent=sp+'×';
}
function wiedergabeMerken(felder){
  const k=aktKey(); if(!k)return;                      // nichts läuft -> nichts zu merken
  const x=libFind(k); if(x)x.wiedergabe=Object.assign({},x.wiedergabe||{},felder);
  fetch('/api/wiedergabe',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(Object.assign({keys:[k],merge:1},felder))}).catch(()=>{});
}
function speedWaehlen(s){playSpeed=s; speedAnwenden(); wiedergabeMerken({speed:s});
  if(vlcAktiv()){vlcRateLetzte=s; vlcBefehl('rate',{wert:s});}}
let wgZiel=null;
function wgGlobalDialog(){wiedergabeDialog({global:1},'Standard für alles ohne eigene Regel');}
function wiedergabeDialog(ziel,name){
  wgZiel=ziel;
  const w=ziel.plid?(((plState.find(p=>p.id===ziel.plid)||{}).wiedergabe)||{})
        :ziel.global?((daten&&daten.config&&daten.config.wiedergabe)||{})
        :(ziel.keys&&ziel.keys.length===1?(((libFind(ziel.keys[0])||{}).wiedergabe)||{}):{});
  const sopt=[['','— erben —'],['aus','aus'],['zeilen','Untertitel'],['karaoke','Karaoke'],['transkript','Transkript']];
  const vopt=[['','— erben —'],['0.5','0.5×'],['0.75','0.75×'],['1','1×'],['1.25','1.25×'],['1.5','1.5×'],['2','2×'],['3','3×']];
  const topt=[['','— egal —'],['de','Deutsch'],['en','Englisch'],['orig','Original']];
  const sel=(id,opt,akt)=>'<select id="'+id+'">'+opt.map(o=>'<option value="'+o[0]+'"'+
    (String(akt||'')===o[0]?' selected':'')+'>'+o[1]+'</option>').join('')+'</select>';
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML='<div class="modal-box" style="max-width:460px"><div class="modal-head"><b>🎚 Wiedergabe — '+esc(name)+'</b>'
    +'<button class="ib" title="Abbrechen" onclick="this.closest(\\'.modal\\').remove()">✕</button></div>'
    +'<div style="padding:14px 16px;display:flex;flex-direction:column;gap:9px">'
    +'<div class="optrow"><span>Untertitel / Karaoke</span>'+sel('wg-sub',sopt,w.sub)+'</div>'
    +'<div class="optrow"><span>Geschwindigkeit</span>'+sel('wg-speed',vopt,w.speed)+'</div>'
    +(ziel.global?'<div class="optrow"><span>Ton-Sprache (Mehrspur, vorbereitet)</span>'+sel('wg-ton',topt,w.ton)+'</div>':'')
    +'<div class="muted2" style="font-size:11.5px">„— erben —" = die Ebene darüber gilt: Titel → Playlist → global → Sitzung.'
    +(ziel.keys&&ziel.keys.length?' Ändert '+ziel.keys.length+' Titel.':'')+'</div>'
    +'</div><div style="padding:0 16px 16px;display:flex;gap:8px;justify-content:flex-end">'
    +'<button class="btn mini" data-nein>Abbrechen</button>'
    +'<button class="btn mini" data-ja style="background:var(--akz);border-color:var(--akz);color:#1b1512">Übernehmen</button>'
    +'</div></div>';
  ov.onclick=e=>{if(e.target===ov)ov.remove();};
  ov.querySelector('[data-nein]').onclick=()=>ov.remove();
  ov.querySelector('[data-ja]').onclick=()=>{wgSpeichern(); ov.remove();};
  document.body.appendChild(ov);
}
async function wgSpeichern(){
  const hol=id=>{const s=document.getElementById(id); return s?s.value:undefined;};
  const body=Object.assign({},wgZiel,{sub:hol('wg-sub')||'',speed:parseFloat(hol('wg-speed'))||0});
  const ton=hol('wg-ton'); if(ton!==undefined)body.ton=ton;
  await fetch('/api/wiedergabe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  await Promise.all([libLaden(),plLaden(),laden()]);   // alle drei Ebenen frisch
  toast('🎚 Wiedergabe-Einstellungen gespeichert.');
}
function renderPlayerMedia(){
  const media=document.getElementById('pl-media'); if(!media)return;
  spulStopp();                                         // Titelwechsel beendet den Spul-Modus
  const k=aktKey(), x=libFind(k);
  if(!x){media.innerHTML='<div class="pl-leer">Kein Titel.</div>'; return;}
  const uebernahme=(adoptEl&&adoptEl._key===k)?adoptEl:null; adoptEl=null;
  if(!uebernahme)xfAbbrechen();                        // normaler Wechsel -> evtl. laufenden Fade verwerfen
  const src='/media?id='+encodeURIComponent(k);
  try{fetch('/api/played',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:k})});}catch(e){}
  // Nach der WIRKLICH servierten Datei entscheiden (dateiart vom Server):
  // fehlt das Video und es gibt nur die MP3, gehört die Audio-Ansicht
  // (Cover+Visualizer) her — statt schwarzem Video-Element (JB 14.07.).
  const istAudio=x.dateiart?x.dateiart==='audio':((x.kategorie==='MP3')||(!x.vcodec&&x.acodec));
  // JB 05.08.: „warum öffnet sich ein neues Fenster mit VLC?" — im BROWSER
  // kann VLC sein Bild nicht einbetten (kein Fenster-Handle über Webseiten).
  // Darum spielt ein VIDEO ohne Hülle im Browser-Element (eingebettet, wie
  // erwartet); Audio bleibt am Gerät VLC (braucht kein Fenster). In der
  // PROGRAMM-HÜLLE rendert VLC eingebettet ins eigene Fenster (set_hwnd).
  const vlcHier=plGeraet==='vlc'&&(istAudio||!!window.pywebview);
  if(!vlcHier&&plGeraet==='vlc')vlcBefehl('stop');     // JB-Fund: sonst spielt VLC-Audio unterm Browser-Video weiter
  if(vlcHier){                                         // Gerät „VLC": Motor auf dem PC statt <audio>/<video>
    xfAbbrechen();                                     // Crossfade gehört dem Browser-Element
    renderPlayerVlc(media,x,k);
  }else if(istAudio){
    // Etappe A (Spec Punkt 5): erst das ECHTE eingebettete Album-Cover
    // (/api/cover); gibt es keins (404), fällt das Bild aufs YouTube-Thumbnail
    // zurück — und erst wenn auch das fehlt, verschwindet es.
    const fb=x.thumb?`this.onerror=function(){this.style.display='none'};this.src='${esc(x.thumb)}'`
                    :`this.style.display='none'`;
    const t=`<img class="pl-cover" src="/api/cover?id=${encodeURIComponent(k)}" style="cursor:pointer" onerror="${fb}">`;
    media.innerHTML=`<canvas id="pl-viz" class="pl-viz"></canvas><div class="pl-vizwrap">${t}</div>`+
      `<div class="pl-subzeile" id="pl-sub-anzeige" style="display:none"></div>`+plBarHTML(false)+
      (uebernahme?'':`<audio id="pl-el" autoplay src="${src}"></audio>`);
    if(uebernahme){uebernahme.id='pl-el'; uebernahme.controls=false; uebernahme.className=''; media.appendChild(uebernahme);}
  }else{
    xfAbbrechen();                                     // Video: kein Crossfade
    media.innerHTML=`<video id="pl-el" autoplay src="${src}"></video>`+
      `<div class="pl-subzeile" id="pl-sub-anzeige" style="display:none"></div>`+plBarHTML(true);
  }
  const el=document.getElementById('pl-el');
  if(el){
    // Ende: wenn schon ein Crossfade läuft, das nächste Element übernehmen, sonst normal weiter
    el.addEventListener('ended',()=>{ if(xfNext)xfUebernehmen(); else playerAdvance(); });
    // Play/Pause-Symbol überall sofort nachziehen (JB 05.08.) — cmdNow malt
    // die Kopfzeile, transportRender die data-tr-Knöpfe der Player-Leiste.
    el.addEventListener('play',()=>{cmdNowRender(); transportRender();});
    el.addEventListener('pause',()=>{cmdNowRender(); transportRender();});
    el.addEventListener('timeupdate',()=>subTick(el));   // Untertitel/Karaoke mitlaufen lassen
    el.addEventListener('play',()=>karLauf(el));         // Karaoke-Wischer im Bildtakt (Build 115)
    if(istAudio)el.addEventListener('timeupdate',()=>uebergangTick(el));   // Gapless/Crossfade/Automix
    try{el.volume=plVol/100;}catch(e){}                   // gemerkte Lautstärke anwenden
    // Klick IRGENDWO in die Player-Fläche = Pause/Play (unsere Leiste ausgenommen)
    media.onclick=ev=>{
      if(ev.target.closest&&ev.target.closest('.pl-bar'))return;
      if(el.paused)el.play(); else el.pause();
    };
    plBarIdleInit(media,el);                              // Leiste blendet bei Maus-Ruhe aus (YouTube-Stil)
    seitenverhaeltnisAnwenden();                          // Build 130: 16:9 fest (JB)
  }
  if(el && istAudio){ vizVerbinde(el); vizFarbeAktualisieren(); vizModeRender(); vizStart(); }
  else{ media.classList.remove('viz-an'); }             // Video: kein Visualizer-Overlay
  document.getElementById('pl-titel').textContent=x.titel;
  document.getElementById('pl-pos').textContent=(playerState.idx+1)+' / '+playerState.queue.length;
  lieblingMalen();                                     // ＋/✓ folgt dem laufenden Titel (Build 144d)
  renderPlayerQueue();
  playerLayoutSet();
  cmdNowRender();
  speedAnwenden();                                     // Geschwindigkeit auf neues Element anwenden
  wiedergabeAnwenden(x,el);                            // Etappe C: Titel/Playlist/global-Regeln obendrauf
  renderKapitel(x);                                    // YouTube-Kapitel als Sprungmarken
  subLaden(k);                                         // Untertitel für den neuen Titel holen
  canvasAnwenden();                                    // animierter Cover-Hintergrund (falls an)
}
function plQueueKlick(i){
  if(i===playerState.idx){                             // schon aktiv -> Pause/Play statt Neustart
    if(vlcAktiv()){plTogglePlay(); return;}
    const el=document.getElementById('pl-el'); if(el){if(el.paused)el.play(); else el.pause();}
    return;
  }
  playerState.idx=i; renderPlayerMedia();
  // Fokus überlebt das Neu-Rendern (JB-Sicht-Check 22.07.): nach Enter/Doppelklick sonst
  // Fokus weg -> Entf/Pfeile brauchten erst wieder einen Klick in die Liste.
  plqSel=i; plqMark(); plqFocus(i);
}
/* Player-Warteschlange: Einträge umsortieren (HTML5-Drag) + Titel aus der
   Bibliothek hineinziehen (JB 13.07.: „aus der Bibliothek in die Playlist schieben") */
let plqVon=null;
// Playlist-Bedienung (JB 22.07.): Einfachklick WÄHLT nur, Doppelklick/Enter spielt,
// Entf löscht, ↑/↓ bewegen die Auswahl. plqSel = markierter Eintrag (Index).
let plqSel=null;
function plqFocus(i){                                  // nur den SICHTBAREN Eintrag fokussieren
  document.querySelectorAll('.pl-queue .pl-item[data-i="'+i+'"]').forEach(el=>{if(el.offsetParent)el.focus();});}
// Auswahl NUR per Klasse markieren, NICHT neu rendern: sonst würde der Einfachklick das
// Element ersetzen und der Doppelklick (zwei Klicks auf DASSELBE Element) fiele aus (JB 22.07.).
// Build 144 (live gemessen): 'sel' hat ZWEI Quellen — den Fokus-Eintrag
// plqSel und die Mehrfachauswahl plqAuswahl. plqMark kannte nur die erste und
// wischte deshalb jede gerade gezogene Rahmen-Auswahl beim Loslassen wieder
// weg (dasselbe galt fuer den Strg-Klick). renderPlayerQueue fragt beide ab —
// hier stand die zweite Wahrheit. Es gibt nur eine.
function plqMark(){document.querySelectorAll('.pl-queue .pl-item').forEach(el=>{
  const i=+el.dataset.i; el.classList.toggle('sel', plqAuswahl.has(i)||i===plqSel);});}
/* ---- Rahmen-Auswahl in der Playlist (Build 139, JB Punkt 4) --------------
   JB: „Ich wuerde gerne auch in der Playlist wieder wie in Windows mehrere
   Titel mit der Maus markieren koennen (Maus macht ein Viereck und
   markiert)." Dasselbe Muster wie in der Bibliothek und im Abo-Fenster,
   damit es sich ueberall gleich anfuehlt: ab 5 px wird es ein Band, Strg
   erweitert, der nachlaufende Klick wird geschluckt.
   Unterschied zur Bibliothek: die Zeilen sind ZIEHBAR (Umsortieren), also
   startet das Band nur auf freier Flaeche — sonst koennte man nicht mehr
   umsortieren. */
let plqAuswahl=new Set(), plqBandLief=false;
function plqSelect(i,ev){
  if(plqBandLief)return;                               // Ende eines Band-Zugs
  if(ev&&(ev.ctrlKey||ev.metaKey)){                    // Strg: dazu/weg
    if(plqAuswahl.has(i))plqAuswahl.delete(i); else plqAuswahl.add(i);
  }else if(ev&&ev.shiftKey&&plqSel!==null){            // Umschalt: Bereich
    const a=Math.min(plqSel,i), b=Math.max(plqSel,i);
    for(let j=a;j<=b;j++)plqAuswahl.add(j);
  }else plqAuswahl.clear();
  plqSel=i; plqMark(); plqFocus(i);
}
/* Build 144 — warum der Rahmen bis hierher nie zu sehen war (JB dreimal:
   „Ich kann im Player immer noch kein Fenster mit der Maus ziehen"):
   Build 139 hatte das Muster der BIBLIOTHEK uebernommen — dort startet das
   Band nur auf freier Flaeche, damit die ziehbaren Kacheln ziehbar bleiben,
   und zwischen Kacheln ist reichlich Luft. Die Playlist ist aber eine LISTE
   und hat diese Luft NIE: am echten Fenster gemessen ist .pl-queue bei 14
   Titeln randvoll (362 px Inhalt in 150 px Sicht) und schrumpft bei 3 Titeln
   auf exakt ihre Zeilenhoehe (76 px) — freie Hoehe 0 px in beiden Faellen,
   weil die Liste mit ihrem Inhalt waechst. Jeder Punkt lag auf einer Zeile,
   also stieg plqBandStart immer sofort aus.
   Jetzt wie im Explorer: eine MARKIERTE Zeile greift man zum Verschieben, auf
   jeder anderen zieht man einen Rahmen auf. Damit bleiben beide Gesten heil,
   ohne neue Bedienzone. Wer das alte Verhalten will, stellt „nur auf freier
   Flaeche" ein (⚙ Ansicht → Playlist-Rahmen). */
function plqRahmenArt(){
  let v='auto'; try{v=localStorage.getItem('ytdl_plqrahmen')||'auto';}catch(e){}
  return v==='frei'?'frei':'auto';
}
function plqRahmenArtSetzen(v){
  try{localStorage.setItem('ytdl_plqrahmen',v==='frei'?'frei':'auto');}catch(e){}
  toast(v==='frei'?'▭ Rahmen nur auf freier Fläche (Ziehen hat überall Vorrang).'
                  :'▭ Rahmen ab der Zeile — markierte Titel bleiben zum Verschieben greifbar.');
}
let plqBandModus=false;                                // laeuft gerade ein Band auf einer Zeile?
let plqZugLaeuft=false;                                // ein Zug ist unterwegs (Zuhoerer haengt an ZWEI Ebenen)
function plqBandStart(ev){
  if(ev.button!==0)return;
  if(plqZugLaeuft)return;                              // sonst entstuenden zwei Baender uebereinander
  if(ev.target.closest('button,a,input,select'))return;
  if(ev.target.closest('.pl-media'))return;            // auf dem Video kein Band (eigene Steuerung, Drop-Ziel)
  const zeile=ev.target.closest('.pl-item');
  if(zeile){
    if(plqRahmenArt()==='frei')return;                 // Einstellung: Ziehen hat Vorrang
    if(zeile.classList.contains('sel'))return;         // markiert = greifen und verschieben
    // Ab hier gilt der Rahmen — der native HTML5-Drag muss schweigen, sonst
    // frisst er die Bewegung, aus der das Band entsteht (plqDragStart).
    plqBandModus=true;
  }
  /* Build 144c (JB nach der echten Maus-Probe): „wie in bibliothek soll der
     fenster ziehen modus in player/playlist schon ein/zwei reihen darueber
     funktionieren koennen." Der Zuhoerer haengt deshalb zusaetzlich am
     BEHAELTER ueber der Liste — genau wie in der Bibliothek seit Build 143.
     Getroffen und gescrollt wird aber weiter die LISTE, nicht der Behaelter:
     sonst schoebe das Rand-Nachschieben am falschen Element. */
  const behaelter=ev.currentTarget;
  const flaeche=behaelter.classList.contains('pl-queue')
    ? behaelter : [...behaelter.querySelectorAll('.pl-queue')].find(n=>n.offsetParent);
  // Ohne SICHTBARE eigene Liste kein Band: ein Panel kann mehrere Ansichten
  // tragen (Reiter), und der Zuhoerer am panel-body wuerde sonst in Ansicht A
  // einen Rahmen ueber Ansicht B ziehen.
  if(!flaeche)return;
  plqZugLaeuft=true;
  const basis=new Set(ev.ctrlKey||ev.metaKey?[...plqAuswahl]:[]);
  const x0=ev.clientX, y0=ev.clientY; let band=null;
  function mv(e){
    if(!band){
      if(Math.abs(e.clientX-x0)<5&&Math.abs(e.clientY-y0)<5)return;
      // Build 143 (JB-Bild): Ohne das hier markiert der Browser beim
      // Aufziehen den TEXT der Kacheln mit (blau hinterlegt) — der
      // Rahmen soll aber Titel waehlen, nicht Buchstaben.
      document.body.classList.add('nosel');
      band=document.createElement('div'); band.className='abo-band'; document.body.appendChild(band);
    }
    const l=Math.min(x0,e.clientX), t=Math.min(y0,e.clientY),
          r=Math.max(x0,e.clientX), b=Math.max(y0,e.clientY);
    band.style.left=l+'px'; band.style.top=t+'px';
    band.style.width=(r-l)+'px'; band.style.height=(b-t)+'px';
    const fr=flaeche.getBoundingClientRect();
    if(e.clientY>fr.bottom-18)flaeche.scrollTop+=14;
    else if(e.clientY<fr.top+18)flaeche.scrollTop-=14;
    plqAuswahl=new Set(basis);
    flaeche.querySelectorAll('.pl-item').forEach(n=>{
      const q=n.getBoundingClientRect();
      if(q.left<r&&q.right>l&&q.top<b&&q.bottom>t)plqAuswahl.add(+n.dataset.i);
      n.classList.toggle('sel',plqAuswahl.has(+n.dataset.i));
    });
  }
  function up(){
    document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
    document.body.classList.remove('nosel'); plqBandModus=false; plqZugLaeuft=false;
    if(band){band.remove(); plqBandLief=true; setTimeout(()=>{plqBandLief=false;},0); plqMark();}
    else if(!zeile&&!basis.size&&(plqAuswahl.size||plqSel!==null)){
      // JB-Kleinkram 05.08. (wie Bibliothek Build 142): ein KLICK auf freie
      // Fläche (kein Zug) räumt die Playlist-Auswahl ab — Explorer-Muster.
      // Mit Strg (basis gefüllt) bleibt sie erhalten.
      plqAuswahl.clear(); plqSel=null; plqMark();
    }
  }
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
}
function plqAuswahlLoeschen(){
  // Mehrere auf einmal entfernen: von HINTEN nach vorn, sonst verschieben
  // sich die Indizes unter den noch zu loeschenden Eintraegen weg.
  if(!plqAuswahl.size){plqRemove(plqSel!==null?plqSel:playerState.idx); return;}
  [...plqAuswahl].sort((a,b)=>b-a).forEach(i=>plqRemove(i));
  plqAuswahl.clear(); plqMark();
}
function plqMoveSel(d){
  if(!playerState.queue.length)return;
  plqSel = plqSel===null ? 0 : Math.max(0, Math.min(playerState.queue.length-1, plqSel+d));
  plqMark(); plqFocus(plqSel);}
function plqRemove(i){                                 // Titel aus der Ad-hoc-Playlist nehmen — auch den LAUFENDEN
  if(i===null||i<0||i>=playerState.queue.length)return;
  const warAktuell=(i===playerState.idx);             // wird der gerade laufende Titel entfernt?
  const curKey=aktKey();                               // laufenden Titel über den Umbau retten
  playerState.queue.splice(i,1);
  if(!playerState.queue.length){                       // Liste leer -> Wiedergabe endet
    plqSel=null; playerState.idx=-1;
    renderPlayerQueue(); renderPlayerMedia(); cmdNowRender(); return;
  }
  if(warAktuell){
    // JB 22.07.: den laufenden Titel entfernen = er ist „beendet". Der nachrückende
    // Titel übernimmt (wie ein Titel-Ende); war es der letzte, endet die Wiedergabe.
    if(i<playerState.queue.length){                    // es gab einen nächsten -> der läuft weiter
      playerState.idx=i; plqSel=i;
      renderPlayerQueue(); renderPlayerMedia();
    }else{                                             // war der letzte -> Wiedergabe endet (Media wird geleert)
      playerState.idx=-1; plqSel=playerState.queue.length-1;
      renderPlayerQueue(); renderPlayerMedia(); cmdNowRender();
    }
    // Fokus-Restore auch HIER (JB-Sicht-Check 22.07.): sonst braucht die Tastatur nach dem
    // Entfernen des laufenden Titels wieder einen Klick (gleicher Tick-Trick wie unten).
    if(plqSel!==null)setTimeout(function(){plqFocus(plqSel);},0);
    return;
  }
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));   // anderer Titel raus -> laufender spielt ungestört weiter
  plqSel=Math.min(i, playerState.queue.length-1);
  renderPlayerQueue();
  // Fokus einen Tick SPÄTER zurückholen (JB-Sicht-Check 22.07.): der Browser setzt den
  // Fokus nach dem Handler auf body, weil das fokussierte Element entfernt wurde —
  // sofortiges focus() wird davon überschrieben; erst dann greifen Entf/Pfeile erneut.
  if(plqSel!==null)setTimeout(function(){plqFocus(plqSel);},0);
}
function plqVerschieben(i,d){                          // einen Titel im Rechtsklick-Menü hoch/runter schieben
  const j=i+d; if(j<0||j>=playerState.queue.length)return;
  const curKey=aktKey();
  const [t]=playerState.queue.splice(i,1);
  playerState.queue.splice(j,0,t);
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));   // laufender Titel behält seinen Platz
  plqSel=j; renderPlayerQueue(); plqFocus(j);
}
function plItemKontext(ev,i){                          // Rechtsklick auf einen Playlist-Titel (JB 22.07.)
  ev.preventDefault(); ev.stopPropagation();           // nicht zum Karten-Menü (#pl-card) durchblubbern
  const k=playerState.queue[i]; if(k===undefined)return false;
  const x=libFind(k)||{};
  const eintraege=[];
  eintraege.push([i===playerState.idx?'⏯ Pause / Weiter':'▶ Abspielen', ()=>plQueueKlick(i)]);
  if(i!==playerState.idx)eintraege.push(['⏭ Als Nächstes abspielen', ()=>queueAlsNaechstes(k)]);
  if(i>0)eintraege.push(['⏫ Nach oben', ()=>plqVerschieben(i,-1)]);
  if(i<playerState.queue.length-1)eintraege.push(['⏬ Nach unten', ()=>plqVerschieben(i,1)]);
  eintraege.push([i===playerState.idx?'✖ Entfernen (Titel endet)':'✖ Aus Playlist entfernen', ()=>plqRemove(i)]);
  eintraege.push(['ℹ Eigenschaften…', ()=>eigenschaften(k)]);
  if(x.vorhanden)eintraege.push(['📁 Im Ordner zeigen', ()=>biblio(k,'ordner')]);
  if(x.url)eintraege.push(['↗ Auf YouTube öffnen', ()=>window.open(x.url,'_blank','noreferrer')]);
  kontextMenuBauen(ev, eintraege);
  return false;
}
/* Warteschlangen-Aktionen (JB 22.07., Muster Spotify „Add to queue/Play next"
   + MusicBee „Queue Next/Last"): einen Bibliotheks-/Playlist-Titel direkt HINTER
   den laufenden setzen bzw. ANS ENDE hängen. Läuft nichts, spielt er sofort.
   Ist er schon in der Queue, wird er verschoben (keine Dublette). */
function queueAlsNaechstes(key){
  const x=libFind(key); if(!x||!x.vorhanden){toast('Titel ist nicht (mehr) auf der Platte.');return;}
  ensurePlayer();
  if(playerState.idx<0||!playerState.queue.length){playerPlay([key]); return;}   // nichts läuft -> sofort
  const cur=aktKey(); if(key===cur)return;                                        // ist schon der laufende
  const vorhanden=playerState.queue.indexOf(key);
  if(vorhanden>=0)playerState.queue.splice(vorhanden,1);                          // erst raus -> keine Dublette
  const at=Math.max(0, playerState.queue.indexOf(cur))+1;                         // hinter den laufenden
  playerState.queue.splice(at,0,key);
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); cmdNowRender();
  toast('⏭ Als Nächstes: „'+((x.titel||key).slice(0,40))+'"');
}
function queueAnsEnde(key){
  const x=libFind(key); if(!x||!x.vorhanden){toast('Titel ist nicht (mehr) auf der Platte.');return;}
  ensurePlayer();
  if(playerState.idx<0||!playerState.queue.length){playerPlay([key]); return;}
  const cur=aktKey(); if(key===cur)return;
  const vorhanden=playerState.queue.indexOf(key);
  if(vorhanden>=0)playerState.queue.splice(vorhanden,1);
  playerState.queue.push(key);
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); cmdNowRender();
  toast('➕ Ans Ende: „'+((x.titel||key).slice(0,40))+'"');
}
/* Warteschlangen-Werkzeuge (JB 22.07., Muster foobar/MusicBee): die aktuelle
   Ad-hoc-Playlist als benannte Playlist speichern, sortieren, umkehren,
   Duplikate entfernen, leeren. Der laufende Titel behält über alle Umbauten
   seinen Platz (curKey-Rettung). */
async function queueAlsPlaylist(){
  if(!playerState.queue.length){toast('Die Warteschlange ist leer.');return;}
  const n=prompt('Name der neuen Playlist:'); if(!n||!n.trim())return;
  const keys=playerState.queue.slice();
  await fetch('/api/playlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({art:'create',name:n.trim()})});
  await plLaden();                                     // plState frisch -> neue id am Ende
  const neu=plState[plState.length-1]; if(!neu){toast('Konnte die Playlist nicht anlegen.');return;}
  for(const k of keys){                                // Backend-add nimmt einen Key; Reihenfolge bleibt
    await fetch('/api/playlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({art:'add',id:neu.id,key:k})});
  }
  await plLaden();
  toast('💾 „'+n.trim()+'" gespeichert ('+keys.length+' Titel).');
}
function queueSortieren(art){
  if(playerState.queue.length<2)return;
  const cur=aktKey();
  const val=({titel:k=>((libFind(k)||{}).titel||k).toLowerCase(),
              dauer:k=>((libFind(k)||{}).dauer||0),
              datum:k=>((libFind(k)||{}).upload_date||'')})[art]||(k=>k);
  playerState.queue.sort((a,b)=>{const va=val(a),vb=val(b); return va<vb?-1:(va>vb?1:0);});
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); toast('↕ Sortiert nach '+({titel:'Titel',dauer:'Dauer',datum:'Datum'}[art]||art)+'.');
}
function queueUmkehren(){
  if(playerState.queue.length<2)return;
  const cur=aktKey(); playerState.queue.reverse();
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); toast('↕ Reihenfolge umgekehrt.');
}
function queueDuplikate(){
  const cur=aktKey(), seen=new Set(), neu=[];
  playerState.queue.forEach(k=>{if(!seen.has(k)){seen.add(k); neu.push(k);}});
  const weg=playerState.queue.length-neu.length;
  if(!weg){toast('Keine Dubletten in der Warteschlange.');return;}
  playerState.queue=neu; playerState.idx=Math.max(0, neu.indexOf(cur)); plqSel=null;
  renderPlayerQueue(); toast('🧹 '+weg+' Dublette(n) entfernt.');
}
function queueLeeren(){
  if(!playerState.queue.length)return;
  if(!confirm('Die ganze Warteschlange leeren? (Titel-Dateien und gespeicherte Playlists bleiben.)'))return;
  playerState.queue=[]; playerState.idx=-1; plqSel=null;
  renderPlayerQueue(); renderPlayerMedia(); cmdNowRender();
  toast('Warteschlange geleert.');
}
function queueWerkzeugListe(){                          // gemeinsame Liste [Label, aktiv?, fn] für Flyout + ⋯-Menü
  return [['💾 Als Playlist speichern…', false, queueAlsPlaylist],
          ['↕ Nach Titel sortieren', false, ()=>queueSortieren('titel')],
          ['↕ Nach Dauer sortieren', false, ()=>queueSortieren('dauer')],
          ['↕ Reihenfolge umkehren', false, queueUmkehren],
          ['🧹 Duplikate entfernen', false, queueDuplikate],
          ['🗑 Warteschlange leeren', false, queueLeeren]];
}
function plqWerkzeuge(ev){                              // ⋯-Knopf im Playlist-Fenster
  ev.stopPropagation();
  kontextMenuBauen(ev, queueWerkzeugListe().map(o=>[o[0], o[2]]));
}
function plWerkzeugeImPlayer(ev){
  /* Build 137 (JB Punkt 4): derselbe Werkzeugkasten im EINGEBAUTEN Player.
     Zwei Gruppen, die sonst an zwei verschiedenen Orten wohnen und leicht zu
     verwechseln sind — deshalb hier mit Überschriften getrennt:
       · was die WARTESCHLANGE betrifft (was gerade läuft),
       · was die gewählte PLAYLIST betrifft (was gespeichert ist).
     Kein neuer Code für die Aktionen: es sind exakt dieselben Funktionen wie
     im herausgelösten Fenster, damit beide Wege nie auseinanderlaufen. */
  ev.stopPropagation();
  const eintraege=[['— Warteschlange —', ()=>{}]];
  queueWerkzeugListe().forEach(o=>eintraege.push([o[0], o[2]]));
  eintraege.push(['— Playlist —', ()=>{}]);
  eintraege.push(['📻 Neues entdecken', entdeckerOeffnen]);
  eintraege.push(['✎ Umbenennen', plRename]);
  eintraege.push(['🎚 Wiedergabe…', ()=>{                // Etappe C: Regeln je Playlist
    const id=(document.getElementById('plsel')||{}).value||playerState.plid;
    const p=plState.find(q=>q.id===id);
    if(p)wiedergabeDialog({plid:p.id}, 'Playlist „'+p.name+'"');
    else toast('Erst eine gespeicherte Playlist wählen/laden.');
  }]);
  eintraege.push(['⇄ Sync einrichten…', plSyncConfig]);
  eintraege.push(['⤓ Als .m3u exportieren', plExport]);
  eintraege.push(['⤒ .m3u importieren…', ()=>document.getElementById('m3ufile').click()]);
  aktionsMenu(ev, eintraege);
}
/* Eigenschaften-Popup (JB 22.07., foobar „Properties"): alle Metadaten eines
   Titels auf einen Blick — Codec/Bitrate/Auflösung/Größe/Pfad-Herkunft/Tags. */
function eigKopiere(key){const x=libFind(key); try{navigator.clipboard&&navigator.clipboard.writeText((x&&x.titel)||key);}catch(e){} toast('Titel kopiert.');}
function eigenschaften(key){
  const x=libFind(key); if(!x){toast('Keine Infos zu diesem Titel.');return;}
  const vid=(String(key).split('|')[0])||key;
  // JB 05.08.: „unter Eigenschaften die Metadaten sehen (wie in iTunes)" —
  // erst der Musik-Block (Künstler/Album/…), dann Datei und Technik.
  const wg=x.wiedergabe||{};
  const wgText=[wg.sub?('Untertitel: '+wg.sub):'', wg.speed?('Tempo '+wg.speed+'×'):'',
                wg.ton?('Ton: '+wg.ton):''].filter(Boolean).join(' · ');
  const musikText={belegt:'belegt (MusicBrainz)', wahrscheinlich:'wahrscheinlich',
                   nein:'kein Lied'}[x.musik]||'unbestimmt';
  const zeilen=[
    ['Titel', x.titel||key],
    ['Künstler', x.kuenstler||'–'],
    ['Song', x.track||'–'],
    ['Album', x.album||'–'],
    ['Jahr', x.jahr||'–'],
    ['Genre', x.genre||'–'],
    ['Musik-Erkennung', musikText],
    ['Album-Cover', x.cover_album?(x.kategorie==='MP3'?'echtes Cover, eingebettet':'echtes Cover (Beilage)'):'YouTube-Thumbnail'],
    ['Wiedergabe-Regel', wgText||'– (erbt von Playlist/global)'],
    ['Kanal / Uploader', x.uploader||'–'],
    ['Kategorie', x.kategorie||'–'],
    ['Qualität', x.qualitaet||'–'],
    ['Technik', technikText(x)],
    ['Dauer', x.dauer?zeit(x.dauer):'–'],
    ['Dateigröße', mb(x.groesse)],
    ['Hochgeladen', ytdatum(x.upload_date)||'–'],
    ['Zuletzt gespielt', x.last_play?new Date(x.last_play*1000).toLocaleString('de-DE'):'–'],
    ['Wiedergaben', String(x.plays||0)],
    ['Video-ID', vid],
    ['Status', x.vorhanden?'auf der Platte':'verschoben / gelöscht']
  ];
  const rows=zeilen.map(z=>`<tr><td class="k">${esc(z[0])}</td><td class="v">${esc(String(z[1]))}</td></tr>`).join('');
  const yt=x.url?`<tr><td class="k">YouTube</td><td class="v"><a href="${esc(x.url)}" target="_blank" rel="noreferrer">${esc(x.url)}</a></td></tr>`:'';
  // Erst das ECHTE Album-Cover (/api/cover), Thumbnail nur als Rückfall.
  const cfb=x.thumb?`this.onerror=function(){this.style.display='none'};this.src='${esc(x.thumb)}'`
                   :`this.style.display='none'`;
  const cover=`<img src="/api/cover?id=${encodeURIComponent(key)}" style="max-width:190px;width:40%;border-radius:8px;float:right;margin:0 0 8px 12px" onerror="${cfb}">`;
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML=`<div class="modal-box" style="max-width:560px"><div class="modal-head"><b>ℹ Eigenschaften</b>`+
    `<button class="ib" title="Schließen" onclick="this.closest('.modal').remove()">✕</button></div>`+
    `<div style="padding:14px 16px 18px">${cover}<table class="eig-tab">${rows}${yt}</table>`+
    `<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;clear:both">`+
      (x.vorhanden?`<button class="btn mini" onclick="biblio('${key}','ordner')">📁 Im Ordner zeigen</button>`:'')+
      `<button class="btn mini" onclick="eigKopiere('${key}')">⧉ Titel kopieren</button>`+
    `</div></div></div>`;
  ov.onclick=e=>{if(e.target===ov)ov.remove();};
  document.body.appendChild(ov);
}
function plqDragStart(e,i){
  // Build 144: Startet gerade ein Rahmen auf dieser Zeile, darf der native
  // Drag NICHT anspringen — er wuerde die Mausbewegung an sich reissen und
  // das Band bliebe leer. Umgekehrt bleibt jede markierte Zeile ziehbar,
  // weil plqBandStart dort gar nicht erst in den Band-Modus geht.
  if(plqBandModus){e.preventDefault(); return false;}
  plqVon=i; e.dataTransfer.effectAllowed='move';}
function plqDragOver(e){e.preventDefault(); e.dataTransfer.dropEffect='move';}
function plqEinfuegen(key,i){                          // Bibliotheks-Titel an Position i einreihen
  const x=libFind(key); if(!x||!x.vorhanden)return;
  const curKey=aktKey();
  if(!playerState.queue.length)playerState.quelle='Playlist';   // frische Ad-hoc-Playlist
  playerState.queue.splice(i,0,key);
  if(playerState.idx<0){playerState.idx=0; ensurePlayer(); renderPlayerMedia(); return;}
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));
  renderPlayerQueue(); cmdNowRender();
}
/* Titel AUF das Video/Cover ziehen (JB 14.07.): spielt sofort, wenn nichts
   läuft — sonst entsteht/wächst die Ad-hoc-Playlist (die Player-Queue, nichts
   wird gespeichert; speichern geht weiter über ＋ Playlist). */
function plMediaOver(e){
  const t=e.dataTransfer?[...e.dataTransfer.types]:[];
  if(!t.includes('ytdl/key'))return;
  e.preventDefault();
  // Sichtbare Rückmeldung an der KARTE, damit man vor dem Loslassen sieht,
  // dass die ganze Fläche annimmt — nicht nur das Bild.
  const c=document.getElementById('pl-card'); if(c)c.classList.add('dropziel');
}
function plKarteLeave(e){
  const c=document.getElementById('pl-card');
  if(c&&!c.contains(e.relatedTarget))c.classList.remove('dropziel');
}
/* Command-Bar-Mini-Player als Drop-Ziel (JB 21.07.: „Video auf den Play-Knopf
   oben links ziehen = in die Playlist"). Reiht ein — spielt sofort, wenn nichts läuft. */
function cmdNowOver(e){
  const t=e.dataTransfer?[...e.dataTransfer.types]:[];
  if(t.includes('ytdl/key')){e.preventDefault(); const n=document.getElementById('cmd-now'); if(n)n.classList.add('dropziel');}
}
function cmdNowLeave(){const n=document.getElementById('cmd-now'); if(n)n.classList.remove('dropziel');}
function cmdNowDrop(e){
  e.preventDefault(); const n=document.getElementById('cmd-now'); if(n)n.classList.remove('dropziel');
  // Build 141: wie plMediaDrop — die ganze Auswahl reist mit.
  const keys=plZiehKeys(e).filter(k=>{const y=libFind(k); return y&&y.vorhanden;});
  if(!keys.length)return;
  const x=libFind(keys[0]);
  if(playerState.idx<0||!playerState.queue.length){playerPlay(keys);}
  else{ keys.forEach(k=>playerState.queue.push(k)); renderPlayerQueue(); cmdNowRender(); }
  plInfo('🎶 „'+((x.titel||'').slice(0,24))+'" eingereiht ('+playerState.queue.length+' Titel)');
}
function plMediaDrop(e){
  e.preventDefault(); e.stopPropagation();
  const c=document.getElementById('pl-card'); if(c)c.classList.remove('dropziel');
  // Build 141 (JB: „wenn ich vier markiert habe und die alle in den player
  // ziehe, dann ist nur eins davon in der playlist"). Hier wurde nur EIN Key
  // gelesen; plZiehKeys() nimmt die ganze Auswahl mit — dieselbe Funktion,
  // die der Wurf auf die Playlist-Auswahl längst benutzt.
  const keys=plZiehKeys(e).filter(k=>{const y=libFind(k); return y&&y.vorhanden;});
  if(!keys.length)return;
  const x=libFind(keys[0]);
  if(playerState.idx<0||!playerState.queue.length){playerPlay(keys);return;}
  keys.forEach(k=>playerState.queue.push(k));          // doppelt ist erlaubt (JB, Build 138)
  renderPlayerQueue(); cmdNowRender();
  plInfo('🎶 „'+((x.titel||'').slice(0,24))+'" eingereiht ('+playerState.queue.length+' Titel)');
}
function plqDrop(e,i){
  e.preventDefault(); e.stopPropagation();             // WICHTIG: sonst blubbert das Drop hoch zum
  // Container-Handler plqZielDrop -> derselbe Titel wird ein 2. Mal ans Ende gehängt (JB-Bug 22.07.:
  // „zwei reingezogen", nur im Layout mit kleiner Playlist unterm Video, wo man AUF einen Eintrag fallen lässt).
  const neu=e.dataTransfer.getData('ytdl/key');
  if(plqVon===null&&neu){plqEinfuegen(neu,i); return;} // von außen (Bibliothek) hereingezogen
  if(plqVon===null||plqVon===i){plqVon=null;return;}
  const curKey=aktKey();                               // laufenden Titel über den Umbau retten
  const [t]=playerState.queue.splice(plqVon,1);
  playerState.queue.splice(i,0,t);
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));
  plqVon=null; renderPlayerQueue();
}
function plqZielOver(e){                               // Freifläche der Liste als Drop-Ziel
  const typen=e.dataTransfer?[...e.dataTransfer.types]:[];
  if(typen.includes('ytdl/key')||plqVon!==null)e.preventDefault();
}
function plqZielDrop(e){
  e.preventDefault();
  const key=e.dataTransfer.getData('ytdl/key');
  if(key&&plqVon===null)plqEinfuegen(key, playerState.queue.length);
  plqVon=null;
}
/* ---- Build 144d, JB Punkt 3: „Spotify-artiges ＋ im Player oben für eine
   Lieblingssongs-Playlist."
   Bewusst KEINE neue Datenstruktur: die Lieblingssongs sind eine ganz normale
   Playlist und damit sofort abspielbar, exportierbar (.m3u), synchronisierbar
   aufs Handy und im Playlist-Menü sichtbar. Eine eigene „Favoriten"-Liste
   neben den Playlists waere ein zweiter Mechanismus fuer dieselbe Sache.
   Sie entsteht beim ERSTEN Klick — JB soll sie nicht vorher anlegen muessen,
   sonst waere der Knopf beim ersten Mal eine Sackgasse. */
const LIEBLINGS_NAME='♥ Lieblingssongs';
function lieblingsPlaylist(){return (plState||[]).find(p=>p.name===LIEBLINGS_NAME);}
function istLiebling(k){const p=lieblingsPlaylist(); return !!(p&&k&&(p.items||[]).includes(k));}
function lieblingMalen(){
  const b=document.getElementById('pl-lieb'); if(!b)return;
  const k=aktKey(), drin=istLiebling(k);
  b.style.display=k?'':'none';                         // ohne laufenden Titel gibt es nichts zu merken
  b.textContent=drin?'✓':'＋';
  b.classList.toggle('an',drin);
  b.title=drin?'Aus „'+LIEBLINGS_NAME+'" wieder herausnehmen'
              :'Zu „'+LIEBLINGS_NAME+'" hinzufügen (die Playlist entsteht beim ersten Mal von selbst)';
}
async function lieblingToggle(){
  const k=aktKey(); if(!k){toast('Es läuft gerade nichts.');return;}
  let p=lieblingsPlaylist();
  if(!p){
    await plApi({art:'create',name:LIEBLINGS_NAME});
    p=lieblingsPlaylist();
    if(!p){toast('Konnte die Lieblings-Playlist nicht anlegen.');return;}
  }
  if((p.items||[]).includes(k)){
    // Zweiter Klick nimmt wieder heraus (Spotify-Verhalten). Ueber 'ersetzen',
    // weil das die Liste exakt setzt — und weil ein Titel hier genau einmal
    // drin ist: gemocht oder nicht, ein Zwischending gibt es nicht.
    await plApi({art:'ersetzen',id:p.id,items:(p.items||[]).filter(x=>x!==k)});
    toast('♥ aus den Lieblingssongs genommen.');
  }else{
    await plApi({art:'add',id:p.id,key:k});
    toast('♥ zu den Lieblingssongs.');
  }
  lieblingMalen();
}

/* ---- Build 144, JB Punkt 2: „Playlist speichern/aktualisieren, wenn man
   Titel in eine gerade laufende Playlist zieht" — „ganz dezent irgendwo".
   Bis hierher war die Warteschlange immer fluechtig: man zog einen Titel
   hinein, hoerte ihn, und beim naechsten Start war er wieder weg. Jetzt weiss
   der Player ueber `playerState.plid`, aus welcher gespeicherten Playlist er
   spielt, und bietet das Sichern an — aber nur, wenn es wirklich etwas zu
   sichern gibt (Calm-Design: Anzeige nur bei Handlungsbedarf). */
function _plqZaehl(arr){const m=new Map(); (arr||[]).forEach(k=>m.set(k,(m.get(k)||0)+1)); return m;}
function plqGeaendert(){
  if(!playerState.plid)return false;
  const p=(plState||[]).find(x=>x.id===playerState.plid); if(!p)return false;
  // Vergleich als MENGE (sortiert), nicht als Reihenfolge: Mischen ist eine
  // Wiedergabe-Entscheidung, keine Playlist-Aenderung — zaehlte die
  // Reihenfolge mit, stuende nach JEDEM Zufalls-Start sofort „geaendert" da
  // und der Hinweis waere wertlos. Sortiert vergleichen erfasst Duplikate
  // richtig (die sind seit Build 138 ausdruecklich erlaubt).
  const a=(p.items||[]).slice().sort(), b=playerState.queue.slice().sort();
  return a.length!==b.length||a.some((k,i)=>k!==b[i]);
}
async function plqSichern(){
  const p=(plState||[]).find(x=>x.id===playerState.plid); if(!p)return;
  // Nicht-destruktiv (HARTE REGEL): die gespeicherte REIHENFOLGE bleibt
  // stehen, Entferntes faellt heraus, Neues haengt hinten an. Wer bei
  // gemischter Wiedergabe einen Titel hineinzieht, zerschiesst damit also
  // nie die Ordnung seiner Playlist. `rest` zaehlt je Titel herunter, damit
  // mehrfach vorhandene Titel nicht verloren gehen.
  const rest=_plqZaehl(playerState.queue), alt=[];
  (p.items||[]).forEach(k=>{const n=rest.get(k)||0; if(n>0){alt.push(k); rest.set(k,n-1);}});
  const neu=playerState.queue.filter(k=>{const n=rest.get(k)||0; if(n>0){rest.set(k,n-1); return true;} return false;});
  const items=alt.concat(neu);
  await plApi({art:'ersetzen',id:p.id,items});
  renderPlayerQueue();
  toast('💾 „'+p.name+'" aktualisiert ('+items.length+' Titel'+(neu.length?', '+neu.length+' neu':'')+').');
}
function renderPlayerQueue(){
  // rendert in BEIDE Ziele: seitliche Liste im Player + eigenes Playlist-Fenster
  const html=playerState.queue.map((k,i)=>{const x=libFind(k)||{titel:k};
    const aus=!artPasst(x||{});
    // Abo-Folgen: die CD-Nummer (#12) vor den Titel — so ist die Reihenfolge sofort klar (JB 21.07.)
    const nr=x.abo_nr?`<span class="pl-nr" title="Folge ${x.abo_nr}">#${x.abo_nr}</span> `:'';
    return `<div class="pl-item ${i===playerState.idx?'akt':''}${(i===plqSel||plqAuswahl.has(i))?' sel':''}${aus?' artaus':''}" draggable="true" tabindex="0" data-i="${i}" `+
      `ondragstart="plqDragStart(event,${i})" ondragover="plqDragOver(event)" ondrop="plqDrop(event,${i})" `+
      `onclick="plqSelect(${i},event)" ondblclick="plQueueKlick(${i})" oncontextmenu="return plItemKontext(event,${i})" title="Klick = auswählen · Doppelklick/Enter = abspielen · Rechtsklick = Menü · Entf = aus Playlist löschen · ↑/↓ = Auswahl · Ziehen = umsortieren">${i+1}. ${nr}${esc(x.titel||k)}</div>`;}).join('')
    ||'<div class="pl-leer">Leer — Titel aus der Bibliothek hierher ziehen.</div>';
  const q=document.getElementById('pl-queue'); if(q){q.innerHTML=html; q.onpointerdown=plqBandStart;}
  const qw=document.getElementById('pl-queue-win'); if(qw){qw.innerHTML=html; qw.onpointerdown=plqBandStart;}
  // Build 144c (JB): Der Rahmen soll schon ein, zwei Reihen ÜBER der Liste
  // beginnen dürfen. Dort liegt gar nicht mehr die Liste, sondern ihr
  // Behälter — im Player die Titel-/Steuerungs-Spalte, im herausgelösten
  // Fenster die Karte mit der Kopfzeile. Beide hören jetzt mit; Bedienelemente
  // filtert plqBandStart ohnehin heraus, und plqZugLaeuft verhindert, dass aus
  // den zwei mithörenden Ebenen zwei Bänder werden.
  const seite=document.querySelector('#view-player .pl-side'); if(seite)seite.onpointerdown=plqBandStart;
  const fenster=document.querySelector('#view-plq .card'); if(fenster)fenster.onpointerdown=plqBandStart;
  /* Build 144e (JB mit Bild): „genauso wie oben, sollte man auch von UNTEN ein
     fenster ziehen koennen … solange es in dem fenster ist, ist ein feld
     ziehen gewaehrleistet." Gemessen: die Karte ist nur so hoch wie ihr
     INHALT, nicht wie das Panel — im Playlist-Fenster lagen 232 px Schwarz
     darunter, an denen kein Zuhoerer hing. Das FENSTER ist der `panel-body`,
     also hoert der. Die Videoflaeche ist oben ausgenommen, und ohne sichtbare
     eigene Liste springt nichts an (Reiter-Panels). */
  ['#view-player','#view-plq'].forEach(sel=>{
    const v=document.querySelector(sel), koerper=v&&v.closest('.panel-body');
    if(koerper)koerper.onpointerdown=plqBandStart;
  });
  const za=document.getElementById('plq-anzahl');
  if(za)za.textContent=playerState.queue.length?(playerState.queue.length+' Titel'):'';
  // Der Sichern-Hinweis haengt an BEIDEN Playlist-Sichten und erscheint nur,
  // wenn die Warteschlange von ihrer gespeicherten Playlist abweicht.
  const dreckig=plqGeaendert();
  document.querySelectorAll('.plq-sichern').forEach(el=>{el.style.display=dreckig?'':'none';});
  // Playlist-Fenster trägt den echten Quellen-Namen (Radio / Playlist-Name /
  // Bibliothek / Mix …) statt statisch „Player-Playlist" (JB 21.07.).
  const pt=document.getElementById('plq-titel');
  if(pt)pt.textContent=playerState.queue.length?(playerState.quelle||'Playlist'):'Playlist';
}

/* ---- Transkript-Volltextsuche (JB 21.07.): findet, in welchem Video ein
   Begriff wann gesagt wird; Klick auf eine Fundstelle spielt das Video ab
   und springt an die Stelle (Tube-Archivist-Muster). ---- */
function tsMarkiere(text,q){
  const i=text.toLowerCase().indexOf(q.toLowerCase());
  if(i<0)return esc(text);
  return esc(text.slice(0,i))+'<mark>'+esc(text.slice(i,i+q.length))+'</mark>'+esc(text.slice(i+q.length));
}
async function transkriptSuche(){
  const q=(document.getElementById('libsuche').value||'').trim();
  if(q.length<2){toast('Bitte mindestens 2 Zeichen für die Transkript-Suche.');return;}
  let ov=document.getElementById('tsuche-ov');
  if(!ov){ov=document.createElement('div'); ov.id='tsuche-ov';
    ov.onclick=e=>{if(e.target===ov)ov.classList.remove('an');};
    ov.innerHTML='<div class="tsuche-box"><div class="tsuche-kopf">'+
      '<b>🔎 Im Transkript</b><input type="text" id="tsuche-inp" placeholder="Begriff…" '+
      'onkeydown="if(event.key===\\'Enter\\')tsuchLauf()"><button class="tog" onclick="tsuchLauf()">Suchen</button>'+
      '<button class="ib" title="Schließen" onclick="document.getElementById(\\'tsuche-ov\\').classList.remove(\\'an\\')">✕</button></div>'+
      '<div class="tsuche-body" id="tsuche-body"></div></div>';
    document.body.appendChild(ov);
  }
  document.getElementById('tsuche-inp').value=q;
  ov.classList.add('an');
  tsuchLauf();
}
async function tsuchLauf(){
  const q=(document.getElementById('tsuche-inp').value||'').trim();
  const body=document.getElementById('tsuche-body');
  if(q.length<2){body.innerHTML='<div class="leer">Mindestens 2 Zeichen.</div>';return;}
  body.innerHTML='<div class="leer">Durchsuche Transkripte…</div>';
  try{
    const r=await fetch('/api/transkript_suche?q='+encodeURIComponent(q));
    const d=await r.json(); const tr=d.treffer||[];
    if(!tr.length){body.innerHTML='<div class="leer">Nichts gefunden. (Nur Videos mit heruntergeladenen Untertiteln/Transkripten werden durchsucht.)</div>';return;}
    body.innerHTML=tr.map(v=>`<div class="tsuche-treffer"><div class="tsuche-t-titel">${esc(v.titel)}</div>`+
      v.treffer.map(t=>`<button class="tsuche-z" onclick="tsSpring('${v.key}',${t.zeit})"><span class="zt">${zeit(t.zeit)}</span>${tsMarkiere(t.text,q)}</button>`).join('')+
      '</div>').join('');
  }catch(e){body.innerHTML='<div class="leer">Suche fehlgeschlagen.</div>';}
}
function tsSpring(key,zeitSek){
  document.getElementById('tsuche-ov').classList.remove('an');
  ensurePlayer();
  playerPlay([key]);
  let versuche=0;
  const spring=()=>{const el=document.getElementById('pl-el');
    if(el&&el.duration){el.currentTime=Math.min(el.duration,zeitSek); el.play&&el.play().catch(()=>{});}
    else if(versuche++<40)setTimeout(spring,150);};
  setTimeout(spring,300);
}

/* ================= Playlists ================= */
let plState=[];
async function plLaden(){try{const r=await fetch('/api/playlists'); const d=await r.json(); plState=d.items||[]; plMalen();}catch(e){}}
function plMalen(){
  const sel=document.getElementById('plsel'); if(!sel)return;
  const cur=sel.value;
  // Build 118 (JB): „Neue Playlist" steht als erster Eintrag IM Feld — dafür
  // braucht es keinen eigenen Knopf mehr daneben.
  sel.innerHTML='<option value="">— keine —</option><option value="__neu">＋ Neue Playlist…</option>'+
    plState.map(p=>`<option value="${p.id}">${esc(p.name)} (${p.items.length})</option>`).join('');
  if(plState.find(p=>p.id===cur))sel.value=cur;
  if(libPlaylistView&&!plState.find(p=>p.id===libPlaylistView))libPlaylistView='';   // gelöschte Playlist? Ansicht schließen
  plViewRender();
  // Build 144d: Die Playlists kommen erst per Netz-Abruf — bis dahin weiss der
  // ＋-Knopf nicht, ob der laufende Titel schon ein Liebling ist. Sobald sie da
  // sind, wird er nachgezogen (und ebenso nach jeder Playlist-Aenderung).
  if(typeof lieblingMalen==='function')lieblingMalen();
}
// Playlist „öffnen": Bibliothek zeigt nur diese Playlist. Nochmal klicken schließt sie wieder.
function plWahl(){                                    // Playlist WÄHLEN = sofort öffnen (JB 14.07.)
  const sel=document.getElementById('plsel');
  if(sel.value==='__neu'){sel.value=''; plCreate(); return;}   // Build 118: Anlegen aus dem Feld
  const id=sel.value;
  libPlaylistView=id||'';                              // „— keine —" = schließen, ohne Meckern
  plViewRender(); libMalen();
}
function plView(){                                     // Knopf: offene Ansicht schließen / wieder öffnen
  const id=document.getElementById('plsel').value;
  libPlaylistView=libPlaylistView?'':(id||'');
  plViewRender(); libMalen();
}
function plViewSchliessen(){libPlaylistView=''; plViewRender(); libMalen();}
function plViewRender(){
  const btn=document.getElementById('plviewbtn');
  const p=plState.find(x=>x.id===libPlaylistView);
  // Build 121 (JB: „wenn ich keine Playlist angewählt habe, wieso werden diese
  // Knöpfe angezeigt?"): ohne gewählte Playlist gibt es nichts zu tun ⇒ die
  // Knöpfe sind gar nicht erst da. Abspielen lebt oben in der Steuerzentrale.
  const sel0=document.getElementById('plsel');
  const gewaehlt=!!((sel0&&sel0.value&&sel0.value!=='__neu')||libPlaylistView);
  const werk=document.getElementById('plwerkbtn');
  if(werk)werk.style.display=gewaehlt?'':'none';
  if(btn)btn.style.display=gewaehlt?'':'none';
  // Build 118 (JB): geöffnete Playlist ⇒ Zurück-Pfeil, sonst das Listen-Symbol.
  if(btn){btn.classList.toggle('an',!!libPlaylistView);
    btn.textContent=libPlaylistView?'↩':'📃';
    btn.title=libPlaylistView?'Zurück zur ganzen Bibliothek':'Titel dieser Playlist anzeigen';
    const sel=document.getElementById('plsel');
    btn.disabled=!libPlaylistView&&!(sel&&sel.value);   // nichts gewählt -> Knopf aus statt Alert
  }
  const info=document.getElementById('plinfo');
  if(info&&libPlaylistView&&p)info.innerHTML=`📃 <b>${esc(p.name)}</b> — ${p.items.length} Titel · Ziehen = Reihenfolge ändern · <a href="#" onclick="plViewSchliessen();return false" style="color:var(--akz2)">Zurück zur Bibliothek</a>`;
  else if(info&&!libPlaylistView&&/^📃/.test(info.textContent||''))info.textContent='';
}
async function plRemove(key){
  if(!libPlaylistView)return;
  await plApi({art:'remove',id:libPlaylistView,key});   // plApi lädt plState neu → plMalen → plViewRender
  libMalen();
}
async function plApi(body){await fetch('/api/playlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); await plLaden();}

/* ---- Titel auf eine Playlist ziehen (Build 135, JB Punkt 4) --------------
   Bisher ging Einreihen nur über das ＋-Menü an jeder Kachel — bei mehreren
   Titeln also viele Klicks. Jetzt zieht man die Auswahl auf die
   Playlist-Liste. Steht dort „— keine —", entsteht eine neue Playlist: genau
   JBs Wunsch, denn beim Ziehen weiß man oft erst im Moment des Loslassens,
   dass man eine neue braucht. */
let plLetzterWurf=null;                                // fürs Rückgängig
function plZiehKeys(ev){
  // Wird ein Titel gezogen, der Teil der Auswahl ist, reist die GANZE
  // Auswahl mit — sonst nur der eine. Das ist das Verhalten aus dem
  // Explorer und verhindert, dass eine mühsame Auswahl unbemerkt verfällt.
  let key=''; try{key=ev.dataTransfer.getData('ytdl/key')||'';}catch(e){}
  if(!key)return [];
  return (libAuswahl.has(key)&&libAuswahl.size>1)?[...libAuswahl]:[key];
}
function plselDragOver(ev){
  let hat=false; try{hat=[...ev.dataTransfer.types].includes('ytdl/key');}catch(e){}
  if(!hat)return;
  ev.preventDefault(); ev.dataTransfer.dropEffect='copy';
  ev.currentTarget.style.outline='2px dashed var(--akz)';
}
function plselDragLeave(ev){ ev.currentTarget.style.outline=''; }
async function plselDrop(ev){
  ev.preventDefault(); ev.currentTarget.style.outline='';
  const keys=plZiehKeys(ev); if(!keys.length)return;
  let id=document.getElementById('plsel').value;
  let neu=false;
  if(!id){                                             // „— keine —" = neue anlegen
    const vorschlag=(libFind(keys[0])||{}).titel||'Neue Playlist';
    const n=prompt('Neue Playlist anlegen — Name:', vorschlag.slice(0,40));
    if(!n||!n.trim())return;
    await plApi({art:'create',name:n.trim()});
    id=(plState[plState.length-1]||{}).id; neu=true;
    if(!id){toast('Playlist ließ sich nicht anlegen.');return;}
  }
  const p=plState.find(x=>x.id===id);
  // Build 138 (JB): Doppelte Titel sind erlaubt — „Ist ja meine Entscheidung."
  // Es wird also NICHT mehr gefiltert. Fürs Rückgängig merken wir uns den
  // Stand VOR dem Wurf und stellen ihn exakt wieder her; ein „remove" je
  // Titel träfe alle Vorkommen, nicht nur die gerade hinzugefügten.
  const vorher=((p&&p.items)||[]).slice();
  for(const k of keys)await plApi({art:'add',id,key:k});
  plLetzterWurf={id,vorher,plNeu:neu};
  const name=(plState.find(x=>x.id===id)||{}).name||'Playlist';
  const schon=keys.filter(k=>vorher.includes(k)).length;
  toastMitZurueck((neu?'📃 „'+name+'" angelegt · ':'')+keys.length+' Titel → „'+name+'"'+
    (schon?' ('+schon+' schon drin — jetzt doppelt)':''), 'plZurueck()');
}
async function plZurueck(){
  const w=plLetzterWurf; if(!w)return;
  plLetzterWurf=null;
  if(w.plNeu)await plApi({art:'delete',id:w.id});       // frisch angelegte Liste wieder weg
  else await plApi({art:'ersetzen',id:w.id,items:w.vorher});
  toast('↩ Rückgängig.');
}
function toastMitZurueck(text,ruf){
  // Wie toast(), nur mit einem Knopf daneben. Bewusst KEIN eigener Kasten:
  // dieselbe Stelle, dieselbe Optik, damit nichts Neues zu lernen ist.
  let t=document.getElementById('toast');
  if(!t){t=document.createElement('div'); t.id='toast'; document.body.appendChild(t);}
  t.innerHTML=esc(text)+' <button class="btn mini" style="margin-left:10px" onclick="'+ruf+
              ';document.getElementById(\\'toast\\').classList.remove(\\'an\\')">↩ Rückgängig</button>';
  t.classList.add('an');
  clearTimeout(t._weg); t._weg=setTimeout(()=>t.classList.remove('an'),7000);
}
/* Playlist-Optionen fürs Ausklapp-Untermenü (kmFuellen zeigt ab 9 automatisch die Suche) */
function plOptionen(key){
  const rein=async(id)=>{await plApi({art:'add',id,key});
    const p=plState.find(x=>x.id===id), t=libFind(key);
    if(p)plInfo('„'+((t&&t.titel)||'').slice(0,22)+'" → '+p.name+' ✓');};
  const opt=plState.map(p=>[p.name+' ('+p.items.length+')', false, ()=>rein(p.id)]);
  opt.push(['＋ Neue Playlist…', false, async()=>{
    const n=prompt('Name der neuen Playlist:'); if(!n||!n.trim())return;
    await plApi({art:'create',name:n.trim()});
    const id=(plState[plState.length-1]||{}).id; if(id)rein(id);}]);
  return opt;
}
async function plCreate(){const n=prompt('Name der neuen Playlist:'); if(n&&n.trim()){await plApi({art:'create',name:n.trim()});
  const neu=plState[plState.length-1]; if(neu){document.getElementById('plsel').value=neu.id; plMalen();}}}
async function plDelete(){const id=document.getElementById('plsel').value; if(!id)return;
  const p=plState.find(x=>x.id===id); if(p&&confirm('Playlist „'+p.name+'" löschen? (Dateien bleiben erhalten)'))await plApi({art:'delete',id});}
async function plRename(){const id=document.getElementById('plsel').value; if(!id)return;
  const p=plState.find(x=>x.id===id); const n=prompt('Neuer Name:',p?p.name:''); if(n&&n.trim())await plApi({art:'rename',id,name:n.trim()});}
async function plAdd(key){
  let id=document.getElementById('plsel').value;
  if(!id){
    if(plState.length){alert('Bitte oben zuerst eine Playlist wählen — oder ＋ Neu.');return;}
    const n=prompt('Neue Playlist — Name:'); if(!n||!n.trim())return;
    await plApi({art:'create',name:n.trim()}); id=(plState[plState.length-1]||{}).id;
    document.getElementById('plsel').value=id; plMalen();
  }
  await plApi({art:'add',id,key});
  const p=plState.find(x=>x.id===id), t=libFind(key);
  if(p)plInfo('„'+((t&&t.titel)||'').slice(0,22)+'" → '+p.name+' ✓');
}
function plPlaySel(){const id=document.getElementById('plsel').value; const p=plState.find(x=>x.id===id);
  if(!id||!p){
    // KEINE Playlist gewählt (JB 14.07.): dann die aktuell ANGEZEIGTE Bibliothek
    // (Suche/Filter/Sortierung/🎶🎬 zählen) komplett als Ad-hoc-Playlist abspielen.
    let alle=libGefiltert().filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x)).map(x=>x.id);
    if(!alle.length){alert('Nichts Abspielbares in der aktuellen Ansicht (Suche/Filter prüfen).');return;}
    if(playShuffle)mische(alle);
    playerPlay(alle,0,'Bibliothek'); return;
  }
  if(!p.items.length){alert('Diese Playlist ist leer.');return;}
  let ids=p.items.slice(); if(playShuffle)mische(ids);
  const start=ids.findIndex(k=>{const x=libFind(k); return x&&x.vorhanden&&artPasst(x);});
  if(start<0){alert('Nach dem 🎶/🎬-Filter bleibt in dieser Playlist nichts übrig.');return;}
  playerPlay(ids,start,p.name,p.id);}   // p.id: die Warteschlange weiss jetzt, wohin sie gehört
function plExport(){
  const id=document.getElementById('plsel').value;
  if(!id){alert('Bitte oben eine Playlist wählen.');return;}
  const a=document.createElement('a'); a.href='/api/playlist_export?id='+encodeURIComponent(id); a.download=''; a.click();
}
async function plImport(input){
  const f=input.files&&input.files[0]; if(!f)return;
  const text=await f.text(); input.value='';
  const name=prompt('Name der importierten Playlist:', f.name.replace(/\\.(m3u8?)$/i,''))||f.name;
  try{
    const r=await fetch('/api/playlist_import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,m3u:text})});
    const d=await r.json(); await plLaden();
    if(d.id){document.getElementById('plsel').value=d.id; plMalen();}
    plInfo('Import ✓ — '+(d.gefunden||0)+' Titel gefunden');
  }catch(e){plInfo('Import fehlgeschlagen');}
}

/* ---- Namens-Baukasten (Build 113, JB: „die Art der Beschreibung wählen …
   das sollte man anwählen und schieben können"). Die Tags in der Datei sind
   die Wahrheit — der Dateiname ist nur eine Projektion daraus (wie Picard/
   beets). Umbenannt wird NIE ohne Probelauf + Klick. ---- */
const NAME_BAUSTEINE=[['nr','Titelnummer','07'],['kuenstler','Künstler','Prince'],
  ['titel','Titel','Purple Rain'],['album','Album','Purple Rain'],['jahr','Jahr','1984'],
  ['zusatz','Zusatz (Live/Remix)','(Live)'],['id','Video-Id','[uW1UIDYmYyI]']];
let nameSchema=['kuenstler','titel','zusatz'], namePlan=null;
async function namenFenster(){
  const alt=document.getElementById('name-fly'); if(alt)alt.remove();
  try{const r=await fetch('/api/status'); const d=await r.json();
    if(d.config&&Array.isArray(d.config.name_schema)&&d.config.name_schema.length)
      nameSchema=d.config.name_schema.slice();
    window._nameAuto=!!(d.config&&d.config.auto_umbenennen);
  }catch(e){}
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='name-fly'; fly.tabIndex=-1; fly.style.height='auto'; fly.style.width='600px';
  fly.innerHTML='<div class="abo-fly-titel">🏷 Dateinamen — Bausteine wählen und schieben'+
    '<span class="spacer"></span><button class="ib" onclick="document.getElementById(\\'name-fly\\').remove()" title="Schließen (Esc)">✕</button></div>'+
    '<div id="name-liste" style="margin:8px 4px"></div>'+
    '<div style="margin:8px 4px;padding:8px;border:1px solid #2c2621;border-radius:8px;background:#141110">'+
      '<div style="font-size:11px;color:#8a7d74;margin-bottom:3px">So heißen die Dateien dann:</div>'+
      '<div id="name-vorschau" style="font-family:Consolas,monospace;font-size:13px;color:#e9ded3"></div></div>'+
    '<label class="chk" style="margin:6px 4px;display:block"><input type="checkbox" id="name-auto" onchange="nameAutoSetzen(this.checked)"> '+
      'Importierte Dateien automatisch so benennen (rückgängig jederzeit hier)</label>'+
    '<div id="name-plan" style="margin:6px 4px;max-height:220px;overflow:auto;font-size:12px"></div>'+
    '<div class="abo-staffel" style="margin-top:8px"><span id="name-stand" style="opacity:.7"></span><span class="spacer"></span>'+
      '<button class="btn mini" onclick="nameProbelauf()" title="Zeigt alt → neu für die ganze Bibliothek — es wird NICHTS umbenannt">🔍 Probelauf</button>'+
      '<button class="btn mini" id="name-go" disabled onclick="nameAnwenden()" title="Erst nach dem Probelauf: benennt die geprüften Dateien um">✔ Anwenden</button>'+
      '<button class="btn mini" onclick="nameUndo()" title="Nimmt den letzten Umbenenn-Lauf zurück (Protokoll + Vermerk in der Datei)">↩ Rückgängig</button></div>';
  document.body.appendChild(fly); nachVorn(fly);
  aboFlyoutPositionieren(fly,null);
  fly.style.height='auto';                             // wächst mit dem Inhalt …
  imBlick(fly);                                        // … aber NIE aus dem Bild (Build 114)
  fly.addEventListener('keydown',e=>{if(e.key==='Escape'){fly.remove(); e.stopPropagation();}});
  const chk=document.getElementById('name-auto'); if(chk)chk.checked=!!window._nameAuto;
  nameListeMalen(); fly.focus();
}
function nameListeMalen(){
  const box=document.getElementById('name-liste'); if(!box)return;
  const drin=NAME_BAUSTEINE.filter(b=>nameSchema.includes(b[0]))
    .sort((a,b)=>nameSchema.indexOf(a[0])-nameSchema.indexOf(b[0]));
  const raus=NAME_BAUSTEINE.filter(b=>!nameSchema.includes(b[0]));
  const zeile=(b,an,i)=>'<div class="name-zeile" draggable="'+(an?'true':'false')+'" data-id="'+b[0]+'" '+
    'style="display:flex;align-items:center;gap:8px;padding:5px 7px;margin:3px 0;border:1px solid #2c2621;'+
    'border-radius:7px;background:'+(an?'#1b1613':'transparent')+';cursor:'+(an?'grab':'default')+'">'+
    '<input type="checkbox" '+(an?'checked':'')+' onchange="nameBausteinToggle(\\''+b[0]+'\\',this.checked)">'+
    '<span style="flex:1">'+esc(b[1])+' <span style="color:#8a7d74">'+esc(b[2])+'</span></span>'+
    (an?'<button class="ib" onclick="nameSchieben(\\''+b[0]+'\\',-1)" title="nach vorn">▲</button>'+
        '<button class="ib" onclick="nameSchieben(\\''+b[0]+'\\',1)" title="nach hinten">▼</button>':'')+
    '</div>';
  box.innerHTML=(drin.length?'<div style="font-size:11px;color:#8a7d74">Reihenfolge — ziehen oder ▲▼:</div>':'')+
    drin.map((b,i)=>zeile(b,true,i)).join('')+
    (raus.length?'<div style="font-size:11px;color:#8a7d74;margin-top:6px">Nicht im Namen:</div>':'')+
    raus.map(b=>zeile(b,false,-1)).join('');
  box.querySelectorAll('.name-zeile[draggable="true"]').forEach(z=>{
    z.addEventListener('dragstart',e=>{e.dataTransfer.setData('text/plain',z.dataset.id); z.style.opacity='.4';});
    z.addEventListener('dragend',()=>{z.style.opacity='';});
    z.addEventListener('dragover',e=>e.preventDefault());
    z.addEventListener('drop',e=>{e.preventDefault();
      const von=e.dataTransfer.getData('text/plain'), auf=z.dataset.id;
      if(!von||von===auf)return;
      nameSchema=nameSchema.filter(x=>x!==von);
      nameSchema.splice(nameSchema.indexOf(auf),0,von);
      nameSchemaSpeichern();});
  });
  nameVorschau();
}
function nameBausteinToggle(id,an){
  nameSchema=an?nameSchema.concat([id]):nameSchema.filter(x=>x!==id);
  nameSchemaSpeichern();
}
function nameSchieben(id,d){
  const i=nameSchema.indexOf(id), j=i+d;
  if(i<0||j<0||j>=nameSchema.length)return;
  nameSchema.splice(j,0,nameSchema.splice(i,1)[0]);
  nameSchemaSpeichern();
}
function nameVorschau(){
  // Beispiel lokal bauen — dieselben Regeln wie im Server (Kopf mit " - ",
  // Zusatz/Album/Jahr/Id in Klammern hinten, Nummer klebt vorn).
  const bsp={nr:'07',kuenstler:'Prince',titel:'Purple Rain',album:'Purple Rain',jahr:'1984',
             zusatz:'(Live)',id:'[uW1UIDYmYyI]'};
  const kopf=[],kl=[];
  nameSchema.forEach(b=>{const w=bsp[b]; if(!w)return;
    if(b==='zusatz'||b==='album'||b==='jahr'||b==='id')kl.push(w.startsWith('(')||w.startsWith('[')?w:'('+w+')');
    else kopf.push(w);});
  let t=kopf.length?(nameSchema[0]==='nr'&&kopf.length>1?kopf[0]+' '+kopf.slice(1).join(' - '):kopf.join(' - ')):'';
  if(kl.length)t+=' '+kl.join(' ');
  const v=document.getElementById('name-vorschau');
  if(v)v.textContent=(t||'(keine Bausteine gewählt — Namen bleiben, wie sie sind)')+(t?'.mp3':'');
}
async function nameSchemaSpeichern(){
  nameListeMalen();
  const go=document.getElementById('name-go'); if(go)go.disabled=true;   // Plan ist veraltet
  namePlan=null;
  const pl=document.getElementById('name-plan'); if(pl)pl.innerHTML='';
  try{await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name_schema:nameSchema})});}catch(e){}
}
async function nameAutoSetzen(an){
  try{await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({auto_umbenennen:!!an})});
    toast(an?'Importe werden künftig automatisch benannt.':'Auto-Benennen aus.');}catch(e){}
}
async function nameProbelauf(){
  const stand=document.getElementById('name-stand'); if(stand)stand.textContent='prüfe …';
  try{
    const r=await fetch('/api/migration_probelauf?schema='+encodeURIComponent(nameSchema.join(',')));
    const d=await r.json(); namePlan=d;
    const box=document.getElementById('name-plan');
    box.innerHTML=d.eintraege.length?('<table style="width:100%;border-collapse:collapse">'+
      d.eintraege.map(x=>'<tr><td style="padding:2px 4px;color:'+(x.konflikt?'#e0a030':'#8a7d74')+'">'+
        (x.konflikt?'⚠':'✅')+'</td><td style="padding:2px 4px;color:#8a7d74">'+esc(x.alt.split(/[\\\\/]/).pop())+'</td>'+
        '<td style="padding:2px 4px">→ '+esc(x.neu.split(/[\\\\/]/).pop())+'</td></tr>'+
        (x.konflikt?'<tr><td></td><td colspan="2" style="padding:0 4px 4px;color:#e0a030;font-size:11px">'+esc(x.konflikt)+'</td></tr>':'')).join('')+
      '</table>'):'<div style="color:#8a7d74;padding:6px">Alle Dateien heißen schon so — nichts zu tun.</div>';
    if(stand)stand.textContent=d.bereit+' bereit, '+d.konflikte+' übersprungen'+(d.gesamt>d.eintraege.length?' (Liste zeigt die ersten '+d.eintraege.length+')':'');
    const go=document.getElementById('name-go'); if(go)go.disabled=!d.bereit;
  }catch(e){if(stand)stand.textContent='Probelauf fehlgeschlagen.';}
}
async function nameAnwenden(){
  if(!namePlan||!namePlan.bereit)return;
  if(!confirm('Jetzt '+namePlan.bereit+' Datei(en) umbenennen?\\n\\nDie Untertitel wandern mit, der alte Name wird IN der Datei vermerkt, und „↩ Rückgängig" macht alles zurück.'))return;
  const stand=document.getElementById('name-stand'); if(stand)stand.textContent='benenne um …';
  try{
    const r=await fetch('/api/umbenennen',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({go:true,schema:nameSchema})});
    const d=await r.json();
    toast('✔ '+d.umbenannt+' umbenannt'+(d.uebersprungen?', '+d.uebersprungen+' übersprungen':''));
    await nameProbelauf(); laden();
  }catch(e){if(stand)stand.textContent='Umbenennen fehlgeschlagen.';}
}
async function nameUndo(){
  if(!confirm('Den letzten Umbenenn-Lauf zurücknehmen?'))return;
  try{
    const r=await fetch('/api/umbenennen',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({art:'undo'})});
    const d=await r.json();
    toast(d.ok?('↩ '+d.zurueck+' Datei(en) zurückbenannt'+(d.blockiert?', '+d.blockiert+' blockiert':'')):(d.fehler||'nichts zurückzunehmen'));
    await nameProbelauf(); laden();
  }catch(e){toast('Rückgängig fehlgeschlagen.');}
}
async function plSyncConfig(){
  // Build 108 (JB): eigenes kleines Fenster statt prompt — Pfad vom letzten
  // Mal vorbelegt und 📁 öffnet den NATIVEN Windows-Ordnerdialog (über den
  // lokalen Server; der Browser darf selbst keine Pfade wählen).
  // Build 109 (JB-Failsafe): existiert der vorbelegte Pfad gerade NICHT
  // (Platte ab, Stick raus), werden Feld + Speicher-Knöpfe nur ausgegraut —
  // ein 2-s-Puls gibt alles von selbst frei, sobald der Ordner wieder da ist.
  // Tippen ändert den Merker NICHT (gemerkt wird erst beim Speichern):
  // Abbrechen + neu öffnen bringt die Vorbelegung zurück.
  const id=document.getElementById('plsel').value;
  if(!id){alert('Bitte zuerst eine Playlist wählen.');return;}
  const p=plState.find(x=>x.id===id);
  let letzter=''; try{letzter=localStorage.getItem('ytdl_sync_letzter')||'';}catch(e){}
  const alt=document.getElementById('sync-fly'); if(alt)alt.remove();
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='sync-fly'; fly.tabIndex=-1; fly.style.height='auto';
  fly.innerHTML='<div class="abo-fly-titel">⇄ Sync einrichten: '+esc(p.name||'')+
    '<span class="spacer"></span><button class="ib" onclick="document.getElementById(\\'sync-fly\\').remove()" title="Schließen (Esc)">✕</button></div>'+
    '<div style="display:flex;gap:6px;margin:8px 4px 4px">'+
      '<input type="text" id="sync-pfad" style="flex:1" placeholder="z. B. E:\\\\Musik — USB-Stick oder Handy-Ordner" value="'+esc(p.sync_ordner||letzter)+'">'+
      '<button class="btn mini" onclick="syncOrdnerWaehlen(this)" title="Nativen Windows-Ordnerdialog öffnen (erscheint auf deinem Bildschirm)">📁 wählen</button></div>'+
    '<div id="sync-tot" style="display:none;margin:6px 4px 0;color:#e0a030;font-size:.85em">⏳ Ordner gerade nicht erreichbar — Platte/Stick anschließen, das Fenster merkt es von selbst.</div>'+
    '<div class="abo-staffel" style="margin-top:8px"><span style="opacity:.7">Spiegeln löscht im Ziel nur Dateien, die die App selbst kopiert hat.</span><span class="spacer"></span>'+
      '<button class="btn mini" onclick="syncSpeichern(\\''+id+'\\',false)" title="Nur kopieren — es wird nie etwas gelöscht">Nur kopieren</button>'+
      '<button class="btn mini" onclick="syncSpeichern(\\''+id+'\\',true)" title="Exakt spiegeln — Entferntes verschwindet auch im Ziel (nur App-eigene Kopien)">Exakt spiegeln</button></div>';
  document.body.appendChild(fly); nachVorn(fly);
  aboFlyoutPositionieren(fly,null);
  fly.style.height='auto';                             // wächst mit dem Inhalt …
  imBlick(fly);                                        // … aber NIE aus dem Bild (Build 114)
  fly.addEventListener('keydown',e=>{if(e.key==='Escape'){fly.remove(); e.stopPropagation();}});
  fly.focus();
  syncPfadWachen(fly);
}
function syncPfadWachen(fly){
  // Build 109 (JB-Failsafe): Feld + Speicher-Knöpfe an der Wirklichkeit
  // ausrichten — toter Pfad grau + gesperrt, lebendiger frei. Der 2-s-Puls
  // räumt sich selbst auf, sobald das Fenster geschlossen ist. Leeres Feld
  // bleibt frei (leer speichern = Sync abschalten, wie bisher).
  const pruefen=async()=>{
    const f=document.getElementById('sync-fly');
    if(!f){clearInterval(takt);return;}
    const inp=document.getElementById('sync-pfad'); if(!inp)return;
    const wert=(inp.value||'').trim();
    let da=true;
    if(wert){
      try{const r=await fetch('/api/pfad_da?pfad='+encodeURIComponent(wert)); da=!!(await r.json()).da;}
      catch(e){da=true;}                    // Server kurz weg: nicht fälschlich sperren
    }
    const tot=!!wert&&!da;
    inp.style.opacity=tot?'.5':'';
    f.querySelectorAll('.abo-staffel .btn').forEach(b=>{b.disabled=tot;});
    const hin=document.getElementById('sync-tot'); if(hin)hin.style.display=tot?'':'none';
  };
  const takt=setInterval(pruefen,2000);
  const inp=document.getElementById('sync-pfad');
  if(inp)inp.addEventListener('input',()=>{clearTimeout(inp._t); inp._t=setTimeout(pruefen,300);});
  pruefen();
}
async function syncOrdnerWaehlen(btn){
  const inp=document.getElementById('sync-pfad'); if(!inp)return;
  if(btn){btn.disabled=true; btn.textContent='⏳ …';}
  try{
    const r=await fetch('/api/ordner_waehlen?start='+encodeURIComponent(inp.value||''));
    const d=await r.json();
    if(d.pfad){inp.value=d.pfad; inp.dispatchEvent(new Event('input'));}
    else if(d.fehler)toast(d.fehler);
  }catch(e){toast('Ordner-Dialog nicht erreichbar.');}
  if(btn){btn.disabled=false; btn.textContent='📁 wählen';}
}
async function syncSpeichern(id,spiegeln){
  const inp=document.getElementById('sync-pfad');
  const ordner=(inp&&inp.value||'').trim();
  try{if(ordner)localStorage.setItem('ytdl_sync_letzter',ordner);}catch(e){}
  await plApi({art:'sync_config',id,sync_ordner:ordner,sync_modus:spiegeln?'spiegeln':'kopieren'});
  const f=document.getElementById('sync-fly'); if(f)f.remove();
  if(ordner){toast('⇄ Sync: '+(spiegeln?'spiegeln':'kopieren')+' → '+ordner); plSyncNow(id);}
}
async function plSyncNow(id){
  id=(typeof id==='string')?id:document.getElementById('plsel').value;
  if(!id){alert('Bitte zuerst eine Playlist wählen.');return;}
  const p=plState.find(x=>x.id===id);
  if(!p||!p.sync_ordner){alert('Für diese Playlist ist noch kein Sync-Ordner eingerichtet („⇄ Sync…“).');return;}
  plInfo('synchronisiere …', true);                    // Fortschritt: bleibt
  try{
    const r=await fetch('/api/playlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({art:'sync',id})});
    const d=await r.json();
    if(d.fehler)info.textContent='Sync-Fehler: '+d.fehler;
    else info.textContent=`Sync ✓ ${d.kopiert} kopiert`+(d.geloescht?`, ${d.geloescht} gelöscht`:'')+`, ${d.im_ziel} im Ordner`;
  }catch(e){info.textContent='Sync fehlgeschlagen (App erreichbar?)';}
  plLaden();
}

async function biblio(id,art){
  await fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,art})});
  libLaden();
}
async function biblioNeuladen(id){
  await fetch('/api/biblio',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,art:'neuladen'})});
  zeigeView('queue');
}

document.getElementById('urls').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();hinzufuegen();}});
// Klick außerhalb schließt das Spalten-Menü
// Build 125: Das Menü hängt jetzt am <body>, liegt also NICHT mehr in
// .colmenuwrap — ohne die #libcolmenu-Prüfung hätte ein Klick auf einen
// eigenen Menüeintrag das Menü sofort zugeklappt.
document.addEventListener('click',e=>{
  if(e.target.closest('.colmenuwrap')||e.target.closest('#libcolmenu'))return;
  const m=document.getElementById('libcolmenu'); if(m)m.style.display='none';});
/* Tastenkürzel (JB 21.07., YouTube-/Player-Standard). Greifen NUR, wenn nicht in
   einem Eingabefeld getippt wird. ? zeigt die Legende. */
function tastenLegende(){
  /* Build 139 (JB: „Legende sollte etwas mehr Zeilenumbrueche haben"): Der
     Einzeiler war eine 300 Zeichen lange Wurst - man las ihn nicht, man
     suchte darin. Jetzt nach Themen gruppiert, jede Gruppe eine Zeile:
     Abspielen, Springen, Ton, Ansicht, Playlist. */
  // Die Legende liest die ECHTE Belegung (Hotkey-Editor) — eine hart
  // getippte Liste würde nach dem ersten Umbelegen lügen.
  const t=a=>hkLabel(a);
  const gruppen=[
    ['Abspielen', t('playpause')+' Play·Pause · '+t('naechster')+'/'+t('voriger')+' nächster/voriger Titel · '+t('wiederholen')+' Wiederholen'],
    ['Springen',  t('rueck10')+'/'+t('vor10')+' −/+10 s · '+t('sprungzurueck')+'/'+t('sprungvor')+' −/+'+sprungWeite()+' s · 0–9 zu 0–90 % · '+t('anfang')+'/'+t('ende')+' Anfang/Ende'],
    ['Ton',       t('lauter')+'/'+t('leiser')+' Lautstärke · '+t('stumm')+' stumm · '+t('langsamer')+'/'+t('schneller')+' Tempo'],
    ['Bild',      t('vollbild')+' Vollbild · '+t('pip')+' Bild-in-Bild · '+t('untertitel')+' Untertitel · '+t('subfrueher')+'/'+t('subspaeter')+' Untertitel-Versatz'],
    ['Playlist',  'Klick wählt · Doppelklick/Enter spielt · Entf löscht · ↑/↓ Auswahl']];
  toastHTML('<div style="font-size:11px;color:#8a7d74;margin-bottom:5px">Tastenkürzel</div>'+
    gruppen.map(([k,v])=>'<div style="display:flex;gap:10px;padding:2px 0;line-height:1.5">'+
      '<b style="flex:none;min-width:74px;color:var(--akz2)">'+k+'</b>'+
      '<span>'+esc(v)+'</span></div>').join(''), 9000);
}
function toastHTML(html,dauer){
  // Wie toast(), nur mit Zeilen statt einer Wurst. Bewusst dieselbe Stelle
  // und dieselbe Optik — es gibt nichts Neues zu lernen.
  let t=document.getElementById('toast');
  if(!t){t=document.createElement('div'); t.id='toast'; document.body.appendChild(t);}
  t.innerHTML=html; t.classList.add('an');
  clearTimeout(t._weg); t._weg=setTimeout(()=>t.classList.remove('an'), dauer||5000);
}
function _vol(d){plbVol(Math.max(0,Math.min(100,(plVol||0)+d)));}
function _rate(d){
  if(vlcAktiv()){                                     // Tempo-Hotkeys auch am Gerät VLC
    const r=Math.max(0.25,Math.min(4,Math.round(((vlcRateLetzte||1)+d)*100)/100));
    vlcRateLetzte=r; vlcBefehl('rate',{wert:r}); toast('⏩ Tempo '+r+'×'); return;}
  const el=document.getElementById('pl-el'); if(!el)return;
  el.playbackRate=Math.max(0.25,Math.min(4,Math.round((el.playbackRate+d)*100)/100));
  toast('⏩ Tempo '+el.playbackRate+'×');}
/* ---- Hotkey-Editor (JB-Wunsch, Marschbefehl 05.08.) ----------------------
   Die Player-Tasten sind eine TABELLE statt hart verdrahteter switch-Fälle:
   HK_DEF = Auslieferung, localStorage 'ytdl_hotkeys' = JBs eigene Belegung.
   Fest bleiben, was System- oder Listen-Konvention ist: Medientasten der
   Tastatur, Ziffern (0–90 %), Strg+←/→, Enter/Entf in Playlist- und
   Fertig-Liste — sonst zerschösse eine Umbelegung die Listenbedienung. */
const HK_DEF={playpause:['Space','KeyK'],rueck10:['KeyJ'],vor10:['KeyL'],
  sprungzurueck:['ArrowLeft'],sprungvor:['ArrowRight'],lauter:['ArrowUp'],leiser:['ArrowDown'],
  naechster:['KeyN'],voriger:['KeyP'],stumm:['KeyM'],vollbild:['KeyF'],pip:['KeyI'],
  untertitel:['KeyS'],anfang:['Home'],ende:['End'],wiederholen:['KeyR'],
  langsamer:['Shift+Comma'],schneller:['Shift+Period'],
  subfrueher:['Comma'],subspaeter:['Period']};
const HK_NAMEN={playpause:'Play / Pause',rueck10:'10 s zurück',vor10:'10 s vor',
  sprungzurueck:'Sprung zurück (←)',sprungvor:'Sprung vor (→)',lauter:'Lauter',leiser:'Leiser',
  naechster:'Nächster Titel',voriger:'Voriger Titel',stumm:'Stumm',vollbild:'Vollbild',
  pip:'Bild-in-Bild',untertitel:'Untertitel wechseln',anfang:'Zum Anfang',ende:'Zum Ende',
  wiederholen:'Wiederholen (Titel)',langsamer:'Tempo −',schneller:'Tempo +',
  subfrueher:'Untertitel früher (−0,5 s)',subspaeter:'Untertitel später (+0,5 s)'};
let HK={};
(function(){let g={}; try{g=JSON.parse(localStorage.getItem('ytdl_hotkeys')||'{}')||{};}catch(e){}
  for(const a in HK_DEF)HK[a]=(Array.isArray(g[a])&&g[a].length)?g[a].slice():HK_DEF[a].slice();})();

function hkSpeichern(){try{localStorage.setItem('ytdl_hotkeys',JSON.stringify(HK));}catch(e){}}
function hkCode(e){return (e.shiftKey?'Shift+':'')+e.code;}
function hkAktionFuer(code){for(const a in HK){if((HK[a]||[]).includes(code))return a;} return '';}
function hkTaste(code){return code.replace('Shift+','⇧').replace('Key','').replace('Arrow','')
  .replace('Space','⎵').replace('Comma',',').replace('Period','.')
  .replace('Up','↑').replace('Down','↓').replace('Left','←').replace('Right','→');}
function hkLabel(a){return (HK[a]||[]).map(hkTaste).join('/')||'—';}
function hkZeileMalen(a){const b=document.getElementById('hk-'+a); if(b)b.textContent=hkLabel(a);}
let _hkFang=null;
function hkFangen(a,btn){
  if(_hkFang)return;
  const alt=btn.textContent; btn.textContent='Taste drücken…';
  _hkFang=ev=>{
    ev.preventDefault(); ev.stopPropagation();
    document.removeEventListener('keydown',_hkFang,true); _hkFang=null; btn.textContent=alt;
    if(ev.code==='Escape')return;                      // Esc = abbrechen
    if(/^(Digit|Numpad)/.test(ev.code)||['Tab','Enter','Delete','Backspace','F5'].includes(ev.code)
       ||ev.ctrlKey||ev.metaKey||ev.altKey){
      toast('Diese Taste ist fest vergeben (Listen/Ziffern-Sprung/System).'); return;}
    const code=hkCode(ev), belegt=hkAktionFuer(code);
    if(belegt&&belegt!==a){toast('Schon belegt: „'+(HK_NAMEN[belegt]||belegt)+'" — dort erst ändern.'); return;}
    HK[a]=[code]; hkSpeichern(); hkZeileMalen(a);
  };
  document.addEventListener('keydown',_hkFang,true);
}
function hkZuruecksetzen(a){HK[a]=HK_DEF[a].slice(); hkSpeichern(); hkZeileMalen(a);}
function hkAlleZurueck(){for(const a in HK_DEF)HK[a]=HK_DEF[a].slice(); hkSpeichern();
  for(const a in HK_DEF)hkZeileMalen(a); toast('⌨ Alle Tasten auf Standard.');}
function hotkeyEditor(){
  const zeilen=Object.keys(HK_DEF).map(a=>'<div class="optrow"><span>'+HK_NAMEN[a]+'</span>'
    +'<span style="display:flex;gap:6px;align-items:center">'
    +'<b id="hk-'+a+'" style="min-width:56px;text-align:right;color:var(--akz2)">'+hkLabel(a)+'</b>'
    +'<button class="btn mini" onclick="hkFangen(\\''+a+'\\',this)">ändern</button>'
    +'<button class="ib" title="Standard wiederherstellen" onclick="hkZuruecksetzen(\\''+a+'\\')">↺</button></span></div>').join('');
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML='<div class="modal-box" style="max-width:470px"><div class="modal-head"><b>⌨ Hotkeys — Player-Tasten belegen</b>'
    +'<button class="ib" title="Schließen" onclick="this.closest(\\'.modal\\').remove()">✕</button></div>'
    +'<div style="padding:12px 16px;max-height:58vh;overflow:auto;display:flex;flex-direction:column;gap:6px">'+zeilen+'</div>'
    +'<div style="padding:0 16px 14px;display:flex;gap:8px;justify-content:space-between;align-items:center">'
    +'<span class="muted2" style="font-size:11px">„ändern" klicken, dann Taste drücken (Esc bricht ab). Gilt in diesem Browser.</span>'
    +'<button class="btn mini" onclick="hkAlleZurueck()">↺ Alle Standard</button></div></div>';
  ov.onclick=e=>{if(e.target===ov)ov.remove();};
  document.body.appendChild(ov);
}
document.addEventListener('keydown',e=>{
  const tgt=e.target;
  if(tgt&&tgt.matches&&tgt.matches('input,textarea,select'))return;
  if(tgt&&tgt.isContentEditable)return;
  // In der Fertig-Liste (JB 22.07.): fokussierte Zeile mit Enter abspielen,
  // mit Entf den Eintrag entfernen (Datei bleibt). Fokus kommt per Klick (tabindex).
  if(tgt&&tgt.dataset&&tgt.dataset.fid&&tgt.closest&&tgt.closest('#view-done')){
    if(e.key==='Enter'){e.preventDefault(); fertigPlay(tgt.dataset.fid); return;}
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault(); aktion(tgt.dataset.fid,'entfernen'); return;}
  }
  // In der Player-Playlist steuern die Tasten die LISTE (JB 22.07.): Pfeile bewegen die
  // Auswahl, Enter spielt, Entf löscht. Nur wenn der Fokus wirklich in der Liste sitzt —
  // sonst gelten ↑/↓ weiter global als Lautstärke.
  if(tgt&&tgt.closest&&tgt.closest('.pl-queue')){
    if(e.key==='ArrowDown'){e.preventDefault(); plqMoveSel(1); return;}
    if(e.key==='ArrowUp'){e.preventDefault(); plqMoveSel(-1); return;}
    if(e.key==='Enter'){e.preventDefault(); if(plqSel!==null)plQueueKlick(plqSel); return;}
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault(); plqAuswahlLoeschen(); return;}
  }
  const el=document.getElementById('pl-el');
  // Build 132: springt UND zeigt es an (JB). J/L bleiben bei 10 s wie bisher,
  // die Pfeiltasten nehmen die einstellbare Weite (Standard 5 s wie YouTube).
  const springen=s=>plbSpringen(s);
  const playPause=()=>{plTogglePlay();};               // VLC-fähig (Gerät zählt, nicht das Element)
  if(e.ctrlKey&&e.key==='ArrowRight'){e.preventDefault();playerNext();return;}
  if(e.ctrlKey&&e.key==='ArrowLeft'){e.preventDefault();playerPrev();return;}
  if(e.ctrlKey||e.metaKey||e.altKey)return;            // keine sonstigen Strg/Cmd/Alt-Kombis kapern
  if(/^(Digit|Numpad)[0-9]$/.test(e.code)&&el&&el.duration){   // 0–9 -> zu 0–90 % springen (YouTube-Standard)
    e.preventDefault(); el.currentTime=el.duration*(+e.code.slice(-1)/10); return;}
  if(_hkFang)return;                                   // der Fang-Dialog hört gerade selbst zu
  // Tabellen-Dispatcher (Hotkey-Editor): HK bestimmt, welche Taste was tut.
  const HK_TUN={
    playpause:()=>{if(el||vlcAktiv())playPause();},
    rueck10:()=>springen(-10), vor10:()=>springen(10),
    sprungvor:()=>springen(sprungWeite()), sprungzurueck:()=>springen(-sprungWeite()),
    lauter:()=>_vol(5), leiser:()=>_vol(-5),
    naechster:()=>playerNext(), voriger:()=>playerPrev(),
    stumm:()=>{if(el){el.muted=!el.muted; toast(el.muted?'🔇 stumm':'🔊 Ton an');}},
    vollbild:()=>plbFullscreen(), pip:()=>plbPip(),
    untertitel:()=>{if(typeof subCycle==='function')subCycle();},
    anfang:()=>{if(el)el.currentTime=0;},
    ende:()=>{if(el&&el.duration)el.currentTime=el.duration;},
    wiederholen:()=>{if(el){el.loop=!el.loop; toast(el.loop?'🔁 Wiederholen an':'▶ Wiederholen aus');}},
    langsamer:()=>{if(el)_rate(-0.25);}, schneller:()=>{if(el)_rate(0.25);},
    subfrueher:()=>subOffsetSchieben(-0.5), subspaeter:()=>subOffsetSchieben(0.5)
  };
  // JB 05.08. (Korrektur): Hotkeys gelten ÜBERALL im Browser-Fenster.
  const tu=HK_TUN[hkAktionFuer(hkCode(e))];
  if(tu){e.preventDefault(); tu(); return;}
  switch(e.code){                                      // fest: Medientasten der Tastatur
    case 'MediaPlayPause': e.preventDefault(); playPause(); break;
    case 'MediaTrackNext': e.preventDefault(); playerNext(); break;
    case 'MediaTrackPrevious': e.preventDefault(); playerPrev(); break;
    default:
      if(e.key==='?'){e.preventDefault(); tastenLegende();}
  }});

/* ================= Init (läuft einmal beim Seiten-Start) ================= */
themeIcon();
layoutAnViewport();                              // gespeichertes Layout an die aktuelle Fenstergröße anpassen (JB 22.07.: „am Anfang ausserhalb des Bildschirms")
renderPanels();
layoutEntwirren();                               // alte Layouts mit Überlappungen einmalig bereinigen
L.panels.forEach(p=>merkeView(p.id,p.active));   // Start-Stationen in den Verlauf
layoutSelectFuellen();
einstellungenModalInit();                        // Einstellungs-Karte ins Modal umziehen
playerLayoutSet();
transportRender();
vizFarbeAktualisieren(); vizModeRender();
geraetMalen();                                    // Gerät-Knopf (Browser/VLC) mit gemerktem Stand
cmdNowRender();
laden();
libLaden();                                       // Bibliothek sofort laden (Player braucht sie)
plLaden();
aboLaden();
setInterval(laden,1000);
</script>

<!-- ===== Schwebende Flaechen (Build 125) =====================================
     Diese Menues standen frueher in .libbar. Seit Build 122 traegt .libbar
     container-type fuer die schmalen Leisten - und Containment sperrt jede
     absolut/fixed positionierte Flaeche darin ein: gemessen lag das Menue mit
     z-index 6100 UNTER einem Panel mit z-index 14. Sie wohnen deshalb hier,
     direkt unter <body>, und werden von popoverBei() an ihrem Knopf
     ausgerichtet. Der Waechter-Test test_schwebende_flaechen_nicht_im_kaefig
     haelt das fest - auch fuer jede kuenftige Flaeche und jeden Kaefig. -->
      <div class="colmenu" id="libansicht" style="display:none">
        <!-- Build 118 (JB: „daneben steht Ansicht, ist das nicht auch eine Art
             Ansicht?"): die vier Darstellungs-Knöpfe wohnen jetzt HIER —
             eine Sache, ein Ort. Die Leiste bricht dadurch auch in schmalen
             Fenstern nicht mehr um (Anti-Scroll-Regel). -->
        <div class="mzeile"><span>Darstellung</span>
          <span style="display:flex;gap:3px">
            <button class="viewbtn" id="vb-kompakt" onclick="libKompaktToggle()" title="Kompakt: mehr Kacheln, nur Bild + Titel">▪▪</button>
            <button class="viewbtn an" id="vb-kachel" onclick="libAnsicht('kachel')" title="Kacheln">⊞</button>
            <button class="viewbtn" id="vb-alben" onclick="libAnsicht('alben')" title="Alben — gruppiert nach Künstler/Album">▤</button>
            <button class="viewbtn" id="vb-liste" onclick="libAnsicht('liste')" title="Liste">☰</button>
          </span></div>
        <!-- JB 05.08. („Ich finde den fernsehmodus nicht"): ganz nach OBEN —
             der wichtigste Modus versteckt sich nicht am Listenende. -->
        <button class="mbtn" onclick="fernsehModus()" title="Player als Vollbild: große Leiste, ⏪/⏩-Spulen, Untertitel-Panel per Fernbedienung">📺 Fernsehmodus</button>
        <div class="msep"></div>
        <!-- Build 144l (JB 25.07.): „Nur Songs" ist von hier in die Abspielart
             (▶-Symbol im Player) gewandert — Alles · Nur Ton · Nur Video ·
             Nur Songs, an einer Stelle, ehrlich beschriftet. -->
        <div class="mzeile"><span>Filter</span>
          <select id="libfilter" onchange="libMalen()">
            <option value="alle">Alle</option>
            <option value="herz">❤ Lieblingssongs</option>
            <option value="vorhanden">Nur vorhandene</option>
            <option value="verschoben">Nur verschobene/gelöschte</option>
          </select></div>
        <!-- Build 124 (JB): Ausgegraute (verschobene/gelöschte Dateien) sind
             standardmäßig AUS dem Blick — wer sie sucht, hakt hier ab. -->
        <label class="chk" style="padding:4px 6px"><input type="checkbox" id="libhidegray" checked onchange="libMalen()"> Ausgegraute ausblenden</label>
        <div class="msep"></div>
        <button class="mbtn" onclick="colMenuToggle(event)">⚙ Spalten wählen…</button>
        <button class="mbtn" id="libenrich" onclick="libEnrich(this)">↻ Fehlende Infos nachladen</button>
        <button class="mbtn" id="libarchivbtn" onclick="libArchivToggle()">🗄 Archiv anzeigen</button>
        <button class="mbtn" id="libselbtn" onclick="libSelectToggle()">☑ Mehrfach-Auswahl</button>
        <button class="mbtn" onclick="dublettenPopover(event);ansichtZu()">⧉ Dubletten finden…</button>
        <button class="mbtn" onclick="autotagAlle();ansichtZu()">🏷 Auto-Tagging (MusicBrainz)…</button>
        <!-- Build 122 (JB: „sollte selbstständig passieren"): der
             Ordner-Blick läuft jetzt von allein, sobald die Bibliothek
             angesehen wird (gedrosselt, im Hintergrund). Kein Menüpunkt
             mehr nötig. -->
      </div>
      <div class="colmenu" id="libcolmenu" style="display:none"></div>

      <!-- TV-Bibliothek (Sync Teilprojekt 2 v1): Vollbild-Overlay, Menü-Schnitt A
           (JB-bestätigt) — eigene Einträge für YouTube und Musik in der Leiste. -->
      <div id="tv">
        <div id="tv-kopf"></div>
        <div id="tv-inhalt"></div>
      </div>
      <div id="tv-info"></div>

</body>
</html>
"""
