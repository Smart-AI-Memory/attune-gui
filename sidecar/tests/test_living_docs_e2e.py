"""Playwright smoke tests for the Living Docs inline-actions UI.

Skipped automatically when playwright is not installed. Install with:
    pip install playwright && playwright install chromium

Three scenarios:
  1. No-JS page load  — table renders with correct badge text server-side
  2. Regenerate flow  — clicking Regenerate shows spinner; no navigation away
  3. Approve flow     — clicking Approve transitions row to current without reload
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

# Guard the whole module — skip if playwright not installed.
pytest.importorskip("playwright.sync_api")

from playwright.sync_api import Page, sync_playwright  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(base_url: str, timeout: float = 10.0) -> None:
    import httpx

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            httpx.get(f"{base_url}/api/living-docs/health", timeout=1)
            return
        except Exception:  # noqa: BLE001
            time.sleep(0.05)
    raise RuntimeError(f"Server at {base_url} did not start within {timeout}s")


@pytest.fixture(scope="module")
def seeded_server():
    """Start a real uvicorn server pre-seeded with one stale doc + one pending-review item."""
    import uvicorn
    from attune_gui import jobs as jobs_mod
    from attune_gui import living_docs_store
    from attune_gui.app import create_app
    from attune_gui.living_docs_store import DocEntry, LivingDocsStore, ReviewItem

    # Build a fresh store with known state before the server thread starts.
    # Because uvicorn runs in the same process, it sees the same module globals.
    store = LivingDocsStore()
    store._docs = [
        DocEntry(
            id="auth/concept",
            feature="auth",
            depth="concept",
            persona="end_user",
            status="stale",
            path=".help/templates/auth/concept.md",
            last_modified=None,
            reason="feature config changed",
        ),
        DocEntry(
            id="auth/reference",
            feature="auth",
            depth="reference",
            persona="developer",
            status="current",
            path=".help/templates/auth/reference.md",
            last_modified=None,
        ),
        DocEntry(
            id="memory/concept",
            feature="memory",
            depth="concept",
            persona="end_user",
            status="current",
            path=".help/templates/memory/concept.md",
            last_modified=None,
        ),
    ]
    store._queue = [
        ReviewItem(
            id="qi-pending-001",
            doc_id="auth/reference",
            feature="auth",
            depth="reference",
            persona="developer",
            trigger="manual",
            auto_applied_at="2026-05-01T00:00:00+00:00",
            reviewed=False,
            diff_summary="3 insertions(+), 1 deletion(-)",
        )
    ]
    living_docs_store._store = store
    jobs_mod._REGISTRY = None  # fresh registry

    port = _free_port()
    app = create_app()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    _wait_for_server(base_url)

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def pw_browser():
    """Module-scoped Playwright browser (chromium)."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


# ---------------------------------------------------------------------------
# Test 1 — No-JS page load
# ---------------------------------------------------------------------------


def test_nojs_page_renders_table_with_badges(seeded_server, pw_browser):
    """Disable JS; verify server-rendered HTML has correct badge text for each state."""
    context = pw_browser.new_context(java_script_enabled=False)
    page: Page = context.new_page()
    page.goto(f"{seeded_server}/dashboard/living-docs")

    # Page title present
    assert "Living Docs" in page.title()

    # Table renders
    assert page.locator("table.data-table tbody tr").count() >= 3

    # stale row renders a 'stale' badge
    stale_tr = page.locator("tr[data-doc-id='auth/concept']")
    assert stale_tr.count() == 1
    badge = stale_tr.locator("[data-slot='badge'] .badge")
    assert "stale" in badge.inner_text()

    # pending-review row renders 'pending review' badge
    pending_tr = page.locator("tr[data-doc-id='auth/reference']")
    assert pending_tr.count() == 1
    pending_badge = pending_tr.locator("[data-slot='badge'] .badge")
    assert "pending" in pending_badge.inner_text()

    # current row renders 'current' badge
    current_tr = page.locator("tr[data-doc-id='memory/concept']")
    assert current_tr.count() == 1
    current_badge = current_tr.locator("[data-slot='badge'] .badge")
    assert "current" in current_badge.inner_text()

    context.close()


# ---------------------------------------------------------------------------
# Test 2 — Regenerate starts poller, no navigation
# ---------------------------------------------------------------------------


