/* ================= Geo/VPN-Assistent ================= */
let geoStatus=null, geoTestTimer=null;
const GEOVERGLEICH=[
  ['Gratis-Proxy (auto)','gratis','–','wechselnd','manchmal','nichts (schon an)'],
  ['Eigener Proxy','je nach Quelle','je nach Quelle','frei wählbar','ja, wenn dort','Adresse eintragen'],
  ['Windscribe Free','gratis','10 GB/Monat','viele','meist ja','Konto + App'],
  ['ProtonVPN Free','gratis','unbegrenzt','wenige','meist nein','Konto + WireGuard'],
  ['NordVPN','Abo (bezahlt)','unbegrenzt','alle','ja','App + Login'],
];
const GEOLANDER=[['GB','Großbritannien'],['US','USA'],['IE','Irland'],['CA','Kanada'],['NL','Niederlande'],
  ['DE','Deutschland'],['FR','Frankreich'],['JP','Japan'],['AU','Australien'],['CH','Schweiz'],
  ['AT','Österreich'],['PL','Polen'],['RO','Rumänien'],['SE','Schweden'],['ES','Spanien'],['IT','Italien']];

function geoWizOffen(){document.getElementById('geowiz').style.display='flex'; geoStatusLaden(true);}
function geoWizZu(){document.getElementById('geowiz').style.display='none'; clearInterval(geoTestTimer); geoTestTimer=null;}
async function geoStatusLaden(voll){
  try{
    const r=await fetch('/api/geo_status'); geoStatus=await r.json();
    const t=geoStatus.test||{};
    if(voll || !document.getElementById('geotest')) geoWizMalen();
    else { const g=document.getElementById('geotest'); if(g)g.innerHTML=geoTestHtml(t); }
    if(t.laeuft && !geoTestTimer) geoTestTimer=setInterval(()=>geoStatusLaden(false),1500);
    if(!t.laeuft && geoTestTimer){ clearInterval(geoTestTimer); geoTestTimer=null; geoWizMalen(); }
  }catch(e){}
}
function gstat(ok){return ok?'<span class="gstat ok">✓ erkannt</span>':'<span class="gstat no">nicht erkannt</span>';}
function ukfarbe(v){const c=v.indexOf('ja')===0?'ja':((v.indexOf('meist nein')===0||v==='nein')?'nein':'teils'); return `<span class="${c}">${v}</span>`;}
function gsec(titel,ok,inner){
  return `<details class="gsec"><summary><span>${titel}</span>${ok?'<span class="gstat ok">✓ eingerichtet</span>':'<span class="gstat no">offen</span>'}</summary><div class="ginner">${inner}</div></details>`;
}
function geoWgForm(){
  return `<div class="gwg"><textarea id="geowg-content" placeholder="[Interface]\nPrivateKey = …\n[Peer]\nEndpoint = …"></textarea>
    <div class="gzeile"><label style="font-size:12px;color:var(--gedaempft)">Land der Config</label>
    <select id="geowg-land">${GEOLANDER.map(([c,n])=>`<option value="${c}">${n} (${c})</option>`).join('')}</select>
    <button class="btn mini" onclick="geoWgImport()">importieren</button>
    <span id="geowg-msg" style="font-size:12px;color:#9ec49a"></span></div></div>`;
}
function geoTestHtml(t){
  t=t||{};
  if((!t.ergebnisse||!t.ergebnisse.length)&&!t.info)return '<div style="font-size:12px;color:#6a5c52;margin-top:6px">Noch nicht getestet.</div>';
  const rows=(t.ergebnisse||[]).map(e=>`<div class="gtestrow"><span>${esc(e.name)}</span><span>${e.ok===null?'… prüft':(e.ok?'<b style="color:#6fcf7f">✓ Zugang</b>':'<span style="color:#e08a6a">✗</span>')}</span></div>`).join('');
  const info=t.info?`<div style="margin-top:6px;font-size:12px;color:${/Zugang über/.test(t.info)?'#6fcf7f':'#e6c34a'}">${esc(t.info)}</div>`:'';
  return (t.titel?`<div style="font-size:11px;color:var(--gedaempft);margin-top:6px">Testvideo: ${esc(t.titel)}</div>`:'')+rows+info;
}
function geoWizMalen(){
  const s=geoStatus||{}, cfg=s.config||{}, t=s.test||{};
  const vgl=`<div class="libwrap"><table class="gcmp"><thead><tr><th>Weg</th><th>Kosten</th><th>Datenlimit</th><th>Länder</th><th>UK gratis?</th><th>Aufwand</th></tr></thead><tbody>`+
    GEOVERGLEICH.map(r=>`<tr><td><b>${r[0]}</b></td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${ukfarbe(r[4])}</td><td>${r[5]}</td></tr>`).join('')+`</tbody></table></div>`;
  const erkannt=`<div style="font-size:12px;color:var(--gedaempft);margin:4px 0 10px">Auf diesem PC erkannt: `+
    `NordVPN ${s.nordvpn?'✓':'✗'} · Windscribe ${s.windscribe?'✓':'✗'} · WireGuard-Programm ${s.wireguard_exe?'✓':'✗'}`+
    (s.aktiver_adapter?` · <b style="color:#6fcf7f">aktiv: ${esc(s.aktiver_adapter)}</b>`:'')+
    ((s.wireguard_laender||[]).length?` · WireGuard-Länder: ${s.wireguard_laender.join(', ')}`:'')+`</div>`;
  const abschnitte=[
    gsec('🟢 Gratis-Proxy (0 Aufwand — läuft automatisch)', !!cfg.geo_gratis_proxy,
      `<p>Die App holt bei einem gesperrten Video kostenlose Proxys im Zielland und probiert sie durch — nichts einzurichten.</p>
       <p>Status: ${cfg.geo_gratis_proxy?'<b style="color:#6fcf7f">aktiv</b>':'<b style="color:#e08a6a">aus</b> — im Zahnrad „Gratis-Proxys" auf ja'}. Eigene Proxys eingetragen: ${s.proxy_anzahl||0}.</p>`),
    gsec('🔵 Windscribe Free — Tipp für UK (gratis, CLI)', !!s.windscribe,
      `<ol><li><a class="glink" href="https://windscribe.com/signup" target="_blank" rel="noreferrer">windscribe.com</a> — kostenloses Konto (10 GB/Monat).</li>
       <li>Windscribe für Windows installieren, einmal anmelden.</li>
       <li>Fertig — die App erkennt <code>windscribe-cli</code> und verbindet bei Bedarf automatisch.</li></ol>
       Status: ${gstat(s.windscribe)}`),
    gsec('🟣 ProtonVPN Free — gratis & unbegrenzt (WireGuard)', (s.wireguard_laender||[]).length>0,
      `<ol><li><a class="glink" href="https://protonvpn.com/free-vpn" target="_blank" rel="noreferrer">protonvpn.com</a> — kostenloses Konto.</li>
       <li><a class="glink" href="https://www.wireguard.com/install/" target="_blank" rel="noreferrer">WireGuard für Windows</a> installieren.</li>
       <li>Im Proton-Konto → Downloads → WireGuard-Config für ein Land erzeugen; die <code>.conf</code> öffnen und den Text kopieren.</li>
       <li>Hier einfügen, Land wählen, „importieren" — die App legt sie richtig benannt ab und trägt den Ordner ein.</li></ol>
       ${geoWgForm()}
       <div style="font-size:11px;color:#6a5c52;margin-top:6px">Hinweis: WireGuard braucht beim Verbinden Windows-Adminrechte (einmalige Abfrage). UK ist im Gratis-Tarif meist nicht dabei.</div>`),
    gsec('⚫ NordVPN — falls du ein Abo hast', !!s.nordvpn,
      `<ol><li><a class="glink" href="https://nordvpn.com/download/windows" target="_blank" rel="noreferrer">NordVPN für Windows</a> installieren + anmelden.</li>
       <li>Fertig — die App steuert es per Kommandozeile.</li></ol>Status: ${gstat(s.nordvpn)}`),
    gsec('⚪ Eigener Proxy (SSH-Tunnel, Mullvad-SOCKS, …)', (s.proxy_anzahl||0)>0,
      `<p>Im Zahnrad unter „Eigene Proxys" eintragen, z.B.:</p>
       <pre style="font-size:11px;color:#cfc2b8;white-space:pre-wrap">GB=socks5://127.0.0.1:1080
socks5://5.6.7.8:1080</pre>
       <p>Funktioniert mit jeder SOCKS5/HTTP-Adresse — auch ein <code>ssh -D 1080 user@server-in-UK</code>-Tunnel. Eingetragen: ${s.proxy_anzahl||0}.</p>`),
  ].join('');
  document.getElementById('geowiz-body').innerHTML=
    `<p style="font-size:12.5px;color:#a99a90;margin:0 0 8px">Alle Wege sind gleichzeitig nutzbar — die App probiert von gratis nach aufwändig durch, bis einer Zugang gibt. Richte einen oder mehrere ein.</p>`+
    vgl+erkannt+abschnitte+
    `<div class="gsec" style="border-color:#6b4a2a" open><div class="ginner"><b>🌍 Test</b> — prüft an einem geo-gesperrten Video deiner Warteschlange, welcher Weg Zugang gibt:
       <div class="gzeile"><button class="btn" onclick="geoTestStart()" ${t.laeuft?'disabled':''}>${t.laeuft?'testet…':'Jetzt testen'}</button></div>
       <div id="geotest">${geoTestHtml(t)}</div></div></div>`;
}
async function geoWgImport(){
  const content=document.getElementById('geowg-content').value, land=document.getElementById('geowg-land').value;
  const msg=document.getElementById('geowg-msg'); msg.textContent='…';
  try{
    const d=await api('/api/geo_wireguard',{content,land});
    if(d.fehler){msg.style.color='#e08a6a';msg.textContent=d.fehler;}
    else{msg.style.color='#9ec49a';msg.textContent='importiert ✓ — Länder: '+(d.laender||[]).join(', ');}
  }catch(e){msg.style.color='#e08a6a';msg.textContent='Fehler';}
  laden();
}
async function geoTestStart(){
  try{const d=await api('/api/geo_test');
    if(d.fehler){alert(d.fehler);return;}}catch(e){}
  geoStatusLaden(true);
  if(!geoTestTimer)geoTestTimer=setInterval(()=>geoStatusLaden(false),1500);
}

