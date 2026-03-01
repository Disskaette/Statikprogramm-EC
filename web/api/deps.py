"""
FastAPI dependency injection module.

Provides singleton instances of backend services and per-request factories.
The project root is added to sys.path here so that all
  `from backend.xxx import ...`
imports work regardless of where uvicorn is started from.
"""

import sys
import os
import types
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so that `from backend.xxx import ...`
# works when uvicorn is started from *any* directory.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ---------------------------------------------------------------------------
# tkinter / matplotlib-tkagg stub
#
# backend/calculations/feebb_schnittstelle.py imports tkinter and
# matplotlib.backends.backend_tkagg at module level, even though those
# symbols are never actually *used* during calculation (dead imports from
# the old desktop-GUI era).  We cannot modify the backend, so we inject
# harmless stub modules into sys.modules *before* the first backend import
# so that the import statements succeed on headless / server environments
# where the _tkinter C extension is unavailable.
#
# This is safe because:
#   1. No code path in calculation_service / orchestrator_service calls any
#      tkinter or FigureCanvasTkAgg symbol at runtime.
#   2. The stubs only affect this process; they do not mutate any files.
# ---------------------------------------------------------------------------

def _install_tkinter_stubs() -> None:
    """Install no-op stubs for tkinter and backend_tkagg if not available."""
    try:
        import tkinter  # noqa: F401 – check whether the real module is present
        return  # Real tkinter available – nothing to do
    except ModuleNotFoundError:
        pass

    # Stub for _tkinter (C extension that tkinter wraps)
    _tkinter_stub = types.ModuleType("_tkinter")
    sys.modules.setdefault("_tkinter", _tkinter_stub)

    # Minimal tkinter stub – only needs to be importable
    tkinter_stub = types.ModuleType("tkinter")
    sys.modules.setdefault("tkinter", tkinter_stub)
    sys.modules.setdefault("tkinter.ttk", types.ModuleType("tkinter.ttk"))
    sys.modules.setdefault("tkinter.messagebox", types.ModuleType("tkinter.messagebox"))
    sys.modules.setdefault("tkinter.filedialog", types.ModuleType("tkinter.filedialog"))

    # Stub for matplotlib.backends.backend_tkagg
    # matplotlib itself is available; only the Tk backend is missing.
    tkagg_stub = types.ModuleType("matplotlib.backends.backend_tkagg")
    tkagg_stub.FigureCanvasTkAgg = None  # type: ignore[attr-defined]
    sys.modules.setdefault("matplotlib.backends.backend_tkagg", tkagg_stub)

    import logging
    logging.getLogger(__name__).warning(
        "tkinter not available – installed no-op stubs for "
        "tkinter and matplotlib.backends.backend_tkagg.  "
        "This is expected on headless/server deployments."
    )


_install_tkinter_stubs()

# ---------------------------------------------------------------------------
# Lazy singleton imports – imported after sys.path is patched and tkinter
# stubs are installed so that backend modules import cleanly on servers.
# ---------------------------------------------------------------------------
from backend.database.datenbank_holz import datenbank_holz_class  # noqa: E402
from backend.project.project_manager import ProjectManager          # noqa: E402
from backend.service.orchestrator_service import OrchestratorService  # noqa: E402


@lru_cache(maxsize=1)
def _db_singleton() -> datenbank_holz_class:
    """Load the timber material database exactly once per process."""
    return datenbank_holz_class()


@lru_cache(maxsize=1)
def _project_manager_singleton() -> ProjectManager:
    """Create the ProjectManager exactly once per process.

    Uses the default projects root (./Projekte relative to the repo root),
    which ProjectManager resolves automatically from its own __file__ location.
    """
    return ProjectManager()


def get_db() -> datenbank_holz_class:
    """FastAPI dependency: cached timber material database instance."""
    return _db_singleton()


def get_project_manager() -> ProjectManager:
    """FastAPI dependency: cached ProjectManager instance."""
    return _project_manager_singleton()


def get_orchestrator() -> OrchestratorService:
    """FastAPI dependency: new OrchestratorService per request.

    A fresh instance per request avoids shared debounce/hash state between
    concurrent API callers.  The debounce mechanism makes sense in the desktop
    GUI context but is unwanted for a stateless HTTP API.
    """
    return OrchestratorService(debounce_sec=0.0)


# ---------------------------------------------------------------------------
# Annotated type aliases for cleaner route signatures
# ---------------------------------------------------------------------------
DBDep = Annotated[datenbank_holz_class, Depends(get_db)]
ProjectManagerDep = Annotated[ProjectManager, Depends(get_project_manager)]
OrchestratorDep = Annotated[OrchestratorService, Depends(get_orchestrator)]
