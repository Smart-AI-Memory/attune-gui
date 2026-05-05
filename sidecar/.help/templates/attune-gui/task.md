---
type: task
feature: attune-gui
depth: task
generated_at: 2026-05-05T00:12:55.669017+00:00
source_hash: 373196211438f141eb9a7c64116a3e8312048764f33da724833860f48eb607bc
status: generated
---

# Work with attune gui

Use attune-gui when you need a local web interface to manage help documentation, run commands, and edit corpus templates.

## Prerequisites

- Access to the project source code
- Python development environment set up
- Familiarity with FastAPI applications

## Configure the application

1. **Create the FastAPI app instance.**
   Call `create_app()` from `attune_gui/app.py` to build the complete application with CORS, origin guard, and all routes:
   ```python
   from attune_gui.app import create_app
   app = create_app()
   ```

2. **Register commands for the GUI.**
   Use the command registry to make functions available through the web interface. Check existing commands with `list_commands()` or add new ones following the `CommandSpec` pattern.

3. **Set up corpus management.**
   Initialize the corpus registry by calling `load_registry()` from `attune_gui/editor_corpora.py`. This loads your existing corpus configurations or creates an empty registry.

## Run commands through the interface

1. **List available commands.**
   Call `list_commands(profile='developer')` to see all commands registered for your profile. Each command returns as a JSON-serializable dictionary with name, title, description, and argument schema.

2. **Execute a specific command.**
   Use `get_command(name)` to retrieve a `CommandSpec` by name, then call its executor function. The command system handles job tracking and cancellation automatically.

3. **Monitor job status.**
   Access the `JobRegistry` to track running commands. Jobs store output lines, status, timestamps, and results for display in the GUI.

## Manage document corpora

1. **Register a new corpus.**
   Call `register(name, path)` to add a corpus directory to the registry:
   ```python
   entry = register("my-docs", "/path/to/docs", kind="source")
   ```

2. **Switch active corpus.**
   Use `set_active(corpus_id)` to change which corpus the editor works with. This raises `KeyError` if the corpus doesn't exist.

3. **Save registry changes.**
   Call `save_registry(reg)` to persist your corpus configuration to `~/.attune/corpora.json`.

## Edit templates with live sessions

1. **Start an editing session.**
   Create an `EditorSession` for a specific file path:
   ```python
   session = EditorSession.load(abs_path, poll_interval=0.1)
   session.start()
   ```

2. **Update draft content.**
   Call `session.update_draft(text)` to modify the working copy without affecting the base file.

3. **Check for external changes.**
   Use `session.matches_base()` to detect if the file changed on disk. Call `session.rebase()` to incorporate external changes.

## Verify the setup

Run the FastAPI development server and navigate to the local URL. You should see:
- The command interface loads without errors
- Corpus registry displays your configured corpora
- Template editor opens files from the active corpus
- Jobs execute and display output in real-time

The application serves on localhost with CORS configured for local development and includes origin validation for security.
