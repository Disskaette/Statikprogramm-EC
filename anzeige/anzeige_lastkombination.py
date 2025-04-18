import tkinter as tk
from tkinter import ttk
from berechnungen.lastenkombination import MethodeLastkombi
from PIL import Image, ImageTk


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

    def aktualisiere_darstellung(self):
        # Alte Inhalte löschen
        for widget in self.latex_frame_lastkombination.winfo_children():
            widget.destroy()
        for widget in self.latex_frame_bemessungslast.winfo_children():
            widget.destroy()

        try:
            latex_kombis = self.kombi_berechnung.berechne_dynamische_lastkombination()
            if not latex_kombis:
                label = ttk.Label(self.latex_frame_lastkombination,
                                  text="Keine gültigen Daten vorhanden.")
                label.pack()
                return

            # Kombis auswählen
            if self.eingabemaske.anzeige_lastkombis.get() == 1:
                kombiliste = [item for item in latex_kombis.items()
                              if item[1].get("massgebend")]
            else:
                kombiliste = list(latex_kombis.items())

            # Anzeige: Kombinationen (mit kmod)
            for _, kombi in kombiliste:
                zeile = ttk.Frame(self.latex_frame_lastkombination)
                zeile.pack(fill="x", anchor="w", pady=5)

                bild = self.kombi_berechnung.render_latex_to_image(
                    kombi["latex"])
                tk_bild = ImageTk.PhotoImage(bild)
                bild_label = tk.Label(zeile, image=tk_bild)
                bild_label.image = tk_bild
                bild_label.pack(side="left")

            # Anzeige: Maßgebende Ed-Kombination (ohne kmod)
            massgebende = next(
                (k for k in latex_kombis.values() if k.get("massgebend")), None)
            if massgebende:
                zeile_ed = ttk.Frame(self.latex_frame_bemessungslast)
                zeile_ed.pack(fill="x", anchor="w", pady=5)

                bild_ed = self.kombi_berechnung.render_latex_to_image(
                    massgebende["latex_ed"])
                tk_bild_ed = ImageTk.PhotoImage(bild_ed)
                bild_label_ed = tk.Label(zeile_ed, image=tk_bild_ed)
                bild_label_ed.image = tk_bild_ed
                bild_label_ed.pack(anchor="w", pady=2)

        except Exception as e:
            error_label = ttk.Label(
                self.latex_frame_lastkombination, text=f"⚠️ Fehler: {e}")
            error_label.pack()
