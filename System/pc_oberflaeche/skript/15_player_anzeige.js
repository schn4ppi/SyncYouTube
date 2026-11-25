/* ================= Player-Anzeige und Ad-hoc-Playlist ================= */
function renderPlayerMedia(){
  const media=document.getElementById('pl-media'); if(!media)return;
  spulStopp();                                         // Titelwechsel beendet den Spul-Modus
  const k=aktKey(), x=libFind(k);
  const altEl=document.getElementById('pl-el');        // wird gleich ersetzt -> danach freigeben
  if(!x){
    media.innerHTML='<div class="pl-leer">Kein Titel.</div>';
    medienS.freigeben(altEl);
    // Wiedergabe endet (Liste geleert, letzter Titel entfernt): nichts darf
    // unsichtbar weiterspielen, und Windows darf keinen Titel mehr zeigen.
    // Befund 23.09.: ein laufender Crossfade und VLC spielten weiter (VLC ohne
    // Titel ist über die Oberfläche nicht mehr anzuhalten), das Overlay zeigte
    // den alten Titel.
    xfAbbrechen(); if(plGeraet==='vlc')vlcBefehl('stop');
    // Übernahme-Element (Blende in einen Titel, der inzwischen aus der
    // Bibliothek verschwand, z. B. Radio): es spielt schon — freigeben.
    if(adoptEl){medienS.freigeben(adoptEl); adoptEl=null;}
    if(!filmTasten())medienS.leeren();
    return;
  }
  const uebernahme=(adoptEl&&adoptEl._key===k)?adoptEl:null;
  if(adoptEl&&!uebernahme)medienS.freigeben(adoptEl);  // verworfen: spielt es schon, nie verwaist weiterlaufen lassen
  adoptEl=null;
  if(!uebernahme)xfAbbrechen();                        // normaler Wechsel -> evtl. laufenden Fade verwerfen
  const src='/media?id='+encodeURIComponent(k);
  try{api('/api/played',{id:k});}catch(e){}
  // Nach der WIRKLICH servierten Datei entscheiden (dateiart vom Server):
  // fehlt das Video und es gibt nur die MP3, gehört die Audio-Ansicht
  // (Cover+Visualizer) her — statt schwarzem Video-Element (14.07.).
  const istAudio=x.dateiart?x.dateiart==='audio':((x.kategorie==='MP3')||(!x.vcodec&&x.acodec));
  // Der Besitzer 05.08.: „warum öffnet sich ein neues Fenster mit VLC?" — im BROWSER
  // kann VLC sein Bild nicht einbetten (kein Fenster-Handle über Webseiten).
  // Darum spielt ein VIDEO ohne Hülle im Browser-Element (eingebettet, wie
  // erwartet); Audio bleibt am Gerät VLC (braucht kein Fenster). In der
  // PROGRAMM-HÜLLE rendert VLC eingebettet ins eigene Fenster (set_hwnd).
  const vlcHier=plGeraet==='vlc'&&(istAudio||!!window.pywebview);
  if(!vlcHier&&plGeraet==='vlc')vlcBefehl('stop');     // Fund: sonst spielt VLC-Audio unterm Browser-Video weiter
  if(vlcHier){                                         // Gerät „VLC": Motor auf dem PC statt <audio>/<video>
    xfAbbrechen();                                     // Crossfade gehört dem Browser-Element
    renderPlayerVlc(media,x,k);
  }else if(istAudio){
    // Etappe A (Spec Punkt 5): erst das ECHTE eingebettete Album-Cover
    // (/api/cover); gibt es keins (404), fällt das Bild aufs YouTube-Thumbnail
    // zurück — und erst wenn auch das fehlt, verschwindet es.
    const t=x.thumb
      ?`<img class="pl-cover" src="/api/cover?id=${encodeURIComponent(k)}" style="cursor:pointer" data-fb="${esc(x.thumb)}" onerror="this.onerror=function(){this.style.display='none'};this.src=this.dataset.fb">`
      :`<img class="pl-cover" src="/api/cover?id=${encodeURIComponent(k)}" style="cursor:pointer" onerror="this.style.display='none'">`;
    media.innerHTML=`<canvas id="pl-viz" class="pl-viz"></canvas><div class="pl-vizwrap">${t}</div>`+
      `<div class="pl-subzeile" id="pl-sub-anzeige" style="display:none"></div>`+plBarHTML(false)+
      (uebernahme?'':`<audio id="pl-el" autoplay src="${src}"></audio>`);
    if(uebernahme){uebernahme.id='pl-el'; uebernahme.controls=false; uebernahme.className=''; media.appendChild(uebernahme);}
  }else{
    xfAbbrechen();                                     // Video: kein Crossfade
    media.innerHTML=`<video id="pl-el" autoplay src="${src}"></video>`+
      `<div class="pl-subzeile" id="pl-sub-anzeige" style="display:none"></div>`+plBarHTML(true);
  }
  const el=document.getElementById('pl-el');
  // Das abgelöste Element löst seine Quelle — sonst hält es Windows' Eintrag
  // (gemessen: „YouTube-Downloader (pausiert)" neben der VLC-Sitzung).
  if(altEl&&altEl!==el)medienS.freigeben(altEl);
  // Übernahme nicht eingehängt (Titel spielt am Gerät VLC oder als Video): freigeben statt verwaist weiterlaufen lassen.
  if(uebernahme&&uebernahme!==el)medienS.freigeben(uebernahme);
  if(el){
    // Ende: vorbereiteten Nachfolger übernehmen, wenn er noch dran ist, sonst normal weiter
    el.addEventListener('ended',plTitelEnde);
    // Play/Pause-Symbol überall sofort nachziehen (05.08.) — cmdNow malt
    // die Kopfzeile, transportRender die data-tr-Knöpfe der Player-Leiste.
    el.addEventListener('play',()=>{cmdNowRender(); transportRender(); if(el.isConnected)medienZustand('playing');});
    el.addEventListener('pause',()=>{
      cmdNowRender(); transportRender();
      if(!el.isConnected)return;                         // abgelöstes Element (Titelwechsel) meldet nichts mehr
      medienZustand('paused');
      // Pause mitten in einer Überblendung (Taste, Klick, Overlay): das nächste
      // Element spielte abgekoppelt weiter und wurde dabei lauter. Übergang
      // abbrechen, Lautstärke zurück — beim Weiterspielen startet uebergangTick
      // ihn mit der Restzeit neu. Gapless ist nicht betroffen (dort wartet xfNext).
      if(!el.ended&&xfNext&&!xfNext.paused)xfZuruecknehmen(el);
    });
    // Zeitleiste im Overlay: nach Sprüngen (Overlay-Regler, Pfeile, Kapitel,
    // Leiste) und Tempowechseln rechnete Windows mit der alten Stelle weiter —
    // setPositionState lief nur bei play/pause (Befund 23.09.).
    ['seeked','ratechange','durationchange'].forEach(t=>el.addEventListener(t,()=>{
      if(!el.isConnected)return;
      // Zurück aus dem Überblend-Fenster gesprungen: sonst hört man den NÄCHSTEN
      // Titel, während der alte stumm weiterläuft.
      if(t==='seeked'&&el._xf&&el.duration-el.currentTime>crossfadeSek+0.5)xfZuruecknehmen(el);
      medienZustand(el.paused?'paused':'playing');
    }));
    el.addEventListener('timeupdate',()=>subTick(el));   // Untertitel/Karaoke mitlaufen lassen
    el.addEventListener('play',()=>karLauf(el));         // Karaoke-Wischer im Bildtakt (Build 115)
    if(istAudio)el.addEventListener('timeupdate',()=>uebergangTick(el));   // Gapless/Crossfade/Automix
    try{el.volume=plVol/100;}catch(e){}                   // gemerkte Lautstärke anwenden
    // Klick IRGENDWO in die Player-Fläche = Pause/Play (unsere Leiste ausgenommen)
    media.onclick=ev=>{
      if(ev.target.closest&&ev.target.closest('.pl-bar'))return;
      if(el.paused)el.play(); else el.pause();
    };
    plBarIdleInit(media,el);                              // Leiste blendet bei Maus-Ruhe aus (YouTube-Stil)
    seitenverhaeltnisAnwenden();                          // Build 130: 16:9 fest (der Besitzer)
  }
  if(el && istAudio){ vizVerbinde(el); vizFarbeAktualisieren(); vizModeRender(); vizStart(); }
  else{ media.classList.remove('viz-an'); }             // Video: kein Visualizer-Overlay
  document.getElementById('pl-titel').textContent=x.titel;
  medienInfoSetzen(x,k);                               // Windows-Overlay + Medientasten
  document.getElementById('pl-pos').textContent=(playerState.idx+1)+' / '+playerState.queue.length;
  lieblingMalen();                                     // ＋/✓ folgt dem laufenden Titel (Build 144d)
  renderPlayerQueue();
  playerLayoutSet();
  cmdNowRender();
  speedAnwenden();                                     // Geschwindigkeit auf neues Element anwenden
  wiedergabeAnwenden(x,el);                            // Etappe C: Titel/Playlist/global-Regeln obendrauf
  // Crossfade/Automix übernimmt ein Element, das SCHON spielt: es feuert kein
  // 'play' mehr, und das 'pause' des alten Titels hatte 'paused' gemeldet.
  if(uebernahme&&el)medienZustand(el.paused?'paused':'playing');
  renderKapitel(x);                                    // YouTube-Kapitel als Sprungmarken
  subLaden(k);                                         // Untertitel für den neuen Titel holen
  canvasAnwenden();                                    // animierter Cover-Hintergrund (falls an)
}
function plQueueKlick(i){
  if(i===playerState.idx){                             // schon aktiv -> Pause/Play statt Neustart
    if(vlcAktiv()){plTogglePlay(); return;}
    const el=document.getElementById('pl-el'); if(el){if(el.paused)el.play(); else el.pause();}
    return;
  }
  playerState.idx=i; renderPlayerMedia();
  // Fokus überlebt das Neu-Rendern (Sicht-Check 22.07.): nach Enter/Doppelklick sonst
  // Fokus weg -> Entf/Pfeile brauchten erst wieder einen Klick in die Liste.
  plqSel=i; plqMark(); plqFocus(i);
}
/* Player-Warteschlange: Einträge umsortieren (HTML5-Drag) + Titel aus der
   Bibliothek hineinziehen (13.07.: „aus der Bibliothek in die Playlist schieben") */
