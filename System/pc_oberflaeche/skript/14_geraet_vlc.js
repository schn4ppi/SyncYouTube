/* ================= Gerät VLC ================= */
/* ---- Gerät „VLC" (Spec Punkt 5, Etappe B Stufe 1) ------------------------
   Spotify-Connect-Muster: die Oberfläche bleibt das Gehirn (Warteschlange,
   Weiterschalten, Abspielart), der Ton kommt aus einer ferngesteuerten
   VLC-Instanz auf dem PC (/api/vlc → python-vlc). Titelende meldet der
   1-s-Status-Takt, dann greift dieselbe playerAdvance-Logik wie im Browser.
   VLC nicht installiert ⇒ Hinweis (toast) + Browser-Player als Rückfall. */
let plGeraet=lsLesen('ytdl_geraet')||'browser';   // gesperrter Speicher (F27)
let vlcTimer=null, vlcEndeFuer='', vlcRateLetzte=1;
/* DIE eine Wahrheit „spielt gerade über VLC?" (05.08.): Gerät VLC gewählt
   UND der aktuelle Titel läuft dort wirklich — Videos OHNE Hülle spielen im
   Browser-Element (VLC kann sein Bild nicht in eine Webseite einbetten),
   Audio immer über VLC, in der Hülle alles. */
function vlcAktiv(){
  if(plGeraet!=='vlc')return false;
  const x=libFind(aktKey()); if(!x)return false;
  const istAudio=x.dateiart?x.dateiart==='audio':((x.kategorie==='MP3')||(!x.vcodec&&x.acodec));
  return istAudio||!!window.pywebview;
}
/* Hülle (Befund 24.09.): das Video-Panel VOR jedem VLC-Start beim Server
   (neu) anmelden. Die Hülle meldete es nur einmal; nach jedem Selbst-Neustart
   des Servers war es dort weg, und das erste Video öffnete VLCs eigenes
   Fenster (Filme im Vollbild). Wartet höchstens HUELLE_MELDEN_MS, Fehler
   still: der Start selbst geht immer weiter. Im Browser: nichts. */
const HUELLE_MELDEN_MS=3000;
/* Überholte Starts (Prüfung Runde 1): jede Anmeldung ist ein eigener js_api-
   Faden, ihre Rückkehr-Reihenfolge ist offen — ohne Zähler startete bei
   schnellem ⏭ der ÄLTERE Titel als letzter. Wer während der Anmeldung
   überholt wurde (neuerer Start, Stopp), schickt nichts mehr. Filme prüfen
   dafür tvpWechselGen (Esc und jeder Folgenwechsel zählen dort hoch). */
