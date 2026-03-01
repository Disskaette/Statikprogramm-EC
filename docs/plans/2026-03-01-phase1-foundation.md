# Phase 1: Foundation – Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up the complete FastAPI + React foundation with the first working calculation endpoint and basic UI shell.

**Architecture:** FastAPI wraps the existing Python backend as a thin REST API. React SPA with Vite + Tailwind + shadcn/ui serves as the frontend. Multi-stage Docker build for production. The existing `backend/` directory is imported directly – zero changes to calculation code.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Pydantic v2, React 19, TypeScript 5, Vite 6, Tailwind CSS 4, shadcn/ui, KaTeX, Plotly.js, Zustand, TanStack React Query

---

### Task 1: Create Python requirements and web API directory structure

**Files:**
- Create: `requirements-web.txt`
- Create: `web/__init__.py`
- Create: `web/api/__init__.py`
- Create: `web/api/main.py`
- Create: `web/api/routes/__init__.py`
- Create: `web/api/schemas/__init__.py`
- Create: `web/api/deps.py`

**Step 1: Create requirements-web.txt**

```
# Web Framework
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
pydantic>=2.0.0
python-multipart>=0.0.9

# Existing backend dependencies
numpy>=2.0.0
pandas>=2.0.0
matplotlib>=3.9.0
Pillow>=10.0.0
openpyxl>=3.1.0

# CORS
# (included in fastapi)
```

**Step 2: Create directory structure**

```bash
mkdir -p web/api/routes web/api/schemas
touch web/__init__.py web/api/__init__.py web/api/routes/__init__.py web/api/schemas/__init__.py
```

**Step 3: Create FastAPI main app (`web/api/main.py`)**

```python
"""
FastAPI application entry point.
Wraps the existing backend calculation engine as a REST API.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from web.api.deps import get_db, get_project_manager
from web.api.routes import calculation, materials, projects

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared resources on startup."""
    logger.info("Initializing database and project manager...")
    # Pre-load the material database (singleton)
    db = get_db()
    logger.info(f"Material database loaded: {len(db.get_materialgruppen())} groups")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Statik-Tool API",
    description="REST API for structural beam calculation (EC5/EC0/EC1)",
    version="1.0.0",
    lifespan=lifespan,
    root_path="",  # Set to "/statik" when behind nginx
)

# CORS for local development (frontend on :5173, backend on :8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(calculation.router, prefix="/api", tags=["calculation"])
app.include_router(materials.router, prefix="/api/materials", tags=["materials"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])


# Serve React frontend in production (built files in web/frontend/dist)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
```

**Step 4: Create dependencies (`web/api/deps.py`)**

```python
"""
Shared dependencies for FastAPI routes.
Singleton instances of backend services.
"""
import os
import sys
from functools import lru_cache
from pathlib import Path

# Ensure project root is in path so backend imports work
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database.datenbank_holz import datenbank_holz_class
from backend.project.project_manager import ProjectManager
from backend.service.orchestrator_service import OrchestratorService


@lru_cache()
def get_db() -> datenbank_holz_class:
    """Singleton material database instance."""
    return datenbank_holz_class()


@lru_cache()
def get_project_manager() -> ProjectManager:
    """Singleton project manager instance."""
    projects_root = os.environ.get("PROJEKTE_ROOT", None)
    if projects_root:
        return ProjectManager(projects_root=Path(projects_root))
    return ProjectManager()


def get_orchestrator() -> OrchestratorService:
    """New orchestrator instance per request (stateful with threading)."""
    return OrchestratorService()
```

