import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import logging
import threading
from PIL import ImageTk
from backend.calculations.nachweis_ec5 import MethodeNachweisEC5

logger = logging.getLogger(__name__)


class NachweisEC5Anzeiger:
    def __init__(self, parent_frame, eingabemaske):
        from frontend.gui.theme_config import ThemeManager
        fonts = ThemeManager.get_fonts()

        self.parent = parent_frame
        self.eingabemaske = eingabemaske
        self.root = eingabemaske.root
        self.db = eingabemaske.db
        self.nachweis_berechnung = MethodeNachweisEC5(
            self.eingabemaske, self.db)
        self.tk_images = []  # Wichtig: Referenzen auf Bilder halten

        # LaTeX-Cache für Light/Dark Varianten
        from frontend.gui.latex_renderer import LaTeXImageCache
        self.latex_cache = LaTeXImageCache()
        # Aktuellen Mode vom ThemeManager holen (bereits importiert oben)
        self._current_mode = ThemeManager._current_mode
        self._last_data = None  # Speichere letzte Daten für Refresh

        # Theme-Callback registrieren: Cache leeren UND neu rendern bei Theme-Wechsel
        ThemeManager.register_theme_callback(self._on_theme_change)

        # Frames für die Anzeige erstellen (analog zur Lastenkombination)
        self.frame_biegung = ctk.CTkFrame(self.parent)
        self.frame_biegung.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(self.frame_biegung, text="Biegungsnachweis",
                     font=fonts['heading']).pack(pady=5)
        self.latex_frame_biegung = ctk.CTkFrame(self.frame_biegung)
        self.latex_frame_biegung.pack(
            fill="both", expand=True, padx=10, pady=10)

        self.frame_schub = ctk.CTkFrame(self.parent)
        self.frame_schub.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(self.frame_schub, text="Schubnachweis",
                     font=fonts['heading']).pack(pady=5)
        self.latex_frame_schub = ctk.CTkFrame(self.frame_schub)
        self.latex_frame_schub.pack(fill="both", expand=True, padx=10, pady=10)

        self.frame_durchbiegung = ctk.CTkFrame(self.parent)
        self.frame_durchbiegung.pack(
            fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(self.frame_durchbiegung, text="Durchbiegungsnachweise",
                     font=fonts['heading']).pack(pady=5)
        self.latex_frame_durchbiegung = ctk.CTkFrame(self.frame_durchbiegung)
        self.latex_frame_durchbiegung.pack(
            fill="both", expand=True, padx=10, pady=10)

    def update(self, nachweise_data: dict, callback=None):
        """Startet die Bilderzeugung in einem Hintergrund-Thread (analog zur Lastenkombination)."""
        self._last_data = nachweise_data  # Speichere für Theme-Wechsel
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
        """Aktualisiert die Bild-Labels im Haupt-Thread."""
        self._clear_frames()
        self.tk_images.clear()

        # Zentrale Skalierung: global + Breitenbeschränkung
        from frontend.gui.theme_config import ThemeManager
        from frontend.gui.latex_renderer import scale_images_uniform

        LATEX_SCALE_FACTOR = ThemeManager.get_latex_scale()

        # Nur die Bilder extrahieren (ohne Typen)
        images_only = [img for _, img in bilder]

        # Zentral skalieren (global + auf längste begrenzt)
        scaled_images = scale_images_uniform(images_only, LATEX_SCALE_FACTOR)

        # Mit Typen wieder kombinieren
        for (typ, _), scaled_img in zip(bilder, scaled_images):
            if scaled_img is None:
                continue

            tk_bild = ImageTk.PhotoImage(scaled_img)
            self.tk_images.append(tk_bild)

            # Bestimme Ziel-Frame basierend auf Nachweis-Typ
            # WICHTIG: durchbiegung muss vor biegung stehen, da "durchbiegung" auch "biegung" enthält!
            if "durchbiegung" in typ:
                parent_frame = self.latex_frame_durchbiegung
            elif "biegung" in typ:
                parent_frame = self.latex_frame_biegung
            elif "schub" in typ:
                parent_frame = self.latex_frame_schub
            else:
                parent_frame = self.latex_frame_biegung  # Fallback

            # CustomTkinter-Label für Bilder mit Theme-Hintergrund
            label = ctk.CTkLabel(parent_frame, text="", image=tk_bild)
            label.image = tk_bild
            label.pack(anchor="w", pady=2)

        if callback:
            callback()

    def _on_theme_change(self):
        """Callback für Theme-Wechsel: Cache leeren und Bilder neu rendern."""
        self.latex_cache.clear()
        if self._last_data:
            # Neu rendern mit gespeicherten Daten
            self.update(self._last_data)

    def zeige_fehler(self, e):
        """Zeigt Fehlermeldung an (analog zur Lastenkombination)."""
        self._clear_frames()
        from frontend.gui.theme_config import ThemeManager
        label = ctk.CTkLabel(self.latex_frame_biegung,
                             text=f"⚠️ Fehler: {e}",
                             text_color=ThemeManager.COLORS['accent_red'])
        label.pack(anchor="w", pady=2)

    def _clear_frames(self):
        """Löscht alle Widgets aus den LaTeX-Frames (analog zur Lastenkombination)."""
        for widget in self.latex_frame_biegung.winfo_children():
            widget.destroy()
        for widget in self.latex_frame_schub.winfo_children():
            widget.destroy()
        for widget in self.latex_frame_durchbiegung.winfo_children():
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
                    latex_str, fg_hex, dpi=1000, fontsize=5)
                if img:
                    self.latex_cache.put(
                        latex_str, mode, cache_key_bg, fg_hex, img)
                    logger.debug(
                        f"LaTeX transparent gerendert & gecacht: mode={mode}, fg={fg_hex}")

            return img

        except Exception as e:
            logger.error(f"Fehler beim LaTeX-Rendering: {e}", exc_info=True)
            return None
