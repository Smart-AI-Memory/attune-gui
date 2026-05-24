# Decisions — Living-docs regen automation

**Status:** draft — awaiting decision on Approach.
**Owner:** Patrick

## Problem

Almost every code-touching PR in attune-gui needs a follow-up
"regenerate sidecar templates" commit added by hand. The
sidecar generates living-docs templates (`.help/templates/`)
and a Vite editor bundle (`editor-frontend/dist/`) that are
**both committed** to the repo. When source changes, the
generated artifacts drift, and a contributor (or assistant)
has to remember to regenerate and commit them in a second
step.

Recent examples — every one of these triggered a manual
follow-up regen commit:

- `30cc722` fix(specs) → `ac6b552` regenerate
- `d282f21` test(mcp) → `7e01b1a` regenerate
- `1657c2f` feat(mcp) → `db4c562` regenerate
- `05489c1` feat(mcp/tools) → regenerate

Across ~10 PRs over recent weeks, that's ~10 extra commits of
mechanical work. The risk is not "we forget once" — the risk
is *we forget often enough that stale generated files become
the norm* and the living-docs system silently drifts from the
source of truth.

## Current state (verified 2026-05-23)

- No git hooks installed (`.pre-commit-config.yaml`,
  `.husky/`, `lefthook.yml` all absent).
- A post-commit *webhook* exists (`scripts/install-living-docs-hook.sh`)
  but it only **notifies the sidecar to scan** — it does
  not regenerate.
- CI (`.github/workflows/tests.yml`) runs ruff + pytest +
  vitest typecheck. **It does not check for stale generated
  artifacts.**
- Generated artifacts are deterministic:
  - Editor bundle uses Vite content-hashed filenames, no
    timestamps in output.
  - Living-docs templates have `generated_at` (timestamp)
    and `source_hash` (content hash) frontmatter — `generated_at`
    is the only intrinsic source of churn, and it's not
    semantic.

## Decision

**Approach: CI-fail-if-stale + a single `make regen-all` target.**

CI runs `make regen-all` then `git diff --exit-code`. If any
generated file changed, CI fails with a clear message pointing
the contributor at `make regen-all` to fix locally. No
auto-commit, no bot, no pre-commit hook blocking local work.

The contributor's loop becomes:

```bash
# After making source changes that touch templates or editor:
make regen-all
git add -u
git commit -m "regenerate sidecar templates"
```

If they forget, CI tells them in the same PR run.

### Why this and not the alternatives

| Option | Pro | Con |
|---|---|---|
| **Pre-commit hook** (chosen against) | Catches drift at commit time. | Blocks local commits; slow (editor build is ~7s + author maintain on top); requires Node + uv on every contributor's machine; regen is partly async — hard to wait for completion in a hook; many contributors disable hooks. |
| **Post-merge bot commit** (chosen against) | Zero friction; always-correct main. | Needs bot write access to main; conflicts with stacked-PR rebases; adds noise (one bot commit per PR); audit trail becomes "Claude regenerated these" rather than "Patrick approved these"; opaque. |
| **CI fail-if-stale** (chosen) | Visible; deterministic; no bot access; one command for contributors; aligns incentives — the PR author owns the regen. | Adds friction of one extra command + commit per affected PR. (Net win: it's the friction we already pay manually, but now it's enforced, so we stop forgetting.) |
| **Auto-regen commit in CI** (chosen against) | No contributor friction. | Same bot-access concerns as post-merge; harder to attribute changes; stacked-PR conflict surface. |

## Scope

**In scope:**

1. New `make regen-all` target that runs:
   - `make build-editor` (already exists at `Makefile:6-18`)
   - `attune-author maintain` for the sidecar living-docs corpus
   - Any other regen step we discover during implementation
2. New CI job `regen-up-to-date` in `.github/workflows/tests.yml`:
   - Installs node + uv
   - Runs `make regen-all`
   - Runs `git diff --exit-code -- .help/ editor-frontend/dist/` (paths refined during impl)
   - On failure: prints a clear message with the fix command
3. README update under `## Development` documenting the contract.

**Out of scope:**

- Pre-commit hooks (deliberately).
- Any bot or automation that writes to main.
- Migrating the post-commit-webhook scan trigger (separate concern).
- Reducing the regen time itself (separate perf spec if it becomes painful).

## Acceptance criteria

- `make regen-all` is a single command that produces a clean
  working tree on a fresh checkout with no source changes.
- CI fails a PR that modifies source-of-truth files without
  regenerating, and the failure message names the fix command.
- README documents `make regen-all` in the existing
  `## Development` section.
- No new commits land on `main` from any bot account.

## Open questions

1. What's the exact `attune-author maintain` invocation for
   this repo's federated config? (Phase 1 task.)
2. Should we gate the CI check behind a label (e.g. only run
   `regen-up-to-date` when paths matching `sidecar/**` or
   `editor-frontend/src/**` change) to keep PR feedback fast
   for docs-only or test-only changes? Default: yes, conditional.
3. CI runtime budget — `make build-editor` is ~7s; `attune-author maintain`
   time unknown. If the combined regen-check exceeds 60s, revisit
   whether to split it.

## Phase outline (when this spec is approved)

- **Phase 1** — Inventory the exact regen commands and write `make regen-all`.
  **Status: shipped via #61.**
- **Phase 2** — Add the CI job, gated on relevant paths; verify it fails
  intentionally on a stale-artifact PR before flipping it to required.
  **Status: blocked.** See "Phase 2 blockers" below.
- **Phase 3** — README update; make the contract official.

## Phase 2 blockers (discovered 2026-05-23)

Phase 2 implementation attempt surfaced two foundational issues:

1. **attune-author regen vs. staleness check disagree on source_hash.**
   Running `attune-author regenerate` writes a new `source_hash` into the
   template frontmatter, but immediately running `attune-author regenerate
   --dry-run` (or `status`) still reports the same feature as stale. The
   loop never reaches a fixed point. Likely cause: regen hashes a
   budget-truncated source view (see `ground_truth.budget: dropped X to
   fit budget` log lines), while the staleness check hashes the full
   source set. Until this is fixed upstream, "fail-if-stale" has no
   meaningful signal — every PR would fail forever.

2. **Spec premise conflicts with CI policy.** This spec originally
   proposed `make regen-all` + `git diff --exit-code` in CI. That
   requires `ANTHROPIC_API_KEY` in CI for polish. But the existing
   workflow (`.github/workflows/tests.yml:38-46`) has an **explicit
   guard** that fails CI if `ANTHROPIC_API_KEY` is set in the default
   suite, to prevent non-`@live`-marked tests from leaking real API
   calls. The `--dry-run` workaround (no API needed) was the obvious
   alternative, but it's blocked by issue #1.

**Phase 2 stays parked until the upstream attune-author bug is fixed.**
Tracking: a chip was filed to debug + fix attune-author's hash
mismatch. Once that lands and attune-gui can pin a fixed release,
Phase 2 design needs a small refresh — likely `--dry-run` as the CI
signal (no API key needed, no policy conflict).
