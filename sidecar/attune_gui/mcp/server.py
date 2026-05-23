"""attune-gui MCP server (Phase 1 scaffold — no tools yet).

Boots a stdio MCP server that registers zero tools. Phase 2 will
populate the registry with the five read-mostly tools listed in
``docs/specs/mcp-server-scope/decisions.md``:

- ``gui_list_specs`` / ``gui_get_spec`` / ``gui_get_spec_status``
- ``gui_list_living_docs`` / ``gui_get_living_doc``

Run with::

    attune-gui-mcp
    # or
    python -m attune_gui.mcp.server

Mirrors the stdio + log-to-tempfile pattern used by
``attune_help.mcp.server`` and ``attune_author.mcp.server`` so a
single Claude-Code MCP config block works across the family.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from attune_gui import __version__

logger = logging.getLogger(__name__)


class AttuneGuiMCPServer:
    """MCP application for attune-gui.

    Holds the tool registry and dispatches calls. Phase 1 ships an
    empty registry — :meth:`call_tool` returns an error envelope for
    any name. Phase 2 wires real handlers in.
    """

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}
        self._dispatch: dict[str, Any] = {}
        logger.info(
            "AttuneGuiMCPServer initialized (tools=%d, version=%s)",
            len(self._tools),
            __version__,
        )

    @property
    def tools(self) -> dict[str, dict[str, Any]]:
        return self._tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        handler = self._dispatch.get(tool_name)
        if handler is None:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        try:
            return await handler(arguments)
        except Exception as exc:  # noqa: BLE001 — keep stdio alive across per-call failures
            logger.exception("Tool execution failed: %s", tool_name)
            return {
                "success": False,
                "error": f"Tool execution failed: {type(exc).__name__}: {exc}",
            }


_mcp_server = Server("attune-gui")
_app: AttuneGuiMCPServer | None = None


def _get_app() -> AttuneGuiMCPServer:
    global _app  # noqa: PLW0603
    if _app is None:
        _app = AttuneGuiMCPServer()
    return _app


@_mcp_server.list_tools()
async def _handle_list_tools() -> list[Tool]:
    app = _get_app()
    return [
        Tool(
            name=name,
            description=defn.get("description", ""),
            inputSchema=defn.get("input_schema", {"type": "object", "properties": {}}),
        )
        for name, defn in app.tools.items()
    ]


@_mcp_server.call_tool()
async def _handle_call_tool(
    name: str,
    arguments: dict[str, Any] | None = None,
) -> list[TextContent]:
    app = _get_app()
    result = await app.call_tool(name, arguments or {})
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


def create_server() -> AttuneGuiMCPServer:
    return AttuneGuiMCPServer()


async def _run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await _mcp_server.run(
            read_stream,
            write_stream,
            _mcp_server.create_initialization_options(),
        )


def main() -> None:
    log_dir = Path(tempfile.gettempdir()) / "attune-gui"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(str(log_dir / "attune-gui-mcp.log"))],
    )

    try:
        asyncio.run(_run_stdio())
    except KeyboardInterrupt:
        logger.info("attune-gui MCP server stopped")
    except Exception as exc:  # noqa: BLE001 — surface crash via non-zero exit
        logger.exception("Server crashed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
