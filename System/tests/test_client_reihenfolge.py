"""Angemeldet ohne Premium: yt-dlp fragt `tv_samsung` vor `web_embedded`.

BEFUND (22.11.2026, Nutzer der Release-exe 1.3.4, Firefox, bei YouTube angemeldet,
kein Premium): jeder Download endet mit »YouTube verweigert den Zugriff (403)«.
yt-dlp 2026.10.26 wählt die Player-Clients nach Konto
(`yt_dlp/extractor/youtube/_video.py`, `_get_requested_clients`):
ohne Anmeldung `tv_samsung, visionos, web`, mit Premium `web_creator, tv_samsung,
web`, angemeldet OHNE Premium `web_embedded, tv_samsung, web`. Seit Anfang November
2026 verlangt YouTube für `web_embedded` in einem A/B-Experiment ein GVS-PO-Token;
yt-dlp kennt dafür in 2026.10.26 keine Pflicht, lädt ohne Token und bekommt 403
(yt-dlp-Issue #17989). Behoben in yt-dlp master am 14.11.2026 (PR #18051, Commit
ee25591): `_DEFAULT_AUTHED_CLIENTS = ('tv_samsung', 'web_embedded', 'web')`.
yt-dlp nimmt je Format-Kennung das Format des ERSTEN Clients (`stream_ids` in
`_extract_formats_and_subtitles`), `web_embedded` füllt danach nur noch Lücken.

Die App zieht genau diese Reihenfolge nach (`youtube_app._client_reihenfolge_nachziehen`),
aber nur, solange yt-dlp noch die alte hat.

Nicht gemessen (P6): ein Download mit einem echten Gratis-Konto (Besitzer-Konto hat
Premium, dort gilt eine andere Liste), und ob YouTube das Experiment auf
`tv_samsung` ausweitet.
"""
import os
import sys

import pytest

MODUL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MODUL_DIR not in sys.path:
    sys.path.insert(0, MODUL_DIR)

import youtube_app as app  # noqa: E402
from yt_dlp.extractor.youtube import YoutubeIE  # noqa: E402

ALT = ("web_embedded", "tv_samsung", "web")
NEU = ("tv_samsung", "web_embedded", "web")


def _angefragte_clients(monkeypatch, premium):
    """Die Clients, die der echte YouTube-Extraktor aus einem App-YoutubeDL
    für ein angemeldetes Konto anfragt (ohne Netz: nur die Auswahl)."""
    monkeypatch.setattr(YoutubeIE, "is_authenticated", property(lambda self: True))
    monkeypatch.setattr(YoutubeIE, "_DEFAULT_AUTHED_CLIENTS", YoutubeIE._DEFAULT_AUTHED_CLIENTS)
    with app._ydl({"quiet": True}) as ydl:
        ie = ydl.get_info_extractor("Youtube")
        assert isinstance(ie, YoutubeIE)
        ie.initialize()                               # lokal: Cookies setzen, JS-Löser finden
        return ie._get_requested_clients(
            "https://www.youtube.com/watch?v=jNQXAC9IVRw", {}, premium)


def test_gratis_konto_fragt_tv_samsung_vor_web_embedded(monkeypatch):
    clients = _angefragte_clients(monkeypatch, premium=False)
    assert "tv_samsung" in clients and "web_embedded" in clients, clients
    assert clients.index("tv_samsung") < clients.index("web_embedded"), (
        f"Angemeldet ohne Premium fragt yt-dlp {clients}: web_embedded vor tv_samsung "
        "endet seit November 2026 im 403 (yt-dlp #17989).")


def test_premium_bleibt_unberuehrt(monkeypatch):
    assert _angefragte_clients(monkeypatch, premium=True)[0] == "web_creator"


class _Attrappe:
    pass


@pytest.mark.parametrize("vorher, nachher, geaendert", [
    (ALT, NEU, True),                                   # yt-dlp 2026.10.26: nachziehen
    (NEU, NEU, False),                                  # neueres yt-dlp: nichts tun
    (("tv_samsung", "web"), ("tv_samsung", "web"), False),   # fremde Liste: nicht anfassen
])
def test_nur_die_alte_reihenfolge_wird_getauscht(vorher, nachher, geaendert):
    ie = type("IE", (_Attrappe,), {"_DEFAULT_AUTHED_CLIENTS": vorher})
    assert app._client_reihenfolge_nachziehen(ie) is geaendert
    assert ie._DEFAULT_AUTHED_CLIENTS == nachher


def test_ohne_das_attribut_passiert_nichts():
    ie = type("IE", (_Attrappe,), {})
    assert app._client_reihenfolge_nachziehen(ie) is False
    assert not hasattr(ie, "_DEFAULT_AUTHED_CLIENTS")
