"""Consumer-side contract tests for the attune-rag boundary.

attune-gui's ``/api/rag/query`` and ``/api/rag/corpus-info`` routes
consume objects from :mod:`attune_rag` (RagPipeline.run, corpus.entries).
This file documents the *shape* gui expects and pins the consumer side
so payload-shape drift in attune-rag is caught at PR time rather than
at runtime.

Tests mock ``pipeline_for()`` at gui's import boundary — no real
attune-rag pipeline is constructed. That keeps the suite fast and
independent of a corpus on disk.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fakes shaped like attune-rag's documented public objects
# ---------------------------------------------------------------------------


def _fake_hit(
    template_path: str = "concepts/auth.md",
    category: str = "concept",
    score: float = 0.91,
    excerpt: str = "Auth is a process by which...",
) -> SimpleNamespace:
    """Mimic ``attune_rag.Citation.Hit`` shape — the gui consumes
    .template_path, .category, .score, .excerpt."""
    return SimpleNamespace(
        template_path=template_path,
        category=category,
        score=score,
        excerpt=excerpt,
    )


def _fake_run_result(
    *hits: SimpleNamespace, augmented_prompt: str = "AUGMENTED"
) -> SimpleNamespace:
    """Mimic ``RagPipeline.run`` return: object with .citation.hits and .augmented_prompt."""
    return SimpleNamespace(
        citation=SimpleNamespace(hits=list(hits)),
        augmented_prompt=augmented_prompt,
    )


class _FakePipeline:
    """Minimal RagPipeline shim for contract tests."""

    def __init__(self, *, hits: list[Any] | None = None, raises: Exception | None = None) -> None:
        self._hits = hits or []
        self._raises = raises
        self.corpus = SimpleNamespace(entries=lambda: iter(()))

    def run(self, query: str, k: int = 3) -> Any:
        if self._raises is not None:
            raise self._raises
        return _fake_run_result(*self._hits)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Re-use the standard sidecar TestClient — mirrors other route tests."""
    from attune_gui.app import create_app
    from attune_gui.security import current_session_token

    app = create_app()
    tc = TestClient(app)
    # Tag the client so callers can grab the token cleanly.
    tc.headers.update(
        {"Origin": "http://localhost:5173", "X-Attune-Client": current_session_token()}
    )
    return tc


# ---------------------------------------------------------------------------
# /api/rag/query — happy path
# ---------------------------------------------------------------------------


def test_query_response_unwraps_documented_hit_shape(client: TestClient) -> None:
    """``RagPipeline.run`` returns Citation.hits with the 4 named attrs;
    gui maps each to a RagHit. Verify the consumer side handles that shape."""
    fake = _FakePipeline(
        hits=[
            _fake_hit("concepts/auth.md", "concept", 0.95, "Auth excerpt"),
            _fake_hit("tasks/login.md", "task", 0.83, "Login excerpt"),
        ]
    )
    with patch("attune_gui.routes.rag.pipeline_for", return_value=fake):
        resp = client.post("/api/rag/query", json={"query": "auth", "k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "auth"
    assert body["k"] == 3
    assert body["total_hits"] == 2
    assert body["augmented_prompt"] == "AUGMENTED"
    # Each hit follows the documented RagHit fields.
    paths = {h["path"] for h in body["hits"]}
    assert paths == {"concepts/auth.md", "tasks/login.md"}
    for hit in body["hits"]:
        assert set(hit.keys()) >= {"path", "category", "score", "excerpt"}


def test_query_returns_empty_hits_when_pipeline_returns_none(client: TestClient) -> None:
    fake = _FakePipeline(hits=[])
    with patch("attune_gui.routes.rag.pipeline_for", return_value=fake):
        resp = client.post("/api/rag/query", json={"query": "no matches", "k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_hits"] == 0
    assert body["hits"] == []


# ---------------------------------------------------------------------------
# /api/rag/query — error envelope contract
# ---------------------------------------------------------------------------


def test_query_400_when_pipeline_raises_value_error(client: TestClient) -> None:
    """Gui surfaces ValueError from attune-rag as 400 with ``code: bad_query``."""
    fake = _FakePipeline(raises=ValueError("query too short"))
    with patch("attune_gui.routes.rag.pipeline_for", return_value=fake):
        resp = client.post("/api/rag/query", json={"query": "x", "k": 3})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "bad_query"
    assert "query too short" in detail["message"]


def test_query_500_when_pipeline_run_raises_unexpected(client: TestClient) -> None:
    """Generic exceptions from attune-rag map to 500 + ``code: rag_run_failed``."""
    fake = _FakePipeline(raises=RuntimeError("upstream blew up"))
    with patch("attune_gui.routes.rag.pipeline_for", return_value=fake):
        resp = client.post("/api/rag/query", json={"query": "anything", "k": 3})
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["code"] == "rag_run_failed"


def test_query_500_when_pipeline_construction_fails(client: TestClient) -> None:
    """attune-rag init failure (e.g. missing corpus) → 500 ``rag_init_failed``."""
    with patch(
        "attune_gui.routes.rag.pipeline_for",
        side_effect=ImportError("attune_rag not installed"),
    ):
        resp = client.post("/api/rag/query", json={"query": "anything", "k": 3})
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["code"] == "rag_init_failed"


# ---------------------------------------------------------------------------
# /api/rag/corpus-info
# ---------------------------------------------------------------------------


def test_corpus_info_aggregates_kinds_from_entry_paths(client: TestClient) -> None:
    """gui's corpus-info derives ``kinds`` from each entry's path prefix."""
    fake = _FakePipeline()
    fake.corpus = SimpleNamespace(
        entries=lambda: iter(
            [
                SimpleNamespace(path="concepts/auth.md"),
                SimpleNamespace(path="concepts/session.md"),
                SimpleNamespace(path="tasks/login.md"),
                SimpleNamespace(path="topfile-no-prefix.md"),  # filtered out
            ]
        )
    )
    with patch("attune_gui.routes.rag.pipeline_for", return_value=fake):
        resp = client.get("/api/rag/corpus-info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entry_count"] == 4
    assert body["kinds"] == ["concepts", "tasks"]
    # corpus_class is the runtime type name; SimpleNamespace here.
    assert "corpus_class" in body


def test_corpus_info_500_when_iteration_fails(client: TestClient) -> None:
    fake = _FakePipeline()

    def _boom() -> Any:
        raise RuntimeError("corpus broken")

    fake.corpus = SimpleNamespace(entries=_boom)
    with patch("attune_gui.routes.rag.pipeline_for", return_value=fake):
        resp = client.get("/api/rag/corpus-info")
    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert detail["code"] == "corpus_info_failed"
