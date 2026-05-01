"""Tests for unified search — merge logic and HTTP endpoint."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from attune_gui.app import create_app
from attune_gui.search import _rag_topic, merge
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# _rag_topic
# ---------------------------------------------------------------------------


def test_rag_topic_bundled_layout():
    assert _rag_topic("concepts/tool-planning.md") == "tool-planning"


def test_rag_topic_author_layout_concept():
    assert _rag_topic("auth/concept.md") == "auth"


def test_rag_topic_author_layout_task():
    assert _rag_topic("billing/task.md") == "billing"


def test_rag_topic_author_layout_reference():
    assert _rag_topic("pipeline/reference.md") == "pipeline"


def test_rag_topic_root_level_file():
    assert _rag_topic("tool-planning.md") == "tool-planning"


# ---------------------------------------------------------------------------
# merge() — pure unit tests with fake hits
# ---------------------------------------------------------------------------


def _rag_hit(path: str, score: float, content: str = "") -> object:
    """Fake CitedSource as returned by RagResult.citation.hits."""
    return SimpleNamespace(
        template_path=path,
        score=score,
        category=path.split("/")[0] if "/" in path else "",
        excerpt=content[:200] if content else None,
    )


def test_merge_rag_only():
    rag_hits = [_rag_hit("concepts/tool-planning.md", 2.0, "content")]
    results = merge([], rag_hits, limit=10)
    assert len(results) == 1
    r = results[0]
    assert r["topic"] == "tool-planning"
    assert r["source"] == "rag"
    assert r["score"] == pytest.approx(0.6, abs=0.01)


def test_merge_help_only():
    results = merge([("tool-planning", 0.9)], [], limit=10)
    assert len(results) == 1
    r = results[0]
    assert r["topic"] == "tool-planning"
    assert r["source"] == "help"
    assert r["score"] == pytest.approx(0.36, abs=0.01)


def test_merge_both_boosts_score():
    rag_hits = [_rag_hit("concepts/tool-planning.md", 2.0)]
    help_hits = [("tool-planning", 1.0)]
    results = merge(help_hits, rag_hits, limit=10)
    assert len(results) == 1
    r = results[0]
    assert r["source"] == "both"
    # (1.0*0.6 + 1.0*0.4) * 1.2 = 1.2 → capped at 1.0
    assert r["score"] == pytest.approx(1.0, abs=0.01)


def test_merge_boost_capped_at_one():
    rag_hits = [_rag_hit("concepts/foo.md", 4.0)]
    help_hits = [("foo", 1.0)]
    results = merge(help_hits, rag_hits, limit=10)
    assert results[0]["score"] <= 1.0


def test_merge_sorted_descending():
    rag_hits = [
        _rag_hit("concepts/low.md", 1.0),
        _rag_hit("concepts/high.md", 2.0),
    ]
    results = merge([], rag_hits, limit=10)
    assert results[0]["score"] >= results[1]["score"]


def test_merge_limit_respected():
    rag_hits = [_rag_hit(f"concepts/topic{i}.md", float(i + 1)) for i in range(20)]
    results = merge([], rag_hits, limit=5)
    assert len(results) == 5


def test_merge_distinct_topics_not_combined():
    rag_hits = [_rag_hit("concepts/planning.md", 2.0)]
    help_hits = [("security", 0.8)]
    results = merge(help_hits, rag_hits, limit=10)
    assert len(results) == 2
    sources = {r["topic"]: r["source"] for r in results}
    assert sources["planning"] == "rag"
    assert sources["security"] == "help"


def test_merge_excerpt_from_rag():
    content = "A" * 300
    rag_hits = [_rag_hit("concepts/foo.md", 2.0, content)]
    results = merge([], rag_hits, limit=10)
    assert len(results[0]["excerpt"]) == 200


def test_merge_empty_both():
    assert merge([], [], limit=10) == []


# ---------------------------------------------------------------------------
# HTTP endpoint — mocked engines
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    return TestClient(create_app(), raise_server_exceptions=True)


def _patch_search(help_return, rag_return):
    return (
        patch("attune_gui.routes.search._help_search", return_value=help_return),
        patch("attune_gui.routes.search._rag_search", return_value=rag_return),
        patch("attune_gui.routes.search.get_workspace", return_value=None),
    )


def test_endpoint_returns_merged_results(client):
    rag_hits = [_rag_hit("concepts/tool-planning.md", 2.0, "planning content")]
    help_hits = [("tool-planning", 0.9)]
    with (
        patch("attune_gui.routes.search._help_search", return_value=help_hits),
        patch("attune_gui.routes.search._rag_search", return_value=rag_hits),
        patch("attune_gui.routes.search.get_workspace", return_value=None),
    ):
        resp = client.get("/api/search/?q=planning")
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "planning"
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "both"


def test_endpoint_requires_q(client):
    resp = client.get("/api/search/")
    assert resp.status_code == 422


def test_endpoint_rejects_short_q(client):
    resp = client.get("/api/search/?q=")
    assert resp.status_code == 422


def test_endpoint_limit_param(client):
    rag_hits = [_rag_hit(f"concepts/t{i}.md", float(i + 1)) for i in range(20)]
    with (
        patch("attune_gui.routes.search._help_search", return_value=[]),
        patch("attune_gui.routes.search._rag_search", return_value=rag_hits),
        patch("attune_gui.routes.search.get_workspace", return_value=None),
    ):
        resp = client.get("/api/search/?q=test&limit=3")
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 3


def test_endpoint_invalid_workspace(client):
    resp = client.get("/api/search/?q=foo&workspace=/nonexistent/path/xyz")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# E2E — real engines, seeded workspace
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_rag_cache():
    from attune_gui.routes import rag

    rag._PIPELINES.clear()
    yield
    rag._PIPELINES.clear()


def test_e2e_seeded_workspace(client, tmp_path, monkeypatch):
    """Seed two templates in a workspace; both appear in unified search results."""
    templates_dir = tmp_path / ".help" / "templates"
    templates_dir.mkdir(parents=True)

    # Bundled-layout templates so HelpEngine can find slugs
    (templates_dir / "concepts").mkdir()
    (templates_dir / "concepts" / "authentication.md").write_text(
        "# authentication\nHow auth works."
    )
    (templates_dir / "concepts" / "billing.md").write_text("# billing\nHow billing works.")

    monkeypatch.setattr("attune_gui.routes.search.get_workspace", lambda: tmp_path)

    resp = client.get("/api/search/?q=authentication")
    assert resp.status_code == 200
    data = resp.json()
    topics = [r["topic"] for r in data["results"]]
    assert "authentication" in topics


def test_engine_failure_degrades_gracefully(client, monkeypatch):
    """_help_search catches its own errors and returns []; RAG results still come through."""
    monkeypatch.setattr("attune_gui.routes.search.get_workspace", lambda: None)
    rag_hits = [_rag_hit("concepts/tool-planning.md", 2.0, "planning content")]
    with (
        patch("attune_gui.routes.search._help_search", return_value=[]),
        patch("attune_gui.routes.search._rag_search", return_value=rag_hits),
    ):
        resp = client.get("/api/search/?q=planning")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "rag"
