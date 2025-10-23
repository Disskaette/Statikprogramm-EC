"""
Datenmodell für eine statische Position.
Kapselt alle Eingaben und Ergebnisse einer Position.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime


@dataclass
class PositionModel:
    """Datenmodell für eine statische Berechnungsposition"""
    
    # Metadaten
    position_nummer: str = ""
    position_name: str = "Neue Position"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Aktives Modul (für Tab-Auswahl)
    active_module: str = "durchlauftraeger"
    
    # Modul-Daten (jedes Modul speichert seine eigenen Daten)
    modules: Dict[str, Optional[Dict[str, Any]]] = field(default_factory=lambda: {
        "durchlauftraeger": None,
        "brandschutz": None,
        "auflager": None
    })
    
    def to_dict(self) -> dict:
        """Konvertiert Position in Dictionary für Serialisierung"""
        return {
            "position_nummer": self.position_nummer,
            "position_name": self.position_name,
            "created": self.created,
            "last_modified": datetime.now().isoformat(),
            "active_module": self.active_module,
            "modules": self.modules
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PositionModel':
        """Erstellt Position aus Dictionary"""
        return cls(
            position_nummer=data.get("position_nummer", ""),
            position_name=data.get("position_name", "Neue Position"),
            created=data.get("created", datetime.now().isoformat()),
            last_modified=data.get("last_modified", datetime.now().isoformat()),
            active_module=data.get("active_module", "durchlauftraeger"),
            modules=data.get("modules", {})
        )
    
    def get_module_data(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Gibt die Daten eines bestimmten Moduls zurück"""
        return self.modules.get(module_id)
    
    def set_module_data(self, module_id: str, data: Dict[str, Any]):
        """Setzt die Daten eines bestimmten Moduls"""
        self.modules[module_id] = data
        self.last_modified = datetime.now().isoformat()
    
    def get_display_name(self) -> str:
        """Gibt einen schönen Anzeigenamen zurück"""
        if self.position_nummer:
            return f"{self.position_nummer} - {self.position_name}"
        return self.position_name
    
    def get_filename(self) -> str:
        """Generiert einen Dateinamen für diese Position"""
        # Sichere Dateinamen (keine Sonderzeichen)
        safe_nummer = self.position_nummer.replace(".", "_").replace("/", "_")
        safe_name = "".join(c for c in self.position_name if c.isalnum() or c in (' ', '_', '-'))
        safe_name = safe_name.replace(" ", "_")
        
        if safe_nummer:
            return f"Position_{safe_nummer}_{safe_name}.json"
        return f"Position_{safe_name}.json"