let vlcStartGen=0, liveStartGen=0;
async function huelleMelden(){
  const pw=window.pywebview&&window.pywebview.api;
  if(!pw||typeof pw.video_melden!=='function')return;
  let uhr=0;
  try{await Promise.race([pw.video_melden(),new Promise(r=>{uhr=setTimeout(r,HUELLE_MELDEN_MS);})]);}
  catch(e){}
  finally{clearTimeout(uhr);}
}
async function vlcBefehl(cmd,extra){
  try{
    // Stopp überholt einen wartenden Start — außer er gilt nur einem Titel
    // (nur_key, Freigabe am Filmende): der trifft am Server nur sich selbst
    // und würgte sonst eine gerade wartende Musik ab (Prüfung Runde 2).
    if(cmd==='play'||(cmd==='stop'&&!(extra&&extra.nur_key))){
      const g=++vlcStartGen;
      if(cmd==='play'){await huelleMelden(); if(g!==vlcStartGen)return null;}
    }
    const d=await api('/api/vlc',Object.assign({cmd:cmd},extra||{}));
    // Jede Antwort (Musik- UND Film-Takt) trägt die Windows-Knöpfe des
    // Server-VLC mit (medien_smtc.py) — hier landen Weiter/Zurück.
    smtcTaste(d).catch(()=>{});
    return d;
  }catch(e){return null;}
}
async function geraetWechsel(){
  if(plGeraet==='vlc'){
    plGeraet='browser'; lsSchreiben('ytdl_geraet','browser');
    vlcBefehl('stop'); geraetMalen(); if(aktKey())renderPlayerMedia();
    return;
  }
  const s=await vlcBefehl('pruefen');                 // lädt libvlc; ehrlicher Rückfall
  if(!s||!s.verfuegbar){toast((s&&s.grund)||'VLC nicht erreichbar — der Browser-Player spielt weiter.'); return;}
  plGeraet='vlc'; lsSchreiben('ytdl_geraet','vlc');
  geraetMalen(); if(aktKey())renderPlayerMedia();
}
function geraetMalen(){
  // Der Besitzer 05.08.: „Warum nicht einfach nur VLC?" — der Knopf heißt immer
  // 🖥 VLC und leuchtet, wenn VLC das Ausgabegerät ist (Toggle-Optik).
  document.querySelectorAll('#pl-geraet').forEach(b=>{
    b.textContent='🖥 VLC';
    b.classList.toggle('an',plGeraet==='vlc');
    b.title=plGeraet==='vlc'
      ?'VLC ist das Ausgabegerät (läuft unabhängig vom Browser-Fenster) — Klick schaltet zurück auf den Browser-Player'
      :'Auf VLC abspielen (dieser PC): läuft auch ohne Browser-Fenster weiter — Klick schaltet um; ohne installiertes VLC bleibt der Browser-Player';
  });
}
function renderPlayerVlc(media,x,k){
  // Der Besitzer 05.08.: „Ich will, dass die identisch aussehen" — die VLC-Ansicht
  // nutzt EXAKT die normale Player-Leiste (plBarHTML); nur der Ton kommt aus
  // VLC. Kein Hinweistext (der Tooltip am 🖥-VLC-Knopf erklärt es). Die
  // Leisten-Funktionen (Seek/Zeit/±10s/Merker/Play-Symbol) sind VLC-fähig
  // und lesen den 1-s-Status statt des <audio>-Elements.
  const t=x.thumb
    ?`<img class="pl-cover" src="/api/cover?id=${encodeURIComponent(k)}" style="cursor:pointer" data-fb="${esc(x.thumb)}" onerror="this.onerror=function(){this.style.display='none'};this.src=this.dataset.fb">`
    :`<img class="pl-cover" src="/api/cover?id=${encodeURIComponent(k)}" style="cursor:pointer" onerror="this.style.display='none'">`;
  media.innerHTML=`<canvas id="pl-viz" class="pl-viz"></canvas><div class="pl-vizwrap">${t}</div>`+
    `<div class="pl-subzeile" id="pl-sub-anzeige" style="display:none"></div>`+plBarHTML(false);
  media.classList.remove('viz-an');
  media.onclick=ev=>{                                  // Klick in die Fläche = Pause/Weiter
    if(ev.target.closest&&ev.target.closest('.pl-bar'))return;
    plTogglePlay();
  };
  vlcEndeFuer='';
  // Wiedergabe-Regeln (Etappe C) gelten auch hier: effektives Tempo mitgeben,
  // und bei eingeschalteten Untertiteln lädt VLC die .vtt als eigene Spur.
  const w=wiedergabeFuer(x);
  vlcRateLetzte=w.speed||playSpeed||1;
  vlcBefehl('play',{key:k,vol:plVol,rate:vlcRateLetzte,sub:subMode!=='aus',ton:w.ton||''}).then(s=>{
    if(s&&!s.verfuegbar){                              // VLC unterwegs verschwunden -> Rückfall
      toast(s.grund||'VLC nicht gefunden — der Browser-Player übernimmt.');
      plGeraet='browser'; lsSchreiben('ytdl_geraet','browser');
      geraetMalen(); renderPlayerMedia();
    }else if(s&&s.fehler)toast('VLC: '+s.fehler);
  });
  if(!vlcTimer)vlcTimer=setInterval(vlcTick,1000);
}
let vlcPosLetzte=0, vlcDauerLetzte=0, vlcHeilt=false, vlcPosTs=0, vlcSpielt=false, vlcKeyLetzter='';
function vlcPosGeschaetzt(){
  // Zwischen zwei Status-Takten weiterzählen — Untertitel/Karaoke laufen
  // sonst nur im 1-s-Ruck („untertitel an, aber kommt kein untertitel":
  // ohne <audio>-Element trieb NICHTS die Anzeige).
  return vlcPosLetzte+(vlcSpielt?((Date.now()-vlcPosTs)/1000)*(vlcRateLetzte||1):0);
}
function vlcKarLauf(){
  // Untertitel im Bildtakt am Gerät VLC — für ALLE Modi, nicht nur Karaoke
  // (Blink-Fix 05.08.: der 1-s-Status allein ließ Zeilen an den Cue-Grenzen
  // flackern und Cues unter 1 s ganz ausfallen).
  if(!window.requestAnimationFrame)return;
  cancelAnimationFrame(karRAF);
  const schritt=()=>{
    if(plGeraet!=='vlc'||!vlcAktiv()||!vlcSpielt||subMode==='aus'){karRAF=0; return;}
    subTick(null);
    karRAF=requestAnimationFrame(schritt);
  };
  karRAF=requestAnimationFrame(schritt);
}
function vlcNeustart(){
  // ↻ („Gibt es einen reload knopf wenn etwas abstürzt?"): VLC frisch
  // starten und an der letzten Stelle weiterspielen (3 s Anlauf).
  const k=aktKey(); if(!k)return;
  const w=wiedergabeFuer(libFind(k));
  const pos=Math.max(0,(vlcPosLetzte||0)-3);
  vlcBefehl('play',{key:k,vol:plVol,rate:(w.speed||playSpeed||1),sub:subMode!=='aus',pos,ton:w.ton||''});
  toast('↻ VLC neu verbunden'+(pos>0?' — weiter bei '+zeit(pos):''));
}
/* Etappe set_hwnd (Freigabe): läuft die Oberfläche in der PROGRAMM-HÜLLE
   (window.pywebview), meldet sie die Player-Fläche — der Server-VLC rendert
   sein Video dann IN das Hüllen-Fenster statt in ein eigenes. Die Leiste
   bleibt frei (Fläche endet an ihrer Oberkante); Geräte-Pixel via dpr. */
