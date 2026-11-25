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
    // Mini-Player (oben, eingebettet, überdeckt nichts — der Besitzer 21.07.).
    if(tabs)tabs.style.display='none'; body.style.display='none';
    const pl=document.getElementById('view-player');
    if(cm&&pl&&pl.parentNode!==cm)cm.appendChild(pl);
    return;
  }
  if(tabs)tabs.style.display=''; body.style.display=''; if(cm)cm.innerHTML='';
  document.querySelectorAll('#dlbox-tabs .dlbox-tab').forEach(t=>t.classList.toggle('an',t.dataset.dlt===dlboxAktiv));
  if(NUR_FERN&&dlboxAktiv==='abos')dlboxAktiv='queue';   // Abos verwaltet nur der PC
  const act=document.getElementById('dlbox-action'), a=DLACTION[dlboxAktiv];   // Aktion oben in der Reiter-Leiste
  if(act&&a&&!(NUR_FERN&&(dlboxAktiv==='queue'||dlboxAktiv==='abos'))){act.textContent=a[0]; act.setAttribute('onclick',a[1]); act.style.display='';}
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
  // Füllt den Bildschirm: Höhe aus dem Fenster statt fixer 660px (14.07.:
  // „Vorlagen schlagen alte Größen vor"), Abstände = eingestellter Gap (Standard 0).
  const W=window.innerWidth, g=Math.max(0,fensterAbstand());
  const bw=Math.max(320, W-16), H=_canvasH();          // Panels füllen genau den Canvas (kein Seiten-Scroll)
  // Downloads (Hinzufügen/Warteschlange/Fertig/Log) leben jetzt fest eingebettet
  // in der Command-Bar (#dlbox) — der Canvas trägt nur noch Bibliothek + Player
  // (21.07.). Bibliothek ist die Hauptfläche, Player als Spalte rechts.
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
  lsWeg('ytdl_layout_vormini');   // frischer Start = kein Mini-Rest
  try{const s=JSON.parse(localStorage.getItem(LKEY)||'null');
    if(s&&s.panels){
      delete s.mini;                                 // Mini-Layout nie als Hauptlayout übernehmen
      s.panels=s.panels.filter(p=>!['pmini','mlib','mplq','mdl'].includes(p.id));   // Mini-Fenster nie mitladen
      // Migration (21.07.): Download-Views leben jetzt im festen dlbox, nicht
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
    // kollisionsfrei platzieren (Fund 14.07.: fixe Position 120/70 lag über der Bibliothek)
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
  // freiePosition würde es bei vollem Canvas unter den Falz schieben, Fund 21.07.).
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
  // Basis-Anker (Build 92, Fund „alles ein wenig bewegt"): NUR eine ECHTE
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
  lsSchreiben(LKEY,JSON.stringify(L));
}
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
/* Fenster-Resize (22.07.): die Canvas-Fenster (Bibliothek/Player/…) wachsen
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
  // Vollbild loest SELBST ein resize aus (Build 97, Vorgabe: „geht sofort wieder
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
  // Fund 08.09.2026, live gemessen: die Minima-Klemme macht ein Fenster
  // BREITER, verschiebt seine Position aber weiter nach rechts — bei 430 px
  // stand der Player auf x=275 mit der Mindestbreite 220 und ragte 65 px aus
  // der Flaeche. Sichtbar sofort, weil #canvas abschneidet (overflow:hidden).
  // Erst zurueck in den Rahmen holen, DANN entklemmen: der Reflow loest die
  // dabei entstehenden Ueberlappungen mit seinem Zeilenumbruch auf.
  LK.inDenRahmen(kopie, m.cw);
  // Bild 05.08.: die Minima-Klemme schob geklemmte Fenster unter ihre
  // Nachbarn (schmales Fenster + breite Basis). Der Reflow ordnet NUR die
  // Projektion — die Basis (gebaute Anordnung) bleibt unangetastet.
  LK.entklemmen(kopie, m.cw, Math.max(0,fensterAbstand()));
  LK.inDenRahmen(kopie, m.cw);          // Zusage x+w<=cw ohne Wenn und Aber
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

/* ---- Verlust-Schutz (13.07.2026, wie im Dashboard — ein System): vor jedem Layout-
   Wechsel (Vorlage, eigenes Layout, Aufräumen, Reset) wird die aktuelle Anordnung gemerkt.
   ↩ Vorheriges TAUSCHT mit der gemerkten -> nochmal ↩ wechselt wieder vor.
   Nichts geht mit EINEM Klick verloren. ---- */
const LPREV='ytdl_layout_prev_v1';
function layoutMerken(){lsSchreiben(LPREV,JSON.stringify(L));}
function layoutVorheriges(){
  let prev=null; try{prev=JSON.parse(localStorage.getItem(LPREV)||'null');}catch(e){}
  if(prev&&prev.panels)prev.panels=prev.panels.filter(p=>p.id!=='pmini');
  if(!prev||!prev.panels||!prev.panels.length){alert('Noch kein vorheriges Layout gemerkt — es wird bei jedem Layout-Wechsel automatisch gesichert.');return;}
  miniVerlassen();
  const cur=JSON.stringify(L);
  L=prev; renderPanels(); saveLayout();
  lsSchreiben(LPREV,cur);
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
  // zuletzt gewählte Anordnung im Select anzeigen (überlebt den Reload, der Besitzer 14.07.)
  try{const merk=localStorage.getItem('ytdl_layout_wahl');
    if(merk&&[...sel.options].some(o=>o.value===merk))sel.value=merk;}catch(e){}
}
function layoutWaehlen(v){
  if(!v)return;
  lsSchreiben('ytdl_layout_wahl',v);
  if(v.startsWith('v:'))layoutVorlage(v.slice(2));
  else if(v.startsWith('m:')){const l=meineLayouts()[v.slice(2)];
    if(l){layoutMerken(); miniVerlassen(); L=JSON.parse(JSON.stringify(l));
      L.panels=L.panels.filter(p=>p.id!=='pmini'); layoutAnViewport(); renderPanels(); saveLayout();}}
}
function layoutSpeichern(){
  const n=prompt('Name für diese Fenster-Anordnung:'); if(!n||!n.trim())return;
  const eigene=meineLayouts(); eigene[n.trim()]=JSON.parse(JSON.stringify(L));
  lsSchreiben('ytdl_layouts_v1',JSON.stringify(eigene));
  layoutSelectFuellen(); document.getElementById('layoutsel').value='m:'+n.trim();
}
function layoutLoeschen(){
  const sel=document.getElementById('layoutsel'), v=sel.value;
  if(!v.startsWith('m:')){alert('Bitte oben eines DEINER gespeicherten Layouts wählen.');return;}
  const name=v.slice(2); if(!confirm('Layout „'+name+'" löschen?'))return;
  const eigene=meineLayouts(); delete eigene[name];
  lsSchreiben('ytdl_layouts_v1',JSON.stringify(eigene));
  layoutSelectFuellen();
}

/* ---- Mini-Player-Modus (21.07.): Player schrumpft zur kleinen Karte oben
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
  // Mini-Layout (21.07.): Bibliothek links groß; rechts als Spalte die
  // Playlist OBEN und darunter das gelöste Download-Fenster (gestapelt). Die
  // Mini-Karte ist position:fixed oben rechts (über der Command-Bar).
  const oben=Math.round((ch-16-g)*0.5);               // Playlist obere Hälfte
  // Kein pmini-Fenster mehr: der Mini-Player sitzt eingebettet oben in der
  // Command-Bar (#cmd-mini) und überdeckt nichts (21.07.).
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
    lsSchreiben(VORMINI,JSON.stringify(miniVor));
    document.body.classList.add('mini');
    L=miniLayoutBauen(); miniAn=true; renderPanels();
    if(b){b.classList.add('an'); b.textContent='🔳 Voll';}
  }else{
    document.body.classList.remove('mini'); miniAn=false;
    let vor=miniVor;
    if(!vor){try{vor=JSON.parse(localStorage.getItem(VORMINI)||'null');}catch(e){}}
    if(vor&&vor.panels){delete vor.mini; vor.panels=vor.panels.filter(p=>p.id!=='pmini'); L=vor;}
    else L=defaultLayout();
    miniVor=null; lsWeg(VORMINI);
    layoutAnViewport();                                // Fenster im Mini resized? Basis-Projektion statt roher Alt-Pixel
    renderPanels();
    if(b){b.classList.remove('an'); b.textContent='🔳 Mini';}
  }
}
function miniVerlassen(){                              // Layout-Wechsel beendet den Mini-Modus (Aufrufer setzt neues L)
  if(!miniAn)return;
  miniAn=false; miniVor=null; document.body.classList.remove('mini');
  lsWeg(VORMINI);
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

function fensterAbstand(){const v=parseInt(lsLesen('ytdl_gap'),10); return isNaN(v)?0:v;}
// Fenster „kleben": die linke/obere Kante des gezogenen Fensters an sinnvolle
// Positionen fangen — Rand, Kanten-Ausrichtung mit Nachbarn, und Anlegen mit
// eingestelltem Abstand (Gap). So sitzen Fenster sauber nebeneinander.
function snapKanten(p){                               // kräftiger Magnet („haften!") — Mathe: layout_kern
  const c=document.getElementById('canvas');
  const s=LK.snapXY(p, L.panels, c.clientWidth, c.clientHeight, fensterAbstand(), 16);
  p.x=s.x; p.y=s.y;
}

/* ---- ✏-Layout-Modus (13.07., Muster wie im Dashboard): AUS = Ziehen ist
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
/* Verdrängen (13.07.: „das bewegte Fenster muss Priorität haben"): alle
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
    // sonst entstehen genau die Rest-Überlappungen, die der Besitzer gesehen hat (14.07.).
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

/* MAGNET (14.07.: „Andocken heißt magnetische Fenster — nichts bleibt in
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
   bewegt NICHTS anderes (14.07.: „die Ordnung darf sich nicht ändern").
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

/* Größtes freies Rechteck um einen Punkt (14.07.: der herausgezogene Tab
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
      // Dashboard-Muster („im Dashboard viel besser"): nichts wackelt live —
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
    // NIE überlappen (der Besitzer): kollidiert der neue Kasten, bleibt die letzte gültige Größe
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
      // Über einem anderen Fenster? Dann wird der Tab DORT angedockt (14.07.)
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
  // restliche Layout bleibt identisch (14.07.).
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
   und Playlist frei kombinieren oder getrennt anordnen (13.07.). */
function plqFenster(){
  // Der Besitzer 04.08.: im Mini-Modus ist die Playlist FEST ein eigenes Fenster —
  // Eingliedern schöbe sie in die ausgeblendete Seitenliste (weg wäre sie).
  // Riegel zusätzlich zum versteckten Knopf, falls ein anderer Weg ruft.
  if(miniAn){toast('Im Mini-Modus bleibt die Playlist ein eigenes Fenster.');return;}
  // Abspalten OHNE dass sich irgendetwas bewegt (14.07.): die Playlist
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

