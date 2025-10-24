# Roadmap: Statikprogramm v2.0+

## Status: Tab-System implementiert ✅

Dieses Dokument definiert die nächsten Entwicklungsschritte nach erfolgreicher Tab-System-Integration.

---

## Phase 1: Stabilisierung & Testing (Woche 1) 🔬

**Ziel:** Sicherstellen, dass das Kern-System fehlerfrei funktioniert

### 1.1 Funktionale Tests
- [ ] **End-to-End Workflow testen:**
  - Projekt erstellen → Position hinzufügen → Berechnung → Speichern → Schließen → Öffnen
  - Mehrere Positionen parallel in Tabs
  - Tab-Wechsel zwischen Modulen
  - Auto-Save-Funktionalität
  
- [ ] **Edge Cases abdecken:**
  - Leere Projekte
  - Sehr große Projekte (100+ Positionen)
  - Positions-Umbenennung
  - Projekt-Pfad mit Sonderzeichen
  - Fehlerhafte JSON-Dateien wiederherstellen

### 1.2 Performance-Optimierung
- [ ] Ladezeiten messen (Position sollte < 500ms laden)
- [ ] Speicher-Leaks prüfen (bei vielen Tab-Wechseln)
- [ ] Lazy Loading für große Projekte implementieren

### 1.3 Bugfixes & Stabilität
- [ ] Exception Handling verbessern (keine Crashes!)
- [ ] Logging-Levels optimieren (weniger DEBUG in Produktion)
- [ ] User-Feedback bei Fehlern (MessageBoxen mit klaren Meldungen)

**Deliverable:** Stabiles, testbares Kern-System

---

## Phase 2: Code-Refactoring & Architektur (Woche 2-3) 🏗️

**Ziel:** Wartbare, skalierbare Codebasis

### 2.1 Eingabemaske modularisieren

**Aktuell:** 1264 Zeilen monolithischer Code  
**Ziel:** Komponenten-basierte Architektur

```python
frontend/gui/eingabemaske/
├── __init__.py
├── base_eingabe.py           # Basis-Klasse für alle Eingabe-Komponenten
├── system_eingabe.py         # Sprungmaß, Felder, Kragarme (200 Zeilen)
├── lasten_eingabe.py         # Lastfälle, NKL, Kombinationen (300 Zeilen)
├── querschnitt_eingabe.py    # Materialien, Festigkeitsklassen (400 Zeilen)
├── gebrauchstauglichkeit.py  # Durchbiegungsnachweise (200 Zeilen)
└── schnittgroessen.py        # Bemessungsschnittgrößen (150 Zeilen)
```

**Vorteile:**
- Einzelne Komponenten testbar
- Parallele Entwicklung möglich
- Einfachere Fehlersuche
- Wiederverwendbare Komponenten

**Schritte:**
1. [ ] BaseEingabe-Komponente definieren
2. [ ] SystemEingabe extrahieren (als Proof-of-Concept)
3. [ ] Tests für SystemEingabe schreiben
4. [ ] Weitere Komponenten migrieren (eine nach der anderen)
5. [ ] Integration testen

### 2.2 Datenmodell erweitern

Aktuell: Daten als lose Dictionaries  
Ziel: Typsichere Datenklassen

```python
# Neu: backend/models/
├── system_model.py           # Sprungmaß, Felder, Auflager
├── last_model.py             # Lastfälle mit Validierung
├── querschnitt_model.py      # Querschnittsdaten
└── ergebnis_model.py         # Berechnungsergebnisse
```

**Vorteile:**
- Type Hints für bessere IDE-Unterstützung
- Automatische Validierung
- Versionierung von Datenformaten
- Einfachere Serialisierung

### 2.3 Service Layer verbessern

```python
backend/services/
├── calculation_service.py    # Berechnungslogik
├── validation_service.py     # Eingabe-Validierung
├── export_service.py         # PDF/Excel Export
└── import_service.py         # Legacy-Daten Import
```

**Deliverable:** Saubere, modulare Architektur

---

## Phase 3: UI/UX Verbesserungen (Woche 4) 🎨

**Ziel:** Professionelles Erscheinungsbild

### 3.1 CustomTkinter Migration

```bash
# Automatisierte Migration:
1. Search & Replace: ttk.Button → ctk.CTkButton
2. Search & Replace: ttk.Entry → ctk.CTkEntry
3. Search & Replace: ttk.Label → ctk.CTkLabel
# ... etc.
```