**Step 5: Install dependencies and verify**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger"
pip install -r requirements-web.txt
```

**Step 6: Commit**

```bash
git add requirements-web.txt web/
git commit -m "feat: create FastAPI project structure and app entry point"
```

---

### Task 2: Create Pydantic schemas for calculation API

**Files:**
- Create: `web/api/schemas/calculation.py`
- Create: `web/api/schemas/material.py`

**Step 1: Create calculation schemas (`web/api/schemas/calculation.py`)**

```python
"""
Pydantic schemas for calculation request/response.
Mirrors the existing snapshot format used by OrchestratorService.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BerechnungsmodusSchema(BaseModel):
    ec_modus: bool = False


class LastSchema(BaseModel):
    lastfall: str = "g"
    wert: float = 0.0
    kategorie: str = "Eigengewicht"
    kommentar: str = ""
    nkl: int = Field(default=1, ge=1, le=3)
    eigengewicht: bool = False


class QuerschnittSchema(BaseModel):
    breite_qs: float = Field(default=200, gt=0, description="Width in mm")
    hoehe_qs: float = Field(default=300, gt=0, description="Height in mm")
    materialgruppe: str = "Balken"
    typ: str = "Nadelholz"
    festigkeitsklasse: str = "C24"


class GebrauchstauglichkeitSchema(BaseModel):
    situation: str = "Allgemein"
    w_c: float = Field(default=0.0, ge=0, description="Camber in mm")
    w_inst_grenz: float = Field(default=300, gt=0, description="w_inst limit: L/x")
    w_fin_grenz: float = Field(default=200, gt=0, description="w_fin limit: L/x")
    w_net_fin_grenz: float = Field(default=300, gt=0, description="w_net_fin limit: L/x")


class CalculationRequest(BaseModel):
    """
    Full calculation input. Mirrors the snapshot dict expected by
    OrchestratorService.process_snapshot().
    """
    sprungmass: float = Field(default=1.0, ge=0, description="Tributary width in m")
    berechnungsmodus: BerechnungsmodusSchema = BerechnungsmodusSchema()
    spannweiten: Dict[str, float] = Field(
        default={"feld_1": 5.0},
        description="Span dict: kragarm_links, feld_1..feld_5, kragarm_rechts"
    )
    lasten: List[LastSchema] = Field(
        default=[LastSchema(lastfall="g", wert=5.0, kategorie="Eigengewicht", eigengewicht=True)],
        min_length=1,
        max_length=10,
    )
    querschnitt: QuerschnittSchema = QuerschnittSchema()
    gebrauchstauglichkeit: GebrauchstauglichkeitSchema = GebrauchstauglichkeitSchema()
    anzeige_lastkombis: int = Field(default=1, ge=1, le=2)

    def to_snapshot(self, db) -> dict:
        """
        Convert Pydantic model to the legacy snapshot dict format
        expected by the backend OrchestratorService.
        """
        # Get material properties from database
        qs = self.querschnitt
        material = db.get_material(qs.materialgruppe, qs.typ, qs.festigkeitsklasse)
        e_modul = db.get_emodul(qs.materialgruppe, qs.typ, qs.festigkeitsklasse) or 11000

        # Calculate section properties
        b = qs.breite_qs  # mm
        h = qs.hoehe_qs   # mm
        I_y = (b * h**3) / 12       # mm⁴
        W_y = I_y / (h / 2)         # mm³

        snapshot = {
            "sprungmass": str(self.sprungmass),
            "berechnungsmodus": {"ec_modus": self.berechnungsmodus.ec_modus},
            "spannweiten": {k: v for k, v in self.spannweiten.items()},
            "lasten": [
                {
                    "lastfall": last.lastfall,
                    "wert": str(last.wert),
                    "kategorie": last.kategorie,
                    "kommentar": last.kommentar,
                    "nkl": last.nkl,
                    "eigengewicht": last.eigengewicht,
                }
                for last in self.lasten
            ],
            "querschnitt": {
                "breite_qs": b,
                "hoehe_qs": h,
                "I_y": I_y,
                "W_y": W_y,
                "materialgruppe": qs.materialgruppe,
                "typ": qs.typ,
                "festigkeitsklasse": qs.festigkeitsklasse,
                "E": e_modul,
            },
            "gebrauchstauglichkeit": {
                "situation": self.gebrauchstauglichkeit.situation,
                "w_c": self.gebrauchstauglichkeit.w_c,
                "w_inst_grenz": self.gebrauchstauglichkeit.w_inst_grenz,
                "w_fin_grenz": self.gebrauchstauglichkeit.w_fin_grenz,
                "w_net_fin_grenz": self.gebrauchstauglichkeit.w_net_fin_grenz,
            },
            "anzeige_lastkombis": self.anzeige_lastkombis,
            "calculation_mode": "full",
        }
        return snapshot


class DeflectionCheckRequest(BaseModel):
    """Request for deflection-only recalculation (when cross-section changes)."""
    snapshot: Dict[str, Any] = Field(
        description="Full snapshot with existing Lastfallkombinationen and Schnittgroessen"
    )
    querschnitt: QuerschnittSchema = QuerschnittSchema()
    gebrauchstauglichkeit: GebrauchstauglichkeitSchema = GebrauchstauglichkeitSchema()


class CalculationResponse(BaseModel):
    """Full calculation results from the backend."""
    lastfallkombinationen: Dict[str, Any] = {}
    gzg_lastfallkombinationen: Dict[str, Any] = {}
    schnittgroessen: Dict[str, Any] = {}
    ec5_nachweise: Dict[str, Any] = {}
    errors: List[str] = []
    success: bool = True
```

**Step 2: Create material schemas (`web/api/schemas/material.py`)**

```python
"""
Pydantic schemas for material database queries.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel


