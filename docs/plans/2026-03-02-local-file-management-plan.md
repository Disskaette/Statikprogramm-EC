# Local File Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Allow users to open a local folder on their machine as a project, auto-save edits directly to disk, and optionally sync between local and server.

**Architecture:** File System Access API (`showDirectoryPicker`) gives the browser a `FileSystemDirectoryHandle` to a real folder. Handles are persisted in IndexedDB so permission only needs to be re-granted once per browser session. A new `useLocalProjectStore` (Zustand) manages the list of open local projects independently from the server-side `useProjectStore`. The `currentProjectMode` field in `useProjectStore` routes auto-save to either the API or the local disk.

**Tech Stack:** TypeScript, React 19, Zustand, idb-keyval (IndexedDB), File System Access API, Vite, TailwindCSS, FastAPI (backend, only for sync + visibility)

---

## Overview of new files

```
web/frontend/src/
  lib/
    localHandleStorage.ts      ← IndexedDB persistence for directory handles
  fs/
    useLocalFileSystem.ts      ← File System Access API wrapper
  stores/
    useLocalProjectStore.ts    ← Zustand store: list of open local projects
  hooks/
    useLocalProjectActions.ts  ← CRUD on local files (mirrors useProjectActions)
  types/
    localProject.ts            ← TypeScript interfaces for local projects
```

Modified files:
```
web/frontend/src/
  stores/useProjectStore.ts         ← add currentProjectMode + currentLocalProjectId
  hooks/useAutoSave.ts              ← route to local save when mode = 'local'
  components/sidebar/ProjectExplorer.tsx  ← add Server/Lokal tabs
web/api/routes/projects.py         ← add visibility field + PATCH endpoint
backend/project/project_manager.py ← add visibility support
```

---

## Task 1: Install idb-keyval + add TypeScript types for local projects

**Files:**
- Modify: `web/frontend/package.json`
- Create: `web/frontend/src/types/localProject.ts`

### Step 1: Install idb-keyval

```bash
cd web/frontend
npm install idb-keyval
```

Expected: `idb-keyval` appears in `package.json` dependencies.

### Step 2: Create local project types

Create `web/frontend/src/types/localProject.ts`:

```typescript
/**
 * TypeScript interfaces for local (File System Access API) projects.
 *
 * A LocalProject mirrors the server Project shape, but uses a
 * FileSystemDirectoryHandle instead of a server UUID.
 */

import type { Position } from "@/types/project";

// ---------------------------------------------------------------------------
// Handle storage entry (persisted in IndexedDB)
// ---------------------------------------------------------------------------

/** Key used in IndexedDB to store a directory handle */
export type HandleKey = string; // e.g. "local:Demo_Wohnhaus"

// ---------------------------------------------------------------------------
// Local project metadata (read from project.json in the opened folder)
// ---------------------------------------------------------------------------

export interface LocalProjectMeta {
  /** UUID from project.json (same as server format) */
  uuid: string;
  /** Human-readable project name */
  name: string;
  /** ISO 8601 creation timestamp */
  created: string;
  /** ISO 8601 last-modified timestamp */
  last_modified: string;
  /** Optional description */
  description: string;
}

// ---------------------------------------------------------------------------
// Full local project entry (in useLocalProjectStore)
// ---------------------------------------------------------------------------

export interface LocalProjectEntry {
  /**
   * Stable key for IndexedDB and store lookup.
   * Format: "local:<folder-name>" e.g. "local:Demo_Wohnhaus"
   */
  key: HandleKey;
  /** The directory handle – used for all file I/O */
  handle: FileSystemDirectoryHandle;
  /** Metadata parsed from project.json */
  meta: LocalProjectMeta;
  /**
   * Flat list of all positions found by scanning the folder recursively.
   * Same Position shape as server, but file_path is relative to handle root.
   */
  positions: Position[];
  /** True if the handle currently has readwrite permission */
  hasPermission: boolean;
}

// ---------------------------------------------------------------------------
// Permission status
// ---------------------------------------------------------------------------

export type PermissionStatus = "granted" | "prompt" | "denied";
```

### Step 3: Commit

```bash
git add web/frontend/package.json web/frontend/package-lock.json web/frontend/src/types/localProject.ts
git commit -m "feat: add idb-keyval dependency + local project TypeScript types"
```

---

## Task 2: localHandleStorage.ts – IndexedDB persistence for handles

**Files:**
- Create: `web/frontend/src/lib/localHandleStorage.ts`

`FileSystemDirectoryHandle` is structured-cloneable and can be stored
directly in IndexedDB. idb-keyval wraps the API in a simple key/value store.

Create `web/frontend/src/lib/localHandleStorage.ts`:

