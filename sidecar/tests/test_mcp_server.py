"""Server-level smoke tests for the attune-gui MCP server.

Verifies the boot path, server identity, and error-envelope contract.
Per-tool behavior is covered in ``test_mcp_tools.py``.
"""

from __future__ import annotations

import pytest


def test_app_initializes_with_phase2_tool_registry() -> None:
    from attune_gui.mcp.server import create_server

    app = create_server()
    assert set(app.tools) == {
        "gui_list_specs",
        "gui_get_spec",
        "gui_get_spec_status",
        "gui_list_living_docs",
        "gui_get_living_doc",
    }


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
