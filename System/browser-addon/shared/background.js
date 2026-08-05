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

// ---- Offline-Merkliste (v1.2.0, JB 05.08.) --------------------------------
// Klicks ohne laufende App gehen NICHT verloren: sie landen persistent in
// storage.local (übersteht Firefox-Neustarts) und werden eingereiht, sobald
// App UND Browser gleichzeitig laufen. Der Minuten-Wecker (alarms) weckt auch
// die schlafende Event-Page/den Service-Worker.
async function merkLesen() {
  try { const o = await api.storage.local.get("ytdl_merk"); return (o && o.ytdl_merk) || {}; }
  catch (e) { return {}; }
}
async function merkSchreiben(liste) {
  try { await api.storage.local.set({ ytdl_merk: liste }); } catch (e) { /* voll/aus */ }
}
function merkKey(eintrag) {
  // Review v1.2.0 (3 Funde, ein Kern): der Listen-Schlüssel darf das
  // Startvideo NICHT enthalten — bei Mixen wechselt v= laufend, dann zeigte
  // die Anzeige (Präfix) gelb, aber das Entfernen (exakter Schlüssel aus der
  // AKTUELLEN URL) löschte ins Leere. Die Einreih-URL (watch-Form!) bleibt
  // im EINTRAG gespeichert; ein Mix = eine Vormerkung, die letzte gewinnt.
  if (eintrag.art === "liste") {
    return "liste:" + ((eintrag.url || "").match(/[?&]list=([\w-]+)/) || [, ""])[1];
  }
  // Video: Id + Qualität — sonst überschreibt „Nur Audio" per Rechtsklick
  // stumm die vorgemerkte Standard-Qualität (Review-Fund 10).
  const m = (eintrag.url || "").match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{6,})/);
  return (m ? m[1] : (eintrag.url || "")) + "|" + (eintrag.qualitaet || "std");
}
// Review-Fund 7: merken/unmerken sind Lesen-Ändern-Schreiben auf DEMSELBEN
// storage-Objekt — zwei Klicks in zwei Tabs verschränkten sich an den
// await-Lücken und der zweite Schreiber verschluckte den ersten. Eine
// Promise-Kette serialisiert alle Änderungen.
let merkSperre = Promise.resolve();
function merkAendern(fn) {
  const p = merkSperre.then(async () => {
    const liste = await merkLesen();
    fn(liste);
    await merkSchreiben(liste);
  });
  merkSperre = p.catch(() => {});
  return p;
}
function merken(eintrag) {
  return merkAendern((liste) => {
    liste[merkKey(eintrag)] = Object.assign({ ts: Date.now() }, eintrag);
  });
}
function unmerken(msg) {
  // Video: ALLE Qualitäten dieser Id entfernen (ein Klick = weg);
  // Liste: der eine Listen-Schlüssel.
  return merkAendern((liste) => {
    if (msg.art === "liste") { delete liste[merkKey(msg)]; return; }
    const m = (msg.url || "").match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{6,})/);
    const id = m ? m[1] : (msg.url || "");
    for (const k of Object.keys(liste)) {
      if (k.indexOf(id + "|") === 0) delete liste[k];
    }
  });
}
async function gemerktVideo(id) {
  const l = await merkLesen();
  return Object.keys(l).some((k) => k.indexOf(id + "|") === 0);
}
async function gemerktListe(lid) {
  const l = await merkLesen();
  return !!l["liste:" + lid];
}

