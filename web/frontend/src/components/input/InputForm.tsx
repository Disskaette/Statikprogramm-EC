/**
 * InputForm – main form container that assembles all input sections.
 *
 * Calculation is triggered automatically via debounce whenever any form state
 * changes. The user does not need to click a "Berechnen" button (though one
 * is provided as a fallback / explicit trigger).
 *
 * Status indicators:
 *  - Spinner + "Berechnung läuft..." when isCalculating
 *  - Red error text when calculationError is set
 *  - Green "Ergebnis bereit" when results are available and no error
 */

import { useEffect, useRef } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import { useCalculation } from "@/hooks/useCalculation";
import { useProjectStore } from "@/stores/useProjectStore";

import { CalculationModeToggle } from "./CalculationModeToggle";
import { SystemSection } from "./SystemSection";
import { LoadsSection } from "./LoadsSection";
import { CrossSectionSection } from "./CrossSectionSection";
import { DeflectionSection } from "./DeflectionSection";

// ---------------------------------------------------------------------------
// Spinner SVG icon
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <svg
      className="animate-spin h-4 w-4 text-[var(--muted-foreground)]"
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
// Status bar shown at the bottom of the form
// ---------------------------------------------------------------------------

function StatusBar() {
  const isCalculating = useBeamStore((s) => s.isCalculating);
  const calculationError = useBeamStore((s) => s.calculationError);
  const results = useBeamStore((s) => s.results);

  if (isCalculating) {
    return (
      <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
        <Spinner />
        Berechnung läuft...
      </div>
    );
  }

  if (calculationError) {
    return (
      <div className="flex items-start gap-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 rounded-md px-3 py-2">
        <span className="shrink-0 font-bold">Fehler:</span>
        <span className="break-all">{calculationError}</span>
      </div>
    );
  }

  if (results) {
    return (
      <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
        <span aria-hidden="true">✓</span>
        Ergebnis bereit
      </div>
    );
  }

  return null;
}

// ---------------------------------------------------------------------------
// Main form component
// ---------------------------------------------------------------------------

export function InputForm() {
  const { triggerCalculation } = useCalculation();
  const setDirty = useProjectStore((s) => s.setDirty);

  // Grab state fields that should trigger recalculation when they change.
  // We use a stable selector that serialises the relevant state into a string
  // so useEffect's dependency comparison works correctly.
  const ecModus = useBeamStore((s) => s.ecModus);
  const sprungmass = useBeamStore((s) => s.sprungmass);
  const spannweiten = useBeamStore((s) => s.spannweiten);
  const lasten = useBeamStore((s) => s.lasten);
  const materialgruppe = useBeamStore((s) => s.materialgruppe);
  const activeVariant = useBeamStore((s) => s.activeVariant);
  const variants = useBeamStore((s) => s.variants);
  const deflection = useBeamStore((s) => s.deflection);

  // Track whether this is the initial render to avoid triggering a calculation
  // immediately on mount before the user has done anything.
  const isFirstRender = useRef(true);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    // Any form change marks the position as dirty (unsaved changes)
    setDirty(true);
    triggerCalculation();
  }, [
    ecModus,
    sprungmass,
    // Use JSON to create a stable primitive comparison for objects/arrays
    // eslint-disable-next-line react-hooks/exhaustive-deps
    JSON.stringify(spannweiten),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    JSON.stringify(lasten),
    materialgruppe,
    activeVariant,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    JSON.stringify(variants),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    JSON.stringify(deflection),
    setDirty,
    triggerCalculation,
  ]);

  const handleManualCalculate = () => {
    triggerCalculation();
  };

  return (
    <div className="space-y-4">
      {/* Calculation mode toggle at the top */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-[var(--foreground)]">
          Durchlaufträger-Berechnung
        </h1>
        <CalculationModeToggle />
      </div>

      {/* Form sections */}
      <SystemSection />
      <LoadsSection />
      <CrossSectionSection />
      <DeflectionSection />

      {/* Bottom bar: status + manual trigger */}
      <div className="flex items-center justify-between gap-4 pt-2">
        <StatusBar />

        <button
          type="button"
          onClick={handleManualCalculate}
          className="ml-auto shrink-0 rounded-md bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90 active:opacity-80 transition-opacity"
        >
          Berechnen
        </button>
      </div>
    </div>
  );
}
