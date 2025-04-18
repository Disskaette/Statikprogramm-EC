import tkinter as tk
from tkinter import ttk


class Eingabemaske:
    def __init__(self, root):
        self.root = root
        self.root.title("Durchlaufträger | Statik-Tool Holzbau")

        self.max_felder = 5
        self.feldanzahl_var = None

        # Kragarme
        self.kragarm_links = None
        self.kragarm_rechts = None
        # Spannweiten-Felder
        self.spannweiten_frame = None
        self.spannweiten_eingaben = None
        # Lasteneingabe
        self.lasten_eingaben = None
        self.lasten_frame = None
        # Plus Button
        self.plus_button = None
        # Self NKL
        self.nkl_label = None
        self.nkl_dropdown = None
        self.nkl_var = None
        # Schnittgrößen
        self.myd_entry = None
        self.vzd_entry = None
        self.kaltfall_entry = None
        self.rundung_var = None
        # Querschnitt
        self.querschnitt_var = None
        self.querschnitt_frame = None
        self.b_entry = None
        self.h_entry = None
        self.bsp_schichten = None
        self.bsp_emodul = None
        self.gamma_m_entry = None
        # Gebrauchstauglichkeit
        self.w_inst = None
        self.w_fin = None
        self.w_be = None
        self.situation_var = None

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
                              textvariable=self.feldanzahl_var, width=5,
                              command=self.update_spannweitenfelder)
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

        # --- Lasteneingabe-Feld ---
        self.lasten_frame = ttk.LabelFrame(
            self.root, text="Lasten [kN/m²]", padding=10)
        self.lasten_frame.pack(padx=10, pady=10, fill="x")

        headers = ["", "LF", "q [kN/m²]", "Lastfall", "Kommentar"]
        for i, header in enumerate(headers):
            ttk.Label(self.lasten_frame, text=header).grid(
                row=0, column=i, padx=5)

        self.lasten_eingaben = []
        self.add_lasteneingabe()
        self.schnittgroessen_eingabe()
        self.querschnitt_eingabe()
        self.gebrauchstauglichkeit_eingabe()

    def add_lasteneingabe(self):
        if len(self.lasten_eingaben) >= 5:
            return

        row = len(self.lasten_eingaben) + 1

        # --- Eingabefelder ---
        lf_var = tk.StringVar(value="g")
        lf_combo = ttk.Combobox(self.lasten_frame, textvariable=lf_var, values=[
                                "g", "s", "w", "p"], width=5, state="readonly")
        lf_combo.grid(row=row, column=1, padx=5, pady=2)

        q_entry = ttk.Entry(self.lasten_frame, width=6)
        q_entry.grid(row=row, column=2, padx=0, pady=2)

        lf_detail_var = tk.StringVar()
        lf_detail_combo = ttk.Combobox(
            self.lasten_frame, textvariable=lf_detail_var, width=10, state="readonly")
        lf_detail_combo.grid(row=row, column=3, padx=5, pady=2)

        kommentar_entry = ttk.Entry(self.lasten_frame, width=20)
        kommentar_entry.grid(row=row, column=4, padx=5, pady=2)

        # Lastfall-Details automatisch setzen (Dropdown aktualisieren bei Änderung)
        lf_var.trace_add(
            "write",
            lambda *args: self.update_lastfall_options(
                lf_var, lf_detail_combo, lf_detail_var)
        )

        self.update_lastfall_options(lf_var, lf_detail_combo, lf_detail_var)

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

    def neu_zeichnen_lasten(self):
        # Lastenzeilen korrekt neu anordnen
        for i, eintrag in enumerate(self.lasten_eingaben):
            row = i + 1
            if "remove" in eintrag and eintrag["remove"]:
                eintrag["remove"].grid(row=row, column=0, padx=2)
            if "lf_combo" in eintrag:
                eintrag["lf_combo"].grid(row=row, column=1, padx=5, pady=2)
            if "wert" in eintrag:
                eintrag["wert"].grid(row=row, column=2, padx=5, pady=2)
            if "detail_combo" in eintrag:
                eintrag["detail_combo"].grid(row=row, column=3, padx=5, pady=2)
            if "kommentar" in eintrag:
                eintrag["kommentar"].grid(row=row, column=4, padx=5, pady=2)

        # Plus-Button an die neue letzte Zeile anhängen
        self.update_plus_button()

    def update_lastfall_options(self, lf_var, detail_combo, detail_var):
        art = lf_var.get()
        if art == "g":
            detail_combo["values"] = ["Eigengewicht"]
            detail_var.set("Eigengewicht")
        elif art == "s":
            detail_combo["values"] = ["Schnee < 1000 m", "Schnee > 1000 m"]
            detail_var.set("Schnee < 1000 m")
        elif art == "w":
            detail_combo["values"] = ["Wind"]
            detail_var.set("Wind")
        elif art == "p":
            detail_combo["values"] = [f"Kategorie {c}" for c in "ABCDEFGH"]
            detail_var.set("Kategorie A")

    def update_plus_button(self, row=None):
        if self.plus_button is not None:
            self.plus_button.destroy()
        self.plus_button = None

        if row is None:
            row = len(self.lasten_eingaben) + 1

        if len(self.lasten_eingaben) < 5:
            self.plus_button = ttk.Button(
                self.lasten_frame, text="+", width=1, command=self.add_lasteneingabe)
            self.plus_button.grid(row=row, column=0, pady=(2, 0))

        self.nkl(row + 1)
        # self.schnittgroessen_eingabe(row + 2)
        # self.querschnitt_eingabe(row + 9)
        # self.gebrauchstauglichkeit_eingabe(row + 20)

    def nkl(self, row=None):
        if self.nkl_label is not None:
            self.nkl_label.destroy()
        if self.nkl_dropdown is not None:
            self.nkl_dropdown.destroy()

        if row is None:
            row = len(self.lasten_eingaben) + 2

        self.nkl_label = ttk.Label(self.lasten_frame, text="Nutzungsklasse:")
        self.nkl_label.grid(row=row, column=1, sticky="w", pady=(10, 0))
        self.nkl_var = tk.StringVar(value="NKL 1")
        self.nkl_dropdown = ttk.Combobox(self.lasten_frame, textvariable=self.nkl_var,
                                         values=["NKL 1", "NKL 2", "NKL 3"], state="readonly", width=5)
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

    # def zeige_system(self):
    #     spannweiten = []
    #     try:
    #         for entry in self.spannweiten_eingaben:
    #             spannweiten.append(float(entry.get().replace(",", ".")))
    #     except ValueError:
    #         print("Ungültige Eingabe bei Spannweite")
    #         return

    #     print("Systemdaten:")
    #     print(f"  Felder: {len(spannweiten)}")
    #     print(f"  Spannweiten: {spannweiten}")
    #     print(f"  Kragarm links: {self.kragarm_links.get()}")
    #     print(f"  Kragarm rechts: {self.kragarm_rechts.get()}")
    def schnittgroessen_eingabe(self):
        self.schnittgroessen_frame = ttk.LabelFrame(
            self.root, text="Schnittgrößen", padding=10)
        self.schnittgroessen_frame.pack(padx=10, pady=10, fill="x")

        headers = ["", "My,d [kNm]:", "Vz,d [kN]:", "", "", "Runden auf:"]
        for i, header in enumerate(headers):
            ttk.Label(self.schnittgroessen_frame, text=header, width=9).grid(
                row=0, column=i, padx=5)

        ttk.Label(self.schnittgroessen_frame, text="Kaltfall [kN]:").grid(
            row=1, column=0, sticky="w")
        ttk.Label(self.schnittgroessen_frame, text="Warmfall [kN]:").grid(
            row=2, column=0, sticky="w")

        self.rundung_var = tk.StringVar(value="0.1")
        rundung_combo = ttk.Combobox(self.schnittgroessen_frame, textvariable=self.rundung_var,
                                     values=["0.1", "0.5", "1.0"], width=5, state="readonly")
        rundung_combo.grid(row=1, column=5, sticky="w")

    def querschnitt_eingabe(self):
        self.querschnitt_frame = ttk.LabelFrame(
            self.root, text="Bemessungsquerschnitt", padding=10)
        self.querschnitt_frame.pack(padx=10, pady=10, fill="x")

        self.querschnitt_var = tk.StringVar(value="Vollholz")
        ttk.Label(self.querschnitt_frame, text="Typ:").grid(
            row=0, column=0, sticky="w")
        qs_typ_combo = ttk.Combobox(self.querschnitt_frame, textvariable=self.querschnitt_var,
                                    values=["Vollholz", "BSP-Platte"], width=12, state="readonly")
        qs_typ_combo.grid(row=0, column=1, sticky="w")
        qs_typ_combo.bind("<<ComboboxSelected>>",
                          lambda e: self.update_querschnitt_felder())

        # Container für dynamische Felder
        self.querschnitt_details_frame = ttk.Frame(self.querschnitt_frame)
        self.querschnitt_details_frame.grid(
            row=1, column=0, columnspan=5, sticky="w")

        self.update_querschnitt_felder()

        # γₘ
        ttk.Label(self.querschnitt_frame, text="γₘ:").grid(
            row=2, column=0, sticky="w")
        self.gamma_m_entry = ttk.Entry(self.querschnitt_frame, width=6)
        self.gamma_m_entry.insert(0, "1.30")
        self.gamma_m_entry.grid(row=2, column=1, sticky="w")

    def update_querschnitt_felder(self):
        for widget in self.querschnitt_details_frame.winfo_children():
            widget.destroy()

        if self.querschnitt_var.get() == "Vollholz":
            ttk.Label(self.querschnitt_details_frame, text="b [mm]:").grid(
                row=0, column=0, sticky="w")
            self.b_entry = ttk.Entry(self.querschnitt_details_frame, width=8)
            self.b_entry.insert(0, "160")
            self.b_entry.grid(row=0, column=1)

            ttk.Label(self.querschnitt_details_frame, text="h [mm]:").grid(
                row=0, column=2, sticky="w")
            self.h_entry = ttk.Entry(self.querschnitt_details_frame, width=8)
            self.h_entry.insert(0, "400")
            self.h_entry.grid(row=0, column=3)
        else:
            ttk.Label(self.querschnitt_details_frame, text="Schichten [n]:").grid(
                row=0, column=0, sticky="w")
            self.bsp_schichten = ttk.Entry(
                self.querschnitt_details_frame, width=5)
            self.bsp_schichten.insert(0, "5")
            self.bsp_schichten.grid(row=0, column=1)

            ttk.Label(self.querschnitt_details_frame,
                      text="E-Modul [N/mm²]:").grid(row=0, column=2, sticky="w")
            self.bsp_emodul = ttk.Entry(
                self.querschnitt_details_frame, width=8)
            self.bsp_emodul.insert(0, "11000")
            self.bsp_emodul.grid(row=0, column=3)

    def gebrauchstauglichkeit_eingabe(self):
        self.gebrauchstauglichkeit_frame = ttk.LabelFrame(
            self.root, text="Gebrauchstauglichkeit", padding=10)
        self.gebrauchstauglichkeit_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(self.gebrauchstauglichkeit_frame, text="w_inst [mm]:", width=10).grid(
            row=0, column=0, sticky="w")
        self.w_inst = ttk.Entry(self.gebrauchstauglichkeit_frame, width=6)
        self.w_inst.insert(0, "20")
        self.w_inst.grid(row=0, column=1)

        ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin [mm]:", width=10).grid(
            row=1, column=0, sticky="w")
        self.w_fin = ttk.Entry(self.gebrauchstauglichkeit_frame, width=6)
        self.w_fin.insert(0, "30")
        self.w_fin.grid(row=1, column=1)

        ttk.Label(self.gebrauchstauglichkeit_frame, text="w_be [mm]:", width=10).grid(
            row=2, column=0, sticky="w")
        self.w_be = ttk.Entry(self.gebrauchstauglichkeit_frame, width=6)
        self.w_be.insert(0, "40")
        self.w_be.grid(row=2, column=1)

        ttk.Label(self.gebrauchstauglichkeit_frame, text="Situation:").grid(
            row=3, column=1, sticky="w")
        self.situation_var = tk.StringVar(value="Decke (Standardbauteile)")
        situation_combo = ttk.Combobox(self.gebrauchstauglichkeit_frame, textvariable=self.situation_var,
                                       values=["Decke (Standardbauteile)", "Überhöhung"], width=25, state="readonly")
        situation_combo.grid(row=3, column=2)


def starte_gui():
    root = tk.Tk()
    app = Eingabemaske(root)
    root.mainloop()
# if __name__ == '__main__':
#     root = tk.Tk()
#     app = Eingabemaske(root)
#     root.mainloop()
