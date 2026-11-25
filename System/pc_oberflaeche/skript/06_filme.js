/* ================= Filme ================= */
/* ---- Filme (Film-Fundament, Doku/SYNC_FILME_SPEC.md Etappe 7) --------------
   Anzeige-Minimum: die serverseitigen Reihen als Poster-Bänder, Klick spielt
   den Jellyfin-Strom im LOKALEN VLC. Das eigentliche TV-Design ist
   Teilprojekt 2 — hier geht es um den sichtbaren Beweis der Engine. */
/* Ein Ausfall muss man SEHEN. der Film-Server antwortete vom 06. bis 13.08.2026
   mit 403 — sieben Tage lang, und nichts hat davon erzählt: der Spiegel steht
   bei einem Ausfall bewusst weiter (Spec), die Poster kommen aus dem Cache,
   nur „Neu auf dem Server" wuchs still nicht mehr. Ein alter Spiegel sah exakt
   aus wie ein frischer. Calm-Design heißt „nur bei Handlungsbedarf anzeigen" —
   nicht „nie". Ein einzelner Fehlversuch (Server startet neu) bleibt still;
   gemeldet wird erst, wenn der 6-Stunden-Rhythmus nachweislich gerissen ist. */
function filmDauerGrob(s){
  const st=Math.round((s||0)/3600);
  if(st<1)return 'weniger als einer Stunde';
  if(st<48)return st+' Stunden';
  return Math.round(st/24)+' Tagen';
}
/* Je Fehlerart ehrlich (24.09.): der Ausfall ab dem 23.09. hieß hier „antwortet
   nicht" — der Film-Server antwortete aber, er lehnte nur unsere Anmeldeform ab
   (Jellyfin 12). Fremde Geräte bekommen fehler nur als Kurztext ohne Adresse;
   die Texte hier nutzen den Rohtext deshalb nur bei Netz- und Serverfehlern. */
function filmWarnung(z){
  if(!z)return '';
  /* Der Besitzer 25.11.2026: Filme nur mit eigenem Zugang. Ein Profil ohne eigenen Jellyfin-
     Zugang bekommt leere Reihen und diesen Hinweis statt fremder Filme. */
  if(z.profil_ohne_zugang)return '🔒 '+(z.fehler||'Dieses Profil hat keinen eigenen Film-Zugang.');
  if(!z.zugang)return '⚙ Kein Jellyfin-Zugang eingerichtet — der Filmteil ist aus.';
  if(z.fehler&&(z.still_seit_s||0)>8*3600){
    const seit=filmDauerGrob(z.still_seit_s);
    const rest=' Gezeigt wird der letzte Spiegel von '+(z.anzahl||0)+' Titeln.';
    const ver=(z.server_version&&z.server_version!=='?')?' (Jellyfin '+z.server_version+')':'';
    if(z.fehler_art==='merkmal_abgelehnt')
      return '⚠ Der Film-Server'+ver+' lehnt seit '+seit+' unsere Anmeldeform ab — die Anmeldung '
        +'selbst klappt. Entweder braucht es ein Programm-Update, oder ein zweites SyncYouTube '
        +'(exe und Quellstart zugleich) nutzt dieselbe Gerätekennung.'+rest;
    if(z.fehler_art==='anmeldung_abgelehnt')
      return '⚠ Der Film-Server lehnt seit '+seit+' Benutzer oder Passwort ab — das Konto '
        +'bitte trennen und neu verbinden.'+rest;
    if(z.fehler_art==='drossel')
      return '⏳ Der Film-Server bremst seit '+seit+' die Anmeldung (HTTP 403). Das heilt sich '
        +'sonst nach Minuten — hält es an, den Betreiber des Servers fragen.'+rest;
    if(z.fehler_art==='server')
      return '⚠ Der Film-Server liefert seit '+seit+' keine brauchbare Antwort ('+z.fehler+').'+rest;
    return '⚠ Der Film-Server antwortet seit '+seit+' nicht ('+z.fehler+').'+rest;
  }
  if((z.still_seit_s||0)>24*3600)
    return '⏳ Der letzte Abgleich mit dem Film-Server war vor '+filmDauerGrob(z.still_seit_s)
      +' — neue Filme fehlen hier noch.';
  return '';
}
async function filmeLaden(){
  const ziel=document.getElementById('filme-reihen'); if(!ziel)return;
  try{
    const r=await fetch('/api/filme/reihen'); const d=filmReihenAnwenden(await r.json());   // Merk-Tabelle (Runde 2)
    const stand=document.getElementById('filme-stand');
    /* Früher wurde hier der GANZE Katalog geholt (2,4 MB), nur um ein Datum
       anzuzeigen. Der Zustand ist ein paar hundert Byte und sagt mehr. */
    const z=await (await fetch('/api/filme/zustand')).json();
    const warn=filmWarnung(z);
    if(stand){
      stand.textContent=z.stand?('Stand '+new Date(z.stand*1000).toLocaleString('de-DE')
        +' · Server '+(z.server_version||'?')+' · '+(z.anzahl||0)+' Titel'):'';
      stand.style.color=warn?'#ffb020':'';
      if(warn)stand.textContent=warn+(stand.textContent?'  ('+stand.textContent+')':'');
      if(z.kann_verbinden)stand.insertAdjacentHTML('beforeend',
        ' <button class="mbtn" onclick="tvKontoOeffnen()">Eigenes Konto verbinden</button>');
    }
    const reihen=[['Weiterschauen',d.weiterschauen],['Top 10',d.top],['Neu auf dem Server',d.neu]]
      .concat(Object.entries(d.genres||{}));
    const html=reihen.filter(([,liste])=>liste&&liste.length).map(([name,liste])=>
      `<div class="f-reihe"><div class="f-rtitel">${esc(name)}</div><div class="f-band">`+
      liste.map(e=>`<div class="f-kachel" data-arg="${esc(e.id)}" onclick="tvInfo(this.dataset.arg)" title="${esc(e.titel)}${e.jahr?' ('+e.jahr+')':''}${e.rating?' · ★'+e.rating.toFixed(1):''}${e.fsk?' · '+esc(e.fsk):''}">`+
        `<img loading="lazy" src="/api/filme/bild?id=${encodeURIComponent(e.id)}" onerror="this.style.visibility='hidden'">`+
        `<div class="f-ktitel">${esc(e.titel)}</div></div>`).join('')+
      `</div></div>`).join('');
    ziel.innerHTML=html||'<div class="hinweis">Kein Film-Katalog. Jellyfin-Zugang im Windows-Keyring (Sync-Jellyfin) einrichten, dann ⟳ Abgleichen.</div>';
  }catch(e){ziel.innerHTML='<div class="hinweis">Filme-Reihen nicht erreichbar.</div>';}
}
/* Browser-Player-Weiche (06.08.: „kein externes fenster … wie bei
   netflix im Browser"): Codecs, die der Browser selbst dekodiert
   (h264/vp9/av1 + aac/mp3/opus …), laufen als <video> über den
   Server-Proxy /api/filme/direkt — ganz ohne VLC-Fenster. HEVC/AC3/DTS
   kann KEIN Browser ohne Transcoding: dort übernimmt weiter der VLC. */
