"""Corpora-registry routes for the template editor (M2 task #7).

Endpoints (under ``/api/corpus``):

- ``GET  /api/corpus``           — list registered corpora + active id
- ``POST /api/corpus/active``    — switch the active corpus
- ``POST /api/corpus/register``  — add a new corpus directory
- ``POST /api/corpus/resolve``   — given an absolute path, find which
  registered corpus owns it (and the rel-path inside it)
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from attune_gui import editor_corpora
from attune_gui.security import require_client_token

router = APIRouter(prefix="/api/corpus", tags=["editor-corpus"])


class CorpusModel(BaseModel):
    id: str
    name: str
    path: str
    kind: Literal["source", "generated", "ad-hoc"]
    warn_on_edit: bool


class ListResponse(BaseModel):
    active: str | None
    corpora: list[CorpusModel]


class ActiveRequest(BaseModel):
    id: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    kind: Literal["source", "generated", "ad-hoc"] = "source"
    warn_on_edit: bool | None = None


class ResolveRequest(BaseModel):
    abs_path: str = Field(min_length=1)


class ResolveResponse(BaseModel):
    corpus_id: str
    rel_path: str


def _to_model(entry: editor_corpora.CorpusEntry) -> CorpusModel:
    return CorpusModel(
        id=entry.id,
        name=entry.name,
        path=entry.path,
        kind=entry.kind,
        warn_on_edit=entry.warn_on_edit,
    )


@router.get("", response_model=ListResponse)
async def list_corpora() -> ListResponse:
    reg = editor_corpora.load_registry()
    return ListResponse(
        active=reg.active,
        corpora=[_to_model(c) for c in reg.corpora],
    )


@router.post(
    "/active",
    response_model=CorpusModel,
    dependencies=[Depends(require_client_token)],
)
async def set_active(req: ActiveRequest) -> CorpusModel:
    try:
        entry = editor_corpora.set_active(req.id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_model(entry)


@router.post(
    "/register",
    response_model=CorpusModel,
    dependencies=[Depends(require_client_token)],
)
async def register(req: RegisterRequest) -> CorpusModel:
    try:
        entry = editor_corpora.register(
            req.name,
            req.path,
            kind=req.kind,
            warn_on_edit=req.warn_on_edit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_model(entry)


@router.post(
    "/resolve",
    response_model=ResolveResponse,
    dependencies=[Depends(require_client_token)],
)
async def resolve(req: ResolveRequest) -> ResolveResponse:
    abs_path = str(Path(req.abs_path).expanduser())
    found = editor_corpora.resolve_path(abs_path)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered corpus contains {abs_path!r}",
        )
    entry, rel_path = found
    return ResolveResponse(corpus_id=entry.id, rel_path=rel_path)
