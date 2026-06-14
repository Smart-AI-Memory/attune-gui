# Spec: Testable Living Docs poll state machine

> Single-layer feature (attune-gui). Follow-on to
> [`dashboard-js-testing`](../dashboard-js-testing/) — reuses its
> approved no-build ES-module + Vitest pattern (build strategy and test
> runner are already settled there; this spec does not re-litigate them).

---

## Phase 1: Requirements

**Status**: draft

### Problem statement

The Living Docs page polls `/api/living-docs/rows` while any document is
regenerating
([`living_docs.html`](attune-gui/sidecar/attune_gui/templates/living_docs.html),
`{% block scripts %}`). The poller — `_startPoll` / `_stopPoll` /
`_scheduleNextPoll` / `_poll` — is a recursive-`setTimeout` state machine
that must:

- **stop** once no row is `regenerating`
  ([`:200`](attune-gui/sidecar/attune_gui/templates/living_docs.html)),
- **pause** on a hidden tab and resume on `visibilitychange`,
- keep going on a transient fetch error (don't give up mid-regeneration).

This is exactly the kind of decision logic that breaks silently — polls
forever, stops too early, or hammers a backgrounded tab — and it is
**untested**. It's the next-richest untested inline block after the batch
panel, and migrating it applies the pattern established in
`dashboard-js-testing`.

### Scope

**In scope:**

- **Extract the poll decision logic** into a `static_cw/*.js` ES module —
  the pure parts: `shouldKeepPolling(rows)` (stop when none regenerating)
  and any next-delay helper. The module is DOM-free / timer-free so
  Vitest imports it in Node.
- **Vitest coverage** for the extracted logic, run by the existing
  `frontend (Vitest)` CI job (the include glob from
  `dashboard-js-testing`).
- **Shrink the inline script** to a `<script type="module">` glue shim
  that keeps the DOM/`setTimeout`/`visibilitychange` wiring and calls the
  module. Behavior-preserving.

**Out of scope:**

- **The Jinja↔JS `computed_state` → badge/action mapping duplication.**
  The same mapping is hand-maintained in Jinja
  ([`:118-157`](attune-gui/sidecar/attune_gui/templates/living_docs.html))
  and in JS `_renderBadge`/`_renderActions`
  ([`:228-256`](attune-gui/sidecar/attune_gui/templates/living_docs.html)).
  It's a real drift risk, but de-duplicating it (e.g. a server-provided
  presentational field) is a larger change with an API-payload impact —
  **deferred to its own follow-up spec**. This spec leaves both copies
  as-is; the glue shim still calls the existing `_renderBadge` /
  `_renderActions` unchanged.
- Other inline blocks (`commands.html`, etc.) — separate follow-ups.
- Re-deriving the build/test-runner choice — settled in
  `dashboard-js-testing`.
- Any change to poll cadence, action behavior, or API semantics.

### User stories

1. **As a maintainer**, I want the poll stop/continue logic unit-tested
   so a change can't silently make the dashboard poll forever or stop
   mid-regeneration.
2. **As a reviewer**, I want the extraction to be behavior-preserving and
   verified live before merge.

### Affected layers

- [x] attune-gui (frontend) — primary and only
- [ ] attune-rag / help / author — no changes

### Coverage areas

| Area | Status | Notes |
|------|--------|-------|
| **Problem & scope** | addressed | Untested poll state machine; extract + test the pure decision. |
| **Data & API contracts** | N/A | No API change — pure client refactor. |
| **UI/UX & states** | addressed | No visual/behavior change; same polling cadence and badges. |
| **Edge cases** | addressed | Empty rows, all-terminal rows (must stop), some-regenerating (must continue), hidden-tab pause, transient fetch error (keep polling). |
| **Cross-layer impact** | N/A | Single layer. |
| **Error handling** | addressed | Transient fetch error preserves current "keep polling" behavior; glue shim retains the try/catch. |
| **Tradeoffs & alternatives** | addressed | Pure-logic extraction vs. leaving inline (defeats the purpose) vs. de-dup refactor (deferred — see Out of scope). |
| **Rollback strategy** | addressed | Revert restores the inline poller; other blocks untouched. |

### Edge cases & open questions

| Question / Edge case | Resolution |
|----------------------|------------|
| Stop when no row regenerating | `shouldKeepPolling(rows)`: some `regenerating` → true; none → false; empty → false. Tested. |
| Hidden-tab pause / resume | Stays in the DOM shim (`document.hidden`, `visibilitychange`); not in the pure module. |
| Transient fetch error mid-poll | Shim keeps the existing try/catch + reschedule; `shouldKeepPolling` only decides from row data, not fetch outcome. |
| Does `_applyRows` / `_renderBadge` / `_renderActions` move? | **No** — DOM rendering stays inline this spec (the badge/action de-dup is a separate deferred spec). Only the poll decision is extracted. |
| What is `shouldKeepPolling`'s input shape? | The `rows` array from `/api/living-docs/rows` (objects with `computed_state`). Pure over that — no DOM. |

### Success criteria

- `shouldKeepPolling` (and any schedule helper) live in a tested
  `static_cw/*.js` module; Vitest covers stop / continue / empty.
- Living Docs polls **identically** to today — starts when a row is
  regenerating, stops when none are, pauses on hidden tab (verified
  live).
- The `frontend (Vitest)` CI job runs the new tests; no new infra.

### Gaps

- The Jinja↔JS badge/action duplication is a known drift risk left
  **explicitly deferred** to a follow-up spec (it needs an API-payload
  decision). Documented, not silently skipped.

---

## Phase 2: Design

**Status**: not started

## Phase 3: Tasks

**Status**: not started
