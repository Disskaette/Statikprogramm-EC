from PIL import Image
from io import BytesIO
import logging

# Root-Logger-Verhalten
logging.basicConfig(
    level=logging.DEBUG,                      # ab welcher Wichtigkeit geloggt wird
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)          # logger für dieses Modul


class MethodeLastkombi:
    def __init__(self, snapshot, db):
        self.snapshot = snapshot
        self.db = db

    def tiefgestellt(self, s: str) -> str:
        return f"_{{{s}}}"

    def compute(self) -> dict:
        return self.berechne_dynamische_lastkombination()

    def kombi_header_latex(self, leit_q=None, q_lasten=None):
        teile = [r"\gamma_{g} \cdot g"]
        reihenfolge = ["s", "w", "p"]

        if leit_q:
            leit_label = r"\mathbf{" + leit_q["lastfall"] + "}"
            teile.append(
                rf"\gamma_{{{leit_q['lastfall']}}} \cdot {leit_label}")
            for q in sorted(q_lasten, key=lambda x: reihenfolge.index(x["lastfall"])):
                if q == leit_q:
                    continue
                teile.append(
                    rf"\psi_0 \cdot \gamma_{{{q['lastfall']}}} \cdot {q['lastfall']}")
        elif q_lasten:
            for q in sorted(q_lasten, key=lambda x: reihenfolge.index(x["lastfall"])):
                teile.append(
                    rf"\gamma_{{{q['lastfall']}}} \cdot {q['lastfall']}")

        return " + ".join(teile)

    def berechne_dynamische_lastkombination(self) -> dict:
        # Debug: starte dynamische Lastkombination
        lasten = self.snapshot.get("lasten", [])
        e = self.snapshot.get("sprungmass")
        typ = self.snapshot.get("querschnitt", {}).get("typ")
        breite = self.snapshot.get("querschnitt", {}).get("breite_qs")
        hoehe = self.snapshot.get("querschnitt", {}).get("hoehe_qs")
        gruppe = self.snapshot.get("querschnitt", {}).get("materialgruppe")
        klasse = self.snapshot.get("querschnitt", {}).get("festigkeitsklasse")

        if not lasten or e is None:
            logger.error(
                "Lastkombination: Fehlende Lasten oder ungültiges Sprungmaß.")
            return {}

        gamma = {"g": 1.35, "s": 1.5, "w": 1.5, "p": 1.5}
        g_summe = 0.0
        q_lasten = []

        for last in lasten:
            nkl = last.get("nkl")
            breite = float(breite)/1000
            hoehe = float(hoehe)/1000

            bemessungsdaten = self.db.get_bemessungsdaten(
                gruppe, typ, klasse, nkl)
            roh_mean = bemessungsdaten.get("roh_mean")
            eigenlast = (roh_mean * breite * hoehe)/1000

            lastfall = last["lastfall"].lower()
            wert = float(last["wert"]) * e
            kategorie = last["kategorie"]
            kmod_typ = self.db.get_si_beiwerte(kategorie).kled
            kmod_entry = self.db.get_kmod(typ, nkl)
            kmod = kmod_entry.kmod_typ.get(kmod_typ, None)

            if lastfall == "g":
                if last.get("eigengewicht") == True:
                    g_summe += wert + eigenlast
                else:
                    g_summe += wert
                kmod_g = kmod
                last.update({
                    "wert_e": wert,
                    "gamma": gamma["g"],
                    "gamma_label": r"\gamma" + self.tiefgestellt("g"),
                    "kmod": kmod_g,
                })
            else:
                si = self.db.get_si_beiwerte(kategorie)

                last.update({
                    "wert_e": wert,
                    "psi0": si.psi0,
                    "gamma": gamma.get(lastfall, 1.5),
                    "gamma_label": r"\gamma" + self.tiefgestellt(lastfall),
                    "psi_label": r"\psi" + self.tiefgestellt("0"),
                    "kmod": kmod,
                })
                q_lasten.append(last)

        kombis = {}

        # 1. Nur G
        qd = gamma["g"] * g_summe
        qd_komb = qd / kmod_g

        header = self.kombi_header_latex()
        formel = rf"\frac{{{gamma['g']:.2f} \cdot g}}{{{kmod_g:.2f}}}"
        formel_ed = rf"{gamma['g']:.2f} \cdot g"
        kombis[header] = {
            "latex": rf"${header}: \quad {formel} = {qd_komb:.2f} \,\text{{kN/m}}$",
            "latex_ed": rf"${header}: \quad {formel_ed} = {qd:.2f} \,\text{{kN/m}}$",
            "wert": qd_komb,
            "Ed": qd,
            "kmod": kmod_g,
            "massgebend": True
        }

        # 2. G + einzelne Q
        for q in q_lasten:
            kmod_max = max(kmod_g, q["kmod"])
            qd = gamma["g"] * g_summe + q["gamma"] * q["wert_e"]
            qd_komb = qd / kmod_max

            header = self.kombi_header_latex(q_lasten=[q])
            formel = rf"\frac{{{gamma['g']:.2f} \cdot g + {q['gamma']:.2f} \cdot {q['lastfall']}}}{{{kmod_max:.2f}}}"
            formel_ed = rf"{gamma['g']:.2f} \cdot g + {q['gamma']:.2f} \cdot {q['lastfall']}"
            kombis[header] = {
                "latex": rf"${header}: \quad {formel} = {qd_komb:.2f} \,\text{{kN/m}}$",
                "latex_ed": rf"${header}: \quad {formel_ed} = {qd:.2f} \,\text{{kN/m}}$",
                "wert": qd_komb,
                "Ed": qd,
                "kmod": kmod_max,
            }

        # 3. G + alle Q mit je einer als Leiteinwirkung (nur wenn mehr als 1 Q)
        if len(q_lasten) > 1:
            for leit_q in q_lasten:
                leit_gamma = leit_q["gamma"]
                leit_label = r"\mathbf{" + leit_q["lastfall"] + "}"
                leit_wert = leit_q["wert_e"]

                kmod_max = max([leit_q["kmod"]] + [q["kmod"]
                               for q in q_lasten if q != leit_q] + [kmod_g])
                qd_summe = gamma["g"] * g_summe + leit_gamma * leit_wert

                latex_parts = [rf"{gamma['g']:.2f} \cdot g",
                               rf"{leit_gamma:.2f} \cdot {leit_label}"]

                for neb_q in q_lasten:
                    if neb_q == leit_q:
                        continue
                    psi = neb_q["psi0"]
                    gamma_ = neb_q["gamma"]
                    neb_label = neb_q["lastfall"]
                    wert = neb_q["wert_e"]

                    latex_parts.append(
                        rf"{psi:.2f} \cdot {gamma_:.2f} \cdot {neb_label}")
                    qd_summe += psi * gamma_ * wert
                qd_komb = qd_summe / kmod_max
                formel = rf"\frac{{{' + '.join(latex_parts)}}}{{{kmod_max:.2f}}}"
                formel_ed = ' + '.join(latex_parts)
                header = self.kombi_header_latex(
                    leit_q=leit_q, q_lasten=q_lasten)
                kombis[header] = {
                    "latex": rf"${header}: \quad {formel} = {qd_komb:.2f} \,\text{{kN/m}}$",
                    "latex_ed": rf"${header}: \quad {formel_ed} = {qd_summe:.2f} \,\text{{kN/m}}$",
                    "wert": qd_komb,
                    "Ed": qd_summe,
                    "kmod": kmod_max,
                }

        # print("\n\U0001F4D0 Lastkombinationen (LaTeX-ready):\n")
        # for name, k in kombis.items():
        #     print(rf"{name}: {k['latex']}")
        massgebende_kombi = max(kombis.items(), key=lambda x: x[1]["wert"])
        name, _ = massgebende_kombi
        for k in kombis.values():
            k["massgebend"] = False  # Feld wird neu erstellt → überall False
        # Nur für die eine Kombination → True
        kombis[name]["massgebend"] = True
        print(kombis)
        return {"Lastfallkombinationen": kombis}
