# Bugfix-Plan

## Problem 1: Drag & Drop funktioniert nicht
**Ursache:** Event-Bindings kollidieren. `<ButtonPress-1>` überschreibt Standard-Selektion.
**Lösung:** 
- Threshold einbauen (5 Pixel Bewegung bevor Drag startet)
- `add="+"` bei Event-Bindings verwenden
- Drag-Flag `dragging` verwenden

## Problem 2: Multi-Select funktioniert nicht  
**Ursache:** `selectmode="extended"` ist gesetzt, aber funktioniert nicht wegen Event-Konflikt
**Lösung:**
- Standard-Tkinter Selection NICHT überschreiben
- Nur bei Drag-Motion über Threshold den Drag starten

## Problem 3: Tabs schließen sich nicht beim Projektwechsel
**Ursache:** Vermutlich schon korrekt implementiert in `_close_project()`
**Lösung:**
- Prüfen ob `cleanup()` wirklich aufgerufen wird
- Logging hinzufügen

## Implementierung:
1. project_explorer.py: Saubere Event-Bindings
2. Threshold-basiertes Drag & Drop
3. Keine Interferenz mit Standard-Selection
4. main_window.py: Prüfen ob cleanup aufgerufen wird
