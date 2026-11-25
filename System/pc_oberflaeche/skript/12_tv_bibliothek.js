/* ================= TV-Bibliothek ================= */
/* ---- TV-Bibliothek (Sync Teilprojekt 2 v1) --------------------------------
   Vorgabe: „erledige alle aufgaben von der roadmap" — der Fernsehmodus öffnet
   jetzt die eigene 10-Fuß-Ansicht: Menü-Schnitt A (Home · Filme · Serien ·
   Neu & Beliebt · ❤ · YouTube · Musik · Suche), Poster-Reihen, reine
   Pfeil-/Fernbedienungs-Navigation (Enter wählt, Esc/Zurück schließt).
   Enter auf einen Film startet ihn im VLC (Film-Fundament); Enter auf einen
   Titel spielt ihn im Player. Feinschliff-Runden folgen mit Besitzer-Blick. */
const TV_TABS=[['suche','🔍'],['home','Home'],['filme','Filme'],['serien','Serien'],
  ['neu','Neu & Beliebt'],['live','📡 Live'],['herz','❤ Favoriten'],['yt','▶ YouTube'],['musik','🎵 Musik']];
let tvTab='home', tvFokus={r:0,i:0}, tvReihenListe=[], tvFilmReihen=null, tvFilmZustand=null;
/* Fake-Fernbedienung (07.08.): ein kleines Fenster unter /fernbedienung
   schickt Tastennamen über einen BroadcastChannel. Hier landen sie — und
   werden als ECHTE Tastatur-Ereignisse in die bestehende tvKey-Behandlung
   geworfen. Kein zweiter Bedienpfad, der auseinanderlaufen könnte. */
let _fbKanal=null;
function fbEmpfangVerkabeln(){
  if(_fbKanal||!('BroadcastChannel' in window))return;
  _fbKanal=new BroadcastChannel('syncyoutube-fb');
  _fbKanal.onmessage=ev=>{
    const n=ev.data||{};
    const tv=document.getElementById('tv');
    const tvAn=!!(tv&&tv.style.display!=='none');
    if(n.art==='hallo'){                                // Zustand zurückmelden
      _fbKanal.postMessage({art:'hier', tv:tvAn,
        spielt:(typeof vlcSpielt!=='undefined'&&vlcSpielt)||
               (typeof tvpOffen!=='undefined'&&tvpOffen&&!!document.querySelector(
                 '#tvp-pp svg path[d^="M6 5"]'))});
      return;}
    if(n.art==='tv'){                                   // EIN Knopf für an UND aus
      if(tvAn)tvZu(); else {fbZeigerWeg(); fernsehModus();}
      return;}
    if(n.art==='maus'){fbMausBewegen(n.dx||0,n.dy||0); return;}
    if(n.art==='klick'){fbMausKlick(n.knopf||'links'); return;}
    if(n.art!=='taste'||!n.taste)return;
    const ziel=document.activeElement&&document.activeElement.tagName==='INPUT'
      ?document.activeElement:document.body;
    ziel.dispatchEvent(new KeyboardEvent('keydown',
      {key:n.taste, bubbles:true, cancelable:true}));
  };
}
window.addEventListener('message',ev=>{                 // Rückweg ohne BroadcastChannel
  if(ev.origin!==location.origin||!ev.data)return;
  const n=ev.data;
  if(n.art==='tv')fernsehModus();
  else if(n.art==='taste'&&n.taste)
    document.body.dispatchEvent(new KeyboardEvent('keydown',
      {key:n.taste, bubbles:true, cancelable:true}));
});
function fernbedienungOeffnen(){
  window.open('/fernbedienung','syncyoutube-fb',
    'width=300,height=760,menubar=no,toolbar=no,location=no,status=no');
}
/* Maus-Modus (07.08.: „kann ich dann die maus simulieren wie die remote
   maus app?"): Ein echter Systemzeiger lässt sich aus einer Webseite nicht
   bewegen — das verbietet jeder Browser. Also führt die Seite einen EIGENEN
   Zeiger: ein Fadenkreuz wandert über die Oberfläche, hebt hervor, worüber
   es steht, und ein Klick löst dort einen echten Klick aus. Für Besitzer-Zweck
   (vom Sofa aus bedienen) ist das gleichwertig — und es funktioniert auch
   auf dem Handy. */
