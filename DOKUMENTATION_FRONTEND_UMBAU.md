# Dokumentation: Frontend-Umbau zum Projektsystem

## 🎯 Überblick

Das Frontend wurde von einer einzelnen Eingabemaske zu einem vollständigen **Projekt-Management-System** mit Tab-basierter Navigation umgebaut.

---

## 📁 Neue Architektur - Hauptkomponenten

### 1. **MainWindow** (`main_window.py`)
Das Hauptfenster - der "Container" für alles.

**Aufgaben:**
- Erstellt Menüleiste (Datei, Bearbeiten, Ansicht, Hilfe)
- Verwaltet Projekt-Zustand (welches Projekt ist offen?)
- Koordiniert Explorer und Tab-System
- Zeigt Welcome-Dialog beim Start

**Wichtige Methoden:**
```python
def _new_project():      # Neues Projekt erstellen
def _open_project():     # Projekt öffnen
def _load_project():     # Projekt laden (intern)
def _close_project():    # Projekt schließen
def _new_position():     # Neue Position erstellen
```

**Aufbau:**
```
┌─────────────────────────────────────┐
│  Menüleiste (Datei, Bearbeiten...) │
├──────────┬──────────────────────────┤
│ Explorer │  Tab-System              │
│          │  ┌───────────────────┐   │
│ Projekt  │  │ Position 1.01     │   │
│ └─ Pos.1 │  │ (Eingabemaske)    │   │
│ └─ Pos.2 │  └───────────────────┘   │
└──────────┴──────────────────────────┘
```

---

### 2. **ProjectExplorer** (`project_explorer.py`)
Der Projekt-Explorer links - zeigt die Projektstruktur.

**Funktionen:**
- TreeView-basierte Darstellung
- Ordner und Positionen anzeigen
- Doppelklick → Position öffnen
- Rechtsklick → Kontextmenü

**Kontextmenü:**
- Öffnen
- Neuer Ordner...
- Umbenennen
- Duplizieren
- Löschen

**Wie es funktioniert:**
```python
# Projekt laden
def load_project(project_path, project_manager):
    # TreeView leeren
    # Projekt-Root erstellen
    # Positionen rekursiv laden
    # + Button aktivieren

# Position öffnen (Doppelklick)
def _on_double_click(event):
    # Position-Pfad aus TreeView-Tags holen
    # Callback aufrufen: on_position_open(position_path)
```

**Wichtig:** Der Explorer ist nur die **Anzeige**. Er speichert nichts selbst, sondern ruft Callbacks auf:
```python
self.on_position_open(position_path)    # → MainWindow öffnet Position
self.on_new_position()                  # → MainWindow erstellt Position
self.on_position_deleted(path)          # → MainWindow schließt Tab
```

---

### 3. **PositionTabManager** (`position_tabs.py`)
Verwaltet die Positions-Tabs (1. Level).

**Aufgaben:**
- Tab pro Position erstellen
- Tab-Titel mit Position-Name
- Positions-Daten verwalten
- Speichern/Laden koordinieren

**Struktur:**
```
PositionTabManager (ttk.Notebook)
├─ Tab "1.01 - Decke"
│  └─ ModuleTabManager (Eingabemaske, System, Nachweise...)
├─ Tab "1.02 - Unterzug"  
│  └─ ModuleTabManager
└─ Tab "2.01 - Sparren"
   └─ ModuleTabManager
```

**Wichtige Methoden:**
```python
def open_position(position_model, position_file):
    # Tab erstellen
    # ModuleTabManager erstellen (→ Eingabemaske etc.)
    # In Dictionary speichern: self.open_positions[path] = (tab_id, position_data)

def close_position(position_file):
    # Tab schließen
    # Cleanup aufrufen
    # Aus Dictionary entfernen

def save_current_position(project_manager):
    # Aktuellen Tab holen
    # Position-Daten holen
    # ProjectManager.save_position() aufrufen
```

---

### 4. **ModuleTabManager** (`module_tabs.py`)
Verwaltet die Modul-Tabs innerhalb einer Position (2. Level).

**Modul-Tabs:**
- **Durchlaufträger** → Eingabemaske + Berechnungen
- **Statisches System** → Systemskizze
- **EC-Kombinatorik** → Lastkombinationen (genau)
- **Nachweise** → EC5-Nachweise

