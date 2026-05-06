---
type: concept
feature: attune_gui-entry
depth: concept
generated_at: 2026-05-06T01:28:13.312831+00:00
source_hash: eeb18d59126ba51aac853e30d7dd4f788b93e41e8c99f37f2a709b501ed2ecc4
status: generated
---

# Attune GUI Entry

The FastAPI app factory that builds Attune's web interface with security, cross-origin support, and all API routes.

## What it creates

The `create_app()` function assembles a complete FastAPI application by wiring together three essential components:

- **Origin guard** — validates requests come from trusted sources
- **CORS middleware** — enables cross-origin requests from the frontend
- **Router registration** — connects all API endpoints to their handlers

This factory pattern lets you spin up the web server with a single function call while keeping security and routing configuration centralized.

## Application structure

| Component | What it does | Why it matters |
|-----------|--------------|----------------|
| **Origin guard** | Blocks requests from untrusted domains | Prevents malicious sites from hitting your local API |
| **CORS middleware** | Allows browser requests from the frontend | Enables the web UI to communicate with the backend |
| **Router wiring** | Connects URL paths to handler functions | Makes all API endpoints available under one app |

## Entry point location

The factory lives in `sidecar/attune_gui/app.py`. When you start the GUI server, it calls `create_app()` to build the FastAPI instance, then serves that instance on your local port.

## Integration pattern

Other parts of the codebase don't call `create_app()` directly — it's invoked once at server startup. The resulting FastAPI app handles all incoming requests and routes them to the appropriate skill handlers, file operations, or configuration endpoints.
