/* ================= Player ================= */
// plid (Build 144, der Besitzer Punkt 2): Kommt die Warteschlange aus einer GESPEICHERTEN
// Playlist, merkt sich der Player deren Id — vorher reiste nur der Anzeige-Name
// mit, und damit war gar nicht bekannt, wohin man zurueckspeichern koennte.
let playerState={queue:[],idx:-1,quelle:'',plid:''};
let playerLayout='horizontal';   // Standard: Video links, Playlist rechts (Favorit)
// Dashboard-Embed (?embed=1): standardmäßig Video OBEN, Playlist UNTEN (22.07.). Die
// GETEILTE localStorage-Preferenz bewusst NICHT lesen, damit die Standalone-Wahl nicht ins
// Embed leckt (und der Toggle unten schreibt im Embed auch nichts zurück).
const _plEmbed=(typeof location!=='undefined'&&location.search.indexOf('embed=1')>=0);
if(_plEmbed){playerLayout='vertikal';}
else{const v=lsLesen('ytdl_player_layout'); if(v)playerLayout=v;}
// „Video links" braucht Breite (24.11.2026: „Macht es vom Platz her nicht
// mehr Sinn?"): Die Seite rechts ist fest 200 px breit. In einer 410 px
// schmalen Player-Spalte blieben dem Video gemessen ~150x85 px, „Video oben"
// gibt ihm dort die volle Breite (~380x214). Darum gilt die Wahl „Video links"
// erst ab PL_HORIZONTAL_AB px Kartenbreite; ab da bekommt das Video mindestens
// so viel Breite wie die Seite daneben. Schmaler stellt der Player von selbst
// auf „Video oben", die gemerkte Wahl bleibt unberührt. Gemessen wird die
// Karte per ResizeObserver (Start unten), nicht per CSS-Container-Abfrage:
// Die Karte kann sich nicht selbst abfragen, und ihr nächster Container
// (.panel-body) ist durch sein Padding 32 px breiter als die Karte, an der die
// Kind-Regeln messen - zwei Schwellen, die auseinanderlaufen.
// Unsichtbare Karte (Breite 0): Wahl unverändert, der Observer meldet sich,
// sobald sie Breite bekommt.
const PL_HORIZONTAL_AB=560;
function playerLayoutSet(){
  const card=document.getElementById('pl-card');
  if(!card)return;
  const w=card.clientWidth;
  card.classList.toggle('pl-horizontal', playerLayout==='horizontal'&&(w===0||w>=PL_HORIZONTAL_AB));
}
function playerLayoutToggle(){
  playerLayout=(playerLayout==='horizontal')?'vertikal':'horizontal';
  if(!_plEmbed){lsSchreiben('ytdl_player_layout',playerLayout);}  // Embed: nur für die Sitzung
  playerLayoutSet();
}
function libFind(k){return libdaten.find(x=>x.id===k);}
function playerPlay(keys,start,quelle,plid){
  if(!(libdaten||[]).length){                          // Bibliothek noch nicht geladen -> erst holen,
    libLaden().then(()=>playerPlay(keys,start,quelle,plid));// sonst filtert der Check ALLES raus und der
    return;                                            // Player bleibt schwarz (Fund 14.07.)
  }
  keys=(keys||[]).filter(k=>{const x=libFind(k); return x&&x.vorhanden;});
  if(!keys.length){alert('Nichts Abspielbares — die Datei fehlt (verschoben/gelöscht).');return;}
  // Genau den LAUFENDEN Titel nochmal angeklickt -> nicht neu starten, sondern Pause/Play
  if(vlcAktiv() && keys.length===1 && keys[0]===aktKey()){ plTogglePlay(); return; }
  const el=document.getElementById('pl-el');
  if(el && keys.length===1 && keys[0]===aktKey()){ if(el.paused)el.play(); else el.pause(); return; }
  radioAktiv=false;                                  // manueller Start beendet den Radio-Stream
  playerState.queue=keys; playerState.idx=start||0;
  playerState.quelle=quelle||'Bibliothek';           // Name fürs Playlist-Fenster (21.07.)
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
  // Radio ist endlos: auch wer per Taste weiterschaltet, kommt nie ans Ende
  // der 40er-Liste (nachgefüllt wurde bisher nur beim natürlichen Titelende).
  if(radioAktiv)radioNachfuellen();
  const n=queueIdxPassend(playerState.idx+1,1);        // Abspielart 🎶/🎬 zählt mit
  if(n>=0){playerState.idx=n; renderPlayerMedia();}
  // Nur EIN Titel in der Playlist (bzw. nichts Passendes mehr dahinter)?
  // ⏭ geht weiter durch die Bibliothek — wie das automatische Titelende.
  else if(playerState.queue.length<=1)naechstesAusBibliothek();
}
function playerPrev(){
  // Standard-Player-Verhalten (05.08., wie Spotify/YT Music): läuft der
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
  // Symmetrisch zu playerNext (14.07.: 'ich kann nur vor, nicht zurück, ohne Playlist'):
  // Einzeltitel / nichts Passendes davor -> ⏮ geht in der Bibliothek einen zurück.
  else if(playerState.queue.length<=1)vorherigesAusBibliothek();
}
/* Mehrere ⏭/⏮ auf einmal (Windows-Knöpfe am Server-VLC zwischen zwei
   Abfragen): EIN Wechsel ans Ziel. Vorher startete jeder Zwischentitel mit
   eigenem VLC-Befehl, und die Reihenfolge am Server war nicht fest
   (Gegenprüfung 24.09.). Ein einzelner Druck bleibt playerNext/playerPrev mit
   allen Regeln (3-s-Regel, Bibliothek, Radio). */
