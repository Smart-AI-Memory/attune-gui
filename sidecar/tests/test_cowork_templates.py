"""Tests for /api/cowork/templates and the templates-root resolver."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from attune_gui.routes import cowork_templates
from fastapi.testclient import TestClient


def _aged(path: Path, days: float) -> None:
    """Backdate ``path``'s mtime by ``days`` days."""
    target = time.time() - days * 86400
    os.utime(path, (target, target))


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

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    items = {t["path"]: t for t in body["templates"]}

    assert body["templates_root"] == str(root)
    assert "concepts/alpha.md" in items
    assert items["concepts/alpha.md"]["tags"] == ["security", "tools"]
    assert items["concepts/alpha.md"]["summary"] == "Alpha doc."
    assert items["concepts/alpha.md"]["manual"] is False

    assert items["tasks/beta.md"]["manual"] is True
    assert items["tasks/legacy.md"]["manual"] is True


def test_templates_staleness_thresholds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "templates-root"
    fresh = root / "fresh.md"
    stale = root / "stale.md"
    very = root / "very.md"
    _seed_template(fresh)
    _seed_template(stale)
    _seed_template(very)
    _aged(fresh, 5)
    _aged(stale, 30)  # between 14 and 60 days
    _aged(very, 90)

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    by_path = {t["path"]: t for t in body["templates"]}
    assert by_path["fresh.md"]["staleness"] == "fresh"
    assert by_path["stale.md"]["staleness"] == "stale"
    assert by_path["very.md"]["staleness"] == "very-stale"


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
