/**
 * BeamSystemSketch – SVG diagram of the continuous beam system.
 *
 * Displays:
 *  - Beam line with pinned support triangles
 *  - Field labels ("Feld 1", "Feld 2", …, "Kragarm")
 *  - Dimension lines with span lengths [m]
 *  - Ground lines below each support
 *
 * Reads beam geometry directly from the Zustand store so it can be placed
 * independently of the Plotly charts in the results layout.
 */

import { useMemo } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import {
  buildSpanEntries,
  totalLength,
  supportPositions,
  fieldBoundaryX,
  type SpanEntry,
} from "./beamGeometry";

// ---------------------------------------------------------------------------
// CSS variable helper
// ---------------------------------------------------------------------------

function getCssVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ---------------------------------------------------------------------------
// SVG system sketch
// ---------------------------------------------------------------------------

interface SystemSketchProps {
  spans: SpanEntry[];
  kragarmLinks: boolean;
  kragarmRechts: boolean;
}

function SystemSketchSvg({ spans, kragarmLinks, kragarmRechts }: SystemSketchProps) {
  const total = totalLength(spans);
  if (total <= 0 || spans.length === 0) return null;

  // SVG canvas dimensions (viewBox units)
  const W = 800;
  const BEAM_Y = 40;      // y-coordinate of the beam line
  const LABEL_Y = 22;     // y for field labels above beam
  const SUPPORT_H = 14;   // triangle height
  // Support labels sit at BEAM_Y + SUPPORT_H + 16 = 70 (baseline).
  // DIM_Y is placed below that so dimension lines never overlap the labels.
  const DIM_Y = 88;       // y for dimension text below beam (was 75)
  const SVG_H = 105;      // increased to fit labels + dimension area (was 90)

  const toX = (xM: number) => (xM / total) * W;

  const supports = supportPositions(spans, kragarmLinks, kragarmRechts);

  function trianglePath(cx: number): string {
    const x = toX(cx);
    const y0 = BEAM_Y;
    const half = SUPPORT_H * 0.7;
    return `M ${x} ${y0} L ${x - half} ${y0 + SUPPORT_H} L ${x + half} ${y0 + SUPPORT_H} Z`;
  }

  let xAccum = 0;
  const fields: {
    x0: number;
    x1: number;
    label: string;
    lengthM: number;
    isField: boolean;
  }[] = [];

  spans.forEach((span, i) => {
    const isInnerField = !span.isCantilever;
    let fieldLabel = "";
    if (!span.isCantilever) {
      const fieldIdx = spans.slice(0, i).filter((s) => !s.isCantilever).length + 1;
      fieldLabel = `Feld ${fieldIdx}`;
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

      {/* Support labels A, B, C, … below each triangle – colour tracks Light/Dark mode */}
      {supports.map((sx, i) => (
        <text
          key={`label-${i}`}
          x={toX(sx)}
          y={BEAM_Y + SUPPORT_H + 16}
          textAnchor="middle"
          fontSize="14"
          fontWeight="700"
          fill={fgColor}
          fontFamily="system-ui, sans-serif"
        >
          {String.fromCharCode(65 + i)}
        </text>
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
// Exported component (reads store directly)
// ---------------------------------------------------------------------------

export function BeamSystemSketch() {
  const spannweiten = useBeamStore((s) => s.spannweiten);
  const feldanzahl = useBeamStore((s) => s.feldanzahl);
  const kragarmLinks = useBeamStore((s) => s.kragarmLinks);
  const kragarmRechts = useBeamStore((s) => s.kragarmRechts);

  const spans = useMemo(
    () => buildSpanEntries(spannweiten, feldanzahl, kragarmLinks, kragarmRechts),
    [spannweiten, feldanzahl, kragarmLinks, kragarmRechts]
  );

  const total = totalLength(spans);
  if (total <= 0 || spans.length === 0) return null;

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 px-4 pt-3 pb-2">
      <SystemSketchSvg
        spans={spans}
        kragarmLinks={kragarmLinks}
        kragarmRechts={kragarmRechts}
      />
    </div>
  );
}
