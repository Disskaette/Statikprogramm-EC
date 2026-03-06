# Load Pattern Sketch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Add a governing-load-combination SVG sketch (with distributed-load arrows) between the max-value summary and the force diagrams in the "Schnittkraftverläufe" section, plus fix a missing `=` sign in the summary.

**Architecture:** Three independent tasks: (1) one-line bug-fix in `SchnittgroessenSummary`, (2) new `LoadPatternSketch.tsx` component that reads beam geometry from the Zustand store and load-pattern data from `schnittgroessen`/`lastfallkombinationen` props, (3) insertion of the new component into `ResultsPanel.tsx`. No backend changes. No new dependencies.

**Tech Stack:** React 19, TypeScript, SVG (no library), KaTeX (already installed), Zustand, Tailwind CSS (CSS vars only)

---

## Context for the implementer

### Key files to read before starting
- `web/frontend/src/components/results/SchnittgroessenSummary.tsx` – Task 1 target
- `web/frontend/src/components/results/BeamSystemSketch.tsx` – SVG patterns to follow
- `web/frontend/src/components/results/beamGeometry.ts` – re-use as-is
- `web/frontend/src/components/results/ResultsPanel.tsx` – Task 3 target (insertion point)
- `web/frontend/src/types/beam.ts` – CalculationResult type

### Backend data available in `results.schnittgroessen`

**EC mode** (when `ecModus === "ec"`):
```
results.schnittgroessen.GZT.max.moment_muster  → boolean[]
    Index 0 = feld_1, index 1 = feld_2, … (INNER fields only, cantilevers excluded)
    true  = this inner field carries the governing variable load
    false = this field carries only permanent load

results.schnittgroessen.GZT.max.moment_kombi   → string (plain Unicode)
    e.g. "GZT: γ_G · G + 1,5 · S"
```

**Quick mode** (when `ecModus === "schnell"`):
```
results.lastfallkombinationen  → Record<string, Kombination>
    The entry where .massgebend === true is the governing combo.
    .latex  → LaTeX string wrapped in $…$
    .Ed     → numeric design load [kN/m]
    .wert   → fallback if Ed is absent
```

### What the SVG should look like

**EC mode (two load layers):**
```
  q/s/w  ↓↓↓  (active spans)       ↓↓↓  (active spans)
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  g      ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ← beam
             △       △       △
          Feld 1  Feld 2  Feld 3
          |←5.00m→||←4.00m→|

  [Kombi-Label unter dem SVG]
```

**Quick mode (single combined layer):**
```
  g+q    ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓
         ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ← beam
             △       △       △
          Feld 1  Feld 2  Feld 3

  [KaTeX formula + Ed = xx.xx kN/m]
```

---

## Task 1: Fix missing `=` in SchnittgroessenSummary

**Files:**
- Modify: `web/frontend/src/components/results/SchnittgroessenSummary.tsx:47-59`

### Step 1: Make the edit

In `StatItem`, find the `<div className="flex items-baseline gap-1">` block and add `=` between the KaTeX symbol and the numeric value:

```tsx
// BEFORE (lines 51-58):
<div className="flex items-baseline gap-1">
  <KatexInline tex={tex} />
  <span className="text-base font-mono font-semibold tabular-nums">
    {value}
  </span>
  <span className="text-xs text-[var(--muted-foreground)]">{unit}</span>
</div>

// AFTER:
<div className="flex items-baseline gap-1">
  <KatexInline tex={tex} />
  <span className="text-sm text-[var(--muted-foreground)]">=</span>
  <span className="text-base font-mono font-semibold tabular-nums">
    {value}
  </span>
  <span className="text-xs text-[var(--muted-foreground)]">{unit}</span>
</div>
```

### Step 2: Verify build

```bash
cd web/frontend && npm run build 2>&1 | grep -E "error|✓"
```
Expected: `✓ built in ...s` (no errors)

### Step 3: Commit

```bash
git add web/frontend/src/components/results/SchnittgroessenSummary.tsx
git commit -m "fix: add missing = sign between symbol and value in SchnittgroessenSummary"
```