function filmeBrowserKann(d){
  const v=((d&&d.video_codec)||'').toLowerCase(), a=((d&&d.audio_codec)||'').toLowerCase();
  const vOk=['h264','avc','vp8','vp9','av1'].some(x=>v.includes(x));
  const aOk=['aac','mp3','opus','vorbis','flac'].some(x=>a.includes(x));
  return vOk&&aOk;
}
async function filmePlay(id,pos,wechsel){
  let meta=(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.id===id)?tvInfoDaten.d
          :(typeof tvHeroDaten!=='undefined'&&tvHeroDaten&&tvHeroDaten.id===id)?tvHeroDaten:null;
  if(!meta){try{meta=await (await fetch('/api/filme/detail?id='+encodeURIComponent(id))).json();}catch(e){}}
  // Folgenwechsel per Taste (wechsel = Generation): inzwischen Esc gedrückt
  // oder ein neuerer Druck? Dann nichts öffnen (Prüf-Befund 24.09.: sonst
  // startete die Folge über der gerade geschlossenen Ansicht).
  if(wechsel&&wechsel!==tvpWechselGen)return;
  /* Ein Fehler-Objekt ist KEINE Meta. Die Route antwortet bei unbekannter Id mit
     {"fehler": …}; das ist in JS wahr, also lief der ganze Weiche-Code darauf
     weiter — mit leerem Titel, Dauer 0 (tote Zeitleiste) und der schwersten
     Transcode-Gangart. Traf bis 13.08.2026 JEDE Serien-Folge, weil Folgen nicht
     im Katalog-Spiegel stehen (Server-Seite jetzt: filme._folge_holen). */
  if(meta&&meta.fehler)meta=null;
  const inHuelle=!!window.pywebview;
  // Folgenwechsel per Taste aus einem VLC-Film in den Browser-Player: den VLC
  // anhalten, sonst liefe die alte Folge unsichtbar weiter.
  const warVlcFilm=tvpOffen&&tvpModus!=='browser';
  if(meta&&filmeBrowserKann(meta)){
    if(warVlcFilm)vlcBefehl('stop');
    tvpModus='browser'; tvpTc=false;                   // Direct Play im <video>
    tvFilmPlayer(id,(meta.titel||''),pos||0,meta);
    return;
  }
  if(meta&&!inHuelle){
    // Freigabe 06.08. („Geh das serverseitige Transcoding an"): im Browser
    // wandelt ffmpeg unterwegs — h264 bleibt Kopie (nur Ton→AAC), Rest
    // wird libx264. In der HÜLLE bleibt der eingebettete VLC der starke
    // Weg (spielt alles nativ, null Transcode-Last).
    if(warVlcFilm)vlcBefehl('stop');
    tvpModus='browser'; tvpTc=true;
    tvpTcVcopy=['h264','avc'].some(x=>((meta.video_codec||'').toLowerCase()).includes(x));
    tvFilmPlayer(id,(meta.titel||''),pos||0,meta);
    return;
  }
  filmePlayVlc(id,pos,meta,wechsel);
}
async function filmePlayVlc(id,pos,meta,wechsel){
  if(wechsel&&wechsel!==tvpWechselGen)return;
  // Ein Folgenwechsel, dessen Ziel nicht aufgeht, darf nicht „ausstehend"
  // hängen bleiben — sonst rechnete jeder weitere ⏭/⏮ von einer Folge aus,
  // die nie lief.
  const gescheitert=()=>{if(wechsel&&wechsel===tvpWechselGen){tvpWechsel=null; tvpModusNaechster=null;}};
  // Vollbild-Ordnung („nicht im Vordergrund"): erst das BROWSER-Vollbild
  // verlassen — sonst kämpfen zwei Fullscreens und das VLC-Bild liegt hinten.
  if(document.fullscreenElement){try{document.exitFullscreen();}catch(e){}}
  const gen=tvpWechselGen;                             // Esc und jeder neuere Folgenwechsel zählen hoch
  try{
    await huelleMelden();                              // Hülle: Film rendert ins Panel
    if(gen!==tvpWechselGen)return;                     // während der Anmeldung überholt: gar nicht erst starten
    const d=await api('/api/filme/play',{id, vol:plVol, pos:pos||0});
    if(d.fehler){toast('🎬 '+d.fehler); gescheitert(); return;}
    // Überholt, während VLC schon startete: spielt der VLC noch DIESE verworfene
    // Folge und ist das Ziel eine andere, anhalten — sonst lief sie unsichtbar
    // neben einer Browser-Folge weiter (Gegenprüfung 24.09.).
    if(wechsel&&wechsel!==tvpWechselGen){
      const ziel=tvpWechsel?tvpWechsel.id:(tvpOffen?tvpIdAkt:'');
      if(ziel!==id){const st=await vlcBefehl('status'); if(st&&st.key==='film:'+id)vlcBefehl('stop');}
      return;
    }
    // Erst JETZT auf VLC umschalten: scheiterte der Start bei einem Folgenwechsel
    // aus dem Browser-Player, liefe die alte Folge sonst mit falscher Fernbedienung.
    tvpModus='vlc';
    const titel=(meta&&meta.titel)||(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.titel)||'';
    tvFilmPlayer(id,titel,pos||0,meta);                // die Fernbedienung (Build 187)
  }catch(e){toast('🎬 Abspielen fehlgeschlagen.'); gescheitert();}
}
/* ---- Film-Player-Screen (Build 187) ---------------------------------------
   Vorgabe: „der Player hat keine controls, kein play, kein exit …" — das
   VLC-Vollbild ist ein NACKTES Renderfenster (libvlc hat keine UI). Dieses
   Overlay ist die Fernbedienung dazu: eigener 1-s-Status-Takt, Play/Pause,
   ±10 s, klickbarer Balken, Lautstärke, Beenden. Tasten: Leertaste/Enter =
   Pause · ←/→ = ±10 s · ↑/↓ = Lautstärke · Esc = Beenden. */
let tvpTimer=null, tvpPos=0, tvpDauer=0, tvpOffen=false, tvpLief=false, tvpTicks=0;
let tvpMeta=null, tvpAktiv=0;                          // Idle-Uhr (Netflix-Auto-Hide)
let tvpModus='vlc', tvpIdAkt='';                       // Browser-<video> oder VLC
let tvpTc=false, tvpTcOffset=0, tvpTcVcopy=false;      // Transcode-Strom (Freigabe)
function tvpDirektSrc(start){
  return '/api/filme/direkt?id='+encodeURIComponent(tvpIdAkt)+
    (tvpTc?('&tc=1'+(tvpTcVcopy?'&vcopy=1':'')+'&start='+Math.max(0,Math.round(start||0))):'');
}
/* Eine Fernbedienung, zwei Motoren: im Browser-Modus steuern die Befehle
   das <video>-Element direkt, sonst gehen sie an den VLC. Beim
   Transcode-Strom beginnt jedes <video> bei 0 — tvpTcOffset rechnet die
   echte Film-Position dazu, Seek startet den Strom an neuer Stelle. */
async function tvpBefehl(cmd,daten){
  if(tvpModus!=='browser')return vlcBefehl(cmd,daten);
  let v=document.getElementById('tvp-video');
  if(!v)return {zustand:'aus', key:'', verfuegbar:true};
  if(cmd==='toggle'){if(v.paused)v.play().catch(()=>{}); else v.pause();}
  else if(cmd==='seek'){
    const ziel=(daten&&daten.wert)||0;
    // Transcoder: neuer Strom ab ziel in einem NEUEN Element (tvpVideoTauschen);
    // die Antwort unten gehört dann schon zum neuen.
    if(tvpTc){tvpTcOffset=ziel; v=tvpVideoTauschen(tvpDirektSrc(ziel))||v;}
    else{try{v.currentTime=ziel;}catch(e){}}
  }
  else if(cmd==='vol')v.volume=Math.max(0,Math.min(1,((daten&&daten.wert)||0)/100));
  else if(cmd==='rate')v.playbackRate=(daten&&daten.wert)||1;
  else if(cmd==='stop'){v.pause(); v.removeAttribute('src'); try{v.load();}catch(e){}}
  else if(cmd==='spuren')return {ton:[],sub:[],rate:v.playbackRate||1};
  const aus=v.ended||!v.currentSrc;
  const metaDauer=(tvpMeta&&tvpMeta.laufzeit_min)?tvpMeta.laufzeit_min*60:0;
  return {zustand:aus?'aus':(v.paused?'pause':'spielt'),
          key:aus?'':'film:'+tvpIdAkt,
          pos:(tvpTc?tvpTcOffset:0)+(v.currentTime||0),
          dauer:tvpTc?metaDauer:(isFinite(v.duration)?v.duration:metaDauer),
          verfuegbar:true};
}
/* Folgenwechsel: das alte <video> wird erst geleert, wenn das neue SPIELT.
   Messung 24.09.2026 (Edge, Windows 11): Leerte man es vorher (Quelle weg +
   load()), spielte in der Seite kurz nichts — Windows gab dann bei der
   nächsten Pause die „aktuelle Sitzung" an eine andere pausierte App ab
   (Firefox, Spotify), und der nächste ⏯ startete DORT statt den Film.
   Geleert bei „playing" der neuen Folge blieb Edge in allen Läufen aktuell.
   Bis dahin schweigt das alte (pause); tvpZu räumt Liegengebliebenes.
   Transcoder-Sprung und Selbstheilung gehen denselben Weg (tvpVideoTauschen):
   eine neue Quelle im SELBEN Element verwürfe dessen Abspieler sofort. */
let tvpAbgeloest=[];
function tvpAbgeloestFreigeben(){
  const l=tvpAbgeloest; tvpAbgeloest=[];
  l.forEach(v=>medienS.freigeben(v));
}
/* Die Listener eines Film-<video> an EINER Stelle: Einstiegsstelle beim
   direkten Abspielen, Selbstheilungs-Kette, Klick = Pause, Windows-Overlay.
   pos = die Stelle, mit der dieses Video startet. */
function tvpVideoVerdrahten(v,id,pos){
  if(pos>0&&!tvpTc)v.addEventListener('loadedmetadata',()=>{try{v.currentTime=pos;}catch(e){}},{once:true});
  // Hat wirklich gespielt (erst dann meldet Chromium die Sitzung bei Windows an):
  // nur so ein Video muss tvpVideoTauschen bis zum Nachfolger halten.
  v.addEventListener('playing',()=>{v._tvpSpielte=true;});
  // Mindest-Sehzeit: das <video> misst selbst (timeupdate, Medienzeit). Nur das
  // AKTUELLE Film-Video: ein getauschtes feuert nach pause() noch ein timeupdate,
  // das mit dem Versatz des neuen gerechnet eine falsche Stelle ergäbe.
  v.addEventListener('timeupdate',()=>{
    if(v===document.getElementById('tvp-video'))tvpSehzeitZaehlen((tvpTc?tvpTcOffset:0)+(v.currentTime||0),!v.paused,v.playbackRate||1);
  });
  v.addEventListener('error',()=>{                     // Selbstheilungs-Kette:
    // direkt → Transcoder → VLC. Nicht für ein abgelöstes Video und nicht,
    // während ein Folgenwechsel lädt (die neue Folge kommt ja).
    if(!tvpOffen||tvpWechsel||tvpIdAkt!==id||!v.isConnected||v!==document.getElementById('tvp-video'))return;
    if(!tvpTc){
      toast('🎬 Format sperrt sich — der Transcoder übernimmt.');
      tvpTc=true; tvpTcVcopy=false; tvpTcOffset=tvpPos||pos||0;
      tvpVideoTauschen(tvpDirektSrc(tvpTcOffset));   // neues Element: ohne den loadedmetadata-Sprung oben
      return;
    }
    toast('🎬 Browser kann dieses Format nicht — VLC übernimmt.');
    // Die AKTUELLE Stelle, vor tvpZu gelesen: nach einem Sprung oder mitten im
    // Film nicht der Einstieg dieses Videos (ein getauschtes startet mit pos=0).
    const mm=tvpMeta, modus=tvpZurueckModus, posJetzt=tvpPos||pos||0;
    tvpZu();                                           // räumt den Modus …
    tvpModusNaechster={id, modus};                     // … darum danach: Besitzer-Zurück-Regel überlebt den Rückfall
    filmePlayVlc(id,posJetzt,mm);
  });
  v.addEventListener('click',ev=>{ev.stopPropagation(); tvpWach();
    tvpBefehl('toggle'); setTimeout(tvpTick,200);});   // Netflix: Klick = Pause
  // Windows-Overlay sofort nachziehen, nicht erst mit dem 1-s-Takt
  v.addEventListener('play',tvpMedienZustand); v.addEventListener('pause',tvpMedienZustand);
}
/* Neue Quelle = neues <video> an derselben Stelle im #tv-player (Ebenen und
   Vollbild bleiben). Lautstärke, Stumm und Tempo gehen mit — das Tempo auch als
   defaultPlaybackRate, weil das Laden der neuen Quelle playbackRate darauf
   zurücksetzt. Das alte verstummt; hat es gespielt, hält es Windows' Sitzung,
   bis das neue spielt. Hat es nie gespielt (schneller Doppelsprung, Fehler vor
   dem ersten Bild), hält es keine Sitzung und wird sofort geleert — das
   schließt auch seine Verbindung zum Server. */
