import tkinter as tk
from tkinter import ttk
import logging
import customtkinter as ctk

# Datenbank importieren
from backend.database.datenbank_holz import datenbank_holz_class
from backend.calculations.lastenkombination import MethodeLastkombi
from frontend.display.anzeige_lastkombination import LastkombiAnzeiger
from frontend.display.anzeige_feebb import FeebbAnzeiger
from backend.service.orchestrator_service import OrchestratorService
from frontend.display.anzeige_system import SystemAnzeiger
from frontend.display.anzeige_nachweis_ec5 import NachweisEC5Anzeiger
from frontend.frontend_orchestrator import FrontendOrchestrator

# Theme importieren
try:
    from frontend.gui.theme_config import ThemeManager
except ImportError:
    ThemeManager = None

# Root-Logger-Verhalten
logging.basicConfig(
    level=logging.DEBUG,                      # ab welcher Wichtigkeit geloggt wird
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)          # logger für dieses Modul


class Eingabemaske:
    def __init__(self, root):
        self.root = root
        self.root.title("Durchlaufträger | Statik-Tool Holzbau")

        # KEIN Theme hier - verursacht Fehler mit aqua-Theme
        # Wir setzen nur die Fonts in _configure_font_styles()

        # Fenster im Vordergrund
        root.attributes("-topmost", True)
        root.focus_force()
        root.after(500, lambda: root.attributes("-topmost", False))

        # Einheitliche Schriftgrößen definieren
        self.FONT_HEADING = ('', 12, 'bold')  # Überschriften
        # Normaler Text, Labels, Radiobuttons etc.
        self.FONT_NORMAL = ('', 10)

        # Style für einheitliche Schriftgrößen konfigurieren
        self._configure_font_styles()

        # Importe
        self.db = datenbank_holz_class()
        self.kombi_berechnung = MethodeLastkombi(self, self.db)
        self.feebb = FeebbAnzeiger(self)
        self.orch = OrchestratorService()
        # Fenstergröße änderbar händisch
        self.fenster_manuell_verkleinert = False
        self.resize_tracking_aktiv = False

        # Dictionarys inititalisierung
        self.lasten_memory = []
        self.spannweiten_memory = {}
        self.querschnitt_memory = {}

        # Systemeingabe
        self.sprungmass = None
        self.max_felder = 5
        self.feldanzahl_var = None
        self.kragarm_laenge_links = None
        self.feld_1 = None
        self.feld_2 = None
        self.feld_3 = None
        self.feld_4 = None
        self.feld_5 = None
        self.kragarm_laenge_rechts = None
        # self.material_typen = None
        # Kragarme
        self.kragarm_links = None
        self.kragarm_rechts = None
        # Spannweiten-Felder
        self.spannweiten_frame = None
        self.spannweiten_eingaben = None
        # Lasteneingabe
        self.lasten_eingaben = []
        self.lasten_frame = None
        self.kmod_typ = 'ständig'
        # Plus Button
        self.plus_button = None
        # Self NKL
        self.nkl_label = None
        self.nkl_dropdown = None
        self.nkl_var = None
        self.anzeige_lastkombis = None
        self.radio_lastkombi_1 = None
        self.radio_lastkombi_2 = None
        self.eigengewicht_label = None
        self.eigengewicht_active = None
        self.eigengewicht_checkbutton = None
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
        # Monitoring und Überwachung
        # __init__ oder setup_gui
        self.gui_fertig_geladen = False
        self._berechnung_laeuft = False
        self._berechnung_nochmal = False
        self._last_berechnung_time = 0
        self.letzter_daten_hash = None
        self._berechnung_timer_id = None
        self._berechnungsversuche = 0
        self._update_timer = None
        # Berechnungsmodus
        self.ec_modus_var = None
        # Ladeindikator
        self.loading_label = None
        self.loading_animation_running = False
        # Cache für strukturelle Berechnungen
        self._cached_structural_hash = None

        '''Scrollbar'''
        # Wrapper-Frame für Scrollbereich
        scroll_container = ttk.Frame(self.root)
        scroll_container.pack(fill="both", expand=True)

        # Canvas erstellen
        self.canvas = tk.Canvas(scroll_container, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Scrollbars
        scrollbar_y = ttk.Scrollbar(
            scroll_container, orient="vertical", command=self.canvas.yview)
        scrollbar_y.pack(side="right", fill="y")

        scrollbar_x = ttk.Scrollbar(
            self.root, orient="horizontal", command=self.canvas.xview)
        scrollbar_x.pack(side="bottom", fill="x")

        self.canvas.configure(yscrollcommand=scrollbar_y.set,
                              xscrollcommand=scrollbar_x.set)

        # Inhalt auf Canvas legen
        self.content_frame = ttk.Frame(self.canvas)
        self.inner_window = self.canvas.create_window(
            (0, 0), window=self.content_frame, anchor="nw")

        self.eingabe_frame = ttk.Frame(self.content_frame)
        self.eingabe_frame.grid(row=0, column=0, sticky="nw")

        self.ausgabe_frame = ttk.Frame(self.content_frame)
        self.ausgabe_frame.grid(row=0, column=1, sticky="nw")
        self.system_anzeiger = SystemAnzeiger(self.ausgabe_frame, self)
        self.kombi_anzeiger = LastkombiAnzeiger(self.ausgabe_frame, self)
        self.nachweis_anzeiger = NachweisEC5Anzeiger(self.ausgabe_frame, self)
        self.orch_front = FrontendOrchestrator(
            self.system_anzeiger,
            self.kombi_anzeiger,
            self.nachweis_anzeiger)

        # Scrollregion automatisch anpassen

        def update_scrollregion(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.content_frame.bind("<Configure>", update_scrollregion)

        # Optional: Fenstergröße begrenzen
        def begrenze_fenstergroesse():
            # Keine automatische Anpassung des Fensters
            if self.fenster_manuell_verkleinert:
                return
            self.root.update_idletasks()
            max_width = 1800
            max_height = 1000
            actual_w = self.content_frame.winfo_reqwidth()
            actual_h = self.content_frame.winfo_reqheight()
            self.root.geometry(
                f"{min(actual_w + 20, max_width)}x{min(actual_h + 20, max_height)}")
            self.root.after(100, begrenze_fenstergroesse)

        '''Programm laden'''
        # self.lade_materialdaten()
        self.setup_gui()
        self.bind_scroll_events()
        self.root.after(100, begrenze_fenstergroesse)
        self.root.after(300, self.on_any_change)
        self.root.after(500, self.on_any_change)

        # self.root.bind("<Configure>", self.on_window_resize)
        # self.root.after(500, lambda: setattr(
        #     self, "resize_tracking_aktiv", True))

    # def on_window_resize(self, event):
    #     if not self.resize_tracking_aktiv:
    #         return  # Ignoriere Ereignisse während des Setups

    #     if event.widget == self.root:
    #         self.fenster_manuell_verkleinert = True
    #         print("🔧 Fenster wurde manuell angepasst!")

    def bind_scroll_events(self):
        # Aktiviert Mausrad-Scrolling, wenn der Mauszeiger über dem Canvas ist
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", self.on_vertical_scroll))
        self.canvas.bind(
            "<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        self.canvas.bind("<Shift-MouseWheel>", self.on_horizontal_scroll)

    def on_horizontal_scroll(self, event):
        system = self.root.tk.call("tk", "windowingsystem")
        if system == "aqua":  # macOS
            self.canvas.xview_scroll(-1 * int(event.delta), "units")
        else:  # Windows/Linux
            self.canvas.xview_scroll(-1 * int(event.delta / 120), "units")

    def on_vertical_scroll(self, event):
        system = self.root.tk.call("tk", "windowingsystem")

        if system == "aqua":  # macOS
            self.canvas.yview_scroll(-1 * int(event.delta), "units")
        else:  # Windows & Linux
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

        # Wenn Inhalt breiter ist als erlaubte Fensterbreite → Scrollbar ermöglichen

    def _configure_font_styles(self):
        """Konfiguriert einheitliche Schriftgrößen für alle Widgets"""
        style = ttk.Style()

        # NUR FONTS - keine background für aqua-Theme (verursacht Fehler)
        # LabelFrame Überschriften - größer und fett
        style.configure('TLabelframe.Label', font=self.FONT_HEADING)

        # Normale Labels - einheitliche Größe
        style.configure('TLabel', font=self.FONT_NORMAL)

        # Buttons - einheitliche Größe
        style.configure('TButton', font=self.FONT_NORMAL)

        # Radiobuttons - einheitliche Größe
        style.configure('TRadiobutton', font=self.FONT_NORMAL)

        # Checkbuttons - einheitliche Größe
        style.configure('TCheckbutton', font=self.FONT_NORMAL)

        # Für Entry, Combobox, Spinbox: option_add funktioniert besser mit aqua
        self.root.option_add('*TCombobox*Listbox.font', ('', 10))
        self.root.option_add('*Entry.font', ('', 10))
        self.root.option_add('*Spinbox.font', ('', 10))

        # Auch über style versuchen (funktioniert nicht immer mit aqua)
        try:
            style.configure('TCombobox', font=('', 10))
            style.configure('TEntry', font=('', 10))
            style.configure('TSpinbox', font=('', 10))
        except:
            pass

    '''Beginn der Eingabemaske'''

    def setup_gui(self):
        # --- Eingabeframe ---
        berechnungsmodus_frame = ttk.LabelFrame(
            self.eingabe_frame, text="Berechnungsmodus", padding=10)
        berechnungsmodus_frame.pack(padx=10, pady=10, fill="x")

        frame_system_eingabe = ttk.LabelFrame(
            self.eingabe_frame, text="Systemeingabe", padding=10)
        frame_system_eingabe.pack(padx=10, pady=10, fill="x")

        # Berechnungsmodus-Umschalter
        # ttk.Separator(berechnungsmodus_frame, orient='horizontal').grid(
        #     row=3, column=0, columnspan=2, sticky='ew', pady=5)
        self.ec_modus_var = tk.BooleanVar(
            value=False)  # Default: Schnell-Modus
        mode_frame = ttk.Frame(berechnungsmodus_frame)
        mode_frame.grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(mode_frame, text="⚡ Volllast (schnell)",
                        variable=self.ec_modus_var, value=False,
                        command=self.on_any_change).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="🔬 EC-Kombinatorik (genau)",
                        variable=self.ec_modus_var, value=True,
                        command=self.on_any_change).pack(side="left", padx=5)

        # Ladeindikator
        self.loading_label_ph = ttk.Label(
            berechnungsmodus_frame, text="", foreground="blue")
        self.loading_label_ph.grid(
            row=0, column=4, columnspan=2, pady=5, padx=30)
        self.loading_label = ttk.Label(
            berechnungsmodus_frame, text="", foreground="blue")
        self.loading_label.grid(row=0, column=6, columnspan=2, pady=5)

        # Sprungmaß
        ttk.Label(frame_system_eingabe, text="Sprungmaß e [m]:").grid(row=0,
                                                                      column=0, sticky="w")
        self.sprungmass_entry = ttk.Entry(frame_system_eingabe, width=6)
        self.sprungmass_entry.insert(0, "1.00")
        self.sprungmass_entry.grid(row=0, column=1, padx=0, pady=2)
        self.sprungmass_entry.bind(
            "<KeyRelease>", self.on_any_change)

        # Anzahl Felder
        ttk.Label(frame_system_eingabe, text="Anzahl Felder (1-5):").grid(row=1,
                                                                          column=0, sticky="w")
        self.feldanzahl_var = tk.IntVar(value=1)
        spinbox = ttk.Spinbox(frame_system_eingabe, from_=1, to=self.max_felder,
                              textvariable=self.feldanzahl_var, width=5,
                              command=self.update_spannweitenfelder)
        spinbox.grid(row=1, column=1, padx=5)

        # Kragarm links/rechts
        self.kragarm_links = tk.BooleanVar()
        self.kragarm_rechts = tk.BooleanVar()
        ttk.Checkbutton(frame_system_eingabe, text="Kragarm links", variable=self.kragarm_links,
                        command=self.update_spannweitenfelder).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(frame_system_eingabe, text="Kragarm rechts", variable=self.kragarm_rechts,
                        command=self.update_spannweitenfelder).grid(row=2, column=1, sticky="w")

        # Spannweiten-Felder
        self.spannweiten_frame = ttk.LabelFrame(
            self.eingabe_frame, text="Spannweiten je Feld [m]", padding=10)
        self.spannweiten_frame.pack(padx=10, pady=10, fill="x")
        self.spannweiten_eingaben = []
        self.update_spannweitenfelder()

        # --- Lasteneingabe-Feld ---
        self.lasten_frame = ttk.LabelFrame(
            self.eingabe_frame, text="Lasten [kN/m²]", padding=10)
        self.lasten_frame.pack(padx=10, pady=10, fill="x")

        headers = ["", "Lastfall", "q [kN/m²]", "Kategorie", "Kommentar"]
        for i, header in enumerate(headers):
            ttk.Label(self.lasten_frame, text=header).grid(
                row=0, column=i, padx=5)

        self.add_lasteneingabe()
        self.schnittgroessen_ausgabe()
        self.querschnitt_eingabe()
        self.gebrauchstauglichkeit_eingabe()
        self.gui_fertig_geladen = True

    def update_spannweitenfelder(self):
        # Aktuelle Werte speichern, bevor Widgets zerstört werden
        temp_memory = {}
        for eintrag in self.spannweiten_eingaben:
            name = eintrag["name"]
            entry_widget = eintrag["entry"]
            try:
                # Aktuellen Wert aus Entry-Feld auslesen
                temp_memory[name] = entry_widget.get()
            except:
                pass

        for widget in self.spannweiten_frame.winfo_children():
            widget.destroy()

        self.spannweiten_eingaben = []
        col = 0

        if self.kragarm_links.get():
            ttk.Label(self.spannweiten_frame, text="Kragarm L [m]").grid(
                row=0, column=col)
            entry_kragarm_l = ttk.Entry(self.spannweiten_frame, width=7)
            # Gespeicherten Wert wiederherstellen oder Default verwenden
            default_value = temp_memory.get("kragarm_links", "5")
            entry_kragarm_l.insert(0, default_value)
            entry_kragarm_l.grid(row=1, column=col)
            self.spannweiten_eingaben.append(
                {"name": "kragarm_links", "entry": entry_kragarm_l})
            col += 1

        for i in range(self.feldanzahl_var.get()):
            ttk.Label(self.spannweiten_frame,
                      text=f"Feld {i+1} [m]").grid(row=0, column=col)
            entry = ttk.Entry(self.spannweiten_frame, width=7)
            # Gespeicherten Wert wiederherstellen oder Default verwenden
            default_value = temp_memory.get(f"feld_{i+1}", "5")
            entry.insert(0, default_value)
            entry.grid(row=1, column=col)
            self.spannweiten_eingaben.append(
                {"name": f"feld_{i+1}", "entry": entry})
            col += 1

        if self.kragarm_rechts.get():
            ttk.Label(self.spannweiten_frame, text="Kragarm R [m]").grid(
                row=0, column=col)
            entry_kragarm_r = ttk.Entry(self.spannweiten_frame, width=7)
            # Gespeicherten Wert wiederherstellen oder Default verwenden
            default_value = temp_memory.get("kragarm_rechts", "5")
            entry_kragarm_r.insert(0, default_value)
            entry_kragarm_r.grid(row=1, column=col)
            self.spannweiten_eingaben.append(
                {"name": "kragarm_rechts", "entry": entry_kragarm_r})

        for spannweite in self.spannweiten_eingaben:
            spannweite["entry"].bind(
                "<KeyRelease>", self.on_any_change)
        self.on_any_change()

    def add_lasteneingabe(self):
        if len(self.lasten_eingaben) >= 5:
            return

        row = len(self.lasten_eingaben) + 1

        # --- Eingabefelder ---
        lf_var = tk.StringVar(value=self.db.get_sortierte_lastfaelle()[0])
        lf_combo = ttk.Combobox(self.lasten_frame, textvariable=lf_var,
                                values=self.db.get_sortierte_lastfaelle(), width=3, state="readonly")
        lf_combo.grid(row=row, column=1, padx=5, pady=2)

        q_entry = ttk.Entry(self.lasten_frame, width=6)
        q_entry.grid(row=row, column=2, padx=0, pady=2)
        q_entry.insert(0, "7,41")

        lf_detail_var = tk.StringVar()
        lf_detail_combo = ttk.Combobox(
            self.lasten_frame, textvariable=lf_detail_var, width=20, state="readonly")
        lf_detail_combo.grid(row=row, column=3, padx=5, pady=2)

        kommentar_entry = ttk.Entry(self.lasten_frame, width=10)
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
        # --- Bindings für automatische Aktualisierung ---
        q_entry.bind("<KeyRelease>", self.on_any_change)
        kommentar_entry.bind("<KeyRelease>", lambda e: (
            self.on_any_change()))
        lf_combo.bind("<<ComboboxSelected>>", lambda e: (
            self.on_any_change()))
        lf_detail_combo.bind("<<ComboboxSelected>>", lambda e: (
            self.on_any_change()))

        self.update_plus_button()
        self.on_any_change()

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
        self.on_any_change()

    def update_lastfall_options(self, lf_var, detail_combo, detail_var):
        lastfall = lf_var.get()
        kategorien = self.db.get_kategorien_fuer_lastfall(lastfall)

        detail_combo["values"] = kategorien
        if kategorien:
            detail_var.set(kategorien[0])  # erste Kategorie setzen
        else:
            detail_var.set("")  # falls keine gefunden

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

        self.nkl_eingabe(row + 1)
        self.on_any_change()

    def nkl_eingabe(self, row=None):

        if self.anzeige_lastkombis is None:
            self.anzeige_lastkombis = tk.IntVar(value=1)
        if self.radio_lastkombi_1 is not None:
            self.radio_lastkombi_1.destroy()
            self.radio_lastkombi_2.destroy()
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
        self.nkl_dropdown.bind("<<ComboboxSelected>>",
                               lambda e: self.on_any_change())
        if self.eigengewicht_label is not None:
            self.eigengewicht_label.destroy()
        if self.eigengewicht_checkbutton is not None:
            self.eigengewicht_checkbutton.destroy()

        self.eigengewicht_label = ttk.Label(
            self.lasten_frame, text="Eigengewicht aktiv:")
        self.eigengewicht_label.grid(row=row+1, column=1, sticky="")
        self.eigengewicht_active = tk.BooleanVar(value=True)
        self.eigengewicht_checkbutton = ttk.Checkbutton(self.lasten_frame, variable=self.eigengewicht_active,
                                                        command=self.on_any_change)
        self.eigengewicht_checkbutton.grid(row=row+1, column=2, sticky="")

        self.radio_lastkombi_1 = ttk.Radiobutton(self.lasten_frame, text="Maßgebender Lastfall", variable=self.anzeige_lastkombis, value=1,
                                                 command=lambda: self.kombi_anzeiger.update(self.lastkombis))
        self.radio_lastkombi_1.grid(
            row=row, column=4, sticky="w", pady=(0, 0))
        self.radio_lastkombi_2 = ttk.Radiobutton(self.lasten_frame, text="Alle Lastfälle", variable=self.anzeige_lastkombis, value=2,
                                                 command=lambda: self.kombi_anzeiger.update(self.lastkombis))
        self.radio_lastkombi_2.grid(
            row=row+1, column=4, sticky="w", pady=(0, 0))

    def schnittgroessen_ausgabe(self):
        self.schnittgroessen_frame = ttk.LabelFrame(
            self.eingabe_frame, text="Schnittgrößen", padding=10)
        self.schnittgroessen_frame.pack(padx=10, pady=10, fill="x")

        headers = ["Bemessungsfall", "My,d [kNm]:",
                   "Vz,d [kN]:", "", "", "Runden auf:"]
        for i, header in enumerate(headers):
            ttk.Label(self.schnittgroessen_frame, text=header).grid(
                row=0, column=i, padx=5, sticky="w")

        ttk.Label(self.schnittgroessen_frame, text="Kaltfall [kN]:").grid(
            row=1, column=0, sticky="w")
        ttk.Label(self.schnittgroessen_frame, text="Warmfall [kN]:").grid(
            row=2, column=0, sticky="w")

        self.max_moment_kalt = ttk.Label(self.schnittgroessen_frame, text="")
        self.max_moment_kalt.grid(row=1, column=1, sticky="w")
        self.max_querkraft_kalt = ttk.Label(
            self.schnittgroessen_frame, text="")
        self.max_querkraft_kalt.grid(row=1, column=2, sticky="w")

        # Schnittgrößenanzeige
        self.schnittgroeßen_anzeige_button = tk.BooleanVar()
        ttk.Checkbutton(self.schnittgroessen_frame, text="Schnittkraftverläufe anzeigen",
                        variable=self.schnittgroeßen_anzeige_button, command=self.feebb.toggle_schnittkraftfenster).grid(row=3, column=0, columnspan=2, sticky="w", pady=5)
        # # # Rundungseinstellung
        # self.rundung_var = tk.StringVar(value="0.1")
        # rundung_combo = ttk.Combobox(self.schnittgroessen_frame, textvariable=self.rundung_var,
        #                              values=["0.1", "0.5", "1.0"], width=5, state="readonly")
        # rundung_combo.grid(row=1, column=5, sticky="w")

    def querschnitt_eingabe(self):
        self.querschnitt_frame = ttk.LabelFrame(
            self.eingabe_frame, text="Bemessungsquerschnitt", padding=10)
        self.querschnitt_frame.pack(padx=10, pady=10, fill="x")

        # Materialgruppe 1
        ttk.Label(self.querschnitt_frame, text="Materialgruppe:").grid(
            row=0, column=0, sticky="w")
        gruppen_1 = self.db.get_materialgruppen()
        self.materialgruppe_var_1 = tk.StringVar(value=gruppen_1[0])
        qs_materialgruppe_combo_1 = ttk.Combobox(self.querschnitt_frame, textvariable=self.materialgruppe_var_1,
                                                 values=gruppen_1, width=13, state="readonly")
        qs_materialgruppe_combo_1.grid(
            row=0, column=1, columnspan=2, sticky="w")
        qs_materialgruppe_combo_1.bind("<<ComboboxSelected>>",
                                       lambda e: (self.update_querschnitt_felder(), self.on_any_change()))
        # Materialgruppe 2
        ttk.Label(self.querschnitt_frame, text="Materialgruppe:").grid(
            row=0, column=3, sticky="w")
        gruppen_2 = self.db.get_materialgruppen()
        self.materialgruppe_var_2 = tk.StringVar(value=gruppen_2[0])
        # qs_materialgruppe_combo_2 = ttk.Combobox(self.querschnitt_frame, textvariable=self.materialgruppe_var_2,
        #                                          values=gruppen_2, width=13, state="readonly")
        # qs_materialgruppe_combo_2.grid(
        #     row=0, column=3, columnspan=2, sticky="w")
        # qs_materialgruppe_combo_2.bind("<<ComboboxSelected>>",
        #                                lambda e: self.update_querschnitt_felder(), self.update_querschnitt_memory())
        # # Materialgruppe 1
        # ttk.Label(self.querschnitt_frame, text="Materialgruppe:").grid(
        #     row=0, column=0, sticky="w")
        # gruppen_3 = self.db.get_materialgruppen()
        # self.materialgruppe_var_3 = tk.StringVar(value=gruppen_3[0])
        # qs_materialgruppe_combo_3 = ttk.Combobox(self.querschnitt_frame, textvariable=self.materialgruppe_var_3,
        #                                          values=gruppen_3, width=13, state="readonly")
        # qs_materialgruppe_combo_3.grid(
        #     row=0, column=5, columnspan=2, sticky="w")
        # qs_materialgruppe_combo_3.bind("<<ComboboxSelected>>",
        #                                lambda e: self.update_querschnitt_felder(), self.update_querschnitt_memory())
        self.b_1 = 200
        self.b_2 = 200
        self.b_3 = 200
        self.h_1 = 300
        self.h_2 = 300
        self.h_3 = 300
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

        materialgruppe_1 = self.materialgruppe_var_1.get()
        # materialgruppe_2 = self.materialgruppe_var_2.get()
        # materialgruppe_3 = self.materialgruppe_var_3.get()

        if materialgruppe_1 == "Balken":
            # Typauswahl 1
            ttk.Label(self.querschnitt_frame, text="Typ:").grid(
                row=1, column=0, sticky="w")
            typen_1 = self.db.get_typen(materialgruppe_1)
            self.querschnitt_var_1 = tk.StringVar(value=typen_1[0])
            qs_typ_combo_1 = ttk.Combobox(self.querschnitt_frame, textvariable=self.querschnitt_var_1,
                                          values=typen_1, width=13, state="readonly")
            qs_typ_combo_1.grid(row=1, column=1, columnspan=2, sticky="w")
            qs_typ_combo_1.bind("<<ComboboxSelected>>",
                                self.on_querschnitt_auswahl)
            self.querschnitt_var_1.set(typen_1[0])

            # Typauswahl 2
            ttk.Label(self.querschnitt_frame, text="Typ:").grid(
                row=1, column=3, sticky="w")
            typen_2 = self.db.get_typen(materialgruppe_1)
            self.querschnitt_var_2 = tk.StringVar(value=typen_2[0])
            qs_typ_combo_2 = ttk.Combobox(self.querschnitt_frame, textvariable=self.querschnitt_var_2,
                                          values=typen_2, width=13, state="readonly")
            qs_typ_combo_2.grid(row=1, column=4, columnspan=2, sticky="w")
            qs_typ_combo_2.bind("<<ComboboxSelected>>",
                                self.on_querschnitt_auswahl)
            self.querschnitt_var_2.set(typen_2[0])

            # Typauswahl 3
            ttk.Label(self.querschnitt_frame, text="Typ:").grid(
                row=1, column=6, sticky="w")
            typen_3 = self.db.get_typen(materialgruppe_1)
            self.querschnitt_var_3 = tk.StringVar(value=typen_3[0])
            qs_typ_combo_3 = ttk.Combobox(self.querschnitt_frame, textvariable=self.querschnitt_var_3,
                                          values=typen_3, width=13, state="readonly")
            qs_typ_combo_3.grid(row=1, column=7, columnspan=2, sticky="w")
            qs_typ_combo_3.bind("<<ComboboxSelected>>",
                                self.on_querschnitt_auswahl)
            self.querschnitt_var_3.set(typen_3[0])

            # Festigkeitsklasse 1
            ttk.Label(self.querschnitt_frame, text="Festigkeit:").grid(
                row=2, column=0, sticky="w")
            typ = self.querschnitt_var_1.get()

            festigkeitsklassen_1 = self.db.get_festigkeitsklassen(
                materialgruppe_1, typ)
            erste_festigkeit_1 = festigkeitsklassen_1[0] if festigkeitsklassen_1 else ""

            self.festigkeitsklasse_var_1 = tk.StringVar(
                value=erste_festigkeit_1)
            self.qs_festigkeit_combo_1 = ttk.Combobox(self.querschnitt_frame, textvariable=self.festigkeitsklasse_var_1,
                                                      values=festigkeitsklassen_1, width=13, state="readonly")
            self.qs_festigkeit_combo_1.grid(
                row=2, column=1, columnspan=5, sticky="w")
            self.qs_festigkeit_combo_1.bind(
                "<<ComboboxSelected>>", self.on_any_change)

            # Festigkeitsklasse 2
            ttk.Label(self.querschnitt_frame, text="Festigkeit:").grid(
                row=2, column=3, sticky="w")
            typ = self.querschnitt_var_2.get()

            festigkeitsklassen_2 = self.db.get_festigkeitsklassen(
                materialgruppe_1, typ)
            erste_festigkeit_var_2 = festigkeitsklassen_2[0] if festigkeitsklassen_2 else ""

            self.festigkeitsklasse_var_2 = tk.StringVar(
                value=erste_festigkeit_var_2)
            self.qs_festigkeit_combo_2 = ttk.Combobox(self.querschnitt_frame, textvariable=self.festigkeitsklasse_var_2,
                                                      values=festigkeitsklassen_2, width=13, state="readonly")
            self.qs_festigkeit_combo_2.grid(
                row=2, column=4, columnspan=2, sticky="w")
            self.qs_festigkeit_combo_2.bind(
                "<<ComboboxSelected>>", self.on_any_change)

            # Festigkeitsklasse 3
            ttk.Label(self.querschnitt_frame, text="Festigkeit:").grid(
                row=2, column=6, sticky="w")
            typ = self.querschnitt_var_3.get()

            festigkeitsklassen_3 = self.db.get_festigkeitsklassen(
                materialgruppe_1, typ)
            erste_festigkeit_var_3 = festigkeitsklassen_3[0] if festigkeitsklassen_3 else ""

            self.festigkeitsklasse_var_3 = tk.StringVar(
                value=erste_festigkeit_var_3)
            self.qs_festigkeit_combo_3 = ttk.Combobox(self.querschnitt_frame, textvariable=self.festigkeitsklasse_var_3,
                                                      values=festigkeitsklassen_3, width=13, state="readonly")
            self.qs_festigkeit_combo_3.grid(
                row=2, column=7, columnspan=2, sticky="w")
            self.qs_festigkeit_combo_3.bind(
                "<<ComboboxSelected>>", self.on_any_change)
            self.update_festigkeitsklasse_dropdown()

            # Checkbox für Querschnittsvariationen
            self.radiobox_var = tk.IntVar()
            self.radiobox_var.set(1)

            ttk.Radiobutton(self.querschnitt_frame, text="Variante 1", variable=self.radiobox_var,
                            value=1).grid(row=3, column=1, columnspan=2, sticky="w", pady=5)
            ttk.Radiobutton(self.querschnitt_frame, text="Variante 2", variable=self.radiobox_var,
                            value=2).grid(row=3, column=4, columnspan=2,  sticky="w", pady=5)
            ttk.Radiobutton(self.querschnitt_frame, text="Variante 3", variable=self.radiobox_var,
                            value=3).grid(row=3, column=7, columnspan=2, sticky="w", pady=5)
            # Aktualiserung Bib Checkboxen
            self.radiobox_var.trace_add("write",
                                        lambda *args: self.on_any_change())

            # Eingabe Variante 1
            ttk.Label(self.querschnitt_frame, text="b [mm]:").grid(
                row=4, column=1, sticky="w")
            self.b_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.b_entry_1.insert(0, self.b_1)
            self.b_entry_1.grid(row=4, column=2, padx=5, sticky="w")
            self.b_entry_1.bind("<KeyRelease>",
                                self.on_any_change)

            ttk.Label(self.querschnitt_frame, text="h [mm]:").grid(
                row=5, column=1, sticky="w")
            self.h_entry_1 = ttk.Entry(self.querschnitt_frame, width=6)
            self.h_entry_1.insert(0, self.h_1)
            self.h_entry_1.grid(row=5, column=2, padx=5, sticky="w")
            self.h_entry_1.bind("<KeyRelease>",
                                self.on_any_change)

            # Eingabe Variante 2
            ttk.Label(self.querschnitt_frame, text="b [mm]:").grid(
                row=4, column=4, sticky="w")
            self.b_entry_2 = ttk.Entry(self.querschnitt_frame, width=6)
            self.b_entry_2.insert(0, self.b_2)
            self.b_entry_2.grid(row=4, column=5, padx=5, sticky="w")
            self.b_entry_2.bind("<KeyRelease>",
                                self.on_any_change)

            ttk.Label(self.querschnitt_frame, text="h [mm]:").grid(
                row=5, column=4, sticky="w")
            self.h_entry_2 = ttk.Entry(self.querschnitt_frame, width=6)
            self.h_entry_2.insert(0, self.h_2)
            self.h_entry_2.grid(row=5, column=5, padx=5, sticky="w")
            self.h_entry_2.bind("<KeyRelease>",
                                self.on_any_change)

            # Eingabe Variante 3
            ttk.Label(self.querschnitt_frame, text="b [mm]:").grid(
                row=4, column=7, sticky="w")
            self.b_entry_3 = ttk.Entry(self.querschnitt_frame, width=6)
            self.b_entry_3.insert(0, self.b_3)
            self.b_entry_3.grid(row=4, column=8, padx=5, sticky="w")
            self.b_entry_3.bind("<KeyRelease>",
                                self.on_any_change)

            ttk.Label(self.querschnitt_frame, text="h [mm]:").grid(
                row=5, column=7, sticky="w")
            self.h_entry_3 = ttk.Entry(self.querschnitt_frame, width=6)
            self.h_entry_3.insert(0, self.h_3)
            self.h_entry_3.grid(row=5, column=8, padx=5, sticky="w")
            self.h_entry_3.bind("<KeyRelease>",
                                self.on_any_change)

            self.on_any_change()

    def _on_dimension_change(self, event):
        self.b_1 = self.b_entry_1.get()
        self.h_1 = self.h_entry_1.get()
        self.b_2 = self.b_entry_2.get()
        self.h_2 = self.h_entry_2.get()
        self.b_3 = self.b_entry_3.get()
        self.h_3 = self.h_entry_3.get()

    def update_festigkeitsklasse_dropdown(self):
        for i in range(1, 4):
            materialgruppe = self.materialgruppe_var_1.get()  # aktuell gleiche Gruppe
            typ = getattr(self, f"querschnitt_var_{i}").get()
            fest_var = getattr(self, f"festigkeitsklasse_var_{i}")
            fest_combo = getattr(self, f"qs_festigkeit_combo_{i}")
            festigkeiten = self.db.get_festigkeitsklassen(materialgruppe, typ)

            if festigkeiten:
                fest_var.set(festigkeiten[0])
                fest_combo["values"] = festigkeiten
            else:
                fest_var.set("")
                fest_combo["values"] = []

        self.on_any_change()

    def gebrauchstauglichkeit_eingabe(self):
        self.gebrauchstauglichkeit_frame = ttk.LabelFrame(
            self.eingabe_frame, text="Gebrauchstauglichkeit", padding=10)
        self.gebrauchstauglichkeit_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(self.gebrauchstauglichkeit_frame, text="Situation:").grid(
            row=0, column=0, sticky="w")
        self.situation_var = tk.StringVar(value="Allgemein")
        situation_combo = ttk.Combobox(self.gebrauchstauglichkeit_frame, textvariable=self.situation_var,
                                       values=["Allgemein", "Überhöhte, Untergeordnete Bauteile", "Eigene Werte"], width=25, state="readonly")
        situation_combo.grid(row=0, column=1, columnspan=5, sticky="w", pady=2)
        situation_combo.bind("<<ComboboxSelected>>",
                             self.update_gebrauchstauglichkeit_eingabe)
        situation_combo.bind("<<ComboboxSelected>>",
                             self._on_gebrauchstauglichkeit_change, add="+")
        self.w_c_überhoehung_wert = "0,00"
        self.update_gebrauchstauglichkeit_eingabe()

    def _on_w_c_change(self, event):
        # aktuellen Text aus dem Entry holen
        self.w_c_überhoehung_wert = self.w_c_überhoehung.get()
        # Nur Durchbiegungsnachweise neu berechnen
        self._on_gebrauchstauglichkeit_change(event)

    def update_gebrauchstauglichkeit_eingabe(self, event=None):
        logger.debug("🏗️ Gebrauchstauglichkeitsfenster wird aktualisiert")
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
            self.w_fin_grenz_allgemein = 200
            self.w_net_fin_grenz_allgemein = 300

            # Überhöhungseingabe
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_c [mm]:", width=12).grid(
                row=2, column=0, sticky="e", pady=2)
            self.w_c_überhoehung = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_c_überhoehung.insert(0, self.w_c_überhoehung_wert)
            self.w_c_überhoehung.grid(row=2, column=1, sticky="w", pady=2)
            self.w_c_überhoehung.bind("<KeyRelease>", self._on_w_c_change,
                                      self.on_any_change)

            self.on_any_change()
            # Ausgabe Grenzwerte
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_inst:", width=6).grid(
                row=3, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_inst_grenz_allgemein}", width=6).grid(
                row=3, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin:", width=12).grid(
                row=4, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_fin_grenz_allgemein}", width=6).grid(
                row=4, column=1, sticky="w")

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin_net:", width=12).grid(
                row=5, column=0, sticky="w")
            ttk.Label(self.gebrauchstauglichkeit_frame, text=f"L / {self.w_net_fin_grenz_allgemein}", width=6).grid(
                row=5, column=1, sticky="w")

        elif self.situation_var.get() == "Überhöhte, Untergeordnete Bauteile":
            # Set Grenzwerte Überhöhte, Untergeordnete Bauteile
            self.w_inst_grenz_ueberhoeht = 200
            self.w_fin_grenz_ueberhoeht = 150
            self.w_net_fin_grenz_ueberhoeht = 250

            # Überhöhungseingabe
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_c [mm]:", width=12).grid(
                row=2, column=0, sticky="e", pady=2)
            self.w_c_überhoehung = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_c_überhoehung.insert(0, self.w_c_überhoehung_wert)
            self.w_c_überhoehung.grid(row=2, column=1, sticky="w", pady=2)
            self.w_c_überhoehung.bind("<KeyRelease>",
                                      self._on_w_c_change, self.on_any_change)

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
            self.on_any_change()
        elif self.situation_var.get() == "Eigene Werte":
            # Überhöhungseingabe
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_c [mm]:", width=12).grid(
                row=2, column=0, sticky="w")
            self.w_c_überhoehung = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_c_überhoehung.insert(0, self.w_c_überhoehung_wert)
            self.w_c_überhoehung.grid(row=2, column=1, sticky="w")
            self.w_c_überhoehung.bind("<KeyRelease>",
                                      self._on_w_c_change, self.on_any_change)

            # Ausgabe Grenzwerte
            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_inst       -> L / :", width=12).grid(
                row=3, column=0, sticky="w")
            self.w_inst_grenz_eigen = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_inst_grenz_eigen.insert(0, "300")
            self.w_inst_grenz_eigen.grid(row=3, column=1, sticky="w")
            self.w_inst_grenz_eigen.bind("<KeyRelease>",
                                         self._on_gebrauchstauglichkeit_change)

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin         -> L / :", width=12).grid(
                row=4, column=0, sticky="w")
            self.w_fin_grenz_eigen = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_fin_grenz_eigen.insert(0, "200")
            self.w_fin_grenz_eigen.grid(row=4, column=1, sticky="w")
            self.w_fin_grenz_eigen.bind("<KeyRelease>",
                                        self._on_gebrauchstauglichkeit_change)

            ttk.Label(self.gebrauchstauglichkeit_frame, text="w_fin_net -> L / :", width=12).grid(
                row=5, column=0, sticky="w")
            self.w_net_fin_grenz_eigen = ttk.Entry(
                self.gebrauchstauglichkeit_frame, width=6)
            self.w_net_fin_grenz_eigen.insert(0, "300")
            self.w_net_fin_grenz_eigen.grid(
                row=5, column=1, sticky="w")
            self.w_net_fin_grenz_eigen.bind("<KeyRelease>",
                                            self._on_gebrauchstauglichkeit_change)

    def _on_gebrauchstauglichkeit_change(self, event=None):
        """
        Spezieller Callback für Änderungen an Gebrauchstauglichkeits-Parametern.
        Sendet Snapshot mit Flag 'only_deflection_check' an Backend.
        """
        if not self.gui_fertig_geladen:
            return

        # Prüfe, ob bereits vollständige Berechnungsergebnisse vorhanden sind
        if not hasattr(self, 'snapshot') or not self.snapshot:
            logger.info(
                "⚠️ Keine Berechnungsergebnisse vorhanden - führe vollständige Berechnung durch")
            self.on_any_change(event)
            return

        # Prüfe, ob Schnittgrößen vorhanden sind
        if 'Schnittgroessen' not in self.snapshot or not self.snapshot.get('Schnittgroessen'):
            logger.info(
                "⚠️ Keine Schnittgrößen vorhanden - führe vollständige Berechnung durch")
            self.on_any_change(event)
            return

        logger.info(
            "🔄 Nur Durchbiegungsnachweise werden über Backend neu berechnet")

        # Erstelle Snapshot mit allen Daten + Flag für Durchbiegungsberechnung
        input_snapshot = {
            "sprungmass": self.snapshot.get("sprungmass"),
            "lasten": self.snapshot.get("lasten"),
            "spannweiten": self.snapshot.get("spannweiten"),
            "querschnitt": self.snapshot.get("querschnitt"),
            "gebrauchstauglichkeit": self.get_gebrauchstauglichkeit_dict(),  # Aktualisiert!
            "berechnungsmodus": self.snapshot.get("berechnungsmodus", {}),
            # Wichtig: Bestehende Ergebnisse mitgeben
            "Schnittgroessen": self.snapshot.get("Schnittgroessen"),
            "Lastfallkombinationen": self.snapshot.get("Lastfallkombinationen"),
            "GZG_Lastfallkombinationen": self.snapshot.get("GZG_Lastfallkombinationen"),
            # Flag: Nur Durchbiegungsnachweise berechnen
            "calculation_mode": "only_deflection_check"
        }

        # Durch den normalen Service-Flow (saubere Trennung!)
        self.orch.process_snapshot(input_snapshot, self._on_service_done)

    def on_any_change(self, event=None):
        # Debounce-Logik: Bricht den vorherigen Timer ab und startet einen neuen.
        if self._update_timer is not None:
            self.root.after_cancel(self._update_timer)
        self._update_timer = self.root.after(200, self._perform_update)

    def _perform_update(self):
        """Diese Methode wird nach einer kurzen Pause bei den Eingaben ausgeführt und enthält die ursprüngliche Logik von on_any_change."""
        if self.gui_fertig_geladen:
            try:
                self.sprungmass = float(
                    self.sprungmass_entry.get().replace(",", "."))
            except ValueError:
                self.sprungmass = None

            # Eingabe-Snapshot (nur Eingabedaten, ohne Backend-Ergebnisse)
            input_snapshot = {
                "sprungmass": self.sprungmass,
                "lasten":    self.get_lasten_list(),
                "spannweiten": self.get_spannweiten_dict(),
                "querschnitt": self.get_querschnitt_dict(),
                "gebrauchstauglichkeit": self.get_gebrauchstauglichkeit_dict(),
                # Berechnungsmodus hinzufügen
                "berechnungsmodus": {
                    "ec_modus": self.ec_modus_var.get() if self.ec_modus_var else False
                }
            }
            logger.info(f"Input Snapshot: {input_snapshot}")
            # Ladeanimation starten
            self._start_loading_animation()
            # Temporärer Snapshot für Backend-Verarbeitung
            # Der finale Snapshot wird erst in _on_service_done erstellt
            # Zwischenspeichern der Eingabedaten für spätere Verwendung
            self._current_input_data = input_snapshot
            self.orch.process_snapshot(input_snapshot, self._on_service_done)

    def _on_service_done(self, result, errors):
        """Callback, der nach Abschluss des OrchestratorService aufgerufen wird."""
        # Direkte Verarbeitung im Haupt-Thread, um Scope-Probleme zu vermeiden
        def handle_in_main_thread():
            if errors:
                self._stop_loading_animation()
                self.show_error_messages(errors)
                return

            if not result:
                # Keine neuen Ergebnisse (z.B. Hash-Match) - Ladeanimation stoppen
                logger.info(
                    "ℹ️ Keine Änderung erkannt - behalte bestehende Ergebnisse")
                self._stop_loading_animation()
                return

            # Debug: Was kommt vom Backend?
            logger.debug(
                f"Backend result keys: {list(result.keys()) if result else 'None'}")
            if 'Schnittgroessen' in result:
                logger.debug(
                    f"Schnittgroessen keys: {list(result['Schnittgroessen'].keys())}")

            # Finaler Snapshot mit Eingabedaten + Backend-Ergebnissen (direkte Keys, ohne system_memory)
            self.result = result

            # Eingabedaten neu sammeln
            try:
                sprungmass = float(
                    self.sprungmass_entry.get().replace(",", "."))
            except (ValueError, AttributeError):
                sprungmass = None

            # Finaler Snapshot: Eingabedaten + Backend-Ergebnisse
            self.snapshot = {
                # Eingabedaten
                "sprungmass": sprungmass,
                "lasten": self.get_lasten_list(),
                "spannweiten": self.get_spannweiten_dict(),
                "querschnitt": self.get_querschnitt_dict(),
                "gebrauchstauglichkeit": self.get_gebrauchstauglichkeit_dict(),
                # Berechnungsmodus
                "berechnungsmodus": {
                    "ec_modus": self.ec_modus_var.get() if self.ec_modus_var else False
                },
                # Backend-Ergebnisse (direkt)
                'Lastfallkombinationen': result.get('Lastfallkombinationen', {}),
                'GZG_Lastfallkombinationen': result.get('GZG_Lastfallkombinationen', {}),
                'Schnittgroessen': result.get('Schnittgroessen', {}),
                'EC5_Nachweise': result.get('EC5_Nachweise', {})
            }

            # Finaler Snapshot ist jetzt komplett und kann dauerhaft referenziert werden
            print(
                f"✅ Finaler Snapshot erstellt mit {len(self.snapshot)} Keys: {list(self.snapshot.keys())}")

            # Lastkombinationen für Anzeige extrahieren
            self.lastkombis = self.result.get('Lastfallkombinationen', {})

            # Frontend-Orchestrator starten (zeigt alle Ergebnisse sequenziell an)
            logger.debug(
                f"🚀 Starte Frontend-Orchestrator mit finalen snapshot keys: {list(self.snapshot.keys())}")
            self.orch_front.update_all(
                snapshot=self.snapshot,
                lastkombis=self.lastkombis
            )

            # FEEBB-Interface aktualisieren
            self.feebb.close_schnittkraftfenster()
            # Button-Zustand zurücksetzen
            self.schnittgroeßen_anzeige_button.set(False)
            self.feebb.update_maxwerte()

            # Ladeanimation stoppen
            self._stop_loading_animation()

        # Führt den handle-Code im Haupt-Thread aus, um Thread-Konflikte zu vermeiden
        self.eingabe_frame.after(0, handle_in_main_thread)

    def show_error_messages(self, errors: list):
        if self.gui_fertig_geladen:
            import tkinter.messagebox as mb
            mb.showerror("Fehler bei der Verarbeitung", "\n".join(errors))

    def get_spannweiten_dict(self) -> dict:
        logger.debug("Spannweiten Dictionary aktualisiert 📕")
        """Liest alle Spannweiten-Felder (l1, l2, …)."""
        spannweiten = {}
        for eintrag in self.spannweiten_eingaben:
            name = eintrag["name"]
            entry_widget = eintrag["entry"]
            try:
                spannweiten[name] = float(entry_widget.get().replace(",", "."))
            except Exception:
                pass
        return spannweiten

    def get_lasten_list(self) -> list:
        logger.debug("Lasten Dictionary aktualisiert 📘")
        """Liest alle Last-Zeilen ein und liefert sie als List[Dict]."""
        lasten = []
        for row in self.lasten_eingaben:
            try:
                lf = row["lf_combo"].get()
                wert = float(row["wert"].get().replace(",", "."))
                kat = row["detail_combo"].get()
                komm = row["kommentar"].get()
                nkl = int(self.nkl_var.get().strip()[-1])
                eigengewicht = self.eigengewicht_active.get()
                # optional kmod aus DB holen…
                lasten.append({
                    "lastfall": lf, "wert": wert,
                    "kategorie": kat, "kommentar": komm,
                    "nkl": nkl,
                    "eigengewicht": eigengewicht
                })
            except:
                pass
        return lasten

    def get_querschnitt_dict(self) -> dict:
        logger.debug("Querschnitt Dictionary aktualisiert 📙")
        """Liest Querschnitts-Geometrie + Material."""
        variante = self.radiobox_var.get()
        b = float(getattr(self, f"b_entry_{variante}").get())
        h = float(getattr(self, f"h_entry_{variante}").get())
        Iy = b * h**3 / 12
        Wy = Iy / (h/2)
        materialgruppe = self.materialgruppe_var_1.get()
        typ = getattr(self, f"querschnitt_var_{variante}").get()
        festigkeitsklasse = getattr(
            self, f"festigkeitsklasse_var_{variante}").get()
        E = self.db.get_emodul(materialgruppe, typ, festigkeitsklasse)
        return {
            "breite_qs": b, "hoehe_qs": h,
            "I_y": Iy, "W_y": Wy,
            "materialgruppe": materialgruppe, "typ": typ,
            "festigkeitsklasse": festigkeitsklasse, "E": E
        }

    def get_gebrauchstauglichkeit_dict(self) -> dict:
        logger.debug("Gebrauchstauglichkeit Dictionary aktualisiert 📚")
        """Liest Gebrauchstauglichkeitsdaten."""
        situation = self.situation_var.get()
        w_c = float(self.w_c_überhoehung_wert.replace(",", "."))
        if situation == "Allgemein":
            w_inst_grenz = self.w_inst_grenz_allgemein
            w_fin_grenz = self.w_fin_grenz_allgemein
            w_net_fin_grenz = self.w_net_fin_grenz_allgemein
        elif situation == "Überhöhte, Untergeordnete Bauteile":
            w_inst_grenz = self.w_inst_grenz_ueberhoeht
            w_fin_grenz = self.w_fin_grenz_ueberhoeht
            w_net_fin_grenz = self.w_net_fin_grenz_ueberhoeht
        else:
            w_inst_grenz = float(self.w_inst_grenz_eigen.get())
            w_fin_grenz = float(self.w_fin_grenz_eigen.get())
            w_net_fin_grenz = float(self.w_net_fin_grenz_eigen.get())
        return {
            "situation": situation,
            "w_c": w_c,
            "w_inst_grenz": w_inst_grenz,
            "w_fin_grenz": w_fin_grenz,
            "w_net_fin_grenz": w_net_fin_grenz
        }

    def on_querschnitt_auswahl(self, event=None):
        self.update_festigkeitsklasse_dropdown()
        self.on_any_change()

    def _start_loading_animation(self):
        """Startet die Ladeanimation."""
        if not self.loading_label:
            return

        # Bestimme Modus-Text
        ec_modus = self.ec_modus_var.get() if self.ec_modus_var else False
        modus_text = "EC-Kombinatorik" if ec_modus else "Volllast"

        self.loading_animation_running = True
        self.loading_label.config(text=f"⏳ Berechnung läuft ({modus_text})...")
        self._animate_loading()

    def _animate_loading(self):
        """Animiert den Ladeindikator mit rotierenden Symbolen."""
        if not self.loading_animation_running or not self.loading_label:
            return

        symbols = ["⏳", "⌛"]
        current_text = self.loading_label.cget("text")

        # Extrahiere Modus aus aktuellem Text
        if "(" in current_text:
            modus_part = current_text[current_text.find(
                "("):current_text.find(")")+1]
        else:
            modus_part = ""

        # Rotiere Symbol
        if "⏳" in current_text:
            new_symbol = "⌛"
        else:
            new_symbol = "⏳"

        self.loading_label.config(
            text=f"{new_symbol} Berechnung läuft {modus_part}...")

        # Wiederhole Animation nach 500ms
        if self.loading_animation_running:
            self.root.after(500, self._animate_loading)

    def _stop_loading_animation(self):
        """Stoppt die Ladeanimation."""
        self.loading_animation_running = False
        if self.loading_label:
            self.loading_label.config(text="✅ Berechnung abgeschlossen")
            # Nach 2 Sekunden Text löschen
            self.root.after(2000, lambda: self.loading_label.config(
                text="") if self.loading_label else None)


def starte_gui():
    print("📦 Starte Programm...")
    root = tk.Tk()
    app = Eingabemaske(root)
    print("🖼️ GUI läuft...")
    root.mainloop()
    print("❌ Programm wurde beendet!")


if __name__ == '__main__':
    starte_gui()
