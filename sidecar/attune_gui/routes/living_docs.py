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
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from attune_gui.living_docs_store import get_store
from attune_gui.security import require_client_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/living-docs", tags=["living-docs"])

_CONFIG_PATH = Path.home() / ".attune-gui" / "config.json"
_FALLBACK_ROOT = Path.cwd()


# ---------------------------------------------------------------------------
# Workspace config helpers
# ---------------------------------------------------------------------------


def _get_workspace() -> Path:
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        ws = data.get("workspace", "")
        if ws:
            p = Path(ws).expanduser()
            if p.is_dir():
                return p
    except Exception:
        pass
    return _FALLBACK_ROOT


def _set_workspace(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"Not a directory: {resolved}")
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    data["workspace"] = str(resolved)
    _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return resolved


# ---------------------------------------------------------------------------
# Config endpoint
# ---------------------------------------------------------------------------


class ConfigUpdate(BaseModel):
    workspace: str


@router.get("/config")
async def get_config() -> dict[str, Any]:
    ws = _get_workspace()
    return {"workspace": str(ws), "has_help_dir": (ws / ".help").is_dir()}


@router.put("/config", dependencies=[Depends(require_client_token)])
async def set_config(body: ConfigUpdate, background_tasks: BackgroundTasks) -> dict[str, Any]:
    try:
        resolved = await asyncio.to_thread(_set_workspace, body.workspace)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_workspace", "message": str(e)},
        )
    background_tasks.add_task(_run_scan, "manual")
    return {"workspace": str(resolved), "has_help_dir": (resolved / ".help").is_dir()}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health() -> dict[str, Any]:
    h = await get_store().get_health()
    h["workspace"] = str(_get_workspace())
    return h


# ---------------------------------------------------------------------------
# Doc registry
# ---------------------------------------------------------------------------


@router.get("/docs")
async def list_docs(persona: str | None = None) -> dict[str, Any]:
    docs = await get_store().list_docs(persona=persona)
    return {"docs": docs}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    trigger: str = "manual"


async def _run_scan(trigger: str) -> None:
    await get_store().scan(_get_workspace(), trigger=trigger)


@router.post("/scan", dependencies=[Depends(require_client_token)])
async def trigger_scan(req: ScanRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    background_tasks.add_task(_run_scan, req.trigger)
    return {"status": "scan_queued", "trigger": req.trigger}


# ---------------------------------------------------------------------------
# Regenerate
# ---------------------------------------------------------------------------


async def _regenerate_doc(doc_id: str, trigger: str) -> None:
    parts = doc_id.split("/", 1)
    feature_name = parts[0]
    depth = parts[1] if len(parts) > 1 else "concept"

    root = _get_workspace()
    store = get_store()
    help_dir = root / ".help"

    try:
        from attune_author.generator import generate_feature_templates
        from attune_author.manifest import load_manifest

        manifest = await asyncio.to_thread(load_manifest, help_dir)
        feat = next(
            (f for f in manifest.features if getattr(f, "name", str(f)) == feature_name),
            None,
        )
        if feat is None:
            logger.error("Feature %r not in manifest — cannot regenerate", feature_name)
            return

        await asyncio.to_thread(
            generate_feature_templates,
            feat,
            help_dir,
            root,
            [depth],
            True,  # overwrite=True
        )
    except Exception:
        logger.exception("Regeneration failed for %s", doc_id)
        return

    await store.add_to_queue(doc_id, trigger=trigger, project_root=root)
    await store.scan(root, trigger=trigger)


@router.post("/docs/{doc_id:path}/regenerate", dependencies=[Depends(require_client_token)])
async def regenerate_doc(doc_id: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    background_tasks.add_task(_regenerate_doc, doc_id, "manual")
    return {"status": "regeneration_queued", "doc_id": doc_id}


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------


@router.get("/queue")
async def list_queue(
    persona: str | None = None,
    reviewed: bool | None = None,
) -> dict[str, Any]:
    items = await get_store().list_queue(persona=persona, reviewed=reviewed)
    return {"queue": items}


@router.post("/queue/{item_id}/approve", dependencies=[Depends(require_client_token)])
async def approve_item(item_id: str) -> dict[str, Any]:
    ok = await get_store().approve(item_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": f"Queue item {item_id!r} not found."},
        )
    return {"ok": True, "item_id": item_id}


@router.post("/queue/{item_id}/revert", dependencies=[Depends(require_client_token)])
async def revert_item(item_id: str) -> dict[str, Any]:
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
    h = await get_store().get_health()
    return {"quality": h.get("quality", {})}


# ---------------------------------------------------------------------------
# Git hook webhook
# ---------------------------------------------------------------------------


@router.post("/webhook/git")
async def git_webhook(background_tasks: BackgroundTasks) -> dict[str, Any]:
    background_tasks.add_task(_run_scan, "git_hook")
    return {"status": "scan_queued", "trigger": "git_hook"}
