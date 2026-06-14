# Design: Testable Cowork dashboard JS

> Phase 2 design for `specs/dashboard-js-testing/`. Read
> `requirements.md` first. Single layer: **attune-gui**.

**Status**: draft

---

## Architecture

The pattern, in one line: **pure logic moves to a plain ES module in
`static_cw/`; the inline `<script>` shrinks to a DOM-glue shim that
imports it; Vitest tests the pure module directly.** No bundler, no
build artifact — the `.js` file is both the source and the served asset.

```
sidecar/attune_gui/static_cw/
  batch-panel.js          ← NEW: pure logic (no DOM, no window)  ┐
  batch-panel.test.js     ← NEW: Vitest unit tests               │ served as-is
  style.css               (existing)                             ┘ at /cw-static/*

sidecar/attune_gui/templates/living_docs.html
  {% block scripts %}
    <script type="module">                      ← was: inline IIFE
      import { batchView, isTerminal } from '/cw-static/batch-panel.js';
      // ...thin DOM glue: EventSource + querySelector + apply view…
    </script>
```

The browser loads `batch-panel.js` as a native ES module
(`import … from '/cw-static/batch-panel.js'`), served by the existing
`StaticFiles` mount at `/cw-static`
([`app.py:109`](attune-gui/sidecar/attune_gui/app.py)). Vitest (Node ESM)
imports the same file directly — because it's DOM-free, it loads without
jsdom.

### What is "pure" (tested) vs "glue" (inline)

The batch panel's logic splits cleanly. The **pure** half — the part with
all the branching, and the part that broke silently before — becomes the
module:

```js
// static_cw/batch-panel.js  (NEW)
export const TERMINAL = ["ended", "canceled", "expired"];

export function isTerminal(frame) {
  return TERMINAL.includes(frame.processing_status) || Boolean(frame.ended_at);
}

/** Frame → a flat view model the DOM shim applies verbatim. */
export function batchView(frame) {
  if (frame.state === "none") return { visible: false };
  if (frame.state === "error") {
    return { visible: true, label: "Status unavailable", counts: "",
             detail: frame.detail || "retry", pct: null };
  }
  const c = frame.request_counts || {};
  const total = frame.request_count || 0;
  const done = (c.succeeded||0)+(c.errored||0)+(c.canceled||0)+(c.expired||0);
  return {
    visible: true,
    pct: total ? Math.round((done / total) * 100) : 0,
    counts: total ? `${done}/${total}` : "",
    label: isTerminal(frame)
      ? `Completed — ${c.succeeded||0} succeeded, ${c.errored||0} errored`
      : (frame.processing_status || "processing"),
    detail: frame.batch_id ? `batch ${frame.batch_id}` : "",
  };
}

/** Should the client close the stream (suppress auto-reconnect)? */
export function shouldClose(frame) {
  return frame.state !== "pending" || isTerminal(frame);
}
```

The **glue** half stays inline in the template (it needs `document`,
`EventSource`, and runs on page load) but becomes a dumb applier:

```html
<script type="module">
  import { batchView, shouldClose } from '/cw-static/batch-panel.js';
  const els = { /* querySelector the panel nodes */ };
  function apply(v) { /* set hidden, textContent, fill width from v */ }
  const es = new EventSource('/api/batch/status/stream');
  es.onmessage = (ev) => {
    let f; try { f = JSON.parse(ev.data); } catch { return; }
    apply(batchView(f));
    if (shouldClose(f)) es.close();
  };
</script>
```

The shim has no branching worth testing; every decision lives in the
module. This is the rule the doc encodes for future panels.

## Test runner: extend editor-frontend's Vitest project (chosen)

There is **no root `package.json`** — Vitest exists only under
`editor-frontend/` (`vitest.config.ts` → `include: ["src/**/*.test.ts"]`),
run by the `frontend (Vitest)` CI job
([`.github/workflows/tests.yml:74`](attune-gui/.github/workflows/tests.yml),
`working-directory: editor-frontend`).

