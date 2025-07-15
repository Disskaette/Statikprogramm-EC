# backend/service/calculation_service.py
from backend.calculations.lastenkombination import MethodeLastkombi
from backend.database.datenbank_holz import datenbank_holz_class
from backend.calculations.feebb_schnittstelle import FeebbBerechnung

# DB-Instanz für Nachschlagewerte
db = datenbank_holz_class()


def add_load_cases(snapshot: dict) -> dict:
    """
    Wrapper für die Lastenkombination.
    Übergabe kompletter Snapshots und Rückgabe
    des kombinierten Ergebnisses zurück.
    """
    # Erstelle MethodeLastkombi mit Snapshot und globaler DB-Instanz
    mlk = MethodeLastkombi(snapshot, db)
    return mlk.compute()


def add_section_forces(snapshot: dict) -> dict:
    """
    Wrapper für die FEEBB-Berechnung.
    Übergabe kompletter Snapshots und Rückgabe
    der maximalen Schnittkräfte.
    """

    # Erstelle MethodeLastkombi mit Snapshot und globaler DB-Instanz
    feb = FeebbBerechnung(snapshot)
    return feb.compute()
