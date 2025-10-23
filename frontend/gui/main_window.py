"""
Haupt-GUI-Fenster der Anwendung.
Integriert alle Komponenten: Menü, Explorer, Tabs, etc.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from pathlib import Path
from typing import Optional

from backend.project import ProjectManager, PositionModel, SettingsManager
from backend.database.datenbank_holz import datenbank_holz_class
from .project_explorer import ProjectExplorer
from .position_tabs import PositionTabManager
from .module_tabs import ModuleTabManager

logger = logging.getLogger(__name__)


class MainWindow:
    """Haupt-Anwendungsfenster"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Statikprogramm v2.0")
        
        # Backend-Komponenten
        self.project_manager = ProjectManager()
        self.settings_manager = SettingsManager()
        self.db = datenbank_holz_class()
        
        # GUI-Status
        self.current_project_path: Optional[Path] = None
        
        # Fenster-Konfiguration
        self._setup_window()
        
        # GUI erstellen
        self._create_menu()
        self._create_gui()
        
        # Letztes Projekt wiederherstellen (optional)
        self._restore_last_project()
        
        logger.info("MainWindow initialisiert")
    
    def _setup_window(self):
        """Konfiguriert Fenster-Eigenschaften"""
        # Geometrie aus Settings
        geometry = self.settings_manager.get_window_geometry()
        self.root.geometry(geometry)
        
        # Fenster im Vordergrund (kurz)
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.root.after(500, lambda: self.root.attributes("-topmost", False))
        
        # Fenster-Close-Event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_menu(self):
        """Erstellt die Menüleiste"""
        menubar = tk.Menu(self.root, tearoff=0)
        self.root.config(menu=menubar)
        
        # macOS: Menü sofort aktivieren
        self.root.createcommand('tk::mac::Quit', self._on_closing)
        
        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        
        file_menu.add_command(label="Neues Projekt...", 
                             command=self._new_project,
                             accelerator="Cmd+N")
        file_menu.add_command(label="Projekt öffnen...", 
                             command=self._open_project,
                             accelerator="Cmd+O")
        file_menu.add_separator()
        file_menu.add_command(label="Neue Position...", 
                             command=self._new_position,
                             accelerator="Cmd+Shift+N",
                             state="disabled")  # Nur wenn Projekt offen
        file_menu.add_separator()
        file_menu.add_command(label="Speichern", 
                             command=self._save_current,
                             accelerator="Cmd+S",
                             state="disabled")
        file_menu.add_command(label="Alle speichern", 
                             command=self._save_all,
                             accelerator="Cmd+Shift+S",
                             state="disabled")
        file_menu.add_separator()
        file_menu.add_command(label="Position schließen", 
                             command=self._close_current_position,
                             accelerator="Cmd+W",
                             state="disabled")
        file_menu.add_command(label="Projekt schließen", 
                             command=self._close_project)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", 
                             command=self._on_closing,
                             accelerator="Cmd+Q")
        
        self.file_menu = file_menu  # Referenz speichern für State-Updates
        
        # Bearbeiten-Menü
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)
        edit_menu.add_command(label="Rückgängig", state="disabled")
        edit_menu.add_command(label="Wiederholen", state="disabled")
        
        # Ansicht-Menü
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        view_menu.add_command(label="Explorer aktualisieren", 
                             command=self._refresh_explorer)
        
        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="?", menu=help_menu)
        help_menu.add_command(label="Über...", command=self._show_about)
        
        # Tastenkombinationen
        self.root.bind("<Command-n>", lambda e: self._new_project())
        self.root.bind("<Command-o>", lambda e: self._open_project())
        self.root.bind("<Command-s>", lambda e: self._save_current())
        self.root.bind("<Command-Shift-s>", lambda e: self._save_all())
        self.root.bind("<Command-w>", lambda e: self._close_current_position())
        self.root.bind("<Command-q>", lambda e: self._on_closing())
    
    def _create_gui(self):
        """Erstellt die Haupt-GUI-Struktur"""
        
        # Haupt-Container (Horizontal: Explorer | Content)
        main_container = ttk.PanedWindow(self.root, orient="horizontal")
        main_container.pack(fill="both", expand=True)
        
        # ========== LINKS: Projekt-Explorer ==========
        explorer_width = self.settings_manager.get_explorer_width()
        
        self.explorer = ProjectExplorer(
            main_container,
            on_position_open=self._on_explorer_position_open
        )
        
        main_container.add(self.explorer, weight=0)
        
        # ========== RECHTS: Tab-Container ==========
        
        # Position-Tabs (Level 1)
        self.position_tabs = PositionTabManager(
            main_container,
            module_tab_creator=self._create_module_tabs
        )
        
        main_container.add(self.position_tabs, weight=1)
        
        # Sash-Position setzen (Explorer-Breite)
        self.root.after(100, lambda: main_container.sashpos(0, explorer_width))
    
    def _create_module_tabs(self, parent, position_model: PositionModel, 
                           position_file: Path) -> ModuleTabManager:
        """
        Factory-Methode zum Erstellen des Modul-Tab-Managers.
        Wird von PositionTabManager aufgerufen.
        
        Args:
            parent: Eltern-Widget
            position_model: Position-Datenmodell
            position_file: Pfad zur Position-Datei
            
        Returns:
            ModuleTabManager-Instanz
        """
        return ModuleTabManager(parent, position_model, position_file, app_ref=self)
    
    # ========== Projekt-Operationen ==========
    
    def _new_project(self):
        """Erstellt ein neues Projekt"""
        from tkinter import simpledialog
        
        project_name = simpledialog.askstring("Neues Projekt", "Projektname:")
        if not project_name:
            return
        
        description = simpledialog.askstring("Neues Projekt", 
                                            "Beschreibung (optional):",
                                            initialvalue="")
        
        try:
            project_path = self.project_manager.create_project(
                project_name, description or ""
            )
            
            # Projekt öffnen
            self._load_project(project_path)
            
            messagebox.showinfo("Erfolg", f"Projekt '{project_name}' erstellt!")
            
        except FileExistsError:
            messagebox.showerror("Fehler", f"Projekt '{project_name}' existiert bereits")
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Projekts: {e}")
            messagebox.showerror("Fehler", f"Projekt konnte nicht erstellt werden:\n{e}")
    
    def _open_project(self):
        """Öffnet ein bestehendes Projekt"""
        # Projekt-Ordner auswählen
        project_dir = filedialog.askdirectory(
            title="Projekt öffnen",
            initialdir=self.project_manager.projects_root
        )
        
        if not project_dir:
            return
        
        project_path = Path(project_dir)
        
        # Prüfe, ob project.json existiert
        if not (project_path / "project.json").exists():
            messagebox.showerror("Fehler", "Kein gültiges Projekt-Verzeichnis")
            return
        
        try:
            self._load_project(project_path)
        except Exception as e:
            logger.error(f"Fehler beim Öffnen des Projekts: {e}")
            messagebox.showerror("Fehler", f"Projekt konnte nicht geöffnet werden:\n{e}")
    
    def _load_project(self, project_path: Path):
        """
        Lädt ein Projekt.
        
        Args:
            project_path: Pfad zum Projektverzeichnis
        """
        # Altes Projekt schließen
        if self.current_project_path:
            self._close_project()
        
        # Projekt öffnen
        project_data = self.project_manager.open_project(project_path)
        self.current_project_path = project_path
        
        # Explorer aktualisieren
        self.explorer.load_project(project_path, self.project_manager)
        
        # Menü-Status aktualisieren
        self._update_menu_states()
        
        # In Recent-Liste
        self.settings_manager.add_recent_project(str(project_path))
        self.settings_manager.set_last_opened_project(str(project_path))
        
        # Fenster-Titel
        self.root.title(f"Statikprogramm v2.0 - {project_data['name']}")
        
        logger.info(f"Projekt geladen: {project_data['name']}")
    
    def _close_project(self):
        """Schließt das aktuelle Projekt"""
        if not self.current_project_path:
            return
        
        # Alle Positionen schließen
        # (Position-Tabs haben bereits Cleanup-Logik)
        self.position_tabs.cleanup()
        
        # Explorer leeren
        self.explorer.clear()
        
        # Status zurücksetzen
        self.current_project_path = None
        self.project_manager.current_project_path = None
        
        # Menü-Status
        self._update_menu_states()
        
        # Titel zurücksetzen
        self.root.title("Statikprogramm v2.0")
        
        logger.info("Projekt geschlossen")
    
    # ========== Position-Operationen ==========
    
    def _new_position(self):
        """Erstellt eine neue Position"""
        if not self.current_project_path:
            messagebox.showwarning("Warnung", "Kein Projekt geöffnet")
            return
        
        from tkinter import simpledialog
        
        pos_nummer = simpledialog.askstring("Neue Position", "Position-Nummer (z.B. 1.01):")
        if not pos_nummer:
            return
        
        pos_name = simpledialog.askstring("Neue Position", "Positionsname:")
        if not pos_name:
            return
        
        # Position-Model erstellen
        position_model = PositionModel(
            position_nummer=pos_nummer,
            position_name=pos_name
        )
        
        try:
            # Position speichern
            position_file = self.project_manager.create_position(position_model)
            
            # Explorer aktualisieren
            self.explorer.refresh(self.project_manager)
            
            # Position öffnen
            self.position_tabs.open_position(position_model, position_file)
            
            logger.info(f"Position erstellt: {position_model.get_display_name()}")
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Position: {e}")
            messagebox.showerror("Fehler", f"Position konnte nicht erstellt werden:\n{e}")
    
    def _on_explorer_position_open(self, position_file: Path):
        """
        Callback wenn Position im Explorer doppelgeklickt wird.
        
        Args:
            position_file: Pfad zur Position-Datei
        """
        try:
            # Position laden
            position_model = self.project_manager.load_position(position_file)
            
            # In Tab öffnen
            self.position_tabs.open_position(position_model, position_file)
            
        except Exception as e:
            logger.error(f"Fehler beim Öffnen der Position: {e}")
            messagebox.showerror("Fehler", f"Position konnte nicht geöffnet werden:\n{e}")
    
    def _close_current_position(self):
        """Schließt die aktuelle Position"""
        self.position_tabs.close_current_position()
    
    # ========== Speichern ==========
    
    def _save_current(self):
        """Speichert die aktuelle Position"""
        if not self.current_project_path:
            return
        
        try:
            self.position_tabs.save_current_position(self.project_manager)
            logger.info("Position gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")
    
    def _save_all(self):
        """Speichert alle offenen Positionen"""
        if not self.current_project_path:
            return
        
        try:
            self.position_tabs.save_all_positions(self.project_manager)
            messagebox.showinfo("Erfolg", "Alle Positionen gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")
    
    # ========== Hilfsfunktionen ==========
    
    def _refresh_explorer(self):
        """Aktualisiert den Explorer"""
        if self.current_project_path:
            self.explorer.refresh(self.project_manager)
    
    def _update_menu_states(self):
        """Aktualisiert Menü-Stati basierend auf Projekt-Status"""
        project_open = self.current_project_path is not None
        position_open = self.position_tabs.get_open_position_count() > 0
        
        # Datei-Menü
        state_project = "normal" if project_open else "disabled"
        state_position = "normal" if position_open else "disabled"
        
        self.file_menu.entryconfig("Neue Position...", state=state_project)
        self.file_menu.entryconfig("Speichern", state=state_position)
        self.file_menu.entryconfig("Alle speichern", state=state_project)
        self.file_menu.entryconfig("Position schließen", state=state_position)
    
    def _restore_last_project(self):
        """Stellt das zuletzt geöffnete Projekt wieder her (optional)"""
        # Deaktiviert für jetzt - könnte nerven
        # last_project = self.settings_manager.get_last_opened_project()
        # if last_project and Path(last_project).exists():
        #     self._load_project(Path(last_project))
        pass
    
    def _show_about(self):
        """Zeigt About-Dialog"""
        messagebox.showinfo(
            "Über Statikprogramm v2.0",
            "Statikprogramm v2.0\n\n"
            "Modulares Statik-Berechnungstool\n"
            "für Holzbau nach EC5\n\n"
            "© 2025"
        )
    
    def _on_closing(self):
        """Behandelt Fenster-Schließen-Event"""
        # Geometrie speichern
        self.settings_manager.set_window_geometry(self.root.geometry())
        
        # TODO: Ungespeicherte Änderungen prüfen
        
        # Cleanup
        self.position_tabs.cleanup()
        
        # Fenster schließen
        self.root.destroy()
        
        logger.info("Anwendung beendet")


def start_application():
    """Startet die Hauptanwendung"""
    print("🚀 Starte Statikprogramm v2.0...")
    
    root = tk.Tk()
    app = MainWindow(root)
    
    print("✅ Anwendung läuft")
    root.mainloop()
    
    print("👋 Programm beendet")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S"
    )
    start_application()