class MaterialProperties(BaseModel):
    fmyk: Optional[float] = None
    fvk: Optional[float] = None
    E: Optional[float] = None
    roh_mean: Optional[float] = None
    gamma_m: Optional[float] = None
    kdef: Optional[float] = None


class KmodData(BaseModel):
    typ: str
    nkl: int
    kmod_values: Dict[str, float]  # {"ständig": 0.6, "lang": 0.7, ...}
    kdef: float


class SiBeiwerte(BaseModel):
    kategorie: str
    psi0: float
    psi1: float
    psi2: float
    kled: str
    lastfall: str


class LoadCategoryInfo(BaseModel):
    lastfall: str
    categories: List[str]
```

**Step 3: Commit**

```bash
git add web/api/schemas/
git commit -m "feat: add Pydantic schemas for calculation and material APIs"
```

---

### Task 3: Create calculation API route

**Files:**
- Create: `web/api/routes/calculation.py`

**Step 1: Create the calculation route**

```python
"""
Calculation API endpoint.
Wraps OrchestratorService.process_snapshot() as a synchronous REST endpoint.
"""
import asyncio
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from web.api.deps import get_db, get_orchestrator
from web.api.schemas.calculation import (
    CalculationRequest,
    CalculationResponse,
    DeflectionCheckRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def run_calculation(snapshot: dict) -> dict:
    """
    Run the backend calculation in a thread and await the result.
    Converts the callback-based OrchestratorService to async/await.
    """
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    def callback(result=None, errors=None):
        if not future.done():
            if errors:
                loop.call_soon_threadsafe(future.set_result, {"errors": errors})
            else:
                loop.call_soon_threadsafe(future.set_result, {"result": result})

    orchestrator = get_orchestrator()
    # Reset state so debouncing doesn't skip our request
    orchestrator._last_hash = None
    orchestrator._last_time = 0
    orchestrator.process_snapshot(snapshot, callback)

    try:
        result = await asyncio.wait_for(future, timeout=60.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Calculation timed out after 60s")

    return result


@router.post("/calculate", response_model=CalculationResponse)
async def calculate(request: CalculationRequest):
    """
    Run a full structural calculation.

    Takes beam geometry, loads, cross-section, and serviceability parameters.
    Returns load combinations, section forces, and EC5 verification results
    including LaTeX formulas for display.
    """
    db = get_db()

    # Convert Pydantic model to legacy snapshot dict
    snapshot = request.to_snapshot(db)
    logger.info(f"Starting calculation: {len(request.lasten)} loads, "
                f"ec_modus={request.berechnungsmodus.ec_modus}")

    result = await run_calculation(snapshot)

    if "errors" in result and result["errors"]:
        return CalculationResponse(
            errors=result["errors"],
            success=False,
        )

    data = result.get("result", {})
    return CalculationResponse(
        lastfallkombinationen=data.get("Lastfallkombinationen", {}),
        gzg_lastfallkombinationen=data.get("GZG_Lastfallkombinationen", {}),
        schnittgroessen=data.get("Schnittgroessen", {}),
        ec5_nachweise=data.get("EC5_Nachweise", {}),
        success=True,
    )


@router.post("/calculate/deflection-only", response_model=CalculationResponse)
async def calculate_deflection_only(request: DeflectionCheckRequest):
    """
    Recalculate only EC5 deflection checks (fast path).
    Used when cross-section or serviceability limits change
    but loads and geometry stay the same.
    """
    snapshot = request.snapshot.copy()
    snapshot["calculation_mode"] = "only_deflection_check"

    # Update cross-section in snapshot
    qs = request.querschnitt
    b, h = qs.breite_qs, qs.hoehe_qs
    snapshot["querschnitt"] = {
        **snapshot.get("querschnitt", {}),
        "breite_qs": b,
        "hoehe_qs": h,
        "I_y": (b * h**3) / 12,
        "W_y": (b * h**3) / 12 / (h / 2),
        "materialgruppe": qs.materialgruppe,
        "typ": qs.typ,
        "festigkeitsklasse": qs.festigkeitsklasse,
    }
    snapshot["gebrauchstauglichkeit"] = request.gebrauchstauglichkeit.model_dump()

    result = await run_calculation(snapshot)

    if "errors" in result and result["errors"]:
        return CalculationResponse(errors=result["errors"], success=False)

    data = result.get("result", {})
    return CalculationResponse(
        lastfallkombinationen=data.get("Lastfallkombinationen", {}),
        gzg_lastfallkombinationen=data.get("GZG_Lastfallkombinationen", {}),
        schnittgroessen=data.get("Schnittgroessen", {}),
        ec5_nachweise=data.get("EC5_Nachweise", {}),
        success=True,
    )
```

**Step 2: Commit**

```bash
git add web/api/routes/calculation.py
git commit -m "feat: add /api/calculate endpoint wrapping OrchestratorService"
```

---

### Task 4: Create materials API route

**Files:**
- Create: `web/api/routes/materials.py`

**Step 1: Create the materials route**

```python
"""
Material database API endpoints.
Provides timber material properties, kmod values, and load categories
from the existing datenbank_holz.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from web.api.deps import get_db
from web.api.schemas.material import KmodData, MaterialProperties, SiBeiwerte

router = APIRouter()


@router.get("/groups", response_model=List[str])
async def get_material_groups():
    """Get all available material groups (e.g., 'Balken', 'BSH')."""
    db = get_db()
    return db.get_materialgruppen()


@router.get("/types", response_model=List[str])
async def get_material_types(gruppe: str = Query(..., description="Material group")):
    """Get material types for a group (e.g., 'Nadelholz', 'Laubholz')."""
    db = get_db()
    types = db.get_typen(gruppe)
    if not types:
        raise HTTPException(status_code=404, detail=f"No types found for group '{gruppe}'")
    return types


@router.get("/strength-classes", response_model=List[str])
async def get_strength_classes(
    gruppe: str = Query(..., description="Material group"),
    typ: str = Query(..., description="Material type"),
):
    """Get strength classes (e.g., 'C14', 'C24', 'GL24h')."""
    db = get_db()
    classes = db.get_festigkeitsklassen(gruppe, typ)
    if not classes:
        raise HTTPException(
            status_code=404,
            detail=f"No classes for gruppe='{gruppe}', typ='{typ}'"
        )
    return classes


@router.get("/properties", response_model=MaterialProperties)
async def get_material_properties(
    gruppe: str = Query(...),
    typ: str = Query(...),
    klasse: str = Query(..., alias="festigkeitsklasse"),
    nkl: int = Query(default=1, ge=1, le=3),
):
    """
    Get design-relevant material properties for a specific timber grade.
    Returns: fmyk, fvk, E, roh_mean, gamma_m, kdef
    """
    db = get_db()
    data = db.get_bemessungsdaten(gruppe, typ, klasse, nkl)
    if not data or all(v is None for v in data.values()):
        raise HTTPException(
            status_code=404,
            detail=f"No material data found for {gruppe}/{typ}/{klasse}/NKL{nkl}"
        )
    return MaterialProperties(**data)


@router.get("/kmod")
async def get_kmod_values(
    typ: str = Query(..., description="Material type (e.g., 'Nadelholz')"),
    nkl: int = Query(default=1, ge=1, le=3),
):
    """Get all kmod values for a material type and service class."""
    db = get_db()
    kmod = db.get_kmod(typ, nkl)
    if not kmod:
        raise HTTPException(status_code=404, detail=f"No kmod for typ='{typ}', nkl={nkl}")
    return KmodData(
        typ=kmod.typ,
        nkl=kmod.nkl,
        kmod_values=kmod.kmod_typ,
        kdef=kmod.kdef,
    )


@router.get("/load-types", response_model=List[str])
async def get_load_types():
    """Get sorted list of available load types (g, s, w, p, ...)."""
    db = get_db()
    return db.get_sortierte_lastfaelle()


@router.get("/load-categories", response_model=List[str])
async def get_load_categories(
    lastfall: str = Query(..., description="Load type (e.g., 'g', 's', 'w')"),
):
    """Get categories for a load type (e.g., 'Schneelast Kat. H' for 's')."""
    db = get_db()
    categories = db.get_kategorien_fuer_lastfall(lastfall)
    return categories


@router.get("/si-beiwerte", response_model=SiBeiwerte)
async def get_si_beiwerte(
    kategorie: str = Query(..., description="Load category"),
):
    """Get safety/combination factors (psi0, psi1, psi2, kled) for a category."""
    db = get_db()
    data = db.get_si_beiwerte(kategorie)
    if not data:
        raise HTTPException(status_code=404, detail=f"No SiBeiwerte for '{kategorie}'")
    return SiBeiwerte(
        kategorie=data.kategorie,
        psi0=data.psi0,
        psi1=data.psi1,
        psi2=data.psi2,
        kled=data.kled,
        lastfall=data.lastfall,
    )
```

**Step 2: Commit**

```bash
git add web/api/routes/materials.py
git commit -m "feat: add /api/materials endpoints for timber database queries"
```

---

### Task 5: Create projects API route (stub)

**Files:**
- Create: `web/api/routes/projects.py`

**Step 1: Create projects route (basic CRUD)**

```python
"""
Project management API endpoints.
Wraps the existing ProjectManager for CRUD operations.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from web.api.deps import get_project_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""


class PositionCreate(BaseModel):
    position_nummer: str = Field(..., min_length=1)
    position_name: str = "Neue Position"
    subfolder: str = ""


class ProjectInfo(BaseModel):
    uuid: str
    name: str
    path: str
    description: str = ""
    created: str = ""
    last_modified: str = ""
    position_count: int = 0


@router.get("", response_model=List[ProjectInfo])
async def list_projects():
    """List all projects for the current user."""
    pm = get_project_manager()
    projects = pm.list_projects()
    result = []
    for p in projects:
        result.append(ProjectInfo(
            uuid=p.get("uuid", ""),
            name=p.get("name", "Unknown"),
            path=str(p.get("path", "")),
            description=p.get("description", ""),
            created=p.get("created", ""),
            last_modified=p.get("last_modified", ""),
            position_count=len(p.get("positions", [])),
        ))
    return result


@router.post("", response_model=ProjectInfo)
async def create_project(data: ProjectCreate):
    """Create a new project."""
    pm = get_project_manager()
    try:
        project_path = pm.create_project(data.name, data.description)
        project_data = pm.open_project(project_path)
        return ProjectInfo(
            uuid=project_data.get("uuid", ""),
            name=project_data.get("name", data.name),
            path=str(project_path),
            description=data.description,
            created=project_data.get("created", ""),
            last_modified=project_data.get("last_modified", ""),
            position_count=0,
        )
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Project '{data.name}' already exists")


@router.get("/{project_id}/positions")
async def list_positions(project_id: str):
    """List all positions in a project."""
    pm = get_project_manager()
    # Find and open project by UUID
    for p in pm.list_projects():
        if p.get("uuid") == project_id:
            pm.open_project(Path(p["path"]))
            return pm.list_positions()
    raise HTTPException(status_code=404, detail="Project not found")


@router.post("/{project_id}/positions")
async def create_position(project_id: str, data: PositionCreate):
    """Create a new position in a project."""
    from backend.project.position_model import PositionModel

    pm = get_project_manager()
    for p in pm.list_projects():
        if p.get("uuid") == project_id:
            pm.open_project(Path(p["path"]))
            model = PositionModel(
                position_nummer=data.position_nummer,
                position_name=data.position_name,
            )
            pos_path = pm.create_position(model, data.subfolder)
            return {"path": str(pos_path), "model": model.to_dict()}
    raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id}/positions/{pos_path:path}")
async def get_position(project_id: str, pos_path: str):
    """Get a specific position's data."""
    pm = get_project_manager()
    for p in pm.list_projects():
        if p.get("uuid") == project_id:
            pm.open_project(Path(p["path"]))
            full_path = Path(p["path"]) / pos_path
            if not full_path.exists():
                raise HTTPException(status_code=404, detail="Position not found")
            model = pm.load_position(full_path)
            return model.to_dict()
    raise HTTPException(status_code=404, detail="Project not found")


@router.put("/{project_id}/positions/{pos_path:path}")
async def save_position(project_id: str, pos_path: str, data: Dict[str, Any]):
    """Save/update a position."""
    from backend.project.position_model import PositionModel

    pm = get_project_manager()
    for p in pm.list_projects():
        if p.get("uuid") == project_id:
            pm.open_project(Path(p["path"]))
            full_path = Path(p["path"]) / pos_path
            model = PositionModel.from_dict(data)
            pm.save_position(model, full_path)
            return {"status": "saved"}
    raise HTTPException(status_code=404, detail="Project not found")
```

**Step 2: Commit**

```bash
git add web/api/routes/projects.py
git commit -m "feat: add /api/projects CRUD endpoints wrapping ProjectManager"
```

---

### Task 6: Test FastAPI backend manually

**Step 1: Start the API server**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger"
python -m uvicorn web.api.main:app --reload --port 8000
```

**Step 2: Test health endpoint**

```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok","version":"1.0.0"}
```

**Step 3: Test materials endpoint**

```bash
curl http://localhost:8000/api/materials/groups
# Expected: ["Balken", "BSH", ...]

curl "http://localhost:8000/api/materials/types?gruppe=Balken"
# Expected: ["Nadelholz", "Laubholz"]

curl "http://localhost:8000/api/materials/strength-classes?gruppe=Balken&typ=Nadelholz"
# Expected: ["C14", "C16", "C18", "C24", ...]
```

**Step 4: Test calculation endpoint**

```bash
curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "sprungmass": 1.0,
    "berechnungsmodus": {"ec_modus": false},
    "spannweiten": {"feld_1": 5.0},
    "lasten": [{"lastfall": "g", "wert": 7.41, "kategorie": "Eigengewicht", "eigengewicht": true, "nkl": 1}],
    "querschnitt": {"breite_qs": 200, "hoehe_qs": 300, "materialgruppe": "Balken", "typ": "Nadelholz", "festigkeitsklasse": "C14"},
    "gebrauchstauglichkeit": {"situation": "Allgemein", "w_c": 0, "w_inst_grenz": 300, "w_fin_grenz": 200, "w_net_fin_grenz": 300}
  }'
# Expected: JSON with lastfallkombinationen, schnittgroessen, ec5_nachweise
```

**Step 5: Visit API docs**

Open http://localhost:8000/docs in browser - should show Swagger UI with all endpoints.

---

### Task 7: Scaffold React frontend project

**Step 1: Create React app with Vite**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger/web"
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Step 2: Install core dependencies**

```bash
npm install tailwindcss @tailwindcss/vite
npm install katex @types/katex
npm install plotly.js-dist-min react-plotly.js @types/react-plotly.js
npm install zustand
npm install @tanstack/react-query
npm install react-icons
npm install react-resizable-panels
npm install clsx tailwind-merge
```

**Step 3: Configure Tailwind CSS (`tailwind.config.ts`)**

Replace contents of `web/frontend/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        success: {
          DEFAULT: "var(--success)",
          foreground: "var(--success-foreground)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

**Step 4: Configure Vite (`vite.config.ts`)**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

**Step 5: Create CSS variables (`src/index.css`)**

```css
@import "tailwindcss";

@layer base {
  :root {
    --background: #ffffff;
    --foreground: #0a0a0a;
    --muted: #f5f5f5;
    --muted-foreground: #737373;
    --primary: #2563eb;
    --primary-foreground: #ffffff;
    --secondary: #f5f5f5;
    --secondary-foreground: #0a0a0a;
    --accent: #f5f5f5;
    --accent-foreground: #0a0a0a;
    --destructive: #ef4444;
    --destructive-foreground: #ffffff;
    --success: #22c55e;
    --success-foreground: #ffffff;
    --border: #e5e7eb;
    --input: #e5e7eb;
    --ring: #2563eb;
    --radius: 0.5rem;
  }

  .dark {
    --background: #1a1a1a;
    --foreground: #e5e5e5;
    --muted: #262626;
    --muted-foreground: #a3a3a3;
    --primary: #3b82f6;
    --primary-foreground: #ffffff;
    --secondary: #262626;
    --secondary-foreground: #e5e5e5;
    --accent: #333333;
    --accent-foreground: #e5e5e5;
    --destructive: #dc2626;
    --destructive-foreground: #ffffff;
    --success: #16a34a;
    --success-foreground: #ffffff;
    --border: #404040;
    --input: #404040;
    --ring: #3b82f6;
  }

  * {
    border-color: var(--border);
  }

  body {
    background-color: var(--background);
    color: var(--foreground);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
}

/* KaTeX theme integration */
.katex {
  color: var(--foreground) !important;
}

.katex-display {
  margin: 0.5em 0 !important;
}
```

**Step 6: Commit**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger"
git add web/frontend/
git commit -m "feat: scaffold React frontend with Vite, Tailwind, and core dependencies"
```

---

### Task 8: Create React app shell with theme and layout

**Files:**
- Create: `web/frontend/src/main.tsx`
- Create: `web/frontend/src/App.tsx`
- Create: `web/frontend/src/hooks/useTheme.ts`
- Create: `web/frontend/src/lib/api.ts`
- Create: `web/frontend/src/lib/cn.ts`
- Create: `web/frontend/src/components/Layout.tsx`
- Create: `web/frontend/src/components/ThemeToggle.tsx`

**Step 1: Create utility (`src/lib/cn.ts`)**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Step 2: Create API client (`src/lib/api.ts`)**

```typescript
const API_BASE = "/api";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) =>
    apiFetch<T>(path, { method: "DELETE" }),
};
```

**Step 3: Create theme hook (`src/hooks/useTheme.ts`)**

```typescript
import { useCallback, useEffect, useState } from "react";

type Theme = "light" | "dark";

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("statik-theme") as Theme;
      if (stored) return stored;
      return window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
    }
    return "dark";
  });

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    localStorage.setItem("statik-theme", theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return { theme, setTheme, toggleTheme };
}
```

**Step 4: Create ThemeToggle (`src/components/ThemeToggle.tsx`)**

```tsx
import { useTheme } from "@/hooks/useTheme";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm
                 bg-secondary text-secondary-foreground
                 hover:bg-accent transition-colors"
      title={theme === "dark" ? "Light Mode" : "Dark Mode"}
    >
      {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
    </button>
  );
}
```

**Step 5: Create Layout (`src/components/Layout.tsx`)**

```tsx
import { type ReactNode } from "react";
import { ThemeToggle } from "./ThemeToggle";

interface LayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export function Layout({ sidebar, children }: LayoutProps) {
  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Top bar */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b bg-background px-4">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold">📐 Statik-Tool</span>
          <span className="text-xs text-muted-foreground">v2.0 Web</span>
        </div>
        <ThemeToggle />
      </header>

      {/* Main content area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 shrink-0 overflow-y-auto border-r bg-muted/30">
          {sidebar}
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
```

**Step 6: Create App.tsx**

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "@/components/Layout";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Layout
        sidebar={
          <div className="p-4">
            <h2 className="text-sm font-semibold text-muted-foreground mb-3">
              Projekt-Explorer
            </h2>
            <p className="text-xs text-muted-foreground italic">
              Wird in Phase 5 implementiert
            </p>
          </div>
        }
      >
        <div className="flex h-full items-center justify-center">
          <div className="text-center space-y-4">
            <h1 className="text-3xl font-bold">🏗️ Statik-Tool v2.0</h1>
            <p className="text-muted-foreground">
              Durchlaufträger-Berechnung nach EC5
            </p>
            <p className="text-sm text-muted-foreground">
              Willkommen! Die Eingabemaske wird in Phase 2 implementiert.
            </p>
          </div>
        </div>
      </Layout>
    </QueryClientProvider>
  );
}

