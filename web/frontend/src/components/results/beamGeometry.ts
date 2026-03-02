/**
 * beamGeometry.ts – shared beam geometry helpers.
 *
 * Used by both BeamSystemSketch (SVG) and ForceCharts (Plotly) to avoid
 * duplicating the span/support logic.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SpanEntry {
  key: string;
  length: number;
  isCantilever: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build an ordered list of span entries from the store's spannweiten dict.
 * Order: kragarm_links → feld_1..feld_N → kragarm_rechts
 */
export function buildSpanEntries(
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
export function totalLength(spans: SpanEntry[]): number {
  return spans.reduce((sum, s) => sum + s.length, 0);
}

/**
 * x-positions of all support points [m].
 * Supports sit at field boundaries; free cantilever ends have none.
 */
export function supportPositions(
  spans: SpanEntry[],
  kragarmLinks: boolean,
  kragarmRechts: boolean
): number[] {
  const positions: number[] = [];
  let x = 0;

  for (let i = 0; i < spans.length; i++) {
    const isLeftCantilever = kragarmLinks && i === 0;
    if (!isLeftCantilever) {
      positions.push(x);
    }
    x += spans[i].length;
  }

  // Right-most support: only if it is not a free cantilever tip
  const isRightCantilever =
    kragarmRechts && spans.length > 0 && spans[spans.length - 1].isCantilever;
  if (!isRightCantilever) {
    positions.push(x);
  }

  return [...new Set(positions)].sort((a, b) => a - b);
}

/** x-positions of all interior field boundaries (for chart vertical lines) */
export function fieldBoundaryX(spans: SpanEntry[]): number[] {
  const boundaries: number[] = [];
  let x = 0;
  for (let i = 0; i < spans.length - 1; i++) {
    x += spans[i].length;
    boundaries.push(x);
  }
  return boundaries;
}