**Struktur:**
```
ModuleTabManager (ttk.Notebook)
├─ Tab "Durchlaufträger"
│  └─ EingabemaskeWrapper (die eigentliche Eingabemaske!)
├─ Tab "Statisches System"
│  └─ SystemAnzeige
├─ Tab "EC-Kombinatorik"
│  └─ LastkombiAnzeige
└─ Tab "Nachweise"
   └─ NachweisEC5Anzeige
```

**Wichtig:** Hier wird die Eingabemaske eingebunden!
```python
def _create_durchlauftraeger_tab():
    # Frame für Tab erstellen
    frame = ttk.Frame(self.notebook)
    
    # EingabemaskeWrapper erstellen (kapselt alte Eingabemaske)
    self.eingabemaske_wrapper = EingabemaskeWrapper(
        frame, 
        self.position_model,
        self.position_file
    )
    
    # Tab hinzufügen
    self.notebook.add(frame, text="Durchlaufträger")
```

---

### 5. **EingabemaskeWrapper** (`eingabemaske_wrapper.py`)
Wrapper für die alte Eingabemaske - macht sie "Tab-fähig".

**Problem:** Die alte `Eingabemaske` braucht ein eigenes `tk.Tk()` Root-Fenster.

**Lösung:** Wrapper erstellt ein **eingebettetes Fenster**:
```python
class EingabemaskeWrapper:
    def __init__(self, parent_frame, position_model, position_file):
        # Toplevel-Fenster INNERHALB des Frames
        self.window = tk.Toplevel(parent_frame)
        self.window.title("Durchlaufträger")
        
        # Alte Eingabemaske darin erstellen
        self.eingabemaske = Eingabemaske(self.window)
        
        # Position-Daten laden
        self.load_position_data(position_model)
```

**Warum Toplevel?** Die alte Eingabemaske erwartet ein Root-Fenster mit `.mainloop()`. Ein Toplevel ist ein eigenständiges Fenster, funktioniert aber im Tab.

**Wichtig:** Das Toplevel wird in den Frame "eingebettet" durch das parent-Child-Verhältnis.

---

## 🔄 Datenfluss: Position öffnen

So läuft es ab, wenn du eine Position doppelklickst:

```
1. ProjectExplorer (Doppelklick)
   └─→ _on_double_click()
       └─→ self.on_position_open(position_path)  [Callback]

2. MainWindow (Callback-Empfänger)
   └─→ _on_explorer_position_open(position_path)
       └─→ position_model = project_manager.load_position(path)
       └─→ position_tabs.open_position(position_model, path)

3. PositionTabManager
   └─→ open_position(position_model, position_file)
       └─→ Tab erstellen
       └─→ module_tabs = ModuleTabManager(tab, position_model, position_file)

4. ModuleTabManager
   └─→ _create_durchlauftraeger_tab()
       └─→ eingabemaske_wrapper = EingabemaskeWrapper(frame, position_model, position_file)

5. EingabemaskeWrapper
   └─→ window = tk.Toplevel(frame)
   └─→ eingabemaske = Eingabemaske(window)
   └─→ load_position_data(position_model)  # Daten in GUI laden
```

---

## 💾 Datenfluss: Position speichern

```
1. User drückt Cmd+S oder Menü "Speichern"
   └─→ MainWindow._save_current()

2. MainWindow
   └─→ position_tabs.save_current_position(project_manager)

3. PositionTabManager
   └─→ Aktuellen Tab finden
   └─→ position_data aus open_positions holen
   └─→ module_tabs.get_position_data()  # Daten aus GUI holen

4. ModuleTabManager
   └─→ eingabemaske_wrapper.get_position_data()

5. EingabemaskeWrapper
   └─→ position_model = PositionModel()
   └─→ Daten aus GUI-Feldern auslesen
   └─→ In position_model speichern
   └─→ return position_model

6. PositionTabManager
   └─→ project_manager.save_position(position_model, position_file)

7. ProjectManager (Backend)
   └─→ JSON-Datei schreiben
```

---

## 🎨 Theme-System

Das Theme wird in `theme_config.py` definiert:

**Wichtig:**
- **MainWindow:** Nutzt `ThemeManager.apply_theme(root)` → aqua-Theme mit weißen Hintergründen
- **Eingabemaske:** Nutzt KEIN Theme (würde crashen) → nur Font-Konfiguration

