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
import struct
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
    WinVerifyTrust-Antwort je Datei steht in `antworten` (Pfad-Endung → Antwort).
    Die Test-Dateien sind keine echten exe: die Aufbau-Prüfung des Signaturblocks
    gilt hier als bestanden; echt gemessen wird sie unten an Kopien der
    signierten python.exe. `geladen` zeichnet jeden Abruf auf."""
    monkeypatch.setattr(update, "MIN_EXE_SIZE", 16)
    monkeypatch.setattr(update, "signaturblock_pruefen", lambda p: (True, ""), raising=False)
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

    geladen = []

    def fetch(url):
        geladen.append(url)
        if isinstance(netz.get(url), Exception):
            raise netz[url]
        return netz[url]
    info = {"exe_url": "https://x/exe", "sha_url": "https://x/sha", "size": len(DATEN)}
    return {"ziel": str(laufend.parent), "antworten": antworten, "netz": netz, "fetch": fetch,
            "info": info, "gefragt": gefragt, "geladen": geladen}


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
    # gefragt wurde nur die laufende exe (vor dem Laden), nie die neue Datei
    assert umgebung["gefragt"] == [("SyncYouTube.exe", True)]


# ------------------------------------------------ erst die eigene Signatur, dann laden
# Ist die laufende exe nicht gültig signiert (selbst gebaut), lässt sich keine
# neue mit ihr vergleichen. Vorher lud das Auto-Update trotzdem täglich die ganze
# exe, schrieb sie als .tmp und verwarf sie erst danach.

@pytest.mark.parametrize("laufend", [(TRUST_E_NOSIGNATURE, None), OSError("wintrust.dll nicht ladbar")])
def test_ohne_gueltig_signierte_laufende_exe_wird_nicht_geladen(umgebung, laufend):
    umgebung["antworten"]["laufend"] = laufend
    grund = _abgelehnt(umgebung)
    assert umgebung["geladen"] == [], f"trotzdem geladen: {umgebung['geladen']}"
    assert "laufende" in grund and "nicht geladen" in grund, grund
    assert os.listdir(umgebung["ziel"]) == ["SyncYouTube.exe"], "kein .tmp und kein .verworfen"


@pytest.mark.parametrize("code", [0x800B010E, 0x80092013, 0x80092012])
def test_sperrliste_nicht_erreichbar_sagt_es_deutlich(umgebung, code):
    """Die neue exe wird samt Sperrlisten geprüft (Netz). Sind die Server der
    Zertifizierungsstelle nicht erreichbar, bleibt es beim Nein (fail-closed),
    aber die Meldung nennt den Grund statt nur einer Fehlernummer."""
    umgebung["antworten"]["neu"] = (code, None)
    grund = _abgelehnt(umgebung)
    assert "Sperrliste" in grund and f"0x{code:08X}" in grund, grund


def test_ohne_laufende_exe_wird_nicht_geladen(umgebung, monkeypatch):
    monkeypatch.setattr(update, "frozen_exe", lambda: None)
    _abgelehnt(umgebung)
    assert umgebung["geladen"] == []


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


# ------------------------------------------------ Aufbau des Signaturblocks (Nacharbeit S9)
# Die Authenticode-Signatur deckt ihren eigenen Block (das PE-Sicherheits-
# verzeichnis) nicht ab. Ohne die systemweite Strengprüfung nimmt WinVerifyTrust
# eine echte signierte exe an, in deren Block hinter der Signatur weitere Bytes
# stehen. Die Aufbau-Prüfung verlangt den Block so, wie signtool ihn schreibt.

def _pe_sicherheit(roh):
    """(Offset des Verzeichnis-Eintrags, Blockanfang, Blockgröße) einer exe."""
    lfanew = struct.unpack_from("<I", roh, 0x3C)[0]
    opt = lfanew + 24
    magic = struct.unpack_from("<H", roh, opt)[0]
    eintrag = opt + (96 if magic == 0x10B else 112) + 4 * 8
    anfang, groesse = struct.unpack_from("<II", roh, eintrag)
    return eintrag, anfang, groesse


def _kopie_mit_anhang(quelle, ziel, anhang, innen=True):
    """Kopie der signierten Datei mit `anhang` am Ende. innen=True: im
    Signaturblock, Verzeichnisgröße und dwLength sind nachgezogen; sonst liegt
    der Anhang hinter dem Block."""
    roh = bytearray(open(quelle, "rb").read())
    eintrag, anfang, groesse = _pe_sicherheit(roh)
    assert anfang + groesse == len(roh), "Vorbedingung: der Block endet am Dateiende"
    roh += anhang
    if innen:
        struct.pack_into("<I", roh, eintrag + 4, groesse + len(anhang))
        dwlen = struct.unpack_from("<I", roh, anfang)[0]
        struct.pack_into("<I", roh, anfang, dwlen + len(anhang))
    ziel.write_bytes(bytes(roh))
    return str(ziel)


def test_zusatzbytes_im_signaturblock_werden_verworfen(tmp_path, monkeypatch):
    quelle, _ = _echt_signiert()
    monkeypatch.setattr(update, "authenticode_online", update.authenticode_offline)  # kein Netz im Test
    # 32 Bytes: auf 8 ausgerichtet, so nimmt WinVerifyTrust die Kopie ohne
    # Strengprüfung an (gemessen: 0x0); unausgerichtet wäre sie schon dort falsch.
    kopie = _kopie_mit_anhang(quelle, tmp_path / "SyncYouTube_neu.exe.tmp", b"ZUSATZ--" * 4)
    ok, grund = update.signatur_pruefen(kopie, quelle)
    assert ok is False, "eine signierte exe mit angehängten Daten im Signaturblock galt als gültig"
    assert "Signaturblock" in grund, grund


@pytest.mark.parametrize("fall", ["acht_nullbytes", "hinter_dem_block", "zweiter_eintrag"])
def test_aufbau_pruefung_weist_abweichungen_ab(tmp_path, fall):
    quelle, _ = _echt_signiert()
    ziel = tmp_path / "neu.exe"
    if fall == "acht_nullbytes":                      # Füllung länger als die Ausrichtung auf 8
        pfad = _kopie_mit_anhang(quelle, ziel, b"\0" * 8)
    elif fall == "hinter_dem_block":                  # Block endet nicht am Dateiende
        pfad = _kopie_mit_anhang(quelle, ziel, b"\0" * 8, innen=False)
    else:                                             # ein zweites WIN_CERTIFICATE im Block
        roh = open(quelle, "rb").read()
        _, anfang, groesse = _pe_sicherheit(roh)
        pfad = _kopie_mit_anhang(quelle, ziel, roh[anfang:anfang + groesse])
        # dwLength des ersten Eintrags bleibt die eigene Länge
        roh2 = bytearray(open(pfad, "rb").read())
        struct.pack_into("<I", roh2, anfang, groesse)
        ziel.write_bytes(bytes(roh2))
    ok, grund = update.signaturblock_pruefen(pfad)
    assert ok is False and grund, (fall, grund)


def test_aufbau_pruefung_nimmt_die_echte_signatur_an(tmp_path):
    quelle, _ = _echt_signiert()
    kopie = tmp_path / "kopie.exe"
    shutil.copyfile(quelle, kopie)
    assert update.signaturblock_pruefen(str(kopie)) == (True, "")


def test_aufbau_pruefung_ohne_exe_oder_ohne_signatur(tmp_path):
    for name, inhalt in (("leer.exe", b""), ("text.exe", b"kein Programm"),
                         ("nur_mz.exe", b"MZ" + b"\0" * 1022)):
        p = tmp_path / name
        p.write_bytes(inhalt)
        ok, grund = update.signaturblock_pruefen(str(p))
        assert ok is False and grund, (name, grund)
    ok, grund = update.signaturblock_pruefen(str(tmp_path / "gibt_es_nicht.exe"))
    assert ok is False and grund


# ------------------------------------------------ F24: Neustart mit Startargumenten

def test_neustart_nach_dem_tausch_behaelt_die_startargumente(tmp_path, monkeypatch):
    """Gesamtprüfung F24: der Neustart nach einem Update startete die exe ohne
    ihre Argumente; wer sie mit --no-browser/--no-tray betrieb, bekam danach
    Browser und Tray. Jetzt gehen sys.argv[1:] mit, wie beim Selbst-Neustart."""
    import subprocess

    class _Ende(Exception):
        pass
    laufend = tmp_path / "SyncYouTube.exe"
    laufend.write_bytes(b"MZ alt")
    neu = tmp_path / "SyncYouTube_neu.exe"
    neu.write_bytes(b"MZ neu")
    gestartet = []
    monkeypatch.setattr(subprocess, "Popen", lambda befehl, **kw: gestartet.append(list(befehl)))

    def ende(code):
        raise _Ende(code)
    monkeypatch.setattr(update.os, "_exit", ende)
    monkeypatch.setattr(sys, "argv", [str(laufend), "--no-browser", "--no-tray"])
    with pytest.raises(_Ende):
        update.apply_exe_update(str(neu), str(laufend))
    assert gestartet == [[str(laufend), "--no-browser", "--no-tray"]], gestartet
    assert laufend.read_bytes() == b"MZ neu"
