/* ================= Command-Bar oben: Download, Live-Queue, Now-Playing, Zwischenablage ================= */
function qualMerken(v){                               // Qualitätswahl fuer naechsten Start sichern
  if(!NUR_FERN)api('/api/config',{standard_qualitaet:v});   // Gerät im WLAN: gilt, solange die Seite offen ist
  const a=document.getElementById('cmd-qual'), b=document.getElementById('qual');
  if(a)a.value=v; if(b)b.value=v;
}
/* ---- Ein Feld für alles (Build 126) ---------------------------------------
   Vorgabe: „Download / Playlist laden / Abonnieren sind drei zu ähnliche Knöpfe."
   Jetzt genügt Enter im Feld — den Typ erkennt die App am Link (link_deuten
   im Backend, EINE Wahrheit, ohne Netz). Gefragt wird nur, wo die Absicht
   wirklich offen ist: Kanal = laden oder abonnieren, watch?v=…&list= = eines
   oder alle. Die Antwort lässt sich merken und im ⚙-Menü wieder umstellen. */
async function cmdDownload(){
  const inp=document.getElementById('cmd-url'); const url=(inp.value||'').trim(); if(!url)return;
  let d=null;
  try{d=await api('/api/link_deuten',{url});}catch(e){}
  if(!d||d.typ==='unbekannt'){toast('Das sieht nicht nach einer Adresse aus — bitte einen Link einfügen.');return;}
  if(d.eindeutig) linkAusfuehren(url,d.typ,null); else linkFrage(d,url);
}
async function linkAusfuehren(url,typ,wahl){
  const q=document.getElementById('cmd-qual').value;
  if(typ==='kanal'&&wahl==='abo'){                     // abonnieren statt laden
    toast('📡 Kanal wird abonniert …');
    let r=null; try{r=await api('/api/abo',{art:'create',url,qualitaet:q});}catch(e){}
    if(!r||r.fehler){toast((r&&r.fehler)||'Abo ließ sich nicht anlegen.');return;}
    cmdFeldLeeren(); toast('📡 Abonniert: „'+(r.name||'Kanal')+'" — neue Folgen kommen von allein.');
    try{abosZeigen();}catch(e){}
    return;
  }
  // Alles, was eine ganze Sammlung ist, geht über den bewährten Weg mit
  // Anzahl + Größenschätzung + Rückfrage (ganzerKanal) — der zeigt vorher,
  // was auf den Besitzer zukommt, statt wortlos 500 Downloads zu starten.
  if(typ==='playlist'||typ==='mix'||typ==='kanal'||(typ==='video_in_playlist'&&wahl==='alle')){
    ganzerKanal(null,url); return;
  }
  await api('/api/add',{urls:url,qualitaet:q,ganze_liste:false});
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
  // Build 127 (der Besitzer): KEIN „immer so"-Haken. Vorgabe: „diese Abfrage ist meiner
  // Meinung nach immer relevant" — bei einem Kanal will man mal abonnieren
  // und mal laden, das hängt am Kanal und nicht an einer Voreinstellung.
  // Eine gemerkte Antwort wäre hier kein Komfort, sondern eine Falle.
  m.innerHTML='<div style="font-size:11.5px;color:var(--gedaempft);padding:2px 6px 7px">'+esc(d.frage)+'</div>'+
    d.optionen.map(o=>'<button class="mbtn" data-id="'+o.id+'">'+esc(o.text)+'</button>').join('');
  document.body.appendChild(m);
  const feld=document.getElementById('cmd-url');
  popoverBei(m, feld.getBoundingClientRect());
  m.querySelectorAll('.mbtn').forEach(b=>b.onclick=()=>{
    m.remove(); linkAusfuehren(url,d.typ,b.dataset.id);
  });
  menuSchliesser(m);
}
/* „Ganzen Kanal laden" (22.07.): Kanal-Link auflösen (Backend normalisiert
   /@name -> /videos, sonst kämen nur die Reiter), Anzahl zeigen, nach Rückfrage
   ALLE Videos in die Warteschlange (ganze_liste=true; schon Geladenes wird
   übersprungen). Funktioniert auch für reine Playlist-Links. */
