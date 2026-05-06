"""Tests for /api/profile — GET/PUT the active UI profile."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attune_gui.app import create_app
from attune_gui.routes import profile
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Override conftest client to attach the X-Attune-Client token by default.

    Profile PUT now requires the token; most tests in this file mutate state.
    The unauth check below uses a fresh TestClient.
    """
    c = TestClient(create_app())
    c.headers["X-Attune-Client"] = c.get("/api/session/token").json()["token"]
    return c


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / ".attune-gui" / "config.json"
    monkeypatch.setattr(profile, "_CONFIG_PATH", cfg)
    return cfg


def test_set_profile_requires_session_token() -> None:
    """PUT /api/profile must reject calls without X-Attune-Client."""
    plain = TestClient(create_app())
    r = plain.put("/api/profile", json={"profile": "developer"})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/profile
# ---------------------------------------------------------------------------


def test_get_returns_default_when_unconfigured(client: TestClient, isolated_config: Path) -> None:
    r = client.get("/api/profile")
    assert r.status_code == 200
    assert r.json() == {"profile": "developer"}


def test_get_returns_stored_profile(client: TestClient, isolated_config: Path) -> None:
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text(json.dumps({"profile": "author"}))
    r = client.get("/api/profile")
    assert r.json() == {"profile": "author"}


def test_get_falls_back_when_stored_profile_invalid(
    client: TestClient, isolated_config: Path
) -> None:
    """An unknown profile in config falls back to the default rather than leaking."""
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text(json.dumps({"profile": "stranger"}))
    r = client.get("/api/profile")
    assert r.json() == {"profile": "developer"}


def test_get_returns_default_when_config_corrupt(client: TestClient, isolated_config: Path) -> None:
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text("garbage {")
    r = client.get("/api/profile")
    assert r.json() == {"profile": "developer"}


# ---------------------------------------------------------------------------
# PUT /api/profile
# ---------------------------------------------------------------------------


def test_set_persists_profile(client: TestClient, isolated_config: Path) -> None:
    r = client.put("/api/profile", json={"profile": "author"})
    assert r.status_code == 200
    assert r.json() == {"profile": "author"}
    data = json.loads(isolated_config.read_text())
    assert data["profile"] == "author"


def test_set_accepts_all_valid_profiles(client: TestClient, isolated_config: Path) -> None:
    for value in ("developer", "author", "support"):
        r = client.put("/api/profile", json={"profile": value})
        assert r.status_code == 200, value
        assert r.json()["profile"] == value


def test_set_rejects_invalid_profile(client: TestClient, isolated_config: Path) -> None:
    r = client.put("/api/profile", json={"profile": "stranger"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["code"] == "invalid_profile"
    assert "stranger" in detail["message"]


def test_set_round_trips_via_get(client: TestClient, isolated_config: Path) -> None:
    client.put("/api/profile", json={"profile": "support"})
    r = client.get("/api/profile")
    assert r.json() == {"profile": "support"}
