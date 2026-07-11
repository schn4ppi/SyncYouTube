# -*- coding: utf-8 -*-
"""AMO-Automatik: lädt das Firefox-Addon per Mozilla-API hoch (statt Klickerei im Browser).

addons.mozilla.org hat eine offizielle API mit JWT-Auth. Damit macht dieses
Skript den kompletten Einreichungs-Weg von der Kommandozeile:

  1. neuestes dist/ytdl-firefox-v*.zip hochladen (Validierung läuft serverseitig)
  2. warten bis die Validierung durch ist (muss "valid" sein)
  3. daraus eine neue Version des Add-ons anlegen
  4. Status melden — gelistet: "wartet auf Mozilla-Prüfung";
     ungelistet (selbst verteilt): wartet aufs Auto-Signieren und lädt die
     fertige, dauerhaft installierbare .xpi nach dist/ herunter.

EINMALIGE Einrichtung (macht JB selbst, das Skript sieht das Secret nur beim
Speichern in den Windows-Anmeldeinformationsspeicher — nie in Dateien/Logs):

  1. https://addons.mozilla.org/de/developers/addon/api/key/  → Schlüssel erzeugen
  2. python amo_sign.py --schluessel   → JWT-Aussteller + Secret eingeben (unsichtbar)

Aufrufe (mit dem Core-venv-Python):
  python amo_sign.py                     # hochladen, Kanal wie letzte Version (listed)
  python amo_sign.py --kanal unlisted    # selbst verteilt: auto-signiert + .xpi-Download
  python amo_sign.py --status            # Versionen + Prüf-Status anzeigen
  python amo_sign.py --schluessel        # API-Schlüssel im Keyring hinterlegen

Sicherheit: Secrets NUR im Windows-Keyring (Suite-Regel), JWT lebt 5 Minuten,
nichts davon wird ausgegeben oder geloggt.
"""
import argparse
import base64
import glob
import hashlib
import hmac
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://addons.mozilla.org/api/v5"
GUID = "youtube-downloader@jbk.local"          # gecko-id aus build.py/manifest
KEYRING_DIENST = "SyncYouTube-AMO"             # Windows-Anmeldeinformationsspeicher


# ---------------------------------------------------------------- Schlüssel --

def _keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        sys.exit("keyring fehlt — bitte mit dem Core-venv-Python starten "
                 "(Core/venv/Scripts/python.exe amo_sign.py …)")


def schluessel_speichern():
    """Fragt JWT-Aussteller + Secret ab (Eingabe unsichtbar) und legt beide im Keyring ab."""
    import getpass
    kr = _keyring()
    print("AMO-API-Schlüssel hinterlegen (von "
          "https://addons.mozilla.org/de/developers/addon/api/key/ ):")
    issuer = input("  JWT-Aussteller (user:…): ").strip()
    secret = getpass.getpass("  JWT-Secret (Eingabe bleibt unsichtbar): ").strip()
    if not issuer or not secret:
        sys.exit("Abbruch: beide Werte werden gebraucht.")
    kr.set_password(KEYRING_DIENST, "jwt-issuer", issuer)
    kr.set_password(KEYRING_DIENST, "jwt-secret", secret)
    print("Gespeichert im Windows-Anmeldeinformationsspeicher "
          f"(Dienst '{KEYRING_DIENST}'). Test: python amo_sign.py --status")


def schluessel_laden():
    kr = _keyring()
    issuer = kr.get_password(KEYRING_DIENST, "jwt-issuer")
    secret = kr.get_password(KEYRING_DIENST, "jwt-secret")
    if not issuer or not secret:
        sys.exit("Keine AMO-Schlüssel im Keyring. Einmalig einrichten:\n"
                 "  1. https://addons.mozilla.org/de/developers/addon/api/key/\n"
                 "  2. python amo_sign.py --schluessel")
    return issuer, secret


# ---------------------------------------------------------------------- JWT --

def _b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=")


def jwt_bauen(issuer, secret, jetzt=None):
    """HS256-JWT wie von AMO verlangt (iat/exp, max. 5 Minuten gültig) — reine stdlib."""
    jetzt = int(jetzt if jetzt is not None else time.time())
    kopf = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    inhalt = _b64url(json.dumps({
        "iss": issuer, "jti": str(uuid.uuid4()),
        "iat": jetzt, "exp": jetzt + 300,
    }).encode())
    signatur = _b64url(hmac.new(secret.encode(), kopf + b"." + inhalt, hashlib.sha256).digest())
    return (kopf + b"." + inhalt + b"." + signatur).decode()


# ---------------------------------------------------------------- HTTP-Kern --

def _api(pfad, methode="GET", json_daten=None, datei=None, felder=None, roh_url=None):
    """Ein API-Aufruf mit frischem JWT. datei=(feldname, pfad) macht multipart."""
    issuer, secret = schluessel_laden()
    kopf = {"Authorization": "JWT " + jwt_bauen(issuer, secret),
            "User-Agent": "SyncYouTube-amo-sign"}
    daten = None
    if datei:
        rand = uuid.uuid4().hex
        buf = io.BytesIO()
        for name, wert in (felder or {}).items():
            buf.write((f"--{rand}\r\nContent-Disposition: form-data; "
                       f"name=\"{name}\"\r\n\r\n{wert}\r\n").encode())
        feldname, dpfad = datei
        with open(dpfad, "rb") as f:
            buf.write((f"--{rand}\r\nContent-Disposition: form-data; name=\"{feldname}\"; "
                       f"filename=\"{os.path.basename(dpfad)}\"\r\n"
                       f"Content-Type: application/zip\r\n\r\n").encode())
            buf.write(f.read())
        buf.write(f"\r\n--{rand}--\r\n".encode())
        daten = buf.getvalue()
        kopf["Content-Type"] = f"multipart/form-data; boundary={rand}"
    elif json_daten is not None:
        daten = json.dumps(json_daten).encode()
        kopf["Content-Type"] = "application/json"
    url = roh_url or (API + pfad)
    req = urllib.request.Request(url, data=daten, method=methode, headers=kopf)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        sys.exit(f"AMO-Fehler {e.code} bei {methode} {pfad or url}:\n{detail}")
    if roh_url:                       # Datei-Download: Bytes zurück
        return body
    return json.loads(body) if body.strip() else {}


