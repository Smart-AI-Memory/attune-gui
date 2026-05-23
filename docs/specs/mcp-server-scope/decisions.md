# Decisions — MCP server for attune-gui (scope)

**Status:** Active — Phase 1 (Scaffold). All execution gates cleared 2026-05-23.
**Owner:** Patrick

## Gate clearance log

- **2026-05-23** — all three execution gates verified clear:
  1. attune-gui PR [#30](https://github.com/Smart-AI-Memory/attune-gui/pull/30) (federated specs) merged + stable since 2026-05-12.
  2. attune-ai PR [#230](https://github.com/Smart-AI-Memory/attune-ai/pull/230) ops-specs-features execution gate verified 2026-05-12; Phases 1–3 shipped via [#236](https://github.com/Smart-AI-Memory/attune-ai/pull/236), [#239](https://github.com/Smart-AI-Memory/attune-ai/pull/239), [#249](https://github.com/Smart-AI-Memory/attune-ai/pull/249).
  3. attune-gui CI green on recent runs; no active CI debt.

Spec moves out of "gated draft" and into active execution. Phase 1 scaffold (pyproject extra, `mcp/server.py` skeleton, console script) lands in a separate PR.

---

## Problem

attune-help and attune-author both expose MCP servers
(`attune_help.mcp`, `attune_author.mcp.server`). attune-gui
does not. Its surface is FastAPI routes + frontend, which means
Claude Code (and other MCP clients) can't programmatically
query attune-gui's data — specs, living docs, telemetry,
federated views.

This creates an asymmetry: every other attune package exposes
its key operations as MCP tools; attune-gui is the only one
that doesn't.

## Decision

Add a focused MCP server to attune-gui exposing a **deliberately
small** set of read-mostly tools. Don't replicate every FastAPI
route — pick the ones a Claude Code session would actually
want.

## What's in scope (initial)

Read-only or low-impact tools:

- `gui_list_specs` — federated multi-root spec listing
  (mirror of the FastAPI route from PR #30)
- `gui_get_spec` — fetch decisions.md / tasks.md / design.md /
  requirements.md content for a spec
- `gui_get_spec_status` — current `**Status**:` line for a
  spec's phase files
- `gui_list_living_docs` — enumerate living-docs templates
- `gui_get_living_doc` — fetch a specific living-docs
  template's content

Optional write tools (gated):

- `gui_set_spec_status` — flip a spec's status (already
  available via FastAPI; mirror to MCP for parity)

## What's NOT in scope

- Editing template content (covered by the GUI editor; not
  Claude Code's job)
- Anthropic API passthrough — gui doesn't call Anthropic
  directly anyway (verified 2026-05-11)
- Authentication / multi-tenant features
- Real-time WebSocket / SSE streaming
- Search / RAG over living-docs — that's attune-rag's job

## Alternatives considered

1. **No MCP server** — current state. attune-gui is
   dashboard-only, accessible to humans not agents. Real cost:
   Claude Code session can't surface attune-gui content
   without screenshots or paste.
2. **Wrap every FastAPI route as an MCP tool** — too much
   surface; many routes are frontend-internal. MCP should be
   the agent-facing API, not the GUI's full API.
3. **Add MCP to attune-rag instead** (since rag is the
   data-richest sibling) — different problem. attune-rag's
   data IS its API; attune-gui's data is structured/spec-
   centric and benefits more from being agent-readable.

## Acceptance criteria

- `attune_gui mcp-serve` entry point that starts a stdio MCP
  server
- ~5 tools listed above implemented, each with a clear
  schema and docstring
- Integration test exercising at least 2 tools end-to-end
- Compatible with the same Claude Code MCP configuration
  pattern as attune-help / attune-author

## Execution gate

**Cleared 2026-05-23** — see "Gate clearance log" at top.

Original gate (preserved for context):

1. attune-gui's federated specs feature (PR #30) is stable
2. attune-ai's [#230 ops-specs-features](https://github.com/Smart-AI-Memory/attune-ai/pull/230) execution gate clears
   (since the two specs touch related territory)
3. No active CI debt in attune-gui

The two specs (attune-ai #230 and this one) complement each
other: #230 brings specs into attune ops dashboard for human
viewing; this spec exposes specs to MCP for agent querying.
Both serve the spec-driven workflow but for different
clients.

---

(per-phase decisions appended as work happens)
