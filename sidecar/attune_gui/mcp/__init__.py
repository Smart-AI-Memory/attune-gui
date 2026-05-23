"""MCP server for attune-gui.

Exposes a deliberately small, read-mostly set of tools (specs and
living-docs) to MCP clients like Claude Code. See
``docs/specs/mcp-server-scope/`` for the scope decisions.

The ``mcp`` SDK is an *optional* dependency — install via the
``mcp`` extra (``pip install 'attune-gui[mcp]'``). Importing this
package without the SDK is fine; importing :mod:`.server` is not.
"""
