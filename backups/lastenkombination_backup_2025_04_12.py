'''Lastenkombination nach EC0'''

from typing import Dict
from datenbank.datenbank_holz import datenbank_holz_class
from gui.eingabemaske import Eingabemaske


class MethodeLastkombi:
    @staticmethod
    def berechne_dynamische_lastkombination(gui: Eingabemaske, db: datenbank_holz_class) -> Dict:
        lasten = gui.lasten_memory
        e = gui.sprungmass

        if not lasten or e is None:
            print("Fehlende Lasten oder ungültiges Sprungmaß.")
            return {"qd": 0, "formel": "–", "werte": "–"}

        gamma = {"g": 1.35, "s": 1.5, "w": 1.5, "p": 1.5}
        g_summe = 0.0
        q_einwirkungen = []

        for last in lasten:
            lastfall = last["lastfall"]
            wert = float(last["wert"]) * e
            kategorie = last["kategorie"]

            if lastfall == "g":
                g_summe += wert
            elif lastfall in ["s", "w", "p"]:
                si = db.get_si_beiwerte(kategorie)
                if si is None:
                    print(f"Fehlender ψ-Wert für Kategorie: {kategorie}")
                    continue
                psi0 = si.psi0
                q_einwirkungen.append({
                    "lastfall": lastfall,
                    "wert": wert,
                    "psi0": psi0,
                    "kategorie": kategorie
                })

        q_einwirkungen.sort(key=lambda x: x["wert"], reverse=True)
        qd = gamma["g"] * g_summe
        formelzeichen = f"1.35·G"
        formelwerte = f"1.35·{g_summe:.2f}"

        if q_einwirkungen:
            haupt = q_einwirkungen[0]
            qd += gamma[haupt["lastfall"]] * haupt["wert"]
            formelzeichen += f" + 1.5·{haupt['lastfall'].upper()}"
            formelwerte += f" + 1.5·{haupt['wert']:.2f}"

            for neb in q_einwirkungen[1:]:
                beitrag = neb["psi0"] * neb["wert"]
                qd += beitrag
                formelzeichen += f" + ψ₀·{neb['lastfall'].upper()}"
                formelwerte += f" + {neb['psi0']:.2f}·{neb['wert']:.2f}"

        ergebnis = {
            "qd": round(qd, 3),
            "formel": formelzeichen,
            "werte": formelwerte
        }

        print("\n💡 Dynamische Lastkombination (GZT)")
        print("Formelzeichen:", ergebnis["formel"])
        print("Werte eingesetzt:", ergebnis["werte"])
        print(f"→ Bemessungslast qd = {ergebnis['qd']} kN/m")

        return ergebnis


if __name__ == "__main__":
    # Beispielaufruf (Dummy-Daten)
    gui = Eingabemaske()
    db = datenbank_holz_class()

    # Dummy-Daten für Lasten
    gui.lasten_memory = [
        {"lastfall": "g", "wert": 5.0, "kategorie": "Dach"},
        {"lastfall": "s", "wert": 2.0, "kategorie": "Dach"},
        {"lastfall": "w", "wert": 1.0, "kategorie": "Dach"}
    ]
    gui.sprungmass = 1.0

    berechne_dynamische_lastkombination(gui, db)