function tvpVideoTauschen(src){
  const alt=document.getElementById('tvp-video'); if(!alt)return null;
  const neu=document.createElement('video');
  neu.id='tvp-video'; neu.className='tvp-video'; neu.autoplay=true; neu.setAttribute('playsinline','');
  neu.volume=alt.volume; neu.muted=alt.muted;
  neu.defaultPlaybackRate=neu.playbackRate=alt.playbackRate||1;
  try{alt.pause();}catch(e){}
  alt.replaceWith(neu);
  if(alt._tvpSpielte)tvpAbgeloest.push(alt); else medienS.freigeben(alt);
  // Anlauf-Gnade wie beim Start: bis zur Quellenwahl ist currentSrc des neuen
  // leer, der Takt hielte das sonst für das Filmende.
  tvpLief=false; tvpTicks=0;
  tvpVideoVerdrahten(neu,tvpIdAkt,0);
  neu.addEventListener('playing',tvpAbgeloestFreigeben,{once:true});
  neu.src=src; neu.play().catch(()=>{});
  return neu;
}
function tvFilmPlayer(id,titel,pos,meta){
  // Nächste Folge derselben Film-Sitzung (⏭/⏮ über tvpWechselStarten): Tempo und
  // Stumm bleiben (24.09.2026: „Behalten"). Jeder andere Start (Bibliothek,
  // Live, VLC-Rückfall) beginnt bei 1x mit Ton — und das Tempo-Menü (tvpRateWert)
  // zeigt immer, was wirklich läuft.
  const folgenwechsel=tvpOffen&&!!tvpWechsel&&tvpWechsel.id===id;
  if(!folgenwechsel)tvpRateWert=1;
  tvpOffen=true; tvpPos=pos||0; tvpDauer=0; tvpLief=false; tvpTicks=0; tvpAktiv=Date.now();
  tvpIdAkt=id;
  tvpGesehenGemeldet='';                               // neuer Start: sein Ende darf wieder melden
  // Mindest-Sehzeit: jede Wiedergabe zählt für sich, ab ihrer Startstelle.
  tvpSeh={start:pos||0, w:0, letzte:null, uhr:0, tempo:0, stueck:null, stuecke:[]};
  // Die volle Meta aus filmePlay (Folgen stehen nie in tvInfoDaten/tvHeroDaten):
  // ohne sie fehlten bei Folgen typ/serie_id (Weiter/Zurück) und laufzeit_min —
  // im Transcode blieb die Zeitleiste dann tot (Dauer 0, Befund 23.09.).
  tvpMeta=(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.id===id)?tvInfoDaten.d
         :(typeof tvHeroDaten!=='undefined'&&tvHeroDaten&&tvHeroDaten.id===id)?tvHeroDaten
         :(meta&&!meta.fehler)?meta
         :{titel:titel||''};                           // Hero-Start: Meta trotzdem da
  // Zurück-Regel: kam diese Folge per „Zurück", gilt ihr Modus (siehe tvpZurueckZiel).
  tvpZurueckModus=(tvpModusNaechster&&tvpModusNaechster.id===id)?tvpModusNaechster.modus:'normal';
  tvpModusNaechster=null;
  if(tvpWechsel&&tvpWechsel.id===id)tvpWechsel=null;  // der ausstehende Folgenwechsel ist angekommen
  // Schlüssel SOFORT (sonst erst mit dem nächsten Takt): Esc direkt nach einem
  // Folgenwechsel schrieb sonst die Stelle der NEUEN Folge in die VORIGE.
  if(tvpModus!=='browser')vlcKeyLetzter=id?'film:'+id:'live:'+(titel||'');
  let el=document.getElementById('tv-player');
  if(!el){el=document.createElement('div'); el.id='tv-player';}
  // Beim Folgenwechsel per Taste ist der Player selbst das Vollbild-Element —
  // sich selbst anhängen wirft (HierarchyRequestError). Dann bleibt er, wo er ist.
  const zielEl=document.fullscreenElement||document.body;
  if(zielEl!==el&&!el.contains(zielEl))zielEl.appendChild(el);
  el.style.display='flex';
  // Netflix-Layout (Besitzer-Player-Bilder): ← oben links, Leiste UNTEN über die
  // volle Breite (roter Balken + Zeit rechts), darunter ⏯ ±10 🔊 links und
  // der Titel mittig. Bei Inaktivität blendet alles aus (tvpIdleTick).
  // Browser-Modus: das <video> IST das Bild (Netflix-Weg, der Besitzer 06.08.) —
  // Pause zeigt automatisch das echte Standbild des Films.
  if(tvpModus==='browser'&&tvpTc)tvpTcOffset=pos||0;   // Strom startet AB pos
  const medien=tvpModus==='browser'
    ?`<video id="tvp-video" class="tvp-video" autoplay playsinline `+
     `src="${tvpDirektSrc(pos||0)}"></video>`
    :`<img class="tvp-bg" src="/api/filme/bild?id=${encodeURIComponent(id)}&art=Backdrop" onerror="this.style.visibility='hidden'">`;
  const altV=document.getElementById('tvp-video');     // Folgenwechsel: die alte Folge verstummt sofort …
  const stumm=folgenwechsel&&!!altV&&!!altV.muted;     // Stumm gibt es nur im Browser-Video (Taste M)
  if(altV){try{altV.pause();}catch(e){} tvpAbgeloest.push(altV);}
  el.innerHTML=
    medien+
    `<img id="tvp-standbild" class="tvp-standbild" style="display:none">`+
    `<div class="tvp-ui">`+
      `<button class="tvp-zurueck" onclick="filmStopp()" title="Beenden (Esc)">←</button>`+
      `<div class="tvp-unten">`+
        `<div class="tvp-balkenzeile"><div class="tvp-balkenwrap" onclick="tvpSeek(event)">`+
          `<div class="tvp-balken"><div id="tvp-fuell"></div></div></div>`+
          `<span id="tvp-zeit" class="tvp-zeit">–</span></div>`+
        `<div class="tvp-reihe">`+
          `<button class="tvp-ib" id="tvp-pp" onclick="tvpBefehl('toggle');setTimeout(tvpTick,300)" title="Pause/Weiter (Leertaste)">${ico('pause')}</button>`+
          `<button class="tvp-ib" onclick="tvpRel(-10)" title="10 s zurück">${ico('r10')}</button>`+
          `<button class="tvp-ib" onclick="tvpRel(10)" title="10 s vor">${ico('f10')}</button>`+
          `<span class="pl-bvolwrap" style="color:#fff">🔊<input type="range" class="pl-bvol" min="0" max="100" value="${plVol}" oninput="plbVol(this.value);tvpBefehl('vol',{wert:plVol})"></span>`+
          `<div class="tvp-mtitel">${esc(tvpMeta.titel||'')}</div>`+
          `<span class="tvp-rechts">`+
            `<button class="tvp-ib" onclick="tvpPanel('spuren')" title="Ton & Untertitel">${ico('sub')}</button>`+
            `<button class="tvp-ib" onclick="tvpPanel('tempo')" title="Wiedergabetempo">${ico('speed')}</button>`+
            `<button class="tvp-ib" onclick="tvpVollbild()" title="Vollbild an/aus">${ico('full')}</button>`+
            `<button class="tvp-ib" onclick="filmStopp()" title="Beenden (Esc)">${ico('kreuz')}</button>`+
          `</span>`+
        `</div>`+
      `</div>`+
      `<div id="tvp-panel" style="display:none"></div>`+
      `<div class="tvp-lade" id="tvp-lade"><div class="tvp-spin"></div>`+
        `<span id="tvp-lade-text">${pos>0?'Springt zu '+zeit(pos)+' …':'Lädt …'}</span></div>`+
      `<div class="tvp-idle" id="tvp-idle" style="display:none">`+
        `<div class="tvp-idle-klein">Du siehst</div>`+
        `<div class="tvp-idle-titel">${esc(tvpMeta.titel||'')}</div>`+
        `<div class="tvp-idle-meta">${[tvpMeta.jahr,esc(tvpMeta.fsk||''),tvpMeta.laufzeit_min?tvpMeta.laufzeit_min+' min':''].filter(Boolean).join('   ')}</div>`+
        `<div class="tvp-idle-besch">${esc((tvpMeta.beschreibung||'').slice(0,220))}</div>`+
        `<div class="tvp-idle-paused">Pausiert</div>`+
      `</div>`+
    `</div>`;
  ['pointermove','pointerdown','keydown'].forEach(evn=>el.addEventListener(evn,tvpWach));
  if(tvpModus==='browser'){
    const v=document.getElementById('tvp-video');
    if(v){
      v.volume=Math.max(0,Math.min(1,plVol/100));
      // Tempo auch als defaultPlaybackRate: jedes Laden setzt playbackRate darauf zurück.
      v.defaultPlaybackRate=v.playbackRate=tvpRateWert; v.muted=stumm;
      tvpVideoVerdrahten(v,id,pos);
    }
  }else{
    // VLC: NACH dem Start setzen. Die Film-Route setzt kein Tempo, und der EINE
    // VLC (Musik + Film) behielte sonst womöglich das seines Vorgängers.
    tvpBefehl('rate',{wert:tvpRateWert});
  }
  const neuV=document.getElementById('tvp-video');     // … und wird geleert, sobald die neue spielt
  if(neuV&&neuV!==altV)neuV.addEventListener('playing',tvpAbgeloestFreigeben,{once:true});
  else tvpAbgeloestFreigeben();                        // kein neues Video (VLC): sofort
  // Die VLC-Fernbedienung geht NUR bei MEHREREN Monitoren selbst ins
  // Vollbild (auf einem verdeckte sie das VLC-Bild); der BROWSER-Player
  // darf immer — sein Bild liegt ja IM Overlay.
  try{
    if((tvpModus==='browser'||screen.isExtended)&&el.requestFullscreen)
      el.requestFullscreen().catch(()=>{});
  }catch(e){}
  if(!tvpTimer)tvpTimer=setInterval(tvpTick,1000);
  setTimeout(tvpTick,600);
  tvpMedienAn();                                       // Medientasten + Windows-Overlay gehören jetzt dem Film
}
function tvpWach(){
  tvpAktiv=Date.now();
  const el=document.getElementById('tv-player'); if(el)el.classList.remove('idle');
  const idle=document.getElementById('tvp-idle'); if(idle)idle.style.display='none';
}
/* Player-Settings (06.08.: „es fehlen noch settings im player. Untertitel,
   playback speed, Vollbild") — Panels im Netflix-Stil über der Leiste. */
