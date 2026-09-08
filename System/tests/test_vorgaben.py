# -*- coding: utf-8 -*-
"""Waechter fuer die zwei Vorgaben und ihre Umstellung (JB-Entscheid 08.09.2026).

JB: *„selbst-update standardmaessig an, cookies aus"*.

Die Entscheidung allein in `STANDARD_CONFIG` zu drehen, waere wirkungslos
gewesen. GEMESSEN am 08.09.2026, bevor etwas geaendert wurde:

  * `config_laden` laesst die gespeicherte `config.json` gewinnen, und eine
    solche Datei hat wirklich JEDE Installation - das Programm schreibt sie
    beim Start selbst. In JBs eigener Datei stand `auto_update: false` und
    `cookies_browser: firefox`. Die gedrehten Vorgaben haetten also nicht
    einmal seinen eigenen PC erreicht, geschweige denn den Rechner, wegen dem
    die Entscheidung fiel.
  * Der Filter `if k in STANDARD_CONFIG` warf FUENF Schluessel weg, die das
    Programm selbst schreibt: `name_schema`, `auto_umbenennen`,
    `untertitel_sprachen`, `wiedergabe` und `wg_sub_migriert`. Das gewaehlte
    Namensschema, das Auto-Umbenennen, die Untertitel-Sprachen und die global
    gemerkte Untertitel-Groesse ueberlebten also keinen Neustart - und weil
    auch der Altlast-Merker wegfiel, lief `wiedergabe_sub_altlast_raeumen` bei
    jedem Start erneut.
  * Das Programm hatte ZWEI Wahrheiten ueber seine Cookie-Vorgabe:
    `STANDARD_CONFIG` und den Rueckfallwert in `_ydl_basis_opts`.

Geprueft wird hier ohne Netz, ohne Server und ohne die echte `config.json`.

ROTE GEGENPROBE (08.09.2026 gefahren): ZEHN Zusagen einzeln zurueckgedreht,
jede an der echten Datei, jede byte-genau zurueckgeschrieben (Pruefsumme vorher
und nachher gleich) - alle zehn zugehoerigen Tests fielen. Zusaetzlich zwei
echte Probelaeufe des Programms mit einer vorbereiteten alten config.json: die
Umstellung greift, der Rueckweg traegt den Originalstand, und der zweite Start
aendert nichts mehr. Der ERSTE Probelauf fand dabei einen Fehler in meiner
eigenen Sicherung - siehe test_der_rueckweg_traegt_den_stand_von_VOR_der_umstellung.

NICHT gemessen (Leitplanke P6 verlangt die Liste): ob ein echter Selbst-Tausch
gegen GitHub laeuft (kein Netz, kein PyInstaller-Bau), ob Cookies-aus bei
YouTube tatsaechlich seltener zu Sperren fuehrt als Cookies-an - das ist JBs
Entscheidung, kein Messergebnis von mir - und das Verhalten in der gepackten
exe.
"""
import ast
import io
import json
import os
import sys

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import update  # noqa: E402
import youtube_app as app  # noqa: E402

# --------------------------------------------------------- die Vorgaben selbst

def test_die_zwei_vorgaben_stehen_wie_jb_sie_entschieden_hat():
    assert app.STANDARD_CONFIG["auto_update"] is True, (
        "JB 08.09.2026: Selbst-Update standardmaessig AN")
    assert app.STANDARD_CONFIG["cookies_browser"] == "keine", (
        "JB 08.09.2026: Cookies standardmaessig AUS")


def test_es_gibt_nur_eine_wahrheit_ueber_die_cookie_vorgabe():
    """Der Rueckfallwert in `_ydl_basis_opts` muss dasselbe sagen wie die Vorgabe.

    Gemessen am Erzeugnis, nicht am Text: CFG wird geleert, damit wirklich der
    Rueckfall greift."""
    alt = dict(app.CFG)
    try:
        app.CFG.clear()                       # kein Schluessel -> Rueckfall zaehlt
        opts = app._ydl_basis_opts(mit_cookies=True)
        assert "cookiesfrombrowser" not in opts, (
            "Ohne gesetzten Schluessel greift der Rueckfallwert - und der stand "
            "auf 'firefox', waehrend die Vorgabe 'keine' sagt")
    finally:
        app.CFG.clear()
        app.CFG.update(alt)


def test_keine_bedeutet_wirklich_keine_cookies():
    alt = dict(app.CFG)
    try:
        app.CFG["cookies_browser"] = "keine"
        assert "cookiesfrombrowser" not in app._ydl_basis_opts(mit_cookies=True)
        app.CFG["cookies_browser"] = "firefox"
        assert app._ydl_basis_opts(mit_cookies=True)["cookiesfrombrowser"] == ("firefox",)
    finally:
        app.CFG.clear()
        app.CFG.update(alt)