let plqVon=null;
// Playlist-Bedienung (22.07.): Einfachklick WÄHLT nur, Doppelklick/Enter spielt,
// Entf löscht, ↑/↓ bewegen die Auswahl. plqSel = markierter Eintrag (Index).
let plqSel=null;
function plqFocus(i){                                  // nur den SICHTBAREN Eintrag fokussieren
  document.querySelectorAll('.pl-queue .pl-item[data-i="'+i+'"]').forEach(el=>{if(el.offsetParent)el.focus();});}
// Auswahl NUR per Klasse markieren, NICHT neu rendern: sonst würde der Einfachklick das
// Element ersetzen und der Doppelklick (zwei Klicks auf DASSELBE Element) fiele aus (22.07.).
// Build 144 (live gemessen): 'sel' hat ZWEI Quellen — den Fokus-Eintrag
// plqSel und die Mehrfachauswahl plqAuswahl. plqMark kannte nur die erste und
// wischte deshalb jede gerade gezogene Rahmen-Auswahl beim Loslassen wieder
// weg (dasselbe galt fuer den Strg-Klick). renderPlayerQueue fragt beide ab —
// hier stand die zweite Wahrheit. Es gibt nur eine.
function plqMark(){document.querySelectorAll('.pl-queue .pl-item').forEach(el=>{
  const i=+el.dataset.i; el.classList.toggle('sel', plqAuswahl.has(i)||i===plqSel);});}
/* ---- Rahmen-Auswahl in der Playlist (Build 139, der Besitzer Punkt 4) --------------
   Vorgabe: „Ich wuerde gerne auch in der Playlist wieder wie in Windows mehrere
   Titel mit der Maus markieren koennen (Maus macht ein Viereck und
   markiert)." Dasselbe Muster wie in der Bibliothek und im Abo-Fenster,
   damit es sich ueberall gleich anfuehlt: ab 5 px wird es ein Band, Strg
   erweitert, der nachlaufende Klick wird geschluckt.
   Unterschied zur Bibliothek: die Zeilen sind ZIEHBAR (Umsortieren), also
   startet das Band nur auf freier Flaeche — sonst koennte man nicht mehr
   umsortieren. */
let plqAuswahl=new Set(), plqBandLief=false;
function plqSelect(i,ev){
  if(plqBandLief)return;                               // Ende eines Band-Zugs
  if(ev&&(ev.ctrlKey||ev.metaKey)){                    // Strg: dazu/weg
    if(plqAuswahl.has(i))plqAuswahl.delete(i); else plqAuswahl.add(i);
  }else if(ev&&ev.shiftKey&&plqSel!==null){            // Umschalt: Bereich
    const a=Math.min(plqSel,i), b=Math.max(plqSel,i);
    for(let j=a;j<=b;j++)plqAuswahl.add(j);
  }else plqAuswahl.clear();
  plqSel=i; plqMark(); plqFocus(i);
}
/* Build 144 — warum der Rahmen bis hierher nie zu sehen war (dreimal:
   „Ich kann im Player immer noch kein Fenster mit der Maus ziehen"):
   Build 139 hatte das Muster der BIBLIOTHEK uebernommen — dort startet das
   Band nur auf freier Flaeche, damit die ziehbaren Kacheln ziehbar bleiben,
   und zwischen Kacheln ist reichlich Luft. Die Playlist ist aber eine LISTE
   und hat diese Luft NIE: am echten Fenster gemessen ist .pl-queue bei 14
   Titeln randvoll (362 px Inhalt in 150 px Sicht) und schrumpft bei 3 Titeln
   auf exakt ihre Zeilenhoehe (76 px) — freie Hoehe 0 px in beiden Faellen,
   weil die Liste mit ihrem Inhalt waechst. Jeder Punkt lag auf einer Zeile,
   also stieg plqBandStart immer sofort aus.
   Jetzt wie im Explorer: eine MARKIERTE Zeile greift man zum Verschieben, auf
   jeder anderen zieht man einen Rahmen auf. Damit bleiben beide Gesten heil,
   ohne neue Bedienzone. Wer das alte Verhalten will, stellt „nur auf freier
   Flaeche" ein (⚙ Ansicht → Playlist-Rahmen). */
