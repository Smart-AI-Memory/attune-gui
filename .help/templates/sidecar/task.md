---
feature: sidecar
depth: task
generated_at: 2026-05-06T03:22:24.078182+00:00
source_hash: 9a45296c182496f7a010644896af3e7b8be6dca9a5412ea5145a2d2e9d9944ab
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
- `is_valid_key()` in `sidecar/attune_gui/config.py`
- `known_keys()` in `sidecar/attune_gui/config.py`
- `env_var_for()` in `sidecar/attune_gui/config.py`
