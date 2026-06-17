import { describe, expect, it } from "vitest";

import { batchView, isTerminal, shouldClose } from "./batch-panel.js";

const pending = (over = {}) => ({
  state: "pending",
  processing_status: "in_progress",
  request_count: 10,
  request_counts: { succeeded: 3, errored: 0, canceled: 0, expired: 0, processing: 7 },
  ended_at: null,
  batch_id: "msgbatch_123",
  ...over,
});

describe("batchView", () => {
  it("hides the panel for the none state", () => {
    expect(batchView({ state: "none" })).toEqual({ visible: false });
  });

  it("shows an error frame with detail passed through, bar untouched", () => {
    const v = batchView({ state: "error", detail: "boom" });
    expect(v).toMatchObject({ visible: true, label: "Status unavailable", counts: "", detail: "boom" });
    expect(v.pct).toBeNull();
  });

  it("falls back to 'retry' when an error frame has no detail", () => {
    expect(batchView({ state: "error" }).detail).toBe("retry");
  });

  it("renders a pending frame: pct, counts, status label, batch detail", () => {
    const v = batchView(pending());
    expect(v).toMatchObject({
      visible: true,
      pct: 30, // (3 done / 10 total)
      counts: "3/10",
      label: "in_progress",
      detail: "batch msgbatch_123",
    });
  });

  it("renders a terminal frame as a completion summary", () => {
    const v = batchView(
      pending({
        processing_status: "ended",
        ended_at: "2026-06-14T12:00:00Z",
        request_counts: { succeeded: 9, errored: 1, canceled: 0, expired: 0 },
      }),
    );
    expect(v.label).toBe("Completed — 9 succeeded, 1 errored");
    expect(v.pct).toBe(100); // (9 + 1) / 10
  });

  it("guards against divide-by-zero: total 0 → pct 0, not NaN", () => {
    const v = batchView(pending({ request_count: 0, request_counts: {} }));
    expect(v.pct).toBe(0);
    expect(v.counts).toBe("");
  });
});

describe("isTerminal", () => {
  it.each(["ended", "canceled", "expired"])("is true for processing_status %s", (s) => {
    expect(isTerminal({ processing_status: s })).toBe(true);
  });

  it("is true when ended_at is set regardless of status", () => {
    expect(isTerminal({ processing_status: "in_progress", ended_at: "2026-06-14T12:00:00Z" })).toBe(true);
  });

  it("is false for an in-progress frame", () => {
    expect(isTerminal({ processing_status: "in_progress", ended_at: null })).toBe(false);
  });
});

describe("shouldClose", () => {
  it("closes on none and error frames", () => {
    expect(shouldClose({ state: "none" })).toBe(true);
    expect(shouldClose({ state: "error" })).toBe(true);
  });

  it("closes on a terminal pending frame", () => {
    expect(shouldClose(pending({ processing_status: "ended" }))).toBe(true);
  });

  it("keeps the stream open on a non-terminal pending frame", () => {
    // The reconnect-suppression invariant: must NOT close here, or the
    // panel would never receive subsequent progress frames.
    expect(shouldClose(pending())).toBe(false);
  });
});
