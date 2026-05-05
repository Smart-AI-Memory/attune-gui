"""Tests for living_docs_store + /api/living-docs routes (combined surface)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from attune_gui.app import create_app
from attune_gui.living_docs_store import (
    DocEntry,
    LivingDocsStore,
    ReviewItem,
    get_store,
)
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def session_token(client: TestClient) -> str:
    return client.get("/api/session/token").json()["token"]


@pytest.fixture(autouse=True)
def reset_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use a fresh LivingDocsStore per test."""
    from attune_gui import living_docs_store

    monkeypatch.setattr(living_docs_store, "_store", None)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set ~/.attune-gui/config.json to point at a tmp workspace."""
    from attune_gui import workspace as ws

    cfg = tmp_path / "config.json"
    monkeypatch.setattr(ws, "_CONFIG_PATH", cfg)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    project = tmp_path / "project"
    project.mkdir()
    cfg.write_text(f'{{"workspace": "{project}"}}')
    return project


# ---------------------------------------------------------------------------
# DocEntry / ReviewItem to_dict
# ---------------------------------------------------------------------------


def test_doc_entry_to_dict_serializes_all_fields() -> None:
    e = DocEntry(
        id="auth/concept",
        feature="auth",
        depth="concept",
        persona="end_user",
        status="current",
        path="auth/concept.md",
        last_modified="2026-01-01T00:00:00",
        reason=None,
    )
    d = e.to_dict()
    assert d["id"] == "auth/concept"
    assert d["status"] == "current"


def test_review_item_to_dict_serializes_all_fields() -> None:
    item = ReviewItem(
        id="r1",
        doc_id="auth/concept",
        feature="auth",
        depth="concept",
        persona="end_user",
        trigger="manual",
        auto_applied_at="2026-01-01T00:00:00",
        diff_summary="3 lines changed",
    )
    d = item.to_dict()
    assert d["trigger"] == "manual"
    assert d["reviewed"] is False
    assert d["diff_summary"] == "3 lines changed"


# ---------------------------------------------------------------------------
# LivingDocsStore.scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_walks_template_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    templates = project / ".help" / "templates" / "auth"
    templates.mkdir(parents=True)
    (templates / "concept.md").write_text("body")
    (templates / "task.md").write_text("body")

    store = LivingDocsStore()
    out = await store.scan(project, trigger="manual")

    assert out["status"] == "ok"
    assert out["scanned"] >= 2
    docs = await store.list_docs()
    feature_names = {d["feature"] for d in docs}
    assert "auth" in feature_names


@pytest.mark.asyncio
async def test_scan_returns_already_scanning_when_in_flight() -> None:
    store = LivingDocsStore()
    store._scanning = True
    out = await store.scan(Path("/anywhere"), trigger="manual")
    assert out["status"] == "already_scanning"


@pytest.mark.asyncio
async def test_scan_handles_missing_help_dir(tmp_path: Path) -> None:
    """If .help/ doesn't exist, scan returns 0 docs without crashing."""
    store = LivingDocsStore()
    out = await store.scan(tmp_path, trigger="manual")
    assert out["status"] == "ok"
    assert out["scanned"] == 0


@pytest.mark.asyncio
async def test_scan_filters_by_persona(tmp_path: Path) -> None:
    project = tmp_path / "project"
    templates = project / ".help" / "templates" / "auth"
    templates.mkdir(parents=True)
    (templates / "concept.md").write_text("body")  # end_user
    (templates / "reference.md").write_text("body")  # developer

    store = LivingDocsStore()
    await store.scan(project)

    end_user = await store.list_docs(persona="end_user")
    developer = await store.list_docs(persona="developer")
    # Each persona returns the docs it owns
    assert all(d["persona"] == "end_user" for d in end_user)
    assert all(d["persona"] == "developer" for d in developer)
    # author = no filter
    all_docs = await store.list_docs(persona="author")
    assert len(all_docs) >= len(end_user)