function playerSchritte(n){
  if(n===1){playerNext(); return;}
  if(n===-1){playerPrev(); return;}
  if(!n)return;
  if(radioAktiv&&n>0)radioNachfuellen();
  const r=n>0?1:-1; let i=playerState.idx;
  for(let k=0;k<Math.abs(n);k++){const j=queueIdxPassend(i+r,r); if(j<0)break; i=j;}
  if(i!==playerState.idx){playerState.idx=i; renderPlayerMedia();}
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
  // Build 93 (der Besitzer): YouTube genau DA oeffnen, wo der Player gerade steht (&t=…s);
  // unter 4 s bleibt der Link sauber ohne Zeitangabe. (Der Parameter steuert
  // NUR das Abspielen — ein Download ueber die App laedt immer das GANZE Video.)
  const x=libFind(aktKey()); if(!x||!x.url)return;
  const el=document.getElementById('pl-el');
  const s=el&&isFinite(el.currentTime)?Math.floor(el.currentTime):0;
  const url=s>3?x.url+(x.url.includes('?')?'&':'?')+'t='+s+'s':x.url;
  window.open(url,'_blank','noreferrer');
}
function playerLinkKopieren(){
  // Build 95 (der Besitzer): Link zum TEILEN — bewusst OHNE Zeitstempel (x.url ist die
  // gespeicherte saubere watch-URL; das t haengt nur playerYoutube beim Oeffnen an).
  const x=libFind(aktKey()); if(!x||!x.url){toast('Kein Titel im Player');return;}
  try{navigator.clipboard.writeText(x.url); toast('🔗 Link kopiert (ohne Zeitstempel)');}
  catch(e){prompt('Link zum Kopieren:',x.url);}
}

