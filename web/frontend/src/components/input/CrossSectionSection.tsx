/**
 * CrossSectionSection – timber cross-section input with 3 parallel variants.
 *
 * Layout: Materialgruppe selector on top, then 3 variant columns side by side.
 * Each variant has:
 *  - Radio button to select it as the active variant
 *  - Typ dropdown (cascading from Materialgruppe)
 *  - Festigkeitsklasse dropdown (cascading from Typ)
 *  - Breite b [mm] input
 *  - Höhe h [mm] input
 *
 * Cascading rules:
 *  - When Materialgruppe changes → typ options update for all variants
 *  - When Typ changes → festigkeitsklasse options update for that variant
 *  - When new option lists load and current selection is not valid → auto-select first
 */

import { useEffect, useState } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import {
  useMaterialGroups,
  useMaterialTypes,
  useStrengthClasses,
} from "@/hooks/useMaterials";
import { cn } from "@/lib/utils";
import type { CrossSectionVariant } from "@/types/beam";

const inputCls =
  "w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]";

const labelCls = "text-xs font-medium text-[var(--muted-foreground)] mb-1";

// ---------------------------------------------------------------------------
// Single variant column
// ---------------------------------------------------------------------------

interface VariantColumnProps {
  /** 1-indexed variant number */
  number: 1 | 2 | 3;
  isActive: boolean;
  variant: CrossSectionVariant;
  materialgruppe: string;
  onSelect: () => void;
  onUpdate: (field: keyof CrossSectionVariant, value: string | number) => void;
}

function VariantColumn({
  number,
  isActive,
  variant,
  materialgruppe,
  onSelect,
  onUpdate,
}: VariantColumnProps) {
  const { data: types } = useMaterialTypes(materialgruppe);
  const { data: classes } = useStrengthClasses(materialgruppe, variant.typ);

  // Local raw strings for dimension inputs
  const [rawBreite, setRawBreite] = useState(String(variant.breite));
  const [rawHoehe, setRawHoehe] = useState(String(variant.hoehe));

  // Sync dimension raw strings when store changes externally
  useEffect(() => setRawBreite(String(variant.breite)), [variant.breite]);
  useEffect(() => setRawHoehe(String(variant.hoehe)), [variant.hoehe]);

  // Auto-select first Typ when material group changes and current Typ is not in list
  useEffect(() => {
    if (!types || types.length === 0) return;
    if (!types.includes(variant.typ)) {
      onUpdate("typ", types[0]);
    }
  }, [types, variant.typ, onUpdate]);

  // Auto-select first Festigkeitsklasse when Typ changes and current class is not in list
  useEffect(() => {
    if (!classes || classes.length === 0) return;
    if (!classes.includes(variant.festigkeitsklasse)) {
      onUpdate("festigkeitsklasse", classes[0]);
    }
  }, [classes, variant.festigkeitsklasse, onUpdate]);

  const handleDimensionChange = (
    raw: string,
    setRaw: (s: string) => void,
    field: "breite" | "hoehe"
  ) => {
    setRaw(raw);
    const num = parseInt(raw, 10);
    if (!isNaN(num) && num > 0) {
      onUpdate(field, num);
    }
  };

  return (
    <div
      className={cn(
        "flex-1 rounded-lg border p-3 space-y-3 cursor-pointer transition-all duration-150",
        isActive
          ? "border-[var(--primary)] bg-[var(--primary)]/5 shadow-sm"
          : "border-[var(--border)] hover:border-[var(--ring)]"
      )}
      onClick={onSelect}
    >
      {/* Header: radio + label */}
      <div className="flex items-center gap-2">
        <input
          type="radio"
          checked={isActive}
          onChange={onSelect}
          onClick={(e) => e.stopPropagation()}
          className="accent-[var(--primary)]"
          aria-label={`Variante ${number} auswählen`}
        />
        <span
          className={cn(
            "text-sm font-semibold",
            isActive ? "text-[var(--primary)]" : "text-[var(--foreground)]"
          )}
        >
          Variante {number}
        </span>
        {isActive && (
          <span className="text-xs text-[var(--primary)] ml-auto">aktiv</span>
        )}
      </div>

      {/* Typ */}
      <div>
        <p className={labelCls}>Typ</p>
        <select
          value={variant.typ}
          onChange={(e) => onUpdate("typ", e.target.value)}
          onClick={(e) => e.stopPropagation()}
          className={inputCls}
        >
          {(types ?? [variant.typ]).map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {/* Festigkeitsklasse */}
      <div>
        <p className={labelCls}>Festigkeitsklasse</p>
        <select
          value={variant.festigkeitsklasse}
          onChange={(e) => onUpdate("festigkeitsklasse", e.target.value)}
          onClick={(e) => e.stopPropagation()}
          className={inputCls}
        >
          {(classes ?? [variant.festigkeitsklasse]).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Dimensions: Breite + Höhe */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className={labelCls}>Breite b (mm)</p>
          <input
            type="number"
            min={1}
            step={1}
            value={rawBreite}
            onChange={(e) =>
              handleDimensionChange(e.target.value, setRawBreite, "breite")
            }
            onBlur={() => setRawBreite(String(variant.breite))}
            onClick={(e) => e.stopPropagation()}
            className={inputCls}
          />
        </div>
        <div>
          <p className={labelCls}>Höhe h (mm)</p>
          <input
            type="number"
            min={1}
            step={1}
            value={rawHoehe}
            onChange={(e) =>
              handleDimensionChange(e.target.value, setRawHoehe, "hoehe")
            }
            onBlur={() => setRawHoehe(String(variant.hoehe))}
            onClick={(e) => e.stopPropagation()}
            className={inputCls}
          />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main section component
// ---------------------------------------------------------------------------

export function CrossSectionSection() {
  const materialgruppe = useBeamStore((s) => s.materialgruppe);
  const activeVariant = useBeamStore((s) => s.activeVariant);
  const variants = useBeamStore((s) => s.variants);

  const setMaterialgruppe = useBeamStore((s) => s.setMaterialgruppe);
  const setActiveVariant = useBeamStore((s) => s.setActiveVariant);
  const updateVariant = useBeamStore((s) => s.updateVariant);

  const { data: groups } = useMaterialGroups();

  // Auto-select first group if current is not in list (should rarely happen)
  useEffect(() => {
    if (!groups || groups.length === 0) return;
    if (!groups.includes(materialgruppe)) {
      setMaterialgruppe(groups[0]);
    }
  }, [groups, materialgruppe, setMaterialgruppe]);

  const variantIndices: Array<0 | 1 | 2> = [0, 1, 2];

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Querschnitt</h2>

        {/* Materialgruppe selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-[var(--muted-foreground)] whitespace-nowrap">
            Materialgruppe
          </label>
          <select
            value={materialgruppe}
            onChange={(e) => setMaterialgruppe(e.target.value)}
            className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            {(groups ?? [materialgruppe]).map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Three variant columns */}
      <div className="flex gap-3">
        {variantIndices.map((i) => (
          <VariantColumn
            key={i}
            number={(i + 1) as 1 | 2 | 3}
            isActive={activeVariant === i + 1}
            variant={variants[i]}
            materialgruppe={materialgruppe}
            onSelect={() => setActiveVariant((i + 1) as 1 | 2 | 3)}
            onUpdate={(field, value) => updateVariant(i, field, value)}
          />
        ))}
      </div>
    </section>
  );
}