```typescript
/**
 * localHandleStorage – persists FileSystemDirectoryHandle in IndexedDB.
 *
 * Uses idb-keyval with a dedicated store ("statik-local-handles") so we
 * don't pollute the default store.
 *
 * Note: FileSystemDirectoryHandle is structured-cloneable → can be stored
 * in IndexedDB natively (no serialisation needed).
 */

import { createStore, get, set, del, keys } from "idb-keyval";
import type { HandleKey } from "@/types/localProject";

// Dedicated IndexedDB store (db: "statik-local", store: "handles")
const idbStore = createStore("statik-local", "handles");

/** Persist a handle under the given key */
export async function saveHandle(
  key: HandleKey,
  handle: FileSystemDirectoryHandle
): Promise<void> {
  await set(key, handle, idbStore);
}

/** Retrieve a previously saved handle, or null if not found */
export async function loadHandle(
  key: HandleKey
): Promise<FileSystemDirectoryHandle | null> {
  return (await get<FileSystemDirectoryHandle>(key, idbStore)) ?? null;
}

/** Remove a handle from IndexedDB */
export async function removeHandle(key: HandleKey): Promise<void> {
  await del(key, idbStore);
}

/** List all stored handle keys */
export async function listHandleKeys(): Promise<HandleKey[]> {
  return (await keys(idbStore)) as HandleKey[];
}

/**
 * Check the current permission state for a handle.
 * Returns 'granted', 'prompt', or 'denied'.
 */
export async function queryHandlePermission(
  handle: FileSystemDirectoryHandle
): Promise<PermissionState> {
  return handle.queryPermission({ mode: "readwrite" });
}

/**
 * Request readwrite permission for a handle.
 * Must be called from a user gesture (e.g. button click).
 * Returns the new permission state.
 */
export async function requestHandlePermission(
  handle: FileSystemDirectoryHandle
): Promise<PermissionState> {
  return handle.requestPermission({ mode: "readwrite" });
}
```

### Verify: TypeScript compiles

```bash
cd web/frontend
npm run build 2>&1 | grep -E "error|warning" | head -20
```

Expected: no TypeScript errors related to localHandleStorage.

### Commit

```bash
git add web/frontend/src/lib/localHandleStorage.ts
git commit -m "feat: add IndexedDB handle storage for local projects"
```

---

## Task 3: useLocalFileSystem.ts – File System Access API wrapper

**Files:**
- Create: `web/frontend/src/fs/useLocalFileSystem.ts`

This module wraps all File System Access API calls. It handles:
- Feature detection
- Opening a folder picker
- Scanning a folder recursively for project.json + positions
- Reading a position JSON file
- Writing a position JSON file

Create `web/frontend/src/fs/useLocalFileSystem.ts`:

```typescript
/**
 * useLocalFileSystem – File System Access API wrapper.
 *
 * All functions are async and throw descriptive errors on failure.
 * Feature detection: check `isFileSystemAccessSupported()` before calling
 * any picker functions.
 */

import type { LocalProjectMeta } from "@/types/localProject";
import type { Position } from "@/types/project";

// ---------------------------------------------------------------------------
// Feature detection
// ---------------------------------------------------------------------------

/** True if the browser supports the File System Access API (showDirectoryPicker) */
export function isFileSystemAccessSupported(): boolean {
  return "showDirectoryPicker" in window;
}

// ---------------------------------------------------------------------------
// Open folder picker
// ---------------------------------------------------------------------------

/**
 * Opens the browser's directory picker and returns the chosen handle.
 * Throws if the user cancels (AbortError).
 */
export async function pickDirectory(): Promise<FileSystemDirectoryHandle> {
  if (!isFileSystemAccessSupported()) {
    throw new Error(
      "Lokale Projekte werden in Chrome, Edge und Firefox 111+ unterstützt."
    );
  }
  // showDirectoryPicker is defined globally in modern browsers
  return (window as Window & typeof globalThis & {
    showDirectoryPicker: (options?: DirectoryPickerOptions) => Promise<FileSystemDirectoryHandle>;
  }).showDirectoryPicker({ mode: "readwrite" });
}

// ---------------------------------------------------------------------------
// Scan folder recursively
// ---------------------------------------------------------------------------

/**
 * Scans a directory handle recursively and collects all .json files that
 * look like position files (contain position_nummer + position_name fields).
 *
 * Returns: { meta, positions } where meta is from project.json and positions
 * is the flat list of all found positions with relative_path populated.
 */
export async function scanProjectFolder(
  handle: FileSystemDirectoryHandle
): Promise<{ meta: LocalProjectMeta; positions: Position[] }> {
  // 1. Read project.json from root
  const meta = await readProjectJson(handle);

  // 2. Recursively collect all positions
  const positions: Position[] = [];
  await collectPositions(handle, "", positions);

  return { meta, positions };
}

/** Read and parse project.json from the root of a handle */
async function readProjectJson(
  handle: FileSystemDirectoryHandle
): Promise<LocalProjectMeta> {
  try {
    const fileHandle = await handle.getFileHandle("project.json");
    const file = await fileHandle.getFile();
    const text = await file.text();
    const data = JSON.parse(text);
    return {
      uuid: data.uuid ?? crypto.randomUUID(),
      name: data.name ?? handle.name,
      created: data.created ?? new Date().toISOString(),
      last_modified: data.last_modified ?? new Date().toISOString(),
      description: data.description ?? "",
    };
  } catch {
    // No project.json → synthesise metadata from folder name
    return {
      uuid: crypto.randomUUID(),
      name: handle.name,
      created: new Date().toISOString(),
      last_modified: new Date().toISOString(),
      description: "",
    };
  }
}

/**
 * Recursively walk a directory handle and push position entries.
 * `prefix` is the relative path from the project root (empty for root).
 */
async function collectPositions(
  dirHandle: FileSystemDirectoryHandle,
  prefix: string,
  out: Position[]
): Promise<void> {
  for await (const [name, entry] of dirHandle.entries()) {
    // Skip project.json and hidden files
    if (name === "project.json" || name.startsWith(".")) continue;

    if (entry.kind === "file" && name.endsWith(".json")) {
      const relativePath = prefix ? `${prefix}/${name}` : name;
      try {
        const file = await (entry as FileSystemFileHandle).getFile();
        const text = await file.text();
        const data = JSON.parse(text);

        // Only include if it looks like a position (has position_nummer)
        if (data.position_nummer !== undefined) {
          out.push({
            position_nummer: data.position_nummer ?? "",
            position_name: data.position_name ?? "",
            created: data.created ?? "",
            last_modified: data.last_modified ?? "",
            active_module: data.active_module ?? "durchlauftraeger",
            modules: data.modules ?? {},
            file_path: relativePath, // used as ID for local positions
            relative_path: relativePath,
          });
        }
      } catch {
        // Skip unreadable / malformed files silently
      }
    } else if (entry.kind === "directory") {
      const subPrefix = prefix ? `${prefix}/${name}` : name;
      await collectPositions(entry as FileSystemDirectoryHandle, subPrefix, out);
    }
  }
}

// ---------------------------------------------------------------------------
// Read a single position file
// ---------------------------------------------------------------------------

/**
 * Read a position JSON from a local folder by its relative_path.
 * Returns the parsed Position object.
 */
export async function readPositionFile(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string
): Promise<Position> {
  const fileHandle = await resolveFileHandle(rootHandle, relativePath);
  const file = await fileHandle.getFile();
  const text = await file.text();
  const data = JSON.parse(text);
  return {
    position_nummer: data.position_nummer ?? "",
    position_name: data.position_name ?? "",
    created: data.created ?? "",
    last_modified: data.last_modified ?? "",
    active_module: data.active_module ?? "durchlauftraeger",
    modules: data.modules ?? {},
    file_path: relativePath,
    relative_path: relativePath,
  };
}

// ---------------------------------------------------------------------------
// Write a position file
// ---------------------------------------------------------------------------

/**
 * Write a position JSON to a local folder.
 * Creates parent directories if needed.
 */
export async function writePositionFile(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string,
  data: Record<string, unknown>
): Promise<void> {
  // Ensure parent directories exist
  const parts = relativePath.split("/");
  const fileName = parts.pop()!;
  let dirHandle: FileSystemDirectoryHandle = rootHandle;
  for (const part of parts) {
    dirHandle = await dirHandle.getDirectoryHandle(part, { create: true });
  }

  // Write the file
  const fileHandle = await dirHandle.getFileHandle(fileName, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(JSON.stringify({ ...data, last_modified: new Date().toISOString() }, null, 2));
  await writable.close();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Resolve a relative path like "EG/Position_1_01.json" to a FileSystemFileHandle */
async function resolveFileHandle(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string
): Promise<FileSystemFileHandle> {
  const parts = relativePath.split("/");
  const fileName = parts.pop()!;
  let dirHandle: FileSystemDirectoryHandle = rootHandle;
  for (const part of parts) {
    dirHandle = await dirHandle.getDirectoryHandle(part);
  }
  return dirHandle.getFileHandle(fileName);
}

/**
 * Delete a file from a local folder by relative path.
 */
export async function deletePositionFile(
  rootHandle: FileSystemDirectoryHandle,
  relativePath: string
): Promise<void> {
  const parts = relativePath.split("/");
  const fileName = parts.pop()!;
  let dirHandle: FileSystemDirectoryHandle = rootHandle;
  for (const part of parts) {
    dirHandle = await dirHandle.getDirectoryHandle(part);
  }
  await dirHandle.removeEntry(fileName);
}
```

