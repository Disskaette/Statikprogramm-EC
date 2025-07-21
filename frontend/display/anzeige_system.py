import tkinter as tk
import threading
import matplotlib.pyplot as plt
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
        self.snapshot = snapshot
        self.frame_system.update_idletasks()
        # Korrekter Aufruf mit lambda auf einem Widget
        self.frame_system.after(100, lambda: self.threaded_update(callback))

    def threaded_update(self, callback):
        try:
            logger.info("SystemAnzeiger: Update gestartet")
            spannweiten_dict = self.snapshot["spannweiten"]
            namen = list(spannweiten_dict.keys())
            werte = list(spannweiten_dict.values())
            hat_kragarm_links = "kragarm_links" in namen
            hat_kragarm_rechts = "kragarm_rechts" in namen
            felder = [wert for name, wert in zip(
                namen, werte) if name.startswith("feld_")]
            kragarm_links = spannweiten_dict.get("kragarm_links", 0)
            kragarm_rechts = spannweiten_dict.get("kragarm_rechts", 0)
            pos = [0]
            if hat_kragarm_links:
                pos[0] = -kragarm_links
            for feld in felder:
                pos.append(pos[-1] + feld)
            auflager_pos = pos.copy()
            if hat_kragarm_links:
                auflager_pos = pos[1:]
            if hat_kragarm_rechts:
                auflager_pos = auflager_pos[:-1]
            fig, ax = plt.subplots(figsize=(8, 2))
            traeger_start = pos[0]
            traeger_ende = pos[-1]
            ax.plot([traeger_start, traeger_ende], [
                    1, 1], color='black', linewidth=2)
            for i, x in enumerate(auflager_pos):
                if i == 0:
                    ax.plot([x, x-0.18, x+0.18, x], [1, 0.7, 0.7, 1],
                            color='black', linewidth=2)
                    ax.plot([x-0.18, x+0.18], [0.7, 0.7],
                            color='black', linewidth=4)
                else:
                    ax.plot([x, x-0.18, x+0.18, x], [1, 0.7, 0.7, 1],
                            color='black', linewidth=2)
                ax.text(x, 1.13, chr(65+i), ha='center',
                        va='bottom', fontsize=12)
            for i in range(len(auflager_pos)-1):
                x1 = auflager_pos[i]
                x2 = auflager_pos[i+1]
                ax.annotate(
                    '', xy=(x1, 0.5), xytext=(x2, 0.5),
                    arrowprops=dict(arrowstyle='<->',
                                    lw=1.2, color='black')
                )
                spannweite = x2 - x1
                ax.text((x1+x2)/2, 0.4, f"{spannweite:.2f} m",
                        ha='center', va='top', fontsize=11)
            ax.axis('off')
            ax.set_aspect('equal')
            ax.set_xlim(traeger_start-1, traeger_ende+1)
            ax.set_ylim(0, 1.3)
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            plt.close(fig)
            buf.seek(0)
            img = Image.open(buf)
            # Das Pillow-Bild UND den Buffer an den Haupt-Thread übergeben
            self.parent.after(0, lambda: self.zeige_bilder(
                img, buf, callback=callback))

        except Exception as e:
            self.parent.after(0, lambda err=e: self.zeige_fehler(err))

    def zeige_bilder(self, img, buf, callback=None):
        for widget in self.system_image_frame.winfo_children():
            widget.destroy()

        # Das Tkinter-Bild wird jetzt hier im Haupt-Thread erstellt
        self.tk_img = ImageTk.PhotoImage(img)
        buf.close()  # Den Buffer erst hier schließen, nachdem das Bild erstellt wurde

        label = tk.Label(self.system_image_frame,
                         image=self.tk_img
                         )
        label.image = self.tk_img  # Referenz speichern!
        label.pack(anchor="w", pady=5)
        if callback:
            self.system_image_frame.after(10, callback)

    def zeige_fehler(self, e):
        for widget in self.system_image_frame.winfo_children():
            widget.destroy()
        label = ttk.Label(self.system_image_frame,
                          text=f"⚠️ Fehler: {e}")
        label.pack()
