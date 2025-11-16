"""
Projektmanagement-System für Statikberechnungen.
Verwaltet Projekte, Positionen und Dateipersistenz.
"""

import os
import json
import logging
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from .position_model import PositionModel

logger = logging.getLogger(__name__)


class ProjectManager:
    """Zentrale Verwaltung für Projekte und Positionen"""

    def __init__(self, projects_root: Optional[Path] = None):
        """
        Args:
            projects_root: Wurzelverzeichnis für Projekte.
                          Default: ./Projekte relativ zum Skript
        """
        if projects_root is None:
            # Default: Projekte-Ordner im gleichen Verzeichnis wie das Programm
            script_dir = Path(__file__).parent.parent.parent
            projects_root = script_dir / "Projekte"

        self.projects_root = Path(projects_root)
        self.projects_root.mkdir(parents=True, exist_ok=True)

        self.current_project_path: Optional[Path] = None
        self.current_project_data: Optional[Dict[str, Any]] = None

        logger.info(f"ProjectManager initialisiert: {self.projects_root}")

    # ========== Projekt-Operationen ==========

    def create_project(self, project_name: str, description: str = "") -> Path:
        """
        Erstellt ein neues Projekt.

        Args:
            project_name: Name des Projekts
            description: Optionale Beschreibung

        Returns:
            Pfad zum Projektverzeichnis
        """
        # Sichere Ordnernamen
        safe_name = "".join(
            c for c in project_name if c.isalnum() or c in (' ', '_', '-'))
        safe_name = safe_name.replace(" ", "_")

        project_path = self.projects_root / safe_name

        if project_path.exists():
            logger.warning(f"Projekt existiert bereits: {project_path}")
            raise FileExistsError(
                f"Projekt '{project_name}' existiert bereits")

        # Projektordner erstellen
        project_path.mkdir(parents=True, exist_ok=True)

        # Projekt-Metadaten erstellen (MIT UUID)
        project_data = {
            "uuid": str(uuid.uuid4()),  # Eindeutige Projekt-ID
            "name": project_name,
            "created": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "description": description,
            "positions": []
        }

        # project.json speichern
        project_file = project_path / "project.json"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Projekt erstellt: {project_path}")
        return project_path

    def open_project(self, project_path: Path) -> Dict[str, Any]:
        """
        Öffnet ein bestehendes Projekt.

        Args:
            project_path: Pfad zum Projektverzeichnis

        Returns:
            Projekt-Metadaten
        """
        project_path = Path(project_path)
        project_file = project_path / "project.json"

        if not project_file.exists():
            raise FileNotFoundError(
                f"Projekt-Datei nicht gefunden: {project_file}")

        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)

        # Migration: UUID hinzufügen, falls nicht vorhanden (Abwärtskompatibilität)
        if "uuid" not in project_data:
            project_data["uuid"] = str(uuid.uuid4())
            # Sofort speichern, um Migration zu persistieren
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            logger.info(
                f"Migration: UUID hinzugefügt zu Projekt {project_data.get('name')}")

        self.current_project_path = project_path
        self.current_project_data = project_data

        logger.info(
            f"Projekt geöffnet: {project_path} (UUID: {project_data['uuid']})")
        return project_data

    def save_project(self):
        """Speichert die aktuellen Projekt-Metadaten"""
        if not self.current_project_path or not self.current_project_data:
            raise ValueError("Kein Projekt geöffnet")

        self.current_project_data["last_modified"] = datetime.now().isoformat()

        project_file = self.current_project_path / "project.json"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_project_data, f,
                      indent=2, ensure_ascii=False)

        logger.debug(f"Projekt gespeichert: {project_file}")

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        Listet alle verfügbaren Projekte auf.

        Returns:
            Liste von Projekt-Informationen
        """
        projects = []

        for item in self.projects_root.iterdir():
            if item.is_dir():
                project_file = item / "project.json"
                if project_file.exists():
                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            project_data = json.load(f)
                            project_data['path'] = str(item)
                            projects.append(project_data)
                    except Exception as e:
                        logger.error(
                            f"Fehler beim Lesen von {project_file}: {e}")

        # Sortiere nach letzter Änderung (neueste zuerst)
        projects.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
        return projects

    # ========== Position-Operationen ==========

    def create_position(self, position_model: PositionModel,
                        subfolder: str = "") -> Path:
        """
        Erstellt eine neue Position im aktuellen Projekt.

        Args:
            position_model: Position-Datenmodell
            subfolder: Optionaler Unterordner (z.B. "EG")

        Returns:
            Pfad zur Position-Datei
        """
        if not self.current_project_path:
            raise ValueError("Kein Projekt geöffnet")

        # Zielordner bestimmen
        if subfolder:
            target_dir = self.current_project_path / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = self.current_project_path

        # Dateiname generieren
        filename = position_model.get_filename()
        position_file = target_dir / filename

        # Position speichern
        with open(position_file, 'w', encoding='utf-8') as f:
            json.dump(position_model.to_dict(), f,
                      indent=2, ensure_ascii=False)

        # Projekt-Metadaten aktualisieren
        relative_path = position_file.relative_to(self.current_project_path)
        if str(relative_path) not in self.current_project_data["positions"]:
            self.current_project_data["positions"].append(str(relative_path))
            self.save_project()

        logger.info(f"Position erstellt: {position_file}")
        return position_file

    def load_position(self, position_file: Path) -> PositionModel:
        """
        Lädt eine Position aus einer Datei.

        Args:
            position_file: Pfad zur Position-Datei

        Returns:
            PositionModel-Instanz
        """
        position_file = Path(position_file)

        if not position_file.exists():
            raise FileNotFoundError(
                f"Position nicht gefunden: {position_file}")

        with open(position_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        position = PositionModel.from_dict(data)
        logger.debug(f"Position geladen: {position_file}")
        return position

    def save_position(self, position_model: PositionModel, position_file: Path):
        """
        Speichert eine Position in eine Datei.

        Args:
            position_model: Position-Datenmodell
            position_file: Pfad zur Zieldatei
        """
        with open(position_file, 'w', encoding='utf-8') as f:
            json.dump(position_model.to_dict(), f,
                      indent=2, ensure_ascii=False)

        logger.debug(f"Position gespeichert: {position_file}")

    def list_positions(self) -> List[Dict[str, Any]]:
        """
        Listet alle Positionen im aktuellen Projekt auf.

        Returns:
            Liste von Position-Informationen mit Pfaden
        """
        if not self.current_project_path:
            raise ValueError("Kein Projekt geöffnet")

        positions = []

        # Durchsuche Projektordner rekursiv nach JSON-Dateien
        for json_file in self.current_project_path.rglob("*.json"):
            # Ignoriere project.json
            if json_file.name == "project.json":
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Prüfe, ob es eine Position ist (hat position_nummer Feld)
                    if "position_nummer" in data or "position_name" in data:
                        data['file_path'] = str(json_file)
                        data['relative_path'] = str(
                            json_file.relative_to(self.current_project_path))
                        positions.append(data)
            except Exception as e:
                logger.error(f"Fehler beim Lesen von {json_file}: {e}")

        return positions

    def delete_position(self, position_file: Path):
        """
        Löscht eine Position.

        Args:
            position_file: Pfad zur Position-Datei
        """
        position_file = Path(position_file)

        if position_file.exists():
            position_file.unlink()

            # Aus Projekt-Metadaten entfernen
            if self.current_project_path and self.current_project_data:
                relative_path = str(position_file.relative_to(
                    self.current_project_path))
                if relative_path in self.current_project_data["positions"]:
                    self.current_project_data["positions"].remove(
                        relative_path)
                    self.save_project()

            logger.info(f"Position gelöscht: {position_file}")

    # ========== Hilfs-Funktionen ==========

    def get_current_project_name(self) -> Optional[str]:
        """Gibt den Namen des aktuellen Projekts zurück"""
        if self.current_project_data:
            return self.current_project_data.get("name")
        return None

    def is_project_open(self) -> bool:
        """Prüft, ob ein Projekt geöffnet ist"""
        return self.current_project_path is not None

    def get_project_uuid(self) -> Optional[str]:
        """Gibt die UUID des aktuellen Projekts zurück"""
        if self.current_project_data:
            return self.current_project_data.get("uuid")
        return None
