# CustomTkinter Migration - Vollständige Anleitung

## Übersicht

Die GUI wurde von tkinter/ttk auf **CustomTkinter** umgestellt. Dies bietet ein modernes, plattformübergreifendes Design mit automatischem Dark Mode Support.

## Bereits migrierte Dateien ✅

### Kern-GUI-Komponenten
1. **main_window.py** - Hauptfenster mit CTk-Root
2. **project_explorer.py** - Projekt-Explorer (TreeView bleibt tkinter.ttk)
3. **position_tabs.py** - Position-Tab-Manager mit CTkTabview
4. **module_tabs.py** - Modul-Tab-Manager mit CTkTabview
5. **welcome_dialog.py** - Welcome-Dialog mit CTkToplevel

## Verbleibende Dateien (Anleitung)

### 5. Eingabemaske (eingabemaske.py)

**Wichtige Änderungen:**
```python
# Imports
import customtkinter as ctk
from tkinter import ttk  # Nur für Treeview/Spinbox falls nötig

# Widget-Konvertierungen:
ttk.Frame → ctk.CTkFrame
ttk.Label → ctk.CTkLabel
ttk.Button → ctk.CTkButton
ttk.Entry → ctk.CTkEntry
ttk.Combobox → ctk.CTkComboBox
ttk.Checkbutton → ctk.CTkCheckBox
ttk.Radiobutton → ctk.CTkRadioButton
ttk.LabelFrame → ctk.CTkFrame (mit Label oben)
ttk.Spinbox → ctk.CTkEntry (mit +/- Buttons oder bleibt ttk.Spinbox)

# Canvas und Scrollbar bleiben tkinter!
tk.Canvas, ttk.Scrollbar - NICHT ändern
```

**Spezielle Anpassungen:**
- `ttk.Separator` → `ctk.CTkFrame(height=2)` oder weglassen
- `foreground="color"` → `text_color="color"`
- Dropdown `state="readonly"` → `state="readonly"` (gleich)

### 6. Display-Module

**anzeige_system.py, anzeige_lastkombination.py, anzeige_nachweis_ec5.py, anzeige_feebb.py:**

```python
# Imports
import customtkinter as ctk

# Widget-Konvertierungen
ttk.Frame → ctk.CTkFrame
ttk.LabelFrame → ctk.CTkFrame + ctk.CTkLabel für Titel
ttk.Label → ctk.CTkLabel
ttk.Button → ctk.CTkButton

# Canvas, PIL ImageTk bleiben unverändert!
```

### 7. Eingabemaske Wrapper

**eingabemaske_wrapper.py:**
```python
# MockRoot muss tkinter.Tk-Methoden unterstützen
# Da CustomTkinter auf tkinter basiert, sollte es funktionieren
# Eventuell CTk-spezifische Attribute hinzufügen
```

### 8. Theme Config

**theme_config.py:**
```python
# CustomTkinter hat eigenes Theme-System
# ThemeManager.apply_theme() → durch ctk.set_appearance_mode() ersetzen
# ctk.set_appearance_mode("system")  # oder "light", "dark"
# ctk.set_default_color_theme("blue")  # oder "green", "dark-blue"
```

## Globale Suchen & Ersetzen (Regex)

Für große Dateien wie eingabemaske.py können Sie diese Ersetzungen verwenden:

```regex
# 1. Imports
from tkinter import ttk → import customtkinter as ctk

# 2. Frame
ttk\.Frame\( → ctk.CTkFrame(

# 3. Labels
ttk\.Label\( → ctk.CTkLabel(

# 4. Buttons
ttk\.Button\( → ctk.CTkButton(

# 5. Entry
ttk\.Entry\( → ctk.CTkEntry(

# 6. Combobox
ttk\.Combobox\( → ctk.CTkComboBox(

# 7. Checkbutton
ttk\.Checkbutton\( → ctk.CTkCheckBox(

# 8. Radiobutton
ttk\.Radiobutton\( → ctk.CTkRadioButton(

# 9. LabelFrame (manuell anpassen)
ttk\.LabelFrame → ctk.CTkFrame

# 10. foreground Parameter
foreground=" → text_color="
```

## Wichtige Hinweise ⚠️

### Was NICHT geändert werden darf:
1. **tkinter.Menu** - CustomTkinter hat kein natives Menü-System
2. **tkinter.Canvas** - Wird für Plots/Diagramme benötigt
3. **ttk.Treeview** - CustomTkinter hat kein TreeView
4. **ttk.Scrollbar** - Funktioniert mit Canvas
5. **tk.IntVar, tk.StringVar, tk.BooleanVar** - Bleiben tkinter

### Variablennamen
- **ALLE** Variablennamen bleiben gleich (wie vom Benutzer gewünscht)
- Nur das Frontend wird geändert, Backend bleibt unverändert

## CTkTabview vs. ttk.Notebook

CustomTkinter verwendet CTkTabview statt Notebook:

```python
# Alt (ttk.Notebook)
notebook = ttk.Notebook(parent)
frame = ttk.Frame(notebook)
notebook.add(frame, text="Tab 1")
notebook.select(frame)

# Neu (CTkTabview)
tabview = ctk.CTkTabview(parent)
tabview.add("Tab 1")
frame = tabview.tab("Tab 1")
tabview.set("Tab 1")
```

## Appearance Mode

CustomTkinter unterstützt automatisch Light/Dark Mode:

```python
# Global setzen (am Anfang)
ctk.set_appearance_mode("system")  # "system", "light", "dark"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

# Wechseln
current = ctk.get_appearance_mode()
new = "light" if current == "Dark" else "dark"
ctk.set_appearance_mode(new)
```

## Testen

Nach der Migration:

1. Alle Imports prüfen
2. Fenster starten: `python main_v2.py`
3. Funktionalität testen:
   - Projekt erstellen/öffnen
   - Positionen hinzufügen
   - Tabs wechseln
   - Eingaben machen
4. Dark Mode testen: Cmd+D

## Beispiel: Vollständige Widget-Konvertierung

### Vorher (tkinter/ttk):
```python
import tkinter as tk
from tkinter import ttk

frame = ttk.Frame(parent, padding=10)
label = ttk.Label(frame, text="Hallo", foreground="blue")
button = ttk.Button(frame, text="OK", command=callback)
entry = ttk.Entry(frame, width=20)
combo = ttk.Combobox(frame, values=["A", "B"], state="readonly")
check = ttk.Checkbutton(frame, text="Option", variable=var)
```

### Nachher (CustomTkinter):
```python
import tkinter as tk
import customtkinter as ctk

frame = ctk.CTkFrame(parent)
label = ctk.CTkLabel(frame, text="Hallo", text_color="blue")
button = ctk.CTkButton(frame, text="OK", command=callback)
entry = ctk.CTkEntry(frame, width=200)
combo = ctk.CTkComboBox(frame, values=["A", "B"], state="readonly")
check = ctk.CTkCheckBox(frame, text="Option", variable=var)
```

## Fertigstellung

Alle migriert? Teste mit:
```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Studium Gesamt/Studium/8. Semester/Python/Statikprogramm"
python main_v2.py
```

---
**Status:** Kern-GUI erfolgreich migriert ✅  
**To-Do:** Eingabemaske + Display-Module (siehe Anleitung oben)