let _hRectSig='';
function huelleVideoRect(s){
  const pw=window.pywebview&&window.pywebview.api;
  if(!pw||!pw.video_rect)return;
  const x=libFind(aktKey());
  const video=x&&(x.dateiart?x.dateiart!=='audio':(x.kategorie!=='MP3'));
  const wrap=document.querySelector('#pl-media .pl-vizwrap');
  const an=!!(vlcAktiv()&&video&&wrap&&s&&s.verfuegbar&&s.zustand!=='aus');
  let sig='aus', args=[0,0,0,0,false];
  if(an){
    const r=wrap.getBoundingClientRect();
    const bar=document.querySelector('#pl-media .pl-bar');
    let unten=r.bottom;
    if(bar){const br=bar.getBoundingClientRect();
      if(br.height>0&&br.top<unten)unten=Math.max(r.top,br.top);}
    const dpr=window.devicePixelRatio||1;
    args=[Math.round(r.left*dpr),Math.round(r.top*dpr),
          Math.round(r.width*dpr),Math.round(Math.max(0,unten-r.top)*dpr),true];
    sig=args.join(',');
  }
  if(sig===_hRectSig)return;                          // nur Änderungen melden
  _hRectSig=sig;
  try{pw.video_rect(args[0],args[1],args[2],args[3],args[4]);}catch(e){}
}
async function vlcTick(){
  if(plGeraet!=='vlc'){clearInterval(vlcTimer); vlcTimer=null; huelleVideoRect(null); return;}
  const s=await vlcBefehl('status'); if(!s||!s.verfuegbar)return;
  huelleVideoRect(s);
  if(s.rate)vlcRateLetzte=s.rate;
  if(s.dauer)vlcDauerLetzte=s.dauer;
  vlcKeyLetzter=s.key||'';
  vlcSpielt=(s.zustand==='spielt');
  if(vlcSpielt){
    // Blink-Wurzel 3 (Uhr-Klemme): der frische Status hängt oft ein paar
    // hundert ms HINTER der weiterlaufenden Schätz-Uhr — kleine Rücksprünge
    // warfen die Untertitel-Zeile kurz aus ihrem Zeitfenster (leer, nächster
    // Takt wieder da = Flackern an Zeilen-Grenzen). Nur echte Sprünge
    // (Seek/Drift > 1,5 s) setzen die Uhr zurück.
    const gesch=vlcPosGeschaetzt();
    if(!(s.pos<gesch&&gesch-s.pos<1.5)){vlcPosLetzte=s.pos; vlcPosTs=Date.now();}
  }
  medienVlcSpiegel(s);                                 // Windows-Overlay: Zustand + Zeitleiste
  // Untertitel am Gerät VLC: der Bildtakt (vlcKarLauf, jetzt für ALLE Modi)
  // treibt die Anzeige weich; der 1-s-Takt bleibt Fallback — aber nur mit
  // gültiger VLC-Uhr (Blink-Wurzel 1: nie mit t=0 malen).
  if(subMode!=='aus'&&subCues&&vlcAktiv())subTick(null);
  if(subMode!=='aus'&&vlcSpielt&&!karRAF)vlcKarLauf();
  // Die NORMALE Player-Leiste spiegelt den VLC-Zustand (identische
  // Optik): Play/Pause-Symbol überall, Tempo-Knopf zeigt die echte Rate.
  document.querySelectorAll('[data-tr="pp"]').forEach(b=>{
    b.innerHTML=ico(s.zustand==='spielt'?'pause':'play');
    b.title=s.zustand==='spielt'?'Pause':'Abspielen';});
  const sb=document.getElementById('plb-speed');
  if(sb)sb.textContent=(s.rate||1)+'×';
  // Selbstheilung: meldet libvlc FEHLER, einmal automatisch neu verbinden
  // (der Server baut die Instanz frisch); erst der zweite Fehler bleibt stehen.
  if(s.zustand==='fehler'&&s.key===aktKey()&&!vlcHeilt){vlcHeilt=true; vlcNeustart(); return;}
  if(s.zustand==='spielt')vlcHeilt=false;
  // Wiedergabe-Merker („wo war ich zuletzt") — derselbe Speicher wie im
  // Browser-Player (ytdl_pos_v1), gleicher 5-s-Takt; gemalt wird er von
  // posMerkerMalen über den normalen Leisten-Ticker.
  const mk=aktKey();
  if(mk&&s.dauer&&s.zustand==='spielt'&&Date.now()-_posMerkTs>5000){
    _posMerkTs=Date.now();
    if(s.pos>20&&s.pos<s.dauer-20)_posMerk[mk]={t:Math.floor(s.pos),ts:Date.now()};
    else if(s.pos>=s.dauer-20)delete _posMerk[mk];
    lsSchreiben('ytdl_pos_v1',JSON.stringify(_posMerk));
  }
  // Titelende: genau EINMAL weiterschalten (der Ended-Zustand bleibt in libvlc
  // stehen, bis etwas Neues spielt — ohne die Merker-Variable liefe die
  // Warteschlange bei leerem Ende im 1-s-Takt immer weiter).
  if(s.zustand==='ende'&&s.key&&s.key===aktKey()&&vlcEndeFuer!==s.key){
    vlcEndeFuer=s.key; if(!uiNeuLaden())playerAdvance();  // F10: vorgemerkter neuer Stand lädt statt weiter
  }
}
/* ---- Wiedergabe-Grundeinstellungen (Spec Punkt 5, Etappe C) --------------
   Drei Ebenen, jede schlägt die darüber (bestätigt 23.07.):
   global (Einstellungen) → je Playlist → je Titel. Änderungen am LAUFENDEN
   Titel merkt sich der Player für genau diesen Titel („absolut") — die
   Sitzungs-Standards (localStorage) bleiben die unterste Ebene, damit sich
   für Titel ohne eigene Regel nichts ändert. Ton-Sprache ist vorbereitet
   und greift, sobald der Film-Import Mehrspur-Dateien bringt. */
