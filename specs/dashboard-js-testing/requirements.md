# Spec: Testable Cowork dashboard JS

> Single-layer feature (attune-gui). Uses the platform template
> (`specs/TEMPLATE.md`).

---

## Phase 1: Requirements

**Status**: approved (2026-06-14)

### Problem statement

The attune-gui **Cowork dashboard** ships all of its interactive
behavior as inline `<script>` blocks inside Jinja templates — **8 blocks**
across `base.html`, `living_docs.html`, `home.html`, `commands.html`,
`preview.html`, `templates.html`, and others. None of it is testable: the
logic is welded into HTML, so there is no unit boundary.

Meanwhile the **template editor** (`editor-frontend/`) is a Vite/TS app
with a healthy Vitest suite (9+ `*.test.ts` files) wired into the
`frontend (Vitest)` CI job. The split is stark: the editor's logic is
well-covered; the dashboard's interactive logic has **zero automated
tests**. `tech.md` records this as standing debt ("attune-gui UI has no
tests") — this spec makes it precise (the *Cowork dashboard inline JS*,
not the editor) and starts closing it.

The gap is live, not theoretical: the batch-status SSE panel shipped in
[attune-gui#67](https://github.com/Smart-AI-Memory/attune-gui/pull/67)
has a non-trivial client state machine (frame → render state,
`isTerminal`, progress %, and a close-the-stream-to-suppress-reconnect
decision) that was verified **once by hand**. The SSE *backend* has 12
tests; the *client* that renders it has none, and no Python test can
cover it.

### Scope

**In scope:**

- A **no-build ES-module pattern** for dashboard JS: extract pure logic
  from inline `<script>` into plain `.js` modules under
  `sidecar/attune_gui/static_cw/` (served as-is via the existing
  `/cw-static` mount — no bundler, no build artifacts), loaded from
  templates via `<script type="module">`.
- A **Vitest path that covers `static_cw/**/*.test.js`** and runs on
  every PR. Today Vitest lives **only** in `editor-frontend/` (its
  `package.json` + `vitest.config.ts`), and the `frontend (Vitest)` CI
  job is scoped to that directory — there is **no** root `package.json`.
  The design decides whether to extend the editor-frontend project to
  cover the dashboard modules or stand up a separate root project (see
  design Tradeoffs).
- **Reference implementation: the batch panel.** Extract
  `batchProgress`'s pure functions (`renderState(frame)`, `isTerminal`,
  progress %, reconnect decision) from `living_docs.html` into a tested
  module, leaving a thin DOM-glue shim inline. This is the canonical
  example the other blocks follow.
- A short **"how to test dashboard JS" doc** (pattern + example) so
  future panels are testable by default.

**Out of scope (this spec):**

- Migrating the other 7 inline script blocks — they follow the pattern
  **incrementally** in later PRs, not here. _(Default — overridable at
  review; alternatives considered: two-highest-logic-panels, or all-8 in
  one sweep.)_
- A build step / bundler / TypeScript for the dashboard — explicitly
  rejected (see Tradeoffs). The editor-frontend's Vite/TS stack stays
  its own thing.
- Any change to the dashboard's runtime behavior or appearance — this is
  pure extraction + tests; the rendered page must be byte-equivalent.
- JSDOM DOM/EventSource integration tests — **pure-logic-first** is the
  default depth _(overridable at review)_; DOM-level tests are a possible
  follow-up.

### User stories

1. **As an attune-gui maintainer**, I want the dashboard's interactive
   logic in tested modules so a refactor that breaks the batch panel (or
   the living-docs poller) fails CI instead of shipping silently.
2. **As a contributor adding a dashboard panel**, I want a documented
   no-build pattern (extract pure logic → module → Vitest) so new UI is
   testable without standing up a bundler.
3. **As a reviewer**, I want the batch panel's state machine covered by
   unit tests so I can trust changes to it without manually driving a
   live batch.

### Affected layers

- [x] attune-gui (frontend) — primary and only
- [ ] attune-rag / attune-help / attune-author — no changes

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Untested dashboard inline JS; start with batch panel as the reference pattern. |
| **Data & API contracts** | addressed | No API change. Modules consume the same SSE/JSON shapes the inline JS does today. |
| **UI/UX & states** | addressed | No visual/behavior change — extraction only; page must render identically. |
| **Edge cases** | addressed | See table below — module/MIME serving, no-build import correctness, CI discovery. |
| **Cross-layer impact** | addressed | None — single layer. |
| **Error handling** | addressed | Extracted logic preserves existing fallback behavior (e.g. malformed SSE frame → no-op). Tests assert it. |
| **Tradeoffs & alternatives** | addressed | No-build ES modules vs Vite/TS vs JSDoc; batch-only vs broader scope. See below. |
| **Rollback strategy** | addressed | Per-panel extraction is revertable in isolation; inline fallback remains until a panel is migrated. |

### Edge cases & open questions

| Question / Edge case | Resolution |
|----------------------|------------|
| Does `StaticFiles` serve `.js` with the right `text/javascript` MIME for `type="module"`? | Verify in design; Starlette `StaticFiles` infers MIME from extension — `.js` should be correct. Add a smoke check. |
| No build step — how do modules import each other? | Native ES `import` from `/cw-static/*.js`. Keep the dependency graph flat (one module per panel + a tiny shared util) so no bundler is needed. |
| Vitest runs in Node, but modules target the browser. | Author pure functions free of DOM/`window` so they import cleanly under Vitest. DOM glue stays in the inline shim, out of the tested module. |
| Will the existing `frontend (Vitest)` CI job pick these up? | No — it's `working-directory: editor-frontend`, and there is no root `package.json`. Design must either broaden the editor-frontend Vitest project (include `../sidecar/.../static_cw/**/*.test.js`) or stand up a separate root project + CI job. |
| CSP / `type="module"` interaction with the origin guard? | Module scripts are same-origin from `/cw-static`; no inline-script CSP change. Confirm no regression in design. |
| Does extraction risk load-order bugs (inline scripts run immediately; modules are deferred)? | `type="module"` is deferred by spec. Confirm the batch panel doesn't depend on synchronous execution against already-parsed DOM; it attaches on load, so deferral is fine. Flag any block that relies on sync timing. |

### Success criteria

- The batch panel's pure logic lives in a `static_cw/*.js` ES module with
  Vitest coverage of: `none`/`error`/`pending`/terminal frame → render
  state, `isTerminal`, progress %, and the reconnect-suppression
  decision.
- `npm test` (root) runs the dashboard module tests, and a CI job runs
  them on every PR (red on failure).
- The Living Docs page renders and behaves **identically** to today (no
  visual/behavior diff; verified live).
- A documented pattern exists so the remaining 7 inline blocks can be
  migrated the same way.
- No build step, no bundle artifact, no TypeScript added to the dashboard.

---

## Phase 2: Design

**Status**: draft — see [`design.md`](design.md)

## Phase 3: Tasks

**Status**: not started
