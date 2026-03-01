/**
 * Zustand store – single source of truth for all beam form state.
 *
 * Design decisions:
 *  - 3 cross-section variants; only the activeVariant is sent to the API.
 *  - Loads array: 1–5 entries, enforced by addLoad / removeLoad guards.
 *  - Spans dict is kept in sync with feldanzahl + cantilever flags so that
 *    deleted fields are never sent to the backend.
 *  - buildRequest() produces exactly the JSON the API expects (field names
 *    match CalculationRequest Pydantic schema in web/api/schemas/calculation.py).
 */

import { create } from "zustand";
import type {
  LoadCase,
  CrossSectionVariant,
  DeflectionSituation,
  DeflectionLimits,
  CalculationRequest,
  CalculationResponse,
} from "@/types/beam";
import { DEFLECTION_PRESETS } from "@/types/beam";

// ---------------------------------------------------------------------------
// Store shape
// ---------------------------------------------------------------------------

interface BeamState {
  // ---- Calculation mode ----
  /** True → EC pattern-load method (slower, more accurate); False → full-load quick */
  ecModus: boolean;

  // ---- System geometry ----
  /** Tributary / influence width e [m] */
  sprungmass: number;
  /** Number of interior spans: 1–5 */
  feldanzahl: number;
  /** Left cantilever flag */
  kragarmLinks: boolean;
  /** Right cantilever flag */
  kragarmRechts: boolean;
  /**
   * Span lengths keyed by field name [m].
   * Keys are automatically kept in sync with feldanzahl + cantilever flags.
   * Example: { kragarm_links: 1.5, feld_1: 5.0, feld_2: 4.0, kragarm_rechts: 1.2 }
   */
  spannweiten: Record<string, number>;

  // ---- Loads ----
  /** 1–5 load cases */
  lasten: LoadCase[];

  // ---- Cross-section ----
  /** Material group selected in the DB, e.g. "Balken" */
  materialgruppe: string;
  /** Which of the 3 variants is currently active (1-indexed) */
  activeVariant: 1 | 2 | 3;
  /** Three parallel variants – allows quick comparison without re-entering data */
  variants: [CrossSectionVariant, CrossSectionVariant, CrossSectionVariant];

  // ---- Deflection limits (SLS / GZG) ----
  deflection: DeflectionLimits;

  // ---- Results ----
  results: CalculationResponse | null;
  isCalculating: boolean;
  calculationError: string | null;

  // ---- Actions: calculation mode ----
  setEcModus: (v: boolean) => void;

  // ---- Actions: geometry ----
  setSprungmass: (v: number) => void;
  setFeldanzahl: (n: number) => void;
  setKragarmLinks: (v: boolean) => void;
  setKragarmRechts: (v: boolean) => void;
  setSpannweite: (key: string, value: number) => void;

  // ---- Actions: loads ----
  addLoad: () => void;
  removeLoad: (index: number) => void;
  updateLoad: (
    index: number,
    field: keyof LoadCase,
    value: LoadCase[keyof LoadCase]
  ) => void;

  // ---- Actions: cross-section ----
  setMaterialgruppe: (v: string) => void;
  setActiveVariant: (v: 1 | 2 | 3) => void;
  updateVariant: (
    index: 0 | 1 | 2,
    field: keyof CrossSectionVariant,
    value: string | number
  ) => void;

  // ---- Actions: deflection ----
  setDeflectionSituation: (s: DeflectionSituation) => void;
  setDeflectionValue: (
    field: keyof Omit<DeflectionLimits, "situation">,
    value: number
  ) => void;

  // ---- Actions: results ----
  setResults: (r: CalculationResponse | null) => void;
  setIsCalculating: (v: boolean) => void;
  setCalculationError: (e: string | null) => void;

