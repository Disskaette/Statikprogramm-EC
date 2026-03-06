# Design: Load Pattern Sketch (Belastungsskizze maßgebende Kombination)

**Date:** 2026-03-06
**Status:** Approved
**Author:** Developer Dave + Maximilian Stark

---

## Summary

Add a graphical load-pattern visualization inside the "Schnittkraftverläufe"
accordion in the results panel. The sketch shows the beam system (like the
existing BeamSystemSketch at the top) with distributed-load arrows drawn on
it, making it immediately clear which spans are loaded with which loads in
the governing combination. Appears in **both** calculation modes (EC and
quick). Intended also for future printout/documentation use.

Additionally fix a minor display bug: `SchnittgroessenSummary` is missing
the `=` sign between symbol and value (e.g. `V_Ed  6.1 kN` → `V_Ed = 6.1 kN`).

---

## Goals

- Show load-pattern SVG diagram in both EC and quick modes
- EC mode: separate layers for permanent (g, all spans) and variable (q/s/w,
  active spans only from `moment_muster`)
- Quick mode: single combined block across all spans
- Show governing combination label below the sketch (plain text or KaTeX)
- No backend changes required – all data already in API response
- Fix missing `=` in `SchnittgroessenSummary`

## Non-Goals

- Interactive span selection or editing
- Separate patterns for V and δ (moment pattern shown, most relevant for EC5)
- Quantitative arrow scaling (qualitative representation only)
- Safari-only quirks (standard SVG, no special handling needed)

---

## New Position in ResultsPanel

Inside the "Schnittkraftverläufe" collapsible section, order becomes:

```
1. SchnittgroessenSummary   (existing – max values, with = fix)
2. LoadPatternSketch        (NEW – beam sketch with load arrows + combo label)
3. ForceCharts              (existing – Plotly force diagrams)
```

The `LoadPatternSketch` is always rendered when `results !== null`, not
conditional on EC mode.

---

## Data Sources (no backend changes)

### EC mode
| Data | Path in API response |
|------|----------------------|
| Load pattern (boolean[]) | `results.schnittgroessen.GZT.max.moment_muster` |
| Governing combo name | `results.schnittgroessen.GZT.max.moment_kombi` |
| Beam geometry | `useBeamStore` (spans, kragarm flags) |

`moment_muster` is indexed by **inner field** (feld_1 … feld_N). Cantilevers
are excluded from the pattern array (they always receive full permanent load).

### Quick mode
| Data | Path in API response |
|------|----------------------|
| All fields loaded (no pattern) | implicit: muster = all true |
| Governing combo LaTeX | `results.lastfallkombinationen` entry where `massgebend === true` |
| Ed value | same entry, `.Ed` field |
| Beam geometry | `useBeamStore` |

---

## SVG Structure

### ViewBox

`width = 800`, height varies by mode:
- EC mode: **SVG_H = 145**
- Quick mode: **SVG_H = 120**

### Y-coordinates (EC mode)

| Layer | y-range | Description |
|-------|---------|-------------|
| Variable load label | y = 8 | Small "q / s / w" text |
| Variable load bar | y = 16 | Horizontal line (only over active spans) |
| Variable load arrows | y = 16 → 36 | Short downward arrows |
| Permanent load label | y = 44 | Small "g" text |
| Permanent load bar | y = 52 | Horizontal line (all spans) |
| Permanent load arrows | y = 52 → 68 | Short downward arrows |
| Beam line | y = 72 | Thick horizontal line |
| Support triangles | y = 72 → 86 | Pinned supports |
| Field labels | y = 56 | Above beam (reuse existing positions) |
| Dimension line | y = 95 | Span lengths |
| Dimension text | y = 108 | e.g. "5.00 m" |

### Y-coordinates (Quick mode)

Same structure but only ONE load block (combined g+q) at:
| Layer | y-range |
|-------|---------|
| Load label | y = 8 |
| Load bar | y = 16 |
| Load arrows | y = 16 → 36 |
| Beam line | y = 52 |
| Support triangles | y = 52 → 66 |
| Field labels | y = 36 |
| Dimension line | y = 78 |
| Dimension text | y = 91 |

### Arrow Drawing

- **Spacing**: fixed ~50 SVG units between arrows (W = 800), centered in each
  active zone
- **Per arrow**: vertical line 12px long + small triangle arrowhead (4px base,
  5px height) pointing downward
- **Variable load arrows**: only drawn where `muster[fieldIndex] === true`
  (mapping: `muster[0]` → feld_1, `muster[1]` → feld_2, …; cantilevers always
  receive permanent load arrows but no variable-load arrows unless the pattern
  explicitly includes them – which the backend currently does not generate for
  cantilevers)
- **Quick mode arrows**: drawn across all spans uniformly

### Colors

| Element | Color |
|---------|-------|
| Variable load (q/s/w) | `var(--primary)` |
| Permanent load (g) | `var(--foreground)` at 55% opacity |
| Quick-mode combined | `var(--foreground)` at 80% opacity |
| Beam, supports, dims | Same as existing `BeamSystemSketch` |

---

## Combination Label (below SVG, HTML)

Rendered as a `<div>` beneath the `<svg>` element (not inside SVG so KaTeX
works normally):

- **EC mode**: plain text from `moment_kombi` (Unicode string, e.g.
  `"GZT: γ_G · G + 1,5 · S"`) – centered, small, muted color
- **Quick mode**: KaTeX-rendered LaTeX from governing `lastfallkombinationen`
  entry, plus `Ed = xx.xx kN/m` numeric value – same styling

---

## New Component

**File:** `web/frontend/src/components/results/LoadPatternSketch.tsx`

```typescript
interface Props {
  schnittgroessen: Record<string, unknown> | null | undefined;
  lastfallkombinationen: Record<string, unknown> | null | undefined;
  isEcMode: boolean;   // from useBeamStore(s => s.ecModus === "ec")
}
```

Reads beam geometry from `useBeamStore` (same as `BeamSystemSketch`).
Re-uses `beamGeometry.ts` utilities unchanged.

---

## Modified Files

| File | Change |
|------|--------|
| `components/results/LoadPatternSketch.tsx` | **New** component |
| `components/results/ResultsPanel.tsx` | Insert `<LoadPatternSketch>` between Summary and ForceCharts |
| `components/results/SchnittgroessenSummary.tsx` | Add `= ` between KaTeX symbol and numeric value in `StatItem` |

No changes to backend, routes, stores, or hooks.

---

## Bug Fix: SchnittgroessenSummary missing `=`

In `StatItem`, the current layout is:

```tsx
<KatexInline tex={tex} />
<span ...>{value}</span>
```

Fix: add a `=` between them:

```tsx
<KatexInline tex={tex} />
<span className="text-[var(--muted-foreground)]">=</span>
<span ...>{value}</span>
```
