/**
 * ForceCharts – Schnittkraftverläufe (section force diagrams).
 *
 * Renders three stacked Plotly charts and a simple SVG system sketch:
 *   1. System sketch (SVG) – beam, supports, field labels, span dimensions
 *   2. Moment diagram M [kNm]  – from GZT data, y-axis inverted (EC convention)
 *   3. Shear diagram V [kN]   – from GZT data, y-axis inverted
 *   4. Deflection diagram w [mm] – from GZG (worst case) or GZT, y-axis inverted
 *
 * Unit conventions (internal API units → display units):
 *   moment    [Nmm] → [kNm]  (÷ 1e6)
 *   querkraft [N]   → [kN]   (÷ 1e3)
 *   durchbiegung [mm] → [mm] (no conversion)
 *
 * Plotly is imported via the react-plotly.js factory pattern to allow
 * tree-shaking with plotly.js-dist-min.
 */

import { useMemo } from "react";
import Plotly from "plotly.js-dist-min";
import createPlotlyComponent from "react-plotly.js/factory";
import { useBeamStore } from "@/stores/useBeamStore";
import { useTheme } from "@/hooks/useTheme";

// Build Plot component once at module level (avoids recreation on every render)
const Plot = createPlotlyComponent(Plotly);

// ---------------------------------------------------------------------------
// CSS variable helpers – read actual computed values for Plotly (canvas)
// ---------------------------------------------------------------------------

/** Read a CSS custom property from :root as a trimmed string */
function getCssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

// ---------------------------------------------------------------------------
// Beam geometry helpers
// ---------------------------------------------------------------------------

/**
 * Ordered list of span entries from the store spannweiten dict.
 * Returns: [{ key, length, isCantilever }]
 * Order: kragarm_links, feld_1..feld_N, kragarm_rechts
 */
interface SpanEntry {
  key: string;
  length: number;
  isCantilever: boolean;
}

function buildSpanEntries(
  spannweiten: Record<string, number>,
  feldanzahl: number,
  kragarmLinks: boolean,
  kragarmRechts: boolean
): SpanEntry[] {
  const entries: SpanEntry[] = [];

  if (kragarmLinks) {
    entries.push({
      key: "kragarm_links",
      length: spannweiten["kragarm_links"] ?? 1.5,
      isCantilever: true,
    });
  }

  for (let i = 1; i <= feldanzahl; i++) {
    entries.push({
      key: `feld_${i}`,
      length: spannweiten[`feld_${i}`] ?? 5.0,
      isCantilever: false,
    });
  }

  if (kragarmRechts) {
    entries.push({
      key: "kragarm_rechts",
      length: spannweiten["kragarm_rechts"] ?? 1.5,
      isCantilever: true,
    });
  }

  return entries;
}

/** Total beam length from left end to right end [m] */
function totalLength(spans: SpanEntry[]): number {
  return spans.reduce((sum, s) => sum + s.length, 0);
}

/** x-positions of all support points [m] (field boundaries, excluding cantilever free ends) */
function supportPositions(
  spans: SpanEntry[],
  kragarmLinks: boolean,
  kragarmRechts: boolean
): number[] {
  const positions: number[] = [];
  let x = 0;

  for (let i = 0; i < spans.length; i++) {
    // A support exists at the START of this span if:
    //  - it is NOT the left free cantilever end
    const isLeftCantilever = kragarmLinks && i === 0;
    if (!isLeftCantilever) {
      positions.push(x);
    }
    x += spans[i].length;
  }

  // Right-most support: at the right end only if it is not a free cantilever tip
  const isRightCantilever =
    kragarmRechts && spans.length > 0 && spans[spans.length - 1].isCantilever;
  if (!isRightCantilever) {
    positions.push(x);
  }

  return [...new Set(positions)].sort((a, b) => a - b);
}

/** x-positions of all interior field boundaries (for Plotly vertical lines) */
function fieldBoundaryX(spans: SpanEntry[]): number[] {
  const boundaries: number[] = [];
  let x = 0;
  for (let i = 0; i < spans.length - 1; i++) {
    x += spans[i].length;
    boundaries.push(x);
  }
  return boundaries;
}