### Verify: TypeScript compiles

```bash
cd web/frontend && npm run build 2>&1 | grep -E "^.*error" | head -20
```

Expected: no errors from the new file.

### Commit

```bash
git add web/frontend/src/fs/useLocalFileSystem.ts
git commit -m "feat: add File System Access API wrapper (useLocalFileSystem)"
```

---

## Task 4: useLocalProjectStore.ts – Zustand store for local projects

**Files:**
- Create: `web/frontend/src/stores/useLocalProjectStore.ts`

```typescript
/**
 * useLocalProjectStore – Zustand store for locally opened projects.
 *
 * Holds the list of LocalProjectEntry objects (one per opened folder).
 * Handles are restored from IndexedDB on app load via initLocalProjects().
 */

import { create } from "zustand";
import type { LocalProjectEntry, HandleKey } from "@/types/localProject";
import {
  saveHandle,
  removeHandle,
  listHandleKeys,
  loadHandle,
  queryHandlePermission,
} from "@/lib/localHandleStorage";
import { scanProjectFolder } from "@/fs/useLocalFileSystem";

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

interface LocalProjectState {
  /** All currently open local projects */
  projects: LocalProjectEntry[];
  /** True while initLocalProjects() is running */
  isInitialising: boolean;

  // ---- Actions ----

  /**
   * Open a new local project by picking a folder.
   * Caller must invoke pickDirectory() first and pass the handle.
   */
  addProject: (handle: FileSystemDirectoryHandle) => Promise<void>;

  /** Remove a local project (removes handle from IndexedDB too) */
  removeProject: (key: HandleKey) => Promise<void>;

  /** Re-scan a project folder and update its positions list */
  refreshProject: (key: HandleKey) => Promise<void>;

  /**
   * Request permission for a project whose permission has expired.
   * Must be called from a user gesture.
   */
  requestPermission: (key: HandleKey) => Promise<void>;

  /**
   * Restore all handles from IndexedDB on app startup.
   * Called once from App.tsx on mount.
   */
  initLocalProjects: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeKey(handle: FileSystemDirectoryHandle): HandleKey {
  return `local:${handle.name}`;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useLocalProjectStore = create<LocalProjectState>((set, get) => ({
  projects: [],
  isInitialising: false,

  // -------------------------------------------------------------------------
  addProject: async (handle) => {
    const key = makeKey(handle);

    // Avoid duplicates
    if (get().projects.find((p) => p.key === key)) {
      return;
    }

    // Scan folder for project.json + positions
    const { meta, positions } = await scanProjectFolder(handle);

    const entry: LocalProjectEntry = {
      key,
      handle,
      meta,
      positions,
      hasPermission: true,
    };

    // Persist handle in IndexedDB
    await saveHandle(key, handle);

    set((state) => ({ projects: [...state.projects, entry] }));
  },

  // -------------------------------------------------------------------------
  removeProject: async (key) => {
    await removeHandle(key);
    set((state) => ({
      projects: state.projects.filter((p) => p.key !== key),
    }));
  },

  // -------------------------------------------------------------------------
  refreshProject: async (key) => {
    const entry = get().projects.find((p) => p.key === key);
    if (!entry) return;

    const { meta, positions } = await scanProjectFolder(entry.handle);

    set((state) => ({
      projects: state.projects.map((p) =>
        p.key === key ? { ...p, meta, positions } : p
      ),
    }));
  },

  // -------------------------------------------------------------------------
  requestPermission: async (key) => {
    const entry = get().projects.find((p) => p.key === key);
    if (!entry) return;

    const result = await entry.handle.requestPermission({ mode: "readwrite" });
    const hasPermission = result === "granted";

    set((state) => ({
      projects: state.projects.map((p) =>
        p.key === key ? { ...p, hasPermission } : p
      ),
    }));

    // If permission granted, re-scan
    if (hasPermission) {
      await get().refreshProject(key);
    }
  },

  // -------------------------------------------------------------------------
  initLocalProjects: async () => {
    set({ isInitialising: true });
    try {
      const keys = await listHandleKeys();

      for (const key of keys) {
        const handle = await loadHandle(key);
        if (!handle) continue;

        const permission = await queryHandlePermission(handle);
        const hasPermission = permission === "granted";

        if (hasPermission) {
          // Full scan
          const { meta, positions } = await scanProjectFolder(handle);
          set((state) => ({
            projects: [
              ...state.projects,
              { key, handle, meta, positions, hasPermission: true },
            ],
          }));
        } else {
          // No permission yet – add with empty positions, show "Zugriff erlauben"
          set((state) => ({
            projects: [
              ...state.projects,
              {
                key,
                handle,
                meta: {
                  uuid: "",
                  name: handle.name,
                  created: "",
                  last_modified: "",
                  description: "",
                },
                positions: [],
                hasPermission: false,
              },
            ],
          }));
        }
      }
    } finally {
      set({ isInitialising: false });
    }
  },
}));
```

