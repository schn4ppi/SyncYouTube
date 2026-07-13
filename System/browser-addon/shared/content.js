// Content-Skript auf youtube.com: kleiner, unscheinbarer Download-Knopf, der beim
// Überfahren eines Videos/Vorschaubilds erscheint und bei Mausstillstand wieder
// verschwindet. Klick schickt die URL (via Hintergrund-Skript) an die App.
(function () {
  const api = (typeof browser !== "undefined") ? browser : chrome;
  let btn = null, curUrl = null, hideTimer = null, lastMove = 0;

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
    if (a && a.href && (a.href.includes("/watch?v=") || a.href.includes("/shorts/"))) return a;
    return null;
  }

  function zeigen(rect, url) {
    curUrl = url;
    btn.style.left = Math.max(4, rect.right - 32) + "px";
    btn.style.top = Math.max(4, rect.top + 8) + "px";
    btn.classList.add("an");
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
    if (!btn) mkBtn();
    if (e.target === btn || (btn && btn.contains(e.target))) { resetIdle(); return; }
    const a = videoAnker(e.target);
    if (a) { zeigen(a.getBoundingClientRect(), a.href); resetIdle(); return; }
    const player = e.target.closest ? e.target.closest("#movie_player, .html5-video-player") : null;
    if (player && location.href.includes("/watch")) {
      zeigen(player.getBoundingClientRect(), location.href.split("&")[0]);
      resetIdle();
      return;
    }
    // sonst nichts tun — der Idle-Timer blendet den Knopf aus
  }

  document.addEventListener("mousemove", onMove, true);
  document.addEventListener("scroll", verstecken, true);
})();
