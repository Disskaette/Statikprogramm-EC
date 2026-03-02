/**
 * useAutoSave – automatically saves the active position after a debounce
 * period whenever there are unsaved changes (isDirty = true).
 *
 * Design:
 *  - Watches isDirty + currentPositionPath from the project store.
 *  - When both are set, waits AUTO_SAVE_DELAY_MS since the last change, then
 *    calls savePosition().
 *  - Uses a ref for the save function to avoid re-triggering the effect when
 *    the callback identity changes.
 *  - Only saves when a position is actually loaded (currentPositionPath set).
 *    No-ops silently when the user hasn't opened a position yet.
 */

import { useRef, useEffect } from "react";
import { useProjectStore } from "@/stores/useProjectStore";
import { useProjectActions } from "@/hooks/useProjectActions";

/** Debounce delay before auto-save fires after the last change [ms] */
const AUTO_SAVE_DELAY_MS = 2000;

export function useAutoSave() {
  const isDirty = useProjectStore((s) => s.isDirty);
  const currentPositionPath = useProjectStore((s) => s.currentPositionPath);
  const { savePosition } = useProjectActions();

  // Stable ref so the effect's cleanup can always call the latest save fn
  const saveRef = useRef(savePosition);
  saveRef.current = savePosition;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Nothing to save: no position open, or no changes
    if (!isDirty || !currentPositionPath) return;

    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      saveRef.current();
    }, AUTO_SAVE_DELAY_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isDirty, currentPositionPath]);
}
