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
import hmac
import os
import re
import threading
import time
import uuid

import familie as fam

_pfade = {}
CODE_ALTER_S = 15 * 60                     # Pairing-Code verfällt nach 15 min
STANDARD_PROFIL = {"id": "standard", "name": "JB", "emoji": "🦊"}


def einrichten(daten_dir):
    _pfade["profile"] = os.path.join(daten_dir, "profile.json")


# ---------------------------------------------------------------- Zustand unter Sperre (S8)
# Gesamtprüfung S8 (25.09.2026): profile.json wurde ohne Sperre gelesen und
# zurückgeschrieben, auch beim bloßen Prüfen eines Tokens (`zuletzt`). Gemessen
# mit 8 Fäden: 12 von 12 getrennten Geräten waren danach wieder gekoppelt, weil
# eine parallele Prüfung den alten Stand zurückschrieb; von 40 gleichzeitig
# angelegten Profilen blieben 5. Jetzt:
#   * Jeder Schreiber geht durch `_aendern` (Lesen, Ändern, Schreiben unter
#     `fam.json_aendern`, dessen Datei-Sperre andere Prozesse fernhält) und
#     `_lock` (die Fäden dieses Prozesses; Leser nehmen sie auch, so sieht keiner
#     eine Datei mitten im Austausch).
#   * Prüfen und Auflisten schreiben NIE. Die letzte Prüfung merkt sich das
#     Modul im Speicher; in die Datei kommt sie mit dem nächsten echten Schreiben.
#   * Ist die Datei da, aber unlesbar, wird nie geschrieben: sonst ersetzten
#     leere Listen JBs Geräte und Profile.
_lock = threading.RLock()
_zuletzt = {}                              # geraet_id -> letzte erfolgreiche Prüfung (Speicher)
_LESEFEHLER = object()                     # Rückfall-Marke für fam.json_laden


class _NichtSchreiben(Exception):
    """Bricht `fam.json_aendern` ab, ohne zu schreiben; trägt das Ergebnis."""

    def __init__(self, wert=None):
        super().__init__()
        self.wert = wert


def _vervollstaendigen(d):
    d.setdefault("profile", [dict(STANDARD_PROFIL)])
    d.setdefault("geraete", [])
    return d


def _lesen():
    """Nur lesen. Unlesbar oder fehlend: die Vorgaben (fail-closed, keine Geräte)."""
    with _lock:
        d = fam.json_laden(_pfade["profile"], None)
    return _vervollstaendigen(d if isinstance(d, dict) else {})


def _aendern(schritt):
    """Lesen-Ändern-Schreiben unter Sperre. `schritt(d)` ändert `d` und gibt
    `(ergebnis, geaendert)` zurück. Rückgabe: das Ergebnis, oder None, wenn nicht
    geschrieben werden konnte (Datei unlesbar, Sperre besetzt, Schreiben
    gescheitert). Ohne Änderung wird nicht geschrieben."""
    pfad = _pfade["profile"]
    ergebnis = []

    def aenderung(d):
        if d is _LESEFEHLER:
            if os.path.exists(pfad):               # da, aber unlesbar: nie überschreiben
                raise _NichtSchreiben(None)
            d = {}                                 # erster Start: die Datei entsteht
        if not isinstance(d, dict):
            raise _NichtSchreiben(None)
        _vervollstaendigen(d)
        geraeumt = _codes_aufraeumen(d)
        wert, geaendert = schritt(d)
        if not (geraeumt or geaendert):
            raise _NichtSchreiben(wert)
        for g in d["geraete"]:                     # gemerkte Prüfungen mitschreiben
            if _zuletzt.get(g.get("id"), 0) > (g.get("zuletzt") or 0):
                g["zuletzt"] = _zuletzt[g["id"]]
        ergebnis.append(wert)
        return d

    with _lock:
        try:
            neu = fam.json_aendern(pfad, aenderung, standard=_LESEFEHLER)
        except _NichtSchreiben as n:
            return n.wert
        # json_aendern meldet ein gescheitertes Schreiben nicht: nachlesen.
        if neu is None or fam.json_laden(pfad, None) != neu:
            return None
    return ergebnis[0]


# ---------------------------------------------------------------- Profile

def profil_liste():
    return _lesen()["profile"]


def profil_anlegen(name, emoji="🙂"):
    """Neues Profil; None bei leerem Namen oder wenn profile.json gerade nicht
    geschrieben werden kann."""
    name = (name or "").strip()[:24]
    if not name:
        return None
    p = {"id": uuid.uuid4().hex[:8], "name": name,
         "emoji": (emoji or "🙂").strip()[:4] or "🙂"}

    def schritt(d):
        d["profile"].append(p)
        return p, True
    return _aendern(schritt)


def profil_gibt_es(profil_id):
    return any(p["id"] == profil_id for p in profil_liste())


# ---------------------------------------------------------------- Geräte

def _abgelaufen(g, jetzt):
    return not g.get("verifiziert") and (jetzt - (g.get("ts") or 0)) >= CODE_ALTER_S


def _codes_aufraeumen(d):
    """Abgelaufene Pairing-Anfragen aus `d` nehmen; True, wenn etwas fiel."""
    jetzt = time.time()
    frisch = [g for g in d["geraete"] if not _abgelaufen(g, jetzt)]
    if len(frisch) == len(d["geraete"]):
        return False
    d["geraete"] = frisch
    return True


