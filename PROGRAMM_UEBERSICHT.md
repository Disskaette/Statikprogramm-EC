# 📊 Statikprogramm für Holztragwerke - Programm-Übersicht

## 🎯 Gesamtzweck des Programms

Dieses Programm ist ein **ingenieurmäßiges Berechnungstool für Holztragwerke** nach Eurocode 5 (EC5) und Eurocode 0/1 (EC0/EC1). Es ermöglicht die vollständige statische Berechnung von Durchlaufträgern aus Holz - von der Eingabe der Geometrie und Lasten über die Schnittgrößenermittlung bis hin zu den Tragfähigkeitsnachweisen.

### Hauptfunktionen:
✅ Mehrfeldträger-Berechnung (inkl. Kragarme)  
✅ EC-konforme Lastkombinationen (GZT/GZG)  
✅ Pattern-Loading für Mehrfeldträger  
✅ Schnittgrößenermittlung (M, Q, w)  
✅ Bauteilnachweise nach EC5  
✅ Graphische Darstellung aller Ergebnisse  
✅ LaTeX-Formelgenerierung für Dokumentation  

---

## 🏗️ Programmarchitektur

Das Programm folgt einer **3-Schicht-Architektur**:

```
┌─────────────────────────────────────────────┐
│         FRONTEND (GUI - Tkinter)            │
│  - Eingabemaske für Geometrie & Lasten      │
│  - Visualisierung der Ergebnisse            │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │   ORCHESTRATOR    │ ← Koordiniert alle Services
         └─────────┬─────────┘
                   │
┌──────────────────▼──────────────────────────┐
│        BACKEND (Berechnungs-Engine)         │
│  - Schnittgrößenberechnung (FEEBB)          │
│  - Lastkombinationen (EC0/EC1)              │
│  - Tragfähigkeitsnachweise (EC5)            │
│  - Materialdatenbank                        │
└─────────────────────────────────────────────┘
```

---

## 📂 Modulübersicht

### **1. HAUPTEINSTIEG**

#### `main_v2.py`
- **Aufgabe**: Programmstart und Haupt-GUI-Initialisierung
- **Funktionen**:
  - Startet die Tkinter-GUI
  - Initialisiert `MainWindow`
  - Lädt Projekt-Explorer und Tab-System
  - Dark/Light Mode Support
- **Workflow**: `main_v2.py` → `MainWindow` → Projekt-Explorer + Tab-System

---

### **2. FRONTEND (GUI-Layer)**

#### **2.1 Hauptfenster & Navigation**

#### `frontend/gui/main_window.py`
- **Aufgabe**: **Zentrale GUI-Koordination und Hauptfenster** ⭐
- **Funktionen**:
  - Menüleiste (Datei, Projekt, Ansicht, Hilfe)
  - Koordiniert Projekt-Explorer und Tab-System
  - Window-Management (Größe, Position, Theme)
  - Verbindet Frontend und Backend-Services
- **Wichtige Klasse**: `MainWindow`
- **Layout**: Splitscreen (Explorer links | Tabs rechts)

#### `frontend/gui/project_explorer.py`
- **Aufgabe**: **Projekt- und Positions-Browser (TreeView)**
- **Funktionen**:
  - Hierarchische Darstellung: Projekt → Positionen
  - Doppelklick zum Öffnen einer Position
  - Kontextmenü (Löschen, Umbenennen)
  - "+ Neue Position" Button
- **Wichtige Klasse**: `ProjectExplorer`
- **Besonderheit**: TreeView-basierte Navigation

#### `frontend/gui/position_tabs.py`
- **Aufgabe**: **Tab-Manager für Positionen (Level 1)**
- **Funktionen**:
  - Verwaltet mehrere geöffnete Positionen als Tabs
  - Jeder Tab = eine Position (z.B. "Deckenträger", "Stütze")
  - Tab-Switching und -Schließen
  - Willkommens-Tab bei Programmstart
- **Wichtige Klasse**: `PositionTabManager`
- **Struktur**: Projekt → **Positionen (Tabs Level 1)** → Module (Tabs Level 2)

