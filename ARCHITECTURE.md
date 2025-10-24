# Architektur-Dokumentation: Statikprogramm v2.0

## Übersicht

### Zielsetzung
Transformation von einem Einzelposition-Tool zu einem vollständigen Projektmanagement-System mit:
- Multi-Position-Verwaltung
- Modulares Tab-System (2 Ebenen)
- Persistente Datenhaltung
- Erweiterbarkeit für neue Berechnungsmodule

---

## 1. Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│                    Hauptfenster (Root)                       │
│  ┌────────────────┬──────────────────────────────────────┐  │
│  │   Menüleiste   │  Datei | Bearbeiten | Ansicht | ?   │  │
│  └────────────────┴──────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  ┌──────────────┬────────────────────────────────────┐ │ │
│  │  │  Projekt-    │   Tab-Container (Level 1)         │ │ │
│  │  │  Explorer    │  ┌──────────────────────────────┐ │ │ │
│  │  │  (TreeView)  │  │ Pos 1.01 │ Pos 1.02 │ + │   │ │ │ │
│  │  │              │  └──────────────────────────────┘ │ │ │
│  │  │  📁 Projekt  │  ┌────────────────────────────────┐│ │ │
│  │  │   📄 Pos 1.01│  │ Tab-Container (Level 2)        ││ │ │
│  │  │   📄 Pos 1.02│  │ ┌───────────────────────────┐  ││ │ │
│  │  │   📁 Ordner  │  │ │Durchlauf│Brand│Auflager│  │  ││ │ │
│  │  │     📄 Pos.. │  │ └───────────────────────────┘  ││ │ │
│  │  │              │  │  ┌──────────────────────────┐  ││ │ │
│  │  │              │  │  │   Modul-Content          │  ││ │ │
│  │  │              │  │  │  (Eingabemaske +         │  ││ │ │
│  │  │              │  │  │   Ausgabebereich)        │  ││ │ │
│  │  │              │  │  └──────────────────────────┘  ││ │ │
│  │  └──────────────┴────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Verzeichnisstruktur

```
Statikprogramm/
├── main_v2.py                       # Entry Point (Haupt-GUI)
├── config/
│   ├── settings.json                # App-Settings (recent files, etc.)
│   └── module_registry.json         # Verfügbare Module
├── backend/
│   ├── database/
│   │   └── datenbank_holz.py
│   ├── calculations/
│   │   ├── lastenkombination.py
│   │   ├── feebb_berechnung.py
│   │   └── nachweis_ec5.py
│   ├── service/
│   │   └── orchestrator_service.py
│   └── project/                     # NEU
│       ├── project_manager.py       # Projektdatei-Verwaltung
│       ├── position_model.py        # Datenmodell für Position
│       └── serializer.py            # JSON/Pickle Serialisierung
├── frontend/
│   ├── gui/
│   │   ├── main_window.py           # NEU: Haupt-GUI (ersetzt eingabemaske.py)
│   │   ├── project_explorer.py      # NEU: Dateibaum-Widget
│   │   ├── position_tabs.py         # NEU: Tab-Manager Level 1
│   │   └── module_tabs.py           # NEU: Tab-Manager Level 2
│   ├── modules/                     # NEU: Alle Berechnungsmodule
│   │   ├── base_module.py           # Abstract Base Class
│   │   ├── durchlauftraeger/
│   │   │   ├── modul_durchlauf.py   # Refactored aus eingabemaske.py
│   │   │   └── config.json
│   │   ├── brandschutz/             # ZUKUNFT
│   │   │   ├── modul_brandschutz.py
│   │   │   └── config.json
│   │   └── auflager/                # ZUKUNFT
│   │       ├── modul_auflager.py
│   │       └── config.json
│   ├── display/
│   │   ├── anzeige_system.py
│   │   ├── anzeige_lastkombination.py
│   │   ├── anzeige_feebb.py
│   │   └── anzeige_nachweis_ec5.py
│   └── frontend_orchestrator.py
└── Projekte/                        # Benutzerdaten (außerhalb Git)
    ├── Mein_Projekt/
    │   ├── project.json             # Projekt-Metadaten
    │   ├── Position_1.01_HT1.json
    │   └── Ordner_EG/
    │       └── Position_1.02_HT2.json
    └── Anderes_Projekt/
        └── ...
```

---

## 3. Datenmodell

### 3.1 Projekt-Datei (`project.json`)
```json
{
  "name": "Mein Projekt",
  "created": "2025-10-23T16:00:00",
  "last_modified": "2025-10-23T17:30:00",
  "description": "Wohnhaus Mustergasse 1",
  "positions": [
    "Position_1.01_HT1.json",
    "Ordner_EG/Position_1.02_HT2.json"
  ]
}
```

### 3.2 Position-Datei (`Position_1.01_HT1.json`)
```json
{
  "position_nummer": "1.01",
  "position_name": "HT 1 - Wohnzimmer",
  "created": "2025-10-23T16:00:00",
  "last_modified": "2025-10-23T17:30:00",
  "active_module": "durchlauftraeger",
  "modules": {
    "durchlauftraeger": {
      "sprungmass": 1.0,
      "lasten": [...],
      "spannweiten": {...},
      "querschnitt": {...},
      "gebrauchstauglichkeit": {...},
      "berechnungsmodus": {...},
      "results": {
        "Lastfallkombinationen": {...},
        "Schnittgroessen": {...},
        "EC5_Nachweise": {...}
      }
    },
    "brandschutz": {
      "feuerwiderstandsklasse": "F30",
      "...": "..."
    },
    "auflager": null
  }
}
```