/* Größen-Schätzung (Build 105, Vorgabe: „wenn ich 5000 Songs lade und auf einmal
   10 TB laden muss, habe ich ein Problem") — MB/min je Qualität kommen als
   MEDIAN aus den ECHTEN eigenen Downloads (Fallback-Erfahrungswerte, wenn
   zu wenig Daten). Ehrlich als „≈"-Schätzung beschriftet. */
let _mbFaktoren=null;
fetch('/api/schaetzfaktoren').then(r=>r.json()).then(d=>{_mbFaktoren=d;}).catch(()=>{});
function groesseSchaetzen(dauerSek,qual){
  if(!dauerSek||!_mbFaktoren||!_mbFaktoren[qual])return '';
  const mb=dauerSek/60*_mbFaktoren[qual];
  const txt=mb>=1024?((mb/1024).toFixed(1)+' GB'):(Math.round(mb)+' MB');
  return '\n≈ '+txt+' (Erfahrungswert deiner Bibliothek)';
}
async function ganzerKanal(btn,urlAus){
  // Build 126: nimmt die Adresse jetzt auch als Parameter entgegen — das
  // eine Feld ruft den Weg direkt auf, statt dass er selbst im Feld nachsieht.
  const inp=document.getElementById('cmd-url');
  const url=(urlAus||inp.value||'').trim();
  if(!url){toast('Erst einen Kanal- oder Playlist-Link oben einfügen.');return;}
  // Mix/Radio (Build 98, der Besitzer): ERST die Wunsch-Anzahl fragen, DANN nur so viele
  // aufloesen — Mixe sind endlos + nicht-deterministisch (mass 1877 vs 563),
  // die Voll-Aufloesung war eine 20-s-Sanduhr fuer eine falsche Zahl.
  const mix=/[?&]list=(RD|UL)/.test(url);
  let limit=null;
  if(mix){
    const w=prompt('YouTube-Mix (Radio) erkannt — der ist endlos.\n\nWie viele Titel ab dem Startvideo laden? (1–500)','50');
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
    if(!confirm('„'+d.name+'"\n\nDie ersten '+d.anzahl+' Titel des Mixes (ab dem Startvideo) in Qualität '+qtext+' laden?'+gr+'\nSchon geladene werden übersprungen.'))return;
    await api('/api/add',{urls:d.url,qualitaet:q,ganze_liste:true,limit:limit});
    cmdFeldLeeren(); laden();
    try{dlboxTab('queue');}catch(e){}
    toast('📺 „'+d.name+'": '+d.anzahl+' Titel werden geladen.');
    return;
  }
  mengenRegler(d,q);                                   // Build 127: Besitzer-Regler
}
/* ---- Mengen-Regler (Build 127) --------------------------------------------
   Vorgabe: „ich würde gerne einen Regler haben bei alle Videos jetzt laden (das
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
    '<div style="font-size:11.5px;color:var(--gedaempft);padding:0 6px 8px">'+gesamt+(d.gedeckelt?'+':'')+' Videos gefunden'+
      (d.gedeckelt?' (Obergrenze erreicht)':'')+'</div>'+
    '<div style="padding:0 6px"><input type="range" id="mr-range" min="1" max="'+gesamt+'" value="'+gesamt+'" style="width:100%"></div>'+
    '<div class="mzeile"><span id="mr-zahl" style="color:var(--akz2);font-weight:700"></span>'+
      '<span id="mr-groesse" style="font-size:11px;color:var(--gedaempft)"></span></div>'+
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
    m.querySelector('#mr-groesse').textContent=(groesseSchaetzen(anteil,q)||'').replace(/^\n/,'');
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
    await api('/api/add',{urls:d.url,qualitaet:q,ganze_liste:true,
                           menge:(menge>=gesamt?0:menge),richtung});
    cmdFeldLeeren(); laden();
    try{dlboxTab('queue');}catch(e){}
    toast('📺 „'+d.name+'": '+menge+' Videos werden geladen ('+(richtung==='alt'?'älteste':'neueste')+' zuerst). Schon geladene werden übersprungen.');
  };
  malen();
  menuSchliesser(m);
}
/* „Now Playing"-Mini in der Command-Bar: Steuerung + Titel, darunter Spulleiste
   mit Zeitanzeige (13.07.). malen() ruft das jede Sekunde — damit die
   Spulleiste beim Ziehen nicht unter der Maus weggerendert wird, baut die
   Funktion das HTML nur bei ECHTER Änderung neu (Signatur-Vergleich); die
   laufende Zeit frischt cmdSeekTick() gezielt per textContent auf. */