let flushLaeuft = false;
async function merkFlush() {
  // Review-Fund 6: das Flag muss VOR den awaits stehen — sonst lesen Alarm
  // und Ping im selben Fenster denselben Stand und reihen alles doppelt ein.
  if (flushLaeuft) return;
  flushLaeuft = true;
  let ok = 0;
  try {
    const liste = await merkLesen();
    const keys = Object.keys(liste);
    if (!keys.length) return;
    if (!(await appLebt())) return;
    for (const k of keys.sort((a, b) => (liste[a].ts || 0) - (liste[b].ts || 0))) {
      const e = liste[k];
      const body = { urls: e.url };
      if (e.art === "liste") {
        body.ganze_liste = true;
        if (e.von) body.von = e.von;
        if (e.bis) { body.bis = e.bis; body.limit = e.bis; }
      }
      if (e.qualitaet) body.qualitaet = e.qualitaet;
      try {
        const r = await fetch(APP, { method: "POST", body: JSON.stringify(body) });
        if (!r.ok) continue;                       // App-Fehler: Eintrag bleibt für später
        ok += 1;
        await merkAendern((l) => { delete l[k]; });   // genau DIESEN Schlüssel abhaken
        if (e.art !== "liste") {
          const id = k.split("|")[0];              // Schlüssel = "<id>|<qualitaet>"
          if (id.length >= 6) habCache.set(id, { da: true, ts: Date.now() });
        }
      } catch (err) { break; }                     // App wieder weg -> Rest wartet weiter
    }
    if (ok) {
      // Die App zeigt die Info selbst („x vorgemerkte Downloads werden geholt").
      try {
        await fetch("http://127.0.0.1:8776/api/addon_nachschub",
                    { method: "POST", body: JSON.stringify({ n: ok }) });
      } catch (e) { /* Info ist Kür, das Einreihen war die Pflicht */ }
      melden("⬇ " + ok + " vorgemerkte Downloads eingereiht", "", false);
    }
  } finally { flushLaeuft = false; }
}
try {
  api.alarms.create("ytdl-merk", { periodInMinutes: 1 });
  api.alarms.onAlarm.addListener((a) => { if (a && a.name === "ytdl-merk") merkFlush(); });
} catch (e) { setInterval(merkFlush, 60000); }      // Rückfall, falls alarms fehlt

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
  // Review-Fund 11: der Kontextmenü-Weg hat keinen Knopf, der gelb werden
  // könnte — beim Vormerken MUSS die System-Meldung kommen (sichtbar=true).
  if (url) senden(url, q === "default" ? null : q, true);
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
    appLebt().then((ok) => { if (ok) merkFlush(); sendResponse({ ok }); });
    return true;                                   // Antwort kommt asynchron
  }
  if (msg && msg.typ === "hab") {
    // v1.2.0: gemerkt reist mit — der Knopf zeigt Vorgemerktes gelb mit „…".
    Promise.all([habVideo(msg.id), gemerktVideo(msg.id)])
      .then(([da, gemerkt]) => sendResponse({ da, gemerkt }));
    return true;
  }
  if (msg && msg.typ === "hab_liste") {
    // v1.1.2: wurde diese Playlist schon komplett eingereiht? (60-s-Cache)
    Promise.all([habListe(msg.id), gemerktListe(msg.id)])
      .then(([da, gemerkt]) => sendResponse({ da, gemerkt }));
    return true;
  }
  if (msg && msg.typ === "unmerken") {
    // v1.2.0 (JB): Klick auf das gelbe „…" nimmt die Vormerkung zurück
    // (Video: alle Qualitäten der Id; Liste: über die list-Id, v=-fest).
    unmerken({ art: msg.art, url: msg.url }).then(() => sendResponse({ ok: true }));
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
      .then((r) => { if (!r.ok) { const err = new Error("HTTP " + r.status); err.http = true; throw err; }
        appOk = true; appOkTs = Date.now();
        // v1.1.2: KOMPLETT eingereiht (ohne von/bis) -> sofort als „hab" merken.
        if (!body.von && !body.bis) {
          const lm = (msg.url || "").match(/[?&]list=([\w-]+)/);
          if (lm) listenCache.set(lm[1], { da: true, ts: Date.now() });
        }
        melden("Playlist in die Warteschlange ✓", "", false);
        merkFlush();                                   // App lebt -> Rückstau mitnehmen
        sendResponse({ ok: true }); })
      .catch(async (e) => { appOk = false; appOkTs = Date.now();
        if (!e.http) {
          // v1.2.0 (JB): App aus -> Liste samt von/bis persistent vormerken.
          await merken({ art: "liste", url: msg.url, von: msg.von || null,
                         bis: msg.bis || null, qualitaet: msg.qualitaet || null });
          melden("Playlist vorgemerkt — lädt beim nächsten App-Start", "", false);
          sendResponse({ ok: true, gemerkt: true });
          return;
        }
        sendResponse({ ok: false, fehler: String((e && e.message) || e) }); });
    return true;
  }
  if (msg && msg.typ === "add" && istYoutube(msg.url)) {
    senden(msg.url, msg.qualitaet || null).then((res) => {
      // v1.2.0: NUR echtes Einreihen zählt als „hab" — Vorgemerktes bleibt „…".
      if (res && res.ok && !res.gemerkt && msg.url) {
        const m = msg.url.match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{6,})/);
        if (m) habCache.set(m[1], { da: true, ts: Date.now() });
      }
      sendResponse(res);
    });
    return true;                                   // Antwort kommt asynchron -> Knopf zeigt ✓/✗
  }
});

