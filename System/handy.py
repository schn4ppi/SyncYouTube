# -*- coding: utf-8 -*-
"""Schlanke Handy-Oberfläche für die Fernsteuerung (wird unter /m ausgeliefert).

Gleicher Server, gleiche APIs wie die PC-Oberfläche — nur touch-optimiert und
mit Zugangscode. Geräte-Wahl wie Spotify Connect: abspielen auf dem PC-Player
(Befehl über /api/remote) ODER auf dem Handy selbst (streamt /media)."""

HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>YTDL · Handy</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0b0f0b;color:#e7f0e7;font-family:system-ui,Segoe UI,sans-serif}
.wrap{max-width:560px;margin:0 auto;padding:12px 12px 90px}
h1{font-family:Consolas,monospace;color:#37f000;font-size:18px;letter-spacing:.06em;margin:6px 0 12px}
#login{padding:24px 8px;text-align:center}
#login input{font-size:22px;letter-spacing:.3em;text-align:center;width:180px;padding:10px;border-radius:10px;
  border:1px solid #234a23;background:#0e150e;color:#e7f0e7}
.btn{background:#122a12;border:1px solid #37f000;color:#8dff6a;border-radius:10px;padding:10px 16px;
  font-size:15px;font-weight:700;cursor:pointer}
.devrow{display:flex;gap:8px;margin:8px 0 14px}
.dev{flex:1;padding:10px;border-radius:10px;border:1px solid #234a23;background:#0e150e;color:#a9c8a9;
  text-align:center;font-size:14px;cursor:pointer}
.dev.an{border-color:#37f000;background:#122a12;color:#8dff6a;font-weight:700}
#now{background:#0e150e;border:1px solid #1c331c;border-radius:12px;padding:12px;margin-bottom:12px}
#nowtitel{font-size:15px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#e7f0e7}
#nowsub{font-size:12px;color:#7fae7f;margin-top:3px}
.ctrl{display:flex;align-items:center;justify-content:center;gap:10px;margin-top:12px}
.big{width:56px;height:56px;border-radius:50%;border:1px solid #37f000;background:#122a12;color:#8dff6a;font-size:22px}
.mid{width:46px;height:46px;border-radius:50%;border:1px solid #234a23;background:#0e150e;color:#a9c8a9;font-size:18px}
#vol{width:100%;margin-top:12px;accent-color:#37f000}
#suche{width:100%;padding:11px 12px;border-radius:10px;border:1px solid #234a23;background:#0e150e;color:#e7f0e7;
  font-size:15px;margin-bottom:8px}
.row{display:flex;align-items:center;gap:10px;padding:9px 6px;border-bottom:1px solid #142014;cursor:pointer}
.row:active{background:#0e150e}
.thumb{width:52px;height:32px;border-radius:5px;object-fit:cover;background:#142014;flex:none}
.rt{flex:1;min-width:0}
.rtt{font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rts{font-size:11px;color:#7fae7f;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hint{color:#5f7f5f;font-size:12px;text-align:center;margin-top:10px}
.fehler{color:#e08a6a}
footer{position:fixed;left:0;right:0;bottom:0;background:#0e150e;border-top:1px solid #1c331c;padding:8px 12px}
footer .ctrl{margin:0}
</style>
</head>
<body>
<div class="wrap">
  <h1>▶ YTDL · Handy</h1>

  <div id="login">
    <div style="margin-bottom:14px;color:#a9c8a9">Zugangscode eingeben<br><small style="color:#7fae7f">(steht am PC im ⚙ → Fernsteuerung)</small></div>
    <input id="code" inputmode="latin" autocapitalize="characters" maxlength="6" placeholder="––––––">
    <div style="margin-top:14px"><button class="btn" onclick="anmelden()">Verbinden</button></div>
    <div id="loginfehler" class="hint fehler"></div>
  </div>

  <div id="app" style="display:none">
    <div class="devrow">
      <div class="dev" id="dev-pc" onclick="setDev('pc')">▶ auf dem PC</div>
      <div class="dev" id="dev-handy" onclick="setDev('handy')">📱 auf dem Handy</div>
    </div>
    <div id="now">
      <div id="nowtitel">– nichts gewählt –</div>
      <div id="nowsub"></div>
      <div class="ctrl">
        <button class="mid" onclick="steuer('prev')">⏮</button>
        <button class="big" id="pp" onclick="steuer('pp')">▶</button>
        <button class="mid" onclick="steuer('next')">⏭</button>
      </div>
      <input type="range" id="vol" min="0" max="100" value="100" oninput="setVol(this.value)">
    </div>
    <input id="suche" placeholder="🔍 Bibliothek durchsuchen…" oninput="malen()">
    <div id="liste"></div>
    <div class="hint" id="tipp"></div>
  </div>

  <audio id="el" style="display:none"></audio>
</div>

<script>
let CODE=localStorage.getItem('ytdl_code')||'';
let dev=localStorage.getItem('ytdl_dev')||'pc';
let daten=[], aktuell=null;

function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML;}
async function api(pfad,opt){opt=opt||{};opt.headers=Object.assign({'X-Code':CODE},opt.headers||{});return fetch(pfad,opt);}

async function anmelden(){
  CODE=(document.getElementById('code').value||'').trim().toUpperCase();
  const r=await api('/api/status');
  if(r.status===403){document.getElementById('loginfehler').textContent='Code stimmt nicht.';return;}
  localStorage.setItem('ytdl_code',CODE);
  document.getElementById('login').style.display='none';
  document.getElementById('app').style.display='';
  setDev(dev); start();
}
function setDev(d){dev=d; localStorage.setItem('ytdl_dev',d);
  document.getElementById('dev-pc').classList.toggle('an',d==='pc');
  document.getElementById('dev-handy').classList.toggle('an',d==='handy');
  document.getElementById('vol').style.display=(d==='handy')?'':'none';
  document.getElementById('tipp').textContent=(d==='pc')?'Tippt einen Titel an → läuft am PC.':'Tippt einen Titel an → läuft hier am Handy.';
}
async function ladenBib(){const r=await api('/api/bibliothek'); const j=await r.json();
  daten=(j.items||[]).filter(x=>x.vorhanden); malen();}
function malen(){
  const q=(document.getElementById('suche').value||'').toLowerCase();
  const arr=daten.filter(x=>!q||(x.titel+' '+(x.uploader||'')).toLowerCase().includes(q)).slice(0,300);
  document.getElementById('liste').innerHTML=arr.map(x=>
    `<div class="row" onclick="spiel('${x.id}')">`+
    (x.thumb?`<img class="thumb" src="${esc(x.thumb)}" onerror="this.style.visibility='hidden'">`:'<span class="thumb"></span>')+
    `<div class="rt"><div class="rtt">${esc(x.titel)}</div><div class="rts">${esc(x.uploader||'')}</div></div></div>`).join('');
}
function libFind(id){return daten.find(x=>x.id===id);}
function spiel(id){
  aktuell=libFind(id);
  document.getElementById('nowtitel').textContent=aktuell?aktuell.titel:'';
  document.getElementById('nowsub').textContent=aktuell?(aktuell.uploader||''):'';
  if(dev==='handy'){
    const el=document.getElementById('el');
    el.src='/media?id='+encodeURIComponent(id)+'&code='+encodeURIComponent(CODE);
    el.play(); document.getElementById('pp').textContent='⏸';
  }else{
    remote('playkey',id);
  }
}
function steuer(was){
  if(dev==='handy'){
    const el=document.getElementById('el');
    if(was==='pp'){ if(el.paused){el.play();document.getElementById('pp').textContent='⏸';}else{el.pause();document.getElementById('pp').textContent='▶';} }
    // prev/next am Handy: einfache Variante – nächster/voriger in der aktuellen Liste
    else if(was==='next'||was==='prev'){ const arr=aktuelleListe(); const i=arr.indexOf(aktuell&&aktuell.id);
      const j=was==='next'?i+1:i-1; if(arr[j])spiel(arr[j]); }
  }else{
    remote(was==='pp'?'play':was);   // PC: play/pause togglet der PC-Player selbst über 'play'
  }
}
function aktuelleListe(){const q=(document.getElementById('suche').value||'').toLowerCase();
  return daten.filter(x=>!q||(x.titel+' '+(x.uploader||'')).toLowerCase().includes(q)).map(x=>x.id);}
function setVol(v){const el=document.getElementById('el'); if(el)el.volume=Math.max(0,Math.min(1,v/100));}
async function remote(cmd,key){try{await api('/api/remote',{method:'POST',
  headers:{'Content-Type':'application/json'},body:JSON.stringify({cmd,key:key||''})});}catch(e){}}

document.getElementById('el').addEventListener('ended',()=>steuer('next'));
document.getElementById('el').addEventListener('pause',()=>{document.getElementById('pp').textContent='▶';});
document.getElementById('el').addEventListener('play',()=>{document.getElementById('pp').textContent='⏸';});

function start(){ladenBib();}
// Auto-Login, wenn schon ein Code gespeichert ist (oder am PC selbst, wo kein Code nötig ist)
(async()=>{ if(CODE!==null){ const r=await api('/api/status');
  if(r.ok){document.getElementById('login').style.display='none';document.getElementById('app').style.display='';setDev(dev);start();}
  else {document.getElementById('code').value=CODE;} }})();
</script>
</body>
</html>
"""