#### `frontend/gui/module_tabs.py`
- **Aufgabe**: **Tab-Manager für Module (Level 2)**
- **Funktionen**:
  - Innerhalb einer Position: Tabs für verschiedene Module
  - Module: Durchlaufträger, Brandschutz, Auflager, etc.
  - Lädt und speichert Modul-Daten automatisch
  - Dynamisches Laden über Module-Registry
- **Wichtige Klasse**: `ModuleTabManager`
- **Struktur**: Position → **Module (Tabs Level 2)** → Eingabemaske/Anzeigen

#### `frontend/gui/welcome_dialog.py`
- **Aufgabe**: **Willkommens-Dialog beim Programmstart**
- **Funktionen**:
  - Optionen: Neues Projekt, Projekt öffnen
  - Recent Projects Liste
  - Quickstart-Option
- **Wichtige Klasse**: `WelcomeDialog`
- **Besonderheit**: Modaler Dialog, blockiert Hauptfenster

#### `frontend/gui/eingabemaske_wrapper.py`
- **Aufgabe**: Integration der alten Eingabemaske in das neue Tab-System
- **Funktionen**:
  - `MockRoot`: Simuliert Root-Fenster für Frame-Betrieb
  - Delegiert Window-Methoden (title, attributes, etc.)
  - Ermöglicht Eingabemaske als eingebettetes Widget
- **Wichtige Klasse**: `EingabemaskeWrapper`, `MockRoot`
- **Hinweis**: Bridge zwischen alter und neuer Architektur

---

#### **2.2 Berechnungs-Eingabe**

#### `frontend/gui/eingabemaske.py`
- **Aufgabe**: Eingabeformular für Berechnungen (Legacy-Modul)
- **Funktionen**:
  - Eingabe von Spannweiten, Querschnitt, Material
  - Verwaltung von Lastfällen (G, S, W, etc.)
  - Navigation zu Berechnungs- und Anzeigeseiten
  - Speichern/Laden von Projekten
- **Wichtige Klasse**: `Eingabemaske`
- **Status**: Wird über `EingabemaskeWrapper` in neues System integriert

---

#### **2.3 Ergebnis-Anzeigen**

#### `frontend/display/anzeige_system.py`
- **Aufgabe**: Graphische Darstellung der Systemgeometrie
- **Funktionen**:
  - Visualisierung des Trägersystems
  - Darstellung der Lager (Fest-/Loslager)
  - Anzeige der Lastverteilung
  - Feldnummerierung
- **Wichtige Klasse**: `SystemAnzeiger`

#### `frontend/display/anzeige_feebb.py`
- **Aufgabe**: Darstellung der Schnittgrößenverläufe
- **Funktionen**:
  - Momentenverlauf (GZT)
  - Querkraftverlauf (GZT)
  - Durchbiegung (GZG)
  - **Pattern-Loading-Visualisierung** (farbige Feldhinterlegung)
  - Anzeige der maßgebenden Kombinationen
- **Wichtige Klasse**: `FeebbAnzeiger`
- **Besonderheit**: Zeigt belastete (grün) und unbelastete (rot) Felder

#### `frontend/display/anzeige_lastkombination.py`
- **Aufgabe**: Anzeige der Lastkombinationen
- **Funktionen**:
  - LaTeX-Rendering der Kombinationsformeln
  - Gruppierung nach GZT/GZG
  - Darstellung mit ψ-Faktoren
- **Wichtige Klasse**: `LastkombinationAnzeige`

#### `frontend/display/anzeige_nachweis_ec5.py`
- **Aufgabe**: Darstellung der EC5-Nachweisformeln
- **Funktionen**:
  - Biegenachweis mit LaTeX-Formeln
  - Schubnachweis
  - Durchbiegungsnachweis
  - Rendering der Berechnungsschritte
- **Wichtige Klasse**: `NachweisEC5Anzeige`

#### `frontend/frontend_orchestrator.py`
- **Aufgabe**: Koordination der Frontend-Module
- **Funktionen**:
  - Initialisierung aller Anzeige-Komponenten
  - Event-Handling
  - Kommunikation mit Backend-Orchestrator

---

### **3. BACKEND (Berechnungs-Layer)**

