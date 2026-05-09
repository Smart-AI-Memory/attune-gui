# attune-gui sidecar tests

## Running locally

```bash
# Install dev deps (includes pytest-cov)
pip install -e ".[dev]"

# Default — Vitest e2e is deselected; pytest runs everything else
pytest

# With coverage (matches CI's py3.11 cell)
pytest --cov --cov-report=term-missing

# Opt in to e2e (Playwright; needs `playwright install chromium`)
pytest -m e2e
```

The `e2e` marker covers Playwright tests in `test_living_docs_e2e.py`.
They need a real uvicorn server and a Chromium install; pass 3 of the
test-strategy spec will stabilize and unify e2e workflows.

## LLM mocking standard

attune-gui itself makes no LLM calls — the heavy lifting is done by
`attune-author` and `attune-rag` upstream. Cross-layer integration tests
follow the **attune-author reference pattern**:

- Strip `ANTHROPIC_API_KEY` via an autouse fixture.
- Patch `anthropic.Anthropic` at import time, not at call site.
- Reset module-level singletons (e.g., `_PIPELINES`) between tests with
  an autouse fixture.

See `attune-author/tests/conftest.py` (`_lenient_polish_by_default`,
`_reset_rag_pipeline`). Pass 2 of the test-strategy spec will formalize
this into a shared `docs/testing-conventions.md` across layers.

## Contract tests

- `test_contract_attune_rag.py` — verifies how attune-gui consumes
  `attune_rag.RagPipeline.run()` results: hit shape, augmented prompt,
  error envelope on `ValueError` / generic exceptions, corpus-info
  aggregation.
- `test_contract_attune_help.py` — verifies how attune-gui consumes
  `attune_help.HelpEngine`: topics list, search with limit clamping,
  template_dir resolution semantics, error envelope shape.

These run consumer-side only — they mock at the boundary so the suite
stays fast and doesn't require a real corpus.

## What's tested vs. not

Tracked in
`/Users/patrickroebuck/attune/specs/test-strategy/current-state.md`. After
pass 1, the highest-value remaining gaps in this layer are:

- `routes/editor_template.py` route handlers (helpers covered; routes
  themselves still mostly indirect)
- `routes/editor_ws.py` (~80%) — WebSocket lifecycle
- `living_docs_store.py` (~86%) — review-queue paths

Pass 2 will revisit these.

## Pre-existing items deferred

- `test_origin_guard_allows_ipv6_loopback` is `xfail(strict=True)`
  documenting the IPv6-loopback parsing bug in
  `attune_gui/security.py:76`. Spawned as its own task during pass 1;
  fix lives in a separate PR.
- `test_living_docs_e2e.py` Playwright assertions are flaky/broken on
  some setups; gated by the `e2e` marker (deselected by default).
  Pass 3.
