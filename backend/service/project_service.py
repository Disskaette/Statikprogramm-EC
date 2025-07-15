from typing import Any, Dict
import os
import json

"""
project_service.py

Funktionen zum Speichern und Laden des gesamten Projekt-Snapshots als JSON-Datei.
"""


def save_project(path: str, state: Dict[str, Any]) -> None:
    """
    Speichert den vollständigen Snapshot (state) in einer JSON-Datei.

    Arguments:
        path: Pfad zur Ziel-Datei (inkl. Dateiname).
        state: Dictionary mit allen Eingabe- und Konfigurationsdaten.
    """
    # Verzeichnis sicherstellen
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_project(path: str) -> Dict[str, Any]:
    """
    Lädt den Snapshot aus einer JSON-Datei und gibt ihn als Dictionary zurück.

    Arguments:
        path: Pfad zur JSON-Datei.

    Returns:
        Dictionary mit den gespeicherten Daten.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Projektdatei nicht gefunden: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data