#### **3.1 Orchestration & Services**

#### `backend/api.py`
- **Aufgabe**: REST-ähnliche API für Frontend-Backend-Kommunikation
- **Funktionen**:
  - Endpunkte für Berechnungsanfragen
  - Datenvalidierung
  - Fehlerbehandlung

#### `backend/service/orchestrator_service.py`
- **Aufgabe**: **Zentrale Koordination aller Berechnungen**
- **Funktionen**:
  - Startet FEEBB-Berechnung
  - Initiiert Lastkombinationen
  - Führt EC5-Nachweise durch
  - Koordiniert den Berechnungsablauf
  - **Wichtigste Serviceklasse im Backend**
- **Wichtige Klasse**: `OrchestratorService`

#### `backend/service/calculation_service.py`
- **Aufgabe**: Verwaltung der Berechnungslogik
- **Funktionen**:
  - Aufruf der Berechnungsmodule
  - Fehlerbehandlung bei Berechnungen
  - Logging

#### `backend/service/memory_service.py`
- **Aufgabe**: Verwaltung des Systemzustands (Snapshot-System)
- **Status**: ⚠️ Aktuell nicht aktiv (auskommentiert in orchestrator_service.py)
- **Funktionen**:
  - Speicherung von Eingabedaten
  - Caching von Berechnungsergebnissen
  - Versionierung der Systemzustände
- **Hinweis**: Wird für zukünftige Undo/Redo-Funktion benötigt

#### `backend/service/project_service.py`
- **Aufgabe**: Service-Layer für Projekt-Management (Legacy)
- **Funktionen**:
  - Speichern von Projekten (JSON)
  - Laden von Projekten
  - Projektvalidierung
- **Status**: Wird größtenteils von `backend/project/project_manager.py` ersetzt

#### `backend/service/validation_service.py`
- **Aufgabe**: Eingabevalidierung
- **Funktionen**:
  - Prüfung der Geometrie-Eingaben
  - Lastfall-Validierung
  - Querschnitts-Checks

---

#### **3.2 Berechnungsmodule**

#### `backend/calculations/feebb.py`
- **Aufgabe**: **Kern-Modul für Finite-Element-Berechnung**
- **Funktionen**:
  - Berechnung der Steifigkeitsmatrix
  - Lösung des Gleichungssystems (Durchlaufträger)
  - Ermittlung von Schnittgrößen (M, Q, w)
  - Unterstützung für Mehrfeldträger mit Kragarmen
- **Methode**: Finite-Element-Methode (Euler-Bernoulli-Balken)
- **Wichtigste Funktionen**:
  - `FrameAnalysis2D()`: Hauptberechnungsklasse
  - `analyse()`: Durchführung der statischen Berechnung

#### `backend/calculations/feebb_schnittstelle.py`
- **Aufgabe**: Alte Schnittstelle zu FEEBB (Legacy)
- **Status**: Wird von `feebb_schnittstelle_ec.py` ersetzt
- **Hinweis**: Enthält noch alte Kombinationslogik

#### `backend/calculations/feebb_schnittstelle_ec.py`
- **Aufgabe**: **EC-konforme Schnittstelle zu FEEBB mit Pattern-Loading**
- **Funktionen**:
  - Generierung aller EC-konformen Lastkombinationen
  - **Pattern-Loading**: Feldweise Lastverteilung
  - Belastungsmuster-Generierung (2^n - 1 Muster)
  - Envelope-Bildung über alle Kombinationen
  - Ermittlung der maßgebenden Kombinationen
  - Metadaten für Belastungsmuster
- **Wichtige Klasse**: `FeebbBerechnungEC`
- **Besonderheiten**:
  - Unterscheidung Leit-/Begleitlasten
  - Kragarme werden immer belastet
  - Normale Felder werden nach Muster belastet
  - Separate GZT/GZG-Berechnungen

#### `backend/calculations/lastenkombination.py`
- **Aufgabe**: GZT-Lastkombinationen nach EC0/EC1
- **Funktionen**:
  - Generierung von γ·G + γ·Q-Kombinationen
  - Vollkombinationen mit ψ₀-Faktoren
  - LaTeX-Formelgenerierung