let _fbZeiger=null, _fbX=0, _fbY=0;
function fbZeigerHolen(){
  if(_fbZeiger&&_fbZeiger.isConnected)return _fbZeiger;
  _fbZeiger=document.createElement('div');
  _fbZeiger.id='fb-zeiger';
  _fbZeiger.style.cssText='position:fixed;z-index:9999;width:22px;height:22px;'+
    'border:2px solid #fff;border-radius:50%;background:rgba(255,255,255,.25);'+
    'box-shadow:0 0 10px rgba(0,0,0,.8);pointer-events:none;transition:none';
  document.body.appendChild(_fbZeiger);
  _fbX=innerWidth/2; _fbY=innerHeight/2;
  return _fbZeiger;
}
function fbZeigerWeg(){
  // Der Besitzer 07.08.: „im Fernsehmodus sollte der Punkt verschwinden mit dem
  // Mauspad" — dort steuert das D-Pad, ein zweiter Zeiger verwirrt nur.
  if(_fbZeiger){_fbZeiger.remove(); _fbZeiger=null;}
  _fbZeigerZiel=null;
}
function fbMausBewegen(dx,dy){
  const tv=document.getElementById('tv');
  if(tv&&tv.style.display!=='none')return;              // im TV kein Zeiger
  const z=fbZeigerHolen();
  _fbX=Math.max(0,Math.min(innerWidth-1,_fbX+dx));
  _fbY=Math.max(0,Math.min(innerHeight-1,_fbY+dy));
  z.style.left=(_fbX-11)+'px'; z.style.top=(_fbY-11)+'px';
  const el=document.elementFromPoint(_fbX,_fbY);
  if(el&&el!==_fbZeigerZiel){
    if(_fbZeigerZiel)_fbZeigerZiel.dispatchEvent(new MouseEvent('mouseout',{bubbles:true,relatedTarget:el}));
    el.dispatchEvent(new MouseEvent('mouseover',{bubbles:true}));
    _fbZeigerZiel=el;
  }
}
let _fbZeigerZiel=null;
function fbMausKlick(knopf){
  fbZeigerHolen();
  const el=document.elementFromPoint(_fbX,_fbY);
  if(!el)return;
  if(knopf==='rechts'){
    el.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,
      clientX:_fbX, clientY:_fbY}));
    return;
  }
  ['mousedown','mouseup','click'].forEach(art=>
    el.dispatchEvent(new MouseEvent(art,{bubbles:true,cancelable:true,
      clientX:_fbX, clientY:_fbY, view:window})));
}
function fernsehModus(){
  fbEmpfangVerkabeln();                                 // Fernbedienung darf mitreden
  fbZeigerWeg();                                        // Maus-Punkt geht mit dem Mauspad
  if(typeof ansichtZu==='function')ansichtZu();
  const o=document.getElementById('optionen'); if(o)o.remove();
  tvOeffnen();
}
/* Hover-Karte („siehst du den unterschied?", Netflix-Referenz): nach
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
    // Der Besitzer 06.08. („Man sieht noch … im hintergrund. Das soll das alte fenster
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
        `data-fb1="${esc('/api/filme/bild?id='+fi+'&art=Backdrop')}" data-fb2="${esc('/api/filme/bild?id='+fi)}" `+
        `onerror="if(!this.dataset.s){this.dataset.s=1;this.src=this.dataset.fb1}else{this.onerror=null;this.src=this.dataset.fb2}">`+
      `<video class="tv-snip" muted loop playsinline data-snip="${fi}" `+
        `onerror="this.remove()"></video>`+
      `<div class="hk-titel">${esc(e.name||'')}</div></div>`+
      `<div class="hk-zeile">`+
      `<button class="hk-ib hk-play" data-arg="${esc(fid)}" data-pos="${+e.pos||0}" onclick="event.stopPropagation();snippetAus();filmePlay(this.dataset.arg,+this.dataset.pos)" title="Abspielen">${ico('play')}</button>`+
      `<button class="hk-ib" data-arg="${esc(fid)}" onclick="event.stopPropagation();tvMerk(this.dataset.arg)" title="Zur Liste">${ico('plus')}</button>`+
      `<button class="hk-ib hk-rechts" data-arg="${esc(fid)}" onclick="event.stopPropagation();snippetAus();tvInfo(this.dataset.arg)" title="Mehr Infos">${ico('chevron')}</button></div>`+
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
      // oben (Fund 06.08. früh). offsetHeight ignoriert transform.
      const h=kt.offsetHeight||240;
      kt.style.left=Math.max(8, Math.min(innerWidth-w-8, kr.left+kr.width/2-w/2))+'px';
      kt.style.top=Math.max(8, Math.min(innerHeight-h-8, kr.top+kr.height/2-h/2))+'px';
    };
    kt._sync=setInterval(setzen,120);                  // VOR setzen() — sonst Waise
    setzen();
    // Der CLIP startet erst nach ein paar Sekunden (07.08.: „man sollte
    // ein paar Sekunden auf einem video sein bevor der clip abspielt") —
    // genau wie Netflix: erst das Standbild, dann bewegtes Bild. Wer nur
    // durch die Reihe fährt, bekommt kein Video-Gewitter.
    kt._clip=setTimeout(()=>{
      const v=kt.querySelector('video.tv-snip');
      if(!v||!kt.isConnected)return;
      v.src='/api/filme/snippet?id='+v.dataset.snip;
      v.play().catch(()=>{});
    },2200);
  },450);                                              // Karte: Netflix-Tempo ~450 ms
}
function snippetAus(){
  clearTimeout(snipTimer);
  document.querySelectorAll('.tv-hoverkarte').forEach(x=>{
    if(x._sync)clearInterval(x._sync);
    if(x._clip)clearTimeout(x._clip);                  // Clip-Start nie verwaisen
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
  try{tvFilmReihen=filmReihenAnwenden(await (await fetch('/api/filme/reihen?profil='+encodeURIComponent(tvProfil()))).json());}
  catch(e){tvFilmReihen={weiterschauen:[],top:[],neu:[],genres:{}};}
  /* Auch vom Sofa aus muss ein Ausfall sichtbar sein: hier sah der Besitzer sieben Tage
     lang eine völlig normale Netflix-Oberfläche, während der Spiegel alterte. */
  try{tvFilmZustand=await (await fetch('/api/filme/zustand?profil='+encodeURIComponent(tvProfil()))).json();}
  catch(e){tvFilmZustand=null;}
  try{const r=await fetch('/api/filme_konto?profil='+encodeURIComponent(tvProfil()));
      tvFilmKonto=r.ok?await r.json():null;}
  catch(e){tvFilmKonto=null;}
  tvMalen();
}
function tvKopfMalen(){
  const k=document.getElementById('tv-kopf');
  const p=(tvProfile||[]).find(x=>x.id===tvProfil())||{emoji:'👤',name:''};
  k.innerHTML=TV_TABS.map(([id,name])=>
    `<button class="tvtab${tvTab===id?' akt':''}" data-tv="${id}" onclick="tvTabWahl(this.dataset.tv)">${name}</button>`).join('')+
    `<button class="tvzu" onclick="tvProfilWahl()" title="Profil wechseln — ${esc(p.name)}" style="margin-left:auto">${esc(p.emoji)}</button>`+
    `<button class="tvzu" style="margin-left:0" onclick="fernbedienungOeffnen()" title="Fernbedienung in einem kleinen Fenster öffnen">🎮</button>`+
    `<button class="tvzu" style="margin-left:0" onclick="tvZu()" title="Fernsehmodus verlassen (Esc)">✕</button>`;
  if(tvFilmKonto&&tvFilmKonto.verbunden)
    k.insertAdjacentHTML('beforeend',
      `<button class="tvzu" style="margin-left:0" onclick="tvKontoTrennen()" title="Eigenes Film-Konto dieses Profils trennen">🔌</button>`);
  const warn=filmWarnung(tvFilmZustand);
  const alt=document.getElementById('tv-warnung');
  if(alt)alt.remove();
  if(warn){
    const d=document.createElement('div');
    d.id='tv-warnung'; d.textContent=warn;
    if(tvFilmZustand&&tvFilmZustand.kann_verbinden)
      d.insertAdjacentHTML('beforeend',
        `<button class="tv-btn" onclick="tvKontoOeffnen()">Eigenes Konto verbinden</button>`);
    k.insertAdjacentElement('afterend',d);
  }
}
/* ---- Geräte koppeln (Teilprojekt 3, nur am PC) ----------------------------
   Fluss: Neues Gerät öffnet die LAN-Adresse (QR abfotografieren) → sieht die
   Pairing-Seite mit GROSSEM Code → der Besitzer gibt HIER frei (Profil zuordnen) → das
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
  const optionen=profile.map(p=>`<option value="${esc(p.id)}">${esc(p.emoji)} ${esc(p.name)}</option>`).join('');
  const wartend=d.items.filter(g=>!g.verifiziert), fest=d.items.filter(g=>g.verifiziert);
  body.innerHTML=
    (d.wlan
      ?`<div style="text-align:center"><img src="/api/geraet_qr" style="width:170px;height:170px;border-radius:8px;background:#fff;padding:6px"><br>`+
       `<span style="font-size:12px;color:var(--gedaempft)">Mit dem Gerät abfotografieren oder öffnen:<br><b>${esc(d.url)}</b></span></div>`
      :`<div style="font-size:13px;color:#c9803f;padding:4px 2px">⚠ Die Fernsteuerung ist AUS — kein Gerät erreicht den Server. `+
       `Erst oben unter „📱 Fernsteuerung" einschalten, dann koppeln.</div>`)+
    (wartend.length?'<div class="sm-titel" style="margin-top:8px">Wartet auf Freigabe</div>'+wartend.map(g=>
      `<div class="optrow"><span>${esc(g.name)} — Code <b style="color:var(--akz2)">${esc(g.code)}</b></span>`+
      `<span><select id="gpr-${esc(g.id)}" class="btn mini">${optionen}</select> `+
      `<button class="btn mini" data-arg="${esc(g.id)}" onclick="geraetFreigeben(this.dataset.arg)">✓ Freigeben</button></span></div>`).join(''):'')+
    (fest.length?'<div class="sm-titel" style="margin-top:8px">Gekoppelt</div>'+fest.map(g=>{
      const p=profile.find(x=>x.id===g.profil)||{emoji:'👤',name:g.profil};
      return `<div class="optrow"><span>${esc(g.name)} · ${esc(p.emoji)} ${esc(p.name)}</span>`+
      `<button class="btn mini" data-arg="${esc(g.id)}" onclick="geraetTrennen(this.dataset.arg)">🗑 Trennen</button></div>`;}).join(''):'')+
    (!wartend.length&&!fest.length&&d.wlan?'<div style="font-size:13px;color:var(--gedaempft);padding:6px 2px">Noch kein Gerät angemeldet — sobald eines die Adresse öffnet, erscheint es hier mit seinem Code.</div>':'');
  if(wartend.length)setTimeout(geraeteMalen,4000);     // frisch halten, solange gewartet wird
}
async function geraetFreigeben(id){
  const sel=document.getElementById('gpr-'+id);
  try{await api('/api/geraet_bestaetigen',{id, profil:(sel&&sel.value)||'standard'});
    toast('📺 Gerät freigegeben — es verbindet sich gleich von selbst.');
  }catch(e){toast('📺 Freigeben fehlgeschlagen.');}
  geraeteMalen();
}
async function geraetTrennen(id){
  try{await api('/api/geraet_entfernen',{id});
    toast('📺 Gerät getrennt — der Zugang ist sofort wertlos.');
  }catch(e){toast('📺 Trennen fehlgeschlagen.');}
  geraeteMalen();
}
/* ---- Profile („Wer schaut?", Teilprojekt 3) ------------------------------- */
let tvProfile=null, tvProfilModus=false;
function tvProfil(){return lsLesen('ytdl_profil')||'standard';}
async function tvProfileLaden(){
  try{tvProfile=((await (await fetch('/api/profile')).json())||{}).items||[];}
  catch(e){tvProfile=[{id:'standard',name:'Ich',emoji:'🦊'}];}
}
function tvProfilWahl(){
  tvProfilModus=true; tvFokus={r:0,i:0};
  const inhalt=document.getElementById('tv-inhalt');
  document.getElementById('tv-kopf').innerHTML='';
  inhalt.innerHTML=`<div class="tv-werschaut"><div class="tv-rtitel" style="font-size:34px;text-align:center;margin-top:8vh">Wer schaut?</div>`+
    `<div class="tv-band" style="justify-content:center;margin-top:30px">`+
    (tvProfile||[]).map((p,i)=>`<div class="tv-kachel tv-profil" data-pr="${i}" data-arg="${esc(p.id)}" onclick="tvProfilSetzen(this.dataset.arg)">`+
      `<div class="tv-pemoji">${esc(p.emoji)}</div><div class="tv-ktitel" style="font-size:18px">${esc(p.name)}</div></div>`).join('')+
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
  lsSchreiben('ytdl_profil',id);
  tvProfilModus=false; tvTab='home'; tvFokus={r:0,i:0};
  tvFilmReihen=null; tvKatalog=null; tvLaden();      // kein Katalog des vorigen Profils stehen lassen
}
/* Eigener TV-Dialog fürs Profil-Anlegen („bau den") — der native
   prompt() warf den Browser aus dem Vollbild. Name + Emoji-Reihe, komplett
   per Fernbedienung bedienbar (Ebenen: Feld → Emojis → Knöpfe). */
