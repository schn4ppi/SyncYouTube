# -*- coding: utf-8 -*-
"""build_release.py: Erzeugnis-Prüfung nach dem PyInstaller-Schritt (24.09.2026).

Befund 2b der Analyse „auslieferung": winrt steht in der exe-BAUVORSCHRIFT
(SyncYouTube.spec, belegt von test_exe_nimmt_pywinrt_mit mit Attrappen), aber in
keiner gebauten exe — die letzte Bauliste (08.09.) enthält 0 winrt-Einträge.
Ein Wächter, der die Vorschrift ausführt, beweist nicht die gebaute Datei.
Darum prüft build_release.py jetzt die BAULISTE (PKG-00.toc, was wirklich in die
exe gepackt wird) an den QUELLPFADEN (Muster eingebackene_namen im 
Wächter test_syncyoutube_lizenzen) und bricht fail-closed ab.

KEIN echter Bau, KEIN Signieren: PyInstaller und signieren sind Attrappen.
"""
import ast
import importlib.util
import os
import re
import sys
import types

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = r"C:\venv\Lib\site-packages"


@pytest.fixture
def br(monkeypatch):
    # signieren liegt außerhalb dieses Repos und fasst den Token an — nie im Test.
    monkeypatch.setitem(sys.modules, "signieren", types.ModuleType("signieren"))
    spec = importlib.util.spec_from_file_location(
        "build_release_unter_test", os.path.join(MODUL_DIR, "build_release.py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    # Die Tests laufen in jeder venv; ob DIESE die Bau-Umgebung ist, prüft
    # test_fremde_umgebung_baut_nicht eigens.
    monkeypatch.setattr(modul.bau_pakete, "abweichungen", lambda *a, **k: [])
    return modul


def _eintrag(rel, art="EXTENSION"):
    """Ein Bauliste-Eintrag (Ziel, Quelle, Art) wie PyInstaller ihn schreibt."""
    return (rel.replace("/", "\\"), SITE + "\\" + rel.replace("/", "\\"), art)


def _bauliste(pfad, eintraege):
    # Form von PKG-00.toc: (pkg-Pfad, Optionen, [Einträge], Python-DLL, …)
    inhalt = (r"C:\bau\SyncYouTube.pkg", {"EXTENSION": True},
              [("PYZ-00.pyz", r"C:\bau\PYZ-00.pyz", "PYZ"),
               _eintrag("PIL/_imaging.cp314-win_amd64.pyd"), *eintraege],
              "python314.dll", False, False, False, [], None, None, None)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(repr(inhalt))
    return str(pfad)


def _oberflaeche_eintraege():
    """Die Teile der PC-Oberfläche, wie PyInstaller sie als Daten einträgt
    (Zielname relativ zur exe, Quelle unter System/)."""
    namen = ["layout_kern.js"]
    for ordner, _unter, dateien in os.walk(os.path.join(MODUL_DIR, "pc_oberflaeche")):
        namen += [os.path.relpath(os.path.join(ordner, d), MODUL_DIR) for d in dateien]
    return [(n, os.path.join(MODUL_DIR, n), "DATA") for n in sorted(namen)]


def _winrt_teile(br):
    teile = [_eintrag(f"winrt/{e}.cp314-win_amd64.pyd") for e in br.winrt_erweiterungen()]
    return teile + [_eintrag(f"winrt/{d}", "BINARY") for d in br.winrt_dlls()]


def _vollstaendig(br):
    """Alles, was die Erzeugnis-Prüfung verlangt: winrt und die Oberfläche."""
    return _winrt_teile(br) + _oberflaeche_eintraege()


def test_erwartete_winrt_teile_kommen_aus_medien_smtc(br, tmp_path):
    # Auto-Discovery: aus den Importen von medien_smtc über die Paket-Quellen der
    # venv zu den Binärerweiterungen — nicht aus einer Handliste.
    # pywinrt 3 hatte je Bereich ein Teil, pywinrt 4 einen Kern (_winrt) und ein
    # eigenes für Interop; in beiden muss der Kern dabei sein.
    namen = br.winrt_erweiterungen()
    assert "_winrt" in namen and "_winrt_windows_media_interop" in namen, namen
    winrt_ordner = os.path.dirname(importlib.util.find_spec("winrt.runtime").origin)
    winrt_ordner = os.path.dirname(winrt_ordner)
    vorhanden = os.listdir(winrt_ordner)
    for name in namen:
        assert any(d.startswith(name + ".") and d.endswith(".pyd") for d in vorhanden), \
            f"{name}: keine .pyd dieses Namens in {winrt_ordner}"
    # Gegenstück: nutzt der Server nur EIN Modul, wird auch nur dessen Teil erwartet.
    klein = tmp_path / "medien_smtc.py"
    klein.write_text("from winrt.windows.foundation import Uri\n", encoding="utf-8")
    # (Interop braucht Foundation nicht, also fehlt sein Teil.)
    wenig = br.winrt_erweiterungen(str(klein))
    assert wenig and wenig <= namen and "_winrt_windows_media_interop" not in wenig, wenig


def test_vollstaendige_bauliste_besteht(br, tmp_path):
    assert br.erzeugnis_pruefen(_bauliste(tmp_path / "PKG-00.toc", _vollstaendig(br))) == []


def test_jedes_fehlende_teil_wird_gemeldet(br, tmp_path):
    voll = _winrt_teile(br)
    for i, weg in enumerate(voll):
        rest = voll[:i] + voll[i + 1:]
        fehlt = br.erzeugnis_pruefen(_bauliste(tmp_path / f"PKG-{i}.toc", rest))
        name = os.path.basename(weg[1])
        assert len(fehlt) == 1 and fehlt[0] in name, (name, fehlt)


def test_gleichnamige_datei_ausserhalb_von_winrt_zaehlt_nicht(br, tmp_path):
    # Eine msvcp140.dll von irgendwoher (z. B. PySide) ersetzt nicht die neben
    # _winrt.pyd — Windows sucht sie im Ordner der Erweiterung.
    rest = [e for e in _vollstaendig(br) if "msvcp140" not in e[1]]
    rest.append(_eintrag("PySide6/msvcp140.dll", "BINARY"))
    # Ausdrücklich verlangt: pywinrt 4 bringt keine DLL mehr mit, die Regel gilt
    # aber für jede, die das Paket mitbringt.
    assert br.erzeugnis_pruefen(_bauliste(tmp_path / "PKG-00.toc", rest),
                                dlls={"msvcp140.dll"}) == ["msvcp140.dll"]


def test_ohne_lesbare_bauliste_fail_closed(br, tmp_path):
    assert br.erzeugnis_pruefen(str(tmp_path / "gibt_es_nicht.toc"))
    kaputt = tmp_path / "kaputt.toc"
    kaputt.write_text("(kein gültiges Python", encoding="utf-8")
    assert br.erzeugnis_pruefen(str(kaputt))


def test_bauen_bricht_ab_wenn_winrt_in_der_exe_fehlt(br, monkeypatch, tmp_path):
    # Die Prüfung hängt IM Bau-Schritt: PyInstaller „erfolgreich", exe da, aber die
    # Bauliste ohne winrt -> Abbruch, bevor signiert oder veröffentlicht wird.
    aufrufe = []
    monkeypatch.setattr(br.subprocess, "run",
                        lambda befehl, **kw: aufrufe.append(befehl) or
                        types.SimpleNamespace(returncode=0))
    exe = tmp_path / "SyncYouTube.exe"
    exe.write_bytes(b"MZ")
    monkeypatch.setattr(br, "GEBAUT", str(exe))
    monkeypatch.setattr(br, "BAULISTE", _bauliste(tmp_path / "PKG-00.toc", []), raising=False)
    with pytest.raises(SystemExit) as abbruch:
        br.bauen()
    assert "winrt" in str(abbruch.value) or "msvcp140" in str(abbruch.value)
    assert aufrufe and "PyInstaller" in aufrufe[0], "Attrappe wurde nicht gerufen"
    # mit vollständiger Bauliste läuft bauen() durch
    monkeypatch.setattr(br, "BAULISTE", _bauliste(tmp_path / "PKG-01.toc", _vollstaendig(br)))
    br.bauen()


def test_nur_signieren_prueft_das_erzeugnis_zuerst(br, monkeypatch, tmp_path):
    """Prüfung Runde 1 (mittel): main() prüfte das Erzeugnis NUR im Bau-Weg.
    Scheiterte die Prüfung, blieb die exe ohne winrt in dist/ liegen — und der
    dokumentierte Weg `--nur-signieren` (etwa weil der Token nicht steckte)
    signierte genau diese exe und legte sie oben zum Veröffentlichen bereit.
    Jetzt prüft auch --nur-signieren zuerst, fail-closed: kein Signieren, keine
    Prüfsumme, nichts nach oben."""
    signiert = _signier_attrappe(br, monkeypatch, token=True)
    exe = tmp_path / "dist" / "SyncYouTube.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")
    oben = tmp_path / "oben"
    oben.mkdir()
    monkeypatch.setattr(br, "GEBAUT", str(exe))
    monkeypatch.setattr(br, "OBEN", str(oben))
    monkeypatch.setattr(br.sys, "argv", ["build_release.py", "--nur-signieren"])
    for name, bauliste in (("ohne winrt", _bauliste(tmp_path / "PKG-00.toc", [])),
                           ("keine Bauliste", str(tmp_path / "gibt_es_nicht.toc"))):
        monkeypatch.setattr(br, "BAULISTE", bauliste)
        with pytest.raises(SystemExit) as abbruch:
            br.main()
        assert "[FEHLER]" in str(abbruch.value), (name, abbruch.value)
        assert signiert == [], f"{name}: signiert trotz fehlendem winrt"
        assert os.listdir(oben) == [] and not os.path.exists(str(exe) + ".sha256"), name
    # Vollständige Bauliste: signieren, Prüfsumme, nach oben — wie bisher.
    monkeypatch.setattr(br, "BAULISTE", _bauliste(tmp_path / "PKG-01.toc", _vollstaendig(br)))
    br.main()
    assert signiert == [str(exe)]
    assert sorted(os.listdir(oben)) == ["SyncYouTube.exe", "SyncYouTube.exe.sha256"]


# ------------------------------------------ ohne Signatur kein Release (S9, 7a Punkt 6)
# Entscheid 25.09.2026: Das Selbst-Update tauscht nur noch signierte exe.
# Ein unsignierter Release hielte damit jedes Update an; darum baut
# build_release.py ohne gesteckten Token gar nicht erst (klare Meldung), und
# scheitert das Signieren später doch, landet nichts oben.

class _SignierFehler(RuntimeError):
    pass


def _signier_attrappe(br, monkeypatch, *, token, signiert_ok=True):
    signiert = []

    def pflicht(pfad, **kw):
        if not (token and signiert_ok):
            raise _SignierFehler("Release-Bau ohne Signatur (kein_zertifikat)")
        signiert.append(pfad)
        return "signiert"
    monkeypatch.setattr(br.signieren, "SignierFehler", _SignierFehler, raising=False)
    monkeypatch.setattr(br.signieren, "signtool_pfad", lambda: r"C:\sdk\signtool.exe", raising=False)
    monkeypatch.setattr(br.signieren, "zertifikate",
                        lambda: [{"Thumbprint": "AB", "Subject": "CN=X", "Issuer": "CN=CA"}]
                        if token else [], raising=False)
    monkeypatch.setattr(br.signieren, "signiere",
                        lambda *d, **kw: "signiert" if token else "kein_zertifikat", raising=False)
    monkeypatch.setattr(br.signieren, "signiere_pflicht", pflicht, raising=False)
    return signiert


def _bau_umgebung(br, monkeypatch, tmp_path, argv):
    aufrufe = []
    monkeypatch.setattr(br.subprocess, "run",
                        lambda befehl, **kw: aufrufe.append(befehl) or
                        types.SimpleNamespace(returncode=0))
    exe = tmp_path / "dist" / "SyncYouTube.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")
    oben = tmp_path / "oben"
    oben.mkdir()
    monkeypatch.setattr(br, "GEBAUT", str(exe))
    monkeypatch.setattr(br, "OBEN", str(oben))
    monkeypatch.setattr(br, "BAULISTE", _bauliste(tmp_path / "PKG-00.toc", _vollstaendig(br)))
    monkeypatch.setattr(br.sys, "argv", argv)
    return aufrufe, exe, oben