### Step 2: Call initLocalProjects() on app mount

Modify `web/frontend/src/App.tsx` – add a `useEffect` that calls `initLocalProjects` once:

```typescript
// Add to imports:
import { useEffect } from "react";
import { useLocalProjectStore } from "@/stores/useLocalProjectStore";

// Add inside App() function body, before return:
const initLocalProjects = useLocalProjectStore((s) => s.initLocalProjects);
useEffect(() => {
  initLocalProjects();
}, []); // eslint-disable-line react-hooks/exhaustive-deps
```

### Step 3: Verify build

```bash
cd web/frontend && npm run build 2>&1 | grep "error" | head -20
```

### Step 4: Commit

```bash
git add web/frontend/src/stores/useLocalProjectStore.ts web/frontend/src/App.tsx
git commit -m "feat: add useLocalProjectStore + init handles from IndexedDB on mount"
```

---

## Task 5: Extend useProjectStore – add currentProjectMode

**Files:**
- Modify: `web/frontend/src/stores/useProjectStore.ts`

The store needs to know whether the active position is on the server or on local disk so `useAutoSave` can route to the right save function.

Add these fields to the `ProjectState` interface and store:

```typescript
// Add to interface ProjectState:
/** Whether the active position lives on the server or on local disk */
currentProjectMode: "server" | "local";
/**
 * For local positions: the HandleKey of the LocalProjectEntry
 * (e.g. "local:Demo_Wohnhaus"). Null when mode is "server".
 */
currentLocalProjectKey: string | null;

// Add actions:
setProjectMode: (mode: "server" | "local", localKey?: string) => void;
```

Add to the initial state:
```typescript
currentProjectMode: "server",
currentLocalProjectKey: null,
```

Add the action implementation:
```typescript
setProjectMode: (mode, localKey) =>
  set({
    currentProjectMode: mode,
    currentLocalProjectKey: localKey ?? null,
  }),
```

Update `clearPosition` to also reset mode:
```typescript
clearPosition: () =>
  set({
    currentPositionPath: null,
    currentPositionName: null,
    isDirty: false,
    currentProjectMode: "server",
    currentLocalProjectKey: null,
  }),
```

### Verify build

```bash
cd web/frontend && npm run build 2>&1 | grep "error" | head -20
```

### Commit

```bash
git add web/frontend/src/stores/useProjectStore.ts
git commit -m "feat: add currentProjectMode + currentLocalProjectKey to useProjectStore"
```

---

## Task 6: useLocalProjectActions.ts – load and auto-save local positions

**Files:**
- Create: `web/frontend/src/hooks/useLocalProjectActions.ts`
- Modify: `web/frontend/src/hooks/useAutoSave.ts`

### Step 1: Create useLocalProjectActions.ts

