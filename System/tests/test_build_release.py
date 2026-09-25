# -*- coding: utf-8 -*-
"""build_release.py: Erzeugnis-Prüfung nach dem PyInstaller-Schritt (24.09.2026).

Befund 2b der Analyse „auslieferung": winrt steht in der exe-BAUVORSCHRIFT
(SyncYouTube.spec, belegt von test_exe_nimmt_pywinrt_mit mit Attrappen), aber in
keiner gebauten exe — die letzte Bauliste (08.09.) enthält 0 winrt-Einträge.
Ein Wächter, der die Vorschrift ausführt, beweist nicht die gebaute Datei.
Darum prüft build_release.py jetzt die BAULISTE (PKG-00.toc, was wirklich in die
exe gepackt wird) an den QUELLPFADEN (Muster eingebackene_namen im Familien-
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
SMTC_PFAD = os.path.join(MODUL_DIR, "medien_smtc.py")
SITE = r"C:\venv\Lib\site-packages"


@pytest.fixture
def br(monkeypatch):
    # signieren liegt in der Familie (SyncDashTray) und fasst den Token an — nie im Test.
    monkeypatch.setitem(sys.modules, "signieren", types.ModuleType("signieren"))
    spec = importlib.util.spec_from_file_location(
        "build_release_unter_test", os.path.join(MODUL_DIR, "build_release.py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _winrt_importe():
    baum = ast.parse(open(SMTC_PFAD, encoding="utf-8").read())
    genutzt = set()
    for n in ast.walk(baum):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("winrt"):
            genutzt.add(n.module)
    assert genutzt, "Auto-Discovery findet keine winrt-Importe — der Wächter wäre blind"
    return genutzt


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


def _vollstaendig(br):
    teile = [_eintrag(f"winrt/{e}.cp314-win_amd64.pyd") for e in br.winrt_erweiterungen()]
    return teile + [_eintrag("winrt/msvcp140.dll", "BINARY")]


def test_erwartete_winrt_teile_kommen_aus_medien_smtc(br, tmp_path):
    # Auto-Discovery: aus den Importen von medien_smtc über die Paket-Quellen der
    # venv zu den Binärerweiterungen — nicht aus einer Handliste.
    namen = br.winrt_erweiterungen()
    assert len(namen) >= len(_winrt_importe()), namen
    winrt_ordner = os.path.dirname(importlib.util.find_spec("winrt.runtime").origin)
    winrt_ordner = os.path.dirname(winrt_ordner)
    vorhanden = os.listdir(winrt_ordner)
    for name in namen:
        assert any(d.startswith(name + ".") and d.endswith(".pyd") for d in vorhanden), \
            f"{name}: keine .pyd dieses Namens in {winrt_ordner}"
    # Gegenstück: nutzt der Server nur EIN Modul, wird auch nur dessen Teil erwartet.
    klein = tmp_path / "medien_smtc.py"
    klein.write_text("from winrt.windows.foundation import Uri\n", encoding="utf-8")
    assert br.winrt_erweiterungen(str(klein)) == {"_winrt_windows_foundation"}


def test_vollstaendige_bauliste_besteht(br, tmp_path):
    assert br.erzeugnis_pruefen(_bauliste(tmp_path / "PKG-00.toc", _vollstaendig(br))) == []


def test_jedes_fehlende_teil_wird_gemeldet(br, tmp_path):
    voll = _vollstaendig(br)
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
    assert br.erzeugnis_pruefen(_bauliste(tmp_path / "PKG-00.toc", rest)) == ["msvcp140.dll"]


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
# JB-Entscheid 25.09.2026: Das Selbst-Update tauscht nur noch signierte exe.
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


def test_mit_token_signiert_und_kopiert(br, monkeypatch, tmp_path):
    signiert = _signier_attrappe(br, monkeypatch, token=True)
    aufrufe, exe, oben = _bau_umgebung(br, monkeypatch, tmp_path, ["build_release.py"])
    br.main()
    assert signiert == [str(exe)]
    assert sorted(os.listdir(oben)) == ["SyncYouTube.exe", "SyncYouTube.exe.sha256"]


# ------------------------------------------ Schnittstelle zu signieren.py der Familie
# Die Bau-Tests ersetzen `signieren` durch ein leeres Modul (es fasst den Token
# an). Drifteten Namen oder Parameter der Familien-Datei, blieben sie alle grün,
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


def test_signieren_der_familie_passt_zum_bau(br):
    nutzung = _nutzung_im_bau()
    assert "signiere_pflicht" in nutzung and nutzung["signiere_pflicht"], \
        "Auto-Discovery findet den Signier-Aufruf nicht — der Wächter wäre blind"
    pfad = os.path.join(br.FAMILIE, "signieren.py")
    if not os.path.exists(pfad):
        pytest.skip(f"{pfad} fehlt (Repo allein ausgecheckt, ohne die Familie)")
    assert _abweichungen(pfad, nutzung) == [], "signieren.py der Familie passt nicht mehr zu build_release.py"


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