let subModeSitzung=subMode;
function wiedergabeFuer(x){
  const p=(playerState.plid&&((plState.find(q=>q.id===playerState.plid)||{}).wiedergabe))||{};
  const g=Object.assign({},(daten&&daten.config&&daten.config.wiedergabe)||{});
  const eigen=NUR_FERN?fernWahl().sub:'';              // Gerät im WLAN: seine Wahl statt des PC-Standards
  if(eigen)g.sub=eigen;
  const t=(x&&x.wiedergabe)||{};
  return {sub:t.sub||p.sub||g.sub||'', speed:t.speed||p.speed||g.speed||0, ton:t.ton||p.ton||g.ton||'',
          sub_offset:t.sub_offset||p.sub_offset||g.sub_offset||0};
}
function wiedergabeAnwenden(x,el){
  const w=wiedergabeFuer(x);
  const sub=w.sub||subModeSitzung;                     // keine Regel -> Sitzungs-Standard
  if(sub!==subMode){subMode=sub; subAnzeigen();}
  subOffset=w.sub_offset||0;                           // gemerkter Untertitel-Versatz je Titel
  const sp=w.speed||playSpeed;
  if(el)el.playbackRate=sp;
  const b=document.getElementById('plb-speed'); if(b)b.textContent=sp+'×';
}
function wiedergabeMerken(felder){
  const k=aktKey(); if(!k)return;                      // nichts läuft -> nichts zu merken
  const x=libFind(k); if(x)x.wiedergabe=Object.assign({},x.wiedergabe||{},felder);
  if(NUR_FERN)return;                                  // Gerät im WLAN: gilt nur hier, bis die Bibliothek neu lädt
  api('/api/wiedergabe',Object.assign({keys:[k],merge:1},felder)).catch(()=>{});
}
function speedWaehlen(s){playSpeed=s; speedAnwenden(); wiedergabeMerken({speed:s});
  if(vlcAktiv()){vlcRateLetzte=s; vlcBefehl('rate',{wert:s});}}
