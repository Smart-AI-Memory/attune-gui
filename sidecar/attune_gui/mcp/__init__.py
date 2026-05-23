"""MCP server for attune-gui.

Exposes a deliberately small, read-mostly set of tools (specs and
living-docs) to MCP clients like Claude Code. See
``docs/specs/mcp-server-scope/`` for the scope decisions.

The ``mcp`` SDK is a core dependency — installing ``attune-gui`` is
enough to get the ``attune-gui-mcp`` console script, matching the
``attune-help`` and ``attune-author`` packaging pattern.
"""
