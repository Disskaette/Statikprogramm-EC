# Auto-Calculate on App Start – Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fire the beam calculation automatically when the app first opens, so the results panel shows output immediately without requiring a user interaction.

**Architecture:** One line added inside the existing `isFirstRender` guard in `InputForm.tsx`. The guard already runs once on mount and then skips; adding `triggerCalculation()` there makes the first render trigger a calculation while still skipping `setDirty(true)` (so no false auto-save is initiated).

**Tech Stack:** React 19, Zustand, @tanstack/react-query, TypeScript

---

### Task 1: Add triggerCalculation() to the isFirstRender guard

**Files:**
- Modify: `web/frontend/src/components/input/InputForm.tsx` (lines 123–127)

**Context:**
`InputForm` has a `useEffect` that watches all form fields and calls
`triggerCalculation()` on every change. A `isFirstRender` ref prevents the
effect from firing on the very first render (mount). We want to fire the
calculation on mount, but still skip `setDirty(true)` so no false auto-save
is triggered.

Current code (lines 123–127):
```typescript
if (isFirstRender.current) {
  isFirstRender.current = false;
  return;
}
```

**Step 1: Apply the change**

Replace the `isFirstRender` block with:
```typescript
if (isFirstRender.current) {
  isFirstRender.current = false;
  triggerCalculation(); // fire once on mount with current store values
  return;
}
```

No other changes needed. The `triggerCalculation` ref is already stable
(stable function identity, empty deps in `useCalculation`), so adding it
here does not introduce any new effect dependency or infinite-loop risk.

**Step 2: Verify in browser – fresh app start**

1. Open the app at http://localhost:5173 (or the deployed URL)
2. Observe: after ~600 ms the results panel should show calculation output
   with the default values (1 field, 5 m, g = 7.41 kN/m, C24 120×240 mm)
   **without any user interaction**
3. The status bar at the bottom of the form should briefly show
   "Berechnung läuft..." then "✓ Ergebnis bereit"

**Step 3: Verify – position load still works**

1. Open a saved position from the project explorer
2. Results should appear automatically (this already worked before; verify
   it has not regressed)
3. The position should NOT be marked dirty immediately after loading
   (no unsaved-changes indicator in the explorer)

**Step 4: Commit**

```bash
git add web/frontend/src/components/input/InputForm.tsx
git commit -m "feat: auto-calculate on app start – fire triggerCalculation on mount"
```
