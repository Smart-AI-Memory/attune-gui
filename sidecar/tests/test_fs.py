"""Tests for /api/fs/browse — the directory-listing endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_browse_lists_subdirectories(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "alpha").mkdir()
    (tmp_path / "beta").mkdir()
    (tmp_path / "readme.txt").write_text("file, not dir")

    r = client.get("/api/fs/browse", params={"path": str(tmp_path)})
    assert r.status_code == 200
    body = r.json()
    names = [e["name"] for e in body["entries"]]
    assert names == ["alpha", "beta"]
    assert "readme.txt" not in names  # files excluded


def test_browse_returns_resolved_absolute_path(client: TestClient, tmp_path: Path) -> None:
    r = client.get("/api/fs/browse", params={"path": str(tmp_path)})
    assert r.status_code == 200
    assert Path(r.json()["path"]) == tmp_path.resolve()


def test_browse_sets_parent(client: TestClient, tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    r = client.get("/api/fs/browse", params={"path": str(nested)})
    assert r.status_code == 200
    assert r.json()["parent"] == str(tmp_path.resolve())


def test_browse_root_has_null_parent(client: TestClient) -> None:
    """At filesystem root, parent == path so the API returns None."""
    r = client.get("/api/fs/browse", params={"path": "/"})
    assert r.status_code == 200
    assert r.json()["parent"] is None


def test_browse_entries_are_sorted_case_insensitive(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "zebra").mkdir()
    (tmp_path / "Apple").mkdir()
    (tmp_path / "banana").mkdir()
    r = client.get("/api/fs/browse", params={"path": str(tmp_path)})
    names = [e["name"] for e in r.json()["entries"]]
    assert names == ["Apple", "banana", "zebra"]


# ---------------------------------------------------------------------------
# Hidden entries
# ---------------------------------------------------------------------------


def test_browse_hides_dot_entries_by_default(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "visible").mkdir()
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".git").mkdir()
    r = client.get("/api/fs/browse", params={"path": str(tmp_path)})
    names = [e["name"] for e in r.json()["entries"]]
    assert names == ["visible"]


def test_browse_shows_attune_dot_entries(client: TestClient, tmp_path: Path) -> None:
    """`.help` and `.attune` are explicitly shown — the user wants to see them."""
    (tmp_path / ".help").mkdir()
    (tmp_path / ".attune").mkdir()
    (tmp_path / ".git").mkdir()
    r = client.get("/api/fs/browse", params={"path": str(tmp_path)})
    names = [e["name"] for e in r.json()["entries"]]
    assert ".help" in names
    assert ".attune" in names
    assert ".git" not in names


# ---------------------------------------------------------------------------
# Tilde expansion
# ---------------------------------------------------------------------------


def test_browse_expands_tilde(client: TestClient) -> None:
    r = client.get("/api/fs/browse", params={"path": "~"})
    assert r.status_code == 200
    assert r.json()["path"] == str(Path.home().resolve())


def test_browse_default_path_is_home(client: TestClient) -> None:
    r = client.get("/api/fs/browse")
    assert r.status_code == 200
    assert r.json()["path"] == str(Path.home().resolve())


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


def test_browse_nonexistent_path_returns_400(client: TestClient, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    r = client.get("/api/fs/browse", params={"path": str(missing)})
    assert r.status_code == 400
    assert "Not a directory" in r.json()["detail"]


def test_browse_file_path_returns_400(client: TestClient, tmp_path: Path) -> None:
    f = tmp_path / "a-file.txt"
    f.write_text("hello")
    r = client.get("/api/fs/browse", params={"path": str(f)})
    assert r.status_code == 400
    assert "Not a directory" in r.json()["detail"]


def test_browse_unreadable_dir_returns_403(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Permission-denied during iterdir maps to HTTP 403."""
    target = tmp_path / "locked"
    target.mkdir()

    real_iterdir = Path.iterdir

    def fake_iterdir(self: Path):  # type: ignore[no-untyped-def]
        if self == target.resolve():
            raise PermissionError("denied")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    r = client.get("/api/fs/browse", params={"path": str(target)})
    assert r.status_code == 403
    assert "denied" in r.json()["detail"]
