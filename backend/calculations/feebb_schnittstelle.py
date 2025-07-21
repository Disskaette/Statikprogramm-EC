'''--- Datenaufbereitung der Dicts für feebb und Berechnung--- '''
import numpy as np
from backend.calculations.feebb import Element, Beam, Postprocessor
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class FeebbBerechnung:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.system_memory = {}  # Ergebnis-Cache für GZT und GZG

    def compute(self) -> dict:
        self.update_feebb()
        schnitt = self.system_memory.get("Schnittgroessen")
        # if schnitt and "GZT" in schnitt and "max" in schnitt["GZT"]:
        #     print(schnitt["GZT"]["max"])
        # else:
        #     print("❌ 'max' nicht gefunden!")
        return self.system_memory

    def update_feebb(self):
        """Aktualisiert die feebb-Berechnung und speichert die Ergebnisse."""
        try:
            print("📣 Update feebb gestartet")
            gzt, gzg = self.erstelle_feebb_dicts()
            self.system_memory = berechne_feebb_gzt_gzg(gzt, gzg)
            maxwerte = self.system_memory['Schnittgroessen']['GZT']['max']
            self.max_moment_feebb = maxwerte['moment']/1e6
            self.max_querkraft_feebb = maxwerte['querkraft']/1e3
            self.max_durchbiegung_feebb = maxwerte['durchbiegung']

            print(f"✅ FE-Berechnung abgeschlossen")
            print(f"🔹 Max. Moment: {maxwerte['moment']/1e6:.2f} kNm")
            print(
                f"🔹 Max. Durchbiegung: {maxwerte['durchbiegung']:.2f} mm")
            print(f"🔹 Max. Querkraft: {maxwerte['querkraft']/1e3:.2f} kN")
            self.moment = self.system_memory['Schnittgroessen']['GZT']['moment']
            self.querkraft = self.system_memory['Schnittgroessen']['GZT']['querkraft']
            self.durchbiegung = self.system_memory['Schnittgroessen']['GZT']['durchbiegung']

            # Schnittkräfte übergeben
            return

        except Exception as e:
            print("⚠️ Fehler im FE-Thread:", e)

    def erstelle_feebb_dicts(self):
        """
        Erzeugt zwei Dicts:
        1. GZT: maßgebende Lastkombination mit allen Systemdaten
        2. GZG: jede Einwirkung einzeln, ohne Sicherheitsbeiwerte
        """

        qs = self.snapshot["querschnitt"]
        E = qs["E"]
        I = qs["I_y"]
        kombis = self.snapshot["Lastfallkombinationen"]
        # print(kombis)
        massgebende = [item[1]["Ed"]
                       for item in kombis.items() if item[1].get("massgebend")]
        if not massgebende:
            raise ValueError("❌ Keine maßgebende Lastkombination gefunden!")
        lastwert = massgebende[0]

        all_elements = []
        zwischenlager_knoten = []
        node_tracker = 0

        # === Kragarm links ===
        spannweiten = self.snapshot.get("spannweiten")
        l = float(spannweiten.get("kragarm_links", 0))
        print(float(spannweiten.get("kragarm_links", 0)))
        if l > 0:
            n = int(round(l * 20))
            l_mm = l * 1000 / n
            for _ in range(n):
                all_elements.append({
                    "length": l_mm,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [{"type": "udl", "magnitude": lastwert}]
                })
            node_tracker += n
            zwischenlager_knoten.append(node_tracker)
            print(node_tracker)
            # node_tracker += 1

        # === Normale Felder ===
        normale_felder = [
            wert for key, wert in self.snapshot["spannweiten"].items()
            if key.startswith("feld_")
        ]

        for idx, feld in enumerate(normale_felder):
            n = int(round(feld * 20))
            l_mm = feld * 1000 / n
            for _ in range(n):
                all_elements.append({
                    "length": l_mm,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [{"type": "udl", "magnitude": lastwert}]
                })
            node_tracker += n
            if idx < len(normale_felder) - 1:
                zwischenlager_knoten.append(node_tracker)

        # hauptfeld_ende = node_tracker

        # === Kragarm rechts ===
        ende_mormale_felder = node_tracker
        l = float(spannweiten.get("kragarm_rechts", 0))
        if l > 0:
            n = int(round(l * 20))
            l_mm = l * 1000 / n
            for _ in range(n):
                all_elements.append({
                    "length": l_mm,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [{"type": "udl", "magnitude": lastwert}]
                })
            node_tracker += n

        # === Knotenanzahl
        knoten_anzahl = node_tracker + 1
        supports = [[0, 0] for _ in range(knoten_anzahl)]

        # === 1. Standard-Lager am Anfang und Ende setzen
        supports[0] = [-1, 0]                      # Start-Gleitlager
        supports[knoten_anzahl - 1] = [-1, 0]      # End-Gleitlager

        # === 2. Zwischenlager
        for k in zwischenlager_knoten:
            supports[k] = [-1, 0]

        # === 3. Kragarm-Überschreibungen
        if float(spannweiten.get("kragarm_links", 0)) > 0:
            supports[0] = [0, 0]  # Start freigeben

        if float(spannweiten.get("kragarm_rechts", 0)) > 0:
            supports[ende_mormale_felder] = [-1, 0]
            supports[node_tracker] = [0, 0]       # Ende freigeben

        # === Debug
        # print("📋 Übersicht aller Knotenlagerungen:")
        # print(f"{'Knoten':>6} | {'u':>5} | {'phi':>5}")
        # print("-" * 26)
        # for i, (u, phi) in enumerate(supports):
        #     print(f"{i:>6} | {u:>5} | {phi:>5}")

        # === Rückgabe GZT + GZG
        supports_flat = [v for pair in supports for v in pair]

        gzt = {
            "elements": all_elements,
            "supports": supports_flat
        }

        gzg = []
        sprungmass = self.snapshot["sprungmass"]
        for last in self.snapshot["lasten"]:
            q_k = float(last["wert"]) * sprungmass
            gzg_elements = [
                {
                    "length": el["length"],
                    "youngs_mod": el["youngs_mod"],
                    "moment_of_inertia": el["moment_of_inertia"],
                    "loads": [{"type": "udl", "magnitude": q_k}]
                }
                for el in all_elements
            ]
            gzg.append({
                "lastfall": last["lastfall"],
                "kommentar": last["kommentar"],
                "elements": gzg_elements,
                "supports": supports_flat
            })

        return gzt, gzg


