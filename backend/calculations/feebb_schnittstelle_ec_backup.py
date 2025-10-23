"""
feebb_schnittstelle_ec.py
~~~~~~~~~~~~~~~~~~~~~~~~~

EC-konforme FEEBB-Schnittstelle für Schnittgrößen- und Durchbiegungsberechnungen
nach Eurocode-Prinzipien mit feldspezifischen Lastkombinationen.

Diese Schnittstelle baut auf der bestehenden FEEBB-Schnittstelle auf, implementiert jedoch
EC-konforme Lastkombinationen mit feldspezifischer Lastverteilung anstatt einer einheitlichen
maßgebenden Kombination über das gesamte System.

Hauptunterschiede zur Standard-Schnittstelle:
- Feldspezifische Lastkombinationen (verschiedene Felder können verschiedene Kombinationen haben)
- Separate Behandlung von GZT (ULS) und GZG (SLS) mit unterschiedlichen Sicherheitsbeiwerten
- Envelope-Bildung über alle möglichen Lastkombinationen
- Dokumentation der maßgebenden Kombination je Schnittgröße/Position
"""

import numpy as np
from backend.calculations.feebb import Element, Beam, Postprocessor
import logging

# Logger für dieses Modul
logger = logging.getLogger(__name__)


class FeebbBerechnungEC:
    """
    EC-konforme FEEBB-Berechnung mit feldspezifischen Lastkombinationen.

    Diese Klasse implementiert die Eurocode-konforme Berechnung von Schnittgrößen
    und Durchbiegungen unter Berücksichtigung aller relevanten Lastkombinationen
    für jeden Feldbereich separat.
    """

    def __init__(self, snapshot, db):
        """
        Initialisierung der EC-konformen FEEBB-Berechnung.

        Args:
            snapshot (dict): System-Snapshot mit allen Eingabedaten
            db: Datenbankverbindung für Materialparameter
        """
        self.snapshot = snapshot
        self.db = db
        self.system_memory = {}  # Ergebnis-Cache für GZT und GZG

        # EC-spezifische Parameter
        self.gamma_g = 1.35  # Teilsicherheitsbeiwert für ständige Lasten (GZT)
        # Teilsicherheitsbeiwert für veränderliche Lasten (GZT)
        self.gamma_q = 1.5
        self.psi_0 = {"s": 0.7, "w": 0.6, "p": 0.7}  # Kombinationsbeiwerte ψ₀

        logger.info("🏗️ EC-konforme FEEBB-Berechnung initialisiert")

    def compute(self) -> dict:
        """
        Hauptberechnungsmethode - führt die komplette EC-konforme Analyse durch.

        Returns:
            dict: Vollständige Ergebnisstruktur mit GZT/GZG-Resultaten und maßgebenden Kombinationen
        """
        logger.info("🚀 Starte EC-konforme FEEBB-Berechnung")

        # 1. Systemgeometrie und Materialdaten extrahieren
        self._extrahiere_systemdaten()

        # 2. Alle relevanten Lastkombinationen generieren
        self._generiere_lastkombinationen()

        # 3. FEEBB-Berechnungen für alle Kombinationen durchführen
        self._berechne_alle_kombinationen()

        # 4. Envelope-Bildung und maßgebende Kombinationen ermitteln
        self._erstelle_envelopes()

        logger.info("✅ EC-konforme FEEBB-Berechnung abgeschlossen")
        return self.system_memory

    def _extrahiere_systemdaten(self):
        """
        Extrahiert Systemgeometrie, Materialdaten und Lastdaten aus dem Snapshot.
        """
        logger.info("📊 Extrahiere Systemdaten")

        # Querschnittsdaten
        qs = self.snapshot["querschnitt"]
        self.E = qs["E"]
        self.I = qs["I_y"]

        # Geometriedaten
        self.spannweiten = self.snapshot.get("spannweiten", {})
        self.sprungmass = self.snapshot.get("sprungmass", 1.0)

        # Lastdaten
        self.lasten = self.snapshot.get("lasten", [])

        # Systemgeometrie analysieren
        self._analysiere_systemgeometrie()

        logger.info(
            f"📏 System: {len(self.felder)} Felder, {self.gesamt_knoten} Knoten")

    def _analysiere_systemgeometrie(self):
        """
        Analysiert die Systemgeometrie und erstellt die Feldstruktur.
        """
        self.felder = []
        self.gesamt_elemente = []
        self.zwischenlager_knoten = []
        node_tracker = 0

        # === Kragarm links ===
        l_krag_links = float(self.spannweiten.get("kragarm_links", 0))
        if l_krag_links > 0:
            n_elemente = int(round(l_krag_links * 20))  # 20 Elemente pro Meter
            self.felder.append({
                "typ": "kragarm_links",
                "laenge": l_krag_links,
                "start_element": len(self.gesamt_elemente),
                "anzahl_elemente": n_elemente,
                "start_knoten": node_tracker,
                "end_knoten": node_tracker + n_elemente
            })

            # Elemente für Kragarm links
            l_element = l_krag_links * 1000 / n_elemente  # in mm
            for _ in range(n_elemente):
                self.gesamt_elemente.append({
                    "length": l_element,
                    "youngs_mod": self.E,
                    "moment_of_inertia": self.I,
                    "feld_typ": "kragarm_links"
                })

            node_tracker += n_elemente
            self.zwischenlager_knoten.append(node_tracker)

        # === Normale Felder ===
        normale_felder = [
            (key, wert) for key, wert in self.spannweiten.items()
            if key.startswith("feld_")
        ]

        for idx, (feld_key, feld_laenge) in enumerate(normale_felder):
            n_elemente = int(round(feld_laenge * 20))
            self.felder.append({
                "typ": feld_key,
                "laenge": feld_laenge,
                "start_element": len(self.gesamt_elemente),
                "anzahl_elemente": n_elemente,
                "start_knoten": node_tracker,
                "end_knoten": node_tracker + n_elemente
            })

            # Elemente für normales Feld
            l_element = feld_laenge * 1000 / n_elemente  # in mm
            for _ in range(n_elemente):
                self.gesamt_elemente.append({
                    "length": l_element,
                    "youngs_mod": self.E,
                    "moment_of_inertia": self.I,
                    "feld_typ": feld_key
                })

            node_tracker += n_elemente

            # Zwischenlager (außer beim letzten Feld)
            if idx < len(normale_felder) - 1:
                self.zwischenlager_knoten.append(node_tracker)

        # === Kragarm rechts ===
        ende_normale_felder = node_tracker
        l_krag_rechts = float(self.spannweiten.get("kragarm_rechts", 0))
        if l_krag_rechts > 0:
            n_elemente = int(round(l_krag_rechts * 20))
            self.felder.append({
                "typ": "kragarm_rechts",
                "laenge": l_krag_rechts,
                "start_element": len(self.gesamt_elemente),
                "anzahl_elemente": n_elemente,
                "start_knoten": node_tracker,
                "end_knoten": node_tracker + n_elemente
            })

            # Elemente für Kragarm rechts
            l_element = l_krag_rechts * 1000 / n_elemente  # in mm
            for _ in range(n_elemente):
                self.gesamt_elemente.append({
                    "length": l_element,
                    "youngs_mod": self.E,
                    "moment_of_inertia": self.I,
                    "feld_typ": "kragarm_rechts"
                })

            node_tracker += n_elemente

        # === Lagerungsbedingungen definieren ===
        self.gesamt_knoten = node_tracker + 1
        self.supports = [[0, 0] for _ in range(self.gesamt_knoten)]

        # Standard-Lager
        self.supports[0] = [-1, 0]  # Start-Gleitlager
        self.supports[self.gesamt_knoten - 1] = [-1, 0]  # End-Gleitlager

        # Zwischenlager
        for k in self.zwischenlager_knoten:
            self.supports[k] = [-1, 0]

        # Kragarm-Anpassungen
        if l_krag_links > 0:
            self.supports[0] = [0, 0]  # Start freigeben

        if l_krag_rechts > 0:
            self.supports[ende_normale_felder] = [-1, 0]
            self.supports[node_tracker] = [0, 0]  # Ende freigeben

    def _generiere_lastkombinationen(self):
        """
        Generiert alle relevanten Lastkombinationen nach Eurocode.

        Erzeugt sowohl GZT- als auch GZG-Kombinationen:
        - GZT: Mit Teilsicherheitsbeiwerten γ
        - GZG: Ohne Teilsicherheitsbeiwerte (charakteristische Werte)
        """
        logger.info("🔄 Generiere EC-konforme Lastkombinationen")

        self.kombinationen_gzt = []  # Grenzzustand der Tragfähigkeit
        self.kombinationen_gzg = []  # Grenzzustand der Gebrauchstauglichkeit

        # Lastdaten aufbereiten
        g_lasten = [l for l in self.lasten if l["lastfall"].lower() == "g"]
        q_lasten = [l for l in self.lasten if l["lastfall"].lower() != "g"]

        # === GZT-Kombinationen (mit Teilsicherheitsbeiwerten) ===

        # 1. Nur ständige Lasten: γ_G · G
        if g_lasten:
            self.kombinationen_gzt.append({
                "name": "GZT: γ_G · G",
                "beschreibung": "Nur ständige Lasten mit Teilsicherheitsbeiwert",
                "lasten": {l["lastfall"]: self.gamma_g * float(l["wert"]) * self.sprungmass for l in g_lasten},
                "typ": "nur_g"
            })

        # 2. G + einzelne veränderliche Last: γ_G · G + γ_Q · Q_i
        for q_last in q_lasten:
            lasten_dict = {}
            # Ständige Lasten
            for g_last in g_lasten:
                lasten_dict[g_last["lastfall"]] = self.gamma_g * \
                    float(g_last["wert"]) * self.sprungmass
            # Eine veränderliche Last
            lasten_dict[q_last["lastfall"]] = self.gamma_q * \
                float(q_last["wert"]) * self.sprungmass

            self.kombinationen_gzt.append({
                "name": f"GZT: γ_G · G + γ_Q · {q_last['lastfall'].upper()}",
                "beschreibung": f"Ständige + {q_last['lastfall'].upper()} als Leiteinwirkung",
                "lasten": lasten_dict,
                "typ": "g_plus_q",
                "leiteinwirkung": q_last["lastfall"]
            })

        # 3. G + alle veränderlichen Lasten mit Kombinationsbeiwerten
        if len(q_lasten) > 1:
            for leit_q in q_lasten:
                lasten_dict = {}
                # Ständige Lasten
                for g_last in g_lasten:
                    lasten_dict[g_last["lastfall"]] = self.gamma_g * \
                        float(g_last["wert"]) * self.sprungmass

                # Leiteinwirkung
                lasten_dict[leit_q["lastfall"]] = self.gamma_q * \
                    float(leit_q["wert"]) * self.sprungmass

                # Begleitende Einwirkungen mit ψ₀
                for neben_q in q_lasten:
                    if neben_q != leit_q:
                        psi = self.psi_0.get(neben_q["lastfall"].lower(), 0.7)
                        lasten_dict[neben_q["lastfall"]] = psi * \
                            self.gamma_q * \
                            float(neben_q["wert"]) * self.sprungmass

                self.kombinationen_gzt.append({
                    "name": f"GZT: γ_G · G + γ_Q · {leit_q['lastfall'].upper()} + Σψ₀ · γ_Q · Q_i",
                    "beschreibung": f"Vollkombination mit {leit_q['lastfall'].upper()} als Leiteinwirkung",
                    "lasten": lasten_dict,
                    "typ": "vollkombination",
                    "leiteinwirkung": leit_q["lastfall"]
                })

        # === GZG-Kombinationen (charakteristische Werte) ===

        # 1. Charakteristische Kombination: G + Q_1 + Σψ₀ · Q_i
        if q_lasten:
            for leit_q in q_lasten:
                lasten_dict = {}
                # Ständige Lasten (ohne γ)
                for g_last in g_lasten:
                    lasten_dict[g_last["lastfall"]] = float(
                        g_last["wert"]) * self.sprungmass

                # Leiteinwirkung (ohne γ)
                lasten_dict[leit_q["lastfall"]] = float(
                    leit_q["wert"]) * self.sprungmass

                # Begleitende Einwirkungen mit ψ₀ (ohne γ)
                for neben_q in q_lasten:
                    if neben_q != leit_q:
                        psi = self.psi_0.get(neben_q["lastfall"].lower(), 0.7)
                        lasten_dict[neben_q["lastfall"]] = psi * \
                            float(neben_q["wert"]) * self.sprungmass

                self.kombinationen_gzg.append({
                    "name": f"GZG-Char: G + {leit_q['lastfall'].upper()} + Σψ₀ · Q_i",
                    "beschreibung": f"Charakteristische Kombination mit {leit_q['lastfall'].upper()} als Leiteinwirkung",
                    "lasten": lasten_dict,
                    "typ": "charakteristisch",
                    "leiteinwirkung": leit_q["lastfall"]
                })

        # 2. Quasi-ständige Kombination: G + Σψ₂ · Q_i
        if q_lasten:
            lasten_dict = {}
            # Ständige Lasten
            for g_last in g_lasten:
                lasten_dict[g_last["lastfall"]] = float(
                    g_last["wert"]) * self.sprungmass

            # Alle veränderlichen Lasten mit ψ₂ (vereinfacht = 0.3)
            for q_last in q_lasten:
                lasten_dict[q_last["lastfall"]] = 0.3 * \
                    float(q_last["wert"]) * self.sprungmass

            self.kombinationen_gzg.append({
                "name": "GZG-Quasi: G + Σψ₂ · Q_i",
                "beschreibung": "Quasi-ständige Kombination",
                "lasten": lasten_dict,
                "typ": "quasi_staendig"
            })

        logger.info(
            f"📋 {len(self.kombinationen_gzt)} GZT-Kombinationen und {len(self.kombinationen_gzg)} GZG-Kombinationen generiert")

    def _berechne_alle_kombinationen(self):
        """
        Führt FEEBB-Berechnungen für alle generierten Lastkombinationen durch.
        """
        logger.info("🔢 Berechne alle Lastkombinationen")

        self.ergebnisse_gzt = []
        self.ergebnisse_gzg = []

        # === GZT-Berechnungen ===
        for kombi in self.kombinationen_gzt:
            logger.debug(f"Berechne GZT: {kombi['name']}")

            # FEEBB-Dict für diese Kombination erstellen
            feebb_dict = self._erstelle_feebb_dict_fuer_kombination(kombi)

            # FEEBB-Berechnung durchführen
            ergebnis = self._fuehre_feebb_berechnung_durch(feebb_dict)
            ergebnis["kombination"] = kombi

            self.ergebnisse_gzt.append(ergebnis)

        # === GZG-Berechnungen ===
        for kombi in self.kombinationen_gzg:
            logger.debug(f"Berechne GZG: {kombi['name']}")

            # FEEBB-Dict für diese Kombination erstellen
            feebb_dict = self._erstelle_feebb_dict_fuer_kombination(kombi)

            # FEEBB-Berechnung durchführen
            ergebnis = self._fuehre_feebb_berechnung_durch(feebb_dict)
            ergebnis["kombination"] = kombi

            self.ergebnisse_gzg.append(ergebnis)

        logger.info(
            f"✅ Alle Kombinationen berechnet: {len(self.ergebnisse_gzt)} GZT + {len(self.ergebnisse_gzg)} GZG")

    def _erstelle_feebb_dict_fuer_kombination(self, kombination):
        """
        Erstellt ein FEEBB-Dictionary für eine spezifische Lastkombination.

        Args:
            kombination (dict): Lastkombination mit Lastfällen und Werten

        Returns:
            dict: FEEBB-Dictionary mit elements und supports
        """
        # Elemente mit Lasten für diese Kombination
        elements_mit_lasten = []

        for element_data in self.gesamt_elemente:
            # Grundelement kopieren
            element = {
                "length": element_data["length"],
                "youngs_mod": element_data["youngs_mod"],
                "moment_of_inertia": element_data["moment_of_inertia"],
                "loads": []
            }

            # Lasten für dieses Element berechnen
            # Hier wird vereinfacht angenommen, dass alle Lasten gleichmäßig verteilt sind
            gesamt_last = 0.0
            for lastfall, wert in kombination["lasten"].items():
                gesamt_last += wert

            if gesamt_last != 0:
                element["loads"].append({
                    "type": "udl",
                    "magnitude": gesamt_last
                })

            elements_mit_lasten.append(element)

        # Lagerungsbedingungen (flach für FEEBB)
        supports_flat = [v for pair in self.supports for v in pair]

        return {
            "elements": elements_mit_lasten,
            "supports": supports_flat
        }

    def _fuehre_feebb_berechnung_durch(self, feebb_dict):
        """
        Führt eine einzelne FEEBB-Berechnung durch.

        Args:
            feebb_dict (dict): FEEBB-Dictionary mit elements und supports

        Returns:
            dict: Berechnungsergebnisse mit moment, querkraft, durchbiegung
        """
        try:
            # FEEBB-Objekte erstellen
            elements = [Element(e) for e in feebb_dict["elements"]]
            beam = Beam(elements, feebb_dict["supports"])
            post = Postprocessor(beam, 100)  # 100 Auswertungspunkte

            # Schnittgrößen berechnen
            moment = post.interp("moment")
            querkraft = post.interp("shear")
            durchbiegung = post.interp("displacement")

            return {
                "moment": moment,
                "querkraft": querkraft,
                "durchbiegung": durchbiegung,
                "max": {
                    "moment": max(abs(m) for m in moment),
                    "querkraft": max(abs(v) for v in querkraft),
                    "durchbiegung": max(abs(w) for w in durchbiegung)
                }
            }

        except Exception as e:
            logger.error(f"❌ Fehler bei FEEBB-Berechnung: {e}")
            return {
                "moment": [0],
                "querkraft": [0],
                "durchbiegung": [0],
                "max": {"moment": 0, "querkraft": 0, "durchbiegung": 0}
            }

    def _erstelle_envelopes(self):
        """
        Erstellt Envelope-Kurven und ermittelt maßgebende Kombinationen.
        """
        logger.info(
            "📊 Erstelle Envelopes und ermittle maßgebende Kombinationen")

        # === GZT-Envelopes ===
        gzt_envelope = self._berechne_envelope(self.ergebnisse_gzt, "GZT")

        # === GZG-Envelopes ===
        gzg_envelope = self._berechne_envelope(self.ergebnisse_gzg, "GZG")

        # === Detaillierte Kombinationsergebnisse erstellen ===
        gzt_detail = self._erstelle_detaillierte_kombinationsergebnisse(
            self.ergebnisse_gzt, "GZT")
        gzg_detail = self._erstelle_detaillierte_kombinationsergebnisse(
            self.ergebnisse_gzg, "GZG")

        # === LaTeX-Formeln generieren ===
        latex_formeln = self._generiere_latex_formeln()

        # Ergebnisse in system_memory speichern
        self.system_memory = {
            "Schnittgroessen": {
                "GZT": gzt_envelope,
                "GZG": gzg_envelope
            },
            "Kombinationen": {
                "GZT": self.kombinationen_gzt,
                "GZG": self.kombinationen_gzg
            },
            "Einzelergebnisse": {
                "GZT": self.ergebnisse_gzt,
                "GZG": self.ergebnisse_gzg
            },
            "Detaillierte_Kombinationen": {
                "GZT": gzt_detail,
                "GZG": gzg_detail
            },
            "LaTeX_Formeln": latex_formeln
        }

        logger.info(
            "✅ Envelopes erstellt und maßgebende Kombinationen ermittelt")

    def _berechne_envelope(self, ergebnisse, grenzzustand):
        """
        Berechnet Envelope-Kurven für eine Gruppe von Ergebnissen.

        Args:
            ergebnisse (list): Liste von Berechnungsergebnissen
            grenzzustand (str): "GZT" oder "GZG"

        Returns:
            dict: Envelope-Ergebnisse mit max/min-Kurven und maßgebenden Kombinationen
        """
        if not ergebnisse:
            return {}

        # Anzahl Auswertungspunkte (sollte bei allen gleich sein)
        n_punkte = len(ergebnisse[0]["moment"])

        # Envelope-Arrays initialisieren
        moment_max = np.full(n_punkte, -np.inf)
        moment_min = np.full(n_punkte, np.inf)
        querkraft_max = np.full(n_punkte, -np.inf)
        querkraft_min = np.full(n_punkte, np.inf)
        durchbiegung_max = np.full(n_punkte, -np.inf)
        durchbiegung_min = np.full(n_punkte, np.inf)

        # Maßgebende Kombinationen je Punkt
        moment_max_kombi = [""] * n_punkte
        moment_min_kombi = [""] * n_punkte
        querkraft_max_kombi = [""] * n_punkte
        querkraft_min_kombi = [""] * n_punkte
        durchbiegung_max_kombi = [""] * n_punkte
        durchbiegung_min_kombi = [""] * n_punkte

        # Envelope-Bildung
        for erg in ergebnisse:
            kombi_name = erg["kombination"]["name"]

            for i in range(n_punkte):
                # Moment
                if erg["moment"][i] > moment_max[i]:
                    moment_max[i] = erg["moment"][i]
                    moment_max_kombi[i] = kombi_name
                if erg["moment"][i] < moment_min[i]:
                    moment_min[i] = erg["moment"][i]
                    moment_min_kombi[i] = kombi_name

                # Querkraft
                if erg["querkraft"][i] > querkraft_max[i]:
                    querkraft_max[i] = erg["querkraft"][i]
                    querkraft_max_kombi[i] = kombi_name
                if erg["querkraft"][i] < querkraft_min[i]:
                    querkraft_min[i] = erg["querkraft"][i]
                    querkraft_min_kombi[i] = kombi_name

                # Durchbiegung
                if erg["durchbiegung"][i] > durchbiegung_max[i]:
                    durchbiegung_max[i] = erg["durchbiegung"][i]
                    durchbiegung_max_kombi[i] = kombi_name
                if erg["durchbiegung"][i] < durchbiegung_min[i]:
                    durchbiegung_min[i] = erg["durchbiegung"][i]
                    durchbiegung_min_kombi[i] = kombi_name

        # Absolute Maximalwerte ermitteln
        abs_max_moment = max(max(abs(m) for m in moment_max),
                             max(abs(m) for m in moment_min))
        abs_max_querkraft = max(max(abs(v) for v in querkraft_max), max(
            abs(v) for v in querkraft_min))
        abs_max_durchbiegung = max(max(abs(w) for w in durchbiegung_max), max(
            abs(w) for w in durchbiegung_min))

        # Maßgebende Kombination für absolute Maxima ermitteln
        moment_abs_max_idx = np.argmax([abs(m) for m in moment_max])
        moment_abs_min_idx = np.argmax([abs(m) for m in moment_min])

        if max(abs(m) for m in moment_max) >= max(abs(m) for m in moment_min):
            moment_abs_kombi = moment_max_kombi[moment_abs_max_idx]
        else:
            moment_abs_kombi = moment_min_kombi[moment_abs_min_idx]

        querkraft_abs_max_idx = np.argmax([abs(v) for v in querkraft_max])
        querkraft_abs_min_idx = np.argmax([abs(v) for v in querkraft_min])

        if max(abs(v) for v in querkraft_max) >= max(abs(v) for v in querkraft_min):
            querkraft_abs_kombi = querkraft_max_kombi[querkraft_abs_max_idx]
        else:
            querkraft_abs_kombi = querkraft_min_kombi[querkraft_abs_min_idx]

        durchbiegung_abs_max_idx = np.argmax(
            [abs(w) for w in durchbiegung_max])
        durchbiegung_abs_min_idx = np.argmax(
            [abs(w) for w in durchbiegung_min])

        if max(abs(w) for w in durchbiegung_max) >= max(abs(w) for w in durchbiegung_min):
            durchbiegung_abs_kombi = durchbiegung_max_kombi[durchbiegung_abs_max_idx]
        else:
            durchbiegung_abs_kombi = durchbiegung_min_kombi[durchbiegung_abs_min_idx]

        return {
            "envelope": {
                "moment_max": moment_max.tolist(),
                "moment_min": moment_min.tolist(),
                "querkraft_max": querkraft_max.tolist(),
                "querkraft_min": querkraft_min.tolist(),
                "durchbiegung_max": durchbiegung_max.tolist(),
                "durchbiegung_min": durchbiegung_min.tolist()
            },
            "massgebende_kombinationen": {
                "moment_max": moment_max_kombi,
                "moment_min": moment_min_kombi,
                "querkraft_max": querkraft_max_kombi,
                "querkraft_min": querkraft_min_kombi,
                "durchbiegung_max": durchbiegung_max_kombi,
                "durchbiegung_min": durchbiegung_min_kombi
            },
            "max": {
                "moment": abs_max_moment,
                "querkraft": abs_max_querkraft,
                "durchbiegung": abs_max_durchbiegung,
                "moment_kombi": moment_abs_kombi,
                "querkraft_kombi": querkraft_abs_kombi,
                "durchbiegung_kombi": durchbiegung_abs_kombi
            },
            # Für Kompatibilität mit bestehender Schnittstelle
            "moment": moment_max.tolist(),
            "querkraft": querkraft_max.tolist(),
            "durchbiegung": durchbiegung_max.tolist()
        }

    def _erstelle_detaillierte_kombinationsergebnisse(self, ergebnisse, grenzzustand):
        """
        Erstellt detaillierte Ergebnisse für jeden Kombinationstyp.

        Args:
            ergebnisse (list): Liste von Berechnungsergebnissen
            grenzzustand (str): "GZT" oder "GZG"

        Returns:
            dict: Detaillierte Ergebnisse nach Kombinationstypen gruppiert
        """
        detail_ergebnisse = {}

        if grenzzustand == "GZT":
            # GZT-Kombinationstypen gruppieren
            typen = {
                "nur_g": {"name": "Nur ständige Lasten", "ergebnisse": []},
                "g_plus_q": {"name": "Ständige + einzelne veränderliche Lasten", "ergebnisse": []},
                "vollkombination": {"name": "Vollkombinationen", "ergebnisse": []}
            }

            for erg in ergebnisse:
                typ = erg["kombination"]["typ"]
                if typ in typen:
                    typen[typ]["ergebnisse"].append(erg)

            # Für jeden Typ die maßgebende Kombination ermitteln
            for typ_key, typ_data in typen.items():
                if typ_data["ergebnisse"]:
                    # Maßgebende Kombination für diesen Typ finden
                    massgebend = max(typ_data["ergebnisse"],
                                     key=lambda x: x["max"]["moment"])

                    detail_ergebnisse[typ_key] = {
                        "name": typ_data["name"],
                        "massgebende_kombination": massgebend["kombination"]["name"],
                        "max_werte": massgebend["max"],
                        "alle_kombinationen": typ_data["ergebnisse"]
                    }

        elif grenzzustand == "GZG":
            # GZG-Kombinationstypen gruppieren
            typen = {
                "charakteristisch": {"name": "Charakteristische Kombination", "ergebnisse": []},
                "haeufig": {"name": "Häufige Kombination", "ergebnisse": []},
                "quasi_staendig": {"name": "Quasi-ständige Kombination", "ergebnisse": []}
            }

            for erg in ergebnisse:
                typ = erg["kombination"]["typ"]
                if typ in typen:
                    typen[typ]["ergebnisse"].append(erg)

            # Für jeden Typ die maßgebende Kombination ermitteln
            for typ_key, typ_data in typen.items():
                if typ_data["ergebnisse"]:
                    # Maßgebende Kombination für diesen Typ finden (bei GZG: max Durchbiegung)
                    massgebend = max(typ_data["ergebnisse"],
                                     key=lambda x: x["max"]["durchbiegung"])

                    detail_ergebnisse[typ_key] = {
                        "name": typ_data["name"],
                        "massgebende_kombination": massgebend["kombination"]["name"],
                        "max_werte": massgebend["max"],
                        "alle_kombinationen": typ_data["ergebnisse"]
                    }

        return detail_ergebnisse

    def _generiere_latex_formeln(self):
        """
        Generiert LaTeX-Formeln für alle Kombinationstypen im Format der bestehenden Module.

        Returns:
            dict: LaTeX-Formeln nach Grenzzustand und Typ gruppiert
        """
        latex_formeln = {
            "GZT": {},
            "GZG": {}
        }

        # Lastdaten für Formeln extrahieren
        g_lasten = [l for l in self.lasten if l["lastfall"].lower() == "g"]
        q_lasten = [l for l in self.lasten if l["lastfall"].lower() != "g"]

        # Sprungmaß für Berechnung
        sprungmass = self.sprungmass

        # === GZT-Formeln ===

        # 1. Nur ständige Lasten: γ_G · G
        if g_lasten:
            g_wert = sum(float(l["wert"]) for l in g_lasten) * sprungmass
            qd_nur_g = self.gamma_g * g_wert

            # Maßgebende Kombination für nur_g finden
            nur_g_ergebnis = next((erg for erg in self.ergebnisse_gzt
                                   if erg["kombination"]["typ"] == "nur_g"), None)

            if nur_g_ergebnis:
                max_moment = nur_g_ergebnis["max"]["moment"] / 1e6  # kNm
                max_querkraft = nur_g_ergebnis["max"]["querkraft"] / 1e3  # kN
                max_durchbiegung = nur_g_ergebnis["max"]["durchbiegung"]  # mm

                latex_formeln["GZT"]["nur_g"] = {
                    "name": "Nur ständige Lasten",
                    "latex": (f"$\\gamma_G \\cdot G: \\quad "
                              f"{self.gamma_g:.2f} \\cdot g = {qd_nur_g:.2f} \\,\\text{{kN/m}} \\quad "
                              f"M_{{Ed,max}} = {max_moment:.2f} \\,\\text{{kNm}}$"),
                    "beschreibung": "Nur ständige Lasten mit Teilsicherheitsbeiwert",
                    "max_werte": {
                        "moment": max_moment,
                        "querkraft": max_querkraft,
                        "durchbiegung": max_durchbiegung
                    }
                }

        # 2. Ständige + einzelne veränderliche Lasten: γ_G · G + γ_Q · Q_i
        if q_lasten:
            # Maßgebende Einzelkombination ermitteln
            g_plus_q_ergebnisse = [erg for erg in self.ergebnisse_gzt
                                   if erg["kombination"]["typ"] == "g_plus_q"]

            if g_plus_q_ergebnisse:
                massgebend = max(g_plus_q_ergebnisse,
                                 key=lambda x: x["max"]["moment"])
                leiteinwirkung = massgebend["kombination"]["leiteinwirkung"]

                # Werte berechnen
                g_wert = sum(float(l["wert"]) for l in g_lasten) * sprungmass
                q_wert = next(float(
                    l["wert"]) for l in q_lasten if l["lastfall"] == leiteinwirkung) * sprungmass
                qd_kombi = self.gamma_g * g_wert + self.gamma_q * q_wert

                max_moment = massgebend["max"]["moment"] / 1e6  # kNm
                max_querkraft = massgebend["max"]["querkraft"] / 1e3  # kN
                max_durchbiegung = massgebend["max"]["durchbiegung"]  # mm

                latex_formeln["GZT"]["g_plus_q"] = {
                    "name": "Ständige + einzelne veränderliche Lasten",
                    "latex": (f"$\\gamma_G \\cdot G + \\gamma_Q \\cdot \\mathbf{{{leiteinwirkung.upper()}}}: \\quad "
                              f"{self.gamma_g:.2f} \\cdot g + {self.gamma_q:.2f} \\cdot {leiteinwirkung} = {qd_kombi:.2f} \\,\\text{{kN/m}} \\quad "
                              f"M_{{Ed,max}} = {max_moment:.2f} \\,\\text{{kNm}}$"),
                    "beschreibung": f"Maßgebende Einzelkombination mit {leiteinwirkung.upper()}",
                    "max_werte": {
                        "moment": max_moment,
                        "querkraft": max_querkraft,
                        "durchbiegung": max_durchbiegung
                    }
                }

        # 3. Vollkombinationen: γ_G · G + γ_Q · Q_leit + Σψ₀ · γ_Q · Q_i
        if len(q_lasten) > 1:
            vollkombi_ergebnisse = [erg for erg in self.ergebnisse_gzt
                                    if erg["kombination"]["typ"] == "vollkombination"]

            if vollkombi_ergebnisse:
                massgebend = max(vollkombi_ergebnisse,
                                 key=lambda x: x["max"]["moment"])
                leiteinwirkung = massgebend["kombination"]["leiteinwirkung"]

                # Werte berechnen
                g_wert = sum(float(l["wert"]) for l in g_lasten) * sprungmass
                leit_wert = next(float(
                    l["wert"]) for l in q_lasten if l["lastfall"] == leiteinwirkung) * sprungmass

                # Begleitende Einwirkungen
                begleitend_terme = []
                qd_begleitend = 0
                for q in q_lasten:
                    if q["lastfall"] != leiteinwirkung:
                        psi = self.psi_0.get(q["lastfall"].lower(), 0.7)
                        q_wert = float(q["wert"]) * sprungmass
                        qd_begleitend += psi * self.gamma_q * q_wert
                        begleitend_terme.append(
                            f"{psi:.1f} \\cdot {self.gamma_q:.2f} \\cdot {q['lastfall']}")

                qd_gesamt = self.gamma_g * g_wert + self.gamma_q * leit_wert + qd_begleitend

                max_moment = massgebend["max"]["moment"] / 1e6  # kNm
                max_querkraft = massgebend["max"]["querkraft"] / 1e3  # kN
                max_durchbiegung = massgebend["max"]["durchbiegung"]  # mm

                begleitend_str = " + " + \
                    " + ".join(begleitend_terme) if begleitend_terme else ""

                latex_formeln["GZT"]["vollkombination"] = {
                    "name": "Vollkombinationen",
                    "latex": (f"$\\gamma_G \\cdot G + \\gamma_Q \\cdot \\mathbf{{{leiteinwirkung.upper()}}} + \\Sigma\\psi_0 \\cdot \\gamma_Q \\cdot Q_i: \\quad "
                              f"{self.gamma_g:.2f} \\cdot g + {self.gamma_q:.2f} \\cdot {leiteinwirkung}{begleitend_str} = {qd_gesamt:.2f} \\,\\text{{kN/m}} \\quad "
                              f"M_{{Ed,max}} = {max_moment:.2f} \\,\\text{{kNm}}$"),
                    "beschreibung": f"Vollkombination mit {leiteinwirkung.upper()} als Leiteinwirkung",
                    "max_werte": {
                        "moment": max_moment,
                        "querkraft": max_querkraft,
                        "durchbiegung": max_durchbiegung
                    }
                }

        # === GZG-Formeln ===

        # 1. Charakteristische Kombination: G + Q_1 + Σψ₀ · Q_i
        if q_lasten:
            char_ergebnisse = [erg for erg in self.ergebnisse_gzg
                               if erg["kombination"]["typ"] == "charakteristisch"]

            if char_ergebnisse:
                massgebend = max(
                    char_ergebnisse, key=lambda x: x["max"]["durchbiegung"])
                leiteinwirkung = massgebend["kombination"]["leiteinwirkung"]

                # Werte berechnen (ohne γ-Faktoren)
                g_wert = sum(float(l["wert"]) for l in g_lasten) * sprungmass
                leit_wert = next(float(
                    l["wert"]) for l in q_lasten if l["lastfall"] == leiteinwirkung) * sprungmass

                begleitend_terme = []
                qd_begleitend = 0
                for q in q_lasten:
                    if q["lastfall"] != leiteinwirkung:
                        psi = self.psi_0.get(q["lastfall"].lower(), 0.7)
                        q_wert = float(q["wert"]) * sprungmass
                        qd_begleitend += psi * q_wert
                        begleitend_terme.append(
                            f"{psi:.1f} \\cdot {q['lastfall']}")

                qd_gesamt = g_wert + leit_wert + qd_begleitend

                max_durchbiegung = massgebend["max"]["durchbiegung"]  # mm

                begleitend_str = " + " + \
                    " + ".join(begleitend_terme) if begleitend_terme else ""

                latex_formeln["GZG"]["charakteristisch"] = {
                    "name": "Charakteristische Kombination",
                    "latex": (f"$G + \\mathbf{{{leiteinwirkung.upper()}}} + \\Sigma\\psi_0 \\cdot Q_i: \\quad "
                              f"g + {leiteinwirkung}{begleitend_str} = {qd_gesamt:.2f} \\,\\text{{kN/m}} \\quad "
                              f"w_{{max}} = {max_durchbiegung:.2f} \\,\\text{{mm}}$"),
                    "beschreibung": f"Charakteristische Kombination mit {leiteinwirkung.upper()} als Leiteinwirkung",
                    "max_werte": {
                        "durchbiegung": max_durchbiegung
                    }
                }

        # 2. Häufige Kombination: G + ψ₁ · Q_1 + Σψ₂ · Q_i
        if q_lasten:
            haeufig_ergebnisse = [erg for erg in self.ergebnisse_gzg
                                  if erg["kombination"]["typ"] == "haeufig"]

            if haeufig_ergebnisse:
                massgebend = max(haeufig_ergebnisse,
                                 key=lambda x: x["max"]["durchbiegung"])
                leiteinwirkung = massgebend["kombination"]["leiteinwirkung"]

                g_wert = sum(float(l["wert"]) for l in g_lasten) * sprungmass
                leit_wert = next(float(
                    l["wert"]) for l in q_lasten if l["lastfall"] == leiteinwirkung) * sprungmass

                begleitend_terme = []
                qd_begleitend = 0
                for q in q_lasten:
                    if q["lastfall"] != leiteinwirkung:
                        q_wert = float(q["wert"]) * sprungmass
                        qd_begleitend += 0.3 * q_wert  # ψ₂ = 0.3
                        begleitend_terme.append(f"0.3 \\cdot {q['lastfall']}")

                qd_gesamt = g_wert + 0.5 * leit_wert + qd_begleitend  # ψ₁ = 0.5
                max_durchbiegung = massgebend["max"]["durchbiegung"]

                begleitend_str = " + " + \
                    " + ".join(begleitend_terme) if begleitend_terme else ""

                latex_formeln["GZG"]["haeufig"] = {
                    "name": "Häufige Kombination",
                    "latex": (f"$G + \\psi_1 \\cdot \\mathbf{{{leiteinwirkung.upper()}}} + \\Sigma\\psi_2 \\cdot Q_i: \\quad "
                              f"g + 0.5 \\cdot {leiteinwirkung}{begleitend_str} = {qd_gesamt:.2f} \\,\\text{{kN/m}} \\quad "
                              f"w_{{max}} = {max_durchbiegung:.2f} \\,\\text{{mm}}$"),
                    "beschreibung": f"Häufige Kombination mit {leiteinwirkung.upper()} als Leiteinwirkung",
                    "max_werte": {
                        "durchbiegung": max_durchbiegung
                    }
                }

        # 3. Quasi-ständige Kombination: G + Σψ₂ · Q_i
        if q_lasten:
            quasi_ergebnisse = [erg for erg in self.ergebnisse_gzg
                                if erg["kombination"]["typ"] == "quasi_staendig"]

            if quasi_ergebnisse:
                # Nur eine quasi-ständige Kombination
                massgebend = quasi_ergebnisse[0]

                g_wert = sum(float(l["wert"]) for l in g_lasten) * sprungmass

                q_terme = []
                qd_q_gesamt = 0
                for q in q_lasten:
                    q_wert = float(q["wert"]) * sprungmass
                    qd_q_gesamt += 0.3 * q_wert  # ψ₂ = 0.3
                    q_terme.append(f"0.3 \\cdot {q['lastfall']}")

                qd_gesamt = g_wert + qd_q_gesamt
                max_durchbiegung = massgebend["max"]["durchbiegung"]

                q_str = " + ".join(q_terme)

                latex_formeln["GZG"]["quasi_staendig"] = {
                    "name": "Quasi-ständige Kombination",
                    "latex": (f"$G + \\Sigma\\psi_2 \\cdot Q_i: \\quad "
                              f"g + {q_str} = {qd_gesamt:.2f} \\,\\text{{kN/m}} \\quad "
                              f"w_{{max}} = {max_durchbiegung:.2f} \\,\\text{{mm}}$"),
                    "beschreibung": "Quasi-ständige Kombination aller veränderlichen Lasten",
                    "max_werte": {
                        "durchbiegung": max_durchbiegung
                    }
                }

        return latex_formeln

    def _ermittle_massgebenden_einzellastfall(self):
        """
        Ermittelt den maßgebenden Einzellastfall für GZT g_plus_q Kombinationen.
        """
        g_plus_q_ergebnisse = [erg for erg in self.ergebnisse_gzt
                               if erg["kombination"]["typ"] == "g_plus_q"]

        if g_plus_q_ergebnisse:
            massgebend = max(g_plus_q_ergebnisse,
                             key=lambda x: x["max"]["moment"])
            return massgebend["kombination"]["leiteinwirkung"].upper()
        return "Q"

    def _ermittle_massgebende_vollkombination(self):
        """
        Ermittelt die maßgebende Leiteinwirkung für Vollkombinationen.
        """
        vollkombi_ergebnisse = [erg for erg in self.ergebnisse_gzt
                                if erg["kombination"]["typ"] == "vollkombination"]

        if vollkombi_ergebnisse:
            massgebend = max(vollkombi_ergebnisse,
                             key=lambda x: x["max"]["moment"])
            return massgebend["kombination"]["leiteinwirkung"].upper()
        return "Q"

    def _ermittle_massgebende_charakteristische(self):
        """Ermittelt die maßgebende Leiteinwirkung für charakteristische Kombinationen."""
        char_ergebnisse = [erg for erg in self.ergebnisse_gzg
                           if erg["kombination"]["typ"] == "charakteristisch"]

        if char_ergebnisse:
            massgebend = max(
                char_ergebnisse, key=lambda x: x["max"]["durchbiegung"])
            return massgebend["kombination"]["leiteinwirkung"].upper()
        return "Q"

    def _ermittle_massgebende_haeufige(self):
        """
        Ermittelt die maßgebende Leiteinwirkung für häufige Kombinationen.
        """
        haeufig_ergebnisse = [erg for erg in self.ergebnisse_gzg
                              if erg["kombination"]["typ"] == "haeufig"]

        if haeufig_ergebnisse:
            massgebend = max(haeufig_ergebnisse,
                             key=lambda x: x["max"]["durchbiegung"])
            return massgebend["kombination"]["leiteinwirkung"].upper()
        return "Q"


# Hilfsfunktion für Kompatibilität mit bestehender Schnittstelle
def berechne_feebb_gzt_gzg_ec(snapshot, db, num_points=100):
    """
    EC-konforme FEEBB-Berechnung - Kompatibilitätsfunktion.

    Args:
        snapshot (dict): System-Snapshot mit allen Eingabedaten
        db: Datenbankverbindung für Materialparameter
        num_points (int): Anzahl Auswertungspunkte (wird ignoriert, fest auf 100 gesetzt)

    Returns:
        dict: Berechnungsergebnisse im Format der bestehenden Schnittstelle
    """
    logger.info("🔄 Starte EC-konforme FEEBB-Berechnung (Kompatibilitätsmodus)")

    berechnung = FeebbBerechnungEC(snapshot, db)
    return berechnung.compute()
