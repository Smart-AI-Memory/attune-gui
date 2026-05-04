"""System / health / session-token routes."""

from __future__ import annotations

import sys

from fastapi import APIRouter

from attune_gui import __version__
from attune_gui.models import HealthResponse
from attune_gui.security import current_session_token

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — returns the sidecar version and Python runtime."""
    return HealthResponse(
        version=__version__,
        python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )


@router.get("/workspace")
async def current_workspace() -> dict:
    """Return the currently configured workspace path, or null if unset."""
    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    ws = get_workspace()
    return {"workspace": str(ws) if ws else None}


@router.get("/session/token")
async def session_token() -> dict:
    """Return the per-process client token the UI must echo on mutating requests.

    This is a soft CSRF guard for localhost-served UIs. Anyone who can reach
    the sidecar (i.e., anything running on 127.0.0.1) can read this, so it's
    not a real authorization boundary — it's a drive-by-fetch mitigation.
    """
    return {"token": current_session_token()}
