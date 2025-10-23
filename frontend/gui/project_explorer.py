"""
Projekt-Explorer Widget (TreeView) für Datei-Navigation.
Zeigt Projektstruktur und Positionen in einem Baum an.
"""

import tkinter as tk
from tkinter import ttk
import logging
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class ProjectExplorer(ttk.Frame):
    """TreeView-basierter Projekt-Explorer"""
    
    def __init__(self, parent, on_position_open: Optional[Callable] = None):
        """
        Args:
            parent: Eltern-Widget
            on_position_open: Callback beim Doppelklick auf Position
        """
        super().__init__(parent)
        
        self.on_position_open = on_position_open
        self.current_project_path: Optional[Path] = None
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Erstellt die GUI-Komponenten"""
        
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(toolbar, text="📁 Projekt-Explorer", 
                 font=("", 10, "bold")).pack(side="left")
        
        # TreeView mit Scrollbar
        tree_container = ttk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container)
        scrollbar.pack(side="right", fill="y")
        
        # TreeView
        self.tree = ttk.Treeview(tree_container, yscrollcommand=scrollbar.set,
                                 selectmode="browse")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Spalten konfigurieren
        self.tree["columns"] = ("type",)
        self.tree.column("#0", width=200, minwidth=150)
        self.tree.column("type", width=80, minwidth=50)
        
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("type", text="Typ", anchor="w")
        
        # Events
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        
        # Kontextmenü (später)
        # self.tree.bind("<Button-2>", self._on_right_click)  # macOS
        # self.tree.bind("<Button-3>", self._on_right_click)  # Windows/Linux
        
    def load_project(self, project_path: Path, project_manager):
        """
        Lädt ein Projekt in den Explorer.
        
        Args:
            project_path: Pfad zum Projekt
            project_manager: ProjectManager-Instanz
        """
        self.current_project_path = project_path
        
        # TreeView leeren
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Projekt-Root
        project_name = project_manager.get_current_project_name() or "Projekt"
        root_id = self.tree.insert("", "end", text=project_name, 
                                   values=("Projekt",), open=True,
                                   tags=("project",))
        
        # Positionen rekursiv laden
        self._load_positions_recursive(root_id, project_path, project_path)
        
        logger.info(f"Projekt geladen in Explorer: {project_name}")
    
    def _load_positions_recursive(self, parent_id: str, base_path: Path, current_path: Path):
        """
        Lädt Positionen rekursiv in den Baum.
        
        Args:
            parent_id: ID des Eltern-Knotens
            base_path: Basis-Projektpfad
            current_path: Aktueller Pfad
        """
        if not current_path.exists():
            return
        
        # Sortiere: Ordner zuerst, dann Dateien
        items = sorted(current_path.iterdir(), 
                      key=lambda x: (not x.is_dir(), x.name.lower()))
        
        for item in items:
            if item.name.startswith("."):
                continue  # Versteckte Dateien ignorieren
            
            if item.is_dir():
                # Unterordner
                folder_id = self.tree.insert(parent_id, "end", 
                                            text=f"📁 {item.name}",
                                            values=("Ordner",),
                                            tags=("folder",))
                # Rekursiv in Unterordner
                self._load_positions_recursive(folder_id, base_path, item)
                
            elif item.suffix == ".json" and item.name != "project.json":
                # Position-Datei
                # Lade Position, um Anzeigenamen zu erhalten
                try:
                    import json
                    with open(item, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    pos_num = data.get("position_nummer", "")
                    pos_name = data.get("position_name", item.stem)
                    
                    if pos_num:
                        display_name = f"{pos_num} - {pos_name}"
                    else:
                        display_name = pos_name
                    
                    self.tree.insert(parent_id, "end", 
                                   text=f"📄 {display_name}",
                                   values=("Position",),
                                   tags=("position", str(item)))
                    
                except Exception as e:
                    logger.warning(f"Fehler beim Laden von {item}: {e}")
                    self.tree.insert(parent_id, "end",
                                   text=f"⚠️ {item.name}",
                                   values=("Fehler",),
                                   tags=("error",))
    
    def _on_double_click(self, event):
        """Behandelt Doppelklick auf Element"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        tags = self.tree.item(item_id, "tags")
        
        # Position öffnen
        if "position" in tags and self.on_position_open:
            # Zweiter Tag ist der Dateipfad
            if len(tags) > 1:
                position_path = Path(tags[1])
                logger.info(f"Position öffnen: {position_path}")
                self.on_position_open(position_path)
    
    def clear(self):
        """Leert den Explorer"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_project_path = None
    
    def refresh(self, project_manager):
        """Aktualisiert die Ansicht"""
        if self.current_project_path:
            self.load_project(self.current_project_path, project_manager)
    
    def get_selected_path(self) -> Optional[Path]:
        """
        Gibt den Pfad des ausgewählten Elements zurück.
        
        Returns:
            Path oder None
        """
        selection = self.tree.selection()
        if not selection:
            return None
        
        item_id = selection[0]
        tags = self.tree.item(item_id, "tags")
        
        if "position" in tags and len(tags) > 1:
            return Path(tags[1])
        
        return None
