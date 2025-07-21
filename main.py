from backend.service.project_service import load_project
from frontend.gui.eingabemaske import Eingabemaske
import customtkinter as ctk
import sys
import os
import logging


#!/usr/bin/env python3

# Pfad anpassen, damit Backend/Frontend-Module gefunden werden
sys.path.append(os.path.dirname(__file__))


def main():
    # CustomTkinter Theme
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # Hauptfenster erstellen
    root = ctk.CTk()
    app = Eingabemaske(root)

    # Automatisches Laden des letzten Snapshots (state.json)
    project_folder = os.getcwd()
    default_state = os.path.join(project_folder, "state.json")
    if os.path.isfile(default_state):
        try:
            state = load_project(default_state)
            app.apply_state(state)
        except Exception as e:
            print(f"⚠️ Konnte letzten Zustand nicht laden: {e}")

    # GUI starten
    root.mainloop()


if __name__ == "__main__":
    main()
