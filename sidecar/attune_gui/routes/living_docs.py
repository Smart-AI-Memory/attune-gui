"""Living Docs API routes.

GET  /api/living-docs/config              — get/set workspace path
PUT  /api/living-docs/config              — set workspace, triggers rescan
GET  /api/living-docs/health              — health summary + quality scores
GET  /api/living-docs/docs                — doc registry (?persona=)
POST /api/living-docs/scan               — trigger a workspace scan
POST /api/living-docs/docs/{id}/regenerate — regenerate a single doc
GET  /api/living-docs/queue              — review queue (?persona= &reviewed=)
POST /api/living-docs/queue/{id}/approve — mark a queue item reviewed
POST /api/living-docs/queue/{id}/revert  — git-revert an auto-applied doc
GET  /api/living-docs/quality            — last smoke eval scores
POST /api/living-docs/webhook/git        — git post-commit hook trigger
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from attune_gui.jobs import JobContext, get_registry
from attune_gui.living_docs_store import get_store
from attune_gui.security import require_client_token
from attune_gui.workspace import get_workspace, set_workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/living-docs", tags=["living-docs"])


# ---------------------------------------------------------------------------
# Workspace config helpers
# ---------------------------------------------------------------------------


def _get_workspace() -> Path:
    """Return configured workspace, falling back to cwd for living-docs routes."""
    return get_workspace() or Path.cwd()


def _set_workspace(path: str) -> Path:
    return set_workspace(path)


# ---------------------------------------------------------------------------
# Config endpoint
# ---------------------------------------------------------------------------


class ConfigUpdate(BaseModel):
    workspace: str


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Return the configured workspace path and whether `.help/` exists in it."""
    ws = _get_workspace()
    return {"workspace": str(ws), "has_help_dir": (ws / ".help").is_dir()}


@router.put("/config", dependencies=[Depends(require_client_token)])
async def set_config(body: ConfigUpdate, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Persist a new workspace path and queue a manual rescan. 400 if the path isn't a directory."""
    try:
        resolved = await asyncio.to_thread(_set_workspace, body.workspace)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_workspace", "message": str(e)},
        ) from e
    background_tasks.add_task(_run_scan, "manual")
    return {"workspace": str(resolved), "has_help_dir": (resolved / ".help").is_dir()}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health() -> dict[str, Any]:
    """Living Docs health summary — counts, last scan, quality scores, plus workspace path."""
    h = await get_store().get_health()
    h["workspace"] = str(_get_workspace())
    return h


# ---------------------------------------------------------------------------
# Doc registry
# ---------------------------------------------------------------------------


@router.get("/docs")
async def list_docs(persona: str | None = None) -> dict[str, Any]:
    """Return the doc registry. ``persona`` filters to one of end-user|developer|support."""
    docs = await get_store().list_docs(persona=persona)
    return {"docs": docs}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    trigger: str = "manual"


async def _run_scan(trigger: str) -> None:
    ws = _get_workspace()
    await get_store().scan(ws, trigger=trigger)
    from attune_gui.routes import rag  # noqa: PLC0415

    rag.invalidate(ws)