let wgZiel=null;
function wgGlobalDialog(){wiedergabeDialog({global:1},'Standard für alles ohne eigene Regel');}
function wiedergabeDialog(ziel,name){
  wgZiel=ziel;
  const w=ziel.plid?(((plState.find(p=>p.id===ziel.plid)||{}).wiedergabe)||{})
        :ziel.global?((daten&&daten.config&&daten.config.wiedergabe)||{})
        :(ziel.keys&&ziel.keys.length===1?(((libFind(ziel.keys[0])||{}).wiedergabe)||{}):{});
  const sopt=[['','— erben —'],['aus','aus'],['zeilen','Untertitel'],['karaoke','Karaoke'],['transkript','Transkript']];
  const vopt=[['','— erben —'],['0.5','0.5×'],['0.75','0.75×'],['1','1×'],['1.25','1.25×'],['1.5','1.5×'],['2','2×'],['3','3×']];
  const topt=[['','— egal —'],['de','Deutsch'],['en','Englisch'],['orig','Original']];
  const sel=(id,opt,akt)=>'<select id="'+id+'">'+opt.map(o=>'<option value="'+o[0]+'"'+
    (String(akt||'')===o[0]?' selected':'')+'>'+o[1]+'</option>').join('')+'</select>';
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML='<div class="modal-box" style="max-width:460px"><div class="modal-head"><b>🎚 Wiedergabe — '+esc(name)+'</b>'
    +'<button class="ib" title="Abbrechen" onclick="this.closest(\'.modal\').remove()">✕</button></div>'
    +'<div style="padding:14px 16px;display:flex;flex-direction:column;gap:9px">'
    +'<div class="optrow"><span>Untertitel / Karaoke</span>'+sel('wg-sub',sopt,w.sub)+'</div>'
    +'<div class="optrow"><span>Geschwindigkeit</span>'+sel('wg-speed',vopt,w.speed)+'</div>'
    +(ziel.global?'<div class="optrow"><span>Ton-Sprache (Mehrspur, vorbereitet)</span>'+sel('wg-ton',topt,w.ton)+'</div>':'')
    +'<div class="muted2" style="font-size:11.5px">„— erben —" = die Ebene darüber gilt: Titel → Playlist → global → Sitzung.'
    +(ziel.keys&&ziel.keys.length?' Ändert '+ziel.keys.length+' Titel.':'')+'</div>'
    +'</div><div style="padding:0 16px 16px;display:flex;gap:8px;justify-content:flex-end">'
    +'<button class="btn mini" data-nein>Abbrechen</button>'
    +'<button class="btn mini" data-ja style="background:var(--akz);border-color:var(--akz);color:#1b1512">Übernehmen</button>'
    +'</div></div>';
  ov.onclick=e=>{if(e.target===ov)ov.remove();};
  ov.querySelector('[data-nein]').onclick=()=>ov.remove();
  ov.querySelector('[data-ja]').onclick=()=>{wgSpeichern(); ov.remove();};
  document.body.appendChild(ov);
}
async function wgSpeichern(){
  const hol=id=>{const s=document.getElementById(id); return s?s.value:undefined;};
  const body=Object.assign({},wgZiel,{sub:hol('wg-sub')||'',speed:parseFloat(hol('wg-speed'))||0});
  const ton=hol('wg-ton'); if(ton!==undefined)body.ton=ton;
  await api('/api/wiedergabe',body);
  await Promise.all([libLaden(),plLaden(),laden()]);   // alle drei Ebenen frisch
  toast('🎚 Wiedergabe-Einstellungen gespeichert.');
}
/* ---- Medientasten der Tastatur ------------------------------------------
   Gemessen 23.09.2026 an der laufenden Oberfläche: `mediaSession.metadata` war
   null, `playbackState` stand auf 'none' — Windows kannte SyncYouTube gar nicht
   als Medienquelle. Zwei Folgen: „Titel weiter/zurück" wirkte NIE (auch nicht
   im Vordergrund), und lief nebenbei Spotify, gewann Spotify jeden Tastendruck.

   Der Grund ist eine Eigenheit des Webs, die viele überrascht: Medientasten
   kommen NICHT als normale Tastendrücke in einer Seite an. Der einzige Weg
   führt über die Media Session API. Play/Pause ist die Ausnahme, die Chrome
   für jedes spielende Medienelement selbst übernimmt — „nächster Titel" kann
   der Browser dagegen nicht raten, das weiß nur diese App.

   Live nachgemessen 23.09.2026 mit ECHTEN Tastendrücken (Tastatur-Scan-Codes
   per SendInput) und Windows' eigener Sitzungsliste: Edge, Firefox und die
   WebView2-Hülle melden sich an (Hülle als „msedgewebview2.exe"); Weiter,
   Zurück und Play/Pause wirken, auch wenn das Fenster hinten liegt. WELCHE
   App eine Taste bekommt, entscheidet Windows („aktuelle Sitzung"): eine neu
   entstehende Sitzung wird aktuell, danach behält Spotify sie, solange es
   spielt — und pausiert bei Play/Pause zusätzlich selbst mit.

   Eine Weiche, drei Ziele: Film offen -> Film (23.09.: „Film steuern +
   nächste Folge"; Musik läuft nie mehr unter dem Film los), Gerät VLC -> VLC
   über den Server, sonst das <audio>/<video>. Im Gerät VLC spielt der Ton
   außerhalb des Browsers, dann kennt Windows die SEITE nicht (gemessen) —
   darum meldet der SERVER den VLC selbst an (medien_smtc.py, pywinrt, Freigabe
   23.09.) und reicht Weiter/Zurück über jede /api/vlc-Antwort hierher
   (smtcTaste). */
