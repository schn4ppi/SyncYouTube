/* ================= Smart-Playlists, Dubletten, Einstellungen speichern ================= */
/* ---- Smart-/Auto-Playlists: Regel-basiert, füllen sich selbst aus der Bibliothek ---- */
let smartListen=[]; try{smartListen=JSON.parse(localStorage.getItem('ytdl_smart'))||[];}catch(e){}
if(!Array.isArray(smartListen))smartListen=[];
function smartSpeichern(){lsSchreiben('ytdl_smart',JSON.stringify(smartListen));}
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
    `<div class="sm-row"><button class="sm-play" data-id="${esc(s.id)}" onclick="smartPlay(this.dataset.id)" title="Abspielen">▶ ${esc(s.name)}</button>`+
    `<span class="sm-cnt">${smartBerechnen(s.rules).length}</span>`+
    `<button class="ib" data-id="${esc(s.id)}" onclick="smartLoeschen(this.dataset.id)" title="Löschen">🗑</button></div>`).join(''):
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
function dubNorm(t){return (t||'').toLowerCase().replace(/\[[^\]]*\]|\([^)]*\)/g,'')
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
      `<button class="ib" title="In den Papierkorb" data-key="${esc(x.id)}" onclick="dubDelete(this.dataset.key)">🗑</button></div>`).join('')+`</div>`).join('');
}
function dublettenPopover(ev){
  const alt=document.getElementById('dubpop'); if(alt){alt.remove(); return;}     // zweiter Klick = zu
  const m=document.createElement('div'); m.className='panelmenu'; m.id='dubpop';
  m.style.minWidth='340px'; m.style.maxHeight='70vh'; m.style.overflowY='auto';
  m.innerHTML=dubBody(); document.body.appendChild(m);
  const r=ev.currentTarget.getBoundingClientRect();
  popoverBei(m,r);
  setTimeout(()=>document.addEventListener('pointerdown',function zu(e2){const p=document.getElementById('dubpop');
    // Klicks in die Lösch-Rückfrage (.modal) schließen das Fenster nicht: danach malt dubDelete es neu.
    if(p&&!p.contains(e2.target)&&!(e2.target.closest&&e2.target.closest('[onclick*="dublettenPopover"],.modal'))){
      p.remove(); document.removeEventListener('pointerdown',zu);}},true),0);
}
function dubDelete(id){
  // App-eigene Rückfrage statt confirm(): der native Dialog hält in Firefox die Musik an (s. libLoeschen).
  const x=libFind(id)||{titel:''};
  frageModal('„'+(x.titel||'').slice(0,40)+'" ('+x.qualitaet+') in den Papierkorb?','🗑 In den Papierkorb',async()=>{
    await api('/api/biblio',{id,art:'loeschen'});
    await libLaden(); const m=document.getElementById('dubpop'); if(m)m.innerHTML=dubBody();   // in place neu füllen
  });
}
async function configSpeichern(){
  await api('/api/config',{
      ziel_ordner:document.getElementById('cfg_ziel').value,
      unterordner:document.getElementById('cfg_ordner').value==='1',
      metadaten:document.getElementById('cfg_meta').value==='1',
      cookies_browser:document.getElementById('cfg_browser').value,
      abrufweg:document.getElementById('cfg_abrufweg').value,
      parallel:parseInt(document.getElementById('cfg_parallel').value,10),
      geo_vpn:document.getElementById('cfg_geo').value==='1',
      geo_gratis_proxy:document.getElementById('cfg_geoproxyfrei').value==='1',
      geo_proxies:document.getElementById('cfg_geoproxies').value.split('\n').map(s=>s.trim()).filter(Boolean),
      geo_wireguard_ordner:document.getElementById('cfg_geowg').value,
      standard_qualitaet:document.getElementById('cfg_qual').value,
      sponsorblock:document.getElementById('cfg_sponsor').value,
      untertitel:document.getElementById('cfg_subs').value==='1',
      untertitel_sprachen:(()=>{                       // Der Besitzer Punkt 6: Sprachwahl
        const sp=[];
        if(document.getElementById('cfg_sub_de').checked)sp.push('de');
        if(document.getElementById('cfg_sub_en').checked)sp.push('en');
        if(document.getElementById('cfg_sub_orig').checked)sp.push('orig');
        document.getElementById('cfg_sub_extra').value.split(',')
          .map(s=>s.trim()).filter(Boolean).forEach(s=>sp.push(s));
        return sp;
      })(),
      auto_update:document.getElementById('cfg_autoupdate').value==='1'});
  document.getElementById('cfg_meldung').textContent='Gespeichert ✓';
  setTimeout(()=>document.getElementById('cfg_meldung').textContent='',2500);
  laden();
}

