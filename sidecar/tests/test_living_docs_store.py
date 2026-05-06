"""Tests for DocEntry.reason field plumbing in LivingDocsStore."""

from __future__ import annotations

from attune_gui.living_docs_store import DocEntry


def _entry(**kwargs) -> DocEntry:
    defaults = dict(
        id="feat/concept",
        feature="feat",
        depth="concept",
        persona="end_user",
        status="current",
        path=".help/templates/feat/concept.md",
        last_modified=None,
    )
    return DocEntry(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# reason field defaults and serialisation
# ---------------------------------------------------------------------------


def test_reason_defaults_to_none():
    entry = _entry()
    assert entry.reason is None


def test_reason_appears_in_to_dict():
    entry = _entry(reason="signature changed: Foo.bar")
    d = entry.to_dict()
    assert d["reason"] == "signature changed: Foo.bar"


def test_reason_none_serialises_as_null():
    entry = _entry()
    d = entry.to_dict()
    assert "reason" in d
    assert d["reason"] is None


# ---------------------------------------------------------------------------
# Backward-compat: missing stale_reasons attribute on report
# ---------------------------------------------------------------------------


def test_getattr_fallback_on_report_without_stale_reasons():
    """getattr(report, "stale_reasons", {}) must return {} when attribute absent.

    This mirrors the defensive pattern used in _scan_sync so that consumers
    running against an older attune-help (pre-0.10) don't raise AttributeError.
    """

    class _OldReport:
        stale_features: list[str] = []

    report = _OldReport()
    stale_reasons = getattr(report, "stale_reasons", {})
    assert stale_reasons == {}
    assert stale_reasons.get("any_feature") is None


def test_scan_sync_produces_reason_none_when_no_help_dir(tmp_path):
    """_scan_sync completes without error when .help/ is absent."""
    from attune_gui.living_docs_store import LivingDocsStore

    store = LivingDocsStore()
    docs = store._scan_sync(tmp_path)
    assert docs == []


# ---------------------------------------------------------------------------
# Persistence — queue + quality survive restart, missing/corrupt file are safe
# ---------------------------------------------------------------------------


import pytest  # noqa: E402
from attune_gui.living_docs_store import (  # noqa: E402
    _STATE_SCHEMA_VERSION,
    LivingDocsStore,
    ReviewItem,
)


def test_load_state_missing_file_starts_empty(tmp_path):
    state_path = tmp_path / "living_docs.json"
    store = LivingDocsStore(state_path=state_path)
    assert store._queue == []
    assert store._quality == {}


def test_load_state_corrupt_json_starts_empty(tmp_path, caplog):
    state_path = tmp_path / "living_docs.json"
    state_path.write_text("{not json", encoding="utf-8")
    with caplog.at_level("WARNING"):
        store = LivingDocsStore(state_path=state_path)
    assert store._queue == []
    assert store._quality == {}
    assert any("corrupt" in rec.message for rec in caplog.records)


def test_load_state_wrong_version_starts_empty(tmp_path, caplog):
    state_path = tmp_path / "living_docs.json"
    state_path.write_text(
        '{"version": 999, "queue": [], "quality": {}}',
        encoding="utf-8",
    )
    with caplog.at_level("WARNING"):
        store = LivingDocsStore(state_path=state_path)
    assert store._queue == []
    assert store._quality == {}


def test_load_state_unexpected_shape_starts_empty(tmp_path, caplog):
    state_path = tmp_path / "living_docs.json"
    state_path.write_text("[]", encoding="utf-8")
    with caplog.at_level("WARNING"):
        store = LivingDocsStore(state_path=state_path)
    assert store._queue == []


def test_save_state_round_trips_queue_and_quality(tmp_path):
    state_path = tmp_path / "living_docs.json"
    store = LivingDocsStore(state_path=state_path)
    store._queue.append(
        ReviewItem(
            id="abc",
            doc_id="auth/concept",
            feature="auth",
            depth="concept",
            persona="end_user",
            trigger="manual",
            auto_applied_at="2026-05-05T00:00:00+00:00",
            diff_summary="1 insertion",
        )
    )
    store._quality = {"faithfulness": 0.92}
    store._save_state()

    second = LivingDocsStore(state_path=state_path)
    assert len(second._queue) == 1
    assert second._queue[0].id == "abc"
    assert second._queue[0].doc_id == "auth/concept"
    assert second._quality == {"faithfulness": 0.92}


def test_save_state_writes_schema_version(tmp_path):
    import json

    state_path = tmp_path / "living_docs.json"
    store = LivingDocsStore(state_path=state_path)
    store._save_state()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert data["version"] == _STATE_SCHEMA_VERSION


def test_save_state_skips_malformed_queue_entry(tmp_path, caplog):
    state_path = tmp_path / "living_docs.json"
    state_path.write_text(
        '{"version": 1, "queue": [{"id": "a"}], "quality": {}}',
        encoding="utf-8",
    )
    with caplog.at_level("WARNING"):
        store = LivingDocsStore(state_path=state_path)
    assert store._queue == []
    assert any("malformed queue entry" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_add_to_queue_persists(tmp_path):
    """add_to_queue should persist; a second store instance sees the item."""
    state_path = tmp_path / "living_docs.json"
    project_root = tmp_path / "proj"
    project_root.mkdir()

    store = LivingDocsStore(state_path=state_path)
    await store.add_to_queue("auth/concept", "manual", project_root)

    second = LivingDocsStore(state_path=state_path)
    assert len(second._queue) == 1
    assert second._queue[0].doc_id == "auth/concept"


@pytest.mark.asyncio
async def test_set_quality_persists(tmp_path):
    state_path = tmp_path / "living_docs.json"
    store = LivingDocsStore(state_path=state_path)
    await store.set_quality({"strict": 0.8})

    second = LivingDocsStore(state_path=state_path)
    assert second._quality == {"strict": 0.8}


@pytest.mark.asyncio
async def test_approve_persists_reviewed_flag(tmp_path):
    state_path = tmp_path / "living_docs.json"
    project_root = tmp_path / "proj"
    project_root.mkdir()

    store = LivingDocsStore(state_path=state_path)
    item = await store.add_to_queue("auth/concept", "manual", project_root)
    ok = await store.approve(item.id)
    assert ok is True

    second = LivingDocsStore(state_path=state_path)
    assert len(second._queue) == 1
    assert second._queue[0].reviewed is True