export default App;
```

**Step 7: Update main.tsx**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

**Step 8: Test it**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger/web/frontend"
npm run dev
# Open http://localhost:5173 - should show the app shell with dark/light toggle
```

**Step 9: Commit**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger"
git add web/frontend/src/
git commit -m "feat: create React app shell with theme system, layout, and API client"
```

---

### Task 9: Create Dockerfile and docker-compose for development

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.dev.yml`
- Create: `.dockerignore`

**Step 1: Create `.dockerignore`**

```
.git/
.venv/
__pycache__/
*.pyc
.pytest_cache/
node_modules/
web/frontend/node_modules/
web/frontend/dist/
.DS_Store
Projekte/
Bilder/
*.xlsx
.claude/
```

**Step 2: Create `Dockerfile`**

```dockerfile
# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

# Stage 2: Python backend + serve built frontend
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy backend (existing calculation engine)
COPY backend/ ./backend/

# Copy web API layer
COPY web/api/ ./web/api/
COPY web/__init__.py ./web/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./web/frontend/dist

EXPOSE 8000

CMD ["uvicorn", "web.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create `docker-compose.dev.yml`**

```yaml
version: "3.8"
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: ""  # Full build
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - ./web/api:/app/web/api
      - ./Projekte:/data/projekte
    environment:
      - PROJEKTE_ROOT=/data/projekte
    command: uvicorn web.api.main:app --reload --host 0.0.0.0 --port 8000

  frontend:
    image: node:22-alpine
    working_dir: /app
    ports:
      - "5173:5173"
    volumes:
      - ./web/frontend:/app
      - /app/node_modules  # Anonymous volume for node_modules
    command: sh -c "npm install && npm run dev -- --host"
    environment:
      - VITE_API_URL=http://localhost:8000
