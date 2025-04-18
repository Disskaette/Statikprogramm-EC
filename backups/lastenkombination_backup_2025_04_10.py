# lastkombination.py

from typing import List, Dict
from datenbank.datenbank_holz import datenbank_holz_class
from gui.eingabemaske import Eingabemaske


def berechne_dynamische_lastkombination(lasten: List[Dict], db: datenbank_holz_class) -> Dict:
    """
    Berechnet die maßgebende Linienlast qd [kN/m] für GZT (Bemessung),
    unter Berücksichtigung von Sicherheits- und Kombinationsbeiwerten.

    :param lasten: Liste von Lastdictionaries aus der GUI
    :param db: Instanz der Datenbankklasse
    :return: Dictionary mit Formeltexten und resultierender Last in kN/m
    """
    lasten = self.lasten_memory
    e = self.sprungmass

    if e is None:
        print("Bitte zuerst ein gültiges Sprungmaß eingeben.")
        return

    gamma = {"g": 1.35, "s": 1.5, "w": 1.5, "p": 1.5}

    g_summe = 0.0
    q_einwirkungen = []

    for last in lasten:
        art = last["lastfall"]
        wert = float(last["wert"]) * e  # Umrechnung auf kN/m mit Sprungmaß
        kategorie = last["kategorie"]

        if art == "g":
            g_summe += wert
        elif art in ["s", "w", "p"]:
            psi0 = db.get_si_beiwerte(kategorie).psi0
            q_einwirkungen.append({
                "art": art,
                "wert": wert,
                "psi0": psi0
            })

    # Sortiere Q-Lasten nach Größe (größte zuerst für Hauptlast)
    q_einwirkungen.sort(key=lambda x: x["wert"], reverse=True)

    # Hauptkombination EC0: 1.35·G + 1.5·Q1 + Σ ψ0·Qi
    qd = gamma["g"] * g_summe
    formelzeichen = f"1.35·G"
    formelwerte = f"1.35·{g_summe:.2f}"

    if q_einwirkungen:
        haupt = q_einwirkungen[0]
        qd += gamma[haupt["art"]] * haupt["wert"]
        formelzeichen += f" + 1.5·{haupt['art'].upper()}"
        formelwerte += f" + 1.5·{haupt['wert']:.2f}"

        # Weitere Einwirkungen mit ψ0 kombinieren
        for neb in q_einwirkungen[1:]:
            beitrag = neb["psi0"] * neb["wert"]
            qd += beitrag
            formelzeichen += f" + {neb['psi0']:.2f}·{neb['art'].upper()}"
            formelwerte += f" + {neb['psi0']:.2f}·{neb['wert']:.2f}"

    ergebnis = {
        "qd": round(qd, 3),
        "formel": formelzeichen,
        "werte": formelwerte
    }

    print("\nDynamische Lastkombination (GZT):")
    print("Formelzeichen:", ergebnis["formel"])
    print("Werte eingesetzt:", ergebnis["werte"])
    print(f"Resultierende Bemessungslast qd = {ergebnis['qd']} kN/m")

    return ergebnis
