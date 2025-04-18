"""Erster Versuch DLT"""
import tkinter as tk
from tkinter import ttk


class eingabemaske:
    def __init__(self, root):
        self.root = root
        self.root.title("Durchlaufträger | Statik-Tool Holzbau")

        self.max_felder = 5

        self.setup_gui()
        self.nkl()

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
        ttk.Checkbutton(frame_eingabe, text="Kragarm links", variable=self.kragarm_links,
                        command=self.update_spannweitenfelder).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(frame_eingabe, text="Kragarm rechts", variable=self.kragarm_rechts,
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

        # --- Lasteneingabe-Feld ---
        self.lasten_frame = ttk.LabelFrame(
            self.root, text="Lasten [kN/m²]", padding=10)
        self.lasten_frame.pack(padx=10, pady=10, fill="x")

        # Beschriftung
        headers = ["", "LF", "q [kN/m²]", "Lastfall", "Kommentar"]
        for i, header in enumerate(headers):
            ttk.Label(self.lasten_frame, text=header).grid(
                row=0, column=i, padx=5)

        self.lasten_eingaben = []
        self.add_lasteneingabe()

    def add_lasteneingabe(self):
        if len(self.lasten_eingaben) >= 5:
            return

        row = len(self.lasten_eingaben) + 1

        # --- Eingabefelder ---
        lf_var = tk.StringVar(value="g")
        lf_combo = ttk.Combobox(self.lasten_frame, textvariable=lf_var, values=[
                                "g", "s", "w", "p"], width=5, state="readonly")
        lf_combo.grid(row=row, column=1, padx=5, pady=2)

        q_entry = ttk.Entry(self.lasten_frame, width=12)
        q_entry.grid(row=row, column=2, padx=5, pady=2)

        lf_detail_var = tk.StringVar()
        lf_detail_combo = ttk.Combobox(
            self.lasten_frame, textvariable=lf_detail_var, width=10, state="readonly")
        lf_detail_combo.grid(row=row, column=3, padx=5, pady=2)

        kommentar_entry = ttk.Entry(self.lasten_frame, width=20)
        kommentar_entry.grid(row=row, column=4, padx=5, pady=2)

        # Lastfall-Details automatisch setzen
        def update_lastfall_options(*args):
            art = lf_var.get()
            if art == "g":
                lf_detail_combo["values"] = ["Eigengewicht"]
                lf_detail_var.set("Eigengewicht")
            elif art == "s":
                lf_detail_combo["values"] = [
                    "Schnee < 1000 m", "Schnee > 1000 m"]
                lf_detail_var.set("Schnee < 1000 m")
            elif art == "w":
                lf_detail_combo["values"] = ["Wind"]
                lf_detail_var.set("Wind")
            elif art == "p":
                lf_detail_combo["values"] = ["Kategorie A", "Kategorie B", "Kategorie C",
                                             "Kategorie D", "Kategorie E", "Kategorie F", "Kategorie G", "Kategorie H"]
                lf_detail_var.set("Kategorie A")

        lf_var.trace_add("write", update_lastfall_options)
        update_lastfall_options()

        # --- Entfernen-Button (nur ab Zeile 2) ---
        remove_button = None

        def remove():
            self.lasten_eingaben.remove(eintrag)
            for widget in eintrag.values():
                if hasattr(widget, "destroy"):
                    widget.destroy()
            self.neu_zeichnen_lasten()
            self.update_plus_button()

        if row > 1:
            remove_button = ttk.Button(
                self.lasten_frame, text="-", width=1, command=remove)
            remove_button.grid(row=row, column=0, padx=2)

        # --- Eintrag speichern ---
        eintrag = {
            "remove": remove_button,
            "lf_combo": lf_combo,
            "wert": q_entry,
            "detail_combo": lf_detail_combo,
            "kommentar": kommentar_entry
        }

        self.lasten_eingaben.append(eintrag)
        self.update_plus_button()

    def update_plus_button(self):
        if hasattr(self, "plus_button"):
            self.plus_button.destroy()

        # Nur anzeigen, wenn weniger als 5 Lasten aktiv sind
        if len(self.lasten_eingaben) < 5:
            row = len(self.lasten_eingaben) + 1
            self.plus_button = ttk.Button(
                self.lasten_frame, text="+", width=1, command=self.add_lasteneingabe
            )
            self.plus_button.grid(row=row, column=0, pady=(2, 0))

        self.nkl()

    def neu_zeichnen_lasten(self):
        for i, eintrag in enumerate(self.lasten_eingaben):
            row = i + 1

            if "remove" in eintrag and eintrag["remove"] and eintrag["remove"].winfo_exists():
                eintrag["remove"].grid(row=row, column=0, padx=2)

            if "lf_combo" in eintrag:
                eintrag["lf_combo"].grid(row=row, column=1, padx=5, pady=2)

            if "wert" in eintrag:
                eintrag["wert"].grid(row=row, column=2, padx=5, pady=2)

            if "detail_combo" in eintrag:
                eintrag["detail_combo"].grid(row=row, column=3, padx=5, pady=2)

            if "kommentar" in eintrag:
                eintrag["kommentar"].grid(row=row, column=4, padx=5, pady=2)

    def nkl(self):  # Nutzungsklasse auswählen
        if hasattr(self, "nkl_label"):  # Vorherige Label entfernen
            self.nkl_label.destroy()
        if hasattr(self, "nkl_dropdown"):
            self.nkl_dropdown.destroy()

        row = len(self.lasten_eingaben) + 2

        self.nkl_label = ttk.Label(self.lasten_frame, text="Nutzungsklasse:")
        self.nkl_label.grid(row=row, column=1, sticky="w", pady=(10, 0))
        self.nkl_var = tk.StringVar(value="NKL 1")
        self.nkl_dropdown = ttk.Combobox(self.lasten_frame, textvariable=self.nkl_var, values=[
            "NKL 1", "NKL 2", "NKL 3"], state="readonly", width=10)
        self.nkl_dropdown.grid(row=row, column=2, pady=(10, 0), sticky="w")

    def update_spannweitenfelder(self):
        for widget in self.spannweiten_frame.winfo_children():
            widget.destroy()

        self.spannweiten_eingaben = []

        col = 0

        if self.kragarm_links.get():
            ttk.Label(self.spannweiten_frame, text="Kragarm L").grid(
                row=0, column=col)
            entry_kragarm_l = ttk.Entry(self.spannweiten_frame, width=7)
            entry_kragarm_l.insert(0, "1.00")
            entry_kragarm_l.grid(row=1, column=col)
            self.spannweiten_eingaben.append(entry_kragarm_l)
            col += 1

        for i in range(self.feldanzahl_var.get()):
            ttk.Label(self.spannweiten_frame,
                      text=f"Feld {i+1}").grid(row=0, column=col)
            entry = ttk.Entry(self.spannweiten_frame, width=7)
            entry.insert(0, "1.00")
            entry.grid(row=1, column=col)
            self.spannweiten_eingaben.append(entry)
            col += 1

        if self.kragarm_rechts.get():
            ttk.Label(self.spannweiten_frame, text="Kragarm R").grid(
                row=0, column=col)
            entry_kragarm_r = ttk.Entry(self.spannweiten_frame, width=7)
            entry_kragarm_r.insert(0, "1.00")
            entry_kragarm_r.grid(row=1, column=col)
            self.spannweiten_eingaben.append(entry_kragarm_r)

    def zeige_system(self):
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
    app = eingabemaske(root)
    root.mainloop()