# ------------------------------------------------------------------- Ablauf --

def neuestes_zip():
    zips = sorted(glob.glob(os.path.join(HERE, "dist", "ytdl-firefox-v*.zip")))
    if not zips:
        sys.exit("Kein dist/ytdl-firefox-v*.zip — erst 'python build.py' laufen lassen.")
    return zips[-1]


def hochladen(kanal):
    zpfad = neuestes_zip()
    print(f"Lade hoch: {os.path.basename(zpfad)}  (Kanal: {kanal})")
    up = _api("/addons/upload/", "POST", datei=("upload", zpfad), felder={"channel": kanal})
    uid = up["uuid"]
    print("  Upload angenommen, warte auf serverseitige Validierung …")
    for _ in range(60):                       # bis ~5 Minuten
        time.sleep(5)
        up = _api(f"/addons/upload/{uid}/")
        if up.get("processed"):
            break
        print("  … validiert noch")
    if not up.get("processed"):
        sys.exit("Validierung nach 5 Minuten nicht fertig — später mit --status prüfen.")
    v = up.get("validation") or {}
    print(f"  Validierung: {v.get('errors', '?')} Fehler, {v.get('warnings', '?')} Warnungen")
    if not up.get("valid"):
        sys.exit("Validierung FEHLGESCHLAGEN — Details in der Entwicklerecke ansehen.")
    version = _api(f"/addons/addon/{GUID}/versions/", "POST", json_daten={"upload": uid})
    vid, vnum = version["id"], version["version"]
    print(f"  Version {vnum} angelegt (id {vid}).")
    if kanal == "listed":
        print("Fertig: Version eingereicht — wartet jetzt auf Mozillas Prüfung "
              "(Status: python amo_sign.py --status).")
        return
    # unlisted: Auto-Signierung abwarten, fertige .xpi holen
    print("  Warte aufs Auto-Signieren (selbst verteilter Kanal) …")
    for _ in range(60):
        time.sleep(10)
        version = _api(f"/addons/addon/{GUID}/versions/{vid}/")
        datei = version.get("file") or {}
        if datei.get("status") == "public":
            ziel = os.path.join(HERE, "dist", f"ytdl-firefox-v{vnum}-signiert.xpi")
            with open(ziel, "wb") as f:
                f.write(_api("", roh_url=datei["url"]))
            print(f"Fertig: signierte Datei -> dist/{os.path.basename(ziel)}\n"
                  "Die .xpi ist dauerhaft in Firefox installierbar (Datei ins "
                  "Add-ons-Fenster ziehen) und darf mit ins GitHub-Release.")
            return
        print(f"  … Status: {datei.get('status', '?')}")
    sys.exit("Signierung nach 10 Minuten nicht fertig — später mit --status prüfen.")


def status_zeigen():
    daten = _api(f"/addons/addon/{GUID}/versions/?filter=all_with_unlisted")
    print(f"Versionen von {GUID}:")
    for v in daten.get("results", []):
        datei = v.get("file") or {}
        print(f"  {v.get('version'):8s}  Kanal={v.get('channel', '?'):8s}  "
              f"Datei-Status={datei.get('status', '?')}")


def xpi_holen():
    """Lädt die neueste fertig signierte .xpi nach dist/ (Status 'public' = signiert)."""
    daten = _api(f"/addons/addon/{GUID}/versions/?filter=all_with_unlisted")
    for v in daten.get("results", []):
        datei = v.get("file") or {}
        if datei.get("status") == "public" and datei.get("url"):
            ziel = os.path.join(HERE, "dist", f"ytdl-firefox-v{v['version']}-signiert.xpi")
            with open(ziel, "wb") as f:
                f.write(_api("", roh_url=datei["url"]))
            print(f"Signierte Datei -> dist/{os.path.basename(ziel)} "
                  f"({os.path.getsize(ziel)} Bytes)\n"
                  "Dauerhaft installieren: Datei in Firefox auf about:addons ziehen.")
            return
    sys.exit("Keine fertig signierte Version gefunden (Status mit --status prüfen).")


def main():
    p = argparse.ArgumentParser(description="Firefox-Addon automatisch bei AMO einreichen")
    p.add_argument("--schluessel", action="store_true", help="API-Schlüssel im Keyring hinterlegen")
    p.add_argument("--status", action="store_true", help="Versionen + Status anzeigen")
    p.add_argument("--holen", action="store_true", help="neueste signierte .xpi nach dist/ laden")
    p.add_argument("--kanal", choices=["listed", "unlisted"], default="listed",
                   help="listed = öffentliche AMO-Seite (Mozilla prüft), "
                        "unlisted = selbst verteilt (auto-signiert, .xpi-Download)")
    args = p.parse_args()
    if args.schluessel:
        schluessel_speichern()
    elif args.status:
        status_zeigen()
    elif args.holen:
        xpi_holen()
    else:
        hochladen(args.kanal)


if __name__ == "__main__":
    main()
