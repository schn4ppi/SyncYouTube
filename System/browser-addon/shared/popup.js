const api = (typeof browser !== "undefined") ? browser : chrome;
const APP = "http://127.0.0.1:8776";

const sel = document.getElementById("quali");
const status = document.getElementById("status");

// gespeicherte Qualität laden
api.storage.local.get("ytdl_quali").then((o) => {
  if (o && o.ytdl_quali) sel.value = o.ytdl_quali;
});
sel.addEventListener("change", () => {
  api.storage.local.set({ ytdl_quali: sel.value });
});

document.getElementById("oeffnen").addEventListener("click", () => {
  api.tabs.create({ url: APP });
});

// Verbindung testen
fetch(APP + "/api/status")
  .then((r) => r.json())
  .then((d) => {
    const n = (d.db && d.db.gesamt) || 0;
    status.className = "status ok";
    status.textContent = "✓ Verbunden — " + n + " Downloads insgesamt";
  })
  .catch(() => {
    status.className = "status bad";
    status.textContent = "✗ App nicht erreichbar — YouTube-Downloader.bat starten";
  });
