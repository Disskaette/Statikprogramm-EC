/**
 * SystemSection – beam geometry input:
 *  - Sprungmaß (tributary width / influence width e [m])
 *  - Feldanzahl stepper (1–5 interior spans)
 *  - Kragarm links / rechts checkboxes
 *  - Dynamic span inputs (one row per span + optional cantilever fields)
 */

import { useState } from "react";
import { useBeamStore } from "@/stores/useBeamStore";
import { parseGermanNumber } from "@/lib/format";

// ---------------------------------------------------------------------------
// Shared input style constants
// ---------------------------------------------------------------------------

const inputCls =
  "w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]";

const labelCls = "text-sm font-medium text-[var(--foreground)]";

// ---------------------------------------------------------------------------
// Sub-component: single span-length input row
// ---------------------------------------------------------------------------

interface SpanRowProps {
  spanKey: string;
  label: string;
  value: number;
  onChange: (key: string, value: number) => void;
}

function SpanRow({ spanKey, label, value, onChange }: SpanRowProps) {
  // Keep a local string state so partial/comma inputs don't trigger NaN store writes
  const [raw, setRaw] = useState(String(value));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const str = e.target.value;
    setRaw(str);
    const num = parseGermanNumber(str);
    if (!isNaN(num) && num > 0) {
      onChange(spanKey, num);
    }
  };

  // Sync displayed value when store resets from outside
  const handleBlur = () => {
    setRaw(String(value));
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-[var(--muted-foreground)] w-28 shrink-0">
        {label}
      </span>
      <div className="flex items-center gap-2 flex-1">
        <input
          type="text"
          inputMode="decimal"
          value={raw}
          onChange={handleChange}
          onBlur={handleBlur}
          className={inputCls}
        />
        <span className="text-sm text-[var(--muted-foreground)] shrink-0">m</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function SystemSection() {
  const sprungmass = useBeamStore((s) => s.sprungmass);
  const feldanzahl = useBeamStore((s) => s.feldanzahl);
  const kragarmLinks = useBeamStore((s) => s.kragarmLinks);
  const kragarmRechts = useBeamStore((s) => s.kragarmRechts);
  const spannweiten = useBeamStore((s) => s.spannweiten);

  const setSprungmass = useBeamStore((s) => s.setSprungmass);
  const setFeldanzahl = useBeamStore((s) => s.setFeldanzahl);
  const setKragarmLinks = useBeamStore((s) => s.setKragarmLinks);
  const setKragarmRechts = useBeamStore((s) => s.setKragarmRechts);
  const setSpannweite = useBeamStore((s) => s.setSpannweite);

  // Local raw string for Sprungmaß input
  const [rawSprungmass, setRawSprungmass] = useState(String(sprungmass));

  const handleSprungmassChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const str = e.target.value;
    setRawSprungmass(str);
    const num = parseGermanNumber(str);
    if (!isNaN(num) && num > 0) {
      setSprungmass(num);
    }
  };

  const handleSprungmassBlur = () => {
    setRawSprungmass(String(sprungmass));
  };

  // Build ordered list of span rows to display
  const spanRows: { key: string; label: string }[] = [];
  if (kragarmLinks) spanRows.push({ key: "kragarm_links", label: "Kragarm links" });
  for (let i = 1; i <= feldanzahl; i++) {
    spanRows.push({ key: `feld_${i}`, label: `Feld ${i}` });
  }
  if (kragarmRechts) spanRows.push({ key: "kragarm_rechts", label: "Kragarm rechts" });

  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-4 space-y-4">
      <h2 className="text-base font-semibold">System</h2>

      {/* Sprungmaß + Feldanzahl */}
      <div className="grid grid-cols-2 gap-4">
        {/* Sprungmaß */}
        <div className="space-y-1">
          <label className={labelCls}>Sprungmaß e</label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              inputMode="decimal"
              value={rawSprungmass}
              onChange={handleSprungmassChange}
              onBlur={handleSprungmassBlur}
              className={inputCls}
            />
            <span className="text-sm text-[var(--muted-foreground)] shrink-0">m</span>
          </div>
        </div>

        {/* Feldanzahl stepper */}
        <div className="space-y-1">
          <label className={labelCls}>Feldanzahl</label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setFeldanzahl(feldanzahl - 1)}
              disabled={feldanzahl <= 1}
              className="h-8 w-8 rounded-md border border-[var(--border)] bg-[var(--background)] text-sm font-bold hover:bg-[var(--muted)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              −
            </button>
            <span className="w-8 text-center text-sm font-semibold tabular-nums">
              {feldanzahl}
            </span>
            <button
              type="button"
              onClick={() => setFeldanzahl(feldanzahl + 1)}
              disabled={feldanzahl >= 5}
              className="h-8 w-8 rounded-md border border-[var(--border)] bg-[var(--background)] text-sm font-bold hover:bg-[var(--muted)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* Kragarm checkboxes */}
      <div className="flex items-center gap-6">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={kragarmLinks}
            onChange={(e) => setKragarmLinks(e.target.checked)}
            className="h-4 w-4 rounded border-[var(--border)] accent-[var(--primary)]"
          />
          <span className="text-sm text-[var(--foreground)]">Kragarm links</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={kragarmRechts}
            onChange={(e) => setKragarmRechts(e.target.checked)}
            className="h-4 w-4 rounded border-[var(--border)] accent-[var(--primary)]"
          />
          <span className="text-sm text-[var(--foreground)]">Kragarm rechts</span>
        </label>
      </div>

      {/* Dynamic span inputs */}
      <div className="space-y-2">
        <p className={labelCls}>Stützweiten</p>
        <div className="space-y-2">
          {spanRows.map(({ key, label }) => (
            <SpanRow
              key={key}
              spanKey={key}
              label={label}
              value={spannweiten[key] ?? 5.0}
              onChange={setSpannweite}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
