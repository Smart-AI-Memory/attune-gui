"""Tests for the batch-status SSE route (``/api/batch/status/stream``).

``status_maintenance_batch`` is always mocked — no live Anthropic call,
per the workspace testing-conventions. The stream self-terminates, so a
plain ``client.get`` reads the full set of ``data:`` frames.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from attune_author.maintenance_batch import BatchStateError, BatchStateNotFound
from attune_gui.routes import batch


def _frames(body: str) -> list[dict[str, Any]]:
    """Parse an SSE response body into a list of frame dicts."""
    out: list[dict[str, Any]] = []
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if chunk.startswith("data:"):
            out.append(json.loads(chunk[len("data:") :].strip()))
    return out


def _pending(processing_status: str = "in_progress", **extra: Any) -> dict[str, Any]:
    """A representative ``status_maintenance_batch`` payload."""
    return {
        "batch_id": "msgbatch_123",
        "processing_status": processing_status,
        "request_count": 10,
        "request_counts": {
            "succeeded": 3,
            "errored": 0,
            "expired": 0,
            "canceled": 0,
            "processing": 7,
        },
        "ended_at": None,
        **extra,
    }


# ---------------------------------------------------------------------------
# _poll_secs
# ---------------------------------------------------------------------------


class TestPollSecs:
    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ATTUNE_GUI_BATCH_POLL_SECS", raising=False)
        assert batch._poll_secs() == 30

    def test_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATTUNE_GUI_BATCH_POLL_SECS", "5")
        assert batch._poll_secs() == 5

    def test_invalid_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATTUNE_GUI_BATCH_POLL_SECS", "not-a-number")
        assert batch._poll_secs() == 30

    def test_floor_is_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATTUNE_GUI_BATCH_POLL_SECS", "0")
        assert batch._poll_secs() == 1


# ---------------------------------------------------------------------------
# _get_help_dir
# ---------------------------------------------------------------------------


def test_get_help_dir_uses_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(batch, "get_workspace", lambda: tmp_path)
    assert batch._get_help_dir() == tmp_path / ".help"


# ---------------------------------------------------------------------------
# Stream behavior (integration via TestClient)
# ---------------------------------------------------------------------------


@pytest.fixture
def fast_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make inter-poll sleeps instant so multi-frame tests don't wait."""
    monkeypatch.setattr(batch, "_poll_secs", lambda: 0)


def _patch_status(monkeypatch: pytest.MonkeyPatch, fn: Any) -> None:
    monkeypatch.setattr("attune_author.maintenance_batch.status_maintenance_batch", fn)


def test_no_pending_batch_emits_none(client, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_help_dir: Any) -> dict[str, Any]:
        raise BatchStateNotFound("no state")

    _patch_status(monkeypatch, _raise)
    resp = client.get("/api/batch/status/stream")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert _frames(resp.text) == [{"state": "none"}]


def test_expired_state_also_emits_none(client, monkeypatch: pytest.MonkeyPatch) -> None:
    # BatchStateExpired is a BatchStateError subclass — same "none" outcome.
    def _raise(_help_dir: Any) -> dict[str, Any]:
        raise BatchStateError("expired")

    _patch_status(monkeypatch, _raise)
    assert _frames(client.get("/api/batch/status/stream").text) == [{"state": "none"}]


def test_unexpected_error_emits_error_frame(client, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_help_dir: Any) -> dict[str, Any]:
        raise ValueError("boom")

    _patch_status(monkeypatch, _raise)
    frames = _frames(client.get("/api/batch/status/stream").text)
    assert len(frames) == 1
    assert frames[0]["state"] == "error"
    assert "boom" in frames[0]["detail"]


def test_pending_then_terminal(client, monkeypatch: pytest.MonkeyPatch, fast_poll) -> None:
    calls = iter([_pending("in_progress"), _pending("ended", ended_at="2026-06-14T12:00:00Z")])

    def _next(_help_dir: Any) -> dict[str, Any]:
        return next(calls)

    _patch_status(monkeypatch, _next)
    frames = _frames(client.get("/api/batch/status/stream").text)
    assert len(frames) == 2
    assert frames[0]["state"] == "pending"
    assert frames[0]["processing_status"] == "in_progress"
    assert frames[1]["processing_status"] == "ended"


def test_terminal_processing_status_closes_immediately(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_status(monkeypatch, lambda _h: _pending("canceled"))
    frames = _frames(client.get("/api/batch/status/stream").text)
    assert len(frames) == 1
    assert frames[0]["processing_status"] == "canceled"


def test_ended_at_set_closes_even_if_status_pending(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_status(
        monkeypatch,
        lambda _h: _pending("in_progress", ended_at="2026-06-14T12:00:00Z"),
    )
    frames = _frames(client.get("/api/batch/status/stream").text)
    assert len(frames) == 1
    assert frames[0]["ended_at"] == "2026-06-14T12:00:00Z"


# ---------------------------------------------------------------------------
# Disconnect handling (unit — TestClient can't disconnect mid-stream)
# ---------------------------------------------------------------------------


async def test_disconnect_ends_generator_without_polling(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _Req:
        async def is_disconnected(self) -> bool:
            return True

    def _should_not_run(_help_dir: Any) -> dict[str, Any]:
        raise AssertionError("status must not be polled after disconnect")

    _patch_status(monkeypatch, _should_not_run)
    frames = [f async for f in batch._events(_Req(), tmp_path / ".help")]
    assert frames == []
