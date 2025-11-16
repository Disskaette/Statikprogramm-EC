import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
import threading
import logging
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import MultipleLocator, AutoMinorLocator

# Root-Logger-Verhalten
logging.basicConfig(
    level=logging.INFO,                      # ab welcher Wichtigkeit geloggt wird
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S"
)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.INFO)
logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
logger = logging.getLogger(__name__)          # logger für dieses Modul


def zeichne_festlager(ax, x, y, size=0.25):
    """Festlager: offenes Dreieck nach oben, Linie direkt darunter."""
    triangle = plt.Polygon([
        (x - size, y),           # links unten
        (x + size, y),           # rechts unten
        (x, y + size * 1.2)      # oben
    ], closed=True, fill=False, edgecolor='black', linewidth=1.5)
    ax.add_patch(triangle)
    # Linie direkt unter dem Dreieck
    ax.plot([x - size * 1.1, x + size * 1.1],
            [y - size * 0.15, y - size * 0.15], color='black', linewidth=2)


def zeichne_loslager(ax, x, y, size=0.25):
    """Loslager: offenes Dreieck nach oben, Strich etwas weiter unterhalb."""
    triangle = plt.Polygon([
        (x - size, y),
        (x + size, y),
        (x, y + size * 1.2)
    ], closed=True, fill=False, edgecolor='black', linewidth=1.5)
    ax.add_patch(triangle)
    # Strich etwas weiter unterhalb
    ax.plot([x - size * 0.7, x + size * 0.7],
            [y - size * 0.35, y - size * 0.35], color='black', linewidth=2)