/* ---- Eigenes Film-Konto (25.11.2026: „jeder hat seine eigenen Zugänge") ----
   Ein Profil ohne eigenen Zugang sieht keine Filme. Hier verbindet es sein EIGENES
   Jellyfin-Konto: der Server prüft die Anmeldung genau einmal und legt sie nur für
   dieses Profil im Schlüsselbund ab. Das Passwort bleibt nach dem Senden nicht im
   Feld stehen. Ein gekoppeltes Gerät verbindet immer nur sein eigenes Profil. */
let tvKontoOffen=false, tvFilmKonto=null;
function tvKontoAdresse(){return '/api/filme_konto?profil='+encodeURIComponent(tvProfil());}
function tvKontoOeffnen(){
  tvKontoOffen=true;
  let el=document.getElementById('tv-konto');
  if(!el){el=document.createElement('div'); el.id='tv-konto';}
  (document.fullscreenElement||document.body).appendChild(el);   // Fullscreen-Regel
  el.style.display='flex';
  el.innerHTML=`<form class="dlg" onsubmit="event.preventDefault();tvKontoVerbinden()">`+
    `<div class="tv-rtitel" style="margin-top:0">Eigenes Film-Konto verbinden</div>`+
    `<div class="tvk-hinweis">Die Zugangsdaten deines eigenen Jellyfin-Kontos. Sie gelten nur für dieses Profil.</div>`+
    `<input id="tvk-url" type="url" placeholder="Jellyfin-Adresse (https://…)" autocomplete="url" required>`+
    `<input id="tvk-ben" placeholder="Benutzer" autocomplete="username" required>`+
    `<input id="tvk-pw" type="password" placeholder="Passwort" autocomplete="current-password" required>`+
    `<input id="tvk-seerr" type="url" placeholder="Jellyseerr-Adresse (freiwillig)" autocomplete="off">`+
    `<input id="tvk-tmdb" placeholder="TMDB-Schlüssel (freiwillig, für Bewertungen)" autocomplete="off">`+
    `<input id="tvk-omdb" placeholder="OMDb-Schlüssel (freiwillig, für Bewertungen)" autocomplete="off">`+
    `<div id="tvk-fehler" class="tvk-fehler"></div>`+
    `<div class="info-btns" style="justify-content:center">`+
      `<button class="tv-btn" type="submit">✓ Verbinden</button>`+
      `<button class="tv-btn zart" type="button" onclick="tvKontoZu()">✕ Abbrechen</button>`+
    `</div></form>`;
  const i=document.getElementById('tvk-url'); if(i)i.focus();
}
function tvKontoZu(){
  tvKontoOffen=false;
  const el=document.getElementById('tv-konto'); if(el){el.style.display='none'; el.innerHTML='';}
}
async function tvKontoVerbinden(){
  const wert=id=>(document.getElementById(id)||{}).value||'';
  const f=document.getElementById('tvk-fehler');
  if(f)f.textContent='Prüfe die Anmeldung …';
  let d=null;
  try{d=await api(tvKontoAdresse(),{art:'verbinden',url:wert('tvk-url'),benutzer:wert('tvk-ben'),
                                     passwort:wert('tvk-pw'),seerr:wert('tvk-seerr'),
                                     tmdb:wert('tvk-tmdb'),omdb:wert('tvk-omdb')});}
  catch(e){d={fehler:'Keine Antwort vom Server.'};}
  const pw=document.getElementById('tvk-pw'); if(pw)pw.value='';
  if(d&&d.ok){
    tvKontoZu(); toast('🎞 Konto verbunden — dein Katalog wird geladen.');
    tvKatalog=null; tvFilmReihen=null;
    const tvEl=document.getElementById('tv');            // Fernsehmodus oder Filme-Fenster am PC
    if(tvEl&&tvEl.style.display!=='none')tvLaden(); else if(typeof filmeLaden==='function')filmeLaden();
    return;
  }
  if(f)f.textContent=(d&&d.fehler)||'Verbinden fehlgeschlagen.';
}
async function tvKontoTrennen(){
  if(!confirm('Das eigene Film-Konto dieses Profils trennen? Merkliste und Zwischenspeicher werden beiseitegelegt, nicht gelöscht.'))return;
  let d=null;
  try{d=await api(tvKontoAdresse(),{art:'trennen'});}catch(e){}
  toast(d&&d.ok?'🔌 Film-Konto getrennt.':'🔌 '+((d&&d.fehler)||'Trennen fehlgeschlagen.'));
  tvKatalog=null; tvFilmReihen=null; tvLaden();
}
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
      `<button class="emo${e===tvDlgEmoji?' akt':''}" data-emo="${i}" onclick="tvDlgEmojiWahl(+this.dataset.emo)">${e}</button>`).join('')}</div>`+
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
    const p=await api('/api/profil_anlegen',{name, emoji:tvDlgEmoji});
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
/* 📡 Live (Freigabe): kodinerds-Legal-Liste, VLC spielt m3u8 direkt. */
let tvLive=null, tvKatalog=null;
async function tvKatalogLaden(){
  try{tvKatalog=((await (await fetch('/api/filme/katalog?profil='+encodeURIComponent(tvProfil()))).json())||{}).eintraege||[];}
  catch(e){tvKatalog=[];}
  tvMalen();
}
async function tvLiveLaden(){
  try{tvLive=((await (await fetch('/api/live')).json())||{}).items||[];}catch(e){tvLive=[];}
  tvMalen();
}
async function tvLivePlay(e){
  if(document.fullscreenElement){try{document.exitFullscreen();}catch(x){}}
  const g=++liveStartGen;
  try{
    await huelleMelden();                              // Hülle: Sender rendert ins Panel
    if(g!==liveStartGen)return;                        // während der Anmeldung überholt: nichts mehr starten
    const r=await api('/api/live/play',{url:e.url, name:e.name, vol:plVol});
    if(r.fehler){toast('📡 '+r.fehler); return;}
    tvFilmPlayer('',e.name);                           // Fernbedienung ohne Seek-Ziel
  }catch(x){toast('📡 Kanal nicht erreichbar.');}
}
function tvTitelReihe(name,arr){return [name, arr.map(x=>({art:'titel',id:x.id,
  name:x.titel, bild:x.cover_album?('/api/cover?id='+encodeURIComponent(x.id)):(x.thumb||''),
  quer:!x.cover_album}))];}
// Bild-Kette (06.08.: „welche Bilder hast du genommen? Gibt es keine
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
  // Der Besitzer 06.08.: Server liefert top 30 (Bayes) — jede Ansicht filtert ihre Art
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
    // Vorgabe: „Wo sind eigentlich die restlichen Filme vom Film-Server?" — die Reihen
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
    /* Der Such-Korpus MUSS der ganze Katalog sein. Bis 13.08.2026 suchte er in
       den REIHEN — und die decken nur einen Teil ab: gemessen 1864 von 4885
       Titeln. Der Besitzer tippte vom Sofa einen Film, den der Film-Server nachweislich hat, und
       bekam „Hier ist noch nichts"; die naheliegende Reaktion ist, ihn über
       Jellyseerr nochmal zu wünschen, obwohl er längst auf dem Server liegt.
       Bis der Katalog nachgeladen ist, wird in den Reihen gesucht (sofortige
       Antwort), danach zeichnet tvKatalogLaden() über tvMalen() neu. */
    if(tvKatalog===null)tvKatalogLaden();
    const filme=tvKatalog||[...(f.top||[]),...(f.neu||[]),
      ...[].concat(...Object.values(f.genres||{}))];
    const gesehen=new Set(); const treffF=filme.filter(e=>{if(gesehen.has(e.id))return false;
      gesehen.add(e.id); return (e.titel||'').toLowerCase().includes(q);});
    return [tvFilmReihe(treffF.length>20?`Filme & Serien (20 von ${treffF.length})`
      :'Filme & Serien',treffF.slice(0,20)),
      tvTitelReihe('Deine Bibliothek',da.filter(x=>(x.titel||'').toLowerCase().includes(q)).slice(0,20)),
      tvWunschReihe('➕ Wünschen — ganzer Katalog (Enter im Suchfeld)',tvSeerrErgebnis||[])];
  }
  return [];
}
/* ---- Wünsche über Jellyseerr (Teilprojekt 4) ------------------------------
   Enter im Suchfeld fragt Film-Server-Jellyseerr (dahinter Radarr/Sonarr) — die
   Treffer zeigen ehrlich ihren Stand: ✔ da · ◐ teils · ⏳ kommt · ➕ wünschbar.
   Enter auf ➕ stellt den Wunsch (Serien: alle Staffeln). Bewusst NUR auf
   Enter, nicht je Tastendruck — wir hämmern nicht auf den Film-Server. */
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
  if(!tvSeerrErgebnis.length)toast('🔍 Nichts gefunden — oder der Wunsch-Server ist gerade aus.');
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
    const r=await api('/api/filme/anfragen',{tmdb:e.tmdb, typ:e.typ});
    if(r.ok){toast('➕ Wunsch gestellt — der Server lädt ihn, sobald er kann.'); e.status='kommt'; tvMalen();}
    else toast('➕ '+(r.fehler||'Anfrage fehlgeschlagen.'));
  }catch(x){toast('➕ Anfrage nicht erreichbar.');}
}
function tvMalen(opt){                                 // opt.vorschau===false: Fokus ohne Hover-Karte (Filmende)
  tvKopfMalen();
  const inhalt=document.getElementById('tv-inhalt');
  tvReihenListe=tvReihenFuer().filter(([,items])=>items.length);
  const suche=tvTab==='suche'
    ?`<input id="tv-suche" placeholder="Titel suchen…" oninput="tvMalen()" autocomplete="off">`:'';
  const hero=(tvTab==='home')?'<div id="tv-hero"></div>':'';
  if(!tvReihenListe.length){
    inhalt.innerHTML=hero+suche+(tvTab==='suche'?'':'<div class="tv-leer">Hier ist noch nichts — '+
      (tvTab==='herz'?'markiere Songs mit dem ♡-Herz.'
        // Ohne eigenen Film-Zugang hilft „Abgleichen“ nicht: der Weg steht oben (25.11.2026).
        :(tvFilmZustand&&tvFilmZustand.profil_ohne_zugang)
          ?(tvFilmZustand.kann_verbinden?'Filme gibt es mit deinem eigenen Konto (oben verbinden).'
                                        :'Filme gibt es nur mit einem eigenen Konto.')
        :'der Film-Katalog füllt sich über 🎬 Filme → ⟳ Abgleichen.')+'</div>');
  }else{
    inhalt.innerHTML=hero+suche+tvReihenListe.map((reihe,r)=>{
      const [name,items]=reihe;
      const pfeile=reihe[2]==='wrap'?'':`<button class="tv-pfeil links" onclick="tvBlaettern(this,-1)" tabindex="-1">‹</button>`+
        `<button class="tv-pfeil rechts" onclick="tvBlaettern(this,1)" tabindex="-1">›</button>`+
        `<div class="tv-seiten"></div>`;
      return `<div class="tv-reihe"><div class="tv-rtitel">${esc(name)}</div><div class="tv-band${reihe[2]==='wrap'?' wrap':''}">`+
      items.map((e,i)=>{
        const film=e.art==='film'&&e.id;
        // Netflix-Referenz (06.08.): 16:9-Cover-Kette Thumb→Backdrop→
        // Poster, Fortschrittsbalken unter angefangenen Titeln.
        const fb=film&&e.bild2
          ?` data-fb1="${esc(e.bild2)}" data-fb2="${esc(e.bild3)}" onerror="if(!this.dataset.s){this.dataset.s=1;this.src=this.dataset.fb1}else if(this.dataset.s==1){this.dataset.s=2;this.src=this.dataset.fb2}else this.style.visibility='hidden'"`
          :` onerror="this.style.visibility='hidden'"`;
        const balken=(film&&e.pos>30&&e.dauer)
          ?`<div class="tv-kbalken"><div style="width:${Math.min(99,Math.round(e.pos/(e.dauer*60)*100))}%"></div></div>`:'';
        return `<div class="tv-kachel${e.quer?' quer':''}${film?' f16':''}" data-r="${r}" data-i="${i}"${film?` data-fid="${esc(e.id)}"`:''} onclick="tvKachelKlick(event,+this.dataset.r,+this.dataset.i)">`+
        (e.bild?`<img loading="lazy" src="${e.bild}"${fb}>`:'<img>')+balken+
        `<div class="tv-ktitel">${esc(e.name)}</div></div>`;}).join('')+`</div>${pfeile}</div>`;}).join('');
  }
  const s=document.getElementById('tv-suche');
  if(s&&tvTab==='suche'){const v=s.value; s.focus(); s.value=''; s.value=v;
    tvFokus={r:-1,i:Math.max(0,TV_TABS.findIndex(t=>t[0]===tvTab))};}   // Fokus gehört dem Feld
  if(tvTab==='home')tvHeroMalen();                     // Billboard lädt asynchron nach
  tvFokusMalen(!(opt&&opt.vorschau===false));
}
function tvFokusMalen(vorschau){                       // vorschau===false: Kachel fokussieren, Karte nicht öffnen
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
    snippetAus(); if(vorschau!==false)snippetAn(k);}   // D-Pad-Fokus = Hover (Fernbedienung)
}
function tvHeroDa(){return !!document.querySelector('#tv-hero [data-hero]');}
function tvKachelKlick(ev,r,i){
  // Netflix-Verhalten (Fund: „ganz rechts … bewegt er die ganze reihe"):
  // eine ANGESCHNITTENE Kachel blättert die Reihe eine Seite weiter, nur
  // eine voll sichtbare öffnet. Fund 06.08. („der mit gelber umrandung
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
  // ENDLOS-KREIS NUR VORWÄRTS (07.08., präzisiert: „1-2-3-4-5-1-2-…" —
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
  // Kachelbündig blättern (07.08.): Schritt = GANZE Kachelspalten und
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
  // Der Besitzer 07.08.: passt ALLES in den Rahmen, braucht es weder Pfeile noch
  // Striche — die Reihe ist dann keine Bahn, sondern ein Regal.
  const passt=!band.dataset.klon&&band.scrollWidth<=band.clientWidth+4;
  reihe.querySelectorAll('.tv-pfeil').forEach(p=>p.style.display=passt?'none':'');
  if(passt){box.innerHTML=''; return;}
  // Am echten Anfang gibt es keinen Links-Weg („Erste Position geht
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
  if(e.art==='live'){tvLivePlay(e); return;}           // 📡 Kanal (Freigabe)
  if(e.art==='seerr'){                                 // Wunsch-Kachel (Teilprojekt 4)
    if(e.status==='da'&&e.id)tvInfo(e.id);             // schon da + im Spiegel -> Info
    else tvAnfrage(e);
    return;
  }
  if(e.art==='film'){tvInfo(e.id);}                    // Netflix-Muster: erst die Info-Seite
  else{tvZu(); playerPlay([e.id]);}
}
/* ---- Hero-Billboard + More-Info (Freigabe: „weiter mit dem tv feinschliff,
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
  try{const a=await (await fetch('/api/filme/detail?id='+encodeURIComponent(kand.id))).json();
      if(a&&!a.fehler)d=a;}catch(e){}                  // Fehler-Objekt ist keine Meta
  tvHeroDaten=d;                                       // Meta für den Player (Hero-Direktstart)
  if(!document.getElementById('tv-hero'))return;       // Tab inzwischen gewechselt
  box.innerHTML=
    `<img class="hero-bg" src="/api/filme/bild?id=${encodeURIComponent(kand.id)}&art=Backdrop" `+
      `data-fb="${esc('/api/filme/bild?id='+encodeURIComponent(kand.id))}" onerror="this.onerror=null;this.src=this.dataset.fb">`+
    `<div class="hero-text"><div class="hero-titel">${esc(d.titel||'')}</div>`+
    `<div class="hero-meta">${tvMetaZeile(d)}</div>`+
    `<div class="hero-besch">${esc(d.beschreibung||'')}</div>`+
    `<div class="hero-btns">`+
      (kand.typ==='serie'
        ?`<button class="tv-btn" data-hero="0" data-arg="${esc(kand.id)}" onclick="tvInfo(this.dataset.arg)">▶ Weiterschauen</button>`
        :`<button class="tv-btn" data-hero="0" data-arg="${esc(kand.id)}" onclick="filmePlay(this.dataset.arg)">▶ Abspielen</button>`)+
      `<button class="tv-btn zart" data-hero="1" data-arg="${esc(kand.id)}" onclick="tvInfo(this.dataset.arg)">ℹ Mehr Infos</button>`+
    `</div></div>`;
}
let tvInfoDaten=null, tvInfoStaffel=0;                 // {d, mw, eps} der offenen Info
async function tvInfo(id){
  // „Mehr wie das"-Rückweg: der vorige Film kommt auf den Stapel — Esc
  // führt erst zu IHM zurück, dann erst ganz raus (Netflix-Verhalten).
  if(tvInfoOffen&&tvInfoId&&tvInfoId!==id)tvInfoStapel.push(tvInfoId);
  tvInfoId=id; tvInfoOffen=true; tvInfoFokus={r:0,i:0}; tvInfoDaten=null; tvInfoStaffel=0;
  // Die Detailseite gibt es auch OHNE TV-Modus (05.08.: Klick im
  // 🎬-Fenster öffnet sie) — dann übernimmt tvKey nur für sie.
  document.addEventListener('keydown',tvKey,true);
  const el=document.getElementById('tv-info');
  // Fullscreen-Falle (Fund): im Fernsehmodus rendert der Browser NUR das
  // Vollbild-Element (#tv) samt Kindern — als Geschwister unter <body>
  // erschien die Info erst NACH dem Vollbild („öffnet sich im Browser").
  // Darum die Seite dorthin umhängen, wo gerade gerendert wird.
  const ziel=document.fullscreenElement||document.body;
  if(el.parentNode!==ziel)ziel.appendChild(el);
  el.style.display='flex';
  el.innerHTML='<div class="info-body" style="font-size:24px;padding:60px">Lade…</div>';
  let d=null, mw=[], eps=[], epsFehler='';
  try{d=await (await fetch('/api/filme/detail?id='+encodeURIComponent(id)+'&profil='+encodeURIComponent(tvProfil()))).json();}catch(e){}
  try{mw=((await (await fetch('/api/filme/mehrwie?id='+encodeURIComponent(id))).json())||{}).items||[];}catch(e){}
  if(d&&d.typ==='serie'){                              // Staffeln + Folgen (Freigabe)
    // fehler ('zugang'|'netz') seit 24.09.: eine leere Liste hieß vorher auch
    // „der Film-Server lehnt uns ab" — und sah aus wie eine Serie ohne Folgen.
    try{const j=(await (await fetch('/api/filme/episoden?id='+encodeURIComponent(id))).json())||{};
      eps=j.items||[]; epsFehler=j.fehler||'';}catch(e){}
  }
  if(!tvInfoOffen||tvInfoId!==id)return;               // inzwischen geschlossen/weiter
  if(!d||d.fehler){el.innerHTML='<div class="info-body" style="padding:60px">Film nicht gefunden. (Esc = zurück)</div>'; return;}
  // Was diese Seite gerade gemeldet hat (Esc öffnet die Info sofort — Spiegel
  // bzw. Jellyfin haben die Meldung da oft noch nicht verarbeitet).
  filmGemeldetAnwenden(d); eps.forEach(filmGemeldetAnwenden);
  tvInfoDaten={d,mw,eps,epsFehler}; tvInfoMehr=mw;
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
  // …an ihrer gemerkten Stelle, nach derselben Regel wie ⏮/⏭ (gesehen, ab 90 %
  // oder bis 30 s = Anfang). Vorher startete der Knopf immer bei 0 (Nebenbefund 24.09.).
  const fehler=tvInfoDaten&&tvInfoDaten.epsFehler;
  if(e)filmePlay(e.id,tvpLandePos(e));
  else toast(fehler?'🎬 '+folgenFehlerText(fehler)+'.':'🎬 Keine Folgen gefunden.');
}
function folgenFehlerText(f){                          // f: 'zugang' | 'netz' (Route episoden)
  return f==='zugang'?'Folgen gerade nicht abrufbar – Zugang zum Film-Server gestört'
                     :'Folgen gerade nicht abrufbar – der Film-Server antwortet nicht';
}
async function tvMerk(id){
  try{
    const r=await api('/api/filme/merk?profil='+encodeURIComponent(tvProfil()),{id});
    if(tvInfoDaten)tvInfoDaten.d.gemerkt=!!r.an;
    toast(r.an?'🎞 Auf deiner Liste.':'🎞 Von der Liste genommen.');
    tvInfoMalen();
    tvFilmReihen=null; tvLadenStill();                 // Home-Reihe frisch ziehen
  }catch(e){toast('🎞 Merken fehlgeschlagen.');}
}
async function tvLadenStill(){
  try{tvFilmReihen=filmReihenAnwenden(await (await fetch('/api/filme/reihen?profil='+encodeURIComponent(tvProfil()))).json());}catch(e){}
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
  // Netflix-/Disney-Muster am Fernseher (Besitzer-Liste 05.08. = exakt deren
  // Detailseite): Titel groß, Fortschrittsbalken mit dem Spot, Weiterschauen/
  // Von vorne, ＋ Liste, Meta-Badges (FSK/Qualität), Klappentext, Besetzung/
  // Genres/Ton/Untertitel, Staffeln, Mehr wie das, Trailer & mehr, und unten
  // der „Über“-Block (Regie · Besetzung · Drehbuch · Genres · Dieser Film
  // ist · Altersfreigabe).
  const el=document.getElementById('tv-info');
  if(!el||!tvInfoDaten)return;
  const {d,mw,eps,epsFehler}=tvInfoDaten, id=tvInfoId;
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
      ?`<button class="tv-btn" data-info="0" data-arg="${esc(id)}" data-pos="${+d.position_s||0}" onclick="filmePlay(this.dataset.arg,+this.dataset.pos)">▶ Weiterschauen</button>`+
       `<button class="tv-btn zart" data-info="1" data-arg="${esc(id)}" onclick="filmePlay(this.dataset.arg,0)">↻ Von vorne</button>`
      :`<button class="tv-btn" data-info="0" data-arg="${esc(id)}" onclick="filmePlay(this.dataset.arg)">▶ Abspielen</button>`))+
    `<button class="tv-btn zart" data-info="2" data-arg="${esc(id)}" onclick="tvMerk(this.dataset.arg)">${d.gemerkt?'✓ Gemerkt':'＋ Meine Liste'}</button>`;
  const dieserFilm=d.tagline||((d.genres||[]).slice(0,3).join(' · '));
  const querBild=(eid)=>`<img loading="lazy" src="/api/filme/bild?id=${encodeURIComponent(eid)}&art=Backdrop" `+
    `data-fb="${esc('/api/filme/bild?id='+encodeURIComponent(eid))}" onerror="this.onerror=null;this.src=this.dataset.fb">`;
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
        staffeln.map(n=>`<button class="tv-btn zart${n===tvInfoStaffel?' akt':''}" data-st="${+n||0}" onclick="tvStaffel(+this.dataset.st)">Staffel ${esc(n||'?')}</button>`).join('')+`</div>`+
        `<div class="tv-band">`+folgen.map((e,i)=>
          `<div class="tv-kachel quer" data-ep="${i}" data-arg="${esc(e.id)}" data-pos="${e.position_s>30&&!e.gesehen?(+e.position_s||0):0}" onclick="filmePlay(this.dataset.arg,+this.dataset.pos)" title="${esc(e.titel)}">`+
          `<img loading="lazy" src="/api/filme/bild?id=${encodeURIComponent(e.id)}" onerror="this.style.visibility='hidden'">`+
          `<div class="tv-ktitel">${e.gesehen?'✓ ':''}F${e.folge} · ${esc(e.titel)}${e.position_s>0&&!e.gesehen?' ⏸':''}</div></div>`).join('')+`</div>`
        :(epsFehler?`<div class="tv-rtitel" style="margin-top:14px">Staffeln</div>`+
          `<div class="info-neben">⚠ ${esc(folgenFehlerText(epsFehler))}</div>`:''))+
      (mw.length?`<div class="tv-rtitel" style="margin-top:16px">Mehr wie das</div><div class="info-grid">`+
        mw.slice(0,9).map((e,i)=>`<div class="tv-kachel" data-mw="${i}" data-arg="${esc(e.id)}" onclick="tvInfo(this.dataset.arg)">`+
          querBild(e.id)+(e.laufzeit_min?`<span class="tv-dauer">${Math.floor(e.laufzeit_min/60)}h ${e.laufzeit_min%60}m</span>`:'')+
          `<div class="tv-ktitel">${esc(e.titel)}</div></div>`).join('')+`</div>`:'')+
      (d.trailer&&d.trailer.length?`<div class="tv-rtitel" style="margin-top:16px">Trailer & mehr</div><div class="info-grid">`+
        d.trailer.map((t,i)=>`<div class="tv-kachel" data-trl="${i}" data-arg="${esc(t.key)}" onclick="window.open('https://www.youtube.com/watch?v='+encodeURIComponent(this.dataset.arg),'_blank')" title="${esc(t.name)}">`+
          `<img loading="lazy" src="https://i.ytimg.com/vi/${esc(t.key)}/mqdefault.jpg" onerror="this.style.visibility='hidden'">`+
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
/* Gedrückt halten = immer schneller (07.08.: „erst langsam, dann
   schnell"). Der Browser wiederholt starr; wir drosseln die ersten
   Wiederholungen und lassen die Schlagzahl dann bis 60 ms/Schritt steigen —
   so wandert man mit einem Tastendruck ruhig, mit gehaltener Taste flott
   durch lange Reihen. */
let _wdhTaste='', _wdhZahl=0, _wdhLetzte=0;
function tvWiederholungBremst(ev){
  const jetzt=Date.now();
  // Neue Taste ODER echte Pause seit dem letzten Anschlag ⇒ neu anfangen.
  // (`ev.repeat` allein trägt nicht: manche Tastaturen/Layouts setzen es
  // nicht, dann wandert der Fokus mit voller Systemrate — der Besitzer 07.08.:
  // „das gedrückt halten … funktioniert nicht".)
  if(ev.key!==_wdhTaste||jetzt-_wdhLetzte>420){
    _wdhTaste=ev.key; _wdhZahl=0; _wdhLetzte=jetzt; return false;
  }
  const abstand=Math.max(55,240-_wdhZahl*30);          // 240 ms → 55 ms
  if(jetzt-_wdhLetzte<abstand)return true;             // zu früh: verwerfen
  _wdhLetzte=jetzt; _wdhZahl++;
  return false;
}
/* Spul-Stufe beim Halten (07.08.: „gedrückt halten soll dann schneller
   und schneller vorspulen"): 10 s → 30 s → 60 s → 120 s. */
function tvSpulWeite(){
  return [10,10,30,30,60,60,120][Math.min(6,_wdhZahl)];
}
/* Senkrecht wandern heißt: zur Kachel, die WIRKLICH darüber/darunter liegt
   (07.08.: „nicht auf die xte Position"). Reihen sind unterschiedlich
   weit gescrollt — der bloße Index führt sonst quer durchs Bild. Wir
   nehmen die Kachel, deren Mitte der aktuellen X-Mitte am nächsten ist. */
function tvNachbarSenkrecht(zielReihe){
  const jetzt=document.querySelector(
    `#tv .tv-kachel[data-r="${tvFokus.r}"][data-i="${tvFokus.i}"]`);
  const kacheln=[...document.querySelectorAll(`#tv .tv-kachel[data-r="${zielReihe}"]`)];
  if(!jetzt||!kacheln.length){
    const n=((tvReihenListe[zielReihe]||[[],[]])[1]||[]).length;
    return Math.max(0,Math.min(tvFokus.i,n-1));        // Rückweg: alter Index
  }
  const r=jetzt.getBoundingClientRect(), mitte=r.left+r.width/2;
  let beste=kacheln[0], abstand=Infinity;
  kacheln.forEach(k=>{
    const kr=k.getBoundingClientRect();
    const d=Math.abs(kr.left+kr.width/2-mitte);
    if(d<abstand){abstand=d; beste=k;}
  });
  return +beste.dataset.i||0;
}
function tvKey(ev){
  const tv=document.getElementById('tv');
  const tvOffen=tv&&tv.style.display!=='none';
  if(!tvOffen&&!tvInfoOffen&&!tvDialogOffen&&!tvpOffen&&!tvKontoOffen)return;  // Overlays auch ohne TV
  if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(ev.key)
     &&tvWiederholungBremst(ev)){ev.preventDefault(); ev.stopPropagation(); return;}
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
    // Spulen mit Beschleunigung (der Besitzer): kurz tippen = 10 s, halten wird
    // immer weiter — die Bremse zählt die Wiederholungen mit.
    else if(ev.key==='ArrowLeft'){
      if(tvWiederholungBremst(ev)){ev.preventDefault(); return;}
      tvpRel(-tvSpulWeite());
    }
    else if(ev.key==='ArrowRight'){
      if(tvWiederholungBremst(ev)){ev.preventDefault(); return;}
      tvpRel(tvSpulWeite());
    }
    else if(ev.key==='ArrowUp'){plbVol(Math.min(100,plVol+5)); tvpBefehl('vol',{wert:plVol});}
    else if(ev.key==='ArrowDown'){plbVol(Math.max(0,plVol-5)); tvpBefehl('vol',{wert:plVol});}
    else if(ev.key==='s'||ev.key==='S')tvpPanel('spuren');   // Sofa-Weg zu den Settings
    else getan=false;
    if(getan){ev.preventDefault(); ev.stopPropagation();}
    return;
  }
  // Konto-Dialog: nur Esc schließt; Tippen, Tab und Enter (sendet das Formular) bleiben frei.
  if(tvKontoOffen){
    if(ev.key==='Escape'){tvKontoZu(); ev.preventDefault(); ev.stopPropagation();}
    else ev.stopPropagation();
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
    // Der Besitzer 07.08.: „zurück darf den fernsehmodus nicht beenden. Nur aus."
    // Backspace geht IMMER nur eine Ebene hoch (Reihe → Kopfleiste) und
    // bleibt dort stehen; schließen tut allein Escape.
    if(ev.key==='Escape'&&filmLaeuft())filmStopp();    // Esc beendet erst den FILM
    else if(ev.key==='Backspace'){
      if(tvFokus.r>=0)tvFokus={r:-1,i:TV_TABS.findIndex(t=>t[0]===tvTab)};
    }
    else tvZu(); }
  else if(ev.key==='ArrowLeft'){ if(tvFokus.r===-2)tvFokus.i=Math.max(0,tvFokus.i-1); else tvFokus.i=Math.max(0,tvFokus.i-1); }
  else if(ev.key==='ArrowRight'){ if(tvFokus.r===-2)tvFokus.i=Math.min(1,tvFokus.i+1); else if(tvFokus.r<0)tvFokus.i=Math.min(tabs-1,tvFokus.i+1); else tvFokus.i=Math.min(reihe().length-1,tvFokus.i+1); }
  else if(ev.key==='ArrowUp'){
    if(tvFokus.r===0){tvFokus=tvHeroDa()?{r:-2,i:0}:{r:-1,i:TV_TABS.findIndex(t=>t[0]===tvTab)};}
    else if(tvFokus.r===-2){tvFokus={r:-1,i:TV_TABS.findIndex(t=>t[0]===tvTab)};}
    else if(tvFokus.r>0)tvFokus={r:tvFokus.r-1,i:tvNachbarSenkrecht(tvFokus.r-1)};
  }
  else if(ev.key==='ArrowDown'){
    if(tvFokus.r===-1){tvFokus=tvHeroDa()?{r:-2,i:0}:{r:0,i:0};}
    else if(tvFokus.r===-2){tvFokus={r:0,i:0};}
    else if(tvFokus.r<tvReihenListe.length-1)
      tvFokus={r:tvFokus.r+1,i:tvNachbarSenkrecht(tvFokus.r+1)};
  }
  else if(ev.key==='Enter'){
    if(tvFokus.r===-2){const b=document.querySelector(`#tv-hero [data-hero="${tvFokus.i}"]`); if(b)b.click();}
    else if(tvFokus.r<0){tvTabWahl(TV_TABS[Math.max(0,tvFokus.i)][0]); tvFokus={r:-1,i:tvFokus.i};}
    else tvWahl(tvFokus.r,tvFokus.i);
  }
  else getan=false;
  if(getan){ev.preventDefault(); ev.stopPropagation(); tvFokusMalen();}
}

