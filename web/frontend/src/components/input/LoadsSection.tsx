/**
 * LoadsSection – the full loads table with:
 *  - Table header
 *  - One LoadRow per load case
 *  - "+ Last hinzufügen" button (max 5 loads)
 *  - NKL (Nutzungsklasse) selector – applies to all loads simultaneously
 *  - Eigengewicht checkbox – activates self-weight for the first permanent load
 */

import { useBeamStore } from "@/stores/useBeamStore";
import { LoadRow } from "./LoadRow";

const NKL_OPTIONS = [
  { value: 1, label: "NKL 1 – trocken" },
  { value: 2, label: "NKL 2 – feucht" },
  { value: 3, label: "NKL 3 – nass" },
];

export function LoadsSection() {
  const lasten = useBeamStore((s) => s.lasten);
  const addLoad = useBeamStore((s) => s.addLoad);
  const updateLoad = useBeamStore((s) => s.updateLoad);

  // NKL is stored on each load; we read from the first one as the "global" value
  const currentNkl = lasten[0]?.nkl ?? 1;

  // Eigengewicht flag lives on the first permanent load entry
  const firstGLoad = lasten.find((l) => l.lastfall === "g");
  const eigengewichtActive = firstGLoad?.eigengewicht ?? false;

  const handleNklChange = (nkl: number) => {
    // Apply the new NKL to every load case
    lasten.forEach((_, i) => updateLoad(i, "nkl", nkl));
  };

  const handleEigengewichtToggle = (checked: boolean) => {
    // Find the index of the first "g" load and toggle eigengewicht
    const idx = lasten.findIndex((l) => l.lastfall === "g");
    if (idx !== -1) {
      updateLoad(idx, "eigengewicht", checked);
    }
  };

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Einwirkungen</h2>

        {/* NKL selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-[var(--muted-foreground)] whitespace-nowrap">
            Nutzungsklasse
          </label>
          <select
            value={currentNkl}
            onChange={(e) => handleNklChange(Number(e.target.value))}
            className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            {NKL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loads table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-[var(--border)]">
              <th className="text-left py-2 pr-2 font-medium text-[var(--muted-foreground)] w-44">
                Lastfall
              </th>
              <th className="text-left py-2 pr-2 font-medium text-[var(--muted-foreground)] w-32">
                Wert
              </th>
              <th className="text-left py-2 pr-2 font-medium text-[var(--muted-foreground)]">
                Kategorie
              </th>
              <th className="text-left py-2 pr-2 font-medium text-[var(--muted-foreground)] w-36">
                Kommentar
              </th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {lasten.map((_, i) => (
              <LoadRow
                key={i}
                index={i}
                canDelete={lasten.length > 1}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Bottom row: add button + eigengewicht checkbox */}
      <div className="flex items-center justify-between pt-1">
        <button
          type="button"
          onClick={addLoad}
          disabled={lasten.length >= 5}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md border border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <span className="text-base leading-none">+</span>
          Last hinzufügen
        </button>

        {/* Eigengewicht only shown if there is a permanent (g) load */}
        {lasten.some((l) => l.lastfall === "g") && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={eigengewichtActive}
              onChange={(e) => handleEigengewichtToggle(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--border)] accent-[var(--primary)]"
            />
            <span className="text-sm text-[var(--foreground)]">
              Eigengewicht Träger einbeziehen
            </span>
          </label>
        )}
      </div>
    </section>
  );
}