// ---------------------------------------------------------------------------
// GZG deflection helpers
// ---------------------------------------------------------------------------

interface GzgEntry {
  max?: { durchbiegung?: number };
  moment?: number[];
  querkraft?: number[];
  durchbiegung?: number[];
  lastfall?: string;
  kommentar?: string;
}

/**
 * From the GZG array, find the entry with the largest absolute max deflection.
 * Falls back to the first entry if all max values are null/undefined.
 */
function findWorstGzgEntry(gzgArr: GzgEntry[]): GzgEntry | null {
  if (!gzgArr || gzgArr.length === 0) return null;

  let best = gzgArr[0];
  let bestAbs = Math.abs(gzgArr[0]?.max?.durchbiegung ?? 0);

  for (const entry of gzgArr) {
    const d = Math.abs(entry?.max?.durchbiegung ?? 0);
    if (d > bestAbs) {
      bestAbs = d;
      best = entry;
    }
  }

  return best;
}

// ---------------------------------------------------------------------------
// Plotly layout builder
// ---------------------------------------------------------------------------

interface ThemeColors {
  textColor: string;
  gridColor: string;
  zerolineColor: string;
}

function getThemeColors(): ThemeColors {
  const fg = getCssVar("--foreground") || "#0a0a0a";
  const border = getCssVar("--border") || "#e5e7eb";
  return {
    textColor: fg,
    gridColor: border,
    zerolineColor: fg,
  };
}

/**
 * Build a Plotly layout for a single force diagram.
 *
 * @param reverseY – If true, y-axis is inverted (autorange: 'reversed') per
 *   structural engineering convention (positive moment plots downward).
 *   For deflection, set to false because the backend already returns
 *   negative values for downward deflection.
 */
function buildLayout(
  yAxisTitle: string,
  colors: ThemeColors,
  xRange: [number, number],
  fieldBoundaries: number[],
  totalLen: number,
  reverseY: boolean = true
): Partial<Plotly.Layout> {
  const { textColor, gridColor, zerolineColor } = colors;

  // Vertical dashed lines at field boundaries
  const shapes: Partial<Plotly.Shape>[] = fieldBoundaries.map((x) => ({
    type: "line" as const,
    x0: x,
    x1: x,
    y0: 0,
    y1: 1,
    yref: "paper" as const,
    line: {
      color: gridColor,
      width: 1,
      dash: "dash" as const,
    },
  }));

  // Dummy annotation to suppress TS unused-var warning on totalLen
  void totalLen;

  return {
    margin: { l: 60, r: 20, t: 10, b: 30 },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    xaxis: {
      range: xRange,
      showgrid: true,
      gridcolor: gridColor,
      zeroline: false,
      tickfont: { color: textColor, size: 11 },
      ticksuffix: " m",
    },
    yaxis: {
      autorange: reverseY ? "reversed" : true,
      showgrid: true,
      gridcolor: gridColor,
      zeroline: true,
      zerolinecolor: zerolineColor,
      zerolinewidth: 1.5,
      title: {
        text: yAxisTitle,
        standoff: 10,
        font: { color: textColor, size: 12 },
      },
      tickfont: { color: textColor, size: 11 },
    },
    shapes,
    showlegend: false,
    hovermode: "x unified" as const,
  };
}

// ---------------------------------------------------------------------------
// System sketch (SVG)
// ---------------------------------------------------------------------------

interface SystemSketchProps {
  spans: SpanEntry[];
  kragarmLinks: boolean;
  kragarmRechts: boolean;
}

