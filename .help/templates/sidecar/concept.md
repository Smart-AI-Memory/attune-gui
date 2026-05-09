---
type: concept
name: sidecar-concept
feature: sidecar
depth: concept
generated_at: 2026-05-08T06:44:22.877630+00:00
source_hash: e3ed1fa3b4aba4c7d35bf2c87e344546d5ffef087a34188fb094d356b89502f8
status: generated
---

# Sidecar

The sidecar is a local FastAPI web server that provides a browser-based interface for attune's RAG, authoring, and help systems.

## What it does

The sidecar acts as a friendly gateway between your web browser and attune's core functionality. Instead of running command-line tools directly, you interact with a local web interface that handles complex operations like corpus management, template editing, and help generation.

The sidecar serves three main roles:

1. **Command execution** — It maintains a registry of available commands (like corpus indexing or template generation) and runs them through a unified interface
2. **File editing** — It provides real-time editing sessions for templates and other project files, with automatic conflict detection when files change on disk
3. **Configuration management** — It resolves configuration values from environment variables, config files, and defaults, presenting a consistent view across all attune tools

## Core components

**CommandSpec** defines what operations the GUI can perform. Each command has a name, description, argument schema, and executor function. Commands are grouped by profile (developer, author, support) to show relevant operations to each user type.

**Config** provides a resolved snapshot of all configuration values. It handles the precedence chain of environment variables, config files, and built-in defaults, so other components always see consistent settings.

**EditorSession** manages the state for editing a single file through the web interface. It tracks the original content, your draft changes, and watches for external modifications to prevent conflicts.

**Registry** maintains an in-memory view of your corpus collection from `~/.attune/corpora.json`. It knows which corpora exist, which one is currently active, and whether each corpus should warn before editing.

## Security model

The sidecar only accepts connections from localhost addresses (127.0.0.1, ::1) to prevent remote access. It generates a random authentication token on startup and stores it in a local port file, ensuring only processes on your machine can connect.

For operations that require the unpublished `attune_rag.editor` module, the sidecar provides helpful error messages rather than cryptic import failures.

## File system integration

The sidecar uses atomic writes to prevent corruption when saving files. It calculates content hashes to detect when files have changed externally, allowing the editor to prompt for conflict resolution rather than silently overwriting changes.
