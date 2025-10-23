import tkinter as tk
import logging
import io
from PIL import Image, ImageTk
from tkinter import ttk

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
        self.eingabemaske = eingabemaske
        self.parent = parent_frame
        self.tk_img = None  # Referenz halten

        # Frame für System
        self.frame_system = ttk.LabelFrame(
            self.parent, text="Statisches System", padding=10)
        self.frame_system.pack(fill="both", expand=True, padx=10, pady=10)

        self.system_image_frame = ttk.Frame(self.frame_system)
        self.system_image_frame.pack(fill="both", expand=True)

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

            # Entpacke die vorbereiteten Daten
            segments = plot_data["segments"]
            auflager_pos = plot_data["auflager_pos"]
            traeger_start = plot_data["traeger_start"]
            traeger_ende = plot_data["traeger_ende"]

            fig, ax = plt.subplots(figsize=(8, 2))
            
            # Normalisierung: Trägerlänge auf feste Darstellungslänge mappen
            DISPLAY_LENGTH = 10.0  # Feste Darstellungslänge
            traeger_laenge_real = traeger_ende - traeger_start
            
            if traeger_laenge_real > 0:
                # Normalisierungsfaktor: real -> display
                norm_factor = DISPLAY_LENGTH / traeger_laenge_real
                
                # Normalisiere alle Positionen
                traeger_start_norm = 0.0
                traeger_ende_norm = DISPLAY_LENGTH
                auflager_pos_norm = [(x - traeger_start) * norm_factor for x in auflager_pos]
                
                # Normalisiere Segment-Positionen
                segments_norm = []
                for seg in segments:
                    segments_norm.append({
                        'label': seg['label'],
                        'start': (seg['start'] - traeger_start) * norm_factor,
                        'end': (seg['end'] - traeger_start) * norm_factor,
                        'len': seg['len']  # Reale Länge für Beschriftung beibehalten
                    })
            else:
                # Fallback bei leerem System
                traeger_start_norm = 0.0
                traeger_ende_norm = DISPLAY_LENGTH
                auflager_pos_norm = []
                segments_norm = []
            
            # Trägerlinie zeichnen (immer gleich lang)
            ax.plot([traeger_start_norm, traeger_ende_norm], [1, 1], color='black', linewidth=2)

            # Feste Auflagergrößen (nicht skaliert)
            dreieck_breite = 0.2
            festlager_breite = 0.3
            loslager_breite = 0.25
            
            # Auflager zeichnen (an normalisierten Positionen)
            for i, x_norm in enumerate(auflager_pos_norm):
                is_fixed = (i == 0 and not any(
                    seg['label'] == 'Kragarm links' for seg in segments))

                # Dreieck (Spitze jetzt exakt auf dem Träger)
                ax.plot([x_norm, x_norm-dreieck_breite, x_norm+dreieck_breite, x_norm], [1.0, 0.6, 0.6, 1.0],
                        color='black', linewidth=1.5)
                ax.text(x_norm, 1.08, chr(65+i), ha='center',
                        va='bottom', fontsize=12)

                if is_fixed:
                    # Festlager: Linie auf gleicher Höhe wie Dreieckbasis, länger
                    ax.plot([x_norm-festlager_breite, x_norm+festlager_breite], [0.6, 0.6],
                            color='black', linewidth=1.5)
                else:
                    # Loslager: Längere Linie mit Abstand unter dem Dreieck
                    ax.plot([x_norm-loslager_breite, x_norm+loslager_breite], [0.5, 0.5],
                            color='black', linewidth=1.5)

            # Bemaßung und Beschriftung für jedes Segment (mit normalisierten Koordinaten)
            label_pos_high = False  # Flag für alternierende Position
            for seg in segments_norm:
                x1_norm, x2_norm = seg['start'], seg['end']
                # Bemaßungspfeil (tiefer gesetzt)
                ax.annotate('', xy=(x1_norm, 0.2), xytext=(x2_norm, 0.2), arrowprops=dict(
                    arrowstyle='<->', lw=1.2, color='black'))

                # Bemaßungstext (ganz unten) - mit realer Länge
                ax.text(
                    (x1_norm+x2_norm)/2, 0.1, f"{seg['len']:.2f} m", ha='center', va='top', fontsize=11)

                # Logik für Beschriftungsposition
                y_pos = 1.05  # Standard-Position über dem Balken

                # Bei kleinen Feldern Position alternieren, um Überlappung zu vermeiden
                if 'Feld' in seg['label'] and seg['len'] < 2.5:
                    if label_pos_high:
                        y_pos = 1.3  # Höhere Position
                    label_pos_high = not label_pos_high
                else:
                    # Bei großen Feldern oder Kragarmen, den Alternator zurücksetzen
                    label_pos_high = False

                # Beschriftung (z.B. "Feld 1") an der berechneten Position zeichnen
                # Kragarme werden nicht beschriftet
                if 'Kragarm' not in seg['label']:
                    ax.text((x1_norm+x2_norm)/2, y_pos,
                            seg['label'], ha='center', va='bottom', fontsize=10)

            ax.axis('off')
            ax.set_aspect('equal')
            ax.set_xlim(traeger_start_norm - 0.5, traeger_ende_norm + 0.5)
            ax.set_ylim(0, 1.8)  # Y-Limit erhöht für mehr Platz

            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            plt.close(fig)  # Wichtig: Figur schließen, um Speicher freizugeben
            buf.seek(0)

            # Tkinter-Bild erstellen und im Label anzeigen
            img = Image.open(buf)
            photo = ImageTk.PhotoImage(img)

            # Bestehende Widgets im Frame entfernen
            for widget in self.system_image_frame.winfo_children():
                widget.destroy()

            label = ttk.Label(self.system_image_frame, image=photo)
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
        label = ttk.Label(self.system_image_frame,
                          text=f"⚠️ Fehler: {e}")
        label.pack()
