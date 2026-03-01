"""
Calculation API routes.

Wraps OrchestratorService.process_snapshot() – which uses a threading.Thread
and a callback – in an asyncio-compatible interface so that FastAPI can await
the result without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException

from web.api.deps import DBDep, OrchestratorDep
from web.api.schemas.calculation import (
    CalculationRequest,
    CalculationResponse,
    DeflectionCheckRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum wall-clock seconds to wait for the background calculation thread.
_CALCULATION_TIMEOUT_S = 60


def _convert_numpy_types(obj: Any) -> Any:
    """
    Recursively convert numpy scalar types to native Python types.

    The backend calculations return dicts containing numpy.float64,
    numpy.int64, numpy.bool_, and numpy.ndarray values.  Pydantic v2
    cannot serialise these, so we must convert them before building
    the response model.
    """
    if isinstance(obj, dict):
        return {k: _convert_numpy_types(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_numpy_types(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_convert_numpy_types(v) for v in obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


# ---------------------------------------------------------------------------
# Helper: bridge callback → asyncio.Future
# ---------------------------------------------------------------------------

async def _run_orchestrator(
    orchestrator,
    snapshot: dict[str, Any],
    timeout: float = _CALCULATION_TIMEOUT_S,
) -> dict[str, Any]:
    """
    Invoke OrchestratorService.process_snapshot() and await its result.

    The orchestrator spawns a daemon thread and signals completion via a
    callback.  We bridge this into an asyncio Future so the ASGI event loop
    is not blocked while the FEM calculation runs.

    Raises:
        HTTPException 400: if the backend validation returns errors.
        HTTPException 504: if the calculation exceeds `timeout` seconds.
        HTTPException 500: if the background worker raises an exception.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future[dict[str, Any]] = loop.create_future()

    def callback(result=None, errors=None):
        """Called by the orchestrator worker thread upon completion."""
        if future.done():
            # Guard against double-invocation (should not happen, but be safe)
            return
        if errors:
            loop.call_soon_threadsafe(
                future.set_exception,
                HTTPException(status_code=400, detail={"errors": errors}),
            )
        elif result is None:
            # The orchestrator skipped computation (debounce / unchanged hash).
            # For an HTTP API this should not happen because we reset those
            # guards before each call – treat it as an internal error.
            loop.call_soon_threadsafe(
                future.set_exception,
                HTTPException(
                    status_code=500,
                    detail="Orchestrator skipped computation unexpectedly",
                ),
            )
        else:
            loop.call_soon_threadsafe(future.set_result, result)

    # Reset debounce guards so the orchestrator never skips our request.
    # The debounce mechanism is designed for the desktop GUI where the user
    # types quickly; it is unwanted for stateless HTTP requests.
    orchestrator._last_hash = None
    orchestrator._last_time = 0.0

    # Start the background thread
    orchestrator.process_snapshot(snapshot, callback)

    try:
        result = await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Calculation timed out after {timeout} seconds",
        )
    # HTTPExceptions set via set_exception are re-raised transparently here

    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/calculate",
    response_model=CalculationResponse,
    summary="Run a full structural calculation",
    description=(
        "Accepts structural input (geometry, loads, cross-section, material) "
        "and returns ULS/SLS load combinations, FEM section forces, and EC5 "
        "design check results.  The FEM solver runs in a background thread; "
        "the request blocks until the result is ready (max 60 s)."
    ),
)
async def calculate(
    request: CalculationRequest,
    db: DBDep,
    orchestrator: OrchestratorDep,
) -> CalculationResponse:
    """
    POST /api/calculate – full calculation pipeline.

    Steps executed by the backend:
      1. Validate snapshot (validation_service)
      2. ULS load combinations (lastenkombination)
      3. SLS load combinations (lastkombination_gzg)
      4. FEM section forces (feebb_schnittstelle / feebb_schnittstelle_ec)
      5. EC5 design checks (nachweis_ec5)
    """
    snapshot = request.to_snapshot(db)

    logger.info(
        "POST /api/calculate – ec_modus=%s, fields=%d, loads=%d",
        request.berechnungsmodus.ec_modus,
        len(request.spannweiten),
        len(request.lasten),
    )

    result = await _run_orchestrator(orchestrator, snapshot)

    # Convert numpy types to native Python types for JSON serialisation
    result = _convert_numpy_types(result)

    return CalculationResponse(
        lastfallkombinationen=result.get("Lastfallkombinationen"),
        gzg_lastfallkombinationen=result.get("GZG_Lastfallkombinationen"),
        schnittgroessen=result.get("Schnittgroessen"),
        ec5_nachweise=result.get("EC5_Nachweise"),
    )


@router.post(
    "/calculate/deflection-only",
    response_model=CalculationResponse,
    summary="Recalculate only the EC5 deflection checks",
    description=(
        "Fast path: reuses previously computed Schnittgroessen and load "
        "combinations and only reruns the EC5 deflection verification.  "
        "Useful when the user changes only the deflection limit values "
        "(w_inst, w_fin, w_net_fin) without altering loads or geometry."
    ),
)
async def calculate_deflection_only(
    request: DeflectionCheckRequest,
    db: DBDep,
    orchestrator: OrchestratorDep,
) -> CalculationResponse:
    """
    POST /api/calculate/deflection-only – EC5 deflection checks only.

    The caller must supply previously computed Schnittgroessen and load
    combination results.  The orchestrator will detect calculation_mode ==
    'only_deflection_check' and skip the FEM step.
    """
    snapshot = request.to_snapshot(db)

    logger.info(
        "POST /api/calculate/deflection-only – reusing existing Schnittgroessen"
    )

    result = await _run_orchestrator(orchestrator, snapshot)

    # Convert numpy types to native Python types for JSON serialisation
    result = _convert_numpy_types(result)

    return CalculationResponse(
        lastfallkombinationen=result.get("Lastfallkombinationen"),
        gzg_lastfallkombinationen=result.get("GZG_Lastfallkombinationen"),
        schnittgroessen=result.get("Schnittgroessen"),
        ec5_nachweise=result.get("EC5_Nachweise"),
    )
