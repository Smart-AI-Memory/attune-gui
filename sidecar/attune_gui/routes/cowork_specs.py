"""Spec listing + authoring API.

Read endpoints:
    GET  /api/cowork/specs
    GET  /api/cowork/specs/template

Write endpoints (require X-Attune-Client):
    POST /api/cowork/specs
        Body: {"feature": "<slug>"}
        Creates ``<specs_root>/<slug>/requirements.md`` from the template's
        Phase 1 section. 409 if the directory already exists.

    POST /api/cowork/specs/{feature}/phase
        Body: {"phase": "design" | "tasks"}
        Bootstraps the next phase file from the template. 409 if the file
        already exists; 400 if the prerequisite phase is missing.

    PUT  /api/cowork/specs/{feature}/{phase}/status
        Body: {"status": "<value>"}
        Rewrites the ``**Status**:`` line in the named phase file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from attune_gui._fs import atomic_write
from attune_gui.security import require_client_token
from attune_gui.workspace import get_workspace

router = APIRouter(prefix="/api/cowork", tags=["cowork-specs"])

_STATUS_RE = re.compile(r"^\s*\*\*Status\*\*:.*$", re.MULTILINE)
_STATUS_VALUE_RE = re.compile(r"\*\*Status\*\*:\s*(\S+)")
_PHASE_FILES = ("requirements.md", "design.md", "tasks.md")
_PHASE_LABELS = {
    "requirements.md": "Requirements",
    "design.md": "Design",
    "tasks.md": "Tasks",
}
_PHASE_NAMES = ("requirements", "design", "tasks")
_VALID_STATUSES = ("draft", "in-review", "approved", "complete", "completed", "done")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def _read_status(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _STATUS_VALUE_RE.search(text)
    return m.group(1).strip() if m else None


def _scan_feature(feat_dir: Path) -> dict[str, Any]:
    present = [name for name in _PHASE_FILES if (feat_dir / name).is_file()]
    if not present:
        return {
            "feature": feat_dir.name,
            "files": [],
            "phase": None,
            "phase_label": None,
            "status": None,
        }

    most_advanced = present[-1]  # _PHASE_FILES is in order
    status = _read_status(feat_dir / most_advanced)

    return {
        "feature": feat_dir.name,
        "files": present,
        "phase": most_advanced,
        "phase_label": _PHASE_LABELS[most_advanced],
        "status": status,
    }


def _specs_root() -> Path | None:
    """Find the workspace ``specs/`` directory.

    Search order:
      1. ``ATTUNE_SPECS_ROOT`` env var (if set and a real dir)
      2. ``<workspace>/specs/``
      3. ``<workspace>/.help/specs/``
      4. ``Path.cwd() / "specs"``
      5. Walk up from cwd looking for the first ``specs/`` dir
    """
    env = os.environ.get("ATTUNE_SPECS_ROOT")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p

    ws = get_workspace()
    candidates: list[Path] = []
    if ws is not None:
        candidates.extend([ws / "specs", ws / ".help" / "specs"])
    candidates.append(Path.cwd() / "specs")

    for c in candidates:
        if c.is_dir():
            return c

    # Walk up from cwd
    cur = Path.cwd().resolve()
    for _ in range(8):  # cap depth so we don't crawl forever
        candidate = cur / "specs"
        if candidate.is_dir():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _template_path() -> Path | None:
    """Return the path to TEMPLATE.md if it exists alongside the specs root."""
    root = _specs_root()
    if root is None:
        return None
    candidate = root / "TEMPLATE.md"
    return candidate if candidate.is_file() else None


def _split_template_phases(template_text: str) -> dict[str, str]:
    """Split TEMPLATE.md into per-phase sections.

    The template separates phases with horizontal rules (``---`` on a line).
    Returns a dict keyed by phase name (``requirements``, ``design``,
    ``tasks``) → markdown body for that phase, with the ``**Status**``
    placeholder normalised to ``draft``.

    Falls back to bare phase headings if the template can't be parsed.
    """
    sections = re.split(r"\n---+\n", template_text)
    # Sections look like: [preamble, phase1, phase2, phase3, phase4]
    # We want to find each phase by its header.
    phase_sections: dict[str, str] = {}
    for sec in sections:
        body = sec.strip()
        if not body:
            continue
        for name, heading in (
            ("requirements", "## Phase 1: Requirements"),
            ("design", "## Phase 2: Design"),
            ("tasks", "## Phase 3: Tasks"),
        ):
            if heading in body:
                # Normalise the Status line to a single value.
                normalised = _STATUS_RE.sub("**Status**: draft", body, count=1)
                phase_sections[name] = normalised
                break
    return phase_sections


def _bootstrap_text(phase: str, feature: str, template_path: Path | None) -> str:
    """Build the file body for a freshly-created phase."""
    title = f"# Spec: {feature}\n\n"
    if template_path is not None:
        try:
            sections = _split_template_phases(template_path.read_text(encoding="utf-8"))
        except OSError:
            sections = {}
        body = sections.get(phase)
        if body:
            return title + body + "\n"

    # Fallback: minimal stub
    label = phase.capitalize()
    return (
        f"{title}## Phase: {label}\n\n"
        f"**Status**: draft\n\n"
        f"_Fill in the {label.lower()} for this feature._\n"
    )


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid slug. Use lowercase letters, digits, and dashes "
                "(start with a letter or digit; max 63 chars)."
            ),
        )


def _validate_phase(phase: str) -> None:
    if phase not in _PHASE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown phase: {phase!r}. Valid: {', '.join(_PHASE_NAMES)}",
        )


def _validate_status(status: str) -> None:
    if status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status!r}. Valid: {', '.join(_VALID_STATUSES)}",
        )


# ---------------------------------------------------------------------------
# Read routes
# ---------------------------------------------------------------------------


@router.get("/specs")
async def list_specs() -> dict[str, Any]:
    """Return a list of feature specs found under the workspace specs root."""
    root = _specs_root()
    if root is None:
        return {"specs": [], "specs_root": None}

    specs = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        # Skip dot-dirs like .git
        if child.name.startswith("."):
            continue
        specs.append(_scan_feature(child))

    return {"specs": specs, "specs_root": str(root)}


@router.get("/specs/template")
async def get_template() -> dict[str, Any]:
    """Return the canonical spec template body, or null when none is found."""
    tpl = _template_path()
    if tpl is None:
        return {"path": None, "content": None}
    try:
        return {"path": str(tpl), "content": tpl.read_text(encoding="utf-8")}
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not read template: {exc}") from exc


# ---------------------------------------------------------------------------
# Write routes
# ---------------------------------------------------------------------------


class CreateSpecRequest(BaseModel):
    feature: str = Field(..., min_length=1, max_length=63)


@router.post("/specs", status_code=201, dependencies=[Depends(require_client_token)])
async def create_spec(body: CreateSpecRequest) -> dict[str, Any]:
    """Create a new feature directory with a starter ``requirements.md``."""
    _validate_slug(body.feature)

    root = _specs_root()
    if root is None:
        raise HTTPException(status_code=404, detail="Specs root not found.")

    feat_dir = root / body.feature
    if feat_dir.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Spec {body.feature!r} already exists.",
        )

    target = feat_dir / "requirements.md"
    text = _bootstrap_text("requirements", body.feature, _template_path())
    try:
        atomic_write(target, text)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Write failed: {exc}") from exc

    return {
        "feature": body.feature,
        "phase": "requirements.md",
        "path": str(target.relative_to(root)),
    }


class AddPhaseRequest(BaseModel):
    phase: str  # "design" | "tasks" (requirements is implicit via create)


@router.post(
    "/specs/{feature}/phase",
    status_code=201,
    dependencies=[Depends(require_client_token)],
)
async def add_phase(feature: str, body: AddPhaseRequest) -> dict[str, Any]:
    """Bootstrap the next phase file (``design.md`` or ``tasks.md``)."""
    _validate_slug(feature)
    _validate_phase(body.phase)
    if body.phase == "requirements":
        raise HTTPException(
            status_code=400,
            detail="Requirements is created automatically by POST /api/cowork/specs.",
        )

    root = _specs_root()
    if root is None:
        raise HTTPException(status_code=404, detail="Specs root not found.")

    feat_dir = root / feature
    if not feat_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Spec {feature!r} not found.")

    # Enforce ordering: design requires requirements, tasks requires design.
    prereqs = {"design": "requirements.md", "tasks": "design.md"}
    prereq = prereqs[body.phase]
    if not (feat_dir / prereq).is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add {body.phase} until {prereq} exists.",
        )

    target = feat_dir / f"{body.phase}.md"
    if target.exists():
        raise HTTPException(
            status_code=409,
            detail=f"{body.phase}.md already exists for spec {feature!r}.",
        )

    text = _bootstrap_text(body.phase, feature, _template_path())
    try:
        atomic_write(target, text)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Write failed: {exc}") from exc

    return {
        "feature": feature,
        "phase": f"{body.phase}.md",
        "path": str(target.relative_to(root)),
    }


@router.put(
    "/specs/{feature}/{phase}/status",
    dependencies=[Depends(require_client_token)],
)
async def update_status(
    feature: str,
    phase: str,
    body: dict[str, Any] = Body(...),  # noqa: B008
) -> dict[str, Any]:
    """Rewrite the ``**Status**:`` line in the named phase file."""
    _validate_slug(feature)
    _validate_phase(phase)
    status = body.get("status")
    if not isinstance(status, str):
        raise HTTPException(status_code=422, detail="Body must include `status` (string).")
    _validate_status(status)

    root = _specs_root()
    if root is None:
        raise HTTPException(status_code=404, detail="Specs root not found.")

    target = root / feature / f"{phase}.md"
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"{phase}.md not found for {feature!r}.")

    try:
        original = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Read failed: {exc}") from exc

    if not _STATUS_VALUE_RE.search(original):
        # No existing line — insert one near the top, after the title if present.
        lines = original.splitlines()
        insert_at = 1 if lines and lines[0].startswith("# ") else 0
        lines.insert(insert_at, f"\n**Status**: {status}\n")
        new_text = "\n".join(lines) + ("\n" if not original.endswith("\n") else "")
    else:
        new_text = _STATUS_RE.sub(f"**Status**: {status}", original, count=1)

    try:
        atomic_write(target, new_text)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Write failed: {exc}") from exc

    return {"feature": feature, "phase": f"{phase}.md", "status": status}
