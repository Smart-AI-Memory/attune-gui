"""Tests for /api/rag routes and the workspace-keyed pipeline cache."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from attune_gui.app import create_app
from attune_gui.routes import rag
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    """Clear the module-global pipeline cache between tests."""
    rag._PIPELINES.clear()
    yield
    rag._PIPELINES.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def session_token(client: TestClient) -> str:
    return client.get("/api/session/token").json()["token"]


# ---------------------------------------------------------------------------
# _get_pipeline cache
# ---------------------------------------------------------------------------


class TestPipelineCache:
    def test_default_pipeline_uses_bundled_corpus(self) -> None:
        with (
            patch("attune_rag.RagPipeline") as rag_pipeline_class,
            patch("attune_rag.QueryExpander") as query_expander_class,
        ):
            rag_pipeline_class.return_value = "pipeline"
            rag._get_pipeline(None)
        # corpus=None means "fall back to the bundled AttuneHelpCorpus"
        kwargs = rag_pipeline_class.call_args.kwargs
        assert kwargs["corpus"] is None
        assert kwargs["expander"] is query_expander_class.return_value

    def test_workspace_with_templates_uses_directory_corpus(self, tmp_path: Path) -> None:
        templates = tmp_path / ".help" / "templates"
        templates.mkdir(parents=True)
        with (
            patch("attune_rag.DirectoryCorpus") as directory_corpus_class,
            patch("attune_rag.QueryExpander"),
            patch("attune_rag.RagPipeline") as rag_pipeline_class,
        ):
            rag._get_pipeline(tmp_path)
        directory_corpus_class.assert_called_once_with(templates)
        assert rag_pipeline_class.call_args.kwargs["corpus"] is directory_corpus_class.return_value

    def test_workspace_without_templates_falls_back(self, tmp_path: Path) -> None:
        # No .help/templates dir
        with (
            patch("attune_rag.DirectoryCorpus") as directory_corpus_class,
            patch("attune_rag.QueryExpander"),
            patch("attune_rag.RagPipeline") as rag_pipeline_class,
        ):
            rag._get_pipeline(tmp_path)
        directory_corpus_class.assert_not_called()
        assert rag_pipeline_class.call_args.kwargs["corpus"] is None

    def test_pipeline_is_cached_per_workspace(self, tmp_path: Path) -> None:
        with (
            patch("attune_rag.DirectoryCorpus"),
            patch("attune_rag.QueryExpander"),
            patch("attune_rag.RagPipeline") as rag_pipeline_class,
        ):
            rag_pipeline_class.side_effect = lambda **k: MagicMock(name=f"p-{id(k)}")
            p1 = rag._get_pipeline(tmp_path)
            p2 = rag._get_pipeline(tmp_path)
        assert p1 is p2

    def test_invalidate_drops_cached_pipeline(self, tmp_path: Path) -> None:
        with (
            patch("attune_rag.DirectoryCorpus"),
            patch("attune_rag.QueryExpander"),
            patch("attune_rag.RagPipeline") as rag_pipeline_class,
        ):
            rag_pipeline_class.side_effect = lambda **k: MagicMock()
            rag._get_pipeline(tmp_path)
            assert tmp_path in rag._PIPELINES
            rag.invalidate(tmp_path)
            assert tmp_path not in rag._PIPELINES


# ---------------------------------------------------------------------------
# POST /api/rag/query
# ---------------------------------------------------------------------------


class TestRagQuery:
    def _stub_pipeline(self, hits: list[SimpleNamespace], augmented: str) -> MagicMock:
        result = SimpleNamespace(citation=SimpleNamespace(hits=hits), augmented_prompt=augmented)
        pipeline = MagicMock()
        pipeline.run.return_value = result
        return pipeline

    def test_query_returns_hits(self, client: TestClient, session_token: str) -> None:
        hits = [
            SimpleNamespace(
                template_path="auth/concept.md", category="concept", score=0.9, excerpt="…"
            )
        ]
        pipeline = self._stub_pipeline(hits, "augmented prompt body")
        with patch("attune_gui.routes.rag._get_pipeline", return_value=pipeline):
            r = client.post(
                "/api/rag/query",
                json={"query": "auth flow", "k": 3},
                headers={"X-Attune-Client": session_token},
            )
        assert r.status_code == 200
        body = r.json()
        assert body["query"] == "auth flow"
        assert body["k"] == 3
        assert body["total_hits"] == 1
        assert body["hits"][0]["category"] == "concept"
        assert body["augmented_prompt"] == "augmented prompt body"

    def test_query_value_error_returns_400(self, client: TestClient, session_token: str) -> None:
        pipeline = MagicMock()
        pipeline.run.side_effect = ValueError("bad query")
        with patch("attune_gui.routes.rag._get_pipeline", return_value=pipeline):
            r = client.post(
                "/api/rag/query",
                json={"query": "x", "k": 3},
                headers={"X-Attune-Client": session_token},
            )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "bad_query"

    def test_query_unexpected_error_returns_500(
        self, client: TestClient, session_token: str
    ) -> None:
        pipeline = MagicMock()
        pipeline.run.side_effect = RuntimeError("kaput")
        with patch("attune_gui.routes.rag._get_pipeline", return_value=pipeline):
            r = client.post(
                "/api/rag/query",
                json={"query": "x", "k": 3},
                headers={"X-Attune-Client": session_token},
            )
        assert r.status_code == 500
        assert r.json()["detail"]["code"] == "rag_run_failed"

    def test_query_pipeline_init_failure_returns_500(
        self, client: TestClient, session_token: str
    ) -> None:
        with patch(
            "attune_gui.routes.rag._get_pipeline",
            side_effect=RuntimeError("init failed"),
        ):
            r = client.post(
                "/api/rag/query",
                json={"query": "x", "k": 3},
                headers={"X-Attune-Client": session_token},
            )
        assert r.status_code == 500
        assert r.json()["detail"]["code"] == "rag_init_failed"

    def test_query_requires_session_token(self, client: TestClient) -> None:
        """Mutating routes are gated by require_client_token."""
        r = client.post("/api/rag/query", json={"query": "x", "k": 3})
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/rag/corpus-info
# ---------------------------------------------------------------------------


class TestCorpusInfo:
    def test_returns_kinds_and_entry_count(self, client: TestClient) -> None:
        entries = [
            SimpleNamespace(path="security/concept.md"),
            SimpleNamespace(path="security/task.md"),
            SimpleNamespace(path="memory/concept.md"),
            SimpleNamespace(path="not-a-kind.md"),  # filtered out (no /)
        ]
        pipeline = MagicMock()
        pipeline.corpus.entries.return_value = iter(entries)
        with patch("attune_gui.routes.rag._get_pipeline", return_value=pipeline):
            r = client.get("/api/rag/corpus-info")
        assert r.status_code == 200
        body = r.json()
        assert body["entry_count"] == 4
        assert body["kinds"] == ["memory", "security"]

    def test_failure_returns_500(self, client: TestClient) -> None:
        with patch(
            "attune_gui.routes.rag._get_pipeline",
            side_effect=RuntimeError("kaboom"),
        ):
            r = client.get("/api/rag/corpus-info")
        assert r.status_code == 500
        assert r.json()["detail"]["code"] == "corpus_info_failed"
