---
type: concept
feature: scripts
depth: concept
generated_at: 2026-05-06T01:28:34.613160+00:00
source_hash: 0b54b65794acebdd97bbda1fab926772fb4db93c308e6cd66fd05fd402954c4e
status: generated
---

# Scripts

## What

Scripts provide automated testing utilities for the project, specifically smoke tests that verify basic API functionality. The primary script is an Editor API smoke tester that validates endpoints are responding correctly with expected status codes and response formats.

## Why

Smoke tests catch integration failures early by exercising real API endpoints with minimal test cases. Unlike unit tests that verify individual functions, smoke tests confirm that the entire system can handle basic requests after deployment or configuration changes.

## Core components

**Check** represents a single API test case with an endpoint name, expected status code, and actual response details. Each check can verify both the HTTP status and optionally validate the response body structure.

**Suite** collects multiple checks and tracks which ones passed or failed. You record individual checks into a suite, then query the suite for failed tests to identify problems.

**Client** handles HTTP communication with the API under test. It manages authentication by fetching tokens and provides GET/POST methods that return both status codes and response data for validation.

## Test execution flow

The `smoke()` function orchestrates a complete test run by creating a client, connecting to the API, and executing a series of predefined checks against known endpoints. It returns a suite containing all test results.

The `main()` function provides a command-line entry point that runs the smoke tests and returns an exit code based on whether any checks failed.
