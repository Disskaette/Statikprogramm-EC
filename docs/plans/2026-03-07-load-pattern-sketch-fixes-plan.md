# LoadPatternSketch Fixes + GZG Sketch – Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix variable-load layer bug (G-only config), add GZG deflection sketch in EC mode, fix `w_{max}` notation.

**Architecture:** Pure frontend changes in two TSX files. No backend changes. `LoadPatternSketch` reads `lasten` from `useBeamStore` to detect variable loads, renders two separate SVG blocks in EC mode (GZT + GZG), and conditionally hides the q/s/w layer. `SchnittgroessenSummary` gets notation fixed.

**Tech Stack:** React 19, TypeScript, Zustand (`useBeamStore`), inline SVG, KaTeX

---

## Context for the implementer

### Key files
- `web/frontend/src/components/results/LoadPatternSketch.tsx` – the main component to change
- `web/frontend/src/components/results/SchnittgroessenSummary.tsx` – notation fix only

### Backend data structure (EC mode)
`results.schnittgroessen` is shaped as:
```typescript
{
  GZT: {
    max: {
      moment:           number,        // [Nmm]
      querkraft:        number,        // [N]
      durchbiegung:     number,        // [mm]
      moment_kombi:     string,        // e.g. "GZT: γ_G · G + γ_Q · Q"
      querkraft_kombi:  string,
      durchbiegung_kombi: string,
      moment_muster:    boolean[],     // indexed by inner field (feld_1=0, feld_2=1, ...)
      querkraft_muster: boolean[],
      durchbiegung_muster: boolean[],
    },
    // ...envelope, massgebende_kombinationen, etc.
  },
  GZG: {
    // SAME structure as GZT in EC mode (NOT an array!)
    max: {
      durchbiegung:       number,
      durchbiegung_kombi: string,      // e.g. "GZG-Quasi: G + ψ₂·Q"
      durchbiegung_muster: boolean[],
      // ...
    }
  }
}
```

In **quick mode** `GZG` is an *array* of per-load objects – no `durchbiegung_muster` field exists there, so the GZG sketch must be skipped in quick mode.

### Variable load detection
```typescript
// A load is "variable" if its lastfall is not "g" (permanent).
// lastfall values: "g" (permanent), "q"/"p" (imposed), "s" (snow), "w" (wind)
const hasVariableLoad = lasten.some((l) => l.lastfall !== "g");
```

### SVG layout constants (current)
`EC_LAYOUT.SVG_H = 122` with variable load block (VAR_LABEL_Y=9, VAR_BAR_Y=15, VAR_ARROW_BOT=29, then PERM block at Y=38+).
When there is no variable load, the top block is removed → everything shifts up by ~29px:
- New PERM_LABEL_Y: 9 (was 38)
- New PERM_BAR_Y: 15 (was 44)
- New PERM_ARROW_BOT: 29 (was 58)
- New BEAM_Y: 35 (was 64)
- New SUPPORT_H: 12 (unchanged)
- New FIELD_LABEL_Y: 61 (was 90)
- New DIM_LINE_Y: 74 (was 103)
- New DIM_TEXT_Y: 85 (was 114)
- New SVG_H: 93 (was 122)

---

### Task 1: Fix notation in SchnittgroessenSummary

**Files:**
- Modify: `web/frontend/src/components/results/SchnittgroessenSummary.tsx` (line ~127)

**Step 1: Apply the change**

In `SchnittgroessenSummary.tsx`, find the `StatItem` for deflection (currently at the bottom of the `return` block) and change `tex` from `"\delta_{max}"` to `"w_{max}"`:

```tsx
// Before
<StatItem
  label="Durchbiegung (GZG)"
  tex="\delta_{max}"
  value={deflMm}
  unit="mm"
/>

// After
<StatItem
  label="Durchbiegung (GZG)"
  tex="w_{max}"
  value={deflMm}
  unit="mm"
/>
```

**Step 2: Verify in browser**

Open the app, trigger a calculation, open "Schnittkraftverläufe".
The deflection stat should now show `w_max = X.XX mm` (KaTeX renders `w_{max}` as w with subscript max).

**Step 3: Commit**
```bash
git add web/frontend/src/components/results/SchnittgroessenSummary.tsx
git commit -m "fix: use EC5-correct w_max notation for deflection in SchnittgroessenSummary"
```

---

### Task 2: Fix variable load layer (hasVariableLoad check)

**Files:**
- Modify: `web/frontend/src/components/results/LoadPatternSketch.tsx`

**Context:**
`SketchSvg` currently always renders a "q / s / w" arrow layer in EC mode.
When the user has only G loads, the backend stores `moment_muster = [True, False, ...]`
(the first belastungsmuster "wins" because all patterns give equal results for G-only loads).
This makes it look like field 1 has variable load when it doesn't.

**Step 1: Add `hasVariableLoad` prop to `SketchSvgProps` and `SketchSvg`**

In `SketchSvgProps` interface add:
```typescript
/** True when at least one variable load (Q/S/W) is configured in the beam store. */
hasVariableLoad: boolean;
```

