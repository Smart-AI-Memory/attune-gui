"""Filesystem browsing — directories only, local use."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/fs", tags=["fs"])

_SHOW_HIDDEN = {".help", ".attune"}


@router.get("/browse")
async def browse(
    path: str = Query(default="~"),
    annotate: str | None = Query(
        default=None,
        description=(
            "If 'help', tag each entry (and the current dir) with "
            "`has_manifest: bool` indicating whether `features.yaml` "
            "is present. Used by the Commands page picker to highlight "
            "valid `.help/` dirs so users don't accidentally pick a "
            "Jinja templates dir or other unrelated folder."
        ),
    ),
) -> dict:
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

    annotate_help = annotate == "help"
    annotate_project = annotate == "project"

    def _has_manifest(p: Path) -> bool:
        """A `.help/`-style dir: contains `features.yaml` directly."""
        try:
            return (p / "features.yaml").is_file()
        except OSError:
            return False

    def _has_project_manifest(p: Path) -> bool:
        """A project root: contains `.help/features.yaml` as a child."""
        try:
            return (p / ".help" / "features.yaml").is_file()
        except OSError:
            return False

    entries = []
    for child in children:
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") and name not in _SHOW_HIDDEN:
            continue
        entry: dict = {"name": name, "path": str(child)}
        if annotate_help:
            entry["has_manifest"] = _has_manifest(child)
        elif annotate_project:
            entry["has_project_manifest"] = _has_project_manifest(child)
        entries.append(entry)

    parent = str(resolved.parent) if resolved.parent != resolved else None

    response: dict = {
        "path": str(resolved),
        "parent": parent,
        "entries": entries,
    }
    if annotate_help:
        response["has_manifest"] = _has_manifest(resolved)
    elif annotate_project:
        response["has_project_manifest"] = _has_project_manifest(resolved)
    return response