async function senden(url, qualitaet, sichtbarMelden) {
  const body = { urls: url };
  if (qualitaet) body.qualitaet = qualitaet;
  try {
    // BEWUSST ohne Content-Type-Header: so ist es ein "einfacher" Request ohne
    // CORS-Preflight — funktioniert auch dann, wenn Firefox die Host-Erlaubnis
    // (MV3 = opt-in!) nicht erteilt hat. Der Server parst den Body ohnehin als JSON.
    const r = await fetch(APP, { method: "POST", body: JSON.stringify(body) });
    if (!r.ok) { const err = new Error("HTTP " + r.status); err.http = true; throw err; }
    appOk = true; appOkTs = Date.now();                    // Erfolg zählt als frischer Ping
    melden("In die Warteschlange ✓", kurz(url), false);   // Erfolg: nur wenn eingeschaltet
    merkFlush();                                          // App lebt -> evtl. Rückstau mitnehmen
    return { ok: true };
  } catch (e) {
    const grund = String((e && e.message) || e);
    appOk = false; appOkTs = Date.now();
    if (!e.http) {
      // v1.2.0 (JB): App aus -> der Klick geht NICHT verloren, sondern wird
      // persistent vorgemerkt und beim nächsten App-Start eingereiht.
      await merken({ art: "video", url, qualitaet: qualitaet || null });
      melden("Vorgemerkt — lädt beim nächsten App-Start", kurz(url), false, !!sichtbarMelden);
      return { ok: true, gemerkt: true };
    }
    // App LÄUFT, lehnte aber ab (HTTP-Fehler): ehrlich melden, nicht horten.
    melden("Fehlgeschlagen: " + grund, "Läuft die App? (YouTube-Downloader.bat)", true);
    return { ok: false, fehler: grund };
  }
}

function kurz(u) {
  const m = u.match(/[?&]v=([\w-]+)/) || u.match(/shorts\/([\w-]+)/) || u.match(/youtu\.be\/([\w-]+)/);
  return m ? "Video " + m[1] : u;
}

async function melden(titel, text, istFehler, erzwingen) {
  // v1.0.7 (JB: „bitte unterbinden"): ALLE Firefox-Meldungen haengen am
  // Popup-Schalter (ytdl_notify, Standard AUS) — auch Fehler; der Knopf
  // selbst zeigt ✓/✗ direkt am Video, die System-Meldung war doppelt.
  // v1.2.0 (Review-Fund 11): erzwingen=true übergeht den Schalter — für den
  // Kontextmenü-Weg, der KEINE andere Rückmeldung hat (sonst passiert
  // sichtbar NICHTS, obwohl vorgemerkt wurde).
  void istFehler;
  if (!erzwingen) {
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
