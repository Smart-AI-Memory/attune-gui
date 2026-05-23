"""Phase 4 integration tests for the MCP server.

Exercises the MCP tool surface against the FastAPI route surface on the
same isolated specs root, proving the two stay in sync. Covers spec tasks
4.1 (``gui_list_specs`` parity), 4.2 (``gui_get_spec`` round-trip), and
adds a bonus round-trip through ``gui_set_spec_status`` (Phase 3) to lock
in the read-after-write contract across both surfaces.

These tests use the in-process MCP application directly via
``create_server().call_tool(...)`` — the same dispatch path the MCP SDK
hits — rather than spawning a stdio subprocess. The spec's "start the
MCP server" wording was aspirational; the value is parity with the
routes, which the in-process path proves at lower cost.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.mcp.server import create_server
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def shared_specs_root(tmp_path, monkeypatch) -> Path:
    """Isolated specs root with two fixture specs, visible to both surfaces."""
    root = tmp_path / "specs"

    alpha = root / "alpha"
    alpha.mkdir(parents=True)
    (alpha / "requirements.md").write_text(
        "# alpha\n\n**Status**: approved\n\nReq body.\n", encoding="utf-8"
    )
    (alpha / "design.md").write_text("# design alpha\n\n**Status**: draft\n", encoding="utf-8")

    beta = root / "beta"
    beta.mkdir(parents=True)
    (beta / "requirements.md").write_text("# beta\n\n**Status**: draft\n", encoding="utf-8")

    monkeypatch.setenv("ATTUNE_SPECS_ROOT", str(root))
    return root


@pytest.fixture
def mcp_app():
    return create_server()


# ---------------------------------------------------------------------------
# 4.1 — gui_list_specs parity with GET /api/cowork/specs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gui_list_specs_matches_fastapi_route(
    mcp_app, client: TestClient, shared_specs_root
) -> None:
    """Same workspace must yield the same spec list on both surfaces."""
    route_resp = client.get("/api/cowork/specs")
    assert route_resp.status_code == 200
    route_body = route_resp.json()

    mcp_resp = await mcp_app.call_tool("gui_list_specs", {})
    assert mcp_resp["success"] is True

    # The MCP surface uses {"specs": [...], "specs_roots": [...]} — the
    # FastAPI route additionally returns a legacy "specs_root" string.
    # Compare the field that both surfaces share verbatim.
    assert mcp_resp["specs"] == route_body["specs"]
    assert mcp_resp["specs_roots"] == route_body["specs_roots"]


# ---------------------------------------------------------------------------
# 4.2 — gui_get_spec content parity with the on-disk fixture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gui_get_spec_returns_disk_truth(
    mcp_app, client: TestClient, shared_specs_root
) -> None:
    """gui_get_spec content must match what's on disk, and the route's
    listing must reference the same feature with the same status."""
    mcp_resp = await mcp_app.call_tool("gui_get_spec", {"feature": "alpha"})
    assert mcp_resp["success"] is True
    assert mcp_resp["feature"] == "alpha"

    # The phase contents the tool returns must match the file bytes on disk.
    for phase_name, phase in mcp_resp["phases"].items():
        expected = (shared_specs_root / "alpha" / phase["file"]).read_text(encoding="utf-8")
        assert phase["content"] == expected, f"content drift on phase={phase_name}"

    # And the FastAPI listing for the same spec must agree on the most-
    # advanced phase + its status — proving both surfaces read the same data.
    route_resp = client.get("/api/cowork/specs")
    alpha_entry = next(s for s in route_resp.json()["specs"] if s["feature"] == "alpha")
    most_advanced = alpha_entry["phase"]  # e.g. "design.md"
    # _PHASE_NAMES order: requirements -> design -> tasks
    expected_name = most_advanced.replace(".md", "")
    assert mcp_resp["phases"][expected_name]["status"] == alpha_entry["status"]


# ---------------------------------------------------------------------------
# Bonus — gui_set_spec_status round-trip across both surfaces (Phase 3 cover)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_spec_status_round_trips_to_fastapi_route(
    mcp_app, client: TestClient, shared_specs_root
) -> None:
    """Flip status via MCP; the FastAPI listing must reflect the new value."""
    # Baseline — beta's only phase is requirements, currently "draft".
    pre = client.get("/api/cowork/specs").json()
    beta_pre = next(s for s in pre["specs"] if s["feature"] == "beta")
    assert beta_pre["status"] == "draft"

    # Flip via MCP.
    flip = await mcp_app.call_tool(
        "gui_set_spec_status",
        {"feature": "beta", "phase": "requirements", "status": "approved"},
    )
    assert flip["success"] is True
    assert flip["status"] == "approved"

    # FastAPI now sees the new status — no cache, both surfaces read the file.
    post = client.get("/api/cowork/specs").json()
    beta_post = next(s for s in post["specs"] if s["feature"] == "beta")
    assert beta_post["status"] == "approved"

    # And the MCP get_spec_status tool agrees.
    follow = await mcp_app.call_tool(
        "gui_get_spec_status", {"feature": "beta", "phase": "requirements"}
    )
    assert follow["status"] == "approved"