@pytest.mark.parametrize("argv", [["build_release.py"], ["build_release.py", "--nur-signieren"]])
def test_ohne_token_wird_nicht_gebaut(br, monkeypatch, tmp_path, argv):
    signiert = _signier_attrappe(br, monkeypatch, token=False)
    aufrufe, exe, oben = _bau_umgebung(br, monkeypatch, tmp_path, argv)
    with pytest.raises(SystemExit) as abbruch:
        br.main()
    meldung = str(abbruch.value)
    assert "[FEHLER]" in meldung and "Token" in meldung, meldung
    assert aufrufe == [], "ohne Token startet kein PyInstaller"
    assert signiert == [] and os.listdir(oben) == []
    assert not os.path.exists(str(exe) + ".sha256")


def test_scheitert_das_signieren_landet_nichts_oben(br, monkeypatch, tmp_path):
    # Token beim Start da, beim Signieren nicht mehr (abgezogen, PIN abgebrochen).
    _signier_attrappe(br, monkeypatch, token=True, signiert_ok=False)
    aufrufe, exe, oben = _bau_umgebung(br, monkeypatch, tmp_path, ["build_release.py"])
    with pytest.raises(SystemExit) as abbruch:
        br.main()
    assert "[FEHLER]" in str(abbruch.value) and "Signatur" in str(abbruch.value)
    assert aufrufe, "gebaut wurde"
    assert os.listdir(oben) == [] and not os.path.exists(str(exe) + ".sha256")


