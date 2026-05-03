"""File read/write/pin/render endpoints for the Cowork dashboard.

Distinct URL prefixes are used per action so the greedy ``:path`` converter
cannot swallow action suffixes.

GET    /api/cowork/files/raw/{root}/{path:path}       — read raw file
PUT    /api/cowork/files/raw/{root}/{path:path}       — write raw file
GET    /api/cowork/files/rendered/{root}/{path:path}  — markdown → HTML
POST   /api/cowork/files/pin/{root}/{path:path}       — toggle ``manual``

Allowed roots:
  - ``templates`` → resolved by cowork_templates._templates_root()
  - ``specs``     → resolved by cowork_specs._specs_root()
  - ``summaries`` → workspace ``.help/`` directory
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import frontmatter
import markdown as md_lib
from fastapi import APIRouter, Body, Depends, HTTPException

from attune_gui.security import require_client_token
from attune_gui.workspace import get_workspace

router = APIRouter(prefix="/api/cowork/files", tags=["cowork-files"])


# ---------------------------------------------------------------------------
# Root resolution (delegates to the listing routes for parity)
# ---------------------------------------------------------------------------


def _resolve_root(root: str) -> Path:
    if root == "specs":
        from attune_gui.routes.cowork_specs import _specs_root  # noqa: PLC0415

        base = _specs_root()
        if base is None:
            raise HTTPException(status_code=404, detail="Specs root not found.")
        return base

    if root == "templates":
        from attune_gui.routes.cowork_templates import _templates_root  # noqa: PLC0415

        base = _templates_root()
        if base is None:
            raise HTTPException(status_code=404, detail="Templates root not found.")
        return base

    if root == "summaries":
        ws = get_workspace()
        if ws is None:
            raise HTTPException(status_code=400, detail="Workspace not configured.")
        help_dir = ws / ".help"
        if not help_dir.is_dir():
            raise HTTPException(status_code=404, detail="No .help directory in workspace.")
        return help_dir

    raise HTTPException(status_code=400, detail=f"Unknown root: {root!r}")


def _resolve_path(root: str, rel: str) -> Path:
    base = _resolve_root(root).resolve()
    candidate = (base / rel).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path traversal blocked.") from exc
    return candidate


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, target)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@router.get("/raw/{root}/{path:path}")
async def read_file(root: str, path: str) -> dict[str, Any]:
    target = _resolve_path(root, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    raw = target.read_text(encoding="utf-8")
    manual = False
    if target.suffix == ".md":
        try:
            post = frontmatter.loads(raw)
            manual = bool(post.metadata.get("manual"))
        except Exception:  # noqa: BLE001
            manual = False

    return {"path": path, "root": root, "content": raw, "manual": manual}


# ---------------------------------------------------------------------------
# Render markdown → HTML fragment
# ---------------------------------------------------------------------------


@router.get("/rendered/{root}/{path:path}")
async def render_file(root: str, path: str) -> dict[str, Any]:
    target = _resolve_path(root, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    raw = target.read_text(encoding="utf-8")
    if target.suffix == ".md":
        try:
            post = frontmatter.loads(raw)
            body = post.content
        except Exception:  # noqa: BLE001
            body = raw
    else:
        body = raw

    html = md_lib.markdown(
        body,
        extensions=["tables", "fenced_code", "codehilite", "toc", "sane_lists"],
        output_format="html5",
    )
    return {"path": path, "root": root, "html": html}


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


@router.put("/raw/{root}/{path:path}", dependencies=[Depends(require_client_token)])
async def write_file(
    root: str,
    path: str,
    body: dict[str, Any] = Body(...),  # noqa: B008
) -> dict[str, Any]:
    target = _resolve_path(root, path)
    content = body.get("content")
    if not isinstance(content, str):
        raise HTTPException(status_code=422, detail="Body must include `content` (string).")

    try:
        _atomic_write(target, content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Write failed: {exc}") from exc

    return {"path": path, "root": root, "saved": True}


# ---------------------------------------------------------------------------
# Pin toggle
# ---------------------------------------------------------------------------


@router.post("/pin/{root}/{path:path}", dependencies=[Depends(require_client_token)])
async def toggle_pin(
    root: str,
    path: str,
    body: dict[str, Any] = Body(...),  # noqa: B008
) -> dict[str, Any]:
    if root != "templates":
        raise HTTPException(status_code=400, detail="Pin is only valid for the `templates` root.")

    target = _resolve_path(root, path)
    if not target.is_file() or target.suffix != ".md":
        raise HTTPException(status_code=400, detail="Pin requires a Markdown template file.")

    manual = bool(body.get("manual"))
    raw = target.read_text(encoding="utf-8")
    try:
        post = frontmatter.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not parse frontmatter: {exc}") from exc

    if manual:
        post.metadata["manual"] = True
    else:
        post.metadata.pop("manual", None)

    new_text = frontmatter.dumps(post) + "\n"
    try:
        _atomic_write(target, new_text)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Write failed: {exc}") from exc

    return {"path": path, "root": root, "manual": manual}
