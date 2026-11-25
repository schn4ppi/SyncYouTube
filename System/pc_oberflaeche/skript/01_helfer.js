/* ================= Helfer & globaler Zustand ================= */
let daten = null;                                    // letzter /api/status (Sekundentakt via laden())

/* esc() muss ATTRIBUT-sicher sein, nicht nur text-sicher. textContent→innerHTML
   maskiert < > &, aber KEINE Anführungszeichen — in `title="${esc(t)}"` bricht
   ein " aus dem Attribut aus und zerlegt das Tag. Kein Grenzfall: die echte
   Bibliothek enthält »Der Fall "Air Cocaine" - Schmuggler in 10000 Meter Höhe«
   und 100 Titel mit Apostroph (»Abi '97«, »Angel's Egg«). Titel sind FREMDE
   Daten von einem Server, den der Besitzer nicht kontrolliert — ein Titel mit " und
   onerror= wäre sonst ausführbarer Code. Gefunden 13.08.2026. */
function esc(t){const d=document.createElement('div');d.textContent=t||'';
  return d.innerHTML.replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
let _toastTimer=null;
function toast(text){                                  // kurze, dezente Rückmeldung (calm — kein Alert-Stopp)
  let t=document.getElementById('toast');
  if(!t){t=document.createElement('div'); t.id='toast';}
  // Fullscreen-Falle (05.08.): der Browser rendert im Vollbild NUR das
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

/* ---- Server-Ruf und Browser-Speicher (Gesamtprüfung O3) -------------------
   api(pfad, body, opt) ist der EINE Weg für POST an den eigenen Server. Vorher
   stand dieselbe fetch-Zeile 57-mal da, und r.ok prüften vier Stellen.
     · body geht als JSON; ein fertiger Text geht unverändert, ohne body '{}'.
     · Zurück kommt die Antwort des Servers als Objekt, unverändert. Einen
       Fehler erkennt man wie bisher an `fehler`: jede Fehlerantwort des
       Servers trägt ihn (_antwort in youtube_app.py). Fehlt er bei einem
       Status außerhalb 2xx doch einmal, setzt api() den einheitlichen Text
       aus apiFehlertext() ein. Gefragt wird r.ok===false: ein echter Response
       hat ok immer, eine Test-Attrappe ohne ok gilt als Erfolg.
     · Ein Netzfehler wirft weiter, wie fetch selbst; eine Antwort, die sich
       nicht als JSON lesen lässt (abgerissene Verbindung), wirft ebenso, mit
       dem einheitlichen Text. So nehmen die Stellen, die die Antwort lesen,
       genau ihren bisherigen catch-Weg.
     · {roh:true} liefert den Response unverändert, für Stellen, die Status und
       Fehlertext selbst auswerten (M3U-Import: 413, Sync einrichten).
   fetch wird bei jedem Ruf neu nachgeschlagen, damit die Hülle für Geräte im
   WLAN (fetchHuelleSetzen) auch hier greift. Welche POSTs bewusst roh bleiben
   und warum, steht in tests/test_oberflaeche_api.py (ROH_BLEIBT).
   lsLesen/lsSchreiben/lsWeg: localStorage mit Netz, wie in handy.py. Ein
   gesperrter Speicher (privates Fenster, blockierte Website-Daten) wirft schon
   beim Zugriff (F27); dann liefert lsLesen null, Schreiben und Löschen tun
   nichts. Blöcke, die zugleich JSON.parse oder mehr schützen, bleiben try. */
function apiFehlertext(status){return 'Server antwortet mit '+status+'.';}
async function api(pfad,body,opt){
  const r=await fetch(pfad,{method:'POST',headers:{'Content-Type':'application/json'},
    body:typeof body==='string'?body:JSON.stringify(body===undefined?{}:body)});
  if(opt&&opt.roh)return r;
  let d;
  try{d=await r.json();}catch(e){throw new Error(apiFehlertext(r.status));}
  if(r.ok===false&&d&&typeof d==='object'&&!d.fehler)d.fehler=apiFehlertext(r.status);
  return d;
}
function lsLesen(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function lsSchreiben(k,v){try{localStorage.setItem(k,v);}catch(e){}}
function lsWeg(k){try{localStorage.removeItem(k);}catch(e){}}

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
  lsSchreiben('ytdl_skin',def[0]);
  themeIcon();
  const sel=document.getElementById('opt_skin'); if(sel)sel.value=def[0];
  if(window.vizFarbeAktualisieren)vizFarbeAktualisieren();   // Visualizer folgt dem Akzent
}
function setSkin(name){applySkin(name);}
function themeToggle(){                                 // 🌙/☀ = schneller Tag/Nacht-Wechsel
  applySkin(document.documentElement.classList.contains('light')?'terracotta':'hell');
}
// Vom Dashboard eingebettet (22.07.): dessen Tag/Nacht uebernehmen — nur die Hell-Klasse
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

/* ---- Bildschirm-Wächter (Build 114, Vorgabe: „Ansicht geht aus dem Bildschirm
   raus, das darf NIE passieren — weder mobil, noch Desktop, noch Browser").
   Wurzel-Lösung statt Einzelfall-Flicken: jedes schwebende Element wird
   geklemmt (Position + Höchstmaße) UND bei jeder späteren Inhalts-Änderung
   erneut geprüft — genau da riss es vorher (Listen, die nachgeladen werden,
   wuchsen über die berechnete Höhe hinaus). Zu viel Inhalt scrollt IM
   Element, statt aus dem Bild zu laufen (Anti-Scroll-Regel: die Seite
   scrollt nie, nur der Inhalt). ---- */
const SCHWEBEND='.abo-flyout,.panelmenu,.itemmenu,.colmenu,.popover,.modal-box';
/* Info-Zeile der Bibliotheksleiste (Build 139, Fund: „eingereiht (3
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

/* Hoechstmasse fuer schwebende Flaechen (Build 139, Wunsch).
   Eine Menue-Spalte wird jenseits von ~1000 px nicht besser lesbar, nur
   breiter - lange Zeilen sind muehsamer zu lesen als kurze. Die Zahlen sind
   deshalb bewusst am Lesbaren orientiert, nicht am verfuegbaren Platz. */
const MAX_FLY={b:1000,h:820};

/* Zuletzt geoeffnetes Fenster liegt oben (Build 139, Fund: der
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
  // Build 139 (der Besitzer): zusaetzlich eine absolute Obergrenze. Die Kopplung an die
  // Position allein ergibt auf einem Ultrawide im Vollbild ein 3000 px
  // breites Menue - Vorgabe: „sie sollten auch eine Standardgroesse haben, nicht
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
    '<div style="font-size:11px;color:var(--gedaempft);padding:2px 6px 6px">Optionen</div>'+
    '<div class="optrow"><span>Look</span><select id="opt_skin" onchange="setSkin(this.value)">'+
      SKINS.map(s=>'<option value="'+s[0]+'">'+s[1]+'</option>').join('')+'</select></div>'+
    '<div class="optrow" style="display:block"><div style="display:flex;justify-content:space-between">'+
      '<span>Fenster-Abstand</span><span id="gapval">'+fensterAbstand()+' px</span></div>'+
      '<input type="range" min="0" max="24" value="'+fensterAbstand()+'" style="width:100%;margin-top:4px" oninput="setGap(this.value)"></div>'+
    '<div class="optrow nur-pc"><span>Fehler ausblenden</span>'+
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
    // Build 130 (der Besitzer): 16:9 ist FEST der Standard, damit das Bild beim
    // Titelwechsel nicht springt. Die anderen Verhältnisse stehen als
    // Layout-Option daneben — „Natürlich" heisst ausdrücklich, dass es
    // wieder springen darf.
    // Build 132 (der Besitzer): Sprungweite der Pfeiltasten. 5 s ist der Standard, weil
    // YouTube es so macht — belegt in dessen Tastenkürzel-Hilfe.
    // Build 134 (Punkt 4): Einfach- oder Doppelklick zum Abspielen.
    '<div class="optrow"><span>Abspielen per</span><select id="opt_klick" onchange="klickArtSetzen(this.value)" '+
      'title="Doppelklick stört die Auswahl nicht — Einfachklick ist schneller">'+
      '<option value="doppel">Doppelklick</option><option value="einfach">Einfachklick</option></select></div>'+
    // Build 144 (Punkt 7): In der Playlist teilen sich Rahmen-Auswahl und
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
    // Untertitel-Stil (05.08., wie Amazon/Netflix): Größe fürs Sofa/TV,
    // Preset für die Optik — gilt für Untertitel-Zeilen UND Karaoke-Größe.
    // Modus inkl. TRANSKRIPT lebt hier (05.08.: im Player-Panel nur noch
    // aus/Untertitel/Karaoke — Taste S wechselt weiter durch alle vier).
    '<div class="optrow"><span>Untertitel-Modus</span><select id="opt_submode" onchange="subModusSetzen(this.value)">'+
      '<option value="aus">aus</option><option value="zeilen">Untertitel</option>'+
      '<option value="karaoke">Karaoke</option><option value="transkript">Transkript</option></select></div>'+
    '<div class="optrow"><span>Untertitel-Darstellung</span><button class="btn mini" onclick="subMenu(event)" '+
      'title="Größe, Schrift, Farben, Schatten, Hintergrund, Versatz — mit Live-Vorschau (Disney-Muster)">💬 einstellen…</button></div>'+
    '<div class="optrow"><span>Sleep-Timer</span><span><select id="opt_sleep" onchange="sleepSetzen(this.value)">'+
      '<option value="0">aus</option><option value="15">15 min</option><option value="30">30 min</option>'+
      '<option value="60">60 min</option><option value="titel">nach diesem Titel</option></select>'+
      '<span id="sleepval" style="color:var(--gedaempft);font-size:11px;margin-left:6px"></span></span></div>'+
    '<div class="optrow nur-pc"><span>Dateinamen</span><button class="btn mini" onclick="namenFenster()" title="Bausteine wählen und schieben, Probelauf ansehen, anwenden oder zurücknehmen">🏷 Namens-Baukasten</button></div>'+
    // Etappe C (Spec Punkt 5): globale Grundeinstellungen — unterste geteilte
    // Ebene; Playlist- und Titel-Regeln gehen vor (drei Ebenen, der Besitzer 23.07.).
    '<div class="optrow nur-pc"><span>Wiedergabe-Standard</span><button class="btn mini" onclick="wgGlobalDialog()" '+
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
    // gefragt wird, wäre ein Knopf ohne Aufgabe (wenige Knöpfe).
    '<div class="optrow nur-pc"><span>Alle Einstellungen</span><button class="btn mini" onclick="einstellungenOeffnen()">⚙ Öffnen</button></div>'+
    // Der Besitzer 05.08.: Fernsehmodus auch HIER — er betrifft den Player, also gehört
    // er zusätzlich in dessen Optionen (Ansicht-Menü hat ihn ebenfalls, oben).
    '<div class="optrow"><span>📺 Fernsehmodus</span><button class="btn mini" onclick="fernsehModus()">Start</button></div>'+
    '<div class="optrow nur-pc"><span>📱 Fernsteuerung</span><button class="btn mini" id="fernbtn" onclick="fernToggle()">…</button></div>'+
    // Teilprojekt 3: Geräte koppeln (QR/Code) + freigeben/trennen — nur am PC.
    '<div class="optrow nur-pc"><span>📺 Geräte (TV/Handy)</span><button class="btn mini" onclick="geraeteDialog()">Koppeln…</button></div>'+
    '<div id="ferninfo" class="nur-pc" style="font-size:11px;color:var(--gedaempft);padding:0 8px 6px"></div>';
  document.body.appendChild(m);
  const sel=m.querySelector('#opt_fehler'); if(sel)sel.value=fmin;
  const ar=m.querySelector('#opt_ar');
  if(ar)ar.value=lsLesen('ytdl_ar')||'16/9';
  const sp=m.querySelector('#opt_sprung'); if(sp)sp.value=sprungWeite();
  const kl=m.querySelector('#opt_klick'); if(kl)kl.value=klickArt();
  const pr=m.querySelector('#opt_plqrahmen'); if(pr)pr.value=plqRahmenArt();
  const sk=m.querySelector('#opt_skin'); if(sk)sk.value=aktuellerSkin();
  const slp=m.querySelector('#opt_sleep'); if(slp)slp.value=sleepTitelende?'titel':(sleepEndeZeit?sleepStufe:'0'); sleepLabel();
  const ub=m.querySelector('#opt_ueb'); if(ub)ub.value=uebergang;
  subStilInit();                                       // Untertitel-Stil-Selects mit gemerktem Stand
  fernInfoMalen();
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  setTimeout(()=>document.addEventListener('pointerdown',function zu(e2){
    if(!m.contains(e2.target)&&e2.target.id!=='optbtn'){m.remove(); document.removeEventListener('pointerdown',zu);}},true),0);
}
function setGap(v){lsSchreiben('ytdl_gap',v); const g=document.getElementById('gapval'); if(g)g.textContent=v+' px';}
async function setFehlerMin(v){
  try{await api('/api/config',{fehler_ausblenden_min:parseInt(v,10)});}catch(e){}
}