let tvpRateWert=1, tvppFokus=0;
function tvppFokusMalen(kn){
  kn.forEach((k,i)=>k.classList.toggle('tv-fokus',i===tvppFokus));
  const z=kn[tvppFokus]; if(z&&z.scrollIntoView)z.scrollIntoView({block:'nearest'});
}
async function tvpPanel(art){
  const p=document.getElementById('tvp-panel'); if(!p)return;
  tvpWach(); tvppFokus=0;
  if(p.dataset.art===art&&p.style.display!=='none'){p.style.display='none'; return;}
  p.dataset.art=art;
  if(art==='tempo'){
    p.innerHTML='<div class="tvpp-titel">Wiedergabetempo</div><div class="tvpp-reihe">'+
      [0.5,0.75,1,1.25,1.5].map(x=>`<button class="tvpp-knopf${Math.abs(x-tvpRateWert)<0.01?' an':''}"`+
        ` data-w="${x}" onclick="tvpRate(+this.dataset.w)">${x===1?'1x (Normal)':x+'x'}</button>`).join('')+'</div>';
  }else{
    p.innerHTML='<div class="tvpp-titel">Lädt …</div>'; p.style.display='block';
    let s={}; try{s=await tvpBefehl('spuren')||{};}catch(e){}
    // Race (Nachtprüfung): wurde das Panel während des Ladens geschlossen
    // oder umgeschaltet, das späte Ergebnis NICHT mehr malen.
    if(p.dataset.art!=='spuren'||p.style.display==='none')return;
    tvpRateWert=s.rate||tvpRateWert;
    const li=(arr,aktiv,art2)=>(arr||[]).filter(t=>art2==='sub'||t.id>=0).map(t=>
      `<button class="tvpp-knopf${t.id===aktiv?' an':''}" data-art="${art2}" data-id="${t.id}" onclick="tvpSpur(this.dataset.art,+this.dataset.id)">`+
      esc(art2==='sub'&&t.id<0?'Aus':(t.name||('Spur '+t.id)))+'</button>').join('');
    p.innerHTML='<div class="tvpp-spalten">'+
      `<div><div class="tvpp-titel">Ton</div>${li(s.ton,s.ton_aktiv,'ton')||'<span class="tvpp-leer">keine Spuren</span>'}</div>`+
      `<div><div class="tvpp-titel">Untertitel</div>${li(s.sub,s.sub_aktiv,'sub')||'<span class="tvpp-leer">keine</span>'}</div>`+
      '</div>';
  }
  p.style.display='block';
}
async function tvpSpur(art,id){
  try{await vlcBefehl('spur',{art,id});}catch(e){}     // Spuren gibt es nur im VLC
  const p=document.getElementById('tvp-panel'); if(p)p.style.display='none';
  tvpPanel('spuren');                                  // neu öffnen = frische Häkchen
}
async function tvpRate(w){
  tvpRateWert=w;
  try{await tvpBefehl('rate',{wert:w});}catch(e){}
  const p=document.getElementById('tvp-panel'); if(p)p.style.display='none';
  tvpPanel('tempo');
}
function tvpVollbild(){
  const el=document.getElementById('tv-player'); if(!el)return;
  if(document.fullscreenElement){try{document.exitFullscreen();}catch(e){}}
  else if(el.requestFullscreen)el.requestFullscreen().catch(()=>{});
}
function tvpIdleTick(spielt){
  // Netflix-Verhalten (Bilder): Inaktivität blendet die Leiste aus; wer in
  // PAUSE verharrt, bekommt den ruhigen „Du siehst …"-Schirm (Bild 3).
  const el=document.getElementById('tv-player'); if(!el)return;
  const still=Date.now()-tvpAktiv>3500;
  el.classList.toggle('idle',still);
  const idle=document.getElementById('tvp-idle');
  if(!idle)return;
  const zeigen=still&&!spielt;
  // Der Besitzer 07.08.: „kein neues bild — das pause gehaltene Bild nehmen und den
  // Text darüberlegen." Im Browser-Modus steht das <video> selbst als
  // Standbild, der Text liegt einfach darüber. NUR in der HÜLLE mit VLC
  // (natives Panel, Text kann nicht darüber) ersetzt ein frischer
  // Schnappschuss den Moment.
  const bg=document.getElementById('tvp-standbild');
  const huelleVlc=tvpModus!=='browser'&&!!window.pywebview;
  if(zeigen&&idle.style.display==='none'&&huelleVlc){
    vlcBefehl('standbild').then(()=>{
      if(bg){
        bg.src='/api/vlc_standbild?t='+Date.now();
        // gleiche Fläche wie das Video-Panel (bis zur Leiste) — sonst
        // springt die Bildgröße beim Pause-Schirm (07.08.).
        const u=document.querySelector('#tv-player .tvp-unten');
        if(u)bg.style.bottom=(innerHeight-u.getBoundingClientRect().top)+'px';
      }
    }).catch(()=>{});
  }
  idle.style.display=zeigen?'flex':'none';
  if(bg)bg.style.display=(zeigen&&huelleVlc)?'block':'none';
}
function tvpZu(){
  // Ein verzögerter Sprung trifft nichts mehr, ein liegengebliebener Zurück-Modus
  // vererbt sich nicht, und die Folgenliste merkt sich die Stelle (Esc,
  // Folgenende, Rückfall — alles läuft hier durch). Einen ladenden Wechsel
  // bricht nur filmStopp ab.
  clearTimeout(_tvpSprungTimer); tvpModusNaechster=null;
  // Schon als gesehen gemeldet: dort steht Stelle 0 (wie bei Jellyfin), nicht
  // die Stelle kurz vor dem Ende.
  if(tvpIdAkt&&tvpGesehenGemeldet!==tvpIdAkt)tvpFolgePosMerken(tvpIdAkt,Math.round(tvpPos||0));
  tvpOffen=false; tvpModus='vlc'; tvpTc=false; tvpTcOffset=0;   // nie hängen lassen
  medienNachFilm();                                    // Overlay + Tasten zurück an die Musik
  if(tvpTimer){clearInterval(tvpTimer); tvpTimer=null;}
  const pw=window.pywebview&&window.pywebview.api;   // Hüllen-Bild freigeben
  if(pw&&pw.video_rect){try{pw.video_rect(0,0,0,0,false);}catch(e){}}
  const el=document.getElementById('tv-player');
  if(el){
    if(document.fullscreenElement===el){try{document.exitFullscreen();}catch(e){}}
    medienS.freigeben(document.getElementById('tvp-video'));   // sonst hält es Windows' Eintrag
    el.style.display='none'; el.innerHTML='';
  }
  tvpAbgeloestFreigeben();                             // alte Folgen, deren Nachfolger nie spielte
}
/* Der Film ist zu Ende — oder der VLC gehört inzwischen jemand anderem (Musik,
   Live). Reihenfolge: Werte festhalten → tvpZu (räumt Modus und Offen-Zustand,
   merkt die Stelle in der Folgenliste) → melden (schreibt „gesehen" und Stelle 0
   DANACH, sonst überschriebe tvpZu sie wieder). „Gesehen" gilt nur beim eigenen
   Ende: Browser 'aus' bzw. VLC 'aus'/'ende' mit dem Schlüssel dieses Films;
   sonst gehört der Status (Stelle!) der Musik. Die Dauer geht in beiden Fällen
   mit: ohne eigenes Ende braucht die Meldestelle sie für Jellyfins Grenze
   (Mindest-Sehzeit). Rückgabe: was danach kommt. */
