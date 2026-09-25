# -*- coding: utf-8 -*-
"""Selbst-Update: Signatur Pflicht, fehlende Prüfsumme bricht ab (JB-Entscheid 7a
Punkt 6, Gesamtprüfung S9, 25.09.2026).

Vorher prüfte der Updater nur Größe und SHA-256 aus DEMSELBEN Release; fehlte
die `.sha256`, lief er still mit der Größenprüfung weiter. Wer das Release
austauschen konnte, brachte so eigenen Code auf jede exe-Installation. Jetzt:
  * ohne `.sha256` (fehlt, nicht ladbar, ohne Prüfsumme darin) kein Tausch;
  * die neue exe muss eine gültige Authenticode-Signatur tragen (WinVerifyTrust
    über ctypes, kein Kindprozess, keine neue Abhängigkeit);
  * ihr Signierer (Inhaber und Aussteller des Zertifikats) muss dem der
    laufenden exe gleichen.
Eine verworfene Datei liegt nie unter dem Zielnamen; sie bleibt als
`SyncYouTube_neu.exe.verworfen` liegen (nichts wird gelöscht).

Die Entscheidung läuft mit Attrappen der WinVerifyTrust-Antwort. Der echte
ctypes-Aufruf wird zusätzlich an einer echt signierten Datei gemessen (der
laufende Python), und zwar nur lokal: ohne Sperrlisten-Abruf und nur aus dem
Zwischenspeicher, also ohne Netz. Die Fassung mit Sperrlisten-Abruf
(`authenticode_online`) sperrt die conftest wie jede andere Netzfunktion.
"""
import hashlib
import os
import shutil
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import update  # noqa: E402

TRUST_E_NOSIGNATURE = 0x800B0100
JB = ("CN=Herausgeber, O=Herausgeber", "CN=Code Signing CA, O=Zertifizierer")
FREMD = ("CN=Jemand anderes, O=Jemand anderes", "CN=Code Signing CA, O=Zertifizierer")
DATEN = b"MZ" + b"x" * 62


@pytest.fixture
def umgebung(monkeypatch, tmp_path):
    """Kleine Mindestgröße, Netz-Attrappe, laufende exe in tmp_path. Die
    WinVerifyTrust-Antwort je Datei steht in `antworten` (Pfad-Endung → Antwort)."""
    monkeypatch.setattr(update, "MIN_EXE_SIZE", 16)
    laufend = tmp_path / "prog" / "SyncYouTube.exe"
    laufend.parent.mkdir()
    laufend.write_bytes(b"MZ alt")
    monkeypatch.setattr(update, "frozen_exe", lambda: str(laufend))
    antworten = {"laufend": (0, JB), "neu": (0, JB)}
    gefragt = []

    def antwort(pfad, offline):
        gefragt.append((os.path.basename(pfad), offline))
        wer = "laufend" if os.path.abspath(pfad) == os.path.abspath(str(laufend)) else "neu"
        a = antworten[wer]
        if isinstance(a, Exception):
            raise a
        return a

    monkeypatch.setattr(update, "authenticode_online", lambda p: antwort(p, False), raising=False)
    monkeypatch.setattr(update, "authenticode_offline", lambda p: antwort(p, True), raising=False)
    netz = {"https://x/exe": DATEN,
            "https://x/sha": (hashlib.sha256(DATEN).hexdigest() + "  SyncYouTube.exe\n").encode()}

    def fetch(url):
        if isinstance(netz.get(url), Exception):
            raise netz[url]
        return netz[url]
    info = {"exe_url": "https://x/exe", "sha_url": "https://x/sha", "size": len(DATEN)}
    return {"ziel": str(laufend.parent), "antworten": antworten, "netz": netz, "fetch": fetch,
            "info": info, "gefragt": gefragt}


def _ziel(u):
    return os.path.join(u["ziel"], "SyncYouTube_neu.exe")


def _abgelehnt(u, info=None):
    with pytest.raises(ValueError) as fehler:
        update.download_exe(info or u["info"], u["ziel"], fetch=u["fetch"])
    assert not os.path.exists(_ziel(u)), "eine verworfene exe darf nie unter dem Zielnamen liegen"
    return str(fehler.value)


def test_gueltig_signiert_vom_selben_herausgeber_wird_getauscht(umgebung):
    pfad = update.download_exe(umgebung["info"], umgebung["ziel"], fetch=umgebung["fetch"])
    assert pfad == _ziel(umgebung)
    with open(pfad, "rb") as f:
        assert f.read() == DATEN
    # die neue Datei wird mit Sperrlisten-Abruf geprüft, die laufende nur lokal
    assert ("SyncYouTube_neu.exe.tmp", False) in umgebung["gefragt"]
    assert ("SyncYouTube.exe", True) in umgebung["gefragt"]


