# -*- coding: utf-8 -*-
"""Profile + Geräte (Sync Teilprojekt 3, JB-Go „weiter mit teilprojekt 3,
profile und geräte-qr").

Zwei Dinge, EIN Zustand (profile.json):
- **Profile** („Wer schaut?", Netflix-Muster): Name + Emoji; die Film-Merkliste
  hängt am Profil (filme.py), der Rest der Bibliothek bleibt gemeinsam.
- **Geräte**: Jedes fremde Gerät (Handy, Fernseher) bekommt beim Koppeln einen
  EIGENEN Token — einzeln widerrufbar, an ein Profil gebunden. Der Pairing-
  Fluss: Gerät meldet sich an (Code erscheint DORT groß), JB gibt am PC frei,
  das Gerät holt sich den Token einmalig mit dem Code ab.

Sicherheits-Regeln (JB 05.08., Spec „Zugriff & Sicherheit"):
- Freigeben/Entfernen geht NUR vom PC selbst (localhost) — der Handler
  erzwingt das; dieses Modul gibt Tokens nie in Listen heraus.
- `geraet_ok(token)` ist der Riegel-Kern für alle Nicht-localhost-Zugriffe
  (zusätzlich zum bestehenden Fernsteuerungs-Code) — Wächter-Test PFLICHT.
- Einbahn-Regel wie filme/geo: importiert NIE youtube_app.
"""
import json
import os
import re
import time
import uuid

import familie as fam

_pfade = {}
CODE_ALTER_S = 15 * 60                     # Pairing-Code verfällt nach 15 min
STANDARD_PROFIL = {"id": "standard", "name": "JB", "emoji": "🦊"}


def einrichten(daten_dir):
    _pfade["profile"] = os.path.join(daten_dir, "profile.json")


