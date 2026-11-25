/* ================= Bibliothek ================= */
let libdaten=[], libModus='kachel', libArchiv=false;
let libAuswahl=new Set(), libSelectMode=false, libLastClick=null;
let libPlaylistView='';   // Wenn gesetzt: Bibliothek zeigt NUR diese Playlist (in ihrer Reihenfolge)

function libSelectToggle(){
  libSelectMode=!libSelectMode; if(!libSelectMode)libAuswahl.clear();
  document.getElementById('libselbtn').classList.toggle('an',libSelectMode);
  libMalen();
}
function libSelektierend(ev){return libSelectMode||ev.ctrlKey||ev.metaKey||ev.shiftKey;}
/* Strg+A wählt die GEFILTERTE Sicht (07.08.: „wenn ich z.B. gefiltert
   habe, dann sollte nur die gefilterten dateien angewählt werden") — genau
   wie im Abo-Fenster. Zweites Strg+A hebt die Auswahl wieder auf. */
function libAllesWaehlen(){
  const arr=libGefiltert();
  if(libAuswahl.size>=arr.length&&arr.length){libAuswahl.clear();}
  else{arr.forEach(x=>libAuswahl.add(x.id));}
  libMalen();
  plInfo(libAuswahl.size?libAuswahl.size+' Titel markiert':'Auswahl aufgehoben');
}
document.addEventListener('keydown',ev=>{
  if(!((ev.ctrlKey||ev.metaKey)&&ev.key.toLowerCase()==='a'))return;
  const el=document.activeElement;
  if(el&&['INPUT','TEXTAREA','SELECT'].includes(el.tagName))return;   // Text markieren bleibt
  const lib=document.getElementById('view-lib');
  if(!lib||!lib.offsetParent)return;                                  // nur in sichtbarer Bibliothek
  if(document.getElementById('tv')&&document.getElementById('tv').style.display!=='none')return;
  ev.preventDefault(); libAllesWaehlen();
});
function libSelectClick(ev,id){
  const arr=libGefiltert();
  if(ev.shiftKey&&libLastClick){
    const i1=arr.findIndex(x=>x.id===libLastClick), i2=arr.findIndex(x=>x.id===id);
    if(i1>=0&&i2>=0){const a=Math.min(i1,i2), b=Math.max(i1,i2);
      for(let i=a;i<=b;i++)libAuswahl.add(arr[i].id);}
  }else if(ev.ctrlKey||ev.metaKey||libSelectMode){
    if(libAuswahl.has(id))libAuswahl.delete(id); else libAuswahl.add(id);
    libLastClick=id;
  }else{ libAuswahl.clear(); libAuswahl.add(id); libLastClick=id; }
  libMalen();
}
function thumbClick(ev,id){
  if(libSelektierend(ev)){ev.stopPropagation(); libSelectClick(ev,id); return;}
  const x=libFind(id);
  if(x&&x.vorhanden)playerPlay([id]); else biblioNeuladen(id);
}
/* ---- Klick-Art zum Abspielen (Build 134, der Besitzer Punkt 4) ---------------------
   Vorgabe: „Einstellung Einfach- vs. Doppelklick zum Abspielen (Doppelklick
   Standard — ein anderer Nutzer bevorzugt Einfachklick; Vorgabe: Doppelklick fühlt sich
   nativer an und stört die Auswahl nicht)."
   Die Begründung ist auch der Grund für den Standard: bei Einfachklick
   kollidiert Abspielen mit dem Auswählen. Deshalb bleibt Doppelklick
   voreingestellt — wer den Einfachklick will, stellt ihn um. Gemerkt wird
   lokal, denn es ist eine Bedien-Vorliebe des Menschen am Gerät, keine
   Programm-Einstellung. */
function klickArt(){
  let v=lsLesen('ytdl_klickart')||'doppel';
  return v==='einfach'?'einfach':'doppel';
}
function klickArtSetzen(v){
  lsSchreiben('ytdl_klickart',v==='einfach'?'einfach':'doppel');
  toast(v==='einfach'?'▶ Einfachklick spielt ab.':'▶ Doppelklick spielt ab (Einfachklick wählt aus).');
}
/* ---- Rahmen-Auswahl in der Bibliothek (Build 135, der Besitzer Punkt 4) ------------
   Vorgabe: „Rahmen-Auswahl mit der Maus wie in Windows / wie in der Abo-Ansicht."
   Dort gibt es das seit Build 94 (aboBandStart) — die Bibliothek bekommt
   bewusst DIESELBEN Eigenschaften, damit sich beides gleich anfühlt: erst ab
   5 px Bewegung wird daraus ein Band (darunter bleibt es ein normaler
   Klick), Strg erweitert die bestehende Auswahl, und der nachlaufende Klick
   der Startkachel wird geschluckt.
   Ein Unterschied ist nötig: Kacheln sind ziehbar (draggable). Ein Zug auf
   einer Kachel muss deshalb ein ZIEHEN bleiben — das Band startet nur auf
   freier Fläche, sonst könnte man Titel nicht mehr auf Playlists ziehen. */
let libBandLief=false;
let libBandLaeuft=false;                               // ein Zug ist unterwegs (Zuhoerer haengt an drei Ebenen)
function libBandStart(ev){
  if(ev.button!==0)return;
  if(ev.target.closest('button,a,input,select'))return;
  // Gezielt .kachel/tr: auch PANELS tragen ein data-id (gemessen) — ein
  // unspezifisches [data-id] haette den Zug schon am Panel abgefangen.
  if(ev.target.closest('.kachel[data-id],tr[data-id]'))return;   // auf einer Kachel: Ziehen hat Vorrang
  // Build 144e: Der Zuhoerer haengt jetzt auch am panel-body (leerer Bereich
  // unter den Kacheln). Getroffen und gescrollt wird trotzdem `libinhalt` —
  // sonst schoebe das Rand-Nachschieben am falschen Element. Ohne sichtbaren
  // Inhalt springt nichts an (ein Panel kann mehrere Ansichten tragen).
  const beh=ev.currentTarget;
  const flaeche=(beh.id==='libinhalt')?beh
    :[...beh.querySelectorAll('#libinhalt')].find(n=>n.offsetParent);
  if(!flaeche)return;
  if(libBandLaeuft)return;                             // zwei Ebenen hoeren mit -> nur EIN Band
  libBandLaeuft=true;
  const basis=new Set(ev.ctrlKey||ev.metaKey?[...libAuswahl]:[]);
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
    const fr=flaeche.getBoundingClientRect();           // Rand-Nachschieben wie im Abo-Fenster
    if(e.clientY>fr.bottom-18)flaeche.scrollTop+=14;
    else if(e.clientY<fr.top+18)flaeche.scrollTop-=14;
    libAuswahl=new Set(basis);
    flaeche.querySelectorAll('.kachel[data-id],tr[data-id]').forEach(n=>{
      const q=n.getBoundingClientRect();
      if(q.left<r&&q.right>l&&q.top<b&&q.bottom>t)libAuswahl.add(n.dataset.id);
      n.classList.toggle('sel',libAuswahl.has(n.dataset.id));
    });
  }
  function up(){
    document.removeEventListener('pointermove',mv); document.removeEventListener('pointerup',up);
    document.body.classList.remove('nosel'); libBandLaeuft=false;
    if(band){
      band.remove(); libBandLief=true;
      setTimeout(()=>{libBandLief=false;},0);
      libMalen();                                      // Auswahl-Leiste/Zähler nachziehen
    }else if(libAuswahl.size&&!basis.size){
      // Build 142 (der Besitzer): Ein KLICK auf freie Fläche (kein Zug) räumt die
      // Auswahl ab — so macht es der Explorer. Vorher blieb sie samt
      // Bulk-Leiste stehen, obwohl man erkennbar danebengeklickt hatte.
      // Mit Strg gedrückt (basis gefüllt) bleibt sie natürlich erhalten.
      libAuswahl.clear(); libMalen();
    }
  }
  document.addEventListener('pointermove',mv); document.addEventListener('pointerup',up);
}
function kachelClick(ev,id){
  if(libBandLief)return;                               // der Klick war das Ende eines Band-Zugs
  if(ev.target.closest('button,a,input'))return;
  // Auswählen hat Vorrang: Strg/Umschalt und der Mehrfach-Auswahl-Modus
  // bleiben unberührt, sonst könnte man nichts mehr markieren.
  if(libSelektierend(ev)){ ev.preventDefault(); libSelectClick(ev,id); return; }
  if(klickArt()==='einfach'){ ev.preventDefault(); playerPlay([id]); }
}
function kachelDblClick(ev,id){
  if(ev.target.closest('button,a,input'))return;
  if(libSelektierend(ev))return;                       // im Auswahl-Modus nie abspielen
  if(klickArt()==='doppel'){ ev.preventDefault(); playerPlay([id]); }
}
/* Wo eine Datei landet, weiß erst der Server: Windows nimmt nicht jede (USB-Stick,
   Netzlaufwerk, sehr langer Pfad, voller Papierkorb). Jede Rückfrage nennt darum beide Orte. */
function korbRueckweg(){return 'Wiederherstellbar aus dem Windows-Papierkorb, sonst aus dem Ordner _Papierkorb im Download-Ordner.';}
/* Titel in den Papierkorb: einer oder die ganze Auswahl (Rückmeldung 19.10.:
   „Trotz Mehrfachauswahl konnte ich nicht mehrere Songs auf einmal löschen“).
   Gefragt wird im app-eigenen frageModal, nie per confirm(): Firefox hält den
   Web-Audio-Graphen an, solange ein nativer Dialog offen ist, und die Musik
   läuft über ihn (vizVerbinde) — gemessen 21.10. in Firefox 158: Stille für
   die ganze Dialog-Zeit, während der Titel weiterlief („der aktuelle Song wird
   kurz pausiert“). Der Server löscht je Titel wie bisher (Papierkorb, sonst
   rückholbar nach _Papierkorb); neu geladen wird einmal am Ende. */
function libLoeschen(keys){
  keys=(keys||[]).filter(k=>libFind(k)); if(!keys.length)return;
  const x=libFind(keys[0]);
  const text=keys.length>1
    ?keys.length+' Titel in den Papierkorb verschieben?\n'+korbRueckweg()
    :'„'+(x.titel||'').slice(0,40)+'“ in den Papierkorb verschieben?\n'+korbRueckweg();
  frageModal(text,'🗑 In den Papierkorb',async()=>{
    let weg=0;
    for(const k of keys){                              // nacheinander: der Server speichert je Titel
      try{const d=await api('/api/biblio',{id:k,art:'loeschen'}); if(!(d&&d.fehler)){weg++; libAuswahl.delete(k);}}
      catch(e){}
    }
    await libLaden();
    toast(weg===keys.length?'🗑 '+(weg>1?weg+' Titel':'Titel')+' in den Papierkorb.'
                           :'🗑 '+weg+' von '+keys.length+' Titeln in den Papierkorb, der Rest blieb.');
  });
}
function bulkPlaylist(ev){
  // Build 142 (der Besitzer): „Wenn ich + Playlist anklicke, dann sollte die Option
  // kommen zu welcher Playlist ich die hinzufügen soll." Vorher verlangte es
  // eine oben VORGEWÄHLTE Liste und brach sonst mit einer Meldung ab — man
  // musste also erst woanders etwas einstellen, um hier klicken zu dürfen.
  // Jetzt dieselbe Auswahl wie am ＋ jeder Kachel (plOptionen), inklusive
  // „Neue Playlist…", nur eben für die ganze Markierung.
  const keys=[...libAuswahl]; if(!keys.length)return;
  const rein=async(id)=>{
    const p=plState.find(x=>x.id===id);
    const vorher=((p&&p.items)||[]).slice();
    for(const k of keys)await plApi({art:'add',id,key:k});
    plLetzterWurf={id,vorher,plNeu:false};
    toastMitZurueck(keys.length+' Titel → „'+((plState.find(x=>x.id===id)||{}).name||'Playlist')+'"',
                    plZurueck);
  };
  const opt=plState.map(p=>[p.name+' ('+p.items.length+')', false, ()=>rein(p.id)]);
  opt.push(['＋ Neue Playlist…', false, async()=>{
    const n=prompt('Name der neuen Playlist:'); if(!n||!n.trim())return;
    const id=await plAnlegen(n.trim()); if(id)rein(id);}]);
  kmListe(kontextMenuBauen(ev||window.event,[]), '＋ '+keys.length+' Titel in …', opt);
}