**Features:**
- [ ] Dark Mode Support
- [ ] Moderne, abgerundete Widgets
- [ ] Bessere Farbpalette (Theme)
- [ ] Animationen (Tab-Wechsel, etc.)

### 3.2 Benutzbarkeit

- [ ] **Keyboard Shortcuts:**
  - `Cmd+T` = Neue Position
  - `Cmd+W` = Tab schließen
  - `Tab/Shift+Tab` = Navigation zwischen Feldern
  - `Cmd+Enter` = Berechnung starten

- [ ] **Kontextmenüs (Rechtsklick):**
  - Explorer: Position umbenennen, löschen, duplizieren
  - Tabs: Tab schließen, alle anderen schließen
  
- [ ] **Drag & Drop:**
  - Positionen im Explorer verschieben
  - Ordner-Strukturierung

- [ ] **Tooltips:**
  - Eingabefelder mit Erklärungen
  - Buttons mit Funktionsbeschreibung

### 3.3 Visualisierungen

- [ ] Interaktive System-Grafik (anklickbar)
- [ ] 3D-Darstellung des Trägers (optional, mit matplotlib 3D)
- [ ] Animierte Lastverläufe
- [ ] Export als SVG/PNG

**Deliverable:** Moderne, benutzerfreundliche Oberfläche

---

## Phase 4: Neue Module (Woche 5-8) ⚡

**Ziel:** Funktionsumfang erweitern

### 4.1 Modul: Brandschutz (Woche 5)

```python
frontend/modules/brandschutz/
├── modul_brandschutz.py
├── brandschutz_eingabe.py
└── brandschutz_berechnung.py
```

**Features:**
- Feuerwiderstandsklassen (F30, F60, F90, etc.)
- Abbrandrate nach DIN EN 1995-1-2
- Restquerschnitt-Berechnung
- Nachweis der Tragfähigkeit im Brandfall

### 4.2 Modul: Auflagernachweis (Woche 6)

```python
frontend/modules/auflager/
├── modul_auflager.py
├── auflager_eingabe.py
└── auflager_berechnung.py
```

**Features:**
- Drucknachweis senkrecht zur Faser
- Auflagerverbreiterungen
- Lochleibung bei Stahlplatte
- Kombinierte Beanspruchung

### 4.3 Modul: Querzug/Ausklinkung (Woche 7)

```python
frontend/modules/querzug/
├── modul_querzug.py
├── querzug_eingabe.py
└── querzug_berechnung.py
```

**Features:**
- Ausklinkungen am Auflager
- Querzugnachweis nach EC5
- Bewehrungsnachweis
- Optimierung der Ausklinkungsgeometrie

### 4.4 Modul: Knotenpunkte (Woche 8)

**Features:**
- Zapfen-Verbindungen
- Schwalbenschwanz
- Stabdübel
- Nagelverbindungen

**Deliverable:** Vollständiges Statik-Tool für Holzbau

---

## Phase 5: Export & Dokumentation (Woche 9-10) 📄

**Ziel:** Professionelle Ausgaben

### 5.1 PDF-Export

```python
backend/export/
├── pdf_generator.py          # ReportLab oder FPDF
├── templates/
│   ├── statik_bericht.html   # HTML-Template
│   └── styles.css
└── assets/
    ├── logo.png
    └── header.png
```

**Features:**
- [ ] Vollständiger Statik-Bericht
- [ ] Grafiken einbetten (System, Schnittgrößen)
- [ ] Übersichtliche Tabellen
- [ ] Firmen-Logo/Header
- [ ] Inhaltsverzeichnis

### 5.2 Excel-Export

- [ ] Eingabedaten
- [ ] Ergebnisse
- [ ] Vergleichstabellen (mehrere Varianten)

### 5.3 Vorlagen-System

```python
Projekte/_Vorlagen/
├── Einfeldträger.json
├── Zweifeldträger.json
├── Durchlaufträger_3_Felder.json
└── Mit_Kragarm.json
```

**Features:**
- [ ] Position aus Vorlage erstellen
- [ ] Eigene Vorlagen speichern
- [ ] Vorlagen-Bibliothek

**Deliverable:** Professionelle Dokumentation

---

## Phase 6: Testing & Quality Assurance (Woche 11) ✅

**Ziel:** Produktionsreife Software

### 6.1 Automatisierte Tests