function SystemSketch({ spans, kragarmLinks, kragarmRechts }: SystemSketchProps) {
  const total = totalLength(spans);
  if (total <= 0 || spans.length === 0) return null;

  // SVG canvas dimensions (viewBox units)
  const W = 800;
  const BEAM_Y = 40;      // y-coordinate of the beam line
  const LABEL_Y = 22;     // y for field labels above beam
  const DIM_Y = 75;       // y for dimension text below beam
  const SUPPORT_H = 14;   // triangle height
  const SVG_H = 90;

  const toX = (xM: number) => (xM / total) * W;

  // Support positions
  const supports = supportPositions(spans, kragarmLinks, kragarmRechts);

  // Triangle SVG path for pinned support (pointing downward from beam)
  function trianglePath(cx: number): string {
    const x = toX(cx);
    const y0 = BEAM_Y;
    const half = SUPPORT_H * 0.7;
    return `M ${x} ${y0} L ${x - half} ${y0 + SUPPORT_H} L ${x + half} ${y0 + SUPPORT_H} Z`;
  }

  // Field label and dimension rendering
  let xAccum = 0;
  const fields: { x0: number; x1: number; label: string; lengthM: number; isField: boolean }[] = [];
  spans.forEach((span, i) => {
    const isInnerField = !span.isCantilever;
    // Count only non-cantilever fields for labeling
    let fieldLabel = "";
    if (!span.isCantilever) {
      // Count how many regular fields come before this
      const fieldIdx = spans.slice(0, i).filter((s) => !s.isCantilever).length + 1;
      fieldLabel = `Feld ${fieldIdx}`;
    } else if (span.key === "kragarm_links") {
      fieldLabel = "Kragarm";
    } else {
      fieldLabel = "Kragarm";
    }
    fields.push({
      x0: xAccum,
      x1: xAccum + span.length,
      label: fieldLabel,
      lengthM: span.length,
      isField: isInnerField,
    });
    xAccum += span.length;
  });

  const fgColor = getCssVar("--foreground") || "#0a0a0a";
  const mutedColor = getCssVar("--muted-foreground") || "#737373";
  const borderColor = getCssVar("--border") || "#e5e7eb";

  return (
    <svg
      viewBox={`0 0 ${W} ${SVG_H}`}
      className="w-full"
      style={{ maxHeight: SVG_H, overflow: "visible" }}
      aria-label="Systemskizze Träger"
      role="img"
    >
      {/* Beam line */}
      <line
        x1={toX(0)}
        y1={BEAM_Y}
        x2={toX(total)}
        y2={BEAM_Y}
        stroke={fgColor}
        strokeWidth={3}
      />

      {/* Support triangles */}
      {supports.map((sx) => (
        <path
          key={sx}
          d={trianglePath(sx)}
          fill={fgColor}
          stroke="none"
          opacity={0.85}
        />
      ))}

      {/* Ground lines below supports */}
      {supports.map((sx) => (
        <line
          key={`ground-${sx}`}
          x1={toX(sx) - SUPPORT_H * 0.9}
          y1={BEAM_Y + SUPPORT_H + 1}
          x2={toX(sx) + SUPPORT_H * 0.9}
          y2={BEAM_Y + SUPPORT_H + 1}
          stroke={borderColor}
          strokeWidth={1.5}
        />
      ))}

      {/* Field boundary tick marks at the top of beam */}
      {fieldBoundaryX(spans).map((bx) => (
        <line
          key={`tick-${bx}`}
          x1={toX(bx)}
          y1={BEAM_Y - 5}
          x2={toX(bx)}
          y2={BEAM_Y + 5}
          stroke={mutedColor}
          strokeWidth={1}
        />
      ))}

      {/* Field labels and dimension lines */}
      {fields.map((f) => {
        const cx = toX((f.x0 + f.x1) / 2);
        const x0px = toX(f.x0);
        const x1px = toX(f.x1);
        return (
          <g key={f.label + f.x0}>
            {/* Field label */}
            <text
              x={cx}
              y={LABEL_Y}
              textAnchor="middle"
              fontSize={11}
              fill={mutedColor}
              fontFamily="system-ui, sans-serif"
            >
              {f.label}
            </text>

            {/* Dimension line */}
            <line
              x1={x0px + 4}
              y1={DIM_Y - 8}
              x2={x1px - 4}
              y2={DIM_Y - 8}
              stroke={borderColor}
              strokeWidth={1}
              markerEnd="none"
            />
            {/* Left tick */}
            <line
              x1={x0px + 4}
              y1={DIM_Y - 12}
              x2={x0px + 4}
              y2={DIM_Y - 4}
              stroke={borderColor}
              strokeWidth={1}
            />
            {/* Right tick */}
            <line
              x1={x1px - 4}
              y1={DIM_Y - 12}
              x2={x1px - 4}
              y2={DIM_Y - 4}
              stroke={borderColor}
              strokeWidth={1}
            />

            {/* Span dimension text */}
            <text
              x={cx}
              y={DIM_Y + 5}
              textAnchor="middle"
              fontSize={10}
              fill={mutedColor}
              fontFamily="system-ui, sans-serif"
            >
              {f.lengthM.toFixed(2)} m
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ForceCharts() {
  const results = useBeamStore((s) => s.results);
  const spannweiten = useBeamStore((s) => s.spannweiten);
  const feldanzahl = useBeamStore((s) => s.feldanzahl);
  const kragarmLinks = useBeamStore((s) => s.kragarmLinks);
  const kragarmRechts = useBeamStore((s) => s.kragarmRechts);

  // useTheme causes re-render when the user switches dark/light, so colors update
  const { theme } = useTheme();

  // Build ordered span list
  const spans = useMemo(
    () => buildSpanEntries(spannweiten, feldanzahl, kragarmLinks, kragarmRechts),
    [spannweiten, feldanzahl, kragarmLinks, kragarmRechts]
  );

  const totalLen = useMemo(() => totalLength(spans), [spans]);
  const boundaries = useMemo(() => fieldBoundaryX(spans), [spans]);
  const xRange: [number, number] = [0, totalLen];

  // Determine number of data points from the API response (varies: often ~9901)
  const numDataPoints = useMemo(() => {
    const gztData = (results?.schnittgroessen as Record<string, unknown> | undefined)?.["GZT"] as
      | { moment?: number[] }
      | undefined;
    return gztData?.moment?.length ?? 100;
  }, [results]);

  // Generate x positions matching the API array length
  const xPositions = useMemo(() => {
    const n = numDataPoints;
    if (n <= 1 || totalLen <= 0) return [0];
    return Array.from({ length: n }, (_, i) => (i / (n - 1)) * totalLen);
  }, [totalLen, numDataPoints]);

  // Extract schnittgroessen from results
  const schnittgroessen = results?.schnittgroessen as Record<string, unknown> | null | undefined;

  const gzt = schnittgroessen?.["GZT"] as
    | {
        max: { moment: number; querkraft: number; durchbiegung: number };
        moment: number[];
        querkraft: number[];
        durchbiegung: number[];
      }
    | undefined;

  const gzgArr = schnittgroessen?.["GZG"] as GzgEntry[] | undefined;

  // Find worst GZG entry for deflection
  const worstGzg = useMemo(
    () => (Array.isArray(gzgArr) ? findWorstGzgEntry(gzgArr) : null),
    [gzgArr]
  );

  // Read theme colors (re-computed when theme changes via the theme dependency)
  const colors = useMemo(() => {
    void theme; // ensure re-run when theme changes
    return getThemeColors();
  }, [theme]);

  // ---------------------------------------------------------------------------
  // Plot data – memoized per diagram
  // ---------------------------------------------------------------------------

  // Moment [kNm] – convert from Nmm (÷1e6)
  const momentData = useMemo((): Plotly.Data[] => {
    const rawMoment = gzt?.moment;
    if (!rawMoment || rawMoment.length === 0) return [];

    const yValues = rawMoment.map((v) => v / 1e6);

    return [
      {
        x: xPositions,
        y: yValues,
        type: "scatter",
        mode: "lines",
        fill: "tozeroy",
        fillcolor: "rgba(239, 68, 68, 0.15)", // red-500 at 15% opacity
        line: { color: "#EF4444", width: 2 },
        hovertemplate: "<b>M = %{y:.3f} kNm</b><br>x = %{x:.2f} m<extra></extra>",
        name: "M",
      },
    ];
  }, [gzt?.moment, xPositions]);

  // Shear [kN] – convert from N (÷1e3)
  const shearData = useMemo((): Plotly.Data[] => {
    const rawShear = gzt?.querkraft;
    if (!rawShear || rawShear.length === 0) return [];

    const yValues = rawShear.map((v) => v / 1e3);

    return [
      {
        x: xPositions,
        y: yValues,
        type: "scatter",
        mode: "lines",
        fill: "tozeroy",
        fillcolor: "rgba(59, 130, 246, 0.15)", // blue-500 at 15% opacity
        line: { color: "#3B82F6", width: 2 },
        hovertemplate: "<b>V = %{y:.3f} kN</b><br>x = %{x:.2f} m<extra></extra>",
        name: "V",
      },
    ];
  }, [gzt?.querkraft, xPositions]);

  // Deflection [mm] – GZG (worst case) or GZT fallback
  const deflectionData = useMemo((): Plotly.Data[] => {
    const rawDefl =
      worstGzg?.durchbiegung ?? gzt?.durchbiegung;

    if (!rawDefl || rawDefl.length === 0) return [];

    return [
      {
        x: xPositions,
        y: rawDefl,
        type: "scatter",
        mode: "lines",
        fill: "tozeroy",
        fillcolor: "rgba(139, 92, 246, 0.15)", // violet-500 at 15% opacity
        line: { color: "#8B5CF6", width: 2 },
        hovertemplate: "<b>w = %{y:.3f} mm</b><br>x = %{x:.2f} m<extra></extra>",
        name: "w",
      },
    ];
  }, [worstGzg, gzt?.durchbiegung, xPositions]);

  // ---------------------------------------------------------------------------
  // Guard: need GZT data to render charts
  // ---------------------------------------------------------------------------

  if (!gzt || xPositions.length === 0) return null;

  // ---------------------------------------------------------------------------
  // Shared Plotly config
  // ---------------------------------------------------------------------------

  const plotConfig: Partial<Plotly.Config> = {
    responsive: true,
    displayModeBar: false,
    displaylogo: false,
  };

  const plotStyle = { width: "100%", height: 200 };

  const momentLayout = buildLayout("M [kNm]", colors, xRange, boundaries, totalLen, true);
  const shearLayout = buildLayout("V [kN]", colors, xRange, boundaries, totalLen, true);
  // Deflection: do NOT invert y-axis. The backend returns negative values for
  // downward deflection (FEM convention), which naturally plots downward in a
  // standard y-axis – matching the physical beam deformation direction.
  const deflectionLayout = buildLayout("w [mm]", colors, xRange, boundaries, totalLen, false);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-0">
      {/* System sketch */}
      <div className="rounded-t-lg border border-[var(--border)] bg-[var(--muted)]/20 px-4 pt-3 pb-1">
        <SystemSketch
          spans={spans}
          kragarmLinks={kragarmLinks}
          kragarmRechts={kragarmRechts}
        />
      </div>

      {/* Moment diagram M */}
      <div className="border-x border-b border-[var(--border)] bg-[var(--background)] px-2 pt-1 pb-0">
        <Plot
          data={momentData}
          layout={momentLayout}
          config={plotConfig}
          style={plotStyle}
          useResizeHandler={true}
        />
      </div>

      {/* Shear diagram V */}
      <div className="border-x border-b border-[var(--border)] bg-[var(--background)] px-2 pt-1 pb-0">
        <Plot
          data={shearData}
          layout={shearLayout}
          config={plotConfig}
          style={plotStyle}
          useResizeHandler={true}
        />
      </div>

      {/* Deflection diagram w */}
      <div className="rounded-b-lg border-x border-b border-[var(--border)] bg-[var(--background)] px-2 pt-1 pb-0">
        <Plot
          data={deflectionData}
          layout={deflectionLayout}
          config={plotConfig}
          style={plotStyle}
          useResizeHandler={true}
        />
      </div>
    </div>
  );
}
