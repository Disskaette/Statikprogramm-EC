"""
Projects API routes.

Wraps the existing ProjectManager (backend/project/project_manager.py) for
HTTP access.  All file I/O is synchronous (ProjectManager uses plain
open() calls); we run those operations in a thread pool via
asyncio.get_running_loop().run_in_executor() so the ASGI event loop is
never blocked.

Route design:
  GET  /api/projects                           → list all projects
  POST /api/projects                           → create a new project
  GET  /api/projects/{project_id}/positions    → list positions in a project
  POST /api/projects/{project_id}/positions    → create a new position
  GET  /api/projects/{project_id}/positions/{position_path} → load a position
  PUT  /api/projects/{project_id}/positions/{position_path} → save a position

Note on {project_id}:
  The ProjectManager identifies projects by their UUID (stored in project.json).
  The route layer resolves this UUID to the on-disk project path before
  delegating to ProjectManager.

Note on {position_path}:
  Positions are stored as relative paths inside the project directory
  (e.g. "EG/Position_1_01_HT_1_-_Wohnzimmer.json").  The path is
  URL-encoded by the client; FastAPI decodes it automatically via the
  `path` converter ("{position_path:path}").
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from web.api.deps import ProjectManagerDep
from backend.project.project_manager import ProjectManager
from backend.project.position_model import PositionModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request bodies (defined here because they are projects-specific)
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""
    name: str = Field(description="Human-readable project name")
    description: str = Field(default="", description="Optional project description")


class CreatePositionRequest(BaseModel):
    """Request body for creating a new position inside a project."""
    position_nummer: str = Field(description="Position number, e.g. '1.01'")
    position_name: str = Field(description="Position name, e.g. 'HT 1 - Wohnzimmer'")
    subfolder: str = Field(
        default="",
        description="Optional subfolder inside the project directory (e.g. 'EG')"
    )
    active_module: str = Field(
        default="durchlauftraeger",
        description="Which calculation module is active for this position"
    )


class SavePositionRequest(BaseModel):
    """Request body for saving (updating) an existing position."""
    position_nummer: str = Field(default="")
    position_name: str = Field(default="")
    active_module: str = Field(default="durchlauftraeger")
    modules: dict[str, Any] = Field(
        default_factory=dict,
        description="Module data dict, keyed by module ID"
    )


# ---------------------------------------------------------------------------
# Helper: resolve project UUID → project path
# ---------------------------------------------------------------------------

def _find_project_path(pm: ProjectManager, project_id: str) -> Path:
    """
    Resolve a project UUID to its on-disk directory path.

    Scans all projects via list_projects() (in-memory dict lookup) and
    returns the path of the matching one.

    Raises:
        HTTPException 404: if no project with the given UUID exists.
    """
    all_projects = pm.list_projects()
    for proj in all_projects:
        if proj.get("uuid") == project_id:
            return Path(proj["path"])
    raise HTTPException(
        status_code=404,
        detail=f"Project with id '{project_id}' not found",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=list[dict[str, Any]],
    summary="List all projects",
)
async def list_projects(pm: ProjectManagerDep) -> list[dict[str, Any]]:
    """
    GET /api/projects

    Returns all projects found under the configured projects root directory,
    sorted by last modification date (newest first).
    Each item contains the project metadata from project.json plus a
    'path' field with the absolute directory path.
    """
    loop = asyncio.get_running_loop()
    projects = await loop.run_in_executor(None, pm.list_projects)
    return projects


@router.post(
    "",
    response_model=dict[str, Any],
    status_code=201,
    summary="Create a new project",
)
async def create_project(
    body: CreateProjectRequest,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    POST /api/projects

    Creates a new project directory and project.json on disk.
    Returns the new project metadata including its generated UUID.
    """
    loop = asyncio.get_running_loop()

    def _create():
        try:
            project_path = pm.create_project(body.name, body.description)
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        # open_project populates current_project_data with the UUID
        project_data = pm.open_project(project_path)
        project_data["path"] = str(project_path)
        return project_data

    return await loop.run_in_executor(None, _create)