def test_fremde_umgebung_baut_nicht(br, monkeypatch, tmp_path):
    # Bis 1.4.0 baute die exe aus der gemeinsamen venv mit deren Fassungen. Weicht das
    # laufende Python vom Bau-Stand ab, endet der Lauf vor Token und PyInstaller.
    signiert = _signier_attrappe(br, monkeypatch, token=True)
    aufrufe, exe, oben = _bau_umgebung(br, monkeypatch, tmp_path, ["build_release.py"])
    monkeypatch.setattr(br.bau_pakete, "abweichungen", lambda *a, **k: ["pillow: 12.2.0 statt 13.0.0"])
    with pytest.raises(SystemExit) as abbruch:
        br.main()
    meldung = str(abbruch.value)
    assert "Bau-Umgebung" in meldung and "pillow" in meldung, meldung
    assert aufrufe == [] and signiert == [] and os.listdir(oben) == []


def test_abweichungen_vergleicht_mit_dem_bau_stand(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "bau_pakete_unter_test", os.path.join(MODUL_DIR, "tools", "bau_pakete.py"))
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    stand = tmp_path / "bau_stand.txt"
    stand.write_text("# Kopf\nPillow==13.0.0\nyt-dlp==2026.11.23\n", encoding="utf-8")
    fassungen = {"pillow": "13.0.0", "yt-dlp": "2026.11.23"}

    def fassung_von(name):
        if name not in fassungen:
            raise bp.md.PackageNotFoundError(name)
        return fassungen[name]
    assert bp.abweichungen(str(stand), fassung_von) == []
    fassungen["pillow"] = "12.2.0"
    del fassungen["yt-dlp"]
    assert bp.abweichungen(str(stand), fassung_von) == [
        "pillow: 12.2.0 statt 13.0.0", "yt-dlp: fehlt (Soll 2026.11.23)"]