- **Wichtige Klasse**: `Lastenkombination`

#### `backend/calculations/lastkombination_gzg.py`
- **Aufgabe**: GZG-Lastkombinationen nach EC0/EC1
- **Funktionen**:
  - Charakteristische Kombination (G + Q₁ + Σψ₀·Qᵢ)
  - Häufige Kombination (G + ψ₁·Q₁ + Σψ₂·Qᵢ)
  - Quasi-ständige Kombination (G + Σψ₂·Qᵢ)
  - LaTeX-Formelgenerierung
- **Wichtige Klasse**: `LastkombinationGZG`

#### `backend/calculations/nachweis_ec5.py`
- **Aufgabe**: **Bauteilnachweise nach Eurocode 5**
- **Funktionen**:
  - Biegespannungsnachweis (σ_m,d ≤ f_m,d)
  - Schubspannungsnachweis (τ_d ≤ f_v,d)
  - Durchbiegungsnachweis (w ≤ w_zul)
  - Berücksichtigung von k_mod, k_h, k_cr
  - LaTeX-Formelgenerierung für Nachweisdokumentation
- **Wichtige Klasse**: `NachweisEC5`
- **Input**: Schnittgrößen aus FEEBB + Materialkennwerte
- **Output**: Ausnutzungsgrade + LaTeX-Formeln

---

#### **3.3 Projektmanagement**

#### `backend/project/project_manager.py`
- **Aufgabe**: **Zentrale Verwaltung von Projekten und Positionen** ⭐
- **Funktionen**:
  - Projekt erstellen/öffnen/schließen
  - Position erstellen/löschen/umbenennen
  - Dateipersistenz (project.json, Position_*.json)
  - Verwaltung des Projektordners (./Projekte)
  - Aktualisierung der Projekt-Metadaten
- **Wichtige Klasse**: `ProjectManager`
- **Datenstruktur**:
  ```
  Projekte/
  └── MeinProjekt/
      ├── project.json          # Projekt-Metadaten
      ├── Position_1.1.json     # Position 1.1
      └── Position_1.2.json     # Position 1.2
  ```

#### `backend/project/position_model.py`
- **Aufgabe**: **Datenmodell für statische Positionen**
- **Funktionen**:
  - Speichert Metadaten (Nummer, Name, Zeitstempel)
  - Verwaltet Modul-Daten (durchlauftraeger, brandschutz, etc.)
  - Serialisierung (to_dict/from_dict)
  - Generierung von Anzeigenamen und Dateinamen
- **Wichtige Klasse**: `PositionModel` (Dataclass)
- **Struktur**:
  ```python
  PositionModel:
    - position_nummer: "1.1"
    - position_name: "Deckenträger"
    - active_module: "durchlauftraeger"
    - modules: {
        "durchlauftraeger": {...},
        "brandschutz": {...}
      }
  ```

#### `backend/project/settings_manager.py`
- **Aufgabe**: Verwaltung von Anwendungseinstellungen
- **Funktionen**:
  - Recent Projects Liste
  - Fenstergeometrie speichern/laden
  - UI-Präferenzen (Theme, Explorer-Breite)
  - Auto-Save Einstellungen
  - Persistierung in config/settings.json
- **Wichtige Klasse**: `SettingsManager`
- **Daten**: Recent Projects, Last Opened Project/Position, Window Geometry

---

#### **3.4 Datenbankmodul**

#### `backend/database/datenbank_holz.py`
- **Aufgabe**: **Materialdatenbank für Holz**
- **Funktionen**:
  - Festigkeitskennwerte (f_m,k, f_v,k, f_c,0,k, etc.)
  - E-Modul, G-Modul
  - Dichte
  - ψ-Faktoren für Einwirkungskombinationen
  - Nutzungsklassen (NK1, NK2, NK3)
  - Lasteinwirkungsdauern (ständig, lang, mittel, kurz, sehr kurz)
- **Materialien**:
  - Vollholz (C14-C50)
  - Brettschichtholz (GL24h-GL32h)
  - Kreuzlagenholz (CLT)
