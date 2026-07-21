/* layout_kern.js — gemeinsamer Layout-Mathe-Kern der Sync-Familie
   (Overlay-Projekt, JB-Go 22.07.2026: "layout_kern go, eigenes Projekt").

   REINE Funktionen, KEIN DOM, KEIN localStorage: Rechtecke rein ({x,y,w,h,id}),
   Rechtecke/Werte raus. Jede Oberflaeche behaelt ihr eigenes Rendering und
   Aussehen (JB: "YouTube gefaellt mir wie es gerade aussieht") — geteilt wird
   nur die Geometrie: Kanten-Magnet (Snapping), Ueberlappungs-Pruefung, uniforme
   Viewport-Einpassung mit Minima. Die Formeln sind ORIGINALGETREU aus dem
   SyncYouTube-Canvas extrahiert (Verhalten per Konstruktion erhalten); der
   Aequivalenz-Waechter test_layout_kern prueft das gegen Referenzvektoren.

   MASTER: SyncDashTray/System/layout_kern.js (vendor_kern verteilt Kopien).
   In SyncYouTube lebt der Kern als markierter Inline-Block in oberflaeche.py
   (LAYOUT_KERN_START/_END — exe-sicher, kein Laufzeit-Dateizugriff); der
   Waechter erzwingt Byte-Gleichheit von Block und Master. */
(function(root){
"use strict";
var LK={};

/* Ueberlappen sich zwei Rechtecke? (Kanten-Beruehrung = KEIN Ueberlappen) */
LK.ueberlappt=function(a,b){
  return a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;
};

/* Kollidiert der Kasten (x,y,w,h) mit einem ANDEREN Rechteck der Liste? */
LK.kollidiert=function(rects,selbstId,x,y,w,h){
  return rects.some(function(o){
    return o.id!==selbstId && x<o.x+o.w && x+w>o.x && y<o.y+o.h && y+h>o.y;
  });
};

/* Die NAECHSTE Kante im Fangradius T — sonst die Ausgangsposition. */
LK.naechsteKante=function(pos,kandidaten,T){
  var best=pos,bestD=T+0.001;
  for(var i=0;i<kandidaten.length;i++){
    var d=Math.abs(pos-kandidaten[i]);
    if(d<bestD){bestD=d; best=kandidaten[i];}
  }
  return best;
};

/* Kanten-Magnet beim Ziehen: Rand, Kanten-Ausrichtung mit Nachbarn und Anlegen
   mit Gap. Liefert die gefangene Position {x,y} (mutiert nichts). */
LK.snapXY=function(p,rects,cw,ch,gap,T){
  if(T==null)T=16;
  var xk=[0,cw-p.w], yk=[0,ch-p.h];
  rects.forEach(function(o){
    if(o.id===p.id)return;
    xk.push(o.x, o.x+o.w-p.w, o.x-gap-p.w, o.x+o.w+gap);
    yk.push(o.y, o.y+o.h-p.h, o.y-gap-p.h, o.y+o.h+gap);
  });
  return {x:LK.naechsteKante(p.x,xk,T), y:LK.naechsteKante(p.y,yk,T)};
};

/* Uniforme Skalierung ALLER Rechtecke um (rx,ry) mit Minima-Klemme — Adjazenz
   bleibt, nichts rutscht ins Negative. Mutiert die Objekte (wie das Original). */
LK.skaliere=function(rects,rx,ry,minW,minH){
  rects.forEach(function(p){
    p.x=Math.max(0,Math.round(p.x*rx)); p.y=Math.max(0,Math.round(p.y*ry));
    p.w=Math.max(minW,Math.round(p.w*rx)); p.h=Math.max(minH,Math.round(p.h*ry));
  });
};

/* Layout in einen Ziel-Viewport einpassen: Bezug = gemerkte Speichergroesse
   (ref) oder — bei Alt-Layouts ohne Bezug — die eigene Bounding-Box. Skaliert
   nur bei Abweichung > schwelle (Default 1%). Rueckgabe: true wenn skaliert. */
LK.passeInViewport=function(rects,ref,ziel,minW,minH,schwelle){
  if(schwelle==null)schwelle=0.01;
  if(!rects||!rects.length||!ziel)return false;
  if(!(ref&&ref.cw>0&&ref.ch>0)){
    var maxR=Math.max.apply(null,rects.map(function(p){return p.x+p.w;}));
    var maxB=Math.max.apply(null,rects.map(function(p){return p.y+p.h;}));
    ref={cw:Math.max(320,maxR), ch:Math.max(320,maxB)};
  }
  var rx=ziel.cw/ref.cw, ry=ziel.ch/ref.ch;
  if(Math.abs(rx-1)>schwelle||Math.abs(ry-1)>schwelle){
    LK.skaliere(rects,rx,ry,minW,minH);
    return true;
  }
  return false;
};

if(typeof module!=="undefined"&&module.exports)module.exports=LK;
if(root)root.LK=LK;
})(typeof window!=="undefined"?window:null);
