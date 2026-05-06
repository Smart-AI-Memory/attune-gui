---
type: task
feature: scripts
depth: task
generated_at: 2026-05-06T01:28:44.437291+00:00
source_hash: 0b54b65794acebdd97bbda1fab926772fb4db93c308e6cd66fd05fd402954c4e
status: generated
---

# Work with scripts

Run editor API smoke tests when you need to verify basic functionality after code changes or before deployment.

## Prerequisites

- Access to the project source code
- Python environment with project dependencies installed
- Running editor API server (if testing against live endpoints)

## Steps

1. **Navigate to the scripts directory.**
   The smoke test script is located at `scripts/smoke_editor_api.py`.

2. **Configure the test client.**
   Set the base URL for the API you want to test. The `Client` class handles authentication and HTTP requests.

3. **Run the smoke test.**
   Execute the script to perform basic API checks:
   ```bash
   python scripts/smoke_editor_api.py
   ```

4. **Review the test results.**
   The `Suite` class collects all checks and reports which ones passed or failed. Each `Check` records the expected vs actual status codes and response details.

5. **Address any failures.**
   If tests fail, examine the `detail` field in failed checks to understand what went wrong. Common issues include authentication problems or API endpoint changes.

## Verify success

The smoke test passes when all checks in the suite return `passed = True`. Failed tests will show specific error details including expected vs actual status codes.

## Key files

- `scripts/smoke_editor_api.py` - Main smoke test implementation
- `scripts/**` - Additional utility scripts

## Common modifications

- Modify `smoke()` function to add new API endpoint checks
- Update `Client` class methods to handle different authentication schemes
- Adjust `Check` criteria for different expected response codes
