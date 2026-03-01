/**
 * LastkombinationenCard – collapsible section showing all load combinations.
 *
 * Two tabs are shown (ULS = GZT, SLS = GZG). Each tab lists every combination
 * with its LaTeX formula, kmod/kdef value, Ed load value and a "maßgebend" badge
 * for the governing combination.
 *
 * The API supplies `lastfallkombinationen` (ULS) and `gzg_lastfallkombinationen`
 * (SLS) as `Record<string, unknown>`.
 *
 * Per combination entry shape (ULS):
 *   latex      – LaTeX formula string (includes $…$ delimiters)
 *   latex_ed   – optional alternative LaTeX for Ed load
 *   wert       – numeric combination value [kN/m]
 *   Ed         – design load Ed [kN/m]
 *   kmod       – kmod value (ULS only)
 *   kdef       – kdef value (SLS only)
 *   massgebend – boolean: true if this combination governs
 *   typ        – optional SLS combination type label
 */

import { useState } from "react";
import katex from "katex";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Kombination {
  latex: string;
  latex_ed?: string;
  wert: number;
  Ed?: number;
  kmod?: number;
  kdef?: number;
  massgebend: boolean;
  typ?: string;
}

interface Props {
  lastfallkombinationen: Record<string, unknown> | null;
  gzgLastfallkombinationen: Record<string, unknown> | null;
}

type ActiveTab = "gzt" | "gzg";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Strip outer $…$ or $$…$$ delimiters before passing to KaTeX.
 * The API always supplies single-dollar wrapped display formulae.
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

function renderKatex(latex: string): string {
  try {
    return katex.renderToString(stripDelimiters(latex), {
      throwOnError: false,
      displayMode: true,
      strict: false, // Accept Unicode chars like ² from backend LaTeX
    });
  } catch {
    return `<code style="font-size:0.8em">${latex}</code>`;
  }
}

// ---------------------------------------------------------------------------
// KaTeX formula component
// ---------------------------------------------------------------------------

function KatexFormula({ latex }: { latex: string }) {
  return (
    <div
      className="overflow-x-auto text-sm"
      dangerouslySetInnerHTML={{ __html: renderKatex(latex) }}
    />
  );
}

// ---------------------------------------------------------------------------
// Single combination row
// ---------------------------------------------------------------------------

interface KombinationRowProps {
  name: string;
  combo: Kombination;
}

function KombinationRow({ name, combo }: KombinationRowProps) {
  const isMassgebend = combo.massgebend === true;
  const modFactor = combo.kmod ?? combo.kdef;

  return (
    <div
      className={[
        "rounded-md border p-3 space-y-2 transition-colors",
        isMassgebend
          ? "border-[var(--primary)] bg-[var(--primary)]/5"
          : "border-[var(--border)] bg-[var(--muted)]/20",
      ].join(" ")}
    >
      {/* Name row + badges – key is LaTeX so render via KaTeX */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="text-xs text-[var(--muted-foreground)] break-all"
          dangerouslySetInnerHTML={{
            __html: (() => {
              try {
                return katex.renderToString(name, {
                  throwOnError: false,
                  displayMode: false,
                  strict: false,
                });
              } catch {
                return name;
              }
            })(),
          }}
        />
        {isMassgebend && (
          <span className="inline-flex items-center rounded-full bg-[var(--primary)] px-2 py-0.5 text-xs font-medium text-white">
            maßgebend
          </span>
        )}
        {combo.typ && (
          <span className="inline-flex items-center rounded-full bg-[var(--muted)] px-2 py-0.5 text-xs text-[var(--muted-foreground)]">
            {combo.typ}
          </span>
        )}
      </div>

      {/* LaTeX formula */}
      <div className="rounded-sm bg-[var(--muted)]/30 px-2 py-1 overflow-x-auto">
        <KatexFormula latex={combo.latex} />
      </div>

      {/* Numeric summary row */}
      <div className="flex flex-wrap gap-4 text-xs text-[var(--muted-foreground)]">
        {combo.Ed != null && (
          <span>
            <span className="font-medium text-[var(--foreground)]">
              E<sub>d</sub>
            </span>{" "}
            = {combo.Ed.toFixed(2)} kN/m
          </span>
        )}
        {combo.wert != null && combo.Ed == null && (
          <span>
            <span className="font-medium text-[var(--foreground)]">Wert</span>{" "}
            = {combo.wert.toFixed(2)} kN/m
          </span>
        )}
        {modFactor != null && (
          <span>
            <span className="font-medium text-[var(--foreground)]">
              {combo.kmod != null ? "k_mod" : "k_def"}
            </span>{" "}
            = {modFactor.toFixed(2)}
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab panel for one set of combinations
// ---------------------------------------------------------------------------

interface TabPanelProps {
  combinations: Record<string, unknown>;
  emptyLabel: string;
}

function TabPanel({ combinations, emptyLabel }: TabPanelProps) {
  const entries = Object.entries(combinations) as [string, Kombination][];

  if (entries.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-[var(--muted-foreground)] italic">
        {emptyLabel}
      </p>
    );
  }

  return (
    <div className="space-y-2 mt-3">
      {entries.map(([name, combo]) => (
        <KombinationRow key={name} name={name} combo={combo} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main collapsible component
// ---------------------------------------------------------------------------

export function LastkombinationenCard({
  lastfallkombinationen,
  gzgLastfallkombinationen,
}: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("gzt");

  const hasGzt =
    lastfallkombinationen != null &&
    Object.keys(lastfallkombinationen).length > 0;
  const hasGzg =
    gzgLastfallkombinationen != null &&
    Object.keys(gzgLastfallkombinationen).length > 0;

  if (!hasGzt && !hasGzg) return null;

  return (
    <div className="rounded-lg border border-[var(--border)] overflow-hidden">
      {/* Collapse toggle header */}
      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[var(--muted)]/40 transition-colors"
        aria-expanded={isOpen}
      >
        <span className="text-sm font-semibold text-[var(--foreground)]">
          Lastkombinationen
        </span>
        <svg
          className={`h-4 w-4 text-[var(--muted-foreground)] transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* Collapsible body */}
      {isOpen && (
        <div className="border-t border-[var(--border)] px-4 pb-4">
          {/* Tabs */}
          <div className="flex gap-1 mt-3 rounded-lg bg-[var(--muted)]/50 p-1">
            <TabButton
              active={activeTab === "gzt"}
              onClick={() => setActiveTab("gzt")}
              label="GZT (ULS)"
              disabled={!hasGzt}
            />
            <TabButton
              active={activeTab === "gzg"}
              onClick={() => setActiveTab("gzg")}
              label="GZG (SLS)"
              disabled={!hasGzg}
            />
          </div>

          {/* Tab content */}
          {activeTab === "gzt" && (
            <TabPanel
              combinations={lastfallkombinationen ?? {}}
              emptyLabel="Keine GZT-Kombinationen vorhanden."
            />
          )}
          {activeTab === "gzg" && (
            <TabPanel
              combinations={gzgLastfallkombinationen ?? {}}
              emptyLabel="Keine GZG-Kombinationen vorhanden."
            />
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab button helper
// ---------------------------------------------------------------------------

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  label: string;
  disabled?: boolean;
}

function TabButton({ active, onClick, label, disabled }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={[
        "flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
        active
          ? "bg-[var(--background)] text-[var(--foreground)] shadow-sm"
          : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
        disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
      ].join(" ")}
    >
      {label}
    </button>
  );
}
