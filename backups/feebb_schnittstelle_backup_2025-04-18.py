'''--- Datenaufbereitung der Dicts für feebb und Berechnung--- '''
from berechnungen.feebb import Element, Beam, Postprocessor
from berechnungen.feebb import Preprocessor, Element, Beam, Postprocessor
from berechnungen.lastenkombination import MethodeLastkombi


class FeebbBerechnung:
    def __init__(self, eingabemaske):
        self.eingabemaske = eingabemaske
        self.lastenkombination = self.eingabemaske.kombi_berechnung
        self.system_memory = {}  # Ergebnis-Cache für GZT und GZG

    def update_feebb(self):
        """Aktualisiert die feebb-Berechnung und speichert die Ergebnisse."""
        print("📣 Update feebb gestartet")
        # Querschnittsdaten laden, falls noch nicht vorhanden
        if not self.eingabemaske.querschnitt_memory:
            print("📌 Querschnittdaten nicht gefunden – Update wird erzwungen.")
            self.eingabemaske.update_querschnitt_memory()

        qs = self.eingabemaske.querschnitt_memory

        # Optional: Immer noch leer? Dann abbrechen
        if not qs or "E" not in qs or "I_y" not in qs:
            raise ValueError(
                "❌ Querschnittdaten konnten nicht geladen werden.")

        gzt, gzg = self.erstelle_feebb_dicts()
        self.system_memory = berechne_feebb_gzt_gzg(gzt, gzg)

        maxwerte = self.system_memory['GZT']['max']
        print(f"✅ FE-Berechnung abgeschlossen")
        print(f"🔹 Max. Moment: {maxwerte['moment']/1e6:.2f} kNm")
        print(f"🔹 Max. Durchbiegung: {maxwerte['durchbiegung']:.2f} mm")
        print(f"🔹 Max. Querkraft: {maxwerte['querkraft']/1e3:.2f} kN")

    def erstelle_feebb_dicts(self):
        """
        Erzeugt zwei Dicts:
        1. GZT: maßgebende Lastkombination mit allen Systemdaten
        2. GZG: jede Einwirkung einzeln, ohne Sicherheitsbeiwerte
        """
        # Importe

        # --- Gemeinsame Querschnittswerte (für alle Elemente gleich) ---
        qs = self.eingabemaske.querschnitt_memory
        # [kN/mm2] evtl. in [N/mm2] umrechnen
        E = qs["E"]
        I = qs['I_y']  # [mm^4] evtl. Umrechnen

        # --- Gemeinsame Geometrie (Spannweiten) ---
        # [m] zu [mm]
        spannweiten = [
            wert * 1000 for wert in self.eingabemaske.spannweiten_memory.values()]

        # --- Unterstützungslager: erstes fest, Rest verschieblich ---
        supports = []
        for i in range(len(spannweiten) + 1):
            if i == 0:
                supports += [-1, -1,]  # fest (u = 0, phi = 0)
            else:
                supports += [-1, 0]  # verschieblich (u frei, phi = 0)

        # --- Maßgebende Lastkombination berechnen ---
        kombis = self.lastenkombination.berechne_dynamische_lastkombination()

        lastwert = [item[1]["Ed"] for item in kombis.items(
        ) if item[1].get("massgebend")][0]  # [kN/m]
        if lastwert is None:
            raise ValueError("❌ Keine maßgebende Lastkombination gefunden!")
        # --- GZT-Dict ---
        gzt = {
            "elements": [
                {
                    "length": l,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [
                        # gleichmäßig über gesamten Balken
                        {"type": "udl", "magnitude": lastwert}
                    ]
                }
                for l in spannweiten
            ],
            "supports": supports
        }

        # --- GZG-Dict ---
        gzg = []
        e = self.eingabemaske.sprungmass
        for last in self.eingabemaske.lasten_memory:
            # Flächenlast [kN/m²] × e = Linienlast
            q_wert = float(last['wert']) * e
            gzg_dict = {
                "lastfall": last['lastfall'],
                "kommentar": last['kommentar'],
                "elements": [
                    {
                        "length": l,
                        "youngs_mod": E,
                        "moment_of_inertia": I,
                        "loads": [
                            {"type": "udl", "magnitude": q_wert}
                        ]
                    }
                    for l in spannweiten
                ],
                "supports": supports
            }
            gzg.append(gzg_dict)

        return gzt, gzg


def berechne_feebb_gzt_gzg(gzt_dict, gzg_dicts, num_points=100):
    # GZT-Berechnung
    gzt_elements = [Element(e) for e in gzt_dict["elements"]]
    gzt_beam = Beam(gzt_elements, gzt_dict["supports"])
    gzt_post = Postprocessor(gzt_beam, num_points)
    for e in gzt_dict["elements"]:
        print(
            f"📦 Eingabe für feebb: Länge = {e['length']} mm, Last = {e['loads']}")
    gzt_m = gzt_post.interp("moment")
    gzt_w = gzt_post.interp("displacement")
    gzt_v = gzt_post.interp("shear")

    # GZG-Berechnung je Einwirkung
    gzg = []
    for einwirkung in gzg_dicts:
        elements = [Element(e) for e in einwirkung["elements"]]
        beam = Beam(elements, einwirkung["supports"])
        post = Postprocessor(beam, num_points)

        mom = post.interp("moment")
        disp = post.interp("displacement")
        shear = post.interp("shear")

        gzg.append({
            "lastfall": einwirkung["lastfall"],
            "kommentar": einwirkung["kommentar"],
            "moment": mom,
            "durchbiegung": disp,
            "querkraft": shear
        })

    return {
        "GZT": {
            "moment": gzt_m,
            "durchbiegung": gzt_w,
            "querkraft": gzt_v,
            "max": {
                "moment": max(abs(m) for m in gzt_m),
                "durchbiegung": max(abs(w) for w in gzt_w),
                "querkraft": max(abs(v) for v in gzt_v)
            }
        },
        "GZG": gzg
    }
