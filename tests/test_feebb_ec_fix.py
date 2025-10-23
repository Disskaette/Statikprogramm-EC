"""
Tests für den G_SUM-Fix in feebb_schnittstelle_ec.py

Testziel: Verifizierung, dass keine Sprünge im Feld auftreten
wenn mehrere G-Lasten definiert sind.
"""

from calculations.feebb_schnittstelle_ec import FeebbBerechnungEC
import pytest
import numpy as np
import sys
from pathlib import Path

# Füge Backend-Pfad zum sys.path hinzu
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


class TestGSumFix:
    """Tests für den G_SUM-Fix (Key-Kollision bei mehreren G-Lasten)"""

    def test_einzelne_g_last(self):
        """Property-Test: Bei einer G-Last keine Sprünge im Feld"""
        systemdaten = {
            "spannweiten": {"feld_1": 5.0, "feld_2": 5.0, "feld_3": 5.0},
            "querschnitt": {"breite": 120, "hoehe": 240},
            "material": {"typ": "GL24h"},
            "lasten": [
                {"lastfall": "g", "wert": 10.0}  # Nur eine G-Last
            ]
        }

        berechnung = FeebbBerechnungEC(systemdaten)
        ergebnisse = berechnung.berechne()

        # Prüfe GZT-Momentenverlauf auf Sprünge
        gzt_moment = ergebnisse["GZT"]["moment"]

        # Erwarte kontinuierlichen Verlauf (keine abrupten Sprünge)
        # Berechne zweite Ableitung (Krümmung)
        second_deriv = np.diff(np.diff(gzt_moment))

        # Bei gleichmäßiger UDL sollte zweite Ableitung nahezu konstant sein
        # (bis auf Sprünge an Lagern, die wir tolerieren)
        max_jump = np.max(np.abs(second_deriv))

        # Akzeptiere Sprünge nur an Feldgrenzen (ca. bei 1/3 und 2/3 der Punkte)
        # Innerhalb der Felder sollte es glatt sein
        assert max_jump < 1e8, "Zu große Sprünge im Momentenverlauf"

    def test_mehrere_g_lasten_regression(self):
        """
        Regression-Test: Mehrere G-Lasten mit gleichem lastfall="g"

        Dieser Test reproduziert den ursprünglichen Bug:
        - Mehrere G-Lasten mit lastfall="g"
        - Key-Kollision führte zu Doppelzählung/Unterzählung
        - Mit Fix: Alle G-Lasten werden korrekt summiert
        """
        systemdaten = {
            "spannweiten": {"feld_1": 5.0, "feld_2": 5.0, "feld_3": 5.0},
            "querschnitt": {"breite": 120, "hoehe": 240},
            "material": {"typ": "GL24h"},
            "lasten": [
                {"lastfall": "g", "wert": 10.0},  # G1: Eigengewicht
                {"lastfall": "g", "wert": 5.0},   # G2: Ausbau (Key-Kollision!)
                {"lastfall": "s", "wert": 3.0},   # Schnee
                {"lastfall": "w", "wert": 2.0}    # Wind
            ]
        }

        berechnung = FeebbBerechnungEC(systemdaten)
        ergebnisse = berechnung.berechne()

        # 1. Prüfe, dass Kombinationen korrekt generiert wurden
        assert len(
            berechnung.kombinationen_gzt) > 0, "Keine GZT-Kombinationen generiert"

        # 2. Prüfe, dass G_SUM korrekt berechnet wurde
        nur_g_kombi = next(
            k for k in berechnung.kombinationen_gzt if k["typ"] == "nur_g")
        g_sum = nur_g_kombi["lasten"]["G_SUM"]

        # Erwarteter Wert: (10 + 5) * γ_G * sprungmass = 15 * 1.35 * 1000 = 20250 N/mm
        expected_g_sum = (10.0 + 5.0) * 1.35 * 1000
        assert abs(
            g_sum - expected_g_sum) < 1e-6, f"G_SUM falsch: {g_sum} != {expected_g_sum}"

        # 3. Prüfe Momentenverlauf auf Sprünge (wie in Test 1)
        gzt_moment = ergebnisse["GZT"]["moment"]
        second_deriv = np.diff(np.diff(gzt_moment))
        max_jump = np.max(np.abs(second_deriv))

        # Mit Fix: Keine großen Sprünge
        assert max_jump < 1e8, f"Sprünge im Feld: max_jump = {max_jump}"

    def test_mehrfeld_muster_leit_begleit(self):
        """
        Test: Leitlast feldweise, Begleitlesten auf alle Felder

        Prüft, dass bei Vollkombinationen (Leit + Begleit) keine
        unerwarteten Sprünge innerhalb eines Feldes auftreten.
        """
        systemdaten = {
            "spannweiten": {"feld_1": 5.0, "feld_2": 5.0, "feld_3": 5.0},
            "querschnitt": {"breite": 120, "hoehe": 240},
            "material": {"typ": "GL24h"},
            "lasten": [
                {"lastfall": "g", "wert": 10.0},
                {"lastfall": "g", "wert": 5.0},  # Zweite G-Last
                {"lastfall": "s", "wert": 3.0},  # Leitlast
                {"lastfall": "w", "wert": 2.0}   # Begleitlest
            ]
        }

        berechnung = FeebbBerechnungEC(systemdaten)
        ergebnisse = berechnung.berechne()

        # Prüfe, dass Vollkombinationen generiert wurden
        vollkombis = [
            k for k in berechnung.kombinationen_gzt if k["typ"] == "vollkombination"]
        assert len(
            vollkombis) == 2, "Sollte 2 Vollkombinationen haben (S als Leit, W als Leit)"

        # Prüfe eine Vollkombination im Detail
        s_leit_kombi = next(
            k for k in vollkombis if k["leiteinwirkung"] == "s")

        # Erwartung: G_SUM + S (Leit) + ψ₀·W (Begleit)
        assert "G_SUM" in s_leit_kombi["lasten"], "G_SUM fehlt in Vollkombination"
        assert "s" in s_leit_kombi["lasten"], "Leitlast 's' fehlt"
        assert "w" in s_leit_kombi["lasten"], "Begleitlest 'w' fehlt"

        # Prüfe GZT-Ergebnisse auf Kontinuität
        gzt_moment = ergebnisse["GZT"]["moment"]

        # Berechne Differenzen zwischen benachbarten Punkten
        first_deriv = np.diff(gzt_moment)

        # Erwarte kontinuierlichen Verlauf (außer an Lagern)
        # Bei 3 Feldern mit je ~100 Elementen: Lager bei Index ~100, ~200
        # Innerhalb eines Feldes sollte die Steigung sanft variieren

        # Prüfe Feld 2 (mittleres Feld, Index ca. 100-200)
        feld2_start = len(gzt_moment) // 3
        feld2_end = 2 * len(gzt_moment) // 3
        feld2_deriv = first_deriv[feld2_start:feld2_end]

        # Innerhalb des Feldes: Steigungsänderung sollte klein sein
        max_deriv_change = np.max(np.abs(np.diff(feld2_deriv)))

        assert max_deriv_change < 1e6, f"Zu große Steigungsänderung in Feld 2: {max_deriv_change}"

    def test_g_sum_in_allen_kombinationen(self):
        """
        Test: Prüfe, dass alle Kombinationen G_SUM statt einzelner G-Keys enthalten

        Dieser Test stellt sicher, dass der Fix durchgängig angewendet wurde.
        """
        systemdaten = {
            "spannweiten": {"feld_1": 5.0},
            "querschnitt": {"breite": 120, "hoehe": 240},
            "material": {"typ": "GL24h"},
            "lasten": [
                {"lastfall": "g", "wert": 10.0},
                {"lastfall": "g", "wert": 5.0},
                {"lastfall": "s", "wert": 3.0}
            ]
        }

        berechnung = FeebbBerechnungEC(systemdaten)
        _ = berechnung.berechne()

        # Prüfe alle GZT-Kombinationen
        for kombi in berechnung.kombinationen_gzt:
            assert "G_SUM" in kombi["lasten"], f"G_SUM fehlt in {kombi['name']}"
            # Prüfe, dass KEINE "g"-Keys mehr existieren
            for key in kombi["lasten"].keys():
                assert key.lower(
                ) != "g", f"Alter 'g'-Key noch in {kombi['name']}"

        # Prüfe alle GZG-Kombinationen
        for kombi in berechnung.kombinationen_gzg:
            assert "G_SUM" in kombi["lasten"], f"G_SUM fehlt in {kombi['name']}"
            for key in kombi["lasten"].keys():
                assert key.lower(
                ) != "g", f"Alter 'g'-Key noch in {kombi['name']}"


if __name__ == "__main__":
    # Tests direkt ausführen
    pytest.main([__file__, "-v"])