def test_regenerate_shows_spinner_and_stays_on_page(seeded_server, pw_browser):
    """Click Regenerate; row should show spinner text and the URL must not change."""
    context = pw_browser.new_context()
    page: Page = context.new_page()

    # Mock the regenerate endpoint to return a job dict immediately.
    page.route(
        "**/api/living-docs/docs/**/regenerate",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"id":"job-abc","name":"living-docs.regenerate","status":"running","args":{}}',
        ),
    )

    # Mock the polling endpoint to return 'regenerating' state.
    page.route(
        "**/api/living-docs/rows",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "rows": [
                    {"id":"auth/concept","feature":"auth","depth":"concept",
                     "persona":"end_user","base_status":"stale",
                     "computed_state":"regenerating","reason":null,"last_modified":null,
                     "regen_job_id":"job-abc","regen_job_status":"running",
                     "regen_job_error":null,"queue_item_id":null,"diff_summary":null},
                    {"id":"auth/reference","feature":"auth","depth":"reference",
                     "persona":"developer","base_status":"current",
                     "computed_state":"pending-review","reason":null,"last_modified":null,
                     "regen_job_id":null,"regen_job_status":null,"regen_job_error":null,
                     "queue_item_id":"qi-pending-001",
                     "diff_summary":"3 insertions(+), 1 deletion(-)"},
                    {"id":"memory/concept","feature":"memory","depth":"concept",
                     "persona":"end_user","base_status":"current",
                     "computed_state":"current","reason":null,"last_modified":null,
                     "regen_job_id":null,"regen_job_status":null,"regen_job_error":null,
                     "queue_item_id":null,"diff_summary":null}
                ]
            }""",
        ),
    )

    page.goto(f"{seeded_server}/dashboard/living-docs")
    original_url = page.url

    stale_tr = page.locator("tr[data-doc-id='auth/concept']")
    regen_btn = stale_tr.locator(".btn-regen")
    assert regen_btn.count() == 1

    regen_btn.click()

    # Badge in the row should update to 'regenerating'.
    page.wait_for_function(
        "() => document.querySelector("
        "\"tr[data-doc-id='auth/concept'] [data-slot='badge']\")"
        ".innerText.includes('regenerating')",
        timeout=3000,
    )

    # URL must not change — no navigation to /dashboard/jobs.
    assert page.url == original_url

    context.close()


# ---------------------------------------------------------------------------
# Test 3 — Approve transitions row to current without page reload
# ---------------------------------------------------------------------------


def test_approve_transitions_row_without_reload(seeded_server, pw_browser):
    """Click Approve on a pending-review row; row should become 'current' in place."""
    context = pw_browser.new_context()
    page: Page = context.new_page()

    # Track whether a full page reload happened by watching navigation events.
    navigations: list[str] = []
    page.on(
        "framenavigated",
        lambda frame: navigations.append(frame.url) if frame == page.main_frame else None,
    )

    # Mock approve endpoint.
    page.route(
        "**/api/living-docs/queue/**/approve",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"ok":true,"item_id":"qi-pending-001"}',
        ),
    )

    # Mock rows endpoint to return 'current' for auth/reference after approve.
    page.route(
        "**/api/living-docs/rows",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body="""{
                "rows": [
                    {"id":"auth/concept","feature":"auth","depth":"concept",
                     "persona":"end_user","base_status":"stale",
                     "computed_state":"stale","reason":null,"last_modified":null,
                     "regen_job_id":null,"regen_job_status":null,"regen_job_error":null,
                     "queue_item_id":null,"diff_summary":null},
                    {"id":"auth/reference","feature":"auth","depth":"reference",
                     "persona":"developer","base_status":"current",
                     "computed_state":"current","reason":null,"last_modified":null,
                     "regen_job_id":null,"regen_job_status":null,"regen_job_error":null,
                     "queue_item_id":null,"diff_summary":null},
                    {"id":"memory/concept","feature":"memory","depth":"concept",
                     "persona":"end_user","base_status":"current",
                     "computed_state":"current","reason":null,"last_modified":null,
                     "regen_job_id":null,"regen_job_status":null,"regen_job_error":null,
                     "queue_item_id":null,"diff_summary":null}
                ]
            }""",
        ),
    )

    page.goto(f"{seeded_server}/dashboard/living-docs")
    # Record URL after initial load (the goto navigation doesn't count).
    navigations.clear()

    pending_tr = page.locator("tr[data-doc-id='auth/reference']")
    approve_btn = pending_tr.locator(".btn-approve")
    assert approve_btn.count() == 1

    approve_btn.click()

    # Row badge should update to 'current'.
    page.wait_for_function(
        "() => document.querySelector("
        "\"tr[data-doc-id='auth/reference'] [data-slot='badge']\")"
        ".innerText.includes('current')",
        timeout=3000,
    )

    # No full-page navigation should have happened.
    assert not any("/dashboard/living-docs" in u for u in navigations), (
        f"Unexpected navigation(s): {navigations}"
    )

    context.close()
