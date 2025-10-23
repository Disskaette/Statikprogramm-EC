"""
Basis-Interface für alle Berechnungsmodule.
Definiert die Schnittstelle, die jedes Modul implementieren muss.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import tkinter as tk


class BaseModule(ABC):
    """
    Abstract Base Class für alle Berechnungsmodule.
    
    Jedes Modul (Durchlaufträger, Brandschutz, Auflager, etc.) 
    muss diese Schnittstelle implementieren.
    """
    
    def __init__(self, eingabemaske_ref):
        """
        Args:
            eingabemaske_ref: Referenz zur Haupt-Eingabemaske (für DB, etc.)
        """
        self.eingabemaske = eingabemaske_ref
        self.gui_frame: Optional[tk.Frame] = None
        self._data_changed_callback: Optional[callable] = None
    
    # ========== Pflicht-Methoden (müssen überschrieben werden) ==========
    
    @abstractmethod
    def get_module_id(self) -> str:
        """
        Gibt eindeutige Modul-ID zurück (z.B. 'durchlauftraeger').
        
        Returns:
            Eindeutige Modul-ID (lowercase, keine Leerzeichen)
        """
        pass
    
    @abstractmethod
    def get_display_name(self) -> str:
        """
        Gibt Anzeigenamen für Tabs zurück (z.B. 'Durchlaufträger').
        
        Returns:
            Benutzerfreundlicher Name für UI
        """
        pass
    
    @abstractmethod
    def create_gui(self, parent_frame: tk.Frame) -> tk.Frame:
        """
        Erstellt die GUI des Moduls.
        
        Args:
            parent_frame: Eltern-Frame, in dem die GUI platziert wird
            
        Returns:
            Der erstellte Frame mit der Modul-GUI
        """
        pass
    
    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """
        Sammelt alle Eingabedaten des Moduls.
        
        Returns:
            Dictionary mit allen Eingabedaten (für Serialisierung)
        """
        pass
    
    @abstractmethod
    def set_data(self, data: Dict[str, Any]):
        """
        Lädt Daten in das Modul (z.B. nach dem Öffnen einer Position).
        
        Args:
            data: Dictionary mit Modul-Daten
        """
        pass
    
    @abstractmethod
    def get_results(self) -> Optional[Dict[str, Any]]:
        """
        Gibt Berechnungsergebnisse zurück.
        
        Returns:
            Dictionary mit Ergebnissen oder None, falls noch keine Berechnung
        """
        pass
    
    # ========== Optionale Methoden (können überschrieben werden) ==========
    
    def is_available(self) -> bool:
        """
        Prüft, ob das Modul verfügbar/aktiviert ist.
        
        Returns:
            True wenn Modul bereit ist, False sonst
        """
        return True
    
    def get_icon(self) -> Optional[str]:
        """
        Gibt Icon-Path für Tab zurück (optional).
        
        Returns:
            Pfad zu Icon-Datei oder None
        """
        return None
    
    def validate_inputs(self) -> tuple[bool, str]:
        """
        Validiert die Eingaben des Moduls.
        
        Returns:
            Tuple (is_valid, error_message)
        """
        return (True, "")
    
    def on_module_activated(self):
        """
        Wird aufgerufen, wenn das Modul aktiviert wird (Tab-Wechsel).
        Kann genutzt werden, um z.B. Daten zu aktualisieren.
        """
        pass
    
    def on_module_deactivated(self):
        """
        Wird aufgerufen, wenn das Modul deaktiviert wird (Tab-Wechsel).
        Kann genutzt werden, um z.B. Auto-Save auszulösen.
        """
        pass
    
    def on_calculation_complete(self, results: Dict[str, Any]):
        """
        Wird aufgerufen, wenn eine Berechnung abgeschlossen wurde.
        
        Args:
            results: Berechnungsergebnisse vom Backend
        """
        pass
    
    def cleanup(self):
        """
        Aufräumen beim Schließen des Moduls.
        Kann überschrieben werden, um Ressourcen freizugeben.
        """
        if self.gui_frame:
            self.gui_frame.destroy()
            self.gui_frame = None
    
    # ========== Utility-Methoden ==========
    
    def register_data_changed_callback(self, callback: callable):
        """
        Registriert einen Callback, der bei Datenänderungen aufgerufen wird.
        
        Args:
            callback: Funktion die aufgerufen wird bei Änderungen
        """
        self._data_changed_callback = callback
    
    def notify_data_changed(self):
        """
        Benachrichtigt das System über Datenänderungen.
        Sollte von Modulen aufgerufen werden, wenn sich Daten ändern.
        """
        if self._data_changed_callback:
            self._data_changed_callback()
    
    def get_gui_frame(self) -> Optional[tk.Frame]:
        """
        Gibt den GUI-Frame des Moduls zurück.
        
        Returns:
            Frame oder None
        """
        return self.gui_frame
    
    # ========== Hilfs-Eigenschaften ==========
    
    @property
    def module_id(self) -> str:
        """Shortcut für get_module_id()"""
        return self.get_module_id()
    
    @property
    def display_name(self) -> str:
        """Shortcut für get_display_name()"""
        return self.get_display_name()
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id='{self.module_id}' name='{self.display_name}'>"
