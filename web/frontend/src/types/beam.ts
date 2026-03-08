/**
 * TypeScript interfaces matching the API schema at web/api/schemas/calculation.py.
 *
 * Unit conventions (identical to the Python side):
 *   - Span lengths (spannweiten):  [m]
 *   - Load values (wert):          [kN/m²]  – float in frontend, converted to string by API
 *   - Cross-section dimensions:    [mm]  (breite_qs, hoehe_qs)
 *   - Deflection denominators:     dimensionless (l / value, e.g. 300 → l/300)
 *   - Pre-camber (w_c):            [mm]
 */

// ---------------------------------------------------------------------------
// Load case
// ---------------------------------------------------------------------------

export interface LoadCase {
  /** Load type identifier: "g" (permanent), "s" (snow), "w" (wind), "p" (imposed) */
  lastfall: string;
  /** Load value [kN/m²] – numeric in frontend, converted to string by API to_snapshot() */
  wert: number;
  /** Load category label – must match DB values exactly (e.g. "Nutzlast Kat. A: Wohnraum") */
  kategorie: string;
  /** Optional comment shown in results */
  kommentar: string;
  /** Nutzungsklasse (service class): 1, 2, or 3 */
  nkl: number;
  /** True if self-weight of the beam shall be added to this permanent load (g-Lastfall only) */
  eigengewicht: boolean;
}

// ---------------------------------------------------------------------------
// Cross-section variant
// ---------------------------------------------------------------------------

export interface CrossSectionVariant {
  /** Material type, e.g. "Nadelholz", "Laubholz", "Brettschichtholz" */
  typ: string;
  /** Strength class, e.g. "C24", "GL24h" */
  festigkeitsklasse: string;
  /** Cross-section width b [mm] */
  breite: number;
  /** Cross-section height h [mm] */
  hoehe: number;
}

// ---------------------------------------------------------------------------
// Deflection limits (SLS / GZG)
// ---------------------------------------------------------------------------

export type DeflectionSituation = "Allgemein" | "Überhöht" | "Eigene Werte";

export interface DeflectionLimits {
  /** Selected preset or custom mode */
  situation: DeflectionSituation;
  /** Instantaneous deflection limit denominator: l / w_inst  (e.g. 300 → l/300) */
  w_inst: number;
  /** Final deflection limit denominator: l / w_fin */
  w_fin: number;
  /** Net final deflection limit denominator: l / w_net_fin */
  w_net_fin: number;
  /** Pre-camber Δ₀ [mm] – subtracted when computing δ_netto */
  w_c: number;
}

// ---------------------------------------------------------------------------
// Deflection presets (EC5 / DIN EN 1995 recommended values)
// ---------------------------------------------------------------------------

export const DEFLECTION_PRESETS: Record<
  Exclude<DeflectionSituation, "Eigene Werte">,
  Omit<DeflectionLimits, "situation" | "w_c">
> = {
  /** Standard case without pre-camber – common default for most beams */
  Allgemein: { w_inst: 300, w_fin: 200, w_net_fin: 300 },
  /** Beams with pre-camber – tighter limits for better appearance */
  Überhöht: { w_inst: 200, w_fin: 150, w_net_fin: 250 },
};

// ---------------------------------------------------------------------------
// Span configuration (UI helper, not sent directly to API)
// ---------------------------------------------------------------------------

export interface SpanConfig {
  /** Number of interior spans: 1–5 */
  feldanzahl: number;
  /** Whether a left cantilever exists */
  kragarmLinks: boolean;
  /** Whether a right cantilever exists */
  kragarmRechts: boolean;
  /** Lengths keyed by field name, e.g. {"feld_1": 5.0, "kragarm_links": 1.5} [m] */
  spannweiten: Record<string, number>;
}

// ---------------------------------------------------------------------------
// API Request (matches CalculationRequest Pydantic schema exactly)
// ---------------------------------------------------------------------------

export interface CalculationRequest {
  /** Tributary / influence width e [m] – multiplied with all load values */
  sprungmass: number;
  /** Field lengths as {field_key: length_in_m} */
  spannweiten: Record<string, number>;
  /** List of load cases */
  lasten: {
    lastfall: string;
    wert: number;
    kategorie: string;
    kommentar: string;
    nkl: number;
    eigengewicht: boolean;
  }[];
  /** Cross-section and material properties */
  querschnitt: {
    materialgruppe: string;
    typ: string;
    festigkeitsklasse: string;
    nkl: number;
    /** Width [mm] */
    breite_qs: number;
    /** Height [mm] */
    hoehe_qs: number;
  };
  /** SLS / GZG deflection limit parameters */
  gebrauchstauglichkeit: {
    /** l / w_inst limit */
    w_inst: number;
    /** l / w_fin limit */
    w_fin: number;
    /** l / w_net_fin limit */
    w_net_fin: number;
    /** Pre-camber Δ₀ [mm] */
    w_c: number;
  };
  /** Calculation mode flags */
  berechnungsmodus: {
    /** True → EC pattern-load method; False → full-load quick method */
    ec_modus: boolean;
  };
}

// ---------------------------------------------------------------------------
// Support reactions (Auflagerkräfte)
// ---------------------------------------------------------------------------

export interface AuflagerKraefte {
  /** Support labels ["A", "B", "C", ...] from left to right */
  labels: string[];
  /** x-positions of supports along the beam [m] */
  x_positionen: number[];
  /** Max ULS design reactions per support [N] – convert to kN for display */
  gzt_design: number[];
  /** Max SLS characteristic reactions per support [N] – convert to kN for display */
  gzg_charakteristisch: number[];
}

// ---------------------------------------------------------------------------
// API Response (matches CalculationResponse Pydantic schema)
// ---------------------------------------------------------------------------

export interface CalculationResponse {
  /** ULS load combinations (GZT / Lastfallkombinationen) – null when not computed */
  lastfallkombinationen: Record<string, unknown> | null;
  /** SLS load combinations (GZG / GZG_Lastfallkombinationen) – null when not computed */
  gzg_lastfallkombinationen: Record<string, unknown> | null;
  /** FEM section forces (Schnittgroessen dict) – null when not computed */
  schnittgroessen: Record<string, unknown> | null;
  /** EC5 design check results (bending, shear, deflection) – null when not computed */
  ec5_nachweise: Record<string, unknown> | null;
  /** Support reactions (Auflagerkräfte) – null when not computed (e.g. deflection-only mode) */
  auflagerkraefte: AuflagerKraefte | null;
}

// ---------------------------------------------------------------------------
// EC5 result helpers (typed subsets of ec5_nachweise entries)
// ---------------------------------------------------------------------------

export interface EC5Nachweis {
  /** LaTeX-formatted formula string for display */
  latex: string;
  /** True if the design check is satisfied (η ≤ 1.0) */
  erfuellt: boolean;
  /** Utilisation ratio η = design value / resistance value */
  ausnutzung: number;
  [key: string]: unknown;
}
