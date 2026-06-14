// Pure logic for the Living Docs row poller.
//
// DOM-free and timer-free on purpose: the recursive-setTimeout loop,
// visibilitychange handling, fetch, and DOM rendering stay in the inline
// shim in living_docs.html. This module holds only the decision the
// poller branches on — extracted so it can be unit-tested (Vitest, Node).
//
// See specs/living-docs-poller-testing.

/** Poll cadence (ms) the shim reschedules on while rows are regenerating. */
export const POLL_INTERVAL_MS = 1500;

/**
 * Keep polling iff at least one row is still regenerating.
 *
 * Input is the `rows` array from GET /api/living-docs/rows (objects with
 * a `computed_state`). Defensive against a non-array payload or rows
 * missing `computed_state` so a malformed response can't throw inside the
 * poll loop.
 */
export function shouldKeepPolling(rows) {
  return (
    Array.isArray(rows) &&
    rows.some((r) => r && r.computed_state === "regenerating")
  );
}
