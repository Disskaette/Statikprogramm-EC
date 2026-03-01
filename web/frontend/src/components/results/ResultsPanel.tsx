/**
 * ResultsPanel – main results container.
 *
 * Reads calculation results directly from the Zustand store and composes the
 * individual result display components:
 *   1. SchnittgroessenSummary  – max moment / shear / deflection header card
 *   2. EC5NachweiseCard        – all five EC5 verification checks
 *   3. LastkombinationenCard   – collapsible ULS + SLS load combinations
 *
 * While a recalculation is running on top of existing results a semi-transparent
 * loading overlay is shown so the user knows the values are being updated.
 *
 * States:
 *   results === null && !isCalculating     → placeholder (empty state)
 *   results === null && isCalculating      → full loading spinner
 *   results !== null && isCalculating      → overlay spinner on existing results
 *   results !== null && !isCalculating     → full results display
 *   calculationError                        → error banner (always shown)
 */

import { useBeamStore } from "@/stores/useBeamStore";
import { SchnittgroessenSummary } from "./SchnittgroessenSummary";
import { EC5NachweiseCard } from "./EC5NachweiseCard";
import { LastkombinationenCard } from "./LastkombinationenCard";
import { ForceCharts } from "./ForceCharts";

// ---------------------------------------------------------------------------
// Spinner
// ---------------------------------------------------------------------------

function Spinner({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const sizeClass = size === "sm" ? "h-4 w-4" : size === "lg" ? "h-8 w-8" : "h-6 w-6";
  return (
    <svg
      className={`animate-spin ${sizeClass} text-[var(--primary)]`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Placeholder shown when no results exist yet
// ---------------------------------------------------------------------------

function EmptyState({ isCalculating }: { isCalculating: boolean }) {
  if (isCalculating) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-[var(--muted-foreground)]">
        <Spinner size="lg" />
        <p className="text-sm">Berechnung läuft...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-[var(--muted-foreground)]">
      <svg
        className="h-10 w-10 opacity-30"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 17v-2m3 2v-4m3 4v-6M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
        />
      </svg>
      <p className="text-sm">
        Ergebnisse erscheinen hier nach der ersten Berechnung.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error banner
// ---------------------------------------------------------------------------

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950/50 dark:text-red-400">
      <span className="shrink-0 font-bold">Fehler:</span>
      <span className="break-words">{message}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recalculating overlay (shown on top of existing results)
// ---------------------------------------------------------------------------

function RecalculatingOverlay() {
  return (
    <div className="absolute inset-0 flex items-start justify-end p-3 pointer-events-none">
      <div className="flex items-center gap-1.5 rounded-full bg-[var(--background)]/90 border border-[var(--border)] px-3 py-1.5 shadow-sm">
        <Spinner size="sm" />
        <span className="text-xs text-[var(--muted-foreground)]">
          Aktualisierung…
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ResultsPanel() {
  const results = useBeamStore((s) => s.results);
  const isCalculating = useBeamStore((s) => s.isCalculating);
  const error = useBeamStore((s) => s.calculationError);

  return (
    <div className="space-y-4">
      {/* Section heading */}
      <h2 className="text-lg font-semibold text-[var(--foreground)]">
        Ergebnisse
      </h2>

      {/* Error banner (always shown when an error is present) */}
      {error && <ErrorBanner message={error} />}

      {/* Main result area */}
      {results === null ? (
        <EmptyState isCalculating={isCalculating} />
      ) : (
        // Relative container so the overlay can be positioned inside
        <div className="relative space-y-4">
          {/* Recalculating overlay – shown when updating existing results */}
          {isCalculating && <RecalculatingOverlay />}

          {/* 1. Section forces summary */}
          {results.schnittgroessen && (
            <SchnittgroessenSummary
              schnittgroessen={results.schnittgroessen}
            />
          )}

          {/* 2. EC5 design checks */}
          {results.ec5_nachweise && (
            <EC5NachweiseCard ec5Nachweise={results.ec5_nachweise} />
          )}

          {/* 3. Section force diagrams (Schnittkraftverläufe) */}
          {results.schnittgroessen && (
            <section>
              <h3 className="text-sm font-semibold text-[var(--foreground)] mb-2 uppercase tracking-wide">
                Schnittkraftverläufe
              </h3>
              <ForceCharts />
            </section>
          )}

          {/* 4. Load combinations (collapsible) */}
          {(results.lastfallkombinationen ??
            results.gzg_lastfallkombinationen) && (
            <LastkombinationenCard
              lastfallkombinationen={results.lastfallkombinationen ?? null}
              gzgLastfallkombinationen={
                results.gzg_lastfallkombinationen ?? null
              }
            />
          )}

          {/* Fallback when all result sections are null (quick mode may omit some) */}
          {!results.schnittgroessen &&
            !results.ec5_nachweise &&
            !results.lastfallkombinationen &&
            !results.gzg_lastfallkombinationen && (
              <p className="rounded-lg border border-[var(--border)] px-4 py-6 text-center text-sm text-[var(--muted-foreground)] italic">
                Die Berechnung lieferte keine Ausgabedaten.
              </p>
            )}
        </div>
      )}
    </div>
  );
}
