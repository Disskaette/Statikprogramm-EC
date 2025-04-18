# main.py

"""
Hauptmodul der Statik-App für Durchlaufträger im Holzbau.
Initialisiert die GUI und verbindet die Anwendungslogik mit den Modulen für
Zeichnung, Berechnung, Export und Datenmodellierung.
"""

import tkinter as tk

# GUI
from gui.eingabemaske import Eingabemaske

# Logik & Rechenmodule
from logic.berechnung import berechne_traeger
from logic.kombinationen import ermittle_lastkombinationen

# Zeichnung & Export
from grafik.zeichen import zeichne_traeger
from export.export import exportiere_pdf

# Datenmodell
from model.strukturdaten import Traeger

# Utils (z. B. für Eingabevalidierung)
from utils.helpers import komma_zu_punkt


def main():
    """
    Einstiegspunkt der Anwendung. Startet die GUI-Oberfläche.
    """
    root = tk.Tk()
    app = Eingabemaske(root)
    root.mainloop()


if __name__ == "__main__":
    main()
