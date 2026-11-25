/* ================= Init (läuft einmal beim Seiten-Start) ================= */
themeIcon();
layoutAnViewport();                              // gespeichertes Layout an die aktuelle Fenstergröße anpassen (22.07.: „am Anfang ausserhalb des Bildschirms")
renderPanels();
layoutEntwirren();                               // alte Layouts mit Überlappungen einmalig bereinigen
L.panels.forEach(p=>merkeView(p.id,p.active));   // Start-Stationen in den Verlauf
layoutSelectFuellen();
einstellungenModalInit();                        // Einstellungs-Karte ins Modal umziehen
playerLayoutSet();
if(typeof ResizeObserver!=='undefined'){        // „Video links" nur bei breiter Karte (playerLayoutSet)
  const plc=document.getElementById('pl-card');
  if(plc)new ResizeObserver(()=>playerLayoutSet()).observe(plc);
}
transportRender();
vizFarbeAktualisieren(); vizModeRender();
geraetMalen();                                    // Gerät-Knopf (Browser/VLC) mit gemerktem Stand
cmdNowRender();
fbEmpfangVerkabeln();                             // Fernbedienung: hört AB START zu —
                                                  // sonst wäre ihr „TV an"-Knopf tot
laden();
libLaden();                                       // Bibliothek sofort laden (Player braucht sie)
plLaden();
aboLaden();
setInterval(laden,1000);
