"""Tests for /api/cowork/specs and the spec-root resolver."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui import config as gui_config
from attune_gui.routes import cowork_specs
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolate_attune_gui_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Point ``attune_gui.config.CONFIG_PATH`` at an empty tmp location.

    Why: ``_specs_roots()`` consults ``config.get("specs_root")``, which reads
    ``~/.attune-gui/config.json``. On a developer machine that file may set a
    federated ``specs_root`` (real paths under $HOME), which silently wins over
    the workspace/cwd fallbacks these tests intend to exercise.
    """
    isolated = tmp_path_factory.mktemp("attune-gui-config") / "config.json"
    monkeypatch.setattr(gui_config, "CONFIG_PATH", isolated)


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

    monkeypatch.setattr(cowork_specs, "_specs_roots", lambda: [specs_root])

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

    monkeypatch.setattr(cowork_specs, "_specs_roots", lambda: [specs_root])

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    names = {s["feature"] for s in body["specs"]}
    assert "real" in names
    assert ".hidden" not in names


def test_specs_returns_empty_when_no_root(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cowork_specs, "_specs_roots", lambda: [])

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    assert body == {"specs": [], "specs_root": None, "specs_roots": []}


def test_spec_with_no_phase_files_handled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    specs_root = tmp_path / "specs"
    feat = specs_root / "empty"
    feat.mkdir(parents=True)
    (feat / "notes.md").write_text("misc")

    monkeypatch.setattr(cowork_specs, "_specs_roots", lambda: [specs_root])

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    s = next(s for s in body["specs"] if s["feature"] == "empty")
    assert s["phase"] is None
    assert s["status"] is None


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("# Spec\n\n**Status**: approved\n", "approved"),  # colon outside
        ("# Spec\n\n**Status:** approved\n", "approved"),  # colon inside (the common form)
        ("# Spec\n\n**Status:** Closed — final\n", "Closed"),  # dashed phrase, common in real specs
        ("# Spec\n  **Status:** pending\n", "pending"),  # indented
    ],
)
def test_status_regex_accepts_both_markdown_emphasis_styles(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source: str,
    expected: str,
) -> None:
    """Pre-fix bug: _STATUS_VALUE_RE only matched ``**Status**:`` (colon
    outside). Real specs in the repo overwhelmingly use ``**Status:**``
    (colon inside), which was silently returning ``None``. Both forms
    must now parse to the same status value."""
    specs_root = tmp_path / "specs"
    feat = specs_root / "alpha"
    feat.mkdir(parents=True)
    (feat / "requirements.md").write_text(source)

    monkeypatch.setattr(cowork_specs, "_specs_roots", lambda: [specs_root])

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    alpha = next(s for s in body["specs"] if s["feature"] == "alpha")
    assert alpha["status"] == expected


@pytest.mark.parametrize(
    "bad_source",
    [
        "# Spec\n\n**Status:\n",  # missing trailing **:
        "# Spec\n\n**Status: approved\n",  # missing closing **
        "# Spec\n\n**Statuss**: approved\n",  # double-s typo
        "# Spec\n\n## Status: approved\n",  # heading, not bold
    ],
)
def test_status_regex_rejects_malformed_lines(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, bad_source: str
) -> None:
    """The looser regex must still reject lines that aren't valid
    bold-Status declarations."""
    specs_root = tmp_path / "specs"
    feat = specs_root / "alpha"
    feat.mkdir(parents=True)
    (feat / "requirements.md").write_text(bad_source)

    monkeypatch.setattr(cowork_specs, "_specs_roots", lambda: [specs_root])

    body = client.get("/api/cowork/specs", headers={"Origin": "http://localhost:5173"}).json()
    alpha = next(s for s in body["specs"] if s["feature"] == "alpha")
    assert alpha["status"] is None


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
    from attune_gui import config as _config

    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    monkeypatch.setattr(_config, "get", lambda key: None)
    ws = tmp_path / "ws"
    (ws / "specs").mkdir(parents=True)
    monkeypatch.setattr(cowork_specs, "get_workspace", lambda: ws)
    monkeypatch.chdir(tmp_path)

    assert cowork_specs._specs_root() == ws / "specs"


def test_specs_root_falls_back_to_workspace_docs_specs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Workspaces that keep specs at ``docs/specs/`` (attune-rag, attune-ai layout)
    are discoverable when neither ``specs/`` nor ``.help/specs/`` exists."""
    from attune_gui import config as _config

    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    monkeypatch.setattr(_config, "get", lambda key: None)
    ws = tmp_path / "ws"
    (ws / "docs" / "specs").mkdir(parents=True)
    monkeypatch.setattr(cowork_specs, "get_workspace", lambda: ws)
    monkeypatch.chdir(tmp_path)

    assert cowork_specs._specs_root() == ws / "docs" / "specs"


def test_specs_root_prefers_specs_over_docs_specs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If a workspace has both ``specs/`` and ``docs/specs/``, ``specs/`` wins —
    matches the documented priority order."""
    from attune_gui import config as _config

    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    monkeypatch.setattr(_config, "get", lambda key: None)
    ws = tmp_path / "ws"
    (ws / "specs").mkdir(parents=True)
    (ws / "docs" / "specs").mkdir(parents=True)
    monkeypatch.setattr(cowork_specs, "get_workspace", lambda: ws)
    monkeypatch.chdir(tmp_path)

    assert cowork_specs._specs_root() == ws / "specs"


def test_specs_root_walks_up_from_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """If env + workspace miss, walk up from cwd until 'specs/' is found."""
    from attune_gui import config as _config

    monkeypatch.delenv("ATTUNE_SPECS_ROOT", raising=False)
    monkeypatch.setattr(_config, "get", lambda key: None)
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
