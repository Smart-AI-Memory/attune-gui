"""Phase 2 tests for the MCP tool handlers.

Exercises each of the five tools via the public ``AttuneGuiMCPServer.call_tool``
surface to keep the dispatch + handler wiring covered in the same path the
MCP SDK uses.

Specs roots and the living-docs workspace are isolated to ``tmp_path`` via
the config loader's env-var override (``ATTUNE_SPECS_ROOT``) and a workspace
monkeypatch — so tests don't read the developer's real specs / workspace.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui import workspace as workspace_mod
from attune_gui.living_docs_store import DocEntry, get_store
from attune_gui.mcp.server import create_server

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def specs_root(tmp_path, monkeypatch) -> Path:
    """Isolated specs root containing one well-formed spec ``alpha``."""
    root = tmp_path / "specs"
    feat = root / "alpha"
    feat.mkdir(parents=True)
    # NOTE: using `**Status**:` (colon outside asterisks) — the format the
    # existing `_STATUS_VALUE_RE` regex matches. Real specs in the wild
    # overwhelmingly use `**Status:**` instead, which the regex misses — that's
    # a pre-existing bug in routes/cowork_specs.py that affects the dashboard's
    # Status column too. Tracked separately; this test uses the working format
    # so the MCP path is covered without depending on the broken one.
    (feat / "requirements.md").write_text(
        "# Spec: alpha\n\n**Status**: approved\n", encoding="utf-8"
    )
    (feat / "design.md").write_text("# Design: alpha\n\n**Status**: draft\n", encoding="utf-8")
    monkeypatch.setenv("ATTUNE_SPECS_ROOT", str(root))
    return root


@pytest.fixture
def workspace_with_doc(tmp_path, monkeypatch) -> Path:
    """Workspace with one living-docs file at .help/templates/alpha/concept.md."""
    ws = tmp_path / "ws"
    doc_path = ws / ".help" / "templates" / "alpha" / "concept.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("# alpha concept\n\nBody.\n", encoding="utf-8")

    monkeypatch.setattr(workspace_mod, "get_workspace", lambda: ws)
    return ws


@pytest.fixture
def app():
    return create_server()


# ---------------------------------------------------------------------------
# gui_list_specs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_specs_returns_configured_specs(app, specs_root) -> None:
    result = await app.call_tool("gui_list_specs", {})
    assert result["success"] is True
    features = [s["feature"] for s in result["specs"]]
    assert "alpha" in features
    assert result["specs_roots"][0]["path"] == str(specs_root)


@pytest.mark.asyncio
async def test_list_specs_with_no_roots_returns_empty(app, monkeypatch, tmp_path) -> None:
    # Point at an empty dir so _specs_roots returns []
    monkeypatch.setenv("ATTUNE_SPECS_ROOT", str(tmp_path / "missing"))
    result = await app.call_tool("gui_list_specs", {})
    assert result == {"success": True, "specs": [], "specs_roots": []}


# ---------------------------------------------------------------------------
# gui_get_spec
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_spec_returns_phase_contents(app, specs_root) -> None:
    result = await app.call_tool("gui_get_spec", {"feature": "alpha"})
    assert result["success"] is True
    assert set(result["phases"].keys()) == {"requirements", "design"}
    req = result["phases"]["requirements"]
    assert "Spec: alpha" in req["content"]
    assert req["status"] == "approved"
    assert req["file"] == "requirements.md"


@pytest.mark.asyncio
async def test_get_spec_rejects_invalid_slug(app, specs_root) -> None:
    result = await app.call_tool("gui_get_spec", {"feature": "../etc/passwd"})
    assert result["success"] is False
    assert "Invalid feature" in result["error"]


@pytest.mark.asyncio
async def test_get_spec_unknown_feature_errors(app, specs_root) -> None:
    result = await app.call_tool("gui_get_spec", {"feature": "nope"})
    assert result["success"] is False
    assert "'nope' not found" in result["error"]


# ---------------------------------------------------------------------------
# gui_get_spec_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_spec_status_returns_most_advanced(app, specs_root) -> None:
    result = await app.call_tool("gui_get_spec_status", {"feature": "alpha"})
    assert result["success"] is True
    # design is most-advanced since both files exist
    assert result["phase"] == "design"
    assert result["status"] == "draft"


@pytest.mark.asyncio
async def test_get_spec_status_explicit_phase(app, specs_root) -> None:
    result = await app.call_tool(
        "gui_get_spec_status", {"feature": "alpha", "phase": "requirements"}
    )
    assert result["success"] is True
    assert result["phase"] == "requirements"
    assert result["status"] == "approved"


@pytest.mark.asyncio
async def test_get_spec_status_rejects_invalid_phase(app, specs_root) -> None:
    result = await app.call_tool("gui_get_spec_status", {"feature": "alpha", "phase": "bogus"})
    assert result["success"] is False
    assert "Invalid phase" in result["error"]


# ---------------------------------------------------------------------------
# gui_set_spec_status (the only write tool)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_spec_status_persists_to_disk(app, specs_root) -> None:
    result = await app.call_tool(
        "gui_set_spec_status",
        {"feature": "alpha", "phase": "requirements", "status": "complete"},
    )
    assert result["success"] is True
    assert result["status"] == "complete"
    # Verify the file actually changed.
    content = (specs_root / "alpha" / "requirements.md").read_text(encoding="utf-8")
    assert "**Status**: complete" in content
    # And that gui_get_spec_status now reports the new value.
    follow = await app.call_tool(
        "gui_get_spec_status", {"feature": "alpha", "phase": "requirements"}
    )
    assert follow["status"] == "complete"


@pytest.mark.asyncio
async def test_set_spec_status_rejects_invalid_status(app, specs_root) -> None:
    result = await app.call_tool(
        "gui_set_spec_status",
        {"feature": "alpha", "phase": "requirements", "status": "shipped-it"},
    )
    assert result["success"] is False
    assert "Invalid status" in result["error"]
    # File must not have been touched.
    content = (specs_root / "alpha" / "requirements.md").read_text(encoding="utf-8")
    assert "**Status**: approved" in content


@pytest.mark.asyncio
async def test_set_spec_status_rejects_invalid_phase(app, specs_root) -> None:
    result = await app.call_tool(
        "gui_set_spec_status",
        {"feature": "alpha", "phase": "summary", "status": "complete"},
    )
    assert result["success"] is False
    assert "Invalid phase" in result["error"]


@pytest.mark.asyncio
async def test_set_spec_status_rejects_invalid_feature(app, specs_root) -> None:
    result = await app.call_tool(
        "gui_set_spec_status",
        {"feature": "../etc", "phase": "requirements", "status": "approved"},
    )
    assert result["success"] is False
    assert "Invalid feature" in result["error"]


@pytest.mark.asyncio
async def test_set_spec_status_unknown_feature(app, specs_root) -> None:
    result = await app.call_tool(
        "gui_set_spec_status",
        {"feature": "ghost", "phase": "requirements", "status": "approved"},
    )
    assert result["success"] is False
    assert "'ghost' not found" in result["error"]


@pytest.mark.asyncio
async def test_set_spec_status_missing_phase_file(app, specs_root) -> None:
    # design.md is present on alpha (from the fixture); tasks.md is not.
    result = await app.call_tool(
        "gui_set_spec_status",
        {"feature": "alpha", "phase": "tasks", "status": "complete"},
    )
    assert result["success"] is False
    assert "Phase file does not exist" in result["error"]


# ---------------------------------------------------------------------------
# gui_list_living_docs / gui_get_living_doc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_living_docs_returns_docs(app, workspace_with_doc) -> None:
    store = get_store()
    async with store._lock:  # noqa: SLF001 — test setup, bypass scan
        store._docs = [
            DocEntry(
                id="alpha/concept",
                feature="alpha",
                depth="concept",
                persona="end_user",
                status="current",
                path=".help/templates/alpha/concept.md",
                last_modified="2026-05-23T12:00:00+00:00",
            )
        ]
    result = await app.call_tool("gui_list_living_docs", {})
    assert result["success"] is True
    assert len(result["docs"]) == 1
    assert result["docs"][0]["id"] == "alpha/concept"


@pytest.mark.asyncio
async def test_get_living_doc_reads_file_content(app, workspace_with_doc) -> None:
    store = get_store()
    async with store._lock:  # noqa: SLF001
        store._docs = [
            DocEntry(
                id="alpha/concept",
                feature="alpha",
                depth="concept",
                persona="end_user",
                status="current",
                path=".help/templates/alpha/concept.md",
                last_modified=None,
            )
        ]
    result = await app.call_tool("gui_get_living_doc", {"doc_id": "alpha/concept"})
    assert result["success"] is True
    assert "alpha concept" in result["content"]
    assert result["feature"] == "alpha"
    assert result["depth"] == "concept"


@pytest.mark.asyncio
async def test_get_living_doc_rejects_malformed_id(app) -> None:
    result = await app.call_tool("gui_get_living_doc", {"doc_id": "../escape"})
    assert result["success"] is False
    assert "Invalid doc_id" in result["error"]


@pytest.mark.asyncio
async def test_get_living_doc_unknown_id_errors(app, workspace_with_doc) -> None:
    store = get_store()
    async with store._lock:  # noqa: SLF001
        store._docs = []
    result = await app.call_tool("gui_get_living_doc", {"doc_id": "no/such"})
    assert result["success"] is False
    assert "not found" in result["error"]