```typescript
/**
 * useLocalProjectActions – load and save positions from/to local disk.
 *
 * Mirrors the API of useProjectActions but uses File System Access API
 * instead of HTTP calls.
 */

import { useCallback, useState } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import { useProjectStore } from "@/stores/useProjectStore";
import { useLocalProjectStore } from "@/stores/useLocalProjectStore";
import { readPositionFile, writePositionFile } from "@/fs/useLocalFileSystem";
import type { HandleKey } from "@/types/localProject";
import type { CalculationRequest } from "@/types/beam";

interface UseLocalProjectActionsResult {
  isLoading: boolean;
  error: string | null;
  loadLocalPosition: (key: HandleKey, relativePath: string) => Promise<void>;
  saveLocalPosition: () => Promise<void>;
  clearError: () => void;
}

export function useLocalProjectActions(): UseLocalProjectActionsResult {
  const loadFromRequest = useBeamStore((s) => s.loadFromRequest);
  const buildRequest = useBeamStore((s) => s.buildRequest);

  const { setCurrentPosition, setDirty, currentPositionPath, currentLocalProjectKey } =
    useProjectStore();
  const setProjectMode = useProjectStore((s) => s.setProjectMode);

  const projects = useLocalProjectStore((s) => s.projects);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // loadLocalPosition
  // -------------------------------------------------------------------------

  const loadLocalPosition = useCallback(
    async (key: HandleKey, relativePath: string) => {
      const project = projects.find((p) => p.key === key);
      if (!project) {
        setError(`Lokales Projekt nicht gefunden: ${key}`);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const position = await readPositionFile(project.handle, relativePath);

        const moduleData = position.modules[
          "durchlauftraeger"
        ] as CalculationRequest | undefined;

        if (moduleData) {
          loadFromRequest(moduleData);
        }

        const displayName = `${position.position_nummer} – ${position.position_name}`;
        setCurrentPosition(relativePath, displayName);
        setProjectMode("local", key);
      } catch (err) {
        const msg =
          err instanceof Error ? err.message : "Fehler beim Laden der Position";
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    [projects, loadFromRequest, setCurrentPosition, setProjectMode]
  );

  // -------------------------------------------------------------------------
  // saveLocalPosition
  // -------------------------------------------------------------------------

  const saveLocalPosition = useCallback(async () => {
    if (!currentLocalProjectKey || !currentPositionPath) {
      setError("Keine lokale Position zum Speichern ausgewählt");
      return;
    }

    const project = projects.find((p) => p.key === currentLocalProjectKey);
    if (!project) {
      setError(`Lokales Projekt nicht gefunden: ${currentLocalProjectKey}`);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const request = buildRequest();

      // Read existing file first to preserve position_nummer, position_name, etc.
      let existing: Record<string, unknown> = {};
      try {
        const pos = await readPositionFile(project.handle, currentPositionPath);
        existing = {
          position_nummer: pos.position_nummer,
          position_name: pos.position_name,
          created: pos.created,
          active_module: pos.active_module,
        };
      } catch {
        // File may not exist yet (new position) – ignore
      }

      await writePositionFile(project.handle, currentPositionPath, {
        ...existing,
        active_module: "durchlauftraeger",
        modules: { durchlauftraeger: request },
      });

      setDirty(false);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Fehler beim Speichern der Position";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [
    currentLocalProjectKey,
    currentPositionPath,
    projects,
    buildRequest,
    setDirty,
  ]);

  const clearError = useCallback(() => setError(null), []);

  return { isLoading, error, loadLocalPosition, saveLocalPosition, clearError };
}
```

### Step 2: Update useAutoSave.ts to route to local save

Replace the content of `web/frontend/src/hooks/useAutoSave.ts`:

```typescript
/**
 * useAutoSave – automatically saves the active position after a debounce
 * period whenever there are unsaved changes (isDirty = true).
 *
 * Routes to the correct save function:
 *  - mode = 'server' → savePosition() via API
 *  - mode = 'local'  → saveLocalPosition() via File System Access API
 *
 * Design:
 *  - Watches isDirty + currentPositionPath + currentProjectMode
 *  - When conditions are met, waits AUTO_SAVE_DELAY_MS then saves
 *  - Uses a ref for save functions to avoid stale closure issues
 *  - Only saves when a position is actually loaded
 */

import { useRef, useEffect } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import { useProjectActions } from "@/hooks/useProjectActions";
import { useLocalProjectActions } from "@/hooks/useLocalProjectActions";

/** Debounce delay before auto-save fires after the last change [ms] */
const AUTO_SAVE_DELAY_MS = 2000;

export function useAutoSave() {
  const isDirty = useProjectStore((s) => s.isDirty);
  const currentPositionPath = useProjectStore((s) => s.currentPositionPath);
  const currentProjectMode = useProjectStore((s) => s.currentProjectMode);

  const { savePosition } = useProjectActions();
  const { saveLocalPosition } = useLocalProjectActions();

  // Stable refs so the effect's cleanup can always call the latest save fn
  const saveServerRef = useRef(savePosition);
  saveServerRef.current = savePosition;

  const saveLocalRef = useRef(saveLocalPosition);
  saveLocalRef.current = saveLocalPosition;

  const modeRef = useRef(currentProjectMode);
  modeRef.current = currentProjectMode;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Nothing to save: no position open, or no changes
    if (!isDirty || !currentPositionPath) return;

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      if (modeRef.current === "local") {
        saveLocalRef.current();
      } else {
        saveServerRef.current();
      }
    }, AUTO_SAVE_DELAY_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isDirty, currentPositionPath, currentProjectMode]);
}
```

### Step 3: Verify build

