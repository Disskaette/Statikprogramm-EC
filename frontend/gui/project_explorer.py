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

    def __init__(self, parent, on_position_open: Optional[Callable] = None,
                 on_new_position: Optional[Callable] = None,
                 on_position_deleted: Optional[Callable] = None):
        """
        Args:
            parent: Eltern-Widget
            on_position_open: Callback beim Doppelklick auf Position
            on_new_position: Callback beim Klick auf + Button
            on_position_deleted: Callback wenn Position gelöscht wurde
        """
        super().__init__(parent)

        self.on_position_open = on_position_open
        self.on_new_position = on_new_position
        self.on_position_deleted = on_position_deleted
        self.current_project_path: Optional[Path] = None
        self.current_project_manager = None  # Speichere ProjectManager-Referenz

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

        # TreeView mit MULTI-SELECT
        self.tree = ttk.Treeview(tree_container, yscrollcommand=scrollbar.set,
                                 selectmode="extended")  # Multi-Select!
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)

        # Drag & Drop State
        self._drag_data = {
            "x": 0,
            "y": 0,
            "dragging": False,
            "threshold": 5,  # Pixel bevor Drag startet
            "hover_item": None,  # Aktuell gehovertes Item
            "original_tags": None  # Ursprüngliche Tags des Hover-Items
        }

        # Spalten konfigurieren
        self.tree["columns"] = ("type",)
        self.tree.column("#0", width=200, minwidth=150)
        self.tree.column("type", width=80, minwidth=50)

        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("type", text="Typ", anchor="w")

        # Events
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        self.tree.bind("<Button-2>", self._on_right_click)  # macOS Right-Click
        # Windows/Linux Right-Click
        self.tree.bind("<Button-3>", self._on_right_click)

        # Drag & Drop Events
        self.tree.bind("<ButtonPress-1>", self._on_drag_start)
        self.tree.bind("<B1-Motion>", self._on_drag_motion)
        self.tree.bind("<ButtonRelease-1>", self._on_drag_release)

        # Kontextmenü erstellen
        self._create_context_menu()

        # + Button
        add_button_frame = ttk.Frame(self)
        add_button_frame.pack(fill="x", padx=5, pady=5)

        self.add_position_button = ttk.Button(
            add_button_frame,
            text="+ Neue Position",
            command=self._on_add_position,
        )
        self.add_position_button.pack(fill="x")

        # Theme initial anwenden
        self._apply_theme_to_treeview()

    def load_project(self, project_path: Path, project_manager):
        """
        Lädt ein Projekt und zeigt es im Baum an.

        Args:
            project_path: Pfad zum Projekt
            project_manager: ProjectManager-Instanz
        """
        self.current_project_path = project_path
        self.current_project_manager = project_manager  # Speichere für späteren Zugriff

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

        # + Button aktivieren
        self.add_position_button.config(state="normal")

        logger.info(f"Projekt geladen in Explorer: {project_name}")

    def _apply_theme_to_treeview(self):
        """Wendet das aktuelle Theme auf die TreeView an (Dark/Light Mode)."""
        from frontend.gui.theme_config import ThemeManager

        style = ttk.Style(self)
        current_mode = ThemeManager.get_current_mode()

        # WICHTIG: Für TreeView NICHT das aqua-Theme nutzen, sondern 'clam' (besser stylingbar)
        try:
            style.theme_use('clam')
        except:
            pass

        # Farben aus ThemeManager holen (konsistent mit restlicher Anwendung)
        # Verwende bg_secondary für TreeView (weicher als bg_main)
        bg = ThemeManager.get_color('bg_secondary')
        fg = ThemeManager.get_color('text_main')
        field_bg = ThemeManager.get_color('bg_secondary')
        selected_bg = ThemeManager.get_color('bg_selected')
        selected_fg = ThemeManager.get_color('text_main')
        border = ThemeManager.get_color('border')
        bg_header = ThemeManager.get_color(
            'bg_main')  # Header etwas dunkler/heller

        # TreeView Hauptstyle
        style.configure('Treeview',
                        background=bg,
                        foreground=fg,
                        fieldbackground=field_bg,
                        borderwidth=0,
                        rowheight=25)

        # TreeView Selection/Hover States
        style.map('Treeview',
                  background=[('selected', selected_bg),
                              ('active', bg)],
                  foreground=[('selected', selected_fg), ('active', fg)])

        # TreeView Header (Spaltenüberschriften)
        style.configure('Treeview.Heading',
                        background=bg_header,
                        foreground=fg,
                        borderwidth=1,
                        relief='flat')

        style.map('Treeview.Heading',
                  background=[('active', border)],
                  foreground=[('active', fg)])

        # Tag für Drag & Drop Ziel (grüner Highlight)
        self.tree.tag_configure('drop_target',
                                background=ThemeManager.get_color(
                                    'accent_green'),
                                foreground=fg)

        logger.debug(f"TreeView Theme aktualisiert: {current_mode}")

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
                                             # Pfad als zweiter Tag
                                             tags=("folder", str(item)))
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

        # + Button deaktivieren
        self.add_position_button.config(state="disabled")

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

    # ========== Kontextmenü & Aktionen ==========

    def _create_context_menu(self):
        """Erstellt das Kontextmenü"""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="Öffnen", command=self._context_open)
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Neuer Ordner...", command=self._context_new_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Umbenennen", command=self._context_rename)
        self.context_menu.add_command(
            label="Duplizieren", command=self._context_duplicate)
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Löschen", command=self._context_delete)

    def _on_right_click(self, event):
        """Behandelt Rechtsklick (Multi-Select aware)"""
        # Finde Item unter Mauszeiger
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        # WICHTIG: Behalte Multi-Selection bei!
        # Nur wenn das Item NICHT bereits selektiert ist, setze neue Selection
        current_selection = self.tree.selection()
        if item_id not in current_selection:
            # Item nicht in aktueller Selection → nur dieses selektieren
            self.tree.selection_set(item_id)
        # Sonst: Behalte aktuelle Multi-Selection bei

        # Zeige Kontextmenü
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_add_position(self):
        """Neue Position hinzufügen (über + Button)"""
        if self.on_new_position:
            self.on_new_position()
        else:
            logger.warning("Kein on_new_position Callback registriert")

    def _context_open(self):
        """Öffnet die ausgewählte Position"""
        path = self.get_selected_path()
        if path and self.on_position_open:
            self.on_position_open(path)

    def _context_rename(self):
        """Benennt Position/Ordner um"""
        from tkinter import simpledialog

        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        tags = self.tree.item(item_id, "tags")
        current_text = self.tree.item(item_id, "text")

        # Aktuellen Namen ohne Emoji
        current_name = current_text.replace("📄 ", "").replace("📁 ", "")

        # Neuen Namen abfragen
        new_name = simpledialog.askstring(
            "Umbenennen", "Neuer Name:", initialvalue=current_name)
        if not new_name:
            return

        # Position umbenennen
        if "position" in tags and len(tags) > 1:
            old_path = Path(tags[1])
            new_path = old_path.parent / f"{new_name}.json"

            try:
                old_path.rename(new_path)
                logger.info(f"Position umbenannt: {old_path} → {new_path}")
                self.refresh(self.current_project_manager)  # Refresh Explorer
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror(
                    "Fehler", f"Umbenennen fehlgeschlagen:\n{e}")

    def _context_duplicate(self):
        """Dupliziert die ausgewählte Position"""
        import json
        import shutil
        from tkinter import simpledialog, messagebox

        path = self.get_selected_path()
        if not path:
            return

        # Neuen Namen abfragen
        new_name = simpledialog.askstring("Duplizieren", "Name der Kopie:")
        if not new_name:
            return

        try:
            # Kopiere Datei
            new_path = path.parent / f"{new_name}.json"
            shutil.copy(path, new_path)

            # Ändere position_name in JSON
            with open(new_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['position_name'] = new_name

            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Position dupliziert: {path} → {new_path}")
            self.refresh(self.current_project_manager)

        except Exception as e:
            messagebox.showerror("Fehler", f"Duplizieren fehlgeschlagen:\n{e}")

    def _context_new_folder(self):
        """Erstellt einen neuen Ordner"""
        from tkinter import simpledialog, messagebox

        # Prüfe, ob ein Projekt geladen ist
        if not self.current_project_path:
            messagebox.showwarning(
                "Kein Projekt",
                "Bitte öffnen Sie zuerst ein Projekt, um Ordner zu erstellen."
            )
            return

        # Finde Ziel-Ordner (wo der neue Ordner erstellt werden soll)
        selection = self.tree.selection()
        target_path = self.current_project_path

        if selection:
            item_id = selection[0]
            tags = self.tree.item(item_id, "tags")

            # Wenn Position ausgewählt: Im gleichen Ordner erstellen
            if "position" in tags and len(tags) > 1:
                target_path = Path(tags[1]).parent
            # Wenn Ordner ausgewählt: Im Ordner erstellen
            elif "folder" in tags and len(tags) > 1:
                target_path = Path(tags[1])

        # Ordnernamen abfragen
        folder_name = simpledialog.askstring(
            "Neuer Ordner",
            "Ordnername (z.B. 'EG', 'OG', 'Dachgeschoss'):"
        )

        if not folder_name:
            return

        try:
            new_folder = target_path / folder_name
            new_folder.mkdir(parents=True, exist_ok=False)

            logger.info(f"Ordner erstellt: {new_folder}")
            self.refresh(self.current_project_manager)

        except FileExistsError:
            messagebox.showerror(
                "Fehler", f"Ordner '{folder_name}' existiert bereits")
        except Exception as e:
            messagebox.showerror(
                "Fehler", f"Ordner erstellen fehlgeschlagen:\n{e}")

    def _context_delete(self):
        """Löscht die ausgewählte(n) Position(en) oder Ordner (Multi-Select Support)"""
        from tkinter import messagebox
        import shutil

        selection = self.tree.selection()
        if not selection:
            return

        # Multi-Select: Mehrere Items löschen
        if len(selection) > 1:
            result = messagebox.askyesno(
                "Mehrere Elemente löschen",
                f"Möchten Sie {len(selection)} Elemente wirklich löschen?\n\nDieser Vorgang kann nicht rückgängig gemacht werden!"
            )

            if not result:
                return

            # Lösche alle selektierten Items
            deleted_count = 0
            errors = []

            for item_id in selection:
                try:
                    tags = self.tree.item(item_id, "tags")

                    if "position" in tags and len(tags) > 1:
                        path = Path(tags[1])
                        path.unlink()

                        if self.on_position_deleted:
                            self.on_position_deleted(path)

                        deleted_count += 1
                        logger.info(f"Position gelöscht: {path}")

                    elif "folder" in tags and len(tags) > 1:
                        folder_path = Path(tags[1])
                        shutil.rmtree(folder_path)
                        deleted_count += 1
                        logger.info(f"Ordner gelöscht: {folder_path}")

                except Exception as e:
                    errors.append(str(e))
                    logger.error(f"Fehler beim Löschen: {e}")

            # Feedback
            if deleted_count > 0:
                self.refresh(self.current_project_manager)

            if errors:
                messagebox.showerror(
                    "Fehler",
                    f"{deleted_count} Element(e) gelöscht.\n\nFehler bei {len(errors)} Element(en):\n" + "\n".join(
                        errors[:3])
                )

            return

        # Single-Select: Original-Logik
        item_id = selection[0]
        tags = self.tree.item(item_id, "tags")

        # Position löschen
        if "position" in tags and len(tags) > 1:
            path = Path(tags[1])

            # Sicherheitsabfrage
            result = messagebox.askyesno(
                "Position löschen",
                f"Möchten Sie diese Position wirklich löschen?\n\n{path.name}\n\nDieser Vorgang kann nicht rückgängig gemacht werden!"
            )

            if not result:
                return

            try:
                path.unlink()
                logger.info(f"Position gelöscht: {path}")

                # Callback aufrufen (damit Tab geschlossen wird)
                if self.on_position_deleted:
                    self.on_position_deleted(path)

                self.refresh(self.current_project_manager)

            except Exception as e:
                messagebox.showerror("Fehler", f"Löschen fehlgeschlagen:\n{e}")

        # Ordner löschen
        elif "folder" in tags and len(tags) > 1:
            folder_path = Path(tags[1])

            # Prüfe ob Ordner leer ist
            if any(folder_path.iterdir()):
                result = messagebox.askyesno(
                    "Ordner löschen",
                    f"Der Ordner '{folder_path.name}' ist nicht leer!\n\nMöchten Sie den Ordner mit allen Inhalten wirklich löschen?\n\nDieser Vorgang kann nicht rückgängig gemacht werden!"
                )
            else:
                result = messagebox.askyesno(
                    "Ordner löschen",
                    f"Möchten Sie den Ordner '{folder_path.name}' wirklich löschen?"
                )

            if not result:
                return

            try:
                shutil.rmtree(folder_path)
                logger.info(f"Ordner gelöscht: {folder_path}")
                self.refresh(self.current_project_manager)

            except Exception as e:
                messagebox.showerror(
                    "Fehler", f"Ordner löschen fehlgeschlagen:\n{e}")

    # ========== Drag & Drop Methoden ==========

    def _on_drag_start(self, event):
        """Start des Drag-Vorgangs"""
        # Speichere Start-Position
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["dragging"] = False
        self._drag_data["item"] = self.tree.identify_row(event.y)

    def _on_drag_motion(self, event):
        """Während des Dragging - zeige visuelles Feedback"""
        if not self._drag_data.get("item"):
            return

        # Prüfe ob Threshold überschritten
        dx = abs(event.x - self._drag_data["x"])
        dy = abs(event.y - self._drag_data["y"])

        if dx > self._drag_data["threshold"] or dy > self._drag_data["threshold"]:
            self._drag_data["dragging"] = True

            # Visuelles Hover-Feedback
            target_item = self.tree.identify_row(event.y)

            # Entferne vorheriges Hover (stelle ursprüngliche Tags wieder her)
            if self._drag_data["hover_item"] and self._drag_data["hover_item"] != target_item:
                try:
                    if self._drag_data["original_tags"]:
                        self.tree.item(
                            self._drag_data["hover_item"], tags=self._drag_data["original_tags"])
                except:
                    pass

            # Neues Hover-Item markieren
            if target_item:
                target_tags = self.tree.item(target_item, "tags")
                source_tags = self.tree.item(self._drag_data["item"], "tags")

                # Nur Ordner oder Projekt als Drop-Ziel erlauben
                if ("folder" in target_tags or "project" in target_tags) and "position" in source_tags:
                    # Speichere ursprüngliche Tags VOR Überschreiben
                    self._drag_data["original_tags"] = target_tags
                    # Füge "drop_target" zu den bestehenden Tags hinzu
                    new_tags = list(target_tags) + ["drop_target"]
                    self.tree.item(target_item, tags=tuple(new_tags))
                    self._drag_data["hover_item"] = target_item
                    # Cursor ändern
                    self.tree.config(cursor="hand2")
                else:
                    # Ungültiges Drop-Ziel
                    self.tree.config(cursor="X_cursor")
                    self._drag_data["hover_item"] = None
                    self._drag_data["original_tags"] = None
            else:
                self.tree.config(cursor="arrow")
                self._drag_data["hover_item"] = None
                self._drag_data["original_tags"] = None

    def _on_drag_release(self, event):
        """Ende des Drag-Vorgangs - führe Move aus"""
        # Prüfe ZUERST ob es ein echtes Drag war
        if not self._drag_data.get("dragging"):
            # Kein echtes Drag → normaler Click → trotzdem aufräumen!
            if self._drag_data.get("hover_item") and self._drag_data.get("original_tags"):
                try:
                    self.tree.item(
                        self._drag_data["hover_item"], tags=self._drag_data["original_tags"])
                except:
                    pass
            self.tree.config(cursor="arrow")
            self._drag_data["hover_item"] = None
            self._drag_data["original_tags"] = None
            return

        # Entferne Hover-Highlighting (stelle ursprüngliche Tags wieder her)
        if self._drag_data.get("hover_item") and self._drag_data.get("original_tags"):
            try:
                self.tree.item(
                    self._drag_data["hover_item"], tags=self._drag_data["original_tags"])
            except:
                pass

        # Cursor zurücksetzen
        self.tree.config(cursor="arrow")
        self._drag_data["hover_item"] = None
        self._drag_data["original_tags"] = None

        source_item = self._drag_data.get("item")
        target_item = self.tree.identify_row(event.y)

        if not source_item or not target_item or source_item == target_item:
            self._drag_data["dragging"] = False
            return

        # Hole Item-Daten
        source_tags = self.tree.item(source_item, "tags")
        target_tags = self.tree.item(target_item, "tags")

        # Nur Positionen können verschoben werden
        if "position" not in source_tags:
            self._drag_data["dragging"] = False
            return

        # Ziel kann Ordner ODER Projekt sein
        if "folder" in target_tags:
            # In Ordner verschieben
            self._move_position_to_folder(source_tags[1], target_tags[1])
        elif "project" in target_tags:
            # In Projekt-Root verschieben
            self._move_position_to_project_root(source_tags[1], target_tags[1])

        self._drag_data["dragging"] = False

    def _move_position_to_folder(self, position_path_str, folder_path_str):
        """Verschiebt eine Position in einen Ordner"""
        try:
            from tkinter import messagebox
            import shutil

            position_path = Path(position_path_str)
            folder_path = Path(folder_path_str)

            # Prüfe ob Position existiert
            if not position_path.exists():
                messagebox.showerror(
                    "Fehler", "Position existiert nicht mehr!")
                return

            # Prüfe ob Zielordner existiert
            if not folder_path.exists():
                messagebox.showerror("Fehler", "Zielordner existiert nicht!")
                return

            # Ziel-Dateiname
            new_path = folder_path / position_path.name

            # Prüfe ob bereits existiert
            if new_path.exists():
                messagebox.showerror(
                    "Fehler", f"Eine Position mit dem Namen '{position_path.name}' existiert bereits im Zielordner!")
                return

            # Verschiebe Datei
            shutil.move(str(position_path), str(new_path))
            logger.info(f"Position verschoben: {position_path} → {new_path}")

            # Refresh TreeView
            self.refresh(self.current_project_manager)

            messagebox.showinfo(
                "Erfolg", f"Position '{position_path.name}' wurde in '{folder_path.name}' verschoben.")

        except Exception as e:
            logger.error(f"Fehler beim Verschieben: {e}")
            messagebox.showerror("Fehler", f"Verschieben fehlgeschlagen:\n{e}")

    def _move_position_to_project_root(self, position_path_str, project_path_str):
        """Verschiebt eine Position in den Projekt-Root (raus aus Ordnern)"""
        try:
            from tkinter import messagebox
            import shutil

            position_path = Path(position_path_str)
            project_path = Path(project_path_str)

            # Prüfe ob Position existiert
            if not position_path.exists():
                messagebox.showerror(
                    "Fehler", "Position existiert nicht mehr!")
                return

            # Prüfe ob Projekt existiert
            if not project_path.exists():
                messagebox.showerror("Fehler", "Projekt existiert nicht!")
                return

            # Ziel-Dateiname (im Projekt-Root)
            new_path = project_path / position_path.name

            # Prüfe ob bereits im Root ist
            if position_path.parent == project_path:
                messagebox.showinfo(
                    "Info", "Position ist bereits im Projekt-Root.")
                return

            # Prüfe ob bereits existiert
            if new_path.exists():
                messagebox.showerror(
                    "Fehler", f"Eine Position mit dem Namen '{position_path.name}' existiert bereits im Projekt-Root!")
                return

            # Verschiebe Datei
            shutil.move(str(position_path), str(new_path))
            logger.info(
                f"Position in Projekt-Root verschoben: {position_path} → {new_path}")

            # Refresh TreeView
            self.refresh(self.current_project_manager)

            messagebox.showinfo(
                "Erfolg", f"Position '{position_path.name}' wurde in den Projekt-Root verschoben.")

        except Exception as e:
            logger.error(f"Fehler beim Verschieben: {e}")
            messagebox.showerror("Fehler", f"Verschieben fehlgeschlagen:\n{e}")
