"""Filesystem browsing — directories only, local use."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/fs", tags=["fs"])

_SHOW_HIDDEN = {".help", ".attune"}


@router.get("/browse")
async def browse(path: str = Query(default="~")) -> dict:
    """Return directory listing for *path*.

    Only directories are included. Hidden entries (names starting with ``.'')
    are suppressed except for a small allow-list that is relevant to attune.
    """
    try:
        resolved = Path(path).expanduser().resolve()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid path: {exc}") from exc

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {resolved}")

    try:
        children = sorted(resolved.iterdir(), key=lambda p: p.name.lower())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    entries = []
    for child in children:
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") and name not in _SHOW_HIDDEN:
            continue
        entries.append({"name": name, "path": str(child)})

    parent = str(resolved.parent) if resolved.parent != resolved else None

    return {
        "path": str(resolved),
        "parent": parent,
        "entries": entries,
    }