/*MEDIEN_SESSION_JS*/
const medienS=medienSitzung(()=>document.getElementById('pl-el'));
/* Wem gehören die Tasten? Der Besitzer 23.09.2026: „Musik läuft weiter, die Tasten
   gehören dem Film." Solange die Film-Fernbedienung offen ist, führen Tastatur,
   keydown UND jede SyncYouTube-Kachel im Windows-Overlay zum Film — egal, ob er
   im Browser-Element oder im VLC läuft; die Browser-Kachel zeigt dann auch den
   Film (tvpMedienAn). Eine Zwischenfassung ließ die Browser-Kachel bei einem
   VLC-Film der Musik — dann entschied Windows' Wahl der „aktuellen Sitzung",
   ob eine Taste den Film oder die Musik traf (Gegenprüfung 24.09.). */
function filmTasten(){return !!tvpOffen;}
/* Gibt es eine SyncYouTube-Sitzung bei Windows, die eine Medientaste ohnehin
   bekommt? Echte Tastendrücke (24.09.2026) zeigten: Mit Fokus auf dem Fenster
   kommt die Taste ZWEIMAL an — über Windows UND als keydown. VLC-⏯ pausierte
   und die Seite schaltete sofort zurück, VLC-⏭ sprang zwei Titel, 2× ⏮ in der
   Serie wurden drei Schritte; die 400-ms-Sperre greift nicht, weil der
   Windows-Weg später ankommt. Die Seite ist bei Windows angemeldet, sobald
   eines ihrer Elemente mit Quelle Ton gespielt hat (Chromium meldet erst beim
   ersten Ton an und hält die Sitzung auch pausiert, bis freigeben() die Quelle
   nimmt); der VLC-Motor, solange der Server angemeldet ist (vlcSmtc). */
function medienTasteHatSitzung(){
  const sitzt=el=>!!(el&&el.src&&(!el.paused||(el.played&&el.played.length>0)));
  if(sitzt(document.getElementById('pl-el'))||sitzt(document.getElementById('tvp-video')))return true;
  // Ein abgelöstes Film-Video, das gespielt hat, hält die Sitzung, bis sein
  // Nachfolger spielt (tvpVideoTauschen) — auch wenn dessen play() scheiterte.
  if(tvpAbgeloest.some(el=>!!(el&&el.src&&el._tvpSpielte)))return true;
  return (filmTasten()?tvpModus!=='browser':vlcAktiv())&&!!vlcSmtc;
}
/* Dieselbe Taste darf nicht doppelt wirken, falls ein Browser sie ZUSÄTZLICH
   als keydown zustellt: gleiche Aktion aus der ANDEREN Quelle binnen 400 ms
   wird geschluckt. Zweimal schnell über denselben Weg bleibt erlaubt. */