function tvpFilmEnde(s,modusVor){
  const id=tvpIdAkt, lief=tvpLief;
  const eigen=modusVor==='browser'||(!!id&&s.key==='film:'+id);
  const echtesEnde=eigen&&(s.zustand==='aus'||s.zustand==='ende');
  const pos=Math.max(tvpPos||0,(lief&&eigen)?(s.pos||0):0);
  const dauer=tvpMeldeDauer(id);                       // VOR tvpZu: danach ist der Player zu
  tvpZu();
  // libvlc hält den Endzustand samt Schlüssel, bis etwas Neues kommt: freigeben —
  // nur, wenn der VLC noch DIESEN Film hat (nur_key: sonst träfe es die Musik),
  // und nur bei einem echten Ende ('ende' oder er lief). Ein Start, der nach 8
  // Takten noch öffnet ('aus'), läuft weiter wie vor dem 24.09. — der Stopp
  // würgte sonst jeden langsamen Jellyfin-Strom ab (Prüfung Runde 2).
  if(modusVor!=='browser'&&id&&s.key==='film:'+id&&(lief||s.zustand==='ende')){
    vlcBefehl('stop',{nur_key:'film:'+id}); vlcKeyLetzter='';}
  // Gemeldet wird, was lief — oder eine Folge, die nahe am Ende fortgesetzt
  // wurde und endete, bevor sie je 'spielt' meldete (dann zählt die Einstiegsstelle).
  if(id&&(lief||(echtesEnde&&dauer>0&&pos>=dauer*SEHZEIT.gesehenAb)))filmFortschrittMelden(id,pos,dauer,echtesEnde?'ende':false);
  else if(tvInfoOffen)tvInfoMalen();
  return nachFilmEnde();
}
async function tvpTick(){
  if(!tvpOffen)return;
  const idVor=tvpIdAkt, modusVor=tvpModus;
  let s=null;
  try{s=await tvpBefehl('status');}catch(e){return;}
  if(!s)return;
  // Die Antwort gehört zu einer anderen Folge/einem anderen Motor (Wechsel lief
  // dazwischen): verwerfen — sonst überschrieb sie Schlüssel und Stelle der
  // neuen Folge (Gegenprüfung 24.09.).
  if(!tvpOffen||tvpIdAkt!==idVor||tvpModus!==modusVor)return;
  // Lädt ein Folgenwechsel im VLC, meldet der Server schon die NEUE Folge — die
  // gehört noch nicht zu dieser Fernbedienung (weder Stelle noch Zustand).
  if(tvpWechsel&&tvpModus!=='browser'&&s.key!=='film:'+tvpIdAkt)return;
  if(s.zustand==='spielt')tvpLief=true;
  tvpTicks++;
  // Fund: vlcKeyLetzter setzte nur der Geräte-VLC-Takt — ohne ihn war
  // filmStopp/Esc/← ein stiller No-op. Der Film-Takt pflegt ihn selbst — aber
  // nur für einen VLC-Film: beim Browser-Film gehört der Geräte-VLC der Musik.
  if(tvpModus!=='browser'){vlcKeyLetzter=s.key||vlcKeyLetzter; vlcSpielt=(s.zustand==='spielt');}
  tvpIdleTick(s.zustand==='spielt');
  // Ende-Erkennung mit ANLAUF-GNADE (live gefunden: der erste Tick kam vor
  // VLCs „spielt" und schloss die Fernbedienung sofort wieder): erst
  // schließen, wenn der Film nachweislich lief oder der Start nie kam.
  // Nicht, solange ein Folgenwechsel lädt: der VLC meldet den Anlauf der NEUEN
  // Folge als 'aus' — das ist kein Ende (Gegenprüfung 24.09.: sonst Film weg).
  // libvlc meldet das Ende als 'ende' (nicht 'aus') und bleibt dort stehen —
  // bis 24.09. blieb die Fernbedienung darum mit Spinner offen (folgenende.md).
  // Nur mit dem Schlüssel DIESES Films (Live bleibt, wie es war: unbestätigt).
  const eigenesEnde=s.zustand==='ende'&&!!tvpIdAkt&&s.key==='film:'+tvpIdAkt;
  if(!tvpWechsel&&(!/^(film|live):/.test(s.key||'')||s.zustand==='aus'||eigenesEnde)&&(tvpLief||tvpTicks>8)){
    tvpFilmEnde(s,modusVor);
    return;
  }
  // Ein kurzes 'ende' im Anlauf (VLC zwischen zwei Titeln) trägt die Stelle des
  // VORIGEN Mediums — sie gehört nicht zu dieser Folge.
  if(!(s.zustand==='ende'&&!tvpLief))tvpPos=s.pos||tvpPos;
  // Mindest-Sehzeit im VLC: aus den Stellen dieses Takts, mit derselben
  // Sprung-Regel (im Browser misst das <video> selbst, tvpVideoVerdrahten).
  if(tvpModus!=='browser')tvpSehzeitZaehlen(s.pos,s.zustand==='spielt',s.rate||1);   // vlc_status liefert das Tempo mit
  tvpDauer=s.dauer||tvpDauer;
  tvpMedienZustand();                                  // Windows-Zeitleiste (Transcode: Offset + Meta-Dauer)
  // Lade-Spinner (Freigabe): sichtbar, bis der Film WIRKLICH spielt — deckt den
  // langsamen Index-/Seek-Anlauf mancher Container über die Leitung ehrlich ab.
  const lade=document.getElementById('tvp-lade');
  if(lade)lade.style.display=(s.zustand==='spielt'||(tvpLief&&s.zustand==='pause'))?'none':'flex';
  const pp=document.getElementById('tvp-pp'); if(pp)pp.innerHTML=ico(s.zustand==='spielt'?'pause':'play');
  // In der PROGRAMM-HÜLLE ist die Bedienung IM Player (der Besitzer): das eingebettete
  // VLC-Bild bekommt die Fläche BIS zur Leisten-Oberkante gemeldet.
  // Nachtprüfung 06.08.: das NATIVE Panel verdeckte Settings-Panel,
  // Lade-Spinner und Pause-Schirm — darum: Fläche endet auch an der
  // Panel-Oberkante, und solange Spinner/Pause-Schirm sichtbar sind,
  // wird das Panel ganz versteckt (der Browser zeigt Backdrop + Overlay).
  const pw=window.pywebview&&window.pywebview.api;
  if(pw&&pw.video_rect&&tvpModus==='browser'){
    try{pw.video_rect(0,0,0,0,false);}catch(e){}      // <video> rendert selbst
  }else if(pw&&pw.video_rect){
    const u=document.querySelector('#tv-player .tvp-unten');
    const dpr=window.devicePixelRatio||1;
    // Der Besitzer 07.08.: „das bild wird plötzlich größer wenn die Bedienung
    // ausblendet" — die Leisten-Fläche bleibt jetzt IMMER reserviert
    // (auch im Idle nur Inhalte ausgeblendet), das Bild ist konstant.
    let bis=u?u.getBoundingClientRect().top:window.innerHeight;
    const pan=document.getElementById('tvp-panel');
    if(pan&&pan.style.display!=='none')
      bis=Math.min(bis,pan.getBoundingClientRect().top);
    const idle2=document.getElementById('tvp-idle');
    const spinner=lade&&lade.style.display!=='none';
    const pauseSchirm=idle2&&idle2.style.display!=='none';
    if(spinner||pauseSchirm){try{pw.video_rect(0,0,0,0,false);}catch(e){}}
    else{try{pw.video_rect(0,0,Math.round(innerWidth*dpr),Math.round(bis*dpr),true);}catch(e){}}
  }
  const f=document.getElementById('tvp-fuell');
  if(f&&tvpDauer)f.style.width=Math.min(100,tvpPos/tvpDauer*100)+'%';
  const z=document.getElementById('tvp-zeit'); if(z)z.textContent=zeit(tvpPos)+' / '+zeit(tvpDauer);
}
function tvpLadeZeigen(text){
  const l=document.getElementById('tvp-lade'), t=document.getElementById('tvp-lade-text');
  if(t)t.textContent=text; if(l)l.style.display='flex';
}
function tvpRel(s){
  tvpPos=Math.max(0,Math.min(tvpDauer||1e9,tvpPos+s));
  if(tvpModus!=='browser')tvpLadeZeigen('Springt zu '+zeit(tvpPos)+' …');
  tvpBefehl('seek',{wert:tvpPos});
  setTimeout(tvpTick,300);
}
function tvpSeek(ev){
  const wrap=ev.currentTarget.querySelector('.tvp-balken');
  const r=wrap.getBoundingClientRect();
  if(!tvpDauer||!r.width)return;
  tvpPos=Math.max(0,Math.min(tvpDauer,(ev.clientX-r.left)/r.width*tvpDauer));
  if(tvpModus!=='browser')tvpLadeZeigen('Springt zu '+zeit(tvpPos)+' …');
  tvpBefehl('seek',{wert:tvpPos});
  setTimeout(tvpTick,300);
}
/* ---- Medientasten im Film (23.09.2026: „Film steuern + nächste Folge") ---
   Play/Pause/Spulen wirken auf den Film, nie auf die Musik darunter. Bei
   Serien schaltet „Weiter" zur nächsten Folge; „Zurück" folgt Besitzer-Regel
   (Variante C, x = 3 s): 1. Druck = Vorfolge an ihrer gemerkten Stelle — war
   sie zu Ende geschaut, direkt an den Anfang —, 2. Druck = Anfang dieser
   Folge, ab da wie beim Musik-Player (über 3 s: Anfang, sonst noch eine Folge
   zurück). Ein Einzelfilm bekommt kein Weiter/Zurück: lieber kein Knopf als
   einer, der ins Leere greift oder einen langen Film versehentlich neu startet.
   Läuft der Film im VLC (Hülle, Live-TV), meldet der Server ihn bei Windows an;
   die Seite liefert ihm Titel, Bild und ob es Weiter/Zurück gibt. */