# ------------------------------------------------- jeder geschriebene Schluessel

def test_jeder_selbst_geschriebene_schluessel_ueberlebt_den_neustart():
    """Was das Programm in CFG schreibt, muss in STANDARD_CONFIG stehen.

    Auto-Discovery ueber den Syntaxbaum statt Handliste: `config_laden` behaelt
    beim Laden NUR Schluessel aus STANDARD_CONFIG. Jeder andere ist eine
    Einstellung ohne Gedaechtnis."""
    quelle = io.open(os.path.join(MODUL_DIR, "youtube_app.py"), encoding="utf-8").read()
    geschrieben = set()
    for k in ast.walk(ast.parse(quelle)):
        if (isinstance(k, ast.Subscript) and getattr(k.value, "id", "") == "CFG"
                and isinstance(k.slice, ast.Constant) and isinstance(k.slice.value, str)):
            geschrieben.add(k.slice.value)
    fehlend = sorted(geschrieben - set(app.STANDARD_CONFIG))
    assert not fehlend, (
        "Diese Schluessel schreibt das Programm, aber config_laden wirft sie beim "
        "naechsten Start weg (die Einstellung ist dann still wieder auf Anfang):\n  "
        + "\n  ".join(fehlend))


# ------------------------------------------------------------- die Umstellung

def _nachziehen(roh):
    """`_vorgaben_nachziehen` an einer gedachten config.json - ohne Datei."""
    app.VORGABEN_NEU.clear()
    cfg = dict(app.STANDARD_CONFIG)
    cfg.update({k: v for k, v in roh.items() if k in app.STANDARD_CONFIG})
    cfg["vorgaben_stand"] = app._vorgaben_nachziehen(cfg, roh)
    return cfg, list(app.VORGABEN_NEU)


def test_bestandsinstallation_bekommt_die_neuen_vorgaben_einmal():
    """Der gemessene Anlassfall: JBs eigene Datei vom 08.09.2026."""
    alt = {"auto_update": False, "cookies_browser": "firefox", "port": 8776}
    cfg, geaendert = _nachziehen(alt)
    assert cfg["auto_update"] is True
    assert cfg["cookies_browser"] == "keine"
    assert cfg["vorgaben_stand"] == app.VORGABEN_STAND
    assert len(geaendert) == 2, "beide Umstellungen muessen gemeldet werden"


def test_die_umstellung_greift_genau_einmal():
    """Wer danach bewusst zurueckstellt, wird nicht erneut ueberfahren."""
    zurueckgestellt = {"auto_update": False, "cookies_browser": "firefox",
                       "vorgaben_stand": app.VORGABEN_STAND}
    cfg, geaendert = _nachziehen(zurueckgestellt)
    assert cfg["auto_update"] is False, "eine spaetere Entscheidung ist unantastbar"
    assert cfg["cookies_browser"] == "firefox"
    assert geaendert == []


def test_eine_bewusste_wahl_wird_nicht_ueberfahren():
    """Umgestellt wird nur, wo noch der ALTE Auslieferungswert steht."""
    eigen = {"auto_update": False, "cookies_browser": "chrome"}
    cfg, _ = _nachziehen(eigen)
    assert cfg["cookies_browser"] == "chrome", "chrome war nie eine Vorgabe"
    assert cfg["auto_update"] is True, "false war die alte Vorgabe - wird gedreht"


def test_frische_installation_wird_nicht_umgestellt():
    """Ohne Datei gibt es nichts nachzuziehen - die Vorgaben gelten ohnehin."""
    cfg, geaendert = _nachziehen({})
    assert geaendert == []
    assert cfg["vorgaben_stand"] == app.VORGABEN_STAND


def _umstellung_vorbereiten(tmp_path, monkeypatch, alt_stand):
    """Eine Umstellung so stellen, wie sie nach `config_laden` aussaehe."""
    ziel = tmp_path / "config.json"
    ziel.write_text(json.dumps(alt_stand), encoding="utf-8")
    monkeypatch.setattr(app, "DATEN_DIR", str(tmp_path))
    monkeypatch.setattr(app, "CONFIG_PFAD", str(ziel))
    monkeypatch.setattr(app, "CFG", dict(app.STANDARD_CONFIG))
    app.CFG["auto_update"] = True
    app.VORGABEN_NEU.clear()
    app.VORGABEN_NEU.append(("auto_update", False, True))
    app.VORGABEN_ROH.clear()
    app.VORGABEN_ROH.update(alt_stand)
    return ziel