```bash
cd web/frontend && npm run build 2>&1 | grep "error" | head -20
```

### Step 4: Commit

```bash
git add web/frontend/src/hooks/useLocalProjectActions.ts web/frontend/src/hooks/useAutoSave.ts
git commit -m "feat: local position load/save + route auto-save to disk for local positions"
```

---

## Task 7: ProjectExplorer – add Server/Lokal tabs

**Files:**
- Modify: `web/frontend/src/components/sidebar/ProjectExplorer.tsx`

This is the largest UI task. Add a tab bar at the top of the explorer with "Server" and "Lokal" tabs. The Server tab shows the existing content unchanged. The Lokal tab shows open local projects.

### Step 1: Add tab state + tab bar to ProjectExplorer

At the top of the `ProjectExplorer` component, add:

```typescript
const [activeTab, setActiveTab] = useState<"server" | "local">("server");
```

Replace the outer JSX wrapper with a structure that includes the tab bar. Add these imports:

```typescript
import { useState } from "react";
import { useLocalProjectStore } from "@/stores/useLocalProjectStore";
import { useLocalProjectActions } from "@/hooks/useLocalProjectActions";
import { pickDirectory } from "@/fs/useLocalFileSystem";
import { isFileSystemAccessSupported } from "@/fs/useLocalFileSystem";
import type { LocalProjectEntry } from "@/types/localProject";
```

### Step 2: Add the tab bar JSX

Insert at the top of the returned JSX (before the existing project list):

```tsx
{/* Tab bar */}
<div className="flex border-b border-[var(--border)] mb-2 shrink-0">
  <button
    onClick={() => setActiveTab("server")}
    className={`flex-1 py-1.5 text-xs font-medium transition-colors ${
      activeTab === "server"
        ? "border-b-2 border-[var(--primary)] text-[var(--primary)]"
        : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
    }`}
  >
    Server
  </button>
  <button
    onClick={() => setActiveTab("local")}
    className={`flex-1 py-1.5 text-xs font-medium transition-colors ${
      activeTab === "local"
        ? "border-b-2 border-[var(--primary)] text-[var(--primary)]"
        : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
    }`}
  >
    Lokal
  </button>
</div>

{/* Tab content */}
{activeTab === "server" && (
  <> {/* existing server content */} </>
)}
{activeTab === "local" && (
  <LocalTab />
)}
```

### Step 3: Add LocalTab sub-component

Add this component inside `ProjectExplorer.tsx` (before the main export):

