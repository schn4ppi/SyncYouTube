// Content-Skript auf youtube.com: kleiner, unscheinbarer Download-Knopf, der beim
// Überfahren eines Videos/Vorschaubilds erscheint und bei Mausstillstand wieder
// verschwindet. Klick schickt die URL (via Hintergrund-Skript) an die App.
(function () {
  const api = (typeof browser !== "undefined") ? browser : chrome;
  let btn = null, curUrl = null, hideTimer = null, lastMove = 0;

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
    if (!curUrl) return;
    // v1.0.7 (JB): schon in der Bibliothek -> Klick blitzt kurz ROT („hast du
    // schon") und laedt NICHT doppelt; anderes Format geht per Rechtsklick.
    if (btn.classList.contains("hab")) {
      btn.classList.add("nein");
      setTimeout(() => btn.classList.remove("nein"), 600);
      return;
    }
    const url = curUrl;
    btn.textContent = "…";                             // ehrlich: erst nach Antwort ✓ oder ✗
    const fertig = (res) => {
      const ok = !!(res && res.ok);
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

  function zeigen(rect, url) {
    curUrl = url;
    // Oben LINKS statt oben rechts (JB 22.07.): oben rechts liegen YouTubes
    // eigene Hover-Knöpfe (Später ansehen / ⋮) — die dürfen wir nie verdecken.
    btn.style.left = Math.max(4, rect.left + 6) + "px";
    btn.style.top = Math.max(4, rect.top + 8) + "px";
    btn.classList.add("an");
    // v1.0.6 (JB): grün, wenn das Video schon in der Bibliothek liegt
    // (Antwort kommt aus dem Hintergrund-Cache — kein Dauerfeuer).
    btn.classList.remove("hab");
    btn.title = "Zur Download-Warteschlange hinzufügen";
    const m = url.match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{6,})/);
    if (m) {
      try {
        api.runtime.sendMessage({ typ: "hab", id: m[1] }).then((res) => {
          if (res && res.da && curUrl === url) {
            btn.classList.add("hab");
            btn.title = "Schon in der Bibliothek — Rechtsklick lädt bewusst in anderem Format";
          }
        }, () => {});
      } catch (e) { /* Hintergrund nicht erreichbar -> Knopf bleibt neutral */ }
    }
  }
  function verstecken() { if (btn) btn.classList.remove("an"); curUrl = null; }

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
    // Über YouTubes eigenen Bedienelementen (⋮-Menü, Knöpfe, Dropdowns) sofort
    // weg — nie deren Klickfläche verdecken (JB 22.07., „Video ausblenden").
    if (e.target.closest && e.target.closest("button, yt-icon-button, ytd-menu-renderer, tp-yt-iron-dropdown, tp-yt-paper-listbox")) {
      verstecken(); return;
    }
    const a = videoAnker(e.target);
    if (a) { zeigen(a.getBoundingClientRect(), a.href); resetIdle(); return; }
    const player = e.target.closest ? e.target.closest("#movie_player, .html5-video-player") : null;
    if (player && location.href.includes("/watch")) {
      // Am echten BILD ausrichten (JB v1.0.5): der Player-Container umfasst
      // auch Letterbox/Chrome — der Knopf sass dadurch "etwas ausserhalb"
      // des sichtbaren Videos. Das <video>-Element hat die echten Bild-Masse.
      const video = player.querySelector("video");
      const rect = (video && video.getBoundingClientRect().width > 0)
        ? video.getBoundingClientRect() : player.getBoundingClientRect();
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
