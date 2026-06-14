"""Batch-status SSE route.

GET /api/batch/status/stream — Server-Sent Events stream of the pending
attune-author maintenance batch (queued → in-progress → terminal).

Observe-only: the dashboard watches a batch kicked off from the CLI; it
does not trigger one (that is a separate spec, ``gui-batch-trigger``).
Backed by ``attune_author.maintenance_batch.status_maintenance_batch``,
which is synchronous and does network I/O, so every poll runs in a
worker thread to keep the single-process event loop responsive.

See ``specs/gui-batch-status-sse/`` for the design.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from attune_gui.workspace import get_workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])

#: ``processing_status`` values (and the presence of ``ended_at``) that mean
#: the batch has stopped; the stream emits a final frame and closes.
_TERMINAL = {"ended", "canceled", "expired"}

_DEFAULT_POLL_SECS = 30


def _poll_secs() -> int:
    """Resolve the poll cadence from ``ATTUNE_GUI_BATCH_POLL_SECS`` (default 30)."""
    raw = os.getenv("ATTUNE_GUI_BATCH_POLL_SECS", str(_DEFAULT_POLL_SECS))
    try:
        return max(1, int(raw))
    except ValueError:
        return _DEFAULT_POLL_SECS


def _get_help_dir() -> Path:
    """The ``.help`` directory under the configured workspace.

    Mirrors the living-docs routes' resolver: configured workspace, or the
    process cwd as a fallback.
    """
    root = get_workspace() or Path.cwd()
    return root / ".help"


def _sse(payload: dict[str, Any]) -> str:
    """Format one dict as an SSE ``data:`` frame."""
    return f"data: {json.dumps(payload)}\n\n"


def _status_once(help_dir: Path) -> dict[str, Any]:
    """One status query. Synchronous; run via ``asyncio.to_thread``.

    Returns a frame dict with a ``state`` discriminator:
      - ``pending`` + the full ``status_maintenance_batch`` payload, or
      - ``none`` when there is no (or an expired) pending batch.
    Raises on unexpected errors — the caller renders an ``error`` frame.
    """
    from attune_author.maintenance_batch import (  # noqa: PLC0415
        BatchStateError,
        status_maintenance_batch,
    )

    try:
        status = status_maintenance_batch(help_dir)
    except BatchStateError:
        # No pending batch, or the local state expired. CLI shows
        # "no pending batch"; the dashboard mirrors that as ``none``.
        return {"state": "none"}
    return {"state": "pending", **status}


async def _events(request: Request, help_dir: Path):
    """SSE generator: poll until disconnect, terminal status, or none/error."""
    while True:
        if await request.is_disconnected():
            return
        try:
            frame = await asyncio.to_thread(_status_once, help_dir)
        except Exception as e:  # noqa: BLE001 - surface, then close
            logger.warning("batch status poll failed: %s", e)
            yield _sse({"state": "error", "detail": str(e)})
            return

        yield _sse(frame)

        if frame["state"] != "pending":
            return  # ``none`` — one frame, then close.
        status = frame
        if status.get("processing_status") in _TERMINAL or status.get("ended_at"):
            return  # terminal — final frame already sent, then close.

        await asyncio.sleep(_poll_secs())


@router.get("/status/stream")
async def stream_status(request: Request) -> StreamingResponse:
    """Stream the pending batch's status as Server-Sent Events.

    Emits one ``data:`` frame per poll. Closes after a ``none``/``error``
    frame or once the batch reaches a terminal state. Read-only GET — the
    app-wide origin guard applies; no client token is required (matching
    the other read endpoints).
    """
    help_dir = _get_help_dir()
    return StreamingResponse(
        _events(request, help_dir),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering for SSE
        },
    )