# ---------------------------------------------------------------------------
# get_health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_health_returns_summary_and_per_persona() -> None:
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
        ),
        DocEntry(
            id="auth/task",
            feature="auth",
            depth="task",
            persona="end_user",
            status="stale",
            path="auth/task.md",
            last_modified=None,
        ),
        DocEntry(
            id="memory/reference",
            feature="memory",
            depth="reference",
            persona="developer",
            status="missing",
            path=None,
            last_modified=None,
        ),
    ]
    h = await store.get_health()
    assert h["summary"]["total"] == 3
    assert h["summary"]["current"] == 1
    assert h["summary"]["stale"] == 1
    assert h["summary"]["missing"] == 1
    assert "end_user" in h["by_persona"]
    assert "developer" in h["by_persona"]


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_to_queue_creates_review_item(tmp_path: Path) -> None:
    store = LivingDocsStore()
    with patch.object(store, "_git_diff_summary", return_value="2 lines"):
        item = await store.add_to_queue("auth/concept", "manual", tmp_path)

    assert item.feature == "auth"
    assert item.depth == "concept"
    assert item.trigger == "manual"
    assert item.diff_summary == "2 lines"

    queue = await store.list_queue()
    assert len(queue) == 1


@pytest.mark.asyncio
async def test_list_queue_filters_by_reviewed(tmp_path: Path) -> None:
    store = LivingDocsStore()
    with patch.object(store, "_git_diff_summary", return_value=""):
        item1 = await store.add_to_queue("auth/concept", "manual", tmp_path)
        await store.add_to_queue("memory/concept", "manual", tmp_path)

    await store.approve(item1.id)

    reviewed = await store.list_queue(reviewed=True)
    unreviewed = await store.list_queue(reviewed=False)
    assert len(reviewed) == 1
    assert len(unreviewed) == 1


@pytest.mark.asyncio
async def test_list_queue_filters_by_persona(tmp_path: Path) -> None:
    store = LivingDocsStore()
    with patch.object(store, "_git_diff_summary", return_value=""):
        await store.add_to_queue("auth/concept", "manual", tmp_path)  # end_user
        await store.add_to_queue("auth/reference", "manual", tmp_path)  # developer

    end_user = await store.list_queue(persona="end_user")
    assert all(i["persona"] == "end_user" for i in end_user)


@pytest.mark.asyncio
async def test_approve_unknown_returns_false() -> None:
    store = LivingDocsStore()
    assert await store.approve("does-not-exist") is False


@pytest.mark.asyncio
async def test_revert_unknown_returns_error() -> None:
    store = LivingDocsStore()
    out = await store.revert("does-not-exist", Path("/tmp"))  # noqa: S108  # noqa: S108
    assert out["ok"] is False
    assert "not found" in out["error"].lower()


@pytest.mark.asyncio
async def test_revert_success_drops_item(tmp_path: Path) -> None:
    store = LivingDocsStore()
    with patch.object(store, "_git_diff_summary", return_value=""):
        item = await store.add_to_queue("auth/concept", "manual", tmp_path)

    fake_result = SimpleNamespace(returncode=0, stderr="", stdout="")
    with patch("asyncio.to_thread", new=_fake_to_thread(fake_result)):
        out = await store.revert(item.id, tmp_path)

    assert out["ok"] is True
    assert await store.list_queue() == []


@pytest.mark.asyncio
async def test_revert_git_failure_returns_error(tmp_path: Path) -> None:
    store = LivingDocsStore()
    with patch.object(store, "_git_diff_summary", return_value=""):
        item = await store.add_to_queue("auth/concept", "manual", tmp_path)

    fake_result = SimpleNamespace(returncode=1, stderr="git complains", stdout="")
    with patch("asyncio.to_thread", new=_fake_to_thread(fake_result)):
        out = await store.revert(item.id, tmp_path)

    assert out["ok"] is False
    assert "git complains" in out["error"]


# Helper: replace asyncio.to_thread with a coroutine that returns a fixed value.
def _fake_to_thread(return_value):  # type: ignore[no-untyped-def]
    async def stub(*args, **kwargs):
        return return_value

    return stub


# ---------------------------------------------------------------------------
# set_quality
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_quality_replaces_scores() -> None:
    store = LivingDocsStore()
    await store.set_quality({"faithfulness": 0.9, "strict_accuracy": 0.85})
    h = await store.get_health()
    assert h["quality"] == {"faithfulness": 0.9, "strict_accuracy": 0.85}


# ---------------------------------------------------------------------------
# get_store singleton
# ---------------------------------------------------------------------------