def test_mit_token_signiert_und_kopiert(br, monkeypatch, tmp_path):
    signiert = _signier_attrappe(br, monkeypatch, token=True)
    aufrufe, exe, oben = _bau_umgebung(br, monkeypatch, tmp_path, ["build_release.py"])
    br.main()
    assert signiert == [str(exe)]
    assert sorted(os.listdir(oben)) == ["SyncYouTube.exe", "SyncYouTube.exe.sha256"]


# ------------------------------------------ Schnittstelle zu signieren.py anderer Programme
# Die Bau-Tests ersetzen `signieren` durch ein leeres Modul (es fasst den Token
# an). Drifteten Namen oder Parameter der Datei, blieben sie alle grün,
# während der echte Bau mit AttributeError oder TypeError abbräche. Dieser
# Wächter liest beide Seiten nur als Syntaxbaum: was build_release.py von
# `signieren` nutzt (Auto-Discovery), muss dort oben stehen, und jedes
# Schlüsselwort eines Aufrufs muss ein Parameter der gerufenen Funktion sein.

def _nutzung_im_bau():
    """{Name: {genutzte Schlüsselwörter}} aller `signieren.<Name>` in build_release.py."""
    baum = ast.parse(open(os.path.join(MODUL_DIR, "build_release.py"), encoding="utf-8").read())
    nutzung = {}
    for n in ast.walk(baum):
        if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                and n.value.id == "signieren"):
            nutzung.setdefault(n.attr, set())
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "signieren"):
            nutzung.setdefault(n.func.attr, set()).update(k.arg for k in n.keywords if k.arg)
    return nutzung