- **Wichtige Funktionen**:
  - `get_holz_eigenschaften()`: Materialdaten abrufen
  - `get_kmod()`: k_mod-Wert nach NK und Lastdauer
  - `get_si_beiwerte()`: ψ₀, ψ₁, ψ₂ nach NA-DE

---

## 🔄 Berechnungsablauf (Workflow)

### **Phase 0: Projekt-Setup** (Neu!)
```
Programmstart → Welcome-Dialog
├─ Option wählen: Neues Projekt / Öffnen / Recent
└─ MainWindow öffnet sich

Hauptfenster:
├─ Links: Project Explorer (TreeView)
│   └─ Projekt → Positionen
└─ Rechts: Tab-System (2 Ebenen)
    ├─ Level 1: Position-Tabs (z.B. "Pos 1.1 Deckenträger")
    └─ Level 2: Modul-Tabs (Durchlaufträger, Brandschutz, etc.)
```

### **Phase 1: Eingabe** (Frontend)
```
Benutzer → Position-Tab → Modul-Tab → Eingabemaske
├─ Geometrie (Spannweiten, Kragarme)
├─ Querschnitt (b, h)
├─ Material (z.B. GL24h)
├─ Lastfälle (G, S, W, etc.)
└─ Auto-Save in Position_*.json
```

### **Phase 2: Orchestrierung** (Backend)
```
Button "Berechnen" → OrchestratorService
├─ Validierung der Eingaben
├─ Generierung der Lastkombinationen (EC0/EC1)
├─ Erstellung der Belastungsmuster
└─ Start der FEEBB-Berechnungen
```

### **Phase 3: Strukturberechnung** (Backend)
```
FeebbBerechnungEC → FEEBB
├─ Für jede Kombination × Belastungsmuster:
│   ├─ Systemmatrix aufstellen
│   ├─ Gleichungssystem lösen
│   ├─ Schnittgrößen ermitteln (M, Q, w)
│   └─ Ergebnisse speichern
├─ Envelope-Bildung (Max/Min-Werte)
└─ Maßgebende Kombinationen ermitteln
```

### **Phase 4: Nachweisführung** (Backend)
```
NachweisEC5
├─ Materialkennwerte aus Datenbank holen
├─ k_mod, γ_M, k_h ermitteln
├─ Biegenachweis: σ_m,d / f_m,d
├─ Schubnachweis: τ_d / f_v,d
├─ Durchbiegungsnachweis: w / w_zul
└─ LaTeX-Formeln generieren
```

### **Phase 5: Visualisierung** (Frontend)
```
Anzeige-Module
├─ Systemdarstellung
├─ Schnittgrößenverläufe
│   ├─ Moment (GZT)
│   ├─ Querkraft (GZT)
│   └─ Durchbiegung (GZG) ← mit Pattern-Loading-Overlay
├─ Lastkombinationen (LaTeX)
└─ EC5-Nachweise (LaTeX)
```

---

## 🆕 Besondere Features

### **1. Pattern-Loading für Mehrfeldträger**
- **Problem**: Bei Mehrfeldträgern müssen veränderliche Lasten feldweise angeordnet werden
- **Lösung**: Automatische Generierung aller relevanten Belastungsmuster
- **Beispiel** (3 Felder): 7 Muster werden berechnet
  - `[True, False, False]` → nur Feld 1 belastet
  - `[True, True, False]` → Feld 1+2 belastet
  - `[True, True, True]` → alle Felder belastet
  - etc.
- **Visualisierung**: Grüne/rote Hinterlegung in Schnittgrößendiagrammen

### **2. EC-konforme Lastkombinationen**
- **GZT** (Grenzzustand der Tragfähigkeit):
  - γ_G · G
  - γ_G · G + γ_Q · Q_i
  - γ_G · G + γ_Q · Q_Leit + Σψ₀ · γ_Q · Q_Begleit
- **GZG** (Grenzzustand der Gebrauchstauglichkeit):
  - Charakteristisch: G + Q₁ + Σψ₀ · Q_i
  - Häufig: G + ψ₁ · Q₁ + Σψ₂ · Q_i
  - Quasi-ständig: G + Σψ₂ · Q_i

