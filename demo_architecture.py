"""
DEMO: Zeigt die neue Architektur in Aktion.

Dieses Skript demonstriert:
1. Projektmanagement (Erstellen, Öffnen, Speichern)
2. Position-Verwaltung
3. Modul-System (Registry)
4. Datenpersistenz

NICHT produktiv verwenden! Nur zu Demonstrations-/Testzwecken.
"""

import sys
from pathlib import Path

# Füge das Projektverzeichnis zum Python-Path hinzu
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.project import ProjectManager, PositionModel, SettingsManager
from frontend.modules.module_registry import get_registry

def demo_projektmanagement():
    """Demonstriert Projektmanagement-Funktionen"""
    print("\n" + "="*60)
    print("DEMO 1: Projektmanagement")
    print("="*60)
    
    # ProjectManager initialisieren
    pm = ProjectManager()
    print(f"✅ ProjectManager initialisiert")
    print(f"   Projekte-Verzeichnis: {pm.projects_root}")
    
    # Neues Projekt erstellen
    try:
        project_path = pm.create_project(
            project_name="Demo Wohnhaus",
            description="Beispielprojekt zur Demonstration"
        )
        print(f"\n✅ Projekt erstellt: {project_path}")
    except FileExistsError:
        print(f"\n⚠️  Projekt existiert bereits, öffne es...")
        project_path = pm.projects_root / "Demo_Wohnhaus"
    
    # Projekt öffnen
    project_data = pm.open_project(project_path)
    print(f"✅ Projekt geöffnet:")
    print(f"   Name: {project_data['name']}")
    print(f"   Erstellt: {project_data['created']}")
    
    # Alle Projekte auflisten
    all_projects = pm.list_projects()
    print(f"\n📁 Verfügbare Projekte ({len(all_projects)}):")
    for proj in all_projects:
        print(f"   - {proj['name']} ({proj['path']})")
    
    return pm

def demo_position_verwaltung(pm: ProjectManager):
    """Demonstriert Position-Verwaltung"""
    print("\n" + "="*60)
    print("DEMO 2: Position-Verwaltung")
    print("="*60)
    
    # Neue Position erstellen
    position1 = PositionModel(
        position_nummer="1.01",
        position_name="HT 1 - Wohnzimmer",
        active_module="durchlauftraeger"
    )
    
    # Beispiel-Daten für Durchlaufträger-Modul
    position1.set_module_data("durchlauftraeger", {
        "sprungmass": 1.0,
        "lasten": [
            {"lastfall": "g", "wert": 7.41, "kategorie": "Eigengewicht"},
            {"lastfall": "s", "wert": 5.0, "kategorie": "Schneelast"}
        ],
        "spannweiten": {"feld_1": 5.0, "feld_2": 5.0},
        "querschnitt": {"breite_qs": 200, "hoehe_qs": 300}
    })
    
    # Position speichern
    pos_file = pm.create_position(position1)
    print(f"✅ Position erstellt: {pos_file}")
    print(f"   Nummer: {position1.position_nummer}")
    print(f"   Name: {position1.position_name}")
    print(f"   Aktives Modul: {position1.active_module}")
    
    # Weitere Position (in Unterordner)
    position2 = PositionModel(
        position_nummer="1.02",
        position_name="HT 2 - Küche"
    )
    pos_file2 = pm.create_position(position2, subfolder="EG")
    print(f"\n✅ Position 2 erstellt: {pos_file2}")
    
    # Position laden
    loaded_position = pm.load_position(pos_file)
    print(f"\n✅ Position geladen:")
    print(f"   {loaded_position.get_display_name()}")
    print(f"   Modul-Daten vorhanden: {list(loaded_position.modules.keys())}")
    
    # Alle Positionen auflisten
    all_positions = pm.list_positions()
    print(f"\n📄 Positionen im Projekt ({len(all_positions)}):")
    for pos in all_positions:
        print(f"   - {pos.get('position_nummer', '?')} - {pos.get('position_name', 'Unbenannt')}")
        print(f"     Datei: {pos.get('relative_path')}")
    
    return position1

def demo_settings_manager():
    """Demonstriert Settings-Verwaltung"""
    print("\n" + "="*60)
    print("DEMO 3: Settings Manager")
    print("="*60)
    
    sm = SettingsManager()
    print(f"✅ SettingsManager initialisiert")
    print(f"   Config-Verzeichnis: {sm.config_dir}")
    
    # Recent Projects
    sm.add_recent_project("/Users/test/Projekte/Projekt1")
    sm.add_recent_project("/Users/test/Projekte/Projekt2")
    
    recent = sm.get_recent_projects()
    print(f"\n📝 Recent Projects ({len(recent)}):")
    for path in recent:
        print(f"   - {path}")
    
    # UI Preferences
    print(f"\n🎨 UI Preferences:")
    print(f"   Fenstergeometrie: {sm.get_window_geometry()}")
    print(f"   Explorer-Breite: {sm.get_explorer_width()}px")
    print(f"   Welcome-Screen: {sm.should_show_welcome_screen()}")
    
    # Auto-Save
    print(f"\n💾 Auto-Save:")
    print(f"   Aktiviert: {sm.is_auto_save_enabled()}")
    print(f"   Intervall: {sm.get_auto_save_interval()}s")
    
    return sm