function plqRahmenArt(){
  let v=lsLesen('ytdl_plqrahmen')||'auto';
  return v==='frei'?'frei':'auto';
}
function plqRahmenArtSetzen(v){
  lsSchreiben('ytdl_plqrahmen',v==='frei'?'frei':'auto');
  toast(v==='frei'?'▭ Rahmen nur auf freier Fläche (Ziehen hat überall Vorrang).'
                  :'▭ Rahmen ab der Zeile — markierte Titel bleiben zum Verschieben greifbar.');
}
let plqBandModus=false;                                // laeuft gerade ein Band auf einer Zeile?
let plqZugLaeuft=false;                                // ein Zug ist unterwegs (Zuhoerer haengt an ZWEI Ebenen)
function plqBandStart(ev){
  if(ev.button!==0)return;
  if(plqZugLaeuft)return;                              // sonst entstuenden zwei Baender uebereinander
  if(ev.target.closest('button,a,input,select'))return;
  if(ev.target.closest('.pl-media'))return;            // auf dem Video kein Band (eigene Steuerung, Drop-Ziel)
  const zeile=ev.target.closest('.pl-item');
  if(zeile){
    if(plqRahmenArt()==='frei')return;                 // Einstellung: Ziehen hat Vorrang
    if(zeile.classList.contains('sel'))return;         // markiert = greifen und verschieben
    // Ab hier gilt der Rahmen — der native HTML5-Drag muss schweigen, sonst
    // frisst er die Bewegung, aus der das Band entsteht (plqDragStart).
    plqBandModus=true;
  }
  /* Build 144c (nach der echten Maus-Probe): „wie in bibliothek soll der
     fenster ziehen modus in player/playlist schon ein/zwei reihen darueber
     funktionieren koennen." Der Zuhoerer haengt deshalb zusaetzlich am
     BEHAELTER ueber der Liste — genau wie in der Bibliothek seit Build 143.
     Getroffen und gescrollt wird aber weiter die LISTE, nicht der Behaelter:
     sonst schoebe das Rand-Nachschieben am falschen Element. */
  const behaelter=ev.currentTarget;
  const flaeche=behaelter.classList.contains('pl-queue')
    ? behaelter : [...behaelter.querySelectorAll('.pl-queue')].find(n=>n.offsetParent);
  // Ohne SICHTBARE eigene Liste kein Band: ein Panel kann mehrere Ansichten
  // tragen (Reiter), und der Zuhoerer am panel-body wuerde sonst in Ansicht A
  // einen Rahmen ueber Ansicht B ziehen.
  if(!flaeche)return;
  plqZugLaeuft=true;
  const basis=new Set(ev.ctrlKey||ev.metaKey?[...plqAuswahl]:[]);
  const x0=ev.clientX, y0=ev.clientY; let band=null;
  function mv(e){
    if(!band){
      if(Math.abs(e.clientX-x0)<5&&Math.abs(e.clientY-y0)<5)return;
      // Build 143 (Bild): Ohne das hier markiert der Browser beim
      // Aufziehen den TEXT der Kacheln mit (blau hinterlegt) — der
      // Rahmen soll aber Titel waehlen, nicht Buchstaben.
      document.body.classList.add('nosel');
      band=document.createElement('div'); band.className='abo-band'; document.body.appendChild(band);
    }
    const l=Math.min(x0,e.clientX), t=Math.min(y0,e.clientY),
          r=Math.max(x0,e.clientX), b=Math.max(y0,e.clientY);
    band.style.left=l+'px'; band.style.top=t+'px';
    band.style.width=(r-l)+'px'; band.style.height=(b-t)+'px';
    const fr=flaeche.getBoundingClientRect();
    if(e.clientY>fr.bottom-18)flaeche.scrollTop+=14;
    else if(e.clientY<fr.top+18)flaeche.scrollTop-=14;
    plqAuswahl=new Set(basis);
    flaeche.querySelectorAll('.pl-item').forEach(n=>{
      const q=n.getBoundingClientRect();
      if(q.left<r&&q.right>l&&q.top<b&&q.bottom>t)plqAuswahl.add(+n.dataset.i);
      n.classList.toggle('sel',plqAuswahl.has(+n.dataset.i));
    });
  }
  function up(){
    document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
    document.body.classList.remove('nosel'); plqBandModus=false; plqZugLaeuft=false;
    if(band){band.remove(); plqBandLief=true; setTimeout(()=>{plqBandLief=false;},0); plqMark();}
    else if(!zeile&&!basis.size&&(plqAuswahl.size||plqSel!==null)){
      // Kleinkram 05.08. (wie Bibliothek Build 142): ein KLICK auf freie
      // Fläche (kein Zug) räumt die Playlist-Auswahl ab — Explorer-Muster.
      // Mit Strg (basis gefüllt) bleibt sie erhalten.
      plqAuswahl.clear(); plqSel=null; plqMark();
    }
  }
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
}
function plqAuswahlLoeschen(){
  // Mehrere auf einmal entfernen: von HINTEN nach vorn, sonst verschieben
  // sich die Indizes unter den noch zu loeschenden Eintraegen weg.
  if(!plqAuswahl.size){plqRemove(plqSel!==null?plqSel:playerState.idx); return;}
  [...plqAuswahl].sort((a,b)=>b-a).forEach(i=>plqRemove(i));
  plqAuswahl.clear(); plqMark();
}
function plqMoveSel(d){
  if(!playerState.queue.length)return;
  plqSel = plqSel===null ? 0 : Math.max(0, Math.min(playerState.queue.length-1, plqSel+d));
  plqMark(); plqFocus(plqSel);}
