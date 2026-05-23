"""Tests for /api/cowork/templates and the templates-root resolver."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.routes import cowork_templates
from attune_gui.services import staleness_cache
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_staleness_cache() -> None:
    staleness_cache._reset_for_tests()
    yield
    staleness_cache._reset_for_tests()


def _seed_template(
    path: Path,
    *,
    body: str = "content",
    tags: list[str] | None = None,
    summary: str | None = None,
    manual: bool = False,
    legacy_manual: bool = False,
) -> None:
    fm: list[str] = ["---"]
    if tags is not None:
        fm.append("tags: [" + ", ".join(tags) + "]")
    if summary is not None:
        fm.append(f"summary: {summary!r}")
    if manual:
        fm.append("status: manual")
    if legacy_manual:
        fm.append("manual: true")
    fm.append("---")
    fm.append(body)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(fm))


# ---------------------------------------------------------------------------
# /api/cowork/templates
# ---------------------------------------------------------------------------


def test_templates_lists_with_metadata(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "templates-root"
    _seed_template(
        root / "concepts" / "alpha.md",
        tags=["security", "tools"],
        summary="Alpha doc.",
    )
    _seed_template(root / "tasks" / "beta.md", manual=True)
    # Old files still using the buggy ``manual: true`` flag should
    # report manual=True too — keeps badges accurate during migration.
    _seed_template(root / "tasks" / "legacy.md", legacy_manual=True)

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)
    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: None)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    items = {t["path"]: t for t in body["templates"]}

    assert body["templates_root"] == str(root)
    assert "concepts/alpha.md" in items
    assert items["concepts/alpha.md"]["tags"] == ["security", "tools"]
    assert items["concepts/alpha.md"]["summary"] == "Alpha doc."
    assert items["concepts/alpha.md"]["manual"] is False

    assert items["tasks/beta.md"]["manual"] is True
    assert items["tasks/legacy.md"]["manual"] is True


def test_templates_staleness_pulls_from_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Route looks up each template's status via the staleness cache."""
    root = tmp_path / "templates-root"
    _seed_template(root / "fresh.md")
    _seed_template(root / "stale.md")
    _seed_template(root / "manual.md")

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)
    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: tmp_path)

    verdicts = {
        root / "fresh.md": "fresh",
        root / "stale.md": "stale",
        root / "manual.md": "manual",
    }

    def fake_get(workspace: Path, path: Path) -> str:
        assert workspace == tmp_path
        return verdicts[path]

    monkeypatch.setattr(staleness_cache, "get_template_staleness", fake_get)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    by_path = {t["path"]: t for t in body["templates"]}
    assert by_path["fresh.md"]["staleness"] == "fresh"
    assert by_path["stale.md"]["staleness"] == "stale"
    assert by_path["manual.md"]["staleness"] == "manual"


def test_templates_staleness_unknown_when_no_workspace(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No workspace context → page still renders, every row 'unknown'."""
    root = tmp_path / "templates-root"
    _seed_template(root / "a.md")

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)
    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: None)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    assert body["templates"][0]["staleness"] == "unknown"


def test_templates_response_keeps_last_modified(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """last_modified field stays in the response shape."""
    root = tmp_path / "templates-root"
    _seed_template(root / "a.md")

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)
    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: None)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    assert body["templates"][0]["last_modified"] is not None


def test_templates_empty_when_no_root(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: None)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    assert body == {"templates": [], "templates_root": None}


# ---------------------------------------------------------------------------
# _templates_root resolution
# ---------------------------------------------------------------------------


def test_templates_root_prefers_help_templates_subdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ws = tmp_path / "ws"
    sub = ws / ".help" / "templates"
    sub.mkdir(parents=True)
    (sub / "x.md").write_text("hi")

    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: ws)
    assert cowork_templates._templates_root() == sub


def test_templates_root_falls_back_to_help(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    help_dir = ws / ".help"
    help_dir.mkdir(parents=True)
    (help_dir / "x.md").write_text("hi")

    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: ws)
    assert cowork_templates._templates_root() == help_dir


def test_templates_root_falls_back_to_workspace_itself(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ws = tmp_path / "templates-direct"
    ws.mkdir()
    (ws / "a.md").write_text("hi")

    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: ws)
    assert cowork_templates._templates_root() == ws


def test_templates_root_returns_none_when_workspace_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: None)
    assert cowork_templates._templates_root() is None


def test_templates_root_returns_none_when_no_md_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ws = tmp_path / "ws"
    (ws / ".help").mkdir(parents=True)
    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: ws)
    assert cowork_templates._templates_root() is None
