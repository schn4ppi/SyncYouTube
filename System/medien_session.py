# -*- coding: utf-8 -*-
"""Gemeinsamer Media-Session-Baustein für die PC-Oberfläche und die Handy-Seite.

Die Media Session API ist der EINZIGE Weg, auf dem eine Webseite die
Medientasten der Tastatur, das Windows-Medien-Overlay und die
Sperrbildschirm-Steuerung von Android/iOS erreicht (live gemessen 23.09.2026 in
Edge, Firefox und der WebView2-Hülle). `oberflaeche.py` und `handy.py` sind zwei
getrennte HTML-Seiten ohne gemeinsamen Skript-Code — damit sie dieselbe
Mechanik nicht zweimal (und irgendwann verschieden) schreiben, liegt sie hier
und wird beim Import in beide Seiten eingesetzt (Platzhalter unten).

Was der Baustein NICHT weiß: welcher Player spielt und was „Weiter" bedeutet.
Das bleibt Sache der Seite (Musik, Film, VLC, Handy). Er kapselt nur, was an
der API fehleranfällig ist:

* `setActionHandler` wirft für Aktionen, die ein Browser nicht kennt — jede
  Anmeldung einzeln gekapselt; `null` meldet einen Knopf ab (Windows blendet
  ihn dann aus, statt ins Leere zu greifen).
* `setPositionState` wirft bei Position > Dauer, bei Rate 0 und bei unfertiger
  Dauer — der Baustein klemmt, und bei unendlicher Dauer (Strom) LÖSCHT er die
  Zeitleiste, statt die des Vortitels stehen zu lassen.

Warum ein Raw-String: der Code landet in Python-Triple-Strings; ein `\\n` im
JS würde dort zum echten Umbruch und das ganze Skript zerreißen (JB-Vorfall
07.08.2026). Ein Raw-String reicht den Text unverändert durch.

Nachladen: Der Server lädt dieses Modul pro Seitenaufruf VOR `oberflaeche.py`/
`handy.py` neu (`_HEISS_NACHLADBAR`), und der Oberflächen-Stand (`ui_stand`)
zählt es mit — offene Tabs erneuern sich also auch bei einer Änderung nur hier.
Scheitert das Einsetzen (Platzhalter fehlt), bleibt die alte, heile Seite
ausgeliefert: die Seiten binden ihre Rohvorlage unter `_HTML_ROH`.
"""

PLATZHALTER = "/*MEDIEN_SESSION_JS*/"

MEDIEN_JS = r"""
/* ---- Media Session: EIN Baustein für PC und Handy (medien_session.py) ----
   elHolen liefert das Medienelement, dessen Zeit gilt, wenn zustand() keine
   eigene Lage bekommt (Film-Transcode und VLC rechnen ihre Position selbst). */
function medienSitzung(elHolen){
  const ms=navigator.mediaSession;
  function aktionen(tabelle){
    if(!ms||!ms.setActionHandler)return;
    for(const name of Object.keys(tabelle)){
      try{ms.setActionHandler(name,tabelle[name]||null);}catch(e){}
    }
  }
  function info(m){
    if(!ms)return;
    if(!m){try{ms.metadata=null;}catch(e){} return;}
    if(!window.MediaMetadata)return;
    try{ms.metadata=new MediaMetadata(m);}catch(e){}
  }
  // [[src, größe], …] -> artwork-Liste; leere Quellen fallen weg (ein Bild
  // ohne src lässt manche Browser die ganze Metadaten-Zuweisung verwerfen).
  function bilder(liste){
    return (liste||[]).filter(b=>b&&b[0]).map(b=>({src:b[0],sizes:b[1]||'512x512',type:'image/jpeg'}));
  }
  function zustand(s,lage){
    if(!ms)return;
    try{ms.playbackState=s;}catch(e){}
    if(!ms.setPositionState)return;
    let d,p,r;
    if(lage){d=lage.dauer; p=lage.pos; r=lage.rate;}
    else{const el=elHolen?elHolen():null; if(!el)return; d=el.duration; p=el.currentTime; r=el.playbackRate;}
    if(!isFinite(d)||d<=0){try{ms.setPositionState();}catch(e){} return;}
    try{ms.setPositionState({duration:d, playbackRate:(r>0?r:1),
      position:Math.max(0,Math.min(p||0,d))});}catch(e){}
  }
  function leeren(){info(null); zustand('none',{dauer:0});}
  // Ein abgelöstes Medienelement HÄLT die Sitzung, solange es eine Quelle hat:
  // gemessen 23.09.2026 blieb Windows' Eintrag nach dem Wechsel auf VLC als
  // „YouTube-Downloader (pausiert)" neben der VLC-Sitzung stehen, am Handy nach
  // dem Umschalten auf „PC" als „YTDL · Handy" — ein toter Knopf im Overlay bzw.
  // auf dem Sperrbildschirm. Quelle lösen beendet den Player und damit die Sitzung.
  function freigeben(el){
    if(!el)return;
    try{el.pause(); el.removeAttribute('src'); el.load();}catch(e){}
  }
  return {aktionen, info, bilder, zustand, leeren, freigeben, kann:()=>!!(ms&&window.MediaMetadata)};
}
"""


def einsetzen(html):
    """Den Baustein genau an der Platzhalter-Stelle einsetzen. Fehlt der
    Platzhalter, ist das ein Bau-Fehler — lieber laut als eine Seite ohne
    Medientasten (der Wächter prüft zusätzlich beide Seiten)."""
    if PLATZHALTER not in html:
        raise ValueError("Platzhalter für den Media-Session-Baustein fehlt")
    return html.replace(PLATZHALTER, MEDIEN_JS, 1)
