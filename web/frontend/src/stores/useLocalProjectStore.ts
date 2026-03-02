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

  addProject: (handle: FileSystemDirectoryHandle) => Promise<void>;
  removeProject: (key: HandleKey) => Promise<void>;
  refreshProject: (key: HandleKey) => Promise<void>;
  requestPermission: (key: HandleKey) => Promise<void>;
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

  addProject: async (handle) => {
    const key = makeKey(handle);
    if (get().projects.find((p) => p.key === key)) return;

    const { meta, positions } = await scanProjectFolder(handle);
    const entry: LocalProjectEntry = { key, handle, meta, positions, hasPermission: true };
    await saveHandle(key, handle);
    set((state) => ({ projects: [...state.projects, entry] }));
  },

  removeProject: async (key) => {
    await removeHandle(key);
    set((state) => ({ projects: state.projects.filter((p) => p.key !== key) }));
  },

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
    if (hasPermission) await get().refreshProject(key);
  },

  initLocalProjects: async () => {
    set({ isInitialising: true });
    try {
      const storedKeys = await listHandleKeys();
      const entries: LocalProjectEntry[] = [];

      for (const key of storedKeys) {
        const handle = await loadHandle(key);
        if (!handle) continue;

        const permission = await queryHandlePermission(handle);
        const hasPermission = permission === "granted";

        if (hasPermission) {
          try {
            const { meta, positions } = await scanProjectFolder(handle);
            entries.push({ key, handle, meta, positions, hasPermission: true });
          } catch {
            // Handle became unreadable since last session – skip silently
          }
        } else {
          entries.push({
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
          });
        }
      }

      // Single set() call – one re-render for all restored projects
      set({ projects: entries });
    } finally {
      set({ isInitialising: false });
    }
  },
}));
