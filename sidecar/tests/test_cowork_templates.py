"""Tests for /api/cowork/templates and the templates-root resolver."""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_author import StalenessReport
from attune_author.staleness import FeatureStaleness
from attune_gui.routes import cowork_templates
from fastapi.testclient import TestClient


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


def _empty_report(_ws: Path) -> StalenessReport:
    """Stub for check_workspace_staleness — no manifest, nothing to compare."""
    return StalenessReport()


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
    monkeypatch.setattr(cowork_templates, "check_workspace_staleness", _empty_report)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    items = {t["path"]: t for t in body["templates"]}

    assert body["templates_root"] == str(root)
    assert "concepts/alpha.md" in items
    assert items["concepts/alpha.md"]["tags"] == ["security", "tools"]
    assert items["concepts/alpha.md"]["summary"] == "Alpha doc."
    assert items["concepts/alpha.md"]["manual"] is False

    assert items["tasks/beta.md"]["manual"] is True
    assert items["tasks/legacy.md"]["manual"] is True


def test_templates_staleness_reflects_content_drift(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The route's `staleness` value comes from attune-author's content-drift check.

    Replaces the legacy mtime-bucket test. Three template shapes:
      - ``auth/concept.md``   — feature is stale per the report → "stale"
      - ``ops/concept.md``    — feature is known and current     → "fresh"
      - ``orphan.md``         — no feature dir (lives at root)   → "unknown"
    """
    root = tmp_path / "templates-root"
    _seed_template(root / "auth" / "concept.md")
    _seed_template(root / "ops" / "concept.md")
    _seed_template(root / "orphan.md")

    def fake_report(_ws: Path) -> StalenessReport:
        return StalenessReport(
            help_entries=[
                FeatureStaleness(feature="auth", is_stale=True, current_hash="x", stored_hash=None),
                FeatureStaleness(feature="ops", is_stale=False, current_hash="y", stored_hash="y"),
            ]
        )

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)
    monkeypatch.setattr(cowork_templates, "get_workspace", lambda: tmp_path)
    monkeypatch.setattr(cowork_templates, "check_workspace_staleness", fake_report)

    body = client.get("/api/cowork/templates", headers={"Origin": "http://localhost:5173"}).json()
    by_path = {t["path"]: t for t in body["templates"]}
    assert by_path["auth/concept.md"]["staleness"] == "stale"
    assert by_path["ops/concept.md"]["staleness"] == "fresh"
    assert by_path["orphan.md"]["staleness"] == "unknown"


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
