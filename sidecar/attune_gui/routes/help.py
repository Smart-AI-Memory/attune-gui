"""attune-help routes — fast read-only endpoints for topic discovery."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/help", tags=["help"])


def _engine(template_dir: str | None):
    from attune_help import HelpEngine  # noqa: PLC0415

    return HelpEngine(
        template_dir=Path(template_dir).resolve() if template_dir else None,
        renderer="plain",
    )


@router.get("/topics")
async def list_topics(
    template_dir: str | None = Query(None),
    type_filter: str | None = Query(None),
) -> dict:
    """List available topic slugs, optionally filtered by type."""
    try:
        engine = _engine(template_dir)
        topics = engine.list_topics(type_filter=type_filter)
        return {"topics": topics, "count": len(topics)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/search")
async def search_topics(
    q: str = Query(..., min_length=1),
    template_dir: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """Fuzzy-search topics by query string."""
    try:
        engine = _engine(template_dir)
        results = engine.search(q, limit=limit)
        return {"query": q, "results": results, "count": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