def _abweichungen(signieren_pfad, nutzung):
    """Liste der Namen/Schlüsselwörter, die build_release.py nutzt, die aber in
    `signieren_pfad` fehlen (leer = Schnittstelle passt)."""
    baum = ast.parse(open(signieren_pfad, encoding="utf-8").read())
    oben = {}
    for n in baum.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            oben[n.name] = (None if a.kwarg else
                            {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs})
        elif isinstance(n, ast.ClassDef):
            oben[n.name] = None
        elif isinstance(n, ast.Assign):
            oben.update({t.id: None for t in n.targets if isinstance(t, ast.Name)})
    fehlt = []
    for name, schluessel in sorted(nutzung.items()):
        if name not in oben:
            fehlt.append(name)
        elif oben[name] is not None:
            fehlt += [f"{name}({s}=)" for s in sorted(schluessel - oben[name])]
    return fehlt


def test_signieren_passt_zum_bau(br):
    nutzung = _nutzung_im_bau()
    assert "signiere_pflicht" in nutzung and nutzung["signiere_pflicht"], \
        "Auto-Discovery findet den Signier-Aufruf nicht — der Wächter wäre blind"
    ordner = br._signier_ordner()
    pfad = os.path.join(ordner, "signieren.py") if ordner else ""
    if not (pfad and os.path.exists(pfad)):
        pytest.skip("kein Signier-Skript eingetragen (tools/bau_lokal.json fehlt auf diesem PC)")
    assert _abweichungen(pfad, nutzung) == [], "signieren.py passt nicht mehr zu build_release.py"


def test_schnittstellen_waechter_schlaegt_an(tmp_path):
    """Gegenprobe an einer gedrifteten Fassung: fehlender Name und fehlendes
    Schlüsselwort werden gemeldet, eine passende Fassung nicht."""
    passend = ("class SignierFehler(RuntimeError):\n    pass\n\n"
               "def signtool_pfad():\n    return ''\n\n"
               "def zertifikate():\n    return []\n\n"
               "def signiere_pflicht(*dateien, beschreibung=None):\n    return ''\n")
    p = tmp_path / "signieren.py"
    p.write_text(passend, encoding="utf-8")
    assert _abweichungen(str(p), _nutzung_im_bau()) == []
    p.write_text(passend.replace("def zertifikate", "def zertifikat_liste")
                 .replace("beschreibung=None", "titel=None"), encoding="utf-8")
    assert _abweichungen(str(p), _nutzung_im_bau()) == ["signiere_pflicht(beschreibung=)", "zertifikate"]


# ------------------------------------------ heiß nachgeladene Seiten in der exe
# Nacharbeit Gruppe 7 (25.09.2026): `_seite_frisch` in youtube_app.py lädt die
# Seiten aus HEISSE_SEITEN über ihren NAMEN (importlib.import_module). Den sieht
# der Import-Scanner von PyInstaller nicht; gemessen mit PyInstaller 6.21: vorher
# stand `import fernbedienung` im Rumpf von do_GET und war sichtbar, danach nicht
# mehr. Ohne hiddenimports fehlte fernbedienung in der exe, und /fernbedienung
# endete dort mit ModuleNotFoundError. Der Wächter liest die Namen aus der
# Tabelle selbst (Auto-Discovery) und fragt das ERGEBNIS der Bauvorschrift ab
# (ausgeführt mit Attrappen für PyInstaller), nicht ihre Schreibweise.

def _spec_hiddenimports(monkeypatch, spec_text):
    """Die Bauvorschrift mit Attrappen für PyInstaller ausführen; ihre hiddenimports."""
    hooks = types.ModuleType("PyInstaller.utils.hooks")
    hooks.collect_all = lambda name: ([], [], [])
    for name, mod in (("PyInstaller", types.ModuleType("PyInstaller")),
                      ("PyInstaller.utils", types.ModuleType("PyInstaller.utils")),
                      ("PyInstaller.utils.hooks", hooks)):
        monkeypatch.setitem(sys.modules, name, mod)
    analyse = {}

    def Analysis(skripte, **kw):
        analyse.update(kw)
        return types.SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
    g = {"__name__": "__spec__", "Analysis": Analysis,
         "PYZ": lambda *a, **k: None, "EXE": lambda *a, **k: None}
    exec(compile(spec_text, "SyncYouTube.spec", "exec"), g)
    return analyse["hiddenimports"]


