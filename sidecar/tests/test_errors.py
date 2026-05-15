"""Tests for the unified error envelope (sidecar/attune_gui/errors.py)."""

from __future__ import annotations

import pytest
from attune_gui.errors import _normalize_detail, install_handlers
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


def _app_raising(detail: object, status_code: int) -> TestClient:
    app = FastAPI()
    install_handlers(app)

    @app.get("/boom")
    def _boom() -> None:
        raise HTTPException(status_code=status_code, detail=detail)

    return TestClient(app)


def test_dict_detail_4xx_preserves_extra_keys() -> None:
    """Routes can attach structured context (e.g. ``owning_path``)
    alongside ``message`` + ``code`` and the envelope must round-trip it."""

    client = _app_raising(
        detail={
            "code": "name_collision",
            "message": "duplicate alias 'bar'",
            "owning_path": "concepts/baz.md",
        },
        status_code=409,
    )
    res = client.get("/boom")
    assert res.status_code == 409
    body = res.json()
    assert body["detail"] == {
        "code": "name_collision",
        "message": "duplicate alias 'bar'",
        "owning_path": "concepts/baz.md",
    }


def test_string_detail_wraps_to_message_with_null_code() -> None:
    client = _app_raising(detail="bad input", status_code=400)
    res = client.get("/boom")
    assert res.status_code == 400
    assert res.json() == {"detail": {"message": "bad input", "code": None}}


def test_5xx_strips_extras_to_sanitize() -> None:
    """5xx responses must not leak structured context — only the
    canonical ``"internal error" / "internal_error"`` body."""

    client = _app_raising(
        detail={"message": "secret detail", "code": "x", "stack": "trace…"},
        status_code=500,
    )
    res = client.get("/boom")
    assert res.status_code == 500
    body = res.json()
    assert "stack" not in body["detail"]
    # 5xx with a usable message preserves it but tags code as internal_error.
    assert body["detail"]["message"] == "secret detail"
    # 5xx preserves caller-provided ``code`` if truthy; falls back to
    # ``"internal_error"`` only when missing/empty.
    assert body["detail"]["code"] == "x"


def test_5xx_with_no_useful_detail_returns_sanitized_envelope() -> None:
    client = _app_raising(detail="anything", status_code=500)
    res = client.get("/boom")
    assert res.json() == {"detail": {"message": "internal error", "code": "internal_error"}}


def test_normalize_detail_dict_missing_message_defaults_to_empty_string() -> None:
    out = _normalize_detail({"code": "x", "owning_path": "p"}, 409)
    assert out == {"code": "x", "owning_path": "p", "message": ""}


@pytest.mark.parametrize("status_code", [400, 404, 409, 422])
def test_dict_detail_extras_preserved_across_4xx_codes(status_code: int) -> None:
    out = _normalize_detail(
        {"code": "name_collision", "message": "m", "owning_path": "p"},
        status_code,
    )
    assert out["owning_path"] == "p"
