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
import logging
import numpy as np
from backend.calculations.feebb import Element, Beam, Postprocessor


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

        # EC-spezifische Parameter (γ aus NA-DE, aktuell als Standardwerte; ψ aus Datenbank)
        self.gamma_g = 1.35  # Teilsicherheitsbeiwert für ständige Lasten (GZT)
        # Teilsicherheitsbeiwert für veränderliche Lasten (GZT)
        self.gamma_q = 1.5
        # Hinweis: ψ0/ψ1/ψ2 werden je Last über die Datenbank ermittelt

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

    # ===== Hilfsfunktionen für ψ-Werte aus der Datenbank =====
    def _get_si(self, last: dict):
        """Liest Si-Beiwerte für die Lastkategorie aus der Datenbank."""
        try:
            kat = last.get("kategorie")
            return self.db.get_si_beiwerte(kat) if kat else None
        except Exception:
            return None

    def _psi0(self, last: dict, fallback_lastfall: str | None = None) -> float:
        si = self._get_si(last)
        if si and si.psi0 is not None:
            return float(si.psi0)
        lf = (fallback_lastfall or last.get("lastfall", "")).lower()
        return {"s": 0.7, "w": 0.6, "p": 0.7}.get(lf, 0.7)

    def _psi1(self, last: dict, fallback_lastfall: str | None = None) -> float:
        si = self._get_si(last)
        if si and si.psi1 is not None:
            return float(si.psi1)
        lf = (fallback_lastfall or last.get("lastfall", "")).lower()
        # konservative Defaults
        return {"p": 0.5, "s": 0.2, "w": 0.2}.get(lf, 0.5)

    def _psi2(self, last: dict, fallback_lastfall: str | None = None) -> float:
        si = self._get_si(last)
        if si and si.psi2 is not None:
            return float(si.psi2)
        lf = (fallback_lastfall or last.get("lastfall", "")).lower()
        return {"p": 0.3, "s": 0.2, "w": 0.0}.get(lf, 0.3)

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
        self.sprungmass = self.snapshot.get("sprungmass")

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

    def _generiere_belastungsmuster(self):
        """
        Generiert alle relevanten Belastungsmuster für Mehrfeldträger nach Eurocode.
        
        Für jeden Feldtyp (normale Felder, keine Kragarme) werden verschiedene
        Belastungsmuster erzeugt, um die ungünstigste Konstellation zu finden.
        """
        # Normale Felder (ohne Kragarme) extrahieren
        self.normale_felder = [f for f in self.felder if f["typ"].startswith("feld_")]
        
        # Debug-Logging
        logger.info(f"🔍 Normale Felder: {len(self.normale_felder)}")
        for fidx, feld in enumerate(self.normale_felder):
            logger.info(f"   Feld {fidx}: {feld['typ']}, Elemente {feld['start_element']}-{feld['start_element'] + feld['anzahl_elemente'] - 1}, Länge {feld['laenge']}m")
        
        if len(self.normale_felder) <= 1:
            # Bei einem Feld oder nur Kragarmen: nur ein Muster (alle belastet)
            self.belastungsmuster = [[True] * len(self.normale_felder)]
            logger.info("📊 Einfeldträger: 1 Belastungsmuster")
        else:
            # Bei Mehrfeldträgern: alle möglichen Kombinationen generieren
            import itertools
            n = len(self.normale_felder)
            # Alle Kombinationen von belastet/unbelastet
            # Mindestens ein Feld muss belastet sein
            self.belastungsmuster = []
            for r in range(1, n + 1):
                for kombi in itertools.combinations(range(n), r):
                    muster = [i in kombi for i in range(n)]
                    self.belastungsmuster.append(muster)
            
            logger.info(f"📊 Mehrfeldträger: {len(self.belastungsmuster)} Belastungsmuster generiert")
    
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

        # Belastungsmuster für Mehrfeldträger generieren
        self._generiere_belastungsmuster()

        # Lastdaten aufbereiten
        g_lasten = [l for l in self.lasten if l["lastfall"].lower() == "g"]
        q_lasten = [l for l in self.lasten if l["lastfall"].lower() != "g"]

        # === GZT-Kombinationen (mit Teilsicherheitsbeiwerten) ===

        # 1. Nur ständige Lasten: γ_G · G
        if g_lasten:
            # Alle G-Lasten summieren (verhindert Key-Kollision bei mehreren G mit gleichem lastfall)
            g_sum = sum(self.gamma_g * float(l["wert"]) * self.sprungmass for l in g_lasten)
            self.kombinationen_gzt.append({
                "name": "GZT: γ_G · G",
                "beschreibung": "Nur ständige Lasten mit Teilsicherheitsbeiwert",
                "lasten": {"G_SUM": g_sum},
                "typ": "nur_g"
            })

        # 2. G + einzelne veränderliche Last: γ_G · G + γ_Q · Q_i
        for q_last in q_lasten:
            lasten_dict = {}
            # Ständige Lasten (summiert als G_SUM)
            g_sum = sum(self.gamma_g * float(l["wert"]) * self.sprungmass for l in g_lasten)
            lasten_dict["G_SUM"] = g_sum
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
                # Ständige Lasten (summiert als G_SUM)
                g_sum = sum(self.gamma_g * float(l["wert"]) * self.sprungmass for l in g_lasten)
                lasten_dict["G_SUM"] = g_sum

                # Leiteinwirkung
                lasten_dict[leit_q["lastfall"]] = self.gamma_q * \
                    float(leit_q["wert"]) * self.sprungmass

                # Begleitende Einwirkungen mit ψ₀
                for neben_q in q_lasten:
                    if neben_q != leit_q:
                        psi = self._psi0(neben_q)
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
                # Ständige Lasten (ohne γ, summiert als G_SUM)
                g_sum = sum(float(l["wert"]) * self.sprungmass for l in g_lasten)
                lasten_dict["G_SUM"] = g_sum

                # Leiteinwirkung (ohne γ)
                lasten_dict[leit_q["lastfall"]] = float(
                    leit_q["wert"]) * self.sprungmass

                # Begleitende Einwirkungen mit ψ₀ (ohne γ)
                for neben_q in q_lasten:
                    if neben_q != leit_q:
                        psi = self._psi0(neben_q)
                        lasten_dict[neben_q["lastfall"]] = psi * \
                            float(neben_q["wert"]) * self.sprungmass

                self.kombinationen_gzg.append({
                    "name": f"GZG-Char: G + {leit_q['lastfall'].upper()} + Σψ₀ · Q_i",
                    "beschreibung": f"Charakteristische Kombination mit {leit_q['lastfall'].upper()} als Leiteinwirkung",
                    "lasten": lasten_dict,
                    "typ": "charakteristisch",
                    "leiteinwirkung": leit_q["lastfall"]
                })

        # 2. Häufige Kombination: G + ψ₁ · Q_1 + Σψ₂ · Q_i
        if q_lasten:
            for leit_q in q_lasten:
                lasten_dict = {}
                # Ständige Lasten (ohne γ, summiert als G_SUM)
                g_sum = sum(float(l["wert"]) * self.sprungmass for l in g_lasten)
                lasten_dict["G_SUM"] = g_sum

                # Leiteinwirkung mit ψ1
                psi1 = self._psi1(leit_q)
                lasten_dict[leit_q["lastfall"]] = psi1 * \
                    float(leit_q["wert"]) * self.sprungmass

                # Begleitende Einwirkungen mit ψ2
                for neben_q in q_lasten:
                    if neben_q != leit_q:
                        psi2 = self._psi2(neben_q)
                        lasten_dict[neben_q["lastfall"]] = psi2 * \
                            float(neben_q["wert"]) * self.sprungmass

                self.kombinationen_gzg.append({
                    "name": f"GZG-Haeufig: G + ψ1 · {leit_q['lastfall'].upper()} + Σψ2 · Q_i",
                    "beschreibung": f"Häufige Kombination mit {leit_q['lastfall'].upper()} als Leiteinwirkung",
                    "lasten": lasten_dict,
                    "typ": "haeufig",
                    "leiteinwirkung": leit_q["lastfall"]
                })

        # 3. Quasi-ständige Kombination: G + Σψ₂ · Q_i
        if q_lasten:
            lasten_dict = {}
            # Ständige Lasten (summiert als G_SUM)
            g_sum = sum(float(l["wert"]) * self.sprungmass for l in g_lasten)
            lasten_dict["G_SUM"] = g_sum

            # Alle veränderlichen Lasten mit ψ₂
            for q_last in q_lasten:
                psi2 = self._psi2(q_last)
                lasten_dict[q_last["lastfall"]] = psi2 * \
                    float(q_last["wert"]) * self.sprungmass

            self.kombinationen_gzg.append({
                "name": "GZG-Quasi: G + Σψ₂ · Q_i",
                "beschreibung": "Quasi-ständige Kombination",
                "lasten": lasten_dict,
                "typ": "quasi_staendig"
            })
        
        # Fallback: Falls keine Q-Lasten vorhanden, erstelle mindestens eine GZG-Kombination (nur G)
        # Dies ist wichtig für Durchbiegungsnachweise, die GZG-Werte benötigen
        if not q_lasten and g_lasten:
            lasten_dict = {}
            g_sum = sum(float(l["wert"]) * self.sprungmass for l in g_lasten)
            lasten_dict["G_SUM"] = g_sum
            
            self.kombinationen_gzg.append({
                "name": "GZG: G (nur ständige Lasten)",
                "beschreibung": "Charakteristische Kombination ohne veränderliche Lasten",
                "lasten": lasten_dict,
                "typ": "nur_g"
            })
            logger.info("⚠️ Keine veränderlichen Lasten → GZG-Fallback erstellt (nur G)")

        logger.info(
            f"📋 {len(self.kombinationen_gzt)} GZT-Kombinationen und {len(self.kombinationen_gzg)} GZG-Kombinationen generiert")

    def _berechne_alle_kombinationen(self):
        """
        Führt FEEBB-Berechnungen für alle generierten Lastkombinationen durch.
        Für jede Lastkombination werden alle Belastungsmuster durchgerechnet.
        """
        logger.info("🔢 Berechne alle Lastkombinationen mit Belastungsmustern")

        self.ergebnisse_gzt = []
        self.ergebnisse_gzg = []

        # === GZT-Berechnungen ===
        for kombi in self.kombinationen_gzt:
            logger.debug(f"Berechne GZT: {kombi['name']}")

            # Für jedes Belastungsmuster eine Berechnung durchführen
            for idx, muster in enumerate(self.belastungsmuster):
                # FEEBB-Dict für diese Kombination mit diesem Muster erstellen
                feebb_dict = self._erstelle_feebb_dict_fuer_kombination(kombi, muster)

                # FEEBB-Berechnung durchführen
                ergebnis = self._fuehre_feebb_berechnung_durch(feebb_dict)
                ergebnis["kombination"] = kombi
                ergebnis["belastungsmuster"] = muster
                ergebnis["muster_id"] = idx

                self.ergebnisse_gzt.append(ergebnis)

        # === GZG-Berechnungen ===
        for kombi in self.kombinationen_gzg:
            logger.debug(f"Berechne GZG: {kombi['name']}")

            # Für jedes Belastungsmuster eine Berechnung durchführen
            for idx, muster in enumerate(self.belastungsmuster):
                # FEEBB-Dict für diese Kombination mit diesem Muster erstellen
                feebb_dict = self._erstelle_feebb_dict_fuer_kombination(kombi, muster)

                # FEEBB-Berechnung durchführen
                ergebnis = self._fuehre_feebb_berechnung_durch(feebb_dict)
                ergebnis["kombination"] = kombi
                ergebnis["belastungsmuster"] = muster
                ergebnis["muster_id"] = idx

                self.ergebnisse_gzg.append(ergebnis)

        logger.info(
            f"✅ Alle Kombinationen berechnet: {len(self.ergebnisse_gzt)} GZT + {len(self.ergebnisse_gzg)} GZG (mit {len(self.belastungsmuster)} Mustern je Kombi)")

    def _erstelle_feebb_dict_fuer_kombination(self, kombination, belastungsmuster):
        """
        Erstellt ein FEEBB-Dictionary für eine spezifische Lastkombination mit feldspezifischer Lastverteilung.

        Args:
            kombination (dict): Lastkombination mit Lastfällen und Werten
            belastungsmuster (list): Boolean-Liste, welche Felder mit veränderlicher Last belastet sind

        Returns:
            dict: FEEBB-Dictionary mit elements und supports
        """
        # Ständige Last (auf alle Felder) - direkt aus G_SUM lesen
        g_last_gesamt = kombination["lasten"].get("G_SUM", 0.0)
        
        # Veränderliche Lasten auftrennen nach Leit- und Begleitlasten
        leiteinwirkung = kombination.get("leiteinwirkung", None)
        
        # Leitlast (wird feldweise nach Muster aufgebracht)
        q_leit_wert = 0.0
        if leiteinwirkung:
            q_leit_wert = kombination["lasten"].get(leiteinwirkung, 0.0)
        
        # Begleitlesten (werden auf ALLE Felder aufgebracht)
        q_begleit_gesamt = 0.0
        for lastfall, wert in kombination["lasten"].items():
            # Alle Lasten außer G_SUM und Leitlast
            if lastfall != "G_SUM" and lastfall != leiteinwirkung:
                q_begleit_gesamt += wert
        
        # Falls keine Leiteinwirkung definiert (z.B. nur G), alle Q-Lasten als Leitlast behandeln
        if not leiteinwirkung:
            q_leit_wert = sum(wert for lastfall, wert in kombination["lasten"].items() 
                             if lastfall != "G_SUM")

        # Erstelle Lastverteilung pro Feld (wichtig für konsistente Belastung!)
        # Key: start_element bis end_element, Value: Lastgröße
        feld_lasten = {}
        
        # Debug: Zeige Belastungsmuster (nur für erste paar Muster, sonst zu viel Output)
        if hasattr(self, '_debug_counter'):
            self._debug_counter += 1
        else:
            self._debug_counter = 0
        
        if self._debug_counter < 3:  # Nur erste 3 Kombinationen debuggen
            logger.info(f"🎯 Belastungsmuster: {belastungsmuster}")
            logger.info(f"   G-Last: {g_last_gesamt:.2f} N/mm")
            logger.info(f"   Q-Leitlast: {q_leit_wert:.2f} N/mm (feldweise)")
            logger.info(f"   Q-Begleitlesten: {q_begleit_gesamt:.2f} N/mm (auf alle Felder)")
        
        for feld in self.felder:
            start_elem = feld["start_element"]
            end_elem = feld["start_element"] + feld["anzahl_elemente"]
            feld_typ = feld["typ"]
            
            # Ständige Last + Begleitlesten (auf alle Felder)
            last_wert = g_last_gesamt + q_begleit_gesamt
            
            # Leitlast hinzufügen (feldweise nach Muster)
            if feld_typ.startswith("feld_"):
                # Normales Feld - prüfe Belastungsmuster für Leitlast
                feld_idx = None
                for fidx, norm_feld in enumerate(self.normale_felder):
                    if norm_feld["typ"] == feld_typ:
                        feld_idx = fidx
                        break
                
                if feld_idx is not None and feld_idx < len(belastungsmuster) and belastungsmuster[feld_idx]:
                    last_wert += q_leit_wert
                    if self._debug_counter < 3:
                        logger.info(f"   {feld_typ} (Elem {start_elem}-{end_elem-1}): {last_wert:.2f} N/mm (G+Begleit+Leit)")
                else:
                    if self._debug_counter < 3:
                        logger.info(f"   {feld_typ} (Elem {start_elem}-{end_elem-1}): {last_wert:.2f} N/mm (G+Begleit)")
            else:
                # Kragarme werden immer mit Leitlast belastet
                last_wert += q_leit_wert
                if self._debug_counter < 3:
                    logger.info(f"   {feld_typ} (Elem {start_elem}-{end_elem-1}): {last_wert:.2f} N/mm (Kragarm, G+Begleit+Leit)")
            
            # Speichere Lastgröße für diesen Elementbereich
            for elem_idx in range(start_elem, end_elem):
                feld_lasten[elem_idx] = last_wert

        # Jetzt Elemente mit Lasten erstellen
        elements_mit_lasten = []
        
        for idx, element_data in enumerate(self.gesamt_elemente):
            element = {
                "length": element_data["length"],
                "youngs_mod": element_data["youngs_mod"],
                "moment_of_inertia": element_data["moment_of_inertia"],
                "loads": []
            }

            # Hole die vorberechnete Last für dieses Element
            gesamt_last = feld_lasten.get(idx, 0.0)

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

        # Maßgebende Kombinationen je Punkt (mit Belastungsmuster)
        moment_max_kombi = [""] * n_punkte
        moment_min_kombi = [""] * n_punkte
        querkraft_max_kombi = [""] * n_punkte
        querkraft_min_kombi = [""] * n_punkte
        durchbiegung_max_kombi = [""] * n_punkte
        durchbiegung_min_kombi = [""] * n_punkte
        
        # Maßgebende Belastungsmuster je Punkt
        moment_max_muster = [None] * n_punkte
        moment_min_muster = [None] * n_punkte
        querkraft_max_muster = [None] * n_punkte
        querkraft_min_muster = [None] * n_punkte
        durchbiegung_max_muster = [None] * n_punkte
        durchbiegung_min_muster = [None] * n_punkte

        # Envelope-Bildung
        for erg in ergebnisse:
            kombi_name = erg["kombination"]["name"]
            belastungsmuster = erg.get("belastungsmuster", None)

            for i in range(n_punkte):
                # Moment
                if erg["moment"][i] > moment_max[i]:
                    moment_max[i] = erg["moment"][i]
                    moment_max_kombi[i] = kombi_name
                    moment_max_muster[i] = belastungsmuster
                if erg["moment"][i] < moment_min[i]:
                    moment_min[i] = erg["moment"][i]
                    moment_min_kombi[i] = kombi_name
                    moment_min_muster[i] = belastungsmuster

                # Querkraft
                if erg["querkraft"][i] > querkraft_max[i]:
                    querkraft_max[i] = erg["querkraft"][i]
                    querkraft_max_kombi[i] = kombi_name
                    querkraft_max_muster[i] = belastungsmuster
                if erg["querkraft"][i] < querkraft_min[i]:
                    querkraft_min[i] = erg["querkraft"][i]
                    querkraft_min_kombi[i] = kombi_name
                    querkraft_min_muster[i] = belastungsmuster

                # Durchbiegung
                if erg["durchbiegung"][i] > durchbiegung_max[i]:
                    durchbiegung_max[i] = erg["durchbiegung"][i]
                    durchbiegung_max_kombi[i] = kombi_name
                    durchbiegung_max_muster[i] = belastungsmuster
                if erg["durchbiegung"][i] < durchbiegung_min[i]:
                    durchbiegung_min[i] = erg["durchbiegung"][i]
                    durchbiegung_min_kombi[i] = kombi_name
                    durchbiegung_min_muster[i] = belastungsmuster

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
            moment_abs_muster = moment_max_muster[moment_abs_max_idx]
        else:
            moment_abs_kombi = moment_min_kombi[moment_abs_min_idx]
            moment_abs_muster = moment_min_muster[moment_abs_min_idx]

        querkraft_abs_max_idx = np.argmax([abs(v) for v in querkraft_max])
        querkraft_abs_min_idx = np.argmax([abs(v) for v in querkraft_min])

        if max(abs(v) for v in querkraft_max) >= max(abs(v) for v in querkraft_min):
            querkraft_abs_kombi = querkraft_max_kombi[querkraft_abs_max_idx]
            querkraft_abs_muster = querkraft_max_muster[querkraft_abs_max_idx]
        else:
            querkraft_abs_kombi = querkraft_min_kombi[querkraft_abs_min_idx]
            querkraft_abs_muster = querkraft_min_muster[querkraft_abs_min_idx]

        durchbiegung_abs_max_idx = np.argmax(
            [abs(w) for w in durchbiegung_max])
        durchbiegung_abs_min_idx = np.argmax(
            [abs(w) for w in durchbiegung_min])

        if max(abs(w) for w in durchbiegung_max) >= max(abs(w) for w in durchbiegung_min):
            durchbiegung_abs_kombi = durchbiegung_max_kombi[durchbiegung_abs_max_idx]
            durchbiegung_abs_muster = durchbiegung_max_muster[durchbiegung_abs_max_idx]
        else:
            durchbiegung_abs_kombi = durchbiegung_min_kombi[durchbiegung_abs_min_idx]
            durchbiegung_abs_muster = durchbiegung_min_muster[durchbiegung_abs_min_idx]
        
        # Finde die vollständigen Verläufe der maßgebenden Kombinationen
        # (für GUI-Darstellung mit korrektem Belastungsmuster)
        moment_massgebend_verlauf = None
        querkraft_massgebend_verlauf = None
        durchbiegung_massgebend_verlauf = None
        
        for erg in ergebnisse:
            if erg["kombination"]["name"] == moment_abs_kombi and erg.get("belastungsmuster") == moment_abs_muster:
                moment_massgebend_verlauf = erg
            if erg["kombination"]["name"] == querkraft_abs_kombi and erg.get("belastungsmuster") == querkraft_abs_muster:
                querkraft_massgebend_verlauf = erg
            if erg["kombination"]["name"] == durchbiegung_abs_kombi and erg.get("belastungsmuster") == durchbiegung_abs_muster:
                durchbiegung_massgebend_verlauf = erg
        
        # Terminal-Ausgabe der maßgebenden Kombinationen
        self._zeige_massgebende_kombination_terminal(grenzzustand, "Moment", moment_abs_kombi, moment_abs_muster, abs_max_moment)
        self._zeige_massgebende_kombination_terminal(grenzzustand, "Querkraft", querkraft_abs_kombi, querkraft_abs_muster, abs_max_querkraft)
        self._zeige_massgebende_kombination_terminal(grenzzustand, "Durchbiegung", durchbiegung_abs_kombi, durchbiegung_abs_muster, abs_max_durchbiegung)

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
            "massgebende_muster": {
                "moment_max": moment_max_muster,
                "moment_min": moment_min_muster,
                "querkraft_max": querkraft_max_muster,
                "querkraft_min": querkraft_min_muster,
                "durchbiegung_max": durchbiegung_max_muster,
                "durchbiegung_min": durchbiegung_min_muster
            },
            "max": {
                "moment": abs_max_moment,
                "querkraft": abs_max_querkraft,
                "durchbiegung": abs_max_durchbiegung,
                "moment_kombi": moment_abs_kombi,
                "querkraft_kombi": querkraft_abs_kombi,
                "durchbiegung_kombi": durchbiegung_abs_kombi,
                "moment_muster": moment_abs_muster,
                "querkraft_muster": querkraft_abs_muster,
                "durchbiegung_muster": durchbiegung_abs_muster
            },
            # Für GUI-Darstellung: Verläufe der maßgebenden Kombinationen (nicht Envelope!)
            "moment": moment_massgebend_verlauf["moment"] if moment_massgebend_verlauf else moment_max.tolist(),
            "querkraft": querkraft_massgebend_verlauf["querkraft"] if querkraft_massgebend_verlauf else querkraft_max.tolist(),
            "durchbiegung": durchbiegung_massgebend_verlauf["durchbiegung"] if durchbiegung_massgebend_verlauf else durchbiegung_max.tolist()
        }

    def _zeige_massgebende_kombination_terminal(self, grenzzustand, schnittgroesse, kombi_name, belastungsmuster, max_wert):
        """
        Zeigt die maßgebende Kombination im Terminal an.
        
        Args:
            grenzzustand (str): "GZT" oder "GZG"
            schnittgroesse (str): "Moment", "Querkraft" oder "Durchbiegung"
            kombi_name (str): Name der Kombination
            belastungsmuster (list): Boolean-Liste der belasteten Felder
            max_wert (float): Maximalwert der Schnittgröße
        """
        if belastungsmuster is None:
            logger.info(f"📊 {grenzzustand} {schnittgroesse}: {kombi_name}")
            return
        
        # Belastungsmuster-String erstellen
        belastete_felder = []
        unbelastete_felder = []
        
        for idx, ist_belastet in enumerate(belastungsmuster):
            feld_name = f"Feld {idx + 1}"
            if ist_belastet:
                belastete_felder.append(feld_name)
            else:
                unbelastete_felder.append(feld_name)
        
        # Einheit bestimmen
        if schnittgroesse == "Moment":
            einheit = "kNm"
            wert_ausgabe = max_wert / 1e6
        elif schnittgroesse == "Querkraft":
            einheit = "kN"
            wert_ausgabe = max_wert / 1e3
        else:  # Durchbiegung
            einheit = "mm"
            wert_ausgabe = max_wert
        
        belastet_str = ", ".join(belastete_felder) if belastete_felder else "keine"
        unbelastet_str = ", ".join(unbelastete_felder) if unbelastete_felder else "keine"
        
        logger.info(f"")
        logger.info(f"📊 === {grenzzustand} - Maßgebend für {schnittgroesse} ===")
        logger.info(f"   Kombination: {kombi_name}")
        logger.info(f"   Maximalwert: {wert_ausgabe:.2f} {einheit}")
        logger.info(f"   ✓ Belastete Felder: {belastet_str}")
        logger.info(f"   ✗ Unbelastete Felder: {unbelastet_str}")
        logger.info(f"")
    
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
                        psi = self._psi0(q)
                        q_wert = float(q["wert"]) * sprungmass
                        qd_begleitend += psi * self.gamma_q * q_wert
                        begleitend_terme.append(
                            f"{psi:.2f} \\cdot {self.gamma_q:.2f} \\cdot {q['lastfall']}")

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
                        psi = self._psi0(q)
                        q_wert = float(q["wert"]) * sprungmass
                        qd_begleitend += psi * q_wert
                        begleitend_terme.append(
                            f"{psi:.2f} \\cdot {q['lastfall']}")

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
                        psi2 = self._psi2(q)
                        q_wert = float(q["wert"]) * sprungmass
                        qd_begleitend += psi2 * q_wert
                        begleitend_terme.append(
                            f"{psi2:.2f} \\cdot {q['lastfall']}")

                psi1 = None
                # leiteinwirkung-Objekt finden um ψ1 zu bestimmen
                for q in q_lasten:
                    if q["lastfall"] == leiteinwirkung:
                        psi1 = self._psi1(q)
                        break
                if psi1 is None:
                    psi1 = 0.5

                qd_gesamt = g_wert + psi1 * leit_wert + qd_begleitend
                max_durchbiegung = massgebend["max"]["durchbiegung"]

                begleitend_str = " + " + \
                    " + ".join(begleitend_terme) if begleitend_terme else ""

                latex_formeln["GZG"]["haeufig"] = {
                    "name": "Häufige Kombination",
                    "latex": (f"$G + \\psi_1 \\cdot \\mathbf{{{leiteinwirkung.upper()}}} + \\Sigma\\psi_2 \\cdot Q_i: \\quad "
                              f"g + {psi1:.2f} \\cdot {leiteinwirkung}{begleitend_str} = {qd_gesamt:.2f} \\,\\text{{kN/m}} \\quad "
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
                    psi2 = self._psi2(q)
                    qd_q_gesamt += psi2 * q_wert
                    q_terme.append(f"{psi2:.2f} \\cdot {q['lastfall']}")

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