def test_spec_legt_jeder_verteilung_ihren_lizenztext_bei(monkeypatch):
    """Bis 1.4.0 lagen der exe nur 13 Lizenztexte bei. Die Bauvorschrift legt jetzt
    für jede Verteilung, deren Module nach der Analyse drin sind, die Lizenzdateien
    aus der .dist-info dazu, dazu PyInstaller und Pythons LICENSE.txt."""
    hooks = types.ModuleType("PyInstaller.utils.hooks")
    hooks.collect_all = lambda name: ([], [], [])
    for name, mod in (("PyInstaller", types.ModuleType("PyInstaller")),
                      ("PyInstaller.utils", types.ModuleType("PyInstaller.utils")),
                      ("PyInstaller.utils.hooks", hooks)):
        monkeypatch.setitem(sys.modules, name, mod)
    analyse = types.SimpleNamespace(
        pure=[("yt_dlp.extractor", "x", "PYMODULE"), ("youtube_app", "y", "PYMODULE")],
        scripts=[], binaries=[], datas=[])
    g = {"__name__": "__spec__", "Analysis": lambda *a, **k: analyse,
         "PYZ": lambda *a, **k: None, "EXE": lambda *a, **k: None}
    with open(os.path.join(MODUL_DIR, "SyncYouTube.spec"), encoding="utf-8") as f:
        exec(compile(f.read(), "SyncYouTube.spec", "exec"), g)
    ziele = {ziel for ziel, quelle, art in analyse.datas
             if art == "DATA" and os.path.isfile(quelle)}
    assert any(z.startswith("lizenzen/yt-dlp/") for z in ziele), sorted(ziele)
    assert "lizenzen/python/LICENSE.txt" in ziele, sorted(ziele)
    # Nur gefundene Verteilungen: eigener Code (youtube_app) gehört zu keiner.
    assert {z.split("/")[1] for z in ziele} <= {"yt-dlp", "pyinstaller", "python"}, sorted(ziele)


def _fehlende_heisse_seiten(hiddenimports):
    """Seiten und Bausteine aus youtube_app.HEISSE_SEITEN, die nicht in den
    hiddenimports stehen (sortiert; leer = alle kommen in die exe)."""
    import youtube_app
    erwartet = {m for seite, bausteine in youtube_app.HEISSE_SEITEN.items()
                for m in (seite, *bausteine)}
    assert "fernbedienung" in erwartet, "HEISSE_SEITEN ohne fernbedienung — der Wächter wäre blind"
    return sorted(erwartet - set(hiddenimports))


def _spec_text():
    with open(os.path.join(MODUL_DIR, "SyncYouTube.spec"), encoding="utf-8") as f:
        return f.read()


def test_exe_nimmt_jede_heisse_seite_mit(monkeypatch):
    fehlend = _fehlende_heisse_seiten(_spec_hiddenimports(monkeypatch, _spec_text()))
    assert not fehlend, f"in der exe fehlten diese per Name geladenen Seiten: {fehlend}"


def test_gegenprobe_spec_ohne_fernbedienung_wird_gemeldet(monkeypatch):
    spec = _spec_text()
    ohne = re.sub(r"""['"]fernbedienung['"],?\s*""", "", spec)
    assert ohne != spec, "fernbedienung steht nicht in der spec — die Gegenprobe wäre blind"
    assert _fehlende_heisse_seiten(_spec_hiddenimports(monkeypatch, ohne)) == ["fernbedienung"]


# ------------------------------------------------- kleine Startdatei der exe
# 25.11.2026: Avira (und F-Secure mit Aviras Erkennung) meldete die exe 1.4.3 als
# „TR/ATRAPS.Gen“. Probebauten grenzten es ein: PyInstaller legt das Startskript
# als eigenen Block in die exe; jeder Bau mit einem Startskript unter 512 KiB war
# sauber, jeder ab 512 KiB gemeldet (auch 1.4.1 mit bloßem Fülltext), und mit der
# kleinen Startdatei start_exe.py war 1.4.3 wieder sauber. youtube_app.py selbst
# ist größer; es liegt seither im Python-Archiv wie jedes andere Modul.

AVIRA_GRENZE = 512 * 1024


