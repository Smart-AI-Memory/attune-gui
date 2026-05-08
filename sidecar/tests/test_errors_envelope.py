"""Phase D4: every ``/api/*`` response renders through one error envelope.

These tests pin the envelope shape against fresh routes registered
directly on a stub app — that decouples the spec from the gui's
particular routes today and from any future ones added later.
"""

from __future__ import annotations

import pytest
from attune_gui.errors import error_envelope, install_handlers
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    install_handlers(app)
    router = APIRouter(prefix="/api")

    class Body(BaseModel):
        x: int

    @router.get("/dict-detail-400")
    async def _dict_400() -> dict:
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_input", "message": "Field x is invalid."},
        )

    @router.get("/string-detail-403")
    async def _string_403() -> dict:
        raise HTTPException(status_code=403, detail="Forbidden by policy.")

    @router.get("/dict-detail-500")
    async def _dict_500() -> dict:
        raise HTTPException(status_code=500, detail={"message": "boom", "code": "boom_code"})

    @router.get("/uncaught-500")
    async def _uncaught_500() -> dict:
        raise RuntimeError("secret internals: db password leaked")

    @router.post("/needs-body")
    async def _needs_body(body: Body) -> dict:
        return {"x": body.x}

    @router.get("/ok")
    async def _ok() -> dict:
        return {"hello": "world"}

    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    # raise_server_exceptions=False so the handler-rendered 500 surfaces in
    # the response instead of bubbling out of the test client as a Python
    # exception.
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# error_envelope helper
# ---------------------------------------------------------------------------


class TestErrorEnvelope:
    def test_with_code(self) -> None:
        assert error_envelope(message="oops", code="bad_thing") == {
            "detail": {"message": "oops", "code": "bad_thing"}
        }

    def test_default_code_is_none(self) -> None:
        assert error_envelope(message="oops") == {"detail": {"message": "oops", "code": None}}


# ---------------------------------------------------------------------------
# HTTPException handler
# ---------------------------------------------------------------------------


class TestHTTPExceptionEnvelope:
    def test_dict_detail_passes_through(self, client: TestClient) -> None:
        r = client.get("/api/dict-detail-400")
        assert r.status_code == 400
        assert r.json() == {"detail": {"code": "bad_input", "message": "Field x is invalid."}}

    def test_string_detail_normalized_to_dict(self, client: TestClient) -> None:
        r = client.get("/api/string-detail-403")
        assert r.status_code == 403
        body = r.json()
        assert set(body) == {"detail"}
        assert body["detail"] == {"message": "Forbidden by policy.", "code": None}

    def test_5xx_with_dict_keeps_message_defaults_code(self, client: TestClient) -> None:
        r = client.get("/api/dict-detail-500")
        assert r.status_code == 500
        assert r.json() == {"detail": {"message": "boom", "code": "boom_code"}}


# ---------------------------------------------------------------------------
# Uncaught exceptions
# ---------------------------------------------------------------------------


class TestUncaughtException:
    def test_500_envelope_does_not_leak_message(self, client: TestClient) -> None:
        r = client.get("/api/uncaught-500")
        assert r.status_code == 500
        body = r.json()
        assert body == {"detail": {"message": "internal error", "code": "internal_error"}}
        # The leaky message must NOT appear in the response body.
        assert "secret" not in r.text


# ---------------------------------------------------------------------------
# Validation 422 envelope
# ---------------------------------------------------------------------------


class TestValidationEnvelope:
    def test_missing_body_returns_envelope_with_validation_code(self, client: TestClient) -> None:
        r = client.post("/api/needs-body", json={})
        assert r.status_code == 422
        body = r.json()
        assert body["detail"]["code"] == "validation_error"
        assert body["detail"]["message"] == "Request validation failed."
        # Original Pydantic error list preserved as a sibling key for clients
        # that want field-level details.
        assert isinstance(body["detail"]["errors"], list)
        assert len(body["detail"]["errors"]) >= 1


# ---------------------------------------------------------------------------
# 200 path is untouched
# ---------------------------------------------------------------------------


def test_2xx_responses_are_unchanged(client: TestClient) -> None:
    r = client.get("/api/ok")
    assert r.status_code == 200
    assert r.json() == {"hello": "world"}
