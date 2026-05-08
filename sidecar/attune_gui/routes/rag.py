"""attune-rag routes — imports the library directly, no subprocess.

The pipeline cache moved to :mod:`attune_gui.services.rag_pipeline`
in Phase D4 of the architecture-realignment spec (finding #5). The
``_get_pipeline`` and ``invalidate`` names are preserved here as
thin re-exports so any in-tree caller that still references them
keeps working through the deprecation window — but new callers
should import from the canonical owner module.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from attune_gui.models import RagHit, RagQueryRequest, RagQueryResponse
from attune_gui.security import require_client_token
from attune_gui.services import rag_pipeline as _rag_pipeline_svc
from attune_gui.services.rag_pipeline import (
    invalidate,
    pipeline_for,
    workspace_from_request,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


# Backwards-compat aliases for callers that still reference the private
# names this module used to own. New callers should import from
# :mod:`attune_gui.services.rag_pipeline` directly.
_get_pipeline = pipeline_for
_PIPELINES = _rag_pipeline_svc._PIPELINES
_DEFAULT_KEY = _rag_pipeline_svc._DEFAULT_KEY
_workspace_from_request = workspace_from_request

__all__ = [
    "_DEFAULT_KEY",
    "_PIPELINES",
    "_get_pipeline",
    "_workspace_from_request",
    "invalidate",
    "pipeline_for",
    "router",
]


@router.post(
    "/query", response_model=RagQueryResponse, dependencies=[Depends(require_client_token)]
)
async def query(req: RagQueryRequest) -> RagQueryResponse:
    """Run retrieval for a query and return hits + augmented prompt."""
    try:
        pipeline = pipeline_for(workspace_from_request())
    except (
        Exception
    ) as exc:  # noqa: BLE001 — attune-rag init can fail for many reasons; surface as 500
        logger.exception("RagPipeline construction failed")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "rag_init_failed",
                "message": f"Could not initialise RagPipeline: {exc}",
            },
        ) from exc

    try:
        result = pipeline.run(req.query, k=req.k)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "bad_query", "message": str(exc)}
        ) from exc
    except (
        Exception
    ) as exc:  # noqa: BLE001 — pipeline run failures convert to 500 with logged exception
        logger.exception("RagPipeline.run failed")
        raise HTTPException(
            status_code=500,
            detail={"code": "rag_run_failed", "message": str(exc)},
        ) from exc

    hits = [
        RagHit(
            path=h.template_path,
            category=h.category,
            score=h.score,
            excerpt=h.excerpt,
        )
        for h in result.citation.hits
    ]

    return RagQueryResponse(
        query=req.query,
        k=req.k,
        total_hits=len(hits),
        hits=hits,
        augmented_prompt=result.augmented_prompt,
    )


@router.get("/corpus-info")
async def corpus_info() -> dict:
    """Stats about the corpus for the current workspace."""
    try:
        pipeline = pipeline_for(workspace_from_request())
        entries = list(pipeline.corpus.entries())
    except Exception as exc:  # noqa: BLE001 — corpus iteration failures convert to a clean 500
        raise HTTPException(
            status_code=500,
            detail={"code": "corpus_info_failed", "message": str(exc)},
        ) from exc

    return {
        "corpus_class": type(pipeline.corpus).__name__,
        "entry_count": len(entries),
        "kinds": sorted({e.path.split("/")[0] for e in entries if "/" in e.path}),
    }
