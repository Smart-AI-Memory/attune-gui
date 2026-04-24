"""Pydantic request/response models shared across routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    python: str


class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    k: int = Field(3, ge=1, le=20)
    expand: bool = False
    rerank: bool = False


class RagHit(BaseModel):
    path: str  # CitedSource.template_path
    category: str  # CitedSource.category
    score: float
    excerpt: str | None = None


class RagQueryResponse(BaseModel):
    query: str
    k: int
    total_hits: int
    hits: list[RagHit]
    augmented_prompt: str | None = None