/* ---- Abspielmodus (zyklisch), Shuffle, Meistgespielt, Zuletzt ---- */
function mische(a){for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
// max. 5 Modi; klicken wechselt Icon + Verhalten
/* Abspielmodus wie bei Spotify: ZWEI getrennte Toggles statt eines 4-Stufen-
   Zyklus (13.07.: „▶ sah aus wie Play, 🔁/🔂 zu klein, Modus nicht erkennbar").
   playShuffle = Zufall an/aus · playRepeat = aus/alle/eins. Die Knöpfe sind
   selbst gezeichnete SVGs (currentColor), aktiv = Akzentfarbe + Punkt darunter. */
/* Fehler-Rekorder (06.08.: „stürzt ab wenn ich ansicht klicke" — hier
   nicht reproduzierbar): JEDER JS-Fehler landet ab jetzt im Server-Log
   (System/js_fehler.jsonl), damit der nächste Absturz eine Spur hat. */
window.addEventListener('error',ev=>{
  try{fetch('/api/js_fehler',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:String(ev.message||'').slice(0,400),
      quelle:String(ev.filename||'').slice(-80), zeile:ev.lineno||0})}).catch(()=>{});}catch(e){}
});
window.addEventListener('unhandledrejection',ev=>{
  try{fetch('/api/js_fehler',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:('Promise: '+String(ev.reason||'')).slice(0,400),
      stack:String((ev.reason&&ev.reason.stack)||'').slice(0,600)})}).catch(()=>{});}catch(e){}
});
const ICONS={
  play:'M8 5v14l11-7z',
  pause:'M6 5h4v14H6zm8 0h4v14h-4z',
  prev:'M6 6h2v12H6zm12 0v12l-8.5-6z',
  next:'M16 6h2v12h-2zM6 6l8.5 6L6 18z',
  shuffle:'M10.59 9.17 5.41 4 4 5.41l5.17 5.17 1.42-1.41zM14.5 4l2.04 2.04L4 18.59 5.41 20 17.96 7.46 20 9.5V4h-5.5zm.33 9.41-1.41 1.41 3.13 3.13L14.5 20H20v-5.5l-2.04 2.04-3.13-3.13z',
  repeat:'M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z',
  repeat1:'M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4zm-4-2V9h-1l-2 1v1h1.5v4H13z',
  yt:'M21.6 7.2c-.2-.9-.9-1.6-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4c-.9.2-1.6.9-1.8 1.8C2 8.8 2 12 2 12s0 3.2.4 4.8c.2.9.9 1.6 1.8 1.8 1.6.4 7.8.4 7.8.4s6.2 0 7.8-.4c.9-.2 1.6-.9 1.8-1.8.4-1.6.4-4.8.4-4.8s0-3.2-.4-4.8zM10 15V9l5.2 3z',
  // Build 132 („die blauen Pfeile sehen schlecht aus, kannst du die vom
  // Stil identisch hinbekommen wie den play button?"). Das waren Emoji (⏪/⏩)
  // — die zeichnet jedes System anders und bringt oft eigene Farbe mit, hier
  // Blau. Jetzt gefüllte SVG-Dreiecke wie play/prev/next, also dieselbe
  // Form-Sprache und dieselbe Farbe wie der Rest der Leiste.
  back:'M11 12 19 6.5v11L11 12zm-8 0 8-5.5v11L3 12z',
  // Netflix-Parität (Nachtprüfung 06.08.): monochrome Flat-SVGs statt Emoji
  // an Karte + Player-Settings — Emoji bringen eigene Farben/Formen mit.
  plus:'M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z',
  chevron:'M12 15.5 4.5 8l1.4-1.4L12 12.7l6.1-6.1L19.5 8z',
  info2:'M11 10h2v7h-2zm0-3h2v2h-2zM12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16z',
  sub:'M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm2 8h6v2H6zm8 0h4v2h-4zM6 15h3v2H6zm5 0h7v2h-7z',
  speed:'M12 4a9 9 0 0 0-9 9 8.9 8.9 0 0 0 1.2 4.5l1.7-1A7 7 0 1 1 19 13a7 7 0 0 1-.9 3.4l1.7 1A9 9 0 0 0 12 4zm-1 9a1.5 1.5 0 0 0 2.4 1.2l4.2-3.2-5-1.4A1.5 1.5 0 0 0 11 13z',
  full:'M4 4h6v2H6v4H4V4zm10 0h6v6h-2V6h-4V4zM4 14h2v4h4v2H4v-6zm14 0h2v6h-6v-2h4v-4z',
  kreuz:'m6 5 6 6 6-6 1.4 1.4L13.4 12l6 6L18 19.4l-6-6-6 6L4.6 18l6-6-6-6z',
  fwd:'M13 12 5 17.5v-11L13 12zm8 0-8 5.5v-11L21 12z'};
