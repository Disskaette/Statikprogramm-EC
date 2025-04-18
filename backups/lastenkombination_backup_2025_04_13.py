class MethodeLastkombi:

    def tiefgestellt(s: str) -> str:
        # Wandelt z. B. "g" in "_{g}", "0" in "_{0}" für LaTeX
        return f"_{{{s}}}"

    def berechne_dynamische_lastkombination(*, lasten, sprungmass) -> dict:
        lasten = gui.lasten_memory
        e = sprungmass

        if not lasten or e is None:
            print("Fehlende Lasten oder ungültiges Sprungmaß.")
            return {}

        gamma = {"g": 1.35, "s": 1.5, "w": 1.5, "p": 1.5}
        g_summe = 0.0
        q_lasten = []

        # Werte aufbereiten
        for last in lasten:
            lastfall = last["lastfall"].lower()
            wert = float(last["wert"]) * e
            # kmod = last.get("kmod", 1.0)
            kategorie = last["kategorie"]

            if lastfall == "g":
                g_summe += wert
                last.update({
                    "wert_e": wert,
                    "gamma": gamma["g"],
                    "gamma_label": r"\gamma" + MethodeLastkombi.tiefgestellt("g")
                })
            else:
                si = db.get_si_beiwerte(kategorie)
                if si is None:
                    print(f"⚠️ Fehlender ψ-Wert für Kategorie: {kategorie}")
                    continue
                last.update({
                    "wert_e": wert,
                    "psi0": si.psi0,
                    "gamma": gamma[lastfall],
                    "gamma_label": r"\gamma" + MethodeLastkombi.tiefgestellt(lastfall),
                    "psi_label": r"\psi" + MethodeLastkombi.tiefgestellt("0")
                })
                q_lasten.append(last)

        kombis = {}

        # 1. Nur G
        kmod_g = next((l["kmod"] for l in lasten if l["lastfall"] == "g"), 1.0)
        qd = gamma["g"] * g_summe
        qd_komb = qd / kmod_g

        kombis["G"] = {
            "latex": rf"$\frac{{{gamma['g']:.2f} \cdot G}}{{{kmod_g:.2f}}} = {qd_komb:.2f} \,\text{{kN/m}}$",
        }

        # 2. G + einzelne Q
        for q in q_lasten:
            kmod_max = max(kmod_g, q.get("kmod", 1.0))
            qd = gamma["g"] * g_summe + q["gamma"] * q["wert_e"]
            qd_komb = qd / kmod_max

            latex = rf"$\frac{{{gamma['g']:.2f} \cdot G + {q['gamma']:.2f} \cdot {q['lastfall'].upper()}}}{{{kmod_max:.2f}}} = {qd_komb:.2f} \,\text{{kN/m}}$"
            kombis[f"G + {q['lastfall'].upper()}"] = {
                "latex": latex
            }

        # 3. G + alle Q mit je einer als Leiteinwirkung
        for leit_q in q_lasten:
            leit_gamma = leit_q["gamma"]
            leit_label = leit_q["lastfall"].upper()
            leit_wert = leit_q["wert_e"]

            kmod_max = max([leit_q["kmod"]] + [q["kmod"]
                           for q in q_lasten if q != leit_q] + [kmod_g])
            qd_summe = gamma["g"] * g_summe + leit_gamma * leit_wert

            latex_parts = [rf"{gamma['g']:.2f} \cdot G",
                           rf"{leit_gamma:.2f} \cdot {leit_label}"]

            for neb_q in q_lasten:
                if neb_q == leit_q:
                    continue
                psi = neb_q["psi0"]
                gamma_ = neb_q["gamma"]
                neb_label = neb_q["lastfall"].upper()
                wert = neb_q["wert_e"]

                latex_parts.append(
                    rf"{gamma_:.2f} \cdot {neb_q['psi_label']} \cdot {neb_label}")
                qd_summe += psi * gamma_ * wert

            latex = rf"$\frac{{{' + '.join(latex_parts)}}}{{{kmod_max:.2f}}} = {qd_summe / kmod_max:.2f} \,\text{{kN/m}}$"
            kombis[rf"G + {leit_label} (Leit)"] = {
                "latex": latex
            }

        # 🖨 Ausgabe
        print("\n📐 Lastkombinationen (LaTeX-ready):\n")
        for name, k in kombis.items():
            print(rf"{name}: {k['latex']}")

        return kombis
