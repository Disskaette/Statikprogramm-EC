/**
 * LoadRow – a single row in the loads table.
 *
 * Cascading dropdowns:
 *  1. Lastfall (load type: g, p, s, w)  → triggers category reload
 *  2. Kategorie (load category)          → must match DB strings exactly!
 *
 * When Lastfall changes, we auto-select the first available Kategorie.
 */

import { useEffect, useState } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import { useLoadCategories } from "@/hooks/useMaterials";
import type { LoadCase } from "@/types/beam";
import { parseGermanNumber } from "@/lib/format";

// ---------------------------------------------------------------------------
// Human-readable labels for load type identifiers
// ---------------------------------------------------------------------------

const LASTFALL_LABELS: Record<string, string> = {
  g: "Ständig (g)",
  p: "Veränderlich (p)",
  s: "Schnee (s)",
  w: "Wind (w)",
};

// All known load type identifiers (shown as fallback if API is unavailable)
const ALL_LASTFAELLE = ["g", "p", "s", "w"];

const inputCls =
  "w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface LoadRowProps {
  index: number;
  canDelete: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LoadRow({ index, canDelete }: LoadRowProps) {
  const load = useBeamStore((s) => s.lasten[index]);
  const updateLoad = useBeamStore((s) => s.updateLoad);
  const removeLoad = useBeamStore((s) => s.removeLoad);

  // Local raw string for the numeric wert input
  const [rawWert, setRawWert] = useState(String(load.wert));

  // Fetch categories for the currently selected lastfall
  const { data: categories } = useLoadCategories(load.lastfall);

  // When categories change (because lastfall changed) and the current
  // kategorie is no longer in the list, auto-select the first available one.
  useEffect(() => {
    if (!categories || categories.length === 0) return;
    if (!categories.includes(load.kategorie)) {
      updateLoad(index, "kategorie", categories[0]);
    }
  }, [categories, load.kategorie, index, updateLoad]);

  // Sync raw wert string if the store value changes externally
  useEffect(() => {
    setRawWert(String(load.wert));
  }, [load.wert]);

  const handleLastfallChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLastfall = e.target.value as LoadCase["lastfall"];
    updateLoad(index, "lastfall", newLastfall);
    // kategorie will be reset by the useEffect above once categories reload
  };

  const handleWertChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const str = e.target.value;
    setRawWert(str);
    const num = parseGermanNumber(str);
    if (!isNaN(num)) {
      updateLoad(index, "wert", num);
    }
  };

  const handleWertBlur = () => {
    setRawWert(String(load.wert));
  };

  return (
    <tr className="border-b border-[var(--border)] last:border-0">
      {/* Lastfall */}
      <td className="py-2 pr-2">
        <select
          value={load.lastfall}
          onChange={handleLastfallChange}
          className={inputCls}
        >
          {ALL_LASTFAELLE.map((lf) => (
            <option key={lf} value={lf}>
              {LASTFALL_LABELS[lf] ?? lf}
            </option>
          ))}
        </select>
      </td>

      {/* Wert [kN/m²] */}
      <td className="py-2 pr-2">
        <div className="flex items-center gap-1">
          <input
            type="text"
            inputMode="decimal"
            value={rawWert}
            onChange={handleWertChange}
            onBlur={handleWertBlur}
            className={inputCls}
          />
          <span className="text-xs text-[var(--muted-foreground)] whitespace-nowrap shrink-0">
            kN/m²
          </span>
        </div>
      </td>

      {/* Kategorie – cascading, depends on lastfall */}
      <td className="py-2 pr-2">
        <select
          value={load.kategorie}
          onChange={(e) => updateLoad(index, "kategorie", e.target.value)}
          className={inputCls}
        >
          {(categories ?? [load.kategorie]).map((cat) => (
            <option key={cat} value={cat}>
              {cat}
            </option>
          ))}
        </select>
      </td>

      {/* Kommentar */}
      <td className="py-2 pr-2">
        <input
          type="text"
          value={load.kommentar}
          onChange={(e) => updateLoad(index, "kommentar", e.target.value)}
          placeholder="optional"
          className={inputCls}
        />
      </td>

      {/* Delete button */}
      <td className="py-2 text-center">
        <button
          type="button"
          onClick={() => removeLoad(index)}
          disabled={!canDelete}
          title="Last entfernen"
          className="h-7 w-7 rounded text-[var(--muted-foreground)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-20 disabled:cursor-not-allowed transition-colors text-base leading-none"
        >
          ×
        </button>
      </td>
    </tr>
  );
}
