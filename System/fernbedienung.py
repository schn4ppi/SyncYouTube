# -*- coding: utf-8 -*-
"""Fake-Fernbedienung (JB-Wunsch 07.08.2026: „kann man einen fake
fernbedienungsmodus simulieren? Also ein kleines Browserfenster das wie die
fernbedienung funktioniert?").

Ein kleines Fenster mit D-Pad, das den Fernsehmodus im HAUPTFENSTER
steuert — ohne echte Fernbedienung, ohne gekoppeltes Handy. Damit lässt
sich die 10-Fuß-Bedienung am Schreibtisch prüfen (und JB kann am PC so
fernsehen, wie es später auf dem Sofa läuft).

Der Weg ist bewusst der EINFACHSTE, der trägt: ein `BroadcastChannel`
(Vanilla-JS, gleicher Ursprung, kein Server dazwischen) schickt Tastennamen;
die Oberfläche wirft sie als echte Tastatur-Ereignisse in ihre bestehende
`tvKey`-Behandlung. Es gibt also KEINEN zweiten Bedienpfad, der auseinander
laufen könnte — die Fernbedienung drückt dieselben Tasten wie ein Mensch.
Wenn `BroadcastChannel` fehlt, greift `window.opener` als Rückweg.

Ausgeliefert unter `/fernbedienung` (siehe youtube_app.py). Der Riegel
`_hat_zugriff` gilt wie für jede Route — von außen also nur mit Zugangsdaten.
"""

