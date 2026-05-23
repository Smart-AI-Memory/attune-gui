"""Phase 1 scaffold smoke tests for the attune-gui MCP server.

Phase 1 ships an empty tool registry; these tests verify the boot path
works and the empty-registry error envelope is correct. Phase 2 will
add per-tool dispatch tests as the five read-mostly tools land.
"""

from __future__ import annotations

import pytest


def test_app_initializes_with_zero_tools() -> None:
    from attune_gui.mcp.server import create_server

    app = create_server()
    assert app.tools == {}


@pytest.mark.asyncio
async def test_unknown_tool_returns_error_envelope() -> None:
    from attune_gui.mcp.server import create_server

    app = create_server()
    result = await app.call_tool("nonexistent_tool", {})
    assert result == {
        "success": False,
        "error": "Unknown tool: nonexistent_tool",
    }


def test_server_name_is_attune_gui() -> None:
    from attune_gui.mcp.server import _mcp_server

    assert _mcp_server.name == "attune-gui"


def test_main_entry_point_is_callable() -> None:
    from attune_gui.mcp.server import main

    assert callable(main)