def berechne_feebb_gzt_gzg(gzt_dict, gzg_dicts, num_points=100):
    # GZT-Berechnung
    gzt_elements = [Element(e) for e in gzt_dict["elements"]]
    gzt_beam = Beam(gzt_elements, gzt_dict["supports"])
    gzt_post = Postprocessor(gzt_beam, num_points)
    # for e in gzt_dict["elements"]:
    #     print(
    #         f"📦 Eingabe für feebb: Länge = {e['length']} mm, Last = {e['loads']}")
    gzt_m = gzt_post.interp("moment")
    gzt_w = gzt_post.interp("displacement")
    gzt_v = gzt_post.interp("shear")

    # GZG-Berechnung je Einwirkung
    gzg = []
    for einwirkung in gzg_dicts:
        gzg_elements = [Element(e) for e in einwirkung["elements"]]
        gzg_beam = Beam(gzg_elements, einwirkung["supports"])
        gzg_post = Postprocessor(gzg_beam, num_points)

        gzg_m = gzg_post.interp("moment")
        gzg_w = gzg_post.interp("displacement")
        gzg_v = gzg_post.interp("shear")

        gzg.append({
            "max": {
                "durchbiegung": max(abs(w) for w in gzg_w)
            },
            "lastfall": einwirkung["lastfall"],
            "kommentar": einwirkung["kommentar"],
            "moment": gzg_m,
            "querkraft": gzg_v,
            "durchbiegung": gzg_w,
        })
    return {
        "Schnittgroessen": {
            "GZT": {
                "max": {
                    "moment": max(abs(m) for m in gzt_m),
                    "durchbiegung": max(abs(w) for w in gzt_w),
                    "querkraft": max(abs(v) for v in gzt_v)
                },
                "moment": gzt_m,
                "durchbiegung": gzt_w,
                "querkraft": gzt_v,
            },
            "GZG": gzg
        }
    }
