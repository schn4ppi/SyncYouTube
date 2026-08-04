// Content-Skript auf youtube.com: kleiner, unscheinbarer Download-Knopf, der beim
// Überfahren eines Videos/Vorschaubilds erscheint und bei Mausstillstand wieder
// verschwindet. Klick schickt die URL (via Hintergrund-Skript) an die App.
(function () {
  const api = (typeof browser !== "undefined") ? browser : chrome;
  let btn = null, curUrl = null, curListe = null, hideTimer = null, lastMove = 0;
  // v1.1.1 (JB: „kommt ganz kurz das download symbol, ein paar frames"):
  // zeigen() setzte bei JEDER Mausbewegung erst ⬇ und wartete auf die
  // Hab-Antwort aus dem Hintergrund — der Haken flackerte. Dieser lokale
  // Speicher (Video-Id -> schon da?) setzt den Zustand SOFORT; die Antwort
  // frischt ihn nur noch auf.
  const habLokal = new Map();

  // Hover-Knopf abschaltbar (JB v1.0.5, Popup-Schalter; Standard AN) —
  // wirkt sofort über storage.onChanged, das Rechtsklick-Menü bleibt immer.
  let hoverAn = true;
  try {
    api.storage.local.get("ytdl_hover").then((o) => { hoverAn = !(o && o.ytdl_hover === false); }, () => {});
    api.storage.onChanged.addListener((aend, bereich) => {
      if (bereich === "local" && aend.ytdl_hover) {
        hoverAn = aend.ytdl_hover.newValue !== false;
        if (!hoverAn) verstecken();
      }
    });
  } catch (e) { /* Storage nicht verfügbar -> Knopf bleibt an */ }

  // App-läuft-Wächter (JB 22.07.): der Knopf erscheint NUR, wenn der Downloader
  // wirklich läuft — vorher tauchte er immer auf und der Klick lief ins Leere.
  // Der Ping läuft im Hintergrund-Skript (Cache dort), hier nur das Ergebnis.
  let appAn = false, appTs = 0;
  function appPruefen() {
    const now = Date.now();
    if (now - appTs < 30000) return;                 // höchstens alle 30 s fragen
    appTs = now;
    try {
      api.runtime.sendMessage({ typ: "ping" }).then(
        (res) => { appAn = !!(res && res.ok); },
        () => { appAn = false; });
    } catch (e) { appAn = false; }
  }

  function mkBtn() {
    btn = document.createElement("button");
    btn.className = "ytdl-hoverbtn";
    btn.type = "button";
    btn.title = "Zur Download-Warteschlange hinzufügen";
    btn.textContent = "⬇";
    // Klicks abfangen, damit YouTube sie nicht als Video-Klick wertet
    btn.addEventListener("mousedown", (e) => { e.stopPropagation(); e.preventDefault(); }, true);
    btn.addEventListener("click", onClick, true);
    document.body.appendChild(btn);
  }

  function onClick(e) {
    e.stopPropagation(); e.preventDefault();
    // v1.1.1 (JB): Klick auf den LISTEN-Pfeil oeffnet den Von-bis-Dialog —
    // kein window.prompt (waere von derselben Firefox-Sperre betroffen wie
    // confirm beim Ausschnitt-Loeschen).
    if (curListe) { listeDialog(curListe); return; }
    if (!curUrl) return;
    // v1.0.7 (JB): schon in der Bibliothek -> Klick laedt NICHT doppelt;
    // anderes Format geht per Rechtsklick. v1.1.0 (JB): der Klick zeigt ROT
    // mit ✗ („hast du schon") und kehrt zum gruenen Haken zurueck.
    if (btn.classList.contains("hab")) {
      btn.classList.add("nein");
      btn.textContent = "✗";
      setTimeout(() => { btn.classList.remove("nein"); btn.textContent = "✓"; }, 600);
      return;
    }
    const url = curUrl;
    btn.textContent = "…";                             // ehrlich: erst nach Antwort ✓ oder ✗
    const fertig = (res) => {
      const ok = !!(res && res.ok);
      if (ok) {                                        // v1.1.1: sofort als „hab" merken
        const mv = url.match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{6,})/);
        if (mv) habLokal.set(mv[1], true);
      }
      btn.classList.add(ok ? "ok" : "fehl");
      btn.textContent = ok ? "✓" : "✗";
      btn.title = ok ? "In der Warteschlange"
                     : "Fehler: " + ((res && res.fehler) || "keine Antwort — läuft die App?");
      setTimeout(() => { btn.classList.remove("ok", "fehl"); btn.textContent = "⬇";
                         btn.title = "Zur Download-Warteschlange hinzufügen"; }, 1800);
    };
    api.storage.local.get("ytdl_quali").then((o) => {
      const q = o && o.ytdl_quali;
      return api.runtime.sendMessage({ typ: "add", url, qualitaet: (q && q !== "default") ? q : null });
    }, () => api.runtime.sendMessage({ typ: "add", url }))
      .then(fertig, () => fertig(null));
  }

  function videoAnker(el) {
    if (!el || !el.closest) return null;
    const a = el.closest('a#thumbnail, a.ytd-thumbnail, a[href*="/watch?v="], a[href*="/shorts/"]');
    if (!(a && a.href && (a.href.includes("/watch?v=") || a.href.includes("/shorts/")))) return null;
    // NUR echte Vorschaubilder (JB 22.07.): Titel-Links matchten auch — dann saß
    // der Knopf am Zeilenende genau ÜBER YouTubes ⋮-Menü („Video ausblenden").
    if (!a.querySelector("img, yt-image")) return null;
    return a;
  }

  // v1.0.9 (JB-Fund: „bei einem beendeten Video ganz oben links, nicht mehr
  // im Video"). getBoundingClientRect() liefert für ein Element OHNE Maße
  // lauter Nullen — das passiert, sobald YouTube am Ende eines Videos den
  // Abspann einblendet, den Player umbaut oder das <video> kurz ausblendet.
  // Vorher rechnete zeigen() blind weiter und Math.max(4, 0+6) parkte den
  // Knopf in der linken oberen Bildschirmecke: sichtbar, aber ohne Bezug.
  // Ein Knopf ohne brauchbaren Anker gehört WEG, nicht an den Rand geklemmt.
  function ankerBrauchbar(r) {
    if (!r || r.width < 40 || r.height < 40) return false;      // ohne Maße/zu klein
    if (r.bottom <= 0 || r.right <= 0) return false;            // links/oben aus dem Bild
    if (r.top >= innerHeight || r.left >= innerWidth) return false;  // unten/rechts draußen
    return true;
  }

  function zeigen(rect, url) {
    if (!ankerBrauchbar(rect)) { verstecken(); return; }
    curUrl = url;
    curListe = null; btn.classList.remove("liste");    // Video-Knopf, kein Listen-Pfeil
    // Oben LINKS statt oben rechts (JB 22.07.): oben rechts liegen YouTubes
    // eigene Hover-Knöpfe (Später ansehen / ⋮) — die dürfen wir nie verdecken.
    // Geklemmt wird an den ANKER, nicht an den Bildschirm (JB-Dauerregel:
    // Höchstmaße an die Position koppeln) — so bleibt der Knopf immer IM Bild.
    const b = 30;                                    // Knopfgröße samt Rand
    const l = Math.min(rect.left + 6, rect.right - b);
    const t = Math.min(rect.top + 8, rect.bottom - b);
    btn.style.left = l + "px";
    btn.style.top = t + "px";
    btn.classList.add("an");
    // v1.1.0 (JB): schon in der Bibliothek -> GRUEN mit Haken ✓, schon BEVOR
    // man klickt. v1.1.1: der Zustand kommt SOFORT aus dem lokalen Speicher
    // (kein ⬇-Flackern mehr); die Hintergrund-Antwort frischt nur noch auf.
    const habAnwenden = (da) => {
      btn.classList.toggle("hab", !!da);
      btn.textContent = da ? "✓" : "⬇";
      btn.title = da ? "Schon in der Bibliothek — Rechtsklick lädt bewusst in anderem Format"
                     : "Zur Download-Warteschlange hinzufügen";
    };
    const m = url.match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{6,})/);
    habAnwenden(m ? habLokal.get(m[1]) : false);
    if (m && !habLokal.has(m[1])) {
      try {
        api.runtime.sendMessage({ typ: "hab", id: m[1] }).then((res) => {
          habLokal.set(m[1], !!(res && res.da));
          if (curUrl === url) habAnwenden(res && res.da);
        }, () => {});
      } catch (e) { /* Hintergrund nicht erreichbar -> Knopf bleibt neutral */ }
    }
  }
  function verstecken() { if (btn) { btn.classList.remove("an", "liste"); } curUrl = null; curListe = null; }

  // ---- Ganze Playlist laden (v1.1.1, JB: „für die ganze playlist … bzw wenn
  // es ein radio ist sollte gefragt werden wie viele") -------------------------
  function listenAnker(el) {
    if (!el || !el.closest) return null;
    // (a) Playlist-Karten/-Links überall auf YouTube.
    const a = el.closest('a[href*="playlist?list="]');
    if (a && a.querySelector("img, yt-image")) {
      const img = a.querySelector("img") || a.querySelector("yt-image");
      return { rect: img.getBoundingClientRect(), url: a.href };
    }
    // (b) Das Playlist-Panel auf der Watch-Seite: der KOPF (Titel/Mix-Zeile),
    // nicht die Video-Zeilen — die behalten ihren eigenen Knopf.
    const panel = el.closest("ytd-playlist-panel-renderer");
    if (panel && !el.closest('a[href*="/watch?v="]')) {
      const kopf = panel.querySelector(".header, h3.title, .title");
      const liste = (location.search.match(/[?&]list=([\w-]+)/) || [])[1];
      if (kopf && liste && el.closest(".header, h3.title, .title, .publisher, .index-message-wrapper")) {
        return { rect: kopf.getBoundingClientRect(),
                 url: "https://www.youtube.com/playlist?list=" + liste };
      }
    }
    return null;
  }

  function listeZeigen(anker) {
    if (!ankerBrauchbar(anker.rect)) { verstecken(); return; }
    curUrl = null;
    curListe = { url: anker.url,
                 mix: /[?&]list=RD/.test(anker.url) };  // RD… = Radio/Mix (endlos)
    const b = 30;
    btn.style.left = Math.min(anker.rect.left + 6, anker.rect.right - b) + "px";
    btn.style.top = Math.min(anker.rect.top + 8, anker.rect.bottom - b) + "px";
    btn.classList.remove("hab", "ok", "fehl");
    btn.classList.add("an", "liste");
    btn.textContent = "⬇";
    btn.title = curListe.mix ? "Diesen Mix laden — Klick fragt, wie viele"
                             : "Diese Playlist laden — Klick fragt von–bis";
  }

  function listeDialog(liste) {
    const alt = document.getElementById("ytdl-listendialog");
    if (alt) alt.remove();
    const box = document.createElement("div");
    box.id = "ytdl-listendialog";
    box.innerHTML =
      '<div class="ytdl-ld-titel">' + (liste.mix ? "🎧 Mix laden" : "📃 Playlist laden") + "</div>" +
      '<div class="ytdl-ld-zeile"><label>Von Nr.</label><input type="number" min="1" id="ytdl-ld-von" placeholder="1"></div>' +
      '<div class="ytdl-ld-zeile"><label>Bis Nr.</label><input type="number" min="1" id="ytdl-ld-bis" placeholder="' +
        (liste.mix ? "50" : "Ende") + '"></div>' +
      '<div class="ytdl-ld-hinweis">' + (liste.mix
        ? 'Ein Mix ist endlos — ohne „Bis" lade ich 50.'
        : "Beides leer = die ganze Playlist.") + "</div>" +
      '<div class="ytdl-ld-knoepfe"><button id="ytdl-ld-nein">Abbrechen</button>' +
      '<button id="ytdl-ld-ja">⬇ Laden</button></div>';
    document.body.appendChild(box);
    const br = btn.getBoundingClientRect();
    box.style.left = Math.max(8, Math.min(br.left, innerWidth - 240)) + "px";
    box.style.top = Math.min(br.bottom + 6, innerHeight - 190) + "px";
    const zu = () => box.remove();
    box.querySelector("#ytdl-ld-nein").onclick = zu;
    box.addEventListener("keydown", (ev) => { if (ev.key === "Escape") zu(); });
    box.querySelector("#ytdl-ld-ja").onclick = () => {
      const von = parseInt(box.querySelector("#ytdl-ld-von").value, 10) || null;
      let bis = parseInt(box.querySelector("#ytdl-ld-bis").value, 10) || null;
      if (liste.mix && !bis) bis = 50;                 // endlos braucht IMMER eine Grenze
      const ja = box.querySelector("#ytdl-ld-ja");
      ja.textContent = "…"; ja.disabled = true;
      api.storage.local.get("ytdl_quali").then((o) => {
        const q = o && o.ytdl_quali;
        return api.runtime.sendMessage({ typ: "add_liste", url: liste.url, von, bis,
                                         qualitaet: (q && q !== "default") ? q : null });
      }, () => api.runtime.sendMessage({ typ: "add_liste", url: liste.url, von, bis }))
        .then((res) => {
          ja.textContent = (res && res.ok) ? "✓ eingereiht" : "✗ App erreichbar?";
          setTimeout(zu, 1200);
        }, () => { ja.textContent = "✗ App erreichbar?"; setTimeout(zu, 1500); });
    };
    setTimeout(() => {
      const s = (ev) => { if (!box.contains(ev.target) && ev.target !== btn) { zu();
        document.removeEventListener("pointerdown", s, true); } };
      document.addEventListener("pointerdown", s, true);
      const v = box.querySelector("#ytdl-ld-von"); if (v) v.focus();
    }, 0);
  }

  function resetIdle() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(verstecken, 1500);   // keine Mausbewegung -> ausblenden
  }

  function onMove(e) {
    const now = Date.now();
    if (now - lastMove < 60) return;            // Drosselung
    lastMove = now;
    if (!hoverAn) { verstecken(); return; }     // Knopf im Popup abgeschaltet (JB v1.0.5)
    appPruefen();
    if (!appAn) { verstecken(); return; }       // App aus -> Knopf existiert nicht (JB 22.07.)
    if (!btn) mkBtn();
    if (e.target === btn || (btn && btn.contains(e.target))) { resetIdle(); return; }
    // Offener Von-bis-Dialog: nichts umbauen, solange JB darin tippt (v1.1.1).
    const dlg = document.getElementById("ytdl-listendialog");
    if (dlg && dlg.contains(e.target)) { resetIdle(); return; }
    // Über YouTubes eigenen Bedienelementen (⋮-Menü, Knöpfe, Dropdowns) sofort
    // weg — nie deren Klickfläche verdecken (JB 22.07., „Video ausblenden").
    if (e.target.closest && e.target.closest("button, yt-icon-button, ytd-menu-renderer, tp-yt-iron-dropdown, tp-yt-paper-listbox")) {
      verstecken(); return;
    }
    const a = videoAnker(e.target);
    if (a) {
      // v1.1.0 (JB, zwei Bilder): "wenn ich neben den track gehe erscheint ein
      // pfeil, wenn ich auf den track gehe, ist der pfeil woanders." Je nach
      // Treffer (Zeilen-Link mit Text vs. Thumbnail-Link) war der ANKER ein
      // anderes Element — der Knopf sprang. Jetzt ankert er IMMER am
      // Vorschaubild IM Link (das videoAnker garantiert), egal wo die Maus
      // in der Zeile steht.
      const img = a.querySelector("img") || a.querySelector("yt-image");
      const ir = img && img.getBoundingClientRect();
      zeigen(ankerBrauchbar(ir) ? ir : a.getBoundingClientRect(), a.href);
      resetIdle(); return;
    }
    // v1.1.1 (JB): Playlist-Karten und der Panel-Kopf bekommen den Listen-Pfeil.
    const liste = listenAnker(e.target);
    if (liste) { listeZeigen(liste); resetIdle(); return; }
    const player = e.target.closest ? e.target.closest("#movie_player, .html5-video-player") : null;
    if (player && location.href.includes("/watch")) {
      // Am echten BILD ausrichten (JB v1.0.5): der Player-Container umfasst
      // auch Letterbox/Chrome — der Knopf sass dadurch "etwas ausserhalb"
      // des sichtbaren Videos. Das <video>-Element hat die echten Bild-Masse.
      // v1.0.9: erst das echte Bild, sonst der Player — und NUR, wenn der
      // gewählte Anker auch Maße hat. Vorher genügte „Breite > 0"; ein
      // beendetes Video kann aber breit und trotzdem ohne Höhe/Position sein.
      const video = player.querySelector("video");
      const vr = video && video.getBoundingClientRect();
      const rect = ankerBrauchbar(vr) ? vr : player.getBoundingClientRect();
      zeigen(rect, location.href.split("&")[0]);
      resetIdle();
      return;
    }
    // v1.0.7 (JB): Maus hat das Video/Vorschaubild VERLASSEN -> Knopf SOFORT
    // weg (vorher blieb er bis zum 1,5-s-Ruhe-Timer stehen).
    verstecken();
  }

  document.addEventListener("mousemove", onMove, true);
  document.addEventListener("scroll", verstecken, true);
})();