  // ---- Computed ----
  /**
   * Assembles the API request body from current state.
   * Field names match CalculationRequest Pydantic schema exactly.
   */
  buildRequest: () => CalculationRequest;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const DEFAULT_VARIANT: CrossSectionVariant = {
  typ: "Nadelholz",
  festigkeitsklasse: "C24",
  breite: 120,
  hoehe: 240,
};

/**
 * Default load case added when the user clicks "Lastfall hinzufügen".
 * Category uses the exact DB label required by the validation service.
 */
function makeDefaultLoad(nkl: number): LoadCase {
  return {
    lastfall: "p",
    wert: 2.5,
    kategorie: "Nutzlast Kat. A: Wohnraum",
    kommentar: "",
    nkl,
    eigengewicht: false,
  };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useBeamStore = create<BeamState>((set, get) => ({
  // ---- Initial state ----
  ecModus: false,

  sprungmass: 1.0,
  feldanzahl: 1,
  kragarmLinks: false,
  kragarmRechts: false,
  spannweiten: { feld_1: 5.0 },

  lasten: [
    {
      lastfall: "g",
      wert: 7.41,
      kategorie: "Eigengewicht",
      kommentar: "",
      nkl: 1,
      eigengewicht: true,
    },
  ],

  materialgruppe: "Balken",
  activeVariant: 1,
  variants: [
    { ...DEFAULT_VARIANT },
    { ...DEFAULT_VARIANT },
    { ...DEFAULT_VARIANT },
  ],

  deflection: {
    situation: "Allgemein",
    // Preset values from DEFLECTION_PRESETS["Allgemein"]
    w_inst: 300,
    w_fin: 200,
    w_net_fin: 300,
    w_c: 0,
  },

  results: null,
  isCalculating: false,
  calculationError: null,

  // ---- Actions: calculation mode ----

  setEcModus: (v) => set({ ecModus: v }),

  // ---- Actions: geometry ----

  setSprungmass: (v) => set({ sprungmass: v }),

  /**
   * Update field count and rebuild the spannweiten dict.
   * Existing values for kept fields are preserved; new fields default to 5.0 m.
   */
  setFeldanzahl: (n) => {
    const clamped = Math.max(1, Math.min(5, n));
    const state = get();
    const newSpans: Record<string, number> = {};

    // Preserve cantilever values or set defaults
    if (state.kragarmLinks) {
      newSpans["kragarm_links"] = state.spannweiten["kragarm_links"] ?? 1.5;
    }
    for (let i = 1; i <= clamped; i++) {
      newSpans[`feld_${i}`] = state.spannweiten[`feld_${i}`] ?? 5.0;
    }
    if (state.kragarmRechts) {
      newSpans["kragarm_rechts"] = state.spannweiten["kragarm_rechts"] ?? 1.5;
    }

    set({ feldanzahl: clamped, spannweiten: newSpans });
  },

  setKragarmLinks: (v) => {
    const state = get();
    const newSpans = { ...state.spannweiten };
    if (v) {
      // Add left cantilever span (keep existing value if user toggled back)
      newSpans["kragarm_links"] = state.spannweiten["kragarm_links"] ?? 1.5;
    } else {
      delete newSpans["kragarm_links"];
    }
    set({ kragarmLinks: v, spannweiten: newSpans });
  },

  setKragarmRechts: (v) => {
    const state = get();
    const newSpans = { ...state.spannweiten };
    if (v) {
      newSpans["kragarm_rechts"] = state.spannweiten["kragarm_rechts"] ?? 1.5;
    } else {
      delete newSpans["kragarm_rechts"];
    }
    set({ kragarmRechts: v, spannweiten: newSpans });
  },

  setSpannweite: (key, value) =>
    set((s) => ({ spannweiten: { ...s.spannweiten, [key]: value } })),

  // ---- Actions: loads ----

  addLoad: () =>
    set((s) => {
      if (s.lasten.length >= 5) return s; // max 5 load cases
      const nkl = s.lasten[0]?.nkl ?? 1;
      return { lasten: [...s.lasten, makeDefaultLoad(nkl)] };
    }),

  removeLoad: (index) =>
    set((s) => {
      if (s.lasten.length <= 1) return s; // always keep at least one load
      return { lasten: s.lasten.filter((_, i) => i !== index) };
    }),

  updateLoad: (index, field, value) =>
    set((s) => {
      const lasten = [...s.lasten];
      lasten[index] = { ...lasten[index], [field]: value };
      return { lasten };
    }),

  // ---- Actions: cross-section ----

  setMaterialgruppe: (v) => set({ materialgruppe: v }),
  setActiveVariant: (v) => set({ activeVariant: v }),

  updateVariant: (index, field, value) =>
    set((s) => {
      const variants = [
        ...s.variants,
      ] as [CrossSectionVariant, CrossSectionVariant, CrossSectionVariant];
      variants[index] = { ...variants[index], [field]: value };
      return { variants };
    }),

  // ---- Actions: deflection ----

  setDeflectionSituation: (situation) =>
    set((s) => {
      if (situation === "Eigene Werte") {
        // Keep current numeric values; user will edit them manually
        return { deflection: { ...s.deflection, situation } };
      }
      // Apply preset values, preserve w_c
      const preset = DEFLECTION_PRESETS[situation];
      return {
        deflection: {
          ...s.deflection,
          situation,
          w_inst: preset.w_inst,
          w_fin: preset.w_fin,
          w_net_fin: preset.w_net_fin,
        },
      };
    }),

  setDeflectionValue: (field, value) =>
    set((s) => ({
      deflection: { ...s.deflection, [field]: value },
    })),

  // ---- Actions: results ----

  setResults: (r) => set({ results: r }),
  setIsCalculating: (v) => set({ isCalculating: v }),
  setCalculationError: (e) => set({ calculationError: e }),

  // ---- Build API request ----

  buildRequest: (): CalculationRequest => {
    const s = get();
    // Active variant is 1-indexed; variants array is 0-indexed
    const variant = s.variants[s.activeVariant - 1];

    // NKL for the cross-section is taken from the first load case (all loads
    // in one calculation share the same service class by convention in this app)
    const nkl = s.lasten[0]?.nkl ?? 1;

    return {
      sprungmass: s.sprungmass,
      spannweiten: s.spannweiten,
      lasten: s.lasten.map((l) => ({
        lastfall: l.lastfall,
        wert: l.wert,         // float – API to_snapshot() converts to string
        kategorie: l.kategorie,
        kommentar: l.kommentar,
        nkl: l.nkl,
        eigengewicht: l.eigengewicht,
      })),
      querschnitt: {
        materialgruppe: s.materialgruppe,
        typ: variant.typ,
        festigkeitsklasse: variant.festigkeitsklasse,
        nkl,
        breite_qs: variant.breite,   // [mm]
        hoehe_qs: variant.hoehe,     // [mm]
      },
      gebrauchstauglichkeit: {
        w_inst: s.deflection.w_inst,
        w_fin: s.deflection.w_fin,
        w_net_fin: s.deflection.w_net_fin,
        w_c: s.deflection.w_c,
      },
      berechnungsmodus: {
        ec_modus: s.ecModus,
      },
    };
  },
}));
