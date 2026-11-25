/* ================= Warteschlange ================= */
const PILLS={wartend:'wartet',prueft:'prüfe…',laeuft:'lädt',pausiert:'pausiert',fertig:'fertig',
  fehler:'Fehler',uebersprungen:'übersprungen'};

let offeneQueue=new Set();
function qToggle(id){ if(offeneQueue.has(id))offeneQueue.delete(id); else offeneQueue.add(id); malen(); }
function balkenAscii(proz,n){ n=n||12; const f=Math.max(0,Math.min(n,Math.round((proz||0)/100*n))); return '█'.repeat(f)+'░'.repeat(n-f); }
function kurzfehler(t){
  t=(t||'').replace(/\s+/g,' ').trim(); const l=t.toLowerCase();
  if(l.includes('available in your country'))return 'geo-gesperrt';
  if(l.includes('private video'))return 'privat';
  if(l.includes('video unavailable'))return 'nicht verfügbar';
  if(l.includes('sign in to confirm your age'))return 'altersbeschränkt';
  if(l.includes('has been removed')||l.includes('no longer available'))return 'entfernt';
  /* Sperren VOR der Cookie-Zeile (Befund 07.09.2026): YouTube haengt an jede
     Bot-Meldung den Satz »Use --cookies-from-browser …« an, das Wort 'cookie'
     steht also DRIN — die Anzeige log den Nutzer deshalb mit 'Cookie-Fehler'
     an, obwohl YouTube uns ausgesperrt hatte. */
  if(l.includes('not a bot')||l.includes('captcha'))return 'YouTube verlangt Anmeldung (Bot-Verdacht)';
  if(l.includes('too many requests')||l.includes('rate-limited')||l.includes('rate limited')||/(^|[^0-9a-z])429([^0-9a-z]|$)/.test(l))return 'zu viele Anfragen — YouTube drosselt';
  if(l.includes('abrufwege abgelehnt'))return 'YouTube hat alle Wege abgelehnt (403)';   // abrufweg.LeiterFehler
  if(l.includes('forbidden')||/(^|[^0-9a-z])403([^0-9a-z]|$)/.test(l))return 'YouTube verweigert den Zugriff (403)';
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
  // Wechsel des Abrufwegs nach einem 403 (abrufweg.abrufen): sichtbar, solange
  // noch nichts fließt — sonst sah er aus wie ein Download, der bei 0 % hängt.
  const wechsel=it.status==='laeuft'&&it.weg_stufe>1;
  if(it.status==='laeuft'){
    if(wechsel&&!it.geladen)rechts='🔀 Weg '+it.weg_stufe+'/'+it.weg_stufen+' · '+(it.weg_titel||'');
    else if(!it.geladen&&it.phase&&(it.phase.startsWith('VPN')||it.phase.startsWith('Geo')))rechts='🌍 '+it.phase.replace(/^Geo: /,'');
    else rechts=`${proz.toFixed(0)}%`+(it.geschw?' '+tempo(it.geschw):'')+(it.eta!=null?' '+zeit(it.eta):'');
  }else if(it.status==='wartend'&&it.naechster_versuch>jetzt)rechts='retry '+Math.max(1,Math.round(it.naechster_versuch-jetzt))+'s';
  else if(it.status==='fehler')rechts=kurzfehler(it.fehler);
  else if(fertigartig)rechts=it.gesamt?mb(it.gesamt):'ok';
  else if(it.status==='wartend')rechts='queued';
  else if(it.status==='prueft')rechts='…';
  // Fertig-Zeilen sind abspielbar (22.07.): Doppelklick spielt, Klick fokussiert
  // (tabindex) -> Enter spielt, Entf entfernt den Eintrag (Datei bleibt).
  const fx=fertigartig?` tabindex="0" data-fid="${esc(it.id)}" ondblclick="fertigPlay(this.dataset.fid)"`:'';
  const tip=fertigartig?'Doppelklick/Enter = abspielen · Entf = Eintrag entfernen (Datei bleibt) · Klick = Details':esc(it.titel);
  const zeile=`<div class="qline ${it.status}" data-qid="${esc(it.id)}"${fx} onclick="qToggle(this.dataset.qid)" title="${tip}">`+
    `<span class="qtri">${auf?'▾':'▸'}</span>`+
    `<span class="qbar">[${balkenAscii(proz)}]</span>`+
    `<span class="qtitel">${esc(it.titel)}</span>`+
    `<span class="qrechts">${esc(rechts)}</span>`+
    // Nach einem 403 der nächste Weg schon in der zugeklappten Zeile: aufgeklappt
    // fand ihn niemand (ein Nutzer, 24.11.2026). Aufgeklappt steht er unten ausgeschrieben.
    (!auf&&it.status==='fehler'&&it.weg_naechster?`<button class="btn mini qweg" data-qid="${esc(it.id)}" title="Anderen Abrufweg versuchen: ${esc(it.weg_naechster_titel||it.weg_naechster)}" onclick="event.stopPropagation();aktion(this.dataset.qid,'anderer_weg')">🔀 Anderer Weg</button>`:'')+
    `</div>`;
  if(!auf)return zeile;
  const k=[];
  if(it.status==='laeuft')k.push(['pause','⏸ Pause']);
  if(it.status==='wartend'){k.push(['pause','⏸ Pause'],['hoch','⏫ Hoch']);
    if(it.naechster_versuch>jetzt)k.push(['sofort','⚡ Sofort']);}
  if(it.status==='pausiert'||it.status==='fehler')k.push(['weiter','▶ Weiter']);
  // 403: genau den nächsten noch nicht versuchten Abrufweg, einmal (abrufweg.py)
  if(it.status==='fehler'&&it.weg_naechster)k.push(['anderer_weg','🔀 Anderen Weg versuchen ('+(it.weg_naechster_titel||it.weg_naechster)+')']);
  // „Trotzdem“ sichert die vorhandene Datei in den Papierkorb und lädt neu
  // (auch aus dem WLAN); „Ordner“ öffnet den Explorer am PC, nur dort.
  if(it.status==='uebersprungen')k.push(['weiter','▶ Trotzdem']);
  if(fertigartig&&!NUR_FERN)k.push(['ordner','📂 Ordner']);
  k.push(['entfernen','✖ Entfernen']);               // geht auch bei Laufenden: bricht ab + nimmt raus
  let knoepfe=k.map(([a,t])=>`<button class="btn mini" data-qid="${esc(it.id)}" data-a="${a}" onclick="event.stopPropagation();aktion(this.dataset.qid,this.dataset.a)">${t}</button>`).join('');
  if(fertigartig)knoepfe=`<button class="btn mini" data-qid="${esc(it.id)}" onclick="event.stopPropagation();fertigPlay(this.dataset.qid)" title="Im Player abspielen">▶ Abspielen</button>`+knoepfe;
  let det='';
  if(it.status==='laeuft')det=`${mb(it.geladen)} / ${mb(it.gesamt)}`+(it.phase?' · '+esc(it.phase):'')+
    (wechsel?` · 🔀 YouTube hat abgelehnt, jetzt Weg ${it.weg_stufe} von ${it.weg_stufen} (${esc(it.weg_titel||'')})`:'');
  else if(it.status==='fehler'){
    det=`<span class="fehltext">${esc(it.fehler||'unbekannter Fehler')}</span>`;
    if(it.weg_naechster)det+=`<div class="qtipp">Tipp: „🔀 Anderen Weg versuchen“ probiert noch ${esc(it.weg_naechster_titel||it.weg_naechster)}. Hilft das nicht, später mit ▶ Weiter erneut versuchen.</div>`;
    else if(/403/.test(kurzfehler(it.fehler)))det+='<div class="qtipp">Alle Abrufwege sind versucht. Später mit ▶ Weiter erneut versuchen; oft hilft auch das nächste App-Update.</div>';
  }
  else if(fertigartig&&it.datei)det=esc(it.datei.split('\\').pop())+
    (it.weg&&it.weg!=='standard'?` · <span title="Nicht der Standardweg: nach einem 403 gewechselt, ein zuletzt erfolgreicher Weg oder die Einstellung „Abrufweg“">🔀 geladen über ${esc(it.weg_titel||it.weg)}</span>`:'');
  else if(it.dauer)det='Länge '+zeit(it.dauer);
  return zeile+`<div class="qdetail"><div class="qdinfo">${esc(it.qualitaet)}`+
    `${it.kategorie?' · '+esc(it.kategorie):''}${det?' · '+det:''}</div>`+
    `<div class="aktionen">${knoepfe}</div></div>`;
}