@router.post("/scan", dependencies=[Depends(require_client_token)])
async def trigger_scan(req: ScanRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Queue a workspace scan. Returns immediately; scan runs in the background."""
    background_tasks.add_task(_run_scan, req.trigger)
    return {"status": "scan_queued", "trigger": req.trigger}


# ---------------------------------------------------------------------------
# Regenerate
# ---------------------------------------------------------------------------


async def _regenerate_doc_executor(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    """Job-system executor for `living-docs.regenerate`.

    Same effective work as the legacy `_regenerate_doc` background task,
    but progress is now visible on the Jobs page via `ctx.log` calls
    instead of disappearing into a fire-and-forget BackgroundTask.
    """
    doc_id = str(args["doc_id"])
    trigger = str(args.get("trigger", "manual"))
    parts = doc_id.split("/", 1)
    feature_name = parts[0]
    depth = parts[1] if len(parts) > 1 else "concept"

    ctx.log(f"regenerating {doc_id} (feature={feature_name}, depth={depth}, trigger={trigger})")
    root = _get_workspace()
    store = get_store()
    help_dir = root / ".help"
    ctx.log(f"workspace = {root}")
    ctx.log(f"help_dir  = {help_dir}")

    from attune_author.generator import generate_feature_templates  # noqa: PLC0415
    from attune_author.manifest import load_manifest  # noqa: PLC0415

    ctx.log("loading manifest…")
    manifest = await asyncio.to_thread(load_manifest, help_dir)
    # `manifest.features` is `dict[str, Feature]`, not a list — the
    # legacy BackgroundTask version was iterating it as a list, which
    # silently produced str keys instead of Feature objects and crashed
    # in `getattr(f, 'name', ...)`. The error never surfaced because
    # BackgroundTask exceptions only logged. Surfaced now via the Jobs
    # page; fix the lookup.
    feat = manifest.features.get(feature_name)
    if feat is None:
        available = ", ".join(sorted(manifest.features.keys())) or "(none)"
        raise ValueError(f"Feature {feature_name!r} not in manifest. Available: {available}")

    ctx.log(f"running attune-author generate (single depth: {depth})…")
    await asyncio.to_thread(
        generate_feature_templates,
        feat,
        help_dir,
        root,
        [depth],
        True,  # overwrite=True
    )
    ctx.log("generate complete; adding to review queue + rescanning")
    await store.add_to_queue(doc_id, trigger=trigger, project_root=root)
    await store.scan(root, trigger=trigger)

    from attune_gui.routes import rag  # noqa: PLC0415

    rag.invalidate(root)
    ctx.log("RAG cache invalidated")

    return {"doc_id": doc_id, "feature": feature_name, "depth": depth, "trigger": trigger}


@router.post("/docs/{doc_id:path}/regenerate", dependencies=[Depends(require_client_token)])
async def regenerate_doc(doc_id: str) -> dict[str, Any]:
    """Start a regeneration job for a single doc (``feature/depth``).

    Returns the job dict so the frontend can navigate to the Jobs page
    and watch progress — the previous BackgroundTask version had no
    visibility, leaving users staring at a "queued" toast with no idea
    whether the work was running.
    """
    job = await get_registry().start(
        name="living-docs.regenerate",
        args={"doc_id": doc_id, "trigger": "manual"},
        executor=_regenerate_doc_executor,
    )
    return job.to_dict()


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------


@router.get("/queue")
async def list_queue(
    persona: str | None = None,
    reviewed: bool | None = None,
) -> dict[str, Any]:
    """Return the auto-applied review queue, optionally filtered by persona / reviewed-state."""
    items = await get_store().list_queue(persona=persona, reviewed=reviewed)
    return {"queue": items}


@router.post("/queue/{item_id}/approve", dependencies=[Depends(require_client_token)])
async def approve_item(item_id: str) -> dict[str, Any]:
    """Mark a queue item as reviewed. 404 if the item isn't in the queue."""
    ok = await get_store().approve(item_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": f"Queue item {item_id!r} not found."},
        )
    return {"ok": True, "item_id": item_id}


@router.post("/queue/{item_id}/revert", dependencies=[Depends(require_client_token)])
async def revert_item(item_id: str) -> dict[str, Any]:
    """Git-revert an auto-applied doc. 500 if `git checkout HEAD -- <path>` fails."""
    result = await get_store().revert(item_id, _get_workspace())
    if not result["ok"]:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "revert_failed",
                "message": result.get("error", "Unknown error"),
            },
        )
    return result


# ---------------------------------------------------------------------------
# Quality scores
# ---------------------------------------------------------------------------


@router.get("/quality")
async def get_quality() -> dict[str, Any]:
    """Return the most recent RAG quality scores (faithfulness + strict accuracy)."""
    h = await get_store().get_health()
    return {"quality": h.get("quality", {})}


# ---------------------------------------------------------------------------
# Git hook webhook
# ---------------------------------------------------------------------------


@router.post("/webhook/git")
async def git_webhook(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Git post-commit hook entry point — queues a workspace scan tagged ``git_hook``."""
    background_tasks.add_task(_run_scan, "git_hook")
    return {"status": "scan_queued", "trigger": "git_hook"}
