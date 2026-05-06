---
type: task
feature: attune_gui-entry
depth: task
generated_at: 2026-05-06T01:28:23.162192+00:00
source_hash: eeb18d59126ba51aac853e30d7dd4f788b93e41e8c99f37f2a709b501ed2ecc4
status: generated
---

# Configure the attune GUI entry point

Use this procedure when you need to modify how the attune GUI application starts up, change its routing configuration, or update CORS and security settings.

## Prerequisites

- Access to the project source code
- Understanding of FastAPI application structure
- Familiarity with CORS and origin guard concepts

## Configure the application

1. **Open the entry point file.**
   Navigate to `sidecar/attune_gui/app.py` in your editor.

2. **Locate the create_app function.**
   This function builds the FastAPI application and wires all components together.

3. **Modify the application settings.**
   Update the specific configuration you need:
   - Add or remove routers in the router registration section
   - Adjust CORS settings for cross-origin requests
   - Modify origin guard parameters for security
   - Change middleware or dependency injection

4. **Follow the existing patterns.**
   Match the naming conventions, error handling style, and logging approach used elsewhere in the file.

5. **Test your changes.**
   Run `pytest -k "attune_gui-entry"` to verify your modifications don't break existing functionality.

## Verify the configuration

Start the application and confirm it behaves as expected. The GUI should load without CORS errors, and all routes should respond correctly.

## Key files

- `sidecar/attune_gui/app.py` — Contains the `create_app()` function that builds the complete FastAPI application
