/**
 * EC5NachweiseCard – displays all EC5 design verification checks.
 *
 * The five checks shown are:
 *   biegung           → Bending        EC5 §6.1.6
 *   schub             → Shear          EC5 §6.1.7
 *   durchbiegung_inst → Instantaneous deflection  (SLS)
 *   durchbiegung_fin  → Final deflection          (SLS)
 *   durchbiegung_net_fin → Net final deflection   (SLS)
 *
 * For each check the API supplies:
 *   latex      – LaTeX formula string with surrounding $…$ delimiters
 *   erfuellt   – boolean: true if η ≤ 1.0
 *   ausnutzung – utilisation ratio η
 *
 * Utilisation bar colour thresholds:
 *   η <  0.90 → green  (ok)
 *   η ≤  1.00 → orange (approaching limit; 100% still passes)
 *   η >  1.00 → red    (exceeded)
 */

import katex from "katex";
import type { EC5Nachweis } from "@/types/beam";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EC5NachweiseResult {
  biegung?: EC5Nachweis;
  schub?: EC5Nachweis;
  durchbiegung_inst?: EC5Nachweis;
  durchbiegung_fin?: EC5Nachweis;
  durchbiegung_net_fin?: EC5Nachweis;
}

interface Props {
  ec5Nachweise: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Strength checks – each rendered as an individual card */
const STRENGTH_KEYS = ["biegung", "schub"] as const;

/** SLS deflection checks – grouped into one combined card */
const DEFLECTION_KEYS = [
  "durchbiegung_inst",
  "durchbiegung_fin",
  "durchbiegung_net_fin",
] as const;

type StrengthKey = (typeof STRENGTH_KEYS)[number];
type DeflectionKey = (typeof DEFLECTION_KEYS)[number];
type CheckKey = StrengthKey | DeflectionKey;

/** Static title fallbacks (used when `bezeichnung` is absent) */
const TITLES: Record<CheckKey, string> = {
  biegung: "Biegung nach EC5 §6.1.6",
  schub: "Schub nach EC5 §6.1.7",
  durchbiegung_inst: "Sofort-Durchbiegung",
  durchbiegung_fin: "End-Durchbiegung",
  durchbiegung_net_fin: "Netto-End-Durchbiegung",
};

// Bar fills to 100 % at η = 1.0; values above 1.0 keep the bar full (clipped).
const BAR_MAX_ETA = 1.0;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Strip outer LaTeX math delimiters ($…$ or $$…$$) before passing to KaTeX.
 * The API always wraps the formula in single-dollar display delimiters.
 */
function stripDelimiters(latex: string): string {
  const trimmed = latex.trim();
  if (trimmed.startsWith("$$") && trimmed.endsWith("$$")) {
    return trimmed.slice(2, -2).trim();
  }
  if (trimmed.startsWith("$") && trimmed.endsWith("$")) {
    return trimmed.slice(1, -1).trim();
  }
  return trimmed;
}

/**
 * Determine Tailwind colour class based on η value.
 *   η <  0.90 → green  (utilisation acceptable)
 *   η ≤  1.00 → orange (approaching limit; η = 1.0 is still ok)
 *   η >  1.00 → red    (limit exceeded)
 */
function barColour(eta: number): string {
  if (eta < 0.9) return "bg-green-500";
  if (eta <= 1.0) return "bg-orange-500";
  return "bg-red-500";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function UtilisationBar({ eta }: { eta: number }) {
  const widthPct = Math.min(eta / BAR_MAX_ETA, 1) * 100;
  const colour = barColour(eta);

  return (
    <div
      className="h-2 w-full rounded-full bg-[var(--border)] overflow-hidden"
      role="progressbar"
      aria-valuenow={Math.round(eta * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={`h-full rounded-full transition-all duration-300 ${colour}`}
        style={{ width: `${widthPct}%` }}
      />
    </div>
  );
}

function KatexFormula({ latex }: { latex: string }) {
  const inner = stripDelimiters(latex);
  let html: string;
  try {
    html = katex.renderToString(inner, {
      throwOnError: false,
      displayMode: true,
      strict: false, // Accept Unicode chars like ² from backend LaTeX
    });
  } catch {
    // Fallback: show raw LaTeX if rendering fails
    html = `<code style="font-size:0.8em">${inner}</code>`;
  }

  return (
    <div
      className="overflow-x-auto text-sm"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

interface CheckCardProps {
  checkKey: CheckKey;
  nachweis: EC5Nachweis;
}

function CheckCard({ checkKey, nachweis }: CheckCardProps) {
  const { latex, erfuellt, ausnutzung } = nachweis;

  // Use `bezeichnung` field when present (deflection checks supply it)
  const bezeichnung = nachweis["bezeichnung"] as string | undefined;
  const title = bezeichnung ?? TITLES[checkKey];

  const etaFormatted = ausnutzung.toFixed(2);
  const statusIcon = erfuellt ? "✅" : "❌";
  const etaColourClass = erfuellt
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400";

  return (
    <div className="rounded-lg border border-[var(--border)] p-4 space-y-3">
      {/* Header row: title + status icon */}
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">
          {title}
        </h3>
        <span aria-label={erfuellt ? "erfüllt" : "nicht erfüllt"}>
          {statusIcon}
        </span>
      </div>

      {/* Utilisation bar + η value */}
      <div className="space-y-1">
        <UtilisationBar eta={ausnutzung} />
        <div className="flex justify-between items-center text-xs">
          <span className="text-[var(--muted-foreground)]">
            Ausnutzung
          </span>
          <span className={`font-mono font-semibold tabular-nums ${etaColourClass}`}>
            {/* Greek η via Unicode (renders without KaTeX dependency here) */}
            η = {etaFormatted}
          </span>
        </div>
      </div>

      {/* LaTeX formula */}
      <div className="rounded-md bg-[var(--muted)]/40 px-3 py-2 overflow-x-auto">
        <KatexFormula latex={latex} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Combined SLS deflection card
// ---------------------------------------------------------------------------

/**
 * DurchbiegungsCard – groups all three SLS deflection checks into one card.
 *
 * Shows a single bar with the maximum η across the three sub-checks plus a
 * compact row per sub-check (name | η value | pass/fail icon | LaTeX formula).
 * This keeps the results panel compact while still showing all detail.
 */
function DurchbiegungsCard({ data }: { data: EC5NachweiseResult }) {
  const checks = DEFLECTION_KEYS.map((key) => ({
    key,
    nachweis: data[key],
  })).filter((c): c is { key: DeflectionKey; nachweis: EC5Nachweis } =>
    c.nachweis != null
  );

  if (checks.length === 0) return null;

  const maxEta = Math.max(...checks.map((c) => c.nachweis.ausnutzung));
  const allPassed = checks.every((c) => c.nachweis.erfuellt);

  const maxEtaColour =
    maxEta <= 1.0
      ? "text-green-600 dark:text-green-400"
      : "text-red-600 dark:text-red-400";

  return (
    <div className="rounded-lg border border-[var(--border)] p-4 space-y-3">
      {/* Header: group title + overall pass/fail */}
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">
          Gebrauchstauglichkeit (GZG)
        </h3>
        <span aria-label={allPassed ? "erfüllt" : "nicht erfüllt"}>
          {allPassed ? "✅" : "❌"}
        </span>
      </div>

      {/* Single bar – maximum η of the three checks */}
      <div className="space-y-1">
        <UtilisationBar eta={maxEta} />
        <div className="flex justify-between items-center text-xs">
          <span className="text-[var(--muted-foreground)]">
            max. Ausnutzung
          </span>
          <span className={`font-mono font-semibold tabular-nums ${maxEtaColour}`}>
            η = {maxEta.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Sub-checks: one row + formula per deflection check */}
      <div className="space-y-3 pt-1 border-t border-[var(--border)]">
        {checks.map(({ key, nachweis }) => {
          const bezeichnung = nachweis["bezeichnung"] as string | undefined;
          const title = bezeichnung ?? TITLES[key];
          const eta = nachweis.ausnutzung;
          const erfuellt = nachweis.erfuellt;
          const etaColour = erfuellt
            ? "text-green-600 dark:text-green-400"
            : "text-red-600 dark:text-red-400";

          return (
            <div key={key} className="space-y-1.5">
              {/* Title row */}
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="font-medium text-[var(--foreground)]">
                  {title}
                </span>
                <span className={`font-mono tabular-nums ${etaColour}`}>
                  η = {eta.toFixed(2)}&nbsp;{erfuellt ? "✅" : "❌"}
                </span>
              </div>
              {/* LaTeX formula */}
              <div className="rounded-md bg-[var(--muted)]/40 px-3 py-2 overflow-x-auto">
                <KatexFormula latex={nachweis.latex} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function EC5NachweiseCard({ ec5Nachweise }: Props) {
  const data = ec5Nachweise as EC5NachweiseResult;

  return (
    <div className="space-y-3">
      <h2 className="text-base font-semibold text-[var(--foreground)]">
        EC5-Nachweise
      </h2>

      {/* Strength checks (ULS) – each as its own card */}
      {STRENGTH_KEYS.map((key) => {
        const nachweis = data[key];
        if (!nachweis) return null;
        return <CheckCard key={key} checkKey={key} nachweis={nachweis} />;
      })}

      {/* SLS deflection checks – grouped in one combined card */}
      <DurchbiegungsCard data={data} />
    </div>
  );
}