let _medienLetzte={gruppe:'',quelle:'',t:0};
function medienEinmal(gruppe,quelle){
  const jetzt=Date.now(), l=_medienLetzte;
  if(l.gruppe===gruppe&&l.quelle!==quelle&&jetzt-l.t<400)return false;
  _medienLetzte={gruppe,quelle,t:jetzt}; return true;
}
function medienPlay(){
  if(filmTasten()){tvpMedien('play'); return;}
  // Gerät VLC: 'play' OHNE Titel scheitert am Server („Datei nicht gefunden") —
  // fortsetzen heißt dort umschalten, und nur, wenn er wirklich steht.
  if(vlcAktiv()){if(!vlcSpielt)plTogglePlay(); return;}
  const el=document.getElementById('pl-el'); if(el)el.play().catch(()=>{});
}
function medienPause(){
  if(filmTasten()){tvpMedien('pause'); return;}
  if(vlcAktiv()){vlcBefehl('pause'); return;}
  const el=document.getElementById('pl-el'); if(el)el.pause();
}
function medienSpringe(ev){
  if(!ev||typeof ev.seekTime!=='number')return;
  if(filmTasten()){tvpSpringeAuf(ev.seekTime); return;}
  if(vlcAktiv()){                                     // kein <audio> im VLC-Modus: über den Server
    if(!vlcDauerLetzte)return;
    vlcPosLetzte=Math.max(0,Math.min(vlcDauerLetzte,ev.seekTime));
    vlcBefehl('seek',{wert:vlcPosLetzte}); return;
  }
  const el=document.getElementById('pl-el'); if(el)el.currentTime=ev.seekTime;
}
function medienRelativ(s){
  if(filmTasten()){tvpRel(s); return;}
  plbSpringen(s,true);                                 // VLC-fähig und aufs Titelende begrenzt
}
function medienWeiter(){if(filmTasten()){tvpFolge(1); return;} playerNext();}
function medienZurueck(){if(filmTasten()){tvpZurueck(); return;} playerPrev();}
function _msPlay(){if(medienEinmal('pp','ms'))medienPlay();}
function _msPause(){if(medienEinmal('pp','ms'))medienPause();}
function _msWeiter(){if(medienEinmal('next','ms'))medienWeiter();}
function _msZurueck(){if(medienEinmal('prev','ms'))medienZurueck();}
let _medienAngemeldet=false;
function medienTastenAnmelden(neu){
  if(!navigator.mediaSession||(_medienAngemeldet&&!neu))return;
  _medienAngemeldet=true;
  medienS.aktionen({
    'play':_msPlay, 'pause':_msPause, 'stop':_msPause,
    'nexttrack':_msWeiter, 'previoustrack':_msZurueck,
    'seekto':ev=>medienSpringe(ev),
    'seekforward':ev=>medienRelativ((ev&&ev.seekOffset)||10),
    'seekbackward':ev=>medienRelativ(-((ev&&ev.seekOffset)||10))});
}
/* Was Windows im Overlay zeigt: Titel, Interpret, Cover. Interpret wie in der
   Bibliothek — Künstler-Feld, sonst der Kanal. Solange ein Film läuft, gehört
   das Overlay ihm: ein Musik-Titelwechsel im Hintergrund überschreibt es nicht
   (medienNachFilm holt die Musik danach zurück). Im Gerät VLC bekommt der
   Server dieselben Angaben für seine eigene Windows-Anmeldung. */
function medienInfoSetzen(x,k){
  if(!x||!navigator.mediaSession)return;
  medienTastenAnmelden();
  const cover='/api/cover?id='+encodeURIComponent(k);
  const m={title:x.titel||'', artist:x.kuenstler||x.uploader||'',
    album:x.album||(playerState&&playerState.quelle)||'',
    artwork:medienS.bilder([[cover,'512x512'],[x.thumb,'480x360']])};
  if(vlcAktiv()){                                      // Server-Kachel: auch bei offenem Film (sonst ohne Cover)
    vlcBefehl('medien',{key:k,titel:m.title,interpret:m.artist,album:m.album,cover,weiter:true,zurueck:true});
    _medienVlcGeraeumt=false;
  }
  if(filmTasten())return;                              // die Browser-Kachel zeigt gerade den Film
  if(vlcAktiv()&&vlcSmtc)return;                       // der Server zeigt den Titel — die Seite nicht doppelt
  medienS.info(m);
}
/* Zustand + Zeitleiste nachziehen, sonst zeigt das Overlay „Play", während
   pausiert ist. Film und VLC pflegen ihren Zustand im eigenen 1-s-Takt
   (tvpTick/vlcTick), das <audio> hier über seine Ereignisse. */