def demo_modul_registry():
    """Demonstriert Modul-Registry"""
    print("\n" + "="*60)
    print("DEMO 4: Modul-Registry")
    print("="*60)
    
    registry = get_registry()
    print(f"✅ ModuleRegistry initialisiert")
    
    # Dummy-Module registrieren (nur zur Demo)
    from frontend.modules.base_module import BaseModule
    import tkinter as tk
    
    class DummyDurchlauftraeger(BaseModule):
        def get_module_id(self): return "durchlauftraeger"
        def get_display_name(self): return "Durchlaufträger"
        def create_gui(self, parent): return tk.Frame(parent)
        def get_data(self): return {}
        def set_data(self, data): pass
        def get_results(self): return None
    
    class DummyBrandschutz(BaseModule):
        def get_module_id(self): return "brandschutz"
        def get_display_name(self): return "Brandschutz"
        def create_gui(self, parent): return tk.Frame(parent)
        def get_data(self): return {}
        def set_data(self, data): pass
        def get_results(self): return None
    
    class DummyAuflager(BaseModule):
        def get_module_id(self): return "auflager"
        def get_display_name(self): return "Auflagernachweis"
        def create_gui(self, parent): return tk.Frame(parent)
        def get_data(self): return {}
        def set_data(self, data): pass
        def get_results(self): return None
    
    # Module registrieren
    registry.register_module(DummyDurchlauftraeger, enabled=True, order=1)
    registry.register_module(DummyBrandschutz, enabled=False, order=2)  # Noch nicht implementiert
    registry.register_module(DummyAuflager, enabled=False, order=3)
    
    # Alle Module anzeigen
    all_modules = registry.get_all_modules()
    print(f"\n📦 Registrierte Module ({len(all_modules)}):")
    for mod in all_modules:
        status = "✅" if mod["enabled"] else "⏸️"
        print(f"   {status} {mod['name']} (ID: {mod['id']}, Order: {mod['order']})")
    
    # Nur aktivierte Module
    enabled = registry.get_all_modules(enabled_only=True)
    print(f"\n✅ Aktivierte Module ({len(enabled)}):")
    for mod in enabled:
        print(f"   - {mod['name']}")
    
    # Modul-Instanz erstellen
    print(f"\n🔨 Instanziiere Modul 'durchlauftraeger'...")
    instance = registry.create_module_instance("durchlauftraeger", eingabemaske_ref=None)
    if instance:
        print(f"   ✅ Instanz erstellt: {instance}")
        print(f"      ID: {instance.module_id}")
        print(f"      Name: {instance.display_name}")
    
    return registry

def demo_datenpersistenz(pm: ProjectManager, position: PositionModel):
    """Demonstriert vollständigen Save/Load-Zyklus"""
    print("\n" + "="*60)
    print("DEMO 5: Datenpersistenz (Save/Load-Zyklus)")
    print("="*60)
    
    # 1. Position modifizieren
    print("\n1️⃣ Position modifizieren...")
    position.set_module_data("durchlauftraeger", {
        "sprungmass": 1.2,  # Geändert von 1.0
        "lasten": [
            {"lastfall": "g", "wert": 8.0, "kategorie": "Eigengewicht"}  # Geändert
        ],
        "spannweiten": {"feld_1": 6.0},  # Geändert
        "querschnitt": {"breite_qs": 240, "hoehe_qs": 360}  # Geändert
    })
    print(f"   ✅ Daten geändert")
    
    # 2. Position speichern
    print("\n2️⃣ Position speichern...")
    pos_file = pm.current_project_path / position.get_filename()
    pm.save_position(position, pos_file)
    print(f"   ✅ Gespeichert nach: {pos_file}")
    
    # 3. Position neu laden
    print("\n3️⃣ Position neu laden...")
    reloaded_position = pm.load_position(pos_file)
    print(f"   ✅ Geladen von: {pos_file}")
    
    # 4. Daten vergleichen
    print("\n4️⃣ Daten-Vergleich:")
    original_data = position.get_module_data("durchlauftraeger")
    reloaded_data = reloaded_position.get_module_data("durchlauftraeger")
    
    print(f"   Original  - Sprungmaß: {original_data['sprungmass']}")
    print(f"   Reloaded  - Sprungmaß: {reloaded_data['sprungmass']}")
    print(f"   Match: {original_data == reloaded_data} ✅")
    
    # 5. JSON-Datei anzeigen
    print("\n5️⃣ JSON-Inhalt (Auszug):")
    with open(pos_file, 'r', encoding='utf-8') as f:
        import json
        content = json.load(f)
        print(json.dumps(content, indent=2, ensure_ascii=False)[:500] + "\n   ...")

def main():
    """Führt alle Demos aus"""
    print("\n" + "="*60)
    print("🏗️  ARCHITEKTUR-DEMO: Statikprogramm v2.0")
    print("="*60)
    print("\nDiese Demo zeigt die neue modulare Architektur:\n")
    print("  ✅ Projektmanagement")
    print("  ✅ Position-Verwaltung")
    print("  ✅ Settings & Recent Files")
    print("  ✅ Modul-Registry-System")
    print("  ✅ JSON-Datenpersistenz")
    
    try:
        # Demo-Reihenfolge
        pm = demo_projektmanagement()
        position = demo_position_verwaltung(pm)
        sm = demo_settings_manager()
        registry = demo_modul_registry()
        demo_datenpersistenz(pm, position)
        
        print("\n" + "="*60)
        print("✅ ALLE DEMOS ERFOLGREICH ABGESCHLOSSEN!")
        print("="*60)
        print(f"\n📁 Projekt-Verzeichnis: {pm.projects_root}")
        print(f"⚙️  Config-Verzeichnis: {sm.config_dir}")
        print("\nDie Architektur ist bereit für die GUI-Integration!")
        
    except Exception as e:
        print(f"\n❌ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