function plqRemove(i){                                 // Titel aus der Ad-hoc-Playlist nehmen — auch den LAUFENDEN
  if(i===null||i<0||i>=playerState.queue.length)return;
  const warAktuell=(i===playerState.idx);             // wird der gerade laufende Titel entfernt?
  const curKey=aktKey();                               // laufenden Titel über den Umbau retten
  playerState.queue.splice(i,1);
  if(!playerState.queue.length){                       // Liste leer -> Wiedergabe endet
    plqSel=null; playerState.idx=-1;
    renderPlayerQueue(); renderPlayerMedia(); cmdNowRender(); return;
  }
  if(warAktuell){
    // Der Besitzer 22.07.: den laufenden Titel entfernen = er ist „beendet". Der nachrückende
    // Titel übernimmt (wie ein Titel-Ende); war es der letzte, endet die Wiedergabe.
    if(i<playerState.queue.length){                    // es gab einen nächsten -> der läuft weiter
      playerState.idx=i; plqSel=i;
      renderPlayerQueue(); renderPlayerMedia();
    }else{                                             // war der letzte -> Wiedergabe endet (Media wird geleert)
      playerState.idx=-1; plqSel=playerState.queue.length-1;
      renderPlayerQueue(); renderPlayerMedia(); cmdNowRender();
    }
    // Fokus-Restore auch HIER (Sicht-Check 22.07.): sonst braucht die Tastatur nach dem
    // Entfernen des laufenden Titels wieder einen Klick (gleicher Tick-Trick wie unten).
    if(plqSel!==null)setTimeout(function(){plqFocus(plqSel);},0);
    return;
  }
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));   // anderer Titel raus -> laufender spielt ungestört weiter
  plqSel=Math.min(i, playerState.queue.length-1);
  renderPlayerQueue();
  // Fokus einen Tick SPÄTER zurückholen (Sicht-Check 22.07.): der Browser setzt den
  // Fokus nach dem Handler auf body, weil das fokussierte Element entfernt wurde —
  // sofortiges focus() wird davon überschrieben; erst dann greifen Entf/Pfeile erneut.
  if(plqSel!==null)setTimeout(function(){plqFocus(plqSel);},0);
}
function plqVerschieben(i,d){                          // einen Titel im Rechtsklick-Menü hoch/runter schieben
  const j=i+d; if(j<0||j>=playerState.queue.length)return;
  const curKey=aktKey();
  const [t]=playerState.queue.splice(i,1);
  playerState.queue.splice(j,0,t);
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));   // laufender Titel behält seinen Platz
  plqSel=j; renderPlayerQueue(); plqFocus(j);
}
function plItemKontext(ev,i){                          // Rechtsklick auf einen Playlist-Titel (22.07.)
  ev.preventDefault(); ev.stopPropagation();           // nicht zum Karten-Menü (#pl-card) durchblubbern
  const k=playerState.queue[i]; if(k===undefined)return false;
  const x=libFind(k)||{};
  const eintraege=[];
  eintraege.push([i===playerState.idx?'⏯ Pause / Weiter':'▶ Abspielen', ()=>plQueueKlick(i)]);
  if(i!==playerState.idx)eintraege.push(['⏭ Als Nächstes abspielen', ()=>queueAlsNaechstes(k)]);
  if(i>0)eintraege.push(['⏫ Nach oben', ()=>plqVerschieben(i,-1)]);
  if(i<playerState.queue.length-1)eintraege.push(['⏬ Nach unten', ()=>plqVerschieben(i,1)]);
  eintraege.push([i===playerState.idx?'✖ Entfernen (Titel endet)':'✖ Aus Playlist entfernen', ()=>plqRemove(i)]);
  eintraege.push(['ℹ Eigenschaften…', ()=>eigenschaften(k)]);
  if(x.vorhanden)eintraege.push(nurPc(['📁 Im Ordner zeigen', ()=>biblio(k,'ordner')]));
  if(x.url)eintraege.push(['↗ Auf YouTube öffnen', ()=>window.open(x.url,'_blank','noreferrer')]);
  kontextMenuBauen(ev, eintraege);
  return false;
}
/* Warteschlangen-Aktionen (22.07., Muster Spotify „Add to queue/Play next"
   + MusicBee „Queue Next/Last"): einen Bibliotheks-/Playlist-Titel direkt HINTER
   den laufenden setzen bzw. ANS ENDE hängen. Läuft nichts, spielt er sofort.
   Ist er schon in der Queue, wird er verschoben (keine Dublette). */
function queueAlsNaechstes(key){
  const x=libFind(key); if(!x||!x.vorhanden){toast('Titel ist nicht (mehr) auf der Platte.');return;}
  ensurePlayer();
  if(playerState.idx<0||!playerState.queue.length){playerPlay([key]); return;}   // nichts läuft -> sofort
  const cur=aktKey(); if(key===cur)return;                                        // ist schon der laufende
  const vorhanden=playerState.queue.indexOf(key);
  if(vorhanden>=0)playerState.queue.splice(vorhanden,1);                          // erst raus -> keine Dublette
  const at=Math.max(0, playerState.queue.indexOf(cur))+1;                         // hinter den laufenden
  playerState.queue.splice(at,0,key);
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); cmdNowRender();
  toast('⏭ Als Nächstes: „'+((x.titel||key).slice(0,40))+'"');
}
function queueAnsEnde(key){
  const x=libFind(key); if(!x||!x.vorhanden){toast('Titel ist nicht (mehr) auf der Platte.');return;}
  ensurePlayer();
  if(playerState.idx<0||!playerState.queue.length){playerPlay([key]); return;}
  const cur=aktKey(); if(key===cur)return;
  const vorhanden=playerState.queue.indexOf(key);
  if(vorhanden>=0)playerState.queue.splice(vorhanden,1);
  playerState.queue.push(key);
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); cmdNowRender();
  toast('➕ Ans Ende: „'+((x.titel||key).slice(0,40))+'"');
}
/* Warteschlangen-Werkzeuge (22.07., Muster foobar/MusicBee): die aktuelle
   Ad-hoc-Playlist als benannte Playlist speichern, sortieren, umkehren,
   Duplikate entfernen, leeren. Der laufende Titel behält über alle Umbauten
   seinen Platz (curKey-Rettung). */