### **3. Automatische Envelope-Bildung**
- Über alle Kombinationen werden Min/Max-Hüllkurven gebildet
- Maßgebende Kombination wird für jeden Punkt gespeichert
- Terminal-Ausgabe zeigt die ungünstigsten Lastfälle an

### **4. LaTeX-Dokumentation**
- Alle Formeln werden als LaTeX generiert
- Rendering direkt in der GUI
- Export-fähig für Berichte

### **5. Snapshot-System**
- Alle Eingaben und Ergebnisse werden im Snapshot gespeichert
- Ermöglicht Undo/Redo (zukünftig)
- Hot-Reload der Berechnungen

---

## 📊 Berechnungsumfang (Beispiel)

**System**: 3-Feld-Träger mit 2 veränderlichen Lasten (S, W)

**Anzahl FEEBB-Berechnungen**:
- GZT: ~29 Berechnungen
  - 1× nur G (alle Felder)
  - 7× G+S (7 Muster)
  - 7× G+W (7 Muster)
  - 7× G+S(Leit)+ψ₀·W(Begleit) (7 Muster)
  - 7× G+W(Leit)+ψ₀·S(Begleit) (7 Muster)
- GZG: ~29 Berechnungen (analog)
- **Gesamt: ~58 strukturmechanische Berechnungen**

**Ausgaben**:
- 6 Envelope-Kurven (Moment max/min, Querkraft max/min, Durchbiegung max/min)
- Maßgebende Kombinationen für jeden Punkt
- LaTeX-Formeln für alle Kombinationstypen
- EC5-Nachweise mit allen Zwischenschritten

---

## 🔧 Technologie-Stack

- **Sprache**: Python 3.x
- **GUI**: Tkinter (Standard-GUI-Bibliothek)
- **Numerik**: NumPy (Matrix-Operationen)
- **Visualisierung**: Matplotlib (Diagramme)
- **LaTeX-Rendering**: Matplotlib LaTeX-Engine
- **Datenspeicherung**: JSON (Projekt-Files)
- **Finite Elemente**: Eigene Implementierung (FEEBB)

---

## 📁 Projektstruktur

```
Statikprogramm/
├── main_v2.py                       # Programmeinstieg ⭐
├── frontend/
│   ├── gui/                         # GUI-Komponenten (Neu!)
│   │   ├── main_window.py          # Hauptfenster & Koordination ⭐
│   │   ├── project_explorer.py     # Projekt-Browser (TreeView) ⭐
│   │   ├── position_tabs.py        # Position-Tab-Manager (Level 1) ⭐
│   │   ├── module_tabs.py          # Modul-Tab-Manager (Level 2) ⭐
│   │   ├── welcome_dialog.py       # Willkommens-Dialog
│   │   ├── eingabemaske_wrapper.py # Wrapper für alte Eingabemaske
│   │   ├── eingabemaske.py         # Eingabeformular (Legacy)
│   │   ├── theme_config.py         # Dark/Light Mode
│   │   └── latex_renderer.py       # LaTeX-Rendering
│   ├── display/                     # Ergebnis-Anzeigen
│   │   ├── anzeige_system.py       # Systemdarstellung
│   │   ├── anzeige_feebb.py        # Schnittgrößen
│   │   ├── anzeige_lastkombination.py  # Kombinationen
│   │   └── anzeige_nachweis_ec5.py # EC5-Nachweise
│   └── frontend_orchestrator.py    # Frontend-Koordination (Legacy)
├── backend/
│   ├── api.py                       # API-Endpunkte
│   ├── service/
│   │   ├── orchestrator_service.py # Haupt-Orchestrator ⭐
│   │   ├── calculation_service.py  # Berechnungs-Service
│   │   ├── memory_service.py       # Snapshot-Verwaltung (inaktiv)
│   │   ├── project_service.py      # Projekt-Management (Legacy)
│   │   └── validation_service.py   # Validierung
│   ├── calculations/
│   │   ├── feebb.py                # Finite-Elemente-Kern ⭐
│   │   ├── feebb_schnittstelle_ec.py  # EC-Schnittstelle ⭐
│   │   ├── lastenkombination.py    # GZT-Kombinationen
│   │   ├── lastkombination_gzg.py  # GZG-Kombinationen
│   │   └── nachweis_ec5.py         # EC5-Nachweise ⭐
│   ├── database/
│   │   └── datenbank_holz.py       # Materialdatenbank ⭐
│   └── project/                     # Projektmanagement (Neu!)
│       ├── project_manager.py      # Projekt-Verwaltung ⭐
│       ├── position_model.py       # Position-Datenmodell ⭐
│       └── settings_manager.py     # App-Einstellungen ⭐
├── config/                          # Anwendungseinstellungen (Neu!)
│   └── settings.json               # Recent Projects, Window Geometry
└── Projekte/                        # Benutzer-Projekte (außerhalb Git)
    └── MeinProjekt/                # Beispiel-Projekt
        ├── project.json            # Projekt-Metadaten
        ├── Position_1.1.json       # Position 1.1 Daten
        └── Position_1.2.json       # Position 1.2 Daten

⭐ = Kern-Module
```