const ICONS_VOLL={
  // 10-Sekunden-Kreispfeile (05.08., Bild): unmissverständlich ±10 s —
  // die alten ⏪/⏩-Doppeldreiecke lasen sich wie voriger/nächster Titel.
  r10:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/><text x="12" y="16.5" text-anchor="middle" font-size="7.5" font-weight="700" fill="currentColor" stroke="none">10</text></svg>',
  f10:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/><text x="12" y="16.5" text-anchor="middle" font-size="7.5" font-weight="700" fill="currentColor" stroke="none">10</text></svg>'};
function ico(n){return ICONS_VOLL[n]||('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="'+ICONS[n]+'"/></svg>');}

/* ---- Browser-Zeichen für den Status-Punkt (Build 133, Wunsch) ----------
   Reihenfolge der Prüfung ist wichtig: Edge und Chrome tragen beide „Chrome"
   im User-Agent, Safari steht auch in Chromes Kennung. Deshalb wird von der
   spezifischsten Kennung zur allgemeinsten geprüft — sonst wäre jeder
   Browser ein Chrome. */
function browserArt(){
  const ua=navigator.userAgent||'';
  if(/Firefox\//.test(ua))                    return 'firefox';
  if(/Edg\//.test(ua))                        return 'edge';
  if(/OPR\//.test(ua))                        return 'opera';
  if(/Chrome\//.test(ua))                     return 'chrome';
  if(/Safari\//.test(ua))                     return 'safari';
  return 'sonst';
}
function browserName(){
  return {firefox:'Firefox',edge:'Edge',opera:'Opera',chrome:'Chrome',
          safari:'Safari',sonst:'unbekannt'}[browserArt()];
}
function browserZeichen(){
  const art=browserArt();
  const kern='<circle class="apikern" cx="12" cy="12" r="4.6"/>';
  // Firefox: Korrektur — ein Kreis mit Meridianen ist ein GENERISCHER
  // Globus, kein Firefox. Erkennbar macht das Zeichen der Fuchsschweif, der
  // sich um die Kugel legt und oben in einer Spitze ausläuft. Deshalb: ein
  // fast geschlossener, kräftiger Bogen (der Schweif) mit Flammenzunge —
  // und der Kern in der Mitte ist die Erdkugel, die die Statusfarbe trägt.
  if(art==='firefox')
    // Vorlage: Der Fuchs windet sich um die blaue ERDKUGEL — und genau
    // die trägt die Statusfarbe. Der Schweif ist ein kräftiger Bogen, der
    // oben rechts in der Flammenspitze ausläuft; die Kugel füllt die Mitte
    // deutlich größer als bei den anderen Zeichen, weil sie beim Firefox-
    // Logo das beherrschende Element ist.
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<circle class="apikern" cx="11.6" cy="12.4" r="6.4"/>'+
      '<path class="apiring" d="M17.2 5.6a9 9 0 1 0 2.4 4.9" stroke-width="2.8" stroke-linecap="round"/>'+
      '<path d="M15.4 2.6 21.4 4.9l-2.2 5.2-1.6-3.6z" fill="currentColor" opacity=".8"/>'+
      '</svg>';
  // Chrome: drei Segmente mit Fugen (statt eines glatten Rings) — das ist
  // das, was man auf kleiner Fläche als Chrome liest. Der Kern sitzt dort,
  // wo sonst das Blau steckt: genau die Stelle, die der Besitzer benannt hat.
  if(art==='chrome'||art==='opera')
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<path class="apiring" d="M12.9 3.05A9 9 0 0 1 20.5 15.6" stroke-width="2.6" stroke-linecap="round"/>'+
      '<path class="apiring" d="M18.6 18.7A9 9 0 0 1 5.2 16.9" stroke-width="2.6" stroke-linecap="round"/>'+
      '<path class="apiring" d="M4.2 14.7A9 9 0 0 1 10.6 3.2" stroke-width="2.6" stroke-linecap="round"/>'+
      kern+'</svg>';
  // Edge: der offene Bogen.
  if(art==='edge')
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<path class="apiring" d="M20 15a9 9 0 1 0-8 5.9" stroke-width="2.2" stroke-linecap="round"/>'+kern+'</svg>';
  // Safari: der Besitzer stellte frei, ob die blaue Scheibe oder die Nadel den Status
  // trägt. Die NADEL — die blaue Scheibe wäre bei 16 px eine große Farbfläche,
  // die den ganzen Kopfbereich einfärbt; ein rot leuchtender Kreis dieser
  // Größe sähe nach Alarm aus, obwohl nur die Verbindung fehlt. Die Nadel ist
  // klein, liegt in der Mitte und ist beim echten Logo ohnehin das rote Teil.
  if(art==='safari')
    return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
      '<circle class="apiring" cx="12" cy="12" r="9" stroke-width="1.8"/>'+
      '<path class="apikern" d="M16.8 7.2 13.9 13.9 7.2 16.8 10.1 10.1z"/>'+
      '</svg>';
  return '<svg viewBox="0 0 24 24" aria-hidden="true">'+
    '<circle class="apiring" cx="12" cy="12" r="9" stroke-width="1.6"/>'+kern+'</svg>';
}
let playShuffle=false, playRepeat='aus';               // 'aus' | 'alle' | 'eins'
try{
  playShuffle=localStorage.getItem('ytdl_shuffle')==='1';
  const r=localStorage.getItem('ytdl_repeat'); if(r==='alle'||r==='eins')playRepeat=r;
  // Migration vom alten 4-Stufen-Modus (einmalig, solange die neuen Keys fehlen)
  if(localStorage.getItem('ytdl_shuffle')===null&&localStorage.getItem('ytdl_repeat')===null){
    const alt=localStorage.getItem('ytdl_playmode');
    if(alt==='zufall')playShuffle=true;
    if(alt==='alle'||alt==='eins')playRepeat=alt;
  }
}catch(e){}
/* Abspielart (Build 144l, der Besitzer 25.07.): EINE Auswahl mit vier Klartext-Optionen
   statt des durchklickenden Symbols, das „nur Musik" hiess aber nach FORMAT
   filterte (Video-Songs fielen raus, Comedy-MP3s blieben).
     Alles · Nur Ton (MP3) · Nur Video · Nur Songs.
   „Nur Songs" ist die INHALTS-Achse: Lieder, egal ob MP3 oder Video-Song —
   stützt sich auf die Musik-Einstufung (`musik`) aus dem Backend (Build 144h).
   Wirkt überall gleich (Raster, Radio, Autoplay), weil alle über artPasst
   gehen; ausgewählte Playlists spielen weiter wörtlich. */
const PLAYART=[
  ['alle','🎬🎵','Alles','Ton und Video, jeder Inhalt'],
  ['mp3','🎧','Nur Ton','nur Audiodateien (MP3/m4a …)'],
  ['video','🎬','Nur Video','nur Videodateien'],
  ['songs','🎵','Nur Songs','Lieder — egal ob MP3 oder Video-Song; Trailer, Gaming-Clips, Comedy und Podcasts bleiben draussen']];
let playArt='alle';
try{const v=localStorage.getItem('ytdl_playart'); if(PLAYART.some(o=>o[0]===v))playArt=v;}catch(e){}
function playArtMenu(ev){
  aktionsMenu(ev, PLAYART.map(o=>[(o[0]===playArt?'✓ ':'　')+o[1]+' '+o[2], ()=>playArtSetzen(o[0])]));
}
function playArtSetzen(v){
  playArt=v; lsSchreiben('ytdl_playart',v);
  transportRender(); libMalen(); renderPlayerQueue();  // Ansicht + Queue folgen sofort
  const o=PLAYART.find(o=>o[0]===v)||PLAYART[0];
  toast('▶ '+o[1]+' '+o[2]);
}
// Hat die Bibliothek überhaupt schon Musik-Einstufungen? Vor dem App-Neustart
// (youtube_app.py lädt nicht heiss nach) fehlt das Feld — dann darf „Nur
// Songs" NICHT alles wegfiltern, sonst sähe die Bibliothek leer aus.
function musikBekannt(){return (libdaten||[]).some(x=>x.musik);}
function artPasst(x){
  if(playArt==='alle')return true;
  if(playArt==='songs')return !musikBekannt()||(!!x.musik&&x.musik!=='nein');
  const audio=x.dateiart?x.dateiart==='audio':(x.kategorie==='MP3');
  return playArt==='mp3'?audio:!audio;
}
function shuffleToggle(){playShuffle=!playShuffle;
  lsSchreiben('ytdl_shuffle',playShuffle?'1':'0');
  transportRender();}
function repeatCycle(){playRepeat=(playRepeat==='aus')?'alle':(playRepeat==='alle'?'eins':'aus');
  lsSchreiben('ytdl_repeat',playRepeat);
  transportRender();
  xfPruefen();}                                        // eins: eine laufende Blende in den nächsten Titel zurücknehmen
/* Zieht NUR die Zustände der Transport-Knöpfe nach (classList/innerHTML des
   einzelnen Knopfs) — kein Neuaufbau der Leiste, darum reagiert der Klick sofort. */
function transportRender(){
  const pe=document.getElementById('pl-el');
  document.querySelectorAll('[data-tr="shuffle"]').forEach(b=>{
    b.classList.toggle('an',playShuffle); b.title='Zufall: '+(playShuffle?'AN':'aus');});
  document.querySelectorAll('[data-tr="repeat"]').forEach(b=>{
    b.classList.toggle('an',playRepeat!=='aus');
    b.innerHTML=ico(playRepeat==='eins'?'repeat1':'repeat');
    b.title='Wiederholen: '+(playRepeat==='aus'?'aus':(playRepeat==='alle'?'alle Titel':'nur dieser Titel'))+' (klicken: aus → alle → einer)';});
  // DER Wurm (05.08., „wechselt kurz und springt zurück"): dieser Maler
  // läuft im 1-s-Takt und las NUR das <audio>-Element — am Gerät VLC gibt es
  // keins, also übermalte er den richtigen Zustand sofort wieder mit ▶.
  const spielt=vlcAktiv()?vlcSpielt:!!(pe&&!pe.paused);
  document.querySelectorAll('[data-tr="pp"]').forEach(b=>{
    b.innerHTML=ico(spielt?'pause':'play');
    b.title=spielt?'Pause':'Abspielen';});
  // Bild und Platzhalter haben getrennte Pseudoelemente, aber denselben Zustand.
  const key=aktKey();
  document.querySelectorAll('.thumbwrap[data-key]').forEach(b=>{
    const laeuft=spielt&&b.dataset.key===key;
    b.classList.toggle('spielt',laeuft); b.title=laeuft?'Pause':'Abspielen';});
  document.querySelectorAll('[data-tr="radio"]').forEach(b=>b.classList.toggle('an',radioAktiv));
  document.querySelectorAll('[data-tr="art"]').forEach(b=>{
    const o=PLAYART.find(o=>o[0]===playArt)||PLAYART[0];
    b.classList.toggle('an',playArt!=='alle');
    b.textContent=o[1];                                 // aktuelles Symbol
    b.title='Was spielt: '+o[2]+' — klicken für die Auswahl (Alles · Nur Ton · '+
      'Nur Video · Nur Songs). Gilt überall: Bibliothek, Playlists (übersprungene '+
      'Titel bleiben gedimmt drin), Radio und Autoplay.';
  });
}
function queueIdxPassend(start,dir){
  const q=playerState.queue;
  for(let i=start;i>=0&&i<q.length;i+=dir){
    const x=libFind(q[i]);
    if(x&&x.vorhanden&&artPasst(x))return i;
  }
  return -1;
}
/* EINE Entscheidung „was kommt nach dem Titelende?" — playerAdvance UND die
   Übergänge (Crossfade/Gapless/Automix) fragen hier, damit Sleep, Radio,
   Wiederholen, Zufall und Abspielart überall gleich gelten (vorher kannten die
   Übergänge nur Radio und „alle" und blendeten an allem anderen vorbei).
   Reihenfolge wie bisher: Sleep „nach diesem Titel" · Radio (schlägt
   Wiederholen-eins) · eins · Zufall · nächster passender (alle: von vorn) ·
   Einzeltitel -> Bibliothek. xf: darf ein Übergang in diesen Titel laufen?
   bevorzugt: bei Zufall den schon gezogenen (vorbereiteten) Titel behalten.
   zufall: die Entscheidung kam aus einem Zufallszug (xfNaechsterIndex merkt ihn). */
function nachEnde(bevorzugt){
  if(sleepTitelende)return {art:'schlaf'};             // Sleep-Timer „nach diesem Titel"
  if(radioAktiv){                                    // Radio läuft linear + füllt endlos nach
    radioNachfuellen();
    const i=playerState.idx, weiter=i<playerState.queue.length-1;
    return {art:'titel', idx:weiter?i+1:i, xf:weiter};
  }
  if(playRepeat==='eins')return {art:'titel', idx:playerState.idx, xf:false};   // gleichen Titel neu starten
  const q=playerState.queue;
  if(playShuffle&&q.length>1){                         // Zufall: anderer PASSENDER Titel
    const kand=q.map((k,i)=>i)
      .filter(i=>i!==playerState.idx&&(x=>x&&x.vorhanden&&artPasst(x))(libFind(q[i])));
    if(!kand.length)return {art:'stopp'};
    const b=bevorzugt===undefined?-1:kand.findIndex(i=>q[i]===bevorzugt);
    return {art:'titel', idx:b>=0?kand[b]:kand[Math.floor(Math.random()*kand.length)], xf:true, zufall:true};
  }
  let n=queueIdxPassend(playerState.idx+1,1);             // nächster passender in der Reihe
  if(n<0&&playRepeat==='alle')n=queueIdxPassend(0,1);
  if(n>=0)return {art:'titel', idx:n, xf:true};
  return q.length<=1?{art:'bibliothek'}:{art:'stopp'};    // stopp: Playlist (nach Abspielart) zu Ende
}
function playerAdvance(d){                             // automatisch nach Titel-Ende
  if(!(d&&d.art))d=nachEnde();                         // plTitelEnde reicht seine Entscheidung durch
  if(d.art==='schlaf'){sleepAusloesen(); return;}
  if(d.art==='titel'){playerState.idx=d.idx; renderPlayerMedia(); return;}
  if(d.art==='bibliothek')naechstesAusBibliothek();
  // sonst: Playlist (nach Abspielart) zu Ende -> Stopp
}

/* Einzeltitel ohne Playlist zu Ende (14.07.): weiterspielen wie YouTube-
   Autoplay — der NÄCHSTE Titel der aktuellen Bibliotheks-Ansicht (Suche/
   Filter/Sortierung zählen), bei Zufall ein zufälliger; Blacklist bleibt
   außen vor. Am Ende der Bibliothek stoppt es ehrlich. */
function naechstesAusBibliothek(){
  const k=aktKey();
  const pool=libGefiltert().filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x));
  if(!pool.length)return;
  let nk=null;
  if(playShuffle){
    const kand=pool.filter(x=>x.id!==k);
    if(kand.length)nk=kand[Math.floor(Math.random()*kand.length)].id;
  }else{
    const i=pool.findIndex(x=>x.id===k);
    if(i>=0&&i<pool.length-1)nk=pool[i+1].id;      // der Nächste in der Ansicht
    else if(i<0)nk=pool[0].id;                     // aktueller nicht in der Ansicht -> von vorn
  }
  if(!nk)return;
  playerState.queue=[nk]; playerState.idx=0; playerState.quelle='Bibliothek';
  renderPlayerMedia();
}
function playMostPlayed(){
  let arr=libdaten.filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x))
    .sort((a,b)=>(b.plays||0)-(a.plays||0)).slice(0,100).map(x=>x.id);
  if(!arr.length){alert('Noch nichts abgespielt.');return;}
  if(playShuffle)mische(arr); playerPlay(arr,0,'★ Meistgespielt');
}
function playLetzte(){                                // „Zuletzt gespielt"
  const arr=libdaten.filter(x=>x.vorhanden&&(x.last_play||0)>0&&artPasst(x))
    .sort((a,b)=>(b.last_play||0)-(a.last_play||0)).slice(0,100).map(x=>x.id);
  if(!arr.length){alert('Noch nichts abgespielt.');return;}
  playerPlay(arr,0,'🕘 Zuletzt gespielt');
}

/* ---- 📻 Radio: endloser, personalisierter Zufalls-Stream ---- */
let radioAktiv=false;
// Build 144o (der Besitzer): „der favorit wird immer abgespielt." Im Zufalls-/Radio-Pool
// zählt nur der Favorit-Repräsentant jeder Gruppe (Hauptsong oder Clip).
function radioKandidaten(){const fb=libdaten.some(x=>typeof x.ist_favorit!=='undefined');
  return libdaten.filter(x=>x.vorhanden&&!x.blacklist&&artPasst(x)&&(!fb||x.ist_favorit));}
function radioPick(anzahl,vermeiden){
  const pool=radioKandidaten(); if(!pool.length)return [];
  // Vermeidungs-Fenster nie größer als der Pool minus 1 — sonst blockiert es bei
  // kleiner Bibliothek ALLE Titel und es käme nichts mehr (Bug 09.07.).
  const maxMeiden=Math.min(pool.length-1, 30);
  const letzte=new Set((vermeiden||[]).slice(-maxMeiden)), out=[];
  let schutz=anzahl*50;                               // Sicherung gegen Endlosschleife
  while(out.length<anzahl && schutz-->0){
    // gewichtete Wahl: beliebtere Titel häufiger (Gewicht = 1 + Abspielungen), aber alles möglich
    const gesamt=pool.reduce((s,x)=>s+1+(x.plays||0),0);
    let r=Math.random()*gesamt, pick=pool[0];
    for(const x of pool){r-=1+(x.plays||0); if(r<=0){pick=x;break;}}
    if(letzte.has(pick.id))continue;                 // keine kurzfristige Wiederholung
    out.push(pick.id); letzte.add(pick.id);
    if(letzte.size>maxMeiden)letzte.delete([...letzte][0]);
  }
  return out;
}
function radioStart(){
  const erste=radioPick(40,[]);
  if(!erste.length){alert('Noch keine abspielbaren Titel — lade erst etwas herunter.');return;}
  radioAktiv=true;
  playerState.queue=erste; playerState.idx=0; playerState.quelle='📻 Radio';
  ensurePlayer(); renderPlayerMedia();
  plInfo('📻 Radio läuft — endloser Mix aus deiner Bibliothek', true);   // Zustand
}
function radioNachfuellen(){                          // hält den Stream unendlich am Laufen
  if(radioAktiv && playerState.idx>=playerState.queue.length-2){
    const mehr=radioPick(20, playerState.queue.slice(-30));
    if(mehr.length)playerState.queue=playerState.queue.concat(mehr);
  }
}

/* ---- Sleep-Timer (Nutzer schaltet ein/aus) ---- */
let sleepTimer=null, sleepTitelende=false, sleepEndeZeit=0, sleepStufe='0', sleepAbgelaufen=false;   // sleepStufe: gewählte Minuten fürs Menü
function sleepSetzen(v){
  clearTimeout(sleepTimer); sleepTimer=null; sleepTitelende=false; sleepEndeZeit=0; sleepStufe='0';
  sleepAbgelaufen=false;                               // neu gestellt (auch „aus"): „abgelaufen" ist vorbei
  if(v==='titel'){sleepTitelende=true;}
  else{const min=parseInt(v,10)||0; if(min>0){sleepStufe=String(min); sleepEndeZeit=Date.now()+min*60000; sleepTimer=setTimeout(sleepAusloesen,min*60000);}}
  sleepLabel();
  xfPruefen();                                         // „nach diesem Titel": eine laufende Blende zurücknehmen
}
function sleepAusloesen(){
  // Gerät VLC hat kein pl-el: dort den Motor anhalten (sonst spielte er weiter).
  // Nur die MUSIK (24.09.: „nein, nur musik"): Film und Musik teilen EINEN
  // VLC — nur_key lässt den Server nur pausieren, wenn er diesen Titel spielt.
  if(vlcAktiv())vlcBefehl('pause',{nur_key:aktKey()}); else{const el=document.getElementById('pl-el'); if(el)el.pause();}
  sleepTimer=null; sleepEndeZeit=0; sleepTitelende=false; sleepStufe='0'; sleepLabel();
  sleepAbgelaufen=true;}                               // … und nach einem Filmende startet nichts mehr (nachFilmEnde)
/* Sleep-Timer aktiv (Minuten oder „nach diesem Titel") oder abgelaufen, bis er
   neu gestellt wird — der Besitzer 24.09.2026: nach einem Filmende startet dann nichts. */
function sleepHaeltAn(){return !!(sleepTimer||sleepTitelende||sleepAbgelaufen);}
function sleepLabel(){const l=document.getElementById('sleepval'); if(!l)return;
  l.textContent=sleepTitelende?'· nach diesem Titel':(sleepEndeZeit?('· noch '+Math.max(1,Math.round((sleepEndeZeit-Date.now())/60000))+' min'):'');}

/* ---- Ausschnitt/Clip: vorne + hinten schneiden -> ein Video (ffmpeg, ohne Längenlimit) ---- */
/* ✂-Schneide-Leiste (Build 101, Vorgabe: „zwei Regler ziehen können") — ersetzt die
   alten mm:ss-Eingabefelder. Griff ziehen springt den Player LIVE an die
   Stelle (B-Griff kurz davor, damit man das Ende hört); läuft die Wiedergabe
   in die B-Marke, pausiert sie. ✂ speichert wie bisher nicht-destruktiv
   als NEUEN Bibliothekseintrag (das Original bleibt). */
let schnitt=null;                                      // {id,a,b,dauer}
async function clipDialog(id){
  if(!id){alert('Kein Titel gewählt.');return;}
  if(aktKey()!==id){playerPlay([id]); await new Promise(r=>setTimeout(r,500));}
  // Am Gerät VLC gibt es kein <audio>-Element — Dauer/Position kommen aus
  // dem letzten VLC-Status (05.08.: ✂ auch im VLC-Modus).
  let dauer, curT;
  if(vlcAktiv()&&aktKey()===id&&vlcDauerLetzte){
    dauer=vlcDauerLetzte; curT=vlcPosLetzte||0;
  }else{
    const el=document.getElementById('pl-el');
    if(!el||!isFinite(el.duration)||!el.duration){toast('Titel lädt noch — gleich nochmal ✂ drücken.');return;}
    dauer=el.duration; curT=el.currentTime;
  }
  schnittZu();
  schnitt={id, a:0, b:(curT>1&&curT<dauer-1)?curT:dauer, dauer};
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='schnitt-fly'; fly.tabIndex=-1; fly.style.height='auto';
  fly.innerHTML='<div class="abo-fly-titel">✂ Ausschnitt wählen<span class="spacer"></span>'+
    '<button class="ib" title="Schließen (Esc)" onclick="schnittZu()">✕</button></div>'+
    '<div class="schnitt-spur" id="schnitt-spur">'+
      '<div class="schnitt-bereich" id="schnitt-bereich"></div>'+
      '<div class="schnitt-griff" id="schnitt-a" title="Anfang ziehen — der Player springt mit">A</div>'+
      '<div class="schnitt-griff" id="schnitt-b" title="Ende ziehen — der Player springt kurz davor">B</div></div>'+
    '<div class="schnitt-zeiten"><span id="schnitt-za"></span><span id="schnitt-zl"></span><span id="schnitt-zb"></span></div>'+
    '<div class="abo-staffel" style="margin-top:8px"><span style="opacity:.7">Wiedergabe endet an B.</span><span class="spacer"></span>'+
      '<button class="btn mini" onclick="schnittVorhoeren()" title="Den gewählten Bereich von A an abspielen">▶ Bereich</button>'+
      '<button class="btn mini" onclick="schnittSpeichern(this)" title="Bereich als NEUEN Titel speichern — das Original bleibt unangetastet">✂ Ausschnitt speichern</button></div>';
  document.body.appendChild(fly); nachVorn(fly);
  const m=document.querySelector('.pl-media'), r0=m?m.getBoundingClientRect():null;
  const w=Math.min(560, window.innerWidth-24);
  fly.style.width=w+'px';
  fly.style.left=Math.max(12,Math.min((r0?r0.left+(r0.width-w)/2:12), window.innerWidth-12-w))+'px';
  fly.style.top=Math.max(12,(r0?Math.min(r0.bottom-140, window.innerHeight-160):window.innerHeight/2))+'px';
  fly.addEventListener('keydown',e=>{if(e.key==='Escape'){schnittZu(); e.stopPropagation();}});
  ['schnitt-a','schnitt-b'].forEach(g=>document.getElementById(g).addEventListener('pointerdown',schnittDrag));
  el.addEventListener('timeupdate',schnittTick);
  fly.focus();
  schnittMalen();
}
function schnittZu(){
  const f=document.getElementById('schnitt-fly'); if(f)f.remove();
  const el=document.getElementById('pl-el'); if(el)el.removeEventListener('timeupdate',schnittTick);
  schnitt=null;
}
function schnittTick(){
  const el=document.getElementById('pl-el');
  if(!schnitt||!el)return;
  if(aktKey()!==schnitt.id){schnittZu();return;}       // Titel gewechselt -> Leiste weg
  if(el.currentTime>=schnitt.b&&!el.paused)el.pause(); // „…und beendet" (der Besitzer)
}
function schnittMalen(){
  if(!schnitt)return;
  const spur=document.getElementById('schnitt-spur'); if(!spur)return;
  const w=spur.clientWidth, pa=schnitt.a/schnitt.dauer*w, pb=schnitt.b/schnitt.dauer*w;
  const ber=document.getElementById('schnitt-bereich');
  ber.style.left=pa+'px'; ber.style.width=Math.max(2,pb-pa)+'px';
  document.getElementById('schnitt-a').style.left=pa+'px';
  document.getElementById('schnitt-b').style.left=pb+'px';
  document.getElementById('schnitt-za').textContent='A '+zeit(schnitt.a);
  document.getElementById('schnitt-zb').textContent='B '+zeit(schnitt.b);
  document.getElementById('schnitt-zl').textContent='Länge '+zeit(Math.max(0,schnitt.b-schnitt.a));
}
function schnittDrag(ev){
  if(!schnitt)return;
  ev.preventDefault(); ev.stopPropagation();
  const griffA=ev.currentTarget.id==='schnitt-a';
  const spur=document.getElementById('schnitt-spur');
  const el=document.getElementById('pl-el');
  function mv(e){
    const r=spur.getBoundingClientRect();
    const t=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width))*schnitt.dauer;
    if(griffA)schnitt.a=Math.min(t,schnitt.b-1);
    else schnitt.b=Math.max(t,schnitt.a+1);
    if(el){el.currentTime=griffA?schnitt.a:Math.max(schnitt.a,schnitt.b-1.5);}   // live mithören
    schnittMalen();
  }
  function up(){document.removeEventListener('pointermove',mv);document.removeEventListener('pointerup',up);}
  document.addEventListener('pointermove',mv);document.addEventListener('pointerup',up);
  mv(ev);
}
function schnittVorhoeren(){
  const el=document.getElementById('pl-el');
  if(!schnitt||!el)return;
  el.currentTime=schnitt.a; el.play();
}
async function schnittSpeichern(btn){
  if(!schnitt)return;
  const daten={id:schnitt.id, start:schnitt.a>0.5?zeit(schnitt.a):'', ende:schnitt.b<schnitt.dauer-0.5?zeit(schnitt.b):''};
  if(btn){btn.disabled=true; btn.textContent='⏳ …';}
  plInfo('✂ Ausschnitt wird erstellt …', true);
  try{
    const d=await api('/api/clip',daten);
    // Build 144i (25.07.: „zeigt dass er es geschafft hat, aber die
    // Fehlermeldung"): Hier wurde eine NIE deklarierte Variable geprüft — der
    // Erfolgspfad warf dadurch einen ReferenceError, der unten im catch als
    // „fehlgeschlagen" ankam, obwohl die Datei längst da war.
    // plInfo() ist der richtige Weg (wie überall sonst im Player).
    if(d.fehler){plInfo(''); alert('Ausschnitt: '+d.fehler); if(btn){btn.disabled=false;btn.textContent='✂ Ausschnitt speichern';}}
    else{plInfo('✂ Ausschnitt erstellt: '+d.name); toast('✂ '+d.name); libLaden(); schnittZu();}
  }catch(e){alert('Ausschnitt fehlgeschlagen (App erreichbar?).'); if(btn){btn.disabled=false;btn.textContent='✂ Ausschnitt speichern';}}
}

