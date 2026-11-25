/* ================= Player, Fortsetzung: Bild-in-Bild und Wiedergabe-Merker ================= */
function plbPip(){                                     // natives Bild-in-Bild (21.07.)
  const el=document.getElementById('pl-el');
  if(!el||el.tagName!=='VIDEO'){toast('Bild-in-Bild geht nur bei Videos.');return;}
  const istFirefox=/firefox/i.test(navigator.userAgent);
  try{
    if(document.pictureInPictureElement)document.exitPictureInPicture();
    else if(el.requestPictureInPicture&&document.pictureInPictureEnabled!==false)el.requestPictureInPicture();
    else if(istFirefox)toast('Firefox: nutze den kleinen Bild-in-Bild-Knopf, der beim Überfahren am Video erscheint (die Schnittstelle ist per Knopf gesperrt).');
    else toast('Dein Browser kann kein Bild-in-Bild.');
  }catch(e){
    toast(istFirefox?'Firefox: nutze den eigenen Bild-in-Bild-Knopf am Video (rechts am Rand beim Überfahren).'
                    :'Bild-in-Bild nicht möglich.');
  }
}
/* ---- Wiedergabe-Merker (Build 102, der Besitzer): je Titel die letzte Stelle merken.
   Gelber Strich auf der Leiste zeigt sie, KLICK springt hin — standardmäßig
   wirkt der Merker NICHT (jeder Titel startet normal bei 0). Anfang (<20 s)
   und fast-Ende löschen den Merker; Deckel 800 Einträge (älteste fliegen). */
let _posMerk={}; try{_posMerk=JSON.parse(localStorage.getItem('ytdl_pos_v1'))||{};}catch(e){}
let _posMerkTs=0;
function posMerken(){
  const el=document.getElementById('pl-el'); const k=aktKey();
  if(!el||!k||!isFinite(el.duration)||!el.duration)return;
  const t=el.currentTime;
  // Build 104 (Fund „sehe den Strich nicht"): am ANFANG (<20 s) den Merker
  // IN RUHE lassen — nach jedem Titelwechsel steht man zwangslaeufig bei 0,
  // und der 5-s-Takt loeschte den Merker genau dann, bevor man ihn je sah.
  // Geloescht wird nur noch am fast-Ende (durchgehoert = Merker sinnlos).
  if(t>20&&t<el.duration-20)_posMerk[k]={t:Math.floor(t),ts:Date.now()};
  else if(t>=el.duration-20)delete _posMerk[k];
  const keys=Object.keys(_posMerk);
  if(keys.length>800)keys.sort((a,b)=>(_posMerk[a].ts||0)-(_posMerk[b].ts||0))
    .slice(0,keys.length-800).forEach(x=>delete _posMerk[x]);
  lsSchreiben('ytdl_pos_v1',JSON.stringify(_posMerk));
}
window.addEventListener('beforeunload',posMerken);
function posMerkerMalen(){
  const seek=document.getElementById('plb-seek'); const wrap=seek&&seek.parentElement;
  if(!wrap)return;
  let m=document.getElementById('plb-merker');
  const el=document.getElementById('pl-el'); const k=aktKey();
  const eintrag=k&&_posMerk[k];
  // Gerät VLC (identische Leiste): Dauer/Position aus dem 1-s-Status.
  const vlc=vlcAktiv();
  const dauer=vlc?vlcDauerLetzte:(el&&isFinite(el.duration)?el.duration:0);
  const pos=vlc?vlcPosLetzte:(el?el.currentTime:0);
  const nah=eintrag&&dauer&&Math.abs(pos-eintrag.t)<3;   // Playhead klebt drauf -> ausblenden
  if(!eintrag||!dauer||nah){if(m)m.remove();return;}
  if(!m){
    m=document.createElement('div'); m.id='plb-merker'; m.className='plb-merker';
    m.addEventListener('click',e=>{e.stopPropagation();
      const el2=document.getElementById('pl-el'), k2=aktKey();
      if(!k2||!_posMerk[k2])return;
      const ziel=Math.max(0,_posMerk[k2].t-3);           // 3 s Anlauf (Build 105)
      if(vlcAktiv()){vlcPosLetzte=ziel; vlcBefehl('seek',{wert:ziel});}
      else if(el2)el2.currentTime=ziel;
      toast('↦ zurück zu '+zeit(_posMerk[k2].t)+' (mit Anlauf)');});
    wrap.appendChild(m);
  }
  const sr=seek.getBoundingClientRect(), wr=wrap.getBoundingClientRect();
  m.style.left=(sr.left-wr.left+sr.width*(eintrag.t/dauer))+'px';
  m.title='Zuletzt warst du hier: '+zeit(eintrag.t)+' — Klick springt hin';
}
function plbTick(){                                    // Position/Zeit der Leiste nachführen
  const s=document.getElementById('plb-seek'),
        t0=document.getElementById('plb-t0'), t1=document.getElementById('plb-t1');
  if(!s||!t0||!t1)return;
  if(Date.now()-_posMerkTs>5000){_posMerkTs=Date.now(); posMerken();}   // Merker-Takt (Build 102)
  posMerkerMalen();
  const st=spulStand();                               // Browser oder Gerät VLC (1-s-Status)
  if(!st.dauer){s.value=0;t0.textContent='0:00';t1.textContent='0:00';return;}
  if(!plbSeekAktiv){s.value=Math.round(st.pos/st.dauer*1000);t0.textContent=zeit(st.pos);}
  t1.textContent=zeit(st.dauer);
}
setInterval(plbTick,500);
function speedMenu(ev){                                // Geschwindigkeit als Liste (Haken = aktiv)
  ev.stopPropagation();
  kmListe(kontextMenuBauen(ev,[]),'⚡ Geschwindigkeit',
    [0.5,0.75,1,1.25,1.5,2].map(s=>[s+'×', s===playSpeed, ()=>speedWaehlen(s)]));
}
function plBarIdleInit(media,el){                      // Leiste ruht die Maus -> ausblenden (nur beim Abspielen)
  clearTimeout(plbIdleTimer);
  media.classList.remove('baridle');
  const wecken=()=>{media.classList.remove('baridle'); clearTimeout(plbIdleTimer);
    plbIdleTimer=setTimeout(()=>{if(!el.paused)media.classList.add('baridle');},3000);};  // Vorgabe: „weg nach ~3 s"
  media.onpointermove=wecken;
  media.onpointerleave=()=>{if(!el.paused)media.classList.add('baridle');};
  el.addEventListener('pause',()=>media.classList.remove('baridle'));
  wecken();
}

