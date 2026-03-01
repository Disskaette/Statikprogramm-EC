"""
Projects API routes.

Wraps the existing ProjectManager (backend/project/project_manager.py) for
HTTP access.  All file I/O is synchronous (ProjectManager uses plain
open() calls); we run those operations in a thread pool via
asyncio.get_running_loop().run_in_executor() so the ASGI event loop is
never blocked.

Route design:
  GET    /api/projects                                              → list all projects
  POST   /api/projects                                             → create a new project
  GET    /api/projects/{project_id}/positions                      → list positions + folders
  POST   /api/projects/{project_id}/positions                      → create a new position
  GET    /api/projects/{project_id}/positions/{position_path}      → load a position
  PUT    /api/projects/{project_id}/positions/{position_path}      → save a position
  DELETE /api/projects/{project_id}/positions/{position_path}      → delete a position
  PATCH  /api/projects/{project_id}/positions/{position_path}/rename    → rename a position
  POST   /api/projects/{project_id}/positions/{position_path}/duplicate → duplicate a position
  PATCH  /api/projects/{project_id}/positions/{position_path}/move      → move a position
  POST   /api/projects/{project_id}/folders                        → create a subfolder
  DELETE /api/projects/{project_id}/folders/{folder_path}          → delete a subfolder

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
import json
import logging
import re
import shutil
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


class RenamePositionRequest(BaseModel):
    """Request body for renaming a position file and updating its metadata."""
    new_nummer: str = Field(
        default="",
        description="New position number, e.g. '1.02'. Empty string keeps the old number."
    )
    new_name: str = Field(description="New human-readable position name")


class MovePositionRequest(BaseModel):
    """Request body for moving a position to a different subfolder."""
    target_folder: str = Field(
        default="",
        description=(
            "Target subfolder relative to the project root. "
            "Empty string means the project root itself."
        )
    )


class CreateFolderRequest(BaseModel):
    """Request body for creating a new subfolder inside a project."""
    folder_name: str = Field(description="Name of the new folder to create")
    parent_folder: str = Field(
        default="",
        description=(
            "Parent subfolder relative to the project root. "
            "Empty string creates the folder directly under the project root."
        )
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


def _safe_filename_part(value: str, *, allow_dots: bool = False) -> str:
    """
    Sanitise a free-form string for use as part of a filename.

    Keeps alphanumeric characters, spaces, underscores and hyphens.
    Spaces are replaced with underscores.  If allow_dots is False (the
    default) dots are also removed; set allow_dots=True only when you
    intentionally want to preserve them (e.g. position numbers like "1.01"
    before the dot-replacement step).

    This mirrors the logic in PositionModel.get_filename().
    """
    if not allow_dots:
        cleaned = re.sub(r"[^A-Za-z0-9 _\-]", "", value)
    else:
        cleaned = re.sub(r"[^A-Za-z0-9 _\-.]", "", value)
    return cleaned.replace(" ", "_")


def _build_position_filename(nummer: str, name: str) -> str:
    """
    Generate a position filename from nummer and name.

    Replicates PositionModel.get_filename() exactly so that the on-disk
    naming convention stays consistent across all code paths.

    Examples:
        ("1.01", "HT 1 - Wohnzimmer") → "Position_1_01_HT_1_-_Wohnzimmer.json"
        ("",     "Sparren")            → "Position_Sparren.json"
    """
    safe_nummer = nummer.replace(".", "_").replace("/", "_")
    safe_name = _safe_filename_part(name)

    if safe_nummer:
        return f"Position_{safe_nummer}_{safe_name}.json"
    return f"Position_{safe_name}.json"


def _assert_inside_project(resolved_path: Path, project_path: Path) -> None:
    """
    Guard against path-traversal attacks.

    Raises HTTPException 400 if *resolved_path* is not strictly inside
    (or equal to) *project_path* after both are fully resolved.
    """
    try:
        resolved_path.resolve().relative_to(project_path.resolve())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Path traversal detected: target path is outside the project directory.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

# *** IMPORTANT: Route registration order matters! ***
# Routes with specific suffixes (/rename, /duplicate, /move) MUST be
# registered BEFORE the catch-all {position_path:path} routes.
# Otherwise FastAPI/Starlette will match the path converter first and
# absorb the suffix into position_path, causing 405 errors.

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
    response_model=dict[str, Any],
    summary="List all positions and subfolders in a project",
)
async def list_positions(
    project_id: str,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    GET /api/projects/{project_id}/positions

    Opens the project (to set pm.current_project_path) then lists all
    position JSON files found recursively inside the project directory,
    as well as all subdirectories (returned as a 'folders' list).

    Response shape::

        {
            "positions": [ { ...position data... }, ... ],
            "folders":   [ "EG", "OG", "EG/Nebengelass", ... ]
        }
    """
    loop = asyncio.get_running_loop()

    def _list():
        project_path = _find_project_path(pm, project_id)
        pm.open_project(project_path)
        positions = pm.list_positions()

        # Collect all subdirectories (excluding the project root itself).
        folders: list[str] = []
        for item in sorted(project_path.rglob("*")):
            if item.is_dir():
                rel = str(item.relative_to(project_path))
                folders.append(rel)

        return {"positions": positions, "folders": folders}

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


