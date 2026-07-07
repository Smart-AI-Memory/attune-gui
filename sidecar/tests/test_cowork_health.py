"""Tests for /api/cowork/layers and /api/cowork/corpus."""

from __future__ import annotations

import importlib.metadata as ilm
from pathlib import Path

import pytest
from attune_gui.routes import cowork_health
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# /api/cowork/layers
# ---------------------------------------------------------------------------


def test_layers_returns_all_known_packages(client: TestClient) -> None:
    r = client.get("/api/cowork/layers", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    layers = body["layers"]
    # Spec promises four keys: rag, help, author, gui
    assert set(layers.keys()) == {"rag", "help", "author", "gui"}
    for info in layers.values():
        assert "importable" in info
        assert "version" in info


def test_layers_includes_interpreter_diagnostic(client: TestClient) -> None:
    """A 'not installed' result is usually env-mismatch; the response surfaces
    the interpreter so the dashboard is self-diagnosing."""
    r = client.get("/api/cowork/layers", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["interpreter"], str) and body["interpreter"]
    assert isinstance(body["python_version"], str)
    # "3.11.7" style
    assert body["python_version"].count(".") == 2


def test_layers_handles_missing_package(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing optional dep should report importable=false, not 500."""

    def fake_version(name: str) -> str:
        if name == "attune-rag":
            raise ilm.PackageNotFoundError(name)
        return "9.9.9"

    monkeypatch.setattr(cowork_health.ilm, "version", fake_version)

    r = client.get("/api/cowork/layers", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    layers = r.json()["layers"]
    assert layers["rag"] == {"importable": False, "version": None}
    assert layers["help"] == {"importable": True, "version": "9.9.9"}


# ---------------------------------------------------------------------------
# /api/cowork/corpus
# ---------------------------------------------------------------------------


def test_corpus_returns_null_when_no_workspace(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cowork_health, "get_workspace", lambda: None)

    r = client.get("/api/cowork/corpus", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    assert r.json() == {
        "workspace": None,
        "template_count": 0,
        "summaries_present": False,
        "has_help_dir": False,
        "manifest_path": None,
        "feature_count": 0,
    }


def test_corpus_counts_md_files_and_finds_summaries(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    help_dir = tmp_path / ".help"
    templates_dir = help_dir / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "one.md").write_text("hello")
    (templates_dir / "sub" / "two.md").parent.mkdir()
    (templates_dir / "sub" / "two.md").write_text("hi")
    (help_dir / "summaries.json").write_text("{}")

    monkeypatch.setattr(cowork_health, "get_workspace", lambda: tmp_path)

    r = client.get("/api/cowork/corpus", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert body["workspace"] == str(tmp_path)
    assert body["has_help_dir"] is True
    assert body["template_count"] == 2
    assert body["summaries_present"] is True


def test_corpus_no_help_dir(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cowork_health, "get_workspace", lambda: tmp_path)

    r = client.get("/api/cowork/corpus", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert body["has_help_dir"] is False
    assert body["template_count"] == 0
    assert body["summaries_present"] is False
    assert body["manifest_path"] is None
    assert body["feature_count"] == 0


def test_corpus_finds_manifest_under_help_dir(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Workspace is a project root: manifest lives at .help/features.yaml."""
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text("version: 1\nfeatures:\n  alpha: {}\n  beta: {}\n")

    monkeypatch.setattr(cowork_health, "get_workspace", lambda: tmp_path)

    r = client.get("/api/cowork/corpus", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert body["manifest_path"] == str(help_dir / "features.yaml")
    assert body["feature_count"] == 2


def test_corpus_finds_manifest_at_workspace_root(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Workspace pointed directly at a .help-style dir holding features.yaml."""
    (tmp_path / "features.yaml").write_text("version: 1\nfeatures:\n  solo: {}\n")

    monkeypatch.setattr(cowork_health, "get_workspace", lambda: tmp_path)

    r = client.get("/api/cowork/corpus", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert body["manifest_path"] == str(tmp_path / "features.yaml")
    assert body["feature_count"] == 1


def test_corpus_unparseable_manifest_reports_path_with_zero_count(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    (help_dir / "features.yaml").write_text("features: [unclosed")

    monkeypatch.setattr(cowork_health, "get_workspace", lambda: tmp_path)

    r = client.get("/api/cowork/corpus", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    body = r.json()
    assert body["manifest_path"] == str(help_dir / "features.yaml")
    assert body["feature_count"] == 0
