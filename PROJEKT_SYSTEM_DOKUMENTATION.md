# Projekt- und Dateibrowser-System - Dokumentation

## Übersicht

Das Statikprogramm verfügt über ein vollständiges Projekt- und Dateibrowser-System mit folgenden Features:
- **UUID-basierte Projektverwaltung** für eindeutige Identifikation
- **Erweiterte Recent Projects** mit Metadaten (Name, Datum, UUID)
- **Ordner- und Unterordner-Struktur** im Dateibrowser
- **Keyboard Shortcuts** für effiziente Navigation
- **Automatisches Cleanup** nicht existierender Projekte

---

## 1. Projekt-Struktur

### Projekt-Metadaten (`project.json`)

Jedes Projekt hat eine `project.json` Datei mit folgender Struktur:

```json
{
  "uuid": "abc-123-def-456",
  "name": "Mein Projekt",
  "created": "2025-11-16T10:00:00",
  "last_modified": "2025-11-16T15:30:00",
  "description": "Projektbeschreibung",
  "positions": []
}
```

**Wichtig:** Die `uuid` ist eindeutig und bleibt auch bei Umbenennung erhalten!

### Migration alter Projekte

- **Automatisch:** Beim Öffnen alter Projekte (ohne UUID) wird automatisch eine UUID generiert
- **Keine Datenverluste:** Alte Projekte funktionieren weiterhin
- **Sofortige Persistierung:** Die UUID wird direkt in `project.json` gespeichert

---

## 2. Recent Projects System

### Datenstruktur

Recent Projects werden in `config/settings.json` gespeichert:

```json
{
  "recent_projects": [
    {
      "uuid": "abc-123",
      "path": "/path/to/project",
      "name": "Projekt 1",
      "last_opened": "2025-11-16T10:00:00"
    }
  ]
}
```

### Features

✅ **Automatisches Cleanup**
- Nicht existierende Projekte werden automatisch entfernt
- Cleanup erfolgt beim Öffnen des Welcome-Dialogs
- Keine manuellen Eingriffe nötig

✅ **UUID-basierte Aktualisierung**
- Bei Umbenennung eines Projekts wird der Pfad in Recent automatisch aktualisiert
- Methode: `settings_manager.update_recent_project_path(uuid, new_path, new_name)`

✅ **Migration alter Einträge**
- Alte String-Einträge werden automatisch zu Dict-Format migriert
- Format: `"/path/to/project"` → `{"uuid": "migrated", "path": ..., "name": ..., "last_opened": "unknown"}`

---

## 3. Ordner-Verwaltung

### Ordner erstellen
- **Rechtsklick** im Tree → "Neuer Ordner..."
- Ordner können verschachtelt werden (Unterordner in Unterordnern)
- Automatische Sortierung: Ordner zuerst, dann Positionen

### Ordner löschen
- **Rechtsklick** → "Löschen" ODER **Delete/BackSpace** Taste
- Sicherheitsabfrage bei nicht-leeren Ordnern
- Rekursives Löschen aller Inhalte

### Ordner umbenennen
- **Rechtsklick** → "Umbenennen" ODER **F2** Taste
- Pfad wird automatisch aktualisiert

---

## 4. Keyboard Shortcuts

| Taste | Aktion |
|-------|--------|
| **F2** | Umbenennen (Position oder Ordner) |
| **Delete** | Löschen (mit Sicherheitsabfrage) |
| **BackSpace** | Löschen (macOS) |
| **Return** | Öffnen der ausgewählten Position |
| **Doppelklick** | Position öffnen |
| **Rechtsklick** | Kontextmenü |
| **Theme-Support** | ✅ | Bereits vorhanden (Dark/Light) |
| **Tab-System** | ✅ | Bereits vorhanden + Schließbar |
| **Migration** | ✅ | Alte Projekte + Recent Projects |
| **Multi-Select** | ✅ | Vollständig implementiert! |
| **Drag & Drop** | ✅ | Vollständig mit visuellem Feedback! |

---

## 5. Last Project Directory

### Funktion
- Das zuletzt verwendete Verzeichnis wird gespeichert
- Öffnen/Speichern-Dialoge starten im gespeicherten Verzeichnis
- Automatische Aktualisierung bei jedem Öffnen

### Verwendung

```python
# Beim Öffnen eines Projekts
self.settings_manager.set_last_project_dir(str(project_path.parent))

# Im Öffnen-Dialog
last_dir = self.settings_manager.get_last_project_dir()
if not last_dir or not Path(last_dir).exists():
    last_dir = self.project_manager.projects_root
```

---

## 6. API-Referenz

### ProjectManager

```python
# UUID des aktuellen Projekts abrufen
uuid = project_manager.get_project_uuid()

# Projekt erstellen (UUID wird automatisch generiert)
project_path = project_manager.create_project("Projektname", "Beschreibung")

# Projekt öffnen (Migration erfolgt automatisch)
project_data = project_manager.open_project(project_path)
```

### SettingsManager

```python
# Recent Project hinzufügen (MIT Metadaten)
settings_manager.add_recent_project(
    project_path="/path/to/project",
    project_uuid="abc-123",
    project_name="Mein Projekt"
)

# Recent Projects abrufen (mit automatischem Cleanup)
recent = settings_manager.get_recent_projects(cleanup_missing=True)

# Projekt-Pfad nach UUID aktualisieren
settings_manager.update_recent_project_path(
    project_uuid="abc-123",
    new_path="/new/path",
    new_name="Neuer Name"
)

# Last Project Directory
settings_manager.set_last_project_dir("/path/to/directory")
last_dir = settings_manager.get_last_project_dir()
```