/* ---- Abspielgeschwindigkeit ---- */
let playSpeed=1; try{const v=parseFloat(localStorage.getItem('ytdl_speed')); if(v>=0.25&&v<=3)playSpeed=v;}catch(e){}
function speedAnwenden(){const el=document.getElementById('pl-el'); if(el)el.playbackRate=playSpeed;
  lsSchreiben('ytdl_speed',playSpeed);
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
  for(const block of (t||'').replace(/\r/g,'').split(/\n\n+/)){
    const zeilen=block.split('\n').filter(Boolean);
    const ti=zeilen.findIndex(z=>z.includes('-->'));
    if(ti<0)continue;
    const m=zeilen[ti].match(/([\d:.]+)\s*-->\s*([\d:.]+)/);
    if(!m)continue;
    const txt=zeilen.slice(ti+1).join(' ').replace(/<[^>]*>/g,'').replace(/\s+/g,' ').trim();
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
  for(const zeile of (t||'').split(/\r?\n/)){
    const txt=zeile.replace(/\[[^\]]*\]/g,'').trim();   // alle [..]-Marken (Zeit + Meta) raus
    let m; const re=/\[(\d+):(\d+(?:\.\d+)?)\]/g;
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
  // Standardmäßig da sein (14.07.: „direkt Karaoke go"): fehlen Untertitel
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
/* Untertitel-Panel am 💬-Knopf (05.08., Amazon/Netflix-Muster): ALLE
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
  // verlassen das Panel nie („kann eh nichts anklicken").
  m.addEventListener('pointerdown',e=>e.stopPropagation());
  const fuellen=()=>{
    m.innerHTML='';
    // Live-VORSCHAU (Disney: „Subtitles will appear like this") — dieselben
    // CSS-Variablen wie die echte Anzeige, jede Wahl wirkt sofort sichtbar.
    // Feste Höhe (05.08.: „das Fenster wird größer und kleiner") — die
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
    // Modus — OHNE Transkript (lebt in den Optionen; Taste S kann alles)
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
    // Der Besitzer 05.08.: bei KARAOKE greifen Farbe/Deckkraft/Hintergrund nicht (die
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
      // Kompakt („zu viel Text in der Zeile"): Deckkraft-Stufen als EIN
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
  // Fernbedienung/Tastatur („für eine Fernbedienung kompatibel"):
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
  lsSchreiben('ytdl_subromaji',subRomaji?'1':'0');
  const k=aktKey(); if(k)subLaden(k);
}
let subLaedt=false;                                    // läuft gerade ein Untertitel-Download?
/* Untertitel-Look (05.08., Disney-Muster: „alle Optionen, unterschiedliche
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
  lsSchreiben('ytdl_substil',JSON.stringify(subStil));
  // Server-global (gilt für alle Videos, überlebt jede Version); ein
  // Gerät im WLAN merkt ihn nur für sich (fernWahl).
  if(NUR_FERN)fernWahlMerken({sub_look:Object.assign({},subStil)});
  else api('/api/wiedergabe',{global:1,merge:1,sub_look:subStil}).catch(()=>{});
  subStilAnwenden();
}
function subStilReset(){
  subStil=Object.assign({},SUB_STANDARD);
  lsSchreiben('ytdl_substil',JSON.stringify(subStil));
  if(NUR_FERN)fernWahlMerken({sub_look:null});      // Gerät: wieder der Stil des PCs ab dem nächsten Öffnen
  else api('/api/wiedergabe',{global:1,merge:1,sub_look:''}).catch(()=>{});
  subStilAnwenden();
}
/* Beim Seitenstart gewinnt der SERVER-Stand (überlebt Versionen/Browser);
   localStorage bleibt der schnelle Zwischenspeicher. Auf einem Gerät im WLAN
   gewinnt ein dort gewählter Stil (fernWahl), sonst ebenfalls der Server. */
let _subStilServer=false;
function subStilVomServer(){
  if(_subStilServer||!daten||!daten.config)return;
  _subStilServer=true;
  const g=Object.assign({},(daten.config.wiedergabe)||{});
  const eigen=NUR_FERN?fernWahl().sub_look:null;
  if(eigen&&typeof eigen==='object')g.sub_look=eigen;
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
    // Sichtbares Feedback (21.07.): beim Laden „⏳", damit nicht „nichts passiert" wirkt.
    const warte=subLaedt&&!subCues&&(subMode==='zeilen'||subMode==='karaoke');
    ov.style.display=((subCues||warte)&&(subMode==='zeilen'||subMode==='karaoke'))?'':'none';
    ov.innerHTML=warte?'<span class="subtxt" style="opacity:.7">⏳ Untertitel werden geladen …</span>':'';}
  const ly=document.getElementById('pl-lyrics');
  if(ly){
    if(subCues&&subMode==='transkript'){
      ly.style.display='';
      ly.innerHTML='<div class="kap-titel">📜 Transkript'+(subLang?' · '+subLang:'')+'</div>'+
        subCues.map((c,i)=>`<div class="lyr" data-i="${i}" data-t="${c.start}" onclick="kapSpring(+this.dataset.t)"><span class="kap-z">${zeit(c.start)}</span>${esc(c.text)}</div>`).join('');
    }else{ly.style.display='none'; ly.innerHTML='';}
  }
  subIdx=-1;
}
function subModusSetzen(mode){
  subMode=mode;
  if(typeof subModeSitzung!=='undefined')subModeSitzung=mode;   // Sitzungs-Standard mitziehen
  lsSchreiben('ytdl_submode',subMode);
  // Blink-Wurzel 2 + der Besitzer 05.08. („wenn ich die einmal an habe, dann sind die
  // für alle an"): der Umschalter gilt GLOBAL — früher schrieb er eine
  // Absolut-Regel je Titel, und Titel mit alter „aus"-Regel schalteten die
  // Untertitel wieder ab. Ausnahmen je Titel/Playlist setzt weiter der
  // Rechtsklick-Dialog „Wiedergabe…" (bewusst, nicht als Nebenwirkung).
  // Ein Gerät im WLAN merkt den Umschalter nur für sich (fernWahl).
  if(NUR_FERN)fernWahlMerken({sub:mode});
  else api('/api/wiedergabe',{global:1,merge:1,sub:mode}).catch(()=>{});
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
   nachladen (13.07.: „Ich will keine Fenster aufploppen sehen"). Je Titel
   nur einmal pro Sitzung versucht; das Ergebnis holt subLaden zeitversetzt ab. */
let subAutoVersucht=new Set();
async function subNachladen(){
  const k=aktKey(); if(!k||subAutoVersucht.has(k))return;
  subAutoVersucht.add(k);
  subLaedt=true; subAnzeigen();                         // sofort „⏳ …" zeigen (21.07.)
  try{await api('/api/untertitel_laden',{id:k});}catch(e){}
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
  return (text||'').split(/(\s+)/).map(w=>/\S/.test(w)?'<span class="kw">'+esc(w)+'</span>':esc(w)).join('');
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
/* Untertitel-/Karaoke-Versatz (05.08., House-of-the-Rising-Sun-Fall:
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
  // Blink-Wurzel 1 (05.08.: „untertitel blinken mal an, mal aus"): ohne
  // gültige Uhr NICHT malen. subTick(null) aus dem VLC-Takt traf früher ein
  // Video im Browser-Element (vlcAktiv()=false, el=null) → t=0 → keine Zeile
  // gefunden → Anzeige leergewischt; das nächste timeupdate malte sie neu —
  // exakt das 1-Hz-Blinken.
  if(!el&&!vlcAktiv())return;
  // Zeit-Quelle je Gerät: Browser = <audio>/<video>, VLC = geschätzte
  // Status-Zeit (Fund 05.08.: am Gerät VLC kam nie ein Untertitel).
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
      // Bei LRCLIB die aktive Zeile in Wörter zerlegt (Mitleuchten, der Besitzer 21.07.);
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
    // Build 115 (der Besitzer, „wie bei einer echten Karaoke-Maschine"): der Wischer
    // läuft KONTINUIERLICH durch die Zeile. Die Zeit wird nicht gleichmäßig
    // auf die Wörter verteilt, sondern nach WORTLÄNGE gewichtet — lange
    // Wörter brauchen länger, das trifft den Silben-Rhythmus deutlich besser
    // (echte Silben-Zeiten liefert die Textquelle leider nicht mit).
    // Der Besitzer 05.08.: LRC kennt keine Endzeiten — „ende" ist der Start der
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
    `<div class="kap" data-t="${c.start}" onclick="kapSpring(+this.dataset.t)"><span class="kap-z">${zeit(c.start)}</span> ${esc(c.titel||'')}</div>`).join('');
}
function kapSpring(s){const el=document.getElementById('pl-el'); if(el){el.currentTime=s; el.play();}}

/* ---- Visualizer (Web Audio): mehrere Stile, Farbe folgt dem aktiven Look ---- */
const VIZMODES=[['balken','📊','Balken'],['spiegel','🪞','Spiegel-Balken'],['welle','〰','Welle'],
  ['oszi','📈','Oszilloskop'],['radial','🎯','Radial'],['matrix','🟩','Matrix-Regen'],
  ['spektro','🌈','Spektrogramm'],['aus','▫','Aus']];
let vizMode='balken';
try{const v=localStorage.getItem('ytdl_viz'); if(v&&VIZMODES.some(m=>m[0]===v))vizMode=v;}catch(e){}
let audioCtx=null, vizAnalyser=null, vizSrc=null, vizGain=null, normGain=null, vizEl=null, vizRAF=null, vizFarbe='#c9952b';
let normAn=lsLesen('ytdl_norm')==='1';
function normSetzen(an){ normAn=!!an; lsSchreiben('ytdl_norm',normAn?'1':'0');
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
  lsSchreiben('ytdl_eq',JSON.stringify(eqWerte));
  const l=document.getElementById('eqval'+i); if(l)l.textContent=(db>0?'+':'')+db;
}
function eqPreset(name){ (EQ_PRESETS[name]||EQ_PRESETS.Flat).forEach((db,i)=>{
  eqSetzen(i,db); const s=document.getElementById('eqsl'+i); if(s)s.value=db; }); }
function eqPopover(ev){
  const alt=document.getElementById('eqpop'); if(alt){alt.remove(); return;}
  const m=document.createElement('div'); m.className='panelmenu'; m.id='eqpop'; m.style.minWidth='240px';
  m.innerHTML='<div class="sm-titel">🎚 Equalizer</div><div class="eq-row">'+
    EQ_BANDS.map((f,i)=>`<div class="eq-band"><span class="eq-val" id="eqval${i}">${(eqWerte[i]>0?'+':'')+(eqWerte[i]||0)}</span>`+
      `<input id="eqsl${i}" class="eq-sl" type="range" min="-12" max="12" step="1" value="${eqWerte[i]||0}" data-i="${i}" oninput="eqSetzen(+this.dataset.i,this.value)">`+
      `<span class="eq-lab">${EQ_LABELS[i]} Hz</span></div>`).join('')+
    '</div><div class="eq-presets">'+Object.keys(EQ_PRESETS).map(n=>`<button class="btn mini" data-n="${esc(n)}" onclick="eqPreset(this.dataset.n)">${n}</button>`).join('')+'</div>'+
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
  uebergang=v; lsSchreiben('ytdl_uebergang',v);
  const r=document.getElementById('xfrow'); if(r)r.style.display=(v==='crossfade'||v==='automix')?'block':'none';
}
/* Canvas: animiertes, weichgezeichnetes Cover als lebender Hintergrund (Spotify-Canvas-Gefühl) */
let canvasAn=lsLesen('ytdl_canvas')==='1';
function setCanvas(an){canvasAn=!!an; lsSchreiben('ytdl_canvas',canvasAn?'1':'0'); canvasAnwenden();}
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
  lsSchreiben('ytdl_crossfade',crossfadeSek);
  const l=document.getElementById('xfval'); if(l)l.textContent=crossfadeSek?crossfadeSek+' s':'aus';
}
function xfAbbrechen(){                                // laufenden Übergang verwerfen, Lautstärke zurück
  if(xfNext){medienS.freigeben(xfNext); xfNext=null;}   // nur pausiert hielt es Windows' Eintrag fest
  if(vizGain){try{vizGain.gain.value=1;}catch(e){}}
}
/* Dieselbe Entscheidung wie playerAdvance (-1: kein Übergang). el: das Element
   des laufenden Titels — es merkt sich den Zufallszug (el._zug). Gapless fragt
   bei jedem timeupdate im 12-s-Fenster, Crossfade beim Start und das Titelende
   noch einmal: ohne Merken zog jede Frage neu, und nur ein Audio-Zug blieb
   hängen (Prüfung Runde 1: Gapless 100 % Audio). EIN Zug je Titel, auch wenn
   er ein Video trifft und darum kein Übergang startet (plTitelEnde nimmt ihn). */
function xfNaechsterIndex(el){
  const d=nachEnde(el?el._zug:undefined);
  if(el&&d.zufall)el._zug=playerState.queue[d.idx];
  return (d.art==='titel'&&d.xf)?d.idx:-1;
}
function xfNachfolgerGilt(d){                          // ist der vorbereitete Titel laut Entscheidung d noch dran?
  return !!(xfNext&&d.art==='titel'&&d.xf&&playerState.queue[d.idx]===xfNext._key);
}
function xfZuruecknehmen(el){                          // Übergang verwerfen, alter Titel wieder in eingestellter Lautstärke
  xfAbbrechen(); if(el){el._xf=false; try{el.volume=plVol/100;}catch(e){}}
}
function xfPruefen(){                                  // Regel umgestellt (Sleep, Wiederholen): darf die Blende noch?
  if(xfNext&&!xfNachfolgerGilt(nachEnde(xfNext._key)))xfZuruecknehmen(document.getElementById('pl-el'));
}
/* 'ended' des Player-Elements. Übernommen wird der vorbereitete Nachfolger nur,
   wenn er JETZT noch dran ist (Sleep, Wiederholen, Warteschlangen-Umbau seit
   der Vorbereitung); sonst wird er freigegeben und es geht normal weiter. */
function plTitelEnde(ev){
  const el=ev&&ev.target; if(!el||!el.isConnected)return;   // abgelöstes Element entscheidet nichts mehr
  if(uiNeuLaden())return;                                 // vorgemerkter neuer Stand: jetzt neu laden (F10)
  const d=nachEnde(xfNext?xfNext._key:el._zug);          // Zufall: der Zug dieses Titels gilt
  if(xfNext){
    if(xfNachfolgerGilt(d)){xfUebernehmen(d.idx); return;}
    xfZuruecknehmen(el);
  }
  playerAdvance(d);
}
function xfIstAudio(key){const x=libFind(key); return !!(x&&x.vorhanden&&((x.kategorie==='MP3')||(!x.vcodec&&x.acodec)));}
function starteCrossfade(cur, restSek){
  const ni=xfNaechsterIndex(cur); if(ni<0)return;
  const key=playerState.queue[ni]; if(!xfIstAudio(key))return;    // nur Audio in Audio überblenden
  // Die Restzeit ist Medienzeit, die Blende läuft in Wanduhrzeit: bei Tempo 2×
  // endet der Titel nach der halben Zeit. Automix mit Dauer „aus" meint 6 s.
  const rate=cur.playbackRate>0?cur.playbackRate:1;
  const dauer=Math.max(0.3, Math.min(crossfadeSek||6, restSek)/rate);
  const nx=new Audio('/media?id='+encodeURIComponent(key)); nx.volume=0; nx._ni=ni; nx._key=key;
  nx.defaultPlaybackRate=rate; nx.playbackRate=rate;   // Nachfolger im selben Tempo (sonst Tempo-Sprung bei der Übernahme)
  nx._xfAlt=cur; nx._xfT0=performance.now(); nx._xfDauer=dauer; nx._xfRate=rate; nx._xfP=0;
  nx._xfRest0=(cur.duration-cur.currentTime)||restSek; // wirkliche Restzeit (Automix startet vor dem Fenster)
  xfNext=nx;
  nx.play().catch(()=>{});
  (function ramp(){                                    // aktuellen Titel aus-, nächsten einblenden
    if(xfNext!==nx)return;                             // übernommen oder zurückgenommen
    xfLautstaerke();
    requestAnimationFrame(ramp);                       // weiter, solange der Nachfolger lebt: der Regler wirkt bis zur Übernahme
  })();
}
/* Lautstärke der laufenden Blende: Ziel ist IMMER die eingestellte Lautstärke
   (plVol, jedes Mal frisch gelesen), nie 1,0. Läuft im Bildtakt UND im
   timeupdate-Takt (uebergangTick) — im verdeckten Tab ruht requestAnimationFrame,
   dann führt die Restzeit des alten Titels die Blende weiter. */
function xfLautstaerke(){
  const nx=xfNext; if(!nx||!nx._xfAlt)return;          // Gapless: nichts zu blenden
  const cur=nx._xfAlt;
  const pZeit=(performance.now()-nx._xfT0)/(nx._xfDauer*1000);
  const pRest=cur.duration?((nx._xfRest0-(cur.duration-cur.currentTime))/nx._xfRate)/nx._xfDauer:0;
  const p=nx._xfP=Math.min(1,Math.max(nx._xfP,pZeit,pRest||0));
  const v=plVol/100;
  if(vizGain){try{vizGain.gain.value=1-p;}catch(e){}} else {try{cur.volume=v*(1-p);}catch(e){}}
  try{nx.volume=v*p;}catch(e){}
}
function xfUebernehmen(idx){                           // Titel-Ende: vorbereitetes Element übernehmen (idx: frisch entschieden)
  if(!xfNext)return false;
  adoptEl=xfNext; xfNext=null; adoptEl.volume=plVol/100; adoptEl._xfAlt=null;
  if(adoptEl.paused)adoptEl.play().catch(()=>{});      // Gapless: gepuffertes Element startet SOFORT
  playerState.idx=(idx===undefined)?adoptEl._ni:idx;
  renderPlayerMedia(); return true;
}
function gaplessPreload(el){                           // nächsten Titel nur PUFFERN (nicht abspielen)
  const ni=xfNaechsterIndex(el); if(ni<0)return;
  const key=playerState.queue[ni]; if(!xfIstAudio(key))return;
  xfNext=new Audio('/media?id='+encodeURIComponent(key));
  xfNext.preload='auto'; xfNext._ni=ni; xfNext._key=key;
}
function uebergangTick(el){                            // ein Ticker für alle Übergangs-Arten
  if(!el.duration)return;
  if(el._xf){if(xfNext&&xfNext._xfAlt===el)xfLautstaerke(); return;}   // Blende läuft: auch ohne Bildtakt nachführen
  const rest=el.duration-el.currentTime;
  // Neuer Stand vorgemerkt: das Titelende lädt neu, darum keine Blende, die
  // den Nachfolger schon vorher hörbar startet (F10, nie mitten im Titel).
  if(uiNeuVorgemerkt&&(uebergang==='crossfade'||uebergang==='automix'))return;
  if(uebergang==='crossfade'&&crossfadeSek>0&&rest<=crossfadeSek){
    el._xf=true; starteCrossfade(el,rest);
  }else if(uebergang==='gapless'&&rest<=12&&!xfNext){
    gaplessPreload(el);
  }else if(uebergang==='automix'&&rest<=Math.max(16,(crossfadeSek||6)+4)){
    // Automix: wird das Outro leise (RMS fällt), JETZT weich überblenden — sonst spätestens kurz vor Ende
    let rms=1;
    if(vizAnalyser){const buf=new Uint8Array(vizAnalyser.fftSize); vizAnalyser.getByteTimeDomainData(buf);
      let s=0; for(let i=0;i<buf.length;i++){const v=(buf[i]-128)/128; s+=v*v;} rms=Math.sqrt(s/buf.length);}
    if(rms<0.06||rest<=Math.max(4,crossfadeSek||6)){el._xf=true; starteCrossfade(el,Math.min(rest,crossfadeSek||6));}
  }
}
/* ---- Steuerleiste AUF dem Video/Cover (13.07.: „wie bei YouTube, Clip wie
   bei Twitch") — ersetzt die native Browser-Leiste bei Video UND Audio.
   Blendet bei Maus-Ruhe aus (nur solange abgespielt wird). ---- */
let plVol=100; try{const v=parseInt(localStorage.getItem('ytdl_vol'),10); if(v>=0&&v<=100)plVol=v;}catch(e){}
let plbSeekAktiv=false, plbIdleTimer=null;
function plBarHTML(istVideo){
  // onclick=stopPropagation: transportRender ersetzt beim Klick das Icon im
  // Knopf — das geklickte SVG ist dann schon aus dem DOM und der closest()-
  // Check in media.onclick griffe ins Leere -> Video pausierte (13.07.).
  // Die Leiste schluckt ihre Klicks deshalb selbst, bevor sie die Fläche erreichen.
  return `<div class="pl-bar" id="pl-bar" onclick="event.stopPropagation()">`+
   `<div class="pl-barseek"><span class="pl-btime" id="plb-t0">0:00</span>`+
    `<input type="range" id="plb-seek" min="0" max="1000" value="0" title="Spulen" `+
      `oninput="plbSeekDrag(this.value)" onchange="plbSeekEnd(this.value)" `+
      `onpointerdown="plbSeekAktiv=true" onpointerup="plbSeekAktiv=false">`+
    `<span class="pl-btime" id="plb-t1">0:00</span></div>`+
   `<div class="pl-barrow">`+
    // Build 121 (Entscheid): Im Bild lebt nur noch, was zum BILD gehört.
    // Play/Pause bleibt (der eine Griff, den man im Video erwartet — und ein
    // Klick ins Bild tut dasselbe); Zufall/Vor/Zurück/Wiederholen/Cover-Stil
    // stehen oben in der Steuerzentrale, die nie verschwindet.
    // Build 130: ±10 s und „nächster Titel" gibt es NUR im Vollbild — dort
    // fehlt die Steuerzentrale oben, die das sonst übernimmt.
    // Der Besitzer 05.08. (Disney/Netflix-Bilder): ±10 s gehören IMMER in die Leiste,
    // nicht nur im Vollbild — fürs Sofa sind die Pfeiltasten zu weit weg.
    // Der Besitzer 05.08.: „im videoplayer im fernseher ist vor und zurückspulen mit
    // höherer geschwindigkeit … schon << und >>. Am PC sollte es jedoch
    // nächster und vorheriger Track sein. PC ist halt anders als fernseher."
    // — Beide Paare stehen in der Leiste, CSS tauscht sie im Vollbild.
    `<button class="mp-btn bo1 weg-im-vollbild" id="plb-prev" onclick="playerPrev()" title="Voriger Titel — läuft der Titel schon, erst an den Anfang (Taste P)">${ico('prev')}</button>`+
    `<button class="mp-btn nur-vollbild" id="plb-rew" onclick="spulen(-1)" title="Zurückspulen — nochmal drücken: schneller (bis 32×), Play hält an der Stelle">${ico('back')}</button>`+
    `<button class="mp-btn bo0" id="plb-back10" onclick="plbSpringen(-10)" title="10 Sekunden zurück (Taste J)">${ico('r10')}</button>`+
    `<button class="mp-btn" data-tr="pp" onclick="plTogglePlay()">${ico('play')}</button>`+
    `<button class="mp-btn bo0" id="plb-fwd10" onclick="plbSpringen(10)" title="10 Sekunden vor (Taste L)">${ico('f10')}</button>`+
    `<button class="mp-btn nur-vollbild" id="plb-ffw" onclick="spulen(1)" title="Vorspulen — nochmal drücken: schneller (bis 32×), Play hält an der Stelle">${ico('fwd')}</button>`+
    `<button class="mp-btn bo1 weg-im-vollbild" id="plb-next" onclick="playerNext()" title="Nächster Titel (Taste N)">${ico('next')}</button>`+
    `<span class="pl-bspacer"></span>`+
    // Der Besitzer 05.08. (Netflix/YouTube-Muster): Untertitel + Lautstärke gehören zum
    // KERN — sie überleben jede Player-Größe (keine bo-Ausblende-Klasse).
    `<button class="pl-bsp" id="plb-sub" onclick="subMenu(event)" title="Untertitel: Modus, Sprache, Größe, Stil, Versatz (Taste S wechselt schnell den Modus)">💬</button>`+
    `<button class="pl-bsp bo3 weg-im-vollbild nur-pc" onclick="clipDialog(aktKey())" title="✂ Ausschnitt schneiden (wie ein Twitch-Clip)">✂</button>`+
    // Der Besitzer 05.08.: am Fernseher (Vollbild) gehört ↻ (VLC neu verbinden) an die
    // Stelle der Schere — sichtbar nur am Gerät VLC.
    `<button class="pl-bsp nur-vollbild" onclick="vlcNeustart()" style="${plGeraet==='vlc'?'':'display:none'}" title="VLC neu verbinden: frisch starten und an der letzten Stelle weiterspielen">↻</button>`+
    `<button class="pl-bsp bo3 weg-im-vollbild" id="plb-speed" onclick="speedMenu(event)" title="Geschwindigkeit wählen">${playSpeed}×</button>`+
    `<span class="pl-bvolwrap">🔊<input type="range" class="pl-bvol" min="0" max="100" value="${plVol}" oninput="plbVol(this.value)" title="Lautstärke"></span>`+
    // YouTube-Öffnen und Link-Kopieren beziehen sich auf den TITEL, nicht auf
    // die Darstellung ⇒ sie stehen oben in der Steuerzentrale (Build 121).
    (istVideo?`<button class="pl-bsp bo2 weg-im-vollbild" onclick="plbPip()" title="Bild-in-Bild: Video schwebt über allen Fenstern (Taste I)">⧉</button>`:'')+
    (istVideo?`<button class="pl-bsp weg-im-vollbild" onclick="plbFullscreen()" title="Vollbild (Taste F)">⛶</button>`:'')+
    // Im Vollbild wird aus „Vollbild" ein deutliches „Beenden" (Beenden
    // gehört zum Wichtigsten) — sonst sucht man im randlosen Bild den Ausweg.
    (istVideo?`<button class="pl-bsp nur-vollbild" id="plb-exitfs" onclick="plbFullscreen()" title="Vollbild beenden (Taste F oder Esc)">✕</button>`:'')+
   `</div></div>`;
}
function plTogglePlay(){
  // Streamer-Muster: Läuft gerade der Spul-Modus, beendet Play/OK NUR das
  // Spulen — es läuft an der Stelle weiter (pausiert wurde ja nie).
  if(spulWeg){spulStopp(); return;}
  if(vlcAktiv()){
    // Der Besitzer 05.08.: das Symbol muss SOFORT umspringen — nicht erst mit dem
    // nächsten 1-s-Status (der korrigiert, falls der Befehl scheiterte).
    vlcSpielt=!vlcSpielt;
    document.querySelectorAll('[data-tr="pp"]').forEach(b=>{
      b.innerHTML=ico(vlcSpielt?'pause':'play');
      b.title=vlcSpielt?'Pause':'Abspielen';});
    vlcBefehl('toggle'); return;}
  const el=document.getElementById('pl-el'); if(el){if(el.paused)el.play(); else el.pause();}}
/* ---- Springen mit sichtbarer Rückmeldung (Build 132) ----------------------
   Vorgabe: „Wenn ich Pfeiltasten drücke, dann will ich wie in YouTube sehen, dass
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
/* ---- Spulen am Fernseher (05.08.) --------------------------------------
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
/* Sprungweite der Pfeiltasten (Wunsch: einstellbar). YouTube nimmt 5 s —
   das bleibt der Standard, damit sich die Tasten vertraut anfühlen. */
function sprungWeite(){
  let v=parseInt(lsLesen('ytdl_sprung'),10)||5;
  return Math.max(1,Math.min(60,v));
}
function sprungWeiteSetzen(v){
  const n=Math.max(1,Math.min(60,parseInt(v,10)||5));
  lsSchreiben('ytdl_sprung',n);
  toast('⏩ Pfeiltasten springen '+n+' Sekunden.');
}
/* Seitenverhältnis des Bildfelds (Build 130). Der Besitzer will 16:9 FEST, damit das
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
  lsSchreiben('ytdl_ar',v);
  const m=document.getElementById('pl-media'); if(!m)return;
  arAnlegen(m,v);
  toast('🖵 Seitenverhältnis: '+((PL_AR.find(a=>a[0]===v)||[])[1]||v));
}
function seitenverhaeltnisAnwenden(){                  // beim Aufbau des Players
  let v=lsLesen('ytdl_ar')||'16/9';
  const m=document.getElementById('pl-media'); if(m)arAnlegen(m,v);
}
function plbSeekDrag(v){const t=document.getElementById('plb-t0'), d=spulStand().dauer;
  if(d&&t)t.textContent=zeit(v/1000*d);}
function plbSeekEnd(v){spulenAuf(v); plbSeekAktiv=false;}
function plbVol(v){plVol=Math.max(0,Math.min(100,+v||0));
  lsSchreiben('ytdl_vol',plVol);
  if(vlcAktiv())vlcBefehl('vol',{wert:plVol});   // Gerät VLC hört auf dieselbe Lautstärke
  const el=document.getElementById('pl-el'); if(el)el.volume=plVol/100;
  // Mini-Player- und Video-Leisten-Regler zeigen immer denselben Stand
  document.querySelectorAll('.pl-bvol').forEach(s=>{if(+s.value!==plVol)s.value=plVol;});}
function plbFullscreen(){const m=document.getElementById('pl-media'); if(!m)return;
  if(document.fullscreenElement)document.exitFullscreen();
  else if(m.requestFullscreen)m.requestFullscreen();}
