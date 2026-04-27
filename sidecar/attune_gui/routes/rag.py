"""attune-rag routes — imports the library directly, no subprocess."""

from __future__ import annotations

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from attune_gui.models import RagHit, RagQueryRequest, RagQueryResponse
from attune_gui.security import require_client_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@lru_cache(maxsize=1)
def _get_pipeline():
    """One RagPipeline per sidecar lifetime. Lazy so import errors surface on first call."""
    from attune_rag import QueryExpander, RagPipeline  # noqa: PLC0415 — intentional lazy import

    return RagPipeline(expander=QueryExpander())


@router.post(
    "/query", response_model=RagQueryResponse, dependencies=[Depends(require_client_token)]
)
async def query(req: RagQueryRequest) -> RagQueryResponse:
    """Run retrieval for a query and return hits + augmented prompt."""
    try:
        pipeline = _get_pipeline()
    except Exception as exc:
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
    except Exception as exc:
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
    """Stats about the default corpus."""
    try:
        pipeline = _get_pipeline()
        entries = list(pipeline.corpus.entries())
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "corpus_info_failed", "message": str(exc)},
        ) from exc

    return {
        "corpus_class": type(pipeline.corpus).__name__,
        "entry_count": len(entries),
        "kinds": sorted({e.path.split("/")[0] for e in entries if "/" in e.path}),
    }
