"""Tests for /api/commands and /api/jobs HTTP routes."""

from __future__ import annotations

import pytest
from attune_gui.app import create_app
from attune_gui.commands import CommandSpec
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def session_token(client: TestClient) -> str:
    return client.get("/api/session/token").json()["token"]


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use a fresh JobRegistry per test so list/cancel/get don't leak across cases."""
    from attune_gui import jobs

    monkeypatch.setattr(jobs, "_REGISTRY", None)


# ---------------------------------------------------------------------------
# GET /api/commands
# ---------------------------------------------------------------------------


def test_commands_returns_registered_list(client: TestClient) -> None:
    r = client.get("/api/commands")
    assert r.status_code == 200
    body = r.json()
    assert "commands" in body
    names = {c["name"] for c in body["commands"]}
    assert "rag.query" in names  # known registered command


def test_commands_filters_by_profile(client: TestClient) -> None:
    r_all = client.get("/api/commands").json()["commands"]
    r_author = client.get("/api/commands", params={"profile": "author"}).json()["commands"]
    assert len(r_author) <= len(r_all)


# ---------------------------------------------------------------------------
# GET /api/jobs
# ---------------------------------------------------------------------------


def test_list_jobs_empty_initially(client: TestClient) -> None:
    r = client.get("/api/jobs")
    assert r.status_code == 200
    assert r.json()["jobs"] == []


# ---------------------------------------------------------------------------
# POST /api/jobs
# ---------------------------------------------------------------------------


def test_start_unknown_command_returns_404(client: TestClient, session_token: str) -> None:
    r = client.post(
        "/api/jobs",
        json={"name": "does.not.exist", "args": {}},
        headers={"X-Attune-Client": session_token},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "unknown_command"


def test_start_missing_required_args_returns_400(client: TestClient, session_token: str) -> None:
    """rag.query has required `query` field — calling without it returns 400."""
    r = client.post(
        "/api/jobs",
        json={"name": "rag.query", "args": {}},
        headers={"X-Attune-Client": session_token},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "missing_args"


def test_start_returns_job_dict(
    client: TestClient, session_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inject a fake command that completes immediately, then verify the job dict."""

    async def fake_executor(args, ctx):
        ctx.log("ran")
        return {"echoed": args}

    fake = CommandSpec(
        name="test.echo",
        title="Test Echo",
        domain="rag",
        description="test",
        args_schema={"type": "object", "properties": {}, "required": []},
        executor=fake_executor,
    )
    from attune_gui import commands as cmds

    monkeypatch.setitem(cmds.COMMANDS, "test.echo", fake)

    r = client.post(
        "/api/jobs",
        json={"name": "test.echo", "args": {"x": 1}},
        headers={"X-Attune-Client": session_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "test.echo"
    assert body["args"] == {"x": 1}
    assert "id" in body


def test_start_requires_session_token(client: TestClient) -> None:
    r = client.post("/api/jobs", json={"name": "rag.query", "args": {"query": "x"}})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/jobs/{id}
# ---------------------------------------------------------------------------


def test_get_unknown_job_returns_404(client: TestClient) -> None:
    r = client.get("/api/jobs/does-not-exist")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "unknown_job"


def test_get_existing_job_returns_dict(
    client: TestClient, session_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_executor(args, ctx):
        return None

    fake = CommandSpec(
        name="test.noop",
        title="Test",
        domain="rag",
        description="test",
        args_schema={"type": "object", "properties": {}, "required": []},
        executor=fake_executor,
    )
    from attune_gui import commands as cmds

    monkeypatch.setitem(cmds.COMMANDS, "test.noop", fake)

    started = client.post(
        "/api/jobs",
        json={"name": "test.noop", "args": {}},
        headers={"X-Attune-Client": session_token},
    ).json()
    job_id = started["id"]

    r = client.get(f"/api/jobs/{job_id}")
    assert r.status_code == 200
    assert r.json()["id"] == job_id


# ---------------------------------------------------------------------------
# DELETE /api/jobs/{id}
# ---------------------------------------------------------------------------


def test_cancel_unknown_job_returns_404(client: TestClient, session_token: str) -> None:
    r = client.delete("/api/jobs/does-not-exist", headers={"X-Attune-Client": session_token})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "unknown_job"


def test_cancel_finished_job_returns_409(
    client: TestClient, session_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancellation of an already-finished job returns 409 not_cancellable."""
    import asyncio

    async def quick(args, ctx):
        return None

    fake = CommandSpec(
        name="test.quick",
        title="Test",
        domain="rag",
        description="test",
        args_schema={"type": "object", "properties": {}, "required": []},
        executor=quick,
    )
    from attune_gui import commands as cmds

    monkeypatch.setitem(cmds.COMMANDS, "test.quick", fake)

    started = client.post(
        "/api/jobs",
        json={"name": "test.quick", "args": {}},
        headers={"X-Attune-Client": session_token},
    ).json()
    job_id = started["id"]

    # Drain the asyncio task so the job actually finishes
    loop = asyncio.new_event_loop()
    loop.run_until_complete(asyncio.sleep(0.05))
    loop.close()

    r = client.delete(f"/api/jobs/{job_id}", headers={"X-Attune-Client": session_token})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "not_cancellable"


def test_cancel_requires_session_token(client: TestClient) -> None:
    r = client.delete("/api/jobs/anything")
    assert r.status_code in (401, 403)
