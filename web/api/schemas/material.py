"""
Pydantic schemas for the materials endpoint.

These schemas mirror the dataclass structures defined in
backend/database/datenbank_holz.py and are used exclusively for
HTTP responses – the backend dataclasses are not exposed directly
so that future database schema changes do not break the API contract.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class MaterialProperties(BaseModel):
    """
    Characteristic and mean material strength/stiffness values.

    All strength values are in [N/mm²] as stored in the material database.
    Density values are in [kg/m³].
    """
    gruppe: str = Field(description="Material group, e.g. 'Balken'")
    typ: str = Field(description="Material type, e.g. 'Nadelholz'")
    festigkeitsklasse: str = Field(description="Strength class, e.g. 'C24'")

    # Characteristic strength values [N/mm²]
    fmyk: float = Field(description="Characteristic bending strength fm,k [N/mm²]")
    fc90k: float = Field(description="Characteristic compression strength perpendicular to grain fc,90,k [N/mm²]")
    fvk: float = Field(description="Characteristic shear strength fv,k [N/mm²]")

    # Stiffness [N/mm²]
    emodul: float = Field(description="Mean bending modulus of elasticity E0,mean [N/mm²]")

    # Density [kg/m³]
    roh: float = Field(description="Characteristic density rho_k [kg/m³]")
    roh_mean: float = Field(description="Mean density rho_mean [kg/m³]")

    # Partial safety factor (EC5 §2.4.1)
    gamma_m: float = Field(
        default=1.3,
        description="Material partial safety factor gamma_M [-] (EC5, NA DE)"
    )


class KmodData(BaseModel):
    """
    kmod values per load duration class and kdef for a given material type
    and service class (NKL).

    References: EC5 §3.1.3 (Table 3.1) and §2.3.2.2 (Table 3.2).
    """
    typ: str = Field(description="Material type identifier")
    nkl: int = Field(description="Service class (Nutzungsklasse): 1, 2, or 3")
    kmod_typ: dict[str, float] = Field(
        description="kmod values keyed by load duration class: "
                    "{'ständig': …, 'lang': …, 'mittel': …, 'kurz': …, "
                    "'kurz/sehr kurz': …, 'sehr kurz': …}"
    )
    kdef: float = Field(
        description="Deformation factor kdef [-] (EC5 Table 3.2)"
    )


class SiBeiwerte(BaseModel):
    """
    Combination coefficients (ψ values) and load duration class (KLED)
    for a specific load category.

    References: EC0 Annex A1 (Table A1.1), EC1 Part 1-1, NA DE.
    """
    kategorie: str = Field(description="Load category label (Lastkategorie)")
    psi0: float = Field(description="Combination value ψ₀ (EC0 6.10)")
    psi1: float = Field(description="Frequent value ψ₁ (EC0 6.10)")
    psi2: float = Field(description="Quasi-permanent value ψ₂ (EC0 6.10)")
    kled: str = Field(
        description="Load duration class (KLED): 'ständig', 'lang', "
                    "'mittel', 'kurz', 'sehr kurz'"
    )
    lastfall: str = Field(
        description="Parent load type: 'g', 's', 'w', 'p'"
    )


class LoadCategoryInfo(BaseModel):
    """
    Flat representation of a load category with its combination coefficients.
    Used by the frontend to populate dropdowns.
    """
    lastfall: str = Field(description="Parent load type identifier")
    kategorie: str = Field(description="Load category label")
    psi0: float
    psi1: float
    psi2: float
    kled: str
