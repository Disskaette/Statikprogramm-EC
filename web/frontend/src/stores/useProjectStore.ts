/**
 * Zustand store for project-level state.
 *
 * Tracks which project and position are currently open, and whether the
 * user has unsaved changes (isDirty). This is kept separate from
 * useBeamStore to avoid mixing calculation state with navigation state.
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

  // ---- Actions ----
  setCurrentProject: (projectId: string | null) => void;
  setCurrentPosition: (path: string | null, name: string | null) => void;
  setDirty: (dirty: boolean) => void;
  /** Reset position state (e.g. when the user clicks "New position") */
  clearPosition: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useProjectStore = create<ProjectState>((set) => ({
  currentProjectId: null,
  currentPositionPath: null,
  currentPositionName: null,
  isDirty: false,

  setCurrentProject: (projectId) =>
    set({ currentProjectId: projectId }),

  setCurrentPosition: (path, name) =>
    set({ currentPositionPath: path, currentPositionName: name, isDirty: false }),

  setDirty: (dirty) => set({ isDirty: dirty }),

  clearPosition: () =>
    set({ currentPositionPath: null, currentPositionName: null, isDirty: false }),
}));
