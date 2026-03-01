/**
 * DeflectionSection – SLS (GZG) deflection limit inputs.
 *
 * Three modes:
 *  - Allgemein:    preset l/300 / l/200 / l/300 (read-only display)
 *  - Überhöht:     preset l/200 / l/150 / l/250 (read-only display)
 *  - Eigene Werte: user-editable number inputs for the denominators
 *
 * Pre-camber w_c [mm] is always editable.
 *
 * Denominators are stored as integers (e.g. 300 means l/300).
 */

import { useState, useEffect } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import { DEFLECTION_PRESETS } from "@/types/beam";
import type { DeflectionSituation } from "@/types/beam";

const inputCls =
  "w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]";

const labelCls = "text-sm font-medium text-[var(--foreground)]";
const mutedLabelCls = "text-xs text-[var(--muted-foreground)]";

const SITUATIONS: DeflectionSituation[] = ["Allgemein", "Überhöht", "Eigene Werte"];

// Deflection field metadata for rendering the three limit rows
const DEFLECTION_FIELDS: Array<{
  field: "w_inst" | "w_fin" | "w_net_fin";
  label: string;
  description: string;
}> = [
  {
    field: "w_inst",
    label: "w_inst",
    description: "Sofortdurchbiegung",
  },
  {
    field: "w_fin",
    label: "w_fin",
    description: "Enddurchbiegung",
  },
  {
    field: "w_net_fin",
    label: "w_net,fin",
    description: "Netto-Enddurchbiegung",
  },
];

export function DeflectionSection() {
  const deflection = useBeamStore((s) => s.deflection);
  const setDeflectionSituation = useBeamStore((s) => s.setDeflectionSituation);
  const setDeflectionValue = useBeamStore((s) => s.setDeflectionValue);

  const isCustom = deflection.situation === "Eigene Werte";

  // Raw strings for custom denominator inputs
  const [rawValues, setRawValues] = useState({
    w_inst: String(deflection.w_inst),
    w_fin: String(deflection.w_fin),
    w_net_fin: String(deflection.w_net_fin),
    w_c: String(deflection.w_c),
  });

  // Sync raw strings when situation changes (preset applies new values)
  useEffect(() => {
    setRawValues({
      w_inst: String(deflection.w_inst),
      w_fin: String(deflection.w_fin),
      w_net_fin: String(deflection.w_net_fin),
      w_c: String(deflection.w_c),
    });
  }, [deflection.situation, deflection.w_inst, deflection.w_fin, deflection.w_net_fin, deflection.w_c]);

  const handleDenominatorChange = (
    field: "w_inst" | "w_fin" | "w_net_fin",
    raw: string
  ) => {
    setRawValues((prev) => ({ ...prev, [field]: raw }));
    const num = parseInt(raw, 10);
    if (!isNaN(num) && num > 0) {
      setDeflectionValue(field, num);
    }
  };

  const handleWcChange = (raw: string) => {
    setRawValues((prev) => ({ ...prev, w_c: raw }));
    const num = parseFloat(raw.replace(",", "."));
    if (!isNaN(num) && num >= 0) {
      setDeflectionValue("w_c", num);
    }
  };

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Durchbiegungsgrenzen (GZG)</h2>

        {/* Situation selector */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-[var(--muted-foreground)] whitespace-nowrap">
            Situation
          </label>
          <select
            value={deflection.situation}
            onChange={(e) =>
              setDeflectionSituation(e.target.value as DeflectionSituation)
            }
            className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
          >
            {SITUATIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Deflection limit rows */}
      <div className="space-y-3">
        {DEFLECTION_FIELDS.map(({ field, label, description }) => {
          const denominator = deflection[field];
          return (
            <div key={field} className="grid grid-cols-3 items-center gap-4">
              {/* Label column */}
              <div>
                <p className={labelCls}>
                  {/* EC5-style notation, e.g. w_net,fin */}
                  <span className="font-mono text-sm">{label}</span>
                </p>
                <p className={mutedLabelCls}>{description}</p>
              </div>

              {/* Limit value column */}
              <div className="flex items-center gap-2">
                {isCustom ? (
                  <>
                    <span className="text-sm text-[var(--muted-foreground)]">L /</span>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      value={rawValues[field]}
                      onChange={(e) => handleDenominatorChange(field, e.target.value)}
                      onBlur={() =>
                        setRawValues((prev) => ({
                          ...prev,
                          [field]: String(deflection[field]),
                        }))
                      }
                      className={inputCls}
                    />
                  </>
                ) : (
                  <span className="text-sm font-medium bg-[var(--muted)] px-3 py-1.5 rounded-md border border-[var(--border)] w-full">
                    L / {denominator}
                  </span>
                )}
              </div>

              {/* Preview column: show fraction representation */}
              <div>
                {!isCustom && (
                  <span className={mutedLabelCls}>
                    Aus Preset:{" "}
                    {deflection.situation !== "Eigene Werte" &&
                      DEFLECTION_PRESETS[deflection.situation]?.[field]}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--border)]" />

      {/* Pre-camber w_c */}
      <div className="grid grid-cols-3 items-center gap-4">
        <div>
          <p className={labelCls}>
            <span className="font-mono text-sm">w_c</span>
          </p>
          <p className={mutedLabelCls}>Überhöhung</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            inputMode="decimal"
            value={rawValues.w_c}
            onChange={(e) => handleWcChange(e.target.value)}
            onBlur={() =>
              setRawValues((prev) => ({ ...prev, w_c: String(deflection.w_c) }))
            }
            className={inputCls}
          />
          <span className="text-sm text-[var(--muted-foreground)] whitespace-nowrap">mm</span>
        </div>
        <p className={mutedLabelCls}>Δ₀ – immer editierbar</p>
      </div>
    </section>
  );
}
