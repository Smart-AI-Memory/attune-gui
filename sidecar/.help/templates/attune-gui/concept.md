---
type: concept
feature: attune-gui
depth: concept
generated_at: 2026-05-05T00:12:36.232891+00:00
source_hash: 373196211438f141eb9a7c64116a3e8312048764f33da724833860f48eb607bc
status: generated
---

# Attune GUI

A local FastAPI web server that provides a browser-based interface for attune-rag, attune-author, and attune-help. The GUI runs as a sidecar process, handling document editing, corpus management, and job execution through web endpoints.

## Architecture

The GUI operates as a standalone FastAPI application with these core components:

**Command registry** — Maintains a catalog of available operations (like document generation or corpus indexing) that the web interface can trigger. Each command has a specification defining its arguments, execution function, and user-facing metadata.

**Corpus management** — Tracks document collections stored in `~/.attune/corpora.json`. Users can register new corpora, switch between active corpora, and configure editing permissions through the web interface.

**Editor sessions** — Manages in-memory state for each open document tab. Sessions track the original file content, current draft changes, and file system polling to detect external modifications.

**Job execution** — Runs long-running operations (like document generation) in background threads while streaming progress updates to the browser. The job registry maintains status, output logs, and results for up to 200 recent jobs.

## Security model

The GUI enforces an origin guard that only accepts requests from localhost addresses (`localhost`, `127.0.0.1`, `[::1]`). This prevents remote access while allowing browser-based interaction from the local machine.

A random token generated at startup provides additional protection against cross-site request attacks. The token must be included in requests to sensitive endpoints.

## Document editing workflow

When you open a document in the GUI editor:

1. **Session creation** — An `EditorSession` loads the current file content and starts polling for external changes
2. **Draft tracking** — Your edits are stored separately from the original content, allowing you to see what changed
3. **Conflict detection** — If another process modifies the file, the session detects the change and can rebase your draft
4. **Save coordination** — The GUI can save drafts back to disk or discard changes to return to the original content

This design prevents data loss when multiple tools (like your text editor and the GUI) work with the same files.

## Integration points

| Component | Purpose | Example usage |
|-----------|---------|---------------|
| **Command executors** | Run attune-rag queries, generate documents, index corpora | Background job triggered from web UI |
| **File watchers** | Detect when documents change outside the GUI | Editor session polls file timestamps |
| **Corpus registry** | Coordinate with attune-author's corpus management | Switch active corpus affects which documents appear |

## When to use the GUI vs. command line

Use the GUI when you need visual document editing, want to manage multiple corpora through a web interface, or prefer monitoring job progress through a browser. The command-line tools remain faster for scripting and automation workflows.

The GUI adds overhead but provides immediate feedback and reduces the need to remember command syntax for infrequent operations.
