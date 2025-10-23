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

#### `main.py`
- **Aufgabe**: Programmstart und Initialisierung
- **Funktionen**:
  - Startet die Tkinter-GUI
  - Initialisiert den Backend-Orchestrator
  - Verbindet Frontend und Backend

---

### **2. FRONTEND (GUI-Layer)**

#### `frontend/gui/eingabemaske.py`
- **Aufgabe**: Hauptfenster für Benutzereingaben
- **Funktionen**:
  - Eingabe von Spannweiten, Querschnitt, Material
  - Verwaltung von Lastfällen (G, S, W, etc.)
  - Navigation zu Berechnungs- und Anzeigeseiten
  - Speichern/Laden von Projekten
- **Wichtige Klasse**: `Eingabemaske`

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
- **Funktionen**:
  - Speicherung von Eingabedaten
  - Caching von Berechnungsergebnissen
  - Versionierung der Systemzustände
- **Wichtig für**: Hot-Reload und Undo-Funktionalität

#### `backend/service/project_service.py`
- **Aufgabe**: Projekt-Management
- **Funktionen**:
  - Speichern von Projekten (JSON)
  - Laden von Projekten
  - Projektvalidierung

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

#### **3.3 Datenbankmodul**

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

### **Phase 1: Eingabe** (Frontend)
```
Benutzer → Eingabemaske
├─ Geometrie (Spannweiten, Kragarme)
├─ Querschnitt (b, h)
├─ Material (z.B. GL24h)
├─ Lastfälle (G, S, W, etc.)
└─ Speichern im Snapshot
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
├── main.py                          # Programmeinstieg
├── frontend/
│   ├── gui/
│   │   └── eingabemaske.py         # Hauptfenster
│   ├── display/
│   │   ├── anzeige_system.py       # Systemdarstellung
│   │   ├── anzeige_feebb.py        # Schnittgrößen
│   │   ├── anzeige_lastkombination.py  # Kombinationen
│   │   └── anzeige_nachweis_ec5.py # EC5-Nachweise
│   └── frontend_orchestrator.py    # Frontend-Koordination
├── backend/
│   ├── api.py                       # API-Endpunkte
│   ├── service/
│   │   ├── orchestrator_service.py # Haupt-Orchestrator ⭐
│   │   ├── calculation_service.py  # Berechnungs-Service
│   │   ├── memory_service.py       # Snapshot-Verwaltung
│   │   ├── project_service.py      # Projekt-Management
│   │   └── validation_service.py   # Validierung
│   ├── calculations/
│   │   ├── feebb.py                # Finite-Elemente-Kern ⭐
│   │   ├── feebb_schnittstelle_ec.py  # EC-Schnittstelle ⭐
│   │   ├── lastenkombination.py    # GZT-Kombinationen
│   │   ├── lastkombination_gzg.py  # GZG-Kombinationen
│   │   └── nachweis_ec5.py         # EC5-Nachweise ⭐
│   └── database/
│       └── datenbank_holz.py       # Materialdatenbank ⭐
├── project_memory/                  # Gespeicherte Projekte
└── tests/                           # Unit-Tests

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
1. **`main.py`**: Programmstart
2. **`orchestrator_service.py`**: Berechnungsablauf verstehen
3. **`feebb_schnittstelle_ec.py`**: Pattern-Loading-Logik
4. **`nachweis_ec5.py`**: Nachweisführung
5. **`datenbank_holz.py`**: Materialdaten

### Code-Konventionen:
- Docstrings für alle Funktionen/Klassen
- Type-Hints wo möglich
- Logging für Debug-Zwecke
- Kommentare bei komplexer Logik

### Testing:
- Unit-Tests im `tests/`-Verzeichnis
- Manuelle Tests über GUI
- Vergleich mit Handrechnungen

---

**Erstellt**: 2025-01-22  
**Version**: 1.0  
**Autor**: Maximilian Stark  
**Betreuer**: -  
**Hochschule**: -  
