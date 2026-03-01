/**
 * Zustand store for project-level state.
 *
 * Tracks which project and position are currently open, whether the
 * user has unsaved changes (isDirty), multi-selection state for bulk
 * operations, and drag-and-drop tracking state.
 *
 * Kept separate from useBeamStore to avoid mixing calculation state
 * with navigation / explorer state.
 */

import { create } from "zustand";

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

interface ProjectState {
  /** UUID of the project currently open in the explorer, or null if none */
  currentProjectId: string | null;
  /** Relative path of the position currently loaded into the form, or null */
  currentPositionPath: string | null;
  /** Display name for the current position (position_nummer + position_name) */
  currentPositionName: string | null;
  /**
   * True when the form has been changed since the position was last saved.
   * Managed externally – InputForm sets this to true on any user edit,
   * savePosition() resets it to false after a successful PUT.
   */
  isDirty: boolean;

  /**
   * Relative paths of positions currently selected in the explorer.
   * Stored as a plain array (not Set) so Zustand can serialize it correctly.
   */
  selectedPaths: string[];

  /** True while a drag operation originating from the explorer is in progress */
  isDragging: boolean;

  /** Relative paths of positions being dragged */
  dragPaths: string[];

  // ---- Actions ----
  setCurrentProject: (projectId: string | null) => void;
  setCurrentPosition: (path: string | null, name: string | null) => void;
  setDirty: (dirty: boolean) => void;
  /** Reset position state (e.g. when the user clicks "New position") */
  clearPosition: () => void;

  /**
   * Toggle or replace the multi-selection.
   * - multiSelect=true : toggle `path` in/out of selectedPaths
   * - multiSelect=false: replace selectedPaths with exactly [path]
   */
  toggleSelection: (path: string, multiSelect: boolean) => void;

  /** Clear the current multi-selection */
  clearSelection: () => void;

  /**
   * Start or stop a drag operation.
   * @param dragging - whether a drag is currently active
   * @param paths    - which positions are being dragged (ignored when dragging=false)
   */
  setDragging: (dragging: boolean, paths?: string[]) => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useProjectStore = create<ProjectState>((set, get) => ({
  currentProjectId: null,
  currentPositionPath: null,
  currentPositionName: null,
  isDirty: false,
  selectedPaths: [],
  isDragging: false,
  dragPaths: [],

  // ---- Basic project / position actions ----

  setCurrentProject: (projectId) =>
    set({ currentProjectId: projectId }),

  setCurrentPosition: (path, name) =>
    set({
      currentPositionPath: path,
      currentPositionName: name,
      isDirty: false,
    }),

  setDirty: (dirty) => set({ isDirty: dirty }),

  clearPosition: () =>
    set({
      currentPositionPath: null,
      currentPositionName: null,
      isDirty: false,
    }),

  // ---- Selection actions ----

  toggleSelection: (path, multiSelect) => {
    if (multiSelect) {
      const current = get().selectedPaths;
      const idx = current.indexOf(path);
      if (idx === -1) {
        // Add to selection
        set({ selectedPaths: [...current, path] });
      } else {
        // Remove from selection
        set({ selectedPaths: current.filter((p) => p !== path) });
      }
    } else {
      // Single-select: replace the whole selection
      set({ selectedPaths: [path] });
    }
  },

  clearSelection: () => set({ selectedPaths: [] }),

  // ---- Drag actions ----

  setDragging: (dragging, paths) =>
    set({
      isDragging: dragging,
      dragPaths: dragging ? (paths ?? get().dragPaths) : [],
    }),
}));
