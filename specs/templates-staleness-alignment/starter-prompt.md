# Starter prompt — Templates page staleness alignment

> Paste this into a fresh Claude Code session (started from
> `~/attune/attune-gui`) to pick up the work cold. The spec
> (`requirements.md` / `design.md` / `tasks.md` next to this file)
> is the source of truth; the prompt below just frames the context
> and guardrails.

---

```
I'm implementing the Templates page staleness alignment from
specs/templates-staleness-alignment/. Phases 1, 2, and 3 are all
approved — read those three files end-to-end before doing anything.

Branch: create `feat/templates-staleness-alignment` off main in
attune-gui.

The spec breaks the work into 11 tasks (Task 0 = recon, Tasks 1–10
= implementation). Do Task 0 FIRST and report findings before
writing any production code — it answers three open questions that
shape Tasks 6, 7, and 8.

Task 0 — recon (~30 min):
  1. Does attune-author publish a test helper for building a
     (manifest + sources + templates) triplet for staleness
     assertions? If yes, use it. If no, build a minimal one in
     `sidecar/tests/_fixtures/staleness.py`.
  2. Grep the whole sidecar test suite for "very-stale" — list
     every assertion that needs updating in Task 8.
  3. Locate where the Templates page badge styles live. Almost
     certainly Jinja template + `cw-static/style.css`, but
     confirm. If the badge HTML is generated client-side, that
     changes Task 7.

Then implement Tasks 1 → 10 in order. The ordering in tasks.md is
intentional: cache module → mapping helper → wire into route →
invalidation hooks (3 sites) → UI → cleanup → docs.

Important context the spec assumes you've already absorbed:

  • The bug being fixed: `/dashboard/templates` uses mtime
    thresholds (<14d fresh / 14-60d stale / ≥60d very-stale).
    `author.maintain` uses semantic hashes from
    `attune_author.staleness.check_staleness`. Patrick repro'd
    on 2026-05-22: 5 templates flagged stale by the page; maintain
    reports "Stale: 0 / 5". Both signals are individually correct
    — they answer different questions. We're picking ONE: the
    semantic-hash signal. mtime becomes informational only.

  • The chosen approach is A from the requirements (single source
    of truth, semantic hash). B and C were considered and
    REJECTED. Do not re-litigate.

  • `attune_author.staleness.check_staleness` returns per-FEATURE
    verdicts, not per-file. The mapping
    template → feature comes from the convention that
    templates live at `<help_dir>/templates/<feature>/…`. Files
    outside any feature dir get status `"manual"`.

  • The `staleness` JSON field's domain narrows from
    `{fresh, stale, very-stale}` → `{fresh, stale, manual,
    unknown}`. `very-stale` is GONE. The Task 8 sweep will catch
    test fallout.

  • Graceful-degrade is a hard requirement: if
    `attune_author.staleness` import fails, return `"unknown"`
    for everything and log ONCE per workspace. The page must
    not break.

  • The cache is in-memory only. No persistence. Cleared on
    sidecar restart. This was explicitly chosen — out-of-scope
    items in tasks.md list persistence as deferred.

  • Three invalidation hook sites (see design.md):
      1. `commands.py:99-106` `_author_proxy(invalidate_after=True)`
         — add a sibling call next to the existing RAG invalidate
      2. `routes/editor_template.py` `/template/save` 200 handler
      3. `routes/editor_ws.py` `file_changed` event handler
    All three call into the same cache module.

Test strategy is in tasks.md §"Testing strategy". The keystone is
`test_staleness_cache.py` — every cache state + every graceful-
degrade path. Get that right and the rest follows.

Performance gates (tasks.md §"Performance check"): on a workspace
with ≥100 templates, first `list_templates()` after sidecar
restart must be < 500ms cold / < 50ms warm. If cold exceeds
500ms, file a follow-up (don't add complexity to this PR).

Workflow:
  1. Read all three spec files (requirements.md, design.md,
     tasks.md) before any code.
  2. Do Task 0. Report findings in chat — wait for ack before
     starting Task 1.
  3. After each task, run `pytest sidecar/tests -q` and
     `ruff check sidecar/`. Commit per task with a
     conventional `feat:` / `refactor:` / `test:` / `docs:`
     prefix.
  4. After Task 10, open one PR linking back to this spec
     directory.

Constraints:
  • This is attune-gui ONLY. Do not touch attune-rag,
    attune-help, or attune-author. The fix is a consumer-side
    change — attune-author already provides the right signal.
  • Do not add new dependencies. `attune_author` is already on
    the import path via `commands.py`.
  • Do not change `attune_author.staleness` behavior. We are
    consuming it, not improving it.
  • Do not merge to main without Patrick's approval. Open the
    PR and stop.

Out of scope (named in tasks.md §"Out of scope" — refuse to do
these even if they seem like obvious adjacent improvements):
  • Persisting the freshness cache across sidecar restarts.
  • Background-refresh of the Templates page.
  • Living Docs quality-scoring alignment.
  • Changing the semantic-hash algorithm.

Start by reading requirements.md.
```

---

## How this prompt was authored

Assembled at the close of the spec-writing session (2026-05-22)
that produced all three Phase 1–3 docs. Captures the *non-obvious*
context an implementer would otherwise rediscover the hard way:

- **The bug's two-signal nature.** A new implementer who only
  reads `cowork_templates.py` will conclude the mtime logic is
  fine and miss that `author.maintain` exists at all. The prompt
  names both, names the repro, and forbids re-litigating the
  choice.
- **Why semantic hash works on per-feature granularity.** The
  manifest-driven mapping is non-obvious from a cold read of
  attune-gui alone.
- **The three invalidation sites.** Easy to do site #1 and forget
  the editor save / watchfiles ones, then ship a cache that goes
  stale silently.
- **Task 0 as a gate.** The recon answers three questions that
  shape later tasks. Doing it first prevents a half-implemented
  feature waiting on basic facts.

If a future spec reuses this prompt structure, the high-value
sections are:
1. *Branch + spec pointer* (one line each).
2. *Task 0 as a gate* — explicit "report findings before code."
3. *The bug's nature* — what the user saw, why the obvious read
   of the code is wrong.
4. *Locked design decisions* — list of "do this, not that" pairs
   with one-line rationale each.
5. *Workflow* — explicit pytest/ruff commands per task.
6. *Out-of-scope list*, named so the agent refuses adjacent work
   even when it would feel productive.
