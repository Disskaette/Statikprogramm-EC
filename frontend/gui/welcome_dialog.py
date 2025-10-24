"""
Welcome-Dialog beim Programmstart.
Bietet Optionen: Neues Projekt, Projekt öffnen, Recent Projects.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class WelcomeDialog(tk.Toplevel):
    """
    Welcome-Dialog beim Start der Anwendung.
    Bietet verschiedene Einstiegsmöglichkeiten.
    """
    
    def __init__(self, parent, settings_manager, on_choice: Callable):
        """
        Args:
            parent: Eltern-Fenster
            settings_manager: SettingsManager-Instanz
            on_choice: Callback (action, path) wenn Auswahl getroffen wurde
                       action: "new", "open", "recent", "quickstart", "cancel"
                       path: Projekt-Pfad (nur bei "recent" und "open")
        """
        super().__init__(parent)
        
        self.settings_manager = settings_manager
        self.on_choice = on_choice
        self.result = None
        
        # Dialog-Eigenschaften
        self.title("Willkommen beim Statikprogramm v2.0")
        self.geometry("600x600")  # Größer für mehr Platz
        self.resizable(False, False)
        
        # Modal
        self.transient(parent)
        self.grab_set()
        
        # Zentrieren
        self._center_window()
        
        # GUI erstellen
        self._create_widgets()
        
        logger.info("Welcome-Dialog geöffnet")
    
    def _center_window(self):
        """Zentriert das Fenster auf dem Bildschirm"""
        self.update_idletasks()
        
        # Bildschirm-Dimensionen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Fenster-Dimensionen
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        
        # Position berechnen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Erstellt die GUI-Elemente"""
        
        # Header
        header_frame = ttk.Frame(self, padding=20)
        header_frame.pack(fill="x")
        
        ttk.Label(header_frame, 
                 text="🏗️ Statikprogramm v2.0",
                 font=("", 20, "bold")).pack()
        
        ttk.Label(header_frame,
                 text="Statik-Tool für Holzbau nach EC5",
                 font=("", 11)).pack(pady=5)
        
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)
        
        # Content (zentriert)
        content_frame = ttk.Frame(self, padding=20)
        content_frame.pack(fill="both", expand=True)
        
        # Titel - zentriert
        ttk.Label(content_frame,
                 text="Wie möchten Sie starten?",
                 font=("", 13, "bold"),
                 anchor="center").pack(pady=(0, 15))
        
        # Buttons Container - zentriert
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(expand=True)
        
        # Neues Projekt
        btn_new = ttk.Button(button_frame,
                            text="📁 Neues Projekt erstellen",
                            command=self._on_new_project,
                            width=40)
        btn_new.pack(pady=5)
        
        # Projekt öffnen
        btn_open = ttk.Button(button_frame,
                             text="📂 Bestehendes Projekt öffnen",
                             command=self._on_open_project,
                             width=40)
        btn_open.pack(pady=5)
        
        # Schnellstart (temporäres Projekt)
        btn_quick = ttk.Button(button_frame,
                              text="⚡ Schnellstart (temporäre Position)",
                              command=self._on_quickstart,
                              width=40)
        btn_quick.pack(pady=5)
        
        ttk.Separator(button_frame, orient="horizontal").pack(fill="x", pady=15)
        
        # Recent Projects - Titel zentriert, gleiche Schriftgröße
        recent_label = ttk.Label(button_frame,
                                text="Zuletzt geöffnet:",
                                font=("", 13, "bold"),
                                anchor="center")
        recent_label.pack(pady=(5, 10))
        
        # Recent Projects Liste
        self.recent_frame = ttk.Frame(button_frame)
        self.recent_frame.pack(fill="both", expand=True)
        
        self._load_recent_projects()
        
        # Footer
        footer_frame = ttk.Frame(self, padding=10)
        footer_frame.pack(fill="x", side="bottom")
        
        ttk.Button(footer_frame,
                  text="Abbrechen",
                  command=self._on_cancel).pack(side="right")
        
        # Checkbox: Nicht mehr anzeigen
        self.show_again_var = tk.BooleanVar(
            value=self.settings_manager.should_show_welcome_screen()
        )
        ttk.Checkbutton(footer_frame,
                       text="Diesen Dialog beim Start anzeigen",
                       variable=self.show_again_var).pack(side="left")
    
    def _load_recent_projects(self):
        """Lädt und zeigt Recent Projects"""
        recent = self.settings_manager.get_recent_projects()
        
        if not recent:
            ttk.Label(self.recent_frame,
                     text="Keine kürzlich geöffneten Projekte",
                     foreground="gray").pack(pady=5)
            return
        
        # Zeige max. 3 Recent Projects (mehr passt nicht gut)
        for project_path in recent[:3]:
            path = Path(project_path)
            
            # Prüfe, ob Projekt noch existiert
            if not path.exists():
                continue
            
            # Button für Recent Project - zentriert, gleiche Breite wie oben
            btn = ttk.Button(self.recent_frame,
                           text=f"📁 {path.name}",
                           command=lambda p=project_path: self._on_recent_project(p),
                           width=40)
            btn.pack(pady=3)
            
            # Pfad als Tooltip (klein) - zentriert
            ttk.Label(self.recent_frame,
                     text=project_path,
                     font=("", 8),
                     foreground="gray").pack()
    
    def _on_new_project(self):
        """Neues Projekt erstellen"""
        self.result = ("new", None)
        self._close()
    
    def _on_open_project(self):
        """Projekt öffnen"""
        self.result = ("open", None)
        self._close()
    
    def _on_quickstart(self):
        """Schnellstart (temporäres Projekt)"""
        self.result = ("quickstart", None)
        self._close()
    
    def _on_recent_project(self, project_path: str):
        """Recent Project öffnen"""
        self.result = ("recent", project_path)
        self._close()
    
    def _on_cancel(self):
        """Dialog abbrechen"""
        self.result = ("cancel", None)
        self._close()
    
    def _close(self):
        """Dialog schließen"""
        # Einstellung speichern
        self.settings_manager.set_show_welcome_screen(self.show_again_var.get())
        
        # Callback aufrufen
        if self.on_choice and self.result:
            action, path = self.result
            self.on_choice(action, path)
        
        # Dialog schließen
        self.grab_release()
        self.destroy()
    
    @staticmethod
    def show_dialog(parent, settings_manager, on_choice: Callable) -> Optional['WelcomeDialog']:
        """
        Zeigt den Welcome-Dialog (falls aktiviert).
        
        Args:
            parent: Eltern-Fenster
            settings_manager: SettingsManager-Instanz
            on_choice: Callback für Auswahl
            
        Returns:
            Dialog-Instanz oder None (falls deaktiviert)
        """
        # Prüfe, ob Dialog angezeigt werden soll
        if not settings_manager.should_show_welcome_screen():
            logger.info("Welcome-Dialog ist deaktiviert")
            return None
        
        # Dialog erstellen und anzeigen
        dialog = WelcomeDialog(parent, settings_manager, on_choice)
        return dialog
