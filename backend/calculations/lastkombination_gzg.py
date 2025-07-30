from PIL import Image
from io import BytesIO
import logging

# Root-Logger-Verhalten
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class MethodeLastkombiGZG:
    """
    Quasi-permanente Lastkombinationen für Gebrauchstauglichkeit (GZG)
    nach EC5 §7.3.2 mit ψ₂-Faktoren
    """

    def __init__(self, snapshot, db):
        self.snapshot = snapshot
        self.db = db

    def tiefgestellt(self, s: str) -> str:
        return f"_{{{s}}}"

    def compute(self) -> dict:
        """Hauptmethode für GZG-Lastkombinationen - konsistent mit anderen Berechnungsmodulen"""
        return self.berechne_gzg_lastkombination()

    def berechne_gzg_lastkombination(self) -> dict:
        """Berechnet quasi-permanente Lastkombinationen für Gebrauchstauglichkeit"""
        logger.info("Starte GZG-Lastkombination (quasi-permanent)")

        # Daten aus Snapshot extrahieren
        lasten = self.snapshot.get("lasten", [])
        e = self.snapshot.get("sprungmass")
        typ = self.snapshot.get("querschnitt", {}).get("typ")

        # Debug-Ausgaben
        logger.debug(f"GZG Debug: lasten = {lasten}")
        logger.debug(f"GZG Debug: sprungmass e = {e}")
        logger.debug(f"GZG Debug: typ = {typ}")

        if not lasten or e is None:
            logger.error(
                "GZG-Lastkombination: Fehlende Lasten oder ungültiges Sprungmaß.")
            return {}

        # ψ₂-Faktoren für quasi-permanente Kombination (EC5 §7.3.2)
        psi2_faktoren = {"g": 1.0, "s": 0.0, "w": 0.0, "p": 0.3}

        g_summe = 0.0
        q_lasten = []

        # Lastfälle organisieren
        for last in lasten:
            lastfall = last["lastfall"].lower()
            wert = float(last["wert"]) * e
            kategorie = last["kategorie"]

            # kdef aus Datenbank für GZG-Berechnung
            kmod_typ = self.db.get_si_beiwerte(kategorie).kled
            kmod_entry = self.db.get_kmod(typ, last.get("nkl"))
            kdef = kmod_entry.kdef if hasattr(
                kmod_entry, 'kdef') else 0.8  # Fallback

            if lastfall == "g":
                g_summe += wert
                kdef_g = kdef
                last.update({
                    "wert_e": wert,
                    "psi2": psi2_faktoren["g"],
                    "kdef": kdef_g,
                })
            else:
                psi2 = psi2_faktoren.get(lastfall, 0.0)
                last.update({
                    "wert_e": wert,
                    "psi2": psi2,
                    "kdef": kdef,
                })
                q_lasten.append(last)

        # GZG-Kombinationen berechnen
        gzg_kombis = {}

        # Debug-Ausgaben
        logger.debug(f"GZG Debug: g_summe = {g_summe}")
        logger.debug(f"GZG Debug: q_lasten = {q_lasten}")

        # 1. Nur G (quasi-permanent)
        if g_summe > 0:
            qd_gzg = g_summe  # Keine Teilsicherheitsbeiwerte bei GZG

            header = "G_k"
            formel = f"G_k = {g_summe:.2f} \,\text{{kN/m}}"

            gzg_kombis[header] = {
                "latex": f"${header}: \quad {formel}$",
                "wert": qd_gzg,
                "kdef": kdef_g,
                "massgebend": len(q_lasten) == 0,  # Maßgebend wenn nur G
                "typ": "nur_g"
            }
            logger.debug(
                f"GZG Debug: Erstellt G-Kombination: {gzg_kombis[header]}")

        # 2. G + quasi-permanente Q-Anteile (ψ₂ · Q)
        if q_lasten:
            for q in q_lasten:
                if q["psi2"] > 0:  # Nur Lasten mit ψ₂ > 0 berücksichtigen
                    qd_gzg = g_summe + q["psi2"] * q["wert_e"]
                    kdef_max = max(kdef_g, q["kdef"])

                    header = f"G_k + \\psi_2 \\cdot {q['lastfall'].upper()}_k"
                    formel = f"G_k + {q['psi2']:.1f} \\cdot {q['lastfall'].upper()}_k = {g_summe:.2f} + {q['psi2']:.1f} \\cdot {q['wert_e']:.2f} = {qd_gzg:.2f} \\,\\text{{kN/m}}"

                    gzg_kombis[header] = {
                        "latex": f"${header}: \\quad {formel}$",
                        "wert": qd_gzg,
                        "kdef": kdef_max,
                        "massgebend": False,
                        "typ": "g_plus_q"
                    }

        # 3. Vollständige quasi-permanente Kombination (alle ψ₂ > 0)
        if len([q for q in q_lasten if q["psi2"] > 0]) > 1:
            qd_gesamt = g_summe
            kdef_max = kdef_g
            formel_teile = [f"G_k = {g_summe:.2f}"]
            header_teile = ["G_k"]

            for q in q_lasten:
                if q["psi2"] > 0:
                    qd_gesamt += q["psi2"] * q["wert_e"]
                    kdef_max = max(kdef_max, q["kdef"])
                    formel_teile.append(
                        f"{q['psi2']:.1f} \\cdot {q['lastfall'].upper()}_k = {q['psi2'] * q['wert_e']:.2f}")
                    header_teile.append(
                        f"\\psi_2 \\cdot {q['lastfall'].upper()}_k")

            header = " + ".join(header_teile)
            formel = " + ".join(formel_teile) + \
                f" = {qd_gesamt:.2f} \\,\\text{{kN/m}}"

            gzg_kombis[header] = {
                "latex": f"${header}: \\quad {formel}$",
                "wert": qd_gesamt,
                "kdef": kdef_max,
                "massgebend": False,
                "typ": "vollstaendig"
            }

        # Maßgebende Kombination ermitteln (höchste Last)
        if gzg_kombis:
            massgebende_kombi = max(
                gzg_kombis.items(), key=lambda x: x[1]["wert"])
            name, _ = massgebende_kombi

            # Alle auf nicht-maßgebend setzen
            for k in gzg_kombis.values():
                k["massgebend"] = False

            # Maßgebende markieren
            gzg_kombis[name]["massgebend"] = True

            logger.info(
                f"Maßgebende GZG-Kombination: {name}, qd = {gzg_kombis[name]['wert']:.2f} kN/m, kdef = {gzg_kombis[name]['kdef']:.2f}")

        return {"GZG_Lastfallkombinationen": gzg_kombis}

    def get_massgebende_kombination(self) -> dict:
        """Gibt nur die maßgebende GZG-Kombination zurück"""
        result = self.compute()
        gzg_kombis = result.get("GZG_Lastfallkombinationen", {})

        for name, kombi_data in gzg_kombis.items():
            if kombi_data.get("massgebend", False):
                return {
                    "name": name,
                    "wert": kombi_data["wert"],
                    "kdef": kombi_data["kdef"],
                    "latex": kombi_data["latex"]
                }

        return {}