def _spec_startskripte(monkeypatch):
    hooks = types.ModuleType("PyInstaller.utils.hooks")
    hooks.collect_all = lambda name: ([], [], [])
    for name, mod in (("PyInstaller", types.ModuleType("PyInstaller")),
                      ("PyInstaller.utils", types.ModuleType("PyInstaller.utils")),
                      ("PyInstaller.utils.hooks", hooks)):
        monkeypatch.setitem(sys.modules, name, mod)
    gefunden = []

    def Analysis(skripte, **kw):
        gefunden.extend(skripte)
        return types.SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])
    g = {"__name__": "__spec__", "Analysis": Analysis,
         "PYZ": lambda *a, **k: None, "EXE": lambda *a, **k: None}
    exec(compile(_spec_text(), "SyncYouTube.spec", "exec"), g)
    return gefunden


def test_exe_startet_ueber_kleine_startdatei(monkeypatch):
    import marshal
    assert _spec_startskripte(monkeypatch) == ["start_exe.py"]
    pfad = os.path.join(MODUL_DIR, "start_exe.py")
    with open(pfad, encoding="utf-8") as f:
        quelle = f.read()
    # So groß wird der Block in der exe (PyInstaller packt den marshal-Code).
    groesse = len(marshal.dumps(compile(quelle, pfad, "exec")))
    assert groesse < AVIRA_GRENZE // 8, groesse
    # Die Startdatei tut nichts als youtube_app laden und main() rufen.
    baum = ast.parse(quelle)
    befehle = [k for k in baum.body if not (isinstance(k, ast.Expr)
                                            and isinstance(k.value, ast.Constant))]
    assert ast.unparse(ast.Module(body=befehle, type_ignores=[])) == \
        "import youtube_app\nyoutube_app.main()"


def test_startdatei_kommt_nicht_ins_quellstart_paket():
    spec = importlib.util.spec_from_file_location(
        "quellstart_paket_startdatei", os.path.join(MODUL_DIR, "tools", "quellstart_paket.py"))
    qp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qp)
    assert not qp._wird_ausgeliefert("System/start_exe.py")
    assert qp._wird_ausgeliefert("System/youtube_app.py")


# ------------------------------------------- Teile der Oberfläche in der exe
# Strukturumbau 25.11.2026: oberflaeche.py setzt die Seite aus pc_oberflaeche/ und
# layout_kern.js zusammen. Fehlt eines davon in der exe, startet sie ohne
# Oberfläche; darum prüft der Bau die Bauliste und bricht ab.

def test_oberflaeche_fehlt_nennt_jedes_fehlende_teil(br, tmp_path):
    alle = _oberflaeche_eintraege()
    assert len(alle) >= 20, "Auto-Discovery der Oberflächen-Teile ist blind"
    assert br.oberflaeche_fehlt(_bauliste(tmp_path / "voll.toc", alle)) == []
    ohne = [e for e in alle if not e[0].endswith("stil.css")]
    assert br.oberflaeche_fehlt(_bauliste(tmp_path / "ohne.toc", ohne)) == ["pc_oberflaeche/stil.css"]
    ohne_kern = [e for e in alle if e[0] != "layout_kern.js"]
    assert br.oberflaeche_fehlt(_bauliste(tmp_path / "ohne_kern.toc", ohne_kern)) == ["layout_kern.js"]
    assert br.oberflaeche_fehlt(str(tmp_path / "gibt_es_nicht.toc")), "fail-closed verletzt"


def test_bauen_bricht_ab_wenn_ein_teil_der_oberflaeche_fehlt(br, monkeypatch, tmp_path):
    monkeypatch.setattr(br.subprocess, "run", lambda befehl, **kw: types.SimpleNamespace(returncode=0))
    exe = tmp_path / "SyncYouTube.exe"
    exe.write_bytes(b"MZ")
    monkeypatch.setattr(br, "GEBAUT", str(exe))
    ohne = [e for e in _vollstaendig(br) if not e[0].endswith("17_init.js")]
    monkeypatch.setattr(br, "BAULISTE", _bauliste(tmp_path / "PKG-00.toc", ohne))
    with pytest.raises(SystemExit) as abbruch:
        br.bauen()
    assert "pc_oberflaeche/skript/17_init.js" in str(abbruch.value)


def test_spec_nimmt_die_oberflaeche_als_daten_mit():
    text = _spec_text()
    assert "('pc_oberflaeche', 'pc_oberflaeche')" in text
    assert "('layout_kern.js', '.')" in text