/* Fertig-Eintrag im Player abspielen (22.07.): aus der Download-URL die
   Video-ID ziehen und den passenden Bibliotheks-Key finden — exakt (id|qualitaet),
   sonst irgendein vorhandenes Format desselben Videos. */
function fertigVid(url){
  const m=(url||'').match(/(?:v=|youtu\.be\/|shorts\/|embed\/)([A-Za-z0-9_-]{6,})/);
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
  // Zähler nicht mehr in den Downloads (21.07.: sieht man an den Reitern) —
  // stattdessen als Übersicht oben im Log.
  const lc=document.getElementById('logchips'); if(lc)lc.innerHTML=
    `<span class="chip"><b>${(daten.db||{}).gesamt||0}</b> insgesamt</span>`+
    `<span class="chip laeuft"><b>${z.laeuft}</b> lädt</span>`+
    `<span class="chip"><b>${z.wartend+z.prueft}</b> wartet</span>`+
    `<span class="chip fertig"><b>${fertig.length-z.uebersprungen}</b> fertig</span>`+
    (z.uebersprungen?`<span class="chip"><b>${z.uebersprungen}</b> übersprungen</span>`:'')+
    (z.fehler?`<span class="chip fehler"><b>${z.fehler}</b> Fehler</span>`:'')+
    (z.pausiert?`<span class="chip"><b>${z.pausiert}</b> pausiert</span>`:'');
  // Pause nach einer erkannten Sperre (youtube_app.youtube_gesperrt): vorher
  // lief sie unsichtbar, und Abos oder Entdecken schienen grundlos still.
  const sh=document.getElementById('sperrhinweis');
  if(sh){
    const rest=daten.sperre_rest||0;
    sh.hidden=!rest;
    if(rest)sh.textContent='⏸ YouTube hat zuletzt abgelehnt oder gebremst (403, 429 oder Bot-Abfrage). Abo-Prüfung, Anreichern und Entdecken '+
      'pausieren noch etwa '+Math.max(1,Math.round(rest/60))+' Min. Was du selbst startest, lädt trotzdem.';
  }
  document.getElementById('liste').innerHTML=
    aktiv.length?aktiv.map(reihe).join(''):'<div class="leer">Keine aktiven Downloads — oben einen Link einfügen und laden.</div>';
  // Fokus in der Fertig-Liste über das Neu-Rendern retten (der Status-Ticker
  // malt alle paar Sekunden — sonst verlöre Entf/Enter seinen Bezug, der Besitzer 22.07.)
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
}

