"""Tests for editor_sidecar portfile + /healthz route (M2 task #8)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from attune_gui import editor_sidecar
from attune_gui.security import current_session_token
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_portfile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    portfile = tmp_path / ".attune" / "sidecar.port"
    monkeypatch.setattr(editor_sidecar, "_PORTFILE_PATH", portfile, raising=False)
    return portfile




# -- helpers --------------------------------------------------------


def test_write_and_read_portfile() -> None:
    editor_sidecar.write_portfile(pid=1234, port=8765, token="abc")
    data = editor_sidecar.read_portfile()
    assert data is not None
    assert data.pid == 1234
    assert data.port == 8765
    assert data.token == "abc"


def test_read_portfile_missing_returns_none() -> None:
    assert editor_sidecar.read_portfile() is None


def test_read_portfile_corrupt_returns_none(tmp_path: Path) -> None:
    editor_sidecar._PORTFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    editor_sidecar._PORTFILE_PATH.write_text("not json", encoding="utf-8")
    assert editor_sidecar.read_portfile() is None


def test_read_portfile_missing_keys_returns_none() -> None:
    editor_sidecar._PORTFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    editor_sidecar._PORTFILE_PATH.write_text('{"pid": 1, "port": 2}', encoding="utf-8")  # no token
    assert editor_sidecar.read_portfile() is None


def test_delete_portfile_idempotent() -> None:
    editor_sidecar.delete_portfile()  # absent: no-op
    editor_sidecar.write_portfile(1, 2, "x")
    editor_sidecar.delete_portfile()
    assert editor_sidecar.read_portfile() is None


def test_is_pid_alive_for_current_process() -> None:
    assert editor_sidecar.is_pid_alive(os.getpid()) is True


def test_is_pid_alive_rejects_invalid() -> None:
    # Very high PID unlikely to be live; some systems cap at 32768/4M.
    assert editor_sidecar.is_pid_alive(0) is False
    assert editor_sidecar.is_pid_alive(-1) is False


def test_is_portfile_stale_when_missing() -> None:
    assert editor_sidecar.is_portfile_stale() is True


def test_is_portfile_stale_when_pid_dead() -> None:
    editor_sidecar.write_portfile(pid=999_999_999, port=1, token="x")
    assert editor_sidecar.is_portfile_stale() is True


def test_is_portfile_stale_false_for_live_pid() -> None:
    editor_sidecar.write_portfile(pid=os.getpid(), port=1, token="x")
    assert editor_sidecar.is_portfile_stale() is False


def test_portfile_context_writes_and_cleans_up() -> None:
    with editor_sidecar.portfile_context(port=4242, token="t") as data:
        assert data.port == 4242
        assert editor_sidecar.read_portfile() is not None
    assert editor_sidecar.read_portfile() is None


def test_portfile_context_cleans_up_on_exception() -> None:
    with (
        pytest.raises(RuntimeError, match="boom"),
        editor_sidecar.portfile_context(port=1, token="t"),
    ):
        raise RuntimeError("boom")
    assert editor_sidecar.read_portfile() is None


# -- /healthz route -------------------------------------------------


def test_healthz_returns_ok_with_valid_token(client: TestClient) -> None:
    token = current_session_token()
    response = client.get("/healthz", params={"token": token})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_returns_401_with_bad_token(client: TestClient) -> None:
    response = client.get("/healthz", params={"token": "wrong-token"})
    assert response.status_code == 401


def test_healthz_requires_token(client: TestClient) -> None:
    response = client.get("/healthz")
    # FastAPI returns 422 for missing required query param.
    assert response.status_code == 422
