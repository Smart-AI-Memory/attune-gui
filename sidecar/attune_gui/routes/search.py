"""Unified search route — fans out to HelpEngine + RagPipeline in parallel.

GET /api/search?q=<query>[&limit=10][&workspace=/path/to/project]
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from attune_gui.search import merge
from attune_gui.workspace import get_workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


def _help_search(q: str, limit: int, workspace: Path | None) -> list[tuple[str, float]]:
    from attune_help import HelpEngine  # noqa: PLC0415

    template_dir = None
    if workspace is not None:
        candidate = workspace / ".help" / "templates"
        if candidate.is_dir():
            template_dir = candidate
    try:
        return HelpEngine(template_dir=template_dir, renderer="plain").search(q, limit=limit)
    except Exception:
        logger.warning("HelpEngine.search failed for %r", q, exc_info=True)
        return []


def _rag_search(q: str, limit: int, workspace: Path | None) -> list[Any]:
    from attune_gui.routes.rag import _get_pipeline  # noqa: PLC0415

    try:
        return _get_pipeline(workspace).run(q, k=limit).citation.hits
    except Exception:
        logger.warning("RagPipeline.run failed for %r", q, exc_info=True)
        return []


@router.get("/")
async def unified_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    workspace: str | None = Query(None),
) -> dict[str, Any]:
    """Search across HelpEngine (fuzzy/keyword) and RAG corpus in parallel.

    Results are merged and re-ranked: RAG weighted 0.6, help 0.4.
    Hits appearing in both sources receive a 1.2× boost.
    """
    ws: Path | None
    if workspace:
        ws = Path(workspace).expanduser().resolve()
        if not ws.is_dir():
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_workspace", "message": f"Not a directory: {ws}"},
            )
    else:
        ws = get_workspace()

    help_task = asyncio.to_thread(_help_search, q, limit, ws)
    rag_task = asyncio.to_thread(_rag_search, q, limit, ws)
    help_hits, rag_hits = await asyncio.gather(help_task, rag_task)

    results = merge(help_hits, rag_hits, limit)
    return {"query": q, "results": results, "count": len(results)}