HTML = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fernbedienung</title>
<style>
  :root{--bg:#141414;--panel:#1f1f1f;--rand:#333;--txt:#fff;--grau:#b3b3b3;--rot:#e50914}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);font-family:system-ui,Segoe UI,sans-serif;
       display:flex;flex-direction:column;align-items:center;gap:14px;padding:16px;user-select:none}
  h1{font-size:15px;font-weight:600;color:var(--grau);margin:0;letter-spacing:.5px}
  .status{font-size:12px;color:var(--grau);min-height:16px}
  .status.an{color:#46d369}
  .dpad{display:grid;grid-template-columns:repeat(3,64px);grid-template-rows:repeat(3,64px);gap:8px}
  button{background:var(--panel);border:1px solid var(--rand);color:var(--txt);border-radius:10px;
         font-size:20px;cursor:pointer;transition:transform .06s,background .15s}
  button:hover{background:#2c2c2c}
  button:active{transform:scale(.94);background:var(--rot)}
  .ok{background:#2c2c2c;font-size:15px;font-weight:700}
  .reihe{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;max-width:220px}
  .reihe button{height:44px;min-width:64px;font-size:14px;flex:1}
  .leer{visibility:hidden}
  .hinweis{font-size:11px;color:#7a7a7a;text-align:center;max-width:230px;line-height:1.45}
</style></head><body>
<h1>FERNBEDIENUNG</h1>
<div class="status" id="status">verbinde …</div>

<div class="dpad">
  <button class="leer"></button>
  <button data-taste="ArrowUp" title="Hoch">▲</button>
  <button class="leer"></button>
  <button data-taste="ArrowLeft" title="Links">◀</button>
  <button class="ok" data-taste="Enter" title="Auswählen">OK</button>
  <button data-taste="ArrowRight" title="Rechts">▶</button>
  <button class="leer"></button>
  <button data-taste="ArrowDown" title="Runter">▼</button>
  <button class="leer"></button>
</div>

<div class="reihe">
  <button data-taste="Backspace" title="Eine Ebene zurück (beendet den Fernsehmodus NIE)">↩ Zurück</button>
  <button data-taste="Escape" title="Film beenden / Fernsehmodus schließen">✕ Aus</button>
</div>
<div class="reihe">
  <button id="pp" data-taste=" " title="Pause / Weiter">⏸</button>
  <button data-taste="s" title="Ton &amp; Untertitel">💬</button>
</div>
<div class="reihe">
  <button id="tvknopf" data-tv="1" title="Fernsehmodus an/aus">📺 TV an</button>
</div>

<!-- Maus-Feld (JB 07.08.): bei ausgeschaltetem Fernsehmodus wird die
     Fernbedienung zum Trackpad — wischen bewegt den Zeiger im
     Hauptfenster, tippen klickt. -->
<div id="mausbox" style="display:none;width:100%;max-width:230px">
  <div id="maus" style="height:150px;background:var(--panel);border:1px dashed var(--rand);
       border-radius:10px;display:flex;align-items:center;justify-content:center;
       color:var(--grau);font-size:12px;touch-action:none;cursor:crosshair">
    Wischen = Zeiger · Tippen = Klick
  </div>
  <div class="reihe" style="margin-top:8px">
    <button data-maus="links" title="Linksklick">Klick</button>
    <button data-maus="rechts" title="Rechtsklick">Rechtsklick</button>
  </div>
</div>

<p class="hinweis">Die Tasten wirken im Hauptfenster von SyncYouTube.
Dieses Fenster offen lassen und daneben legen.</p>

<script>
/* Ein Kanal, keine Sonderwege: die Fernbedienung sendet Tastennamen, das
   Hauptfenster wirft sie in seine normale Tastatur-Behandlung. */
const kanal = ('BroadcastChannel' in window) ? new BroadcastChannel('syncyoutube-fb') : null;
const status = document.getElementById('status');

function melde(text, gut){ status.textContent = text; status.classList.toggle('an', !!gut); }

function senden(nachricht){
  // GENAU EIN Weg (Fund 07.08.: beide gleichzeitig liessen jede Taste
  // DOPPELT ankommen — der Fokus sprang zwei Felder weit). Kanal zuerst,
  // das Fenster nur als Rueckweg, wenn es keinen Kanal gibt.
  let weg = false;
  if (kanal) { kanal.postMessage(nachricht); weg = true; }
  else {
    try {
      if (window.opener && !window.opener.closed) { window.opener.postMessage(nachricht, location.origin); weg = true; }
    } catch (e) { /* anderer Ursprung */ }
  }
  melde(weg ? 'verbunden' : 'kein Hauptfenster gefunden', weg);
}

document.querySelectorAll('button[data-taste]').forEach(b => {
  b.addEventListener('click', () => senden({ art: 'taste', taste: b.dataset.taste }));
});
document.querySelectorAll('button[data-tv]').forEach(b => {
  b.addEventListener('click', () => senden({ art: 'tv' }));   // EIN Knopf, schaltet um
});

/* Maus-Feld (JB: „kann ich dann die maus simulieren wie die remote maus
   app?"): Wischen bewegt den Zeiger im Hauptfenster relativ, Tippen klickt.
   Nur sichtbar, wenn der Fernsehmodus AUS ist — dort steuert das D-Pad. */
const maus = document.getElementById('maus');
let letzte = null, gewandert = 0;
maus.addEventListener('pointerdown', ev => {
  maus.setPointerCapture(ev.pointerId);
  letzte = { x: ev.clientX, y: ev.clientY }; gewandert = 0;
});
maus.addEventListener('pointermove', ev => {
  if (!letzte) return;
  const dx = ev.clientX - letzte.x, dy = ev.clientY - letzte.y;
  letzte = { x: ev.clientX, y: ev.clientY };
  gewandert += Math.abs(dx) + Math.abs(dy);
  if (dx || dy) senden({ art: 'maus', dx: dx * 2.2, dy: dy * 2.2 });   // Beschleunigung
});
maus.addEventListener('pointerup', ev => {
  if (letzte && gewandert < 6) senden({ art: 'klick', knopf: 'links' });  // Tippen = Klick
  letzte = null;
});
document.querySelectorAll('button[data-maus]').forEach(b => {
  b.addEventListener('click', () => senden({ art: 'klick', knopf: b.dataset.maus }));
});

/* Wer lieber die echte Tastatur nutzt, kann es auch hier tun. */
document.addEventListener('keydown', ev => {
  if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Escape','Backspace',' '].includes(ev.key)) {
    ev.preventDefault();
    senden({ art: 'taste', taste: ev.key });
  }
});

/* Lebenszeichen + Zustand: das Hauptfenster meldet, ob der Fernsehmodus an
   ist und ob gerade gespielt wird — danach richten sich der TV-Knopf
   (an/aus in EINER Taste) und das Pause-Symbol (JB 07.08.). */
function zustandAnzeigen(z){
  const tv = document.getElementById('tvknopf'), pp = document.getElementById('pp');
  const box = document.getElementById('mausbox');
  if (tv) { tv.textContent = z.tv ? '📺 TV aus' : '📺 TV an';
            tv.title = z.tv ? 'Fernsehmodus schliessen' : 'Fernsehmodus oeffnen'; }
  if (pp) pp.textContent = z.spielt ? '⏸' : '▶';
  if (box) box.style.display = z.tv ? 'none' : 'block';   // Maus nur ausserhalb des TV
  melde('verbunden', true);
}
if (kanal) {
  kanal.onmessage = ev => { const d = ev.data || {}; if (d.art === 'hier') zustandAnzeigen(d); };
  const fragen = () => kanal.postMessage({ art: 'hallo' });
  fragen();
  setInterval(fragen, 1000);                              // Zustand aktuell halten
  setTimeout(() => { if (!status.classList.contains('an')) melde('Hauptfenster nicht erreichbar — SyncYouTube offen?', false); }, 1200);
}
</script>
</body></html>
"""
