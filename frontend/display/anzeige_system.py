import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import logging
import io
from PIL import Image, ImageTk

# Root-Logger-Verhalten
logging.basicConfig(
    level=logging.INFO,                      # ab welcher Wichtigkeit geloggt wird
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S"
)
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.INFO)
logging.getLogger("matplotlib.font_manager").setLevel(logging.INFO)
logger = logging.getLogger(__name__)          # logger für dieses Modul


class SystemAnzeiger:
    def __init__(self, parent_frame, eingabemaske):
        from frontend.gui.theme_config import ThemeManager
        fonts = ThemeManager.get_fonts()

        self.parent = parent_frame
        self.root = eingabemaske.root
        self.eingabemaske = eingabemaske  # Für Zugriff auf max_formula_width

        # Frame System
        self.frame_system = ctk.CTkFrame(self.parent)
        self.frame_system.pack(fill="both", expand=True, padx=10, pady=10)

        # Titel-Label
        ctk.CTkLabel(self.frame_system, text="Statisches System",
                     font=fonts['heading']).pack(pady=5)

        self.system_image_frame = ctk.CTkFrame(self.frame_system)
        self.system_image_frame.pack(
            fill="both", expand=True, padx=10, pady=10)

    def update(self, snapshot, callback=None):
        """Aktualisiert den System-Plot direkt im Haupt-Thread."""
        logger.info("SystemAnzeiger: Update-Anfrage erhalten.")
        try:
            # Datenaufbereitung
            plot_data = self._prepare_plot_data(snapshot)
            # Direkte Zeichnung im Haupt-Thread
            self._draw_system(plot_data, callback)
        except Exception as e:
            logger.error(f"Fehler bei der Plot-Erstellung: {e}")
            self.zeige_fehler(e)

    def _prepare_plot_data(self, snapshot):
        """Bereitet alle notwendigen Koordinaten und Daten für den Plot vor."""
        spannweiten_dict = snapshot["spannweiten"]
        namen = list(spannweiten_dict.keys())
        werte = list(spannweiten_dict.values())

        hat_kragarm_links = "kragarm_links" in namen
        kragarm_links_len = spannweiten_dict.get("kragarm_links", 0)
        hat_kragarm_rechts = "kragarm_rechts" in namen
        kragarm_rechts_len = spannweiten_dict.get("kragarm_rechts", 0)
        felder = [wert for name, wert in zip(
            namen, werte) if name.startswith("feld_")]

        segments = []
        current_pos = 0

        # Linken Kragarm hinzufügen
        if hat_kragarm_links:
            start = -kragarm_links_len
            end = 0
            segments.append({"label": "Kragarm links", "start": start,
                            "end": end, "len": kragarm_links_len})
            current_pos = 0

        # Felder hinzufügen
        for i, feld_len in enumerate(felder):
            start = current_pos
            end = current_pos + feld_len
            segments.append(
                {"label": f"Feld {i+1}", "start": start, "end": end, "len": feld_len})
            current_pos = end

        # Rechten Kragarm hinzufügen
        if hat_kragarm_rechts:
            start = current_pos
            end = current_pos + kragarm_rechts_len
            segments.append({"label": "Kragarm rechts", "start": start,
                            "end": end, "len": kragarm_rechts_len})

        # Auflagerpositionen bestimmen
        auflager_pos = []
        if segments:
            # Das erste Auflager ist am Ende des ersten Segments, wenn es ein Kragarm ist,
            # oder am Anfang, wenn es ein Feld ist.
            if segments[0]['label'] == 'Kragarm links':
                auflager_pos.append(segments[0]['end'])
            else:
                auflager_pos.append(segments[0]['start'])

            # Auflager zwischen den Feldern und am Ende
            for i in range(len(segments)):
                # Ein Auflager existiert am Ende jedes Feldes
                if segments[i]['label'].startswith('Feld'):
                    auflager_pos.append(segments[i]['end'])

        # Duplikate entfernen und sortieren
        auflager_pos = sorted(list(set(auflager_pos)))

        return {
            "segments": segments,
            "auflager_pos": auflager_pos,
            "traeger_start": segments[0]['start'] if segments else 0,
            "traeger_ende": segments[-1]['end'] if segments else 0
        }

    def _draw_system(self, plot_data, callback):
        """Zeichnet das System mit Matplotlib. Läuft im Haupt-Thread."""
        try:
            logger.info("SystemAnzeiger: Zeichnung im Haupt-Thread gestartet.")

            # ALLE Matplotlib-Operationen hier im Haupt-Thread
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt  # Import hierher verlagert

            # WICHTIG: Nutze die TATSÄCHLICHE ttk-Textfarbe!
            from frontend.gui.theme_config import ThemeManager
            from frontend.gui.latex_renderer import tkcolor_to_hex

            style = ttk.Style(self.root)
            fg_ttk = style.lookup('TLabel', 'foreground')
            if fg_ttk:
                text_color = tkcolor_to_hex(self.root, fg_ttk)
            else:
                # Fallback: System-Farbe
                text_color = '#000000' if ThemeManager._current_mode == 'light' else '#E0E0E0'

            # Entpacke die vorbereiteten Daten
            segments = plot_data["segments"]
            auflager_pos = plot_data["auflager_pos"]
            traeger_start = plot_data["traeger_start"]
            traeger_ende = plot_data["traeger_ende"]

            # FESTE Bildbreite für System-Darstellung!
            # System soll NICHT von Formelbreite abhängen, sonst wird Träger bei jeder Berechnung schmaler
            FIXED_SYSTEM_WIDTH = 800  # Feste Breite in Pixel
            fig_width_inches = FIXED_SYSTEM_WIDTH / 100.0  # 8 inches bei 100 DPI

            # Höhe ebenfalls kompakt halten
            fig_height_inches = 2.0

            fig, ax = plt.subplots(
                figsize=(fig_width_inches, fig_height_inches))
            fig.patch.set_visible(False)  # Transparenter Hintergrund

            # Normalisierung: Trägerlänge auf feste Darstellungslänge mappen
            DISPLAY_LENGTH = 10.0  # Feste Darstellungslänge
            traeger_laenge_real = traeger_ende - traeger_start

            if traeger_laenge_real > 0:
                # Normalisierungsfaktor: real -> display
                norm_factor = DISPLAY_LENGTH / traeger_laenge_real

                # Normalisiere alle Positionen
                traeger_start_norm = 0.0
                traeger_ende_norm = DISPLAY_LENGTH
                auflager_pos_norm = [(x - traeger_start)
                                     * norm_factor for x in auflager_pos]

                # Normalisiere Segment-Positionen
                segments_norm = []
                for seg in segments:
                    segments_norm.append({
                        'label': seg['label'],
                        'start': (seg['start'] - traeger_start) * norm_factor,
                        'end': (seg['end'] - traeger_start) * norm_factor,
                        # Reale Länge für Beschriftung beibehalten
                        'len': seg['len']
                    })
            else:
                # Fallback bei leerem System
                traeger_start_norm = 0.0
                traeger_ende_norm = DISPLAY_LENGTH
                auflager_pos_norm = []
                segments_norm = []

            # Trägerlinie zeichnen (immer gleich lang) - mit Theme-Farbe
            ax.plot([traeger_start_norm, traeger_ende_norm],
                    [1, 1], color=text_color, linewidth=2)

            # Auflagergrößen - KLEINER gemacht
            dreieck_breite = 0.15  # Kleiner: 0.15 statt 0.2
            dreieck_hoehe = 0.75  # Kleiner: bis y=0.75 statt 0.6
            festlager_breite = 0.25  # Kleiner: 0.25 statt 0.3
            loslager_breite = 0.2  # Kleiner: 0.2 statt 0.25

            # Auflager zeichnen (an normalisierten Positionen) - mit Theme-Farbe
            for i, x_norm in enumerate(auflager_pos_norm):
                is_fixed = (i == 0 and not any(
                    seg['label'] == 'Kragarm links' for seg in segments))

                # Dreieck - KLEINER (Spitze auf Träger bei y=1.0, Basis bei y=0.75)
                ax.plot([x_norm, x_norm-dreieck_breite, x_norm+dreieck_breite, x_norm],
                        [1.0, dreieck_hoehe, dreieck_hoehe, 1.0],
                        color=text_color, linewidth=1.5)

                if is_fixed:
                    # Festlager: Linie DIREKT auf Dreieckbasis (y=0.75)
                    ax.plot([x_norm-festlager_breite, x_norm+festlager_breite],
                            [dreieck_hoehe, dreieck_hoehe],
                            color=text_color, linewidth=1.5)
                else:
                    # Loslager: Linie etwas UNTER der Dreieckbasis (y=0.65)
                    ax.plot([x_norm-loslager_breite, x_norm+loslager_breite],
                            [dreieck_hoehe - 0.1, dreieck_hoehe - 0.1],
                            color=text_color, linewidth=1.5)

                # Lagerbuchstaben UNTER den Auflagern (y=0.55)
                ax.text(x_norm, 0.55, chr(65+i), ha='center',
                        va='top', fontsize=12, color=text_color)

            # Bemaßung für jedes Segment - UNTER den Lagerbuchstaben
            label_pos_high = False  # Flag für alternierende Position
            for seg in segments_norm:
                x1_norm, x2_norm = seg['start'], seg['end']
                # Bemaßungspfeil TIEFER bei y=0.15 (mehr Abstand zu Lagerbuchstaben)
                ax.annotate('', xy=(x1_norm, 0.15), xytext=(x2_norm, 0.15), arrowprops=dict(
                    arrowstyle='<->', lw=1.2, color=text_color))

                # Bemaßungstext bei y=0.05 - mit realer Länge
                ax.text(
                    (x1_norm+x2_norm)/2, 0.05, f"{seg['len']:.2f} m", ha='center', va='top', fontsize=11, color=text_color)

                # Logik für Beschriftungsposition - HÖHER gesetzt
                y_pos = 1.15  # Standard-Position über dem Balken (höher!)

                # Bei kleinen Feldern Position alternieren, um Überlappung zu vermeiden
                if 'Feld' in seg['label'] and seg['len'] < 2.5:
                    if label_pos_high:
                        y_pos = 1.4  # Höhere Position (höher!)
                    label_pos_high = not label_pos_high
                else:
                    # Bei großen Feldern oder Kragarmen, den Alternator zurücksetzen
                    label_pos_high = False

                # Beschriftung (z.B. "Feld 1") an der berechneten Position zeichnen
                # Kragarme werden nicht beschriftet
                if 'Kragarm' not in seg['label']:
                    ax.text((x1_norm+x2_norm)/2, y_pos,
                            seg['label'], ha='center', va='bottom', fontsize=10, color=text_color)

            ax.axis('off')
            ax.set_aspect('equal')

            # Feste xlim (da Bildbreite jetzt auch fest ist)
            ax.set_xlim(traeger_start_norm - 0.3, traeger_ende_norm + 0.3)
            # ylim ENGER für gleichmäßige Abstände oben und unten
            ax.set_ylim(-0.05, 1.5)  # Von -0.05 bis 1.5 statt 0 bis 1.8

            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight',
                        dpi=1000, transparent=True)  # Transparent, höhere Auflösung
            plt.close(fig)  # Wichtig: Figur schließen, um Speicher freizugeben
            buf.seek(0)

            # Tkinter-Bild erstellen und auf passende Größe skalieren
            img = Image.open(buf)

            # Bild mit globalem Skalierungsfaktor verkleinern (gekoppelt an UI_SCALE)
            system_scale = ThemeManager.get_system_scale()
            w, h = img.size
            new_size = (int(w * system_scale),
                        int(h * system_scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

            photo = ImageTk.PhotoImage(img)

            # Bestehende Widgets im Frame entfernen
            for widget in self.system_image_frame.winfo_children():
                widget.destroy()

            # CustomTkinter-Label ohne bg-Argument verwenden
            label = ctk.CTkLabel(self.system_image_frame, text="", image=photo)
            # WICHTIG: Referenz auf das Bild speichern, um Garbage Collection zu verhindern!
            label.image = photo
            self.tk_img = photo  # Zusätzliche Referenz in der Klasse
            label.pack()

            if callback:
                callback()

        except Exception as e:
            logger.error(f"Fehler beim Zeichnen des System-Plots: {e}")
            self.zeige_fehler(e)

    def zeige_fehler(self, e):
        # Bestehende Widgets im Frame entfernen
        for widget in self.system_image_frame.winfo_children():
            widget.destroy()
        label = tk.Label(self.system_image_frame,
                         text=f"⚠️ Fehler: {e}")
        label.pack()
