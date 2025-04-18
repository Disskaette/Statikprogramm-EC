"""Erster Versuch DLT"""
import tkinter as tk
from tkinter import ttk


class statik_dlt:
    def __init__(self, root):
        self.root = root
        self.root.title("Durchlaufträger | Statik-Tool Holzbau")

        self.max_felder = 5

        self.setup_gui()

    def setup_gui(self):
        # --- Eingabeframe ---
        frame_eingabe = ttk.LabelFrame(
            self.root, text="Systemeingabe", padding=10)
        frame_eingabe.pack(padx=10, pady=10, fill="x")
        # Anzahl Felder
        ttk.Label(frame_eingabe, text="Anzahl Felder (1-5):").grid(row=0,
                                                                   column=0, sticky="w")
        self.feldanzahl_var = tk.IntVar(value=2)
        spinbox = ttk.Spinbox(frame_eingabe, from_=1, to=self.max_felder,
                              textvariable=self.feldanzahl_var, width=5, command=self.update_spannweitenfelder)
        spinbox.grid(row=0, column=1, padx=5)

        # Kragarm links/rechts
        self.kragarm_links = tk.BooleanVar()
        self.kragarm_rechts = tk.BooleanVar()
        ttk.Checkbutton(frame_eingabe, text="Kragarm links",
                        variable=self.kragarm_links,
                        command=self.update_spannweitenfelder).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(frame_eingabe, text="Kragarm rechts",
                        variable=self.kragarm_rechts,
                        command=self.update_spannweitenfelder).grid(row=1, column=1, sticky="w")

        # Spannweiten-Felder
        self.spannweiten_frame = ttk.LabelFrame(
            self.root, text="Spannweiten je Feld [m]", padding=10)
        self.spannweiten_frame.pack(padx=10, pady=10, fill="x")
        self.spannweiten_eingaben = []
        self.update_spannweitenfelder()

        # Button
        ttk.Button(self.root, text="System anzeigen",
                   command=self.zeige_system).pack(pady=10)

    def update_spannweitenfelder(self):
        for widget in self.spannweiten_frame.winfo_children():
            widget.destroy()

        self.spannweiten_eingaben = []

        col = 0
        # Kragarm links
        if self.kragarm_links.get():
            ttk.Label(self.spannweiten_frame, text="Kragarm L").grid(
                row=0, column=col)
            entry_kragarm_l = ttk.Entry(self.spannweiten_frame, width=7)
            entry_kragarm_l.insert(0, "1.00")
            entry_kragarm_l.grid(row=1, column=col)
            self.spannweiten_eingaben.append(entry_kragarm_l)
            col += 1  # alle folgenden Felder starten ab Spalte 1

        # Normale Felder
        for i in range(self.feldanzahl_var.get()):
            ttk.Label(self.spannweiten_frame,
                      text=f"Feld {i+1}").grid(row=0, column=col)
            entry = ttk.Entry(self.spannweiten_frame, width=7)
            entry.insert(0, "1.00")
            entry.grid(row=1, column=col)
            self.spannweiten_eingaben.append(entry)
            col += 1

        # Kragarm rechts
        if self.kragarm_rechts.get():
            ttk.Label(self.spannweiten_frame, text="Kragarm R").grid(
                row=0, column=col)
            entry_kragarm_r = ttk.Entry(self.spannweiten_frame, width=7)
            entry_kragarm_r.insert(0, "1.00")
            entry_kragarm_r.grid(row=1, column=col)
            self.spannweiten_eingaben.append(entry_kragarm_r)

    def zeige_system(self):
        # Hier könnte später die Systemgrafik oder die Struktur-Logik eingebaut werden
        spannweiten = []
        try:
            for entry in self.spannweiten_eingaben:
                spannweiten.append(float(entry.get().replace(",", ".")))
        except ValueError:
            print("Ungültige Eingabe bei Spannweite")
            return

        print("Systemdaten:")
        print(f"  Felder: {len(spannweiten)}")
        print(f"  Spannweiten: {spannweiten}")
        print(f"  Kragarm links: {self.kragarm_links.get()}")
        print(f"  Kragarm rechts: {self.kragarm_rechts.get()}")


if __name__ == '__main__':
    root = tk.Tk()
    app = statik_dlt(root)
    root.mainloop()
