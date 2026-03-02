# Design: Local File Management (File System Access API)

**Date:** 2026-03-02
**Status:** Approved
**Author:** Developer Dave + Maximilian Stark

---

## Summary

Add local project storage alongside the existing server-side storage.
Users can open a local folder on their machine via the browser's
File System Access API. All edits auto-save directly to disk (silent,
2 s debounce). Server projects remain unchanged. Optional manual sync
between local and server is possible.

---

## Goals

- Open any local folder as a project (same structure as server)
- Auto-save every change directly into the local JSON files (no prompts)
- Keep server projects working exactly as before
- Allow manual sync: Local → Server and Server → Local
- Server projects have a visibility flag: `private` (default) or `shared`
- Works in Chrome, Edge, Firefox 111+

---

## Non-Goals

- Offline calculations (server always required for FEM/EC5)
- Automatic sync / conflict resolution
- New file format (same JSON as server)
- Safari support (graceful error message shown instead)

---

## Approach: File System Access API

`showDirectoryPicker()` gives the browser a `FileSystemDirectoryHandle`
to a real folder on disk. The app reads/writes JSON files directly via
this handle. The handle is persisted in IndexedDB so the user only needs
to re-grant permission once per browser session (one click per folder).

---

## UI Design

The ProjectExplorer sidebar gets two tabs:

```
┌─────────────────────────────┐
│  📁 Projekte                │
│  ┌──────────┬─────────────┐ │
│  │  Server  │   Lokal  ▶  │ │
│  └──────────┴─────────────┘ │
│                             │
│  + Ordner öffnen            │  → showDirectoryPicker()
│  + Neues lokales Projekt    │  → new folder + project.json
│                             │
│  📂 Demo_Wohnhaus    🔄 ☁↑ │  → 🔄 = unsaved, ☁↑ = sync to server
│    📂 EG                    │
│      📄 Pos 1.01 Wohnzimmer │
│      📄 Pos 1.02 Sparren    │
│                             │
│  ⚠️ [Zugriff wieder erlauben]│  → shown if permission expired
└─────────────────────────────┘
```

- Multiple local folders can be open simultaneously
- Server tab: unchanged behavior
- Local tab: all opened local folders listed

---

## Folder Structure on Disk

Identical to server structure — no conversion needed:

```
~/Dokumente/Statik/Demo_Wohnhaus/
  ├── project.json
  ├── EG/
  │   ├── Position_1_01_HT_1.json
  │   └── Position_1_02_Sparren.json
  └── OG/
      └── Position_2_01_Decke.json
```

Copy-paste in Finder → directly loadable on server and vice versa.

---

## Data Model

### IndexedDB handle store

```
DB: "statik-local-handles"
  "handle:<folder-name>" → FileSystemDirectoryHandle
```

On page load: `handle.queryPermission({ mode: 'readwrite' })`
- `'granted'`  → load immediately
- `'prompt'`   → show "Zugriff wieder erlauben" button
- `'denied'`   → show error, offer to re-link or remove

### Frontend store (new: useLocalProjectStore)

```typescript
interface LocalProjectEntry {
  handle: FileSystemDirectoryHandle;
  project: ProjectMetadata;     // from project.json
  positions: PositionEntry[];   // scanned from folder
}
```

`useBeamStore` and all calculation logic remain unchanged.
Only the load (read) and auto-save (write) path differs.

### Operation mapping

| Action              | Server project          | Local project                        |
|---------------------|-------------------------|--------------------------------------|
| Load position       | GET /api/projects/…     | FileSystemFileHandle.getFile()       |
| Auto-save           | PUT /api/projects/…     | FileSystemFileHandle.createWritable()|
| Rename position     | PATCH /api/…/rename     | handle.move() / rename               |
| Delete position     | DELETE /api/…           | handle.removeEntry()                 |
| **Calculation**     | POST /api/calculate     | POST /api/calculate ← always server  |

---

## Auto-Save Behaviour

- Trigger: same as current (any form change → 2 s debounce)
- For local positions: write JSON directly to disk via `createWritable()`
- **Completely silent** – no toast, no spinner, no confirmation
- `isDirty` flag cleared after successful write (same as server path)

---

## Sync Feature

### Local → Server (☁↑)

1. User clicks ☁↑ on a local project
2. Dialog: confirm project name + choose visibility (`private` / `shared`)
3. `POST /api/projects` to create project on server
4. `PUT /api/projects/{id}/positions/…` for each position file
5. Project now appears in Server tab too

### Server → Local (☁↓)

1. User clicks ☁↓ on a server project
2. `showDirectoryPicker()` → user selects or creates target folder
3. App reads all positions from server and writes JSON files to folder
4. Handle saved in IndexedDB → project appears in Local tab

### Conflict handling

No automatic merge. Both directions are explicit bulk overwrites:
- Upload (Local → Server): warning dialog before overwriting server version
- Download (Server → Local): warning dialog before overwriting local files
- Normal auto-save: always silent, no warnings

---

## Visibility (Server Projects)

`project.json` gets a `visibility` field:

| Value     | Meaning                                    |
|-----------|--------------------------------------------|
| `private` | Only visible to uploader **(default)**     |
| `shared`  | Visible to all users with tool access      |

- Shown as 🔒 (private) or 👥 (shared) in Server tab
- Toggle via context menu on the project
- Backend: `PATCH /api/projects/{id}/visibility` endpoint

---

## Error Handling

| Situation                        | Behaviour                                              |
|----------------------------------|--------------------------------------------------------|
| Permission expired after restart | Show "Zugriff wieder erlauben" button per folder       |
| Folder moved/deleted in Finder   | Show "Ordner nicht mehr gefunden – neu verknüpfen"     |
| Folder is read-only              | Show "Schreibzugriff verweigert" in ProjectExplorer    |
| Browser without API support      | Show "Lokale Projekte werden in Chrome, Edge und Firefox 111+ unterstützt" |

---

## Backend Changes

- Add `visibility` field to `project.json` schema (default `private`)
- Add `PATCH /api/projects/{id}/visibility` endpoint
- No other backend changes for local project operations

---

## New Frontend Modules

| Module                          | Purpose                                           |
|---------------------------------|---------------------------------------------------|
| `useLocalProjectStore.ts`       | Zustand store for local project state             |
| `useLocalFileSystem.ts`         | Wraps File System Access API (open, read, write)  |
| `useLocalProjectActions.ts`     | CRUD operations on local files                    |
| `localHandleStorage.ts`         | IndexedDB persistence for directory handles       |
| `ProjectExplorer.tsx`           | Add Server/Lokal tabs (refactor existing)         |

---

## Implementation Phases

1. **Phase 1** – Core local read: open folder, scan structure, load positions
2. **Phase 2** – Auto-save to local files
3. **Phase 3** – Create/rename/delete positions in local folder
4. **Phase 4** – Sync Local → Server and Server → Local
5. **Phase 5** – Visibility flag on server projects
