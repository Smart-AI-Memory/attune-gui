"""attune-rag routes — imports the library directly, no subprocess."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from attune_gui.models import RagHit, RagQueryRequest, RagQueryResponse
from attune_gui.security import require_client_token

if TYPE_CHECKING:
    from attune_rag import RagPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])

# Workspace-keyed pipeline cache.  Key is the resolved workspace Path; a
# separate sentinel (None key via _DEFAULT_KEY) holds the fallback pipeline
# that uses the bundled AttuneHelpCorpus when no workspace is configured.
_PIPELINES: dict[Path, RagPipeline] = {}
_DEFAULT_KEY = Path()  # empty Path is an otherwise-invalid workspace sentinel


def _get_pipeline(workspace: Path | None = None) -> RagPipeline:
    """Return a RagPipeline, scoped to ``workspace`` when provided.

    When ``workspace/.help/templates/`` exists, uses ``DirectoryCorpus`` from
    that path so queries retrieve from the project's own generated templates.
    Falls back to the bundled ``AttuneHelpCorpus`` when workspace is None or
    the templates directory has not been created yet.
    """
    from attune_rag import DirectoryCorpus, QueryExpander, RagPipeline  # noqa: PLC0415

    key = workspace if workspace is not None else _DEFAULT_KEY

    if key not in _PIPELINES:
        corpus = None
        if workspace is not None:
            corpus_dir = workspace / ".help" / "templates"
            if corpus_dir.is_dir():
                corpus = DirectoryCorpus(corpus_dir)
        _PIPELINES[key] = RagPipeline(corpus=corpus, expander=QueryExpander())

    return _PIPELINES[key]


def invalidate(workspace: Path) -> None:
    """Drop the cached pipeline for a workspace so the next call rebuilds it."""
    _PIPELINES.pop(workspace, None)


def _workspace_from_request() -> Path | None:
    """Resolve the current workspace for HTTP route handlers."""
    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    return get_workspace()


@router.post(
    "/query", response_model=RagQueryResponse, dependencies=[Depends(require_client_token)]
)
async def query(req: RagQueryRequest) -> RagQueryResponse:
    """Run retrieval for a query and return hits + augmented prompt."""
    try:
        pipeline = _get_pipeline(_workspace_from_request())
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
    """Stats about the corpus for the current workspace."""
    try:
        pipeline = _get_pipeline(_workspace_from_request())
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
