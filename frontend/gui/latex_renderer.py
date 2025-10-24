"""
LaTeX-Renderer für Formeln ohne Transparenz (vermeidet Halos im Dark Mode).

Implementiert theme-fähiges Rendering:
- Ermittelt effektive Hintergrundfarbe aus ttk.Style
- Rendert direkt auf BG (kein Alpha-Kanal)
- Caching für Light/Dark Mode Varianten
"""

import logging
from tkinter import ttk
from typing import Optional, Tuple
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


def tkcolor_to_hex(root, color_str: str) -> str:
    """
    Konvertiert Tk-Farbe zu Hex-String #RRGGBB.
    
    Args:
        root: Tk root widget für winfo_rgb
        color_str: Tk-Farbe (z.B. 'systemWindowBackgroundColor', '#abc', '#aabbcc')
    
    Returns:
        Hex-String im Format #RRGGBB
    """
    if not color_str:
        return "#ffffff"
    
    # Bereits Hex?
    if color_str.startswith("#"):
        if len(color_str) == 7:
            return color_str
        elif len(color_str) == 4:  # #RGB -> #RRGGBB
            return "#" + "".join(2 * c for c in color_str[1:])
    
    try:
        # Tk-Farbe zu RGB konvertieren
        r, g, b = root.winfo_rgb(color_str)  # Gibt Werte 0..65535
        return f"#{r//256:02x}{g//256:02x}{b//256:02x}"
    except Exception as e:
        logger.warning(f"Konnte Farbe '{color_str}' nicht konvertieren: {e}")
        return "#ffffff"


def effective_ttk_bg(widget) -> str:
    """
    Ermittelt die effektive Hintergrundfarbe eines ttk-Widgets.
    
    Reihenfolge:
    1. Expliziter Style am Widget
    2. Klassenstyle (z.B. 'TFrame', 'TLabel')
    3. Widget.cget("background") Fallback
    4. Weiß als Default
    
    Args:
        widget: ttk oder tk Widget
    
    Returns:
        Hex-Farbe #RRGGBB
    """
    root = widget.winfo_toplevel()
    
    try:
        style = ttk.Style(widget)
        
        # 1. Expliziter Style?
        explicit_style = None
        try:
            explicit_style = widget.cget("style")
        except Exception:
            pass
        
        bg = None
        if explicit_style:
            bg = style.lookup(explicit_style, "background")
        
        # 2. Klassenstyle?
        if not bg:
            widget_class = widget.winfo_class()
            bg = style.lookup(widget_class, "background")
        
        # 3. Widget-Background direkt?
        if not bg:
            try:
                bg = widget.cget("background")
            except Exception:
                pass
        
        # 4. Default
        if not bg:
            bg = "#ffffff"
        
        return tkcolor_to_hex(root, bg)
        
    except Exception as e:
        logger.warning(f"Konnte BG von {widget} nicht ermitteln: {e}")
        return "#ffffff"


