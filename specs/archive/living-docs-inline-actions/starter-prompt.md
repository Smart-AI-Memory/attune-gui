# Starter prompt — Living Docs Inline Actions

> Paste this into a fresh Claude Code session to pick up the work
> cold. The spec (`requirements.md` next to this file) is the
> source of truth; the prompt below just frames the context and
> guardrails.

---

```
I'm implementing the Living Docs inline-actions redesign from
specs/living-docs-inline-actions/requirements.md. Phases 1, 2, and 3
are all approved — read that file end-to-end before doing anything.

Branch: create `feat/living-docs-inline-actions` off main in
attune-gui.

The spec breaks the work into 10 ordered tasks. Pick them up in
order; do NOT skip ahead, the dependencies in §"Dependencies" are
real. Specifically:
  - Tasks 1-3 must land first (helper → endpoint → tests)
  - Task 4 (server-rendered initial paint) before task 5 (JS)
  - Task 8 (cleanup) lands with or after task 5

Important context the spec assumes you've already absorbed:

  • The previous attune-gui PR #12 already routed the Regenerate
    button through the Jobs system. Do NOT rewrite that — the
    `_regenerate_doc_executor` and the `living-docs.regenerate`
    job name stay. The redesign is purely the UI on top.

  • The dashboard's Templates page is structurally similar and is
    a future migration candidate. This spec is explicit that
    Templates migration is OUT OF SCOPE for this PR. Don't
    refactor Templates "while you're in there." That's a
    follow-up.

  • Smart polling, NOT WebSocket. 1.5s interval. Only while any
    row has `regen_job_id` set. NO `location.reload()` — patch
    the DOM in place. The spec's §2.1 has the rationale.

  • The composed endpoint is server-side join, NOT a client-side
    join across three endpoints. The spec's §2.2 has the
    rationale and the exact response shape.

  • The state-priority rule (regenerating > pending-review >
    errored > stale > current) is NOT my preference — it's a
    locked design decision in §2.4. Implement it as written.

Test strategy is in §"Testing strategy". The keystone is unit
tests on `_project_doc_state` — every state combination + every
priority rule. Get that right and the rest follows.

Workflow:
  1. Read specs/living-docs-inline-actions/requirements.md
  2. Skim attune-gui's existing routes/living_docs.py to
     understand current shape
  3. Skim sidecar/attune_gui/templates/living_docs.html and
     templates/jobs.html for the Jinja patterns the codebase uses
  4. Start on Task 1: extract `_project_doc_state` as a pure
     function. Write its tests (Task 3) immediately after to
     keep the contract tight.
  5. After each task, run `pytest sidecar/tests -q`,
     `ruff check sidecar/`, and `make build-editor` if you
     touched the bundle. Commit per task with a conventional
     `feat:` / `refactor:` / `test:` prefix.
  6. After Task 9 (Playwright), open one PR linking back to the
     spec.

Constraints:
  • Don't touch attune-rag or attune-author — pure attune-gui work.
  • Don't add new dependencies. Vanilla JS + the existing AttuneUI
    helpers. No reactive frameworks.
  • Don't merge to main without my approval. Open the PR and stop.

Out of scope (named in §"Out of scope" — refuse to do these even
if it seems like an obvious adjacent improvement):
  • Bulk-regenerate-all button
  • Full unified-diff inline preview (only diff_summary one-liner)
  • Templates page migration
  • WebSocket transport
  • Optimistic UI on Approve/Revert

Start by reading the spec.
```

---

## How this prompt was authored

This prompt was assembled at the close of the spec-writing session
that produced `requirements.md`. It captures the *non-obvious*
context an implementer would otherwise rediscover the hard way:

- **Which existing infrastructure is reused vs replaced.** PR #12
  laid the foundation (route + executor + Jobs visibility); the
  redesign is on top. New implementers tend to redo work they
  shouldn't.
- **Which decisions are locked.** Smart polling, composed
  endpoint, state priority, drop-the-queue-section — all four
  were debated and decided in the counsel session that closed
  Phase 2. Re-debating them in implementation wastes a session.
- **Out-of-scope items.** Adjacent improvements that look
  obvious but belong in their own spec.

If a future spec reuses the same prompt structure, the high-value
sections are:
1. *Branch + spec pointer* (one line each).
2. *Task ordering rules* (what depends on what).
3. *Locked design decisions* — list of "do this, not that"
   pairs with a one-line rationale.
4. *Workflow* — explicit pytest/ruff/build commands per task.
5. *Out-of-scope list*, named so the agent refuses adjacent
   work even when it would feel productive.