function ext(n){const m=(n||'').match(/\.([a-z0-9]+)$/i); return m?m[1].toUpperCase():'–';}
// Wählbare Spalten (= „Reiter"): Beschriftung, Text-Funktion, Sortier-Funktion
const COLDEF={
  kategorie:{l:'Kategorie', t:x=>x.kategorie, s:x=>x.kategorie||''},
  qualitaet:{l:'Qualität', t:x=>x.qualitaet, s:x=>x.qualitaet||''},
  technik:{l:'Codec / Audio', t:x=>technikText(x), s:x=>x.abr||0},
  groesse:{l:'Größe', t:x=>mb(x.groesse), s:x=>x.groesse||0},
  dauer:{l:'Dauer', t:x=>x.dauer?zeit(x.dauer):'–', s:x=>x.dauer||0},
  uploader:{l:'Kanal', t:x=>x.uploader||'–', s:x=>x.uploader||''},
  kuenstler:{l:'Künstler', t:x=>x.kuenstler||'–', s:x=>x.kuenstler||''},
  album:{l:'Album', t:x=>x.album||'–', s:x=>x.album||''},
  upload_date:{l:'Datum', t:x=>ytdatum(x.upload_date)||'–', s:x=>x.upload_date||''},
  status:{l:'Status', t:x=>x.vorhanden?'vorhanden':'verschoben', s:x=>x.vorhanden?1:0},
  abr:{l:'Bitrate', t:x=>x.abr?x.abr+' kbps':'–', s:x=>x.abr||0},
  asr:{l:'Samplerate', t:x=>x.asr?Math.round(x.asr/1000)+' kHz':'–', s:x=>x.asr||0},
  hoehe:{l:'Auflösung', t:x=>x.hoehe?x.hoehe+'p':'–', s:x=>x.hoehe||0},
  videoid:{l:'Video-ID', t:x=>x.videoid, s:x=>x.videoid||''},
  added:{l:'Hinzugefügt', t:x=>x.ts?new Date(x.ts*1000).toLocaleDateString('de-DE'):'–', s:x=>x.ts||0},
  plays:{l:'Abspielungen', t:x=>String(x.plays||0), s:x=>x.plays||0},
  folge:{l:'Folge #', t:x=>x.abo_nr?('#'+x.abo_nr):'–', s:x=>x.abo_nr||0},
  // Build 144g (Punkt 4): „Videonummer je Kanal" — ausdrücklich NICHT die
  // Track-Nummer (die stünde bei Einzelvideos 500-mal auf 1). Bei Abos ist es
  // die echte Nummer aus dem Backkatalog, sonst die Position innerhalb der
  // Videos dieses Kanals hier. „von" macht die Bezugsgröße sichtbar.
  // An echter Bibliothek gemessen: 69 von 84 Titeln stünden auf „#1" —
  // nicht als Track-Nummer, sondern weil er von den meisten Kanälen genau EIN
  // Video hat. Angezeigt sähe das aus wie die befürchtete „500× die 1".
  // Deshalb: eine abgeleitete Nummer erscheint nur, wenn es beim selben Kanal
  // etwas zu ordnen GIBT. Die echte Abo-Nummer steht immer — sie zählt über
  // den ganzen Kanal und sagt auch bei einem einzelnen Video etwas aus.
  kanalnr:{l:'Kanal #', t:x=>x.abo_nr?('#'+x.abo_nr)
                          :(x.kanal_von>1?('#'+x.kanal_nr+' von '+x.kanal_von):'–'),
           s:x=>x.kanal_nr||0},
  // Etappe A (Spec Punkt 5): Genre aus MusicBrainz — Grundlage der TV-Bibliothek.
  genre:{l:'Genre', t:x=>x.genre||'–', s:x=>(x.genre||'').toLowerCase()},
  ext:{l:'Endung', t:x=>ext(x.name), s:x=>ext(x.name)}
};
const COLALL=Object.keys(COLDEF);
const COLDEFAULT=['kategorie','qualitaet','technik','groesse','dauer','uploader','upload_date','status'];
let libcols=ladeCols(), libsort=ladeSort();

function ladeCols(){
  let cfg=null; try{cfg=JSON.parse(localStorage.getItem('ytdl_libcols_v1'));}catch(e){}
  if(Array.isArray(cfg)&&cfg.every(c=>c&&COLALL.includes(c.key))){
    COLALL.forEach(k=>{if(!cfg.find(c=>c.key===k))cfg.push({key:k,sichtbar:false});});
    return cfg.filter(c=>COLALL.includes(c.key));
  }
  return COLALL.map(k=>({key:k,sichtbar:COLDEFAULT.includes(k)}));
}
function saveCols(){lsSchreiben('ytdl_libcols_v1',JSON.stringify(libcols));}
function sichtbareCols(){return libcols.filter(c=>c.sichtbar).map(c=>c.key);}
function ladeSort(){try{const s=JSON.parse(localStorage.getItem('ytdl_libsort_v1'));if(s&&s.key)return s;}catch(e){}return {key:'neu',dir:-1};}
function saveSort(){lsSchreiben('ytdl_libsort_v1',JSON.stringify(libsort));}

let _libSig=null;
async function libLaden(){
  // Ausdruecklicher Aufruf (Aktion, Auswahl aufheben, Menue frisch): IMMER zeichnen.
  try{const r=await fetch('/api/bibliothek'); const txt=await r.text(); _libSig=txt;
      const d=JSON.parse(txt); libdaten=d.items||[]; libMalen();}catch(e){}
}
async function libPoll(){
  // Der 5-Sekunden-Takt baute bisher IMMER das ganze Bibliotheks-innerHTML neu auf
  // -- dabei werden alle <img> neu erzeugt, und Thumbnails ohne Browser-Cache laden
  // sichtbar nach (Flackern alle 5 s, der Besitzer 25.07.: „ein paar, John Waite …"). Jetzt
  // im Takt nur zeichnen, wenn sich die Antwort WIRKLICH geaendert hat.
  try{const r=await fetch('/api/bibliothek'); const txt=await r.text();
      if(txt===_libSig)return; _libSig=txt;
      const d=JSON.parse(txt); libdaten=d.items||[]; libMalen();}catch(e){}
}
function libAnsicht(m){
  libModus=m;
  document.getElementById('vb-kachel').classList.toggle('an',m==='kachel');
  document.getElementById('vb-alben').classList.toggle('an',m==='alben');
  document.getElementById('vb-liste').classList.toggle('an',m==='liste');
  libMalen();
}
function libArchivToggle(){
  libArchiv=!libArchiv;
  const b=document.getElementById('libarchivbtn');
  b.classList.toggle('an',libArchiv); b.textContent=libArchiv?'← Zurück zur Bibliothek':'🗄 Archiv anzeigen';
  libMalen();
}
async function libEnrich(btn){
  btn.disabled=true; const t=btn.textContent; btn.textContent='lädt…';
  try{await api('/api/biblio_enrich');}catch(e){}
  setTimeout(()=>{btn.disabled=false; btn.textContent=t; libLaden();},2000);
}
function ytdatum(d){if(!d||d.length!==8)return'';return d.slice(6,8)+'.'+d.slice(4,6)+'.'+d.slice(0,4);}
function technikText(x){
  // Nach der WIRKLICH servierten Datei entscheiden (dateiart vom Server):
  // fehlt das Video und es gibt nur die MP3, gehört die Audio-Ansicht
  // (Cover+Visualizer) her — statt schwarzem Video-Element (14.07.).
  const istAudio=x.dateiart?x.dateiart==='audio':((x.kategorie==='MP3')||(!x.vcodec&&x.acodec));
  const p=[];
  if(istAudio){
    if(x.acodec)p.push(x.acodec.toUpperCase());
    if(x.abr)p.push(x.abr+' kbps');
    if(x.asr)p.push(Math.round(x.asr/1000)+' kHz');
  }else{
    if(x.vcodec)p.push(x.vcodec.toUpperCase());
    if(x.hoehe)p.push(x.hoehe+'p');
    if(x.acodec)p.push(x.acodec.toUpperCase());
  }
  return p.join(' · ')||'–';
}

function sortVal(x,key){
  if(key==='neu')return x.ts||0;
  if(key==='titel')return (x.titel||'').toLowerCase();
  const d=COLDEF[key]; return d?d.s(x):0;
}
function libGefiltert(){
  const q=(document.getElementById('libsuche').value||'').toLowerCase().trim();
  // Playlist-Ansicht: nur die Titel dieser Playlist, in Playlist-Reihenfolge (keine Sortierung).
  if(libPlaylistView){
    const p=plState.find(x=>x.id===libPlaylistView);
    let arr=(p?p.items:[]).map(k=>libFind(k)).filter(Boolean).filter(artPasst);
    if(q)arr=arr.filter(x=>(x.titel+' '+(x.uploader||'')).toLowerCase().includes(q));
    return arr;
  }
  const f=document.getElementById('libfilter').value;
  const hide=document.getElementById('libhidegray').checked;
  // Build 144o (der Besitzer): Es erscheint nur der FAVORIT jeder Gruppe als Kachel
  // (Hauptsong ODER ein Ausschnitt); die Alternativen liegen im Rechtsklick.
  // Solange die API das Feld noch nicht liefert (kurz vor dem Selbst-Neustart),
  // NICHT filtern — sonst sähe die Bibliothek leer aus.
  // Build 144l: „Nur Songs" steckt in der Abspielart (artPasst), wirkt überall.
  const favBekannt=libdaten.some(x=>typeof x.ist_favorit!=='undefined');
  let arr=libdaten.filter(x=>!favBekannt||x.ist_favorit).filter(x=>!!x.archiviert===libArchiv).filter(artPasst);
  if(f==='vorhanden')arr=arr.filter(x=>x.vorhanden);
  else if(f==='verschoben')arr=arr.filter(x=>!x.vorhanden);
  else if(f==='herz')arr=arr.filter(x=>x.herz);        // ❤ Lieblingssongs (05.08.)
  if(hide&&!libArchiv)arr=arr.filter(x=>x.vorhanden);
  if(q)arr=arr.filter(x=>(x.titel+' '+(x.uploader||'')).toLowerCase().includes(q));
  const key=libsort.key, dir=libsort.dir;
  arr.sort((a,b)=>{
    let va=sortVal(a,key), vb=sortVal(b,key), c;
    if(typeof va==='number')c=va-vb; else c=String(va).localeCompare(String(vb));
    c=dir<0?-c:c;
    if(c===0&&key!=='titel')return (a.titel||'').localeCompare(b.titel||'');   // Sekundär immer Titel
    return c;
  });
  return arr;
}
function fuelleSortSelect(){
  const sel=document.getElementById('libsort'); if(!sel)return;
  const opts=[['neu','Neueste zuerst'],['titel','Titel A–Z']].concat(sichtbareCols().map(k=>[k,COLDEF[k].l]));
  sel.innerHTML=opts.map(([k,l])=>`<option value="${k}">${l}</option>`).join('');
  sel.value=opts.find(o=>o[0]===libsort.key)?libsort.key:'neu';
}
function setSortSelect(v){libsort={key:v,dir:v==='neu'?-1:1}; saveSort(); libMalen();}
function setSort(key){
  if(libsort.key===key)libsort.dir=-libsort.dir; else libsort={key,dir:key==='neu'?-1:1};
  saveSort(); libMalen();
}
function pfeil(key){return libsort.key===key?(libsort.dir<0?' ▼':' ▲'):'';}

