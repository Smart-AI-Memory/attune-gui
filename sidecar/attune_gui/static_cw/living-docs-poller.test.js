import { describe, expect, it } from "vitest";

import { POLL_INTERVAL_MS, shouldKeepPolling } from "./living-docs-poller.js";

const row = (computed_state) => ({ id: "f/concept", computed_state });

describe("shouldKeepPolling", () => {
  it("is true when any row is regenerating", () => {
    expect(shouldKeepPolling([row("current"), row("regenerating"), row("stale")])).toBe(true);
  });

  it("is false when no row is regenerating", () => {
    const rows = ["current", "stale", "missing", "pending-review", "errored"].map(row);
    expect(shouldKeepPolling(rows)).toBe(false);
  });

  it("is false for an empty list", () => {
    expect(shouldKeepPolling([])).toBe(false);
  });

  it("does not throw and is false for non-array input", () => {
    expect(shouldKeepPolling(undefined)).toBe(false);
    expect(shouldKeepPolling(null)).toBe(false);
    expect(shouldKeepPolling({})).toBe(false);
  });

  it("does not throw on rows missing computed_state", () => {
    expect(shouldKeepPolling([{}, null, { computed_state: undefined }])).toBe(false);
  });
});

describe("POLL_INTERVAL_MS", () => {
  it("pins the poll cadence the shim relies on", () => {
    expect(POLL_INTERVAL_MS).toBe(1500);
  });
});
