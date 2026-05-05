"""Tests for /api/help/topics and /api/help/search."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# /api/help/topics
# ---------------------------------------------------------------------------


def test_topics_returns_list_and_count(client: TestClient) -> None:
    engine = MagicMock()
    engine.list_topics.return_value = ["auth", "memory", "rag"]
    with patch("attune_help.HelpEngine", return_value=engine):
        r = client.get("/api/help/topics")
    assert r.status_code == 200
    body = r.json()
    assert body["topics"] == ["auth", "memory", "rag"]
    assert body["count"] == 3


def test_topics_passes_type_filter_to_engine(client: TestClient) -> None:
    engine = MagicMock()
    engine.list_topics.return_value = []
    with patch("attune_help.HelpEngine", return_value=engine):
        r = client.get("/api/help/topics", params={"type_filter": "concept"})
    assert r.status_code == 200
    engine.list_topics.assert_called_once_with(type_filter="concept")


def test_topics_resolves_template_dir(client: TestClient, tmp_path: Path) -> None:
    engine = MagicMock()
    engine.list_topics.return_value = []
    with patch("attune_help.HelpEngine", return_value=engine) as he:
        r = client.get("/api/help/topics", params={"template_dir": str(tmp_path)})
    assert r.status_code == 200
    kwargs = he.call_args.kwargs
    assert kwargs["template_dir"] == tmp_path.resolve()
    assert kwargs["renderer"] == "plain"


def test_topics_engine_failure_returns_500(client: TestClient) -> None:
    with patch("attune_help.HelpEngine", side_effect=RuntimeError("boom")):
        r = client.get("/api/help/topics")
    assert r.status_code == 500
    assert "boom" in r.json()["detail"]


# ---------------------------------------------------------------------------
# /api/help/search
# ---------------------------------------------------------------------------


def test_search_returns_results_and_count(client: TestClient) -> None:
    engine = MagicMock()
    engine.search.return_value = [("auth", 0.9), ("memory", 0.4)]
    with patch("attune_help.HelpEngine", return_value=engine):
        r = client.get("/api/help/search", params={"q": "auth"})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "auth"
    assert body["count"] == 2


def test_search_respects_limit(client: TestClient) -> None:
    engine = MagicMock()
    engine.search.return_value = []
    with patch("attune_help.HelpEngine", return_value=engine):
        r = client.get("/api/help/search", params={"q": "auth", "limit": 5})
    assert r.status_code == 200
    engine.search.assert_called_once_with("auth", limit=5)


def test_search_rejects_empty_query(client: TestClient) -> None:
    """min_length=1 on the query — FastAPI returns 422 for an empty string."""
    r = client.get("/api/help/search", params={"q": ""})
    assert r.status_code == 422


def test_search_rejects_out_of_range_limit(client: TestClient) -> None:
    """limit must be 1..50."""
    r = client.get("/api/help/search", params={"q": "auth", "limit": 0})
    assert r.status_code == 422
    r = client.get("/api/help/search", params={"q": "auth", "limit": 999})
    assert r.status_code == 422


def test_search_engine_failure_returns_500(client: TestClient) -> None:
    with patch("attune_help.HelpEngine", side_effect=RuntimeError("kaput")):
        r = client.get("/api/help/search", params={"q": "auth"})
    assert r.status_code == 500
    assert "kaput" in r.json()["detail"]
