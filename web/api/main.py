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
        "spa": "StaticFiles-html-True",  # identifies this code version
    }


# ---------------------------------------------------------------------------
# Static files: serve the built React frontend (if present)
#
# Pattern: mount the entire dist/ directory with html=True at the root "/".
# Starlette's StaticFiles(html=True) automatically serves index.html for any
# path that doesn't match a real file – this is the correct SPA fallback.
#
# IMPORTANT: This mount must be registered AFTER all API routes. Starlette
# evaluates mounts before @app.get() catch-all routes (/{full_path:path}),
# which caused the old /assets mount to be bypassed by the catch-all, making
# FastAPI serve index.html for every request including JS/CSS assets.
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(_FRONTEND_DIST), html=True),
        name="spa",
    )
