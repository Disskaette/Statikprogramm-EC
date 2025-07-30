import tkinter as tk
import matplotlib.pyplot as plt
import threading
import logging
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
        self.eingabemaske.root.after(0, lambda: self.eingabemaske.max_moment_kalt.config(
            text=f"{moment/1_000_000:.1f}"))
        self.eingabemaske.root.after(0, lambda: self.eingabemaske.max_querkraft_kalt.config(
            text=f"{querkraft/1000:.1f}"))

    def toggle_schnittkraftfenster(self):
        if self.eingabemaske.schnittgroeßen_anzeige_button.get():
            if self.schnittkraftfenster is None or not tk.Toplevel.winfo_exists(self.schnittkraftfenster):
                self.schnittkraftfenster = tk.Toplevel(self.eingabemaske.root)
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
        # Direkter Zugriff auf Schnittgrößen-Daten (ohne system_memory)
        schnittgroessen = self.eingabemaske.snapshot.get("Schnittgroessen", {})
        schnitt = schnittgroessen.get("GZT")

        if not schnitt:
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

        m = schnitt.get("moment")
        q = schnitt.get("querkraft")
        w = schnitt.get("durchbiegung", None)

        if not m or not q:
            print("Unvollständige Schnittgrößen-Daten.")
            return

        # Spannweiten und Feldgrenzen bestimmen

        spannweiten_dict = self.eingabemaske.snapshot.get("spannweiten", {})
        spannweiten_keys = list(spannweiten_dict.keys())
        spannweiten = list(spannweiten_dict.values())
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

        # 6. Momentendiagramm (klassische Vorzeichen)
        # Vorzeichen drehen und in kNm umrechnen
        m_kNm = np.array(m) / 1000000
        axs[1].plot(x, m_kNm, color='red', label="Moment")
        axs[1].axhline(0, color='gray', linestyle='--', linewidth=1)
        axs[1].set_ylabel("M [kNm]")
        axs[1].set_title("Momentenverlauf (unten positiv)")
        axs[1].legend()

        # 7. Querkraftdiagramm (klassische Vorzeichen, in kN)
        q_kN = np.array(q) / 1000  # Vorzeichen drehen und in kN umrechnen
        axs[2].plot(x, q_kN, color='blue', label="Querkraft")
        axs[2].axhline(0, color='gray', linestyle='--', linewidth=1)
        axs[2].set_ylabel("Q [kN]")
        axs[2].set_title("Querkraftverlauf (unten positiv)")
        axs[2].legend()

        # 8. Durchbiegung (wie gehabt)
        if w is not None:
            axs[3].plot(x, -np.array(w), color='purple', label="Durchbiegung")
            axs[3].axhline(0, color='gray', linestyle='--', linewidth=1)
            axs[3].set_ylabel("w [mm]")
            axs[3].set_title("Durchbiegung (unten positiv)")
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
