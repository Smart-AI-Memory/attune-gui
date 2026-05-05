"""Lint + autocomplete proxy routes for the template editor (M2 task #11).

Both endpoints delegate to :mod:`attune_rag.editor`. The corpus is
resolved per-request from the registry so the browser can lint
against any registered corpus without a workspace switch round-trip.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from attune_gui import editor_corpora

router = APIRouter(prefix="/api/corpus", tags=["editor-lint"])


class LintRequest(BaseModel):
    path: str = Field(..., min_length=1)
    text: str


class DiagnosticModel(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    line: int
    col: int
    end_line: int
    end_col: int


class AliasInfoModel(BaseModel):
    alias: str
    template_path: str
    template_name: str


@router.post("/{corpus_id}/lint", response_model=list[DiagnosticModel])
async def lint(corpus_id: str, req: LintRequest) -> list[DiagnosticModel]:
    from attune_gui._editor_dep import require_editor_submodule  # noqa: PLC0415

    editor_mod = require_editor_submodule("")

    try:
        corpus = editor_corpora.load_corpus(corpus_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    diagnostics = editor_mod.lint_template(req.text, req.path, corpus)
    return [DiagnosticModel(**d.to_dict()) for d in diagnostics]


@router.get("/{corpus_id}/autocomplete")
async def autocomplete(
    corpus_id: str,
    kind: Literal["tag", "alias"] = Query(...),
    prefix: str = Query("", description="Case-insensitive prefix; empty matches all"),
    limit: int = Query(50, ge=1, le=500),
) -> list:
    from attune_gui._editor_dep import require_editor_submodule  # noqa: PLC0415

    editor_mod = require_editor_submodule("")

    try:
        corpus = editor_corpora.load_corpus(corpus_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if kind == "tag":
        return editor_mod.autocomplete_tags(corpus, prefix, limit)
    aliases = editor_mod.autocomplete_aliases(corpus, prefix, limit)
    return [AliasInfoModel(**info).model_dump() for info in aliases]