function colMenuToggle(ev){ if(ev)ev.stopPropagation();
  const m=document.getElementById('libcolmenu'); const zu=m.style.display==='none';
  m.style.display=zu?'block':'none';
  // Build 125: erst zeichnen (sonst misst popoverBei eine leere Box), dann
  // an den <body> hängen und am Knopf ausrichten.
  // Build 125: Das Spalten-Menü löst das Ansicht-Menü ab, statt sich darüber
  // zu legen (gemessen: beide offen überlappten sich). Genauso machen es die
  // Nachbar-Einträge „Dubletten" und „Auto-Tagging" mit ansichtZu().
  // Anker bleibt der ⚙-Knopf — der ist immer sichtbar, der Menüeintrag nicht.
  if(zu){ansichtZu(); colMenuMalen();
    menuAnBody(m, document.getElementById('libansichtbtn'));}}
function colMenuMalen(){
  const m=document.getElementById('libcolmenu');
  m.innerHTML='<div class="colmenu-titel">Spalten — Häkchen = anzeigen, Pfeile = Reihenfolge.<br>Klick auf eine Spaltenüberschrift sortiert danach.</div>'+
    libcols.map((c,i)=>`<div class="colrow">
      <button class="colmv" data-i="${i}" onclick="colMove(+this.dataset.i,-1)" ${i===0?'disabled':''}>▲</button>
      <button class="colmv" data-i="${i}" onclick="colMove(+this.dataset.i,1)" ${i===libcols.length-1?'disabled':''}>▼</button>
      <label><input type="checkbox" ${c.sichtbar?'checked':''} data-col="${esc(c.key)}" onchange="colToggle(this.dataset.col)"> ${COLDEF[c.key].l}</label>
    </div>`).join('');
}
function colMove(i,d){const j=i+d; if(j<0||j>=libcols.length)return; const t=libcols[i]; libcols[i]=libcols[j]; libcols[j]=t; saveCols(); colMenuMalen(); libMalen();}
function colToggle(key){const c=libcols.find(x=>x.key===key); if(c)c.sichtbar=!c.sichtbar; saveCols(); colMenuMalen(); libMalen();}

function bulkMalen(){
  const bulk=document.getElementById('libbulk'); if(!bulk)return;
  // Das ＋ neben der Playlist-Liste erscheint nur, wenn es etwas
  // hinzuzufuegen GIBT — sonst waere es ein Knopf ohne Aufgabe.
  const plus=document.getElementById('plplus');
  if(plus)plus.style.display=libAuswahl.size?'':'none';
  if(!libAuswahl.size){bulk.style.display='none'; bulk.innerHTML=''; return;}
  bulk.style.display='';
  // Build 143 (der Besitzer, JEDEN Knopf einzeln durchgegangen): Abspielen -> Ziehen in
  // den Player; Tags/Metadaten -> passiert automatisch, Einzelfaelle per
  // Rechtsklick; Archivieren/Aus Archiv/Loeschen -> Rechtsklick kann es
  // besser; Aufheben -> Klick ins Leere. Damit blieb kein einziger Knopf
  // uebrig, der seine Zeile wert waere. Vorgabe: „Die simplen Dinge sind oft die
  // schoensten." Es bleibt die reine Anzeige, WIE VIELE markiert sind.
  bulk.innerHTML=`<b>${libAuswahl.size} ausgewählt</b>`+
    `<span class="muted2" style="font-size:11.5px">· ziehen = in den Player oder auf „Playlist:" · Rechtsklick = alles Weitere${NUR_FERN?'':libPlaylistView?' · Entf = aus der Playlist':' · Entf = in den Papierkorb'} · Klick ins Leere hebt auf</span>`;
}
function libMalen(){
  fuelleSortSelect();
  document.getElementById('libselbtn').classList.toggle('an',libSelectMode);
  bulkMalen();
  const el=document.getElementById('libinhalt'); if(!el)return;
  const arr=libGefiltert();
  if(!arr.length){
    // Build 118 („Warum ist Suchen nicht automatisch Text? Wenn man nichts
    // findet, könnte es doch automatisch kommen"): steht ein Suchwort im Feld
    // und die Bibliothek gibt nichts her, wird OHNE Zutun im gesprochenen Text
    // weitergesucht — das Ergebnis erscheint direkt hier darunter.
    const q=(document.getElementById('libsuche').value||'').trim();
    if(q.length>1&&!libPlaylistView&&!libArchiv){
      el.innerHTML='<div class="libleer">Nichts im Titel gefunden — ich schaue im gesprochenen Text …</div>';
      clearTimeout(window._volltextTimer);
      window._volltextTimer=setTimeout(async()=>{                 // erst wenn das Tippen ruht
        if(((document.getElementById('libsuche')||{}).value||'').trim()!==q)return;
        try{
          const r=await fetch('/api/transkript_suche?q='+encodeURIComponent(q));
          const d=await r.json(); const tr=d.items||d||[];
          const box=document.getElementById('libinhalt'); if(!box)return;
          box.innerHTML=tr.length
            ?'<div class="libleer">Im Titel nichts — aber '+tr.length+' Titel sagen/singen „'+esc(q)+'":</div>'+
             '<div style="padding:0 10px 10px">'+tr.slice(0,25).map(x=>
               '<div class="mbtn" style="text-align:left" onclick="transkriptSuche()">🔎 '+esc(x.titel||'')+
               ' <span style="color:var(--gedaempft)">('+((x.treffer||[]).length)+'×'+
               (x.quelle?' · '+esc(x.quelle):'')+')</span></div>').join('')+'</div>'
            :'<div class="libleer">Nichts gefunden — weder im Titel noch im gesprochenen Text.</div>';
        }catch(e){}
      },600);
      return;
    }
    el.innerHTML='<div class="libleer">'+(libPlaylistView?'Diese Playlist ist noch leer — füge mit ＋ Titel hinzu.':libArchiv?'Archiv ist leer.':'Nichts gefunden — lade etwas herunter oder ändere den Filter.')+'</div>'; return;}
  el.innerHTML = libModus==='kachel' ? kacheln(arr) : libModus==='alben' ? albenHTML(arr) : listeTab(arr);
  transportRender();                                  // neu erzeugte Kacheln zeigen den laufenden Zustand
  // Build 135: Rahmen-Auswahl aufziehen. Der Zuhörer sitzt am Behälter, nicht
  // an den Kacheln — er soll ja gerade auf FREIER Fläche anspringen.
  el.onpointerdown=libBandStart;
  // Build 143 („ich kann immer noch kein Fenster ziehen von einer Reihe
  // ueber der Bibliothek, das ist frustrierend"). Gemessen: ueber der ersten
  // Kachelreihe liegt gar nicht mehr libinhalt, sondern die KARTE — dort kam
  // der Zuhoerer nie an. Jetzt hoert die ganze Bibliotheks-Karte mit;
  // Bedienelemente filtert libBandStart ohnehin heraus.
  const karte=el.closest('.card'); if(karte)karte.onpointerdown=libBandStart;
  /* Build 144e (mit Bild, dieselbe Regel wie in der Playlist): „solange es
     in dem fenster ist, ist ein feld ziehen gewaehrleistet." Auch hier endet
     die Karte am Inhalt — bei der auf einen Treffer gefilterten Bibliothek
     gemessen 105 px Schwarz darunter, ohne Zuhoerer. Das Fenster ist der
     `panel-body`. */
  const koerper=el.closest('.panel-body'); if(koerper)koerper.onpointerdown=libBandStart;
}

/* ---- Alben-Ansicht: nach Künstler/Album gruppiert (Felder aus dem Auto-Tagging) ---- */
let _albGruppen=[];
function albPlay(i){const g=_albGruppen[i]; if(g)playerPlay(g.filter(x=>x.vorhanden).map(x=>x.id),0);}
function albenHTML(arr){
  const gr=new Map(); const rest=[];
  arr.forEach(x=>{
    if(x.album){const k=(x.kuenstler||x.uploader||'?')+'|||'+x.album;
      if(!gr.has(k))gr.set(k,[]); gr.get(k).push(x);}
    else rest.push(x);
  });
  _albGruppen=[];
  let h='';
  [...gr.entries()].sort((a,b)=>a[0].localeCompare(b[0])).forEach(([k,g])=>{
    const i=_albGruppen.push(g)-1, teile=k.split('|||');
    h+=`<div class="albgrp"><div class="albkopf">`+
      `<button class="ib play" data-i="${i}" onclick="albPlay(+this.dataset.i)" title="Album abspielen">▶</button>`+
      `<span class="albtitel">${esc(teile[1])}</span><span class="albku">${esc(teile[0])}</span>`+
      `<span class="albn">${g.length} Titel${g[0].jahr?' · '+esc(g[0].jahr):''}</span></div>`+kacheln(g)+`</div>`;
  });
  if(rest.length)
    h+=`<div class="albgrp"><div class="albkopf"><span class="albtitel" style="color:var(--gedaempft)">Ohne Album-Info</span>`+
      `<span class="albn">${rest.length} Titel — Tags holen: ⚙ Ansicht → 🏷 Auto-Tagging</span></div>`+kacheln(rest)+`</div>`;
  return h||'<div class="libleer">Nichts gefunden.</div>';
}

/* Auto-Tagging anstoßen (alles ohne Album bzw. die aktuelle Auswahl) */
async function autotagAlle(){
  if(!confirm('Auto-Tagging: Musik ohne Album-Info bei MusicBrainz nachschlagen und\nKünstler / Titel / Album eintragen (auch in die MP3-Dateien).\n\nLäuft im Hintergrund, ca. 1 Titel pro Sekunde. Starten?'))return;
  await api('/api/autotag');
}
// Symbol für die Art des Titels: 🎵 Musik/MP3, 🎬 hochauflösend, 🎥 normales Video.
function katIcon(x){
  const audio=(x.kategorie==='MP3')||(!x.vcodec&&x.acodec);
  if(audio)return '🎵';
  if((x.hoehe||0)>=2160||x.kategorie==='4K+')return '🎬';
  return '🎥';
}
// Schlanke Info-Zeile im Spotify-Stil: Symbol · Dauer · Größe · Kanal.
function kachelInfo(x){
  const teile=[];
  if(x.dauer)teile.push(zeit(x.dauer));
  teile.push(mb(x.groesse));
  const wer=x.kuenstler||x.uploader;                   // getaggter Künstler schlägt den Kanalnamen
  if(wer)teile.push(esc(wer));
  return katIcon(x)+' '+teile.join(' · ');
}
// Wenige, ruhige Icon-Knöpfe. Alles Weitere steckt im „⋯"-Menü (aufgeräumt).
/* ❤ Lieblingssongs (05.08.: „zu den lieblingssongs sollte ein herz sein") */
function herzKnopf(x){
  return `<button class="ib herz${x.herz?' an':''}" data-key="${esc(x.id)}" onclick="event.stopPropagation();herzToggle(this.dataset.key)" `+
    `title="${x.herz?'❤ Lieblingssong — Herz entfernen':'Als Lieblingssong markieren'}">${x.herz?'♥':'♡'}</button>`;
}
async function herzToggle(id){
  const x=libFind(id); if(!x)return;
  x.herz=!x.herz;                                      // sofort sichtbar, Server zieht nach
  try{api('/api/biblio',{id, art:'herz'}).catch(()=>{});}catch(e){}
  document.querySelectorAll('[data-tr="herz"]').forEach(b=>{
    if(aktKey()===id){b.textContent=x.herz?'♥':'♡'; b.classList.toggle('an',!!x.herz);}});
  libMalen();
}
function aktBtnsKachel(x){
  let b='';
  if(x.vorhanden){
    b+=`<button class="ib play" data-key="${esc(x.id)}" onclick="event.stopPropagation();playerPlay([this.dataset.key])" title="Abspielen">▶</button>`;
    b+=herzKnopf(x);
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="plAddMenu(event,this.dataset.key)" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="event.stopPropagation();biblio(this.dataset.key,'ordner')" title="Im Ordner zeigen">📁</button>`;
  }else{
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="event.stopPropagation();biblioNeuladen(this.dataset.key)" title="Fehlende Datei erneut laden">⬇</button>`;
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="plAddMenu(event,this.dataset.key)" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
  }
  b+=`<button class="ib" data-key="${esc(x.id)}" onclick="libItemMenu(event,this.dataset.key)" title="Mehr… (auch per Rechtsklick)">⋯</button>`;
  return b;
}
/* ---- Menü-Werkzeuge (Explorer-Stil) ---- */
function menuSchliesser(m){                            // Außenklick schließt Menü + offene Flyouts
  // Build 128 (Fund: „das Fenster ging eben nicht weg, auch wenn ich
  // nichts angewählt habe"). Wurzel: diese Funktion nahm `m` entgegen und
  // benutzte es NIE — sie räumte hartkodiert nur `.itemmenu` weg. Wer sie
  // mit einer anderen Klasse aufrief (die Link-Rückfrage und der
  // Mengen-Regler sind `.panelmenu`), bekam stillschweigend gar kein
  // Schließen. Jetzt schließt sie das übergebene Menü mit — damit gilt sie
  // für JEDEN künftigen Aufrufer, egal welche Klasse er wählt.
  setTimeout(()=>{
    const zu=(e2)=>{
      const t=e2.target;
      const drin=t&&t.closest&&(t.closest('.itemmenu')||(m&&m.contains(t)));
      if(drin)return;                                 // Klick INS Menü: offen lassen
      // Toggle-Gedächtnis (05.08.: „wenn ich es nochmal anklicke, dann
      // sollte es sich schließen"): dieses pointerdown räumt das Menü weg —
      // kommt gleich der click desselben Knopfs, darf der NICHT neu öffnen.
      _menuZuKnopf=(t&&t.closest)?t.closest('button'):null; _menuZuTs=Date.now();
      document.querySelectorAll('.itemmenu').forEach(x=>x.remove());
      if(m)m.remove();
      document.removeEventListener('pointerdown',zu,true);
      document.removeEventListener('keydown',esc,true);
    };
    // Esc schließt ebenfalls — dasselbe Bedürfnis („weg damit"), nur über
    // die Tastatur; sonst bliebe das Fenster bei reiner Tastaturbedienung.
    const esc=(e2)=>{ if(e2.key==='Escape')zu({target:document.body}); };
    document.addEventListener('pointerdown',zu,true);
    document.addEventListener('keydown',esc,true);
  },0);
}
let _menuZuKnopf=null, _menuZuTs=0;                    // s. menuSchliesser (Toggle)
function menuGeradeZu(knopf){
  // Wahr, wenn der Außenklick-Schließer das Menü soeben über GENAU diesen
  // Knopf weggeräumt hat — dann ist der laufende click das Zumachen.
  if(_menuZuKnopf&&knopf===_menuZuKnopf&&Date.now()-_menuZuTs<400){_menuZuKnopf=null; return true;}
  return false;
}
function aktionsMenu(ev,eintraege){                    // generisches Klick-Menü an einem Knopf
  ev.stopPropagation();
  if(menuGeradeZu(ev.currentTarget))return;            // 2. Klick = schließen (05.08.)
  eintraege=menuFuerGeraet(eintraege);                 // Gerät im WLAN: ohne nur-PC-Einträge
  document.querySelectorAll('.itemmenu').forEach(m=>m.remove());
  const m=document.createElement('div'); m.className='itemmenu';
  m.innerHTML=eintraege.map((e,i)=>`<button data-i="${i}">${e[0]}</button>`).join('');
  document.body.appendChild(m);
  popoverBei(m, ev.currentTarget.getBoundingClientRect());
  m.querySelectorAll('button').forEach(b=>b.onclick=(e2)=>{e2.stopPropagation(); const f=eintraege[+b.dataset.i][1]; m.remove(); f();});
  menuSchliesser(m);
}
function ansichtToggle(ev){ if(ev)ev.stopPropagation();
  const m=document.getElementById('libansicht'); const zu=m.style.display==='none';
  m.style.display=zu?'block':'none';
  if(zu)menuAnBody(m, document.getElementById('libansichtbtn'));   // Build 125: frei am <body>
  if(zu){const s=(e2)=>{if(!m.contains(e2.target)&&e2.target.id!=='libansichtbtn'&&!e2.target.closest('#libcolmenu')){
      ansichtZu(); document.removeEventListener('pointerdown',s,true);}};
    setTimeout(()=>document.addEventListener('pointerdown',s,true),0);}
}
function ansichtZu(){const m=document.getElementById('libansicht'); if(m)m.style.display='none';}
function plWerkzeuge(ev){
  // Build 124 (der Besitzer): Was die schmale Leiste ausblendet, taucht HIER oben auf —
  // ausgeblendet heißt nie unerreichbar. Sichtbar in der Leiste? Dann nicht
  // doppelt anbieten.
  const versteckt=el=>{const e=document.querySelector(el);
    return !e||getComputedStyle(e).display==='none'||e.getBoundingClientRect().width<2;};
  const extra=[];
  if(versteckt('.plbar .btn[onclick*="mixeMenu"]'))extra.push(['🎛 Mixer…', mixeMenu]);
  aktionsMenu(ev,extra.concat([
  ['📻 Neues entdecken', entdeckerOeffnen],
  nurPc(['✎ Umbenennen', plRename]),
  nurPc(['🗑 Löschen', plDelete]),
  nurPc(['⇄ Sync einrichten…', plSyncConfig]),
  nurPc(['⇄ Jetzt synchronisieren', ()=>plSyncNow()]),
  ['⤓ Als .m3u exportieren', plExport],
  nurPc(['⤒ .m3u importieren…', ()=>document.getElementById('m3ufile').click()])]));}