def test_umstellung_schreibt_nichts_ohne_rueckweg(tmp_path, monkeypatch):
    """JB-Regel: kein Verlust ohne Rueckweg. Laesst sich die Sicherung nicht
    anlegen, wird NICHT umgestellt."""
    alt = {"auto_update": False}
    ziel = _umstellung_vorbereiten(tmp_path, monkeypatch, alt)
    echt = app._json_speichern

    def schreiben(pfad, daten):
        if "config_vor_stand" in pfad:
            raise OSError("Platte voll")
        echt(pfad, daten)

    monkeypatch.setattr(app, "_json_speichern", schreiben)
    assert app.vorgaben_umstellung_festschreiben() == []
    assert json.loads(ziel.read_text(encoding="utf-8")) == alt, (
        "ohne Sicherung darf die Datei nicht angefasst werden")


def test_der_rueckweg_traegt_den_stand_von_VOR_der_umstellung(tmp_path, monkeypatch):
    """GEMESSEN 08.09.2026 an einem echten Probelauf: die erste Fassung kopierte
    in main() einfach die Datei - und die hatte `wiedergabe_sub_altlast_raeumen`
    da laengst neu geschrieben. Die Sicherung trug also schon die NEUEN Werte.
    Deshalb wird jetzt der beim Laden gelesene Stand gesichert, nicht die Datei."""
    alt = {"auto_update": False, "cookies_browser": "firefox"}
    ziel = _umstellung_vorbereiten(tmp_path, monkeypatch, alt)
    # So sieht es echt aus: die Datei ist beim Sichern schon veraendert.
    ziel.write_text(json.dumps({"auto_update": True, "cookies_browser": "keine"}),
                    encoding="utf-8")
    assert app.vorgaben_umstellung_festschreiben()
    sicherung = tmp_path / ("config_vor_stand%d.json" % app.VORGABEN_STAND)
    assert sicherung.exists(), "der Rueckweg muss als Datei existieren"
    assert json.loads(sicherung.read_text(encoding="utf-8")) == alt, (
        "Ein Rueckweg, der den bereits geaenderten Stand traegt, ist keiner")


# ---------------------------------------------------- der nun scharfe Updater

def test_testmodus_tauscht_niemals_eine_exe():
    cfg = app._testmodus_config(dict(app.STANDARD_CONFIG), "irgendwo")
    assert cfg["auto_update"] is False, (
        "Seit die Vorgabe AN ist, wuerde eine Probe sonst die echte exe tauschen")


def test_selbst_tausch_wartet_auf_den_leerlauf():
    """Der Tausch beendet den Prozess hart - nicht mitten im Download."""
    with app.Q.lock:
        gemerkt = list(app.Q.items)
        app.Q.items[:] = [{"id": "x", "status": "laeuft"}]
    try:
        assert app._downloads_aktiv() is True
        with app.Q.lock:
            app.Q.items[:] = [{"id": "x", "status": "fertig"}]
        assert app._downloads_aktiv() is False
    finally:
        with app.Q.lock:
            app.Q.items[:] = gemerkt


def test_pruefsumme_wird_eindeutig_gewaehlt():
    """Das echte Release traegt ZWEI .sha256-Assets."""
    basis = "https://github.com/schn4ppi/SyncYouTube/releases/download/v.1.2.4/"
    assets = [
        {"name": "SyncYouTube-Quellstart.zip", "browser_download_url": basis + "SyncYouTube-Quellstart.zip"},
        {"name": "SyncYouTube-Quellstart.zip.sha256", "browser_download_url": basis + "SyncYouTube-Quellstart.zip.sha256"},
        {"name": "SyncYouTube.exe", "browser_download_url": basis + "SyncYouTube.exe"},
        {"name": "SyncYouTube.exe.sha256", "browser_download_url": basis + "SyncYouTube.exe.sha256"},
    ]
    for reihenfolge in (assets, list(reversed(assets))):
        exe, sha = update.pick_assets(reihenfolge)
        assert exe["name"] == "SyncYouTube.exe"
        assert sha["name"] == "SyncYouTube.exe.sha256", (
            "Die Pruefsumme des Quellstart-Pakets wuerde jede gesunde exe "
            "verwerfen - und das Selbst-Update stillschweigend toeten")


def test_kein_neues_release_ist_nicht_dasselbe_wie_kein_netz():
    rel = {"tag_name": "v.1.2.4", "assets": [
        {"name": "SyncYouTube.exe", "size": 200 * 2 ** 20,
         "browser_download_url":
             "https://github.com/schn4ppi/SyncYouTube/releases/download/v.1.2.4/SyncYouTube.exe"}]}

    def offline():
        raise OSError("kein Netz")

    assert update.check_release("1.2.4", fetch_json=lambda: rel)["grund"] == "aktuell"
    assert update.check_release("1.0.0", fetch_json=lambda: rel)["grund"] == "neu"
    assert update.check_release("1.0.0", fetch_json=offline)["grund"] == "offline"
    assert update.check_release("1.0.0", fetch_json=lambda: {"tag_name": "v.9.9.9",
                                                            "assets": []})["grund"] == "kein-asset"