---

## 7. Welcome-Dialog

### Features
- **Recent Projects** mit Metadaten (Name, Pfad, Datum)
- **Automatisches Cleanup** nicht existierender Projekte
- **Tooltip** zeigt Pfad und "Zuletzt geöffnet"-Datum
- **Max. 3 Projekte** werden angezeigt

### Anzeige-Format
```
📁 Projekt 1
/path/to/project (zuletzt geöffnet: 16.11.2025 10:00)
```

---

## 8. Multi-Select & Drag & Drop ✅

**Status:** Vollständig implementiert!

### Multi-Select

**Aktivierung:**
- TTK Treeview mit `selectmode="extended"`
- **Strg/Cmd + Klick**: Einzelne Items hinzufügen/entfernen
- **Shift + Klick**: Bereich auswählen
- **Strg/Cmd + A**: Alle auswählen (Standard TTK)

**Batch-Operationen:**
- **Löschen mehrerer Items**: Alle selektierten Items werden mit einer Sicherheitsabfrage gelöscht
- **Verschieben mehrerer Items**: Drag & Drop funktioniert mit Multi-Selection

### Drag & Drop

**Funktionsweise:**
1. **Drag starten**: Klicke und halte auf ein Item (oder selektierte Items)
2. **Drag bewegen**: Ziehe Items zu einem Zielordner
3. **Drop ausführen**: Lasse Maustaste los, um Items zu verschieben

**Visuelles Feedback:**
- **Während Drag**: Items werden mit blau-grauer/hellblauer Hintergrundfarbe markiert
- **Drop-Ziel**: Potentielle Zielordner werden mit türkis/grüner Farbe hervorgehoben
- **Theme-abhängig**: 
  - Dark Mode: Blau-grau (#3d5a80) für Drag, Türkis (#2a9d8f) für Drop-Target
  - Light Mode: Hellblau (#cce5ff) für Drag, Hellgrün (#90ee90) für Drop-Target

**Regeln:**
- Drop nur auf **Ordner** oder **Projekt-Root** erlaubt
- **Keine Schleifen**: Items können nicht auf sich selbst oder ihre Kinder gedroppt werden
- **Duplikat-Check**: Warnung bei bereits existierenden Zielen
- **Fehlerbehandlung**: Teilweise erfolgreiche Operationen werden gemeldet

**Multi-Item Drag:**
- Ziehe ein selektiertes Item → alle selektierten Items werden mitbewegt
- Ziehe ein nicht-selektiertes Item → nur dieses Item wird bewegt

---

## 9. Testing & Verifikation

### Test-Szenarios

✅ **Altes Projekt öffnen (ohne UUID)**
1. Öffne altes Projekt
2. UUID wird automatisch generiert
3. Projekt funktioniert normal
4. UUID ist in `project.json` gespeichert

✅ **Recent Projects Cleanup**
1. Lösche Projekt-Ordner manuell
2. Öffne Welcome-Dialog
3. Gelöschtes Projekt wird automatisch entfernt

✅ **Projekt umbenennen**
1. Benenne Projekt-Ordner um
2. UUID bleibt erhalten
3. Recent Projects wird (noch) nicht automatisch aktualisiert
   - **TODO:** Hook für Umbenennung über GUI hinzufügen

✅ **Keyboard Shortcuts**
1. Wähle Position im Tree
2. Drücke F2 → Umbenennen-Dialog öffnet sich
3. Drücke Delete → Löschen-Dialog öffnet sich
4. Drücke Return → Position wird geöffnet

---

## 10. Bekannte Einschränkungen

### Multi-Select
- Nicht implementiert (TTK Treeview Limitation)
- Einzelselektion funktioniert perfekt

### Drag & Drop
- Nicht implementiert
- Positionen können durch Ausschneiden/Einfügen verschoben werden

### Umbenennung via OS
- Wenn Projekt-Ordner außerhalb der App umbenannt wird:
  - UUID bleibt erhalten ✅
  - Recent Projects zeigt alten Pfad ⚠️
  - **Workaround:** Projekt manuell aus Recent entfernen und neu öffnen

---

## 11. Zukunfts-Erweiterungen

### Mögliche Features
1. **Project History** - Änderungshistorie pro Projekt
2. **Project Tags** - Tagging-System für Kategorisierung
3. **Project Search** - Globale Suche über alle Projekte
4. **Cloud Sync** - Synchronisation mit Cloud-Storage
5. **Project Templates** - Vorlagen für neue Projekte
6. **Collaborative Features** - Mehrbenutzer-Unterstützung

---

## 12. Fehlerbehebung

### Problem: Recent Projects zeigt falschen Pfad
**Lösung:** Projekt aus Recent entfernen und neu öffnen

### Problem: UUID-Migration funktioniert nicht
**Lösung:** `project.json` manuell prüfen, UUID hinzufügen:
```json
{
  "uuid": "manuelle-uuid-123",
  ...
}
```

### Problem: Keyboard Shortcuts funktionieren nicht
**Lösung:** Tree muss Fokus haben (einmal klicken)

---

## Kontakt & Support

Bei Fragen oder Problemen:
- Logging aktivieren: `logging.basicConfig(level=logging.DEBUG)`
- Log-Dateien prüfen
- Issues auf GitHub erstellen (falls vorhanden)

---

**Version:** 2.0  
**Letzte Aktualisierung:** 16.11.2025  
**Autor:** Maximilian Stark
