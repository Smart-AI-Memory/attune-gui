"""Unified error envelope for the gui's HTTP API.

Phase D4 of the architecture-realignment spec, finding #7. Every
``/api/*`` response — whether raised as :class:`HTTPException` from a
route, raised as an ordinary :class:`Exception`, or returned through
FastAPI's own validation machinery — renders through one shape::

    4xx → {"detail": {"message": str, "code": str | None}}
    5xx → {"detail": {"message": "internal error", "code": "internal_error"}}

The two exception handlers below register at app construction time.
Routes already raising ``HTTPException(detail={"code": ..., "message": ...})``
flow through unchanged; routes raising ``HTTPException(detail="some string")``
get normalized into the dict shape; uncaught exceptions become
sanitized 500s.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def error_envelope(
    *,
    message: str,
    code: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Build the canonical ``{"detail": {"message": ..., "code": ...}}`` body."""

    return {"detail": {"message": message, "code": code}}


def _normalize_detail(detail: Any, status_code: int) -> dict[str, Any]:
    """Coerce a ``HTTPException.detail`` into the envelope's inner shape.

    - A dict already shaped ``{"message": str, "code": ...}`` passes through
      with a defaulted ``code: None`` if the key is missing.
    - A string detail is wrapped: ``{"message": detail, "code": None}``.
    - A 5xx with no useful detail is replaced with the standard
      ``"internal error" / "internal_error"`` body so we never leak a
      raw exception message in a server-error response.
    - Anything else (lists, ints) is stringified for the message and
      tagged with ``"code": None`` so clients can still parse the shape.
    """

    if status_code >= 500:
        if isinstance(detail, dict) and "message" in detail:
            return {"message": detail["message"], "code": detail.get("code") or "internal_error"}
        return {"message": "internal error", "code": "internal_error"}

    if isinstance(detail, dict):
        # Preserve any extra keys the route attached (e.g. ``owning_path``
        # on rename collisions). The 5xx branch above keeps server
        # errors sanitized; here on 4xx the route is the trusted author.
        return {
            **detail,
            "message": str(detail.get("message", "")),
            "code": detail.get("code"),
        }

    if isinstance(detail, str):
        return {"message": detail, "code": None}

    return {"message": str(detail), "code": None}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Render every :class:`HTTPException` through :func:`error_envelope`."""

    body = {"detail": _normalize_detail(exc.detail, exc.status_code)}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Render FastAPI's request-validation 422s through :func:`error_envelope`.

    The original ``exc.errors()`` list is preserved under ``code: "validation_error"``'s
    ``message`` so clients have human-readable text without losing the details — the
    raw error list moves to a sibling ``errors`` key inside ``detail``.
    """

    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": "Request validation failed.",
                "code": "validation_error",
                "errors": exc.errors(),
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler for anything that escapes the route layer.

    Logs the exception with a stack trace; returns the canonical 500
    envelope without leaking the raw message to the client.
    """

    logger.exception("unhandled error in %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": {"message": "internal error", "code": "internal_error"}},
    )


def install_handlers(app: FastAPI) -> None:
    """Register the three handlers on ``app`` at construction time."""

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