/* ---- 📻 Neues entdecken (Build 99, der Besitzer): Radio-Mixe zu Titeln der gewählten
   Playlist, alles Bekannte gefiltert — nur NEUE Songs, mit Anhören + Laden.
   Fenster im Backkatalog-Stil, rechts unter der Download-Box angedockt. ---- */
async function entdeckerOeffnen(){
  // Build 106 (der Besitzer): ohne gewählte Playlist nimmt der Entdecker die GANZE
  // Bibliothek als Quelle (Seeds gewichtet nach dem, was du wirklich hörst).
  const sel=document.getElementById('plsel');
  const pid=sel&&sel.value; const pl=plState.find(p=>p.id===pid);
  entdeckerZu();
  const fly=document.createElement('div');
  fly.className='abo-flyout'; fly.id='ent-flyout'; fly.tabIndex=-1;
  fly.innerHTML='<div class="abo-fly-titel">📻 Neues entdecken: '+esc(pl?(pl.name||''):'deine Bibliothek')+
    '<span class="spacer"></span><button class="ib" title="Neu würfeln (andere Zufalls-Titel als Radio-Start)" onclick="entdeckerLaden()">🔄</button>'+
    '<button class="ib" title="Schließen (Esc)" onclick="entdeckerZu()">✕</button></div>'+
    '<div id="ent-inhalt" class="abo-folgen"><div class="leer">📡 Radios zu deinen Titeln werden aufgelöst…</div></div>';
  document.body.appendChild(fly); nachVorn(fly);
  aboFlyoutPositionieren(fly,null);
  fly.addEventListener('keydown',e=>{if(e.key==='Escape'){entdeckerZu(); e.stopPropagation();}});
  setTimeout(()=>document.addEventListener('pointerdown',entdeckerAussen,true),0);
  fly.focus(); fly.dataset.pl=pl?pid:'';
  entdeckerLaden();
}
function entdeckerZu(){
  const f=document.getElementById('ent-flyout'); if(f)f.remove();
  document.removeEventListener('pointerdown',entdeckerAussen,true);
}
function entdeckerAussen(e){
  const f=document.getElementById('ent-flyout'); if(!f)return;
  if(f.contains(e.target)||e.target.closest('.itemmenu'))return;
  entdeckerZu();
}
async function entdeckerLaden(){
  const fly=document.getElementById('ent-flyout'); if(!fly)return;
  const box=document.getElementById('ent-inhalt');
  box.innerHTML='<div class="leer">📡 Radios zu deinen Titeln werden aufgelöst… (ein paar Sekunden)</div>';
  let d=null;
  try{const r=await fetch('/api/entdecken?pl='+encodeURIComponent(fly.dataset.pl)+'&seeds=3&je=25'); d=await r.json();}catch(e){}
  if(!d||!d.ok){box.innerHTML='<div class="leer">'+esc((d&&d.fehler)||'Entdecken fehlgeschlagen — später erneut.')+'</div>'; return;}
  if(!d.funde.length){box.innerHTML='<div class="leer">Nichts Neues gefunden — 🔄 würfelt andere Radio-Startpunkte.</div>'; return;}
  const q=document.getElementById('cmd-qual').value;
  const quelleText=d.quelle==='bibliothek'?' (Radio-Start gemischt: Meistgehört + neu Hinzugefügt + Zufall, je Künstler einer)':'';
  const zeilen=d.funde.map(f=>
    '<div class="abo-f" data-vid="'+f.id+'">'+
    (f.score>1?'<span class="abo-nr" title="Kam in '+f.score+' der '+d.seeds+' Radios vor — starkes Signal">'+f.score+'×</span>':'<span class="abo-nr"></span>')+
    '<span class="abo-ft">'+esc(f.titel)+(f.kanal?' <span style="opacity:.55">· '+esc(f.kanal)+'</span>':'')+'</span>'+
    (f.dauer?'<span class="abo-fd">'+zeit(f.dauer)+'</span>':'')+
    '<button class="ib" title="Auf YouTube anhören" data-vid="'+esc(f.id)+'" onclick="window.open(\'https://www.youtube.com/watch?v=\'+this.dataset.vid,\'_blank\',\'noreferrer\')">▶</button>'+
    '<button class="ib" title="In die Warteschlange laden" data-vid="'+esc(f.id)+'" onclick="entdeckerHolen(this,this.dataset.vid)">⬇</button>'+
    '</div>').join('');
  box.innerHTML='<div class="abo-staffel" title="'+esc(quelleText.trim())+'">'+d.funde.length+' neue Titel aus '+d.seeds+' Radios — nichts davon ist in deiner Bibliothek.'+
    '<span class="spacer"></span>'+
    '<button class="btn mini" onclick="entdeckerDurchhoeren()" title="Alle Funde als temporäre YouTube-Playlist öffnen und am Stück durchhören (max. 50)">▶ Auf YouTube durchhören</button>'+
    '<button class="btn mini" onclick="entdeckerAlle()" title="Alle Funde laden — sie sammeln sich in der Playlist „✨ Entdeckt (Datum)"">⬇ Alle ('+d.funde.length+')</button></div>'+
    '<div class="abo-fliste">'+zeilen+'</div>';
  fly.dataset.qual=q;
}
function entdeckerPlName(){
  const d=new Date();
  return '✨ Entdeckt '+String(d.getDate()).padStart(2,'0')+'.'+String(d.getMonth()+1).padStart(2,'0')+'.';
}
function entdeckerDurchhoeren(){
  // Build 100 (der Besitzer): alle Funde als TEMPORAERE YouTube-Playlist am Stück hören —
  // der watch_videos-Trick baut daraus eine echte list=TL…-Playlist (max 50).
  const fly=document.getElementById('ent-flyout'); if(!fly)return;
  const vids=[...fly.querySelectorAll('.abo-f')].map(z=>z.dataset.vid).slice(0,50);
  if(!vids.length)return;
  window.open('https://www.youtube.com/watch_videos?video_ids='+vids.join(','),'_blank','noreferrer');
}
async function entdeckerHolen(btn,vid){
  const q=(document.getElementById('cmd-qual')||{}).value||'beste';
  await api('/api/add',{urls:'https://www.youtube.com/watch?v='+vid,qualitaet:q,ziel_playlist:entdeckerPlName()});
  if(btn){btn.textContent='✓'; btn.disabled=true;}
  const z=btn&&btn.closest('.abo-f'); if(z)z.style.opacity=.45;
  laden();
}
async function entdeckerAlle(){
  const fly=document.getElementById('ent-flyout'); if(!fly)return;
  const zeilen=[...fly.querySelectorAll('.abo-f')];
  const vids=zeilen.map(z=>z.dataset.vid);
  if(!vids.length)return;
  const dsum=zeilen.reduce((s,z)=>{const t=z.querySelector('.abo-fd'); if(!t)return s;
    const teile=t.textContent.split(':').map(Number); return s+teile.reduce((a,b)=>a*60+b,0);},0);
  const gr=groesseSchaetzen(dsum,(document.getElementById('cmd-qual')||{}).value||'beste');
  if(!confirm(vids.length+' neue Titel laden? Sie sammeln sich in der Playlist „'+entdeckerPlName()+'".'+gr))return;
  const q=(document.getElementById('cmd-qual')||{}).value||'beste';
  await api('/api/add',{urls:vids.map(v=>'https://www.youtube.com/watch?v='+v).join('\n'),qualitaet:q,ziel_playlist:entdeckerPlName()});
  toast('📻 '+vids.length+' Titel eingereiht → „'+entdeckerPlName()+'"'); entdeckerZu(); laden();
  try{dlboxTab('queue');}catch(e){}
}
function mixeMenu(ev){
  const r=ev.currentTarget.getBoundingClientRect();    // Rect merken, der Knopf-Kontext geht im Menü verloren
  // Build 117 (der Besitzer): Radio lag doppelt (Kopfleiste UND Bibliotheks-Leiste).
  // Es ist eine Mix-Art wie die anderen ⇒ es gehört hierher; oben bleibt der
  // 📻-Knopf am Transport, hier ist der Weg über den Mixer.
  aktionsMenu(ev,[
    ['📻 Endlos-Radio', radioStart],
    ['★ Meistgespielt', playMostPlayed],
    ['🕘 Zuletzt gespielt', playLetzte],
    ['▶ Gefilterte abspielen', playGefilterte],
    ['✨ Smart-Playlists…', ()=>smartPopover({currentTarget:{getBoundingClientRect:()=>r}})]]);
}

/* „Zu Playlist" — Auswahl-Liste direkt am Titel (kein Dropdown-Vorwählen nötig) */
function plAddListe(m,key,fertig){
  fertig=fertig||(()=>m.remove());                   // im Flyout: schließt Flyout und Menü
  // Der Besitzer 07.08.: „Bei mehreren markierten dateien wird nur die erste zur
  // Playlist hinzugefügt" — ist der geklickte Titel Teil der Auswahl,
  // wandert die GANZE Auswahl mit; die Zahl steht in der Überschrift.
  const inAuswahl=typeof libAuswahl!=='undefined'&&libAuswahl&&libAuswahl.has&&libAuswahl.has(key);
  const keys=inAuswahl?[...libAuswahl]:[key];
  const wieViele=keys.length>1?` (${keys.length})`:'';
  // Ab 9 Playlists erscheint ein Suchfeld (tippen filtert die Liste live).
  const suche=plState.length>8
    ?'<input class="km-such" placeholder="Playlist suchen…" onclick="event.stopPropagation()" '+
     'oninput="const q=this.value.toLowerCase();this.parentNode.querySelectorAll(\'button[data-pl]\').forEach(b=>{if(b.dataset.pl!==\'__neu\')b.style.display=b.textContent.toLowerCase().includes(q)?\'\':\'none\'})">'
    :'';
  m.innerHTML=`<div class="sm-titel">＋ Zu Playlist hinzufügen${wieViele}</div>`+suche+'<div class="km-sub">'+
    plState.map(p=>`<button data-pl="${p.id}">${esc(p.name)} <span style="color:var(--gedaempft)">(${p.items.length})</span></button>`).join('')+
    '<button data-pl="__neu">＋ Neue Playlist…</button></div>';
  m.querySelectorAll('button').forEach(b=>b.onclick=async(e2)=>{
    e2.stopPropagation();
    let id=b.dataset.pl;
    if(id==='__neu'){
      const n=prompt('Name der neuen Playlist:'); if(!n||!n.trim()){fertig();return;}
      id=await plAnlegen(n.trim());
    }
    if(id){
      for(const k of keys)await plApi({art:'add',id,key:k});
      const p=plState.find(x=>x.id===id), t=libFind(keys[0]);
      if(p)plInfo(keys.length>1
        ? keys.length+' Titel → '+p.name+' ✓'
        : '„'+((t&&t.titel)||'').slice(0,22)+'" → '+p.name+' ✓'); }
    fertig();
  });
}
function plAddMenu(ev,key){
  ev.stopPropagation();
  if(menuGeradeZu(ev.currentTarget))return;            // 2. Klick = zu (05.08.)
  document.querySelectorAll('.itemmenu').forEach(x=>x.remove());
  const m=document.createElement('div'); m.className='itemmenu'; document.body.appendChild(m);
  plAddListe(m,key);
  popoverBei(m,(ev.currentTarget||ev.target).getBoundingClientRect());
  menuSchliesser(m);
}

