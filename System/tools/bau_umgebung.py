# -*- coding: utf-8 -*-
"""Die Bau-Umgebung `System\\bau_venv` aus `bau_pakete.py` neu aufbauen.

Ein eigenes Python (`System\\bau_python`, entpackt mit
`py install --target=System\\bau_python 3.14.10`, ohne Anmeldung im System)
und eine eigene venv, in der NUR die Pakete aus bau_pakete.py liegen. Danach
schreibt das Werkzeug `bau_stand.txt`: was die Umgebung wirklich enthält,
samt allen mitgezogenen Paketen. Das ist der Stand, den exe und Quellstart
bündeln, und der Bau prüft ihn vor jedem Lauf (bau_pakete.abweichungen).

Eine vorhandene venv wird nicht überschrieben: sie kommt in den Papierkorb
(mit derselben Platzprüfung wie das Löschen in der App), und die neue entsteht
frisch, damit nichts Altes darin liegen bleibt.

Aufruf (aus SyncYouTube\\System):
    bau_python\\python.exe tools\\bau_umgebung.py
Danach bauen:
    bau_venv\\Scripts\\python.exe tools\\quellstart_paket.py
    bau_venv\\Scripts\\python.exe build_release.py
"""
import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
SYSTEM = os.path.dirname(HIER)
sys.path.insert(0, HIER)
import bau_pakete  # noqa: E402

BAU_PYTHON = os.path.join(SYSTEM, "bau_python", "python.exe")
VENV = os.path.join(SYSTEM, "bau_venv")
VENV_PYTHON = os.path.join(VENV, "Scripts", "python.exe")


def ordner_in_papierkorb(pfad):
    """Einen Bau-Ordner in den Windows-Papierkorb legen, nie endgültig löschen.
    Nutzt die Prüfungen der App: passt er nicht in den Papierkorb, bleibt er liegen."""
    sys.path.insert(0, SYSTEM)
    import youtube_app as app
    groesse = sum(os.path.getsize(os.path.join(w, d))
                  for w, _, dateien in os.walk(pfad) for d in dateien)
    if not app._papierkorb_platz(pfad, groesse):
        return f"bleibt liegen, der Papierkorb nimmt {groesse / 2**20:.0f} MB nicht sicher auf: {pfad}"
    if not app._in_papierkorb(pfad) or os.path.exists(pfad):
        return f"bleibt liegen, Windows hat ihn nicht in den Papierkorb gelegt: {pfad}"
    return None


def _pip(*argumente):
    subprocess.run([VENV_PYTHON, "-m", "pip", "--isolated", "--disable-pip-version-check",
                    *argumente], check=True)


def main():
    if not os.path.isfile(BAU_PYTHON):
        sys.exit(f"{BAU_PYTHON} fehlt. Erst: py install --target=System\\bau_python 3.14.10")
    if os.path.exists(VENV):
        befund = ordner_in_papierkorb(VENV)
        if befund:
            sys.exit(befund)
        print(f"Alte Bau-Umgebung liegt im Papierkorb: {VENV}")
    subprocess.run([BAU_PYTHON, "-m", "venv", VENV], check=True)
    _pip("install", "--upgrade", "pip")
    _pip("install", *bau_pakete.pip_format(), *bau_pakete.LAUFZEIT, *bau_pakete.WERKSTATT)
    stand = subprocess.run([VENV_PYTHON, "-m", "pip", "--isolated", "freeze",
                            "--disable-pip-version-check"],
                           check=True, capture_output=True, text=True).stdout
    with open(bau_pakete.STAND_DATEI, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Erzeugt von tools/bau_umgebung.py: was System\\bau_venv enthält.\n"
                "# Von Hand nichts ändern; Fassungen stehen in tools/bau_pakete.py.\n")
        f.write(stand)
    print(f"Bau-Umgebung steht: {VENV}")
    print(f"Stand geschrieben: {bau_pakete.STAND_DATEI}")


if __name__ == "__main__":
    main()
