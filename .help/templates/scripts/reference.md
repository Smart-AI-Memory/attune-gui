---
type: reference
feature: scripts
depth: reference
generated_at: 2026-05-06T01:28:54.372073+00:00
source_hash: 0b54b65794acebdd97bbda1fab926772fb4db93c308e6cd66fd05fd402954c4e
status: generated
---

# Scripts reference

Editor API testing utilities for smoke test validation.

## Classes

| Class | Description |
|-------|-------------|
| `Check` | Single API endpoint test case with expected and actual response validation |
| `Suite` | Collection of test checks with pass/fail tracking |
| `Client` | HTTP client for Editor API requests with token-based authentication |

### Check

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | | Test case identifier |
| `expected_status` | `int` | | Expected HTTP status code |
| `actual_status` | `int` | | Received HTTP status code |
| `detail` | `str` | `''` | Additional test details or error information |
| `body_check` | `bool` | `True` | Whether to validate response body content |

| Property | Type | Description |
|----------|------|-------------|
| `passed` | `bool` | Whether the test check passed validation |

### Suite

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `checks` | `list[Check]` | `field(default_factory=list)` | List of test checks in the suite |

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `record` | `check: Check` | `None` | Add a test check to the suite |

| Property | Type | Description |
|----------|------|-------------|
| `failed` | `list[Check]` | List of checks that failed validation |

### Client

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `base: str` | `None` | Initialize client with base URL |
| `fetch_token` | | `None` | Retrieve authentication token for API requests |
| `get` | `path: str` | `tuple[int, dict[str, Any]]` | Send GET request and return status code with response data |
| `post` | `path: str, body: dict[str, Any]` | `tuple[int, dict[str, Any]]` | Send POST request with JSON body and return status code with response data |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `smoke` | `client: Client, corpus_root: Path` | `Suite` | Run smoke tests against Editor API endpoints |
| `main` | | `int` | Entry point for smoke test execution |

## Source files

- `scripts/smoke_editor_api.py`
