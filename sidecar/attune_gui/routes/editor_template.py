"""Template GET / diff / save routes for the editor (M2 task #10).

Endpoints (under ``/api/corpus/<corpus_id>``):

- ``GET  /template?path=<rel>`` — load the template; returns
  ``{frontmatter, body, base_hash, mtime}``.
- ``POST /template/diff`` — compute a unified diff between the
  on-disk text and the client's draft, with stable per-hunk ids.
- ``POST /template/save`` — write the file atomically; supports
  per-hunk save via ``accepted_hunks``. 409 when ``base_hash``
  doesn't match the on-disk file (drift detected).

Path traversal is blocked: any normalized path that resolves outside
the corpus root is rejected with 400.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from attune_gui import editor_corpora

router = APIRouter(prefix="/api/corpus", tags=["editor-template"])


# -- models ---------------------------------------------------------


class TemplateResponse(BaseModel):
    rel_path: str
    frontmatter_text: str
    body: str
    text: str
    base_hash: str
    mtime: float


class DiffRequest(BaseModel):
    path: str = Field(..., min_length=1)
    draft_text: str
    base_hash: str = Field(..., min_length=1)


class HunkModel(BaseModel):
    hunk_id: str
    header: str
    lines: list[str]


class DiffResponse(BaseModel):
    rel_path: str
    base_hash: str
    new_hash: str
    hunks: list[HunkModel]


class SaveRequest(BaseModel):
    path: str = Field(..., min_length=1)
    draft_text: str
    base_hash: str = Field(..., min_length=1)
    accepted_hunks: list[str] | None = Field(
        default=None,
        description=(
            "If omitted or null, save the entire draft. If a list, save "
            "only the hunks whose ids are present (by re-applying them "
            "to the on-disk base)."
        ),
    )


class SaveResponse(BaseModel):
    rel_path: str
    new_hash: str
    mtime: float


# -- helpers --------------------------------------------------------


def _resolve(corpus_id: str, rel_path: str) -> tuple[Path, Path]:
    """Resolve ``(corpus_root, target_file)``; raise if path traversal."""
    entry = editor_corpora.get_corpus(corpus_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown corpus id: {corpus_id!r}",
        )
    root = Path(entry.path).resolve()
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path escapes corpus root: {rel_path!r}",
        ) from exc
    return root, candidate


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return ``(frontmatter_text, body)``. Empty fm if no block."""
    if not text.startswith("---"):
        return "", text
    after_open = text[3:]
    nl = after_open.find("\n")
    if nl == -1:
        return "", text
    rest = after_open[nl + 1 :]
    end = rest.find("\n---")
    if end == -1:
        return "", text
    fm = rest[:end]
    body_start = end + len("\n---")
    if rest[body_start : body_start + 1] == "\n":
        body_start += 1
    return fm, rest[body_start:]


def _atomic_write(target: Path, text: str) -> float:
    """Write ``text`` atomically; return the new mtime."""
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, target)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    return target.stat().st_mtime


def _rename_hunks(rel_path: str, old_text: str, new_text: str):
    """Lazy proxy for ``attune_rag.editor._rename._hunks``.

    Imported lazily so attune-gui's cold start does not require
    ``attune_rag.editor`` to be present until the editor routes are
    actually exercised. Surfaces a friendly 503 if the submodule is
    missing (e.g. shipped attune-rag has no editor support).
    """
    from attune_gui._editor_dep import require_editor_submodule  # noqa: PLC0415

    rename_mod = require_editor_submodule("_rename")
    return rename_mod._hunks(rel_path, old_text, new_text)


def _hunks(rel_path: str, old_text: str, new_text: str) -> list[dict[str, Any]]:
    """Re-export rename module's hunk computation."""
    return [h.to_dict() for h in _rename_hunks(rel_path, old_text, new_text)]


