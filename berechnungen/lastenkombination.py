import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image, ImageTk


class MethodeLastkombi:
    def __init__(self, gui, db):
        self.gui = gui
        self.db = db

    def tiefgestellt(self, s: str) -> str:
        return f"_{{{s}}}"

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
        lasten = self.gui.lasten_memory
        e = self.gui.sprungmass

        if not lasten or e is None:
            print("Fehlende Lasten oder ungültiges Sprungmaß.")
            return {}

        gamma = {"g": 1.35, "s": 1.5, "w": 1.5, "p": 1.5}
        g_summe = 0.0
        q_lasten = []

        for last in lasten:
            lastfall = last["lastfall"].lower()
            wert = float(last["wert"]) * e
            kategorie = last["kategorie"]

            if lastfall == "g":
                g_summe += wert
                last.update({
                    "wert_e": wert,
                    "gamma": gamma["g"],
                    "gamma_label": r"\gamma" + self.tiefgestellt("g")
                })
            else:
                si = self.db.get_si_beiwerte(kategorie)
                if si is None:
                    print(f"⚠️ Fehlender ψ-Wert für Kategorie: {kategorie}")
                    continue
                last.update({
                    "wert_e": wert,
                    "psi0": si.psi0,
                    "gamma": gamma.get(lastfall, 1.5),
                    "gamma_label": r"\gamma" + self.tiefgestellt(lastfall),
                    "psi_label": r"\psi" + self.tiefgestellt("0")
                })
                q_lasten.append(last)

        kombis = {}

        # 1. Nur G
        kmod_g = next((l["kmod"]
                      for l in lasten if l["lastfall"].lower() == "g"), 1.0)
        qd = gamma["g"] * g_summe
        qd_komb = qd / kmod_g

        header = self.kombi_header_latex()
        formel = rf"\frac{{{gamma['g']:.2f} \cdot g}}{{{kmod_g:.2f}}}"
        formel_ed = rf"{gamma['g']:.2f} \cdot g"
        kombis[header] = {
            "latex": rf"${header}: \quad {formel} = {qd_komb:.2f} \,\text{{kN/m}}$",
            "latex_ed": rf"${header}: \quad {formel_ed} = {qd:.2f} \,\text{{kN/m}}$",
            "wert": qd_komb,
            "Ed": qd
        }

        # 2. G + einzelne Q
        for q in q_lasten:
            kmod_max = max(kmod_g, q.get("kmod", 1.0))
            qd = gamma["g"] * g_summe + q["gamma"] * q["wert_e"]
            qd_komb = qd / kmod_max

            header = self.kombi_header_latex(q_lasten=[q])
            formel = rf"\frac{{{gamma['g']:.2f} \cdot g + {q['gamma']:.2f} \cdot {q['lastfall']}}}{{{kmod_max:.2f}}}"
            formel_ed = rf"{gamma['g']:.2f} \cdot g + {q['gamma']:.2f} \cdot {q['lastfall']}"
            kombis[header] = {
                "latex": rf"${header}: \quad {formel} = {qd_komb:.2f} \,\text{{kN/m}}$",
                "latex_ed": rf"${header}: \quad {formel_ed} = {qd:.2f} \,\text{{kN/m}}$",
                "wert": qd_komb,
                "Ed": qd
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
                    "Ed": qd_summe
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

        return kombis

    def render_latex_to_image(self, latex_str):
        fig, ax = plt.subplots(figsize=(4, 0.05), dpi=200)
        fig.patch.set_visible(False)
        ax.axis("off")

        ax.text(0.01, 0.5, latex_str,
                fontsize=5, va="center", ha="left")

        buf = BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight",
                    pad_inches=0.05, transparent=True)
        plt.close(fig)

        buf.seek(0)
        return Image.open(buf)
