"""Tests for the spec authoring endpoints.

Covers:
    POST /api/cowork/specs                 (create new feature)
    POST /api/cowork/specs/{feature}/phase (add design or tasks)
    PUT  /api/cowork/specs/{feature}/{phase}/status
    GET  /api/cowork/specs/template
"""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.app import create_app
from attune_gui.routes import cowork_specs
from fastapi.testclient import TestClient

HDR = {"Origin": "http://localhost:5173"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def token(client: TestClient) -> str:
    return client.get("/api/session/token", headers=HDR).json()["token"]


@pytest.fixture
def specs_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "specs"
    root.mkdir()
    # Minimal but realistic TEMPLATE.md so bootstrap exercises the parser.
    (root / "TEMPLATE.md").write_text(
        "# Spec: [Feature Name]\n\n"
        "---\n\n"
        "## Phase 1: Requirements\n\n"
        "**Status**: draft | in-review | approved\n\n"
        "### Problem statement\n\n_TODO_\n\n"
        "---\n\n"
        "## Phase 2: Design\n\n"
        "**Status**: draft | in-review | approved\n\n"
        "### Architecture\n\n_TODO_\n\n"
        "---\n\n"
        "## Phase 3: Tasks\n\n"
        "**Status**: draft | in-review | approved\n\n"
        "### Implementation order\n\n_TODO_\n"
    )
    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: root)
    return root


def _post_token(client, url, body, token):
    return client.post(url, json=body, headers={**HDR, "X-Attune-Client": token})


def _put_token(client, url, body, token):
    return client.put(url, json=body, headers={**HDR, "X-Attune-Client": token})


# ---------------------------------------------------------------------------
# GET /api/cowork/specs/template
# ---------------------------------------------------------------------------


def test_get_template_returns_content(client: TestClient, specs_root: Path) -> None:
    r = client.get("/api/cowork/specs/template", headers=HDR)
    assert r.status_code == 200
    body = r.json()
    assert body["path"].endswith("TEMPLATE.md")
    assert "Phase 1: Requirements" in body["content"]


def test_get_template_returns_null_when_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "no-template"
    root.mkdir()
    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: root)

    r = client.get("/api/cowork/specs/template", headers=HDR)
    assert r.status_code == 200
    assert r.json() == {"path": None, "content": None}


# ---------------------------------------------------------------------------
# POST /api/cowork/specs (create new spec)
# ---------------------------------------------------------------------------


def test_create_spec_writes_requirements_from_template(
    client: TestClient, specs_root: Path, token: str
) -> None:
    r = _post_token(client, "/api/cowork/specs", {"feature": "my-feature"}, token)
    assert r.status_code == 201
    body = r.json()
    assert body["feature"] == "my-feature"
    assert body["phase"] == "requirements.md"
    assert body["path"] == "my-feature/requirements.md"

    target = specs_root / "my-feature" / "requirements.md"
    assert target.is_file()
    content = target.read_text()
    assert "# Spec: my-feature" in content
    assert "## Phase 1: Requirements" in content
    assert "**Status**: draft" in content
    # The placeholder pipe-syntax should have been normalised
    assert "draft | in-review" not in content


def test_create_spec_requires_token(client: TestClient, specs_root: Path) -> None:
    r = client.post("/api/cowork/specs", json={"feature": "x"}, headers=HDR)
    assert r.status_code == 403


def test_create_spec_rejects_invalid_slug(client: TestClient, specs_root: Path, token: str) -> None:
    bad = ["My-Feature", "feature with spaces", "../escape", "_leading", ""]
    for slug in bad:
        r = _post_token(client, "/api/cowork/specs", {"feature": slug}, token)
        # 400 (our validator) or 422 (pydantic) is acceptable
        assert r.status_code in (400, 422), f"slug {slug!r} should be rejected"


def test_create_spec_409_when_exists(client: TestClient, specs_root: Path, token: str) -> None:
    (specs_root / "already-here").mkdir()
    r = _post_token(client, "/api/cowork/specs", {"feature": "already-here"}, token)
    assert r.status_code == 409


def test_create_spec_falls_back_when_no_template(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, token: str
) -> None:
    """Without TEMPLATE.md we should still produce a usable starter file."""
    root = tmp_path / "specs"
    root.mkdir()
    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: root)

    r = _post_token(client, "/api/cowork/specs", {"feature": "fresh"}, token)
    assert r.status_code == 201
    target = root / "fresh" / "requirements.md"
    assert target.is_file()
    text = target.read_text()
    assert "# Spec: fresh" in text
    assert "**Status**: draft" in text


