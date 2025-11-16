"""
Tab-Manager für Module (Level 2).
Verwaltet verschiedene Berechnungsmodule innerhalb einer Position.
"""

import tkinter as tk
import customtkinter as ctk
import logging
from pathlib import Path
from typing import Dict, Optional
from backend.project import PositionModel
from frontend.modules.module_registry import get_registry
from frontend.modules.base_module import BaseModule

logger = logging.getLogger(__name__)


class ModuleTabManager(ctk.CTkFrame):
    """Verwaltet Tabs für verschiedene Module (Durchlaufträger, Brandschutz, etc.)"""
    
    def __init__(self, parent, position_model: PositionModel, position_file: Path, app_ref):
        """
        Args:
            parent: Eltern-Widget
            position_model: Position-Datenmodell
            position_file: Pfad zur Position-Datei
            app_ref: Referenz zur Hauptanwendung (für DB, etc.)
        """
        super().__init__(parent)
        
        self.position_model = position_model
        self.position_file = position_file
        self.app_ref = app_ref
        
        # Modul-Instanzen
        self.module_instances: Dict[str, BaseModule] = {}
        self.module_tab_names: Dict[str, str] = {}  # module_id -> tab_name
        
        # Tabview erstellen
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True)
        
        # Tab-Wechsel-Callback
        self.tabview.configure(command=self._on_tab_changed)
        
        # Module laden
        self._load_modules()
        
        # Aktives Modul setzen
        self._activate_module(position_model.active_module)
        
        logger.info(f"ModuleTabManager initialisiert für Position: {position_model.get_display_name()}")
    
    def _load_modules(self):
        """Lädt alle verfügbaren Module als Tabs"""
        registry = get_registry()
        available_modules = registry.get_all_modules(enabled_only=True)
        
        for mod_info in available_modules:
            module_id = mod_info["id"]
            module_name = mod_info["name"]
            
            # Modul-Instanz erstellen
            module_instance = registry.create_module_instance(module_id, self.app_ref)
            
            if not module_instance:
                logger.warning(f"Konnte Modul nicht instanziieren: {module_id}")
                continue
            
            # Tab erstellen
            self.tabview.add(module_name)
            module_frame = self.tabview.tab(module_name)
            
            try:
                module_instance.create_gui(module_frame)
            except Exception as e:
                logger.error(f"Fehler beim Erstellen der GUI für {module_id}: {e}")
                continue
            
            # Daten laden (falls vorhanden)
            module_data = self.position_model.get_module_data(module_id)
            if module_data:
                try:
                    module_instance.set_data(module_data)
                except Exception as e:
                    logger.error(f"Fehler beim Laden der Daten für {module_id}: {e}")
            
            # Speichern
            self.module_instances[module_id] = module_instance
            self.module_tab_names[module_id] = module_name
            
            logger.debug(f"Modul geladen: {module_id}")
    
    def _activate_module(self, module_id: str):
        """
        Aktiviert ein bestimmtes Modul (Tab).
        
        Args:
            module_id: ID des zu aktivierenden Moduls
        """
        if module_id not in self.module_tab_names:
            logger.warning(f"Modul nicht gefunden: {module_id}")
            return
        
        # Tab auswählen
        tab_name = self.module_tab_names[module_id]
        self.tabview.set(tab_name)
        
        # on_module_activated aufrufen
        if module_id in self.module_instances:
            try:
                self.module_instances[module_id].on_module_activated()
            except Exception as e:
                logger.error(f"Fehler in on_module_activated für {module_id}: {e}")
    
    def _on_tab_changed(self):
        """Callback wenn Modul-Tab gewechselt wird"""
        current_tab = self.tabview.get()
        
        if not current_tab:
            return
        
        # Finde Modul-ID für diesen Tab
        current_module_id = None
        for mod_id, tab_name in self.module_tab_names.items():
            if tab_name == current_tab:
                current_module_id = mod_id
                break
        
        if current_module_id:
            # Aktualisiere active_module im Model
            self.position_model.active_module = current_module_id
            
            # Callbacks
            if current_module_id in self.module_instances:
                try:
                    self.module_instances[current_module_id].on_module_activated()
                except Exception as e:
                    logger.error(f"Fehler in on_module_activated: {e}")
            
            logger.debug(f"Modul-Tab gewechselt zu: {current_module_id}")
    
    def collect_data_to_model(self, position_model: Optional[PositionModel] = None):
        """
        Sammelt Daten von allen Modulen und speichert sie im Model.
        
        Args:
            position_model: Optional anderes Model (default: self.position_model)
        """
        if position_model is None:
            position_model = self.position_model
        
        for module_id, module_instance in self.module_instances.items():
            try:
                module_data = module_instance.get_data()
                
                # Ergebnisse hinzufügen (falls vorhanden)
                results = module_instance.get_results()
                if results:
                    if module_data is None:
                        module_data = {}
                    module_data["results"] = results
                
                position_model.set_module_data(module_id, module_data)
                
            except Exception as e:
                logger.error(f"Fehler beim Sammeln der Daten von {module_id}: {e}")
        
        logger.debug("Modul-Daten gesammelt")
    
    def get_active_module(self) -> Optional[BaseModule]:
        """
        Gibt die Instanz des aktuell aktiven Moduls zurück.
        
        Returns:
            BaseModule-Instanz oder None
        """
        current_tab = self.tabview.get()
        
        if not current_tab:
            return None
        
        for mod_id, tab_name in self.module_tab_names.items():
            if tab_name == current_tab:
                return self.module_instances.get(mod_id)
        
        return None
    
    def get_module_instance(self, module_id: str) -> Optional[BaseModule]:
        """
        Gibt die Instanz eines bestimmten Moduls zurück.
        
        Args:
            module_id: ID des Moduls
            
        Returns:
            BaseModule-Instanz oder None
        """
        return self.module_instances.get(module_id)
    
    def cleanup(self):
        """Räumt alle Modul-Ressourcen auf"""
        for module_instance in self.module_instances.values():
            try:
                module_instance.cleanup()
            except Exception as e:
                logger.error(f"Fehler beim Cleanup: {e}")
        
        self.module_instances.clear()
        self.module_tab_names.clear()
        
        logger.debug("ModuleTabManager aufgeräumt")
