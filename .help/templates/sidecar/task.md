---
feature: sidecar
depth: task
generated_at: 2026-05-06T01:32:33.449490+00:00
source_hash: 6cf2ec1dea9a074d0cc9830a3dd6a31eb9696ebfd5fe85f42cbb10d54afc2067
status: generated
---

# Work with sidecar

Use sidecar when you need to sidecar.

## Prerequisites

- Access to the project source code
- Familiarity with the files under sidecar/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what sidecar
   does today before making changes.
   The primary functions are:
   - `require_editor_submodule()` in `sidecar/attune_gui/_editor_dep.py` — Import ``attune_rag.editor.<name>`` or raise an HTTP 503.
   - `atomic_write()` in `sidecar/attune_gui/_fs.py` — Write ``text`` to ``target`` atomically; return the new mtime.
   - `create_app()` in `sidecar/attune_gui/app.py` — Build the FastAPI app with origin-guard, CORS, and all routers wired.
   - `get_command()` in `sidecar/attune_gui/commands.py` — Return the CommandSpec for ``name``, or None if it isn't registered.
   - `list_commands()` in `sidecar/attune_gui/commands.py` — Return registered commands as JSON-serializable dicts.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "sidecar"`.

## Key files

- `sidecar/**`

## Common modifications

Functions you are most likely to modify:

- `require_editor_submodule()` in `sidecar/attune_gui/_editor_dep.py`
- `atomic_write()` in `sidecar/attune_gui/_fs.py`
- `create_app()` in `sidecar/attune_gui/app.py`
- `get_command()` in `sidecar/attune_gui/commands.py`
- `list_commands()` in `sidecar/attune_gui/commands.py`
- `load_registry()` in `sidecar/attune_gui/editor_corpora.py`
- `save_registry()` in `sidecar/attune_gui/editor_corpora.py`
- `list_corpora()` in `sidecar/attune_gui/editor_corpora.py`