def test_fehlende_pruefsumme_bricht_ab(umgebung):
    ohne = dict(umgebung["info"], sha_url="")
    assert "Prüfsumme" in _abgelehnt(umgebung, ohne)


def test_nicht_ladbare_pruefsumme_bricht_ab(umgebung):
    umgebung["netz"]["https://x/sha"] = OSError("abgebrochen")
    assert "Prüfsumme" in _abgelehnt(umgebung)


def test_pruefsummen_datei_ohne_pruefsumme_bricht_ab(umgebung):
    umgebung["netz"]["https://x/sha"] = b"nichts Brauchbares"
    assert "Prüfsumme" in _abgelehnt(umgebung)


def test_unsignierte_exe_wird_verworfen(umgebung):
    umgebung["antworten"]["neu"] = (TRUST_E_NOSIGNATURE, None)
    grund = _abgelehnt(umgebung)
    assert "Signatur" in grund and "0x800B0100" in grund
    verworfen = _ziel(umgebung) + ".verworfen"
    assert os.path.exists(verworfen), "die verworfene Datei bleibt liegen, sie wird nicht gelöscht"


def test_anderer_signierer_wird_verworfen(umgebung):
    umgebung["antworten"]["neu"] = (0, FREMD)
    grund = _abgelehnt(umgebung)
    assert "Jemand anderes" in grund


def test_anderer_aussteller_wird_verworfen(umgebung):
    umgebung["antworten"]["neu"] = (0, (JB[0], "CN=Andere CA"))
    assert "Aussteller" in _abgelehnt(umgebung)


def test_ohne_signierte_laufende_exe_kein_vergleich_kein_tausch(umgebung):
    umgebung["antworten"]["laufend"] = (TRUST_E_NOSIGNATURE, None)
    assert "laufende" in _abgelehnt(umgebung)


def test_fehler_der_pruefung_bricht_ab(umgebung):
    umgebung["antworten"]["neu"] = OSError("wintrust.dll nicht ladbar")
    assert "Signatur" in _abgelehnt(umgebung)


def test_ohne_laufende_exe_kein_tausch(umgebung, monkeypatch):
    monkeypatch.setattr(update, "frozen_exe", lambda: None)
    _abgelehnt(umgebung)


def test_falsche_pruefsumme_prueft_gar_nicht_erst_die_signatur(umgebung):
    umgebung["netz"]["https://x/sha"] = b"0" * 64
    assert "SHA256" in _abgelehnt(umgebung)
    assert umgebung["gefragt"] == []


# ------------------------------------------------ der echte ctypes-Aufruf, lokal

def _echt_signiert():
    """Eine echt Authenticode-signierte exe dieses Rechners: der laufende Python
    (python.org signiert ihn). Fehlt die Signatur, ist der Test hier nicht messbar."""
    code, wer = update.authenticode_offline(sys.executable)
    if code != 0 or not wer:
        pytest.skip(f"{sys.executable} ist hier nicht signiert (0x{code:08X})")
    return sys.executable, wer


def test_echter_aufruf_liest_signierer_der_laufenden_datei():
    _, (inhaber, aussteller) = _echt_signiert()
    assert "CN=" in inhaber and "CN=" in aussteller and inhaber != aussteller


def test_echter_aufruf_erkennt_unsignierte_und_veraenderte_datei(tmp_path):
    quelle, _ = _echt_signiert()
    leer = tmp_path / "unsigniert.exe"
    leer.write_bytes(b"MZ" + b"\0" * 1022)
    code, wer = update.authenticode_offline(str(leer))
    assert code != 0 and wer is None
    kopie = tmp_path / "veraendert.exe"
    shutil.copyfile(quelle, kopie)
    roh = bytearray(kopie.read_bytes())
    roh[len(roh) // 3] ^= 0xFF                      # ein Byte mitten im signierten Teil
    kopie.write_bytes(bytes(roh))
    code, wer = update.authenticode_offline(str(kopie))
    assert code != 0 and wer is None, f"veränderte Datei galt als gültig (0x{code:08X})"


def test_echte_pruefung_am_zwischennamen(tmp_path, monkeypatch):
    """Der ganze Weg mit echtem WinVerifyTrust: eine Kopie der signierten Datei
    unter dem Zwischennamen `.tmp` gegen das Original als laufende exe."""
    quelle, _ = _echt_signiert()
    monkeypatch.setattr(update, "authenticode_online", update.authenticode_offline)  # kein Netz im Test
    kopie = tmp_path / "SyncYouTube_neu.exe.tmp"
    shutil.copyfile(quelle, kopie)
    assert update.signatur_pruefen(str(kopie), quelle) == (True, "")
    fremd = tmp_path / "fremd.exe"
    fremd.write_bytes(b"MZ" + b"\0" * 1022)
    ok, grund = update.signatur_pruefen(str(kopie), str(fremd))
    assert ok is False and "laufende" in grund
