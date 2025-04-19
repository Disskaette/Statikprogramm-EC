   def erstelle_feebb_dicts(self):
        """
        Erzeugt zwei Dicts:
        1. GZT: maßgebende Lastkombination mit allen Systemdaten
        2. GZG: jede Einwirkung einzeln, ohne Sicherheitsbeiwerte
        """
        # Querschnittsdaten
        qs = self.eingabemaske.querschnitt_memory
        E = qs["E"]
        I = qs['I_y']  # in mm^4

        # Spannweiten in [m]
        spannweiten = [
            wert for wert in self.eingabemaske.spannweiten_memory.values()]

        all_elements = []
        node_tracker = 0
        lager_knoten = [0]  # Start mit erstem Knoten
        kombis = self.lastenkombination.berechne_dynamische_lastkombination()

        lastwert = [item[1]["Ed"] for item in kombis.items(
        ) if item[1].get("massgebend")][0]  # [kN/m]
        if lastwert is None:
            raise ValueError("❌ Keine maßgebende Lastkombination gefunden!")

        dummy_laenge = 0.001  # mm
        dummy_element = {
            "length": dummy_laenge,
            "youngs_mod": E,
            "moment_of_inertia": I,
            "loads": []
        }

        # Kragarm links: Dummy vor Start einfügen
        if self.eingabemaske.kragarm_links.get():
            all_elements.append(dummy_element.copy())
            node_tracker += 1
            lager_knoten.append(node_tracker)  # Einspannung
            print("🏠 Dummy eingefügt für Kragarm links")

        for idx, feld in enumerate(spannweiten):
            num_elem = int(round(feld * 20))  # 20 Elemente pro m
            elem_laenge = feld * 1000 / num_elem  # in mm

            for _ in range(num_elem):
                all_elements.append({
                    "length": elem_laenge,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [{"type": "udl", "magnitude": lastwert}]
                })

            node_tracker += num_elem
            if idx < len(spannweiten) - 1:
                lager_knoten.append(node_tracker)

        # Kragarm rechts: Dummy hinter letztem Feld
        if self.eingabemaske.kragarm_rechts.get():
            all_elements.append(dummy_element.copy())
            node_tracker += 1
            lager_knoten.append(node_tracker)  # Einspannung
            print("🏠 Dummy eingefügt für Kragarm rechts")

        lager_knoten.append(node_tracker)
        knoten_anzahl = node_tracker + 1

        supports = [[0, 0] for _ in range(knoten_anzahl)]
        for k in lager_knoten:
            supports[k] = [-1, 0]

        # Dummy-Knoten für Einspannung setzen
        if self.eingabemaske.kragarm_links.get():
            supports[lager_knoten[0]] = [0, 0]
            supports[lager_knoten[1]] = [-1, -1]  # Einspannung Kragarm links
        if self.eingabemaske.kragarm_rechts.get():
            supports[lager_knoten[-1]] = [0, 0]
            supports[lager_knoten[-2]] = [-1, -1]  # Einspannung Kragarm rechts

        supports_flat = [v for pair in supports for v in pair]
        print("📌 Lagerknoten mit Randbedingungen:")
        for idx, knoten in enumerate(lager_knoten):
            print(
                f"  • Lager {idx + 1}: Knoten {knoten}, Auflagerbedingungen: {supports[knoten]}")

        # GZT-Dict
        gzt = {
            "elements": all_elements,
            "supports": supports_flat
        }

        # GZG-Dicts mit jeweils einer Einwirkung
        gzg = []
        sprungmass = self.eingabemaske.sprungmass
        for last in self.eingabemaske.lasten_memory:
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





    def erstelle_feebb_dicts(self):
        """
        Erzeugt zwei Dicts:
        1. GZT: maßgebende Lastkombination mit allen Systemdaten
        2. GZG: jede Einwirkung einzeln, ohne Sicherheitsbeiwerte
        """
        qs = self.eingabemaske.querschnitt_memory
        E = qs["E"]
        I = qs["I_y"]  # mm^4
        kombis = self.lastenkombination.berechne_dynamische_lastkombination()

        # GZT-Lastwert (maßgebend)
        lastwert = [item[1]["Ed"] for item in kombis.items()
                    if item[1].get("massgebend")][0]  # [kN/m]
        if lastwert is None:
            raise ValueError("❌ Keine maßgebende Lastkombination gefunden!")

        dummy_laenge = 0.001  # mm
        dummy_element = {
            "length": dummy_laenge,
            "youngs_mod": E,
            "moment_of_inertia": I,
            "loads": []
        }

        all_elements = []
        lager_knoten = []
        node_tracker = 0

        # === Kragarm links ===
        if self.eingabemaske.kragarm_links.get():
            laenge_kragarm = self.eingabemaske.spannweiten_memory['kragarm_links']
            num_elem_kragarm = int(round(laenge_kragarm * 20))
            elem_laenge_kragarm = laenge_kragarm * 1000 / num_elem_kragarm  # mm

            for _ in range(num_elem_kragarm):
                all_elements.append({
                    "length": elem_laenge_kragarm,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [{"type": "udl", "magnitude": lastwert}]
                })

            node_tracker += num_elem_kragarm
            lager_knoten.append(node_tracker)  # Einspannung am Ende des Kragarms

            all_elements.append(dummy_element.copy())  # Dummy danach
            node_tracker += 1
            lager_knoten.append(node_tracker)
            print("🏠 Dummy eingefügt für Kragarm links")

        # === Normale Felder ===
        normale_felder = [
            feld for key, feld in self.eingabemaske.spannweiten_memory.items()
            if key.startswith("feld_")
        ]

        for idx, feld in enumerate(normale_felder):
            num_elem = int(round(feld * 20))
            elem_laenge = feld * 1000 / num_elem  # mm

            for _ in range(num_elem):
                all_elements.append({
                    "length": elem_laenge,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [{"type": "udl", "magnitude": lastwert}]
                })

            node_tracker += num_elem
            if idx < len(normale_felder) - 1:
                lager_knoten.append(node_tracker)  # Zwischenlager

        # === Kragarm rechts ===
        if self.eingabemaske.kragarm_rechts.get():
            all_elements.append(dummy_element.copy())  # Dummy vor dem Kragarm
            node_tracker += 1
            lager_knoten.append(node_tracker)

            laenge_kragarm = self.eingabemaske.spannweiten_memory['kragarm_rechts']
            num_elem_kragarm = int(round(laenge_kragarm * 20))
            elem_laenge_kragarm = laenge_kragarm * 1000 / num_elem_kragarm  # mm

            for _ in range(num_elem_kragarm):
                all_elements.append({
                    "length": elem_laenge_kragarm,
                    "youngs_mod": E,
                    "moment_of_inertia": I,
                    "loads": [{"type": "udl", "magnitude": lastwert}]
                })

            node_tracker += num_elem_kragarm
            lager_knoten.append(node_tracker)  # Einspannung am Ende
            print("🏠 Dummy eingefügt für Kragarm rechts")

        knoten_anzahl = node_tracker + 1
        supports = [[0, 0] for _ in range(knoten_anzahl)]
        for k in lager_knoten:
            supports[k] = [-1, 0]

        # Explizite Einspannungsknoten für Kragarme
        if self.eingabemaske.kragarm_links.get():
            supports[lager_knoten[0]] = [-1, -1]  # Kragarm links → echte Einspannung
        if self.eingabemaske.kragarm_rechts.get():
            supports[lager_knoten[-1]] = [-1, -1]  # Kragarm rechts → echte Einspannung

        supports_flat = [v for pair in supports for v in pair]

        # Debug-Ausgabe
        print("📌 Lagerknoten mit Randbedingungen:")
        for idx, knoten in enumerate(lager_knoten):
            print(f"  • Lager {idx + 1}: Knoten {knoten}, Auflagerbedingungen: {supports[knoten]}")

        print("📋 Übersicht aller Knotenlagerungen:")
        print(f"{'Knoten':>6} | {'u':>5} | {'phi':>5}")
        print("-" * 26)
        for i, (u, phi) in enumerate(supports):
            print(f"{i:>6} | {u:>5} | {phi:>5}")

        # GZT-Dict
        gzt = {
            "elements": all_elements,
            "supports": supports_flat
        }

        # GZG-Dicts mit jeweils einer Einwirkung
        gzg = []
        sprungmass = self.eingabemaske.sprungmass
        for last in self.eingabemaske.lasten_memory:
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
        print("📋 Übersicht aller Knotenlagerungen:")
        print(f"{'Knoten':>6} | {'u':>5} | {'phi':>5}")
        print("-" * 26)
        for i, (u, phi) in enumerate(supports):
            print(f"{i:>6} | {u:>5} | {phi:>5}")
        return gzt, gzg