function apiStatus(ok){
  const d=document.getElementById('apidot');
  if(d){
    d.className='apidot'+(ok?'':' bad');
    if(!d.firstChild)d.innerHTML=browserZeichen();      // einmal zeichnen, dann nur umfärben
    d.title=(ok?'API verbunden · 127.0.0.1:8776':'API getrennt — läuft die App?')
            +' · Browser: '+browserName();
  }
  // Build 134: Das Geräte-Symbol hängt am Datenstand, nicht am ⚙-Menü —
  // sonst erschiene es erst, wenn jemand die Einstellungen öffnet.
  try{fernInfoMalen();}catch(e){}
}

/* Gekoppelte Geräte (Entscheid 7a Punkt 1, 25.09.2026): Die volle
   Oberfläche läuft auch auf einem Fernseher oder Handy im WLAN; der Zugang
   reist als HttpOnly-Cookie mit jedem Aufruf (vorher bekam dort jeder Aufruf
   403, Gesamtprüfung F9). /api/status meldet „lokal“. Auf einem Gerät im WLAN
   ist ausgeblendet, was nur am PC geht (Einstellungen, Löschen, Pfade, Tags,
   Clips, Abos, Playlists ändern); der Server sperrt es ohnehin (LAN_ERLAUBT).
   Elemente tragen die Klasse „nur-pc“, Menü-Einträge markiert nurPc(). */