def test_get_store_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    from attune_gui import living_docs_store

    monkeypatch.setattr(living_docs_store, "_store", None)
    a = get_store()
    b = get_store()
    assert a is b


# ---------------------------------------------------------------------------
# /api/living-docs HTTP routes
# ---------------------------------------------------------------------------


class TestLivingDocsRoutes:
    def test_get_config(self, client: TestClient, workspace: Path) -> None:
        r = client.get("/api/living-docs/config")
        assert r.status_code == 200
        body = r.json()
        assert body["workspace"] == str(workspace)
        assert "has_help_dir" in body

    def test_set_config_invalid_path_returns_400(
        self, client: TestClient, session_token: str, tmp_path: Path
    ) -> None:
        r = client.put(
            "/api/living-docs/config",
            json={"workspace": str(tmp_path / "missing")},
            headers={"X-Attune-Client": session_token},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "invalid_workspace"

    def test_set_config_persists_workspace(
        self,
        client: TestClient,
        session_token: str,
        workspace: Path,
        tmp_path: Path,
    ) -> None:
        new_ws = tmp_path / "new-project"
        new_ws.mkdir()
        r = client.put(
            "/api/living-docs/config",
            json={"workspace": str(new_ws)},
            headers={"X-Attune-Client": session_token},
        )
        assert r.status_code == 200
        assert r.json()["workspace"] == str(new_ws.resolve())

    def test_health_endpoint(self, client: TestClient, workspace: Path) -> None:
        r = client.get("/api/living-docs/health")
        assert r.status_code == 200
        body = r.json()
        assert "summary" in body
        assert "workspace" in body

    def test_list_docs_endpoint(self, client: TestClient, workspace: Path) -> None:
        r = client.get("/api/living-docs/docs")
        assert r.status_code == 200
        assert "docs" in r.json()

    def test_list_queue_endpoint(self, client: TestClient, workspace: Path) -> None:
        r = client.get("/api/living-docs/queue")
        assert r.status_code == 200
        assert r.json() == {"queue": []}

    def test_quality_endpoint(self, client: TestClient, workspace: Path) -> None:
        r = client.get("/api/living-docs/quality")
        assert r.status_code == 200
        assert "quality" in r.json()

    def test_trigger_scan(self, client: TestClient, session_token: str, workspace: Path) -> None:
        r = client.post(
            "/api/living-docs/scan",
            json={"trigger": "manual"},
            headers={"X-Attune-Client": session_token},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "scan_queued"

    def test_approve_unknown_item_returns_404(
        self, client: TestClient, session_token: str, workspace: Path
    ) -> None:
        r = client.post(
            "/api/living-docs/queue/does-not-exist/approve",
            headers={"X-Attune-Client": session_token},
        )
        assert r.status_code == 404

    def test_git_webhook_queues_scan(self, client: TestClient, workspace: Path) -> None:
        r = client.post("/api/living-docs/webhook/git")
        assert r.status_code == 200
        assert r.json() == {"status": "scan_queued", "trigger": "git_hook"}

    def test_regenerate_starts_a_visible_job(
        self, client: TestClient, session_token: str, workspace: Path
    ) -> None:
        """The regen route now goes through the Jobs registry instead of
        a fire-and-forget BackgroundTask, so users can watch progress
        on the Jobs page. The response is the job dict with an id."""
        r = client.post(
            "/api/living-docs/docs/auth/concept/regenerate",
            headers={"X-Attune-Client": session_token},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "living-docs.regenerate"
        assert body["args"] == {"doc_id": "auth/concept", "trigger": "manual"}
        # Job is at least pending; may have started by the time we read.
        assert body["status"] in ("pending", "running", "completed", "errored")
        assert "id" in body and isinstance(body["id"], str) and body["id"]


# ---------------------------------------------------------------------------
# Mutating routes require session token
# ---------------------------------------------------------------------------


def test_set_config_requires_token(client: TestClient) -> None:
    r = client.put("/api/living-docs/config", json={"workspace": "/tmp"})  # noqa: S108
    assert r.status_code in (401, 403)


def test_scan_requires_token(client: TestClient) -> None:
    r = client.post("/api/living-docs/scan", json={"trigger": "manual"})
    assert r.status_code in (401, 403)
