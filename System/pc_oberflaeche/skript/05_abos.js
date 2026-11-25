/* ================= Abos ================= */
/* ---- Abos: Kanäle/Playlists abonnieren (neue Videos werden automatisch geholt).
   Abo-Fenster nach Sonarr-Muster: Karte je Abo mit Format-Wahl, Regeln (⚙) und
   Backkatalog (📜) — fehlende Folgen ausgegraut, per Doppelklick/Auswahl nachladbar. ---- */
let aboState=[], aboOffen={}, aboLetzterKlick={};
async function aboPost(daten){
  return await api('/api/abo',daten);
}
async function aboLaden(){try{const r=await fetch('/api/abos'); aboState=(await r.json()).items||[]; aboMalen();}catch(e){}}