async function queueAlsPlaylist(){
  if(!playerState.queue.length){toast('Die Warteschlange ist leer.');return;}
  const n=prompt('Name der neuen Playlist:'); if(!n||!n.trim())return;
  const keys=playerState.queue.slice();
  const id=await plAnlegen(n.trim()); if(!id){toast('Konnte die Playlist nicht anlegen.');return;}
  for(const k of keys){                                // Backend-add nimmt einen Key; Reihenfolge bleibt
    await api('/api/playlist',{art:'add',id,key:k});
  }
  await plLaden();
  toast('💾 „'+n.trim()+'" gespeichert ('+keys.length+' Titel).');
}
function queueSortieren(art){
  if(playerState.queue.length<2)return;
  const cur=aktKey();
  const val=({titel:k=>((libFind(k)||{}).titel||k).toLowerCase(),
              dauer:k=>((libFind(k)||{}).dauer||0),
              datum:k=>((libFind(k)||{}).upload_date||'')})[art]||(k=>k);
  playerState.queue.sort((a,b)=>{const va=val(a),vb=val(b); return va<vb?-1:(va>vb?1:0);});
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); toast('↕ Sortiert nach '+({titel:'Titel',dauer:'Dauer',datum:'Datum'}[art]||art)+'.');
}
function queueUmkehren(){
  if(playerState.queue.length<2)return;
  const cur=aktKey(); playerState.queue.reverse();
  playerState.idx=Math.max(0, playerState.queue.indexOf(cur));
  renderPlayerQueue(); toast('↕ Reihenfolge umgekehrt.');
}
function queueDuplikate(){
  const cur=aktKey(), seen=new Set(), neu=[];
  playerState.queue.forEach(k=>{if(!seen.has(k)){seen.add(k); neu.push(k);}});
  const weg=playerState.queue.length-neu.length;
  if(!weg){toast('Keine Dubletten in der Warteschlange.');return;}
  playerState.queue=neu; playerState.idx=Math.max(0, neu.indexOf(cur)); plqSel=null;
  renderPlayerQueue(); toast('🧹 '+weg+' Dublette(n) entfernt.');
}
function queueLeeren(){
  if(!playerState.queue.length)return;
  if(!confirm('Die ganze Warteschlange leeren? (Titel-Dateien und gespeicherte Playlists bleiben.)'))return;
  playerState.queue=[]; playerState.idx=-1; plqSel=null;
  renderPlayerQueue(); renderPlayerMedia(); cmdNowRender();
  toast('Warteschlange geleert.');
}
function queueWerkzeugListe(){                          // gemeinsame Liste [Label, aktiv?, fn] für Flyout + ⋯-Menü
  return [nurPc(['💾 Als Playlist speichern…', false, queueAlsPlaylist]),
          ['↕ Nach Titel sortieren', false, ()=>queueSortieren('titel')],
          ['↕ Nach Dauer sortieren', false, ()=>queueSortieren('dauer')],
          ['↕ Reihenfolge umkehren', false, queueUmkehren],
          ['🧹 Duplikate entfernen', false, queueDuplikate],
          ['🗑 Warteschlange leeren', false, queueLeeren]];
}
function plqWerkzeuge(ev){                              // ⋯-Knopf im Playlist-Fenster
  ev.stopPropagation();
  kontextMenuBauen(ev, queueWerkzeugListe().map(o=>Object.assign([o[0], o[2]],{nurPc:o.nurPc})));
}
function plWerkzeugeImPlayer(ev){
  /* Build 137 (Punkt 4): derselbe Werkzeugkasten im EINGEBAUTEN Player.
     Zwei Gruppen, die sonst an zwei verschiedenen Orten wohnen und leicht zu
     verwechseln sind — deshalb hier mit Überschriften getrennt:
       · was die WARTESCHLANGE betrifft (was gerade läuft),
       · was die gewählte PLAYLIST betrifft (was gespeichert ist).
     Kein neuer Code für die Aktionen: es sind exakt dieselben Funktionen wie
     im herausgelösten Fenster, damit beide Wege nie auseinanderlaufen. */
  ev.stopPropagation();
  const eintraege=[['— Warteschlange —', ()=>{}]];
  queueWerkzeugListe().forEach(o=>eintraege.push(Object.assign([o[0], o[2]],{nurPc:o.nurPc})));
  eintraege.push(['— Playlist —', ()=>{}]);
  eintraege.push(['📻 Neues entdecken', entdeckerOeffnen]);
  eintraege.push(nurPc(['✎ Umbenennen', plRename]));
  eintraege.push(nurPc(['🎚 Wiedergabe…', ()=>{          // Etappe C: Regeln je Playlist
    const id=(document.getElementById('plsel')||{}).value||playerState.plid;
    const p=plState.find(q=>q.id===id);
    if(p)wiedergabeDialog({plid:p.id}, 'Playlist „'+p.name+'"');
    else toast('Erst eine gespeicherte Playlist wählen/laden.');
  }]));
  eintraege.push(nurPc(['⇄ Sync einrichten…', plSyncConfig]));
  eintraege.push(['⤓ Als .m3u exportieren', plExport]);
  eintraege.push(nurPc(['⤒ .m3u importieren…', ()=>document.getElementById('m3ufile').click()]));
  aktionsMenu(ev, eintraege);
}
/* Eigenschaften-Popup (22.07., foobar „Properties"): alle Metadaten eines
   Titels auf einen Blick — Codec/Bitrate/Auflösung/Größe/Pfad-Herkunft/Tags. */
function eigKopiere(key){const x=libFind(key); try{navigator.clipboard&&navigator.clipboard.writeText((x&&x.titel)||key);}catch(e){} toast('Titel kopiert.');}
function eigenschaften(key){
  const x=libFind(key); if(!x){toast('Keine Infos zu diesem Titel.');return;}
  const vid=(String(key).split('|')[0])||key;
  // Der Besitzer 05.08.: „unter Eigenschaften die Metadaten sehen (wie in iTunes)" —
  // erst der Musik-Block (Künstler/Album/…), dann Datei und Technik.
  const wg=x.wiedergabe||{};
  const wgText=[wg.sub?('Untertitel: '+wg.sub):'', wg.speed?('Tempo '+wg.speed+'×'):'',
                wg.ton?('Ton: '+wg.ton):''].filter(Boolean).join(' · ');
  const musikText={belegt:'belegt (MusicBrainz)', wahrscheinlich:'wahrscheinlich',
                   nein:'kein Lied'}[x.musik]||'unbestimmt';
  const zeilen=[
    ['Titel', x.titel||key],
    ['Künstler', x.kuenstler||'–'],
    ['Song', x.track||'–'],
    ['Album', x.album||'–'],
    ['Jahr', x.jahr||'–'],
    ['Genre', x.genre||'–'],
    ['Musik-Erkennung', musikText],
    ['Album-Cover', x.cover_album?(x.kategorie==='MP3'?'echtes Cover, eingebettet':'echtes Cover (Beilage)'):'YouTube-Thumbnail'],
    ['Wiedergabe-Regel', wgText||'– (erbt von Playlist/global)'],
    ['Kanal / Uploader', x.uploader||'–'],
    ['Kategorie', x.kategorie||'–'],
    ['Qualität', x.qualitaet||'–'],
    ['Technik', technikText(x)],
    ['Dauer', x.dauer?zeit(x.dauer):'–'],
    ['Dateigröße', mb(x.groesse)],
    ['Hochgeladen', ytdatum(x.upload_date)||'–'],
    ['Zuletzt gespielt', x.last_play?new Date(x.last_play*1000).toLocaleString('de-DE'):'–'],
    ['Wiedergaben', String(x.plays||0)],
    ['Video-ID', vid],
    ['Status', x.vorhanden?'auf der Platte':'verschoben / gelöscht']
  ];
  const rows=zeilen.map(z=>`<tr><td class="k">${esc(z[0])}</td><td class="v">${esc(String(z[1]))}</td></tr>`).join('');
  const yt=x.url?`<tr><td class="k">YouTube</td><td class="v"><a href="${esc(x.url)}" target="_blank" rel="noreferrer">${esc(x.url)}</a></td></tr>`:'';
  // Erst das ECHTE Album-Cover (/api/cover), Thumbnail nur als Rückfall.
  const cstil='max-width:190px;width:40%;border-radius:8px;float:right;margin:0 0 8px 12px';
  const cover=x.thumb
    ?`<img src="/api/cover?id=${encodeURIComponent(key)}" style="${cstil}" data-fb="${esc(x.thumb)}" onerror="this.onerror=function(){this.style.display='none'};this.src=this.dataset.fb">`
    :`<img src="/api/cover?id=${encodeURIComponent(key)}" style="${cstil}" onerror="this.style.display='none'">`;
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML=`<div class="modal-box" style="max-width:560px"><div class="modal-head"><b>ℹ Eigenschaften</b>`+
    `<button class="ib" title="Schließen" onclick="this.closest('.modal').remove()">✕</button></div>`+
    `<div style="padding:14px 16px 18px">${cover}<table class="eig-tab">${rows}${yt}</table>`+
    `<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;clear:both">`+
      (x.vorhanden?`<button class="btn mini" data-key="${esc(key)}" onclick="biblio(this.dataset.key,'ordner')">📁 Im Ordner zeigen</button>`:'')+
      `<button class="btn mini" data-key="${esc(key)}" onclick="eigKopiere(this.dataset.key)">⧉ Titel kopieren</button>`+
    `</div></div></div>`;
  ov.onclick=e=>{if(e.target===ov)ov.remove();};
  document.body.appendChild(ov);
}
function plqDragStart(e,i){
  // Build 144: Startet gerade ein Rahmen auf dieser Zeile, darf der native
  // Drag NICHT anspringen — er wuerde die Mausbewegung an sich reissen und
  // das Band bliebe leer. Umgekehrt bleibt jede markierte Zeile ziehbar,
  // weil plqBandStart dort gar nicht erst in den Band-Modus geht.
  if(plqBandModus){e.preventDefault(); return false;}
  plqVon=i; e.dataTransfer.effectAllowed='move';}
