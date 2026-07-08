---
type: task
name: sidecar-task
feature: sidecar
depth: task
generated_at: 2026-06-23T04:14:34.353737+00:00
source_hash: 6d1a3b2a6686655be45c94fbd62b43d5887dec3496603be6ca7a12500650779e
status: generated
---

# Work with the attune-gui sidecar

Use the attune-gui sidecar when you need to extend or modify the local FastAPI process that drives attune-rag, attune-author, and attune-help.

## Prerequisites

- Read access to the `sidecar/attune_gui/` source tree
- A working Python environment with the attune-gui package installed
- `pytest` available on your path

## Steps

1. **Identify the entry point that owns the behavior you want to change.**

   The sidecar is organized by responsibility. Match your goal to the right module:

   | Goal | Function | Module |
   |---|---|---|
   | Change how the FastAPI app starts, sets up CORS, or enforces the origin guard | `create_app()` | `sidecar/attune_gui/app.py` |
   | Look up or list registered commands | `get_command()`, `list_commands()` | `sidecar/attune_gui/commands.py` |
   | Read or validate config keys and their sources | `get()`, `known_keys()`, `is_valid_key()`, `env_var_for()` | `sidecar/attune_gui/config.py` |
   | Write files atomically from a route handler | `atomic_write()` | `sidecar/attune_gui/_fs.py` |

2. **Read the function's signature, docstring, and return type before editing.**

   Confirm the function owns exactly the behavior you need. For example:
   - `get_command(name: str) -> CommandSpec | None` returns `None` when the name is not registered — callers must handle that case.
   - `list_commands(profile: str | None = None) -> list[dict[str, Any]]` filters by profile; pass `None` to return all commands.
   - `get_source(key: ConfigKey) -> KeySource` returns `'default'` when no env var or file override is present.

3. **Make your change in the identified module.**

   Keep changes consistent with the module's existing error-handling style and naming conventions. If you add a new config key, register it in `_KEYS` and provide a corresponding `env_var_for()` mapping. If you add a command, define it as a `CommandSpec` with all required fields (`name`, `title`, `domain`, `description`, `args_schema`, `executor`) before registering it.

4. **Run the sidecar test suite.**

   ```
   pytest -k "sidecar"
   ```

   Fix any failures before moving on. The test run is your confirmation that existing routes, command dispatch, and config resolution still behave correctly.

## Verify success

After the tests pass, start the sidecar locally and confirm the following:

- `create_app()` returns without error and the FastAPI app responds to requests from `localhost`, `127.0.0.1`, or `::1` (the allowed origin hosts).
- `list_commands()` includes your new or modified command in its output.
- `get(key)` returns the expected value, and `get_source(key)` reports the correct precedence level (`'default'`, env, or file).

If all three checks pass, your change is complete.
