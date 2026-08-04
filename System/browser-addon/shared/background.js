// Hintergrund-Skript: Kontextmenü + Nachrichten vom Hover-Knopf -> POST an die App.
// Der fetch läuft bewusst HIER (privilegierter Erweiterungs-Kontext mit host_permissions),
// nicht im Content-Skript — so gibt es keine CORS-Probleme mit der YouTube-Seite.
const api = (typeof browser !== "undefined") ? browser : chrome;
const APP = "http://127.0.0.1:8776/api/add";
const APP_STATUS = "http://127.0.0.1:8776/api/status";

// App-läuft-Ping mit Cache (JB 22.07.): das Content-Skript fragt vor dem
// Einblenden des Hover-Knopfs — läuft der Downloader nicht, gibt es keinen Knopf.
let appOk = false, appOkTs = 0;
async function appLebt() {
  const now = Date.now();
  if (now - appOkTs < 20000) return appOk;         // 20-s-Cache, kein Dauerfeuer
  appOkTs = now;
  try {
    const r = await fetch(APP_STATUS, { method: "GET" });
    appOk = !!r.ok;
  } catch (e) { appOk = false; }
  return appOk;
}

const QUALITAETEN = [
  ["default", "Standard-Qualität"],
  ["beste", "Beste verfügbare"],
  ["2160p", "4K (2160p)"],
  ["1080p", "1080p"],
  ["720p", "720p"],
  ["audio", "Nur Audio (MP3)"],
];

function menusBauen() {
  api.contextMenus.removeAll(() => {
    api.contextMenus.create({
      id: "ytdl-parent", title: "Zur Download-Warteschlange",
      contexts: ["link", "video", "page"],
      documentUrlPatterns: ["*://*.youtube.com/*"],
    });
    for (const [q, label] of QUALITAETEN) {
      api.contextMenus.create({
        id: "ytdl:" + q, parentId: "ytdl-parent", title: label,
        contexts: ["link", "video", "page"],
        documentUrlPatterns: ["*://*.youtube.com/*"],
      });
    }
  });
}
api.runtime.onInstalled.addListener(menusBauen);
menusBauen();

function istYoutube(u) {
  return !!u && /(?:youtube\.com\/(?:watch\?|shorts\/)|youtu\.be\/)/.test(u);
}

api.contextMenus.onClicked.addListener((info) => {
  if (typeof info.menuItemId !== "string" || !info.menuItemId.startsWith("ytdl:")) return;
  const q = info.menuItemId.slice(5);
  const url = [info.linkUrl, info.srcUrl, info.pageUrl].find(istYoutube);
  if (url) senden(url, q === "default" ? null : q);
});

// Schon-geladen-Abfrage mit Cache (v1.0.6, JB: Knopf wird gruen, wenn das
// Video bereits in der Bibliothek liegt). 60-s-Cache je Video-Id; nach einem
// erfolgreichen "add" wird die Id sofort als vorhanden gemerkt.
const habCache = new Map();
async function habVideo(id) {
  if (!id) return false;
  const c = habCache.get(id);
  if (c && Date.now() - c.ts < 60000) return c.da;
  let da = false;
  try {
    const r = await fetch("http://127.0.0.1:8776/api/addon_hab?id=" + encodeURIComponent(id));
    da = !!(r.ok && (await r.json()).da);
  } catch (e) { da = false; }
  habCache.set(id, { da, ts: Date.now() });
  return da;
}

// v1.1.2: dasselbe fuer ganze Listen — „schon komplett eingereiht?".
const listenCache = new Map();
async function habListe(id) {
  if (!id) return false;
  const c = listenCache.get(id);
  if (c && Date.now() - c.ts < 60000) return c.da;
  let da = false;
  try {
    const r = await fetch("http://127.0.0.1:8776/api/addon_hab_liste?id=" + encodeURIComponent(id));
    da = !!(r.ok && (await r.json()).da);
  } catch (e) { da = false; }
  listenCache.set(id, { da, ts: Date.now() });
  return da;
}

