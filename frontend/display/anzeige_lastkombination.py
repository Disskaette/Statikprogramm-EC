import tkinter as tk
from tkinter import ttk
import logging
import threading
from PIL import ImageTk

logger = logging.getLogger(__name__)


class LastkombiAnzeiger:
    def __init__(self, parent_frame, eingabemaske):
        self.parent_frame = parent_frame
        self.root = eingabemaske.root
        self.eingabemaske = eingabemaske
        self.tk_images = []  # Referenzen für GC-Schutz

        # LaTeX-Cache für Light/Dark Varianten
        from frontend.gui.latex_renderer import LaTeXImageCache
        from frontend.gui.theme_config import ThemeManager
        self.latex_cache = LaTeXImageCache()
        self._current_mode = ThemeManager._current_mode

        # Frames für die Anzeige erstellen
        self.frame_lastkombi = ttk.LabelFrame(
            parent_frame, text="Lastkombinationen", padding=10)
        self.frame_lastkombi.pack(fill="both", expand=True, padx=10, pady=10)

        # WICHTIG: ttk.Frame nutzt automatisch richtige Theme-Farbe!
        self.latex_frame_lastkombination = ttk.Frame(self.frame_lastkombi)
        self.latex_frame_lastkombination.pack(fill="both", expand=True)

        self.frame_ed = ttk.LabelFrame(
            parent_frame, text="Bemessungslast Ed", padding=10)
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

            # ttk.Label nutzt automatisch richtige Theme-Farbe!
            label = ttk.Label(parent_frame, image=tk_bild)
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
        """Rendert LaTeX MIT TRANSPARENZ (wie Systemanzeige)."""
        try:
            from frontend.gui.latex_renderer import render_latex_transparent, tkcolor_to_hex
            from frontend.gui.theme_config import ThemeManager

            # WICHTIG: Nutze die TATSÄCHLICHE ttk-Textfarbe, nicht ThemeManager!
            style = ttk.Style(self.root)
            fg_ttk = style.lookup('TLabel', 'foreground')
            if fg_ttk:
                fg_hex = tkcolor_to_hex(self.root, fg_ttk)
            else:
                # Fallback: System-Farbe (schwarz in Light, weiß in Dark)
                fg_hex = '#000000' if ThemeManager._current_mode == 'light' else '#E0E0E0'

            mode = ThemeManager._current_mode

            # Aus Cache holen oder neu rendern
            cache_key_bg = "transparent"
            img = self.latex_cache.get(latex_str, mode, cache_key_bg, fg_hex)

            if img is None:
                # Neu rendern: MIT TRANSPARENZ (hohe Qualität!)
                img = render_latex_transparent(
                    latex_str, fg_hex, dpi=200, fontsize=5)
                if img:
                    self.latex_cache.put(
                        latex_str, mode, cache_key_bg, fg_hex, img)
                    logger.debug(
                        f"LaTeX transparent gerendert & gecacht: mode={mode}, fg={fg_hex}")

            return img

        except Exception as e:
            logger.error(f"Fehler beim LaTeX-Rendering: {e}", exc_info=True)
            return None
