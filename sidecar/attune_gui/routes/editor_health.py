"""Top-level ``/healthz`` route for portfile freshness validation.

Used by the attune-author CLI: it reads the portfile, then calls
``GET /healthz?token=<t>`` to confirm the sidecar at the recorded
port is the one that wrote the file. Mismatch = stale sidecar; CLI
spawns a fresh one.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from attune_gui.security import current_session_token

router = APIRouter(tags=["editor-health"])


@router.get("/healthz")
async def healthz(token: str = Query(..., min_length=1)) -> dict:
    """Return ``{"status": "ok"}`` if ``token`` matches this sidecar.

    Returns 401 on mismatch — the CLI treats that as "wrong sidecar
    is listening on this port" (stale portfile).
    """
    if token != current_session_token():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not match this sidecar.",
        )
    return {"status": "ok"}