let cmdNowSig='', cmdSeekAktiv=false;
function cmdNowRender(){
  const el=document.getElementById('cmd-now'); if(!el)return;
  // Build 117 (Freigabe): dieselben Transport-Knöpfe standen doppelt da — hier
  // UND im Player. Ist der Player offen, führt er; die Kopfleiste behält nur
  // Titel, Zeitleiste, Lautstärke und Radio (die hat der Player nicht).
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
/* Stelle und Dauer des laufenden Titels, im Browser oder am Gerät VLC, und
   das Spulen dorthin (F11): Kopfleiste und Player-Leiste nutzen dieselben
   Helfer. Am Gerät VLC kommen die Werte aus dem 1-s-Status (vlcTick). */
function spulStand(){
  if(vlcAktiv())return {pos:vlcPosLetzte, dauer:vlcDauerLetzte||0};
  const el=document.getElementById('pl-el');
  return {pos:el?el.currentTime:0, dauer:(el&&el.duration)||0};
}
function spulenAuf(v){                                 // v: Promille der Dauer
  if(vlcAktiv()){
    if(vlcDauerLetzte){vlcPosLetzte=v/1000*vlcDauerLetzte; vlcBefehl('seek',{wert:vlcPosLetzte});}
    return;
  }
  const el=document.getElementById('pl-el');
  if(el&&el.duration)el.currentTime=v/1000*el.duration;
}
function cmdSeekDrag(v){                               // beim Ziehen läuft nur die Zeitanzeige mit
  const t0=document.getElementById('cmd-t0'), d=spulStand().dauer;
  if(d&&t0)t0.textContent=zeit(v/1000*d);
}
function cmdSeekEnd(v){                                // losgelassen -> wirklich spulen
  spulenAuf(v);
  cmdSeekAktiv=false;
}
function cmdSeekTick(){                                // Position/Zeiten nachführen (auch via setInterval)
  const s=document.getElementById('cmd-seek'), t0=document.getElementById('cmd-t0'),
        t1=document.getElementById('cmd-t1'), st=spulStand();
  if(!s||!t0||!t1)return;
  if(!st.dauer){s.value=0;s.disabled=true;t0.textContent='0:00';t1.textContent='0:00';return;}
  s.disabled=false;
  if(!cmdSeekAktiv){s.value=Math.round(st.pos/st.dauer*1000);t0.textContent=zeit(st.pos);}
  t1.textContent=zeit(st.dauer);
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
   den ersten Klick/Rechtsklick schluckt (13.07.). Wo die Erlaubnis fehlt,
   greift stattdessen die Einfügen-Erkennung: Strg+V irgendwo in der App. */
let cmdClipLast='';
async function cmdClipCheck(){
  try{
    if(!navigator.permissions)return;
    const p=await navigator.permissions.query({name:'clipboard-read'});
    if(p.state!=='granted')return;                     // würde nachfragen -> lieber gar nicht
    const t=((await navigator.clipboard.readText())||'').trim();
    if(t&&t!==cmdClipLast&&/(?:youtube\.com|youtu\.be)\//i.test(t)){cmdClipLast=t; cmdClipZeigen(t);}
  }catch(e){}                                          // Browser kennt die Abfrage nicht (Firefox) -> still lassen
}
document.addEventListener('paste',(e)=>{               // Strg+V in der App = Link anbieten
  try{
    const t=((e.clipboardData||{}).getData('text')||'').trim();
    if(t&&/(?:youtube\.com|youtu\.be)\//i.test(t)&&(e.target||{}).id!=='cmd-url'){cmdClipLast=t; cmdClipZeigen(t);}
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
  const url=(e.dataTransfer.getData('text/uri-list')||e.dataTransfer.getData('text/plain')||'').trim().split(/\s+/)[0];
  if(!/^https?:\/\//i.test(url))return;              // interne Drags (Umsortieren) haben keinen http-Text
  e.preventDefault();
  const q=(document.getElementById('cmd-qual')||{}).value||'beste';
  try{await api('/api/add',{urls:url,qualitaet:q});}catch(err){}
  plInfo('⬇ Per Drag&Drop hinzugefügt: '+url.slice(0,48));
  laden();
});

