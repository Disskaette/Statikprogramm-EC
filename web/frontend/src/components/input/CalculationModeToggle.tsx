/**
 * Toggle between the two calculation modes:
 *  - Schnell (Volllast): full load applied to all fields, fast
 *  - EC-Kombinatorik: EC0 pattern loading, slower but normative
 */

import { useBeamStore } from "@/stores/useBeamStore";
import { cn } from "@/lib/utils";

interface ModeOption {
  label: string;
  value: boolean;
}

const MODES: ModeOption[] = [
  { label: "Schnell (Volllast)", value: false },
  { label: "EC-Kombinatorik", value: true },
];

export function CalculationModeToggle() {
  const ecModus = useBeamStore((s) => s.ecModus);
  const setEcModus = useBeamStore((s) => s.setEcModus);

  return (
    <div className="flex gap-1 p-1 rounded-lg bg-[var(--muted)] border border-[var(--border)] w-fit">
      {MODES.map((mode) => {
        const isActive = ecModus === mode.value;
        return (
          <button
            key={String(mode.value)}
            type="button"
            onClick={() => setEcModus(mode.value)}
            className={cn(
              "px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-150",
              isActive
                ? "bg-[var(--background)] text-[var(--foreground)] shadow-sm border border-[var(--border)]"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            )}
          >
            {mode.value ? "🔬 " : "⚡ "}
            {mode.label}
          </button>
        );
      })}
    </div>
  );
}
