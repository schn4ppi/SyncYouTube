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
.apidot{width:9px;height:9px;border-radius:50%;background:#6fcf7f;display:inline-block;flex:none}
.apidot.bad{background:#e08a6a}
.tools{display:flex;align-items:center;gap:8px;padding-top:6px;flex:none}
.iconbtn{width:34px;height:34px;border-radius:9px;border:1px solid #3a332e;background:#171310;color:#eee;
  font-size:16px;cursor:pointer;line-height:1}
.iconbtn:hover{border-color:var(--akz)}
.counter{position:relative;border:1px solid #3a332e;background:#171310;border-radius:999px;
  padding:6px 13px;font-size:13px;color:#d7c7bd;cursor:default;user-select:none;white-space:nowrap}
.counter b{color:var(--akz2);font-weight:700}
.counter .tip{display:none;position:absolute;right:0;top:calc(100% + 8px);z-index:200;min-width:190px;
  background:#211b16;border:1px solid #3a332e;border-radius:10px;padding:9px 11px;
  box-shadow:0 8px 24px rgba(0,0,0,.5);text-align:left;cursor:default}
.counter:hover .tip,.counter:focus .tip,.counter:focus-within .tip{display:block}
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
/* Höhe kommt aus der linken Steuerspalte (cmd-main align-items:stretch) — so ist
   die Command-Bar in Voll- UND Mini-Modus EXAKT gleich hoch, nichts springt (JB 21.07.). */
.dlbox-body{flex:1 1 auto;min-height:0;overflow:auto;background:var(--panel2,#1c1815);border-radius:0 8px 8px 8px}
.dlbox-body::-webkit-scrollbar{width:6px}.dlbox-body::-webkit-scrollbar-thumb{background:var(--panelln);border-radius:3px}
.dlbox-body .card{margin:0;background:transparent;border:0;padding:6px 10px}
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
.cmd-now{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center;gap:6px;font-size:12px;color:#9a8d84;
  border:1px solid #2e2823;border-radius:12px;padding:7px 14px;background:rgba(255,255,255,.022)}
.cmd-now.spielt{border-color:rgba(214,95,95,.45);box-shadow:0 0 0 1px rgba(214,95,95,.12),0 4px 16px rgba(0,0,0,.25)}
.cmd-now.dropziel{outline:2px dashed var(--akz);outline-offset:2px}
/* Build 117: Player offen ⇒ Kopfleiste zeigt keine doppelten Transport-
   Knöpfe mehr (8 Stück waren identisch). Radio bleibt — das gibt es dort
   sonst nirgends; Zeitleiste und Lautstärke ebenso. */
body.hat-player .cmd-now .mp-btn:not(.mp-radio){display:none}
html.light .cmd-now{border-color:#e3d8cc;background:rgba(0,0,0,.02)}
.cmd-nowtitel{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;font-size:12.5px;color:#d7c7bd;font-weight:500}
.cmd-nolabel{color:#6a5c52}
.cmd-seekline{display:flex;align-items:center;gap:8px}
.cmd-time{flex:none;font-size:11px;color:#8a7d74;min-width:36px;text-align:center;font-variant-numeric:tabular-nums}
#cmd-seek{flex:1;min-width:60px;height:14px;accent-color:var(--akz);cursor:pointer;margin:0}
#cmd-seek:disabled{opacity:.35;cursor:default}
.cmd-stat{display:flex;flex-direction:column;justify-content:center;align-items:flex-end;gap:5px;flex:none}
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
  .cmd-right{border-left:0;border-top:1px solid var(--panelln);padding-left:0;padding-top:6px;max-height:96px}
  .cmd-side,.cmd-stat{flex-direction:row;align-items:center}}
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
.pl-subzeile .subtxt{display:inline-block;background:rgba(0,0,0,.68);color:#fff;padding:4px 12px;border-radius:8px;font-size:15px;line-height:1.4}
.pl-subzeile.karaoke{top:6%;bottom:58px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px}
.kar-neben{color:rgba(255,255,255,.45);font-size:15px;max-width:92%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kar-akt{color:var(--akz2);font-size:23px;font-weight:700;text-align:center;max-width:94%;line-height:1.3}
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
.colmenu{position:absolute;top:calc(100% + 6px);left:0;z-index:300;background:#211b16;border:1px solid #3a332e;
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
.pl-media video{width:100%;height:100%;max-height:none;border-radius:8px;background:#000;object-fit:contain}
.pl-media audio{width:100%;flex:none;position:relative;z-index:2}
/* Visualizer: Canvas als animierter Hintergrund hinter dem Cover, Audio-Leiste oben drüber */
.pl-media{position:relative;container-type:inline-size;container-name:plmedia}
.pl-viz{position:absolute;inset:0;width:100%;height:100%;z-index:0;display:none}
.pl-media.viz-an .pl-viz{display:block}
.pl-vizwrap{position:relative;z-index:1;flex:1;display:flex;align-items:center;justify-content:center;min-height:0;overflow:hidden}
.pl-cover{max-width:96%;max-height:100%;border-radius:10px;object-fit:contain}
.pl-side{display:flex;flex-direction:column;flex:none;min-height:0;min-width:0}
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
/* Steuerleiste AUF dem Video/Cover (YouTube-Stil, JB 13.07.): Spulleiste oben,
   Transport links, Werkzeuge rechts; blendet bei Maus-Ruhe aus (.baridle). */
.pl-bar{position:absolute;left:0;right:0;bottom:0;z-index:6;display:flex;flex-direction:column;gap:1px;
  padding:4px 10px 7px;background:linear-gradient(transparent,rgba(0,0,0,.82));transition:opacity .25s}
.pl-media.baridle .pl-bar{opacity:0;pointer-events:none}
.pl-media.baridle{cursor:none}
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
html.light .btn,html.light .iconbtn,html.light .counter,html.light .chip,
html.light .viewbtn,html.light .tog{
  background:#fbf8f4;border-color:#d9cfc4;color:#2a2320}
html.light .btn.haupt{background:#f3e7d6;border-color:#d8b98a;color:#8a5a1e}
html.light .viewbtn.an,html.light .tog.an{background:#f3e7d6;border-color:#d8b98a;color:#8a5a1e}
html.light .counter b{color:#9a6a12}
html.light .counter .tip{background:#fff;border-color:#e6ddd3;box-shadow:0 8px 24px rgba(120,90,60,.18)}
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
<script>if(location.search.indexOf('embed=1')>=0)document.body.classList.add('embed');</script>
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
        <button class="btn mini" id="layoutedit-btn" onclick="layoutEditToggle()"
                title="Layout bearbeiten: Werkzeuge ausklappen, Fenster verschieben &amp; an 8 Griffen ziehen (ohne Überlappen) — AUS: Ziehen dockt nur als Tab an">✏ Layout</button>
        <button class="btn mini" id="mini-btn" onclick="miniToggle()" title="Mini-Player: schrumpft auf Cover + Regler, bleibt oben eingebettet">🔳 Mini</button>
        <span id="buildmark" title="Baustand — bei Problemen prüfen, ob dieser aktuell ist">Build 2026-07-14 · 118</span>
      </div>
      <div class="cmd-rowadd">
        <input id="cmd-url" class="cmd-url" placeholder="🔗 Link oder Playlist einfügen — Enter lädt… (Abos: 📡)"
               onkeydown="if(event.key==='Enter')cmdDownload()">
        <select id="cmd-qual" class="cmd-qual" title="Qualität (Auswahl wird gemerkt)" onchange="qualMerken(this.value)">
          <option value="beste">Beste</option><option value="2160p">2160p</option>
          <option value="1440p">1440p</option><option value="1080p">1080p</option>
          <option value="720p">720p</option><option value="audio">MP3</option>
        </select>
        <button class="cmd-dl" onclick="cmdDownload()" title="In die Warteschlange laden">⬇ Download</button>
        <button class="iconbtn sm" onclick="ganzerKanal(this)" title="Ganzen Kanal / ganze Playlist laden — löst den Link auf und stellt ALLE Videos in die Warteschlange (fragt vorher mit Anzahl)">📺</button>
      </div>
      <div class="cmd-row2">
        <div class="cmd-now" id="cmd-now" ondragover="cmdNowOver(event)" ondragleave="cmdNowLeave(event)" ondrop="cmdNowDrop(event)"
             title="Titel aus der Bibliothek hierher ziehen = in die Playlist einreihen"><span class="cmd-nolabel">// nichts läuft</span></div>
        <div class="cmd-stat">
          <span id="ffwarn" style="display:none;color:#e08a6a;font-size:11.5px;white-space:nowrap"
                title="ffmpeg.exe, ffprobe.exe und deno.exe müssen im Ordner „bin&quot; NEBEN der App liegen (im Komplett-Zip enthalten). Ohne ffmpeg: Videos nur bis ~720p, kein MP3, kein Cover.">⚠ bin-Ordner fehlt</span>
          <span class="cmd-count" id="counter" tabindex="0" title="Gesamtzahl aller je geladenen Dateien — drüberfahren für die Aufschlüsselung">⬇ <b id="counter_num">0</b><span class="tip" id="counter_tip"></span></span>
          <span class="apidot bad" id="apidot" title="API-Status"></span>
        </div>
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
      <div class="legrow"><b>▶</b> abspielen · <b>＋</b> zu Playlist (Liste wählen) · <b>📁</b> im Ordner zeigen · <b>⋯</b> mehr · <b>⊞/▤/☰</b> Kacheln/Alben/Liste · <b>⚙ Ansicht</b> Filter &amp; Werkzeuge</div>
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
            <option value="1">an (de/en, auch automatische)</option>
            <option value="0">aus</option>
          </select>
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
        <div class="colmenuwrap">
          <button class="tog" id="libansichtbtn" onclick="ansichtToggle(event)" title="Darstellung, Filter, Spalten, Archiv, Auswahl, Dubletten …">⚙ Ansicht</button>
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
            <div class="msep"></div>
            <div class="mzeile"><span>Filter</span>
              <select id="libfilter" onchange="libMalen()">
                <option value="alle">Alle</option>
                <option value="vorhanden">Nur vorhandene</option>
                <option value="verschoben">Nur verschobene/gelöschte</option>
              </select></div>
            <label class="chk" style="padding:4px 6px"><input type="checkbox" id="libhidegray" onchange="libMalen()"> Ausgegraute ausblenden</label>
            <div class="msep"></div>
            <button class="mbtn" onclick="colMenuToggle(event)">⚙ Spalten wählen…</button>
            <button class="mbtn" id="libenrich" onclick="libEnrich(this)">↻ Fehlende Infos nachladen</button>
            <button class="mbtn" id="libarchivbtn" onclick="libArchivToggle()">🗄 Archiv anzeigen</button>
            <button class="mbtn" id="libselbtn" onclick="libSelectToggle()">☑ Mehrfach-Auswahl</button>
            <button class="mbtn" onclick="dublettenPopover(event);ansichtZu()">⧉ Dubletten finden…</button>
            <button class="mbtn" onclick="autotagAlle();ansichtZu()">🏷 Auto-Tagging (MusicBrainz)…</button>
            <button class="mbtn" onclick="ordnerImportieren();ansichtZu()" title="Fremde Musik-/Videodateien im Downloads-Ordner in die Bibliothek aufnehmen">📥 Dateien aus dem Ordner aufnehmen</button>
          </div>
          <div class="colmenu" id="libcolmenu" style="display:none"></div>
        </div>
        <span class="spacer"></span>
      </div>
      <div id="libbulk" class="libbulk" style="display:none"></div>
      <div class="libbar plbar">
        <!-- Build 118 (JB): „Neue Playlist" steckt jetzt IM Auswahlfeld,
             Öffnen/Schließen ist ein Pfeil, Abspielen ein reiner Play-Knopf —
             aus vier Textknöpfen werden drei Symbole. -->
        <span style="font-size:12px;color:#8a7d74">Playlist:</span>
        <select id="plsel" onchange="plWahl()" title="Playlist wählen — Auswahl zeigt sie sofort in der Bibliothek"></select>
        <button class="ib" id="plviewbtn" onclick="plView()" title="Titel dieser Playlist unten in der Bibliothek anzeigen (nochmal = zurück zur ganzen Bibliothek)">📃</button>
        <button class="ib" onclick="plPlaySel()" title="Gewählte Playlist abspielen — ohne gewählte Playlist wandert die ganze angezeigte Bibliothek in den Player">▶</button>
        <button class="ib" onclick="plWerkzeuge(event)" title="Umbenennen · Löschen · Sync · .m3u-Export/-Import">⋯</button>
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
    <div class="card" id="pl-card" oncontextmenu="return playerKontext(event)">
      <div class="pl-media" id="pl-media" ondragover="plMediaOver(event)" ondrop="plMediaDrop(event)" title="Titel aus der Bibliothek hierher ziehen = abspielen / einreihen (Ad-hoc-Playlist, nichts wird gespeichert)"><div class="pl-leer">Kein Titel gewählt — in der Bibliothek auf ▶ klicken.</div></div>
      <div class="pl-side">
        <div class="pl-titel" id="pl-titel"></div>
        <div class="pl-ctrl">
          <!-- Steuerung lebt AUF dem Video (Leiste unten, YouTube-Stil) + im
               Rechtsklick-Menü — hier bleibt nur, was die Anordnung betrifft. -->
          <button class="btn mini" onclick="playerLayoutToggle()" title="Anordnung wechseln: Video oben ↔ Video links (Playlist rechts)">⇆ Layout</button>
          <button class="btn mini" id="plq-btn" onclick="plqFenster()" title="Player-Playlist als eigenes Fenster herauslösen / wieder eingliedern — als Fenster ist sie andockbar wie jeder Tab">🎶 Playlist</button>
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
        <span class="spacer"></span>
        <button class="btn mini" onclick="plqWerkzeuge(event)" title="Warteschlangen-Werkzeuge: als Playlist speichern · sortieren · Duplikate entfernen · leeren">⋯ Werkzeuge</button>
        <button class="btn mini" onclick="plqFenster()" title="Playlist wieder in den Player eingliedern — der Player bekommt seine Breite zurück">⧉ In den Player</button></div>
      <div class="pl-queue plq-gross" id="pl-queue-win" ondragover="plqZielOver(event)" ondrop="plqZielDrop(event)"
           title="Titel aus der Bibliothek hierher ziehen = einreihen"></div>
    </div>
  </div>

  <div id="view-abos">
    <div class="card">
      <div class="zeile">
        <input type="text" id="abo-url" placeholder="Kanal- oder Playlist-Link…" style="flex:1;min-width:150px"
               onkeydown="if(event.key==='Enter')aboCreate()">
        <select id="abo-qual">
          <option value="beste">Beste</option><option value="1080p">1080p</option>
          <option value="720p">720p</option><option value="audio">MP3</option>
        </select>
        <button class="btn" onclick="aboCreate()">＋ Abonnieren</button>
      </div>
      <div id="abo-liste" class="abo-liste"></div>
      <div class="hinweis">Beim Abonnieren werden die aktuellen Videos nur „gemerkt“ (nicht geladen) — automatisch
        geholt wird nur, was danach neu erscheint (Start + alle 6&nbsp;Stunden, leichter RSS-Puls).
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
  if(!t){t=document.createElement('div'); t.id='toast'; document.body.appendChild(t);}
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
  el.style.maxHeight=(vh-t-rand)+'px';
  el.style.maxWidth=(vw-l-rand)+'px';
  if(getComputedStyle(el).overflowY==='visible')el.style.overflowY='auto';
}
function alleImBlick(){document.querySelectorAll(SCHWEBEND).forEach(e=>imBlick(e));}
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
    '<div class="optrow"><span>Canvas-Hintergrund</span><label class="chk"><input type="checkbox" id="opt_canvas" '+
      (canvasAn?'checked':'')+' onchange="setCanvas(this.checked)"> animiertes Cover</label></div>'+
    '<div class="optrow"><span>Sleep-Timer</span><span><select id="opt_sleep" onchange="sleepSetzen(this.value)">'+
      '<option value="0">aus</option><option value="15">15 min</option><option value="30">30 min</option>'+
      '<option value="60">60 min</option><option value="titel">nach diesem Titel</option></select>'+
      '<span id="sleepval" style="color:#8a7d74;font-size:11px;margin-left:6px"></span></span></div>'+
    '<div class="optrow"><span>Dateinamen</span><button class="btn mini" onclick="namenFenster()" title="Bausteine wählen und schieben, Probelauf ansehen, anwenden oder zurücknehmen">🏷 Namens-Baukasten</button></div>'+
    '<div class="optrow"><span>Alle Einstellungen</span><button class="btn mini" onclick="einstellungenOeffnen()">⚙ Öffnen</button></div>'+
    '<div class="optrow"><span>📱 Fernsteuerung</span><button class="btn mini" id="fernbtn" onclick="fernToggle()">…</button></div>'+
    '<div id="ferninfo" style="font-size:11px;color:#8a7d74;padding:0 8px 6px"></div>';
  document.body.appendChild(m);
  const sel=m.querySelector('#opt_fehler'); if(sel)sel.value=fmin;
  const sk=m.querySelector('#opt_skin'); if(sk)sk.value=aktuellerSkin();
  const slp=m.querySelector('#opt_sleep'); if(slp)slp.value=sleepTitelende?'titel':'0'; sleepLabel();
  const ub=m.querySelector('#opt_ueb'); if(ub)ub.value=uebergang;
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
const VIEWS={add:'➕ Hinzufügen', queue:'⬇ Downloads', done:'✅ Fertig', log:'📜 Log', lib:'📚 Bibliothek', player:'▶ Player', plq:'🎶 Playlist', abos:'📡 Abos'};
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
  if(libSichtbar){if(!libTimer){libLaden();libTimer=setInterval(libLaden,5000);}}
  else{clearInterval(libTimer);libTimer=null;}
  if(L.panels.some(p=>p.active==='abos'))aboLaden();   // Abo-Fenster sichtbar -> Stand auffrischen
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
  if(d){d.className='apidot'+(ok?'':' bad'); d.title=ok?'API verbunden · 127.0.0.1:8776':'API getrennt — läuft die App?';}
  const t=document.getElementById('apitext'); if(t)t.textContent=ok?'API verbunden · 127.0.0.1:8776':'API getrennt — läuft die App?';
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
  }catch(e){apiStatus(false);}
}
/* ---- Handy-Fernsteuerung: Befehle vom Handy am PC-Player ausführen ---- */
let _remoteN=null;
function remoteAusfuehren(r){
  if(!r)return;
  if(_remoteN===null){_remoteN=r.n; return;}           // beim Start nur merken, alten Befehl nicht ausführen
  if(r.n===_remoteN)return; _remoteN=r.n;
  const el=document.getElementById('pl-el');
  if(r.cmd==='playkey'&&r.key)playerPlay([r.key]);
  else if(r.cmd==='play'&&el){if(el.paused)el.play(); else el.pause();}   // 'play' vom Handy = togglen
  else if(r.cmd==='pause'&&el)el.pause();
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
function fernInfoMalen(){
  const b=document.getElementById('fernbtn'), info=document.getElementById('ferninfo');
  const f=daten&&daten.fernsteuerung;
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
  if(at.laeuft&&info)info.textContent=`🏷 Auto-Tagging läuft … ${at.erledigt}/${at.gesamt} geprüft · ${at.getaggt} getaggt`;
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
async function cmdDownload(){
  const inp=document.getElementById('cmd-url'); const urls=(inp.value||'').trim(); if(!urls)return;
  // Mix/Playlist-Link erkannt? Fragen, ob die ganze Liste geladen werden soll.
  let ganze=false;
  const l=urls.toLowerCase();
  if(l.includes('list=') && (l.includes('watch?v=')||l.includes('youtu.be/')))
    ganze=confirm('Dieser Link gehört zu einer Playlist bzw. einem Mix.\\n\\nOK = die ganze Liste / den Mix laden (Mixe bis 50 Titel)\\nAbbrechen = nur dieses eine Video');
  else if(l.includes('/playlist?list='))
    ganze=true;                                        // reiner Playlist-Link = immer ganze Liste
  await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({urls,qualitaet:document.getElementById('cmd-qual').value,ganze_liste:ganze})});
  inp.value=''; cmdClipVerstecken(); laden();
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
async function ganzerKanal(btn){
  const inp=document.getElementById('cmd-url'); const url=(inp.value||'').trim();
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
  const qtext=({beste:'Beste',audio:'MP3'}[q])||q;
  const n=d.anzahl+(d.gedeckelt?'+':'');
  const gr=groesseSchaetzen(d.dauer_summe,q);
  const frage=d.mix
    ?('„'+d.name+'"\\n\\nDie ersten '+d.anzahl+' Titel des Mixes (ab dem Startvideo) in Qualität '+qtext+' laden?'+gr+'\\nSchon geladene werden übersprungen.')
    :('„'+d.name+'"\\n\\n'+n+' Videos gefunden.\\n\\nAlle in Qualität '+qtext+' laden?'+gr+'\\nSchon geladene werden übersprungen.');
  if(!confirm(frage))return;
  await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({urls:d.url,qualitaet:q,ganze_liste:true,limit:limit})});
  inp.value=''; cmdClipVerstecken(); laden();
  try{dlboxTab('queue');}catch(e){}
  toast('📺 „'+d.name+'": '+(d.mix?d.anzahl:n)+' Videos werden geladen.');
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
  document.body.classList.toggle('hat-player', !!document.getElementById('pl-el'));
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
    `<button class="mp-btn mp-tog mp-art" data-tr="art" onclick="playArtCycle()"></button>`+
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
  const info=document.getElementById('plinfo'); if(info)info.textContent='⬇ Per Drag&Drop hinzugefügt: '+url.slice(0,48);
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
  document.body.appendChild(fly);
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
async function aboCreate(){
  const inp=document.getElementById('abo-url'); const url=(inp.value||'').trim(); if(!url)return;
  const qual=document.getElementById('abo-qual').value; inp.disabled=true;
  try{
    const r=await fetch('/api/abo',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({art:'create',url,qualitaet:qual})});
    const d=await r.json();
    if(d.fehler)alert(d.fehler);
    else{inp.value=''; alert('Abonniert: „'+(d.name||url)+'" — '+d.basis+' aktuelle Videos gemerkt (nicht geladen). Neues wird automatisch geholt.');}
  }catch(e){alert('Abonnieren fehlgeschlagen (App erreichbar?)');}
  inp.disabled=false; aboLaden();
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
  const info=document.getElementById('plinfo'); if(info)info.textContent='📥 Ordner wird durchsucht …';
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
function kachelClick(ev,id){
  if(!libSelektierend(ev))return;
  if(ev.target.closest('button,a,input'))return;
  ev.preventDefault(); libSelectClick(ev,id);
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
  const info=document.getElementById('plinfo'); if(info)info.textContent='Metadaten für '+keys.length+' Titel werden nachgeladen …';
  libAuswahl.clear(); libMalen(); setTimeout(libLaden,4000);
}
async function bulkPlaylist(){
  const id=document.getElementById('plsel').value;
  if(!id){alert('Bitte oben eine Playlist wählen (Playlist-Leiste).');return;}
  for(const k of libAuswahl)await plApi({art:'add',id,key:k});
  document.getElementById('plinfo').textContent=libAuswahl.size+' zur Playlist hinzugefügt ✓';
}

/* ---- Abspielmodus (zyklisch), Shuffle, Meistgespielt, Zuletzt ---- */
function mische(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
// max. 5 Modi; klicken wechselt Icon + Verhalten
/* Abspielmodus wie bei Spotify: ZWEI getrennte Toggles statt eines 4-Stufen-
   Zyklus (JB 13.07.: „▶ sah aus wie Play, 🔁/🔂 zu klein, Modus nicht erkennbar").
   playShuffle = Zufall an/aus · playRepeat = aus/alle/eins. Die Knöpfe sind
   selbst gezeichnete SVGs (currentColor), aktiv = Akzentfarbe + Punkt darunter. */
const ICONS={
  play:'M8 5v14l11-7z',
  pause:'M6 5h4v14H6zm8 0h4v14h-4z',
  prev:'M6 6h2v12H6zm12 0v12l-8.5-6z',
  next:'M16 6h2v12h-2zM6 6l8.5 6L6 18z',
  shuffle:'M10.59 9.17 5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z',
  repeat:'M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z',
  repeat1:'M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4zm-4-2V9h-1l-2 1v1h1.5v4H13z',
  yt:'M21.6 7.2c-.2-.9-.9-1.6-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4c-.9.2-1.6.9-1.8 1.8C2 8.8 2 12 2 12s0 3.2.4 4.8c.2.9.9 1.6 1.8 1.8 1.6.4 7.8.4 7.8.4s6.2 0 7.8-.4c.9-.2 1.6-.9 1.8-1.8.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3z'};
function ico(n){return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+ICONS[n]+'"/></svg>';}
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
/* Abspielart (JB 14.07.): 🎶 nur Musik / 🎬 nur Videos / 🎶🎬 beides —
   Symbolwechsel wie beim Wiederholen. Wirkt auf Radio, Autoplay/⏭ und
   „Gefilterte abspielen"; ausgewählte Playlists spielen immer wörtlich. */
let playArt='alle';
try{const v=localStorage.getItem('ytdl_playart'); if(['alle','mp3','video'].includes(v))playArt=v;}catch(e){}
function playArtCycle(){
  playArt=playArt==='alle'?'mp3':(playArt==='mp3'?'video':'alle');
  try{localStorage.setItem('ytdl_playart',playArt);}catch(e){}
  transportRender();
  libMalen(); renderPlayerQueue();                     // Ansicht + Queue folgen sofort
}
function artPasst(x){
  if(playArt==='alle')return true;
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
  document.querySelectorAll('[data-tr="pp"]').forEach(b=>{
    b.innerHTML=ico(pe&&!pe.paused?'pause':'play');
    b.title=(pe&&!pe.paused)?'Pause':'Abspielen';});
  document.querySelectorAll('[data-tr="radio"]').forEach(b=>b.classList.toggle('an',radioAktiv));
  document.querySelectorAll('[data-tr="art"]').forEach(b=>{
    b.classList.toggle('an',playArt!=='alle');
    b.textContent=playArt==='mp3'?'🎶':(playArt==='video'?'🎬':'🎶🎬');
    b.title='Was spielt: '+(playArt==='alle'?'Musik + Videos':(playArt==='mp3'?'nur Musik':'nur Videos'))+
      ' — klicken zum Wechseln. Gilt überall: Bibliothek-Anzeige, Playlists (übersprungene Titel bleiben gedimmt drin), Radio und Autoplay.';
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
function radioKandidaten(){return libdaten.filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x));}
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
  const info=document.getElementById('plinfo'); if(info)info.textContent='📻 Radio läuft — endloser Mix aus deiner Bibliothek';
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
  const el=document.getElementById('pl-el');
  if(!el||!isFinite(el.duration)||!el.duration){toast('Titel lädt noch — gleich nochmal ✂ drücken.');return;}
  schnittZu();
  const dauer=el.duration;
  schnitt={id, a:0, b:(el.currentTime>1&&el.currentTime<dauer-1)?el.currentTime:dauer, dauer};
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
  document.body.appendChild(fly);
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
  const info=document.getElementById('plinfo'); if(info)info.textContent='✂ Ausschnitt wird erstellt …';
  try{
    const r=await fetch('/api/clip',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(daten)});
    const d=await r.json();
    if(d.fehler){if(info)info.textContent=''; alert('Ausschnitt: '+d.fehler); if(btn){btn.disabled=false;btn.textContent='✂ Ausschnitt speichern';}}
    else{if(info)info.textContent='✂ Ausschnitt erstellt: '+d.name; toast('✂ '+d.name); libLaden(); schnittZu();}
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

async function libLaden(){
  try{const r=await fetch('/api/bibliothek'); const d=await r.json(); libdaten=d.items||[]; libMalen();}catch(e){}
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
  let arr=libdaten.filter(x=>!!x.archiviert===libArchiv).filter(artPasst);   // 🎶/🎬-Schalter
  if(f==='vorhanden')arr=arr.filter(x=>x.vorhanden);
  else if(f==='verschoben')arr=arr.filter(x=>!x.vorhanden);
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
  m.style.display=zu?'block':'none'; if(zu)colMenuMalen();}
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
  if(!libAuswahl.size){bulk.style.display='none'; bulk.innerHTML=''; return;}
  bulk.style.display='';
  bulk.innerHTML=`<b>${libAuswahl.size} ausgewählt</b>`+
    `<button class="btn mini" onclick="bulkPlay()">▶ Abspielen</button>`+
    `<button class="btn mini" onclick="bulkPlaylist()">＋ Playlist</button>`+
    `<button class="btn mini" onclick="bulkTags()" title="Kanal setzen / im Titel suchen+ersetzen (für alle Ausgewählten)">✎ Tags</button>`+
    `<button class="btn mini" onclick="bulkAutotag()" title="Künstler/Album via MusicBrainz für die Auswahl nachschlagen">🏷 Auto-Tag</button>`+
    `<button class="btn mini" onclick="bulkMetadaten()" title="Titel/Kanal/Datum neu von YouTube laden">↻ Metadaten</button>`+
    `<button class="btn mini" onclick="bulkAktion('archiv')">🗄 Archivieren</button>`+
    `<button class="btn mini" onclick="bulkAktion('entarchiv')">↩ Aus Archiv</button>`+
    `<button class="btn mini" onclick="bulkAktion('loeschen')">🗑 Löschen</button>`+
    `<button class="btn mini" onclick="libAuswahl.clear();libMalen()">✖ Aufheben</button>`;
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
function aktBtnsKachel(x){
  let b='';
  if(x.vorhanden){
    b+=`<button class="ib play" onclick="event.stopPropagation();playerPlay(['${x.id}'])" title="Abspielen">▶</button>`;
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
  setTimeout(()=>{const zu=(e2)=>{
    if(!(e2.target.closest&&e2.target.closest('.itemmenu'))){
      document.querySelectorAll('.itemmenu').forEach(x=>x.remove());
      document.removeEventListener('pointerdown',zu,true);}};
    document.addEventListener('pointerdown',zu,true);},0);
}
function aktionsMenu(ev,eintraege){                    // generisches Klick-Menü an einem Knopf
  ev.stopPropagation();
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
  if(zu){const s=(e2)=>{if(!m.contains(e2.target)&&e2.target.id!=='libansichtbtn'&&!e2.target.closest('#libcolmenu')){
      ansichtZu(); document.removeEventListener('pointerdown',s,true);}};
    setTimeout(()=>document.addEventListener('pointerdown',s,true),0);}
}
function ansichtZu(){const m=document.getElementById('libansicht'); if(m)m.style.display='none';}
function plWerkzeuge(ev){aktionsMenu(ev,[
  ['📻 Neues entdecken', entdeckerOeffnen],
  ['✎ Umbenennen', plRename],
  ['🗑 Löschen', plDelete],
  ['⇄ Sync einrichten…', plSyncConfig],
  ['⇄ Jetzt synchronisieren', ()=>plSyncNow()],
  ['⤓ Als .m3u exportieren', plExport],
  ['⤒ .m3u importieren…', ()=>document.getElementById('m3ufile').click()]]);}

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
  document.body.appendChild(fly);
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
      const p=plState.find(x=>x.id===id), t=libFind(key), info=document.getElementById('plinfo');
      if(p&&info)info.textContent='„'+((t&&t.titel)||'').slice(0,22)+'" → '+p.name+' ✓'; }
    m.remove();
  });
}
function plAddMenu(ev,key){
  ev.stopPropagation();
  document.querySelectorAll('.itemmenu').forEach(x=>x.remove());
  const m=document.createElement('div'); m.className='itemmenu'; document.body.appendChild(m);
  plAddListe(m,key);
  popoverBei(m,(ev.currentTarget||ev.target).getBoundingClientRect());
  menuSchliesser(m);
}

// Kontext-/⋯-Menü am Titel (Explorer-Stil; Einträge mit 'bleib' tauschen nur den Inhalt).
function libItemMenu(ev,id){
  ev.stopPropagation();
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
  eintraege.push([x.archiviert?'↩ Aus dem Archiv holen':'🗄 Ins Archiv legen', ()=>biblio(id, x.archiviert?'entarchiv':'archiv')]);
  eintraege.push([x.blacklist?'✓ Für Meistgespielt zulassen':'🚫 Von Meistgespielt ausschließen', ()=>biblio(id, x.blacklist?'unblacklist':'blacklist')]);
  if(libPlaylistView)eintraege.push(['✖ Aus dieser Playlist entfernen', ()=>plRemove(id)]);
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
  const x=libFind(id); const t=x?(x.titel||id):id;
  const g=document.createElement('div'); g.className='ziehghost';
  g.textContent='🎵 '+t;
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
function kmListe(m,titel,optionen){kmFuellen(m,titel,optionen,()=>m.remove());}

/* Rechtsklick im PLAYER: Menü für den laufenden Titel (pausiert nichts, startet nichts neu) */
function playerKontext(ev){
  ev.preventDefault(); ev.stopPropagation();
  const k=aktKey(); if(!k)return false;
  const x=libFind(k)||{};
  const el=document.getElementById('pl-el');
  const pos={clientX:ev.clientX, clientY:ev.clientY};   // fürs EQ-Popover an der Mausposition
  const eintraege=[];
  eintraege.push([(el&&!el.paused)?'⏸ Pause':'▶ Weiter', ()=>{if(el){if(el.paused)el.play(); else el.pause();}}]);
  eintraege.push(['⏮ Vorheriger Titel', playerPrev]);
  eintraege.push(['⏭ Nächster Titel', playerNext]);
  // Untermenüs klappen wie in Windows RECHTS aus (Hover oder Klick), Haken = aktiv
  eintraege.push(['＋ Zu Playlist', ()=>plOptionen(k), 'sub']);
  eintraege.push(['🎶 Warteschlange', queueWerkzeugListe, 'sub']);
  eintraege.push(['📊 Visualizer', ()=>VIZMODES.map(v=>[v[2], v[0]===vizMode, ()=>{vizMode=v[0];
      try{localStorage.setItem('ytdl_viz',vizMode);}catch(e){} vizModeRender();}]), 'sub']);
  eintraege.push(['⚡ Geschwindigkeit ('+playSpeed+'×)', ()=>
    [0.5,0.75,1,1.25,1.5,2].map(s=>[s+'×', s===playSpeed, ()=>{playSpeed=s; speedAnwenden();}]), 'sub']);
  eintraege.push(['💬 Untertitel', ()=>{
    const opt=SUBMODES.map(sm=>[sm[2], sm[0]===subMode, ()=>subModusSetzen(sm[0])]);
    if(subSprachen.length>1)opt.push(['🌐 Sprache: '+(subLang||'?')+' → nächste', false, subSpracheWechsel]);
    if(subCues)opt.push(['あ→a Romaji: '+(subRomaji?'AN':'aus'), subRomaji, subRomajiToggle]);
    return opt;}, 'sub']);
  eintraege.push(['🎚 Equalizer…', ()=>eqPopover({currentTarget:{getBoundingClientRect:
    ()=>({left:pos.clientX,right:pos.clientX,top:pos.clientY,bottom:pos.clientY})}})]);
  if(x.vorhanden)eintraege.push(['✂ Ausschnitt schneiden…', ()=>clipDialog(k)]);
  if(x.vorhanden)eintraege.push(['📁 Im Ordner zeigen', ()=>biblio(k,'ordner')]);
  if(x.url)eintraege.push(['↗ Auf YouTube öffnen', ()=>window.open(x.url,'_blank','noreferrer')]);
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
  const thumb=x.thumb?`<img class="thumb" src="${esc(x.thumb)}" loading="lazy" draggable="false" onerror="this.style.display='none';this.parentNode.classList.add('platzhalter')">`:'';
  const sel=libAuswahl.has(x.id)?' sel':'';
  // Ausführliche Details nur noch als Tooltip auf der Info-Zeile (Kachel bleibt ruhig).
  const det=[COLDEF.kategorie.t(x),COLDEF.qualitaet.t(x),technikText(x),mb(x.groesse),
             x.dauer?zeit(x.dauer):'',x.uploader||'',ytdatum(x.upload_date)].filter(Boolean).join('  ·  ');
  return `<div class="kachel ${x.vorhanden?'':'weg'}${sel}" onclick="kachelClick(event,'${x.id}')" oncontextmenu="return kachelKontext(event,'${x.id}')"${dragAttrs(x.id)}>
    <div class="thumbwrap ${x.thumb?'':'platzhalter'}" onclick="thumbClick(event,'${x.id}')" title="Abspielen">${thumb}${dauer}${weg}</div>
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
    return `<tr class="${x.vorhanden?'':'weg'}${sel}" onclick="kachelClick(event,'${x.id}')" oncontextmenu="return kachelKontext(event,'${x.id}')"${dragAttrs(x.id)}><td><div class="ltitel">${th}<span class="ltxt" title="${esc(x.titel)}">${esc(x.titel)}</span></div></td>${tds}<td class="num">${aktBtnsListe(x)}</td></tr>`;
  }).join('');
  return `<div class="libwrap"><table class="libtab${libKompakt?' kompakt':''}"><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

/* ================= Player ================= */
let playerState={queue:[],idx:-1,quelle:''};
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
function playerPlay(keys,start,quelle){
  if(!(libdaten||[]).length){                          // Bibliothek noch nicht geladen -> erst holen,
    libLaden().then(()=>playerPlay(keys,start,quelle));// sonst filtert der Check ALLES raus und der
    return;                                            // Player bleibt schwarz (JB-Fund 14.07.)
  }
  keys=(keys||[]).filter(k=>{const x=libFind(k); return x&&x.vorhanden;});
  if(!keys.length){alert('Nichts Abspielbares — die Datei fehlt (verschoben/gelöscht).');return;}
  // Genau den LAUFENDEN Titel nochmal angeklickt -> nicht neu starten, sondern Pause/Play
  const el=document.getElementById('pl-el');
  if(el && keys.length===1 && keys[0]===aktKey()){ if(el.paused)el.play(); else el.pause(); return; }
  radioAktiv=false;                                  // manueller Start beendet den Radio-Stream
  playerState.queue=keys; playerState.idx=start||0;
  playerState.quelle=quelle||'Bibliothek';           // Name fürs Playlist-Fenster (JB 21.07.)
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
function subRomajiToggle(){
  subRomaji=!subRomaji;
  try{localStorage.setItem('ytdl_subromaji',subRomaji?'1':'0');}catch(e){}
  const k=aktKey(); if(k)subLaden(k);
}
let subLaedt=false;                                    // läuft gerade ein Untertitel-Download?
function subAnzeigen(){
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
  try{localStorage.setItem('ytdl_submode',subMode);}catch(e){}
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
function subTick(el){
  if(!subCues||subMode==='aus')return;
  const t=el.currentTime;
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
    const c=subCues[i], dauer=(c.ende-c.start)||1;
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
    `<button class="mp-btn mp-tog bo2" data-tr="shuffle" onclick="shuffleToggle()">${ico('shuffle')}</button>`+
    `<button class="mp-btn bo1" onclick="playerPrev()" title="Vorheriger">${ico('prev')}</button>`+
    `<button class="mp-btn" data-tr="pp" onclick="plTogglePlay()">${ico('play')}</button>`+
    `<button class="mp-btn bo1" onclick="playerNext()" title="Nächster">${ico('next')}</button>`+
    `<button class="mp-btn mp-tog bo2" data-tr="repeat" onclick="repeatCycle()">${ico('repeat')}</button>`+
    `<button class="mp-btn mp-tog mp-art bo2" data-tr="art" onclick="playArtCycle()"></button>`+
    `<span class="pl-bspacer"></span>`+
    `<button class="pl-bsp bo3" id="plb-sub" onclick="subCycle()" title="Untertitel: aus → Zeile → Karaoke → Transkript">💬</button>`+
    `<button class="pl-bsp bo3" onclick="clipDialog(aktKey())" title="✂ Ausschnitt schneiden (wie ein Twitch-Clip)">✂</button>`+
    `<button class="pl-bsp bo3" id="plb-speed" onclick="speedMenu(event)" title="Geschwindigkeit wählen">${playSpeed}×</button>`+
    `<span class="pl-bvolwrap bo2">🔊<input type="range" class="pl-bvol" min="0" max="100" value="${plVol}" oninput="plbVol(this.value)" title="Lautstärke"></span>`+
    `<button class="pl-bsp pl-byt bo3" onclick="playerYoutube()" title="Dieses Video auf YouTube öffnen — springt zur aktuellen Stelle">${ico('yt')}<span class="bo-yttxt"> YouTube</span></button>`+
    `<button class="pl-bsp bo3" onclick="playerLinkKopieren()" title="YouTube-Link kopieren (zum Teilen, OHNE Zeitstempel)">🔗</button>`+
    (istVideo?`<button class="pl-bsp bo2" onclick="plbPip()" title="Bild-in-Bild: Video schwebt über allen Fenstern (Taste I)">⧉</button>`:'')+
    (istVideo?`<button class="pl-bsp" onclick="plbFullscreen()" title="Vollbild (Taste F)">⛶</button>`:'')+
   `</div></div>`;
}
function plTogglePlay(){const el=document.getElementById('pl-el'); if(el){if(el.paused)el.play(); else el.pause();}}
function plbSeekDrag(v){const el=document.getElementById('pl-el'), t=document.getElementById('plb-t0');
  if(el&&el.duration&&t)t.textContent=zeit(v/1000*el.duration);}
function plbSeekEnd(v){const el=document.getElementById('pl-el');
  if(el&&el.duration)el.currentTime=v/1000*el.duration; plbSeekAktiv=false;}
function plbVol(v){plVol=Math.max(0,Math.min(100,+v||0));
  try{localStorage.setItem('ytdl_vol',plVol);}catch(e){}
  const el=document.getElementById('pl-el'); if(el)el.volume=plVol/100;
  // Mini-Player- und Video-Leisten-Regler zeigen immer denselben Stand
  document.querySelectorAll('.pl-bvol').forEach(s=>{if(+s.value!==plVol)s.value=plVol;});}
function plbFullscreen(){const m=document.getElementById('pl-media'); if(!m)return;
  if(document.fullscreenElement)document.exitFullscreen();
  else if(m.requestFullscreen)m.requestFullscreen();}
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
  const nah=el&&eintrag&&Math.abs(el.currentTime-eintrag.t)<3;   // Playhead klebt drauf -> ausblenden
  if(!eintrag||!el||!isFinite(el.duration)||!el.duration||nah){if(m)m.remove();return;}
  if(!m){
    m=document.createElement('div'); m.id='plb-merker'; m.className='plb-merker';
    m.addEventListener('click',e=>{e.stopPropagation();
      const el2=document.getElementById('pl-el'), k2=aktKey();
      // 3 s Anlauf vor der Marke (Build 105, JB: „dann ist man mehr im Moment")
      if(el2&&k2&&_posMerk[k2]){el2.currentTime=Math.max(0,_posMerk[k2].t-3); toast('↦ zurück zu '+zeit(_posMerk[k2].t)+' (mit Anlauf)');}});
    wrap.appendChild(m);
  }
  const sr=seek.getBoundingClientRect(), wr=wrap.getBoundingClientRect();
  m.style.left=(sr.left-wr.left+sr.width*(eintrag.t/el.duration))+'px';
  m.title='Zuletzt warst du hier: '+zeit(eintrag.t)+' — Klick springt hin';
}
function plbTick(){                                    // Position/Zeit der Leiste nachführen
  const el=document.getElementById('pl-el'), s=document.getElementById('plb-seek'),
        t0=document.getElementById('plb-t0'), t1=document.getElementById('plb-t1');
  if(!s||!t0||!t1)return;
  if(Date.now()-_posMerkTs>5000){_posMerkTs=Date.now(); posMerken();}   // Merker-Takt (Build 102)
  posMerkerMalen();
  if(!el||!el.duration){s.value=0;t0.textContent='0:00';t1.textContent='0:00';return;}
  if(!plbSeekAktiv){s.value=Math.round(el.currentTime/el.duration*1000);t0.textContent=zeit(el.currentTime);}
  t1.textContent=zeit(el.duration);
}
setInterval(plbTick,500);
function speedMenu(ev){                                // Geschwindigkeit als Liste (Haken = aktiv)
  ev.stopPropagation();
  kmListe(kontextMenuBauen(ev,[]),'⚡ Geschwindigkeit',
    [0.5,0.75,1,1.25,1.5,2].map(s=>[s+'×', s===playSpeed, ()=>{playSpeed=s; speedAnwenden();}]));
}
function plBarIdleInit(media,el){                      // Leiste ruht die Maus -> ausblenden (nur beim Abspielen)
  clearTimeout(plbIdleTimer);
  media.classList.remove('baridle');
  const wecken=()=>{media.classList.remove('baridle'); clearTimeout(plbIdleTimer);
    plbIdleTimer=setTimeout(()=>{if(!el.paused)media.classList.add('baridle');},2600);};
  media.onpointermove=wecken;
  media.onpointerleave=()=>{if(!el.paused)media.classList.add('baridle');};
  el.addEventListener('pause',()=>media.classList.remove('baridle'));
  wecken();
}

function renderPlayerMedia(){
  const media=document.getElementById('pl-media'); if(!media)return;
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
  if(istAudio){
    const t=x.thumb?`<img class="pl-cover" src="${esc(x.thumb)}" style="cursor:pointer" onerror="this.style.display='none'">`:'';
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
    el.addEventListener('play',cmdNowRender); el.addEventListener('pause',cmdNowRender);
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
  }
  if(el && istAudio){ vizVerbinde(el); vizFarbeAktualisieren(); vizModeRender(); vizStart(); }
  else{ media.classList.remove('viz-an'); }             // Video: kein Visualizer-Overlay
  document.getElementById('pl-titel').textContent=x.titel;
  document.getElementById('pl-pos').textContent=(playerState.idx+1)+' / '+playerState.queue.length;
  renderPlayerQueue();
  playerLayoutSet();
  cmdNowRender();
  speedAnwenden();                                     // Geschwindigkeit auf neues Element anwenden
  renderKapitel(x);                                    // YouTube-Kapitel als Sprungmarken
  subLaden(k);                                         // Untertitel für den neuen Titel holen
  canvasAnwenden();                                    // animierter Cover-Hintergrund (falls an)
}
function plQueueKlick(i){
  if(i===playerState.idx){                             // schon aktiv -> Pause/Play statt Neustart
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
function plqMark(){document.querySelectorAll('.pl-queue .pl-item').forEach(el=>el.classList.toggle('sel',+el.dataset.i===plqSel));}
function plqSelect(i){plqSel=i; plqMark(); plqFocus(i);}
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
/* Eigenschaften-Popup (JB 22.07., foobar „Properties"): alle Metadaten eines
   Titels auf einen Blick — Codec/Bitrate/Auflösung/Größe/Pfad-Herkunft/Tags. */
function eigKopiere(key){const x=libFind(key); try{navigator.clipboard&&navigator.clipboard.writeText((x&&x.titel)||key);}catch(e){} toast('Titel kopiert.');}
function eigenschaften(key){
  const x=libFind(key); if(!x){toast('Keine Infos zu diesem Titel.');return;}
  const vid=(String(key).split('|')[0])||key;
  const zeilen=[
    ['Titel', x.titel||key],
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
  const cover=x.thumb?`<img src="${esc(x.thumb)}" style="max-width:190px;width:40%;border-radius:8px;float:right;margin:0 0 8px 12px" onerror="this.style.display='none'">`:'';
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
function plqDragStart(e,i){plqVon=i; e.dataTransfer.effectAllowed='move';}
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
  if(t.includes('ytdl/key'))e.preventDefault();
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
  const key=e.dataTransfer.getData('ytdl/key'); if(!key)return;
  const x=libFind(key); if(!x||!x.vorhanden)return;
  if(playerState.idx<0||!playerState.queue.length){playerPlay([key]);}
  else{ if(!playerState.queue.includes(key))playerState.queue.push(key); renderPlayerQueue(); cmdNowRender(); }
  const info=document.getElementById('plinfo');
  if(info)info.textContent='🎶 „'+((x.titel||'').slice(0,24))+'" eingereiht ('+playerState.queue.length+' Titel)';
}
function plMediaDrop(e){
  e.preventDefault(); e.stopPropagation();
  const key=e.dataTransfer.getData('ytdl/key'); if(!key)return;
  const x=libFind(key); if(!x||!x.vorhanden)return;
  if(playerState.idx<0||!playerState.queue.length){playerPlay([key]);return;}
  if(!playerState.queue.includes(key))playerState.queue.push(key);
  renderPlayerQueue(); cmdNowRender();
  const info=document.getElementById('plinfo');
  if(info)info.textContent='🎶 „'+((x.titel||'').slice(0,24))+'" eingereiht ('+playerState.queue.length+' Titel)';
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
function renderPlayerQueue(){
  // rendert in BEIDE Ziele: seitliche Liste im Player + eigenes Playlist-Fenster
  const html=playerState.queue.map((k,i)=>{const x=libFind(k)||{titel:k};
    const aus=!artPasst(x||{});
    // Abo-Folgen: die CD-Nummer (#12) vor den Titel — so ist die Reihenfolge sofort klar (JB 21.07.)
    const nr=x.abo_nr?`<span class="pl-nr" title="Folge ${x.abo_nr}">#${x.abo_nr}</span> `:'';
    return `<div class="pl-item ${i===playerState.idx?'akt':''}${i===plqSel?' sel':''}${aus?' artaus':''}" draggable="true" tabindex="0" data-i="${i}" `+
      `ondragstart="plqDragStart(event,${i})" ondragover="plqDragOver(event)" ondrop="plqDrop(event,${i})" `+
      `onclick="plqSelect(${i})" ondblclick="plQueueKlick(${i})" oncontextmenu="return plItemKontext(event,${i})" title="Klick = auswählen · Doppelklick/Enter = abspielen · Rechtsklick = Menü · Entf = aus Playlist löschen · ↑/↓ = Auswahl · Ziehen = umsortieren">${i+1}. ${nr}${esc(x.titel||k)}</div>`;}).join('')
    ||'<div class="pl-leer">Leer — Titel aus der Bibliothek hierher ziehen.</div>';
  const q=document.getElementById('pl-queue'); if(q)q.innerHTML=html;
  const qw=document.getElementById('pl-queue-win'); if(qw)qw.innerHTML=html;
  const za=document.getElementById('plq-anzahl');
  if(za)za.textContent=playerState.queue.length?(playerState.queue.length+' Titel'):'';
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
/* Playlist-Optionen fürs Ausklapp-Untermenü (kmFuellen zeigt ab 9 automatisch die Suche) */
function plOptionen(key){
  const rein=async(id)=>{await plApi({art:'add',id,key});
    const p=plState.find(x=>x.id===id), t=libFind(key), info=document.getElementById('plinfo');
    if(p&&info)info.textContent='„'+((t&&t.titel)||'').slice(0,22)+'" → '+p.name+' ✓';};
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
  const p=plState.find(x=>x.id===id), info=document.getElementById('plinfo'), t=libFind(key);
  if(p&&info)info.textContent='„'+((t&&t.titel)||'').slice(0,22)+'" → '+p.name+' ✓';
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
  playerPlay(ids,start,p.name);}
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
    document.getElementById('plinfo').textContent='Import ✓ — '+(d.gefunden||0)+' Titel gefunden';
  }catch(e){document.getElementById('plinfo').textContent='Import fehlgeschlagen';}
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
  document.body.appendChild(fly);
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
  document.body.appendChild(fly);
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
  const info=document.getElementById('plinfo'); info.textContent='synchronisiere …';
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
document.addEventListener('click',e=>{ if(!e.target.closest('.colmenuwrap')){
  const m=document.getElementById('libcolmenu'); if(m)m.style.display='none';}});
/* Tastenkürzel (JB 21.07., YouTube-/Player-Standard). Greifen NUR, wenn nicht in
   einem Eingabefeld getippt wird. ? zeigt die Legende. */
function tastenLegende(){
  toast('⎵/K Play·Pause · J/L −/+10s · ←/→ −/+5s · ↑/↓ Lautstärke · N/P Titel · 0–9 Sprung · Home/End Anfang/Ende · M stumm · R Loop · Shift+,/. Tempo · F Vollbild · I Bild-in-Bild · S Untertitel · Playlist: Klick wählt · Doppelklick/Enter spielt · Entf löscht · ↑/↓ Auswahl');
}
function _vol(d){plbVol(Math.max(0,Math.min(100,(plVol||0)+d)));}
function _rate(d){const el=document.getElementById('pl-el'); if(!el)return;
  el.playbackRate=Math.max(0.25,Math.min(4,Math.round((el.playbackRate+d)*100)/100));
  toast('⏩ Tempo '+el.playbackRate+'×');}
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
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault(); plqRemove(plqSel!==null?plqSel:playerState.idx); return;}
  }
  const el=document.getElementById('pl-el');
  const springen=s=>{if(el&&el.duration){el.currentTime=Math.max(0,Math.min(el.duration,el.currentTime+s));}};
  const playPause=()=>{if(el){if(el.paused)el.play(); else el.pause();}};
  if(e.ctrlKey&&e.key==='ArrowRight'){e.preventDefault();playerNext();return;}
  if(e.ctrlKey&&e.key==='ArrowLeft'){e.preventDefault();playerPrev();return;}
  if(e.ctrlKey||e.metaKey||e.altKey)return;            // keine sonstigen Strg/Cmd/Alt-Kombis kapern
  if(/^(Digit|Numpad)[0-9]$/.test(e.code)&&el&&el.duration){   // 0–9 -> zu 0–90 % springen (YouTube-Standard)
    e.preventDefault(); el.currentTime=el.duration*(+e.code.slice(-1)/10); return;}
  switch(e.code){
    case 'Space': case 'KeyK': if(el){e.preventDefault(); playPause();} break;
    case 'KeyJ': e.preventDefault(); springen(-10); break;
    case 'KeyL': e.preventDefault(); springen(10); break;
    case 'ArrowRight': e.preventDefault(); springen(5); break;
    case 'ArrowLeft': e.preventDefault(); springen(-5); break;
    case 'ArrowUp': e.preventDefault(); _vol(5); break;
    case 'ArrowDown': e.preventDefault(); _vol(-5); break;
    case 'KeyN': e.preventDefault(); playerNext(); break;
    case 'KeyP': e.preventDefault(); playerPrev(); break;
    case 'KeyM': if(el){e.preventDefault(); el.muted=!el.muted; toast(el.muted?'🔇 stumm':'🔊 Ton an');} break;
    case 'KeyF': e.preventDefault(); plbFullscreen(); break;
    case 'KeyI': e.preventDefault(); plbPip(); break;
    case 'KeyS': e.preventDefault(); if(typeof subCycle==='function')subCycle(); break;
    case 'Home': if(el){e.preventDefault(); el.currentTime=0;} break;
    case 'End': if(el&&el.duration){e.preventDefault(); el.currentTime=el.duration;} break;
    case 'KeyR': if(el){e.preventDefault(); el.loop=!el.loop; toast(el.loop?'🔁 Wiederholen an':'▶ Wiederholen aus');} break;
    case 'Comma': if(e.shiftKey&&el){e.preventDefault(); _rate(-0.25);} break;   // Shift+, langsamer
    case 'Period': if(e.shiftKey&&el){e.preventDefault(); _rate(0.25);} break;   // Shift+. schneller
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
cmdNowRender();
laden();
libLaden();                                       // Bibliothek sofort laden (Player braucht sie)
plLaden();
aboLaden();
setInterval(laden,1000);
</script>
</body>
</html>
"""