```

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.dev.yml .dockerignore
git commit -m "feat: add Dockerfile and dev docker-compose for web application"
```

---

### Task 10: Verify end-to-end – API + Frontend running together

**Step 1: Start backend**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger"
python -m uvicorn web.api.main:app --reload --port 8000
```

**Step 2: Start frontend (in separate terminal)**

```bash
cd "/Users/maximilianstark/Library/Mobile Documents/com~apple~CloudDocs/Dokumente/Programmierzeug/Durchlaufträger/web/frontend"
npm run dev
```

**Step 3: Verify in browser**

1. Open http://localhost:5173 → Should show app shell with dark theme
2. Click "☀️ Light" → Should switch to light mode
3. Open http://localhost:8000/docs → Should show Swagger API docs
4. Test API proxy: Open browser console at :5173, run:
   ```javascript
   fetch('/api/health').then(r => r.json()).then(console.log)
   // Expected: {status: "ok", version: "1.0.0"}
   ```
5. Test materials API from browser console:
   ```javascript
   fetch('/api/materials/groups').then(r => r.json()).then(console.log)
   // Expected: ["Balken", ...]
   ```

**Step 4: Final commit for Phase 1**

```bash
git add -A
git commit -m "feat: Phase 1 complete - FastAPI + React foundation with working API"
```

---

## Phase 1 Complete Checklist

After completing all 10 tasks, verify:

- [ ] `uvicorn web.api.main:app` starts without errors
- [ ] `/api/health` returns `{"status": "ok"}`
- [ ] `/api/materials/groups` returns material groups from datenbank_holz
- [ ] `/api/materials/types?gruppe=Balken` returns timber types
- [ ] `/api/materials/strength-classes?gruppe=Balken&typ=Nadelholz` returns classes
- [ ] `/api/materials/properties?gruppe=Balken&typ=Nadelholz&festigkeitsklasse=C24&nkl=1` returns props
- [ ] `/api/calculate` with test payload returns lastfallkombinationen + ec5_nachweise
- [ ] `/api/projects` returns project list
- [ ] React dev server starts on :5173
- [ ] App shell renders with dark/light theme toggle
- [ ] API proxy works (fetch from browser to /api/ endpoints)
- [ ] Swagger docs at :8000/docs work
- [ ] Dockerfile builds successfully

## Next: Phase 2 (Input Form)

After Phase 1 is verified, create the implementation plan for Phase 2:
- All input form components
- Form state management (Zustand)
- Debounced calculation hook
- API integration with React Query
