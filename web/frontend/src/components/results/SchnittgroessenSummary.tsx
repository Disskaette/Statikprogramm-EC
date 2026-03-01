/**
 * SchnittgroessenSummary – compact card showing max governing section forces.
 *
 * Unit conversions (from API internal units):
 *   moment    [Nmm] → [kNm]  (÷ 1e6)
 *   querkraft [N]   → [kN]   (÷ 1e3)
 *   durchbiegung    [mm]     (stays mm)
 *
 * Displays GZT (ULS) values for moment and shear; GZG for deflection.
 */

import katex from "katex";

interface Props {
  schnittgroessen: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Inline KaTeX helper – renders a short symbol expression
// ---------------------------------------------------------------------------

function KatexInline({ tex }: { tex: string }) {
  const html = katex.renderToString(tex, {
    throwOnError: false,
    displayMode: false,
    strict: false, // Accept Unicode chars like ² from backend LaTeX
  });
  return (
    <span
      className="katex-inline"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

// ---------------------------------------------------------------------------
// Single stat item
// ---------------------------------------------------------------------------

interface StatItemProps {
  label: string;
  tex: string;
  value: string;
  unit: string;
}

function StatItem({ label, tex, value, unit }: StatItemProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-xs text-[var(--muted-foreground)]">{label}</span>
      <div className="flex items-baseline gap-1">
        <KatexInline tex={tex} />
        <span className="text-base font-mono font-semibold tabular-nums">
          {value}
        </span>
        <span className="text-xs text-[var(--muted-foreground)]">{unit}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SchnittgroessenSummary({ schnittgroessen }: Props) {
  // Extract GZT max values (ULS) for moment and shear
  const gzt = schnittgroessen["GZT"] as
    | { max: { moment: number; querkraft: number; durchbiegung: number } }
    | undefined;

  // Extract GZG max deflection (SLS).
  // GZG is an ARRAY of per-load entries: [{max: {durchbiegung}, ...}, ...]
  // We find the maximum deflection across all load entries.
  const gzgArr = schnittgroessen["GZG"] as
    | Array<{ max: { durchbiegung?: number } }>
    | undefined;

  const momentKNm =
    gzt?.max?.moment != null
      ? (Math.abs(gzt.max.moment) / 1e6).toFixed(2)
      : "—";

  const shearKN =
    gzt?.max?.querkraft != null
      ? (Math.abs(gzt.max.querkraft) / 1e3).toFixed(2)
      : "—";

  // Deflection: pick max from GZG array entries; fall back to GZT.max
  let maxDeflection: number | undefined;
  if (Array.isArray(gzgArr) && gzgArr.length > 0) {
    for (const entry of gzgArr) {
      const d = entry?.max?.durchbiegung;
      if (d != null && (maxDeflection == null || Math.abs(d) > Math.abs(maxDeflection))) {
        maxDeflection = d;
      }
    }
  }
  if (maxDeflection == null && gzt?.max?.durchbiegung != null) {
    maxDeflection = gzt.max.durchbiegung;
  }
  const deflMm =
    maxDeflection != null ? Math.abs(maxDeflection).toFixed(2) : "—";

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 px-4 py-3">
      <p className="text-xs font-medium text-[var(--muted-foreground)] mb-3 uppercase tracking-wide">
        Maßgebende Schnittgrößen
      </p>
      <div className="flex items-center justify-around gap-4 flex-wrap">
        <StatItem
          label="Biegemoment (GZT)"
          tex="M_{Ed}"
          value={momentKNm}
          unit="kNm"
        />
        <div className="h-8 w-px bg-[var(--border)]" aria-hidden="true" />
        <StatItem
          label="Querkraft (GZT)"
          tex="V_{Ed}"
          value={shearKN}
          unit="kN"
        />
        <div className="h-8 w-px bg-[var(--border)]" aria-hidden="true" />
        <StatItem
          label="Durchbiegung (GZG)"
          tex="\delta_{max}"
          value={deflMm}
          unit="mm"
        />
      </div>
    </div>
  );
}
