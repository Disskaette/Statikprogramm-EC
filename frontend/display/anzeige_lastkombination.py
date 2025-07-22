import tkinter as tk
from tkinter import ttk
import logging
import threading
from PIL import ImageTk
from backend.calculations.lastenkombination import MethodeLastkombi

logger = logging.getLogger(__name__)


class LastkombiAnzeiger:
    def __init__(self, root, parent_frame, eingabemaske, db):
        self.root = root
        self.parent = parent_frame
        self.eingabemaske = eingabemaske
        self.db = db
        self.kombi_berechnung = MethodeLastkombi(self.eingabemaske, self.db)
        self.tk_images = []  # Wichtig: Referenzen auf Bilder halten

        # Frames für die Anzeige erstellen
        self.frame_lastkombi = ttk.LabelFrame(
            self.parent, text="Lastkombinationen", padding=10)
        self.frame_lastkombi.pack(fill="both", expand=True, padx=10, pady=10)
        self.latex_frame_lastkombination = ttk.Frame(self.frame_lastkombi)
        self.latex_frame_lastkombination.pack(fill="both", expand=True)

        self.frame_ed = ttk.LabelFrame(
            self.parent, text="Bemessungslast Ed", padding=10)
        self.frame_ed.pack(fill="both", expand=True, padx=10, pady=10)
        self.latex_frame_bemessungslast = ttk.Frame(self.frame_ed)
        self.latex_frame_bemessungslast.pack(fill="both", expand=True)

    def update(self, latex_kombis: dict, callback=None):
        """Startet die Bilderzeugung in einem Hintergrund-Thread."""
        thread = threading.Thread(
            target=self._run_update_in_thread, args=(latex_kombis, callback))
        thread.daemon = True
        thread.start()

    def _run_update_in_thread(self, latex_kombis, callback):
        """Rendert LaTeX zu Bildern im Hintergrund."""
        try:
            bilder = []
            massgebende_kombi = next(
                (item for item in latex_kombis.items() if item[1].get("massgebend")), None)

            kombiliste = [massgebende_kombi] if self.eingabemaske.anzeige_lastkombis.get(
            ) == 1 and massgebende_kombi else list(latex_kombis.items())

            for _, kombi in kombiliste:
                img = self.render_latex_to_image(kombi["latex"])
                if img:
                    bilder.append(("kombi", img))

            if massgebende_kombi:
                img_ed = self.render_latex_to_image(
                    massgebende_kombi[1]["latex_ed"])
                if img_ed:
                    bilder.append(("ed", img_ed))

            self.root.after(0, lambda: self._show_images(bilder, callback))
        except Exception as e:
            logger.error(
                f"Fehler bei Bilderzeugung für Lastkombis: {e}", exc_info=True)
            self.root.after(0, lambda err=e: self.zeige_fehler(err))

    def _show_images(self, bilder, callback):
        """Aktualisiert die Bild-Labels im Haupt-Thread."""
        self._clear_frames()
        self.tk_images.clear()

        for typ, img in bilder:
            tk_bild = ImageTk.PhotoImage(img)
            self.tk_images.append(tk_bild)
            parent_frame = self.latex_frame_lastkombination if typ == "kombi" else self.latex_frame_bemessungslast
            label = tk.Label(parent_frame, image=tk_bild, bg="white")
            label.image = tk_bild
            label.pack(anchor="w", pady=2)

        if callback:
            callback()

    def zeige_fehler(self, e):
        self._clear_frames()
        label = ttk.Label(self.latex_frame_lastkombination,
                          text=f"⚠️ Fehler: {e}")
        label.pack()

    def _clear_frames(self):
        for widget in self.latex_frame_lastkombination.winfo_children():
            widget.destroy()
        for widget in self.latex_frame_bemessungslast.winfo_children():
            widget.destroy()

    def render_latex_to_image(self, latex_str):
        """Rendert LaTeX-String zu PIL-Image (Frontend-Methode)."""
        try:
            # Matplotlib nur im Haupt-Thread importieren
            import matplotlib
            matplotlib.use('Agg')  # Thread-sicherer Backend
            import matplotlib.pyplot as plt
            from PIL import Image
            from io import BytesIO

            fig, ax = plt.subplots(figsize=(4, 0.05), dpi=200)
            fig.patch.set_visible(False)
            ax.axis("off")

            ax.text(0.01, 0.5, latex_str,
                    fontsize=5, va="center", ha="left")

            buf = BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight",
                        pad_inches=0.05, transparent=True)
            plt.close(fig)

            buf.seek(0)
            return Image.open(buf)

        except Exception as e:
            logger.error(f"Fehler beim LaTeX-Rendering: {e}")
            return None
