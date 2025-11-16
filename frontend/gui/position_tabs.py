"""
Tab-Manager für Positionen (Level 1).
Verwaltet mehrere geöffnete Positionen in Tabs.
"""

import tkinter as tk
import customtkinter as ctk
import logging
from pathlib import Path
from typing import Dict, Optional, Callable
from backend.project import PositionModel

logger = logging.getLogger(__name__)


class PositionTabManager(ctk.CTkFrame):
    """Verwaltet Tabs für verschiedene Positionen"""

    def __init__(self, parent, module_tab_creator: Callable):
        """
        Args:
            parent: Eltern-Widget
            module_tab_creator: Callback zum Erstellen des Modul-Tab-Systems
        """
        super().__init__(parent)

        self.module_tab_creator = module_tab_creator

        # Datenstrukturen
        # position_file -> {model, tab_id, module_tabs}
        self.open_positions: Dict[str, Dict] = {}

        # Top-Bar mit Close-Button
        top_bar = ctk.CTkFrame(self, height=35)
        top_bar.pack(fill="x", padx=2, pady=2)

        # Close-Button (rechts)
        self.close_tab_button = ctk.CTkButton(
            top_bar,
            text="× Tab schließen",
            width=100,
            height=28,
            command=self.close_current_position,
            hover_color="#EF5350",  # Rot beim Hover
            corner_radius=8
        )
        self.close_tab_button.pack(side="right", padx=5)

        # Tabview erstellen
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=2)

        # Willkommens-Seite (wenn keine Tabs offen)
        self._create_welcome_tab()

        logger.info("PositionTabManager initialisiert")

    def _create_welcome_tab(self):
        """Erstellt die Willkommens-Seite"""
        self.tabview.add("🏠 Start")
        welcome_frame = self.tabview.tab("🏠 Start")

        # Zentrierter Inhalt
        content = ctk.CTkFrame(welcome_frame)
        content.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(content, text="🏭️ Statikprogramm v2.0",
                     font=("", 18, "bold")).pack(pady=10)

        ctk.CTkLabel(content, text="Willkommen!",
                     font=("", 12)).pack(pady=5)

        ctk.CTkLabel(content, text="Erste Schritte:",
                     font=("", 11, "bold")).pack(anchor="w", pady=15)

        steps = [
            "1. Datei → Neues Projekt erstellen",
            "2. Position hinzufügen",
            "3. Oder bestehendes Projekt öffnen"
        ]

        for step in steps:
            ctk.CTkLabel(content, text=step, font=("", 10)).pack(
                anchor="w", padx=20, pady=2)

        self.welcome_tab_name = "🏠 Start"

    def open_position(self, position_model: PositionModel, position_file: Path):
        """
        Öffnet eine Position in einem neuen Tab.

        Args:
            position_model: Position-Datenmodell
            position_file: Pfad zur Position-Datei
        """
        position_key = str(position_file)

        # Prüfe, ob Position bereits offen ist
        if position_key in self.open_positions:
            # Tab aktivieren
            existing = self.open_positions[position_key]
            self.tabview.set(existing["tab_name"])
            logger.info(
                f"Position bereits offen, aktiviere Tab: {position_file.name}")
            return

        # Tab-Titel vorbereiten
        tab_title = position_model.get_display_name()
        if len(tab_title) > 25:
            tab_title = tab_title[:22] + "..."

        # Neuer Tab erstellen
        self.tabview.add(tab_title)
        tab_frame = self.tabview.tab(tab_title)

        # Modul-Tab-System erstellen (Level 2)
        module_tabs = self.module_tab_creator(
            tab_frame, position_model, position_file)
        module_tabs.pack(fill="both", expand=True)

        # Speichere Referenz
        self.open_positions[position_key] = {
            "model": position_model,
            "file": position_file,
            "tab_name": tab_title,
            "module_tabs": module_tabs
        }

        # Willkommens-Tab ausblenden
        self._hide_welcome_tab()

        # Neuen Tab aktivieren
        self.tabview.set(tab_title)

        logger.info(f"Position geöffnet: {position_file.name}")

    def close_position(self, position_file: Path):
        """
        Schließt eine Position (Tab).

        Args:
            position_file: Pfad zur Position-Datei
        """
        position_key = str(position_file)

        if position_key not in self.open_positions:
            return

        pos_data = self.open_positions[position_key]

        # Tab entfernen
        try:
            self.tabview.delete(pos_data["tab_name"])
        except Exception as e:
            logger.warning(f"Fehler beim Entfernen des Tabs: {e}")

        # Cleanup
        if pos_data["module_tabs"]:
            pos_data["module_tabs"].cleanup()

        # Aus Dictionary entfernen
        del self.open_positions[position_key]

        logger.info(f"Position geschlossen: {position_file.name}")

        # Willkommens-Tab anzeigen, wenn keine Tabs mehr offen
        if len(self.open_positions) == 0:
            self._show_welcome_tab()

    def close_current_position(self):
        """Schließt die aktuell aktive Position"""
        current_tab = self.tabview.get()

        if not current_tab or current_tab == self.welcome_tab_name:
            return

        # Finde Position-File für diesen Tab
        for pos_key, pos_data in self.open_positions.items():
            if pos_data["tab_name"] == current_tab:
                self.close_position(Path(pos_key))
                break

    def get_current_position(self) -> Optional[tuple[PositionModel, Path]]:
        """
        Gibt die aktuell aktive Position zurück.

        Returns:
            Tuple (PositionModel, Path) oder None
        """
        current_tab = self.tabview.get()

        if not current_tab or current_tab == self.welcome_tab_name:
            return None

        for pos_data in self.open_positions.values():
            if pos_data["tab_name"] == current_tab:
                return (pos_data["model"], pos_data["file"])

        return None

    def save_current_position(self, project_manager):
        """Speichert die aktuell aktive Position"""
        current = self.get_current_position()
        if not current:
            logger.warning("Keine Position zum Speichern aktiv")
            return

        position_model, position_file = current

        # Daten aus Modulen sammeln
        pos_key = str(position_file)
        if pos_key in self.open_positions:
            module_tabs = self.open_positions[pos_key]["module_tabs"]
            if module_tabs:
                module_tabs.collect_data_to_model(position_model)

        # Position speichern
        project_manager.save_position(position_model, position_file)
        logger.info(f"Position gespeichert: {position_file.name}")

    def save_all_positions(self, project_manager):
        """Speichert alle offenen Positionen"""
        for pos_key, pos_data in self.open_positions.items():
            position_model = pos_data["model"]
            position_file = pos_data["file"]
            module_tabs = pos_data["module_tabs"]

            # Daten sammeln
            if module_tabs:
                module_tabs.collect_data_to_model(position_model)

            # Speichern
            project_manager.save_position(position_model, position_file)

        logger.info(f"{len(self.open_positions)} Position(en) gespeichert")

    # Callback wird nicht mehr benötigt, da CTkTabview Events anders handhabt

    def _hide_welcome_tab(self):
        """Blendet den Willkommens-Tab aus"""
        try:
            self.tabview.delete(self.welcome_tab_name)
        except:
            pass  # Tab existiert nicht mehr

    def _show_welcome_tab(self):
        """Zeigt den Willkommens-Tab an"""
        # Welcome-Tab neu erstellen
        self._create_welcome_tab()
        self.tabview.set(self.welcome_tab_name)

    def get_open_position_count(self) -> int:
        """Gibt die Anzahl offener Positionen zurück"""
        return len(self.open_positions)

    def cleanup(self):
        """Räumt alle Ressourcen auf"""
        for pos_data in self.open_positions.values():
            if pos_data["module_tabs"]:
                pos_data["module_tabs"].cleanup()

        self.open_positions.clear()
        logger.info("PositionTabManager aufgeräumt")
