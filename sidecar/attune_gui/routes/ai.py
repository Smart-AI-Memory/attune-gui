"""attune-ai routes — availability check."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
async def ai_status() -> dict:
    """Check if attune-ai is installed and return its version."""
    try:
        import attune

        return {"available": True, "version": attune.__version__}
    except ImportError:
        return {"available": False, "version": None}