### 3.3 Settings-Datei (`settings.json`)
```json
{
  "recent_projects": [
    "/Users/.../Projekte/Mein_Projekt",
    "/Users/.../Projekte/Anderes_Projekt"
  ],
  "last_opened_position": "Position_1.01_HT1.json",
  "window_geometry": "1200x800+100+100",
  "ui_preferences": {
    "explorer_width": 250,
    "theme": "default"
  }
}
```

---

## 4. Modul-System

### 4.1 Base Module Interface
```python
class BaseModule(ABC):
    @abstractmethod
    def get_module_name(self) -> str:
        """Returns unique module identifier"""
        
    @abstractmethod
    def get_display_name(self) -> str:
        """Returns human-readable name for tabs"""
        
    @abstractmethod
    def create_gui(self, parent_frame) -> tk.Frame:
        """Creates and returns the module's GUI"""
        
    @abstractmethod
    def get_data(self) -> dict:
        """Returns current input data as dict"""
        
    @abstractmethod
    def set_data(self, data: dict):
        """Loads data into the module"""
        
    @abstractmethod
    def get_results(self) -> dict:
        """Returns calculation results"""
        
    def is_available(self) -> bool:
        """Check if module dependencies are met"""
        return True
```

### 4.2 Modul-Registrierung
```python
# In module_registry.py
AVAILABLE_MODULES = [
    {
        "id": "durchlauftraeger",
        "name": "Durchlaufträger",
        "class": "ModulDurchlauftraeger",
        "enabled": True,
        "order": 1
    },
    {
        "id": "brandschutz",
        "name": "Brandschutz",
        "class": "ModulBrandschutz",
        "enabled": False,  # Noch nicht implementiert
        "order": 2
    }
]
```

---

## 5. Implementierungsreihenfolge

### Phase 1: Backend (Projektmanagement) ✅
1. ✅ `project_manager.py` - CRUD für Projekte/Positionen
2. ✅ `position_model.py` - Datenklasse für Position
3. ✅ `serializer.py` - JSON-Persistierung

### Phase 2: GUI-Infrastruktur ✅
4. ✅ `main_window.py` - Hauptfenster mit Layout
5. ✅ `project_explorer.py` - TreeView für Dateien
6. ✅ `position_tabs.py` - Tab-Manager Level 1
7. ✅ `module_tabs.py` - Tab-Manager Level 2
8. ✅ `theme_config.py` - Dark/Light Mode Support

### Phase 3: Modul-System ✅
9. ✅ `base_module.py` - Abstract Base Class
10. ✅ Refactor: `eingabemaske.py` → `modul_durchlauftraeger.py`
11. ✅ `module_registry.py` - Dynamische Modul-Registrierung

### Phase 4: Integration ✅
12. ✅ Menüleiste (Datei → Neu, Öffnen, Speichern)
13. ✅ Speichern/Laden-Logik
14. ✅ Recent Files
15. ✅ Frontend-Orchestrator mit Threading

### Phase 5: Berechnungsmodule ✅
16. ✅ EC5-Nachweismodul implementiert
17. ✅ LaTeX-Rendering mit transparentem Background
18. ✅ Pattern-Loading Visualisierung
19. ✅ Dark Mode Theme-System

### Phase 6: Erweiterungen (Zukunft)
20. ⏳ Modul "Brandschutz"
21. ⏳ Modul "Auflagernachweis"
22. ⏳ Modul "Querzug"

---

## 6. Migrations-Strategie

### Bestehenden Code integrieren:
- `eingabemaske.py` wird zu `modules/durchlauftraeger/modul_durchlauf.py`
- Alle Display-Komponenten bleiben unverändert
- Orchestrator-Pattern bleibt erhalten
- Backend-Berechnungen bleiben unverändert

### Rückwärtskompatibilität:
- Alte Einzelposition-Daten können in neues Format konvertiert werden
- Import-Funktion für Legacy-Daten

---

## 7. Technologie-Stack

- **GUI**: tkinter/ttk (bestehend)
- **Persistenz**: JSON (Klartext, Git-freundlich)
- **Architektur**: MVC-Pattern
- **Modulsystem**: Plugin-Architektur mit Registry
- **State Management**: Observer-Pattern für Tab-Updates

---

## 8. Implementierte Features

- ✅ Multi-Projekt-Verwaltung
- ✅ Position-basierte Struktur
- ✅ TreeView Projekt-Explorer
- ✅ Modulares Tab-System (2 Ebenen)
- ✅ Dark/Light Mode Support
- ✅ LaTeX-Rendering (transparent)
- ✅ EC5-Nachweismodul komplett
- ✅ Pattern-Loading Visualisierung
- ✅ Thread-sicheres Frontend
- ✅ JSON-Persistierung

## 9. Offene Punkte / ToDo

- [ ] Versionierung von Positionsdateien
- [ ] Undo/Redo-Funktionalität
- [ ] Multi-User (Dateisperren)
- [ ] Export-Funktionen (PDF-Berichte)
- [ ] Vorlagen-System
- [ ] Weitere Berechnungsmodule (Brandschutz, Auflager)

---

## Status: Production Ready (v2.0)
Erstellt: 2025-10-23
Letztes Update: 2025-10-24
Version: 2.0.0
