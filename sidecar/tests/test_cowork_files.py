"""Tests for /api/cowork/files/* — read, write, render, pin."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.app import create_app
from attune_gui.routes import cowork_files
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def session_token(client: TestClient) -> str:
    """Get a session token for mutating-route tests."""
    return client.get("/api/session/token").json()["token"]


def _patch_specs_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    from attune_gui.routes import cowork_specs

    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: root)


def _patch_templates_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    from attune_gui.routes import cowork_templates

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)


def _patch_workspace(monkeypatch: pytest.MonkeyPatch, ws: Path | None) -> None:
    monkeypatch.setattr(cowork_files, "get_workspace", lambda: ws)


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def test_read_specs_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "specs"
    feat = root / "feature-a"
    feat.mkdir(parents=True)
    (feat / "requirements.md").write_text("# Hello")

    _patch_specs_root(monkeypatch, root)

    r = client.get(
        "/api/cowork/files/raw/specs/feature-a/requirements.md",
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "# Hello"
    assert body["manual"] is False


def test_read_404_for_missing_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_specs_root(monkeypatch, tmp_path / "specs")
    (tmp_path / "specs").mkdir()

    r = client.get(
        "/api/cowork/files/raw/specs/nope.md",
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Path traversal guard
# ---------------------------------------------------------------------------


def test_read_blocks_path_traversal(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "specs"
    root.mkdir()
    (tmp_path / "secret.txt").write_text("nope")

    _patch_specs_root(monkeypatch, root)

    # ../secret.txt would resolve outside the specs root
    r = client.get(
        "/api/cowork/files/raw/specs/..%2Fsecret.txt",
        headers={"Origin": "http://localhost:5173"},
    )
    # Either path-traversal-blocked (400) or not-found (404) is acceptable —
    # both indicate the file was not served.
    assert r.status_code in (400, 404)


def test_unknown_root_rejected(client: TestClient) -> None:
    r = client.get(
        "/api/cowork/files/raw/notreal/x.md",
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 400
    assert "Unknown root" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def test_render_strips_frontmatter_and_returns_html(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "specs"
    feat = root / "feature"
    feat.mkdir(parents=True)
    (feat / "design.md").write_text("---\ntitle: hi\n---\n# Heading\n\nBody paragraph.")

    _patch_specs_root(monkeypatch, root)

    r = client.get(
        "/api/cowork/files/rendered/specs/feature/design.md",
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 200
    html = r.json()["html"]
    assert "<h1" in html
    assert "Heading" in html
    assert "Body paragraph" in html
    # Frontmatter should NOT appear in the rendered HTML
    assert "title: hi" not in html


# ---------------------------------------------------------------------------
# Write (atomic)
# ---------------------------------------------------------------------------


def test_write_round_trip(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session_token: str,
) -> None:
    root = tmp_path / "specs"
    feat = root / "feat"
    feat.mkdir(parents=True)
    (feat / "requirements.md").write_text("old")

    _patch_specs_root(monkeypatch, root)

    r = client.put(
        "/api/cowork/files/raw/specs/feat/requirements.md",
        json={"content": "fresh content"},
        headers={"Origin": "http://localhost:5173", "X-Attune-Client": session_token},
    )
    assert r.status_code == 200
    assert (feat / "requirements.md").read_text() == "fresh content"


def test_write_requires_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "specs"
    (root / "feat").mkdir(parents=True)
    _patch_specs_root(monkeypatch, root)

    r = client.put(
        "/api/cowork/files/raw/specs/feat/x.md",
        json={"content": "x"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert r.status_code == 403


def test_write_rejects_non_string_content(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session_token: str,
) -> None:
    root = tmp_path / "specs"
    (root / "feat").mkdir(parents=True)
    _patch_specs_root(monkeypatch, root)

    r = client.put(
        "/api/cowork/files/raw/specs/feat/x.md",
        json={"content": 42},
        headers={"Origin": "http://localhost:5173", "X-Attune-Client": session_token},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Pin toggle
# ---------------------------------------------------------------------------


def test_pin_sets_manual_true_in_frontmatter(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session_token: str,
) -> None:
    root = tmp_path / "templates"
    root.mkdir()
    (root / "concept.md").write_text("---\ntype: concept\n---\nbody")

    _patch_templates_root(monkeypatch, root)

    r = client.post(
        "/api/cowork/files/pin/templates/concept.md",
        json={"manual": True},
        headers={"Origin": "http://localhost:5173", "X-Attune-Client": session_token},
    )
    assert r.status_code == 200
    assert r.json()["manual"] is True

    raw = (root / "concept.md").read_text()
    assert "manual: true" in raw


def test_pin_clears_manual_flag(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session_token: str,
) -> None:
    root = tmp_path / "templates"
    root.mkdir()
    (root / "concept.md").write_text("---\nmanual: true\n---\nbody")

    _patch_templates_root(monkeypatch, root)

    r = client.post(
        "/api/cowork/files/pin/templates/concept.md",
        json={"manual": False},
        headers={"Origin": "http://localhost:5173", "X-Attune-Client": session_token},
    )
    assert r.status_code == 200
    raw = (root / "concept.md").read_text()
    assert "manual:" not in raw


def test_pin_only_valid_for_templates_root(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    session_token: str,
) -> None:
    root = tmp_path / "specs"
    (root / "feat").mkdir(parents=True)
    (root / "feat" / "design.md").write_text("---\n---\nbody")

    _patch_specs_root(monkeypatch, root)

    r = client.post(
        "/api/cowork/files/pin/specs/feat/design.md",
        json={"manual": True},
        headers={"Origin": "http://localhost:5173", "X-Attune-Client": session_token},
    )
    assert r.status_code == 400