@router.get(
    "/{project_id}/positions",
    response_model=list[dict[str, Any]],
    summary="List all positions in a project",
)
async def list_positions(
    project_id: str,
    pm: ProjectManagerDep,
) -> list[dict[str, Any]]:
    """
    GET /api/projects/{project_id}/positions

    Opens the project (to set pm.current_project_path) then lists all
    position JSON files found recursively inside the project directory.
    """
    loop = asyncio.get_running_loop()

    def _list():
        project_path = _find_project_path(pm, project_id)
        pm.open_project(project_path)
        return pm.list_positions()

    return await loop.run_in_executor(None, _list)


@router.post(
    "/{project_id}/positions",
    response_model=dict[str, Any],
    status_code=201,
    summary="Create a new position in a project",
)
async def create_position(
    project_id: str,
    body: CreatePositionRequest,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    POST /api/projects/{project_id}/positions

    Creates a new position file inside the project directory and updates
    project.json with the relative path.
    Returns the position data as stored on disk.
    """
    loop = asyncio.get_running_loop()

    def _create():
        project_path = _find_project_path(pm, project_id)
        pm.open_project(project_path)

        model = PositionModel(
            position_nummer=body.position_nummer,
            position_name=body.position_name,
            active_module=body.active_module,
        )
        position_file = pm.create_position(model, subfolder=body.subfolder)
        data = model.to_dict()
        data["file_path"] = str(position_file)
        data["relative_path"] = str(
            position_file.relative_to(project_path)
        )
        return data

    return await loop.run_in_executor(None, _create)


@router.get(
    "/{project_id}/positions/{position_path:path}",
    response_model=dict[str, Any],
    summary="Load a position",
)
async def get_position(
    project_id: str,
    position_path: str,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    GET /api/projects/{project_id}/positions/{position_path}

    Loads a position JSON file by its relative path inside the project.
    The position_path is URL-decoded automatically by FastAPI (e.g.
    "EG/Position_1_01_HT_1_-_Wohnzimmer.json").
    """
    loop = asyncio.get_running_loop()

    def _load():
        project_path = _find_project_path(pm, project_id)
        full_path = project_path / position_path
        if not full_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Position '{position_path}' not found in project '{project_id}'",
            )
        model = pm.load_position(full_path)
        data = model.to_dict()
        data["file_path"] = str(full_path)
        data["relative_path"] = position_path
        return data

    return await loop.run_in_executor(None, _load)


@router.put(
    "/{project_id}/positions/{position_path:path}",
    response_model=dict[str, Any],
    summary="Save (update) a position",
)
async def save_position(
    project_id: str,
    position_path: str,
    body: SavePositionRequest,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    PUT /api/projects/{project_id}/positions/{position_path}

    Overwrites an existing position JSON file with the supplied data.
    Creates the file if it does not yet exist (upsert semantics).
    Returns the saved position data.
    """
    loop = asyncio.get_running_loop()

    def _save():
        project_path = _find_project_path(pm, project_id)
        full_path = project_path / position_path

        # Ensure parent directory exists (e.g. "EG/" subfolder)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        model = PositionModel(
            position_nummer=body.position_nummer,
            position_name=body.position_name,
            active_module=body.active_module,
            modules=body.modules,
        )
        pm.open_project(project_path)
        pm.save_position(model, full_path)

        # Register position in project.json if not already listed
        relative = str(full_path.relative_to(project_path))
        if (
            pm.current_project_data
            and relative not in pm.current_project_data.get("positions", [])
        ):
            pm.current_project_data["positions"].append(relative)
            pm.save_project()

        data = model.to_dict()
        data["file_path"] = str(full_path)
        data["relative_path"] = position_path
        return data

    return await loop.run_in_executor(None, _save)