---

## 🎓 Normative Grundlagen

Das Programm basiert auf folgenden Normen:

- **EN 1990** (Eurocode 0): Grundlagen der Tragwerksplanung
  - Lastkombinationen
  - Teilsicherheitsbeiwerte
  - ψ-Faktoren

- **EN 1991** (Eurocode 1): Einwirkungen auf Tragwerke
  - Schneelasten
  - Windlasten
  - Nutzlasten

- **EN 1995-1-1** (Eurocode 5): Holzbau
  - Biegetragfähigkeit
  - Schubtragfähigkeit
  - Durchbiegungsgrenzen
  - Modifikationsfaktoren (k_mod, k_h, k_cr)

- **Nationaler Anhang Deutschland** (NA-DE)
  - γ-Werte: γ_G = 1.35, γ_Q = 1.50, γ_M = 1.30
  - ψ-Faktoren für Deutschland

---

## 🚀 Zukünftige Erweiterungen (geplant)

- [ ] PDF-Export der Berechnungen
- [ ] Mehrere Querschnittsformen (Rechteck, I-Profil, etc.)
- [ ] Fachwerke
- [ ] Verbindungsmittel-Nachweise
- [ ] Brandschutz-Nachweise
- [ ] Schwingungsnachweis
- [ ] Bauteiloptimierung

---

## 📝 Hinweise für Entwickler

### Wichtige Einstiegspunkte:
1. **`main_v2.py`**: Programmstart
2. **`main_window.py`**: GUI-Hauptfenster und Navigation
3. **`project_manager.py`**: Projekt- und Positionsverwaltung
4. **`project_explorer.py`**: Projekt-Browser (TreeView)
5. **`position_tabs.py` / `module_tabs.py`**: 2-Ebenen-Tab-System
6. **`orchestrator_service.py`**: Berechnungsablauf verstehen
7. **`feebb_schnittstelle_ec.py`**: Pattern-Loading-Logik
8. **`nachweis_ec5.py`**: Nachweisführung
9. **`datenbank_holz.py`**: Materialdaten
10. **`theme_config.py`**: Dark/Light Mode
11. **`latex_renderer.py`**: LaTeX-Rendering

### Code-Konventionen:
- Docstrings für alle Funktionen/Klassen
- Type-Hints wo möglich
- Logging für Debug-Zwecke
- Kommentare bei komplexer Logik
- Threading für GUI-responsiveness

### Testing:
- Manuelle Tests über GUI
- Vergleich mit Handrechnungen
- Visual Testing (LaTeX-Rendering)

---

**Erstellt**: 2025-01-22  
**Letztes Update**: 2025-10-24  
**Version**: 2.0.0 (Production Ready)  
**Autor**: Maximilian Stark  
**Neue Features (v2.0)**:  
✅ Multi-Projekt-System mit Projekt-Explorer  
✅ 2-Ebenen-Tab-System (Positionen → Module)  
✅ Willkommens-Dialog mit Recent Projects  
✅ Auto-Save und Einstellungsverwaltung  
✅ Dark/Light Mode  
✅ LaTeX-Rendering & EC5-Nachweise  
✅ Pattern-Loading für Mehrfeldträger  