class FeebbAnzeiger:
    def __init__(self, eingabemaske):
        self.eingabemaske = eingabemaske
        self.schnittkraftfenster = None
        self.schnittkraft_canvas = None
        self._plot_retry_count = 0  # Zähler für Retry-Versuche

    def update_maxwerte(self):
        # Direkter Zugriff auf Schnittgrößen-Daten (ohne system_memory)
        schnittgroessen = self.eingabemaske.snapshot.get("Schnittgroessen", {})
        gzt_data = schnittgroessen.get("GZT", {})
        max_data = gzt_data.get("max", {})

        if not max_data:
            print("Keine Maximalwerte verfügbar. Berechnung noch nicht abgeschlossen.")
            return

        print("✅ Maximalwerte erfolgreich gefunden!")

        moment = max_data.get('moment', 0)
        querkraft = max_data.get('querkraft', 0)
        self.eingabemaske.root.after(0, lambda: self.eingabemaske.max_moment_kalt.configure(
            text=f"{moment/1_000_000:.1f}"))
        self.eingabemaske.root.after(0, lambda: self.eingabemaske.max_querkraft_kalt.configure(
            text=f"{querkraft/1000:.1f}"))

    def toggle_schnittkraftfenster(self):
        if self.eingabemaske.schnittgroeßen_anzeige_button.get():
            if self.schnittkraftfenster is None or not ctk.CTkToplevel.winfo_exists(self.schnittkraftfenster):
                self.schnittkraftfenster = ctk.CTkToplevel(self.eingabemaske.root)
                self.schnittkraftfenster.title(
                    "Schnittkraft- und Durchbiegungsverläufe GZT")
                self.schnittkraftfenster.protocol(
                    "WM_DELETE_WINDOW", self.close_schnittkraftfenster)
                self.plot_schnittkraefte()
        else:
            self.close_schnittkraftfenster()

    def close_schnittkraftfenster(self):
        if self.schnittkraftfenster is not None:
            self.schnittkraftfenster.destroy()
            self.schnittkraftfenster = None
        else:
            return

    def plot_schnittkraefte(self):
        # Theme für Matplotlib konfigurieren (Dark Mode Support)
        from frontend.gui.theme_config import ThemeManager
        ThemeManager.configure_matplotlib()
        
        # Direkter Zugriff auf Schnittgrößen-Daten (ohne system_memory)
        schnittgroessen = self.eingabemaske.snapshot.get("Schnittgroessen", {})
        schnitt_gzt = schnittgroessen.get("GZT")
        schnitt_gzg = schnittgroessen.get("GZG")
        
        # Debug: Prüfe, was tatsächlich vorhanden ist
        print(f"🔍 Debug Schnittgroessen-Keys: {list(schnittgroessen.keys())}")
        print(f"🔍 Debug GZT vorhanden: {schnitt_gzt is not None}")
        print(f"🔍 Debug GZG vorhanden: {schnitt_gzg is not None}")
        if schnitt_gzg:
            if isinstance(schnitt_gzg, dict):
                print(f"🔍 Debug GZG-Typ: Dictionary, Keys: {list(schnitt_gzg.keys())}")
                print(f"🔍 Debug GZG hat Durchbiegung: {'durchbiegung' in schnitt_gzg}")
            elif isinstance(schnitt_gzg, list):
                print(f"🔍 Debug GZG-Typ: Liste mit {len(schnitt_gzg)} Einwirkungen (Schnell-Modus)")
            else:
                print(f"🔍 Debug GZG-Typ: {type(schnitt_gzg)}")

        if not schnitt_gzt:
            self._plot_retry_count += 1
            if self._plot_retry_count > 10:  # Maximal 10 Versuche (5 Sekunden)
                print("❌ Timeout: Keine GZT-Schnittgrößen nach 10 Versuchen verfügbar.")
                print(
                    "   Bitte warten Sie, bis die Berechnung abgeschlossen ist, und versuchen Sie erneut.")
                self._plot_retry_count = 0  # Reset für nächsten Versuch
                return

            print(
                f"Keine GZT-Schnittgrößen verfügbar. Warte auf Backend-Berechnung... (Versuch {self._plot_retry_count}/10)")
            # Automatisches Retry nach 500ms
            self.eingabemaske.root.after(500, self.plot_schnittkraefte)
            return

        # Erfolg: Reset retry counter
        self._plot_retry_count = 0
        print("✅ GZT-Schnittgrößen erfolgreich gefunden!")

        # GZT-Daten für Moment und Querkraft
        # Beide Modi (Schnell/EC) haben "moment" und "querkraft" direkt im Dict
        m = schnitt_gzt.get("moment")
        q = schnitt_gzt.get("querkraft")
        
        # Debug: Prüfe ob m und q vorhanden sind
        if not m or not q:
            print(f"❌ Fehler: GZT-Daten unvollständig!")
            print(f"   m vorhanden: {m is not None}, q vorhanden: {q is not None}")
            if m: print(f"   m Typ: {type(m)}, Länge: {len(m) if hasattr(m, '__len__') else 'N/A'}")
            if q: print(f"   q Typ: {type(q)}, Länge: {len(q) if hasattr(q, '__len__') else 'N/A'}")
        
        # GZG-Daten für Durchbiegung - Unterscheidung zwischen Schnell-Modus (Liste) und EC-Modus (Dict)
        gzg_verfuegbar = False
        durchbiegung_muster = None
        durchbiegung_kombi = ""
        
        if schnitt_gzg:
            # Prüfe, ob GZG eine Liste (Schnell-Modus) oder Dict (EC-Modus) ist
            if isinstance(schnitt_gzg, list):
                # Schnell-Modus: GZG ist Liste von Einzeleinwirkungen
                # Finde die Einwirkung mit der größten Durchbiegung
                if len(schnitt_gzg) > 0:
                    max_durchbiegung = 0
                    max_einwirkung = None
                    
                    for einwirkung in schnitt_gzg:
                        if "durchbiegung" in einwirkung and einwirkung["durchbiegung"]:
                            max_w = max(abs(wert) for wert in einwirkung["durchbiegung"])
                            if max_w > max_durchbiegung:
                                max_durchbiegung = max_w
                                max_einwirkung = einwirkung
                    
                    if max_einwirkung:
                        w = max_einwirkung["durchbiegung"]
                        lastfall = max_einwirkung.get("lastfall", "unbekannt")
                        print(f"ℹ️ Schnell-Modus: GZG-Durchbiegung von Lastfall '{lastfall}' verwendet (max: {max_durchbiegung:.2f} mm)")
                        gzg_verfuegbar = True
                    else:
                        # Fallback falls keine Durchbiegungsdaten in GZG
                        w = schnitt_gzt.get("durchbiegung", None)
                        print("⚠️ Schnell-Modus: Keine GZG-Durchbiegungen gefunden, verwende GZT")
                        gzg_verfuegbar = False
                else:
                    # Leere Liste
                    w = schnitt_gzt.get("durchbiegung", None)
                    print("⚠️ Schnell-Modus: GZG-Liste leer, verwende GZT-Durchbiegung")
                    gzg_verfuegbar = False
                    
            elif isinstance(schnitt_gzg, dict) and "durchbiegung" in schnitt_gzg:
                # EC-Modus: GZG ist Dictionary mit Envelope
                w = schnitt_gzg.get("durchbiegung")
                print("✅ EC-Modus: GZG-Durchbiegung für Darstellung verwendet.")
                gzg_verfuegbar = True
                max_data_gzg = schnitt_gzg.get("max", {})
                durchbiegung_muster = max_data_gzg.get("durchbiegung_muster")
                durchbiegung_kombi = max_data_gzg.get("durchbiegung_kombi", "")
            else:
                # Fallback
                w = schnitt_gzt.get("durchbiegung", None)
                print("⚠️ Fallback: GZT-Durchbiegung verwendet (GZG-Struktur unbekannt).")
                gzg_verfuegbar = False
        else:
            # Kein GZG vorhanden
            w = schnitt_gzt.get("durchbiegung", None)
            print("⚠️ Fallback: GZT-Durchbiegung verwendet (GZG nicht vorhanden).")
            gzg_verfuegbar = False

        # Belastungsmuster für maßgebende Kombinationen (GZT)
        max_data_gzt = schnitt_gzt.get("max", {})
        moment_muster = max_data_gzt.get("moment_muster")
        querkraft_muster = max_data_gzt.get("querkraft_muster")
        
        # Falls GZG nicht verfügbar oder Schnell-Modus: Verwende GZT-Durchbiegungsmuster
        if not gzg_verfuegbar:
            durchbiegung_muster = max_data_gzt.get("durchbiegung_muster")
            durchbiegung_kombi = max_data_gzt.get("durchbiegung_kombi", "")

        # Kombinationsnamen (GZT)
        moment_kombi = max_data_gzt.get("moment_kombi", "")
        querkraft_kombi = max_data_gzt.get("querkraft_kombi", "")

        if not m or not q:
            print("Unvollständige Schnittgrößen-Daten.")
            return

        # Spannweiten und Feldgrenzen bestimmen (in korrekter Reihenfolge!)

        spannweiten_dict = self.eingabemaske.snapshot.get("spannweiten", {})
        
        # WICHTIG: Felder in korrekter geometrischer Reihenfolge sortieren
        # Reihenfolge: kragarm_links, feld_1, feld_2, ..., kragarm_rechts
        kragarm_links = spannweiten_dict.get("kragarm_links", 0)
        kragarm_rechts = spannweiten_dict.get("kragarm_rechts", 0)
        normale_felder = sorted([(k, v) for k, v in spannweiten_dict.items() if k.startswith("feld_")])
        
        # Korrekte Reihenfolge aufbauen
        spannweiten_keys = []
        spannweiten = []
        
        if kragarm_links > 0:
            spannweiten_keys.append("kragarm_links")
            spannweiten.append(kragarm_links)
        
        for feld_key, feld_wert in normale_felder:
            spannweiten_keys.append(feld_key)
            spannweiten.append(feld_wert)
        
        if kragarm_rechts > 0:
            spannweiten_keys.append("kragarm_rechts")
            spannweiten.append(kragarm_rechts)
        
        # Feldgrenzen berechnen
        feldgrenzen = [0]
        for l in spannweiten:
            feldgrenzen.append(feldgrenzen[-1] + l)
        gesamtlaenge = feldgrenzen[-1]
        num_points = len(m)
        x = np.linspace(0, gesamtlaenge, num_points)

        fig, axs = plt.subplots(4, 1, figsize=(10, 12), sharex=True, gridspec_kw={
                                'height_ratios': [0.5, 1, 1, 1]})
        fig.subplots_adjust(hspace=0.4)

        # 1. Balken zeichnen
        y_beam = 0
        axs[0].plot([0, gesamtlaenge], [y_beam, y_beam],
                    color='black', linewidth=4, solid_capstyle='round')
        axs[0].set_ylim(-1, 1)
        axs[0].axis('off')

        # 2. Auflager-Positionen bestimmen
        kragarm_links = spannweiten_dict.get("kragarm_links", 0)
        kragarm_rechts = spannweiten_dict.get("kragarm_rechts", 0)
        num_fields = len(
            [k for k in spannweiten_keys if k.startswith("feld_")])

        # Auflager nur an Feldgrenzen, NICHT an den Enden von Kragarmen!
        auflager_pos = []
        for i in range(len(feldgrenzen)):
            # Erster und letzter Punkt sind nur Auflager, wenn KEIN Kragarm vorhanden ist
            if i == 0 and kragarm_links > 0:
                continue
            if i == len(feldgrenzen)-1 and kragarm_rechts > 0:
                continue
            auflager_pos.append(feldgrenzen[i])

        # 3. Auflager zeichnen
        for idx, pos in enumerate(auflager_pos):
            if idx == 0:
                # Erstes Auflager: Festlager
                zeichne_festlager(axs[0], pos, y_beam-0.5)
            else:
                # Alle weiteren: Loslager
                zeichne_loslager(axs[0], pos, y_beam-0.5)

        # 4. Feldnummern eintragen
        for i in range(num_fields):
            x_feldmitte = (feldgrenzen[i+1] + feldgrenzen[i]) / 2
            axs[0].text(x_feldmitte, y_beam+0.6,
                        f"Feld {i+1}", ha='center', va='bottom', fontsize=12, color='gray')

        # 5. Feldgrenzen als gestrichelte Linien
        for grenze in feldgrenzen:
            axs[1].axvline(grenze, color='gray', linestyle='--', linewidth=1)
            axs[2].axvline(grenze, color='gray', linestyle='--', linewidth=1)
            axs[3].axvline(grenze, color='gray', linestyle='--', linewidth=1)

        # 5b. Belastungsmuster als farbige Hinterlegung darstellen
        def zeichne_belastungsmuster(ax, muster, feldgrenzen):
            """Zeichnet belastete Felder als farbige Hintergründe."""
            if muster is None:
                return

            # Normale Felder identifizieren (ohne Kragarme)
            # Das Muster enthält nur die normalen Felder (feld_1, feld_2, ...)
            # Die Feldgrenzen-Liste enthält aber alle Felder inkl. Kragarme
            
            # Index-Offset für normale Felder berechnen
            offset = 1 if kragarm_links > 0 else 0
            
            for idx, ist_belastet in enumerate(muster):
                # idx bezieht sich auf normale Felder (0 = feld_1, 1 = feld_2, ...)
                # In feldgrenzen ist das bei Position offset + idx
                feld_start_idx = offset + idx
                feld_ende_idx = offset + idx + 1
                
                if feld_ende_idx < len(feldgrenzen):
                    feld_start = feldgrenzen[feld_start_idx]
                    feld_ende = feldgrenzen[feld_ende_idx]

                    if ist_belastet:
                        ax.axvspan(feld_start, feld_ende,
                                   alpha=0.15, color='green', zorder=0)
                    else:
                        ax.axvspan(feld_start, feld_ende,
                                   alpha=0.08, color='red', zorder=0)

        # 6. Momentendiagramm (klassische Vorzeichen)
        # Vorzeichen drehen und in kNm umrechnen
        m_kNm = np.array(m) / 1000000
        zeichne_belastungsmuster(axs[1], moment_muster, feldgrenzen)
        axs[1].plot(x, m_kNm, color='red', linewidth=2,
                    label="Moment", zorder=2)
        axs[1].axhline(0, color='gray', linestyle='--', linewidth=1, zorder=1)
        axs[1].set_ylabel("M [kNm]")
        title_moment = f"Momentenverlauf (unten positiv)\n{moment_kombi}"
        axs[1].set_title(title_moment, fontsize=10)
        
        # Feinere Y-Achsen-Skalierung für Moment
        m_max = np.max(np.abs(m_kNm))
        y_limit = m_max * 1.15  # 15% Puffer
        axs[1].set_ylim(-y_limit, y_limit)
        # Tick-Spacing auf saubere 5er oder 10er runden
        raw_spacing = m_max / 5  # Ca. 5-6 Intervalle
        if raw_spacing <= 5:
            tick_spacing = 5
        elif raw_spacing <= 10:
            tick_spacing = 10
        elif raw_spacing <= 15:
            tick_spacing = 15
        elif raw_spacing <= 20:
            tick_spacing = 20
        elif raw_spacing <= 25:
            tick_spacing = 25
        elif raw_spacing <= 50:
            tick_spacing = 50
        else:
            tick_spacing = int(round(raw_spacing / 10) * 10)  # Auf 10er runden
        axs[1].yaxis.set_major_locator(MultipleLocator(tick_spacing))
        axs[1].yaxis.set_minor_locator(AutoMinorLocator(2))
        axs[1].grid(True, which='major', alpha=0.3, linestyle='-')
        axs[1].grid(True, which='minor', alpha=0.15, linestyle=':')
        
        # Maxima/Minima markieren
        idx_max = np.argmax(m_kNm)
        idx_min = np.argmin(m_kNm)
        axs[1].plot(x[idx_max], m_kNm[idx_max], 'ro', markersize=6, zorder=3)
        axs[1].plot(x[idx_min], m_kNm[idx_min], 'ro', markersize=6, zorder=3)
        axs[1].annotate(f'{m_kNm[idx_max]:.1f}', xy=(x[idx_max], m_kNm[idx_max]), 
                       xytext=(5, 5), textcoords='offset points', fontsize=8, color='red',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='red', alpha=0.8))
        axs[1].annotate(f'{m_kNm[idx_min]:.1f}', xy=(x[idx_min], m_kNm[idx_min]), 
                       xytext=(5, -15), textcoords='offset points', fontsize=8, color='red',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='red', alpha=0.8))

        # Legende mit Belastungsmuster-Info
        from matplotlib.patches import Patch
        legend_elements = [
            plt.Line2D([0], [0], color='red', linewidth=2, label='Moment'),
            Patch(facecolor='green', alpha=0.15, label='Feld belastet (Q)'),
            Patch(facecolor='red', alpha=0.08, label='Feld unbelastet')
        ]
        axs[1].legend(handles=legend_elements, loc='best', fontsize=8)

        # 7. Querkraftdiagramm (klassische Vorzeichen, in kN)
        q_kN = np.array(q) / 1000  # Vorzeichen drehen und in kN umrechnen
        zeichne_belastungsmuster(axs[2], querkraft_muster, feldgrenzen)
        axs[2].plot(x, q_kN, color='blue', linewidth=2,
                    label="Querkraft", zorder=2)
        axs[2].axhline(0, color='gray', linestyle='--', linewidth=1, zorder=1)
        axs[2].set_ylabel("Q [kN]")
        title_querkraft = f"Querkraftverlauf (unten positiv)\n{querkraft_kombi}"
        axs[2].set_title(title_querkraft, fontsize=10)
        
        # Feinere Y-Achsen-Skalierung für Querkraft
        q_max = np.max(np.abs(q_kN))
        y_limit_q = q_max * 1.15
        axs[2].set_ylim(-y_limit_q, y_limit_q)
        # Tick-Spacing auf saubere 5er oder 10er runden (gleiche Logik wie Moment)
        raw_spacing_q = q_max / 5
        if raw_spacing_q <= 5:
            tick_spacing_q = 5
        elif raw_spacing_q <= 10:
            tick_spacing_q = 10
        elif raw_spacing_q <= 15:
            tick_spacing_q = 15
        elif raw_spacing_q <= 20:
            tick_spacing_q = 20
        elif raw_spacing_q <= 25:
            tick_spacing_q = 25
        elif raw_spacing_q <= 50:
            tick_spacing_q = 50
        else:
            tick_spacing_q = int(round(raw_spacing_q / 10) * 10)
        axs[2].yaxis.set_major_locator(MultipleLocator(tick_spacing_q))
        axs[2].yaxis.set_minor_locator(AutoMinorLocator(2))
        axs[2].grid(True, which='major', alpha=0.3, linestyle='-')
        axs[2].grid(True, which='minor', alpha=0.15, linestyle=':')
        
        # Maxima/Minima markieren
        idx_max_q = np.argmax(q_kN)
        idx_min_q = np.argmin(q_kN)
        axs[2].plot(x[idx_max_q], q_kN[idx_max_q], 'bo', markersize=6, zorder=3)
        axs[2].plot(x[idx_min_q], q_kN[idx_min_q], 'bo', markersize=6, zorder=3)
        axs[2].annotate(f'{q_kN[idx_max_q]:.1f}', xy=(x[idx_max_q], q_kN[idx_max_q]), 
                       xytext=(5, 5), textcoords='offset points', fontsize=8, color='blue',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='blue', alpha=0.8))
        axs[2].annotate(f'{q_kN[idx_min_q]:.1f}', xy=(x[idx_min_q], q_kN[idx_min_q]), 
                       xytext=(5, -15), textcoords='offset points', fontsize=8, color='blue',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='blue', alpha=0.8))
        
        axs[2].legend()

        # 8. Durchbiegung (GZG!)
        if w is not None:
            w_mm = -np.array(w)  # Vorzeichen für Darstellung (unten positiv)
            zeichne_belastungsmuster(axs[3], durchbiegung_muster, feldgrenzen)
            axs[3].plot(x, w_mm, color='purple',
                        linewidth=2, label="Durchbiegung", zorder=2)
            axs[3].axhline(0, color='gray', linestyle='--',
                           linewidth=1, zorder=1)
            axs[3].set_ylabel("w [mm]")
            # GZG im Titel kennzeichnen (nur wenn GZG wirklich verfügbar)
            grenzzustand_text = "GZG" if gzg_verfuegbar else "GZT (Fallback)"
            title_durchbiegung = f"Durchbiegung (unten positiv) - {grenzzustand_text}\n{durchbiegung_kombi}"
            axs[3].set_title(title_durchbiegung, fontsize=10)
            
            # Feinere Y-Achsen-Skalierung für Durchbiegung
            # Obere Grenze bei 0 (keine Aufbiegung), untere Grenze bei max Durchbiegung + Puffer
            w_max = np.max(w_mm)  # Maximale Durchbiegung nach unten
            w_min = np.min(w_mm)  # Sollte ~0 sein oder leicht negativ
            # Y-Limits: von kleiner negativer Wert (oder 0) bis max + 15%
            y_min_w = min(w_min * 1.15, -w_max * 0.05)  # Kleiner Puffer nach oben
            y_max_w = w_max * 1.15  # 15% Puffer nach unten
            axs[3].set_ylim(y_min_w, y_max_w)
            
            # Ticks anpassen - auf gerade Zahlen runden
            raw_spacing_w = w_max / 5  # Ca. 5-6 Intervalle
            # Auf nächste gerade Zahl runden (2, 4, 6, 8, 10, 12, ...)
            tick_spacing_w = max(2, int(round(raw_spacing_w / 2) * 2))
            axs[3].yaxis.set_major_locator(MultipleLocator(tick_spacing_w))
            axs[3].yaxis.set_minor_locator(AutoMinorLocator(2))
            axs[3].grid(True, which='major', alpha=0.3, linestyle='-')
            axs[3].grid(True, which='minor', alpha=0.15, linestyle=':')
            
            # Maxima/Minima markieren (bei Durchbiegung vor allem Maximum interessant)
            idx_max_w = np.argmax(w_mm)
            axs[3].plot(x[idx_max_w], w_mm[idx_max_w], 'o', color='purple', markersize=6, zorder=3)
            axs[3].annotate(f'{w_mm[idx_max_w]:.2f} mm', xy=(x[idx_max_w], w_mm[idx_max_w]), 
                           xytext=(5, 5), textcoords='offset points', fontsize=8, color='purple',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='purple', alpha=0.8))
            
            axs[3].legend()

        axs[3].set_xlabel("Länge [m]")
        axs[1].invert_yaxis()  # Momentendiagramm: positiv nach unten
        axs[2].invert_yaxis()  # Querkraftdiagramm: positiv nach unten
        axs[3].invert_yaxis()  # Durchbiegung: positiv nach unten

        # 9. In Tkinter-Fenster einbetten
        if hasattr(self, "canvas") and self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(fig, master=self.schnittkraftfenster)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
