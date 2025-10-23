"""
Zentrale Registry für alle verfügbaren Berechnungsmodule.
Verwaltet Modul-Metadaten und Instanziierung.
"""

import logging
from typing import Dict, List, Type, Optional
from .base_module import BaseModule

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """Singleton-Registry für alle verfügbaren Module"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._modules: Dict[str, Dict] = {}
        self._module_classes: Dict[str, Type[BaseModule]] = {}
        self._initialized = True
        
        logger.info("ModuleRegistry initialisiert")
    
    def register_module(self, 
                       module_class: Type[BaseModule],
                       enabled: bool = True,
                       order: int = 999,
                       category: str = "Berechnungen"):
        """
        Registriert ein Modul in der Registry.
        
        Args:
            module_class: Klasse des Moduls (muss BaseModule erben)
            enabled: Ob das Modul standardmäßig aktiviert ist
            order: Sortierreihenfolge in Tabs (niedrigere Zahlen = weiter vorne)
            category: Kategorie für Gruppierung (optional)
        """
        if not issubclass(module_class, BaseModule):
            raise TypeError(f"{module_class} muss von BaseModule erben")
        
        # Temporäre Instanz erstellen, um Metadaten zu lesen
        # (wird später für echte Instanziierung verworfen)
        try:
            temp_instance = module_class(eingabemaske_ref=None)
            module_id = temp_instance.get_module_id()
            display_name = temp_instance.get_display_name()
        except Exception as e:
            logger.error(f"Fehler beim Registrieren von {module_class}: {e}")
            return
        
        self._modules[module_id] = {
            "id": module_id,
            "name": display_name,
            "class_name": module_class.__name__,
            "enabled": enabled,
            "order": order,
            "category": category
        }
        
        self._module_classes[module_id] = module_class
        
        logger.info(f"Modul registriert: {module_id} ({display_name})")
    
    def get_module_class(self, module_id: str) -> Optional[Type[BaseModule]]:
        """
        Gibt die Klasse eines Moduls zurück.
        
        Args:
            module_id: ID des Moduls
            
        Returns:
            Modul-Klasse oder None
        """
        return self._module_classes.get(module_id)
    
    def create_module_instance(self, module_id: str, eingabemaske_ref) -> Optional[BaseModule]:
        """
        Erstellt eine neue Instanz eines Moduls.
        
        Args:
            module_id: ID des Moduls
            eingabemaske_ref: Referenz zur Hauptanwendung
            
        Returns:
            Modul-Instanz oder None
        """
        module_class = self.get_module_class(module_id)
        if module_class:
            try:
                instance = module_class(eingabemaske_ref)
                logger.debug(f"Modul-Instanz erstellt: {module_id}")
                return instance
            except Exception as e:
                logger.error(f"Fehler beim Instanziieren von {module_id}: {e}")
                return None
        else:
            logger.warning(f"Modul nicht gefunden: {module_id}")
            return None
    
    def get_all_modules(self, enabled_only: bool = False) -> List[Dict]:
        """
        Gibt Liste aller registrierten Module zurück.
        
        Args:
            enabled_only: Nur aktivierte Module zurückgeben
            
        Returns:
            Liste von Modul-Metadaten (sortiert nach order)
        """
        modules = list(self._modules.values())
        
        if enabled_only:
            modules = [m for m in modules if m["enabled"]]
        
        # Sortiere nach order
        modules.sort(key=lambda x: x["order"])
        
        return modules
    
    def is_module_available(self, module_id: str) -> bool:
        """
        Prüft, ob ein Modul verfügbar ist.
        
        Args:
            module_id: ID des Moduls
            
        Returns:
            True wenn verfügbar, False sonst
        """
        return module_id in self._modules and self._modules[module_id]["enabled"]
    
    def get_module_info(self, module_id: str) -> Optional[Dict]:
        """
        Gibt Metadaten eines Moduls zurück.
        
        Args:
            module_id: ID des Moduls
            
        Returns:
            Dictionary mit Modul-Informationen oder None
        """
        return self._modules.get(module_id)
    
    def enable_module(self, module_id: str):
        """Aktiviert ein Modul"""
        if module_id in self._modules:
            self._modules[module_id]["enabled"] = True
            logger.info(f"Modul aktiviert: {module_id}")
    
    def disable_module(self, module_id: str):
        """Deaktiviert ein Modul"""
        if module_id in self._modules:
            self._modules[module_id]["enabled"] = False
            logger.info(f"Modul deaktiviert: {module_id}")


# Globale Singleton-Instanz
registry = ModuleRegistry()


def get_registry() -> ModuleRegistry:
    """Gibt die globale Registry-Instanz zurück"""
    return registry