```tsx
function LocalTab() {
  const projects = useLocalProjectStore((s) => s.projects);
  const addProject = useLocalProjectStore((s) => s.addProject);
  const removeProject = useLocalProjectStore((s) => s.removeProject);
  const requestPermission = useLocalProjectStore((s) => s.requestPermission);
  const { loadLocalPosition } = useLocalProjectActions();

  const [openFolderError, setOpenFolderError] = useState<string | null>(null);

  const handleOpenFolder = async () => {
    setOpenFolderError(null);
    try {
      const handle = await pickDirectory();
      await addProject(handle);
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        setOpenFolderError(err.message);
      }
      // AbortError = user cancelled picker → ignore
    }
  };

  if (!isFileSystemAccessSupported()) {
    return (
      <div className="p-3 text-xs text-[var(--muted-foreground)]">
        Lokale Projekte werden in Chrome, Edge und Firefox 111+ unterstützt.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Open folder button */}
      <button
        onClick={handleOpenFolder}
        className="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)] px-2 py-1 rounded hover:bg-[var(--accent)] transition-colors"
      >
        <span>＋</span> Ordner öffnen
      </button>

      {openFolderError && (
        <p className="text-xs text-red-500 px-2">{openFolderError}</p>
      )}

      {/* Local project list */}
      {projects.length === 0 && (
        <p className="text-xs text-[var(--muted-foreground)] px-2 py-4 text-center">
          Noch kein lokaler Ordner geöffnet.
        </p>
      )}

      {projects.map((project) => (
        <LocalProjectItem
          key={project.key}
          project={project}
          onLoadPosition={loadLocalPosition}
          onRequestPermission={() => requestPermission(project.key)}
          onRemove={() => removeProject(project.key)}
        />
      ))}
    </div>
  );
}

interface LocalProjectItemProps {
  project: LocalProjectEntry;
  onLoadPosition: (key: string, relativePath: string) => Promise<void>;
  onRequestPermission: () => Promise<void>;
  onRemove: () => void;
}

function LocalProjectItem({
  project,
  onLoadPosition,
  onRequestPermission,
  onRemove,
}: LocalProjectItemProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="text-xs">
      {/* Project header */}
      <div className="flex items-center gap-1 px-2 py-1 rounded hover:bg-[var(--accent)] group">
        <button
          className="flex-1 flex items-center gap-1 text-left font-medium text-[var(--foreground)]"
          onClick={() => setIsExpanded((v) => !v)}
        >
          <span>{isExpanded ? "▾" : "▸"}</span>
          <span>📂</span>
          <span className="truncate">{project.meta.name || project.handle.name}</span>
        </button>
        <button
          onClick={onRemove}
          className="opacity-0 group-hover:opacity-100 text-[var(--muted-foreground)] hover:text-red-500 transition-opacity px-1"
          title="Aus Liste entfernen"
        >
          ✕
        </button>
      </div>

      {/* Permission warning */}
      {!project.hasPermission && (
        <div className="mx-2 my-1 p-2 rounded bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
          <p className="text-amber-700 dark:text-amber-400 mb-1">
            ⚠️ Zugriff nötig
          </p>
          <button
            onClick={onRequestPermission}
            className="text-xs underline text-amber-600 dark:text-amber-400 hover:text-amber-800"
          >
            Ordner wieder erlauben
          </button>
        </div>
      )}

      {/* Positions list */}
      {isExpanded && project.hasPermission && (
        <div className="ml-4 space-y-0.5">
          {project.positions.length === 0 && (
            <p className="text-[var(--muted-foreground)] px-2 py-1 italic">
              Keine Positionen gefunden
            </p>
          )}
          {project.positions.map((pos) => (
            <button
              key={pos.relative_path}
              className="w-full text-left px-2 py-0.5 rounded hover:bg-[var(--accent)] text-[var(--foreground)] truncate"
              onClick={() => onLoadPosition(project.key, pos.relative_path)}
            >
              📄 {pos.position_nummer} – {pos.position_name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Step 4: Wrap existing server content in the `activeTab === "server"` branch

The existing project list JSX (everything that was previously the full return) should now be conditionally rendered only when `activeTab === "server"`. The overall structure becomes:

```tsx
return (
  <div className="flex flex-col h-full overflow-hidden ...">
    {/* Tab bar */}
    ...

    {/* Server tab content */}
    {activeTab === "server" && (
      <div className="flex flex-col h-full overflow-hidden">
        {/* EXISTING server content here unchanged */}
      </div>
    )}

    {/* Local tab content */}
    {activeTab === "local" && (
      <div className="flex-1 overflow-y-auto p-2">
        <LocalTab />
      </div>
    )}
  </div>
);
```

### Step 5: Verify build + manual test

```bash
cd web/frontend && npm run build 2>&1 | grep "error" | head -20
```

Manual test:
1. Open app in Chrome
2. Click "Lokal" tab
3. Click "Ordner öffnen"
4. Select a folder containing a valid project structure
5. Verify positions appear
6. Click a position → form loads
7. Edit something → wait 2s → verify the JSON file on disk is updated

### Step 6: Commit

```bash
git add web/frontend/src/components/sidebar/ProjectExplorer.tsx
git commit -m "feat: add Server/Lokal tabs to ProjectExplorer with local project browser"
```

---

## Task 8: Create + Rename + Delete local positions

**Files:**
- Modify: `web/frontend/src/hooks/useLocalProjectActions.ts`
- Modify: `web/frontend/src/components/sidebar/ProjectExplorer.tsx` (LocalProjectItem)

### Step 1: Add createLocalPosition to useLocalProjectActions

Add to the hook return type and implementation:

```typescript
createLocalPosition: (
  key: HandleKey,
  options: { position_nummer: string; position_name: string; subfolder?: string }
) => Promise<void>;
```

Implementation:

```typescript
const createLocalPosition = useCallback(
  async (key: HandleKey, options: { position_nummer: string; position_name: string; subfolder?: string }) => {
    const project = projects.find((p) => p.key === key);
    if (!project) return;

    setIsLoading(true);
    setError(null);
    try {
      // Build filename from nummer + name (safe chars only)
      const safeName = `${options.position_nummer}_${options.position_name}`
        .replace(/[^a-zA-Z0-9._\- ]/g, "_")
        .replace(/ /g, "_");
      const fileName = `Position_${safeName}.json`;
      const relativePath = options.subfolder
        ? `${options.subfolder}/${fileName}`
        : fileName;

      const request = buildRequest();
      await writePositionFile(project.handle, relativePath, {
        position_nummer: options.position_nummer,
        position_name: options.position_name,
        created: new Date().toISOString(),
        active_module: "durchlauftraeger",
        modules: { durchlauftraeger: request },
      });

      const displayName = `${options.position_nummer} – ${options.position_name}`;
      setCurrentPosition(relativePath, displayName);
      setProjectMode("local", key);

      // Refresh project positions list
      await refreshProject(key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Erstellen");
    } finally {
      setIsLoading(false);
    }
  },
  [projects, buildRequest, setCurrentPosition, setProjectMode]
);
```

### Step 2: Add deleteLocalPosition

```typescript
deleteLocalPosition: (key: HandleKey, relativePath: string) => Promise<void>;
```

```typescript
const deleteLocalPosition = useCallback(
  async (key: HandleKey, relativePath: string) => {
    const project = projects.find((p) => p.key === key);
    if (!project) return;

    setIsLoading(true);
    setError(null);
    try {
      await deletePositionFile(project.handle, relativePath);

      if (currentPositionPath === relativePath) {
        clearPosition();
      }

      await refreshProject(key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Löschen");
    } finally {
      setIsLoading(false);
    }
  },
  [projects, currentPositionPath, clearPosition]
);
```

### Step 3: Wire up create/delete buttons in LocalProjectItem

Add a "＋ Neue Position" button and a delete button per position to `LocalProjectItem`. Use the same dialog pattern as the server explorer (context menu or inline button).

### Step 4: Verify build + manual test

```bash
cd web/frontend && npm run build 2>&1 | grep "error" | head -20
```

Manual test: create a new position in a local project, verify JSON file appears on disk.

### Step 5: Commit

```bash
git add web/frontend/src/hooks/useLocalProjectActions.ts web/frontend/src/components/sidebar/ProjectExplorer.tsx
git commit -m "feat: create + delete local positions via File System Access API"
```

---

## Task 9: Sync – Local → Server

**Files:**
- Modify: `web/frontend/src/hooks/useLocalProjectActions.ts`
- Modify: `web/frontend/src/components/sidebar/ProjectExplorer.tsx`

### Step 1: Add uploadToServer to useLocalProjectActions

```typescript
uploadToServer: (
  key: HandleKey,
  options: { projectName: string; visibility: "private" | "shared" }
) => Promise<void>;
```

```typescript
const uploadToServer = useCallback(
  async (key, options) => {
    const project = projects.find((p) => p.key === key);
    if (!project) return;

    setIsLoading(true);
    setError(null);
    try {
      // 1. Create project on server
      const newProject = await api.post<{ uuid: string }>(
        "/api/projects",
        { name: options.projectName, description: project.meta.description }
      );

      // 2. Upload all positions
      for (const pos of project.positions) {
        const fullPos = await readPositionFile(project.handle, pos.relative_path);
        await api.put(
          `/api/projects/${newProject.uuid}/positions/${pos.relative_path}`,
          {
            position_nummer: fullPos.position_nummer,
            position_name: fullPos.position_name,
            active_module: fullPos.active_module,
            modules: fullPos.modules,
          }
        );
      }

      // 3. Set visibility
      if (options.visibility !== "private") {
        await api.patch(`/api/projects/${newProject.uuid}/visibility`, {
          visibility: options.visibility,
        });
      }

      // Refresh server projects list
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Hochladen");
    } finally {
      setIsLoading(false);
    }
  },
  [projects, queryClient]
);
```

### Step 2: Add ☁↑ button to LocalProjectItem

Show an upload button that opens a small confirmation dialog (project name + visibility picker) before calling `uploadToServer`.

### Step 3: Verify build

```bash
cd web/frontend && npm run build 2>&1 | grep "error" | head -20
```

### Step 4: Commit

```bash
git add web/frontend/src/hooks/useLocalProjectActions.ts web/frontend/src/components/sidebar/ProjectExplorer.tsx
git commit -m "feat: sync local → server (upload all positions with visibility choice)"
```

---

## Task 10: Sync – Server → Local + Visibility backend

**Files:**
- Modify: `web/api/routes/projects.py`
- Modify: `backend/project/project_manager.py`
- Modify: `web/frontend/src/components/sidebar/ProjectExplorer.tsx`

### Step 1: Add visibility field to project.json (backend)

In `backend/project/project_manager.py`, in `create_project()`, add `"visibility": "private"` to the project_data dict:

```python
project_data = {
    "uuid": str(uuid.uuid4()),
    "name": project_name,
    "created": datetime.now().isoformat(),
    "last_modified": datetime.now().isoformat(),
    "description": description,
    "visibility": "private",   # ← add this line
    "positions": []
}
```

### Step 2: Add PATCH visibility endpoint

In `web/api/routes/projects.py`, add:

```python
class VisibilityRequest(BaseModel):
    visibility: str = Field(description="'private' or 'shared'")

@router.patch("/api/projects/{project_id}/visibility")
async def set_project_visibility(
    project_id: str,
    body: VisibilityRequest,
    pm: ProjectManagerDep,
):
    """Set the visibility of a project (private / shared)."""
    loop = asyncio.get_running_loop()

    def _update():
        project_path = _resolve_project_path(pm, project_id)
        project_file = project_path / "project.json"
        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["visibility"] = body.visibility
        data["last_modified"] = datetime.now().isoformat()
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data

    return await loop.run_in_executor(None, _update)
```

### Step 3: Add Download (Server → Local) to ProjectExplorer

In the server tab, add a ☁↓ button per project that:
1. Calls `showDirectoryPicker()` to pick a target folder
2. Reads all positions from server
3. Writes JSON files to the picked folder
4. Saves handle in IndexedDB
5. Adds to local projects store

Wire this into a `downloadToLocal` function using the existing API + `writePositionFile`.

### Step 4: Show visibility icon in server tab

For each server project in the Server tab, show:
- 🔒 if `visibility === "private"` (or field absent)
- 👥 if `visibility === "shared"`

Add a toggle in the project context menu (right-click or "…" button).

### Step 5: Verify full build

```bash
cd web/frontend && npm run build 2>&1 | grep "error" | head -20
```

Also verify backend starts:
```bash
cd web && python -m uvicorn api.main:app --port 8000 2>&1 | head -20
```

### Step 6: Commit

```bash
git add web/api/routes/projects.py backend/project/project_manager.py web/frontend/src/components/sidebar/ProjectExplorer.tsx
git commit -m "feat: visibility flag (private/shared) + sync server→local download"
```

---

## Task 11: Final integration + deploy

### Step 1: Full build check

```bash
cd web/frontend && npm run build
```

Expected: build succeeds with no errors.

### Step 2: Manual end-to-end test checklist

- [ ] Open Lokal tab → "Ordner öffnen" → pick a project folder → positions appear
- [ ] Click a local position → form loads correctly
- [ ] Edit something → wait 2s → verify JSON file on disk updated (open in editor)
- [ ] Reload page → "Lokal" tab → click "Zugriff wieder erlauben" → positions appear
- [ ] Create new local position → JSON file appears in folder
- [ ] Delete local position → JSON file removed from folder
- [ ] Upload local project to server (☁↑) → appears in Server tab
- [ ] Download server project to local (☁↓) → appears in Lokal tab
- [ ] Toggle visibility private/shared → icon updates
- [ ] Unsupported browser: navigate to app in Safari → Lokal tab shows warning message

### Step 3: Push and deploy

```bash
git push origin main
```

GitHub Actions deploys automatically. Monitor at:
https://github.com/Disskaette/Statikprogramm-EC/actions
