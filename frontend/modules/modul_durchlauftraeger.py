"""
Durchlaufträger-Modul (vollständige Integration der Eingabemaske).
Wrapper um die bestehende Eingabemaske-Klasse.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
import logging

from .base_module import BaseModule
from frontend.gui.eingabemaske_wrapper import EingabemaskeWrapper

logger = logging.getLogger(__name__)


class ModulDurchlauftraeger(BaseModule):
    """
    Durchlaufträger-Modul mit vollständiger Eingabemaske.
    Wrapper um die bestehende Eingabemaske-Klasse.
    """
    
    def __init__(self, eingabemaske_ref):
        super().__init__(eingabemaske_ref)
        
        # Eingabemaske-Wrapper (wird später erstellt)
        self.eingabemaske_wrapper: Optional[EingabemaskeWrapper] = None
    
    def get_module_id(self) -> str:
        return "durchlauftraeger"
    
    def get_display_name(self) -> str:
        return "Durchlaufträger"
    
    def create_gui(self, parent_frame: tk.Frame) -> tk.Frame:
        """Erstellt die vollständige Eingabemaske-GUI"""
        
        self.gui_frame = ttk.Frame(parent_frame)
        self.gui_frame.pack(fill="both", expand=True)
        
        logger.info(f"🔨 create_gui aufgerufen, parent_frame: {parent_frame}")
        logger.info(f"🔨 gui_frame erstellt: {self.gui_frame}")
        
        # Eingabemaske-Wrapper erstellen
        # (angepasste Version ohne eigenes root-Fenster)
        try:
            logger.info("🔨 Erstelle EingabemaskeWrapper...")
            self.eingabemaske_wrapper = EingabemaskeWrapper(
                parent=self.gui_frame,
                db=self.eingabemaske.db if hasattr(self.eingabemaske, 'db') else None
            )
            
            logger.info("✅ Eingabemaske-GUI erfolgreich erstellt")
            logger.info(f"✅ Wrapper hat {len(self.gui_frame.winfo_children())} Kinder")
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Eingabemaske-GUI: {e}")
            
            # Fallback: Fehler anzeigen
            error_frame = ttk.Frame(self.gui_frame)
            error_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            ttk.Label(error_frame, 
                     text="⚠️ Fehler beim Laden der Eingabemaske",
                     font=("", 12, "bold"),
                     foreground="red").pack(pady=10)
            
            ttk.Label(error_frame, 
                     text=str(e),
                     font=("", 10)).pack(pady=5)
        
        return self.gui_frame
    
    def get_data(self) -> Dict[str, Any]:
        """
        Sammelt alle Eingabedaten der Eingabemaske.
        
        Returns:
            Dictionary mit allen Eingabedaten
        """
        if not self.eingabemaske_wrapper:
            return {}
        
        try:
            return self.eingabemaske_wrapper.get_all_data()
        except Exception as e:
            logger.error(f"Fehler beim Sammeln der Daten: {e}")
            return {}
    
    def set_data(self, data: Dict[str, Any]):
        """
        Lädt Daten in die Eingabemaske.
        
        Args:
            data: Dictionary mit Eingabedaten
        """
        if not self.eingabemaske_wrapper or not data:
            return
        
        try:
            self.eingabemaske_wrapper.set_all_data(data)
            logger.info("Daten in Eingabemaske geladen")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Daten: {e}")
    
    def get_results(self) -> Optional[Dict[str, Any]]:
        """
        Gibt Berechnungsergebnisse zurück.
        
        Returns:
            Dictionary mit Ergebnissen oder None
        """
        if not self.eingabemaske_wrapper:
            return None
        
        try:
            return self.eingabemaske_wrapper.get_results()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Ergebnisse: {e}")
            return None
    
    def validate_inputs(self) -> tuple[bool, str]:
        """
        Validiert die Eingaben.
        
        Returns:
            Tuple (is_valid, error_message)
        """
        if not self.eingabemaske_wrapper:
            return (False, "Eingabemaske nicht initialisiert")
        
        # TODO: Validierung implementieren
        return (True, "")
    
    def on_module_activated(self):
        """Wird aufgerufen, wenn das Modul aktiviert wird"""
        logger.debug("Durchlaufträger-Modul aktiviert")
        
        # Berechnungen aktualisieren (falls nötig)
        if self.eingabemaske_wrapper:
            try:
                self.eingabemaske_wrapper.refresh_display()
            except Exception as e:
                logger.error(f"Fehler beim Aktualisieren der Anzeige: {e}")
    
    def on_module_deactivated(self):
        """Wird aufgerufen, wenn das Modul deaktiviert wird"""
        logger.debug("Durchlaufträger-Modul deaktiviert")
        
        # Auto-Save-Trigger
        self.notify_data_changed()
    
    def cleanup(self):
        """Räumt Ressourcen auf"""
        if self.eingabemaske_wrapper:
            try:
                self.eingabemaske_wrapper.cleanup()
            except Exception as e:
                logger.error(f"Fehler beim Cleanup: {e}")
            
            self.eingabemaske_wrapper = None
        
        super().cleanup()