function plqDragOver(e){e.preventDefault(); e.dataTransfer.dropEffect='move';}
function plqEinfuegen(key,i){                          // Bibliotheks-Titel an Position i einreihen
  const x=libFind(key); if(!x||!x.vorhanden)return;
  const curKey=aktKey();
  if(!playerState.queue.length)playerState.quelle='Playlist';   // frische Ad-hoc-Playlist
  playerState.queue.splice(i,0,key);
  if(playerState.idx<0){playerState.idx=0; ensurePlayer(); renderPlayerMedia(); return;}
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));
  renderPlayerQueue(); cmdNowRender();
}
/* Titel AUF das Video/Cover ziehen (14.07.): spielt sofort, wenn nichts
   läuft — sonst entsteht/wächst die Ad-hoc-Playlist (die Player-Queue, nichts
   wird gespeichert; speichern geht weiter über ＋ Playlist). */
function plMediaOver(e){
  const t=e.dataTransfer?[...e.dataTransfer.types]:[];
  if(!t.includes('ytdl/key'))return;
  e.preventDefault();
  // Sichtbare Rückmeldung an der KARTE, damit man vor dem Loslassen sieht,
  // dass die ganze Fläche annimmt — nicht nur das Bild.
  const c=document.getElementById('pl-card'); if(c)c.classList.add('dropziel');
}
function plKarteLeave(e){
  const c=document.getElementById('pl-card');
  if(c&&!c.contains(e.relatedTarget))c.classList.remove('dropziel');
}
/* Command-Bar-Mini-Player als Drop-Ziel (21.07.: „Video auf den Play-Knopf
   oben links ziehen = in die Playlist"). Reiht ein — spielt sofort, wenn nichts läuft. */
function cmdNowOver(e){
  const t=e.dataTransfer?[...e.dataTransfer.types]:[];
  if(t.includes('ytdl/key')){e.preventDefault(); const n=document.getElementById('cmd-now'); if(n)n.classList.add('dropziel');}
}
function cmdNowLeave(){const n=document.getElementById('cmd-now'); if(n)n.classList.remove('dropziel');}
function cmdNowDrop(e){
  e.preventDefault(); const n=document.getElementById('cmd-now'); if(n)n.classList.remove('dropziel');
  // Build 141: wie plMediaDrop — die ganze Auswahl reist mit.
  const keys=plZiehKeys(e).filter(k=>{const y=libFind(k); return y&&y.vorhanden;});
  if(!keys.length)return;
  const x=libFind(keys[0]);
  if(playerState.idx<0||!playerState.queue.length){playerPlay(keys);}
  else{ keys.forEach(k=>playerState.queue.push(k)); renderPlayerQueue(); cmdNowRender(); }
  plInfo('🎶 „'+((x.titel||'').slice(0,24))+'" eingereiht ('+playerState.queue.length+' Titel)');
}
function plMediaDrop(e){
  e.preventDefault(); e.stopPropagation();
  const c=document.getElementById('pl-card'); if(c)c.classList.remove('dropziel');
  // Build 141 („wenn ich vier markiert habe und die alle in den player
  // ziehe, dann ist nur eins davon in der playlist"). Hier wurde nur EIN Key
  // gelesen; plZiehKeys() nimmt die ganze Auswahl mit — dieselbe Funktion,
  // die der Wurf auf die Playlist-Auswahl längst benutzt.
  const keys=plZiehKeys(e).filter(k=>{const y=libFind(k); return y&&y.vorhanden;});
  if(!keys.length)return;
  const x=libFind(keys[0]);
  if(playerState.idx<0||!playerState.queue.length){playerPlay(keys);return;}
  keys.forEach(k=>playerState.queue.push(k));          // doppelt ist erlaubt (der Besitzer, Build 138)
  renderPlayerQueue(); cmdNowRender();
  plInfo('🎶 „'+((x.titel||'').slice(0,24))+'" eingereiht ('+playerState.queue.length+' Titel)');
}
function plqDrop(e,i){
  e.preventDefault(); e.stopPropagation();             // WICHTIG: sonst blubbert das Drop hoch zum
  // Container-Handler plqZielDrop -> derselbe Titel wird ein 2. Mal ans Ende gehängt (Bug 22.07.:
  // „zwei reingezogen", nur im Layout mit kleiner Playlist unterm Video, wo man AUF einen Eintrag fallen lässt).
  const neu=e.dataTransfer.getData('ytdl/key');
  if(plqVon===null&&neu){plqEinfuegen(neu,i); return;} // von außen (Bibliothek) hereingezogen
  if(plqVon===null||plqVon===i){plqVon=null;return;}
  const curKey=aktKey();                               // laufenden Titel über den Umbau retten
  const [t]=playerState.queue.splice(plqVon,1);
  playerState.queue.splice(i,0,t);
  playerState.idx=Math.max(0, playerState.queue.indexOf(curKey));
  plqVon=null; renderPlayerQueue();
}
function plqZielOver(e){                               // Freifläche der Liste als Drop-Ziel
  const typen=e.dataTransfer?[...e.dataTransfer.types]:[];
  if(typen.includes('ytdl/key')||plqVon!==null)e.preventDefault();
}
function plqZielDrop(e){
  e.preventDefault();
  const key=e.dataTransfer.getData('ytdl/key');
  if(key&&plqVon===null)plqEinfuegen(key, playerState.queue.length);
  plqVon=null;
}
/* ---- Build 144d, der Besitzer Punkt 3: „Spotify-artiges ＋ im Player oben für eine
   Lieblingssongs-Playlist."
   Bewusst KEINE neue Datenstruktur: die Lieblingssongs sind eine ganz normale
   Playlist und damit sofort abspielbar, exportierbar (.m3u), synchronisierbar
   aufs Handy und im Playlist-Menü sichtbar. Eine eigene „Favoriten"-Liste
   neben den Playlists waere ein zweiter Mechanismus fuer dieselbe Sache.
   Sie entsteht beim ERSTEN Klick — der Besitzer soll sie nicht vorher anlegen muessen,
   sonst waere der Knopf beim ersten Mal eine Sackgasse. */
