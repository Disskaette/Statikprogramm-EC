# backend/service/calculation_service.py
import logging
from backend.calculations.lastenkombination import MethodeLastkombi
from backend.calculations.lastkombination_gzg import MethodeLastkombiGZG
from backend.database.datenbank_holz import datenbank_holz_class
from backend.calculations.feebb_schnittstelle import FeebbBerechnung
from backend.calculations.nachweis_ec5 import MethodeNachweisEC5

# Logger für dieses Modul
logger = logging.getLogger(__name__)

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
    # Erstelle FeebbBerechnung mit Snapshot
    feb = FeebbBerechnung(snapshot)
    return feb.compute()


def add_gzg_load_combinations(snapshot: dict) -> dict:
    """Wrapper für GZG-Lastkombinationen (quasi-permanent)"""
    try:
        gzg_calculator = MethodeLastkombiGZG(snapshot, db)
        result = gzg_calculator.compute()
        return result
    except Exception as e:
        logger.error(f"Fehler bei GZG-Lastkombination: {e}")
        return {'GZG_Lastfallkombinationen': {}}


def add_ec5_verification(snapshot: dict) -> dict:
    """
    Wrapper für die EC5-Nachweise.
    Übergabe kompletter Snapshots und Rückgabe
    der Nachweisergebnisse mit LaTeX-Formeln.
    """
    # Erstelle MethodeNachweisEC5 mit Snapshot und globaler DB-Instanz
    ec5 = MethodeNachweisEC5(snapshot, db)
    return ec5.compute()