# ---------------------------------------------------------------------------
# POST /api/cowork/specs/{feature}/phase (add design or tasks)
# ---------------------------------------------------------------------------


def _seed_feature(specs_root: Path, name: str, files: list[str]) -> Path:
    feat = specs_root / name
    feat.mkdir()
    for f in files:
        (feat / f).write_text(f"# {name}\n\n**Status**: draft\n")
    return feat


def test_add_design_when_requirements_exists(
    client: TestClient, specs_root: Path, token: str
) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md"])
    r = _post_token(client, "/api/cowork/specs/feat/phase", {"phase": "design"}, token)
    assert r.status_code == 201
    target = specs_root / "feat" / "design.md"
    assert target.is_file()
    text = target.read_text()
    assert "## Phase 2: Design" in text
    assert "**Status**: draft" in text


def test_add_tasks_when_design_exists(client: TestClient, specs_root: Path, token: str) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md", "design.md"])
    r = _post_token(client, "/api/cowork/specs/feat/phase", {"phase": "tasks"}, token)
    assert r.status_code == 201
    target = specs_root / "feat" / "tasks.md"
    assert target.is_file()
    assert "## Phase 3: Tasks" in target.read_text()


def test_add_design_blocked_without_requirements(
    client: TestClient, specs_root: Path, token: str
) -> None:
    (specs_root / "feat").mkdir()
    r = _post_token(client, "/api/cowork/specs/feat/phase", {"phase": "design"}, token)
    assert r.status_code == 400


def test_add_tasks_blocked_without_design(client: TestClient, specs_root: Path, token: str) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md"])
    r = _post_token(client, "/api/cowork/specs/feat/phase", {"phase": "tasks"}, token)
    assert r.status_code == 400


def test_add_phase_409_when_exists(client: TestClient, specs_root: Path, token: str) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md", "design.md"])
    r = _post_token(client, "/api/cowork/specs/feat/phase", {"phase": "design"}, token)
    assert r.status_code == 409


def test_add_phase_unknown_value(client: TestClient, specs_root: Path, token: str) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md"])
    r = _post_token(client, "/api/cowork/specs/feat/phase", {"phase": "review"}, token)
    assert r.status_code == 400


def test_add_phase_404_for_unknown_feature(
    client: TestClient, specs_root: Path, token: str
) -> None:
    r = _post_token(client, "/api/cowork/specs/nope/phase", {"phase": "design"}, token)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/cowork/specs/{feature}/{phase}/status
# ---------------------------------------------------------------------------


def test_update_status_rewrites_existing_line(
    client: TestClient, specs_root: Path, token: str
) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md"])
    r = _put_token(
        client,
        "/api/cowork/specs/feat/requirements/status",
        {"status": "approved"},
        token,
    )
    assert r.status_code == 200
    text = (specs_root / "feat" / "requirements.md").read_text()
    assert "**Status**: approved" in text
    assert "**Status**: draft" not in text


def test_update_status_404_for_missing_phase(
    client: TestClient, specs_root: Path, token: str
) -> None:
    r = _put_token(
        client,
        "/api/cowork/specs/missing/requirements/status",
        {"status": "approved"},
        token,
    )
    assert r.status_code == 404


def test_update_status_rejects_invalid_value(
    client: TestClient, specs_root: Path, token: str
) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md"])
    r = _put_token(
        client,
        "/api/cowork/specs/feat/requirements/status",
        {"status": "shipped"},
        token,
    )
    assert r.status_code == 400


def test_update_status_inserts_when_no_status_line(
    client: TestClient, specs_root: Path, token: str
) -> None:
    feat = specs_root / "feat"
    feat.mkdir()
    (feat / "requirements.md").write_text("# Spec: feat\n\nbody\n")

    r = _put_token(
        client,
        "/api/cowork/specs/feat/requirements/status",
        {"status": "in-review"},
        token,
    )
    assert r.status_code == 200
    assert "**Status**: in-review" in (feat / "requirements.md").read_text()


def test_update_status_requires_token(client: TestClient, specs_root: Path) -> None:
    _seed_feature(specs_root, "feat", ["requirements.md"])
    r = client.put(
        "/api/cowork/specs/feat/requirements/status",
        json={"status": "approved"},
        headers=HDR,
    )
    assert r.status_code == 403