const LIEBLINGS_NAME='♥ Lieblingssongs';
function lieblingsPlaylist(){return (plState||[]).find(p=>p.name===LIEBLINGS_NAME);}
function istLiebling(k){const p=lieblingsPlaylist(); return !!(p&&k&&(p.items||[]).includes(k));}
function lieblingMalen(){
  const b=document.getElementById('pl-lieb'); if(!b)return;
  const k=aktKey(), drin=istLiebling(k);
  b.style.display=k?'':'none';                         // ohne laufenden Titel gibt es nichts zu merken
  b.textContent=drin?'✓':'＋';
  b.classList.toggle('an',drin);
  b.title=drin?'Aus „'+LIEBLINGS_NAME+'" wieder herausnehmen'
              :'Zu „'+LIEBLINGS_NAME+'" hinzufügen (die Playlist entsteht beim ersten Mal von selbst)';
}
async function lieblingToggle(){
  const k=aktKey(); if(!k){toast('Es läuft gerade nichts.');return;}
  let p=lieblingsPlaylist();
  if(!p){
    await plApi({art:'create',name:LIEBLINGS_NAME});
    p=lieblingsPlaylist();
    if(!p){toast('Konnte die Lieblings-Playlist nicht anlegen.');return;}
  }
  if((p.items||[]).includes(k)){
    // Zweiter Klick nimmt wieder heraus (Spotify-Verhalten). Ueber 'ersetzen',
    // weil das die Liste exakt setzt — und weil ein Titel hier genau einmal
    // drin ist: gemocht oder nicht, ein Zwischending gibt es nicht.
    await plApi({art:'ersetzen',id:p.id,items:(p.items||[]).filter(x=>x!==k)});
    toast('♥ aus den Lieblingssongs genommen.');
  }else{
    await plApi({art:'add',id:p.id,key:k});
    toast('♥ zu den Lieblingssongs.');
  }
  lieblingMalen();
}

/* ---- Build 144, der Besitzer Punkt 2: „Playlist speichern/aktualisieren, wenn man
   Titel in eine gerade laufende Playlist zieht" — „ganz dezent irgendwo".
   Bis hierher war die Warteschlange immer fluechtig: man zog einen Titel
   hinein, hoerte ihn, und beim naechsten Start war er wieder weg. Jetzt weiss
   der Player ueber `playerState.plid`, aus welcher gespeicherten Playlist er
   spielt, und bietet das Sichern an — aber nur, wenn es wirklich etwas zu
   sichern gibt (Calm-Design: Anzeige nur bei Handlungsbedarf). */
