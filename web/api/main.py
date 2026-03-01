"""
FastAPI application entry point.

Start the development server with:
    uvicorn web.api.main:app --reload --host 0.0.0.0 --port 8000

Or from the project root:
    python -m uvicorn web.api.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import deps first so that sys.path is patched before any backend import
from web.api.deps import get_db  # noqa: F401 – side-effect: patches sys.path

from web.api.routes import calculation, materials, projects

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)


# ---------------------------------------------------------------------------
# Lifespan: pre-load material database at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Pre-loads the timber material database so that the first API request
    does not pay the ~1 s Excel parsing cost.  The database singleton is
    cached via @lru_cache in deps.py and reused for all subsequent requests.
    """
    logger.info("Startup: loading timber material database …")
    db = get_db()  # triggers lru_cache → datenbank_holz_class.__init__()
    logger.info(
        "Startup: database loaded – %d materials, %d kmod entries, %d load categories",
        len(db.materialien),
        len(db.kmod),
        len(db.si_beiwerte),
    )
    yield
    logger.info("Shutdown: cleanup complete")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Durchlaufträger – Statik API",
    description=(
        "REST API for the timber continuous-beam structural analysis tool. "
        "Implements EC0/EC1/EC5 load combinations and design checks via "
        "FastAPI + the existing Python FEM backend."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS – allow the Vite dev server and the production SPA origin
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server (React)
        "http://localhost:3000",   # alternative dev server
        "http://localhost:8000",   # same-origin for testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

app.include_router(
    calculation.router,
    prefix="/api",
    tags=["calculation"],
)

app.include_router(
    materials.router,
    prefix="/api/materials",
    tags=["materials"],
)

app.include_router(
    projects.router,
    prefix="/api/projects",
    tags=["projects"],
)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """
    GET /api/health

    Returns {"status": "ok"} when the API is running and the material
    database has been loaded successfully.
    """
    db = get_db()
    return {
        "status": "ok",
        "materials": str(len(db.materialien)),
        "kmod_entries": str(len(db.kmod)),
    }


# ---------------------------------------------------------------------------
# Static files: serve the built React frontend (if present)
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    # Serve JS/CSS/image assets from the build output directory
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """
        Catch-all route: serve index.html for all non-API paths so that
        React Router (client-side routing) works correctly on page refresh.
        """
        index_file = _FRONTEND_DIST / "index.html"
        return FileResponse(str(index_file))
