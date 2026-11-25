/* ================= Playlists ================= */
let plState=[];
async function plLaden(){try{const r=await fetch('/api/playlists'); const d=await r.json(); plState=d.items||[]; plMalen();}catch(e){}}
function plMalen(){
  const sel=document.getElementById('plsel'); if(!sel)return;
  const cur=sel.value;
  // Build 118 (der Besitzer): „Neue Playlist" steht als erster Eintrag IM Feld — dafür
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
function plWahl(){                                    // Playlist WÄHLEN = sofort öffnen (14.07.)
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
  // Build 121 („wenn ich keine Playlist angewählt habe, wieso werden diese
  // Knöpfe angezeigt?"): ohne gewählte Playlist gibt es nichts zu tun ⇒ die
  // Knöpfe sind gar nicht erst da. Abspielen lebt oben in der Steuerzentrale.
  const sel0=document.getElementById('plsel');
  const gewaehlt=!!((sel0&&sel0.value&&sel0.value!=='__neu')||libPlaylistView);
  const werk=document.getElementById('plwerkbtn');
  if(werk)werk.style.display=gewaehlt?'':'none';
  if(btn)btn.style.display=gewaehlt?'':'none';
  // Build 118 (der Besitzer): geöffnete Playlist ⇒ Zurück-Pfeil, sonst das Listen-Symbol.
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
/* Entf in der Playlist-Ansicht (07.08.): nimmt die MARKIERTEN Titel aus
   der Liste — Dateien bleiben (nicht-destruktiv). Ein Rückgängig gibt es
   über das ＋-Menü; darum kein Nachfrage-Dialog bei wenigen, aber eine
   Sicherheitsfrage ab 5 Titeln. */
async function plAuswahlEntfernen(){
  if(!libPlaylistView||!libAuswahl.size)return;
  const keys=[...libAuswahl], plid=libPlaylistView;    // Liste festhalten: die Ansicht kann während der Rückfrage wechseln
  const p=plState.find(x=>x.id===plid);
  const raus=async()=>{
    for(const k of keys)await plApi({art:'remove',id:plid,key:k});
    libAuswahl.clear(); libMalen();
    plInfo(keys.length+(keys.length===1?' Titel':' Titel')+' aus der Playlist entfernt (Dateien bleiben)');
  };
  // App-eigene Rückfrage statt confirm(): der native Dialog hält in Firefox die Musik an (s. libLoeschen).
  if(keys.length>=5)frageModal(keys.length+' Titel aus „'+((p&&p.name)||'')+
     '" entfernen? Die Dateien bleiben auf der Platte.','✖ Entfernen',raus);
  else await raus();
}
async function plApi(body){await api('/api/playlist',body); await plLaden();}
/* Neue Playlist anlegen -> ihre id ('' bei einem Fehler). Der Server nennt
   die id selbst (F17); vorher wurde „die zuletzt gelistete“ geraten, und bei
   einem Fehler oder einer gleichzeitig angelegten Abo-Playlist landeten die
   Titel in der falschen Liste. */
async function plAnlegen(name){
  let id='';
  try{
    id=(await api('/api/playlist',{art:'create',name})).id||'';
  }catch(e){}
  await plLaden();
  return id;
}

/* ---- Titel auf eine Playlist ziehen (Build 135, der Besitzer Punkt 4) --------------
   Bisher ging Einreihen nur über das ＋-Menü an jeder Kachel — bei mehreren
   Titeln also viele Klicks. Jetzt zieht man die Auswahl auf die
   Playlist-Liste. Steht dort „— keine —", entsteht eine neue Playlist: genau
   Besitzer-Wunsch, denn beim Ziehen weiß man oft erst im Moment des Loslassens,
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
    id=await plAnlegen(n.trim()); neu=true;
    if(!id){toast('Playlist ließ sich nicht anlegen.');return;}
  }
  const p=plState.find(x=>x.id===id);
  // Build 138 (der Besitzer): Doppelte Titel sind erlaubt — „Ist ja meine Entscheidung."
  // Es wird also NICHT mehr gefiltert. Fürs Rückgängig merken wir uns den
  // Stand VOR dem Wurf und stellen ihn exakt wieder her; ein „remove" je
  // Titel träfe alle Vorkommen, nicht nur die gerade hinzugefügten.
  const vorher=((p&&p.items)||[]).slice();
  for(const k of keys)await plApi({art:'add',id,key:k});
  plLetzterWurf={id,vorher,plNeu:neu};
  const name=(plState.find(x=>x.id===id)||{}).name||'Playlist';
  const schon=keys.filter(k=>vorher.includes(k)).length;
  toastMitZurueck((neu?'📃 „'+name+'" angelegt · ':'')+keys.length+' Titel → „'+name+'"'+
    (schon?' ('+schon+' schon drin — jetzt doppelt)':''), plZurueck);
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
  t.innerHTML=esc(text)+' <button class="btn mini" style="margin-left:10px">↩ Rückgängig</button>';
  t.lastChild.onclick=()=>{ruf(); document.getElementById('toast').classList.remove('an');};
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
    const id=await plAnlegen(n.trim()); if(id)rein(id);}]);
  return opt;
}
async function plCreate(){const n=prompt('Name der neuen Playlist:'); if(n&&n.trim()){const id=await plAnlegen(n.trim());
  if(id){document.getElementById('plsel').value=id; plMalen();}}}
async function plDelete(){const id=document.getElementById('plsel').value; if(!id)return;
  const p=plState.find(x=>x.id===id); if(p&&confirm('Playlist „'+p.name+'" löschen? (Dateien bleiben erhalten)'))await plApi({art:'delete',id});}
async function plRename(){const id=document.getElementById('plsel').value; if(!id)return;
  const p=plState.find(x=>x.id===id); const n=prompt('Neuer Name:',p?p.name:''); if(n&&n.trim())await plApi({art:'rename',id,name:n.trim()});}
function plPlaySel(){const id=document.getElementById('plsel').value; const p=plState.find(x=>x.id===id);
  if(!id||!p){
    // KEINE Playlist gewählt (14.07.): dann die aktuell ANGEZEIGTE Bibliothek
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
  const name=prompt('Name der importierten Playlist:', f.name.replace(/\.(m3u8?)$/i,''))||f.name;
  // Der Server nimmt höchstens 2 MB an (MAX_KOERPER, S14) und schließt danach
  // die Verbindung: darum vorher selbst messen und ehrlich „zu groß“ melden,
  // statt „Import ✓ — 0 Titel“ (Gesamtprüfung Gruppe 6).
  const body=JSON.stringify({name,m3u:text});
  if(new Blob([body]).size>2*1024*1024){plInfo('Import abgebrochen: die Datei ist zu groß (höchstens 2 MB).');return;}
  try{
    const r=await api('/api/playlist_import',body,{roh:true});
    const d=await r.json().catch(()=>({}));
    if(!r.ok){
      plInfo('Import fehlgeschlagen: '+(r.status===413?'die Datei ist zu groß (höchstens 2 MB).'
                                                     :(d.fehler||('Antwort '+r.status))));
      return;
    }
    await plLaden();
    if(d.id){document.getElementById('plsel').value=d.id; plMalen();}
    plInfo('Import ✓ — '+(d.gefunden||0)+' Titel gefunden');
  }catch(e){plInfo('Import fehlgeschlagen');}
}

/* ---- Namens-Baukasten (Build 113, Vorgabe: „die Art der Beschreibung wählen …
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
    '<span class="spacer"></span><button class="ib" onclick="document.getElementById(\'name-fly\').remove()" title="Schließen (Esc)">✕</button></div>'+
    '<div id="name-liste" style="margin:8px 4px"></div>'+
    '<div style="margin:8px 4px;padding:8px;border:1px solid #2c2621;border-radius:8px;background:#141110">'+
      '<div style="font-size:11px;color:var(--gedaempft);margin-bottom:3px">So heißen die Dateien dann:</div>'+
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
    '<input type="checkbox" '+(an?'checked':'')+' data-id="'+esc(b[0])+'" onchange="nameBausteinToggle(this.dataset.id,this.checked)">'+
    '<span style="flex:1">'+esc(b[1])+' <span style="color:var(--gedaempft)">'+esc(b[2])+'</span></span>'+
    (an?'<button class="ib" data-id="'+esc(b[0])+'" onclick="nameSchieben(this.dataset.id,-1)" title="nach vorn">▲</button>'+
        '<button class="ib" data-id="'+esc(b[0])+'" onclick="nameSchieben(this.dataset.id,1)" title="nach hinten">▼</button>':'')+
    '</div>';
  box.innerHTML=(drin.length?'<div style="font-size:11px;color:var(--gedaempft)">Reihenfolge — ziehen oder ▲▼:</div>':'')+
    drin.map((b,i)=>zeile(b,true,i)).join('')+
    (raus.length?'<div style="font-size:11px;color:var(--gedaempft);margin-top:6px">Nicht im Namen:</div>':'')+
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
  try{await api('/api/config',{name_schema:nameSchema});}catch(e){}
}
async function nameAutoSetzen(an){
  try{await api('/api/config',{auto_umbenennen:!!an});
    toast(an?'Importe werden künftig automatisch benannt.':'Auto-Benennen aus.');}catch(e){}
}
async function nameProbelauf(){
  const stand=document.getElementById('name-stand'); if(stand)stand.textContent='prüfe …';
  try{
    const r=await fetch('/api/migration_probelauf?schema='+encodeURIComponent(nameSchema.join(',')));
    const d=await r.json(); namePlan=d;
    const box=document.getElementById('name-plan');
    box.innerHTML=d.eintraege.length?('<table style="width:100%;border-collapse:collapse">'+
      d.eintraege.map(x=>'<tr><td style="padding:2px 4px;color:'+(x.konflikt?'#e0a030':'var(--gedaempft)')+'">'+
        (x.konflikt?'⚠':'✅')+'</td><td style="padding:2px 4px;color:var(--gedaempft)">'+esc(x.alt.split(/[\\/]/).pop())+'</td>'+
        '<td style="padding:2px 4px">→ '+esc(x.neu.split(/[\\/]/).pop())+'</td></tr>'+
        (x.konflikt?'<tr><td></td><td colspan="2" style="padding:0 4px 4px;color:#e0a030;font-size:11px">'+esc(x.konflikt)+'</td></tr>':'')).join('')+
      '</table>'):'<div style="color:var(--gedaempft);padding:6px">Alle Dateien heißen schon so — nichts zu tun.</div>';
    if(stand)stand.textContent=d.bereit+' bereit, '+d.konflikte+' übersprungen'+(d.gesamt>d.eintraege.length?' (Liste zeigt die ersten '+d.eintraege.length+')':'');
    const go=document.getElementById('name-go'); if(go)go.disabled=!d.bereit;
  }catch(e){if(stand)stand.textContent='Probelauf fehlgeschlagen.';}
}
async function nameAnwenden(){
  if(!namePlan||!namePlan.bereit)return;
  if(!confirm('Jetzt '+namePlan.bereit+' Datei(en) umbenennen?\n\nDie Untertitel wandern mit, der alte Name wird IN der Datei vermerkt, und „↩ Rückgängig" macht alles zurück.'))return;
  const stand=document.getElementById('name-stand'); if(stand)stand.textContent='benenne um …';
  try{
    const d=await api('/api/umbenennen',{go:true,schema:nameSchema});
    toast('✔ '+d.umbenannt+' umbenannt'+(d.uebersprungen?', '+d.uebersprungen+' übersprungen':''));
    await nameProbelauf(); laden();
  }catch(e){if(stand)stand.textContent='Umbenennen fehlgeschlagen.';}
}
async function nameUndo(){
  if(!confirm('Den letzten Umbenenn-Lauf zurücknehmen?'))return;
  try{
    const d=await api('/api/umbenennen',{art:'undo'});
    toast(d.ok?('↩ '+d.zurueck+' Datei(en) zurückbenannt'+(d.blockiert?', '+d.blockiert+' blockiert':'')):(d.fehler||'nichts zurückzunehmen'));
    await nameProbelauf(); laden();
  }catch(e){toast('Rückgängig fehlgeschlagen.');}
}
async function plSyncConfig(){
  // Build 108 (der Besitzer): eigenes kleines Fenster statt prompt — Pfad vom letzten
  // Mal vorbelegt und 📁 öffnet den NATIVEN Windows-Ordnerdialog (über den
  // lokalen Server; der Browser darf selbst keine Pfade wählen).
  // Build 109 (Failsafe): existiert der vorbelegte Pfad gerade NICHT
  // (Platte ab, Stick raus), werden Feld + Speicher-Knöpfe nur ausgegraut —
  // ein 2-s-Puls gibt alles von selbst frei, sobald der Ordner wieder da ist.
  // Tippen ändert den Merker NICHT (gemerkt wird erst beim Speichern):
  // Abbrechen + neu öffnen bringt die Vorbelegung zurück.
  const id=document.getElementById('plsel').value;
  if(!id){alert('Bitte zuerst eine Playlist wählen.');return;}
  const p=plState.find(x=>x.id===id);
  let letzter=lsLesen('ytdl_sync_letzter')||'';
  const alt=document.getElementById('sync-fly'); if(alt)alt.remove();
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='sync-fly'; fly.tabIndex=-1; fly.style.height='auto';
  fly.innerHTML='<div class="abo-fly-titel">⇄ Sync einrichten: '+esc(p.name||'')+
    '<span class="spacer"></span><button class="ib" onclick="document.getElementById(\'sync-fly\').remove()" title="Schließen (Esc)">✕</button></div>'+
    '<div style="display:flex;gap:6px;margin:8px 4px 4px">'+
      '<input type="text" id="sync-pfad" style="flex:1" placeholder="z. B. E:\\Musik — USB-Stick oder Handy-Ordner" value="'+esc(p.sync_ordner||letzter)+'">'+
      '<button class="btn mini" onclick="syncOrdnerWaehlen(this)" title="Nativen Windows-Ordnerdialog öffnen (erscheint auf deinem Bildschirm)">📁 wählen</button></div>'+
    '<div id="sync-tot" style="display:none;margin:6px 4px 0;color:#e0a030;font-size:.85em">⏳ Ordner gerade nicht erreichbar — Platte/Stick anschließen, das Fenster merkt es von selbst.</div>'+
    // Der Besitzer 07.08.: „es sollte auch eine option für automatisch synchronisieren
    // existieren" — hängt sich in den bestehenden 5-s-Ticker (Last-Budget:
    // kein neuer Zeitplan) und läuft nur, wenn der Zielordner erreichbar ist.
    '<label style="display:flex;gap:8px;align-items:center;margin:8px 4px 0;font-size:.9em">'+
      '<input type="checkbox" id="sync-auto"'+(p.sync_auto?' checked':'')+'>'+
      'Automatisch synchronisieren — sobald sich die Playlist ändert und der Ordner da ist</label>'+
    '<div class="abo-staffel" style="margin-top:8px"><span style="opacity:.7">Spiegeln löscht im Ziel nur Dateien, die die App selbst kopiert hat.</span><span class="spacer"></span>'+
      '<button class="btn mini" data-id="'+esc(id)+'" onclick="syncSpeichern(this.dataset.id,false)" title="Nur kopieren — es wird nie etwas gelöscht">Nur kopieren</button>'+
      '<button class="btn mini" data-id="'+esc(id)+'" onclick="syncSpeichern(this.dataset.id,true)" title="Exakt spiegeln — Entferntes verschwindet auch im Ziel (nur App-eigene Kopien)">Exakt spiegeln</button></div>';
  document.body.appendChild(fly); nachVorn(fly);
  aboFlyoutPositionieren(fly,null);
  fly.style.height='auto';                             // wächst mit dem Inhalt …
  imBlick(fly);                                        // … aber NIE aus dem Bild (Build 114)
  fly.addEventListener('keydown',e=>{if(e.key==='Escape'){fly.remove(); e.stopPropagation();}});
  fly.focus();
  syncPfadWachen(fly);
}
function syncPfadWachen(fly){
  // Build 109 (Failsafe): Feld + Speicher-Knöpfe an der Wirklichkeit
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
  const auto=!!(document.getElementById('sync-auto')||{}).checked;
  /* Der Besitzer 25.09.: Ziel in der Bibliothek oder als Netzwerkpfad lehnt der Server ab;
     dann bleibt der Dialog offen, und der Ordner wird nicht als letzter gemerkt. */
  let d={};
  try{
    const r=await api('/api/playlist',{art:'sync_config',id,sync_ordner:ordner,
                           sync_modus:spiegeln?'spiegeln':'kopieren',sync_auto:auto},{roh:true});
    d=await r.json().catch(()=>({}));
    if(!r.ok&&!d.fehler)d={fehler:'Speichern abgelehnt ('+r.status+').'};
  }catch(e){d={fehler:'Server nicht erreichbar.'};}
  if(d.fehler){toast('⇄ Sync: '+d.fehler);return;}
  if(ordner)lsSchreiben('ytdl_sync_letzter',ordner);
  await plLaden();
  const f=document.getElementById('sync-fly'); if(f)f.remove();
  if(ordner){toast('⇄ Sync: '+(spiegeln?'spiegeln':'kopieren')+(auto?', automatisch':'')+' → '+ordner);
    plSyncNow(id);}
}
async function plSyncNow(id){
  id=(typeof id==='string')?id:document.getElementById('plsel').value;
  if(!id){alert('Bitte zuerst eine Playlist wählen.');return;}
  const p=plState.find(x=>x.id===id);
  if(!p||!p.sync_ordner){alert('Für diese Playlist ist noch kein Sync-Ordner eingerichtet („⇄ Sync…“).');return;}
  plInfo('synchronisiere …', true);                    // Fortschritt: bleibt
  const info=document.getElementById('plinfo');      // 06.09.: war undeklariert (ReferenceError)
  try{
    const d=await api('/api/playlist',{art:'sync',id});
    if(d.fehler)info.textContent='Sync-Fehler: '+d.fehler;
    else info.textContent=`Sync ✓ ${d.kopiert} kopiert`+(d.geloescht?`, ${d.geloescht} gelöscht`:'')+`, ${d.im_ziel} im Ordner`;
  }catch(e){info.textContent='Sync fehlgeschlagen (App erreichbar?)';}
  plLaden();
}

async function biblio(id,art){
  await api('/api/biblio',{id,art});
  libLaden();
}
async function biblioNeuladen(id){
  await api('/api/biblio',{id,art:'neuladen'});
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
/* Tastenkürzel (21.07., YouTube-/Player-Standard). Greifen NUR, wenn nicht in
   einem Eingabefeld getippt wird. ? zeigt die Legende. */
function tastenLegende(){
  /* Build 139 („Legende sollte etwas mehr Zeilenumbrueche haben"): Der
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
    ['Playlist',  'Klick wählt · Doppelklick/Enter spielt · Entf löscht · ↑/↓ Auswahl'],
    ['Bibliothek','Strg/Umschalt+Klick markiert · Strg+A alles'+(NUR_FERN?'':' · Entf legt Markiertes in den Papierkorb')]];
  toastHTML('<div style="font-size:11px;color:var(--gedaempft);margin-bottom:5px">Tastenkürzel</div>'+
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
/* ---- Hotkey-Editor (Wunsch, Marschbefehl 05.08.) ----------------------
   Die Player-Tasten sind eine TABELLE statt hart verdrahteter switch-Fälle:
   HK_DEF = Auslieferung, localStorage 'ytdl_hotkeys' = eigene Belegung.
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

function hkSpeichern(){lsSchreiben('ytdl_hotkeys',JSON.stringify(HK));}
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
    +'<button class="btn mini" data-a="'+a+'" onclick="hkFangen(this.dataset.a,this)">ändern</button>'
    +'<button class="ib" title="Standard wiederherstellen" data-a="'+a+'" onclick="hkZuruecksetzen(this.dataset.a)">↺</button></span></div>').join('');
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML='<div class="modal-box" style="max-width:470px"><div class="modal-head"><b>⌨ Hotkeys — Player-Tasten belegen</b>'
    +'<button class="ib" title="Schließen" onclick="this.closest(\'.modal\').remove()">✕</button></div>'
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
  // In der Fertig-Liste (22.07.): fokussierte Zeile mit Enter abspielen,
  // mit Entf den Eintrag entfernen (Datei bleibt). Fokus kommt per Klick (tabindex).
  if(tgt&&tgt.dataset&&tgt.dataset.fid&&tgt.closest&&tgt.closest('#view-done')){
    if(e.key==='Enter'){e.preventDefault(); fertigPlay(tgt.dataset.fid); return;}
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault(); aktion(tgt.dataset.fid,'entfernen'); return;}
  }
  // In der Player-Playlist steuern die Tasten die LISTE (22.07.): Pfeile bewegen die
  // Auswahl, Enter spielt, Entf löscht. Nur wenn der Fokus wirklich in der Liste sitzt —
  // sonst gelten ↑/↓ weiter global als Lautstärke.
  if(tgt&&tgt.closest&&tgt.closest('.pl-queue')){
    if(e.key==='ArrowDown'){e.preventDefault(); plqMoveSel(1); return;}
    if(e.key==='ArrowUp'){e.preventDefault(); plqMoveSel(-1); return;}
    if(e.key==='Enter'){e.preventDefault(); if(plqSel!==null)plQueueKlick(plqSel); return;}
    if(e.key==='Delete'||e.key==='Backspace'){e.preventDefault(); plqAuswahlLoeschen(); return;}
  }
  // Playlist-ANSICHT der Bibliothek (07.08.: „möchte mit delete lieder aus
  // einer playlist löschen"): Entf nimmt die markierten Titel AUS DER LISTE —
  // die Dateien bleiben (nicht-destruktiv, harte Regel). Greift nur, wenn
  // eine Playlist-Ansicht offen ist und wirklich etwas markiert war.
  if((e.key==='Delete'||e.key==='Backspace')&&libPlaylistView&&libAuswahl.size){
    const lib=document.getElementById('view-lib');
    if(lib&&lib.offsetParent){e.preventDefault(); plAuswahlEntfernen(); return;}
  }
  // Übrige Bibliothek (Rückmeldung 19.10.: „Entf. ging auch nicht"): Entf legt
  // die markierten Titel in den Papierkorb — nach Rückfrage, nur am PC (wie der
  // Menüpunkt), und nicht, solange ein Fenster offen ist (Rückfrage, Einstellungen).
  // Sichtbarkeit zählt: Legende, Einstellungen und Geo-Assistent stehen als
  // versteckte .modal dauerhaft im Dokument.
  if((e.key==='Delete'||e.key==='Backspace')&&!libPlaylistView&&libAuswahl.size&&!NUR_FERN
     &&![...document.querySelectorAll('.modal')].some(m=>getComputedStyle(m).display!=='none')){
    const lib=document.getElementById('view-lib');
    if(lib&&lib.offsetParent){e.preventDefault(); libLoeschen([...libAuswahl]); return;}
  }
  const el=document.getElementById('pl-el');
  // Build 132: springt UND zeigt es an (der Besitzer). J/L bleiben bei 10 s wie bisher,
  // die Pfeiltasten nehmen die einstellbare Weite (Standard 5 s wie YouTube).
  // Film offen: Sprünge gehören dem Film, nie der unsichtbaren Musik darunter
  // (Prüf-Befund 24.09.: J/L, Ziffern und Pos1 sprangen in der Musik).
  const springen=s=>filmTasten()?tvpRel(s):plbSpringen(s);
  const playPause=()=>{plTogglePlay();};               // VLC-fähig (Gerät zählt, nicht das Element)
  if(e.ctrlKey&&e.key==='ArrowRight'){e.preventDefault();playerNext();return;}
  if(e.ctrlKey&&e.key==='ArrowLeft'){e.preventDefault();playerPrev();return;}
  if(e.ctrlKey||e.metaKey||e.altKey)return;            // keine sonstigen Strg/Cmd/Alt-Kombis kapern
  if(/^(Digit|Numpad)[0-9]$/.test(e.code)){           // 0–9 -> zu 0–90 % springen (YouTube-Standard)
    const anteil=+e.code.slice(-1)/10;
    if(filmTasten()){if(tvpDauer){e.preventDefault(); tvpSpringeAuf(tvpDauer*anteil);} return;}
    if(el&&el.duration){e.preventDefault(); el.currentTime=el.duration*anteil; return;}
  }
  if(_hkFang)return;                                   // der Fang-Dialog hört gerade selbst zu
  // Tabellen-Dispatcher (Hotkey-Editor): HK bestimmt, welche Taste was tut.
  const HK_TUN={
    // Film offen: K/N/P steuern den Film wie die Medientasten — vorher starteten
    // sie die Musik unter dem Film (Befund 23.09.).
    playpause:()=>{if(filmTasten()){tvpBefehl('toggle'); setTimeout(tvpTick,300); return;}
      if(el||vlcAktiv())playPause();},
    rueck10:()=>springen(-10), vor10:()=>springen(10),
    sprungvor:()=>springen(sprungWeite()), sprungzurueck:()=>springen(-sprungWeite()),
    lauter:()=>_vol(5), leiser:()=>_vol(-5),
    naechster:()=>medienWeiter(), voriger:()=>medienZurueck(),
    stumm:()=>{
      if(filmTasten()){const v=document.getElementById('tvp-video');   // Browser-Film: seinen Ton
        if(v){v.muted=!v.muted; toast(v.muted?'🔇 stumm':'🔊 Ton an');} return;}
      if(el){el.muted=!el.muted; toast(el.muted?'🔇 stumm':'🔊 Ton an');}},
    // Film offen: F schaltet das FILM-Vollbild (wie der Knopf der Fernbedienung),
    // I tut nichts — der Film hat kein Bild-in-Bild, die Musik darunter ist
    // unsichtbar (Nebenbefund 24.09.: beide griffen in die Musik).
    vollbild:()=>{if(filmTasten()){tvpVollbild(); return;} plbFullscreen();},
    pip:()=>{if(filmTasten())return; plbPip();},
    untertitel:()=>{if(typeof subCycle==='function')subCycle();},
    anfang:()=>{if(filmTasten()){tvpSpringeAuf(0); return;} if(el)el.currentTime=0;},
    // Musik-Werkzeuge greifen bei offenem Film NICHT in die Musik darunter
    ende:()=>{if(filmTasten())return; if(el&&el.duration)el.currentTime=el.duration;},
    wiederholen:()=>{if(filmTasten())return; if(el){el.loop=!el.loop; toast(el.loop?'🔁 Wiederholen an':'▶ Wiederholen aus');}},
    langsamer:()=>{if(filmTasten())return; if(el)_rate(-0.25);}, schneller:()=>{if(filmTasten())return; if(el)_rate(0.25);},
    subfrueher:()=>subOffsetSchieben(-0.5), subspaeter:()=>subOffsetSchieben(0.5)
  };
  // Der Besitzer 05.08. (Korrektur): Hotkeys gelten ÜBERALL im Browser-Fenster.
  const tu=HK_TUN[hkAktionFuer(hkCode(e))];
  if(tu){e.preventDefault(); tu(); return;}
  // Fest: Medientasten als keydown (manche Browser stellen sie ZUSÄTZLICH zur
  // Media Session zu). Dieselbe Weiche wie die Windows-Knöpfe, und
  // medienEinmal verhindert, dass eine Taste doppelt schaltet.
  switch(e.code){
    // Medientasten: nur Rückfall, wenn Windows sie keiner SyncYouTube-Sitzung gibt
    case 'MediaPlayPause': e.preventDefault(); if(medienTasteHatSitzung())break;
      if(medienEinmal('pp','taste')){if(filmTasten()){tvpBefehl('toggle'); setTimeout(tvpTick,300);} else playPause();}
      break;
    case 'MediaTrackNext': e.preventDefault(); if(!medienTasteHatSitzung()&&medienEinmal('next','taste'))medienWeiter(); break;
    case 'MediaTrackPrevious': e.preventDefault(); if(!medienTasteHatSitzung()&&medienEinmal('prev','taste'))medienZurueck(); break;
    default:
      if(e.key==='?'){e.preventDefault(); tastenLegende();}
  }});