**Warum?**
- Das aqua-Theme erlaubt keine `background='#FFFFFF'` Optionen für ttk-Widgets
- Wenn wir es trotzdem setzen → `unknown option '-bg'` Fehler
- Lösung: MainWindow nutzt Theme, Eingabemaske nur Fonts

**Schriftgrößen:**
```python
FONT_HEADING = ('', 12, 'bold')  # Überschriften (LabelFrames)
FONT_NORMAL = ('', 10)           # Labels, Buttons, Radiobuttons
Font 9pt für Entry/Combobox      # Eingabefelder kleiner
```

---

## 📂 Projekt-Struktur auf Disk

```
projects_root/
├── Projekt_Wohnhaus/
│   ├── project.json          # Projekt-Metadaten
│   ├── EG/                    # Ordner für Geschoss
│   │   ├── 1.01 - Decke.json
│   │   └── 1.02 - Unterzug.json
│   ├── OG/
│   │   └── 2.01 - Decke.json
│   └── Dach/
│       └── 3.01 - Sparren.json
```

**project.json:**
```json
{
  "name": "Projekt_Wohnhaus",
  "description": "Einfamilienhaus mit Keller",
  "created_at": "2025-01-20T10:30:00",
  "last_modified": "2025-01-20T15:45:00"
}
```

**Position.json (z.B. "1.01 - Decke.json"):**
```json
{
  "position_nummer": "1.01",
  "position_name": "Decke",
  "sprungmass": 1.0,
  "anzahl_felder": 3,
  "kragarm_links": false,
  "kragarm_rechts": false,
  "spannweiten": {
    "feld_1": 5.0,
    "feld_2": 5.0,
    "feld_3": 5.0
  },
  "lasten": [
    {
      "lastfall": "g",
      "q_value": 7.41,
      "kategorie": "Eigengewicht",
      "kommentar": "Alle Lastfälle"
    }
  ],
  ...
}
```

---

## 🔧 Wichtige Backend-Klassen

### **ProjectManager** (`backend/project.py`)
Verwaltet Projekte und Positionen.

**Methoden:**
```python
def create_project(name, description):
    # Projektordner erstellen
    # project.json schreiben
    # Pfad zurückgeben

def open_project(project_path):
    # project.json lesen
    # Metadaten zurückgeben

def create_position(position_model):
    # Position als JSON speichern
    # Dateiname: "1.01 - Decke.json"

def load_position(position_file):
    # JSON lesen
    # PositionModel erstellen
    # Daten füllen
    # Zurückgeben

def save_position(position_model, position_file):
    # PositionModel zu JSON konvertieren
    # In Datei schreiben
```

### **PositionModel** (`backend/models.py`)
Daten-Modell für eine Position.

**Enthält alle Daten:**
- Systemeingaben (Sprungmaß, Felder, Kragarme)
- Spannweiten
- Lasten
- Querschnitt
- Nutzungsklasse
- Berechnungsmodus

**Wichtig:** Dieses Model ist die "Brücke" zwischen GUI und Dateisystem.

---

## 🎯 Zusammenfassung: Wie alles zusammenhängt

```
Benutzer interagiert mit GUI
         ↓
MainWindow koordiniert alles
         ↓
    ┌────┴────┐
    ↓         ↓
Explorer    Tabs
(zeigt)   (bearbeitet)
    ↓         ↓
    └────┬────┘
         ↓
  PositionModel
  (Daten-Objekt)
         ↓
  ProjectManager
  (speichert/lädt)
         ↓
  JSON-Dateien
```

---

## ❓ Soll die Eingabemaske umgebaut werden?

### **NEIN - aus folgenden Gründen:**

#### 1. **Sie funktioniert bereits**
- Die Eingabemaske ist voll funktionsfähig
- Alle Berechnungen laufen
- Integration ins Tab-System funktioniert über Wrapper

#### 2. **CustomTkinter hat Nachteile**
- ❌ Andere Widgets → alles müsste umgeschrieben werden
- ❌ Nicht-native macOS-Optik → verliert native Scrollbars, Dropdowns
- ❌ Mixing mit ttk ist kompliziert → zwei verschiedene Widget-Systeme
- ❌ Mehr Arbeit als Nutzen

#### 3. **Das Wrapper-Pattern ist elegant**
```python
# Die alte Eingabemaske bleibt unverändert
# Wrapper macht sie Tab-kompatibel
# → Keine Umschreibung nötig!
```