function _plqZaehl(arr){const m=new Map(); (arr||[]).forEach(k=>m.set(k,(m.get(k)||0)+1)); return m;}
function plqGeaendert(){
  if(!playerState.plid)return false;
  const p=(plState||[]).find(x=>x.id===playerState.plid); if(!p)return false;
  // Vergleich als MENGE (sortiert), nicht als Reihenfolge: Mischen ist eine
  // Wiedergabe-Entscheidung, keine Playlist-Aenderung — zaehlte die
  // Reihenfolge mit, stuende nach JEDEM Zufalls-Start sofort „geaendert" da
  // und der Hinweis waere wertlos. Sortiert vergleichen erfasst Duplikate
  // richtig (die sind seit Build 138 ausdruecklich erlaubt).
  const a=(p.items||[]).slice().sort(), b=playerState.queue.slice().sort();
  return a.length!==b.length||a.some((k,i)=>k!==b[i]);
}
async function plqSichern(){
  const p=(plState||[]).find(x=>x.id===playerState.plid); if(!p)return;
  // Nicht-destruktiv (HARTE REGEL): die gespeicherte REIHENFOLGE bleibt
  // stehen, Entferntes faellt heraus, Neues haengt hinten an. Wer bei
  // gemischter Wiedergabe einen Titel hineinzieht, zerschiesst damit also
  // nie die Ordnung seiner Playlist. `rest` zaehlt je Titel herunter, damit
  // mehrfach vorhandene Titel nicht verloren gehen.
  const rest=_plqZaehl(playerState.queue), alt=[];
  (p.items||[]).forEach(k=>{const n=rest.get(k)||0; if(n>0){alt.push(k); rest.set(k,n-1);}});
  const neu=playerState.queue.filter(k=>{const n=rest.get(k)||0; if(n>0){rest.set(k,n-1); return true;} return false;});
  const items=alt.concat(neu);
  await plApi({art:'ersetzen',id:p.id,items});
  renderPlayerQueue();
  toast('💾 „'+p.name+'" aktualisiert ('+items.length+' Titel'+(neu.length?', '+neu.length+' neu':'')+').');
}
function renderPlayerQueue(){
  // rendert in BEIDE Ziele: seitliche Liste im Player + eigenes Playlist-Fenster
  const html=playerState.queue.map((k,i)=>{const x=libFind(k)||{titel:k};
    const aus=!artPasst(x||{});
    // Abo-Folgen: die CD-Nummer (#12) vor den Titel — so ist die Reihenfolge sofort klar (21.07.)
    const nr=x.abo_nr?`<span class="pl-nr" title="Folge ${x.abo_nr}">#${x.abo_nr}</span> `:'';
    return `<div class="pl-item ${i===playerState.idx?'akt':''}${(i===plqSel||plqAuswahl.has(i))?' sel':''}${aus?' artaus':''}" draggable="true" tabindex="0" data-i="${i}" `+
      `ondragstart="plqDragStart(event,+this.dataset.i)" ondragover="plqDragOver(event)" ondrop="plqDrop(event,+this.dataset.i)" `+
      `onclick="plqSelect(+this.dataset.i,event)" ondblclick="plQueueKlick(+this.dataset.i)" oncontextmenu="return plItemKontext(event,+this.dataset.i)" title="Klick = auswählen · Doppelklick/Enter = abspielen · Rechtsklick = Menü · Entf = aus Playlist löschen · ↑/↓ = Auswahl · Ziehen = umsortieren">${i+1}. ${nr}${esc(x.titel||k)}</div>`;}).join('')
    ||'<div class="pl-leer">Leer — Titel aus der Bibliothek hierher ziehen.</div>';
  const q=document.getElementById('pl-queue'); if(q){q.innerHTML=html; q.onpointerdown=plqBandStart;}
  const qw=document.getElementById('pl-queue-win'); if(qw){qw.innerHTML=html; qw.onpointerdown=plqBandStart;}
  // Build 144c (der Besitzer): Der Rahmen soll schon ein, zwei Reihen ÜBER der Liste
  // beginnen dürfen. Dort liegt gar nicht mehr die Liste, sondern ihr
  // Behälter — im Player die Titel-/Steuerungs-Spalte, im herausgelösten
  // Fenster die Karte mit der Kopfzeile. Beide hören jetzt mit; Bedienelemente
  // filtert plqBandStart ohnehin heraus, und plqZugLaeuft verhindert, dass aus
  // den zwei mithörenden Ebenen zwei Bänder werden.
  const seite=document.querySelector('#view-player .pl-side'); if(seite)seite.onpointerdown=plqBandStart;
  const fenster=document.querySelector('#view-plq .card'); if(fenster)fenster.onpointerdown=plqBandStart;
  /* Build 144e (mit Bild): „genauso wie oben, sollte man auch von UNTEN ein
     fenster ziehen koennen … solange es in dem fenster ist, ist ein feld
     ziehen gewaehrleistet." Gemessen: die Karte ist nur so hoch wie ihr
     INHALT, nicht wie das Panel — im Playlist-Fenster lagen 232 px Schwarz
     darunter, an denen kein Zuhoerer hing. Das FENSTER ist der `panel-body`,
     also hoert der. Die Videoflaeche ist oben ausgenommen, und ohne sichtbare
     eigene Liste springt nichts an (Reiter-Panels). */
  ['#view-player','#view-plq'].forEach(sel=>{
    const v=document.querySelector(sel), koerper=v&&v.closest('.panel-body');
    if(koerper)koerper.onpointerdown=plqBandStart;
  });
  const za=document.getElementById('plq-anzahl');
  if(za)za.textContent=playerState.queue.length?(playerState.queue.length+' Titel'):'';
  // Der Sichern-Hinweis haengt an BEIDEN Playlist-Sichten und erscheint nur,
  // wenn die Warteschlange von ihrer gespeicherten Playlist abweicht.
  const dreckig=plqGeaendert();
  document.querySelectorAll('.plq-sichern').forEach(el=>{el.style.display=dreckig?'':'none';});
  // Playlist-Fenster trägt den echten Quellen-Namen (Radio / Playlist-Name /
  // Bibliothek / Mix …) statt statisch „Player-Playlist" (21.07.).
  const pt=document.getElementById('plq-titel');
  if(pt)pt.textContent=playerState.queue.length?(playerState.quelle||'Playlist'):'Playlist';
}

/* ---- Transkript-Volltextsuche (21.07.): findet, in welchem Video ein
   Begriff wann gesagt wird; Klick auf eine Fundstelle spielt das Video ab
   und springt an die Stelle (Tube-Archivist-Muster). ---- */
function tsMarkiere(text,q){
  const i=text.toLowerCase().indexOf(q.toLowerCase());
  if(i<0)return esc(text);
  return esc(text.slice(0,i))+'<mark>'+esc(text.slice(i,i+q.length))+'</mark>'+esc(text.slice(i+q.length));
}
async function transkriptSuche(){
  const q=(document.getElementById('libsuche').value||'').trim();
  if(q.length<2){toast('Bitte mindestens 2 Zeichen für die Transkript-Suche.');return;}
  let ov=document.getElementById('tsuche-ov');
  if(!ov){ov=document.createElement('div'); ov.id='tsuche-ov';
    ov.onclick=e=>{if(e.target===ov)ov.classList.remove('an');};
    ov.innerHTML='<div class="tsuche-box"><div class="tsuche-kopf">'+
      '<b>🔎 Im Transkript</b><input type="text" id="tsuche-inp" placeholder="Begriff…" '+
      'onkeydown="if(event.key===\'Enter\')tsuchLauf()"><button class="tog" onclick="tsuchLauf()">Suchen</button>'+
      '<button class="ib" title="Schließen" onclick="document.getElementById(\'tsuche-ov\').classList.remove(\'an\')">✕</button></div>'+
      '<div class="tsuche-body" id="tsuche-body"></div></div>';
    document.body.appendChild(ov);
  }
  document.getElementById('tsuche-inp').value=q;
  ov.classList.add('an');
  tsuchLauf();
}
async function tsuchLauf(){
  const q=(document.getElementById('tsuche-inp').value||'').trim();
  const body=document.getElementById('tsuche-body');
  if(q.length<2){body.innerHTML='<div class="leer">Mindestens 2 Zeichen.</div>';return;}
  body.innerHTML='<div class="leer">Durchsuche Transkripte…</div>';
  try{
    const r=await fetch('/api/transkript_suche?q='+encodeURIComponent(q));
    const d=await r.json(); const tr=d.treffer||[];
    if(!tr.length){body.innerHTML='<div class="leer">Nichts gefunden. (Nur Videos mit heruntergeladenen Untertiteln/Transkripten werden durchsucht.)</div>';return;}
    body.innerHTML=tr.map(v=>`<div class="tsuche-treffer"><div class="tsuche-t-titel">${esc(v.titel)}</div>`+
      v.treffer.map(t=>`<button class="tsuche-z" data-key="${esc(v.key)}" data-t="${t.zeit}" onclick="tsSpring(this.dataset.key,+this.dataset.t)"><span class="zt">${zeit(t.zeit)}</span>${tsMarkiere(t.text,q)}</button>`).join('')+
      '</div>').join('');
  }catch(e){body.innerHTML='<div class="leer">Suche fehlgeschlagen.</div>';}
}
function tsSpring(key,zeitSek){
  document.getElementById('tsuche-ov').classList.remove('an');
  ensurePlayer();
  playerPlay([key]);
  let versuche=0;
  const spring=()=>{const el=document.getElementById('pl-el');
    if(el&&el.duration){el.currentTime=Math.min(el.duration,zeitSek); el.play&&el.play().catch(()=>{});}
    else if(versuche++<40)setTimeout(spring,150);};
  setTimeout(spring,300);
}

