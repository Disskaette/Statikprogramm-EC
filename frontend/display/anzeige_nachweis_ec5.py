import tkinter as tk
from tkinter import ttk
import logging
import threading
from PIL import ImageTk
from backend.calculations.nachweis_ec5 import MethodeNachweisEC5

logger = logging.getLogger(__name__)


class NachweisEC5Anzeiger:
    def __init__(self, parent_frame, eingabemaske):
        self.parent = parent_frame
        self.eingabemaske = eingabemaske
        self.root = eingabemaske.root
        self.db = eingabemaske.db
        self.nachweis_berechnung = MethodeNachweisEC5(
            self.eingabemaske, self.db)
        self.tk_images = []  # Wichtig: Referenzen auf Bilder halten

        # Frames für die Anzeige erstellen (analog zur Lastenkombination)
        self.frame_biegung = ttk.LabelFrame(
            self.parent, text="Biegungsnachweis", padding=10)
        self.frame_biegung.pack(fill="both", expand=True, padx=10, pady=10)
        self.latex_frame_biegung = ttk.Frame(self.frame_biegung)
        self.latex_frame_biegung.pack(fill="both", expand=True)

        self.frame_schub = ttk.LabelFrame(
            self.parent, text="Schubnachweis", padding=10)
        self.frame_schub.pack(fill="both", expand=True, padx=10, pady=10)
        self.latex_frame_schub = ttk.Frame(self.frame_schub)
        self.latex_frame_schub.pack(fill="both", expand=True)

        self.frame_durchbiegung = ttk.LabelFrame(
            self.parent, text="Durchbiegungsnachweise", padding=10)
        self.frame_durchbiegung.pack(
            fill="both", expand=True, padx=10, pady=10)
        self.latex_frame_durchbiegung = ttk.Frame(self.frame_durchbiegung)
        self.latex_frame_durchbiegung.pack(fill="both", expand=True)

    def update(self, nachweise_data: dict, callback=None):
        """Startet die Bilderzeugung in einem Hintergrund-Thread (analog zur Lastenkombination)."""
        thread = threading.Thread(
            target=self._run_update_in_thread, args=(nachweise_data, callback))
        thread.daemon = True
        thread.start()

    def _run_update_in_thread(self, nachweise_data, callback):
        """Rendert LaTeX zu Bildern im Hintergrund (analog zur Lastenkombination)."""
        try:
            bilder = []

            # Für jeden Nachweis LaTeX-Bilder erstellen (nur das latex-Feld)
            for nachweis_typ, nachweis_data in nachweise_data.items():
                if not nachweis_data or 'latex' not in nachweis_data:
                    continue

                # Direkt das LaTeX-Feld rendern (Frontend-Methode)
                img = self.render_latex_to_image(nachweis_data['latex'])
                if img:
                    bilder.append((nachweis_typ, img))

            self.root.after(0, lambda: self._show_images(bilder, callback))
        except Exception as e:
            logger.error(
                f"Fehler bei Bilderzeugung für EC5-Nachweise: {e}", exc_info=True)
            self.root.after(0, lambda err=e: self.zeige_fehler(err))

    def _show_images(self, bilder, callback):
        """Aktualisiert die Bild-Labels im Haupt-Thread (analog zur Lastenkombination)."""
        self._clear_frames()
        self.tk_images.clear()

        for typ, img in bilder:
            tk_bild = ImageTk.PhotoImage(img)
            self.tk_images.append(tk_bild)

            # Bestimme Ziel-Frame basierend auf Nachweis-Typ
            # WICHTIG: durchbiegung muss vor biegung stehen, da "durchbiegung" auch "biegung" enthält!
            if "durchbiegung" in typ:  # durchbiegung_inst, durchbiegung_fin, durchbiegung_net_fin
                parent_frame = self.latex_frame_durchbiegung
            elif "biegung" in typ:
                parent_frame = self.latex_frame_biegung
            elif "schub" in typ:
                parent_frame = self.latex_frame_schub
            else:
                parent_frame = self.latex_frame_biegung  # Fallback

            label = tk.Label(parent_frame, image=tk_bild, bg="white")
            label.image = tk_bild
            label.pack(anchor="w", pady=2)

        if callback:
            callback()

    def zeige_fehler(self, e):
        """Zeigt Fehlermeldung an (analog zur Lastenkombination)."""
        self._clear_frames()
        label = ttk.Label(self.latex_frame_biegung,
                          text=f"⚠️ Fehler: {e}")
        label.pack()

    def _clear_frames(self):
        """Löscht alle Widgets aus den LaTeX-Frames (analog zur Lastenkombination)."""
        for widget in self.latex_frame_biegung.winfo_children():
            widget.destroy()
        for widget in self.latex_frame_schub.winfo_children():
            widget.destroy()
        for widget in self.latex_frame_durchbiegung.winfo_children():
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