In `SketchSvg` function signature:
```typescript
function SketchSvg({
  spans,
  kragarmLinks,
  kragarmRechts,
  isEcMode,
  muster,
  hasVariableLoad,   // ← add
}: SketchSvgProps) {
```

**Step 2: Add a reduced-height EC layout for G-only case**

After the existing `EC_LAYOUT` constant, add:
```typescript
// EC mode without variable loads: the top q/s/w block is omitted,
// everything shifts up by 29px (the height of the variable-load block).
const EC_LAYOUT_PERM_ONLY = {
  PERM_LABEL_Y: 9,
  PERM_BAR_Y: 15,
  PERM_ARROW_BOT: 15 + ARROW_SHAFT_LEN,   // = 29
  BEAM_Y: 35,
  SUPPORT_H: 12,
  FIELD_LABEL_Y: 61,
  DIM_LINE_Y: 74,
  DIM_TEXT_Y: 85,
  SVG_H: 93,
} as const;
```

**Step 3: Use the correct layout in `SketchSvg`**

Replace the existing layout-picking block at the top of `SketchSvg` body:
```typescript
// Pick layout constants
const ecLayout = (isEcMode && hasVariableLoad) ? EC_LAYOUT : EC_LAYOUT_PERM_ONLY;

const beamY       = isEcMode ? ecLayout.BEAM_Y           : QK_LAYOUT.BEAM_Y;
const supportH    = isEcMode ? ecLayout.SUPPORT_H        : QK_LAYOUT.SUPPORT_H;
const fieldLabelY = isEcMode ? ecLayout.FIELD_LABEL_Y    : QK_LAYOUT.FIELD_LABEL_Y;
const dimLineY    = isEcMode ? ecLayout.DIM_LINE_Y       : QK_LAYOUT.DIM_LINE_Y;
const dimTextY    = isEcMode ? ecLayout.DIM_TEXT_Y       : QK_LAYOUT.DIM_TEXT_Y;
const svgH        = isEcMode ? ecLayout.SVG_H            : QK_LAYOUT.SVG_H;
```

Also update the permanent-load layer to use `ecLayout`:
- Replace all `EC_LAYOUT.PERM_*` references inside the `{/* Permanent load layer */}` block with `ecLayout.PERM_*`.

**Step 4: Guard the variable load layer with `hasVariableLoad`**

Wrap the entire variable load block in EC mode with the guard:
```tsx
{isEcMode ? (
  <>
    {/* ── Variable load layer (q / s / w) – only when variable loads exist ── */}
    {hasVariableLoad && (
      <>
        <text
          x={4} y={EC_LAYOUT.VAR_LABEL_Y}
          fontSize={9} fill={primaryColor}
          fontFamily="system-ui, sans-serif"
        >
          q / s / w
        </text>
        {innerFields.map((r, idx) => {
          if (!muster[idx]) return null;
          const x0 = toX(r.x0);
          const x1 = toX(r.x1);
          return (
            <g key={`var-${idx}`}>
              <line
                x1={x0} y1={EC_LAYOUT.VAR_BAR_Y}
                x2={x1} y2={EC_LAYOUT.VAR_BAR_Y}
                stroke={primaryColor} strokeWidth={2}
              />
              {arrowPositions(x0, x1).map((cx, j) => (
                <Arrow
                  key={j} cx={cx}
                  barY={EC_LAYOUT.VAR_BAR_Y}
                  botY={EC_LAYOUT.VAR_ARROW_BOT}
                  color={primaryColor}
                />
              ))}
            </g>
          );
        })}
      </>
    )}

    {/* ── Permanent load layer (g) – all spans ── */}
    <text
      x={4} y={ecLayout.PERM_LABEL_Y}
      fontSize={9} fill={fgColor} opacity={0.6}
      fontFamily="system-ui, sans-serif"
    >
      g
    </text>
    {spanRanges.map((r, idx) => {
      const x0 = toX(r.x0);
      const x1 = toX(r.x1);
      return (
        <g key={`perm-${idx}`} opacity={0.6}>
          <line
            x1={x0} y1={ecLayout.PERM_BAR_Y}
            x2={x1} y2={ecLayout.PERM_BAR_Y}
            stroke={fgColor} strokeWidth={2}
          />
          {arrowPositions(x0, x1).map((cx, j) => (
            <Arrow
              key={j} cx={cx}
              barY={ecLayout.PERM_BAR_Y}
              botY={ecLayout.PERM_ARROW_BOT}
              color={fgColor}
            />
          ))}
        </g>
      );
    })}
  </>
) : (
  // ... quick mode unchanged ...
)}
```

**Step 5: Pass `hasVariableLoad` from `LoadPatternSketch` to `SketchSvg`**

In the exported `LoadPatternSketch` component, add:
```typescript
const lasten = useBeamStore((s) => s.lasten);
const hasVariableLoad = lasten.some((l) => l.lastfall !== "g");
```