---

## Task 2: Create LoadPatternSketch.tsx

**Files:**
- Create: `web/frontend/src/components/results/LoadPatternSketch.tsx`

### Step 1: Create the file with this exact content

```tsx
/**
 * LoadPatternSketch – SVG sketch of the governing load combination.
 *
 * Shown between SchnittgroessenSummary and ForceCharts inside the
 * "Schnittkraftverläufe" collapsible section.
 *
 * EC mode:    two layers – permanent load (g, all spans) and variable load
 *             (q/s/w, only spans where moment_muster[i] === true)
 * Quick mode: single combined block (g+q) across all spans
 *
 * Combo label rendered below the SVG as plain HTML (KaTeX for quick mode,
 * plain text for EC mode).
 *
 * Data sources (no backend changes needed):
 *   EC mode:    results.schnittgroessen.GZT.max.moment_muster  (boolean[])
 *               results.schnittgroessen.GZT.max.moment_kombi   (string)
 *   Quick mode: results.lastfallkombinationen entry where massgebend===true
 */

import { useMemo } from "react";
import katex from "katex";
import { useBeamStore } from "@/stores/useBeamStore";
import {
  buildSpanEntries,
  totalLength,
  supportPositions,
  type SpanEntry,
} from "./beamGeometry";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  schnittgroessen?: Record<string, unknown> | null;
  lastfallkombinationen?: Record<string, unknown> | null;
}

interface KombinationEntry {
  latex?: string;
  Ed?: number;
  wert?: number;
  massgebend?: boolean;
}

// ---------------------------------------------------------------------------
// SVG layout constants
// ---------------------------------------------------------------------------

const W = 800;
const ARROW_SPACING = 50; // px between arrows (viewBox units)
const ARROW_SHAFT_LEN = 14;
const ARROWHEAD_HALF_W = 5;
const ARROWHEAD_H = 5;

// EC mode: two load layers
const EC_LAYOUT = {
  VAR_LABEL_Y: 9,
  VAR_BAR_Y: 15,
  VAR_ARROW_BOT: 15 + ARROW_SHAFT_LEN,   // = 29
  PERM_LABEL_Y: 38,
  PERM_BAR_Y: 44,
  PERM_ARROW_BOT: 44 + ARROW_SHAFT_LEN,  // = 58
  BEAM_Y: 64,
  SUPPORT_H: 12,
  FIELD_LABEL_Y: 90,
  DIM_LINE_Y: 103,
  DIM_TEXT_Y: 114,
  SVG_H: 122,
} as const;

// Quick mode: single combined load layer
const QK_LAYOUT = {
  LOAD_LABEL_Y: 9,
  LOAD_BAR_Y: 15,
  LOAD_ARROW_BOT: 15 + ARROW_SHAFT_LEN,  // = 29
  BEAM_Y: 42,
  SUPPORT_H: 12,
  FIELD_LABEL_Y: 68,
  DIM_LINE_Y: 81,
  DIM_TEXT_Y: 92,
  SVG_H: 100,
} as const;

// ---------------------------------------------------------------------------
// CSS variable helper
// ---------------------------------------------------------------------------

function cssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ---------------------------------------------------------------------------
// Arrow x-positions: evenly spaced across [x0px, x1px]
// ---------------------------------------------------------------------------

function arrowPositions(x0px: number, x1px: number): number[] {
  const width = x1px - x0px;
  if (width <= 0) return [];
  const count = Math.max(1, Math.round(width / ARROW_SPACING));
  const gap = width / count;
  const result: number[] = [];
  for (let i = 0; i < count; i++) {
    result.push(x0px + gap * (i + 0.5));
  }
  return result;
}

// ---------------------------------------------------------------------------
// Single downward arrow
// ---------------------------------------------------------------------------

function Arrow({
  cx,
  barY,
  botY,
  color,
}: {
  cx: number;
  barY: number;
  botY: number;
  color: string;
}) {
  const headTopY = botY - ARROWHEAD_H;
  return (
    <g>
      <line
        x1={cx} y1={barY}
        x2={cx} y2={headTopY}
        stroke={color}
        strokeWidth={1.5}
      />
      <polygon
        points={`${cx},${botY} ${cx - ARROWHEAD_HALF_W},${headTopY} ${cx + ARROWHEAD_HALF_W},${headTopY}`}
        fill={color}
      />
    </g>
  );
}

// ---------------------------------------------------------------------------
// Inner SVG component
// ---------------------------------------------------------------------------

interface SketchSvgProps {
  spans: SpanEntry[];
  kragarmLinks: boolean;
  kragarmRechts: boolean;
  isEcMode: boolean;
  /** Boolean array indexed by inner field index (feld_1=0, feld_2=1, …).
   *  EC mode only. Cantilevers are not included in this array. */
  muster: boolean[];
}

function SketchSvg({
  spans,
  kragarmLinks,
  kragarmRechts,
  isEcMode,
  muster,
}: SketchSvgProps) {
  const total = totalLength(spans);
  if (total <= 0 || spans.length === 0) return null;

  const toX = (xM: number) => (xM / total) * W;
  const supports = supportPositions(spans, kragarmLinks, kragarmRechts);

  // Pick layout constants
  const beamY        = isEcMode ? EC_LAYOUT.BEAM_Y        : QK_LAYOUT.BEAM_Y;
  const supportH     = isEcMode ? EC_LAYOUT.SUPPORT_H     : QK_LAYOUT.SUPPORT_H;
  const fieldLabelY  = isEcMode ? EC_LAYOUT.FIELD_LABEL_Y : QK_LAYOUT.FIELD_LABEL_Y;
  const dimLineY     = isEcMode ? EC_LAYOUT.DIM_LINE_Y    : QK_LAYOUT.DIM_LINE_Y;
  const dimTextY     = isEcMode ? EC_LAYOUT.DIM_TEXT_Y    : QK_LAYOUT.DIM_TEXT_Y;
  const svgH         = isEcMode ? EC_LAYOUT.SVG_H         : QK_LAYOUT.SVG_H;

  // Colors
  const fgColor      = cssVar("--foreground")       || "#0a0a0a";
  const primaryColor = cssVar("--primary")           || "#6366f1";
  const mutedColor   = cssVar("--muted-foreground")  || "#737373";
  const borderColor  = cssVar("--border")            || "#e5e7eb";
  // Permanent load: foreground at ~55 % opacity via hex alpha
  const permColor    = `${fgColor}8C`; // 8C hex ≈ 55 %

  // Build per-span x-ranges in metres
  let xAccum = 0;
  const spanRanges = spans.map((s) => {
    const x0 = xAccum;
    const x1 = xAccum + s.length;
    xAccum = x1;
    return { x0, x1, span: s };
  });

  // Inner-field spans (not cantilevers) in order
  const innerFields = spanRanges.filter((r) => !r.span.isCantilever);

  // Support triangle path
  function trianglePath(cx: number): string {
    const x = toX(cx);
    const half = supportH * 0.7;
    return `M ${x} ${beamY} L ${x - half} ${beamY + supportH} L ${x + half} ${beamY + supportH} Z`;
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${svgH}`}
      className="w-full"
      style={{ maxHeight: svgH, overflow: "visible" }}
      aria-label="Belastungsskizze maßgebende Kombination"
      role="img"
    >
      {isEcMode ? (
        <>
          {/* ── Variable load layer (q / s / w) ─────────────────────────── */}
          <text
            x={4} y={EC_LAYOUT.VAR_LABEL_Y}
            fontSize={9} fill={primaryColor}
            fontFamily="system-ui, sans-serif"
          >
            q / s / w
          </text>
          {innerFields.map((r, idx) => {
            // Only draw where muster[idx] === true
            // If muster is shorter than innerFields (safety), treat as false
            if (!muster[idx]) return null;
            const x0 = toX(r.x0);
            const x1 = toX(r.x1);
            return (
              <g key={`var-${idx}`}>
                {/* Top bar */}
                <line
                  x1={x0} y1={EC_LAYOUT.VAR_BAR_Y}
                  x2={x1} y2={EC_LAYOUT.VAR_BAR_Y}
                  stroke={primaryColor} strokeWidth={2}
                />
                {/* Arrows */}
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

          {/* ── Permanent load layer (g) – all spans ────────────────────── */}
          <text
            x={4} y={EC_LAYOUT.PERM_LABEL_Y}
            fontSize={9} fill={permColor}
            fontFamily="system-ui, sans-serif"
          >
            g
          </text>
          {spanRanges.map((r, idx) => {
            const x0 = toX(r.x0);
            const x1 = toX(r.x1);
            return (
              <g key={`perm-${idx}`}>
                <line
                  x1={x0} y1={EC_LAYOUT.PERM_BAR_Y}
                  x2={x1} y2={EC_LAYOUT.PERM_BAR_Y}
                  stroke={permColor} strokeWidth={2}
                />
                {arrowPositions(x0, x1).map((cx, j) => (
                  <Arrow
                    key={j} cx={cx}
                    barY={EC_LAYOUT.PERM_BAR_Y}
                    botY={EC_LAYOUT.PERM_ARROW_BOT}
                    color={permColor}
                  />
                ))}
              </g>
            );
          })}
        </>
      ) : (
        <>
          {/* ── Quick mode: combined g + q block – all spans ─────────────── */}
          <text
            x={4} y={QK_LAYOUT.LOAD_LABEL_Y}
            fontSize={9} fill={fgColor} opacity={0.8}
            fontFamily="system-ui, sans-serif"
          >
            g + q
          </text>
          {spanRanges.map((r, idx) => {
            const x0 = toX(r.x0);
            const x1 = toX(r.x1);
            return (
              <g key={`qk-${idx}`}>
                <line
                  x1={x0} y1={QK_LAYOUT.LOAD_BAR_Y}
                  x2={x1} y2={QK_LAYOUT.LOAD_BAR_Y}
                  stroke={fgColor} strokeWidth={2} opacity={0.8}
                />
                {arrowPositions(x0, x1).map((cx, j) => (
                  <Arrow
                    key={j} cx={cx}
                    barY={QK_LAYOUT.LOAD_BAR_Y}
                    botY={QK_LAYOUT.LOAD_ARROW_BOT}
                    color={`${fgColor}CC`} // 80 % opacity
                  />
                ))}
              </g>
            );
          })}
        </>
      )}

      {/* ── Beam line ─────────────────────────────────────────────────────── */}
      <line
        x1={toX(0)} y1={beamY}
        x2={toX(total)} y2={beamY}
        stroke={fgColor} strokeWidth={3}
      />

      {/* ── Support triangles + ground lines ─────────────────────────────── */}
      {supports.map((sx) => (
        <g key={`sup-${sx}`}>
          <path d={trianglePath(sx)} fill={fgColor} stroke="none" opacity={0.85} />
          <line
            x1={toX(sx) - supportH * 0.9}
            y1={beamY + supportH + 1}
            x2={toX(sx) + supportH * 0.9}
            y2={beamY + supportH + 1}
            stroke={borderColor} strokeWidth={1.5}
          />
        </g>
      ))}

      {/* ── Field labels + dimension lines ───────────────────────────────── */}
      {(() => {
        let xA = 0;
        return spans.map((s, i) => {
          const x0 = xA;
          const x1 = xA + s.length;
          xA = x1;
          const isInner = !s.isCantilever;
          const fieldIdx =
            spans.slice(0, i).filter((ss) => !ss.isCantilever).length + 1;
          const label = isInner ? `Feld ${fieldIdx}` : "Kragarm";
          const cx = toX((x0 + x1) / 2);
          const x0px = toX(x0);
          const x1px = toX(x1);
          return (
            <g key={`dim-${i}`}>
              <text
                x={cx} y={fieldLabelY}
                textAnchor="middle" fontSize={11}
                fill={mutedColor} fontFamily="system-ui, sans-serif"
              >
                {label}
              </text>
              {/* Dimension line */}
              <line
                x1={x0px + 4} y1={dimLineY - 8}
                x2={x1px - 4} y2={dimLineY - 8}
                stroke={borderColor} strokeWidth={1}
              />
              {/* Left tick */}
              <line
                x1={x0px + 4} y1={dimLineY - 12}
                x2={x0px + 4} y2={dimLineY - 4}
                stroke={borderColor} strokeWidth={1}
              />
              {/* Right tick */}
              <line
                x1={x1px - 4} y1={dimLineY - 12}
                x2={x1px - 4} y2={dimLineY - 4}
                stroke={borderColor} strokeWidth={1}
              />
              <text
                x={cx} y={dimTextY}
                textAnchor="middle" fontSize={10}
                fill={mutedColor} fontFamily="system-ui, sans-serif"
              >
                {s.length.toFixed(2)} m
              </text>
            </g>
          );
        });
      })()}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Combo label rendered below the SVG
// ---------------------------------------------------------------------------

function ComboLabel({
  isEcMode,
  kombiName,
  kombiLatex,
  kombiEd,
}: {
  isEcMode: boolean;
  kombiName: string;
  kombiLatex: string;
  kombiEd: number | null;
}) {
  if (!kombiName && !kombiLatex) return null;

  if (isEcMode) {
    // Plain Unicode string from backend (e.g. "GZT: γ_G · G + 1,5 · S")
    return (
      <p className="text-center text-xs text-[var(--muted-foreground)] mt-1 px-2">
        {kombiName}
      </p>
    );
  }

  // Quick mode: render LaTeX + Ed value
  let formulaHtml = "";
  if (kombiLatex) {
    const inner = kombiLatex.trim().replace(/^\$+/, "").replace(/\$+$/, "");
    try {
      formulaHtml = katex.renderToString(inner, {
        throwOnError: false,
        displayMode: false,
        strict: false,
      });
    } catch {
      formulaHtml = `<code>${inner}</code>`;
    }
  }

  return (
    <div className="flex items-center justify-center gap-3 mt-1 text-xs text-[var(--muted-foreground)] flex-wrap">
      {formulaHtml && (
        <span dangerouslySetInnerHTML={{ __html: formulaHtml }} />
      )}
      {kombiEd != null && (
        <span className="font-mono tabular-nums">
          E<sub>d</sub> = {kombiEd.toFixed(2)} kN/m
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Exported component
// ---------------------------------------------------------------------------

export function LoadPatternSketch({
  schnittgroessen,
  lastfallkombinationen,
}: Props) {
  const spannweiten  = useBeamStore((s) => s.spannweiten);
  const feldanzahl   = useBeamStore((s) => s.feldanzahl);
  const kragarmLinks = useBeamStore((s) => s.kragarmLinks);
  const kragarmRechts = useBeamStore((s) => s.kragarmRechts);
  const ecModus      = useBeamStore((s) => s.ecModus);

  const isEcMode = ecModus === "ec";

  const spans = useMemo(
    () => buildSpanEntries(spannweiten, feldanzahl, kragarmLinks, kragarmRechts),
    [spannweiten, feldanzahl, kragarmLinks, kragarmRechts],
  );

  // ── Extract load-pattern data ────────────────────────────────────────────

  // EC mode: read muster + combo name from schnittgroessen.GZT.max
  const gzt = (schnittgroessen as Record<string, unknown> | undefined)?.GZT as
    | { max?: { moment_muster?: boolean[]; moment_kombi?: string } }
    | undefined;
  const muster: boolean[] = gzt?.max?.moment_muster ?? [];
  const kombiName: string = gzt?.max?.moment_kombi ?? "";

  // Quick mode: find governing combo in lastfallkombinationen
  const governingEntry = useMemo((): KombinationEntry | null => {
    if (!lastfallkombinationen) return null;
    const found = Object.values(lastfallkombinationen).find(
      (v) => (v as KombinationEntry).massgebend === true,
    ) as KombinationEntry | undefined;
    return found ?? null;
  }, [lastfallkombinationen]);

  const kombiLatex: string = governingEntry?.latex ?? "";
  const kombiEd: number | null =
    governingEntry?.Ed ?? governingEntry?.wert ?? null;

  // ── Guard: nothing to show ───────────────────────────────────────────────
  if (totalLength(spans) <= 0) return null;

  return (
    <div className="space-y-1">
      <SketchSvg
        spans={spans}
        kragarmLinks={kragarmLinks}
        kragarmRechts={kragarmRechts}
        isEcMode={isEcMode}
        muster={muster}
      />
      <ComboLabel
        isEcMode={isEcMode}
        kombiName={kombiName}
        kombiLatex={kombiLatex}
        kombiEd={kombiEd}
      />
    </div>
  );
}
```

### Step 2: Verify build

```bash
cd web/frontend && npm run build 2>&1 | grep -E "error|✓"
```
Expected: `✓ built in ...s` — no TypeScript errors.

If there are TypeScript errors about the `gzt` cast, adjust the type assertion on line:
```typescript
const gzt = (schnittgroessen as Record<string, unknown> | undefined)?.GZT as ...
```
to use `as unknown as { max?: ... }` if needed.

### Step 3: Commit

```bash
git add web/frontend/src/components/results/LoadPatternSketch.tsx
git commit -m "feat: add LoadPatternSketch – governing load combination SVG diagram"
```

---

## Task 3: Integrate LoadPatternSketch into ResultsPanel

**Files:**
- Modify: `web/frontend/src/components/results/ResultsPanel.tsx`

### Step 1: Add import

At the top of `ResultsPanel.tsx`, after the existing result-component imports, add:

```tsx
import { LoadPatternSketch } from "./LoadPatternSketch";
```

The existing imports look like:
```tsx
import { BeamSystemSketch } from "./BeamSystemSketch";
import { SchnittgroessenSummary } from "./SchnittgroessenSummary";
import { EC5NachweiseCard } from "./EC5NachweiseCard";
import { LastkombinationenCard } from "./LastkombinationenCard";
import { ForceCharts } from "./ForceCharts";
```

### Step 2: Insert the component

Inside the collapsible body of "Schnittkraftverläufe" (look for the comment `{/* Max values summary */}`), the current structure is:

```tsx
{/* Collapsible body */}
{isSchnittgraeffeOpen && (
  <div className="border-t border-[var(--border)]">
    {/* Max values summary */}
    <div className="px-4 pt-3 pb-2">
      <SchnittgroessenSummary
        schnittgroessen={results.schnittgroessen}
      />
    </div>
    {/* Force diagrams */}
    <div className="px-4 pb-3">
      <ForceCharts />
    </div>
  </div>
)}
```

Replace with (insert `LoadPatternSketch` between Summary and ForceCharts):

```tsx
{/* Collapsible body */}
{isSchnittgraeffeOpen && (
  <div className="border-t border-[var(--border)]">
    {/* Max values summary */}
    <div className="px-4 pt-3 pb-2">
      <SchnittgroessenSummary
        schnittgroessen={results.schnittgroessen}
      />
    </div>
    {/* Governing load combination sketch */}
    <div className="px-4 pb-2">
      <LoadPatternSketch
        schnittgroessen={results.schnittgroessen}
        lastfallkombinationen={results.lastfallkombinationen}
      />
    </div>
    {/* Force diagrams */}
    <div className="px-4 pb-3">
      <ForceCharts />
    </div>
  </div>
)}
```

### Step 3: Verify build

```bash
cd web/frontend && npm run build 2>&1 | grep -E "error|✓"
```
Expected: `✓ built in ...s`

### Step 4: Commit

```bash
git add web/frontend/src/components/results/ResultsPanel.tsx
git commit -m "feat: insert LoadPatternSketch into Schnittkraftverläufe section"
```

---

## Final check

After all three tasks are committed, run a full build one more time:

```bash
cd web/frontend && npm run build 2>&1 | tail -5
```

Expected output ends with `✓ built in ...s` and no error lines.

Then push to trigger deploy:

```bash
git push origin main
```
