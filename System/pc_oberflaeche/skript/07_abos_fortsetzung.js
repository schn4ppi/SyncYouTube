/* ================= Abos, Fortsetzung ================= */
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
  const qsel=`<select class="abo-qsel" title="Download-Format dieses Abos (gilt ab der nächsten Prüfung; Bisheriges unter ⚙ erneuerbar)" data-abo="${esc(a.id)}" onchange="aboQualitaet(this.dataset.abo,this.value)">`+
    Object.keys(ABO_Q).map(q=>`<option value="${q}" ${q===a.qualitaet?'selected':''}>${ABO_Q[q]}</option>`).join('')+'</select>';
  return `<div class="abo-card" data-abo="${esc(a.id)}">
    <div class="abo-kopf">
      <span class="abo-name" title="${esc(a.url)}">📡 ${esc(a.name||a.url)}</span>
      ${qsel}
      <span class="abo-meta">${a.neu?('+'+a.neu+' geholt · '):''}${a.geprueft?('geprüft '+aboVor(a.geprueft)):''}</span>
      <button class="ib" title="Abo-Playlist im Player abspielen" data-abo="${esc(a.id)}" onclick="aboAbspielen(this.dataset.abo)">▶</button>
      <button class="ib ${o.auf?'an':''}" title="Backkatalog: alle Folgen des Kanals als eigenes Fenster — Ausgegrautes ist noch nicht geladen" data-abo="${esc(a.id)}" onclick="aboFolgenToggle(this.dataset.abo,event)">📜</button>
      <button class="ib ${o.regeln?'an':''}" title="Regeln: Titel-Filter, Stichtag, Shorts/Streams, Auto-Löschen, Format-Erneuern" data-abo="${esc(a.id)}" onclick="aboRegelnToggle(this.dataset.abo)">⚙</button>
      <button class="ib" title="Abo entfernen — mit oder ohne die geladenen Videos" data-abo="${esc(a.id)}" onclick="aboDelete(this.dataset.abo,event)">🗑</button>
    </div>
    ${o.regeln?aboRegelnHTML(a):''}
  </div>`;
}
function aboRegelnHTML(a){
  return `<div class="abo-regeln">
    <label title="Nur Videos laden, deren Titel diesen Text enthält (leer = alle)">Titel enthält
      <input type="text" value="${esc(a.filter_titel||'')}" data-abo="${esc(a.id)}" onchange="aboRegel(this.dataset.abo,'filter_titel',this.value)"></label>
    <label title="Nur Videos ab diesem Datum laden (leer = alle)">ab
      <input type="date" value="${esc(a.ab_datum||'')}" data-abo="${esc(a.id)}" onchange="aboRegel(this.dataset.abo,'ab_datum',this.value)"></label>
    <label title="Kurzvideos (≤ 62 s) überspringen"><input type="checkbox" ${a.ohne_shorts?'checked':''}
      data-abo="${esc(a.id)}" onchange="aboRegel(this.dataset.abo,'ohne_shorts',this.checked)"> keine Shorts</label>
    <label title="Livestreams und Premieren überspringen"><input type="checkbox" ${a.ohne_streams?'checked':''}
      data-abo="${esc(a.id)}" onchange="aboRegel(this.dataset.abo,'ohne_streams',this.checked)"> keine Streams</label>
    <label title="Folgen der Abo-Playlist nach X Tagen automatisch in den Papierkorb (0 = aus)">löschen nach
      <input type="number" min="0" max="3650" style="width:58px" value="${a.loeschen_nach_tagen||0}"
        data-abo="${esc(a.id)}" onchange="aboRegel(this.dataset.abo,'loeschen_nach_tagen',parseInt(this.value,10)||0)"> Tagen</label>
    <span class="spacer"></span>
    <button class="btn mini" data-abo="${esc(a.id)}" onclick="aboErneuern(this.dataset.abo,false)"
      title="Alles bereits Geladene zusätzlich im aktuellen Abo-Format holen — alte Dateien bleiben">🔁 Erneuern (behalten)</button>
    <button class="btn mini" data-abo="${esc(a.id)}" onclick="aboErneuern(this.dataset.abo,true)"
      title="…und die alte Datei im anderen Format NACH dem Erfolg in den Papierkorb legen">🔁 Erneuern (ersetzen)</button>
  </div>`;
}
async function aboRegel(id,feld,wert){const d={art:'aendern',id}; d[feld]=wert; await aboPost(d); aboLaden();}
async function aboQualitaet(id,q){await aboPost({art:'aendern',id,qualitaet:q}); aboLaden();}
function aboRegelnToggle(id){const o=aboOffen[id]=aboOffen[id]||{zeige:300,sel:new Set()}; o.regeln=!o.regeln; aboMalen();}
/* ---- Backkatalog-Flyout (Build 93, der Besitzer): grosses Fenster am 📜-Knopf, nie aus
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
  // Der Besitzer (Build 94): rechtsbuendig UNTER dem eingebetteten Downloads-Fenster
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
    return `<div class="abo-f ${x.geladen?'':'fehlt'} ${o.sel.has(x.id)?'sel':''}" data-abo="${esc(id)}" data-vid="${esc(x.id)}"
      onclick="aboFolgeKlick(event,this.dataset.abo,this.dataset.vid)" ondblclick="aboFolgenHolen(this.dataset.abo,[this.dataset.vid])"
      oncontextmenu="return aboFolgeKontext(event,this.dataset.abo,this.dataset.vid)"
      title="Folge ${x.nr} von ${alle.length}${x.geladen?' — geladen, Doppelklick lädt ggf. im Abo-Format nach':' — noch nicht geladen, Doppelklick lädt im Abo-Format'}">
      <span class="abo-nr" title="Folge ${x.nr} (älteste = 1, neueste = ${alle.length})">#${x.nr}</span>
      <span class="abo-ft">${esc(x.titel)}</span>${x.dauer?'<span class="abo-fd">'+zeit(x.dauer)+'</span>':''}${badge}</div>`;
  }).join('');
  const fehltSicht=liste.filter(x=>!x.geladen).length;
  const staffel=[10,25,50,100].map(n=>
    `<button class="btn mini" data-abo="${esc(id)}" data-n="${n}" onclick="aboFehlendeLaden(this.dataset.abo,+this.dataset.n)" ${fehltSicht?'':'disabled'}
       title="Die ${o.richtung==='neu'?'neuesten':'ältesten'} ${n} noch fehlenden Folgen der aktuellen Sicht laden">${n}</button>`).join('');
  box.innerHTML=`<div class="abo-fkopf">
      <input type="text" placeholder="Folgen durchsuchen…" value="${esc(o.filter||'')}"
        data-abo="${esc(id)}" oninput="const a=this.dataset.abo;aboOffen[a].filter=this.value;aboOffen[a].zeige=300;aboFolgenMalen(a)">
      <select data-abo="${esc(id)}" onchange="aboOffen[this.dataset.abo].nur=this.value;aboFolgenMalen(this.dataset.abo)" title="Anzeige filtern">
        <option value="">alle (${alle.length})</option>
        <option value="fehlt" ${o.nur==='fehlt'?'selected':''}>fehlende (${fehlen})</option>
        <option value="da" ${o.nur==='da'?'selected':''}>geladene (${alle.length-fehlen})</option></select>
      <button class="btn mini" data-abo="${esc(id)}" onclick="aboAuswahlLaden(this.dataset.abo)" ${o.sel.size?'':'disabled'}
        title="Markierte Folgen im Abo-Format in die Warteschlange (Klick = diese, Strg+Klick = dazu/weg, Shift = Bereich, Strg+A = alle, Rahmen aufziehen = viele)">⬇ Auswahl (${o.sel.size})</button>
      <button class="ib" title="Folgen-Liste frisch vom Kanal holen${o.ts?' (Stand '+aboVor(o.ts)+')':''}" data-abo="${esc(id)}" onclick="aboFolgenLaden(this.dataset.abo,true)">🔄</button>
    </div>
    <div class="abo-staffel">⬇ Fehlende laden: ${staffel}
      <button class="btn mini" data-abo="${esc(id)}" onclick="aboAlleFehlenden(this.dataset.abo)" ${fehltSicht?'':'disabled'}
        title="ALLE noch fehlenden Folgen der aktuellen Sicht laden">Alle (${fehltSicht})</button>
      <button class="btn mini" data-abo="${esc(id)}" onclick="const o=aboOffen[this.dataset.abo];o.richtung=o.richtung==='neu'?'alt':'neu';aboFolgenMalen(this.dataset.abo)"
        title="Reihenfolge der Mengen-Knöpfe umschalten">${o.richtung==='neu'?'⏭ neueste zuerst':'⏮ älteste zuerst'}</button>
    </div>
    <div class="abo-fliste" data-abo="${esc(id)}" onpointerdown="aboBandStart(event,this.dataset.abo)">${zeilen||'<div class="leer">nichts gefunden</div>'}</div>
    ${liste.length>o.zeige?`<button class="btn mini" style="margin-top:4px" data-abo="${esc(id)}" onclick="aboOffen[this.dataset.abo].zeige+=600;aboFolgenMalen(this.dataset.abo)">… mehr anzeigen (${liste.length-o.zeige} weitere)</button>`:''}
    ${o.sel.size?`<div class="abo-selbar">🎯 <b>${o.sel.size}</b> markiert
      <span class="spacer"></span>
      <button class="btn mini" data-abo="${esc(id)}" onclick="aboAuswahlLaden(this.dataset.abo)" title="Die markierten Folgen im Abo-Format in die Warteschlange">⬇ ${o.sel.size} laden</button>
      <button class="btn mini" data-abo="${esc(id)}" onclick="aboOffen[this.dataset.abo].sel.clear();aboFolgenMalen(this.dataset.abo)" title="Auswahl aufheben (Esc)">✕</button></div>`:''}`;
}
function aboFolgeKlick(ev,id,vid){
  // Windows-Semantik (Build 93, Entscheid): Klick = NUR diese, Strg+Klick =
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
   Fund: die Zeilen sind vollbreit, freie Flaeche gibt es kaum. Erst ab
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
  // Build 95 (der Besitzer): beim Entfernen wahlweise die ueber DIESES Abo geladenen
  // Videos mit in den Papierkorb (nur Abo-Playlist-Inhalte,
  // wiederherstellbar) — manuell Geladenes bleibt immer unberuehrt.
  kontextMenuBauen(ev,[
    ['🗑 Nur das Abo entfernen (Videos bleiben)', async()=>{
      await aboPost({art:'delete',id}); aboLaden();
    }],
    ['🗑 Abo + geladene Videos in den Papierkorb', async()=>{
      if(!confirm('Auch alle über dieses Abo geladenen Videos in den Papierkorb legen? Manuell Geladenes bleibt.\n'+korbRueckweg()))return;
      const d=await aboPost({art:'delete',id,mit_videos:true});
      toast('🗑 '+(d.geloescht||0)+' Datei(en) in den Papierkorb');
      aboLaden(); libLaden();
    }],
  ]);
}
async function aboPruefen(btn){
  const t=btn&&btn.textContent; if(btn){btn.disabled=true; btn.textContent='prüfe…';}
  try{const d=await api('/api/abo',{art:'pruefen'});
    alert(d.neu?(d.neu+' neue(s) Video(s) in die Warteschlange gelegt.'):'Keine neuen Videos.');
  }catch(e){alert('Prüfen fehlgeschlagen.');}
  if(btn){btn.disabled=false; btn.textContent=t;} aboLaden(); laden();
}