// Kontext-/⋯-Menü am Titel (Explorer-Stil; Untermenüs klappen wie überall rechts aus).
function libItemMenu(ev,id){
  ev.stopPropagation();
  if(ev.currentTarget&&menuGeradeZu(ev.currentTarget))return;   // 2. Klick = zu
  document.querySelectorAll('.itemmenu').forEach(m=>m.remove());
  const x=libFind(id); if(!x)return;
  const eintraege=[];
  if(!x.vorhanden)eintraege.push(['⬇ Erneut herunterladen', ()=>biblioNeuladen(id)]);
  if(x.vorhanden)eintraege.push(['▶ Abspielen', ()=>playerPlay([id])]);
  if(x.vorhanden)eintraege.push(['⏭ Als Nächstes abspielen', ()=>queueAlsNaechstes(id)]);
  if(x.vorhanden)eintraege.push(['➕ Ans Ende der Warteschlange', ()=>queueAnsEnde(id)]);
  const nAus=(libAuswahl&&libAuswahl.has&&libAuswahl.has(id))?libAuswahl.size:0;
  eintraege.push(nurPc([`＋ Zu Playlist${nAus>1?' ('+nAus+')':''}`, (f,fertig)=>plAddListe(f,id,fertig), 'sub']));
  // Der Besitzer 07.08.: „Eventuell auch einen knopf im rechtsklick menü für alles
  // anwählen?" — wählt die GEFILTERTE Sicht (wie Strg+A).
  eintraege.push(['☑ Alles auswählen (Strg+A)', ()=>libAllesWaehlen()]);
  if(x.vorhanden)eintraege.push(nurPc(['📁 Im Ordner zeigen', ()=>biblio(id,'ordner')]));
  if(x.url)eintraege.push(['↗ Auf YouTube öffnen', ()=>window.open(x.url,'_blank','noreferrer')]);
  if(x.vorhanden)eintraege.push(nurPc(['✂ Ausschnitt schneiden…', ()=>clipDialog(id)]));
  // Build 144k („Rechtsklick auf den song = welcher der ausschnitte ist
  // der favorit?"): Die Ausschnitte dieses Songs wohnen HIER, nicht als
  // eigene Kacheln. ⭐ markiert den Favoriten; der zählt allein im Zufall.
  // Build 144o: hat die Gruppe Alternativen (Hauptsong + Clips)? Dann hier
  // wählen, welcher der Favorit ist — Hauptsong oder Ausschnitt.
  if(x.hat_geschwister){
    const clips=gruppeVon(id).filter(c=>c.clip).length;
    eintraege.push(nurPc(['✂ Ausschnitte ('+clips+')', (f,fertig)=>gruppeListe(f,id,fertig), 'sub']));
  }
  eintraege.push(nurPc([x.archiviert?'↩ Aus dem Archiv holen':'🗄 Ins Archiv legen', ()=>biblio(id, x.archiviert?'entarchiv':'archiv')]));
  eintraege.push(nurPc([x.blacklist?'✓ Für Meistgespielt zulassen':'🚫 Von Meistgespielt ausschließen', ()=>biblio(id, x.blacklist?'unblacklist':'blacklist')]));
  if(libPlaylistView)eintraege.push(nurPc(['✖ Aus dieser Playlist entfernen', ()=>plRemove(id)]));
  // Etappe C (Spec Punkt 5): Wiedergabe-Regeln je Titel — ist der Titel Teil
  // einer Mehrfach-Auswahl, reist die GANZE Auswahl mit (Explorer-Muster,
  // dieselbe Regel wie beim Ziehen) = Besitzer-„Eigenschaften setzen" in Masse.
  const wgKeys=(libAuswahl.has(id)&&libAuswahl.size>1)?[...libAuswahl]:[id];
  eintraege.push(nurPc(['🎚 Wiedergabe…'+(wgKeys.length>1?' ('+wgKeys.length+' Titel)':''),
    ()=>wiedergabeDialog({keys:wgKeys}, wgKeys.length>1?wgKeys.length+' Titel':(x.titel||'Titel'))]));
  eintraege.push(['ℹ Eigenschaften…', ()=>eigenschaften(id)]);
  // Löschen nimmt dieselbe Regel: Teil der Auswahl = die ganze Auswahl.
  eintraege.push(nurPc(['🗑 In den Papierkorb'+(wgKeys.length>1?' ('+wgKeys.length+')':''), ()=>libLoeschen(wgKeys)]));
  // Derselbe Motor wie jeder Rechtsklick (Entscheid 7a Punkt 8): am Knopf
  // bzw. an der Mausposition, die kachelKontext als currentTarget mitgibt.
  kontextMenuBauen({currentTarget:ev.currentTarget}, eintraege);
}
/* Build 144n (25.07.): app-eigener Ja/Nein-Dialog. Das native confirm()
   lässt sich im Browser abschalten („diese Handlung unterbinden") — dann kam
   keine Rückfrage mehr und das Löschen ging ins Leere. Ein Modal auf dem
   `<body>` unterliegt dieser Sperre NICHT. */
function frageModal(text, jaLabel, onJa){
  const ov=document.createElement('div'); ov.className='modal';
  ov.innerHTML='<div class="modal-box" style="max-width:430px"><div class="modal-head"><b>Bitte bestätigen</b>'
    +'<button class="ib" title="Abbrechen" onclick="this.closest(\'.modal\').remove()">✕</button></div>'
    +'<div style="padding:16px;line-height:1.5">'+esc(text).replace(/\n/g,'<br>')+'</div>'
    +'<div style="padding:0 16px 16px;display:flex;gap:8px;justify-content:flex-end">'
    +'<button class="btn mini" data-nein>Abbrechen</button>'
    +'<button class="btn mini" data-ja style="background:var(--akz);border-color:var(--akz);color:#1b1512">'+esc(jaLabel||'OK')+'</button>'
    +'</div></div></div>';
  ov.onclick=e=>{if(e.target===ov)ov.remove();};
  ov.querySelector('[data-nein]').onclick=()=>ov.remove();
  ov.querySelector('[data-ja]').onclick=()=>{ov.remove(); onJa&&onJa();};
  // Esc bricht ab (Enter bestätigt über den fokussierten Ja-Knopf) — wer per
  // Entf löscht, hat die Hände an der Tastatur.
  ov.addEventListener('keydown',e=>{if(e.key==='Escape'){ov.remove(); e.stopPropagation();}});
  document.body.appendChild(ov);
  try{ov.querySelector('[data-ja]').focus();}catch(e){}
}
/* Build 144k (der Besitzer): die Ausschnitte eines Songs — sie teilen seine Video-Id.
   Der Favorit (⭐) zählt allein im Zufall; hier wählt man ihn, spielt einen
   Ausschnitt oder wirft ihn in den Papierkorb. */
function gruppeVon(id){                                 // alle Eintraege der Gruppe (Hauptsong + Clips)
  const x=libFind(id); const g=(x&&x.gruppe)||(id||'').split('|')[0];
  return libdaten.filter(c=>((c.gruppe)||(c.id||'').split('|')[0])===g);
}
function gruppeListe(m,id,fertig){
  fertig=fertig||(()=>m.remove());                   // im Flyout: schließt Flyout und Menü
  // Hauptsong zuerst, dann Clips (neuste oben). Der ⭐ markiert den Favoriten —
  // die sichtbare, abgespielte Kachel. Der Hauptsong ist NICHT löschbar
  // („das hauptvideo bleibt jedoch immer erhalten").
  const alle=gruppeVon(id).slice().sort((a,b)=>{
    if(!a.clip&&b.clip)return -1; if(a.clip&&!b.clip)return 1; return (b.ts||0)-(a.ts||0);});
  const rows=alle.map(c=>{
    const fav=c.ist_favorit;
    const label=c.clip?esc(c.titel||'Ausschnitt'):('🎵 '+esc(c.titel||'Hauptsong'));
    return '<div class="clip-row" data-k="'+c.id+'">'
      +'<button class="clip-fav'+(fav?' an':'')+'" data-act="fav" title="'+(fav?'Ist der Favorit — wird angezeigt & abgespielt':'Als Favorit setzen (wird angezeigt & abgespielt)')+'">'+(fav?'⭐':'☆')+'</button>'
      +'<button class="clip-play" data-act="play" title="Abspielen">▶ '+label+(c.dauer?' <span class="clip-meta">'+zeit(c.dauer)+'</span>':'')+'</button>'
      +(c.clip?'<button class="clip-del" data-act="del" title="Ausschnitt in den Papierkorb">🗑</button>'
              :'<span class="clip-del clip-schutz" title="Der Hauptsong bleibt immer erhalten">🔒</span>')
      +'</div>';
  }).join('')||'<div class="km-leer">nichts</div>';
  m.innerHTML='<div class="sm-titel">⭐ Favorit — wird angezeigt & abgespielt</div><div class="km-sub clip-sub">'+rows+'</div>';
  m.querySelectorAll('.clip-row button[data-act]').forEach(b=>b.onclick=async(e2)=>{
    e2.stopPropagation();
    const row=b.closest('.clip-row'), k=row.dataset.k, act=b.dataset.act;
    if(act==='play'){playerPlay([k]); fertig(); return;}
    if(act==='fav'){
      await api('/api/clip_favorit',{id:k});
      await libLaden(); if(document.body.contains(m))gruppeListe(m,id,fertig); return;   // frisch neu malen
    }
    if(act==='del'){
      frageModal('Diesen Ausschnitt in den Papierkorb verschieben?\n'+korbRueckweg(), '🗑 In den Papierkorb', async()=>{
        await api('/api/biblio',{id:k,art:'loeschen'});
        await libLaden();
        if(document.body.contains(m)&&gruppeVon(id).length>1)gruppeListe(m,id,fertig); else fertig();
        toast('🗑 Ausschnitt in den Papierkorb.');
      });
      return;
    }
  });
}
/* Playlist-Ansicht: Titel mit der Maus umsortieren (speichert die neue Reihenfolge) */
let plvVon=null;
function plvDragStart(e,key){plvVon=key; e.dataTransfer.effectAllowed='move';}
function plvDragOver(e){if(libPlaylistView){e.preventDefault(); e.dataTransfer.dropEffect='move';}}
async function plvDrop(e,key){
  e.preventDefault();
  if(!libPlaylistView||!plvVon||plvVon===key){plvVon=null;return;}
  const p=plState.find(x=>x.id===libPlaylistView); if(!p){plvVon=null;return;}
  const items=p.items.slice(), von=items.indexOf(plvVon), zu=items.indexOf(key);
  if(von<0||zu<0){plvVon=null;return;}
  items.splice(von,1); items.splice(zu,0,plvVon);
  plvVon=null;
  await plApi({art:'reorder',id:libPlaylistView,items});   // Backend speichert die Reihenfolge
  libMalen();
}
function dragAttrs(){
  // Titel sind IMMER ziehbar (in die Player-Playlist, der Besitzer 13.07.); in der
  // Playlist-Ansicht zusätzlich als Umsortier-Ziel. Den Schlüssel liest der
  // Handler aus data-key DESSELBEN Elements (Kachel und Zeile setzen es) —
  // nie roh im Handler (Gesamtprüfung S3: er ist nicht garantiert harmlos).
  const basis=` draggable="true" ondragstart="libDragStart(event,this.dataset.key)"`;
  return basis+(libPlaylistView?` ondragover="plvDragOver(event)" ondrop="plvDrop(event,this.dataset.key)"`:'');
}
function libDragStart(ev,id){
  try{ev.dataTransfer.setData('ytdl/key',id);}catch(e){}   // fürs Fallenlassen in der Player-Playlist
  ev.dataTransfer.effectAllowed='copyMove';
  ziehTooltip(ev,id);                                      // kleiner Text-Anfasser statt großem Bild (21.07.)
  if(libPlaylistView)plvDragStart(ev,id);                  // Reihenfolge ziehen wie bisher
}
/* Drag-Ghost: nur der Titel als kleiner Tooltip mitgezogen — nicht das ganze
   Kachelbild (21.07.: „nur der Text, nicht das Bild bewegt sich"). */
function ziehTooltip(ev,id){
  // Build 142 (der Besitzer): Bei mehreren Markierten zeigte der Anfasser nur den
  // Titel, den man zufällig gegriffen hatte — man sah nicht, dass acht
  // Stück mitreisen. Windows stapelt dafür die Symbole mit einem
  // Zähler-Abzeichen, macOS macht es genauso mit rotem Abzeichen;
  // gemeinsam ist beiden: die ANZAHL steht dran. Genau das hier auch.
  const mehrere=libAuswahl.has(id)&&libAuswahl.size>1;
  const x=libFind(id);
  const t=mehrere ? (libAuswahl.size+' ausgewählte Titel')
                  : (x?(x.titel||id):id);
  const g=document.createElement('div'); g.className='ziehghost'+(mehrere?' stapel':'');
  g.textContent=(mehrere?'🎵🎵 ':'🎵 ')+t;
  document.body.appendChild(g);
  try{ev.dataTransfer.setDragImage(g,12,12);}catch(e){}
  setTimeout(()=>g.remove(),0);                            // Browser hat das Bild bereits kopiert
}

/* Generischer Menü-Bauer: an Mausposition (clientX) oder an einem Knopf (currentTarget).
   Kontextmenü mit Windows-Ausklapp-Untermenüs (13.07.): Einträge der Form
   [Label, fn] klicken normal; [Label, optionenOderFunktion, 'sub'] zeigen ▸
   und klappen bei Hover/Klick RECHTS DANEBEN ein Flyout aus (Haken = aktiv).
   Die Funktion bekommt das Flyout und `fertig` (schließt alles): liefert sie
   Optionen [Label, aktiv?, fn], baut kmFuellen die Liste; sonst füllt sie das
   Flyout selbst (Playlists mit „Neue Playlist“, Ausschnitte mit ⭐/▶/🗑).
   Seit Entscheid 7a Punkt 8 das EINE Untermenü-Verhalten: das frühere
   'bleib' (Inhalt des Menüs tauschen) im Bibliotheks-Menü ist entfallen. */
