import tkinter as tk
import matplotlib.pyplot as plt
import threading
import logging
import numpy as np
from tkinter import ttk
from backend.calculations.lastenkombination import MethodeLastkombi
from PIL import ImageTk
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


class LastkombiAnzeiger:
    def __init__(self, parent_frame, eingabemaske, db):
        self.parent = parent_frame
        self.eingabemaske = eingabemaske
        self.db = db
        self.kombi_berechnung = MethodeLastkombi(self.eingabemaske, self.db)
        self.schnittkraftfenster = None
        self.schnittkraft_canvas = None

        # Frame für Lastkombinationen
        self.frame_lastkombis = ttk.LabelFrame(
            self.parent, text="Lastkombinationen", padding=10)
        self.frame_lastkombis.pack(fill="both", expand=True, padx=10, pady=10)

        self.latex_frame_lastkombination = ttk.Frame(self.frame_lastkombis)
        self.latex_frame_lastkombination.pack(fill="both", expand=True)

        # Frame für Bemessungslast
        self.frame_ed = ttk.LabelFrame(
            self.parent, text="Bemessungslast Ed", padding=10)
        self.frame_ed.pack(fill="both", expand=True, padx=10, pady=10)

        self.latex_frame_bemessungslast = ttk.Frame(self.frame_ed)
        self.latex_frame_bemessungslast.pack(fill="both", expand=True)

    def aktualisiere_darstellung_threaded(self, latex_kombis: dict):
        def worker():
            try:
                bilder = []

                massgebende_kombi = next(
                    (item for item in latex_kombis.items() if item[1].get("massgebend")), None)

                if self.eingabemaske.anzeige_lastkombis.get() == 1 and massgebende_kombi:
                    kombiliste = [massgebende_kombi]
                else:
                    kombiliste = list(latex_kombis.items())

                for _, kombi in kombiliste:
                    img = self.kombi_berechnung.render_latex_to_image(
                        kombi["latex"])
                    bilder.append(("kombi", img))

                if massgebende_kombi:
                    img_ed = self.kombi_berechnung.render_latex_to_image(
                        massgebende_kombi[1]["latex_ed"])
                    bilder.append(("ed", img_ed))

                # Bilder an Hauptthread übergeben
                self.parent.after(0, lambda: self.zeige_bilder(bilder))

            except Exception as e:
                # Fehler an GUI übergeben, e als Default-Argument festhalten
                self.parent.after(0, lambda err=e: self.zeige_fehler(err))

        threading.Thread(target=worker, daemon=True).start()

    def zeige_bilder(self, bilder):
        for widget in self.latex_frame_lastkombination.winfo_children():
            widget.destroy()
        for widget in self.latex_frame_bemessungslast.winfo_children():
            widget.destroy()

        for typ, img in bilder:
            tk_bild = ImageTk.PhotoImage(img)
            label = tk.Label(
                self.latex_frame_bemessungslast if typ == "ed"
                else self.latex_frame_lastkombination,
                image=tk_bild
            )
            label.image = tk_bild  # Referenz speichern!
            label.pack(anchor="w", pady=5)

    def zeige_fehler(self, e):
        for widget in self.latex_frame_lastkombination.winfo_children():
            widget.destroy()
        label = ttk.Label(self.latex_frame_lastkombination,
                          text=f"⚠️ Fehler: {e}")
        label.pack()

    def toggle_schnittkraftfenster(self):
        if self.eingabemaske.schnittgroeßen_anzeige_button.get():
            if self.schnittkraftfenster is None or not tk.Toplevel.winfo_exists(self.schnittkraftfenster):
                self.schnittkraftfenster = tk.Toplevel(self.parent)
                self.schnittkraftfenster.title(
                    "Schnittkraft- und Durchbiegungsverläufe GZT")
                self.schnittkraftfenster.protocol(
                    "WM_DELETE_WINDOW", self._close_schnittkraftfenster)
                self._plot_schnittkraefte()
        else:
            self._close_schnittkraftfenster()

    def _close_schnittkraftfenster(self):
        if self.schnittkraftfenster is not None:
            self.schnittkraftfenster.destroy()
            self.schnittkraftfenster = None
        else:
            return

    def _plot_schnittkraefte(self):
        import numpy as np
        import matplotlib.pyplot as plt

        schnitt = self.eingabemaske.result["Schnittgroessen"]["GZT"]
        m = schnitt["moment"]
        q = schnitt["querkraft"]
        w = schnitt.get("durchbiegung", None)

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
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        if hasattr(self, "canvas") and self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(fig, master=self.schnittkraftfenster)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