let NUR_FERN=false;
function fernModusSetzen(lokal){
  // Ohne das Feld (ein noch laufender Server von vor dem 25.09. lädt diese
  // Seite schon heiß nach) bleibt alles, wie es ist: die PC-Seite bleibt PC.
  if(lokal!==true&&lokal!==false)return;
  const fern=(lokal===false);
  if(fern===NUR_FERN)return;
  NUR_FERN=fern;
  if(document.body)document.body.classList.toggle('fern',fern);
}
function nurPc(eintrag){eintrag.nurPc=true; return eintrag;}
function menuFuerGeraet(eintraege){return NUR_FERN?(eintraege||[]).filter(e=>!(e&&e.nurPc)):eintraege;}
/* Wiedergabe-Wahlen eines Geräts im WLAN (Abnahme 25.09.2026, offene Frage 3
   an den Besitzer): Qualität, Untertitel-Modus und -Stil, Tempo und Versatz schreibt der
   Server nur vom PC (config.json). Auf dem Gerät wirken sie sofort, gehen
   aber nicht an den Server (vorher 403 und „🔒 Nur am PC“ mitten in der
   Wiedergabe). Untertitel-Modus und -Stil merkt sich der Browser des Geräts
   (ytdl_fern_wahl); sie schlagen dort den globalen Standard des PCs, Regeln je
   Titel und Playlist gelten weiter. „Zurücksetzen“ gibt den Stil wieder dem PC. */
function fernWahl(){try{const w=JSON.parse(localStorage.getItem('ytdl_fern_wahl')||'{}'); return (w&&typeof w==='object')?w:{};}catch(e){return {};}}
function fernWahlMerken(felder){
  const w=Object.assign(fernWahl(),felder);
  lsSchreiben('ytdl_fern_wahl',JSON.stringify(w));
}
/* Was trotzdem abgewiesen wird (403 mit nur_pc), meldet sich EINMAL je Weg,
   statt still nichts zu tun. */
const _nurPcGemeldet=new Set();
function fetchHuelleSetzen(){
  const roh=globalThis.fetch; if(!roh||roh._nurPc)return;
  const huelle=async function(...a){
    const r=await roh.apply(this,a);
    if(r&&r.status===403&&NUR_FERN){
      const weg=String((a[0]&&a[0].url)||a[0]||'').split('?')[0];
      if(!_nurPcGemeldet.has(weg)){
        _nurPcGemeldet.add(weg);
        r.clone().json().then(j=>{if(j&&j.nur_pc)toast('🔒 '+(j.fehler||'Nur am PC möglich.'));
          else _nurPcGemeldet.delete(weg);}).catch(()=>_nurPcGemeldet.delete(weg));
      }
    }
    return r;
  };
  huelle._nurPc=true; globalThis.fetch=huelle;
}
fetchHuelleSetzen();