#### 4. **Was bereits gut ist:**
- ✅ Einheitliche Schriftgrößen
- ✅ Funktioniert im Tab-System
- ✅ Speichern/Laden funktioniert
- ✅ Alle Berechnungen laufen
- ✅ Native macOS-Widgets (sehen gut aus)

---

## 💡 Was stattdessen verbessern?

### **Kleine, sinnvolle Verbesserungen:**

1. **Eingabefeld-Validierung**
```python
def validate_number(value):
    try:
        float(value)
        return True
    except:
        return False

entry = ttk.Entry(frame, validate='key', 
                  validatecommand=(validate_number, '%P'))
```

2. **Tooltips hinzufügen**
```python
from tkinter import ttk
import tkinter as tk

def create_tooltip(widget, text):
    def on_enter(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
        label = tk.Label(tooltip, text=text, background="yellow")
        label.pack()
        widget.tooltip = tooltip
    
    def on_leave(event):
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

# Nutzung:
entry = ttk.Entry(frame)
create_tooltip(entry, "Sprungmaß in Metern eingeben (z.B. 1.00)")
```

3. **Keyboard-Shortcuts**
```python
# Bereits implementiert:
# Cmd+S → Speichern
# Cmd+W → Tab schließen
# Cmd+N → Neues Projekt
# Cmd+O → Projekt öffnen

# Könnte hinzugefügt werden:
# Tab → Nächstes Feld
# Shift+Tab → Vorheriges Feld
# Enter → Berechnung starten
```

4. **Undo/Redo-Funktion**
```python
class UndoManager:
    def __init__(self):
        self.undo_stack = []
        self.redo_stack = []
    
    def push(self, state):
        self.undo_stack.append(state)
        self.redo_stack.clear()
    
    def undo(self):
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            return state
    
    def redo(self):
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(current_state)
            return state
```

---

## 📚 Weitere Ressourcen

**Tkinter/ttk Dokumentation:**
- [Tkinter Tutorial](https://docs.python.org/3/library/tkinter.html)
- [ttk Widgets](https://docs.python.org/3/library/tkinter.ttk.html)

**Best Practices:**
1. **Separation of Concerns:** GUI ↔ Datenmodell ↔ Dateisystem trennen ✅
2. **Callback-Pattern:** Kommunikation über Callbacks statt direkter Aufrufe ✅
3. **Wrapper-Pattern:** Alte Komponenten durch Wrapper integrieren ✅

---

## 🎓 Für Anfänger: Die wichtigsten Konzepte

### **1. Callbacks**
Eine Funktion als Parameter übergeben:
```python
def button_clicked():
    print("Button wurde geklickt!")

button = ttk.Button(frame, text="Klick mich", command=button_clicked)
```

### **2. Parent-Child-Hierarchie**
Jedes Widget braucht ein Eltern-Widget:
```python
root = tk.Tk()                    # Top-Level
frame = ttk.Frame(root)           # Child von root
button = ttk.Button(frame, ...)   # Child von frame
```

### **3. Pack/Grid/Place Layout-Manager**
```python
# Pack: Widgets stapeln
widget.pack()

# Grid: Tabellen-Layout
widget.grid(row=0, column=1)

# Place: Absolute Position
widget.place(x=100, y=50)
```

### **4. Bind Events**
Auf Ereignisse reagieren:
```python
entry.bind("<KeyRelease>", on_key_pressed)  # Bei jeder Taste
button.bind("<Button-1>", on_left_click)    # Bei Linksklick
```

---

## ✅ Fazit

**Das Frontend ist jetzt professionell aufgebaut:**
- ✅ Klare Struktur mit Trennung der Verantwortlichkeiten
- ✅ Projekt-Management mit Explorer und Tabs
- ✅ Alte Eingabemaske erfolgreich integriert (Wrapper-Pattern)
- ✅ Native macOS-Optik mit aqua-Theme
- ✅ Einheitliche Schriftgrößen

**Kein Umbau nötig!** Die Eingabemaske funktioniert gut, ist integriert und hat native Widgets.

**Fokus stattdessen auf:**
- Kleine UX-Verbesserungen (Tooltips, Validierung)
- Weitere Features (Undo/Redo, Keyboard-Shortcuts)
- Stabilität und Bugfixes

---

**Viel Erfolg mit dem Projekt! 🚀**