# ---------------------------------------------------------------------------
# Specific position sub-routes (rename, duplicate, move) – MUST come before
# the catch-all {position_path:path} routes below!
# ---------------------------------------------------------------------------

# Endpoint: PATCH rename a position
@router.patch(
    "/{project_id}/positions/{position_path:path}/rename",
    response_model=dict[str, Any],
    summary="Rename a position (file and metadata)",
)
async def rename_position(
    project_id: str,
    position_path: str,
    body: RenamePositionRequest,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    PATCH /api/projects/{project_id}/positions/{position_path}/rename

    Renames a position by:

    1. Loading the existing JSON file.
    2. Updating ``position_nummer`` and ``position_name`` inside it.
    3. Writing it to a new filename derived from the new number/name.
    4. Deleting the old file.
    5. Updating the ``positions`` array in project.json.

    If ``new_nummer`` is an empty string the old position_nummer is kept.

    The new filename is generated with the same logic as
    ``PositionModel.get_filename()``, so it mirrors every other position
    created in this app.

    Returns the full position data dict with updated ``relative_path`` and
    ``file_path``.

    Raises:
        404 if the source position file does not exist.
        409 if a file with the new generated name already exists at the
            same location (different content would be silently overwritten
            otherwise).
    """
    loop = asyncio.get_running_loop()

    def _rename():
        project_path = _find_project_path(pm, project_id)
        old_full_path = project_path / position_path

        _assert_inside_project(old_full_path, project_path)

        if not old_full_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Position '{position_path}' not found in project '{project_id}'",
            )

        # Load existing data so we can update it in-place
        with open(old_full_path, "r", encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)

        old_nummer = data.get("position_nummer", "")
        old_name = data.get("position_name", "")

        new_nummer = body.new_nummer if body.new_nummer else old_nummer
        new_name = body.new_name

        # Update in-place
        data["position_nummer"] = new_nummer
        data["position_name"] = new_name

        # Build new filename (same parent directory, new name)
        new_filename = _build_position_filename(new_nummer, new_name)
        new_full_path = old_full_path.parent / new_filename

        _assert_inside_project(new_full_path, project_path)

        # Refuse to clobber an *existing different* file
        if new_full_path.exists() and new_full_path != old_full_path:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"A position file with the generated name '{new_filename}' "
                    f"already exists in the same directory."
                ),
            )

        # Write updated content to new path
        with open(new_full_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

        # Remove old file only if name actually changed
        if new_full_path != old_full_path:
            old_full_path.unlink()

        # Update project.json positions array
        pm.open_project(project_path)
        if pm.current_project_data:
            positions: list[str] = pm.current_project_data.get("positions", [])
            old_relative = str(old_full_path.relative_to(project_path))
            new_relative = str(new_full_path.relative_to(project_path))

            if old_relative in positions:
                positions.remove(old_relative)
            if new_relative not in positions:
                positions.append(new_relative)

            pm.current_project_data["positions"] = positions
            pm.save_project()

        new_relative = str(new_full_path.relative_to(project_path))
        data["file_path"] = str(new_full_path)
        data["relative_path"] = new_relative

        logger.info(
            "Renamed position '%s' → '%s' in project '%s' "
            "(nummer: '%s'→'%s', name: '%s'→'%s')",
            position_path, new_relative, project_id,
            old_nummer, new_nummer, old_name, new_name,
        )
        return data

    return await loop.run_in_executor(None, _rename)


# ---------------------------------------------------------------------------
# New endpoint 3: POST duplicate a position
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/positions/{position_path:path}/duplicate",
    response_model=dict[str, Any],
    status_code=201,
    summary="Duplicate a position",
)
async def duplicate_position(
    project_id: str,
    position_path: str,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    POST /api/projects/{project_id}/positions/{position_path}/duplicate

    Creates a copy of the position file.  The copy is placed in the same
    directory as the original.

    Naming convention:  ``<stem>_Kopie.json``

    If a file with the ``_Kopie`` suffix already exists a numeric counter
    is appended (``_Kopie_2``, ``_Kopie_3``, …) until a free name is found.

    The ``position_name`` inside the copied JSON is updated to append
    ``" (Kopie)"`` (or ``" (Kopie N)"`` for subsequent copies).

    The new relative path is registered in project.json.

    Returns the position data of the new copy including ``relative_path``
    and ``file_path``.

    Raises:
        404 if the source position file does not exist.
    """
    loop = asyncio.get_running_loop()

    def _duplicate():
        project_path = _find_project_path(pm, project_id)
        source_path = project_path / position_path

        _assert_inside_project(source_path, project_path)

        if not source_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Position '{position_path}' not found in project '{project_id}'",
            )

        stem = source_path.stem  # filename without .json
        parent = source_path.parent

        # Find a free "_Kopie[_N]" name
        candidate = parent / f"{stem}_Kopie.json"
        name_suffix = " (Kopie)"
        counter = 2
        while candidate.exists():
            candidate = parent / f"{stem}_Kopie_{counter}.json"
            name_suffix = f" (Kopie {counter})"
            counter += 1

        _assert_inside_project(candidate, project_path)

        # Copy file (preserves metadata timestamps)
        shutil.copy2(source_path, candidate)

        # Update position_name inside the copy
        with open(candidate, "r", encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)

        data["position_name"] = data.get("position_name", "") + name_suffix

        with open(candidate, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

        # Register new path in project.json
        pm.open_project(project_path)
        if pm.current_project_data:
            new_relative = str(candidate.relative_to(project_path))
            positions: list[str] = pm.current_project_data.get("positions", [])
            if new_relative not in positions:
                positions.append(new_relative)
            pm.current_project_data["positions"] = positions
            pm.save_project()

        new_relative = str(candidate.relative_to(project_path))
        data["file_path"] = str(candidate)
        data["relative_path"] = new_relative

        logger.info(
            "Duplicated position '%s' → '%s' in project '%s'",
            position_path, new_relative, project_id,
        )
        return data

    return await loop.run_in_executor(None, _duplicate)


# ---------------------------------------------------------------------------
# New endpoint 4: PATCH move a position to a different subfolder
# ---------------------------------------------------------------------------

@router.patch(
    "/{project_id}/positions/{position_path:path}/move",
    response_model=dict[str, Any],
    summary="Move a position to a different subfolder",
)
async def move_position(
    project_id: str,
    position_path: str,
    body: MovePositionRequest,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    PATCH /api/projects/{project_id}/positions/{position_path}/move

    Moves the position file to *target_folder* (relative to the project
    root).  An empty *target_folder* moves the file to the project root.

    The target directory is created automatically if it does not yet exist.

    The ``positions`` array in project.json is updated accordingly.

    Returns the position data with the updated ``relative_path`` and
    ``file_path``.

    Raises:
        404 if the source position file does not exist.
        409 if a file with the same name already exists in the target folder.
    """
    loop = asyncio.get_running_loop()

    def _move():
        project_path = _find_project_path(pm, project_id)
        source_path = project_path / position_path

        _assert_inside_project(source_path, project_path)

        if not source_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Position '{position_path}' not found in project '{project_id}'",
            )

        # Resolve target directory
        if body.target_folder:
            target_dir = project_path / body.target_folder
        else:
            target_dir = project_path

        _assert_inside_project(target_dir, project_path)

        target_path = target_dir / source_path.name

        _assert_inside_project(target_path, project_path)

        # Nothing to do if already at the destination
        if source_path.resolve() == target_path.resolve():
            with open(source_path, "r", encoding="utf-8") as fh:
                data: dict[str, Any] = json.load(fh)
            data["file_path"] = str(source_path)
            data["relative_path"] = position_path
            return data

        if target_path.exists():
            raise HTTPException(
                status_code=409,
                detail=(
                    f"A file named '{source_path.name}' already exists "
                    f"in the target folder '{body.target_folder or '(project root)'}'."
                ),
            )

        # Create target directory tree if necessary
        target_dir.mkdir(parents=True, exist_ok=True)

        # Move the file
        shutil.move(str(source_path), str(target_path))

        # Load the data from the new location for the response
        with open(target_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        # Update project.json
        pm.open_project(project_path)
        if pm.current_project_data:
            positions: list[str] = pm.current_project_data.get("positions", [])
            old_relative = str(source_path.relative_to(project_path))
            new_relative = str(target_path.relative_to(project_path))

            if old_relative in positions:
                positions.remove(old_relative)
            if new_relative not in positions:
                positions.append(new_relative)

            pm.current_project_data["positions"] = positions
            pm.save_project()

        new_relative = str(target_path.relative_to(project_path))
        data["file_path"] = str(target_path)
        data["relative_path"] = new_relative

        logger.info(
            "Moved position '%s' → '%s' in project '%s'",
            position_path, new_relative, project_id,
        )
        return data

    return await loop.run_in_executor(None, _move)


# ---------------------------------------------------------------------------
# Catch-all position routes (GET, PUT, DELETE) – MUST come AFTER the
# specific sub-routes above (rename, duplicate, move) because the
# {position_path:path} converter would otherwise absorb the suffix.
# ---------------------------------------------------------------------------

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


@router.delete(
    "/{project_id}/positions/{position_path:path}",
    response_model=dict[str, Any],
    summary="Delete a position",
)
async def delete_position(
    project_id: str,
    position_path: str,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    DELETE /api/projects/{project_id}/positions/{position_path}

    Deletes the position JSON file identified by its relative path inside
    the project directory.  Also removes the entry from project.json
    (delegated to pm.delete_position which handles that internally).

    Returns::

        {"deleted": "<relative_path>"}

    Raises:
        404 if the position file does not exist.
    """
    loop = asyncio.get_running_loop()

    def _delete():
        project_path = _find_project_path(pm, project_id)
        full_path = project_path / position_path

        # Path traversal guard
        _assert_inside_project(full_path, project_path)

        if not full_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Position '{position_path}' not found in project '{project_id}'",
            )

        pm.open_project(project_path)
        pm.delete_position(full_path)

        logger.info("Deleted position '%s' from project '%s'", position_path, project_id)
        return {"deleted": position_path}

    return await loop.run_in_executor(None, _delete)


# ---------------------------------------------------------------------------
# Endpoint: POST create a subfolder
# ---------------------------------------------------------------------------

@router.post(
    "/{project_id}/folders",
    response_model=dict[str, Any],
    status_code=201,
    summary="Create a subfolder inside a project",
)
async def create_folder(
    project_id: str,
    body: CreateFolderRequest,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    POST /api/projects/{project_id}/folders

    Creates a new subfolder at ``<project_root>/<parent_folder>/<folder_name>``.
    The *parent_folder* defaults to the project root (empty string).

    Returns::

        {"folder": "<relative_folder_path>"}

    Raises:
        400 if the path would escape the project directory.
        409 if the folder already exists.
    """
    loop = asyncio.get_running_loop()

    def _create_folder():
        project_path = _find_project_path(pm, project_id)

        if body.parent_folder:
            target = project_path / body.parent_folder / body.folder_name
        else:
            target = project_path / body.folder_name

        _assert_inside_project(target, project_path)

        if target.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Folder '{body.folder_name}' already exists.",
            )

        try:
            target.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            # Race condition: created between the exists() check and mkdir()
            raise HTTPException(
                status_code=409,
                detail=f"Folder '{body.folder_name}' already exists.",
            )

        relative_folder = str(target.relative_to(project_path))
        logger.info(
            "Created folder '%s' in project '%s'", relative_folder, project_id
        )
        return {"folder": relative_folder}

    return await loop.run_in_executor(None, _create_folder)


# ---------------------------------------------------------------------------
# New endpoint 6: DELETE a subfolder (and all positions inside it)
# ---------------------------------------------------------------------------

@router.delete(
    "/{project_id}/folders/{folder_path:path}",
    response_model=dict[str, Any],
    summary="Delete a subfolder and all positions inside it",
)
async def delete_folder(
    project_id: str,
    folder_path: str,
    pm: ProjectManagerDep,
) -> dict[str, Any]:
    """
    DELETE /api/projects/{project_id}/folders/{folder_path}

    Recursively deletes the specified subfolder and every file inside it
    using ``shutil.rmtree``.

    Also cleans up project.json: any positions whose ``relative_path``
    starts with ``<folder_path>/`` are removed from the ``positions`` array
    and ``pm.save_project()`` is called.

    Returns::

        {
            "deleted": "<folder_path>",
            "removed_positions": ["<rel_path_1>", ...]
        }

    Raises:
        400 if the path would escape the project directory or if an attempt
            is made to delete the project root itself.
        404 if the folder does not exist.
    """
    loop = asyncio.get_running_loop()

    def _delete_folder():
        project_path = _find_project_path(pm, project_id)
        target = project_path / folder_path

        _assert_inside_project(target, project_path)

        # Refuse to delete the project root
        if target.resolve() == project_path.resolve():
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the project root directory.",
            )

        if not target.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Folder '{folder_path}' not found in project '{project_id}'",
            )

        if not target.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"'{folder_path}' is not a directory.",
            )

        # Determine which positions will be removed BEFORE deleting the tree
        pm.open_project(project_path)
        removed_positions: list[str] = []

        if pm.current_project_data:
            positions: list[str] = pm.current_project_data.get("positions", [])
            prefix = folder_path.rstrip("/") + "/"

            # On Windows path separators may differ; normalise to forward slash
            still_valid = []
            for rel in positions:
                # Normalise separators to "/" for the prefix check
                rel_normalised = rel.replace("\\", "/")
                if rel_normalised.startswith(prefix) or rel_normalised == folder_path:
                    removed_positions.append(rel)
                else:
                    still_valid.append(rel)

            pm.current_project_data["positions"] = still_valid
            pm.save_project()

        # Recursively delete the folder
        shutil.rmtree(target)

        logger.info(
            "Deleted folder '%s' from project '%s' (removed %d positions)",
            folder_path, project_id, len(removed_positions),
        )
        return {"deleted": folder_path, "removed_positions": removed_positions}

    return await loop.run_in_executor(None, _delete_folder)
