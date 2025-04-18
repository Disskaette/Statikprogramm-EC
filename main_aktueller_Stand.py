# main.py

"""
Hauptmodul der Statik-App.
Startet die grafische Benutzeroberfläche (GUI).
Andere Module wie Berechnung, Zeichnung und Export
werden später eingebunden.
"""

import tkinter as tk
from gui.eingabemaske import starte_gui
from backups.statik_modul import berechne_und_zeichne


def main():
    """
    Einstiegspunkt der Anwendung. Startet die GUI.
    """
    starte_gui()


def statik_berechnen(self):
    spannweiten = [float(e.get().replace(",", "."))
                   for e in self.spannweiten_eingaben]
    lasten = [float(e["wert"].get().replace(",", "."))
              for e in self.lasten_eingaben]
    berechne_und_zeichne(spannweiten, lasten)


if __name__ == "__main__":
    main()
