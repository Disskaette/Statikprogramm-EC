from PIL import Image
from io import BytesIO
import logging
import math

# Root-Logger-Verhalten
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class MethodeNachweisEC5:
    def __init__(self, snapshot, db):
        self.snapshot = snapshot
        self.db = db

    def tiefgestellt(self, s: str) -> str:
        """Hilfsfunktion für tiefgestellte LaTeX-Indizes"""
        return f"_{{{s}}}"

    def compute(self) -> dict:
        """Hauptmethode für alle EC5-Nachweise - analog zur Lastenkombination"""
        return self.berechne_ec5_nachweise()

    def berechne_ec5_nachweise(self) -> dict:
        """Berechnet alle EC5-Nachweise: Schub, Biegung, Durchbiegung"""
        logger.info("Starte EC5-Nachweisberechnung")

        # Daten aus Snapshot extrahieren
        querschnitt = self.snapshot.get("querschnitt", {})
        gebrauchstauglichkeit = self.snapshot.get("gebrauchstauglichkeit", {})
        spannweiten = self.snapshot.get("spannweiten", {})
        logger.info(querschnitt)
        logger.info(gebrauchstauglichkeit)
        logger.info(spannweiten)
        logger.info(self.snapshot.get("Lastfallkombinationen"))
        if not self.snapshot.get("Schnittgroessen"):
            logger.error("Keine Schnittgrößen im Snapshot gefunden")
            return {}

        # Querschnittswerte (korrekte Feldnamen aus Snapshot)
        b = querschnitt.get("breite_qs", 0)  # Breite in mm
        h = querschnitt.get("hoehe_qs", 0)  # Höhe in mm
        typ = querschnitt.get("typ", "")
        klasse = querschnitt.get("festigkeitsklasse", "")
        nkl = querschnitt.get("nkl", 1)
        gruppe = querschnitt.get("materialgruppe", "")

        # Spannweite (erste verfügbare Spannweite)
        l = 1000  # Fallback in mm
        if spannweiten:
            # Erste Spannweite in m
            l_m = next(iter(spannweiten.values()), 1.0)
            l = l_m * 1000  # Umrechnung m → mm

        # Materialwerte aus DB
        bemessungsdaten = self.db.get_bemessungsdaten(gruppe, typ, klasse, nkl)

        fm_k = bemessungsdaten.get("fmyk")  # N/mm²
        fv_k = bemessungsdaten.get("fvk")  # N/mm²
        E_mean = bemessungsdaten.get("E")  # N/mm²
        gamma_m = bemessungsdaten.get("gamma_m")  # Teilsicherheitsbeiwert

        # Kmod aus Lastkombination
        kmod = self._get_kmod_from_kombination()
        # Bemessungswerte
        fm_d = kmod * fm_k / gamma_m
        fv_d = kmod * fv_k / gamma_m

        # Maximale Schnittgrößen aus GZT
        gzt_data = self.snapshot["Schnittgroessen"]["GZT"]["max"]
        max_med = gzt_data.get("moment")
        max_ved = gzt_data.get("querkraft")

        # EC5-konforme Durchbiegungsberechnung mit GZG-Lastkombinationen
        durchbiegungen = self._berechne_ec5_durchbiegungen(l, E_mean)

        # Durchbiegungsgrenzwerte dynamisch aus Snapshot
        grenzwerte = self._get_durchbiegungsgrenzwerte(
            gebrauchstauglichkeit, l)

        # Nachweise durchführen
        nachweise = {}

        # 1. Biegungsnachweis
        nachweise["biegung"] = self._nachweis_biegung(
            max_med, b, h, fm_d, fm_k, kmod, gamma_m)

        # 2. Schubnachweis
        nachweise["schub"] = self._nachweis_schub(
            max_ved, b, h, fv_d, fv_k, kmod, gamma_m)

        # 3. EC5-konforme Durchbiegungsnachweise (drei separate Nachweise)
        nachweise["durchbiegung_inst"] = self._nachweis_durchbiegung(
            durchbiegungen["delta_inst"], grenzwerte["w_inst"], l, "Sofort-Durchbiegung", "\\delta_{inst,max}")

        nachweise["durchbiegung_fin"] = self._nachweis_durchbiegung(
            durchbiegungen["delta_end"], grenzwerte["w_fin"], l, "End-Durchbiegung", "\\delta_{end,max}")

        nachweise["durchbiegung_net_fin"] = self._nachweis_durchbiegung(
            durchbiegungen["delta_netto"], grenzwerte["w_net_fin"], l, "Netto-End-Durchbiegung", "\\delta_{netto,max}")

        logger.info("EC5-Nachweisberechnung abgeschlossen")
        return nachweise

    def _get_kmod_from_kombination(self):
        """Extrahiert kmod aus der maßgebenden Lastkombination direkt aus dem Snapshot"""
        try:
            # Lastfallkombinationen direkt aus dem Snapshot lesen
            lastkombis = self.snapshot.get("Lastfallkombinationen", {})

            if not lastkombis:
                logger.warning(
                    "Keine Lastfallkombinationen im Snapshot gefunden")
                return 0.9

            # Suche maßgebende Kombination
            for kombi_name, kombi_data in lastkombis.items():
                if kombi_data.get("massgebend", False):
                    kmod_value = kombi_data.get("kmod", 0.9)
                    logger.info(
                        f"Maßgebende Kombination gefunden: {kombi_name}, kmod = {kmod_value}")
                    return kmod_value

            # Fallback: erste Kombination
            first_kombi_name = next(iter(lastkombis.keys()))
            first_kombi_data = lastkombis[first_kombi_name]
            kmod_value = first_kombi_data.get("kmod", 0.9)
            logger.info(
                f"Fallback auf erste Kombination: {first_kombi_name}, kmod = {kmod_value}")
            return kmod_value

        except Exception as e:
            logger.warning(f"Fehler beim Extrahieren von kmod: {e}")

        return 0.9  # Fallback-Wert

    def _berechne_ec5_durchbiegungen(self, l, E_mean):
        """Berechnet EC5-konforme Durchbiegungen: δinst, δend, δnetto mit GZG-Lastkombinationen"""
        try:
            # Prüfe, ob EC-Modus aktiv ist und EC-FEEBB-Durchbiegungen verfügbar sind
            ec_modus = self.snapshot.get(
                'berechnungsmodus', {}).get('ec_modus', False)
            gzg_schnittgroessen = self.snapshot.get(
                "Schnittgroessen", {}).get("GZG", {})

            if ec_modus and gzg_schnittgroessen and "max" in gzg_schnittgroessen:
                # EC-Modus: Verwende bereits berechnete Durchbiegungen aus FEEBB-EC
                logger.info("🔬 EC-Modus: Verwende FEEBB-EC Durchbiegungen")

                # Durchbiegung direkt aus FEEBB-Envelope
                delta_inst = gzg_schnittgroessen["max"].get(
                    "durchbiegung", 0)  # mm

                # kdef aus Materialdatenbank
                querschnitt = self.snapshot.get("querschnitt", {})
                gruppe = querschnitt.get("materialgruppe", "")
                typ = querschnitt.get("typ", "")
                klasse = querschnitt.get("festigkeitsklasse", "")
                nkl = querschnitt.get("nkl", 1)
                bemessungsdaten = self.db.get_bemessungsdaten(
                    gruppe, typ, klasse, nkl)
                kdef = bemessungsdaten.get("kdef", 0.8)

                # Zeitabhängige Durchbiegungen
                delta_end = (1 + kdef) * delta_inst
                gebrauchstauglichkeit = self.snapshot.get(
                    "gebrauchstauglichkeit", {})
                delta_0 = gebrauchstauglichkeit.get("w_c", 0)
                delta_netto = delta_end - delta_0

                logger.info(f"EC-FEEBB Durchbiegungen:")
                logger.info(f"  - δinst (aus FEEBB-EC) = {delta_inst:.2f} mm")
                logger.info(
                    f"  - δend = (1+kdef) · δinst = {delta_end:.2f} mm (kdef = {kdef:.2f})")
                logger.info(
                    f"  - δnetto = {delta_netto:.2f} mm (Δ₀ = {delta_0:.2f} mm)")

                return {
                    "delta_inst": delta_inst,
                    "delta_end": delta_end,
                    "delta_netto": delta_netto,
                    "qd_gzg": 0,  # Nicht direkt verfügbar im EC-Modus
                    "kdef": kdef,
                    "delta_0": delta_0
                }

            # Fallback: Alte Methode (Schnell-Modus)
            logger.info(
                "⚡ Schnell-Modus: Berechne Durchbiegungen aus GZG-Lastkombinationen")

            # Maßgebende GZG-Lastkombination aus Snapshot
            gzg_kombis = self.snapshot.get("GZG_Lastfallkombinationen", {})
            if not gzg_kombis:
                logger.warning(
                    "Keine GZG-Lastkombinationen für Durchbiegungsberechnung gefunden")
                return {"delta_inst": 0, "delta_end": 0, "delta_netto": 0}

            # Maßgebende GZG-Kombination finden
            massgebende_gzg = None
            for kombi_name, kombi_data in gzg_kombis.items():
                if kombi_data.get("massgebend", False):
                    massgebende_gzg = kombi_data
                    break

            if not massgebende_gzg:
                # Fallback: Höchste Last
                massgebende_gzg = max(
                    gzg_kombis.values(), key=lambda x: x.get("wert", 0))

            # Quasi-permanente Last und kdef
            qd_gzg = massgebende_gzg.get("wert", 0)  # kN/m
            kdef = massgebende_gzg.get("kdef", 0.8)  # Aus Datenbank

            # Querschnittswerte
            querschnitt = self.snapshot.get("querschnitt", {})
            I_y = querschnitt.get("I_y", 0) / 1e12  # mm⁴ → m⁴

            if I_y <= 0:
                logger.error("Ungültiges Flächenträgheitsmoment")
                return {"delta_inst": 0, "delta_end": 0, "delta_netto": 0}

            # Debug-Ausgaben für Durchbiegungsberechnung
            logger.debug(f"Durchbiegung Debug: qd_gzg = {qd_gzg} kN/m")
            logger.debug(f"Durchbiegung Debug: l = {l} mm")
            logger.debug(f"Durchbiegung Debug: E_mean = {E_mean} N/mm²")
            logger.debug(
                f"Durchbiegung Debug: I_y = {I_y} m⁴ (original: {querschnitt.get('I_y', 0)} mm⁴)")
            logger.debug(f"Durchbiegung Debug: kdef = {kdef}")

            # EC5-Durchbiegungsberechnung für Gleichlast auf einfachem Balken
            # δinst = (5 * q * L⁴) / (384 * E * I)
            delta_inst = (5 * qd_gzg * 1000 * (l/1000)**4) / \
                (384 * E_mean * 1e6 * I_y) * 1000  # mm

            logger.debug(
                f"Durchbiegung Debug: delta_inst berechnet = {delta_inst} mm")

            # δend = kdef * δinst (Langzeitdurchbiegung)
            delta_end = kdef * delta_inst

            # δnetto = δend - Δ₀ (Netto-Enddurchbiegung)
            # Δ₀ = Anfangsüberhöhung (aus Gebrauchstauglichkeit)
            gebrauchstauglichkeit = self.snapshot.get(
                "gebrauchstauglichkeit", {})
            delta_0 = gebrauchstauglichkeit.get("w_c", 0)  # Anfangsüberhöhung
            delta_netto = delta_end - delta_0

            logger.info(f"EC5-Durchbiegungen berechnet:")
            logger.info(f"  - qd,GZG = {qd_gzg:.2f} kN/m, kdef = {kdef:.2f}")
            logger.info(f"  - δinst = {delta_inst:.2f} mm")
            logger.info(f"  - δend = {delta_end:.2f} mm")
            logger.info(
                f"  - δnetto = {delta_netto:.2f} mm (Δ₀ = {delta_0:.2f} mm)")

            return {
                "delta_inst": delta_inst,
                "delta_end": delta_end,
                "delta_netto": delta_netto,
                "qd_gzg": qd_gzg,
                "kdef": kdef,
                "delta_0": delta_0
            }

        except Exception as e:
            logger.error(f"Fehler bei EC5-Durchbiegungsberechnung: {e}")
            return {"delta_inst": 0, "delta_end": 0, "delta_netto": 0}

    def _nachweis_biegung(self, max_med, b, h, fm_d, fm_k, kmod, gamma_m):
        """Biegungsnachweis nach EC5 - analog zur Lastenkombination"""
        # Widerstandsmoment (Rechteckquerschnitt)
        w_y = (b * h**2) / 6  # mm³

        # Biegespannung
        sigma_m_d = max_med / w_y  # N/mm²

        # Ausnutzung
        eta = sigma_m_d / fm_d
        erfuellt = eta <= 1.0

        # LaTeX-String direkt erstellen (analog zur Lastenkombination)
        latex_str = (f"$\\sigma_{{m,d}} = \\frac{{M_{{Ed}}}}{{W_y}} = "
                     f"\\frac{{{max_med/1000000:.1f}\\cdot{{10^6}}}}{{{w_y:.0f}}} = {sigma_m_d:.2f} \\,\\text{{N/mm²}} "
                     f"\\leq {fm_d:.2f} \\,\\text{{N/mm²}} \\quad "
                     f"\\eta = {eta:.2f} {'\\checkmark' if erfuellt else '\\times'}$")

        return {
            "latex": latex_str,
            "erfuellt": erfuellt,
            "ausnutzung": eta,
            "sigma_m_d": sigma_m_d,
            "fm_d": fm_d,
            "w_y": w_y
        }

    def _nachweis_schub(self, max_ved, b, h, fv_d, fv_k, kmod, gamma_m):
        """Schubnachweis nach EC5 - analog zur Lastenkombination"""
        # Schubspannung (vereinfacht für Rechteckquerschnitt)
        tau_d = 1.5 * max_ved / (b * h)  # N/mm²

        # Ausnutzung
        eta = tau_d / fv_d
        erfuellt = eta <= 1.0

        # LaTeX-String direkt erstellen (analog zur Lastenkombination)
        latex_str = (f"$\\tau_d = 1.5 \\cdot \\frac{{V_{{Ed}}}}{{b \\cdot h}} = "
                     f"1.5 \\cdot \\frac{{{max_ved/1000:.1f}\\cdot{{10^3}}}}{{{b:.0f} \\cdot {h:.0f}}} = {tau_d:.0f} \\,\\text{{N/mm²}} "
                     f"\\leq {fv_d:.2f} \\,\\text{{N/mm²}} \\quad "
                     f"\\eta = {eta:.2f} {'\\checkmark' if erfuellt else '\\times'}$")

        return {
            "latex": latex_str,
            "erfuellt": erfuellt,
            "ausnutzung": eta,
            "tau_d": tau_d,
            "fv_d": fv_d
        }

    def _get_durchbiegungsgrenzwerte(self, gebrauchstauglichkeit, l):
        """Extrahiert die Durchbiegungsgrenzwerte basierend auf der gewählten Situation"""

        w_inst_grenz = gebrauchstauglichkeit.get("w_inst_grenz")
        w_fin_grenz = gebrauchstauglichkeit.get("w_fin_grenz")
        w_net_fin_grenz = gebrauchstauglichkeit.get("w_net_fin_grenz")

        return {
            "w_inst": l / w_inst_grenz,
            "w_fin": l / w_fin_grenz,
            "w_net_fin": l / w_net_fin_grenz,
            "faktoren": {
                "w_inst": w_inst_grenz,
                "w_fin": w_fin_grenz,
                "w_net_fin": w_net_fin_grenz
            }
        }

    def _nachweis_durchbiegung(self, max_w, w_grenz, l, bezeichnung="Durchbiegung", symbol="w"):
        """Durchbiegungsnachweis nach EC5 - analog zur Lastenkombination"""
        # Ausnutzung
        eta = max_w / w_grenz
        erfuellt = eta <= 1.0

        # Grenzfaktor berechnen
        grenz_faktor = l / w_grenz if w_grenz > 0 else 0

        # LaTeX-String direkt erstellen (analog zur Lastenkombination)
        latex_str = (f"${symbol} = {max_w:.2f} \\,\\text{{mm}} \\leq "
                     f"{symbol.replace(',max', '_{{grenz}}')} = \\frac{{L}}{{{grenz_faktor:.0f}}} = {w_grenz:.2f} \\,\\text{{mm}} \\quad "
                     f"\\eta = {eta:.2f} {'\\checkmark' if erfuellt else '\\times'}$")

        return {
            "latex": latex_str,
            "erfuellt": erfuellt,
            "ausnutzung": eta,
            "w_max": max_w,
            "w_grenz": w_grenz,
            "bezeichnung": bezeichnung
        }