let tvpMedienGen=0, tvpZurueckModus='normal', tvpModusNaechster=null, tvpFolgenCache=null, _tvpSprungTimer=null, tvpWechsel=null, tvpWechselGen=0;
function tvpLandePos(e){
  // Gemerkte Stelle — außer die Folge ist zu Ende geschaut (gesehen, oder ab
  // 90 %: Jellyfins Standard-Grenze für „gespielt") oder kaum angefangen
  // (bis 30 s, wie bei den Folgen-Kacheln der Infoseite).
  if(!e||e.gesehen)return 0;
  const p=e.position_s||0, d=(e.laufzeit_min||0)*60;
  if(p<=30||(d&&p>=d*SEHZEIT.jfMaxResume))return 0;
  return p;
}
function tvpZurueckZiel(eps,aktId,pos,modus){
  const i=(eps||[]).findIndex(e=>e.id===aktId);
  if(i<0)return null;                                  // Folge fehlt in der Liste: lieber nichts als ein Neustart
  if(modus==='gelandet'||(modus==='musik'&&pos>3))return {art:'anfang',modus:'musik'};
  const vor=i>0?eps[i-1]:null;
  if(!vor)return {art:'anfang',modus:'musik'};
  const p=tvpLandePos(vor);
  return {art:'folge',e:vor,pos:p,modus:p>0?'gelandet':'musik'};
}
function tvpWeiterZiel(eps,aktId){
  const i=(eps||[]).findIndex(e=>e.id===aktId);
  if(i<0||i+1>=eps.length)return null;
  const n=eps[i+1];
  return {art:'folge',e:n,pos:tvpLandePos(n),modus:'normal'};
}
async function tvpFolgenHolen(){
  const m=tvpMeta||{};
  if(m.typ!=='folge'||!m.serie_id)return null;         // Einzelfilm/Live: keine Folgen
  if(tvInfoDaten&&tvInfoDaten.d&&tvInfoDaten.d.id===m.serie_id&&(tvInfoDaten.eps||[]).length)return tvInfoDaten.eps;
  if(tvpFolgenCache&&tvpFolgenCache.sid===m.serie_id)return tvpFolgenCache.eps;
  try{
    const j=await (await fetch('/api/filme/episoden?id='+encodeURIComponent(m.serie_id))).json();
    const l=(j&&j.items)||[];
    // Jellyfin-Fehler kommen als LEERE Liste (HTTP 200) — nicht für die Sitzung
    // festschreiben, der nächste Druck fragt neu.
    if(!l.length)return null;
    tvpFolgenCache={sid:m.serie_id, eps:l};
    return l;
  }catch(e){return null;}
}
/* Lädt die Zielfolge noch (Detail-Abruf an den Film-Server), rechnet der nächste
   Druck von IHR aus, nicht von der alten Folge — sonst traf ein schneller
   zweiter ⏮ dieselbe Folge, und Besitzer-„2. Druck = Anfang" ging verloren
   (Prüf-Befund 24.09.). */
function tvpBasis(){
  return tvpWechsel?{id:tvpWechsel.id, pos:tvpWechsel.pos, modus:tvpWechsel.modus}
                   :{id:tvpIdAkt, pos:tvpPos, modus:tvpZurueckModus};
}
async function tvpFolge(dir){
  if(dir<0)return tvpZurueck();
  if(!tvpOffen)return;
  const eps=await tvpFolgenHolen(); if(!eps||!tvpOffen)return;
  tvpZielAusfuehren(tvpWeiterZiel(eps,tvpBasis().id),eps);
}
async function tvpZurueck(){
  if(!tvpOffen)return;
  const eps=await tvpFolgenHolen(); if(!eps||!tvpOffen)return;   // Einzelfilm: kein Zurück
  const b=tvpBasis();
  tvpZielAusfuehren(tvpZurueckZiel(eps,b.id,b.pos,b.modus),eps);
}
function tvpFolgePosMerken(id,pos,gesehen){            // Folgenliste (Info-Seite + Zwischenspeicher) nachziehen
  const setze=l=>(l||[]).forEach(e=>{if(e.id===id){e.position_s=pos; if(gesehen)e.gesehen=true;}});
  if(tvInfoDaten)setze(tvInfoDaten.eps);
  if(tvpFolgenCache)setze(tvpFolgenCache.eps);
}
function tvpWechselStarten(id,pos,modus){
  const gen=++tvpWechselGen;                           // überholt jeden älteren, noch ladenden Wechsel
  tvpWechsel={gen, id, pos, modus};
  tvpModusNaechster={id, modus};
  filmePlay(id,pos,gen);
}
function tvpZielAusfuehren(z,eps){
  if(!z||!tvpOffen)return;
  if(z.art==='anfang'){
    if(tvpWechsel){tvpWechselStarten(tvpWechsel.id,0,z.modus); return;}   // Ziel lädt noch: von vorn
    tvpZurueckModus=z.modus; tvpPos=0;
    if(tvpModus!=='browser')tvpLadeZeigen('Springt zu '+zeit(0)+' …');
    tvpBefehl('seek',{wert:0}); setTimeout(tvpTick,300);
    return;
  }
  // Die laufende Folge meldet ihre Stelle (wie filmStopp) — ein späteres
  // „Weiter" führt genau dorthin zurück; im Abspann (ab 90 %) ist sie gesehen (der Besitzer),
  // wenn die Mindest-Sehzeit reicht — sonst die gemeldete Stelle (sehzeitUrteil).
  // Nur beim ERSTEN Druck: danach läuft die alte Folge bloß weiter, bis das Ziel lädt.
  const id=tvpIdAkt, pos=Math.round(tvpPos||0);
  if(id&&!tvpWechsel){
    const m=filmFortschrittMelden(id,pos,tvpMeldeDauer(id));
    (eps||[]).forEach(e=>{if(e.id===id&&m.stelle!==null){e.position_s=m.gesehen?0:m.stelle; if(m.gesehen)e.gesehen=true;}});
  }
  tvpWechselStarten(z.e.id,z.pos,z.modus);
}
function tvpMedien(was){                               // Windows-Play/-Pause gezielt (kein blindes Umschalten)
  if(!tvpOffen)return;
  if(tvpModus==='browser'){
    const v=document.getElementById('tvp-video'); if(!v)return;
    if(was==='play')v.play().catch(()=>{}); else v.pause();
  }else if((was==='play')!==vlcSpielt)tvpBefehl('toggle');
  setTimeout(tvpTick,300);
}
function tvpSpringeAuf(t){
  if(!tvpOffen)return;
  const ziel=Math.max(0,Math.min(tvpDauer||1e9,t)), id=tvpIdAkt;
  tvpPos=ziel;
  if(tvpModus!=='browser')tvpLadeZeigen('Springt zu '+zeit(ziel)+' …');
  // Der Overlay-Regler feuert beim Ziehen ganze Serien — im Transcode startet
  // jeder Sprung ffmpeg neu. Darum erst springen, wenn der Regler ruht. Das
  // Ziel steht fest (der 1-s-Takt überschreibt tvpPos zwischendurch), und nach
  // Esc oder Folgenwechsel gilt der Sprung nicht mehr (Prüf-Befund 24.09.:
  // sonst traf er als VLC-Befehl die Musik).
  clearTimeout(_tvpSprungTimer);
  _tvpSprungTimer=setTimeout(()=>{
    if(!tvpOffen||tvpIdAkt!==id)return;
    tvpPos=ziel; tvpBefehl('seek',{wert:ziel}); setTimeout(tvpTick,300);
  },250);
}
function tvpFolgeTitel(t){                             // „Dark · S1 F3 — Name" (filme._folge_holen)
  const m=/^(.*?) · S(\d+) F(\d+)(?: — (.*))?$/.exec(t||'');
  return m?{serie:m[1], name:m[4]||t, staffel:+m[2], folge:+m[3]}:null;
}
async function tvpMedienAn(){
  const gen=++tvpMedienGen;
  medienTastenAnmelden();
  const m=tvpMeta||{}, live=!tvpIdAkt;
  const f=m.typ==='folge'?tvpFolgeTitel(m.titel):null;
  const titel=f?f.name:(m.titel||'');
  const interpret=f?f.serie:[m.jahr,(m.regie||[])[0]].filter(Boolean).join(' · ');
  const album=f?'Staffel '+f.staffel+' · Folge '+f.folge:(live?'📡 Live':'');
  const cover=live?'':'/api/filme/bild?id='+encodeURIComponent(tvpIdAkt)+'&art=Primary';
  const eps=f?await tvpFolgenHolen():null;
  if(gen!==tvpMedienGen||!tvpOffen)return;             // inzwischen zu oder schon die nächste Folge
  const weiter=!!(eps&&tvpWeiterZiel(eps,tvpIdAkt)), zurueck=!!(eps&&eps.length);
  if(tvpModus!=='browser')                             // Ton im VLC: der Server meldet bei Windows an
    vlcBefehl('medien',{key:live?'live:'+titel:'film:'+tvpIdAkt, titel, interpret, album, cover, weiter, zurueck});
  // Die Browser-Kachel (falls es sie wegen weiterlaufender Musik gibt) zeigt und
  // steuert den Film ebenfalls — die Tasten gehören ihm (der Besitzer).
  const bilder=[[cover,'512x512']];
  if(f&&m.serie_id)bilder.push(['/api/filme/bild?id='+encodeURIComponent(m.serie_id),'512x512']);
  medienS.info({title:titel, artist:interpret, album, artwork:medienS.bilder(bilder)});
  medienS.aktionen({'nexttrack':weiter?_msWeiter:null, 'previoustrack':zurueck?_msZurueck:null});
  tvpMedienZustand();
}
function tvpMedienZustand(){                           // Browser-Film: Zustand + Zeitleiste ans Overlay
  if(!tvpOffen||tvpModus!=='browser')return;
  const v=document.getElementById('tvp-video');
  medienS.zustand(v&&!v.paused?'playing':'paused',{dauer:tvpDauer, pos:tvpPos, rate:v?v.playbackRate:1});
}
/* ---- Stelle und „gesehen" melden (folgenende.md, der Besitzer 24.09.2026) ----------
   EINE Meldestelle für Takt-Ende, Esc/←/✕ (filmStopp) und den Folgenwechsel
   per ⏭/⏮. Bis 24.09. sandte die Seite „gesehen" nie: Jellyfin und die lokalen
   Listen erfuhren kein Ende, die Kachel zeigte ⏸ statt ✓, „▶ Weiterschauen"
   wählte die fertige Folge. Vorgabe: auch Esc oder ⏭ im Abspann zählen. Ob es
   „gesehen" ist, entscheidet seit Runde 3 die Mindest-Sehzeit (sehzeitUrteil).
   Einmalig: ist „gesehen" für eine Kennung hinausgegangen, meldet sie bis zu
   ihrem nächsten Start nichts mehr (sonst schriebe eine späte Stelle darüber).
   Geht die Seite selbst (Hülle zu, Tab zu, neu laden), meldet filmAbschied —
   auch das über diese Stelle (Nacharbeit Runde 3). */
