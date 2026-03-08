"""
Pydantic schemas for the calculation endpoint.

These schemas describe the HTTP-layer data model that the React frontend
sends and receives.  They are deliberately kept separate from the backend's
internal "snapshot" dict format; a `to_snapshot()` method on
`CalculationRequest` handles the conversion.

Unit conventions (matching the legacy desktop frontend):
  - Lengths (spans, cross-section dimensions): user-facing in [m] / [mm]
  - Loads: [kN/m]
  - Cross-section: breite_qs / hoehe_qs in [mm]
  - E-modulus: [N/mm²]  (as stored in the material database)
  - I_y: [mm⁴]
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-schemas (building blocks)
# ---------------------------------------------------------------------------

class BerechnungsmodusSchema(BaseModel):
    """Calculation mode flags passed alongside the structural input."""
    ec_modus: bool = Field(
        default=False,
        description="True → EC-pattern load method (slower, more accurate); "
                    "False → full-load quick method"
    )


class LastSchema(BaseModel):
    """
    A single load case (Lastfall) as submitted by the frontend.

    The API accepts 'wert' as a FLOAT for a clean REST interface.
    The conversion to STRING (required by validation_service) happens
    in CalculationRequest.to_snapshot().
    """
    lastfall: str = Field(
        default="g",
        description="Load type identifier: 'g' (permanent), 's' (snow), "
                    "'w' (wind), 'p' (imposed)"
    )
    wert: float = Field(
        default=0.0,
        description="Load value [kN/m²] – converted to string internally"
    )
    kategorie: str = Field(
        default="Eigengewicht",
        description="Load category label from the material database "
                    "(e.g. 'Nutzlast Kat. A: Wohnraum')"
    )
    kommentar: str = Field(
        default="",
        description="Optional comment for this load case"
    )
    nkl: int = Field(
        default=1,
        description="Nutzungsklasse (service class): 1, 2, or 3"
    )
    eigengewicht: bool = Field(
        default=False,
        description="True if self-weight of the beam shall be added to this "
                    "permanent load (g-Lastfall only)"
    )


class QuerschnittSchema(BaseModel):
    """
    Cross-section and material data.

    Dimensions are in [mm], matching the existing snapshot convention used
    throughout the backend (breite_qs, hoehe_qs).
    """
    materialgruppe: str = Field(default="Balken", description="Material group, e.g. 'Balken'")
    typ: str = Field(default="Nadelholz", description="Material type, e.g. 'Nadelholz'")
    festigkeitsklasse: str = Field(default="C24", description="Strength class, e.g. 'C24'")
    nkl: int = Field(default=1, description="Nutzungsklasse (service class): 1, 2, or 3")
    breite_qs: float = Field(default=200, description="Cross-section width b [mm]")
    hoehe_qs: float = Field(default=300, description="Cross-section height h [mm]")


class GebrauchstauglichkeitSchema(BaseModel):
    """
    Serviceability limit state (SLS / GZG) deflection parameters.

    Limit fractions are interpreted as l / value by the backend
    (e.g. w_inst=300 means l/300).
    """
    w_inst: float = Field(
        default=300.0,
        description="Instantaneous deflection limit denominator (l / w_inst)"
    )
    w_fin: float = Field(
        default=200.0,
        description="Final deflection limit denominator (l / w_fin)"
    )
    w_net_fin: float = Field(
        default=150.0,
        description="Net final deflection limit denominator (l / w_net_fin)"
    )
    w_c: float = Field(
        default=0.0,
        description="Pre-camber Δ₀ [mm] – subtracted when computing δnetto"
    )


# ---------------------------------------------------------------------------
# Main request schema
# ---------------------------------------------------------------------------

class CalculationRequest(BaseModel):
    """
    Full calculation request sent by the React frontend to POST /api/calculate.

    The method `to_snapshot()` converts this into the internal dict format
    expected by OrchestratorService.process_snapshot().
    """
    sprungmass: float = Field(
        description="Tributary width / influence width e [m] – applied to all "
                    "loads as a multiplication factor (spreads line loads)"
    )
    spannweiten: dict[str, float] = Field(
        description="Field lengths as {field_key: length_in_m}, "
                    "e.g. {'feld_1': 5.0, 'feld_2': 4.5}"
    )
    lasten: list[LastSchema] = Field(
        description="List of load cases"
    )
    querschnitt: QuerschnittSchema = Field(
        description="Cross-section and material properties"
    )
    gebrauchstauglichkeit: GebrauchstauglichkeitSchema = Field(
        default_factory=GebrauchstauglichkeitSchema,
        description="SLS / GZG deflection limit parameters"
    )
    berechnungsmodus: BerechnungsmodusSchema = Field(
        default_factory=BerechnungsmodusSchema,
        description="Calculation mode flags"
    )
    calculation_mode: str = Field(
        default="full",
        description="'full' for complete calculation, "
                    "'only_deflection_check' to reuse existing Schnittgroessen"
    )

    def to_snapshot(self, db) -> dict[str, Any]:
        """
        Convert this request into the legacy snapshot dict format.

        IMPORTANT invariants (enforced here to avoid silent failures):
          - 'wert' for each load must be a STRING (validation_service checks
            `wert not in (None, "")` before attempting float conversion)
          - 'sprungmass' must be a STRING (same reason)
          - I_y and W_y are computed from dimensions b and h [mm]
          - E-modulus is looked up from the material database
        """
        qs = self.querschnitt
        b = qs.breite_qs   # [mm]
        h = qs.hoehe_qs    # [mm]

        # Second moment of area and section modulus for a rectangular section
        # EC5 §6.1 – these are needed by the SLS check (nachweis_ec5.py)
        I_y = (b * h**3) / 12.0   # [mm⁴]
        W_y = I_y / (h / 2.0)     # [mm³]

        # E-modulus from material database [N/mm²]
        E_mean = db.get_emodul(
            qs.materialgruppe, qs.typ, qs.festigkeitsklasse
        )

        # Build the cross-section dict expected by the backend
        querschnitt_snap: dict[str, Any] = {
            "materialgruppe": qs.materialgruppe,
            "typ": qs.typ,
            "festigkeitsklasse": qs.festigkeitsklasse,
            "nkl": qs.nkl,
            "breite_qs": b,
            "hoehe_qs": h,
            "I_y": I_y,
            "W_y": W_y,
            "E": E_mean,
        }

        # Convert each load – 'wert' MUST be a string (see validation_service)
        lasten_snap = []
        for last in self.lasten:
            lasten_snap.append({
                "lastfall": last.lastfall,
                "wert": str(last.wert),         # STRING – critical!
                "kategorie": last.kategorie,
                "kommentar": last.kommentar,
                "nkl": last.nkl,
                "eigengewicht": last.eigengewicht,
            })

        # sprungmass is used as a FLOAT multiplier in lastenkombination.py line 75:
        #   wert = float(last["wert"]) * e
        # validation_service only checks it's not negative, so float is fine.
        sprungmass_val = self.sprungmass

        gzt = self.gebrauchstauglichkeit
        # Backend (nachweis_ec5.py) expects keys with '_grenz' suffix:
        #   gebrauchstauglichkeit.get("w_inst_grenz") etc.
        # The API-facing field names (w_inst, w_fin, …) are mapped here.
        gebrauchstauglichkeit_snap: dict[str, Any] = {
            "w_inst_grenz": gzt.w_inst,
            "w_fin_grenz": gzt.w_fin,
            "w_net_fin_grenz": gzt.w_net_fin,
            "w_c": gzt.w_c,
        }

        snapshot: dict[str, Any] = {
            "sprungmass": sprungmass_val,
            "spannweiten": self.spannweiten,
            "lasten": lasten_snap,
            "querschnitt": querschnitt_snap,
            "gebrauchstauglichkeit": gebrauchstauglichkeit_snap,
            "berechnungsmodus": self.berechnungsmodus.model_dump(),
            "calculation_mode": self.calculation_mode,
        }
        return snapshot


# ---------------------------------------------------------------------------
# Fast-path deflection-only request
# ---------------------------------------------------------------------------

class DeflectionCheckRequest(BaseModel):
    """
    Fast-path request for recalculating only the EC5 deflection checks.

    The caller must supply the already-computed Schnittgroessen and
    Lastfallkombinationen from a previous full calculation so that the
    backend can skip the FEM step.
    """
    base_snapshot: CalculationRequest = Field(
        description="The structural input parameters (same as CalculationRequest)"
    )
    schnittgroessen: dict[str, Any] = Field(
        description="Previously computed section forces (Schnittgroessen dict)"
    )
    lastfallkombinationen: dict[str, Any] = Field(
        description="Previously computed ULS load combinations"
    )
    gzg_lastfallkombinationen: dict[str, Any] = Field(
        description="Previously computed SLS load combinations"
    )

    def to_snapshot(self, db) -> dict[str, Any]:
        """Build a deflection-only snapshot from the cached results."""
        snapshot = self.base_snapshot.to_snapshot(db)
        snapshot["calculation_mode"] = "only_deflection_check"
        snapshot["Schnittgroessen"] = self.schnittgroessen
        snapshot["Lastfallkombinationen"] = self.lastfallkombinationen
        snapshot["GZG_Lastfallkombinationen"] = self.gzg_lastfallkombinationen
        return snapshot


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CalculationResponse(BaseModel):
    """
    Response body for POST /api/calculate.

    All fields are typed as Any because the backend returns deeply nested
    dicts with LaTeX strings, floats, and booleans whose exact structure
    depends on the number of load cases and fields.  Strong typing of the
    response bodies is deferred to a later iteration once the frontend
    contract is stable.
    """
    lastfallkombinationen: Optional[dict[str, Any]] = Field(
        default=None,
        description="ULS load combinations (GZT / Lastfallkombinationen)"
    )
    gzg_lastfallkombinationen: Optional[dict[str, Any]] = Field(
        default=None,
        description="SLS load combinations (GZG / GZG_Lastfallkombinationen)"
    )
    schnittgroessen: Optional[dict[str, Any]] = Field(
        default=None,
        description="FEM section forces (Schnittgroessen dict)"
    )
    ec5_nachweise: Optional[dict[str, Any]] = Field(
        default=None,
        description="EC5 design check results (bending, shear, deflection)"
    )
    auflagerkraefte: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Support reactions: labels [A,B,C,...], x_positionen [m], "
            "gzt_design [N], gzg_charakteristisch [N]"
        )
    )
