# Design: Auto-Calculate on App Start

**Date:** 2026-03-07
**Status:** Approved
**Author:** Developer Dave + Maximilian Stark

---

## Summary

When the app is opened, the calculation should fire automatically with the
current store values (defaults on fresh start, loaded data when a position
was already in the store). Currently, a `isFirstRender` guard in `InputForm`
explicitly skips the very first `useEffect` run to avoid triggering a
calculation before the user has done anything. This guard is removed in
the sense that `triggerCalculation()` is now called inside it — but
`setDirty(true)` is still skipped, so no unwanted auto-save is triggered.

Position loading already works: when `loadFromRequest` changes the store,
the `useEffect` re-fires (because JSON-serialised deps change) and calls
`triggerCalculation()`. No change needed for that path.

---

## Goals

- On fresh app start: auto-calculate with default values immediately
- On position load: already works, no change needed
- Do NOT mark the form as dirty on mount (no false auto-save)

## Non-Goals

- Changing calculation logic or debounce timing
- Any backend changes
- Any store changes

---

## Changed File

| File | Change |
|------|--------|
| `web/frontend/src/components/input/InputForm.tsx` | Add `triggerCalculation()` inside `isFirstRender` block |

---

## Code Change

```typescript
// Before
if (isFirstRender.current) {
  isFirstRender.current = false;
  return;
}

// After
if (isFirstRender.current) {
  isFirstRender.current = false;
  triggerCalculation(); // fire once on mount with current store values
  return;
}
```

The rest of the `useEffect` (including `setDirty(true)`) remains unchanged
and only runs on subsequent changes.