let tvpGesehenGemeldet='', filmGemeldet={}, tvpSeh={start:0, w:0, letzte:null, uhr:0, tempo:0, stueck:null, stuecke:[]};   // Kennung mit „gesehen" · id → {position_s, gesehen} dieser Seite · Sehzeit der offenen Wiedergabe
/* ---- Mindest-Sehzeit (Idee 24.09.2026, wörtlich: „eventuell auch gucken
   wie lange ein film geguckt wurde, sozusagen einen mindest timer um
   festzulegen - bedenken wenn ab einer bestimmten stelle weiter, bzw angefangen
   wird") --------------------------------------------------------------------
   „Gesehen" nur, wenn (a) die Stelle 90 % der Dauer erreicht (das natürliche
   Ende liegt dahinter) UND (b) in DIESER Wiedergabe wirklich geschaute Zeit
   W >= M, M = min(5 min, 50 % × max(0, 90 % der Dauer − Startstelle)).
   Das eigene Ende erfüllt (a), sobald es hinter 90 % der kleinsten möglichen
   Laufzeit liegt (Dauer − 30 s, s. unten): im Transcoder ist die Dauer auf
   Minuten gerundet, ein 151-s-Stück hieße sonst nie „gesehen".
   W = Summe der Spiel-Intervalle in Medienzeit (Tempo egal); ein Sprung ist ein
   Schritt, der mehr als 3 s SCHNELLER lief als die Wanduhr (× Tempo) —
   rückwärts und in Pause zählt nichts. Nicht schon jeder große Abstand: im
   verdeckten Tab drosselt Chrome den 1-s-Takt auf einmal je Minute, der Film
   läuft trotzdem durch (Nacharbeit Runde 3). Startstelle = die
   Stelle, mit der tvFilmPlayer diese Wiedergabe öffnet (Start, Weiterschauen,
   nächste Folge). Gemessen im Browser am <video> (timeupdate; der 1-s-Takt
   ruht im verdeckten Tab), im VLC aus den Stellen des 1-s-Takts.
   Die Schwellen (5 min, 50 %, 3 s, 30 s Spielraum) sind die Regel des
   Hauptagenten (Runde 3) zu Besitzer-Idee — vom Besitzer zu bestätigen.
   Verweigert die Regel „gesehen", darf die gemeldete Stelle Jellyfin nicht
   selbst zum Haken bringen. Jellyfin 12.1 (Tag v12.1, UserDataManager.
   UpdatePlayState, bei JEDER Progress-Meldung) setzt Played bei > 90 % der
   Laufzeit (MaxResumePct), ab Laufzeit − 1 s und — bei Laufzeiten unter 5 min
   (MinResumeDurationSeconds) — schon ab 5 %. Seine Laufzeit kennt die Seite nur
   ungefähr (laufzeit_min ist auf Minuten gerundet): gerechnet wird mit Dauer −
   30 s. Über dieser Grenze geht darum die letzte ECHT geschaute Stelle darunter
   hinaus („vor dem Sprung"), höchstens die Grenze selbst. Ohne bekannte Dauer
   lässt sich keine Grenze beweisen: dann geht gar nichts hinaus (stelle null).
   Der Server rechnet für „Hülle zu" ohne Meldung der Seite dieselbe Grenze
   (youtube_app._stelle_unter_jf_grenze, Gleichheit geprüft im Test). */
const SEHZEIT={gesehenAb:0.9, mindestS:300, mindestAnteil:0.5, sprungS:3, jfMaxResume:0.9, jfKurzS:300, jfSpielraumS:30, uhr:()=>Date.now()/1000};
function tvpSehzeitZaehlen(pos,spielt,tempo){          // eine Stelle der offenen Wiedergabe (Medienzeit)
  const s=tvpSeh, vor=s.letzte, vorUhr=s.uhr, vorTempo=s.tempo, jetzt=SEHZEIT.uhr();
  if(!(pos>=0))return;
  s.letzte=pos; s.uhr=jetzt; s.tempo=tempo;
  if(!spielt||vor===null)return;                       // Pause, erster Wert
  const d=pos-vor, dt=jetzt-vorUhr;
  // So weit darf die Medienzeit in der verstrichenen Wanduhr laufen — mit dem
  // größeren Tempo der beiden Stellen (Tempowechsel dazwischen). Ungültige
  // Werte (NaN) zählen als 0: dann gilt die alte, strenge Regel (nur sprungS).
  const erlaubt=(dt>0?dt:0)*Math.max(tempo>0?tempo:0, vorTempo>0?vorTempo:0);
  if(!(d>0)||d-erlaubt>SEHZEIT.sprungS)return;         // rückwärts oder Sprung
  s.w+=d;
  if(s.stueck&&s.stueck.bis===vor)s.stueck.bis=pos;    // läuft weiter
  else{s.stueck={von:vor, bis:pos}; s.stuecke.push(s.stueck);}
}
/* Rückgabe {gesehen, stelle, zuKurz}: stelle = was an Jellyfin geht (null =
   nichts melden: ohne Dauer keine beweisbare Grenze); zuKurz = die Stelle
   reichte, die Sehzeit nicht. darfGesehen: true = Esc/⏭/Seite geht, 'ende' =
   das eigene Ende des Films, false = kein eigenes Ende (die Musik hat den VLC
   übernommen) — dann nur die Grenze für Jellyfin. seh=null: keine Messung
   dieser Wiedergabe (Esc ohne Fernbedienung) — nie „gesehen", die Grenze. */
function sehzeitUrteil(pos,dauer,seh,darfGesehen){
  const K=SEHZEIT;
  if(!(dauer>0))return {gesehen:false, stelle:null, zuKurz:false};   // ohne Dauer: nie „gesehen", keine Grenze bekannt
  const laufzeit=dauer-K.jfSpielraumS;                 // die kleinste, die Jellyfin haben kann
  const amEnde=pos>=dauer*K.gesehenAb||(darfGesehen==='ende'&&pos>=K.gesehenAb*laufzeit);
  if(darfGesehen&&seh&&amEnde&&seh.w>=Math.min(K.mindestS, K.mindestAnteil*Math.max(0, K.gesehenAb*dauer-seh.start)))
    return {gesehen:true, stelle:pos, zuKurz:false};
  const grenze=laufzeit<K.jfKurzS?0:Math.floor(K.jfMaxResume*laufzeit);
  if(pos<=grenze)return {gesehen:false, stelle:pos, zuKurz:false};
  let echt=seh?seh.start:pos;                          // die letzte ECHT geschaute Stelle unter der Grenze
  if(seh)seh.stuecke.forEach(st=>{if(st.von<grenze)echt=st.bis;});
  return {gesehen:false, stelle:Math.min(Math.round(echt),grenze), zuKurz:!!darfGesehen&&!!seh&&amEnde};
}
function tvpMeldeDauer(id){
  // Nur die OFFENE Folge hat eine gültige Dauer — ohne offenen Player (VLC,
  // Esc aus der Musik-Leiste) sind tvpDauer/tvpMeta vom vorigen Film übrig.
  if(!tvpOffen||!id||id!==tvpIdAkt)return 0;
  return tvpDauer||(((tvpMeta&&tvpMeta.laufzeit_min)||0)*60);
}
/* Rückgabe {gesehen, stelle, zuKurz} (sehzeitUrteil; stelle null = nichts
   gemeldet). Die Sehzeit tvpSeh gehört der offenen Wiedergabe — nur sie hat
   eine Dauer (tvpMeldeDauer). darfGesehen (Vorgabe true): tvpFilmEnde reicht
   'ende' bzw. false durch, filmStopp ohne Fernbedienung false. seh (Vorgabe
   tvpSeh): null = keine Messung dieser Wiedergabe. keepalive: die Meldung
   überlebt das Entladen der Seite (filmAbschied). */
function filmFortschrittMelden(id,pos,dauer,darfGesehen,seh){
  if(!id)return {gesehen:false, stelle:0, zuKurz:false};              // Live: nichts zu melden
  if(tvpGesehenGemeldet===id)return {gesehen:true, stelle:0, zuKurz:false};
  const u=sehzeitUrteil(Math.round(pos||0),dauer,seh===undefined?tvpSeh:seh,
                        darfGesehen===undefined?true:darfGesehen);
  if(u.stelle===null){if(tvInfoOffen)tvInfoMalen(); return u;}        // keine beweisbare Grenze: nichts hinaus
  const koerper={id, position_s:u.stelle}; if(u.gesehen)koerper.gesehen=true;
  try{
    fetch('/api/filme/fortschritt',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(koerper), keepalive:true}).catch(()=>{});
    if(u.gesehen)tvpGesehenGemeldet=id;                 // erst, wenn der Ruf wirklich hinausging
  }catch(e){}
  filmLokalNachziehen(id,u.gesehen?0:u.stelle,u.gesehen);   // wie Jellyfin: gesehen heißt Stelle 0
  return u;
}
/* Die Seite geht mit offenem Film (Nacharbeit Runde 3): Hülle zu, Tab zu oder
   neu laden. Bis dahin meldete sie dann nichts, und für die Hülle schickte der
   Server die rohe VLC-Stelle — über 90 % hakte Jellyfin selbst, an der
   Mindest-Sehzeit vorbei. Das Schließen im Abspann ist dieselbe Art Beenden wie
   Esc (Entscheidung des Hauptagenten, analog zu Besitzer-Esc-Regel vom 24.09.): die
   Seite kennt die Sehzeit und meldet über die EINE Meldestelle, mit keepalive.
   Der Server wartet kurz auf diese Meldung und kappt nur, wenn sie ausbleibt
   (youtube_app._film_stelle_melden). Nichts bei Stelle 0 (der Film lädt noch —
   eine 0 setzte die Weiterschauen-Stelle zurück). Läuft der Film danach im VLC
   weiter (Tab zu, neu laden), ist die Meldung eine Momentaufnahme — im Abspann
   mit reichender Sehzeit gilt er dann schon als gesehen (Grenze, s. Übergabe). */
