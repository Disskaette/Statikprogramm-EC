"""
Verwaltung von Anwendungseinstellungen und Recent Files.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class SettingsManager:
    """Verwaltet persistente Anwendungseinstellungen"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Args:
            config_dir: Verzeichnis für Konfigurationsdateien.
                       Default: ./config relativ zum Skript
        """
        if config_dir is None:
            script_dir = Path(__file__).parent.parent.parent
            config_dir = script_dir / "config"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.settings_file = self.config_dir / "settings.json"
        self.settings = self._load_settings()
        
        logger.info(f"SettingsManager initialisiert: {self.config_dir}")
    
    def _load_settings(self) -> Dict[str, Any]:
        """Lädt Einstellungen aus Datei oder erstellt Defaults"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Einstellungen: {e}")
                return self._get_default_settings()
        else:
            return self._get_default_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Gibt Standard-Einstellungen zurück"""
        return {
            "recent_projects": [],
            "last_opened_project": None,
            "last_opened_position": None,
            "window_geometry": "1400x900",
            "ui_preferences": {
                "explorer_width": 250,
                "theme": "default",
                "show_welcome_screen": True
            },
            "auto_save": {
                "enabled": True,
                "interval_seconds": 300  # 5 Minuten
            }
        }
    
    def save(self):
        """Speichert aktuelle Einstellungen in Datei"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.debug("Einstellungen gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Einstellungen: {e}")
    
    # ========== Recent Projects ==========
    
    def add_recent_project(self, project_path: str):
        """
        Fügt ein Projekt zur Recent-Liste hinzu.
        
        Args:
            project_path: Absoluter Pfad zum Projekt
        """
        recent = self.settings.get("recent_projects", [])
        
        # Entferne Duplikate (falls vorhanden)
        if project_path in recent:
            recent.remove(project_path)
        
        # An Anfang einfügen
        recent.insert(0, project_path)
        
        # Maximal 10 behalten
        self.settings["recent_projects"] = recent[:10]
        self.save()
    
    def get_recent_projects(self) -> List[str]:
        """
        Gibt Liste der zuletzt geöffneten Projekte zurück.
        
        Returns:
            Liste von Projekt-Pfaden
        """
        return self.settings.get("recent_projects", [])
    
    def clear_recent_projects(self):
        """Löscht die Recent-Projects-Liste"""
        self.settings["recent_projects"] = []
        self.save()
    
    # ========== Last Opened ==========
    
    def set_last_opened_project(self, project_path: Optional[str]):
        """Setzt das zuletzt geöffnete Projekt"""
        self.settings["last_opened_project"] = project_path
        self.save()
    
    def get_last_opened_project(self) -> Optional[str]:
        """Gibt das zuletzt geöffnete Projekt zurück"""
        return self.settings.get("last_opened_project")
    
    def set_last_opened_position(self, position_path: Optional[str]):
        """Setzt die zuletzt geöffnete Position"""
        self.settings["last_opened_position"] = position_path
        self.save()
    
    def get_last_opened_position(self) -> Optional[str]:
        """Gibt die zuletzt geöffnete Position zurück"""
        return self.settings.get("last_opened_position")
    
    # ========== UI Preferences ==========
    
    def get_window_geometry(self) -> str:
        """Gibt die gespeicherte Fenstergeometrie zurück"""
        return self.settings.get("window_geometry", "1400x900")
    
    def set_window_geometry(self, geometry: str):
        """Speichert die Fenstergeometrie"""
        self.settings["window_geometry"] = geometry
        self.save()
    
    def get_explorer_width(self) -> int:
        """Gibt die Breite des Projekt-Explorers zurück"""
        return self.settings.get("ui_preferences", {}).get("explorer_width", 250)
    
    def set_explorer_width(self, width: int):
        """Setzt die Breite des Projekt-Explorers"""
        if "ui_preferences" not in self.settings:
            self.settings["ui_preferences"] = {}
        self.settings["ui_preferences"]["explorer_width"] = width
        self.save()
    
    def should_show_welcome_screen(self) -> bool:
        """Prüft, ob der Welcome-Screen angezeigt werden soll"""
        return self.settings.get("ui_preferences", {}).get("show_welcome_screen", True)
    
    def set_show_welcome_screen(self, show: bool):
        """Setzt, ob der Welcome-Screen angezeigt werden soll"""
        if "ui_preferences" not in self.settings:
            self.settings["ui_preferences"] = {}
        self.settings["ui_preferences"]["show_welcome_screen"] = show
        self.save()
    
    # ========== Auto-Save ==========
    
    def is_auto_save_enabled(self) -> bool:
        """Prüft, ob Auto-Save aktiviert ist"""
        return self.settings.get("auto_save", {}).get("enabled", True)
    
    def get_auto_save_interval(self) -> int:
        """Gibt das Auto-Save-Intervall in Sekunden zurück"""
        return self.settings.get("auto_save", {}).get("interval_seconds", 300)
    
    # ========== Generic Getter/Setter ==========
    
    def get(self, key: str, default: Any = None) -> Any:
        """Generischer Getter für beliebige Settings"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Generischer Setter für beliebige Settings"""
        self.settings[key] = value
        self.save()
