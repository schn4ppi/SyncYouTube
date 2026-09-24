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
    signiert = []
    monkeypatch.setattr(br.signieren, "signiere",
                        lambda pfad, **kw: signiert.append(pfad) or "signiert", raising=False)
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
