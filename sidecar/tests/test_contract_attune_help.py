"""Consumer-side contract tests for the attune-help boundary.

attune-gui's ``/api/help/topics`` and ``/api/help/search`` routes
consume :class:`attune_help.HelpEngine`. This file pins the consumer
side of that contract: payload shapes returned to the frontend, and
the error envelope shape when the engine fails.

Tests mock ``attune_help.HelpEngine`` at gui's import boundary so no
real corpus is needed.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from attune_gui.app import create_app

    app = create_app()
    tc = TestClient(app)
    tc.headers.update({"Origin": "http://localhost:5173"})
    return tc


# ---------------------------------------------------------------------------
# /api/help/topics
# ---------------------------------------------------------------------------


def test_list_topics_returns_array_and_count(client: TestClient) -> None:
    fake_engine = MagicMock()
    fake_engine.list_topics.return_value = ["auth", "memory", "rag"]
    with patch("attune_help.HelpEngine", return_value=fake_engine):
        resp = client.get("/api/help/topics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["topics"] == ["auth", "memory", "rag"]
    assert body["count"] == 3


def test_list_topics_passes_type_filter_through(client: TestClient) -> None:
    fake_engine = MagicMock()
    fake_engine.list_topics.return_value = ["concept-only"]
    with patch("attune_help.HelpEngine", return_value=fake_engine):
        resp = client.get("/api/help/topics?type_filter=concept")
    assert resp.status_code == 200
    fake_engine.list_topics.assert_called_once_with(type_filter="concept")


def test_list_topics_500_when_engine_raises(client: TestClient) -> None:
    """Engine errors map to a generic 500 envelope (gui's global error handler
    sanitizes the detail to ``{code: internal_error}`` — verify the contract)."""
    fake_engine = MagicMock()
    fake_engine.list_topics.side_effect = RuntimeError("corpus missing")
    with patch("attune_help.HelpEngine", return_value=fake_engine):
        resp = client.get("/api/help/topics")
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert isinstance(detail, dict)
    assert detail.get("code") == "internal_error"


# ---------------------------------------------------------------------------
# /api/help/search
# ---------------------------------------------------------------------------


def test_search_returns_query_results_and_count(client: TestClient) -> None:
    fake_engine = MagicMock()
    fake_engine.search.return_value = [
        {"slug": "auth", "score": 0.9},
        {"slug": "memory", "score": 0.6},
    ]
    with patch("attune_help.HelpEngine", return_value=fake_engine):
        resp = client.get("/api/help/search?q=auth")
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "auth"
    assert body["count"] == 2
    assert body["results"][0]["slug"] == "auth"


def test_search_rejects_empty_query(client: TestClient) -> None:
    """``q`` requires min_length=1 — Pydantic surfaces 422."""
    resp = client.get("/api/help/search?q=")
    assert resp.status_code == 422


def test_search_clamps_limit_to_documented_range(client: TestClient) -> None:
    """Limits below 1 or above 50 must be rejected at the boundary."""
    resp = client.get("/api/help/search?q=foo&limit=0")
    assert resp.status_code == 422
    resp = client.get("/api/help/search?q=foo&limit=51")
    assert resp.status_code == 422


def test_search_passes_limit_to_engine(client: TestClient) -> None:
    fake_engine = MagicMock()
    fake_engine.search.return_value = []
    with patch("attune_help.HelpEngine", return_value=fake_engine):
        resp = client.get("/api/help/search?q=foo&limit=25")
    assert resp.status_code == 200
    fake_engine.search.assert_called_once_with("foo", limit=25)


def test_search_500_when_engine_raises(client: TestClient) -> None:
    fake_engine = MagicMock()
    fake_engine.search.side_effect = RuntimeError("index corrupt")
    with patch("attune_help.HelpEngine", return_value=fake_engine):
        resp = client.get("/api/help/search?q=foo")
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert isinstance(detail, dict)
    assert detail.get("code") == "internal_error"


# ---------------------------------------------------------------------------
# Construction contract
# ---------------------------------------------------------------------------


def test_engine_constructor_called_with_resolved_template_dir(
    client: TestClient, tmp_path: Any
) -> None:
    """When ``template_dir`` is provided, gui resolves it via Path.resolve()
    before passing to HelpEngine."""
    fake_engine = MagicMock()
    fake_engine.list_topics.return_value = []
    with patch("attune_help.HelpEngine", return_value=fake_engine) as ctor:
        resp = client.get(f"/api/help/topics?template_dir={tmp_path}")
    assert resp.status_code == 200
    kwargs = ctor.call_args.kwargs
    assert kwargs["renderer"] == "plain"
    assert kwargs["template_dir"] == tmp_path.resolve()


def test_engine_constructor_called_with_none_when_no_template_dir(
    client: TestClient,
) -> None:
    fake_engine = MagicMock()
    fake_engine.list_topics.return_value = []
    with patch("attune_help.HelpEngine", return_value=fake_engine) as ctor:
        resp = client.get("/api/help/topics")
    assert resp.status_code == 200
    assert ctor.call_args.kwargs["template_dir"] is None
