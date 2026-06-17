// Pure logic for the Living Docs "Batch progress" panel.
//
// DOM-free and window-free on purpose: the browser loads this as a native
// ES module (`<script type="module">`), and Vitest imports it directly in
// Node — no jsdom needed. All DOM wiring (EventSource, querySelector,
// applying the view) lives in the inline shim in living_docs.html.
//
// Consumes the frame shape emitted by GET /api/batch/status/stream
// (see specs/gui-batch-status-sse): {state, processing_status,
// request_count, request_counts{...}, ended_at, batch_id, detail}.

/** processing_status values (and a set ended_at) that mean the batch stopped. */
export const TERMINAL = ["ended", "canceled", "expired"];

/** Has the batch reached a stop state? */
export function isTerminal(frame) {
  return TERMINAL.includes(frame.processing_status) || Boolean(frame.ended_at);
}

/**
 * Map an SSE frame to a flat view model the DOM shim applies verbatim.
 *
 * Returns:
 *   { visible: false }                                  // hide the panel
 *   { visible: true, label, counts, detail, pct }       // render
 * `pct` is `null` for the error state (leave the progress bar untouched);
 * a number 0..100 otherwise.
 */
export function batchView(frame) {
  if (frame.state === "none") return { visible: false };
  if (frame.state === "error") {
    return {
      visible: true,
      label: "Status unavailable",
      counts: "",
      detail: frame.detail || "retry",
      pct: null,
    };
  }
  const c = frame.request_counts || {};
  const total = frame.request_count || 0;
  const done =
    (c.succeeded || 0) + (c.errored || 0) + (c.canceled || 0) + (c.expired || 0);
  return {
    visible: true,
    pct: total ? Math.round((done / total) * 100) : 0,
    counts: total ? `${done}/${total}` : "",
    label: isTerminal(frame)
      ? `Completed — ${c.succeeded || 0} succeeded, ${c.errored || 0} errored`
      : frame.processing_status || "processing",
    detail: frame.batch_id ? `batch ${frame.batch_id}` : "",
  };
}

/**
 * Should the client close the EventSource (and suppress the browser's
 * auto-reconnect)? True once the server has sent its last frame for this
 * stream: a none/error frame, or any terminal pending frame.
 */
export function shouldClose(frame) {
  return frame.state !== "pending" || isTerminal(frame);
}
