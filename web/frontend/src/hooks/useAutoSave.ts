/**
 * useAutoSave – automatically saves the active position after a debounce
 * period whenever there are unsaved changes (isDirty = true).
 *
 * Routes to the correct save function based on currentProjectMode:
 *  - mode = 'server' → savePosition() via FastAPI
 *  - mode = 'local'  → saveLocalPosition() via File System Access API (silent, direct to disk)
 *
 * Auto-save is completely silent in both modes – no toast, no spinner.
 * Only the explicit Sync operations (Local→Server, Server→Local) show warnings.
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

  // Stable refs – avoid stale closures in the timeout callback
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
