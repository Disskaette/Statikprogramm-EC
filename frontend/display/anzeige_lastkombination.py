import tkinter as tk
import threading
import logging
from tkinter import ttk
from backend.calculations.lastenkombination import MethodeLastkombi
from PIL import ImageTk

# Root-Logger-Verhalten
logging.basicConfig(
    level=logging.INFO,                      # ab welcher Wichtigkeit geloggt wird
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S"
)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.INFO)
logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
logger = logging.getLogger(__name__)          # logger für dieses Modul


class LastkombiAnzeiger:
    def __init__(self, parent_frame, eingabemaske, db):
        self.parent = parent_frame
        self.eingabemaske = eingabemaske
        self.db = db
        self.kombi_berechnung = MethodeLastkombi(self.eingabemaske, self.db)

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

    def aktualisiere_darstellung_threaded(self, latex_kombis: dict, callback=None):
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
                self.parent.after(0, lambda: self.zeige_bilder(
                    bilder, callback=callback))

            except Exception as e:
                # Fehler an GUI übergeben, e als Default-Argument festhalten
                self.parent.after(0, lambda err=e: self.zeige_fehler(err))

        threading.Thread(target=worker, daemon=True).start()

    def zeige_bilder(self, bilder, callback=None):
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

        if callback:
            callback()

    def zeige_fehler(self, e):
        for widget in self.latex_frame_lastkombination.winfo_children():
            widget.destroy()
        label = ttk.Label(self.latex_frame_lastkombination,
                          text=f"⚠️ Fehler: {e}")
        label.pack()