function filmAbschied(){
  if(!tvpOffen||!tvpIdAkt||!(tvpPos>0))return;
  filmFortschrittMelden(tvpIdAkt,tvpPos,tvpMeldeDauer(tvpIdAkt));
}
window.addEventListener('pagehide',filmAbschied);
function filmGemeldetAnwenden(e){                      // was diese Seite gemeldet hat, gilt auch für frisch Geladenes
  const m=e&&filmGemeldet[e.id];
  if(m){e.position_s=m.position_s; if(m.gesehen)e.gesehen=true;}
  return e;
}
/* Die Merk-Tabelle auf ALLE Reihen (Prüfung Runde 2): auch auf frisch vom
   Server geladene (tvLaden, tvLadenStill, filmeLaden). Den Spiegel zieht nur
   eine angenommene Meldung nach — liegt sie in der Warteschlange, kamen beim
   nächsten Öffnen die alten Reihen, und „Weiterschauen" zeigte den gesehenen
   Film wieder. Wie reihen() am Server: „Weiterschauen" = Stelle > 0 und nicht
   gesehen. */
function filmReihenAnwenden(f){
  if(!f||typeof f!=='object')return f;
  Object.values(f).forEach(v=>{
    if(Array.isArray(v))v.forEach(filmGemeldetAnwenden);
    else if(v&&typeof v==='object')Object.values(v).forEach(a=>Array.isArray(a)&&a.forEach(filmGemeldetAnwenden));});
  if(Array.isArray(f.weiterschauen))f.weiterschauen=f.weiterschauen.filter(e=>!(e&&e.gesehen));
  return f;
}
/* Alle lokalen Kopien an EINER Stelle: Folgenliste der Info + Zwischenspeicher,
   Film-Info, Hero, alle Reihen — dann neu zeichnen. Die Merk-Tabelle gilt auch
   für Daten, die später frisch vom Server kommen (tvInfo): der Katalog-Spiegel
   zieht erst nach, wenn Jellyfin die Meldung angenommen hat, und Esc öffnet
   die Info sofort. */
function filmLokalNachziehen(id,pos,gesehen){
  const alt=filmGemeldet[id];
  filmGemeldet[id]={position_s:pos, gesehen:!!(gesehen||(alt&&alt.gesehen))};
  tvpFolgePosMerken(id,pos,gesehen);
  if(tvInfoDaten)filmGemeldetAnwenden(tvInfoDaten.d);
  if(typeof tvHeroDaten!=='undefined')filmGemeldetAnwenden(tvHeroDaten);
  filmReihenAnwenden(tvFilmReihen);
  if(tvInfoOffen)tvInfoMalen();
  // Reihen und Hero neu, aber OHNE die Fokus-Vorschau (Prüfung Runde 2): sonst
  // öffnete das Ende auf der Fokus-Kachel die Hover-Karte mit stummem
  // Endlos-Clip — auch mit Sleep. Die Karte kommt erst, wenn der Besitzer den Fokus bewegt.
  else if(!tvpOffen){const tv=document.getElementById('tv'); if(tv&&tv.style.display!=='none')tvMalen({vorschau:false});}
}
/* Was kommt nach einem Filmende? Heute: nichts — keine nächste Folge, keine
   Musik (eine Automatik „nächste Folge" ist nicht bestätigt). Der Besitzer 24.09.2026 zum
   Sleep-Timer: „nein, nur musik, aber wenn der film zu ende ist, keinen
   weiteren starten" — ist der Timer aktiv oder abgelaufen, bleibt es dabei,
   auch für jede künftige Automatik: die fragt hier (Wächter:
   tests/test_film_ende.py). */
function nachFilmEnde(){
  return sleepHaeltAn()?{art:'schlaf'}:{art:'nichts'};
}
/* Film beenden (05.08.: „auch beendet werden können mit escape") — meldet
   den Spot an Jellyfin UND lokal, damit „Weiterschauen ab …" SOFORT stimmt,
   ohne auf den nächsten Katalog-Abzug zu warten. */
function filmLaeuft(){return !!tvpOffen||(vlcSpielt&&/^(film|live):/.test(vlcKeyLetzter||''));}
async function filmStopp(){
  // Esc überholt einen noch ladenden Folgenwechsel — NUR hier: Folgenende und
  // Selbstheilung der alten Folge dürfen den ausdrücklichen Druck nicht schlucken.
  tvpWechselGen++; tvpWechsel=null; tvpModusNaechster=null;
  // Bei offenem Player zählt die offene Folge (tvpIdAkt), nicht der zuletzt
  // gesehene VLC-Schlüssel: mit Gerät VLC schrieb der Geräte-Takt dort den
  // Musik-Schlüssel dazwischen (Gegenprüfung 24.09.: Stelle unter falscher Id).
  const live=tvpOffen?!tvpIdAkt:(vlcKeyLetzter||'').startsWith('live:');
  if(live){                                            // 📡 Live: nur stoppen
    vlcBefehl('stop');
    if(typeof tvpZu==='function')tvpZu();
    const tvL=document.getElementById('tv');
    if(tvL&&tvL.style.display!=='none'&&!document.fullscreenElement){
      try{tvL.requestFullscreen&&tvL.requestFullscreen().catch(()=>{});}catch(e){}
    }
    toast('📡 Live beendet.');
    return;
  }
  const offen=tvpOffen, id=offen?tvpIdAkt:(vlcKeyLetzter||'').slice(5); if(!id)return;
  let pos=Math.round((offen?tvpPos:vlcPosGeschaetzt())||0);
  // Bei einer Folge führt ← zur Info der SERIE (die Folgen-Info hat keine
  // Staffeln). Die Meta zählt nur, wenn sie zu dieser Kennung gehört — ohne
  // offenen Player ist sie sonst vom vorigen Film übrig.
  const meta=(tvpIdAkt===id&&tvpMeta)||{};
  const infoId=(meta.typ==='folge'&&meta.serie_id)||id;
  let dauer=tvpMeldeDauer(id);                         // VOR tvpZu: danach ist der Player zu
  if(!offen){
    // Ohne offene Fernbedienung (Seite neu geladen, der VLC spielt weiter) kennt
    // die Seite weder Dauer noch Sehzeit (Nacharbeit Runde 3: vorher ging die
    // Stelle ungekappt hinaus, über 90 % hakte Jellyfin selbst). Schlüssel,
    // Stelle und Dauer sagt der VLC selbst — vor dem Stopp; gehört sein Status
    // einem anderen Titel, bleibt die Dauer unbekannt und es geht nichts hinaus.
    let st=null; try{st=await vlcBefehl('status');}catch(e){}
    dauer=0;
    if(st&&st.key==='film:'+id){dauer=st.dauer||0; if(st.pos>0)pos=Math.round(st.pos);}
  }
  tvpBefehl('stop'); vlcKeyLetzter=''; vlcSpielt=false;
  if(typeof tvpZu==='function')tvpZu();               // Fernbedienung mit abräumen
  // Melden NACH tvpZu: das merkt die Stelle in der Folgenliste, die Meldestelle
  // schreibt „gesehen" samt Stelle 0 darüber und zeichnet die offene Info neu
  // (die Info zeigt bei Folgen die Serie — Nebenbefund 24.09.). Ohne
  // Fernbedienung nie „gesehen" (keine Sehzeit dieser Wiedergabe), nur die Grenze.
  const m=offen?filmFortschrittMelden(id,pos,dauer):filmFortschrittMelden(id,pos,dauer,false,null);
  // Zurück ins TV-Vollbild, wenn der Fernsehmodus offen ist (die Esc-Taste
  // ist die nötige Nutzer-Geste).
  const tv=document.getElementById('tv');
  if(tv&&tv.style.display!=='none'&&!document.fullscreenElement){
    try{tv.requestFullscreen&&tv.requestFullscreen().catch(()=>{});}catch(e){}
  }
  // Die gemeldete Stelle, nicht die Sprung-Stelle (Mindest-Sehzeit).
  toast(m.gesehen?'🎬 Film beendet — als gesehen markiert.'
       :m.stelle===null?'🎬 Film beendet.'
       :(m.zuKurz?'🎬 Film beendet — zu wenig geschaut für „gesehen“, gemerkt bei '
                 :'🎬 Film beendet — gemerkt bei ')+zeit(m.stelle)+'.');
  // ← bringt IMMER zur Detailansicht zurück (der Besitzer) — auch wenn sie zu war.
  if(!tvInfoOffen&&id)tvInfo(infoId);
}
document.addEventListener('keydown',ev=>{
  // Esc beendet den laufenden Film — überall, außer ein Menü/Panel liegt oben
  // (die schließen sich selbst zuerst; das TV regelt seine Ebenen in tvKey).
  if(ev.key!=='Escape'||!filmLaeuft())return;
  const tv=document.getElementById('tv');
  if(tv&&tv.style.display!=='none')return;             // tvKey ist zuständig
  if(document.querySelector('.itemmenu,.panelmenu'))return;
  ev.preventDefault(); filmStopp();
});
async function filmeSync(){
  try{await api('/api/filme/sync');
    toast('🎬 Katalog-Abzug gestartet — dauert bei großen Bibliotheken etwas.');
    setTimeout(filmeLaden, 8000);
  }catch(e){toast('🎬 Abzug nicht erreichbar.');}
}