**Decision:** broaden the *existing* project rather than stand up a
second one. `editor-frontend` becomes "the attune-gui frontend test
project," covering both the editor (`src/**`) and the dashboard
(`../sidecar/.../static_cw/**`):

```ts
// editor-frontend/vitest.config.ts
export default defineConfig({
  test: {
    include: [
      "src/**/*.test.ts",
      "../sidecar/attune_gui/static_cw/**/*.test.js",
    ],
    exclude: ["node_modules", "e2e"],
  },
});
```

The dashboard test file lives **next to its module** in `static_cw/`
(preserving the "tests next to source" convention) and imports it with a
relative path (`./batch-panel.js`). Only the *glob* reaches across
directories; resolution stays colocated. The existing `frontend (Vitest)`
CI job then covers the dashboard modules with **zero new job, zero new
`node_modules`, zero new toolchain** — the lowest-infra path consistent
with the no-build decision.

## API changes

None. No route, schema, or contract change. `batch-panel.js` consumes the
exact SSE frame shape `/api/batch/status/stream` already emits.

## Data model changes

None.

## UI/UX

No change — this is behavior-preserving extraction. The rendered Living
Docs page and the batch panel must be **byte-equivalent** to today
(verified live: panel hidden with no batch; identical states when one
runs). The only delta is `<script type="module">` (deferred) replacing
the inline IIFE; the panel attaches on load, so deferral is safe.

## Cross-layer impact

- **attune-gui** only. New `static_cw/batch-panel.js` + test, a one-line
  `vitest.config.ts` include, a template edit, and a docs page.
- **No attune-rag / help / author impact.**
- **Depends on** the batch panel being on `main` (shipped via
  [attune-gui#67](https://github.com/Smart-AI-Memory/attune-gui/pull/67),
  merged) — the implementation branch rebases onto current `main`.

## Tradeoffs & alternatives

| Option | Pros | Cons | Chosen? |
|--------|------|------|---------|
| **Extend editor-frontend Vitest** (include `../sidecar/.../static_cw`) | Reuses existing project, CI job, `node_modules`, config; one-line change; no build | Test glob reaches outside the project dir (cosmetic) | ✅ |
| New root JS project (`package.json` + `vitest.config.js` + CI job) | "Clean" separation of dashboard vs editor | Second `node_modules`, second CI job, more to maintain — more infra for no real gain | ❌ |
| Vite/TS for the dashboard | Strong typing | Adds a build step + bundle artifacts to a build-free surface; rejected at Phase 1 | ❌ |
| Keep logic inline, add jsdom tests against templates | No extraction | Can't unit-test HTML-embedded JS without a render harness; flaky; defeats the point | ❌ |

## Testing strategy

Pure-logic unit tests in `static_cw/batch-panel.test.js` (Node env, no
jsdom):

1. `batchView({state:"none"})` → `{visible:false}`.
2. `batchView({state:"error",detail})` → visible, "Status unavailable",
   detail passed through.
3. `batchView` pending: progress % from `request_counts` (done/total);
   `counts` string; non-terminal label = `processing_status`.
4. `batchView` terminal: "Completed — N succeeded, M errored".
5. `isTerminal`: true for each of `ended`/`canceled`/`expired` and for any
   `ended_at`; false otherwise.
6. `shouldClose`: true for `none`/`error`/terminal; false for pending
   non-terminal (the reconnect-suppression invariant — the bug this
   guards).
7. Division-by-zero guard: `request_count: 0` → `pct: 0`, not `NaN`.

Plus one **live re-verification** (manual, per the verification workflow):
load `/dashboard/living-docs`, confirm `GET /api/batch/status/stream` →
200, panel hidden on no-batch, no console errors — identical to pre-change
behavior.

## Rollback

Self-contained and revertable in one commit: restore the inline IIFE in
`living_docs.html`, drop `batch-panel.{js,test.js}` and the
`vitest.config.ts` include line. No data, route, or contract migration.
Until a panel is migrated, its inline JS keeps working unchanged — the
other 7 blocks are untouched by this PR.