function medienZustand(s){
  if(filmTasten()||vlcAktiv())return;
  medienS.zustand(s);
}
/* Gerät VLC (aus vlcTick): gemessen 23.09. — ohne Spiegel blieb playbackState
   auf 'paused', Windows schickte bei Play/Pause deshalb immer „play", und VLC
   ließ sich per Taste nicht anhalten. Meldet der Server VLC selbst bei Windows
   an (smtc), räumt die Seite ihre Sitzung — sonst stünde SyncYouTube doppelt
   im Overlay. */
let _smtcTasteN=null, vlcSmtc=false, _medienVlcGeraeumt=false;
function medienVlcSpiegel(s){
  if(!s||filmTasten()||!vlcAktiv())return;
  if(s.smtc){if(!_medienVlcGeraeumt){medienS.leeren(); _medienVlcGeraeumt=true;} return;}
  if(s.key!==aktKey())return;                          // spielt der VLC gerade etwas anderes (Film), nichts spiegeln
  medienS.zustand(s.zustand==='spielt'?'playing':'paused',{dauer:s.dauer,pos:s.pos,rate:s.rate});
}
/* Windows-Knöpfe am Server-VLC (Vertrag mit medien_smtc.py): jede /api/vlc-
   Antwort trägt taste={n,was}. Der erste Stand wird nur gemerkt (kein
   Nachplappern nach dem Laden; ein kleinerer Zähler heißt: Server neu
   gestartet). Jeder Druck ist ein Schritt — zwei schnelle ⏭ sind zwei Titel.
   HANDELN darf nur die Seite, der das Gespielte gehört: jede offene Seite, die
   VLC abfragt, sieht denselben Zähler (Prüf-Befund 24.09.: ein zweiter Tab
   schaltete mit und übernahm den gemeinsamen VLC). */
async function smtcTaste(d){
  if(!d||typeof d!=='object')return;
  if(typeof d.smtc==='boolean')vlcSmtc=d.smtc;
  const t=d.taste; if(!t||typeof t.n!=='number')return;
  const vor=+t.vor||0, zur=+t.zurueck||0, alt=_smtcTasteN;
  _smtcTasteN={n:t.n, vor, zur};
  if(alt===null||t.n<alt.n||t.n===alt.n)return;      // erster Stand, Server neu gestartet, nichts Neues
  // Netto-Schritte: ⏭ und ein schnell folgendes ⏮ heben sich auf (Zähler je
  // Richtung, Gegenprüfung 24.09.); ein älterer Server kennt nur n + letzte Richtung.
  let netto=(typeof t.vor==='number'&&typeof t.zurueck==='number')?(vor-alt.vor)-(zur-alt.zur)
           :(t.n-alt.n)*(t.was==='next'?1:t.was==='prev'?-1:0);
  netto=Math.max(-5,Math.min(5,netto));
  if(!netto)return;
  const k=d.key||'', film=/^(film|live):/.test(k);
  const meins=film?(tvpOffen&&(k==='film:'+tvpIdAkt||(!tvpIdAkt&&k.startsWith('live:'))))
                  :!!(k&&vlcAktiv()&&k===aktKey());
  if(!meins)return;
  if(tvpOffen){                                        // die Tasten gehören dem Film (der Besitzer) — auch die Musik-Kachel
    for(let i=0;i<Math.abs(netto);i++)await (netto>0?tvpFolge(1):tvpZurueck());
    return;
  }
  playerSchritte(netto);
}
/* Nach dem Film gehört das Overlay wieder der Musik (oder niemandem). */
function medienNachFilm(){
  tvpMedienGen++;                                      // späte Film-Antworten verwerfen
  medienTastenAnmelden(true);                          // alle Musik-Knöpfe zurück (der Film blendete evtl. Weiter aus)
  const k=aktKey(), x=k?libFind(k):null;
  if(!x){medienS.leeren(); return;}
  medienInfoSetzen(x,k);
  const el=document.getElementById('pl-el');
  if(el)medienZustand(el.paused?'paused':'playing');
}

