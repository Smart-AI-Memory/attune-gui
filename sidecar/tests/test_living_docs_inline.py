"""Tests for _project_doc_state and the /api/living-docs/rows endpoint."""

from __future__ import annotations

from typing import Any

import pytest
from attune_gui.routes.living_docs import _project_doc_state

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc(status: str = "current") -> dict[str, Any]:
    return {
        "id": "auth/concept",
        "feature": "auth",
        "depth": "concept",
        "persona": "end_user",
        "status": status,
        "reason": None,
        "last_modified": None,
    }


def _qi() -> dict[str, Any]:
    return {"id": "qi-1", "doc_id": "auth/concept", "diff_summary": "2 lines"}


def _job(status: str) -> dict[str, Any]:
    return {
        "id": "job-1",
        "name": "living-docs.regenerate",
        "status": status,
        "error": "boom" if status == "errored" else None,
    }


# ---------------------------------------------------------------------------
# _project_doc_state — full matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "doc_status,queue_item,job,expected",
    [
        # base cases — no queue, no job
        ("current", None, None, "current"),
        ("stale", None, None, "stale"),
        ("missing", None, None, "missing"),
        # queue item wins over base status
        ("current", _qi(), None, "pending-review"),
        ("stale", _qi(), None, "pending-review"),
        # running job beats everything
        ("current", None, _job("running"), "regenerating"),
        ("stale", None, _job("pending"), "regenerating"),
        ("missing", None, _job("running"), "regenerating"),
        # running job beats pending-review
        ("stale", _qi(), _job("running"), "regenerating"),
        # errored job (no queue item)
        ("current", None, _job("errored"), "errored"),
        ("stale", None, _job("errored"), "errored"),
        # pending-review beats errored
        ("stale", _qi(), _job("errored"), "pending-review"),
        # completed job is irrelevant
        ("current", None, _job("completed"), "current"),
        ("stale", None, _job("completed"), "stale"),
    ],
)
def test_project_doc_state(doc_status, queue_item, job, expected):
    doc = _doc(doc_status)
    assert _project_doc_state(doc, queue_item, job) == expected


# ---------------------------------------------------------------------------
# /api/living-docs/rows — HTTP integration
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_store(monkeypatch):
    from attune_gui import jobs as jobs_mod
    from attune_gui import living_docs_store

    monkeypatch.setattr(living_docs_store, "_store", None)
    monkeypatch.setattr(jobs_mod, "_REGISTRY", None)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    from attune_gui import config

    cfg = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_PATH", cfg)
    monkeypatch.delenv("ATTUNE_WORKSPACE", raising=False)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "project"
    project.mkdir()
    cfg.write_text(f'{{"workspace": "{project}"}}')
    return project


def test_rows_endpoint_returns_correct_shape(client, workspace):
    r = client.get("/api/living-docs/rows")
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
    assert isinstance(body["rows"], list)


def test_rows_endpoint_computed_state_for_stale_doc(client, workspace, monkeypatch):
    from attune_gui import living_docs_store
    from attune_gui.living_docs_store import DocEntry, LivingDocsStore

    store = LivingDocsStore()
    store._docs = [
        DocEntry(
            id="auth/concept",
            feature="auth",
            depth="concept",
            persona="end_user",
            status="stale",
            path="auth/concept.md",
            last_modified=None,
        )
    ]
    monkeypatch.setattr(living_docs_store, "_store", store)

    r = client.get("/api/living-docs/rows")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["computed_state"] == "stale"
    assert rows[0]["base_status"] == "stale"


def test_rows_endpoint_pending_review_state(client, workspace, monkeypatch):
    from unittest.mock import patch

    from attune_gui import living_docs_store
    from attune_gui.living_docs_store import DocEntry, LivingDocsStore

    store = LivingDocsStore()
    store._docs = [
        DocEntry(
            id="auth/concept",
            feature="auth",
            depth="concept",
            persona="end_user",
            status="current",
            path="auth/concept.md",
            last_modified=None,
        )
    ]
    monkeypatch.setattr(living_docs_store, "_store", store)

    # Seed a review item directly
    with patch.object(store, "_git_diff_summary", return_value="1 line"):
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            store.add_to_queue("auth/concept", "manual", workspace)
        )

    r = client.get("/api/living-docs/rows")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert rows[0]["computed_state"] == "pending-review"
    assert rows[0]["queue_item_id"] is not None
    assert rows[0]["diff_summary"] == "1 line"