def _apply_accepted_hunks(
    base_text: str, draft_text: str, accepted_ids: list[str], rel_path: str
) -> str:
    """Apply only ``accepted_ids`` from the diff to ``base_text``.

    Strategy: split the diff into hunks; replay each line-based hunk
    on top of base. Unaccepted hunks are skipped (their lines stay as
    in base). This relies on ``difflib`` ordering, which is stable
    across hunks of a single diff.
    """
    hunks = _rename_hunks(rel_path, base_text, draft_text)
    accepted = {h.hunk_id for h in hunks if h.hunk_id in set(accepted_ids)}
    if not accepted:
        return base_text

    # Walk base_text line-by-line and replay accepted hunks.
    base_lines = base_text.splitlines(keepends=False)
    out: list[str] = []
    cursor = 0  # 0-indexed line position in base
    for h in hunks:
        start_line, base_count = _parse_hunk_header(h.header)
        # base_count is the number of base lines this hunk covers.
        # Copy unchanged base lines up to the hunk start.
        while cursor < start_line:
            if cursor < len(base_lines):
                out.append(base_lines[cursor])
            cursor += 1
        if h.hunk_id in accepted:
            # Apply: emit the `+`/' ' lines from the hunk body.
            for raw in h.lines:
                if raw.startswith("+"):
                    out.append(raw[1:])
                elif raw.startswith(" "):
                    out.append(raw[1:])
                # `-` lines drop from output (rejected base lines).
        else:
            # Skip: emit base lines in this hunk's range untouched.
            for offset in range(base_count):
                idx = start_line + offset
                if idx < len(base_lines):
                    out.append(base_lines[idx])
        cursor = start_line + base_count

    # Emit any remaining base lines past the last hunk.
    while cursor < len(base_lines):
        out.append(base_lines[cursor])
        cursor += 1

    trailing_nl = "\n" if base_text.endswith("\n") else ""
    return "\n".join(out) + trailing_nl


def _parse_hunk_header(header: str) -> tuple[int, int]:
    """Parse ``@@ -a,b +c,d @@`` → ``(0-indexed start, count)`` for base side."""
    import re

    m = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", header)
    if not m:
        return 0, 0
    start = int(m.group(1))
    count = int(m.group(2)) if m.group(2) else 1
    # difflib uses 1-indexed line numbers; for count==0 (pure
    # insertion) ``start`` is the line *before* the inserted content.
    if count == 0:
        return start, 0
    return start - 1, count


# -- routes ---------------------------------------------------------


@router.get("/{corpus_id}/template", response_model=TemplateResponse)
async def get_template(
    corpus_id: str,
    path: str = Query(..., min_length=1, alias="path"),
) -> TemplateResponse:
    _, target = _resolve(corpus_id, path)
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {path!r}",
        )
    text = target.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    return TemplateResponse(
        rel_path=path,
        frontmatter_text=fm,
        body=body,
        text=text,
        base_hash=_hash_text(text),
        mtime=target.stat().st_mtime,
    )


@router.post("/{corpus_id}/template/diff", response_model=DiffResponse)
async def diff_template(corpus_id: str, req: DiffRequest) -> DiffResponse:
    _, target = _resolve(corpus_id, req.path)
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {req.path!r}",
        )
    base_text = target.read_text(encoding="utf-8")
    if _hash_text(base_text) != req.base_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File changed on disk since load (base_hash mismatch).",
        )
    hunks = _hunks(req.path, base_text, req.draft_text)
    return DiffResponse(
        rel_path=req.path,
        base_hash=req.base_hash,
        new_hash=_hash_text(req.draft_text),
        hunks=[HunkModel(**h) for h in hunks],
    )


@router.post("/{corpus_id}/template/save", response_model=SaveResponse)
async def save_template(corpus_id: str, req: SaveRequest) -> SaveResponse:
    _, target = _resolve(corpus_id, req.path)
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {req.path!r}",
        )
    base_text = target.read_text(encoding="utf-8")
    if _hash_text(base_text) != req.base_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File changed on disk since load (base_hash mismatch).",
        )

    if req.accepted_hunks is None:
        new_text = req.draft_text
    else:
        new_text = _apply_accepted_hunks(base_text, req.draft_text, req.accepted_hunks, req.path)

    if new_text == base_text:
        # Nothing to write.
        return SaveResponse(rel_path=req.path, new_hash=req.base_hash, mtime=target.stat().st_mtime)

    mtime = _atomic_write(target, new_text)
    return SaveResponse(rel_path=req.path, new_hash=_hash_text(new_text), mtime=mtime)