let cfgInit=false;
function configFuellen(){
  // cfgInit erst nach Erfolg (F9): ein Fehler mitten im Füllen sperrte das
  // Formular bisher für immer, auch nach der nächsten guten Antwort.
  if(cfgInit||!daten||!daten.config)return;
  document.getElementById('cfg_ziel').value=daten.config.ziel_ordner||daten.ziel;
  document.getElementById('cfg_ordner').value=daten.config.unterordner?'1':'0';
  document.getElementById('cfg_meta').value=daten.config.metadaten?'1':'0';
  document.getElementById('cfg_browser').value=daten.config.cookies_browser;
  document.getElementById('cfg_abrufweg').value=daten.config.abrufweg||'auto';
  document.getElementById('cfg_parallel').value=daten.config.parallel;
  document.getElementById('cfg_geo').value=daten.config.geo_vpn?'1':'0';
  document.getElementById('cfg_geoproxyfrei').value=daten.config.geo_gratis_proxy?'1':'0';
  document.getElementById('cfg_geoproxies').value=(daten.config.geo_proxies||[]).join('\n');
  document.getElementById('cfg_geowg').value=daten.config.geo_wireguard_ordner||'';
  document.getElementById('cfg_qual').value=daten.config.standard_qualitaet;
  document.getElementById('cfg_sponsor').value=daten.config.sponsorblock||'';
  document.getElementById('cfg_subs').value=daten.config.untertitel?'1':'0';
  // Der Besitzer Punkt 6: Sprachwahl. Ohne gespeicherte Wahl gilt der Standard de/en/orig.
  const sp=(daten.config.untertitel_sprachen&&daten.config.untertitel_sprachen.length)
    ?daten.config.untertitel_sprachen:['de','en','orig'];
  document.getElementById('cfg_sub_de').checked=sp.includes('de');
  document.getElementById('cfg_sub_en').checked=sp.includes('en');
  document.getElementById('cfg_sub_orig').checked=sp.includes('orig');
  document.getElementById('cfg_sub_extra').value=sp.filter(s=>!['de','en','orig'].includes(s)).join(', ');
  document.getElementById('cfg_autoupdate').value=daten.config.auto_update?'1':'0';
  document.getElementById('qual').value=daten.config.standard_qualitaet;
  const cq=document.getElementById('cmd-qual'); if(cq)cq.value=daten.config.standard_qualitaet;
  cfgInit=true;
}

async function laden(){
  try{
    const r=await fetch('/api/status');
    if(!r.ok)throw new Error('HTTP '+r.status);        // F9: eine Fehlerantwort (etwa 403) wird nie zum Stand
    daten=await r.json();
    fernModusSetzen(daten.lokal);                      // Gerät im WLAN? (7a Punkt 1)
    apiStatus(true); configFuellen(); malen();
    remoteAusfuehren(daten.remote);                    // Befehle vom Handy ausführen
    nachschubMelden(daten.addon_nachschub);            // Addon-Vormerkungen (v1.2.0)
    subStilVomServer();                                // Untertitel-Stil: Server-Stand gewinnt
    uiStandPruefen(daten.ui_stand);                    // alte Tabs erneuern sich selbst
  }catch(e){apiStatus(false);}
}
/* Selbst-Erneuerung (Wurzel-Fix 07.08.: der Besitzer testete mehrfach mit einem TAGE
   alten Tab — die Oberfläche lädt heiß vom Server, aber nur bei einem
   RELOAD, den nie jemand machte). Ändert sich der Stand der Oberfläche auf
   der Platte, lädt die Seite sich selbst neu — sanft: nie mitten im Film,
   in einem Dialog oder beim Tippen, höchstens einmal je Minute.
   Nie mitten im Titel (Entscheid 7a Punkt 5, 25.09.2026): spielt Musik
   oder VLC, bleibt das Neuladen vorgemerkt; der Sekundentakt holt es in der
   nächsten Pause nach, am Titelende ersetzt es das Weiterschalten
   (plTitelEnde, vlcTick). Crossfade und Automix starten den Nachfolger
   schon vor dem Titelende hörbar: solange ein Stand vorgemerkt ist, startet
   darum keine Blende (uebergangTick), und läuft eine schon, wartet das
   Neuladen auch am Titelende auf die nächste Pause. */
let uiStand=null, uiNeuVorgemerkt=false;
function uiStandPruefen(stand){
  if(!stand)return;
  if(uiStand===null){uiStand=stand; return;}
  if(stand===uiStand)return;
  uiNeuVorgemerkt=true;
  if(wiedergabeSpielt())return;
  uiNeuLaden();
}
function wiedergabeSpielt(){                           // Musik im Browser oder am Gerät VLC
  const pe=document.getElementById('pl-el');
  return !!(pe&&!pe.paused&&!pe.ended)||(plGeraet==='vlc'&&vlcSpielt);
}
/* Lädt neu, wenn ein neuer Stand vorgemerkt ist und nichts dagegen spricht;
   true heißt: die Seite lädt jetzt neu. */
