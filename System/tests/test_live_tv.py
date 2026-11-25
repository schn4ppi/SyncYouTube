# -*- coding: utf-8 -*-
"""Live-TV: ein gescheiterter Abruf der Senderliste darf nicht still bleiben
(Lehrbuch P5: Stille ist ein Ausfall). Befund SyncYouTube-03, 06.09.2026.
Alles in tmp_path, kein Netz: urlopen ist gepatcht (P7)."""
import json
import os
import sys
import time

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)
import live_tv  # noqa: E402

ALT = [{"name": "ARD", "logo": "", "gruppe": "Sender", "url": "http://x/ard.m3u8"}]


def _cache_anlegen(tmp_path, stand):
    live_tv.einrichten(str(tmp_path))
    with open(tmp_path / "live_tv.json", "w", encoding="utf-8") as f:
        json.dump({"stand": stand, "kanaele": ALT}, f)


def test_abruf_fehler_wird_gemerkt_und_alter_cache_traegt(tmp_path, monkeypatch):
    stand_alt = time.time() - 3 * live_tv.CACHE_ALTER_S
    _cache_anlegen(tmp_path, stand_alt)

    def kaputt(*a, **k):
        raise OSError("Netz weg")
    monkeypatch.setattr(live_tv.urllib.request, "urlopen", kaputt)

    assert live_tv.kanaele() == ALT                 # Rückfall bleibt (Verhalten erhalten)
    d = json.loads((tmp_path / "live_tv.json").read_text(encoding="utf-8"))
    assert d["kanaele"] == ALT and d["stand"] == stand_alt, "alter Stand bleibt unverändert"
    assert "Netz weg" in d["letzter_fehler"] and d["fehler_seit"] > 0
    st = live_tv.status()
    assert st["fehler"] and st["stand"] == stand_alt and st["kanaele"] == 1


def test_erfolg_loescht_den_gemerkten_fehler(tmp_path, monkeypatch):
    _cache_anlegen(tmp_path, 0)
    with open(tmp_path / "live_tv.json", "w", encoding="utf-8") as f:
        json.dump({"stand": 0, "kanaele": ALT, "letzter_fehler": "alt", "fehler_seit": 1}, f)

    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'#EXTINF:-1 tvg-logo="l" group-title="G",ZDF\nhttp://x/zdf.m3u8\n'
    monkeypatch.setattr(live_tv.urllib.request, "urlopen", lambda *a, **k: R())
    assert live_tv.kanaele(frisch=True)[0]["name"] == "ZDF"
    st = live_tv.status()
    assert st["fehler"] == "" and st["fehler_seit"] == 0 and st["kanaele"] == 1


def test_leere_liste_zaehlt_als_fehler(tmp_path, monkeypatch):
    _cache_anlegen(tmp_path, 0)

    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"# nichts\n"
    monkeypatch.setattr(live_tv.urllib.request, "urlopen", lambda *a, **k: R())
    assert live_tv.kanaele(frisch=True) == ALT
    assert "leer" in live_tv.status()["fehler"]


def test_nach_einem_fehlschlag_ruht_der_abruf_eine_stunde(tmp_path, monkeypatch):
    """Gesamtprüfung F18 (25.09.2026): nach einem gescheiterten Abruf versuchte
    jeder Aufruf und jeder Senderklick erneut, jedes Mal bis zu 30 s lang.
    Jetzt ruht der Abruf eine Stunde (`letzter_versuch`); der alte Cache trägt."""
    _cache_anlegen(tmp_path, time.time() - 3 * live_tv.CACHE_ALTER_S)
    versuche = []

    def kaputt(*a, **k):
        versuche.append(1)
        raise OSError("Netz weg")
    monkeypatch.setattr(live_tv.urllib.request, "urlopen", kaputt)
    assert live_tv.kanaele() == ALT and len(versuche) == 1
    assert live_tv.kanaele() == ALT and live_tv.kanaele() == ALT
    assert len(versuche) == 1, f"{len(versuche)} Abrufe binnen einer Stunde nach dem Fehlschlag"
    d = json.loads((tmp_path / "live_tv.json").read_text(encoding="utf-8"))
    d["letzter_versuch"] -= 3601
    (tmp_path / "live_tv.json").write_text(json.dumps(d), encoding="utf-8")
    assert live_tv.kanaele() == ALT and len(versuche) == 2, "nach einer Stunde wird erneut gefragt"
    live_tv.kanaele(frisch=True)
    assert len(versuche) == 3, "ein ausdrücklich frischer Abruf fragt sofort"
