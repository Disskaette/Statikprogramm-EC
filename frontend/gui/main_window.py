"""
Haupt-GUI-Fenster der Anwendung.
Integriert alle Komponenten: Menü, Explorer, Tabs, etc.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import logging
from pathlib import Path
from typing import Optional

from backend.project import ProjectManager, PositionModel, SettingsManager
from backend.database.datenbank_holz import datenbank_holz_class
from .project_explorer import ProjectExplorer
from .position_tabs import PositionTabManager
from .module_tabs import ModuleTabManager
from .welcome_dialog import WelcomeDialog
from .theme_config import ThemeManager

logger = logging.getLogger(__name__)


class MainWindow:
    """Haupt-Anwendungsfenster"""

    def __init__(self, root: ctk.CTk):
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

        # Welcome-Dialog anzeigen (nach kurzer Verzögerung, damit Fenster sichtbar ist)
        self.root.after(100, self._show_welcome_dialog)

        logger.info("MainWindow initialisiert")

    def _setup_window(self):
        """Konfiguriert Fenster-Eigenschaften"""
        # CustomTkinter Appearance Mode setzen - Default: Dark
        ctk.set_appearance_mode("dark")  # "system", "light", "dark"
        ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

        # Minimale Fenstergröße setzen (klein, da dynamisch)
        self.root.minsize(800, 500)

        # Geometrie aus Settings
        geometry = self.settings_manager.get_window_geometry()
        if geometry and geometry != "1200x800":
            # Nutze gespeicherte Geometrie (Nutzer hat manuell angepasst)
            self.root.geometry(geometry)
        else:
            # Kompakte Startgröße, passt sich dann an Inhalt an
            # ThemeManager für MAX_DISPLAY_WIDTH nutzen
            from frontend.gui.theme_config import ThemeManager
            start_width = ThemeManager.MAX_DISPLAY_WIDTH + 450  # Kompakt: Eingabe + Anzeige
            start_height = 700  # Kompakte Höhe

            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            # Zentriert positionieren
            x = (screen_width - start_width) // 2
            y = (screen_height - start_height) // 2

            self.root.geometry(f"{start_width}x{start_height}+{x}+{y}")

        # Fenster im Vordergrund (kurz)
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.root.after(500, lambda: self.root.attributes("-topmost", False))

        # Fenster-Close-Event
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_menu(self):
        """Erstellt die Menüleiste"""
        menubar = tk.Menu(self.root, tearoff=0)
        self.root.configure(menu=menubar)

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
        file_menu.add_command(label="Projekt speichern unter...",
                              command=self._save_project_as,
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
        view_menu.add_separator()
        view_menu.add_command(label="Dark Mode umschalten",
                              command=self._toggle_theme,
                              accelerator="Cmd+D")

        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="?", menu=help_menu)
        help_menu.add_command(label="Über...", command=self._show_about)

        # Tastenkombinationen
        self.root.bind("<Command-n>", lambda e: self._new_project())
        self.root.bind("<Command-o>", lambda e: self._open_project())
        self.root.bind("<Command-s>", lambda e: self._save_current())
        self.root.bind("<Command-d>", lambda e: self._toggle_theme())
        self.root.bind("<Command-Shift-s>", lambda e: self._save_all())
        self.root.bind("<Command-w>", lambda e: self._close_current_position())
        self.root.bind("<Command-q>", lambda e: self._on_closing())

    def _create_gui(self):
        """Erstellt die Haupt-GUI-Struktur"""

        # Top-Bar mit Theme-Button
        top_bar = ctk.CTkFrame(self.root, height=40)
        top_bar.pack(fill="x", padx=5, pady=5)

        # Theme-Toggle-Button (rechts) mit Hover-Effekt
        self.theme_button = ctk.CTkButton(
            top_bar,
            text="☀️ Light",
            width=100,
            command=self._toggle_theme,
            hover_color="#64B5F6",  # Hellblau beim Hover
            corner_radius=8
        )
        self.theme_button.pack(side="right", padx=5)
        self._update_theme_button_text()

        # Haupt-Container (Horizontal: Explorer | Content)
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=0, minsize=250)
        main_container.grid_columnconfigure(1, weight=1)

        # ========== LINKS: Projekt-Explorer ==========
        explorer_width = self.settings_manager.get_explorer_width()

        self.explorer = ProjectExplorer(
            main_container,
            on_position_open=self._on_explorer_position_open,
            on_new_position=self._new_position,  # + Button Handler
            on_position_deleted=self._on_position_deleted  # Position gelöscht
        )
        self.explorer.grid(row=0, column=0, sticky="nsew", padx=(0, 2))

        # ========== RECHTS: Tab-Container ==========

        # Position-Tabs (Level 1)
        self.position_tabs = PositionTabManager(
            main_container,
            module_tab_creator=self._create_module_tabs
        )
        self.position_tabs.grid(row=0, column=1, sticky="nsew")

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

            messagebox.showinfo(
                "Erfolg", f"Projekt '{project_name}' erstellt!")

        except FileExistsError:
            messagebox.showerror(
                "Fehler", f"Projekt '{project_name}' existiert bereits")
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Projekts: {e}")
            messagebox.showerror(
                "Fehler", f"Projekt konnte nicht erstellt werden:\n{e}")

    def _open_project(self):
        """Öffnet ein bestehendes Projekt"""
        # Starte im zuletzt verwendeten Verzeichnis (falls vorhanden)
        last_dir = self.settings_manager.get_last_project_dir()
        if not last_dir or not Path(last_dir).exists():
            last_dir = self.project_manager.projects_root

        # Projekt-Ordner auswählen
        project_dir = filedialog.askdirectory(
            title="Projekt öffnen",
            initialdir=last_dir
        )

        if not project_dir:
            return

        project_path = Path(project_dir)

        # Prüfe, ob project.json existiert
        if not (project_path / "project.json").exists():
            messagebox.showerror("Fehler", "Kein gültiges Projekt-Verzeichnis")
            return

        try:
            # Speichere Verzeichnis für zukünftige Dialoge
            self.settings_manager.set_last_project_dir(
                str(project_path.parent))

            self._load_project(project_path)
        except Exception as e:
            logger.error(f"Fehler beim Öffnen des Projekts: {e}")
            messagebox.showerror(
                "Fehler", f"Projekt konnte nicht geöffnet werden:\n{e}")

    def _load_project(self, project_path: Path):
        """
        Lädt ein Projekt.

        Args:
            project_path: Pfad zum Projektverzeichnis
        """
        # Altes Projekt schließen (inkl. ALLE Tabs!)
        if self.current_project_path:
            logger.info(
                f"🔄 Schließe altes Projekt: {self.current_project_path}")
            self._close_project()
        else:
            # Auch wenn kein Projekt offen ist: Tabs könnten offen sein (z.B. Schnellstart)
            logger.info("🔄 Kein altes Projekt, aber räume Tabs auf")
            self.position_tabs.cleanup()

        # Projekt öffnen
        project_data = self.project_manager.open_project(project_path)
        self.current_project_path = project_path

        # Explorer aktualisieren
        self.explorer.load_project(project_path, self.project_manager)

        # Menü-Status aktualisieren
        self._update_menu_states()

        # In Recent-Liste (MIT UUID und Name)
        project_uuid = self.project_manager.get_project_uuid()
        project_name = project_data.get('name', project_path.name)
        self.settings_manager.add_recent_project(
            str(project_path),
            project_uuid=project_uuid,
            project_name=project_name
        )
        self.settings_manager.set_last_opened_project(str(project_path))

        # Fenster-Titel
        self.root.title(f"Statikprogramm v2.0 - {project_data['name']}")

        logger.info(f"Projekt geladen: {project_data['name']}")

        # Automatisch erste Position öffnen (falls vorhanden)
        try:
            positions = self.project_manager.list_positions()
            logger.debug(f"Gefundene Positionen: {len(positions)}")

            if positions and len(positions) > 0:
                # Nimm einfach die erste Position (alphabetisch nach Dateiname)
                first_position = sorted(
                    positions, key=lambda p: p.get('file_path', ''))[0]
                logger.debug(f"Erste Position Data: {first_position}")

                first_position_path = Path(first_position['file_path'])
                logger.debug(f"Position Pfad: {first_position_path}")

                # Versuche einen Namen zu finden
                position_name = (
                    first_position.get('position_name') or
                    first_position.get('position_nummer') or
                    first_position_path.stem  # Dateiname ohne Endung
                )

                logger.info(
                    f"🚀 Öffne automatisch erste Position: {position_name}")

                # Lade die Position erst (gibt PositionModel zurück)
                position_model = self.project_manager.load_position(
                    first_position_path)

                # Jetzt öffnen mit dem PositionModel
                self.position_tabs.open_position(
                    position_model, first_position_path)
                logger.info(
                    f"✅ Position erfolgreich geöffnet: {position_name}")
            else:
                logger.info(
                    "ℹ️ Keine Positionen im Projekt gefunden - keine automatische Auswahl")
        except Exception as e:
            logger.error(
                f"❌ Konnte erste Position nicht automatisch öffnen: {e}", exc_info=True)

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

        pos_nummer = simpledialog.askstring(
            "Neue Position", "Position-Nummer (z.B. 1.01):")
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
            position_file = self.project_manager.create_position(
                position_model)

            # Explorer aktualisieren
            self.explorer.refresh(self.project_manager)

            # Position öffnen
            self.position_tabs.open_position(position_model, position_file)

            logger.info(
                f"Position erstellt: {position_model.get_display_name()}")

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Position: {e}")
            messagebox.showerror(
                "Fehler", f"Position konnte nicht erstellt werden:\n{e}")

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
            messagebox.showerror(
                "Fehler", f"Position konnte nicht geöffnet werden:\n{e}")

    def _close_current_position(self):
        """Schließt die aktuelle Position"""
        self.position_tabs.close_current_position()

    def _on_position_deleted(self, position_file: Path):
        """
        Callback wenn Position gelöscht wurde.
        Schließt den zugehörigen Tab.

        Args:
            position_file: Pfad zur gelöschten Position
        """
        logger.info(f"Position wurde gelöscht, schließe Tab: {position_file}")
        self.position_tabs.close_position(position_file)

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

    def _save_project_as(self):
        """Speichert Projekt unter neuem Namen (für temporäre Projekte)"""
        if not self.current_project_path:
            return

        from tkinter import simpledialog
        import shutil
        import uuid

        # Neuen Projektnamen abfragen
        new_name = simpledialog.askstring(
            "Projekt speichern unter",
            "Neuer Projektname:",
            initialvalue=self.current_project_path.name
        )

        if not new_name:
            return

        try:
            # Alle Positionen speichern
            self.position_tabs.save_all_positions(self.project_manager)

            # Neuen Projektpfad erstellen
            new_project_path = self.project_manager.projects_root / new_name

            if new_project_path.exists():
                result = messagebox.askyesno(
                    "Projekt existiert bereits",
                    f"Ein Projekt mit dem Namen '{new_name}' existiert bereits.\nÜberschreiben?"
                )
                if not result:
                    return
                shutil.rmtree(new_project_path)

            # Projekt kopieren
            shutil.copytree(self.current_project_path, new_project_path)

            # project.json aktualisieren
            import json
            project_json = new_project_path / "project.json"
            with open(project_json, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            project_data['name'] = new_name
            # Neue UUID für kopiertes Projekt
            project_data['uuid'] = str(uuid.uuid4())

            with open(project_json, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)

            # Altes Projekt schließen, neues öffnen
            old_project = self.current_project_path
            self._load_project(new_project_path)

            # Optionally: Temporäres Projekt löschen
            if "Schnellstart" in old_project.name:
                result = messagebox.askyesno(
                    "Temporäres Projekt löschen?",
                    "Möchten Sie das temporäre Schnellstart-Projekt löschen?"
                )
                if result:
                    try:
                        shutil.rmtree(old_project)
                        logger.info(
                            f"Temporäres Projekt gelöscht: {old_project}")
                    except Exception as e:
                        logger.warning(
                            f"Konnte temp. Projekt nicht löschen: {e}")

            messagebox.showinfo(
                "Erfolg", f"Projekt gespeichert als '{new_name}'")

        except Exception as e:
            logger.error(f"Fehler beim Speichern unter: {e}")
            messagebox.showerror(
                "Fehler", f"Speichern unter fehlgeschlagen:\n{e}")

    # ========== Hilfsfunktionen ==========

    def _refresh_explorer(self):
        """Aktualisiert den Explorer"""
        if self.current_project_path:
            self.explorer.refresh(self.project_manager)

    def _toggle_theme(self):
        """Wechselt zwischen Light und Dark Mode"""
        # ThemeManager toggle nutzen
        ThemeManager.toggle_mode()
        new_mode = ThemeManager.get_current_mode()

        # CustomTkinter Appearance Mode synchronisieren
        ctk.set_appearance_mode(new_mode)

        # Matplotlib umkonfigurieren
        ThemeManager.configure_matplotlib()

        # Button-Text aktualisieren
        self._update_theme_button_text()

        # Project Explorer Theme aktualisieren
        self.explorer._apply_theme_to_treeview()

        logger.info(f"Theme gewechselt zu: {new_mode}")

    def _update_theme_button_text(self):
        """Aktualisiert den Theme-Button-Text basierend auf aktuellem Mode"""
        current_mode = ThemeManager.get_current_mode()
        if current_mode == "dark":
            self.theme_button.configure(text="☀️ Light")
        else:
            self.theme_button.configure(text="🌙 Dark")

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
        self.file_menu.entryconfig(
            "Projekt speichern unter...", state=state_project)
        self.file_menu.entryconfig("Position schließen", state=state_position)

    def _show_welcome_dialog(self):
        """Zeigt den Welcome-Dialog beim Start"""
        WelcomeDialog.show_dialog(
            self.root,
            self.settings_manager,
            self._on_welcome_choice
        )

    def _on_welcome_choice(self, action: str, path: Optional[str]):
        """
        Handler für Welcome-Dialog-Auswahl.

        Args:
            action: "new", "open", "recent", "quickstart", "cancel"
            path: Projekt-Pfad (nur bei "recent")
        """
        logger.info(f"Welcome-Dialog Auswahl: {action}, path={path}")

        if action == "new":
            self._new_project()

        elif action == "open":
            self._open_project()

        elif action == "recent" and path:
            try:
                self._load_project(Path(path))
            except Exception as e:
                logger.error(f"Fehler beim Öffnen von Recent Project: {e}")
                messagebox.showerror(
                    "Fehler", f"Projekt konnte nicht geöffnet werden:\n{e}")

        elif action == "quickstart":
            self._quickstart_mode()

        elif action == "cancel":
            logger.info("Welcome-Dialog abgebrochen")

    def _quickstart_mode(self):
        """
        Schnellstart-Modus: Erstellt temporäres Projekt.
        """
        import tempfile
        from datetime import datetime

        # Temporäres Projekt erstellen
        temp_name = f"Schnellstart_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            project_path = self.project_manager.create_project(
                temp_name,
                "Temporäres Projekt für Schnellstart"
            )

            # Projekt öffnen
            self._load_project(project_path)

            # Automatisch erste Position erstellen
            position_model = PositionModel(
                position_nummer="1",
                position_name="Schnellstart-Position"
            )

            position_file = self.project_manager.create_position(
                position_model)
            self.explorer.refresh(self.project_manager)
            self.position_tabs.open_position(position_model, position_file)

            logger.info("Schnellstart-Modus aktiviert")

        except Exception as e:
            logger.error(f"Fehler im Schnellstart-Modus: {e}")
            messagebox.showerror(
                "Fehler", f"Schnellstart fehlgeschlagen:\n{e}")

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

    root = ctk.CTk()
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