```python
tests/
├── unit/
│   ├── test_lastenkombination.py
│   ├── test_feebb.py
│   └── test_nachweis_ec5.py
├── integration/
│   ├── test_workflow.py
│   └── test_data_persistence.py
└── e2e/
    └── test_complete_calculation.py
```

**Tools:**
- `pytest` = Test-Framework
- `pytest-cov` = Code Coverage
- `pytest-qt` = GUI Testing

**Ziel: 80% Code Coverage**

### 6.2 Code Quality

```python
# CI/CD Pipeline (.github/workflows/ci.yml)
name: Quality Checks
on: [push, pull_request]
jobs:
  test:
    - pytest
    - mypy (Type Checking)
    - ruff (Linting)
    - black (Code Formatting)
```

### 6.3 Benutzer-Tests

- [ ] Beta-Tester finden (3-5 Ingenieure)
- [ ] Feedback sammeln
- [ ] Bugs fixen
- [ ] Usability verbessern

**Deliverable:** Stabile v2.0 Release

---

## Phase 7: Deployment & Verteilung (Woche 12) 🚀

**Ziel:** Programm auslieferbar machen

### 7.1 Executable erstellen

```bash
# PyInstaller:
pyinstaller --windowed --onefile \
  --name "Statikprogramm" \
  --icon "assets/icon.icns" \
  main_v2.py
```

**Plattformen:**
- macOS (`.app` Bundle)
- Windows (`.exe`)
- Linux (AppImage)

### 7.2 Installer

- macOS: `.dmg` mit Drag&Drop Installation
- Windows: `.msi` Installer (Inno Setup)
- Update-Mechanismus (Auto-Update)

### 7.3 Dokumentation

```
docs/
├── Benutzerhandbuch.pdf
├── Installation.md
├── FAQ.md
└── API_Documentation/
```

**Deliverable:** Installierbare Anwendung

---

## Optionale Features (Backlog) 💡

### Cloud-Integration
- [ ] Online-Backup von Projekten
- [ ] Team-Kollaboration (mehrere Nutzer)
- [ ] Cloud-Berechnungen (für große Projekte)

### Erweiterte Analysen
- [ ] Optimierung (z.B. minimaler Querschnitt)
- [ ] Parameterstudien
- [ ] Stochastische Analysen

### Schnittstellen
- [ ] Import aus CAD (DXF)
- [ ] Export nach FEM-Software
- [ ] API für externe Tools

### Mobile App
- [ ] iOS/Android App (React Native?)
- [ ] Nur Ansicht, keine Berechnung
- [ ] Projekt-Synchronisierung

---

## Zeitplan Übersicht

```
┌───────────┬──────────────────────────────────────┬────────────┐
│  Woche    │  Phase                               │  Status    │
├───────────┼──────────────────────────────────────┼────────────┤
│  1        │  Stabilisierung & Testing            │  Pending   │
│  2-3      │  Code-Refactoring                    │  Pending   │
│  4        │  UI/UX (CustomTkinter)               │  Pending   │
│  5-8      │  Neue Module                         │  Pending   │
│  9-10     │  Export & Dokumentation              │  Pending   │
│  11       │  Quality Assurance                   │  Pending   │
│  12       │  Deployment                          │  Pending   │
└───────────┴──────────────────────────────────────┴────────────┘
```

**Geschätzte Gesamtdauer:** ~3 Monate (bei 10-15h/Woche)

---

## Prioritäten

**MUSS (für v2.0 Release):**
- ✅ Tab-System
- ⏳ Stabilisierung & Bugfixes
- ⏳ Vollständige Eingabemaske-Integration
- ⏳ Speichern/Laden funktioniert fehlerfrei
- ⏳ PDF-Export (Basis)

**SOLL (für v2.1):**
- Eingabemaske modularisiert
- CustomTkinter
- 1-2 neue Module (Brandschutz, Auflager)

**KANN (für v3.0):**
- Erweiterte Module
- Cloud-Features
- Mobile App

---

## Nächste Schritte (diese Woche)

1. ✅ Tab-System testen
2. ⏳ End-to-End Workflow validieren
3. ⏳ Kritische Bugs fixen
4. ⏳ Erste Refactoring-Schritte planen

**Ziel:** Funktionsfähige v2.0-alpha bis Ende der Woche

---

Erstellt: 2025-10-23  
Letzte Aktualisierung: 2025-10-23  
Version: 1.0