api.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.typ === "ping") {
    appLebt().then((ok) => sendResponse({ ok }));
    return true;                                   // Antwort kommt asynchron
  }
  if (msg && msg.typ === "hab") {
    habVideo(msg.id).then((da) => sendResponse({ da }));
    return true;
  }
  if (msg && msg.typ === "hab_liste") {
    // v1.1.2: wurde diese Playlist schon komplett eingereiht? (60-s-Cache)
    habListe(msg.id).then((da) => sendResponse({ da }));
    return true;
  }
  if (msg && msg.typ === "add_liste") {
    // Review-Finding 1/5: Mixe kommen als watch?v=…&list=RD… (die
    // playlist?list=RD…-Form ist bei YouTube „unviewable") — beide Formen
    // zulassen; und bei einer fremden URL EHRLICH antworten statt den
    // Dialog ohne Antwort haengen zu lassen.
    if (!/youtube\.com\/(?:playlist\?list=|watch\?\S*[?&]list=)/.test(msg.url || "")) {
      sendResponse({ ok: false, fehler: "keine Playlist-Adresse" });
      return true;
    }
    // v1.1.1 (JB): ganze Playlist/Mix — von/bis reisen bis zur App
    // (/api/add versteht sie seit v1.1.1 als playliststart/playlistend).
    const body = { urls: msg.url, ganze_liste: true };
    if (msg.von) body.von = msg.von;
    if (msg.bis) { body.bis = msg.bis; body.limit = msg.bis; }
    if (msg.qualitaet) body.qualitaet = msg.qualitaet;
    fetch(APP, { method: "POST", body: JSON.stringify(body) })
      .then((r) => { if (!r.ok) throw new Error("HTTP " + r.status);
        appOk = true; appOkTs = Date.now();
        // v1.1.2: KOMPLETT eingereiht (ohne von/bis) -> sofort als „hab" merken.
        if (!body.von && !body.bis) {
          const lm = (msg.url || "").match(/[?&]list=([\w-]+)/);
          if (lm) listenCache.set(lm[1], { da: true, ts: Date.now() });
        }
        melden("Playlist in die Warteschlange ✓", "", false);
        sendResponse({ ok: true }); })
      .catch((e) => { appOk = false; appOkTs = Date.now();
        sendResponse({ ok: false, fehler: String((e && e.message) || e) }); });
    return true;
  }
  if (msg && msg.typ === "add" && istYoutube(msg.url)) {
    senden(msg.url, msg.qualitaet || null).then((res) => {
      if (res && res.ok && msg.url) {
        const m = msg.url.match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{6,})/);
        if (m) habCache.set(m[1], { da: true, ts: Date.now() });
      }
      sendResponse(res);
    });
    return true;                                   // Antwort kommt asynchron -> Knopf zeigt ✓/✗
  }
});

async function senden(url, qualitaet) {
  const body = { urls: url };
  if (qualitaet) body.qualitaet = qualitaet;
  try {
    // BEWUSST ohne Content-Type-Header: so ist es ein "einfacher" Request ohne
    // CORS-Preflight — funktioniert auch dann, wenn Firefox die Host-Erlaubnis
    // (MV3 = opt-in!) nicht erteilt hat. Der Server parst den Body ohnehin als JSON.
    const r = await fetch(APP, { method: "POST", body: JSON.stringify(body) });
    if (!r.ok) throw new Error("HTTP " + r.status);
    appOk = true; appOkTs = Date.now();                    // Erfolg zählt als frischer Ping
    melden("In die Warteschlange ✓", kurz(url), false);   // Erfolg: nur wenn eingeschaltet
    return { ok: true };
  } catch (e) {
    const grund = String((e && e.message) || e);
    appOk = false; appOkTs = Date.now();                   // App offenbar aus -> Knopf verschwindet
    melden("Fehlgeschlagen: " + grund, "Läuft die App? (YouTube-Downloader.bat)", true);
    return { ok: false, fehler: grund };
  }
}

function kurz(u) {
  const m = u.match(/[?&]v=([\w-]+)/) || u.match(/shorts\/([\w-]+)/) || u.match(/youtu\.be\/([\w-]+)/);
  return m ? "Video " + m[1] : u;
}

async function melden(titel, text, istFehler) {
  // v1.0.7 (JB: „bitte unterbinden"): ALLE Firefox-Meldungen haengen am
  // Popup-Schalter (ytdl_notify, Standard AUS) — auch Fehler; der Knopf
  // selbst zeigt ✓/✗ direkt am Video, die System-Meldung war doppelt.
  void istFehler;
  try {
    const o = await api.storage.local.get("ytdl_notify");
    if (!(o && o.ytdl_notify)) return;
  } catch (e) { return; }
  try {
    // icon128.png — das alte icon.svg existiert im Build nicht mehr; ein kaputtes
    // Icon ließ die Meldung in Firefox STILL scheitern (Fehler blieben unsichtbar).
    api.notifications.create({
      type: "basic",
      iconUrl: api.runtime.getURL("icons/icon128.png"),
      title: "YouTube-Downloader",
      message: titel + (text ? " — " + text : ""),
    });
  } catch (e) { /* Benachrichtigungen optional */ }
}
