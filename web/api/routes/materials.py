"""
Materials API routes.

All endpoints are read-only and backed by the singleton datenbank_holz_class
instance.  The material database is loaded once at startup (see main.py
lifespan) so all responses are effectively in-memory lookups.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from web.api.deps import DBDep
from web.api.schemas.material import (
    KmodData,
    LoadCategoryInfo,
    MaterialProperties,
    SiBeiwerte,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Material hierarchy
# ---------------------------------------------------------------------------

@router.get(
    "/groups",
    response_model=list[str],
    summary="List all material groups",
    description="Returns the ordered list of material groups available in the "
                "timber database (e.g. ['Balken', 'BSP']).",
)
async def get_groups(db: DBDep) -> list[str]:
    """GET /api/materials/groups"""
    return db.get_materialgruppen()


@router.get(
    "/types",
    response_model=list[str],
    summary="List material types for a group",
)
async def get_types(
    db: DBDep,
    gruppe: str = Query(description="Material group name, e.g. 'Balken'"),
) -> list[str]:
    """GET /api/materials/types?gruppe=Balken"""
    result = db.get_typen(gruppe)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No material types found for group '{gruppe}'",
        )
    return result


@router.get(
    "/strength-classes",
    response_model=list[str],
    summary="List strength classes for a material type",
)
async def get_strength_classes(
    db: DBDep,
    gruppe: str = Query(description="Material group, e.g. 'Balken'"),
    typ: str = Query(description="Material type, e.g. 'Nadelholz'"),
) -> list[str]:
    """GET /api/materials/strength-classes?gruppe=Balken&typ=Nadelholz"""
    result = db.get_festigkeitsklassen(gruppe, typ)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No strength classes found for group='{gruppe}', type='{typ}'",
        )
    return result


@router.get(
    "/properties",
    response_model=dict[str, Any],
    summary="Get characteristic material properties and kdef",
    description=(
        "Returns fmyk, fvk, E-modulus, density, gamma_M and kdef for the "
        "requested material + service class combination."
    ),
)
async def get_properties(
    db: DBDep,
    gruppe: str = Query(description="Material group"),
    typ: str = Query(description="Material type"),
    festigkeitsklasse: str = Query(description="Strength class, e.g. 'C24'"),
    nkl: int = Query(description="Service class (Nutzungsklasse): 1, 2, or 3"),
) -> dict[str, Any]:
    """GET /api/materials/properties?gruppe=...&typ=...&festigkeitsklasse=...&nkl=..."""
    result = db.get_bemessungsdaten(gruppe, typ, festigkeitsklasse, nkl)
    if result.get("fmyk") is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No material data found for gruppe='{gruppe}', typ='{typ}', "
                f"festigkeitsklasse='{festigkeitsklasse}', nkl={nkl}"
            ),
        )
    return result


# ---------------------------------------------------------------------------
# kmod values
# ---------------------------------------------------------------------------

@router.get(
    "/kmod",
    response_model=KmodData,
    summary="Get kmod values for a material type and service class",
    description=(
        "Returns all load-duration-class kmod values and the creep factor "
        "kdef for the given material type and Nutzungsklasse (NKL). "
        "Reference: EC5 §3.1.3 Table 3.1 and Table 3.2."
    ),
)
async def get_kmod(
    db: DBDep,
    typ: str = Query(description="Material type, e.g. 'Nadelholz'"),
    nkl: int = Query(description="Service class (Nutzungsklasse): 1, 2, or 3"),
) -> KmodData:
    """GET /api/materials/kmod?typ=Nadelholz&nkl=1"""
    entry = db.get_kmod(typ, nkl)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No kmod data found for typ='{typ}', nkl={nkl}",
        )
    return KmodData(
        typ=entry.typ,
        nkl=entry.nkl,
        kmod_typ=entry.kmod_typ,
        kdef=entry.kdef,
    )


# ---------------------------------------------------------------------------
# Load types and categories
# ---------------------------------------------------------------------------

@router.get(
    "/load-types",
    response_model=list[str],
    summary="List available load types in database order",
    description=(
        "Returns load type identifiers in the order they appear in the "
        "database (e.g. ['g', 's', 'w', 'p']).  Use this to build "
        "load-type dropdowns in the correct sequence."
    ),
)
async def get_load_types(db: DBDep) -> list[str]:
    """GET /api/materials/load-types"""
    return db.get_sortierte_lastfaelle()


@router.get(
    "/load-categories",
    response_model=list[str],
    summary="List load categories for a load type",
)
async def get_load_categories(
    db: DBDep,
    lastfall: str = Query(description="Load type identifier, e.g. 'p'"),
) -> list[str]:
    """GET /api/materials/load-categories?lastfall=p"""
    result = db.get_kategorien_fuer_lastfall(lastfall)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No load categories found for lastfall='{lastfall}'",
        )
    return result


@router.get(
    "/si-beiwerte",
    response_model=SiBeiwerte,
    summary="Get combination coefficients (ψ values) for a load category",
    description=(
        "Returns ψ₀, ψ₁, ψ₂, KLED and the parent load type for the "
        "requested load category.  Reference: EC0 Annex A1, NA DE."
    ),
)
async def get_si_beiwerte(
    db: DBDep,
    kategorie: str = Query(
        description="Load category label, e.g. 'Nutzlast Kat. A: Wohnraum'"
    ),
) -> SiBeiwerte:
    """GET /api/materials/si-beiwerte?kategorie=..."""
    entry = db.get_si_beiwerte(kategorie)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No combination coefficients found for kategorie='{kategorie}'",
        )
    return SiBeiwerte(
        kategorie=entry.kategorie,
        psi0=entry.psi0,
        psi1=entry.psi1,
        psi2=entry.psi2,
        kled=entry.kled,
        lastfall=entry.lastfall,
    )