def render_latex_transparent(
    latex: str,
    fg_hex: str,
    dpi: int = 200,
    fontsize: int = 5
) -> Optional[Image.Image]:
    """
    Rendert LaTeX MIT TRANSPARENZ (wie Systemanzeige).
    
    Robusteste Lösung: Transparenter Hintergrund, Label-BG setzt Container-Farbe.
    
    Args:
        latex: LaTeX-String (ohne $...$)
        fg_hex: Text-Farbe #RRGGBB
        dpi: Auflösung (default: 200)
        fontsize: Schriftgröße (default: 5)
    
    Returns:
        PIL.Image (RGBA mit Transparenz) oder None bei Fehler
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        buf = BytesIO()
        
        # Transparente Figure/Axes (wie Systemanzeige!)
        fig = plt.figure(figsize=(4, 0.05), dpi=dpi)
        fig.patch.set_alpha(0.0)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.patch.set_alpha(0.0)
        
        # Text rendern
        ax.text(0.01, 0.5, latex,
                fontsize=fontsize, va="center", ha="left",
                color=fg_hex)
        
        # WICHTIG: transparent=True, kein Padding
        plt.savefig(buf, format="png", bbox_inches="tight",
                    pad_inches=0.0, transparent=True)
        plt.close(fig)
        
        buf.seek(0)
        img = Image.open(buf).convert("RGBA")
        
        # Guard gegen 1-px Mischsaum (verhindert Clipping-AA)
        w, h = img.size
        guard = Image.new("RGBA", (w+2, h+2), (0, 0, 0, 0))
        guard.paste(img, (1, 1))
        return guard
        
    except Exception as e:
        logger.error(f"Fehler beim LaTeX-Rendering: {e}", exc_info=True)
        return None


def render_latex_on_bg(
    latex: str,
    fg_hex: str,
    bg_hex: str,
    dpi: int = 200,
    fontsize: int = 5
) -> Optional[Image.Image]:
    """
    Rendert LaTeX-String direkt auf Hintergrundfarbe (OHNE Transparenz).
    
    DEPRECATED: Nutze render_latex_transparent() für bessere Ergebnisse!
    
    Args:
        latex: LaTeX-String (ohne $...$)
        fg_hex: Text-Farbe #RRGGBB
        bg_hex: Hintergrund-Farbe #RRGGBB
        dpi: Auflösung (default: 200)
        fontsize: Schriftgröße (default: 5)
    
    Returns:
        PIL.Image (RGB, kein Alpha) oder None bei Fehler
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        buf = BytesIO()
        
        # Figure mit exakter BG-Farbe
        fig = plt.figure(figsize=(4, 0.05), dpi=dpi)
        fig.patch.set_facecolor(bg_hex)
        
        # Axes mit gleicher BG-Farbe
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.set_facecolor(bg_hex)
        
        # Text rendern
        ax.text(0.01, 0.5, latex,
                fontsize=fontsize, va="center", ha="left",
                color=fg_hex)
        
        # WICHTIG: transparent=False, facecolor=bg_hex
        plt.savefig(buf, format="png", bbox_inches="tight",
                    pad_inches=0.05, transparent=False,
                    facecolor=bg_hex, edgecolor=bg_hex)
        plt.close(fig)
        
        buf.seek(0)
        img = Image.open(buf)
        
        # Sicherstellen dass es RGB ist (kein Alpha)
        if img.mode == "RGBA":
            # Alpha-Kanal entfernen, auf BG compositen
            rgb_img = Image.new("RGB", img.size, bg_hex)
            rgb_img.paste(img, mask=img.split()[3])  # Alpha als Maske
            return rgb_img
        
        return img.convert("RGB")
        
    except Exception as e:
        logger.error(f"Fehler beim LaTeX-Rendering: {e}", exc_info=True)
        return None


class LaTeXImageCache:
    """
    Cache für gerenderte LaTeX-Bilder (Light/Dark Varianten).
    
    Key: (latex, mode, bg_hex, fg_hex, dpi, fontsize)
    """
    
    def __init__(self):
        self._cache = {}
    
    def get(self, latex: str, mode: str, bg_hex: str, fg_hex: str,
            dpi: int = 200, fontsize: int = 5) -> Optional[Image.Image]:
        """Holt Bild aus Cache oder None."""
        key = (latex, mode, bg_hex, fg_hex, dpi, fontsize)
        return self._cache.get(key)
    
    def put(self, latex: str, mode: str, bg_hex: str, fg_hex: str,
            img: Image.Image, dpi: int = 200, fontsize: int = 5):
        """Speichert Bild im Cache."""
        key = (latex, mode, bg_hex, fg_hex, dpi, fontsize)
        self._cache[key] = img
    
    def clear(self):
        """Leert den Cache."""
        self._cache.clear()
    
    def __len__(self):
        return len(self._cache)