function uiNeuLaden(){
  if(!uiNeuVorgemerkt)return false;
  if(xfNext&&!xfNext.paused&&!xfNext.ended)return false;   // Blende läuft: der Nachfolger ist schon hörbar
  const tippt=document.activeElement&&['INPUT','TEXTAREA'].includes(document.activeElement.tagName);
  if(tvpOffen||tvInfoOffen||tvDialogOffen||tippt)return false;
  let letzter=0;
  try{letzter=+sessionStorage.getItem('ui_reload_ts')||0;}catch(e){}   // gesperrter Speicher (F27)
  if(Date.now()-letzter<60000)return false;
  try{sessionStorage.setItem('ui_reload_ts',String(Date.now()));}catch(e){}
  location.reload();
  return true;
}
/* Addon-Nachschub (v1.2.0, der Besitzer): „eine kurze Info, dass jetzt x Downloads
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
  await api('/api/config',{fernsteuerung:an});
  await laden(); fernInfoMalen();
  if(an)alert('Fernsteuerung aktiviert.\n\nBitte die App EINMAL neu starten (Tray → Beenden → neu öffnen), '+
    'damit sie im WLAN erreichbar wird. Danach steht hier im ⚙ der Code + der Handy-Link.\n\n'+
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
  m.innerHTML='<div style="font-size:11.5px;color:var(--gedaempft);padding:2px 6px 7px">📱 Fernsteuerung läuft</div>'+
    '<div class="mzeile"><span>Code</span><b style="color:var(--akz2);letter-spacing:.08em">'+esc(f.code||'')+'</b></div>'+
    (f.url?'<div class="mzeile"><span>Am Handy öffnen</span><b style="font-size:11.5px">'+esc(f.url)+'</b></div>'
          :'<div class="mzeile"><span style="font-size:11.5px">Handy-Link erscheint nach einem App-Neustart</span></div>')+
    '<div class="msep"></div>'+
    '<button class="mbtn" onclick="document.getElementById(\'fernfly\').remove();fernToggle()">Fernsteuerung ausschalten</button>';
  document.body.appendChild(m);
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  menuSchliesser(m);
}
/* Entscheid 7a Punkt 3 (25.09.2026): neuer, längerer Code auf Knopfdruck.
   Der bisherige Code gilt bis zu diesem Klick (kein Zwangswechsel beim
   Update); danach müssen Handys mit dem alten Code den neuen eingeben.
   Gekoppelte Geräte (eigener Token) bleiben gekoppelt. */
async function fernCodeErneuern(){
  frageModal('Neuen Fernsteuerungs-Code erzeugen?\n\nHandys, die mit dem bisherigen Code verbunden sind, '+
    'müssen danach den neuen eingeben. Gekoppelte Geräte (Fernseher) bleiben gekoppelt.', '🔄 Code erneuern',
    async()=>{
      let neu='';
      try{neu=(await api('/api/code_erneuern')).code||'';}catch(e){}
      await laden(); fernInfoMalen();
      toast(neu?('📱 Neuer Code: '+neu):'Code konnte nicht erneuert werden.');
    });
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
      ' <button class="btn mini" onclick="fernCodeErneuern()" title="Neuen, längeren Code erzeugen — der bisherige gilt bis zu diesem Klick">🔄 Code erneuern</button>'+
      (f.url?'<br>Handy-Link: <b>'+esc(f.url)+'</b> (im selben WLAN öffnen)':'<br>(nach App-Neustart erscheint hier der Handy-Link)');
    else info.textContent='Aus — nur dein PC hat Zugriff (127.0.0.1).';
  }
}

async function hinzufuegen(){
  const box=document.getElementById('urls');
  const urls=box.value.trim(); if(!urls)return;
  await api('/api/add',{urls,qualitaet:document.getElementById('qual').value});
  box.value=''; laden();
}
async function aktion(id,art){
  await api('/api/action',{id,art});
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
  if(NUR_FERN){toast('⚙ Die Einstellungen gibt es nur am PC.'); return;}
  einstellungenModalInit();
  const m=document.getElementById('settingsmodal'); if(m)m.style.display='flex';
}
function settingsZu(){const m=document.getElementById('settingsmodal'); if(m)m.style.display='none';}
function hilfeModal(an){const m=document.getElementById('hilfemodal'); if(m)m.style.display=an?'flex':'none';}