def geraet_anmelden(name):
    """Schritt 1 (vom NEUEN Gerät): anmelden → 6-stelliger Code, der DORT
    angezeigt wird. Kein Token, bevor JB am PC freigibt.
    Flut-Deckel (Nachtprüfung 06.08.): höchstens 20 unbestätigte Anmeldungen —
    die älteste fällt raus, verifizierte Geräte bleiben unangetastet.
    None, wenn profile.json gerade nicht geschrieben werden kann."""
    g = {"id": uuid.uuid4().hex[:12],
         "name": re.sub(r"[<>&\"']", "", (name or "Gerät"))[:40] or "Gerät",
         "code": uuid.uuid4().hex[:6].upper(),
         "verifiziert": False, "profil": "", "token": "", "ts": time.time()}

    def schritt(d):
        offen = [x for x in d["geraete"] if not x.get("verifiziert")]
        if len(offen) >= 20:
            aeltester = min(offen, key=lambda x: x.get("ts", 0))
            d["geraete"].remove(aeltester)
        d["geraete"].append(g)
        return {"geraet_id": g["id"], "code": g["code"]}, True
    return _aendern(schritt)


def geraete_liste():
    """Für die PC-Ansicht: NIE Tokens herausgeben — nur Zustand. Liest nur;
    abgelaufene Anfragen blendet sie aus (weggeräumt beim nächsten Schreiben)."""
    d = _lesen()
    jetzt = time.time()
    with _lock:
        gemerkt = dict(_zuletzt)
    return [{"id": g["id"], "name": g["name"], "code": ("" if g["verifiziert"] else g.get("code", "")),
             "verifiziert": bool(g["verifiziert"]), "profil": g.get("profil", ""),
             "zuletzt": max(g.get("zuletzt", 0) or 0, gemerkt.get(g["id"], 0))}
            for g in d["geraete"] if not _abgelaufen(g, jetzt)]


def geraet_bestaetigen(geraet_id, profil_id):
    """Schritt 2 (NUR vom PC, Handler erzwingt localhost): freigeben + Profil
    zuordnen. Der Token entsteht hier, bleibt aber liegen, bis das Gerät ihn
    mit seinem Code abholt."""
    def schritt(d):
        g = next((x for x in d["geraete"] if x["id"] == geraet_id), None)
        if not g:
            return False, False
        g["verifiziert"] = True
        g["profil"] = profil_id if any(p["id"] == profil_id for p in d["profile"]) else "standard"
        g["token"] = uuid.uuid4().hex
        return True, True
    return bool(_aendern(schritt))


def _gleich(ist, soll):
    """Zeitkonstanter Vergleich für Code und Token (Gesamtprüfung S7)."""
    return hmac.compare_digest(str(ist or "").encode("utf-8"), str(soll or "").encode("utf-8"))


def geraet_token_abholen(geraet_id, code):
    """Schritt 3 (vom wartenden Gerät, pollt): erst nach der Freigabe UND nur
    mit dem richtigen Code gibt es den Token — EINMALIG (Code wird entwertet)."""
    def schritt(d):
        g = next((x for x in d["geraete"] if x["id"] == geraet_id), None)
        if not (g and g.get("verifiziert") and g.get("code") and _gleich(code, g["code"])):
            return None, False
        g["code"] = ""                          # entwertet: kein zweiter Abruf
        return {"token": g["token"], "profil": g.get("profil", "standard")}, True
    return _aendern(schritt)


def geraet_ok(token):
    """DER Riegel-Kern: gültiger Geräte-Token → Profil-Id, sonst None.
    Liest nur (S8); die Prüfung merkt sich das Modul im Speicher."""
    if not token:
        return None
    d = _lesen()
    g = next((x for x in d["geraete"]
              if x.get("verifiziert") and x.get("token") and _gleich(token, x["token"])), None)
    if not g:
        return None
    with _lock:
        _zuletzt[g["id"]] = time.time()
    return g.get("profil") or "standard"


def geraet_entfernen(geraet_id):
    """Widerruf (NUR vom PC): Gerät raus = Token sofort wertlos. False auch,
    wenn profile.json gerade nicht geschrieben werden kann."""
    def schritt(d):
        vorher = len(d["geraete"])
        d["geraete"] = [g for g in d["geraete"] if g["id"] != geraet_id]
        weg = len(d["geraete"]) != vorher
        return weg, weg
    ok = bool(_aendern(schritt))
    if ok:
        with _lock:
            _zuletzt.pop(geraet_id, None)
    return ok


# ---------------------------------------------------------------- Fernsteuerung aus

# Nachschärfung 25.09.2026: Ein gekoppeltes Gerät las bei ausgeschalteter
# Fernsteuerung „Gerät nicht gekoppelt“ und hätte sich neu koppeln wollen. Die
# Kopplung bleibt aber gültig; es fehlt nur der Schalter am PC.
FERNSTEUERUNG_AUS_HTML = """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sync — Fernsteuerung aus</title><style>
body{margin:0;background:#0c0a09;color:#f2ece5;font-family:system-ui,sans-serif;
  display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center}
.box{padding:30px}h1{font-size:24px}p{color:#b9aea4;font-size:17px;max-width:420px}
</style></head><body><div class="box"><h1>📴 Fernsteuerung am PC ausgeschaltet.</h1>
<p>Die Kopplung dieses Geräts bleibt gültig. Am PC unter <b>⚙ → 📱 Fernsteuerung</b>
wieder einschalten, dann diese Seite neu laden.</p></div></body></html>"""


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
