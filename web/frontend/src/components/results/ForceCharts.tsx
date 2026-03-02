/**
 * ForceCharts – Schnittkraftverläufe (section force diagrams).
 *
 * Renders three stacked Plotly charts:
 *   1. Moment diagram M [kNm]  – from GZT data, y-axis inverted (EC convention)
 *   2. Shear diagram V [kN]   – from GZT data, y-axis inverted
 *   3. Deflection diagram w [mm] – from GZG (worst case) or GZT, y-axis not inverted
 *
 * The beam system sketch (SVG) is rendered separately in BeamSystemSketch.tsx
 * so it can be placed above these charts in the results layout.
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
import {
  buildSpanEntries,
  totalLength,
  fieldBoundaryX,
} from "./beamGeometry";

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
// Main component
// ---------------------------------------------------------------------------
// Note: SystemSketch is now in BeamSystemSketch.tsx (displayed separately above
// the charts in ResultsPanel) and no longer rendered here.

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
      {/* Moment diagram M */}
      <div className="rounded-t-lg border border-[var(--border)] bg-[var(--background)] px-2 pt-1 pb-0">
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
