"""
Vereinfachtes Durchlaufträger-Modul für MVP-Test.
Wird später durch vollständige Integration der eingabemaske.py ersetzt.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
from .base_module import BaseModule


class ModulDurchlauftraegerSimple(BaseModule):
    """Vereinfachtes Durchlaufträger-Modul (MVP)"""
    
    def __init__(self, eingabemaske_ref):
        super().__init__(eingabemaske_ref)
        
        # Eingabe-Widgets (Referenzen)
        self.sprungmass_entry = None
        self.feldanzahl_var = None
        self.eigengewicht_entry = None
        
    def get_module_id(self) -> str:
        return "durchlauftraeger"
    
    def get_display_name(self) -> str:
        return "Durchlaufträger"
    
    def create_gui(self, parent_frame: tk.Frame) -> tk.Frame:
        """Erstellt eine vereinfachte GUI"""
        
        self.gui_frame = ttk.Frame(parent_frame)
        self.gui_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Info-Label
        info_frame = ttk.LabelFrame(self.gui_frame, text="ℹ️ Hinweis", padding=10)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(info_frame, 
                 text="Dies ist eine vereinfachte Demo-Version.\n"
                      "Die vollständige Integration der Eingabemaske kommt als nächstes.",
                 font=("", 10)).pack()
        
        # Systemeingabe
        system_frame = ttk.LabelFrame(self.gui_frame, text="Systemeingabe", padding=10)
        system_frame.pack(fill="x", pady=5)
        
        ttk.Label(system_frame, text="Sprungmaß e [m]:").grid(row=0, column=0, sticky="w")
        self.sprungmass_entry = ttk.Entry(system_frame, width=10)
        self.sprungmass_entry.insert(0, "1.00")
        self.sprungmass_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(system_frame, text="Anzahl Felder:").grid(row=1, column=0, sticky="w")
        self.feldanzahl_var = tk.IntVar(value=2)
        spinbox = ttk.Spinbox(system_frame, from_=1, to=5, 
                             textvariable=self.feldanzahl_var, width=8)
        spinbox.grid(row=1, column=1, padx=5, pady=2)
        
        # Lasten
        lasten_frame = ttk.LabelFrame(self.gui_frame, text="Lasten", padding=10)
        lasten_frame.pack(fill="x", pady=5)
        
        ttk.Label(lasten_frame, text="Eigengewicht [kN/m²]:").grid(row=0, column=0, sticky="w")
        self.eigengewicht_entry = ttk.Entry(lasten_frame, width=10)
        self.eigengewicht_entry.insert(0, "7.41")
        self.eigengewicht_entry.grid(row=0, column=1, padx=5, pady=2)
        
        # Ergebnisse (Placeholder)
        ergebnis_frame = ttk.LabelFrame(self.gui_frame, text="Ergebnisse", padding=10)
        ergebnis_frame.pack(fill="both", expand=True, pady=5)
        
        ttk.Label(ergebnis_frame, 
                 text="Die vollständige Berechnung und Anzeige\n"
                      "wird in der finalen Version integriert.",
                 font=("", 9), foreground="gray").pack(pady=20)
        
        # Button
        ttk.Button(ergebnis_frame, 
                  text="🔬 Berechnung starten",
                  command=self._run_calculation).pack(pady=5)
        
        self.result_label = ttk.Label(ergebnis_frame, text="", font=("", 10, "bold"))
        self.result_label.pack(pady=10)
        
        return self.gui_frame
    
    def get_data(self) -> Dict[str, Any]:
        """Sammelt Eingabedaten"""
        try:
            return {
                "sprungmass": float(self.sprungmass_entry.get().replace(",", ".")),
                "feldanzahl": self.feldanzahl_var.get(),
                "eigengewicht": float(self.eigengewicht_entry.get().replace(",", ".")),
            }
        except Exception as e:
            return {
                "sprungmass": 1.0,
                "feldanzahl": 2,
                "eigengewicht": 7.41
            }
    
    def set_data(self, data: Dict[str, Any]):
        """Lädt Daten in die GUI"""
        if not self.gui_frame:
            return
        
        if "sprungmass" in data:
            self.sprungmass_entry.delete(0, tk.END)
            self.sprungmass_entry.insert(0, str(data["sprungmass"]))
        
        if "feldanzahl" in data:
            self.feldanzahl_var.set(data["feldanzahl"])
        
        if "eigengewicht" in data:
            self.eigengewicht_entry.delete(0, tk.END)
            self.eigengewicht_entry.insert(0, str(data["eigengewicht"]))
    
    def get_results(self) -> Optional[Dict[str, Any]]:
        """Gibt Dummy-Ergebnisse zurück"""
        return {
            "max_moment": 15.5,
            "max_querkraft": 12.3,
            "max_durchbiegung": 2.1
        }
    
    def _run_calculation(self):
        """Dummy-Berechnung"""
        data = self.get_data()
        
        # Dummy-Berechnung
        result_text = (
            f"✅ Berechnung abgeschlossen!\n\n"
            f"Sprungmaß: {data['sprungmass']} m\n"
            f"Felder: {data['feldanzahl']}\n"
            f"Last: {data['eigengewicht']} kN/m²"
        )
        
        self.result_label.config(text=result_text)
        
        # Callback für Datenänderungen
        self.notify_data_changed()
