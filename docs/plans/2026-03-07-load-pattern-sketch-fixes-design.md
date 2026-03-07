# Design: LoadPatternSketch – Bug-fixes + GZG Sketch

**Date:** 2026-03-07
**Status:** Approved
**Author:** Developer Dave + Maximilian Stark

---

## Summary

Two fixes + one extension to the `LoadPatternSketch` component and
`SchnittgroessenSummary`:

1. **Bug-fix – variable load layer shown for G-only configuration:**
   When no variable loads (Q/S/W) are configured, the backend stores the
   *first* belastungsmuster `[True, False, ...]` as `moment_muster` (because
   all patterns give identical results for G-only loads). The frontend
   incorrectly renders variable load arrows in field 1. Fix: only show the
   q/s/w layer when at least one variable load exists in `useBeamStore.lasten`.

2. **Extension – GZG sketch for deflection (EC mode only):**
   A second `SketchSvg` block is shown below the GZT block, using
   `schnittgroessen.GZG.max.durchbiegung_muster` and
   `schnittgroessen.GZG.max.durchbiegung_kombi`. Labeled `"GZG – w_max"`.
   Quick mode remains unchanged (single sketch).

3. **Notation fix – `\delta_{max}` → `w_{max}` in SchnittgroessenSummary:**
   EC5 uses `w` for Durchbiegung (not `δ`). The KaTeX symbol and value label
   are updated to match Eurocode notation.

No backend changes. No store changes. No route changes.

---

## Goals

- q/s/w arrows only when variable loads are configured
- EC mode shows both GZT (M, V) and GZG (w) governing patterns
- EC5-correct notation: `w_{max}` instead of `\delta_{max}`
- Quick mode unchanged

## Non-Goals

- Any backend changes
- Fixing the 504 timeout for 4+ fields (infrastructure issue, separate)
- Interactive features in the sketch

---

## Data Sources

### GZT sketch (existing)
| Data | Path |
|------|------|
| Load pattern | `schnittgroessen.GZT.max.moment_muster` (boolean[]) |
| Combo label  | `schnittgroessen.GZT.max.moment_kombi` (string) |

### GZG sketch (new, EC mode only)
| Data | Path |
|------|------|
| Load pattern | `schnittgroessen.GZG.max.durchbiegung_muster` (boolean[]) |
| Combo label  | `schnittgroessen.GZG.max.durchbiegung_kombi` (string) |

Note: In EC mode `schnittgroessen.GZG` is an **object** (same structure as GZT).
In quick mode `schnittgroessen.GZG` is an **array** of per-load entries – no
`durchbiegung_muster` available there, so GZG sketch is skipped in quick mode.

### Variable load check
```typescript
const lasten = useBeamStore((s) => s.lasten);
const hasVariableLoad = lasten.some((l) => l.lastfall !== "g");
```

---

## Modified Files

| File | Change |
|------|--------|
| `web/frontend/src/components/results/LoadPatternSketch.tsx` | hasVariableLoad prop; second GZG sketch in EC mode |
| `web/frontend/src/components/results/SchnittgroessenSummary.tsx` | `\delta_{max}` → `w_{max}` |

---

## Visual Layout (EC mode, G + Q loads)

```
GZT – M_Ed, V_Ed
┌─────────────────────────────────────────┐
│ q/s/w  ██████░░░███████  (moment_muster)│
│ g      ████████████████████████████     │
│         △──────────────────────────△    │
│   Feld 1 (5.00 m)   Feld 2 (5.00 m)    │
└─────────────────────────────────────────┘
GZT: γ_G·G + 1,5·Q

GZG – w_max
┌─────────────────────────────────────────┐
│ q/s/w  ██████░░░███████  (defl. muster) │
│ g      ████████████████████████████     │
│         △──────────────────────────△    │
│   Feld 1 (5.00 m)   Feld 2 (5.00 m)    │
└─────────────────────────────────────────┘
GZG-Quasi: G + ψ₂·Q
```

## Visual Layout (EC mode, G-only)

```
GZT – M_Ed, V_Ed
┌─────────────────────────────────────────┐
│ g      ████████████████████████████     │  ← no q/s/w layer
│         △──────────────────────────△    │
└─────────────────────────────────────────┘
GZT: γ_G·G

GZG – w_max
┌─────────────────────────────────────────┐
│ g      ████████████████████████████     │
│         △──────────────────────────△    │
└─────────────────────────────────────────┘
GZG-Quasi: G
```

---

## SVG Height Adjustment

When `hasVariableLoad === false`, the EC layout no longer needs the top
variable-load block. Use a reduced height variant:

| Condition | SVG_H |
|-----------|-------|
| EC mode + variable loads | 122 (current) |
| EC mode + G-only         | 95 (variable block removed: ~27px saved) |
| Quick mode               | 100 (unchanged) |

The Y-coordinates of beam, supports, field labels and dimension lines shift
up by the height of the removed variable-load block (~29px) in the G-only case.