And pass it to `SketchSvg`:
```tsx
<SketchSvg
  spans={spans}
  kragarmLinks={kragarmLinks}
  kragarmRechts={kragarmRechts}
  isEcMode={isEcMode}
  muster={muster}
  hasVariableLoad={hasVariableLoad}   // ← add
/>
```

**Step 6: Verify in browser**

Test A – G-only (default config, EC mode, 2 fields):
- Variable load arrows should be completely absent
- Only `g` block with arrows on all fields visible

Test B – G + Q (add Nutzlast, EC mode, 2 fields):
- `q / s / w` layer appears on the fields indicated by `moment_muster`
- `g` layer appears on all fields

**Step 7: Commit**
```bash
git add web/frontend/src/components/results/LoadPatternSketch.tsx
git commit -m "fix: hide variable load layer in EC mode when no Q/S/W loads are configured"
```

---

### Task 3: Add GZG sketch block in EC mode

**Files:**
- Modify: `web/frontend/src/components/results/LoadPatternSketch.tsx`

**Context:**
In EC mode, `schnittgroessen.GZG` is an object (not array!) with the same
shape as `GZT`. We extract `durchbiegung_muster` and `durchbiegung_kombi` and
render a second identical `SketchSvg` + `ComboLabel` block below the GZT block,
with a section header label above each block.

**Step 1: Update `Props` interface to accept `isEcMode`**

Currently `isEcMode` is derived inside `LoadPatternSketch`. We keep that.
No interface changes needed – `schnittgroessen` already contains both GZT and GZG.

**Step 2: Extract GZG data inside `LoadPatternSketch`**

After the existing GZT data extraction, add:
```typescript
// GZG deflection pattern (EC mode only – in quick mode GZG is an array, not an object)
const gzgObj = isEcMode
  ? ((schnittgroessen as Record<string, unknown> | undefined)
      ?.GZG as { max?: { durchbiegung_muster?: boolean[]; durchbiegung_kombi?: string } } | undefined)
  : undefined;
const deflMuster: boolean[]   = gzgObj?.max?.durchbiegung_muster ?? [];
const deflKombi:  string      = gzgObj?.max?.durchbiegung_kombi  ?? "";
```

**Step 3: Replace the single-block return with a two-block layout**

Replace the current `return` statement in `LoadPatternSketch`:

```tsx
// Before
return (
  <div className="space-y-1">
    <SketchSvg ... muster={muster} hasVariableLoad={hasVariableLoad} />
    <ComboLabel isEcMode={isEcMode} kombiName={kombiName} ... />
  </div>
);

// After
return (
  <div className="space-y-3">
    {/* ── GZT block: governing combination for M_Ed and V_Ed ── */}
    <div className="space-y-1">
      {isEcMode && (
        <p className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wide px-1">
          GZT – M<sub>Ed</sub>, V<sub>Ed</sub>
        </p>
      )}
      <SketchSvg
        spans={spans}
        kragarmLinks={kragarmLinks}
        kragarmRechts={kragarmRechts}
        isEcMode={isEcMode}
        muster={muster}
        hasVariableLoad={hasVariableLoad}
      />
      <ComboLabel
        isEcMode={isEcMode}
        kombiName={kombiName}
        kombiLatex={kombiLatex}
        kombiEd={kombiEd}
      />
    </div>

    {/* ── GZG block: governing combination for w_max (EC mode only) ── */}
    {isEcMode && (deflMuster.length > 0 || deflKombi) && (
      <div className="space-y-1">
        <p className="text-xs font-medium text-[var(--muted-foreground)] uppercase tracking-wide px-1">
          GZG – w<sub>max</sub>
        </p>
        <SketchSvg
          spans={spans}
          kragarmLinks={kragarmLinks}
          kragarmRechts={kragarmRechts}
          isEcMode={isEcMode}
          muster={deflMuster}
          hasVariableLoad={hasVariableLoad}
        />
        <ComboLabel
          isEcMode={isEcMode}
          kombiName={deflKombi}
          kombiLatex=""
          kombiEd={null}
        />
      </div>
    )}
  </div>
);
```

**Step 4: Verify in browser**

Test A – EC mode, G + Q, 2 fields:
- Two sketch blocks visible: "GZT – M_Ed, V_Ed" and "GZG – w_max"
- Each has its own variable load pattern and combo label
- GZT label: e.g. "GZT: γ_G · G + γ_Q · Q"
- GZG label: e.g. "GZG-Quasi: G + ψ₂ · Q"

Test B – EC mode, G-only, 2 fields:
- Both blocks visible but neither shows q/s/w arrows (hasVariableLoad = false)
- Combo names differ between GZT and GZG blocks

Test C – Quick mode:
- Only one block, no "GZT" / "GZG" header, unchanged behavior

**Step 5: Commit**
```bash
git add web/frontend/src/components/results/LoadPatternSketch.tsx
git commit -m "feat: show GZG deflection sketch alongside GZT in EC mode"
```

---

### Task 4: Push and deploy

```bash
git push origin main
```

Verify deploy at https://tools.askbenstark.com/statik/ with EC mode + multiple fields.
