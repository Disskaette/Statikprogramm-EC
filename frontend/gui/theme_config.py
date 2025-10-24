"""
Theme-Konfiguration für einheitliches Design.
Definiert Farben und Styles für die gesamte Anwendung.
Unterstützt Light und Dark Mode.
"""

from tkinter import ttk
import logging
import subprocess
import platform

logger = logging.getLogger(__name__)


class ThemeManager:
    """Verwaltet das visuelle Theme der Anwendung mit Dark Mode Support"""

    # Flag für aktuelles Theme
    _current_mode = 'light'
    _registered_roots = []  # Alle Root-Fenster für Theme-Updates

    # Light Mode Farbpalette
    COLORS_LIGHT = {
        # Hauptfarben
        'bg_main': '#FFFFFF',          # Weiß (Haupthintergrund)
        'bg_secondary': '#F5F5F5',     # Hellgrau (Panels, Frames)
        'bg_input': '#FFFFFF',          # Weiß (Eingabefelder)
        'bg_hover': '#E8F4F8',         # Helles Blau (Hover)
        'bg_selected': '#D1E7F3',      # Mittleres Blau (Selected)

        # Rahmen und Linien
        'border': '#D0D0D0',           # Helles Grau (Rahmen)
        'border_light': '#E5E5E5',     # Sehr helles Grau (dezente Trenner)

        # Text
        'text_main': '#2C3E50',        # Dunkelgrau (Haupttext)
        'text_secondary': '#7F8C8D',   # Mittelgrau (Sekundärtext)
        'text_disabled': '#BDC3C7',    # Hellgrau (Disabled)

        # Akzentfarben
        'accent_blue': '#3498DB',      # Blau (Links, Buttons)
        'accent_green': '#27AE60',     # Grün (Erfolg)
        'accent_orange': '#E67E22',    # Orange (Warnung)
        'accent_red': '#E74C3C',       # Rot (Fehler)
    }

    # Dark Mode Farbpalette
    COLORS_DARK = {
        # Hauptfarben
        'bg_main': '#1E1E1E',          # Dunkelgrau (Haupthintergrund)
        'bg_secondary': '#2D2D2D',     # Mitteldunkel (Panels, Frames)
        'bg_input': '#3C3C3C',         # Helleres Dunkel (Eingabefelder)
        'bg_hover': '#404040',         # Hover-Effekt
        'bg_selected': '#4A4A4A',      # Selected-Effekt

        # Rahmen und Linien
        'border': '#555555',           # Mittelgrau (Rahmen)
        'border_light': '#3C3C3C',     # Dunkler (dezente Trenner)

        # Text
        'text_main': '#E0E0E0',        # Hellgrau (Haupttext)
        'text_secondary': '#B0B0B0',   # Mittelgrau (Sekundärtext)
        'text_disabled': '#707070',    # Dunkelgrau (Disabled)

        # Akzentfarben
        'accent_blue': '#64B5F6',      # Hellblau (Links, Buttons)
        'accent_green': '#81C784',     # Hellgrün (Erfolg)
        'accent_orange': '#FFB74D',    # Hellorange (Warnung)
        'accent_red': '#E57373',       # Hellrot (Fehler)
    }

    # Aktuelle Farben (wird bei Theme-Wechsel aktualisiert)
    COLORS = COLORS_LIGHT.copy()

    @classmethod
    def detect_system_theme(cls):
        """
        Erkennt das System-Theme (Light/Dark Mode).

        Returns:
            str: 'light' oder 'dark'
        """
        if platform.system() == 'Darwin':  # macOS
            try:
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                    capture_output=True,
                    text=True
                )
                # Wenn "Dark" zurückkommt → Dark Mode
                if result.returncode == 0 and 'Dark' in result.stdout:
                    return 'dark'
            except:
                pass

        # Default: Light Mode
        return 'light'

    @classmethod
    def set_mode(cls, mode):
        """
        Setzt den Theme-Modus (light/dark) und aktualisiert alle Fenster.

        Args:
            mode: str - 'light' oder 'dark'
        """
        cls._current_mode = mode

        # Farben aktualisieren
        if mode == 'dark':
            cls.COLORS = cls.COLORS_DARK.copy()
        else:
            cls.COLORS = cls.COLORS_LIGHT.copy()

        # Alle registrierten Root-Fenster aktualisieren
        for root in cls._registered_roots:
            try:
                cls.apply_theme(root, register=False)
            except:
                logger.warning(f"Konnte Theme nicht für Fenster aktualisieren")

    @classmethod
    def toggle_mode(cls):
        """
        Wechselt zwischen Light und Dark Mode.
        """
        new_mode = 'dark' if cls._current_mode == 'light' else 'light'
        cls.set_mode(new_mode)

    @classmethod
    def get_current_mode(cls):
        """
        Gibt den aktuellen Theme-Modus zurück.

        Returns:
            str: 'light' oder 'dark'
        """
        return cls._current_mode

    @classmethod
    def apply_theme(cls, root, register=True, auto_detect=True):
        """
        Wendet das Theme auf die gesamte Anwendung an.

        Args:
            root: tk.Tk Root-Fenster
            register: bool - Fenster registrieren für Theme-Updates
            auto_detect: bool - System-Theme automatisch erkennen
        """
        # Root registrieren für spätere Updates
        if register and root not in cls._registered_roots:
            cls._registered_roots.append(root)

        # System-Theme erkennen (beim ersten Aufruf)
        if auto_detect and register:
            system_theme = cls.detect_system_theme()
            cls.set_mode(system_theme)
            logger.info(f"System-Theme erkannt: {system_theme}")

        style = ttk.Style(root)

        # Nutze aqua-Theme (folgt automatisch macOS System-Theme)
        # aqua passt sich automatisch an Dark Mode an
        if platform.system() == 'Darwin':  # macOS
            try:
                style.theme_use('aqua')
                logger.info(
                    "aqua-Theme geladen (folgt System-Theme automatisch)")
            except:
                style.theme_use('default')
        else:
            try:
                style.theme_use('clam')
            except:
                logger.warning("Theme nicht verfügbar, nutze Standard")
                style.theme_use('default')

        # KEINE Root-Hintergrund-Konfiguration → aqua folgt System automatisch
        # root.configure(bg=cls.COLORS['bg_main'])  # NICHT SETZEN!

        # ========== Frame Styles ==========
        # KEINE Background-Farben setzen → aqua passt sich automatisch an
        # style.configure('TFrame', background=cls.COLORS['bg_main'])  # NICHT SETZEN!

        style.configure('Card.TFrame',
                        relief='flat',
                        borderwidth=1)

        # ========== Label Styles ==========
        # NUR FONTS - aqua folgt automatisch System-Theme
        style.configure('TLabel', font=('', 10))

        style.configure('Header.TLabel', font=('', 12, 'bold'))

        style.configure('Secondary.TLabel', font=('', 10))

        # ========== Button Styles ==========
        # Nur minimale Anpassungen - natives Aussehen beibehalten
        # (Keine Überschreibung - macOS Buttons sehen nativ besser aus)

        # ========== Entry/Combobox/Notebook/TreeView etc. ==========
        # KEINE Styles setzen - aqua folgt automatisch macOS System-Theme!
        # Das native Theme passt sich automatisch an Light/Dark Mode an

        # NUR Font-Größen setzen (keine Farben!)
        style.configure('TNotebook.Tab', padding=(15, 8))
        style.configure('TLabelframe.Label', font=('', 10, 'bold'))

        logger.info("Theme erfolgreich angewendet")

    @classmethod
    def get_color(cls, key: str) -> str:
        """
        Gibt eine Farbe aus der Palette zurück.

        Args:
            key: Farb-Schlüssel (z.B. 'bg_main', 'accent_blue')

        Returns:
            Hex-Farbcode
        """
        return cls.COLORS.get(key, '#FFFFFF')

    @classmethod
    def configure_matplotlib(cls):
        """
        Konfiguriert Matplotlib für das aktuelle Theme (Light/Dark Mode).
        Muss NACH import matplotlib aufgerufen werden.
        """
        try:
            import matplotlib.pyplot as plt

            if cls._current_mode == 'dark':
                # Dark Mode für Matplotlib
                plt.style.use('dark_background')
                # Zusätzliche Anpassungen
                plt.rcParams.update({
                    'figure.facecolor': cls.COLORS['bg_main'],
                    'axes.facecolor': cls.COLORS['bg_secondary'],
                    'axes.edgecolor': cls.COLORS['border'],
                    'axes.labelcolor': cls.COLORS['text_main'],
                    'text.color': cls.COLORS['text_main'],
                    'xtick.color': cls.COLORS['text_main'],
                    'ytick.color': cls.COLORS['text_main'],
                    'grid.color': cls.COLORS['border'],
                    'legend.facecolor': cls.COLORS['bg_secondary'],
                    'legend.edgecolor': cls.COLORS['border']
                })
            else:
                # Light Mode für Matplotlib
                plt.style.use('default')
                # Zusätzliche Anpassungen
                plt.rcParams.update({
                    'figure.facecolor': cls.COLORS['bg_main'],
                    'axes.facecolor': cls.COLORS['bg_main'],
                    'axes.edgecolor': cls.COLORS['border'],
                    'axes.labelcolor': cls.COLORS['text_main'],
                    'text.color': cls.COLORS['text_main'],
                    'xtick.color': cls.COLORS['text_main'],
                    'ytick.color': cls.COLORS['text_main'],
                    'grid.color': cls.COLORS['border_light'],
                    'legend.facecolor': 'white',
                    'legend.edgecolor': cls.COLORS['border']
                })

            logger.info(
                f"Matplotlib für {cls._current_mode} mode konfiguriert")
        except Exception as e:
            logger.warning(f"Konnte Matplotlib nicht konfigurieren: {e}")
