"""Tests for /api/cowork/specs and the spec-root resolver."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.app import create_app
from attune_gui.routes import cowork_specs
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _seed_spec(root: Path, name: str, *, files: list[str], status: str | None = None) -> None:
    feat = root / name
    feat.mkdir(parents=True)
    for fname in files:
        body = "# Spec\n"
        if status is not None and fname == files[-1]:
            body = f"# Spec\n\n**Status**: {status}\n"
        (feat / fname).write_text(body)


# ---------------------------------------------------------------------------
# /api/cowork/specs — listing + phase + status inference
# ---------------------------------------------------------------------------


def test_specs_lists_features_with_phase_and_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs_root = tmp_path / "specs"
    _seed_spec(specs_root, "alpha", files=["requirements.md"], status="draft")
    _seed_spec(specs_root, "bravo", files=["requirements.md", "design.md"], status="approved")
    _seed_spec(
        specs_root,
        "charlie",
        files=["requirements.md", "design.md", "tasks.md"],
        status="complete",
    )

    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: specs_root)

    r = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert body["specs_root"] == str(specs_root)

    by_name = {s["feature"]: s for s in body["specs"]}
    assert by_name["alpha"]["phase"] == "requirements.md"
    assert by_name["alpha"]["phase_label"] == "Requirements"
    assert by_name["alpha"]["status"] == "draft"

    assert by_name["bravo"]["phase"] == "design.md"
    assert by_name["bravo"]["phase_label"] == "Design"
    assert by_name["bravo"]["status"] == "approved"

    assert by_name["charlie"]["phase"] == "tasks.md"
    assert by_name["charlie"]["phase_label"] == "Tasks"
    assert by_name["charlie"]["status"] == "complete"


def test_specs_skips_dot_dirs(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs_root = tmp_path / "specs"
    _seed_spec(specs_root, "real", files=["requirements.md"])
    _seed_spec(specs_root, ".hidden", files=["requirements.md"])

    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: specs_root)

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    names = {s["feature"] for s in body["specs"]}
    assert "real" in names
    assert ".hidden" not in names


def test_specs_returns_empty_when_no_root(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: None)

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    assert body == {"specs": [], "specs_root": None}


def test_spec_with_no_phase_files_handled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs_root = tmp_path / "specs"
    feat = specs_root / "empty"
    feat.mkdir(parents=True)
    (feat / "notes.md").write_text("misc")

    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: specs_root)

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    s = next(s for s in body["specs"] if s["feature"] == "empty")
    assert s["phase"] is None
    assert s["status"] is None


# ---------------------------------------------------------------------------
# _specs_root resolution
# ---------------------------------------------------------------------------


def test_specs_root_env_var_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "custom-specs"
    target.mkdir()
    monkeypatch.setenv("ATTUNE_SPECS_ROOT", str(target))
    monkeypatch.setattr(cowork_specs, "get_workspace", lambda: tmp_path)

    assert cowork_specs._specs_root() == target


def test_specs_root_falls_back_to_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    ws = tmp_path / "ws"
    (ws / "specs").mkdir(parents=True)
    monkeypatch.setattr(cowork_specs, "get_workspace", lambda: ws)
    monkeypatch.chdir(tmp_path)

    assert cowork_specs._specs_root() == ws / "specs"


def test_specs_root_walks_up_from_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If env + workspace miss, walk up from cwd until 'specs/' is found."""
    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    monkeypatch.setattr(cowork_specs, "get_workspace", lambda: None)

    project = tmp_path / "proj"
    nested = project / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (project / "specs").mkdir()

    monkeypatch.chdir(nested)
    assert cowork_specs._specs_root() == project / "specs"


def test_specs_root_returns_none_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    monkeypatch.setattr(cowork_specs, "get_workspace", lambda: None)

    isolated = tmp_path / "lonely"
    isolated.mkdir()
    monkeypatch.chdir(isolated)

    # Walk-up should not escape into the user's home tree and find a real specs/.
    # We can't fully guarantee the system is clean, so just assert behaviour: either
    # None or a path rooted somewhere outside our tmp_path.
    found = cowork_specs._specs_root()
    if found is not None:
        assert tmp_path not in found.parents
