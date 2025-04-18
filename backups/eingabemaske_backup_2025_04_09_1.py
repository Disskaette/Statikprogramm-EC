import tkinter as tk
from tkinter import ttk
import pandas as pd
import os


class Eingabemaske:
    def __init__(self, root):
        self.root = root
        self.root.title("Durchlaufträger | Statik-Tool Holzbau")

        self.max_felder = 5
        self.feldanzahl_var = None
        # self.material_typen = None
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
        self.querschnitt_var_1 = None
        self.querschnitt_frame = None
        # Querschnittgruppen
        self.querschnitt_balken = None
        self.querschnitt_bsp = None
        self.festigkeitsklasse_vh = None
        # Querschnittvariationen
        self.b_entry_1 = None
        self.b_entry_2 = None
        self.b_entry_3 = None
        self.h_entry_1 = None
        self.h_entry_2 = None
        self.h_entry_3 = None

        self.bsp_schichten = None
        self.bsp_emodul = None
        self.gamma_m_entry = None
        # Gebrauchstauglichkeit
        self.w_inst = None
        self.w_fin = None
        self.w_be = None
        self.situation_var = None

        '''Scrollbar'''
        # Frame für den Scrollbereich
        scroll_container = ttk.Frame(self.root)
        scroll_container.pack(fill="both", expand=True)

        # Canvas + vertikale Scrollbar
        self.canvas = tk.Canvas(scroll_container)
        # self.canvas.bind("<Configure>",
        #                  lambda e: self.canvas.itemconfig("inner_frame", width=e.width))
        scrollbar = ttk.Scrollbar(
            scroll_container, orient="vertical", command=self.canvas.yview)

        # Der Frame mit allem Inhalt
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Scrollbereich automatisch anpassen
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        # Scrollbarer Bereich in Canvas einfügen
        self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw", tags="inner_frame")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Pack alles
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        '''Programm laden'''
        self.bind_scroll_events()
        self.lade_materialdaten()
        self.setup_gui()
        self.root.after(100, self.ermittle_erforderliche_breite)

    def bind_scroll_events(self):
        # Aktiviert Mausrad-Scrolling, wenn der Mauszeiger über dem Canvas ist
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self._on_mousewheel))
        self.canvas.bind(
            "<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event):
        system = self.root.tk.call("tk", "windowingsystem")

        if system == "aqua":  # macOS
            self.canvas.yview_scroll(-1 * int(event.delta), "units")
        else:  # Windows & Linux
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def ermittle_erforderliche_breite(self):
        self.root.update_idletasks()
        breite = self.scrollable_frame.winfo_reqwidth()
        height = self.scrollable_frame.winfo_reqheight()
        max_height = min(height, 1200)
        self.root.geometry(f"{breite+20}x{max_height}")

    def lade_materialdaten(self):
        # Absoluten Pfad zur Datei berechnen – relativ zu dieser Python-Datei
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dateipfad = os.path.join(
            script_dir, "..", "datenbank", "datenbank_dlt.xlsx")

        if not os.path.exists(dateipfad):
            print("❌ Datei nicht gefunden unter:", dateipfad)
            return

        df = pd.read_excel(dateipfad, sheet_name="materials")

        # Umstrukturieren in geschachteltes Dict
        material_dict = {}
        for _, row in df.iterrows():
            gruppe = row["Materialgruppe"]
            typ = row["Typ"]
            festigkeitsklasse = row["Festigkeitsklasse"]

            if gruppe not in material_dict:
                material_dict[gruppe] = {}

            if pd.notna(typ) and typ not in material_dict[gruppe]:
                material_dict[gruppe][typ] = []

            if pd.notna(festigkeitsklasse):
                material_dict[gruppe][typ].append(festigkeitsklasse)

        self.material_typen = material_dict

    def setup_gui(self):
        # --- Eingabeframe ---
        frame_eingabe = ttk.LabelFrame(
            self.scrollable_frame, text="Systemeingabe", padding=10)
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
            self.scrollable_frame, text="Spannweiten je Feld [m]", padding=10)
        self.spannweiten_frame.pack(padx=10, pady=10, fill="x")
        self.spannweiten_eingaben = []
        self.update_spannweitenfelder()

        # --- Lasteneingabe-Feld ---
        self.lasten_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Lasten [kN/m²]", padding=10)
        self.lasten_frame.pack(padx=10, pady=10, fill="x")

        headers = ["", "LF", "q [kN/m²]", "Lastfall", "Kommentar"]
        for i, header in enumerate(headers):
            ttk.Label(self.lasten_frame, text=header).grid(
                row=0, column=i, padx=5)

        self.lasten_eingaben = []
        self.add_lasteneingabe()
        self.schnittgroessen_ausgabe()
        self.querschnitt_eingabe()
        self.update_querschnitt_felder()
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

    def schnittgroessen_ausgabe(self):
        self.schnittgroessen_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Schnittgrößen", padding=10)
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
            self.scrollable_frame, text="Bemessungsquerschnitt", padding=10)
        self.querschnitt_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(self.querschnitt_frame, text="Materialgruppe:").grid(
            row=0, column=0, sticky="w")
        self.materialgruppe_var = tk.StringVar(value="Balken")
        qs_materialgruppe_combo = ttk.Combobox(self.querschnitt_frame, textvariable=self.materialgruppe_var,
                                               values=("Balken"), width=12, state="readonly")
        qs_materialgruppe_combo.grid(row=0, column=1, columnspan=2, sticky="w")
        qs_materialgruppe_combo.bind("<<ComboboxSelected>>",
                                     lambda e: self.update_querschnitt_felder())

        self.update_querschnitt_felder()

    def update_querschnitt_felder(self):
        # Lösche nur Widgets ab Zeile 1 (Materialgruppe bleibt erhalten)
        for widget in self.querschnitt_frame.winfo_children():
            try:
                row = int(widget.grid_info().get("row", -1))
                if row >= 1:
                    widget.destroy()
            except Exception:
                pass

        materialgruppe = self.materialgruppe_var.get()

        if materialgruppe == "Balken":
            # Typauswahl
            ttk.Label(self.querschnitt_frame, text="Typ:").grid(
                row=1, column=0, sticky="w")
            self.querschnitt_var_1 = tk.StringVar()
            typen_1 = list(self.material_typen[materialgruppe].keys())
            self.querschnitt_var_1.set(typen_1[0])
            qs_typ_combo_1 = ttk.Combobox(self.querschnitt_frame, textvariable=self.querschnitt_var_1,
                                          values=typen_1, width=12, state="readonly")
            qs_typ_combo_1.grid(row=1, column=1, columnspan=2, sticky="w")
            qs_typ_combo_1.bind("<<ComboboxSelected>>",
                                lambda e: self.update_festigkeitsklasse_dropdown())
            self.querschnitt_var_1.set(typen_1[0])

            # Festigkeitsklasse
            ttk.Label(self.querschnitt_frame, text="Festigkeit:").grid(
                row=2, column=0, sticky="w")
            self.festigkeitsklasse_var_1 = tk.StringVar()
            festigkeiten = self.material_typen[materialgruppe][self.querschnitt_var_1.get(
            )]
            self.festigkeitsklasse_var_1.set(festigkeiten[0])
            self.qs_festigkeit_combo = ttk.Combobox(self.querschnitt_frame, textvariable=self.festigkeitsklasse_var_1,
                                                    values=festigkeiten, width=12, state="readonly")
            self.qs_festigkeit_combo.grid(
                row=2, column=1, columnspan=2, sticky="w")
            self.update_festigkeitsklasse_dropdown()

            # Checkbox für Querschnittsvariationen
            self.radiobox_var = tk.IntVar()
            self.radiobox_var.set(1)

            ttk.Radiobutton(self.querschnitt_frame, text="Variante 1", variable=self.radiobox_var,
                            value=1).grid(row=3, column=1, columnspan=2, sticky="w", pady=5)
            ttk.Radiobutton(self.querschnitt_frame, text="Variante 2", variable=self.radiobox_var,
                            value=2).grid(row=3, column=3, columnspan=2,  sticky="w", pady=5)
            ttk.Radiobutton(self.querschnitt_frame, text="Variante 3", variable=self.radiobox_var,
                            value=3).grid(row=3, column=5, columnspan=2, sticky="w", pady=5)

            # Eingabe Variante 1
            ttk.Label(self.querschnitt_frame, text="b [mm]:").grid(
                row=4, column=1, sticky="w")
            self.b_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.b_entry_1.insert(0, "160")
            self.b_entry_1.grid(row=4, column=2, padx=5, sticky="w")

            ttk.Label(self.querschnitt_frame, text="h [mm]:").grid(
                row=5, column=1, sticky="w")
            self.h_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.h_entry_1.insert(0, "400")
            self.h_entry_1.grid(row=5, column=2, padx=5, sticky="w")

            # Eingabe Variante 2
            ttk.Label(self.querschnitt_frame, text="b [mm]:").grid(
                row=4, column=3, sticky="w")
            self.b_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.b_entry_1.insert(0, "160")
            self.b_entry_1.grid(row=4, column=4, padx=5, sticky="w")

            ttk.Label(self.querschnitt_frame, text="h [mm]:").grid(
                row=5, column=3, sticky="w")
            self.h_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.h_entry_1.insert(0, "400")
            self.h_entry_1.grid(row=5, column=4, padx=5, sticky="w")

            # Eingabe Variante 3
            ttk.Label(self.querschnitt_frame, text="b [mm]:").grid(
                row=4, column=5, sticky="w")
            self.b_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.b_entry_1.insert(0, "160")
            self.b_entry_1.grid(row=4, column=6, padx=5, sticky="w")

            ttk.Label(self.querschnitt_frame, text="h [mm]:").grid(
                row=5, column=5, sticky="w")
            self.h_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.h_entry_1.insert(0, "400")
            self.h_entry_1.grid(row=5, column=6, padx=5, sticky="w")

    def update_festigkeitsklasse_dropdown(self):
        materialgruppe = self.materialgruppe_var.get()
        typ = self.querschnitt_var_1.get()

        festigkeiten = self.material_typen.get(materialgruppe, {}).get(typ, [])
        if festigkeiten:
            self.festigkeitsklasse_var_1.set(festigkeiten[0])
            self.qs_festigkeit_combo["values"] = festigkeiten
        else:
            self.festigkeitsklasse_var_1.set("")
            self.qs_festigkeit_combo["values"] = []

    def gebrauchstauglichkeit_eingabe(self):
        self.gebrauchstauglichkeit_frame = ttk.LabelFrame(
            self.scrollable_frame, text="Gebrauchstauglichkeit", padding=10)
        self.gebrauchstauglichkeit_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(self.gebrauchstauglichkeit_frame, text="Situation:").grid(
            row=0, column=0, sticky="w")
        self.situation_var = tk.StringVar(value="Allgemein")
        situation_combo = ttk.Combobox(self.gebrauchstauglichkeit_frame, textvariable=self.situation_var,
                                       values=["Allgemein", "Überhöhte, Untergeordnete Bauteile", "Eigene Werte"], width=25, state="readonly")
        situation_combo.grid(row=0, column=1, columnspan=5, sticky="w", pady=2)
        situation_combo.bind("<<ComboboxSelected>>",
                             lambda e: self.update_gebrauchstauglichkeit_eingabe())
        self.update_gebrauchstauglichkeit_eingabe()

    def update_gebrauchstauglichkeit_eingabe(self):
        # Lösche nur Widgets ab Zeile 1 (Materialgruppe bleibt erhalten)
        for widget in self.gebrauchstauglichkeit_frame.winfo_children():
            try:
                row = int(widget.grid_info().get("row", -1))
                if row >= 1:
                    widget.destroy()
            except Exception:
                pass
        if self.situation_var.get() == "Allgemein":
            # Set Grenzwerte Allgemeoin
            self.w_inst_grenz_allgemein = 300
            self.w_fin_grenz_allgmein = 200
            self.w_net_fin_grenz_allgemein = 300

            # Ausgabe Grenzwerte
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_inst:", width=6).grid(
                row=2, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_inst_grenz_allgemein}", width=6).grid(
                row=2, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin:", width=12).grid(
                row=3, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_fin_grenz_allgmein}", width=6).grid(
                row=3, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin_net:", width=12).grid(
                row=4, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_net_fin_grenz_allgemein}", width=6).grid(
                row=4, column=1, sticky="w")

        elif self.situation_var.get() == "Überhöhte, Untergeordnete Bauteile":
            # Set Grenzwerte Überhöhte, Untergeordnete Bauteile
            self.w_inst_grenz_ueberhoeht = 200
            self.w_fin_grenz_ueberhoeht = 150
            self.w_net_fin_grenz_ueberhoeht = 250

            # Überhöhungseingabe
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_c [mm]:", width=12).grid(
                row=2, column=0, sticky="e", pady=2)
            self.w_c_überhöhung = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_c_überhöhung.insert(0, "0.00")
            self.w_c_überhöhung.grid(row=2, column=1, sticky="w", pady=2)

            # Ausgabe Grenzwerte
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_inst:", width=12).grid(
                row=3, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_inst_grenz_ueberhoeht}", width=6).grid(
                row=3, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin:", width=12).grid(
                row=4, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_fin_grenz_ueberhoeht}", width=6).grid(
                row=4, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin_net:", width=12).grid(
                row=5, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_net_fin_grenz_ueberhoeht}", width=6).grid(
                row=5, column=1, sticky="w")

        elif self.situation_var.get() == "Eigene Werte":
            # Überhöhungseingabe
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_c [mm]:", width=12).grid(
                row=2, column=0, sticky="w")
            self.w_c_überhöhung = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_c_überhöhung.insert(0, "0.00")
            self.w_c_überhöhung.grid(row=2, column=1, sticky="w")

            # Ausgabe Grenzwerte
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_inst       -> L / :", width=12).grid(
                row=3, column=0, sticky="w")
            self.w_inst_grenz_eigen = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_inst_grenz_eigen.insert(0, "300")
            self.w_inst_grenz_eigen.grid(row=3, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin         -> L / :", width=12).grid(
                row=4, column=0, sticky="w")
            self.w_fin_grenz_eigen = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_fin_grenz_eigen.insert(0, "200")
            self.w_fin_grenz_eigen.grid(row=4, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin_net -> L / :", width=12).grid(
                row=5, column=0, sticky="w")
            self.w_net_fin_grenz_eigen = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_net_fin_grenz_eigen.insert(0, "300")
            self.w_net_fin_grenz_eigen.grid(
                row=5, column=1, sticky="w")


# def starte_gui():
#     root = tk.Tk()
#     app = Eingabemaske(root)
#     root.mainloop()
if __name__ == '__main__':
    root = tk.Tk()
    app = Eingabemaske(root)
    root.mainloop()
