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
            # Jetzt mit Metadaten: {uuid, path, name, last_opened}
            "recent_projects": [],
            "last_opened_project": None,
            "last_opened_position": None,
            "last_project_dir": None,  # Letzter Ordner für Öffnen/Speichern-Dialoge
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

    # ========== Recent Projects (erweitert mit Metadaten) ==========

    def add_recent_project(self, project_path: str, project_uuid: str = None, project_name: str = None):
        """
        Fügt ein Projekt zur Recent-Liste hinzu (mit Metadaten).

        Args:
            project_path: Absoluter Pfad zum Projekt
            project_uuid: UUID des Projekts (optional)
            project_name: Name des Projekts (optional)
        """
        from datetime import datetime

        recent = self.settings.get("recent_projects", [])

        # Migriere alte Einträge (nur Strings) zu neuem Format
        recent = self._migrate_recent_projects(recent)

        # Entferne Duplikate (nach UUID oder Pfad)
        recent = [r for r in recent if r.get(
            "uuid") != project_uuid and r.get("path") != project_path]

        # Neuer Eintrag mit Metadaten
        new_entry = {
            "uuid": project_uuid or "unknown",
            "path": project_path,
            "name": project_name or Path(project_path).name,
            "last_opened": datetime.now().isoformat()
        }

        # An Anfang einfügen
        recent.insert(0, new_entry)

        # Maximal 10 behalten
        self.settings["recent_projects"] = recent[:10]
        self.save()

    def _migrate_recent_projects(self, recent: List) -> List[Dict]:
        """Migriert alte String-Einträge zu neuem Dict-Format."""
        migrated = []
        for entry in recent:
            if isinstance(entry, str):
                # Altes Format: nur Pfad
                migrated.append({
                    "uuid": "migrated",
                    "path": entry,
                    "name": Path(entry).name,
                    "last_opened": "unknown"
                })
            elif isinstance(entry, dict):
                # Neues Format: bereits Dict
                migrated.append(entry)
        return migrated

    def get_recent_projects(self, cleanup_missing: bool = True) -> List[Dict[str, str]]:
        """
        Gibt Liste der zuletzt geöffneten Projekte zurück (mit Metadaten).

        Args:
            cleanup_missing: Automatisch nicht existierende Projekte entfernen

        Returns:
            Liste von Projekt-Dicts: {uuid, path, name, last_opened}
        """
        recent = self.settings.get("recent_projects", [])

        # Migriere alte Einträge
        recent = self._migrate_recent_projects(recent)

        if cleanup_missing:
            # Entferne nicht existierende Projekte
            valid_recent = []
            for entry in recent:
                project_path = Path(entry.get("path", ""))
                if project_path.exists() and (project_path / "project.json").exists():
                    valid_recent.append(entry)
                else:
                    logger.info(
                        f"Entferne nicht existierendes Projekt aus Recent: {entry.get('name')}")

            # Speichere bereinigte Liste
            if len(valid_recent) != len(recent):
                self.settings["recent_projects"] = valid_recent
                self.save()

            return valid_recent

        return recent

    def clear_recent_projects(self):
        """Löscht die Recent-Projects-Liste"""
        self.settings["recent_projects"] = []
        self.save()

    def remove_recent_project_by_uuid(self, project_uuid: str):
        """Entfernt ein Projekt aus Recent nach UUID."""
        recent = self.settings.get("recent_projects", [])
        recent = [r for r in recent if r.get("uuid") != project_uuid]
        self.settings["recent_projects"] = recent
        self.save()

    def update_recent_project_path(self, project_uuid: str, new_path: str, new_name: str = None):
        """
        Aktualisiert Pfad und Name eines Projekts nach UUID (bei Umbenennung).

        Args:
            project_uuid: UUID des Projekts
            new_path: Neuer Pfad
            new_name: Neuer Name (optional)
        """
        recent = self.settings.get("recent_projects", [])

        for entry in recent:
            if entry.get("uuid") == project_uuid:
                entry["path"] = new_path
                if new_name:
                    entry["name"] = new_name
                logger.info(
                    f"Projekt-Pfad aktualisiert: {project_uuid} -> {new_path}")
                break

        self.settings["recent_projects"] = recent
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

    # ========== Last Project Directory (für Dialoge) ==========

    def set_last_project_dir(self, directory: str):
        """Setzt das zuletzt verwendete Verzeichnis für Öffnen/Speichern-Dialoge."""
        self.settings["last_project_dir"] = directory
        self.save()

    def get_last_project_dir(self) -> Optional[str]:
        """Gibt das zuletzt verwendete Verzeichnis zurück."""
        return self.settings.get("last_project_dir")

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
