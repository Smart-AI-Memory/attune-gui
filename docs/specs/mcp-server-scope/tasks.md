# Tasks — MCP server for attune-gui

## Phase 1 — Scaffold

- [x] **1.1** Add `mcp>=0.9.0` to `[project.optional-dependencies].mcp`
      in pyproject.toml (mirror attune-help / attune-author pattern)
- [x] **1.2** Create `sidecar/attune_gui/mcp/__init__.py` and
      `sidecar/attune_gui/mcp/server.py`
- [x] **1.3** Add `attune-gui-mcp = "attune_gui.mcp.server:main"`
      to `[project.scripts]`
- [x] **1.4** Start server on stdio per the MCP server pattern
      used by sibling packages

## Phase 2 — Implement core tools

For each:

- [x] **2.1** `gui_list_specs` — wrap existing
      `routes/cowork_specs.py` GET handler
- [x] **2.2** `gui_get_spec` — wrap existing per-spec read
      (returns content of all present phase files)
- [x] **2.3** `gui_get_spec_status` — extract `**Status**:`
      line from a phase file. *Inherits a pre-existing regex bug
      in `_STATUS_VALUE_RE` that misses the common `**Status:**`
      format; tracked separately.*
- [x] **2.4** `gui_list_living_docs` — wrap existing
      living-docs listing route
- [x] **2.5** `gui_get_living_doc` — wrap existing
      living-doc content read (with path-traversal guard)

Each tool:
- Has a clear schema (input + output)
- Has a docstring that Claude can read to decide when to
  invoke
- Handles path validation (consistent with existing route
  protection)

## Phase 3 — Optional write tool

- [x] **3.1** `gui_set_spec_status` — wrap the existing
      PUT route. Same validation (slug regex, phase enum,
      `_VALID_STATUSES`). Atomic write via `attune_gui._fs.atomic_write`.
      Inserts a `**Status**:` line if missing, otherwise substitutes
      via `_STATUS_RE`. The only write tool — additive to the
      five read-mostly tools.

## Phase 4 — Integration test

- [ ] **4.1** Test that starts the MCP server, queries
      `gui_list_specs`, and asserts the result matches the
      FastAPI route's response on the same data
- [ ] **4.2** Same for `gui_get_spec` against a known fixture
      spec

## Phase 5 — Docs

- [x] **5.1** README section: "MCP integration" — how to
      configure Claude Code to use the server
- [x] **5.2** Example `.mcp.json` snippet showing
      `attune-gui-mcp` registered
- [x] **5.3** Cross-link with attune-ai's
      ops-specs-features spec (the two complement each other)

## Out of scope

- Authentication / API tokens — local stdio MCP doesn't need it
- Streaming responses — start with one-shot tool calls only
- Multi-root federation in MCP — Phase 1 lists local specs;
  cross-root listing can be a follow-up
- Editing template content via MCP — covered by GUI editor
- Replacing the FastAPI surface — MCP is additive, not a
  replacement
