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

api.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.typ === "ping") {
    appLebt().then((ok) => sendResponse({ ok }));
    return true;                                   // Antwort kommt asynchron
  }
  if (msg && msg.typ === "add" && istYoutube(msg.url)) {
    senden(msg.url, msg.qualitaet || null).then(sendResponse);
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
  // Erfolgs-Benachrichtigungen sind standardmaessig AUS (der Hover-Knopf zeigt
  // schon ✓/✗) — sonst kaeme bei jedem Download ein Ton (Kumpel-Feedback).
  // Fehler werden immer gemeldet. Umschaltbar im Popup (ytdl_notify).
  if (!istFehler) {
    try {
      const o = await api.storage.local.get("ytdl_notify");
      if (!(o && o.ytdl_notify)) return;
    } catch (e) { return; }
  }
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