def _lesen():
    try:
        with open(_pfade["profile"], encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault("profile", [dict(STANDARD_PROFIL)])
    d.setdefault("geraete", [])
    return d


def _schreiben(d):
    fam.json_schreiben(_pfade["profile"], d)


# ---------------------------------------------------------------- Profile

def profil_liste():
    return _lesen()["profile"]


def profil_anlegen(name, emoji="🙂"):
    name = (name or "").strip()[:24]
    if not name:
        return None
    d = _lesen()
    p = {"id": uuid.uuid4().hex[:8], "name": name,
         "emoji": (emoji or "🙂").strip()[:4] or "🙂"}
    d["profile"].append(p)
    _schreiben(d)
    return p


def profil_gibt_es(profil_id):
    return any(p["id"] == profil_id for p in profil_liste())


# ---------------------------------------------------------------- Geräte

def _codes_aufraeumen(d):
    frisch = []
    for g in d["geraete"]:
        if g.get("verifiziert") or (time.time() - (g.get("ts") or 0)) < CODE_ALTER_S:
            frisch.append(g)
    if len(frisch) != len(d["geraete"]):
        d["geraete"] = frisch
        _schreiben(d)
    return d


def geraet_anmelden(name):
    """Schritt 1 (vom NEUEN Gerät): anmelden → 6-stelliger Code, der DORT
    angezeigt wird. Kein Token, bevor JB am PC freigibt."""
    d = _codes_aufraeumen(_lesen())
    g = {"id": uuid.uuid4().hex[:12],
         "name": re.sub(r"[<>&\"']", "", (name or "Gerät"))[:40] or "Gerät",
         "code": uuid.uuid4().hex[:6].upper(),
         "verifiziert": False, "profil": "", "token": "", "ts": time.time()}
    d["geraete"].append(g)
    _schreiben(d)
    return {"geraet_id": g["id"], "code": g["code"]}


def geraete_liste():
    """Für die PC-Ansicht: NIE Tokens herausgeben — nur Zustand."""
    d = _codes_aufraeumen(_lesen())
    return [{"id": g["id"], "name": g["name"], "code": ("" if g["verifiziert"] else g.get("code", "")),
             "verifiziert": bool(g["verifiziert"]), "profil": g.get("profil", ""),
             "zuletzt": g.get("zuletzt", 0)} for g in d["geraete"]]


def geraet_bestaetigen(geraet_id, profil_id):
    """Schritt 2 (NUR vom PC, Handler erzwingt localhost): freigeben + Profil
    zuordnen. Der Token entsteht hier, bleibt aber liegen, bis das Gerät ihn
    mit seinem Code abholt."""
    d = _lesen()
    g = next((x for x in d["geraete"] if x["id"] == geraet_id), None)
    if not g:
        return False
    g["verifiziert"] = True
    g["profil"] = profil_id if profil_gibt_es(profil_id) else "standard"
    g["token"] = uuid.uuid4().hex
    _schreiben(d)
    return True


def geraet_token_abholen(geraet_id, code):
    """Schritt 3 (vom wartenden Gerät, pollt): erst nach der Freigabe UND nur
    mit dem richtigen Code gibt es den Token — EINMALIG (Code wird entwertet)."""
    d = _lesen()
    g = next((x for x in d["geraete"] if x["id"] == geraet_id), None)
    if not (g and g.get("verifiziert") and g.get("code") and code == g["code"]):
        return None
    g["code"] = ""                          # entwertet: kein zweiter Abruf
    _schreiben(d)
    return {"token": g["token"], "profil": g.get("profil", "standard")}


def geraet_ok(token):
    """DER Riegel-Kern: gültiger Geräte-Token → Profil-Id, sonst None."""
    if not token:
        return None
    d = _lesen()
    g = next((x for x in d["geraete"]
              if x.get("verifiziert") and x.get("token") == token), None)
    if not g:
        return None
    if time.time() - (g.get("zuletzt") or 0) > 3600:    # sparsam stempeln
        g["zuletzt"] = time.time()
        _schreiben(d)
    return g.get("profil") or "standard"


def geraet_entfernen(geraet_id):
    """Widerruf (NUR vom PC): Gerät raus = Token sofort wertlos."""
    d = _lesen()
    vorher = len(d["geraete"])
    d["geraete"] = [g for g in d["geraete"] if g["id"] != geraet_id]
    if len(d["geraete"]) != vorher:
        _schreiben(d)
        return True
    return False


# ---------------------------------------------------------------- Pairing-Seite

PAIRING_HTML = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sync — Gerät koppeln</title><style>
body{margin:0;background:#0c0a09;color:#f2ece5;font-family:system-ui,sans-serif;
  display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center}
.box{padding:30px}h1{font-size:26px}#code{font-size:64px;letter-spacing:10px;
  font-weight:800;color:#e8b04b;margin:20px 0}p{color:#b9aea4;font-size:17px;max-width:420px}
</style></head><body><div class="box"><h1>📺 Dieses Gerät koppeln</h1>
<div id="code">……</div>
<p>Gib dieses Gerät am PC frei: <b>Optionen → 📱 Geräte</b> — dort erscheint
der Code. Diese Seite macht danach von selbst weiter.</p></div>
<script>
(async function(){
  const name=(navigator.userAgent.match(/Android TV|SmartTV|Silk|Android|iPhone|iPad/)||['Browser'])[0]+' '+
    new Date().toLocaleDateString('de-DE');
  const r=await (await fetch('/api/geraet_anmelden',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({name})})).json();
  document.getElementById('code').textContent=r.code;
  const takt=setInterval(async()=>{
    const s=await (await fetch('/api/geraet_status?id='+r.geraet_id+'&code='+r.code)).json();
    if(s.token){clearInterval(takt);
      try{localStorage.setItem('ytdl_geraet_token',s.token);
          localStorage.setItem('ytdl_profil',s.profil||'standard');}catch(e){}
      location.href='/?geraet='+encodeURIComponent(s.token);}
  },3000);
})();
</script></body></html>"""