function kontextMenuBauen(pos, eintraege){
  // ⋯-Knöpfe (kein Rechtsklick): 2. Klick schließt statt neu zu öffnen.
  if(pos.clientX===undefined&&pos.currentTarget&&menuGeradeZu(pos.currentTarget))return;
  eintraege=menuFuerGeraet(eintraege);                 // Gerät im WLAN: ohne nur-PC-Einträge
  document.querySelectorAll('.itemmenu').forEach(m=>m.remove());
  const m=document.createElement('div'); m.className='itemmenu';
  m.innerHTML=eintraege.map((e,i)=>e[2]==='sub'
    ?`<button data-i="${i}" class="km-hatsub">${e[0]}<span class="km-pfeil">▸</span></button>`
    :`<button data-i="${i}">${e[0]}</button>`).join('');
  document.body.appendChild(m);
  const r=(pos.clientX!==undefined)
    ?{left:pos.clientX,right:pos.clientX,top:pos.clientY,bottom:pos.clientY}
    :pos.currentTarget.getBoundingClientRect();
  popoverBei(m,r);
  let flyTimer=null;
  const flyZu=()=>document.querySelectorAll('.km-flyout').forEach(f=>f.remove());
  const flyAuf=(b,ent)=>{
    flyZu();
    const f=document.createElement('div'); f.className='itemmenu km-flyout';
    const fertig=()=>{flyZu(); m.remove();};
    const opt=(typeof ent[1]==='function')?ent[1](f,fertig):ent[1];   // erst beim Öffnen (frischer Zustand)
    if(Array.isArray(opt))kmFuellen(f, ent[0].replace(' ▸',''), opt, fertig);
    document.body.appendChild(f);
    const br=b.getBoundingClientRect(), mr=m.getBoundingClientRect();
    let left=mr.right+2;                                      // rechts daneben; kein Platz -> links
    if(left+f.offsetWidth>window.innerWidth-8)left=Math.max(8, mr.left-f.offsetWidth-2);
    const top=Math.max(8, Math.min(br.top-4, window.innerHeight-f.offsetHeight-8));
    f.style.left=left+'px'; f.style.top=top+'px';
  };
  m.querySelectorAll('button').forEach(b=>{
    const ent=eintraege[+b.dataset.i];
    if(ent[2]==='sub'){
      b.onmouseenter=()=>{clearTimeout(flyTimer); flyTimer=setTimeout(()=>flyAuf(b,ent),150);};
      b.onmouseleave=()=>clearTimeout(flyTimer);
      b.onclick=(e2)=>{e2.stopPropagation(); flyAuf(b,ent);};
    }else{
      b.onmouseenter=()=>{clearTimeout(flyTimer); flyTimer=setTimeout(flyZu,300);};
      b.onmouseleave=()=>clearTimeout(flyTimer);
      b.onclick=(e2)=>{
        e2.stopPropagation();
        ent[1](); flyZu(); m.remove();
      };
    }
  });
  menuSchliesser(m);
  return m;
}

/* Füllt ein Menü-Element mit einer Auswahl-Liste: Haken = aktiv, ab 9 Einträgen
   erscheint ein Suchfeld (Frage Playlists: kostet nichts, kommt nur bei Bedarf). */
function kmFuellen(f,titel,optionen,fertig){           // optionen: [Label, aktiv?, fn]
  optionen=menuFuerGeraet(optionen);
  const suche=optionen.length>8?'<input class="km-such" placeholder="Suchen…">':'';
  f.innerHTML='<div class="sm-titel">'+titel+'</div>'+suche+'<div class="km-sub">'+
    optionen.map((o,i)=>`<button data-i="${i}"><span class="km-check"${o[1]?'':' style="visibility:hidden"'}>✓</span>${esc(o[0])}</button>`).join('')+'</div>';
  const inp=f.querySelector('.km-such');
  if(inp){inp.onclick=(e)=>e.stopPropagation();
    inp.oninput=()=>{const q=inp.value.toLowerCase();
      f.querySelectorAll('.km-sub button').forEach(b=>{b.style.display=b.textContent.toLowerCase().includes(q)?'':'none';});};}
  f.querySelectorAll('.km-sub button').forEach(b=>b.onclick=(e2)=>{
    e2.stopPropagation(); optionen[+b.dataset.i][2](); fertig();});
}
function kmListe(m,titel,optionen){if(!m)return; kmFuellen(m,titel,optionen,()=>m.remove());}   // m fehlt = Toggle hat geschlossen

/* Rechtsklick im PLAYER: Menü für den laufenden Titel (pausiert nichts, startet nichts neu) */
function playerKontext(ev){
  ev.preventDefault(); ev.stopPropagation();
  const k=aktKey(); if(!k)return false;
  const x=libFind(k)||{};
  const el=document.getElementById('pl-el');
  const pos={clientX:ev.clientX, clientY:ev.clientY};   // fürs EQ-Popover an der Mausposition
  const eintraege=[];
  eintraege.push([(el&&!el.paused)?'⏸ Pause':'▶ Weiter / Pause', plTogglePlay]);
  eintraege.push(['⏮ Vorheriger Titel', playerPrev]);
  eintraege.push(['⏭ Nächster Titel', playerNext]);
  if(plGeraet==='vlc')eintraege.push(['↻ VLC neu verbinden', vlcNeustart]);
  // Untermenüs klappen wie in Windows RECHTS aus (Hover oder Klick), Haken = aktiv
  eintraege.push(nurPc(['＋ Zu Playlist', ()=>plOptionen(k), 'sub']));
  eintraege.push(['🎶 Warteschlange', queueWerkzeugListe, 'sub']);
  eintraege.push(['📊 Visualizer', ()=>VIZMODES.map(v=>[v[2], v[0]===vizMode, ()=>{vizMode=v[0];
      lsSchreiben('ytdl_viz',vizMode); vizModeRender();}]), 'sub']);
  eintraege.push(['⚡ Geschwindigkeit ('+playSpeed+'×)', ()=>
    [0.5,0.75,1,1.25,1.5,2].map(s=>[s+'×', s===playSpeed, ()=>speedWaehlen(s)]), 'sub']);
  eintraege.push(['💬 Untertitel', ()=>{
    const opt=SUBMODES.map(sm=>[sm[2], sm[0]===subMode, ()=>subModusSetzen(sm[0])]);
    if(subSprachen.length>1)opt.push(['🌐 Sprache: '+(subLang||'?')+' → nächste', false, subSpracheWechsel]);
    if(subCues)opt.push(['あ→a Romaji: '+(subRomaji?'AN':'aus'), subRomaji, subRomajiToggle]);
    return opt;}, 'sub']);
  eintraege.push(['🎚 Equalizer…', ()=>eqPopover({currentTarget:{getBoundingClientRect:
    ()=>({left:pos.clientX,right:pos.clientX,top:pos.clientY,bottom:pos.clientY})}})]);
  if(x.vorhanden)eintraege.push(nurPc(['✂ Ausschnitt schneiden…', ()=>clipDialog(k)]));
  if(x.vorhanden)eintraege.push(nurPc(['📁 Im Ordner zeigen', ()=>biblio(k,'ordner')]));
  // Build 144i (25.07.: „auf youtube öffnen mit rechtsklick geht nicht zum
  // moment wo man gerade ist"): playerYoutube() hängt &t=<Position>s an — genau
  // wie der Werkzeug-Knopf. Nur HIER, im Player-Rechtsklick, wo es eine
  // laufende Stelle gibt (in der Bibliothek gibt es keine).
  if(x.url)eintraege.push(['↗ Auf YouTube öffnen (an dieser Stelle)', playerYoutube]);
  eintraege.push(nurPc(['⧉ In VLC / extern öffnen', playerExtern]));
  eintraege.push(['ℹ Eigenschaften…', ()=>eigenschaften(k)]);
  kontextMenuBauen(ev, eintraege);
  return false;
}

// Rechtsklick auf einen Titel = dasselbe Menü an der Mausposition (wie im Explorer)
function kachelKontext(ev,id){
  ev.preventDefault();
  libItemMenu({stopPropagation(){}, currentTarget:{getBoundingClientRect:
    ()=>({left:ev.clientX, right:ev.clientX, top:ev.clientY, bottom:ev.clientY})}}, id);
  return false;
}
function kachel(x){
  const dauer=x.dauer?`<span class="kdauer">${zeit(x.dauer)}</span>`:'';
  const weg=x.vorhanden?'':'<span class="wegbadge">verschoben</span>';
  // Der Besitzer 05.08.: „die ganzen Lieder haben in der Bibliothek immer noch das
  // thumbnail von youtube als Bild. Warum nicht das Albumcover?" — Kacheln
  // zeigen das ECHTE Album-Cover (/api/cover), sobald eins getaggt ist;
  // scheitert der Abruf, fällt das Bild aufs Thumbnail zurück (Player-Muster).
  // Rückfall aufs Thumbnail über data-fb (S3): der Handler bleibt fester Code.
  const quelle=x.cover_album?`/api/cover?id=${encodeURIComponent(x.id)}`:(x.thumb?esc(x.thumb):'');
  const thumb=!quelle?'':(x.cover_album&&x.thumb)
    ?`<img class="thumb" src="${quelle}" loading="lazy" draggable="false" data-fb="${esc(x.thumb)}" onerror="this.onerror=function(){this.style.display='none';this.parentNode.classList.add('platzhalter')};this.src=this.dataset.fb">`
    :`<img class="thumb" src="${quelle}" loading="lazy" draggable="false" onerror="this.style.display='none';this.parentNode.classList.add('platzhalter')">`;
  // Build 144o (der Besitzer): kleine ✂ oben rechts, wenn diese Kachel ein Ausschnitt ist
  // (der Hauptsong liegt dann im Rechtsklick) — damit man es auf einen Blick sieht.
  const schere=x.clip?'<span class="clip-schere" title="Ausschnitt — der Hauptsong liegt im Rechtsklick">✂</span>':'';
  const herz=x.herz?'<span class="herzbadge" title="❤ Lieblingssong">♥</span>':'';
  const sel=libAuswahl.has(x.id)?' sel':'';
  // Ausführliche Details nur noch als Tooltip auf der Info-Zeile (Kachel bleibt ruhig).
  const det=[COLDEF.kategorie.t(x),COLDEF.qualitaet.t(x),technikText(x),mb(x.groesse),
             x.dauer?zeit(x.dauer):'',x.uploader||'',ytdatum(x.upload_date)].filter(Boolean).join('  ·  ');
  return `<div class="kachel ${x.vorhanden?'':'weg'}${sel}" data-id="${esc(x.id)}" data-key="${esc(x.id)}" onclick="kachelClick(event,this.dataset.key)" ondblclick="kachelDblClick(event,this.dataset.key)" oncontextmenu="return kachelKontext(event,this.dataset.key)"${dragAttrs()}>
    <div class="thumbwrap ${quelle?'':'platzhalter'}" data-key="${esc(x.id)}" onclick="thumbClick(event,this.dataset.key)" title="Abspielen">${thumb}${dauer}${weg}${schere}${herz}</div>
    <div class="kbody">
      <div class="ktitel" title="${esc(x.titel)}">${esc(x.titel)}</div>
      <div class="kinfo" title="${esc(det)}">${kachelInfo(x)}</div>
      <div class="kakt">${aktBtnsKachel(x)}</div>
    </div>
  </div>`;
}
let libKompakt=false;
function libKompaktToggle(){libKompakt=!libKompakt;
  document.getElementById('vb-kompakt').classList.toggle('an',libKompakt); libMalen();}
function kacheln(arr){return '<div class="kacheln'+(libKompakt?' kompakt':'')+'">'+arr.map(kachel).join('')+'</div>';}
function aktBtnsListe(x){
  let b='<div class="lakt">';
  if(x.vorhanden){
    b+=`<button class="ib play" data-key="${esc(x.id)}" onclick="event.stopPropagation();playerPlay([this.dataset.key])" title="Abspielen">▶</button>`;
    b+=herzKnopf(x);
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="plAddMenu(event,this.dataset.key)" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="event.stopPropagation();biblio(this.dataset.key,'ordner')" title="Im Ordner zeigen">📁</button>`;
  }else{
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="event.stopPropagation();biblioNeuladen(this.dataset.key)" title="Erneut laden">⬇</button>`;
    b+=`<button class="ib" data-key="${esc(x.id)}" onclick="plAddMenu(event,this.dataset.key)" title="Zu Playlist hinzufügen — Liste wählen">＋</button>`;
  }
  b+=`<button class="ib" data-key="${esc(x.id)}" onclick="libItemMenu(event,this.dataset.key)" title="Mehr…">⋯</button>`;
  return b+'</div>';
}
function listeTab(arr){
  const cols=sichtbareCols();
  const heads=`<th class="th-sort ${libsort.key==='titel'?'akt':''}" onclick="setSort('titel')">Titel${pfeil('titel')}</th>`+
    cols.map(k=>`<th class="th-sort ${libsort.key===k?'akt':''}" data-k="${esc(k)}" onclick="setSort(this.dataset.k)">${COLDEF[k].l}${pfeil(k)}</th>`).join('')+'<th></th>';
  const rows=arr.map(x=>{
    const th=x.thumb?`<img class="lthumb" src="${esc(x.thumb)}" loading="lazy" draggable="false" style="cursor:pointer" data-key="${esc(x.id)}" onclick="event.stopPropagation();thumbClick(event,this.dataset.key)" onerror="this.style.visibility='hidden'">`:'<span class="lthumb"></span>';
    const tds=cols.map(k=>{
      if(k==='status')return `<td class="lstatus ${x.vorhanden?'ok':'weg2'}">${x.vorhanden?'vorhanden':'verschoben'}</td>`;
      return `<td class="num">${esc(String(COLDEF[k].t(x)))}</td>`;
    }).join('');
    const sel=libAuswahl.has(x.id)?' sel':'';
    return `<tr class="${x.vorhanden?'':'weg'}${sel}" data-id="${esc(x.id)}" data-key="${esc(x.id)}" onclick="kachelClick(event,this.dataset.key)" ondblclick="kachelDblClick(event,this.dataset.key)" oncontextmenu="return kachelKontext(event,this.dataset.key)"${dragAttrs()}><td><div class="ltitel">${th}<span class="ltxt" title="${esc(x.titel)}">${esc(x.titel)}</span></div></td>${tds}<td class="num">${aktBtnsListe(x)}</td></tr>`;
  }).join('');
  return `<div class="libwrap"><table class="libtab${libKompakt?' kompakt':''}"><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

